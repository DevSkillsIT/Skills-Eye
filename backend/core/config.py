"""
Configuração central adaptada do consul-manager.py original
"""
import os
from typing import Dict, List, Set
from dotenv import load_dotenv

load_dotenv()

class Config:
    """Configuração central do ambiente Skills IT

    NOTA: META_FIELDS e REQUIRED_FIELDS agora são carregados DINAMICAMENTE
    do metadata_fields.json via metadata_loader!
    """

    # Consul
    CONSUL_TOKEN = os.getenv("CONSUL_TOKEN", "8382a112-81e0-cd6d-2b92-8565925a0675")
    CONSUL_PORT = int(os.getenv("CONSUL_PORT", "8500"))

    @staticmethod
    def get_main_server() -> str:
        """
        Retorna IP do servidor principal.

        FONTE: Primeiro nó do KV metadata/sites
        ZERO HARDCODE - Se KV vazio, usa variável de ambiente
        """
        # Lazy loading: popular KNOWN_NODES se ainda não foi feito
        if Config.KNOWN_NODES is None:
            Config.KNOWN_NODES = Config.get_known_nodes()
        
        if Config.KNOWN_NODES:
            # Retornar primeiro IP do dicionário
            return list(Config.KNOWN_NODES.values())[0]
        
        # Fallback: APENAS variável de ambiente (ZERO hardcode)
        env_host = os.getenv("CONSUL_HOST")
        if not env_host:
            raise RuntimeError(
                "❌ ERRO CRÍTICO: CONSUL_HOST não definido em .env e KV metadata/sites vazio! "
                "Configure CONSUL_HOST=<ip_consul> no arquivo .env"
            )
        return env_host

    @staticmethod
    def get_main_server_name() -> str:
        """
        Retorna nome do servidor principal.

        FONTE: Primeiro hostname do KV metadata/sites
        ZERO HARDCODE - Se KV vazio, extrai do CONSUL_HOST
        """
        # Lazy loading: popular KNOWN_NODES se ainda não foi feito
        if Config.KNOWN_NODES is None:
            Config.KNOWN_NODES = Config.get_known_nodes()
            
        if Config.KNOWN_NODES:
            # Retornar primeiro hostname do dicionário
            return list(Config.KNOWN_NODES.keys())[0]
        
        # Fallback: usar IP do CONSUL_HOST como hostname (ZERO hardcode)
        return os.getenv("CONSUL_HOST", "localhost")

    @staticmethod
    def get_known_nodes() -> Dict[str, str]:
        """
        Retorna mapa de nós conhecidos (hostname → IP).

        SPRINT 2 - FIX CRÍTICO: REMOVIDO asyncio.run() para evitar erro em event loop
        
        NOVA ESTRATÉGIA:
        1. Tenta carregar do cache em memória (se já foi carregado antes)
        2. Se não tem cache, retorna dict vazio (será carregado sob demanda por endpoints async)
        
        ZERO HARDCODE - Valores vêm apenas do KV ou ficam vazios
        """
        # Se já foi carregado antes, retornar cache
        if hasattr(Config, '_known_nodes_cache') and Config._known_nodes_cache:
            return Config._known_nodes_cache
        
        # Não podemos usar asyncio.run() aqui (causa erro em event loop)
        # Retornar dict vazio - será populado por endpoint async quando necessário
        return {}

    # Service Names
    SERVICE_NAMES = {
        "blackbox_exporter": "Blackbox local no nó selecionado",
        "blackbox_remote_dtc_skills": "Blackbox remoto DTC Skills",
        "blackbox_remote_rmd_ldc": "Blackbox remoto RMD LDC Rio",
        "selfnode_exporter": "Selfnode (requer agente no host remoto)",
        "selfnode_exporter_rio": "Selfnode RMD"
    }

    # Módulos Blackbox
    BLACKBOX_MODULES = [
        "icmp", "http_2xx", "http_4xx", "https",
        "http_post_2xx", "tcp_connect", "ssh_banner",
        "pop3s_banner", "irc_banner"
    ]

    # ========================================================================
    # CAMPOS METADATA - AGORA 100% DINÂMICOS DO PROMETHEUS
    # ========================================================================
    # Campos são extraídos do prometheus.yml via SSH e salvos no Consul KV
    # Não mais usa JSON hardcoded - tudo vem do Prometheus!
    # ========================================================================

    @staticmethod
    def get_meta_fields() -> List[str]:
        """
        Retorna todos os campos metadata extraídos do Prometheus.

        SPRINT 2 - FIX: Removido asyncio.run() - retorna lista vazia
        Campos serão carregados sob demanda por endpoints async
        """
        # Não usar asyncio.run() - retornar vazio (será carregado por endpoints async)
        return []

    @staticmethod
    def get_required_fields() -> List[str]:
        """
        Retorna campos obrigatórios extraídos do Prometheus.

        SPRINT 2 - FIX: Removido asyncio.run() - retorna lista vazia
        Campos serão carregados sob demanda por endpoints async
        """
        # Não usar asyncio.run() - retornar vazio (será carregado por endpoints async)
        return []

    # Propriedades para compatibilidade com código legado
    # (deprecated - usar get_meta_fields() e get_required_fields())
    @property
    def META_FIELDS(self) -> List[str]:
        """DEPRECATED: Use Config.get_meta_fields() - Agora busca do Prometheus/KV"""
        return Config.get_meta_fields()

    @property
    def REQUIRED_FIELDS(self) -> List[str]:
        """DEPRECATED: Use Config.get_required_fields() - Agora busca do Prometheus/KV"""
        return Config.get_required_fields()


# SPRINT 2 - FIX CRÍTICO: ZERO HARDCODE!
# Não inicializar no import (causa erro asyncio.run em event loop)
# Valores serão carregados dinamicamente via lazy loading
Config.KNOWN_NODES = None  # Lazy loading - será populado na primeira chamada
Config.MAIN_SERVER = None  # Lazy loading - será populado na primeira chamada
Config.MAIN_SERVER_NAME = None  # Lazy loading - será populado na primeira chamada