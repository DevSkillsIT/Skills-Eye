# SPRINT 2 - PLANO COMPLETO REVISADO (OFICIAL)

**Data**: 2025-11-15
**Prerequisito**: SPRINT 1 concluído
**Status**: 🎯 **ANÁLISE COMPLETA - PRONTO PARA IMPLEMENTAÇÃO**

---

## 🔴 DESCOBERTAS CRÍTICAS NA REVISÃO FINAL

### **DESCOBERTA #1: Confusão entre METADATA e FIELDS**

**ESCLARECIMENTO IMPORTANTE**:

1. **`_metadata`** (performance info do backend):
   ```python
   # Retornado por get_all_services_catalog()
   {
       "source_node": "172.16.1.26",
       "source_name": "Palmas",
       "is_master": True,
       "cache_status": "HIT",
       "age_seconds": 0,
       "staleness_ms": 15,
       "total_time_ms": 450
   }
   ```

2. **`metadata/fields`** (configuração KV de campos disponíveis):
   ```json
   // KV: skills/eye/metadata/fields
   {
       "fields": [
           {"name": "company", "display_name": "Empresa", "field_type": "string"},
           {"name": "site", "display_name": "Site", "field_type": "string"},
           {"name": "env", "display_name": "Ambiente", "field_type": "string"}
       ]
   }
   ```

**SÃO COISAS DIFERENTES!**
- `_metadata` → Info de **PERFORMANCE** (cache, fallback)
- KV fields → **CONFIGURAÇÃO** de colunas disponíveis

---

### **DESCOBERTA #2: Erro KV Persistente em TODOS os Testes**

```
ERROR - ❌ Erro ao carregar sites do KV: 'str' object has no attribute 'get'
RuntimeWarning: coroutine 'KVManager.get_json' was never awaited
```

**CAUSA RAIZ IDENTIFICADA**:
- `Config.py` linha 80 chama `KVManager.get_json()` de forma **SÍNCRONA**
- `KVManager.get_json()` é **ASYNC**!
- Resultado: retorna **coroutine** (str representation) ao invés de dict

---

### **DESCOBERTA #3: Frontend NÃO Consome Novos Recursos**

**Páginas que chamam APIs antigas e precisam atualização**:

1. ❌ **Services.tsx** - Usa `/services?node_addr=ALL`
   - Backend usa `get_all_services_catalog()` ✅
   - Frontend recebe corretamente ✅
   - Mas **NÃO captura `_metadata`** ❌

2. ❌ **BlackboxTargets.tsx** - Usa `/blackbox/targets`
   - Backend usa `get_all_services_catalog()` ✅
   - Frontend **NÃO captura `_metadata`** ❌

3. ❌ **DynamicMonitoringPage.tsx** - Usa `/monitoring/data`
   - Backend retorna `_metadata` ✅
   - Frontend **NÃO captura `_metadata`** ❌

4. ❌ **Dashboard.tsx** - Usa múltiplos endpoints
   - Precisa exibir status geral do sistema

---

## 🎯 SPRINT 2 - OBJETIVOS COMPLETOS

### **OBJETIVO 1: CORRIGIR GAPS DO SPRINT 1**
1. ✅ Corrigir erro KV (async/await)
2. ✅ Capturar `_metadata` em TODAS as páginas
3. ✅ Exibir indicadores visuais (cache, fallback, performance)

### **OBJETIVO 2: OBSERVABILIDADE COMPLETA**
1. ✅ Endpoint `/metrics` para Prometheus scraping
2. ✅ Dashboard de métricas tempo real
3. ✅ Página System Health (nodes Consul)
4. ✅ Histórico de eventos de fallback

### **OBJETIVO 3: PERFORMANCE**
1. ✅ Cache local backend (TTL 60s)
2. ✅ Reduzir 1289ms → ~10ms
3. ✅ Benchmark e validação

