"""
Test Script - Fallback Strategy (Master → Clients)

Valida comportamento de fallback quando master está offline:
- Tenta master primeiro (timeout 2s)
- Se falhar, tenta client nodes
- Retorna no primeiro sucesso (fail-fast)
- Metadata indica qual node respondeu

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


async def test_fallback_strategy():
    """
    Testa estratégia de fallback master → clients

    CENÁRIOS TESTADOS:
    1. Todos nodes online: deve usar master
    2. Timeout curto (2s): deve falhar rápido e tentar próximo
    3. Metadata indica tentativas e source correto
    """
    consul = ConsulManager()

    print("\n" + "="*80)
    print("TESTE: Estratégia de Fallback (Master → Clients)")
    print("="*80 + "\n")

    # =====================================================================
    # TESTE 1: Fallback com timeout normal (30s total)
    # =====================================================================
    print("[TESTE 1] Fallback com timeout padrão (2s por node, 30s total)")
    start = time.time()

    services, metadata = await consul.get_services_with_fallback(
        timeout_per_node=2.0,
        global_timeout=30.0
    )

    elapsed = int((time.time() - start) * 1000)

    source_node = metadata.get('source_node', 'unknown')
    source_name = metadata.get('source_name', 'unknown')
    is_master = metadata.get('is_master', False)
    attempts = metadata.get('attempts', 0)
    total_time_ms = metadata.get('total_time_ms', 0)

    print(f"   ✓ Tempo total: {elapsed}ms")
    print(f"   ✓ Source Node: {source_node} ({source_name})")
    print(f"   ✓ Is Master: {is_master}")
    print(f"   ✓ Tentativas: {attempts}")
    print(f"   ✓ Total de serviços: {len(services)}")

    # Validação
    if is_master:
        print(f"   ✅ Master respondeu (cenário ideal)")
        if elapsed < 3000:
            print(f"   ✅ Performance excelente: {elapsed}ms < 3s")
        else:
            print(f"   ⚠️ Master lento: {elapsed}ms > 3s")
    else:
        print(f"   ⚠️ Master offline! Usando fallback: {source_name}")
        print(f"   → Tentativa #{attempts}")
        if elapsed < 5000:
            print(f"   ✅ Fallback rápido: {elapsed}ms < 5s")
        else:
            print(f"   ⚠️ Fallback lento: {elapsed}ms > 5s")

    # =====================================================================
    # TESTE 2: Fallback com timeout agressivo (1s por node)
    # =====================================================================
    print("\n[TESTE 2] Fallback com timeout agressivo (1s por node)")
    start = time.time()

    services2, metadata2 = await consul.get_services_with_fallback(
        timeout_per_node=1.0,
        global_timeout=10.0
    )

    elapsed2 = int((time.time() - start) * 1000)

    source_name2 = metadata2.get('source_name', 'unknown')
    is_master2 = metadata2.get('is_master', False)
    attempts2 = metadata2.get('attempts', 0)

    print(f"   ✓ Tempo total: {elapsed2}ms")
    print(f"   ✓ Source: {source_name2}")
    print(f"   ✓ Is Master: {is_master2}")
    print(f"   ✓ Tentativas: {attempts2}")
    print(f"   ✓ Total de serviços: {len(services2)}")

    if is_master2:
        print(f"   ✅ Master respondeu mesmo com timeout agressivo")
    else:
        print(f"   ⚠️ Master não respondeu em 1s - usando fallback")

    # Validação de fail-fast
    if elapsed2 < 2000 and is_master2:
        print(f"   ✅ FAIL-FAST funcionando: {elapsed2}ms < 2s")
    elif elapsed2 < 3000 and not is_master2:
        print(f"   ✅ FAIL-FAST com fallback: {elapsed2}ms < 3s (1s timeout + 1 retry)")
    else:
        print(f"   ⚠️ Tempo alto: {elapsed2}ms")

    # =====================================================================
    # TESTE 3: Múltiplas chamadas consecutivas (validar consistência)
    # =====================================================================
    print("\n[TESTE 3] Múltiplas chamadas consecutivas (validar consistência)")

    sources = []
    times = []

    for i in range(3):
        start = time.time()
        _, meta = await consul.get_services_with_fallback(timeout_per_node=2.0)
        elapsed = int((time.time() - start) * 1000)

        sources.append(meta.get('source_name', 'unknown'))
        times.append(elapsed)

        print(f"   Chamada #{i+1}: {elapsed}ms - Source: {sources[-1]}")

    # Validar consistência
    if len(set(sources)) == 1:
        print(f"   ✅ Consistência: todas chamadas usaram {sources[0]}")
    else:
        print(f"   ⚠️ Sources diferentes: {set(sources)}")
        print(f"   → Pode indicar que master ficou intermitente")

    avg_time = sum(times) / len(times)
    print(f"   ✓ Tempo médio: {avg_time:.0f}ms")

    if avg_time < 100:
        print(f"   ✅ Performance consistente < 100ms (cache funcionando)")
    elif avg_time < 500:
        print(f"   ⚠️ Performance aceitável < 500ms")
    else:
        print(f"   ❌ Performance ruim > 500ms")

    # =====================================================================
    # RESUMO FINAL
    # =====================================================================
    print("\n" + "="*80)
    print("RESUMO DOS TESTES DE FALLBACK")
    print("="*80)
    print(f"Teste 1 (timeout 2s):  {elapsed}ms - {attempts} tentativa(s) - {source_name}")
    print(f"Teste 2 (timeout 1s):  {elapsed2}ms - {attempts2} tentativa(s) - {source_name2}")
    print(f"Teste 3 (consistência): {avg_time:.0f}ms médio - Sources: {set(sources)}")

    # Recomendações
    print("\n[RECOMENDAÇÕES]")
    if is_master and is_master2:
        print("   ✅ Master online e estável - sistema operando normalmente")
    elif not is_master and not is_master2:
        print("   ⚠️ Master offline - sistema usando fallback")
        print("   → Verificar saúde do master Consul")
    else:
        print("   ⚠️ Master intermitente - investigar rede ou carga")

    print("="*80 + "\n")


if __name__ == "__main__":
    asyncio.run(test_fallback_strategy())
