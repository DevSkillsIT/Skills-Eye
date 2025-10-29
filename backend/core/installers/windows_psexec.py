"""
Windows Exporter installer via PSexec
Uses pypsexec library for pure Python implementation
No need for PSExec.exe executable
"""
import asyncio
import socket
import logging
import requests
from typing import Tuple, Optional, Dict
from pathlib import Path
from .base import BaseInstaller

try:
    from pypsexec.client import Client
    from pypsexec.exceptions import PypsexecException, SCMRException
    PYPSEXEC_AVAILABLE = True
except ImportError:
    PYPSEXEC_AVAILABLE = False
    Client = None
    PypsexecException = Exception
    SCMRException = Exception


logger = logging.getLogger(__name__)


# Collector configurations
WINDOWS_EXPORTER_COLLECTORS = {
    'recommended': ['cpu', 'cs', 'logical_disk', 'memory', 'net', 'os', 'system'],
    'full': ['cpu', 'cs', 'logical_disk', 'memory', 'net', 'os', 'system', 'service', 'tcp', 'thermalzone'],
    'minimal': ['cpu', 'memory', 'logical_disk', 'os']
}


def test_port(host: str, port: int, timeout: int = 10) -> bool:
    """
    Test if a port is open on a host
    
    Returns:
        True: Port is open and accepting connections
        False: Port is closed/filtered but host responded quickly (connection refused)
        
    Raises:
        socket.gaierror: DNS resolution failed
        socket.timeout: Connection timeout (host unreachable, offline, or network very slow)
        ConnectionRefusedError: Connection actively refused by host
        Exception: Other network errors (unreachable, no route, etc)
    """
    sock = None
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        
        # Analyze result codes:
        # 0 = success, port open
        # 10061 (Windows) or 111 (Linux) = connection refused (host UP, port closed)
        # 10060 (Windows) or 110 (Linux) = timeout (host DOWN or unreachable)
        
        if result == 0:
            return True
        elif result in (10061, 111):  # Connection refused - host is UP but port closed
            return False
        elif result in (10060, 110, 10065, 113):  # Timeout or unreachable - host is DOWN
            raise socket.timeout(f"Connection to {host}:{port} timed out (error code {result}). Host may be offline or unreachable.")
        else:
            # Other error codes - treat as network issue
            raise Exception(f"Network error connecting to {host}:{port} (error code {result})")
            
    except socket.gaierror as e:
        # DNS resolution failed - cannot resolve hostname
        raise socket.gaierror(f"DNS resolution failed for {host}: {e}")
    except socket.timeout:
        # Connection timed out - propagate the exception
        raise
    except OSError as e:
        # Handle OS-level errors (unreachable, no route, etc)
        error_msg = str(e).lower()
        if "timed out" in error_msg or "timeout" in error_msg:
            raise socket.timeout(f"Connection to {host}:{port} timed out: {e}")
        else:
            raise Exception(f"Network error testing {host}:{port}: {e}")
    except Exception as e:
        # Other unexpected errors
        raise Exception(f"Unexpected error testing {host}:{port}: {e}")
    finally:
        if sock:
            try:
                sock.close()
            except:
                pass


