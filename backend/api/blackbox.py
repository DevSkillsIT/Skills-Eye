"""
FastAPI router for blackbox target management with enhanced features.
Includes group management, bulk operations, and KV-based configuration.
"""
import logging
from fastapi import APIRouter, File, HTTPException, Query, UploadFile, Body
from fastapi.responses import PlainTextResponse
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

from core.blackbox_manager import BlackboxManager
from .models import (
    BlackboxDeleteRequest,
    BlackboxTarget,
    BlackboxUpdateRequest,
)

logger = logging.getLogger(__name__)

router = APIRouter()


# ============================================================================
# Enhanced Request Models
# ============================================================================

class BlackboxTargetEnhanced(BaseModel):
    """Enhanced blackbox target with additional fields"""
    module: str
    company: str
    project: str
    env: str
    name: str
    instance: str
    group: Optional[str] = None
    labels: Optional[Dict[str, str]] = None
    interval: str = "30s"
    timeout: str = "10s"
    enabled: bool = True
    notes: Optional[str] = None


class BlackboxGroupCreate(BaseModel):
    """Request to create a blackbox target group"""
    id: str = Field(..., description="Unique group identifier")
    name: str = Field(..., description="Friendly group name")
    filters: Optional[Dict[str, str]] = Field(None, description="Auto-include filters")
    labels: Optional[Dict[str, str]] = Field(None, description="Labels to apply to members")
    description: Optional[str] = None


class BulkEnableDisableRequest(BaseModel):
    """Request to enable/disable multiple targets"""
    group_id: Optional[str] = None
    target_ids: Optional[List[str]] = None
    enabled: bool


@router.get("/", include_in_schema=True)
async def list_targets(
    module: Optional[str] = Query(None, description="Filter by module"),
    company: Optional[str] = Query(None, description="Filter by company"),
    project: Optional[str] = Query(None, description="Filter by project"),
    env: Optional[str] = Query(None, description="Filter by environment"),
    group: Optional[str] = Query(None, description="Filter by group"),
    node: Optional[str] = Query(None, description="Filter by Consul node"),
):
    manager = BlackboxManager()
    data = await manager.list_targets(module, company, project, env, group, node)
    return {"success": True, **data}


@router.get("/summary", include_in_schema=True)
async def list_all_targets():
    manager = BlackboxManager()
    data = await manager.list_all_targets()
    return {"success": True, **data}


@router.post("/", include_in_schema=True)
async def create_target(target: BlackboxTarget):
    manager = BlackboxManager()
    success, reason, detail = await manager.add_target(
        module=target.module,
        company=target.company,
        project=target.project,
        env=target.env,
        name=target.name,
        instance=target.instance,
        group=target.group,
        labels=target.labels,
        interval=target.interval or "30s",
        timeout=target.timeout or "10s",
        enabled=target.enabled,
        notes=target.notes,
        user="system",
    )

    if success:
        return {
            "success": True,
            "message": "Blackbox target created",
            "service_id": detail,
        }

    status_map = {
        "validation_error": 400,
        "duplicate": 409,
        "consul_error": 502,
    }
    status_code = status_map.get(reason, 500)
    raise HTTPException(status_code=status_code, detail=detail or reason)


@router.put("/", include_in_schema=True)
async def update_target(request: BlackboxUpdateRequest):
    manager = BlackboxManager()
    success, detail = await manager.update_target(
        request.current.model_dump(),
        request.replacement.model_dump(),
    )

    if success:
        return {"success": True, "message": "Blackbox target updated", "service_id": detail}

    raise HTTPException(status_code=500, detail=detail)


