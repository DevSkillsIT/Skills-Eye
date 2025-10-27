# Consul Manager - Phase 2 Implementation Summary

## 🎯 Phase 2 Complete: Service Presets & Advanced Search

**Version**: 2.3.0
**Completion Date**: January 2025
**Build on**: Phase 1 (KV namespaces, dual storage, groups, audit)

---

## ✨ What's New in Phase 2

### 1. **Service Presets System** 🎨

Template-based service registration que permite criar serviços rapidamente usando presets reutilizáveis.

**Arquivos Criados**:
- [`backend/core/service_preset_manager.py`](backend/core/service_preset_manager.py) - Core preset logic
- [`backend/api/presets.py`](backend/api/presets.py) - Preset API endpoints

**Features**:
- ✅ Criar templates de serviços reutilizáveis
- ✅ Substituição de variáveis (${var} e ${var:default})
- ✅ Presets built-in (Node Exporter, Windows Exporter, Redis, etc.)
- ✅ Registrar múltiplos serviços de um preset (bulk)
- ✅ Preview antes de registrar
- ✅ Categorização de presets
- ✅ Validação completa de templates

### 2. **Advanced Search Engine** 🔍

Sistema de busca poderoso com suporte a operadores complexos, regex, e lógica AND/OR.

**Arquivos Criados**:
- [`backend/core/advanced_search.py`](backend/core/advanced_search.py) - Search engine
- [`backend/api/search.py`](backend/api/search.py) - Search API endpoints

**Features**:
- ✅ Múltiplos operadores (eq, ne, contains, regex, in, gt/lt, etc.)
- ✅ Lógica AND/OR para combinar condições
- ✅ Busca full-text em múltiplos campos
- ✅ Extração de valores únicos para filtros
- ✅ Ordenação por qualquer campo
- ✅ Paginação eficiente
- ✅ Estatísticas e analytics
- ✅ Quick filters (by company, env, tag)

### 3. **Enhanced API Documentation** 📚

- Swagger UI atualizado com novos endpoints
- Exemplos completos de uso
- Modelos Pydantic para validação
- Testes automatizados

---

## 📋 New API Endpoints

### Service Presets (`/api/v1/presets`)

```
POST   /api/v1/presets                    # Create preset
GET    /api/v1/presets                    # List presets
GET    /api/v1/presets/{id}               # Get specific preset
PUT    /api/v1/presets/{id}               # Update preset
DELETE /api/v1/presets/{id}               # Delete preset

POST   /api/v1/presets/register           # Register service from preset
POST   /api/v1/presets/bulk/register      # Bulk register from preset
POST   /api/v1/presets/preview            # Preview without registering
POST   /api/v1/presets/builtin/create     # Create built-in presets
GET    /api/v1/presets/categories         # List categories
```

### Advanced Search (`/api/v1/search`)

```
POST   /api/v1/search/advanced            # Advanced multi-condition search
POST   /api/v1/search/text                # Full-text search
GET    /api/v1/search/filters             # Get filter options
GET    /api/v1/search/unique-values       # Get unique values for field
GET    /api/v1/search/stats               # Get statistics

# Quick filters
GET    /api/v1/search/by-company/{company}
GET    /api/v1/search/by-env/{env}
GET    /api/v1/search/by-tag/{tag}
GET    /api/v1/search/blackbox            # Blackbox-specific search
```

---

## 💡 Usage Examples

### Example 1: Create and Use a Service Preset

