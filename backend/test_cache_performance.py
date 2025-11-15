"""
Test Script - Cache Local Performance

Testa a performance do LocalCache (TTL 60s) comparando:
1. Primeira chamada (MISS) - vai buscar do Consul (~1289ms)
2. Segunda chamada (HIT) - retorna do cache local (~10ms)

EXPECTATIVA SPRINT 2:
- Cache MISS: ~1289ms
- Cache HIT: ~10ms (128x mais rápido!)
- Hit rate após warming: >90%

SPRINT 2 - 2025-11-15
"""
import asyncio
import time
import logging
from core.cache_manager import LocalCache

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_cache_performance():
    """
    Testa performance do LocalCache com TTL 60s

    PASSOS:
    1. Simular operação lenta (1289ms) no primeiro acesso
    2. Cache armazena resultado
    3. Segunda chamada retorna do cache (~10ms)
    """
    cache = LocalCache(default_ttl_seconds=60)

    print("\n" + "="*80)
    print("TESTE: LocalCache Performance (TTL 60s)")
    print("="*80 + "\n")

    cache_key = "test:expensive_operation"

    # =====================================================================
    # SIMULAÇÃO: Operação lenta (representa busca no Consul)
    # =====================================================================
    async def expensive_operation():
        """Simula operação lenta que demora ~1289ms"""
        await asyncio.sleep(1.289)  # Simula latência Consul
        return {
            "services": ["service1", "service2", "service3"],
            "total": 3,
            "timestamp": time.time()
        }

    # =====================================================================
    # TESTE 1: CACHE MISS (primeira chamada)
    # =====================================================================
    print("[TESTE 1] CACHE MISS - Primeira chamada (sem cache)")

    start = time.time()
    cached_value = await cache.get(cache_key)

    if cached_value is None:
        print("   -> Cache MISS detectado (esperado)")
        print("   -> Executando operação lenta...")

        value = await expensive_operation()
        await cache.set(cache_key, value)

        elapsed_miss = int((time.time() - start) * 1000)
        print(f"   -> Tempo total: {elapsed_miss}ms")
        print(f"   -> Dados armazenados no cache")
    else:
        print("   [ERROR] Cache HIT inesperado! Cache deveria estar vazio")
        elapsed_miss = int((time.time() - start) * 1000)

    # =====================================================================
    # TESTE 2: CACHE HIT (segunda chamada)
    # =====================================================================
    print(f"\n[TESTE 2] CACHE HIT - Segunda chamada (com cache)")

    start = time.time()
    cached_value = await cache.get(cache_key)
    elapsed_hit = int((time.time() - start) * 1000)

    if cached_value is not None:
        print(f"   -> Cache HIT detectado (esperado)")
        print(f"   -> Tempo total: {elapsed_hit}ms")
        print(f"   -> Dados recuperados do cache:")
        print(f"      - Services: {cached_value['services']}")
        print(f"      - Total: {cached_value['total']}")
    else:
        print("   [ERROR] Cache MISS inesperado! Dados deveriam estar no cache")

    # =====================================================================
    # TESTE 3: Múltiplas chamadas (simular warming do cache)
    # =====================================================================
    print(f"\n[TESTE 3] WARMING - 10 chamadas consecutivas")

    warming_times = []
    for i in range(10):
        start = time.time()
        result = await cache.get(cache_key)
        elapsed = int((time.time() - start) * 1000)
        warming_times.append(elapsed)

    avg_warming = sum(warming_times) / len(warming_times)
    print(f"   -> Tempo médio: {avg_warming:.2f}ms")
    print(f"   -> Tempo mínimo: {min(warming_times)}ms")
    print(f"   -> Tempo máximo: {max(warming_times)}ms")

    # =====================================================================
    # COMPARAÇÃO E VALIDAÇÃO
    # =====================================================================
    print("\n" + "="*80)
    print("ANÁLISE DE PERFORMANCE")
    print("="*80)

    print(f"\nTempo CACHE MISS:  {elapsed_miss}ms")
    print(f"Tempo CACHE HIT:   {elapsed_hit}ms")
    print(f"Tempo médio (10x): {avg_warming:.2f}ms")

    if elapsed_miss > 0 and elapsed_hit > 0:
        speedup = elapsed_miss / elapsed_hit
        reduction_percent = ((elapsed_miss - elapsed_hit) / elapsed_miss) * 100

        print(f"\nGANHO DE PERFORMANCE:")
        print(f"   -> Speedup: {speedup:.1f}x mais rápido")
        print(f"   -> Redução: {reduction_percent:.1f}% menos tempo")
        print(f"   -> Economia: {elapsed_miss - elapsed_hit}ms salvos por request")

        # VALIDAÇÃO
        if speedup >= 100:
            print(f"   [OK] EXCELENTE! Speedup {speedup:.0f}x >= 100x esperado")
        elif speedup >= 50:
            print(f"   [OK] MUITO BOM! Speedup {speedup:.0f}x >= 50x")
        elif speedup >= 10:
            print(f"   [WARN] BOM! Speedup {speedup:.0f}x >= 10x (target: 128x)")
        else:
            print(f"   [ERROR] ABAIXO DO ESPERADO! Speedup {speedup:.1f}x < 10x")

        # Validar se atinge meta SPRINT 2
        if elapsed_hit <= 10:
            print(f"   [OK] META SPRINT 2 ATINGIDA! Cache HIT <= 10ms")
        else:
            print(f"   [WARN] Cache HIT {elapsed_hit}ms acima da meta (10ms)")

    # =====================================================================
    # TESTE 4: Estatísticas do Cache
    # =====================================================================
    print(f"\n[TESTE 4] ESTATÍSTICAS DO CACHE")
    stats = await cache.get_stats()

    print(f"   -> Total Requests: {stats['total_requests']}")
    print(f"   -> Hits: {stats['hits']}")
    print(f"   -> Misses: {stats['misses']}")
    print(f"   -> Hit Rate: {stats['hit_rate_percent']:.1f}%")
    print(f"   -> Tamanho Atual: {stats['current_size']} chaves")
    print(f"   -> TTL: {stats['ttl_seconds']}s")

    if stats['hit_rate_percent'] >= 90:
        print(f"   [OK] Hit Rate {stats['hit_rate_percent']:.1f}% >= 90% (target SPRINT 2)")
    else:
        print(f"   [WARN] Hit Rate {stats['hit_rate_percent']:.1f}% < 90%")

    # =====================================================================
    # TESTE 5: Invalidação
    # =====================================================================
    print(f"\n[TESTE 5] INVALIDAÇÃO DE CACHE")

    print("   -> Invalidando chave...")
    await cache.invalidate(cache_key)

    cached_after_invalidate = await cache.get(cache_key)
    if cached_after_invalidate is None:
        print("   [OK] Invalidacao bem-sucedida (cache vazio)")
    else:
        print("   [ERROR] Dados ainda no cache apos invalidacao")

    print("="*80 + "\n")


if __name__ == "__main__":
    asyncio.run(test_cache_performance())
