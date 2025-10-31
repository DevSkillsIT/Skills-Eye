"""
Metadata Loader - FONTE ÚNICA DA VERDADE

Este módulo centraliza TODA a leitura de metadata_fields.json.
NUNCA mais use campos hardcoded em outro lugar!

Uso:
    from core.metadata_loader import MetadataLoader

    loader = MetadataLoader()
    required_fields = loader.get_required_fields()
    blackbox_fields = loader.get_fields(show_in_blackbox=True)
"""

import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class MetadataField:
    """
    Representa um campo de metadata com todas as suas propriedades
    """
    def __init__(self, data: Dict[str, Any]):
        # Propriedades básicas
        self.name: str = data['name']
        self.display_name: str = data['display_name']
        self.description: str = data.get('description', '')
        self.source_label: str = data.get('source_label', '')
        self.field_type: str = data.get('field_type', 'string')

        # Controles de obrigatoriedade
        self.required: bool = data.get('required', False)

        # Controles de visibilidade
        self.enabled: bool = data.get('enabled', True)
        self.show_in_table: bool = data.get('show_in_table', True)
        self.show_in_dashboard: bool = data.get('show_in_dashboard', False)
        self.show_in_form: bool = data.get('show_in_form', True)
        self.show_in_filter: bool = data.get('show_in_filter', True)

        # Controles por tipo de exporter/serviço
        self.show_in_blackbox: bool = data.get('show_in_blackbox', True)
        self.show_in_exporters: bool = data.get('show_in_exporters', True)
        self.show_in_services: bool = data.get('show_in_services', True)

        # Controles de edição
        self.editable: bool = data.get('editable', True)
        self.available_for_registration: bool = data.get('available_for_registration', True)

        # Metadados
        self.options: List[str] = data.get('options', [])
        self.default_value: Optional[Any] = data.get('default_value')
        self.placeholder: str = data.get('placeholder', '')
        self.order: int = data.get('order', 999)
        self.category: str = data.get('category', 'basic')
        self.validation: Dict[str, Any] = data.get('validation', {})

    def to_dict(self) -> Dict[str, Any]:
        """Converte para dicionário"""
        return {
            'name': self.name,
            'display_name': self.display_name,
            'description': self.description,
            'source_label': self.source_label,
            'field_type': self.field_type,
            'required': self.required,
            'enabled': self.enabled,
            'show_in_table': self.show_in_table,
            'show_in_dashboard': self.show_in_dashboard,
            'show_in_form': self.show_in_form,
            'show_in_filter': self.show_in_filter,
            'show_in_blackbox': self.show_in_blackbox,
            'show_in_exporters': self.show_in_exporters,
            'show_in_services': self.show_in_services,
            'editable': self.editable,
            'available_for_registration': self.available_for_registration,
            'options': self.options,
            'default_value': self.default_value,
            'placeholder': self.placeholder,
            'order': self.order,
            'category': self.category,
            'validation': self.validation,
        }


