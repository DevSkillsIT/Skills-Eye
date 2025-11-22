"""
API Admin - Endpoints administrativos para operacoes de manutencao

SPEC-PERF-001 (2025-11-21) - Problema 2: Invalidacao de Cache

ENDPOINTS:
- POST /api/v1/admin/cache/nodes/flush - Invalidar cache de nodes manualmente

IMPORTANTE - LIMITACAO DE CACHE LOCAL:
Este sistema utiliza cache LOCAL em memoria (por instancia da aplicacao).
Em ambientes com multiplas instancias (load balancer, docker swarm, k8s),
cada instancia mantem seu proprio cache. A invalidacao via este endpoint
afeta APENAS a instancia que recebeu a requisicao.

Para invalidar cache em TODAS as instancias em ambiente distribuido:
1. Chamar o endpoint em cada instancia separadamente, ou
2. Implementar mecanismo de invalidacao distribuida (Redis pub/sub, etc)

CASOS DE USO:
- Forcas atualizacao apos mudancas no membership do Consul
- Resolver inconsistencias de dados pos-manutencao
- Debug e troubleshooting em producao
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Dict, Any, List
from datetime import datetime
import logging

from core.cache_manager import get_cache

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Admin"])


# ============================================================================
# MODELOS PYDANTIC
# ============================================================================

class FlushResponse(BaseModel):
    """Response padrao para operacoes de flush de cache."""
    success: bool = Field(..., description="Se a operacao foi bem sucedida")
    message: str = Field(..., description="Mensagem descritiva do resultado")
    keys_flushed: int = Field(..., description="Numero de chaves invalidadas")
    flushed_at: str = Field(..., description="Timestamp ISO8601 da operacao")
    warning: str = Field(
        None,
        description="Aviso sobre limitacoes (ex: cache local em ambiente distribuido)"
    )


class CacheKeysInfo(BaseModel):
    """Informacoes sobre chaves de cache de nodes."""
    nodes_cache_key: str = Field(..., description="Chave principal do cache de nodes")
    sites_cache_key: str = Field(..., description="Chave do cache de sites")
    nodes_ttl_seconds: int = Field(..., description="TTL do cache de nodes")
    sites_ttl_seconds: int = Field(..., description="TTL do cache de sites")


# ============================================================================
# ENDPOINTS ADMINISTRATIVOS
# ============================================================================

@router.post("/admin/cache/nodes/flush", response_model=FlushResponse, tags=["Admin"])
async def flush_nodes_cache():
    """
    Invalida o cache de nodes manualmente.

    **Quando usar:**
    - Apos mudancas no membership do Consul (novos nodes adicionados/removidos)
    - Apos manutencao em nodes do cluster
    - Para forcar atualizacao imediata sem esperar expiracao do TTL (60s)
    - Debug e troubleshooting de dados inconsistentes

    **Chaves invalidadas:**
    - `nodes:list:all` - Lista completa de nodes do cluster
    - `sites:map:all` - Mapeamento IP -> site_name

    **IMPORTANTE - Limitacao de Cache Local:**
    Este endpoint invalida o cache APENAS na instancia que recebeu a requisicao.
    Em ambientes com multiplas instancias (load balancer), cada instancia
    mantem cache separado. Para invalidar em todas as instancias:
    1. Chame este endpoint em cada instancia, ou
    2. Considere implementar invalidacao distribuida (Redis pub/sub)

    **Response:**
    - success: Se a operacao foi bem sucedida
    - message: Descricao do resultado
    - keys_flushed: Numero de chaves removidas do cache
    - flushed_at: Timestamp da operacao
    - warning: Aviso sobre limitacoes em ambiente distribuido

    **Exemplo de uso:**
    ```bash
    curl -X POST http://localhost:5000/api/v1/admin/cache/nodes/flush
    ```
    """
    try:
        # PASSO 1: Obter instancia do cache global
        # Usa mesma instancia que nodes.py para garantir invalidacao correta
        cache = get_cache()

        # PASSO 2: Definir chaves a serem invalidadas
        # Estas chaves sao usadas em backend/api/nodes.py
        nodes_cache_key = "nodes:list:all"
        sites_cache_key = "sites:map:all"

        keys_flushed = 0

        # PASSO 3: Invalidar cache de nodes
        # Chave principal usada em get_nodes()
        nodes_removed = await cache.invalidate(nodes_cache_key)
        if nodes_removed:
            keys_flushed += 1
            logger.info(f"[Admin] Cache de nodes invalidado: {nodes_cache_key}")
        else:
            logger.debug(f"[Admin] Cache de nodes nao estava em cache: {nodes_cache_key}")

        # PASSO 4: Invalidar cache de sites
        # Usado para mapeamento IP -> site_name
        sites_removed = await cache.invalidate(sites_cache_key)
        if sites_removed:
            keys_flushed += 1
            logger.info(f"[Admin] Cache de sites invalidado: {sites_cache_key}")
        else:
            logger.debug(f"[Admin] Cache de sites nao estava em cache: {sites_cache_key}")

        # PASSO 5: Montar mensagem de resultado
        if keys_flushed > 0:
            message = (
                f"Cache de nodes invalidado com sucesso. "
                f"{keys_flushed} chave(s) removida(s). "
                f"Proxima requisicao buscara dados frescos do Consul."
            )
        else:
            message = (
                "Nenhuma chave de cache encontrada para invalidar. "
                "Cache pode ja estar vazio ou expirado."
            )

        # PASSO 6: Log da operacao administrativa
        logger.info(
            f"[Admin] Flush de cache de nodes executado: "
            f"keys_flushed={keys_flushed}, "
            f"nodes_removed={nodes_removed}, "
            f"sites_removed={sites_removed}"
        )

        return FlushResponse(
            success=True,
            message=message,
            keys_flushed=keys_flushed,
            flushed_at=datetime.utcnow().isoformat() + "Z",
            warning=(
                "ATENCAO: Este endpoint invalida cache APENAS nesta instancia. "
                "Em ambiente com multiplas instancias, chame em cada uma separadamente."
            )
        )

    except Exception as e:
        # Registrar erro completo para debug
        logger.error(f"[Admin] Erro ao invalidar cache de nodes: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao invalidar cache de nodes: {str(e)}"
        )


@router.get("/admin/cache/nodes/info", response_model=CacheKeysInfo, tags=["Admin"])
async def get_nodes_cache_info():
    """
    Retorna informacoes sobre as chaves de cache de nodes.

    **Util para:**
    - Entender estrutura do cache
    - Debugging
    - Documentacao

    **Retorna:**
    - Chaves utilizadas
    - TTLs configurados
    """
    from core.config import Config

    return CacheKeysInfo(
        nodes_cache_key="nodes:list:all",
        sites_cache_key="sites:map:all",
        nodes_ttl_seconds=60,
        sites_ttl_seconds=Config.SITES_CACHE_TTL
    )
