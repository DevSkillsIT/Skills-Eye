# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Skills Eye** is a comprehensive web application for managing HashiCorp Consul services, with specialized focus on Prometheus monitoring infrastructure. It transforms a 2980+ line CLI Python script into a modern web UI for managing Blackbox Exporter targets, service discovery, and remote exporter installation.

**Primary User:** Non-developer infrastructure analyst with 25 years experience. Explanations should be clear and interfaces intuitive.

**Production Environment:**
- Main Server: 172.16.1.26 (glpi-grafana-prometheus.skillsit.com.br)
- Consul Token: `8382a112-81e0-cd6d-2b92-8565925a0675`
- Monitoring Stack: Consul (8500), Prometheus (9090), Grafana (3000), Blackbox Exporter (9115), AlertManager (9093)

**Note:** Additional AI assistant guidance available in [.github/copilot-instructions.md](.github/copilot-instructions.md)

## Architecture

### Backend (Python 3.12 + FastAPI)

**Core Components:**

1. **ConsulManager** (`backend/core/consul_manager.py`)
   - Async HTTP client for Consul API
   - Service registration, deregistration, health checks
   - Retry logic with exponential backoff
   - Service ID sanitization (removes invalid chars, validates slashes)

2. **Dual Storage Pattern**
   - **Consul Services**: Primary storage for Prometheus service discovery
   - **Consul KV**: Metadata, groups, presets, audit logs under `skills/cm/` namespace
   - All KV operations go through `KVManager` with namespace validation

3. **BlackboxManager** (`backend/core/blackbox_manager.py`)
   - CRUD operations for Blackbox Exporter targets
   - CSV/XLSX import/export
   - Prometheus config generation
   - Module persistence in KV

4. **Service Preset System** (`backend/core/service_preset_manager.py`)
   - Reusable service templates with variables `${var}` and `${var:default}`
   - Preview rendering before registration
   - Bulk registration support
   - Built-in presets for common exporters

5. **Advanced Search** (`backend/core/advanced_search.py`)
   - 12 comparison operators (eq, ne, gt, lt, contains, regex, etc.)
   - Nested field queries (Meta.company, Meta.env)
   - AND/OR condition support
   - Filter metadata extraction

6. **Remote Installers** (`backend/core/installers/`)
   - **Linux**: SSH-based Node Exporter installation with systemd
   - **Windows**: Multi-connector (SSH/WinRM/PSExec) with automatic fallback
   - WebSocket streaming for real-time logs
   - Pre-flight validation and rollback
   - Connection priority: SSH → WinRM → PSExec

7. **KV Namespace Structure:**
   ```
   skills/cm/
   ├── blackbox/
   │   ├── targets/{id}.json
   │   ├── groups/{id}.json
   │   └── modules.json
   ├── services/
   │   ├── presets/{id}.json
   │   └── templates/{id}.json
   ├── settings/
   │   ├── ui.json
   │   ├── credentials/{id}.json
   │   └── users/{username}.json
   └── audit/{timestamp}-{id}.json
   ```

8. **Metadata Fields Manager** (`backend/api/metadata_fields_manager.py`)
   - Extracts dynamic fields from Prometheus `relabel_configs`
   - Provides available columns for frontend tables
   - Supports multi-server field aggregation
   - Endpoint: `/api/v1/metadata-fields/servers`

9. **Prometheus Config Manager** (`backend/api/prometheus_config.py`, `backend/core/yaml_config_service.py`)
   - Multi-server YAML config editor via SSH
   - Support for prometheus.yml, blackbox.yml, alertmanager.yml
   - Comment preservation with ruamel.yaml
   - Remote validation with promtool
   - Batch updates across multiple servers
   - SSH connection pooling with retry logic

10. **Multi-Config Manager** (`backend/core/multi_config_manager.py`)
    - Parallel SSH operations across Prometheus cluster
    - Centralized credential management from .env
    - Format: `PROMETHEUS_CONFIG_HOSTS=host:port/user/pass;host2:port/user/pass`
    - Automatic master/slave server coordination

**API Structure:**

All endpoints under `/api/v1/`:
- `/services` - Consul service CRUD
- `/blackbox/targets` - Blackbox target management
- `/blackbox/groups` - Group organization
- `/presets` - Service template system
- `/search/advanced` - Advanced query engine
- `/kv/*` - Direct KV store access
- `/installer/*` - Remote installation (Basic Auth protected)
- `/health/*` - System health checks
- `/dashboard/*` - Aggregated metrics
- `/audit/events` - Audit log queries
- `/metadata-fields/*` - Dynamic field extraction from Prometheus configs
- `/prometheus-config/*` - Multi-server YAML config editor with SSH
- `/optimized-endpoints/*` - Performance-optimized bulk operations

