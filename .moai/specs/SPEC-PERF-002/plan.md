---
id: SPEC-PERF-002
version: "2.1.0"
status: draft
created: 2025-11-22
updated: 2025-11-22
author: Claude Code
priority: CRITICAL
---

# Plano de Implementacao - SPEC-PERF-002

## Visao Geral

Este plano detalha as etapas para corrigir os problemas criticos de performance no `DynamicMonitoringPage.tsx` com **abordagem Backend-First**. A auditoria consolidada de 4 IAs (Claude, Cursor, Codex, Gemini-3) identificou que o plano anterior focava em micro-otimizacoes React ignorando o problema real: **processamento client-side de dados massivos**.

**Principio fundamental**: Backend faz o trabalho pesado, Frontend fica leve.

---

## Diagnostico Corrigido

### Problemas Fatais Identificados

1. **Paginacao client-side** - Sistema baixa TODOS os dados e processa no browser
2. **Filtros client-side** - Loops O(n) e O(n^2) sobre arrays gigantes
3. **Race conditions** - Debounce sem AbortController nao cancela requests anteriores
4. **Consul sem paginacao nativa** - API nao suporta (Issue #9422)

### Erros do Plano Anterior

1. **ERRADO**: Remover `filteredValue`/`sortOrder` das deps - QUEBRA visual do ProTable
2. **ERRADO**: FilterDropdown como componente separado - Deve ser funcao inline
3. **ERRADO**: Context global para display names - Overhead desnecessario
4. **ERRADO**: Diagnostico de "Colunas (0/0)" como loop infinito - E race condition

---

## FASE 0: Pre-requisitos e Baseline (2-3 dias)

**Objetivo**: Capturar estado atual e preparar ambiente.

### Tarefas

0.1. **Capturar metricas baseline**
   ```bash
   # Abrir React DevTools Profiler
   # Gravar interacoes: filtro, sort, paginacao, busca
   # Anotar: re-renders por interacao, tempo de render

   # Network tab
   # Anotar: tamanho payload, tempo resposta, requests simultaneos
   ```

0.2. **Instalar dependencias**
   ```bash
   cd frontend
   npm install use-debounce
   npm ls use-debounce  # Verificar instalacao
   ```

0.3. **Documentar estado atual**
   - Criar `docs/SPEC-PERF-002-baseline.md`
   - Capturar screenshots do Profiler
   - Listar metricas: payload, tempo, re-renders

0.4. **Verificar compatibilidade ProTable**
   - Confirmar que controlled mode requer `filteredValue`/`sortOrder`
   - Testar em sandbox isolado

### Nota: React 19 Strict Mode

O projeto usa React 19.1.1 que tem Strict Mode mais agressivo em desenvolvimento:
- useEffect executa 3 vezes: mount → unmount → mount → unmount → mount
- Isso eh NORMAL em dev e nao ocorre em producao
- Usar cleanup functions para evitar warnings:

```typescript
useEffect(() => {
  let cancelled = false;

  const loadData = async () => {
    const data = await fetchData();
    if (!cancelled) {
      setData(data);
    }
  };

  loadData();

  return () => {
    cancelled = true; // Evita setState apos unmount
  };
}, []);
```

**Criterio de sucesso**: Baseline documentado, dependencias instaladas.

---

## FASE 1: Backend - Paginacao Server-Side (5-7 dias)

**Objetivo**: Mover processamento pesado para o servidor.

### 1.1. Implementar Paginacao no Endpoint

**Arquivo**: `backend/api/monitoring_unified.py`

```python
@router.get("/data")
async def get_monitoring_data(
    category: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=10, le=200),
    sort_field: Optional[str] = None,
    sort_order: Optional[str] = None,  # "ascend" | "descend"
    node: Optional[str] = None,  # Filtro por no
    # Filtros dinamicos via query params
    **filters
):
    """
    Endpoint com paginacao, ordenacao e filtros server-side.
    Consul nao suporta paginacao nativa, entao usamos cache intermediario.
    """
    # 1. Buscar dados do cache (ou Consul se cache expirado)
    all_data = await cache_manager.get_monitoring_data(category)

    # 2. Aplicar filtro por no (ANTES de tudo)
    if node and node != 'all':
        all_data = [item for item in all_data if item.get('node_ip') == node]

    # 3. Aplicar filtros de metadata
    filtered_data = apply_metadata_filters(all_data, filters)

    # 4. Aplicar ordenacao
    sorted_data = apply_sort(filtered_data, sort_field, sort_order)

    # 5. Paginar
    start = (page - 1) * page_size
    end = start + page_size
    page_data = sorted_data[start:end]

    # 6. Extrair opcoes de filtro dos dados FILTRADOS
    filter_options = extract_filter_options(filtered_data)

    return {
        "success": True,
        "data": page_data,
        "total": len(filtered_data),
        "page": page,
        "pageSize": page_size,
        "filterOptions": filter_options,
        "_metadata": {
            "cache_status": "hit" if from_cache else "miss",
            "processing_time_ms": processing_time
        }
    }
```

### 1.2. Implementar Cache Intermediario

**Arquivo**: `backend/core/monitoring_cache.py`

```python
import time
from typing import Dict, Any, Optional

class MonitoringDataCache:
    """
    Cache intermediario para dados do Consul.
    Consul API nao suporta paginacao nativa (Issue #9422).
    """

    def __init__(self, ttl_seconds: int = 30):
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.ttl = ttl_seconds

    async def get_monitoring_data(self, category: str) -> list:
        cache_key = f"monitoring:{category}"

        # Verificar se cache valido
        if cache_key in self.cache:
            entry = self.cache[cache_key]
            if entry['expires'] > time.time():
                return entry['data']

        # Cache miss ou expirado - buscar do Consul
        all_data = await self._fetch_from_consul(category)

        # Atualizar cache
        self.cache[cache_key] = {
            'data': all_data,
            'expires': time.time() + self.ttl
        }

        return all_data

    def invalidate(self, category: Optional[str] = None):
        """Invalidar cache para refresh forcado."""
        if category:
            cache_key = f"monitoring:{category}"
            self.cache.pop(cache_key, None)
        else:
            self.cache.clear()

# Singleton
cache_manager = MonitoringDataCache(ttl_seconds=30)
```

### 1.3. Implementar Filtros e Ordenacao Server-Side

**Arquivo**: `backend/core/monitoring_filters.py`

```python
from typing import List, Dict, Any, Optional

def apply_metadata_filters(data: List[Dict], filters: Dict[str, str]) -> List[Dict]:
    """Aplicar filtros de metadata no servidor."""
    if not filters:
        return data

    filtered = data
    for field, value in filters.items():
        if value:
            filtered = [
                item for item in filtered
                if item.get('Meta', {}).get(field) == value
            ]

    return filtered

def apply_sort(data: List[Dict], field: Optional[str], order: Optional[str]) -> List[Dict]:
    """Ordenar dados no servidor."""
    if not field:
        return data

    reverse = order == 'descend'

    def get_sort_key(item):
        # Tentar Meta primeiro, depois campo direto
        value = item.get('Meta', {}).get(field) or item.get(field, '')
        return str(value).lower() if value else ''

    return sorted(data, key=get_sort_key, reverse=reverse)

def extract_filter_options(data: List[Dict]) -> Dict[str, List[str]]:
    """Extrair opcoes unicas para filtros dropdown."""
    options = {}

    for item in data:
        meta = item.get('Meta', {})
        for key, value in meta.items():
            if value:
                if key not in options:
                    options[key] = set()
                options[key].add(value)

    # Converter sets para lists ordenadas
    return {k: sorted(list(v)) for k, v in options.items()}
```

### 1.4. Testes Backend com Fixtures

**Arquivo**: `backend/tests/test_monitoring_unified_baseline.py`

```python
"""
Testes baseline para endpoints de monitoramento unificado.
USA FIXTURES, nao infraestrutura externa.
"""
import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from app import app

# Fixture de dados mock
@pytest.fixture
def mock_monitoring_data():
    return [
        {
            "Service": "service-1",
            "node_ip": "172.16.1.26",
            "Meta": {"company": "Agro Xingu", "site": "Site A"}
        },
        {
            "Service": "service-2",
            "node_ip": "172.16.1.27",
            "Meta": {"company": "Agro Xingu", "site": "Site B"}
        },
        {
            "Service": "service-3",
            "node_ip": "172.16.1.26",
            "Meta": {"company": "Outro", "site": "Site A"}
        },
    ]

@pytest.fixture
def client():
    return TestClient(app)

class TestMonitoringUnifiedBaseline:

    @patch('backend.core.monitoring_cache.cache_manager.get_monitoring_data')
    def test_pagination_returns_correct_page(self, mock_get, client, mock_monitoring_data):
        mock_get.return_value = mock_monitoring_data

        response = client.get("/api/v1/monitoring/data?category=network-probes&page=1&page_size=2")

        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 2
        assert data["total"] == 3
        assert data["page"] == 1

    @patch('backend.core.monitoring_cache.cache_manager.get_monitoring_data')
    def test_filter_by_node(self, mock_get, client, mock_monitoring_data):
        mock_get.return_value = mock_monitoring_data

        response = client.get("/api/v1/monitoring/data?category=network-probes&node=172.16.1.26")

        data = response.json()
        # Deve retornar apenas 2 items do node 172.16.1.26
        assert len(data["data"]) == 2
        for item in data["data"]:
            assert item["node_ip"] == "172.16.1.26"

    @patch('backend.core.monitoring_cache.cache_manager.get_monitoring_data')
    def test_filter_by_metadata(self, mock_get, client, mock_monitoring_data):
        mock_get.return_value = mock_monitoring_data

        response = client.get("/api/v1/monitoring/data?category=network-probes&company=Agro%20Xingu")

        data = response.json()
        assert len(data["data"]) == 2
        for item in data["data"]:
            assert item["Meta"]["company"] == "Agro Xingu"

    @patch('backend.core.monitoring_cache.cache_manager.get_monitoring_data')
    def test_sort_ascending(self, mock_get, client, mock_monitoring_data):
        mock_get.return_value = mock_monitoring_data

        response = client.get("/api/v1/monitoring/data?category=network-probes&sort_field=Service&sort_order=ascend")

        data = response.json()
        services = [item["Service"] for item in data["data"]]
        assert services == sorted(services)

    @patch('backend.core.monitoring_cache.cache_manager.get_monitoring_data')
    def test_filter_options_extracted(self, mock_get, client, mock_monitoring_data):
        mock_get.return_value = mock_monitoring_data

        response = client.get("/api/v1/monitoring/data?category=network-probes")

        data = response.json()
        assert "filterOptions" in data
        assert "company" in data["filterOptions"]
        assert "Agro Xingu" in data["filterOptions"]["company"]
```

**Criterio de sucesso**: Backend pagina, filtra e ordena no servidor. Frontend recebe apenas dados da pagina atual.

---

## FASE 2: Frontend - Correcoes Criticas (3-4 dias)

**Objetivo**: Corrigir problemas do plano anterior que quebrariam funcionalidades.

### 2.1. MANTER filteredValue e sortOrder nas Dependencias

**IMPORTANTE**: ProTable REQUER estas propriedades para feedback visual.

```typescript
// ✅ CORRETO - Manter nas dependencias
const proTableColumns = useMemo<ProColumns<MonitoringDataItem>[]>(() => {
  return visibleConfigs.map((colConfig) => {
    const baseColumn: ProColumns<MonitoringDataItem> = {
      // ... outras props ...

      // OBRIGATORIO para icone de filtro ficar azul
      filteredValue: filters[colConfig.key] ? [filters[colConfig.key]] : null,

      // OBRIGATORIO para seta de ordenacao aparecer
      sortOrder: sortField === colConfig.key ? sortOrder : null,
    };

    return baseColumn;
  });
}, [
  columnConfig,
  columnWidths,
  tableFields,
  filters,        // MANTER - necessario para visual
  sortField,      // MANTER - necessario para visual
  sortOrder,      // MANTER - necessario para visual
  handleResize,
  getFieldValue,
  metadataOptionsRef.current,  // Usar ref estavel
]);
```

### 2.2. Usar useRef para metadataOptions Estavel

```typescript
// Evitar stale closure no filterDropdown
const metadataOptionsRef = useRef<Record<string, string[]>>({});

// Atualizar ref quando options mudam
useEffect(() => {
  metadataOptionsRef.current = metadataOptions;
}, [metadataOptions]);

// No filterDropdown, usar ref
baseColumn.filterDropdown = ({ setSelectedKeys, selectedKeys, confirm, clearFilters }) => {
  const fieldOptions = metadataOptionsRef.current[colConfig.key] || [];
  // ... render com fieldOptions atualizado
};
```

### 2.3. Implementar AbortController para Cancelar Requests

```typescript
const abortControllerRef = useRef<AbortController | null>(null);

const requestHandler = useCallback(async (params: any) => {
  // CANCELAR request anterior
  if (abortControllerRef.current) {
    abortControllerRef.current.abort();
  }

  // Criar novo controller
  abortControllerRef.current = new AbortController();

  try {
    const response = await consulAPI.getMonitoringData(category, {
      page: params.current,
      pageSize: params.pageSize,
      node: selectedNode,
      sortField,
      sortOrder,
      ...filters,
      signal: abortControllerRef.current.signal,  // Passar signal
    });

    // Atualizar metadataOptions com opcoes do servidor
    if (response.filterOptions) {
      setMetadataOptions(response.filterOptions);
    }

    return {
      data: response.data,
      total: response.total,
      success: true,
    };
  } catch (error) {
    if (error.name === 'AbortError') {
      // Request cancelado, ignorar
      return { data: [], total: 0, success: true };
    }
    throw error;
  }
}, [category, selectedNode, sortField, sortOrder, filters]);

// Cleanup ao desmontar
useEffect(() => {
  return () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
  };
}, []);
```

### 2.4. Implementar isMountedRef para Evitar Memory Leak

```typescript
const isMountedRef = useRef(true);

useEffect(() => {
  isMountedRef.current = true;
  return () => {
    isMountedRef.current = false;
  };
}, []);

// Em qualquer setState async
const requestHandler = useCallback(async (params: any) => {
  // ... fetch ...

  // Verificar antes de atualizar estado
  if (!isMountedRef.current) return { data: [], total: 0, success: true };

  setMetadataOptions(response.filterOptions);
  // ...
}, []);
```

### 2.5. Corrigir Race Condition metadataOptions/metadataOptionsLoaded

**Problema**: Estados nao sao atomicos, pode haver inconsistencia entre eles.

```typescript
// ❌ PROBLEMA: Nao atomico
setMetadataOptions(options);     // Estado 1
setMetadataOptionsLoaded(true);  // Estado 2
// Se outro request executar entre as duas linhas, estado fica inconsistente

// ✅ SOLUCAO: Usar um unico estado
const [metadataState, setMetadataState] = useState({
  options: {} as Record<string, string[]>,
  loaded: false
});

// Atualizacao atomica
setMetadataState({
  options: extractedOptions,
  loaded: true
});

// No componente, usar:
const { options: metadataOptions, loaded: metadataOptionsLoaded } = metadataState;
```

### 2.6. Corrigir useEffect de columnConfig

**Problema real**: Race condition durante carregamento, NAO loop infinito.

```typescript
// O codigo atual JA tem protecao contra loop
// Problema eh que tableFields pode estar vazio no primeiro render

useEffect(() => {
  // Esperar tableFields carregar
  if (defaultColumnConfig.length > 0 && tableFields.length > 0) {
    const defaultKeys = defaultColumnConfig.map(c => c.key).sort().join(',');
    const currentKeys = columnConfig.map(c => c.key).sort().join(',');

    // So atualizar se realmente diferente
    if (defaultKeys !== currentKeys || defaultColumnConfig.length !== columnConfig.length) {
      setColumnConfig(defaultColumnConfig);
    }
  }
}, [defaultColumnConfig, columnConfig, tableFields.length]);
```

### 2.7. FilterDropdown como Funcao Inline

**ProTable espera funcao que retorna JSX**, nao componente React.

```typescript
// ✅ CORRETO - Funcao inline
baseColumn.filterDropdown = ({ setSelectedKeys, selectedKeys, confirm, clearFilters }) => {
  // Estado local - OK aqui porque e funcao inline
  const [searchText, setSearchText] = useState('');
  const fieldOptions = metadataOptionsRef.current[colConfig.key] || [];

  return (
    <div style={{ padding: 8 }}>
      <Input
        placeholder={`Buscar ${colConfig.title}`}
        value={searchText}
        onChange={(e) => setSearchText(e.target.value)}
        style={{ marginBottom: 8, display: 'block' }}
      />
      {/* ... resto do dropdown */}
    </div>
  );
};
```

**Criterio de sucesso**: Feedback visual de filtros/sort funciona, sem race conditions, sem memory leaks.

---

## FASE 3: Frontend - Otimizacoes React (2-3 dias)

**Objetivo**: Otimizar performance apos backend estar pronto.

### 3.1. Debounce com Cancelamento

```typescript
import { useDebouncedCallback } from 'use-debounce';

const debouncedReload = useDebouncedCallback(() => {
  // AbortController ja cuida de cancelar request anterior
  actionRef.current?.reload();
}, 300);

// Em handlers de filtro/busca
const handleSearchChange = useCallback((value: string) => {
  setSearchValue(value);
  debouncedReload();
}, [debouncedReload]);

const handleFilterChange = useCallback((newFilters: Record<string, string | undefined>) => {
  setFilters(newFilters);
  debouncedReload();
}, [debouncedReload]);

// Mudanca de no eh pontual - sem debounce
const handleNodeChange = useCallback((nodeAddr: string) => {
  setSelectedNode(nodeAddr);
  actionRef.current?.reload();  // Imediato
}, []);
```

### 3.2. Virtualizacao de Tabela (Para Grandes Volumes)

```typescript
import { ProTable } from '@ant-design/pro-components';

<ProTable
  // ... outras props ...

  // Habilitar virtualizacao para tabelas grandes
  virtual={true}
  scroll={{ y: 600, x: 'max-content' }}
/>
```

### 3.3. Consolidar useEffects

```typescript
// REMOVER useEffect separado para selectedNode/filters
// Usar handlers diretos com reload

// MANTER apenas useEffect para mudanca de categoria
useEffect(() => {
  // Reset estados ao mudar categoria
  setFilters({});
  setSelectedNode('all');
  setSearchValue('');
  setSortField(undefined);
  setSortOrder(undefined);
  setMetadataOptions({});

  // Reload automatico
  actionRef.current?.reload();
}, [category]);
```

### 3.4. Memoizacao de getFieldValue

**Problema**: getFieldValue eh chamada muitas vezes para cada celula da tabela.

```typescript
// Cache para getFieldValue
const fieldValueCacheRef = useRef<Record<string, string>>({});

const getFieldValue = useCallback((row: MonitoringDataItem, field: string): string => {
  const cacheKey = `${row.ID}-${field}`;

  // Retornar do cache se existir
  if (fieldValueCacheRef.current[cacheKey] !== undefined) {
    return fieldValueCacheRef.current[cacheKey];
  }

  // Calculo normal
  let value = '';
  if (field === 'Tags') {
    value = (row.Tags || []).join(', ');
  } else if (row.Meta?.[field] !== undefined) {
    value = String(row.Meta[field]);
  } else if (row[field as keyof MonitoringDataItem] !== undefined) {
    value = String(row[field as keyof MonitoringDataItem]);
  }

  // Salvar no cache
  fieldValueCacheRef.current[cacheKey] = value;
  return value;
}, []);

// Limpar cache ao mudar categoria
useEffect(() => {
  fieldValueCacheRef.current = {};
}, [category]);
```

### 3.5. Nota sobre Processamento O(n²)

**Detalhamento do problema**:
- `applyAdvancedFilters` tem loop aninhado quando usa operador OR
- Para cada registro, verifica cada condicao
- Com 5000 registros e 10 condicoes = 50.000 operacoes
- **SOLUCAO**: Mover para backend (ja implementado na FASE 1) ou usar Web Worker

### 3.6. Remover CATEGORY_DISPLAY_NAMES Hardcoded

**Solucao simples**: Usar dados que JA vem do tableFields.

```typescript
// REMOVER
const CATEGORY_DISPLAY_NAMES: Record<string, string> = { ... };

// ADICIONAR - funcao de formatacao
const formatCategoryName = (slug: string): string => {
  return slug
    .split('-')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
};

// Usar no componente
const categoryTitle = tableFields[0]?.category_display_name || formatCategoryName(category);
```

**NAO criar Context global** - e overhead desnecessario que aumenta bundle e re-renders.

**Criterio de sucesso**: Digitacao rapida gera 1 request, tabela renderiza sem lag.

---

## FASE 4: Features Avancadas (Opcional - 3-4 dias)

**Objetivo**: Otimizacoes avancadas para escala enterprise.

### 4.1. Web Workers para Processamento Pesado

```typescript
// worker.ts
self.onmessage = (e) => {
  const { data, filters } = e.data;
  const filtered = heavyFilterLogic(data, filters);
  self.postMessage(filtered);
};

// No componente
const worker = new Worker(new URL('./worker.ts', import.meta.url));
worker.onmessage = (e) => setFilteredData(e.data);
worker.postMessage({ data, filters });
```

### 4.2. Web Vitals Monitoring

```typescript
import { getCLS, getFID, getFCP, getLCP, getTTFB } from 'web-vitals';

// Enviar para analytics
getCLS(console.log);
getFID(console.log);
getLCP(console.log);
```

### 4.3. Error Boundaries

```typescript
class MonitoringErrorBoundary extends React.Component {
  state = { hasError: false };

  static getDerivedStateFromError(error) {
    return { hasError: true };
  }

  render() {
    if (this.state.hasError) {
      return <Alert type="error" message="Erro ao carregar dados" />;
    }
    return this.props.children;
  }
}
```

### 4.4. Service Worker para Cache Offline

```javascript
// public/serviceWorker.js
self.addEventListener('fetch', (event) => {
  // Cache apenas requests de monitoring data
  if (event.request.url.includes('/api/v1/monitoring/data')) {
    event.respondWith(
      caches.match(event.request)
        .then(response => {
          // Retornar cache ou fazer fetch
          return response || fetch(event.request).then(fetchResponse => {
            // Cachear resposta para uso offline
            return caches.open('monitoring-cache').then(cache => {
              cache.put(event.request, fetchResponse.clone());
              return fetchResponse;
            });
          });
        })
    );
  }
});
```

### 4.5. Intersection Observer para Lazy Loading

```typescript
// Lazy loading de componentes pesados apenas quando visiveis
const LazyComponent: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [isVisible, setIsVisible] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const observer = new IntersectionObserver(
      ([entry]) => setIsVisible(entry.isIntersecting),
      { threshold: 0.1 }
    );

    if (ref.current) observer.observe(ref.current);

    return () => observer.disconnect();
  }, []);

  return <div ref={ref}>{isVisible && children}</div>;
};

// Uso para componentes pesados
<LazyComponent>
  <HeavyChartComponent data={data} />
</LazyComponent>
```

---

## FASE 5: Validacao e Deploy (2-3 dias)

**Objetivo**: Validar correcoes e deploy gradual.

### 5.1. Testes E2E com Playwright

```typescript
test('filtros mantém estado após interação', async ({ page }) => {
  await page.goto('/monitoring/network-probes');

  // Abrir filtro
  await page.click('[data-testid="filter-company"]');
  await page.fill('[placeholder="Buscar"]', 'Agro');

  // Interagir com tabela
  await page.click('th[data-testid="sort-service"]');

  // Verificar filtro manteve estado
  const input = page.locator('[placeholder="Buscar"]');
  await expect(input).toHaveValue('Agro');
});
```

### 5.2. Load Testing

```bash
# Testar com volume real
# 5000+ registros
# 10+ usuarios simultaneos
```

### 5.3. Profiling Antes/Depois

- React DevTools Profiler
- Network waterfall
- Memory heap
- Web Vitals

---

## Metricas de Sucesso Revisadas

| Metrica | Atual (estimado) | Meta Minima | Meta Ideal | Como Medir |
|---------|-----------------|-------------|------------|------------|
| **Payload inicial** | ~5MB (5k registros) | <200KB | <100KB | Network tab |
| **Tempo carregamento** | ~8s | <2s | <500ms | Performance.measure() |
| **Re-renders/interacao** | 15-20 | ≤5 | ≤3 | React Profiler |
| **Memory heap** | ~150MB | <50MB | <20MB | Chrome Memory |
| **Requests simultaneos** | 5-10 | ≤2 | 1 | Network tab |

---

## Riscos e Mitigacoes

### Risco 1: Backend demora mais que previsto

**Mitigacao**: Implementar em fases, frontend pode comecar com mock

### Risco 2: ProTable nao aceita mudancas

**Mitigacao**: Testar em sandbox primeiro, consultar docs oficiais

### Risco 3: Cache inconsistente

**Mitigacao**: TTL curto (30s), botao de refresh manual, invalidacao em mutations

---

## O que NAO Fazer

1. **NUNCA** remover `filteredValue`/`sortOrder` das deps - QUEBRA visual
2. **NUNCA** processar dados no cliente com volume > 1000
3. **NUNCA** criar FilterDropdown como componente separado
4. **NUNCA** usar debounce sem AbortController
5. **NUNCA** ignorar paginacao server-side

## O que DEVE Fazer

1. **SEMPRE** paginar no servidor
2. **SEMPRE** cancelar requests anteriores com AbortController
3. **SEMPRE** verificar isMounted antes de setState
4. **SEMPRE** medir com React Profiler
5. **SEMPRE** testar com volume real (5k+ registros)

---

## Entregaveis

### Backend (FASE 1)

1. `backend/api/monitoring_unified.py` - Endpoint com paginacao server-side
2. `backend/core/monitoring_cache.py` - Cache intermediario para Consul
3. `backend/core/monitoring_filters.py` - Filtros e ordenacao server-side
4. `backend/tests/test_monitoring_unified_baseline.py` - Testes com fixtures

### Frontend (FASES 2-3)

1. `frontend/src/pages/DynamicMonitoringPage.tsx` - Refatorado com:
   - AbortController para cancelar requests
   - isMountedRef para evitar memory leak
   - useRef para metadataOptions estavel
   - MANTENDO filteredValue/sortOrder nas deps
   - Debounce com cancelamento
   - Remocao de CATEGORY_DISPLAY_NAMES hardcoded

2. `frontend/src/components/MetadataFilterBar.tsx` - Debounce integrado

---

## Tempo Total Realista

**18-23 dias** (nao 11 do plano anterior)

- FASE 0: 2-3 dias
- FASE 1: 5-7 dias (Backend - CRITICO)
- FASE 2: 3-4 dias
- FASE 3: 2-3 dias
- FASE 4: 3-4 dias (opcional)
- FASE 5: 2-3 dias

---

## Traceability

- **Relacionado a**: SPEC-PERF-001
- **Baseado em**: AUDITORIA-COMPLETA-CONSOLIDADA-SPEC-PERF-002.md
- **Tags**: performance, backend-first, pagination, react, refactoring, critical