```bash
# Step 1: Create a custom preset
curl -X POST "http://localhost:5000/api/v1/presets?user=admin" \
  -H "Content-Type: application/json" \
  -d '{
    "id": "my-app",
    "name": "My Application",
    "service_name": "my_app",
    "port": 8080,
    "tags": ["application", "custom"],
    "meta_template": {
      "app": "my_app",
      "env": "${env}",
      "version": "${version:1.0.0}",
      "datacenter": "${datacenter}"
    },
    "checks": [{
      "HTTP": "http://${address}:${port}/health",
      "Interval": "30s"
    }],
    "category": "application",
    "description": "My custom application template"
  }'

# Step 2: Register service from preset
curl -X POST "http://localhost:5000/api/v1/presets/register?user=admin" \
  -H "Content-Type: application/json" \
  -d '{
    "preset_id": "my-app",
    "variables": {
      "address": "10.0.0.10",
      "env": "prod",
      "version": "2.0.0",
      "datacenter": "palmas"
    }
  }'

# Response:
# {
#   "success": true,
#   "message": "Service registered successfully",
#   "service_id": "my_app_10_0_0_10_prod",
#   "preset_used": "my-app"
# }
```

### Example 2: Bulk Register from Preset

```bash
# Deploy Node Exporter to 5 servers
curl -X POST "http://localhost:5000/api/v1/presets/bulk/register?preset_id=node-exporter-linux&user=admin" \
  -H "Content-Type: application/json" \
  -d '[
    {"address": "10.0.0.1", "env": "prod", "datacenter": "palmas", "hostname": "web-01"},
    {"address": "10.0.0.2", "env": "prod", "datacenter": "palmas", "hostname": "web-02"},
    {"address": "10.0.0.3", "env": "prod", "datacenter": "palmas", "hostname": "web-03"},
    {"address": "10.0.0.4", "env": "prod", "datacenter": "rio", "hostname": "db-01"},
    {"address": "10.0.0.5", "env": "staging", "datacenter": "rio", "hostname": "staging-01"}
  ]'

# Response:
# {
#   "success": true,
#   "summary": {
#     "total": 5,
#     "successful": 5,
#     "failed": 0
#   },
#   "results": [...]
# }
```

### Example 3: Advanced Search with Multiple Conditions

```bash
# Find all production Ramada services with HTTP module
curl -X POST "http://localhost:5000/api/v1/search/advanced" \
  -H "Content-Type: application/json" \
  -d '{
    "conditions": [
      {"field": "Meta.company", "operator": "eq", "value": "Ramada"},
      {"field": "Meta.env", "operator": "eq", "value": "prod"},
      {"field": "Meta.module", "operator": "contains", "value": "http"}
    ],
    "logical_operator": "and",
    "sort_by": "Meta.name",
    "sort_desc": false,
    "page": 1,
    "page_size": 20
  }'

# Response:
# {
#   "success": true,
#   "data": [...],  # Matching services
#   "pagination": {
#     "page": 1,
#     "page_size": 20,
#     "total": 12,
#     "total_pages": 1,
#     "has_previous": false,
#     "has_next": false
#   }
# }
```

### Example 4: Full-Text Search

```bash
# Search for anything containing "web"
curl -X POST "http://localhost:5000/api/v1/search/text" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "web",
    "page": 1,
    "page_size": 20
  }'

# Searches in: Meta.name, Meta.instance, Meta.company, Meta.project, service, id
```

### Example 5: Get Filter Options

```bash
# Get all available filter values
curl "http://localhost:5000/api/v1/search/filters"

# Response:
# {
#   "success": true,
#   "filters": {
#     "module": ["http_2xx", "icmp", "tcp_connect", "node_exporter"],
#     "company": ["Ramada", "Skills IT", "TenSunS"],
#     "project": ["web", "infrastructure", "monitoring"],
#     "env": ["prod", "dev", "staging"],
#     "datacenter": ["palmas", "rio"]
#   },
#   "total_services": 150
# }
```

### Example 6: Use Built-in Presets

```bash
# Step 1: Create built-in presets
curl -X POST "http://localhost:5000/api/v1/presets/builtin/create?user=admin"

# Response:
# {
#   "success": true,
#   "message": "Created 4 built-in presets",
#   "summary": {
#     "successful": ["node-exporter-linux", "windows-exporter", "blackbox-icmp", "redis-exporter"],
#     "failed": [],
#     "total": 4
#   }
# }

# Step 2: Use Node Exporter preset
curl -X POST "http://localhost:5000/api/v1/presets/register?user=admin" \
  -H "Content-Type: application/json" \
  -d '{
    "preset_id": "node-exporter-linux",
    "variables": {
      "address": "172.16.1.100",
      "env": "prod",
      "datacenter": "palmas",
      "hostname": "production-server-01"
    }
  }'
```

