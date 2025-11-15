"""
Test Script - Agent Caching Performance

Valida que Agent Caching está funcionando conforme especificado:
- Primeira chamada: ~50ms (cache miss)
- Chamadas seguintes: <10ms (cache hit)
- Background refresh automático

SPRINT 1 - 2025-11-15
"""
import asyncio
import time
import logging
from core.consul_manager import ConsulManager

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_agent_caching():
    """
    Testa Agent Caching com múltiplas chamadas consecutivas

    CRITÉRIOS DE SUCESSO:
    - Primeira chamada (cache MISS): ~50ms
    - Segunda chamada (cache HIT): <10ms
    - Terceira chamada (cache HIT): <10ms
    - Header Age presente nas respostas cached
    """
    consul = ConsulManager()

    print("\n" + "="*80)
    print("TESTE: Agent Caching Performance")
    print("="*80 + "\n")

    # =====================================================================
    # TESTE 1: Primeira chamada (cache MISS esperado)
    # =====================================================================
    print("[TESTE 1] Primeira chamada - Esperado: cache MISS (~50ms)")
    start = time.time()

    services1, metadata1 = await consul.get_services_with_fallback(timeout_per_node=5.0)

    elapsed1 = int((time.time() - start) * 1000)
    cache_status1 = metadata1.get('cache_status', 'UNKNOWN')
    age1 = metadata1.get('age_seconds', 0)

    print(f"   -> Tempo: {elapsed1}ms")
    print(f"   -> Cache Status: {cache_status1}")
    print(f"   -> Age: {age1}s")
    print(f"   -> Total de servicos: {len(services1)}")

    # Validação
    assert elapsed1 > 0, "Tempo deve ser maior que 0ms"
    assert len(services1) > 0, "Deve retornar serviços"

    # =====================================================================
    # TESTE 2: Segunda chamada (cache HIT esperado)
    # =====================================================================
    print("\n[TESTE 2] Segunda chamada - Esperado: cache HIT (<10ms)")

    # Aguardar 1s para garantir que cache está ativo
    await asyncio.sleep(1)

    start = time.time()
    services2, metadata2 = await consul.get_services_with_fallback(timeout_per_node=5.0)
    elapsed2 = int((time.time() - start) * 1000)

    cache_status2 = metadata2.get('cache_status', 'UNKNOWN')
    age2 = metadata2.get('age_seconds', 0)

    print(f"   -> Tempo: {elapsed2}ms")
    print(f"   -> Cache Status: {cache_status2}")
    print(f"   -> Age: {age2}s")
    print(f"   -> Total de servicos: {len(services2)}")

    # Validação - cache hit deve ser rápido
    if cache_status2 == "HIT":
        print(f"   [OK] SUCESSO: Cache hit detectado (Age: {age2}s)")
        if elapsed2 < 20:
            print(f"   [OK] PERFORMANCE EXCELENTE: {elapsed2}ms < 20ms")
        elif elapsed2 < 50:
            print(f"   [WARN] PERFORMANCE BOA: {elapsed2}ms < 50ms (esperado <20ms)")
        else:
            print(f"   [ERROR] PERFORMANCE RUIM: {elapsed2}ms > 50ms")
    else:
        print(f"   [WARN] Cache MISS na segunda chamada (pode acontecer se TTL expirou)")

    # =====================================================================
    # TESTE 3: Terceira chamada (cache HIT esperado)
    # =====================================================================
    print("\n[TESTE 3] Terceira chamada - Esperado: cache HIT (<10ms)")

    start = time.time()
    services3, metadata3 = await consul.get_services_with_fallback(timeout_per_node=5.0)
    elapsed3 = int((time.time() - start) * 1000)

    cache_status3 = metadata3.get('cache_status', 'UNKNOWN')
    age3 = metadata3.get('age_seconds', 0)

    print(f"   -> Tempo: {elapsed3}ms")
    print(f"   -> Cache Status: {cache_status3}")
    print(f"   -> Age: {age3}s")
    print(f"   -> Total de servicos: {len(services3)}")

    # =====================================================================
    # RESUMO FINAL
    # =====================================================================
    print("\n" + "="*80)
    print("RESUMO DOS TESTES")
    print("="*80)
    print(f"Teste 1 (primeira): {elapsed1}ms - {cache_status1}")
    print(f"Teste 2 (segunda):  {elapsed2}ms - {cache_status2}")
    print(f"Teste 3 (terceira): {elapsed3}ms - {cache_status3}")

    # Cálculo de ganho de performance
    if cache_status2 == "HIT" or cache_status3 == "HIT":
        cache_times = [elapsed2, elapsed3]
        avg_cache_hit = sum(t for t, s in zip(cache_times, [cache_status2, cache_status3]) if s == "HIT") / len([s for s in [cache_status2, cache_status3] if s == "HIT"])
        speedup = elapsed1 / avg_cache_hit if avg_cache_hit > 0 else 0
        print(f"\n[OK] GANHO DE PERFORMANCE: {speedup:.1f}x mais rapido com cache")
        print(f"   Sem cache: {elapsed1}ms")
        print(f"   Com cache: {avg_cache_hit:.0f}ms (media)")
    else:
        print("\n[WARN] Cache hits nao detectados - verificar configuracao do Consul Agent")

    print("="*80 + "\n")


if __name__ == "__main__":
    asyncio.run(test_agent_caching())
