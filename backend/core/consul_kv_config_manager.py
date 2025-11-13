"""
Consul KV Config Manager - Gerenciador Central de Configurações

RESPONSABILIDADES:
- Centralizar acesso ao Consul KV
- Cache inteligente com TTL
- Validação de dados com Pydantic
- Namespace automático (skills/eye/)

AUTOR: Sistema de Refatoração Skills Eye v2.0
DATA: 2025-11-13
"""

from typing import Optional, Dict, Any, TypeVar, Type
from datetime import datetime, timedelta
from pydantic import BaseModel
import logging
import json

from core.kv_manager import KVManager

logger = logging.getLogger(__name__)

T = TypeVar('T', bound=BaseModel)


class CachedValue:
    """
    Valor com timestamp para cache em memória

    Armazena valores junto com timestamp de criação e TTL,
    permitindo verificar se o cache expirou.
    """

    def __init__(self, value: Any, ttl_seconds: int):
        self.value = value
        self.timestamp = datetime.now()
        self.ttl_seconds = ttl_seconds

    def is_expired(self) -> bool:
        """Verifica se o valor em cache expirou"""
        age = datetime.now() - self.timestamp
        return age.total_seconds() > self.ttl_seconds


class ConsulKVConfigManager:
    """
    Gerenciador centralizado de configurações no Consul KV

    Features:
    - Cache em memória com TTL configurável
    - Validação automática com Pydantic
    - Namespace automático (skills/eye/)
    - Invalidação de cache seletiva

    Exemplo de Uso:
        ```python
        manager = ConsulKVConfigManager(ttl_seconds=300)  # 5 minutos

        # Salvar config
        await manager.put('monitoring-types/cache', types_data)

        # Ler config com cache
        data = await manager.get('monitoring-types/cache')

        # Invalidar cache
        manager.invalidate('monitoring-types/cache')
        ```

    IMPORTANTE:
    - NÃO adiciona prefixo 'skills/eye/' automaticamente
    - A key deve ser passada SEM o prefixo (ex: 'monitoring-types/cache')
    - O KVManager internamente já adiciona o prefixo correto
    """

    def __init__(self, prefix: str = "skills/eye/", ttl_seconds: int = 300):
        """
        Inicializa o gerenciador

        Args:
            prefix: Namespace raiz (padrão: skills/eye/)
            ttl_seconds: Tempo de vida do cache em segundos (padrão: 300 = 5 minutos)
        """
        self.prefix = prefix
        self.ttl_seconds = ttl_seconds
        self.kv_manager = KVManager()
        self._cache: Dict[str, CachedValue] = {}

    def _full_key(self, key: str) -> str:
        """
        Adiciona namespace ao key

        Args:
            key: Chave relativa (ex: 'monitoring-types/cache')

        Returns:
            Chave completa (ex: 'skills/eye/monitoring-types/cache')
        """
        # Se key já começa com o prefixo, não adicionar novamente
        if key.startswith(self.prefix):
            return key

        return f"{self.prefix}{key}"

    async def get(
        self,
        key: str,
        model: Optional[Type[T]] = None,
        use_cache: bool = True
    ) -> Optional[Any]:
        """
        Busca valor do KV com cache em memória

        Fluxo:
        1. Verifica cache em memória (se use_cache=True)
        2. Se cache válido (não expirado), retorna valor
        3. Se cache expirado ou inexistente, busca do Consul KV
        4. Valida com Pydantic se model fornecido
        5. Salva no cache e retorna

        Args:
            key: Chave (sem namespace, ex: 'monitoring-types/cache')
            model: Modelo Pydantic para validação (opcional)
            use_cache: Se deve usar cache em memória (padrão: True)

        Returns:
            Valor parseado ou None se não encontrado

        Exemplo:
            ```python
            # Sem validação
            data = await manager.get('monitoring-types/cache')

            # Com validação Pydantic
            class ConfigModel(BaseModel):
                version: str
                data: List[Dict]

            config = await manager.get('monitoring-types/cache', model=ConfigModel)
            ```
        """
        full_key = self._full_key(key)

        # PASSO 1: Tentar cache primeiro
        if use_cache and full_key in self._cache:
            cached = self._cache[full_key]
            if not cached.is_expired():
                logger.debug(f"[CACHE HIT] {key} (idade: {(datetime.now() - cached.timestamp).total_seconds():.1f}s)")
                return cached.value
            else:
                logger.debug(f"[CACHE EXPIRED] {key} (idade: {(datetime.now() - cached.timestamp).total_seconds():.1f}s)")
                del self._cache[full_key]

        # PASSO 2: Cache miss - buscar do Consul
        logger.debug(f"[CACHE MISS] {key} - buscando do Consul KV")
        value = await self.kv_manager.get_json(full_key)

        if value is None:
            logger.debug(f"[KV NOT FOUND] {key}")
            return None

        # PASSO 3: Validar com Pydantic se model fornecido
        if model:
            try:
                value = model(**value)
                logger.debug(f"[VALIDATION OK] {key} validado com {model.__name__}")
            except Exception as e:
                logger.error(f"[VALIDATION ERROR] {key} falhou validação: {e}")
                return None

        # PASSO 4: Salvar no cache
        if use_cache:
            self._cache[full_key] = CachedValue(value, self.ttl_seconds)
            logger.debug(f"[CACHE WRITE] {key} (TTL: {self.ttl_seconds}s)")

        return value

    async def put(
        self,
        key: str,
        value: Any,
        update_cache: bool = True
    ) -> bool:
        """
        Salva valor no KV e opcionalmente atualiza cache

        Args:
            key: Chave (sem namespace, ex: 'monitoring-types/cache')
            value: Valor (dict, list ou Pydantic model)
            update_cache: Se deve atualizar cache após salvar (padrão: True)

        Returns:
            True se salvou com sucesso

        Exemplo:
            ```python
            data = {
                "version": "1.0.0",
                "types": [...]
            }

            success = await manager.put('monitoring-types/cache', data)
            ```
        """
        full_key = self._full_key(key)

        # Converter Pydantic model para dict
        value_to_save = value
        if isinstance(value, BaseModel):
            value_to_save = value.dict()

        # Salvar no Consul
        success = await self.kv_manager.put_json(full_key, value_to_save)

        if success:
            logger.debug(f"[KV WRITE OK] {key}")

            # Atualizar cache com o novo valor (não invalidar!)
            # Isso evita uma busca extra ao KV na próxima leitura
            if update_cache:
                self._cache[full_key] = CachedValue(value_to_save, self.ttl_seconds)
                logger.debug(f"[CACHE UPDATED] {key} após PUT (TTL: {self.ttl_seconds}s)")
        else:
            logger.error(f"[KV WRITE FAILED] {key}")

        return success

    async def delete(self, key: str) -> bool:
        """
        Remove key do KV e invalida cache

        Args:
            key: Chave (sem namespace)

        Returns:
            True se removeu com sucesso
        """
        full_key = self._full_key(key)

        success = await self.kv_manager.delete_key(full_key)

        if success:
            logger.debug(f"[KV DELETE OK] {key}")
            self.invalidate(key)
        else:
            logger.error(f"[KV DELETE FAILED] {key}")

        return success

    def invalidate(self, key: str) -> None:
        """
        Invalida cache de um key específico

        Args:
            key: Chave (sem namespace)
        """
        full_key = self._full_key(key)
        if full_key in self._cache:
            del self._cache[full_key]
            logger.debug(f"[CACHE INVALIDATED] {key}")

    def invalidate_all(self) -> None:
        """Invalida todo o cache em memória"""
        count = len(self._cache)
        self._cache.clear()
        logger.info(f"[CACHE] {count} itens invalidados")

    def clear_cache(self) -> None:
        """
        Alias para invalidate_all() - mantido para backward compatibility

        Usado pelos testes e scripts que esperam este nome de método.
        """
        self.invalidate_all()

    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Retorna estatísticas do cache

        Returns:
            Dicionário com estatísticas:
            - total_items: Total de itens no cache
            - active_items: Itens não expirados
            - expired_items: Itens expirados mas ainda no cache
            - ttl_seconds: TTL configurado
        """
        total_items = len(self._cache)
        expired_items = sum(1 for v in self._cache.values() if v.is_expired())

        return {
            "total_items": total_items,
            "active_items": total_items - expired_items,
            "expired_items": expired_items,
            "ttl_seconds": self.ttl_seconds
        }

    async def get_or_compute(
        self,
        key: str,
        compute_fn,
        use_cache: bool = True
    ) -> Optional[Any]:
        """
        Busca valor do cache/KV ou computa se não existir

        Pattern útil para lazy loading de dados computados.

        Args:
            key: Chave (sem namespace)
            compute_fn: Função async que computa o valor se não encontrado
            use_cache: Se deve usar cache

        Returns:
            Valor do cache/KV ou resultado de compute_fn

        Exemplo:
            ```python
            async def extract_types():
                # Operação custosa (SSH, parsing, etc)
                return await extract_from_prometheus()

            types = await manager.get_or_compute(
                'monitoring-types/cache',
                extract_types
            )
            ```
        """
        # Tentar buscar do cache/KV
        value = await self.get(key, use_cache=use_cache)

        if value is not None:
            return value

        # Não encontrado - computar
        logger.info(f"[COMPUTE] {key} não encontrado, computando...")
        computed_value = await compute_fn()

        # Salvar no KV e atualizar cache
        if computed_value is not None:
            await self.put(key, computed_value, update_cache=True)
            logger.debug(f"[COMPUTE SAVED] {key} salvo no KV e cache")

        return computed_value
