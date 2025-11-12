"""
Serviço de Extração de Campos Dinâmicos

Este módulo analisa os relabel_configs do Prometheus e identifica:
- Campos metadata do Consul (__meta_consul_service_metadata_*)
- Target labels que são gerados
- Tipos de dados inferidos
- Valores únicos existentes

Estes campos são usados para gerar formulários dinâmicos no frontend.
"""

from typing import Dict, List, Set, Optional, Any, Union
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

    # Campos adicionais para compatibilidade completa com frontend
    description: str = ""  # Descrição do campo
    show_in_form: bool = True  # Se aparece em formulários
    show_in_services: bool = True  # Se aparece na página Services
    show_in_exporters: bool = True  # Se aparece na página Exporters
    show_in_blackbox: bool = True  # Se aparece na página Blackbox
    show_in_filter: bool = True  # Se aparece nos filtros
    order: int = 999  # Ordem de exibição
    category: Union[str, List[str]] = "extra"  # Categoria(s) - aceita string única ou lista para múltiplas
    editable: bool = True  # Se pode ser editado
    enabled: bool = True  # Se está habilitado
    available_for_registration: bool = False  # Se disponível para registro (PADRÃO: DESABILITADO)
    validation_regex: Optional[str] = None  # Regex de validação (deprecated)
    validation: Optional[Dict[str, Any]] = None  # Validação (objeto)
    default_value: Optional[Any] = None  # Valor padrão
    placeholder: str = ""  # Placeholder para input
    discovered_in: List[str] = None  # Lista de hostnames onde campo foi descoberto (MULTI-SERVER)

    def to_dict(self) -> Dict[str, Any]:
        """Converte para dicionário"""
        result = asdict(self)
        # Garantir que discovered_in seja sempre uma lista (não None)
        if result.get('discovered_in') is None:
            result['discovered_in'] = []
        return result


