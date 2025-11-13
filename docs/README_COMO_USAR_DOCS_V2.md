# 📚 COMO USAR A DOCUMENTAÇÃO DO PLANO V2.0

**Data:** 13/11/2025  
**Status:** DOCUMENTAÇÃO COMPLETA E VALIDADA

---

## 🎯 ESTRUTURA DA DOCUMENTAÇÃO

Você tem **3 documentos principais** para a implementação:

### 1️⃣ **PLANO DE REFATORAÇÃO SKILLS EYE - VERSÃO COMPLETA 2.0.md**
- **Tamanho:** 3466 linhas
- **Quando usar:** Como referência arquitetural geral
- **O que contém:**
  - Análise completa do sistema atual
  - Visão geral da arquitetura V2.0
  - Estrutura de pastas
  - Cronograma de 13 dias
  - Diagramas de fluxo

### 2️⃣ **GUIA_IMPLEMENTACAO_CORRIGIDO_V2.md** ⭐ **USE ESTE PRIMEIRO**
- **Tamanho:** 642 linhas
- **Quando usar:** Durante a codificação (Dias 3-6)
- **O que contém:**
  - Código Python/TypeScript pronto para copiar
  - Substituições de seções problemáticas do plano original
  - Implementações completas de:
    - MetadataFieldModel com 4 novos campos
    - Endpoint `/monitoring/data` (Consul)
    - Endpoint `/monitoring/metrics` (Prometheus)
    - DynamicMonitoringPage com consulAPI
    - Métodos novos em consulAPI
  - Checklist de validação final

### 3️⃣ **AJUSTES_CRITICOS_PLANO_V2.md**
- **Tamanho:** 1162 linhas
- **Quando usar:** Para entender PORQUÊ das mudanças
- **O que contém:**
  - Explicação detalhada dos 5 ajustes
  - Contexto histórico das correções
  - Script de migração completo
  - Integração com testes de persistência

---

## 📋 WORKFLOW DE IMPLEMENTAÇÃO

### ANTES DE COMEÇAR
```bash
# 1. Ler documentos na ordem:
1º → GUIA_IMPLEMENTACAO_CORRIGIDO_V2.md    # Código pronto
2º → AJUSTES_CRITICOS_PLANO_V2.md          # Entender razões
3º → PLANO original (seções não corrigidas) # Contexto geral

# 2. Validar pré-requisitos:
✓ Backend rodando (http://localhost:5000)
✓ Frontend rodando (http://localhost:8081)
✓ Consul acessível (http://localhost:8500)
✓ Testes de persistência passando (run_all_persistence_tests.sh)
```

### DURANTE A IMPLEMENTAÇÃO

#### **Dias 1-2: Análise e Setup**
- **Use:** PLANO original - Seção 3 (Análise Atual)
- **Ação:** Mapear código existente, identificar pontos de integração

#### **Dia 3: Metadata Fields (Backend)**
- **Use:** GUIA_IMPLEMENTACAO_CORRIGIDO_V2.md - Seção 1
- **Ação:** Copiar código da classe `MetadataFieldModel` com 4 novos campos
- **Validar:** 
  ```bash
  grep -n "show_in_network_probes\|show_in_web_probes" backend/api/metadata_fields_manager.py
  # Deve mostrar as 4 novas linhas
  ```

#### **Dia 4: ConsulKVConfigManager + Regras**
- **Use:** PLANO original - Seção 5.1.2 e 5.1.3
- **Ação:** Implementar cache de KV e categorization_rule_engine
- **Nota:** Não precisa de ajustes, código original está correto

#### **Dia 5: Endpoints Backend**
- **Use:** GUIA_IMPLEMENTACAO_CORRIGIDO_V2.md - Seções 2 e 3
- **Ação:** 
  1. Copiar endpoint `/monitoring/data` (Consul)
  2. Copiar endpoint `/monitoring/metrics` (Prometheus)
- **Validar:**
  ```bash
  curl "http://localhost:5000/api/v1/monitoring/data?category=network-probes"
  curl "http://localhost:5000/api/v1/monitoring/metrics?category=network-probes&metric_type=status"
  ```

#### **Dia 6: consulAPI (Frontend)**
- **Use:** GUIA_IMPLEMENTACAO_CORRIGIDO_V2.md - Seção 5
- **Ação:** Adicionar métodos `getMonitoringData()` e `syncMonitoringCache()` em `api.ts`
- **Validar:**
  - Verificar que importações TypeScript não têm erros
  - Testar no DevTools do browser: `consulAPI.getMonitoringData('network-probes')`

#### **Dias 7-8: DynamicMonitoringPage**
- **Use:** 
  - GUIA_IMPLEMENTACAO_CORRIGIDO_V2.md - Seção 4 (requestHandler)
  - PLANO original - Seção 5.2.1 (resto do componente)
