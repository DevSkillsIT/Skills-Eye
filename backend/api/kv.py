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
from .models import KVPutRequest, FieldConfigUpdate

router = APIRouter()
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
    Retorna todas as chaves/valores de um prefixo (JSON quando possível).

    PERMITE navegação em QUALQUER namespace do Consul KV.
    """
    _validate_prefix_read(prefix)
    consul = ConsulManager()
    data = await consul.get_kv_tree(prefix)
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


# ============================================================================
# ENDPOINTS ESPECÍFICOS PARA FIELD-CONFIG (CONFIGURAÇÃO DE EXIBIÇÃO POR PÁGINA)
# ============================================================================

@router.get("/metadata/field-config/{field_name}")
async def get_field_config(field_name: str) -> Dict[str, Any]:
    """
    Retorna a configuração de exibição de um campo específico.

    Args:
        field_name: Nome do campo (ex: "cluster", "site", "modelo")

    Returns:
        Configuração com show_in_services, show_in_exporters, show_in_blackbox

    Exemplo:
        GET /api/v1/kv/metadata/field-config/modelo
        {
            "success": true,
            "field_name": "modelo",
            "config": {
                "show_in_services": true,
                "show_in_exporters": true,
                "show_in_blackbox": false
            }
        }
    """
    key = f"{PRIMARY_PREFIX}metadata/field-config/{field_name}"
    consul = ConsulManager()

    value = await consul.get_kv_json(key)

    # Se não existe, retornar configuração padrão (todos habilitados)
    if value is None:
        default_config = {
            "show_in_services": True,
            "show_in_exporters": True,
            "show_in_blackbox": True,
        }
        return {
            "success": True,
            "field_name": field_name,
            "config": default_config,
            "is_default": True
        }

    return {
        "success": True,
        "field_name": field_name,
        "config": value,
        "is_default": False
    }


@router.put("/metadata/field-config/{field_name}")
async def update_field_config(field_name: str, config: FieldConfigUpdate) -> Dict[str, Any]:
    """
    Atualiza a configuração COMPLETA de um campo metadata.

    IMPORTANTE: Aceita TODOS os campos de configuração do campo (não apenas show_in_*)

    Args:
        field_name: Nome técnico do campo
        config: Objeto com configurações (display_name, category, show_in_*, etc)

    Body esperado (todos os campos são opcionais):
        {
            "display_name": "Sistema Operacional",
            "description": "Sistema operacional do servidor",
            "category": "Infraestrutura",
            "field_type": "select",
            "order": 10,
            "required": false,
            "show_in_table": true,
            "show_in_dashboard": true,
            "show_in_form": true,
            "editable": true,
            "show_in_services": true,
            "show_in_exporters": true,
            "show_in_blackbox": false
        }

    Returns:
        Sucesso e configuração salva
    """
    key = f"{PRIMARY_PREFIX}metadata/field-config/{field_name}"

    # Converter Pydantic model para dict, excluindo valores None (não enviados)
    config_dict = config.model_dump(exclude_none=True)

    if not config_dict:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nenhuma configuração foi fornecida"
        )

    consul = ConsulManager()

    # Tentar ler configuração existente para fazer merge (atualização parcial)
    existing_config = await consul.get_kv_json(key)
    if existing_config:
        # Merge: atualiza apenas os campos enviados
        merged_config = {**existing_config, **config_dict}
    else:
        # Primeira vez salvando: usar apenas os valores enviados
        merged_config = config_dict

    # Salvar configuração atualizada
    ok = await consul.put_kv_json(key, merged_config)

    if not ok:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Falha ao salvar configuração no Consul KV"
        )

    return {
        "success": True,
        "field_name": field_name,
        "config": merged_config,
        "message": f"Configuração do campo '{field_name}' atualizada com sucesso"
    }
