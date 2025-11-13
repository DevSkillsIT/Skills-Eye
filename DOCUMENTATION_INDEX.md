# Índice de Documentação - Skills Eye

**Última Atualização:** 2025-11-12 (Reorganização Completa - Fase 2)

Este documento serve como índice para TODA a documentação do projeto, organizada por categoria.

**🆕 Mudanças nesta revisão (Fase 2):**
- ✅ **ESTRUTURA PROFISSIONAL:** Pastas organizadas seguindo melhores práticas
- ✅ **51+ arquivos reorganizados** da raiz para pastas apropriadas
- ✅ Scripts movidos para `scripts/{deployment,migration,development,benchmarks}`
- ✅ Logs movidos para `logs/` (gitignored)
- ✅ Dados movidos para `data/{baselines,fixtures,temp}`
- ✅ Screenshots movidos para `assets/screenshots/`
- ✅ Docs separados: `docs/developer/` vs `docs/user/`
- ✅ Correções isoladas em `docs/developer/corrections/`
- ✅ Arquitetura em `docs/developer/architecture/`
- ✅ README.md COMPLETAMENTE atualizado com navegação
- ✅ .gitignore atualizado para nova estrutura
- ✅ **RAIZ LIMPA:** Apenas 6 arquivos essenciais permanecem

---

## 📂 ESTRUTURA DO PROJETO

```
Skills-Eye/
├── backend/          # API FastAPI + Business Logic
├── frontend/         # React 19 + TypeScript
├── docs/            # 📖 DOCUMENTAÇÃO ORGANIZADA
│   ├── features/           # Funcionalidades principais (15 docs)
│   ├── developer/          # Para desenvolvedores
│   │   ├── corrections/    # Correções aplicadas (10 docs)
│   │   ├── architecture/   # Análises técnicas (8 docs)
│   │   └── troubleshooting/
│   ├── guides/             # Guias de uso
│   ├── planning/           # Roadmap e refatoração
│   ├── performance/        # Análises de performance
│   ├── obsolete/           # Documentos antigos
│   └── user/               # Para usuários finais
├── Tests/           # 🧪 34 TESTES ORGANIZADOS
│   ├── naming/             # 3 testes nomenclatura
│   ├── metadata/           # 12 testes campos dinâmicos
│   ├── performance/        # 5 testes performance
│   ├── integration/        # 14 testes integração
│   └── README.md
├── scripts/         # 🔧 AUTOMAÇÃO (25+ scripts)
│   ├── deployment/         # Deploy e restart (15 scripts)
│   ├── migration/          # Migrações (5 scripts)
│   ├── development/        # Análise e debug (7 scripts)
│   └── benchmarks/         # Performance tests (3 scripts)
├── data/            # 📊 DADOS DE TESTE
│   ├── baselines/          # Baselines JSON (3 arquivos)
│   ├── fixtures/           # Fixtures de teste (4 arquivos)
│   └── temp/               # Temporários (gitignored)
├── logs/            # 📝 LOGS (gitignored)
├── assets/          # 🖼️ SCREENSHOTS E ASSETS
│   └── screenshots/        # Capturas de tela (2 imagens)
└── tools/           # 🛠️ FERRAMENTAS AUXILIARES

RAIZ (apenas essenciais):
├── README.md               # Documentação principal
├── CLAUDE.md               # Instruções para IA
├── COMANDOS_RAPIDOS.md     # Quick reference
├── DOCUMENTATION_INDEX.md  # Este arquivo
├── .gitignore              # Git ignore rules
└── _ul                     # Arquivo de controle
```

---

## 🎯 NAVEGAÇÃO RÁPIDA POR PERFIL

### 👤 Usuário Final
- 📖 [README Principal](../README.md) - Início rápido e funcionalidades
- 📖 [Quick Start](docs/guides/quick-start.md) - Primeiros passos
- 📖 [Guias de Uso](docs/guides/) - Tutoriais passo a passo

