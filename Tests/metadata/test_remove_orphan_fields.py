#!/usr/bin/env python3
"""
Teste completo do endpoint /metadata-fields/remove-orphans
Valida se a remoção de campos órfãos funciona corretamente
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

def test_list_fields():
    """Lista todos os campos metadata atuais"""
    print_section("PASSO 1: Listar Campos Metadata Atuais")
    
    try:
        response = requests.get(f"{API_URL}/metadata-fields/")
        response.raise_for_status()
        data = response.json()
        
        print(f"✓ Status: {response.status_code}")
        print(f"✓ Success: {data.get('success')}")
        print(f"✓ Total de campos: {len(data.get('fields', []))}")
        print(f"✓ Servidores: {data.get('successful_servers')}/{data.get('total_servers')}")
        
        fields = data.get('fields', [])
        
        if fields:
            print(f"\n📋 Primeiros 10 campos:")
            for field in fields[:10]:
                print(f"  - {field['name']}: {field.get('display_name', 'N/A')}")
        
        return data
    except Exception as e:
        print(f"✗ Erro: {e}")
        return {}

def test_create_orphan_field():
    """Cria um campo órfão de teste manualmente via POST /add-to-kv"""
    print_section("PASSO 2: Criar Campo Órfão de Teste")
    
    test_field = {
        "name": "test_orphan_field_12345",
        "display_name": "Campo Órfão de Teste",
        "source_label": "__meta_consul_test",
        "description": "Campo criado automaticamente para teste de remoção de órfãos",
        "category": "extra",
        "required": False,
        "show_in_table": False,
        "show_in_services": False,
        "show_in_exporters": False,
        "show_in_blackbox": False,
        "order": 9999
    }
    
    print(f"📝 Criando campo de teste: '{test_field['name']}'")
    
    try:
        payload = {
            "field_names": [test_field["name"]],
            "fields_data": [test_field]
        }
        
        response = requests.post(
            f"{API_URL}/metadata-fields/add-to-kv",
            json=payload
        )
        response.raise_for_status()
        data = response.json()
        
        print(f"✓ Status: {response.status_code}")
        print(f"✓ Success: {data.get('success')}")
        print(f"✓ Mensagem: {data.get('message')}")
        print(f"✓ Campos adicionados: {data.get('total_added')}")
        print(f"✓ Campos pulados: {data.get('total_skipped')}")
        
        if data.get('total_added', 0) > 0:
            print(f"\n✅ Campo órfão '{test_field['name']}' criado com sucesso!")
            return test_field['name']
        elif data.get('total_skipped', 0) > 0:
            print(f"\n⚠️  Campo já existe no KV, será usado para teste de remoção")
            return test_field['name']
        else:
            print(f"\n✗ Falha ao criar campo de teste")
            return None
            
    except Exception as e:
        print(f"✗ Erro: {e}")
        if hasattr(e, 'response') and e.response:
            print(f"  Resposta: {e.response.text}")
        return None

def test_verify_orphan_exists(field_name: str):
    """Verifica se o campo órfão foi realmente criado"""
    print_section(f"PASSO 3: Verificar se Campo Órfão '{field_name}' Existe")
    
    try:
        response = requests.get(f"{API_URL}/metadata-fields/{field_name}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✓ Status: {response.status_code}")
            print(f"✓ Campo encontrado: {data.get('field', {}).get('name')}")
            print(f"✓ Display Name: {data.get('field', {}).get('display_name')}")
            print(f"\n✅ Campo órfão confirmado no KV!")
            return True
        else:
            print(f"✗ Status: {response.status_code}")
            print(f"✗ Campo NÃO encontrado (pode ter sido criado mas não está visível)")
            return False
            
    except Exception as e:
        print(f"✗ Erro: {e}")
        return False

def test_remove_orphan(field_name: str):
    """Testa a remoção do campo órfão"""
    print_section(f"PASSO 4: Remover Campo Órfão '{field_name}'")
    
    try:
        payload = {"field_names": [field_name]}
        
        print(f"🗑️  Enviando requisição de remoção...")
        print(f"   POST /metadata-fields/remove-orphans")
        print(f"   Body: {json.dumps(payload, indent=2)}")
        
        response = requests.post(
            f"{API_URL}/metadata-fields/remove-orphans",
            json=payload
        )
        response.raise_for_status()
        data = response.json()
        
        print(f"\n✓ Status: {response.status_code}")
        print(f"✓ Success: {data.get('success')}")
        print(f"✓ Mensagem: {data.get('message')}")
        print(f"✓ Campos removidos: {data.get('removed_count')}")
        print(f"✓ Lista de removidos: {data.get('removed_fields')}")
        
        if data.get('success') and data.get('removed_count', 0) > 0:
            print(f"\n✅ Campo órfão removido com sucesso!")
            return True
        else:
            print(f"\n⚠️  Remoção retornou sucesso mas 0 campos removidos")
            return False
            
    except Exception as e:
        print(f"✗ Erro: {e}")
        if hasattr(e, 'response') and e.response:
            print(f"  Resposta: {e.response.text}")
        return False

def test_verify_orphan_removed(field_name: str):
    """Verifica se o campo órfão foi realmente removido"""
    print_section(f"PASSO 5: Verificar se Campo '{field_name}' Foi Removido")
    
    try:
        response = requests.get(f"{API_URL}/metadata-fields/{field_name}")
        
        if response.status_code == 404:
            print(f"✓ Status: {response.status_code} (Not Found)")
            print(f"\n✅ Campo órfão CONFIRMADO como removido!")
            return True
        elif response.status_code == 200:
            print(f"✗ Status: {response.status_code}")
            print(f"✗ Campo AINDA EXISTE no KV!")
            data = response.json()
            print(f"   Campo encontrado: {data.get('field', {})}")
            return False
        else:
            print(f"? Status: {response.status_code} (inesperado)")
            return False
            
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            print(f"✓ Status: 404 (Not Found)")
            print(f"\n✅ Campo órfão CONFIRMADO como removido!")
            return True
        else:
            print(f"✗ Erro HTTP: {e}")
            return False
    except Exception as e:
        print(f"✗ Erro: {e}")
        return False

def main():
    print("""
