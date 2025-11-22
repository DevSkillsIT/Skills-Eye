---
id: SPEC-PERF-002
version: "2.2.0"
status: completed
created: 2025-11-22
updated: 2025-11-22
author: Claude Code
priority: CRITICAL
completed_date: 2025-11-22
---

# HISTORY

| Versao | Data       | Autor       | Descricao                      |
|--------|------------|-------------|--------------------------------|
| 1.0.0  | 2025-11-22 | Claude Code | Versao inicial do SPEC         |
| 1.1.0  | 2025-11-22 | Claude Code | Adicionado problema de colunas nao renderizadas, KVs dinamicos, testes baseline |
| 1.2.0  | 2025-11-22 | Claude Code | Simplificado FR-005 - usar KV skills/eye/monitoring-types e hook useAllMonitoringTypes existente |
| 2.0.0  | 2025-11-22 | Claude Code | REVISAO COMPLETA - Abordagem Backend-First baseada em AUDITORIA-COMPLETA-CONSOLIDADA |
| 2.1.0  | 2025-11-22 | Claude Code | Ajustes finais: corrigir Causa Raiz 1, race condition atomica, React 19 Strict Mode, memoizacao, O(n2), Service Worker, Intersection Observer |
| 2.2.0  | 2025-11-22 | Claude Code | IMPLEMENTACAO COMPLETA - Sincronizacao final com relatorio consolidado. Status: COMPLETED |

---

# SPEC-PERF-002: Correcao de Performance Critica no DynamicMonitoringPage

## Resumo Executivo

Este SPEC define correcoes criticas de performance para o componente `DynamicMonitoringPage.tsx`. Analise comparativa com `Exporters.tsx` e `BlackboxTargets.tsx` (que funcionam corretamente) revelou anti-patterns graves que causam re-renders excessivos e perda de estado em filtros.

## Contexto e Motivacao

### Problema Identificado

O componente `DynamicMonitoringPage.tsx` apresenta problemas graves de performance que afetam todas as 8 paginas de monitoramento:

| Metrica | Valor Atual | Impacto |
|---------|-------------|---------|
| Re-renders por interacao | 10+ | UX degradada, lentidao perceptivel |
| Filtros perdendo estado | Frequente | Usuario precisa re-selecionar |
| Race conditions em fetch | Sim | Dados incorretos exibidos |
| Recalculo de colunas | A cada interacao | CPU alta, lag em digitacao |
| Colunas nao renderizadas | Intermitente | Tabela mostra apenas checkboxes |
| Botao "Colunas (0/0)" | Detectado | columnConfig nao atualizado corretamente |

### Causa Raiz 1: proTableColumns com Muitas Dependencias (MEDIUM)

**Localizacao**: `frontend/src/pages/DynamicMonitoringPage.tsx` linhas 407-658

**Esclarecimento apos auditoria**:
- `filters`, `sortField` e `sortOrder` **DEVEM permanecer** nas dependencias (requisito do ProTable para controlled mode)
- `metadataOptions` deve ser estabilizado com useRef para evitar recalculos desnecessarios
- O problema real e a falta de estabilizacao de metadataOptions, nao a presenca nas dependencias

```typescript
// CORRETO: Manter filters/sortField/sortOrder, estabilizar metadataOptions
const metadataOptionsRef = useRef(metadataOptions);
useEffect(() => {
  metadataOptionsRef.current = metadataOptions;
}, [metadataOptions]);

const proTableColumns = useMemo<ProColumns<MonitoringDataItem>[]>(() => {
  // ... logica ...
  // Usar metadataOptionsRef.current ao inves de metadataOptions
  const fieldOptions = metadataOptionsRef.current[colConfig.key] || [];
}, [
  columnConfig,
  columnWidths,
  tableFields,
  filters,        // MANTER - necessario para filteredValue
  sortField,      // MANTER - necessario para sortOrder
  sortOrder,      // MANTER - necessario para sortOrder
  handleResize,
  getFieldValue,
  // metadataOptions removido - usar ref
]);
```

