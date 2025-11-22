# GAPS E PROBLEMAS IDENTIFICADOS - SPEC-PERF-002

**Data da Análise:** 2025-11-22  
**Branch Analisado:** dev-adriano  
**Status:** ⚠️ **IMPLEMENTAÇÃO PARCIAL - PROBLEMAS CRÍTICOS IDENTIFICADOS**

---

## 🔴 PROBLEMAS CRÍTICOS QUE IMPEDEM FUNCIONAMENTO

### 1. TABELA NÃO RENDERIZA COLUNAS (CRÍTICO - BLOQUEADOR)

**Sintoma Observado:**
- Logs mostram: `[DynamicMonitoringPage] ✅ Atualizando columnConfig: metadataColumns: 22`
- Logs mostram: `[PERF] Registros na pagina: 8 | Total: 8`
- Mas a tabela não exibe colunas de dados (apenas checkboxes)

**Causa Raiz Identificada:**

No arquivo `DynamicMonitoringPage.tsx` linha 472-474:

```typescript
const proTableColumns = useMemo<ProColumns<MonitoringDataItem>[]>(() => {
  // ✅ CORREÇÃO: Só calcular colunas quando columnConfig estiver pronto
  if (columnConfig.length === 0) {
    return [];  // ❌ PROBLEMA: Retorna array vazio se columnConfig ainda não carregou
  }
```

**Problema:**
- Race condition entre `tableFields` carregar e `columnConfig` ser atualizado
- `proTableColumns` é calculado ANTES de `columnConfig` ser populado pelo `useEffect` (linha 265-285)
- Quando `columnConfig.length === 0`, retorna `[]` e a tabela não renderiza colunas

**Solução Necessária:**

```typescript
const proTableColumns = useMemo<ProColumns<MonitoringDataItem>[]>(() => {
  // ✅ CORREÇÃO: Aguardar tableFields OU columnConfig estar pronto
  if (columnConfig.length === 0 && tableFields.length > 0) {
    // Se tableFields já carregou mas columnConfig ainda não foi atualizado,
    // usar defaultColumnConfig diretamente
    const configsToUse = defaultColumnConfig.length > 0 ? defaultColumnConfig : columnConfig;
    if (configsToUse.length === 0) {
      return []; // Ainda não tem dados
    }
    // Continuar com configsToUse...
  }
  
  if (columnConfig.length === 0) {
    return []; // Ainda não tem dados
  }
  // ... resto do código
```

**OU melhor ainda:** Remover a verificação `columnConfig.length === 0` e usar `defaultColumnConfig` diretamente quando `columnConfig` estiver vazio.

---

### 2. BACKEND NÃO ESTÁ USANDO monitoring_cache.py (CRÍTICO)

**Problema Identificado:**

No arquivo `backend/api/monitoring_unified.py` linha 33-34:

```python
from core.monitoring_cache import get_monitoring_cache  # SPEC-PERF-002: Cache intermediario
from core.monitoring_filters import process_monitoring_data  # SPEC-PERF-002: Filtros server-side
```

**MAS** o código não está usando `get_monitoring_cache()`!

Linha 424-430:
```python
# USAR CACHE - Chama fetch_data() com cache wrapper
raw_result = await get_services_cached(
    category=category,
    company=company,
    site=site,
    env=env,
    fetch_function=fetch_data
)
```

**Problema:**
- `get_services_cached()` usa `LocalCache` genérico (linha 47)
- **NÃO** usa `MonitoringDataCache` criado especificamente para SPEC-PERF-002
- O cache intermediário `monitoring_cache.py` foi criado mas **NÃO ESTÁ SENDO USADO**

**Solução Necessária:**

Modificar `get_monitoring_data()` para usar `get_monitoring_cache()`:

```python
# No início da função get_monitoring_data()
monitoring_cache = get_monitoring_cache(ttl_seconds=30)

# Verificar cache primeiro
cached_data = await monitoring_cache.get_data(category, node)
if cached_data is not None:
    # Usar dados do cache
    raw_result = {
        "success": True,
        "category": category,
        "data": cached_data,
        "total": len(cached_data),
        "available_fields": [],
    }
else:
    # Cache miss - buscar dados
    raw_result = await fetch_data()
    # Armazenar no cache
    await monitoring_cache.set_data(category, raw_result.get('data', []), node)
```

---

