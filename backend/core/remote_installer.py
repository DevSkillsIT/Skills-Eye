"""
Instalador remoto de Node Exporter via SSH
Adaptado do consul_manager_original.py para funcionar com FastAPI e WebSocket
"""
import asyncio
import socket
import paramiko
import requests
from typing import Tuple, Optional, Dict
from datetime import datetime
from pathlib import Path
from .websocket_manager import ws_manager


# Configurações de collectors
NODE_EXPORTER_COLLECTORS = {
    'recommended': {
        'enable': [
            'cpu', 'loadavg', 'meminfo', 'diskstats', 'filesystem',
            'netdev', 'time', 'uname',
        ],
        'disable': [
            'interrupts', 'ipvs', 'sockstat',
        ]
    },
    'full': {
        'enable': [
            'cpu', 'loadavg', 'meminfo', 'diskstats', 'filesystem',
            'netdev', 'time', 'uname', 'systemd', 'processes', 'tcpstat'
        ],
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
    """Testa se uma porta está aberta"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except:
        return False


def validate_ip(ip: str) -> bool:
    """Valida se é um IP válido"""
    import ipaddress
    try:
        ipaddress.ip_address(ip)
        return True
    except ValueError:
        return False


class RemoteExporterInstaller:
    """Instalador remoto de Node Exporter via SSH com suporte a WebSocket"""

    def __init__(
        self,
        host: str,
        username: str,
        password: Optional[str] = None,
        key_file: Optional[str] = None,
        use_sudo: bool = False,
        ssh_port: int = 22,
        client_id: str = "default"
    ):
        self.host = host
        self.username = username
        self.password = password
        self.key_file = key_file
        self.use_sudo = use_sudo
        self.ssh_port = ssh_port
        self.client_id = client_id
        self.ssh_client: Optional[paramiko.SSHClient] = None
        self.os_type: Optional[str] = None
        self.os_details: Dict[str, str] = {}
        self.backup_path: Optional[str] = None
        self.installed_version: Optional[str] = None

    async def log(self, message: str, level: str = "info", data: dict = None):
        """Envia log via WebSocket"""
        await ws_manager.send_log(message, level, self.client_id, data)

    async def validate_connection_params(self) -> Tuple[bool, str]:
        """Valida parâmetros de conexão ANTES de tentar conectar"""
        if not validate_ip(self.host):
            try:
                socket.gethostbyname(self.host)
            except:
                return False, f"IP/hostname inválido: {self.host}"

        await self.log(f"Testando porta SSH {self.ssh_port}...", "info")

        # Testar porta em thread separada para não bloquear
        port_open = await asyncio.to_thread(test_port, self.host, self.ssh_port, 5)

        if not port_open:
            return False, f"Porta SSH {self.ssh_port} não está acessível em {self.host}"

        await self.log(f"Porta SSH {self.ssh_port} acessível", "success")
        return True, "OK"

    async def connect(self) -> bool:
        """Conecta via SSH com validações"""
        try:
            valid, msg = await self.validate_connection_params()
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

            # Conectar em thread separada
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

    async def execute_command(self, command: str, use_sudo: Optional[bool] = None) -> Tuple[int, str, str]:
        """Executa comando remoto via SSH"""
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

            # Executar em thread separada
            return await asyncio.to_thread(_exec)

        except Exception as e:
            return 1, "", str(e)

    async def detect_os(self) -> Optional[str]:
        """Detecta sistema operacional"""
        await self.log("Detectando sistema operacional...", "info")

        exit_code, output, _ = await self.execute_command("cat /etc/os-release 2>/dev/null || echo 'not_linux'")

        if exit_code == 0 and 'not_linux' not in output:
            self.os_type = 'linux'
            for line in output.split('\n'):
                if '=' in line:
                    key, value = line.split('=', 1)
                    self.os_details[key] = value.strip('"')

            distro = self.os_details.get('ID', 'unknown')
            version = self.os_details.get('VERSION_ID', 'unknown')
            pretty_name = self.os_details.get('PRETTY_NAME', 'Unknown Linux')

            await self.log(f"Linux detectado: {pretty_name}", "success")
            await self.log(f"Distribuição: {distro} {version}", "debug")
            return 'linux'

        await self.log("SO não suportado ou não detectado", "error")
        return None

    async def check_disk_space(self, required_mb: int = 200) -> bool:
        """Verifica espaço em disco"""
        await self.log("Verificando espaço em disco...", "info")

        if self.os_type == 'linux':
            exit_code, output, _ = await self.execute_command("df -BM /usr/local/bin | tail -1 | awk '{print $4}'")
            if exit_code == 0:
                try:
                    available = int(output.strip().replace('M', ''))
                    if available < required_mb:
                        await self.log(
                            f"Espaço insuficiente: {available}MB disponível, {required_mb}MB necessário",
                            "error"
                        )
                        return False
                    await self.log(f"Espaço suficiente: {available}MB disponível", "success")
                    return True
                except:
                    pass

        await self.log("Não foi possível verificar espaço em disco", "warning")
        return True

    async def check_exporter_installed(self) -> bool:
        """Verifica se exporter já está instalado"""
        await self.log("Verificando instalação existente...", "info")

        if self.os_type == 'linux':
            port = 9100
            binary_path = "/usr/local/bin/node_exporter"
            service_name = "node_exporter"

            # Testar porta
            port_in_use = await asyncio.to_thread(test_port, self.host, port, 2)

            # Verificar serviço
            exit_code, output, _ = await self.execute_command(f"systemctl is-active {service_name}")
            service_running = exit_code == 0 and 'active' in output

            # Verificar versão
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

    async def check_port_available(self, port: int) -> bool:
        """Verifica se porta está disponível"""
        await self.log(f"Verificando se porta {port} está disponível...", "info")

        if self.os_type == 'linux':
            exit_code, output, _ = await self.execute_command(f"lsof -i :{port} || netstat -tuln | grep :{port}")
            if exit_code == 0 and output.strip():
                await self.log(f"Porta {port} já está em uso!", "error")
                await self.log(f"Processo: {output[:200]}", "debug")
                return False

        await self.log(f"Porta {port} disponível", "success")
        return True

    async def install_node_exporter(
        self,
        collector_profile: str = 'recommended',
        custom_collectors: Optional[Dict] = None
    ) -> bool:
        """Instala Node Exporter no Linux"""
        await self.log("=== Iniciando Instalação do Node Exporter ===", "info")

        # Verificações iniciais
        if not await self.check_disk_space(200):
            return False

        port = 9100
        if not await self.check_port_available(port):
            await self.log("Porta 9100 está em uso, mas continuando...", "warning")

        if await self.check_exporter_installed():
            await self.log("Exporter já instalado, atualizando...", "warning")

        # Detectar arquitetura
        exit_code, arch, _ = await self.execute_command("uname -m")
        arch = arch.strip()

        arch_map = {'x86_64': 'amd64', 'aarch64': 'arm64', 'armv7l': 'armv7'}
        arch_suffix = arch_map.get(arch)

        if not arch_suffix:
            await self.log(f"Arquitetura não suportada: {arch}", "error")
            return False

        await self.log(f"Arquitetura: {arch} ({arch_suffix})", "success")

        # Obter versão mais recente
        try:
            await self.log("Obtendo última versão do GitHub...", "info")

            def get_latest_version():
                response = requests.get(
                    "https://api.github.com/repos/prometheus/node_exporter/releases/latest",
                    timeout=10
                )
                return response.json()['tag_name'].lstrip('v')

            version = await asyncio.to_thread(get_latest_version)
            await self.log(f"Versão mais recente: {version}", "success")

        except Exception as e:
            await self.log(f"Erro ao obter versão: {e}", "error")
            return False

        # Preparar collectors
        if custom_collectors:
            collectors = custom_collectors
        else:
            collectors = NODE_EXPORTER_COLLECTORS[collector_profile]

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

        # Script de instalação
        install_script = f'''#!/bin/bash
set -e
TMP_DIR=$(mktemp -d)
cd "$TMP_DIR"
echo "Baixando Node Exporter v{version}..."
wget -q --show-progress "{url}" || exit 1
echo "Extraindo..."
tar -xzf "node_exporter-{version}.linux-{arch_suffix}.tar.gz"
if [ -f /usr/local/bin/node_exporter ]; then
    echo "Fazendo backup do binário existente..."
    mv /usr/local/bin/node_exporter /usr/local/bin/node_exporter.bak
fi
echo "Instalando binário..."
cp "node_exporter-{version}.linux-{arch_suffix}/node_exporter" /usr/local/bin/
chmod +x /usr/local/bin/node_exporter
if ! id -u node_exporter > /dev/null 2>&1; then
    echo "Criando usuário node_exporter..."
    useradd --no-create-home --shell /bin/false node_exporter
fi
echo "Criando serviço systemd..."
cat > /etc/systemd/system/node_exporter.service << 'EOF'
[Unit]
Description=Node Exporter
Documentation=https://github.com/prometheus/node_exporter
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=node_exporter
Group=node_exporter
ExecStart=/usr/local/bin/node_exporter \\
    --web.listen-address=:9100 \\
    {collector_string} \\
    --collector.filesystem.mount-points-exclude='^/(dev|proc|sys|var/lib/docker/.+)($|/)' \\
    --collector.filesystem.fs-types-exclude='^(autofs|binfmt_misc|bpf|cgroup2?|configfs|debugfs|devpts|devtmpfs|fusectl|hugetlbfs|mqueue|nsfs|overlay|proc|pstore|rpc_pipefs|securityfs|selinuxfs|squashfs|sysfs|tracefs)$'
Restart=always
RestartSec=10s
StandardOutput=journal
StandardError=journal
SyslogIdentifier=node_exporter

[Install]
WantedBy=multi-user.target
EOF
systemctl daemon-reload
systemctl enable node_exporter
systemctl restart node_exporter
sleep 3
if systemctl is-active --quiet node_exporter; then
    echo "SUCCESS"
    if curl -s http://localhost:9100/metrics > /dev/null; then
        echo "METRICS_OK"
    fi
else
    echo "FAILED"
    journalctl -u node_exporter -n 20 --no-pager
    exit 1
fi
cd /
rm -rf "$TMP_DIR"
'''

        # Executar instalação
        await self.log("Executando instalação...", "info")
        await ws_manager.send_progress(10, 100, "Enviando script de instalação...", self.client_id)

        await self.execute_command(f"cat > /tmp/install_ne.sh << 'EOFSCRIPT'\n{install_script}\nEOFSCRIPT")

        await ws_manager.send_progress(30, 100, "Baixando e instalando Node Exporter...", self.client_id)

        exit_code, output, error = await self.execute_command("bash /tmp/install_ne.sh 2>&1")

        await ws_manager.send_progress(90, 100, "Finalizando instalação...", self.client_id)

        if exit_code == 0 and 'SUCCESS' in output:
            await ws_manager.send_progress(100, 100, "Instalação concluída!", self.client_id)
            await self.log(f"Node Exporter v{version} instalado com sucesso!", "success")

            if 'METRICS_OK' in output:
                await self.log("Métricas acessíveis em http://localhost:9100/metrics", "success")

            await self.log(f"Collectors habilitados ({collector_profile}):", "info")
            for col in collectors.get('enable', []):
                desc = NODE_EXPORTER_COLLECTOR_DETAILS.get(col, 'N/A')
                await self.log(f"• {col}: {desc}", "debug")

            await self.execute_command("rm -f /tmp/install_ne.sh")

            return True
        else:
            await self.log("Instalação falhou!", "error")
            await self.log(f"Output: {output}", "debug")
            await self.log(f"Error: {error}", "debug")
            return False

    async def validate_installation(
        self,
        basic_auth_user: Optional[str] = None,
        basic_auth_password: Optional[str] = None
    ) -> bool:
        """Valida instalação com teste opcional de Basic Auth"""
        await self.log("Validando instalação...", "info")

        port = 9100
        service_name = "node_exporter"

        # Verificar serviço
        exit_code, output, _ = await self.execute_command(f"systemctl is-active {service_name}")
        if exit_code == 0 and 'active' in output:
            await self.log(f"Serviço {service_name} está rodando", "success")
        else:
            await self.log(f"Serviço {service_name} não está ativo", "error")
            return False

        # Testar métricas (com Basic Auth se fornecido)
        await self.log("Testando métricas...", "info")
        if basic_auth_user and basic_auth_password:
            await self.log("Testando com credenciais Basic Auth...", "info")
            exit_code, output, _ = await self.execute_command(
                f"curl -s -u {basic_auth_user}:{basic_auth_password} http://localhost:{port}/metrics | head -10"
            )
        else:
            exit_code, output, _ = await self.execute_command(f"curl -s http://localhost:{port}/metrics | head -10")

        if exit_code == 0 and output:
            await self.log("Métricas acessíveis localmente", "success")
            await self.log(f"Primeiras linhas: {output[:200]}...", "debug")
        else:
            await self.log("Métricas não acessíveis", "error")
            return False

        # Testar porta externa
        await self.log("Testando acesso externo...", "info")
        port_accessible = await asyncio.to_thread(test_port, self.host, port, 3)

        if port_accessible:
            await self.log(f"Porta {port} acessível externamente", "success")
        else:
            await self.log(f"Porta {port} pode não estar acessível externamente (verificar firewall)", "warning")

        await self.log("Instalação validada com sucesso!", "success")
        return True

    def close(self):
        """Fecha conexão SSH"""
        if self.ssh_client:
            self.ssh_client.close()
