"""Rotas para visualização de arquivos de configuração remotos."""

from fastapi import APIRouter, HTTPException, Query
from fastapi.concurrency import run_in_threadpool

from .models import (
    ConfigFileContentResponse,
    ConfigFileListResponse,
    ConfigHostListResponse,
)
from core.config_file_manager import ConfigFileManager

router = APIRouter()
config_file_manager = ConfigFileManager()


@router.get("/hosts", response_model=ConfigHostListResponse)
async def list_config_hosts():
    """Retorna a lista de servidores configurados."""
    hosts = config_file_manager.list_hosts()
    return {"success": True, "hosts": hosts}


@router.get("/{host_id}", response_model=ConfigFileListResponse)
async def list_config_files(host_id: str):
    """Lista os arquivos permitidos para o host informado."""
    try:
        files = await run_in_threadpool(config_file_manager.list_files, host_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (PermissionError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ConnectionError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return {"success": True, "files": files}


@router.get("/{host_id}/content", response_model=ConfigFileContentResponse)
async def get_config_file(host_id: str, path: str = Query(..., description="Caminho completo do arquivo")):
    """Retorna o conteúdo de um arquivo específico."""
    try:
        content = await run_in_threadpool(config_file_manager.read_file, host_id, path)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (ConnectionError, ValueError) as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return {"success": True, "content": content}