### **OBJETIVO 4: UX/UI**
1. ✅ Badges de status (cache/fallback)
2. ✅ Alertas quando master offline
3. ✅ Indicador de performance em tempo real
4. ✅ Tema consistente

---

## 📋 IMPLEMENTAÇÃO DETALHADA

---

## **PARTE 1: CORREÇÕES CRÍTICAS DO SPRINT 1**

### **TAREFA 1.1: Corrigir Erro KV Async/Await**

**Problema**: `Config.py` chama `get_json()` de forma síncrona

**Arquivo**: `backend/core/config.py`

**Localização**: Linha ~72-80

**Código Atual (ERRADO)**:
```python
from core.kv_manager import KVManager

def load_sites_from_kv() -> dict:
    """Carrega sites do KV"""
    try:
        kv = KVManager()
        # ❌ ERRO: get_json() é async mas está sendo chamado sync!
        sites_data = kv.get_json('skills/eye/metadata/sites')
        return sites_data if sites_data else {}
    except Exception as e:
        logger.error(f"❌ Erro ao carregar sites do KV: {e}")
        return {}
```

**Correção**:
```python
import asyncio
from core.kv_manager import KVManager

def load_sites_from_kv() -> dict:
    """
    Carrega sites do KV de forma SÍNCRONA (wrapper para async)

    CORREÇÃO SPRINT 2: Envolver chamada async em asyncio.run()
    """
    try:
        kv = KVManager()

        # ✅ CORRETO: Executar async em contexto síncrono
        sites_data = asyncio.run(kv.get_json('skills/eye/metadata/sites'))

        return sites_data if sites_data else {}
    except Exception as e:
        logger.error(f"❌ Erro ao carregar sites do KV: {e}")
        return {}
```

**IMPORTANTE**: Se `Config.py` for chamado em contexto async, usar:
```python
async def load_sites_from_kv() -> dict:
    """Versão async"""
    try:
        kv = KVManager()
        sites_data = await kv.get_json('skills/eye/metadata/sites')
        return sites_data if sites_data else {}
    except Exception as e:
        logger.error(f"❌ Erro ao carregar sites do KV: {e}")
        return {}
```

---

### **TAREFA 1.2: Validar get_kv_json() Retorna Dict**

**Arquivo**: `backend/core/kv_manager.py`

**Garantir que SEMPRE retorna dict/list, NUNCA str**:

```python
async def get_json(self, key: str) -> Optional[Union[dict, list]]:
    """
    Busca valor do KV e parseia como JSON

    SPRINT 2 CORREÇÃO: Garantir que SEMPRE retorna dict/list

    Returns:
        dict | list | None - NUNCA retorna str!
    """
    try:
        response = await self._request("GET", f"/kv/{key}")
        data = response.json()

        if not data or len(data) == 0:
            logger.debug(f"[KV] Key '{key}' não encontrada")
            return None

        # data é lista de {Key, Value, Flags, ...}
        item = data[0]
        value_b64 = item.get("Value")

        if not value_b64:
            logger.warning(f"[KV] Key '{key}' existe mas Value está vazio")
            return None

        # Decode base64
        import base64
        import json
        value_decoded = base64.b64decode(value_b64).decode('utf-8')

        # ✅ CRÍTICO: Parse JSON SEMPRE!
        try:
            parsed = json.loads(value_decoded)

            # ✅ VALIDAÇÃO: Garantir que é dict ou list
            if not isinstance(parsed, (dict, list)):
                logger.error(f"[KV] Key '{key}' retornou tipo inválido: {type(parsed)}")
                return None

            return parsed

        except json.JSONDecodeError as e:
            logger.error(f"[KV] Key '{key}' não é JSON válido: {e}")
            logger.debug(f"[KV] Conteúdo: {value_decoded[:200]}")
            return None

    except Exception as e:
        logger.error(f"[KV] Erro ao buscar '{key}': {e}")
        return None
```

---

### **TAREFA 1.3: Capturar `_metadata` no Frontend**

