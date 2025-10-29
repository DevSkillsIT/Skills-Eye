"""
Gerenciador de Múltiplos Arquivos de Configuração YAML

Gerencia configurações de:
- Prometheus (/etc/prometheus/*.yml)
- Blackbox Exporter (/etc/blackbox_exporter/*.yml)
- Alertmanager (/etc/alertmanager/*.yml)

Suporta conexão SSH remota usando PROMETHEUS_CONFIG_HOSTS do .env
"""

from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
import os
import logging
import re
from dataclasses import dataclass
import paramiko

from core.yaml_config_service import YamlConfigService
from core.fields_extraction_service import FieldsExtractionService, MetadataField

logger = logging.getLogger(__name__)


@dataclass
class ConfigHost:
    """Representa um host de configuração"""
    hostname: str
    port: int
    username: str
    password: Optional[str] = None
    key_path: Optional[str] = None

    @staticmethod
    def parse_from_string(host_string: str) -> 'ConfigHost':
        """
        Parse host string no formato: host:porta/usuario/senha

        Exemplos:
        - 172.16.1.26:22/root/Skills@2021,TI
        - 172.16.1.26/root/senha
        - 172.16.1.26:22/root  (usa chave SSH)

        Args:
            host_string: String com formato host:porta/user/pass

        Returns:
            ConfigHost parseado
        """
        # Parse: host:porta/usuario/senha
        pattern = r'^([^:]+)(?::(\d+))?/([^/]+)(?:/(.+))?$'
        match = re.match(pattern, host_string.strip())

        if not match:
            raise ValueError(f"Formato inválido de CONFIG_HOST: {host_string}")

        hostname, port, username, password = match.groups()

        return ConfigHost(
            hostname=hostname,
            port=int(port) if port else 22,
            username=username,
            password=password
        )


@dataclass
class ConfigFile:
    """Representa um arquivo de configuração"""
    path: str  # String para manter formato Unix em sistemas Windows
    service: str  # 'prometheus', 'blackbox', 'alertmanager'
    filename: str
    host: ConfigHost
    exists: bool = True


