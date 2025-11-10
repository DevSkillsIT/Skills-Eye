# Migration Guide - Upgrading to Phase 1

This guide helps you migrate from the original Consul Manager or TenSunS-based setup to the new Phase 1 implementation with standardized KV namespaces and enhanced features.

---

## Overview of Changes

### What's New?

1. **Standardized KV Namespace**: All app data moved to `skills/eye/*`
2. **Dual Storage**: Blackbox targets stored in both Services (for Prometheus) and KV (for advanced features)
3. **Group Management**: Organize targets into logical groups
4. **Audit Logging**: Complete audit trail of all operations
5. **Enhanced Metadata**: Custom labels, intervals, timeouts, enable/disable flags
6. **UI Preferences**: Per-user settings storage
7. **Bulk Operations**: Enable/disable multiple targets at once

### What's Compatible?

✅ **All existing APIs remain functional** - No breaking changes to core endpoints
✅ **Prometheus service discovery continues working** - Services are still registered the same way
✅ **Existing blackbox targets are preserved** - Just enhanced with additional features
✅ **Import/Export format unchanged** - CSV/XLSX import still works

---

## Migration Scenarios

### Scenario 1: Fresh Installation

If you're starting fresh, no migration needed! Just:

1. Start the backend: `cd backend && python app.py`
2. Access the API at http://localhost:5000
3. Create your first target using the enhanced endpoint

**Example:**

```bash
curl -X POST "http://localhost:5000/api/v1/blackbox/enhanced?user=admin" \
  -H "Content-Type: application/json" \
  -d '{
    "module": "http_2xx",
    "company": "MyCompany",
    "project": "Website",
    "env": "prod",
    "name": "Homepage",
    "instance": "https://mycompany.com",
    "group": "production-sites",
    "interval": "30s",
    "timeout": "10s",
    "enabled": true,
    "notes": "Main homepage"
  }'
```

---

### Scenario 2: Upgrading from Original Consul Manager

If you have existing blackbox targets registered as Consul services:

#### Step 1: Backup Your Data

```bash
# Export existing targets to CSV
curl "http://localhost:5000/api/v1/blackbox" > existing_targets.json

# Or use the UI Export button
```

#### Step 2: Run the Backend

```bash
cd backend
python app.py
```

#### Step 3: Enable Dual Storage (Optional)

Edit `backend/core/blackbox_manager.py`:

```python
ENABLE_KV_STORAGE = True  # This is the default
```

#### Step 4: Sync Existing Targets to KV

Option A: **Automatic** (via API):

```bash
# This will scan all existing blackbox services and create KV entries
curl -X POST "http://localhost:5000/api/v1/kv/sync-services?user=admin"
```

Option B: **Manual** (re-import):

```bash
# Export targets
curl "http://localhost:5000/api/v1/blackbox" > targets.json

# Re-import using enhanced endpoint (Python script)
python sync_to_kv.py
```

**sync_to_kv.py:**

```python
import asyncio
import json
from core.blackbox_manager import BlackboxManager

async def sync_services_to_kv():
    manager = BlackboxManager()

    # Get all existing services
    data = await manager.list_all_targets()
    services = data.get('services', [])

    print(f"Found {len(services)} existing targets")

    for service in services:
        meta = service.get('meta', {})

        # Create KV entry for each
        await manager.kv.put_blackbox_target(
            target_id=service['service_id'],
            target_data={
                "id": service['service_id'],
                "target": meta.get('instance'),
                "module": meta.get('module'),
                "labels": {
                    "company": meta.get('company'),
                    "project": meta.get('project'),
                    "env": meta.get('env'),
                    "name": meta.get('name')
                },
                "enabled": True,
                "interval": "30s",
                "timeout": "10s"
            },
            user="migration_script"
        )

        print(f"  ✓ Synced: {service['service_id']}")

    print(f"\n✓ Synced {len(services)} targets to KV")

if __name__ == "__main__":
    asyncio.run(sync_services_to_kv())
```

