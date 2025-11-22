"""
Test Script - Performance Paralelo vs Sequencial

Compara performance de chamadas paralelas vs sequenciais:
- Sequencial: for loop com await
- Paralelo: asyncio.gather()

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


async def test_performance_comparison():
    """
    Compara performance sequencial vs paralelo

    EXPECTATIVA:
    - Sequencial: ~1388ms (testado)
    - Paralelo: ~300ms (4-5x mais rapido)
    """
    consul = ConsulManager()

    print("\n" + "="*80)
    print("TESTE: Performance Paralelo vs Sequencial")
    print("="*80 + "\n")

    # =====================================================================
    # TESTE 1: Buscar servicos (obtem lista de servicos)
    # =====================================================================
    print("[PREPARACAO] Buscando lista de servicos...")
    services_catalog, metadata = await consul.get_services_with_fallback()
    service_names = list(services_catalog.keys())

    print(f"   -> Total de servicos: {len(service_names)}")
    print(f"   -> Servicos: {service_names}\n")

    # =====================================================================
    # TESTE 2: MODO SEQUENCIAL (loop tradicional)
    # =====================================================================
    print("[TESTE 1] MODO SEQUENCIAL - for loop com await")
    start = time.time()

    sequential_results = []
    for service_name in service_names:
        try:
            detail_response = await consul._request(
                "GET",
                f"/catalog/service/{service_name}",
                use_cache=True,
                params={"stale": ""}
            )
            instances = detail_response.json()
            sequential_results.append((service_name, len(instances)))
        except Exception as e:
            logger.error(f"Erro sequencial em {service_name}: {e}")
            sequential_results.append((service_name, 0))

    elapsed_sequential = int((time.time() - start) * 1000)

    print(f"   -> Tempo total: {elapsed_sequential}ms")
    print(f"   -> Servicos processados: {len(sequential_results)}")
    total_instances_seq = sum(count for _, count in sequential_results)
    print(f"   -> Total de instancias: {total_instances_seq}")

    # Detalhamento
    for svc_name, count in sequential_results:
        print(f"      - {svc_name}: {count} instancias")

    # =====================================================================
    # TESTE 3: MODO PARALELO (asyncio.gather)
    # =====================================================================
    print(f"\n[TESTE 2] MODO PARALELO - asyncio.gather()")
    start = time.time()

    async def fetch_service_details(service_name: str):
        try:
            detail_response = await consul._request(
                "GET",
                f"/catalog/service/{service_name}",
                use_cache=True,
                params={"stale": ""}
            )
            instances = detail_response.json()
            return (service_name, len(instances))
        except Exception as e:
            logger.error(f"Erro paralelo em {service_name}: {e}")
            return (service_name, 0)

    # EXECUCAO PARALELA - Todas as chamadas simultaneas!
    parallel_results = await asyncio.gather(
        *[fetch_service_details(svc_name) for svc_name in service_names],
        return_exceptions=False
    )

    elapsed_parallel = int((time.time() - start) * 1000)

    print(f"   -> Tempo total: {elapsed_parallel}ms")
    print(f"   -> Servicos processados: {len(parallel_results)}")
    total_instances_par = sum(count for _, count in parallel_results)
    print(f"   -> Total de instancias: {total_instances_par}")

    # Detalhamento
    for svc_name, count in parallel_results:
        print(f"      - {svc_name}: {count} instancias")

    # =====================================================================
    # COMPARACAO E VALIDACAO
    # =====================================================================
    print("\n" + "="*80)
    print("COMPARACAO DE RESULTADOS")
    print("="*80)

    print(f"Tempo Sequencial: {elapsed_sequential}ms")
    print(f"Tempo Paralelo:   {elapsed_parallel}ms")

    if elapsed_sequential > 0:
        speedup = elapsed_sequential / elapsed_parallel
        reduction_percent = ((elapsed_sequential - elapsed_parallel) / elapsed_sequential) * 100

        print(f"\nGANHO DE PERFORMANCE:")
        print(f"   -> Speedup: {speedup:.2f}x mais rapido")
        print(f"   -> Reducao: {reduction_percent:.1f}% menos tempo")
        print(f"   -> Economia: {elapsed_sequential - elapsed_parallel}ms salvos")

        if speedup >= 4.0:
            print(f"   [OK] EXCELENTE! {speedup:.1f}x speedup >= 4x esperado")
        elif speedup >= 2.0:
            print(f"   [OK] BOM! {speedup:.1f}x speedup >= 2x")
        else:
            print(f"   [WARN] Speedup {speedup:.1f}x abaixo do esperado (target: 4x)")

    # Validar integridade dos dados
    print(f"\nVALIDACAO DE INTEGRIDADE:")
    if total_instances_seq == total_instances_par:
        print(f"   [OK] Mesma quantidade de instancias: {total_instances_seq}")
    else:
        print(f"   [ERROR] Diferenca! Seq={total_instances_seq}, Par={total_instances_par}")

    if len(sequential_results) == len(parallel_results):
        print(f"   [OK] Mesma quantidade de servicos processados: {len(sequential_results)}")
    else:
        print(f"   [ERROR] Diferenca! Seq={len(sequential_results)}, Par={len(parallel_results)}")

    # Verificar se resultados sao identicos
    seq_dict = dict(sequential_results)
    par_dict = dict(parallel_results)

    if seq_dict == par_dict:
        print(f"   [OK] Resultados identicos (mesmos dados)")
    else:
        print(f"   [ERROR] Resultados diferentes!")
        for svc_name in seq_dict:
            if seq_dict[svc_name] != par_dict.get(svc_name):
                print(f"      -> {svc_name}: seq={seq_dict[svc_name]}, par={par_dict.get(svc_name)}")

    print("="*80 + "\n")


if __name__ == "__main__":
    asyncio.run(test_performance_comparison())
