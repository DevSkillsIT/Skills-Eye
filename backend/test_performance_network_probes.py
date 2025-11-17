#!/usr/bin/env python3
"""
Teste de Performance: Network Probes Page
Mede tempo de carregamento, renderização e requisições HTTP
"""

import asyncio
import json
import time
from datetime import datetime
from playwright.async_api import async_playwright
from typing import Dict, List, Any

async def measure_page_performance(url: str, iterations: int = 5) -> Dict[str, Any]:
    """Mede performance da página de Network Probes"""
    
    results = {
        'url': url,
        'iterations': iterations,
        'timestamp': datetime.now().isoformat(),
        'metrics': []
    }
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        
        for i in range(iterations):
            print(f"\n🔄 Iteração {i+1}/{iterations}...")
            
            page = await context.new_page()
            
            # Coletar métricas de performance
            performance_metrics = []
            network_requests = []
            
            # Interceptar requisições
            async def handle_request(request):
                network_requests.append({
                    'url': request.url,
                    'method': request.method,
                    'timestamp': time.time()
                })
            
            async def handle_response(response):
                if response.request.url.startswith('http://localhost:5000'):
                    try:
                        performance_metrics.append({
                            'url': response.url,
                            'status': response.status,
                        })
                    except:
                        pass
            
            page.on('request', handle_request)
            page.on('response', handle_response)
            
            # Medir tempo de navegação
            start_time = time.time()
            
            try:
                # Navegar para a página
                await page.goto(url, wait_until='networkidle', timeout=30000)
                navigation_time = time.time() - start_time
                
                # Aguardar tabela estar visível
                await page.wait_for_selector('table, .ant-table', timeout=10000)
                table_visible_time = time.time() - start_time
                
                # Aguardar dados carregarem (verificar se há linhas na tabela)
                try:
                    await page.wait_for_selector('tbody tr', timeout=10000)
                    data_loaded_time = time.time() - start_time
                except Exception as e:
                    data_loaded_time = None
                    print(f"    ⚠️  Dados não carregaram: {str(e)[:50]}")
                
                # Aguardar filtros estarem visíveis
                try:
                    await page.wait_for_selector('.ant-select, [class*="filter"]', timeout=5000)
                    filters_visible_time = time.time() - start_time
                except Exception as e:
                    filters_visible_time = None
                
                # Medir tempo total até tudo estar pronto
                total_time = time.time() - start_time
                
                # Contar elementos
                table_rows = await page.locator('tbody tr').count()
                api_requests = len([r for r in network_requests if 'localhost:5000' in r['url']])
                
                # Coletar métricas do console (se disponível)
                console_logs = []
                try:
                    nav_timing = await page.evaluate('''() => {
                        const nav = window.performance.getEntriesByType('navigation')[0];
                        return nav ? {
                            domContentLoaded: nav.domContentLoadedEventEnd - nav.domContentLoadedEventStart,
                            load: nav.loadEventEnd - nav.loadEventStart,
                        } : null;
                    }''')
                    if nav_timing:
                        console_logs.append(nav_timing)
                except Exception as e:
                    pass
                
                iteration_result = {
                    'iteration': i + 1,
                    'navigation_time_ms': round(navigation_time * 1000, 2),
                    'table_visible_time_ms': round(table_visible_time * 1000, 2),
                    'data_loaded_time_ms': round(data_loaded_time * 1000, 2) if data_loaded_time else None,
                    'filters_visible_time_ms': round(filters_visible_time * 1000, 2) if filters_visible_time else None,
                    'total_time_ms': round(total_time * 1000, 2),
                    'table_rows': table_rows,
                    'api_requests': api_requests,
                    'network_requests_count': len(network_requests),
                    'performance_metrics': performance_metrics[:10],  # Primeiras 10
                }
                
                results['metrics'].append(iteration_result)
                
                print(f"  ✅ Navegação: {navigation_time*1000:.0f}ms | Tabela: {table_visible_time*1000:.0f}ms | Dados: {data_loaded_time*1000:.0f}ms | Total: {total_time*1000:.0f}ms")
                print(f"  📊 Linhas: {table_rows} | Requisições API: {api_requests}")
                
            except Exception as e:
                print(f"  ❌ Erro na iteração {i+1}: {str(e)}")
                results['metrics'].append({
                    'iteration': i + 1,
                    'error': str(e)
                })
            
            finally:
                await page.close()
                await asyncio.sleep(1)  # Pequeno delay entre iterações
        
        await browser.close()
    
    # Calcular estatísticas
    valid_metrics = [m for m in results['metrics'] if 'error' not in m]
    
    if valid_metrics:
        results['statistics'] = {
            'navigation_time': {
                'mean': round(sum(m['navigation_time_ms'] for m in valid_metrics) / len(valid_metrics), 2),
                'min': round(min(m['navigation_time_ms'] for m in valid_metrics), 2),
                'max': round(max(m['navigation_time_ms'] for m in valid_metrics), 2),
            },
            'table_visible_time': {
                'mean': round(sum(m['table_visible_time_ms'] for m in valid_metrics) / len(valid_metrics), 2),
                'min': round(min(m['table_visible_time_ms'] for m in valid_metrics), 2),
                'max': round(max(m['table_visible_time_ms'] for m in valid_metrics), 2),
            },
            'data_loaded_time': {
                'mean': round(sum(m['data_loaded_time_ms'] for m in valid_metrics if m.get('data_loaded_time_ms')) / len([m for m in valid_metrics if m.get('data_loaded_time_ms')]), 2) if any(m.get('data_loaded_time_ms') for m in valid_metrics) else None,
                'min': round(min(m['data_loaded_time_ms'] for m in valid_metrics if m.get('data_loaded_time_ms')), 2) if any(m.get('data_loaded_time_ms') for m in valid_metrics) else None,
                'max': round(max(m['data_loaded_time_ms'] for m in valid_metrics if m.get('data_loaded_time_ms')), 2) if any(m.get('data_loaded_time_ms') for m in valid_metrics) else None,
            },
            'total_time': {
                'mean': round(sum(m['total_time_ms'] for m in valid_metrics) / len(valid_metrics), 2),
                'min': round(min(m['total_time_ms'] for m in valid_metrics), 2),
                'max': round(max(m['total_time_ms'] for m in valid_metrics), 2),
            },
            'api_requests': {
                'mean': round(sum(m['api_requests'] for m in valid_metrics) / len(valid_metrics), 1),
                'min': min(m['api_requests'] for m in valid_metrics),
                'max': max(m['api_requests'] for m in valid_metrics),
            },
        }
    
    return results

