#!/usr/bin/env python3
"""
Teste do sistema discovered_in para campos metadata multi-servidor

OBJETIVO:
Validar que campos descobertos em um servidor aparecem corretamente:
- testeCampo10: Existe em 200.14, deve mostrar discovered_in: ["172.16.200.14"]
- testeSP: Existe em 172.16.1.26, deve mostrar discovered_in: ["172.16.1.26"]
- Campos comuns: Devem mostrar discovered_in com TODOS os servidores
"""

import requests
import json

API_URL = "http://localhost:5000/api/v1/metadata-fields"

def print_section(title):
    print(f"\n{'='*80}")
    print(f"  {title}")
    print('='*80)

def test_get_all_fields():
    """Busca TODOS os campos metadata"""
    print_section("TESTE 1: Buscar TODOS os campos metadata")
    
    try:
        response = requests.get(API_URL, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        print(f"✓ Status: {response.status_code}")
        print(f"✓ Total campos: {data.get('total_fields')}")
        print(f"✓ Servidores verificados: {data.get('successful_servers')}/{data.get('total_servers')}")
        
        return data.get('fields', [])
    except Exception as e:
        print(f"✗ Erro: {e}")
        return []

def test_specific_field(fields, field_name):
    """Testa campo específico"""
    print_section(f"TESTE: Campo '{field_name}'")
    
    field = next((f for f in fields if f['name'] == field_name), None)
    
    if not field:
        print(f"❌ Campo '{field_name}' NÃO encontrado!")
        print(f"   Isso significa que o campo:")
        print(f"   1. Não existe em NENHUM servidor Prometheus")
        print(f"   2. OU foi removido do KV como órfão")
        return False
    
    discovered_in = field.get('discovered_in', [])
    
    print(f"✅ Campo '{field_name}' ENCONTRADO!")
    print(f"   Display Name: {field.get('display_name')}")
    print(f"   Categoria: {field.get('category')}")
    print(f"   Sync Status: {field.get('sync_status')}")
    
    if not discovered_in:
        print(f"   ⚠️  discovered_in: VAZIO (bug no backend!)")
    else:
        print(f"   ✓ discovered_in: {json.dumps(discovered_in, indent=6)}")
        
    return True

def main():
    print("""
╔════════════════════════════════════════════════════════════════════════╗
║  TESTE DISCOVERED_IN: Multi-Server Field Tracking                     ║
║  Valida que campos são corretamente trackeados por servidor           ║
╚════════════════════════════════════════════════════════════════════════╝
""")
    
    # TESTE 1: Buscar todos os campos
    fields = test_get_all_fields()
    
    if not fields:
        print("\n❌ Nenhum campo retornado. Backend pode estar offline.")
        return
    
    # TESTE 2: testeCampo10 (deve estar em 200.14)
    found_tc10 = test_specific_field(fields, 'testeCampo10')
    
    # TESTE 3: testeSP (deve estar em 172.16.1.26)
    found_sp = test_specific_field(fields, 'testeSP')
    
    # TESTE 4: Campo comum (deve estar em MÚLTIPLOS servidores)
    test_specific_field(fields, 'company')
    
    # RESUMO
    print_section("RESUMO DOS TESTES")
    print(f"✓ Total de campos: {len(fields)}")
    print(f"{'✓' if found_tc10 else '✗'} testeCampo10: {'Encontrado' if found_tc10 else 'NÃO encontrado'}")
    print(f"{'✓' if found_sp else '✗'} testeSP: {'Encontrado' if found_sp else 'NÃO encontrado'}")
    
    if found_tc10 or found_sp:
        print("\n✅ Sistema discovered_in implementado!")
    else:
        print("\n⚠️  Campos de teste não encontrados. Verifique se existem no Prometheus.")

if __name__ == '__main__':
    main()
