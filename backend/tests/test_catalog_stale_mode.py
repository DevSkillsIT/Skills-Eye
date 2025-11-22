"""
Test Script - Catalog API + Stale Mode Performance

Valida que Stale Reads distribui carga entre servers Consul:
- Catalog API retorna TODOS os serviços (não apenas locais)
- Stale mode permite leitura de qualquer server (não apenas leader)
- Staleness tracking via X-Consul-LastContact header

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


async def test_catalog_stale_mode():
    """
    Testa Catalog API com Stale Mode

    CRITÉRIOS DE SUCESSO:
    - Retorna TODOS os serviços do datacenter (não apenas locais)
    - Staleness < 10s (dados relativamente frescos)
    - Performance ~50ms (rápido devido a stale reads)
    """
    consul = ConsulManager()

    print("\n" + "="*80)
    print("TESTE: Catalog API + Stale Mode")
    print("="*80 + "\n")

    # =====================================================================
    # TESTE 1: Catalog API com fallback (inclui stale mode)
    # =====================================================================
    print("[TESTE 1] Catalog API com use_fallback=True")
    start = time.time()

    all_services = await consul.get_all_services_catalog(use_fallback=True)

    elapsed = int((time.time() - start) * 1000)

    # Extrair metadata
    metadata = all_services.pop("_metadata", {})
    source_node = metadata.get('source_node', 'unknown')
    source_name = metadata.get('source_name', 'unknown')
    is_master = metadata.get('is_master', False)
    total_time_ms = metadata.get('total_time_ms', 0)
    staleness_ms = metadata.get('staleness_ms', 0)
    cache_status = metadata.get('cache_status', 'MISS')
    age_seconds = metadata.get('age_seconds', 0)

    print(f"   ✓ Tempo total: {elapsed}ms")
    print(f"   ✓ Source Node: {source_node} ({source_name})")
    print(f"   ✓ Is Master: {is_master}")
    print(f"   ✓ Staleness: {staleness_ms}ms")
    print(f"   ✓ Cache Status: {cache_status}")
    print(f"   ✓ Cache Age: {age_seconds}s")

    # Contar serviços por node
    services_per_node = {}
    total_services = 0

    for node_name, services in all_services.items():
        count = len(services)
        services_per_node[node_name] = count
        total_services += count

    print(f"\n   ✓ Total de serviços: {total_services}")
    print(f"   ✓ Distribuição por node:")
    for node_name, count in sorted(services_per_node.items()):
        print(f"      - {node_name}: {count} serviços")

    # =====================================================================
    # VALIDAÇÕES
    # =====================================================================
    print("\n[VALIDAÇÕES]")

    # Validação 1: Deve ter serviços
    if total_services > 0:
        print(f"   ✅ Retornou {total_services} serviços")
    else:
        print(f"   ❌ ERRO: Nenhum serviço retornado!")
        return

    # Validação 2: Deve ter múltiplos nodes (confirma que não é apenas local)
    if len(services_per_node) > 1:
        print(f"   ✅ Dados de {len(services_per_node)} nodes diferentes (Catalog API funcionando)")
    elif len(services_per_node) == 1:
        print(f"   ⚠️ Apenas 1 node retornado - pode ser cluster single-node ou problema")
    else:
        print(f"   ❌ ERRO: Nenhum node retornado!")

    # Validação 3: Staleness aceitável (<10s)
    if staleness_ms < 10000:
        print(f"   ✅ Staleness aceitável: {staleness_ms}ms < 10s")
    else:
        print(f"   ⚠️ Staleness alto: {staleness_ms}ms > 10s (dados podem estar desatualizados)")

    # Validação 4: Performance aceitável (<100ms)
    if elapsed < 100:
        print(f"   ✅ Performance excelente: {elapsed}ms < 100ms")
    elif elapsed < 500:
        print(f"   ⚠️ Performance aceitável: {elapsed}ms < 500ms")
    else:
        print(f"   ❌ Performance ruim: {elapsed}ms > 500ms")

    # =====================================================================
    # TESTE 2: Catalog API SEM fallback (direto no host configurado)
    # =====================================================================
    print("\n[TESTE 2] Catalog API com use_fallback=False")
    start = time.time()

    try:
        all_services_no_fallback = await consul.get_all_services_catalog(use_fallback=False)
        elapsed_no_fallback = int((time.time() - start) * 1000)

        metadata_no_fallback = all_services_no_fallback.pop("_metadata", {})
        total_no_fallback = sum(len(svcs) for svcs in all_services_no_fallback.values())

        print(f"   ✓ Tempo: {elapsed_no_fallback}ms")
        print(f"   ✓ Total de serviços: {total_no_fallback}")
        print(f"   ✓ Source: {metadata_no_fallback.get('source_name', 'unknown')}")

        # Comparar resultados
        if total_no_fallback == total_services:
            print(f"   ✅ Mesma quantidade de serviços com/sem fallback ({total_services})")
        else:
            print(f"   ⚠️ Diferença: com fallback={total_services}, sem fallback={total_no_fallback}")

    except Exception as e:
        print(f"   ❌ ERRO sem fallback: {e}")
        print(f"   → Fallback é necessário quando master está offline")

    # =====================================================================
    # RESUMO FINAL
    # =====================================================================
    print("\n" + "="*80)
    print("RESUMO DOS TESTES")
    print("="*80)
    print(f"Catalog API retornou {total_services} serviços de {len(services_per_node)} nodes")
    print(f"Tempo de resposta: {elapsed}ms")
    print(f"Staleness: {staleness_ms}ms")
    print(f"Source: {source_name} (master={is_master})")
    print("="*80 + "\n")


if __name__ == "__main__":
    asyncio.run(test_catalog_stale_mode())