@router.delete("/", include_in_schema=True)
async def delete_target(request: BlackboxDeleteRequest):
    """
    Remove um target do Consul usando service_id diretamente.

    Estratégia:
    1. Se node_addr fornecido → tenta /agent/service/deregister no agente
    2. Se falhar ou não fornecido → usa /catalog/deregister (força remoção)
    """
    logger.info(f"[DELETE] service_id='{request.service_id}', node_addr='{request.node_addr}', datacenter='{request.datacenter}'")

    from core.consul_manager import ConsulManager
    from core.kv_manager import KVManager

    consul = ConsulManager()
    kv = KVManager(consul)

    try:
        # ========================================================================
        # MÉTODO 1: /agent/service/deregister (RECOMENDADO)
        # ========================================================================
        if request.node_addr:
            logger.info(f"[DELETE MÉTODO 1] Tentando /agent/service/deregister no agente {request.node_addr}...")
            logger.info(f"[DELETE MÉTODO 1] URL: http://{request.node_addr}:8500/v1/agent/service/deregister/{request.service_id} (URL-encoded)")

            success = await consul.deregister_service(request.service_id, request.node_addr)

            if success:
                logger.info(f"[DELETE MÉTODO 1] ✅ SUCESSO! Removido via agent no {request.node_addr}")
                # Limpar KV também
                await kv.delete_blackbox_target(request.service_id)
                await kv.log_audit_event(
                    action="DELETE",
                    resource_type="blackbox_target",
                    resource_id=request.service_id,
                    user="web-user",
                    details={"method": "agent", "node": request.node_addr}
                )
                return {"success": True, "message": "✅ Método 1: Removido via agent", "service_id": request.service_id}
            else:
                logger.warning(f"[DELETE MÉTODO 1] ❌ FALHOU! Agent deregister não funcionou no {request.node_addr}")
                logger.info(f"[DELETE FAILOVER] Iniciando Método 2 (catalog deregister)...")
        else:
            logger.info(f"[DELETE] node_addr não fornecido, pulando Método 1")

        # ========================================================================
        # MÉTODO 2: /catalog/deregister (FALLBACK - força remoção)
        # ========================================================================
        logger.info(f"[DELETE MÉTODO 2] Usando /catalog/deregister (fallback)...")

        # Passo 2.1: Usar dados fornecidos pelo frontend (sem extrair nada "na unha")
        import urllib.parse
        from httpx import AsyncClient

        node_name = request.node_name
        datacenter = request.datacenter  # Usa o que vier do frontend (None se não fornecido)

        # catalog/deregister EXIGE Node + Datacenter. Se faltar algum, buscar via service_name
        if not node_name or not datacenter:
            if not request.service_name:
                logger.error(f"[DELETE MÉTODO 2] ❌ ERRO: Faltam dados! Precisa de (node_name + datacenter) OU service_name")
                raise HTTPException(
                    status_code=400,
                    detail="Método 2 requer (node_name + datacenter) OU service_name para buscar os dados"
                )

            # Buscar node via /health/service usando service_name fornecido
            url = f"{consul.base_url}/health/service/{urllib.parse.quote(request.service_name)}"
            headers = {"X-Consul-Token": consul.token} if consul.token else {}

            logger.info(f"[DELETE MÉTODO 2] Passo 1: Buscando node via GET {url} (service_name='{request.service_name}', dc={datacenter or 'default'})")

            async with AsyncClient() as client:
                # Se datacenter não fornecido, Consul usa o datacenter padrão do agente
                params = {"dc": datacenter} if datacenter else None
                resp = await client.get(url, headers=headers, params=params)
                resp.raise_for_status()
                health_data = resp.json()

                # Encontrar o registro com esse service_id
                for entry in health_data:
                    if entry.get("Service", {}).get("ID") == request.service_id:
                        node_name = entry.get("Node", {}).get("Node")
                        datacenter = entry.get("Node", {}).get("Datacenter")  # Pega do Consul
                        logger.info(f"[DELETE MÉTODO 2] Encontrado: Node='{node_name}', Datacenter='{datacenter}'")
                        break

                if not node_name:
                    logger.error(f"[DELETE MÉTODO 2] ❌ Service ID '{request.service_id}' NÃO encontrado no serviço '{request.service_name}'!")
                    raise HTTPException(status_code=404, detail=f"Service ID '{request.service_id}' não encontrado")
        else:
            logger.info(f"[DELETE MÉTODO 2] Usando dados fornecidos: node_name='{node_name}', datacenter='{datacenter or 'default'}')")

            # Passo 2.2: Fazer PUT /catalog/deregister
            catalog_url = f"{consul.base_url}/catalog/deregister"
            payload = {
                "Datacenter": datacenter,
                "Node": node_name,
                "ServiceID": request.service_id
            }
            logger.info(f"[DELETE MÉTODO 2] Passo 2: Enviando PUT {catalog_url}")
            logger.info(f"[DELETE MÉTODO 2] Payload: {payload}")

            resp2 = await client.put(catalog_url, json=payload, headers=headers)
            resp2.raise_for_status()

            logger.info(f"[DELETE MÉTODO 2] ✅ SUCESSO! Removido via catalog")

            # Limpar KV também
            await kv.delete_blackbox_target(request.service_id)
            await kv.log_audit_event(
                action="DELETE",
                resource_type="blackbox_target",
                resource_id=request.service_id,
                user="web-user",
                details={"method": "catalog", "node": node_name, "datacenter": datacenter}
            )

            return {"success": True, "message": "✅ Método 2: Removido via catalog (fallback)", "service_id": request.service_id}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[DELETE] Exceção: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/import", include_in_schema=True)
