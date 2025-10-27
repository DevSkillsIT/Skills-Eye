"""
Phase 1 Implementation Test Script
Tests KV Manager, Blackbox Manager enhancements, and API endpoints
"""
import asyncio
import json
from core.kv_manager import KVManager
from core.blackbox_manager import BlackboxManager
from core.consul_manager import ConsulManager


async def test_kv_manager():
    """Test KV Manager operations"""
    print("\n" + "="*80)
    print("Testing KV Manager")
    print("="*80)

    kv = KVManager()

    # Test 1: Basic KV operations
    print("\n[Test 1] Basic KV Put/Get")
    test_key = "skills/cm/test/sample.json"
    test_value = {"message": "Hello from Phase 1", "version": "1.0"}

    success = await kv.put_json(test_key, test_value, metadata={"updated_by": "test_script"})
    print(f"  Put: {'✓' if success else '✗'} - {test_key}")

    retrieved = await kv.get_json(test_key)
    print(f"  Get: {'✓' if retrieved else '✗'} - {retrieved}")

    # Test 2: List keys
    print("\n[Test 2] List Keys")
    keys = await kv.list_keys("skills/cm/test/")
    print(f"  Found {len(keys)} keys under skills/cm/test/")
    for key in keys[:5]:  # Show first 5
        print(f"    - {key}")

    # Test 3: Audit logging
    print("\n[Test 3] Audit Logging")
    await kv.log_audit_event(
        action="TEST",
        resource_type="test_resource",
        resource_id="test-001",
        user="test_script",
        details={"test": True, "phase": 1}
    )
    print("  ✓ Audit event logged")

    # Test 4: Get recent audit events
    events = await kv.get_audit_events(resource_type="test_resource")
    print(f"  Found {len(events)} audit events for test_resource")

    # Test 5: UI Settings
    print("\n[Test 4] UI Settings")
    settings = {
        "theme": "dark",
        "page_size": 50,
        "columns": ["module", "name", "instance"]
    }
    await kv.put_ui_settings(settings, user="test_user")
    retrieved_settings = await kv.get_ui_settings(user="test_user")
    print(f"  ✓ Settings saved and retrieved: {retrieved_settings}")

    print("\n✓ KV Manager tests completed")


async def test_blackbox_groups():
    """Test Blackbox Group Management"""
    print("\n" + "="*80)
    print("Testing Blackbox Group Management")
    print("="*80)

    manager = BlackboxManager()

    # Test 1: Create a group
    print("\n[Test 1] Create Group")
    success, message = await manager.create_group(
        group_id="test-websites",
        name="Test Websites",
        filters={"company": "Test", "project": "web"},
        labels={"monitored_by": "test_script"},
        description="Testing group functionality",
        user="test_script"
    )
    print(f"  {'✓' if success else '✗'} - {message}")

    # Test 2: List groups
    print("\n[Test 2] List Groups")
    groups = await manager.list_groups()
    print(f"  Found {len(groups)} groups")
    for group in groups:
        print(f"    - {group.get('id')}: {group.get('name')}")

    # Test 3: Get specific group
    print("\n[Test 3] Get Group Details")
    group = await manager.get_group("test-websites")
    if group:
        print(f"  ✓ Retrieved group: {group.get('name')}")
        print(f"    Filters: {group.get('filters')}")
        print(f"    Labels: {group.get('labels')}")
    else:
        print("  ✗ Group not found")

    print("\n✓ Blackbox Group tests completed")


async def test_enhanced_targets():
    """Test Enhanced Blackbox Target Creation"""
    print("\n" + "="*80)
    print("Testing Enhanced Blackbox Targets")
    print("="*80)

    manager = BlackboxManager()

    # Test 1: Create enhanced target
    print("\n[Test 1] Create Enhanced Target")
    success, reason, detail = await manager.add_target(
        module="http_2xx",
        company="Test",
        project="Monitoring",
        env="dev",
        name="Google",
        instance="https://www.google.com",
        group="test-websites",
        labels={"region": "global", "priority": "high"},
        interval="15s",
        timeout="5s",
        enabled=True,
        notes="Google homepage monitoring",
        user="test_script"
    )

    if success:
        print(f"  ✓ Target created: {detail}")
    else:
        print(f"  ✗ Failed: {reason} - {detail}")

    # Test 2: List targets with group filter
    print("\n[Test 2] List Group Members")
    members = await manager.get_group_members("test-websites")
    print(f"  Found {len(members)} members in 'test-websites' group")
    for member in members:
        print(f"    - {member.get('id')}: {member.get('target')} ({member.get('enabled')})")

    # Test 3: Bulk enable/disable
    print("\n[Test 3] Bulk Disable Group")
    result = await manager.bulk_enable_disable(
        group_id="test-websites",
        enabled=False,
        user="test_script"
    )
    print(f"  ✓ Disabled {result['success_count']} targets")
    print(f"    Summary: {result}")

    print("\n✓ Enhanced Target tests completed")