**Consequencia original**: Todas as colunas eram recalculadas quando metadataOptions mudava
**Solucao**: Usar useRef para metadataOptions

### Causa Raiz 2: useState Dentro de filterDropdown (CRITICAL)

**Localizacao**: `frontend/src/pages/DynamicMonitoringPage.tsx` linhas 481-573

```typescript
// ANTI-PATTERN GRAVE: useState dentro de useMemo
baseColumn.filterDropdown = ({ setSelectedKeys, selectedKeys, confirm, clearFilters }) => {
  const [searchText, setSearchText] = useState('');  // PROBLEMA!

  // Quando useMemo recalcula, este componente eh remontado
  // e searchText volta para ''
```

**Consequencia**: Filtros perdem estado de busca a cada recalculo de colunas.

### Causa Raiz 3: requestHandler com 10+ Dependencias (CRITICAL)

**Localizacao**: `frontend/src/pages/DynamicMonitoringPage.tsx` linhas 661-928

```typescript
const requestHandler = useCallback(async (params: any) => {
  // ... 260 linhas de logica ...
}, [
  category,
  filters,              // VOLATIL
  selectedNode,         // VOLATIL
  searchValue,          // VOLATIL
  sortField,            // VOLATIL
  sortOrder,            // VOLATIL
  filterFields,
  applyAdvancedFilters, // VOLATIL
  getFieldValue,
  metadataOptionsLoaded // VOLATIL
]);
```

**Consequencia**: Callback eh recriado a cada mudanca de estado, causando re-renders em cascata.

### Causa Raiz 4: Multiplos useEffect Chamando reload() (HIGH)

**Localizacao**: `frontend/src/pages/DynamicMonitoringPage.tsx` linhas 1060-1097

```typescript
// useEffect 1: category muda
useEffect(() => {
  // ... reset estados ...
  actionRef.current?.reload();  // RELOAD 1
}, [category]);

// useEffect 2: filters/node mudam
useEffect(() => {
  if (isFirstRender.current) {
    isFirstRender.current = false;
    return;
  }
  actionRef.current?.reload();  // RELOAD 2
}, [selectedNode, filters]);
```

**Consequencia**: Race conditions entre fetches, dados inconsistentes.

### Causa Raiz 5: Sem Debounce em Filtros (HIGH)

Cada tecla digitada em filtros dispara fetch imediato, causando multiplas requisicoes simultaneas.

### Causa Raiz 6: CATEGORY_DISPLAY_NAMES Hardcoded (MEDIUM)

**Localizacao**: linhas 96-103

```typescript
const CATEGORY_DISPLAY_NAMES: Record<string, string> = {
  'network-probes': 'Network Probes (Rede)',
  'web-probes': 'Web Probes (Aplicacoes)',
  // ... hardcoded
};
```

**Consequencia**: Novos tipos de monitoramento requerem mudanca de codigo.

### Causa Raiz 7: Problema de Sincronizacao columnConfig (CRITICAL)

**Observado via Playwright**: Botao "Colunas (0/0)" e tabela sem colunas de dados.

**Localizacao**: `frontend/src/pages/DynamicMonitoringPage.tsx` linhas 228-249

```typescript
useEffect(() => {
  // ✅ OTIMIZAÇÃO: Só atualizar quando realmente necessário
  if (defaultColumnConfig.length > 0 && tableFields.length > 0) {
    // ... logica de comparacao ...
    if (defaultKeys !== currentKeys || defaultColumnConfig.length !== columnConfig.length) {
      setColumnConfig(defaultColumnConfig);  // PROBLEMA: Nao atualiza corretamente
    }
  }
}, [defaultColumnConfig, columnConfig, tableFields.length]);
```

**Problema**: O `columnConfig` esta incluido nas dependencias do useEffect que o atualiza, criando um ciclo que pode impedir a atualizacao correta.

