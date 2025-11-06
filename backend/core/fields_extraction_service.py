"""
Serviço de Extração de Campos Dinâmicos

Este módulo analisa os relabel_configs do Prometheus e identifica:
- Campos metadata do Consul (__meta_consul_service_metadata_*)
- Target labels que são gerados
- Tipos de dados inferidos
- Valores únicos existentes

Estes campos são usados para gerar formulários dinâmicos no frontend.
"""

from typing import Dict, List, Set, Optional, Any
from dataclasses import dataclass, asdict
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)


@dataclass
class MetadataField:
    """Representa um campo metadata dinâmico"""
    name: str  # Nome do target_label (ex: "company")
    display_name: str  # Nome amigável (ex: "Empresa")
    source_label: str  # Source do Consul (ex: "__meta_consul_service_metadata_company")
    field_type: str  # "string", "number", "select"
    required: bool  # Se é obrigatório
    show_in_table: bool  # Se aparece nas tabelas
    show_in_dashboard: bool  # Se aparece no dashboard
    options: List[str] = None  # Valores únicos (para selects)
    regex: Optional[str] = None  # Regex usado no relabel
    replacement: Optional[str] = None  # Replacement usado

    def to_dict(self) -> Dict[str, Any]:
        """Converte para dicionário"""
        return asdict(self)


