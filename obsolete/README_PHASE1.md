# Consul Manager - Enhanced Web Application

> **Phase 1 Complete** - Standardized KV namespaces, dual storage, group management, audit logging, and bulk operations

A modern web application for managing HashiCorp Consul services with enhanced features for monitoring blackbox targets via Prometheus and Blackbox Exporter.

---

## 🎯 Features (Phase 1)

### Core Features
- ✅ **Consul Service Management** - Full CRUD operations for services
- ✅ **Blackbox Target Management** - Monitor websites, APIs, and network endpoints
- ✅ **Dual Storage System** - Services + KV for advanced features
- ✅ **Group Management** - Organize targets into logical groups
- ✅ **Bulk Operations** - Enable/disable multiple targets at once
- ✅ **Audit Logging** - Complete audit trail in Consul KV
- ✅ **UI Preferences** - User-specific settings persistence
- ✅ **Import/Export** - CSV/XLSX batch import with validation
- ✅ **Config Generation** - Auto-generate Prometheus/Blackbox configs
- ✅ **Remote Installer** - Deploy exporters to Linux/Windows hosts

### Advanced Features
- 📊 **Multi-dimensional Filtering** - Filter by company/project/env/module
- 🏷️ **Custom Labels** - Add metadata beyond standard fields
- ⏱️ **Configurable Intervals** - Per-target scrape intervals and timeouts
- 🔄 **Real-time Sync** - Changes reflected immediately in Prometheus
- 🔍 **Advanced Search** - Search across all metadata fields
- 📝 **Rich Metadata** - Notes, descriptions, and custom properties
- 🔐 **Namespace Security** - All app data in isolated KV namespace

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Frontend (React)                        │
│              Ant Design Pro + TypeScript                     │
└────────────────────┬────────────────────────────────────────┘
                     │ HTTP/WebSocket
┌────────────────────┴────────────────────────────────────────┐
│                   Backend (FastAPI)                          │
│  ┌────────────┐  ┌──────────────┐  ┌──────────────┐        │
│  │  Services  │  │   Blackbox   │  │      KV      │        │
│  │  Manager   │  │   Manager    │  │   Manager    │        │
│  └─────┬──────┘  └──────┬───────┘  └──────┬───────┘        │
└────────┼─────────────────┼──────────────────┼───────────────┘
         │                 │                  │
