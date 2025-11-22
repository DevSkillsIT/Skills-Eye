# Ajustes Finais Necessários - SPEC-PERF-002 v2.0.0

**Data:** 22/11/2025  
**Revisor:** Auditor Técnico  
**Status:** Plano 90% completo - faltam ajustes críticos

## ✅ O QUE ESTÁ EXCELENTE NO PLANO v2.0.0

O plano melhorou drasticamente e agora contempla:

1. **Backend-first approach** com paginação server-side obrigatória
2. **Cache intermediário** com TTL de 30 segundos para contornar limitação do Consul
3. **Menciona Consul Issue #9422** sobre falta de paginação nativa
4. **AbortController e isMountedRef** com código completo
5. **Testes com fixtures** ao invés de infraestrutura externa
6. **Tempo realista** de 18-23 dias
7. **NÃO criar FilterDropdown.tsx** - manter inline
8. **NÃO criar Context global** - overhead desnecessário
9. **Virtualização de tabela** para grandes volumes
10. **Web Workers e Web Vitals** para otimizações avançadas

---

## 🔴 INCONSISTÊNCIA CRÍTICA ENTRE spec.md E plan.md

### PROBLEMA: Contradição sobre filteredValue/sortOrder/metadataOptions

**spec.md (linhas 48-62)** ainda diz que são dependências VOLÁTEIS a remover:
```typescript
// PROBLEMA: metadataOptions, filters, sortField, sortOrder mudam a cada interação
const proTableColumns = useMemo<ProColumns<MonitoringDataItem>[]>(() => {
  // ...
}, [
  metadataOptions,  // VOLATIL - muda a cada fetch
  filters,          // VOLATIL - muda a cada interação
  sortField,        // VOLATIL - muda ao ordenar
  sortOrder,        // VOLATIL - muda ao ordenar
]);
```

**plan.md (linha 32)** corretamente identifica como ERRO:
```
ERRADO: Remover `filteredValue`/`sortOrder` das deps - QUEBRA visual do ProTable
```

### CORREÇÃO NECESSÁRIA:

**No spec.md, atualizar a seção "Causa Raiz 1" (linhas 43-69) para:**

```markdown
### Causa Raiz 1: proTableColumns com Muitas Dependências (MEDIUM)

**Localização**: `frontend/src/pages/DynamicMonitoringPage.tsx` linhas 407-658

**Esclarecimento após auditoria**: 
- `filteredValue` e `sortOrder` DEVEM permanecer nas dependências (requisito do ProTable para controlled mode)
- `metadataOptions` deve ser estabilizado com useRef para evitar recálculos desnecessários
- O problema real é a falta de estabilização, não a presença nas dependências

**Solução**: Usar useRef para valores que mudam frequentemente mas não precisam causar recálculo:

```typescript
const metadataOptionsRef = useRef(metadataOptions);
useEffect(() => {
  metadataOptionsRef.current = metadataOptions;
}, [metadataOptions]);

// Em proTableColumns, usar ref.current
const fieldOptions = metadataOptionsRef.current[colConfig.key] || [];
```
```

---

## 🟡 LACUNAS TÉCNICAS QUE PRECISAM SER ADICIONADAS

### 1. Race Condition: metadataOptions vs metadataOptionsLoaded

**Adicionar na FASE 2 do plan.md:**

```typescript
// PROBLEMA: Não atômico
setMetadataOptions(options);     // Estado 1
setMetadataOptionsLoaded(true);  // Estado 2

// SOLUÇÃO: Usar um único estado
const [metadataState, setMetadataState] = useState({
  options: {},
  loaded: false
});

// Atualização atômica
setMetadataState({
  options: extractedOptions,
  loaded: true
});
```

### 2. React 19 Strict Mode Triple Mount

**Adicionar como nota na FASE 0:**

