"""
API de Auditoria
Endpoints para consulta de logs de auditoria
"""
from fastapi import APIRouter, Query
from typing import Optional
from pydantic import BaseModel
from core.audit_manager import audit_manager

router = APIRouter(prefix="/kv/audit", tags=["Audit Logs"])


class AuditEventResponse(BaseModel):
    """Resposta de evento de auditoria"""
    id: int
    timestamp: str
    action: str
    resource_type: str
    resource_id: str
    user: str
    details: str
    metadata: dict


class AuditEventsResponse(BaseModel):
    """Resposta de lista de eventos"""
    events: list[dict]
    total: int
    count: int
    limit: int
    offset: int


class AuditStatisticsResponse(BaseModel):
    """Resposta de estatísticas de auditoria"""
    total_events: int
    by_action: dict
    by_resource_type: dict
    by_user: dict


@router.get("/events", response_model=AuditEventsResponse)
async def get_audit_events(
    start_date: Optional[str] = Query(None, description="Data inicial (ISO format)"),
    end_date: Optional[str] = Query(None, description="Data final (ISO format)"),
    resource_type: Optional[str] = Query(None, description="Tipo de recurso"),
    action: Optional[str] = Query(None, description="Ação realizada"),
    limit: int = Query(20, ge=1, le=1000, description="Limite de eventos"),
    offset: int = Query(0, ge=0, description="Número de eventos a pular")
):
    """
    Lista eventos de auditoria com filtros opcionais

    - **start_date**: Filtrar eventos após esta data (ISO format)
    - **end_date**: Filtrar eventos antes desta data (ISO format)
    - **resource_type**: Filtrar por tipo de recurso (service, kv, blackbox_target, etc.)
    - **action**: Filtrar por ação (create, update, delete, read)
    - **limit**: Número máximo de eventos a retornar (padrão: 20, máximo: 1000)
    - **offset**: Número de eventos a pular para paginação (padrão: 0)
    """
    events, total = audit_manager.get_events(
        start_date=start_date,
        end_date=end_date,
        resource_type=resource_type,
        action=action,
        limit=limit,
        offset=offset
    )

    return {
        "events": events,
        "total": total,
        "count": len(events),
        "limit": limit,
        "offset": offset
    }


@router.get("/statistics", response_model=AuditStatisticsResponse)
async def get_audit_statistics():
    """
    Retorna estatísticas sobre os eventos de auditoria

    Retorna:
    - Total de eventos
    - Contagem por ação
    - Contagem por tipo de recurso
    - Contagem por usuário
    """
    stats = audit_manager.get_statistics()
    return stats


@router.delete("/events")
async def clear_audit_events():
    """
    Limpa todos os eventos de auditoria

    **ATENÇÃO**: Esta ação é irreversível!
    """
    audit_manager.clear_events()
    return {"success": True, "message": "Todos os eventos de auditoria foram removidos"}
