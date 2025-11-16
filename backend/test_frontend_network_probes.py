#!/usr/bin/env python3
"""
TESTE DE PERFORMANCE FRONTEND - Network Probes Page

OBJETIVO:
- Medir tempo de carregamento da página /monitoring/network-probes
- Identificar delays e gargalos
- Validar se otimizações backend melhoraram performance

AUTOR: Análise de Performance - 16/11/2025
"""

from playwright.sync_api import sync_playwright
import time
import json
import statistics
from datetime import datetime
from pathlib import Path

FRONTEND_URL = "http://localhost:8081"
PAGE_PATH = "/monitoring/network-probes"

# Diretório para resultados
RESULTS_DIR = Path(__file__).parent.parent / "data" / "baselines"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)


def test_network_probes_page_performance(iterations: int = 5):
    """
    Testa performance da página Network Probes
    
    Mede:
    - Tempo de navegação
    - Tempo até primeiro conteúdo renderizado
    - Tempo até tabela carregada
    - Requests de rede (quantidade, duração)
    - Tempo de processamento frontend
    """
    print("\n" + "="*80)
    print("TESTE DE PERFORMANCE: Network Probes Page")
    print("="*80)
    print(f"URL: {FRONTEND_URL}{PAGE_PATH}")
    print(f"Iterações: {iterations}")
    print()
    
    all_results = []
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        
        for i in range(iterations):
            print(f"\n{'='*80}")
            print(f"ITERAÇÃO {i+1}/{iterations}")
            print(f"{'='*80}")
            
            page = context.new_page()
            
            # Capturar requests de rede
            network_requests = []
            network_responses = []
            
            def handle_request(request):
                network_requests.append({
                    'url': request.url,
                    'method': request.method,
                    'resource_type': request.resource_type,
                    'start_time': time.time()
                })
            
            def handle_response(response):
                for req in network_requests:
                    if req['url'] == response.url and 'end_time' not in req:
                        req['end_time'] = time.time()
                        req['duration_ms'] = (req['end_time'] - req['start_time']) * 1000
                        req['status'] = response.status
                        req['size'] = response.headers.get('content-length', '0')
                        network_responses.append(req)
                        break
            
            page.on("request", handle_request)
            page.on("response", handle_response)
            
            # Medir tempos
            navigation_start = time.time()
            
            # Navegar para a página
            page.goto(f"{FRONTEND_URL}{PAGE_PATH}", wait_until="networkidle")
            
            navigation_end = time.time()
            navigation_time = (navigation_end - navigation_start) * 1000
            
            # Aguardar tabela carregar (esperar por elemento específico)
            try:
                # Esperar por tabela ou loading desaparecer
                page.wait_for_selector("table, .ant-table, [data-testid='monitoring-table']", timeout=10000)
                table_ready_time = time.time()
                table_load_time = (table_ready_time - navigation_start) * 1000
            except:
                table_load_time = None
                print("  ⚠️  Tabela não encontrada ou timeout")
            
            # Aguardar um pouco mais para garantir que tudo carregou
            time.sleep(1)
            
            # Capturar métricas do navegador
            metrics = page.evaluate("""
                () => {
                    const perf = window.performance;
                    const nav = perf.getEntriesByType('navigation')[0];
                    const paint = perf.getEntriesByType('paint');
                    
                    return {
                        domContentLoaded: nav.domContentLoadedEventEnd - nav.domContentLoadedEventStart,
                        loadComplete: nav.loadEventEnd - nav.loadEventStart,
                        firstPaint: paint.find(p => p.name === 'first-paint')?.startTime || 0,
                        firstContentfulPaint: paint.find(p => p.name === 'first-contentful-paint')?.startTime || 0,
                        totalTime: nav.loadEventEnd - nav.fetchStart
                    };
                }
            """)
            
            # Filtrar requests relevantes
            api_requests = [r for r in network_responses if '/api/v1/' in r['url']]
            monitoring_requests = [r for r in api_requests if 'monitoring' in r['url']]
            
            result = {
                'iteration': i + 1,
                'navigation_time_ms': navigation_time,
                'table_load_time_ms': table_load_time,
                'dom_content_loaded_ms': metrics.get('domContentLoaded', 0),
                'load_complete_ms': metrics.get('loadComplete', 0),
                'first_paint_ms': metrics.get('firstPaint', 0),
                'first_contentful_paint_ms': metrics.get('firstContentfulPaint', 0),
                'total_time_ms': metrics.get('totalTime', 0),
                'total_requests': len(network_requests),
                'api_requests': len(api_requests),
                'monitoring_requests': len(monitoring_requests),
                'network_requests': network_responses
            }
            
            all_results.append(result)
            
            # Print resumo da iteração
            print(f"  ✅ Navegação: {navigation_time:.0f}ms")
            if table_load_time:
                print(f"  ✅ Tabela carregada: {table_load_time:.0f}ms")
            print(f"  ✅ First Paint: {metrics.get('firstPaint', 0):.0f}ms")
            print(f"  ✅ First Contentful Paint: {metrics.get('firstContentfulPaint', 0):.0f}ms")
            print(f"  ✅ Total Requests: {len(network_requests)}")
            print(f"  ✅ API Requests: {len(api_requests)}")
            print(f"  ✅ Monitoring Requests: {len(monitoring_requests)}")
            
            # Detalhar requests de monitoring
            if monitoring_requests:
                print(f"\n  📊 Requests de Monitoring:")
                for req in monitoring_requests:
                    print(f"    → {req['url'].split('/')[-1]}: {req['duration_ms']:.0f}ms (Status: {req['status']})")
            
            page.close()
            
            # Aguardar entre iterações
            if i < iterations - 1:
                time.sleep(2)
        
        browser.close()
    
    # Calcular estatísticas
    navigation_times = [r['navigation_time_ms'] for r in all_results]
    table_times = [r['table_load_time_ms'] for r in all_results if r['table_load_time_ms']]
    fcp_times = [r['first_contentful_paint_ms'] for r in all_results if r['first_contentful_paint_ms']]
    
    stats = {
        'timestamp': datetime.now().isoformat(),
        'page': 'network-probes',
        'url': f"{FRONTEND_URL}{PAGE_PATH}",
        'iterations': iterations,
        'navigation': {
            'mean_ms': statistics.mean(navigation_times) if navigation_times else 0,
            'median_ms': statistics.median(navigation_times) if navigation_times else 0,
            'min_ms': min(navigation_times) if navigation_times else 0,
            'max_ms': max(navigation_times) if navigation_times else 0,
            'p95_ms': statistics.quantiles(navigation_times, n=20)[18] if len(navigation_times) > 1 else navigation_times[0] if navigation_times else 0
        },
        'table_load': {
            'mean_ms': statistics.mean(table_times) if table_times else 0,
            'median_ms': statistics.median(table_times) if table_times else 0,
            'min_ms': min(table_times) if table_times else 0,
            'max_ms': max(table_times) if table_times else 0
        },
        'first_contentful_paint': {
            'mean_ms': statistics.mean(fcp_times) if fcp_times else 0,
            'median_ms': statistics.median(fcp_times) if fcp_times else 0
        },
        'requests': {
            'mean_total': statistics.mean([r['total_requests'] for r in all_results]),
            'mean_api': statistics.mean([r['api_requests'] for r in all_results]),
            'mean_monitoring': statistics.mean([r['monitoring_requests'] for r in all_results])
        },
        'detailed_results': all_results
    }
    
    # Salvar resultados
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = RESULTS_DIR / f"FRONTEND_NETWORK_PROBES_{timestamp}.json"
    
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2, ensure_ascii=False)
    
    # Print resumo final
    print("\n" + "="*80)
    print("RESUMO FINAL")
    print("="*80)
    print(f"\n📊 NAVEGAÇÃO:")
    print(f"   Média: {stats['navigation']['mean_ms']:.0f}ms")
    print(f"   Mediana: {stats['navigation']['median_ms']:.0f}ms")
    print(f"   P95: {stats['navigation']['p95_ms']:.0f}ms")
    print(f"   Min: {stats['navigation']['min_ms']:.0f}ms | Max: {stats['navigation']['max_ms']:.0f}ms")
    
    if table_times:
        print(f"\n📊 TABELA CARREGADA:")
        print(f"   Média: {stats['table_load']['mean_ms']:.0f}ms")
        print(f"   Mediana: {stats['table_load']['median_ms']:.0f}ms")
        print(f"   Min: {stats['table_load']['min_ms']:.0f}ms | Max: {stats['table_load']['max_ms']:.0f}ms")
    
    if fcp_times:
        print(f"\n📊 FIRST CONTENTFUL PAINT:")
        print(f"   Média: {stats['first_contentful_paint']['mean_ms']:.0f}ms")
        print(f"   Mediana: {stats['first_contentful_paint']['median_ms']:.0f}ms")
    
    print(f"\n📊 REQUESTS:")
    print(f"   Total: {stats['requests']['mean_total']:.1f} (média)")
    print(f"   API: {stats['requests']['mean_api']:.1f} (média)")
    print(f"   Monitoring: {stats['requests']['mean_monitoring']:.1f} (média)")
    
    # Identificar delays
    print(f"\n🔍 ANÁLISE DE DELAYS:")
    if stats['navigation']['mean_ms'] > 2000:
        print(f"   ⚠️  Navegação lenta: {stats['navigation']['mean_ms']:.0f}ms (esperado: <2000ms)")
    else:
        print(f"   ✅ Navegação OK: {stats['navigation']['mean_ms']:.0f}ms")
    
    if table_times and stats['table_load']['mean_ms'] > 3000:
        print(f"   ⚠️  Tabela lenta: {stats['table_load']['mean_ms']:.0f}ms (esperado: <3000ms)")
    elif table_times:
        print(f"   ✅ Tabela OK: {stats['table_load']['mean_ms']:.0f}ms")
    
    if stats['requests']['mean_monitoring'] > 3:
        print(f"   ⚠️  Muitos requests de monitoring: {stats['requests']['mean_monitoring']:.1f} (esperado: 1-2)")
    else:
        print(f"   ✅ Requests OK: {stats['requests']['mean_monitoring']:.1f}")
    
    print(f"\n📁 Resultados salvos em: {filename}")
    print("="*80)
    
    return stats


if __name__ == "__main__":
    try:
        stats = test_network_probes_page_performance(iterations=5)
        
        # Retornar código de saída baseado em performance
        if stats['navigation']['mean_ms'] > 3000 or (stats.get('table_load', {}).get('mean_ms', 0) > 5000):
            print("\n⚠️  ATENÇÃO: Performance abaixo do esperado!")
            exit(1)
        else:
            print("\n✅ Performance dentro do esperado!")
            exit(0)
    except Exception as e:
        print(f"\n❌ ERRO: {e}")
        import traceback
        traceback.print_exc()
        exit(1)