╔════════════════════════════════════════════════════════════════════════╗
║  TESTE COMPLETO: Remove Orphan Fields                                 ║
║  Endpoint: POST /metadata-fields/remove-orphans                        ║
╚════════════════════════════════════════════════════════════════════════╝
""")
    
    # PASSO 1: Listar campos atuais
    fields_data = test_list_fields()
    
    if not fields_data or not fields_data.get('success'):
        print("\n❌ FALHA: Não foi possível listar campos. Backend pode estar offline.")
        return
    
    # PASSO 2: Criar campo órfão de teste
    orphan_field_name = test_create_orphan_field()
    
    if not orphan_field_name:
        print("\n❌ FALHA: Não foi possível criar campo órfão de teste.")
        return
    
    # PASSO 3: Verificar se campo foi criado
    exists = test_verify_orphan_exists(orphan_field_name)
    
    if not exists:
        print("\n⚠️  AVISO: Campo não encontrado via GET, mas pode estar no KV")
        print("   Prosseguindo com teste de remoção mesmo assim...")
    
    # PASSO 4: Remover campo órfão
    removed = test_remove_orphan(orphan_field_name)
    
    if not removed:
        print("\n❌ FALHA: Endpoint de remoção não funcionou corretamente.")
        return
    
    # PASSO 5: Verificar se foi realmente removido
    confirmed_removed = test_verify_orphan_removed(orphan_field_name)
    
    # RESUMO FINAL
    print_section("RESUMO DOS TESTES")
    print("✓ Passo 1: Listagem de campos - OK")
    print(f"{'✓' if orphan_field_name else '✗'} Passo 2: Criação de campo órfão - {'OK' if orphan_field_name else 'FALHA'}")
    print(f"{'✓' if exists else '⚠'} Passo 3: Verificação de existência - {'OK' if exists else 'AVISO'}")
    print(f"{'✓' if removed else '✗'} Passo 4: Remoção do órfão - {'OK' if removed else 'FALHA'}")
    print(f"{'✓' if confirmed_removed else '✗'} Passo 5: Confirmação de remoção - {'OK' if confirmed_removed else 'FALHA'}")
    
    if orphan_field_name and removed and confirmed_removed:
        print("\n" + "="*80)
        print("✅ TODOS OS TESTES PASSARAM!")
        print("="*80)
        print("\n📋 Endpoint /metadata-fields/remove-orphans está funcionando corretamente:")
        print("   1. ✓ Aceita lista de field_names")
        print("   2. ✓ Remove campos do KV")
        print("   3. ✓ Limpa cache corretamente")
        print("   4. ✓ Retorna confirmação de sucesso")
        print("   5. ✓ Campos removidos não aparecem mais em GET")
    else:
        print("\n" + "="*80)
        print("❌ ALGUNS TESTES FALHARAM")
        print("="*80)
        print("\nVerifique os logs acima para identificar o problema.")

if __name__ == '__main__':
    main()
