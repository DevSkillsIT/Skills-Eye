"""
API endpoints para gerenciamento do Consul KV

IMPORTANTE:
- Leitura (/tree, /value): Permite acesso a QUALQUER namespace para navegação
- Escrita (/value POST, DELETE): Restrito a 'skills/eye/' por segurança
"""
from fastapi import APIRouter, HTTPException, Query, status
from typing import Any, Dict, Optional
import logging

from core.consul_manager import ConsulManager
from .models import KVPutRequest

router = APIRouter(tags=["Key-Value Store"])
logger = logging.getLogger(__name__)

# Prefixo principal da aplicação (usado para validação de escrita)
PRIMARY_PREFIX = "skills/eye/"

# Prefixos permitidos para leitura (navegação)
ALLOWED_READ_PREFIXES = [
    "skills/eye/",
    "config/",
    "services/",
    "apps/",
    "",  # Root - permite ver tudo
]


def _validate_prefix_read(path: str) -> None:
    """
    Validação leve para operações de LEITURA (GET).
    Permite navegação em qualquer namespace, mas loga acessos fora do padrão.
    """
    if path is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Prefixo/Chave não pode ser None",
        )

    # Log de acesso a namespaces fora do padrão
    if path and not path.startswith(PRIMARY_PREFIX):
        logger.info(f"Acesso a namespace fora de '{PRIMARY_PREFIX}': {path}")


def _validate_prefix_write(path: str) -> None:
    """
    Validação RESTRITA para operações de ESCRITA (POST, DELETE).
    Apenas permite modificações em 'skills/eye/' por segurança.
    """
    if not path:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Prefixo/Chave não pode ser vazio",
        )
    if not path.startswith(PRIMARY_PREFIX):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Operações de escrita permitidas apenas em '{PRIMARY_PREFIX}'",
        )


@router.get("/tree")
async def get_tree(prefix: str = Query(..., description="Prefixo do KV")) -> Dict[str, Any]:
    """
    Retorna todas as chaves/valores de um prefixo com metadados (CreateIndex, ModifyIndex).

    PERMITE navegação em QUALQUER namespace do Consul KV.

    Response format:
        {
            "success": true,
            "prefix": "skills/eye/",
            "data": {
                "skills/eye/metadata/fields": {
                    "value": {...},
                    "metadata": {
                        "CreateIndex": 12345,
                        "ModifyIndex": 67890,
                        ...
                    }
                }
            }
        }
    """
    _validate_prefix_read(prefix)
    consul = ConsulManager()
    data = await consul.get_kv_tree(prefix, include_metadata=True)
    return {"success": True, "prefix": prefix, "data": data}


@router.get("/value")
async def get_value(key: str = Query(..., description="Chave completa do KV")) -> Dict[str, Any]:
    """
    Retorna o valor (JSON) de uma chave específica.

    PERMITE leitura de QUALQUER namespace do Consul KV.
    """
    _validate_prefix_read(key)
    consul = ConsulManager()
    value = await consul.get_kv_json(key)
    if value is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chave não encontrada")
    return {"success": True, "key": key, "value": value}


@router.post("/value")
async def put_value(payload: KVPutRequest) -> Dict[str, Any]:
    """
    Grava/atualiza um valor JSON em uma chave específica.

    RESTRITO a 'skills/eye/' por segurança.
    """
    _validate_prefix_write(payload.key)
    consul = ConsulManager()
    ok = await consul.put_kv_json(payload.key, payload.value)
    if not ok:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Falha ao gravar no Consul")
    return {"success": True, "key": payload.key, "value": payload.value}


@router.delete("/value")
async def delete_value(key: str = Query(..., description="Chave completa do KV")) -> Dict[str, Any]:
    """
    Remove uma chave (se existir).

    RESTRITO a 'skills/eye/' por segurança.
    """
    _validate_prefix_write(key)
    consul = ConsulManager()
    deleted = await consul.delete_key(key)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chave não encontrada ou falha ao remover")
    return {"success": True, "key": key}
