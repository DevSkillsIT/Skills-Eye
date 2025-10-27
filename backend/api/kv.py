"""
API endpoints para gerenciamento seguro do Consul KV (prefixo skills/cm/)
"""
from fastapi import APIRouter, HTTPException, Query, status
from typing import Any, Dict, Optional

from core.consul_manager import ConsulManager
from .models import KVPutRequest

router = APIRouter()

ALLOWED_PREFIX = "skills/cm/"


def _validate_prefix(path: str) -> None:
    if not path:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Prefixo/Chave não pode ser vazio",
        )
    if not path.startswith(ALLOWED_PREFIX):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Apenas chaves iniciando com '{ALLOWED_PREFIX}' são permitidas",
        )


@router.get("/tree")
async def get_tree(prefix: str = Query(..., description="Prefixo do KV")) -> Dict[str, Any]:
    """
    Retorna todas as chaves/valores de um prefixo (JSON quando possível).
    """
    _validate_prefix(prefix)
    consul = ConsulManager()
    data = await consul.get_kv_tree(prefix)
    return {"success": True, "prefix": prefix, "data": data}


@router.get("/value")
async def get_value(key: str = Query(..., description="Chave completa do KV")) -> Dict[str, Any]:
    """
    Retorna o valor (JSON) de uma chave específica.
    """
    _validate_prefix(key)
    consul = ConsulManager()
    value = await consul.get_kv_json(key)
    if value is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chave não encontrada")
    return {"success": True, "key": key, "value": value}


@router.post("/value")
async def put_value(payload: KVPutRequest) -> Dict[str, Any]:
    """
    Grava/atualiza um valor JSON em uma chave específica.
    """
    _validate_prefix(payload.key)
    consul = ConsulManager()
    ok = await consul.put_kv_json(payload.key, payload.value)
    if not ok:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Falha ao gravar no Consul")
    return {"success": True, "key": payload.key, "value": payload.value}


@router.delete("/value")
async def delete_value(key: str = Query(..., description="Chave completa do KV")) -> Dict[str, Any]:
    """
    Remove uma chave (se existir).
    """
    _validate_prefix(key)
    consul = ConsulManager()
    deleted = await consul.delete_key(key)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chave não encontrada ou falha ao remover")
    return {"success": True, "key": key}
