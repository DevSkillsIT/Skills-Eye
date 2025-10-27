"""
Sistema de cache simples para otimizar performance
"""
from datetime import datetime, timedelta
from typing import Optional, Any, Dict
import threading

class CacheManager:
    """Gerenciador de cache em memória com TTL"""

    def __init__(self):
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()

    def get(self, key: str) -> Optional[Any]:
        """
        Recupera valor do cache se ainda válido

        Args:
            key: Chave do cache

        Returns:
            Valor cacheado ou None se expirado/inexistente
        """
        with self._lock:
            if key in self._cache:
                entry = self._cache[key]
                if datetime.now() < entry['expires_at']:
                    return entry['value']
                else:
                    # Cache expirado, remover
                    del self._cache[key]
            return None

    def set(self, key: str, value: Any, ttl_seconds: int = 60):
        """
        Armazena valor no cache com TTL

        Args:
            key: Chave do cache
            value: Valor a armazenar
            ttl_seconds: Tempo de vida em segundos (padrão: 60s)
        """
        with self._lock:
            self._cache[key] = {
                'value': value,
                'expires_at': datetime.now() + timedelta(seconds=ttl_seconds)
            }

    def delete(self, key: str):
        """Remove entrada do cache"""
        with self._lock:
            if key in self._cache:
                del self._cache[key]

    def clear(self):
        """Limpa todo o cache"""
        with self._lock:
            self._cache.clear()

    def cleanup_expired(self):
        """Remove entradas expiradas"""
        with self._lock:
            now = datetime.now()
            expired_keys = [
                key for key, entry in self._cache.items()
                if now >= entry['expires_at']
            ]
            for key in expired_keys:
                del self._cache[key]


# Instância global do cache
cache_manager = CacheManager()
