"""
API endpoints para gerenciamento de nós
"""
from fastapi import APIRouter, HTTPException
from typing import List, Dict
from core.consul_manager import ConsulManager
from core.config import Config

router = APIRouter()

@router.get("/", include_in_schema=True)
@router.get("")
async def get_nodes():
    """Retorna todos os nós do cluster"""
    try:
        consul = ConsulManager()
        members = await consul.get_members()

        # Enriquecer com informações adicionais
        for member in members:
            # Testar conectividade
            member["services_count"] = 0
            try:
                temp_consul = ConsulManager(host=member["addr"])
                services = await temp_consul.get_services()
                member["services_count"] = len(services)
            except:
                pass

        return {
            "success": True,
            "data": members,
            "total": len(members),
            "main_server": Config.MAIN_SERVER
        }
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