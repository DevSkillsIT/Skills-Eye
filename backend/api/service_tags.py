"""
Service Tags API - Sistema de Auto-Cadastro para Tags de Serviços

DIFERENÇA dos Reference Values:
- Reference Values: campos metadata individuais (string única)
- Service Tags: array de strings nos serviços Consul

OBJETIVO:
- Extrair tags únicas de todos os serviços existentes
- Permitir auto-cadastro de novas tags
- Fornecer autocomplete para formulários

Tags vêm do campo Tags dos serviços Consul:
{
  "Service": "node_exporter",
  "Tags": ["linux", "monitoring", "production"]  ← Array!
}
"""

from fastapi import APIRouter, HTTPException, Query
from typing import List, Set
from pydantic import BaseModel, Field

from core.consul_manager import ConsulManager
from core.reference_values_manager import ReferenceValuesManager

router = APIRouter()


class TagEnsureRequest(BaseModel):
    """Request para garantir que tag existe"""
    tag: str = Field(..., description="Tag a ser garantida")

    class Config:
        json_schema_extra = {
            "example": {
                "tag": "production"
            }
        }


# ============================================================================
# Endpoints
# ============================================================================

@router.get("/unique", include_in_schema=True)
async def get_unique_tags():
    """
    Lista todas as tags únicas usadas em todos os serviços Consul.

    Extrai tags de TODOS os serviços e retorna lista ordenada alfabeticamente.

    Example Response:
        {
            "success": true,
            "total": 15,
            "tags": [
                "database",
                "dev",
                "hml",
                "linux",
                "monitoring",
                "mysql",
                "production",
                "windows"
            ]
        }
    """
    consul = ConsulManager()

    try:
        # Buscar todos os serviços
        services_response = await consul.get_services()

        if not services_response or 'services' not in services_response:
            return {
                "success": True,
                "total": 0,
                "tags": []
            }

        # Extrair tags únicas
        unique_tags: Set[str] = set()

        for service_list in services_response['services'].values():
            if not isinstance(service_list, list):
                continue

            for service in service_list:
                tags = service.get('Tags', [])
                if isinstance(tags, list):
                    unique_tags.update(tags)

        # Ordenar alfabeticamente
        sorted_tags = sorted(list(unique_tags))

        return {
            "success": True,
            "total": len(sorted_tags),
            "tags": sorted_tags
        }

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao buscar tags: {str(exc)}"
        )


@router.post("/ensure", include_in_schema=True)
async def ensure_tag(
    request: TagEnsureRequest,
    user: str = Query("system", description="Usuário executando ação")
):
    """
    Garante que tag existe no sistema (auto-cadastro).

    Similar ao /reference-values/ensure, mas específico para tags.

    Example:
        POST /api/v1/service-tags/ensure
        {
            "tag": "production"
        }

        Response:
        {
            "success": true,
            "created": true,
            "tag": "Production",  ← Normalizado (Title Case)
            "message": "Tag 'Production' cadastrada automaticamente"
        }
    """
    manager = ReferenceValuesManager()

    # Usar sistema de Reference Values com field_name especial "service_tag"
    created, normalized, message = await manager.ensure_value(
        field_name="service_tag",
        value=request.tag,
        user=user
    )

    return {
        "success": True,
        "created": created,
        "tag": normalized,
        "message": message
    }


@router.get("/", include_in_schema=True)
async def list_registered_tags(include_stats: bool = Query(False)):
    """
    Lista tags cadastradas via auto-cadastro (no KV store).

    Diferente de /unique que extrai dos serviços ativos,
    este endpoint lista tags cadastradas manualmente ou via auto-cadastro.

    Útil para ver histórico e estatísticas de uso.
    """
    manager = ReferenceValuesManager()

    tags = await manager.list_values("service_tag", include_stats=include_stats)

    return {
        "success": True,
        "total": len(tags),
        "tags": tags
    }


@router.delete("/{tag}", include_in_schema=True)
async def delete_tag(
    tag: str,
    user: str = Query("system"),
    force: bool = Query(False)
):
    """
    Deleta tag cadastrada.

    PROTEÇÃO: Bloqueia se tag está em uso em serviços.
    """
    manager = ReferenceValuesManager()

    success, message = await manager.delete_value(
        field_name="service_tag",
        value=tag,
        user=user,
        force=force
    )

    if not success:
        raise HTTPException(status_code=400, detail=message)

    return {
        "success": True,
        "message": message
    }


@router.post("/batch-ensure", include_in_schema=True)
async def batch_ensure_tags(
    tags: List[str],
    user: str = Query("system")
):
    """
    Garante múltiplas tags de uma vez (batch operation).

    Útil para processar formulários com múltiplas tags.

    Example:
        POST /api/v1/service-tags/batch-ensure?user=admin
        ["linux", "monitoring", "production"]

        Response:
        {
            "success": true,
            "total_processed": 3,
            "created": 2,
            "existing": 1,
            "results": [...]
        }
    """
    manager = ReferenceValuesManager()

    results = []
    created_count = 0
    existing_count = 0

    for tag in tags:
        if not tag:
            continue

        created, normalized, message = await manager.ensure_value(
            field_name="service_tag",
            value=tag,
            user=user
        )

        results.append({
            "tag": normalized,
            "created": created,
            "message": message
        })

        if created:
            created_count += 1
        else:
            existing_count += 1

    return {
        "success": True,
        "total_processed": len(tags),
        "created": created_count,
        "existing": existing_count,
        "results": results
    }
