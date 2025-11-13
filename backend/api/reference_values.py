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
from core.category_manager import CategoryManager

router = APIRouter(tags=["Reference Values"])


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


class CreateCategoryRequest(BaseModel):
    """Request para criar categoria"""
    key: str = Field(..., description="ID único (lowercase, sem espaços)")
    label: str = Field(..., description="Nome exibido na aba")
    icon: str = Field("📝", description="Emoji/ícone da aba")
    description: str = Field("", description="Descrição da categoria")
    order: int = Field(99, description="Ordem de exibição")
    color: str = Field("default", description="Cor Ant Design (blue, cyan, purple, etc)")

    class Config:
        json_schema_extra = {
            "example": {
                "key": "monitoring",
                "label": "Monitoramento",
                "icon": "📊",
                "description": "Campos relacionados a monitoramento",
                "order": 7,
                "color": "green"
            }
        }


class UpdateCategoryRequest(BaseModel):
    """Request para atualizar categoria"""
    label: Optional[str] = Field(None, description="Nome exibido")
    icon: Optional[str] = Field(None, description="Emoji/ícone")
    description: Optional[str] = Field(None, description="Descrição")
    order: Optional[int] = Field(None, description="Ordem")
    color: Optional[str] = Field(None, description="Cor")

    class Config:
        json_schema_extra = {
            "example": {
                "label": "Monitoramento Avançado",
                "icon": "📈",
                "description": "Campos de monitoramento e observabilidade",
                "order": 5,
                "color": "cyan"
            }
        }


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

    DINÂMICO: Categorias são carregadas do Consul KV (skills/eye/metadata/categories.json).
    Se KV vazio, retorna categorias padrão como fallback.

    Categorias organizam campos em abas temáticas na página Reference Values.
    """
    manager = CategoryManager()
    categories = await manager.get_all_categories()

    return {
        "success": True,
        "total": len(categories),
        "categories": categories
    }


@router.post("/categories", include_in_schema=True)
async def create_category(
    request: CreateCategoryRequest,
    user: str = Query("system", description="Usuário criando categoria")
):
    """
    Cria nova categoria.

    VALIDAÇÕES:
    - Key único (não pode duplicar)
    - Key deve ser lowercase, sem espaços
    - Label obrigatório

    Example:
        POST /api/v1/reference-values/categories
        {
            "key": "monitoring",
            "label": "Monitoramento",
            "icon": "📊",
            "description": "Campos de monitoramento",
            "order": 7,
            "color": "green"
        }
    """
    manager = CategoryManager()

    success, message = await manager.create_category(
        key=request.key,
        label=request.label,
        icon=request.icon,
        description=request.description,
        order=request.order,
        color=request.color,
        user=user
    )

    if not success:
        raise HTTPException(status_code=400, detail=message)

    return {
        "success": True,
        "message": message
    }


@router.post("/categories/reset", include_in_schema=True)
async def reset_categories_to_defaults(
    user: str = Query("system", description="Usuário executando reset")
):
    """
    Restaura categorias padrão (apaga customizações).

    CUIDADO: Esta operação remove TODAS as categorias customizadas!
    Útil para resetar após testes ou quando categorias ficarem inconsistentes.
    """
    manager = CategoryManager()

    success, message = await manager.reset_to_defaults(user=user)

    if not success:
        raise HTTPException(status_code=400, detail=message)

    return {
        "success": True,
        "message": message
    }


@router.put("/categories/{key}", include_in_schema=True)
async def update_category(
    key: str,
    request: UpdateCategoryRequest,
    user: str = Query("system", description="Usuário atualizando")
):
    """
    Atualiza categoria existente.

    IMPORTANTE: Não permite alterar 'key' (ID da categoria).
    Para renomear key, delete a categoria antiga e crie uma nova.

    Example:
        PUT /api/v1/reference-values/categories/monitoring
        {
            "label": "Monitoramento Avançado",
            "icon": "📈",
            "order": 5
        }
    """
    manager = CategoryManager()

    # Montar dict com apenas campos não-None
    updates = {}
    if request.label is not None:
        updates['label'] = request.label
    if request.icon is not None:
        updates['icon'] = request.icon
    if request.description is not None:
        updates['description'] = request.description
    if request.order is not None:
        updates['order'] = request.order
    if request.color is not None:
        updates['color'] = request.color

    if not updates:
        raise HTTPException(status_code=400, detail="Nenhum campo para atualizar")

    success, message = await manager.update_category(
        key=key,
        updates=updates,
        user=user
    )

    if not success:
        raise HTTPException(status_code=400, detail=message)

    return {
        "success": True,
        "message": message
    }


@router.delete("/categories/{key}", include_in_schema=True)
async def delete_category(
    key: str,
    user: str = Query("system", description="Usuário deletando"),
    force: bool = Query(False, description="Forçar deleção mesmo se em uso")
):
    """
    Deleta categoria.

    PROTEÇÃO: Bloqueia deleção se categoria tem campos associados.
    Use force=true para forçar deleção.

    Example:
        DELETE /api/v1/reference-values/categories/monitoring?force=false
    """
    manager = CategoryManager()

    success, message = await manager.delete_category(
        key=key,
        user=user,
        force=force
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
