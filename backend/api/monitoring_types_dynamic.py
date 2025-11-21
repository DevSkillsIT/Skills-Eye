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
        if 'data' in sites_kv:
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
            "module": type_info.get('module') or module,
            "fields": fields,
            "metrics_path": job.get('metrics_path', '/metrics'),
            "server": server_host,
            "job_config": job,  # ✅ NOVO: Salvar job completo do prometheus.yml
        }

        types.append(type_schema)

        logger.info(
            f"[EXTRACT-TYPES] Extraído tipo '{job_name}' (categoria={category}, exporter={type_info.get('exporter_type')}, campos={len(fields)})"
        )

    return types


# ✅ SPEC-ARCH-001: Função _infer_category_and_type REMOVIDA
# Agora usamos CategorizationRuleEngine.categorize() que usa regras do KV
# como FONTE ÚNICA DA VERDADE. Isso permite que novas regras sejam
# adicionadas via /monitoring/rules sem alterar código.


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


# ✅ SPEC-ARCH-001: Funções _format_display_name e _format_category_display_name REMOVIDAS
# Display names agora vêm 100% das regras dinâmicas do KV via CategorizationRuleEngine.
# Isso permite que novos exporters sejam adicionados sem alterar código.

def _format_category_display_name(category: str) -> str:
    """
    Formata nome da categoria para exibição

    ✅ SPEC-ARCH-001: Esta função permanece como fallback para agrupamento
    de categorias na resposta. Futuramente pode buscar do KV categories.
    """
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


async def _process_single_server(
    host,
    multi_config,
    rule_engine
) -> Dict[str, Any]:
    """
    Processa um único servidor e extrai seus tipos de monitoramento

    Args:
        host: Objeto host com hostname
        multi_config: Instância de MultiConfigManager
        rule_engine: Instância de CategorizationRuleEngine

    Returns:
        Dict com estrutura:
        {
            "hostname": str,
            "success": bool,
            "types": List[Dict],
            "total": int,
            "prometheus_file": str | None,
            "error": str | None,
            "duration_ms": int,
            "fields_count": int
        }
    """
    server_host = host.hostname
    start_time = datetime.now()

    try:
        logger.info(f"[EXTRACT-TYPES] Processando servidor {server_host}...")

        # Buscar arquivo prometheus.yml
        prom_files = multi_config.list_config_files(service='prometheus', hostname=server_host)

        if not prom_files:
            duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            logger.warning(f"[EXTRACT-TYPES] Nenhum prometheus.yml encontrado em {server_host}")
            return {
                "hostname": server_host,
                "success": False,
                "types": [],
                "total": 0,
                "prometheus_file": None,
                "error": "prometheus.yml não encontrado",
                "duration_ms": duration_ms,
                "fields_count": 0
            }

        # Usar o primeiro arquivo encontrado
        prom_file = prom_files[0]

        # Ler conteúdo do arquivo
        config = multi_config.read_config_file(prom_file)

        # Extrair tipos dos jobs
        scrape_configs = config.get('scrape_configs', [])
        types = await extract_types_from_prometheus_jobs(scrape_configs, server_host)

        duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)

        # Contar campos únicos
        all_fields = set()
        for type_def in types:
            all_fields.update(type_def.get('fields', []))

        logger.info(f"[EXTRACT-TYPES] Servidor {server_host}: {len(types)} tipos extraídos em {duration_ms}ms")

        return {
            "hostname": server_host,
            "success": True,
            "types": types,
            "total": len(types),
            "prometheus_file": prom_file.path,
            "error": None,
            "duration_ms": duration_ms,
            "fields_count": len(all_fields)
        }

    except Exception as e:
        duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)
        logger.error(f"[EXTRACT-TYPES] Erro ao extrair tipos de {server_host}: {e}", exc_info=True)
        return {
            "hostname": server_host,
            "success": False,
            "types": [],
            "total": 0,
            "prometheus_file": None,
            "error": str(e),
            "duration_ms": duration_ms,
            "fields_count": 0
        }


def _aggregate_types(server_results: List[Dict[str, Any]]) -> Dict[str, Dict]:
    """
    Agrega tipos de todos os servidores, deduplicando por ID

    Args:
        server_results: Lista de resultados de _process_single_server()

    Returns:
        Dict[type_id, type_def] com tipos agregados
    """
    all_types_dict = {}

    for result in server_results:
        if not result['success']:
            continue

        server_host = result['hostname']

        for type_def in result['types']:
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

    return all_types_dict


def _group_by_category(all_types_dict: Dict[str, Dict]) -> List[Dict[str, Any]]:
    """
    Agrupa tipos por categoria para retorno na API

    Args:
        all_types_dict: Dict[type_id, type_def]

    Returns:
        Lista de categorias com seus tipos
    """
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

    return list(categories.values())


