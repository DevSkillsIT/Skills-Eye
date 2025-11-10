# 🔍 Análise de Performance - Página Services (PARTE 2)

**Data:** 2025-11-10 16:20
**Profile:** Firefox 2025-11-10 16.03 profile.json
**Status:** Após otimizações P0

---

## 📊 RESULTADOS APÓS OTIMIZAÇÕES P0

### Métricas Comparativas

| Métrica | Profile 15.42 (ANTES) | Profile 16.03 (DEPOIS) | Resultado |
|---------|----------------------|------------------------|-----------|
| **Paint operations** | ~22 | 124 | ❌ **+463% PIORA** |
| **Style recalculations** | 615 | 588 | ✅ **-4.4% melhoria** |
| **Largest Contentful Paint** | N/A | 250ms, 79ms, 240ms | ⚠️ **Variável** |
| **Network requests** | N/A | 2,909 | ❌ **MUITO ALTO** |
| **Garbage Collection** | N/A | 15 eventos | ⚠️ **Pode causar pausas** |

### ⚠️ PROBLEMA CRÍTICO IDENTIFICADO

**O profile não capturou a página correta!**
- Esperado: `http://localhost:8081/services`
- Capturado: `chrome://browser/content/browser.xhtml` (página interna do Firefox)

**Isso explica:**
- Métricas inconsistentes com análise anterior
- Estrutura diferente dos markers (dict vs array)
- Dificuldade em comparar resultados

---

## 🔬 ANÁLISE PROFUNDA DO CÓDIGO

### Problema #1: StrictMode Causa Duplicação (Comportamento Normal)

**Evidência no código:**
```tsx
// frontend/src/main.tsx
createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
```

**Impacto:**
- useEffect executa 2x em dev (mount → unmount → mount)
- Requisições HTTP duplicadas no console
- Logs duplicados
- **NÃO afeta produção** (StrictMode desabilitado automaticamente)

**Pesquisa Web Confirma:**
> "StrictMode does not degrade performance in production - it is a powerful debugging tool that only runs in development mode. The double-rendering only happens in development."

**Ação:** ✅ **MANTER StrictMode** (detecta bugs importantes)

---

### Problema #2: Múltiplas Requisições no Mount

**Cadeia de Execução Identificada:**

```
App.tsx (monta)
  └─> MetadataFieldsProvider (carrega)
       ├─> GET /api/v1/metadata-fields/ (10s timeout) ← UMA REQUISIÇÃO
       │
  └─> Services.tsx (monta)
       ├─> useTableFields() ─┐
       ├─> useFormFields()  ─┤── REUTILIZAM contexto (0 requests extras)
       ├─> useFilterFields()─┘
       │
       └─> useEffect (linha 734) ← Aguarda filterFields carregar
            └─> requestHandler()
                 └─> GET /api/v1/services ← UMA REQUISIÇÃO
```

**Descoberta:**
- ✅ **APENAS 2 requisições** no mount (metadata + services)
- ✅ Context compartilhado evita duplicação
- ⚠️ StrictMode **duplica cada uma** em dev (total: 4 logs no console)

**Problema Real:**
- Timeout alto (10s) no cold start
- Backend faz SSH para Prometheus servers

---

### Problema #3: useEffect com Muitas Dependências

**Código atual (Services.tsx:734):**
```tsx
useEffect(() => {
  if (filterFields.length === 0 || filterFieldsLoading) {
    return;
  }

  requestHandler({}, {}, {}).then(result => {
    if (result.data) {
      setTableSnapshot(result.data);
    }
  });
}, [filterFieldsLoading, selectedNode, advancedConditions, advancedOperator, searchValue]);
```

**Problema:**
- Qualquer mudança em 5 dependências → reload completo
- `requestHandler` não está memoizado → recriado em cada render
- **Causa:** Layout Shift durante recarregamentos

---

### Problema #4: Cálculos Pesados em useEffect (Linha 675)