### 👨‍💻 Desenvolvedor
- 🔧 [Arquitetura](docs/developer/architecture/) - Design técnico
- 🔧 [Correções Aplicadas](docs/developer/corrections/) - Histórico de fixes
- 🔧 [Testes](Tests/README.md) - 34 testes documentados
- 🔧 [Scripts](scripts/) - Automação e deploy
- 🔧 [Roadmap](docs/planning/) - Futuro do projeto

### 🔍 QA / Tester
- 🧪 [Tests/README.md](Tests/README.md) - Guia completo de testes
- 📊 [data/baselines/](data/baselines/) - Dados de baseline
- 📊 [data/fixtures/](data/fixtures/) - Fixtures de teste

### 🚀 DevOps
- 🔧 [scripts/deployment/](scripts/deployment/) - Scripts de deploy
- 🔧 [scripts/migration/](scripts/migration/) - Scripts de migração
- 📝 [logs/](logs/) - Arquivos de log

---

## 📚 DOCUMENTAÇÃO POR CATEGORIA

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

## 🎯 FEATURES E FUNCIONALIDADES

| Documento | Localização | Descrição |
|-----------|-------------|-----------|
| **Naming System Complete** | [docs/features/NAMING_SYSTEM_COMPLETE.md](docs/features/NAMING_SYSTEM_COMPLETE.md) | **NOVO** - Sistema de naming dinâmico 100% completo |
| **Guia de Uso Naming** | [docs/features/GUIA_USO_NAMING_SYSTEM.md](docs/features/GUIA_USO_NAMING_SYSTEM.md) | Guia prático de uso do naming system |
| **Migração Naming** | [docs/features/MIGRACAO_NAMING_DINAMICO_COMPLETA.md](docs/features/MIGRACAO_NAMING_DINAMICO_COMPLETA.md) | História completa da migração naming |
| **Plano Naming** | [docs/features/PLANO_NAMING_DINAMICO.md](docs/features/PLANO_NAMING_DINAMICO.md) | Plano original da implementação |
| **Análise Naming Sites** | [docs/features/ANALISE_NAMING_SITES_2025-11-12.md](docs/features/ANALISE_NAMING_SITES_2025-11-12.md) | Análise detalhada de sites e naming |
| **Resumo Dinâmico** | [docs/features/RESUMO_DINAMICO_COMPLETO.md](docs/features/RESUMO_DINAMICO_COMPLETO.md) | Resumo da implementação dinâmica |
| **Correções Fase 7** | [docs/features/CORRECOES_FASE_7_COMPLETA.md](docs/features/CORRECOES_FASE_7_COMPLETA.md) | Correções finais fase 7 |
| **Sites & External Labels** | [docs/features/RESPOSTA_SITES_EXTERNAL_LABELS.md](docs/features/RESPOSTA_SITES_EXTERNAL_LABELS.md) | Explicação de sites e external labels |
| **Dados Sites/External Labels** | [docs/features/EXPLICACAO_DADOS_SITES_EXTERNAL_LABELS.md](docs/features/EXPLICACAO_DADOS_SITES_EXTERNAL_LABELS.md) | Estrutura de dados detalhada |
| **Correções Sites** | [docs/features/CORRECOES_SITES_2025-11-12.md](docs/features/CORRECOES_SITES_2025-11-12.md) | Correções específicas de sites |
| **Consolidação Completa** | [docs/features/CONSOLIDACAO_COMPLETA_RESUMO.md](docs/features/CONSOLIDACAO_COMPLETA_RESUMO.md) | Resumo da consolidação settings→metadata |
| **Remoção Settings** | [docs/features/REMOCAO_SETTINGS_2025-11-12.md](docs/features/REMOCAO_SETTINGS_2025-11-12.md) | Migração /settings → /metadata-fields |
| **Implementação Completa** | [docs/features/IMPLEMENTACAO_COMPLETA.md](docs/features/IMPLEMENTACAO_COMPLETA.md) | Implementação completa de features |
| **Análise Backend** | [docs/features/ANALISE_BACKEND_SETTINGS_VS_METADATA.md](docs/features/ANALISE_BACKEND_SETTINGS_VS_METADATA.md) | Análise settings vs metadata |
| **Análise Arquitetura** | [docs/features/ANALISE_ARQUITETURA_FINAL.md](docs/features/ANALISE_ARQUITETURA_FINAL.md) | Análise final da arquitetura |

