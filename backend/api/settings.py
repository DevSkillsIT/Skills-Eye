"""
API de Settings - Configurações globais da aplicação

Expõe e gerencia configurações do backend
"""
import os
import json
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional
from core.kv_manager import KVManager
from core.yaml_config_service import YamlConfigService
import logging

logger = logging.getLogger(__name__)
yaml_service = YamlConfigService()

router = APIRouter(prefix="/settings", tags=["Settings"])
kv = KVManager()

# Namespace KV para settings
SETTINGS_KV_PATH = "skills/eye/settings/"
SITES_KV_KEY = f"{SETTINGS_KV_PATH}sites"


# ============================================================================
# MODELOS PYDANTIC
# ============================================================================

class SiteConfig(BaseModel):
    """
    Configuração de um site/servidor Prometheus

    IMPORTANTE: external_labels são adicionados automaticamente no Meta dos serviços
    registrados neste site, permitindo que o Prometheus identifique a origem.
    """
    code: str = Field(..., description="Código do site (ex: rio, palmas, dtc)")
    name: str = Field(..., description="Nome descritivo (ex: Rio de Janeiro)")
    is_default: bool = Field(False, description="Se é o site padrão (sem sufixo)")
    color: Optional[str] = Field(None, description="Cor do badge no frontend")
    prometheus_host: Optional[str] = Field(None, description="Host/IP do servidor Prometheus desse site")
    prometheus_port: Optional[int] = Field(9090, description="Porta do Prometheus")
    external_labels: Optional[dict] = Field(
        None,
        description="External labels do prometheus.yml desse servidor (cluster, datacenter, environment, site, etc.)"
    )


class SitesListResponse(BaseModel):
    """Lista de sites configurados"""
    sites: List[SiteConfig]


class NamingConfigUpdate(BaseModel):
    """Atualização da naming config"""
    naming_strategy: Optional[str] = Field(None, description="option1 ou option2")
    suffix_enabled: Optional[bool] = Field(None, description="Habilitar sufixos automáticos")
    default_site: Optional[str] = Field(None, description="Site padrão sem sufixo")


# ============================================================================
# SITES DEFAULT (Fallback se KV estiver vazio)
# ============================================================================

DEFAULT_SITES = [
    {"code": "palmas", "name": "Palmas (TO)", "is_default": True, "color": "blue"},
    {"code": "rio", "name": "Rio de Janeiro (RJ)", "is_default": False, "color": "green"},
    {"code": "dtc", "name": "DTC/Genesis", "is_default": False, "color": "orange"},
    {"code": "genesis", "name": "Genesis (Alternativo)", "is_default": False, "color": "purple"},
]


# ============================================================================
# HELPERS
# ============================================================================

async def get_sites_from_kv() -> List[dict]:
    """Busca sites do Consul KV"""
    try:
        data = await kv.get_json(SITES_KV_KEY)
        if data and "sites" in data:
            return data["sites"]
    except Exception as e:
        logger.warning(f"[Settings] Erro ao buscar sites do KV: {e}")

    # Fallback para sites default
    return DEFAULT_SITES


async def save_sites_to_kv(sites: List[dict]) -> bool:
    """Salva sites no Consul KV"""
    try:
        await kv.put_json(SITES_KV_KEY, {"sites": sites})
        return True
    except Exception as e:
        logger.error(f"[Settings] Erro ao salvar sites no KV: {e}")
        return False


# ============================================================================
# ENDPOINTS - NAMING CONFIG
# ============================================================================

@router.get("/naming-config")
async def get_naming_config():
    """
    Retorna configuração de naming strategy multi-site

    Usado pelo frontend para sincronizar lógica de sufixos
    com a configuração do backend

    Returns:
        {
            naming_strategy: 'option1' | 'option2',
            suffix_enabled: bool,
            default_site: str
        }
    """
    naming_strategy = os.getenv("NAMING_STRATEGY", "option2")
    suffix_enabled = os.getenv("SITE_SUFFIX_ENABLED", "true").lower() == "true"
    default_site = os.getenv("DEFAULT_SITE", "palmas").lower()

    # Buscar sites do KV para retornar também
    sites = await get_sites_from_kv()

    return {
        "naming_strategy": naming_strategy,
        "suffix_enabled": suffix_enabled,
        "default_site": default_site,
        "sites": sites  # Incluir lista de sites disponíveis
    }


# ============================================================================
# ENDPOINTS - SITES CRUD
# ============================================================================

