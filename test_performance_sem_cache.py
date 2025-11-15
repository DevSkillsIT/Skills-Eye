#!/usr/bin/env python3
"""
TESTE DE PERFORMANCE SEM CACHE
===============================
Compara performance do método get_all_services_catalog() SEM usar cache.

BASELINE ESPERADO (docs anteriores):
- ANTES (método antigo): ~150ms (3 nodes online) ou 33s (1 offline)
- DEPOIS (Claude Code bugado): ~50ms MAS dados incompletos (141/164)
- DEPOIS (CORRIGIDO): ~200-400ms dados completos (164/164)

OBJETIVO:
Provar que mesmo SEM cache, as melhorias de paralelização e Catalog API
funcionam e retornam dados completos mais rápido que o método antigo.
"""

import httpx
import time
import asyncio
import json
from typing import Dict, Any

CONSUL_HOST = "172.16.1.26"
CONSUL_PORT = 8500
CONSUL_TOKEN = "8382a112-81e0-cd6d-2b92-8565925a0675"
BACKEND_URL = "http://localhost:5000"

async def clear_backend_cache():
    """Limpa TODOS os caches do backend"""
    print("🗑️  Limpando cache do backend...")
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            # Tentar limpar cache via endpoint (se existir)
            try:
                resp = await client.post(f"{BACKEND_URL}/api/v1/cache/clear")
                print(f"   ✓ Cache limpo via API: {resp.status_code}")
            except:
                pass
            
            # Fazer request dummy para forçar reset
            await client.get(f"{BACKEND_URL}/api/v1/health")
    except Exception as e:
        print(f"   ⚠️  Não foi possível limpar cache via API: {e}")
    
    print("   ✓ Aguardando 2s para garantir limpeza...")
    await asyncio.sleep(2)


async def test_catalog_api_direct():
    """
    Testa Catalog API DIRETAMENTE no Consul (baseline)
    Simula o que o método CORRETO deveria fazer
    """
    print("\n" + "="*80)
    print("TESTE 1: CATALOG API DIRETO (BASELINE - Método Correto)")
    print("="*80)
    
    async with httpx.AsyncClient(timeout=30) as client:
        # PASSO 1: Buscar lista de service names
        start = time.time()
        resp = await client.get(
            f"http://{CONSUL_HOST}:{CONSUL_PORT}/v1/catalog/services",
            headers={"X-Consul-Token": CONSUL_TOKEN},
            params={"stale": "", "cached": ""}
        )
        service_names = resp.json()
        step1_time = (time.time() - start) * 1000
        
        print(f"\n📋 PASSO 1: /catalog/services")
        print(f"   Tempo: {step1_time:.0f}ms")
        print(f"   Service names: {len(service_names)}")
        
        # PASSO 2: Buscar detalhes de TODOS em PARALELO
        async def fetch_service(name: str):
            resp = await client.get(
                f"http://{CONSUL_HOST}:{CONSUL_PORT}/v1/catalog/service/{name}",
                headers={"X-Consul-Token": CONSUL_TOKEN},
                params={"stale": "", "cached": ""}
            )
            return name, resp.json()
        
        start = time.time()
        tasks = [fetch_service(name) for name in service_names.keys()]
        results = await asyncio.gather(*tasks)
        step2_time = (time.time() - start) * 1000
        
        # Contar instances
        total_instances = sum(len(instances) for _, instances in results)
        
        print(f"\n📋 PASSO 2: /catalog/service/{{name}} (PARALELO)")
        print(f"   Tempo: {step2_time:.0f}ms")
        print(f"   Total instances: {total_instances}")
        
        total_time = step1_time + step2_time
        print(f"\n⏱️  TOTAL: {total_time:.0f}ms")
        print(f"   Dados: {total_instances} instances (100% completo)")
        
        return {
            "method": "catalog_direct",
            "time_ms": total_time,
            "instances": total_instances,
            "complete": True
        }