**Key Patterns:**

- **Async Everywhere**: All I/O operations use `async/await`
- **Error Handling**: Try/except with meaningful HTTPException responses
- **Validation**: Pydantic models for all request/response data
- **Logging**: Python `logging` module with context
- **Retry Logic**: `@retry_with_backoff` decorator for Consul API calls

**Security Features:**

- **Basic Authentication**: Installer endpoints protected with HTTP Basic Auth
- **Token Management**: Consul ACL token validation
- **SSH Key Support**: Public key authentication for remote installers
- **Credential Storage**: Encrypted storage in Consul KV under `skills/cm/settings/credentials`
- **CORS Policy**: Restrictive CORS with configurable origins in .env

### Frontend (React 19 + TypeScript + Ant Design Pro)

**Component Organization:**

```
frontend/src/
├── pages/           # Route-level components
│   ├── Dashboard.tsx         # Metrics, charts, quick actions
│   ├── Services.tsx          # Main service list with filters
│   ├── BlackboxTargets.tsx   # Blackbox monitoring targets
│   ├── BlackboxGroups.tsx    # Target organization
│   ├── ServicePresets.tsx    # Template management
│   ├── KvBrowser.tsx         # Tree navigation of KV store
│   ├── AuditLog.tsx          # Operation history
│   ├── Installer.tsx         # Remote exporter installation
│   ├── PrometheusConfig.tsx  # Multi-server YAML config editor
│   └── MetadataFields.tsx    # Dynamic field configuration
├── components/      # Reusable components
│   ├── AdvancedSearchPanel.tsx    # Query builder UI
│   ├── ColumnSelector.tsx         # Drag-drop column config
│   ├── MetadataFilterBar.tsx      # Quick filters
│   ├── ListPageLayout.tsx         # Standardized page wrapper
│   └── ServerSelector.tsx         # Multi-server switcher
├── services/
│   └── api.ts       # Axios HTTP client with TypeScript types
└── hooks/           # Custom React hooks
    ├── useConsulServices.ts
    └── usePrometheusFields.ts
```

**Key Patterns:**

- **ProTable**: Use `@ant-design/pro-table` for all data tables (built-in pagination, filters, search)
- **TypeScript Strict**: All API responses typed via interfaces in `api.ts`
- **State Management**: React hooks + context (no Redux/MobX)
- **Modals**: Ant Design Modal for create/edit forms
- **Real-time Updates**: WebSocket connections for installer logs
- **Column Persistence**: Save user column preferences to localStorage
- **Dynamic Columns**: Fetch available metadata fields from `/api/v1/metadata-fields/servers` to generate columns

**Data Flow Example:**
```
User Action → Component → api.ts → Backend API → ConsulManager → Consul API
                                              ↘ KVManager → Consul KV
```

## Development Commands

### Initial Setup

```bash
# Backend
cd backend
python -m venv venv
venv\Scripts\activate          # Windows
source venv/bin/activate       # Linux
pip install -r requirements.txt

# Configure environment variables
# Copy from example or manually create .env with:
# CONSUL_HOST=172.16.1.26
# CONSUL_PORT=8500
# CONSUL_TOKEN=8382a112-81e0-cd6d-2b92-8565925a0675
# PROMETHEUS_USER=prometheus
# PROMETHEUS_PASSWORD=your-password
# PROMETHEUS_CONFIG_HOSTS=host:port/user/pass;host2:port/user/pass

# Frontend
cd frontend
npm install
```

### Running Development Servers

```bash
# Backend (port 5000)
cd backend
python app.py

# Frontend (port 8081 - avoids conflict with Grafana:3000)
cd frontend
npm run dev

# Or use convenience script (Windows only)
restart-app.bat    # Kills existing Node.js/Python processes
                   # Cleans __pycache__ and .vite cache
                   # Starts backend (5000) and frontend (8081) in separate windows
```

### Testing

```bash
# Backend integration tests
cd backend
python test_phase1.py    # KV namespace and dual storage
python test_phase2.py    # Presets and advanced search

# Build frontend
cd frontend
npm run build            # Output to dist/
npm run preview          # Preview production build
```

### Common Operations

```bash
# Check API documentation
# Open http://localhost:5000/docs (Swagger UI)

# Lint frontend
cd frontend
npm run lint

# Check backend for import errors
cd backend
python -c "from app import app; print('OK')"

# Test Consul connectivity
cd backend
python -c "from core.consul_manager import ConsulManager; import asyncio; cm = ConsulManager(); print(asyncio.run(cm.get_services_overview()))"
```

## Important Implementation Details

