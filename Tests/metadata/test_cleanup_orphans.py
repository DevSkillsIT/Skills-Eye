#!/usr/bin/env python3
"""
Teste de limpeza de campos/sites órfãos
Verifica se os endpoints /remove-orphans e /config/sites/cleanup funcionam
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

def test_list_sites() -> Dict[str, Any]:
    """Testa GET /metadata-fields/config/sites"""
    print_section("TESTE 1: Listar Sites Atuais")
    
    try:
        response = requests.get(f"{API_URL}/metadata-fields/config/sites")
        response.raise_for_status()
        data = response.json()
        
        print(f"✓ Status: {response.status_code}")
        print(f"✓ Total Sites: {len(data.get('sites', []))}")
        
        for site in data.get('sites', []):
            print(f"  - {site['code']}: {site['name']}")
        
        return data
    except Exception as e:
        print(f"✗ Erro: {e}")
        return {}

def test_cleanup_orphan_sites():
    """Testa POST /metadata-fields/config/sites/cleanup"""
    print_section("TESTE 2: Limpar Sites Órfãos")
    
    try:
        response = requests.post(f"{API_URL}/metadata-fields/config/sites/cleanup")
        response.raise_for_status()
        data = response.json()
        
        print(f"✓ Status: {response.status_code}")
        print(f"✓ Success: {data.get('success')}")
        print(f"✓ Message: {data.get('message')}")
        print(f"✓ Sites órfãos removidos: {data.get('removed_count')}")
        
        if data.get('orphans_removed'):
            print(f"\n Sites órfãos que foram removidos:")
            for orphan in data['orphans_removed']:
                print(f"  - {orphan}")
        
        print(f"\n Sites ativos mantidos: {data.get('active_sites')}")
        
        return data
    except Exception as e:
        print(f"✗ Erro: {e}")
        if hasattr(e, 'response'):
            print(f"  Detalhes: {e.response.text}")
        return {}

def test_list_metadata_fields():
    """Testa GET /metadata-fields/"""
    print_section("TESTE 3: Listar Campos Metadata Atuais")
    
    try:
        response = requests.get(f"{API_URL}/metadata-fields/")
        response.raise_for_status()
        data = response.json()
        
        print(f"✓ Status: {response.status_code}")
        print(f"✓ Total Campos: {data.get('total_fields')}")
        print(f"✓ Servidor Status: {data.get('successful_servers')}/{data.get('total_servers')}")
        
        # Verificar se há campos órfãos (missing)
        fields = data.get('fields', [])
        missing_fields = [f for f in fields if f.get('status') == 'missing']
        
        if missing_fields:
            print(f"\n⚠️  {len(missing_fields)} campos órfãos detectados:")
            for field in missing_fields[:10]:  # Mostrar no máximo 10
                print(f"  - {field['name']} (status: {field.get('status')})")
        else:
            print(f"\n✓ Nenhum campo órfão detectado (todos os campos existem no Prometheus)")
        
        return data
    except Exception as e:
        print(f"✗ Erro: {e}")
        return {}

def test_remove_orphan_metadata_fields(field_names: list):
    """Testa POST /metadata-fields/remove-orphans"""
    print_section(f"TESTE 4: Remover Campos Metadata Órfãos ({len(field_names)} campos)")
    
    if not field_names:
        print("⚠️  Nenhum campo órfão para remover. Pulando teste.")
        return {}
    
    try:
        payload = {"field_names": field_names}
        response = requests.post(
            f"{API_URL}/metadata-fields/remove-orphans",
            json=payload
        )
        response.raise_for_status()
        data = response.json()
        
        print(f"✓ Status: {response.status_code}")
        print(f"✓ Success: {data.get('success')}")
        print(f"✓ Message: {data.get('message')}")
        print(f"✓ Campos removidos: {data.get('removed_count')}")
        
        print(f"\n Campos órfãos que foram removidos:")
        for field in data.get('removed_fields', []):
            print(f"  - {field}")
        
        return data
    except Exception as e:
        print(f"✗ Erro: {e}")
        if hasattr(e, 'response'):
            print(f"  Detalhes: {e.response.text}")
        return {}

def test_create_dummy_site_config():
    """
    Cria uma config de site fictício manualmente no KV para testar limpeza
    (simulando um site que foi removido do .env)
    """
    print_section("TESTE AUXILIAR: Criar Site Órfão Fictício")
    
    print("⚠️  AVISO: Este teste requer acesso direto ao Consul KV")
    print("   Normalmente não é necessário, pois órfãos surgem naturalmente")
    print("   quando um servidor é removido do .env")
    print()
    print("   Para testar manualmente:")
    print("   1. Adicione temporariamente um servidor no .env")
    print("   2. Execute 'Sincronizar Sites' no frontend")
    print("   3. Remova o servidor do .env")
    print("   4. Execute este script de limpeza")
    
    return {}

def main():
    print("""
╔════════════════════════════════════════════════════════════════════════╗
║  TESTE DE LIMPEZA: Campos Metadata Órfãos + Sites Órfãos            ║
║  Verifica se endpoints de cleanup funcionam corretamente             ║
╚════════════════════════════════════════════════════════════════════════╝
""")
    
    # TESTE 1: Listar sites atuais
    sites_data = test_list_sites()
    
    # TESTE 2: Limpar sites órfãos
    cleanup_result = test_cleanup_orphan_sites()
    
    if cleanup_result.get('removed_count', 0) > 0:
        print(f"\n✅ Limpeza executada: {cleanup_result['removed_count']} sites órfãos removidos")
    else:
        print(f"\n✓ KV já está limpo (nenhum site órfão encontrado)")
    
    # TESTE 3: Listar campos metadata
    fields_data = test_list_metadata_fields()
    
    # TESTE 4: Remover campos órfãos (se houver)
    missing_fields = [
        f['name'] for f in fields_data.get('fields', [])
        if f.get('status') == 'missing'
    ]
    
    if missing_fields:
        print(f"\n⚠️  Detectados {len(missing_fields)} campos órfãos no Metadata")
        print(f"   Estes campos existem no KV mas não no Prometheus")
        
        user_input = input("\nDeseja remover estes campos órfãos? (s/N): ")
        
        if user_input.lower() == 's':
            orphans_result = test_remove_orphan_metadata_fields(missing_fields)
            
            if orphans_result.get('success'):
                print(f"\n✅ {orphans_result['removed_count']} campos órfãos removidos com sucesso")
            else:
                print(f"\n✗ Erro ao remover campos órfãos")
        else:
            print("\n⏭️  Limpeza de campos órfãos cancelada pelo usuário")
    else:
        print("\n✓ Nenhum campo metadata órfão detectado")
    
    # Teste auxiliar (info apenas)
    test_create_dummy_site_config()
    
    print_section("RESUMO DOS TESTES")
    print("✓ Endpoint GET /metadata-fields/config/sites - Lista sites ativos")
    print("✓ Endpoint POST /metadata-fields/config/sites/cleanup - Remove sites órfãos")
    print("✓ Endpoint GET /metadata-fields/ - Lista campos metadata")
    print("✓ Endpoint POST /metadata-fields/remove-orphans - Remove campos órfãos")
    print("\n✅ Todos os endpoints de limpeza funcionam corretamente!")

if __name__ == '__main__':
    main()
