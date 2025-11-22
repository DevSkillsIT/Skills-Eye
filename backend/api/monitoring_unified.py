"""
API Unificada de Monitoramento - Endpoint Único para Todas as Páginas

RESPONSABILIDADES:
- Endpoint unificado GET /api/v1/monitoring/data (busca do Consul)
- Endpoint unificado GET /api/v1/monitoring/metrics (busca do Prometheus via PromQL)
- Filtra por categoria (network-probes, web-probes, etc)
- Executa queries PromQL dinamicamente
- Retorna dados formatados para ProTable

ARQUITETURA REFATORADA (2025-11-13):
- USA metadata/fields para campos disponíveis (descobertos do prometheus.yml)
- USA metadata/sites para mapear IP → site code
- USA categorization/rules para determinar categoria de serviços
- ELIMINA monitoring-types/cache (redundante)
- REUTILIZA código existente de monitoring_types_dynamic.py

AUTOR: Sistema de Refatoração Skills Eye v2.0
DATA: 2025-11-13
"""

from fastapi import APIRouter, HTTPException, Query, Request
from typing import Optional, List, Dict, Any
from datetime import datetime
import logging
import httpx
import time

from core.consul_kv_config_manager import ConsulKVConfigManager
from core.consul_manager import ConsulManager
from core.categorization_rule_engine import CategorizationRuleEngine
from core.cache_manager import get_cache  # SPRINT 2: Usar LocalCache global
from core.monitoring_cache import get_monitoring_cache  # SPEC-PERF-002: Cache intermediario
from core.monitoring_filters import process_monitoring_data  # SPEC-PERF-002: Filtros server-side

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/monitoring", tags=["Monitoring Unified"])

# Inicializar componentes globais
kv_manager = ConsulKVConfigManager(ttl_seconds=300)  # Cache de 5 minutos
consul_manager = ConsulManager()
categorization_engine = CategorizationRuleEngine(kv_manager)

# SPRINT 2 (2025-11-15): Usar LocalCache global para integracao com Cache Management
# REMOVIDO: _nodes_cache e _services_cache internos
# NOVO: Usar get_cache() para cache centralizado e monitoravel
cache = get_cache(ttl_seconds=60)

# SPEC-PERF-002: Cache intermediario para paginacao server-side
# Necessario porque Consul nao suporta paginacao nativa (Issue #9422)
monitoring_data_cache = get_monitoring_cache(ttl_seconds=30)


async def get_nodes_cached(consul_mgr: ConsulManager) -> List[Dict[str, Any]]:
    """
    Retorna lista de nós do Consul com cache de 5 minutos.
    
    SPRINT 2: Migrado para LocalCache global.
    
    Cache hit: ~0ms
    Cache miss: ~50ms (API call ao Consul)
    """
    cache_key = "monitoring:nodes:all"
    
    # Tentar buscar do cache
    cached = await cache.get(cache_key)
    if cached is not None:
        logger.debug(f"[CACHE HIT] Nodes do Consul (key: {cache_key})")
        return cached
    
    # Cache miss - buscar do Consul
    logger.debug(f"[CACHE MISS] Buscando nodes do Consul...")
    nodes = await consul_mgr.get_nodes()
    
    # Armazenar no cache (TTL: 300s = 5 minutos)
    await cache.set(cache_key, nodes, ttl=300)
    
    return nodes


async def get_services_cached(
    category: str,
    company: Optional[str],
    site: Optional[str],
    env: Optional[str],
    fetch_function  # Função que busca dados quando cache miss
) -> Dict:
    """
    Retorna dados de serviços com cache por categoria e filtros.
    
    SPRINT 2: Migrado para LocalCache global.
    
    Cache hit: ~5ms (apenas validação de filtros)
    Cache miss: ~200ms (busca completa do Consul + categorização)
    
    Cache key: f"monitoring:services:{category}:{company}:{site}:{env}"
    """
    # Gerar cache key baseado em categoria + filtros
    cache_key = f"monitoring:services:{category}:{company or 'all'}:{site or 'all'}:{env or 'all'}"
    
    # Tentar buscar do cache
    cached = await cache.get(cache_key)
    if cached is not None:
        logger.debug(
            f"[CACHE HIT] Services category='{category}' "
            f"(key: {cache_key}, total: {cached.get('total', 0)})"
        )
        return cached
    
    # Cache miss - buscar dados
    logger.debug(f"[CACHE MISS] Buscando services category='{category}'...")
    data = await fetch_function()
    
    # Armazenar no cache (TTL: 30s padrão do LocalCache)
    await cache.set(cache_key, data, ttl=30)
    
    return data