**Código atual:**
```tsx
useEffect(() => {
  if (tableSnapshot.length === 0) return;

  // Extrair valores únicos para filtros
  const options: Record<string, Set<string>> = {};
  const DEFAULT_MODULES = ['blackbox_exporter', 'node_exporter', 'windows_exporter'];

  tableSnapshot.forEach((item) => {
    Object.entries(item.meta || {}).forEach(([key, value]) => {
      if (value !== null && value !== undefined && value !== '') {
        if (!options[key]) options[key] = new Set();
        options[key].add(String(value));
      }
    });
  });

  // ... mais processamento ...

  setMetadataOptions(finalOptions);
  setSummary(nextSummary);
}, [tableSnapshot]);
```

**Problemas:**
- Executa **a cada mudança** em `tableSnapshot`
- Loop duplo: `forEach` + `Object.entries`
- Complexidade: **O(n × m)** onde n=serviços, m=campos metadata
- Dispara **2 state updates** (setMetadataOptions + setSummary)
- **Cada state update = 1 re-render**

**Impacto:**
- Para 163 serviços × ~20 campos = **3,260 iterações**
- Causa múltiplos re-renders → Layout Shift

---

### Problema #5: visibleColumns Recalcula Sempre (Linha 1091)

**Código atual:**
```tsx
const visibleColumns = useMemo(() => {
  // ... lógica complexa ...
  return allColumns.filter(col => {
    const config = columnConfig.find(c => c.key === col.key);
    return config ? config.visible : true;
  });
}, [columnConfig, columnMap, columnWidths, handleResize]);
```

**Problemas:**
- `handleResize` muda a cada render (callback não memoizado)
- `columnWidths` é objeto mutável
- useMemo **NÃO funciona** (dependências sempre mudam)
- **Recalcula colunas em TODA renderização** → Layout Shift

---

## 🎯 SOLUÇÕES PROPOSTAS (P1 - ALTO IMPACTO)

### Solução P1.1: Memoizar requestHandler com useCallback

**ANTES:**
```tsx
const requestHandler = useCallback(
  async (pagination: any, filters: any, sorter: any) => {
    // ... lógica ...
  },
  [filterFieldsLoading, selectedNode, ...] // Muitas dependências
);
```

**DEPOIS:**
```tsx
// SEPARAR lógica de carregamento
const loadServicesData = useCallback(async () => {
  if (filterFieldsLoading || filterFields.length === 0) return;

  const query = buildQueryParams();
  const { data } = await consulAPI.getServices(query);

  // Aplicar filtros locais
  let filtered = flattenServices(data);
  filtered = applyAdvancedFilters(filtered);
  filtered = applyTextSearch(filtered);

  setTableSnapshot(filtered);
}, [filterFieldsLoading, filterFields.length, selectedNode, advancedConditions, searchValue]);

// requestHandler só para ProTable (sem lógica pesada)
const requestHandler = useCallback(async (params: any) => {
  // Retorna dados do snapshot (já filtrados)
  return {
    data: tableSnapshot,
    success: true,
    total: tableSnapshot.length
  };
}, [tableSnapshot]);
```

**Resultado:**
- ✅ Reduz re-renders desnecessários
- ✅ Separa lógica de carregamento vs exibição
- ✅ ProTable recebe dados estáveis

---

### Solução P1.2: Debounce de Cálculos Pesados

**Implementação:**
```tsx
import { debounce } from 'lodash-es';

// Debounce de cálculo de metadataOptions
const calculateMetadataOptions = useMemo(
  () => debounce((data: ServiceTableItem[]) => {
    // ... lógica de extração ...
    setMetadataOptions(finalOptions);
    setSummary(nextSummary);
  }, 150), // 150ms de delay
  []
);

useEffect(() => {
  if (tableSnapshot.length === 0) return;
  calculateMetadataOptions(tableSnapshot);
}, [tableSnapshot, calculateMetadataOptions]);
```

**Resultado:**
- ✅ Agrupa múltiplas mudanças em 150ms
- ✅ Reduz state updates de N para 1
- ✅ Menos re-renders → menos Layout Shift

---

### Solução P1.3: Virtualização da Tabela (react-window)

