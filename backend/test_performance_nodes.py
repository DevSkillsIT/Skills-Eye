"""
Teste de Performance - Endpoint /api/v1/nodes
SPEC-PERF-001: Baseline e Comparacao

Executar ANTES e DEPOIS das otimizacoes para gerar relatorio comparativo.

Uso:
    # Antes das otimizacoes (salvar baseline)
    python test_performance_nodes.py --mode baseline

    # Depois das otimizacoes (comparar)
    python test_performance_nodes.py --mode compare

    # Apenas testar (sem salvar)
    python test_performance_nodes.py --mode test
"""
import asyncio
import time
import json
import argparse
import statistics
from datetime import datetime
from pathlib import Path
import httpx

# Configuracoes
API_URL = "http://localhost:5000/api/v1"
ITERATIONS = 10
BASELINE_FILE = Path("test_results/nodes_baseline.json")


async def test_nodes_endpoint():
    """Testa endpoint /api/v1/nodes multiplas vezes"""
    results = {
        "timestamp": datetime.now().isoformat(),
        "endpoint": f"{API_URL}/nodes",
        "iterations": ITERATIONS,
        "measurements": [],
        "cache_hits": 0,
        "cache_misses": 0,
        "errors": 0
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        # Limpar cache primeiro (se possivel)
        try:
            await client.post(f"{API_URL}/cache/clear/nodes:list:all")
            print("[INFO] Cache limpo antes dos testes")
        except Exception:
            print("[WARN] Nao foi possivel limpar cache")

        for i in range(ITERATIONS):
            start_time = time.time()
            try:
                response = await client.get(f"{API_URL}/nodes")
                elapsed_ms = (time.time() - start_time) * 1000

                if response.status_code == 200:
                    data = response.json()
                    results["measurements"].append({
                        "iteration": i + 1,
                        "time_ms": round(elapsed_ms, 2),
                        "nodes_count": data.get("total", 0),
                        "success": True
                    })

                    # Primeira iteracao eh cache miss, demais sao hits
                    if i == 0:
                        results["cache_misses"] += 1
                    else:
                        results["cache_hits"] += 1

                    print(f"[{i+1}/{ITERATIONS}] {elapsed_ms:.0f}ms - {data.get('total', 0)} nos")
                else:
                    results["errors"] += 1
                    print(f"[{i+1}/{ITERATIONS}] ERRO: Status {response.status_code}")

            except Exception as e:
                results["errors"] += 1
                elapsed_ms = (time.time() - start_time) * 1000
                results["measurements"].append({
                    "iteration": i + 1,
                    "time_ms": round(elapsed_ms, 2),
                    "nodes_count": 0,
                    "success": False,
                    "error": str(e)
                })
                print(f"[{i+1}/{ITERATIONS}] ERRO: {e}")

            # Esperar 100ms entre iteracoes para nao estressar
            await asyncio.sleep(0.1)

    # Calcular estatisticas
    times = [m["time_ms"] for m in results["measurements"] if m.get("success")]
    if times:
        sorted_times = sorted(times)
        results["statistics"] = {
            "min_ms": round(min(times), 2),
            "max_ms": round(max(times), 2),
            "avg_ms": round(statistics.mean(times), 2),
            "median_ms": round(statistics.median(times), 2),
            "p50_ms": round(statistics.median(times), 2),
            "p95_ms": round(sorted_times[int(len(times) * 0.95) - 1], 2) if len(times) >= 10 else round(sorted_times[-1], 2),
            "p99_ms": round(sorted_times[int(len(times) * 0.99) - 1], 2) if len(times) >= 100 else round(sorted_times[-1], 2),
            "first_ms": times[0] if times else None,  # Cache miss
            "rest_avg_ms": round(statistics.mean(times[1:]), 2) if len(times) > 1 else None  # Cache hits
        }

    return results


def save_baseline(results: dict):
    """Salva resultados como baseline"""
    BASELINE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(BASELINE_FILE, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"\n[BASELINE] Salvo em: {BASELINE_FILE}")


def load_baseline() -> dict:
    """Carrega baseline anterior"""
    if not BASELINE_FILE.exists():
        return None
    with open(BASELINE_FILE, 'r') as f:
        return json.load(f)


def generate_comparison_report(baseline: dict, current: dict):
    """Gera relatorio comparativo"""
    print("\n" + "="*80)
    print("RELATORIO DE PERFORMANCE - SPEC-PERF-001")
    print("="*80)

    print(f"\nBaseline: {baseline['timestamp']}")
    print(f"Current:  {current['timestamp']}")

    print("\n" + "-"*80)
    print("METRICAS DE TEMPO")
    print("-"*80)

    b_stats = baseline.get("statistics", {})
    c_stats = current.get("statistics", {})

    metrics = [
        ("Media", "avg_ms"),
        ("Mediana", "median_ms"),
        ("Minimo", "min_ms"),
        ("Maximo", "max_ms"),
        ("P50", "p50_ms"),
        ("P95", "p95_ms"),
        ("1a Req (cache miss)", "first_ms"),
        ("Resto (cache hits)", "rest_avg_ms"),
    ]

    improvement = 0
    for label, key in metrics:
        b_val = b_stats.get(key)
        c_val = c_stats.get(key)

        if b_val and c_val:
            diff = c_val - b_val
            pct = ((c_val - b_val) / b_val) * 100
            status = "v" if diff < 0 else "^" if diff > 0 else "="

            print(f"{label:25} {b_val:>8.0f}ms -> {c_val:>8.0f}ms  {status} {abs(pct):>5.1f}%")

    print("\n" + "-"*80)
    print("RESUMO")
    print("-"*80)

    # Calcular ganho total
    b_avg = b_stats.get("avg_ms", 0)
    c_avg = c_stats.get("avg_ms", 0)

    if b_avg > 0:
        improvement = ((b_avg - c_avg) / b_avg) * 100
        if improvement > 0:
            print(f"[OK] MELHORIA: {improvement:.1f}% mais rapido")
            print(f"   Tempo medio: {b_avg:.0f}ms -> {c_avg:.0f}ms")
        else:
            print(f"[FALHA] REGRESSAO: {abs(improvement):.1f}% mais lento")
            print(f"   Tempo medio: {b_avg:.0f}ms -> {c_avg:.0f}ms")

    # Verificar criterios de aceitacao
    print("\n" + "-"*80)
    print("CRITERIOS DE ACEITACAO")
    print("-"*80)

    checks = [
        ("Tempo cache miss < 600ms", c_stats.get("first_ms", 999) < 600),
        ("Tempo cache hit < 50ms", c_stats.get("rest_avg_ms", 999) < 50),
        ("Melhoria > 50%", improvement > 50 if b_avg > 0 else False),
        ("Zero erros", current.get("errors", 0) == 0),
    ]

    for label, passed in checks:
        status = "[OK]" if passed else "[FALHA]"
        print(f"  {status} {label}")

    print("\n" + "="*80)

    # Salvar relatorio
    report_file = Path("test_results/nodes_performance_report.md")
    report_file.parent.mkdir(parents=True, exist_ok=True)

    with open(report_file, 'w') as f:
        f.write(f"# Relatorio de Performance - SPEC-PERF-001\n\n")
        f.write(f"**Baseline**: {baseline['timestamp']}\n")
        f.write(f"**Current**: {current['timestamp']}\n\n")
        f.write(f"## Resultados\n\n")
        f.write(f"| Metrica | Antes | Depois | Variacao |\n")
        f.write(f"|---------|-------|--------|----------|\n")

        for label, key in metrics:
            b_val = b_stats.get(key)
            c_val = c_stats.get(key)
            if b_val and c_val:
                pct = ((c_val - b_val) / b_val) * 100
                f.write(f"| {label} | {b_val:.0f}ms | {c_val:.0f}ms | {pct:+.1f}% |\n")

        if b_avg > 0:
            f.write(f"\n## Conclusao\n\n")
            f.write(f"**Melhoria Total**: {improvement:.1f}%\n")

    print(f"\n[REPORT] Salvo em: {report_file}")


async def main():
    parser = argparse.ArgumentParser(description='Teste de performance do endpoint /nodes')
    parser.add_argument('--mode', choices=['baseline', 'compare', 'test'], default='test',
                        help='Modo: baseline (salvar), compare (comparar), test (apenas testar)')
    args = parser.parse_args()

    print("\n" + "="*80)
    print("TESTE DE PERFORMANCE - /api/v1/nodes")
    print(f"Modo: {args.mode.upper()}")
    print("="*80)

    results = await test_nodes_endpoint()

    if args.mode == 'baseline':
        save_baseline(results)
        print("\nEstatisticas do Baseline:")
        for key, value in results.get("statistics", {}).items():
            print(f"  {key}: {value}")

    elif args.mode == 'compare':
        baseline = load_baseline()
        if baseline:
            generate_comparison_report(baseline, results)
        else:
            print("\n[ERRO] Baseline nao encontrado!")
            print(f"   Execute primeiro: python {__file__} --mode baseline")

    else:  # test
        print("\nEstatisticas:")
        for key, value in results.get("statistics", {}).items():
            print(f"  {key}: {value}")


if __name__ == "__main__":
    asyncio.run(main())
