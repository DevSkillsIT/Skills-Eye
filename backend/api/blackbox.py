"""
FastAPI router for blackbox target management with enhanced features.
Includes group management, bulk operations, and KV-based configuration.
"""
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
    manager = BlackboxManager()
    success, detail = await manager.delete_target(
        request.module,
        request.company,
        request.project,
        request.env,
        request.name,
        user="system",
    )

    if success:
        return {"success": True, "message": "Blackbox target removed", "service_id": detail}

    raise HTTPException(status_code=500, detail=detail)


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