### Service ID Sanitization

When creating services, IDs **must** be sanitized:
```python
# backend/core/consul_manager.py:73
sanitized = re.sub(r'[[ \]`~!\\#$^&*=|"{}\':;?\t\n]', '_', raw_id)
if '//' in sanitized or sanitized.startswith('/') or sanitized.endswith('/'):
    raise ValueError("Invalid slashes")
```

Always use `ConsulManager.sanitize_service_id()` before registration.

### Dual Storage Synchronization

When updating Blackbox targets:
1. **Always update Consul Service first** (source of truth for Prometheus)
2. Then update KV store (for metadata/grouping)
3. If KV fails, service is still discoverable
4. Background job can reconcile discrepancies

### Dynamic Fields System

The frontend columns adapt to Prometheus `relabel_configs`:
```yaml
# prometheus.yml
relabel_configs:
  - source_labels: ["__meta_consul_service_metadata_company"]
    target_label: company
```

The `target_label` values become table columns. API extracts these via:
```
GET /api/v1/metadata-fields/servers
```

### WebSocket Installer Logs

Installation uses WebSocket for streaming logs:
```typescript
// Frontend
const ws = new WebSocket(`ws://localhost:5000/ws/installer/${sessionId}`);
ws.onmessage = (event) => {
  const log = JSON.parse(event.data);
  appendLog(log.message);
};

# Backend
@app.websocket("/ws/installer/{session_id}")
async def installer_websocket(websocket: WebSocket, session_id: str):
    await websocket.accept()
    # Stream logs from SSH session
```

### Multi-Server Prometheus Configuration

When editing Prometheus configs across multiple servers:
1. **SSH Connection Setup**: Configure in `.env`:
   ```
   PROMETHEUS_CONFIG_HOSTS=172.16.1.26:5522/root/password;172.16.200.14:22/root/password
   ```
2. **File Path Detection**: Backend automatically locates prometheus.yml, blackbox.yml
3. **Parallel Operations**: Updates pushed to all servers simultaneously
4. **Validation**: Each server runs `promtool check config` before applying
5. **Rollback**: Failed validations prevent config updates
6. **Comment Preservation**: Uses `ruamel.yaml` to maintain YAML comments

Always test on a single server first before pushing to all hosts.

### Basic Auth for Installer Endpoints

Remote installation endpoints require HTTP Basic Auth:
```python
# Backend validates credentials from Consul KV or environment
headers = {
    'Authorization': f'Basic {base64_encode("user:password")}'
}
```

Frontend automatically includes credentials when configured in Settings.

### Port Conflicts

- **3000**: Grafana (production)
- **3001**: Loki (production)
- **5000**: Backend API (development)
- **8080**: Avoid (often in use)
- **8081**: Frontend dev server ✅
- **5522**: SSH (alternate port for main server)

## Code Style Conventions

### Backend
- **Async by default**: Use `async def` for all I/O operations
- **Type hints**: All function signatures have return types
- **Docstrings**: Use triple quotes with Args/Returns sections
- **Error messages**: User-friendly Portuguese messages in HTTPException
- **Imports**: Group by stdlib → third-party → local

### Frontend
- **Functional components**: Use hooks, not class components
- **TypeScript**: No `any` types except for complex Ant Design types
- **Comments**: Portuguese for business logic, English for technical
- **File naming**: PascalCase for components, camelCase for utilities
- **Props**: Destructure in function signature

## Critical Files to Preserve

1. **backend/core/consul_manager_original.py** - Original CLI script (reference only)
2. **backend/.env** - Contains production credentials (**NEVER COMMIT**)
3. **PHASE*_SUMMARY.md** - Implementation documentation
4. **MIGRATION_GUIDE.md** - Data migration procedures
5. **CHANGELOG-SESSION.md** - Recent feature additions and changes

## Troubleshooting

### Backend won't start
- Check Consul is accessible: `curl http://172.16.1.26:8500/v1/status/leader`
- Verify token: `curl -H "X-Consul-Token: ..." http://172.16.1.26:8500/v1/agent/services`
- Check port 5000 availability: `netstat -an | findstr :5000`

### Frontend API calls fail
- Verify backend running on port 5000
- Check CORS headers in `backend/app.py` include `http://localhost:8081`
- Inspect browser console for CORS/network errors

### Services not appearing in Prometheus
- Confirm service registered: `GET /api/v1/services`
- Check Prometheus targets: http://172.16.1.26:9090/targets
- Verify service has correct tags and metadata for `consul_sd_configs`

### Installer hangs
- Check SSH connectivity: `ssh user@target-host`
- Verify credentials in installer payload
- Monitor WebSocket messages for error details
- Check firewall rules on target host

