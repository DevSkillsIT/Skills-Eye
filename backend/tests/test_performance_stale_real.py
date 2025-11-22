#!/usr/bin/env python3
"""
TESTE DE PERFORMANCE REAL - ?stale vs SEM ?stale

OBJETIVO:
- Medir performance REAL antes e depois de adicionar ?stale
- Testar cenários com nodes offline
- Testar cenários com latência alta
- Validar se ?stale realmente melhora ou piora a performance

IMPORTANTE: Teoria é uma coisa, prática é outra!
SEMPRE validar com testes reais.

AUTOR: Análise Crítica - 16/11/2025
"""

import asyncio
import time
import httpx
import statistics
from typing import Dict, List, Any
from datetime import datetime
import json
from pathlib import Path

# Configuração
CONSUL_HOST = "172.16.1.26"
CONSUL_PORT = 8500
CONSUL_TOKEN = "8382a112-81e0-cd6d-2b92-8565925a0675"
CONSUL_BASE = f"http://{CONSUL_HOST}:{CONSUL_PORT}/v1"
HEADERS = {"X-Consul-Token": CONSUL_TOKEN}

# Diretório para resultados
RESULTS_DIR = Path(__file__).parent.parent / "data" / "baselines"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)


class PerformanceTester:
    """Testador de performance real"""
    
    def __init__(self):
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "tests": {}
        }
    
    async def test_catalog_services_no_stale(self, iterations: int = 10) -> Dict[str, Any]:
        """Testa SEM ?stale (baseline)"""
        print("\n" + "="*80)
        print("TESTE 1: /catalog/services SEM ?stale (BASELINE)")
        print("="*80)
        
        durations = []
        errors = []
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            for i in range(iterations):
                try:
                    start = time.time()
                    response = await client.get(
                        f"{CONSUL_BASE}/catalog/services",
                        headers=HEADERS
                    )
                    duration = (time.time() - start) * 1000
                    durations.append(duration)
                    
                    if response.status_code != 200:
                        errors.append(f"Iteration {i+1}: Status {response.status_code}")
                    
                    print(f"  Iteração {i+1}/{iterations}: {duration:.2f}ms")
                except Exception as e:
                    errors.append(f"Iteration {i+1}: {str(e)[:100]}")
                    print(f"  Iteração {i+1}/{iterations}: ❌ ERRO - {str(e)[:100]}")
        
        stats = {
            "iterations": iterations,
            "successful": len(durations),
            "errors": len(errors),
            "error_list": errors,
            "durations_ms": durations,
            "mean_ms": statistics.mean(durations) if durations else 0,
            "median_ms": statistics.median(durations) if durations else 0,
            "min_ms": min(durations) if durations else 0,
            "max_ms": max(durations) if durations else 0,
            "p95_ms": self._percentile(durations, 95) if durations else 0,
            "p99_ms": self._percentile(durations, 99) if durations else 0,
        }
        
        print(f"\n  ✅ Média: {stats['mean_ms']:.2f}ms")
        print(f"  ✅ Mediana: {stats['median_ms']:.2f}ms")
        print(f"  ✅ P95: {stats['p95_ms']:.2f}ms")
        print(f"  ✅ P99: {stats['p99_ms']:.2f}ms")
        print(f"  ✅ Min: {stats['min_ms']:.2f}ms | Max: {stats['max_ms']:.2f}ms")
        print(f"  {'❌' if errors else '✅'} Erros: {len(errors)}")
        
        return stats
    
    async def test_catalog_services_with_stale(self, iterations: int = 10) -> Dict[str, Any]:
        """Testa COM ?stale"""
        print("\n" + "="*80)
        print("TESTE 2: /catalog/services COM ?stale")
        print("="*80)
        
        durations = []
        errors = []
        stale_ages = []
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            for i in range(iterations):
                try:
                    start = time.time()
                    response = await client.get(
                        f"{CONSUL_BASE}/catalog/services",
                        headers=HEADERS,
                        params={"stale": ""}
                    )
                    duration = (time.time() - start) * 1000
                    durations.append(duration)
                    
                    # Capturar headers de stale
                    age = int(response.headers.get("Age", "0"))
                    last_contact = int(response.headers.get("X-Consul-LastContact", "0"))
                    stale_ages.append(age)
                    
                    if response.status_code != 200:
                        errors.append(f"Iteration {i+1}: Status {response.status_code}")
                    
                    print(f"  Iteração {i+1}/{iterations}: {duration:.2f}ms | Age: {age}s | LastContact: {last_contact}ms")
                except Exception as e:
                    errors.append(f"Iteration {i+1}: {str(e)[:100]}")
                    print(f"  Iteração {i+1}/{iterations}: ❌ ERRO - {str(e)[:100]}")
        
        stats = {
            "iterations": iterations,
            "successful": len(durations),
            "errors": len(errors),
            "error_list": errors,
            "durations_ms": durations,
            "mean_ms": statistics.mean(durations) if durations else 0,
            "median_ms": statistics.median(durations) if durations else 0,
            "min_ms": min(durations) if durations else 0,
            "max_ms": max(durations) if durations else 0,
            "p95_ms": self._percentile(durations, 95) if durations else 0,
            "p99_ms": self._percentile(durations, 99) if durations else 0,
            "stale_ages": stale_ages,
            "mean_age": statistics.mean(stale_ages) if stale_ages else 0,
            "max_age": max(stale_ages) if stale_ages else 0,
        }
        
        print(f"\n  ✅ Média: {stats['mean_ms']:.2f}ms")
        print(f"  ✅ Mediana: {stats['median_ms']:.2f}ms")
        print(f"  ✅ P95: {stats['p95_ms']:.2f}ms")
        print(f"  ✅ P99: {stats['p99_ms']:.2f}ms")
        print(f"  ✅ Min: {stats['min_ms']:.2f}ms | Max: {stats['max_ms']:.2f}ms")
        print(f"  📊 Stale Age - Média: {stats['mean_age']:.1f}s | Max: {stats['max_age']:.1f}s")
        print(f"  {'❌' if errors else '✅'} Erros: {len(errors)}")
        
        return stats
    
    async def test_with_offline_node_simulation(self) -> Dict[str, Any]:
        """Simula cenário com node offline (usando host inválido)"""
        print("\n" + "="*80)
        print("TESTE 3: Simulação de Node Offline")
        print("="*80)
        
        # Testar com host inválido (simula node offline)
        invalid_host = "192.168.99.99"
        invalid_base = f"http://{invalid_host}:{CONSUL_PORT}/v1"
        
        results = {
            "no_stale": {},
            "with_stale": {}
        }
        
        async with httpx.AsyncClient(timeout=5.0) as client:
            # SEM ?stale
            print("\n  → SEM ?stale (deve falhar rápido)")
            try:
                start = time.time()
                response = await client.get(
                    f"{invalid_base}/catalog/services",
                    headers=HEADERS
                )
                duration = (time.time() - start) * 1000
                results["no_stale"] = {
                    "success": True,
                    "duration_ms": duration,
                    "status_code": response.status_code
                }
                print(f"    ✅ {duration:.2f}ms | Status: {response.status_code}")
            except Exception as e:
                duration = (time.time() - start) * 1000
                results["no_stale"] = {
                    "success": False,
                    "duration_ms": duration,
                    "error": str(e)[:200]
                }
                print(f"    ❌ {duration:.2f}ms | Erro: {str(e)[:100]}")
            
            # COM ?stale
            print("\n  → COM ?stale (pode tentar outros nodes)")
            try:
                start = time.time()
                response = await client.get(
                    f"{invalid_base}/catalog/services",
                    headers=HEADERS,
                    params={"stale": ""}
                )
                duration = (time.time() - start) * 1000
                results["with_stale"] = {
                    "success": True,
                    "duration_ms": duration,
                    "status_code": response.status_code
                }
                print(f"    ✅ {duration:.2f}ms | Status: {response.status_code}")
            except Exception as e:
                duration = (time.time() - start) * 1000
                results["with_stale"] = {
                    "success": False,
                    "duration_ms": duration,
                    "error": str(e)[:200]
                }
                print(f"    ❌ {duration:.2f}ms | Erro: {str(e)[:100]}")
        
        return results
    
    async def test_consul_manager_methods(self) -> Dict[str, Any]:
        """Testa métodos do ConsulManager"""
        print("\n" + "="*80)
        print("TESTE 4: Métodos ConsulManager (get_service_names)")
        print("="*80)
        
        results = {}
        
        try:
            from core.consul_manager import ConsulManager
            
            consul = ConsulManager()
            
            # Testar get_service_names() (agora com ?stale)
            print("\n  → get_service_names() (COM ?stale agora)")
            durations = []
            for i in range(10):
                start = time.time()
                service_names = await consul.get_service_names()
                duration = (time.time() - start) * 1000
                durations.append(duration)
                print(f"    Iteração {i+1}/10: {duration:.2f}ms | Services: {len(service_names)}")
            
            results["get_service_names"] = {
                "mean_ms": statistics.mean(durations),
                "median_ms": statistics.median(durations),
                "min_ms": min(durations),
                "max_ms": max(durations),
                "p95_ms": self._percentile(durations, 95),
                "count": len(service_names) if 'service_names' in locals() else 0
            }
            
            print(f"\n  ✅ Média: {results['get_service_names']['mean_ms']:.2f}ms")
            print(f"  ✅ P95: {results['get_service_names']['p95_ms']:.2f}ms")
        
        except Exception as e:
            results["error"] = str(e)
            print(f"  ❌ ERRO: {e}")
        
        return results
    
    def _percentile(self, data: List[float], percentile: float) -> float:
        """Calcula percentil"""
        if not data:
            return 0
        sorted_data = sorted(data)
        index = int(len(sorted_data) * percentile / 100)
        return sorted_data[min(index, len(sorted_data) - 1)]
    
    def compare_results(self, no_stale: Dict, with_stale: Dict) -> Dict[str, Any]:
        """Compara resultados e calcula melhorias"""
        comparison = {
            "mean_improvement_pct": 0,
            "median_improvement_pct": 0,
            "p95_improvement_pct": 0,
            "p99_improvement_pct": 0,
            "faster": "unknown",
            "more_reliable": "unknown"
        }
        
        if no_stale.get("mean_ms") and with_stale.get("mean_ms"):
            mean_improvement = ((no_stale["mean_ms"] - with_stale["mean_ms"]) / no_stale["mean_ms"]) * 100
            comparison["mean_improvement_pct"] = round(mean_improvement, 2)
            comparison["faster"] = "with_stale" if mean_improvement > 0 else "no_stale"
        
        if no_stale.get("median_ms") and with_stale.get("median_ms"):
            median_improvement = ((no_stale["median_ms"] - with_stale["median_ms"]) / no_stale["median_ms"]) * 100
            comparison["median_improvement_pct"] = round(median_improvement, 2)
        
        if no_stale.get("p95_ms") and with_stale.get("p95_ms"):
            p95_improvement = ((no_stale["p95_ms"] - with_stale["p95_ms"]) / no_stale["p95_ms"]) * 100
            comparison["p95_improvement_pct"] = round(p95_improvement, 2)
        
        if no_stale.get("p99_ms") and with_stale.get("p99_ms"):
            p99_improvement = ((no_stale["p99_ms"] - with_stale["p99_ms"]) / no_stale["p99_ms"]) * 100
            comparison["p99_improvement_pct"] = round(p99_improvement, 2)
        
        # Comparar confiabilidade
        no_stale_error_rate = (no_stale.get("errors", 0) / no_stale.get("iterations", 1)) * 100
        with_stale_error_rate = (with_stale.get("errors", 0) / with_stale.get("iterations", 1)) * 100
        comparison["no_stale_error_rate_pct"] = round(no_stale_error_rate, 2)
        comparison["with_stale_error_rate_pct"] = round(with_stale_error_rate, 2)
        comparison["more_reliable"] = "with_stale" if with_stale_error_rate < no_stale_error_rate else "no_stale"
        
        return comparison
    
    async def run_all_tests(self):
        """Executa todos os testes"""
        print("\n" + "🔬" * 40)
        print("TESTE DE PERFORMANCE REAL - ?stale vs SEM ?stale")
        print("🔬" * 40)
        print(f"\nData: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Consul: {CONSUL_HOST}:{CONSUL_PORT}")
        print(f"Iterações por teste: 10")
        
        # Teste 1: SEM ?stale (baseline)
        no_stale = await self.test_catalog_services_no_stale(iterations=10)
        self.results["tests"]["no_stale"] = no_stale
        
        # Aguardar 2s entre testes
        await asyncio.sleep(2)
        
        # Teste 2: COM ?stale
        with_stale = await self.test_catalog_services_with_stale(iterations=10)
        self.results["tests"]["with_stale"] = with_stale
        
        # Teste 3: Node offline
        offline_test = await self.test_with_offline_node_simulation()
        self.results["tests"]["offline_simulation"] = offline_test
        
        # Teste 4: ConsulManager methods
        consul_methods = await self.test_consul_manager_methods()
        self.results["tests"]["consul_manager_methods"] = consul_methods
        
        # Comparação
        comparison = self.compare_results(no_stale, with_stale)
        self.results["comparison"] = comparison
        
        # Salvar resultados
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = RESULTS_DIR / f"PERFORMANCE_STALE_REAL_{timestamp}.json"
        
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)
        
        # Print resumo
        print("\n" + "="*80)
        print("RESUMO COMPARATIVO")
        print("="*80)
        print(f"\n📊 MÉDIA:")
        print(f"   SEM ?stale: {no_stale['mean_ms']:.2f}ms")
        print(f"   COM ?stale: {with_stale['mean_ms']:.2f}ms")
        print(f"   {'✅' if comparison['mean_improvement_pct'] > 0 else '❌'} Melhoria: {comparison['mean_improvement_pct']:+.2f}%")
        
        print(f"\n📊 P95:")
        print(f"   SEM ?stale: {no_stale['p95_ms']:.2f}ms")
        print(f"   COM ?stale: {with_stale['p95_ms']:.2f}ms")
        print(f"   {'✅' if comparison['p95_improvement_pct'] > 0 else '❌'} Melhoria: {comparison['p95_improvement_pct']:+.2f}%")
        
        print(f"\n📊 CONFIABILIDADE:")
        print(f"   SEM ?stale: {comparison['no_stale_error_rate_pct']:.2f}% erro")
        print(f"   COM ?stale: {comparison['with_stale_error_rate_pct']:.2f}% erro")
        print(f"   {'✅' if comparison['more_reliable'] == 'with_stale' else '❌'} Mais confiável: {comparison['more_reliable']}")
        
        if with_stale.get("mean_age", 0) > 5:
            print(f"\n⚠️  ATENÇÃO: Stale Age médio é {with_stale['mean_age']:.1f}s (dados podem estar desatualizados)")
        
        print(f"\n📁 Resultados salvos em: {filename}")
        print("\n" + "="*80)
        
        return self.results


async def main():
    """Função principal"""
    tester = PerformanceTester()
    results = await tester.run_all_tests()
    
    # Retornar código de saída baseado em resultados
    comparison = results.get("comparison", {})
    if comparison.get("mean_improvement_pct", 0) < -10:  # Piorou mais de 10%
        print("\n⚠️  ATENÇÃO: ?stale piorou a performance significativamente!")
        return 1
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)