class FieldsExtractionService:
    """Serviço para extrair campos dinâmicos dos relabel_configs

    AGORA USA METADATA_LOADER - Sistema totalmente dinâmico!
    """

    def __init__(self, consul_manager=None):
        """
        Inicializa o serviço

        Args:
            consul_manager: Instância do ConsulManager para buscar valores únicos
        """
        self.consul_manager = consul_manager

        # Cache de campos obrigatórios e dashboard
        self._required_fields = None
        self._dashboard_fields = None

    @property
    def REQUIRED_FIELDS(self) -> set:
        """
        Campos obrigatórios extraídos do Prometheus.

        Busca do Consul KV (skills/cm/metadata/fields)
        Campos são extraídos dinamicamente do prometheus.yml via SSH
        """
        if self._required_fields is None:
            try:
                from core.kv_manager import KVManager
                import asyncio

                kv = KVManager()
                fields_data = asyncio.run(kv.get_json('skills/cm/metadata/fields'))

                if fields_data and 'fields' in fields_data:
                    required = [
                        field['name']
                        for field in fields_data['fields']
                        if field.get('required', False)
                    ]
                    self._required_fields = set(required)
                else:
                    self._required_fields = set()
            except Exception:
                self._required_fields = set()

        return self._required_fields

    @property
    def DASHBOARD_FIELDS(self) -> set:
        """
        Campos do dashboard extraídos do Prometheus.

        Busca do Consul KV campos com show_in_dashboard=True
        """
        if self._dashboard_fields is None:
            try:
                from core.kv_manager import KVManager
                import asyncio

                kv = KVManager()
                fields_data = asyncio.run(kv.get_json('skills/cm/metadata/fields'))

                if fields_data and 'fields' in fields_data:
                    dashboard = [
                        field['name']
                        for field in fields_data['fields']
                        if field.get('show_in_dashboard', False)
                    ]
                    self._dashboard_fields = set(dashboard)
                else:
                    self._dashboard_fields = set()
            except Exception:
                self._dashboard_fields = set()

        return self._dashboard_fields

    def extract_fields_from_jobs(self, jobs: List[Dict[str, Any]]) -> List[MetadataField]:
        """
        Extrai todos os campos metadata de uma lista de jobs

        Args:
            jobs: Lista de jobs do Prometheus

        Returns:
            Lista de MetadataField identificados
        """
        fields_map: Dict[str, MetadataField] = {}

        for job in jobs:
            job_name = job.get('job_name', 'unknown')
            relabel_configs = job.get('relabel_configs', [])

            for relabel in relabel_configs:
                field = self._extract_field_from_relabel(relabel, job_name)

                if field:
                    # Se já existe, mesclar informações
                    if field.name in fields_map:
                        existing = fields_map[field.name]
                        # Manter regex/replacement se ainda não definidos
                        if not existing.regex and field.regex:
                            existing.regex = field.regex
                        if not existing.replacement and field.replacement:
                            existing.replacement = field.replacement
                    else:
                        fields_map[field.name] = field

        # Converter para lista ordenada
        fields = list(fields_map.values())

        # Ordenar: campos obrigatórios primeiro, depois alfabético
        fields.sort(key=lambda f: (not f.required, f.name))

        logger.info(f"Extraídos {len(fields)} campos metadata")
        return fields

    def _extract_field_from_relabel(
        self,
        relabel: Dict[str, Any],
        job_name: str
    ) -> Optional[MetadataField]:
        """
        Extrai campo metadata de um relabel_config

        Args:
            relabel: Configuração de relabel
            job_name: Nome do job (para contexto)

        Returns:
            MetadataField ou None se não for metadata field
        """
        source_labels = relabel.get('source_labels', [])
        target_label = relabel.get('target_label')
        action = relabel.get('action', 'replace')

        # Ignorar relabels que não são replace ou labelmap
        if action not in ['replace', 'labelmap']:
            return None

        # Procurar source_labels que são metadata do Consul
        metadata_source = None
        for source in source_labels:
            if isinstance(source, str) and source.startswith('__meta_consul_service_metadata_'):
                metadata_source = source
                break

        if not metadata_source or not target_label:
            return None

        # FILTRO: Ignorar campos internos do Prometheus que começam com "__"
        if isinstance(target_label, str) and target_label.startswith('__'):
            return None

        # Extrair nome do campo do source_label
        # __meta_consul_service_metadata_company → company
        field_name = metadata_source.replace('__meta_consul_service_metadata_', '')

        # Criar MetadataField
        field = MetadataField(
            name=target_label,
            display_name=self._generate_display_name(target_label),
            source_label=metadata_source,
            field_type=self._infer_field_type(target_label, field_name),
            required=target_label in self.REQUIRED_FIELDS,
            show_in_table=True,  # Por padrão, todos aparecem na tabela
            show_in_dashboard=target_label in self.DASHBOARD_FIELDS,
            regex=relabel.get('regex'),
            replacement=relabel.get('replacement')
        )

        return field

    def _generate_display_name(self, field_name: str) -> str:
        """
        Gera nome amigável para o campo

        Args:
            field_name: Nome técnico do campo

        Returns:
            Nome amigável
        """
        # Mapeamento de nomes comuns
        name_map = {
            'company': 'Empresa',
            'env': 'Ambiente',
            'project': 'Projeto',
            'name': 'Nome',
            'instance': 'Instância',
            'module': 'Módulo',
            'group': 'Grupo',
            'region': 'Região',
            'datacenter': 'Datacenter',
            'vendor': 'Fornecedor',
            'account': 'Conta',
            'os': 'Sistema Operacional',
        }

        if field_name in name_map:
            return name_map[field_name]

        # Fallback: Capitalizar e substituir _ por espaço
        return field_name.replace('_', ' ').title()

    def _infer_field_type(self, target_label: str, source_name: str) -> str:
        """
        Infere tipo do campo baseado no nome

        Args:
            target_label: Nome do target_label
            source_name: Nome original do metadata

        Returns:
            "string", "number" ou "select"
        """
        # Campos que geralmente são selects (opções limitadas)
        select_fields = {'env', 'module', 'os', 'region', 'datacenter'}

        # Campos numéricos
        number_fields = {'port', 'timeout', 'interval'}

        if target_label in select_fields or source_name in select_fields:
            return 'select'
        elif target_label in number_fields or source_name in number_fields:
            return 'number'
        else:
            return 'string'

    async def enrich_fields_with_values(
        self,
        fields: List[MetadataField]
    ) -> List[MetadataField]:
        """
        Enriquece campos com valores únicos do Consul

        Args:
            fields: Lista de campos a enriquecer

        Returns:
            Lista de campos com opções preenchidas
        """
        if not self.consul_manager:
            logger.warning("ConsulManager não disponível para enriquecer campos")
            return fields

        # Buscar todos os serviços do Consul
        try:
            services = await self.consul_manager.get_services()
        except Exception as e:
            logger.error(f"Erro ao buscar serviços do Consul: {e}")
            return fields

        # Extrair valores únicos para cada campo
        for field in fields:
            if field.field_type == 'select':
                values = self._extract_unique_values(services, field.name)
                field.options = sorted(values)

        return fields

    def _extract_unique_values(
        self,
        services: Dict[str, Any],
        field_name: str
    ) -> Set[str]:
        """
        Extrai valores únicos de um campo dos serviços

        Args:
            services: Dicionário de serviços do Consul
            field_name: Nome do campo

        Returns:
            Set de valores únicos
        """
        values = set()

        for service_data in services.values():
            meta = service_data.get('Meta', {})

            if field_name in meta:
                value = meta[field_name]
                if value:  # Ignorar valores vazios
                    values.add(str(value))

        return values

    def get_field_statistics(
        self,
        services: Dict[str, Any],
        field_name: str
    ) -> Dict[str, Any]:
        """
        Gera estatísticas sobre um campo

        Args:
            services: Serviços do Consul
            field_name: Nome do campo

        Returns:
            Dict com estatísticas
        """
        value_counts = defaultdict(int)
        total = 0

        for service_data in services.values():
            meta = service_data.get('Meta', {})

            if field_name in meta:
                value = meta[field_name]
                value_counts[value] += 1
                total += 1

        return {
            'field': field_name,
            'total_services': total,
            'unique_values': len(value_counts),
            'values': dict(value_counts),
            'most_common': sorted(
                value_counts.items(),
                key=lambda x: x[1],
                reverse=True
            )[:10]  # Top 10
        }

    def validate_service_metadata(
        self,
        service_meta: Dict[str, Any],
        required_fields: List[MetadataField]
    ) -> tuple[bool, List[str]]:
        """
        Valida se metadata de um serviço tem todos os campos obrigatórios

        Args:
            service_meta: Metadata do serviço
            required_fields: Lista de campos obrigatórios

        Returns:
            (válido, lista de erros)
        """
        errors = []

        for field in required_fields:
            if not field.required:
                continue

            if field.name not in service_meta:
                errors.append(f"Campo obrigatório ausente: {field.display_name}")
            elif not service_meta[field.name]:
                errors.append(f"Campo obrigatório vazio: {field.display_name}")

        return len(errors) == 0, errors

    def generate_relabel_config(
        self,
        field: MetadataField,
        action: str = 'replace'
    ) -> Dict[str, Any]:
        """
        Gera configuração de relabel para um campo

        Args:
            field: Campo metadata
            action: Ação do relabel (replace, keep, drop, etc)

        Returns:
            Dict com configuração do relabel
        """
        config = {
            'source_labels': [field.source_label],
            'target_label': field.name
        }

        if action and action != 'replace':
            config['action'] = action

        if field.regex:
            config['regex'] = field.regex

        if field.replacement:
            config['replacement'] = field.replacement

        return config

    def suggest_fields_from_services(
        self,
        services: Dict[str, Any]
    ) -> List[MetadataField]:
        """
        Analisa serviços existentes e sugere campos metadata

        Args:
            services: Serviços do Consul

        Returns:
            Lista de campos sugeridos
        """
        # Analisar todas as chaves de metadata
        all_meta_keys: Set[str] = set()

        for service_data in services.values():
            meta = service_data.get('Meta', {})
            all_meta_keys.update(meta.keys())

        # Criar MetadataField para cada chave encontrada
        suggested_fields = []

        for key in sorted(all_meta_keys):
            field = MetadataField(
                name=key,
                display_name=self._generate_display_name(key),
                source_label=f'__meta_consul_service_metadata_{key}',
                field_type=self._infer_field_type(key, key),
                required=key in self.REQUIRED_FIELDS,
                show_in_table=True,
                show_in_dashboard=key in self.DASHBOARD_FIELDS
            )

            # Adicionar valores únicos
            values = self._extract_unique_values(services, key)
            if field.field_type == 'select':
                field.options = sorted(values)

            suggested_fields.append(field)

        logger.info(f"Sugeridos {len(suggested_fields)} campos baseados em serviços existentes")
        return suggested_fields