### 3. CONVERSÃO INCORRETA DE sort_order (MÉDIO)

**Problema Identificado:**

No arquivo `frontend/src/services/api.ts` linha 928-929:

```typescript
if (options.sort_order) {
  // Converter 'ascend'/'descend' para 'asc'/'desc' do backend
  params.sort_order = options.sort_order === 'ascend' ? 'asc' : 'desc';
}
```

**Problema:**
- Frontend está convertendo 'ascend'/'descend' para 'asc'/'desc'
- **MAS** o backend espera 'ascend'/'descend' (linha 135 de `monitoring_unified.py`)
- Backend não reconhece 'asc'/'desc' e ordenação não funciona

**Solução Necessária:**

Remover a conversão e passar diretamente:

```typescript
if (options.sort_order) {
  params.sort_order = options.sort_order; // ✅ Passar diretamente 'ascend' ou 'descend'
}
```

**NOTA:** Os filtros dinâmicos estão sendo passados corretamente (linha 936-942 de `api.ts` expande o objeto `filters` em query params individuais).

---

### 4. filterOptions NÃO ESTÁ SENDO RETORNADO CORRETAMENTE (MÉDIO)

**Problema Identificado:**

No arquivo `backend/api/monitoring_unified.py` linha 483:

```python
response["filterOptions"] = processed["filter_options"]
```

**MAS** `process_monitoring_data()` retorna `filter_options` (com underscore), não `filterOptions` (camelCase).

**Verificação Necessária:**
- Confirmar se o frontend está esperando `filterOptions` ou `filter_options`
- Padronizar nomenclatura entre backend e frontend

---

## 🟠 GAPS DE IMPLEMENTAÇÃO

### 5. TESTES BACKEND NÃO FORAM CRIADOS (ALTO)

**Gap Identificado:**

O plano SPEC-PERF-002 FASE 1 exige:
- Arquivo `backend/tests/test_monitoring_unified_baseline.py`
- Testes com fixtures (não infraestrutura externa)
- Cobertura mínima 80%

**Status:** ❌ **ARQUIVO NÃO EXISTE**

**Verificação:**
```bash
$ find backend/tests -name "*monitoring_unified*" -type f
# Nenhum resultado
```

**Solução Necessária:**
Criar arquivo `backend/tests/test_monitoring_unified_baseline.py` conforme especificado no plano (linhas 264-358 de `plan.md`).

---

### 6. DEBOUNCE NÃO ESTÁ CANCELANDO REQUESTS ANTERIORES (MÉDIO)

**Problema Identificado:**

No arquivo `DynamicMonitoringPage.tsx` linha 318-320:

```typescript
// ✅ SPEC-PERF-002: Debounce com cancelamento para evitar requests excessivos
const debouncedReload = useDebouncedCallback(() => {
  actionRef.current?.reload();
}, 300);
```

**Problema:**
- Debounce está implementado, MAS não está cancelando o `AbortController` antes de chamar `reload()`
- O `AbortController` só é cancelado dentro do `requestHandler`, não antes do debounce

**Solução Necessária:**

```typescript
const debouncedReload = useDebouncedCallback(() => {
  // ✅ Cancelar request anterior ANTES de chamar reload
  if (abortControllerRef.current) {
    abortControllerRef.current.abort();
  }
  actionRef.current?.reload();
}, 300);
```

---

### 7. CATEGORY_DISPLAY_NAMES REMOVIDO MAS FALLBACK PODE FALHAR (BAIXO)

**Implementação Atual:**

No arquivo `DynamicMonitoringPage.tsx` linha 1122-1130:

```typescript
const categoryTitle = useMemo(() => {
  // Tentar pegar display_name do primeiro tableField (se disponivel)
  const firstField = tableFields[0];
  if (firstField && (firstField as any).category_display_name) {
    return (firstField as any).category_display_name;
  }
  // Fallback para formatacao automatica
  return formatCategoryName(category);
}, [tableFields, category]);
```

**Problema Potencial:**
- Se `tableFields[0]` não existir ou não tiver `category_display_name`, usa `formatCategoryName()`
- `formatCategoryName()` pode não gerar nomes amigáveis (ex: "System Exporters" vs "System-Exporters")

**Solução Sugerida:**
Verificar se o backend está retornando `category_display_name` nos `tableFields`. Se não, adicionar ao backend.

---

