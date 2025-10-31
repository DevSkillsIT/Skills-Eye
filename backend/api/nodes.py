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
    """Retorna apenas os nomes únicos de serviços de um nó específico

    Útil para popular dropdown de tipos de serviços baseado no nó selecionado.
    Retorna apenas nomes de serviços únicos (ex: selfnode_exporter, windows_exporter, etc)
    """
    try:
        consul = ConsulManager(host=node_addr)
        service_names = await consul.get_service_names()

        return {
            "success": True,
            "node": node_addr,
            "data": service_names,
            "total": len(service_names)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))