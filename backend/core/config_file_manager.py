"""
Gerenciador para leitura de arquivos de configuração remotos (Prometheus, Alertmanager, Blackbox, etc.).

Os servidores e credenciais são definidos via variáveis de ambiente:

  CONFIG_HOSTS             -> JSON com a lista de hosts permitidos
  CONFIG_HOSTS_FILE        -> Caminho para arquivo JSON contendo a configuração (opcional)

Cada host possui os campos:
  id              (str)   identificador único (usado na URL)
  name            (str)   nome amigável exibido no frontend
  description     (str)   descrição opcional
  host            (str)   endereço/IP do servidor
  port            (int)   porta SSH (default: 22)
  username        (str)   usuário SSH
  password        (str)   senha SSH (opcional se usar chave)
  ssh_key_path    (str)   caminho para chave privada (opcional)
  ssh_key         (str)   chave privada inline em formato PEM (opcional)
  ssh_key_passphrase (str) senha da chave privada, se necessário
  files           (list)  lista de caminhos absolutos dos arquivos .yml que podem ser visualizados
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime
from io import StringIO
from typing import Dict, List, Optional, Tuple

import paramiko


@dataclass
class ConfigHost:
    """Representa um servidor alvo configurado para leitura de arquivos."""

    id: str
    name: str
    host: str
    username: str
    port: int = 22
    description: Optional[str] = None
    password: Optional[str] = None
    ssh_key_path: Optional[str] = None
    ssh_key: Optional[str] = None
    ssh_key_passphrase: Optional[str] = None
    files: List[str] = field(default_factory=list)

    def summary(self) -> Dict[str, Optional[str]]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
        }


class ConfigFileManager:
    """Orquestra conexões SSH/SFTP para leitura dos arquivos de configuração."""

    def __init__(self) -> None:
        self._hosts: Dict[str, ConfigHost] = {}
        self._env_signature: Tuple[Optional[str], Optional[str]] = (None, None)
        self._load_hosts()

    # --------------------------------------------------------------------- #
    # Host loading
    # --------------------------------------------------------------------- #
    def _load_hosts(self) -> None:
        raw_env = os.getenv("CONFIG_HOSTS")
        file_path = os.getenv("CONFIG_HOSTS_FILE")
        signature = (raw_env, file_path)
        if signature == self._env_signature:
            return

        hosts: Dict[str, ConfigHost] = {}

        payload: List[Dict] = []
        if raw_env:
            try:
                parsed = json.loads(raw_env)
                if isinstance(parsed, dict):
                    payload = [parsed]
                elif isinstance(parsed, list):
                    payload = parsed
            except json.JSONDecodeError as exc:
                raise ValueError(f"CONFIG_HOSTS inválido: {exc}") from exc
        elif file_path:
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"Arquivo em CONFIG_HOSTS_FILE não encontrado: {file_path}")
            with open(file_path, "r", encoding="utf-8") as handle:
                try:
                    parsed_file = json.load(handle)
                    if isinstance(parsed_file, dict):
                        payload = [parsed_file]
                    elif isinstance(parsed_file, list):
                        payload = parsed_file
                except json.JSONDecodeError as exc:
                    raise ValueError(f"Arquivo CONFIG_HOSTS_FILE inválido: {exc}") from exc

        for entry in payload:
            host_id = entry.get("id") or entry.get("host")
            if not host_id:
                continue

            files = entry.get("files") or []
            if not isinstance(files, list):
                files = [files]

            hosts[host_id] = ConfigHost(
                id=host_id,
                name=entry.get("name") or host_id,
                description=entry.get("description"),
                host=entry.get("host") or "",
                port=int(entry.get("port") or 22),
                username=entry.get("username") or entry.get("user") or "root",
                password=entry.get("password"),
                ssh_key_path=entry.get("ssh_key_path"),
                ssh_key=entry.get("ssh_key"),
                ssh_key_passphrase=entry.get("ssh_key_passphrase"),
                files=[str(path) for path in files],
            )

        self._hosts = hosts
        self._env_signature = signature

    def _ensure_hosts(self) -> None:
        self._load_hosts()

    # --------------------------------------------------------------------- #
    # Public helpers
    # --------------------------------------------------------------------- #
    def list_hosts(self) -> List[Dict[str, Optional[str]]]:
        self._ensure_hosts()
        return [host.summary() for host in self._hosts.values()]

    def get_host(self, host_id: str) -> ConfigHost:
        self._ensure_hosts()
        host = self._hosts.get(host_id)
        if not host:
            raise KeyError(f"Host '{host_id}' não configurado")
        return host

    # --------------------------------------------------------------------- #
    # SSH/SFTP helpers
    # --------------------------------------------------------------------- #
    def _build_private_key(self, host: ConfigHost) -> Optional[paramiko.PKey]:
        """Carrega chave privada a partir de caminho ou string PEM."""
        key_data: Optional[str] = None
        if host.ssh_key:
            key_data = host.ssh_key
        elif host.ssh_key_path and os.path.exists(host.ssh_key_path):
            with open(host.ssh_key_path, "r", encoding="utf-8") as handle:
                key_data = handle.read()

        if not key_data:
            return None

        key_stream = StringIO(key_data)
        password = host.ssh_key_passphrase

        for key_cls in (
            paramiko.RSAKey,
            paramiko.DSSKey,
            paramiko.ECDSAKey,
            paramiko.Ed25519Key,
        ):
            key_stream.seek(0)
            try:
                return key_cls.from_private_key(
                    key_stream,
                    password=password,
                )
            except (paramiko.SSHException, ValueError):
                continue

        raise ValueError("Não foi possível carregar a chave privada fornecida")

    def _connect(self, host: ConfigHost) -> paramiko.SSHClient:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        kwargs = {
            "hostname": host.host,
            "port": host.port,
            "username": host.username,
            "timeout": 10,
            "look_for_keys": False,
            "allow_agent": False,
        }

        pkey = None
        try:
            pkey = self._build_private_key(host)
        except ValueError as exc:
            raise ValueError(f"Chave privada inválida para host {host.id}: {exc}") from exc

        if pkey:
            kwargs["pkey"] = pkey

        if host.password and not pkey:
            kwargs["password"] = host.password
        elif host.password and pkey:
            # Paramiko suporta password + pkey (para passphrase de key), mas manteremos password para sudo/ssh.
            kwargs["password"] = host.password

        if "password" not in kwargs and "pkey" not in kwargs:
            raise ValueError(f"Nenhuma credencial fornecida para o host {host.id}")

        try:
            client.connect(**kwargs)
        except paramiko.AuthenticationException as exc:
            raise PermissionError(f"Falha de autenticação ao conectar no host {host.id}") from exc
        except paramiko.SSHException as exc:
            raise ConnectionError(f"Erro SSH ao conectar no host {host.id}: {exc}") from exc
        except Exception as exc:  # pragma: no cover - erro inesperado
            raise ConnectionError(f"Não foi possível conectar ao host {host.id}: {exc}") from exc

        return client

    # --------------------------------------------------------------------- #
    # File operations
    # --------------------------------------------------------------------- #
    def list_files(self, host_id: str) -> List[Dict[str, Optional[str]]]:
        host = self.get_host(host_id)
        if not host.files:
            return []

        client = self._connect(host)
        try:
            sftp = client.open_sftp()
            files_info: List[Dict[str, Optional[str]]] = []
            for path in host.files:
                info: Dict[str, Optional[str]] = {"path": path}
                try:
                    stat = sftp.stat(path)
                    info["size"] = stat.st_size
                    info["modified"] = datetime.fromtimestamp(stat.st_mtime).isoformat()
                except FileNotFoundError:
                    info["size"] = None
                    info["modified"] = None
                except Exception:
                    info["size"] = None
                    info["modified"] = None
                files_info.append(info)
            return files_info
        finally:
            try:
                client.close()
            except Exception:
                pass

    def read_file(self, host_id: str, file_path: str) -> str:
        host = self.get_host(host_id)
        if host.files and file_path not in host.files:
            raise PermissionError("Arquivo solicitado não está na lista permitida")

        client = self._connect(host)
        try:
            sftp = client.open_sftp()
            with sftp.file(file_path, "r") as remote_file:
                data = remote_file.read()
            return data.decode("utf-8", errors="replace")
        except FileNotFoundError as exc:
            raise FileNotFoundError(f"Arquivo {file_path} não encontrado no host {host_id}") from exc
        finally:
            try:
                client.close()
            except Exception:
                pass