async def _extract_types_from_all_servers(server: Optional[str] = None) -> Dict[str, Any]:
    """
    Função helper para extrair tipos de monitoramento de todos os servidores

    Orquestra a extração de tipos através de funções especializadas:
    1. _process_single_server() - processa 1 servidor
    2. _aggregate_types() - deduplica tipos
    3. _group_by_category() - agrupa por categoria

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
            "successful_servers": int,
            "server_status": [...]
        }
    """
    result_servers = {}
    server_status = []
    server_results = []

    # PASSO 1: Processar cada servidor
    for host in multi_config.hosts:
        server_host = host.hostname

        # Filtrar por servidor se especificado
        if server and server != 'ALL' and server != server_host:
            continue

        result = await _process_single_server(host, multi_config, rule_engine)
        server_results.append(result)

        # Montar estrutura de retorno
        if result['success']:
            result_servers[server_host] = {
                "types": result['types'],
                "total": result['total'],
                "prometheus_file": result['prometheus_file']
            }
        else:
            result_servers[server_host] = {
                "error": result['error'],
                "types": [],
                "total": 0
            }

        server_status.append({
            "hostname": server_host,
            "success": result['success'],
            "from_cache": False,
            "files_count": 1 if result['success'] else 0,
            "fields_count": result['fields_count'],
            "error": result['error'],
            "duration_ms": result['duration_ms']
        })

    # PASSO 2: Agregar tipos de todos os servidores
    all_types_dict = _aggregate_types(server_results)

    # PASSO 3: Agrupar por categoria
    categories = _group_by_category(all_types_dict)

    # PASSO 4: Calcular estatísticas
    successful_servers = len([r for r in server_results if r['success']])
    total_servers = len(server_results)

    logger.info(
        f"[EXTRACT-TYPES] Extração concluída: "
        f"{len(categories)} categorias, {len(all_types_dict)} tipos únicos, "
        f"{successful_servers}/{total_servers} servidores OK"
    )

    return {
        "servers": result_servers,
        "all_types": list(all_types_dict.values()),
        "categories": categories,
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
        
        # PASSO 4: Salvar no KV (sobrescrever - não precisa merge como metadata-fields)
        # ✅ CORREÇÃO: Salvar COM fields para que o cache tenha os dados completos!
        kv_value = {
            'version': '1.0.0',
            'last_updated': datetime.now().isoformat(),
            'source': 'force_refresh' if force_refresh else 'fallback_empty_kv',
            'total_types': result['total_types'],
            'total_servers': result['total_servers'],
            'successful_servers': result['successful_servers'],
            'servers': enriched_servers,        # ✅ COM fields!
            'all_types': result['all_types'],   # ✅ COM fields!
            'categories': result['categories'], # ✅ COM fields!
            'server_status': result['server_status']
        }
        
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
        logger.info(f"[UPDATE-FORM-SCHEMA] Atualizando form_schema para tipo: {type_id}")

        # PASSO 1: Buscar KV atual
        kv_data = await kv_manager.get_json('skills/eye/monitoring-types')

        if not kv_data or not kv_data.get('all_types'):
            raise HTTPException(
                status_code=404,
                detail="KV monitoring-types não encontrado. Execute force_refresh=true primeiro."
            )

        # PASSO 2: Encontrar tipo no all_types
        type_found = False
        for type_def in kv_data['all_types']:
            if type_def.get('id') == type_id:
                # ✅ ATUALIZAR form_schema diretamente
                type_def['form_schema'] = request.form_schema
                type_found = True
                logger.info(f"[UPDATE-FORM-SCHEMA] ✅ Tipo '{type_id}' atualizado com form_schema")
                break

        if not type_found:
            raise HTTPException(
                status_code=404,
                detail=f"Tipo '{type_id}' não encontrado. Tipos disponíveis: {[t['id'] for t in kv_data['all_types'][:10]]}"
            )

        # PASSO 3: Atualizar também em servers (para consistência)
        for server_host, server_data in kv_data.get('servers', {}).items():
            for type_def in server_data.get('types', []):
                if type_def.get('id') == type_id:
                    type_def['form_schema'] = request.form_schema

        # PASSO 4: Atualizar metadata
        kv_data['last_updated'] = datetime.now().isoformat()

        # PASSO 4.5: ✅ CRIAR BACKUP antes de salvar (preservar histórico de changes)
        logger.info(f"[UPDATE-FORM-SCHEMA] Criando backup antes de salvar tipo '{type_id}'...")
        backup_success = await backup_manager.create_backup(kv_data)
        if backup_success:
            logger.info(f"[UPDATE-FORM-SCHEMA] ✅ Backup criado para tipo '{type_id}'")
        else:
            logger.warning(f"[UPDATE-FORM-SCHEMA] ⚠️ Falha ao criar backup para '{type_id}' (continuando salvamento)")

        # PASSO 5: Salvar de volta no KV
        success = await kv_manager.put_json(
            key='skills/eye/monitoring-types',
            value=kv_data
        )

        if not success:
            raise HTTPException(
                status_code=500,
                detail="Erro ao salvar no KV Consul"
            )

        logger.info(f"[UPDATE-FORM-SCHEMA] ✅ Form schema salvo no KV para tipo '{type_id}'")

        return {
            "success": True,
            "message": f"Form schema atualizado para tipo '{type_id}'",
            "type_id": type_id,
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
