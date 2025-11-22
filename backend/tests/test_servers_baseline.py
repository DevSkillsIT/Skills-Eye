#!/usr/bin/env python3
"""
TESTE DE BASELINE: ServersContext - ANTES DAS MELHORIAS

Este script executa testes completos de:
1. Endpoint /metadata-fields/servers (funcionalidade + performance)
2. Simulação de requests duplicados (4 páginas abertas)
3. Validação de dados retornados
4. Métricas de performance

Resultados são salvos em data/baselines/SERVERS_BASELINE_ANTES_<timestamp>.json

AUTOR: Plano de Teste ServersContext
DATA: 2025-11-16
"""

import asyncio
import httpx
import time
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any
import statistics

# URLs
BACKEND_URL = "http://localhost:5000/api/v1"
ENDPOINT_SERVERS = "/metadata-fields/servers"

# Diretório para salvar resultados
BASELINE_DIR = Path(__file__).parent.parent / "data" / "baselines"
BASELINE_DIR.mkdir(parents=True, exist_ok=True)


class ServersBaselineTester:
    """Classe para executar testes de baseline de servidores"""
    
    def __init__(self):
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "test_type": "servers_baseline_antes",
            "endpoint": ENDPOINT_SERVERS,
            "tests": {}
        }
        self.errors = []
    
    async def test_endpoint_functionality(self) -> Dict[str, Any]:
        """Testa funcionalidade do endpoint /metadata-fields/servers"""
        print("\n" + "="*80)
        print("TESTE 1: FUNCIONALIDADE DO ENDPOINT")
        print("="*80)
        
        results = {
            "status": "PENDING",
            "response_time_ms": 0,
            "status_code": 0,
            "success": False,
            "servers_count": 0,
            "has_master": False,
            "servers_data": []
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                print(f"\n  → GET {ENDPOINT_SERVERS}")
                start = time.time()
                response = await client.get(f"{BACKEND_URL}{ENDPOINT_SERVERS}")
                duration = (time.time() - start) * 1000
                
                results["response_time_ms"] = round(duration, 2)
                results["status_code"] = response.status_code
                
                if response.status_code == 200:
                    data = response.json()
                    results["success"] = data.get("success", False)
                    results["servers_count"] = len(data.get("servers", []))
                    results["has_master"] = bool(data.get("master"))
                    results["servers_data"] = [
                        {
                            "id": s.get("id"),
                            "hostname": s.get("hostname"),
                            "type": s.get("type"),
                            "display_name": s.get("display_name")
                        }
                        for s in data.get("servers", [])[:5]  # Primeiros 5
                    ]
                    results["status"] = "SUCCESS"
                    print(f"    ✅ {duration:.0f}ms | Status: {response.status_code}")
                    print(f"    ✅ Servers: {results['servers_count']} | Master: {results['has_master']}")
                else:
                    results["status"] = "ERROR"
                    self.errors.append(f"Endpoint retornou status {response.status_code}")
                    print(f"    ❌ Status: {response.status_code}")
        except Exception as e:
            results["status"] = "ERROR"
            results["error"] = str(e)
            self.errors.append(f"Erro ao testar endpoint: {e}")
            print(f"    ❌ Erro: {e}")
        
        return results
    
    async def test_duplicate_requests(self) -> Dict[str, Any]:
        """Simula 4 requests simultâneos (como se 4 páginas fossem abertas)"""
        print("\n" + "="*80)
        print("TESTE 2: REQUESTS DUPLICADOS (SIMULAÇÃO)")
        print("="*80)
        
        results = {
            "status": "PENDING",
            "total_requests": 4,
            "requests_times": [],
            "average_time_ms": 0,
            "min_time_ms": 0,
            "max_time_ms": 0,
            "p95_time_ms": 0,
            "all_successful": False
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Simular 4 requests simultâneos (como 4 páginas abertas)
                print("\n  → Simulando 4 requests simultâneos...")
                
                async def make_request(index: int) -> Dict[str, Any]:
                    start = time.time()
                    try:
                        response = await client.get(f"{BACKEND_URL}{ENDPOINT_SERVERS}")
                        duration = (time.time() - start) * 1000
                        return {
                            "index": index,
                            "duration_ms": round(duration, 2),
                            "status_code": response.status_code,
                            "success": response.status_code == 200
                        }
                    except Exception as e:
                        duration = (time.time() - start) * 1000
                        return {
                            "index": index,
                            "duration_ms": round(duration, 2),
                            "status_code": 0,
                            "success": False,
                            "error": str(e)
                        }
                
                # Executar 4 requests em paralelo
                request_results = await asyncio.gather(*[make_request(i) for i in range(4)])
                
                results["requests_times"] = [r["duration_ms"] for r in request_results]
                results["average_time_ms"] = round(statistics.mean(results["requests_times"]), 2)
                results["min_time_ms"] = min(results["requests_times"])
                results["max_time_ms"] = max(results["requests_times"])
                if len(results["requests_times"]) >= 4:
                    results["p95_time_ms"] = round(statistics.quantiles(results["requests_times"], n=100)[94], 2)
                results["all_successful"] = all(r["success"] for r in request_results)
                results["status"] = "SUCCESS" if results["all_successful"] else "ERROR"
                
                print(f"    ✅ Média: {results['average_time_ms']:.0f}ms")
                print(f"    ✅ Min: {results['min_time_ms']:.0f}ms | Max: {results['max_time_ms']:.0f}ms")
                print(f"    ✅ Todos sucesso: {results['all_successful']}")
        except Exception as e:
            results["status"] = "ERROR"
            results["error"] = str(e)
            self.errors.append(f"Erro ao testar requests duplicados: {e}")
            print(f"    ❌ Erro: {e}")
        
        return results
    
    async def test_cache_behavior(self) -> Dict[str, Any]:
        """Testa comportamento do cache (primeira request vs segunda)"""
        print("\n" + "="*80)
        print("TESTE 3: COMPORTAMENTO DO CACHE")
        print("="*80)
        
        results = {
            "status": "PENDING",
            "first_request_ms": 0,
            "second_request_ms": 0,
            "cache_improvement_percent": 0,
            "cache_working": False
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Primeira request (cache miss)
                print("\n  → Primeira request (cache miss)...")
                start = time.time()
                response1 = await client.get(f"{BACKEND_URL}{ENDPOINT_SERVERS}")
                first_duration = (time.time() - start) * 1000
                results["first_request_ms"] = round(first_duration, 2)
                print(f"    ⏱️  {first_duration:.0f}ms")
                
                # Pequeno delay para garantir cache
                await asyncio.sleep(0.1)
                
                # Segunda request (cache hit esperado)
                print("\n  → Segunda request (cache hit esperado)...")
                start = time.time()
                response2 = await client.get(f"{BACKEND_URL}{ENDPOINT_SERVERS}")
                second_duration = (time.time() - start) * 1000
                results["second_request_ms"] = round(second_duration, 2)
                print(f"    ⏱️  {second_duration:.0f}ms")
                
                # Calcular melhoria
                if first_duration > 0:
                    improvement = ((first_duration - second_duration) / first_duration) * 100
                    results["cache_improvement_percent"] = round(improvement, 2)
                    results["cache_working"] = second_duration < first_duration
                    print(f"    ✅ Melhoria: {improvement:.1f}%")
                    print(f"    ✅ Cache funcionando: {results['cache_working']}")
                
                results["status"] = "SUCCESS"
        except Exception as e:
            results["status"] = "ERROR"
            results["error"] = str(e)
            self.errors.append(f"Erro ao testar cache: {e}")
            print(f"    ❌ Erro: {e}")
        
        return results
    
    async def run_all_tests(self):
        """Executa todos os testes"""
        print("\n" + "="*80)
        print("TESTE DE BASELINE: ServersContext - ANTES DAS MELHORIAS")
        print("="*80)
        print(f"Endpoint: {ENDPOINT_SERVERS}")
        print(f"Backend URL: {BACKEND_URL}")
        print(f"Timestamp: {self.results['timestamp']}")
        
        # Executar testes
        self.results["tests"]["functionality"] = await self.test_endpoint_functionality()
        self.results["tests"]["duplicate_requests"] = await self.test_duplicate_requests()
        self.results["tests"]["cache_behavior"] = await self.test_cache_behavior()
        
        # Resumo
        self.results["summary"] = {
            "total_tests": 3,
            "passed_tests": sum(1 for t in self.results["tests"].values() if t.get("status") == "SUCCESS"),
            "failed_tests": sum(1 for t in self.results["tests"].values() if t.get("status") == "ERROR"),
            "errors": self.errors
        }
        
        # Salvar resultados
        filename = f"SERVERS_BASELINE_ANTES_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        filepath = BASELINE_DIR / filename
        
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)
        
        # Imprimir resumo
        print("\n" + "="*80)
        print("RESUMO FINAL")
        print("="*80)
        print(f"✅ Testes passados: {self.results['summary']['passed_tests']}/{self.results['summary']['total_tests']}")
        print(f"❌ Testes falhados: {self.results['summary']['failed_tests']}/{self.results['summary']['total_tests']}")
        print(f"\n📁 Resultados salvos em: {filepath}")
        
        if self.errors:
            print("\n⚠️  ERROS ENCONTRADOS:")
            for error in self.errors:
                print(f"  - {error}")
        
        return self.results


async def main():
    """Função principal"""
    tester = ServersBaselineTester()
    await tester.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())

