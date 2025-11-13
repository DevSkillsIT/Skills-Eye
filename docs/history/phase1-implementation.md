# Consul Manager - Phase 1 Implementation Summary

## Overview

This document summarizes the Phase 1 implementation of the enhanced Consul Manager, following the comprehensive blueprint and incorporating patterns from TenSunS.

---

## What's Been Implemented

### 1. KV Namespace Standardization (`backend/core/kv_manager.py`)

**New Standardized Namespace Structure:**

```
skills/eye/
├── blackbox/
│   ├── targets/<id>.json         # Individual target configurations
│   ├── groups/<group>.json       # Target group definitions
│   └── modules.json              # Supported modules list
├── services/
│   ├── presets/<id>.json         # Service registration presets
│   └── templates/<id>.json       # Service templates
├── settings/
│   ├── ui.json                   # Global UI settings
│   └── users/<user>.json         # User-specific preferences
├── imports/
│   ├── last.json                 # Last import details
│   └── history/                  # Import history
└── audit/
    └── YYYY/MM/DD/<timestamp>.json  # Audit log entries
```

**Key Features:**

- **Versioned Metadata**: All KV entries include metadata (created_at, updated_at, updated_by, version)
- **Namespace Safety**: All operations validate keys start with `skills/eye/`
- **Automatic Audit Logging**: All mutations are logged to audit trail
- **Migration Support**: Tools to migrate from old TenSunS namespace

**Core Methods:**

```python
# Basic KV operations
await kv.get_json(key, default=None)
await kv.put_json(key, value, metadata=None)
await kv.delete_key(key)
await kv.list_keys(prefix)
await kv.get_tree(prefix, unwrap_metadata=True)

# Blackbox target operations
await kv.get_blackbox_target(target_id)
await kv.put_blackbox_target(target_id, target_data, user)
await kv.delete_blackbox_target(target_id)
await kv.list_blackbox_targets(filters)

# Group operations
await kv.get_blackbox_group(group_id)
await kv.put_blackbox_group(group_id, group_data, user)
await kv.list_blackbox_groups()

# Audit logging
await kv.log_audit_event(action, resource_type, resource_id, user, details)
await kv.get_audit_events(start_date, end_date, resource_type, action)

# UI settings
await kv.get_ui_settings(user=None)
await kv.put_ui_settings(settings, user=None)

# Migration
await kv.migrate_from_old_namespace(old_prefix)
```

---

### 2. Enhanced Blackbox Manager (`backend/core/blackbox_manager.py`)

**Dual Storage Mode:**

- **Consul Services**: For Prometheus service discovery (existing)
- **Consul KV**: For advanced configuration, grouping, and metadata (NEW)

**Enhanced Target Schema (Blueprint Compliant):**

```json
{
  "id": "site-ramada-www",
  "group": "ramada-sites",
  "target": "https://www.ramada.com.br",
  "module": "http_2xx",
  "labels": {
    "company": "Ramada",
    "env": "prod",
    "project": "web"
  },
  "interval": "30s",
  "timeout": "10s",
  "enabled": true,
  "notes": "Home institucional"
}
```

**New Features:**

1. **Target Groups**: Organize targets into logical groups
2. **Bulk Operations**: Enable/disable multiple targets at once
3. **Enhanced Labels**: Support for custom labels beyond standard metadata
4. **Configurable Intervals**: Per-target scrape intervals and timeouts
5. **Enable/Disable**: Soft delete (disable) without removing from Consul
6. **Audit Trail**: All operations logged automatically

**New Methods:**

