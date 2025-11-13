"""
Testes Unitários: DynamicQueryBuilder

OBJETIVO:
- Validar renderização de templates Jinja2
- Validar cache de templates compilados
- Validar templates predefinidos
- Validar helpers (build_simple_query, build_regex_job_query)

AUTOR: Sistema de Refatoração Skills Eye v2.0
DATA: 2025-11-13
"""

import pytest
from jinja2 import TemplateError

from core.dynamic_query_builder import (
    DynamicQueryBuilder,
    QUERY_TEMPLATES,
    build_simple_query,
    build_regex_job_query
)


# ============================================================================
# TESTES DE DYNAMIC QUERY BUILDER
# ============================================================================

class TestDynamicQueryBuilder:
    """Testes do construtor de queries PromQL"""

    @pytest.fixture
    def builder(self):
        """Fixture que cria um builder para cada teste"""
        return DynamicQueryBuilder()

    def test_initialization(self, builder):
        """Testa inicialização do builder"""
        assert builder.env is not None
        assert builder._template_cache == {}

    def test_build_simple_template(self, builder):
        """Testa renderização de template simples"""
        template = 'up{job="{{ job }}"}'
        params = {'job': 'blackbox'}

        query = builder.build(template, params)

        assert query == 'up{job="blackbox"}'

    def test_build_with_list_join(self, builder):
        """Testa template com join de lista"""
        template = 'up{job=~"{{ jobs|join(\'|\') }}"}'
        params = {'jobs': ['node', 'mysql', 'redis']}

        query = builder.build(template, params)

        assert query == 'up{job=~"node|mysql|redis"}'

    def test_build_with_conditionals(self, builder):
        """Testa template com condicionais"""
        template = '''
        up{
            job="blackbox"
            {% if company %},company="{{ company }}"{% endif %}
            {% if site %},site="{{ site }}"{% endif %}
        }
        '''

        # Com company e site
        query1 = builder.build(template, {'company': 'ACME', 'site': 'palmas'})
        assert 'company="ACME"' in query1
        assert 'site="palmas"' in query1

        # Sem filtros
        query2 = builder.build(template, {})
        assert 'company' not in query2
        assert 'site' not in query2

    def test_build_caches_template(self, builder):
        """Testa que template é cacheado após compilação"""
        template = 'up{job="{{ job }}"}'

        # Primeira renderização
        builder.build(template, {'job': 'node'})
        assert template in builder._template_cache

        # Segunda renderização (deve usar cache)
        builder.build(template, {'job': 'mysql'})
        assert len(builder._template_cache) == 1

    def test_clear_cache(self, builder):
        """Testa limpeza do cache"""
        # Compilar alguns templates
        builder.build('up{job="{{ job }}"}', {'job': 'node'})
        builder.build('probe_success{job="{{ job }}"}', {'job': 'blackbox'})

        assert len(builder._template_cache) == 2

        # Limpar cache
        builder.clear_cache()

        assert len(builder._template_cache) == 0

    def test_get_cache_stats(self, builder):
        """Testa estatísticas do cache"""
        # Cache vazio
        stats = builder.get_cache_stats()
        assert stats["cached_templates"] == 0

        # Compilar templates
        builder.build('template1', {})
        builder.build('template2', {})

        stats = builder.get_cache_stats()
        assert stats["cached_templates"] == 2

    def test_build_invalid_template(self, builder):
        """Testa erro com template inválido"""
        template = 'up{job="{{ unclosed }'  # Template malformado

        with pytest.raises(TemplateError):
            builder.build(template, {})

    def test_build_removes_extra_spaces(self, builder):
        """Testa que espaços extras são removidos"""
        template = '''
        up{
            job="blackbox",
            instance="{{ instance }}"
        }
        '''
        params = {'instance': '10.0.0.1'}

        query = builder.build(template, params)

        # Não deve ter múltiplos espaços
        assert '  ' not in query
        assert '\n' not in query


# ============================================================================
# TESTES DE TEMPLATES PREDEFINIDOS
# ============================================================================

