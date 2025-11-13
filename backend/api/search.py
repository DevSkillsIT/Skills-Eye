"""
Advanced Search API
Provides powerful search capabilities for services and metadata.
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from core.consul_manager import ConsulManager
from core.advanced_search import AdvancedSearch, SearchOperator, LogicalOperator

router = APIRouter(tags=["Search"])


# ============================================================================
# Request Models
# ============================================================================

class SearchConditionModel(BaseModel):
    """Single search condition"""
    field: str = Field(..., description="Field path (e.g., 'Meta.company', 'tags')")
    operator: str = Field(..., description="Operator (eq, ne, contains, regex, in, etc.)")
    value: Any = Field(..., description="Value to compare")

    class Config:
        json_schema_extra = {
            "example": {
                "field": "Meta.company",
                "operator": "eq",
                "value": "Ramada"
            }
        }


class AdvancedSearchRequest(BaseModel):
    """Advanced search request with multiple conditions"""
    conditions: List[SearchConditionModel] = Field(..., description="List of search conditions")
    logical_operator: str = Field("and", description="How to combine conditions (and/or)")
    sort_by: Optional[str] = Field(None, description="Field to sort by")
    sort_desc: bool = Field(False, description="Sort in descending order")
    page: int = Field(1, description="Page number (1-indexed)", ge=1)
    page_size: int = Field(20, description="Items per page", ge=1, le=100)

    class Config:
        json_schema_extra = {
            "example": {
                "conditions": [
                    {"field": "Meta.company", "operator": "eq", "value": "Ramada"},
                    {"field": "Meta.env", "operator": "in", "value": ["prod", "staging"]}
                ],
                "logical_operator": "and",
                "sort_by": "Meta.name",
                "sort_desc": False,
                "page": 1,
                "page_size": 20
            }
        }


class TextSearchRequest(BaseModel):
    """Full-text search request"""
    text: str = Field(..., description="Text to search for")
    fields: Optional[List[str]] = Field(None, description="Fields to search (default: all common fields)")
    page: int = Field(1, description="Page number", ge=1)
    page_size: int = Field(20, description="Items per page", ge=1, le=100)


# ============================================================================
# Search Endpoints
# ============================================================================

@router.post("/advanced", include_in_schema=True)
async def advanced_search(request: AdvancedSearchRequest):
    """
    Advanced search with multiple conditions and operators.

    Supports operators:
    - eq: Equals
    - ne: Not equals
    - contains: String contains
    - regex: Regular expression match
    - in: Value in list
    - not_in: Value not in list
    - starts_with: String starts with
    - ends_with: String ends with
    - gt, lt, gte, lte: Numeric comparisons

    Logical operators:
    - and: All conditions must match
    - or: At least one condition must match

    Examples:
    ```json
    {
      "conditions": [
        {"field": "Meta.company", "operator": "eq", "value": "Ramada"},
        {"field": "Meta.env", "operator": "in", "value": ["prod", "staging"]},
        {"field": "Meta.name", "operator": "regex", "value": "web-.*"}
      ],
      "logical_operator": "and",
      "sort_by": "Meta.name",
      "page": 1,
      "page_size": 20
    }
    ```
    """
    consul = ConsulManager()

    # Get all services
    services_dict = await consul.get_services()
    services_list = list(services_dict.values())

    # Convert conditions to dict format
    conditions = [c.model_dump() for c in request.conditions]

    # Apply search
    filtered = AdvancedSearch.search(
        items=services_list,
        conditions=conditions,
        logical_operator=request.logical_operator
    )

    # Sort if requested
    if request.sort_by:
        filtered = AdvancedSearch.sort_by_field(
            filtered,
            request.sort_by,
            request.sort_desc
        )

    # Paginate
    result = AdvancedSearch.paginate(
        filtered,
        request.page,
        request.page_size
    )

    return {
        "success": True,
        "data": result["data"],
        "pagination": result["pagination"],
        "filters_applied": {
            "conditions_count": len(request.conditions),
            "logical_operator": request.logical_operator,
            "sorted_by": request.sort_by
        }
    }


@router.post("/text", include_in_schema=True)
async def text_search(request: TextSearchRequest):
    """
    Full-text search across multiple fields.

    Searches in: Meta.name, Meta.instance, Meta.company, Meta.project, service, id

    Example:
    ```json
    {
      "text": "ramada",
      "page": 1,
      "page_size": 20
    }
    ```
    """
    consul = ConsulManager()

    # Get all services
    services_dict = await consul.get_services()
    services_list = list(services_dict.values())

    # Apply text search
    filtered = AdvancedSearch.search_text(
        services_list,
        request.text,
        request.fields
    )

    # Paginate
    result = AdvancedSearch.paginate(
        filtered,
        request.page,
        request.page_size
    )

    return {
        "success": True,
        "data": result["data"],
        "pagination": result["pagination"],
        "search_term": request.text,
        "fields_searched": request.fields or "all common fields"
    }


@router.get("/filters", include_in_schema=True)
async def get_filter_options():
    """
    Get available filter options from current services.

    Returns unique values for common metadata fields:
    - module
    - company
    - project
    - env
    - datacenter
    - service
    - tags

    Useful for building dynamic filter UIs.
    """
    consul = ConsulManager()

    # Get all services
    services_dict = await consul.get_services()
    services_list = list(services_dict.values())

    # Build filter options
    filters = AdvancedSearch.build_filters_from_metadata(services_list)

    return {
        "success": True,
        "filters": filters,
        "total_services": len(services_list)
    }


@router.get("/unique-values", include_in_schema=True)
async def get_unique_values(
    field: str = Query(..., description="Field path (e.g., 'Meta.company')")
):
    """
    Get unique values for a specific field.

    Useful for autocomplete and filter dropdowns.

    Example: /search/unique-values?field=Meta.company
    """
    consul = ConsulManager()

    # Get all services
    services_dict = await consul.get_services()
    services_list = list(services_dict.values())

    # Extract unique values
    values = AdvancedSearch.extract_unique_values(services_list, field)

    return {
        "success": True,
        "field": field,
        "values": values,
        "count": len(values)
    }


# ============================================================================
# Quick Filters (Convenience Endpoints)
# ============================================================================

@router.get("/by-company/{company}", include_in_schema=True)
async def search_by_company(
    company: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100)
):
    """Quick search by company"""
    consul = ConsulManager()
    services_dict = await consul.get_services()
    services_list = list(services_dict.values())

    filtered = AdvancedSearch.search(
        services_list,
        [{"field": "Meta.company", "operator": "eq", "value": company}],
        "and"
    )

    result = AdvancedSearch.paginate(filtered, page, page_size)

    return {
        "success": True,
        "data": result["data"],
        "pagination": result["pagination"],
        "company": company
    }


@router.get("/by-env/{env}", include_in_schema=True)
async def search_by_environment(
    env: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100)
):
    """Quick search by environment (prod, dev, staging, etc.)"""
    consul = ConsulManager()
    services_dict = await consul.get_services()
    services_list = list(services_dict.values())

    filtered = AdvancedSearch.search(
        services_list,
        [{"field": "Meta.env", "operator": "eq", "value": env}],
        "and"
    )

    result = AdvancedSearch.paginate(filtered, page, page_size)

    return {
        "success": True,
        "data": result["data"],
        "pagination": result["pagination"],
        "environment": env
    }


@router.get("/by-tag/{tag}", include_in_schema=True)
async def search_by_tag(
    tag: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100)
):
    """Quick search by tag"""
    consul = ConsulManager()
    services_dict = await consul.get_services()
    services_list = list(services_dict.values())

    filtered = AdvancedSearch.search(
        services_list,
        [{"field": "Tags", "operator": "contains", "value": tag}],
        "and"
    )

    result = AdvancedSearch.paginate(filtered, page, page_size)

    return {
        "success": True,
        "data": result["data"],
        "pagination": result["pagination"],
        "tag": tag
    }


# ============================================================================
# Blackbox-Specific Search
# ============================================================================

@router.get("/blackbox", include_in_schema=True)
async def search_blackbox_targets(
    module: Optional[str] = Query(None, description="Blackbox module"),
    company: Optional[str] = Query(None, description="Company name"),
    project: Optional[str] = Query(None, description="Project name"),
    env: Optional[str] = Query(None, description="Environment"),
    enabled: Optional[bool] = Query(None, description="Enabled status"),
    group: Optional[str] = Query(None, description="Group ID"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100)
):
    """
    Search blackbox targets with common filters.

    Convenience endpoint for blackbox-specific searches.
    """
    consul = ConsulManager()

    # Get blackbox services only
    services_dict = await consul.query_agent_services('Service == "blackbox_exporter"')
    services_list = list(services_dict.values())

    # Build conditions
    conditions = []

    if module:
        conditions.append({"field": "Meta.module", "operator": "eq", "value": module})
    if company:
        conditions.append({"field": "Meta.company", "operator": "eq", "value": company})
    if project:
        conditions.append({"field": "Meta.project", "operator": "eq", "value": project})
    if env:
        conditions.append({"field": "Meta.env", "operator": "eq", "value": env})
    if group:
        conditions.append({"field": "Meta.group", "operator": "eq", "value": group})

    # Apply search if conditions exist
    if conditions:
        filtered = AdvancedSearch.search(services_list, conditions, "and")
    else:
        filtered = services_list

    # Paginate
    result = AdvancedSearch.paginate(filtered, page, page_size)

    return {
        "success": True,
        "data": result["data"],
        "pagination": result["pagination"],
        "filters_applied": {
            "module": module,
            "company": company,
            "project": project,
            "env": env,
            "group": group
        }
    }


# ============================================================================
# Statistics & Analytics
# ============================================================================

@router.get("/stats", include_in_schema=True)
async def get_search_statistics():
    """
    Get statistics about services for analytics.

    Returns counts grouped by:
    - Company
    - Environment
    - Module
    - Datacenter
    - Service type
    """
    consul = ConsulManager()
    services_dict = await consul.get_services()
    services_list = list(services_dict.values())

    stats = {
        "total_services": len(services_list),
        "by_company": {},
        "by_env": {},
        "by_module": {},
        "by_datacenter": {},
        "by_service_name": {}
    }

    for service in services_list:
        meta = service.get("Meta", {})

        # Count by company
        company = meta.get("company", "unknown")
        stats["by_company"][company] = stats["by_company"].get(company, 0) + 1

        # Count by env
        env = meta.get("env", "unknown")
        stats["by_env"][env] = stats["by_env"].get(env, 0) + 1

        # Count by module
        module = meta.get("module", "unknown")
        stats["by_module"][module] = stats["by_module"].get(module, 0) + 1

        # Count by datacenter
        datacenter = meta.get("datacenter", "unknown")
        stats["by_datacenter"][datacenter] = stats["by_datacenter"].get(datacenter, 0) + 1

        # Count by service name
        service_name = service.get("Service", "unknown")
        stats["by_service_name"][service_name] = stats["by_service_name"].get(service_name, 0) + 1

    return {
        "success": True,
        "statistics": stats
    }