**Arquivos Afetados**:
1. `frontend/src/pages/DynamicMonitoringPage.tsx`
2. `frontend/src/pages/Services.tsx`
3. `frontend/src/pages/BlackboxTargets.tsx`

**Padrão de Implementação**:

```typescript
// 1. Adicionar estado para metadata
const [responseMetadata, setResponseMetadata] = useState<{
  source_name?: string;
  is_master?: boolean;
  cache_status?: string;
  age_seconds?: number;
  staleness_ms?: number;
  total_time_ms?: number;
} | null>(null);

// 2. No requestHandler ou fetchData:
const response = await consulAPI.getMonitoringData(category, ...);

// ✅ EXTRAIR METADATA
if (response.metadata) {
  setResponseMetadata(response.metadata);

  console.log(`[METADATA] Source: ${response.metadata.source_name}`);
  console.log(`[METADATA] Master: ${response.metadata.is_master}`);
  console.log(`[METADATA] Cache: ${response.metadata.cache_status}`);
  console.log(`[METADATA] Time: ${response.metadata.total_time_ms}ms`);
}

const rows = response.data || [];

// 3. Passar metadata para BadgeStatus component
<BadgeStatus metadata={responseMetadata} />
```

---

### **TAREFA 1.4: Criar Componente BadgeStatus**

**Arquivo**: `frontend/src/components/BadgeStatus.tsx`

```typescript
import React from 'react';
import { Space, Tag, Tooltip } from 'antd';
import {
  CheckCircleOutlined,
  ClockCircleOutlined,
  ThunderboltOutlined,
  WarningOutlined,
  DatabaseOutlined
} from '@ant-design/icons';

interface ResponseMetadata {
  source_name?: string;
  is_master?: boolean;
  cache_status?: string;
  age_seconds?: number;
  staleness_ms?: number;
  total_time_ms?: number;
  attempts?: number;
}

interface BadgeStatusProps {
  metadata: ResponseMetadata | null;
  showAll?: boolean; // Se false, mostra apenas warnings
}

export const BadgeStatus: React.FC<BadgeStatusProps> = ({
  metadata,
  showAll = true
}) => {
  if (!metadata) return null;

  const isMaster = metadata.is_master ?? true;
  const cacheStatus = metadata.cache_status || 'MISS';
  const cacheAge = metadata.age_seconds || 0;
  const staleness = metadata.staleness_ms || 0;
  const responseTime = metadata.total_time_ms || 0;
  const attempts = metadata.attempts || 1;

  // Se showAll=false, só mostra problemas
  if (!showAll && isMaster && cacheStatus === 'HIT' && staleness < 1000) {
    return null;
  }

  return (
    <Space size="small" wrap>
      {/* Fallback Warning (sempre mostra se não for master) */}
      {!isMaster && (
        <Tooltip title={`Master offline! Usando fallback: ${metadata.source_name} (tentativa ${attempts})`}>
          <Tag
            icon={<WarningOutlined />}
            color="warning"
          >
            Fallback: {metadata.source_name}
          </Tag>
        </Tooltip>
      )}

      {/* Master OK (só se showAll=true) */}
      {isMaster && showAll && (
        <Tooltip title={`Dados do master: ${metadata.source_name}`}>
          <Tag
            icon={<CheckCircleOutlined />}
            color="success"
          >
            {metadata.source_name}
          </Tag>
        </tooltip>
      )}

      {/* Cache Status */}
      {showAll && (
        <Tooltip title={`Agent Caching ${cacheStatus} (Age: ${cacheAge}s)`}>
          <Tag
            icon={<DatabaseOutlined />}
            color={cacheStatus === 'HIT' ? 'blue' : 'default'}
          >
            {cacheStatus === 'HIT' ? `Cache HIT (${cacheAge}s)` : 'Cache MISS'}
          </Tag>
        </Tooltip>
      )}

      {/* Staleness Warning */}
      {staleness > 1000 && (
        <Tooltip title={`Dados com ${staleness}ms de lag do leader`}>
          <Tag icon={<ClockCircleOutlined />} color="orange">
            Stale: {staleness}ms
          </Tag>
        </Tooltip>
      )}

      {/* Performance */}
      {showAll && (
        <Tooltip title="Tempo de resposta total">
          <Tag
            icon={<ThunderboltOutlined />}
            color={responseTime < 500 ? 'green' : responseTime < 2000 ? 'orange' : 'red'}
          >
            {responseTime}ms
          </Tag>
        </Tooltip>
      )}
    </Space>
  );
};

export default BadgeStatus;
```

