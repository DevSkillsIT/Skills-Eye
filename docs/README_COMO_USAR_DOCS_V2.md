# 📚 COMO USAR A DOCUMENTAÇÃO DO PLANO V2.0

**Data:** 13/11/2025  
**Versão:** 2.0 - ESTRUTURA 2 PARTES  
**Status:** DOCUMENTAÇÃO COMPLETA E VALIDADA

---

## 🎯 ESTRUTURA DA DOCUMENTAÇÃO

Você tem **5 documentos** para a implementação, divididos em 2 categorias:

### 📘 CATEGORIA 1: PLANO PRINCIPAL (2 PARTES - SUBSTITUI O ORIGINAL)

#### 1️⃣ **PLANO_V2_PARTE1_ANALISE_ARQUITETURA.md**
- **Tamanho:** ~900 linhas (~50 KB)
- **Quando usar:** Antes de implementar (contexto técnico)
- **O que contém:**
  - Sumário executivo (12-13 dias, não 10-15)
  - Análise do projeto atual
  - ⚠️ **AVISOS sobre show_in_* existentes**
  - Recomendações técnicas (dual endpoint)
  - Arquitetura proposta (diagramas atualizados)
  - Componentes a criar (specs completas)
- **Por que ler:** Entender decisões técnicas e "POR QUÊ"

#### 2️⃣ **PLANO_V2_PARTE2_IMPLEMENTACAO.md**
- **Tamanho:** ~1000 linhas (~60 KB)
- **Quando usar:** Durante implementação (guia dia-a-dia)
- **O que contém:**
  - FASE 1: Preparação (Dias 1-2)
  - FASE 2: Backend (Dias 3-5)
  - FASE 3: Frontend (Dias 6-8)
  - FASE 4: Testes (Dias 9-10)
  - **Dia 9.5:** ⭐ Testes de persistência (NOVO)
  - FASE 5: Migração e Deploy (Dias 11-13)
  - **Dia 11:** ⭐ Migração categorização (NOVO)
  - Checklists de validação
- **Por que ler:** Saber "QUANDO" e "COMO" fazer cada passo

### 📗 CATEGORIA 2: GUIAS E CORREÇÕES

#### 3️⃣ **GUIA_IMPLEMENTACAO_CORRIGIDO_V2.md** ⭐ **USE DURANTE CODIFICAÇÃO**
- **Tamanho:** 642 linhas (23 KB)
- **Quando usar:** Durante a codificação (Dias 3-8)
- **O que contém:**
  - Código Python/TypeScript pronto para copiar
  - Substituições de seções problemáticas
  - Implementações completas:
    - MetadataFieldModel com 4 novos campos
    - Endpoint `/monitoring/data` (Consul)
    - Endpoint `/monitoring/metrics` (Prometheus)
    - DynamicMonitoringPage com consulAPI
    - Métodos novos em consulAPI
  - Checklist de validação final

#### 4️⃣ **AJUSTES_CRITICOS_PLANO_V2.md**
- **Tamanho:** 1162 linhas (35 KB)
- **Quando usar:** Para entender PORQUÊ das mudanças
- **O que contém:**
  - Explicação detalhada dos 5 ajustes
  - Contexto histórico das correções
  - Script de migração completo
  - Integração com testes de persistência

#### 5️⃣ **NOTA_AJUSTES_PLANO_V2.md** ⭐ **LER PRIMEIRO**
- **Tamanho:** 3.4 KB
- **Quando usar:** Antes de tudo (resumo executivo)
- **O que contém:**
  - Resumo dos 5 ajustes críticos
  - Impacto de cada ajuste
  - Checklist rápido

#### 6️⃣ **README_COMO_USAR_DOCS_V2.md** (este arquivo)
- **Tamanho:** 7 KB
- **Quando usar:** Sempre que estiver perdido
- **O que contém:**
  - Guia de navegação
  - Workflow de implementação
  - Ordem de leitura recomendada

---

## 📋 WORKFLOW DE IMPLEMENTAÇÃO

### ANTES DE COMEÇAR
```bash
# 1. Ler documentos na ordem:
1º → NOTA_AJUSTES_PLANO_V2.md              # Resumo executivo rápido
2º → PLANO_V2_PARTE1_ANALISE_ARQUITETURA.md  # Contexto técnico e POR QUÊ
3º → PLANO_V2_PARTE2_IMPLEMENTACAO.md      # Cronograma dia-a-dia
4º → GUIA_IMPLEMENTACAO_CORRIGIDO_V2.md    # Código pronto para copiar

# 2. Validar pré-requisitos:
✓ Backend rodando (http://localhost:5000)
✓ Frontend rodando (http://localhost:8081)
✓ Consul acessível (http://localhost:8500)
✓ Testes de persistência passando (run_all_persistence_tests.sh)
```

### DURANTE A IMPLEMENTAÇÃO

