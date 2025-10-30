"""
Utilitários Compartilhados para Detecção de Servidores

Funções reutilizáveis para:
- Detectar capacidades de servidores (Prometheus, Blackbox, Alertmanager)
- Encontrar arquivos de configuração em múltiplos caminhos
- Validar e categorizar servidores
- Fornecer informações padronizadas sobre servidores

Usado por:
- metadata_fields_manager.py
- prometheus_config.py
- Qualquer API que precise interagir com servidores remotos
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import logging

from core.multi_config_manager import MultiConfigManager

logger = logging.getLogger(__name__)


class ServerCapability(str, Enum):
    """Capacidades que um servidor pode ter"""
    PROMETHEUS = "prometheus"
    ALERTMANAGER = "alertmanager"
    BLACKBOX_EXPORTER = "blackbox_exporter"
    NODE_EXPORTER = "node_exporter"
    WINDOWS_EXPORTER = "windows_exporter"


class ServerRole(str, Enum):
    """Papel do servidor no cluster"""
    MASTER = "master"
    SLAVE = "slave"
    STANDALONE = "standalone"
    UNKNOWN = "unknown"


@dataclass
class ServerInfo:
    """Informações completas sobre um servidor"""
    hostname: str
    port: int
    capabilities: List[ServerCapability]
    role: ServerRole
    prometheus_config_path: Optional[str] = None
    alertmanager_config_path: Optional[str] = None
    blackbox_config_path: Optional[str] = None
    has_prometheus: bool = False
    has_alertmanager: bool = False
    has_blackbox_exporter: bool = False
    error: Optional[str] = None

    @property
    def is_monitoring_server(self) -> bool:
        """Servidor tem Prometheus ou Alertmanager"""
        return self.has_prometheus or self.has_alertmanager

    @property
    def is_exporter_only(self) -> bool:
        """Servidor só tem exporters, sem Prometheus/Alertmanager"""
        return (
            self.has_blackbox_exporter and
            not self.has_prometheus and
            not self.has_alertmanager
        )

    @property
    def description(self) -> str:
        """Descrição legível das capacidades"""
        if self.error:
            return f"Erro: {self.error}"

        if not self.capabilities:
            return "Servidor sem serviços detectados"

        parts = []
        if self.has_prometheus:
            parts.append("Prometheus")
        if self.has_alertmanager:
            parts.append("Alertmanager")
        if self.has_blackbox_exporter:
            parts.append("Blackbox Exporter")

        return " + ".join(parts) if parts else "Servidor básico"


class ServerDetector:
    """
    Classe para detectar capacidades de servidores

    Métodos principais:
    - detect_server_capabilities(): Retorna ServerInfo completo
    - find_config_file(): Procura arquivo em múltiplos caminhos
    - check_file_exists(): Verifica se arquivo existe via SSH
    """

    # Caminhos possíveis para cada tipo de configuração
    PROMETHEUS_PATHS = [
        "/etc/prometheus/prometheus.yml",
        "/opt/prometheus/prometheus.yml",
        "/usr/local/etc/prometheus/prometheus.yml",
        "/home/prometheus/prometheus.yml",
    ]

    ALERTMANAGER_PATHS = [
        "/etc/alertmanager/alertmanager.yml",
        "/opt/alertmanager/alertmanager.yml",
        "/usr/local/etc/alertmanager/alertmanager.yml",
    ]

    BLACKBOX_PATHS = [
        "/etc/blackbox_exporter/blackbox.yml",
        "/opt/blackbox_exporter/blackbox.yml",
        "/usr/local/etc/blackbox_exporter/blackbox.yml",
    ]

    def __init__(self):
        """Inicializa o detector"""
        self.multi_config = MultiConfigManager()
        self._capabilities_cache: Dict[str, ServerInfo] = {}

    def detect_server_capabilities(
        self,
        hostname: str,
        use_cache: bool = True
    ) -> ServerInfo:
        """
        Detecta todas as capacidades de um servidor

        Args:
            hostname: Hostname ou IP do servidor
            use_cache: Se True, usa cache de detecções anteriores

        Returns:
            ServerInfo com todas as capacidades detectadas
        """
        # Verificar cache
        if use_cache and hostname in self._capabilities_cache:
            logger.info(f"[SERVER-DETECT] Usando cache para {hostname}")
            return self._capabilities_cache[hostname]

        logger.info(f"[SERVER-DETECT] Detectando capacidades de {hostname}")

        # Extrair porta se fornecida (formato hostname:port)
        if ':' in hostname:
            host_only, port_str = hostname.split(':', 1)
            port = int(port_str)
        else:
            host_only = hostname
            port = 22

        # Inicializar ServerInfo
        server_info = ServerInfo(
            hostname=host_only,
            port=port,
            capabilities=[],
            role=ServerRole.UNKNOWN
        )

        try:
            # 1. Verificar Prometheus
            prometheus_path = self.find_config_file(
                self.PROMETHEUS_PATHS,
                hostname=host_only
            )
            if prometheus_path:
                logger.info(f"[SERVER-DETECT] Prometheus encontrado: {prometheus_path}")
                server_info.has_prometheus = True
                server_info.prometheus_config_path = prometheus_path
                server_info.capabilities.append(ServerCapability.PROMETHEUS)
            else:
                logger.info(f"[SERVER-DETECT] Prometheus não encontrado em {host_only}")

            # 2. Verificar Alertmanager
            alertmanager_path = self.find_config_file(
                self.ALERTMANAGER_PATHS,
                hostname=host_only
            )
            if alertmanager_path:
                logger.info(f"[SERVER-DETECT] Alertmanager encontrado: {alertmanager_path}")
                server_info.has_alertmanager = True
                server_info.alertmanager_config_path = alertmanager_path
                server_info.capabilities.append(ServerCapability.ALERTMANAGER)

            # 3. Verificar Blackbox Exporter
            blackbox_path = self.find_config_file(
                self.BLACKBOX_PATHS,
                hostname=host_only
            )
            if blackbox_path:
                logger.info(f"[SERVER-DETECT] Blackbox Exporter encontrado: {blackbox_path}")
                server_info.has_blackbox_exporter = True
                server_info.blackbox_config_path = blackbox_path
                server_info.capabilities.append(ServerCapability.BLACKBOX_EXPORTER)

            # 4. Determinar role
            # TODO: Implementar lógica de master/slave baseada em configuração
            if server_info.has_prometheus:
                server_info.role = ServerRole.MASTER  # Simplificado por enquanto
            elif server_info.is_exporter_only:
                server_info.role = ServerRole.STANDALONE

            logger.info(
                f"[SERVER-DETECT] {hostname} - Capabilities: "
                f"{[c.value for c in server_info.capabilities]}, "
                f"Role: {server_info.role.value}"
            )

        except Exception as e:
            logger.error(f"[SERVER-DETECT] Erro ao detectar {hostname}: {e}", exc_info=True)
            server_info.error = str(e)

        # Armazenar em cache
        self._capabilities_cache[hostname] = server_info

        return server_info

    def find_config_file(
        self,
        possible_paths: List[str],
        hostname: str
    ) -> Optional[str]:
        """
        Procura um arquivo de configuração em múltiplos caminhos

        Args:
            possible_paths: Lista de caminhos possíveis
            hostname: Hostname do servidor

        Returns:
            Path do arquivo encontrado ou None
        """
        for path in possible_paths:
            if self.check_file_exists(path, hostname):
                return path

        return None

    def check_file_exists(self, file_path: str, hostname: str) -> bool:
        """
        Verifica se um arquivo existe no servidor remoto

        Args:
            file_path: Path do arquivo
            hostname: Hostname do servidor

        Returns:
            True se arquivo existe, False caso contrário
        """
        try:
            # Tentar ler o arquivo - se não existir, lançará FileNotFoundError
            content = self.multi_config.get_file_content_raw(file_path, hostname=hostname)
            return bool(content)
        except FileNotFoundError:
            return False
        except Exception as e:
            logger.debug(f"[SERVER-DETECT] Erro ao verificar {file_path} em {hostname}: {e}")
            return False

    def clear_cache(self, hostname: Optional[str] = None):
        """
        Limpa cache de detecções

        Args:
            hostname: Se fornecido, limpa apenas este host. Se None, limpa tudo.
        """
        if hostname:
            if hostname in self._capabilities_cache:
                del self._capabilities_cache[hostname]
                logger.info(f"[SERVER-DETECT] Cache limpo para {hostname}")
        else:
            self._capabilities_cache.clear()
            logger.info("[SERVER-DETECT] Cache completamente limpo")

    def get_monitoring_servers(self) -> List[ServerInfo]:
        """
        Retorna lista de servidores com Prometheus ou Alertmanager

        Returns:
            Lista de ServerInfo com is_monitoring_server=True
        """
        return [
            info for info in self._capabilities_cache.values()
            if info.is_monitoring_server
        ]

    def get_exporter_only_servers(self) -> List[ServerInfo]:
        """
        Retorna lista de servidores apenas com exporters

        Returns:
            Lista de ServerInfo com is_exporter_only=True
        """
        return [
            info for info in self._capabilities_cache.values()
            if info.is_exporter_only
        ]


# Instância singleton para reutilização
_detector_instance: Optional[ServerDetector] = None


def get_server_detector() -> ServerDetector:
    """
    Retorna instância singleton do ServerDetector

    Returns:
        ServerDetector global
    """
    global _detector_instance
    if _detector_instance is None:
        _detector_instance = ServerDetector()
    return _detector_instance