---

## **PARTE 2: OBSERVABILIDADE COMPLETA**

### **TAREFA 2.1: Endpoint /metrics para Prometheus**

**Arquivo**: `backend/app.py`

```python
from fastapi.responses import Response
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

@app.get("/metrics", tags=["Metrics"], include_in_schema=True)
async def prometheus_metrics():
    """
    Endpoint para Prometheus scraping

    Expõe métricas do SPRINT 1:
    - consul_cache_hits_total{endpoint, age_bucket}
    - consul_stale_responses_total{endpoint, lag_bucket}
    - consul_api_calls_total{api_type}
    - consul_request_duration_seconds{method, endpoint, node}
    - consul_requests_total{method, endpoint, node, status}
    - consul_nodes_available
    - consul_fallback_total{from_node, to_node}

    Exemplo de scrape config:
    ```yaml
    scrape_configs:
      - job_name: 'skills-eye'
        static_configs:
          - targets: ['localhost:5000']
    ```
    """
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )
```

---

### **TAREFA 2.2: Cache Local Backend (TTL 60s)**

**Criar**: `backend/core/cache_manager.py`

```python
"""
Cache Manager - Cache local em memória com TTL

SPRINT 2 - 2025-11-15
Reduz 1289ms → ~10ms em requests repetidas
"""
from typing import Any, Optional, Dict, Tuple
from datetime import datetime, timedelta
import asyncio
import logging

logger = logging.getLogger(__name__)


class LocalCache:
    """
    Cache local thread-safe com TTL configurável

    Features:
    - TTL por item
    - Lock para thread-safety (asyncio.Lock)
    - Estatísticas (hits/misses)
    - Auto-cleanup de itens expirados
    """

    def __init__(self, default_ttl_seconds: int = 60):
        self.default_ttl = default_ttl_seconds
        self._cache: Dict[str, Tuple[Any, datetime, int]] = {}  # {key: (value, timestamp, ttl)}
        self._lock = asyncio.Lock()
        self._stats = {"hits": 0, "misses": 0, "sets": 0}

    async def get(self, key: str) -> Optional[Any]:
        """
        Busca valor do cache

        Returns:
            Value se encontrado e não expirado, None caso contrário
        """
        async with self._lock:
            if key not in self._cache:
                self._stats["misses"] += 1
                logger.debug(f"[CACHE MISS] {key}")
                return None

            value, timestamp, ttl = self._cache[key]

            # Verificar TTL
            age = (datetime.now() - timestamp).total_seconds()
            if age > ttl:
                del self._cache[key]
                self._stats["misses"] += 1
                logger.debug(f"[CACHE EXPIRED] {key} (age: {age:.1f}s > TTL: {ttl}s)")
                return None

            self._stats["hits"] += 1
            logger.debug(f"[CACHE HIT] {key} (age: {age:.1f}s)")
            return value

    async def set(self, key: str, value: Any, ttl: Optional[int] = None):
        """
        Armazena valor no cache

        Args:
            key: Chave do cache
            value: Valor a armazenar
            ttl: TTL em segundos (usa default se None)
        """
        async with self._lock:
            ttl_seconds = ttl if ttl is not None else self.default_ttl
            self._cache[key] = (value, datetime.now(), ttl_seconds)
            self._stats["sets"] += 1
            logger.debug(f"[CACHE SET] {key} (TTL: {ttl_seconds}s)")

    async def invalidate(self, key: str) -> bool:
        """Invalida item específico"""
        async with self._lock:
            if key in self._cache:
                del self._cache[key]
                logger.info(f"[CACHE INVALIDATE] {key}")
                return True
            return False

    async def clear(self):
        """Limpa todo o cache"""
        async with self._lock:
            count = len(self._cache)
            self._cache.clear()
            logger.info(f"[CACHE CLEAR] Removidos {count} itens")

    async def cleanup_expired(self):
        """Remove itens expirados (executar periodicamente)"""
        async with self._lock:
            now = datetime.now()
            expired_keys = []

            for key, (value, timestamp, ttl) in self._cache.items():
                age = (now - timestamp).total_seconds()
                if age > ttl:
                    expired_keys.append(key)

            for key in expired_keys:
                del self._cache[key]

            if expired_keys:
                logger.info(f"[CACHE CLEANUP] Removidos {len(expired_keys)} itens expirados")

    def get_stats(self) -> dict:
        """Retorna estatísticas do cache"""
        total_requests = self._stats["hits"] + self._stats["misses"]
        hit_rate = (self._stats["hits"] / total_requests * 100) if total_requests > 0 else 0

        return {
            "hits": self._stats["hits"],
            "misses": self._stats["misses"],
            "sets": self._stats["sets"],
            "total_requests": total_requests,
            "hit_rate_percent": round(hit_rate, 2),
            "current_size": len(self._cache)
        }


# Singleton global para cache de serviços do Catalog API
_catalog_cache = LocalCache(default_ttl_seconds=60)


async def get_catalog_cache() -> LocalCache:
    """Retorna instância global do cache"""
    return _catalog_cache
```

