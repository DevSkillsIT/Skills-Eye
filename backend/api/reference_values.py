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


@router.get("/categories", include_in_schema=True)
async def list_categories():
    """
    Lista todas as categorias disponíveis para organizar campos em abas.

    Retorna metadados de cada categoria (label, icon, description, order).
    Categorias vêm do campo 'field_category' em Reference Values (dinâmico).

    Se não houver valores cadastrados, retorna categorias padrão.
    """
    # Categorias padrão (fallback se não houver cadastradas)
    default_categories = [
        {
            "key": "basic",
            "label": "Básico",
            "icon": "📝",
            "description": "Campos básicos e obrigatórios",
            "order": 1,
        },
        {
            "key": "infrastructure",
            "label": "Infraestrutura",
            "icon": "☁️",
            "description": "Campos relacionados à infraestrutura e cloud",
            "order": 2,
        },
        {
            "key": "device",
            "label": "Dispositivo",
            "icon": "💻",
            "description": "Campos de hardware e dispositivos",
            "order": 3,
        },
        {
            "key": "location",
            "label": "Localização",
            "icon": "📍",
            "description": "Campos de localização geográfica",
            "order": 4,
        },
        {
            "key": "network",
            "label": "Rede",
            "icon": "🌐",
            "description": "Campos de configuração de rede",
            "order": 5,
        },
        {
            "key": "security",
            "label": "Segurança",
            "icon": "🔒",
            "description": "Campos relacionados à segurança",
            "order": 6,
        },
        {
            "key": "extra",
            "label": "Extras",
            "icon": "➕",
            "description": "Campos adicionais e opcionais",
            "order": 99,
        },
    ]

    # TODO FUTURO: Carregar categorias dinâmicas de reference_values/field_category
    # Por enquanto, retorna categorias padrão
    # Quando usuário cadastrar categorias em field_category, esse endpoint buscará de lá

    return {
        "success": True,
        "total": len(default_categories),
        "categories": default_categories
    }


@router.get("/{field_name}", include_in_schema=True)
async def list_values(
    field_name: str,
    include_stats: bool = Query(False, description="Incluir estatísticas de uso"),
    sort_by: str = Query("value", description="Ordenar por: value, usage_count, created_at")
):
    """
    Lista todos os valores de um campo.

    Example:
        GET /api/v1/reference-values/company?include_stats=true&sort_by=usage_count

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

    values = await manager.list_values(
        field_name,
        include_stats=include_stats,
        sort_by=sort_by
    )

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


@router.patch("/{field_name}/{old_value}/rename", include_in_schema=True)
async def rename_value(
    field_name: str,
    old_value: str,
    new_value: str = Query(..., description="Novo valor"),
    user: str = Query("system", description="Usuário renomeando")
):
    """
    Renomeia um valor existente (PRESERVA REFERÊNCIAS).

    IMPORTANTE:
    - Atualiza apenas o campo 'value' no JSON
    - Mantém metadata, created_at, usage_count
    - NÃO quebra referências existentes

    Exemplo:
    - old_value: "Paraguacu"
    - new_value: "Paraguaçu Paulista"
    - Resultado: Valor renomeado, todas as referências preservadas
    """
    manager = ReferenceValuesManager()

    success, message = await manager.rename_value(
        field_name=field_name,
        old_value=old_value,
        new_value=new_value,
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
    Lista todos os campos que suportam reference values (DINÂMICO).

    Retorna lista dos campos metadata com available_for_registration: true.
    Campos são carregados DINAMICAMENTE do Consul KV (extraídos do Prometheus via SSH).

    IMPORTANTE: Este endpoint agora é 100% dinâmico!
    - Campos vêm do Prometheus (não hardcoded)
    - Filtra por available_for_registration=true
    - Cache de 5 minutos (via load_fields_config)

    Para adicionar/remover campos:
    1. Adicione campo no prometheus.yml
    2. Sistema extrai automaticamente via SSH
    3. Edite campo em Metadata Fields → ative "Auto-Cadastro"
    4. Campo aparece automaticamente aqui!
    """
    from api.metadata_fields_manager import load_fields_config

    # Carregar campos do Consul KV (com cache de 5min)
    config = await load_fields_config()
    all_fields = config.get('fields', [])

    # Mapeamento de categoria → icon e color padrão
    # Usado quando campo não tem icon/color customizado
    CATEGORY_DEFAULTS = {
        'basic': {'icon': '📝', 'color': 'blue'},
        'infrastructure': {'icon': '☁️', 'color': 'cyan'},
        'device': {'icon': '💻', 'color': 'purple'},
        'location': {'icon': '📍', 'color': 'orange'},
        'network': {'icon': '🌐', 'color': 'geekblue'},
        'security': {'icon': '🔒', 'color': 'red'},
        'extra': {'icon': '➕', 'color': 'default'},
    }

    # Filtrar apenas campos com available_for_registration=true
    supported_fields = []
    for field in all_fields:
        if field.get('available_for_registration', False) is not True:
            continue

        # Converter category (string ou array) em lista de categorias
        category_raw = field.get('category', 'extra')
        if isinstance(category_raw, str):
            # Suporta múltiplas categorias separadas por vírgula: "basic,device"
            categories = [c.strip() for c in category_raw.split(',') if c.strip()]
        elif isinstance(category_raw, list):
            categories = category_raw
        else:
            categories = ['extra']

        # Se não tem categoria, usa 'extra'
        if not categories:
            categories = ['extra']

        # Pegar icon e color (usa customizado ou padrão da primeira categoria)
        primary_category = categories[0]
        defaults = CATEGORY_DEFAULTS.get(primary_category, {'icon': '📝', 'color': 'default'})

        supported_fields.append({
            "name": field.get('name'),
            "display_name": field.get('display_name'),
            "description": field.get('description', ''),
            "categories": categories,  # ARRAY de categorias (pode estar em múltiplas abas)
            "icon": field.get('icon', defaults['icon']),  # Icon customizado ou padrão
            "color": field.get('color', defaults['color']),  # Color customizado ou padrão
            "required": field.get('required', False),
            "editable": field.get('editable', True),
            "field_type": field.get('field_type', 'string'),
            "order": field.get('order', 999),
        })

    # Ordenar por order (mesmo padrão do metadata-fields)
    supported_fields.sort(key=lambda f: f.get('order', 999))

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