---

## KVs Disponiveis para Sistema Dinamico

### skills/eye/monitoring-types (KV PRINCIPAL)

**JÁ EXISTE E JÁ ESTÁ SENDO USADO** - Contém todos os monitoring types com display names por categoria.

**Localização**: KV `skills/eye/monitoring-types`
**Gerenciado por**: `MonitoringTypeManager` via prewarm_startup
**Tamanho**: ~300KB

**Estrutura**:
```json
{
  "data": {
    "version": "1.0.0",
    "last_updated": "2025-11-21T23:51:48.541978",
    "source": "prewarm_startup",
    "total_types": 28,
    "total_servers": 3,
    "successful_servers": 3,
    "servers": {
      "172.16.1.26": {
        "types": [
          {
            "id": "http_2xx",
            "display_name": "HTTP 2xx",
            "category": "web-probes",
            "job_name": "http_2xx",
            "exporter_type": "blackbox",
            "module": "http_2xx",
            "server": "172.16.1.26",
            ...
          }
        ]
      }
    }
  }
}
```

### Hook Existente: useAllMonitoringTypes

**JÁ EXISTE EM** `frontend/src/hooks/useMonitoringType.ts`

```typescript
// Retorna todas as categorias com display_name, icon, color
export function useAllMonitoringTypes() {
  const [categories, setCategories] = useState<MonitoringCategory[]>([]);
  // Chama: /api/v1/monitoring-types-dynamic/from-prometheus
  return { categories, loading, error, reload };
}
```

**Tipo MonitoringCategory** (já definido em `frontend/src/types/monitoring.ts`):
```typescript
export interface MonitoringCategory {
  schema_version: string;
  category: string;           // "network-probes"
  display_name: string;       // "Network Probes (Rede)"
  display_name_singular: string;
  icon: string;
  color: string;
  description: string;
  enabled: boolean;
  order: number;
  types: MonitoringType[];
  page_config: PageConfig;
}
```

**Solução para CATEGORY_DISPLAY_NAMES**:

1. **Usar hook existente** `useAllMonitoringTypes()`
2. **Criar Context** para cache e compartilhamento entre componentes
3. **Substituir hardcode** por lookup dinâmico

**IMPORTANTE**: Não precisa modificar backend nem KVs - tudo já existe!

---

## Arquivos de Referencia (Funcionam Corretamente)

### Exporters.tsx - Padroes Corretos

1. **Dependencias estaveis em useMemo**: Nao inclui estados volateis
2. **columnMap pattern**: Define colunas estaticamente
3. **Callbacks diretos**: Sem dependencias desnecessarias

### BlackboxTargets.tsx - Padroes Corretos

1. **Mesmo padrao que Exporters.tsx**
2. **Performance estavel**: Sem re-renders excessivos

---

## Functional Requirements (MUST)

### FR-000: Implementar Paginacao Server-Side (CRITICAL - BACKEND)

**EARS Format**: O sistema **DEVE** implementar paginacao, filtros e ordenacao no backend para eliminar processamento client-side.

**Detalhes**:
- Endpoint recebe page, pageSize, sortField, sortOrder, node, filters
- Backend aplica filtros e ordena antes de paginar
- Retorna apenas dados da pagina atual (max 50-200 items)
- Inclui total de registros para paginacao no frontend
- Inclui filterOptions extraidas dos dados filtrados

