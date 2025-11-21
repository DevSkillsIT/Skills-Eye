"""
Categorization Rule Engine - Motor de Regras Baseado em JSON

RESPONSABILIDADES:
- Carregar regras do Consul KV (ÚNICA FONTE DE VERDADE)
- Aplicar regras em ordem de prioridade
- Categorizar jobs Prometheus automaticamente
- Suportar regex patterns para job_name e módulos

✅ SPEC-ARCH-001: REMOVIDO BUILTIN_RULES
   O KV é a ÚNICA fonte de verdade. Quando KV está vazio, o sistema
   retorna apenas default_category para forçar configuração correta.

AUTOR: Sistema de Refatoração Skills Eye v2.0
DATA: 2025-11-13
"""

import re
from typing import Dict, List, Optional, Any
import logging

logger = logging.getLogger(__name__)


class CategorizationRule:
    """
    Uma regra de categorização individual

    Cada regra tem:
    - ID único
    - Prioridade (maior = aplicada primeiro)
    - Categoria de destino
    - Condições (job_name_pattern, metrics_path, module_pattern)

    Exemplo de regra JSON:
        ```json
        {
            "id": "blackbox_icmp",
            "priority": 100,
            "category": "network-probes",
            "display_name": "ICMP (Ping)",
            "conditions": {
                "job_name_pattern": "^(icmp|ping).*",
                "metrics_path": "/probe",
                "module_pattern": "^(icmp|ping)$"
            }
        }
        ```
    """

    def __init__(self, rule_data: Dict):
        """
        Inicializa regra a partir de dados JSON

        Args:
            rule_data: Dicionário com dados da regra
        """
        self.id = rule_data['id']
        self.priority = rule_data.get('priority', 50)
        self.category = rule_data['category']
        self.display_name = rule_data.get('display_name', '')
        self.exporter_type = rule_data.get('exporter_type', '')
        self.conditions = rule_data['conditions']
        # ✅ SPEC-ARCH-001: form_schema REMOVIDO
        # form_schema existe APENAS em monitoring-types, não nas regras de categorização

        # Pre-compilar regexes para performance
        # Compilar apenas uma vez no init, reutilizar no matches()
        self._compiled_patterns = {}
        for key, pattern in self.conditions.items():
            if key.endswith('_pattern'):
                try:
                    self._compiled_patterns[key] = re.compile(pattern, re.IGNORECASE)
                except re.error as e:
                    logger.error(f"[RULE {self.id}] Regex inválida em {key}: {e}")

    def matches(self, job_data: Dict) -> bool:
        """
        Verifica se job satisfaz TODAS as condições da regra (lógica AND)

        Args:
            job_data: Dados do job a verificar:
                {
                    'job_name': 'icmp',
                    'metrics_path': '/probe',
                    'module': 'icmp'  # opcional
                }

        Returns:
            True se job satisfaz todas as condições
        """
        job_name = job_data.get('job_name', '').lower()
        metrics_path = job_data.get('metrics_path', '/metrics')
        module = job_data.get('module', '')

        # Verificar job_name_pattern (regex) - OPCIONAL
        # Só aplicar se a regra especificar esta condição
        if 'job_name_pattern' in self.conditions:
            pattern = self._compiled_patterns.get('job_name_pattern')
            if pattern and not pattern.match(job_name):
                # EXCETO: Se houver module_pattern E module bater, ignorar job_name_pattern
                # Isso permite jobs genéricos "blackbox" serem categorizados pelo module
                if 'module_pattern' in self.conditions and module:
                    module_pattern = self._compiled_patterns.get('module_pattern')
                    if not (module_pattern and module_pattern.match(module)):
                        return False
                else:
                    return False

        # Verificar metrics_path (match exato) - OBRIGATÓRIO se especificado
        if 'metrics_path' in self.conditions:
            if metrics_path != self.conditions['metrics_path']:
                return False

        # Verificar module_pattern (regex) - OPCIONAL
        # Só aplicar se module estiver presente no job_data
        # Se job não tem module, ignorar esta condição
        if 'module_pattern' in self.conditions and module:
            pattern = self._compiled_patterns.get('module_pattern')
            if pattern and not pattern.match(module):
                return False

        # Todas as condições satisfeitas
        return True


