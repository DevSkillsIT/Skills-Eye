"""
Monitoring Type Manager - Gerencia tipos de monitoramento configuráveis

Este módulo implementa o sistema configuration-driven onde tipos de monitoramento
são definidos via JSON schemas armazenados no Consul KV ou em arquivos.

CRÍTICO: Sistema é 100% agnóstico a nomes de exporters/módulos.
         Usa matchers flexíveis para suportar qualquer nomenclatura.
"""

import json
import os
from typing import List, Dict, Optional, Any
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class MonitoringTypeManager:
    """
    Gerencia tipos de monitoramento configuration-driven

    Suporta dois modos:
    1. File-based: Lê JSONs do diretório backend/schemas/monitoring-types/
    2. Consul KV-based (futuro): Lê de skills/eye/monitoring-types/
    """

    def __init__(self, consul_client=None, use_local_files=True):
        """
        Args:
            consul_client: Cliente Consul para modo KV (futuro)
            use_local_files: Se True, lê JSONs locais (modo desenvolvimento)
        """
        self.consul = consul_client
        self.use_local_files = use_local_files
        self.schemas_dir = Path(__file__).parent.parent / "schemas" / "monitoring-types"

        # Cache de schemas em memória
        self._schema_cache: Dict[str, Dict] = {}

    async def get_all_categories(self) -> List[Dict]:
        """
        Retorna todas as categorias de monitoramento disponíveis

        Returns:
            List de dicts com estrutura:
            [
                {
                    "category": "network-probes",
                    "display_name": "Network Probes (Rede)",
                    "icon": "📡",
                    "color": "blue",
                    "enabled": true,
                    "order": 1,
                    "types": [...],  // Array de tipos
                    "page_config": {...}
                },
                ...
            ]
        """
        categories = []

        if self.use_local_files:
            # Ler JSONs do diretório local
            if not self.schemas_dir.exists():
                logger.warning(f"Schemas directory not found: {self.schemas_dir}")
                return []

            for json_file in self.schemas_dir.glob("*.json"):
                try:
                    with open(json_file, 'r', encoding='utf-8') as f:
                        schema = json.load(f)

                    # Validar schema básico
                    if not self._validate_basic_schema(schema):
                        logger.error(f"Invalid schema in {json_file.name}")
                        continue

                    # Adicionar ao cache
                    self._schema_cache[schema['category']] = schema

                    categories.append(schema)

                except Exception as e:
                    logger.error(f"Error loading schema {json_file.name}: {e}")
                    continue

        # Ordenar por order field
        categories.sort(key=lambda x: x.get('order', 999))

        return categories

    async def get_category(self, category: str) -> Optional[Dict]:
        """
        Retorna schema completo de uma categoria específica

        Args:
            category: ID da categoria (ex: 'network-probes')

        Returns:
            Dict com schema completo ou None se não encontrado
        """
        # Verificar cache primeiro
        if category in self._schema_cache:
            return self._schema_cache[category]

        if self.use_local_files:
            json_file = self.schemas_dir / f"{category}.json"

            if not json_file.exists():
                logger.warning(f"Category schema not found: {category}")
                return None

            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    schema = json.load(f)

                # Adicionar ao cache
                self._schema_cache[category] = schema

                return schema

            except Exception as e:
                logger.error(f"Error loading category {category}: {e}")
                return None

        return None

    async def get_type(self, category: str, type_id: str) -> Optional[Dict]:
        """
        Retorna schema de um tipo específico dentro de uma categoria

        Args:
            category: ID da categoria (ex: 'network-probes')
            type_id: ID do tipo (ex: 'icmp')

        Returns:
            Dict com schema do tipo ou None se não encontrado
        """
        category_schema = await self.get_category(category)

        if not category_schema:
            return None

        # Buscar tipo específico no array types
        for type_def in category_schema.get('types', []):
            if type_def.get('id') == type_id:
                # Retornar tipo com contexto da categoria
                return {
                    **type_def,
                    "category": category,
                    "category_display_name": category_schema.get('display_name'),
                    "category_icon": category_schema.get('icon'),
                }

        logger.warning(f"Type {type_id} not found in category {category}")
        return None

    def build_filter_query(self, type_schema: Dict) -> Dict:
        """
        Constrói query de filtro baseado em matchers do schema

        CRÍTICO: Este método permite que o sistema funcione com QUALQUER nome
                 de exporter/módulo, eliminando vendor lock-in.

        Args:
            type_schema: Schema do tipo (com field 'matchers')

        Returns:
            Dict com estrutura de query:
            {
                "operator": "and",
                "conditions": [
                    {"field": "Meta.exporter_type", "operator": "in", "values": [...]},
                    {"field": "Meta.module", "operator": "in", "values": [...]}
                ]
            }

        Exemplo:
            Para Node Exporter com matchers:
            {
                "exporter_type_values": ["node", "selfnode", "custom-node"]
            }

            Resultado:
            {
                "conditions": [
                    {
                        "field": "Meta.exporter_type",
                        "operator": "in",
                        "values": ["node", "selfnode", "custom-node"]
                    }
                ]
            }
        """
        matchers = type_schema.get('matchers', {})
        conditions = []

        # Filtro por exporter_type (múltiplos valores aceitos)
        exporter_field = matchers.get('exporter_type_field', 'exporter_type')
        exporter_values = matchers.get('exporter_type_values', [])

        if exporter_values:
            conditions.append({
                'field': f'Meta.{exporter_field}',
                'operator': 'in',
                'values': exporter_values
            })

        # Filtro por module (múltiplos valores aceitos, incluindo null)
        module_field = matchers.get('module_field', 'module')
        module_values = matchers.get('module_values', [])

        if module_values:
            # Filtrar null values (significa "aceita ausência do campo")
            module_values_filtered = [v for v in module_values if v is not None]

            if module_values_filtered:
                conditions.append({
                    'field': f'Meta.{module_field}',
                    'operator': 'in',
                    'values': module_values_filtered
                })

        # Filtros adicionais customizados
        for additional in matchers.get('additional_filters', []):
            conditions.append(additional)

        return {
            'operator': 'and',
            'conditions': conditions
        } if conditions else {}

    def matches_type(self, service: Dict, type_schema: Dict) -> bool:
        """
        Verifica se um serviço Consul corresponde a um tipo de monitoramento

        CRÍTICO: Use SEMPRE este método ao invés de comparações hardcoded!

        Args:
            service: Dict do serviço Consul com estrutura:
                {
                    "ID": "...",
                    "Service": "...",
                    "Meta": {
                        "exporter_type": "selfnode",  // Pode ser qualquer valor!
                        "module": "node_exporter",
                        ...
                    }
                }
            type_schema: Schema do tipo com matchers

        Returns:
            True se o serviço corresponde ao tipo, False caso contrário

        Exemplo:
            # ❌ NUNCA FAZER:
            if service['Meta']['exporter_type'] == 'node_exporter':
                ...

            # ✅ SEMPRE FAZER:
            if manager.matches_type(service, node_type_schema):
                ...
        """
        matchers = type_schema.get('matchers', {})
        service_meta = service.get('Meta', {})

        # Verificar exporter_type
        exporter_field = matchers.get('exporter_type_field', 'exporter_type')
        exporter_values = matchers.get('exporter_type_values', [])

        if exporter_values:
            service_exporter = service_meta.get(exporter_field)
            if service_exporter not in exporter_values:
                return False

        # Verificar module
        module_field = matchers.get('module_field', 'module')
        module_values = matchers.get('module_values', [])

        if module_values:
            service_module = service_meta.get(module_field)

            # Se null está nos module_values, aceita ausência do campo
            if None in module_values and service_module is None:
                pass  # OK, null é aceito
            elif service_module not in [v for v in module_values if v is not None]:
                return False

        # Verificar filtros adicionais
        for additional_filter in matchers.get('additional_filters', []):
            field = additional_filter.get('field')
            values = additional_filter.get('values', [])

            # Suporte a nested fields (ex: "Meta.custom_field")
            if '.' in field:
                parts = field.split('.')
                value = service
                for part in parts:
                    value = value.get(part, {})
                    if value == {}:
                        return False
            else:
                value = service_meta.get(field)

            if value not in values:
                return False

        return True

    def _validate_basic_schema(self, schema: Dict) -> bool:
        """
        Validação básica de schema (campos obrigatórios)

        Args:
            schema: Dict do schema

        Returns:
            True se válido, False caso contrário
        """
        required_fields = ['schema_version', 'category', 'display_name', 'types']

        for field in required_fields:
            if field not in schema:
                logger.error(f"Missing required field: {field}")
                return False

        # Validar que types é array
        if not isinstance(schema['types'], list):
            logger.error("Field 'types' must be an array")
            return False

        # Validar cada tipo
        for type_def in schema['types']:
            if 'id' not in type_def or 'display_name' not in type_def:
                logger.error(f"Invalid type definition: missing id or display_name")
                return False

        return True


# Singleton instance (modo file-based)
_manager_instance: Optional[MonitoringTypeManager] = None


def get_monitoring_type_manager() -> MonitoringTypeManager:
    """
    Retorna instância singleton do MonitoringTypeManager

    Returns:
        MonitoringTypeManager instance
    """
    global _manager_instance

    if _manager_instance is None:
        _manager_instance = MonitoringTypeManager(use_local_files=True)

    return _manager_instance
