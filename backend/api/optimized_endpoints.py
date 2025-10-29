"""
Endpoints Otimizados para TODAS as páginas
Sistema de cache inteligente com invalidação automática
"""
from fastapi import APIRouter, Query, HTTPException
from typing import Dict, List, Optional
from core.cache_manager import cache_manager
from core.config import Config
import requests
import time
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/optimized", tags=["optimized"])

# Headers e URL do Consul
CONSUL_HEADERS = {"X-Consul-Token": Config.CONSUL_TOKEN}
CONSUL_URL = f"http://{Config.MAIN_SERVER}:{Config.CONSUL_PORT}/v1"

# TTLs configuráveis por tipo de dados
CACHE_TTL = {
    'exporters': 20,     # Exporters mudam raramente
    'blackbox': 15,      # Blackbox targets mudam moderadamente
    'groups': 30,        # Grupos mudam raramente
    'services': 25,      # Services (geral) mudam moderadamente
}


# ============================================================================
# EXPORTERS OTIMIZADO
# ============================================================================

@router.get("/exporters")
def get_exporters_optimized(
    force_refresh: bool = Query(False, description="Forçar atualização (ignora cache)")
):
    """
    Lista exporters OTIMIZADA

    - Cache de 20 segundos
    - Processamento no backend
    - Retorna ~10-50ms (vs 2-3 segundos)
    """
    start_time = time.time()
    cache_key = "exporters:list"

    # Verificar cache
    if not force_refresh:
        cached = cache_manager.get(cache_key)
        if cached:
            cached['load_time_ms'] = int((time.time() - start_time) * 1000)
            cached['from_cache'] = True
            logger.info(f"✓ Exporters from cache ({cached['load_time_ms']}ms)")
            return cached

    try:
        logger.info("Fetching exporters from Consul...")

        # Buscar serviços agregados
        services_response = requests.get(
            f"{CONSUL_URL}/internal/ui/services",
            headers=CONSUL_HEADERS,
            timeout=10
        )
        services_response.raise_for_status()
        all_services = services_response.json() or []

        # Buscar nodes para mapear endereços
        nodes_response = requests.get(
            f"{CONSUL_URL}/catalog/nodes",
            headers=CONSUL_HEADERS,
            timeout=5
        )
        nodes_response.raise_for_status()
        nodes_list = nodes_response.json() or []
        node_map = {n.get('Node'): n.get('Address') for n in nodes_list if n.get('Node')}

        # Módulos blackbox (para excluir)
        BLACKBOX_MODULES = {'icmp', 'http_2xx', 'http_4xx', 'http_5xx', 'http_post_2xx',
                           'https', 'tcp_connect', 'ssh_banner', 'pop3s_banner', 'irc_banner'}

        # Função para detectar tipo do exporter pelo nome do serviço E TAGS
        def detect_exporter_type(service_name: str, tags: Optional[List[str]] = None) -> str:
            """
            Detecta o tipo de exporter baseado no nome do serviço e tags
            
            Para selfnode_exporter: usa as TAGS para diferenciar:
            - Tag 'linux' → Node Exporter
            - Tag 'windows' → Windows Exporter
            """
            service_lower = service_name.lower()
            tags = tags or []
            tags_lower = [str(t).lower() for t in tags]

            # SELFNODE_EXPORTER: Diferencia por TAG (linux vs windows)
            if 'selfnode' in service_lower:
                logger.info(f"🔍 DEBUG: selfnode detectado! Tags: {tags_lower}")
                if 'windows' in tags_lower:
                    logger.info(f"✅ Tag 'windows' encontrada → Windows Exporter")
                    return 'Windows Exporter'
                elif 'linux' in tags_lower:
                    logger.info(f"✅ Tag 'linux' encontrada → Node Exporter")
                    return 'Node Exporter'
                else:
                    logger.info(f"⚠️ Sem tag linux/windows → SelfNode Exporter")
                    return 'SelfNode Exporter'  # Fallback se não tiver tag
            
            # Outros exporters: detecção por nome
            elif 'node_exporter' in service_lower or 'node-exporter' in service_lower:
                return 'Node Exporter'
            elif 'windows_exporter' in service_lower or 'windows-exporter' in service_lower:
                return 'Windows Exporter'
            elif 'mysql' in service_lower or 'mysqld_exporter' in service_lower:
                return 'MySQL Exporter'
            elif 'postgres' in service_lower or 'postgresql' in service_lower:
                return 'PostgreSQL Exporter'
            elif 'redis_exporter' in service_lower:
                return 'Redis Exporter'
            elif 'mongodb' in service_lower or 'mongo' in service_lower:
                return 'MongoDB Exporter'
            elif 'elasticsearch' in service_lower:
                return 'Elasticsearch Exporter'
            elif 'blackbox_exporter' in service_lower:
                return 'Blackbox Exporter'
            else:
                return 'Other Exporter'

        exporters_data = []
        summary = {'by_type': {}, 'by_env': {}}

        # 🚀 BUSCAR TODAS AS INSTÂNCIAS DE TODOS OS SERVIÇOS
        for svc in all_services:
            if not svc or svc.get('Name') == 'consul':
                continue

            service_name = svc.get('Name', '')

            # Buscar instances deste serviço
            try:
                instances_resp = requests.get(
                    f"{CONSUL_URL}/health/service/{service_name}",
                    headers=CONSUL_HEADERS,
                    timeout=5
                )

                if instances_resp.status_code != 200:
                    continue

                instances = instances_resp.json() or []

                for inst in instances:
                    if not inst:
                        continue

                    svc_data = inst.get('Service', {})
                    if not svc_data:
                        continue

                    node_info = inst.get('Node', {})
                    node_name = node_info.get('Node', 'unknown')
                    meta = svc_data.get('Meta', {}) or {}
                    tags = svc_data.get('Tags', []) or []
                    
                    service_lower = str(svc_data.get('Service', '')).lower()

                    # ❌ EXCLUIR: Blackbox targets (baseado no módulo)
                    module = str(meta.get('module', '')).lower()
                    if module in BLACKBOX_MODULES:
                        continue

                    # ❌ EXCLUIR: Serviços que NÃO são exporters
                    # Verificar se tem '_exporter' ou '-exporter' no nome do serviço
                    if '_exporter' not in service_lower and '-exporter' not in service_lower:
                        logger.debug(f"Ignorando serviço não-exporter: {service_lower}")
                        continue

                    # ✅ INCLUIR: É um exporter válido
                    # Detectar tipo do exporter pelo nome do serviço E TAGS
                    exp_type = detect_exporter_type(svc_data.get('Service', ''), tags)
                    logger.debug(f"Incluindo exporter: {service_lower} com tags {tags} → tipo: {exp_type}")
                    
                    env = meta.get('env', meta.get('ambiente', 'unknown'))

                    exporter_item = {
                        'key': f"{node_name}_{svc_data.get('ID', '')}",
                        'id': svc_data.get('ID', ''),
                        'node': node_name,
                        'nodeAddr': node_map.get(node_name),
                        'service': svc_data.get('Service', ''),
                        'tags': svc_data.get('Tags', []),
                        'address': svc_data.get('Address'),
                        'port': svc_data.get('Port'),
                        'meta': meta,
                        'exporterType': exp_type,
                        'company': meta.get('company'),
                        'project': meta.get('project'),
                        'env': env
                    }

                    exporters_data.append(exporter_item)

                    # Update summary
                    summary['by_type'][exp_type] = summary['by_type'].get(exp_type, 0) + 1
                    summary['by_env'][env] = summary['by_env'].get(env, 0) + 1

            except Exception as e:
                logger.warning(f"Error fetching instances for {svc.get('Name')}: {e}")
                continue

        result = {
            'data': exporters_data,
            'total': len(exporters_data),
            'summary': summary,
            'load_time_ms': int((time.time() - start_time) * 1000),
            'from_cache': False
        }

        # Cache por 20 segundos
        cache_manager.set(cache_key, result, ttl_seconds=CACHE_TTL['exporters'])
        logger.info(f"✓ Exporters fetched in {result['load_time_ms']}ms ({result['total']} items)")

        return result

    except requests.exceptions.RequestException as e:
        logger.error(f"Consul connection error: {e}")
        raise HTTPException(status_code=503, detail=f"Erro ao conectar com Consul: {str(e)}")
    except Exception as e:
        logger.error(f"Error fetching exporters: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Erro: {str(e)}")