---

### **TAREFA 2.3: Integrar Cache em get_all_services_catalog()**

**Arquivo**: `backend/core/consul_manager.py`

**Modificar função** (linha ~935):

```python
from core.cache_manager import get_catalog_cache

async def get_all_services_catalog(
    self,
    use_fallback: bool = True,
    use_local_cache: bool = True  # ✅ NOVO parâmetro
) -> Dict[str, Dict]:
    """
    ✅ NOVA ABORDAGEM - Usa /catalog/services com fallback

    SPRINT 2 MELHORIAS (2025-11-15):
    - ✅ Cache local (TTL 60s) reduz 1289ms → ~10ms
    - ✅ Invalidação manual via endpoint
    - ✅ Estatísticas de cache

    Args:
        use_fallback: Se True, tenta master → clients (default: True)
        use_local_cache: Se True, usa cache local 60s (default: True)
    """
    cache_key = f"catalog:all_services:fallback={use_fallback}"

    # ✅ SPRINT 2: Tentar cache local primeiro
    if use_local_cache:
        cache = await get_catalog_cache()
        cached_result = await cache.get(cache_key)

        if cached_result:
            logger.info(f"[LOCAL CACHE HIT] Retornando dados cached (evita 1289ms de latência)")
            return cached_result

    # Cache MISS - buscar do Consul
    logger.debug(f"[LOCAL CACHE MISS] Buscando do Consul...")

    if use_fallback:
        # ... código existente de fallback ...
        services_catalog, metadata = await self.get_services_with_fallback()

        # ... resto do código existente ...

        all_services["_metadata"] = metadata

        # ✅ SPRINT 2: Armazenar no cache local
        if use_local_cache:
            cache = await get_catalog_cache()
            await cache.set(cache_key, all_services, ttl=60)

        logger.info(
            f"[Catalog] ✅ Retornados {sum(len(svcs) for k, svcs in all_services.items() if k != '_metadata')} "
            f"serviços de {len(all_services) - 1} nodes"
        )

        return all_services
    else:
        # Modo sem fallback (legado)
        # ... código existente ...
```