async def main():
    """Executa teste de performance"""
    url = 'http://localhost:8081/monitoring/network-probes'
    
    print("=" * 60)
    print("🚀 TESTE DE PERFORMANCE: Network Probes Page")
    print("=" * 60)
    print(f"URL: {url}")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print()
    
    results = await measure_page_performance(url, iterations=5)
    
    # Salvar resultados
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f'backend/performance_test_network_probes_{timestamp}.json'
    
    with open(filename, 'w') as f:
        json.dump(results, f, indent=2)
    
    print("\n" + "=" * 60)
    print("📊 RESULTADOS")
    print("=" * 60)
    
    if 'statistics' in results:
        stats = results['statistics']
        print(f"\n⏱️  Tempo de Navegação:")
        print(f"   Média: {stats['navigation_time']['mean']}ms")
        print(f"   Min: {stats['navigation_time']['min']}ms | Max: {stats['navigation_time']['max']}ms")
        
        print(f"\n📋 Tabela Visível:")
        print(f"   Média: {stats['table_visible_time']['mean']}ms")
        print(f"   Min: {stats['table_visible_time']['min']}ms | Max: {stats['table_visible_time']['max']}ms")
        
        if stats['data_loaded_time']['mean']:
            print(f"\n📊 Dados Carregados:")
            print(f"   Média: {stats['data_loaded_time']['mean']}ms")
            print(f"   Min: {stats['data_loaded_time']['min']}ms | Max: {stats['data_loaded_time']['max']}ms")
        
        print(f"\n⏱️  Tempo Total:")
        print(f"   Média: {stats['total_time']['mean']}ms")
        print(f"   Min: {stats['total_time']['min']}ms | Max: {stats['total_time']['max']}ms")
        
        print(f"\n🌐 Requisições API:")
        print(f"   Média: {stats['api_requests']['mean']}")
        print(f"   Min: {stats['api_requests']['min']} | Max: {stats['api_requests']['max']}")
    
    print(f"\n💾 Resultados salvos em: {filename}")
    print("=" * 60)

if __name__ == '__main__':
    asyncio.run(main())

