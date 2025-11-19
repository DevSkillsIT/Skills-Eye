# 🚀 PLANO DE OTIMIZAÇÃO FRONTEND - Network Probes Page

**Data:** 16/11/2025  
**Objetivo:** Reduzir tempo de carregamento da tabela de 2.8s para <1.5s

---

## 📊 ANÁLISE ANTES (Baseline)

### Métricas Atuais
- **Navegação:** 2193ms (média)
- **Tabela carregada:** 2807ms (média)
- **First Contentful Paint:** 676ms (média)
- **API Requests:** 9 (média)

### Requests Identificados
1. `/metadata-fields/` (MetadataFieldsContext) - ~100ms
2. `/settings/sites-config` (SitesProvider) - ~100ms
3. `/settings/naming-config` (App.tsx) - ~100ms
4. `/settings/naming-config` (duplicado) - ~24ms
5. `/settings/sites-config` (duplicado) - ~24ms
6. `/metadata-fields/` (duplicado?) - ~24ms
7. `/monitoring/data?category=network-probes` - ~24ms (após cache)
8. `/nodes` (NodeSelector) - **1454ms** ⚠️ **GARGALO PRINCIPAL!**

### Problemas Identificados

#### 🔴 CRÍTICO
1. **`/nodes` muito lento (1454ms):**
   - NodeSelector faz request no mount
   - Bloqueia renderização da tabela
   - Não está em cache

#### 🟡 MÉDIO
2. **Requests duplicados:**
   - `naming-config` aparece 2x
   - `sites-config` aparece 2x
   - `metadata-fields` pode estar duplicado

3. **Requests sequenciais:**
   - Providers carregam sequencialmente
   - NodeSelector espera providers carregarem
   - Não há paralelização

---

## ✅ SOLUÇÕES PROPOSTAS

### 1. Otimizar NodeSelector (CRÍTICO)
**Problema:** `/nodes` leva 1454ms e bloqueia renderização

**Solução:**
- ✅ Carregar `/nodes` em paralelo com outros requests
- ✅ Não bloquear renderização (loading state)
- ✅ Cachear resultado no frontend (localStorage ou Context)
- ✅ Usar dados do SitesProvider se disponível (evita request extra)

**Impacto esperado:** -1400ms (de 1454ms para ~50ms com cache)

### 2. Paralelizar Requests Independentes
**Problema:** Providers carregam sequencialmente

**Solução:**
- ✅ Garantir que MetadataFieldsContext, SitesProvider e loadNamingConfig rodem em paralelo
- ✅ Usar Promise.all() quando possível

**Impacto esperado:** -200ms (de 300ms sequencial para 100ms paralelo)

### 3. Remover Requests Duplicados
**Problema:** naming-config e sites-config aparecem 2x

**Solução:**
- ✅ Verificar se há múltiplos componentes chamando mesmo endpoint
- ✅ Usar Context compartilhado
- ✅ Cachear no frontend

**Impacto esperado:** -50ms (eliminar requests duplicados)

### 4. Otimizar Carregamento de MetadataOptions
**Problema:** metadataOptions é calculado após dados carregarem

**Solução:**
- ✅ Já está otimizado (calculado dos dados recebidos)
- ✅ Manter como está

---

## 🎯 META DE PERFORMANCE

### Antes
- Navegação: 2193ms
- Tabela: 2807ms

### Depois (Esperado)
- Navegação: <1500ms (-693ms, -31%)
- Tabela: <1500ms (-1307ms, -46%)

---

## 📝 IMPLEMENTAÇÃO

### Fase 1: Otimizar NodeSelector
1. Criar Context para nodes (compartilhar entre componentes)
2. Carregar nodes em paralelo com outros providers
3. Cachear resultado (localStorage ou Context)
4. Não bloquear renderização

### Fase 2: Paralelizar Providers
1. Verificar se providers já estão paralelos
2. Se não, usar Promise.all() no App.tsx

### Fase 3: Remover Duplicados
1. Identificar origem dos requests duplicados
2. Consolidar em Context único
3. Remover chamadas redundantes

---

**Documento criado em:** 16/11/2025  
**Autor:** Análise de Performance