**Instalação:**
```bash
npm install react-window @types/react-window
```

**Implementação:**
```tsx
import { FixedSizeList as List } from 'react-window';

<ProTable
  // ... props existentes ...
  components={{
    body: {
      wrapper: ({ children, ...props }) => (
        <List
          height={600}
          itemCount={tableSnapshot.length}
          itemSize={54} // Altura de cada linha
          width="100%"
        >
          {({ index, style }) => (
            <div style={style}>
              {children[index]}
            </div>
          )}
        </List>
      )
    }
  }}
/>
```

**Resultado:**
- ✅ Renderiza **APENAS linhas visíveis** (10-15 em vez de 163)
- ✅ **Melhoria estimada:** -80% em rendering time
- ✅ Scroll suave mesmo com milhares de registros

**Referência:** Encontrado em pesquisa web - "virtualize long lists with react-window for Table/List components, which renders only visible items"

---

### Solução P1.4: Otimizar visibleColumns

**ANTES:**
```tsx
const visibleColumns = useMemo(() => {
  // ... filtrar colunas ...
}, [columnConfig, columnMap, columnWidths, handleResize]); // ❌ Dependências instáveis
```

**DEPOIS:**
```tsx
// 1. Estabilizar handleResize
const handleResize = useCallback(
  (key: string) => (e: React.SyntheticEvent, { size }: any) => {
    setColumnWidths(prev => ({ ...prev, [key]: size.width }));
  },
  [] // ✅ SEM dependências
);

// 2. Estabilizar columnWidths (usar ref)
const columnWidthsRef = useRef<Record<string, number>>({});
const setColumnWidths = (updater: (prev: Record<string, number>) => Record<string, number>) => {
  columnWidthsRef.current = updater(columnWidthsRef.current);
  setColumnWidthsState(columnWidthsRef.current);
};

// 3. visibleColumns REALMENTE memoizado
const visibleColumns = useMemo(() => {
  return allColumns.filter(col => {
    const config = columnConfig.find(c => c.key === col.key);
    return config ? config.visible : true;
  });
}, [columnConfig, allColumns]); // ✅ APENAS dependências estáveis
```

**Resultado:**
- ✅ useMemo funciona de verdade
- ✅ Colunas NÃO recalculam em cada render
- ✅ Menos reflows → menos Layout Shift

---

### Solução P1.5: Code Splitting da Página

**Implementação:**
```tsx
// App.tsx
import { lazy, Suspense } from 'react';
import { Skeleton } from 'antd';

const Services = lazy(() => import('./pages/Services'));
const BlackboxTargets = lazy(() => import('./pages/BlackboxTargets'));
const Installer = lazy(() => import('./pages/Installer'));

// No Router
<Route
  path="/services"
  element={
    <Suspense fallback={<Skeleton active paragraph={{ rows: 10 }} />}>
      <Services />
    </Suspense>
  }
/>
```

**Resultado:**
- ✅ Reduz bundle inicial
- ✅ Faster First Contentful Paint
- ✅ Carrega componente sob demanda

---

## 🚀 SOLUÇÕES COMPLEMENTARES (P2 - MÉDIO IMPACTO)

### P2.1: Memoizar Componentes Pesados

```tsx
const ServiceRow = memo(({ record, onEdit, onDelete }: ServiceRowProps) => {
  return (
    <tr>
      {/* ... conteúdo da linha ... */}
    </tr>
  );
}, (prevProps, nextProps) => {
  // Só re-renderiza se record mudou
  return prevProps.record.id === nextProps.record.id &&
         prevProps.record.meta === nextProps.record.meta;
});
```

---

### P2.2: Web Workers para Cálculos Pesados

```tsx
// metadata-worker.ts
self.addEventListener('message', (e) => {
  const { tableSnapshot } = e.data;

  // Processar em thread separada
  const options = extractMetadataOptions(tableSnapshot);
  const summary = calculateSummary(tableSnapshot);

  self.postMessage({ options, summary });
});

// Services.tsx
const worker = useMemo(() => new Worker(new URL('./metadata-worker.ts', import.meta.url)), []);

useEffect(() => {
  worker.postMessage({ tableSnapshot });
  worker.onmessage = (e) => {
    setMetadataOptions(e.data.options);
    setSummary(e.data.summary);
  };
}, [tableSnapshot]);
```