async def import_targets(file: UploadFile = File(...)):
    contents = await file.read()
    manager = BlackboxManager()

    filename = file.filename or ""
    if filename.lower().endswith(".csv"):
        result = await manager.import_from_csv(contents)
    elif filename.lower().endswith((".xlsx", ".xlsm", ".xls")):
        try:
            result = await manager.import_from_excel(contents)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    else:
        raise HTTPException(status_code=400, detail="Unsupported file type. Use CSV or XLSX.")

    return {
        "success": True,
        "message": f"Imported {result['created']} targets",
        "summary": result,
    }


@router.get("/config/rules", response_class=PlainTextResponse, include_in_schema=True)
async def get_rules_snippet():
    return BlackboxManager.get_rules_snippet()


@router.get("/config/blackbox", response_class=PlainTextResponse, include_in_schema=True)
async def get_blackbox_config():
    return BlackboxManager.get_blackbox_config_snippet()


@router.get("/config/prometheus", response_class=PlainTextResponse, include_in_schema=True)
async def get_prometheus_config(
    consul_server: Optional[str] = Query(None, description="Override Consul server host:port"),
    consul_token: Optional[str] = Query(None, description="Override Consul ACL token"),
):
    return BlackboxManager.get_prometheus_config_snippet(consul_server, consul_token)


# ============================================================================
# Group Management Endpoints
# ============================================================================

@router.post("/groups", include_in_schema=True)
async def create_group(group: BlackboxGroupCreate, user: str = Query("system", description="User creating group")):
    """Create a new blackbox target group for organization"""
    manager = BlackboxManager()

    success, message = await manager.create_group(
        group_id=group.id,
        name=group.name,
        filters=group.filters,
        labels=group.labels,
        description=group.description,
        user=user
    )

    if success:
        return {"success": True, "message": message, "group_id": group.id}

    raise HTTPException(status_code=500, detail=message)


@router.get("/groups", include_in_schema=True)
async def list_groups():
    """List all blackbox target groups"""
    manager = BlackboxManager()
    groups = await manager.list_groups()

    return {
        "success": True,
        "groups": groups,
        "total": len(groups)
    }


@router.get("/groups/{group_id}", include_in_schema=True)
async def get_group(group_id: str):
    """Get a specific group and its members"""
    manager = BlackboxManager()

    group = await manager.get_group(group_id)
    if not group:
        raise HTTPException(status_code=404, detail=f"Group '{group_id}' not found")

    members = await manager.get_group_members(group_id)

    return {
        "success": True,
        "group": group,
        "members": members,
        "member_count": len(members)
    }


@router.post("/bulk/enable-disable", include_in_schema=True)
async def bulk_enable_disable(
    request: BulkEnableDisableRequest,
    user: str = Query("system", description="User performing operation")
):
    """Enable or disable multiple targets (by group or explicit list)"""
    manager = BlackboxManager()

    if not request.group_id and not request.target_ids:
        raise HTTPException(
            status_code=400,
            detail="Either group_id or target_ids must be provided"
        )

    result = await manager.bulk_enable_disable(
        group_id=request.group_id,
        target_ids=request.target_ids,
        enabled=request.enabled,
        user=user
    )

    return {
        "success": True,
        "message": f"{'Enabled' if request.enabled else 'Disabled'} {result['success_count']} targets",
        "summary": result
    }


# ============================================================================
# Enhanced Target Creation (with groups, labels, etc.)
# ============================================================================

@router.post("/enhanced", include_in_schema=True)
async def create_target_enhanced(
    target: BlackboxTargetEnhanced,
    user: str = Query("system", description="User creating target")
):
    """Create a blackbox target with enhanced features (groups, labels, intervals)"""
    manager = BlackboxManager()

    success, reason, detail = await manager.add_target(
        module=target.module,
        company=target.company,
        project=target.project,
        env=target.env,
        name=target.name,
        instance=target.instance,
        group=target.group,
        labels=target.labels,
        interval=target.interval,
        timeout=target.timeout,
        enabled=target.enabled,
        notes=target.notes,
        user=user
    )

    if success:
        return {
            "success": True,
            "message": "Blackbox target created with enhanced features",
            "service_id": detail
        }

    status_map = {
        "validation_error": 400,
        "duplicate": 409,
        "consul_error": 502,
    }
    status_code = status_map.get(reason, 500)
    raise HTTPException(status_code=status_code, detail=detail or reason)
