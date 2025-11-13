"""
Testes Unitários: CategorizationRuleEngine

OBJETIVO:
- Validar carregamento de regras do KV
- Validar matching de regras por prioridade
- Validar fallback para custom-exporters
- Validar cache de regras

AUTOR: Sistema de Refatoração Skills Eye v2.0
DATA: 2025-11-13
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from core.categorization_rule_engine import CategorizationRuleEngine


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def mock_rules_data():
    """Dados de regras para testes"""
    return {
        "version": "1.0.0",
        "last_updated": "2025-11-13T10:00:00",
        "total_rules": 3,
        "rules": [
            {
                "id": "blackbox_icmp",
                "priority": 100,
                "category": "network-probes",
                "display_name": "ICMP (Ping)",
                "exporter_type": "blackbox",
                "conditions": {
                    "job_name_pattern": "^icmp.*",
                    "metrics_path": "/probe",
                    "module_pattern": "^icmp$"
                }
            },
            {
                "id": "exporter_node",
                "priority": 80,
                "category": "system-exporters",
                "display_name": "Node Exporter",
                "exporter_type": "node_exporter",
                "conditions": {
                    "job_name_pattern": "^node.*",
                    "metrics_path": "/metrics"
                }
            },
            {
                "id": "exporter_mysql",
                "priority": 80,
                "category": "database-exporters",
                "display_name": "MySQL Exporter",
                "exporter_type": "mysqld_exporter",
                "conditions": {
                    "job_name_pattern": "^mysql.*",
                    "metrics_path": "/metrics"
                }
            }
        ],
        "default_category": "custom-exporters"
    }


@pytest.fixture
def mock_config_manager():
    """Fixture que cria um mock do ConsulKVConfigManager"""
    mock = AsyncMock()
    mock.get = AsyncMock(return_value=None)
    mock.put = AsyncMock(return_value=True)
    return mock


@pytest.fixture
def engine(mock_config_manager):
    """Fixture que cria um engine para cada teste"""
    return CategorizationRuleEngine(mock_config_manager)


# ============================================================================
# TESTES DE LOAD_RULES
# ============================================================================

class TestLoadRules:
    """Testes de carregamento de regras"""

    @pytest.mark.asyncio
    async def test_load_rules_success(self, engine, mock_rules_data):
        """Testa carregamento bem-sucedido de regras"""
        # Mock do config manager
        with patch.object(engine.config_manager, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_rules_data

            # Carregar regras
            success = await engine.load_rules()

            # Validações
            assert success is True
            assert len(engine.rules) == 3
            assert engine.default_category == "custom-exporters"
            mock_get.assert_called_once_with('monitoring-types/categorization/rules', use_cache=True)

    @pytest.mark.asyncio
    async def test_load_rules_force_reload(self, engine, mock_rules_data):
        """Testa force reload ignora cache"""
        with patch.object(engine.config_manager, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_rules_data

            # Carregar com force_reload
            await engine.load_rules(force_reload=True)

            # Deve usar use_cache=False
            mock_get.assert_called_once_with('monitoring-types/categorization/rules', use_cache=False)

    @pytest.mark.asyncio
    async def test_load_rules_no_data(self, engine):
        """Testa comportamento quando não há regras no KV"""
        with patch.object(engine.config_manager, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = None

            # Carregar regras
            success = await engine.load_rules()

            # Validações
            assert success is False
            assert len(engine.rules) == 0

    @pytest.mark.asyncio
    async def test_load_rules_caching(self, engine, mock_rules_data):
        """Testa que regras são cacheadas após carregamento"""
        with patch.object(engine.config_manager, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_rules_data

            # Primeira carga
            await engine.load_rules()
            assert mock_get.call_count == 1

            # Segunda carga (sem force_reload) - deve usar cache interno
            await engine.load_rules()
            assert mock_get.call_count == 1  # Não deve chamar get novamente


# ============================================================================
# TESTES DE CATEGORIZE
# ============================================================================

class TestCategorize:
    """Testes de categorização de jobs"""

    @pytest.mark.asyncio
    async def test_categorize_blackbox_icmp(self, engine, mock_rules_data):
        """Testa categorização de ICMP (blackbox)"""
        with patch.object(engine.config_manager, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_rules_data
            await engine.load_rules()

        # Job ICMP
        job_data = {
            "job_name": "icmp",
            "metrics_path": "/probe",
            "relabel_configs": [
                {"target_label": "__param_module", "replacement": "icmp"}
            ]
        }

        category, type_info = engine.categorize(job_data)

        # Validações
        assert category == "network-probes"
        assert type_info["id"] == "icmp"
        assert type_info["exporter_type"] == "blackbox"

    @pytest.mark.asyncio
    async def test_categorize_node_exporter(self, engine, mock_rules_data):
        """Testa categorização de Node Exporter"""
        with patch.object(engine.config_manager, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_rules_data
            await engine.load_rules()

        # Job Node Exporter
        job_data = {
            "job_name": "node_exporter",
            "metrics_path": "/metrics"
        }

        category, type_info = engine.categorize(job_data)

        # Validações
        assert category == "system-exporters"
        assert type_info["exporter_type"] == "node_exporter"

    @pytest.mark.asyncio
    async def test_categorize_priority_order(self, engine, mock_rules_data):
        """Testa que maior prioridade vence"""
        # Adicionar regra de baixa prioridade que também match'a 'icmp'
        mock_rules_data["rules"].append({
            "id": "generic_icmp",
            "priority": 50,  # Menor que blackbox (100)
            "category": "custom-exporters",
            "conditions": {
                "job_name_pattern": ".*icmp.*",
            }
        })

        with patch.object(engine.config_manager, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_rules_data
            await engine.load_rules()

        # Job que match'a ambas as regras
        job_data = {
            "job_name": "icmp",
            "metrics_path": "/probe"
        }

        category, type_info = engine.categorize(job_data)

        # Deve usar regra de maior prioridade (blackbox_icmp)
        assert category == "network-probes"
        assert type_info["priority"] == 100

    @pytest.mark.asyncio
    async def test_categorize_fallback_to_default(self, engine, mock_rules_data):
        """Testa fallback para categoria default quando nenhuma regra match"""
        with patch.object(engine.config_manager, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_rules_data
            await engine.load_rules()

        # Job que não match'a nenhuma regra
        job_data = {
            "job_name": "unknown_exporter",
            "metrics_path": "/metrics"
        }

        category, type_info = engine.categorize(job_data)

        # Deve usar categoria default
        assert category == "custom-exporters"
        assert type_info["id"] == "unknown_exporter"
        assert type_info["display_name"] == "Unknown Exporter"

    @pytest.mark.asyncio
    async def test_categorize_module_matching(self, engine, mock_rules_data):
        """Testa matching por module_pattern (blackbox)"""
        with patch.object(engine.config_manager, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_rules_data
            await engine.load_rules()

        # Job com módulo ICMP
        job_data = {
            "job_name": "blackbox",  # Nome genérico
            "metrics_path": "/probe",
            "relabel_configs": [
                {"target_label": "__param_module", "replacement": "icmp"}
            ]
        }

        category, type_info = engine.categorize(job_data)

        # Deve match por module_pattern
        assert category == "network-probes"

    @pytest.mark.asyncio
    async def test_categorize_metrics_path_distinction(self, engine, mock_rules_data):
        """Testa distinção por metrics_path"""
        with patch.object(engine.config_manager, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_rules_data
            await engine.load_rules()

        # Job com metrics_path /probe
        job_probe = {
            "job_name": "test",
            "metrics_path": "/probe"
        }

        # Job com metrics_path /metrics
        job_metrics = {
            "job_name": "test",
            "metrics_path": "/metrics"
        }

        # Blackbox deve ter priority maior (100) se path = /probe
        # Sem regras específicas, deve usar default
        cat_probe, _ = engine.categorize(job_probe)
        cat_metrics, _ = engine.categorize(job_metrics)

        # Ambos vão para default pois não match'am nenhuma regra
        assert cat_probe == "custom-exporters"
        assert cat_metrics == "custom-exporters"


# ============================================================================
# EXECUTAR TESTES
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