```python
# Enhanced target creation
await manager.add_target(
    module, company, project, env, name, instance,
    group=None,           # NEW: Group assignment
    labels=None,          # NEW: Additional labels
    interval="30s",       # NEW: Custom interval
    timeout="10s",        # NEW: Custom timeout
    enabled=True,         # NEW: Enable/disable flag
    notes=None,           # NEW: Notes/description
    user="system"         # NEW: User tracking
)

# Group management
await manager.create_group(group_id, name, filters, labels, description, user)
await manager.list_groups()
await manager.get_group(group_id)
await manager.get_group_members(group_id)

# Bulk operations
await manager.bulk_enable_disable(group_id=None, target_ids=None, enabled=True, user="system")
```

---

### 3. Blackbox API Enhancements (`backend/api/blackbox.py`)

**New Endpoints:**

#### Group Management

```
POST   /api/v1/blackbox/groups              # Create group
GET    /api/v1/blackbox/groups              # List all groups
GET    /api/v1/blackbox/groups/{group_id}   # Get group + members
```

#### Bulk Operations

```
POST   /api/v1/blackbox/bulk/enable-disable # Enable/disable multiple targets
```

#### Enhanced Target Creation

```
POST   /api/v1/blackbox/enhanced            # Create with full feature set
```

**Request Models:**

```python
class BlackboxTargetEnhanced(BaseModel):
    module: str
    company: str
    project: str
    env: str
    name: str
    instance: str
    group: Optional[str] = None
    labels: Optional[Dict[str, str]] = None
    interval: str = "30s"
    timeout: str = "10s"
    enabled: bool = True
    notes: Optional[str] = None

class BlackboxGroupCreate(BaseModel):
    id: str
    name: str
    filters: Optional[Dict[str, str]] = None
    labels: Optional[Dict[str, str]] = None
    description: Optional[str] = None

class BulkEnableDisableRequest(BaseModel):
    group_id: Optional[str] = None
    target_ids: Optional[List[str]] = None
    enabled: bool
```

---

### 4. KV Store API (`backend/api/kv.py` - NEW)

**Complete KV management API with namespace safety:**

#### KV CRUD Operations

```
GET    /api/v1/kv/get?key=skills/eye/...          # Get single key
POST   /api/v1/kv/put                            # Store value
DELETE /api/v1/kv/delete?key=skills/eye/...      # Delete key
GET    /api/v1/kv/list?prefix=skills/eye/...     # List keys
GET    /api/v1/kv/tree?prefix=skills/eye/...     # Get tree
```

#### Audit Log

```
GET    /api/v1/kv/audit/events                  # Query audit log
  ?start_date=2025-01-01
  &end_date=2025-01-31
  &resource_type=blackbox_target
  &action=CREATE
```

#### UI Settings

```
GET    /api/v1/kv/settings/ui?user=johndoe      # Get settings
POST   /api/v1/kv/settings/ui?user=johndoe      # Save settings
```

#### Import Tracking

```
GET    /api/v1/kv/imports/last                  # Get last import details
```

#### Migration Utility

```
POST   /api/v1/kv/migrate?old_prefix=...        # Migrate old namespace
```

---

## Integration Points

### Prometheus Service Discovery (Existing + Enhanced)

**How it Works:**

1. **Target Registration**: Each blackbox target is registered as a Consul service:
   ```json
   {
     "id": "http_2xx/Ramada/web/prod@HomePage",
     "name": "blackbox_exporter",
     "tags": ["http_2xx"],
     "Meta": {
       "module": "http_2xx",
       "company": "Ramada",
       "project": "web",
       "env": "prod",
       "name": "HomePage",
       "instance": "https://www.ramada.com.br"
     }
   }
   ```

2. **Prometheus Configuration** (Auto-generated):
   ```yaml
   scrape_configs:
     - job_name: 'blackbox_exporter'
       scrape_interval: 15s
       metrics_path: /probe
       consul_sd_configs:
         - server: '172.16.1.26:8500'
           token: '${CONSUL_TOKEN}'
           services: ['blackbox_exporter']
       relabel_configs:
         - source_labels: [__meta_consul_service_metadata_instance]
           target_label: __param_target
         - source_labels: [__meta_consul_service_metadata_module]
           target_label: __param_module
         - source_labels: [__meta_consul_service_metadata_company]
           target_label: company
         - source_labels: [__meta_consul_service_metadata_env]
           target_label: env
         - source_labels: [__meta_consul_service_metadata_name]
           target_label: name
         - source_labels: [__meta_consul_service_metadata_project]
           target_label: project
         - source_labels: [__param_target]
           target_label: instance
         - target_label: __address__
           replacement: 127.0.0.1:9115
   ```

