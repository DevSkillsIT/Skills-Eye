"""
Naming Utils - Utilitários para nomenclatura multi-site (100% DINÂMICO)

Gerencia sufixos automáticos em service names baseado na estratégia de naming
configurada no KV (com fallback para .env).

Estratégias:
- option1: Nomes iguais em todos os sites (requer filtros no Prometheus)
- option2: Nomes diferentes por site (sufixos automáticos)

MUDANÇAS (2025-11-12):
- ✅ Cache de sites do KV (TTL 60s)
- ✅ Cache de naming strategy do KV
- ✅ Inferência dinâmica de site por cluster
- ✅ Default site inferido de is_default=True
- ✅ Fallback para .env se KV indisponível
"""

import os
import logging
import time
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)

# ============================================================================
# CACHE GLOBAL (atualizado a cada 60s via background task)
# ============================================================================

_sites_cache: List[Dict[str, Any]] = []
_naming_cache: Dict[str, Any] = {}
_cache_last_update: float = 0
_cache_ttl: int = 60  # segundos
_cache_initialized: bool = False


# ============================================================================
# FUNÇÕES DE CARREGAMENTO DO KV
# ============================================================================

async def _load_sites_from_kv() -> List[Dict[str, Any]]:
    """
    Carrega sites do KV: skills/eye/metadata/sites
    
    Fallback para .env se KV não existir (backward compatibility)
    
    Returns:
        Lista de dicts com dados dos sites
    """
    try:
        from core.kv_manager import KVManager
        kv = KVManager()
        
        # Tentar carregar do KV primeiro
        logger.info("[NAMING] 🔍 Tentando carregar sites do KV...")
        kv_data = await kv.get_json("skills/eye/metadata/sites")
        logger.info(f"[NAMING] 📦 KV retornou: {type(kv_data)} - has_data: {'data' in kv_data if kv_data else False}")
        
        if kv_data and "data" in kv_data and "sites" in kv_data["data"]:
            sites = kv_data["data"]["sites"]
            logger.info(f"[NAMING] ✅ Carregados {len(sites)} sites do KV")
            return sites
        else:
            logger.warning(f"[NAMING] ⚠️  Estrutura KV inesperada: {kv_data.keys() if kv_data else 'None'}")
    except Exception as e:
        logger.error(f"[NAMING] ❌ Erro ao carregar sites do KV: {e}")
        import traceback
        traceback.print_exc()
    
    # ❌ SEM FALLBACK HARDCODED - Sistema deve falhar se KV não configurado
    # Força usuário a configurar via Gerenciador de Sites
    logger.error("[NAMING] ❌ KV não configurado! Configure sites via Gerenciador de Sites")
    logger.error("[NAMING] 📍 Acesse: /metadata-fields → Gerenciar Sites")
    return []  # Lista vazia - sistema vai falhar propositalmente


async def _load_naming_strategy() -> Dict[str, Any]:
    """
    Carrega naming strategy do MESMO JSON de sites: skills/eye/metadata/sites
    
    ✅ MUDANÇA (2025-11-12): Lê de data.naming_config do JSON unificado
       ao invés de criar outro KV separado (skills/eye/settings/naming-strategy)
    
    Fallback para .env se não existir
    
    Returns:
        Dict com naming_strategy e suffix_enabled
    """
    try:
        from core.kv_manager import KVManager
        kv = KVManager()
        
        # ✅ Ler do JSON unificado de sites (campo global data.naming_config)
        sites_data = await kv.get_json("skills/eye/metadata/sites")
        
        if sites_data and "data" in sites_data and "naming_config" in sites_data["data"]:
            naming_config = sites_data["data"]["naming_config"]
            logger.info("[NAMING] ✅ Naming strategy carregada do JSON unificado de sites")
            return {
                "naming_strategy": naming_config.get("strategy", "option2"),
                "suffix_enabled": naming_config.get("suffix_enabled", True),
            }
    except Exception as e:
        logger.warning(f"[NAMING] ⚠️  Erro ao carregar strategy do KV: {e}")
    
    # ❌ SEM FALLBACK HARDCODED - Retornar padrões mínimos
    # Naming config é menos crítico, pode usar padrões seguros
    logger.warning("[NAMING] ⚠️  Usando padrões: option2 + suffix_enabled=true")
    return {
        "naming_strategy": "option2",  # Padrão seguro
        "suffix_enabled": True,
    }


