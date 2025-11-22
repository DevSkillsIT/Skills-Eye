#!/usr/bin/env python3
"""
Script de benchmark para validar performance do endpoint /api/v1/nodes.

Este script coleta metricas de performance (baseline/compare) e gera relatorios
com percentis P50/P95/P99 para validar otimizacoes do SPEC-PERF-001.

Data: 2025-11-21
Autor: Claude Code
Versao: 1.0.0

Uso:
    python scripts/bench_nodes.py --mode baseline    # Coleta baseline inicial
    python scripts/bench_nodes.py --mode compare     # Compara com baseline salvo
    python scripts/bench_nodes.py --mode benchmark   # Executa benchmark unico
    python scripts/bench_nodes.py --mode report      # Gera relatorio do ultimo benchmark

Exemplos:
    # Coletar baseline antes das otimizacoes
    python scripts/bench_nodes.py --mode baseline --iterations 30

    # Comparar apos otimizacoes
    python scripts/bench_nodes.py --mode compare --iterations 30

    # Benchmark rapido com menos iteracoes
    python scripts/bench_nodes.py --mode benchmark --iterations 10

Requisitos:
    - Backend rodando em localhost:5000
    - httpx instalado (pip install httpx)
"""

import argparse
import asyncio
import time
import json
import statistics
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

import httpx

# Configuracoes padrao
BASE_URL = "http://localhost:5000/api/v1"
RESULTS_DIR = Path(__file__).parent.parent / "test_results"
BASELINE_FILE = RESULTS_DIR / "nodes_baseline.json"
COMPARE_FILE = RESULTS_DIR / "nodes_compare.json"
REPORT_FILE = RESULTS_DIR / "nodes_benchmark_report.json"

# Cores para output no terminal
class Colors:
    """Cores ANSI para formatacao do terminal"""
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    RESET = "\033[0m"
    BOLD = "\033[1m"


def ensure_results_dir():
    """
    Garante que o diretorio de resultados existe.

    Cria o diretorio test_results se nao existir.
    """
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)


