# Consul Manager Web Application - AI Developer Guide

## Project Overview
Full-stack Consul service management platform with modern React frontend and FastAPI backend. Focuses on Blackbox Exporter monitoring, service discovery, and configuration management through a centralized web interface.

## Architecture Essentials

### Backend Structure (FastAPI + Async)
- **Core Layer**: `backend/core/` contains business logic managers (`consul_manager.py`, `kv_manager.py`, `service_preset_manager.py`)
- **API Layer**: `backend/api/` contains FastAPI routers with clear separation of concerns
- **Dual Storage**: Services stored in both Consul's service registry AND KV store under `skills/cm/` namespace
- **Async Throughout**: All Consul operations use `httpx` async client, avoid sync patterns

### Frontend Structure (React 19 + TypeScript)
- **Ant Design Pro**: Use `@ant-design/pro-components` for tables, forms, layouts (already configured)
- **Centralized API**: All backend calls go through `frontend/src/services/api.ts` with TypeScript interfaces
- **Page-per-Feature**: Each major feature has dedicated page in `frontend/src/pages/`
- **Portuguese Interface**: All user-facing text in PT-BR, component labels, messages, etc.

### Key Namespace Patterns
```
skills/cm/blackbox/targets/<id>.json     # Blackbox monitoring targets
skills/cm/blackbox/groups/<id>.json      # Logical groupings  
skills/cm/services/presets/<id>.json     # Service templates
skills/cm/audit/YYYY/MM/DD/<ts>.json     # Audit trail
```

## Development Workflows

### Local Development
```bash
# Backend: cd backend && python app.py (port 5000)
# Frontend: cd frontend && npm run dev (port 8081)
# Use start_dev.bat for Windows development setup
```

### Service Registration Patterns
```python
# Always include required metadata fields
Meta = {
    "module": "icmp|http_2xx|etc",      # Required: monitoring type
    "company": "Company Name",           # Required: organization
    "project": "Project Name",           # Required: project scope  
    "env": "prod|dev|staging",          # Required: environment
    "name": "Service Display Name",      # Required: human name
    "instance": "IP or URL target"       # Required: monitoring target
}
```

### Advanced Search Implementation
- **12 Operators**: eq, ne, contains, regex, in, not_in, starts_with, ends_with, gt, lt, gte, lte
- **Nested Fields**: Use dot notation like `Meta.company`, `Meta.env` for deep property access
- **Combined Logic**: Support AND/OR operations with multiple conditions
- **Field Validation**: All search fields must exist in the service metadata structure

## Component Patterns

### API Integration
```typescript
// Use pre-defined interfaces from api.ts
import { consulAPI, ServiceCreatePayload, BlackboxTargetPayload } from '../services/api';

// Always handle async operations with proper error handling
try {
  const response = await consulAPI.createService(payload);
  // Handle success
} catch (error) {
  // Handle error with user-friendly messages
}
```

### Form Validation
- **Required Fields**: Always validate module, company, project, env, name, instance
- **Instance Format**: Validate IP addresses for ICMP, URLs for HTTP modules
- **Portuguese Messages**: Error messages and validation feedback in Portuguese

### Table Components
```typescript
// Use ProTable from Ant Design Pro for consistency
import { ProTable } from '@ant-design/pro-components';

// Include column selector and metadata filtering
// Follow existing patterns in Services.tsx, BlackboxTargets.tsx
```

## Integration Points

### Consul Client Configuration
- **Multi-Node Support**: Use `node_addr` parameter to target specific Consul instances
- **Token Management**: Handle ACL tokens securely, never expose in client responses
- **Retry Logic**: Implement exponential backoff for network operations

### WebSocket Integration
- **Real-time Logs**: Use `/ws/installer/{id}` for installation progress
- **Connection Management**: Handle reconnection and error states
- **Message Format**: Structured JSON with log level and timestamp

### Legacy TenSunS Integration
- **Migration Path**: Support importing from old `blackbox/` namespace
- **Config Generation**: Maintain Prometheus config compatibility
- **Module Mapping**: Preserve existing blackbox module configurations

## Testing & Validation

### Backend Testing
```bash
cd backend
python test_phase1.py  # KV and dual storage
python test_phase2.py  # Presets and advanced search
```

### Data Validation
- **Duplicate Prevention**: Check service ID uniqueness across all Consul nodes
- **Metadata Consistency**: Enforce required fields before service registration
- **Audit Logging**: All create/update/delete operations must log to audit trail

## Code Style Guidelines

### Python (Backend)
- **Type Hints**: Always use typing annotations for parameters and returns
- **Async/Await**: Prefer async patterns for all I/O operations
- **Error Handling**: Use specific HTTPException with appropriate status codes
- **Docstrings**: Document complex business logic and API endpoints

### TypeScript (Frontend)
- **Interface Definitions**: Export all interfaces from `api.ts` for reuse
- **Component Props**: Use destructuring with TypeScript interfaces
- **State Management**: Use React hooks with proper TypeScript typing
- **Error Boundaries**: Handle API errors gracefully with user feedback

## Security Considerations
- **Namespace Isolation**: All KV operations must use `skills/cm/` prefix
- **Input Validation**: Sanitize all user inputs before Consul operations
- **Token Protection**: Never log or expose Consul tokens in responses
- **CORS Configuration**: Maintain restrictive CORS policy for production

## Performance Patterns
- **Batch Operations**: Use bulk endpoints for multiple service operations
- **Caching Strategy**: Cache metadata unique values for dropdown populations
- **Pagination**: Implement server-side pagination for large datasets
- **Debounced Search**: Debounce user input for real-time search features