async def _update_cache():
    """
    Atualiza cache de sites e naming
    Deve ser chamado em background task ou periodicamente
    """
    global _sites_cache, _naming_cache, _cache_last_update, _cache_initialized
    
    current_time = time.time()
    
    # Verifica se cache expirou
    if _cache_initialized and (current_time - _cache_last_update < _cache_ttl):
        return  # Cache ainda válido
    
    logger.info("[NAMING] 🔄 Atualizando cache...")
    
    _sites_cache = await _load_sites_from_kv()
    _naming_cache = await _load_naming_strategy()
    _cache_last_update = current_time
    _cache_initialized = True
    
    logger.info(f"[NAMING] ✅ Cache atualizado: {len(_sites_cache)} sites, strategy={_naming_cache.get('naming_strategy')}")


def _ensure_cache_sync():
    """
    Garante que cache está carregado (versão síncrona para uso em funções síncronas)
    """
    global _cache_initialized
    
    if not _cache_initialized:
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # Se já existe loop rodando, cria uma nova tarefa
                asyncio.create_task(_update_cache())
            else:
                # Se não tem loop, executa diretamente
                loop.run_until_complete(_update_cache())
        except RuntimeError:
            # Se falhar, tenta criar novo loop
            try:
                new_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(new_loop)
                new_loop.run_until_complete(_update_cache())
                new_loop.close()
            except Exception as e:
                logger.error(f"[NAMING] ❌ Erro ao inicializar cache: {e}")


# ============================================================================
# FUNÇÕES PÚBLICAS DE CACHE
# ============================================================================

def get_sites_cache() -> List[Dict[str, Any]]:
    """
    Retorna cache de sites (síncrono para uso em funções síncronas)
    
    Returns:
        Lista de sites do cache
    """
    _ensure_cache_sync()
    return _sites_cache


def get_naming_cache() -> Dict[str, Any]:
    """
    Retorna cache de naming strategy
    
    Returns:
        Dict com naming_strategy e suffix_enabled
    """
    _ensure_cache_sync()
    return _naming_cache


def get_default_site() -> Optional[str]:
    """
    Retorna código do site padrão
    Busca no cache por is_default=True
    
    Returns:
        Código do site padrão (ex: "palmas") ou None
    """
    _ensure_cache_sync()
    
    for site in _sites_cache:
        if site.get("is_default", False):
            return site["code"]
    
    # ❌ SEM FALLBACK - Se não há site default configurado, retornar None
    # Sistema deve falhar e forçar configuração via Gerenciador de Sites
    logger.warning("[NAMING] ⚠️  Nenhum site com is_default=true configurado!")
    return None


def get_site_by_cluster(cluster: str) -> Optional[Dict[str, Any]]:
    """
    Busca site pelo cluster DINAMICAMENTE
    
    ANTES: if "rio" in cluster: return "rio"  # ❌ Hardcoded
    DEPOIS: Busca em _sites_cache por cluster matching
    
    Args:
        cluster: Nome do cluster (ex: "rmd-ldc-cliente")
    
    Returns:
        Dict com dados do site ou None
    """
    _ensure_cache_sync()
    
    cluster_lower = cluster.lower()
    
    # Busca exata primeiro
    for site in _sites_cache:
        if site.get("cluster", "").lower() == cluster_lower:
            return site
    
    # Busca parcial (cluster contém código do site OU vice-versa)
    for site in _sites_cache:
        site_code = site["code"].lower()
        cluster_pattern = site.get("cluster", "").lower()
        
        # Verifica se cluster contém o código do site OU o padrão de cluster
        if site_code in cluster_lower or cluster_pattern in cluster_lower:
            return site
    
    return None


def get_site_by_code(code: str) -> Optional[Dict[str, Any]]:
    """
    Busca site pelo código
    
    Args:
        code: Código do site (ex: "palmas", "rio", "dtc")
    
    Returns:
        Dict com dados do site ou None
    """
    _ensure_cache_sync()
    
    code_lower = code.lower()
    for site in _sites_cache:
        if site["code"].lower() == code_lower:
            return site
    
    return None


# ============================================================================
# FUNÇÕES PRINCIPAIS (REFATORADAS PARA USAR CACHE)
# ============================================================================

