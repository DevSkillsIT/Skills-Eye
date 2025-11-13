"""
Testes Unitários: ConsulKVConfigManager

OBJETIVO:
- Validar cache em memória com TTL
- Validar operações get/put/invalidate
- Validar namespace automático
- Validar comportamento de expiração

AUTOR: Sistema de Refatoração Skills Eye v2.0
DATA: 2025-11-13
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from core.consul_kv_config_manager import ConsulKVConfigManager, CachedValue


# ============================================================================
# TESTES DE CachedValue
# ============================================================================

def test_cached_value_creation():
    """Testa criação de CachedValue"""
    value = {"test": "data"}
    ttl = 300

    cached = CachedValue(value, ttl)

    assert cached.value == value
    assert cached.ttl_seconds == ttl
    assert isinstance(cached.timestamp, datetime)


def test_cached_value_not_expired():
    """Testa que valor recém-criado não está expirado"""
    value = {"test": "data"}
    cached = CachedValue(value, ttl_seconds=300)

    assert not cached.is_expired()


def test_cached_value_expired():
    """Testa que valor antigo expira"""
    value = {"test": "data"}
    cached = CachedValue(value, ttl_seconds=1)

    # Simular tempo passando
    cached.timestamp = datetime.now() - timedelta(seconds=2)

    assert cached.is_expired()


# ============================================================================
# TESTES DE ConsulKVConfigManager
# ============================================================================

class TestConsulKVConfigManager:
    """Testes do gerenciador de configurações"""

    @pytest.fixture
    def manager(self):
        """Fixture que cria um manager para cada teste"""
        return ConsulKVConfigManager(ttl_seconds=300)

    def test_initialization(self, manager):
        """Testa inicialização do manager"""
        assert manager.prefix == "skills/eye/"
        assert manager.ttl_seconds == 300
        assert manager._cache == {}

    def test_full_key_adds_prefix(self, manager):
        """Testa que _full_key adiciona prefixo"""
        key = "monitoring-types/cache"
        full = manager._full_key(key)

        assert full == "skills/eye/monitoring-types/cache"

    def test_full_key_no_double_prefix(self, manager):
        """Testa que não adiciona prefixo duplicado"""
        key = "skills/eye/monitoring-types/cache"
        full = manager._full_key(key)

        assert full == "skills/eye/monitoring-types/cache"
        assert full.count("skills/eye/") == 1

    @pytest.mark.asyncio
    async def test_get_cache_miss(self, manager):
        """Testa GET com cache miss - deve buscar do KV"""
        key = "test/key"
        expected_data = {"test": "value"}

        # Mock do KV manager
        manager.kv_manager.get_json = AsyncMock(return_value=expected_data)

        # GET sem cache
        result = await manager.get(key)

        # Validações
        assert result == expected_data
        manager.kv_manager.get_json.assert_called_once_with("skills/eye/test/key")
        assert "skills/eye/test/key" in manager._cache

    @pytest.mark.asyncio
    async def test_get_cache_hit(self, manager):
        """Testa GET com cache hit - não deve buscar do KV"""
        key = "test/key"
        cached_data = {"cached": "value"}

        # Popular cache manualmente
        manager._cache["skills/eye/test/key"] = CachedValue(cached_data, 300)

        # Mock do KV manager (não deve ser chamado)
        manager.kv_manager.get_json = AsyncMock()

        # GET com cache
        result = await manager.get(key)

        # Validações
        assert result == cached_data
        manager.kv_manager.get_json.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_cache_expired(self, manager):
        """Testa GET com cache expirado - deve buscar do KV novamente"""
        key = "test/key"
        old_data = {"old": "value"}
        new_data = {"new": "value"}

        # Popular cache com valor expirado
        cached = CachedValue(old_data, 1)
        cached.timestamp = datetime.now() - timedelta(seconds=2)  # Expirado
        manager._cache["skills/eye/test/key"] = cached

        # Mock do KV manager
        manager.kv_manager.get_json = AsyncMock(return_value=new_data)

        # GET com cache expirado
        result = await manager.get(key)

        # Validações
        assert result == new_data
        manager.kv_manager.get_json.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_without_cache(self, manager):
        """Testa GET com use_cache=False - sempre busca do KV"""
        key = "test/key"
        cached_data = {"cached": "value"}
        kv_data = {"kv": "value"}

        # Popular cache
        manager._cache["skills/eye/test/key"] = CachedValue(cached_data, 300)

        # Mock do KV manager
        manager.kv_manager.get_json = AsyncMock(return_value=kv_data)

        # GET sem usar cache
        result = await manager.get(key, use_cache=False)

        # Validações
        assert result == kv_data
        manager.kv_manager.get_json.assert_called_once()

    @pytest.mark.asyncio
    async def test_put(self, manager):
        """Testa PUT - salva no KV e atualiza cache"""
        key = "test/key"
        data = {"test": "value"}

        # Mock do KV manager
        manager.kv_manager.put_json = AsyncMock(return_value=True)

        # PUT
        success = await manager.put(key, data)

        # Validações
        assert success is True
        manager.kv_manager.put_json.assert_called_once_with("skills/eye/test/key", data)
        assert "skills/eye/test/key" in manager._cache
        assert manager._cache["skills/eye/test/key"].value == data

    @pytest.mark.asyncio
    async def test_put_updates_cache(self, manager):
        """Testa que PUT atualiza cache existente"""
        key = "test/key"
        old_data = {"old": "value"}
        new_data = {"new": "value"}

        # Popular cache com valor antigo
        manager._cache["skills/eye/test/key"] = CachedValue(old_data, 300)

        # Mock do KV manager
        manager.kv_manager.put_json = AsyncMock(return_value=True)

        # PUT com novo valor
        await manager.put(key, new_data)

        # Validações
        assert manager._cache["skills/eye/test/key"].value == new_data

    def test_invalidate(self, manager):
        """Testa invalidação de cache"""
        key = "test/key"

        # Popular cache
        manager._cache["skills/eye/test/key"] = CachedValue({"test": "value"}, 300)

        # Invalidar
        manager.invalidate(key)

        # Validações
        assert "skills/eye/test/key" not in manager._cache

    def test_invalidate_nonexistent_key(self, manager):
        """Testa invalidação de chave inexistente (não deve dar erro)"""
        key = "nonexistent/key"

        # Não deve dar erro
        manager.invalidate(key)

    def test_clear_cache(self, manager):
        """Testa limpeza completa do cache"""
        # Popular cache com múltiplas chaves
        manager._cache["key1"] = CachedValue({"data": 1}, 300)
        manager._cache["key2"] = CachedValue({"data": 2}, 300)
        manager._cache["key3"] = CachedValue({"data": 3}, 300)

        # Limpar cache
        manager.clear_cache()

        # Validações
        assert len(manager._cache) == 0

    @pytest.mark.asyncio
    async def test_get_or_compute_cache_hit(self, manager):
        """Testa get_or_compute com cache hit"""
        key = "test/key"
        cached_data = {"cached": "value"}

        # Popular cache
        manager._cache["skills/eye/test/key"] = CachedValue(cached_data, 300)

        # Função de computação (não deve ser chamada)
        compute_fn = AsyncMock()

        # GET
        result = await manager.get_or_compute(key, compute_fn)

        # Validações
        assert result == cached_data
        compute_fn.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_or_compute_cache_miss(self, manager):
        """Testa get_or_compute com cache miss - executa compute_fn"""
        key = "test/key"
        computed_data = {"computed": "value"}

        # Função de computação
        async def compute_fn():
            return computed_data

        # GET (cache vazio)
        result = await manager.get_or_compute(key, compute_fn)

        # Validações
        assert result == computed_data
        assert "skills/eye/test/key" in manager._cache
        assert manager._cache["skills/eye/test/key"].value == computed_data

    def test_get_cache_stats(self, manager):
        """Testa estatísticas do cache"""
        # Cache vazio
        stats = manager.get_cache_stats()
        assert stats["cached_keys"] == 0

        # Adicionar itens ao cache
        manager._cache["key1"] = CachedValue({"data": 1}, 300)
        manager._cache["key2"] = CachedValue({"data": 2}, 300)

        # Verificar stats
        stats = manager.get_cache_stats()
        assert stats["cached_keys"] == 2


# ============================================================================
# EXECUTAR TESTES
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
