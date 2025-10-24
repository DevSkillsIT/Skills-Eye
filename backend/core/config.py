"""
Configuração central adaptada do consul-manager.py original
"""
import os
from typing import Dict, List, Set
from dotenv import load_dotenv

load_dotenv()

class Config:
    """Configuração central do ambiente Skills IT"""
    
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
    
    # Campos Meta
    META_FIELDS = [
        "module", "company", "project", "env", "name",
        "instance", "localizacao", "tipo", "cod_localidade",
        "cidade", "notas", "provedor", "fabricante",
        "modelo", "tipo_dispositivo_abrev", "glpi_url"
    ]
    
    REQUIRED_FIELDS = ["module", "company", "project", "env", "name", "instance"]