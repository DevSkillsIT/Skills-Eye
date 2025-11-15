"""
LocalCache Manager - Cache em memória com TTL para reduzir latência

SPRINT 2 (2025-11-15)

OBJETIVO: Reduzir latência de 1289ms → ~10ms (128x mais rápido!)

ESTRATÉGIA:
- Cache local em memória (dict + asyncio.Lock)
- TTL padrão: 60 segundos
- Thread-safe para concorrência
- Invalidação manual via endpoint
- Estatísticas de hit/miss rate

IMPORTANTE: Este é um cache LOCAL de aplicação, diferente do Agent Caching
do Consul (que tem TTL de 3 dias). Este cache visa reduzir chamadas repetidas
em janelas curtas de tempo.
"""
import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger(__name__)


class LocalCache:
    """
    Cache local em memória com TTL configurável.

    Thread-safe usando asyncio.Lock.
    Armazena tupla: (value, timestamp, ttl)
    """

    def __init__(self, default_ttl_seconds: int = 60):
        """
        Inicializa cache local.

        Args:
            default_ttl_seconds: TTL padrão em segundos (padrão: 60s)
        """
        self._cache: Dict[str, Tuple[Any, datetime, int]] = {}
        self._lock = asyncio.Lock()
        self.default_ttl = default_ttl_seconds

        # Estatísticas
        self._stats = {
            "hits": 0,
            "misses": 0,
            "evictions": 0,
            "invalidations": 0,
        }

        logger.info(
            f"✅ LocalCache inicializado com TTL padrão: {default_ttl_seconds}s"
        )

    async def get(self, key: str) -> Optional[Any]:
        """
        Busca valor do cache.

        Args:
            key: Chave do cache

        Returns:
            Valor armazenado ou None se expirado/inexistente
        """
        async with self._lock:
            if key not in self._cache:
                self._stats["misses"] += 1
                logger.debug(f"[CACHE] ❌ MISS: {key}")
                return None

            value, timestamp, ttl = self._cache[key]
            age = (datetime.utcnow() - timestamp).total_seconds()

            # Verificar se expirou
            if age > ttl:
                # Remover entrada expirada
                del self._cache[key]
                self._stats["evictions"] += 1
                self._stats["misses"] += 1
                logger.debug(
                    f"[CACHE] ⏰ EXPIRED: {key} (age: {age:.1f}s > TTL: {ttl}s)"
                )
                return None

            # Cache hit!
            self._stats["hits"] += 1
            logger.debug(
                f"[CACHE] ✅ HIT: {key} (age: {age:.1f}s, TTL: {ttl}s restantes: {ttl - age:.1f}s)"
            )
            return value

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """
        Armazena valor no cache.

        Args:
            key: Chave do cache
            value: Valor a armazenar (qualquer tipo serializável)
            ttl: TTL customizado em segundos (None = usar default)
        """
        used_ttl = ttl if ttl is not None else self.default_ttl

        async with self._lock:
            self._cache[key] = (value, datetime.utcnow(), used_ttl)
            logger.debug(f"[CACHE] 💾 SET: {key} (TTL: {used_ttl}s)")

    async def invalidate(self, key: str) -> bool:
        """
        Remove uma chave do cache manualmente.

        Args:
            key: Chave a remover

        Returns:
            True se removido, False se não existia
        """
        async with self._lock:
            if key in self._cache:
                del self._cache[key]
                self._stats["invalidations"] += 1
                logger.info(f"[CACHE] 🗑️  INVALIDATED: {key}")
                return True
            return False

    async def invalidate_pattern(self, pattern: str) -> int:
        """
        Remove todas as chaves que correspondem a um padrão.

        Args:
            pattern: Padrão de busca (ex: "services:*")

        Returns:
            Número de chaves removidas
        """
        count = 0
        async with self._lock:
            keys_to_remove = [
                k for k in self._cache.keys() if self._matches_pattern(k, pattern)
            ]
            for key in keys_to_remove:
                del self._cache[key]
                count += 1
                self._stats["invalidations"] += 1

        if count > 0:
            logger.info(f"[CACHE] 🗑️  INVALIDATED {count} keys matching '{pattern}'")

        return count

    async def clear(self) -> int:
        """
        Limpa TODO o cache.

        Returns:
            Número de entradas removidas
        """
        async with self._lock:
            count = len(self._cache)
            self._cache.clear()
            self._stats["invalidations"] += count
            logger.warning(f"[CACHE] 🗑️  CLEARED all cache ({count} entries)")
            return count

    async def get_stats(self) -> Dict[str, Any]:
        """
        Retorna estatísticas do cache.

        Returns:
            Dict com hits, misses, evictions, invalidations, hit_rate, size
        """
        async with self._lock:
            total_requests = self._stats["hits"] + self._stats["misses"]
            hit_rate = (
                (self._stats["hits"] / total_requests * 100) if total_requests > 0 else 0
            )

            return {
                "hits": self._stats["hits"],
                "misses": self._stats["misses"],
                "evictions": self._stats["evictions"],
                "invalidations": self._stats["invalidations"],
                "hit_rate_percent": round(hit_rate, 2),
                "total_requests": total_requests,
                "current_size": len(self._cache),
                "ttl_seconds": self.default_ttl,
            }

    async def get_keys(self) -> list[str]:
        """
        Retorna lista de todas as chaves no cache (para debug).

        Returns:
            Lista de chaves
        """
        async with self._lock:
            return list(self._cache.keys())

    async def get_entry_info(self, key: str) -> Optional[Dict[str, Any]]:
        """
        Retorna informações detalhadas sobre uma entrada do cache.

        Args:
            key: Chave a consultar

        Returns:
            Dict com informações ou None se não existir
        """
        async with self._lock:
            if key not in self._cache:
                return None

            value, timestamp, ttl = self._cache[key]
            age = (datetime.utcnow() - timestamp).total_seconds()

            return {
                "key": key,
                "age_seconds": round(age, 2),
                "ttl_seconds": ttl,
                "remaining_seconds": round(max(0, ttl - age), 2),
                "is_expired": age > ttl,
                "timestamp": timestamp.isoformat(),
                "value_type": type(value).__name__,
                "value_size_bytes": len(str(value).encode('utf-8')),
            }

    def _matches_pattern(self, key: str, pattern: str) -> bool:
        """
        Verifica se chave corresponde ao padrão (suporta wildcards).

        Args:
            key: Chave a verificar
            pattern: Padrão (ex: "services:*", "*:cache")

        Returns:
            True se corresponde
        """
        if "*" not in pattern:
            return key == pattern

        # Converter padrão para regex simples
        import re
        regex_pattern = pattern.replace("*", ".*")
        return bool(re.match(f"^{regex_pattern}$", key))


# Instância global do cache (singleton)
_global_cache: Optional[LocalCache] = None


def get_cache(ttl_seconds: int = 60) -> LocalCache:
    """
    Retorna instância global do cache (singleton).

    Args:
        ttl_seconds: TTL padrão (usado apenas na primeira chamada)

    Returns:
        Instância de LocalCache
    """
    global _global_cache
    if _global_cache is None:
        _global_cache = LocalCache(default_ttl_seconds=ttl_seconds)
    return _global_cache


def reset_cache() -> None:
    """
    Reseta cache global (útil para testes).
    """
    global _global_cache
    _global_cache = None
    logger.warning("[CACHE] 🔄 Cache global resetado")
