"""
Service Presets API
Endpoints for managing reusable service registration templates.
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from core.service_preset_manager import ServicePresetManager

router = APIRouter()


# ============================================================================
# Request Models
# ============================================================================

class PresetCreate(BaseModel):
    """Request to create a service preset"""
    id: str = Field(..., description="Unique preset identifier")
    name: str = Field(..., description="Friendly preset name")
    service_name: str = Field(..., description="Consul service name")
    port: Optional[int] = Field(None, description="Default port")
    tags: Optional[List[str]] = Field(None, description="Default tags")
    meta_template: Optional[Dict[str, str]] = Field(None, description="Metadata template with variables")
    checks: Optional[List[Dict[str, Any]]] = Field(None, description="Health check definitions")
    description: Optional[str] = Field(None, description="Preset description")
    category: str = Field("custom", description="Category (exporter, application, database, etc.)")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "node-exporter-linux",
                "name": "Node Exporter (Linux)",
                "service_name": "node_exporter",
                "port": 9100,
                "tags": ["monitoring", "linux"],
                "meta_template": {
                    "env": "${env}",
                    "datacenter": "${datacenter:unknown}",
                    "hostname": "${hostname}"
                },
                "checks": [{
                    "HTTP": "http://${address}:${port}/metrics",
                    "Interval": "30s"
                }],
                "description": "Node Exporter for Linux",
                "category": "exporter"
            }
        }


class PresetUpdate(BaseModel):
    """Request to update a preset"""
    name: Optional[str] = None
    service_name: Optional[str] = None
    port: Optional[int] = None
    tags: Optional[List[str]] = None
    meta_template: Optional[Dict[str, str]] = None
    checks: Optional[List[Dict[str, Any]]] = None
    description: Optional[str] = None
    category: Optional[str] = None


class RegisterFromPreset(BaseModel):
    """Request to register a service from preset"""
    preset_id: str = Field(..., description="Preset to use")
    variables: Dict[str, str] = Field(..., description="Variable substitutions")
    node_addr: Optional[str] = Field(None, description="Specific node address")

    class Config:
        json_schema_extra = {
            "example": {
                "preset_id": "node-exporter-linux",
                "variables": {
                    "address": "10.0.0.5",
                    "env": "prod",
                    "datacenter": "palmas",
                    "hostname": "web-server-01"
                },
                "node_addr": None
            }
        }


# ============================================================================
# Preset CRUD Endpoints
# ============================================================================

@router.post("/", include_in_schema=True)
async def create_preset(
    preset: PresetCreate,
    user: str = Query("system", description="User creating preset")
):
    """Create a new service preset template"""
    manager = ServicePresetManager()

    success, message = await manager.create_preset(
        preset_id=preset.id,
        name=preset.name,
        service_name=preset.service_name,
        port=preset.port,
        tags=preset.tags,
        meta_template=preset.meta_template,
        checks=preset.checks,
        description=preset.description,
        category=preset.category,
        user=user
    )

    if success:
        return {
            "success": True,
            "message": message,
            "preset_id": preset.id
        }

    raise HTTPException(status_code=400, detail=message)


@router.get("/", include_in_schema=True)
async def list_presets(category: Optional[str] = Query(None, description="Filter by category")):
    """List all service presets, optionally filtered by category"""
    manager = ServicePresetManager()
    presets = await manager.list_presets(category=category)

    return {
        "success": True,
        "presets": presets,
        "total": len(presets)
    }


@router.get("/{preset_id}", include_in_schema=True)
async def get_preset(preset_id: str):
    """Get a specific preset by ID"""
    manager = ServicePresetManager()
    preset = await manager.get_preset(preset_id)

    if not preset:
        raise HTTPException(status_code=404, detail=f"Preset '{preset_id}' not found")

    return {
        "success": True,
        "preset": preset
    }


@router.put("/{preset_id}", include_in_schema=True)
async def update_preset(
    preset_id: str,
    updates: PresetUpdate,
    user: str = Query("system", description="User updating preset")
):
    """Update an existing preset"""
    manager = ServicePresetManager()

    # Only include non-None fields
    update_dict = {k: v for k, v in updates.model_dump().items() if v is not None}

    if not update_dict:
        raise HTTPException(status_code=400, detail="No fields to update")

    success, message = await manager.update_preset(preset_id, update_dict, user)

    if success:
        return {
            "success": True,
            "message": message,
            "preset_id": preset_id
        }

    raise HTTPException(status_code=400, detail=message)


@router.delete("/{preset_id}", include_in_schema=True)
async def delete_preset(
    preset_id: str,
    user: str = Query("system", description="User deleting preset")
):
    """Delete a preset"""
    manager = ServicePresetManager()

    success, message = await manager.delete_preset(preset_id, user)

    if success:
        return {
            "success": True,
            "message": message,
            "preset_id": preset_id
        }

    raise HTTPException(status_code=404 if "not found" in message else 400, detail=message)


# ============================================================================
# Service Registration from Preset
# ============================================================================

@router.post("/register", include_in_schema=True)
async def register_from_preset(
    request: RegisterFromPreset,
    user: str = Query("system", description="User registering service")
):
    """
    Register a service using a preset with variable substitution.

    This endpoint takes a preset ID and variables, then:
    1. Loads the preset template
    2. Substitutes variables (${var} or ${var:default})
    3. Registers the service in Consul
    4. Logs the operation

    Example variables:
    - address: Service IP/hostname
    - env: Environment (prod, dev, staging)
    - datacenter: Datacenter name
    - hostname: Host identifier
    - port: Override default port
    """
    manager = ServicePresetManager()

    success, message, service_id = await manager.register_from_preset(
        preset_id=request.preset_id,
        variables=request.variables,
        node_addr=request.node_addr,
        user=user
    )

    if success:
        return {
            "success": True,
            "message": message,
            "service_id": service_id,
            "preset_used": request.preset_id
        }

    status_code = 404 if "not found" in message else 400
    raise HTTPException(status_code=status_code, detail=message)


# ============================================================================
# Bulk Operations
# ============================================================================

@router.post("/bulk/register", include_in_schema=True)
async def bulk_register_from_preset(
    preset_id: str = Query(..., description="Preset to use for all registrations"),
    registrations: List[Dict[str, str]] = ...,
    user: str = Query("system", description="User performing bulk operation")
):
    """
    Register multiple services from the same preset.

    Useful for deploying the same exporter to multiple hosts.

    Body: List of variable dictionaries, e.g.:
    [
        {"address": "10.0.0.1", "env": "prod", "hostname": "web-01"},
        {"address": "10.0.0.2", "env": "prod", "hostname": "web-02"},
        {"address": "10.0.0.3", "env": "prod", "hostname": "web-03"}
    ]
    """
    manager = ServicePresetManager()

    results = []
    success_count = 0
    failed_count = 0

    for idx, variables in enumerate(registrations):
        success, message, service_id = await manager.register_from_preset(
            preset_id=preset_id,
            variables=variables,
            user=user
        )

        result = {
            "index": idx,
            "variables": variables,
            "success": success,
            "message": message,
            "service_id": service_id
        }

        results.append(result)

        if success:
            success_count += 1
        else:
            failed_count += 1

    return {
        "success": True,
        "summary": {
            "total": len(registrations),
            "successful": success_count,
            "failed": failed_count
        },
        "results": results,
        "preset_used": preset_id
    }


# ============================================================================
# Built-in Presets
# ============================================================================

@router.post("/builtin/create", include_in_schema=True)
async def create_builtin_presets(user: str = Query("system", description="User creating presets")):
    """
    Create built-in preset templates for common exporters.

    Creates presets for:
    - node-exporter-linux
    - windows-exporter
    - blackbox-icmp
    - redis-exporter

    Safe to run multiple times (will update existing presets).
    """
    manager = ServicePresetManager()
    results = await manager.create_builtin_presets(user=user)

    successful = [k for k, v in results.items() if v]
    failed = [k for k, v in results.items() if not v]

    return {
        "success": True,
        "message": f"Created {len(successful)} built-in presets",
        "summary": {
            "successful": successful,
            "failed": failed,
            "total": len(results)
        },
        "results": results
    }


# ============================================================================
# Preview & Validation
# ============================================================================

@router.post("/preview", include_in_schema=True)
async def preview_preset(request: RegisterFromPreset):
    """
    Preview the service payload that would be generated from a preset.

    Does NOT register the service - just shows what would be created.
    Useful for debugging variable substitution.
    """
    manager = ServicePresetManager()

    # Get preset
    preset = await manager.get_preset(request.preset_id)
    if not preset:
        raise HTTPException(status_code=404, detail=f"Preset '{request.preset_id}' not found")

    try:
        # Apply preset (without registering)
        service_data = manager._apply_preset(preset, request.variables)

        return {
            "success": True,
            "preview": service_data,
            "preset_used": request.preset_id,
            "variables_provided": request.variables,
            "note": "This is a preview - service has NOT been registered"
        }
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Error applying preset: {str(exc)}")


@router.get("/categories", include_in_schema=True)
async def list_categories():
    """List all preset categories with counts"""
    manager = ServicePresetManager()
    presets = await manager.list_presets()

    # Count by category
    categories = {}
    for preset in presets:
        category = preset.get("category", "uncategorized")
        categories[category] = categories.get(category, 0) + 1

    return {
        "success": True,
        "categories": categories,
        "total_presets": len(presets)
    }
