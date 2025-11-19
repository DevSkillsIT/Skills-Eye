#!/usr/bin/env python3
"""
TESTE ADICIONAL - Entender diferença entre /catalog/services e /catalog/service/{name}
"""
import asyncio
import httpx
import json

TOKEN = "8382a112-81e0-cd6d-2b92-8565925a0675"
MASTER = "172.16.1.26"

async def test_catalog_detail():
    print("=" * 80)
    print("TESTE: /catalog/services vs /catalog/service/{name}")
    print("=" * 80)
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        headers = {"X-Consul-Token": TOKEN}
        
        # 1. Listar nomes de serviços
        print("\n📋 STEP 1: /catalog/services (lista de NOMES)")
        url1 = f"http://{MASTER}:8500/v1/catalog/services"
        resp1 = await client.get(url1, headers=headers)
        service_names = resp1.json()
        
        print(f"   Total de SERVICE NAMES: {len(service_names)}")
        print(f"   Names: {list(service_names.keys())}")
        
        # 2. Para cada nome, buscar instances
        print("\n📋 STEP 2: /catalog/service/{name} (INSTANCES de cada serviço)")
        
        total_instances = 0
        for service_name in service_names.keys():
            url2 = f"http://{MASTER}:8500/v1/catalog/service/{service_name}"
            resp2 = await client.get(url2, headers=headers)
            instances = resp2.json()
            
            total_instances += len(instances)
            print(f"   - {service_name}: {len(instances)} instances")
            
            if len(instances) > 0 and service_name == "blackbox_exporter":
                # Mostrar exemplo de estrutura
                print(f"\n     Exemplo de instance:")
                print(f"     Node: {instances[0].get('Node')}")
                print(f"     ServiceID: {instances[0].get('ServiceID')}")
                print(f"     ServiceName: {instances[0].get('ServiceName')}")
        
        print(f"\n📊 TOTAL DE INSTANCES: {total_instances}")
        
        # 3. Comparar com Agent API
        print("\n📋 STEP 3: /agent/services (COMPARAÇÃO)")
        url3 = f"http://{MASTER}:8500/v1/agent/services"
        resp3 = await client.get(url3, headers=headers)
        agent_services = resp3.json()
        
        print(f"   Total Agent API: {len(agent_services)} services")
        
        print("\n" + "=" * 80)
        print("CONCLUSÃO")
        print("=" * 80)
        print(f"\n/catalog/services: {len(service_names)} SERVICE NAMES (tipos)")
        print(f"/catalog/service/{{name}}: {total_instances} INSTANCES total")
        print(f"/agent/services (Palmas): {len(agent_services)} INSTANCES locais")
        
        print("\n🔍 ANÁLISE:")
        if total_instances == len(agent_services):
            print("   ✅ TODOS os serviços estão registrados no MASTER (Palmas)")
            print("   ✅ Agent API do master = Catalog API completo")
            print("   → Claude Code NÃO perde dados SE consultar o MASTER!")
        else:
            print(f"   ⚠️  Catalog tem {total_instances} mas Agent tem {len(agent_services)}")
            print("   → Há serviços em outros nodes NÃO visíveis no Catalog!")

asyncio.run(test_catalog_detail())