# ============================================================================
# BLACKBOX TARGETS OTIMIZADO
# ============================================================================

@router.get("/blackbox-targets")
def get_blackbox_targets_optimized(force_refresh: bool = Query(False)):
    """Lista blackbox targets otimizada - Cache de 15s"""
    start_time = time.time()
    cache_key = "blackbox-targets:list"

    if not force_refresh:
        cached = cache_manager.get(cache_key)
        if cached:
            cached['load_time_ms'] = int((time.time() - start_time) * 1000)
            cached['from_cache'] = True
            logger.info(f"✓ Blackbox targets from cache ({cached['load_time_ms']}ms)")
            return cached

    try:
        logger.info("Fetching blackbox targets from Consul...")

        # Buscar todos os serviços
        services_response = requests.get(
            f"{CONSUL_URL}/internal/ui/services",
            headers=CONSUL_HEADERS,
            timeout=10
        )
        services_response.raise_for_status()
        all_services = services_response.json() or []

        nodes_response = requests.get(
            f"{CONSUL_URL}/catalog/nodes",
            headers=CONSUL_HEADERS,
            timeout=5
        )
        nodes_response.raise_for_status()
        nodes_list = nodes_response.json() or []
        node_map = {n.get('Node'): n.get('Address') for n in nodes_list if n.get('Node')}

        BLACKBOX_MODULES = {'icmp', 'http_2xx', 'http_4xx', 'http_5xx', 'http_post_2xx',
                           'https', 'tcp_connect', 'ssh_banner', 'pop3s_banner', 'irc_banner'}

        blackbox_data = []
        summary = {'by_module': {}, 'by_env': {}}

        for svc in all_services:
            if not svc or svc.get('Name') == 'consul':
                continue

            # Buscar instances
            try:
                instances_resp = requests.get(
                    f"{CONSUL_URL}/health/service/{svc['Name']}",
                    headers=CONSUL_HEADERS,
                    timeout=5
                )

                if instances_resp.status_code != 200:
                    continue

                instances = instances_resp.json() or []

                for inst in instances:
                    if not inst:
                        continue

                    svc_data = inst.get('Service', {})
                    if not svc_data:
                        continue

                    meta = svc_data.get('Meta', {}) or {}
                    module = str(meta.get('module', '')).lower()

                    # Apenas blackbox modules
                    if module not in BLACKBOX_MODULES:
                        continue

                    node_info = inst.get('Node', {})
                    node_name = node_info.get('Node', 'unknown')
                    env = meta.get('env', meta.get('ambiente', 'unknown'))

                    target_item = {
                        'key': f"{node_name}_{svc_data.get('ID', '')}",
                        'id': svc_data.get('ID', ''),
                        'node': node_name,
                        'nodeAddr': node_map.get(node_name),
                        'service': svc_data.get('Service', ''),
                        'tags': svc_data.get('Tags', []),
                        'meta': meta,
                        'module': module,
                        'instance': meta.get('instance'),
                        'company': meta.get('company'),
                        'project': meta.get('project'),
                        'env': env
                    }

                    blackbox_data.append(target_item)

                    summary['by_module'][module] = summary['by_module'].get(module, 0) + 1
                    summary['by_env'][env] = summary['by_env'].get(env, 0) + 1

            except Exception as e:
                logger.warning(f"Error fetching instances for {svc.get('Name')}: {e}")
                continue

        result = {
            'data': blackbox_data,
            'total': len(blackbox_data),
            'summary': summary,
            'load_time_ms': int((time.time() - start_time) * 1000),
            'from_cache': False
        }

        cache_manager.set(cache_key, result, ttl_seconds=CACHE_TTL['blackbox'])
        logger.info(f"✓ Blackbox targets fetched in {result['load_time_ms']}ms ({result['total']} items)")

        return result

    except Exception as e:
        logger.error(f"Error fetching blackbox targets: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Erro: {str(e)}")


