"""
Serviço de Gerenciamento de Configurações YAML do Prometheus

Este módulo fornece funcionalidades para:
- Ler e parsear arquivos prometheus.yml
- Extrair estrutura de jobs e relabel_configs
- Gerar YAML validado
- Gerenciar backups
- Recarregar Prometheus

IMPORTANTE: YAML é a ÚNICA fonte da verdade.
Não duplicamos dados em banco de dados.
"""

from ruamel.yaml import YAML
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
import shutil
import subprocess
import requests
import json
import logging
import os
from dotenv import load_dotenv
import paramiko
from io import StringIO

logger = logging.getLogger(__name__)

load_dotenv()


class YamlConfigService:
    """Serviço para manipular configurações YAML do Prometheus"""

    def __init__(self, config_path: str = None):
        """
        Inicializa o serviço

        Args:
            config_path: Caminho para o prometheus.yml (se None, lê do .env)
        """
        # Ler configurações do .env
        self.config_path = Path(config_path or os.getenv('PROMETHEUS_CONFIG_PATH', '/etc/prometheus/prometheus.yml'))
        self.ssh_host = os.getenv('PROMETHEUS_CONFIG_SSH_HOST')
        self.ssh_user = os.getenv('PROMETHEUS_CONFIG_SSH_USER', 'prometheus')
        self.ssh_key_path = os.getenv('PROMETHEUS_CONFIG_SSH_KEY')
        self.prometheus_host = os.getenv('PROMETHEUS_HOST', 'localhost')
        self.prometheus_port = os.getenv('PROMETHEUS_PORT', '9090')
        self.promtool_path = os.getenv('PROMTOOL_PATH', 'promtool')

        # URLs
        self.prometheus_url = f"http://{self.prometheus_host}:{self.prometheus_port}"

        # Determinar se é acesso remoto via SSH
        self.use_ssh = bool(self.ssh_host and self.ssh_user)

        # Diretório de backups (local)
        self.backup_dir = Path("backups/prometheus")
        self.backup_dir.mkdir(parents=True, exist_ok=True)

        # Configurar ruamel.yaml para preservar formatação
        self.yaml = YAML()
        self.yaml.preserve_quotes = True
        self.yaml.default_flow_style = None  # None = preservar estilo original (flow ou block)
        self.yaml.width = 4096
        self.yaml.indent(mapping=2, sequence=2, offset=0)

        logger.info(f"YamlConfigService inicializado:")
        logger.info(f"  - Config path: {self.config_path}")
        logger.info(f"  - SSH mode: {self.use_ssh}")
        if self.use_ssh:
            logger.info(f"  - SSH: {self.ssh_user}@{self.ssh_host}")
        logger.info(f"  - Prometheus: {self.prometheus_url}")

    def _get_ssh_client(self) -> paramiko.SSHClient:
        """
        Cria cliente SSH

        Returns:
            Cliente SSH conectado
        """
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        # Conectar com chave SSH ou senha
        if self.ssh_key_path and os.path.exists(self.ssh_key_path):
            client.connect(
                hostname=self.ssh_host,
                username=self.ssh_user,
                key_filename=self.ssh_key_path
            )
        else:
            # Tentar sem senha (assume que chave está em ~/.ssh/)
            client.connect(
                hostname=self.ssh_host,
                username=self.ssh_user,
                look_for_keys=True
            )

        return client

    def _read_file_ssh(self, file_path: Path) -> str:
        """
        Lê arquivo via SSH

        Args:
            file_path: Caminho do arquivo remoto

        Returns:
            Conteúdo do arquivo
        """
        client = self._get_ssh_client()
        try:
            sftp = client.open_sftp()
            with sftp.open(str(file_path), 'r') as f:
                content = f.read().decode('utf-8')
            sftp.close()
            return content
        finally:
            client.close()

    def _write_file_ssh(self, file_path: Path, content: str):
        """
        Escreve arquivo via SSH

        Args:
            file_path: Caminho do arquivo remoto
            content: Conteúdo a escrever
        """
        client = self._get_ssh_client()
        try:
            sftp = client.open_sftp()
            with sftp.open(str(file_path), 'w') as f:
                f.write(content.encode('utf-8'))
            sftp.close()
        finally:
            client.close()

    def read_config(self) -> Dict[str, Any]:
        """
        Lê e parseia o arquivo prometheus.yml

        Returns:
            Dict com a configuração completa

        Raises:
            FileNotFoundError: Se arquivo não existe
            yaml.YAMLError: Se YAML é inválido
        """
        try:
            if self.use_ssh:
                # Ler via SSH
                content = self._read_file_ssh(self.config_path)
                config = self.yaml.load(StringIO(content))
                logger.info(f"Configuração lida via SSH de {self.ssh_host}:{self.config_path}")
            else:
                # Ler local
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    config = self.yaml.load(f)
                logger.info(f"Configuração lida de {self.config_path}")

            return config

        except FileNotFoundError:
            logger.error(f"Arquivo não encontrado: {self.config_path}")
            raise
        except Exception as e:
            logger.error(f"Erro ao ler configuração: {e}")
            raise

    def get_all_jobs(self) -> List[Dict[str, Any]]:
        """
        Extrai todos os scrape jobs da configuração

        Returns:
            Lista de jobs com estrutura completa
        """
        config = self.read_config()
        scrape_configs = config.get('scrape_configs', [])

        jobs = []
        for idx, job in enumerate(scrape_configs):
            job_data = {
                'index': idx,
                'job_name': job.get('job_name'),
                'scrape_interval': job.get('scrape_interval'),
                'scrape_timeout': job.get('scrape_timeout'),
                'metrics_path': job.get('metrics_path', '/metrics'),
                'scheme': job.get('scheme', 'http'),
                'honor_labels': job.get('honor_labels', False),
                'honor_timestamps': job.get('honor_timestamps', True),
                'params': job.get('params', {}),
                'basic_auth': job.get('basic_auth'),
                'bearer_token': job.get('bearer_token'),
                'bearer_token_file': job.get('bearer_token_file'),
                'tls_config': job.get('tls_config'),
                'proxy_url': job.get('proxy_url'),
                'consul_sd_configs': job.get('consul_sd_configs', []),
                'static_configs': job.get('static_configs', []),
                'file_sd_configs': job.get('file_sd_configs', []),
                'relabel_configs': job.get('relabel_configs', []),
                'metric_relabel_configs': job.get('metric_relabel_configs', []),
            }

            # Limpar campos None/vazios
            job_data = {k: v for k, v in job_data.items() if v is not None and v != {} and v != []}

            jobs.append(job_data)

        logger.info(f"Extraídos {len(jobs)} jobs")
        return jobs

    def get_job_by_name(self, job_name: str) -> Optional[Dict[str, Any]]:
        """
        Busca um job específico pelo nome

        Args:
            job_name: Nome do job

        Returns:
            Dados do job ou None se não encontrado
        """
        jobs = self.get_all_jobs()
        for job in jobs:
            if job.get('job_name') == job_name:
                return job
        return None

    def create_job(self, job_data: Dict[str, Any]) -> bool:
        """
        Adiciona um novo job à configuração

        Args:
            job_data: Dados do novo job

        Returns:
            True se sucesso

        Raises:
            ValueError: Se job_name já existe
        """
        config = self.read_config()

        # Validar se job_name já existe
        job_name = job_data.get('job_name')
        if not job_name:
            raise ValueError("job_name é obrigatório")

        existing_jobs = config.get('scrape_configs', [])
        if any(j.get('job_name') == job_name for j in existing_jobs):
            raise ValueError(f"Job '{job_name}' já existe")

        # Adicionar novo job
        existing_jobs.append(job_data)
        config['scrape_configs'] = existing_jobs

        # Salvar
        return self.save_config(config, f"Adicionado job '{job_name}'")

    def update_job(self, job_name: str, job_data: Dict[str, Any]) -> bool:
        """
        Atualiza um job existente

        Args:
            job_name: Nome do job a atualizar
            job_data: Novos dados do job

        Returns:
            True se sucesso

        Raises:
            ValueError: Se job não existe
        """
        config = self.read_config()
        scrape_configs = config.get('scrape_configs', [])

        # Encontrar job
        job_index = None
        for idx, job in enumerate(scrape_configs):
            if job.get('job_name') == job_name:
                job_index = idx
                break

        if job_index is None:
            raise ValueError(f"Job '{job_name}' não encontrado")

        # Atualizar job
        scrape_configs[job_index] = job_data
        config['scrape_configs'] = scrape_configs

        # Salvar
        return self.save_config(config, f"Atualizado job '{job_name}'")

    def delete_job(self, job_name: str) -> bool:
        """
        Remove um job da configuração

        Args:
            job_name: Nome do job a remover

        Returns:
            True se sucesso

        Raises:
            ValueError: Se job não existe
        """
        config = self.read_config()
        scrape_configs = config.get('scrape_configs', [])

        # Filtrar job
        new_configs = [j for j in scrape_configs if j.get('job_name') != job_name]

        if len(new_configs) == len(scrape_configs):
            raise ValueError(f"Job '{job_name}' não encontrado")

        config['scrape_configs'] = new_configs

        # Salvar
        return self.save_config(config, f"Removido job '{job_name}'")

    def save_config(self, config: Dict[str, Any], reason: str = "Manual edit") -> bool:
        """
        Salva configuração no arquivo (com backup automático)

        Args:
            config: Configuração completa
            reason: Motivo da mudança (para audit log)

        Returns:
            True se sucesso
        """
        try:
            # 1. Validar YAML com promtool
            if not self.validate_config(config):
                raise ValueError("Configuração inválida segundo promtool")

            # 2. Criar backup
            backup_path = self.create_backup(reason)
            logger.info(f"Backup criado: {backup_path}")

            # 3. Salvar nova configuração
            with open(self.config_path, 'w', encoding='utf-8') as f:
                self.yaml.dump(config, f)

            logger.info(f"Configuração salva: {reason}")

            # 4. Registrar no audit log
            self._log_change(reason, backup_path)

            return True

        except Exception as e:
            logger.error(f"Erro ao salvar configuração: {e}")
            raise

    def create_backup(self, reason: str = "") -> Path:
        """
        Cria backup do arquivo atual

        Args:
            reason: Motivo do backup

        Returns:
            Path do arquivo de backup criado
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"prometheus_{timestamp}.yml"
        backup_path = self.backup_dir / backup_filename

        shutil.copy2(self.config_path, backup_path)

        # Salvar metadados do backup
        metadata = {
            'timestamp': timestamp,
            'reason': reason,
            'original_file': str(self.config_path),
            'backup_file': str(backup_path)
        }

        metadata_path = backup_path.with_suffix('.json')
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)

        return backup_path

    def list_backups(self) -> List[Dict[str, Any]]:
        """
        Lista todos os backups disponíveis

        Returns:
            Lista de backups com metadados
        """
        backups = []

        for backup_file in sorted(self.backup_dir.glob("prometheus_*.yml"), reverse=True):
            metadata_file = backup_file.with_suffix('.json')

            backup_info = {
                'filename': backup_file.name,
                'path': str(backup_file),
                'size': backup_file.stat().st_size,
                'created': datetime.fromtimestamp(backup_file.stat().st_mtime).isoformat()
            }

            # Adicionar metadados se existirem
            if metadata_file.exists():
                with open(metadata_file) as f:
                    metadata = json.load(f)
                backup_info.update(metadata)

            backups.append(backup_info)

        return backups

    def restore_backup(self, backup_filename: str) -> bool:
        """
        Restaura um backup

        Args:
            backup_filename: Nome do arquivo de backup

        Returns:
            True se sucesso
        """
        backup_path = self.backup_dir / backup_filename

        if not backup_path.exists():
            raise FileNotFoundError(f"Backup não encontrado: {backup_filename}")

        # Criar backup do arquivo atual antes de restaurar
        self.create_backup("Antes de restaurar backup")

        # Restaurar
        shutil.copy2(backup_path, self.config_path)

        logger.info(f"Backup restaurado: {backup_filename}")
        self._log_change(f"Restaurado backup: {backup_filename}")

        return True

    def validate_config(self, config: Dict[str, Any]) -> bool:
        """
        Valida configuração usando promtool

        Args:
            config: Configuração a validar

        Returns:
            True se válida

        Raises:
            RuntimeError: Se validação falhar
        """
        # Salvar config temporário para validar
        temp_path = self.config_path.parent / "prometheus_temp.yml"

        try:
            with open(temp_path, 'w', encoding='utf-8') as f:
                self.yaml.dump(config, f)

            # Executar promtool check config
            result = subprocess.run(
                [self.promtool_path, 'check', 'config', str(temp_path)],
                capture_output=True,
                text=True
            )

            if result.returncode != 0:
                logger.error(f"Validação falhou: {result.stderr}")
                raise RuntimeError(f"Configuração inválida: {result.stderr}")

            logger.info("Configuração validada com sucesso")
            return True

        finally:
            # Remover arquivo temporário
            if temp_path.exists():
                temp_path.unlink()

    def reload_prometheus(self) -> bool:
        """
        Recarrega configuração do Prometheus via API

        Returns:
            True se sucesso
        """
        try:
            response = requests.post(
                f"{self.prometheus_url}/-/reload",
                timeout=10
            )

            if response.status_code == 200:
                logger.info("Prometheus recarregado com sucesso")
                return True
            else:
                logger.error(f"Falha ao recarregar: HTTP {response.status_code}")
                return False

        except Exception as e:
            logger.error(f"Erro ao recarregar Prometheus: {e}")
            return False

    def get_preview(self, config: Dict[str, Any]) -> str:
        """
        Gera preview em YAML de uma configuração

        Args:
            config: Configuração a visualizar

        Returns:
            String com YAML formatado
        """
        from io import StringIO

        stream = StringIO()
        self.yaml.dump(config, stream)
        return stream.getvalue()

    def _log_change(self, action: str, backup_path: Path = None):
        """
        Registra mudança no audit log

        Args:
            action: Descrição da ação
            backup_path: Path do backup (opcional)
        """
        log_file = self.config_path.parent / "config_audit.json"

        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'action': action,
            'backup': str(backup_path) if backup_path else None,
            'config_file': str(self.config_path)
        }

        # Adicionar ao arquivo de log
        logs = []
        if log_file.exists():
            with open(log_file, 'r') as f:
                logs = json.load(f)

        logs.append(log_entry)

        # Manter apenas últimos 1000 registros
        logs = logs[-1000:]

        with open(log_file, 'w') as f:
            json.dump(logs, f, indent=2)
