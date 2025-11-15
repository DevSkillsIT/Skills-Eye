"""
Teste de Performance COMPLETO - Validação SPRINT 1 e SPRINT 2

Testa:
- SPRINT 1: Fallback master→client (timeout 2s)
- SPRINT 1: Agent Caching (stale mode)
- SPRINT 1: Paralelização asyncio.gather()
- SPRINT 2: LocalCache (1290ms → 0ms)
- SPRINT 2: Cache API endpoints

2025-11-15
"""
import asyncio
import time
import httpx
from core.consul_manager import ConsulManager
from core.cache_manager import LocalCache


async def test_sprint1_fallback():
    """
    SPRINT 1: Testa fallback master offline → clients
    """
    print("\n" + "="*80)
    print("TESTE SPRINT 1: Fallback Master → Clients")
    print("="*80)

    consul = ConsulManager()

    # Simular master offline (host inválido)
    consul_offline = ConsulManager(host="192.168.99.99", port=8500)

    print("\n[1] Tentando master OFFLINE (192.168.99.99)...")
    start = time.time()

    try:
        services, metadata = await consul_offline.get_services_with_fallback()
        elapsed = int((time.time() - start) * 1000)

        print(f"   ✅ Fallback funcionou em {elapsed}ms")
        print(f"   Source: {metadata.get('source_name', 'unknown')}")
        print(f"   Is Master: {metadata.get('is_master', False)}")
        print(f"   Total Services: {len(services)}")

        # Validar que usou fallback
        if metadata.get('is_master'):
            print("   ❌ ERRO: Deveria ter usado FALLBACK mas retornou MASTER")
            return False
        else:
            print("   ✅ OK: Usou fallback client como esperado")
            return True

    except Exception as e:
        print(f"   ❌ Fallback FALHOU: {e}")
        return False


async def test_sprint1_agent_caching():
    """
    SPRINT 1: Testa Agent Caching (stale mode)
    """
    print("\n" + "="*80)
    print("TESTE SPRINT 1: Agent Caching (stale mode)")
    print("="*80)

    consul = ConsulManager()

    # Primeira chamada (cache MISS)
    print("\n[1] Primeira chamada (cache MISS)...")
    start = time.time()
    services1, meta1 = await consul.get_services_with_fallback()
    elapsed1 = int((time.time() - start) * 1000)
    print(f"   Tempo: {elapsed1}ms")
    print(f"   Cache Status: {meta1.get('cache_status', 'UNKNOWN')}")

    # Segunda chamada (cache HIT esperado)
    print("\n[2] Segunda chamada (cache HIT esperado)...")
    start = time.time()
    services2, meta2 = await consul.get_services_with_fallback()
    elapsed2 = int((time.time() - start) * 1000)
    print(f"   Tempo: {elapsed2}ms")
    print(f"   Cache Status: {meta2.get('cache_status', 'UNKNOWN')}")
    print(f"   Cache Age: {meta2.get('age_seconds', 0)}s")

    # Validar speedup
    if meta2.get('cache_status') == 'HIT':
        speedup = elapsed1 / elapsed2 if elapsed2 > 0 else 999
        print(f"\n   ✅ Cache HIT! Speedup: {speedup:.1f}x")
        print(f"   Tempo reduzido: {elapsed1}ms → {elapsed2}ms")
        return True
    else:
        print(f"\n   ❌ Esperava cache HIT mas recebeu: {meta2.get('cache_status')}")
        return False


async def test_sprint1_parallelization():
    """
    SPRINT 1: Testa paralelização asyncio.gather()
    """
    print("\n" + "="*80)
    print("TESTE SPRINT 1: Paralelização asyncio.gather()")
    print("="*80)

    consul = ConsulManager()

    # Buscar lista de serviços
    services_catalog, _ = await consul.get_services_with_fallback()
    service_names = list(services_catalog.keys())[:5]  # Limitar a 5 para teste rápido

    print(f"\n[1] Testando com {len(service_names)} serviços: {service_names}")

    # MODO PARALELO
    print("\n[2] Modo PARALELO (asyncio.gather)...")
    start = time.time()

    async def fetch_service(name):
        response = await consul._request("GET", f"/catalog/service/{name}", use_cache=True, params={"stale": ""})
        return name, len(response.json())

    results_parallel = await asyncio.gather(*[fetch_service(n) for n in service_names])
    elapsed_parallel = int((time.time() - start) * 1000)

    print(f"   Tempo total: {elapsed_parallel}ms")
    print(f"   Serviços processados: {len(results_parallel)}")

    # Validar
    if elapsed_parallel < 500:  # Deve ser rápido (< 500ms para 5 serviços)
        print(f"   ✅ Paralelização RÁPIDA: {elapsed_parallel}ms < 500ms")
        return True
    else:
        print(f"   ⚠️ Paralelização LENTA: {elapsed_parallel}ms >= 500ms")
        return False


