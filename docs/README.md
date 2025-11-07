# 📚 Documentação do Skills Eye

Bem-vindo à documentação completa do Skills Eye - Sistema dinâmico de gerenciamento Consul + Prometheus.

---

## 🎯 Sobre o Skills Eye

O **Skills Eye** é um sistema **100% dinâmico** que se adapta automaticamente à sua infraestrutura Prometheus:

- ✅ Extrai campos do `prometheus.yml` via SSH
- ✅ Detecta monitoring types automaticamente dos jobs
- ✅ Sincroniza metadata fields entre múltiplos servidores
- ✅ Auto-cadastra reference values ao criar serviços
- ✅ Replicação master→slave automática

**Diferencial:** Adicione novos tipos e campos no Prometheus - o Skills Eye detecta e adapta sozinho!

---

## 📂 Organização da Documentação

### 🚀 [Guias de Uso](guides/)
Documentação prática para usuários do sistema.

| Guia | Descrição |
|------|-----------|
| **[Quick Start](guides/quick-start.md)** | Início rápido - configure e rode em 10 minutos |
| **[Prometheus Basic Auth](guides/prometheus-basic-auth.md)** | Configurar autenticação HTTP Basic |
| **[Restart Guide](guides/restart-guide.md)** | Como reiniciar serviços backend/frontend |
| **[Reference Values](guides/reference-values.md)** | Sistema de valores de referência |
| **[External Labels](guides/external-labels.md)** | Uso correto de external_labels |
| **[Migration Guide](guides/migration.md)** | Migração entre versões |
| **[Git Workflow](guides/git-workflow.md)** | Boas práticas Git para o projeto |

### 🏗️ [Arquitetura](architecture/)
Design técnico e decisões arquiteturais.

| Documento | Descrição |
|-----------|-----------|
| **[Metadata Fields Analysis](architecture/METADATA_FIELDS_ANALYSIS.md)** | Análise do sistema de campos dinâmicos |
| **[Monitoring Types](architecture/monitoring-types.md)** | Sistema de tipos de monitoramento dinâmico |
| **[Multi-Site](architecture/multi-site.md)** | Setup multi-servidor Prometheus |
| **[Dynamic Fields](architecture/dynamic-fields.md)** | Compatibilidade de campos dinâmicos |
| **[Service ID Sanitization](architecture/service-id-sanitization.md)** | Regras de sanitização de IDs |
| **[Reload Logic](architecture/reload-logic.md)** | Lógica de recarregamento de serviços |
| **[Prometheus Config Editor](architecture/PROMETHEUS_CONFIG_PAGE_SUMMARY.md)** | Editor YAML multi-servidor |
| **[Server Detection](architecture/SERVER_DETECTION_INTEGRATION.md)** | Detecção automática de servidores |

### 🔌 [API Reference](api/)
Documentação completa da API REST.

| Documento | Descrição |
|-----------|-----------|
| **[Endpoints Reference](api/endpoints-reference.md)** | Todos os 100+ endpoints documentados |

**Swagger UI Interativo:** http://localhost:5000/docs

### 🛠️ [Desenvolvimento](development/)
Guias para desenvolvedores que contribuem com o projeto.

*Em construção - documentação de setup, testes, contribuição*

### 📅 [Planejamento](planning/)
Roadmap e planos de refatoração futuros.

| Documento | Descrição |
|-----------|-----------|
| **[Refactoring Architecture](planning/refactoring-architecture.md)** | Proposta de arquitetura futura (Clean Architecture) |
| **[Refactoring Plan](planning/refactoring-plan.md)** | Roadmap detalhado de refatoração (1626 linhas) |

### ⚡ [Performance](performance/)
Análises de performance e otimizações.

| Documento | Descrição |
|-----------|-----------|
| **[Analysis Complete](performance/analysis-complete.md)** | Análise completa de problemas de performance (1812 linhas) |
| **[Context API Implementation](performance/context-api-implementation.md)** | Implementação do Context API |
| **[Context API Checklist](performance/context-api-checklist.md)** | Checklist de testes de performance |

### 🔬 [Pesquisa](research/)
Estudos e pesquisas técnicas realizadas.

| Documento | Descrição |
|-----------|-----------|
| **[Prometheus Architecture Research](research/prometheus-architecture-research.md)** | Pesquisa web sobre arquitetura Prometheus |

### 🚨 [Incidentes](incidents/)
Relatórios de incidentes e lições aprendidas.

| Documento | Descrição |
|-----------|-----------|
| **[Jobs Perdidos](incidents/jobs-perdidos.md)** | Incidente: Jobs perdidos após edição YAML sem backup |

### 📜 [Histórico](history/)
Documentação de fases anteriores do projeto.

| Documento | Descrição |
|-----------|-----------|
| **[Phase 1](history/phase1-implementation.md)** | KV Namespace e Dual Storage Pattern |
| **[Phase 2](history/phase2-implementation.md)** | Service Presets e Advanced Search |
| **[Phase 3](history/phase3-implementation.md)** | Frontend Modernization |
| **[Prometheus Editor Phase 1](history/prometheus-editor-phase1.md)** | Primeira versão do editor YAML |
| **[Installer Improvements](history/installer-improvements.md)** | Melhorias do remote installer |
| **[Layout Standardization](history/layout-standardization.md)** | Padronização de layouts |

