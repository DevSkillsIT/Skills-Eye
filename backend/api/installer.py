"""
API endpoints para instalação remota de Exporters
Suporta múltiplos métodos de instalação para Windows e Linux
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Literal, Union
from enum import Enum
import asyncio
import uuid
from core.installers import (
    LinuxSSHInstaller,
    WindowsPSExecInstaller,
    WindowsWinRMInstaller,
    WindowsSSHInstaller
)
from core.consul_manager import ConsulManager
from core.config import Config
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

# Storage for installation tasks
installation_tasks: Dict[str, dict] = {}


# ============================================================================
# PYDANTIC MODELS
# ============================================================================

class LinuxSSHInstallRequest(BaseModel):
    """Request for Linux installation via SSH"""
    os_type: Literal["linux"] = Field("linux", description="Sistema operacional")
    method: Literal["ssh"] = Field("ssh", description="Método de instalação")
    host: str = Field(..., description="Endereço IP ou hostname")
    username: str = Field(..., description="Usuário SSH")
    password: Optional[str] = Field(None, description="Senha SSH")
    key_file: Optional[str] = Field(None, description="Caminho para chave SSH")
    ssh_port: int = Field(22, description="Porta SSH")
    use_sudo: bool = Field(True, description="Usar sudo")
    collector_profile: str = Field("recommended", description="Perfil de collectors")
    register_in_consul: bool = Field(True, description="Registrar no Consul")
    consul_node: Optional[str] = Field(None, description="Nó Consul (Palmas/Rio)")


class WindowsSSHInstallRequest(BaseModel):
    """Request for Windows installation via SSH (OpenSSH)"""
    os_type: Literal["windows"] = Field("windows", description="Sistema operacional")
    method: Literal["ssh"] = Field("ssh", description="Método de instalação")
    host: str = Field(..., description="Endereço IP ou hostname")
    username: str = Field(..., description="Usuário (sem domínio)")
    password: Optional[str] = Field(None, description="Senha")
    key_file: Optional[str] = Field(None, description="Caminho para chave SSH")
    domain: Optional[str] = Field(None, description="Domínio (para contas de domínio)")
    ssh_port: int = Field(22, description="Porta SSH")
    collector_profile: str = Field("recommended", description="Perfil de collectors")
    register_in_consul: bool = Field(True, description="Registrar no Consul")
    consul_node: Optional[str] = Field(None, description="Nó Consul")


class WindowsWinRMInstallRequest(BaseModel):
    """Request for Windows installation via WinRM/PowerShell"""
    os_type: Literal["windows"] = Field("windows", description="Sistema operacional")
    method: Literal["winrm"] = Field("winrm", description="Método de instalação")
    host: str = Field(..., description="Endereço IP ou hostname")
    username: str = Field(..., description="Usuário (sem domínio)")
    password: str = Field(..., description="Senha (obrigatória para WinRM)")
    domain: Optional[str] = Field(None, description="Domínio (ex: DOMAIN ou None para conta local)")
    use_ssl: bool = Field(False, description="Usar HTTPS (porta 5986)")
    port: Optional[int] = Field(None, description="Porta customizada (padrão: 5985 HTTP, 5986 HTTPS)")
    collector_profile: str = Field("recommended", description="Perfil de collectors")
    register_in_consul: bool = Field(True, description="Registrar no Consul")
    consul_node: Optional[str] = Field(None, description="Nó Consul")


class WindowsPSExecInstallRequest(BaseModel):
    """Request for Windows installation via PSExec"""
    os_type: Literal["windows"] = Field("windows", description="Sistema operacional")
    method: Literal["psexec"] = Field("psexec", description="Método de instalação")
    host: str = Field(..., description="Endereço IP ou hostname")
    username: str = Field(..., description="Usuário (sem domínio)")
    password: str = Field(..., description="Senha (obrigatória para PSExec)")
    domain: Optional[str] = Field(None, description="Domínio (ex: DOMAIN ou None para conta local)")
    psexec_path: str = Field("psexec.exe", description="Caminho para PSExec")
    collector_profile: str = Field("recommended", description="Perfil de collectors")
    register_in_consul: bool = Field(True, description="Registrar no Consul")
    consul_node: Optional[str] = Field(None, description="Nó Consul")


class InstallResponse(BaseModel):
    """Response quando instalação é iniciada"""
    success: bool
    message: str
    installation_id: str
    websocket_url: str
    details: Dict


class InstallStatusResponse(BaseModel):
    """Status de uma instalação"""
    installation_id: str
    status: str
    progress: int
    message: str
    details: Optional[Dict] = None


# ============================================================================
# API ENDPOINTS
# ============================================================================

@router.post("/install", response_model=InstallResponse)
async def install_exporter(
    request: Dict,
    background_tasks: BackgroundTasks
):
    """
    Inicia instalação remota de exporter

    Suporta múltiplos métodos:
    - Linux via SSH
    - Windows via SSH (OpenSSH)
    - Windows via WinRM/PowerShell
    - Windows via PSExec

    WebSocket URL: ws://localhost:5000/ws/installer/{installation_id}
    """
    try:
        # Parse OS type and method
        os_type = request.get("os_type", "").lower()
        method = request.get("method", "").lower()

        # Validate OS and method combination
        if os_type == "linux" and method != "ssh":
            raise HTTPException(
                status_code=400,
                detail="Linux só suporta método SSH"
            )

        if os_type == "windows" and method not in ["ssh", "winrm", "psexec"]:
            raise HTTPException(
                status_code=400,
                detail="Windows suporta métodos: ssh, winrm, psexec"
            )

        # Validate request based on method
        if os_type == "linux":
            validated_request = LinuxSSHInstallRequest(**request)
        elif method == "ssh":
            validated_request = WindowsSSHInstallRequest(**request)
        elif method == "winrm":
            validated_request = WindowsWinRMInstallRequest(**request)
        elif method == "psexec":
            validated_request = WindowsPSExecInstallRequest(**request)
        else:
            raise HTTPException(status_code=400, detail="Combinação inválida de OS e método")

        # Generate installation ID
        installation_id = str(uuid.uuid4())

        # Store initial status
        installation_tasks[installation_id] = {
            "status": "pending",
            "progress": 0,
            "message": "Instalação na fila",
            "host": validated_request.host,
            "os_type": os_type,
            "method": method,
            "started_at": None,
            "completed_at": None
        }

        # Start installation in background
        background_tasks.add_task(
            run_installation,
            installation_id,
            validated_request
        )

        logger.info(f"Instalação iniciada: {installation_id} - {os_type}/{method} em {validated_request.host}")

        return InstallResponse(
            success=True,
            message=f"Instalação iniciada para {validated_request.host}",
            installation_id=installation_id,
            websocket_url=f"/ws/installer/{installation_id}",
            details={
                "host": validated_request.host,
                "os_type": os_type,
                "method": method,
                "collector_profile": validated_request.collector_profile
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao iniciar instalação: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/install/{installation_id}/status", response_model=InstallStatusResponse)
async def get_install_status(installation_id: str):
    """Obtém status de uma instalação"""
    if installation_id not in installation_tasks:
        raise HTTPException(status_code=404, detail="Instalação não encontrada")

    task_info = installation_tasks[installation_id]

    return InstallStatusResponse(
        installation_id=installation_id,
        status=task_info["status"],
        progress=task_info["progress"],
        message=task_info["message"],
        details={
            "host": task_info["host"],
            "os_type": task_info["os_type"],
            "method": task_info["method"],
            "started_at": task_info["started_at"],
            "completed_at": task_info["completed_at"]
        }
    )


@router.get("/install/active")
async def get_active_installations():
    """Lista instalações ativas ou recentes"""
    return {
        "success": True,
        "installations": [
            {
                "installation_id": inst_id,
                "host": info["host"],
                "os_type": info["os_type"],
                "method": info["method"],
                "status": info["status"],
                "progress": info["progress"],
                "message": info["message"]
            }
            for inst_id, info in installation_tasks.items()
        ],
        "total": len(installation_tasks)
    }


@router.delete("/install/{installation_id}")
async def cancel_installation(installation_id: str):
    """Cancela instalação em andamento"""
    if installation_id not in installation_tasks:
        raise HTTPException(status_code=404, detail="Instalação não encontrada")

    task_info = installation_tasks[installation_id]

    if task_info["status"] in ["completed", "failed"]:
        raise HTTPException(
            status_code=400,
            detail=f"Instalação já {task_info['status']}"
        )

    task_info["status"] = "cancelled"
    task_info["message"] = "Instalação cancelada"

    return {
        "success": True,
        "message": "Instalação marcada para cancelamento",
        "installation_id": installation_id
    }


@router.get("/collectors/profiles")
async def get_collector_profiles():
    """Retorna perfis de collectors disponíveis"""
    from core.installers.linux_ssh import NODE_EXPORTER_COLLECTORS, NODE_EXPORTER_COLLECTOR_DETAILS
    from core.installers.windows_winrm import WINDOWS_EXPORTER_COLLECTORS, WINDOWS_EXPORTER_COLLECTOR_DETAILS

    return {
        "success": True,
        "linux": {
            profile_name: {
                "enabled": [
                    {"name": col, "description": NODE_EXPORTER_COLLECTOR_DETAILS.get(col, "N/A")}
                    for col in config.get('enable', [])
                ],
                "disabled": config.get('disable', [])
            }
            for profile_name, config in NODE_EXPORTER_COLLECTORS.items()
        },
        "windows": {
            profile_name: [
                {"name": col, "description": WINDOWS_EXPORTER_COLLECTOR_DETAILS.get(col, "N/A")}
                for col in collectors
            ]
            for profile_name, collectors in WINDOWS_EXPORTER_COLLECTORS.items()
        }
    }


@router.post("/test-connection")
async def test_connection(request: Dict):
    """
    Testa conexão sem instalar

    Detecta SO e retorna informações do sistema
    """
    try:
        os_type = request.get("os_type", "").lower()
        method = request.get("method", "").lower()

        # Create appropriate installer
        test_id = "test-" + str(uuid.uuid4())[:8]

        if os_type == "linux":
            installer = LinuxSSHInstaller(
                host=request["host"],
                username=request["username"],
                password=request.get("password"),
                key_file=request.get("key_file"),
                ssh_port=request.get("ssh_port", 22),
                use_sudo=request.get("use_sudo", True),
                client_id=test_id
            )
        elif os_type == "windows" and method == "ssh":
            installer = WindowsSSHInstaller(
                host=request["host"],
                username=request["username"],
                password=request.get("password"),
                key_file=request.get("key_file"),
                domain=request.get("domain"),
                ssh_port=request.get("ssh_port", 22),
                client_id=test_id
            )
        elif os_type == "windows" and method == "winrm":
            installer = WindowsWinRMInstaller(
                host=request["host"],
                username=request["username"],
                password=request["password"],
                domain=request.get("domain"),
                use_ssl=request.get("use_ssl", False),
                port=request.get("port"),
                client_id=test_id
            )
        elif os_type == "windows" and method == "psexec":
            installer = WindowsPSExecInstaller(
                host=request["host"],
                username=request["username"],
                password=request["password"],
                domain=request.get("domain"),
                psexec_path=request.get("psexec_path", "psexec.exe"),
                client_id=test_id
            )
        else:
            raise HTTPException(status_code=400, detail="Combinação inválida de OS e método")

        # Test connection
        if not await installer.connect():
            raise HTTPException(
                status_code=503,
                detail="Falha ao conectar. Verifique credenciais e conectividade."
            )

        # Detect OS
        detected_os = await installer.detect_os()
        if not detected_os:
            await installer.disconnect()
            raise HTTPException(status_code=400, detail="SO não suportado")

        # Get system info
        system_info = await installer.get_system_info()

        await installer.disconnect()

        return {
            "success": True,
            "message": "Conexão bem-sucedida",
            "details": {
                **system_info,
                "method": method
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao testar conexão: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/methods")
async def get_installation_methods():
    """Retorna métodos de instalação disponíveis por SO"""
    return {
        "success": True,
        "methods": {
            "linux": [
                {
                    "method": "ssh",
                    "name": "SSH",
                    "description": "Instalação via SSH usando paramiko",
                    "requires": ["username", "password ou key_file"],
                    "supported": True
                }
            ],
            "windows": [
                {
                    "method": "ssh",
                    "name": "SSH (OpenSSH)",
                    "description": "Instalação via SSH (requer OpenSSH instalado no Windows)",
                    "requires": ["username", "password ou key_file", "domain (opcional)"],
                    "supported": True
                },
                {
                    "method": "winrm",
                    "name": "WinRM/PowerShell",
                    "description": "Instalação via Windows Remote Management (PowerShell Remoting)",
                    "requires": ["username", "password", "domain (opcional)"],
                    "ports": ["5985 (HTTP)", "5986 (HTTPS)"],
                    "supported": True
                },
                {
                    "method": "psexec",
                    "name": "PSExec",
                    "description": "Instalação via PSExec (requer PSExec.exe disponível)",
                    "requires": ["username", "password", "domain (opcional)", "psexec_path"],
                    "ports": ["445 (SMB)"],
                    "supported": True,
                    "notes": "Requer PSExec da Sysinternals instalado no servidor da API"
                }
            ]
        }
    }


# ============================================================================
# BACKGROUND TASK
# ============================================================================

async def run_installation(installation_id: str, request):
    """Execute installation in background"""
    from datetime import datetime

    task_info = installation_tasks[installation_id]
    task_info["status"] = "running"
    task_info["started_at"] = datetime.now().isoformat()

    installer = None

    try:
        # Create appropriate installer
        if isinstance(request, LinuxSSHInstallRequest):
            installer = LinuxSSHInstaller(
                host=request.host,
                username=request.username,
                password=request.password,
                key_file=request.key_file,
                ssh_port=request.ssh_port,
                use_sudo=request.use_sudo,
                client_id=installation_id
            )
        elif isinstance(request, WindowsSSHInstallRequest):
            installer = WindowsSSHInstaller(
                host=request.host,
                username=request.username,
                password=request.password,
                key_file=request.key_file,
                domain=request.domain,
                ssh_port=request.ssh_port,
                client_id=installation_id
            )
        elif isinstance(request, WindowsWinRMInstallRequest):
            installer = WindowsWinRMInstaller(
                host=request.host,
                username=request.username,
                password=request.password,
                domain=request.domain,
                use_ssl=request.use_ssl,
                port=request.port,
                client_id=installation_id
            )
        elif isinstance(request, WindowsPSExecInstallRequest):
            installer = WindowsPSExecInstaller(
                host=request.host,
                username=request.username,
                password=request.password,
                domain=request.domain,
                psexec_path=request.psexec_path,
                client_id=installation_id
            )

        task_info["progress"] = 10
        task_info["message"] = "Conectando..."

        # Connect
        if not await installer.connect():
            raise Exception("Falha ao conectar")

        task_info["progress"] = 20
        task_info["message"] = "Detectando SO..."

        # Detect OS
        if not await installer.detect_os():
            raise Exception("Falha ao detectar SO")

        task_info["progress"] = 25
        task_info["message"] = "Verificando espaço em disco..."

        # Check disk space
        await installer.check_disk_space()

        task_info["progress"] = 30
        task_info["message"] = "Iniciando instalação..."

        # Install
        success = await installer.install_exporter(request.collector_profile)
        if not success:
            raise Exception("Instalação falhou")

        task_info["progress"] = 85
        task_info["message"] = "Validando instalação..."

        # Validate
        if not await installer.validate_installation():
            raise Exception("Validação falhou")

        task_info["progress"] = 95
        task_info["message"] = "Finalizando..."

        # Register in Consul if requested
        if request.register_in_consul:
            await register_in_consul(installer, request)

        task_info["progress"] = 100
        task_info["status"] = "completed"
        task_info["message"] = "Instalação concluída com sucesso!"
        task_info["completed_at"] = datetime.now().isoformat()

        await installer.log("=== INSTALAÇÃO CONCLUÍDA COM SUCESSO ===", "success")

    except Exception as e:
        logger.error(f"Erro na instalação {installation_id}: {e}", exc_info=True)
        task_info["status"] = "failed"
        task_info["message"] = f"Erro: {str(e)}"
        task_info["completed_at"] = datetime.now().isoformat()

        if installer:
            await installer.log(f"ERRO: {str(e)}", "error")

    finally:
        if installer:
            await installer.disconnect()


async def register_in_consul(installer, request):
    """Register exporter in Consul"""
    try:
        consul = ConsulManager()

        # Determine target node
        target_node = Config.MAIN_SERVER
        service_name = "selfnode_exporter" if request.os_type == "linux" else "windows_exporter"

        if request.consul_node:
            if request.consul_node.lower() == "rio":
                target_node = "172.16.200.14"
                if request.os_type == "linux":
                    service_name = "selfnode_exporter_rio"

        # Get system info
        system_info = await installer.get_system_info()
        hostname = system_info.get("hostname", request.host)

        port = 9100 if request.os_type == "linux" else 9182
        service_id = f"{service_name}/{hostname}@{request.host}"

        service_data = {
            "id": service_id,
            "name": service_name,
            "tags": [request.os_type, request.method],
            "address": request.host,
            "port": port,
            "Meta": {
                "instance": f"{request.host}:{port}",
                "name": hostname,
                "company": "Skills IT",
                "env": "prod",
                "project": "Monitoring",
                "module": "node_exporter" if request.os_type == "linux" else "windows_exporter",
                "tipo": "Server",
                "os": request.os_type
            }
        }

        await consul.register_service(service_data, target_node)
        await installer.log(f"Registrado no Consul: {service_id}", "success")

    except Exception as e:
        logger.error(f"Erro ao registrar no Consul: {e}")
        await installer.log(f"Erro ao registrar no Consul: {e}", "warning")
