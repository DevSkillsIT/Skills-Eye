#!/usr/bin/env python3
"""
Script para testar endpoints usados pelo frontend
Simula exatamente as chamadas que o React faz
"""

import requests
import json
from pprint import pprint

API_URL = "http://localhost:5000/api/v1"

def test_endpoint(name, endpoint, expected_keys=None):
    """Testa um endpoint e valida a resposta"""
    print(f"\n{'='*80}")
    print(f"🧪 TESTANDO: {name}")
    print(f"📍 URL: {API_URL}{endpoint}")
    print('='*80)
    
    try:
        response = requests.get(f"{API_URL}{endpoint}", timeout=5)
        print(f"✅ Status Code: {response.status_code}")
        print(f"✅ Content-Type: {response.headers.get('Content-Type')}")
        
        data = response.json()
        
        print(f"\n📦 Response Keys: {list(data.keys())}")
        
        if 'success' in data:
            print(f"   success: {data['success']}")
        
        if expected_keys:
            print(f"\n🔍 Validando campos esperados:")
            for key in expected_keys:
                value = data.get(key) if key in data else data.get('data', {}).get(key)
                if value is not None:
                    if isinstance(value, (list, dict)):
                        print(f"   ✅ {key}: {type(value).__name__} (len={len(value)})")
                    else:
                        print(f"   ✅ {key}: {value}")
                else:
                    print(f"   ❌ {key}: MISSING!")
        
        # Mostrar preview dos dados
        if 'data' in data:
            print(f"\n📄 data type: {type(data['data']).__name__}")
            if isinstance(data['data'], list):
                print(f"   items: {len(data['data'])}")
                if len(data['data']) > 0:
                    print(f"   first item keys: {list(data['data'][0].keys())[:10]}")
            elif isinstance(data['data'], dict):
                print(f"   dict keys: {list(data['data'].keys())}")
        
        return True
        
    except requests.exceptions.Timeout:
        print(f"❌ TIMEOUT após 5s")
        return False
    except requests.exceptions.ConnectionError as e:
        print(f"❌ CONNECTION ERROR: {e}")
        return False
    except json.JSONDecodeError as e:
        print(f"❌ JSON DECODE ERROR: {e}")
        print(f"   Response text: {response.text[:200]}")
        return False
    except Exception as e:
        print(f"❌ ERROR: {type(e).__name__}: {e}")
        return False

def main():
    print("""
╔══════════════════════════════════════════════════════════════════════════════╗
║                  SKILLS EYE - FRONTEND ENDPOINT TESTER                        ║
║                  Testa todos os endpoints usados pelo React                   ║
╚══════════════════════════════════════════════════════════════════════════════╝
    """)
    
    tests = [
        {
            'name': 'Categorization Rules (MonitoringRules.tsx)',
            'endpoint': '/categorization-rules',
            'expected_keys': ['success', 'version', 'total_rules', 'rules', 'default_category', 'categories']
        },
        {
            'name': 'Monitoring Data - Network Probes (DynamicMonitoringPage.tsx)',
            'endpoint': '/monitoring/data?category=network-probes',
            'expected_keys': ['success', 'category', 'data', 'total', 'available_fields']
        },
        {
            'name': 'Monitoring Data - Web Probes',
            'endpoint': '/monitoring/data?category=web-probes',
            'expected_keys': ['success', 'category', 'data', 'total', 'available_fields']
        },
        {
            'name': 'Monitoring Data - System Exporters',
            'endpoint': '/monitoring/data?category=system-exporters',
            'expected_keys': ['success', 'category', 'data', 'total', 'available_fields']
        },
        {
            'name': 'Metadata Fields (useMetadataFields hook)',
            'endpoint': '/metadata-fields/',
            'expected_keys': ['success', 'fields', 'total']
        },
    ]
    
    results = []
    for test in tests:
        success = test_endpoint(
            test['name'],
            test['endpoint'],
            test.get('expected_keys')
        )
        results.append((test['name'], success))
    
    print(f"\n\n{'='*80}")
    print("📊 RESUMO DOS TESTES")
    print('='*80)
    
    for name, success in results:
        status = "✅ PASSOU" if success else "❌ FALHOU"
        print(f"{status} - {name}")
    
    total = len(results)
    passed = sum(1 for _, s in results if s)
    failed = total - passed
    
    print(f"\n📈 Total: {total} | Passaram: {passed} | Falharam: {failed}")
    
    if failed == 0:
        print("\n🎉 TODOS OS TESTES PASSARAM! Frontend deveria funcionar normalmente.")
    else:
        print(f"\n⚠️  {failed} teste(s) falharam. Verificar endpoints.")

if __name__ == '__main__':
    main()