---

### **TAREFA 2.4: Endpoint de Invalidação de Cache**

**Arquivo**: `backend/app.py`

```python
from core.cache_manager import get_catalog_cache

@app.post("/api/v1/cache/invalidate", tags=["Cache"])
async def invalidate_cache(key: Optional[str] = None):
    """
    Invalida cache local

    Args:
        key: Chave específica para invalidar (None = limpa tudo)

    Returns:
        Estatísticas do cache após invalidação
    """
    cache = await get_catalog_cache()

    if key:
        invalidated = await cache.invalidate(key)
        message = f"Cache invalidado: {key}" if invalidated else f"Key não encontrada: {key}"
    else:
        await cache.clear()
        message = "Cache completamente limpo"

    stats = cache.get_stats()

    return {
        "success": True,
        "message": message,
        "stats": stats
    }

@app.get("/api/v1/cache/stats", tags=["Cache"])
async def get_cache_stats():
    """
    Retorna estatísticas do cache local

    Returns:
        hits, misses, hit_rate, current_size
    """
    cache = await get_catalog_cache()
    stats = cache.get_stats()

    return {
        "success": True,
        "stats": stats
    }
```

---

## **PARTE 3: DASHBOARDS FRONTEND**

### **TAREFA 3.1: Página Metrics Dashboard**

**Criar**: `frontend/src/pages/MetricsDashboard.tsx`

