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
        self._files_cache: Dict[str, List[ConfigFile]] = {}  # OTIMIZAÇÃO: Cache para list_config_files

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
        # OTIMIZAÇÃO: Cache key baseado em service+hostname
        cache_key = f"{service or 'all'}:{hostname or 'all'}"

        # Verificar cache
        if cache_key in self._files_cache:
            return self._files_cache[cache_key]

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

        # OTIMIZAÇÃO: Armazenar no cache
        self._files_cache[cache_key] = all_files

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
            print(f"[CACHE] extract_all_fields: CACHE HIT - retornando {len(self._fields_cache)} fields do cache")
            return self._fields_cache

        # Delegar para extract_all_fields_with_status e retornar apenas fields
        result = self.extract_all_fields_with_status()
        return result['fields']

    def extract_all_fields_with_status(self) -> Dict[str, Any]:
        """
        Extrai TODOS os campos metadata de TODOS os arquivos
        Retorna fields + status de cada servidor para tracking de progresso

        Returns:
            Dict com:
            - fields: Lista consolidada de MetadataField
            - server_status: Lista com status de cada servidor
            - total_servers: Total de servidores
            - successful_servers: Quantidade de servidores com sucesso
        """
        # Verificar cache
        if self._fields_cache:
            print(f"[CACHE] extract_all_fields: CACHE HIT - retornando {len(self._fields_cache)} fields do cache")
            # Retornar com status de cache
            return {
                'fields': self._fields_cache,
                'server_status': [
                    {
                        'hostname': host.hostname,
                        'success': True,
                        'from_cache': True,
                        'files_count': 0,
                        'fields_count': 0,
                    }
                    for host in self.hosts
                ],
                'total_servers': len(self.hosts),
                'successful_servers': len(self.hosts),
                'from_cache': True,
            }

        print(f"[CACHE] extract_all_fields: CACHE MISS - extraindo fields de todos os arquivos")

        all_fields_map: Dict[str, MetadataField] = {}
        fields_service = FieldsExtractionService()
        server_status = []

        # OTIMIZAÇÃO: Listar arquivos por servidor para aproveitar cache _files_cache
        # Isso evita SSH desnecessário se os arquivos já foram listados antes
        # FAILBACK: Continua mesmo se um servidor falhar
        for host in self.hosts:
            host_status = {
                'hostname': host.hostname,
                'success': False,
                'from_cache': False,
                'files_count': 0,
                'fields_count': 0,
                'error': None,
                'duration_ms': 0,
            }

            try:
                import time
                start_time = time.time()

                # Cada chamada usa cache com chave "all:{hostname}"
                files_from_host = self.list_config_files(hostname=host.hostname)
                host_status['files_count'] = len(files_from_host)

                fields_before = len(all_fields_map)

                # Processar cada arquivo do servidor
                for config_file in files_from_host:
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
                        # Continua processando outros arquivos

                fields_after = len(all_fields_map)
                host_status['fields_count'] = fields_after - fields_before
                host_status['success'] = True
                host_status['duration_ms'] = int((time.time() - start_time) * 1000)

                print(f"[SERVER OK] {host.hostname}: {host_status['files_count']} arquivos, {host_status['fields_count']} campos novos em {host_status['duration_ms']}ms")

            except Exception as e:
                host_status['error'] = str(e)
                logger.error(f"❌ Erro ao processar servidor {host.hostname}: {e}")
                print(f"[SERVER ERROR] {host.hostname}: {str(e)}")
                # Continua com próximo servidor (FAILBACK)

            server_status.append(host_status)

        # Converter para lista ordenada
        all_fields = list(all_fields_map.values())
        all_fields.sort(key=lambda f: (not f.required, f.name))

        # Armazenar no cache
        self._fields_cache = all_fields

        successful_count = sum(1 for s in server_status if s['success'])
        logger.info(f"Extraídos {len(all_fields)} campos únicos - {successful_count}/{len(self.hosts)} servidores com sucesso")

        return {
            'fields': all_fields,
            'server_status': server_status,
            'total_servers': len(self.hosts),
            'successful_servers': successful_count,
            'from_cache': False,
        }

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

    def get_file_by_path(self, file_path: str, hostname: Optional[str] = None) -> Optional[ConfigFile]:
        """
        Encontra um ConfigFile pelo path e opcionalmente pelo hostname

        Args:
            file_path: Path do arquivo
            hostname: Hostname do servidor (opcional, OTIMIZAÇÃO para evitar SSH em múltiplos servidores)

        Returns:
            ConfigFile ou None
        """
        # OTIMIZAÇÃO: Passar hostname para list_config_files para usar cache + SSH apenas no servidor correto
        files = self.list_config_files(hostname=hostname)
        for f in files:
            if f.path == file_path:
                # Se hostname foi especificado, verificar se bate
                if hostname and f.host.hostname != hostname:
                    continue
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

    def get_config_structure(self, file_path: str, hostname: Optional[str] = None) -> Dict[str, Any]:
        """
        Retorna a estrutura completa de um arquivo de configuração,
        detectando automaticamente o tipo

        Args:
            file_path: Path do arquivo
            hostname: Hostname do servidor (opcional, OTIMIZAÇÃO para evitar SSH em múltiplos servidores)

        Returns:
            Dict com: type, main_key, items, raw_config
        """
        config_file = self.get_file_by_path(file_path, hostname=hostname)

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

    def _copy_comments_deep(self, target: Any, source: Any):
        """
        Copia TODOS os comentários de source para target recursivamente.

        Args:
            target: Objeto ruamel.yaml destino (sem comentários)
            source: Objeto ruamel.yaml origem (com comentários)
        """
        from ruamel.yaml.comments import CommentedMap, CommentedSeq

        # Copiar comentários do CommentedMap
        if isinstance(target, CommentedMap) and isinstance(source, CommentedMap):
            if hasattr(source, 'ca') and source.ca:
                if hasattr(target, 'ca') and target.ca:
                    # Copiar comment attributes
                    try:
                        # Copiar comentários antes/após
                        if source.ca.comment:
                            target.ca.comment = source.ca.comment
                        # Copiar comentários EOL (end-of-line)
                        if hasattr(source.ca, 'items') and source.ca.items:
                            if not hasattr(target.ca, 'items') or not target.ca.items:
                                target.ca.items = {}
                            target.ca.items.update(source.ca.items)
                        # Copiar comentários finais
                        if hasattr(source.ca, 'end') and source.ca.end:
                            target.ca.end = source.ca.end
                    except Exception as e:
                        logger.debug(f"[COPY COMMENTS] Erro ao copiar comentários: {e}")

            # Recursão para cada chave
            for key in target:
                if key in source:
                    self._copy_comments_deep(target[key], source[key])

        # Copiar comentários do CommentedSeq
        elif isinstance(target, CommentedSeq) and isinstance(source, CommentedSeq):
            if hasattr(source, 'ca') and source.ca and hasattr(target, 'ca'):
                try:
                    # Copiar comment attributes da sequência
                    if source.ca.comment:
                        target.ca.comment = source.ca.comment
                    if hasattr(source.ca, 'items') and source.ca.items:
                        if not hasattr(target.ca, 'items') or not target.ca.items:
                            target.ca.items = {}
                        target.ca.items.update(source.ca.items)
                except Exception as e:
                    logger.debug(f"[COPY COMMENTS] Erro ao copiar comentários de seq: {e}")

            # Recursão para cada item da lista
            for i in range(min(len(target), len(source))):
                self._copy_comments_deep(target[i], source[i])

    def _update_dict_surgically(self, target: Any, source: Dict[str, Any], path: str = "") -> int:
        """
        Atualiza um dicionário (CommentedMap) de forma cirúrgica.
        Modifica apenas valores que mudaram, preservando estrutura e comentários.

        Args:
            target: Objeto ruamel.yaml (CommentedMap/CommentedSeq) a atualizar
            source: Dicionário Python com novos valores
            path: Path do campo (para debug)

        Returns:
            Número de campos alterados
        """
        from ruamel.yaml.comments import CommentedMap, CommentedSeq
        import copy

        changes_count = 0

        # Se target não é CommentedMap, não podemos fazer edição cirúrgica
        if not isinstance(target, (CommentedMap, dict)):
            return 0

        # Iterar sobre cada chave no source
        for key, new_value in source.items():
            current_path = f"{path}.{key}" if path else key

            # Caso 1: Chave não existe no target - adicionar
            if key not in target:
                logger.debug(f"[CIRÚRGICO] Adicionando novo campo: {current_path}")
                target[key] = new_value
                changes_count += 1
                continue

            old_value = target[key]

            # Caso 2: Ambos são dicts - recursão
            if isinstance(new_value, dict) and isinstance(old_value, (CommentedMap, dict)):
                sub_changes = self._update_dict_surgically(old_value, new_value, current_path)
                changes_count += sub_changes
                continue

            # Caso 3: Ambos são listas - MANTER OBJETO ORIGINAL E ATUALIZAR VALORES
            if isinstance(new_value, list) and isinstance(old_value, CommentedSeq):
                # Guardar comentários originais ANTES de modificar
                old_ca = None
                old_fa = None
                if hasattr(old_value, 'ca'):
                    old_ca = copy.deepcopy(old_value.ca)
                if hasattr(old_value, 'fa'):
                    old_fa = old_value.fa

                # Atualizar valores
                old_value.clear()
                old_value.extend(new_value)

                # Restaurar comentários
                if old_ca and hasattr(old_value, 'ca'):
                    old_value.ca = old_ca

                logger.debug(f"[CIRÚRGICO] Lista atualizada: {current_path} ({len(new_value)} itens)")
                changes_count += 1
                continue

            # Caso 4: Valores primitivos - comparar e atualizar se diferente
            if old_value != new_value:
                logger.info(f"[CIRÚRGICO] ✏️  Modificando: {current_path}")
                logger.info(f"              Antes: {old_value}")
                logger.info(f"              Depois: {new_value}")
                target[key] = new_value
                changes_count += 1

        # IMPORTANTE: NÃO remover chaves que não estão no source!
        # Isso seria uma edição destrutiva, não cirúrgica.
        # Apenas adicionamos/modificamos campos que foram explicitamente alterados.

        return changes_count

    def _update_yaml_text_based(self, content: str, old_jobs: List[Dict], new_jobs: List[Dict]) -> str:
        """
        Atualiza YAML usando edição baseada em TEXTO (preserva 100% dos comentários).

        Esta função compara old_jobs com new_jobs e aplica substituições cirúrgicas
        no texto YAML, preservando TUDO (comentários, formatação, aspas, etc.)

        Args:
            content: Conteúdo YAML como string
            old_jobs: Jobs originais (parsed do arquivo)
            new_jobs: Jobs novos (recebidos do frontend)

        Returns:
            Conteúdo YAML modificado
        """
        import re
        import json

        logger.info(f"[TEXT-BASED] Iniciando edição baseada em texto")
        logger.info(f"[TEXT-BASED] old_jobs count: {len(old_jobs)}")
        logger.info(f"[TEXT-BASED] new_jobs count: {len(new_jobs)}")

        # Criar mapa para comparação rápida
        old_map = {j.get('job_name'): j for j in old_jobs}
        new_map = {j.get('job_name'): j for j in new_jobs}

        logger.info(f"[TEXT-BASED] old_map keys: {list(old_map.keys())[:5]}")  # Primeiros 5
        logger.info(f"[TEXT-BASED] new_map keys: {list(new_map.keys())[:5]}")

        changes_made = 0

        for job_name in old_map:
            if job_name not in new_map:
                logger.warning(f"[TEXT-BASED] Job '{job_name}' foi removido")
                continue

            old_job = old_map[job_name]
            new_job = new_map[job_name]

            logger.info(f"[TEXT-BASED] Comparando job: {job_name}")

            # Detectar mudanças específicas
            changes = self._detect_yaml_changes(old_job, new_job, path=job_name)

            logger.info(f"[TEXT-BASED] Mudanças detectadas em '{job_name}': {len(changes)}")

            if len(changes) > 0:
                logger.info(f"[TEXT-BASED] Mudanças: {changes}")

            for change in changes:
                # Aplicar substituição cirúrgica
                old_content_len = len(content)
                content = self._apply_text_replacement(content, change, job_name)
                new_content_len = len(content)

                if old_content_len != new_content_len:
                    changes_made += 1
                    logger.info(f"[TEXT-BASED] ✓ Aplicada mudança: {change['path']} = {change['new_value']}")
                else:
                    logger.warning(f"[TEXT-BASED] ⚠️ Mudança NÃO aplicada (content igual): {change['path']}")

        logger.info(f"[TEXT-BASED] Total de mudanças aplicadas: {changes_made}")
        return content

    def _detect_yaml_changes(self, old_dict: Dict, new_dict: Dict, path: str = "") -> List[Dict]:
        """
        Detecta mudanças entre dois dicts recursivamente.

        Returns:
            Lista de dicts com {path, old_value, new_value, field_name}
        """
        changes = []

        for key in new_dict:
            if key not in old_dict:
                continue  # Campo novo - ignorar em text-based

            old_val = old_dict[key]
            new_val = new_dict[key]
            current_path = f"{path}.{key}" if path else key

            # Se ambos são dicts, recursão
            if isinstance(old_val, dict) and isinstance(new_val, dict):
                sub_changes = self._detect_yaml_changes(old_val, new_val, current_path)
                changes.extend(sub_changes)

            # Se ambos são listas, comparar
            elif isinstance(old_val, list) and isinstance(new_val, list):
                if old_val != new_val:
                    changes.append({
                        'path': current_path,
                        'field_name': key,
                        'old_value': old_val,
                        'new_value': new_val,
                        'type': 'list'
                    })

            # Valores primitivos
            elif old_val != new_val:
                changes.append({
                    'path': current_path,
                    'field_name': key,
                    'old_value': old_val,
                    'new_value': new_val,
                    'type': 'primitive'
                })

        return changes

    def _apply_text_replacement(self, content: str, change: Dict, job_name: str) -> str:
        """
        Aplica uma substituição cirúrgica no texto YAML.

        Args:
            content: Conteúdo YAML
            change: Dict com path, old_value, new_value
            job_name: Nome do job sendo modificado

        Returns:
            Conteúdo modificado
        """
        import re

        field_name = change['field_name']
        old_value = change['old_value']
        new_value = change['new_value']

        logger.info(f"[TEXT-REPLACE] Campo: {field_name}, De: {old_value}, Para: {new_value}")

        # Converter valores para formato YAML
        old_yaml = self._value_to_yaml_text(old_value)
        new_yaml = self._value_to_yaml_text(new_value)

        # Encontrar a seção do job específico
        job_pattern = rf"(- job_name:\s*['\"]?{re.escape(job_name)}['\"]?.*?)(\n- job_name:|\nrule_files:|\Z)"
        job_match = re.search(job_pattern, content, re.DOTALL)

        if not job_match:
            logger.error(f"[TEXT-REPLACE] Não encontrou job '{job_name}' no arquivo!")
            return content

        job_section = job_match.group(1)
        job_start = job_match.start(1)
        job_end = job_match.end(1)

        # Substituir o campo dentro da seção do job
        field_pattern = rf"(\s+{re.escape(field_name)}:\s*){re.escape(old_yaml)}"
        replacement = rf"\1{new_yaml}"

        modified_section = re.sub(field_pattern, replacement, job_section, count=1)

        if modified_section == job_section:
            logger.warning(f"[TEXT-REPLACE] Não encontrou padrão para substituir! Campo: {field_name}")
            logger.warning(f"[TEXT-REPLACE] Procurando por: {field_pattern}")
            return content

        # Reconstruir conteúdo
        new_content = content[:job_start] + modified_section + content[job_end:]
        return new_content

    def _value_to_yaml_text(self, value: Any) -> str:
        """
        Converte um valor Python para representação YAML como texto.

        Args:
            value: Valor a converter

        Returns:
            String representando o valor em YAML
        """
        if isinstance(value, list):
            # Formato flow-style: ['a', 'b']
            items = [f"'{item}'" if isinstance(item, str) else str(item) for item in value]
            return f"[{', '.join(items)}]"
        elif isinstance(value, str):
            # Preservar aspas simples se tiver caracteres especiais
            if any(c in value for c in [' ', ':', '#', '@', '/', '\\']):
                return f"'{value}'"
            return value
        elif isinstance(value, (int, float, bool)):
            return str(value).lower() if isinstance(value, bool) else str(value)
        else:
            return str(value)

    def _detect_simple_changes(self, old_jobs: List[Dict], new_jobs: List[Dict]) -> List[Dict]:
        """
        Detecta mudanças SIMPLES entre old_jobs e new_jobs.

        Returns:
            Lista de mudanças: [{pattern, replacement, description}]
        """
        changes = []

        old_map = {j.get('job_name'): j for j in old_jobs}
        new_map = {j.get('job_name'): j for j in new_jobs}

        for job_name in old_map:
            if job_name not in new_map:
                continue

            old_job = old_map[job_name]
            new_job = new_map[job_name]

            # Comparar cada campo de forma recursiva
            field_changes = self._compare_dicts_for_sed(old_job, new_job, job_name)
            changes.extend(field_changes)

        return changes

    def _compare_dicts_for_sed(self, old_dict: Dict, new_dict: Dict, context: str) -> List[Dict]:
        """
        Compara dois dicts e retorna mudanças em formato SED.

        Returns:
            Lista de {pattern, replacement, description}
        """
        changes = []

        for key in new_dict:
            if key not in old_dict:
                continue

            old_val = old_dict[key]
            new_val = new_dict[key]

            if old_val == new_val:
                continue

            # Listas
            if isinstance(old_val, list) and isinstance(new_val, list):
                # Se lista de dicts, comparar elemento por elemento
                if old_val and isinstance(old_val[0], dict):
                    # Comparar cada elemento da lista
                    for i in range(min(len(old_val), len(new_val))):
                        sub_changes = self._compare_dicts_for_sed(
                            old_val[i],
                            new_val[i],
                            f'{context}.{key}[{i}]'
                        )
                        changes.extend(sub_changes)
                else:
                    # Lista simples (strings/números)
                    old_yaml = self._list_to_yaml_sed_format(old_val)
                    new_yaml = self._list_to_yaml_sed_format(new_val)

                    changes.append({
                        'pattern': f'{key}: {old_yaml}',
                        'replacement': f'{key}: {new_yaml}',
                        'description': f'{context}.{key}: {old_val} -> {new_val}',
                        'context': context
                    })

            # Strings simples
            elif isinstance(old_val, str) and isinstance(new_val, str):
                # Gerar pattern SED
                old_yaml = f"'{old_val}'" if any(c in old_val for c in [' ', ':', '#']) else old_val
                new_yaml = f"'{new_val}'" if any(c in new_val for c in [' ', ':', '#']) else new_val

                changes.append({
                    'pattern': f'{key}: {old_yaml}',
                    'replacement': f'{key}: {new_yaml}',
                    'description': f'{context}.{key}: {old_val} -> {new_val}',
                    'context': context
                })

            # Números
            elif isinstance(old_val, (int, float)) and isinstance(new_val, (int, float)):
                changes.append({
                    'pattern': f'{key}: {old_val}',
                    'replacement': f'{key}: {new_val}',
                    'description': f'{context}.{key}: {old_val} -> {new_val}',
                    'context': context
                })

            # Dicts aninhados - recursão
            elif isinstance(old_val, dict) and isinstance(new_val, dict):
                sub_changes = self._compare_dicts_for_sed(old_val, new_val, f'{context}.{key}')
                changes.extend(sub_changes)

        return changes

    def _list_to_yaml_sed_format(self, lst: List) -> str:
        """
        Converte lista Python para formato YAML (flow-style) para SED.

        Ex: ['http_2xx'] → "['http_2xx']"
        """
        if not lst:
            return "[]"

        # Flow-style com aspas simples
        items = [f"'{item}'" if isinstance(item, str) else str(item) for item in lst]
        return f"[{', '.join(items)}]"

    def _apply_sed_changes(self, config_file, changes: List[Dict]) -> bool:
        """
        Aplica mudanças usando SED via SSH.

        Args:
            config_file: ConfigFile object
            changes: Lista de mudanças {pattern, replacement, description}

        Returns:
            True se sucesso
        """
        if not changes:
            logger.info(f"[SED] Nenhuma mudança para aplicar")
            return True

        try:
            client = self._get_ssh_client(config_file.host)

            # Criar backup primeiro
            backup_path = f"{config_file.path}.backup-$(date +%Y%m%d-%H%M%S)"
            backup_cmd = f"cp {config_file.path} {backup_path}"

            logger.info(f"[SED] Criando backup: {backup_path}")
            stdin, stdout, stderr = client.exec_command(backup_cmd)
            exit_code = stdout.channel.recv_exit_status()

            if exit_code != 0:
                error = stderr.read().decode('utf-8')
                logger.error(f"[SED] Erro ao criar backup: {error}")
                return False

            # Aplicar cada mudança
            for i, change in enumerate(changes):
                pattern = change['pattern']
                replacement = change['replacement']
                description = change['description']

                logger.info(f"[SED] Mudança {i+1}/{len(changes)}: {description}")

                # Escapar caracteres especiais para SED
                pattern_escaped = pattern.replace('/', r'\/')
                replacement_escaped = replacement.replace('/', r'\/')

                # Comando SED
                sed_cmd = f"sed -i 's/{pattern_escaped}/{replacement_escaped}/g' {config_file.path}"

                logger.info(f"[SED] Executando: {sed_cmd}")

                stdin, stdout, stderr = client.exec_command(sed_cmd)
                exit_code = stdout.channel.recv_exit_status()

                if exit_code != 0:
                    error = stderr.read().decode('utf-8')
                    logger.error(f"[SED] Erro: {error}")
                    # Restaurar backup
                    client.exec_command(f"cp {backup_path} {config_file.path}")
                    return False

                logger.info(f"[SED] ✓ Mudança aplicada")

            logger.info(f"[SED] ✅ Todas as {len(changes)} mudanças aplicadas com sucesso!")
            return True

        except Exception as e:
            logger.error(f"[SED] Erro ao aplicar mudanças: {e}")
            return False

    def update_jobs_in_file(self, file_path: str, jobs: List[Dict[str, Any]]) -> bool:
        """
        Atualiza a lista de jobs em um arquivo de forma CIRÚRGICA.

        ESTRATÉGIA HÍBRIDA:
        1. Tenta edição TEXT-BASED (preserva 100% comentários)
        2. Se falhar, usa ruamel.yaml (pode perder comentários)

        Args:
            file_path: Path do arquivo
            jobs: Nova lista de jobs

        Returns:
            True se sucesso
        """
        config_file = self.get_file_by_path(file_path)
        if not config_file:
            raise FileNotFoundError(f"Arquivo não encontrado: {file_path}")

        # Ler configuração atual (parseada)
        config = self.read_config_file(config_file)

        if 'scrape_configs' not in config:
            raise ValueError(f"Arquivo {file_path} não contém 'scrape_configs'")

        original_scrape_configs = config['scrape_configs']

        logger.info(f"[UPDATE JOBS] Iniciando atualização")
        logger.info(f"[UPDATE JOBS] Jobs no arquivo: {len(original_scrape_configs)}")
        logger.info(f"[UPDATE JOBS] Jobs novos: {len(jobs)}")

        # TENTAR EDIÇÃO VIA SED (SSH) PRIMEIRO
        try:
            logger.info(f"[SED] Tentando edição via SED (SSH)")

            # Detectar mudanças
            changes = self._detect_simple_changes(original_scrape_configs, jobs)

            if len(changes) == 0:
                logger.info(f"[SED] Nenhuma mudança detectada")
                return True

            logger.info(f"[SED] Detectadas {len(changes)} mudança(s)")

            # Gerar e executar comandos SED
            success = self._apply_sed_changes(config_file, changes)

            if success:
                logger.info(f"[UPDATE JOBS] ✅ Sucesso com edição via SED")
                # Limpar cache para forçar reload
                cache_key = f"{config_file.host.hostname}:{config_file.path}"
                if cache_key in self._config_cache:
                    del self._config_cache[cache_key]
                return True
            else:
                logger.warning(f"[SED] Edição via SED falhou, tentando fallback...")

        except Exception as e:
            logger.error(f"[UPDATE JOBS] Edição via SED falhou: {e}")
            logger.info(f"[UPDATE JOBS] Tentando fallback com ruamel.yaml...")

        # FALLBACK: ruamel.yaml (pode perder comentários)
        logger.warning(f"[UPDATE JOBS] ⚠️  Usando ruamel.yaml - comentários podem ser perdidos!")

        total_changes = 0

        # Criar mapa de jobs por job_name para facilitar comparação
        jobs_map = {job.get('job_name'): job for job in jobs}
        original_jobs_map = {
            job.get('job_name'): (idx, job)
            for idx, job in enumerate(original_scrape_configs)
        }

        # Atualizar jobs existentes de forma cirúrgica
        for job_name, new_job in jobs_map.items():
            if job_name in original_jobs_map:
                idx, old_job = original_jobs_map[job_name]
                logger.info(f"[CIRÚRGICO] Atualizando job existente: {job_name}")

                # Edição cirúrgica - modifica apenas campos alterados
                changes = self._update_dict_surgically(old_job, new_job, f"job[{job_name}]")
                total_changes += changes

                if changes == 0:
                    logger.info(f"[CIRÚRGICO] ✓ Job '{job_name}' sem alterações")
                else:
                    logger.info(f"[CIRÚRGICO] ✓ Job '{job_name}' - {changes} campo(s) modificado(s)")

        # Adicionar novos jobs (que não existiam antes)
        from ruamel.yaml.comments import CommentedMap
        yaml_service = YamlConfigService()

        for job_name, new_job in jobs_map.items():
            if job_name not in original_jobs_map:
                logger.info(f"[CIRÚRGICO] Adicionando novo job: {job_name}")
                job_yaml = yaml_service.yaml.load(yaml_service.yaml.dump(new_job))
                original_scrape_configs.append(job_yaml)
                total_changes += 1

        # Remover jobs que não existem mais
        jobs_to_remove = [
            job_name for job_name in original_jobs_map.keys()
            if job_name not in jobs_map
        ]
        for job_name in jobs_to_remove:
            idx, _ = original_jobs_map[job_name]
            logger.info(f"[CIRÚRGICO] Removendo job: {job_name}")
            del original_scrape_configs[idx]
            total_changes += 1

        logger.info(f"[CIRÚRGICO] ✅ Total de alterações: {total_changes}")

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
