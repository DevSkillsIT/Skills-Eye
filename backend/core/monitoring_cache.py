"""
Cache intermediario para dados de monitoramento - SPEC-PERF-002 FASE 1

RESPONSABILIDADES:
- Cache de dados do Consul com TTL configuravel (padrao 30s)
- Necessario porque Consul nao suporta paginacao nativa (Issue #9422)
- Permite paginacao, filtros e ordenacao server-side eficientes

ARQUITETURA:
- Cache em memoria com invalidacao por TTL
- Integracao com LocalCache global para consistencia
- Suporte a invalidacao manual por categoria

AUTOR: Backend Expert Agent
DATA: 2025-11-22
VERSION: 1.0.0
"""

import logging
import time
from typing import Any, Dict, List, Optional
from datetime import datetime

from core.cache_manager import get_cache

logger = logging.getLogger(__name__)


class MonitoringDataCache:
    """
    Cache com TTL para dados de monitoramento do Consul.

    IMPORTANTE: Consul nao suporta paginacao nativa (Issue #9422).
    Este cache permite:
    1. Armazenar todos os dados do Consul em memoria
    2. Aplicar filtros, ordenacao e paginacao server-side
    3. Reduzir chamadas repetidas ao Consul

    TTL padrao: 30 segundos (equilibrio entre freshness e performance)
    """

    def __init__(self, ttl_seconds: int = 30):
        """
        Inicializa cache de monitoramento.

        Args:
            ttl_seconds: Tempo de vida do cache em segundos (padrao: 30s)
        """
        self.ttl = ttl_seconds

        # Usar LocalCache global para consistencia com resto da aplicacao
        self._cache = get_cache(ttl_seconds=ttl_seconds)

        # Prefixo para chaves do cache de monitoramento
        self._prefix = "monitoring:data:"

        # Estatisticas especificas de monitoramento
        self._stats = {
            "requests": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "invalidations": 0
        }

        logger.info(
            f"[MonitoringDataCache] Inicializado com TTL={ttl_seconds}s"
        )

    def _make_key(self, category: str, node: Optional[str] = None) -> str:
        """
        Gera chave unica para o cache.

        Args:
            category: Categoria de monitoramento (ex: network-probes)
            node: IP do no para filtro (opcional)

        Returns:
            Chave no formato: monitoring:data:{category}:{node}
        """
        node_key = node if node and node != 'all' else 'all'
        return f"{self._prefix}{category}:{node_key}"

    async def get_data(
        self,
        category: str,
        node: Optional[str] = None
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Retorna dados do cache se disponiveis e validos.

        Args:
            category: Categoria de monitoramento
            node: IP do no para filtro (opcional)

        Returns:
            Lista de servicos do cache ou None se expirado/inexistente
        """
        self._stats["requests"] += 1
        cache_key = self._make_key(category, node)

        # Tentar buscar do cache
        cached = await self._cache.get(cache_key)

        if cached is not None:
            self._stats["cache_hits"] += 1
            logger.debug(
                f"[MonitoringDataCache] HIT: category='{category}', node='{node}', "
                f"total={len(cached)} servicos"
            )
            return cached

        self._stats["cache_misses"] += 1
        logger.debug(
            f"[MonitoringDataCache] MISS: category='{category}', node='{node}'"
        )
        return None

    async def set_data(
        self,
        category: str,
        data: List[Dict[str, Any]],
        node: Optional[str] = None,
        ttl: Optional[int] = None
    ) -> None:
        """
        Armazena dados no cache.

        Args:
            category: Categoria de monitoramento
            data: Lista de servicos para armazenar
            node: IP do no para filtro (opcional)
            ttl: TTL customizado em segundos (None = usar padrao)
        """
        cache_key = self._make_key(category, node)
        used_ttl = ttl if ttl is not None else self.ttl

        await self._cache.set(cache_key, data, ttl=used_ttl)

        logger.debug(
            f"[MonitoringDataCache] SET: category='{category}', node='{node}', "
            f"total={len(data)} servicos, TTL={used_ttl}s"
        )

    async def invalidate(self, category: Optional[str] = None) -> int:
        """
        Invalida cache para refresh.

        Args:
            category: Categoria para invalidar (None = todas)

        Returns:
            Numero de entradas invalidadas
        """
        self._stats["invalidations"] += 1

        if category:
            # Invalidar apenas categoria especifica
            pattern = f"{self._prefix}{category}:*"
            count = await self._cache.invalidate_pattern(pattern)
            logger.info(
                f"[MonitoringDataCache] Invalidado: category='{category}', "
                f"entradas={count}"
            )
        else:
            # Invalidar todas as categorias de monitoramento
            pattern = f"{self._prefix}*"
            count = await self._cache.invalidate_pattern(pattern)
            logger.info(
                f"[MonitoringDataCache] Invalidado: TODAS categorias, "
                f"entradas={count}"
            )

        return count

    async def get_stats(self) -> Dict[str, Any]:
        """
        Retorna estatisticas do cache de monitoramento.

        Returns:
            Dict com requests, hits, misses, hit_rate
        """
        total = self._stats["requests"]
        hit_rate = (
            (self._stats["cache_hits"] / total * 100)
            if total > 0 else 0
        )

        return {
            "requests": self._stats["requests"],
            "cache_hits": self._stats["cache_hits"],
            "cache_misses": self._stats["cache_misses"],
            "invalidations": self._stats["invalidations"],
            "hit_rate_percent": round(hit_rate, 2),
            "ttl_seconds": self.ttl
        }


# Instancia global do cache de monitoramento (singleton)
_monitoring_cache: Optional[MonitoringDataCache] = None


def get_monitoring_cache(ttl_seconds: int = 30) -> MonitoringDataCache:
    """
    Retorna instancia global do cache de monitoramento (singleton).

    Args:
        ttl_seconds: TTL padrao (usado apenas na primeira chamada)

    Returns:
        Instancia de MonitoringDataCache
    """
    global _monitoring_cache
    if _monitoring_cache is None:
        _monitoring_cache = MonitoringDataCache(ttl_seconds=ttl_seconds)
    return _monitoring_cache


def reset_monitoring_cache() -> None:
    """
    Reseta cache global de monitoramento (util para testes).
    """
    global _monitoring_cache
    _monitoring_cache = None
    logger.warning("[MonitoringDataCache] Cache global resetado")
