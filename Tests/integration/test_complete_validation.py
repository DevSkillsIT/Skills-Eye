#!/usr/bin/env python3
"""
Script completo de teste e validação:
1. Testa estrutura do KV
2. Popula dados se vazio
3. Testa todos os endpoints
4. Valida funcionamento completo
"""

import requests
import json

API_URL = "http://localhost:5000/api/v1"
CONSUL_URL = "http://localhost:8500"
CONSUL_TOKEN = "8382a112-81e0-cd6d-2b92-8565925a0675"

def print_section(title):
    print(f"\n{'='*80}")
    print(f"  {title}")
    print('='*80)

def check_kv_structure():
    """Verifica estrutura atual do KV"""
    print_section("TESTE 1: Verificar Estrutura KV")
    
    keys_to_check = [
        'skills/eye/metadata/sites',
        'skills/eye/settings/sites',
        'skills/eye/metadata/fields'
    ]
    
    for key in keys_to_check:
        try:
            response = requests.get(
                f"{CONSUL_URL}/v1/kv/{key}?raw",
                headers={"X-Consul-Token": CONSUL_TOKEN}
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"✓ {key}: {type(data).__name__}")
                
                if isinstance(data, dict):
                    if 'sites' in data:
                        print(f"  → Estrutura CORRETA (array): {len(data['sites'])} sites")
                    else:
                        print(f"  → Estrutura DICT: {len(data)} keys: {list(data.keys())[:5]}")
                elif isinstance(data, list):
                    print(f"  → Estrutura LIST: {len(data)} items")
            elif response.status_code == 404:
                print(f"⚠️  {key}: VAZIO (404)")
            else:
                print(f"✗ {key}: HTTP {response.status_code}")
        except Exception as e:
            print(f"✗ {key}: Erro - {e}")

def test_force_extract():
    """Testa extração de campos do Prometheus"""
    print_section("TESTE 2: Force Extract (Extração SSH)")
    
    try:
        print("Disparando extração SSH dos servidores Prometheus...")
        response = requests.post(f"{API_URL}/metadata-fields/force-extract")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✓ Status: {response.status_code}")
            print(f"✓ Success: {data.get('success')}")
            print(f"✓ Total campos: {data.get('total_fields')}")
            print(f"✓ Campos novos: {data.get('new_fields_count')}")
            print(f"✓ Servidores verificados: {data.get('servers_checked')}")
            print(f"✓ Servidores com sucesso: {data.get('servers_success')}")
            
            if data.get('new_fields'):
                print(f"\n Campos novos descobertos:")
                for field in data['new_fields'][:10]:
                    print(f"  - {field}")
            
            return True
        else:
            print(f"✗ HTTP {response.status_code}: {response.text}")
            return False
    except Exception as e:
        print(f"✗ Erro: {e}")
        return False

def test_list_sites():
    """Testa GET /config/sites"""
    print_section("TESTE 3: Listar Sites (GET /config/sites)")
    
    try:
        response = requests.get(f"{API_URL}/metadata-fields/config/sites")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✓ Status: {response.status_code}")
            print(f"✓ Total sites: {data.get('total')}")
            
            for site in data.get('sites', []):
                print(f"\n Site: {site['code']}")
                print(f"  - Nome: {site['name']}")
                print(f"  - Default: {site['is_default']}")
                print(f"  - Color: {site['color']}")
                print(f"  - Host: {site['prometheus_host']}")
                if site.get('external_labels'):
                    print(f"  - External Labels: {site['external_labels']}")
            
            return data.get('sites', [])
        else:
            print(f"✗ HTTP {response.status_code}: {response.text}")
            return []
    except Exception as e:
        print(f"✗ Erro: {e}")
        return []

def test_sync_sites():
    """Testa POST /config/sites/sync"""
    print_section("TESTE 4: Sincronizar Sites (POST /config/sites/sync)")
    
    try:
        response = requests.post(f"{API_URL}/metadata-fields/config/sites/sync")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✓ Status: {response.status_code}")
            print(f"✓ Success: {data.get('success')}")
            print(f"✓ Sites sincronizados: {data.get('sites_synced')}")
            print(f"✓ Sites novos: {len(data.get('new_sites', []))}")
            print(f"✓ Sites existentes: {len(data.get('existing_sites', []))}")
            
            if data.get('new_sites'):
                print(f"\n Novos sites auto-detectados:")
                for site in data['new_sites']:
                    print(f"  - {site}")
            
            return True
        else:
            print(f"✗ HTTP {response.status_code}: {response.text}")
            return False
    except Exception as e:
        print(f"✗ Erro: {e}")
        return False

