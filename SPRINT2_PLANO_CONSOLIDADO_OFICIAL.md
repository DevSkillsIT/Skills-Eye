# SPRINT 2 - PLANO CONSOLIDADO OFICIAL

**Data**: 2025-11-15
**Prerequisito**: SPRINT 1 concluído
**Status**: 🎯 PRONTO PARA IMPLEMENTAÇÃO

---

## 🔴 SPRINT 1 - GAPS CRÍTICOS ENCONTRADOS NA REVISÃO

### **GAP CRÍTICO #1: Frontend NÃO captura metadata do backend**

**Problema**: Backend retorna `_metadata` mas frontend **IGNORA COMPLETAMENTE**!

**Arquivo**: `frontend/src/pages/DynamicMonitoringPage.tsx` linha 563

**Código Atual (ERRADO)**:
```typescript
let rows: MonitoringDataItem[] = response.data || [];
// ❌ Metadata perdida aqui! response contém _metadata mas não é capturada
```

**Correção Necessária**:
```typescript
// ✅ Extrair metadata ANTES de usar response.data
const metadata = response.metadata || null;
let rows: MonitoringDataItem[] = response.data || [];

// ✅ Exibir metadata ao usuário
if (metadata) {
  console.log('[METADATA]', metadata);
  // Atualizar estado para exibir badges/indicadores
  setResponseMetadata(metadata);
}
```

---

### **GAP CRÍTICO #2: Erro KV `'str' object has no attribute 'get'`**

**Problema**: Aparece em TODOS os testes!

**Arquivo**: `backend/core/config.py` linha 80

**Provável Causa**: `KVManager.get_json()` retornando `str` ao invés de `dict`

**Correção Necessária**: Investigar e corrigir parsing JSON do KV

---

## 🎯 SPRINT 2 - IMPLEMENTAÇÃO COMPLETA (Backend + Frontend)

### **OBJETIVO GERAL**
Adicionar observabilidade completa, cache local e dashboards visuais para monitorar:
- Cache effectiveness (hits/misses)
- Fallback events (master offline)
- Staleness distribution
- Performance metrics

---

## 📋 SPRINT 2 - TAREFAS DETALHADAS

### **TAREFA 1: Corrigir Erro KV (PRIORIDADE MÁXIMA)**

**Arquivo**: `backend/core/config.py` ou `backend/core/kv_manager.py`

**Problema**:
```python
# Linha 781 de consul_manager.py
sites_data = await self.get_kv_json('skills/eye/metadata/sites')
# ❌ Retorna string, deveria retornar dict/list
```

**Correção**:
```python
async def get_kv_json(self, key: str) -> Any:
    """
    CORREÇÃO: Garantir que SEMPRE retorna dict/list, nunca str
    """
    try:
        response = await self._request("GET", f"/kv/{key}")
        data = response.json()

        if not data or len(data) == 0:
            return None

        # data é lista de {Key, Value, ...}
        value_b64 = data[0].get("Value")
        if not value_b64:
            return None

        import base64
        import json
        value_decoded = base64.b64decode(value_b64).decode('utf-8')

        # ✅ CRÍTICO: Parse JSON SEMPRE
        return json.loads(value_decoded)

    except json.JSONDecodeError as e:
        logger.error(f"❌ KV {key} não é JSON válido: {e}")
        return None
    except Exception as e:
        logger.error(f"❌ Erro ao buscar KV {key}: {e}")
        return None
```

---

### **TAREFA 2: Capturar Metadata no Frontend**

**Arquivo**: `frontend/src/pages/DynamicMonitoringPage.tsx`

**Adicionar Estado**:
```typescript
const [responseMetadata, setResponseMetadata] = useState<any>(null);
```

**Modificar requestHandler** (linha 563):
```typescript
// ✅ EXTRAIR METADATA
const metadata = response.metadata || null;
if (metadata) {
  setResponseMetadata(metadata);

  // Log performance info
  console.log(`[METADATA] Source: ${metadata.source_name} (${metadata.is_master ? 'MASTER' : 'CLIENT'})`);
  console.log(`[METADATA] Cache: ${metadata.cache_status}, Age: ${metadata.age_seconds}s`);
  console.log(`[METADATA] Staleness: ${metadata.staleness_ms}ms`);
  console.log(`[METADATA] Time: ${metadata.total_time_ms}ms`);
}

let rows: MonitoringDataItem[] = response.data || [];
```

---

### **TAREFA 3: Componente BadgeStatus**

**Criar**: `frontend/src/components/BadgeStatus.tsx`

