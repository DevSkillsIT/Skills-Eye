"""
Additional Consul insights endpoints inspired by TenSunS views.
Provide host metrics and service overview data for UI dashboards.
"""
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from core.consul_manager import ConsulManager

router = APIRouter()


@router.get("/hosts", include_in_schema=True)
async def get_consul_host_metrics(
    node_addr: Optional[str] = Query(
        None,
        description="Specific Consul agent address to query. Default is the main server.",
    ),
):
    manager = ConsulManager(host=node_addr) if node_addr else ConsulManager()
    data = await manager.get_agent_host_info()

    if not data:
        raise HTTPException(status_code=502, detail="Falha ao obter metricas do host Consul")

    return {"success": True, **data}


@router.get("/services/overview", include_in_schema=True)
async def get_consul_services_overview():
    manager = ConsulManager()
    overview = await manager.get_services_overview()
    return {
        "success": True,
        "services": overview or [],
    }
