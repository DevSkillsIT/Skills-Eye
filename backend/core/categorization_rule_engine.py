"""
Categorization Rule Engine - Motor de Regras Baseado em JSON

RESPONSABILIDADES:
- Carregar regras do Consul KV
- Aplicar regras em ordem de prioridade
- Categorizar jobs Prometheus automaticamente
- Suportar regex patterns para job_name e módulos
- Usar fallback hardcoded quando KV está vazio/indisponível

AUTOR: Sistema de Refatoração Skills Eye v2.0
DATA: 2025-11-13
"""

import re
from typing import Dict, List, Optional, Any
import logging

logger = logging.getLogger(__name__)


# =============================================================================
# BUILTIN_RULES: Regras padrão usadas quando KV está vazio ou indisponível
# =============================================================================
# Estas regras garantem categorização mínima mesmo sem acesso ao Consul KV.
# Cobrem os tipos mais comuns do ecossistema Prometheus/Blackbox.
# Quando KV está disponível, essas regras são IGNORADAS em favor do KV.
# =============================================================================

BUILTIN_RULES = {
    "version": "builtin-1.0.0",
    "last_updated": "2025-11-21",
    "description": "Regras builtin para fallback quando KV indisponível",
    "default_category": "custom-exporters",
    "rules": [
        # Probes de Rede (Blackbox)
        {
            "id": "builtin_icmp",
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
        {
            "id": "builtin_tcp",
            "priority": 100,
            "category": "network-probes",
            "display_name": "TCP Connect",
            "exporter_type": "blackbox",
            "conditions": {
                "job_name_pattern": "^tcp.*",
                "metrics_path": "/probe",
                "module_pattern": "^tcp"
            }
        },
        {
            "id": "builtin_dns",
            "priority": 100,
            "category": "network-probes",
            "display_name": "DNS Query",
            "exporter_type": "blackbox",
            "conditions": {
                "job_name_pattern": "^dns.*",
                "metrics_path": "/probe",
                "module_pattern": "^dns"
            }
        },
        # Probes Web (Blackbox)
        {
            "id": "builtin_http_2xx",
            "priority": 100,
            "category": "web-probes",
            "display_name": "HTTP 2xx",
            "exporter_type": "blackbox",
            "conditions": {
                "job_name_pattern": "^http.*2xx.*",
                "metrics_path": "/probe",
                "module_pattern": "^http.*2xx"
            }
        },
        {
            "id": "builtin_https",
            "priority": 100,
            "category": "web-probes",
            "display_name": "HTTPS",
            "exporter_type": "blackbox",
            "conditions": {
                "job_name_pattern": "^https.*",
                "metrics_path": "/probe",
                "module_pattern": "^https"
            }
        },
        # Exporters de Sistema
        {
            "id": "builtin_node_exporter",
            "priority": 90,
            "category": "system-exporters",
            "display_name": "Node Exporter",
            "exporter_type": "node",
            "conditions": {
                "job_name_pattern": "^node.*exporter.*",
                "metrics_path": "/metrics"
            }
        },
        {
            "id": "builtin_windows_exporter",
            "priority": 90,
            "category": "system-exporters",
            "display_name": "Windows Exporter",
            "exporter_type": "windows",
            "conditions": {
                "job_name_pattern": "^windows.*exporter.*",
                "metrics_path": "/metrics"
            }
        },
        # Exporters de Banco de Dados
        {
            "id": "builtin_mysql_exporter",
            "priority": 85,
            "category": "database-exporters",
            "display_name": "MySQL Exporter",
            "exporter_type": "mysql",
            "conditions": {
                "job_name_pattern": "^mysql.*exporter.*",
                "metrics_path": "/metrics"
            }
        },
        {
            "id": "builtin_postgres_exporter",
            "priority": 85,
            "category": "database-exporters",
            "display_name": "PostgreSQL Exporter",
            "exporter_type": "postgres",
            "conditions": {
                "job_name_pattern": "^postgres.*exporter.*",
                "metrics_path": "/metrics"
            }
        },
        # Exporters de Infraestrutura
        {
            "id": "builtin_snmp_exporter",
            "priority": 80,
            "category": "infrastructure-exporters",
            "display_name": "SNMP Exporter",
            "exporter_type": "snmp",
            "conditions": {
                "job_name_pattern": "^snmp.*",
                "metrics_path": "/snmp"
            }
        },
    ]
}


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
        self._using_builtin = False  # Flag para indicar se está usando BUILTIN_RULES como fallback

    async def load_rules(self, force_reload: bool = False) -> bool:
        """
        Carrega regras do Consul KV ou usa fallback builtin

        Fluxo:
        1. Busca JSON do KV: skills/eye/monitoring-types/categorization/rules
        2. Se KV vazio/indisponível: Usa BUILTIN_RULES como fallback
        3. Cria objetos CategorizationRule para cada regra
        4. Ordena por prioridade (maior primeiro)
        5. Armazena categoria padrão

        Args:
            force_reload: Se True, recarrega mesmo se já carregado

        Returns:
            True se carregou com sucesso (KV ou fallback)

        Raises:
            Não lança exceção - retorna True mesmo com fallback
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

            # Se KV vazio, usar fallback builtin
            if not rules_data:
                logger.warning(
                    "[RULES] KV vazio - usando BUILTIN_RULES como fallback. "
                    "Execute migrate_categorization_to_json.py para popular KV."
                )
                rules_data = BUILTIN_RULES
                self._using_builtin = True
            else:
                self._using_builtin = False

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

            source = "BUILTIN" if self._using_builtin else "KV"
            logger.info(
                f"[RULES] {len(self.rules)} regras carregadas de {source} "
                f"(default_category: {self.default_category})"
            )
            return True

        except Exception as e:
            # Em caso de erro, tentar usar builtin como fallback de emergência
            logger.error(f"[RULES] Erro ao carregar regras do KV: {e}")
            logger.warning("[RULES] Usando BUILTIN_RULES como fallback de emergência")

            try:
                self.rules = []
                for rule_data in BUILTIN_RULES.get('rules', []):
                    try:
                        rule = CategorizationRule(rule_data)
                        self.rules.append(rule)
                    except Exception as rule_error:
                        logger.error(f"[RULES] Erro ao criar regra builtin {rule_data.get('id', '?')}: {rule_error}")
                        continue

                self.rules.sort(key=lambda r: r.priority, reverse=True)
                self.default_category = BUILTIN_RULES.get('default_category', 'custom-exporters')
                self.rules_loaded = True
                self._using_builtin = True

                logger.info(f"[RULES] {len(self.rules)} regras BUILTIN carregadas como fallback de emergência")
                return True
            except Exception as fallback_error:
                logger.error(f"[RULES] Falha crítica ao carregar BUILTIN: {fallback_error}", exc_info=True)
                self.rules = []
                self.rules_loaded = False
                self._using_builtin = False
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

                type_info = {
                    'id': job_data.get('module') or job_data.get('job_name'),
                    'display_name': rule.display_name or self._format_display_name(job_data.get('job_name', '')),
                    'exporter_type': rule.exporter_type or 'custom',
                    'priority': rule.priority
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
            'exporter_type': 'custom'
        }

        if job_data.get('module'):
            type_info['module'] = job_data['module']

        return self.default_category, type_info

    def _format_display_name(self, name: str) -> str:
        """
        Formata nome para exibição

        Args:
            name: Nome técnico (ex: 'icmp', 'node_exporter')

        Returns:
            Nome formatado (ex: 'ICMP', 'Node Exporter')
        """
        # Mapeamento de nomes conhecidos
        mapping = {
            'icmp': 'ICMP (Ping)',
            'ping': 'ICMP (Ping)',
            'tcp': 'TCP Connect',
            'tcp_connect': 'TCP Connect',
            'dns': 'DNS Query',
            'ssh': 'SSH Banner',
            'ssh_banner': 'SSH Banner',
            'http_2xx': 'HTTP 2xx',
            'http_4xx': 'HTTP 4xx',
            'http_5xx': 'HTTP 5xx',
            'https': 'HTTPS',
            'http_post_2xx': 'HTTP POST 2xx',
        }

        name_lower = name.lower()
        if name_lower in mapping:
            return mapping[name_lower]

        # Fallback: capitalizar e substituir separadores
        return name.replace('-', ' ').replace('_', ' ').title()

    def get_rules_summary(self) -> Dict[str, Any]:
        """
        Retorna resumo das regras carregadas

        Returns:
            Dicionário com estatísticas das regras (incluindo fonte: builtin vs consul_kv)
        """
        categories = {}
        for rule in self.rules:
            categories[rule.category] = categories.get(rule.category, 0) + 1

        return {
            "total_rules": len(self.rules),
            "rules_loaded": self.rules_loaded,
            "default_category": self.default_category,
            "source": "builtin" if self._using_builtin else "consul_kv",  # Indica fonte das regras
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