- **Ação:**
  1. Criar componente base
  2. Substituir `requestHandler` pela versão do guia
  3. Manter restante do código do plano original
- **Validar:**
  - Página carrega sem erros
  - Filtros funcionam
  - Botão "Sincronizar" funciona

#### **Dias 9-10: 4 Páginas Específicas + Testes**
- **Use:** PLANO original - Seção 5.2.2 e Day 9 implementation
- **Dia 9.5:** AJUSTES_CRITICOS_PLANO_V2.md - Seção "Ajuste 5" (testes)
- **Validar:**
  ```bash
  ./run_all_persistence_tests.sh
  # Todos devem passar
  ```

#### **Dias 11-12: Categorization UI + Migration**
- **Use:** AJUSTES_CRITICOS_PLANO_V2.md - Seção "Ajuste 4" (script migração)
- **Ação:**
  ```bash
  python backend/migrate_categorization_to_json.py
  ```

#### **Dia 13: Validação Final**
- **Use:** GUIA_IMPLEMENTACAO_CORRIGIDO_V2.md - Checklist final

---

## ⚠️ CONFLITOS: O QUE PREVALECE?

Se houver conflito entre documentos:

**PRIORIDADE 1:** `GUIA_IMPLEMENTACAO_CORRIGIDO_V2.md`  
**PRIORIDADE 2:** `AJUSTES_CRITICOS_PLANO_V2.md`  
**PRIORIDADE 3:** `PLANO DE REFATORAÇÃO... 2.0.md`

### Exemplos de Conflitos Resolvidos:

| Situação | Plano Original Diz | Guia Corrigido Diz | ✅ USE |
|----------|-------------------|-------------------|--------|
| Endpoint `/monitoring/data` | Busca do Prometheus | Busca do Consul | **Guia Corrigido** |
| `MetadataFieldModel` | 3 campos `show_in_*` | 7 campos `show_in_*` | **Guia Corrigido** |
| `requestHandler` | Fetch direto | Usa `consulAPI.*` | **Guia Corrigido** |
| Referência Services.tsx | "Usar mesma lógica" | "Apenas referência" | **Guia Corrigido** |

---

## 🔍 BUSCA RÁPIDA

### Preciso de código para...

- **Adicionar 4 campos show_in_*:** Seção 1 do Guia Corrigido
- **Endpoint que busca serviços do Consul:** Seção 2 do Guia Corrigido
- **Endpoint que busca métricas do Prometheus:** Seção 3 do Guia Corrigido
- **Frontend chamar backend:** Seção 5 do Guia Corrigido
- **Script de migração:** Ajustes Críticos - Seção "Ajuste 4"
- **Entender arquitetura geral:** Plano Original - Seção 4
- **Ver cronograma completo:** Plano Original - Seção 8

### Preciso entender...

- **Por que 2 endpoints (data + metrics)?** Ajustes Críticos - "Ajuste 2"
- **Por que não usar lógica de Services.tsx?** Ajustes Críticos - "Ajuste 3"
- **Como funciona cache de tipos?** Plano Original - Seção 5.1.2
- **Estrutura de pastas:** Plano Original - Seção 6

---

## ✅ CHECKLIST PRÉ-IMPLEMENTAÇÃO

Antes de começar Dia 1:

- [ ] Li GUIA_IMPLEMENTACAO_CORRIGIDO_V2.md completamente
- [ ] Li AJUSTES_CRITICOS_PLANO_V2.md - seção "Resumo dos Ajustes"
- [ ] Revisei seções 3 e 4 do PLANO original
- [ ] Verifiquei que `show_in_*` já existe no código atual:
  ```bash
  grep -n "show_in_services" backend/api/metadata_fields_manager.py
  ```
- [ ] Entendi diferença entre `/monitoring/data` (Consul) e `/monitoring/metrics` (Prometheus)
- [ ] Tenho ambiente dev rodando e testado

---

## 🚀 COMEÇAR IMPLEMENTAÇÃO

Quando estiver pronto:

```bash
# 1. Criar branch de feature
git checkout -b feature/monitoring-v2

# 2. Abrir documentos lado a lado
code docs/GUIA_IMPLEMENTACAO_CORRIGIDO_V2.md
code docs/AJUSTES_CRITICOS_PLANO_V2.md

# 3. Seguir cronograma do Dia 1
# (Plano Original - Seção 8 - Implementation Plan)
```

---

**📖 DOCUMENTAÇÃO VALIDADA E PRONTA PARA USO!**

**Dúvidas?** Consulte primeiro o GUIA_IMPLEMENTACAO_CORRIGIDO_V2.md (código pronto).
