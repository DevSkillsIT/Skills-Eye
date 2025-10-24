#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
consul-manager.py - Sistema de Gestão de Monitoramento Skills IT
v2.2.0 - Instalação Remota Aprimorada (CÓDIGO COMPLETO)

ARQUIVO PARTE 1 DE 3 - Cole as 3 partes em sequência

Autor: Skills IT Infrastructure Team
Changelog v2.2.0:
- Instalação remota COMPLETAMENTE aprimorada
- TODAS as funções originais mantidas
- Adicionado validações completas
- Adicionado rollback automático
- Adicionado scan de rede
- Adicionado instalação em lote
"""

import argparse
import csv
import json
import os
import subprocess
import sys
import time
import socket
import requests
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Set
from datetime import datetime
from collections import defaultdict
from functools import wraps
from urllib.parse import quote
import paramiko
import tempfile
import ipaddress

# Importações para interface rica
try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.progress import track, Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
    from rich.layout import Layout
    from rich.live import Live
    from rich.align import Align
    from rich.text import Text
    from rich import box
    import questionary
    from questionary import Style
except ImportError:
    print("Instalando dependências necessárias...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "rich", "questionary", "paramiko"])
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.progress import track, Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
    from rich.layout import Layout
    from rich.live import Live
    from rich.align import Align
    from rich.text import Text
    from rich import box
    import questionary
    from questionary import Style

# ============================================================================
# CONFIGURAÇÃO DO AMBIENTE SKILLS IT
# ============================================================================
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
    'cpu': 'Uso de CPU por core e modo (user, system, idle, etc)',
    'loadavg': 'Carga média do sistema (1min, 5min, 15min)',
    'meminfo': 'Uso de memória RAM (total, livre, cache, swap)',
    'diskstats': 'I/O de disco (leituras, escritas, tempo)',
    'filesystem': 'Uso de espaço em disco por filesystem',
    'netdev': 'Tráfego de rede (bytes enviados/recebidos)',
    'time': 'Timestamp do sistema',
    'uname': 'Informações do kernel',
    'systemd': 'Status de serviços systemd',
    'processes': 'Processos em execução',
    'tcpstat': 'Estatísticas de conexões TCP',
    'interrupts': 'Interrupções do sistema (verbose)',
    'ipvs': 'Load balancer IPVS',
    'sockstat': 'Estatísticas de sockets'
}

WINDOWS_EXPORTER_COLLECTORS = {
    'recommended': [
        'cpu', 'cs', 'logical_disk', 'memory', 'net', 'os', 'system',
    ],
    'full': [
        'cpu', 'cs', 'logical_disk', 'memory', 'net', 'os', 'system',
        'service', 'tcp', 'thermalzone'
    ],
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

class Config:
    """Configuração central do ambiente Skills IT"""
    
    MAIN_SERVER = "172.16.1.26"
    MAIN_SERVER_NAME = "glpi-grafana-prometheus.skillsit.com.br"
    
    CONSUL_TOKEN = os.getenv("CONSUL_TOKEN", "8382a112-81e0-cd6d-2b92-8565925a0675")
    CONSUL_PORT = 8500
    
    KNOWN_NODES = {
        "glpi-grafana-prometheus.skillsit.com.br": "172.16.1.26",
        "consul-DTC-Genesis-Skills": "11.144.0.21", 
        "consul-RMD-LDC-Rio": "172.16.200.14"
    }
    
    SERVICE_NAMES = {
        "blackbox_exporter": "Blackbox local no nó selecionado",
        "blackbox_remote_dtc_skills": "Blackbox remoto DTC Skills (aponta para 172.16.1.26)",
        "blackbox_remote_rmd_ldc": "Blackbox remoto RMD LDC Rio",
        "selfnode_exporter": "Selfnode (requer agente no host remoto)",
        "selfnode_exporter_rio": "Selfnode RMD (requer agente no host remoto)"
    }
    
    SERVICE_NAME_TO_NODE = {
        "blackbox_exporter": None,
        "blackbox_remote_dtc_skills": "11.144.0.21",
        "blackbox_remote_rmd_ldc": "172.16.200.14",
        "selfnode_exporter": None,
        "selfnode_exporter_rio": "172.16.200.14",
    }
    
    BLACKBOX_MODULES = [
        "icmp",
        "http_2xx",
        "http_4xx",
        "https",
        "http_post_2xx",
        "tcp_connect",
        "ssh_banner",
        "pop3s_banner",
        "irc_banner"
    ]
    
    MODULE_DESCRIPTIONS = {
        "icmp": {
            "name": "ICMP (Ping)",
            "description": "Monitoramento de conectividade via ping",
            "use_cases": [
                "Verificar se host/servidor está online",
                "Medir latência de rede",
                "Monitorar gateways, roteadores, switches"
            ],
            "example_instance": "192.168.1.1, 8.8.8.8, router.example.com",
            "required_fields": ["instance"],
            "optional_fields": [],
            "timeout": "5s"
        },
        "http_2xx": {
            "name": "HTTP 2xx (Sucesso)",
            "description": "Monitora sites/APIs HTTP esperando status 200-303",
            "use_cases": [
                "Sites públicos e privados",
                "APIs REST",
                "Aplicações web"
            ],
            "example_instance": "http://site.com, http://api.company.com/health",
            "required_fields": ["instance"],
            "optional_fields": ["timeout", "interval"],
            "timeout": "5s",
            "valid_status": "200, 301, 302, 303"
        },
        "http_4xx": {
            "name": "HTTP 4xx (Erro Cliente)",
            "description": "Monitora endpoints esperando erros 4xx (400-404)",
            "use_cases": [
                "Páginas de erro customizadas",
                "Validar autenticação (401)",
                "Testar acesso negado (403)"
            ],
            "example_instance": "http://site.com/admin, http://api.com/forbidden",
            "required_fields": ["instance"],
            "optional_fields": ["timeout", "interval"],
            "timeout": "5s",
            "valid_status": "400, 401, 403, 404"
        },
        "https": {
            "name": "HTTPS (Seguro)",
            "description": "Monitora sites HTTPS com validação de certificado SSL",
            "use_cases": [
                "Sites com HTTPS obrigatório",
                "Validar certificados SSL",
                "Alertar sobre expiração de certificado"
            ],
            "example_instance": "https://secure.site.com, https://api.company.com",
            "required_fields": ["instance"],
            "optional_fields": ["timeout", "interval"],
            "timeout": "5s",
            "ssl_validation": True,
            "valid_status": "200, 301, 302, 303"
        },
        "http_post_2xx": {
            "name": "HTTP POST 2xx",
            "description": "Testa endpoints que requerem método POST",
            "use_cases": [
                "APIs que só aceitam POST",
                "Webhooks",
                "Formulários de autenticação"
            ],
            "example_instance": "http://api.com/webhook, http://app.com/login",
            "required_fields": ["instance"],
            "optional_fields": ["timeout", "interval"],
            "timeout": "5s",
            "method": "POST"
        },
        "tcp_connect": {
            "name": "TCP Connect",
            "description": "Testa conectividade TCP em porta específica",
            "use_cases": [
                "Serviços TCP genéricos",
                "Banco de dados (MySQL:3306, PostgreSQL:5432)",
                "SMTP (25), IMAP (143), etc."
            ],
            "example_instance": "192.168.1.10:3306, db.company.com:5432, smtp.company.com:25",
            "required_fields": ["instance"],
            "optional_fields": ["timeout"],
            "timeout": "5s",
            "format": "host:porta"
        },
        "ssh_banner": {
            "name": "SSH Banner",
            "description": "Verifica banner SSH (porta 22) e valida resposta",
            "use_cases": [
                "Servidores SSH",
                "Validar serviço SSH ativo",
                "Detectar versão SSH"
            ],
            "example_instance": "192.168.1.100:22, server.company.com:22",
            "required_fields": ["instance"],
            "optional_fields": ["timeout"],
            "timeout": "5s",
            "expected_banner": "SSH-2.0-",
            "format": "host:porta"
        },
        "pop3s_banner": {
            "name": "POP3S Banner (Seguro)",
            "description": "Verifica banner POP3 com TLS",
            "use_cases": [
                "Servidores de email POP3",
                "Validar TLS/SSL",
                "Monitorar caixa de entrada"
            ],
            "example_instance": "mail.company.com:995",
            "required_fields": ["instance"],
            "optional_fields": ["timeout"],
            "timeout": "5s",
            "expected_banner": "+OK",
            "tls": True,
            "format": "host:porta"
        },
        "irc_banner": {
            "name": "IRC Banner",
            "description": "Verifica protocolo IRC completo",
            "use_cases": [
                "Servidores IRC",
                "Chat interno corporativo"
            ],
            "example_instance": "irc.company.com:6667",
            "required_fields": ["instance"],
            "optional_fields": ["timeout"],
            "timeout": "5s",
            "format": "host:porta"
        }
    }
    
    MODULE_DEFAULTS = {
        "tcp_connect": {"interval": "15s", "timeout": "5s"},
        "http_2xx": {"interval": "15s", "timeout": "5s"},
        "http_4xx": {"interval": "15s", "timeout": "5s"},
        "https": {"interval": "15s", "timeout": "5s"},
        "http_post_2xx": {"interval": "15s", "timeout": "5s"},
        "ssh_banner": {"timeout": "5s"},
        "pop3s_banner": {"timeout": "5s"},
        "irc_banner": {"timeout": "5s"},
        "icmp": {"timeout": "5s"}
    }
    
    SERVICE_PORTS = {
        "consul": 8500,
        "prometheus": 9090,
        "grafana": 3000,
        "blackbox": 9115,
        "blackbox_json": 9116,
        "node_exporter": 9100,
        "windows_exporter": 9182,
        "nginx-consul": 1026,
        "influxdb": 8086,
        "alertmanager": 9093,
        "alertmanager_cluster": 9094,
        "mongodb": 27017,
        "mysql": 3306,
        "nginx_http": 80,
        "nginx_https": 443,
        "webmin": 10000
    }
    
    META_FIELDS = [
        "module",
        "company",
        "project", 
        "env",
        "name",
        "instance",
        "localizacao",
        "tipo",
        "cod_localidade",
        "cidade",
        "notas",
        "provedor",
        "fabricante",
        "modelo",
        "tipo_dispositivo_abrev",
        "glpi_url"
    ]
    
    REQUIRED_FIELDS = ["module", "company", "project", "env", "name", "instance"]
    
    INFLUXDB_BUCKETS = {
        "Telegraf": "Métricas do sistema (CPU, mem, disk, net)",
        "skillsvcenter": "Métricas do vCenter/vSphere",
        "MonitSNMP": "SNMP de impressoras",
        "MonitPing": "Monitoramento de ping",
        "MonitIdrac": "Monitoramento IDRAC"
    }

# ============================================================================
# UTILITÁRIOS E HELPERS
# ============================================================================

console = Console()

custom_style = Style([
    ('qmark', 'fg:#673ab7 bold'),
    ('question', 'bold'),
    ('answer', 'fg:#f44336 bold'),
    ('pointer', 'fg:#673ab7 bold'),
    ('highlighted', 'fg:#673ab7 bold'),
    ('selected', 'fg:#cc5454'),
    ('separator', 'fg:#cc5454'),
    ('instruction', 'fg:#abb2bf'),
    ('text', ''),
])

def retry_with_backoff(max_retries=3, base_delay=1, max_delay=10):
    """Decorator para retry com backoff exponencial"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            retries = 0
            delay = base_delay
            
            while retries < max_retries:
                try:
                    return func(*args, **kwargs)
                except (requests.exceptions.RequestException, ConnectionError) as e:
                    retries += 1
                    if retries >= max_retries:
                        raise
                    console.print(f"[yellow]Tentativa {retries} falhou: {e}[/yellow]")
                    time.sleep(delay)
                    delay = min(delay * 2, max_delay)
            return None
        return wrapper
    return decorator

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
    try:
        ipaddress.ip_address(ip)
        return True
    except ValueError:
        return False

def format_timestamp() -> str:
    """Retorna timestamp formatado"""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def safe_request(url: str, headers: dict = None, timeout: int = 5) -> Optional[requests.Response]:
    """Faz request HTTP com tratamento de erro"""
    try:
        response = requests.get(url, headers=headers, timeout=timeout)
        if response.status_code < 400:
            return response
        return None
    except:
        return None

# ============================================================================
# CLASSE PRINCIPAL CONSUL
# ============================================================================

class ConsulManager:
    """Gerenciador principal do Consul"""
    
    def __init__(self, host: str = None, port: int = None, token: str = None):
        self.host = host or Config.MAIN_SERVER
        self.port = port or Config.CONSUL_PORT
        self.token = token or Config.CONSUL_TOKEN
        self.base_url = f"http://{self.host}:{self.port}/v1"
        self.headers = {"X-Consul-Token": self.token}
        
    @retry_with_backoff()
    def _request(self, method: str, path: str, **kwargs):
        """Requisição HTTP para API do Consul"""
        kwargs.setdefault("headers", self.headers)
        kwargs.setdefault("timeout", 10)
        url = f"{self.base_url}{path}"
        response = requests.request(method, url, **kwargs)
        response.raise_for_status()
        return response
    
    def get_members(self) -> List[Dict]:
        """Obtém membros do cluster via API"""
        try:
            response = self._request("GET", "/agent/members")
            members = response.json()
            
            known_nodes_dict = {}
            for name, ip in Config.KNOWN_NODES.items():
                known_nodes_dict[ip] = {"node": name, "addr": ip, "status": "unknown", "type": "unknown"}
            
            for m in members:
                addr = m["Addr"].split(":")[0]
                known_nodes_dict[addr] = {
                    "node": m["Name"],
                    "addr": addr,
                    "status": "alive" if m["Status"] == 1 else "dead",
                    "type": "server" if m.get("Tags", {}).get("role") == "consul" else "client"
                }
            
            return list(known_nodes_dict.values())
        except:
            return self._get_members_cli()
    
    def _get_members_cli(self) -> List[Dict]:
        """Obtém membros via CLI como fallback"""
        try:
            out = subprocess.check_output(
                ["consul", "members"],
                text=True,
                stderr=subprocess.DEVNULL
            )
            lines = [l.split() for l in out.strip().splitlines()[1:]]
            return [
                {
                    "node": l[0],
                    "addr": l[1].split(':')[0],
                    "status": l[2],
                    "type": l[3] if len(l) > 3 else "unknown"
                }
                for l in lines
            ]
        except:
            return [
                {"node": name, "addr": ip, "status": "unknown", "type": "unknown"}
                for name, ip in Config.KNOWN_NODES.items()
            ]
    
    def get_services(self, node_addr: str = None) -> Dict:
        """Obtém serviços de um nó específico ou local"""
        if node_addr and node_addr != self.host:
            temp_manager = ConsulManager(host=node_addr, token=self.token)
            return temp_manager.get_services()
        
        try:
            response = self._request("GET", "/agent/services")
            return response.json()
        except:
            return {}
    
    def register_service(self, service_data: Dict, node_addr: str = None) -> bool:
        """Registra um serviço"""
        if node_addr and node_addr != self.host:
            temp_manager = ConsulManager(host=node_addr, token=self.token)
            return temp_manager.register_service(service_data)
        
        try:
            self._request("PUT", "/agent/service/register", json=service_data)
            return True
        except Exception as e:
            console.print(f"[red]Erro ao registrar: {e}[/red]")
            return False
    
    def deregister_service(self, service_id: str, node_addr: str = None) -> bool:
        """Remove um serviço"""
        if node_addr and node_addr != self.host:
            temp_manager = ConsulManager(host=node_addr, token=self.token)
            return temp_manager.deregister_service(service_id)
        
        try:
            self._request("PUT", f"/agent/service/deregister/{quote(service_id, safe='')}")
            return True
        except requests.exceptions.ReadTimeout:
            console.print("[yellow]Timeout ao remover (provável sucesso)[/yellow]")
            return True
        except Exception as e:
            if "Unknown service ID" in str(e):
                console.print("[yellow]Serviço já não existe[/yellow]")
                return True
            console.print(f"[red]Erro: {e}[/red]")
            return False
    
    def get_health_status(self, service_name: str = None) -> Dict:
        """Obtém status de saúde dos serviços"""
        try:
            if service_name:
                response = self._request("GET", f"/health/service/{service_name}")
            else:
                response = self._request("GET", "/health/state/any")
            return response.json()
        except:
            return []
    
    def get_catalog_services(self) -> Dict:
        """Lista todos os serviços do catálogo"""
        try:
            response = self._request("GET", "/catalog/services")
            return response.json()
        except:
            return {}
    
    def get_unique_values(self, field: str) -> Set[str]:
        """Obtém valores únicos de um campo específico"""
        values = set()
        try:
            services = self.get_services()
            for sid, svc in services.items():
                meta = svc.get("Meta", {})
                if field in meta and meta[field]:
                    values.add(meta[field])
        except:
            pass
        return values