```typescript
import React from 'react';
import { Badge, Space, Tag, Tooltip } from 'antd';
import {
  CheckCircleOutlined,
  ClockCircleOutlined,
  WarningOutlined
} from '@ant-design/icons';

interface BadgeStatusProps {
  metadata: {
    source_name?: string;
    is_master?: boolean;
    cache_status?: string;
    age_seconds?: number;
    staleness_ms?: number;
    total_time_ms?: number;
  } | null;
}

export const BadgeStatus: React.FC<BadgeStatusProps> = ({ metadata }) => {
  if (!metadata) return null;

  const isMaster = metadata.is_master ?? true;
  const cacheStatus = metadata.cache_status || 'MISS';
  const cacheAge = metadata.age_seconds || 0;
  const staleness = metadata.staleness_ms || 0;
  const responseTime = metadata.total_time_ms || 0;

  return (
    <Space size="small">
      {/* Source Badge */}
      <Tooltip title={`Dados de: ${metadata.source_name || 'unknown'}`}>
        <Tag
          icon={isMaster ? <CheckCircleOutlined /> : <WarningOutlined />}
          color={isMaster ? 'green' : 'orange'}
        >
          {isMaster ? 'Master' : 'Fallback'}
        </Tag>
      </Tooltip>

      {/* Cache Badge */}
      <Tooltip title={`Cache ${cacheStatus}, Age: ${cacheAge}s`}>
        <Tag
          icon={<ClockCircleOutlined />}
          color={cacheStatus === 'HIT' ? 'blue' : 'default'}
        >
          Cache: {cacheStatus}
        </Tag>
      </Tooltip>

      {/* Staleness Badge */}
      {staleness > 1000 && (
        <Tooltip title={`Dados com ${staleness}ms de lag`}>
          <Tag color="warning">
            Stale: {staleness}ms
          </Tag>
        </Tooltip>
      )}

      {/* Performance Badge */}
      <Tooltip title={`Tempo de resposta total`}>
        <Tag color={responseTime < 500 ? 'success' : 'default'}>
          {responseTime}ms
        </Tag>
      </Tooltip>
    </Space>
  );
};
```

**Usar em DynamicMonitoringPage**:
```typescript
import { BadgeStatus } from '../components/BadgeStatus';

// No render, após título:
<PageContainer
  header={{
    title: displayName,
    extra: <BadgeStatus metadata={responseMetadata} />
  }}
>
```

---

### **TAREFA 4: Endpoint /metrics para Prometheus**

**Criar**: `backend/app.py` (adicionar endpoint)

```python
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

@app.get("/metrics")
async def metrics():
    """
    Endpoint para Prometheus scraping

    Expõe métricas:
    - consul_cache_hits_total
    - consul_stale_responses_total
    - consul_api_calls_total
    - consul_request_duration_seconds
    - consul_requests_total
    """
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )
```

---

### **TAREFA 5: Cache Local Backend (TTL 60s)**

**Criar**: `backend/core/cache_manager.py`

```python
from typing import Any, Optional
from datetime import datetime, timedelta
import asyncio

class LocalCache:
    """
    Cache local em memória com TTL configurável

    BENEFÍCIOS:
    - Reduz 1289ms → ~10ms em requests repetidas
    - TTL 60s (configurável)
    - Thread-safe (asyncio.Lock)
    """
    def __init__(self, ttl_seconds: int = 60):
        self.ttl_seconds = ttl_seconds
        self._cache: dict[str, tuple[Any, datetime]] = {}
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> Optional[Any]:
        async with self._lock:
            if key not in self._cache:
                return None

            value, timestamp = self._cache[key]

            # Verificar TTL
            if datetime.now() - timestamp > timedelta(seconds=self.ttl_seconds):
                del self._cache[key]
                return None

            return value

    async def set(self, key: str, value: Any):
        async with self._lock:
            self._cache[key] = (value, datetime.now())

    async def invalidate(self, key: str):
        async with self._lock:
            if key in self._cache:
                del self._cache[key]

    async def clear(self):
        async with self._lock:
            self._cache.clear()

# Singleton global
_catalog_cache = LocalCache(ttl_seconds=60)

# Usar em consul_manager.py
async def get_all_services_catalog(self, use_fallback: bool = True, use_local_cache: bool = True):
    cache_key = f"catalog:all_services:fallback={use_fallback}"

    # Tentar cache local primeiro
    if use_local_cache:
        cached = await _catalog_cache.get(cache_key)
        if cached:
            logger.debug(f"[LOCAL CACHE HIT] {cache_key}")
            return cached

    # Cache miss - buscar do Consul
    result = await self._fetch_catalog_services(use_fallback)

    # Armazenar no cache local
    if use_local_cache:
        await _catalog_cache.set(cache_key, result)

    return result
```

---

### **TAREFA 6: Página Metrics Dashboard**