# ============================================================================
# SERVICE GROUPS OTIMIZADO
# ============================================================================

@router.get("/service-groups")
def get_service_groups_optimized(force_refresh: bool = Query(False)):
    """Lista grupos de serviços otimizada - Cache de 30s"""
    start_time = time.time()
    cache_key = "service-groups:list"

    if not force_refresh:
        cached = cache_manager.get(cache_key)
        if cached:
            cached['load_time_ms'] = int((time.time() - start_time) * 1000)
            cached['from_cache'] = True
            return cached

    try:
        services_response = requests.get(
            f"{CONSUL_URL}/internal/ui/services",
            headers=CONSUL_HEADERS,
            timeout=10
        )
        services_response.raise_for_status()
        all_services = [s for s in (services_response.json() or []) if s and s.get('Name') != 'consul']

        # Para cada serviço selfnode*, buscar as instâncias para pegar o primeiro node_addr
        enriched_services = []
        for service in all_services:
            service_name = service.get('Name', '')
            
            # Se for selfnode*, buscar primeira instância para pegar node_addr
            if service_name.lower().startswith('selfnode'):
                try:
                    instances_resp = requests.get(
                        f"{CONSUL_URL}/health/service/{service_name}",
                        headers=CONSUL_HEADERS,
                        timeout=3
                    )
                    if instances_resp.status_code == 200:
                        instances = instances_resp.json() or []
                        if instances:
                            # Pegar o endereço do primeiro nó
                            first_instance = instances[0]
                            node_info = first_instance.get('Node', {})
                            node_addr = node_info.get('Address', '')
                            node_name = node_info.get('Node', '')
                            
                            # Adicionar informações ao serviço
                            service['NodeAddress'] = node_addr
                            service['NodeName'] = node_name
                except Exception as e:
                    logger.warning(f"Erro ao buscar node_addr para {service_name}: {e}")
                    service['NodeAddress'] = ''
                    service['NodeName'] = ''
            
            enriched_services.append(service)

        result = {
            'data': enriched_services,
            'total': len(enriched_services),
            'summary': {
                'totalInstances': sum(s.get('InstanceCount', 0) for s in enriched_services),
                'healthy': sum(s.get('ChecksPassing', 0) for s in enriched_services),
                'unhealthy': sum(s.get('ChecksCritical', 0) for s in enriched_services)
            },
            'load_time_ms': int((time.time() - start_time) * 1000),
            'from_cache': False
        }

        cache_manager.set(cache_key, result, ttl_seconds=CACHE_TTL['groups'])
        return result

    except Exception as e:
        logger.error(f"Error fetching service groups: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Erro: {str(e)}")


