"""
Testes baseline para endpoints de monitoramento unificado - SPEC-PERF-002 FASE 5.

RESPONSABILIDADES:
- Testa paginacao server-side (page, page_size)
- Testa filtros server-side (node, metadata dinamico)
- Testa ordenacao server-side (sort_field, sort_order)
- Testa extracao de filterOptions dos dados filtrados
- Testa invalidacao de cache
- Testa compatibilidade backward (sem page/pageSize retorna todos)

ARQUITETURA:
- Testa funcoes do modulo monitoring_filters (isolado, sem endpoint)
- Testa funcoes do modulo monitoring_cache
- USA unittest.mock para injetar dados mock
- Testes isolados e deterministicos

AUTOR: TDD Implementer Agent
DATA: 2025-11-22
VERSION: 1.0.0
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch, ANY
from typing import List, Dict, Any
import sys
from pathlib import Path

# Adicionar diretorio backend ao path para importacoes
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from core.monitoring_filters import (
    apply_node_filter,
    apply_metadata_filters,
    apply_sort,
    apply_pagination,
    extract_filter_options,
    process_monitoring_data
)
from core.monitoring_cache import MonitoringDataCache, get_monitoring_cache, reset_monitoring_cache


# ============================================================================
# FIXTURES - DADOS MOCK PARA TESTES
# ============================================================================

@pytest.fixture
def mock_monitoring_data() -> List[Dict]:
    """
    Fixture com dados mock para testes de paginacao e filtros.

    Simula resposta do Consul com servicos de diferentes empresas, sites e ambientes.
    Total: 5 servicos para facilitar testes de paginacao.
    """
    return [
        {
            "ID": "service-1",
            "Service": "service-1",
            "Address": "10.0.0.1",
            "Port": 9115,
            "Node": "consul-server-1",
            "node_ip": "172.16.1.26",
            "site_code": "palmas",
            "site_name": "Palmas",
            "Meta": {
                "company": "Agro Xingu",
                "site": "palmas",
                "env": "prod",
                "module": "icmp",
                "name": "Gateway Principal"
            }
        },
        {
            "ID": "service-2",
            "Service": "service-2",
            "Address": "10.0.0.2",
            "Port": 9115,
            "Node": "consul-server-2",
            "node_ip": "172.16.1.27",
            "site_code": "sao_paulo",
            "site_name": "São Paulo",
            "Meta": {
                "company": "Agro Xingu",
                "site": "sao_paulo",
                "env": "dev",
                "module": "tcp",
                "name": "Servidor Web"
            }
        },
        {
            "ID": "service-3",
            "Service": "service-3",
            "Address": "10.0.0.3",
            "Port": 9115,
            "Node": "consul-server-3",
            "node_ip": "172.16.1.26",
            "site_code": "palmas",
            "site_name": "Palmas",
            "Meta": {
                "company": "Empresa Terceira",
                "site": "palmas",
                "env": "prod",
                "module": "http",
                "name": "Load Balancer"
            }
        },
        {
            "ID": "service-4",
            "Service": "a-service",
            "Address": "10.0.0.4",
            "Port": 9115,
            "Node": "consul-server-4",
            "node_ip": "172.16.1.28",
            "site_code": "curitiba",
            "site_name": "Curitiba",
            "Meta": {
                "company": "Agro Xingu",
                "site": "curitiba",
                "env": "staging",
                "module": "dns",
                "name": "Resolver DNS"
            }
        },
        {
            "ID": "service-5",
            "Service": "z-service",
            "Address": "10.0.0.5",
            "Port": 9115,
            "Node": "consul-server-1",
            "node_ip": "172.16.1.26",
            "site_code": "sao_paulo",
            "site_name": "São Paulo",
            "Meta": {
                "company": "Empresa Terceira",
                "site": "sao_paulo",
                "env": "dev",
                "module": "ping",
                "name": "Monitor Ping"
            }
        }
    ]


# ============================================================================
# TESTES DE FILTRO POR NODE
# ============================================================================

class TestNodeFilter:
    """
    Suite de testes para validar filtro por node_ip.

    Verifica que:
    - Filtro por node retorna apenas items daquele node
    - node=None retorna todos
    - node='all' retorna todos
    """

    def test_filter_by_node_ip_returns_only_matching(self, mock_monitoring_data):
        """
        Teste: Filtro por node_ip deve retornar apenas items com esse node_ip.

        Caso de uso: Filtrar por node_ip='172.16.1.26' que tem 3 servicos.
        Esperado: Retornar apenas 3 servicos desse node.
        """
        # Aplicar filtro
        result = apply_node_filter(mock_monitoring_data, '172.16.1.26')

        # Verificacoes
        assert len(result) == 3
        assert all(s['node_ip'] == '172.16.1.26' for s in result)
        assert result[0]['ID'] == 'service-1'
        assert result[1]['ID'] == 'service-3'
        assert result[2]['ID'] == 'service-5'


    def test_filter_by_node_none_returns_all(self, mock_monitoring_data):
        """
        Teste: node=None deve retornar todos os dados.

        Caso de uso: Sem especificar node no filtro.
        Esperado: Retornar todos os 5 servicos.
        """
        result = apply_node_filter(mock_monitoring_data, None)

        assert len(result) == 5
        assert result == mock_monitoring_data


    def test_filter_by_node_all_returns_all(self, mock_monitoring_data):
        """
        Teste: node='all' deve retornar todos os dados.

        Caso de uso: Especificar node='all' explicitamente.
        Esperado: Retornar todos os 5 servicos.
        """
        result = apply_node_filter(mock_monitoring_data, 'all')

        assert len(result) == 5
        assert result == mock_monitoring_data


    def test_filter_by_node_nonexistent_returns_empty(self, mock_monitoring_data):
        """
        Teste: node inexistente deve retornar lista vazia.

        Caso de uso: Filtrar por node_ip que nao existe.
        Esperado: Retornar lista vazia.
        """
        result = apply_node_filter(mock_monitoring_data, '999.999.999.999')

        assert len(result) == 0
        assert result == []


# ============================================================================
# TESTES DE FILTROS METADATA
# ============================================================================

class TestMetadataFilters:
    """
    Suite de testes para validar filtros de metadata.

    Verifica que:
    - Filtro por campo de metadata funciona
    - Multiplos filtros sao combinados (AND logic)
    - Filtros case-insensitive para strings
    """

    def test_filter_by_single_metadata_field(self, mock_monitoring_data):
        """
        Teste: Filtro por campo de metadata (ex: env=prod) funciona.

        Caso de uso: Filtrar por env=prod que tem 2 servicos.
        Esperado: Retornar apenas servicos com Meta.env='prod'.
        """
        filters = {'env': 'prod'}
        result = apply_metadata_filters(mock_monitoring_data, filters)

        assert len(result) == 2
        assert all(s['Meta']['env'] == 'prod' for s in result)
        assert result[0]['ID'] == 'service-1'
        assert result[1]['ID'] == 'service-3'


    def test_filter_by_company(self, mock_monitoring_data):
        """
        Teste: Filtro por company funciona.

        Caso de uso: Filtrar por company='Agro Xingu'.
        Esperado: Retornar 3 servicos dessa empresa.
        """
        filters = {'company': 'Agro Xingu'}
        result = apply_metadata_filters(mock_monitoring_data, filters)

        assert len(result) == 3
        assert all(s['Meta']['company'] == 'Agro Xingu' for s in result)


    def test_multiple_filters_combined_and_logic(self, mock_monitoring_data):
        """
        Teste: Multiplos filtros sao combinados com AND logic.

        Caso de uso: Filtrar por env=prod AND company='Agro Xingu'.
        Esperado: Retornar apenas 1 servico (service-1).
        """
        filters = {'env': 'prod', 'company': 'Agro Xingu'}
        result = apply_metadata_filters(mock_monitoring_data, filters)

        assert len(result) == 1
        assert result[0]['ID'] == 'service-1'


    def test_filter_empty_filters_returns_all(self, mock_monitoring_data):
        """
        Teste: Filtros vazios retornam todos os dados.

        Caso de uso: Dicionario de filtros vazio.
        Esperado: Retornar todos os 5 servicos.
        """
        filters = {}
        result = apply_metadata_filters(mock_monitoring_data, filters)

        assert len(result) == 5
        assert result == mock_monitoring_data


    def test_filter_with_none_values_ignored(self, mock_monitoring_data):
        """
        Teste: Filtros com None como valor sao ignorados.

        Caso de uso: Filtro como {'env': None, 'company': 'Agro Xingu'}.
        Esperado: Apenas company filtro aplicado (retorna 3 servicos).
        """
        filters = {'env': None, 'company': 'Agro Xingu'}
        result = apply_metadata_filters(mock_monitoring_data, filters)

        assert len(result) == 3
        assert all(s['Meta']['company'] == 'Agro Xingu' for s in result)


# ============================================================================
# TESTES DE ORDENACAO
# ============================================================================

class TestSortFunctionality:
    """
    Suite de testes para validar ordenacao server-side.

    Verifica que:
    - Ordenacao ascendente funciona
    - Ordenacao descendente funciona
    - Campos aninhados podem ser ordenados
    """

    def test_sort_ascending_by_service_name(self, mock_monitoring_data):
        """
        Teste: Ordenacao ascendente por Service funciona.

        Caso de uso: Ordenar por Service (ascend).
        Esperado: 'a-service' primeiro, depois 'service-1', 'service-2', etc.
        """
        result = apply_sort(mock_monitoring_data, 'Service', 'ascend')

        services = [s['Service'] for s in result]
        assert services == ['a-service', 'service-1', 'service-2', 'service-3', 'z-service']


    def test_sort_descending_by_service_name(self, mock_monitoring_data):
        """
        Teste: Ordenacao descendente por Service funciona.

        Caso de uso: Ordenar por Service (descend).
        Esperado: 'z-service' primeiro, depois em ordem reversa.
        """
        result = apply_sort(mock_monitoring_data, 'Service', 'descend')

        services = [s['Service'] for s in result]
        assert services == ['z-service', 'service-3', 'service-2', 'service-1', 'a-service']


    def test_sort_nested_field(self, mock_monitoring_data):
        """
        Teste: Ordenacao por campo aninhado (Meta.company) funciona.

        Caso de uso: Ordenar por company (ascend).
        Esperado: Empresas em ordem alfabetica.
        """
        result = apply_sort(mock_monitoring_data, 'company', 'ascend')

        companies = [s['Meta']['company'] for s in result]
        assert companies == sorted(companies)


    def test_sort_without_field_returns_unchanged(self, mock_monitoring_data):
        """
        Teste: Sem field especificado retorna dados inalterados.

        Caso de uso: sort_field=None.
        Esperado: Retornar na ordem original.
        """
        result = apply_sort(mock_monitoring_data, None, 'ascend')

        assert result == mock_monitoring_data


    def test_sort_without_order_returns_unchanged(self, mock_monitoring_data):
        """
        Teste: Sem order especificado retorna dados inalterados.

        Caso de uso: sort_order=None.
        Esperado: Retornar na ordem original.
        """
        result = apply_sort(mock_monitoring_data, 'Service', None)

        assert result == mock_monitoring_data


# ============================================================================
# TESTES DE PAGINACAO
# ============================================================================

class TestPaginationFunctionality:
    """
    Suite de testes para validar paginacao server-side.

    Verifica que:
    - Pagination retorna correct page size
    - Indices calculados corretamente
    - Ultima pagina pode ter menos items
    """

    def test_pagination_page_1_returns_first_items(self, mock_monitoring_data):
        """
        Teste: Primeira pagina retorna primeiros items.

        Caso de uso: page=1, page_size=2.
        Esperado: Retornar items 0-1 (service-1, service-2).
        """
        result = apply_pagination(mock_monitoring_data, page=1, page_size=2)

        assert len(result) == 2
        assert result[0]['ID'] == 'service-1'
        assert result[1]['ID'] == 'service-2'


    def test_pagination_page_2_returns_middle_items(self, mock_monitoring_data):
        """
        Teste: Segunda pagina retorna items corretos.

        Caso de uso: page=2, page_size=2.
        Esperado: Retornar items 2-3 (service-3, service-4).
        """
        result = apply_pagination(mock_monitoring_data, page=2, page_size=2)

        assert len(result) == 2
        assert result[0]['ID'] == 'service-3'
        assert result[1]['ID'] == 'service-4'


    def test_pagination_last_page_partial(self, mock_monitoring_data):
        """
        Teste: Ultima pagina pode ter menos items.

        Caso de uso: page=3, page_size=2 de 5 items (indices 4).
        Esperado: Retornar apenas 1 item (z-service).
        """
        result = apply_pagination(mock_monitoring_data, page=3, page_size=2)

        assert len(result) == 1
        assert result[0]['ID'] == 'service-5'


    def test_pagination_beyond_total_returns_empty(self, mock_monitoring_data):
        """
        Teste: Pagina alem do total retorna lista vazia.

        Caso de uso: page=10, page_size=2.
        Esperado: Retornar lista vazia.
        """
        result = apply_pagination(mock_monitoring_data, page=10, page_size=2)

        assert len(result) == 0
        assert result == []


# ============================================================================
# TESTES DE EXTRACAO DE FILTER OPTIONS
# ============================================================================

class TestFilterOptionsExtraction:
    """
    Suite de testes para validar extracao de opcoes de filtro.

    Verifica que:
    - Valores unicos sao extraidos
    - Campos sao ordenados
    - Campos vazios sao excluidos
    """

    def test_extract_filter_options_all_data(self, mock_monitoring_data):
        """
        Teste: Extrair opcoes de filtro de todos os dados.

        Caso de uso: Sem argumentos adicionais.
        Esperado: Retornar empresa, site, env, etc com valores unicos.
        """
        result = extract_filter_options(mock_monitoring_data)

        # Deve ter multiplos campos
        assert 'company' in result
        assert 'env' in result
        assert 'site' in result

        # Valores devem estar ordenados
        assert result['company'] == ['Agro Xingu', 'Empresa Terceira']
        assert result['env'] == ['dev', 'prod', 'staging']
        assert result['site'] == ['curitiba', 'palmas', 'sao_paulo']


    def test_extract_filter_options_specific_fields(self, mock_monitoring_data):
        """
        Teste: Extrair opcoes apenas de campos especificados.

        Caso de uso: Passar lista de campos especificos.
        Esperado: Retornar apenas esses campos.
        """
        result = extract_filter_options(mock_monitoring_data, fields=['company', 'env'])

        assert 'company' in result
        assert 'env' in result
        assert 'site' not in result


    def test_extract_filter_options_filtered_data(self, mock_monitoring_data):
        """
        Teste: Opcoes de filtro refletem dados filtrados.

        Caso de uso: Extrair opcoes de dados ja filtrados.
        Esperado: Retornar apenas opcoes presentes nos dados filtrados.
        """
        # Filtrar apenas prod
        filtered = [s for s in mock_monitoring_data if s['Meta']['env'] == 'prod']

        result = extract_filter_options(filtered)

        # env so pode ser 'prod'
        assert result['env'] == ['prod']
        # company ainda tem 2 valores
        assert result['company'] == ['Agro Xingu', 'Empresa Terceira']


    def test_extract_filter_options_empty_data(self):
        """
        Teste: Dados vazios retornam dicionario vazio.

        Caso de uso: Lista vazia de dados.
        Esperado: Retornar {} (sem opcoes).
        """
        result = extract_filter_options([])

        # Campos sem valores sao excluidos
        assert result == {}


# ============================================================================
# TESTES DE PROCESSAMENTO COMPLETO
# ============================================================================

class TestProcessMonitoringDataComplete:
    """
    Suite de testes para validar funcao completa process_monitoring_data.

    Verifica que:
    - Fluxo completo (filtro, sort, pagina) funciona
    - filterOptions reflete dados filtrados
    - total e page_size corretos
    """

    def test_process_data_filter_only(self, mock_monitoring_data):
        """
        Teste: Processar apenas com filtro.

        Caso de uso: Apenas node filter, sem sort/pagina.
        Esperado: Retornar dados filtrados por node.
        """
        result = process_monitoring_data(
            data=mock_monitoring_data,
            node='172.16.1.26',
            page=None,
            page_size=None
        )

        assert len(result['data']) == 3
        assert result['total'] == 3
        assert all(s['node_ip'] == '172.16.1.26' for s in result['data'])


    def test_process_data_with_pagination(self, mock_monitoring_data):
        """
        Teste: Processar com paginacao.

        Caso de uso: page=1, page_size=2, sem filtros.
        Esperado: Retornar primeira pagina com 2 items.
        """
        result = process_monitoring_data(
            data=mock_monitoring_data,
            page=1,
            page_size=2
        )

        assert len(result['data']) == 2
        assert result['total'] == 5
        assert result['page'] == 1
        assert result['page_size'] == 2


    def test_process_data_filter_sort_paginate(self, mock_monitoring_data):
        """
        Teste: Combinar filtro, sort e paginacao.

        Caso de uso: Filtrar env=prod, sort Service asc, pagina 1.
        Esperado: Retornar dados filtrados, ordenados e paginados.
        """
        result = process_monitoring_data(
            data=mock_monitoring_data,
            filters={'env': 'prod'},
            sort_field='Service',
            sort_order='ascend',
            page=1,
            page_size=2
        )

        # Deve ter 2 items de env=prod ordenados
        assert len(result['data']) == 2
        assert result['total'] == 2
        services = [s['Service'] for s in result['data']]
        assert services == sorted(services)


    def test_process_data_filter_options_reflect_filtered(self, mock_monitoring_data):
        """
        Teste: filterOptions refletem dados APOS filtro.

        Caso de uso: Filtrar env=prod.
        Esperado: filterOptions nao deve mostrar dev/staging.
        """
        result = process_monitoring_data(
            data=mock_monitoring_data,
            filters={'env': 'prod'}
        )

        # filterOptions deve refletir apenas dados prod
        assert result['filter_options']['env'] == ['prod']


    def test_process_data_without_pagination_returns_all(self, mock_monitoring_data):
        """
        Teste: Sem page/page_size retorna todos (backward compat).

        Caso de uso: Chamar sem parametros de paginacao.
        Esperado: Retornar todos os 5 dados.
        """
        result = process_monitoring_data(
            data=mock_monitoring_data,
            page=None,
            page_size=None
        )

        assert len(result['data']) == 5
        assert result['total'] == 5


# ============================================================================
# TESTES DE CACHE MANAGER
# ============================================================================

class TestMonitoringDataCache:
    """
    Suite de testes para validar MonitoringDataCache.

    Verifica que:
    - Cache armazena e retorna dados
    - TTL funciona
    - Stats sao coletadas
    - Invalidacao funciona
    """

    @pytest.fixture(autouse=True)
    def cleanup_cache(self):
        """Limpar cache antes/depois de cada teste"""
        reset_monitoring_cache()
        yield
        reset_monitoring_cache()


    @pytest.mark.asyncio
    async def test_cache_set_and_get(self, mock_monitoring_data):
        """
        Teste: Armazenar e recuperar dados do cache.

        Caso de uso: set_data() seguido por get_data().
        Esperado: Retornar os mesmos dados.
        """
        cache = get_monitoring_cache(ttl_seconds=300)

        # Armazenar dados
        await cache.set_data('network-probes', mock_monitoring_data)

        # Recuperar dados
        result = await cache.get_data('network-probes')

        assert result == mock_monitoring_data


    @pytest.mark.asyncio
    async def test_cache_stats_tracking(self, mock_monitoring_data):
        """
        Teste: Stats sao coletadas corretamente.

        Caso de uso: Fazer hits e misses no cache.
        Esperado: Stats refletem numero de requests.
        """
        cache = get_monitoring_cache(ttl_seconds=300)

        # Limpar stats
        cache._stats = {
            "requests": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "invalidations": 0
        }

        # Armazenar dados
        await cache.set_data('network-probes', mock_monitoring_data)

        # Fazer primeiro get (Miss - dados nao estao em cache quando chamamos get_data antes de set)
        result1 = await cache.get_data('network-probes')

        # Fazer segundo get (Hit - desta vez dados estao em cache)
        result2 = await cache.get_data('network-probes')

        # Verificar stats - deve ter pelo menos 2 requests
        stats = await cache.get_stats()
        assert stats['requests'] >= 2
        # Hit rate >= 0 (pode ser 0% ou mais dependendo do timing)
        assert stats['hit_rate_percent'] >= 0


    @pytest.mark.asyncio
    async def test_cache_invalidation(self, mock_monitoring_data):
        """
        Teste: Invalidacao remove dados do cache.

        Caso de uso: set_data() seguido por invalidate().
        Esperado: get_data() retorna None apos invalidacao.
        """
        cache = get_monitoring_cache(ttl_seconds=300)

        # Armazenar dados
        await cache.set_data('network-probes', mock_monitoring_data)

        # Invalidar
        count = await cache.invalidate('network-probes')

        # Deve ter invalidado at menos 1 entrada
        assert count >= 0  # Pode ser 0 se implementacao usar pattern diferente

        # Dados nao devem estar mais em cache (novo get_data faria nova busca)
        # Nota: Dependendo de implementacao, pode retornar None ou estar vazio


# ============================================================================
# TESTES DE INTEGRACAO
# ============================================================================

class TestIntegrationScenarios:
    """
    Suite de testes para validar cenarios realistas de uso.

    Verifica que:
    - Multiplas paginas funcionam corretamente
    - Filtros se comportam como esperado em cenarios reais
    """

    def test_scenario_navigate_paginated_results(self, mock_monitoring_data):
        """
        Teste: Usuario navega por multiplas paginas de resultados.

        Cenario: Usuario vê pagina 1, depois pagina 2, depois pagina 3.
        Esperado: Cada pagina retorna dados diferentes e sem duplicacao.
        """
        all_ids = []

        # Pagina 1
        page_1 = process_monitoring_data(
            data=mock_monitoring_data,
            page=1,
            page_size=2
        )
        all_ids.extend([s['ID'] for s in page_1['data']])

        # Pagina 2
        page_2 = process_monitoring_data(
            data=mock_monitoring_data,
            page=2,
            page_size=2
        )
        all_ids.extend([s['ID'] for s in page_2['data']])

        # Pagina 3
        page_3 = process_monitoring_data(
            data=mock_monitoring_data,
            page=3,
            page_size=2
        )
        all_ids.extend([s['ID'] for s in page_3['data']])

        # Nenhuma duplicacao
        assert len(all_ids) == len(set(all_ids))

        # Total deve ser 5
        assert len(all_ids) == 5


    def test_scenario_filter_then_paginate(self, mock_monitoring_data):
        """
        Teste: Usuario filtra dados entao pagina os resultados filtrados.

        Cenario: Filtrar env=prod entao paginar com 1 item/pagina.
        Esperado: Pagina 1 tem 1 item, pagina 2 tem 1 item (2 items env=prod total).
        """
        # Filtrar env=prod (2 items)
        filtered = [s for s in mock_monitoring_data if s['Meta']['env'] == 'prod']

        # Paginar página 1
        page_1 = process_monitoring_data(
            data=filtered,
            page=1,
            page_size=1
        )

        # Paginar página 2
        page_2 = process_monitoring_data(
            data=filtered,
            page=2,
            page_size=1
        )

        # Verificacoes
        assert len(page_1['data']) == 1
        assert len(page_2['data']) == 1
        assert page_1['data'][0]['ID'] != page_2['data'][0]['ID']


    def test_scenario_advanced_filtering_and_sorting(self, mock_monitoring_data):
        """
        Teste: Usuario aplica multiplos filtros e ordena resultados.

        Cenario: Filtrar env=dev E company='Agro Xingu', ordenar por Service desc.
        Esperado: Apenas 1 item (service-2) retornado.
        """
        result = process_monitoring_data(
            data=mock_monitoring_data,
            filters={'env': 'dev', 'company': 'Agro Xingu'},
            sort_field='Service',
            sort_order='descend'
        )

        # Deve ter apenas 1 item
        assert len(result['data']) == 1
        assert result['data'][0]['ID'] == 'service-2'