Run: `python sync_to_kv.py`

---

### Scenario 3: Migrating from TenSunS

If you have data in the old `ConsulManager/record/blackbox` KV namespace:

#### Step 1: Use the Migration API

```bash
curl -X POST "http://localhost:5000/api/v1/kv/migrate?old_prefix=ConsulManager/record/blackbox&user=admin"
```

**Response:**

```json
{
  "success": true,
  "message": "Migration completed",
  "summary": {
    "migrated": 150,
    "failed": 0,
    "total": 150
  }
}
```

#### Step 2: Verify Migration

```bash
# List migrated keys
curl "http://localhost:5000/api/v1/kv/list?prefix=skills/eye/blackbox/targets/"

# Get audit log of migration
curl "http://localhost:5000/api/v1/kv/audit/events?action=MIGRATE"
```

#### Step 3: Update Prometheus Configuration

If you have hardcoded KV paths in Prometheus config, update them:

**Before:**

```yaml
# Old TenSunS pattern (if using KV-based discovery)
file_sd_configs:
  - files:
    - /etc/prometheus/targets/blackbox_*.json
```

**After:**

```yaml
# Use consul_sd_configs (recommended)
consul_sd_configs:
  - server: '172.16.1.26:8500'
    token: '${CONSUL_TOKEN}'
    services: ['blackbox_exporter']
relabel_configs:
  - source_labels: [__meta_consul_service_metadata_instance]
    target_label: __param_target
  # ... (see full config in IMPLEMENTATION_SUMMARY.md)
```

---

## Feature Migration Guide

### Adding Groups to Existing Targets

#### Step 1: Create Groups

```bash
# Create a group for production sites
curl -X POST "http://localhost:5000/api/v1/blackbox/groups?user=admin" \
  -H "Content-Type: application/json" \
  -d '{
    "id": "prod-sites",
    "name": "Production Websites",
    "filters": {"env": "prod", "project": "web"},
    "description": "All production websites"
  }'
```

#### Step 2: Assign Targets to Groups

Option A: **Manually update each target** (via UI or API)

Option B: **Bulk update via script**:

```python
import asyncio
from core.blackbox_manager import BlackboxManager

async def assign_groups():
    manager = BlackboxManager()

    # Get all prod web targets
    targets = await manager.kv.list_blackbox_targets(
        filters={"labels": {"env": "prod", "project": "web"}}
    )

    # Assign to group
    for target in targets:
        target['group'] = 'prod-sites'
        await manager.kv.put_blackbox_target(
            target['id'],
            target,
            user="migration_script"
        )
        print(f"  ✓ Assigned {target['id']} to prod-sites")

asyncio.run(assign_groups())
```

---

## Configuration Updates

### Environment Variables

Add to your `.env` file:

```env
# Existing variables (keep these)
CONSUL_SERVER=172.16.1.26
CONSUL_PORT=8500
CONSUL_TOKEN=your-token-here

# New optional variables
KV_NAMESPACE=skills/eye        # Default namespace
ENABLE_AUDIT_LOG=true         # Enable audit logging
ENABLE_KV_STORAGE=true        # Enable dual storage mode
```

### Prometheus Configuration

Update your Prometheus `consul_sd_configs` to use the new metadata structure:

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

## Rollback Plan

If you need to rollback to the previous version:

### Step 1: Disable KV Storage

Edit `backend/core/blackbox_manager.py`:

```python
ENABLE_KV_STORAGE = False  # Disable dual storage
```

### Step 2: Services Remain Intact

All Consul services are still registered normally, so Prometheus continues working without interruption.

### Step 3: Export KV Data (Optional)

Before rolling back completely, export KV data for future use:

```bash
curl "http://localhost:5000/api/v1/kv/tree?prefix=skills/eye/" > kv_backup.json
```

---

