# Plano de Implementação - SPEC-PERF-002-FIX

## Metadata

| Campo | Valor |
|-------|-------|
| SPEC | SPEC-PERF-002-FIX |
| Status | PENDENTE |
| Tempo Total | 6-7 horas |
| Prioridade | CRÍTICA |

---

## Visão Geral

Este plano detalha a implementação das correções identificadas no documento de consolidação SPEC-PERF-002, excluindo o item 2 (Filtros Avançados).

---

## FASE 1: HOJE (2 horas)

### Milestone 1.1: Ordenação Descendente
**Requisito:** REQ-003 | **Tempo:** 5 minutos

#### Tarefas:
1. Abrir `frontend/src/services/api.ts`
2. Localizar função `getMonitoringData` (~linha 900-933)
3. Modificar conversão de `sort_order`:

```typescript
// DE (incorreto):
if (options.sort_order) {
  params.sort_order = options.sort_order === 'ascend' ? 'asc' : 'desc';
}

// PARA (correto):
if (options.sort_order) {
  params.sort_order = options.sort_order;
}
```

4. Testar ordenação ascendente e descendente

---

### Milestone 1.2: Debounce com Cancelamento
**Requisito:** REQ-006 | **Tempo:** 15 minutos

#### Tarefas:
1. Abrir `frontend/src/pages/DynamicMonitoringPage.tsx`
2. Localizar `debouncedReload` (~linha 318-320)
3. Adicionar cancelamento de abort controller:

```typescript
const debouncedReload = useDebouncedCallback(() => {
  // Cancelar request anterior primeiro
  if (abortControllerRef.current) {
    abortControllerRef.current.abort();
    console.log('[DynamicMonitoringPage] Request anterior cancelada');
  }

  // Agora fazer novo reload
  actionRef.current?.reload();
}, 300);
```

4. Testar digitação rápida na busca

---

### Milestone 1.3: Remover Duplo Disparo de Filtros
**Requisito:** REQ-004 | **Tempo:** 30 minutos

#### Tarefas:
1. Em `DynamicMonitoringPage.tsx`, localizar MetadataFilterBar (~linha 1374-1385)
2. Remover reload do onChange:

```typescript
<MetadataFilterBar
  onChange={(newFilters) => {
    setFilters(newFilters);
    // actionRef.current?.reload();  REMOVER ESTA LINHA
  }}
  onReset={() => {
    setFilters({});
    actionRef.current?.reload();
  }}
/>
```

3. Localizar useEffect de filters (~linha 1104-1115)
4. Substituir reload direto por debouncedReload:

```typescript
useEffect(() => {
  if (isFirstRender.current) {
    isFirstRender.current = false;
    return;
  }
  debouncedReload();
}, [selectedNode, filters, debouncedReload]);
```

5. Testar mudança de filtros e verificar console (apenas 1 request)

---

### Milestone 1.4: Busca Textual Backend
**Requisito:** REQ-001 | **Tempo:** 1 hora

#### Tarefas:

**Parte A - api.ts:**
1. Abrir `frontend/src/services/api.ts`
2. Na função `getMonitoringData`, adicionar mapeamento:

```typescript
if (options.q || options.search_query) {
  params.q = options.q || options.search_query;
}
```

**Parte B - Enviar searchValue:**
1. Em `DynamicMonitoringPage.tsx`, localizar chamada getMonitoringData (~linha 800-810)
2. Adicionar parâmetro q:

```typescript
const axiosResponse = await consulAPI.getMonitoringData(category, {
  page: params?.current || 1,
  page_size: params?.pageSize || 50,
  sort_field: sortField || undefined,
  sort_order: sortOrder || undefined,
  node: selectedNode !== 'all' ? selectedNode : undefined,
  filters: filters,
  q: searchValue || undefined,  // ADICIONAR
  signal: signal,
});
```

**Parte C - Remover busca local:**
1. Localizar linhas 956-972 em `DynamicMonitoringPage.tsx`
2. REMOVER completamente o bloco de busca local:

```typescript
// REMOVER TODO ESTE BLOCO
const keyword = searchValue.trim().toLowerCase();
if (keyword) {
  processedRows = processedRows.filter((item) => {
    // ... código de filtro local ...
  });
}
```

3. Testar busca por termo que existe em página diferente da atual

---

## FASE 2: AMANHÃ (5 horas)

### Milestone 2.1: Cache Intermediário
**Requisito:** REQ-002 | **Tempo:** 2 horas

#### Tarefas:
1. Abrir `backend/api/monitoring_unified.py`
2. Localizar uso de `get_services_cached` (~linha 423-450)
3. Substituir por `monitoring_data_cache`:

```python
# Substituir get_services_cached por monitoring_data_cache:
cached_data = await monitoring_data_cache.get_data(category)
if cached_data:
    raw_result = {"data": cached_data, "success": True}
else:
    raw_result = await fetch_data()
    await monitoring_data_cache.set_data(category, raw_result.get('data', []))
```

4. Verificar imports de `monitoring_data_cache`
5. Testar endpoint `/monitoring/cache/stats` (deve mostrar hits/misses)
6. Testar endpoint `/monitoring/cache/invalidate` (deve afetar dados)

---

### Milestone 2.2: Dropdown de Filtros - Estado Persistente
**Requisito:** REQ-005 (parte 1) | **Tempo:** 1 hora

#### Tarefas:
1. Em `DynamicMonitoringPage.tsx`, adicionar ref no topo do componente:

```typescript
const filterSearchTextRef = useRef<Record<string, string>>({});
```

2. Localizar filterDropdown (~linha 544-558)
3. Modificar inicialização do estado:

```typescript
const [searchText, setSearchText] = useState(
  filterSearchTextRef.current[colConfig.key] || ''
);
```

4. Criar handler para persistir:

```typescript
const handleSearchChange = (value: string) => {
  setSearchText(value);
  filterSearchTextRef.current[colConfig.key] = value;
};
```

5. Atualizar onChange do input de busca para usar `handleSearchChange`
6. Testar: digitar no filtro, ordenar coluna, verificar se texto persiste

---

### Milestone 2.3: Dropdown de Filtros - Múltipla Seleção
**Requisito:** REQ-005 (parte 2) | **Tempo:** 2 horas

#### Tarefas:
1. Localizar lógica de seleção (~linha 601-615)
2. Modificar para suportar múltiplos valores:

```typescript
if (selectedKeys.length > 0) {
  newFilters[colConfig.key] = selectedKeys.join(',');
} else {
  delete newFilters[colConfig.key];
}
```

3. Verificar se backend suporta filtros com vírgula (se não, implementar split)
4. Testar "Selecionar todos" e verificar se todos valores são aplicados
5. Verificar resposta da API com múltiplos filtros

---

## Riscos e Mitigações

| Risco | Probabilidade | Impacto | Mitigação |
|-------|---------------|---------|-----------|
| Backend não suporta filtro com vírgula | Média | Alto | Implementar split no backend |
| Cache tem comportamento diferente | Baixa | Médio | Testar em ambiente isolado primeiro |
| Debounce causa flicker na UI | Baixa | Baixo | Ajustar tempo de debounce |

---

## Dependências Técnicas

- `useDebouncedCallback` de `use-debounce`
- `useRef` de React
- `AbortController` nativo do browser
- `monitoring_data_cache` do backend (já implementado)

---

## Checklist de Conclusão

### Fase 1 (HOJE)
- [ ] REQ-003: Ordenação sem conversão
- [ ] REQ-006: Debounce com cancelamento
- [ ] REQ-004: Sem duplo disparo
- [ ] REQ-001: Busca textual via backend

### Fase 2 (AMANHÃ)
- [ ] REQ-002: Cache integrado
- [ ] REQ-005a: Estado dropdown persistente
- [ ] REQ-005b: Múltipla seleção funcional

---

## TAGs de Rastreabilidade

<!-- TAG: SPEC-PERF-002-FIX -->
<!-- TAG: PLAN-PERF-002-FIX -->

---

*Plano criado em 2025-11-22 baseado no documento de consolidação final*