**Resultado:**
- ✅ Cálculos pesados NÃO bloqueiam UI
- ✅ Thread principal livre → sem travamentos

---

### P2.3: Backend - Cache Redis

**Backend (app.py):**
```python
import redis
import json

redis_client = redis.Redis(host='localhost', port=6379, decode_responses=True)

@app.get("/api/v1/services")
async def get_services():
    # Tentar cache primeiro (TTL 30s)
    cache_key = "services:list"
    cached = redis_client.get(cache_key)

    if cached:
        return json.loads(cached)

    # Se não tem cache, buscar do Consul
    services = await consul_manager.get_all_services()

    # Cachear por 30s
    redis_client.setex(cache_key, 30, json.dumps(services))

    return services
```

**Resultado:**
- ✅ Resposta instantânea (<10ms) para dados cacheados
- ✅ Reduz carga no Consul
- ✅ TTL configurável

---

## 📈 IMPACTO ESTIMADO DAS OTIMIZAÇÕES

| Solução | Implementação | Impacto CLS | Impacto TTI | Dificuldade |
|---------|--------------|-------------|-------------|-------------|
| **P1.1 - Memoizar requestHandler** | 2h | 🟢 Médio | 🟢 Médio | 🟢 Baixa |
| **P1.2 - Debounce cálculos** | 1h | 🟢 Alto | 🟢 Médio | 🟢 Baixa |
| **P1.3 - Virtualização** | 4h | 🟡 Baixo | 🟢 Alto | 🟡 Média |
| **P1.4 - Otimizar visibleColumns** | 2h | 🟢 Alto | 🟢 Alto | 🟡 Média |
| **P1.5 - Code Splitting** | 1h | 🟡 Baixo | 🟢 Alto | 🟢 Baixa |
| **P2.1 - Memoizar Rows** | 3h | 🟢 Médio | 🟡 Baixo | 🟡 Média |
| **P2.2 - Web Workers** | 6h | 🟢 Alto | 🟢 Alto | 🔴 Alta |
| **P2.3 - Redis Cache** | 4h | 🟡 Baixo | 🟢 Alto | 🟡 Média |

**Legenda:**
- 🟢 = Alto impacto / Fácil
- 🟡 = Médio impacto / Moderado
- 🔴 = Baixo impacto / Difícil

---

## 🎯 PLANO DE IMPLEMENTAÇÃO RECOMENDADO

### SPRINT 1 - Quick Wins (1 semana)
1. ✅ **P1.2** - Debounce de cálculos (1h)
2. ✅ **P1.5** - Code Splitting (1h)
3. ✅ **P1.1** - Memoizar requestHandler (2h)
4. ✅ **P1.4** - Otimizar visibleColumns (2h)

**Resultado esperado:** CLS < 0.1, TTI < 2s

---

### SPRINT 2 - Performance Boost (2 semanas)
5. ✅ **P1.3** - Virtualização com react-window (4h)
6. ✅ **P2.3** - Backend Redis cache (4h)
7. ✅ **P2.1** - Memoizar componentes (3h)

**Resultado esperado:** CLS < 0.05, TTI < 1s

---

### SPRINT 3 - Advanced (opcional)
8. ⚠️ **P2.2** - Web Workers (6h)
   - Apenas se ainda houver problemas após Sprint 1 e 2

---

## 🔍 COMO MEDIR RESULTADOS

### 1. Lighthouse CI (Automatizado)

```bash
npm install -g @lhci/cli

# Criar arquivo lighthouserc.js
{
  "ci": {
    "collect": {
      "url": ["http://localhost:8081/services"],
      "numberOfRuns": 5
    },
    "assert": {
      "assertions": {
        "cumulative-layout-shift": ["warn", {"maxNumericValue": 0.1}],
        "interactive": ["error", {"maxNumericValue": 3000}]
      }
    }
  }
}

# Executar
lhci autorun
```

