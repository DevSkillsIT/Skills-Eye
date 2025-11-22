"""
Testes unitarios para a API de nodes.

Este arquivo contem testes para validar o comportamento do endpoint
/api/v1/nodes, incluindo cenarios de sucesso, timeout e erros.

Data: 2025-11-21
Autor: Claude Code
Versao: 1.0.0

Uso:
    pytest tests/test_nodes_api.py -v
    pytest tests/test_nodes_api.py -v -k "timeout"
    pytest tests/test_nodes_api.py -v --cov=api.nodes

Requisitos:
    - pytest
    - pytest-asyncio
    - pytest-cov (opcional, para coverage)
"""

import pytest
import asyncio
import time
from unittest.mock import patch, AsyncMock, MagicMock
from typing import Dict, Any, List

# Importar modulos do projeto
import sys
from pathlib import Path

# Adicionar backend ao path para imports
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))


class TestGetServiceCount:
    """
    Testes para a funcao get_service_count interna do endpoint /api/v1/nodes.

    Esta funcao e responsavel por contar servicos de cada no usando a Catalog API
    e tratar timeouts/erros de forma resiliente.
    """

    @pytest.mark.asyncio
    async def test_get_service_count_success(self):
        """
        Testa cenario de sucesso na contagem de servicos.

        Quando a Catalog API responde corretamente, a funcao deve:
        - Retornar services_count com o numero correto de servicos
        - Definir services_status como "ok"
        - Mapear site_name corretamente
        """
        from api.nodes import router, get_cache
        from core.consul_manager import ConsulManager

        # Mock do ConsulManager.get_node_services
        mock_node_data = {
            "Node": {"Node": "test-node", "Address": "192.168.1.100"},
            "Services": {
                "service1": {"ID": "service1", "Service": "app1"},
                "service2": {"ID": "service2", "Service": "app2"},
                "consul": {"ID": "consul", "Service": "consul"}  # Deve ser ignorado
            }
        }

        # Member de entrada para testar
        member = {
            "node": "test-node",
            "addr": "192.168.1.100",
            "port": 8301,
            "status": 1,
            "tags": {}
        }

        # Sites map simulado
        sites_map = {"192.168.1.100": "Site-A"}

        with patch.object(ConsulManager, 'get_node_services', new_callable=AsyncMock) as mock_get_services:
            mock_get_services.return_value = mock_node_data

            with patch.object(ConsulManager, 'get_members', new_callable=AsyncMock) as mock_get_members:
                mock_get_members.return_value = [member]

                # Limpar cache para forcar nova requisicao
                cache = get_cache(ttl_seconds=60)
                await cache.delete("nodes:list:all")

                # Mock do KVManager para sites
                with patch('api.nodes.KVManager') as mock_kv_class:
                    mock_kv = MagicMock()
                    mock_kv.get_json = AsyncMock(return_value={
                        "data": {
                            "sites": [
                                {"prometheus_instance": "192.168.1.100", "name": "Site-A"}
                            ]
                        }
                    })
                    mock_kv_class.return_value = mock_kv

                    # Importar e executar endpoint
                    from api.nodes import get_nodes
                    result = await get_nodes()

                    # Verificar resultado
                    assert result["success"] is True
                    assert len(result["data"]) == 1

                    node_data = result["data"][0]
                    # Deve ter 2 servicos (consul e ignorado)
                    assert node_data["services_count"] == 2
                    assert node_data["services_status"] == "ok"
                    assert node_data["site_name"] == "Site-A"

    @pytest.mark.asyncio
    async def test_get_service_count_timeout(self):
        """
        Testa comportamento quando ocorre timeout na Catalog API.

        Quando a Catalog API nao responde no tempo configurado, a funcao deve:
        - Definir services_count como 0
        - Definir services_status como "error"
        - NAO lancar excecao (fail gracefully)
        - Incrementar metrica consul_node_enrich_failures
        """
        from api.nodes import router, get_cache
        from core.consul_manager import ConsulManager
        from core.config import Config

        # Member de entrada
        member = {
            "node": "slow-node",
            "addr": "192.168.1.200",
            "port": 8301,
            "status": 1,
            "tags": {}
        }

        async def slow_response():
            """Simula resposta lenta que causa timeout"""
            await asyncio.sleep(10)  # Muito maior que o timeout configurado
            return {}

        with patch.object(ConsulManager, 'get_node_services', new_callable=AsyncMock) as mock_get_services:
            # Configurar para lancar TimeoutError
            mock_get_services.side_effect = asyncio.TimeoutError()

            with patch.object(ConsulManager, 'get_members', new_callable=AsyncMock) as mock_get_members:
                mock_get_members.return_value = [member]

                # Limpar cache
                cache = get_cache(ttl_seconds=60)
                await cache.delete("nodes:list:all")

                # Mock do KVManager
                with patch('api.nodes.KVManager') as mock_kv_class:
                    mock_kv = MagicMock()
                    mock_kv.get_json = AsyncMock(return_value={"data": {"sites": []}})
                    mock_kv_class.return_value = mock_kv

                    # Executar endpoint
                    from api.nodes import get_nodes
                    result = await get_nodes()

                    # Verificar que nao lancou excecao
                    assert result["success"] is True
                    assert len(result["data"]) == 1

                    node_data = result["data"][0]
                    # Timeout deve resultar em services_count = 0 e status = error
                    assert node_data["services_count"] == 0
                    assert node_data["services_status"] == "error"

    @pytest.mark.asyncio
    async def test_get_service_count_connection_error(self):
        """
        Testa tratamento de erro de conexao.

        Quando nao e possivel conectar ao Consul, a funcao deve:
        - Definir services_count como 0
        - Definir services_status como "error"
        - Registrar erro nas metricas
        """
        import httpx
        from api.nodes import router, get_cache
        from core.consul_manager import ConsulManager

        # Member de entrada
        member = {
            "node": "unreachable-node",
            "addr": "192.168.1.250",
            "port": 8301,
            "status": 1,
            "tags": {}
        }

        with patch.object(ConsulManager, 'get_node_services', new_callable=AsyncMock) as mock_get_services:
            # Simular erro de conexao
            mock_get_services.side_effect = httpx.ConnectError("Connection refused")

            with patch.object(ConsulManager, 'get_members', new_callable=AsyncMock) as mock_get_members:
                mock_get_members.return_value = [member]

                # Limpar cache
                cache = get_cache(ttl_seconds=60)
                await cache.delete("nodes:list:all")

                # Mock do KVManager
                with patch('api.nodes.KVManager') as mock_kv_class:
                    mock_kv = MagicMock()
                    mock_kv.get_json = AsyncMock(return_value={"data": {"sites": []}})
                    mock_kv_class.return_value = mock_kv

                    # Executar endpoint
                    from api.nodes import get_nodes
                    result = await get_nodes()

                    # Verificar tratamento de erro
                    assert result["success"] is True
                    assert len(result["data"]) == 1

                    node_data = result["data"][0]
                    assert node_data["services_count"] == 0
                    assert node_data["services_status"] == "error"

    @pytest.mark.asyncio
    async def test_get_service_count_http_error(self):
        """
        Testa tratamento de erro HTTP (4xx/5xx).

        Quando o Consul retorna erro HTTP, a funcao deve:
        - Definir services_count como 0
        - Definir services_status como "error"
        - Registrar codigo de status nas metricas
        """
        import httpx
        from api.nodes import router, get_cache
        from core.consul_manager import ConsulManager

        # Member de entrada
        member = {
            "node": "error-node",
            "addr": "192.168.1.251",
            "port": 8301,
            "status": 1,
            "tags": {}
        }

        # Criar resposta HTTP com erro
        mock_response = httpx.Response(status_code=503)

        with patch.object(ConsulManager, 'get_node_services', new_callable=AsyncMock) as mock_get_services:
            # Simular erro HTTP
            mock_get_services.side_effect = httpx.HTTPStatusError(
                "Service Unavailable",
                request=httpx.Request("GET", "http://test"),
                response=mock_response
            )

            with patch.object(ConsulManager, 'get_members', new_callable=AsyncMock) as mock_get_members:
                mock_get_members.return_value = [member]

                # Limpar cache
                cache = get_cache(ttl_seconds=60)
                await cache.delete("nodes:list:all")

                # Mock do KVManager
                with patch('api.nodes.KVManager') as mock_kv_class:
                    mock_kv = MagicMock()
                    mock_kv.get_json = AsyncMock(return_value={"data": {"sites": []}})
                    mock_kv_class.return_value = mock_kv

                    # Executar endpoint
                    from api.nodes import get_nodes
                    result = await get_nodes()

                    # Verificar tratamento de erro
                    assert result["success"] is True
                    assert len(result["data"]) == 1

                    node_data = result["data"][0]
                    assert node_data["services_count"] == 0
                    assert node_data["services_status"] == "error"

    @pytest.mark.asyncio
    async def test_get_service_count_generic_error(self):
        """
        Testa tratamento de erro generico/desconhecido.

        Qualquer excecao nao tratada especificamente deve:
        - Definir services_count como 0
        - Definir services_status como "error"
        - Nao quebrar a listagem dos demais nos
        """
        from api.nodes import router, get_cache
        from core.consul_manager import ConsulManager

        # Member de entrada
        member = {
            "node": "broken-node",
            "addr": "192.168.1.252",
            "port": 8301,
            "status": 1,
            "tags": {}
        }

        with patch.object(ConsulManager, 'get_node_services', new_callable=AsyncMock) as mock_get_services:
            # Simular erro generico
            mock_get_services.side_effect = ValueError("Unexpected error in parsing")

            with patch.object(ConsulManager, 'get_members', new_callable=AsyncMock) as mock_get_members:
                mock_get_members.return_value = [member]

                # Limpar cache
                cache = get_cache(ttl_seconds=60)
                await cache.delete("nodes:list:all")

                # Mock do KVManager
                with patch('api.nodes.KVManager') as mock_kv_class:
                    mock_kv = MagicMock()
                    mock_kv.get_json = AsyncMock(return_value={"data": {"sites": []}})
                    mock_kv_class.return_value = mock_kv

                    # Executar endpoint
                    from api.nodes import get_nodes
                    result = await get_nodes()

                    # Verificar tratamento de erro
                    assert result["success"] is True
                    assert len(result["data"]) == 1

                    node_data = result["data"][0]
                    assert node_data["services_count"] == 0
                    assert node_data["services_status"] == "error"