async def test_kv_namespace_validation():
    """Test namespace security"""
    print("\n" + "="*80)
    print("Testing Namespace Validation")
    print("="*80)

    kv = KVManager()

    # Test 1: Valid namespace
    print("\n[Test 1] Valid Namespace")
    try:
        await kv.put_json("skills/cm/test/valid.json", {"test": "valid"})
        print("  ✓ Valid namespace accepted")
    except ValueError as e:
        print(f"  ✗ Unexpected error: {e}")

    # Test 2: Invalid namespace
    print("\n[Test 2] Invalid Namespace")
    try:
        await kv.put_json("invalid/path/test.json", {"test": "invalid"})
        print("  ✗ Invalid namespace was accepted (SECURITY ISSUE!)")
    except ValueError as e:
        print(f"  ✓ Invalid namespace rejected: {e}")

    print("\n✓ Namespace validation tests completed")


async def show_consul_status():
    """Show current Consul status"""
    print("\n" + "="*80)
    print("Consul Connection Status")
    print("="*80)

    consul = ConsulManager()

    try:
        # Test connection
        services = await consul.get_catalog_services()
        print(f"\n✓ Connected to Consul at {consul.host}:{consul.port}")
        print(f"  Services in catalog: {len(services)}")

        # Show datacenters
        datacenters = await consul.get_datacenters()
        print(f"  Datacenters: {', '.join(datacenters)}")

        # Show nodes
        nodes = await consul.get_nodes()
        print(f"  Nodes in cluster: {len(nodes)}")

        # Show blackbox targets
        blackbox_services = await consul.query_agent_services('Service == "blackbox_exporter"')
        print(f"  Blackbox targets: {len(blackbox_services)}")

    except Exception as e:
        print(f"\n✗ Error connecting to Consul: {e}")
        print("  Make sure Consul is running and configured correctly")


async def cleanup_test_data():
    """Clean up test data"""
    print("\n" + "="*80)
    print("Cleanup Test Data")
    print("="*80)

    kv = KVManager()
    manager = BlackboxManager()

    # Delete test keys
    print("\n[Cleanup] Removing test data...")

    # Delete test KV entries
    await kv.delete_key("skills/cm/test/sample.json")
    await kv.delete_key("skills/cm/test/valid.json")
    print("  ✓ Removed test KV entries")

    # Delete test target
    try:
        await manager.delete_target(
            module="http_2xx",
            company="Test",
            project="Monitoring",
            env="dev",
            name="Google",
            user="test_script"
        )
        print("  ✓ Removed test blackbox target")
    except:
        print("  - No test target to remove")

    print("\n✓ Cleanup completed")


async def main():
    """Run all tests"""
    print("\n" + "="*80)
    print("CONSUL MANAGER - PHASE 1 IMPLEMENTATION TESTS")
    print("="*80)

    # Show Consul status first
    await show_consul_status()

    # Run tests
    try:
        await test_kv_manager()
        await test_blackbox_groups()
        await test_enhanced_targets()
        await test_kv_namespace_validation()
    except Exception as e:
        print(f"\n✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()

    # Cleanup
    cleanup = input("\nCleanup test data? (y/n): ")
    if cleanup.lower() == 'y':
        await cleanup_test_data()

    print("\n" + "="*80)
    print("ALL TESTS COMPLETED")
    print("="*80)
    print("\nNext steps:")
    print("  1. Check the API documentation at http://localhost:5000/docs")
    print("  2. Test endpoints using curl or Postman")
    print("  3. Review IMPLEMENTATION_SUMMARY.md for details")
    print("  4. Start implementing Phase 2 (Service Presets)")
    print("\n")


if __name__ == "__main__":
    asyncio.run(main())
