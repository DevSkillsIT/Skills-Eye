"""
API para Monitoring Types DINÂMICOS extraídos de Prometheus.yml

Este endpoint SUBSTITUI os JSONs estáticos!
Extrai tipos de monitoramento diretamente dos jobs do prometheus.yml de cada servidor.

FONTE DA VERDADE: prometheus.yml (não JSONs)
"""

from fastapi import APIRouter, HTTPException, Query
from typing import List, Dict, Any, Optional
import logging

from core.multi_config_manager import MultiConfigManager

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/monitoring-types-dynamic", tags=["Monitoring Types"])

# Instanciar manager
multi_config = MultiConfigManager()


async def extract_types_from_prometheus_jobs(
    scrape_configs: List[Dict],
    server_host: str
) -> List[Dict]:
    """
    Extrai tipos de monitoramento dos jobs do Prometheus

    Cada job vira um tipo de monitoramento.

    Args:
        scrape_configs: Lista de jobs do prometheus.yml
        server_host: Hostname do servidor (para debug)

    Returns:
        Lista de tipos com schema simplificado
    """
    types = []

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

        # Determinar categoria e tipo baseado no job_name
        category, type_info = _infer_category_and_type(job_name, job)

        type_schema = {
            "id": job_name,
            "display_name": type_info['display_name'],
            "category": category,
            "job_name": job_name,
            "exporter_type": type_info['exporter_type'],
            "module": type_info.get('module'),
            "fields": fields,
            "metrics_path": job.get('metrics_path', '/metrics'),
            "server": server_host,
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


@router.get("/from-prometheus")
async def get_types_from_prometheus(
    server: Optional[str] = Query(None, description="Server hostname (ALL para todos)")
):
    """
    Extrai tipos de monitoramento DINAMICAMENTE dos prometheus.yml

    Este endpoint SUBSTITUI /api/v1/monitoring-types!

    Args:
        server: Hostname do servidor ou 'ALL' para todos

    Returns:
        {
            "success": true,
            "servers": {
                "172.16.1.26": {
                    "types": [...]
                },
                "172.16.200.14": {
                    "types": [...]
                }
            },
            "all_types": [...]  // União de todos os tipos (sem duplicatas)
        }

    Example:
        GET /api/v1/monitoring-types-dynamic/from-prometheus?server=ALL
        GET /api/v1/monitoring-types-dynamic/from-prometheus?server=172.16.1.26
    """
    try:
        logger.info(f"[MONITORING-TYPES-DYNAMIC] Extraindo tipos de monitoramento do Prometheus (server={server or 'ALL'})")

        result_servers = {}
        all_types_dict = {}  # Usar dict para deduplicar por id

        # Iterar por hosts configurados
        for host in multi_config.hosts:
            server_host = host.hostname

            # Filtrar por servidor se especificado
            if server and server != 'ALL' and server != server_host:
                continue

            try:
                logger.info(f"[MONITORING-TYPES-DYNAMIC] Processando servidor {server_host}...")

                # Buscar arquivo prometheus.yml
                prom_files = multi_config.list_config_files(service='prometheus', hostname=server_host)

                if not prom_files:
                    logger.warning(f"[MONITORING-TYPES-DYNAMIC] Nenhum prometheus.yml encontrado em {server_host}")
                    result_servers[server_host] = {
                        "error": "prometheus.yml não encontrado",
                        "types": [],
                        "total": 0
                    }
                    continue

                # Usar o primeiro arquivo encontrado
                prom_file = prom_files[0]

                # Ler conteúdo do arquivo
                config = multi_config.read_config_file(prom_file)

                # Extrair tipos dos jobs
                scrape_configs = config.get('scrape_configs', [])
                types = await extract_types_from_prometheus_jobs(scrape_configs, server_host)

                result_servers[server_host] = {
                    "types": types,
                    "total": len(types),
                    "prometheus_file": prom_file.path
                }

                logger.info(f"[MONITORING-TYPES-DYNAMIC] Servidor {server_host}: {len(types)} tipos extraídos")

                # Adicionar ao all_types (deduplicar por id)
                for type_def in types:
                    type_id = type_def['id']
                    if type_id not in all_types_dict:
                        # Primeira vez que vemos este tipo
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
                logger.error(f"[MONITORING-TYPES-DYNAMIC] Erro ao extrair tipos de {server_host}: {e}", exc_info=True)
                result_servers[server_host] = {
                    "error": str(e),
                    "types": [],
                    "total": 0
                }

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

        logger.info(
            f"[MONITORING-TYPES-DYNAMIC] Extração concluída: "
            f"{len(categories)} categorias, {len(all_types_dict)} tipos únicos"
        )

        return {
            "success": True,
            "servers": result_servers,
            "categories": list(categories.values()),
            "all_types": list(all_types_dict.values()),
            "total_types": len(all_types_dict),
            "total_servers": len([s for s in result_servers.values() if 'error' not in s])
        }

    except Exception as e:
        logger.error(f"[MONITORING-TYPES-DYNAMIC] Erro ao extrair tipos do Prometheus: {e}", exc_info=True)
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