class TestNodesEndpoint:
    """
    Testes de integracao para o endpoint GET /api/v1/nodes.

    Valida comportamento geral do endpoint incluindo cache,
    contrato de resposta e tratamento de multiplos nos.
    """

    @pytest.mark.asyncio
    async def test_nodes_response_contract(self):
        """
        Testa que a resposta segue o contrato definido no SPEC-PERF-001.

        O endpoint deve retornar:
        - success: boolean
        - data: array de nodes
        - total: numero de nodes
        - main_server: string com IP do servidor principal
        """
        from api.nodes import router, get_cache
        from core.consul_manager import ConsulManager
        from core.config import Config

        # Mock de dados
        members = [
            {"node": "node1", "addr": "192.168.1.1", "port": 8301, "status": 1, "tags": {}},
            {"node": "node2", "addr": "192.168.1.2", "port": 8301, "status": 1, "tags": {}}
        ]

        mock_node_data = {
            "Node": {"Node": "test", "Address": "192.168.1.1"},
            "Services": {"svc1": {"ID": "svc1", "Service": "app"}}
        }

        with patch.object(ConsulManager, 'get_node_services', new_callable=AsyncMock) as mock_get_services:
            mock_get_services.return_value = mock_node_data

            with patch.object(ConsulManager, 'get_members', new_callable=AsyncMock) as mock_get_members:
                mock_get_members.return_value = members

                # Limpar cache
                cache = get_cache(ttl_seconds=60)
                await cache.delete("nodes:list:all")

                # Mock do KVManager
                with patch('api.nodes.KVManager') as mock_kv_class:
                    mock_kv = MagicMock()
                    mock_kv.get_json = AsyncMock(return_value={"data": {"sites": []}})
                    mock_kv_class.return_value = mock_kv

                    # Executar endpoint
                    from api.nodes import get_nodes
                    result = await get_nodes()

                    # Validar contrato
                    assert "success" in result
                    assert "data" in result
                    assert "total" in result
                    assert "main_server" in result

                    assert isinstance(result["success"], bool)
                    assert isinstance(result["data"], list)
                    assert isinstance(result["total"], int)
                    assert isinstance(result["main_server"], str)

                    # Validar estrutura de cada node
                    for node in result["data"]:
                        assert "node" in node or "name" in node
                        assert "addr" in node
                        assert "services_count" in node
                        assert "site_name" in node
                        assert "services_status" in node

    @pytest.mark.asyncio
    async def test_nodes_cache_behavior(self):
        """
        Testa comportamento do cache de nodes.

        O cache deve:
        - Retornar dados cacheados se TTL nao expirou
        - Evitar chamadas redundantes ao Consul
        - Ter TTL de 60 segundos (SPEC-PERF-001)
        """
        from api.nodes import router, get_cache
        from core.consul_manager import ConsulManager

        # Preparar dados
        members = [
            {"node": "node1", "addr": "192.168.1.1", "port": 8301, "status": 1, "tags": {}}
        ]

        mock_node_data = {
            "Node": {"Node": "node1", "Address": "192.168.1.1"},
            "Services": {}
        }

        call_count = 0

        async def counting_get_members():
            nonlocal call_count
            call_count += 1
            return members

        with patch.object(ConsulManager, 'get_node_services', new_callable=AsyncMock) as mock_get_services:
            mock_get_services.return_value = mock_node_data

            with patch.object(ConsulManager, 'get_members', side_effect=counting_get_members):
                # Limpar cache
                cache = get_cache(ttl_seconds=60)
                await cache.delete("nodes:list:all")

                # Mock do KVManager
                with patch('api.nodes.KVManager') as mock_kv_class:
                    mock_kv = MagicMock()
                    mock_kv.get_json = AsyncMock(return_value={"data": {"sites": []}})
                    mock_kv_class.return_value = mock_kv

                    # Primeira chamada - deve buscar do Consul
                    from api.nodes import get_nodes
                    result1 = await get_nodes()
                    first_call_count = call_count

                    # Segunda chamada - deve usar cache
                    result2 = await get_nodes()
                    second_call_count = call_count

                    # Verificar que cache funcionou
                    assert first_call_count == 1, "Primeira chamada deve acessar Consul"
                    assert second_call_count == 1, "Segunda chamada deve usar cache"

                    # Resultados devem ser iguais
                    assert result1["total"] == result2["total"]

    @pytest.mark.asyncio
    async def test_nodes_multiple_nodes_parallel(self):
        """
        Testa processamento paralelo de multiplos nodes.

        O endpoint deve:
        - Processar todos os nodes em paralelo
        - Respeitar limite de concorrencia (semaphore)
        - Retornar todos os nodes mesmo se alguns falharem
        """
        from api.nodes import router, get_cache
        from core.consul_manager import ConsulManager

        # 5 nodes - alguns vao falhar
        members = [
            {"node": f"node{i}", "addr": f"192.168.1.{i}", "port": 8301, "status": 1, "tags": {}}
            for i in range(1, 6)
        ]

        async def selective_response(node_name):
            """Node 3 falha, outros retornam OK"""
            if "node3" in node_name:
                raise asyncio.TimeoutError()
            return {
                "Node": {"Node": node_name, "Address": "192.168.1.1"},
                "Services": {"svc": {"ID": "svc", "Service": "app"}}
            }

        with patch.object(ConsulManager, 'get_node_services', side_effect=selective_response):
            with patch.object(ConsulManager, 'get_members', new_callable=AsyncMock) as mock_get_members:
                mock_get_members.return_value = members

                # Limpar cache
                cache = get_cache(ttl_seconds=60)
                await cache.delete("nodes:list:all")

                # Mock do KVManager
                with patch('api.nodes.KVManager') as mock_kv_class:
                    mock_kv = MagicMock()
                    mock_kv.get_json = AsyncMock(return_value={"data": {"sites": []}})
                    mock_kv_class.return_value = mock_kv

                    # Executar endpoint
                    from api.nodes import get_nodes
                    result = await get_nodes()

                    # Deve retornar todos os 5 nodes
                    assert result["success"] is True
                    assert result["total"] == 5

                    # Node3 deve ter erro, outros devem estar OK
                    for node in result["data"]:
                        if "node3" in node.get("node", ""):
                            assert node["services_status"] == "error"
                            assert node["services_count"] == 0
                        else:
                            assert node["services_status"] == "ok"
                            assert node["services_count"] >= 0