**Criar**: `frontend/src/pages/MetricsDashboard.tsx`

```typescript
import React, { useState, useEffect } from 'react';
import { Card, Col, Row, Statistic, Table, Tag } from 'antd';
import { Line, Pie } from '@ant-design/charts';
import { PageContainer } from '@ant-design/pro-components';
import {
  ClockCircleOutlined,
  RocketOutlined,
  DatabaseOutlined
} from '@ant-design/icons';
import { consulAPI } from '../services/api';

export default function MetricsDashboard() {
  const [metrics, setMetrics] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetchMetrics();
    const interval = setInterval(fetchMetrics, 5000); // Atualizar a cada 5s
    return () => clearInterval(interval);
  }, []);

  const fetchMetrics = async () => {
    setLoading(true);
    try {
      const response = await fetch('http://localhost:5000/metrics');
      const text = await response.text();

      // Parse Prometheus metrics
      const parsed = parsePrometheusMetrics(text);
      setMetrics(parsed);
    } catch (error) {
      console.error('Erro ao buscar métricas:', error);
    } finally {
      setLoading(false);
    }
  };

  const parsePrometheusMetrics = (text: string) => {
    // Simplificado - parsear métricas Prometheus
    const lines = text.split('\n');
    const metrics: any = {
      cache_hits: 0,
      cache_total: 0,
      stale_responses: 0,
      api_calls: {}
    };

    lines.forEach(line => {
      if (line.startsWith('consul_cache_hits_total')) {
        const match = line.match(/(\d+)$/);
        if (match) metrics.cache_hits += parseInt(match[1]);
      }
      if (line.startsWith('consul_api_calls_total')) {
        const match = line.match(/api_type="(\w+)".*?(\d+)$/);
        if (match) {
          metrics.api_calls[match[1]] = parseInt(match[2]);
        }
      }
    });

    return metrics;
  };

  const cacheHitRate = metrics
    ? ((metrics.cache_hits / (metrics.cache_total || 1)) * 100).toFixed(1)
    : 0;

  return (
    <PageContainer
      header={{
        title: 'Metrics Dashboard',
        subTitle: 'Monitoramento em tempo real do sistema'
      }}
    >
      <Row gutter={[16, 16]}>
        {/* KPIs */}
        <Col span={8}>
          <Card>
            <Statistic
              title="Cache Hit Rate"
              value={cacheHitRate}
              suffix="%"
              prefix={<DatabaseOutlined />}
              valueStyle={{ color: '#3f8600' }}
            />
          </Card>
        </Col>
        <Col span={8}>
          <Card>
            <Statistic
              title="Cache Hits (Total)"
              value={metrics?.cache_hits || 0}
              prefix={<ClockCircleOutlined />}
            />
          </Card>
        </Col>
        <Col span={8}>
          <Card>
            <Statistic
              title="Stale Responses"
              value={metrics?.stale_responses || 0}
              prefix={<RocketOutlined />}
              valueStyle={{ color: metrics?.stale_responses > 10 ? '#cf1322' : '#3f8600' }}
            />
          </Card>
        </Col>

        {/* Gráfico de API Calls */}
        <Col span={24}>
          <Card title="API Calls por Tipo">
            <Pie
              data={Object.entries(metrics?.api_calls || {}).map(([type, count]) => ({
                type,
                value: count as number
              }))}
              angleField="value"
              colorField="type"
              radius={0.8}
              label={{
                type: 'outer',
                content: '{name} {percentage}'
              }}
            />
          </Card>
        </Col>
      </Row>
    </PageContainer>
  );
}
```

**Adicionar rota em App.tsx**:
```typescript
import MetricsDashboard from './pages/MetricsDashboard';

// Na configuração de rotas
{
  path: '/metrics',
  name: 'Métricas',
  icon: <DashboardOutlined />,
  component: MetricsDashboard
}
```

---

### **TAREFA 7: Página System Health**

**Criar**: `frontend/src/pages/SystemHealth.tsx`

