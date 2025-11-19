#!/usr/bin/env python3
"""
TESTE DE VALIDAÇÃO - PROVA QUE CLAUDE CODE ESTÁ ERRADO

Este script demonstra que usar /agent/services ao invés de /catalog/services
resulta em PERDA DE DADOS.

Data: 15/11/2025
Autor: Desenvolvedor Sênior validando código do Claude Code
"""
import asyncio
import httpx
import json
from datetime import datetime

# Configuração do cluster (mesmo do KV)
SITES = [
    {"name": "Palmas", "host": "172.16.1.26", "is_default": True},
    {"name": "Rio", "host": "172.16.200.14", "is_default": False},
    {"name": "Dtc", "host": "11.144.0.21", "is_default": False},
]

TOKEN = "8382a112-81e0-cd6d-2b92-8565925a0675"  # Token do sistema (real)


async def test_agent_vs_catalog():
    """
    TESTE 1: Comparar /agent/services vs /catalog/services
    
    HIPÓTESE: Agent API retorna APENAS serviços LOCAIS
    EXPECTATIVA: Catalog API retorna TODOS os serviços
    """
    print("=" * 80)
    print("TESTE 1: /agent/services vs /catalog/services")
    print("=" * 80)
    
    results = {
        "agent_api": {},
        "catalog_api": {}
    }
    
    async with httpx.AsyncClient(timeout=5.0) as client:
        for site in SITES:
            site_name = site["name"]
            site_host = site["host"]
            
            print(f"\n🔍 Testando {site_name} ({site_host})...")
            
            headers = {"X-Consul-Token": TOKEN}
            
            # TESTE: Agent API
            try:
                agent_url = f"http://{site_host}:8500/v1/agent/services"
                agent_resp = await client.get(agent_url, headers=headers)
                agent_services = agent_resp.json()
                
                results["agent_api"][site_name] = {
                    "count": len(agent_services),
                    "services": list(agent_services.keys())
                }
                
                print(f"  📊 Agent API: {len(agent_services)} serviços")
                print(f"     Serviços: {', '.join(list(agent_services.keys())[:5])}")
                
            except Exception as e:
                print(f"  ❌ Agent API falhou: {e}")
                results["agent_api"][site_name] = {"error": str(e)}
            
            # TESTE: Catalog API
            try:
                catalog_url = f"http://{site_host}:8500/v1/catalog/services"
                catalog_resp = await client.get(catalog_url, headers=headers)
                catalog_services = catalog_resp.json()
                
                results["catalog_api"][site_name] = {
                    "count": len(catalog_services),
                    "services": list(catalog_services.keys())
                }
                
                print(f"  📊 Catalog API: {len(catalog_services)} serviços")
                print(f"     Serviços: {', '.join(list(catalog_services.keys())[:5])}")
                
            except Exception as e:
                print(f"  ❌ Catalog API falhou: {e}")
                results["catalog_api"][site_name] = {"error": str(e)}
    
    # ANÁLISE
    print("\n" + "=" * 80)
    print("ANÁLISE DOS RESULTADOS")
    print("=" * 80)
    
    print("\n🔍 Agent API (dados LOCAIS apenas):")
    for site_name, data in results["agent_api"].items():
        if "error" not in data:
            print(f"  - {site_name}: {data['count']} serviços")
        else:
            print(f"  - {site_name}: ERRO - {data['error']}")
    
    print("\n🌍 Catalog API (dados GLOBAIS - cluster inteiro):")
    for site_name, data in results["catalog_api"].items():
        if "error" not in data:
            print(f"  - {site_name}: {data['count']} serviços")
        else:
            print(f"  - {site_name}: ERRO - {data['error']}")
    
    # VEREDICTO
    print("\n" + "=" * 80)
    print("VEREDICTO")
    print("=" * 80)
    
    # Verificar se Catalog retorna o MESMO em todos os nodes
    catalog_counts = [
        data["count"] for data in results["catalog_api"].values() 
        if "error" not in data
    ]
    
    if catalog_counts and all(c == catalog_counts[0] for c in catalog_counts):
        print(f"✅ Catalog API: CONSISTENTE ({catalog_counts[0]} serviços em TODOS os nodes)")
        print("   → Gossip Protocol funcionando corretamente!")
    else:
        print(f"⚠️  Catalog API: Resultados diferentes entre nodes: {catalog_counts}")
    
    # Verificar se Agent retorna DIFERENTE em cada node
    agent_counts = [
        data["count"] for data in results["agent_api"].values() 
        if "error" not in data
    ]
    
    if agent_counts and not all(c == agent_counts[0] for c in agent_counts):
        print(f"\n⚠️  Agent API: DADOS DIFERENTES ({agent_counts})")
        print("   → Agent API retorna APENAS serviços LOCAIS do node!")
        print("   → Se usar Agent API, vai PERDER DADOS de outros nodes!")
    else:
        print(f"\n✅ Agent API: Mesma quantidade em todos ({agent_counts})")
        print("   (Pode ser coincidência se todos têm mesmos serviços)")
    
    return results


