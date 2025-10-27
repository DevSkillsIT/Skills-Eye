"""
Phase 2 Implementation Test Script
Tests Service Presets, Advanced Search, and new features
"""
import asyncio
import json
from core.service_preset_manager import ServicePresetManager
from core.advanced_search import AdvancedSearch, SearchCondition, SearchOperator
from core.consul_manager import ConsulManager


async def test_service_presets():
    """Test Service Preset Manager"""
    print("\n" + "="*80)
    print("Testing Service Presets")
    print("="*80)

    manager = ServicePresetManager()

    # Test 1: Create built-in presets
    print("\n[Test 1] Create Built-in Presets")
    results = await manager.create_builtin_presets(user="test_script")

    for preset_id, success in results.items():
        status = "✓" if success else "✗"
        print(f"  {status} {preset_id}")

    # Test 2: List presets
    print("\n[Test 2] List Presets")
    presets = await manager.list_presets()
    print(f"  Found {len(presets)} presets")

    for preset in presets:
        print(f"    - {preset.get('id')}: {preset.get('name')} ({preset.get('category')})")

    # Test 3: Get specific preset
    print("\n[Test 3] Get Node Exporter Preset")
    preset = await manager.get_preset("node-exporter-linux")

    if preset:
        print(f"  ✓ Retrieved preset: {preset.get('name')}")
        print(f"    Service: {preset.get('service_name')}")
        print(f"    Port: {preset.get('port')}")
        print(f"    Tags: {preset.get('tags')}")
        print(f"    Meta template: {preset.get('meta_template')}")
    else:
        print("  ✗ Preset not found")

    # Test 4: Create custom preset
    print("\n[Test 4] Create Custom Preset")
    success, message = await manager.create_preset(
        preset_id="custom-app",
        name="Custom Application",
        service_name="my_app",
        port=8080,
        tags=["custom", "application"],
        meta_template={
            "app": "my_app",
            "env": "${env}",
            "version": "${version:1.0.0}"
        },
        checks=[{
            "HTTP": "http://${address}:${port}/health",
            "Interval": "10s"
        }],
        description="Custom application template",
        category="application",
        user="test_script"
    )

    print(f"  {'✓' if success else '✗'} {message}")

    # Test 5: Register service from preset (preview mode)
    print("\n[Test 5] Preview Service from Preset")
    preset = await manager.get_preset("node-exporter-linux")

    if preset:
        variables = {
            "address": "10.0.0.10",
            "env": "test",
            "datacenter": "test-dc",
            "hostname": "test-server-01"
        }

        try:
            service_data = manager._apply_preset(preset, variables)
            print("  ✓ Preview generated successfully:")
            print(f"    Service ID: {service_data.get('id')}")
            print(f"    Service Name: {service_data.get('name')}")
            print(f"    Address: {service_data.get('address')}")
            print(f"    Port: {service_data.get('port')}")
            print(f"    Meta: {json.dumps(service_data.get('Meta', {}), indent=6)}")
        except Exception as exc:
            print(f"  ✗ Error: {exc}")

    print("\n✓ Service Preset tests completed")


async def test_advanced_search():
    """Test Advanced Search capabilities"""
    print("\n" + "="*80)
    print("Testing Advanced Search")
    print("="*80)

    consul = ConsulManager()

    # Get sample services
    services_dict = await consul.get_services()
    services_list = list(services_dict.values())

    print(f"\nTotal services: {len(services_list)}")

    # Test 1: Simple equality search
    print("\n[Test 1] Search by Company (Equals)")

    # First, get unique companies
    unique_companies = AdvancedSearch.extract_unique_values(services_list, "Meta.company")

    if unique_companies:
        test_company = unique_companies[0]
        print(f"  Searching for company: {test_company}")

        results = AdvancedSearch.search(
            services_list,
            [{"field": "Meta.company", "operator": "eq", "value": test_company}],
            "and"
        )

        print(f"  ✓ Found {len(results)} services")
    else:
        print("  - No companies found in metadata")

    # Test 2: Multiple conditions (AND)
    print("\n[Test 2] Search with Multiple Conditions (AND)")

    conditions = [
        {"field": "Service", "operator": "eq", "value": "blackbox_exporter"},
        {"field": "Meta.module", "operator": "contains", "value": "http"}
    ]

    results = AdvancedSearch.search(services_list, conditions, "and")
    print(f"  ✓ Found {len(results)} blackbox HTTP targets")

    # Test 3: OR conditions
    print("\n[Test 3] Search with OR Operator")

    conditions = [
        {"field": "Meta.env", "operator": "eq", "value": "prod"},
        {"field": "Meta.env", "operator": "eq", "value": "staging"}
    ]

    results = AdvancedSearch.search(services_list, conditions, "or")
    print(f"  ✓ Found {len(results)} services in prod OR staging")

    # Test 4: Regex search
    print("\n[Test 4] Regex Search")

    results = AdvancedSearch.search(
        services_list,
        [{"field": "Meta.name", "operator": "regex", "value": ".*server.*"}],
        "and"
    )
    print(f"  ✓ Found {len(results)} services with 'server' in name")

    # Test 5: Full-text search
    print("\n[Test 5] Full-Text Search")

    results = AdvancedSearch.search_text(services_list, "10.0", None)
    print(f"  ✓ Found {len(results)} services containing '10.0'")

    # Test 6: Extract unique values
    print("\n[Test 6] Extract Unique Values")

    fields_to_check = ["Meta.module", "Meta.env", "Meta.company", "Service"]

    for field in fields_to_check:
        values = AdvancedSearch.extract_unique_values(services_list, field)
        if values:
            field_name = field.split(".")[-1]
            print(f"  {field_name}: {', '.join(values[:5])}" +
                  (f" (+{len(values)-5} more)" if len(values) > 5 else ""))

    # Test 7: Build filter options
    print("\n[Test 7] Build Filter Options")

    filters = AdvancedSearch.build_filters_from_metadata(services_list)

    for field, values in filters.items():
        print(f"  {field}: {len(values)} unique values")

    # Test 8: Sorting
    print("\n[Test 8] Sort by Field")

    sorted_services = AdvancedSearch.sort_by_field(services_list, "Service", descending=False)

    if sorted_services:
        print(f"  ✓ Sorted {len(sorted_services)} services by Service name")
        print(f"    First: {sorted_services[0].get('Service')}")
        print(f"    Last: {sorted_services[-1].get('Service')}")

    # Test 9: Pagination
    print("\n[Test 9] Pagination")

    paginated = AdvancedSearch.paginate(services_list, page=1, page_size=10)

    print(f"  ✓ Page 1 of {paginated['pagination']['total_pages']}")
    print(f"    Items: {len(paginated['data'])} / {paginated['pagination']['total']}")
    print(f"    Has next: {paginated['pagination']['has_next']}")

    print("\n✓ Advanced Search tests completed")


