# SPEC-PERF-002-FIX: Correções de Performance e UX

## Metadata

| Campo | Valor |
|-------|-------|
| ID | SPEC-PERF-002-FIX |
| Status | DRAFT |
| Versão | 1.0.0 |
| Prioridade | CRÍTICA |
| Dependência | SPEC-PERF-002 |
| Criado | 2025-11-22 |

---

## 1. Environment (Ambiente)

### 1.1 Contexto do Sistema

- **Frontend**: React + TypeScript + Ant Design Pro Table
- **Backend**: Python FastAPI com endpoints de monitoramento
- **Paginação**: Server-side com 50 registros por página
- **Branch Base**: `dev-adriano`

### 1.2 Arquivos Afetados

- `frontend/src/services/api.ts` - Serviço de comunicação com backend
- `frontend/src/pages/DynamicMonitoringPage.tsx` - Página principal de monitoramento
- `backend/api/monitoring_unified.py` - API unificada de monitoramento

---

## 2. Assumptions (Premissas)

- O backend já possui implementação completa do parâmetro `q` para busca textual
- O backend aceita `sort_order` nos valores `ascend` e `descend`
- O cache `monitoring_data_cache` já está implementado mas não integrado
- A tabela usa `actionRef.current?.reload()` para atualizar dados

---

## 3. Requirements (Requisitos)

### REQ-001: Busca Textual - Backend Pronto, Frontend Ignora
**Severidade:** CRÍTICO | **Tempo Estimado:** 1 hora

**When** o usuário digita um termo na busca textual,
**the system shall** enviar o parâmetro `q` para o backend processar a busca em TODO o dataset ANTES da paginação.

#### Especificação Técnica

**3.1.1 api.ts - Adicionar mapeamento do parâmetro:**
```typescript
if (options.q || options.search_query) {
  params.q = options.q || options.search_query;
}
```

**3.1.2 DynamicMonitoringPage.tsx linha 800-810 - Enviar searchValue:**
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

**3.1.3 DynamicMonitoringPage.tsx linhas 956-972 - REMOVER busca local:**
```typescript
// REMOVER TODO ESTE BLOCO:
// const keyword = searchValue.trim().toLowerCase();
// if (keyword) {
//   processedRows = processedRows.filter((item) => {
//     const fields = [
//       item.Service || '',
//       item.ID || '',
//       item.Address || '',
//       item.Port?.toString() || '',
//       ...Object.values(item.Meta || {}),
//       ...(item.Tags || [])
//     ];
//     return fields.some(field =>
//       String(field).toLowerCase().includes(keyword)
//     );
//   });
// }
```

---

### REQ-002: Cache Intermediário - Criado mas Não Integrado
**Severidade:** ALTO | **Tempo Estimado:** 2 horas

**When** o endpoint `/monitoring/data` é chamado,
**the system shall** utilizar `monitoring_data_cache` ao invés de `get_services_cached`.

#### Especificação Técnica

**3.2.1 backend/api/monitoring_unified.py - Substituir cache genérico:**
```python
# Substituir get_services_cached por monitoring_data_cache:
cached_data = await monitoring_data_cache.get_data(category)
if cached_data:
    raw_result = {"data": cached_data, "success": True}
else:
    raw_result = await fetch_data()
    await monitoring_data_cache.set_data(category, raw_result.get('data', []))
```

---

### REQ-003: Ordenação Descendente - Conversão Desnecessária
**Severidade:** MÉDIO | **Tempo Estimado:** 5 minutos

**When** o usuário ordena uma coluna,
**the system shall** enviar o valor de `sort_order` diretamente SEM conversão.

#### Especificação Técnica

**3.3.1 api.ts - Remover conversão:**
```typescript
// Remover conversão - passar valor direto
if (options.sort_order) {
  params.sort_order = options.sort_order;  // Backend aceita ascend/descend
}
```

---

### REQ-004: Filtros Dinâmicos - Duplo Disparo e Sem Debounce
**Severidade:** ALTO | **Tempo Estimado:** 30 minutos

**When** o usuário altera um filtro,
**the system shall** disparar APENAS uma requisição com debounce.

#### Especificação Técnica

**3.4.1 DynamicMonitoringPage.tsx - MetadataFilterBar onChange - REMOVER reload:**
```typescript
<MetadataFilterBar
  onChange={(newFilters) => {
    setFilters(newFilters);
    // actionRef.current?.reload();  REMOVER
  }}
  onReset={() => {
    setFilters({});
    actionRef.current?.reload();
  }}
/>
```

