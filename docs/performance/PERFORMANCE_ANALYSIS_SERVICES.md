# 🔍 Análise de Performance - Página Services

**Data:** 2025-11-10 15:42
**URL:** http://localhost:8081/services
**Fonte:** Firefox Performance Profile

---

## 📊 Descobertas Principais

### 1. **Layout Shift (CLS) - Problema Crítico** 🔴

**Evidências:**
- ✅ **22x MozAfterPaint events** - 22 repinturas da página
- ✅ **615 operações de recálculo de estilos** (32.51ms total)
- ✅ **Múltiplos paints em sequência rápida** (+0ms, +11ms)

**Causa Raiz:**
Componentes renderizam em etapas:
1. Dashboard vazio (métricas = 0)
2. Dashboard atualiza (métricas reais)
3. Tabela vazia
4. Colunas dinâmicas carregam
5. Dados da tabela carregam

**Cada atualização = 1 repintura = Layout Shift!**

---

## 🎯 Problemas Identificados

### Problema #1: Cascata de Carregamentos

```
filterFields loading (4.5s) →
  tableFields loading →
    formFields loading →
      requestHandler →
        tableSnapshot atualiza →
          22x REPAINTS!
```

### Problema #2: Dashboard Renderiza 2x

```jsx
// Renderiza com valores zerados
Total: 0, Nós: 0, Empresas: 0

// Depois atualiza quando dados chegam
Total: 163, Nós: 3, Empresas: 18
```

**Impacto:** Shift vertical empurrando tabela para baixo

### Problema #3: Colunas Dinâmicas

```jsx
const visibleColumns = useMemo(() => {
  // Recalcula quando tableFields muda
  // Causa reflow da tabela inteira
}, [columnConfig, columnMap, columnWidths, handleResize]);
```

**Impacto:** Shift horizontal mudando larguras

### Problema #4: StrictMode em Dev

```jsx
<StrictMode>
  <App />
</StrictMode>
```

**Efeito:** Duplica carregamentos (2x requisições, 2x renders)

---

## ✅ Soluções Propostas

### Solução #1: Reservar Espaço do Dashboard

```tsx
// Services.tsx - Dashboard com altura mínima reservada
<Card style={{ minHeight: 60 }}> {/* Reserva espaço */}
  <div style={{ display: 'flex', gap: 16 }}>
    {/* Métricas */}
  </div>
</Card>
```

**Resultado:** Evita shift quando métricas carregam

### Solução #2: Skeleton para Tabela

```tsx
// Mostrar skeleton até TUDO carregar
{filterFieldsLoading ? (
  <Skeleton active paragraph={{ rows: 10 }} />
) : (
  <ProTable dataSource={tableSnapshot} />
)}
```

**Resultado:** Usuário vê feedback, sem shifts

### Solução #3: Larguras Fixas Iniciais para Colunas

```tsx
const fixedColumns = {
  node: { width: 160 },      // Fixo
  service: { width: 260 },   // Fixo
  id: { width: 260 },        // Fixo
  // Evita reflow quando conteúdo carrega
};
```

**Resultado:** Sem shift horizontal

### Solução #4: Consolidar Carregamentos

```tsx
// ANTES: 3 contextos separados
useTableFields();
useFormFields();
useFilterFields();

// DEPOIS: 1 contexto único
useMetadataFields(); // Carrega tudo junto
```

**Resultado:** 1 carregamento = menos repaints

### Solução #5: Debounce de Updates

```tsx
// Evitar updates rápidos em sequência
const debouncedUpdate = useMemo(
  () => debounce((data) => setTableSnapshot(data), 100),
  []
);
```

**Resultado:** Agrupa updates, menos repaints

---

## 📈 Impacto Esperado

| Métrica | Antes | Depois (estimado) |
|---------|-------|-------------------|
| **MozAfterPaint events** | 22x | ~3-5x |
| **Cumulative Layout Shift (CLS)** | Alto | <0.1 (bom) |
| **Time to Interactive (TTI)** | ~5s | ~2s |
| **Recálculos de estilo** | 615 | ~100 |

---

## 🚀 Prioridade de Implementação

### P0 - CRÍTICO (fazer agora)
1. ✅ Reservar espaço do Dashboard (minHeight)
2. ✅ Larguras fixas para colunas principais
3. ✅ Skeleton durante carregamento inicial

### P1 - ALTO (próxima sprint)
1. Consolidar contextos de metadata
2. Debounce de updates da tabela
3. Lazy load de colunas não visíveis

### P2 - MÉDIO (backlog)
1. Virtualização da tabela (react-window)
2. Code splitting da página Services
3. Service Worker para cache

---

## 🔧 Como Testar

1. **Lighthouse CI**:
   ```bash
   npm install -g @lhci/cli
   lhci autorun --collect.url=http://localhost:8081/services
   ```

2. **Chrome DevTools**:
   - Performance > Record
   - Filtrar por "Layout Shift"
   - Verificar CLS < 0.1

3. **Firefox Profiler**:
   - about:profiling
   - Contar MozAfterPaint events < 5

---

## 📚 Referências

- [Web Vitals - CLS](https://web.dev/cls/)
- [Optimize CLS](https://web.dev/optimize-cls/)
- [React Performance](https://react.dev/learn/render-and-commit)

---

**Próximos Passos:** Implementar soluções P0 e medir resultados com Lighthouse.
