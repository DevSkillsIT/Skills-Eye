"""
Reference Values API - Sistema de Auto-Cadastro/Retroalimentação

Endpoints para gerenciar valores de referência de campos metadata.

USO PRINCIPAL:
- Frontend usa /ensure para auto-cadastro ao salvar formulários
- Frontend usa /list para popular selects com valores existentes
- Página de administração usa CRUD completo
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from core.reference_values_manager import ReferenceValuesManager

router = APIRouter()


# ============================================================================
# Request/Response Models
# ============================================================================

class EnsureValueRequest(BaseModel):
    """Request para garantir que valor existe (auto-cadastro)"""
    field_name: str = Field(..., description="Nome do campo (company, localizacao, etc)")
    value: str = Field(..., description="Valor digitado pelo usuário")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Metadata opcional")

    class Config:
        json_schema_extra = {
            "example": {
                "field_name": "company",
                "value": "empresa ramada",
                "metadata": {
                    "description": "Empresa cliente principal"
                }
            }
        }


class CreateValueRequest(BaseModel):
    """Request para criar valor manualmente"""
    field_name: str = Field(..., description="Nome do campo")
    value: str = Field(..., description="Valor a ser criado")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Metadata adicional")

    class Config:
        json_schema_extra = {
            "example": {
                "field_name": "cidade",
                "value": "São Paulo",
                "metadata": {
                    "estado": "SP",
                    "regiao": "Sudeste"
                }
            }
        }


class UpdateValueRequest(BaseModel):
    """Request para atualizar metadata de valor"""
    metadata: Dict[str, Any] = Field(..., description="Novos valores de metadata")

    class Config:
        json_schema_extra = {
            "example": {
                "metadata": {
                    "description": "Nova descrição",
                    "cor": "#FF5733"
                }
            }
        }


class ValueResponse(BaseModel):
    """Response com dados de um valor"""
    field_name: str
    value: str
    original_value: Optional[str] = None
    created_at: str
    created_by: str
    usage_count: int = 0
    last_used_at: Optional[str] = None
    metadata: Dict[str, Any] = {}


# ============================================================================
# Endpoints Principais
# ============================================================================

@router.post("/ensure", include_in_schema=True)
async def ensure_value(
    request: EnsureValueRequest,
    user: str = Query("system", description="Usuário executando ação")
):
    """
    Garante que valor existe (auto-cadastro).

    CRÍTICO: Este endpoint é usado automaticamente ao salvar serviços/exporters/blackbox!

    - Se valor JÁ EXISTE → retorna normalizado
    - Se valor NÃO EXISTE → cria automaticamente e retorna normalizado

    Example:
        POST /api/v1/reference-values/ensure
        {
            "field_name": "company",
            "value": "empresa ramada"
        }

        Response:
        {
            "success": true,
            "created": true,
            "value": "Empresa Ramada",  ← Normalizado (Title Case)
            "message": "Valor 'Empresa Ramada' cadastrado automaticamente"
        }
    """
    manager = ReferenceValuesManager()

    created, normalized, message = await manager.ensure_value(
        field_name=request.field_name,
        value=request.value,
        user=user,
        metadata=request.metadata
    )

    return {
        "success": True,
        "created": created,
        "value": normalized,
        "message": message
    }


@router.post("/", include_in_schema=True)
async def create_value(
    request: CreateValueRequest,
    user: str = Query("system", description="Usuário criando valor")
):
    """
    Cria novo valor manualmente (via página de administração).

    Diferente do /ensure, este endpoint retorna erro se valor já existe.
    """
    manager = ReferenceValuesManager()

    success, message = await manager.create_value(
        field_name=request.field_name,
        value=request.value,
        user=user,
        metadata=request.metadata
    )

    if not success:
        raise HTTPException(status_code=400, detail=message)

    return {
        "success": True,
        "message": message
    }


@router.get("/{field_name}", include_in_schema=True)
async def list_values(
    field_name: str,
    include_stats: bool = Query(False, description="Incluir estatísticas de uso")
):
    """
    Lista todos os valores de um campo.

    Example:
        GET /api/v1/reference-values/company?include_stats=true

        Response:
        {
            "success": true,
            "field_name": "company",
            "total": 3,
            "values": [
                {
                    "value": "Acme Corp",
                    "created_at": "2025-01-01T12:00:00",
                    "created_by": "admin",
                    "usage_count": 15,
                    "last_used_at": "2025-10-31T10:30:00"
                },
                {
                    "value": "Empresa Ramada",
                    "created_at": "2025-01-02T14:30:00",
                    "created_by": "user1",
                    "usage_count": 8,
                    "last_used_at": "2025-10-30T16:45:00"
                }
            ]
        }
    """
    manager = ReferenceValuesManager()

    values = await manager.list_values(field_name, include_stats=include_stats)

    return {
        "success": True,
        "field_name": field_name,
        "total": len(values),
        "values": values
    }


@router.get("/{field_name}/{value}", include_in_schema=True)
async def get_value(field_name: str, value: str):
    """
    Busca valor específico.

    Example:
        GET /api/v1/reference-values/company/Empresa%20Ramada

        Response:
        {
            "success": true,
            "data": {
                "field_name": "company",
                "value": "Empresa Ramada",
                "created_at": "2025-01-02T14:30:00",
                "created_by": "user1",
                "usage_count": 8,
                "metadata": {}
            }
        }
    """
    manager = ReferenceValuesManager()

    data = await manager.get_value(field_name, value)

    if not data:
        raise HTTPException(
            status_code=404,
            detail=f"Valor '{value}' não encontrado para campo '{field_name}'"
        )

    return {
        "success": True,
        "data": data
    }


@router.put("/{field_name}/{value}", include_in_schema=True)
async def update_value(
    field_name: str,
    value: str,
    request: UpdateValueRequest,
    user: str = Query("system", description="Usuário atualizando")
):
    """
    Atualiza metadata de um valor.

    IMPORTANTE: Não permite alterar o valor em si para evitar quebra de referências!
    """
    manager = ReferenceValuesManager()

    success, message = await manager.update_value(
        field_name=field_name,
        value=value,
        updates={"metadata": request.metadata},
        user=user
    )

    if not success:
        raise HTTPException(status_code=400, detail=message)

    return {
        "success": True,
        "message": message
    }


@router.delete("/{field_name}/{value}", include_in_schema=True)
async def delete_value(
    field_name: str,
    value: str,
    user: str = Query("system", description="Usuário deletando"),
    force: bool = Query(False, description="Forçar deleção mesmo se em uso")
):
    """
    Deleta valor de referência.

    PROTEÇÃO: Bloqueia deleção se valor está em uso.

    Example:
        DELETE /api/v1/reference-values/company/Empresa%20Ramada

        Response (bloqueado):
        {
            "success": false,
            "error": "Valor 'Empresa Ramada' está em uso em 15 instância(s). Não é possível deletar."
        }

        Com force=true:
        {
            "success": true,
            "message": "Valor 'Empresa Ramada' deletado com sucesso"
        }
    """
    manager = ReferenceValuesManager()

    success, message = await manager.delete_value(
        field_name=field_name,
        value=value,
        user=user,
        force=force
    )

    if not success:
        raise HTTPException(status_code=400, detail=message)

    return {
        "success": True,
        "message": message
    }


# ============================================================================
# Endpoints Auxiliares
# ============================================================================

@router.get("/", include_in_schema=True)
async def list_all_fields():
    """
    Lista todos os campos que suportam reference values.

    Retorna lista dos campos metadata com available_for_registration: true.
    """
    # Campos suportados (obtidos do metadata_fields.json com available_for_registration: true)
    supported_fields = [
        {"name": "company", "display_name": "Empresa", "description": "Nome da empresa"},
        {"name": "grupo_monitoramento", "display_name": "Grupo Monitoramento", "description": "Grupo de monitoramento (projeto)"},
        {"name": "localizacao", "display_name": "Localização", "description": "Localização física ou lógica"},
        {"name": "tipo", "display_name": "Tipo", "description": "Tipo do dispositivo ou serviço"},
        {"name": "modelo", "display_name": "Modelo", "description": "Modelo do dispositivo"},
        {"name": "cod_localidade", "display_name": "Código da Localidade", "description": "Código identificador da localidade"},
        {"name": "tipo_dispositivo_abrev", "display_name": "Tipo Dispositivo (Abrev)", "description": "Tipo do dispositivo (abreviado)"},
        {"name": "cidade", "display_name": "Cidade", "description": "Cidade onde está localizado"},
        {"name": "provedor", "display_name": "Provedor", "description": "Provedor de serviços (ISP, cloud, etc)"},
        {"name": "vendor", "display_name": "Fornecedor", "description": "Fornecedor do serviço ou infraestrutura (AWS, Azure, GCP, etc)"},
        {"name": "fabricante", "display_name": "Fabricante", "description": "Fabricante do hardware/dispositivo (Dell, HP, Cisco, etc)"},
    ]

    return {
        "success": True,
        "total": len(supported_fields),
        "fields": supported_fields
    }


@router.post("/batch-ensure", include_in_schema=True)
async def batch_ensure(
    values: List[EnsureValueRequest],
    user: str = Query("system", description="Usuário executando ação")
):
    """
    Garante múltiplos valores de uma vez (batch operation).

    Útil para processar formulários com múltiplos campos metadata.

    Example:
        POST /api/v1/reference-values/batch-ensure
        [
            {"field_name": "company", "value": "Empresa Ramada"},
            {"field_name": "cidade", "value": "sao paulo"},
            {"field_name": "provedor", "value": "AWS"}
        ]

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

    for req in values:
        created, normalized, message = await manager.ensure_value(
            field_name=req.field_name,
            value=req.value,
            user=user,
            metadata=req.metadata
        )

        results.append({
            "field_name": req.field_name,
            "value": normalized,
            "created": created,
            "message": message
        })

        if created:
            created_count += 1
        else:
            existing_count += 1

    return {
        "success": True,
        "total_processed": len(values),
        "created": created_count,
        "existing": existing_count,
        "results": results
    }