**3.4.2 DynamicMonitoringPage.tsx - useEffect - Usar debouncedReload:**
```typescript
useEffect(() => {
  if (isFirstRender.current) {
    isFirstRender.current = false;
    return;
  }
  debouncedReload();  // Usar versão com debounce
}, [selectedNode, filters, debouncedReload]);
```

---

### REQ-005: Dropdown de Filtros - Perde Estado e Múltipla Seleção
**Severidade:** ALTO | **Tempo Estimado:** 3 horas

**When** o usuário interage com o dropdown de filtro,
**the system shall** manter o estado de busca e suportar múltipla seleção corretamente.

#### Especificação Técnica

**3.5.1 DynamicMonitoringPage.tsx - Criar ref para estado persistente:**
```typescript
// No topo do componente:
const filterSearchTextRef = useRef<Record<string, string>>({});
```

**3.5.2 DynamicMonitoringPage.tsx - Inicializar estado do filterDropdown:**
```typescript
// No filterDropdown:
const [searchText, setSearchText] = useState(
  filterSearchTextRef.current[colConfig.key] || ''
);

// Ao mudar:
const handleSearchChange = (value: string) => {
  setSearchText(value);
  filterSearchTextRef.current[colConfig.key] = value;  // Persiste
};
```

**3.5.3 DynamicMonitoringPage.tsx - Múltipla seleção:**
```typescript
if (selectedKeys.length > 0) {
  // Enviar como string concatenada
  newFilters[colConfig.key] = selectedKeys.join(',');
} else {
  delete newFilters[colConfig.key];
}
```

---

### REQ-006: Debounce Não Cancela Requests
**Severidade:** MÉDIO | **Tempo Estimado:** 15 minutos

**When** o debounce dispara uma nova requisição,
**the system shall** cancelar a requisição anterior para evitar race conditions.

#### Especificação Técnica

**3.6.1 DynamicMonitoringPage.tsx - debouncedReload com cancelamento:**
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

---

## 4. Specifications (Especificações)

### 4.1 Resumo de Arquivos e Linhas

| Requisito | Arquivo | Linha(s) | Ação |
|-----------|---------|----------|------|
| REQ-001 | api.ts | ~900-945 | Adicionar mapeamento `q` |
| REQ-001 | DynamicMonitoringPage.tsx | 800-810 | Adicionar `q: searchValue` |
| REQ-001 | DynamicMonitoringPage.tsx | 956-972 | REMOVER busca local |
| REQ-002 | monitoring_unified.py | 423-450 | Substituir cache |
| REQ-003 | api.ts | ~900-933 | Remover conversão sort_order |
| REQ-004 | DynamicMonitoringPage.tsx | 1374-1385 | Remover reload onChange |
| REQ-004 | DynamicMonitoringPage.tsx | 1104-1115 | Usar debouncedReload |
| REQ-005 | DynamicMonitoringPage.tsx | 544-558 | Criar filterSearchTextRef |
| REQ-005 | DynamicMonitoringPage.tsx | 601-615 | Múltipla seleção join |
| REQ-006 | DynamicMonitoringPage.tsx | 318-320 | Cancelar abort controller |

---

## 5. Traceability (Rastreabilidade)

### TAGs Relacionadas
- `<!-- TAG: SPEC-PERF-002-FIX -->` - Marcador principal
- `<!-- TAG: REQ-001-BUSCA -->` - Busca textual
- `<!-- TAG: REQ-002-CACHE -->` - Cache intermediário
- `<!-- TAG: REQ-003-SORT -->` - Ordenação
- `<!-- TAG: REQ-004-DEBOUNCE-DUPLO -->` - Duplo disparo
- `<!-- TAG: REQ-005-DROPDOWN -->` - Dropdown de filtros
- `<!-- TAG: REQ-006-CANCEL -->` - Cancelamento requests

### Documento Base
- `/home/adrianofante/projetos/Skills-Eye/.moai/specs/SPEC-PERF-002/CONSOLIDACAO-FINAL-DEFINITIVA-SPEC-PERF-002.md`

---

## 6. Notas Importantes

- **BACKEND-FIRST**: Todo processamento deve ser feito no backend
- **ZERO HARDCODE**: Frontend apenas renderiza dados do backend
- **Este documento é EXATAMENTE baseado no documento de consolidação**
- Item 2 (Filtros Avançados) foi EXCLUÍDO conforme solicitação

---

*SPEC criada em 2025-11-22 baseada no documento de consolidação final*