```typescript
import React, { useState, useEffect } from 'react';
import { Card, Col, Row, Badge, Descriptions, Alert, Timeline } from 'antd';
import { PageContainer, ProCard } from '@ant-design/pro-components';
import {
  CheckCircleOutlined,
  CloseCircleOutlined,
  ClockCircleOutlined
} from '@ant-design/icons';

export default function SystemHealth() {
  const [health, setHealth] = useState<any>(null);
  const [fallbackLog, setFallbackLog] = useState<any[]>([]);

  useEffect(() => {
    fetchHealth();
    const interval = setInterval(fetchHealth, 10000);
    return () => clearInterval(interval);
  }, []);

  const fetchHealth = async () => {
    try {
      // Simular consulta de health
      // TODO: Criar endpoint /api/v1/health/status
      const response = {
        consul_nodes: [
          { name: 'Palmas', ip: '172.16.1.26', status: 'healthy', is_master: true },
          { name: 'Rio', ip: '172.16.200.14', status: 'healthy', is_master: false },
          { name: 'Dtc', ip: '172.16.100.10', status: 'unknown', is_master: false }
        ],
        last_fallback: {
          timestamp: '2025-11-15 10:30:00',
          reason: 'Master timeout',
          fallback_to: 'Rio'
        }
      };

      setHealth(response);
    } catch (error) {
      console.error('Erro ao buscar health:', error);
    }
  };

  return (
    <PageContainer
      header={{
        title: 'System Health',
        subTitle: 'Status dos nodes Consul e fallback'
      }}
    >
      <Row gutter={[16, 16]}>
        {/* Status dos Nodes */}
        {health?.consul_nodes.map((node: any) => (
          <Col span={8} key={node.ip}>
            <ProCard
              title={node.name}
              extra={
                <Badge
                  status={node.status === 'healthy' ? 'success' : 'error'}
                  text={node.status}
                />
              }
              bordered
              hoverable
            >
              <Descriptions column={1} size="small">
                <Descriptions.Item label="IP">{node.ip}</Descriptions.Item>
                <Descriptions.Item label="Role">
                  {node.is_master ? 'Master' : 'Client'}
                </Descriptions.Item>
                <Descriptions.Item label="Status">
                  {node.status === 'healthy' ? (
                    <CheckCircleOutlined style={{ color: '#52c41a' }} />
                  ) : (
                    <CloseCircleOutlined style={{ color: '#f5222d' }} />
                  )}
                </Descriptions.Item>
              </Descriptions>
            </ProCard>
          </Col>
        ))}

        {/* Log de Fallback */}
        <Col span={24}>
          <Card title="Histórico de Fallback">
            {health?.last_fallback ? (
              <Alert
                message="Último Fallback Detectado"
                description={
                  <Timeline>
                    <Timeline.Item color="red">
                      {health.last_fallback.timestamp} - {health.last_fallback.reason}
                    </Timeline.Item>
                    <Timeline.Item color="green">
                      Fallback para: {health.last_fallback.fallback_to}
                    </Timeline.Item>
                  </Timeline>
                }
                type="warning"
                showIcon
                icon={<ClockCircleOutlined />}
              />
            ) : (
              <Alert
                message="Sistema Operacional Normal"
                description="Nenhum evento de fallback registrado"
                type="success"
                showIcon
              />
            )}
          </Card>
        </Col>
      </Row>
    </PageContainer>
  );
}
```

---

## ✅ CHECKLIST DE IMPLEMENTAÇÃO

### SPRINT 1 - CORREÇÕES:
- [ ] Corrigir erro KV `'str' object has no attribute 'get'`
- [ ] Capturar `_metadata` no frontend (DynamicMonitoringPage)
- [ ] Criar componente `BadgeStatus` para exibir metadata
- [ ] Integrar BadgeStatus em DynamicMonitoringPage

### SPRINT 2 - BACKEND:
- [ ] Criar endpoint `/metrics` para Prometheus
- [ ] Implementar `LocalCache` com TTL 60s
- [ ] Integrar LocalCache em `get_all_services_catalog()`
- [ ] Criar endpoint `/api/v1/health/status` (opcional)

### SPRINT 2 - FRONTEND:
- [ ] Criar página `MetricsDashboard.tsx`
- [ ] Criar página `SystemHealth.tsx`
- [ ] Adicionar rotas no App.tsx
- [ ] Adicionar menu items

### TESTES:
- [ ] Testar cache local (verificar 1289ms → ~10ms)
- [ ] Testar endpoint /metrics (curl http://localhost:5000/metrics)
- [ ] Testar BadgeStatus renderizando metadata
- [ ] Testar MetricsDashboard atualização tempo real
- [ ] Testar SystemHealth status dos nodes

---

## 🎯 RESULTADO ESPERADO

### Performance:
- **Com cache local**: 1289ms → **~10ms** (128x mais rápido!)
- **Cache hit rate**: >90% após warming

### Observabilidade:
- ✅ Dashboard de métricas tempo real
- ✅ Badges visuais de cache/fallback
- ✅ Health status dos nodes Consul
- ✅ Histórico de eventos de fallback

### UX:
- ✅ Usuário vê se dados vêm do cache ou não
- ✅ Usuário vê se master está offline (fallback ativo)
- ✅ Usuário vê performance em tempo real
- ✅ Usuário monitora saúde do sistema

---

**PRONTO PARA IMPLEMENTAR!** 🚀
