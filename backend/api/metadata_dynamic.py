"""
API para Metadata Fields Dinâmicos

Endpoint centralizado para frontend buscar campos dinamicamente do JSON.
Substitui TODOS os campos hardcoded no frontend!
"""

from fastapi import APIRouter, Query, HTTPException
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
import logging

from core.metadata_loader import metadata_loader

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/metadata-dynamic", tags=["Metadata Dynamic"])


class FieldResponse(BaseModel):
    """Schema de resposta de um campo"""
    name: str
    display_name: str
    description: str
    source_label: str
    field_type: str
    required: bool
    enabled: bool
    show_in_table: bool
    show_in_dashboard: bool
    show_in_form: bool
    show_in_filter: bool
    show_in_blackbox: bool
    show_in_exporters: bool
    show_in_services: bool
    editable: bool
    available_for_registration: bool
    options: Optional[List[str]] = None
    default_value: Optional[Any] = None
    placeholder: str = ""
    order: int
    category: str
    validation: Dict[str, Any] = {}


class FieldsListResponse(BaseModel):
    """Resposta da lista de campos"""
    success: bool
    fields: List[FieldResponse]
    total: int
    context: Optional[str] = None
    filters_applied: Dict[str, Any]


@router.get("/fields", response_model=FieldsListResponse)
async def get_dynamic_fields(
    context: Optional[str] = Query(None, description="Contexto: 'blackbox', 'exporters', 'services', 'general'"),
    enabled: Optional[bool] = Query(True, description="Apenas campos ativos"),
    required: Optional[bool] = Query(None, description="Filtrar por obrigatório"),
    show_in_table: Optional[bool] = Query(None),
    show_in_form: Optional[bool] = Query(None),
    show_in_filter: Optional[bool] = Query(None),
    category: Optional[str] = Query(None, description="Categoria: basic, infrastructure, location, business, technical"),
):
    """
    Retorna campos metadata DINAMICAMENTE do JSON

    Este endpoint SUBSTITUI todos os campos hardcoded no frontend!

    Exemplos de uso:
    - GET /metadata-dynamic/fields?context=blackbox
      → Retorna campos para Blackbox Targets

    - GET /metadata-dynamic/fields?context=exporters&show_in_form=true
      → Retorna campos para formulário de Exporters

    - GET /metadata-dynamic/fields?show_in_filter=true
      → Retorna campos para barra de filtros

    - GET /metadata-dynamic/fields?required=true
      → Retorna apenas campos obrigatórios

    Args:
        context: Contexto específico (blackbox, exporters, services)
        enabled: Filtrar campos ativos
        required: Filtrar por obrigatório
        show_in_*: Filtros de visibilidade
        category: Categoria dos campos

    Returns:
        Lista de campos filtrados
    """
    try:
        # Preparar filtros
        filters = {}

        if enabled is not None:
            filters['enabled'] = enabled
        if required is not None:
            filters['required'] = required
        if show_in_table is not None:
            filters['show_in_table'] = show_in_table
        if show_in_form is not None:
            filters['show_in_form'] = show_in_form
        if show_in_filter is not None:
            filters['show_in_filter'] = show_in_filter
        if category is not None:
            filters['category'] = category

        # Aplicar filtros de contexto
        if context == 'blackbox':
            filters['show_in_blackbox'] = True
        elif context == 'exporters':
            filters['show_in_exporters'] = True
        elif context == 'services':
            filters['show_in_services'] = True

        # Buscar campos
        fields = metadata_loader.get_fields(**filters)

        # Ordenar por order
        fields.sort(key=lambda f: f.order)

        # Converter para dicts
        fields_data = [
            FieldResponse(
                name=f.name,
                display_name=f.display_name,
                description=f.description,
                source_label=f.source_label,
                field_type=f.field_type,
                required=f.required,
                enabled=f.enabled,
                show_in_table=f.show_in_table,
                show_in_dashboard=f.show_in_dashboard,
                show_in_form=f.show_in_form,
                show_in_filter=f.show_in_filter,
                show_in_blackbox=f.show_in_blackbox,
                show_in_exporters=f.show_in_exporters,
                show_in_services=f.show_in_services,
                editable=f.editable,
                available_for_registration=f.available_for_registration,
                options=f.options if f.options is not None else [],
                default_value=f.default_value,
                placeholder=f.placeholder if f.placeholder else "",
                order=f.order,
                category=f.category,
                validation=f.validation if f.validation else {},
            )
            for f in fields
        ]

        return FieldsListResponse(
            success=True,
            fields=fields_data,
            total=len(fields_data),
            context=context,
            filters_applied=filters
        )

    except Exception as e:
        logger.error(f"Erro ao buscar campos dinâmicos: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/fields/names", response_model=Dict[str, Any])
async def get_field_names(
    context: Optional[str] = Query(None),
    enabled: bool = Query(True),
    required: Optional[bool] = Query(None),
):
    """
    Retorna apenas os NOMES dos campos (mais leve)

    Útil para validações rápidas no backend/frontend

    Returns:
        {"success": true, "field_names": ["company", "env", ...], "total": 10}
    """
    try:
        filters = {'enabled': enabled}

        if required is not None:
            filters['required'] = required

        if context == 'blackbox':
            filters['show_in_blackbox'] = True
        elif context == 'exporters':
            filters['show_in_exporters'] = True
        elif context == 'services':
            filters['show_in_services'] = True

        field_names = metadata_loader.get_field_names(**filters)

        return {
            "success": True,
            "field_names": field_names,
            "total": len(field_names),
            "context": context
        }

    except Exception as e:
        logger.error(f"Erro ao buscar nomes de campos: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/fields/required", response_model=Dict[str, Any])
async def get_required_fields():
    """
    Retorna campos obrigatórios

    Atalho para /fields/names?required=true

    Returns:
        {"success": true, "required_fields": ["company", ...], "total": 5}
    """
    try:
        required_fields = metadata_loader.get_required_fields()

        return {
            "success": True,
            "required_fields": required_fields,
            "total": len(required_fields)
        }

    except Exception as e:
        logger.error(f"Erro ao buscar campos obrigatórios: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/reload", response_model=Dict[str, Any])
async def reload_metadata():
    """
    Força reload do cache do metadata_fields.json

    Útil após editar campos na página MetadataFields

    Returns:
        {"success": true, "message": "Cache recarregado", "total_fields": 20}
    """
    try:
        metadata_loader.reload()
        fields = metadata_loader.get_all_fields(reload=True)

        return {
            "success": True,
            "message": "Cache de metadata recarregado com sucesso",
            "total_fields": len(fields)
        }

    except Exception as e:
        logger.error(f"Erro ao recarregar metadata: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/validate", response_model=Dict[str, Any])
async def validate_metadata(
    metadata: Dict[str, Any],
    context: str = Query('general', description="Contexto de validação")
):
    """
    Valida metadata contra os campos definidos

    Args:
        metadata: Dicionário com metadata a validar
        context: Contexto (blackbox, exporters, services, general)

    Returns:
        {"valid": bool, "errors": [...], "warnings": [...]}
    """
    try:
        result = metadata_loader.validate_metadata(metadata, context)

        return {
            "success": True,
            **result
        }

    except Exception as e:
        logger.error(f"Erro ao validar metadata: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