## Testing Migration

### Validation Checklist

After migration, verify:

- [ ] All existing blackbox targets are still present
- [ ] Prometheus is still scraping targets correctly
- [ ] Grafana dashboards still show data
- [ ] New enhanced endpoints work
- [ ] Groups can be created and managed
- [ ] Audit log is recording events
- [ ] UI settings can be saved

### Test Script

Run the provided test script:

```bash
cd backend
python test_phase1.py
```

This will:
1. Test KV operations
2. Test group management
3. Test enhanced target creation
4. Test namespace validation
5. Show Consul connection status

---

## Common Issues & Solutions

### Issue 1: "Key outside namespace" Error

**Problem:** Trying to access KV keys outside `skills/eye/`

**Solution:** All app KV keys must start with `skills/eye/`. Use the API endpoints which enforce this.

### Issue 2: Targets Not Appearing in Prometheus

**Problem:** New targets not being discovered

**Solution:**
1. Check Consul service is registered: `curl http://localhost:8500/v1/agent/services | jq '.[] | select(.Service=="blackbox_exporter")'`
2. Verify Prometheus consul_sd_configs is correct
3. Check Prometheus targets page: http://localhost:9090/targets

### Issue 3: Duplicate Targets

**Problem:** Targets appear twice after migration

**Solution:**
- This is expected if you have both old and new registrations
- Use the deduplication endpoint: `POST /api/v1/blackbox/deduplicate`
- Or manually remove duplicates via UI

### Issue 4: Migration Fails Partially

**Problem:** Migration summary shows failed entries

**Solution:**
1. Check the audit log for details: `GET /api/v1/kv/audit/events?action=MIGRATE`
2. Manually inspect failed keys in old namespace
3. Re-run migration after fixing issues
4. Contact support with error details

---

## Support & Next Steps

### Documentation

- **API Docs**: http://localhost:5000/docs
- **Implementation Summary**: See `IMPLEMENTATION_SUMMARY.md`
- **Code Examples**: See test scripts in `backend/`

### Reporting Issues

If you encounter issues:

1. Check the logs: `backend/logs/app.log`
2. Run the test script: `python backend/test_phase1.py`
3. Export diagnostic info: `curl http://localhost:5000/api/v1/health/connectivity`
4. Report issue with logs and diagnostic output

### What's Next?

After successful migration:

1. **Organize targets into groups** for better management
2. **Review audit logs** to understand system changes
3. **Set up UI preferences** for your team
4. **Explore bulk operations** for efficiency
5. **Wait for Phase 2** (Service Presets) for even more features!

---

## Frequently Asked Questions

**Q: Will this break my existing setup?**
A: No. All existing APIs are backward compatible. Services continue to be registered the same way for Prometheus.

**Q: Do I have to use groups?**
A: No, groups are optional. Targets work fine without groups.

**Q: Can I disable KV storage?**
A: Yes, set `ENABLE_KV_STORAGE = False` in `blackbox_manager.py`.

**Q: How much KV storage will this use?**
A: Minimal. Each target takes ~500 bytes. 1000 targets = ~500 KB.

**Q: Can I migrate back to TenSunS?**
A: Yes, but you'll lose the new features (groups, audit, preferences, etc.). Export your data first.

**Q: Is there a UI for this?**
A: Frontend (Phase 3) is coming soon! For now, use the Swagger UI at /docs or curl commands.

---

## Migration Timeline

### Recommended Approach

**Week 1: Testing**
- Set up test environment
- Run migration on test data
- Validate all features work

**Week 2: Staging**
- Migrate staging environment
- Test with real workflows
- Train team on new features

**Week 3: Production**
- Backup production data
- Migrate during maintenance window
- Monitor for 24 hours
- Celebrate! 🎉

---

## Contact

For migration assistance:
- Check the GitHub Issues
- Review the documentation
- Run the test script for diagnostics

Good luck with your migration! 🚀
