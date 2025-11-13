"""
Dynamic Query Builder - Construtor de Queries PromQL com Jinja2

RESPONSABILIDADES:
- Renderizar templates Jinja2 de queries PromQL
- Suportar variáveis dinâmicas (modules, jobs, labels)
- Cache de templates compilados
- Templates predefinidos para casos comuns

AUTOR: Sistema de Refatoração Skills Eye v2.0
DATA: 2025-11-13

DEPENDÊNCIA EXTERNA:
- Jinja2 (adicionar ao requirements.txt se não existir)
"""

from jinja2 import Environment, Template, TemplateError
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class DynamicQueryBuilder:
    """
    Construtor de queries PromQL dinâmicas usando Jinja2

    Features:
    - Templates reutilizáveis com variáveis
    - Lógica condicional (if/else)
    - Loops (for)
    - Filtros customizados (join, default, etc)
    - Cache de templates compilados
    - Auto-escape desabilitado (PromQL não precisa)

    Exemplo de Uso:
        ```python
        builder = DynamicQueryBuilder()

        # Template com variáveis
        template = '''
        probe_success{
            job="blackbox",
            __param_module=~"{{ modules|join('|') }}"
            {% if company %},company="{{ company }}"{% endif %}
            {% if site %},site="{{ site }}"{% endif %}
        }
        '''

        query = builder.build(template, {
            'modules': ['icmp', 'tcp'],
            'company': 'ACME',
            'site': 'palmas'
        })

        # Resultado:
        # probe_success{job="blackbox",__param_module=~"icmp|tcp",company="ACME",site="palmas"}
        ```

    Templates Predefinidos (ver QUERY_TEMPLATES no final):
    - network_probe_success: Success rate de probes de rede
    - network_probe_duration: Latência de probes
    - node_cpu_usage: Uso de CPU do Node Exporter
    - node_memory_usage: Uso de memória do Node Exporter
    - database_up: Status up de database exporters
    """

    def __init__(self):
        """
        Inicializa o builder com Environment Jinja2 customizado
        """
        self.env = Environment(
            trim_blocks=True,          # Remove newlines após blocos
            lstrip_blocks=True,        # Remove espaços antes de blocos
            autoescape=False           # PromQL não precisa de escape
        )

        # Cache de templates compilados (key: template_str, value: Template)
        self._template_cache: Dict[str, Template] = {}

    def build(self, template_str: str, params: Dict[str, Any]) -> str:
        """
        Constrói query PromQL a partir de template Jinja2

        Fluxo:
        1. Busca template no cache (se já foi compilado)
        2. Se não está no cache, compila e armazena
        3. Renderiza template com parâmetros fornecidos
        4. Limpa espaços extras
        5. Retorna query PromQL final

        Args:
            template_str: Template Jinja2 (string)
            params: Dicionário com parâmetros para substituição

        Returns:
            Query PromQL renderizada (string)

        Raises:
            TemplateError: Se template inválido ou erro de renderização

        Exemplo:
            ```python
            template = 'up{job=~"{{ jobs|join("|") }}"}'
            query = builder.build(template, {'jobs': ['node', 'mysql']})
            # Retorna: 'up{job=~"node|mysql"}'
            ```
        """
        try:
            # PASSO 1: Buscar template no cache
            if template_str not in self._template_cache:
                # Cache miss - compilar template
                self._template_cache[template_str] = self.env.from_string(template_str)
                logger.debug(f"[QUERY BUILDER] Template compilado e adicionado ao cache")

            template = self._template_cache[template_str]

            # PASSO 2: Renderizar com parâmetros
            query = template.render(**params)

            # PASSO 3: Limpar espaços extras (múltiplos espaços → um espaço)
            # Mantém legibilidade mas remove formatação desnecessária
            query = ' '.join(query.split())

            logger.debug(f"[QUERY BUILDER] Query renderizada: {query[:100]}{'...' if len(query) > 100 else ''}")
            return query

        except TemplateError as e:
            logger.error(f"[QUERY BUILDER ERROR] Template inválido: {e}")
            raise
        except Exception as e:
            logger.error(f"[QUERY BUILDER ERROR] Erro inesperado: {e}", exc_info=True)
            raise

    def clear_cache(self) -> None:
        """
        Limpa cache de templates compilados

        Útil para forçar recompilação de templates após mudanças.
        """
        count = len(self._template_cache)
        self._template_cache.clear()
        logger.info(f"[QUERY BUILDER] Cache limpo ({count} templates removidos)")

    def get_cache_stats(self) -> Dict[str, int]:
        """
        Retorna estatísticas do cache

        Returns:
            Dicionário com número de templates em cache
        """
        return {
            "cached_templates": len(self._template_cache)
        }


# ============================================================================
# TEMPLATES PREDEFINIDOS
# ============================================================================