```markdown
### Nota: React 19 Strict Mode

O projeto usa React 19.1.1 que tem Strict Mode mais agressivo em desenvolvimento:
- useEffect executa 3 vezes: mount → unmount → mount → unmount → mount
- Isso é NORMAL em dev e não ocorre em produção
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
    cancelled = true; // Evita setState após unmount
  };
}, []);
```
```

### 3. Memoização de getFieldValue

**Adicionar na FASE 3 como otimização:**

```typescript
// Cache para getFieldValue que é chamada muitas vezes
const fieldValueCacheRef = useRef<Record<string, string>>({});

const getFieldValue = useCallback((row: MonitoringDataItem, field: string): string => {
  const cacheKey = `${row.ID}-${field}`;
  
  if (fieldValueCacheRef.current[cacheKey]) {
    return fieldValueCacheRef.current[cacheKey];
  }
  
  // Cálculo normal
  let value = '';
  if (field === 'Tags') {
    value = (row.Tags || []).join(', ');
  } else if (row.Meta?.[field] !== undefined) {
    value = String(row.Meta[field]);
  } else if (row[field] !== undefined) {
    value = String(row[field]);
  }
  
  fieldValueCacheRef.current[cacheKey] = value;
  return value;
}, []);

// Limpar cache ao mudar dados
useEffect(() => {
  fieldValueCacheRef.current = {};
}, [category]);
```

### 4. Processamento O(n²) - Detalhar no spec.md

**Adicionar explicação após linha 26 do plan.md:**

```markdown
**Detalhamento do O(n²)**: 
- applyAdvancedFilters tem loop aninhado quando usa operador OR
- Para cada registro, verifica cada condição
- Com 5000 registros e 10 condições = 50.000 operações
- SOLUÇÃO: Mover para backend ou usar Web Worker
```

### 5. Service Worker para Cache Offline

**Adicionar na FASE 4 (opcional):**

```javascript
// serviceWorker.js
self.addEventListener('fetch', (event) => {
  if (event.request.url.includes('/api/v1/monitoring/data')) {
    event.respondWith(
      caches.match(event.request)
        .then(response => response || fetch(event.request))
    );
  }
});
```

---

## 🔵 AJUSTES MENORES (Nice to Have)

### 1. Rolldown-vite Experimental

**Adicionar como risco no spec.md:**

```markdown
| Rolldown-vite experimental | Baixa | Médio | Usar Vite oficial se houver problemas de build |
```

### 2. Intersection Observer para Lazy Loading

**Adicionar na FASE 4:**

```typescript
// Lazy loading de componentes pesados
const LazyComponent = ({ children }) => {
  const [isVisible, setIsVisible] = useState(false);
  const ref = useRef(null);
  
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
```

---

## 📋 CHECKLIST FINAL DE CORREÇÕES

### Críticas (DEVEM ser corrigidas):

- [ ] **spec.md**: Corrigir seção "Causa Raiz 1" - filteredValue/sortOrder DEVEM ficar nas deps
- [ ] **plan.md**: Adicionar solução para race condition metadataOptions/loaded
- [ ] **plan.md**: Adicionar nota sobre React 19 Strict Mode

### Importantes (DEVERIAM ser adicionadas):

- [ ] **plan.md**: Adicionar memoização de getFieldValue
- [ ] **spec.md**: Detalhar problema O(n²) em applyAdvancedFilters
- [ ] **plan.md**: Adicionar Service Worker básico para cache offline

### Nice to Have:

- [ ] **spec.md**: Adicionar rolldown-vite como risco
- [ ] **plan.md**: Adicionar Intersection Observer para lazy loading

---

## 🎯 CONCLUSÃO

O plano v2.0.0 está **90% completo e correto**. As correções listadas acima são principalmente para:

1. **Eliminar contradição** entre spec.md e plan.md sobre filteredValue/sortOrder
2. **Adicionar detalhes técnicos** sobre race conditions e React 19
3. **Incluir otimizações** que já foram identificadas mas não detalhadas

Com esses ajustes, o plano estará 100% alinhado com as melhores práticas e evitará TODOS os problemas identificados pelas 4 IAs.

**Tempo estimado para ajustes no documento**: 1-2 horas

**Impacto se não corrigir**: A principal contradição sobre filteredValue/sortOrder pode confundir o desenvolvedor e levar à implementação errada que quebra o ProTable.
