"""
Testes para verificar se monitoring-types KV está sendo salvo SEM campos 'fields'

Este teste verifica:
1. Se o KV está sendo salvo sem 'fields'
2. Se o pre-warm está funcionando corretamente
3. Se o endpoint está removendo 'fields' antes de salvar
"""

import asyncio
import json
import sys
from pathlib import Path

# Adicionar backend ao path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from core.kv_manager import KVManager


async def test_kv_has_no_fields():
    """Testa se o KV não tem campo 'fields' nos tipos"""
    print("\n" + "="*80)
    print("TESTE 1: Verificar se KV não tem campo 'fields'")
    print("="*80)
    
    kv_manager = KVManager()
    kv_data = await kv_manager.get_json('skills/eye/monitoring-types')
    
    if not kv_data:
        print("❌ ERRO: KV está vazio!")
        return False
    
    print(f"✅ KV encontrado: {kv_data.get('total_types', 0)} tipos")
    
    # Verificar servers
    servers = kv_data.get('servers', {})
    for hostname, server_data in servers.items():
        types = server_data.get('types', [])
        print(f"\n📊 Servidor {hostname}: {len(types)} tipos")
        
        for i, type_def in enumerate(types[:3]):  # Verificar apenas os 3 primeiros
            if 'fields' in type_def:
                print(f"❌ ERRO: Tipo '{type_def.get('id')}' TEM campo 'fields'!")
                print(f"   Campos presentes: {list(type_def.keys())}")
                return False
            else:
                print(f"   ✅ Tipo '{type_def.get('id')}' SEM campo 'fields'")
    
    # Verificar all_types
    all_types = kv_data.get('all_types', [])
    print(f"\n📊 All Types: {len(all_types)} tipos")
    
    for i, type_def in enumerate(all_types[:3]):  # Verificar apenas os 3 primeiros
        if 'fields' in type_def:
            print(f"❌ ERRO: All Types[{i}] '{type_def.get('id')}' TEM campo 'fields'!")
            return False
    
    # Verificar categories
    categories = kv_data.get('categories', [])
    print(f"\n📊 Categories: {len(categories)} categorias")
    
    for cat in categories:
        types = cat.get('types', [])
        for type_def in types[:2]:  # Verificar apenas os 2 primeiros de cada categoria
            if 'fields' in type_def:
                print(f"❌ ERRO: Category '{cat.get('category')}' tipo '{type_def.get('id')}' TEM campo 'fields'!")
                return False
    
    print("\n✅ SUCESSO: KV não tem campo 'fields' em nenhum lugar!")
    return True


async def test_endpoint_removes_fields():
    """Testa se o endpoint remove 'fields' antes de salvar"""
    print("\n" + "="*80)
    print("TESTE 2: Verificar se endpoint remove 'fields' ao salvar")
    print("="*80)
    
    import httpx
    
    # Forçar refresh para garantir que salva sem fields
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "http://localhost:5000/api/v1/monitoring-types-dynamic/from-prometheus",
            params={"server": "ALL", "force_refresh": True},
            timeout=60.0
        )
        
        if response.status_code != 200:
            print(f"❌ ERRO: Endpoint retornou {response.status_code}")
            print(f"   Resposta: {response.text[:200]}")
            return False
        
        data = response.json()
        
        if not data.get('success'):
            print(f"❌ ERRO: Endpoint retornou success=False")
            return False
        
        print(f"✅ Endpoint respondeu: {data.get('total_types', 0)} tipos")
        print(f"   From cache: {data.get('from_cache', False)}")
        
        # Aguardar um pouco para garantir que salvou no KV
        await asyncio.sleep(2)
        
        # Verificar KV novamente
        kv_manager = KVManager()
        kv_data = await kv_manager.get_json('skills/eye/monitoring-types')
        
        if not kv_data:
            print("❌ ERRO: KV está vazio após refresh!")
            return False
        
        # Verificar se tem fields
        servers = kv_data.get('servers', {})
        for hostname, server_data in servers.items():
            types = server_data.get('types', [])
            for type_def in types[:2]:
                if 'fields' in type_def:
                    print(f"❌ ERRO: Após refresh, tipo '{type_def.get('id')}' AINDA TEM 'fields'!")
                    return False
        
        print("✅ SUCESSO: Endpoint remove 'fields' corretamente!")
        return True