# ============================================================================
# SERVICES INSTÂNCIAS OTIMIZADO - Todas as instâncias processadas no backend
# ============================================================================

@router.get("/services-instances")
def get_services_instances_optimized(
    force_refresh: bool = Query(False, description="Forçar atualização (ignora cache)"),
    node_addr: Optional[str] = Query(None, description="Filtrar por node")
):
    """
    Lista TODAS as instâncias de TODOS os serviços OTIMIZADA

    - Cache de 25 segundos
    - Processamento TODO no backend
    - Retorna dados prontos para exibição
    - Retorna ~200-500ms (vs 5+ segundos)
    """
    start_time = time.time()
    cache_key = f"services:instances:{node_addr or 'ALL'}"

    # Verificar cache
    if not force_refresh:
        cached = cache_manager.get(cache_key)
        if cached:
            cached['from_cache'] = True
            cached['load_time_ms'] = int((time.time() - start_time) * 1000)
            logger.info(f"✓ Service instances from cache ({cached['load_time_ms']}ms)")
            return cached

    try:
        logger.info(f"Fetching service instances from Consul (node={node_addr or 'ALL'})...")

        # Buscar TODOS os serviços
        services_response = requests.get(
            f"{CONSUL_URL}/internal/ui/services",
            headers=CONSUL_HEADERS,
            timeout=10
        )
        services_response.raise_for_status()
        all_services = services_response.json() or []

        instances_data = []
        summary = {'by_module': {}, 'by_env': {}}

        for svc in all_services:
            if not svc or svc.get('Name') == 'consul':
                continue

            service_name = svc.get('Name', '')

            try:
                # Buscar instâncias deste serviço
                instances_resp = requests.get(
                    f"{CONSUL_URL}/health/service/{service_name}",
                    headers=CONSUL_HEADERS,
                    timeout=5
                )

                if instances_resp.status_code != 200:
                    continue

                instances = instances_resp.json() or []

                for inst in instances:
                    if not inst:
                        continue

                    svc_data = inst.get('Service', {})
                    if not svc_data:
                        continue

                    node_info = inst.get('Node', {})
                    node_name = node_info.get('Node', 'unknown')
                    node_address = node_info.get('Address', '')

                    # Filtrar por node se especificado
                    if node_addr and node_addr != 'ALL':
                        if node_address != node_addr and node_name != node_addr:
                            continue

                    meta = svc_data.get('Meta', {}) or {}
                    module = meta.get('module', '')
                    env = meta.get('env', meta.get('ambiente', 'unknown'))

                    instance_item = {
                        'key': f"{node_name}_{svc_data.get('ID', '')}",
                        'id': svc_data.get('ID', ''),
                        'node': node_name,
                        'nodeAddr': node_address,
                        'service': svc_data.get('Service', ''),
                        'tags': svc_data.get('Tags', []),
                        'address': svc_data.get('Address'),
                        'port': svc_data.get('Port'),
                        'meta': meta,
                        'company': meta.get('company'),
                        'project': meta.get('project'),
                        'env': env,
                        'module': module
                    }

                    instances_data.append(instance_item)

                    # Update summary
                    if module:
                        summary['by_module'][module] = summary['by_module'].get(module, 0) + 1
                    summary['by_env'][env] = summary['by_env'].get(env, 0) + 1

            except Exception as e:
                logger.warning(f"Error fetching instances for {service_name}: {e}")
                continue

        load_ms = int((time.time() - start_time) * 1000)

        result = {
            'data': instances_data,
            'total': len(instances_data),
            'summary': summary,
            'load_time_ms': load_ms,
            'from_cache': False
        }

        # Cache por 25 segundos
        cache_manager.set(cache_key, result, ttl_seconds=25)
        logger.info(f"✓ Service instances fetched ({load_ms}ms) - {len(instances_data)} instances")

        return result

    except requests.exceptions.RequestException as e:
        logger.error(f"Consul connection error: {e}")
        raise HTTPException(status_code=503, detail=f"Erro ao conectar com Consul: {str(e)}")
    except Exception as e:
        logger.error(f"Error fetching service instances: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Erro: {str(e)}")