3. **Result**: Prometheus automatically discovers all blackbox targets from Consul and scrapes them with proper labels.

---

## API Documentation

### Complete Endpoint List (Updated)

#### Services
- `GET    /api/v1/services`
- `GET    /api/v1/services/{id}`
- `POST   /api/v1/services`
- `PUT    /api/v1/services/{id}`
- `DELETE /api/v1/services/{id}`

#### Nodes
- `GET    /api/v1/nodes`
- `GET    /api/v1/nodes/{addr}/services`

#### Blackbox (Enhanced)
- `GET    /api/v1/blackbox`
- `GET    /api/v1/blackbox/summary`
- `POST   /api/v1/blackbox` (basic)
- `POST   /api/v1/blackbox/enhanced` (NEW - with groups/labels/intervals)
- `PUT    /api/v1/blackbox`
- `DELETE /api/v1/blackbox`
- `POST   /api/v1/blackbox/import`
- `GET    /api/v1/blackbox/config/{rules|blackbox|prometheus}`
- `POST   /api/v1/blackbox/groups` (NEW)
- `GET    /api/v1/blackbox/groups` (NEW)
- `GET    /api/v1/blackbox/groups/{group_id}` (NEW)
- `POST   /api/v1/blackbox/bulk/enable-disable` (NEW)

#### KV Store (NEW)
- `GET    /api/v1/kv/get`
- `POST   /api/v1/kv/put`
- `DELETE /api/v1/kv/delete`
- `GET    /api/v1/kv/list`
- `GET    /api/v1/kv/tree`
- `GET    /api/v1/kv/audit/events`
- `GET    /api/v1/kv/settings/ui`
- `POST   /api/v1/kv/settings/ui`
- `GET    /api/v1/kv/imports/last`
- `POST   /api/v1/kv/migrate`

#### Health & Installer (Existing)
- `GET    /api/v1/health/status`
- `GET    /api/v1/health/connectivity`
- `POST   /api/v1/installer/check`
- `POST   /api/v1/installer/run`
- `WS     /ws/installer/{installation_id}`

---

## Usage Examples

### Example 1: Create a Blackbox Target with Group

```python
import httpx

# Create target with enhanced features
response = await httpx.post(
    "http://localhost:5000/api/v1/blackbox/enhanced",
    json={
        "module": "http_2xx",
        "company": "Ramada",
        "project": "web",
        "env": "prod",
        "name": "HomePage",
        "instance": "https://www.ramada.com.br",
        "group": "ramada-sites",
        "labels": {"region": "brazil"},
        "interval": "15s",
        "timeout": "5s",
        "enabled": True,
        "notes": "Main website homepage"
    },
    params={"user": "admin"}
)

print(response.json())
# {
#   "success": True,
#   "message": "Blackbox target created with enhanced features",
#   "service_id": "http_2xx/Ramada/web/prod@HomePage"
# }
```

### Example 2: Create a Target Group

```python
# Create group
response = await httpx.post(
    "http://localhost:5000/api/v1/blackbox/groups",
    json={
        "id": "ramada-sites",
        "name": "Ramada Websites",
        "filters": {"company": "Ramada", "project": "web"},
        "labels": {"monitored_by": "ops-team"},
        "description": "All Ramada web properties"
    },
    params={"user": "admin"}
)

print(response.json())
# {
#   "success": True,
#   "message": "Group 'Ramada Websites' created successfully",
#   "group_id": "ramada-sites"
# }
```