class TestSiteMapping:
    """
    Testes para mapeamento de sites (IP -> nome).

    Valida que o endpoint mapeia corretamente IPs de nodes
    para nomes de sites definidos no KV.
    """

    @pytest.mark.asyncio
    async def test_site_mapping_success(self):
        """
        Testa mapeamento correto de IP para nome de site.

        Quando o IP do node esta no KV metadata/sites, o campo
        site_name deve ser preenchido com o nome do site.
        """
        from api.nodes import router, get_cache
        from core.consul_manager import ConsulManager

        # Member com IP mapeado
        member = {
            "node": "mapped-node",
            "addr": "10.0.0.100",
            "port": 8301,
            "status": 1,
            "tags": {}
        }

        # Sites no KV
        sites_data = {
            "data": {
                "sites": [
                    {"prometheus_instance": "10.0.0.100", "name": "Datacenter-Rio"},
                    {"prometheus_instance": "10.0.0.200", "name": "Datacenter-SP"}
                ]
            }
        }

        mock_node_data = {
            "Node": {"Node": "mapped-node", "Address": "10.0.0.100"},
            "Services": {}
        }

        with patch.object(ConsulManager, 'get_node_services', new_callable=AsyncMock) as mock_get_services:
            mock_get_services.return_value = mock_node_data

            with patch.object(ConsulManager, 'get_members', new_callable=AsyncMock) as mock_get_members:
                mock_get_members.return_value = [member]

                # Limpar caches
                cache = get_cache(ttl_seconds=60)
                await cache.delete("nodes:list:all")

                from api.nodes import sites_cache
                await sites_cache.delete("sites:map:all")

                # Mock do KVManager
                with patch('api.nodes.KVManager') as mock_kv_class:
                    mock_kv = MagicMock()
                    mock_kv.get_json = AsyncMock(return_value=sites_data)
                    mock_kv_class.return_value = mock_kv

                    # Executar endpoint
                    from api.nodes import get_nodes
                    result = await get_nodes()

                    # Verificar mapeamento
                    assert result["success"] is True
                    node_data = result["data"][0]
                    assert node_data["site_name"] == "Datacenter-Rio"

    @pytest.mark.asyncio
    async def test_site_mapping_not_found(self):
        """
        Testa comportamento quando IP nao esta mapeado.

        Quando o IP do node nao existe no KV metadata/sites,
        o campo site_name deve ser "Nao mapeado".
        """
        from api.nodes import router, get_cache
        from core.consul_manager import ConsulManager

        # Member com IP nao mapeado
        member = {
            "node": "unmapped-node",
            "addr": "192.168.99.99",
            "port": 8301,
            "status": 1,
            "tags": {}
        }

        # Sites no KV (sem o IP 192.168.99.99)
        sites_data = {
            "data": {
                "sites": [
                    {"prometheus_instance": "10.0.0.100", "name": "Site-A"}
                ]
            }
        }

        mock_node_data = {
            "Node": {"Node": "unmapped-node", "Address": "192.168.99.99"},
            "Services": {}
        }

        with patch.object(ConsulManager, 'get_node_services', new_callable=AsyncMock) as mock_get_services:
            mock_get_services.return_value = mock_node_data

            with patch.object(ConsulManager, 'get_members', new_callable=AsyncMock) as mock_get_members:
                mock_get_members.return_value = [member]

                # Limpar caches
                cache = get_cache(ttl_seconds=60)
                await cache.delete("nodes:list:all")

                from api.nodes import sites_cache
                await sites_cache.delete("sites:map:all")

                # Mock do KVManager
                with patch('api.nodes.KVManager') as mock_kv_class:
                    mock_kv = MagicMock()
                    mock_kv.get_json = AsyncMock(return_value=sites_data)
                    mock_kv_class.return_value = mock_kv

                    # Executar endpoint
                    from api.nodes import get_nodes
                    result = await get_nodes()

                    # Verificar valor padrao
                    assert result["success"] is True
                    node_data = result["data"][0]
                    assert node_data["site_name"] == "Nao mapeado"


