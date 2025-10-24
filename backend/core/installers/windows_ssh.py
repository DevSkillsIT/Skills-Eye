"""
Windows Exporter installer via SSH
For Windows servers with OpenSSH installed
Uses paramiko for SSH connections
"""
import asyncio
import socket
import paramiko
import requests
from typing import Tuple, Optional, Dict
from .base import BaseInstaller


# Collector configurations
WINDOWS_EXPORTER_COLLECTORS = {
    'recommended': ['cpu', 'cs', 'logical_disk', 'memory', 'net', 'os', 'system'],
    'full': ['cpu', 'cs', 'logical_disk', 'memory', 'net', 'os', 'system', 'service', 'tcp', 'thermalzone'],
    'minimal': ['cpu', 'memory', 'logical_disk', 'os']
}


def test_port(host: str, port: int, timeout: int = 2) -> bool:
    """Test if a port is open"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except:
        return False


class WindowsSSHInstaller(BaseInstaller):
    """Windows Exporter installer via SSH (OpenSSH on Windows)"""

    def __init__(
        self,
        host: str,
        username: str,
        password: Optional[str] = None,
        key_file: Optional[str] = None,
        domain: Optional[str] = None,
        ssh_port: int = 22,
        client_id: str = "default"
    ):
        super().__init__(host, client_id)
        self.username = username
        self.password = password
        self.key_file = key_file
        self.domain = domain
        self.ssh_port = ssh_port
        self.ssh_client: Optional[paramiko.SSHClient] = None

        # Build full username for domain accounts
        if domain:
            self.full_username = f"{domain}\\{username}"
        else:
            self.full_username = username

    async def validate_connection(self) -> Tuple[bool, str]:
        """Validate connection parameters"""
        await self.log(f"Validando conexão SSH para {self.host}...", "info")

        # Test SSH port
        port_open = await asyncio.to_thread(test_port, self.host, self.ssh_port, 5)
        if not port_open:
            return False, f"Porta SSH {self.ssh_port} não está acessível em {self.host}"

        await self.log(f"Porta SSH {self.ssh_port} acessível", "success")
        return True, "OK"

    async def connect(self) -> bool:
        """Connect via SSH"""
        try:
            valid, msg = await self.validate_connection()
            if not valid:
                await self.log(msg, "error")
                return False

            self.ssh_client = paramiko.SSHClient()
            self.ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

            kwargs = {
                'hostname': self.host,
                'username': self.full_username,
                'port': self.ssh_port,
                'timeout': 10
            }

            if self.key_file:
                kwargs['key_filename'] = self.key_file
            elif self.password:
                kwargs['password'] = self.password

            await self.log("Conectando via SSH ao Windows...", "info")
            await asyncio.to_thread(self.ssh_client.connect, **kwargs)
            await self.log("Conectado via SSH com sucesso", "success")
            return True

        except paramiko.AuthenticationException:
            await self.log("Falha de autenticação SSH", "error")
            return False
        except paramiko.SSHException as e:
            await self.log(f"Erro SSH: {e}", "error")
            return False
        except Exception as e:
            await self.log(f"Erro ao conectar: {e}", "error")
            return False

    async def disconnect(self):
        """Disconnect SSH"""
        if self.ssh_client:
            self.ssh_client.close()
            await self.log("Conexão SSH fechada", "debug")

    async def execute_command(self, command: str, powershell: bool = True) -> Tuple[int, str, str]:
        """Execute remote command via SSH"""
        try:
            # For Windows SSH, prepend powershell if needed
            if powershell:
                command = f'powershell.exe -Command "{command}"'

            def _exec():
                stdin, stdout, stderr = self.ssh_client.exec_command(command)
                exit_status = stdout.channel.recv_exit_status()
                output = stdout.read().decode('utf-8', errors='ignore')
                error = stderr.read().decode('utf-8', errors='ignore')
                return exit_status, output, error

            return await asyncio.to_thread(_exec)
        except Exception as e:
            return 1, "", str(e)

    async def detect_os(self) -> Optional[str]:
        """Detect operating system"""
        await self.log("Detectando sistema operacional...", "info")

        exit_code, output, _ = await self.execute_command("$PSVersionTable.PSVersion.Major", powershell=True)

        if exit_code == 0 and output.strip().isdigit():
            self.os_type = 'windows'

            # Get detailed OS info
            exit_code, os_info, _ = await self.execute_command(
                "(Get-WmiObject -Class Win32_OperatingSystem).Caption",
                powershell=True
            )
            if exit_code == 0:
                self.os_details['name'] = os_info.strip()

            exit_code, version, _ = await self.execute_command(
                "(Get-WmiObject -Class Win32_OperatingSystem).Version",
                powershell=True
            )
            if exit_code == 0:
                self.os_details['version'] = version.strip()

            await self.log(f"Windows detectado: {self.os_details.get('name', 'Unknown')}", "success")
            return 'windows'

        await self.log("SO não é Windows ou não detectado", "error")
        return None

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
        await self.log("=== Instalando Windows Exporter via SSH ===", "info")

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
$process = Start-Process msiexec.exe -ArgumentList $arguments -Wait -PassThru -NoNewWindow

if ($process.ExitCode -ne 0) {{
    Write-Host "FAILED: Exit code $($process.ExitCode)"
    exit 1
}}

Start-Sleep -Seconds 5

$service = Get-Service -Name "windows_exporter" -ErrorAction SilentlyContinue
if ($service -and $service.Status -eq "Running") {{
    Write-Host "SUCCESS"
    try {{
        $response = Invoke-WebRequest -Uri "http://localhost:9182/metrics" -UseBasicParsing -TimeoutSec 5
        if ($response.StatusCode -eq 200) {{
            Write-Host "METRICS_OK"
        }}
    }} catch {{}}
}} else {{
    Write-Host "FAILED: Service not running"
    exit 1
}}

Remove-Item $installer -Force -ErrorAction SilentlyContinue
'''

        await self.progress(30, 100, "Executando instalação...")
        await self.progress(40, 100, "Baixando Windows Exporter...")

        # For long-running scripts on Windows SSH, we need to handle them differently
        # Create a temp script file and execute it
        script_path = "$env:TEMP\\install_we.ps1"

        # Upload script
        exit_code, _, _ = await self.execute_command(
            f'Set-Content -Path {script_path} -Value @"\n{install_script}\n"@',
            powershell=True
        )

        if exit_code != 0:
            await self.log("Erro ao criar script de instalação", "error")
            return False

        # Execute script
        exit_code, output, error = await self.execute_command(
            f"& {script_path}",
            powershell=True
        )

        await self.progress(90, 100, "Finalizando...")

        # Clean up
        await self.execute_command(f"Remove-Item {script_path} -Force -ErrorAction SilentlyContinue", powershell=True)

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
        exit_code, output, _ = await self.execute_command(command, powershell=True)

        if exit_code == 0 and 'Running' in output:
            await self.log("Serviço windows_exporter está rodando", "success")
        else:
            await self.log("Serviço windows_exporter não está ativo", "error")
            return False

        # Test metrics
        command = '(Invoke-WebRequest -Uri "http://localhost:9182/metrics" -UseBasicParsing).StatusCode'
        exit_code, output, _ = await self.execute_command(command, powershell=True)

        if exit_code == 0 and '200' in output:
            await self.log("Métricas acessíveis", "success")
        else:
            await self.log("Métricas não acessíveis", "warning")

        await self.log("Instalação validada com sucesso!", "success")
        return True

    async def get_system_info(self) -> Dict[str, str]:
        """Get system information"""
        info = await super().get_system_info()

        exit_code, hostname, _ = await self.execute_command("$env:COMPUTERNAME", powershell=True)
        if exit_code == 0:
            info["hostname"] = hostname.strip()

        exit_code, uptime, _ = await self.execute_command(
            "(Get-CimInstance -ClassName Win32_OperatingSystem).LastBootUpTime",
            powershell=True
        )
        if exit_code == 0:
            info["last_boot"] = uptime.strip()

        return info
