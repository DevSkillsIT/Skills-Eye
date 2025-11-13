"""
API endpoints para instalação remota de Node Exporter via SSH
Usa WebSocket para logs em tempo real
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import asyncio
import uuid
from core.remote_installer import RemoteExporterInstaller
from core.consul_manager import ConsulManager
from core.config import Config
from core.installers.task_state import installation_tasks, create_task
import logging

router = APIRouter()
logger = logging.getLogger(__name__)


class InstallRequest(BaseModel):
    """Requisição de instalação de Node Exporter"""
    host: str = Field(..., description="Endereço IP ou hostname do servidor")
    username: str = Field(..., description="Usuário SSH")
    password: Optional[str] = Field(None, description="Senha SSH (se não usar chave)")
    key_file: Optional[str] = Field(None, description="Caminho para chave SSH privada")
    ssh_port: int = Field(22, description="Porta SSH")
    use_sudo: bool = Field(True, description="Usar sudo para comandos")
    collector_profile: str = Field("recommended", description="Perfil de collectors (recommended, full, minimal)")
    register_in_consul: bool = Field(True, description="Registrar no Consul após instalação")
    consul_node: Optional[str] = Field(None, description="Nó Consul para registro (Palmas, Rio)")


class InstallResponse(BaseModel):
    """Resposta de início de instalação"""
    success: bool
    message: str
    installation_id: str
    websocket_url: str


class InstallLogEntry(BaseModel):
    """Log estruturado de instalações legacy"""
    timestamp: str
    level: str
    message: str
    data: Optional[Dict[str, Any]] = None


class InstallStatusResponse(BaseModel):
    """Status de instalação"""
    installation_id: str
    status: str  # pending, running, completed, failed
    progress: int
    message: str
    details: Optional[Dict] = None
    logs: List[InstallLogEntry] = Field(default_factory=list)


@router.post("/install", response_model=InstallResponse)
async def install_node_exporter(
    request: InstallRequest,
    background_tasks: BackgroundTasks
):
    """
    Inicia instalação remota de Node Exporter via SSH

    Retorna um installation_id que pode ser usado para conectar ao WebSocket
    e acompanhar os logs em tempo real.

    WebSocket URL: ws://localhost:5000/ws/installer/{installation_id}
    """
    try:
        # Gerar ID único para esta instalação
        installation_id = str(uuid.uuid4())

        # Validar parâmetros básicos
        if not request.password and not request.key_file:
            raise HTTPException(
                status_code=400,
                detail="É necessário fornecer password ou key_file"
            )

        # Validar perfil de collectors
        valid_profiles = ['recommended', 'full', 'minimal']
        if request.collector_profile not in valid_profiles:
            raise HTTPException(
                status_code=400,
                detail=f"Perfil inválido. Use: {', '.join(valid_profiles)}"
            )

        # Armazenar status inicial
        create_task(installation_id, {
            "status": "pending",
            "progress": 0,
            "message": "Instalação na fila",
            "host": request.host,
            "started_at": None,
            "completed_at": None
        })

        # Iniciar instalação em background
        background_tasks.add_task(
            run_installation,
            installation_id,
            request
        )

        logger.info(f"Instalação iniciada: {installation_id} para {request.host}")

        return InstallResponse(
            success=True,
            message=f"Instalação iniciada para {request.host}",
            installation_id=installation_id,
            websocket_url=f"/ws/installer/{installation_id}"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao iniciar instalação: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/install/{installation_id}/status", response_model=InstallStatusResponse)
async def get_install_status(installation_id: str):
    """
    Obtém status de uma instalação

    Retorna informações sobre progresso e status atual
    """
    if installation_id not in installation_tasks:
        raise HTTPException(
            status_code=404,
            detail="Instalação não encontrada"
        )

    task_info = installation_tasks[installation_id]

    return InstallStatusResponse(
        installation_id=installation_id,
        status=task_info["status"],
        progress=task_info["progress"],
        message=task_info["message"],
        details={
            "host": task_info["host"],
            "started_at": task_info["started_at"],
            "completed_at": task_info["completed_at"]
        },
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
    """
    Lista todas as instalações ativas ou recentes

    Retorna informações sobre instalações em andamento ou concluídas recentemente
    """
    return {
        "success": True,
        "installations": [
            {
                "installation_id": inst_id,
                "host": info["host"],
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
    """
    Cancela uma instalação em andamento

    Nota: A instalação pode não parar imediatamente se já estiver executando comandos
    """
    if installation_id not in installation_tasks:
        raise HTTPException(
            status_code=404,
            detail="Instalação não encontrada"
        )

    task_info = installation_tasks[installation_id]

    if task_info["status"] in ["completed", "failed"]:
        raise HTTPException(
            status_code=400,
            detail=f"Instalação já {task_info['status']}"
        )

    # Marcar como cancelado
    task_info["status"] = "cancelled"
    task_info["message"] = "Instalação cancelada pelo usuário"

    return {
        "success": True,
        "message": "Instalação marcada para cancelamento",
        "installation_id": installation_id
    }


@router.get("/collectors/profiles")
async def get_collector_profiles():
    """
    Retorna perfis de collectors disponíveis

    Mostra quais collectors são habilitados em cada perfil
    """
    from core.remote_installer import NODE_EXPORTER_COLLECTORS, NODE_EXPORTER_COLLECTOR_DETAILS

    profiles = {}
    for profile_name, config in NODE_EXPORTER_COLLECTORS.items():
        profiles[profile_name] = {
            "enabled": [
                {
                    "name": col,
                    "description": NODE_EXPORTER_COLLECTOR_DETAILS.get(col, "N/A")
                }
                for col in config.get('enable', [])
            ],
            "disabled": config.get('disable', [])
        }

    return {
        "success": True,
        "profiles": profiles
    }


@router.post("/test-connection")
async def test_ssh_connection(request: InstallRequest):
    """
    Testa conexão SSH sem instalar nada

    Útil para validar credenciais antes de iniciar a instalação
    """
    try:
        # Criar installer temporário
        test_id = "test-" + str(uuid.uuid4())[:8]

        installer = RemoteExporterInstaller(
            host=request.host,
            username=request.username,
            password=request.password,
            key_file=request.key_file,
            ssh_port=request.ssh_port,
            use_sudo=request.use_sudo,
            client_id=test_id
        )

        # Tentar conectar
        if not await installer.connect():
            raise HTTPException(
                status_code=503,
                detail="Falha ao conectar via SSH. Verifique credenciais e conectividade."
            )

        # Detectar SO
        os_type = await installer.detect_os()

        if not os_type:
            installer.close()
            raise HTTPException(
                status_code=400,
                detail="Sistema operacional não suportado"
            )

        # Obter informações do sistema
        exit_code, hostname, _ = await installer.execute_command("hostname")
        hostname = hostname.strip() if exit_code == 0 else "unknown"

        exit_code, uptime, _ = await installer.execute_command("uptime")
        uptime = uptime.strip() if exit_code == 0 else "unknown"

        installer.close()

        return {
            "success": True,
            "message": "Conexão SSH bem-sucedida",
            "details": {
                "host": request.host,
                "os_type": os_type,
                "os_details": installer.os_details,
                "hostname": hostname,
                "uptime": uptime,
                "ssh_port": request.ssh_port,
                "username": request.username
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao testar conexão: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao testar conexão: {str(e)}"
        )


# ============================================================================
# FUNÇÕES DE BACKGROUND
# ============================================================================

async def run_installation(installation_id: str, request: InstallRequest):
    """
    Executa instalação em background

    Envia logs via WebSocket em tempo real
    """
    from datetime import datetime

    task_info = installation_tasks[installation_id]
    task_info["status"] = "running"
    task_info["started_at"] = datetime.now().isoformat()

    installer = None

    try:
        # Criar installer
        installer = RemoteExporterInstaller(
            host=request.host,
            username=request.username,
            password=request.password,
            key_file=request.key_file,
            ssh_port=request.ssh_port,
            use_sudo=request.use_sudo,
            client_id=installation_id
        )

        task_info["progress"] = 10
        task_info["message"] = "Conectando via SSH..."

        # Conectar
        if not await installer.connect():
            raise Exception("Falha ao conectar via SSH")

        task_info["progress"] = 20
        task_info["message"] = "Detectando sistema operacional..."

        # Detectar SO
        os_type = await installer.detect_os()
        if not os_type or os_type != 'linux':
            raise Exception("Sistema operacional não suportado. Apenas Linux é suportado.")

        task_info["progress"] = 30
        task_info["message"] = "Iniciando instalação..."

        # Instalar
        success = await installer.install_node_exporter(
            collector_profile=request.collector_profile
        )

        if not success:
            raise Exception("Instalação falhou")

        task_info["progress"] = 80
        task_info["message"] = "Validando instalação..."

        # Validar
        if not await installer.validate_installation():
            raise Exception("Validação falhou")

        task_info["progress"] = 90
        task_info["message"] = "Instalação concluída"

        # Registrar no Consul se solicitado
        if request.register_in_consul:
            task_info["message"] = "Registrando no Consul..."

            try:
                consul = ConsulManager()

                # Determinar nó Consul
                target_node = Config.MAIN_SERVER
                service_name = "selfnode_exporter"

                if request.consul_node:
                    if request.consul_node.lower() == "rio":
                        target_node = "172.16.200.14"
                        service_name = "selfnode_exporter_rio"

                # Obter hostname
                exit_code, hostname, _ = await installer.execute_command("hostname")
                hostname = hostname.strip() if exit_code == 0 else request.host

                service_id = f"selfnode/{hostname}@{request.host}"

                service_data = {
                    "id": service_id,
                    "name": service_name,
                    "tags": ["linux", "node_exporter"],
                    "address": request.host,
                    "port": 9100,
                    "Meta": {
                        "instance": f"{request.host}:9100",
                        "name": hostname,
                        "company": "Skills IT",
                        "env": "prod",
                        "project": "Monitoring",
                        "module": "node_exporter",
                        "tipo": "Server",
                        "os": "linux"
                    }
                }

                await consul.register_service(service_data, target_node)

                await installer.log(f"Registrado no Consul: {service_id}", "success")

            except Exception as e:
                logger.error(f"Erro ao registrar no Consul: {e}")
                await installer.log(f"Erro ao registrar no Consul: {e}", "warning")

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
            installer.close()