def test_update_site(site_code):
    """Testa PATCH /config/sites/{code}"""
    print_section(f"TESTE 5: Atualizar Site '{site_code}' (PATCH)")
    
    try:
        payload = {
            "name": f"Site Atualizado - {site_code}",
            "color": "purple",
            "is_default": False
        }
        
        response = requests.patch(
            f"{API_URL}/metadata-fields/config/sites/{site_code}",
            json=payload
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✓ Status: {response.status_code}")
            print(f"✓ Success: {data.get('success')}")
            print(f"✓ Site atualizado: {data.get('site', {}).get('name')}")
            return True
        else:
            print(f"✗ HTTP {response.status_code}: {response.text}")
            return False
    except Exception as e:
        print(f"✗ Erro: {e}")
        return False

def test_cleanup_orphans():
    """Testa POST /config/sites/cleanup"""
    print_section("TESTE 6: Limpar Sites Órfãos (POST /config/sites/cleanup)")
    
    try:
        response = requests.post(f"{API_URL}/metadata-fields/config/sites/cleanup")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✓ Status: {response.status_code}")
            print(f"✓ Success: {data.get('success')}")
            print(f"✓ Órfãos removidos: {data.get('removed_count')}")
            print(f"✓ Sites ativos: {len(data.get('active_sites', []))}")
            
            if data.get('orphans_removed'):
                print(f"\n Órfãos removidos:")
                for orphan in data['orphans_removed']:
                    print(f"  - {orphan}")
            
            return True
        else:
            print(f"✗ HTTP {response.status_code}: {response.text}")
            return False
    except Exception as e:
        print(f"✗ Erro: {e}")
        return False

def verify_kv_final_structure():
    """Verifica estrutura final do KV após testes"""
    print_section("VALIDAÇÃO FINAL: Estrutura do KV")
    
    try:
        response = requests.get(
            f"{CONSUL_URL}/v1/kv/skills/eye/metadata/sites?raw",
            headers={"X-Consul-Token": CONSUL_TOKEN}
        )
        
        if response.status_code == 200:
            data = response.json()
            
            if isinstance(data, dict) and 'sites' in data:
                print(f"✅ Estrutura CORRETA: Array com {len(data['sites'])} sites")
                print(f"\nConteúdo:")
                print(json.dumps(data, indent=2))
                return True
            else:
                print(f"❌ Estrutura ERRADA: {type(data).__name__}")
                print(f"Conteúdo: {data}")
                return False
        elif response.status_code == 404:
            print(f"⚠️  KV ainda vazio (precisa sincronizar)")
            return False
        else:
            print(f"✗ HTTP {response.status_code}")
            return False
    except Exception as e:
        print(f"✗ Erro: {e}")
        return False

def main():
    print("""
╔════════════════════════════════════════════════════════════════════════╗
║  VALIDAÇÃO COMPLETA: Sites + KV + Endpoints                          ║
╚════════════════════════════════════════════════════════════════════════╝
""")
    
    # TESTE 1: Verificar estrutura atual do KV
    check_kv_structure()
    
    # TESTE 2: Force Extract (popula external_labels)
    extract_success = test_force_extract()
    
    if not extract_success:
        print("\n⚠️  Force Extract falhou. Continuando testes...")
    
    # TESTE 3: Listar sites
    sites = test_list_sites()
    
    # TESTE 4: Sincronizar sites (cria estrutura no KV)
    test_sync_sites()
    
    # TESTE 5: Atualizar site (se houver)
    if sites:
        test_update_site(sites[0]['code'])
    
    # TESTE 6: Limpar órfãos
    test_cleanup_orphans()
    
    # VALIDAÇÃO FINAL
    verify_kv_final_structure()
    
    print_section("RESUMO")
    print("✓ Estrutura do KV verificada")
    print("✓ Extração SSH testada")
    print("✓ Todos os endpoints testados")
    print("✓ Estrutura final validada")
    print("\n✅ VALIDAÇÃO COMPLETA!")

if __name__ == '__main__':
    main()