# ============================================================================
# SERVICES AGREGADOS - Mesma estratégia do TenSunS
# ============================================================================

@router.get("/services")
def get_services_optimized(
    force_refresh: bool = Query(False, description="Forçar atualização (ignora cache)")
):
    """
    Lista serviços AGREGADOS - Usa mesma estratégia do TenSunS

    - Cache de 25 segundos
    - UMA única chamada ao Consul (/internal/ui/services)
    - Processamento mínimo no backend
    - Retorna ~10-50ms (vs 5+ segundos)
    """
    start_time = time.time()
    cache_key = "services:all"

    # Verificar cache
    if not force_refresh:
        cached = cache_manager.get(cache_key)
        if cached:
            cached['from_cache'] = True
            cached['load_time_ms'] = int((time.time() - start_time) * 1000)
            logger.info(f"✓ Services from cache ({cached['load_time_ms']}ms)")
            return cached

    try:
        # 🚀 UMA ÚNICA CHAMADA - Endpoint agregado do Consul (IGUAL AO TENSUNS!)
        logger.info("Fetching services from Consul /internal/ui/services...")
        services_response = requests.get(
            f"{CONSUL_URL}/internal/ui/services",
            headers=CONSUL_HEADERS,
            timeout=10
        )
        services_response.raise_for_status()
        all_services = services_response.json() or []

        # Processar serviços (similar ao TenSunS - bem simples!)
        processed_services = []
        summary_by_datacenter = {}
        summary_by_tag = {}
        total_instances = 0
        total_passing = 0
        total_critical = 0

        for svc in all_services:
            if not svc or svc.get('Name') == 'consul':
                continue

            service_name = svc.get('Name', '')
            datacenter = svc.get('Datacenter', 'unknown')
            instance_count = svc.get('InstanceCount', 0)
            checks_passing = svc.get('ChecksPassing', 0)
            checks_critical = svc.get('ChecksCritical', 0)
            checks_warning = svc.get('ChecksWarning', 0)
            tags = svc.get('Tags', [])
            nodes = list(set(svc.get('Nodes', [])))  # Remove duplicatas

            processed_services.append({
                'Name': service_name,
                'Datacenter': datacenter,
                'InstanceCount': instance_count,
                'ChecksPassing': checks_passing,
                'ChecksCritical': checks_critical,
                'ChecksWarning': checks_warning,
                'Tags': tags,
                'Nodes': nodes,
                'NodesCount': len(nodes),
            })

            # Acumular estatísticas
            total_instances += instance_count
            total_passing += checks_passing
            total_critical += checks_critical

            # Por datacenter
            if datacenter not in summary_by_datacenter:
                summary_by_datacenter[datacenter] = 0
            summary_by_datacenter[datacenter] += instance_count

            # Por tag (primeira tag como categoria principal)
            if tags:
                main_tag = tags[0]
                if main_tag not in summary_by_tag:
                    summary_by_tag[main_tag] = 0
                summary_by_tag[main_tag] += instance_count

        load_ms = int((time.time() - start_time) * 1000)

        result = {
            'data': processed_services,
            'total': len(processed_services),
            'summary': {
                'total_services': len(processed_services),
                'total_instances': total_instances,
                'total_passing': total_passing,
                'total_critical': total_critical,
                'by_datacenter': summary_by_datacenter,
                'by_tag': summary_by_tag,
            },
            'load_time_ms': load_ms,
            'from_cache': False,
        }

        # Salvar no cache
        cache_manager.set(cache_key, result, ttl_seconds=25)
        logger.info(f"✓ Services loaded fresh ({load_ms}ms) - {len(processed_services)} services")

        return result

    except requests.RequestException as e:
        logger.error(f"Error fetching services: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching from Consul: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error in get_services_optimized: {e}")
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


