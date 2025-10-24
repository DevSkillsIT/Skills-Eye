"""
Linux Node Exporter installer via SSH
Uses paramiko for SSH connections
"""
import asyncio
import socket
import paramiko
import requests
from typing import Tuple, Optional, Dict
from .base import BaseInstaller


# Collector configurations
NODE_EXPORTER_COLLECTORS = {
    'recommended': {
        'enable': ['cpu', 'loadavg', 'meminfo', 'diskstats', 'filesystem', 'netdev', 'time', 'uname'],
        'disable': ['interrupts', 'ipvs', 'sockstat']
    },
    'full': {
        'enable': ['cpu', 'loadavg', 'meminfo', 'diskstats', 'filesystem', 'netdev', 'time', 'uname', 'systemd', 'processes', 'tcpstat'],
        'disable': ['interrupts', 'ipvs']
    },
    'minimal': {
        'enable': ['cpu', 'meminfo', 'filesystem', 'loadavg'],
        'disable': ['*']
    }
}

NODE_EXPORTER_COLLECTOR_DETAILS = {
    'cpu': 'Uso de CPU por core e modo',
    'loadavg': 'Carga média do sistema',
    'meminfo': 'Uso de memória RAM',
    'diskstats': 'I/O de disco',
    'filesystem': 'Uso de espaço em disco',
    'netdev': 'Tráfego de rede',
    'time': 'Timestamp do sistema',
    'uname': 'Informações do kernel',
    'systemd': 'Status de serviços systemd',
    'processes': 'Processos em execução',
    'tcpstat': 'Estatísticas de conexões TCP',
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


class LinuxSSHInstaller(BaseInstaller):
    """Linux Node Exporter installer via SSH"""

    def __init__(
        self,
        host: str,
        username: str,
        password: Optional[str] = None,
        key_file: Optional[str] = None,
        ssh_port: int = 22,
        use_sudo: bool = True,
        client_id: str = "default"
    ):
        super().__init__(host, client_id)
        self.username = username
        self.password = password
        self.key_file = key_file
        self.ssh_port = ssh_port
        self.use_sudo = use_sudo
        self.ssh_client: Optional[paramiko.SSHClient] = None

    async def validate_connection(self) -> Tuple[bool, str]:
        """Validate connection parameters before connecting"""
        await self.log(f"Validando parâmetros de conexão para {self.host}...", "info")

        # Test SSH port
        await self.log(f"Testando porta SSH {self.ssh_port}...", "info")
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
                'username': self.username,
                'port': self.ssh_port,
                'timeout': 10
            }

            if self.key_file:
                kwargs['key_filename'] = self.key_file
            elif self.password:
                kwargs['password'] = self.password

            await self.log("Conectando via SSH...", "info")
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

    async def execute_command(self, command: str, use_sudo: Optional[bool] = None) -> Tuple[int, str, str]:
        """Execute remote command via SSH"""
        if use_sudo is None:
            use_sudo = self.use_sudo

        if use_sudo and self.username != 'root':
            command = f"sudo -S {command}"

        try:
            def _exec():
                stdin, stdout, stderr = self.ssh_client.exec_command(command)

                if use_sudo and self.password:
                    stdin.write(self.password + '\n')
                    stdin.flush()

                exit_status = stdout.channel.recv_exit_status()
                output = stdout.read().decode('utf-8')
                error = stderr.read().decode('utf-8')
                return exit_status, output, error

            return await asyncio.to_thread(_exec)
        except Exception as e:
            return 1, "", str(e)

    async def detect_os(self) -> Optional[str]:
        """Detect operating system"""
        await self.log("Detectando sistema operacional...", "info")

        exit_code, output, _ = await self.execute_command("cat /etc/os-release 2>/dev/null || echo 'not_linux'")

        if exit_code == 0 and 'not_linux' not in output:
            self.os_type = 'linux'
            for line in output.split('\n'):
                if '=' in line:
                    key, value = line.split('=', 1)
                    self.os_details[key] = value.strip('"')

            pretty_name = self.os_details.get('PRETTY_NAME', 'Unknown Linux')
            await self.log(f"Linux detectado: {pretty_name}", "success")
            return 'linux'

        await self.log("SO não é Linux ou não detectado", "error")
        return None

    async def check_disk_space(self, required_mb: int = 200) -> bool:
        """Check available disk space"""
        await self.log("Verificando espaço em disco...", "info")

        exit_code, output, _ = await self.execute_command("df -BM /usr/local/bin | tail -1 | awk '{print $4}'")
        if exit_code == 0:
            try:
                available = int(output.strip().replace('M', ''))
                if available < required_mb:
                    await self.log(f"Espaço insuficiente: {available}MB disponível, {required_mb}MB necessário", "error")
                    return False
                await self.log(f"Espaço suficiente: {available}MB disponível", "success")
                return True
            except:
                pass

        await self.log("Não foi possível verificar espaço em disco", "warning")
        return True

    async def check_exporter_installed(self) -> bool:
        """Check if Node Exporter is already installed"""
        await self.log("Verificando instalação existente...", "info")

        port = 9100
        binary_path = "/usr/local/bin/node_exporter"
        service_name = "node_exporter"

        # Test port
        port_in_use = await asyncio.to_thread(test_port, self.host, port, 2)

        # Check service
        exit_code, output, _ = await self.execute_command(f"systemctl is-active {service_name}")
        service_running = exit_code == 0 and 'active' in output

        # Check version
        exit_code, output, _ = await self.execute_command(f"{binary_path} --version 2>&1 | head -1")
        if exit_code == 0:
            self.installed_version = output.strip()

        if port_in_use or service_running:
            await self.log(f"{service_name} já está instalado e rodando", "warning")
            if self.installed_version:
                await self.log(f"Versão instalada: {self.installed_version}", "debug")
            return True

        await self.log("Nenhuma instalação anterior detectada", "success")
        return False

    async def install_exporter(self, collector_profile: str = 'recommended') -> bool:
        """Install Node Exporter"""
        await self.log("=== Instalando Node Exporter ===", "info")

        # Get architecture
        exit_code, arch, _ = await self.execute_command("uname -m")
        arch = arch.strip()

        arch_map = {'x86_64': 'amd64', 'aarch64': 'arm64', 'armv7l': 'armv7'}
        arch_suffix = arch_map.get(arch)

        if not arch_suffix:
            await self.log(f"Arquitetura não suportada: {arch}", "error")
            return False

        await self.log(f"Arquitetura: {arch} ({arch_suffix})", "success")

        # Get latest version
        try:
            await self.log("Obtendo última versão do GitHub...", "info")

            def get_version():
                response = requests.get(
                    "https://api.github.com/repos/prometheus/node_exporter/releases/latest",
                    timeout=10
                )
                return response.json()['tag_name'].lstrip('v')

            version = await asyncio.to_thread(get_version)
            await self.log(f"Versão: {version}", "success")
        except Exception as e:
            await self.log(f"Erro ao obter versão: {e}", "error")
            return False

        # Prepare collectors
        collectors = NODE_EXPORTER_COLLECTORS.get(collector_profile, NODE_EXPORTER_COLLECTORS['recommended'])
        collector_flags = []

        for col in collectors.get('enable', []):
            collector_flags.append(f"--collector.{col}")

        for col in collectors.get('disable', []):
            if col == '*':
                collector_flags.append("--collector.disable-defaults")
            else:
                collector_flags.append(f"--no-collector.{col}")

        collector_string = ' \\\n    '.join(collector_flags)
        url = f"https://github.com/prometheus/node_exporter/releases/download/v{version}/node_exporter-{version}.linux-{arch_suffix}.tar.gz"

        # Installation script
        install_script = f'''#!/bin/bash
set -e
TMP_DIR=$(mktemp -d)
cd "$TMP_DIR"
echo "Baixando Node Exporter v{version}..."
wget -q --show-progress "{url}" || exit 1
echo "Extraindo..."
tar -xzf "node_exporter-{version}.linux-{arch_suffix}.tar.gz"
if [ -f /usr/local/bin/node_exporter ]; then
    mv /usr/local/bin/node_exporter /usr/local/bin/node_exporter.bak
fi
cp "node_exporter-{version}.linux-{arch_suffix}/node_exporter" /usr/local/bin/
chmod +x /usr/local/bin/node_exporter
if ! id -u node_exporter > /dev/null 2>&1; then
    useradd --no-create-home --shell /bin/false node_exporter
fi
cat > /etc/systemd/system/node_exporter.service << 'EOF'
[Unit]
Description=Node Exporter
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=node_exporter
Group=node_exporter
ExecStart=/usr/local/bin/node_exporter \\
    --web.listen-address=:9100 \\
    {collector_string}
Restart=always
RestartSec=10s

[Install]
WantedBy=multi-user.target
EOF
systemctl daemon-reload
systemctl enable node_exporter
systemctl restart node_exporter
sleep 3
if systemctl is-active --quiet node_exporter; then
    echo "SUCCESS"
else
    echo "FAILED"
    exit 1
fi
cd /
rm -rf "$TMP_DIR"
'''

        await self.progress(30, 100, "Executando instalação...")

        # Execute installation
        await self.execute_command(f"cat > /tmp/install_ne.sh << 'EOFSCRIPT'\n{install_script}\nEOFSCRIPT")
        await self.progress(40, 100, "Baixando Node Exporter...")

        exit_code, output, error = await self.execute_command("bash /tmp/install_ne.sh 2>&1")
        await self.progress(90, 100, "Finalizando...")

        if exit_code == 0 and 'SUCCESS' in output:
            await self.log(f"Node Exporter v{version} instalado com sucesso!", "success")
            await self.execute_command("rm -f /tmp/install_ne.sh")
            return True
        else:
            await self.log("Instalação falhou", "error")
            await self.log(f"Output: {output[:500]}", "debug")
            return False

    async def validate_installation(self) -> bool:
        """Validate installation"""
        await self.log("Validando instalação...", "info")

        # Check service
        exit_code, output, _ = await self.execute_command("systemctl is-active node_exporter")
        if exit_code == 0 and 'active' in output:
            await self.log("Serviço node_exporter está rodando", "success")
        else:
            await self.log("Serviço node_exporter não está ativo", "error")
            return False

        # Test metrics
        exit_code, output, _ = await self.execute_command("curl -s http://localhost:9100/metrics | head -5")
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

        exit_code, hostname, _ = await self.execute_command("hostname")
        if exit_code == 0:
            info["hostname"] = hostname.strip()

        exit_code, uptime, _ = await self.execute_command("uptime")
        if exit_code == 0:
            info["uptime"] = uptime.strip()

        return info
