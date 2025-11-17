#!/usr/bin/env python3
"""
TESTE DETALHADO FRONTEND: ServersContext - Análise de Requests Duplicados

Este script usa Playwright para testar as páginas do frontend com análise detalhada:
1. Captura TODOS os requests de rede
2. Identifica requests duplicados para /metadata-fields/servers
3. Analisa timing dos requests
4. Verifica se é StrictMode ou outro problema

Resultados são salvos em data/baselines/SERVERS_FRONTEND_DETAILED_<timestamp>.json

AUTOR: Análise Detalhada ServersContext
DATA: 2025-11-16
"""

from playwright.sync_api import sync_playwright
import time
import json
import statistics
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List
from collections import defaultdict

FRONTEND_URL = "http://localhost:8081"
BACKEND_URL = "http://localhost:5000/api/v1"

# Diretório para salvar resultados
BASELINE_DIR = Path(__file__).parent.parent / "data" / "baselines"
BASELINE_DIR.mkdir(parents=True, exist_ok=True)


class DetailedFrontendTester:
    """Classe para executar testes detalhados do frontend"""
    
    def __init__(self):
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "test_type": "servers_frontend_detailed",
            "pages": {}
        }
        self.all_requests = []
    
    def analyze_requests(self, network_requests: List[Dict]) -> Dict[str, Any]:
        """Analisa requests de rede em detalhe"""
        servers_requests = []
        api_requests = []
        duplicate_requests = defaultdict(list)
        
        for req in network_requests:
            url = req.get('url', '')
            
            # Requests de API
            if BACKEND_URL in url:
                api_requests.append(req)
                
                # Requests específicos para /servers
                if '/metadata-fields/servers' in url:
                    servers_requests.append(req)
                    # Identificar duplicados (mesma URL em tempo próximo)
                    key = url
                    duplicate_requests[key].append(req)
        
        # Analisar duplicados
        duplicates_analysis = {}
        for url, requests_list in duplicate_requests.items():
            if len(requests_list) > 1:
                # Calcular diferença de tempo entre requests
                times = sorted([r.get('start_time', 0) for r in requests_list])
                time_diffs = [times[i+1] - times[i] for i in range(len(times)-1)]
                
                duplicates_analysis[url] = {
                    "count": len(requests_list),
                    "time_diffs_ms": [round(td * 1000, 2) for td in time_diffs],
                    "avg_time_diff_ms": round(statistics.mean(time_diffs) * 1000, 2) if time_diffs else 0,
                    "min_time_diff_ms": round(min(time_diffs) * 1000, 2) if time_diffs else 0,
                    "max_time_diff_ms": round(max(time_diffs) * 1000, 2) if time_diffs else 0,
                    "likely_strictmode": any(td < 0.1 for td in time_diffs),  # Requests < 100ms apart
                    "requests": [
                        {
                            "start_time": r.get('start_time', 0),
                            "duration_ms": round(r.get('duration', 0) * 1000, 2),
                            "status": r.get('status', 0)
                        }
                        for r in requests_list
                    ]
                }
        
        return {
            "total_requests": len(network_requests),
            "api_requests_count": len(api_requests),
            "servers_requests_count": len(servers_requests),
            "servers_requests": [
                {
                    "url": r.get('url', ''),
                    "start_time": r.get('start_time', 0),
                    "duration_ms": round(r.get('duration', 0) * 1000, 2),
                    "status": r.get('status', 0),
                    "method": r.get('method', 'GET')
                }
                for r in servers_requests
            ],
            "duplicates": duplicates_analysis,
            "all_api_requests": [
                {
                    "url": r.get('url', '').replace(BACKEND_URL, ''),
                    "duration_ms": round(r.get('duration', 0) * 1000, 2),
                    "status": r.get('status', 0),
                    "method": r.get('method', 'GET')
                }
                for r in api_requests
            ]
        }
    
    def test_page_detailed(self, page, page_path: str, page_name: str) -> Dict[str, Any]:
        """Testa uma página com análise detalhada"""
        print(f"\n{'='*80}")
        print(f"TESTE DETALHADO: {page_name}")
        print(f"{'='*80}")
        print(f"URL: {FRONTEND_URL}{page_path}\n")
        
        network_requests = []
        request_times = {}
        
        def handle_request(request):
            req_id = request.url
            request_times[req_id] = {
                'url': request.url,
                'method': request.method,
                'start_time': time.time()
            }
        
        def handle_response(response):
            url = response.url
            if url in request_times:
                req_data = request_times[url]
                req_data['end_time'] = time.time()
                req_data['duration'] = req_data['end_time'] - req_data['start_time']
                req_data['status'] = response.status
                network_requests.append(req_data)
                del request_times[url]
        
        page.on("request", handle_request)
        page.on("response", handle_response)
        
        # Navegação
        navigation_start = time.time()
        page.goto(f"{FRONTEND_URL}{page_path}", wait_until="networkidle")
        navigation_time = (time.time() - navigation_start) * 1000
        
        # Aguardar um pouco para capturar todos os requests
        time.sleep(2)
        
        # Capturar métricas do browser
        try:
            performance_metrics = page.evaluate("""() => {
                const perfData = window.performance.timing;
                const paintEntries = performance.getEntriesByType('paint');
                const resourceEntries = performance.getEntriesByType('resource');
                
                return {
                    domContentLoaded: perfData.domContentLoadedEventEnd - perfData.navigationStart,
                    loadComplete: perfData.loadEventEnd - perfData.navigationStart,
                    firstPaint: paintEntries.find(e => e.name === 'first-paint')?.startTime || 0,
                    firstContentfulPaint: paintEntries.find(e => e.name === 'first-contentful-paint')?.startTime || 0,
                    resourceCount: resourceEntries.length
                };
            }""")
        except:
            performance_metrics = {}
        
        # Analisar requests
        requests_analysis = self.analyze_requests(network_requests)
        
        result = {
            "page_name": page_name,
            "page_path": page_path,
            "navigation_time_ms": round(navigation_time, 2),
            "performance": performance_metrics,
            "requests_analysis": requests_analysis
        }
        
        # Imprimir resumo
        print(f"  ✅ Navegação: {navigation_time:.0f}ms")
        print(f"  📊 Requests /servers: {requests_analysis['servers_requests_count']}")
        
        if requests_analysis['servers_requests']:
            for i, req in enumerate(requests_analysis['servers_requests'], 1):
                print(f"    {i}. {req['duration_ms']:.0f}ms (Status: {req['status']})")
        
        if requests_analysis['duplicates']:
            print(f"\n  ⚠️  REQUESTS DUPLICADOS DETECTADOS:")
            for url, dup_info in requests_analysis['duplicates'].items():
                print(f"    URL: {url.replace(BACKEND_URL, '')}")
                print(f"    Count: {dup_info['count']}")
                print(f"    Diferença média: {dup_info['avg_time_diff_ms']:.2f}ms")
                print(f"    Provável StrictMode: {'SIM' if dup_info['likely_strictmode'] else 'NÃO'}")
        
        return result
    
    def run_all_tests(self):
        """Executa todos os testes"""
        print("\n" + "="*80)
        print("TESTE DETALHADO FRONTEND: Análise de Requests Duplicados")
        print("="*80)
        print(f"Frontend URL: {FRONTEND_URL}")
        print(f"Backend URL: {BACKEND_URL}")
        print(f"Timestamp: {self.results['timestamp']}")
        
        pages_to_test = [
            ("/prometheus-config", "PrometheusConfig"),
            ("/metadata-fields", "MetadataFields"),
            ("/monitoring-types", "MonitoringTypes"),
        ]
        
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False)  # headless=False para ver o navegador
            context = browser.new_context()
            page = context.new_page()
            
            # Habilitar logging de rede
            page.on("console", lambda msg: print(f"[CONSOLE] {msg.text}"))
            
            for page_path, page_name in pages_to_test:
                try:
                    self.results["pages"][page_name] = self.test_page_detailed(page, page_path, page_name)
                    time.sleep(1)  # Pequeno delay entre páginas
                except Exception as e:
                    print(f"    ❌ Erro ao testar {page_name}: {e}")
                    self.results["pages"][page_name] = {
                        "error": str(e),
                        "status": "ERROR"
                    }
            
            browser.close()
        
        # Calcular totais
        total_servers_requests = sum(
            p.get("requests_analysis", {}).get("servers_requests_count", 0)
            for p in self.results["pages"].values()
            if isinstance(p, dict) and "requests_analysis" in p
        )
        
        total_duplicates = sum(
            len(p.get("requests_analysis", {}).get("duplicates", {}))
            for p in self.results["pages"].values()
            if isinstance(p, dict) and "requests_analysis" in p
        )
        
        self.results["summary"] = {
            "total_pages_tested": len(pages_to_test),
            "total_servers_requests": total_servers_requests,
            "total_duplicate_groups": total_duplicates,
            "expected_after_optimization": 1,  # Com ServersContext, deve ser 1
            "reduction_expected": round((1 - (1 / total_servers_requests)) * 100, 2) if total_servers_requests > 0 else 0
        }
        
        # Salvar resultados
        filename = f"SERVERS_FRONTEND_DETAILED_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        filepath = BASELINE_DIR / filename
        
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)
        
        # Imprimir resumo
        print("\n" + "="*80)
        print("RESUMO FINAL")
        print("="*80)
        print(f"📄 Páginas testadas: {self.results['summary']['total_pages_tested']}")
        print(f"📊 Total requests /servers: {self.results['summary']['total_servers_requests']}")
        print(f"🔄 Grupos de duplicados: {self.results['summary']['total_duplicate_groups']}")
        print(f"🎯 Esperado após otimização: {self.results['summary']['expected_after_optimization']}")
        print(f"📉 Redução esperada: {self.results['summary']['reduction_expected']:.1f}%")
        print(f"\n📁 Resultados salvos em: {filepath}")
        
        return self.results


if __name__ == "__main__":
    tester = DetailedFrontendTester()
    tester.run_all_tests()

