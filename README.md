# Skills Eye Web Application

<div align="center">

![Version](https://img.shields.io/badge/version-2.3.0-blue.svg)
![Status](https://img.shields.io/badge/status-production--ready-success.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)

**Sistema completo e DINÂMICO de gerenciamento Consul + Prometheus**

[Instalação](#-instalação) • [Funcionalidades](#-funcionalidades) • [Documentação](#-documentação) • [API](#-api-reference)

</div>

---

## 📋 Sobre o Projeto

O **Skills Eye** é uma aplicação web moderna e **100% dinâmica** para gerenciar serviços do HashiCorp Consul, com foco em infraestrutura de monitoramento Prometheus.

### 🎯 Filosofia do Projeto

**Sistema DINÂMICO - Zero Hardcode:**
- ✅ Campos extraídos automaticamente do `prometheus.yml` via SSH
- ✅ Monitoring types detectados dinamicamente dos jobs Prometheus
- ✅ Metadata fields sincronizados com múltiplos servidores
- ✅ Reference values auto-cadastrados ao criar serviços
- ✅ Multi-site: master→slave replication automática
- ✅ Performance: Context API, cache inteligente, operações paralelas

**Diferencial:** Adicione novos tipos de monitoramento e campos no Prometheus - o Skills Eye detecta e adapta automaticamente!

### Stack Tecnológico

**Backend:**
- Python 3.12+
- FastAPI 0.115+ (async)
- httpx (async HTTP client)
- Consul HTTP API
- paramiko (SSH para edição remota YAML)
- ruamel.yaml (preservação de comentários)
- pywinrm + pypsexec (instaladores Windows)

**Frontend:**
- React 19+
- TypeScript (strict mode)
- Ant Design Pro (ProTable, ProLayout)
- @ant-design/charts (G2Plot visualizations)
- @dnd-kit (drag & drop)
- Context API (state management)

**Infraestrutura:**
- Consul 1.15+ (Service Mesh + KV Store)
- Prometheus 2.40+ (Monitoring)
- Blackbox Exporter (Probes)
- Multi-server SSH (edição remota YAML)

---

## 🚀 Instalação

### Pré-requisitos

- Python 3.12 ou superior
- Node.js 18+ e npm
- Consul rodando (local ou remoto)
- Git
- SSH acesso aos servidores Prometheus (para edição remota de configs)

### 1. Clone o Repositório

```bash
git clone https://github.com/DevSkillsIT/Skills-Eye.git
cd Skills-Eye
```

### 2. Configuração do Backend

```bash
cd backend

# Criar ambiente virtual
python -m venv venv

# Ativar ambiente virtual
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Instalar dependências
pip install -r requirements.txt

# Configurar variáveis de ambiente
cp .env.example .env
# Edite .env com suas configurações:
# CONSUL_HOST=172.16.1.26
# CONSUL_PORT=8500
# CONSUL_TOKEN=your-token-here  # se ACL habilitado
# PROMETHEUS_CONFIG_HOSTS=host1:port/user/pass;host2:port/user/pass
```

### 3. Configuração do Frontend

```bash
cd frontend

# Instalar dependências
npm install

# Configurar API endpoint (se necessário)
# Edite frontend/src/services/api.ts
# baseURL: 'http://localhost:5000/api/v1'
```

### 4. Iniciar Aplicação

**Opção 1 - Desenvolvimento (2 terminais):**

```bash
# Terminal 1 - Backend
cd backend
python app.py
# Backend: http://localhost:5000
# Swagger UI: http://localhost:5000/docs

# Terminal 2 - Frontend
cd frontend
npm run dev
# Frontend: http://localhost:8081
```

**Opção 2 - Script Automático (Windows):**

```bash
restart-app.bat
# Mata processos antigos, limpa cache, inicia ambos
```

**Acesse:** http://localhost:8081

---

## ✨ Funcionalidades

### 🎯 Dashboard Moderno
- **Métricas visuais em tempo real** com cache inteligente (30s)
- **Gráficos de distribuição** por ambiente, datacenter, tipo de monitoramento
- **Health status** do cluster Consul
- **Timeline de atividades recentes** com audit log integrado
- **Auto-refresh configurável** sem sobrecarga do backend
- **Ações rápidas** para tarefas comuns

### 🔬 Sistema de Monitoring Types (DINÂMICO)
- **Detecção automática** de tipos de monitoramento dos jobs Prometheus
- **Categorização inteligente:** System, Network, Web, Database, Messaging, Cache
- **Matchers configuráveis** para classificação automática de serviços
- **Formulários dinâmicos** adaptados a cada tipo de exporter
- **Zero configuração:** Adicione job no Prometheus, Skills Eye detecta!
- **Páginas:** Exporters, Hosts, MonitoringTypes, TestMonitoringTypes

### 🌐 Multi-Site Prometheus
- **Gerenciamento de múltiplos servidores** Prometheus via SSH
- **Master→Slave replication** automática de configurações
- **Editor YAML remoto** com preservação de comentários
- **Validação com promtool** antes de aplicar mudanças
- **Backup automático** timestamped antes de cada edição
- **Reload inteligente** de serviços via systemctl
- **Página:** PrometheusConfig

### 📊 Campos Dinâmicos (Metadata Fields)
- **Extração automática** de campos do `relabel_configs` do Prometheus
- **Sincronização multi-servidor** via SSH
- **Autocomplete inteligente** com reference values
- **Formulários adaptativos** baseados em esquema JSON
- **Reordenação drag & drop** de campos
- **Blacklist** de campos que não devem ter autocomplete
- **Página:** MetadataFields

### 📝 Reference Values
- **Auto-cadastro** ao criar serviços novos
- **Display name** customizável para cada valor
- **Gerenciamento centralizado** de valores permitidos
- **Proteção contra deleção** de valores em uso
- **Sincronização** entre serviços e formulários
- **Página:** ReferenceValues

### 🎨 Service Presets
- **Templates reutilizáveis** para serviços
- **Variáveis customizáveis** `${var}` e `${var:default}`
- **Preview antes do registro** com substituição visual
- **Bulk registration** (múltiplos serviços de uma vez)
- **Presets built-in** para exporters populares
- **Página:** ServicePresets

### 📊 Blackbox Targets
- **CRUD completo** de alvos de monitoramento
- **Múltiplos módulos:** HTTP, ICMP, TCP, SSH, DNS
- **Organização em grupos** lógicos
- **Import/Export** CSV e XLSX
- **Geração automática** de configs Prometheus
- **Bulk operations:** enable/disable múltiplos alvos
- **Página:** BlackboxTargets

### 🗂️ Blackbox Groups
- **Organização por projeto/cliente/ambiente**
- **Tags e metadata** customizável
- **Visualização hierárquica** de targets
- **Gestão centralizada** de grupos
- **Página:** BlackboxGroups

### 🔍 Busca Avançada
- **12 operadores de comparação:** eq, ne, gt, lt, gte, lte, contains, not_contains, in, not_in, regex, exists
- **Múltiplas condições** com AND/OR
- **Busca em campos nested:** `Meta.company`, `Meta.env`
- **Preview visual** das condições
- **Integração** com todas as tabelas do sistema
- **Salvar pesquisas** favoritas no KV

### 💾 KV Store Browser
- **Navegação visual em árvore** do Consul KV
- **Editor JSON integrado** com syntax highlighting
- **Namespace isolado:** `skills/eye/`
- **Metadados automáticos:** created_at, updated_by, version
- **Breadcrumb navigation** para facilitar navegação
- **Página:** KvBrowser

### 📜 Audit Log
- **Histórico completo** de todas operações
- **Filtros avançados** por data, ação, usuário, recurso
- **Metadata detalhada** de cada evento (antes/depois)
- **Timeline visual** com ordenação
- **Rastreabilidade completa** para compliance
- **Estatísticas** de uso do sistema
- **Página:** AuditLog

### 🔧 Remote Installer
- **Multi-connector:** SSH, WinRM, PSExec (fallback automático)
- **Instalação remota** de exporters (Node, Windows, Redis, MySQL, etc.)
- **Suporte systemd** para serviços Linux
- **Windows Service** registration automático
- **Logs em tempo real** via WebSocket
- **Pre-flight checks:** conectividade, espaço em disco, SO
- **Rollback automático** em caso de falha
- **Templates customizáveis** para cada exporter
- **Basic Auth** para segurança
- **Página:** Installer

### 🎛️ Customização de Interface
- **Seletor de colunas** com drag & drop
- **Persistência de preferências** no localStorage
- **Colunas redimensionáveis** com mouse
- **Filtros salvos** por página
- **Layout responsivo** (mobile, tablet, desktop)

### 🏢 Service Groups
- **Agrupamento lógico** de serviços
- **Hierarquia de grupos** para organização
- **Visualização por grupo** na interface
- **Página:** ServiceGroups

### 🖥️ Hosts Management
- **Lista de hosts** monitorados
- **Serviços por host** com drill-down
- **Health status** por host
- **Página:** Hosts

### ⚙️ Settings
- **Configuração de sites** (multi-site)
- **Naming patterns** para service IDs
- **Credenciais SSH** para servidores Prometheus
- **Blacklist de campos** para autocomplete
- **Página:** Settings

---

## 📱 Páginas da Interface (17 Páginas)

1. **Dashboard** - Métricas, gráficos, ações rápidas
2. **Services** - Lista completa de serviços Consul
3. **Exporters** - Gerenciamento de exporters (System/Database)
4. **Hosts** - Gerenciamento de hosts monitorados
5. **BlackboxTargets** - Alvos de probes de rede/web
6. **BlackboxGroups** - Organização de targets em grupos
7. **ServiceGroups** - Agrupamento lógico de serviços
8. **ServicePresets** - Templates reutilizáveis
9. **MonitoringTypes** - Configuração de tipos de monitoramento
10. **ReferenceValues** - Valores de referência compartilhados
11. **MetadataFields** - Configuração de campos dinâmicos
12. **KvBrowser** - Navegador visual do KV Store
13. **AuditLog** - Histórico de operações
14. **Installer** - Instalação remota de exporters
15. **PrometheusConfig** - Editor YAML multi-servidor
16. **Settings** - Configurações do sistema
17. **TestMonitoringTypes** - Debug de tipos de monitoramento

---

## 🧩 Componentes React (12 Componentes)

1. **AdvancedSearchPanel** - Construtor visual de queries
2. **ColumnSelector** - Drag & drop para seleção de colunas
3. **FormFieldRenderer** - Renderização dinâmica de campos de formulário
4. **ListPageLayout** - Layout padronizado para páginas de lista
5. **MetadataFilterBar** - Barra de filtros rápidos
6. **NodeSelector** - Seletor de nós Consul
7. **ReferenceValueInput** - Input com autocomplete de reference values
8. **ResizableTitle** - Colunas redimensionáveis em tabelas
9. **ServerSelector** - Seletor multi-servidor Prometheus
10. **ServiceNamePreview** - Preview de nomes de serviço
11. **SiteBadge** - Badge visual para identificar sites
12. **TagsInput** - Input de tags com autocomplete

---

## 🪝 Custom Hooks (6 Hooks)

1. **useConsulDelete** - Hook para deleção com confirmação
2. **useMetadataFields** - Context API para campos dinâmicos (cache global)
3. **useMonitoringType** - Detecção de tipo de monitoramento de serviços
4. **usePrometheusFields** - Extração de campos do Prometheus
5. **useReferenceValues** - Gerenciamento de valores de referência
6. **useServiceTags** - Auto-complete e gerenciamento de tags

---

## 🔌 API Reference

### Base URL
```
http://localhost:5000/api/v1
```

### Documentação Completa
📖 **[Ver documentação completa de endpoints](docs/api/endpoints-reference.md)** - 100+ endpoints documentados

### Principais Módulos da API

| Módulo | Endpoints | Descrição |
|--------|-----------|-----------|
| **Services** | 10 | CRUD + bulk + search de serviços Consul |
| **Monitoring Types** | 5 | Tipos de monitoramento (detecção dinâmica) |
| **Monitoring Types Dynamic** | 2 | Extração automática do Prometheus |
| **Metadata Fields** | 10 | Campos dinâmicos + sincronização SSH |
| **Reference Values** | 6 | Auto-cadastro de valores permitidos |
| **Blackbox Targets** | 6 | Gerenciamento de alvos de probes |
| **Blackbox Groups** | 4 | Organização de targets |
| **Service Presets** | 8 | Templates reutilizáveis |
| **Search** | 8 | Busca avançada com 12 operadores |
| **Prometheus Config** | 12 | Editor YAML remoto via SSH |
| **Dashboard** | 2 | Métricas agregadas com cache |
| **Health** | 2 | Status e conectividade |
| **Audit** | 3 | Logs de auditoria |
| **KV Store** | 4 | Acesso direto ao Consul KV |
| **Nodes** | 4 | Gerenciamento de nós |
| **Installer** | 8 | Instalação remota (SSH/WinRM/PSExec) |
| **Settings** | 5 | Configurações (sites, naming, etc) |
| **Service Tags** | 5 | Gerenciamento de tags |
| **Consul Insights** | 2 | Analytics e insights |
| **Optimized Endpoints** | 8 | Endpoints com cache e otimizações |

### Swagger UI Interativo
```
http://localhost:5000/docs
```

---

## 📚 Documentação

### Guias de Uso
- **[Quick Start](docs/guides/quick-start.md)** - Início rápido
- **[Prometheus Basic Auth](docs/guides/prometheus-basic-auth.md)** - Configurar autenticação
- **[Restart Guide](docs/guides/restart-guide.md)** - Como reiniciar serviços
- **[Reference Values](docs/guides/reference-values.md)** - Sistema de valores
- **[External Labels](docs/guides/external-labels.md)** - Uso correto de labels
- **[Migration Guide](docs/guides/migration.md)** - Migração de versões
- **[Git Workflow](docs/guides/git-workflow.md)** - Boas práticas Git

### Arquitetura
- **[Overview](docs/architecture/METADATA_FIELDS_ANALYSIS.md)** - Visão geral do sistema
- **[Monitoring Types](docs/architecture/monitoring-types.md)** - Sistema de tipos
- **[Multi-Site](docs/architecture/multi-site.md)** - Setup multi-servidor
- **[Dynamic Fields](docs/architecture/dynamic-fields.md)** - Campos dinâmicos
- **[Service ID Sanitization](docs/architecture/service-id-sanitization.md)** - Regras de IDs
- **[Reload Logic](docs/architecture/reload-logic.md)** - Lógica de recarregamento
- **[Prometheus Config Editor](docs/architecture/PROMETHEUS_CONFIG_PAGE_SUMMARY.md)** - Editor YAML
- **[Server Detection](docs/architecture/SERVER_DETECTION_INTEGRATION.md)** - Detecção automática

### API
- **[Endpoints Reference](docs/api/endpoints-reference.md)** - Todos os 100+ endpoints

### Planejamento
- **[Refactoring Architecture](docs/planning/refactoring-architecture.md)** - Arquitetura futura
- **[Refactoring Plan](docs/planning/refactoring-plan.md)** - Roadmap detalhado

### Performance
- **[Analysis Complete](docs/performance/analysis-complete.md)** - Análise de performance
- **[Context API Implementation](docs/performance/context-api-implementation.md)** - Implementação Context API
- **[Context API Checklist](docs/performance/context-api-checklist.md)** - Testes de performance

### Pesquisa
- **[Prometheus Architecture Research](docs/research/prometheus-architecture-research.md)** - Pesquisa sobre arquitetura

### Incidentes
- **[Jobs Perdidos](docs/incidents/jobs-perdidos.md)** - Lições aprendidas

### Histórico
- **[Phase 1](docs/history/phase1-implementation.md)** - KV Namespace e Dual Storage
- **[Phase 2](docs/history/phase2-implementation.md)** - Presets e Advanced Search
- **[Phase 3](docs/history/phase3-implementation.md)** - Frontend Modernization
- **[Prometheus Editor Phase 1](docs/history/prometheus-editor-phase1.md)** - Editor YAML inicial
- **[Installer Improvements](docs/history/installer-improvements.md)** - Melhorias do installer
- **[Layout Standardization](docs/history/layout-standardization.md)** - Padronização de layout

---

## 🗺️ Estrutura do Projeto

```
Skills-Eye/
│
├── 📁 backend/                       # API FastAPI + Business Logic
│   ├── api/                          # 100+ REST endpoints
│   │   ├── services.py               # Serviços Consul (CRUD)
│   │   ├── monitoring_types*.py      # Detecção dinâmica de tipos
│   │   ├── metadata_fields*.py       # Campos extraídos do Prometheus
│   │   ├── reference_values.py       # Auto-cadastro de valores
│   │   ├── blackbox.py               # Monitoring targets
│   │   ├── presets.py                # Templates de serviços
│   │   ├── search.py                 # 12 operadores de busca
│   │   ├── prometheus_config.py      # Editor YAML remoto (SSH)
│   │   ├── installer.py              # Multi-connector installers
│   │   └── ... (20+ módulos)
│   ├── core/                         # Business logic
│   │   ├── consul_manager.py         # Client async Consul
│   │   ├── yaml_config_service.py    # Editor YAML com SSH
│   │   ├── multi_config_manager.py   # Multi-servidor SSH
│   │   ├── advanced_search.py        # Search engine
│   │   └── installers/               # SSH/WinRM/PSExec
│   ├── config/                       # Configurações
│   │   └── metadata_fields.json      # Schema de campos dinâmicos
│   ├── app.py                        # FastAPI app
│   └── requirements.txt              # Dependências Python
│
├── 📁 frontend/                      # React 19 + TypeScript
│   ├── src/
│   │   ├── pages/                    # 17 páginas
│   │   │   ├── Dashboard.tsx         # Métricas + gráficos
│   │   │   ├── Services.tsx          # Lista de serviços
│   │   │   ├── Exporters.tsx         # Exporters por tipo
│   │   │   ├── BlackboxTargets.tsx   # Probes de rede/web
│   │   │   ├── PrometheusConfig.tsx  # Editor YAML multi-server
│   │   │   ├── MetadataFields.tsx    # Campos dinâmicos
│   │   │   ├── Installer.tsx         # Instalação remota
│   │   │   └── ... (10+ páginas)
│   │   ├── components/               # 12 componentes
│   │   │   ├── AdvancedSearchPanel   # Construtor de queries
│   │   │   ├── ColumnSelector        # Drag & drop colunas
│   │   │   ├── ListPageLayout        # Layout padronizado
│   │   │   └── ... (9+ componentes)
│   │   ├── contexts/                 # Context API
│   │   │   └── MetadataFieldsContext # Cache global de campos
│   │   ├── hooks/                    # 6 custom hooks
│   │   ├── services/api.ts           # Client HTTP
│   │   └── types/monitoring.ts       # TypeScript interfaces
│   ├── package.json
│   └── vite.config.ts
│
├── 📁 docs/                          # Documentação Organizada
│   ├── features/                     # 📄 15 documentos de funcionalidades
│   │   ├── NAMING_SYSTEM_COMPLETE.md       # Sistema de nomenclatura (100+ pgs)
│   │   ├── ADVANCED_SEARCH_IMPLEMENTATION.md
│   │   ├── BLACKBOX_TARGETS_COMPLETE.md
│   │   ├── METADATA_FIELDS_COMPLETE.md
│   │   ├── MONITORING_TYPES_COMPLETE.md
│   │   ├── PROMETHEUS_CONFIG_EDITOR_COMPLETE.md
│   │   └── ... (9+ docs)
│   ├── developer/                    # 📄 Para desenvolvedores
│   │   ├── corrections/              # Correções aplicadas
│   │   │   ├── CHANGELOG-SESSION.md
│   │   │   ├── CORRECOES_2025-11-11.md
│   │   │   └── ... (10 docs)
│   │   ├── architecture/             # Análises técnicas
│   │   │   ├── METADATA_FIELDS_ANALYSIS.md
│   │   │   ├── SERVER_DETECTION_INTEGRATION.md
│   │   │   └── ... (8 docs)
│   │   └── troubleshooting/          # (futuro)
│   ├── guides/                       # 📄 Guias de uso
│   ├── planning/                     # 📄 Roadmap e refatoração
│   ├── performance/                  # 📄 Análises de performance
│   ├── obsolete/                     # 📄 Documentos antigos
│   └── user/                         # 📄 Documentação para usuários finais
│
├── 📁 Tests/                         # 34 Testes Organizados
│   ├── naming/                       # 3 testes de nomenclatura
│   ├── metadata/                     # 12 testes de campos dinâmicos
│   ├── performance/                  # 5 testes de performance
│   ├── integration/                  # 14 testes de integração
│   └── README.md                     # Documentação completa de testes
│
├── 📁 scripts/                       # Scripts de Automação
│   ├── deployment/                   # 🔧 15 scripts de deploy/restart
│   │   ├── restart-all.sh
│   │   ├── restart-backend.sh
│   │   ├── start-app.sh
│   │   └── ... (12+ scripts)
│   ├── migration/                    # 🔧 5 scripts de migração
│   │   ├── migrate_consul_kv.py
│   │   ├── migrate_namespace.py
│   │   ├── migrate_naming_to_kv.py
│   │   └── validate_migration.py
│   ├── development/                  # 🔧 7 scripts de análise
│   │   ├── analyze_profile.py
│   │   ├── analyze_react_complexity.py
│   │   ├── compare_pages_performance.py
│   │   └── ... (4+ scripts)
│   └── benchmarks/                   # 🔧 3 scripts de benchmark
│       ├── benchmark-api-before.bat
│       └── run-benchmark-api.ps1
│
├── 📁 data/                          # Dados de Teste e Baselines
│   ├── baselines/                    # JSON de baseline
│   │   ├── BASELINE_ENDPOINTS.json
│   │   ├── BASELINE_PRE_MIGRATION.json
│   │   └── TESTE_POS_FASE1_API.json
│   ├── fixtures/                     # Fixtures de teste
│   │   ├── test_3servers.json
│   │   ├── test_exporters_fields.json
│   │   └── ... (4 fixtures)
│   └── temp/                         # Temporários (gitignored)
│       ├── temp_final.json
│       └── temp_response*.json
│
├── 📁 logs/                          # Logs (gitignored)
│   ├── backend.log
│   ├── TESTE_POS_FASE1.log
│   └── migration_report.txt
│
├── 📁 assets/                        # Assets do Projeto
│   └── screenshots/
│       ├── screenshot_blackboxtargets.png
│       └── screenshot_services.png
│
├── 📁 tools/                         # Ferramentas auxiliares (futuro)
│
├── 📁 TenSunS/                       # Legado (embedded repo)
├── 📁 obsolete/                      # Código obsoleto
│
├── 📄 README.md                      # Este arquivo - Documentação principal
├── 📄 CLAUDE.md                      # Instruções para IA (desenvolvedor)
├── 📄 COMANDOS_RAPIDOS.md            # Quick reference de comandos
├── 📄 DOCUMENTATION_INDEX.md         # Índice completo de documentação
├── 📄 .gitignore                     # Git ignore rules
└── 📄 _ul                            # Arquivo de controle
```

### 📂 Organização por Tipo de Conteúdo

| Pasta | Conteúdo | Quem Usa | Git |
|-------|----------|----------|-----|
| **backend/** | API + business logic | Desenvolvedores | ✅ Commitado |
| **frontend/** | Interface React | Desenvolvedores | ✅ Commitado |
| **docs/** | Documentação organizada | Todos | ✅ Commitado |
| **Tests/** | Testes automatizados | Desenvolvedores | ✅ Commitado |
| **scripts/** | Automação e deploy | DevOps | ✅ Commitado |
| **data/baselines/** | Dados de baseline | QA | ✅ Commitado |
| **data/fixtures/** | Fixtures de teste | QA | ✅ Commitado |
| **data/temp/** | Temporários | Sistema | ❌ Ignorado |
| **logs/** | Arquivos de log | Sistema | ❌ Ignorado |
| **assets/** | Screenshots, imagens | Documentação | ✅ Commitado |
| **tools/** | Ferramentas auxiliares | Desenvolvedores | ✅ Commitado |

### 🎯 Navegação Rápida

**Para Usuários:**
- 📖 [Início Rápido](docs/guides/quick-start.md)
- 📖 [Guias de Uso](docs/guides/)
- 📖 [FAQ](docs/user/)

**Para Desenvolvedores:**
- 🔧 [Arquitetura](docs/developer/architecture/)
- 🔧 [Correções Aplicadas](docs/developer/corrections/)
- 🔧 [Roadmap](docs/planning/)
- 🔧 [Testes](Tests/README.md)
- 🔧 [Scripts](scripts/)

**Documentação Técnica:**
- 📚 [Features Completas](docs/features/)
- 📚 [API Reference](docs/api/endpoints-reference.md)
- 📚 [Performance Analysis](docs/performance/)

### 🔍 Como Encontrar Algo

**Buscar funcionalidade específica:**
```bash
# Ver índice completo
cat DOCUMENTATION_INDEX.md

# Buscar por palavra-chave
grep -r "monitoring types" docs/
```

**Entender uma feature:**
```
docs/features/ → Documentação completa de cada funcionalidade
```

**Resolver problema:**
```
docs/developer/corrections/ → Correções já aplicadas
docs/developer/troubleshooting/ → Soluções comuns (futuro)
```

**Analisar performance:**
```
docs/performance/ → Análises e otimizações
Tests/performance/ → Testes de performance
```

**Executar testes:**
```
Tests/ → Todos os testes com README.md explicativo
```

---

## 🚀 Roadmap

### Implementado ✅
- [x] Sistema de monitoring types DINÂMICO
- [x] Multi-site Prometheus com replicação
- [x] Campos dinâmicos extraídos do Prometheus
- [x] Reference values com auto-cadastro
- [x] Context API para performance
- [x] Multi-connector installer (SSH/WinRM/PSExec)
- [x] Editor YAML remoto com preservação de comentários
- [x] Cache inteligente multi-layer
- [x] Operações paralelas em múltiplos servidores

### Em Planejamento 📋
- [ ] Refatoração arquitetural (Clean Architecture)
- [ ] Testes automatizados (unit + integration)
- [ ] Docker Compose para deploy fácil
- [ ] Suporte a Kubernetes service discovery
- [ ] Dashboard customizável com widgets
- [ ] Alerting rules editor
- [ ] Grafana dashboard generator
- [ ] CLI tool para automação
- [ ] Backup/restore automático de configurações

---

## 🤝 Contribuindo

Contribuições são bem-vindas! Por favor:

1. Fork o projeto
2. Crie uma branch para sua feature (`git checkout -b feature/MinhaFeature`)
3. Commit suas mudanças (`git commit -m 'feat: Adicionar MinhaFeature'`)
4. Push para a branch (`git push origin feature/MinhaFeature`)
5. Abra um Pull Request

**Guia de Contribuição:** [docs/development/contributing.md](#) (em breve)

---

## 📄 Licença

Este projeto está sob a licença MIT. Veja o arquivo [LICENSE](LICENSE) para mais detalhes.

---

## 👥 Autores

- **Adriano Fante** - *Desenvolvimento inicial* - Skills IT

---

## 🙏 Agradecimentos

- HashiCorp pela incrível ferramenta Consul
- Prometheus community
- Ant Design team
- FastAPI framework
- TenSunS project (inspiração inicial)

---

## 📞 Suporte

- 📧 Email: repositories@skillsit.com.br
- 🐛 Issues: https://github.com/DevSkillsIT/Skills-Eye/issues
- 📚 Docs: https://github.com/DevSkillsIT/Skills-Eye/tree/main/docs

---

<div align="center">

**Feito com ❤️ por Skills IT**

*Sistema DINÂMICO - Adapta-se automaticamente ao seu Prometheus!*

</div>