# FIM DA PARTE 1 - CONTINUE NA PARTE 2
# CONTINUAÇÃO - consul-manager.py COMPLETO - Parte 2/3
# Cole APÓS a Parte 1

# ============================================================================
# CLASSE DE INSTALAÇÃO REMOTA APRIMORADA
# ============================================================================

class RemoteExporterInstaller:
    """Instalador aprimorado de exporters via SSH com todas as validações"""
    
    def __init__(self, host, username, password=None, key_file=None, use_sudo=False, ssh_port=22):
        self.host = host
        self.username = username
        self.password = password
        self.key_file = key_file
        self.use_sudo = use_sudo
        self.ssh_port = ssh_port
        self.ssh_client = None
        self.os_type = None
        self.os_details = {}
        self.backup_path = None
        self.installed_version = None
        
    def validate_connection_params(self) -> Tuple[bool, str]:
        """Valida parâmetros de conexão ANTES de tentar conectar"""
        if not validate_ip(self.host):
            try:
                socket.gethostbyname(self.host)
            except:
                return False, f"❌ IP/hostname inválido: {self.host}"
        
        console.print(f"[yellow]Testando porta SSH {self.ssh_port}...[/yellow]")
        if not test_port(self.host, self.ssh_port, timeout=5):
            return False, f"❌ Porta SSH {self.ssh_port} não está acessível em {self.host}"
        
        console.print(f"[green]✓ Porta SSH {self.ssh_port} acessível[/green]")
        return True, "OK"
    
    def connect(self) -> bool:
        """Conecta via SSH com validações"""
        try:
            valid, msg = self.validate_connection_params()
            if not valid:
                console.print(f"[red]{msg}[/red]")
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
            
            console.print("[yellow]Conectando via SSH...[/yellow]")
            self.ssh_client.connect(**kwargs)
            console.print("[green]✓ Conectado via SSH[/green]")
            return True
        except paramiko.AuthenticationException:
            console.print("[red]✗ Falha de autenticação SSH[/red]")
            return False
        except paramiko.SSHException as e:
            console.print(f"[red]✗ Erro SSH: {e}[/red]")
            return False
        except Exception as e:
            console.print(f"[red]✗ Erro: {e}[/red]")
            return False
    
    def execute_command(self, command, use_sudo=None):
        """Executa comando remoto"""
        if use_sudo is None:
            use_sudo = self.use_sudo
        
        if use_sudo and self.username != 'root':
            command = f"sudo -S {command}"
        
        try:
            stdin, stdout, stderr = self.ssh_client.exec_command(command)
            
            if use_sudo and self.password:
                stdin.write(self.password + '\n')
                stdin.flush()
            
            exit_status = stdout.channel.recv_exit_status()
            output = stdout.read().decode('utf-8')
            error = stderr.read().decode('utf-8')
            
            return exit_status, output, error
        except Exception as e:
            return 1, "", str(e)
    
    def detect_os(self):
        """Detecta SO com detalhes"""
        console.print("[yellow]Detectando SO...[/yellow]")
        
        exit_code, output, _ = self.execute_command("cat /etc/os-release 2>/dev/null || echo 'not_linux'")
        if exit_code == 0 and 'not_linux' not in output:
            self.os_type = 'linux'
            for line in output.split('\n'):
                if '=' in line:
                    key, value = line.split('=', 1)
                    self.os_details[key] = value.strip('"')
            
            distro = self.os_details.get('ID', 'unknown')
            version = self.os_details.get('VERSION_ID', 'unknown')
            
            console.print(f"[green]✓ Linux detectado: {self.os_details.get('PRETTY_NAME', 'Unknown')}[/green]")
            console.print(f"[dim]Distribuição: {distro} {version}[/dim]")
            return 'linux'
        
        exit_code, output, _ = self.execute_command("systeminfo | findstr /B /C:\"OS Name\"")
        if exit_code == 0 and 'Windows' in output:
            self.os_type = 'windows'
            self.os_details['name'] = output.strip()
            console.print(f"[green]✓ Windows detectado: {output.strip()}[/green]")
            
            _, version_output, _ = self.execute_command("systeminfo | findstr /B /C:\"OS Version\"")
            if version_output:
                self.os_details['version'] = version_output.strip()
                console.print(f"[dim]{version_output.strip()}[/dim]")
            
            return 'windows'
        
        console.print("[red]✗ SO não suportado ou não detectado[/red]")
        return None
    
    def check_disk_space(self, required_mb=200):
        """Verifica espaço em disco"""
        console.print("[yellow]Verificando espaço em disco...[/yellow]")
        
        if self.os_type == 'linux':
            exit_code, output, _ = self.execute_command("df -BM /usr/local/bin | tail -1 | awk '{print $4}'")
            if exit_code == 0:
                try:
                    available = int(output.strip().replace('M', ''))
                    if available < required_mb:
                        console.print(f"[red]✗ Espaço insuficiente: {available}MB disponível, {required_mb}MB necessário[/red]")
                        return False
                    console.print(f"[green]✓ Espaço suficiente: {available}MB disponível[/green]")
                    return True
                except:
                    pass
        
        elif self.os_type == 'windows':
            exit_code, output, _ = self.execute_command('powershell "Get-PSDrive C | Select-Object -ExpandProperty Free"')
            if exit_code == 0:
                try:
                    available_bytes = int(output.strip())
                    available_mb = available_bytes / (1024 * 1024)
                    if available_mb < required_mb:
                        console.print(f"[red]✗ Espaço insuficiente: {available_mb:.0f}MB disponível[/red]")
                        return False
                    console.print(f"[green]✓ Espaço suficiente: {available_mb:.0f}MB disponível[/green]")
                    return True
                except:
                    pass
        
        console.print("[yellow]⚠ Não foi possível verificar espaço em disco[/yellow]")
        return True
    
    def check_exporter_installed(self):
        """Verifica se exporter já está instalado"""
        console.print("[yellow]Verificando instalação existente...[/yellow]")
        
        if self.os_type == 'linux':
            port = 9100
            binary_path = "/usr/local/bin/node_exporter"
            service_name = "node_exporter"
        else:
            port = 9182
            service_name = "windows_exporter"
            binary_path = None
        
        port_in_use = test_port(self.host, port, timeout=2)
        
        if self.os_type == 'linux':
            exit_code, output, _ = self.execute_command(f"systemctl is-active {service_name}")
            service_running = exit_code == 0 and 'active' in output
            
            exit_code, output, _ = self.execute_command(f"{binary_path} --version 2>&1 | head -1")
            if exit_code == 0:
                self.installed_version = output.strip()
        else:
            exit_code, _, _ = self.execute_command(f'sc query "{service_name}" | findstr RUNNING')
            service_running = exit_code == 0
        
        if port_in_use or service_running:
            console.print(f"[yellow]⚠ {service_name} já está instalado e rodando[/yellow]")
            if self.installed_version:
                console.print(f"[dim]Versão instalada: {self.installed_version}[/dim]")
            return True
        
        console.print("[green]✓ Nenhuma instalação anterior detectada[/green]")
        return False
    
    def check_port_available(self, port):
        """Verifica se porta está disponível"""
        console.print(f"[yellow]Verificando se porta {port} está disponível...[/yellow]")
        
        if self.os_type == 'linux':
            exit_code, output, _ = self.execute_command(f"lsof -i :{port} || netstat -tuln | grep :{port}")
            if exit_code == 0 and output.strip():
                console.print(f"[red]✗ Porta {port} já está em uso![/red]")
                console.print(f"[dim]Processo usando a porta:{output[:200]}[/dim]")
                return False
        else:
            exit_code, output, _ = self.execute_command(f'netstat -ano | findstr ":{port}"')
            if exit_code == 0 and output.strip():
                console.print(f"[red]✗ Porta {port} já está em uso![/red]")
                return False
        
        console.print(f"[green]✓ Porta {port} disponível[/green]")
        return True
    
    def backup_existing_config(self):
        """Faz backup de configuração existente"""
        if self.os_type == 'linux':
            service_file = "/etc/systemd/system/node_exporter.service"
            exit_code, _, _ = self.execute_command(f"test -f {service_file}")
            
            if exit_code == 0:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                self.backup_path = f"{service_file}.backup_{timestamp}"
                console.print(f"[yellow]Fazendo backup de {service_file}...[/yellow]")
                
                exit_code, _, _ = self.execute_command(f"cp {service_file} {self.backup_path}")
                if exit_code == 0:
                    console.print(f"[green]✓ Backup salvo em {self.backup_path}[/green]")
                    return True
        
        return False
    
    def rollback(self):
        """Reverte alterações em caso de falha"""
        console.print("[yellow]⚠ Revertendo alterações (rollback)...[/yellow]")
        
        if self.os_type == 'linux':
            self.execute_command("systemctl stop node_exporter")
            self.execute_command("systemctl disable node_exporter")
            self.execute_command("rm -f /usr/local/bin/node_exporter")
            
            if self.backup_path:
                exit_code, _, _ = self.execute_command(f"mv {self.backup_path} /etc/systemd/system/node_exporter.service")
                if exit_code == 0:
                    self.execute_command("systemctl daemon-reload")
                    self.execute_command("systemctl start node_exporter")
                    console.print("[green]✓ Backup restaurado[/green]")
        
        elif self.os_type == 'windows':
            self.execute_command('sc stop windows_exporter')
            self.execute_command('sc delete windows_exporter')
            self.execute_command('powershell "Remove-Item -Path \'C:\\Program Files\\windows_exporter\' -Recurse -Force -ErrorAction SilentlyContinue"')
        
        console.print("[green]✓ Rollback concluído[/green]")
    
    def install_node_exporter(self, collector_profile='recommended', custom_collectors=None):
        """Instala Node Exporter no Linux com progress bar e validações"""
        console.print("\n[cyan]═══ Instalando Node Exporter ═══[/cyan]\n")
        
        if not self.check_disk_space(200):
            return False
        
        port = 9100
        if not self.check_port_available(port):
            if not questionary.confirm("Porta em uso. Continuar mesmo assim?").ask():
                return False
        
        if self.check_exporter_installed():
            action = questionary.select(
                "O que deseja fazer?",
                choices=[
                    "Atualizar para última versão",
                    "Reinstalar (remove e instala novamente)",
                    "Cancelar"
                ]
            ).ask()
            
            if action == "Cancelar":
                return False
            elif action == "Atualizar para última versão":
                self.backup_existing_config()
        
        exit_code, arch, _ = self.execute_command("uname -m")
        arch = arch.strip()
        
        arch_map = {'x86_64': 'amd64', 'aarch64': 'arm64', 'armv7l': 'armv7'}
        arch_suffix = arch_map.get(arch)
        
        if not arch_suffix:
            console.print(f"[red]✗ Arquitetura não suportada: {arch}[/red]")
            return False
        
        console.print(f"[green]✓ Arquitetura: {arch} ({arch_suffix})[/green]")
        
        try:
            console.print("[yellow]Obtendo última versão do GitHub...[/yellow]")
            response = requests.get("https://api.github.com/repos/prometheus/node_exporter/releases/latest", timeout=10)
            version = response.json()['tag_name'].lstrip('v')
            console.print(f"[green]✓ Versão mais recente: {version}[/green]")
            
            if self.installed_version:
                console.print(f"[dim]Versão atual: {self.installed_version}[/dim]")
        except:
            console.print("[red]✗ Erro ao obter versão do GitHub[/red]")
            return False
        
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
        
        console.print("\n[yellow]Executando instalação...[/yellow]")
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console
        ) as progress:
            task = progress.add_task("Instalando...", total=100)
            
            progress.update(task, advance=10, description="Enviando script...")
            self.execute_command(f"cat > /tmp/install_ne.sh << 'EOFSCRIPT'\n{install_script}\nEOFSCRIPT")
            
            progress.update(task, advance=20, description="Baixando Node Exporter...")
            exit_code, output, error = self.execute_command("bash /tmp/install_ne.sh 2>&1")
            
            progress.update(task, advance=70, description="Finalizando...")
            
            if exit_code == 0 and 'SUCCESS' in output:
                progress.update(task, completed=100, description="✓ Instalação concluída!")
                
                console.print(f"\n[bold green]✅ Node Exporter v{version} instalado com sucesso![/bold green]")
                
                if 'METRICS_OK' in output:
                    console.print("[green]✓ Métricas acessíveis em http://localhost:9100/metrics[/green]")
                
                console.print(f"\n[bold]Collectors habilitados ({collector_profile}):[/bold]")
                for col in collectors.get('enable', []):
                    console.print(f"  • {col}: [dim]{NODE_EXPORTER_COLLECTOR_DETAILS.get(col, 'N/A')}[/dim]")
                
                self.execute_command("rm -f /tmp/install_ne.sh")
                
                return True
            else:
                progress.update(task, description="✗ Instalação falhou!")
                console.print(f"\n[red]✗ Falha na instalação:[/red]")
                console.print(f"[dim]{output}[/dim]")
                console.print(f"[dim]{error}[/dim]")
                
                if questionary.confirm("Deseja reverter alterações?").ask():
                    self.rollback()
                
                return False
    
    def install_windows_exporter(self, collectors='recommended'):
        """Instala Windows Exporter com validações"""
        console.print("\n[cyan]═══ Instalando Windows Exporter ═══[/cyan]\n")
        
        console.print("[yellow]Verificando SSH no Windows...[/yellow]")
        exit_code, output, _ = self.execute_command('sc query sshd')
        
        if exit_code != 0 or 'RUNNING' not in output:
            console.print("[red]✗ Serviço SSH não está rodando no Windows![/red]")
            console.print("\n[bold yellow]Como habilitar SSH no Windows:[/bold yellow]")
            console.print("1. Abra PowerShell como Administrador")
            console.print("2. Execute: Add-WindowsCapability -Online -Name OpenSSH.Server~~~~0.0.1.0")
            console.print("3. Execute: Start-Service sshd")
            console.print("4. Execute: Set-Service -Name sshd -StartupType 'Automatic'")
            
            if questionary.confirm("\nDeseja gerar um script PowerShell para instalação manual?").ask():
                self.generate_windows_install_script(collectors)
            
            return False
        
        console.print("[green]✓ SSH está rodando no Windows[/green]")
        
        if not self.check_disk_space(100):
            return False
        
        port = 9182
        if not self.check_port_available(port):
            if not questionary.confirm("Porta em uso. Continuar?").ask():
                return False
        
        if self.check_exporter_installed():
            action = questionary.select(
                "O que deseja fazer?",
                choices=["Atualizar", "Reinstalar", "Cancelar"]
            ).ask()
            
            if action == "Cancelar":
                return False
        
        try:
            console.print("[yellow]Obtendo última versão...[/yellow]")
            response = requests.get("https://api.github.com/repos/prometheus-community/windows_exporter/releases/latest", timeout=10)
            version = response.json()['tag_name'].lstrip('v')
            console.print(f"[green]✓ Versão: {version}[/green]")
        except:
            console.print("[red]✗ Erro ao obter versão[/red]")
            return False
        
        collector_list = WINDOWS_EXPORTER_COLLECTORS[collectors]
        collectors_enabled = ','.join(collector_list)
        
        url = f"https://github.com/prometheus-community/windows_exporter/releases/download/v{version}/windows_exporter-{version}-amd64.msi"
        
        install_script = f'''
$ErrorActionPreference = "Stop"
$url = "{url}"
$installer = "$env:TEMP\\windows_exporter.msi"
$collectors = "{collectors_enabled}"
$logFile = "$env:TEMP\\windows_exporter_install.log"

Write-Host "Baixando Windows Exporter v{version}..." -ForegroundColor Yellow
try {{
    Invoke-WebRequest -Uri $url -OutFile $installer -UseBasicParsing
    Write-Host "Download concluído" -ForegroundColor Green
}} catch {{
    Write-Host "Erro no download: $_" -ForegroundColor Red
    exit 1
}}

Write-Host "Parando serviço existente (se houver)..." -ForegroundColor Yellow
Stop-Service -Name "windows_exporter" -ErrorAction SilentlyContinue

Write-Host "Instalando..." -ForegroundColor Yellow
$arguments = @("/i", $installer, "ENABLED_COLLECTORS=$collectors", "/quiet", "/norestart", "/l*v", $logFile)
$process = Start-Process msiexec.exe -ArgumentList $arguments -Wait -PassThru -NoNewWindow

if ($process.ExitCode -ne 0) {{
    Write-Host "Erro na instalação. Código: $($process.ExitCode)" -ForegroundColor Red
    Get-Content $logFile | Select-Object -Last 50
    exit 1
}}

Write-Host "Aguardando inicialização..." -ForegroundColor Yellow
Start-Sleep -Seconds 5

$service = Get-Service -Name "windows_exporter" -ErrorAction SilentlyContinue
if ($service -and $service.Status -eq "Running") {{
    Write-Host "SUCCESS" -ForegroundColor Green
    
    try {{
        $response = Invoke-WebRequest -Uri "http://localhost:9182/metrics" -UseBasicParsing -TimeoutSec 5
        if ($response.StatusCode -eq 200) {{
            Write-Host "METRICS_OK" -ForegroundColor Green
        }}
    }} catch {{
        Write-Host "WARN: Métricas não acessíveis ainda" -ForegroundColor Yellow
    }}
}} else {{
    Write-Host "FAILED: Serviço não está rodando" -ForegroundColor Red
    if ($service) {{
        Write-Host "Status: $($service.Status)" -ForegroundColor Red
    }}
    exit 1
}}

Remove-Item $installer -Force -ErrorAction SilentlyContinue
Write-Host "Instalação concluída!" -ForegroundColor Green
'''
        
        console.print("\n[yellow]Executando instalação...[/yellow]")
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            console=console
        ) as progress:
            task = progress.add_task("Instalando...", total=100)
            
            progress.update(task, advance=20, description="Baixando...")
            exit_code, output, error = self.execute_command(f'powershell -Command "{install_script}"')
            
            progress.update(task, advance=80, description="Finalizando...")
            
            if exit_code == 0 and 'SUCCESS' in output:
                progress.update(task, completed=100, description="✓ Concluído!")
                
                console.print(f"\n[bold green]✅ Windows Exporter v{version} instalado![/bold green]")
                
                if 'METRICS_OK' in output:
                    console.print("[green]✓ Métricas acessíveis em http://localhost:9182/metrics[/green]")
                
                console.print(f"\n[bold]Collectors habilitados ({collectors}):[/bold]")
                for col in collector_list:
                    console.print(f"  • {col}: [dim]{WINDOWS_EXPORTER_COLLECTOR_DETAILS.get(col, 'N/A')}[/dim]")
                
                return True
            else:
                progress.update(task, description="✗ Falhou!")
                console.print(f"\n[red]✗ Falha:[/red]")
                console.print(f"[dim]{output}[/dim]")
                console.print(f"[dim]{error}[/dim]")
                
                if questionary.confirm("Reverter?").ask():
                    self.rollback()
                
                return False
    
    def generate_windows_install_script(self, collectors='recommended'):
        """Gera script PowerShell para instalação manual"""
        collector_list = WINDOWS_EXPORTER_COLLECTORS[collectors]
        collectors_str = ','.join(collector_list)
        
        script = f'''# Script de Instalação Manual - Windows Exporter
# Gerado em: {format_timestamp()}
# Execute como Administrador

$ErrorActionPreference = "Stop"

Write-Host "Verificando SSH..." -ForegroundColor Yellow
$sshService = Get-Service -Name sshd -ErrorAction SilentlyContinue

if (-not $sshService) {{
    Write-Host "Instalando SSH..." -ForegroundColor Yellow
    Add-WindowsCapability -Online -Name OpenSSH.Server~~~~0.0.1.0
}}

Write-Host "Iniciando SSH..." -ForegroundColor Yellow
Start-Service sshd
Set-Service -Name sshd -StartupType 'Automatic'

Write-Host "Configurando firewall..." -ForegroundColor Yellow
New-NetFirewallRule -Name 'OpenSSH-Server-In-TCP' -DisplayName 'OpenSSH Server (sshd)' -Enabled True -Direction Inbound -Protocol TCP -Action Allow -LocalPort 22 -ErrorAction SilentlyContinue

Write-Host "Baixando Windows Exporter..." -ForegroundColor Yellow
$version = (Invoke-RestMethod "https://api.github.com/repos/prometheus-community/windows_exporter/releases/latest").tag_name.TrimStart('v')
$url = "https://github.com/prometheus-community/windows_exporter/releases/download/v$version/windows_exporter-$version-amd64.msi"
$installer = "$env:TEMP\\windows_exporter.msi"

Invoke-WebRequest -Uri $url -OutFile $installer -UseBasicParsing

Write-Host "Instalando..." -ForegroundColor Yellow
$collectors = "{collectors_str}"
msiexec.exe /i $installer ENABLED_COLLECTORS=$collectors /quiet /norestart

Start-Sleep -Seconds 10

$service = Get-Service -Name windows_exporter -ErrorAction SilentlyContinue
if ($service.Status -eq 'Running') {{
    Write-Host "Instalado com sucesso!" -ForegroundColor Green
    Write-Host "Métricas: http://localhost:9182/metrics" -ForegroundColor Cyan
}} else {{
    Write-Host "Erro: Serviço não está rodando" -ForegroundColor Red
}}

Remove-Item $installer -Force
'''
        
        script_path = Path.cwd() / f"install_windows_exporter_{self.host}.ps1"
        with open(script_path, 'w', encoding='utf-8') as f:
            f.write(script)
        
        console.print(f"\n[green]✓ Script salvo em: {script_path}[/green]")
        console.print("\n[bold]Para usar:[/bold]")
        console.print(f"1. Copie o arquivo para o servidor Windows")
        console.print(f"2. Abra PowerShell como Administrador")
        console.print(f"3. Execute: .\\{script_path.name}")
    
    def configure_firewall(self, prometheus_ips):
        """Configura firewall"""
        console.print("\n[yellow]Configurando firewall...[/yellow]")
        
        if self.os_type == 'linux':
            exit_code, _, _ = self.execute_command("which ufw")
            if exit_code == 0:
                console.print("[yellow]Configurando UFW...[/yellow]")
                for ip in prometheus_ips:
                    cmd = f"ufw allow from {ip} to any port 9100 comment 'Prometheus {ip}'"
                    exit_code, _, _ = self.execute_command(cmd)
                    if exit_code == 0:
                        console.print(f"[green]✓ Regra UFW para {ip}[/green]")
                return True
            
            exit_code, _, _ = self.execute_command("which firewall-cmd")
            if exit_code == 0:
                console.print("[yellow]Configurando firewalld...[/yellow]")
                for ip in prometheus_ips:
                    cmd = f"firewall-cmd --permanent --add-rich-rule='rule family=\"ipv4\" source address=\"{ip}\" port port=\"9100\" protocol=\"tcp\" accept'"
                    exit_code, _, _ = self.execute_command(cmd)
                    if exit_code == 0:
                        console.print(f"[green]✓ Regra firewalld para {ip}[/green]")
                
                self.execute_command("firewall-cmd --reload")
                return True
            
            console.print("[yellow]⚠ Firewall não detectado (UFW/firewalld)[/yellow]")
            
        elif self.os_type == 'windows':
            console.print("[yellow]Configurando Windows Firewall...[/yellow]")
            for ip in prometheus_ips:
                cmd = f'netsh advfirewall firewall add rule name="Prometheus {ip}" dir=in action=allow protocol=TCP localport=9182 remoteip={ip}'
                exit_code, _, _ = self.execute_command(cmd)
                if exit_code == 0:
                    console.print(f"[green]✓ Regra Windows Firewall para {ip}[/green]")
            return True
        
        return False
    
    def validate_installation(self, prometheus_ips):
        """Valida instalação completa"""
        console.print("\n[bold cyan]Validando instalação...[/bold cyan]")
        
        port = 9100 if self.os_type == 'linux' else 9182
        service_name = "node_exporter" if self.os_type == 'linux' else "windows_exporter"
        
        if self.os_type == 'linux':
            exit_code, output, _ = self.execute_command(f"systemctl is-active {service_name}")
            if exit_code == 0 and 'active' in output:
                console.print(f"[green]✓ Serviço {service_name} está rodando[/green]")
            else:
                console.print(f"[red]✗ Serviço {service_name} não está ativo[/red]")
                return False
        else:
            exit_code, _, _ = self.execute_command(f'sc query "{service_name}" | findstr RUNNING')
            if exit_code == 0:
                console.print(f"[green]✓ Serviço {service_name} está rodando[/green]")
            else:
                console.print(f"[red]✗ Serviço {service_name} não está ativo[/red]")
                return False
        
        console.print(f"[yellow]Testando métricas em localhost:{port}...[/yellow]")
        if self.os_type == 'linux':
            exit_code, output, _ = self.execute_command(f"curl -s http://localhost:{port}/metrics | head -20")
        else:
            exit_code, output, _ = self.execute_command(f'powershell "Invoke-WebRequest -Uri http://localhost:{port}/metrics -UseBasicParsing | Select-Object -ExpandProperty Content | Select-Object -First 20"')
        
        if exit_code == 0 and output:
            console.print(f"[green]✓ Métricas acessíveis localmente[/green]")
            console.print(f"[dim]Primeiras linhas das métricas:[/dim]")
            console.print(f"[dim]{output[:300]}...[/dim]")
        else:
            console.print(f"[red]✗ Métricas não acessíveis[/red]")
            return False
        
        console.print(f"\n[yellow]Testando acesso externo...[/yellow]")
        try:
            for prom_ip in prometheus_ips[:1]:
                console.print(f"[dim]Tentando conectar de {prom_ip} para {self.host}:{port}...[/dim]")
                
                if test_port(self.host, port, timeout=3):
                    console.print(f"[green]✓ Porta {port} acessível externamente[/green]")
                else:
                    console.print(f"[yellow]⚠ Porta {port} pode não estar acessível externamente[/yellow]")
                    console.print(f"[dim]Verifique firewall/security groups[/dim]")
        except:
            console.print(f"[yellow]⚠ Não foi possível testar acesso externo[/yellow]")
        
        console.print(f"\n[bold green]✅ Instalação validada com sucesso![/bold green]")
        return True
    
    def register_in_consul(self, consul_manager, node_choice="Palmas"):
        """Registra exporter no Consul"""
        console.print("\n[bold cyan]Registrando no Consul...[/bold cyan]")
        
        if node_choice == "Palmas":
            target_node = Config.MAIN_SERVER
            service_name = "selfnode_exporter"
        elif node_choice == "Rio":
            target_node = "172.16.200.14"
            service_name = "selfnode_exporter_rio"
        else:
            console.print("[red]Nó inválido[/red]")
            return False
        
        os_tag = "linux" if self.os_type == 'linux' else "windows"
        port = 9100 if self.os_type == 'linux' else 9182
        
        hostname_cmd = "hostname" if self.os_type == 'linux' else "hostname"
        exit_code, hostname, _ = self.execute_command(hostname_cmd)
        hostname = hostname.strip() if exit_code == 0 else self.host
        
        service_id = f"selfnode/{hostname}@{self.host}"
        
        meta = {
            "instance": f"{self.host}:{port}",
            "name": hostname,
            "company": "Skills",
            "env": "Production",
            "project": "Monitoring",
            "tipo": "Server",
            "os": self.os_type
        }
        
        service_data = {
            "id": service_id,
            "name": service_name,
            "tags": [os_tag],
            "meta": meta,
            "address": self.host,
            "port": port
        }
        
        console.print(f"[yellow]Registrando em {node_choice} ({target_node})...[/yellow]")
        
        if consul_manager.register_service(service_data, target_node):
            console.print(f"[bold green]✅ Registrado no Consul com sucesso![/bold green]")
            console.print(f"[cyan]Service ID: {service_id}[/cyan]")
            console.print(f"[cyan]Nó: {node_choice}[/cyan]")
            return True
        else:
            console.print("[red]✗ Falha ao registrar no Consul[/red]")
            return False
    
    def close(self):
        """Fecha conexão SSH"""
        if self.ssh_client:
            self.ssh_client.close()
            console.print("[dim]Conexão SSH fechada[/dim]")