---

## 🔍 Search Operators Reference

| Operator | Description | Example |
|----------|-------------|---------|
| `eq` | Equals | `{"field": "Meta.env", "operator": "eq", "value": "prod"}` |
| `ne` | Not equals | `{"field": "Meta.env", "operator": "ne", "value": "dev"}` |
| `contains` | String contains | `{"field": "Meta.name", "operator": "contains", "value": "web"}` |
| `regex` | Regular expression | `{"field": "Meta.name", "operator": "regex", "value": "^web-.*"}` |
| `in` | Value in list | `{"field": "Meta.env", "operator": "in", "value": ["prod", "staging"]}` |
| `not_in` | Value not in list | `{"field": "Meta.env", "operator": "not_in", "value": ["dev"]}` |
| `starts_with` | String starts with | `{"field": "Meta.name", "operator": "starts_with", "value": "server"}` |
| `ends_with` | String ends with | `{"field": "Meta.name", "operator": "ends_with", "value": "-01"}` |
| `gt` | Greater than (numeric) | `{"field": "Meta.port", "operator": "gt", "value": "8000"}` |
| `lt` | Less than (numeric) | `{"field": "Meta.port", "operator": "lt", "value": "9000"}` |
| `gte` | Greater than or equal | `{"field": "Meta.port", "operator": "gte", "value": "8080"}` |
| `lte` | Less than or equal | `{"field": "Meta.port", "operator": "lte", "value": "9999"}` |

---

## 📦 Built-in Presets

### node-exporter-linux
```yaml
Name: Node Exporter (Linux)
Service: node_exporter
Port: 9100
Tags: [monitoring, linux, exporter]
Variables: env, datacenter, hostname
Health Check: HTTP /metrics
```

### windows-exporter
```yaml
Name: Windows Exporter
Service: windows_exporter
Port: 9182
Tags: [monitoring, windows, exporter]
Variables: env, datacenter, hostname
Health Check: HTTP /metrics
```

### blackbox-icmp
```yaml
Name: Blackbox ICMP Probe
Service: blackbox_exporter
Port: 9115
Tags: [monitoring, blackbox, icmp]
Variables: company, project, env, name, target
```

### redis-exporter
```yaml
Name: Redis Exporter
Service: redis_exporter
Port: 9121
Tags: [monitoring, redis, database]
Variables: env, address, redis_port (default: 6379)
Health Check: HTTP /metrics
```

---

## 🧪 Testing Phase 2

### Run Test Suite

```bash
cd backend
python test_phase2.py
```

**Tests Include**:
- ✓ Service preset creation
- ✓ Built-in presets generation
- ✓ Variable substitution
- ✓ Service registration from preset
- ✓ Advanced search with all operators
- ✓ Full-text search
- ✓ Filter options extraction
- ✓ Pagination and sorting
- ✓ Statistics generation

### Manual API Testing

Use Swagger UI: http://localhost:5000/docs

Navigate to:
- **Presets** section - Test preset CRUD
- **Search** section - Test search capabilities

---

## 🎓 Key Concepts

### Variable Substitution in Presets

Presets support two types of variables:

1. **Required variables**: `${variable}`
   - Must be provided when registering
   - Example: `${address}`, `${env}`

2. **Optional variables with defaults**: `${variable:default}`
   - Uses default if not provided
   - Example: `${port:9100}`, `${version:1.0.0}`

### Nested Field Paths

Search supports dot notation for nested fields:

- `Meta.company` - Company in metadata
- `Meta.env` - Environment in metadata
- `Tags` - Service tags array
- `Service` - Service name

### Logical Operators

- **AND**: All conditions must match
- **OR**: At least one condition must match