**Justificativa (Auditoria)**:
- Sistema atual baixa TODOS os dados (5MB+ para 5k registros)
- Loops O(n) e O(n^2) no requestHandler travam browser
- Consul API nao suporta paginacao nativa (Issue #9422)

**Codigo sugerido**:
```python
@router.get("/data")
async def get_monitoring_data(
    category: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=10, le=200),
    sort_field: Optional[str] = None,
    sort_order: Optional[str] = None,
    node: Optional[str] = None,
    **filters
):
    all_data = await cache_manager.get_monitoring_data(category)
    filtered = apply_filters(all_data, node, filters)
    sorted_data = apply_sort(filtered, sort_field, sort_order)
    page_data = sorted_data[(page-1)*page_size : page*page_size]

    return {
        "data": page_data,
        "total": len(filtered),
        "filterOptions": extract_options(filtered)
    }
```

### FR-001: MANTER filteredValue e sortOrder nas Dependencias

**EARS Format**: O sistema **DEVE** manter `filters`, `sortField` e `sortOrder` nas dependencias de `proTableColumns` para feedback visual correto.

**Detalhes**:
- ProTable REQUER filteredValue para icone de filtro azul
- ProTable REQUER sortOrder para seta de ordenacao
- Documentacao Ant Design confirma: "controlled mode"
- Usar useRef para metadataOptions (evitar stale closure)

**CORRECAO DA AUDITORIA**: O plano anterior sugeria REMOVER estas deps, o que QUEBRA o visual do ProTable.

**Codigo sugerido**:
```typescript
const metadataOptionsRef = useRef<Record<string, string[]>>({});

useEffect(() => {
  metadataOptionsRef.current = metadataOptions;
}, [metadataOptions]);

const proTableColumns = useMemo<ProColumns<MonitoringDataItem>[]>(() => {
  return visibleConfigs.map((colConfig) => {
    const baseColumn: ProColumns<MonitoringDataItem> = {
      // OBRIGATORIO para feedback visual
      filteredValue: filters[colConfig.key] ? [filters[colConfig.key]] : null,
      sortOrder: sortField === colConfig.key ? sortOrder : null,
    };

    // Usar ref para metadataOptions estavel
    const fieldOptions = metadataOptionsRef.current[colConfig.key] || [];
    // ...
    return baseColumn;
  });
}, [
  columnConfig, columnWidths, tableFields,
  filters,     // MANTER
  sortField,   // MANTER
  sortOrder,   // MANTER
  handleResize, getFieldValue
]);
```

### FR-002: FilterDropdown como Funcao Inline (NAO Componente)

**EARS Format**: O sistema **DEVE** manter filterDropdown como funcao inline que retorna JSX, nao componente React separado.

**CORRECAO DA AUDITORIA**: ProTable espera funcao que retorna JSX. Componente externo seria remontado a cada re-render, perdendo estado.

**Detalhes**:
- MANTER filterDropdown inline no useMemo
- Estado local (searchText) e permitido em funcao inline
- Usar metadataOptionsRef para evitar stale closure
- NAO criar componente FilterDropdown.tsx

**Codigo sugerido**:
```typescript
baseColumn.filterDropdown = ({ setSelectedKeys, selectedKeys, confirm, clearFilters }) => {
  // Estado local OK aqui - funcao inline
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

### FR-003: Consolidar useEffects em Reload Unico

**EARS Format**: O sistema **DEVE** consolidar os dois `useEffect` que chamam `reload()` em um unico ponto de controle.

**Detalhes**:
- Remover `useEffect` duplicado para filters/selectedNode
- Usar callback em setFilters e setSelectedNode para chamar reload
- Evitar race conditions entre fetches

**Codigo sugerido**:
```typescript
// Handler unificado para mudancas que requerem reload
const handleFilterChange = useCallback((newFilters: Record<string, string | undefined>) => {
  setFilters(newFilters);
  // Debounced reload (FR-004)
}, []);

const handleNodeChange = useCallback((nodeAddr: string) => {
  setSelectedNode(nodeAddr);
  actionRef.current?.reload();  // Node muda raramente, reload imediato
}, []);

// Unico useEffect para category reset
useEffect(() => {
  setFilters({});
  setSelectedNode('all');
  // ... outros resets ...
  actionRef.current?.reload();
}, [category]);
```

### FR-004: Debounce com AbortController para Cancelar Requests

**EARS Format**: O sistema **DEVE** implementar debounce de 300ms COM AbortController para cancelar requests anteriores.

**CORRECAO DA AUDITORIA**: Debounce sozinho NAO resolve race conditions. Request anterior pode resolver depois do novo e sobrescrever dados.

**Detalhes**:
- Debounce para searchValue e filters
- AbortController para cancelar request anterior
- isMountedRef para evitar setState apos unmount
- Sem debounce para selectedNode (mudanca pontual)

**Codigo sugerido**:
```typescript
import { useDebouncedCallback } from 'use-debounce';

const abortControllerRef = useRef<AbortController | null>(null);
const isMountedRef = useRef(true);

useEffect(() => {
  isMountedRef.current = true;
  return () => {
    isMountedRef.current = false;
    abortControllerRef.current?.abort();
  };
}, []);

const requestHandler = useCallback(async (params: any) => {
  // CANCELAR request anterior
  abortControllerRef.current?.abort();
  abortControllerRef.current = new AbortController();

  try {
    const response = await api.get('/monitoring/data', {
      signal: abortControllerRef.current.signal,
      params: { page: params.current, ...filters }
    });

    if (!isMountedRef.current) return { data: [], total: 0, success: true };
    return response;
  } catch (error) {
    if (error.name === 'AbortError') {
      return { data: [], total: 0, success: true };
    }
    throw error;
  }
}, [filters, ...]);

const debouncedReload = useDebouncedCallback(() => {
  actionRef.current?.reload();
}, 300);
```

### FR-005: Remover CATEGORY_DISPLAY_NAMES Hardcoded (Solucao Simples)

**EARS Format**: O sistema **DEVE** remover o hardcode e usar dados que JA vem do tableFields ou formatacao dinamica.

**CORRECAO DA AUDITORIA**: Context global e overhead desnecessario que:
- Forca download de ~300KB em TODAS as paginas
- Duplica chamadas ao endpoint
- Adiciona re-renders em toda aplicacao

**Detalhes**:
- NAO criar Context global
- Usar dados de tableFields que JA tem category_display_name
- Fallback para formatacao simples do slug

**Codigo sugerido**:
```typescript
// REMOVER
const CATEGORY_DISPLAY_NAMES: Record<string, string> = {
  'network-probes': 'Network Probes (Rede)',
  // ...
};

// ADICIONAR - funcao simples de formatacao
const formatCategoryName = (slug: string): string => {
  return slug
    .split('-')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
};

// Usar no componente - dados JA vem do backend
const categoryTitle = tableFields[0]?.category_display_name || formatCategoryName(category);
```

**IMPORTANTE**: Solucao simples sem Context adicional!

### FR-007: Corrigir Sincronizacao de columnConfig

**EARS Format**: O sistema **DEVE** corrigir a logica de atualizacao do `columnConfig` para evitar ciclos de dependencia.

**Detalhes**:
- Remover `columnConfig` das dependencias do useEffect que o atualiza
- Usar `useRef` para comparar valores anteriores sem dependencias
- Garantir que colunas renderizem corretamente apos tableFields carregar

**Codigo sugerido**:
```typescript
const prevDefaultColumnConfigRef = useRef<string>('');

useEffect(() => {
  if (defaultColumnConfig.length > 0 && tableFields.length > 0) {
    const defaultKeys = defaultColumnConfig.map(c => c.key).sort().join(',');

    // Comparar com valor anterior (sem columnConfig nas deps)
    if (prevDefaultColumnConfigRef.current !== defaultKeys) {
      setColumnConfig(defaultColumnConfig);
      prevDefaultColumnConfigRef.current = defaultKeys;
    }
  }
}, [defaultColumnConfig, tableFields.length]); // SEM columnConfig aqui!
```

### FR-006: Criar Testes de Baseline para monitoring_unified.py

**EARS Format**: O sistema **DEVE** criar arquivo de testes `backend/tests/test_monitoring_unified_baseline.py`.

**Detalhes**:
- Testes de performance (latencia P50, P95)
- Testes funcionais (filtros, paginacao, ordenacao)
- Testes de integracao com cache
- Cobertura minima 80%

**Estrutura de testes baseada em `test_baseline_completo.py` existente**:

```python
# backend/tests/test_monitoring_unified_baseline.py
"""
Testes de baseline para endpoints de monitoramento unificado.
Garante que correcoes de performance nao quebram funcionalidades.
"""
import pytest
import httpx
import time

BACKEND_URL = "http://localhost:5000/api/v1"

class TestMonitoringUnifiedBaseline:
    """Testes baseline para /monitoring/data endpoint"""

    @pytest.fixture
    async def client(self):
        async with httpx.AsyncClient(timeout=60.0) as client:
            yield client

    async def test_network_probes_returns_data(self, client):
        """Endpoint retorna dados para network-probes"""
        response = await client.get(f"{BACKEND_URL}/monitoring/data?category=network-probes")
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") is True
        assert "data" in data
        assert len(data["data"]) > 0

    async def test_filters_work_correctly(self, client):
        """Filtros por company/site funcionam"""
        response = await client.get(
            f"{BACKEND_URL}/monitoring/data?category=network-probes&company=Agro%20Xingu"
        )
        assert response.status_code == 200
        data = response.json()
        # Todos os registros devem ter company = Agro Xingu
        for item in data.get("data", []):
            assert item.get("Meta", {}).get("company") == "Agro Xingu"

    async def test_performance_under_100ms(self, client):
        """Endpoint responde em menos de 100ms (com cache)"""
        # Primeira chamada (warm cache)
        await client.get(f"{BACKEND_URL}/monitoring/data?category=network-probes")

        # Segunda chamada (cached)
        start = time.time()
        response = await client.get(f"{BACKEND_URL}/monitoring/data?category=network-probes")
        duration = (time.time() - start) * 1000

        assert response.status_code == 200
        assert duration < 100, f"Resposta demorou {duration:.0f}ms (esperado <100ms)"

    async def test_all_categories_work(self, client):
        """Todos os 8 tipos de categoria funcionam"""
        categories = [
            "network-probes", "web-probes", "system-exporters",
            "database-exporters", "infrastructure-exporters",
            "hardware-exporters", "network-devices", "custom-exporters"
        ]
        for cat in categories:
            response = await client.get(f"{BACKEND_URL}/monitoring/data?category={cat}")
            assert response.status_code == 200, f"Falha em {cat}"

    async def test_metadata_contains_required_fields(self, client):
        """_metadata contem campos de performance"""
        response = await client.get(f"{BACKEND_URL}/monitoring/data?category=network-probes")
        data = response.json()
        metadata = data.get("_metadata", {})

        # Campos esperados de performance
        assert "source_name" in metadata or "cache_status" in metadata
```

**Referencia**: Ver `backend/tests/test_baseline_completo.py` para padrao de testes existente.

---

## Non-Functional Requirements (SHOULD)

### NFR-001: Reducao de Re-renders

O sistema **DEVERIA** reduzir re-renders em 90% por interacao de usuario.

**Metricas alvo**:
- Re-renders por mudanca de filtro: 1-2 (vs 10+ atual)
- Re-renders por ordenacao: 1-2 (vs 10+ atual)
- Re-renders por digitacao: 0-1 com debounce

### NFR-002: Estabilidade de Filtros

O sistema **DEVERIA** manter estado de filtros abertos durante todas as interacoes.

### NFR-003: Tempo de Resposta UI

O sistema **DEVERIA** responder a interacoes do usuario em menos de 100ms.

### NFR-004: Compatibilidade Total

O sistema **DEVERIA** manter 100% das funcionalidades existentes:
- CRUD completo
- Filtros por coluna
- Ordenacao
- Paginacao
- Exportacao CSV
- Busca global
- Filtros avancados
- Selecao em batch

---

## Interface Requirements (SHALL)

### IR-001: Props Mantidas

O componente **MANTERA** mesma interface de props:

```typescript
interface DynamicMonitoringPageProps {
  category: string;
}
```

### IR-002: Comportamento Visual Identico

O componente **MANTERA** comportamento visual identico para usuario final.

---

## Design Constraints (MUST)

### DC-001: Nao Quebrar Outras Paginas

O sistema **NAO DEVE** quebrar nenhuma das 8 paginas que usam DynamicMonitoringPage:
- `/monitoring/network-probes`
- `/monitoring/web-probes`
- `/monitoring/system-exporters`
- `/monitoring/database-exporters`
- `/monitoring/infrastructure-exporters`
- `/monitoring/hardware-exporters`
- `/monitoring/network-devices`
- `/monitoring/custom-exporters`

### DC-002: Usar Padroes de Exporters.tsx

As correcoes **DEVEM** seguir os padroes do Exporters.tsx que funcionam corretamente.

### DC-003: Sem Dependencias Externas Novas

As correcoes **NAO DEVEM** adicionar dependencias externas alem de `use-debounce` (ja comum em React).

### DC-004: Testes Antes e Depois

O sistema **DEVE** ter testes passando antes e depois das mudancas.

---

## Arquivos a Serem Modificados

### Backend (FASE 1 - CRITICO)

| Arquivo | Modificacao | Linhas Estimadas | Risco |
|---------|-------------|------------------|-------|
| `backend/api/monitoring_unified.py` | Paginacao, filtros, ordenacao server-side | ~150 linhas | Alto |
| `backend/core/monitoring_cache.py` | **NOVO** - Cache intermediario para Consul | ~100 linhas | Medio |
| `backend/core/monitoring_filters.py` | **NOVO** - Funcoes de filtro e ordenacao | ~80 linhas | Baixo |
| `backend/tests/test_monitoring_unified_baseline.py` | **NOVO** - Testes com fixtures (nao infra real) | ~200 linhas | Baixo |

### Frontend (FASES 2-3)

| Arquivo | Modificacao | Linhas Estimadas | Risco |
|---------|-------------|------------------|-------|
| `frontend/src/pages/DynamicMonitoringPage.tsx` | AbortController, isMountedRef, useRef metadataOptions, debounce, remover hardcode | ~150 linhas | Alto |
| `frontend/src/components/MetadataFilterBar.tsx` | Integrar debounce | ~20 linhas | Baixo |

**NOTA**:
- NAO criar `FilterDropdown.tsx` - manter como funcao inline
- NAO criar `MonitoringCategoriesContext.tsx` - usar dados existentes
- NAO modificar `monitoring_types_dynamic.py` - backend de paginacao eh separado

---

## Ganhos Esperados

| Metrica | Antes (estimado) | Meta Minima | Meta Ideal | Como Medir |
|---------|-----------------|-------------|------------|------------|
| **Payload inicial** | ~5MB (5k registros) | <200KB | <100KB | Network tab |
| **Tempo carregamento** | ~8s | <2s | <500ms | Performance.measure() |
| **Re-renders/interacao** | 15-20 | ≤5 | ≤3 | React Profiler |
| **Memory heap** | ~150MB | <50MB | <20MB | Chrome Memory |
| **Requests simultaneos** | 5-10 | ≤2 | 1 | Network tab |
| **Race conditions** | Presentes | Eliminadas | Eliminadas | Logs/testes |
| **Filtros perdendo estado** | Frequente | Nunca | Nunca | Teste manual |

---

## Riscos e Mitigacoes

| Risco | Probabilidade | Impacto | Mitigacao |
|-------|---------------|---------|-----------|
| Regressao em funcionalidades | Media | Alto | Testar todas as 8 paginas manualmente |
| Incompatibilidade com ProTable | Baixa | Alto | Usar patterns do Exporters.tsx |
| Performance piora | Baixa | Alto | Medir com React DevTools Profiler |
| Debounce muito longo | Baixa | Baixo | Configuravel (300ms padrao) |
| Rolldown-vite experimental | Baixa | Medio | Usar Vite oficial se houver problemas de build |

---

## Dependencias Tecnicas

1. **use-debounce** - Package npm para debounce (se nao existir, usar setTimeout)
2. **React.memo** - Para memoizacao do FilterDropdown
3. **useCallback estavel** - Para handlers sem dependencias volateis
4. **ProTable onChange** - Para controle de sort/filter externo

---

## Estimativa de Complexidade e Tempo

**Tempo Total Realista: 18-23 dias** (nao 11 do plano anterior)

| Fase | Descricao | Tempo | Complexidade |
|------|-----------|-------|--------------|
| FASE 0 | Pre-requisitos e Baseline | 2-3 dias | Baixa |
| FASE 1 | Backend - Paginacao Server-Side | 5-7 dias | Alta |
| FASE 2 | Frontend - Correcoes Criticas | 3-4 dias | Alta |
| FASE 3 | Frontend - Otimizacoes React | 2-3 dias | Media |
| FASE 4 | Features Avancadas (opcional) | 3-4 dias | Media |
| FASE 5 | Validacao e Deploy | 2-3 dias | Media |

**Justificativa do tempo maior**:
- Backend requer paginacao completa com cache
- Testes precisam de fixtures adequadas
- QA deve validar 8 paginas com volume real
- Metricas baseline precisam ser capturadas

---

## Notas de Implementacao

1. **ORDEM DE EXECUCAO - Backend First**:
   - **FASE 0**: Pre-requisitos e Baseline
   - **FASE 1**: Backend - Paginacao Server-Side (CRITICAL)
   - **FASE 2**: Frontend - Correcoes Criticas
   - **FASE 3**: Frontend - Otimizacoes React
   - **FASE 4**: Features Avancadas (opcional)
   - **FASE 5**: Validacao e Deploy

2. **Testar cada fase**: Validar performance com React DevTools

3. **Rollback facil**: Manter backup do arquivo original

4. **Profile antes/depois**: Usar React DevTools Profiler para medir ganhos

5. **Validacao E2E**:
   - Testar todas as 8 paginas de monitoramento
   - Verificar que filtros funcionam em todas
   - Confirmar que ordenacao funciona
   - Testar exportacao CSV
   - Testar com volume real (5k+ registros)

---

## O que NAO Fazer (CRITICO)

1. **NUNCA** remover `filteredValue`/`sortOrder` das deps - QUEBRA visual do ProTable
2. **NUNCA** processar dados no cliente com volume > 1000 registros
3. **NUNCA** criar FilterDropdown como componente separado - deve ser funcao inline
4. **NUNCA** usar debounce sem AbortController - race conditions persistem
5. **NUNCA** ignorar paginacao server-side - browser travara
6. **NUNCA** criar Context global para display names - overhead desnecessario
7. **NUNCA** fazer testes que dependem de infra externa - CI/CD quebra

---

## O que DEVE Fazer (OBRIGATORIO)

1. **SEMPRE** paginar no servidor - nunca baixar todos os dados
2. **SEMPRE** cancelar requests anteriores com AbortController
3. **SEMPRE** verificar isMounted antes de setState
4. **SEMPRE** medir com React Profiler antes e depois
5. **SEMPRE** testar com volume real (5k+ registros)
6. **SEMPRE** usar fixtures nos testes de backend
7. **SEMPRE** manter filterDropdown como funcao inline

---

## Traceability

- **Related to**: SPEC-PERF-001 (NodeSelector performance)
- **Baseado em**: AUDITORIA-COMPLETA-CONSOLIDADA-SPEC-PERF-002.md
- **Auditores**: Claude, Cursor, Codex, Gemini-3
- **Blocks**: Nenhum
- **Blocked by**: Nenhum
- **Tags**: performance, backend-first, pagination, react, refactoring, critical