---

### 2. Firefox Profiler (Manual)

**IMPORTANTE:** Capturar profile CORRETO!

1. Abrir Firefox
2. Ir para `about:profiling`
3. Selecionar preset: **Web Developer**
4. **LIMPAR cache** (Ctrl+Shift+Delete)
5. **Recarregar página** (Ctrl+R)
6. Clicar **Capture** imediatamente
7. Aguardar 5 segundos
8. Clicar **Stop**
9. **Verificar** se capturou `http://localhost:8081/services` (não páginas internas do Firefox!)
10. Salvar JSON

---

### 3. Chrome DevTools Performance

1. Abrir DevTools (F12)
2. Aba **Performance**
3. **Limpar cache**
4. Click **Record**
5. Recarregar página (Ctrl+R)
6. Aguardar 5s
7. **Stop**
8. Analisar:
   - **Layout Shifts** (devem ser < 5)
   - **Long Tasks** (devem ser < 50ms)
   - **Total Blocking Time** (deve ser < 200ms)

---

## 🧪 TESTE A/B COMPARATIVO

**Criar branch de teste:**
```bash
git checkout -b perf/p1-optimizations
# Implementar P1.1 a P1.5
git commit -m "perf: Implementar otimizações P1"
```

**Medir ANTES:**
```bash
git checkout main
npm run dev
# Capturar Lighthouse + Firefox Profile
```

**Medir DEPOIS:**
```bash
git checkout perf/p1-optimizations
npm run dev
# Capturar Lighthouse + Firefox Profile
```

**Comparar:**
- CLS: deve reduzir > 50%
- TTI: deve reduzir > 40%
- Paint ops: deve reduzir > 60%

---

## 📚 REFERÊNCIAS TÉCNICAS

### Pesquisa Web Realizada

1. **Ant Design Performance Issues**
   - GitHub Issue #51409: "AntD v5 is very slow" (Oct 2024)
   - Solução: Virtualização + memoização

2. **ProTable Optimization**
   - Discussão #44120: "Table performance optimization"
   - Técnicas: pagination, virtualization, React.memo

3. **React 19 StrictMode**
   - Comportamento esperado de duplicação em dev
   - NÃO impacta produção

4. **Virtualization Best Practices**
   - react-window para listas longas
   - Renderizar apenas itens visíveis

---

## ✅ CHECKLIST DE IMPLEMENTAÇÃO

**Antes de começar:**
- [ ] Criar branch `perf/p1-optimizations`
- [ ] Capturar métricas baseline (Lighthouse + Profile)
- [ ] Fazer backup do Services.tsx atual

**Durante implementação:**
- [ ] Implementar P1.2 (Debounce)
- [ ] Testar: CLS melhorou?
- [ ] Implementar P1.5 (Code Splitting)
- [ ] Testar: Bundle reduziu?
- [ ] Implementar P1.1 (Memoizar requestHandler)
- [ ] Testar: Re-renders reduziram?
- [ ] Implementar P1.4 (Otimizar visibleColumns)
- [ ] Testar: Layout Shift reduziu?

**Após implementação:**
- [ ] Capturar novas métricas
- [ ] Comparar com baseline
- [ ] Se CLS < 0.1 → Merge para main
- [ ] Se não → Investigar P1.3 (Virtualização)

---

## 🎯 META FINAL

**Web Vitals Targets:**
- ✅ CLS (Cumulative Layout Shift) < 0.1
- ✅ LCP (Largest Contentful Paint) < 2.5s
- ✅ TTI (Time to Interactive) < 3.0s
- ✅ TBT (Total Blocking Time) < 200ms

**User Experience:**
- ✅ Página carrega em < 2s
- ✅ SEM travamentos durante scroll
- ✅ SEM "pulos" de conteúdo
- ✅ Feedback visual durante carregamento

---

**Próximo passo:** Implementar P1.2 (Debounce) como quick win inicial.
