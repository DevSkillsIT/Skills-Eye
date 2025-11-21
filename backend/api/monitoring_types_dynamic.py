"""
API para Monitoring Types DINÂMICOS extraídos de Prometheus.yml

Este endpoint SUBSTITUI os JSONs estáticos!
Extrai tipos de monitoramento diretamente dos jobs do prometheus.yml de cada servidor.

FONTE DA VERDADE: prometheus.yml (não JSONs)
"""

from fastapi import APIRouter, HTTPException, Query, Body
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
import logging
import asyncio
from datetime import datetime

from core.multi_config_manager import MultiConfigManager
from core.kv_manager import KVManager
from core.monitoring_types_backup import get_backup_manager
from core.consul_kv_config_manager import ConsulKVConfigManager
from core.categorization_rule_engine import CategorizationRuleEngine

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/monitoring-types-dynamic", tags=["Monitoring Types"])

# Instanciar managers
multi_config = MultiConfigManager()
kv_manager = KVManager()
backup_manager = get_backup_manager()

# ✅ SPEC-ARCH-001: Instanciar engine de categorização dinâmica
# O engine usa regras do KV como FONTE ÚNICA DA VERDADE para categorização
consul_kv_manager = ConsulKVConfigManager()
rule_engine = CategorizationRuleEngine(consul_kv_manager)


# ============================================================================
# MODELOS PYDANTIC
# ============================================================================

class FormSchemaUpdateRequest(BaseModel):
    """Request para atualizar form_schema de um tipo"""
    form_schema: Optional[Dict[str, Any]] = None
    server: Optional[str] = None  # ✅ NOVO: Servidor específico (opcional - se não fornecido, atualiza em todos)