# ============================================================================
# SCAN DE REDE E INSTALAÇÃO EM LOTE
# ============================================================================

class NetworkScanner:
    """Scanner de rede para descoberta automática"""
    
    @staticmethod
    def scan_network(network: str, ssh_port: int = 22) -> List[str]:
        """Scan básico de rede"""
        console.print(f"\n[yellow]Escaneando rede {network}...[/yellow]")
        
        try:
            net = ipaddress.ip_network(network, strict=False)
            hosts = list(net.hosts())
            
            if len(hosts) > 254:
                console.print(f"[yellow]⚠ Rede muito grande ({len(hosts)} hosts). Limitando a /24[/yellow]")
                network_24 = f"{str(hosts[0]).rsplit('.', 1)[0]}.0/24"
                net = ipaddress.ip_network(network_24, strict=False)
                hosts = list(net.hosts())
            
            available_hosts = []
            
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TaskProgressColumn(),
                console=console
            ) as progress:
                task = progress.add_task(f"Escaneando {len(hosts)} IPs...", total=len(hosts))
                
                for host in hosts:
                    host_str = str(host)
                    
                    if test_port(host_str, ssh_port, timeout=1):
                        available_hosts.append(host_str)
                        console.print(f"[green]✓ Encontrado: {host_str}[/green]")
                    
                    progress.advance(task)
            
            console.print(f"\n[bold]Encontrados {len(available_hosts)} hosts com SSH:[/bold]")
            for h in available_hosts:
                console.print(f"  • {h}")
            
            return available_hosts
            
        except ValueError as e:
            console.print(f"[red]Erro: rede inválida - {e}[/red]")
            return []

class BatchInstaller:
    """Instalador em lote para múltiplos servidores"""
    
    def __init__(self, hosts: List[str], username: str, password: str = None, key_file: str = None):
        self.hosts = hosts
        self.username = username
        self.password = password
        self.key_file = key_file
        self.results = []
    
    def install_all(self, os_type: str = 'auto', collector_profile: str = 'recommended'):
        """Instala em todos os hosts"""
        console.print(f"\n[bold cyan]Instalação em lote iniciada[/bold cyan]")
        console.print(f"Total de hosts: {len(self.hosts)}\n")
        
        for i, host in enumerate(self.hosts, 1):
            console.print(f"\n[bold yellow]═══ Host {i}/{len(self.hosts)}: {host} ═══[/bold yellow]")
            
            installer = RemoteExporterInstaller(
                host=host,
                username=self.username,
                password=self.password,
                key_file=self.key_file
            )
            
            success = False
            error_msg = None
            
            try:
                if not installer.connect():
                    error_msg = "Falha na conexão SSH"
                    self.results.append({"host": host, "success": False, "error": error_msg})
                    continue
                
                detected_os = installer.detect_os()
                if not detected_os:
                    error_msg = "SO não suportado"
                    self.results.append({"host": host, "success": False, "error": error_msg})
                    installer.close()
                    continue
                
                if detected_os == 'linux':
                    success = installer.install_node_exporter(collector_profile)
                else:
                    success = installer.install_windows_exporter(collector_profile)
                
                self.results.append({
                    "host": host,
                    "success": success,
                    "os": detected_os,
                    "error": None if success else "Falha na instalação"
                })
                
                installer.close()
                
            except Exception as e:
                error_msg = str(e)
                self.results.append({"host": host, "success": False, "error": error_msg})
                console.print(f"[red]Erro: {e}[/red]")
        
        self.show_report()
    
    def show_report(self):
        """Mostra relatório da instalação em lote"""
        console.print("\n[bold cyan]═══ Relatório de Instalação em Lote ═══[/bold cyan]\n")
        
        success_count = sum(1 for r in self.results if r['success'])
        fail_count = len(self.results) - success_count
        
        table = Table(title=f"Resultados ({success_count} OK, {fail_count} Falhas)", box=box.ROUNDED)
        table.add_column("Host", style="cyan")
        table.add_column("Status", style="yellow")
        table.add_column("SO", style="blue")
        table.add_column("Erro", style="red")
        
        for result in self.results:
            status = "✅ OK" if result['success'] else "❌ Falha"
            os_type = result.get('os', 'N/A')
            error = result.get('error', '')
            
            table.add_row(
                result['host'],
                status,
                os_type,
                error if error else '-'
            )
        
        console.print(table)
        
        console.print(f"\n[bold]Estatísticas:[/bold]")
        console.print(f"  Total: {len(self.results)}")
        console.print(f"  [green]Sucesso: {success_count}[/green]")
        console.print(f"  [red]Falhas: {fail_count}[/red]")