async def benchmark_nodes(iterations: int = 20, warmup: int = 3) -> Dict[str, Any]:
    """
    Executa benchmark do endpoint /api/v1/nodes.

    Realiza chamadas ao endpoint e coleta metricas de tempo de resposta,
    calculando percentis P50, P95, P99 e outras estatisticas.

    Args:
        iterations: Numero de chamadas ao endpoint para o benchmark
        warmup: Numero de chamadas de warmup (nao contabilizadas)

    Returns:
        Dicionario com metricas de performance:
        - p50: Percentil 50 (mediana)
        - p95: Percentil 95
        - p99: Percentil 99
        - avg: Media
        - min: Tempo minimo
        - max: Tempo maximo
        - std_dev: Desvio padrao
        - total_requests: Total de requisicoes
        - success_rate: Taxa de sucesso (%)
        - errors: Lista de erros encontrados
        - raw_times: Tempos brutos de cada requisicao
    """
    times: List[float] = []
    errors: List[str] = []
    success_count = 0

    print(f"\n{Colors.CYAN}[Benchmark]{Colors.RESET} Iniciando benchmark do endpoint /api/v1/nodes")
    print(f"{Colors.CYAN}[Config]{Colors.RESET} Iteracoes: {iterations}, Warmup: {warmup}")

    async with httpx.AsyncClient(timeout=30.0) as client:
        # PASSO 1: Warmup - prepara cache e conexoes
        # Isso evita que o primeiro request seja artificialmente lento
        print(f"\n{Colors.YELLOW}[Warmup]{Colors.RESET} Executando {warmup} requisicoes de warmup...")

        for i in range(warmup):
            try:
                await client.get(f"{BASE_URL}/nodes")
                print(f"  Warmup {i + 1}/{warmup} concluido")
            except Exception as e:
                print(f"  {Colors.YELLOW}Warmup {i + 1} falhou: {e}{Colors.RESET}")

        # PASSO 2: Benchmark principal - coletar metricas
        print(f"\n{Colors.BLUE}[Benchmark]{Colors.RESET} Executando {iterations} requisicoes...")

        for i in range(iterations):
            try:
                # Medir tempo de resposta em milissegundos
                start = time.time()
                response = await client.get(f"{BASE_URL}/nodes")
                elapsed = (time.time() - start) * 1000  # Converter para ms

                # Validar resposta
                if response.status_code == 200:
                    data = response.json()
                    if data.get("success", False):
                        times.append(elapsed)
                        success_count += 1

                        # Mostrar progresso a cada 5 requisicoes
                        if (i + 1) % 5 == 0 or i == iterations - 1:
                            print(f"  Request {i + 1}/{iterations}: {elapsed:.2f}ms")
                    else:
                        errors.append(f"Request {i + 1}: success=False")
                        print(f"  {Colors.RED}Request {i + 1}: success=False{Colors.RESET}")
                else:
                    errors.append(f"Request {i + 1}: HTTP {response.status_code}")
                    print(f"  {Colors.RED}Request {i + 1}: HTTP {response.status_code}{Colors.RESET}")

            except httpx.TimeoutException:
                errors.append(f"Request {i + 1}: Timeout")
                print(f"  {Colors.RED}Request {i + 1}: Timeout{Colors.RESET}")

            except httpx.ConnectError as e:
                errors.append(f"Request {i + 1}: Connection error - {str(e)[:50]}")
                print(f"  {Colors.RED}Request {i + 1}: Connection error{Colors.RESET}")

            except Exception as e:
                errors.append(f"Request {i + 1}: {type(e).__name__} - {str(e)[:50]}")
                print(f"  {Colors.RED}Request {i + 1}: {type(e).__name__}{Colors.RESET}")

    # PASSO 3: Calcular estatisticas
    # Verifica se temos dados suficientes para calcular percentis
    if not times:
        print(f"\n{Colors.RED}[Erro]{Colors.RESET} Nenhuma requisicao bem-sucedida!")
        return {
            "p50": 0,
            "p95": 0,
            "p99": 0,
            "avg": 0,
            "min": 0,
            "max": 0,
            "std_dev": 0,
            "total_requests": iterations,
            "success_count": 0,
            "success_rate": 0,
            "errors": errors,
            "raw_times": [],
            "timestamp": datetime.now().isoformat()
        }

    # Calcular percentis usando quantiles
    # statistics.quantiles divide em n partes iguais
    sorted_times = sorted(times)
    n = len(sorted_times)

    # P50 (mediana)
    p50 = statistics.median(sorted_times)

    # P95 - usar quantiles se temos dados suficientes
    if n >= 20:
        quantiles_20 = statistics.quantiles(sorted_times, n=20)
        p95 = quantiles_20[18]  # 19o valor de 20 partes = 95%
    else:
        # Para poucos dados, usar interpolacao manual
        p95_idx = int(n * 0.95)
        p95 = sorted_times[min(p95_idx, n - 1)]

    # P99 - usar quantiles se temos dados suficientes
    if n >= 100:
        quantiles_100 = statistics.quantiles(sorted_times, n=100)
        p99 = quantiles_100[98]  # 99o valor de 100 partes = 99%
    else:
        # Para poucos dados, usar o maximo ou interpolacao
        p99_idx = int(n * 0.99)
        p99 = sorted_times[min(p99_idx, n - 1)]

    # Outras estatisticas
    avg = statistics.mean(sorted_times)
    std_dev = statistics.stdev(sorted_times) if n > 1 else 0

    result = {
        "p50": round(p50, 2),
        "p95": round(p95, 2),
        "p99": round(p99, 2),
        "avg": round(avg, 2),
        "min": round(min(sorted_times), 2),
        "max": round(max(sorted_times), 2),
        "std_dev": round(std_dev, 2),
        "total_requests": iterations,
        "success_count": success_count,
        "success_rate": round((success_count / iterations) * 100, 2),
        "errors": errors,
        "raw_times": [round(t, 2) for t in times],
        "timestamp": datetime.now().isoformat()
    }

    return result


