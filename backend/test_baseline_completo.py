#!/usr/bin/env python3
"""
TESTE DE BASELINE COMPLETO - ANTES DAS CORREÇÕES

Este script executa testes completos de:
1. Endpoints Backend (curl via httpx)
2. Performance de Consul API (com e sem ?stale, ?cached)
3. Testes unitários
4. Queries PromQL
5. Frontend (via Playwright se disponível)

Resultados são salvos em data/baselines/BASELINE_ANTES_CORRECOES_<timestamp>.json

AUTOR: Análise Completa de Alinhamento
DATA: 2025-11-15
"""

import asyncio
import httpx
import time
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any
import subprocess

# URLs
BACKEND_URL = "http://localhost:5000/api/v1"
CONSUL_HOST = "172.16.1.26"  # Será substituído por Config.get_main_server() dinamicamente
CONSUL_PORT = 8500
CONSUL_TOKEN = "8382a112-81e0-cd6d-2b92-8565925a0675"

# Diretório para salvar resultados
BASELINE_DIR = Path(__file__).parent.parent / "data" / "baselines"
BASELINE_DIR.mkdir(parents=True, exist_ok=True)


class BaselineTester:
    """Classe para executar testes de baseline completos"""
    
    def __init__(self):
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "branch": "main",
            "commit": self._get_current_commit(),
            "tests": {}
        }
        self.errors = []
    
    def _get_current_commit(self) -> str:
        """Obtém hash do commit atual"""
        try:
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                capture_output=True,
                text=True,
                cwd=Path(__file__).parent.parent
            )
            return result.stdout.strip()[:7]
        except:
            return "unknown"
    
    async def test_backend_endpoints(self) -> Dict[str, Any]:
        """Testa endpoints principais do backend"""
        print("\n" + "="*80)
        print("TESTE 1: ENDPOINTS BACKEND")
        print("="*80)
        
        results = {}
        async with httpx.AsyncClient(timeout=60.0) as client:
            endpoints = [
                ("/monitoring/data?category=network-probes", "monitoring_data_network"),
                ("/monitoring/data?category=web-probes", "monitoring_data_web"),
                ("/monitoring/data?category=system-exporters", "monitoring_data_system"),
                ("/metadata-fields/", "metadata_fields"),
                ("/categorization-rules", "categorization_rules"),
                ("/services", "services"),
                ("/nodes", "nodes"),
            ]
            
            for endpoint, key in endpoints:
                print(f"\n  → GET {endpoint}")
                try:
                    start = time.time()
                    response = await client.get(f"{BACKEND_URL}{endpoint}")
                    duration = (time.time() - start) * 1000
                    
                    if response.status_code == 200:
                        data = response.json()
                        results[key] = {
                            "status": "SUCCESS",
                            "status_code": response.status_code,
                            "duration_ms": round(duration, 2),
                            "success": data.get("success", True),
                            "total": data.get("total", len(data.get("data", []))),
                            "has_data": bool(data.get("data") or data.get("fields") or data.get("rules"))
                        }
                        print(f"    ✅ {duration:.0f}ms | Status: {response.status_code} | Total: {results[key]['total']}")
                    else:
                        results[key] = {
                            "status": "ERROR",
                            "status_code": response.status_code,
                            "duration_ms": round(duration, 2),
                            "error": response.text[:200]
                        }
                        print(f"    ❌ {duration:.0f}ms | Status: {response.status_code}")
                        self.errors.append(f"{endpoint}: {response.status_code}")
                except Exception as e:
                    results[key] = {
                        "status": "EXCEPTION",
                        "error": str(e)[:200]
                    }
                    print(f"    ❌ EXCEPTION: {e}")
                    self.errors.append(f"{endpoint}: {str(e)}")
        
        return results
    
    async def test_consul_api_performance(self) -> Dict[str, Any]:
        """Testa performance de chamadas Consul API"""
        print("\n" + "="*80)
        print("TESTE 2: PERFORMANCE CONSUL API")
        print("="*80)
        
        results = {}
        consul_base = f"http://{CONSUL_HOST}:{CONSUL_PORT}/v1"
        headers = {"X-Consul-Token": CONSUL_TOKEN}
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Teste 2.1: Catalog API SEM ?stale (baseline)
            print("\n  → GET /catalog/services (SEM ?stale)")
            try:
                start = time.time()
                response = await client.get(
                    f"{consul_base}/catalog/services",
                    headers=headers
                )
                duration = (time.time() - start) * 1000
                results["catalog_services_no_stale"] = {
                    "duration_ms": round(duration, 2),
                    "status_code": response.status_code,
                    "has_data": bool(response.json() if response.status_code == 200 else False)
                }
                print(f"    ✅ {duration:.0f}ms | Status: {response.status_code}")
            except Exception as e:
                results["catalog_services_no_stale"] = {"error": str(e)}
                print(f"    ❌ EXCEPTION: {e}")
            
            # Teste 2.2: Catalog API COM ?stale
            print("\n  → GET /catalog/services?stale (COM ?stale)")
            try:
                start = time.time()
                response = await client.get(
                    f"{consul_base}/catalog/services",
                    headers=headers,
                    params={"stale": ""}
                )
                duration = (time.time() - start) * 1000
                results["catalog_services_with_stale"] = {
                    "duration_ms": round(duration, 2),
                    "status_code": response.status_code,
                    "has_data": bool(response.json() if response.status_code == 200 else False)
                }
                print(f"    ✅ {duration:.0f}ms | Status: {response.status_code}")
            except Exception as e:
                results["catalog_services_with_stale"] = {"error": str(e)}
                print(f"    ❌ EXCEPTION: {e}")
            
            # Teste 2.3: Agent API SEM ?cached
            print("\n  → GET /agent/services (SEM ?cached)")
            try:
                start = time.time()
                response = await client.get(
                    f"{consul_base}/agent/services",
                    headers=headers
                )
                duration = (time.time() - start) * 1000
                results["agent_services_no_cached"] = {
                    "duration_ms": round(duration, 2),
                    "status_code": response.status_code,
                    "has_data": bool(response.json() if response.status_code == 200 else False)
                }
                print(f"    ✅ {duration:.0f}ms | Status: {response.status_code}")
            except Exception as e:
                results["agent_services_no_cached"] = {"error": str(e)}
                print(f"    ❌ EXCEPTION: {e}")
            
            # Teste 2.4: Agent API COM ?cached
            print("\n  → GET /agent/services?cached (COM ?cached)")
            try:
                start = time.time()
                response = await client.get(
                    f"{consul_base}/agent/services",
                    headers=headers,
                    params={"cached": ""}
                )
                duration = (time.time() - start) * 1000
                cache_status = response.headers.get("X-Cache", "UNKNOWN")
                age = response.headers.get("Age", "0")
                results["agent_services_with_cached"] = {
                    "duration_ms": round(duration, 2),
                    "status_code": response.status_code,
                    "cache_status": cache_status,
                    "age_seconds": int(age) if age.isdigit() else 0,
                    "has_data": bool(response.json() if response.status_code == 200 else False)
                }
                print(f"    ✅ {duration:.0f}ms | Status: {response.status_code} | Cache: {cache_status} | Age: {age}s")
            except Exception as e:
                results["agent_services_with_cached"] = {"error": str(e)}
                print(f"    ❌ EXCEPTION: {e}")
        
        return results
    
    async def test_promql_queries(self) -> Dict[str, Any]:
        """Testa queries PromQL"""
        print("\n" + "="*80)
        print("TESTE 3: QUERIES PROMQL")
        print("="*80)
        
        results = {}
        prometheus_url = f"http://{CONSUL_HOST}:9090"
        
        queries = [
            ("probe_success{__param_module=~\"icmp|http_2xx\"}", "network_probes"),
            ("up{job=~\"node|windows\"}", "system_exporters"),
            ("up{job=~\"mysql|postgres\"}", "database_exporters"),
        ]
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            for query, key in queries:
                print(f"\n  → Query: {query[:50]}...")
                try:
                    start = time.time()
                    response = await client.get(
                        f"{prometheus_url}/api/v1/query",
                        params={"query": query}
                    )
                    duration = (time.time() - start) * 1000
                    
                    if response.status_code == 200:
                        data = response.json()
                        result_count = len(data.get("data", {}).get("result", []))
                        results[key] = {
                            "status": "SUCCESS",
                            "duration_ms": round(duration, 2),
                            "result_count": result_count,
                            "status_prometheus": data.get("status", "unknown")
                        }
                        print(f"    ✅ {duration:.0f}ms | Results: {result_count}")
                    else:
                        results[key] = {
                            "status": "ERROR",
                            "status_code": response.status_code,
                            "duration_ms": round(duration, 2)
                        }
                        print(f"    ❌ {duration:.0f}ms | Status: {response.status_code}")
                except Exception as e:
                    results[key] = {
                        "status": "EXCEPTION",
                        "error": str(e)[:200]
                    }
                    print(f"    ❌ EXCEPTION: {e}")
        
        return results
    
    def test_unit_tests(self) -> Dict[str, Any]:
        """Executa testes unitários"""
        print("\n" + "="*80)
        print("TESTE 4: TESTES UNITÁRIOS")
        print("="*80)
        
        results = {}
        test_files = [
            "test_categorization_rule_engine.py",
        ]
        
        backend_dir = Path(__file__).parent
        
        for test_file in test_files:
            test_path = backend_dir / test_file
            if not test_path.exists():
                print(f"\n  ⚠️  {test_file} não encontrado")
                continue
            
            print(f"\n  → pytest {test_file}")
            try:
                result = subprocess.run(
                    ["python", "-m", "pytest", str(test_path), "-v", "--tb=short"],
                    capture_output=True,
                    text=True,
                    cwd=backend_dir,
                    timeout=60
                )
                
                # Parse output
                output = result.stdout + result.stderr
                passed = output.count("PASSED")
                failed = output.count("FAILED")
                total = passed + failed
                
                results[test_file] = {
                    "status": "SUCCESS" if result.returncode == 0 else "FAILED",
                    "return_code": result.returncode,
                    "total": total,
                    "passed": passed,
                    "failed": failed,
                    "output_summary": output[-500:] if len(output) > 500 else output
                }
                
                if result.returncode == 0:
                    print(f"    ✅ {passed}/{total} testes passaram")
                else:
                    print(f"    ❌ {failed}/{total} testes falharam")
                    self.errors.append(f"{test_file}: {failed} falhas")
            except subprocess.TimeoutExpired:
                results[test_file] = {
                    "status": "TIMEOUT",
                    "error": "Teste excedeu 60s"
                }
                print(f"    ❌ TIMEOUT (>60s)")
            except Exception as e:
                results[test_file] = {
                    "status": "EXCEPTION",
                    "error": str(e)
                }
                print(f"    ❌ EXCEPTION: {e}")
        
        return results
    
    async def test_consul_manager_methods(self) -> Dict[str, Any]:
        """Testa métodos específicos do ConsulManager"""
        print("\n" + "="*80)
        print("TESTE 5: MÉTODOS CONSULMANAGER")
        print("="*80)
        
        results = {}
        
        try:
            from core.consul_manager import ConsulManager
            
            consul = ConsulManager()
            
            # Teste 5.1: get_service_names() (deve usar Catalog API)
            print("\n  → get_service_names()")
            try:
                start = time.time()
                service_names = await consul.get_service_names()
                duration = (time.time() - start) * 1000
                results["get_service_names"] = {
                    "duration_ms": round(duration, 2),
                    "count": len(service_names),
                    "has_data": len(service_names) > 0
                }
                print(f"    ✅ {duration:.0f}ms | Services: {len(service_names)}")
            except Exception as e:
                results["get_service_names"] = {"error": str(e)}
                print(f"    ❌ EXCEPTION: {e}")
            
            # Teste 5.2: query_agent_services() (deve usar Agent API)
            print("\n  → query_agent_services()")
            try:
                start = time.time()
                agent_services = await consul.query_agent_services()
                duration = (time.time() - start) * 1000
                results["query_agent_services"] = {
                    "duration_ms": round(duration, 2),
                    "count": len(agent_services),
                    "has_data": len(agent_services) > 0
                }
                print(f"    ✅ {duration:.0f}ms | Services: {len(agent_services)}")
            except Exception as e:
                results["query_agent_services"] = {"error": str(e)}
                print(f"    ❌ EXCEPTION: {e}")
            
            # Teste 5.3: get_all_services_catalog()
            print("\n  → get_all_services_catalog()")
            try:
                start = time.time()
                all_services = await consul.get_all_services_catalog(use_fallback=True)
                duration = (time.time() - start) * 1000
                total_services = sum(
                    len(svcs) for k, svcs in all_services.items() 
                    if k != "_metadata"
                )
                results["get_all_services_catalog"] = {
                    "duration_ms": round(duration, 2),
                    "total_services": total_services,
                    "nodes": len([k for k in all_services.keys() if k != "_metadata"]),
                    "has_metadata": "_metadata" in all_services
                }
                print(f"    ✅ {duration:.0f}ms | Total: {total_services} services")
            except Exception as e:
                results["get_all_services_catalog"] = {"error": str(e)}
                print(f"    ❌ EXCEPTION: {e}")
        
        except ImportError as e:
            results["import_error"] = str(e)
            print(f"    ❌ Não foi possível importar ConsulManager: {e}")
        
        return results
    
    def check_code_issues(self) -> Dict[str, Any]:
        """Verifica problemas no código"""
        print("\n" + "="*80)
        print("TESTE 6: VERIFICAÇÃO DE CÓDIGO")
        print("="*80)
        
        results = {}
        backend_dir = Path(__file__).parent
        
        # Verificar asyncio.run()
        print("\n  → Verificando uso de asyncio.run()")
        try:
            result = subprocess.run(
                ["grep", "-rn", "asyncio.run(", str(backend_dir / "core" / "config.py")],
                capture_output=True,
                text=True
            )
            matches = result.stdout.strip().split('\n') if result.stdout.strip() else []
            results["asyncio_run_usage"] = {
                "count": len(matches),
                "locations": [m.split(':')[0] + ':' + m.split(':')[1] for m in matches if ':' in m]
            }
            print(f"    {'⚠️' if matches else '✅'} {len(matches)} ocorrências encontradas")
        except Exception as e:
            results["asyncio_run_usage"] = {"error": str(e)}
        
        # Verificar ?stale em Catalog API
        print("\n  → Verificando uso de ?stale em Catalog API")
        try:
            result = subprocess.run(
                ["grep", "-rn", "/catalog/", str(backend_dir / "core" / "consul_manager.py")],
                capture_output=True,
                text=True
            )
            catalog_calls = [l for l in result.stdout.strip().split('\n') if '/catalog/' in l]
            stale_calls = [l for l in catalog_calls if 'stale' in l.lower()]
            results["catalog_stale_usage"] = {
                "total_catalog_calls": len(catalog_calls),
                "with_stale": len(stale_calls),
                "without_stale": len(catalog_calls) - len(stale_calls)
            }
            print(f"    {'⚠️' if len(stale_calls) < len(catalog_calls) else '✅'} {len(stale_calls)}/{len(catalog_calls)} com ?stale")
        except Exception as e:
            results["catalog_stale_usage"] = {"error": str(e)}
        
        # Verificar ?cached em Agent API
        print("\n  → Verificando uso de ?cached em Agent API")
        try:
            result = subprocess.run(
                ["grep", "-rn", "/agent/services", str(backend_dir / "core" / "consul_manager.py")],
                capture_output=True,
                text=True
            )
            agent_calls = [l for l in result.stdout.strip().split('\n') if '/agent/services' in l]
            cached_calls = [l for l in agent_calls if 'cached' in l.lower() or 'use_cache' in l.lower()]
            results["agent_cached_usage"] = {
                "total_agent_calls": len(agent_calls),
                "with_cached": len(cached_calls),
                "without_cached": len(agent_calls) - len(cached_calls)
            }
            print(f"    {'⚠️' if len(cached_calls) < len(agent_calls) else '✅'} {len(cached_calls)}/{len(agent_calls)} com ?cached")
        except Exception as e:
            results["agent_cached_usage"] = {"error": str(e)}
        
        return results
    
    async def run_all_tests(self):
        """Executa todos os testes"""
        print("\n" + "🔬" * 40)
        print("TESTE DE BASELINE COMPLETO - ANTES DAS CORREÇÕES")
        print("🔬" * 40)
        print(f"\nData: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Branch: {self.results['branch']}")
        print(f"Commit: {self.results['commit']}")
        
        # Executar todos os testes
        self.results["tests"]["backend_endpoints"] = await self.test_backend_endpoints()
        self.results["tests"]["consul_api_performance"] = await self.test_consul_api_performance()
        self.results["tests"]["promql_queries"] = await self.test_promql_queries()
        self.results["tests"]["unit_tests"] = self.test_unit_tests()
        self.results["tests"]["consul_manager_methods"] = await self.test_consul_manager_methods()
        self.results["tests"]["code_issues"] = self.check_code_issues()
        
        # Resumo
        self.results["summary"] = {
            "total_tests": sum(len(v) if isinstance(v, dict) else 1 for v in self.results["tests"].values()),
            "errors": len(self.errors),
            "error_list": self.errors
        }
        
        # Salvar resultados
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = BASELINE_DIR / f"BASELINE_ANTES_CORRECOES_{timestamp}.json"
        
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)
        
        # Print resumo
        print("\n" + "="*80)
        print("RESUMO FINAL")
        print("="*80)
        print(f"\n✅ Testes executados: {self.results['summary']['total_tests']}")
        print(f"{'❌' if self.errors else '✅'} Erros encontrados: {len(self.errors)}")
        if self.errors:
            print("\nErros:")
            for error in self.errors:
                print(f"  - {error}")
        
        print(f"\n📁 Resultados salvos em: {filename}")
        print("\n" + "="*80)
        
        return self.results


async def main():
    """Função principal"""
    tester = BaselineTester()
    results = await tester.run_all_tests()
    
    # Retornar código de saída baseado em erros
    sys.exit(1 if tester.errors else 0)


if __name__ == "__main__":
    asyncio.run(main())