def apply_site_suffix(service_name: str, site: Optional[str] = None, cluster: Optional[str] = None) -> str:
    """
    Aplica sufixo de site ao service name baseado na estratégia configurada
    
    ✅ REFATORADO (2025-11-12): Usa cache dinâmico do KV

    OPÇÃO 2 (NAMING_STRATEGY=option2):
    - Services em sites diferentes do DEFAULT_SITE recebem sufixo _site
    - Exemplo: selfnode_exporter → selfnode_exporter_rio (se site="rio")
    - Palmas (DEFAULT_SITE) não recebe sufixo: selfnode_exporter

    OPÇÃO 1 (NAMING_STRATEGY=option1):
    - Nenhum sufixo é adicionado
    - Nomes iguais em todos os sites
    - Prometheus usa filtros (relabel_configs com drop) para evitar duplicidade

    Args:
        service_name: Nome base do serviço (ex: "selfnode_exporter", "blackbox_exporter")
        site: Site físico do serviço (ex: "palmas", "rio", "dtc", "genesis")
        cluster: Cluster Prometheus (alternativa ao site, ex: "rmd-ldc-cliente")

    Returns:
        Service name com sufixo aplicado se necessário

    Examples:
        # NAMING_STRATEGY=option2, DEFAULT_SITE=palmas
        >>> apply_site_suffix("selfnode_exporter", site="palmas")
        'selfnode_exporter'  # Sem sufixo (site padrão)

        >>> apply_site_suffix("selfnode_exporter", site="rio")
        'selfnode_exporter_rio'  # Com sufixo

        >>> apply_site_suffix("blackbox_exporter", site="dtc")
        'blackbox_exporter_dtc'  # Com sufixo

        # NAMING_STRATEGY=option1
        >>> apply_site_suffix("selfnode_exporter", site="rio")
        'selfnode_exporter'  # Sem sufixo (option1 usa nomes iguais)
    """
    # ✅ Usar cache ao invés de .env
    naming_config = get_naming_cache()
    naming_strategy = naming_config.get("naming_strategy", "option2")
    suffix_enabled = naming_config.get("suffix_enabled", True)
    default_site = get_default_site()

    # OPÇÃO 1: Não adiciona sufixo
    if naming_strategy == "option1":
        logger.debug(f"[NAMING] option1 ativo - mantendo nome original: {service_name}")
        return service_name

    # OPÇÃO 2: Adiciona sufixo se habilitado
    if naming_strategy == "option2" and suffix_enabled:
        # Determinar site efetivo (prioriza 'site' sobre 'cluster')
        effective_site = None

        if site:
            effective_site = site.lower()
        elif cluster:
            # ✅ DINÂMICO: Buscar site pelo cluster usando cache
            site_obj = get_site_by_cluster(cluster)
            if site_obj:
                effective_site = site_obj["code"]
                logger.debug(f"[NAMING] Site inferido do cluster '{cluster}': {effective_site}")

        # Se não conseguiu determinar site, não adiciona sufixo
        if not effective_site:
            logger.warning(f"[NAMING] Não foi possível determinar site para '{service_name}' - mantendo nome original")
            return service_name

        # ✅ Verificar se é site padrão DINAMICAMENTE
        if effective_site == default_site:
            logger.debug(f"[NAMING] Site padrão ({default_site}) - mantendo nome original: {service_name}")
            return service_name

        # Adicionar sufixo do site
        suffixed_name = f"{service_name}_{effective_site}"
        logger.info(f"[NAMING] Aplicando sufixo de site: {service_name} → {suffixed_name}")
        return suffixed_name

    # Fallback: retornar nome original
    logger.debug(f"[NAMING] Sufixo desabilitado ou configuração inválida - mantendo nome original: {service_name}")
    return service_name


def extract_site_from_metadata(metadata: dict) -> Optional[str]:
    """
    Extrai site dos metadata do serviço
    
    ✅ REFATORADO (2025-11-12): Usa cache dinâmico do KV

    Procura em ordem:
    1. metadata['site']
    2. metadata['cluster'] (busca dinâmica no cache)
    3. metadata['datacenter'] (busca dinâmica no cache)

    Args:
        metadata: Dicionário de metadata do Consul

    Returns:
        Site identificado ou None
    """
    if not metadata:
        return None

    # Primeira prioridade: campo 'site' explícito
    if 'site' in metadata and metadata['site']:
        return metadata['site'].lower()

    # Segunda prioridade: inferir do 'cluster' DINAMICAMENTE
    if 'cluster' in metadata and metadata['cluster']:
        site_obj = get_site_by_cluster(metadata['cluster'])
        if site_obj:
            return site_obj["code"]

    # Terceira prioridade: 'datacenter' DINAMICAMENTE
    if 'datacenter' in metadata and metadata['datacenter']:
        dc = metadata['datacenter'].lower()
        
        # Buscar site por datacenter no cache
        _ensure_cache_sync()
        for site in _sites_cache:
            site_dc = site.get("datacenter", "").lower()
            if site_dc == dc:
                return site["code"]

    return None


def get_naming_config() -> dict:
    """
    Retorna configuração atual de naming strategy
    
    ✅ REFATORADO (2025-11-12): Usa cache dinâmico do KV

    Returns:
        Dict com configurações atuais
    """
    naming_cache = get_naming_cache()
    default_site = get_default_site()
    
    return {
        "naming_strategy": naming_cache.get("naming_strategy", "option2"),
        "suffix_enabled": naming_cache.get("suffix_enabled", True),
        "default_site": default_site,
        "description": (
            "option1: Nomes iguais + filtros | "
            "option2: Nomes diferentes por site"
        )
    }