### Example 3: Bulk Disable Group

```python
# Disable all targets in a group
response = await httpx.post(
    "http://localhost:5000/api/v1/blackbox/bulk/enable-disable",
    json={
        "group_id": "ramada-sites",
        "enabled": False
    },
    params={"user": "admin"}
)

print(response.json())
# {
#   "success": True,
#   "message": "Disabled 12 targets",
#   "summary": {
#     "success_count": 12,
#     "failed_count": 0,
#     "total": 12,
#     "details": []
#   }
# }
```

### Example 4: Query Audit Log

```python
# Get all blackbox target creations in January 2025
response = await httpx.get(
    "http://localhost:5000/api/v1/kv/audit/events",
    params={
        "start_date": "2025-01-01",
        "end_date": "2025-01-31",
        "resource_type": "blackbox_target",
        "action": "CREATE"
    }
)

print(response.json())
# {
#   "success": True,
#   "events": [
#     {
#       "timestamp": "2025-01-15T10:30:00Z",
#       "action": "CREATE",
#       "resource_type": "blackbox_target",
#       "resource_id": "http_2xx/Ramada/web/prod@HomePage",
#       "user": "admin",
#       "details": {
#         "module": "http_2xx",
#         "instance": "https://www.ramada.com.br",
#         "group": "ramada-sites"
#       }
#     },
#     ...
#   ],
#   "count": 45
# }
```

### Example 5: Store UI Preferences

```python
# Save user-specific column preferences
response = await httpx.post(
    "http://localhost:5000/api/v1/kv/settings/ui",
    json={
        "blackbox_table_columns": ["module", "name", "instance", "env"],
        "page_size": 50,
        "theme": "dark"
    },
    params={"user": "johndoe"}
)

print(response.json())
# {
#   "success": True,
#   "message": "Settings saved successfully",
#   "scope": "user"
# }
```

---

## Testing the Implementation

### Start the Backend

```bash
cd backend
python app.py
```

The API will be available at:
- **API**: http://localhost:5000
- **Docs**: http://localhost:5000/docs (Swagger UI)
- **ReDoc**: http://localhost:5000/redoc

### Test Endpoints

```bash
# Test KV get/put
curl -X POST "http://localhost:5000/api/v1/kv/put" \
  -H "Content-Type: application/json" \
  -d '{
    "key": "skills/eye/test/hello.json",
    "value": {"message": "Hello World"},
    "metadata": {"updated_by": "test"}
  }'

curl "http://localhost:5000/api/v1/kv/get?key=skills/eye/test/hello.json"

# Test group creation
curl -X POST "http://localhost:5000/api/v1/blackbox/groups?user=admin" \
  -H "Content-Type: application/json" \
  -d '{
    "id": "test-group",
    "name": "Test Group",
    "filters": {"env": "dev"},
    "description": "Testing group functionality"
  }'

# List groups
curl "http://localhost:5000/api/v1/blackbox/groups"

# Create enhanced target
curl -X POST "http://localhost:5000/api/v1/blackbox/enhanced?user=admin" \
  -H "Content-Type: application/json" \
  -d '{
    "module": "icmp",
    "company": "Test",
    "project": "Monitoring",
    "env": "dev",
    "name": "Google DNS",
    "instance": "8.8.8.8",
    "group": "test-group",
    "interval": "10s",
    "timeout": "3s",
    "enabled": true,
    "notes": "Google public DNS server"
  }'

# Get audit events
curl "http://localhost:5000/api/v1/kv/audit/events?resource_type=blackbox_target&action=CREATE"
```

---

## Migration from TenSunS/Old Structure

If you have existing data in the old `ConsulManager/record/blackbox` namespace:

```bash
# Run migration
curl -X POST "http://localhost:5000/api/v1/kv/migrate?old_prefix=ConsulManager/record/blackbox&user=admin"

# Response:
# {
#   "success": true,
#   "message": "Migration completed",
#   "summary": {
#     "migrated": 150,
#     "failed": 0,
#     "total": 150
#   }
# }
```