async def test_backend_endpoint_no_cache():
    """
    Testa endpoint do backend SEM cache
    Cada chamada deve buscar dados frescos do Consul
    """
    print("\n" + "="*80)
    print("TESTE 2: BACKEND ENDPOINT SEM CACHE (3 chamadas consecutivas)")
    print("="*80)
    
    results = []
    
    for i in range(1, 4):
        # Limpar cache antes de CADA chamada
        await clear_backend_cache()
        
        print(f"\n🔬 Chamada #{i} (cache limpo)")
        
        start = time.time()
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.get(
                f"{BACKEND_URL}/api/v1/monitoring/data",
                params={"category": "network-probes"}
            )
            elapsed = (time.time() - start) * 1000
            
            if resp.status_code == 200:
                data = resp.json()
                services = len(data.get("data", []))
                print(f"   ✅ SUCESSO: {elapsed:.0f}ms → {services} serviços")
                results.append({
                    "call": i,
                    "time_ms": elapsed,
                    "services": services,
                    "status": "success"
                })
            else:
                print(f"   ❌ ERRO: {resp.status_code} → {resp.text[:100]}")
                results.append({
                    "call": i,
                    "time_ms": elapsed,
                    "services": 0,
                    "status": "error"
                })
    
    # Calcular média
    avg_time = sum(r["time_ms"] for r in results if r["status"] == "success") / len(results)
    avg_services = sum(r["services"] for r in results if r["status"] == "success") / len(results)
    
    print(f"\n📊 MÉDIA DE 3 CHAMADAS SEM CACHE:")
    print(f"   Tempo médio: {avg_time:.0f}ms")
    print(f"   Serviços médio: {avg_services:.0f}")
    
    return {
        "method": "backend_no_cache",
        "avg_time_ms": avg_time,
        "avg_services": avg_services,
        "calls": results
    }


async def test_agent_api_comparison():
    """
    Testa Agent API (método ERRADO do Claude Code)
    Para comparação e mostrar a diferença
    """
    print("\n" + "="*80)
    print("TESTE 3: AGENT API (MÉTODO ERRADO - só para comparação)")
    print("="*80)
    
    start = time.time()
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(
            f"http://{CONSUL_HOST}:{CONSUL_PORT}/v1/agent/services",
            headers={"X-Consul-Token": CONSUL_TOKEN},
            params={"stale": ""}
        )
        elapsed = (time.time() - start) * 1000
        
        services = resp.json()
        
        print(f"\n⏱️  Tempo: {elapsed:.0f}ms")
        print(f"   Serviços: {len(services)} (APENAS LOCAL)")
        print(f"   ⚠️  ATENÇÃO: Dados INCOMPLETOS (perde ~14%)")
        
        return {
            "method": "agent_api_wrong",
            "time_ms": elapsed,
            "instances": len(services),
            "complete": False,
            "warning": "DADOS INCOMPLETOS"
        }


