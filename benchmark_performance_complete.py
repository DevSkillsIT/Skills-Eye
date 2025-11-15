#!/usr/bin/env python3
"""
BENCHMARK COMPLETO - Performance ANTES vs DEPOIS

Mede:
1. Tempo de resposta /api/v1/monitoring/data
2. Quantidade de requests ao Consul
3. Performance com e sem cache
4. Completude dos dados (164/164 services)
"""
import asyncio
import httpx
import time
import json
from datetime import datetime

BACKEND_URL = "http://localhost:5000"
CONSUL_TOKEN = "8382a112-81e0-cd6d-2b92-8565925a0675"
CONSUL_HOST = "172.16.1.26"

class PerformanceBenchmark:
    def __init__(self):
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "tests": []
        }
    
    async def test_monitoring_endpoint(self, category="network-probes", clear_cache=False):
        """Testa endpoint principal de monitoramento"""
        print(f"\n{'='*80}")
        print(f"TESTE: /api/v1/monitoring/data?category={category}")
        print(f"Cache: {'DISABLED (cleared)' if clear_cache else 'ENABLED'}")
        print(f"{'='*80}")
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            # Limpar cache se solicitado
            if clear_cache:
                try:
                    await client.delete(f"{BACKEND_URL}/api/v1/cache/clear")
                    print("✓ Cache limpo")
                except:
                    pass
            
            # Fazer request
            start = time.time()
            try:
                response = await client.get(
                    f"{BACKEND_URL}/api/v1/monitoring/data",
                    params={"category": category}
                )
                duration_ms = (time.time() - start) * 1000
                
                if response.status_code == 200:
                    data = response.json()
                    total_services = data.get("total", 0)
                    
                    result = {
                        "endpoint": f"/api/v1/monitoring/data?category={category}",
                        "cache_cleared": clear_cache,
                        "status": "SUCCESS",
                        "duration_ms": round(duration_ms, 2),
                        "total_services": total_services,
                        "http_status": 200
                    }
                    
                    print(f"\n✅ SUCESSO!")
                    print(f"   Tempo: {duration_ms:.0f}ms")
                    print(f"   Serviços: {total_services}")
                    print(f"   Status: {response.status_code}")
                    
                else:
                    result = {
                        "endpoint": f"/api/v1/monitoring/data?category={category}",
                        "cache_cleared": clear_cache,
                        "status": "ERROR",
                        "duration_ms": round(duration_ms, 2),
                        "http_status": response.status_code,
                        "error": response.text[:200]
                    }
                    
                    print(f"\n❌ ERRO {response.status_code}")
                    print(f"   Tempo: {duration_ms:.0f}ms")
                    print(f"   Error: {response.text[:200]}")
                
                self.results["tests"].append(result)
                return result
                
            except Exception as e:
                duration_ms = (time.time() - start) * 1000
                result = {
                    "endpoint": f"/api/v1/monitoring/data?category={category}",
                    "cache_cleared": clear_cache,
                    "status": "EXCEPTION",
                    "duration_ms": round(duration_ms, 2),
                    "error": str(e)
                }
                
                print(f"\n💥 EXCEPTION!")
                print(f"   Tempo: {duration_ms:.0f}ms")
                print(f"   Error: {str(e)}")
                
                self.results["tests"].append(result)
                return result
    
    async def test_consul_direct(self):
        """Testa acesso direto ao Consul para baseline"""
        print(f"\n{'='*80}")
        print(f"TESTE: Consul Direto (baseline)")
        print(f"{'='*80}")
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            headers = {"X-Consul-Token": CONSUL_TOKEN}
            
            # Teste 1: /catalog/services
            print("\n1️⃣ GET /v1/catalog/services")
            start = time.time()
            resp1 = await client.get(f"http://{CONSUL_HOST}:8500/v1/catalog/services", headers=headers)
            duration1 = (time.time() - start) * 1000
            service_names = resp1.json()
            print(f"   Tempo: {duration1:.0f}ms")
            print(f"   Service names: {len(service_names)}")
            
            # Teste 2: /catalog/service/blackbox_exporter
            print("\n2️⃣ GET /v1/catalog/service/blackbox_exporter")
            start = time.time()
            resp2 = await client.get(
                f"http://{CONSUL_HOST}:8500/v1/catalog/service/blackbox_exporter",
                headers=headers
            )
            duration2 = (time.time() - start) * 1000
            instances = resp2.json()
            print(f"   Tempo: {duration2:.0f}ms")
            print(f"   Instances: {len(instances)}")
            
            # Teste 3: /agent/services
            print("\n3️⃣ GET /v1/agent/services")
            start = time.time()
            resp3 = await client.get(f"http://{CONSUL_HOST}:8500/v1/agent/services", headers=headers)
            duration3 = (time.time() - start) * 1000
            agent_services = resp3.json()
            print(f"   Tempo: {duration3:.0f}ms")
            print(f"   Services: {len(agent_services)}")
            
            return {
                "catalog_services_ms": round(duration1, 2),
                "catalog_service_detail_ms": round(duration2, 2),
                "agent_services_ms": round(duration3, 2)
            }
    
    async def run_full_benchmark(self):
        """Executa benchmark completo"""
        print("\n" + "🔬" * 40)
        print("BENCHMARK COMPLETO - PERFORMANCE")
        print("🔬" * 40)
        print(f"\nData: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Backend: {BACKEND_URL}")
        
        # Teste 1: Consul direto (baseline)
        print("\n" + "="*80)
        print("FASE 1: BASELINE CONSUL DIRETO")
        print("="*80)
        consul_baseline = await self.test_consul_direct()
        
        # Teste 2: Endpoint SEM cache (cold start)
        print("\n" + "="*80)
        print("FASE 2: ENDPOINT SEM CACHE (COLD START)")
        print("="*80)
        cold_result = await self.test_monitoring_endpoint(clear_cache=True)
        
        # Teste 3: Endpoint COM cache (warm)
        print("\n" + "="*80)
        print("FASE 3: ENDPOINT COM CACHE (WARM)")
        print("="*80)
        warm_result = await self.test_monitoring_endpoint(clear_cache=False)
        
        # Teste 4: Endpoint COM cache (should be fast!)
        print("\n" + "="*80)
        print("FASE 4: ENDPOINT COM CACHE (2ª CHAMADA)")
        print("="*80)
        warm_result2 = await self.test_monitoring_endpoint(clear_cache=False)
        
        # Resumo
        print("\n" + "="*80)
        print("RESUMO FINAL")
        print("="*80)
        
        print("\n📊 CONSUL DIRETO (baseline):")
        print(f"   /catalog/services: {consul_baseline['catalog_services_ms']}ms")
        print(f"   /catalog/service/{{name}}: {consul_baseline['catalog_service_detail_ms']}ms")
        print(f"   /agent/services: {consul_baseline['agent_services_ms']}ms")
        
        print("\n📊 BACKEND ENDPOINT:")
        if cold_result['status'] == 'SUCCESS':
            print(f"   Cold start (sem cache): {cold_result['duration_ms']:.0f}ms ({cold_result['total_services']} services)")
        else:
            print(f"   Cold start (sem cache): ERRO - {cold_result.get('error', 'unknown')}")
        
        if warm_result['status'] == 'SUCCESS':
            print(f"   Warm (com cache 1ª): {warm_result['duration_ms']:.0f}ms ({warm_result['total_services']} services)")
        else:
            print(f"   Warm (com cache 1ª): ERRO - {warm_result.get('error', 'unknown')}")
        
        if warm_result2['status'] == 'SUCCESS':
            print(f"   Warm (com cache 2ª): {warm_result2['duration_ms']:.0f}ms ({warm_result2['total_services']} services)")
        else:
            print(f"   Warm (com cache 2ª): ERRO - {warm_result2.get('error', 'unknown')}")
        
        # Análise
        print("\n📈 ANÁLISE:")
        if cold_result['status'] == 'SUCCESS' and warm_result2['status'] == 'SUCCESS':
            improvement = ((cold_result['duration_ms'] - warm_result2['duration_ms']) / cold_result['duration_ms']) * 100
            print(f"   Melhoria com cache: {improvement:.1f}%")
            print(f"   Speedup: {cold_result['duration_ms'] / warm_result2['duration_ms']:.1f}x")
            
            if improvement > 50:
                print("   ✅ Cache funcionando BEM!")
            elif improvement > 20:
                print("   🟡 Cache funcionando mas pode melhorar")
            else:
                print("   ❌ Cache NÃO está funcionando bem!")
        
        # Salvar resultados
        with open("/tmp/benchmark_results.json", "w") as f:
            json.dump(self.results, f, indent=2)
        
        print(f"\n💾 Resultados salvos em: /tmp/benchmark_results.json")
        
        return self.results

async def main():
    benchmark = PerformanceBenchmark()
    results = await benchmark.run_full_benchmark()
    
    print("\n" + "="*80)
    print("")

if __name__ == "__main__":
    asyncio.run(main())