@router.get("/sites", response_model=SitesListResponse)
async def get_sites():
    """
    Lista todos os sites configurados

    Returns:
        Lista de sites com code, name, is_default, color

    NOTA: External labels dos servidores Prometheus estão disponíveis
    no endpoint /settings/prometheus-servers
    """
    sites = await get_sites_from_kv()
    return {"sites": sites}


@router.post("/sites", response_model=SiteConfig)
async def create_site(site: SiteConfig):
    """
    Adiciona um novo site à configuração

    Args:
        site: Configuração do novo site

    Returns:
        Site criado
    """
    sites = await get_sites_from_kv()

    # Validar se code já existe
    if any(s["code"] == site.code for s in sites):
        raise HTTPException(
            status_code=400,
            detail=f"Site com código '{site.code}' já existe"
        )

    # Se marcar como default, desmarcar os outros
    if site.is_default:
        for s in sites:
            s["is_default"] = False

    # Adicionar novo site (prometheus_host/port são opcionais, external_labels vêm do prometheus.yml)
    sites.append(site.model_dump(exclude_none=False, exclude={"external_labels"}))

    # Salvar no KV
    if not await save_sites_to_kv(sites):
        raise HTTPException(
            status_code=500,
            detail="Erro ao salvar site no Consul KV"
        )

    logger.info(f"[Settings] Site criado: {site.code}")
    return site


@router.put("/sites/{code}", response_model=SiteConfig)
async def update_site(code: str, site: SiteConfig):
    """
    Atualiza um site existente

    Args:
        code: Código do site a atualizar
        site: Novos dados do site

    Returns:
        Site atualizado
    """
    sites = await get_sites_from_kv()

    # Encontrar site
    site_index = None
    for i, s in enumerate(sites):
        if s["code"] == code:
            site_index = i
            break

    if site_index is None:
        raise HTTPException(
            status_code=404,
            detail=f"Site '{code}' não encontrado"
        )

    # Se marcar como default, desmarcar os outros
    if site.is_default:
        for s in sites:
            s["is_default"] = False

    # Atualizar site (prometheus_host/port são salvos, external_labels NÃO - vêm do prometheus.yml)
    sites[site_index] = site.model_dump(exclude_none=False, exclude={"external_labels"})

    # Salvar no KV
    if not await save_sites_to_kv(sites):
        raise HTTPException(
            status_code=500,
            detail="Erro ao salvar alterações no Consul KV"
        )

    logger.info(f"[Settings] Site atualizado: {code}")
    return site


@router.delete("/sites/{code}")
async def delete_site(code: str):
    """
    Remove um site da configuração

    Args:
        code: Código do site a remover

    Returns:
        Mensagem de sucesso
    """
    sites = await get_sites_from_kv()

    # Encontrar e remover site
    original_len = len(sites)
    sites = [s for s in sites if s["code"] != code]

    if len(sites) == original_len:
        raise HTTPException(
            status_code=404,
            detail=f"Site '{code}' não encontrado"
        )

    # Validar que pelo menos um site permanece
    if len(sites) == 0:
        raise HTTPException(
            status_code=400,
            detail="Não é possível remover o último site"
        )

    # Garantir que existe pelo menos um default
    if not any(s.get("is_default", False) for s in sites):
        sites[0]["is_default"] = True
        logger.info(f"[Settings] Site '{sites[0]['code']}' marcado como default automaticamente")

    # Salvar no KV
    if not await save_sites_to_kv(sites):
        raise HTTPException(
            status_code=500,
            detail="Erro ao salvar alterações no Consul KV"
        )

    logger.info(f"[Settings] Site removido: {code}")
    return {"message": f"Site '{code}' removido com sucesso", "deleted": code}


# ENDPOINT DESABILITADO - NÃO USAR SSH AQUI
# Settings deve ler do Consul KV (skills/eye/metadata/fields.json)
# Dados são salvos automaticamente quando /prometheus-config/fields é chamado
#
# @router.get("/prometheus-servers")
# async def get_prometheus_servers_with_external_labels():
#     """
#     DEPRECATED - Use /api/v1/kv/metadata/fields em vez disso
#
#     Este endpoint fazia SSH desnecessário. Agora os dados vêm do KV.
#     """
#     pass


# External labels são buscados AUTOMATICAMENTE no GET /sites
# NÃO precisam ser salvos no KV (são visualização em tempo real do prometheus.yml)