```typescript
import React, { useState, useEffect } from 'react';
import { Card, Col, Row, Statistic, Alert, Spin } from 'antd';
import { Line, Pie } from '@ant-design/charts';
import { PageContainer, ProCard } from '@ant-design/pro-components';
import {
  ClockCircleOutlined,
  DatabaseOutlined,
  ThunderboltOutlined,
  WarningOutlined
} from '@ant-design/icons';

export default function MetricsDashboard() {
  const [metrics, setMetrics] = useState<any>(null);
  const [cacheStats, setCacheStats] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchAllMetrics();

    // Atualizar a cada 10 segundos
    const interval = setInterval(fetchAllMetrics, 10000);
    return () => clearInterval(interval);
  }, []);

  const fetchAllMetrics = async () => {
    setLoading(true);
    setError(null);

    try {
      // Fetch Prometheus metrics
      const metricsResponse = await fetch('http://localhost:5000/metrics');
      const metricsText = await metricsResponse.text();
      const parsed = parsePrometheusMetrics(metricsText);
      setMetrics(parsed);

      // Fetch cache stats
      const cacheResponse = await fetch('http://localhost:5000/api/v1/cache/stats');
      const cacheData = await cacheResponse.json();
      setCacheStats(cacheData.stats);

    } catch (err) {
      console.error('Erro ao buscar métricas:', err);
      setError('Erro ao carregar métricas. Verifique se o backend está rodando.');
    } finally {
      setLoading(false);
    }
  };

  const parsePrometheusMetrics = (text: string) => {
    const lines = text.split('\n');
    const result: any = {
      cache_hits: {},
      stale_responses: {},
      api_calls: {},
      fallback_events: 0
    };

    lines.forEach(line => {
      // Parse consul_cache_hits_total
      if (line.startsWith('consul_cache_hits_total{')) {
        const bucketMatch = line.match(/age_bucket="(\w+)"/);
        const valueMatch = line.match(/(\d+)$/);
        if (bucketMatch && valueMatch) {
          const bucket = bucketMatch[1];
          const value = parseInt(valueMatch[1]);
          result.cache_hits[bucket] = (result.cache_hits[bucket] || 0) + value;
        }
      }

      // Parse consul_stale_responses_total
      if (line.startsWith('consul_stale_responses_total{')) {
        const bucketMatch = line.match(/lag_bucket="([\w\-\>]+)"/);
        const valueMatch = line.match(/(\d+)$/);
        if (bucketMatch && valueMatch) {
          const bucket = bucketMatch[1];
          const value = parseInt(valueMatch[1]);
          result.stale_responses[bucket] = (result.stale_responses[bucket] || 0) + value;
        }
      }

      // Parse consul_api_calls_total
      if (line.startsWith('consul_api_calls_total{')) {
        const typeMatch = line.match(/api_type="(\w+)"/);
        const valueMatch = line.match(/(\d+)$/);
        if (typeMatch && valueMatch) {
          const type = typeMatch[1];
          const value = parseInt(valueMatch[1]);
          result.api_calls[type] = (result.api_calls[type] || 0) + value;
        }
      }

      // Parse consul_fallback_total
      if (line.startsWith('consul_fallback_total')) {
        const valueMatch = line.match(/(\d+)$/);
        if (valueMatch) {
          result.fallback_events += parseInt(valueMatch[1]);
        }
      }
    });

    return result;
  };

  if (error) {
    return (
      <PageContainer>
        <Alert
          message="Erro ao Carregar Métricas"
          description={error}
          type="error"
          showIcon
        />
      </PageContainer>
    );
  }

  const totalCacheHits = metrics
    ? Object.values(metrics.cache_hits).reduce((sum: number, val: any) => sum + val, 0)
    : 0;

  const totalApiCalls = metrics
    ? Object.values(metrics.api_calls).reduce((sum: number, val: any) => sum + val, 0)
    : 0;

  return (
    <PageContainer
      header={{
        title: 'Metrics Dashboard',
        subTitle: 'Monitoramento em tempo real do Skills Eye'
      }}
    >
      <Spin spinning={loading}>
        <Row gutter={[16, 16]}>
          {/* KPIs Principais */}
          <Col xs={24} sm={12} lg={6}>
            <Card>
              <Statistic
                title="Cache Hit Rate"
                value={cacheStats?.hit_rate_percent || 0}
                suffix="%"
                prefix={<DatabaseOutlined />}
                valueStyle={{
                  color: (cacheStats?.hit_rate_percent || 0) > 80 ? '#3f8600' : '#cf1322'
                }}
              />
            </Card>
          </Col>

          <Col xs={24} sm={12} lg={6}>
            <Card>
              <Statistic
                title="Total Cache Hits"
                value={totalCacheHits}
                prefix={<ClockCircleOutlined />}
              />
            </Card>
          </Col>

          <Col xs={24} sm={12} lg={6}>
            <Card>
              <Statistic
                title="Fallback Events"
                value={metrics?.fallback_events || 0}
                prefix={<WarningOutlined />}
                valueStyle={{
                  color: (metrics?.fallback_events || 0) > 0 ? '#cf1322' : '#3f8600'
                }}
              />
            </Card>
          </Col>

          <Col xs={24} sm={12} lg={6}>
            <Card>
              <Statistic
                title="Total API Calls"
                value={totalApiCalls}
                prefix={<ThunderboltOutlined />}
              />
            </Card>
          </Col>

          {/* Gráfico: Cache Hits por Age Bucket */}
          <Col xs={24} lg={12}>
            <ProCard title="Cache Hits por Freshness" bordered>
              {metrics && Object.keys(metrics.cache_hits).length > 0 ? (
                <Pie
                  data={Object.entries(metrics.cache_hits).map(([bucket, count]) => ({
                    type: bucket,
                    value: count as number
                  }))}
                  angleField="value"
                  colorField="type"
                  radius={0.8}
                  label={{
                    type: 'outer',
                    content: '{name}: {percentage}'
                  }}
                  height={250}
                />
              ) : (
                <div style={{ textAlign: 'center', padding: '40px' }}>
                  Sem dados de cache
                </div>
              )}
            </ProCard>
          </Col>

          {/* Gráfico: API Calls por Tipo */}
          <Col xs={24} lg={12}>
            <ProCard title="API Calls por Tipo" bordered>
              {metrics && Object.keys(metrics.api_calls).length > 0 ? (
                <Pie
                  data={Object.entries(metrics.api_calls).map(([type, count]) => ({
                    type,
                    value: count as number
                  }))}
                  angleField="value"
                  colorField="type"
                  radius={0.8}
                  label={{
                    type: 'outer',
                    content: '{name}: {percentage}'
                  }}
                  height={250}
                />
              ) : (
                <div style={{ textAlign: 'center', padding: '40px' }}>
                  Sem dados de API calls
                </div>
              )}
            </ProCard>
          </Col>

          {/* Cache Local Stats */}
          <Col span={24}>
            <ProCard title="Cache Local (Backend)" bordered>
              <Row gutter={16}>
                <Col span={6}>
                  <Statistic title="Hits" value={cacheStats?.hits || 0} />
                </Col>
                <Col span={6}>
                  <Statistic title="Misses" value={cacheStats?.misses || 0} />
                </Col>
                <Col span={6}>
                  <Statistic title="Total Requests" value={cacheStats?.total_requests || 0} />
                </Col>
                <Col span={6}>
                  <Statistic title="Current Size" value={cacheStats?.current_size || 0} />
                </Col>
              </Row>
            </ProCard>
          </Col>
        </Row>
      </Spin>
    </PageContainer>
  );
}
```

