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

    # Servidor Principal
    MAIN_SERVER = os.getenv("CONSUL_HOST", "172.16.1.26")
    MAIN_SERVER_NAME = "glpi-grafana-prometheus.skillsit.com.br"

    # Consul
    CONSUL_TOKEN = os.getenv("CONSUL_TOKEN", "8382a112-81e0-cd6d-2b92-8565925a0675")
    CONSUL_PORT = int(os.getenv("CONSUL_PORT", "8500"))

    # Nós conhecidos
    KNOWN_NODES = {
        "glpi-grafana-prometheus.skillsit.com.br": "172.16.1.26",
        "consul-DTC-Genesis-Skills": "11.144.0.21",
        "consul-RMD-LDC-Rio": "172.16.200.14"
    }

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