class TestPerformanceMetrics:
    """
    Testes para metricas Prometheus de performance.

    Valida que as metricas consul_node_enrich_failures e
    consul_node_enrich_duration sao registradas corretamente.
    """

    @pytest.mark.asyncio
    async def test_metrics_registered_on_success(self):
        """
        Testa que metrica de duracao e registrada em sucesso.

        A metrica consul_node_enrich_duration deve ser observada
        com status="success" quando a chamada funciona.
        """
        from api.nodes import router, get_cache
        from core.consul_manager import ConsulManager

        member = {
            "node": "metric-node",
            "addr": "192.168.1.1",
            "port": 8301,
            "status": 1,
            "tags": {}
        }

        mock_node_data = {
            "Node": {"Node": "metric-node", "Address": "192.168.1.1"},
            "Services": {"svc": {"ID": "svc", "Service": "app"}}
        }

        with patch.object(ConsulManager, 'get_node_services', new_callable=AsyncMock) as mock_get_services:
            mock_get_services.return_value = mock_node_data

            with patch.object(ConsulManager, 'get_members', new_callable=AsyncMock) as mock_get_members:
                mock_get_members.return_value = [member]

                # Limpar cache
                cache = get_cache(ttl_seconds=60)
                await cache.delete("nodes:list:all")

                # Mock das metricas para verificar chamadas
                with patch('api.nodes.consul_node_enrich_duration') as mock_duration:
                    mock_histogram = MagicMock()
                    mock_duration.labels.return_value = mock_histogram

                    # Mock do KVManager
                    with patch('api.nodes.KVManager') as mock_kv_class:
                        mock_kv = MagicMock()
                        mock_kv.get_json = AsyncMock(return_value={"data": {"sites": []}})
                        mock_kv_class.return_value = mock_kv

                        # Executar endpoint
                        from api.nodes import get_nodes
                        result = await get_nodes()

                        # Verificar que metrica foi chamada
                        mock_duration.labels.assert_called()
                        mock_histogram.observe.assert_called()

    @pytest.mark.asyncio
    async def test_metrics_registered_on_failure(self):
        """
        Testa que metrica de falha e registrada em erro.

        A metrica consul_node_enrich_failures deve ser incrementada
        quando ocorre timeout ou outro erro.
        """
        from api.nodes import router, get_cache
        from core.consul_manager import ConsulManager

        member = {
            "node": "fail-node",
            "addr": "192.168.1.1",
            "port": 8301,
            "status": 1,
            "tags": {}
        }

        with patch.object(ConsulManager, 'get_node_services', new_callable=AsyncMock) as mock_get_services:
            mock_get_services.side_effect = asyncio.TimeoutError()

            with patch.object(ConsulManager, 'get_members', new_callable=AsyncMock) as mock_get_members:
                mock_get_members.return_value = [member]

                # Limpar cache
                cache = get_cache(ttl_seconds=60)
                await cache.delete("nodes:list:all")

                # Mock das metricas para verificar chamadas
                with patch('api.nodes.consul_node_enrich_failures') as mock_failures:
                    mock_counter = MagicMock()
                    mock_failures.labels.return_value = mock_counter

                    # Mock do KVManager
                    with patch('api.nodes.KVManager') as mock_kv_class:
                        mock_kv = MagicMock()
                        mock_kv.get_json = AsyncMock(return_value={"data": {"sites": []}})
                        mock_kv_class.return_value = mock_kv

                        # Executar endpoint
                        from api.nodes import get_nodes
                        result = await get_nodes()

                        # Verificar que metrica de falha foi chamada
                        mock_failures.labels.assert_called_with(
                            node_name="fail-node",
                            error_type="timeout"
                        )
                        mock_counter.inc.assert_called()


if __name__ == "__main__":
    # Executar testes com pytest
    pytest.main([__file__, "-v", "-s"])
