"""
API Endpoints para Monitoring Types

Endpoints configuration-driven para gerenciar tipos de monitoramento.
"""

from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
import logging

from core.monitoring_type_manager import get_monitoring_type_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/monitoring-types", tags=["Monitoring Types"])


# ===========================
# Response Models
# ===========================

class MonitoringCategoryResponse(BaseModel):
    """Response para GET /monitoring-types"""
    success: bool
    categories: List[Dict[str, Any]]
    total: int


class MonitoringTypeDetailResponse(BaseModel):
    """Response para GET /monitoring-types/{category} ou /{category}/{type_id}"""
    success: bool
    data: Dict[str, Any]


class ErrorResponse(BaseModel):
    """Response padrão para erros"""
    success: bool = False
    error: str


# ===========================
# Endpoints
# ===========================

@router.get("", response_model=MonitoringCategoryResponse)
async def get_all_categories():
    """
    Lista todas as categorias de monitoramento disponíveis

    Returns:
        {
            "success": true,
            "categories": [
                {
                    "category": "network-probes",
                    "display_name": "Network Probes (Rede)",
                    "icon": "📡",
                    "color": "blue",
                    "enabled": true,
                    "order": 1,
                    "types": [...],
                    "page_config": {...}
                },
                ...
            ],
            "total": 4
        }
    """
    try:
        manager = get_monitoring_type_manager()
        categories = await manager.get_all_categories()

        return {
            "success": True,
            "categories": categories,
            "total": len(categories)
        }

    except Exception as e:
        logger.error(f"Error getting categories: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{category}", response_model=MonitoringTypeDetailResponse)
async def get_category(category: str):
    """
    Retorna schema completo de uma categoria específica

    Args:
        category: ID da categoria (ex: 'network-probes', 'system-exporters')

    Returns:
        {
            "success": true,
            "data": {
                "category": "network-probes",
                "display_name": "Network Probes (Rede)",
                "types": [
                    {
                        "id": "icmp",
                        "display_name": "ICMP (Ping)",
                        "matchers": {...},
                        "form_schema": {...},
                        "table_schema": {...}
                    },
                    ...
                ],
                "page_config": {...}
            }
        }
    """
    try:
        manager = get_monitoring_type_manager()
        category_schema = await manager.get_category(category)

        if not category_schema:
            raise HTTPException(
                status_code=404,
                detail=f"Category '{category}' not found"
            )

        return {
            "success": True,
            "data": category_schema
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting category {category}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{category}/{type_id}", response_model=MonitoringTypeDetailResponse)
async def get_type(category: str, type_id: str):
    """
    Retorna schema de um tipo específico dentro de uma categoria

    Args:
        category: ID da categoria (ex: 'network-probes')
        type_id: ID do tipo (ex: 'icmp', 'tcp', 'node', 'windows')

    Returns:
        {
            "success": true,
            "data": {
                "id": "icmp",
                "display_name": "ICMP (Ping)",
                "icon": "🏓",
                "description": "...",
                "category": "network-probes",
                "category_display_name": "Network Probes (Rede)",
                "matchers": {
                    "exporter_type_values": ["blackbox", "bb-exporter", ...],
                    "module_values": ["icmp", "ping", ...]
                },
                "form_schema": {...},
                "table_schema": {...},
                "filters": {...},
                "metrics": {...}
            }
        }
    """
    try:
        manager = get_monitoring_type_manager()
        type_schema = await manager.get_type(category, type_id)

        if not type_schema:
            raise HTTPException(
                status_code=404,
                detail=f"Type '{type_id}' not found in category '{category}'"
            )

        return {
            "success": True,
            "data": type_schema
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting type {category}/{type_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{category}/filter-query")
async def build_filter_query(category: str, type_id: Optional[str] = None):
    """
    Constrói query de filtro para um tipo de monitoramento

    Útil para frontend aplicar filtros baseados em matchers.

    Args:
        category: ID da categoria
        type_id: ID do tipo (opcional, se não fornecido retorna query da categoria)

    Returns:
        {
            "success": true,
            "query": {
                "operator": "and",
                "conditions": [
                    {"field": "Meta.exporter_type", "operator": "in", "values": [...]},
                    {"field": "Meta.module", "operator": "in", "values": [...]}
                ]
            }
        }
    """
    try:
        manager = get_monitoring_type_manager()

        if type_id:
            # Query para tipo específico
            type_schema = await manager.get_type(category, type_id)
            if not type_schema:
                raise HTTPException(404, f"Type {type_id} not found")

            query = manager.build_filter_query(type_schema)

        else:
            # Query para todos os tipos da categoria
            category_schema = await manager.get_category(category)
            if not category_schema:
                raise HTTPException(404, f"Category {category} not found")

            # Combinar matchers de todos os tipos
            all_conditions = []
            for type_def in category_schema.get('types', []):
                type_query = manager.build_filter_query(type_def)
                if 'conditions' in type_query:
                    all_conditions.extend(type_query['conditions'])

            query = {
                'operator': 'or' if all_conditions else 'and',
                'conditions': all_conditions
            }

        return {
            "success": True,
            "query": query
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error building filter query: {e}", exc_info=True)
        raise HTTPException(500, str(e))


@router.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        manager = get_monitoring_type_manager()
        categories = await manager.get_all_categories()

        return {
            "success": True,
            "status": "healthy",
            "schemas_loaded": len(categories)
        }

    except Exception as e:
        return {
            "success": False,
            "status": "unhealthy",
            "error": str(e)
        }