# ============================================================================
# BLACKBOX GROUPS OTIMIZADO
# ============================================================================

@router.get("/blackbox-groups")
def get_blackbox_groups_optimized(
    force_refresh: bool = Query(False, description="Forçar atualização (ignora cache)")
):
    """
    Lista Blackbox Groups OTIMIZADA

    - Cache de 30 segundos
    - Busca direto do KV store
    - Processamento no backend
    """
    start_time = time.time()
    cache_key = "blackbox-groups:list"

    # Verificar cache
    if not force_refresh:
        cached = cache_manager.get(cache_key)
        if cached:
            cached['from_cache'] = True
            cached['load_time_ms'] = int((time.time() - start_time) * 1000)
            logger.info(f"✓ Blackbox Groups from cache ({cached['load_time_ms']}ms)")
            return cached

    try:
        # Buscar do KV store
        kv_response = requests.get(
            f"{CONSUL_URL}/kv/blackbox/groups?recurse=true",
            headers=CONSUL_HEADERS,
            timeout=5
        )

        groups = []
        if kv_response.status_code == 200:
            kv_data = kv_response.json() or []
            for item in kv_data:
                try:
                    import base64
                    import json
                    key = item.get('Key', '')
                    if '/' in key:
                        group_id = key.split('/')[-1]
                        value_b64 = item.get('Value', '')
                        if value_b64:
                            value_str = base64.b64decode(value_b64).decode('utf-8')
                            group_data = json.loads(value_str)
                            group_data['id'] = group_id
                            groups.append(group_data)
                except Exception as e:
                    logger.warning(f"Error parsing group {key}: {e}")
                    continue

        load_ms = int((time.time() - start_time) * 1000)

        result = {
            'data': groups,
            'total': len(groups),
            'load_time_ms': load_ms,
            'from_cache': False,
        }

        # Salvar no cache
        cache_manager.set(cache_key, result, ttl_seconds=30)
        logger.info(f"✓ Blackbox Groups loaded ({load_ms}ms) - {len(groups)} groups")

        return result

    except Exception as e:
        logger.error(f"Error fetching blackbox groups: {e}")
        raise HTTPException(status_code=500, detail=f"Erro: {str(e)}")


