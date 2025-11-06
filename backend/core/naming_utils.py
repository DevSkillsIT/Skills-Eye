"""
Naming Utils - Utilitários para nomenclatura multi-site

Gerencia sufixos automáticos em service names baseado na estratégia de naming
configurada no .env

Estratégias:
- option1: Nomes iguais em todos os sites (requer filtros no Prometheus)
- option2: Nomes diferentes por site (sufixos automáticos)
"""

import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def apply_site_suffix(service_name: str, site: Optional[str] = None, cluster: Optional[str] = None) -> str:
    """
    Aplica sufixo de site ao service name baseado na estratégia configurada

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
        cluster: Cluster Prometheus (alternativa ao site, ex: "rio-rmd-ldc")

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
    # Ler configurações do .env
    naming_strategy = os.getenv("NAMING_STRATEGY", "option1")
    suffix_enabled = os.getenv("SITE_SUFFIX_ENABLED", "false").lower() == "true"
    default_site = os.getenv("DEFAULT_SITE", "palmas").lower()

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
            # Extrair site do cluster se possível (ex: "rio-rmd-ldc" → "rio")
            cluster_lower = cluster.lower()
            if "rio" in cluster_lower:
                effective_site = "rio"
            elif "dtc" in cluster_lower or "genesis" in cluster_lower:
                effective_site = "dtc"
            elif "palmas" in cluster_lower:
                effective_site = "palmas"

        # Se não conseguiu determinar site, não adiciona sufixo
        if not effective_site:
            logger.warning(f"[NAMING] Não foi possível determinar site para '{service_name}' - mantendo nome original")
            return service_name

        # Se é o site padrão, não adiciona sufixo
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

    Procura em ordem:
    1. metadata['site']
    2. metadata['cluster'] (tenta inferir)
    3. metadata['datacenter']

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

    # Segunda prioridade: inferir do 'cluster'
    if 'cluster' in metadata and metadata['cluster']:
        cluster = metadata['cluster'].lower()
        if 'rio' in cluster:
            return 'rio'
        elif 'dtc' in cluster or 'genesis' in cluster:
            return 'dtc'
        elif 'palmas' in cluster:
            return 'palmas'

    # Terceira prioridade: 'datacenter'
    if 'datacenter' in metadata and metadata['datacenter']:
        dc = metadata['datacenter'].lower()
        if dc in ['rio', 'palmas', 'dtc', 'genesis', 'genesis-dtc']:
            return dc.replace('genesis-dtc', 'dtc')

    return None


def get_naming_config() -> dict:
    """
    Retorna configuração atual de naming strategy

    Returns:
        Dict com configurações atuais
    """
    return {
        "naming_strategy": os.getenv("NAMING_STRATEGY", "option1"),
        "suffix_enabled": os.getenv("SITE_SUFFIX_ENABLED", "false").lower() == "true",
        "default_site": os.getenv("DEFAULT_SITE", "palmas").lower(),
        "description": (
            "option1: Nomes iguais + filtros | "
            "option2: Nomes diferentes por site"
        )
    }