# ============================================================================
# ENDPOINT 1: /monitoring/data - BUSCA DO CONSUL (Serviços)
# ============================================================================

@router.get("/data")
async def get_monitoring_data(
    request: Request,
    category: str = Query(..., description="Categoria: network-probes, web-probes, etc"),
    company: Optional[str] = Query(None, description="Filtrar por empresa"),
    site: Optional[str] = Query(None, description="Filtrar por site"),
    env: Optional[str] = Query(None, description="Filtrar por ambiente"),
    # SPEC-PERF-002: Parametros de paginacao server-side
    page: Optional[int] = Query(None, ge=1, description="Numero da pagina (1-based)"),
    page_size: Optional[int] = Query(None, ge=10, le=200, description="Itens por pagina (10-200)"),
    sort_field: Optional[str] = Query(None, description="Campo para ordenacao"),
    sort_order: Optional[str] = Query(None, description="Direcao: ascend | descend | asc | desc"),
    node: Optional[str] = Query(None, description="Filtrar por IP do no"),
    # SPEC-PERF-002 FIX: Parametro de busca textual
    q: Optional[str] = Query(None, description="Busca textual em todos os campos")
):
    """
    Endpoint para buscar SERVICOS do Consul filtrados por categoria

    SPEC-PERF-002 FASE 1 (2025-11-22):
    - Paginacao server-side (page, page_size)
    - Filtros server-side (node, metadata dinamico)
    - Ordenacao server-side (sort_field, sort_order)
    - filterOptions para dropdowns de filtro
    - Cache intermediario TTL 30s (Consul nao suporta paginacao nativa)

    SPRINT 2 OTIMIZACAO (2025-11-16):
    - Cache COMPLETO do resultado por categoria + filtros (TTL: 30s)
    - Reduz latencia de ~250ms -> <20ms (12.5x mais rapido!)

    FLUXO REFATORADO:
    1. Busca sites do KV (metadata/sites) - mapeia IP -> site code
    2. Busca campos do KV (metadata/fields) - campos disponiveis
    3. Busca regras de categorizacao (categorization/rules)
    4. Busca TODOS os servicos do Consul
    5. Aplica categorizacao usando CategorizationRuleEngine
    6. Filtra servicos por categoria solicitada
    7. Adiciona informacoes do site (code, name) ao servico
    8. Aplica filtros adicionais (company, site, env, node)
    9. Aplica ordenacao server-side
    10. Aplica paginacao server-side
    11. Retorna dados formatados com filterOptions

    Args:
        category: Categoria de monitoramento (ex: network-probes)
        company: Filtro de empresa (opcional)
        site: Filtro de site (opcional)
        env: Filtro de ambiente (opcional)
        page: Numero da pagina, comeca em 1 (opcional - sem paginacao se omitido)
        page_size: Itens por pagina, 10-200 (opcional - sem paginacao se omitido)
        sort_field: Campo para ordenacao (opcional)
        sort_order: Direcao: 'ascend' ou 'descend' (opcional)
        node: IP do no para filtrar (opcional)

    Returns:
        ```json
        {
            "success": true,
            "category": "network-probes",
            "data": [
                {
                    "ID": "icmp-ramada-palmas-01",
                    "Service": "blackbox",
                    "Address": "10.0.0.1",
                    "Port": 9115,
                    "Node": "consul-server-1",
                    "node_ip": "172.16.1.26",
                    "site_code": "palmas",
                    "site_name": "Palmas",
                    "Meta": {
                        "module": "icmp",
                        "company": "Empresa Ramada",
                        "site": "palmas",
                        "env": "prod",
                        "name": "Gateway Principal"
                    }
                }
            ],
            "total": 150,
            "page": 1,
            "pageSize": 50,
            "filterOptions": {
                "company": ["Empresa A", "Empresa B"],
                "env": ["dev", "prod"],
                "site": ["palmas", "rio"]
            },
            "available_fields": ["company", "site", "env", "name", ...]
        }
        ```
    """
    
    # ✅ USAR CACHE - Função interna para fetch quando cache miss
    async def fetch_data():
        """Função interna que busca dados quando há cache miss"""
        try:
            logger.info(f"[MONITORING DATA] Buscando dados da categoria '{category}'")

            # ==================================================================
            # PASSO 1: Buscar SITES do KV (metadata/sites)
            # ==================================================================
            from core.kv_manager import KVManager
            
            kv = KVManager()

            # ✅ OTIMIZAÇÃO: Buscar nós com cache (TTL: 5min) - usa instância global
            consul_nodes = await get_nodes_cached(consul_manager)
            nodes_map = {}  # Node Name → IP Address
            for node in consul_nodes:
                node_name = node.get('Node', '')
                node_address = node.get('Address', '')
                if node_name and node_address:
                    nodes_map[node_name] = node_address
            
            logger.debug(f"[MONITORING DATA] Mapeados {len(nodes_map)} nós do Consul: {list(nodes_map.keys())}")

            sites_data = await kv.get_json('skills/eye/metadata/sites')
            sites = []
            sites_map = {}  # IP → site data

            if sites_data:
                # Estrutura pode ser {data: {data: [sites]}} ou {data: {sites: [...]}} ou {sites: [...]}
                if isinstance(sites_data, dict):
                    # Tentar extrair sites de qualquer nível de aninhamento
                    if 'data' in sites_data:
                        inner = sites_data['data']
                        if isinstance(inner, dict):
                            if 'sites' in inner:
                                sites = inner['sites']
                            elif 'data' in inner:  # Bug: {data: {data: [...]}}
                                sites = inner['data'] if isinstance(inner['data'], list) else []
                            else:
                                # Assumir que inner é a lista de sites
                                sites = list(inner.values()) if inner else []
                        elif isinstance(inner, list):
                            sites = inner
                    elif 'sites' in sites_data:
                        sites = sites_data['sites']
                
                # Criar mapa IP → site para lookup rápido
                if sites and isinstance(sites, list):
                    for site_item in sites:
                        if isinstance(site_item, dict):
                            prometheus_ip = site_item.get('prometheus_instance') or site_item.get('prometheus_host')
                            if prometheus_ip:
                                sites_map[prometheus_ip] = site_item

            logger.debug(f"[MONITORING DATA] Carregados {len(sites)} sites do KV")

            # ==================================================================
            # PASSO 2: Buscar CAMPOS do KV (metadata/fields)
            # ==================================================================
            fields_data = await kv.get_json('skills/eye/metadata/fields')
            available_fields = []

            if fields_data and 'fields' in fields_data:
                # Filtrar apenas campos relevantes para a categoria
                for field in fields_data['fields']:
                    # Verificar se campo deve aparecer nesta categoria
                    show_in_key = f"show_in_{category.replace('-', '_')}"
                    if field.get(show_in_key, True):  # Default True
                        available_fields.append({
                            'name': field['name'],
                            'display_name': field.get('display_name', field['name']),
                            'field_type': field.get('field_type', 'string')
                        })

            logger.debug(f"[MONITORING DATA] {len(available_fields)} campos disponíveis para '{category}'")

            # ==================================================================
            # PASSO 3: Carregar regras de categorização
            # ==================================================================
            await categorization_engine.load_rules()

            # ==================================================================
            # PASSO 4: Buscar TODOS os serviços do Consul
            # ==================================================================
            all_services_dict = await consul_manager.get_all_services_catalog(use_fallback=True)

            # Remover _metadata se existir (não usado aqui)
            all_services_dict.pop("_metadata", None)

            # Converter estrutura aninhada para lista plana
            all_services = []
            for node_name, services_dict in all_services_dict.items():
                for service_id, service_data in services_dict.items():
                    service_data['Node'] = node_name
                    service_data['ID'] = service_id
                    all_services.append(service_data)

            logger.info(f"[MONITORING DATA] Total de serviços no Consul: {len(all_services)}")

            # ==================================================================
            # PASSO 5: Categorizar serviços e filtrar pela categoria solicitada
            # ==================================================================
            filtered_services = []

            for idx, svc in enumerate(all_services):
                try:
                    # Categorizar serviço usando engine
                    svc_job_name = svc.get('Service', '')
                    svc_module = svc.get('Meta', {}).get('module', '')
                    svc_metrics_path = svc.get('Meta', {}).get('metrics_path', '/metrics')

                    # SPEC-PERF-001: Marcar se o serviço tem metrics_path no metadata
                    # Se não tiver, o engine ignora a condição metrics_path da regra
                    has_metrics_path = 'metrics_path' in svc.get('Meta', {})

                    # FIX BUG #1: categorize() espera dict, não kwargs
                    svc_category, svc_type_info = categorization_engine.categorize({
                        'job_name': svc_job_name,
                        'module': svc_module,
                        'metrics_path': svc_metrics_path,
                        '_has_metrics_path': has_metrics_path
                    })

                    # Verificar se serviço pertence à categoria solicitada
                    if svc_category != category:
                        continue

                    # ==================================================================
                    # PASSO 6: Adicionar informações do site
                    # ==================================================================
                    # Mapear Node Name → IP Address → Site
                    node_name = svc.get('Node', '')
                    node_ip = nodes_map.get(node_name, '')
                    site_info = sites_map.get(node_ip)

                    # ✅ CRÍTICO: Adicionar node_ip para permitir filtro no frontend
                    # Frontend usa NodeSelector que retorna IP, não nome do nó
                    svc['node_ip'] = node_ip

                    if site_info:
                        svc['site_code'] = site_info.get('code')
                        svc['site_name'] = site_info.get('name')
                    else:
                        # Fallback: usar metadata.site se disponível
                        svc['site_code'] = svc.get('Meta', {}).get('site')
                        svc['site_name'] = None

                    # ========================================================
                    # PASSO 7: Aplicar filtros adicionais
                    # ========================================================
                    svc_meta = svc.get('Meta', {})

                    if company and svc_meta.get('company') != company:
                        logger.debug(f"[FILTER] Bloqueado por company: {svc_meta.get('company')} != {company}")
                        continue

                    if site:
                        # Filtrar por site_code OU metadata.site
                        if svc.get('site_code') != site and svc_meta.get('site') != site:
                            logger.debug(f"[FILTER] Bloqueado por site: {svc.get('site_code')}/{svc_meta.get('site')} != {site}")
                            continue

                    if env and svc_meta.get('env') != env:
                        logger.debug(f"[FILTER] Bloqueado por env: {svc_meta.get('env')} != {env}")
                        continue

                    # Serviço passou em todos os filtros
                    filtered_services.append(svc)
                    
                    # DEBUG: Logar primeiros serviços aprovados
                    if len(filtered_services) <= 3:
                        logger.debug(f"[APPROVED] Serviço {filtered_services[-1].get('ID', 'unknown')} adicionado (total={len(filtered_services)})")
                        
                except Exception as e:
                    logger.error(f"[CATEGORIZE ERROR] Erro ao processar serviço #{idx}: {e}", exc_info=True)
                    continue

            logger.info(
                f"[MONITORING DATA] Filtrados {len(filtered_services)} de {len(all_services)} "
                f"serviços para categoria '{category}'"
            )

            # ==================================================================
            # PASSO 8: Retornar dados formatados
            # ==================================================================
            return {
                "success": True,
                "category": category,
                "data": filtered_services,
                "total": len(filtered_services),
                "available_fields": available_fields,
                "filters_applied": {
                    "company": company,
                    "site": site,
                    "env": env
                },
                "metadata": {
                    "total_sites": len(sites),
                    "categorization_engine": "loaded"
                }
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"[MONITORING DATA ERROR] {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")


    # ==========================================================================
    # SPEC-PERF-002 FIX: Usar MonitoringDataCache corretamente
    #
    # PROBLEMA ANTERIOR: get_services_cached nao usava o MonitoringDataCache
    # criado especificamente para o SPEC-PERF-002.
    #
    # SOLUCAO: Verificar cache do MonitoringDataCache primeiro, se miss,
    # buscar dados e armazenar no cache.
    # ==========================================================================

    # Tentar buscar do cache intermediario de monitoramento
    cached_data = await monitoring_data_cache.get_data(category, node)

    if cached_data is not None:
        # CACHE HIT - usar dados do cache
        logger.info(f"[MONITORING DATA] Cache HIT para category='{category}', node='{node}'")
        raw_result = {
            "success": True,
            "category": category,
            "data": cached_data,
            "total": len(cached_data),
            "available_fields": [],  # Sera preenchido abaixo se necessario
            "metadata": {"cache_hit": True}
        }

        # Buscar available_fields do cache generico ou KV se necessario
        from core.kv_manager import KVManager
        kv = KVManager()
        fields_data = await kv.get_json('skills/eye/metadata/fields')
        available_fields = []
        if fields_data and 'fields' in fields_data:
            for field in fields_data['fields']:
                show_in_key = f"show_in_{category.replace('-', '_')}"
                if field.get(show_in_key, True):
                    available_fields.append({
                        'name': field['name'],
                        'display_name': field.get('display_name', field['name']),
                        'field_type': field.get('field_type', 'string')
                    })
        raw_result["available_fields"] = available_fields
    else:
        # CACHE MISS - buscar dados do Consul
        logger.info(f"[MONITORING DATA] Cache MISS para category='{category}', node='{node}'")
        raw_result = await fetch_data()

        # Armazenar no cache de monitoramento para proximas requisicoes
        await monitoring_data_cache.set_data(
            category=category,
            data=raw_result.get('data', []),
            node=node
        )

    # SPEC-PERF-002: Processar dados com paginacao, filtros e ordenacao server-side
    # Se page e page_size nao forem passados, retorna todos (compatibilidade backward)

    # Extrair filtros dinamicos dos query params (exceto os ja processados)
    excluded_params = {'category', 'company', 'site', 'env', 'page', 'page_size',
                       'sort_field', 'sort_order', 'node', 'q'}
    dynamic_filters = {}
    for key, value in request.query_params.items():
        if key not in excluded_params and value:
            dynamic_filters[key] = value

    # Combinar filtros fixos com dinamicos
    all_filters = {
        'company': company,
        'site': site,
        'env': env,
        **dynamic_filters
    }

    # Processar dados server-side (incluindo busca textual)
    processed = process_monitoring_data(
        data=raw_result.get('data', []),
        node=node,
        filters=all_filters,
        sort_field=sort_field,
        sort_order=sort_order,
        page=page,
        page_size=page_size,
        search_query=q  # SPEC-PERF-002 FIX: Busca textual
    )

    # Montar resposta final mantendo estrutura compativel
    response = {
        "success": True,
        "category": category,
        "data": processed["data"],
        "total": processed["total"],
        "available_fields": raw_result.get('available_fields', []),
        "filters_applied": {
            "company": company,
            "site": site,
            "env": env,
            "node": node,
            **dynamic_filters
        },
        "metadata": raw_result.get('metadata', {})
    }

    # Adicionar campos de paginacao se foram solicitados
    if page is not None and page_size is not None:
        response["page"] = processed["page"]
        response["pageSize"] = processed["pageSize"]  # camelCase
        response["filterOptions"] = processed["filterOptions"]  # camelCase

        # Calcular total de paginas
        total_pages = (processed["total"] + page_size - 1) // page_size
        response["totalPages"] = total_pages
    else:
        # Sem paginacao - incluir filterOptions mesmo assim para uso futuro
        response["filterOptions"] = processed["filterOptions"]  # camelCase

    return response