# ============================================================================
# SERVICE PRESETS OTIMIZADO
# ============================================================================

@router.get("/presets")
def get_presets_optimized(
    force_refresh: bool = Query(False, description="Forçar atualização (ignora cache)"),
    category: Optional[str] = Query(None, description="Filtrar por categoria")
):
    """
    Lista Service Presets OTIMIZADA

    - Cache de 30 segundos
    - Busca direto do KV store
    - Processamento no backend
    """
    start_time = time.time()
    cache_key = f"presets:list:{category or 'all'}"

    # Verificar cache
    if not force_refresh:
        cached = cache_manager.get(cache_key)
        if cached:
            cached['from_cache'] = True
            cached['load_time_ms'] = int((time.time() - start_time) * 1000)
            logger.info(f"✓ Presets from cache ({cached['load_time_ms']}ms)")
            return cached

    try:
        # Buscar do KV store
        kv_response = requests.get(
            f"{CONSUL_URL}/kv/service/presets?recurse=true",
            headers=CONSUL_HEADERS,
            timeout=5
        )

        presets = []
        if kv_response.status_code == 200:
            kv_data = kv_response.json() or []
            for item in kv_data:
                try:
                    import base64
                    import json
                    key = item.get('Key', '')
                    if '/' in key:
                        preset_id = key.split('/')[-1]
                        value_b64 = item.get('Value', '')
                        if value_b64:
                            value_str = base64.b64decode(value_b64).decode('utf-8')
                            preset_data = json.loads(value_str)
                            preset_data['id'] = preset_id

                            # Filtrar por categoria se especificado
                            if category and preset_data.get('category') != category:
                                continue

                            presets.append(preset_data)
                except Exception as e:
                    logger.warning(f"Error parsing preset {key}: {e}")
                    continue

        load_ms = int((time.time() - start_time) * 1000)

        result = {
            'data': presets,
            'total': len(presets),
            'load_time_ms': load_ms,
            'from_cache': False,
        }

        # Salvar no cache
        cache_manager.set(cache_key, result, ttl_seconds=30)
        logger.info(f"✓ Presets loaded ({load_ms}ms) - {len(presets)} presets")

        return result

    except Exception as e:
        logger.error(f"Error fetching presets: {e}")
        raise HTTPException(status_code=500, detail=f"Erro: {str(e)}")


# ============================================================================
# CLEAR CACHE
# ============================================================================

@router.post("/clear-cache")
def clear_cache(cache_type: Optional[str] = Query(None)):
    """
    Limpa cache

    Tipos:
    - exporters
    - blackbox-targets
    - service-groups
    - all (padrão)

    **Chame após CREATE/UPDATE/DELETE para invalidar cache**
    """
    cache_manager.clear()
    return {"success": True, "message": f"Cache limpo: {cache_type or 'all'}"}
