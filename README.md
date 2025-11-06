# Skills Eye Web Application

<div align="center">

![Version](https://img.shields.io/badge/version-2.3.0-blue.svg)
![Status](https://img.shields.io/badge/status-production--ready-success.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)

**Sistema completo de gerenciamento do Consul com interface web moderna**

[Instalação](#-instalação) • [Funcionalidades](#-funcionalidades) • [Documentação](#-documentação) • [Screenshots](#-screenshots)

</div>

---

## 📋 Sobre o Projeto

O **Skills Eye** é uma aplicação web completa para gerenciar serviços do HashiCorp Consul, com foco especial em:

- Gerenciamento de **Blackbox Exporter** targets
- Integração com **Prometheus** via service discovery
- Instalação remota de exporters (Node, Windows, Redis, etc.)
- Templates reutilizáveis para registro de serviços
- Busca avançada com múltiplos operadores
- Auditoria completa de operações
- Interface moderna e responsiva 100% em PT-BR

### Stack Tecnológico

**Backend:**
- Python 3.12+
- FastAPI 0.115+
- httpx (async HTTP)
- Consul HTTP API

**Frontend:**
- React 19+
- TypeScript
- Ant Design Pro
- @ant-design/charts (G2Plot)
- @dnd-kit (drag & drop)

---

## 🚀 Instalação

### Pré-requisitos

- Python 3.12 ou superior
- Node.js 18+ e npm
- Consul rodando (local ou remoto)
- Git

### 1. Clone o Repositório

```bash
git clone https://github.com/seu-usuario/consul-manager-web.git
cd consul-manager-web
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
# CONSUL_HOST=localhost
# CONSUL_PORT=8500
# CONSUL_TOKEN=your-token-here  # se ACL habilitado
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

**Terminal 1 - Backend:**
```bash
cd backend
python app.py
# Backend rodando em http://localhost:5000
# Swagger UI em http://localhost:5000/docs
```

**Terminal 2 - Frontend:**
```bash
cd frontend
npm run dev
# Frontend rodando em http://localhost:8080
```

**Acesse:** http://localhost:8080

---

## ✨ Funcionalidades

### 🎯 Dashboard Moderno
- Métricas visuais em tempo real
- Gráficos de distribuição (ambientes, datacenters)
- Health status do cluster
- Timeline de atividades recentes
- Auto-refresh configurável
- Ações rápidas para tarefas comuns

### 🎨 Service Presets
- Templates reutilizáveis para serviços
- Variáveis customizáveis `${var}` e `${var:default}`
- Preview antes do registro
- Bulk registration (registrar múltiplos serviços)
- Presets built-in para exporters populares:
  - Node Exporter (Linux)
  - Windows Exporter
  - Blackbox Exporter (ICMP)
  - Redis Exporter

### 📊 Blackbox Targets
- CRUD completo de alvos de monitoramento
- Suporte a múltiplos módulos (HTTP, ICMP, TCP, SSH)
- Organização em grupos lógicos
- Importação/exportação CSV
- Geração automática de configs Prometheus
- Filtros avançados por metadata

### 🗂️ Blackbox Groups
- Organizar targets por projeto/cliente/ambiente
- Tags e metadata customizável
- Visualização de targets por grupo
- Gestão centralizada

### 🔍 Busca Avançada
- 12 operadores de comparação
- Múltiplas condições (AND/OR)
- Busca em campos nested (Meta.company, Meta.env)
- Preview visual das condições
- Integração com todas as tabelas

### 💾 KV Store Browser
- Navegação visual em árvore
- Editor JSON integrado
- Namespace isolado `skills/cm/`
- Metadados automáticos (created_at, updated_by, version)
- Breadcrumb navigation

### 📜 Audit Log
- Histórico completo de operações
- Filtros por data, ação, recurso
- Metadata detalhada de cada evento
- Timeline visual
- Rastreabilidade completa

### 🔧 Remote Installer
- Instalação SSH remota de exporters
- Suporte a systemd
- Logs em tempo real via WebSocket
- Templates para múltiplos exporters

### 🎛️ Customização de Interface
- Seletor de colunas com drag & drop
- Persistência de preferências
- Modo claro/escuro
- Layout responsivo (mobile, tablet, desktop)

---

## 📚 Documentação

### Guias de Implementação

- **[IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md)** - Phase 1: KV Namespace e Dual Storage
- **[PHASE2_SUMMARY.md](PHASE2_SUMMARY.md)** - Phase 2: Presets e Advanced Search
- **[PHASE3_SUMMARY.md](PHASE3_SUMMARY.md)** - Phase 3: Frontend Modernization
- **[MIGRATION_GUIDE.md](MIGRATION_GUIDE.md)** - Guia de migração de dados

### API Documentation

Acesse a documentação interativa (Swagger UI):

```
http://localhost:5000/docs
```

**Principais Endpoints:**

```
# Dashboard
GET /api/v1/services
GET /api/v1/health/status
GET /api/v1/search/stats

# Service Presets
GET    /api/v1/presets
POST   /api/v1/presets
GET    /api/v1/presets/{id}
PUT    /api/v1/presets/{id}
DELETE /api/v1/presets/{id}
POST   /api/v1/presets/register
POST   /api/v1/presets/preview

# Blackbox Groups
GET    /api/v1/blackbox/groups
POST   /api/v1/blackbox/groups
GET    /api/v1/blackbox/groups/{id}
PUT    /api/v1/blackbox/groups/{id}
DELETE /api/v1/blackbox/groups/{id}

# KV Store
GET    /api/v1/kv/get?key=skills/cm/...
PUT    /api/v1/kv/put
DELETE /api/v1/kv/delete
GET    /api/v1/kv/tree?prefix=skills/cm

# Audit Log
GET    /api/v1/kv/audit/events

# Advanced Search
POST   /api/v1/search/advanced
POST   /api/v1/search/text
GET    /api/v1/search/filters
GET    /api/v1/search/blackbox
```

---

## 📸 Screenshots

### Dashboard
![Dashboard](docs/screenshots/dashboard.png)
*Dashboard moderno com métricas, gráficos e atividades recentes*

### Service Presets
![Presets](docs/screenshots/presets.png)
*Gerenciamento de templates de serviços com preview*

### Blackbox Groups
![Groups](docs/screenshots/groups.png)
*Organização de alvos em grupos lógicos*

### KV Browser
![KV Browser](docs/screenshots/kv-browser.png)
*Navegador visual do KV store com editor JSON*

### Audit Log
![Audit Log](docs/screenshots/audit-log.png)
*Histórico completo de operações com filtros*

---

## 🗺️ Estrutura do Projeto

```
consul-manager-web/
├── backend/
│   ├── api/
│   │   ├── services.py          # Endpoints de serviços
│   │   ├── blackbox.py          # Blackbox targets
│   │   ├── presets.py           # Service presets
│   │   ├── search.py            # Advanced search
│   │   ├── kv.py                # KV store
│   │   ├── nodes.py             # Nodes do cluster
│   │   ├── health.py            # Health checks
│   │   └── installer.py         # Remote installer
│   ├── core/
│   │   ├── consul_manager.py    # Client Consul
│   │   ├── blackbox_manager.py  # Blackbox logic
│   │   ├── service_preset_manager.py  # Presets logic
│   │   ├── advanced_search.py   # Search engine
│   │   ├── kv_manager.py        # KV operations
│   │   ├── remote_installer.py  # SSH installer
│   │   └── config.py            # Configurações
│   ├── app.py                   # FastAPI app
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── pages/
│   │   │   ├── Dashboard.tsx
│   │   │   ├── Services.tsx
│   │   │   ├── BlackboxTargets.tsx
│   │   │   ├── ServicePresets.tsx
│   │   │   ├── BlackboxGroups.tsx
│   │   │   ├── KVBrowser.tsx
│   │   │   ├── AuditLog.tsx
│   │   │   └── Installer.tsx
│   │   ├── components/
│   │   │   ├── AdvancedSearchPanel.tsx
│   │   │   ├── ColumnSelector.tsx
│   │   │   └── MetadataFilterBar.tsx
│   │   ├── services/
│   │   │   └── api.ts           # API client
│   │   └── App.tsx
│   ├── package.json
│   └── vite.config.ts
├── IMPLEMENTATION_SUMMARY.md    # Docs Phase 1
├── PHASE2_SUMMARY.md            # Docs Phase 2
├── PHASE3_SUMMARY.md            # Docs Phase 3
├── MIGRATION_GUIDE.md
└── README.md
```

---

## 🔧 Configuração Avançada

### Variáveis de Ambiente (Backend)

```bash
# .env
CONSUL_HOST=localhost
CONSUL_PORT=8500
CONSUL_SCHEME=http
CONSUL_TOKEN=                    # Opcional: se ACL habilitado
MAIN_SERVER=localhost            # IP do servidor principal Consul
ENABLE_KV_STORAGE=true           # Dual storage (Services + KV)
```

### Configuração do Consul

**Habilitar ACL (opcional):**

```hcl
# consul.hcl
acl {
  enabled = true
  default_policy = "deny"
  enable_token_persistence = true
}
```

**Criar token para o Skills Eye:**

```bash
consul acl policy create \
  -name consul-manager \
  -rules @consul-manager-policy.hcl

consul acl token create \
  -description "Skills Eye Token" \
  -policy-name consul-manager
```

**Política recomendada (consul-manager-policy.hcl):**

```hcl
service_prefix "" {
  policy = "write"
}

node_prefix "" {
  policy = "read"
}

key_prefix "skills/cm/" {
  policy = "write"
}

operator = "read"
```

---

## 🧪 Testes

### Backend

```bash
cd backend

# Testar Phase 1 (KV e Dual Storage)
python test_phase1.py

# Testar Phase 2 (Presets e Search)
python test_phase2.py

# Testes unitários (se implementados)
pytest tests/
```

### Frontend

```bash
cd frontend

# Build de produção
npm run build

# Preview do build
npm run preview

# Linting
npm run lint
```

---

## 🚀 Deploy em Produção

### Backend (Systemd)

**1. Criar arquivo de serviço:**

```bash
sudo nano /etc/systemd/system/consul-manager.service
```

```ini
[Unit]
Description=Skills Eye API
After=network.target consul.service

[Service]
Type=simple
User=consul-manager
WorkingDirectory=/opt/consul-manager/backend
Environment="PATH=/opt/consul-manager/backend/venv/bin"
ExecStart=/opt/consul-manager/backend/venv/bin/python app.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**2. Ativar e iniciar:**

```bash
sudo systemctl daemon-reload
sudo systemctl enable consul-manager
sudo systemctl start consul-manager
```

### Frontend (Nginx)

**1. Build:**

```bash
cd frontend
npm run build
# Gera dist/
```

**2. Configurar Nginx:**

```nginx
server {
    listen 80;
    server_name consul-manager.example.com;

    root /opt/consul-manager/frontend/dist;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    location /api/ {
        proxy_pass http://localhost:5000/api/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }
}
```

**3. Reiniciar Nginx:**

```bash
sudo nginx -t
sudo systemctl reload nginx
```

---

## 🤝 Contribuindo

Contribuições são bem-vindas! Para contribuir:

1. Fork o projeto
2. Crie uma branch para sua feature (`git checkout -b feature/NovaFuncionalidade`)
3. Commit suas mudanças (`git commit -m 'Adiciona nova funcionalidade'`)
4. Push para a branch (`git push origin feature/NovaFuncionalidade`)
5. Abra um Pull Request

---

## 📄 Licença

Este projeto está sob a licença MIT. Veja o arquivo [LICENSE](LICENSE) para mais detalhes.

---

## 👨‍💻 Autores

- **Desenvolvedor Principal** - Implementação completa das 3 fases
- **Claude (Anthropic)** - Assistência no desenvolvimento

---

## 🙏 Agradecimentos

- [HashiCorp Consul](https://www.consul.io/) - Service mesh e service discovery
- [Prometheus](https://prometheus.io/) - Monitoramento e alertas
- [Blackbox Exporter](https://github.com/prometheus/blackbox_exporter) - Probing
- [Ant Design](https://ant.design/) - UI components
- [FastAPI](https://fastapi.tiangolo.com/) - Framework backend
- [React](https://react.dev/) - Frontend framework

---

## 📞 Suporte

Para questões e suporte:

- 📧 Email: suporte@example.com
- 🐛 Issues: [GitHub Issues](https://github.com/seu-usuario/consul-manager-web/issues)
- 📖 Docs: Ver arquivos `*_SUMMARY.md`

---

## 🗓️ Roadmap

- [x] **Phase 1:** KV Namespace + Dual Storage + Audit Log
- [x] **Phase 2:** Service Presets + Advanced Search
- [x] **Phase 3:** Frontend Modernization + UI Completa
- [ ] **Phase 4 (Futuro):** Notificações real-time, RBAC, Dashboards customizáveis

---

<div align="center">

**Desenvolvido com ❤️ usando React, TypeScript, Ant Design Pro e FastAPI**

⭐ Se este projeto foi útil, considere dar uma estrela!

</div>
