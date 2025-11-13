"""
API Unificada de Monitoramento - Endpoint Único para Todas as Páginas

RESPONSABILIDADES:
- Endpoint unificado GET /api/v1/monitoring/data (busca do Consul)
- Endpoint unificado GET /api/v1/monitoring/metrics (busca do Prometheus via PromQL)
- Endpoint POST /api/v1/monitoring/sync-cache (sincronização forçada)
- Filtra por categoria (network-probes, web-probes, etc)
- Executa queries PromQL dinamicamente
- Retorna dados formatados para ProTable

AUTOR: Sistema de Refatoração Skills Eye v2.0
DATA: 2025-11-13

IMPORTANTE: Este arquivo implementa a ESTRATÉGIA DUPLA conforme
documento NOTA_AJUSTES_PLANO_V2.md - Seção 2️⃣
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List, Dict, Any
from datetime import datetime
import logging
import httpx

from core.consul_kv_config_manager import ConsulKVConfigManager
from core.dynamic_query_builder import DynamicQueryBuilder, QUERY_TEMPLATES
from core.consul_manager import ConsulManager

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/monitoring", tags=["Monitoring Unified"])

# Inicializar componentes globais
config_manager = ConsulKVConfigManager(ttl=300)  # Cache de 5 minutos
query_builder = DynamicQueryBuilder()
consul_manager = ConsulManager()


# ============================================================================
# ENDPOINT 1: /monitoring/data - BUSCA DO CONSUL (Serviços)
# ============================================================================

@router.get("/data")
async def get_monitoring_data(
    category: str = Query(..., description="Categoria: network-probes, web-probes, etc"),
    company: Optional[str] = Query(None, description="Filtrar por empresa"),
    site: Optional[str] = Query(None, description="Filtrar por site"),
    env: Optional[str] = Query(None, description="Filtrar por ambiente")
):
    """
    Endpoint para buscar SERVIÇOS do Consul filtrados por categoria

    Este endpoint busca do Consul Service Registry (igual Services.tsx faz),
    NÃO do Prometheus. É a fonte primária de dados para as 4 novas páginas.

    FLUXO:
    1. Busca tipos de monitoramento do cache KV
    2. Identifica módulos/jobs da categoria solicitada
    3. Busca TODOS os serviços do Consul
    4. Filtra serviços por módulo/job da categoria
    5. Aplica filtros adicionais (company, site, env)
    6. Retorna dados formatados

    Args:
        category: Categoria de monitoramento (ex: network-probes)
        company: Filtro de empresa (opcional)
        site: Filtro de site (opcional)
        env: Filtro de ambiente (opcional)

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
                    "Tags": ["icmp", "network"],
                    "Meta": {
                        "module": "icmp",
                        "company": "Empresa Ramada",
                        "site": "palmas",
                        "env": "prod",
                        "name": "Gateway Principal",
                        "instance": "10.0.0.1"
                    }
                }
            ],
            "total": 150,
            "modules": ["icmp", "tcp", "dns"],  # Para categoria network-probes
            "cache_age_seconds": 42
        }
        ```

    Example:
        GET /api/v1/monitoring/data?category=network-probes&company=Ramada
        GET /api/v1/monitoring/data?category=system-exporters&site=palmas
    """
    try:
        logger.info(f"[MONITORING DATA] Buscando dados da categoria '{category}'")

        # ==================================================================
        # PASSO 1: Buscar tipos de monitoramento do cache KV
        # ==================================================================
        types_cache = await config_manager.get('monitoring-types/cache')

        if not types_cache:
            raise HTTPException(
                status_code=500,
                detail="Cache de tipos não disponível. Execute sync-cache primeiro."
            )

        cache_stats = config_manager.get_cache_stats()
        logger.debug(f"[MONITORING DATA] Cache stats: {cache_stats}")

        # ==================================================================
        # PASSO 2: Filtrar tipos pela categoria solicitada
        # ==================================================================
        category_types = []
        for category_data in types_cache.get('categories', []):
            if category_data['category'] == category:
                category_types = category_data['types']
                break

        if not category_types:
            # Categoria não encontrada - listar categorias disponíveis
            available_categories = [c['category'] for c in types_cache.get('categories', [])]
            raise HTTPException(
                status_code=404,
                detail=f"Categoria '{category}' não encontrada. Categorias disponíveis: {available_categories}"
            )

        logger.info(f"[MONITORING DATA] Categoria '{category}' tem {len(category_types)} tipos")

        # ==================================================================
        # PASSO 3: Mapear categoria → módulos/jobs para filtrar serviços
        # ==================================================================
        # Extrair módulos (para blackbox) e job_names (para exporters)
        modules = set()
        job_names = set()

        for type_def in category_types:
            if type_def.get('module'):  # Blackbox probe
                modules.add(type_def['module'])
            if type_def.get('job_name'):
                job_names.add(type_def['job_name'])

        logger.debug(f"[MONITORING DATA] Módulos: {modules}, Jobs: {job_names}")

        # ==================================================================
        # PASSO 4: Buscar TODOS os serviços do Consul
        # ==================================================================
        all_services = await consul_manager.get_services_list()
        logger.info(f"[MONITORING DATA] Total de serviços no Consul: {len(all_services)}")

        # ==================================================================
        # PASSO 5: Filtrar serviços pela categoria
        # ==================================================================
        filtered_services = []

        for svc in all_services:
            # Verificar se serviço pertence à categoria
            # Regra 1: Se tem módulo nos metadata, comparar com módulos da categoria
            svc_module = svc.get('Meta', {}).get('module', '')
            svc_belongs_to_category = False

            if svc_module and svc_module in modules:
                # Este serviço é um blackbox probe da categoria
                svc_belongs_to_category = True
            # Regra 2: Se job_name está na lista de jobs da categoria
            elif svc.get('Service') in job_names:
                # Este serviço é um exporter da categoria
                svc_belongs_to_category = True

            # Se serviço não pertence à categoria, pular
            if not svc_belongs_to_category:
                continue

            # ========================================================
            # Aplicar filtros adicionais (company, site, env)
            # ========================================================
            svc_meta = svc.get('Meta', {})

            if company and svc_meta.get('company') != company:
                continue  # Filtrar por company

            if site and svc_meta.get('site') != site:
                continue  # Filtrar por site

            if env and svc_meta.get('env') != env:
                continue  # Filtrar por env

            # Serviço passou em todos os filtros
            filtered_services.append(svc)

        logger.info(
            f"[MONITORING DATA] Filtrados {len(filtered_services)} de {len(all_services)} "
            f"serviços para categoria '{category}'"
        )

        # ==================================================================
        # PASSO 6: Retornar dados formatados
        # ==================================================================
        return {
            "success": True,
            "category": category,
            "data": filtered_services,
            "total": len(filtered_services),
            "modules": list(modules),
            "job_names": list(job_names),
            "cache_age_seconds": (
                (datetime.now() - config_manager._cache.get(
                    f"{config_manager.prefix}monitoring-types/cache",
                    type('obj', (), {'timestamp': datetime.now()})()
                ).timestamp).total_seconds()
                if f"{config_manager.prefix}monitoring-types/cache" in config_manager._cache
                else 0
            ),
            "filters_applied": {
                "company": company,
                "site": site,
                "env": env
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[MONITORING DATA ERROR] {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")


# ============================================================================
# ENDPOINT 2: /monitoring/metrics - BUSCA DO PROMETHEUS (Métricas PromQL)
# ============================================================================

@router.get("/metrics")
async def get_monitoring_metrics(
    category: str = Query(..., description="Categoria: network-probes, web-probes, etc"),
    server: Optional[str] = Query(None, description="Servidor Prometheus"),
    time_range: str = Query("5m", description="Intervalo de tempo (ex: 5m, 1h)"),
    company: Optional[str] = Query(None),
    site: Optional[str] = Query(None)
):
    """
    Endpoint para buscar MÉTRICAS do Prometheus via PromQL

    Este endpoint executa queries PromQL e retorna métricas atuais,
    diferente de /data que busca serviços cadastrados no Consul.

    USO TÍPICO:
    - Dashboards com métricas em tempo real
    - Gráficos de performance
    - Alertas baseados em métricas

    FLUXO:
    1. Busca tipos de monitoramento do cache KV
    2. Determina servidor Prometheus (ou usa padrão)
    3. Constrói query PromQL baseado na categoria
    4. Executa query no Prometheus
    5. Processa e formata resultados
    6. Retorna métricas

    Args:
        category: Categoria de monitoramento
        server: Servidor Prometheus específico (opcional, padrão: primeiro disponível)
        time_range: Intervalo de tempo para métricas (ex: 5m)
        company: Filtro de empresa
        site: Filtro de site

    Returns:
        ```json
        {
            "success": true,
            "category": "network-probes",
            "metrics": [
                {
                    "instance": "10.0.0.1",
                    "job": "blackbox",
                    "module": "icmp",
                    "status": 1,
                    "latency_ms": 25.3,
                    "timestamp": "2025-11-13T10:30:00Z",
                    "company": "Ramada",
                    "site": "palmas"
                }
            ],
            "query": "probe_success{job='blackbox',__param_module=~'icmp|tcp'}",
            "prometheus_server": "172.16.1.26:9090",
            "total": 45
        }
        ```
    """
    try:
        logger.info(f"[MONITORING METRICS] Buscando métricas da categoria '{category}'")

        # ==================================================================
        # PASSO 1: Buscar tipos de monitoramento do cache
        # ==================================================================
        types_cache = await config_manager.get('monitoring-types/cache')

        if not types_cache:
            raise HTTPException(
                status_code=500,
                detail="Cache de tipos não disponível"
            )

        # ==================================================================
        # PASSO 2: Determinar servidor Prometheus
        # ==================================================================
        if not server:
            # Usar primeiro servidor disponível
            servers = list(types_cache.get('servers', {}).keys())
            if not servers:
                raise HTTPException(
                    status_code=500,
                    detail="Nenhum servidor Prometheus configurado"
                )
            server = servers[0]

        logger.info(f"[MONITORING METRICS] Usando servidor Prometheus: {server}")

        # ==================================================================
        # PASSO 3: Buscar tipos da categoria
        # ==================================================================
        category_types = []
        for cat_data in types_cache.get('categories', []):
            if cat_data['category'] == category:
                category_types = cat_data['types']
                break

        if not category_types:
            raise HTTPException(
                status_code=404,
                detail=f"Categoria '{category}' não encontrada"
            )

        # ==================================================================
        # PASSO 4: Construir query PromQL baseado na categoria
        # ==================================================================
        query = None

        if category in ['network-probes', 'web-probes']:
            # Blackbox probes - usar template network_probe_success
            modules = [t['module'] for t in category_types if t.get('module')]

            query = query_builder.build(
                QUERY_TEMPLATES['network_probe_success'],
                {
                    'modules': modules,
                    'company': company,
                    'site': site
                }
            )

        elif category == 'system-exporters':
            # Node/Windows exporters - usar template node_cpu_usage
            jobs = [t['job_name'] for t in category_types]

            query = query_builder.build(
                QUERY_TEMPLATES['node_cpu_usage'],
                {
                    'jobs': jobs,
                    'time_range': time_range
                }
            )

        elif category == 'database-exporters':
            # Database exporters - query de up status
            jobs = [t['job_name'] for t in category_types]
            query = f"up{{job=~\"{'|'.join(jobs)}\"}}"

        else:
            # Categoria genérica - query up
            jobs = [t['job_name'] for t in category_types]
            query = f"up{{job=~\"{'|'.join(jobs)}\"}}"

        logger.info(f"[MONITORING METRICS] Query PromQL: {query[:100]}...")

        # ==================================================================
        # PASSO 5: Executar query no Prometheus
        # ==================================================================
        prometheus_url = f"http://{server}:9090"

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
        # PASSO 6: Processar resultados
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
            "prometheus_server": server,
            "total": len(formatted_metrics)
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[MONITORING METRICS ERROR] {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# ENDPOINT 3: /monitoring/sync-cache - SINCRONIZAÇÃO FORÇADA
# ============================================================================

@router.post("/sync-cache")
async def sync_monitoring_cache():
    """
    Força sincronização do cache de tipos de monitoramento

    Este endpoint:
    1. Extrai tipos de TODOS os servidores Prometheus via SSH
    2. Invalida cache existente
    3. Salva novos tipos no KV
    4. Retorna status

    IMPORTANTE:
    - Operação pode demorar 20-30 segundos (SSH para múltiplos servidores)
    - Use apenas quando necessário (mudanças em prometheus.yml)
    - Cache normal tem TTL de 5 minutos

    Returns:
        ```json
        {
            "success": true,
            "message": "Cache sincronizado com sucesso",
            "total_types": 45,
            "total_servers": 3,
            "categories": [
                {"category": "network-probes", "count": 8},
                {"category": "system-exporters", "count": 12},
                ...
            ],
            "duration_seconds": 23.5
        }
        ```
    """
    try:
        logger.info("[SYNC CACHE] Iniciando sincronização forçada...")
        start_time = datetime.now()

        # ==================================================================
        # PASSO 1: Importar função de extração
        # ==================================================================
        from api.monitoring_types_dynamic import extract_types_from_prometheus_jobs
        from core.multi_config_manager import MultiConfigManager

        multi_config = MultiConfigManager()

        # ==================================================================
        # PASSO 2: Extrair tipos de todos os servidores
        # ==================================================================
        result_servers = {}
        all_types_dict = {}

        for host in multi_config.hosts:
            server_host = host.hostname

            try:
                logger.info(f"[SYNC CACHE] Extraindo de {server_host}...")

                # Buscar prometheus.yml
                prom_files = multi_config.list_config_files(service='prometheus', hostname=server_host)

                if not prom_files:
                    logger.warning(f"[SYNC CACHE] prometheus.yml não encontrado em {server_host}")
                    continue

                prom_file = prom_files[0]
                config = multi_config.read_config_file(prom_file)

                # Extrair tipos dos jobs
                scrape_configs = config.get('scrape_configs', [])
                types = await extract_types_from_prometheus_jobs(scrape_configs, server_host)

                result_servers[server_host] = {
                    "types": types,
                    "total": len(types)
                }

                # Adicionar ao all_types (deduplicar por id)
                for type_def in types:
                    type_id = type_def['id']
                    if type_id not in all_types_dict:
                        all_types_dict[type_id] = type_def.copy()

            except Exception as e:
                logger.error(f"[SYNC CACHE] Erro em {server_host}: {e}")
                result_servers[server_host] = {
                    "error": str(e),
                    "types": [],
                    "total": 0
                }

        # ==================================================================
        # PASSO 3: Agrupar por categoria
        # ==================================================================
        categories_dict = {}
        for type_def in all_types_dict.values():
            cat = type_def['category']
            if cat not in categories_dict:
                categories_dict[cat] = []
            categories_dict[cat].append(type_def)

        categories = [
            {"category": cat, "types": types_list}
            for cat, types_list in categories_dict.items()
        ]

        # ==================================================================
        # PASSO 4: Preparar dados para cache
        # ==================================================================
        cache_data = {
            "version": "1.0.0",
            "last_updated": datetime.now().isoformat(),
            "ttl_seconds": 300,
            "servers": result_servers,
            "categories": categories,
            "all_types": list(all_types_dict.values()),
            "total_types": len(all_types_dict),
            "total_servers": len(result_servers)
        }

        # ==================================================================
        # PASSO 5: Salvar no KV (invalidando cache)
        # ==================================================================
        await config_manager.put('monitoring-types/cache', cache_data, invalidate_cache=True)

        duration = (datetime.now() - start_time).total_seconds()

        logger.info(f"[SYNC CACHE] ✓ Sincronizado: {cache_data['total_types']} tipos em {duration:.1f}s")

        return {
            "success": True,
            "message": "Cache sincronizado com sucesso",
            "total_types": cache_data['total_types'],
            "total_servers": cache_data['total_servers'],
            "categories": [
                {"category": c['category'], "count": len(c['types'])}
                for c in categories
            ],
            "duration_seconds": round(duration, 2)
        }

    except Exception as e:
        logger.error(f"[SYNC CACHE ERROR] {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