class CategorizationRuleEngine:
    """
    Motor de regras para categorização de jobs Prometheus

    Features:
    - Carrega regras do Consul KV (JSON)
    - Aplica regras em ordem de prioridade (maior primeiro)
    - Suporta regex patterns
    - Categoria padrão para jobs não categorizados
    - Fallback para categorização hardcoded se KV vazio

    Exemplo de Uso:
        ```python
        from core.consul_kv_config_manager import ConsulKVConfigManager

        config_manager = ConsulKVConfigManager()
        engine = CategorizationRuleEngine(config_manager)

        # Carregar regras do KV
        await engine.load_rules()

        # Categorizar job
        category, type_info = engine.categorize({
            'job_name': 'icmp',
            'metrics_path': '/probe',
            'module': 'icmp'
        })

        # Retorna: ('network-probes', {'display_name': 'ICMP (Ping)', ...})
        ```

    Estrutura JSON no KV (skills/eye/monitoring-types/categorization/rules):
        ```json
        {
            "version": "1.0.0",
            "last_updated": "2025-11-13T10:00:00",
            "total_rules": 50,
            "rules": [
                {
                    "id": "blackbox_icmp",
                    "priority": 100,
                    "category": "network-probes",
                    "display_name": "ICMP (Ping)",
                    "exporter_type": "blackbox",
                    "conditions": {
                        "job_name_pattern": "^(icmp|ping).*",
                        "metrics_path": "/probe",
                        "module_pattern": "^(icmp|ping)$"
                    }
                },
                ...
            ],
            "default_category": "custom-exporters"
        }
        ```
    """

    def __init__(self, config_manager):
        """
        Inicializa engine

        Args:
            config_manager: Instância de ConsulKVConfigManager
        """
        self.config_manager = config_manager
        self.rules: List[CategorizationRule] = []
        self.default_category = 'custom-exporters'
        self.rules_loaded = False
        # ✅ SPEC-ARCH-001: REMOVIDO _using_builtin - KV é única fonte de verdade

    async def load_rules(self, force_reload: bool = False) -> bool:
        """
        Carrega regras do Consul KV (ÚNICA FONTE DE VERDADE)

        ✅ SPEC-ARCH-001: KV é a única fonte de verdade para regras.
           Quando KV está vazio, retorna False para forçar configuração correta.
           O sistema usará apenas default_category até que as regras sejam populadas.

        Fluxo:
        1. Busca JSON do KV: skills/eye/monitoring-types/categorization/rules
        2. Se KV vazio: Retorna False e loga warning
        3. Cria objetos CategorizationRule para cada regra
        4. Ordena por prioridade (maior primeiro)
        5. Armazena categoria padrão

        Args:
            force_reload: Se True, recarrega mesmo se já carregado

        Returns:
            True se carregou com sucesso do KV, False se KV vazio
        """
        # Se já carregou e não é force_reload, skip
        if self.rules_loaded and not force_reload:
            logger.debug("[RULES] Regras já carregadas, usando cache")
            return True

        try:
            # Buscar regras do KV
            rules_data = await self.config_manager.get(
                'monitoring-types/categorization/rules',
                use_cache=not force_reload
            )

            # ✅ SPEC-ARCH-001: Se KV vazio, retornar False (não usar fallback)
            if not rules_data:
                logger.warning(
                    "[RULES] ⚠️ KV vazio - nenhuma regra carregada. "
                    "Execute migrate_categorization_to_json.py para popular KV. "
                    "Sistema usará apenas default_category para categorização."
                )
                self.rules = []
                self.rules_loaded = False
                return False

            # Criar objetos de regra
            self.rules = []
            for rule_data in rules_data.get('rules', []):
                try:
                    rule = CategorizationRule(rule_data)
                    self.rules.append(rule)
                except Exception as e:
                    logger.error(f"[RULES] Erro ao criar regra {rule_data.get('id', '?')}: {e}")
                    continue

            # Ordenar por prioridade (maior primeiro)
            self.rules.sort(key=lambda r: r.priority, reverse=True)

            # Categoria padrão
            self.default_category = rules_data.get('default_category', 'custom-exporters')

            self.rules_loaded = True

            logger.info(
                f"[RULES] ✅ {len(self.rules)} regras carregadas do KV "
                f"(default_category: {self.default_category})"
            )
            return True

        except Exception as e:
            logger.error(f"[RULES] ❌ Erro ao carregar regras do KV: {e}", exc_info=True)
            self.rules = []
            self.rules_loaded = False
            return False

    def categorize(self, job_data: Dict) -> tuple:
        """
        Categoriza um job baseado nas regras

        Aplica regras em ordem de prioridade até encontrar match.
        Se nenhuma regra aplicar, usa categoria padrão.

        Args:
            job_data: Dados do job:
                {
                    'job_name': 'icmp',
                    'metrics_path': '/probe',
                    'module': 'icmp',  # opcional (ou em relabel_configs)
                    'relabel_configs': [...]  # opcional
                }

        Returns:
            Tupla (categoria, type_info):
                - categoria: string ('network-probes', 'system-exporters', etc)
                - type_info: dict com display_name, exporter_type, module, id

        Exemplo:
            ```python
            category, type_info = engine.categorize({
                'job_name': 'icmp',
                'metrics_path': '/probe',
                'module': 'icmp'
            })

            # Retorna:
            # ('network-probes', {
            #     'id': 'icmp',
            #     'display_name': 'ICMP (Ping)',
            #     'exporter_type': 'blackbox',
            #     'module': 'icmp'
            # })
            ```
        """
        # Extrair module de relabel_configs se não estiver presente
        if 'module' not in job_data and 'relabel_configs' in job_data:
            for config in job_data.get('relabel_configs', []):
                if config.get('target_label') == '__param_module':
                    job_data['module'] = config.get('replacement', '')
                    break
        
        # Se não tem regras carregadas, usar categoria padrão
        if not self.rules:
            logger.debug(
                f"[CATEGORIZE] Sem regras carregadas, usando categoria padrão: {self.default_category}"
            )
            return self._default_categorize(job_data)

        # Aplicar regras em ordem de prioridade
        for rule in self.rules:
            if rule.matches(job_data):
                logger.debug(
                    f"[CATEGORIZE] '{job_data.get('job_name')}' → "
                    f"'{rule.category}' (regra: {rule.id}, prioridade: {rule.priority})"
                )

                # SPEC-REGEX-001: Determinar quais patterns fizeram match
                job_name = job_data.get('job_name', '').lower()
                module = job_data.get('module', '')

                job_pattern_matched = False
                module_pattern_matched = False

                # Verificar job_name_pattern
                if 'job_name_pattern' in rule.conditions:
                    pattern = rule._compiled_patterns.get('job_name_pattern')
                    if pattern and pattern.match(job_name):
                        job_pattern_matched = True

                # Verificar module_pattern
                if 'module_pattern' in rule.conditions and module:
                    pattern = rule._compiled_patterns.get('module_pattern')
                    if pattern and pattern.match(module):
                        module_pattern_matched = True

                type_info = {
                    'id': job_data.get('module') or job_data.get('job_name'),
                    'display_name': rule.display_name or self._format_display_name(job_data.get('job_name', '')),
                    'exporter_type': rule.exporter_type or 'custom',
                    'priority': rule.priority,
                    # SPEC-REGEX-001: Informacao detalhada do match
                    'matched_rule': {
                        'id': rule.id,
                        'priority': rule.priority,
                        'job_pattern_matched': job_pattern_matched,
                        'module_pattern_matched': module_pattern_matched,
                        'job_pattern': rule.conditions.get('job_name_pattern'),
                        'module_pattern': rule.conditions.get('module_pattern')
                    }
                }

                # Adicionar module se presente
                if job_data.get('module'):
                    type_info['module'] = job_data['module']

                return rule.category, type_info

        # Nenhuma regra aplicou - usar categoria padrão
        logger.debug(
            f"[CATEGORIZE] '{job_data.get('job_name')}' → "
            f"'{self.default_category}' (nenhuma regra aplicou)"
        )
        return self._default_categorize(job_data)

    def _default_categorize(self, job_data: Dict) -> tuple:
        """
        Categorização padrão quando nenhuma regra aplica

        Args:
            job_data: Dados do job

        Returns:
            Tupla (categoria, type_info)
        """
        job_name = job_data.get('job_name', 'unknown')

        type_info = {
            'id': job_data.get('module') or job_name,
            'display_name': self._format_display_name(job_name),
            'exporter_type': 'custom',
            # SPEC-REGEX-001: matched_rule nulo para categoria padrão
            'matched_rule': None
        }

        if job_data.get('module'):
            type_info['module'] = job_data['module']

        return self.default_category, type_info

    def _format_display_name(self, name: str) -> str:
        """
        Formata nome para exibição

        ✅ SPEC-ARCH-001: REMOVIDO mapeamento hardcoded.
           Display names devem vir das regras no KV.
           Esta função apenas formata o nome técnico para formato amigável.

        Args:
            name: Nome técnico (ex: 'icmp', 'node_exporter')

        Returns:
            Nome formatado usando capitalização (ex: 'Icmp', 'Node Exporter')
        """
        # ✅ SPEC-ARCH-001: Apenas capitalizar, sem mapeamento hardcoded
        # Display names específicos devem estar nas regras do KV
        return name.replace('-', ' ').replace('_', ' ').title()

    def get_rules_summary(self) -> Dict[str, Any]:
        """
        Retorna resumo das regras carregadas

        Returns:
            Dicionário com estatísticas das regras
        """
        categories = {}
        for rule in self.rules:
            categories[rule.category] = categories.get(rule.category, 0) + 1

        return {
            "total_rules": len(self.rules),
            "rules_loaded": self.rules_loaded,
            "default_category": self.default_category,
            "source": "consul_kv",  # ✅ SPEC-ARCH-001: KV é única fonte de verdade
            "categories": categories,
            "priority_range": {
                "min": min([r.priority for r in self.rules]) if self.rules else None,
                "max": max([r.priority for r in self.rules]) if self.rules else None
            }
        }

    def get_rules_by_category(self, category: str) -> List[Dict[str, Any]]:
        """
        Retorna todas as regras de uma categoria específica

        Args:
            category: Nome da categoria (ex: 'network-probes')

        Returns:
            Lista de dicionários com dados das regras da categoria
        """
        matching_rules = []

        for rule in self.rules:
            if rule.category == category:
                matching_rules.append({
                    'id': rule.id,
                    'priority': rule.priority,
                    'category': rule.category,
                    'display_name': rule.display_name,
                    'exporter_type': rule.exporter_type,
                    'conditions': rule.conditions
                })

        return matching_rules