### 8. VIRTUALIZAÇÃO ESTÁ HABILITADA MAS PODE CAUSAR PROBLEMAS (BAIXO)

**Implementação Atual:**

No arquivo `DynamicMonitoringPage.tsx` linha 1400:

```typescript
// ✅ SPEC-PERF-002 GAP 4: Virtualizacao para grandes volumes
virtual={true}
```

**Problema Potencial:**
- Virtualização pode causar problemas de renderização se `proTableColumns` estiver vazio ou inconsistente
- Pode estar contribuindo para o problema de colunas não renderizadas

**Solução Sugerida:**
Desabilitar virtualização temporariamente para debug, ou garantir que só habilite quando `proTableColumns.length > 0`.

---

## 🟡 PROBLEMAS MENORES

### 9. LOGS DE PERFORMANCE EXCESSIVOS (BAIXO)

**Problema:**
- Muitos logs de performance no console mesmo em produção
- `DEBUG_PERFORMANCE` está definido como `import.meta.env.DEV`, mas logs ainda aparecem

**Solução:**
Verificar se `import.meta.env.DEV` está funcionando corretamente ou usar flag explícita.

---

### 10. DEPENDÊNCIA use-debounce PODE NÃO ESTAR INSTALADA (BAIXO)

**Verificação Necessária:**
```bash
cd frontend && npm ls use-debounce
```

Se não estiver instalada, instalar:
```bash
npm install use-debounce
```

---

## 📊 RESUMO DE IMPLEMENTAÇÃO

### ✅ O QUE FOI IMPLEMENTADO CORRETAMENTE:

1. ✅ AbortController para cancelar requests
2. ✅ isMountedRef para evitar memory leaks
3. ✅ metadataOptionsRef para estabilidade
4. ✅ Estado atômico para metadataOptions (MetadataState)
5. ✅ Debounce básico (mas sem cancelamento antes do reload)
6. ✅ Remoção de CATEGORY_DISPLAY_NAMES hardcoded
7. ✅ Arquivos `monitoring_cache.py` e `monitoring_filters.py` criados
8. ✅ Paginação server-side parcialmente implementada no backend
9. ✅ Filtros server-side parcialmente implementados no backend
10. ✅ Ordenação server-side parcialmente implementada no backend

### ❌ O QUE NÃO FOI IMPLEMENTADO OU ESTÁ QUEBRADO:

1. ❌ **CRÍTICO:** Tabela não renderiza colunas (race condition columnConfig)
2. ❌ **CRÍTICO:** Backend não está usando `monitoring_cache.py`
3. ❌ **MÉDIO:** Conversão incorreta de sort_order ('ascend'/'descend' → 'asc'/'desc')
4. ❌ **ALTO:** Testes backend não foram criados
5. ❌ **MÉDIO:** Debounce não cancela requests antes do reload
6. ❌ **MÉDIO:** filterOptions pode ter problema de nomenclatura

---

## 🎯 PRIORIZAÇÃO DE CORREÇÕES

### PRIORIDADE 1 (BLOQUEADORES - CORRIGIR IMEDIATAMENTE):

1. **Corrigir race condition de columnConfig** - Tabela não renderiza
2. **Integrar monitoring_cache.py no backend** - Cache não está sendo usado
3. **Corrigir conversão de sort_order** - Ordenação não funciona

### PRIORIDADE 2 (ALTA - CORRIGIR EM BREVE):

4. **Criar testes backend** - Sem testes, regressões não são detectadas
5. **Corrigir debounce com cancelamento** - Race conditions podem persistir
6. **Verificar filterOptions nomenclatura** - Dropdowns podem não funcionar

### PRIORIDADE 3 (MÉDIA - CORRIGIR QUANDO POSSÍVEL):

7. **Verificar category_display_name do backend**
8. **Ajustar virtualização condicional**
9. **Reduzir logs de performance**

---

## 📝 PRÓXIMOS PASSOS RECOMENDADOS

1. **Imediato:** Corrigir problema de renderização de colunas (Gap #1)
2. **Imediato:** Integrar `monitoring_cache.py` no fluxo do backend (Gap #2)
3. **Urgente:** Corrigir conversão de sort_order (Gap #3)
4. **Esta semana:** Criar testes backend (Gap #5)
5. **Esta semana:** Corrigir debounce com cancelamento (Gap #6)

---

**Documento gerado após análise completa do código no branch dev-adriano**
