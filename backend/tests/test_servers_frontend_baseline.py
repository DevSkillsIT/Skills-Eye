#!/usr/bin/env python3
"""
TESTE DE BASELINE FRONTEND: ServersContext - ANTES DAS MELHORIAS

Este script usa Playwright para testar as páginas do frontend:
1. PrometheusConfig
2. MetadataFields
3. MonitoringTypes

Mede:
- Tempo de carregamento
- Requests de API (especialmente /metadata-fields/servers)
- Funcionalidades (seleção de servidor)

Resultados são salvos em data/baselines/SERVERS_FRONTEND_BASELINE_ANTES_<timestamp>.json

AUTOR: Plano de Teste ServersContext
DATA: 2025-11-16
"""

from playwright.sync_api import sync_playwright
import time
import json
import statistics
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List

FRONTEND_URL = "http://localhost:8081"
BACKEND_URL = "http://localhost:5000/api/v1"

# Diretório para salvar resultados
BASELINE_DIR = Path(__file__).parent.parent / "data" / "baselines"
BASELINE_DIR.mkdir(parents=True, exist_ok=True)


class FrontendServersBaselineTester:
    """Classe para executar testes de baseline do frontend"""
    
    def __init__(self):
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "test_type": "servers_frontend_baseline_antes",
            "pages": {}
        }
    
    def measure_page_performance(self, page, page_path: str, page_name: str) -> Dict[str, Any]:
        """Mede performance de uma página específica"""
        network_requests = []
        servers_requests = []
        
        def handle_request(request):
            network_requests.append({
                'url': request.url,
                'method': request.method,
                'start_time': time.time()
            })
        
        def handle_response(response):
            for req in network_requests:
                if req['url'] == response.url and 'end_time' not in req:
                    req['end_time'] = time.time()
                    req['status'] = response.status
                    req['duration'] = (req['end_time'] - req['start_time']) * 1000
                    
                    # Contar requests para /metadata-fields/servers
                    if '/metadata-fields/servers' in req['url']:
                        servers_requests.append(req)
                    break
        
        page.on("request", handle_request)
        page.on("response", handle_response)
        
        # Navegação
        navigation_start = time.time()
        page.goto(f"{FRONTEND_URL}{page_path}")
        navigation_time = (time.time() - navigation_start) * 1000
        
        # Aguardar página carregar
        try:
            page.wait_for_selector("body", timeout=30000)
            # Aguardar seletor de servidor aparecer (se existir)
            try:
                page.wait_for_selector(".ant-select, [class*='server'], [class*='Server']", timeout=5000)
            except:
                pass  # Pode não ter seletor visível
        except Exception as e:
            print(f"    ⚠️  Timeout ao aguardar página: {e}")
        
        # Capturar métricas do browser
        performance_metrics = page.evaluate("""() => {
            const perfData = window.performance.timing;
            const paintEntries = performance.getEntriesByType('paint');
            
            return {
                domContentLoaded: perfData.domContentLoadedEventEnd - perfData.navigationStart,
                loadComplete: perfData.loadEventEnd - perfData.navigationStart,
                firstPaint: paintEntries.find(e => e.name === 'first-paint')?.startTime || 0,
                firstContentfulPaint: paintEntries.find(e => e.name === 'first-contentful-paint')?.startTime || 0
            };
        }""")
        
        return {
            "navigation_time_ms": round(navigation_time, 2),
            "dom_content_loaded_ms": round(performance_metrics['domContentLoaded'], 2),
            "load_complete_ms": round(performance_metrics['loadComplete'], 2),
            "first_contentful_paint_ms": round(performance_metrics['firstContentfulPaint'], 2),
            "total_requests": len(network_requests),
            "api_requests": len([r for r in network_requests if BACKEND_URL in r['url']]),
            "servers_requests_count": len(servers_requests),
            "servers_requests_details": [
                {
                    "duration_ms": round(r.get('duration', 0), 2),
                    "status": r.get('status', 0)
                }
                for r in servers_requests
            ],
            "all_requests": [
                {
                    "url": r['url'].split(BACKEND_URL)[1] if BACKEND_URL in r['url'] else r['url'],
                    "duration_ms": round(r.get('duration', 0), 2),
                    "status": r.get('status', 0)
                }
                for r in network_requests if BACKEND_URL in r['url']
            ]
        }
    
    def test_page(self, page, page_path: str, page_name: str, iterations: int = 3) -> Dict[str, Any]:
        """Testa uma página específica"""
        print(f"\n{'='*80}")
        print(f"TESTE: {page_name}")
        print(f"{'='*80}")
        print(f"URL: {FRONTEND_URL}{page_path}")
        print(f"Iterações: {iterations}\n")
        
        metrics_list = []
        
        for i in range(iterations):
            print(f"  Iteração {i+1}/{iterations}...")
            metrics = self.measure_page_performance(page, page_path, page_name)
            metrics_list.append(metrics)
            
            print(f"    ✅ Navegação: {metrics['navigation_time_ms']:.0f}ms")
            print(f"    ✅ Requests de /servers: {metrics['servers_requests_count']}")
            if metrics['servers_requests_details']:
                for detail in metrics['servers_requests_details']:
                    print(f"      → {detail['duration_ms']:.0f}ms (Status: {detail['status']})")
            
            time.sleep(1)  # Pequeno delay entre iterações
        
        # Calcular estatísticas
        nav_times = [m['navigation_time_ms'] for m in metrics_list]
        servers_req_counts = [m['servers_requests_count'] for m in metrics_list]
        
        return {
            "page_name": page_name,
            "page_path": page_path,
            "iterations": iterations,
            "metrics": metrics_list,
            "statistics": {
                "navigation": {
                    "mean_ms": round(statistics.mean(nav_times), 2),
                    "median_ms": round(statistics.median(nav_times), 2),
                    "min_ms": round(min(nav_times), 2),
                    "max_ms": round(max(nav_times), 2)
                },
                "servers_requests": {
                    "mean_count": round(statistics.mean(servers_req_counts), 2),
                    "total_requests": sum(servers_req_counts)
                }
            }
        }
    
    def run_all_tests(self):
        """Executa todos os testes"""
        print("\n" + "="*80)
        print("TESTE DE BASELINE FRONTEND: ServersContext - ANTES DAS MELHORIAS")
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
            browser = p.chromium.launch()
            page = browser.new_page()
            
            for page_path, page_name in pages_to_test:
                try:
                    self.results["pages"][page_name] = self.test_page(page, page_path, page_name, iterations=3)
                except Exception as e:
                    print(f"    ❌ Erro ao testar {page_name}: {e}")
                    self.results["pages"][page_name] = {
                        "error": str(e),
                        "status": "ERROR"
                    }
            
            browser.close()
        
        # Calcular totais
        total_servers_requests = sum(
            p.get("statistics", {}).get("servers_requests", {}).get("total_requests", 0)
            for p in self.results["pages"].values()
            if isinstance(p, dict) and "statistics" in p
        )
        
        self.results["summary"] = {
            "total_pages_tested": len(pages_to_test),
            "total_servers_requests": total_servers_requests,
            "expected_after_optimization": 1,  # Com ServersContext, deve ser 1
            "reduction_expected": round((1 - (1 / total_servers_requests)) * 100, 2) if total_servers_requests > 0 else 0
        }
        
        # Salvar resultados
        filename = f"SERVERS_FRONTEND_BASELINE_ANTES_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        filepath = BASELINE_DIR / filename
        
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)
        
        # Imprimir resumo
        print("\n" + "="*80)
        print("RESUMO FINAL")
        print("="*80)
        print(f"📄 Páginas testadas: {self.results['summary']['total_pages_tested']}")
        print(f"📊 Total requests /servers: {self.results['summary']['total_servers_requests']}")
        print(f"🎯 Esperado após otimização: {self.results['summary']['expected_after_optimization']}")
        print(f"📉 Redução esperada: {self.results['summary']['reduction_expected']:.1f}%")
        print(f"\n📁 Resultados salvos em: {filepath}")
        
        return self.results


if __name__ == "__main__":
    tester = FrontendServersBaselineTester()
    tester.run_all_tests()