---

### **TAREFA 3.2: Adicionar Rotas no App.tsx**

**Arquivo**: `frontend/src/App.tsx`

```typescript
import MetricsDashboard from './pages/MetricsDashboard';
import { DashboardOutlined } from '@ant-design/icons';

// Na configuração de rotas (routes):
{
  path: '/metrics',
  name: 'Métricas',
  icon: <DashboardOutlined />,
  component: MetricsDashboard,
}
```

---

## ✅ CHECKLIST COMPLETO

### SPRINT 1 - CORREÇÕES:
- [ ] Corrigir erro KV async/await (Config.py)
- [ ] Validar get_kv_json() retorna dict/list
- [ ] Capturar `_metadata` em DynamicMonitoringPage
- [ ] Capturar `_metadata` em Services.tsx
- [ ] Capturar `_metadata` em BlackboxTargets.tsx
- [ ] Criar componente BadgeStatus
- [ ] Integrar BadgeStatus em todas as páginas

### SPRINT 2 - BACKEND:
- [ ] Endpoint /metrics para Prometheus
- [ ] Criar LocalCache manager
- [ ] Integrar cache em get_all_services_catalog()
- [ ] Endpoint /api/v1/cache/invalidate
- [ ] Endpoint /api/v1/cache/stats

### SPRINT 2 - FRONTEND:
- [ ] Página MetricsDashboard.tsx
- [ ] Adicionar rotas no App.tsx
- [ ] Testar integração end-to-end

### TESTES FINAIS:
- [ ] Teste cache local (1289ms → ~10ms)
- [ ] Teste endpoint /metrics
- [ ] Teste BadgeStatus renderização
- [ ] Teste MetricsDashboard atualização
- [ ] Benchmark completo antes/depois

---

## 🎯 RESULTADO ESPERADO FINAL

### Performance:
- **Primeira chamada**: 1289ms (Catalog API com paralelização)
- **Chamadas subsequentes**: **~10ms** (cache local HIT)
- **Cache hit rate**: >90% após 5 minutos

### Observabilidade:
- ✅ Dashboard tempo real (/metrics)
- ✅ Badges visuais (cache/fallback/performance)
- ✅ Estatísticas completas

### UX/UI:
- ✅ Usuário vê origem dos dados (master/fallback)
- ✅ Usuário vê status do cache (HIT/MISS/age)
- ✅ Usuário vê performance real
- ✅ Alertas quando master offline

---

**PRONTO PARA IMPLEMENTAÇÃO COMPLETA!** 🚀

**Data**: 2025-11-15
**Status**: ✅ PLANO VALIDADO E APROVADO