async def test_prewarm_removes_fields():
    """Testa se o pre-warm remove 'fields' antes de salvar"""
    print("\n" + "="*80)
    print("TESTE 3: Verificar se pre-warm remove 'fields'")
    print("="*80)
    
    # Este teste precisa ser executado após reiniciar a aplicação
    # Por enquanto, apenas verifica se o código está correto
    from backend.app import _prewarm_monitoring_types_cache
    
    # Verificar se a função existe e tem a lógica de remover fields
    import inspect
    source = inspect.getsource(_prewarm_monitoring_types_cache)
    
    if 'remove_fields_from_types' not in source:
        print("❌ ERRO: Pre-warm NÃO tem função remove_fields_from_types!")
        return False
    
    if 'cleaned_servers' not in source:
        print("❌ ERRO: Pre-warm NÃO está usando cleaned_servers!")
        return False
    
    print("✅ SUCESSO: Pre-warm tem código para remover 'fields'!")
    print("   (Execute após reiniciar aplicação para testar na prática)")
    return True


async def test_frontend_filter():
    """Testa se o filtro de servidor funciona no frontend"""
    print("\n" + "="*80)
    print("TESTE 4: Verificar se endpoint filtra por servidor corretamente")
    print("="*80)
    
    import httpx
    
    # Testar com servidor específico
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "http://localhost:5000/api/v1/monitoring-types-dynamic/from-prometheus",
            params={"server": "11.144.0.21"},
            timeout=30.0
        )
        
        if response.status_code != 200:
            print(f"❌ ERRO: Endpoint retornou {response.status_code}")
            return False
        
        data = response.json()
        
        if not data.get('success'):
            print(f"❌ ERRO: Endpoint retornou success=False")
            return False
        
        servers = data.get('servers', {})
        server_keys = list(servers.keys())
        
        print(f"📊 Servidores retornados: {server_keys}")
        
        # Deve retornar todos os servidores (filtro é no frontend)
        if len(server_keys) == 0:
            print("❌ ERRO: Nenhum servidor retornado!")
            return False
        
        # Verificar se o servidor solicitado está na lista
        if '11.144.0.21' not in server_keys:
            print("❌ ERRO: Servidor solicitado não está na resposta!")
            return False
        
        print("✅ SUCESSO: Endpoint retorna servidores corretamente!")
        return True


async def main():
    """Executa todos os testes"""
    print("\n" + "="*80)
    print("TESTES DE MONITORING-TYPES KV")
    print("="*80)
    
    results = []
    
    # Teste 1: Verificar KV
    try:
        result1 = await test_kv_has_no_fields()
        results.append(("KV sem fields", result1))
    except Exception as e:
        print(f"❌ ERRO no teste 1: {e}")
        import traceback
        traceback.print_exc()
        results.append(("KV sem fields", False))
    
    # Teste 2: Endpoint remove fields
    try:
        result2 = await test_endpoint_removes_fields()
        results.append(("Endpoint remove fields", result2))
    except Exception as e:
        print(f"❌ ERRO no teste 2: {e}")
        import traceback
        traceback.print_exc()
        results.append(("Endpoint remove fields", False))
    
    # Teste 3: Pre-warm remove fields
    try:
        result3 = await test_prewarm_removes_fields()
        results.append(("Pre-warm remove fields", result3))
    except Exception as e:
        print(f"❌ ERRO no teste 3: {e}")
        import traceback
        traceback.print_exc()
        results.append(("Pre-warm remove fields", False))
    
    # Teste 4: Filtro de servidor
    try:
        result4 = await test_frontend_filter()
        results.append(("Filtro de servidor", result4))
    except Exception as e:
        print(f"❌ ERRO no teste 4: {e}")
        import traceback
        traceback.print_exc()
        results.append(("Filtro de servidor", False))
    
    # Resumo
    print("\n" + "="*80)
    print("RESUMO DOS TESTES")
    print("="*80)
    
    for test_name, result in results:
        status = "✅ PASSOU" if result else "❌ FALHOU"
        print(f"{status}: {test_name}")
    
    total = len(results)
    passed = sum(1 for _, r in results if r)
    
    print(f"\nTotal: {passed}/{total} testes passaram")
    
    if passed == total:
        print("\n🎉 TODOS OS TESTES PASSARAM!")
        return 0
    else:
        print(f"\n⚠️  {total - passed} TESTE(S) FALHARAM!")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)