def print_results(results: Dict[str, Any], title: str = "Resultados"):
    """
    Imprime resultados do benchmark formatados.

    Exibe metricas de performance com cores para facilitar
    identificacao de valores dentro/fora dos limites esperados.

    Args:
        results: Dicionario com metricas do benchmark
        title: Titulo para exibir no cabecalho
    """
    print(f"\n{Colors.BOLD}{'=' * 60}{Colors.RESET}")
    print(f"{Colors.BOLD}{title}{Colors.RESET}")
    print(f"{'=' * 60}")

    # Metricas principais com cores baseadas nos limites do SPEC-PERF-001
    # Limites: P50 < 200ms, P95 < 500ms, P99 < 600ms

    p50 = results.get("p50", 0)
    p95 = results.get("p95", 0)
    p99 = results.get("p99", 0)

    # P50 - verde se < 200ms, amarelo se < 300ms, vermelho se >= 300ms
    p50_color = Colors.GREEN if p50 < 200 else (Colors.YELLOW if p50 < 300 else Colors.RED)
    print(f"  P50 (mediana):    {p50_color}{p50:.2f}ms{Colors.RESET} {'OK' if p50 < 200 else 'ALERTA'}")

    # P95 - verde se < 500ms, amarelo se < 600ms, vermelho se >= 600ms
    p95_color = Colors.GREEN if p95 < 500 else (Colors.YELLOW if p95 < 600 else Colors.RED)
    print(f"  P95:              {p95_color}{p95:.2f}ms{Colors.RESET} {'OK' if p95 < 500 else 'ALERTA'}")

    # P99 - verde se < 600ms, amarelo se < 800ms, vermelho se >= 800ms
    p99_color = Colors.GREEN if p99 < 600 else (Colors.YELLOW if p99 < 800 else Colors.RED)
    print(f"  P99:              {p99_color}{p99:.2f}ms{Colors.RESET} {'OK' if p99 < 600 else 'ALERTA'}")

    print(f"\n  Media:            {results.get('avg', 0):.2f}ms")
    print(f"  Min:              {results.get('min', 0):.2f}ms")
    print(f"  Max:              {results.get('max', 0):.2f}ms")
    print(f"  Desvio Padrao:    {results.get('std_dev', 0):.2f}ms")

    # Taxa de sucesso
    success_rate = results.get("success_rate", 0)
    rate_color = Colors.GREEN if success_rate >= 99 else (Colors.YELLOW if success_rate >= 95 else Colors.RED)
    print(f"\n  Requisicoes:      {results.get('total_requests', 0)}")
    print(f"  Sucesso:          {rate_color}{results.get('success_count', 0)} ({success_rate:.1f}%){Colors.RESET}")

    # Erros
    errors = results.get("errors", [])
    if errors:
        print(f"\n  {Colors.RED}Erros ({len(errors)}):{Colors.RESET}")
        for error in errors[:5]:  # Mostrar apenas os 5 primeiros
            print(f"    - {error}")
        if len(errors) > 5:
            print(f"    ... e mais {len(errors) - 5} erros")

    print(f"\n  Timestamp:        {results.get('timestamp', 'N/A')}")
    print(f"{'=' * 60}\n")


def save_results(results: Dict[str, Any], filepath: Path):
    """
    Salva resultados do benchmark em arquivo JSON.

    Args:
        results: Dicionario com metricas do benchmark
        filepath: Caminho do arquivo para salvar
    """
    ensure_results_dir()

    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"{Colors.GREEN}[Salvo]{Colors.RESET} Resultados salvos em: {filepath}")


def load_results(filepath: Path) -> Optional[Dict[str, Any]]:
    """
    Carrega resultados de benchmark de arquivo JSON.

    Args:
        filepath: Caminho do arquivo para carregar

    Returns:
        Dicionario com metricas ou None se arquivo nao existir
    """
    if not filepath.exists():
        return None

    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


def compare_results(baseline: Dict[str, Any], current: Dict[str, Any]) -> Dict[str, Any]:
    """
    Compara resultados do benchmark atual com baseline.

    Calcula diferencas percentuais entre metricas para identificar
    melhorias ou regressoes de performance.

    Args:
        baseline: Resultados do baseline
        current: Resultados atuais

    Returns:
        Dicionario com diferencas percentuais e status
    """
    comparison = {}

    metrics = ["p50", "p95", "p99", "avg", "min", "max"]

    for metric in metrics:
        base_val = baseline.get(metric, 0)
        curr_val = current.get(metric, 0)

        if base_val > 0:
            # Calcular diferenca percentual
            # Negativo = melhoria (menor tempo)
            diff_pct = ((curr_val - base_val) / base_val) * 100

            comparison[metric] = {
                "baseline": base_val,
                "current": curr_val,
                "diff_ms": round(curr_val - base_val, 2),
                "diff_pct": round(diff_pct, 2),
                "improved": diff_pct < 0
            }
        else:
            comparison[metric] = {
                "baseline": base_val,
                "current": curr_val,
                "diff_ms": curr_val,
                "diff_pct": 0,
                "improved": False
            }

    return comparison