#### **Dias 1-2: Análise e Setup**
- **Use:** PLANO_V2_PARTE2_IMPLEMENTACAO.md - FASE 1 (Dias 1-2)
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
- **Use:** PLANO_V2_PARTE1_ANALISE_ARQUITETURA.md - Seções 5.1.1, 5.1.2, 5.1.3
- **Ação:** Implementar cache de KV e categorization_rule_engine
- **Nota:** Código completo está no GUIA_IMPLEMENTACAO_CORRIGIDO_V2.md

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
  - PLANO_V2_PARTE1_ANALISE_ARQUITETURA.md - Seção 5.2.2 (componente completo)
- **Ação:**
  1. Criar componente base
  2. Usar `requestHandler` da versão corrigida
  3. Seguir estrutura do PLANO_V2_PARTE1
- **Validar:**
  - Página carrega sem erros
  - Filtros funcionam
  - Botão "Sincronizar" funciona

#### **Dias 9-10: 4 Páginas Específicas + Testes**
- **Use:** PLANO_V2_PARTE2_IMPLEMENTACAO.md - FASE 4 (Dias 9-10)
- **Dia 9.5:** PLANO_V2_PARTE2_IMPLEMENTACAO.md - DIA 9.5 (Testes de Persistência)
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

**PRIORIDADE 1:** `GUIA_IMPLEMENTACAO_CORRIGIDO_V2.md` (código pronto)  
**PRIORIDADE 2:** `PLANO_V2_PARTE2_IMPLEMENTACAO.md` (cronograma)  
**PRIORIDADE 3:** `PLANO_V2_PARTE1_ANALISE_ARQUITETURA.md` (contexto técnico)

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

- **Adicionar 4 campos show_in_*:** GUIA_IMPLEMENTACAO_CORRIGIDO_V2.md - Seção 1
- **Endpoint que busca serviços do Consul:** GUIA_IMPLEMENTACAO_CORRIGIDO_V2.md - Seção 2
- **Endpoint que busca métricas do Prometheus:** GUIA_IMPLEMENTACAO_CORRIGIDO_V2.md - Seção 3
- **Frontend chamar backend:** GUIA_IMPLEMENTACAO_CORRIGIDO_V2.md - Seção 5
- **Script de migração:** AJUSTES_CRITICOS_PLANO_V2.md - Seção "Ajuste 4"
- **Entender arquitetura geral:** PLANO_V2_PARTE1_ANALISE_ARQUITETURA.md - Seção 4
- **Ver cronograma completo:** PLANO_V2_PARTE2_IMPLEMENTACAO.md - Todas as fases

### Preciso entender...

- **Por que 2 endpoints (data + metrics)?** PLANO_V2_PARTE1_ANALISE_ARQUITETURA.md - Seção 3.2
- **Por que não usar lógica de Services.tsx?** PLANO_V2_PARTE1_ANALISE_ARQUITETURA.md - Seção 2.2
- **Como funciona cache de tipos?** PLANO_V2_PARTE1_ANALISE_ARQUITETURA.md - Seção 3.3
- **Estrutura de componentes:** PLANO_V2_PARTE1_ANALISE_ARQUITETURA.md - Seção 5

---

## ✅ CHECKLIST PRÉ-IMPLEMENTAÇÃO

Antes de começar Dia 1:

- [ ] Li NOTA_AJUSTES_PLANO_V2.md (resumo executivo)
- [ ] Li PLANO_V2_PARTE1_ANALISE_ARQUITETURA.md (contexto)
- [ ] Li PLANO_V2_PARTE2_IMPLEMENTACAO.md (cronograma dias 1-13)
- [ ] Li GUIA_IMPLEMENTACAO_CORRIGIDO_V2.md (código pronto)
- [ ] Verifiquei que `show_in_*` já existe no código atual:
  ```bash
  grep -n "show_in_services" backend/api/metadata_fields_manager.py
  ```
- [ ] Entendi diferença entre `/monitoring/data` (Consul) e `/monitoring/metrics` (Prometheus)
- [ ] Tenho ambiente dev rodando e testado (backend:5000, frontend:8081)

---

## 🚀 COMEÇAR IMPLEMENTAÇÃO

Quando estiver pronto:

```bash
# 1. Criar branch de feature
git checkout -b feature/monitoring-v2

# 2. Abrir documentos lado a lado
code docs/PLANO_V2_PARTE2_IMPLEMENTACAO.md
code docs/GUIA_IMPLEMENTACAO_CORRIGIDO_V2.md

# 3. Seguir cronograma do Dia 1
# (PLANO_V2_PARTE2_IMPLEMENTACAO.md - FASE 1 - Dia 1)
```

---

**📖 DOCUMENTAÇÃO VALIDADA E PRONTA PARA USO!**

**Dúvidas?** Consulte primeiro o GUIA_IMPLEMENTACAO_CORRIGIDO_V2.md (código pronto).