---

## 📝 SESSÕES E CORREÇÕES

| Documento | Localização | Descrição |
|-----------|-------------|-----------|
| **CHANGELOG Session** | [docs/sessions/CHANGELOG-SESSION.md](docs/sessions/CHANGELOG-SESSION.md) | Changelog de sessão específica |
| **Correções 2025-11-11** | [docs/sessions/CORRECOES_2025-11-11.md](docs/sessions/CORRECOES_2025-11-11.md) | Correções aplicadas em 11/11 |
| **Correções Críticas** | [docs/sessions/CORRECOES_CRITICAS_2025-11-11.md](docs/sessions/CORRECOES_CRITICAS_2025-11-11.md) | Correções críticas específicas |
| **Correções Finais 11/11** | [docs/sessions/CORRECOES_FINAIS_2025-11-11.md](docs/sessions/CORRECOES_FINAIS_2025-11-11.md) | Últimas correções de 11/11 |
| **Correções Completas** | [docs/sessions/CORRECOES_FINAIS_COMPLETAS.md](docs/sessions/CORRECOES_FINAIS_COMPLETAS.md) | Correções completas consolidadas |
| **Correções Estrutura KV** | [docs/sessions/CORRECOES_URGENTES_ESTRUTURA_KV.md](docs/sessions/CORRECOES_URGENTES_ESTRUTURA_KV.md) | Correções urgentes KV |
| **KV Órfãos** | [docs/sessions/CORRECOES_APLICADAS_KV_ORFAOS.md](docs/sessions/CORRECOES_APLICADAS_KV_ORFAOS.md) | Correção de campos órfãos |
| **Colunas** | [docs/sessions/CORRECOES_COLUNAS_2025-11-12.md](docs/sessions/CORRECOES_COLUNAS_2025-11-12.md) | Correções de colunas em tabelas |
| **External Labels Aba** | [docs/sessions/CORRECOES_FINAIS_ABA_EXTERNAL_LABELS.md](docs/sessions/CORRECOES_FINAIS_ABA_EXTERNAL_LABELS.md) | Correções aba external labels |
| **Órfãos vs Missing** | [docs/sessions/EXPLICACAO_ORFAOS_VS_MISSING.md](docs/sessions/EXPLICACAO_ORFAOS_VS_MISSING.md) | Explicação de campos órfãos |

---

## 🧪 TESTES AUTOMATIZADOS

**Localização:** [Tests/](Tests/)

| Categoria | Testes | Descrição |
|-----------|--------|-----------|
| **Naming** | 3 testes | Sistema de naming dinâmico (11/12 passing) |
| **Metadata** | 12 testes | Metadata fields, reference values, external labels |
| **Performance** | 5 testes | Performance, cache, rendering, API benchmarks |
| **Integration** | 14 testes | Endpoints, validação, multi-site, prometheus config |
| **TOTAL** | **34 testes** | **✅ 33/34 passing (97%)** |

**Documentação completa:** [Tests/README.md](Tests/README.md)

**Como executar:**
```bash
# Todos os testes de naming
for test in Tests/naming/*.py; do python3 "$test"; done

# Todos os testes de metadata
for test in Tests/metadata/*.py; do python3 "$test"; done

# Todos os testes de performance
for test in Tests/performance/*.py; do python3 "$test"; done

# Todos os testes de integração
for test in Tests/integration/*.py; do python3 "$test"; done
```

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
