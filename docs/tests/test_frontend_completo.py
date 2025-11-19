#!/usr/bin/env python3
"""
TESTE COMPLETO DO FRONTEND - Skills Eye
========================================
Valida que TODAS as páginas de monitoramento estão usando a API corrigida
e retornando dados completos.

CATEGORIAS TESTADAS:
- network-probes (ICMP, TCP, etc)
- web-probes (HTTP, HTTPS)
- system-exporters (node_exporter, windows_exporter)
- database-exporters (mysql, postgres, redis)
"""

import asyncio
import httpx
import time
import json
from typing import Dict, List, Any

BACKEND_URL = "http://localhost:5000"
FRONTEND_URL = "http://localhost:8081"

CATEGORIES = [
    "network-probes",
    "web-probes", 
    "system-exporters",
    "database-exporters"
]

async def test_category(category: str) -> Dict[str, Any]:
    """
    Testa uma categoria específica
    """
    print(f"\n{'='*80}")
    print(f"TESTANDO CATEGORIA: {category}")
    print(f"{'='*80}")
    
    start = time.time()
    
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            # Testar endpoint backend
            response = await client.get(
                f"{BACKEND_URL}/api/v1/monitoring/data",
                params={"category": category}
            )
            elapsed = (time.time() - start) * 1000
            
            if response.status_code == 200:
                data = response.json()
                services = data.get("data", [])
                total = data.get("total", 0)
                
                print(f"\n✅ SUCESSO!")
                print(f"   Status: {response.status_code}")
                print(f"   Tempo: {elapsed:.0f}ms")
                print(f"   Serviços: {total}")
                print(f"   Categoria: {data.get('category')}")
                
                # Validar estrutura de dados
                if services and len(services) > 0:
                    sample = services[0]
                    print(f"\n📋 Exemplo de serviço:")
                    print(f"   ID: {sample.get('ID', 'N/A')}")
                    print(f"   Service: {sample.get('Service', 'N/A')}")
                    print(f"   Node: {sample.get('Node', 'N/A')}")
                    print(f"   Meta.module: {sample.get('Meta', {}).get('module', 'N/A')}")
                    print(f"   Meta.company: {sample.get('Meta', {}).get('company', 'N/A')}")
                
                # Validar campos esperados
                available_fields = data.get("available_fields", [])
                print(f"\n📊 Campos disponíveis: {len(available_fields)}")
                if available_fields:
                    field_names = [f['name'] for f in available_fields[:5]]
                    print(f"   Primeiros 5: {', '.join(field_names)}")
                
                return {
                    "category": category,
                    "status": "success",
                    "status_code": response.status_code,
                    "time_ms": elapsed,
                    "total_services": total,
                    "has_data": total > 0,
                    "available_fields": len(available_fields)
                }
            else:
                print(f"\n❌ ERRO!")
                print(f"   Status: {response.status_code}")
                print(f"   Tempo: {elapsed:.0f}ms")
                print(f"   Body: {response.text[:200]}")
                
                return {
                    "category": category,
                    "status": "error",
                    "status_code": response.status_code,
                    "time_ms": elapsed,
                    "error": response.text[:200]
                }
                
    except Exception as e:
        elapsed = (time.time() - start) * 1000
        print(f"\n💥 EXCEÇÃO!")
        print(f"   Erro: {str(e)}")
        print(f"   Tempo: {elapsed:.0f}ms")
        
        return {
            "category": category,
            "status": "exception",
            "time_ms": elapsed,
            "error": str(e)
        }


async def test_frontend_routes():
    """
    Testa se rotas do frontend estão acessíveis
    """
    print(f"\n{'='*80}")
    print(f"TESTANDO ROTAS DO FRONTEND")
    print(f"{'='*80}")
    
    routes = [
        "/monitoring/network-probes",
        "/monitoring/web-probes",
        "/monitoring/system-exporters",
        "/monitoring/database-exporters"
    ]
    
    results = []
    
    async with httpx.AsyncClient(timeout=10) as client:
        for route in routes:
            url = f"{FRONTEND_URL}{route}"
            try:
                start = time.time()
                response = await client.get(url, follow_redirects=True)
                elapsed = (time.time() - start) * 1000
                
                status = "✅" if response.status_code == 200 else "❌"
                print(f"\n{status} {route}")
                print(f"   Status: {response.status_code}")
                print(f"   Tempo: {elapsed:.0f}ms")
                
                results.append({
                    "route": route,
                    "status_code": response.status_code,
                    "time_ms": elapsed,
                    "success": response.status_code == 200
                })
                
            except Exception as e:
                print(f"\n❌ {route}")
                print(f"   Erro: {str(e)}")
                results.append({
                    "route": route,
                    "error": str(e),
                    "success": False
                })
    
    return results