QUERY_TEMPLATES = {
    # ========================================================================
    # NETWORK PROBES (Blackbox Exporter)
    # ========================================================================

    "network_probe_success": """
        probe_success{
            job="blackbox",
            __param_module=~"{{ modules|join('|') }}"
            {% if company %},company="{{ company }}"{% endif %}
            {% if site %},site="{{ site }}"{% endif %}
            {% if env %},env="{{ env }}"{% endif %}
        }
    """,

    "network_probe_duration": """
        probe_duration_seconds{
            job="blackbox",
            __param_module=~"{{ modules|join('|') }}"
            {% if company %},company="{{ company }}"{% endif %}
            {% if site %},site="{{ site }}"{% endif %}
        }
    """,

    "network_probe_http_status": """
        probe_http_status_code{
            job="blackbox",
            __param_module=~"{{ modules|join('|') }}"
            {% if company %},company="{{ company }}"{% endif %}
        }
    """,

    # ========================================================================
    # WEB PROBES (HTTP/HTTPS)
    # ========================================================================

    "web_probe_success": """
        probe_success{
            job="blackbox",
            __param_module=~"{{ modules|join('|') }}"
            {% if company %},company="{{ company }}"{% endif %}
        }
    """,

    "web_probe_ssl_expiry": """
        probe_ssl_earliest_cert_expiry{
            job="blackbox",
            __param_module=~"{{ modules|join('|') }}"
            {% if company %},company="{{ company }}"{% endif %}
        } - time()
    """,

    # ========================================================================
    # SYSTEM EXPORTERS (Node/Windows)
    # ========================================================================

    "node_cpu_usage": """
        100 - (avg by (instance) (
            rate(node_cpu_seconds_total{
                job=~"{{ jobs|join('|') }}",
                mode="idle"
            }[{{ time_range|default("5m") }}])
        ) * 100)
    """,

    "node_memory_usage": """
        (1 - (
            node_memory_MemAvailable_bytes{job=~"{{ jobs|join('|') }}"} /
            node_memory_MemTotal_bytes{job=~"{{ jobs|join('|') }}"}
        )) * 100
    """,

    "node_disk_usage": """
        100 - (
            node_filesystem_avail_bytes{
                job=~"{{ jobs|join('|') }}",
                mountpoint="{{ mountpoint|default("/") }}"
            } /
            node_filesystem_size_bytes{
                job=~"{{ jobs|join('|') }}",
                mountpoint="{{ mountpoint|default("/") }}"
            }
        ) * 100
    """,

    "node_load_average": """
        node_load1{job=~"{{ jobs|join('|') }}"}
    """,

    # ========================================================================
    # DATABASE EXPORTERS
    # ========================================================================

    "database_up": """
        up{
            job=~"{{ jobs|join('|') }}"
            {% if company %},company="{{ company }}"{% endif %}
            {% if site %},site="{{ site }}"{% endif %}
        }
    """,

    "mysql_connections": """
        mysql_global_status_threads_connected{
            job=~"{{ jobs|join('|') }}"
            {% if company %},company="{{ company }}"{% endif %}
        }
    """,

    "mysql_queries_per_second": """
        rate(mysql_global_status_queries{
            job=~"{{ jobs|join('|') }}"
        }[{{ time_range|default("5m") }}])
    """,

    "postgres_connections": """
        pg_stat_database_numbackends{
            job=~"{{ jobs|join('|') }}",
            datname!="template0"
        }
    """,

    "redis_connected_clients": """
        redis_connected_clients{
            job=~"{{ jobs|join('|') }}"
        }
    """,

    # ========================================================================
    # GENERIC / MULTI-PURPOSE
    # ========================================================================

    "exporter_up": """
        up{
            job=~"{{ jobs|join('|') }}"
            {% if company %},company="{{ company }}"{% endif %}
            {% if site %},site="{{ site }}"{% endif %}
            {% if env %},env="{{ env }}"{% endif %}
        }
    """,

    "exporter_scrape_duration": """
        scrape_duration_seconds{
            job=~"{{ jobs|join('|') }}"
        }
    """,

    # ========================================================================
    # AGGREGATIONS / COUNTS
    # ========================================================================

    "count_by_status": """
        sum by ({{ group_by|default("instance") }}) (
            {{ metric }}{
                job=~"{{ jobs|join('|') }}"
                {% if filters %}
                {% for key, value in filters.items() %},{{ key }}="{{ value }}"{% endfor %}
                {% endif %}
            }
        )
    """,
}


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def build_simple_query(metric: str, job: str, labels: Optional[Dict[str, str]] = None) -> str:
    """
    Helper para construir queries PromQL simples sem template

    Args:
        metric: Nome da métrica (ex: 'up', 'probe_success')
        job: Nome do job (ex: 'blackbox', 'node')
        labels: Labels adicionais opcionais

    Returns:
        Query PromQL simples

    Exemplo:
        ```python
        query = build_simple_query('up', 'blackbox', {'company': 'ACME'})
        # Retorna: up{job="blackbox",company="ACME"}
        ```
    """
    label_parts = [f'job="{job}"']

    if labels:
        for key, value in labels.items():
            label_parts.append(f'{key}="{value}"')

    labels_str = ','.join(label_parts)
    return f"{metric}{{{labels_str}}}"


def build_regex_job_query(metric: str, jobs: list, labels: Optional[Dict[str, str]] = None) -> str:
    """
    Helper para construir queries com múltiplos jobs (regex OR)

    Args:
        metric: Nome da métrica
        jobs: Lista de jobs
        labels: Labels adicionais

    Returns:
        Query PromQL com job regex

    Exemplo:
        ```python
        query = build_regex_job_query('up', ['node', 'mysql', 'redis'])
        # Retorna: up{job=~"node|mysql|redis"}
        ```
    """
    jobs_regex = '|'.join(jobs)
    label_parts = [f'job=~"{jobs_regex}"']

    if labels:
        for key, value in labels.items():
            label_parts.append(f'{key}="{value}"')

    labels_str = ','.join(label_parts)
    return f"{metric}{{{labels_str}}}"