async def _enrich_servers_with_sites_data(servers_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Enriquece dados de servidores com informações de sites do KV
    
    Faz match entre hostname do servidor e prometheus_host/prometheus_instance do site.
    
    Args:
        servers_data: Dict com dados dos servidores (hostname como key)
    
    Returns:
        Dict enriquecido com dados de sites
    """
    try:
        logger.info(f"[ENRICH-SITES] Iniciando enriquecimento de {len(servers_data)} servidores...")
        
        # Buscar sites do KV
        sites_kv = await kv_manager.get_json('skills/eye/metadata/sites')
        
        if not sites_kv:
            logger.warning("[ENRICH-SITES] ❌ KV sites vazio - servidores não serão enriquecidos")
            return servers_data
        
        logger.info(f"[ENRICH-SITES] ✅ KV sites encontrado: {type(sites_kv)}")
        
        # Estrutura pode ter wrapper 'data' ou ser direta
        # FIX: KV pode retornar data.data.sites (aninhamento duplo)
        if 'data' in sites_kv and isinstance(sites_kv['data'], dict) and 'data' in sites_kv['data']:
             sites = sites_kv['data']['data'].get('sites', [])
             logger.info(f"[ENRICH-SITES] Sites encontrados em 'data.data.sites': {len(sites)}")
        elif 'data' in sites_kv:
            sites = sites_kv.get('data', {}).get('sites', [])
            logger.info(f"[ENRICH-SITES] Sites encontrados em 'data.sites': {len(sites)}")
        else:
            sites = sites_kv.get('sites', [])
            logger.info(f"[ENRICH-SITES] Sites encontrados em 'sites': {len(sites)}")
        
        if not sites:
            logger.warning("[ENRICH-SITES] ❌ Nenhum site encontrado no KV")
            return servers_data
        
        # Criar mapa de sites por prometheus_host/prometheus_instance
        sites_map = {}
        for site in sites:
            host = site.get('prometheus_host') or site.get('prometheus_instance')
            if host:
                sites_map[host] = site
                logger.debug(f"[ENRICH-SITES] Mapeado: {host} -> {site.get('code')}")
        
        logger.info(f"[ENRICH-SITES] ✅ {len(sites_map)} sites mapeados para enriquecimento")
        
        # Enriquecer cada servidor
        enriched_servers = {}
        for server_host, server_info in servers_data.items():
            enriched_server = server_info.copy()
            
            # Buscar site correspondente
            site_data = sites_map.get(server_host)
            
            if site_data:
                # Adicionar dados do site ao servidor
                enriched_server['site'] = {
                    'code': site_data.get('code'),
                    'name': site_data.get('name'),
                    'color': site_data.get('color'),
                    'is_default': site_data.get('is_default', False),
                    'cluster': site_data.get('cluster'),
                    'datacenter': site_data.get('datacenter'),
                    'environment': site_data.get('environment'),
                    'site': site_data.get('site'),
                    'prometheus_port': site_data.get('prometheus_port'),
                    'ssh_port': site_data.get('ssh_port', 22)
                }
                logger.info(f"[ENRICH-SITES] ✅ Servidor {server_host} enriquecido com site {site_data.get('code')}")
            else:
                logger.warning(f"[ENRICH-SITES] ⚠️  Nenhum site encontrado para servidor {server_host} (hosts disponíveis: {list(sites_map.keys())})")
                enriched_server['site'] = None
            
            enriched_servers[server_host] = enriched_server
        
        return enriched_servers
        
    except Exception as e:
        logger.error(f"[ENRICH-SITES] Erro ao enriquecer servidores com dados de sites: {e}", exc_info=True)
        # Retornar dados originais em caso de erro
        return servers_data


async def extract_types_from_prometheus_jobs(
    scrape_configs: List[Dict],
    server_host: str
) -> List[Dict]:
    """
    Extrai tipos de monitoramento dos jobs do Prometheus

    ✅ SPEC-ARCH-001: Usa CategorizationRuleEngine para categorizar
    ao invés de código hardcoded. As regras do KV são a FONTE ÚNICA DA VERDADE.

    Cada job vira um tipo de monitoramento.

    Args:
        scrape_configs: Lista de jobs do prometheus.yml
        server_host: Hostname do servidor (para debug)

    Returns:
        Lista de tipos com schema simplificado
    """
    types = []

    # ✅ SPEC-ARCH-001: Carregar regras do KV (engine faz cache)
    await rule_engine.load_rules()

    for job in scrape_configs:
        job_name = job.get('job_name', 'unknown')

        # Pular job 'prometheus' (self-monitoring)
        if job_name == 'prometheus':
            continue

        # Verificar se tem consul_sd_configs (serviços dinâmicos)
        if not job.get('consul_sd_configs'):
            logger.debug(f"[EXTRACT-TYPES] Job '{job_name}' sem consul_sd_configs, pulando")
            continue

        # Extrair relabel_configs para identificar campos
        relabel_configs = job.get('relabel_configs', [])
        fields = []

        for relabel in relabel_configs:
            if not isinstance(relabel, dict):
                continue
            target_label = relabel.get('target_label')
            if target_label and target_label != '__address__' and not target_label.startswith('__'):
                fields.append(target_label)

        # ✅ SPEC-ARCH-001: Usar engine dinâmico para categorização
        # Extrair módulo blackbox para enviar ao engine
        module = _extract_blackbox_module(job)

        # Montar dados do job para o engine
        job_data = {
            'job_name': job_name,
            'metrics_path': job.get('metrics_path', '/metrics'),
            'module': module,
            'relabel_configs': relabel_configs
        }

        # Categorizar usando regras dinâmicas do KV
        category, type_info = rule_engine.categorize(job_data)

        type_schema = {
            "id": job_name,
            "display_name": type_info.get('display_name', job_name),
            "category": category,
            "job_name": job_name,
            "exporter_type": type_info.get('exporter_type', 'custom'),
            "module": type_info.get('module'),
            "fields": fields,
            "metrics_path": job.get('metrics_path', '/metrics'),
            "server": server_host,
            "job_config": job,  # ✅ NOVO: Salvar job completo do prometheus.yml
        }

        types.append(type_schema)

        logger.info(
            f"[EXTRACT-TYPES] Extraído tipo '{job_name}' (categoria={category}, exporter={type_info['exporter_type']}, campos={len(fields)})"
        )

    return types


def _infer_category_and_type(job_name: str, job_config: Dict) -> tuple:
    """
    Infere categoria e tipo baseado no job_name

    Regras de inferência:
    - blackbox-* → network-probes ou web-probes
    - node-* ou *selfnode* → system-exporters (node)
    - windows-* → system-exporters (windows)
    - mysql-* → database-exporters (mysql)
    - etc
    """
    job_lower = job_name.lower()
    metrics_path = job_config.get('metrics_path', '/metrics')

    # Blackbox Exporter - detecta por:
    # 1. Palavra 'blackbox' no job_name
    # 2. metrics_path = '/probe' (característico do blackbox)
    # 3. Job name corresponde a módulos conhecidos (http_2xx, icmp, etc.)
    is_blackbox = (
        'blackbox' in job_lower or
        metrics_path == '/probe' or
        job_lower in ['http_2xx', 'http_4xx', 'http_5xx', 'https', 'http_post_2xx',
                      'icmp', 'ping', 'tcp', 'tcp_connect', 'dns', 'ssh', 'ssh_banner']
    )

    if is_blackbox:
        # Tentar extrair módulo do config
        module = _extract_blackbox_module(job_config)

        # Se não encontrou, inferir do job_name
        if not module:
            module = job_lower

        # Categorizar como network ou web probe
        if module in ['icmp', 'ping', 'tcp', 'tcp_connect', 'dns', 'ssh', 'ssh_banner']:
            return 'network-probes', {
                'display_name': _format_display_name(module),
                'exporter_type': 'blackbox',
                'module': module
            }
        else:
            return 'web-probes', {
                'display_name': _format_display_name(module),
                'exporter_type': 'blackbox',
                'module': module
            }

    # Node Exporter
    if 'node' in job_lower or 'selfnode' in job_lower:
        return 'system-exporters', {
            'display_name': 'Node Exporter (Linux)',
            'exporter_type': 'node_exporter'
        }

    # Windows Exporter
    if 'windows' in job_lower:
        return 'system-exporters', {
            'display_name': 'Windows Exporter',
            'exporter_type': 'windows_exporter'
        }

    # SNMP Exporter
    if 'snmp' in job_lower:
        return 'system-exporters', {
            'display_name': 'SNMP Exporter',
            'exporter_type': 'snmp_exporter'
        }

    # MySQL
    if 'mysql' in job_lower:
        return 'database-exporters', {
            'display_name': 'MySQL Exporter',
            'exporter_type': 'mysql_exporter'
        }

    # PostgreSQL
    if 'postgres' in job_lower or 'pg' in job_lower:
        return 'database-exporters', {
            'display_name': 'PostgreSQL Exporter',
            'exporter_type': 'postgres_exporter'
        }

    # Redis
    if 'redis' in job_lower:
        return 'database-exporters', {
            'display_name': 'Redis Exporter',
            'exporter_type': 'redis_exporter'
        }

    # MongoDB
    if 'mongo' in job_lower:
        return 'database-exporters', {
            'display_name': 'MongoDB Exporter',
            'exporter_type': 'mongodb_exporter'
        }

    # MKTXP (MikroTik Exporter) - detecta por job_name
    if 'mktxp' in job_lower or 'mikrotik' in job_lower:
        return 'network-devices', {
            'display_name': 'MikroTik Exporter (MKTXP)',
            'exporter_type': 'mktxp'
        }

    # Exporters conhecidos - baseado na lista oficial Prometheus + terceiros populares
    # Formato: pattern: (categoria, display_name, exporter_type)
    exporter_patterns = {
        # Web Servers (Infrastructure)
        'haproxy': ('infrastructure-exporters', 'HAProxy Exporter', 'haproxy_exporter'),
        'nginx': ('infrastructure-exporters', 'Nginx Exporter', 'nginx_exporter'),
        'apache': ('infrastructure-exporters', 'Apache Exporter', 'apache_exporter'),

        # Message Queues (Infrastructure)
        'kafka': ('infrastructure-exporters', 'Kafka Exporter', 'kafka_exporter'),
        'rabbitmq': ('infrastructure-exporters', 'RabbitMQ Exporter', 'rabbitmq_exporter'),
        'nats': ('infrastructure-exporters', 'NATS Exporter', 'nats_exporter'),

        # Databases (Database-Exporters)
        'elasticsearch': ('database-exporters', 'Elasticsearch Exporter', 'elasticsearch_exporter'),
        'memcached': ('database-exporters', 'Memcached Exporter', 'memcached_exporter'),

        # Service Discovery / Orchestration (Infrastructure)
        'consul_exporter': ('infrastructure-exporters', 'Consul Exporter', 'consul_exporter'),
        'consul': ('infrastructure-exporters', 'Consul Exporter', 'consul_exporter'),

        # Other Monitoring Systems (Infrastructure)
        'jmx': ('infrastructure-exporters', 'JMX Exporter', 'jmx_exporter'),
        'collectd': ('infrastructure-exporters', 'Collectd Exporter', 'collectd_exporter'),
        'statsd': ('infrastructure-exporters', 'StatsD Exporter', 'statsd_exporter'),
        'graphite': ('infrastructure-exporters', 'Graphite Exporter', 'graphite_exporter'),
        'influxdb': ('infrastructure-exporters', 'InfluxDB Exporter', 'influxdb_exporter'),

        # Cloud Providers (Infrastructure)
        'cloudwatch': ('infrastructure-exporters', 'AWS CloudWatch Exporter', 'cloudwatch_exporter'),

        # Hardware (Hardware-Exporters)
        'ipmi': ('hardware-exporters', 'IPMI Exporter', 'ipmi_exporter'),
        'dellhw': ('hardware-exporters', 'Dell Hardware OMSA Exporter', 'dellhw_exporter'),

        # APIs & Development Tools (Infrastructure)
        'github': ('infrastructure-exporters', 'GitHub Exporter', 'github_exporter'),
        'gitlab': ('infrastructure-exporters', 'GitLab Exporter', 'gitlab_exporter'),
        'jenkins': ('infrastructure-exporters', 'Jenkins Exporter', 'jenkins_exporter'),
    }

    for pattern, (category, display, exporter_type) in exporter_patterns.items():
        if pattern in job_lower:
            return category, {
                'display_name': display,
                'exporter_type': exporter_type
            }

    # Default: custom exporter
    return 'custom-exporters', {
        'display_name': job_name.replace('-', ' ').replace('_', ' ').title(),
        'exporter_type': 'custom'
    }


def _extract_blackbox_module(job_config: Dict) -> Optional[str]:
    """Extrai módulo blackbox do params ou relabel_configs"""

    # Método 1: params.module
    params = job_config.get('params', {})
    if 'module' in params:
        modules = params['module']
        if isinstance(modules, list) and modules:
            return modules[0]
        return str(modules)

    # Método 2: relabel_configs com __param_module
    for relabel in job_config.get('relabel_configs', []):
        if not isinstance(relabel, dict):
            continue
        if relabel.get('target_label') == '__param_module':
            replacement = relabel.get('replacement')
            if replacement:
                return replacement

    return None


def _format_display_name(name: str) -> str:
    """Formata nome para display"""
    mapping = {
        'icmp': 'ICMP (Ping)',
        'ping': 'ICMP (Ping)',
        'tcp': 'TCP Connect',
        'tcp_connect': 'TCP Connect',
        'dns': 'DNS Query',
        'ssh': 'SSH Banner',
        'ssh_banner': 'SSH Banner',
        'http_2xx': 'HTTP 2xx',
        'http_4xx': 'HTTP 4xx',
        'http_5xx': 'HTTP 5xx',
        'https': 'HTTPS',
        'http_post_2xx': 'HTTP POST 2xx',
    }

    return mapping.get(name.lower(), name.replace('-', ' ').replace('_', ' ').title())


def _format_category_display_name(category: str) -> str:
    """Formata nome da categoria"""
    mapping = {
        'network-probes': 'Network Probes (Rede)',
        'web-probes': 'Web Probes (Aplicações)',
        'system-exporters': 'Exporters: Sistemas',
        'database-exporters': 'Exporters: Bancos de Dados',
        'infrastructure-exporters': 'Exporters: Infraestrutura',
        'hardware-exporters': 'Exporters: Hardware',
        'network-devices': 'Dispositivos de Rede',
        'custom-exporters': 'Exporters: Customizados',
    }
    return mapping.get(category, category.replace('-', ' ').title())


async def _extract_types_from_all_servers(server: Optional[str] = None) -> Dict[str, Any]:
    """
    Função helper para extrair tipos de monitoramento de todos os servidores
    
    Esta função é reutilizada tanto pelo endpoint quanto pelo prewarm.
    
    Args:
        server: Hostname do servidor específico (None para todos)
    
    Returns:
        Dict com estrutura:
        {
            "servers": {...},
            "all_types": [...],
            "categories": {...},
            "total_types": int,
            "total_servers": int,
            "server_status": [...]
        }
    """
    result_servers = {}
    all_types_dict = {}  # Usar dict para deduplicar por id
    server_status = []  # Status de cada servidor (para modal)
    
    # Iterar por hosts configurados
    for host in multi_config.hosts:
        server_host = host.hostname
        
        # Filtrar por servidor se especificado
        if server and server != 'ALL' and server != server_host:
            continue
        
        start_time = datetime.now()
        try:
            logger.info(f"[EXTRACT-TYPES] Processando servidor {server_host}...")
            
            # Buscar arquivo prometheus.yml
            prom_files = multi_config.list_config_files(service='prometheus', hostname=server_host)
            
            if not prom_files:
                logger.warning(f"[EXTRACT-TYPES] Nenhum prometheus.yml encontrado em {server_host}")
                duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)
                result_servers[server_host] = {
                    "error": "prometheus.yml não encontrado",
                    "types": [],
                    "total": 0
                }
                server_status.append({
                    "hostname": server_host,
                    "success": False,
                    "from_cache": False,
                    "files_count": 0,
                    "fields_count": 0,
                    "error": "prometheus.yml não encontrado",
                    "duration_ms": duration_ms
                })
                continue
            
            # Usar o primeiro arquivo encontrado
            prom_file = prom_files[0]
            
            # Ler conteúdo do arquivo
            config = multi_config.read_config_file(prom_file)
            
            # Extrair tipos dos jobs
            scrape_configs = config.get('scrape_configs', [])
            types = await extract_types_from_prometheus_jobs(scrape_configs, server_host)
            
            duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            
            result_servers[server_host] = {
                "types": types,
                "total": len(types),
                "prometheus_file": prom_file.path
            }
            
            # Contar campos únicos (fields de todos os tipos)
            all_fields = set()
            for type_def in types:
                all_fields.update(type_def.get('fields', []))
            
            server_status.append({
                "hostname": server_host,
                "success": True,
                "from_cache": False,
                "files_count": 1,  # 1 arquivo prometheus.yml
                "fields_count": len(all_fields),
                "error": None,
                "duration_ms": duration_ms
            })
            
            logger.info(f"[EXTRACT-TYPES] Servidor {server_host}: {len(types)} tipos extraídos em {duration_ms}ms")
            
            # Adicionar ao all_types (deduplicar por id)
            # ✅ CORREÇÃO: Manter 'fields' no dict para retornar ao frontend!
            # Fields serão removidos apenas ao salvar no KV (mais abaixo)
            for type_def in types:
                type_id = type_def['id']
                
                if type_id not in all_types_dict:
                    # Primeira vez que vemos este tipo - MANTER COM FIELDS!
                    all_types_dict[type_id] = type_def.copy()
                else:
                    # Tipo já existe, adicionar à lista de servidores
                    existing = all_types_dict[type_id]
                    if 'servers' not in existing:
                        # Converter single server para array
                        existing['servers'] = [existing.pop('server')]
                    if server_host not in existing['servers']:
                        existing['servers'].append(server_host)
        
        except Exception as e:
            duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            logger.error(f"[EXTRACT-TYPES] Erro ao extrair tipos de {server_host}: {e}", exc_info=True)
            result_servers[server_host] = {
                "error": str(e),
                "types": [],
                "total": 0
            }
            server_status.append({
                "hostname": server_host,
                "success": False,
                "from_cache": False,
                "files_count": 0,
                "fields_count": 0,
                "error": str(e),
                "duration_ms": duration_ms
            })
    
    # Agrupar por categoria
    categories = {}
    for type_def in all_types_dict.values():
        category = type_def['category']
        if category not in categories:
            categories[category] = {
                "category": category,
                "display_name": _format_category_display_name(category),
                "types": []
            }
        categories[category]['types'].append(type_def)
    
    # Ordenar tipos dentro de cada categoria
    for category_data in categories.values():
        category_data['types'].sort(key=lambda x: x['display_name'])
    
    successful_servers = len([s for s in result_servers.values() if 'error' not in s])
    total_servers = len(result_servers)
    
    logger.info(
        f"[EXTRACT-TYPES] Extração concluída: "
        f"{len(categories)} categorias, {len(all_types_dict)} tipos únicos, "
        f"{successful_servers}/{total_servers} servidores OK"
    )
    
    return {
        "servers": result_servers,
        "all_types": list(all_types_dict.values()),
        "categories": list(categories.values()),
        "total_types": len(all_types_dict),
        "total_servers": total_servers,
        "successful_servers": successful_servers,
        "server_status": server_status
    }


@router.get("/from-prometheus")
async def get_types_from_prometheus(
    server: Optional[str] = Query(None, description="Server hostname (ALL para todos)"),
    force_refresh: bool = Query(False, description="Forçar re-extração via SSH (ignora cache KV)")
):
    """
    Extrai tipos de monitoramento DINAMICAMENTE dos prometheus.yml com cache KV

    Este endpoint SUBSTITUI /api/v1/monitoring-types!
    
    FLUXO (igual metadata-fields):
    1. Se force_refresh=False: Buscar do KV primeiro (skills/eye/monitoring-types)
    2. Se KV vazio OU force_refresh=True: Extrair do Prometheus + salvar no KV
    3. Retornar dados do KV (rápido) ou recém-extraídos
    
    ⚠️ DIFERENÇA vs metadata-fields:
    - Não precisa backup/restore (é só cópia do prometheus.yml)
    - Se não tem no Prometheus, não tem no KV (simples)
    - Menos resiliente (não é editável via frontend)

    Args:
        server: Hostname do servidor ou 'ALL' para todos
        force_refresh: Forçar re-extração via SSH (ignora cache KV)

    Returns:
        {
            "success": true,
            "from_cache": true/false,
            "servers": {...},
            "categories": [...],
            "all_types": [...],
            "total_types": int,
            "total_servers": int,
            "successful_servers": int,
            "server_status": [...],
            "last_updated": "ISO8601"
        }

    Example:
        GET /api/v1/monitoring-types-dynamic/from-prometheus?server=ALL
        GET /api/v1/monitoring-types-dynamic/from-prometheus?server=172.16.1.26&force_refresh=true
    """
    try:
        # PASSO 1: Tentar ler do KV primeiro (se não forçar refresh)
        if not force_refresh:
            kv_data = await kv_manager.get_json('skills/eye/monitoring-types')
            if kv_data and kv_data.get('all_types'):
                logger.info(f"[MONITORING-TYPES] ✅ KV encontrado com {len(kv_data['all_types'])} tipos")
                
                # ✅ CORREÇÃO: Filtrar por servidor se especificado (igual versão 16/11)
                if server and server != 'ALL':
                    logger.info(f"[MONITORING-TYPES] Filtrando tipos para servidor: {server}")
                    
                    # Filtrar tipos que pertencem ao servidor especificado
                    filtered_types = []
                    for type_def in kv_data.get('all_types', []):
                        # Verificar se tipo pertence ao servidor (campo 'server' ou 'servers')
                        if type_def.get('server') == server or server in type_def.get('servers', []):
                            filtered_types.append(type_def)
                    
                    # Reagrupar por categoria com tipos filtrados
                    filtered_categories = {}
                    for type_def in filtered_types:
                        category = type_def['category']
                        if category not in filtered_categories:
                            filtered_categories[category] = {
                                "category": category,
                                "display_name": _format_category_display_name(category),
                                "types": []
                            }
                        filtered_categories[category]['types'].append(type_def)
                    
                    # Filtrar servidor específico
                    filtered_servers = {server: kv_data['servers'].get(server, {})} if server in kv_data.get('servers', {}) else {}
                    
                    logger.info(f"[MONITORING-TYPES] ✅ Filtrado: {len(filtered_types)} tipos para servidor {server}")
                    
                    return {
                        "success": True,
                        "from_cache": True,
                        "categories": list(filtered_categories.values()),
                        "all_types": filtered_types,
                        "servers": filtered_servers,
                        "total_types": len(filtered_types),
                        "total_servers": 1,
                        "successful_servers": 1 if server in kv_data.get('servers', {}) else 0,
                        "server_status": [s for s in kv_data.get('server_status', []) if s.get('hostname') == server],
                        "last_updated": kv_data.get('last_updated')
                    }
                else:
                    # Retornar todos os dados do cache
                    logger.info(f"[MONITORING-TYPES] ✅ Retornando todos os {len(kv_data['all_types'])} tipos do KV (cache)")
                    return {
                        "success": True,
                        "from_cache": True,
                        "categories": kv_data.get('categories', []),
                        "all_types": kv_data.get('all_types', []),
                        "servers": kv_data.get('servers', {}),
                        "total_types": kv_data.get('total_types', 0),
                        "total_servers": kv_data.get('total_servers', 0),
                        "successful_servers": kv_data.get('successful_servers', 0),
                        "server_status": kv_data.get('server_status', []),
                        "last_updated": kv_data.get('last_updated')
                    }
        
        # PASSO 2: KV vazio ou force_refresh: Extrair do Prometheus
        logger.info(f"[MONITORING-TYPES] 🔄 Extraindo tipos do Prometheus via SSH (force_refresh={force_refresh})...")

        # Limpar cache interno do multi_config se forçar refresh
        if force_refresh:
            multi_config.clear_cache(close_connections=True)

        # Extrair tipos usando função helper
        result = await _extract_types_from_all_servers(server=server)
        logger.info(f"[MONITORING-TYPES] ✅ Extração concluída: {result['total_types']} tipos de {result['successful_servers']}/{result['total_servers']} servidores")

        # PASSO 3: Enriquecer servidores com dados de sites do KV
        logger.info("[MONITORING-TYPES] 🔄 Enriquecendo servidores com dados de sites...")
        logger.info(f"[MONITORING-TYPES] Servidores antes do enriquecimento: {list(result['servers'].keys())}")
        enriched_servers = await _enrich_servers_with_sites_data(result['servers'])
        logger.info(f"[MONITORING-TYPES] ✅ Enriquecimento concluído. Servidores enriquecidos: {list(enriched_servers.keys())}")

        # PASSO 3.5: ✅ MERGE de form_schema (preservar customizações manuais)
        # Buscar KV existente para preservar form_schema customizados
        existing_kv = await kv_manager.get_json('skills/eye/monitoring-types')
        existing_form_schemas = {}
        if existing_kv:
            # Buscar form_schema de servers (específico por servidor) - PRIORIDADE
            if existing_kv.get('servers'):
                for server_host, server_data in existing_kv['servers'].items():
                    if 'types' in server_data:
                        for type_def in server_data.get('types', []):
                            if type_def.get('form_schema'):
                                type_id = type_def['id']
                                # Usar chave composta: type_id + servidor
                                key = f"{type_id}::{server_host}"
                                existing_form_schemas[key] = type_def['form_schema']
                                logger.debug(f"[MONITORING-TYPES] Preservando form_schema: {key}")
            
            # Buscar form_schema de all_types (fallback)
            if existing_kv.get('all_types'):
                for existing_type in existing_kv['all_types']:
                    if existing_type.get('form_schema'):
                        type_id = existing_type['id']
                        # Se não tem form_schema específico por servidor, usar o global
                        has_server_specific = any(k.startswith(f"{type_id}::") for k in existing_form_schemas.keys())
                        if not has_server_specific:
                            existing_form_schemas[type_id] = existing_type['form_schema']
                            logger.debug(f"[MONITORING-TYPES] Preservando form_schema global: {type_id}")

        if existing_form_schemas:
            logger.info(f"[MONITORING-TYPES] 🔄 Preservando {len(existing_form_schemas)} form_schema customizados...")

        # Aplicar merge em servers (usar form_schema específico do servidor)
        for server_host, server_data in enriched_servers.items():
            if 'types' in server_data:
                for type_def in server_data['types']:
                    type_id = type_def['id']
                    # Tentar chave específica por servidor primeiro
                    server_key = f"{type_id}::{server_host}"
                    if server_key in existing_form_schemas:
                        type_def['form_schema'] = existing_form_schemas[server_key]
                    elif type_id in existing_form_schemas:
                        # Fallback: usar form_schema global
                        type_def['form_schema'] = existing_form_schemas[type_id]

        # Aplicar merge em all_types (priorizar global > primeiro servidor)
        for type_def in result['all_types']:
            type_id = type_def['id']
            if type_id in existing_form_schemas:
                # Encontrou schema global (exato)
                type_def['form_schema'] = existing_form_schemas[type_id]
            else:
                # Fallback: primeiro específico encontrado
                for key, schema in existing_form_schemas.items():
                    if key.startswith(f"{type_id}::"):
                        type_def['form_schema'] = schema
                        break

        # Aplicar merge em categories (priorizar global > primeiro servidor)
        for category in result['categories']:
            for type_def in category.get('types', []):
                type_id = type_def['id']
                if type_id in existing_form_schemas:
                    type_def['form_schema'] = existing_form_schemas[type_id]
                else:
                    # Fallback: primeiro específico encontrado
                    for key, schema in existing_form_schemas.items():
                        if key.startswith(f"{type_id}::"):
                            type_def['form_schema'] = schema
                            break

        # PASSO 4: Salvar no KV SEM 'fields' (fields são obtidos via SSH, não salvos no KV)
        # ⚠️ CRÍTICO: 'fields' é apenas para display no frontend, não deve ser persistido no KV
        # A fonte de verdade para campos metadata é metadata-fields KV

        # Limpar 'fields' de all_types para salvar no KV
        all_types_for_kv = []
        for type_def in result['all_types']:
            type_clean = {k: v for k, v in type_def.items() if k != 'fields'}
            all_types_for_kv.append(type_clean)

        # Limpar 'fields' de servers para salvar no KV
        servers_for_kv = {}
        for server_host, server_data in enriched_servers.items():
            if 'types' in server_data:
                types_clean = [{k: v for k, v in t.items() if k != 'fields'} for t in server_data['types']]
                servers_for_kv[server_host] = {**server_data, 'types': types_clean}
            else:
                servers_for_kv[server_host] = server_data

        # Limpar 'fields' de categories para salvar no KV
        categories_for_kv = []
        for category in result['categories']:
            types_clean = [{k: v for k, v in t.items() if k != 'fields'} for t in category.get('types', [])]
            categories_for_kv.append({**category, 'types': types_clean})

        kv_value = {
            'version': '1.0.0',
            'last_updated': datetime.now().isoformat(),
            'source': 'force_refresh' if force_refresh else 'fallback_empty_kv',
            'total_types': result['total_types'],
            'total_servers': result['total_servers'],
            'successful_servers': result['successful_servers'],
            'servers': servers_for_kv,           # ❌ SEM fields (para KV)
            'all_types': all_types_for_kv,       # ❌ SEM fields (para KV)
            'categories': categories_for_kv,     # ❌ SEM fields (para KV)
            'server_status': result['server_status']
        }

        # PASSO 4.5: ✅ CRIAR BACKUP antes de salvar (preservar form_schemas customizados)
        logger.info("[MONITORING-TYPES] Criando backup antes de salvar...")
        backup_success = await backup_manager.create_backup(kv_value)
        if backup_success:
            logger.info("[MONITORING-TYPES] ✅ Backup criado com sucesso")
        else:
            logger.warning("[MONITORING-TYPES] ⚠️ Falha ao criar backup (continuando salvamento)")

        await kv_manager.put_json(
            key='skills/eye/monitoring-types',
            value=kv_value,
            metadata={'auto_updated': True, 'source': 'force_refresh' if force_refresh else 'fallback_empty_kv'}
        )
        
        logger.info(f"[MONITORING-TYPES] ✅ Tipos salvos no KV: {result['total_types']} tipos de {result['successful_servers']}/{result['total_servers']} servidores")
        
        return {
            "success": True,
            "from_cache": False,
            "categories": result['categories'],  # ✅ COM fields para frontend!
            "all_types": result['all_types'],    # ✅ COM fields para frontend!
            "servers": enriched_servers,         # ✅ COM fields para frontend!
            "total_types": result['total_types'],
            "total_servers": result['total_servers'],
            "successful_servers": result['successful_servers'],
            "server_status": result['server_status'],
            "last_updated": kv_value['last_updated']
        }

    except Exception as e:
        logger.error(f"[MONITORING-TYPES-DYNAMIC] Erro ao extrair tipos do Prometheus: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/type/{type_id}/form-schema")
async def update_type_form_schema(
    type_id: str,
    request: FormSchemaUpdateRequest
):
    """
    ✅ SOLUÇÃO PRAGMÁTICA: Atualiza form_schema de um tipo específico

    Salva form_schema diretamente no KV skills/eye/monitoring-types.
    Cada tipo tem seu próprio form_schema (sem duplicação, sem ambiguidade).

    Args:
        type_id: ID do tipo (ex: 'icmp', 'http_2xx', 'node_exporter')
        request: FormSchemaUpdateRequest com form_schema

    Returns:
        {"success": true, "message": "...", "type_id": "..."}

    Example:
        PUT /api/v1/monitoring-types-dynamic/type/icmp/form-schema
        Body: {
            "form_schema": {
                "fields": [
                    {"name": "target", "type": "text", "required": true, ...}
                ],
                "required_metadata": ["target", "module"],
                "optional_metadata": []
            }
        }
    """
    try:
        logger.info(f"[UPDATE-FORM-SCHEMA] Atualizando form_schema para tipo: {type_id}, servidor: {request.server}")

        # PASSO 1: Buscar KV atual
        kv_data = await kv_manager.get_json('skills/eye/monitoring-types')
        
        if not kv_data or not kv_data.get('all_types'):
            raise HTTPException(
                status_code=404,
                detail="KV monitoring-types não encontrado. Execute force_refresh=true primeiro."
            )

        target_server = request.server
        servers_updated = 0

        # PASSO 2: Atualizar form_schema
        if target_server and target_server != 'ALL':
            # Servidor específico: atualizar apenas nele
            if target_server not in kv_data.get('servers', {}):
                raise HTTPException(
                    status_code=404,
                    detail=f"Servidor '{target_server}' não encontrado."
                )
            
            server_data = kv_data['servers'][target_server]
            type_found = False
            for type_def in server_data.get('types', []):
                if type_def.get('id') == type_id:
                    type_def['form_schema'] = request.form_schema
                    type_found = True
                    servers_updated = 1
                    logger.info(f"[UPDATE-FORM-SCHEMA] ✅ Tipo '{type_id}' atualizado no servidor '{target_server}'")
                    break
            
            if not type_found:
                raise HTTPException(
                    status_code=404,
                    detail=f"Tipo '{type_id}' não encontrado no servidor '{target_server}'."
                )
        else:
            # Sem servidor específico: atualizar em todos os servidores que têm este tipo
            for server_host, server_data in kv_data.get('servers', {}).items():
                for type_def in server_data.get('types', []):
                    if type_def.get('id') == type_id:
                        type_def['form_schema'] = request.form_schema
                        servers_updated += 1
                        logger.info(f"[UPDATE-FORM-SCHEMA] ✅ Tipo '{type_id}' atualizado no servidor '{server_host}'")
            
            # ✅ ATUALIZAR GLOBAIS (all_types/categories) para refletir mudança imediatamente
            if kv_data.get('all_types'):
                for type_def in kv_data['all_types']:
                    if type_def.get('id') == type_id:
                        type_def['form_schema'] = request.form_schema
            
            if kv_data.get('categories'):
                for category in kv_data['categories']:
                    if 'types' in category:
                        for type_def in category['types']:
                            if type_def.get('id') == type_id:
                                type_def['form_schema'] = request.form_schema

        # PASSO 3: Atualizar metadata
        kv_data['last_updated'] = datetime.now().isoformat()

        # PASSO 4: Criar backup
        backup_success = await backup_manager.create_backup(kv_data)
        if backup_success:
            logger.info(f"[UPDATE-FORM-SCHEMA] ✅ Backup criado")
        else:
            logger.warning(f"[UPDATE-FORM-SCHEMA] ⚠️ Falha ao criar backup (continuando)")

        # PASSO 5: Salvar no KV
        success = await kv_manager.put_json(
            key='skills/eye/monitoring-types',
            value=kv_data,
            metadata={
                'auto_updated': False,
                'source': 'form_schema_update',
                'updated_by': 'user',
                'type_id': type_id,
                'server': target_server if target_server and target_server != 'ALL' else 'all'
            }
        )

        if not success:
            raise HTTPException(status_code=500, detail="Erro ao salvar no KV Consul")
        
        logger.info(f"[UPDATE-FORM-SCHEMA] ✅ Form schema salvo no KV para tipo '{type_id}' (servidores atualizados: {servers_updated})")

        return {
            "success": True,
            "message": f"Form schema atualizado para tipo '{type_id}'" + (f" no servidor '{target_server}'" if target_server and target_server != 'ALL' else " em todos os servidores"),
            "type_id": type_id,
            "server": target_server,
            "servers_updated": servers_updated,
            "last_updated": kv_data['last_updated']
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[UPDATE-FORM-SCHEMA] Erro ao atualizar form_schema: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        return {
            "success": True,
            "status": "healthy",
            "servers_configured": len(multi_config.hosts),
            "message": "Monitoring Types Dynamic API is operational"
        }

    except Exception as e:
        return {
            "success": False,
            "status": "unhealthy",
            "error": str(e)
        }