async def test_cache_effectiveness():
    """
    Testa efetividade do cache fazendo múltiplas chamadas
    """
    print(f"\n{'='*80}")
    print(f"TESTANDO EFETIVIDADE DO CACHE")
    print(f"{'='*80}")
    
    category = "network-probes"
    
    times = []
    
    async with httpx.AsyncClient(timeout=30) as client:
        # Fazer 5 chamadas consecutivas
        for i in range(1, 6):
            start = time.time()
            response = await client.get(
                f"{BACKEND_URL}/api/v1/monitoring/data",
                params={"category": category}
            )
            elapsed = (time.time() - start) * 1000
            times.append(elapsed)
            
            data = response.json()
            total = data.get("total", 0)
            
            print(f"\nChamada #{i}:")
            print(f"   Tempo: {elapsed:.0f}ms")
            print(f"   Serviços: {total}")
            
            # Aguardar 100ms entre chamadas
            await asyncio.sleep(0.1)
    
    # Análise
    first_call = times[0]
    avg_cached = sum(times[1:]) / len(times[1:])
    improvement = ((first_call - avg_cached) / first_call) * 100
    
    print(f"\n📊 ANÁLISE DO CACHE:")
    print(f"   1ª chamada (cold): {first_call:.0f}ms")
    print(f"   Média 2-5 (warm): {avg_cached:.0f}ms")
    print(f"   Melhoria: {improvement:.1f}%")
    
    if improvement > 80:
        print(f"   Status: ✅ EXCELENTE (cache muito efetivo)")
    elif improvement > 50:
        print(f"   Status: ✅ BOM (cache funcionando)")
    elif improvement > 20:
        print(f"   Status: 🟡 REGULAR (cache funcionando parcialmente)")
    else:
        print(f"   Status: ❌ RUIM (cache não funcionando)")
    
    return {
        "first_call_ms": first_call,
        "avg_cached_ms": avg_cached,
        "improvement_pct": improvement,
        "all_times": times
    }


async def main():
    print("🔬" * 40)
    print("TESTE COMPLETO DO FRONTEND - Skills Eye")
    print("🔬" * 40)
    print(f"\nData: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Backend: {BACKEND_URL}")
    print(f"Frontend: {FRONTEND_URL}")
    
    # TESTE 1: Backend endpoints por categoria
    print(f"\n{'#'*80}")
    print("PARTE 1: TESTE DE BACKEND (API)")
    print(f"{'#'*80}")
    
    category_results = []
    for category in CATEGORIES:
        result = await test_category(category)
        category_results.append(result)
    
    # TESTE 2: Frontend routes
    print(f"\n{'#'*80}")
    print("PARTE 2: TESTE DE ROTAS DO FRONTEND")
    print(f"{'#'*80}")
    
    frontend_results = await test_frontend_routes()
    
    # TESTE 3: Cache effectiveness
    print(f"\n{'#'*80}")
    print("PARTE 3: TESTE DE EFETIVIDADE DO CACHE")
    print(f"{'#'*80}")
    
    cache_result = await test_cache_effectiveness()
    
    # RESUMO FINAL
    print(f"\n{'='*80}")
    print("RESUMO GERAL")
    print(f"{'='*80}")
    
    # Backend API
    print(f"\n📊 BACKEND API ({len(category_results)} categorias):")
    success_count = sum(1 for r in category_results if r.get("status") == "success")
    avg_time = sum(r.get("time_ms", 0) for r in category_results if r.get("status") == "success") / max(success_count, 1)
    total_services = sum(r.get("total_services", 0) for r in category_results)
    
    print(f"   Sucesso: {success_count}/{len(category_results)}")
    print(f"   Tempo médio: {avg_time:.0f}ms")
    print(f"   Total de serviços: {total_services}")
    
    for result in category_results:
        status_icon = "✅" if result.get("status") == "success" else "❌"
        category = result.get("category")
        time_ms = result.get("time_ms", 0)
        total = result.get("total_services", 0)
        print(f"   {status_icon} {category}: {time_ms:.0f}ms → {total} serviços")
    
    # Frontend Routes
    print(f"\n📊 FRONTEND ROUTES ({len(frontend_results)} rotas):")
    frontend_success = sum(1 for r in frontend_results if r.get("success"))
    print(f"   Sucesso: {frontend_success}/{len(frontend_results)}")
    
    for result in frontend_results:
        status_icon = "✅" if result.get("success") else "❌"
        route = result.get("route")
        print(f"   {status_icon} {route}")
    
    # Cache
    print(f"\n📊 CACHE PERFORMANCE:")
    print(f"   1ª chamada: {cache_result['first_call_ms']:.0f}ms")
    print(f"   Média cached: {cache_result['avg_cached_ms']:.0f}ms")
    print(f"   Melhoria: {cache_result['improvement_pct']:.1f}%")
    
    # Status Final
    print(f"\n{'='*80}")
    all_backend_ok = success_count == len(category_results)
    all_frontend_ok = frontend_success == len(frontend_results)
    cache_ok = cache_result['improvement_pct'] > 50
    
    if all_backend_ok and all_frontend_ok and cache_ok:
        print("✅ TODOS OS TESTES PASSARAM!")
        print("   Backend: ✅ Todas categorias funcionando")
        print("   Frontend: ✅ Todas rotas acessíveis")
        print("   Cache: ✅ Funcionando efetivamente")
    else:
        print("⚠️  ALGUNS TESTES FALHARAM:")
        if not all_backend_ok:
            print(f"   Backend: ❌ {len(category_results) - success_count} categorias com erro")
        if not all_frontend_ok:
            print(f"   Frontend: ❌ {len(frontend_results) - frontend_success} rotas inacessíveis")
        if not cache_ok:
            print(f"   Cache: ❌ Melhoria apenas {cache_result['improvement_pct']:.1f}%")
    
    # Salvar resultados
    report = {
        "timestamp": time.strftime('%Y-%m-%d %H:%M:%S'),
        "backend_api": category_results,
        "frontend_routes": frontend_results,
        "cache_performance": cache_result,
        "summary": {
            "backend_success": success_count,
            "backend_total": len(category_results),
            "frontend_success": frontend_success,
            "frontend_total": len(frontend_results),
            "cache_improvement_pct": cache_result['improvement_pct']
        }
    }
    
    with open("/tmp/frontend_test_results.json", "w") as f:
        json.dump(report, f, indent=2)
    
    print(f"\n💾 Resultados salvos em: /tmp/frontend_test_results.json")
    print(f"\n{'='*80}")


if __name__ == "__main__":
    asyncio.run(main())