def print_comparison(comparison: Dict[str, Any]):
    """
    Imprime comparacao entre baseline e resultados atuais.

    Exibe diferencas percentuais com cores indicando
    melhorias (verde) ou regressoes (vermelho).

    Args:
        comparison: Dicionario com comparacoes de metricas
    """
    print(f"\n{Colors.BOLD}{'=' * 70}{Colors.RESET}")
    print(f"{Colors.BOLD}Comparacao com Baseline{Colors.RESET}")
    print(f"{'=' * 70}")
    print(f"{'Metrica':<10} {'Baseline':>12} {'Atual':>12} {'Diff (ms)':>12} {'Diff (%)':>12}")
    print(f"{'-' * 70}")

    for metric, data in comparison.items():
        baseline = data["baseline"]
        current = data["current"]
        diff_ms = data["diff_ms"]
        diff_pct = data["diff_pct"]
        improved = data["improved"]

        # Cor baseada em melhoria/regressao
        if improved:
            color = Colors.GREEN
            arrow = "v"
        elif diff_pct > 0:
            color = Colors.RED
            arrow = "^"
        else:
            color = Colors.RESET
            arrow = "="

        print(f"{metric:<10} {baseline:>10.2f}ms {current:>10.2f}ms "
              f"{color}{diff_ms:>+10.2f}ms {diff_pct:>+10.1f}% {arrow}{Colors.RESET}")

    print(f"{'=' * 70}")

    # Resumo
    improvements = sum(1 for d in comparison.values() if d["improved"])
    regressions = sum(1 for d in comparison.values() if d["diff_pct"] > 0)

    if improvements > regressions:
        print(f"\n{Colors.GREEN}[RESULTADO]{Colors.RESET} Performance MELHOROU em {improvements}/{len(comparison)} metricas")
    elif regressions > improvements:
        print(f"\n{Colors.RED}[RESULTADO]{Colors.RESET} Performance PIOROU em {regressions}/{len(comparison)} metricas")
    else:
        print(f"\n{Colors.YELLOW}[RESULTADO]{Colors.RESET} Performance sem mudancas significativas")

    print()


async def run_baseline(iterations: int):
    """
    Executa benchmark e salva como baseline.

    Args:
        iterations: Numero de iteracoes do benchmark
    """
    print(f"\n{Colors.BOLD}[Baseline]{Colors.RESET} Coletando metricas de baseline...")

    results = await benchmark_nodes(iterations=iterations)

    # Adicionar metadados
    results["mode"] = "baseline"
    results["iterations"] = iterations

    print_results(results, "Resultados do Baseline")
    save_results(results, BASELINE_FILE)

    print(f"{Colors.GREEN}[Sucesso]{Colors.RESET} Baseline salvo! Use --mode compare para comparar apos otimizacoes.")


async def run_compare(iterations: int):
    """
    Executa benchmark e compara com baseline existente.

    Args:
        iterations: Numero de iteracoes do benchmark
    """
    # Carregar baseline
    baseline = load_results(BASELINE_FILE)

    if not baseline:
        print(f"{Colors.RED}[Erro]{Colors.RESET} Baseline nao encontrado!")
        print(f"Execute primeiro: python scripts/bench_nodes.py --mode baseline")
        return

    print(f"\n{Colors.BOLD}[Compare]{Colors.RESET} Coletando metricas atuais para comparacao...")

    results = await benchmark_nodes(iterations=iterations)

    # Adicionar metadados
    results["mode"] = "compare"
    results["iterations"] = iterations
    results["baseline_timestamp"] = baseline.get("timestamp")

    print_results(results, "Resultados Atuais")

    # Comparar com baseline
    comparison = compare_results(baseline, results)
    print_comparison(comparison)

    # Salvar resultados da comparacao
    save_results(results, COMPARE_FILE)

    # Salvar relatorio completo
    report = {
        "baseline": baseline,
        "current": results,
        "comparison": comparison,
        "timestamp": datetime.now().isoformat()
    }
    save_results(report, REPORT_FILE)