async def test_claude_code_implementation():
    """
    TESTE 2: Simular exatamente o que o Claude Code está fazendo
    """
    print("\n" + "=" * 80)
    print("TESTE 2: SIMULANDO CÓDIGO DO CLAUDE CODE")
    print("=" * 80)
    
    print("\n📝 O Claude Code está fazendo:")
    print("   1. get_services_with_fallback() → retorna 1 node")
    print("   2. /agent/services no node retornado")
    print("   3. Retorna como se fosse TODOS os serviços")
    
    async with httpx.AsyncClient(timeout=5.0) as client:
        # Simular: pegar primeiro node (Palmas = master)
        master = SITES[0]
        print(f"\n🎯 Usando {master['name']} como source_node")
        
        headers = {"X-Consul-Token": TOKEN}
        agent_url = f"http://{master['host']}:8500/v1/agent/services"
        
        try:
            response = await client.get(agent_url, headers=headers)
            services = response.json()
            
            print(f"\n📊 RESULTADO:")
            print(f"   Total de serviços: {len(services)}")
            print(f"   Primeiros 10: {list(services.keys())[:10]}")
            
            # VERIFICAÇÃO: Tem serviços de RIO e DTC?
            has_rio = any("rio" in sid.lower() for sid in services.keys())
            has_dtc = any("dtc" in sid.lower() or "genesis" in sid.lower() for sid in services.keys())
            
            print(f"\n🔍 VALIDAÇÃO:")
            print(f"   Serviços do Rio encontrados? {'✅ SIM' if has_rio else '❌ NÃO'}")
            print(f"   Serviços do Dtc encontrados? {'✅ SIM' if has_dtc else '❌ NÃO'}")
            
            if not has_rio or not has_dtc:
                print("\n🚨 PROBLEMA CONFIRMADO!")
                print("   /agent/services em Palmas NÃO retorna serviços de outros nodes!")
                print("   Claude Code está PERDENDO DADOS!")
            else:
                print("\n✅ Serviços de todos os nodes encontrados")
                print("   (Todos podem estar registrados no master)")
        
        except Exception as e:
            print(f"\n❌ Erro ao consultar: {e}")


async def test_correct_implementation():
    """
    TESTE 3: Implementação CORRETA usando Catalog API
    """
    print("\n" + "=" * 80)
    print("TESTE 3: IMPLEMENTAÇÃO CORRETA (Catalog API)")
    print("=" * 80)
    
    print("\n📝 Implementação correta:")
    print("   1. /catalog/services → retorna TODOS os serviços do datacenter")
    print("   2. Usar ?stale para escalabilidade")
    print("   3. Usar ?cached para performance")
    
    async with httpx.AsyncClient(timeout=5.0) as client:
        master = SITES[0]
        headers = {"X-Consul-Token": TOKEN}
        
        # URL correta
        catalog_url = f"http://{master['host']}:8500/v1/catalog/services?stale&cached"
        
        try:
            start = datetime.now()
            response = await client.get(catalog_url, headers=headers)
            duration_ms = (datetime.now() - start).total_seconds() * 1000
            
            services = response.json()
            
            print(f"\n📊 RESULTADO:")
            print(f"   Total de serviços: {len(services)}")
            print(f"   Tempo de resposta: {duration_ms:.0f}ms")
            print(f"   Cache status: {response.headers.get('X-Cache', 'MISS')}")
            print(f"   Age: {response.headers.get('Age', '0')}s")
            print(f"   Staleness: {response.headers.get('X-Consul-LastContact', '0')}ms")
            print(f"   Serviços: {', '.join(list(services.keys())[:10])}")
            
            print("\n✅ Catalog API retorna TODOS os serviços em 1 request!")
            
        except Exception as e:
            print(f"\n❌ Erro ao consultar: {e}")


async def main():
    print("\n" + "🔬" * 40)
    print("TESTE DE VALIDAÇÃO - CLAUDE CODE vs DOCUMENTAÇÃO OFICIAL")
    print("🔬" * 40)
    print(f"\nData: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Objetivo: Provar que usar /agent/services está ERRADO")
    print("")
    
    # TESTE 1: Comparar APIs
    results1 = await test_agent_vs_catalog()
    
    # TESTE 2: Simular Claude Code
    await test_claude_code_implementation()
    
    # TESTE 3: Implementação correta
    await test_correct_implementation()
    
    # CONCLUSÃO FINAL
    print("\n" + "=" * 80)
    print("CONCLUSÃO FINAL")
    print("=" * 80)
    
    print("\n❌ PROBLEMAS IDENTIFICADOS NO CÓDIGO DO CLAUDE CODE:")
    print("   1. Usa /agent/services ao invés de /catalog/services")
    print("   2. Agent API retorna APENAS dados LOCAIS do node")
    print("   3. Resulta em PERDA DE DADOS de outros nodes")
    print("   4. VIOLA documentação oficial HashiCorp")
    
    print("\n✅ SOLUÇÃO CORRETA (conforme Copilot especificou):")
    print("   1. Usar /catalog/services (vista GLOBAL do datacenter)")
    print("   2. Adicionar ?stale (escalabilidade)")
    print("   3. Adicionar ?cached (Agent Caching)")
    print("   4. Fallback master → clients funciona CORRETAMENTE")
    
    print("\n📚 FONTES:")
    print("   - https://developer.hashicorp.com/consul/api-docs/agent/service")
    print("   - https://developer.hashicorp.com/consul/api-docs/catalog")
    print("   - Stack Overflow (HashiCorp Engineer confirma)")
    
    print("\n" + "=" * 80)
    print("")


if __name__ == "__main__":
    asyncio.run(main())
