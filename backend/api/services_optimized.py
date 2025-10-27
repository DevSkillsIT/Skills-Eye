"""
API otimizada de Serviços
Cache inteligente + processamento no backend
"""
from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel
from typing import Dict, List, Optional
from core.cache_manager import cache_manager
from core.config import Config
import requests
import time

router = APIRouter(prefix="/services-optimized", tags=["services-optimized"])

# Headers e URL do Consul
CONSUL_HEADERS = {"X-Consul-Token": Config.CONSUL_TOKEN}
CONSUL_URL = f"http://{Config.MAIN_SERVER}:{Config.CONSUL_PORT}/v1"

# TTL do cache: 15 segundos (dados relativamente frescos)
CACHE_TTL = 15


class ServiceItem(BaseModel):
    """Item de serviço processado"""
    key: str
    id: str
    node: str
    node_addr: Optional[str]
    service: str
    tags: List[str]
    address: Optional[str]
    port: Optional[int]
    meta: Dict
    module: Optional[str]
    instance: Optional[str]
    company: Optional[str]
    project: Optional[str]
    env: Optional[str]


class ServicesResponse(BaseModel):
    """Resposta otimizada de serviços"""
    data: List[ServiceItem]
    total: int
    summary: Dict[str, int]
    load_time_ms: int
    from_cache: bool


@router.get("/list", response_model=ServicesResponse)
def get_services_optimized(
    node: Optional[str] = Query(None, description="Filtrar por node"),
    search: Optional[str] = Query(None, description="Busca por nome/ID"),
    force_refresh: bool = Query(False, description="Forçar atualização (ignora cache)")
):
    """
    Lista serviços de forma OTIMIZADA

    - Cache de 15 segundos
    - Processamento no backend
    - Filtros aplicados no backend
    - Retorna dados prontos para exibição
    """
    start_time = time.time()

    # Chave de cache baseada nos filtros
    cache_key = f"services:list:{node or 'all'}:{search or 'all'}"

    # Tentar cache (se não forçar refresh)
    if not force_refresh:
        cached_data = cache_manager.get(cache_key)
        if cached_data:
            cached_data['load_time_ms'] = int((time.time() - start_time) * 1000)
            cached_data['from_cache'] = True
            return cached_data

    try:
        # Buscar TODOS os nodes e serviços (1 chamada)
        nodes_response = requests.get(
            f"{CONSUL_URL}/catalog/nodes",
            headers=CONSUL_HEADERS,
            timeout=5
        )
        nodes_response.raise_for_status()
        nodes_list = nodes_response.json()

        # Mapear node -> address
        node_address_map = {n['Node']: n['Address'] for n in nodes_list}

        # Buscar serviços de todos os nodes ou de um específico
        all_services = []

        if node:
            # Buscar de um node específico
            services_response = requests.get(
                f"{CONSUL_URL}/catalog/node/{node}",
                headers=CONSUL_HEADERS,
                timeout=5
            )
            services_response.raise_for_status()
            node_data = services_response.json()
            services = node_data.get('Services', {})

            for svc_id, svc in services.items():
                if svc.get('Service') == 'consul':
                    continue
                all_services.append({
                    'node': node,
                    'node_addr': node_address_map.get(node),
                    **svc
                })
        else:
            # Buscar de todos os nodes (paralelo simulado - sequencial é mais estável)
            for node_info in nodes_list:
                node_name = node_info['Node']
                try:
                    services_response = requests.get(
                        f"{CONSUL_URL}/catalog/node/{node_name}",
                        headers=CONSUL_HEADERS,
                        timeout=3
                    )
                    if services_response.status_code == 200:
                        node_data = services_response.json()
                        services = node_data.get('Services', {})

                        for svc_id, svc in services.items():
                            if svc.get('Service') == 'consul':
                                continue
                            all_services.append({
                                'node': node_name,
                                'node_addr': node_address_map.get(node_name),
                                **svc
                            })
                except:
                    continue

        # Processar serviços
        processed_services = []
        summary = {'total': 0, 'by_env': {}, 'by_module': {}}

        for svc in all_services:
            meta = svc.get('Meta', {}) or {}

            # Aplicar filtro de busca (se houver)
            if search:
                search_lower = search.lower()
                service_name = str(svc.get('Service', '')).lower()
                service_id = str(svc.get('ID', '')).lower()

                if search_lower not in service_name and search_lower not in service_id:
                    continue

            item = ServiceItem(
                key=f"{svc.get('Node', '')}_{svc.get('ID', '')}",
                id=svc.get('ID', ''),
                node=svc.get('node', ''),
                node_addr=svc.get('node_addr'),
                service=svc.get('Service', ''),
                tags=svc.get('Tags', []),
                address=svc.get('Address'),
                port=svc.get('Port'),
                meta=meta,
                module=meta.get('module'),
                instance=meta.get('instance'),
                company=meta.get('company'),
                project=meta.get('project'),
                env=meta.get('env', meta.get('ambiente', 'unknown'))
            )

            processed_services.append(item)

            # Summary
            summary['total'] += 1
            env = item.env or 'unknown'
            summary['by_env'][env] = summary['by_env'].get(env, 0) + 1

            if item.module:
                summary['by_module'][item.module] = summary['by_module'].get(item.module, 0) + 1

        response_data = {
            'data': [s.dict() for s in processed_services],
            'total': len(processed_services),
            'summary': summary,
            'load_time_ms': int((time.time() - start_time) * 1000),
            'from_cache': False
        }

        # Cachear por 15 segundos
        cache_manager.set(cache_key, response_data, ttl_seconds=CACHE_TTL)

        return response_data

    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=503, detail=f"Erro ao conectar com Consul: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao buscar serviços: {str(e)}")


@router.post("/clear-cache")
def clear_services_cache():
    """
    Limpa TODOS os caches de serviços
    Útil após criar/editar/deletar serviços
    """
    # Limpar cache com padrão "services:*"
    cache_manager.clear()  # Por enquanto limpa tudo (podemos melhorar depois)
    return {"success": True, "message": "Cache de serviços limpo"}
