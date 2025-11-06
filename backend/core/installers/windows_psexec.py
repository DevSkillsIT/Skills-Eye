"""
Windows Exporter installer via PSexec
Uses pypsexec library for pure Python implementation
No need for PSExec.exe executable
"""
import asyncio
import base64
import socket
import logging
import requests
from typing import Tuple, Optional, Dict
from pathlib import Path
from textwrap import dedent
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
    'recommended': ['cpu', 'logical_disk', 'memory', 'net', 'os', 'physical_disk', 'service', 'system'],
    'full': ['cpu', 'logical_disk', 'memory', 'net', 'os', 'physical_disk', 'service', 'system', 'tcp', 'thermalzone'],
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
            await self.log(f"❌ Falha na resolução DNS: {e}", "error")
            return False, f"DNS_ERROR|Não foi possível resolver o hostname {self.host}|network"

        except socket.timeout as e:
            await self.log(f"❌ Timeout: {e}", "error")
            return False, f"TIMEOUT|Host {self.host} não respondeu (offline ou rede inacessível)|network"

        except Exception as e:
            await self.log(f"❌ Erro de rede: {e}", "error")
            return False, f"NETWORK_ERROR|Erro de conectividade: {e}|network"

        await self.log("✅ pypsexec disponível e host acessível", "success")
        return True, "OK"

    async def connect(self) -> bool:
        """Establish connection via pypsexec"""
        try:
            await self.log("🔌 Testando conexão pypsexec...", "info")

            username_to_use = self.username
            if "\\" not in username_to_use and "@" not in username_to_use and self.domain:
                username_to_use = f"{self.domain}\\{self.username}"
                await self.log(f"🔑 Usando credenciais de domínio: {username_to_use}", "info")
            else:
                await self.log(f"🔑 Usando credenciais: {username_to_use}", "info")

            def _connect():
                if Client is None:
                    raise RuntimeError("pypsexec client is unavailable")
                
                logs = []  # Capturar logs para enviar depois
                
                client = Client(
                    self.host,
                    username=username_to_use,
                    password=self.password,
                    port=445,
                    encrypt=False
                )
                try:
                    logs.append(("info", "[psexec] Iniciando conexão SMB..."))
                    client.connect()
                    logs.append(("success", "[psexec] ✅ Conexão SMB estabelecida"))

                    try:
                        logs.append(("info", "[psexec] Executando cleanup inicial..."))
                        client.cleanup()
                        logs.append(("success", "[psexec] ✅ Cleanup inicial OK"))
                    except Exception as cleanup_err:
                        logs.append(("warning", f"[psexec] ⚠️ Cleanup inicial falhou: {cleanup_err}"))

                    logs.append(("info", "[psexec] Criando serviço temporário PAExec..."))
                    client.create_service()
                    logs.append(("success", "[psexec] ✅ Serviço PAExec criado"))
                    
                    logs.append(("info", "[psexec] Executando comando de teste..."))
                    stdout, stderr, rc = client.run_executable(
                        "cmd.exe",
                        arguments="/c echo Connected"
                    )
                    logs.append(("info", f"[psexec] Comando retornou: rc={rc}"))

                    try:
                        logs.append(("info", "[psexec] Removendo serviço PAExec..."))
                        client.remove_service()
                        logs.append(("success", "[psexec] ✅ Serviço removido com sucesso"))
                    except Exception as remove_err:
                        error_type = type(remove_err).__name__
                        error_msg = str(remove_err)
                        logs.append(("error", "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"))
                        logs.append(("error", "[psexec] ❌ FALHA AO REMOVER SERVIÇO PAExec"))
                        logs.append(("error", "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"))
                        logs.append(("error", f"[psexec] Tipo da exceção: {error_type}"))
                        logs.append(("error", f"[psexec] Mensagem: {error_msg}"))
                        
                        # Extrair detalhes completos da exceção
                        if hasattr(remove_err, 'args') and remove_err.args:
                            for i, arg in enumerate(remove_err.args):
                                logs.append(("error", f"[psexec] Exception.args[{i}]: {arg}"))
                        
                        # Atributos específicos do pypsexec
                        if hasattr(remove_err, '__dict__'):
                            logs.append(("error", "[psexec] Atributos da exceção:"))
                            for key, value in remove_err.__dict__.items():
                                logs.append(("error", f"[psexec]   {key} = {value}"))
                        
                        # Se for SCMRException, tem mais detalhes
                        if 'SCMR' in error_type or hasattr(remove_err, 'error_id'):
                            if hasattr(remove_err, 'error_id'):
                                logs.append(("error", f"[psexec] SCMR Error ID: {getattr(remove_err, 'error_id', 'N/A')}"))
                            if hasattr(remove_err, 'error_msg'):
                                logs.append(("error", f"[psexec] SCMR Error Message: {getattr(remove_err, 'error_msg', 'N/A')}"))
                        
                        logs.append(("error", "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"))
                        
                        try:
                            logs.append(("info", "[psexec] Tentando cleanup após falha de remoção..."))
                            client.cleanup()
                            logs.append(("success", "[psexec] ✅ Cleanup executado com sucesso"))
                        except Exception as cleanup_err:
                            cleanup_type = type(cleanup_err).__name__
                            cleanup_msg = str(cleanup_err)
                            logs.append(("error", "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"))
                            logs.append(("error", "[psexec] ❌ CLEANUP TAMBÉM FALHOU"))
                            logs.append(("error", "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"))
                            logs.append(("error", f"[psexec] Tipo: {cleanup_type}"))
                            logs.append(("error", f"[psexec] Mensagem: {cleanup_msg}"))
                            
                            if hasattr(cleanup_err, 'args') and cleanup_err.args:
                                for i, arg in enumerate(cleanup_err.args):
                                    logs.append(("error", f"[psexec] Exception.args[{i}]: {arg}"))
                            
                            logs.append(("error", "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"))

                    logs.append(("info", "[psexec] Desconectando..."))
                    client.disconnect()
                    logs.append(("success", "[psexec] ✅ Desconectado"))
                    
                    return rc == 0, stdout, stderr, logs
                except Exception as e:
                    logs.append(("error", f"[psexec] ❌ Exceção durante conexão: {e}"))
                    try:
                        logs.append(("info", "[psexec] Tentando cleanup em exceção..."))
                        client.cleanup()
                        logs.append(("success", "[psexec] ✅ Cleanup em exceção OK"))
                    except Exception as cleanup_err:
                        logs.append(("error", f"[psexec] ❌ Cleanup em exceção falhou: {cleanup_err}"))
                    try:
                        client.disconnect()
                    except Exception:
                        pass
                    raise e

            success, stdout, stderr, logs = await asyncio.to_thread(_connect)
            
            # Enviar todos os logs capturados
            for level, message in logs:
                await self.log(message, level)

            if success:
                await self.log("✅ Conexão pypsexec bem-sucedida", "success")
                return True

            await self.log(f"❌ Falha na conexão pypsexec: {stderr}", "error")
            raise Exception(f"CONNECTION_FAILED|Falha ao executar comando teste: {stderr}|connection")

        except PypsexecException as e:
            error_msg = str(e)
            await self.log(f"❌ Erro pypsexec: {error_msg}", "error")

            if "STATUS_LOGON_FAILURE" in error_msg or "0xc000006d" in error_msg:
                raise Exception("AUTH_FAILED|Usuário ou senha inválidos|authentication")
            if "STATUS_LOGON_TYPE_NOT_GRANTED" in error_msg or "0xc0000192" in error_msg:
                raise Exception("PERMISSION_DENIED|Usuário não tem permissão de logon remoto neste computador. Adicione o usuário ao grupo 'Administradores' ou 'Usuários da Área de Trabalho Remota'|authentication")
            if "STATUS_ACCOUNT_RESTRICTION" in error_msg or "0xc000006e" in error_msg:
                raise Exception("AUTH_FAILED|Conta com restrições - verifique se é administrador local|authentication")
            if "STATUS_ACCESS_DENIED" in error_msg or "Access is denied" in error_msg or "0xc0000022" in error_msg:
                raise Exception("PERMISSION_DENIED|Acesso negado - credenciais sem permissões administrativas|authentication")
            if "STATUS_CANNOT_DELETE" in error_msg or "0xc0000121" in error_msg:
                raise Exception("PERMISSION_DENIED|Erro de permissão ao gerenciar serviço - verifique se o usuário é administrador local|authentication")
            if "STATUS_OBJECT_NAME_NOT_FOUND" in error_msg or "0xc0000034" in error_msg:
                raise Exception("SERVICE_ERROR|Erro ao criar/gerenciar serviço remoto - pode precisar de permissões elevadas|service")
            if "timed out" in error_msg.lower() or "timeout" in error_msg.lower():
                raise Exception("TIMEOUT|Conexão expirou (timeout)|timeout")
            if "connection" in error_msg.lower() and "refused" in error_msg.lower():
                raise Exception("CONNECTION_REFUSED|Conexão recusada pelo servidor|connection")

            raise Exception(f"PSEXEC_ERROR|{error_msg}|psexec")

        except Exception as e:
            error_msg = str(e)
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
                
                logs = []  # Capturar logs
                
                client = Client(
                    self.host,
                    username=username_to_use,
                    password=self.password,
                    port=445,
                    encrypt=False  # Manter consistência com a verificação de conexão
                )
                try:
                    logs.append(("info", "[psexec] Conectando para executar comando..."))
                    client.connect()
                    logs.append(("success", "[psexec] ✅ Conectado"))

                    try:
                        logs.append(("info", "[psexec] Cleanup inicial..."))
                        client.cleanup()
                        logs.append(("success", "[psexec] ✅ Cleanup OK"))
                    except Exception as cleanup_err:
                        logs.append(("warning", f"[psexec] ⚠️ Cleanup falhou: {cleanup_err}"))

                    logs.append(("info", "[psexec] Criando serviço PAExec..."))
                    client.create_service()
                    logs.append(("success", "[psexec] ✅ Serviço criado"))

                    if powershell:
                        logs.append(("info", f"[psexec] Executando PowerShell (encoded): {command[:100]}..."))
                        encoded = base64.b64encode(command.encode("utf-16le")).decode()
                        stdout, stderr, rc = client.run_executable(
                            "powershell.exe",
                            arguments=f'-NoProfile -ExecutionPolicy Bypass -EncodedCommand {encoded}'
                        )
                    else:
                        logs.append(("info", f"[psexec] Executando CMD: {command[:100]}..."))
                        stdout, stderr, rc = client.run_executable(
                            "cmd.exe",
                            arguments=f'/c {command}'
                        )
                    
                    logs.append(("info", f"[psexec] Comando retornou rc={rc}"))

                    try:
                        logs.append(("info", "[psexec] Removendo serviço PAExec..."))
                        client.remove_service()
                        logs.append(("success", "[psexec] ✅ Serviço removido"))
                    except Exception as remove_err:
                        logs.append(("error", f"[psexec] ❌ Falha ao remover serviço: {remove_err}"))
                        try:
                            logs.append(("info", "[psexec] Tentando cleanup..."))
                            client.cleanup()
                            logs.append(("success", "[psexec] ✅ Cleanup OK"))
                        except Exception as cleanup_err:
                            logs.append(("error", f"[psexec] ❌ Cleanup falhou: {cleanup_err}"))

                    logs.append(("info", "[psexec] Desconectando..."))
                    client.disconnect()
                    logs.append(("success", "[psexec] ✅ Desconectado"))

                    # Decodificar com fallback para evitar erros de encoding
                    stdout_str = stdout.decode('utf-8', errors='replace') if isinstance(stdout, bytes) else (stdout or "")
                    stderr_str = stderr.decode('utf-8', errors='replace') if isinstance(stderr, bytes) else (stderr or "")

                    return rc, stdout_str, stderr_str, logs
                except Exception as e:
                    logs.append(("error", f"[psexec] ❌ Exceção: {e}"))
                    try:
                        logs.append(("info", "[psexec] Cleanup em exceção..."))
                        client.cleanup()
                        logs.append(("success", "[psexec] ✅ Cleanup OK"))
                    except Exception as cleanup_err:
                        logs.append(("error", f"[psexec] ❌ Cleanup falhou: {cleanup_err}"))
                    try:
                        client.disconnect()
                    except:
                        pass
                    raise e

            rc, stdout_str, stderr_str, logs = await asyncio.to_thread(_exec)
            
            # Enviar logs capturados
            for level, message in logs:
                await self.log(message, level)
            
            return rc, stdout_str, stderr_str

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

    async def install_exporter(self, collector_profile: str = 'recommended', basic_auth_user: Optional[str] = None, basic_auth_password: Optional[str] = None) -> bool:
        """Install Windows Exporter with optional Basic Auth"""
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
            detail = str(e)
            raise Exception(
                f"DOWNLOAD_FAILED|Não foi possível consultar a versão mais recente do windows_exporter no GitHub."
                " Verifique acesso HTTPS/Proxy a github.com.|network|"
                f"{detail[:500]}"
            )

        # Prepare collectors
        collectors = WINDOWS_EXPORTER_COLLECTORS.get(collector_profile, WINDOWS_EXPORTER_COLLECTORS['recommended'])
        collectors_str = ','.join(collectors)
        
        # Generate bcrypt hash for password if Basic Auth is enabled
        bcrypt_hash = ""
        await self.log(f"🔍 DEBUG: basic_auth_user={basic_auth_user}, basic_auth_password={'***' if basic_auth_password else 'None'}", "info")
        if basic_auth_user and basic_auth_password:
            await self.log(f"🔐 Basic Auth HABILITADO para usuário: {basic_auth_user}", "info")
            try:
                import bcrypt
                await self.log("📦 Módulo bcrypt importado com sucesso", "info")
                password_bytes = basic_auth_password.encode('utf-8')
                await self.log("🔄 Gerando salt bcrypt...", "info")
                salt = bcrypt.gensalt(rounds=10)
                await self.log("🔄 Gerando hash bcrypt...", "info")
                hash_bytes = bcrypt.hashpw(password_bytes, salt)
                bcrypt_hash = hash_bytes.decode('utf-8')
                await self.log(f"✅ Hash bcrypt gerado com sucesso (length={len(bcrypt_hash)})", "success")
                await self.log(f"🔍 DEBUG: bcrypt_hash[:20]={bcrypt_hash[:20]}...", "info")
            except ImportError as e:
                await self.log(f"❌ Módulo bcrypt não disponível - Basic Auth não será configurado: {e}", "error")
                self._raise_install_error(
                    "BCRYPT_MISSING",
                    "Módulo bcrypt não está instalado. Execute: pip install bcrypt",
                    "dependency",
                    "",
                    ""
                )
            except Exception as e:
                await self.log(f"❌ Erro ao gerar hash bcrypt: {e}", "error")
                self._raise_install_error(
                    "BCRYPT_HASH_FAILED",
                    f"Falha ao gerar hash bcrypt: {str(e)}",
                    "configuration",
                    "",
                    str(e)
                )
        else:
            await self.log("ℹ️ Basic Auth NÃO habilitado (usuário ou senha não fornecidos)", "info")

        # ============================================================================
        # CONFIGURAR BASIC AUTH **ANTES** DE INSTALAR O MSI!
        # ============================================================================
        if bcrypt_hash:
            await self.log("🔐 CONFIGURANDO BASIC AUTH ANTES DA INSTALAÇÃO DO MSI", "info")
            await self.progress(25, 100, "Configurando Basic Auth...")
            
            try:
                # Criar config.yaml com Basic Auth
                config_content = f"""# Windows Exporter - Basic Authentication Configuration
# Generated by Consul Manager Web
# Date: {__import__('datetime').datetime.now().isoformat()}

basic_auth_users:
  {basic_auth_user}: {bcrypt_hash}
"""
                
                await self.log("📝 Criando arquivo config.yaml...", "info")
                
                # Codificar em Base64 para evitar problemas com caracteres especiais no PowerShell
                import base64
                config_base64 = base64.b64encode(config_content.encode('utf-8')).decode('ascii')
                
                create_config_cmd = (
                    "$ErrorActionPreference = 'Stop';"
                    "$installDir = 'C:\\Program Files\\windows_exporter';"
                    "if (-not (Test-Path $installDir)) { New-Item -ItemType Directory -Path $installDir -Force | Out-Null; };"
                    "$configPath = Join-Path $installDir 'config.yaml';"
                    f"$configBase64 = '{config_base64}';"
                    "$configContent = [System.Text.Encoding]::UTF8.GetString([System.Convert]::FromBase64String($configBase64));"
                    "[System.IO.File]::WriteAllText($configPath, $configContent, [System.Text.Encoding]::UTF8);"
                    "Write-Host \"CONFIG_CREATED:$configPath\";"
                    "Write-Host \"CONFIG_SIZE:$((Get-Item $configPath).Length)\";"
                    "$preview = Get-Content $configPath -Head 3 | Out-String;"
                    "Write-Host \"CONFIG_PREVIEW:$preview\";"
                )
                
                exit_code, output, error = await self.execute_command(create_config_cmd, powershell=True)
                if output:
                    for line in output.splitlines():
                        await self.log(f"  {line}", "info")
                
                if exit_code != 0:
                    await self.log("❌ Falha ao criar config.yaml", "error")
                    self._raise_install_error(
                        "CONFIG_CREATE_FAILED",
                        "Não foi possível criar o arquivo de configuração do Basic Auth",
                        "configuration",
                        output,
                        error
                    )
                
                await self.log("✅ config.yaml criado com sucesso", "success")
                
            except Exception as e:
                await self.log(f"❌ Erro ao configurar Basic Auth: {e}", "error")
                self._raise_install_error(
                    "BASIC_AUTH_CONFIG_FAILED",
                    f"Falha ao configurar Basic Auth: {str(e)}",
                    "configuration",
                    "",
                    str(e)
                )

        url = f"https://github.com/prometheus-community/windows_exporter/releases/download/v{version}/windows_exporter-{version}-amd64.msi"

        # DEBUG: Antes do download
        await self.log("🔍 [DEBUG] Antes do download - URL preparada", "info")

        # Etapa 1 - Download do instalador
        await self.log("Baixando instalador do windows_exporter...", "info")
        download_cmd = (
            "$ErrorActionPreference = 'Stop';"
            f"$url = '{url}';"
            "$installer = Join-Path $env:TEMP 'windows_exporter.msi';"
            "[System.Net.ServicePointManager]::SecurityProtocol = [System.Net.SecurityProtocolType]::Tls12;"
            "Write-Host 'DOWNLOAD_START';"
            "Write-Host ('DOWNLOAD_URL:' + $url);"
            "Write-Host ('DOWNLOAD_DEST:' + $installer);"
            "Invoke-WebRequest -Uri $url -OutFile $installer -UseBasicParsing;"
            "Write-Host ('DOWNLOAD_OK_BYTES:' + (Get-Item $installer).Length);"
        )

        exit_code, output, error = await self.execute_command(download_cmd, powershell=True)
        if output:
            for line in output.splitlines():
                await self.log(f"[download] {line}", "info")
        if exit_code != 0:
            await self.log("Falha ao baixar o instalador", "error")
            self._raise_install_error(
                "DOWNLOAD_FAILED",
                "Falha ao baixar o instalador do windows_exporter. Verifique conectividade HTTPS.",
                "network",
                output,
                error
            )
        await self.log("Instalador baixado com sucesso em %TEMP%\\windows_exporter.msi", "info")

        # DEBUG: Após download, antes da instalação
        await self.log("🔍 [DEBUG] Download concluído, iniciando instalação", "info")

        await self.progress(30, 100, "Executando instalação/atualização...")

        # DEBUG: Confirmar que chegou na etapa 2
        await self.log("🔍 [DEBUG] Iniciando etapa 2 - verificação de instalação existente", "info")

        # Etapa 2 - Verificar instalação existente e decidir estratégia
        await self.log("Verificando instalação existente do windows_exporter...", "info")
        
        check_installed_cmd = (
            "$ErrorActionPreference = 'Stop';"
            "Write-Host 'CHECK_INSTALLED_START';"
            "$productCode = '{13C1979E-FEE4-4895-A029-B7814AAA1E0E}';"  # Windows Exporter MSI Product Code
            "$installed = Get-WmiObject -Class Win32_Product -Filter \"IdentifyingNumber='$productCode'\" -ErrorAction SilentlyContinue;"
            "if ($installed) {"
            "    Write-Host \"PRODUCT_INSTALLED: $($installed.Name) v$($installed.Version)\";"
            f"    $currentVersion = '{version}';"
            "    if ([version]$installed.Version -lt [version]$currentVersion) {"
            "        Write-Host 'STRATEGY: UNINSTALL_THEN_INSTALL';"
            "        Write-Host \"VERSION_COMPARISON: $($installed.Version) < $currentVersion\";"
            "    } elseif ([version]$installed.Version -eq [version]$currentVersion) {"
            "        Write-Host 'STRATEGY: MODIFY_EXISTING';"
            "        Write-Host \"VERSION_COMPARISON: $($installed.Version) = $currentVersion\";"
            "    } else {"
            "        Write-Host 'STRATEGY: DOWNGRADE_EXISTING';"
            "        Write-Host \"VERSION_COMPARISON: $($installed.Version) > $currentVersion\";"
            "    };"
            "} else {"
            "    Write-Host 'PRODUCT_NOT_INSTALLED';"
            "    Write-Host 'STRATEGY: FRESH_INSTALL';"
            "};"
        )
        
        exit_code, output, error = await self.execute_command(check_installed_cmd, powershell=True)
        
        strategy = "FRESH_INSTALL"
        current_installed_version = None
        
        if output:
            for line in output.splitlines():
                if "PRODUCT_INSTALLED:" in line:
                    await self.log(f"✅ {line}", "info")
                    # Extrair versão do log
                    version_match = line.split("v")[-1] if "v" in line else None
                    if version_match:
                        current_installed_version = version_match
                elif "PRODUCT_NOT_INSTALLED" in line:
                    await self.log("ℹ️ Produto não instalado - fará instalação completa", "info")
                elif "STRATEGY:" in line:
                    strategy = line.split(":")[1]
                    await self.log(f"📋 Estratégia: {strategy}", "info")
                elif "VERSION_COMPARISON:" in line:
                    await self.log(f"🔄 {line}", "info")
        
        # Etapa 3 - Executar estratégia apropriada
        if strategy == "UNINSTALL_THEN_INSTALL":
            await self.log("🔄 Desinstalando versão antiga antes de instalar nova...", "info")
            
            uninstall_cmd = (
                "$ErrorActionPreference = 'Stop';"
                "Write-Host 'UNINSTALL_START';"
                "$productCode = '{13C1979E-FEE4-4895-A029-B7814AAA1E0E}';"
                "$uninstallLog = Join-Path $env:TEMP 'windows_exporter_uninstall.log';"
                "$arguments = @('/x', $productCode, '/quiet', '/norestart', '/log', $uninstallLog);"
                "Write-Host \"MSIEXEC_CMD: msiexec.exe $arguments\";"
                "$process = Start-Process msiexec.exe -ArgumentList $arguments -PassThru -Wait -NoNewWindow;"
                "$exitCode = $process.ExitCode;"
                "Write-Host \"MSIEXEC_EXITCODE:$exitCode\";"
                "if ($exitCode -eq 0) { Write-Host 'UNINSTALL_SUCCESS'; }"
                "elseif ($exitCode -eq 1605) { Write-Host 'UNINSTALL_NOT_INSTALLED'; }"  # Produto não instalado
                "else { Write-Host \"UNINSTALL_FAILED:$exitCode\"; };"
                "if (Test-Path $uninstallLog) { Get-Content $uninstallLog -Tail 10 | ForEach-Object { Write-Host \"LOG: $_\" }; };"
                "exit $exitCode;"
            )
            
            exit_code, output, error = await self.execute_command(uninstall_cmd, powershell=True)
            
            if output:
                for line in output.splitlines():
                    if "UNINSTALL_SUCCESS" in line:
                        await self.log("✅ Desinstalação da versão antiga concluída", "success")
                    elif "UNINSTALL_NOT_INSTALLED" in line:
                        await self.log("ℹ️ Produto não estava instalado", "info")
                    elif "UNINSTALL_FAILED" in line:
                        await self.log(f"⚠️ Desinstalação falhou: {line}", "warning")
                    elif line.startswith("LOG:"):
                        await self.log(f"  {line}", "info")
                    elif "MSIEXEC_CMD" in line or "MSIEXEC_EXITCODE" in line:
                        await self.log(f"  {line}", "info")
            
            # Se desinstalação falhou mas produto não existe, continua
            if exit_code != 0 and "UNINSTALL_NOT_INSTALLED" not in (output or ""):
                await self.log("⚠️ Desinstalação falhou, tentando instalar mesmo assim", "warning")
        
        # Etapa 4 - Instalar/modificar conforme estratégia
        await self.log(f"Executando {'modificação' if strategy == 'MODIFY_EXISTING' else 'instalação'}...", "info")
        
        if strategy == "MODIFY_EXISTING":
            # Produto instalado com mesma versão - modificar propriedades
            install_cmd = (
                "$ErrorActionPreference = 'Stop';"
                "Write-Host 'MODIFY_START';"
                "$installer = Join-Path $env:TEMP 'windows_exporter.msi';"
                f"$collectors = '{collectors_str}';"
                "$logPath = Join-Path $env:TEMP 'windows_exporter_modify.log';"
                "if (-not (Test-Path $installer)) { Write-Host 'INSTALLER_NOT_FOUND'; exit 2 };"
                "$arguments = \"/c `\"$installer`\" ENABLED_COLLECTORS=$collectors /quiet /norestart /log `\"$logPath`\"\";"
                "Write-Host \"MSIEXEC_CMD: msiexec.exe $arguments\";"
                "$process = Start-Process msiexec.exe -ArgumentList $arguments -PassThru -Wait -NoNewWindow;"
                "$exitCode = $process.ExitCode;"
                "Write-Host \"MSIEXEC_EXITCODE:$exitCode\";"
                "if ($exitCode -eq 0) { Write-Host 'MODIFY_SUCCESS'; }"
                "elseif ($exitCode -eq 1603) { Write-Host 'MODIFY_FAILED_1603'; }"
                "elseif ($exitCode -eq 1618) { Write-Host 'MODIFY_IN_PROGRESS'; }"
                "else { Write-Host \"MODIFY_FAILED:$exitCode\"; };"
                "if (Test-Path $logPath) { Get-Content $logPath -Tail 15 | ForEach-Object { Write-Host \"LOG: $_\" }; };"
                "exit $exitCode;"
            )
        else:
            # Instalação nova ou após desinstalação
            install_cmd = (
                "$ErrorActionPreference = 'Stop';"
                "Write-Host 'INSTALL_START';"
                "$installer = Join-Path $env:TEMP 'windows_exporter.msi';"
                f"$collectors = '{collectors_str}';"
                "$logPath = Join-Path $env:TEMP 'windows_exporter_install.log';"
                "if (-not (Test-Path $installer)) { Write-Host 'INSTALLER_NOT_FOUND'; exit 2 };"
                "$arguments = \"/i `\"$installer`\" ENABLED_COLLECTORS=$collectors /quiet /norestart /log `\"$logPath`\"\";"
                "Write-Host \"MSIEXEC_CMD: msiexec.exe $arguments\";"
                "$process = Start-Process msiexec.exe -ArgumentList $arguments -PassThru -Wait -NoNewWindow;"
                "$exitCode = $process.ExitCode;"
                "Write-Host \"MSIEXEC_EXITCODE:$exitCode\";"
                "if ($exitCode -eq 0) { Write-Host 'INSTALL_SUCCESS'; }"
                "elseif ($exitCode -eq 1603) { Write-Host 'INSTALL_FAILED_1603'; }"
                "elseif ($exitCode -eq 1618) { Write-Host 'INSTALL_IN_PROGRESS'; }"
                "else { Write-Host \"INSTALL_FAILED:$exitCode\"; };"
                "if (Test-Path $logPath) { Get-Content $logPath -Tail 15 | ForEach-Object { Write-Host \"LOG: $_\" }; };"
                "exit $exitCode;"
            )

        exit_code, output, error = await self.execute_command(install_cmd, powershell=True)
        
        print(f"[DEBUG 1] execute_command retornou: exit_code={exit_code}, output_len={len(output) if output else 0}")
        await self.log(f"🔍 [DEBUG 1] execute_command retornou: exit_code={exit_code}, output_len={len(output) if output else 0}", "info")
        
        # Log instalação/modificação
        if output:
            print(f"[DEBUG 2] Processando {len(output.splitlines())} linhas de output")
            await self.log(f"🔍 [DEBUG 2] Processando {len(output.splitlines())} linhas de output", "info")
            for line in output.splitlines():
                if line.strip():
                    if "MODIFY_SUCCESS" in line or "INSTALL_SUCCESS" in line:
                        await self.log("✅ Windows Exporter instalado/modificado com sucesso", "success")
                    elif "MODIFY_FAILED" in line or "INSTALL_FAILED" in line or "MSIEXEC_EXITCODE:1603" in line:
                        await self.log(f"❌ {line}", "error")
                    elif line.startswith("LOG:"):
                        await self.log(f"  {line}", "info")
                    elif "MSIEXEC_CMD" in line or "MSIEXEC_EXITCODE" in line:
                        await self.log(f"  {line}", "info")
                    elif "PRODUCT_INSTALLED:" in line or "PRODUCT_NOT_INSTALLED" in line or "STRATEGY:" in line or "VERSION_COMPARISON:" in line:
                        await self.log(f"  {line}", "info")
        
        print(f"[DEBUG 3] Saiu do loop de output")
        await self.log(f"🔍 [DEBUG 3] Saiu do loop de output", "info")
        
        if error:
            print(f"[DEBUG 4] Processando error output")
            await self.log(f"🔍 [DEBUG 4] Processando error output", "info")
            try:
                error_lines = [l for l in error.splitlines() if l.strip() and not l.strip().startswith("#< CLIXML")]
                print(f"[DEBUG 4.5] Encontradas {len(error_lines)} linhas de erro")
                await self.log(f"🔍 [DEBUG 4.5] Encontradas {len(error_lines)} linhas de erro", "info")
                print(f"[DEBUG 4.6] Antes do loop de error_lines")
                if error_lines:
                    print(f"[DEBUG 4.7] Dentro do if error_lines (vai fazer loop)")
                    for idx, line in enumerate(error_lines):
                        print(f"[DEBUG 4.8.{idx}] Logando linha de erro")
                        await self.log(f"  [stderr] {line}", "warning")
                print(f"[DEBUG 4.9] Após processar error_lines")
            except Exception as e:
                print(f"[DEBUG 4.99] EXCEÇÃO ao processar stderr: {e}")
                await self.log(f"🔍 [DEBUG 4.99] EXCEÇÃO: {e}", "error")
        
        print(f"[DEBUG 5] Verificando exit_code: {exit_code}")
        await self.log(f"🔍 [DEBUG 5] Verificando exit_code: {exit_code}", "info")
        
        if exit_code != 0:
            print(f"[DEBUG 6] exit_code != 0, lançando erro")
            await self.log(f"🔍 [DEBUG 6] exit_code != 0, lançando erro", "error")
            await self.log(f"❌ MSI retornou código {exit_code}", "error")
            combined_text = "\n".join(part for part in [output, error] if part).strip()
            reason, error_code, error_category = self._classify_install_failure(combined_text)
            self._raise_install_error(error_code, reason, error_category, output, error)
        
        await self.log("✅ MSI instalado com sucesso", "success")

        # Etapa 3 - Modificar serviço Windows Exporter para usar config.yaml (se Basic Auth habilitado)
        if bcrypt_hash:
            await self.log("🔐 Modificando serviço para usar Basic Auth...", "info")
            await self.progress(70, 100, "Modificando serviço...")
            
            modify_service_cmd = (
                "$ErrorActionPreference = 'Stop';"
                "Write-Host 'SERVICE_MODIFY_START';"
                "$serviceName = 'windows_exporter';"
                "$service = Get-CimInstance -ClassName Win32_Service -Filter \"Name='$serviceName'\";"
                "if (-not $service) { Write-Host 'SERVICE_NOT_FOUND'; exit 1; };"
                "$currentPath = $service.PathName;"
                "Write-Host \"SERVICE_CURRENT_PATH:$currentPath\";"
                "if ($currentPath -match '^\"?([^\"]+\\.exe)\"?') {"
                "    $exePath = $Matches[1];"
                "} else {"
                "    Write-Host 'SERVICE_PATH_PARSE_ERROR'; exit 2;"
                "};"
                "Write-Host \"SERVICE_EXE_PATH:$exePath\";"
                f"$collectors = '{collectors_str}';"
                "$configPath = 'C:\\Program Files\\windows_exporter\\config.yaml';"
                "$newPath = \"`\"$exePath`\" --config.file=`\"$configPath`\" --collectors.enabled=$collectors\";"
                "Write-Host \"SERVICE_NEW_PATH:$newPath\";"
                "$scResult = sc.exe config $serviceName binPath= $newPath;"
                "Write-Host \"SC_RESULT:$scResult\";"
                "if ($LASTEXITCODE -eq 0) { Write-Host 'SERVICE_MODIFIED_OK'; } else { Write-Host 'SERVICE_MODIFY_FAILED'; exit 3; };"
            )
            
            exit_code, output, error = await self.execute_command(modify_service_cmd, powershell=True)
            
            if output:
                for line in output.splitlines():
                    await self.log(f"  {line}", "info")
            
            if exit_code != 0:
                await self.log("❌ Falha ao modificar serviço", "error")
            else:
                await self.log("✅ Serviço modificado com sucesso", "success")
            
            # Reiniciar serviço
            await self.log("🔄 Reiniciando serviço...", "info")
            restart_cmd = (
                "$ErrorActionPreference = 'Stop';"
                "Restart-Service -Name 'windows_exporter' -Force;"
                "Start-Sleep -Seconds 3;"
                "$status = (Get-Service -Name 'windows_exporter').Status;"
                "Write-Host \"SERVICE_STATUS:$status\";"
            )
            
            exit_code, output, error = await self.execute_command(restart_cmd, powershell=True)
            if "SERVICE_STATUS:Running" in (output or ""):
                await self.log("✅ Serviço reiniciado com sucesso", "success")
            else:
                await self.log("⚠️ Serviço pode não estar executando corretamente", "warning")
            
            # Validar Basic Auth
            await self.log("🔐 Validando Basic Auth...", "info")
            await asyncio.sleep(2)
            
            validate_cmd = (
                "$ErrorActionPreference = 'Stop';"
                "try {"
                "    $response = Invoke-WebRequest -Uri 'http://localhost:9182/metrics' -UseBasicParsing -ErrorAction Stop;"
                "    Write-Host 'AUTH_CHECK:NO_AUTH_200';"
                "} catch {"
                "    if ($_.Exception.Response.StatusCode -eq 401) {"
                "        Write-Host 'AUTH_CHECK:NO_AUTH_401_OK';"
                "    } else {"
                "        Write-Host 'AUTH_CHECK:NO_AUTH_ERROR';"
                "    }"
                "};"
                f"$pair = '{basic_auth_user}:{basic_auth_password}';"
                "$bytes = [System.Text.Encoding]::ASCII.GetBytes($pair);"
                "$base64 = [System.Convert]::ToBase64String($bytes);"
                "$headers = @{ Authorization = \"Basic $base64\" };"
                "try {"
                "    $response = Invoke-WebRequest -Uri 'http://localhost:9182/metrics' -Headers $headers -UseBasicParsing -ErrorAction Stop;"
                "    if ($response.StatusCode -eq 200) {"
                "        Write-Host 'AUTH_CHECK:WITH_AUTH_200_OK';"
                "    } else {"
                "        Write-Host 'AUTH_CHECK:WITH_AUTH_ERROR';"
                "    }"
                "} catch {"
                "    Write-Host 'AUTH_CHECK:WITH_AUTH_FAILED';"
                "};"
            )
            
            exit_code, output, error = await self.execute_command(validate_cmd, powershell=True)
            if output:
                if "NO_AUTH_401_OK" in output and "WITH_AUTH_200_OK" in output:
                    await self.log("✅ Basic Auth validado: 401 sem auth, 200 com auth", "success")
                else:
                    await self.log(f"⚠️ Validação parcial: {output[:100]}", "warning")

        await self.progress(80, 100, "Validando serviço windows_exporter...")

        # Etapa 4 - Validar serviço e limpar instalador temporário
        check_cmd = dedent(r"""
            Write-Host '=== PSEXEC_VALIDATION_BEGIN ==='
            
            $service = Get-Service -Name 'windows_exporter' -ErrorAction SilentlyContinue;
            if (-not $service) {
                Write-Host 'SERVICE_NOT_FOUND_AFTER_INSTALL';
                
                # Listar todos os serviços com 'exporter' no nome
                Write-Host 'LISTING_EXPORTER_SERVICES:'
                Get-Service | Where-Object { $_.Name -like '*exporter*' -or $_.DisplayName -like '*exporter*' } | 
                    ForEach-Object { Write-Host "  - $($_.Name): $($_.Status) ($($_.DisplayName))" }
                
                Write-Host 'CHECKING_EVENT_LOG:'
                $events = Get-WinEvent -LogName Application -MaxEvents 50 -ErrorAction SilentlyContinue |
                    Where-Object { $_.ProviderName -in @('windows_exporter','MsiInstaller','Service Control Manager') } |
                    Select-Object -First 10;
                foreach ($evt in $events) {
                    Write-Host "EVENT: Provider=$($evt.ProviderName), Level=$($evt.LevelDisplayName), Time=$($evt.TimeCreated.ToString('HH:mm:ss')), Message=$($evt.Message -replace '`r`n', ' ' | Select-Object -First 150)";
                }
                
                exit 1;
            }
            
            Write-Host "SERVICE_FOUND: Status=$($service.Status), DisplayName=$($service.DisplayName), StartType=$($service.StartType)"
            
            if ($service.Status -ne 'Running') {
                Write-Host "SERVICE_NOT_RUNNING: Status=$($service.Status)"
                try {
                    Write-Host 'SERVICE_START_ATTEMPT...'
                    Start-Service -Name 'windows_exporter' -ErrorAction Stop;
                    Start-Sleep -Seconds 3;
                    $service.Refresh();
                    Write-Host "SERVICE_START_RESULT: Status=$($service.Status)"
                } catch {
                    Write-Host "SERVICE_START_ERROR: $($_.Exception.Message)"
                }
            } else {
                Write-Host 'SERVICE_ALREADY_RUNNING: OK'
            }
            
            if ($service.Status -eq 'Running') {
                Write-Host 'SERVICE_RUNNING: OK'
            } else {
                Write-Host "SERVICE_FAILED: FinalStatus=$($service.Status)"
                
                Write-Host 'CHECKING_EVENT_LOG_FOR_ERRORS:'
                $events = Get-WinEvent -LogName Application -MaxEvents 50 -ErrorAction SilentlyContinue |
                    Where-Object { $_.ProviderName -in @('windows_exporter','MsiInstaller','Service Control Manager') } |
                    Select-Object -First 10;
                foreach ($evt in $events) {
                    Write-Host "EVENT: Provider=$($evt.ProviderName), Level=$($evt.LevelDisplayName), Time=$($evt.TimeCreated.ToString('HH:mm:ss')), Message=$($evt.Message -replace '`r`n', ' ' | Select-Object -First 150)";
                }
                
                exit 1;
            }
            
            Write-Host 'CLEANUP: Removing temporary MSI...'
            Remove-Item -Path (Join-Path $env:TEMP 'windows_exporter.msi') -Force -ErrorAction SilentlyContinue;
            
            Write-Host '=== PSEXEC_VALIDATION_END ==='
        """).strip()

        exit_code, output, error = await self.execute_command(check_cmd, powershell=True)
        
        # Log detalhado da validação
        if output:
            await self.log("=== VALIDAÇÃO DO SERVIÇO ===", "info")
            for line in output.splitlines():
                if line.strip():
                    level = "error" if "ERROR" in line.upper() or "FAIL" in line.upper() else "info"
                    await self.log(f"  {line}", level)
        if error:
            await self.log("=== ERROS DA VALIDAÇÃO ===", "error")
            for line in error.splitlines():
                if line.strip():
                    await self.log(f"  {line}", "error")
                    
        if exit_code != 0:
            await self.log("Serviço windows_exporter não iniciou após a instalação", "error")
            self._raise_install_error(
                "SERVICE_NOT_RUNNING",
                "Serviço windows_exporter não está ativo após a instalação. Verifique logs do Windows.",
                "service",
                output,
                error
            )

        await self.progress(90, 100, "Finalizando...")
        operation_type = "modificado" if strategy == "MODIFY_EXISTING" else "instalado"
        await self.log(f"Windows Exporter v{version} {operation_type} com sucesso!", "success")
        return True

    def _classify_install_failure(self, combined_text: str) -> Tuple[str, str, str]:
        """Provide user-friendly reason, code and category for installation failures"""
        if not combined_text:
            return (
                "Instalação do windows_exporter falhou sem detalhes retornados."
                " Verifique logs no servidor e permissões do usuário.",
                "INSTALLATION_FAILED",
                "installer"
            )

        text_lower = combined_text.lower()

        if "invoke-webrequest" in text_lower:
            if any(phrase in text_lower for phrase in ["unable to connect", "could not connect", "não foi possível estabelecer", "unable to resolve", "could not be resolved", "tempo esgotado"]):
                return (
                    "Falha ao baixar o instalador do windows_exporter (Invoke-WebRequest)."
                    " Verifique acesso HTTPS à internet/Proxy para github.com.",
                    "DOWNLOAD_FAILED",
                    "network"
                )
            if "could not create ssl/tls secure channel" in text_lower:
                return (
                    "Falha de SSL/TLS ao baixar o instalador. Habilite TLS 1.2 no servidor Windows.",
                    "TLS_ERROR",
                    "network"
                )
            if "proxy" in text_lower or "407" in text_lower:
                return (
                    "Falha ao baixar o instalador: Proxy corporativo exigiu autenticação.",
                    "PROXY_AUTH",
                    "network"
                )
            if "not recognized" in text_lower:
                return (
                    "PowerShell não possui o cmdlet Invoke-WebRequest (versão antiga)."
                    " Atualize para PowerShell 3.0+ ou habilite o módulo WebRequest.",
                    "POWERSHELL_LEGACY",
                    "environment"
                )

        if "start-process" in text_lower and any(term in text_lower for term in ["access is denied", "acesso negado", "access denied"]):
            return (
                "Permissão negada ao executar msiexec via PSExec. Usuário precisa ser administrador local e o UAC deve permitir acesso remoto.",
                "PERMISSION_DENIED",
                "permissions"
            )

        if any(code in text_lower for code in ["exit code 1603", "returned exit code: 1603", "error code 1603", "1603"]):
            return (
                "Msiexec retornou código 1603. Verifique instalações anteriores do windows_exporter, antivirus ou pendências de reinicialização.",
                "MSI_ERROR_1603",
                "installer"
            )

        if any(code in text_lower for code in ["exit code 1618", "returned exit code: 1618", "error code 1618", "another installation is in progress"]):
            return (
                "Outra instalação MSI está em andamento no host. Aguarde finalizar para tentar novamente.",
                "MSI_ERROR_1618",
                "installer"
            )

        if "system cannot find the file" in text_lower or "arquivo especificado" in text_lower:
            return (
                "Sistema não encontrou arquivos temporários do instalador. Verifique espaço em disco, antivírus e permissões em %TEMP%.",
                "FILE_NOT_FOUND",
                "filesystem"
            )

        if "verifique se o nome está correto" in text_lower and "invoke-webrequest" in text_lower:
            return (
                "Invoke-WebRequest não está disponível nesta versão do PowerShell."
                " Instale Windows Management Framework 5.1 ou superior.",
                "POWERSHELL_LEGACY",
                "environment"
            )

        return (
            "Instalação do windows_exporter falhou. Revise o log detalhado e valide conectividade, permissões e antivírus.",
            "INSTALLATION_FAILED",
            "installer"
        )

    def _raise_install_error(
        self,
        code: str,
        message: str,
        category: str,
        output: Optional[str],
        error: Optional[str]
    ) -> None:
        combined_text = "\n".join(part for part in [output, error] if part).strip()
        snippet = combined_text[-1000:] if combined_text else ""
        raise Exception(f"{code}|{message}|{category}|{snippet}")

    async def validate_installation(self, basic_auth_user: Optional[str] = None, basic_auth_password: Optional[str] = None) -> bool:
        """Validate installation with optional Basic Auth test"""
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
        
        # Test HTTP endpoint with Basic Auth if enabled
        if basic_auth_user and basic_auth_password:
            try:
                import requests
                from requests.auth import HTTPBasicAuth
                
                url = f"http://{self.host}:9182/metrics"
                await self.log(f"Testando Basic Auth em {url}...", "info")
                
                def test_auth():
                    # Test without auth (should fail)
                    response_no_auth = requests.get(url, timeout=5)
                    if response_no_auth.status_code != 401:
                        return False, "Endpoint não está protegido (esperado 401 sem credenciais)"
                    
                    # Test with auth (should succeed)
                    response_auth = requests.get(url, auth=HTTPBasicAuth(basic_auth_user, basic_auth_password), timeout=5)
                    if response_auth.status_code == 200:
                        return True, "Basic Auth funcionando corretamente"
                    else:
                        return False, f"Falha na autenticação (status {response_auth.status_code})"
                
                success, message = await asyncio.to_thread(test_auth)
                if success:
                    await self.log(f"✅ {message}", "success")
                else:
                    await self.log(f"⚠️ {message}", "warning")
            except Exception as e:
                await self.log(f"⚠️ Não foi possível testar Basic Auth: {e}", "warning")

        await self.log("Instalação validada com sucesso!", "success")
        return True

    async def get_system_info(self) -> Dict[str, str]:
        """Get system information"""
        info = await super().get_system_info()

        exit_code, hostname, _ = await self.execute_command("echo %COMPUTERNAME%", powershell=False)
        if exit_code == 0:
            info["hostname"] = hostname.strip()

        return info
