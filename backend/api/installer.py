"""
API endpoints para instalação remota de Exporters
Suporta múltiplos métodos de instalação para Windows e Linux
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Literal, Union, Any
from enum import Enum
import asyncio
import uuid
import socket
from core.installers import (
    LinuxSSHInstaller,
    WindowsPSExecInstaller,
    WindowsWinRMInstaller,
    WindowsSSHInstaller,
    WindowsMultiConnector
)
from core.installers.task_state import (
    installation_tasks,
    create_task
)
from core.consul_manager import ConsulManager
from core.config import Config
import logging

router = APIRouter(tags=["Installer"])
logger = logging.getLogger(__name__)

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
    basic_auth_user: Optional[str] = Field(None, description="Usuário para Basic Auth")
    basic_auth_password: Optional[str] = Field(None, description="Senha para Basic Auth")


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
    basic_auth_user: Optional[str] = Field(None, description="Usuário para Basic Auth")
    basic_auth_password: Optional[str] = Field(None, description="Senha para Basic Auth")


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
    basic_auth_user: Optional[str] = Field(None, description="Usuário para Basic Auth")
    basic_auth_password: Optional[str] = Field(None, description="Senha para Basic Auth")


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
    basic_auth_user: Optional[str] = Field(None, description="Usuário para Basic Auth")
    basic_auth_password: Optional[str] = Field(None, description="Senha para Basic Auth")


class InstallResponse(BaseModel):
    """Response quando instalação é iniciada"""
    success: bool
    message: str
    installation_id: str
    websocket_url: str
    details: Dict


class InstallLogEntry(BaseModel):
    """Log estruturado da instalação"""
    timestamp: str
    level: str
    message: str
    data: Optional[Dict[str, Any]] = None


class InstallStatusResponse(BaseModel):
    """Status de uma instalação"""
    installation_id: str
    status: str
    progress: int
    message: str
    details: Optional[Dict] = None
    error_code: Optional[str] = None
    error_category: Optional[str] = None
    error_details: Optional[str] = None
    logs: List[InstallLogEntry] = Field(default_factory=list)


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
        create_task(installation_id, {
            "status": "pending",
            "progress": 0,
            "message": "Instalação na fila",
            "host": validated_request.host,
            "os_type": os_type,
            "method": method,
            "started_at": None,
            "completed_at": None,
            "error_code": None,
            "error_category": None,
            "error_details": None
        })

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
        },
        error_code=task_info.get("error_code"),
        error_category=task_info.get("error_category"),
        error_details=task_info.get("error_details"),
        logs=[
            InstallLogEntry(
                timestamp=entry.get("timestamp", ""),
                level=entry.get("level", "info"),
                message=entry.get("message", ""),
                data=entry.get("data") if isinstance(entry.get("data"), dict) else None
            )
            for entry in task_info.get("logs", [])
            if entry.get("message")
        ]
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
    
    Para Windows: Tenta automaticamente PSExec -> WinRM -> SSH
    Para Linux: Usa SSH diretamente

    Detecta SO e retorna informações do sistema
    """
    try:
        os_type = request.get("os_type", "").lower()
        method = request.get("method", "").lower()

        # Create appropriate installer
        test_id = "test-" + str(uuid.uuid4())[:8]
        installer = None
        connection_method = method
        multi_connector = None  # Inicializar para Windows

        if os_type == "linux":
            # Linux: sempre SSH
            installer = LinuxSSHInstaller(
                host=request["host"],
                username=request["username"],
                password=request.get("password"),
                key_file=request.get("key_file"),
                ssh_port=request.get("ssh_port", 22),
                use_sudo=request.get("use_sudo", True),
                client_id=test_id
            )
            
            # Test connection
            try:
                if not await installer.connect():
                    raise HTTPException(
                        status_code=503,
                        detail="CONNECTION_FAILED|Falha ao conectar via SSH.|CONEXAO"
                    )
            except HTTPException:
                raise
            except Exception as e:
                error_msg = str(e)
                logger.error(f"Erro ao testar conexão Linux: {error_msg}")
                
                if "|" in error_msg:
                    parts = error_msg.split("|")
                    error_code = parts[0] if len(parts) > 0 else "UNKNOWN"
                    
                    if error_code == "AUTH_FAILED" or error_code == "AUTH_METHOD_UNAVAILABLE":
                        status_code = 401
                    elif error_code == "PERMISSION_DENIED":
                        status_code = 403
                    elif error_code == "TIMEOUT":
                        status_code = 504
                    elif error_code in ["CONNECTION_REFUSED", "PORT_CLOSED", "DNS_ERROR", "NETWORK_UNREACHABLE", "NETWORK_ERROR", "SSH_ERROR", "HOSTKEY_ERROR"]:
                        status_code = 503
                    else:
                        status_code = 500
                    
                    raise HTTPException(status_code=status_code, detail=error_msg)
                else:
                    raise HTTPException(
                        status_code=503,
                        detail=f"CONNECTION_ERROR|{error_msg}|DESCONHECIDO"
                    )
        
        elif os_type == "windows":
            # Windows: usar MultiConnector para tentar todos os métodos
            logger.info(f"Iniciando conexão Windows com multi-connector para {request['host']}")
            
            multi_connector = WindowsMultiConnector(
                host=request["host"],
                username=request["username"],
                password=request["password"],
                domain=request.get("domain"),
                client_id=test_id,
                ssh_port=request.get("ssh_port", 22),
                winrm_port=request.get("port"),
                winrm_use_ssl=request.get("use_ssl", False),
                psexec_path=request.get("psexec_path", "psexec.exe"),
                key_file=request.get("key_file")
            )
            
            try:
                success, message, installer = await multi_connector.connect_with_fallback()
                if not success or not installer:
                    raise HTTPException(
                        status_code=503,
                        detail="ALL_METHODS_FAILED|Todos os métodos de conexão falharam. Veja logs.|CONEXAO_MULTIPLA"
                    )
                
                connection_method = multi_connector.connection_method
                logger.info(f"Windows conectado com sucesso via: {connection_method}")
                
            except Exception as e:
                error_msg = str(e)
                logger.error(f"Erro ao testar conexão Windows multi-método: {error_msg}")
                
                # Capturar resumo das tentativas para incluir na resposta
                connection_summary = multi_connector.get_connection_summary()
                
                if "|" in error_msg:
                    parts = error_msg.split("|")
                    error_code = parts[0] if len(parts) > 0 else "UNKNOWN"
                    
                    # Para ALL_METHODS_FAILED, retornar 503 com detalhes
                    if error_code == "ALL_METHODS_FAILED":
                        detail_msg = f"{error_msg}\n\nTentativas realizadas:\n"
                        for attempt in connection_summary["attempts"]:
                            status = "✅" if attempt["success"] else "❌"
                            detail_msg += f"• {attempt['method'].upper()}: {status} - {attempt['message']}\n"
                        
                        raise HTTPException(status_code=503, detail=detail_msg)
                    else:
                        # Outros erros estruturados
                        status_code = 503
                        if error_code in ["AUTH_FAILED", "AUTH_METHOD_UNAVAILABLE"]:
                            status_code = 401
                        elif error_code == "PERMISSION_DENIED":
                            status_code = 403
                        elif error_code == "TIMEOUT":
                            status_code = 504
                        
                        raise HTTPException(status_code=status_code, detail=error_msg)
                else:
                    raise HTTPException(
                        status_code=503,
                        detail=f"CONNECTION_ERROR|{error_msg}|DESCONHECIDO"
                    )
        else:
            raise HTTPException(status_code=400, detail="Sistema operacional inválido")

        # Detect OS
        detected_os = await installer.detect_os()
        if not detected_os:
            await installer.disconnect()
            raise HTTPException(status_code=400, detail="SO não suportado")

        # Get system info
        system_info = await installer.get_system_info()

        await installer.disconnect()

        # Construir resposta com informações do método usado
        response = {
            "success": True,
            "message": "Conexão bem-sucedida",
            "details": {
                **system_info,
                "method": connection_method  # Método que realmente funcionou
            }
        }
        
        # Se foi Windows multi-connector, incluir resumo das tentativas
        if os_type == "windows":
            response["connection_summary"] = multi_connector.get_connection_summary()
            response["message"] = f"Conexão Windows bem-sucedida via {connection_method.upper()}"
        
        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao testar conexão: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/check-existing")
