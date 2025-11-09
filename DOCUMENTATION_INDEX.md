# Índice de Documentação - Skills Eye

**Última Atualização:** 2025-01-07

Este documento serve como índice para TODA a documentação do projeto, organizada por categoria.

---

## 📊 PERFORMANCE E OTIMIZAÇÕES

### Documentação Principal

| Documento | Localização | Descrição |
|-----------|-------------|-----------|
| **Relatório Real de Performance** | [docs/performance/RELATORIO_REAL_PERFORMANCE.md](docs/performance/RELATORIO_REAL_PERFORMANCE.md) | **DOCUMENTO PRINCIPAL** - Análise completa de performance P0/P1/P2, caminho das pedras para migrações futuras |
| **Resumo Executivo P2** | [docs/performance/RESUMO_EXECUTIVO_P2.md](docs/performance/RESUMO_EXECUTIVO_P2.md) | Resumo executivo da implementação P2 (AsyncSSH + TAR) |
| **Context API Implementation** | [docs/performance/context-api-implementation.md](docs/performance/context-api-implementation.md) | Implementação do Context API no frontend |
| **Context API Checklist** | [docs/performance/context-api-checklist.md](docs/performance/context-api-checklist.md) | Checklist de validação do Context API |
| **Analysis Complete** | [docs/performance/analysis-complete.md](docs/performance/analysis-complete.md) | Análise completa de problemas de performance (anterior ao P2) |

### Dados de Performance

**P0 (Baseline):**
- Cold start: 22.0s
- Force refresh: 22.0s
- Status: ❌ Lento

**P1 (Paramiko Pool):**
- Cold start: ~18s
- Force refresh: 15.8s
- Status: ⚠️ Melhor mas ainda lento

**P2 (AsyncSSH + TAR):**
- Cold start: **2.4s** ✅
- Force refresh: **4.6s** ✅
- Status: ✅ **ÓTIMO** (79% mais rápido!)

---

## 🔐 SSH E OTIMIZAÇÕES DE REDE

| Documento | Localização | Descrição |
|-----------|-------------|-----------|
| **Análise SSH Completa** | [docs/ssh-optimization/ANALISE_SSH_COMPLETA.md](docs/ssh-optimization/ANALISE_SSH_COMPLETA.md) | Análise de 21 arquivos que usam SSH, decisões de migração Paramiko vs AsyncSSH |

### Quando Usar Cada Tecnologia

**AsyncSSH + TAR (P2):**
- ✅ Múltiplos arquivos de múltiplos servidores
- ✅ Hot path (endpoints frequentes)
- ✅ Operações bulk/batch
- ✅ Cold start crítico

**Paramiko (manter):**
- ✅ Operações individuais
- ✅ Operações interativas (instaladores)
- ✅ Operações raras
- ✅ Single-server local

---

## 🏗️ ARQUITETURA

| Documento | Localização | Descrição |
|-----------|-------------|-----------|
| **Dynamic Fields** | [docs/architecture/dynamic-fields.md](docs/architecture/dynamic-fields.md) | Sistema de campos dinâmicos metadata |
| **Multi-Site** | [docs/architecture/multi-site.md](docs/architecture/multi-site.md) | Arquitetura multi-site |
| **Metadata Fields Analysis** | [docs/architecture/METADATA_FIELDS_ANALYSIS.md](docs/architecture/METADATA_FIELDS_ANALYSIS.md) | Análise detalhada de metadata fields |
| **Service ID Sanitization** | [docs/architecture/service-id-sanitization.md](docs/architecture/service-id-sanitization.md) | Regras de sanitização de service IDs |
| **Reload Logic** | [docs/architecture/reload-logic.md](docs/architecture/reload-logic.md) | Lógica de reload do Prometheus |
| **Monitoring Types** | [docs/architecture/monitoring-types.md](docs/architecture/monitoring-types.md) | Sistema de tipos de monitoramento |
| **Prometheus Config Summary** | [docs/architecture/PROMETHEUS_CONFIG_PAGE_SUMMARY.md](docs/architecture/PROMETHEUS_CONFIG_PAGE_SUMMARY.md) | Página de configuração Prometheus |
| **Server Detection** | [docs/architecture/SERVER_DETECTION_INTEGRATION.md](docs/architecture/SERVER_DETECTION_INTEGRATION.md) | Integração de detecção de servidores |

---

## 📚 GUIAS E TUTORIAIS

| Documento | Localização | Descrição |
|-----------|-------------|-----------|
| **Quick Start** | [docs/guides/quick-start.md](docs/guides/quick-start.md) | Início rápido do projeto |
| **Migration Guide** | [docs/guides/migration.md](docs/guides/migration.md) | Guia de migração de dados |
| **Git Workflow** | [docs/guides/git-workflow.md](docs/guides/git-workflow.md) | Workflow Git do projeto |
| **Restart Guide** | [docs/guides/restart-guide.md](docs/guides/restart-guide.md) | Como reiniciar a aplicação |
| **External Labels** | [docs/guides/external-labels.md](docs/guides/external-labels.md) | Guia de external labels |
| **Reference Values** | [docs/guides/reference-values.md](docs/guides/reference-values.md) | Sistema de valores de referência |
| **Prometheus Basic Auth** | [docs/guides/prometheus-basic-auth.md](docs/guides/prometheus-basic-auth.md) | Configurar Basic Auth no Prometheus |