### SSH connection issues for Prometheus config
- Verify SSH credentials in `.env` PROMETHEUS_CONFIG_HOSTS
- Test manual SSH: `ssh -p 5522 root@172.16.1.26`
- Check SSH key permissions if using key-based auth
- Verify promtool is installed on remote servers: `ssh user@host 'which promtool'`

## Testing Against Production

When testing against the production Consul (172.16.1.26):
- **Use a test namespace** for services: prefix with `test_` or use `env=dev` metadata
- **Never delete production services** without confirmation
- **Test KV writes** under `skills/cm/test/` first
- **Monitor Prometheus** for unexpected scrape errors
- **Backup KV data** before bulk operations: `GET /api/v1/kv/tree?prefix=skills/cm`
- **Test Prometheus config changes** on a single server before batch updates

## Common Patterns

### Adding a new API endpoint

```python
# backend/api/my_feature.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/my-feature", tags=["My Feature"])

class MyRequest(BaseModel):
    field: str

@router.post("/action")
async def my_action(req: MyRequest):
    # Business logic
    return {"success": True, "data": result}

# backend/app.py
from api.my_feature import router as my_feature_router
app.include_router(my_feature_router, prefix="/api/v1")
```

### Adding a new frontend page

```typescript
// frontend/src/pages/MyPage.tsx
import { ProTable } from '@ant-design/pro-components';
import { getMyData } from '../services/api';

export default function MyPage() {
  return (
    <ProTable
      columns={columns}
      request={async (params) => {
        const data = await getMyData(params);
        return { data: data.items, total: data.total };
      }}
    />
  );
}

// frontend/src/App.tsx
import MyPage from './pages/MyPage';
// Add route
<Route path="/my-page" element={<MyPage />} />
```

### Querying with Advanced Search

```typescript
import { advancedSearch } from './services/api';

const results = await advancedSearch({
  resource: 'services',
  conditions: [
    { field: 'Meta.company', operator: 'eq', value: 'ACME' },
    { field: 'Meta.env', operator: 'in', value: ['prod', 'staging'] }
  ],
  operator: 'and'
});
```

### Editing Prometheus Config Remotely

```typescript
import { getPrometheusConfig, updatePrometheusConfig } from './services/api';

// Fetch config from all servers
const configs = await getPrometheusConfig();

// Edit specific server
const updatedConfig = {
  ...configs['172.16.1.26'],
  yaml_content: modifiedYaml
};

// Update (validates on server before applying)
await updatePrometheusConfig('172.16.1.26', updatedConfig);
```

```python
# Backend validates YAML before applying
from core.yaml_config_service import YamlConfigService

service = YamlConfigService()
await service.update_config(
    host='172.16.1.26',
    file_path='/etc/prometheus/prometheus.yml',
    yaml_content=new_content,
    validate=True  # Runs promtool
)
```

## Project History

- **Phase 1**: KV namespace, dual storage, audit logging
- **Phase 2**: Service presets, advanced search, blackbox groups
- **Phase 3**: Frontend modernization, column selector, dashboard redesign
- **Phase 4**: Multi-server Prometheus YAML editor with SSH, metadata fields extraction
- **Phase 5**: Basic Auth security, installer improvements with multiple connectors
- **Current**: Performance optimizations, Windows multi-connector (SSH/WinRM/PSExec)

See `PHASE*_SUMMARY.md` and session changelog files for detailed implementation notes.

## Dependencies

**Backend Key Libraries:**
- `fastapi` - Web framework
- `httpx` - Async HTTP client for Consul API
- `paramiko` - SSH for Linux installer and remote config editing
- `pywinrm` - Windows Remote Management
- `pypsexec` - Windows PSExec protocol
- `pydantic` - Data validation
- `ruamel.yaml` - YAML parsing with comment preservation
- `bcrypt` + `passlib` - Password hashing for Basic Auth
- `python-jose` - JWT token handling
- `websockets` - Real-time installer logs
- `pandas` + `openpyxl` - CSV/Excel import/export

**Frontend Key Libraries:**
- `react` 19 - UI framework
- `antd` - Ant Design components
- `@ant-design/pro-components` - ProTable, ProLayout
- `@ant-design/charts` - G2Plot visualizations
- `@dnd-kit/*` - Drag and drop for column selector
- `axios` - HTTP client
- `react-router-dom` - Routing
- `dayjs` - Date manipulation

## References

- Consul API: https://developer.hashicorp.com/consul/api-docs
- FastAPI: https://fastapi.tiangolo.com
- Ant Design: https://ant.design
- Prometheus: https://prometheus.io/docs
- Original TenSunS project: `TenSunS/` directory (reference implementation)
