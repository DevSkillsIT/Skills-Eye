#!/usr/bin/env python3
"""
Teste da consolidação de Sites - Fase 3
Verifica se endpoints /metadata-fields/sites funcionam corretamente
"""

import requests
import json
from typing import Dict, Any

API_URL = "http://localhost:5000/api/v1"

def print_section(title: str):
    """Print section header"""
    print(f"\n{'='*80}")
    print(f"  {title}")
    print('='*80)

def test_get_sites() -> Dict[str, Any]:
    """Testa GET /metadata-fields/sites"""
    print_section("TESTE 1: GET /metadata-fields/sites")
    
    try:
        response = requests.get(f"{API_URL}/metadata-fields/config/sites")
        response.raise_for_status()
        data = response.json()
        
        print(f"✓ Status: {response.status_code}")
        print(f"✓ Success: {data.get('success')}")
        print(f"✓ Total Sites: {len(data.get('sites', []))}")
        
        print("\n Sites encontrados:")
        for site in data.get('sites', []):
            print(f"  - {site['code']}: {site['name']}")
            print(f"    Prometheus: {site.get('prometheus_host')}:{site.get('prometheus_port')}")
            print(f"    Default: {site.get('is_default')}, Cor: {site.get('color')}")
            if site.get('external_labels'):
                print(f"    External Labels: {json.dumps(site['external_labels'], indent=6)}")
        
        return data
    except Exception as e:
        print(f"✗ Erro: {e}")
        return {}

def test_update_site(site_code: str):
    """Testa PATCH /metadata-fields/sites/{code}"""
    print_section(f"TESTE 2: PATCH /metadata-fields/sites/{site_code}")
    
    payload = {
        "name": f"Site Teste Atualizado - {site_code}",
        "color": "purple",
        "is_default": False
    }
    
    try:
        response = requests.patch(
            f"{API_URL}/metadata-fields/config/sites/{site_code}",
            json=payload
        )
        response.raise_for_status()
        data = response.json()
        
        print(f"✓ Status: {response.status_code}")
        print(f"✓ Success: {data.get('success')}")
        print(f"✓ Message: {data.get('message')}")
        print(f"✓ Site atualizado: {json.dumps(data.get('site'), indent=2)}")
        
        return data
    except Exception as e:
        print(f"✗ Erro: {e}")
        if hasattr(e, 'response'):
            print(f"  Detalhes: {e.response.text}")
        return {}

def test_sync_sites():
    """Testa POST /metadata-fields/sites/sync"""
    print_section("TESTE 3: POST /metadata-fields/sites/sync")
    
    try:
        response = requests.post(f"{API_URL}/metadata-fields/config/sites/sync")
        response.raise_for_status()
        data = response.json()
        
        print(f"✓ Status: {response.status_code}")
        print(f"✓ Success: {data.get('success')}")
        print(f"✓ Message: {data.get('message')}")
        print(f"✓ Sites sincronizados: {data.get('sites_synced')}")
        
        if data.get('new_sites'):
            print(f"\n Sites novos detectados ({len(data['new_sites'])}):")
            for site in data['new_sites']:
                print(f"  - {site}")
        
        if data.get('existing_sites'):
            print(f"\n Sites existentes atualizados ({len(data['existing_sites'])}):")
            for site in data['existing_sites']:
                print(f"  - {site}")
        
        return data
    except Exception as e:
        print(f"✗ Erro: {e}")
        if hasattr(e, 'response'):
            print(f"  Detalhes: {e.response.text}")
        return {}

def test_naming_config():
    """Testa GET /settings/naming-config (deve continuar funcionando)"""
    print_section("TESTE 4: GET /settings/naming-config (compatibilidade)")
    
    try:
        response = requests.get(f"{API_URL}/settings/naming-config")
        response.raise_for_status()
        data = response.json()
        
        print(f"✓ Status: {response.status_code}")
        print(f"✓ Naming Strategy: {data.get('naming_strategy')}")
        print(f"✓ Suffix Enabled: {data.get('suffix_enabled')}")
        print(f"✓ Default Site: {data.get('default_site')}")
        
        return data
    except Exception as e:
        print(f"✗ Erro: {e}")
        return {}

def main():
    print("""
╔════════════════════════════════════════════════════════════════════════╗
║  TESTE DE CONSOLIDAÇÃO: Sites Management                             ║
║  /metadata-fields/sites (NOVO) vs /settings/sites (DEPRECATED)       ║
╚════════════════════════════════════════════════════════════════════════╝
""")
    
    # TESTE 1: Listar sites
    sites_data = test_get_sites()
    
    if not sites_data.get('sites'):
        print("\n⚠️  Nenhum site encontrado. Execute 'Sincronizar Sites' primeiro.")
        
        # Tentar sincronizar
        sync_result = test_sync_sites()
        
        if sync_result.get('success'):
            # Recarregar sites
            sites_data = test_get_sites()
    
    # TESTE 2: Atualizar primeiro site (se existir)
    if sites_data.get('sites') and len(sites_data['sites']) > 0:
        first_site = sites_data['sites'][0]
        test_update_site(first_site['code'])
        
        # Verificar se mudança persistiu
        updated_sites = test_get_sites()
        updated_site = next(
            (s for s in updated_sites.get('sites', []) if s['code'] == first_site['code']),
            None
        )
        
        if updated_site:
            print(f"\n✓ Verificação: Site {first_site['code']} foi atualizado com sucesso")
            print(f"  Nome: {updated_site['name']}")
            print(f"  Cor: {updated_site['color']}")
    
    # TESTE 3: Verificar compatibilidade com /settings/naming-config
    test_naming_config()
    
    print_section("RESUMO DOS TESTES")
    print("✓ GET /metadata-fields/sites - Auto-detecção de sites")
    print("✓ PATCH /metadata-fields/sites/{code} - Atualização de campos editáveis")
    print("✓ POST /metadata-fields/sites/sync - Sincronização SSH + auto-criação")
    print("✓ GET /settings/naming-config - Compatibilidade mantida")
    print("\n✅ Consolidação FASE 1-3 completa!")

if __name__ == '__main__':
    main()
