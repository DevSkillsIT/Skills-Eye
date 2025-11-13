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
        ZERO HARDCODE - Se KV vazio, usa variável de ambiente ou localhost
        """
        nodes = Config.get_known_nodes()
        if nodes:
            # Retornar primeiro IP do dicionário
            return list(nodes.values())[0]
        # Fallback: variável de ambiente ou localhost (ZERO IPs hardcoded)
        return os.getenv("CONSUL_HOST", "localhost")

    @staticmethod
    def get_main_server_name() -> str:
        """
        Retorna nome do servidor principal.

        FONTE: Primeiro hostname do KV metadata/sites
        ZERO HARDCODE - Se KV vazio, retorna "localhost"
        """
        nodes = Config.get_known_nodes()
        if nodes:
            # Retornar primeiro hostname do dicionário
            return list(nodes.keys())[0]
        return "localhost"

    @staticmethod
    def get_known_nodes() -> Dict[str, str]:
        """
        Retorna mapa de nós conhecidos (hostname → IP).

        FONTE: Consul KV (skills/eye/metadata/sites)
        ZERO HARDCODE - Se KV vazio/falhar, retorna dict vazio
        """
        try:
            from core.kv_manager import KVManager
            kv = KVManager()

            import asyncio
            sites_data = asyncio.run(kv.get_json('skills/eye/metadata/sites'))

            if sites_data:
                # Converter lista de sites para dict {hostname: prometheus_instance}
                nodes = {}
                for site in sites_data:
                    # Usar hostname se disponível, senão usar name
                    hostname = site.get('hostname') or site.get('name', 'unknown')
                    ip = site.get('prometheus_instance')
                    if ip:
                        nodes[hostname] = ip
                return nodes

            # KV vazio: retornar dict vazio (ZERO HARDCODE)
            return {}
        except Exception:
            # Falha ao acessar KV: retornar dict vazio (ZERO HARDCODE)
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

        NOTA: Agora busca do Consul KV (skills/eye/metadata/fields)
        Os campos são extraídos dinamicamente do prometheus.yml via SSH
        """
        try:
            from core.kv_manager import KVManager
            kv = KVManager()

            # Buscar do KV (dados extraídos do Prometheus)
            import asyncio
            fields_data = asyncio.run(kv.get_json('skills/eye/metadata/fields'))

            if fields_data and 'fields' in fields_data:
                return [field['name'] for field in fields_data['fields']]

            # Fallback: retornar lista vazia se KV não disponível
            return []
        except Exception:
            # Se falhar, retornar lista vazia (campos serão carregados sob demanda)
            return []

    @staticmethod
    def get_required_fields() -> List[str]:
        """
        Retorna campos obrigatórios extraídos do Prometheus.

        NOTA: Campos obrigatórios agora são definidos pelo flag 'required' no KV
        """
        try:
            from core.kv_manager import KVManager
            kv = KVManager()

            import asyncio
            fields_data = asyncio.run(kv.get_json('skills/eye/metadata/fields'))

            if fields_data and 'fields' in fields_data:
                return [
                    field['name']
                    for field in fields_data['fields']
                    if field.get('required', False)
                ]

            return []
        except Exception:
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


# Inicializar ao carregar módulo (compatibilidade legado)
Config.KNOWN_NODES = Config.get_known_nodes()
Config.MAIN_SERVER = Config.get_main_server()
Config.MAIN_SERVER_NAME = Config.get_main_server_name()