async def run_benchmark(iterations: int):
    """
    Executa benchmark unico sem salvar como baseline.

    Args:
        iterations: Numero de iteracoes do benchmark
    """
    print(f"\n{Colors.BOLD}[Benchmark]{Colors.RESET} Executando benchmark unico...")

    results = await benchmark_nodes(iterations=iterations)

    # Adicionar metadados
    results["mode"] = "benchmark"
    results["iterations"] = iterations

    print_results(results, "Resultados do Benchmark")

    # Verificar limites do SPEC-PERF-001
    print(f"\n{Colors.BOLD}Verificacao SPEC-PERF-001:{Colors.RESET}")

    checks = [
        ("P50 < 200ms", results["p50"] < 200),
        ("P95 < 500ms", results["p95"] < 500),
        ("P99 < 600ms", results["p99"] < 600),
        ("Taxa sucesso >= 99%", results["success_rate"] >= 99)
    ]

    all_passed = True
    for check_name, passed in checks:
        status = f"{Colors.GREEN}PASS{Colors.RESET}" if passed else f"{Colors.RED}FAIL{Colors.RESET}"
        print(f"  [{status}] {check_name}")
        if not passed:
            all_passed = False

    if all_passed:
        print(f"\n{Colors.GREEN}[SPEC-PERF-001]{Colors.RESET} Todos os criterios atendidos!")
    else:
        print(f"\n{Colors.RED}[SPEC-PERF-001]{Colors.RESET} Alguns criterios NAO foram atendidos!")


def run_report():
    """
    Gera relatorio do ultimo benchmark salvo.
    """
    # Tentar carregar comparacao primeiro
    report = load_results(REPORT_FILE)

    if report:
        print(f"\n{Colors.BOLD}[Report]{Colors.RESET} Carregando ultimo relatorio de comparacao...")
        print(f"Timestamp: {report.get('timestamp')}")

        if "baseline" in report:
            print_results(report["baseline"], "Baseline")

        if "current" in report:
            print_results(report["current"], "Resultado Atual")

        if "comparison" in report:
            print_comparison(report["comparison"])

        return

    # Se nao tem comparacao, mostrar baseline
    baseline = load_results(BASELINE_FILE)

    if baseline:
        print(f"\n{Colors.BOLD}[Report]{Colors.RESET} Carregando baseline...")
        print_results(baseline, "Baseline Salvo")
        return

    # Nenhum resultado encontrado
    print(f"{Colors.RED}[Erro]{Colors.RESET} Nenhum resultado encontrado!")
    print(f"Execute primeiro: python scripts/bench_nodes.py --mode baseline")


def main():
    """
    Funcao principal do script de benchmark.

    Processa argumentos da linha de comando e executa o modo selecionado:
    - baseline: Coleta metricas de referencia
    - compare: Compara com baseline
    - benchmark: Executa benchmark unico
    - report: Exibe ultimo relatorio
    """
    parser = argparse.ArgumentParser(
        description="Benchmark do endpoint /api/v1/nodes para SPEC-PERF-001",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos:
  python scripts/bench_nodes.py --mode baseline    # Coleta baseline
  python scripts/bench_nodes.py --mode compare     # Compara com baseline
  python scripts/bench_nodes.py --mode benchmark   # Benchmark unico
  python scripts/bench_nodes.py --mode report      # Ver ultimo relatorio
        """
    )

    parser.add_argument(
        "--mode",
        choices=["baseline", "compare", "benchmark", "report"],
        default="benchmark",
        help="Modo de execucao (default: benchmark)"
    )

    parser.add_argument(
        "--iterations",
        type=int,
        default=20,
        help="Numero de iteracoes do benchmark (default: 20)"
    )

    parser.add_argument(
        "--warmup",
        type=int,
        default=3,
        help="Numero de requisicoes de warmup (default: 3)"
    )

    args = parser.parse_args()

    print(f"\n{Colors.BOLD}{'=' * 60}{Colors.RESET}")
    print(f"{Colors.BOLD}SPEC-PERF-001 - Benchmark de Performance{Colors.RESET}")
    print(f"{'=' * 60}")
    print(f"Endpoint: {BASE_URL}/nodes")
    print(f"Modo: {args.mode}")

    if args.mode == "report":
        run_report()
    else:
        print(f"Iteracoes: {args.iterations}")
        print(f"Warmup: {args.warmup}")

        # Executar modo selecionado
        if args.mode == "baseline":
            asyncio.run(run_baseline(args.iterations))
        elif args.mode == "compare":
            asyncio.run(run_compare(args.iterations))
        else:  # benchmark
            asyncio.run(run_benchmark(args.iterations))


if __name__ == "__main__":
    main()