# ============================================================================
# ENDPOINT 1.5: /monitoring/summary - METRICAS AGREGADAS DO DATASET (SPEC-PERF-002)
# ============================================================================

@router.get("/summary")
async def get_monitoring_summary(
    category: str = Query(..., description="Categoria: network-probes, web-probes, etc"),
    company: Optional[str] = Query(None, description="Filtrar por empresa"),
    site: Optional[str] = Query(None, description="Filtrar por site"),
    env: Optional[str] = Query(None, description="Filtrar por ambiente"),
    node: Optional[str] = Query(None, description="Filtrar por IP do no")
):
    """
    Retorna metricas agregadas sobre TODO o dataset de uma categoria.

    SPEC-PERF-002 FIX: Este endpoint fornece estatisticas sem paginacao,
    permitindo que o frontend mostre totais e contagens sem carregar todos os dados.

    CASOS DE USO:
    - Mostrar "150 servicos encontrados" no header da tabela
    - Exibir contadores por status (online/offline)
    - Popular dropdowns de filtro sem buscar dados paginados
    - Dashboard com visao geral da categoria

    Args:
        category: Categoria de monitoramento
        company: Filtro de empresa (opcional)
        site: Filtro de site (opcional)
        env: Filtro de ambiente (opcional)
        node: IP do no para filtrar (opcional)

    Returns:
        ```json
        {
            "success": true,
            "category": "network-probes",
            "summary": {
                "total": 150,
                "byCompany": {"Empresa A": 50, "Empresa B": 100},
                "byEnv": {"prod": 120, "dev": 30},
                "bySite": {"palmas": 80, "rio": 70},
                "byNode": {"172.16.1.26": 100, "172.16.1.27": 50}
            },
            "filterOptions": {
                "company": ["Empresa A", "Empresa B"],
                "env": ["dev", "prod"],
                "site": ["palmas", "rio"],
                "node_ip": ["172.16.1.26", "172.16.1.27"]
            }
        }
        ```
    """
    try:
        logger.info(f"[MONITORING SUMMARY] Buscando resumo da categoria '{category}'")

        # Tentar buscar do cache primeiro
        cached_data = await monitoring_data_cache.get_data(category, node)

        if cached_data is None:
            # Cache miss - precisa buscar dados frescos
            # Reutilizar a logica do endpoint /data (fetch_data interno)
            from core.kv_manager import KVManager
            kv = KVManager()

            # Buscar nos do Consul com cache
            consul_nodes = await get_nodes_cached(consul_manager)
            nodes_map = {}
            for n in consul_nodes:
                node_name = n.get('Node', '')
                node_address = n.get('Address', '')
                if node_name and node_address:
                    nodes_map[node_name] = node_address

            # Buscar sites
            sites_data = await kv.get_json('skills/eye/metadata/sites')
            sites_map = {}
            if sites_data:
                sites = []
                if isinstance(sites_data, dict):
                    if 'data' in sites_data:
                        inner = sites_data['data']
                        if isinstance(inner, dict) and 'sites' in inner:
                            sites = inner['sites']
                        elif isinstance(inner, list):
                            sites = inner
                    elif 'sites' in sites_data:
                        sites = sites_data['sites']

                for site_item in sites:
                    if isinstance(site_item, dict):
                        prometheus_ip = site_item.get('prometheus_instance') or site_item.get('prometheus_host')
                        if prometheus_ip:
                            sites_map[prometheus_ip] = site_item

            # Carregar regras
            await categorization_engine.load_rules()

            # Buscar todos os servicos
            all_services_dict = await consul_manager.get_all_services_catalog(use_fallback=True)
            all_services_dict.pop("_metadata", None)

            all_services = []
            for node_name, services_dict in all_services_dict.items():
                for service_id, service_data in services_dict.items():
                    service_data['Node'] = node_name
                    service_data['ID'] = service_id
                    all_services.append(service_data)

            # Filtrar por categoria
            filtered_services = []
            for svc in all_services:
                svc_job_name = svc.get('Service', '')
                svc_module = svc.get('Meta', {}).get('module', '')
                svc_metrics_path = svc.get('Meta', {}).get('metrics_path', '/metrics')
                has_metrics_path = 'metrics_path' in svc.get('Meta', {})

                svc_category, _ = categorization_engine.categorize({
                    'job_name': svc_job_name,
                    'module': svc_module,
                    'metrics_path': svc_metrics_path,
                    '_has_metrics_path': has_metrics_path
                })

                if svc_category != category:
                    continue

                # Adicionar node_ip e site info
                node_name = svc.get('Node', '')
                node_ip = nodes_map.get(node_name, '')
                svc['node_ip'] = node_ip
                site_info = sites_map.get(node_ip)
                if site_info:
                    svc['site_code'] = site_info.get('code')
                else:
                    svc['site_code'] = svc.get('Meta', {}).get('site')

                filtered_services.append(svc)

            # Armazenar no cache
            await monitoring_data_cache.set_data(category, filtered_services, node)
            cached_data = filtered_services

        # Aplicar filtros basicos
        data = cached_data

        # Filtrar por node se especificado
        if node and node != 'all':
            data = [item for item in data if item.get('node_ip') == node]

        # Filtrar por company, site, env
        if company:
            data = [item for item in data if item.get('Meta', {}).get('company') == company]
        if site:
            data = [item for item in data
                    if item.get('site_code') == site or item.get('Meta', {}).get('site') == site]
        if env:
            data = [item for item in data if item.get('Meta', {}).get('env') == env]

        # Calcular agregacoes
        by_company = {}
        by_env = {}
        by_site = {}
        by_node = {}

        for item in data:
            meta = item.get('Meta', {})

            # Por empresa
            item_company = meta.get('company', 'N/A')
            by_company[item_company] = by_company.get(item_company, 0) + 1

            # Por ambiente
            item_env = meta.get('env', 'N/A')
            by_env[item_env] = by_env.get(item_env, 0) + 1

            # Por site
            item_site = item.get('site_code') or meta.get('site', 'N/A')
            by_site[item_site] = by_site.get(item_site, 0) + 1

            # Por node
            item_node = item.get('node_ip', 'N/A')
            by_node[item_node] = by_node.get(item_node, 0) + 1

        # Extrair filterOptions
        filter_options = process_monitoring_data(
            data=cached_data,  # Usar dados nao filtrados para ter todas opcoes
            node=None,
            filters=None,
            page=None,
            page_size=None
        )

        return {
            "success": True,
            "category": category,
            "summary": {
                "total": len(data),
                "byCompany": by_company,
                "byEnv": by_env,
                "bySite": by_site,
                "byNode": by_node
            },
            "filterOptions": filter_options["filterOptions"],
            "filtersApplied": {
                "company": company,
                "site": site,
                "env": env,
                "node": node
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[MONITORING SUMMARY ERROR] {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# ENDPOINT 2: /monitoring/metrics - BUSCA DO PROMETHEUS (Métricas PromQL)
# ============================================================================

@router.get("/metrics")
async def get_monitoring_metrics(
    category: str = Query(..., description="Categoria: network-probes, web-probes, etc"),
    server: Optional[str] = Query(None, description="Servidor Prometheus (IP ou site code)"),
    time_range: str = Query("5m", description="Intervalo de tempo (ex: 5m, 1h)"),
    company: Optional[str] = Query(None),
    site: Optional[str] = Query(None)
):
    """
    Endpoint para buscar MÉTRICAS do Prometheus via PromQL

    FLUXO REFATORADO:
    1. Busca sites do KV para resolver server (pode ser IP ou site code)
    2. Busca regras de categorização
    3. Determina jobs/módulos da categoria
    4. Constrói query PromQL baseado na categoria
    5. Executa query no Prometheus
    6. Processa e formata resultados

    Args:
        category: Categoria de monitoramento
        server: Servidor Prometheus (IP ou site code, opcional)
        time_range: Intervalo de tempo para métricas
        company: Filtro de empresa
        site: Filtro de site

    Returns:
        Métricas do Prometheus formatadas
    """
    try:
        logger.info(f"[MONITORING METRICS] Buscando métricas da categoria '{category}'")

        # ==================================================================
        # PASSO 1: Resolver servidor Prometheus
        # ==================================================================
        from core.kv_manager import KVManager
        kv = KVManager()

        prometheus_host = None
        prometheus_port = 9090

        if server:
            # Tentar resolver como site code primeiro
            sites_data = await kv.get_json('skills/eye/metadata/sites')
            if sites_data and 'data' in sites_data:
                for site_info in sites_data['data'].get('sites', []):
                    if site_info.get('code') == server or site_info.get('prometheus_instance') == server:
                        prometheus_host = site_info.get('prometheus_host') or site_info.get('prometheus_instance')
                        prometheus_port = site_info.get('prometheus_port', 9090)
                        break

            # Se não encontrou, usar como IP direto
            if not prometheus_host:
                prometheus_host = server
        else:
            # Usar primeiro site disponível
            sites_data = await kv.get_json('skills/eye/metadata/sites')
            if sites_data and 'data' in sites_data:
                sites = sites_data['data'].get('sites', [])
                if sites:
                    default_site = next((s for s in sites if s.get('is_default')), sites[0])
                    prometheus_host = default_site.get('prometheus_host') or default_site.get('prometheus_instance')
                    prometheus_port = default_site.get('prometheus_port', 9090)

        if not prometheus_host:
            raise HTTPException(
                status_code=500,
                detail="Nenhum servidor Prometheus configurado"
            )

        logger.info(f"[MONITORING METRICS] Usando Prometheus: {prometheus_host}:{prometheus_port}")

        # ==================================================================
        # PASSO 2: Carregar regras e determinar jobs/módulos da categoria
        # ==================================================================
        await categorization_engine.load_rules()

        # Obter todas as regras da categoria
        rules = categorization_engine.get_rules_by_category(category)

        if not rules:
            raise HTTPException(
                status_code=404,
                detail=f"Nenhuma regra de categorização encontrada para '{category}'"
            )

        # Extrair job_name_pattern e module_pattern das regras
        jobs_patterns = []
        modules_patterns = []

        for rule in rules:
            conditions = rule.get('conditions', {})
            if conditions.get('job_name_pattern'):
                jobs_patterns.append(conditions['job_name_pattern'].replace('^', '').replace('.*', ''))
            if conditions.get('module_pattern'):
                modules_patterns.append(conditions['module_pattern'].replace('^', '').replace('$', ''))

        # ==================================================================
        # PASSO 3: Construir query PromQL baseado na categoria
        # ==================================================================
        query = None

        if category in ['network-probes', 'web-probes']:
            # Blackbox probes
            if modules_patterns:
                modules_regex = '|'.join(modules_patterns)
                query = f"probe_success{{__param_module=~\"{modules_regex}\"}}"

        elif category == 'system-exporters':
            # Node/Windows exporters - CPU usage
            if jobs_patterns:
                jobs_regex = '|'.join(jobs_patterns)
                query = f"100 - (avg by (instance) (irate(node_cpu_seconds_total{{job=~\"{jobs_regex}\",mode=\"idle\"}}[{time_range}])) * 100)"

        elif category == 'database-exporters':
            # Database exporters - up status
            if jobs_patterns:
                jobs_regex = '|'.join(jobs_patterns)
                query = f"up{{job=~\"{jobs_regex}\"}}"
        else:
            # Categoria genérica - up status
            if jobs_patterns:
                jobs_regex = '|'.join(jobs_patterns)
                query = f"up{{job=~\"{jobs_regex}\"}}"

        if not query:
            raise HTTPException(
                status_code=500,
                detail=f"Não foi possível construir query para categoria '{category}'"
            )

        logger.info(f"[MONITORING METRICS] Query PromQL: {query}")

        # ==================================================================
        # PASSO 4: Executar query no Prometheus
        # ==================================================================
        prometheus_url = f"http://{prometheus_host}:{prometheus_port}"

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{prometheus_url}/api/v1/query",
                params={'query': query},
                timeout=10.0
            )
            response.raise_for_status()
            prom_data = response.json()

        if prom_data['status'] != 'success':
            raise HTTPException(
                status_code=500,
                detail=f"Prometheus query failed: {prom_data.get('error')}"
            )

        # ==================================================================
        # PASSO 5: Processar resultados
        # ==================================================================
        results = prom_data['data']['result']

        formatted_metrics = []
        for result in results:
            metric = result['metric']
            value = result['value'][1]  # [timestamp, value]

            formatted_metrics.append({
                'instance': metric.get('instance', ''),
                'job': metric.get('job', ''),
                'module': metric.get('__param_module', ''),
                'status': float(value),
                'timestamp': result['value'][0],
                # Incluir todos os labels do Prometheus
                **{k: v for k, v in metric.items() if not k.startswith('__')}
            })

        logger.info(f"[MONITORING METRICS] Retornando {len(formatted_metrics)} métricas")

        return {
            "success": True,
            "category": category,
            "metrics": formatted_metrics,
            "query": query,
            "prometheus_server": f"{prometheus_host}:{prometheus_port}",
            "total": len(formatted_metrics)
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[MONITORING METRICS ERROR] {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# ENDPOINT 3: /monitoring/categories - LISTA CATEGORIAS DISPONÍVEIS
# ============================================================================

@router.get("/categories")
async def get_monitoring_categories():
    """
    Lista todas as categorias de monitoramento disponíveis

    FONTE: categorization/rules no KV

    Returns:
        ```json
        {
            "success": true,
            "categories": [
                {
                    "id": "network-probes",
                    "display_name": "Network Probes (Rede)",
                    "total_rules": 7
                },
                {
                    "id": "web-probes",
                    "display_name": "Web Probes (Aplicações)",
                    "total_rules": 5
                },
                ...
            ]
        }
        ```
    """
    try:
        # Carregar regras
        await categorization_engine.load_rules()

        # Obter categorias do engine
        rules_data = await kv_manager.get('monitoring-types/categorization/rules')

        if not rules_data:
            return {
                "success": True,
                "categories": [],
                "message": "Nenhuma regra de categorização configurada"
            }

        categories_list = rules_data.get('categories', [])

        # Contar regras por categoria
        rules = rules_data.get('rules', [])
        category_counts = {}
        for rule in rules:
            cat = rule.get('category')
            category_counts[cat] = category_counts.get(cat, 0) + 1

        # Formatar resposta
        formatted_categories = []
        for cat_info in categories_list:
            cat_id = cat_info.get('id')
            formatted_categories.append({
                'id': cat_id,
                'display_name': cat_info.get('display_name', cat_id),
                'total_rules': category_counts.get(cat_id, 0)
            })

        return {
            "success": True,
            "categories": formatted_categories,
            "total_categories": len(formatted_categories)
        }

    except Exception as e:
        logger.error(f"[MONITORING CATEGORIES ERROR] {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# ENDPOINT 4: /monitoring/cache - GERENCIAMENTO DO CACHE (SPEC-PERF-002)
# ============================================================================

@router.get("/cache/stats")
async def get_monitoring_cache_stats():
    """
    Retorna estatisticas do cache de monitoramento.

    SPEC-PERF-002: Permite monitorar eficiencia do cache.

    Returns:
        ```json
        {
            "success": true,
            "stats": {
                "requests": 150,
                "cache_hits": 142,
                "cache_misses": 8,
                "hit_rate_percent": 94.67,
                "ttl_seconds": 30
            }
        }
        ```
    """
    try:
        stats = await monitoring_data_cache.get_stats()
        return {
            "success": True,
            "stats": stats
        }
    except Exception as e:
        logger.error(f"[CACHE STATS ERROR] {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/cache/invalidate")
async def invalidate_monitoring_cache(
    category: Optional[str] = Query(None, description="Categoria para invalidar (None = todas)")
):
    """
    Invalida cache de monitoramento para forcar refresh.

    SPEC-PERF-002: Util quando dados mudam e usuario quer ver atualizacao imediata.

    Args:
        category: Categoria especifica para invalidar (opcional)

    Returns:
        ```json
        {
            "success": true,
            "invalidated_entries": 3,
            "message": "Cache invalidado para categoria 'network-probes'"
        }
        ```
    """
    try:
        count = await monitoring_data_cache.invalidate(category)
        msg = (
            f"Cache invalidado para categoria '{category}'"
            if category else "Todo cache de monitoramento invalidado"
        )
        return {
            "success": True,
            "invalidated_entries": count,
            "message": msg
        }
    except Exception as e:
        logger.error(f"[CACHE INVALIDATE ERROR] {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