async def check_existing_installation(request: Dict):
    """
    Verifica se já existe instalação do exporter no servidor remoto
    
    Retorna:
        - port_open: bool - Porta do exporter está em uso
        - service_running: bool - Serviço está rodando
        - has_config: bool - Arquivo de configuração existe
    """
    try:
        host = request["host"]
        username = request["username"]
        password = request.get("password")
        port = request.get("port", 22)
        exporter_port = request.get("exporter_port", 9100)
        target_type = request.get("target_type", "linux")
        
        # Criar instalador temporário apenas para verificação
        check_id = "check-" + str(uuid.uuid4())[:8]
        installer = None
        
        if target_type == "linux":
            installer = LinuxSSHInstaller(
                host=host,
                username=username,
                password=password,
                ssh_port=port,
                use_sudo=True,
                client_id=check_id
            )
            
            # Conectar
            if not await installer.connect():
                raise HTTPException(status_code=503, detail="CONNECTION_FAILED|Não foi possível conectar ao servidor|CONEXAO")
                
        else:
            # Windows: usar multi-connector
            logger.info(f"[check-existing] Verificando instalação Windows em {host} usando multi-connector")
            
            multi_connector = WindowsMultiConnector(
                host=host,
                username=username,
                password=password,
                domain=request.get("domain"),
                client_id=check_id,
                ssh_port=port,
                winrm_port=request.get("winrm_port"),
                winrm_use_ssl=request.get("use_ssl", False)
            )
            
            try:
                success, message, installer = await multi_connector.connect_with_fallback()
                if not success or not installer:
                    logger.error(f"[check-existing] ❌ Falha ao conectar: {message}")
                    raise HTTPException(
                        status_code=503,
                        detail="ALL_METHODS_FAILED|Todos os métodos de conexão falharam ao verificar instalação|CONEXAO_MULTIPLA"
                    )
                logger.info(f"[check-existing] ✅ Windows conectado via {multi_connector.connection_method} para verificação")
            except HTTPException:
                raise
            except Exception as e:
                error_msg = str(e)
                logger.error(f"[check-existing] ❌ Erro ao conectar Windows: {error_msg}", exc_info=True)
                raise HTTPException(status_code=503, detail=error_msg if "|" in error_msg else f"CONNECTION_ERROR|{error_msg}|CONEXAO")
        
        # Verificar porta
        port_open = False
        try:
            # Testar se a porta está em uso (netstat/ss)
            if target_type == "linux":
                exit_code, stdout, stderr = await installer.execute_command(f"sudo ss -tuln | grep ':{exporter_port}' || true")
                result = stdout
            else:
                exit_code, stdout, stderr = await installer.execute_command(f"netstat -an | findstr ':{exporter_port}'")
                result = stdout
            
            port_open = bool(result and len(result.strip()) > 0)
        except Exception as e:
            logger.warning(f"Erro ao verificar porta: {e}")
        
        # Verificar serviço
        service_running = False
        try:
            if target_type == "linux":
                exit_code, stdout, stderr = await installer.execute_command("sudo systemctl is-active node_exporter 2>/dev/null || echo 'inactive'")
                service_running = stdout.strip() == "active"
            else:
                exit_code, stdout, stderr = await installer.execute_command("sc query windows_exporter 2>nul")
                service_running = "RUNNING" in stdout
        except Exception as e:
            logger.warning(f"Erro ao verificar serviço: {e}")
        
        # Verificar arquivo de configuração
        has_config = False
        try:
            if target_type == "linux":
                exit_code, stdout, stderr = await installer.execute_command("test -f /etc/systemd/system/node_exporter.service && echo 'exists' || echo 'not found'")
                has_config = "exists" in stdout
            else:
                exit_code, stdout, stderr = await installer.execute_command("if exist C:\\Program Files\\windows_exporter\\windows_exporter.exe echo exists")
                has_config = "exists" in stdout
        except Exception as e:
            logger.warning(f"Erro ao verificar config: {e}")
        
        await installer.disconnect()
        
        return {
            "port_open": port_open,
            "service_running": service_running,
            "has_config": has_config
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao verificar instalação existente: {e}", exc_info=True)
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

        # Install (pass Basic Auth params for Linux and Windows)
        if isinstance(request, (LinuxSSHInstallRequest, WindowsPSExecInstallRequest, WindowsWinRMInstallRequest, WindowsSSHInstallRequest)):
            # Check if request has basic_auth attributes
            basic_auth_user = getattr(request, 'basic_auth_user', None)
            basic_auth_password = getattr(request, 'basic_auth_password', None)
            
            success = await installer.install_exporter(
                request.collector_profile,
                basic_auth_user,
                basic_auth_password
            )
        else:
            success = await installer.install_exporter(request.collector_profile)
            
        if not success:
            raise Exception("Instalação falhou")

        task_info["progress"] = 85
        task_info["message"] = "Validando instalação..."

        # Validate (pass Basic Auth params for Linux and Windows)
        if isinstance(request, (LinuxSSHInstallRequest, WindowsPSExecInstallRequest, WindowsWinRMInstallRequest, WindowsSSHInstallRequest)):
            basic_auth_user = getattr(request, 'basic_auth_user', None)
            basic_auth_password = getattr(request, 'basic_auth_password', None)
            
            if not await installer.validate_installation(
                basic_auth_user,
                basic_auth_password
            ):
                raise Exception("Validação falhou")
        else:
            # Fallback para métodos sem basic auth
            validate_method = getattr(installer, 'validate_installation', None)
            if validate_method:
                import inspect
                sig = inspect.signature(validate_method)
                if len(sig.parameters) > 0:
                    if not await installer.validate_installation(None, None):
                        raise Exception("Validação falhou")
                else:
                    if not await installer.validate_installation():
                        raise Exception("Validação falhou")
            else:
                raise Exception("Método validate_installation não encontrado")

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
        raw_message = str(e) if e else "Erro desconhecido"
        error_code = "INSTALLATION_ERROR"
        error_category = "installer"
        error_details = None
        user_message = raw_message

        if "|" in raw_message:
            parts = [part.strip() for part in raw_message.split("|")]
            if len(parts) >= 2 and parts[1]:
                error_code = parts[0] or error_code
                user_message = parts[1]
            else:
                error_code = parts[0] or error_code
            if len(parts) >= 3 and parts[2]:
                error_category = parts[2]
            if len(parts) >= 4:
                error_details = "|".join(parts[3:]).strip() or None

        display_message = user_message
        if not display_message.lower().startswith("erro"):
            display_message = f"Erro: {display_message}"

        task_info["status"] = "failed"
        task_info["message"] = display_message
        task_info["completed_at"] = datetime.now().isoformat()
        task_info["error_code"] = error_code
        task_info["error_category"] = error_category
        task_info["error_details"] = error_details

        if installer:
            await installer.log(f"ERRO: {str(e)}", "error")
            if error_details:
                await installer.log(f"Detalhes: {error_details}", "debug")

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

        # Build metadata
        service_meta = {
            "instance": f"{request.host}:{port}",
            "name": hostname,
            "company": "Skills IT",
            "env": "prod",
            "project": "Monitoring",
            "module": "node_exporter" if request.os_type == "linux" else "windows_exporter",
            "tipo": "Server",
            "os": request.os_type
        }
        
        # Build health check configuration
        check_config: Dict[str, Any] = {
            "HTTP": f"http://{request.host}:{port}/metrics",
            "Interval": "30s",
            "Timeout": "10s"
        }
        
        # Add Basic Auth credentials to metadata for Prometheus scraping
        if hasattr(request, 'basic_auth_user') and request.basic_auth_user and hasattr(request, 'basic_auth_password') and request.basic_auth_password:
            service_meta["basic_auth_enabled"] = "true"
            service_meta["basic_auth_user"] = request.basic_auth_user
            
            # Add Basic Auth to health check
            import base64
            auth_string = f"{request.basic_auth_user}:{request.basic_auth_password}"
            b64_auth = base64.b64encode(auth_string.encode()).decode()
            check_config["Header"] = {
                "Authorization": [f"Basic {b64_auth}"]
            }
            
            await installer.log(f"Basic Auth configurado no health check do Consul", "info")
            await installer.log(f"Basic Auth metadata adicionado ao Consul para Prometheus", "info")

        service_data = {
            "id": service_id,
            "name": service_name,
            "tags": [request.os_type, request.method],
            "address": request.host,
            "port": port,
            "Meta": service_meta,
            "Check": check_config
        }

        await consul.register_service(service_data, target_node)
        await installer.log(f"Registrado no Consul: {service_id}", "success")
        
        if hasattr(request, 'basic_auth_user') and request.basic_auth_user and hasattr(request, 'basic_auth_password') and request.basic_auth_password:
            await installer.log(f"✓ Health check do Consul configurado com Basic Auth", "success")
            await installer.log(f"✓ Metadata inclui basic_auth_enabled=true para Prometheus", "success")
            await installer.log(f"✓ Prometheus pode usar service discovery do Consul para obter credenciais", "info")
        else:
            await installer.log(f"⚠ Instalação SEM Basic Auth - métricas expostas publicamente", "warning")

    except Exception as e:
        logger.error(f"Erro ao registrar no Consul: {e}")
        await installer.log(f"Erro ao registrar no Consul: {e}", "warning")