class TestQueryTemplates:
    """Testes dos templates predefinidos"""

    @pytest.fixture
    def builder(self):
        return DynamicQueryBuilder()

    def test_network_probe_success_template(self, builder):
        """Testa template de network probe success"""
        template = QUERY_TEMPLATES['network_probe_success']
        params = {
            'modules': ['icmp', 'tcp', 'dns'],
            'company': 'ACME',
            'site': 'palmas'
        }

        query = builder.build(template, params)

        assert 'probe_success' in query
        assert 'job="blackbox"' in query
        assert '__param_module=~"icmp|tcp|dns"' in query
        assert 'company="ACME"' in query
        assert 'site="palmas"' in query

    def test_node_cpu_usage_template(self, builder):
        """Testa template de CPU usage"""
        template = QUERY_TEMPLATES['node_cpu_usage']
        params = {
            'jobs': ['node', 'selfnode'],
            'time_range': '5m'
        }

        query = builder.build(template, params)

        assert 'node_cpu_seconds_total' in query
        assert 'mode="idle"' in query
        assert 'job=~"node|selfnode"' in query
        assert '[5m]' in query

    def test_database_up_template(self, builder):
        """Testa template de database up"""
        template = QUERY_TEMPLATES['database_up']
        params = {
            'jobs': ['mysql', 'postgres', 'redis']
        }

        query = builder.build(template, params)

        assert 'up{' in query
        assert 'job=~"mysql|postgres|redis"' in query

    def test_web_probe_ssl_expiry_template(self, builder):
        """Testa template de SSL certificate expiry"""
        template = QUERY_TEMPLATES['web_probe_ssl_expiry']
        params = {
            'modules': ['https', 'http_2xx'],
            'company': 'ACME'
        }

        query = builder.build(template, params)

        assert 'probe_ssl_earliest_cert_expiry' in query
        assert '- time()' in query  # Calcula dias restantes

    def test_mysql_connections_template(self, builder):
        """Testa template de MySQL connections"""
        template = QUERY_TEMPLATES['mysql_connections']
        params = {
            'jobs': ['mysql', 'mariadb']
        }

        query = builder.build(template, params)

        assert 'mysql_global_status_threads_connected' in query
        assert 'job=~"mysql|mariadb"' in query

    def test_template_with_default_filter(self, builder):
        """Testa template com filtro |default"""
        template = QUERY_TEMPLATES['node_disk_usage']
        params = {
            'jobs': ['node']
            # mountpoint não fornecido - deve usar default "/"
        }

        query = builder.build(template, params)

        assert 'mountpoint="/"' in query


# ============================================================================
# TESTES DE HELPER FUNCTIONS
# ============================================================================

class TestHelperFunctions:
    """Testes das funções auxiliares"""

    def test_build_simple_query(self):
        """Testa construção de query simples"""
        query = build_simple_query('up', 'blackbox', {'company': 'ACME', 'site': 'palmas'})

        assert query == 'up{job="blackbox",company="ACME",site="palmas"}'

    def test_build_simple_query_no_labels(self):
        """Testa query simples sem labels extras"""
        query = build_simple_query('up', 'node')

        assert query == 'up{job="node"}'

    def test_build_regex_job_query(self):
        """Testa query com múltiplos jobs (regex)"""
        query = build_regex_job_query('up', ['node', 'mysql', 'redis'])

        assert query == 'up{job=~"node|mysql|redis"}'

    def test_build_regex_job_query_with_labels(self):
        """Testa query regex com labels extras"""
        query = build_regex_job_query(
            'up',
            ['node', 'mysql'],
            {'company': 'ACME'}
        )

        assert 'job=~"node|mysql"' in query
        assert 'company="ACME"' in query

    def test_build_regex_job_query_single_job(self):
        """Testa query regex com apenas um job"""
        query = build_regex_job_query('up', ['blackbox'])

        assert query == 'up{job=~"blackbox"}'


# ============================================================================
# TESTES DE INTEGRAÇÃO
# ============================================================================

class TestIntegration:
    """Testes de integração completos"""

    @pytest.fixture
    def builder(self):
        return DynamicQueryBuilder()

    def test_render_all_predefined_templates(self, builder):
        """Testa que todos os templates predefinidos são renderizáveis"""
        params = {
            'modules': ['icmp', 'tcp'],
            'jobs': ['node', 'mysql'],
            'company': 'ACME',
            'site': 'palmas',
            'env': 'prod',
            'time_range': '5m',
            'mountpoint': '/',
            'metric': 'up',
            'group_by': 'instance',
            'filters': {}
        }

        errors = []
        for template_name, template_str in QUERY_TEMPLATES.items():
            try:
                query = builder.build(template_str, params)
                assert len(query) > 0
            except Exception as e:
                errors.append(f"{template_name}: {e}")

        # Não deve haver erros
        assert len(errors) == 0, f"Erros encontrados: {errors}"

    def test_cache_performance(self, builder):
        """Testa que cache melhora performance"""
        template = QUERY_TEMPLATES['network_probe_success']
        params = {'modules': ['icmp']}

        # Primeira renderização (compila template)
        import time
        start1 = time.time()
        builder.build(template, params)
        time1 = time.time() - start1

        # Segunda renderização (usa cache)
        start2 = time.time()
        builder.build(template, params)
        time2 = time.time() - start2

        # Cache deve ser mais rápido (ou igual se já estava muito rápido)
        assert time2 <= time1


# ============================================================================
# EXECUTAR TESTES
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
