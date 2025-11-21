"""
API endpoints para gerenciamento de nós
"""
from fastapi import APIRouter, HTTPException
from typing import List, Dict, Optional
from core.consul_manager import ConsulManager
from core.config import Config
from core.cache_manager import get_cache  # SPRINT 2: LocalCache global
import asyncio
import time

router = APIRouter(tags=["Nodes"])

# SPRINT 2 (2025-11-15): Migração para LocalCache global
# REMOVIDO: _nodes_cache, _nodes_cache_time (variáveis globais)
# NOVO: Usar LocalCache global para integração com Cache Management
cache = get_cache(ttl_seconds=60)

@router.get("/", include_in_schema=True)
@router.get("")
async def get_nodes():
    """Retorna todos os nós do cluster com cache de 30s"""
    
    # SPRINT 2: Usar LocalCache global
    cache_key = "nodes:list:all"
    
    # Verificar cache
    cached = await cache.get(cache_key)
    if cached is not None:
        return cached

    try:
        consul = ConsulManager()
        members = await consul.get_members()

        # Buscar mapeamento de sites do KV
        from core.kv_manager import KVManager
        kv = KVManager()
        sites_data = await kv.get_json('skills/eye/metadata/sites')

        # Criar mapa IP → site_name
        sites_map = {}
        if sites_data:
            # Estrutura KV: data.data.sites (dois níveis de 'data')
            inner_data = sites_data.get('data', {})
            sites_list = inner_data.get('sites', []) if isinstance(inner_data, dict) else []
            
            for site in sites_list:
                if isinstance(site, dict):
                    ip = site.get('prometheus_instance') or site.get('prometheus_host')
                    name = site.get('name') or site.get('code', 'unknown')
                    if ip:
                        sites_map[ip] = name

        # OTIMIZAÇÃO: Enriquecer em paralelo usando asyncio.gather para evitar timeouts
        async def get_service_count(member: dict) -> dict:
            """Conta serviços de um nó específico com timeout de 5s"""
            member["services_count"] = 0
            # Adicionar site_name baseado no IP do sites.json
            # Se não encontrar no mapeamento, usa "Não mapeado" ao invés de mostrar IP
            member["site_name"] = sites_map.get(member["addr"], "Não mapeado")
            try:
                temp_consul = ConsulManager(host=member["addr"])
                # Timeout individual de 5s por nó (aumentado de 3s)
                services = await asyncio.wait_for(
                    temp_consul.get_services(),
                    timeout=5.0
                )
                member["services_count"] = len(services)
            except Exception as e:
                # Silencioso - se falhar, deixa services_count = 0
                pass
            return member

        # Executar todas as requisições em paralelo
        enriched_members = await asyncio.gather(*[get_service_count(m) for m in members])

        result = {
            "success": True,
            "data": enriched_members,
            "total": len(enriched_members),
            "main_server": Config.MAIN_SERVER
        }

        # SPRINT 2: Atualizar LocalCache global (TTL 30s)
        await cache.set(cache_key, result, ttl=30)

        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{node_addr}/services")
async def get_node_services(node_addr: str):
    """Retorna serviços de um nó específico"""
    try:
        consul = ConsulManager()
        services = await consul.get_services(node_addr)

        return {
            "success": True,
            "node": node_addr,
            "services": services,
            "total": len(services)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{node_addr}/service-names")
async def get_node_service_names(node_addr: str):
    """Retorna apenas os nomes únicos de serviços REGISTRADOS em um nó específico

    Útil para popular dropdown de tipos de serviços baseado no nó selecionado.
    Retorna apenas nomes de serviços únicos (ex: selfnode_exporter, windows_exporter, node_exporter_rio, etc)

    IMPORTANTE: Conecta ao Consul e busca serviços do catálogo que estão registrados neste nó.
    node_addr pode ser IP (172.16.1.26) ou hostname (glpi-grafana-prometheus)
    """
    try:
        # Conectar ao Consul
        consul = ConsulManager()

        # Primeiro, precisamos descobrir o node_name correspondente ao node_addr
        # Buscar todos os nós do catálogo
        all_nodes = await consul.get_nodes()

        # Encontrar o nó que corresponde ao node_addr
        target_node_name = None
        for node in all_nodes:
            # node tem: {"ID", "Node", "Address", "Datacenter", ...}
            if node.get("Address") == node_addr or node.get("Node") == node_addr:
                target_node_name = node.get("Node")
                break

        if not target_node_name:
            # Se não encontrou, assume que node_addr já é o nome
            target_node_name = node_addr

        # Buscar serviços deste nó específico usando /catalog/node/{node_name}
        node_data = await consul.get_node_services(target_node_name)

        # Extrair nomes únicos de serviços
        service_names_set = set()

        # node_data tem formato: {"Node": {...}, "Services": {...}}
        services_dict = node_data.get("Services", {})
        for service_id, service_info in services_dict.items():
            # service_info tem: {"ID", "Service", "Tags", "Address", "Port", ...}
            service_name = service_info.get("Service", "")
            if service_name and service_name != "consul":
                service_names_set.add(service_name)

        service_names = sorted(list(service_names_set))

        return {
            "success": True,
            "node": node_addr,
            "node_name": target_node_name,
            "data": service_names,
            "total": len(service_names)
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))