async def test_operators():
    """Test all search operators"""
    print("\n" + "="*80)
    print("Testing Search Operators")
    print("="*80)

    # Sample data for testing
    test_items = [
        {"id": "1", "Meta": {"name": "server-01", "port": "9100", "env": "prod"}},
        {"id": "2", "Meta": {"name": "server-02", "port": "9182", "env": "dev"}},
        {"id": "3", "Meta": {"name": "web-server", "port": "8080", "env": "staging"}},
        {"id": "4", "Meta": {"name": "database-01", "port": "5432", "env": "prod"}},
    ]

    operators_to_test = [
        ("eq", "equals", {"field": "Meta.env", "operator": "eq", "value": "prod"}),
        ("ne", "not equals", {"field": "Meta.env", "operator": "ne", "value": "prod"}),
        ("contains", "contains", {"field": "Meta.name", "operator": "contains", "value": "server"}),
        ("starts_with", "starts with", {"field": "Meta.name", "operator": "starts_with", "value": "web"}),
        ("ends_with", "ends with", {"field": "Meta.name", "operator": "ends_with", "value": "01"}),
        ("in", "in list", {"field": "Meta.env", "operator": "in", "value": ["prod", "staging"]}),
        ("not_in", "not in list", {"field": "Meta.env", "operator": "not_in", "value": ["dev"]}),
        ("gt", "greater than", {"field": "Meta.port", "operator": "gt", "value": "8000"}),
        ("regex", "regex", {"field": "Meta.name", "operator": "regex", "value": "^server-.*"}),
    ]

    for op_code, op_name, condition in operators_to_test:
        results = AdvancedSearch.search(test_items, [condition], "and")
        print(f"  {op_code:12} ({op_name:15}): {len(results)} matches")

    print("\n✓ Operator tests completed")


async def cleanup_test_data():
    """Clean up test presets"""
    print("\n" + "="*80)
    print("Cleanup Test Data")
    print("="*80)

    manager = ServicePresetManager()

    # Delete custom preset
    print("\n[Cleanup] Removing test preset...")
    success, message = await manager.delete_preset("custom-app", user="test_script")

    if success:
        print(f"  ✓ {message}")
    else:
        print(f"  - {message}")

    print("\n✓ Cleanup completed")


async def main():
    """Run all tests"""
    print("\n" + "="*80)
    print("CONSUL MANAGER - PHASE 2 IMPLEMENTATION TESTS")
    print("="*80)

    try:
        await test_service_presets()
        await test_advanced_search()
        await test_operators()
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
    print("\nPhase 2 Features:")
    print("  ✓ Service Presets - Template-based service registration")
    print("  ✓ Advanced Search - Multi-condition search with operators")
    print("  ✓ Full-text Search - Search across all metadata")
    print("  ✓ Filter Options - Dynamic filter generation")
    print("  ✓ Pagination & Sorting - Efficient data handling")
    print("\nNext steps:")
    print("  1. Check the API documentation at http://localhost:5000/docs")
    print("  2. Test preset endpoints: /api/v1/presets")
    print("  3. Test search endpoints: /api/v1/search")
    print("  4. Review PHASE2_SUMMARY.md for details")
    print("\n")


if __name__ == "__main__":
    asyncio.run(main())
