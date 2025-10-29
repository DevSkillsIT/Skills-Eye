"""
Windows Exporter installer via WinRM/PowerShell
Uses pywinrm for remote PowerShell execution
"""
import asyncio
import socket
import requests
from typing import Tuple, Optional, Dict
from .base import BaseInstaller

try:
    import winrm
    HAS_WINRM = True
except ImportError:
    HAS_WINRM = False


# Collector configurations for Windows Exporter
WINDOWS_EXPORTER_COLLECTORS = {
    'recommended': ['cpu', 'cs', 'logical_disk', 'memory', 'net', 'os', 'system'],
    'full': ['cpu', 'cs', 'logical_disk', 'memory', 'net', 'os', 'system', 'service', 'tcp', 'thermalzone'],
    'minimal': ['cpu', 'memory', 'logical_disk', 'os']
}

WINDOWS_EXPORTER_COLLECTOR_DETAILS = {
    'cpu': 'Uso de CPU',
    'cs': 'Informações do computador',
    'logical_disk': 'Uso de disco',
    'memory': 'Uso de memória',
    'net': 'Tráfego de rede',
    'os': 'Informações do SO',
    'system': 'Sistema geral',
    'service': 'Serviços Windows',
    'tcp': 'Conexões TCP',
    'thermalzone': 'Temperatura'
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
        
        if result == 0:
            return True
        elif result in (10061, 111):  # Connection refused - host is UP but port closed
            return False
        elif result in (10060, 110, 10065, 113):  # Timeout or unreachable - host is DOWN
            raise socket.timeout(f"Connection to {host}:{port} timed out (error code {result}). Host may be offline or unreachable.")
        else:
            raise Exception(f"Network error connecting to {host}:{port} (error code {result})")
            
    except socket.gaierror as e:
        raise socket.gaierror(f"DNS resolution failed for {host}: {e}")
    except socket.timeout:
        raise
    except OSError as e:
        error_msg = str(e).lower()
        if "timed out" in error_msg or "timeout" in error_msg:
            raise socket.timeout(f"Connection to {host}:{port} timed out: {e}")
        else:
            raise Exception(f"Network error testing {host}:{port}: {e}")
    except Exception as e:
        raise Exception(f"Unexpected error testing {host}:{port}: {e}")
    finally:
        if sock:
            try:
                sock.close()
            except:
                pass


class WindowsWinRMInstaller(BaseInstaller):
    """Windows Exporter installer via WinRM/PowerShell"""

    def __init__(
        self,
        host: str,
        username: str,
        password: str,
        domain: Optional[str] = None,
        use_ssl: bool = False,
        port: Optional[int] = None,
        client_id: str = "default"
    ):
        super().__init__(host, client_id)
        self.username = username
        self.password = password
        self.domain = domain  # For domain accounts, e.g., "DOMAIN" or None for local
        self.use_ssl = use_ssl
        self.port = port or (5986 if use_ssl else 5985)
        self.session = None

        # Build full username
        if domain:
            self.full_username = f"{domain}\\{username}"
        else:
            self.full_username = username

    async def validate_connection(self) -> Tuple[bool, str]:
        """Validate connection parameters with network checks"""
        if not HAS_WINRM:
            return False, "pywinrm não está instalado. Execute: pip install pywinrm"

        await self.log(f"🔧 Validando conexão WinRM para {self.host}:{self.port}...", "info")

        # Test network connectivity and DNS
        await self.log(f"🌐 Testando conectividade com {self.host}...", "info")
        
        try:
            # Test WinRM port with detailed error handling
            port_open = await asyncio.to_thread(test_port, self.host, self.port, 10)
            if not port_open:
                await self.log(f"⚠️ Porta WinRM {self.port} não está acessível", "warning")
                return False, f"Porta WinRM {self.port} não está acessível em {self.host}"
            
            await self.log(f"✅ Porta WinRM {self.port} está acessível", "success")
            
        except socket.gaierror as e:
            await self.log(f"❌ Falha na resolução DNS: {e}", "error")
            return False, f"DNS_ERROR|Não foi possível resolver o hostname {self.host}|network"
            
        except socket.timeout as e:
            await self.log(f"❌ Timeout: {e}", "error")
            return False, f"TIMEOUT|Host {self.host} não respondeu (offline ou rede inacessível)|network"
            
        except Exception as e:
            await self.log(f"❌ Erro de rede: {e}", "error")
            return False, f"NETWORK_ERROR|Erro de conectividade: {e}|network"

        await self.log("✅ WinRM disponível e host acessível", "success")
        return True, "OK"

    async def connect(self) -> bool:
        """Connect via WinRM"""
        try:
            valid, msg = await self.validate_connection()
            if not valid:
                await self.log(msg, "error")
                # Lançar exceção estruturada para informar o motivo
                if "pywinrm não está instalado" in msg:
                    raise Exception("DEPENDENCY_MISSING|pywinrm não está instalado. Execute: pip install pywinrm|CONFIGURACAO")
                elif "Porta WinRM" in msg:
                    raise Exception(f"PORT_CLOSED|{msg}|CONEXAO")
                else:
                    raise Exception(f"VALIDATION_ERROR|{msg}|CONFIGURACAO")

            await self.log("Conectando via WinRM...", "info")

            protocol = 'https' if self.use_ssl else 'http'
            endpoint = f"{protocol}://{self.host}:{self.port}/wsman"

            def _connect():
                return winrm.Session(
                    endpoint,
                    auth=(self.full_username, self.password),
                    server_cert_validation='ignore' if self.use_ssl else None
                )

            self.session = await asyncio.to_thread(_connect)

            # Test connection with detailed error
            result = await self.execute_command("echo Connected")
            if result[0] == 0:
                await self.log("Conectado via WinRM com sucesso", "success")
                return True
            else:
                error_detail = result[2] if result[2] else "Falha ao executar comando de teste"
                await self.log(f"Falha ao testar conexão WinRM: {error_detail}", "error")
                
                # Lançar exceção com detalhes do erro
                if "401" in error_detail or "Unauthorized" in error_detail:
                    raise Exception(f"AUTH_FAILED|Autenticação falhou. Verifique usuário e senha.|AUTENTICACAO")
                elif "Connection refused" in error_detail or "timeout" in error_detail.lower():
                    raise Exception(f"TIMEOUT|Timeout ao conectar via WinRM. Serviço WinRM pode estar desabilitado.|CONEXAO")
                else:
                    raise Exception(f"WINRM_ERROR|{error_detail}|CONEXAO")

        except Exception as e:
            error_msg = str(e)
            await self.log(f"Erro ao conectar via WinRM: {error_msg}", "error")
            
            # Se já é uma exceção estruturada, re-lançar
            if "|" in error_msg:
                raise
            
            # Analisar erro do pywinrm para fornecer detalhes úteis
            if "401" in error_msg or "Unauthorized" in error_msg:
                raise Exception("AUTH_FAILED|Usuário ou senha inválidos. Verifique as credenciais.|AUTENTICACAO")
            elif "Connection refused" in error_msg:
                raise Exception(f"CONNECTION_REFUSED|WinRM recusou conexão. Verifique se o serviço WinRM está habilitado em {self.host}.|CONEXAO")
            elif "timeout" in error_msg.lower() or "timed out" in error_msg.lower():
                raise Exception(f"TIMEOUT|Timeout ao conectar via WinRM na porta {self.port}. Verifique firewall e serviço WinRM.|CONEXAO")
            elif "Name or service not known" in error_msg or "getaddrinfo failed" in error_msg:
                raise Exception(f"DNS_ERROR|Não foi possível resolver o hostname '{self.host}'.|REDE")
            elif "No route to host" in error_msg or "Network is unreachable" in error_msg:
                raise Exception(f"NETWORK_UNREACHABLE|Host {self.host} está inacessível pela rede.|REDE")
            else:
                raise Exception(f"WINRM_ERROR|{error_msg}|DESCONHECIDO")

    async def disconnect(self):
        """Disconnect WinRM"""
        self.session = None
        await self.log("Conexão WinRM fechada", "debug")

    async def execute_command(self, command: str, powershell: bool = True) -> Tuple[int, str, str]:
        """Execute remote command via WinRM"""
        try:
            def _exec():
                if powershell:
                    result = self.session.run_ps(command)
                else:
                    result = self.session.run_cmd(command)

                return result.status_code, result.std_out.decode('utf-8'), result.std_err.decode('utf-8')

            return await asyncio.to_thread(_exec)
        except Exception as e:
            return 1, "", str(e)

    async def detect_os(self) -> Optional[str]:
        """Detect operating system with multiple fallback methods"""
        await self.log("🔍 Detectando sistema operacional...", "info")

        # Método 1: Tentar via Win32_OperatingSystem (mais completo)
        await self.log("📋 Tentando detectar via PowerShell (Win32_OperatingSystem)...", "info")
        exit_code, os_info, _ = await self.execute_command(
            "(Get-WmiObject -Class Win32_OperatingSystem).Caption"
        )
        
        if exit_code == 0 and os_info and os_info.strip():
            self.os_type = 'windows'
            self.os_details['name'] = os_info.strip()
            
            # Tentar pegar versão também
            exit_code, version, _ = await self.execute_command(
                "(Get-WmiObject -Class Win32_OperatingSystem).Version"
            )
            if exit_code == 0 and version:
                self.os_details['version'] = version.strip()
            
            await self.log(f"✅ Windows detectado: {os_info.strip()}", "info")
            return 'windows'
        
        # Método 2: Tentar via $PSVersionTable (confirma PowerShell/Windows)
        await self.log("📋 Tentando detectar via $PSVersionTable...", "info")
        exit_code, output, _ = await self.execute_command("$PSVersionTable.PSVersion.Major")
        
        if exit_code == 0 and output and output.strip():
            self.os_type = 'windows'
            self.os_details['name'] = f'Windows (PowerShell {output.strip()})'
            await self.log(f"✅ Windows detectado via PowerShell", "info")
            return 'windows'
        
        # Método 3: Assumir Windows se chegou até aqui (estamos usando WinRM que é Windows-only)
        await self.log("⚠️ Não foi possível detectar versão específica, mas assumindo Windows (conexão WinRM funcionou)", "warning")
        self.os_type = 'windows'
        self.os_details['name'] = 'Windows (versão não detectada)'
        self.os_details['version'] = 'Unknown'
        return 'windows'

    async def check_disk_space(self, required_mb: int = 200) -> bool:
        """Check available disk space"""
        await self.log("Verificando espaço em disco...", "info")

        command = "(Get-PSDrive C | Select-Object -ExpandProperty Free) / 1MB"
        exit_code, output, _ = await self.execute_command(command)

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
        """Check if Windows Exporter is already installed"""
        await self.log("Verificando instalação existente...", "info")

        port = 9182
        service_name = "windows_exporter"

        # Test port
        port_in_use = await asyncio.to_thread(test_port, self.host, port, 2)

        # Check service
        command = f'(Get-Service -Name "{service_name}" -ErrorAction SilentlyContinue).Status'
        exit_code, output, _ = await self.execute_command(command)
        service_running = exit_code == 0 and 'Running' in output

        if port_in_use or service_running:
            await self.log(f"{service_name} já está instalado e rodando", "warning")
            return True

        await self.log("Nenhuma instalação anterior detectada", "success")
        return False

    async def install_exporter(self, collector_profile: str = 'recommended') -> bool:
        """Install Windows Exporter"""
        await self.log("=== Instalando Windows Exporter ===", "info")

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
$logFile = "$env:TEMP\\windows_exporter_install.log"

Write-Host "Baixando Windows Exporter v{version}..."
try {{
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
    Invoke-WebRequest -Uri $url -OutFile $installer -UseBasicParsing
    Write-Host "Download concluído"
}} catch {{
    Write-Host "Erro no download: $_"
    exit 1
}}

Write-Host "Parando serviço existente (se houver)..."
Stop-Service -Name "windows_exporter" -ErrorAction SilentlyContinue

Write-Host "Instalando..."
$arguments = @("/i", $installer, "ENABLED_COLLECTORS=$collectors", "/quiet", "/norestart", "/l*v", $logFile)
$process = Start-Process msiexec.exe -ArgumentList $arguments -Wait -PassThru -NoNewWindow

if ($process.ExitCode -ne 0) {{
    Write-Host "Erro na instalação. Código: $($process.ExitCode)"
    exit 1
}}

Write-Host "Aguardando inicialização..."
Start-Sleep -Seconds 5

$service = Get-Service -Name "windows_exporter" -ErrorAction SilentlyContinue
if ($service -and $service.Status -eq "Running") {{
    Write-Host "SUCCESS"
    try {{
        $response = Invoke-WebRequest -Uri "http://localhost:9182/metrics" -UseBasicParsing -TimeoutSec 5
        if ($response.StatusCode -eq 200) {{
            Write-Host "METRICS_OK"
        }}
    }} catch {{
        Write-Host "WARN: Métricas não acessíveis ainda"
    }}
}} else {{
    Write-Host "FAILED: Serviço não está rodando"
    exit 1
}}

Remove-Item $installer -Force -ErrorAction SilentlyContinue
Write-Host "Instalação concluída!"
'''

        await self.progress(30, 100, "Executando instalação...")
        await self.progress(40, 100, "Baixando Windows Exporter...")

        exit_code, output, error = await self.execute_command(install_script)
        await self.progress(90, 100, "Finalizando...")

        if exit_code == 0 and 'SUCCESS' in output:
            await self.log(f"Windows Exporter v{version} instalado com sucesso!", "success")
            if 'METRICS_OK' in output:
                await self.log("Métricas acessíveis em http://localhost:9182/metrics", "success")
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
        exit_code, output, _ = await self.execute_command(command)

        if exit_code == 0 and 'Running' in output:
            await self.log("Serviço windows_exporter está rodando", "success")
        else:
            await self.log("Serviço windows_exporter não está ativo", "error")
            return False

        # Test metrics
        command = '(Invoke-WebRequest -Uri "http://localhost:9182/metrics" -UseBasicParsing).Content.Substring(0,200)'
        exit_code, output, _ = await self.execute_command(command)

        if exit_code == 0 and output:
            await self.log("Métricas acessíveis", "success")
        else:
            await self.log("Métricas não acessíveis", "error")
            return False

        await self.log("Instalação validada com sucesso!", "success")
        return True

    async def get_system_info(self) -> Dict[str, str]:
        """Get system information"""
        info = await super().get_system_info()

        exit_code, hostname, _ = await self.execute_command("$env:COMPUTERNAME")
        if exit_code == 0:
            info["hostname"] = hostname.strip()

        exit_code, uptime, _ = await self.execute_command(
            "(Get-CimInstance -ClassName Win32_OperatingSystem).LastBootUpTime"
        )
        if exit_code == 0:
            info["last_boot"] = uptime.strip()

        return info
