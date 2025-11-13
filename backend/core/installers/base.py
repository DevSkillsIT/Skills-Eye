"""
Base class for all remote installers
Provides common functionality and interface
"""
import asyncio
from abc import ABC, abstractmethod
from typing import Tuple, Optional, Dict
from core.websocket_manager import ws_manager


class BaseInstaller(ABC):
    """Base class for remote installers"""

    def __init__(self, host: str, client_id: str = "default"):
        self.host = host
        self.client_id = client_id
        self.os_type: Optional[str] = None
        self.os_details: Dict[str, str] = {}
        self.installed_version: Optional[str] = None

    async def log(self, message: str, level: str = "info", data: dict = None):
        """Send log via WebSocket"""
        await ws_manager.send_log(message, level, self.client_id, data)

    async def progress(self, current: int, total: int, message: str = ""):
        """Send progress update"""
        await ws_manager.send_progress(current, total, message, self.client_id)

    @abstractmethod
    async def connect(self) -> bool:
        """Connect to remote host"""
        pass

    @abstractmethod
    async def disconnect(self):
        """Disconnect from remote host"""
        pass

    @abstractmethod
    async def validate_connection(self) -> Tuple[bool, str]:
        """Validate connection parameters before connecting"""
        pass

    @abstractmethod
    async def detect_os(self) -> Optional[str]:
        """Detect operating system"""
        pass

    @abstractmethod
    async def check_disk_space(self, required_mb: int = 200) -> bool:
        """Check available disk space"""
        pass

    @abstractmethod
    async def check_exporter_installed(self) -> bool:
        """Check if exporter is already installed"""
        pass

    @abstractmethod
    async def install_exporter(self, collector_profile: str = 'recommended') -> bool:
        """Install the exporter"""
        pass

    @abstractmethod
    async def validate_installation(
        self,
        basic_auth_user: Optional[str] = None,
        basic_auth_password: Optional[str] = None
    ) -> bool:
        """
        Validate that installation was successful

        Args:
            basic_auth_user: Optional Basic Auth username for validation
            basic_auth_password: Optional Basic Auth password for validation
        """
        pass

    async def get_system_info(self) -> Dict[str, str]:
        """Get system information (hostname, uptime, etc)"""
        return {
            "host": self.host,
            "os_type": self.os_type,
            "os_details": self.os_details
        }