---

## Next Steps (Remaining Phases)

### Phase 2: Service Presets & Advanced Features
- [ ] Implement service presets system
- [ ] Add advanced metadata search
- [ ] Enhance Prometheus config generation
- [ ] Create batch service operations

### Phase 3: Frontend Development
- [ ] Update API client with new endpoints
- [ ] Create BlackboxGroups UI page
- [ ] Create KV Browser component
- [ ] Create AuditLog page
- [ ] Add bulk operations UI
- [ ] Enhance existing pages with new features

### Phase 4: Installer Enhancements
- [ ] Add comprehensive pre-checks
- [ ] Windows OpenSSH detection
- [ ] PowerShell script fallback
- [ ] Batch installation support

---

## Architecture Decisions

### Why Dual Storage?

1. **Services** - Required for Prometheus consul_sd_configs to work
2. **KV** - Provides:
   - Advanced configuration (intervals, timeouts, enabled/disabled state)
   - Grouping and hierarchical organization
   - Rich metadata beyond Consul service limits
   - Audit trail and versioning
   - UI preferences persistence

### Why skills/eye/ Namespace?

- **Isolation**: Prevents conflicts with other apps using Consul
- **Security**: Makes it easier to restrict KV access
- **Organization**: Clear structure for app data
- **Migration**: Easy to identify and migrate app-specific data

---

## Files Modified/Created

### New Files
- `backend/core/kv_manager.py` - KV namespace management
- `backend/api/kv.py` - KV API endpoints
- `IMPLEMENTATION_SUMMARY.md` - This document

### Modified Files
- `backend/core/blackbox_manager.py` - Enhanced with dual storage, groups, bulk ops
- `backend/api/blackbox.py` - Added group endpoints, bulk operations, enhanced creation
- `backend/app.py` - Registered KV router

---

## Patterns Adapted from TenSunS

1. **KV Storage**: Base64 encoding, recursive retrieval, JSON serialization
2. **Service ID Generation**: Composite IDs with sanitization
3. **Multi-dimensional Filtering**: Company/project/env/module filters
4. **Bulk Operations**: Import/export with validation and error reporting
5. **Config Generation**: Dynamic Prometheus/Blackbox config snippets
6. **Relabel Configs**: Metadata to Prometheus label mapping

---

## API Compatibility

### Backward Compatibility

All existing endpoints remain functional:
- `/api/v1/blackbox` (basic CRUD) - **UNCHANGED**
- `/api/v1/blackbox/config/*` - **UNCHANGED**
- `/api/v1/services` - **UNCHANGED**
- `/api/v1/installer` - **UNCHANGED**

### New Enhanced Endpoints

Use `/api/v1/blackbox/enhanced` for new features without breaking existing clients.

---

## Security Considerations

1. **Namespace Validation**: All KV operations validate `skills/eye/` prefix
2. **User Tracking**: All mutations track the user performing the operation
3. **Audit Logging**: Complete audit trail of all changes
4. **Metadata Wrapping**: Prevents accidental data loss with version tracking

---

## Performance Optimizations

1. **Lazy KV Writes**: KV storage only activated when `ENABLE_KV_STORAGE = True`
2. **Batch Operations**: Group operations minimize API calls
3. **Caching**: Module lists cached in KV to reduce service queries
4. **Async Operations**: All I/O operations are async

---

## Conclusion

Phase 1 successfully implements:
- ✅ Standardized KV namespace structure
- ✅ Dual storage for blackbox targets
- ✅ Group management system
- ✅ Bulk operations support
- ✅ Complete audit logging
- ✅ UI settings persistence
- ✅ Migration utilities
- ✅ Full API coverage

The foundation is now ready for Phase 2 (Service Presets) and Phase 3 (Frontend Development).