class WindowsPSExecInstaller(BaseInstaller):
    """Windows Exporter installer via pypsexec library"""

    def __init__(
        self,
        host: str,
        username: str,
        password: str,
        domain: Optional[str] = None,
        psexec_path: Optional[str] = None,  # Not used anymore, kept for compatibility
        client_id: str = "default"
    ):
        super().__init__(host, client_id)
        self.username = username
        self.password = password
        self.domain = domain  # Domain for domain accounts
        self.client = None
        
        # pypsexec expects username without domain prefix
        # domain is passed separately to the client

    async def validate_connection(self) -> Tuple[bool, str]:
        """Validate connection parameters with network checks"""
        await self.log(f"🔧 Validando pypsexec para {self.host}...", "info")

        # Check if pypsexec is available
        if not PYPSEXEC_AVAILABLE:
            return False, "DEPENDENCY_MISSING|pypsexec não está instalado. Execute: pip install pypsexec|dependency"

        # Test network connectivity and DNS
        await self.log(f"🌐 Testando conectividade com {self.host}...", "info")
        
        try:
            # Test SMB port (445) with detailed error handling
            port_open = await asyncio.to_thread(test_port, self.host, 445, 10)
            if not port_open:
                await self.log("⚠️ Porta SMB 445 não está acessível (bloqueada por firewall)", "warning")
                return False, "PORT_CLOSED|Porta SMB 445 está bloqueada ou inacessível|network"
            
            await self.log("✅ Porta SMB 445 está acessível", "success")
            
        except socket.gaierror as e:
            # DNS resolution failed
            await self.log(f"❌ Falha na resolução DNS: {e}", "error")
            return False, f"DNS_ERROR|Não foi possível resolver o hostname {self.host}|network"
            
        except socket.timeout as e:
            # Connection timeout - host offline or unreachable
            await self.log(f"❌ Timeout: {e}", "error")
            return False, f"TIMEOUT|Host {self.host} não respondeu (offline ou rede inacessível)|network"
            
        except Exception as e:
            # Other network errors
            await self.log(f"❌ Erro de rede: {e}", "error")
            return False, f"NETWORK_ERROR|Erro de conectividade: {e}|network"

        await self.log("✅ pypsexec disponível e host acessível", "success")
        return True, "OK"

    async def connect(self) -> bool:
        """Test connection via pypsexec"""
        try:
            valid, msg = await self.validate_connection()
            if not valid:
                await self.log(f"❌ {msg}", "error")
                # Raise structured exception
                raise Exception(msg)

            await self.log("🔌 Testando conexão pypsexec...", "info")

            # 🔧 Preparar username com domínio se necessário
            # pypsexec aceita: "DOMAIN\\username" ou "username@domain" ou "username"
            username_to_use = self.username
            
            # Se username já tem domínio (DOMAIN\username ou username@domain), usar como está
            if "\\" not in username_to_use and "@" not in username_to_use and self.domain:
                # Adicionar domínio no formato DOMAIN\username
                username_to_use = f"{self.domain}\\{self.username}"
                await self.log(f"🔑 Usando credenciais de domínio: {username_to_use}", "info")
            else:
                await self.log(f"🔑 Usando credenciais: {username_to_use}", "info")

            # Create pypsexec client
            def _connect():
                if Client is None:
                    raise RuntimeError("pypsexec client is unavailable")
                client = Client(
                    self.host,
                    username=username_to_use,
                    password=self.password,
                    port=445,
                    encrypt=False  # Usar modo compatível com PsExec.exe (sem SMB encryption)
                )
                try:
                    client.connect()

                    # Garantir limpeza caso restem artefatos de execuções anteriores
                    try:
                        client.cleanup()
                    except Exception as cleanup_err:
                        # Apenas registrar; não bloquear sequência normal
                        logger.warning(f"[psexec] Falha ao executar cleanup inicial: {cleanup_err}")

                    client.create_service()
                    # Teste simples (sem flags especiais)
                    stdout, stderr, rc = client.run_executable(
                        "cmd.exe",
                        arguments="/c echo Connected"
                    )

                    try:
                        client.remove_service()
                    except Exception as remove_err:
                        logger.warning(f"[psexec] Falha ao remover serviço temporário: {remove_err}")
                        # Tentar limpeza forçada
                        try:
                            client.cleanup()
                        except Exception as cleanup_err:
                            logger.warning(f"[psexec] Cleanup após remoção falhou: {cleanup_err}")

                    client.disconnect()
                    return rc == 0, stdout, stderr
                except Exception as e:
                    try:
                        client.cleanup()
                    except Exception as cleanup_err:
                        logger.warning(f"[psexec] Cleanup em exceção falhou: {cleanup_err}")
                    try:
                        client.disconnect()
                    except:
                        pass
                    raise e

            success, stdout, stderr = await asyncio.to_thread(_connect)

            if success:
                await self.log("✅ Conexão pypsexec bem-sucedida", "success")
                return True
            else:
                await self.log(f"❌ Falha na conexão pypsexec: {stderr}", "error")
                raise Exception(f"CONNECTION_FAILED|Falha ao executar comando teste: {stderr}|connection")

        except PypsexecException as e:
            error_msg = str(e)
            await self.log(f"❌ Erro pypsexec: {error_msg}", "error")
            
            # Map common errors to structured format
            if "STATUS_LOGON_FAILURE" in error_msg or "0xc000006d" in error_msg:
                raise Exception("AUTH_FAILED|Usuário ou senha inválidos|authentication")
            elif "STATUS_LOGON_TYPE_NOT_GRANTED" in error_msg or "0xc0000192" in error_msg:
                raise Exception("PERMISSION_DENIED|Usuário não tem permissão de logon remoto neste computador. Adicione o usuário ao grupo 'Administradores' ou 'Usuários da Área de Trabalho Remota'|authentication")
            elif "STATUS_ACCOUNT_RESTRICTION" in error_msg or "0xc000006e" in error_msg:
                raise Exception("AUTH_FAILED|Conta com restrições - verifique se é administrador local|authentication")
            elif "STATUS_ACCESS_DENIED" in error_msg or "Access is denied" in error_msg or "0xc0000022" in error_msg:
                raise Exception("PERMISSION_DENIED|Acesso negado - credenciais sem permissões administrativas|authentication")
            elif "STATUS_CANNOT_DELETE" in error_msg or "0xc0000121" in error_msg:
                raise Exception("PERMISSION_DENIED|Erro de permissão ao gerenciar serviço - verifique se o usuário é administrador local|authentication")
            elif "STATUS_OBJECT_NAME_NOT_FOUND" in error_msg or "0xc0000034" in error_msg:
                raise Exception("SERVICE_ERROR|Erro ao criar/gerenciar serviço remoto - pode precisar de permissões elevadas|service")
            elif "timed out" in error_msg.lower() or "timeout" in error_msg.lower():
                raise Exception("TIMEOUT|Conexão expirou (timeout)|timeout")
            elif "connection" in error_msg.lower() and "refused" in error_msg.lower():
                raise Exception("CONNECTION_REFUSED|Conexão recusada pelo servidor|connection")
            else:
                raise Exception(f"PSEXEC_ERROR|{error_msg}|psexec")
                
        except Exception as e:
            error_msg = str(e)
            # If already structured, re-raise
            if "|" in error_msg and error_msg.count("|") >= 2:
                raise
            await self.log(f"❌ Erro ao conectar via pypsexec: {error_msg}", "error")
            raise Exception(f"CONNECTION_ERROR|{error_msg}|connection")

    async def disconnect(self):
        """Disconnect pypsexec client"""
        if self.client:
            try:
                await asyncio.to_thread(self.client.disconnect)
                await self.log("🔌 pypsexec desconectado", "debug")
            except:
                pass
            self.client = None

    async def execute_command(self, command: str, powershell: bool = False) -> Tuple[int, str, str]:
        """Execute remote command via pypsexec"""
        try:
            # 🔧 Preparar username com domínio (mesmo código do connect)
            username_to_use = self.username
            if "\\" not in username_to_use and "@" not in username_to_use and self.domain:
                username_to_use = f"{self.domain}\\{self.username}"
            
            def _exec():
                if Client is None:
                    raise RuntimeError("pypsexec client is unavailable")
                client = Client(
                    self.host,
                    username=username_to_use,
                    password=self.password,
                    port=445,
                    encrypt=False  # Manter consistência com a verificação de conexão
                )
                try:
                    client.connect()

                    try:
                        client.cleanup()
                    except Exception as cleanup_err:
                        logger.warning(f"[psexec] Falha ao executar cleanup inicial: {cleanup_err}")

                    client.create_service()

                    if powershell:
                        stdout, stderr, rc = client.run_executable(
                            "powershell.exe",
                            arguments=f'-ExecutionPolicy Bypass -NoProfile -Command "{command}"'
                        )
                    else:
                        stdout, stderr, rc = client.run_executable(
                            "cmd.exe",
                            arguments=f'/c {command}'
                        )

                    try:
                        client.remove_service()
                    except Exception as remove_err:
                        logger.warning(f"[psexec] Falha ao remover serviço temporário: {remove_err}")
                        try:
                            client.cleanup()
                        except Exception as cleanup_err:
                            logger.warning(f"[psexec] Cleanup após remoção falhou: {cleanup_err}")

                    client.disconnect()

                    stdout_str = stdout.decode('utf-8') if isinstance(stdout, bytes) else (stdout or "")
                    stderr_str = stderr.decode('utf-8') if isinstance(stderr, bytes) else (stderr or "")

                    return rc, stdout_str, stderr_str
                except Exception as e:
                    try:
                        client.cleanup()
                    except Exception as cleanup_err:
                        logger.warning(f"[psexec] Cleanup em exceção falhou: {cleanup_err}")
                    try:
                        client.disconnect()
                    except:
                        pass
                    raise e

            return await asyncio.to_thread(_exec)

        except Exception as e:
            return 1, "", str(e)

    async def detect_os(self) -> Optional[str]:
        """Detect operating system with multiple fallback methods"""
        await self.log("🔍 Detectando sistema operacional...", "info")

        # Método 1: Tentar via PowerShell (mais confiável)
        await self.log("📋 Tentando detectar via PowerShell (Win32_OperatingSystem)...", "info")
        exit_code, output, error = await self.execute_command(
            "(Get-WmiObject -Class Win32_OperatingSystem).Caption",
            powershell=True
        )
        
        if exit_code == 0 and output and 'Windows' in output:
            self.os_type = 'windows'
            self.os_details['version'] = output.strip()
            self.os_details['name'] = output.strip()
            await self.log(f"✅ Windows detectado: {output.strip()}", "info")
            return 'windows'
        
        # Método 2: Tentar via comando 'ver'
        await self.log("📋 Tentando detectar via comando 'ver'...", "info")
        exit_code, output, error = await self.execute_command("ver", powershell=False)
        
        if exit_code == 0 and output and 'Windows' in output:
            self.os_type = 'windows'
            self.os_details['name'] = output.strip()
            self.os_details['version'] = output.strip()
            await self.log(f"✅ Windows detectado: {output.strip()}", "info")
            return 'windows'
        
        # Método 3: Tentar via systeminfo
        await self.log("📋 Tentando detectar via 'systeminfo'...", "info")
        exit_code, output, error = await self.execute_command(
            "systeminfo | findstr /B /C:\"OS Name\"",
            powershell=False
        )
        
        if exit_code == 0 and output and 'Windows' in output:
            self.os_type = 'windows'
            self.os_details['name'] = output.strip()
            self.os_details['version'] = output.strip()
            await self.log(f"✅ Windows detectado: {output.strip()}", "info")
            return 'windows'
        
        # Método 4: Assumir Windows se chegou até aqui (estamos usando pypsexec que é Windows-only)
        await self.log("⚠️ Não foi possível detectar versão específica, mas assumindo Windows (conexão SMB funcionou)", "warning")
        self.os_type = 'windows'
        self.os_details['name'] = 'Windows (versão não detectada)'
        self.os_details['version'] = 'Unknown'
        return 'windows'

    async def check_disk_space(self, required_mb: int = 200) -> bool:
        """Check available disk space"""
        await self.log("Verificando espaço em disco...", "info")

        command = "(Get-PSDrive C | Select-Object -ExpandProperty Free) / 1MB"
        exit_code, output, _ = await self.execute_command(command, powershell=True)

        if exit_code == 0:
            try:
                available_mb = int(float(output.strip()))
                if available_mb < required_mb:
                    await self.log(f"Espaço insuficiente: {available_mb}MB disponível", "error")
                    return False
                await self.log(f"Espaço suficiente: {available_mb}MB disponível", "success")
                return True
            except:
                pass

        await self.log("Não foi possível verificar espaço em disco", "warning")
        return True

    async def check_exporter_installed(self) -> bool:
        """Check if Windows Exporter is installed"""
        await self.log("Verificando instalação existente...", "info")

        port = 9182
        port_in_use = await asyncio.to_thread(test_port, self.host, port, 2)

        command = '(Get-Service -Name "windows_exporter" -ErrorAction SilentlyContinue).Status'
        exit_code, output, _ = await self.execute_command(command, powershell=True)
        service_running = exit_code == 0 and 'Running' in output

        if port_in_use or service_running:
            await self.log("windows_exporter já está instalado e rodando", "warning")
            return True

        await self.log("Nenhuma instalação anterior detectada", "success")
        return False

    async def install_exporter(self, collector_profile: str = 'recommended') -> bool:
        """Install Windows Exporter"""
        await self.log("=== Instalando Windows Exporter via PSexec ===", "info")

        # Get latest version
        try:
            await self.log("Obtendo última versão do GitHub...", "info")

            def get_version():
                response = requests.get(
                    "https://api.github.com/repos/prometheus-community/windows_exporter/releases/latest",
                    timeout=10
                )
                return response.json()['tag_name'].lstrip('v')

            version = await asyncio.to_thread(get_version)
            await self.log(f"Versão: {version}", "success")
        except Exception as e:
            await self.log(f"Erro ao obter versão: {e}", "error")
            return False

        # Prepare collectors
        collectors = WINDOWS_EXPORTER_COLLECTORS.get(collector_profile, WINDOWS_EXPORTER_COLLECTORS['recommended'])
        collectors_str = ','.join(collectors)

        url = f"https://github.com/prometheus-community/windows_exporter/releases/download/v{version}/windows_exporter-{version}-amd64.msi"

        # PowerShell installation script
        install_script = f'''
$ErrorActionPreference = "Stop"
$url = "{url}"
$installer = "$env:TEMP\\windows_exporter.msi"
$collectors = "{collectors_str}"

Write-Host "Baixando Windows Exporter v{version}..."
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
Invoke-WebRequest -Uri $url -OutFile $installer -UseBasicParsing

Write-Host "Instalando..."
Stop-Service -Name "windows_exporter" -ErrorAction SilentlyContinue
$arguments = "/i `"$installer`" ENABLED_COLLECTORS=$collectors /quiet /norestart"
Start-Process msiexec.exe -ArgumentList $arguments -Wait -NoNewWindow

Start-Sleep -Seconds 5

$service = Get-Service -Name "windows_exporter" -ErrorAction SilentlyContinue
if ($service -and $service.Status -eq "Running") {{
    Write-Host "SUCCESS"
}} else {{
    Write-Host "FAILED"
    exit 1
}}

Remove-Item $installer -Force -ErrorAction SilentlyContinue
'''

        await self.progress(30, 100, "Executando instalação remota...")
        await self.progress(40, 100, "Baixando Windows Exporter no host remoto...")

        exit_code, output, error = await self.execute_command(install_script, powershell=True)
        await self.progress(90, 100, "Finalizando...")

        if exit_code == 0 and 'SUCCESS' in output:
            await self.log(f"Windows Exporter v{version} instalado com sucesso!", "success")
            return True
        else:
            await self.log("Instalação falhou", "error")
            await self.log(f"Output: {output[:500]}", "debug")
            await self.log(f"Error: {error[:500]}", "debug")
            return False

    async def validate_installation(self) -> bool:
        """Validate installation"""
        await self.log("Validando instalação...", "info")

        # Check service
        command = '(Get-Service -Name "windows_exporter").Status'
        exit_code, output, _ = await self.execute_command(command, powershell=True)

        if exit_code == 0 and 'Running' in output:
            await self.log("Serviço windows_exporter está rodando", "success")
        else:
            await self.log("Serviço windows_exporter não está ativo", "error")
            return False

        # Test port
        port_open = await asyncio.to_thread(test_port, self.host, 9182, 3)
        if port_open:
            await self.log("Porta 9182 acessível", "success")
        else:
            await self.log("Porta 9182 não acessível (verifique firewall)", "warning")

        await self.log("Instalação validada com sucesso!", "success")
        return True

    async def get_system_info(self) -> Dict[str, str]:
        """Get system information"""
        info = await super().get_system_info()

        exit_code, hostname, _ = await self.execute_command("echo %COMPUTERNAME%", powershell=False)
        if exit_code == 0:
            info["hostname"] = hostname.strip()

        return info