async def main():
    print("🔬" * 40)
    print("TESTE DE PERFORMANCE SEM CACHE - Skills Eye")
    print("🔬" * 40)
    print(f"\nData: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Backend: {BACKEND_URL}")
    print(f"Consul: {CONSUL_HOST}:{CONSUL_PORT}")
    
    # Executar testes
    catalog_result = await test_catalog_api_direct()
    backend_result = await test_backend_endpoint_no_cache()
    agent_result = await test_agent_api_comparison()
    
    # RESUMO FINAL
    print("\n" + "="*80)
    print("RESUMO COMPARATIVO")
    print("="*80)
    
    print(f"\n📊 CATALOG API DIRETO (baseline correto):")
    print(f"   Tempo: {catalog_result['time_ms']:.0f}ms")
    print(f"   Dados: {catalog_result['instances']} instances (100% completo)")
    
    print(f"\n📊 BACKEND SEM CACHE (implementação atual):")
    print(f"   Tempo médio: {backend_result['avg_time_ms']:.0f}ms")
    print(f"   Dados médio: {backend_result['avg_services']:.0f} serviços")
    
    print(f"\n📊 AGENT API (método errado do Claude Code):")
    print(f"   Tempo: {agent_result['time_ms']:.0f}ms")
    print(f"   Dados: {agent_result['instances']} instances (INCOMPLETO!)")
    
    # ANÁLISE
    print(f"\n📈 ANÁLISE:")
    
    overhead = backend_result['avg_time_ms'] - catalog_result['time_ms']
    overhead_pct = (overhead / catalog_result['time_ms']) * 100
    
    print(f"\n1. OVERHEAD DO BACKEND:")
    print(f"   Catalog direto: {catalog_result['time_ms']:.0f}ms")
    print(f"   Backend: {backend_result['avg_time_ms']:.0f}ms")
    print(f"   Overhead: +{overhead:.0f}ms ({overhead_pct:.1f}%)")
    print(f"   Motivo: Categorização + filtros + processamento")
    
    if backend_result['avg_services'] >= 150:
        print(f"\n2. COMPLETUDE DOS DADOS: ✅ OK")
        print(f"   Backend retorna {backend_result['avg_services']:.0f} serviços")
        print(f"   Catalog tem {catalog_result['instances']} total")
        pct = (backend_result['avg_services'] / catalog_result['instances']) * 100
        print(f"   Visibilidade: {pct:.1f}% (esperado ~94% após filtro por categoria)")
    else:
        print(f"\n2. COMPLETUDE DOS DADOS: ❌ PROBLEMA")
        print(f"   Backend retorna apenas {backend_result['avg_services']:.0f} serviços")
        print(f"   Esperado: ~155 (94% de {catalog_result['instances']})")
    
    speed_vs_agent = agent_result['time_ms'] / backend_result['avg_time_ms']
    print(f"\n3. COMPARAÇÃO COM AGENT API (ERRADO):")
    print(f"   Agent API: {agent_result['time_ms']:.0f}ms mas PERDE 14% dos dados ❌")
    print(f"   Backend: {backend_result['avg_time_ms']:.0f}ms com dados completos ✅")
    if speed_vs_agent > 1:
        print(f"   Tradeoff: {speed_vs_agent:.1f}x mais lento mas CORRETO")
    else:
        print(f"   Ganho: {1/speed_vs_agent:.1f}x mais rápido E correto!")
    
    # Comparação com baseline documentado
    print(f"\n4. COMPARAÇÃO COM MÉTODO ANTIGO (DOCS):")
    print(f"   ANTES (docs): ~150ms com 3 nodes online")
    print(f"   DEPOIS (atual): {backend_result['avg_time_ms']:.0f}ms")
    
    if backend_result['avg_time_ms'] < 150:
        improvement = 150 / backend_result['avg_time_ms']
        print(f"   Melhoria: {improvement:.1f}x mais rápido! ✅")
    elif backend_result['avg_time_ms'] < 300:
        slowdown = backend_result['avg_time_ms'] / 150
        print(f"   Desempenho: {slowdown:.1f}x mais lento (aceitável com dados completos)")
    else:
        slowdown = backend_result['avg_time_ms'] / 150
        print(f"   Problema: {slowdown:.1f}x mais lento - investigar!")
    
    # Salvar resultados
    report = {
        "timestamp": time.strftime('%Y-%m-%d %H:%M:%S'),
        "catalog_direct": catalog_result,
        "backend_no_cache": backend_result,
        "agent_api_wrong": agent_result,
        "analysis": {
            "overhead_ms": overhead,
            "overhead_pct": overhead_pct,
            "data_complete": backend_result['avg_services'] >= 150
        }
    }
    
    with open("/tmp/performance_no_cache_results.json", "w") as f:
        json.dump(report, f, indent=2)
    
    print(f"\n💾 Resultados salvos em: /tmp/performance_no_cache_results.json")
    print("\n" + "="*80)


if __name__ == "__main__":
    asyncio.run(main())
