"""
API de Settings - Configurações globais da aplicação (MINIMAL)

NOTA: Endpoints de CRUD de sites foram MOVIDOS para metadata_fields_manager.py
Este arquivo mantém APENAS o endpoint de naming-config que ainda é usado por:
- frontend/src/pages/MetadataFields.tsx
- frontend/src/utils/namingUtils.ts
"""
import os
from fastapi import APIRouter
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/settings", tags=["Settings"])


# MODELOS E HELPERS REMOVIDOS
# Sites são gerenciados em metadata_fields_manager.py


# ============================================================================
# ENDPOINTS - NAMING CONFIG
# ============================================================================

@router.get("/naming-config")
async def get_naming_config():
    """
    Retorna configuração de naming strategy multi-site
    
    ✅ REFATORADO (2025-11-12): Agora lê do KV com fallback para .env

    Usado pelo frontend para sincronizar lógica de sufixos
    com a configuração do backend

    Returns:
        {
            naming_strategy: 'option1' | 'option2',
            suffix_enabled: bool,
            default_site: str
        }
    
    NOTA: Sites são buscados via /api/v1/metadata-fields/config/sites
    """
    from core.naming_utils import get_naming_config, get_default_site
    
    config = get_naming_config()
    
    return {
        "naming_strategy": config.get("naming_strategy", "option2"),
        "suffix_enabled": config.get("suffix_enabled", True),
        "default_site": get_default_site(),  # ✅ Dinâmico: busca site com is_default=true
    }


@router.get("/sites-config")
async def get_sites_config():
    """
    🆕 NOVO ENDPOINT (2025-11-12): Retorna configuração COMPLETA de sites + naming
    
    ✅ ACESSA DIRETAMENTE O KV (mesma lógica de /metadata-fields/config/sites que funciona)
    
    Combina dados de sites do KV com naming strategy em um único endpoint.
    Usado pelo frontend (hook useSites) para carregar toda configuração dinâmica.
    
    Returns:
        {
            "success": true,
            "sites": [...],
            "naming": {
                "strategy": "option2",
                "suffix_enabled": true
            },
            "default_site": "palmas",
            "total_sites": 3
        }
    
    FLUXO:
    1. Busca TUDO de skills/eye/metadata/sites (JSON unificado)
    2. Extrai sites de data.sites
    3. Extrai naming de data.naming_config
    4. Infere default_site do site com is_default=true
    """
    from core.kv_manager import KVManager
    
    try:
        kv = KVManager()
        
        # ✅ Buscar do KV (mesma lógica do endpoint que funciona)
        kv_data = await kv.get_json('skills/eye/metadata/sites') or {"data": {"sites": []}}
        
        # Estrutura pode ter wrapper 'data' ou ser direta
        if 'data' in kv_data:
            sites = kv_data.get('data', {}).get('sites', [])
            naming_config = kv_data.get('data', {}).get('naming_config', {})
        else:
            sites = kv_data.get('sites', [])
            naming_config = {}
        
        # Buscar default_site dinamicamente (APENAS do KV, sem fallbacks hardcoded)
        default_site = None
        for site in sites:
            if site.get("is_default", False):
                default_site = site["code"]
                break
        
        # ✅ Se não encontrou, usar primeiro site (se houver) OU None
        if not default_site and sites:
            default_site = sites[0]["code"]
            logger.warning(f"[SITES-CONFIG] ⚠️  Nenhum site is_default=true, usando primeiro: {default_site}")
        elif not default_site:
            logger.error("[SITES-CONFIG] ❌ Nenhum site configurado no KV!")
        
        # Simplificar estrutura de sites para frontend
        simplified_sites = []
        for site in sites:
            simplified_sites.append({
                "code": site.get("code"),
                "name": site.get("name"),
                "is_default": site.get("is_default", False),
                "color": site.get("color"),
                "cluster": site.get("cluster"),
                "datacenter": site.get("datacenter"),
                "prometheus_instance": site.get("prometheus_instance")
            })
        
        return {
            "success": True,
            "sites": simplified_sites,
            "naming": {
                # ✅ Padrões seguros (sem .env), mas prioriza KV
                "strategy": naming_config.get("strategy", "option2"),
                "suffix_enabled": naming_config.get("suffix_enabled", True)
            },
            "default_site": default_site,  # Pode ser None se não configurado
            "total_sites": len(simplified_sites)
        }
    
    except Exception as e:
        logger.error(f"❌ Erro ao carregar sites-config: {e}")
        import traceback
        traceback.print_exc()
        return {
            "success": False,
            "error": str(e),
            "sites": [],
            "naming": {
                "strategy": "option2",
                "suffix_enabled": True
            },
            "default_site": "palmas",
            "total_sites": 0
        }


# ============================================================================
# ENDPOINTS REMOVIDOS (MIGRADOS PARA metadata_fields_manager.py)
# ============================================================================
# 
# Os seguintes endpoints foram movidos para /api/v1/metadata-fields/config/sites:
# - GET    /settings/sites                    → GET    /metadata-fields/config/sites
# - POST   /settings/sites                    → (criar site automaticamente via sync)
# - PUT    /settings/sites/{code}             → PATCH  /metadata-fields/config/sites/{code}
# - DELETE /settings/sites/{code}             → DELETE /metadata-fields/config/sites/{code}
# - POST   /settings/sites/sync               → POST   /metadata-fields/config/sites/sync
#
# ============================================================================