class FieldsExtractionService:
    """Serviço para extrair campos dinâmicos dos relabel_configs

    AGORA USA METADATA_LOADER - Sistema totalmente dinâmico!
    """

    def __init__(self, consul_manager=None, required_fields: set = None, dashboard_fields: set = None):
        """
        Inicializa o serviço

        Args:
            consul_manager: Instância do ConsulManager para buscar valores únicos
            required_fields: Set de campos obrigatórios (se None, usa fallback estático)
            dashboard_fields: Set de campos do dashboard (se None, usa fallback estático)
        """
        self.consul_manager = consul_manager

        # CORREÇÃO: Usar valores passados ou fallback estático
        # Não podemos usar asyncio.run() em properties porque causa RuntimeWarning
        # quando chamado de dentro de código async do FastAPI
        self._required_fields = required_fields if required_fields is not None else {
            'company', 'env', 'instance'  # Fallback: campos mais comuns
        }
        self._dashboard_fields = dashboard_fields if dashboard_fields is not None else {
            'company', 'env', 'vendor', 'region'  # Fallback: campos mais úteis
        }

    @property
    def REQUIRED_FIELDS(self) -> set:
        """
        Campos obrigatórios.

        IMPORTANTE: Valores são passados no __init__ ou usa fallback estático.
        Para carregar dinamicamente do KV, passe os valores ao instanciar.
        """
        return self._required_fields

    @property
    def DASHBOARD_FIELDS(self) -> set:
        """
        Campos do dashboard.

        IMPORTANTE: Valores são passados no __init__ ou usa fallback estático.
        Para carregar dinamicamente do KV, passe os valores ao instanciar.
        """
        return self._dashboard_fields

    def extract_fields_from_jobs(self, jobs: List[Dict[str, Any]]) -> List[MetadataField]:
        """
        Extrai todos os campos metadata de uma lista de jobs

        ALGORITMO UNIVERSAL - Replicado do PrometheusConfig.tsx

        Args:
            jobs: Lista de jobs do Prometheus

        Returns:
            Lista de MetadataField identificados
        """
        fields_map: Dict[str, MetadataField] = {}

        for job in jobs:
            job_name = job.get('job_name', 'unknown')
            relabel_configs = job.get('relabel_configs', [])

            # PASSO 1: Detectar padrão multi-target para este job
            multi_target_info = self._detect_multi_target_pattern(relabel_configs)
            is_multi_target = multi_target_info is not None

            # PASSO 2: Processar todos os relabel_configs
            for relabel in relabel_configs:
                source_labels = relabel.get('source_labels', [])
                target_label = relabel.get('target_label')

                # FILTROS: O que ignorar
                if not target_label:
                    continue
                if target_label.startswith('__'):
                    continue
                if target_label == 'job':
                    continue
                # IMPORTANTE: NÃO filtrar 'instance' em multi-target!
                # Se instance vem de __param_target, é uma transformação EXPLÍCITA válida
                # As condições de inclusão abaixo já tratam corretamente

                # CONDIÇÕES DE INCLUSÃO (qualquer uma verdadeira = incluir campo)

                # 1. Tem source com __meta_* (service discovery: Consul, K8s, EC2, etc)
                has_meta_source = any(sl and sl.startswith('__meta_') for sl in source_labels)

                # 2. Tem source com __param_* (multi-target exporters: SNMP, Blackbox)
                has_param_source = any(sl and sl.startswith('__param_') for sl in source_labels)

                # 3. Transformação válida: source_labels públicos (sem __) gerando target público
                #    Isso captura file_sd (datacenter→dc) e static (env→priority)
                has_valid_transformation = (
                    len(source_labels) > 0 and
                    any(sl and not sl.startswith('__') for sl in source_labels)
                )

                # INCLUIR se QUALQUER condição for verdadeira
                if has_meta_source or is_multi_target or has_param_source or has_valid_transformation:
                    # PASSO 3: Identificar tipo de service discovery
                    sd_type = self._identify_service_discovery(source_labels)

                    # PASSO 4: Extrair source_label principal
                    source_label = self._get_source_pattern(source_labels, sd_type)

                    # PASSO 5: Criar MetadataField
                    field = MetadataField(
                        name=target_label,
                        display_name=self._generate_display_name(target_label),
                        source_label=source_label,
                        field_type=self._infer_field_type(target_label, target_label),
                        required=target_label in self.REQUIRED_FIELDS,
                        show_in_table=True,  # Por padrão, todos aparecem na tabela
                        show_in_dashboard=target_label in self.DASHBOARD_FIELDS,
                        regex=relabel.get('regex'),
                        replacement=relabel.get('replacement')
                    )

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

            logger.debug(
                f"[EXTRACT-UNIVERSAL] Job '{job_name}': "
                f"Extraídos {len([f for f in fields_map.values()])} campos "
                f"(multi-target={is_multi_target})"
            )

        # Converter para lista ordenada
        fields = list(fields_map.values())

        # Ordenar: campos obrigatórios primeiro, depois alfabético
        fields.sort(key=lambda f: (not f.required, f.name))

        # CORREÇÃO: Atribuir ordens sequenciais aos campos
        # Campos obrigatórios: 1-19, campos opcionais: 20+
        for index, field in enumerate(fields, start=1):
            field.order = index

        logger.info(f"[EXTRACT-UNIVERSAL] Extraídos {len(fields)} campos metadata TOTAL de {len(jobs)} jobs")
        return fields

    # ============================================================================
    # FUNÇÕES HELPER UNIVERSAIS - Replicadas do PrometheusConfig.tsx
    # ============================================================================

    @staticmethod
    def _identify_service_discovery(source_labels: List[str]) -> str:
        """
        Identifica o tipo de service discovery baseado nos prefixos dos source_labels

        Args:
            source_labels: Array de source labels do relabel_config

        Returns:
            Tipo de service discovery detectado
        """
        patterns = {
            'consul': '__meta_consul_',
            'ec2': '__meta_ec2_',
            'kubernetes': '__meta_kubernetes_',
            'dns': '__meta_dns_',
            'file': '__meta_filepath',
            'digitalocean': '__meta_digitalocean_',
            'docker': '__meta_docker_',
            # Multi-target exporters (SNMP, Blackbox)
            'param': '__param_'
        }

        for sd_type, prefix in patterns.items():
            if any(sl and sl.startswith(prefix) for sl in source_labels):
                return sd_type

        return 'static'  # Static targets

    @staticmethod
    def _is_custom_metadata_field(source_labels: List[str], sd_type: str) -> bool:
        """
        Determina se é um campo customizado pelo usuário (vs campo padrão do service discovery)

        Args:
            source_labels: Array de source labels
            sd_type: Tipo de service discovery

        Returns:
            True se for campo customizado
        """
        custom_patterns = {
            # Consul: campos com _metadata_ são customizados pelo usuário
            'consul': lambda label: '_metadata_' in label,
            # EC2: tags customizadas
            'ec2': lambda label: '_tag_' in label,
            # Kubernetes: labels e annotations customizadas
            'kubernetes': lambda label: '_label_' in label or '_annotation_' in label,
            # SNMP/Blackbox não têm campos custom nativos, usam __param_
        }

        checker = custom_patterns.get(sd_type)
        if not checker:
            return False

        return any(checker(sl) for sl in source_labels if sl)

    @staticmethod
    def _get_source_pattern(source_labels: List[str], sd_type: str) -> str:
        """
        Extrai padrão do source_label para identificação

        Args:
            source_labels: Array de source labels
            sd_type: Tipo de service discovery

        Returns:
            Padrão identificado
        """
        # Retorna o primeiro source_label que identifica o tipo
        meta_label = next((sl for sl in source_labels if sl and sl.startswith('__meta_')), None)
        return meta_label or (source_labels[0] if source_labels else 'unknown')

    @staticmethod
    def _detect_multi_target_pattern(relabel_configs: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """
        Detecta e processa padrão multi-target (SNMP/Blackbox Exporters)

        Multi-target exporters usam um padrão onde:
        - __param_target define o alvo real
        - __address__ é substituído pelo endereço do exporter

        Args:
            relabel_configs: Array completo de relabel configs

        Returns:
            Informações do multi-target ou None
        """
        # Padrão característico de multi-target exporters
        has_param_target = any(
            rc.get('target_label') == '__param_target'
            for rc in relabel_configs
        )

        has_address_replacement = any(
            rc.get('target_label') == '__address__' and rc.get('replacement')
            for rc in relabel_configs
        )

        if has_param_target and has_address_replacement:
            # É um multi-target exporter
            # IMPORTANTE: instance agora É VÁLIDO quando vem de __param_target
            extractable_fields = [
                rc.get('target_label')
                for rc in relabel_configs
                if rc.get('target_label') and
                   not rc.get('target_label').startswith('__')
                   # Removido filtro de 'instance' - é um campo válido!
            ]
            return {
                'type': 'multi-target',
                'extractable_fields': extractable_fields
            }

        return None

    # ============================================================================

    def _extract_field_from_relabel(
        self,
        relabel: Dict[str, Any],
        job_name: str
    ) -> Optional[MetadataField]:
        """
        ⚠️ DEPRECATED: Substituída pela lógica universal em extract_fields_from_jobs()

        Esta função está mantida apenas para compatibilidade, mas NÃO É MAIS USADA.
        A nova implementação universal suporta TODOS os tipos de service discovery:
        - Consul, EC2, Kubernetes, Docker, DNS, DigitalOcean
        - SNMP/Blackbox (multi-target)
        - file_sd e static (transformações)

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

    @staticmethod
    def enrich_fields_with_static_metadata(fields: List[MetadataField]) -> List[MetadataField]:
        """
        Enriquece campos extraídos do Prometheus com metadata estática

        IMPORTANTE: Mescla campos dinâmicos (do Prometheus) com configuração
        estática (category, order, description, etc.)

        Args:
            fields: Lista de campos extraídos do Prometheus

        Returns:
            Lista de campos enriquecidos com metadata completa
        """
        # Mapeamento de campos conhecidos com metadata completa
        STATIC_METADATA = {
            "cservice": {
                "description": "Nome do serviço registrado no Consul",
                "category": "infrastructure",
                "order": 1,
                "show_in_form": True,
                "show_in_services": True,
                "show_in_exporters": True,
                "show_in_blackbox": True,
            },
            "vendor": {
                "description": "Fornecedor do serviço ou infraestrutura (AWS, Azure, GCP, etc)",
                "category": "infrastructure",
                "order": 2,
                "field_type": "select",
            },
            "region": {
                "description": "Região geográfica do serviço",
                "category": "infrastructure",
                "order": 3,
            },
            "account": {
                "description": "Conta ou tenant do serviço",
                "category": "infrastructure",
                "order": 5,
            },
            "instance": {
                "description": "IP ou hostname da instância",
                "category": "basic",
                "order": 8,
                "required": True,
                "validation_regex": "^[a-zA-Z0-9\\.\\-:]+$",
            },
            "company": {
                "description": "Empresa ou cliente proprietário do serviço",
                "category": "basic",
                "order": 10,
                "required": True,
            },
            "project": {
                "description": "Nome do projeto ao qual o serviço pertence",
                "category": "basic",
                "order": 11,
            },
            "env": {
                "description": "Ambiente do serviço",
                "category": "basic",
                "order": 12,
                "required": True,
                "field_type": "select",
            },
            "module": {
                "description": "Nome do módulo do Blackbox Exporter",
                "category": "basic",
                "order": 13,
                "field_type": "select",
            },
            "name": {
                "description": "Nome descritivo do serviço",
                "category": "basic",
                "order": 14,
            },
            "exporter_version": {
                "description": "Versão do exporter instalado",
                "category": "device",
                "order": 20,
            },
            "os": {
                "description": "Sistema operacional",
                "category": "device",
                "order": 21,
                "field_type": "select",
            },
            "datacenter": {
                "description": "Datacenter onde o serviço está hospedado",
                "category": "infrastructure",
                "order": 4,
            },
            "cluster": {
                "description": "Cluster ou agrupamento lógico",
                "category": "infrastructure",
                "order": 6,
            },
            "site": {
                "description": "Site ou localização física",
                "category": "infrastructure",
                "order": 7,
            },
            "group": {
                "description": "Grupo ou categoria de serviços",
                "category": "extra",
                "order": 100,
            },
        }

        enriched_fields = []

        for field in fields:
            # Obter metadata estática se existir
            static = STATIC_METADATA.get(field.name, {})

            # Aplicar metadata estática ao campo
            if static:
                # Preservar valores extraídos do Prometheus
                field.description = static.get("description", field.description)
                field.category = static.get("category", field.category)
                field.order = static.get("order", field.order)
                field.show_in_form = static.get("show_in_form", field.show_in_form)
                field.show_in_services = static.get("show_in_services", field.show_in_services)
                field.show_in_exporters = static.get("show_in_exporters", field.show_in_exporters)
                field.show_in_blackbox = static.get("show_in_blackbox", field.show_in_blackbox)
                field.validation_regex = static.get("validation_regex", field.validation_regex)

                # Mesclar required (priorizar se já está True no Prometheus)
                if static.get("required", False):
                    field.required = True

                # Mesclar field_type (priorizar metadata estática se mais específico)
                if static.get("field_type"):
                    field.field_type = static["field_type"]

            # Converter validation_regex para objeto validation
            if field.validation_regex and not field.validation:
                field.validation = {
                    "pattern": field.validation_regex,
                    "message": f"Formato inválido para {field.display_name}"
                }

            enriched_fields.append(field)

        # Ordenar por order
        enriched_fields.sort(key=lambda f: f.order)

        logger.info(f"[ENRICH] Enriquecidos {len(enriched_fields)} campos com metadata estática")
        return enriched_fields

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