┌────────┴─────────────────┴──────────────────┴───────────────┐
│                    Consul (Service + KV)                     │
│  ┌──────────────┐              ┌───────────────┐            │
│  │   Services   │◄─────────────┤  KV Store     │            │
│  │  (Discovery) │  consul_sd   │  skills/eye/*  │            │
│  └──────┬───────┘              └───────────────┘            │
└─────────┼──────────────────────────────────────────────────┘
          │ Service Discovery
┌─────────┴──────────────────────────────────────────────────┐
│                      Prometheus                              │
│  Scrapes targets discovered via consul_sd_configs           │
└──────────────────────────────────────────────────────────────┘
```

---

## 📋 Requirements

### Backend
- Python 3.12+
- FastAPI
- httpx (async HTTP client)
- pydantic (data validation)
- pandas + openpyxl (optional, for XLSX import)

### Infrastructure
- HashiCorp Consul 1.14+
- Prometheus 2.40+ (with consul_sd_configs)
- Blackbox Exporter 0.23+
- Nginx (reverse proxy)

### Frontend (Phase 3)
- Node.js 18+
- React 18
- TypeScript 4.9+
- Ant Design Pro 6+

---

## 🚀 Quick Start

### 1. Clone Repository

```bash
git clone <repository-url>
cd Skills-Eye
```

### 2. Configure Environment

```bash
cd backend
cp .env.example .env
```

Edit `.env`:

```env
# Consul Configuration
CONSUL_SERVER=172.16.1.26
CONSUL_PORT=8500
CONSUL_TOKEN=your-consul-token-here

# Application Settings
KV_NAMESPACE=skills/eye
ENABLE_AUDIT_LOG=true
ENABLE_KV_STORAGE=true

# Known Nodes (optional)
KNOWN_NODES={"Palmas": "172.16.1.26", "Rio": "172.16.1.27"}
```

### 3. Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 4. Start Backend

```bash
python app.py
```

The API will be available at:
- **API**: http://localhost:5000
- **Swagger Docs**: http://localhost:5000/docs
- **ReDoc**: http://localhost:5000/redoc

### 5. Test Installation

```bash
python test_phase1.py
```

---

## 📚 API Documentation

### Complete Endpoint Reference

#### **Services** (`/api/v1/services`)
```
GET     /                      # List all services
GET     /{id}                  # Get service details
POST    /                      # Register service
PUT     /{id}                  # Update service
DELETE  /{id}                  # Deregister service
```

#### **Blackbox** (`/api/v1/blackbox`)
```
GET     /                      # List targets (with filters)
GET     /summary               # Aggregated summary
POST    /                      # Create target (basic)
POST    /enhanced              # Create target (with groups/labels)
PUT     /                      # Update target
DELETE  /                      # Delete target
POST    /import                # Import CSV/XLSX
GET     /config/rules          # Get Prometheus alert rules
GET     /config/blackbox       # Get blackbox.yml config
GET     /config/prometheus     # Get Prometheus job config

# Groups
POST    /groups                # Create group
GET     /groups                # List groups
GET     /groups/{id}           # Get group + members

# Bulk Operations
POST    /bulk/enable-disable   # Enable/disable multiple targets
```

#### **KV Store** (`/api/v1/kv`)
```
GET     /get                   # Get single key
POST    /put                   # Store value
DELETE  /delete                # Delete key
GET     /list                  # List keys
GET     /tree                  # Get tree

# Audit
GET     /audit/events          # Query audit log

# Settings
GET     /settings/ui           # Get UI settings
POST    /settings/ui           # Save UI settings

# Import Tracking
GET     /imports/last          # Get last import

# Migration
POST    /migrate               # Migrate old namespace
```

#### **Nodes** (`/api/v1/nodes`)
```
GET     /                      # List cluster nodes
GET     /{addr}/services       # Get node services
```

#### **Health** (`/api/v1/health`)
```
GET     /status                # System status
GET     /connectivity          # Test connectivity
```

#### **Installer** (`/api/v1/installer`)
```
POST    /check                 # Pre-installation checks
POST    /run                   # Install exporter
WS      /ws/installer/{id}     # Real-time logs
```

---

## 💡 Usage Examples

### Create a Blackbox Target with Group

```bash
curl -X POST "http://localhost:5000/api/v1/blackbox/enhanced?user=admin" \
  -H "Content-Type: application/json" \
  -d '{
    "module": "http_2xx",
    "company": "Ramada",
    "project": "web",
    "env": "prod",
    "name": "HomePage",
    "instance": "https://www.ramada.com.br",
    "group": "ramada-sites",
    "labels": {"region": "brazil", "priority": "high"},
    "interval": "15s",
    "timeout": "5s",
    "enabled": true,
    "notes": "Main website homepage"
  }'
```

### Create a Target Group

```bash
curl -X POST "http://localhost:5000/api/v1/blackbox/groups?user=admin" \
  -H "Content-Type: application/json" \
  -d '{
    "id": "ramada-sites",
    "name": "Ramada Websites",
    "filters": {"company": "Ramada", "project": "web"},
    "labels": {"monitored_by": "ops-team"},
    "description": "All Ramada web properties"
  }'
```

### Bulk Disable Group

```bash
curl -X POST "http://localhost:5000/api/v1/blackbox/bulk/enable-disable?user=admin" \
  -H "Content-Type: application/json" \
  -d '{
    "group_id": "ramada-sites",
    "enabled": false
  }'
```

### Query Audit Log

```bash
curl "http://localhost:5000/api/v1/kv/audit/events?start_date=2025-01-01&resource_type=blackbox_target&action=CREATE"
```

### Import Targets from CSV

```bash
# CSV format: module,company,project,env,name,instance
curl -X POST "http://localhost:5000/api/v1/blackbox/import" \
  -F "file=@targets.csv"
```

---

## 🗂️ KV Namespace Structure

```
skills/eye/
├── blackbox/
│   ├── targets/
│   │   ├── http_2xx_Ramada_web_prod@HomePage.json
│   │   ├── icmp_Skills_network_prod@Gateway.json
│   │   └── ...
│   ├── groups/
│   │   ├── ramada-sites.json
│   │   ├── production-apis.json
│   │   └── ...
│   └── modules.json
├── services/
│   └── presets/
│       ├── node-exporter-linux.json
│       ├── windows-exporter.json
│       └── ...
├── settings/
│   ├── ui.json (global)
│   └── users/
│       ├── admin.json
│       ├── johndoe.json
│       └── ...
├── imports/
│   └── last.json
└── audit/
    └── 2025/
        └── 01/
            └── 20/
                ├── 103000-blackbox_target-site-ramada.json
                └── ...
```

---

## 🔄 Prometheus Integration

### Consul Service Discovery Configuration

Add to your `prometheus.yml`:

```yaml
scrape_configs:
  - job_name: 'blackbox_exporter'
    scrape_interval: 15s
    scrape_timeout: 5s
    metrics_path: /probe
    consul_sd_configs:
      - server: '172.16.1.26:8500'
        token: '${CONSUL_TOKEN}'
        services: ['blackbox_exporter']
    relabel_configs:
      # Target instance
      - source_labels: [__meta_consul_service_metadata_instance]
        target_label: __param_target

      # Blackbox module
      - source_labels: [__meta_consul_service_metadata_module]
        target_label: __param_module
      - source_labels: [__meta_consul_service_metadata_module]
        target_label: module

      # Business metadata
      - source_labels: [__meta_consul_service_metadata_company]
        target_label: company
      - source_labels: [__meta_consul_service_metadata_project]
        target_label: project
      - source_labels: [__meta_consul_service_metadata_env]
        target_label: env
      - source_labels: [__meta_consul_service_metadata_name]
        target_label: name

      # Set instance label
      - source_labels: [__param_target]
        target_label: instance

      # Point to blackbox exporter
      - target_label: __address__
        replacement: 127.0.0.1:9115
```

---

## 🧪 Testing

### Run Test Suite

```bash
cd backend
python test_phase1.py
```

Tests include:
- KV Manager operations
- Namespace validation
- Blackbox group management
- Enhanced target creation
- Bulk operations
- Audit logging
- UI settings persistence

### Manual API Testing

Use the Swagger UI at http://localhost:5000/docs to test endpoints interactively.

---

## 📖 Documentation

- **[IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md)** - Complete Phase 1 implementation details
- **[MIGRATION_GUIDE.md](MIGRATION_GUIDE.md)** - Upgrade guide from TenSunS or older versions
- **[API Reference](http://localhost:5000/docs)** - Interactive Swagger documentation
- **[Blueprint](docs/BLUEPRINT.md)** - Original project blueprint (when available)

---

## 🛠️ Development

### Project Structure

```
Skills-Eye/
├── backend/
│   ├── api/
│   │   ├── blackbox.py          # Blackbox endpoints
│   │   ├── kv.py                # KV store endpoints
│   │   ├── services.py          # Service endpoints
│   │   ├── nodes.py             # Node endpoints
│   │   ├── health.py            # Health endpoints
│   │   ├── installer.py         # Installer endpoints
│   │   └── models.py            # Pydantic models
│   ├── core/
│   │   ├── consul_manager.py    # Consul API wrapper
│   │   ├── kv_manager.py        # KV namespace manager
│   │   ├── blackbox_manager.py  # Blackbox logic
│   │   ├── config.py            # Configuration
│   │   └── websocket_manager.py # WebSocket handler
│   ├── app.py                   # FastAPI application
│   ├── test_phase1.py           # Test suite
│   └── requirements.txt
├── frontend/                    # React frontend (Phase 3)
├── docs/                        # Documentation
├── IMPLEMENTATION_SUMMARY.md
├── MIGRATION_GUIDE.md
└── README_PHASE1.md (this file)
```

### Adding New Features

1. **Backend API**: Add endpoints in `backend/api/`
2. **Business Logic**: Implement in `backend/core/`
3. **Models**: Define schemas in `backend/api/models.py`
4. **Tests**: Add tests to `test_phase1.py`
5. **Documentation**: Update relevant .md files

---

## 🔜 Roadmap

### Phase 2: Service Presets & Advanced Features
- [ ] Service registration presets
- [ ] Advanced metadata search with operators
- [ ] Enhanced Prometheus config generation
- [ ] Batch service operations
- [ ] Service templates

### Phase 3: Frontend Development
- [ ] Update API client
- [ ] BlackboxGroups UI page
- [ ] KV Browser component
- [ ] AuditLog viewer
- [ ] Bulk operations interface
- [ ] Enhanced filters and search

### Phase 4: Installer Enhancements
- [ ] Comprehensive pre-checks
- [ ] Windows OpenSSH detection
- [ ] PowerShell script fallback
- [ ] Batch installation support
- [ ] Rollback mechanisms

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📝 License

[Your License Here]

---

## 🙏 Acknowledgments

- **TenSunS Project** - Inspiration for KV patterns and config generation
- **HashiCorp Consul** - Service mesh and KV store
- **Prometheus** - Metrics and monitoring
- **Ant Design Pro** - UI framework
- **FastAPI** - Modern Python web framework

---

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/your-repo/issues)
- **Documentation**: See `docs/` directory
- **API Docs**: http://localhost:5000/docs

---

## ✨ Status

✅ **Phase 1 Complete** - January 2025

**What's Working:**
- KV namespace management
- Dual storage for blackbox targets
- Group management
- Bulk operations
- Audit logging
- UI settings
- Import/Export
- Prometheus integration
- Full REST API

**Next:** Phase 2 - Service Presets (Q1 2025)

---

**Built with ❤️ for better Consul management**
