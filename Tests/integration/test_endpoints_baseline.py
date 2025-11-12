#!/usr/bin/env python3
"""
BASELINE DE TESTES - ENDPOINTS

Testa endpoints atuais antes da migração.
Salva responses para comparação pós-migração.

Data: 2025-11-12
"""

import requests
import json
from datetime import datetime


def test_endpoints():
    """Testa endpoints atuais"""
    
    results = {
        "timestamp": datetime.now().isoformat(),
        "endpoints": {}
    }
    
    base_url = "http://localhost:5000"
    
    print("=" * 80)
    print("BASELINE DE ENDPOINTS - PRÉ-MIGRAÇÃO")
    print("=" * 80)
    
    # TEST 1: /api/v1/settings/naming-config
    print("\n🔍 TEST 1: GET /api/v1/settings/naming-config")
    try:
        response = requests.get(f"{base_url}/api/v1/settings/naming-config", timeout=5)
        results["endpoints"]["naming-config"] = {
            "url": f"{base_url}/api/v1/settings/naming-config",
            "status_code": response.status_code,
            "response": response.json() if response.status_code == 200 else None,
            "success": response.status_code == 200,
            "notes": "Config atual vem de .env"
        }
        
        if response.status_code == 200:
            data = response.json()
            print(f"  ✅ Status: {response.status_code}")
            print(f"  naming_strategy: {data.get('naming_strategy')}")
            print(f"  suffix_enabled: {data.get('suffix_enabled')}")
            print(f"  default_site: {data.get('default_site')}")
        else:
            print(f"  ❌ Status: {response.status_code}")
    
    except Exception as e:
        results["endpoints"]["naming-config"] = {
            "error": str(e),
            "success": False
        }
        print(f"  ❌ Erro: {e}")
    
    # TEST 2: /api/v1/metadata-fields/config/sites
    print("\n🔍 TEST 2: GET /api/v1/metadata-fields/config/sites")
    try:
        response = requests.get(f"{base_url}/api/v1/metadata-fields/config/sites", timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            sites = data.get("sites", [])
            
            results["endpoints"]["sites-config"] = {
                "url": f"{base_url}/api/v1/metadata-fields/config/sites",
                "status_code": response.status_code,
                "total_sites": len(sites),
                "sites": [
                    {
                        "code": s.get("code"),
                        "name": s.get("name"),
                        "is_default": s.get("is_default"),
                        "color": s.get("color"),
                        "cluster": s.get("cluster"),
                        "prometheus_instance": s.get("prometheus_instance")
                    }
                    for s in sites
                ],
                "success": True,
                "notes": "Sites atuais do KV"
            }
            
            print(f"  ✅ Status: {response.status_code}")
            print(f"  Total sites: {len(sites)}")
            for site in sites:
                print(f"    - {site.get('code')}: {site.get('name')} (color={site.get('color')}, default={site.get('is_default')})")
        else:
            results["endpoints"]["sites-config"] = {
                "status_code": response.status_code,
                "success": False
            }
            print(f"  ❌ Status: {response.status_code}")
    
    except Exception as e:
        results["endpoints"]["sites-config"] = {
            "error": str(e),
            "success": False
        }
        print(f"  ❌ Erro: {e}")
    
    # TEST 3: Verificar se /api/v1/settings/sites-config existe (NÃO DEVE EXISTIR AINDA)
    print("\n🔍 TEST 3: GET /api/v1/settings/sites-config (não deve existir ainda)")
    try:
        response = requests.get(f"{base_url}/api/v1/settings/sites-config", timeout=5)
        results["endpoints"]["sites-config-new"] = {
            "url": f"{base_url}/api/v1/settings/sites-config",
            "status_code": response.status_code,
            "exists": response.status_code == 200,
            "notes": "Este endpoint será criado na FASE 2"
        }
        
        if response.status_code == 404:
            print(f"  ✅ Endpoint não existe (esperado): {response.status_code}")
        else:
            print(f"  ⚠️  Endpoint existe: {response.status_code}")
    
    except Exception as e:
        results["endpoints"]["sites-config-new"] = {
            "error": str(e),
            "exists": False,
            "notes": "Endpoint não existe (esperado)"
        }
        print(f"  ✅ Endpoint não existe (esperado)")
    
    # Salvar resultados
    output_file = "BASELINE_ENDPOINTS.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print("\n" + "=" * 80)
    print("RESUMO")
    print("=" * 80)
    print(f"📄 Resultados salvos em: {output_file}")
    print("=" * 80)
    
    return results


if __name__ == "__main__":
    test_endpoints()