class MultiConfigManager:
    """Gerencia múltiplos arquivos de configuração YAML"""

    # Pastas padrão para cada serviço
    # NOTA: Blackbox e Alertmanager foram removidos pois as configurações
    # ficam dentro da pasta do Prometheus (/etc/prometheus)
    DEFAULT_PATHS = {
        'prometheus': '/etc/prometheus',
        # 'blackbox': '/etc/blackbox_exporter',  # DESABILITADO - não existe
        # 'alertmanager': '/etc/alertmanager'    # DESABILITADO - não existe
    }

    def __init__(self):
        """Inicializa o gerenciador"""
        # Parse CONFIG_HOSTS do .env
        self.hosts = self._parse_config_hosts()

        # Cache de configurações
        self._config_cache: Dict[str, Dict[str, Any]] = {}
        self._fields_cache: Optional[List[MetadataField]] = None

        logger.info(f"MultiConfigManager inicializado com {len(self.hosts)} host(s)")
        for host in self.hosts:
            logger.info(f"  - {host.username}@{host.hostname}:{host.port}")

    def _parse_config_hosts(self) -> List[ConfigHost]:
        """
        Parse PROMETHEUS_CONFIG_HOSTS do .env

        Returns:
            Lista de ConfigHost
        """
        hosts_str = os.getenv('PROMETHEUS_CONFIG_HOSTS', '')
        hosts_file = os.getenv('PROMETHEUS_CONFIG_HOSTS_FILE', '')

        hosts = []

        # Parse PROMETHEUS_CONFIG_HOSTS (separado por ponto-e-vírgula)
        if hosts_str:
            for host_str in hosts_str.split(';'):
                host_str = host_str.strip()
                if host_str:
                    try:
                        host = ConfigHost.parse_from_string(host_str)
                        hosts.append(host)
                    except ValueError as e:
                        logger.error(f"Erro ao parsear host: {e}")

        # Parse PROMETHEUS_CONFIG_HOSTS_FILE (um por linha)
        if hosts_file and os.path.exists(hosts_file):
            with open(hosts_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        try:
                            host = ConfigHost.parse_from_string(line)
                            hosts.append(host)
                        except ValueError as e:
                            logger.error(f"Erro ao parsear host: {e}")

        # Fallback: usar configuração do .env antigo
        if not hosts:
            ssh_host = os.getenv('PROMETHEUS_CONFIG_SSH_HOST')
            if ssh_host:
                hosts.append(ConfigHost(
                    hostname=ssh_host,
                    port=int(os.getenv('PROMETHEUS_CONFIG_SSH_PORT', '22')),
                    username=os.getenv('PROMETHEUS_CONFIG_SSH_USER', 'root'),
                    password=os.getenv('PROMETHEUS_CONFIG_SSH_PASSWORD'),
                    key_path=os.getenv('PROMETHEUS_CONFIG_SSH_KEY')
                ))

        return hosts

    def _get_ssh_client(self, host: ConfigHost) -> paramiko.SSHClient:
        """
        Cria cliente SSH para um host

        Args:
            host: Configuração do host

        Returns:
            Cliente SSH conectado
        """
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        # Conectar
        if host.password:
            client.connect(
                hostname=host.hostname,
                port=host.port,
                username=host.username,
                password=host.password,
                timeout=10
            )
        elif host.key_path and os.path.exists(host.key_path):
            client.connect(
                hostname=host.hostname,
                port=host.port,
                username=host.username,
                key_filename=host.key_path,
                timeout=10
            )
        else:
            # Tentar com chaves padrão do ~/.ssh/
            client.connect(
                hostname=host.hostname,
                port=host.port,
                username=host.username,
                look_for_keys=True,
                timeout=10
            )

        return client

    def list_config_files(self, service: Optional[str] = None, hostname: Optional[str] = None) -> List[ConfigFile]:
        """
        Lista todos os arquivos .yml disponíveis

        Args:
            service: Filtrar por serviço ('prometheus', 'blackbox', 'alertmanager')
            hostname: Filtrar por hostname específico (OTIMIZAÇÃO - evita SSH em todos os servidores)

        Returns:
            Lista de ConfigFile
        """
        all_files = []

        services_to_check = [service] if service else self.DEFAULT_PATHS.keys()

        # OTIMIZAÇÃO: Se hostname especificado, conectar apenas naquele servidor
        hosts_to_check = self.hosts
        if hostname:
            hosts_to_check = [h for h in self.hosts if h.hostname == hostname]
            if not hosts_to_check:
                print(f"[OTIMIZAÇÃO] Hostname {hostname} não encontrado nos servidores configurados")
                return []
            print(f"[OTIMIZAÇÃO] Listando arquivos apenas de {hostname} (evitando SSH em outros {len(self.hosts)-1} servidores)")

        for host in hosts_to_check:
            for svc in services_to_check:
                path = self.DEFAULT_PATHS.get(svc)
                if not path:
                    continue

                # Listar arquivos .yml via SSH
                try:
                    client = self._get_ssh_client(host)
                    sftp = client.open_sftp()

                    # Listar arquivos no diretório
                    try:
                        files = sftp.listdir(path)

                        for filename in files:
                            if filename.endswith('.yml') or filename.endswith('.yaml'):
                                # Manter path como string Unix para SSH
                                file_path = f"{path}/{filename}" if not path.endswith('/') else f"{path}{filename}"
                                config_file = ConfigFile(
                                    path=file_path,
                                    service=svc,
                                    filename=filename,
                                    host=host,
                                    exists=True
                                )
                                all_files.append(config_file)
                    except FileNotFoundError:
                        logger.warning(f"Diretório não encontrado: {path} em {host.hostname}")

                    sftp.close()
                    # OTIMIZAÇÃO: NÃO fechar conexão SSH - reutilizar nas próximas requisições
                    # client.close()

                except Exception as e:
                    logger.error(f"Erro ao listar arquivos de {host.hostname}: {e}")

        logger.info(f"Encontrados {len(all_files)} arquivos de configuração")
        return all_files

    def read_config_file(self, config_file: ConfigFile) -> Dict[str, Any]:
        """
        Lê um arquivo de configuração

        Args:
            config_file: Arquivo a ler

        Returns:
            Configuração parseada
        """
        cache_key = f"{config_file.host.hostname}:{config_file.path}"

        # Verificar cache
        if cache_key in self._config_cache:
            return self._config_cache[cache_key]

        # Ler arquivo via SSH
        try:
            client = self._get_ssh_client(config_file.host)
            sftp = client.open_sftp()

            # Usar path como string diretamente (já está em formato Unix)
            with sftp.open(config_file.path, 'r') as f:
                content = f.read().decode('utf-8')

            sftp.close()
            # OTIMIZAÇÃO: NÃO fechar conexão SSH - reutilizar nas próximas requisições
            # client.close()

            # Parse YAML
            yaml_service = YamlConfigService()
            from io import StringIO
            config = yaml_service.yaml.load(StringIO(content))

            # Armazenar no cache
            self._config_cache[cache_key] = config

            return config

        except Exception as e:
            logger.error(f"Erro ao ler arquivo {config_file.path}: {e}")
            raise

    def extract_all_fields(self) -> List[MetadataField]:
        """
        Extrai TODOS os campos metadata de TODOS os arquivos

        Returns:
            Lista consolidada de MetadataField
        """
        # Verificar cache
        if self._fields_cache:
            return self._fields_cache

        all_fields_map: Dict[str, MetadataField] = {}
        fields_service = FieldsExtractionService()

        # Listar todos os arquivos de configuração
        config_files = self.list_config_files()

        for config_file in config_files:
            try:
                # Ler configuração
                config = self.read_config_file(config_file)

                # Extrair jobs (prometheus) ou scrape_configs (outros)
                jobs = []

                if 'scrape_configs' in config:
                    # Prometheus
                    jobs = config.get('scrape_configs', [])
                elif 'modules' in config:
                    # Blackbox - não tem jobs mas tem módulos
                    # Pular por enquanto
                    continue
                elif 'route' in config:
                    # Alertmanager - não tem relabel_configs
                    continue

                # Extrair campos de cada job
                for job in jobs:
                    job_fields = fields_service.extract_fields_from_jobs([job])

                    # Mesclar com campos existentes
                    for field in job_fields:
                        if field.name not in all_fields_map:
                            all_fields_map[field.name] = field

            except Exception as e:
                logger.error(f"Erro ao processar {config_file.filename}: {e}")

        # Converter para lista ordenada
        all_fields = list(all_fields_map.values())
        all_fields.sort(key=lambda f: (not f.required, f.name))

        # Armazenar no cache
        self._fields_cache = all_fields

        logger.info(f"Extraídos {len(all_fields)} campos únicos de {len(config_files)} arquivos")
        return all_fields

    def clear_cache(self):
        """Limpa cache de configurações e campos"""
        self._config_cache.clear()
        self._fields_cache = None
        logger.info("Cache limpo")

    def get_config_summary(self) -> Dict[str, Any]:
        """
        Retorna resumo de todas as configurações

        Returns:
            Dict com estatísticas
        """
        files = self.list_config_files()
        fields = self.extract_all_fields()

        summary = {
            'total_files': len(files),
            'files_by_service': {},
            'total_fields': len(fields),
            'required_fields': len([f for f in fields if f.required]),
            'hosts': len(self.hosts),
            'files': []
        }

        # Agrupar por serviço
        for file in files:
            if file.service not in summary['files_by_service']:
                summary['files_by_service'][file.service] = 0
            summary['files_by_service'][file.service] += 1

            summary['files'].append({
                'service': file.service,
                'filename': file.filename,
                'path': str(file.path),
                'host': f"{file.host.username}@{file.host.hostname}:{file.host.port}"
            })

        return summary

    def get_file_by_path(self, file_path: str) -> Optional[ConfigFile]:
        """
        Encontra um ConfigFile pelo path

        Args:
            file_path: Path do arquivo

        Returns:
            ConfigFile ou None
        """
        files = self.list_config_files()
        for f in files:
            if f.path == file_path:
                return f
        return None

    def get_file_content_raw(self, file_path: str) -> str:
        """
        Retorna conteúdo bruto (string) de um arquivo

        Args:
            file_path: Path do arquivo

        Returns:
            Conteúdo do arquivo como string
        """
        config_file = self.get_file_by_path(file_path)
        if not config_file:
            raise FileNotFoundError(f"Arquivo não encontrado: {file_path}")

        try:
            client = self._get_ssh_client(config_file.host)
            sftp = client.open_sftp()

            with sftp.open(config_file.path, 'r') as f:
                content = f.read().decode('utf-8')

            sftp.close()
            # OTIMIZAÇÃO: NÃO fechar conexão SSH - reutilizar nas próximas requisições
            # client.close()

            return content

        except Exception as e:
            logger.error(f"Erro ao ler arquivo {file_path}: {e}")
            raise

    def get_config_structure(self, file_path: str) -> Dict[str, Any]:
        """
        Retorna a estrutura completa de um arquivo de configuração,
        detectando automaticamente o tipo

        Args:
            file_path: Path do arquivo

        Returns:
            Dict com: type, main_key, items, raw_config
        """
        config_file = self.get_file_by_path(file_path)
        if not config_file:
            raise FileNotFoundError(f"Arquivo não encontrado: {file_path}")

        config = self.read_config_file(config_file)

        # Detectar tipo de estrutura
        structure = {
            'file_path': file_path,
            'filename': config_file.filename,
            'raw_config': config,
            'editable_sections': []
        }

        # TIPO 1: Prometheus (scrape_configs)
        if 'scrape_configs' in config:
            structure['type'] = 'prometheus'
            structure['main_key'] = 'scrape_configs'
            structure['items'] = config.get('scrape_configs', [])
            structure['item_key'] = 'job_name'
            structure['editable_sections'].append({
                'key': 'scrape_configs',
                'label': 'Jobs / Scrape Configs',
                'count': len(config.get('scrape_configs', []))
            })
            # Adicionar outras seções editáveis
            if 'global' in config:
                structure['editable_sections'].append({
                    'key': 'global',
                    'label': 'Configurações Globais',
                    'count': 1
                })
            if 'alerting' in config:
                structure['editable_sections'].append({
                    'key': 'alerting',
                    'label': 'Alerting',
                    'count': 1
                })

        # TIPO 2: Blackbox (modules)
        elif 'modules' in config:
            structure['type'] = 'blackbox'
            structure['main_key'] = 'modules'
            structure['items'] = [
                {'module_name': k, **v}
                for k, v in config.get('modules', {}).items()
            ]
            structure['item_key'] = 'module_name'
            structure['editable_sections'].append({
                'key': 'modules',
                'label': 'Módulos',
                'count': len(config.get('modules', {}))
            })

        # TIPO 3: Alertmanager (route, receivers)
        elif 'route' in config or 'receivers' in config:
            structure['type'] = 'alertmanager'
            structure['main_key'] = 'route'
            structure['items'] = []
            if 'receivers' in config:
                structure['items'] = config.get('receivers', [])
                structure['item_key'] = 'name'
                structure['editable_sections'].append({
                    'key': 'receivers',
                    'label': 'Receivers',
                    'count': len(config.get('receivers', []))
                })
            if 'route' in config:
                structure['editable_sections'].append({
                    'key': 'route',
                    'label': 'Route Configuration',
                    'count': 1
                })
            if 'global' in config:
                structure['editable_sections'].append({
                    'key': 'global',
                    'label': 'Global',
                    'count': 1
                })

        # TIPO 4: Rules (groups)
        elif 'groups' in config:
            structure['type'] = 'rules'
            structure['main_key'] = 'groups'
            structure['items'] = config.get('groups', [])
            structure['item_key'] = 'name'
            structure['editable_sections'].append({
                'key': 'groups',
                'label': 'Grupos de Regras',
                'count': len(config.get('groups', []))
            })

        # TIPO 5: Outros (web-config, etc)
        else:
            structure['type'] = 'other'
            structure['main_key'] = None
            structure['items'] = []
            # Listar todas as chaves top-level
            for key in config.keys():
                structure['editable_sections'].append({
                    'key': key,
                    'label': key.replace('_', ' ').title(),
                    'count': 1 if not isinstance(config[key], list) else len(config[key])
                })

        return structure

    def get_jobs_from_file(self, file_path: str) -> List[Dict[str, Any]]:
        """
        DEPRECATED: Use get_config_structure() para suporte a múltiplos tipos

        Extrai lista de jobs de um arquivo de configuração

        Args:
            file_path: Path do arquivo

        Returns:
            Lista de jobs/scrape_configs
        """
        structure = self.get_config_structure(file_path)
        return structure.get('items', [])

    def save_file_content(self, file_path: str, content: str) -> bool:
        """
        Salva conteúdo em um arquivo remoto

        Args:
            file_path: Path do arquivo
            content: Conteúdo a salvar

        Returns:
            True se sucesso
        """
        config_file = self.get_file_by_path(file_path)
        if not config_file:
            raise FileNotFoundError(f"Arquivo não encontrado: {file_path}")

        try:
            client = self._get_ssh_client(config_file.host)
            sftp = client.open_sftp()

            # Fazer backup antes de salvar
            backup_path = f"{file_path}.backup"
            backup_exists = False
            try:
                sftp.rename(file_path, backup_path)
                backup_exists = True
                print(f"[SAVE] Backup criado: {backup_path}")
            except:
                pass  # Backup pode não existir

            # Salvar novo conteúdo
            with sftp.open(config_file.path, 'w') as f:
                f.write(content.encode('utf-8'))

            print(f"[SAVE] Arquivo salvo: {file_path}")

            # IMPORTANTE: Restaurar proprietário prometheus:prometheus
            try:
                stdin, stdout, stderr = client.exec_command(f'chown prometheus:prometheus {file_path}')
                exit_status = stdout.channel.recv_exit_status()
                if exit_status == 0:
                    print(f"[SAVE] Proprietário restaurado: prometheus:prometheus")
                else:
                    error_msg = stderr.read().decode('utf-8')
                    print(f"[SAVE] AVISO: Falha ao restaurar proprietário: {error_msg}")
            except Exception as e:
                print(f"[SAVE] AVISO: Não foi possível restaurar proprietário: {e}")

            # Remover backup se salvamento foi bem-sucedido
            if backup_exists:
                try:
                    sftp.remove(backup_path)
                    print(f"[SAVE] Backup removido: {backup_path}")
                except Exception as e:
                    print(f"[SAVE] AVISO: Não foi possível remover backup: {e}")

            sftp.close()
            # OTIMIZAÇÃO: NÃO fechar conexão SSH - reutilizar nas próximas requisições
            # client.close()

            # Limpar cache
            self.clear_cache()

            logger.info(f"Arquivo salvo com sucesso: {file_path}")
            return True

        except Exception as e:
            logger.error(f"Erro ao salvar arquivo {file_path}: {e}")
            raise

    def update_jobs_in_file(self, file_path: str, jobs: List[Dict[str, Any]]) -> bool:
        """
        Atualiza a lista de jobs em um arquivo

        Args:
            file_path: Path do arquivo
            jobs: Nova lista de jobs

        Returns:
            True se sucesso
        """
        config_file = self.get_file_by_path(file_path)
        if not config_file:
            raise FileNotFoundError(f"Arquivo não encontrado: {file_path}")

        # Ler configuração atual (mantém metadados ruamel.yaml)
        config = self.read_config_file(config_file)

        if 'scrape_configs' not in config:
            raise ValueError(f"Arquivo {file_path} não contém 'scrape_configs'")

        # CRÍTICO: NÃO substituir o CommentedSeq!
        # Isso destruiria todos os comentários do ruamel.yaml
        # Em vez disso, limpar e reconstruir mantendo o objeto original
        original_scrape_configs = config['scrape_configs']

        # Limpar lista mantendo o objeto CommentedSeq
        original_scrape_configs.clear()

        # Adicionar cada job mantendo estrutura ruamel.yaml
        from ruamel.yaml.comments import CommentedMap
        yaml_service = YamlConfigService()

        for job in jobs:
            # Converter job dict para CommentedMap (preserva estrutura YAML)
            job_yaml = yaml_service.yaml.load(yaml_service.yaml.dump(job))
            original_scrape_configs.append(job_yaml)

        # Converter para YAML (preserva TODOS os comentários)
        from io import StringIO
        output = StringIO()
        yaml_service.yaml.dump(config, output)
        content = output.getvalue()

        # Salvar
        return self.save_file_content(file_path, content)

    def validate_prometheus_config(self, file_path: str, yaml_content: str) -> Dict[str, Any]:
        """
        Valida configuração do Prometheus usando promtool

        Args:
            file_path: Path do arquivo (para identificar o host)
            yaml_content: Conteúdo YAML a ser validado

        Returns:
            Dict com: success (bool), errors (list), output (str)
        """
        config_file = self.get_file_by_path(file_path)
        if not config_file:
            raise FileNotFoundError(f"Arquivo não encontrado: {file_path}")

        # Verificar se é um arquivo prometheus
        if config_file.service != 'prometheus':
            return {
                'success': True,
                'message': 'Validação skipped - não é arquivo Prometheus',
                'errors': []
            }

        try:
            client = self._get_ssh_client(config_file.host)
            sftp = client.open_sftp()

            # Criar arquivo temporário para validação
            import tempfile
            import time
            temp_filename = f"/tmp/prometheus_validate_{int(time.time())}.yml"

            # Escrever conteúdo no arquivo temporário
            with sftp.open(temp_filename, 'w') as f:
                f.write(yaml_content.encode('utf-8'))

            # Executar promtool check config
            stdin, stdout, stderr = client.exec_command(
                f"promtool check config {temp_filename}"
            )

            # Ler resultado
            exit_status = stdout.channel.recv_exit_status()
            output_text = stdout.read().decode('utf-8')
            error_text = stderr.read().decode('utf-8')

            # Remover arquivo temporário
            try:
                sftp.remove(temp_filename)
            except:
                pass  # Ignorar erros ao remover temp file

            sftp.close()
            # OTIMIZAÇÃO: NÃO fechar conexão SSH - reutilizar nas próximas requisições
            # client.close()

            # Analisar resultado
            if exit_status == 0:
                return {
                    'success': True,
                    'message': 'Configuração válida',
                    'output': output_text,
                    'errors': []
                }
            else:
                # Extrair erros do output
                errors = []
                for line in (output_text + error_text).split('\n'):
                    if line.strip() and ('error' in line.lower() or 'failed' in line.lower()):
                        errors.append(line.strip())

                return {
                    'success': False,
                    'message': 'Configuração inválida',
                    'output': output_text + error_text,
                    'errors': errors if errors else ['Validação falhou - verifique output']
                }

        except Exception as e:
            logger.error(f"Erro ao validar configuração prometheus: {e}")
            return {
                'success': False,
                'message': f'Erro ao executar promtool: {str(e)}',
                'errors': [str(e)]
            }