class MetadataLoader:
    """
    Carrega e gerencia campos de metadata do arquivo JSON

    SINGLETON: Mantém cache em memória para performance
    """

    _instance = None
    _cache: Optional[List[MetadataField]] = None
    _cache_time: Optional[datetime] = None
    _cache_ttl: int = 60  # 60 segundos de cache

    def __new__(cls):
        """Singleton pattern"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @property
    def json_path(self) -> Path:
        """Caminho do arquivo JSON"""
        return Path(__file__).parent.parent / 'config' / 'metadata_fields.json'

    def _load_from_file(self) -> List[MetadataField]:
        """Carrega campos do arquivo JSON"""
        try:
            with open(self.json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                fields_data = data.get('fields', [])

                # Converter para objetos MetadataField
                fields = [MetadataField(field_data) for field_data in fields_data]

                logger.info(f"[MetadataLoader] Carregados {len(fields)} campos de {self.json_path}")
                return fields
        except FileNotFoundError:
            logger.error(f"[MetadataLoader] Arquivo não encontrado: {self.json_path}")
            return []
        except json.JSONDecodeError as e:
            logger.error(f"[MetadataLoader] Erro ao parsear JSON: {e}")
            return []
        except Exception as e:
            logger.error(f"[MetadataLoader] Erro ao carregar campos: {e}")
            return []

    def get_all_fields(self, reload: bool = False) -> List[MetadataField]:
        """
        Retorna TODOS os campos

        Args:
            reload: Forçar reload do arquivo (ignora cache)

        Returns:
            Lista de MetadataField
        """
        # Verificar se precisa recarregar
        now = datetime.now()
        should_reload = (
            reload or
            self._cache is None or
            self._cache_time is None or
            (now - self._cache_time).total_seconds() > self._cache_ttl
        )

        if should_reload:
            self._cache = self._load_from_file()
            self._cache_time = now
            logger.info(f"[MetadataLoader] Cache recarregado: {len(self._cache)} campos")

        return self._cache or []

    def get_fields(
        self,
        enabled: Optional[bool] = None,
        required: Optional[bool] = None,
        show_in_table: Optional[bool] = None,
        show_in_dashboard: Optional[bool] = None,
        show_in_form: Optional[bool] = None,
        show_in_filter: Optional[bool] = None,
        show_in_blackbox: Optional[bool] = None,
        show_in_exporters: Optional[bool] = None,
        show_in_services: Optional[bool] = None,
        category: Optional[str] = None,
    ) -> List[MetadataField]:
        """
        Retorna campos filtrados por critérios

        Args:
            enabled: Filtrar por campo ativo
            required: Filtrar por obrigatório
            show_in_*: Filtros de visibilidade
            category: Filtrar por categoria

        Returns:
            Lista de MetadataField filtrados
        """
        fields = self.get_all_fields()

        # Aplicar filtros
        if enabled is not None:
            fields = [f for f in fields if f.enabled == enabled]
        if required is not None:
            fields = [f for f in fields if f.required == required]
        if show_in_table is not None:
            fields = [f for f in fields if f.show_in_table == show_in_table]
        if show_in_dashboard is not None:
            fields = [f for f in fields if f.show_in_dashboard == show_in_dashboard]
        if show_in_form is not None:
            fields = [f for f in fields if f.show_in_form == show_in_form]
        if show_in_filter is not None:
            fields = [f for f in fields if f.show_in_filter == show_in_filter]
        if show_in_blackbox is not None:
            fields = [f for f in fields if f.show_in_blackbox == show_in_blackbox]
        if show_in_exporters is not None:
            fields = [f for f in fields if f.show_in_exporters == show_in_exporters]
        if show_in_services is not None:
            fields = [f for f in fields if f.show_in_services == show_in_services]
        if category is not None:
            fields = [f for f in fields if f.category == category]

        return fields

    def get_field_names(self, **filters) -> List[str]:
        """
        Retorna apenas os NOMES dos campos (útil para validações)

        Args:
            **filters: Mesmos filtros de get_fields()

        Returns:
            Lista de nomes de campos
        """
        fields = self.get_fields(**filters)
        return [f.name for f in fields]

    def get_required_fields(self) -> List[str]:
        """Retorna nomes dos campos obrigatórios"""
        return self.get_field_names(enabled=True, required=True)

    def get_blackbox_fields(self) -> List[MetadataField]:
        """Retorna campos para Blackbox Targets"""
        return self.get_fields(enabled=True, show_in_blackbox=True)

    def get_exporters_fields(self) -> List[MetadataField]:
        """Retorna campos para Exporters (Node/Windows)"""
        return self.get_fields(enabled=True, show_in_exporters=True)

    def get_services_fields(self) -> List[MetadataField]:
        """Retorna campos para Services gerais"""
        return self.get_fields(enabled=True, show_in_services=True)

    def get_filter_fields(self) -> List[MetadataField]:
        """Retorna campos para barra de filtros"""
        return self.get_fields(enabled=True, show_in_filter=True)

    def get_form_fields(self, context: str = 'general') -> List[MetadataField]:
        """
        Retorna campos para formulários

        Args:
            context: 'blackbox', 'exporters', 'services', 'general'

        Returns:
            Lista de campos apropriados para o contexto
        """
        filters = {'enabled': True, 'show_in_form': True}

        if context == 'blackbox':
            filters['show_in_blackbox'] = True
        elif context == 'exporters':
            filters['show_in_exporters'] = True
        elif context == 'services':
            filters['show_in_services'] = True

        fields = self.get_fields(**filters)
        # Ordenar por order
        fields.sort(key=lambda f: f.order)
        return fields

    def get_field_by_name(self, name: str) -> Optional[MetadataField]:
        """Retorna um campo específico pelo nome"""
        fields = self.get_all_fields()
        for field in fields:
            if field.name == name:
                return field
        return None

    def validate_metadata(self, metadata: Dict[str, Any], context: str = 'general') -> Dict[str, Any]:
        """
        Valida metadata contra os campos definidos

        Args:
            metadata: Dicionário com metadata
            context: Contexto ('blackbox', 'exporters', 'services')

        Returns:
            Dict com: {"valid": bool, "errors": List[str], "warnings": List[str]}
        """
        errors = []
        warnings = []

        # Obter campos obrigatórios para o contexto
        required_fields = self.get_field_names(
            enabled=True,
            required=True,
            **{f'show_in_{context}': True} if context != 'general' else {}
        )

        # Verificar campos obrigatórios
        for field_name in required_fields:
            if field_name not in metadata or not metadata[field_name]:
                field = self.get_field_by_name(field_name)
                display_name = field.display_name if field else field_name
                errors.append(f"Campo obrigatório ausente: {display_name}")

        # Verificar campos com opções (select)
        for field_name, value in metadata.items():
            field = self.get_field_by_name(field_name)
            if field and field.options and value not in field.options:
                warnings.append(
                    f"Valor '{value}' não está nas opções de '{field.display_name}'. "
                    f"Opções válidas: {', '.join(field.options)}"
                )

        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings
        }

    def reload(self):
        """Força reload do cache"""
        self._cache = None
        self._cache_time = None
        logger.info("[MetadataLoader] Cache limpo - próxima chamada irá recarregar")


# Instância global (singleton)
metadata_loader = MetadataLoader()


# Funções de conveniência (atalhos)
def get_required_fields() -> List[str]:
    """Atalho: retorna campos obrigatórios"""
    return metadata_loader.get_required_fields()


def get_all_field_names() -> List[str]:
    """Atalho: retorna todos os nomes de campos"""
    return metadata_loader.get_field_names(enabled=True)


def get_blackbox_fields() -> List[MetadataField]:
    """Atalho: retorna campos para Blackbox"""
    return metadata_loader.get_blackbox_fields()


def get_exporters_fields() -> List[MetadataField]:
    """Atalho: retorna campos para Exporters"""
    return metadata_loader.get_exporters_fields()


def validate_metadata(metadata: Dict[str, Any], context: str = 'general') -> Dict[str, Any]:
    """Atalho: valida metadata"""
    return metadata_loader.validate_metadata(metadata, context)