---

## 📜 HISTÓRICO DE IMPLEMENTAÇÕES

| Documento | Localização | Descrição |
|-----------|-------------|-----------|
| **Phase 1** | [docs/history/phase1-implementation.md](docs/history/phase1-implementation.md) | KV namespace, dual storage |
| **Phase 2** | [docs/history/phase2-implementation.md](docs/history/phase2-implementation.md) | Service presets, advanced search |
| **Phase 3** | [docs/history/phase3-implementation.md](docs/history/phase3-implementation.md) | Frontend modernization |
| **Installer Improvements** | [docs/history/installer-improvements.md](docs/history/installer-improvements.md) | Melhorias no instalador |
| **Layout Standardization** | [docs/history/layout-standardization.md](docs/history/layout-standardization.md) | Padronização de layout |
| **Prometheus Editor Phase 1** | [docs/history/prometheus-editor-phase1.md](docs/history/prometheus-editor-phase1.md) | Editor Prometheus inicial |

---

## 🔧 API E ENDPOINTS

| Documento | Localização | Descrição |
|-----------|-------------|-----------|
| **Endpoints Reference** | [docs/api/endpoints-reference.md](docs/api/endpoints-reference.md) | Referência completa de endpoints |

---

## 📋 PLANEJAMENTO

| Documento | Localização | Descrição |
|-----------|-------------|-----------|
| **Refactoring Plan** | [docs/planning/refactoring-plan.md](docs/planning/refactoring-plan.md) | Plano de refatoração |
| **Refactoring Architecture** | [docs/planning/refactoring-architecture.md](docs/planning/refactoring-architecture.md) | Arquitetura de refatoração |

---

## 🔬 PESQUISAS

| Documento | Localização | Descrição |
|-----------|-------------|-----------|
| **Prometheus Architecture Research** | [docs/research/prometheus-architecture-research.md](docs/research/prometheus-architecture-research.md) | Pesquisa sobre arquitetura Prometheus |

---

## 🚨 INCIDENTES

| Documento | Localização | Descrição |
|-----------|-------------|-----------|
| **Jobs Perdidos** | [docs/incidents/jobs-perdidos.md](docs/incidents/jobs-perdidos.md) | Incidente de jobs perdidos |

---

## 📁 DOCUMENTAÇÃO OBSOLETA

Documentos antigos mantidos para referência histórica:

📂 [docs/obsolete/](docs/obsolete/)

---

## 🎯 DOCUMENTOS PRINCIPAIS POR CASO DE USO

### Preciso entender performance do sistema

1. ✅ [docs/performance/RELATORIO_REAL_PERFORMANCE.md](docs/performance/RELATORIO_REAL_PERFORMANCE.md) - **LER PRIMEIRO**
2. [docs/performance/RESUMO_EXECUTIVO_P2.md](docs/performance/RESUMO_EXECUTIVO_P2.md) - Resumo executivo
3. [docs/ssh-optimization/ANALISE_SSH_COMPLETA.md](docs/ssh-optimization/ANALISE_SSH_COMPLETA.md) - Decisões SSH

### Preciso migrar código Paramiko → AsyncSSH

1. ✅ [docs/performance/RELATORIO_REAL_PERFORMANCE.md](docs/performance/RELATORIO_REAL_PERFORMANCE.md) - Seção "Caminho das Pedras"
2. [docs/ssh-optimization/ANALISE_SSH_COMPLETA.md](docs/ssh-optimization/ANALISE_SSH_COMPLETA.md) - Análise completa

### Preciso entender arquitetura

1. [docs/architecture/dynamic-fields.md](docs/architecture/dynamic-fields.md) - Campos dinâmicos
2. [docs/architecture/multi-site.md](docs/architecture/multi-site.md) - Multi-site
3. [CLAUDE.md](CLAUDE.md) - Visão geral completa

### Preciso começar a desenvolver

1. [docs/guides/quick-start.md](docs/guides/quick-start.md) - Início rápido
2. [docs/guides/git-workflow.md](docs/guides/git-workflow.md) - Workflow Git
3. [CLAUDE.md](CLAUDE.md) - Visão geral técnica

---

## 📝 COMO MANTER ESTA DOCUMENTAÇÃO

**REGRAS:**

1. ✅ **Documentação nova** → Adicione na pasta `docs/` com categoria apropriada
2. ✅ **Documentação redundante** → Mescle no documento principal existente
3. ✅ **Documentação obsoleta** → Mova para `docs/obsolete/`
4. ✅ **Atualizações importantes** → Atualize este INDEX.md
5. ✅ **Documentação de sessão** → `docs/history/session-summaries/`

**ESTRUTURA DE PASTAS:**

```
docs/
├── api/              ← Documentação de API
├── architecture/     ← Documentação de arquitetura
├── guides/           ← Guias e tutoriais
├── history/          ← Histórico de implementações
├── incidents/        ← Incidentes e soluções
├── obsolete/         ← Documentos antigos (manter para referência)
├── performance/      ← Análises e otimizações de performance
├── planning/         ← Planejamento e roadmap
├── research/         ← Pesquisas técnicas
└── ssh-optimization/ ← Otimizações SSH específicas
```

---

**ÚLTIMA REVISÃO:** 2025-01-07 (Implementação P2)
**PRÓXIMA REVISÃO:** Quando houver mudanças significativas