---

## 📊 Performance Optimizations

1. **Lazy Loading**: Presets loaded only when needed
2. **Caching**: Filter options cached per request
3. **Pagination**: Efficient handling of large result sets
4. **In-Memory Search**: Fast filtering without database queries
5. **Regex Compilation**: Patterns compiled once per search

---

## 🔒 Security & Validation

### Preset Validation

- ✓ Required fields check (id, name, service_name)
- ✓ Port range validation (1-65535)
- ✓ Health check structure validation
- ✓ Variable syntax validation
- ✓ Service ID sanitization

### Search Security

- ✓ No code injection via regex (safe patterns only)
- ✓ Field path validation
- ✓ Page size limits (max 100)
- ✓ Operator whitelist

---

## 🎯 Use Cases

### 1. Standardized Deployments

```python
# Create company-wide preset
await manager.create_preset(
    preset_id="company-standard-app",
    ...preset config...
)

# Deploy to 100 servers
for server in servers:
    await manager.register_from_preset(
        preset_id="company-standard-app",
        variables={"address": server.ip, "env": server.env}
    )
```

### 2. Dynamic Filtering UI

```javascript
// Get filter options
const filters = await fetch('/api/v1/search/filters').then(r => r.json());

// Build dropdown
<Select options={filters.company.map(c => ({label: c, value: c}))} />

// Search with selected filters
const results = await fetch('/api/v1/search/advanced', {
    method: 'POST',
    body: JSON.stringify({
        conditions: [
            {field: 'Meta.company', operator: 'eq', value: selectedCompany}
        ]
    })
});
```

### 3. Compliance Reporting

```bash
# Find all production services missing health checks
curl -X POST "http://localhost:5000/api/v1/search/advanced" \
  -d '{
    "conditions": [
      {"field": "Meta.env", "operator": "eq", "value": "prod"},
      {"field": "Check", "operator": "eq", "value": null}
    ],
    "logical_operator": "and"
  }'
```

---

## 🔜 Next Steps (Phase 3)

### Frontend Development

- [ ] Update API client with Phase 2 endpoints
- [ ] Create Preset Management UI
- [ ] Add Advanced Search component
- [ ] Build Filter Builder interface
- [ ] Add bulk operations UI
- [ ] Statistics dashboard

### Remaining Backend Features

- [ ] Batch service operations (update/delete multiple)
- [ ] Enhanced Prometheus config generation
- [ ] Service health check templates
- [ ] Import/Export presets
- [ ] Preset versioning

---

## 📚 Documentation

- **Phase 1 Summary**: [`IMPLEMENTATION_SUMMARY.md`](IMPLEMENTATION_SUMMARY.md)
- **Migration Guide**: [`MIGRATION_GUIDE.md`](MIGRATION_GUIDE.md)
- **API Docs**: http://localhost:5000/docs
- **Test Scripts**:
  - Phase 1: [`backend/test_phase1.py`](backend/test_phase1.py)
  - Phase 2: [`backend/test_phase2.py`](backend/test_phase2.py)

---

## 🎉 Phase 2 Completion Status

**✅ COMPLETE - January 2025**

### Delivered Features

- ✅ Service Presets Manager (core + API)
- ✅ Advanced Search Engine (12 operators)
- ✅ Built-in Preset Templates (4 exporters)
- ✅ Variable Substitution System
- ✅ Bulk Operations
- ✅ Full-text Search
- ✅ Filter Options API
- ✅ Statistics & Analytics
- ✅ Comprehensive Testing
- ✅ Complete Documentation

### API Endpoints Added

- **Presets**: 9 endpoints
- **Search**: 10 endpoints
- **Total New**: 19 endpoints

### Lines of Code

- **Core Logic**: ~1,200 lines
- **API Endpoints**: ~800 lines
- **Tests**: ~400 lines
- **Total**: ~2,400 lines

---

**Built with ❤️ for better Consul management**

**Version 2.3.0** - Service Presets & Advanced Search Complete 🚀