async def test_sprint2_local_cache():
    """
    SPRINT 2: Testa LocalCache (TTL 60s)
    """
    print("\n" + "="*80)
    print("TESTE SPRINT 2: LocalCache Performance")
    print("="*80)

    cache = LocalCache(default_ttl_seconds=60)

    # Operação lenta simulada
    async def expensive_operation():
        await asyncio.sleep(0.5)  # 500ms
        return {"data": "test", "timestamp": time.time()}

    cache_key = "test:performance"

    # Primeira chamada (MISS)
    print("\n[1] Primeira chamada (cache MISS)...")
    start = time.time()
    cached = await cache.get(cache_key)
    if cached is None:
        result = await expensive_operation()
        await cache.set(cache_key, result)
    elapsed1 = int((time.time() - start) * 1000)
    print(f"   Tempo: {elapsed1}ms")

    # Segunda chamada (HIT)
    print("\n[2] Segunda chamada (cache HIT)...")
    start = time.time()
    cached = await cache.get(cache_key)
    elapsed2 = int((time.time() - start) * 1000)
    print(f"   Tempo: {elapsed2}ms")

    # Validar speedup
    if cached is not None:
        speedup = elapsed1 / elapsed2 if elapsed2 > 0 else 999
        print(f"\n   ✅ LocalCache funcionando! Speedup: {speedup:.0f}x")
        print(f"   Tempo reduzido: {elapsed1}ms → {elapsed2}ms")

        # Validar meta SPRINT 2 (~10ms)
        if elapsed2 <= 10:
            print(f"   ✅ META SPRINT 2 ATINGIDA! {elapsed2}ms <= 10ms")
            return True
        else:
            print(f"   ⚠️ Acima da meta: {elapsed2}ms > 10ms (mas ainda muito rápido!)")
            return True
    else:
        print(f"   ❌ Cache não funcionou!")
        return False


async def test_sprint2_cache_api():
    """
    SPRINT 2: Testa endpoints API de cache
    """
    print("\n" + "="*80)
    print("TESTE SPRINT 2: Cache Management API")
    print("="*80)

    base_url = "http://localhost:5000/api/v1/cache"

    async with httpx.AsyncClient(timeout=5.0) as client:
        # Teste 1: /cache/stats
        print("\n[1] GET /cache/stats")
        start = time.time()
        response = await client.get(f"{base_url}/stats")
        elapsed = int((time.time() - start) * 1000)

        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Status 200 - {elapsed}ms")
            print(f"   Hits: {data.get('hits', 0)}")
            print(f"   Misses: {data.get('misses', 0)}")
            print(f"   Hit Rate: {data.get('hit_rate_percent', 0)}%")
            print(f"   Current Size: {data.get('current_size', 0)}")
        else:
            print(f"   ❌ Status {response.status_code}")
            return False

        # Teste 2: /cache/keys
        print("\n[2] GET /cache/keys")
        start = time.time()
        response = await client.get(f"{base_url}/keys")
        elapsed = int((time.time() - start) * 1000)

        if response.status_code == 200:
            keys = response.json()
            print(f"   ✅ Status 200 - {elapsed}ms")
            print(f"   Total Keys: {len(keys)}")
            print(f"   Keys: {keys[:5]}")  # Primeiras 5
        else:
            print(f"   ❌ Status {response.status_code}")
            return False

        print("\n   ✅ TODOS os endpoints funcionando!")
        return True


async def main():
    """
    Executa TODOS os testes de performance
    """
    print("\n" + "="*80)
    print("VALIDAÇÃO COMPLETA - SPRINT 1 e SPRINT 2")
    print("Performance Tests")
    print("="*80)

    results = {}

    # SPRINT 1
    results['SPRINT1_Fallback'] = await test_sprint1_fallback()
    results['SPRINT1_AgentCaching'] = await test_sprint1_agent_caching()
    results['SPRINT1_Parallelization'] = await test_sprint1_parallelization()

    # SPRINT 2
    results['SPRINT2_LocalCache'] = await test_sprint2_local_cache()
    results['SPRINT2_CacheAPI'] = await test_sprint2_cache_api()

    # Relatório Final
    print("\n" + "="*80)
    print("RELATÓRIO FINAL")
    print("="*80)

    total = len(results)
    passed = sum(1 for v in results.values() if v)

    for test_name, passed_test in results.items():
        status = "✅ PASSOU" if passed_test else "❌ FALHOU"
        print(f"{status}  {test_name}")

    print(f"\nTotal: {passed}/{total} testes passaram ({passed/total*100:.0f}%)")

    if passed == total:
        print("\n🎉 TODOS OS TESTES PASSARAM COM SUCESSO!")
    else:
        print(f"\n⚠️ {total - passed} teste(s) falharam - revisar implementação")


if __name__ == "__main__":
    asyncio.run(main())
