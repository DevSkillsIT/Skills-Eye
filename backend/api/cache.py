"""
API Cache Management - Endpoints para controle do LocalCache

SPRINT 2 (2025-11-15)

Endpoints:
- GET /api/v1/cache/stats - Estatísticas do cache (hits, misses, hit rate)
- POST /api/v1/cache/invalidate - Invalidar chave específica
- POST /api/v1/cache/invalidate-pattern - Invalidar por padrão (wildcards)
- POST /api/v1/cache/clear - Limpar TODO o cache
- GET /api/v1/cache/keys - Listar todas as chaves (debug)
- GET /api/v1/cache/entry/{key} - Detalhes de uma entrada
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List

from core.cache_manager import get_cache

router = APIRouter()


# ============================================================================
# MODELOS PYDANTIC
# ============================================================================

class CacheStatsResponse(BaseModel):
    """Estatísticas do cache."""
    hits: int = Field(..., description="Total de cache hits")
    misses: int = Field(..., description="Total de cache misses")
    evictions: int = Field(..., description="Total de evictions (expirados)")
    invalidations: int = Field(..., description="Total de invalidações manuais")
    hit_rate_percent: float = Field(..., description="Taxa de hit em % (0-100)")
    total_requests: int = Field(..., description="Total de requisições ao cache")
    current_size: int = Field(..., description="Número de entradas no cache")
    ttl_seconds: int = Field(..., description="TTL padrão do cache em segundos")


class InvalidateRequest(BaseModel):
    """Request para invalidar uma chave."""
    key: str = Field(..., description="Chave a invalidar", example="services:catalog:all")


class InvalidatePatternRequest(BaseModel):
    """Request para invalidar por padrão."""
    pattern: str = Field(
        ...,
        description="Padrão de busca (suporta wildcards *)",
        example="services:*"
    )


class InvalidateResponse(BaseModel):
    """Response de invalidação."""
    success: bool
    message: str
    keys_removed: int


class CacheEntryInfo(BaseModel):
    """Informações sobre uma entrada do cache."""
    key: str
    age_seconds: float
    ttl_seconds: int
    remaining_seconds: float
    is_expired: bool
    timestamp: str
    value_type: str
    value_size_bytes: int


# ============================================================================
# ENDPOINTS
# ============================================================================

@router.get("/cache/stats", response_model=CacheStatsResponse, tags=["Cache"])
async def get_cache_stats():
    """
    Retorna estatísticas do cache local.

    **Retorna:**
    - hits: Total de cache hits
    - misses: Total de cache misses
    - hit_rate_percent: Taxa de acerto (0-100%)
    - current_size: Número de entradas no cache
    - ttl_seconds: TTL padrão do cache

    **Use Case:**
    - Monitorar eficiência do cache
    - Identificar se cache está sendo utilizado
    - Ajustar TTL se hit rate muito baixo
    """
    cache = get_cache()
    stats = await cache.get_stats()
    return stats


@router.post("/cache/invalidate", response_model=InvalidateResponse, tags=["Cache"])
async def invalidate_cache_key(request: InvalidateRequest):
    """
    Invalida uma chave específica do cache.

    **Parâmetros:**
    - key: Chave exata a invalidar

    **Exemplo:**
    ```json
    {
      "key": "services:catalog:all"
    }
    ```

    **Use Case:**
    - Forçar refresh de dados após atualização
    - Limpar cache de endpoint específico
    """
    cache = get_cache()
    removed = await cache.invalidate(request.key)

    if not removed:
        return InvalidateResponse(
            success=False,
            message=f"Chave '{request.key}' não encontrada no cache",
            keys_removed=0
        )

    return InvalidateResponse(
        success=True,
        message=f"Chave '{request.key}' invalidada com sucesso",
        keys_removed=1
    )


@router.post("/cache/invalidate-pattern", response_model=InvalidateResponse, tags=["Cache"])
async def invalidate_cache_pattern(request: InvalidatePatternRequest):
    """
    Invalida todas as chaves que correspondem ao padrão.

    **Suporta wildcards:**
    - `services:*` - Todas as chaves começando com "services:"
    - `*:catalog` - Todas as chaves terminando com ":catalog"
    - `*blackbox*` - Todas as chaves contendo "blackbox"

    **Exemplo:**
    ```json
    {
      "pattern": "services:*"
    }
    ```

    **Use Case:**
    - Invalidar todo cache de uma categoria (ex: todos os serviços)
    - Limpar cache relacionado a um recurso específico
    """
    cache = get_cache()
    count = await cache.invalidate_pattern(request.pattern)

    return InvalidateResponse(
        success=True,
        message=f"Invalidadas {count} chaves correspondentes ao padrão '{request.pattern}'",
        keys_removed=count
    )


@router.post("/cache/clear", response_model=InvalidateResponse, tags=["Cache"])
async def clear_all_cache():
    """
    **⚠️ ATENÇÃO: LIMPA TODO O CACHE!**

    Remove TODAS as entradas do cache. Use com cautela!

    **Use Case:**
    - Debug/troubleshooting
    - Forçar refresh completo do sistema
    - Após mudanças significativas na configuração

    **Efeito:**
    - Próximas requisições serão mais lentas (cache miss)
    - Cache será reconstruído conforme uso
    """
    cache = get_cache()
    count = await cache.clear()

    return InvalidateResponse(
        success=True,
        message=f"Cache completamente limpo. {count} entradas removidas.",
        keys_removed=count
    )


@router.get("/cache/keys", response_model=List[str], tags=["Cache"])
async def get_cache_keys():
    """
    Lista todas as chaves atualmente no cache.

    **Use Case:**
    - Debug/troubleshooting
    - Ver quais dados estão cacheados
    - Identificar chaves para invalidação específica

    **Retorna:**
    - Lista de strings (chaves)
    """
    cache = get_cache()
    keys = await cache.get_keys()
    return keys


@router.get("/cache/entry/{key}", response_model=Optional[CacheEntryInfo], tags=["Cache"])
async def get_cache_entry_info(key: str):
    """
    Retorna informações detalhadas sobre uma entrada do cache.

    **Parâmetros:**
    - key: Chave a consultar

    **Retorna:**
    - age_seconds: Idade do cache
    - ttl_seconds: TTL configurado
    - remaining_seconds: Tempo restante até expirar
    - is_expired: Se já expirou
    - value_type: Tipo do valor (dict, list, str, etc)
    - value_size_bytes: Tamanho aproximado em bytes

    **Use Case:**
    - Debug de cache específico
    - Ver se cache está próximo de expirar
    - Verificar tamanho de payloads cacheados
    """
    cache = get_cache()
    info = await cache.get_entry_info(key)

    if info is None:
        raise HTTPException(
            status_code=404,
            detail=f"Chave '{key}' não encontrada no cache"
        )

    return info
