## Front-end Roadmap (TenSunS parity)

### Layout & Navigation
- Adopt Ant Design Pro `BasicLayout` with sidebar items mirroring TenSunS: Dashboard, Consul Services, Blackbox Targets, Configuration.
- Provide global header widgets for Consul status (leader, health) using new `/api/v1/config/health` endpoint.

### Consul Services Management
- Replace current `Services.tsx` with Ant Design Pro `ProTable` listing service overview (`/api/v1/services?node_addr=ALL`) plus node filter.
- Add metadata filters (module/company/project/env) backed by `/api/v1/services/metadata/unique-values` and search endpoints.
- Implement drawer for instance details using `ConsulManager.get_service_instances`.
- Support create/edit modals using `ServiceCreateRequest` and update/delete endpoints, including batch actions.

### Blackbox Targets (new page)
- New `BlackboxTargets.tsx` page using `ProTable` + `Card` filters replicating module/company/project/env selectors.
- Integrate with `/api/v1/blackbox` endpoints for list, summary, create/update/delete.
- Provide import/export bar: CSV/XLSX upload mapped to `/api/v1/blackbox/import`, and export generating current dataset.
- Implement modals for create/edit with validation (module + target unique check) and friendly feedback.
- Add drawer showing Prometheus, Blackbox and alert rules snippets using `/api/v1/blackbox/config/*` with copy-to-clipboard actions.

### Shared Components & Utilities
- Create reusable `MetadataFilterBar` component reused by Services and Blackbox pages.
- Implement `useConsulQuery` hook (React Query) for standardized loading/error handling with optimistic updates.
- Add notification + audit log integration via WebSocket `/ws` to surface backend events (service created/import success).

### Testing & Tooling
- Configure Cypress (or Playwright) smoke tests for Services and Blackbox flows (list → create → delete).
- Add Storybook stories for filter bars and modals to accelerate UI iteration.