### 🗑️ [Obsoletos](obsolete/)
Documentos históricos que não refletem mais o estado atual do projeto.

*Mantidos para referência histórica, mas não devem ser usados.*

---

## 🎓 Por Onde Começar?

### Se você é novo no projeto:
1. Leia o **[README principal](../README.md)** - Visão geral do projeto
2. Siga o **[Quick Start](guides/quick-start.md)** - Setup em 10 minutos
3. Explore o **[Swagger UI](http://localhost:5000/docs)** - API interativa
4. Veja **[Monitoring Types](architecture/monitoring-types.md)** - Entenda o coração do sistema

### Se você vai desenvolver:
1. Leia **[Refactoring Architecture](planning/refactoring-architecture.md)** - Direção futura
2. Veja **[Endpoints Reference](api/endpoints-reference.md)** - Toda a API
3. Entenda **[Dynamic Fields](architecture/dynamic-fields.md)** - Sistema dinâmico
4. Consulte **[Git Workflow](guides/git-workflow.md)** - Boas práticas

### Se você vai operar:
1. **[Quick Start](guides/quick-start.md)** - Setup inicial
2. **[Restart Guide](guides/restart-guide.md)** - Reiniciar serviços
3. **[Prometheus Basic Auth](guides/prometheus-basic-auth.md)** - Segurança
4. **[Migration Guide](guides/migration.md)** - Atualizar versões

---

## 📊 Estatísticas da Documentação

| Categoria | Documentos | Linhas Totais |
|-----------|-----------|---------------|
| **Guias** | 7 | ~3.500 linhas |
| **Arquitetura** | 8 | ~5.800 linhas |
| **API** | 1 | ~2.100 linhas |
| **Planejamento** | 2 | ~2.600 linhas |
| **Performance** | 3 | ~2.300 linhas |
| **Pesquisa** | 1 | ~800 linhas |
| **Incidentes** | 1 | ~280 linhas |
| **Histórico** | 6 | ~4.200 linhas |
| **TOTAL** | **29** | **~21.600 linhas** |

---

## 🔍 Busca Rápida

### Tópicos Comuns

**Como adicionar um novo tipo de monitoramento?**
→ É automático! Adicione um job no `prometheus.yml`, o Skills Eye detecta sozinho. Ver: [Monitoring Types](architecture/monitoring-types.md)

**Como adicionar um novo campo de metadata?**
→ Adicione no `relabel_configs` do Prometheus, sincronize via interface. Ver: [Dynamic Fields](architecture/dynamic-fields.md)

**Como configurar multi-site?**
→ Configure `PROMETHEUS_CONFIG_HOSTS` no `.env`. Ver: [Multi-Site](architecture/multi-site.md)

**Como instalar exporters remotamente?**
→ Use a página Installer com SSH/WinRM/PSExec. Ver: [API Reference - Installer](api/endpoints-reference.md#installer)

**Como funciona o cache de performance?**
→ Context API + cache por endpoint. Ver: [Context API Implementation](performance/context-api-implementation.md)

**Quais são todos os endpoints da API?**
→ Ver: [Endpoints Reference](api/endpoints-reference.md) - 100+ endpoints documentados

---

## 🤝 Contribuindo com a Documentação

A documentação é mantida em Markdown e segue estas convenções:

**Estrutura de Arquivos:**
```
docs/
├── guides/          # Guias práticos (.md em kebab-case)
├── architecture/    # Docs técnicas (PascalCase ou SCREAMING_SNAKE_CASE)
├── api/            # API reference (kebab-case)
├── planning/       # Roadmap (kebab-case)
├── performance/    # Análises (kebab-case)
├── research/       # Pesquisas (kebab-case)
├── incidents/      # Relatórios (kebab-case)
└── history/        # Histórico (kebab-case com phase-)
```

**Estilo de Escrita:**
- ✅ Português-BR para texto
- ✅ Termos técnicos em inglês (API, endpoint, cache)
- ✅ Código comentado em português
- ✅ Exemplos práticos sempre que possível
- ✅ Diagramas quando ajudar a entender

**Atualização:**
- Ao modificar funcionalidade, atualize a documentação
- Mantenha exemplos sincronizados com código real
- Documente decisões arquiteturais importantes
- Registre lições aprendidas de incidentes

---

## 📞 Suporte

- 📧 Email: repositories@skillsit.com.br
- 🐛 Issues: https://github.com/DevSkillsIT/Skills-Eye/issues
- 📚 Docs: https://github.com/DevSkillsIT/Skills-Eye/tree/main/docs

---

<div align="center">

**Skills Eye - Sistema DINÂMICO**

*Adapta-se automaticamente ao seu Prometheus!*

[⬆ Voltar ao topo](#-documentação-do-skills-eye)

</div>