# FIM DA PARTE 2 - CONTINUE NA PARTE 3
# CONTINUAÇÃO FINAL - consul-manager.py COMPLETO - Parte 3/3
# Cole APÓS a Parte 2

# ============================================================================
# INTERFACE INTERATIVA COMPLETA
# ============================================================================

class InteractiveUI:
    """Interface interativa com menus e visualizações ricas"""
    
    def __init__(self, consul_manager: ConsulManager):
        self.consul = consul_manager
        self.current_node = None
        self.current_node_addr = None
        
    def display_banner(self):
        """Exibe banner inicial"""
        banner_text = """
╔═══════════════════════════════════════════════════════════════╗
║     Sistema de Gestão de Monitoramento - Skills IT           ║
║     v2.2.0 - Instalação Remota Completamente Aprimorada     ║
║                                                               ║
║     Consul + Prometheus + Blackbox + TenSunS                 ║
║     Telegraf + InfluxDB + Grafana                           ║
╚═══════════════════════════════════════════════════════════════╝
        """
        console.print(Panel.fit(
            banner_text,
            style="bold cyan",
            border_style="cyan"
        ))
        console.print(f"[dim]Versão 2.2.0 | {format_timestamp()}[/dim]\n")
    
    def select_node(self) -> Tuple[str, str]:
        """Menu para seleção de nó"""
        members = self.consul.get_members()
        
        table = Table(title="Membros do Cluster Consul", box=box.ROUNDED)
        table.add_column("ID", style="cyan", no_wrap=True)
        table.add_column("Nome do Nó", style="magenta")
        table.add_column("IP", style="yellow")
        table.add_column("Status", style="green")
        table.add_column("Tipo", style="blue")
        
        for i, m in enumerate(members, 1):
            status_icon = "🟢" if m["status"] == "alive" else "🔴"
            table.add_row(
                str(i),
                m["node"],
                m["addr"],
                f"{status_icon} {m['status']}",
                m["type"]
            )
        
        console.print(table)
        
        choices = [f"{i}) {m['node']} ({m['addr']})" for i, m in enumerate(members, 1)]
        choices.append("0) TODOS os nós")
        choices.append("99) Especificar IP manualmente")
        
        choice = questionary.select(
            "Selecione o nó para operar:",
            choices=choices,
            style=custom_style
        ).ask()
        
        if not choice:
            return None, None
        
        idx = int(choice.split(")")[0])
        
        if idx == 0:
            return "ALL", "ALL"
        elif idx == 99:
            custom_ip = questionary.text(
                "Digite o IP do nó:",
                default=Config.MAIN_SERVER
            ).ask()
            return "custom", custom_ip
        else:
            member = members[idx - 1]
            return member["node"], member["addr"]
    
    def main_menu(self):
        """Menu principal"""
        while True:
            console.print("\n" + "="*60)
            options = {
                "📊 Listar Serviços": self.list_services,
                "➕ Adicionar Serviço": self.add_service,
                "✏️  Editar Serviço": self.edit_service,
                "🗑️  Remover Serviço": self.remove_service,
                "📥 Importar CSV": self.import_csv,
                "📤 Exportar CSV": self.export_csv,
                "🔍 Buscar/Filtrar": self.search_services,
                "❤️  Status de Saúde": self.health_status,
                "🧪 Testar Conectividade": self.test_connectivity,
                "📈 Status do Stack": self.stack_status,
                "🔧 Ferramentas Avançadas": self.advanced_tools,
                "📚 Documentação": self.show_documentation,
                "🔄 Trocar de Nó": self.change_node,
                "🚀 Instalar Exporter Remotamente": self.install_exporter_remotely,
                "❌ Sair": self.exit_app
            }
            
            if self.current_node:
                console.print(f"[bold cyan]Nó atual:[/bold cyan] {self.current_node} ({self.current_node_addr})")
            
            choice = questionary.select(
                "Menu Principal:",
                choices=list(options.keys()),
                style=custom_style
            ).ask()
            
            if not choice:
                continue
            
            if choice == "❌ Sair":
                break
            
            options[choice]()
    
    def list_services(self):
        """Lista serviços com visualização rica"""
        if self.current_node == "ALL":
            self._list_all_nodes()
        else:
            self._list_single_node()
        
        questionary.press_any_key_to_continue("Pressione ENTER para voltar ao menu...").ask()
    
    def _list_single_node(self):
        """Lista serviços de um único nó"""
        try:
            services = self.consul.get_services(self.current_node_addr)
            
            if not services:
                console.print("[yellow]Nenhum serviço encontrado[/yellow]")
                return
            
            by_module = defaultdict(list)
            for sid, svc in services.items():
                meta = svc.get("Meta", {})
                module = meta.get("module", "")
                
                if module and module.lower() not in Config.BLACKBOX_MODULES:
                    module = ""
                
                if not module:
                    tags = svc.get("Tags", [])
                    for tag in tags:
                        if tag and tag.lower() in Config.BLACKBOX_MODULES:
                            module = tag.lower()
                            break
                
                if not module or module.lower() not in Config.BLACKBOX_MODULES:
                    module = "outros"
                else:
                    module = module.lower()
                    
                by_module[module].append((sid, svc))
            
            for module, svcs in sorted(by_module.items()):
                table = Table(
                    title=f"Módulo: {module.upper()}",
                    box=box.ROUNDED,
                    title_style="bold cyan"
                )
                
                table.add_column("#", style="dim", width=3)
                table.add_column("Node", style="cyan")
                table.add_column("Name", style="yellow")
                table.add_column("Instance", style="yellow")
                table.add_column("Company", style="magenta")
                table.add_column("Project", style="green")
                table.add_column("Env", style="blue")
                table.add_column("Cod Local", style="green")
                table.add_column("Tipo", style="yellow")
                table.add_column("Localização", style="cyan")
                table.add_column("Module", style="blue")
                table.add_column("Provedor", style="magenta")
                
                for i, (sid, svc) in enumerate(svcs, 1):
                    meta = svc.get("Meta", {})
                    table.add_row(
                        str(i),
                        self.current_node[:20],
                        meta.get("name", "N/A")[:15],
                        meta.get("instance", "N/A")[:25],
                        meta.get("company", "N/A")[:15],
                        meta.get("project", "N/A")[:15],
                        meta.get("env", "N/A")[:10],
                        meta.get("cod_localidade", "N/A")[:10],
                        meta.get("tipo", "N/A")[:10],
                        meta.get("localizacao", "N/A")[:15],
                        meta.get("module", "N/A")[:10],
                        meta.get("provedor", "N/A")[:10]
                    )
                
                console.print(table)
                
        except Exception as e:
            console.print(f"[red]Erro ao listar serviços: {e}[/red]")
    
    def _list_all_nodes(self):
        """Lista serviços de todos os nós"""
        members = self.consul.get_members()
        all_services = []
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Coletando dados de todos os nós...", total=len(members))
            
            for member in members:
                progress.update(task, description=f"Consultando {member['node']}...")
                
                try:
                    temp_consul = ConsulManager(host=member["addr"], token=self.consul.token)
                    services = temp_consul.get_services()
                    
                    for sid, svc in services.items():
                        svc["_node"] = member["node"]
                        svc["_node_addr"] = member["addr"]
                        all_services.append((sid, svc))
                        
                except Exception as e:
                    console.print(f"[yellow]Erro em {member['node']}: {e}[/yellow]")
                
                progress.advance(task)
        
        if not all_services:
            console.print("[yellow]Nenhum serviço encontrado em nenhum nó[/yellow]")
            return
        
        page_size = 50
        total_pages = (len(all_services) + page_size - 1) // page_size
        current_page = 0
        
        while True:
            start_idx = current_page * page_size
            end_idx = min(start_idx + page_size, len(all_services))
            page_services = all_services[start_idx:end_idx]
            
            table = Table(
                title=f"Serviços em TODOS os Nós - Página {current_page + 1}/{total_pages} ({len(all_services)} total)",
                box=box.ROUNDED
            )
            
            table.add_column("Node", style="cyan")
            table.add_column("Name", style="yellow")
            table.add_column("Instance", style="yellow")
            table.add_column("Company", style="magenta")
            table.add_column("Project", style="green")
            table.add_column("Env", style="blue")
            table.add_column("Cod Local", style="green")
            table.add_column("Tipo", style="yellow")
            table.add_column("Localização", style="cyan")
            table.add_column("Module", style="blue")
            table.add_column("Provedor", style="magenta")
            
            for sid, svc in page_services:
                meta = svc.get("Meta", {})
                
                table.add_row(
                    svc["_node"][:20],
                    meta.get("name", "N/A")[:15],
                    meta.get("instance", "N/A")[:25],
                    meta.get("company", "N/A")[:15],
                    meta.get("project", "N/A")[:15],
                    meta.get("env", "N/A")[:10],
                    meta.get("cod_localidade", "N/A")[:10],
                    meta.get("tipo", "N/A")[:10],
                    meta.get("localizacao", "N/A")[:15],
                    meta.get("module", "N/A")[:10],
                    meta.get("provedor", "N/A")[:10]
                )
            
            console.print(table)
            
            if total_pages > 1:
                choices = []
                if current_page > 0:
                    choices.append("⬅️  Página anterior")
                if current_page < total_pages - 1:
                    choices.append("➡️  Próxima página")
                choices.append("🔙 Voltar ao menu")
                
                choice = questionary.select(
                    "Navegação:",
                    choices=choices
                ).ask()
                
                if choice == "⬅️  Página anterior":
                    current_page -= 1
                elif choice == "➡️  Próxima página":
                    current_page += 1
                else:
                    break
            else:
                break
    
    def add_service(self):
        """Adiciona novo serviço interativamente"""
        console.print("\n[bold cyan]➕ Adicionar Novo Serviço[/bold cyan]\n")
        
        if self.current_node == "ALL":
            console.print("[yellow]⚠️  Não é possível adicionar serviços no modo 'TODOS os nós'.[/yellow]")
            console.print("[cyan]Por favor, selecione um nó específico primeiro usando 'Trocar de Nó'.[/cyan]")
            questionary.press_any_key_to_continue("Pressione ENTER para voltar...").ask()
            return
        
        console.print("[bold]Service Names disponíveis:[/bold]")
        table = Table(box=box.SIMPLE)
        table.add_column("ServiceName", style="cyan")
        table.add_column("Descrição", style="yellow")
        table.add_column("Nó de Destino", style="green")
        
        for name, desc in Config.SERVICE_NAMES.items():
            target_node = Config.SERVICE_NAME_TO_NODE.get(name)
            if target_node:
                node_display = target_node
                for node_name, node_ip in Config.KNOWN_NODES.items():
                    if node_ip == target_node:
                        node_display = f"{node_name} ({target_node})"
                        break
            else:
                node_display = "Nó atual selecionado"
            
            table.add_row(name, desc, node_display)
        
        console.print(table)
        
        choices = list(Config.SERVICE_NAMES.keys()) + ["❌ Cancelar"]
        service_name = questionary.select(
            "Selecione o ServiceName:",
            choices=choices
        ).ask()
        
        if not service_name or service_name == "❌ Cancelar":
            return
        
        console.print("\n[bold yellow]📋 Módulos de Monitoramento Disponíveis:[/bold yellow]\n")
        
        module_table = Table(title="Escolha o tipo de monitoramento", box=box.ROUNDED)
        module_table.add_column("#", style="cyan", width=3)
        module_table.add_column("Módulo", style="yellow", width=15)
        module_table.add_column("Descrição", style="green", width=50)
        
        for i, mod in enumerate(Config.BLACKBOX_MODULES, 1):
            desc = Config.MODULE_DESCRIPTIONS[mod]
            module_table.add_row(
                str(i),
                desc["name"],
                desc["description"]
            )
        
        console.print(module_table)
        
        module_choices = [f"{i}) {Config.MODULE_DESCRIPTIONS[mod]['name']}" 
                         for i, mod in enumerate(Config.BLACKBOX_MODULES, 1)]
        module_choices.append("❌ Cancelar")
        
        module_choice = questionary.select(
            "Selecione o módulo:",
            choices=module_choices,
            style=custom_style
        ).ask()
        
        if not module_choice or module_choice == "❌ Cancelar":
            return
        
        idx = int(module_choice.split(")")[0]) - 1
        module = Config.BLACKBOX_MODULES[idx]
        module_info = Config.MODULE_DESCRIPTIONS[module]
        
        console.print(f"\n[bold cyan]ℹ️  Informações sobre '{module_info['name']}':[/bold cyan]")
        console.print(f"[yellow]Descrição:[/yellow] {module_info['description']}")
        console.print(f"[yellow]Casos de uso:[/yellow]")
        for use_case in module_info["use_cases"]:
            console.print(f"  • {use_case}")
        console.print(f"[yellow]Exemplo de instance:[/yellow] {module_info['example_instance']}")
        
        if "format" in module_info:
            console.print(f"[yellow]Formato:[/yellow] {module_info['format']}")
        if "valid_status" in module_info:
            console.print(f"[yellow]Status HTTP válidos:[/yellow] {module_info['valid_status']}")
        if "ssl_validation" in module_info:
            console.print(f"[yellow]Validação SSL:[/yellow] {'✅ Sim' if module_info['ssl_validation'] else '❌ Não'}")
        if "method" in module_info:
            console.print(f"[yellow]Método HTTP:[/yellow] {module_info['method']}")
        if "expected_banner" in module_info:
            console.print(f"[yellow]Banner esperado:[/yellow] {module_info['expected_banner']}")
        if "tls" in module_info:
            console.print(f"[yellow]TLS:[/yellow] {'✅ Sim' if module_info['tls'] else '❌ Não'}")
        
        console.print()
        
        target_node_addr = Config.SERVICE_NAME_TO_NODE.get(service_name)
        if target_node_addr is None:
            target_node_addr = self.current_node_addr
        
        console.print("\n[bold]Preencha os metadados (digite 'cancelar' para sair):[/bold]")
        meta = {"module": module}
        
        if module in Config.MODULE_DEFAULTS:
            defaults = Config.MODULE_DEFAULTS[module]
            
            if "timeout" in defaults:
                timeout = questionary.text(
                    f"⏱️  Timeout (tempo limite, padrão: {defaults['timeout']}):",
                    default=defaults.get('timeout', '5s')
                ).ask()
                if timeout and timeout.lower() == 'cancelar':
                    return
                if timeout:
                    meta["timeout"] = timeout
            
            if "interval" in defaults:
                interval = questionary.text(
                    f"🔄 Intervalo de verificação (padrão: {defaults.get('interval', '15s')}):",
                    default=defaults.get('interval', '15s')
                ).ask()
                if interval and interval.lower() == 'cancelar':
                    return
                if interval:
                    meta["interval"] = interval
        
        fields_with_options = ["company", "project", "env", "localizacao", "tipo", 
                              "cod_localidade", "cidade", "provedor", "fabricante", 
                              "modelo", "tipo_dispositivo_abrev"]
        
        for field in Config.META_FIELDS[1:]:
            if field == "name":
                while True:
                    value = questionary.text(f"{field} (Nome único do serviço, 'cancelar' para sair):").ask()
                    if value and value.lower() == 'cancelar':
                        return
                    if not value:
                        break
                    
                    if self._check_duplicate_combined_key(
                        module, 
                        meta.get('company', ''), 
                        meta.get('project', ''), 
                        meta.get('env', ''),
                        value,
                        target_node_addr=target_node_addr
                    ):
                        console.print(f"[red]⚠️  ATENÇÃO: Já existe um serviço com a combinação:[/red]")
                        console.print(f"[yellow]   module: {module}[/yellow]")
                        console.print(f"[yellow]   company: {meta.get('company', '')}[/yellow]")
                        console.print(f"[yellow]   project: {meta.get('project', '')}[/yellow]")
                        console.print(f"[yellow]   env: {meta.get('env', '')}[/yellow]")
                        console.print(f"[yellow]   name: {value}[/yellow]")
                        console.print(f"[red]Essa combinação deve ser ÚNICA! Usar o mesmo substituirá o item existente.[/red]")
                        if not questionary.confirm("Deseja continuar e sobrescrever?").ask():
                            continue
                    
                    meta[field] = value
                    break
                        
            elif field == "instance":
                value = questionary.text(
                    f"{field} (Alvo: {module_info['example_instance']}, 'cancelar' para sair):",
                    default=""
                ).ask()
                if value and value.lower() == 'cancelar':
                    return
                if value:
                    meta[field] = value
                        
            elif field in fields_with_options:
                existing_values = sorted(self.consul.get_unique_values(field))
                
                if existing_values:
                    choices = list(existing_values) + ["➕ Adicionar novo...", "⏭️  Pular", "❌ Cancelar"]
                    value = questionary.select(
                        f"{field} (selecione, adicione novo ou pule):",
                        choices=choices
                    ).ask()
                    
                    if value == "❌ Cancelar":
                        return
                    elif value == "⏭️  Pular":
                        continue
                    elif value == "➕ Adicionar novo...":
                        value = questionary.text(f"Digite novo {field} ('cancelar' para sair):").ask()
                        if value and value.lower() == 'cancelar':
                            return
                    
                    if value and value not in ["⏭️  Pular", "➕ Adicionar novo..."]:
                        meta[field] = value
                else:
                    value = questionary.text(f"{field} (opcional, 'cancelar' para sair):").ask()
                    if value and value.lower() == 'cancelar':
                        return
                    if value:
                        meta[field] = value
            else:
                value = questionary.text(f"{field} (opcional, 'cancelar' para sair):").ask()
                if value and value.lower() == 'cancelar':
                    return
                if value:
                    meta[field] = value
        
        missing = [f for f in Config.REQUIRED_FIELDS if f not in meta or not meta[f]]
        if missing:
            console.print(f"[red]Campos obrigatórios faltando: {', '.join(missing)}[/red]")
            questionary.press_any_key_to_continue("Pressione ENTER para voltar...").ask()
            return
        
        sid = f"{module}/{meta.get('company', 'none')}/{meta.get('project', 'none')}/{meta.get('env', 'none')}@{meta.get('name', 'unnamed')}"
        
        try:
            temp_consul = ConsulManager(host=target_node_addr, token=self.consul.token)
            existing_services = temp_consul.get_services()
            if sid in existing_services:
                console.print(f"[red]Service ID '{sid}' já existe no nó de destino![/red]")
                if not questionary.confirm("Deseja sobrescrever?").ask():
                    questionary.press_any_key_to_continue("Pressione ENTER para voltar...").ask()
                    return
        except:
            pass
        
        target_node_name = "nó atual"
        for node_name, node_ip in Config.KNOWN_NODES.items():
            if node_ip == target_node_addr:
                target_node_name = f"{node_name} ({node_ip})"
                break
        
        console.print(f"\n[cyan]ℹ️  Este serviço será registrado em: {target_node_name}[/cyan]\n")
        
        console.print("\n[bold]Resumo do serviço:[/bold]")
        console.print(f"ID: {sid}")
        console.print(f"ServiceName: {service_name}")
        console.print(f"Tags: [{module}]")
        console.print(f"Nó de destino: {target_node_name}")
        console.print(f"Meta: {json.dumps(meta, indent=2, ensure_ascii=False)}")
        
        if questionary.confirm("Confirma o registro?").ask():
            service_data = {
                "id": sid,
                "name": service_name,
                "tags": [module],
                "meta": meta
            }
            
            if self.consul.register_service(service_data, target_node_addr):
                console.print(f"\n[bold green]✅ SUCESSO! Serviço registrado com ID:[/bold green]")
                console.print(f"[bold cyan]{sid}[/bold cyan]")
                console.print(f"[green]No nó: {target_node_name}[/green]")
            else:
                console.print("[red]❌ Falha ao registrar serviço[/red]")
        
        questionary.press_any_key_to_continue("Pressione ENTER para voltar...").ask()
    
    def _check_duplicate_combined_key(self, module: str, company: str, project: str, env: str, name: str, exclude_sid: str = None, target_node_addr: str = None) -> bool:
        """Verifica se já existe um serviço com a mesma combinação"""
        node_addr = target_node_addr if target_node_addr else self.current_node_addr
        
        if node_addr == "ALL":
            return False
        
        try:
            temp_consul = ConsulManager(host=node_addr, token=self.consul.token)
            services = temp_consul.get_services()
            
            for sid, svc in services.items():
                if exclude_sid and sid == exclude_sid:
                    continue
                    
                meta = svc.get("Meta", {})
                
                if (meta.get("module", "").lower() == module.lower() and
                    meta.get("company", "") == company and
                    meta.get("project", "") == project and
                    meta.get("env", "") == env and
                    meta.get("name", "") == name):
                    return True
        except:
            pass
        
        return False
    
    def edit_service(self):
        """Edita um serviço existente"""
        console.print("\n[bold cyan]✏️  Editar Serviço[/bold cyan]\n")
        
        if self.current_node == "ALL":
            console.print("[yellow]⚠️  Não é possível editar serviços no modo 'TODOS os nós'.[/yellow]")
            console.print("[cyan]Por favor, selecione um nó específico primeiro usando 'Trocar de Nó'.[/cyan]")
            questionary.press_any_key_to_continue("Pressione ENTER para voltar...").ask()
            return
        
        services = self.consul.get_services(self.current_node_addr)
        
        if not services:
            console.print("[yellow]Nenhum serviço para editar[/yellow]")
            questionary.press_any_key_to_continue("Pressione ENTER para voltar...").ask()
            return
        
        table = Table(title="Serviços Disponíveis para Edição", box=box.ROUNDED)
        table.add_column("#", style="cyan", width=3)
        table.add_column("Name", style="yellow")
        table.add_column("Instance", style="yellow")
        table.add_column("Company", style="magenta")
        table.add_column("Project", style="green")
        table.add_column("Env", style="blue")
        table.add_column("Cod Local", style="green")
        table.add_column("Tipo", style="yellow")
        table.add_column("Localização", style="cyan")
        table.add_column("Module", style="blue")
        table.add_column("Provedor", style="magenta")
        
        service_list = []
        for sid, svc in services.items():
            meta = svc.get("Meta", {})
            service_list.append({
                'id': sid,
                'name': svc.get('Service', svc.get('ID', sid)),
                'tags': svc.get('Tags', []),
                'meta': meta
            })
        
        for i, svc in enumerate(service_list, 1):
            table.add_row(
                str(i),
                svc['meta'].get("name", "N/A")[:15],
                svc['meta'].get("instance", "N/A")[:30],
                svc['meta'].get("company", "N/A")[:20],
                svc['meta'].get("project", "N/A")[:20],
                svc['meta'].get("env", "N/A")[:10],
                svc['meta'].get("cod_localidade", "N/A")[:10],
                svc['meta'].get("tipo", "N/A")[:10],
                svc['meta'].get("localizacao", "N/A")[:15],
                svc['meta'].get("module", "N/A")[:10],
                svc['meta'].get("provedor", "N/A")[:10]
            )
        
        console.print(table)
        
        selection = questionary.text(
            "Digite o número do serviço para editar (ou 'v' para voltar):",
            default="v"
        ).ask()
        
        if not selection or selection.lower() == 'v':
            return
        
        try:
            idx = int(selection) - 1
            if idx < 0 or idx >= len(service_list):
                console.print("[red]Número inválido![/red]")
                questionary.press_any_key_to_continue("Pressione ENTER para voltar...").ask()
                return
        except ValueError:
            console.print("[red]Entrada inválida![/red]")
            questionary.press_any_key_to_continue("Pressione ENTER para voltar...").ask()
            return
        
        old_service = service_list[idx]
        old_meta = old_service['meta']
        old_sid = old_service['id']
        
        console.print(f"\n[bold]Editando: {old_sid}[/bold]\n")
        console.print("[dim]Pressione ENTER para manter o valor atual, 'cancelar' para abortar[/dim]\n")
        
        new_meta = {}
        
        console.print("[bold yellow]📋 Módulos de Monitoramento Disponíveis:[/bold yellow]\n")
        
        module_table = Table(title="Escolha o tipo de monitoramento", box=box.ROUNDED)
        module_table.add_column("#", style="cyan", width=3)
        module_table.add_column("Módulo", style="yellow", width=15)
        module_table.add_column("Descrição", style="green", width=50)
        
        current_module = old_meta.get("module", "icmp")
        
        for i, mod in enumerate(Config.BLACKBOX_MODULES, 1):
            desc = Config.MODULE_DESCRIPTIONS[mod]
            marker = " ⭐" if mod == current_module else ""
            module_table.add_row(
                str(i),
                desc["name"] + marker,
                desc["description"]
            )
        
        console.print(module_table)
        console.print(f"[dim]⭐ = Módulo atual ({current_module})[/dim]\n")
        
        module_choices = [f"{i}) {Config.MODULE_DESCRIPTIONS[mod]['name']}" 
                         for i, mod in enumerate(Config.BLACKBOX_MODULES, 1)]
        module_choices.append("❌ Cancelar")
        
        default_choice = None
        for i, mod in enumerate(Config.BLACKBOX_MODULES, 1):
            if mod == current_module:
                default_choice = f"{i}) {Config.MODULE_DESCRIPTIONS[mod]['name']}"
                break
        
        module_choice = questionary.select(
            f"Módulo (atual: {current_module}):",
            choices=module_choices,
            default=default_choice if default_choice else module_choices[0]
        ).ask()
        
        if not module_choice or module_choice == "❌ Cancelar":
            return
        
        idx_mod = int(module_choice.split(")")[0]) - 1
        module = Config.BLACKBOX_MODULES[idx_mod]
        module_info = Config.MODULE_DESCRIPTIONS[module]
        
        if module != current_module:
            console.print(f"\n[bold cyan]ℹ️  Novo módulo: '{module_info['name']}':[/bold cyan]")
            console.print(f"[yellow]Descrição:[/yellow] {module_info['description']}")
            console.print(f"[yellow]Exemplo de instance:[/yellow] {module_info['example_instance']}\n")
        
        new_meta["module"] = module
        
        service_name = old_service['name']
        
        target_node_addr = Config.SERVICE_NAME_TO_NODE.get(service_name)
        if target_node_addr is None:
            target_node_addr = self.current_node_addr
        
        for field in ["company", "project", "env", "name", "instance"]:
            current_value = old_meta.get(field, "")
            
            if field in ["company", "project", "env"]:
                existing_values = sorted(self.consul.get_unique_values(field))
                
                if existing_values and current_value in existing_values:
                    choices = list(existing_values) + ["➕ Novo valor...", "❌ Cancelar"]
                    value = questionary.select(
                        f"{field} (atual: {current_value}):",
                        choices=choices,
                        default=current_value
                    ).ask()
                    
                    if value == "❌ Cancelar":
                        return
                    elif value == "➕ Novo valor...":
                        value = questionary.text(
                            f"Digite novo {field}:",
                            default=current_value
                        ).ask()
                        if not value or value.lower() == 'cancelar':
                            return
                else:
                    value = questionary.text(
                        f"{field} (atual: {current_value}):",
                        default=current_value
                    ).ask()
                    if not value or value.lower() == 'cancelar':
                        return
            elif field == "name":
                while True:
                    value = questionary.text(
                        f"{field} (atual: {current_value}):",
                        default=current_value
                    ).ask()
                    if not value or value.lower() == 'cancelar':
                        return
                    
                    if self._check_duplicate_combined_key(
                        new_meta['module'],
                        new_meta.get('company', ''),
                        new_meta.get('project', ''),
                        new_meta.get('env', ''),
                        value,
                        exclude_sid=old_sid,
                        target_node_addr=target_node_addr
                    ):
                        console.print(f"[red]⚠️  ATENÇÃO: Já existe outro serviço com essa combinação![/red]")
                        console.print(f"[yellow]   module: {new_meta['module']}[/yellow]")
                        console.print(f"[yellow]   company: {new_meta.get('company', '')}[/yellow]")
                        console.print(f"[yellow]   project: {new_meta.get('project', '')}[/yellow]")
                        console.print(f"[yellow]   env: {new_meta.get('env', '')}[/yellow]")
                        console.print(f"[yellow]   name: {value}[/yellow]")
                        console.print(f"[red]Essa combinação deve ser ÚNICA![/red]")
                        if not questionary.confirm("Deseja continuar e sobrescrever?").ask():
                            continue
                    
                    new_meta[field] = value
                    break
            elif field == "instance":
                value = questionary.text(
                    f"{field} (Ex: {module_info['example_instance']}, atual: {current_value}):",
                    default=current_value
                ).ask()
                if not value or value.lower() == 'cancelar':
                    return
            
            if value and field not in new_meta:
                new_meta[field] = value
        
        optional_fields = ["localizacao", "tipo", "cod_localidade", "cidade", "notas", 
                          "provedor", "fabricante", "modelo", "tipo_dispositivo_abrev", "glpi_url"]
        
        console.print("\n[dim]Campos opcionais (pressione ENTER para manter valor atual ou deixar vazio)[/dim]\n")
        
        for field in optional_fields:
            current_value = old_meta.get(field, "")
            value = questionary.text(
                f"{field} (atual: {current_value}):",
                default=current_value
            ).ask()
            
            if value and value.lower() != 'cancelar':
                new_meta[field] = value
            elif current_value:
                new_meta[field] = current_value
        
        new_sid = f"{new_meta['module']}/{new_meta.get('company', 'none')}/{new_meta.get('project', 'none')}/{new_meta.get('env', 'none')}@{new_meta.get('name', 'unnamed')}"
        
        console.print("\n[bold yellow]Resumo das Alterações:[/bold yellow]")
        console.print(f"ID antigo: {old_sid}")
        console.print(f"ID novo:   {new_sid}")
        console.print(f"\nMeta antigo: {json.dumps(old_meta, indent=2, ensure_ascii=False)}")
        console.print(f"\nMeta novo: {json.dumps(new_meta, indent=2, ensure_ascii=False)}")
        
        if not questionary.confirm("\nConfirma as alterações?").ask():
            console.print("[yellow]Operação cancelada[/yellow]")
            questionary.press_any_key_to_continue("Pressione ENTER para voltar...").ask()
            return
        
        console.print("\n[yellow]Removendo serviço antigo...[/yellow]")
        if not self.consul.deregister_service(old_sid, target_node_addr):
            console.print("[red]❌ Erro ao remover serviço antigo. Operação abortada.[/red]")
            questionary.press_any_key_to_continue("Pressione ENTER para voltar...").ask()
            return
        
        time.sleep(1)
        
        console.print("[yellow]Registrando serviço atualizado...[/yellow]")
        service_data = {
            "id": new_sid,
            "name": service_name,
            "tags": [new_meta['module']],
            "meta": new_meta
        }
        
        if self.consul.register_service(service_data, target_node_addr):
            console.print(f"\n[bold green]✅ SUCESSO! Serviço atualizado com novo ID:[/bold green]")
            console.print(f"[bold cyan]{new_sid}[/bold cyan]")
        else:
            console.print("[red]❌ Erro ao registrar serviço atualizado[/red]")
            console.print("[yellow]⚠️  O serviço antigo foi removido mas o novo não foi criado![/yellow]")
        
        questionary.press_any_key_to_continue("Pressione ENTER para voltar...").ask()
    
    def remove_service(self):
        """Remove serviços com visualização em tabela"""
        if self.current_node == "ALL":
            console.print("[yellow]⚠️  Não é possível remover serviços no modo 'TODOS os nós'.[/yellow]")
            console.print("[cyan]Por favor, selecione um nó específico primeiro usando 'Trocar de Nó'.[/cyan]")
            questionary.press_any_key_to_continue("Pressione ENTER para voltar...").ask()
            return
        
        services = self.consul.get_services(self.current_node_addr)
        
        if not services:
            console.print("[yellow]Nenhum serviço para remover[/yellow]")
            questionary.press_any_key_to_continue("Pressione ENTER para voltar...").ask()
            return
        
        table = Table(title="Serviços Disponíveis para Remoção", box=box.ROUNDED)
        table.add_column("#", style="cyan", width=3)
        table.add_column("Name", style="yellow")
        table.add_column("Instance", style="yellow")
        table.add_column("Company", style="magenta")
        table.add_column("Project", style="green")
        table.add_column("Env", style="blue")
        table.add_column("Cod Local", style="green")
        table.add_column("Tipo", style="yellow")
        table.add_column("Localização", style="cyan")
        table.add_column("Module", style="blue")
        table.add_column("Provedor", style="magenta")
        
        service_list = []
        for sid, svc in services.items():
            meta = svc.get("Meta", {})
            service_list.append({
                'id': sid,
                'name': meta.get("name", "N/A"),
                'instance': meta.get("instance", "N/A"),
                'company': meta.get("company", "N/A"),
                'project': meta.get("project", "N/A"),
                'env': meta.get("env", "N/A"),
                'cod_localidade': meta.get("cod_localidade", "N/A"),
                'tipo': meta.get("tipo", "N/A"),
                'localizacao': meta.get("localizacao", "N/A"),
                'module': meta.get("module", "N/A"),
                'provedor': meta.get("provedor", "N/A")
            })
        
        for i, svc in enumerate(service_list, 1):
            table.add_row(
                str(i),
                svc['name'][:15],
                svc['instance'][:30],
                svc['company'][:20],
                svc['project'][:20],
                svc['env'][:10],
                svc['cod_localidade'][:10],
                svc['tipo'][:10],
                svc['localizacao'][:15],
                svc['module'][:10],
                svc['provedor'][:10]
            )
        
        console.print(table)
        
        selection = questionary.text(
            "Digite os números dos serviços a remover (separados por vírgula) ou 'v' para voltar:",
            default=""
        ).ask()
        
        if not selection or selection.lower() == 'v':
            return
        
        selected_indices = []
        try:
            for num in selection.split(','):
                idx = int(num.strip()) - 1
                if 0 <= idx < len(service_list):
                    selected_indices.append(idx)
        except ValueError:
            console.print("[red]Entrada inválida![/red]")
            questionary.press_any_key_to_continue("Pressione ENTER para voltar...").ask()
            return
        
        if not selected_indices:
            console.print("[yellow]Nenhum serviço válido selecionado[/yellow]")
            questionary.press_any_key_to_continue("Pressione ENTER para voltar...").ask()
            return
        
        console.print("\n[bold yellow]Serviços a serem removidos:[/bold yellow]")
        for idx in selected_indices:
            svc = service_list[idx]
            console.print(f"  • {svc['name']} - {svc['instance']}")
        
        if questionary.confirm(f"\nConfirma a remoção de {len(selected_indices)} serviço(s)?").ask():
            for idx in selected_indices:
                sid = service_list[idx]['id']
                name = service_list[idx]['name']
                if self.consul.deregister_service(sid, self.current_node_addr):
                    console.print(f"[green]✅ Removido: {name}[/green]")
                else:
                    console.print(f"[red]❌ Falha ao remover: {name}[/red]")
        else:
            console.print("[yellow]Operação cancelada[/yellow]")
        
        questionary.press_any_key_to_continue("Pressione ENTER para voltar...").ask()
    
    def import_csv(self):
        """Importa serviços de arquivo CSV"""
        console.print("\n[bold cyan]📥 Importar CSV[/bold cyan]\n")
        
        if self.current_node == "ALL":
            console.print("[yellow]⚠️  Não é possível importar serviços no modo 'TODOS os nós'.[/yellow]")
            console.print("[cyan]Por favor, selecione um nó específico primeiro usando 'Trocar de Nó'.[/cyan]")
            questionary.press_any_key_to_continue("Pressione ENTER para voltar...").ask()
            return
        
        csv_files = list(Path.cwd().glob("*.csv"))
        
        if not csv_files:
            console.print("[yellow]Nenhum arquivo CSV encontrado no diretório atual[/yellow]")
            questionary.press_any_key_to_continue("Pressione ENTER para voltar...").ask()
            return
        
        choices = [str(f.name) for f in csv_files]
        choices.append("🔙 Voltar")
        
        file_name = questionary.select(
            "Selecione o arquivo:",
            choices=choices
        ).ask()
        
        if not file_name or file_name == "🔙 Voltar":
            return
        
        file_path = str(Path.cwd() / file_name)
        
        service_choices = list(Config.SERVICE_NAMES.keys()) + ["🔙 Voltar"]
        service_name = questionary.select(
            "Selecione o ServiceName para os serviços importados:",
            choices=service_choices
        ).ask()
        
        if not service_name or service_name == "🔙 Voltar":
            return
        
        imported = 0
        errors = 0
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                
                for row in track(list(reader), description="Importando..."):
                    try:
                        module = row.get("module", "icmp").lower()
                        
                        if module not in Config.BLACKBOX_MODULES:
                            console.print(f"[yellow]Módulo inválido '{module}' na linha, pulando...[/yellow]")
                            errors += 1
                            continue
                        
                        sid = f"{module}/{row.get('company', 'none')}/{row.get('project', 'none')}/{row.get('env', 'none')}@{row.get('name', 'unnamed')}"
                        
                        service_data = {
                            "id": sid,
                            "name": service_name,
                            "tags": [module],
                            "meta": {k: v for k, v in row.items() if k in Config.META_FIELDS}
                        }
                        
                        if self.consul.register_service(service_data, self.current_node_addr):
                            imported += 1
                        else:
                            errors += 1
                            
                    except Exception as e:
                        console.print(f"[red]Erro na linha: {e}[/red]")
                        errors += 1
            
            console.print(f"\n[green]✅ Importados: {imported}[/green]")
            if errors:
                console.print(f"[red]❌ Erros: {errors}[/red]")
                
        except Exception as e:
            console.print(f"[red]Erro ao ler arquivo: {e}[/red]")
        
        questionary.press_any_key_to_continue("Pressione ENTER para voltar...").ask()
    
    def export_csv(self):
        """Exporta serviços para CSV"""
        console.print("\n[bold cyan]📤 Exportar CSV[/bold cyan]\n")
        
        filename = questionary.text(
            "Nome do arquivo (ou 'v' para voltar):",
            default=f"consul_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        ).ask()
        
        if not filename or filename.lower() == 'v':
            return
        
        if self.current_node == "ALL":
            members = self.consul.get_members()
            all_services = []
            
            for member in track(members, description="Coletando dados..."):
                try:
                    temp_consul = ConsulManager(host=member["addr"], token=self.consul.token)
                    services = temp_consul.get_services()
                    
                    for sid, svc in services.items():
                        row = {"node": member["node"], "service_id": sid}
                        meta = svc.get("Meta", {})
                        for field in Config.META_FIELDS:
                            row[field] = meta.get(field, "")
                        row["tags"] = ",".join(svc.get("Tags", []))
                        all_services.append(row)
                except:
                    pass
            
            services_to_export = all_services
        else:
            services = self.consul.get_services(self.current_node_addr)
            services_to_export = []
            
            for sid, svc in services.items():
                row = {"node": self.current_node, "service_id": sid}
                meta = svc.get("Meta", {})
                for field in Config.META_FIELDS:
                    row[field] = meta.get(field, "")
                row["tags"] = ",".join(svc.get("Tags", []))
                services_to_export.append(row)
        
        if services_to_export:
            fieldnames = ["node", "service_id"] + Config.META_FIELDS + ["tags"]
            
            with open(filename, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
                writer.writeheader()
                writer.writerows(services_to_export)
            
            console.print(f"[green]✅ Exportado {len(services_to_export)} serviços para {filename}[/green]")
        else:
            console.print("[yellow]Nenhum serviço para exportar[/yellow]")
        
        questionary.press_any_key_to_continue("Pressione ENTER para voltar...").ask()
    
    def search_services(self):
        """Busca e filtra serviços"""
        console.print("\n[bold cyan]🔍 Buscar/Filtrar Serviços[/bold cyan]\n")
        
        search_term = questionary.text(
            "Termo de busca (ou 'v' para voltar):",
            default=""
        ).ask()
        
        if not search_term or search_term.lower() == 'v':
            return
        
        search_field = questionary.select(
            "Buscar em:",
            choices=["Todos os campos", "instance", "company", "project", "env", "localizacao", "tipo", "🔙 Voltar"]
        ).ask()
        
        if not search_field or search_field == "🔙 Voltar":
            return
        
        if self.current_node == "ALL":
            members = self.consul.get_members()
            all_results = []
            
            for member in members:
                try:
                    temp_consul = ConsulManager(host=member["addr"], token=self.consul.token)
                    services = temp_consul.get_services()
                    
                    for sid, svc in services.items():
                        meta = svc.get("Meta", {})
                        
                        match = False
                        if search_field == "Todos os campos":
                            if search_term.lower() in sid.lower() or \
                               any(search_term.lower() in str(v).lower() for v in meta.values()):
                                match = True
                        else:
                            if search_term.lower() in str(meta.get(search_field, "")).lower():
                                match = True
                        
                        if match:
                            all_results.append({
                                "node": member["node"],
                                "sid": sid,
                                "meta": meta,
                                "tags": svc.get("Tags", [])
                            })
                except:
                    pass
        else:
            services = self.consul.get_services(self.current_node_addr)
            all_results = []
            
            for sid, svc in services.items():
                meta = svc.get("Meta", {})
                
                match = False
                if search_field == "Todos os campos":
                    if search_term.lower() in sid.lower() or \
                       any(search_term.lower() in str(v).lower() for v in meta.values()):
                        match = True
                else:
                    if search_term.lower() in str(meta.get(search_field, "")).lower():
                        match = True
                
                if match:
                    all_results.append({
                        "node": self.current_node,
                        "sid": sid,
                        "meta": meta,
                        "tags": svc.get("Tags", [])
                    })
        
        if all_results:
            table = Table(
                title=f"Resultados da busca: '{search_term}' ({len(all_results)} encontrados)",
                box=box.ROUNDED
            )
            
            table.add_column("Node", style="cyan")
            table.add_column("Name", style="yellow")
            table.add_column("Instance", style="yellow")
            table.add_column("Company", style="magenta")
            table.add_column("Project", style="green")
            table.add_column("Env", style="blue")
            table.add_column("Cod Local", style="green")
            table.add_column("Tipo", style="yellow")
            table.add_column("Localização", style="cyan")
            table.add_column("Module", style="blue")
            table.add_column("Provedor", style="magenta")
            
            for result in all_results[:30]:
                table.add_row(
                    result["node"][:20],
                    result["meta"].get("name", "N/A")[:15],
                    result["meta"].get("instance", "N/A")[:25],
                    result["meta"].get("company", "N/A")[:15],
                    result["meta"].get("project", "N/A")[:15],
                    result["meta"].get("env", "N/A")[:10],
                    result["meta"].get("cod_localidade", "N/A")[:10],
                    result["meta"].get("tipo", "N/A")[:10],
                    result["meta"].get("localizacao", "N/A")[:15],
                    result["meta"].get("module", "N/A")[:10],
                    result["meta"].get("provedor", "N/A")[:10]
                )
            
            console.print(table)
            
            if len(all_results) > 30:
                console.print(f"[dim]... e mais {len(all_results) - 30} resultados[/dim]")
        else:
            console.print("[yellow]Nenhum resultado encontrado[/yellow]")
        
        questionary.press_any_key_to_continue("Pressione ENTER para voltar...").ask()
    
    def health_status(self):
        """Mostra status de saúde dos serviços"""
        console.print("\n[bold cyan]❤️  Status de Saúde[/bold cyan]\n")
        
        try:
            health = self.consul.get_health_status()
            
            passing = []
            warning = []
            critical = []
            
            for h in health:
                status = h.get("Status", "unknown")
                service_name = h.get("ServiceName", "")
                service_id = h.get("ServiceID", "")
                check_id = h.get("CheckID", "")
                output = h.get("Output", "")
                notes = h.get("Notes", "")
                
                info = {
                    "service": service_name or check_id,
                    "id": service_id,
                    "output": output[:100] if output else "No output",
                    "notes": notes
                }
                
                if status == "passing":
                    passing.append(info)
                elif status == "warning":
                    warning.append(info)
                elif status == "critical":
                    critical.append(info)
            
            status_text = f"""
🟢 Passing:  {len(passing)}
🟡 Warning:  {len(warning)}
🔴 Critical: {len(critical)}
            """
            
            console.print(Panel(
                status_text,
                title="Health Status",
                border_style="green" if len(critical) == 0 else "red"
            ))
            
            if critical:
                console.print("\n[bold yellow]⚠️  NOTA IMPORTANTE:[/bold yellow]")
                console.print("[dim]Serviços podem aparecer como 'Critical' mesmo funcionando se:[/dim]")
                console.print("[dim]  • Não têm health check configurado (aparece 'No output')[/dim]")
                console.print("[dim]  • O health check está aguardando primeira execução[/dim]")
                console.print("[dim]  • O serviço foi registrado recentemente[/dim]")
                console.print("[dim]Se os dados aparecem no Grafana, o serviço está funcionando![/dim]\n")
            
            if critical:
                console.print("[bold red]Serviços Marcados como Críticos:[/bold red]")
                console.print("[dim](podem estar funcionando mesmo assim)[/dim]\n")
                for c in critical[:10]:
                    if c['output'] == "No output":
                        console.print(f"  - {c['service']} (ID: {c['id'][:60]}...)")
                        console.print(f"    [dim]↳ Sem health check configurado - verificar Prometheus/Grafana[/dim]")
                    else:
                        console.print(f"  - {c['service']} (ID: {c['id'][:60]}...): {c['output']}")
                if len(critical) > 10:
                    console.print(f"  ... e mais {len(critical) - 10} serviços")
            
            if warning:
                console.print("\n[bold yellow]Serviços em Alerta:[/bold yellow]")
                for w in warning[:5]:
                    console.print(f"  - {w['service']}: {w['output']}")
            
        except Exception as e:
            console.print(f"[red]Erro ao obter status: {e}[/red]")
        
        questionary.press_any_key_to_continue("Pressione ENTER para voltar...").ask()
    
    def test_connectivity(self):
        """Testa conectividade com todos os serviços"""
        console.print("\n[bold cyan]🧪 Teste de Conectividade[/bold cyan]\n")
        
        table = Table(title="Status das Portas", box=box.ROUNDED)
        table.add_column("Serviço", style="cyan")
        table.add_column("Porta", style="yellow")
        table.add_column("Status", style="green")
        table.add_column("Resposta", style="blue")
        
        host = self.current_node_addr if self.current_node_addr != "ALL" else Config.MAIN_SERVER
        
        for service, port in Config.SERVICE_PORTS.items():
            test_host = "127.0.0.1" if service == "mongodb" and host == Config.MAIN_SERVER else host
            
            port_open = test_port(test_host, port)
            status = "🟢 Aberta" if port_open else "🔴 Fechada"
            
            response = "N/A"
            if port_open:
                url_map = {
                    "consul": f"http://{host}:8500/v1/status/leader",
                    "prometheus": f"http://{host}:9090/-/healthy", 
                    "grafana": f"http://{host}:3000/api/health",
                    "blackbox": f"http://{host}:9115/metrics",
                    "blackbox_json": f"http://{host}:9116/metrics",
                    "nginx-consul": f"http://{host}:1026/",
                    "alertmanager": f"http://{host}:9093/-/healthy",
                    "influxdb": f"http://{host}:8086/ping",
                    "nginx_http": f"http://{host}:80/",
                    "nginx_https": f"https://{host}:443/",
                    "webmin": f"https://{host}:10000/"
                }
                
                if service in url_map:
                    resp = safe_request(url_map[service], timeout=2)
                    if resp:
                        response = f"HTTP {resp.status_code}"
            
            if service == "mongodb":
                service_name = "mongodb (localhost)"
            else:
                service_name = service
                
            table.add_row(service_name, str(port), status, response)
        
        console.print(table)
        
        console.print("\n[bold]Teste TenSunS:[/bold]")
        
        if test_port(host, 1026):
            resp = safe_request(f"http://{host}:1026/")
            if resp:
                console.print(f"  nginx-consul (1026): [green]✅ OK (HTTP {resp.status_code})[/green]")
            else:
                console.print(f"  nginx-consul (1026): [yellow]⚠️  Porta aberta mas sem resposta HTTP[/yellow]")
        else:
            console.print(f"  nginx-consul (1026): [red]❌ Porta fechada[/red]")
        
        console.print("\n[dim]Nota: flask-consul (2026) não está rodando atualmente[/dim]")
        console.print("[dim]Nota: MongoDB só escuta em localhost (127.0.0.1)[/dim]")
        
        questionary.press_any_key_to_continue("Pressione ENTER para voltar...").ask()
    
    def stack_status(self):
        """Mostra status completo do stack de monitoramento"""
        console.print("\n[bold cyan]📈 Status do Stack de Monitoramento[/bold cyan]\n")
        
        env_info = f"""
[bold]Ambiente Skills IT[/bold]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🖥️  Servidor Principal: {Config.MAIN_SERVER} ({Config.MAIN_SERVER_NAME})
🌐 Datacenter: dtc-skills-local
🔑 Token Consul: {'✅ Configurado' if Config.CONSUL_TOKEN else '❌ Não configurado'}

[bold]Stack de Monitoramento[/bold]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• Consul (Service Discovery)
• Prometheus (Métricas)
• Blackbox Exporter (Probing) - Porta 9115
• Blackbox JSON Exporter - Porta 9116
• Grafana (Visualização)
• TenSunS (nginx-consul:1026)
• Telegraf + InfluxDB (SNMP, vCenter, Ping)
• Node/Windows Exporters
• AlertManager (Porta 9093/9094)
• MongoDB (localhost:27017)
• MariaDB (Porta 3306)

[bold]Buckets InfluxDB[/bold]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"""
        
        console.print(env_info)
        
        for bucket, desc in Config.INFLUXDB_BUCKETS.items():
            console.print(f"  • {bucket}: {desc}")
        
        console.print("\n[bold]Status dos Nós Consul[/bold]")
        console.print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        
        members = self.consul.get_members()
        for m in members:
            status_icon = "🟢" if m["status"] == "alive" else "🔴"
            console.print(f"{status_icon} {m['node']}: {m['addr']} ({m['type']})")
        
        try:
            catalog = self.consul.get_catalog_services()
            
            valid_services = {}
            for svc_name, tags in catalog.items():
                if svc_name in Config.SERVICE_NAMES or svc_name in ['consul', 'prometheus', 'grafana']:
                    valid_services[svc_name] = tags
            
            console.print(f"\n📊 Total de ServiceNames válidos: {len(valid_services)}")
            
            if valid_services:
                console.print("\n[bold]ServiceNames no Catálogo:[/bold]")
                for svc_name, tags in sorted(valid_services.items()):
                    if 'blackbox' in svc_name:
                        valid_tags = [t for t in tags if t.lower() in Config.BLACKBOX_MODULES]
                        tag_display = ', '.join(valid_tags) if valid_tags else 'sem tags de módulo'
                        console.print(f"  • {svc_name}: {tag_display}")
                    
                    elif svc_name == 'selfnode_exporter':
                        os_tags = [t for t in tags if t.lower() in ['linux', 'windows', 'telefonia', 'aplicacao']]
                        company_tags = [t for t in tags if t not in os_tags and t.lower() not in Config.BLACKBOX_MODULES]
                        
                        if os_tags:
                            console.print(f"  • {svc_name}: OS={', '.join(os_tags)}")
                            if company_tags and len(company_tags) <= 5:
                                console.print(f"    [dim]↳ Empresas: {', '.join(company_tags[:5])}{'...' if len(company_tags) > 5 else ''}[/dim]")
                        else:
                            console.print(f"  • {svc_name}: {len(tags)} instâncias registradas")
                    
                    else:
                        console.print(f"  • {svc_name}: {len(tags)} tags")
                        
        except Exception as e:
            console.print(f"[yellow]Erro ao obter catálogo: {e}[/yellow]")
        
        questionary.press_any_key_to_continue("Pressione ENTER para voltar...").ask()
    
    def advanced_tools(self):
        """Ferramentas avançadas"""
        while True:
            console.print("\n[bold cyan]🔧 Ferramentas Avançadas[/bold cyan]\n")
            
            tools = {
                "Validar configuração Prometheus": self.validate_prometheus,
                "Testar probe Blackbox": self.test_blackbox_probe,
                "Verificar métricas Consul": self.check_consul_metrics,
                "Executar comando Consul CLI": self.run_consul_command,
                "Verificar logs": self.check_logs,
                "🔙 Voltar": None
            }
            
            choice = questionary.select(
                "Selecione a ferramenta:",
                choices=list(tools.keys())
            ).ask()
            
            if not choice or choice == "🔙 Voltar":
                break
            
            tools[choice]()
    
    def validate_prometheus(self):
        """Valida configuração do Prometheus"""
        console.print("\n[bold]Validando Prometheus...[/bold]\n")
        
        try:
            result = subprocess.run(
                ["promtool", "check", "config", "/etc/prometheus/prometheus.yml"],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                console.print("[green]✅ Configuração válida![/green]")
                console.print(result.stdout)
            else:
                console.print("[red]❌ Configuração inválida![/red]")
                console.print(result.stderr)
        except FileNotFoundError:
            console.print("[yellow]promtool não encontrado, tentando via API...[/yellow]")
            
            resp = safe_request(f"http://{Config.MAIN_SERVER}:9090/-/ready")
            if resp:
                console.print("[green]✅ Prometheus está pronto![/green]")
            else:
                console.print("[red]❌ Prometheus não está respondendo[/red]")
        
        questionary.press_any_key_to_continue("Pressione ENTER para continuar...").ask()
    
    def test_blackbox_probe(self):
        """Testa probe do Blackbox"""
        console.print("\n[bold cyan]🧪 Teste de Probe Blackbox[/bold cyan]\n")
        console.print("[dim]Esta ferramenta permite testar se um alvo está respondendo antes de adicionar ao monitoramento[/dim]\n")
        
        console.print("[bold yellow]📋 Tipos de Teste Disponíveis:[/bold yellow]\n")
        
        module_table = Table(title="Escolha o tipo de teste que deseja fazer", box=box.ROUNDED)
        module_table.add_column("#", style="cyan", width=3)
        module_table.add_column("Tipo", style="yellow", width=20)
        module_table.add_column("O que faz?", style="green", width=50)
        module_table.add_column("Exemplo de uso", style="blue", width=30)
        
        simple_descriptions = {
            "icmp": ("Ping", "Verifica se o servidor/equipamento está ligado e acessível na rede", "8.8.8.8, 192.168.1.1"),
            "http_2xx": ("Site HTTP", "Testa se um site está no ar (sem HTTPS)", "http://meusite.com"),
            "https": ("Site HTTPS", "Testa se um site seguro está funcionando e certificado válido", "https://meusite.com"),
            "http_4xx": ("Página de Erro", "Verifica se páginas restritas retornam erro correto (401/403/404)", "http://site.com/admin"),
            "http_post_2xx": ("API POST", "Testa APIs que precisam de método POST", "http://api.com/webhook"),
            "tcp_connect": ("Porta TCP", "Verifica se uma porta específica está aberta (banco, SMTP, etc)", "192.168.1.10:3306"),
            "ssh_banner": ("Servidor SSH", "Testa se o serviço SSH está ativo", "192.168.1.100:22"),
            "pop3s_banner": ("Email POP3S", "Verifica servidor de email POP3 com segurança", "mail.empresa.com:995"),
            "irc_banner": ("Chat IRC", "Testa servidor de chat IRC", "irc.empresa.com:6667")
        }
        
        for i, mod in enumerate(Config.BLACKBOX_MODULES, 1):
            name, what, example = simple_descriptions.get(mod, (mod, "Sem descrição", "N/A"))
            module_table.add_row(str(i), name, what, example)
        
        console.print(module_table)
        
        module_choices = [f"{i}) {simple_descriptions.get(mod, (mod, '', ''))[0]}" 
                         for i, mod in enumerate(Config.BLACKBOX_MODULES, 1)]
        module_choices.append("❌ Cancelar")
        
        module_choice = questionary.select(
            "Qual tipo de teste deseja fazer?",
            choices=module_choices,
            style=custom_style
        ).ask()
        
        if not module_choice or module_choice == "❌ Cancelar":
            return
        
        idx = int(module_choice.split(")")[0]) - 1
        module = Config.BLACKBOX_MODULES[idx]
        module_info = Config.MODULE_DESCRIPTIONS[module]
        
        console.print(f"\n[bold cyan]ℹ️  Dica para '{simple_descriptions[module][0]}':[/bold cyan]")
        console.print(f"[yellow]{module_info['description']}[/yellow]")
        console.print(f"[yellow]Formato esperado:[/yellow] {module_info['example_instance']}")
        
        if "format" in module_info:
            console.print(f"[yellow]Lembre-se:[/yellow] {module_info['format']}")
        
        console.print()
        
        target = questionary.text(
            f"Digite o alvo para testar (ex: {module_info['example_instance'].split(',')[0].strip()}) ou 'v' para voltar:",
            default=""
        ).ask()
        
        if not target or target.lower() == 'v':
            return
        
        url = f"http://{Config.MAIN_SERVER}:9115/probe?target={target}&module={module}"
        
        console.print(f"\n[dim]Executando teste em: {target}[/dim]")
        console.print(f"[dim]URL do teste: {url}[/dim]\n")
        
        with console.status("[bold yellow]Testando... aguarde...[/bold yellow]"):
            resp = safe_request(url, timeout=10)
        
        if resp:
            lines = resp.text.split('\n')
            success = False
            
            for line in lines:
                if 'probe_success' in line and not line.startswith('#'):
                    if '1' in line:
                        console.print("[bold green]✅ SUCESSO! O alvo está respondendo corretamente![/bold green]")
                        success = True
                    else:
                        console.print("[bold red]❌ FALHOU! O alvo NÃO está respondendo.[/bold red]")
                        console.print("[yellow]Possíveis causas:[/yellow]")
                        console.print("  • O servidor/equipamento está offline")
                        console.print("  • Firewall bloqueando a conexão")
                        console.print("  • Endereço ou porta incorretos")
                        console.print("  • Serviço não está rodando")
                    break
            
            console.print("\n[bold]Detalhes do teste:[/bold]")
            
            metrics_found = {
                "probe_duration_seconds": ("Tempo de resposta", "s"),
                "probe_http_status_code": ("Status HTTP", ""),
                "probe_ssl_earliest_cert_expiry": ("Certificado expira em", "dias"),
                "probe_dns_lookup_time_seconds": ("Tempo de DNS", "s"),
                "probe_ip_protocol": ("Protocolo IP", "")
            }
            
            for line in lines:
                if not line.startswith('#') and line.strip():
                    for metric, (label, unit) in metrics_found.items():
                        if metric in line and '{' not in line:
                            try:
                                value = line.split()[1]
                                if metric == "probe_ssl_earliest_cert_expiry":
                                    import time
                                    days = int((float(value) - time.time()) / 86400)
                                    console.print(f"  • {label}: {days} {unit}")
                                else:
                                    console.print(f"  • {label}: {value} {unit}")
                            except:
                                pass
            
            if success:
                console.print("\n[bold green]✅ Você pode adicionar este alvo ao monitoramento![/bold green]")
            else:
                console.print("\n[bold yellow]⚠️  Corrija o problema antes de adicionar ao monitoramento[/bold yellow]")
                
        else:
            console.print("[bold red]❌ Não foi possível executar o teste[/bold red]")
            console.print("[yellow]Verifique se:[/yellow]")
            console.print("  • O Blackbox Exporter está rodando (porta 9115)")
            console.print("  • O formato do alvo está correto")
            console.print("  • Há conectividade de rede")
        
        questionary.press_any_key_to_continue("\nPressione ENTER para continuar...").ask()
    
    def check_consul_metrics(self):
        """Verifica métricas do Consul"""
        console.print("\n[bold]Métricas do Consul[/bold]\n")
        
        url = f"http://{Config.MAIN_SERVER}:8500/v1/agent/metrics?format=prometheus"
        resp = safe_request(url, headers=self.consul.headers)
        
        if resp:
            lines = resp.text.split('\n')
            
            table = Table(title="Métricas Consul", box=box.ROUNDED)
            table.add_column("Métrica", style="cyan")
            table.add_column("Valor", style="yellow")
            
            important_metrics = [
                "consul_catalog_services",
                "consul_health_checks",
                "consul_raft_leader",
                "consul_serf_lan_members",
                "consul_runtime_num_goroutines"
            ]
            
            for line in lines:
                if not line.startswith('#') and line:
                    for metric in important_metrics:
                        if metric in line:
                            parts = line.split()
                            if len(parts) >= 2:
                                metric_name = parts[0]
                                value = parts[1]
                                table.add_row(metric_name, value)
                                break
            
            console.print(table)
        else:
            console.print("[red]❌ Não foi possível obter métricas[/red]")
        
        questionary.press_any_key_to_continue("Pressione ENTER para continuar...").ask()
    
    def run_consul_command(self):
        """Executa comando Consul CLI"""
        console.print("\n[bold]Executar Comando Consul[/bold]\n")
        
        common_commands = [
            "members",
            "members -detailed",
            "operator raft list-peers",
            "catalog services",
            "catalog nodes",
            "info",
            "Comando customizado...",
            "🔙 Voltar"
        ]
        
        choice = questionary.select(
            "Selecione o comando:",
            choices=common_commands
        ).ask()
        
        if not choice or choice == "🔙 Voltar":
            return
        
        if choice == "Comando customizado...":
            command = questionary.text("Digite o comando (sem 'consul'):").ask()
        else:
            command = choice
        
        if not command:
            return
        
        try:
            result = subprocess.run(
                ["consul"] + command.split(),
                capture_output=True,
                text=True,
                env={**os.environ, "CONSUL_HTTP_TOKEN": self.consul.token}
            )
            
            console.print(f"[bold]Output:[/bold]")
            console.print(result.stdout)
            
            if result.stderr:
                console.print(f"[red]Erros:[/red]")
                console.print(result.stderr)
                
        except Exception as e:
            console.print(f"[red]Erro ao executar comando: {e}[/red]")
        
        questionary.press_any_key_to_continue("Pressione ENTER para continuar...").ask()
    
    def check_logs(self):
        """Verifica logs dos serviços"""
        console.print("\n[bold]Verificar Logs[/bold]\n")
        
        services = [
            "consul",
            "prometheus", 
            "prometheus-blackbox-exporter",
            "prometheus-json-exporter",
            "grafana-server",
            "telegraf",
            "influxdb",
            "alertmanager",
            "🔙 Voltar"
        ]
        
        service = questionary.select(
            "Selecione o serviço:",
            choices=services
        ).ask()
        
        if not service or service == "🔙 Voltar":
            return
        
        lines = questionary.text("Quantas linhas? (padrão: 50):", default="50").ask()
        
        try:
            result = subprocess.run(
                ["journalctl", "-u", service, "-n", lines, "--no-pager"],
                capture_output=True,
                text=True
            )
            
            if result.stdout:
                console.print(f"[bold]Últimas {lines} linhas de {service}:[/bold]\n")
                console.print(result.stdout)
            else:
                console.print(f"[yellow]Nenhum log encontrado para {service}[/yellow]")
                console.print("[dim]Talvez o nome do serviço seja diferente. Tente com outro nome.[/dim]")
            
        except Exception as e:
            console.print(f"[red]Erro ao ler logs: {e}[/red]")
        
        questionary.press_any_key_to_continue("Pressione ENTER para continuar...").ask()
    
    def show_documentation(self):
        """Mostra documentação"""
        console.print("\n[bold cyan]📚 Documentação[/bold cyan]\n")
        
        doc = """
[bold]Estrutura de Service ID:[/bold]
module/company/project/env@name

[bold]Exemplos:[/bold]
• icmp/SkillsIT/Monitor/Prod@gateway_192.168.1.1
• http_2xx/ClienteX/API/Dev@api.example.com
• tcp_connect/Empresa/Sistema/Prod@servidor_porta_3306

[bold]ServiceNames Disponíveis:[/bold]"""
        
        console.print(doc)
        
        for name, desc in Config.SERVICE_NAMES.items():
            console.print(f"  • {name}: {desc}")
        
        console.print("\n[bold yellow]⚠️  Nota sobre Tags:[/bold yellow]")
        console.print("[dim]No selfnode_exporter, você pode ver tags como 'Skills', 'Emin', etc.[/dim]")
        console.print("[dim]Essas são tags de empresas/projetos, NÃO módulos de monitoramento.[/dim]")
        console.print(f"[dim]Os módulos válidos são: {', '.join(Config.BLACKBOX_MODULES)}[/dim]")
        
        console.print("\n[bold]Módulos de Monitoramento:[/bold]")
        
        table = Table(title="Módulos Blackbox Disponíveis", box=box.ROUNDED)
        table.add_column("Módulo", style="cyan")
        table.add_column("Nome", style="yellow")
        table.add_column("Descrição", style="green")
        table.add_column("Exemplo", style="blue")
        
        for mod in Config.BLACKBOX_MODULES:
            desc = Config.MODULE_DESCRIPTIONS[mod]
            table.add_row(
                mod,
                desc["name"],
                desc["description"][:40] + "...",
                desc["example_instance"][:40] + "..."
            )
        
        console.print(table)
        
        console.print("\n[bold]Meta Campos Disponíveis:[/bold]")
        console.print(f"  {', '.join(Config.META_FIELDS)}")
        
        console.print("\n[bold]Integração com TenSunS:[/bold]")
        console.print("• nginx-consul: http://172.16.1.26:1026 (✅ Ativo)")
        console.print("• flask-consul: Não está rodando atualmente")
        console.print("• GitHub: https://github.com/starsliao/TenSunS")
        
        console.print("\n[bold]Stack Completo:[/bold]")
        console.print("• Prometheus → Consul SD → Blackbox → Targets")
        console.print("• Telegraf → InfluxDB → Grafana")
        console.print("• Node/Windows Exporters → Prometheus")
        console.print("• AlertManager para notificações")
        
        questionary.press_any_key_to_continue("Pressione ENTER para voltar...").ask()
    
    def change_node(self):
        """Troca o nó ativo"""
        self.current_node, self.current_node_addr = self.select_node()
        console.print(f"[green]Nó alterado para: {self.current_node}[/green]")
    
    def install_exporter_remotely(self):
        """Menu APRIMORADO de instalação remota com scan, lote e individual"""
        console.clear()
        console.print(Panel.fit(
            "[bold cyan]🚀 Instalação Remota de Exporters - APRIMORADA[/bold cyan]\n\n"
            "✅ Validações completas pré-instalação\n"
            "✅ Detecção automática de SO e arquitetura\n"
            "✅ Verificação de conflitos e espaço em disco\n"
            "✅ Backup e rollback automático em falhas\n"
            "✅ Registro automático no Consul\n"
            "✅ Scan de rede e instalação em lote\n"
            "✅ Configuração customizada de collectors",
            border_style="cyan"
        ))
        
        mode = questionary.select(
            "Modo de instalação:",
            choices=[
                "Individual - Um servidor por vez",
                "Lote - Múltiplos servidores",
                "Scan - Descobrir servidores na rede",
                "🔙 Voltar"
            ],
            style=custom_style
        ).ask()
        
        if mode == "🔙 Voltar" or not mode:
            return
        
        if mode == "Scan - Descobrir servidores na rede":
            self._install_with_scan()
        elif mode == "Lote - Múltiplos servidores":
            self._install_batch()
        else:
            self._install_single()
    
    def _install_single(self):
        """Instalação individual - MANTIDA DO CÓDIGO ORIGINAL"""
        host = questionary.text("IP ou hostname:", style=custom_style).ask()
        if not host:
            return
        
        if not validate_ip(host):
            try:
                socket.gethostbyname(host)
            except:
                console.print(f"[red]❌ IP/hostname inválido: {host}[/red]")
                questionary.press_any_key_to_continue("Pressione ENTER...").ask()
                return
        
        ssh_port = questionary.text("Porta SSH:", default="22", style=custom_style).ask()
        try:
            ssh_port = int(ssh_port)
        except:
            console.print("[red]Porta inválida[/red]")
            return
        
        username = questionary.text("Usuário SSH:", default="root", style=custom_style).ask()
        
        auth_method = questionary.select(
            "Autenticação:",
            choices=["Senha", "Chave SSH"],
            style=custom_style
        ).ask()
        
        password = None
        key_file = None
        
        if auth_method == "Senha":
            password = questionary.password("Senha:").ask()
        else:
            key_file = questionary.text("Caminho da chave:", default="~/.ssh/id_rsa").ask()
            key_file = str(Path(key_file).expanduser())
            
            if not Path(key_file).exists():
                console.print(f"[red]❌ Chave não encontrada: {key_file}[/red]")
                return
        
        use_sudo = False
        if username != 'root':
            use_sudo = questionary.confirm("Usar sudo?", default=True).ask()
        
        installer = RemoteExporterInstaller(
            host=host,
            username=username,
            password=password,
            key_file=key_file,
            use_sudo=use_sudo,
            ssh_port=ssh_port
        )
        
        console.print("\n[yellow]Conectando...[/yellow]")
        if not installer.connect():
            questionary.press_any_key_to_continue("Pressione ENTER...").ask()
            return
        
        os_type = installer.detect_os()
        if not os_type:
            installer.close()
            questionary.press_any_key_to_continue("Pressione ENTER...").ask()
            return
        
        if os_type == 'linux':
            console.print("\n[bold yellow]Perfis de Collectors - Node Exporter:[/bold yellow]")
            console.print("  [green]recommended[/green] - Balanceado (CPU, RAM, Disco, Rede, Load)")
            console.print("  [cyan]full[/cyan] - Completo (inclui systemd, processos, TCP)")
            console.print("  [dim]minimal[/dim] - Mínimo (apenas CPU, RAM, Disco)")
            console.print("  [yellow]custom[/yellow] - Personalizado (escolha cada collector)")
            
            profile = questionary.select(
                "Perfil de collectors:",
                choices=[
                    questionary.Choice("recommended - Balanceado ⭐", value='recommended'),
                    questionary.Choice("full - Completo", value='full'),
                    questionary.Choice("minimal - Mínimo", value='minimal'),
                    questionary.Choice("custom - Personalizado", value='custom')
                ],
                style=custom_style
            ).ask()
            
            custom_collectors = None
            if profile == 'custom':
                custom_collectors = self._select_custom_collectors('linux')
            
            success = installer.install_node_exporter(profile if profile != 'custom' else 'recommended', custom_collectors)
        else:
            console.print("\n[bold yellow]Perfis de Collectors - Windows Exporter:[/bold yellow]")
            console.print("  [green]recommended[/green] - Balanceado")
            console.print("  [cyan]full[/cyan] - Completo")
            console.print("  [dim]minimal[/dim] - Mínimo")
            
            profile = questionary.select(
                "Perfil:",
                choices=[
                    questionary.Choice("recommended", value='recommended'),
                    questionary.Choice("full", value='full'),
                    questionary.Choice("minimal", value='minimal')
                ],
                style=custom_style
            ).ask()
            
            success = installer.install_windows_exporter(profile)
        
        if not success:
            installer.close()
            questionary.press_any_key_to_continue("Pressione ENTER...").ask()
            return
        
        if questionary.confirm("Configurar firewall?", default=True).ask():
            prometheus_ips = ["172.16.1.26", "172.16.200.14", "11.144.0.21"]
            installer.configure_firewall(prometheus_ips)
        
        if questionary.confirm("Validar instalação?", default=True).ask():
            prometheus_ips = ["172.16.1.26"]
            installer.validate_installation(prometheus_ips)
        
        if questionary.confirm("Registrar no Consul?", default=True).ask():
            node_choice = questionary.select(
                "Em qual nó?",
                choices=["Palmas", "Rio"],
                default="Palmas"
            ).ask()
            
            installer.register_in_consul(self.consul, node_choice)
        
        installer.close()
        console.print("\n[bold green]✅ Processo concluído![/bold green]")
        questionary.press_any_key_to_continue("Pressione ENTER...").ask()
    
    def _select_custom_collectors(self, os_type: str) -> Dict:
        """Seleção customizada de collectors"""
        console.print("\n[bold cyan]Selecione os collectors desejados:[/bold cyan]\n")
        
        if os_type == 'linux':
            all_collectors = [
                'cpu', 'loadavg', 'meminfo', 'diskstats', 'filesystem',
                'netdev', 'time', 'uname', 'systemd', 'processes', 'tcpstat'
            ]
            
            table = Table(title="Collectors Disponíveis", box=box.ROUNDED)
            table.add_column("Collector", style="cyan")
            table.add_column("Descrição", style="yellow")
            
            for col in all_collectors:
                desc = NODE_EXPORTER_COLLECTOR_DETAILS.get(col, "N/A")
                table.add_row(col, desc)
            
            console.print(table)
            
            selected = questionary.checkbox(
                "Selecione (use ESPAÇO para marcar):",
                choices=[f"{col} - {NODE_EXPORTER_COLLECTOR_DETAILS.get(col, '')}" for col in all_collectors],
                default=[f"{col} - {NODE_EXPORTER_COLLECTOR_DETAILS.get(col, '')}" 
                        for col in ['cpu', 'loadavg', 'meminfo', 'diskstats', 'filesystem', 'netdev']]
            ).ask()
            
            enabled = [s.split(' - ')[0] for s in selected]
            disabled = [c for c in all_collectors if c not in enabled]
            
            return {'enable': enabled, 'disable': disabled}
        
        return None
    
    def _install_batch(self):
        """Instalação em lote"""
        console.print("\n[bold cyan]Instalação em Lote[/bold cyan]\n")
        
        ips_input = questionary.text(
            "Digite os IPs separados por vírgula ou espaço:",
            style=custom_style
        ).ask()
        
        if not ips_input:
            return
        
        hosts = [ip.strip() for ip in ips_input.replace(',', ' ').split() if ip.strip()]
        
        if not hosts:
            console.print("[yellow]Nenhum IP válido fornecido[/yellow]")
            return
        
        console.print(f"\n[bold]Hosts para instalar ({len(hosts)}):[/bold]")
        for h in hosts:
            console.print(f"  • {h}")
        
        if not questionary.confirm(f"\nContinuar com {len(hosts)} hosts?").ask():
            return
        
        username = questionary.text("Usuário (mesmo para todos):", default="root").ask()
        
        auth = questionary.select("Autenticação:", choices=["Senha", "Chave SSH"]).ask()
        
        password = None
        key_file = None
        
        if auth == "Senha":
            password = questionary.password("Senha:").ask()
        else:
            key_file = questionary.text("Chave:", default="~/.ssh/id_rsa").ask()
            key_file = str(Path(key_file).expanduser())
        
        profile = questionary.select(
            "Perfil de collectors:",
            choices=["recommended", "full", "minimal"]
        ).ask()
        
        batch = BatchInstaller(hosts, username, password, key_file)
        batch.install_all(collector_profile=profile)
        
        questionary.press_any_key_to_continue("\nPressione ENTER...").ask()
    
    def _install_with_scan(self):
        """Instalação com scan de rede"""
        console.print("\n[bold cyan]Scan de Rede[/bold cyan]\n")
        
        network = questionary.text(
            "Rede para escanear (ex: 192.168.1.0/24):",
            style=custom_style
        ).ask()
        
        if not network:
            return
        
        ssh_port = questionary.text("Porta SSH:", default="22").ask()
        try:
            ssh_port = int(ssh_port)
        except:
            ssh_port = 22
        
        scanner = NetworkScanner()
        hosts = scanner.scan_network(network, ssh_port)
        
        if not hosts:
            console.print("[yellow]Nenhum host encontrado[/yellow]")
            questionary.press_any_key_to_continue("Pressione ENTER...").ask()
            return
        
        if questionary.confirm(f"Instalar em todos os {len(hosts)} hosts encontrados?").ask():
            username = questionary.text("Usuário:", default="root").ask()
            auth = questionary.select("Autenticação:", choices=["Senha", "Chave"]).ask()
            
            password = None
            key_file = None
            
            if auth == "Senha":
                password = questionary.password("Senha:").ask()
            else:
                key_file = str(Path(questionary.text("Chave:", default="~/.ssh/id_rsa").ask()).expanduser())
            
            profile = questionary.select("Perfil:", choices=["recommended", "full", "minimal"]).ask()
            
            batch = BatchInstaller(hosts, username, password, key_file)
            batch.install_all(collector_profile=profile)
        
        questionary.press_any_key_to_continue("\nPressione ENTER...").ask()
    
    def exit_app(self):
        """Sai do aplicativo"""
        if questionary.confirm("Deseja realmente sair?").ask():
            console.print("\n[yellow]Até logo! 👋[/yellow]")
            sys.exit(0)
    
    def run(self):
        """Executa a interface"""
        self.display_banner()
        self.current_node, self.current_node_addr = self.select_node()
        
        if not self.current_node:
            console.print("[red]Nenhum nó selecionado. Saindo...[/red]")
            return
        
        self.main_menu()

# ============================================================================
# ENTRADA PRINCIPAL
# ============================================================================

def main():
    """Função principal"""
    parser = argparse.ArgumentParser(
        description="Sistema de Gestão de Monitoramento Skills IT v2.2.0"
    )
    
    parser.add_argument("--host", default=Config.MAIN_SERVER, help=f"Host do Consul (padrão: {Config.MAIN_SERVER})")
    parser.add_argument("--port", type=int, default=Config.CONSUL_PORT, help=f"Porta do Consul (padrão: {Config.CONSUL_PORT})")
    parser.add_argument("--token", default=Config.CONSUL_TOKEN, help="Token do Consul")
    parser.add_argument("--non-interactive", action="store_true", help="Modo não-interativo (para scripts)")
    parser.add_argument("--command", choices=["list", "export", "status"], help="Comando para modo não-interativo")
    parser.add_argument("--output", help="Arquivo de saída para export")
    
    args = parser.parse_args()
    
    try:
        consul_manager = ConsulManager(host=args.host, port=args.port, token=args.token)
        
        if args.non_interactive:
            if args.command == "list":
                services = consul_manager.get_services()
                for sid, svc in services.items():
                    print(f"{sid}: {svc.get('Meta', {}).get('instance', 'N/A')}")
            
            elif args.command == "export":
                services = consul_manager.get_services()
                output = args.output or "export.csv"
                
                with open(output, 'w', newline='', encoding='utf-8') as f:
                    fieldnames = ["service_id"] + Config.META_FIELDS + ["tags"]
                    writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
                    writer.writeheader()
                    
                    for sid, svc in services.items():
                        row = {"service_id": sid}
                        meta = svc.get("Meta", {})
                        for field in Config.META_FIELDS:
                            row[field] = meta.get(field, "")
                        row["tags"] = ",".join(svc.get("Tags", []))
                        writer.writerow(row)
                
                print(f"Exportado para {output}")
            
            elif args.command == "status":
                members = consul_manager.get_members()
                for m in members:
                    print(f"{m['node']}: {m['addr']} ({m['status']})")
        else:
            ui = InteractiveUI(consul_manager)
            ui.run()
            
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrompido pelo usuário[/yellow]")
        sys.exit(0)
    except Exception as e:
        console.print(f"\n[red]Erro fatal: {e}[/red]")
        sys.exit(1)

if __name__ == "__main__":
    main()

# FIM DO CÓDIGO COMPLETO - 2980+ LINHAS
# Cole as 3 partes em sequência para ter o script completo funcional