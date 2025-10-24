"""
Windows Exporter installer via PSexec
Uses subprocess to run PSexec commands
PSexec must be installed and available in PATH or specified path
"""
import asyncio
import socket
import subprocess
import requests
from typing import Tuple, Optional, Dict
from pathlib import Path
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


class WindowsPSExecInstaller(BaseInstaller):
    """Windows Exporter installer via PSexec"""

    def __init__(
        self,
        host: str,
        username: str,
        password: str,
        domain: Optional[str] = None,
        psexec_path: str = "psexec.exe",
        client_id: str = "default"
    ):
        super().__init__(host, client_id)
        self.username = username
        self.password = password
        self.domain = domain  # Domain for domain accounts
        self.psexec_path = psexec_path

        # Build full username
        if domain:
            self.full_username = f"{domain}\\{username}"
        else:
            self.full_username = username

    async def validate_connection(self) -> Tuple[bool, str]:
        """Validate connection parameters"""
        await self.log(f"Validando PSexec para {self.host}...", "info")

        # Check if psexec exists
        try:
            result = await asyncio.to_thread(
                subprocess.run,
                [self.psexec_path],
                capture_output=True,
                timeout=5
            )
            # PSexec returns error when run without args, but that's expected
        except FileNotFoundError:
            return False, f"PSexec não encontrado em: {self.psexec_path}"
        except subprocess.TimeoutExpired:
            pass  # Expected
        except Exception as e:
            return False, f"Erro ao verificar PSexec: {e}"

        # Test SMB port (445)
        port_open = await asyncio.to_thread(test_port, self.host, 445, 5)
        if not port_open:
            await self.log("Porta SMB 445 não está acessível (pode estar bloqueada por firewall)", "warning")

        await self.log("PSexec disponível", "success")
        return True, "OK"

    async def connect(self) -> bool:
        """Test connection via PSexec"""
        try:
            valid, msg = await self.validate_connection()
            if not valid:
                await self.log(msg, "error")
                return False

            await self.log("Testando conexão PSexec...", "info")

            # Test with simple command
            exit_code, output, error = await self.execute_command("echo Connected")

            if exit_code == 0:
                await self.log("Conexão PSexec bem-sucedida", "success")
                return True
            else:
                await self.log(f"Falha na conexão PSexec: {error}", "error")
                return False

        except Exception as e:
            await self.log(f"Erro ao conectar via PSexec: {e}", "error")
            return False

    async def disconnect(self):
        """PSexec doesn't maintain persistent connections"""
        await self.log("PSexec não mantém conexões persistentes", "debug")

    async def execute_command(self, command: str, powershell: bool = False) -> Tuple[int, str, str]:
        """Execute remote command via PSexec"""
        try:
            # Build PSexec command
            psexec_cmd = [
                self.psexec_path,
                f"\\\\{self.host}",
                "-u", self.full_username,
                "-p", self.password,
                "-accepteula",  # Auto-accept EULA
                "-nobanner"  # Suppress banner
            ]

            if powershell:
                psexec_cmd.extend([
                    "powershell.exe",
                    "-ExecutionPolicy", "Bypass",
                    "-NoProfile",
                    "-Command", command
                ])
            else:
                psexec_cmd.extend(["cmd.exe", "/c", command])

            def _exec():
                result = subprocess.run(
                    psexec_cmd,
                    capture_output=True,
                    text=True,
                    timeout=300  # 5 minute timeout
                )
                return result.returncode, result.stdout, result.stderr

            return await asyncio.to_thread(_exec)

        except subprocess.TimeoutExpired:
            return 1, "", "Timeout ao executar comando"
        except Exception as e:
            return 1, "", str(e)

    async def detect_os(self) -> Optional[str]:
        """Detect operating system"""
        await self.log("Detectando sistema operacional...", "info")

        exit_code, output, _ = await self.execute_command("ver", powershell=False)

        if exit_code == 0 and 'Windows' in output:
            self.os_type = 'windows'
            self.os_details['name'] = output.strip()

            # Get more details
            exit_code, version, _ = await self.execute_command(
                "(Get-WmiObject -Class Win32_OperatingSystem).Caption",
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
