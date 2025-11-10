"""
TESTE COMPLETO DE PERFORMANCE - PLAYWRIGHT
Mede TODOS os aspectos: backend, frontend, rendering, network
Sem suposições - apenas DADOS CONCRETOS
"""
from playwright.sync_api import sync_playwright
import time
import json
import statistics

FRONTEND_URL = "http://localhost:8081"
BACKEND_URL = "http://localhost:5000/api/v1"

def measure_page_performance(page, page_name, page_path):
    """
    Mede TODOS os aspectos de performance de uma página

    Returns:
        dict com todas as métricas
    """
    print(f"\n{'='*80}")
    print(f"TESTANDO: {page_name}")
    print(f"{'='*80}\n")

    results = {
        'page': page_name,
        'path': page_path
    }

    # ========================================================================
    # FASE 1: MEDIÇÃO DE REDE (Network Requests)
    # ========================================================================
    print("FASE 1: Capturando requests de rede...")

    network_requests = []

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
                break

    page.on("request", handle_request)
    page.on("response", handle_response)

    # ========================================================================
    # FASE 2: NAVEGAÇÃO E TIMING
    # ========================================================================
    print("FASE 2: Navegando e medindo tempos...")

    navigation_start = time.time()
    page.goto(f"{FRONTEND_URL}{page_path}")
    navigation_end = time.time()
    navigation_time = (navigation_end - navigation_start) * 1000

    print(f"  Navegacao completa: {navigation_time:.0f}ms")

    # ========================================================================
    # FASE 3: AGUARDAR TABELA APARECER (DOM Ready)
    # ========================================================================
    print("FASE 3: Aguardando tabela aparecer no DOM...")

    dom_ready_start = time.time()
    try:
        page.wait_for_selector(".ant-pro-table", timeout=30000)
        dom_ready_end = time.time()
        dom_ready_time = (dom_ready_end - dom_ready_start) * 1000
        print(f"  DOM ready: {dom_ready_time:.0f}ms")
    except Exception as e:
        print(f"  ERRO: Tabela nao apareceu! {e}")
        dom_ready_time = None

    # ========================================================================
    # FASE 4: AGUARDAR DADOS VISIVEIS (First Paint)
    # ========================================================================
    print("FASE 4: Aguardando dados visiveis...")

    first_paint_start = time.time()
    try:
        page.wait_for_selector("tbody tr.ant-table-row td", timeout=30000)
        first_paint_end = time.time()
        first_paint_time = (first_paint_end - first_paint_start) * 1000
        print(f"  First paint (dados visiveis): {first_paint_time:.0f}ms")
    except Exception as e:
        print(f"  ERRO: Dados nao apareceram! {e}")
        first_paint_time = None

    # ========================================================================
    # FASE 5: AGUARDAR LOADING DESAPARECER
    # ========================================================================
    print("FASE 5: Aguardando loading desaparecer...")

    loading_end_start = time.time()
    try:
        # Aguardar qualquer spinner ou loading desaparecer
        page.wait_for_selector(".ant-spin-spinning", state="hidden", timeout=30000)
        loading_end_time = (time.time() - loading_end_start) * 1000
        print(f"  Loading finalizado: {loading_end_time:.0f}ms")
    except Exception as e:
        # Pode não ter loading
        loading_end_time = 0
        print(f"  Sem loading detectado")

    # ========================================================================
    # FASE 6: CAPTURAR MÉTRICAS DA PÁGINA
    # ========================================================================
    print("FASE 6: Capturando metricas da pagina...")

    # Contar linhas
    rows = page.query_selector_all("tbody tr.ant-table-row")
    row_count = len(rows)
    print(f"  Linhas renderizadas: {row_count}")

    # Contar colunas
    headers = page.query_selector_all("thead th")
    column_count = len(headers)
    print(f"  Colunas renderizadas: {column_count}")

    # Total de células
    cells = row_count * column_count
    print(f"  Total de celulas: {cells}")

    # ========================================================================
    # FASE 7: CAPTURAR PERFORMANCE METRICS DO BROWSER
    # ========================================================================
    print("FASE 7: Capturando metricas do browser...")

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

    print(f"  DOM Content Loaded: {performance_metrics['domContentLoaded']:.0f}ms")
    print(f"  Load Complete: {performance_metrics['loadComplete']:.0f}ms")
    print(f"  First Paint: {performance_metrics['firstPaint']:.0f}ms")
    print(f"  First Contentful Paint: {performance_metrics['firstContentfulPaint']:.0f}ms")

    # ========================================================================
    # FASE 8: ANALISAR REQUESTS DE REDE
    # ========================================================================
    print("\nFASE 8: Analisando requests de rede...")

    # Filtrar requests para API
    api_requests = [r for r in network_requests if '/api/v1/' in r['url'] and 'duration' in r]

    if api_requests:
        for req in api_requests:
            print(f"  {req['method']} {req['url'].split('/api/v1/')[-1]}")
            print(f"    Status: {req['status']}")
            print(f"    Duracao: {req['duration']:.0f}ms")

    # ========================================================================
    # FASE 9: CALCULAR TEMPO TOTAL
    # ========================================================================
    total_time = navigation_time
    if dom_ready_time:
        total_time += dom_ready_time
    if first_paint_time:
        total_time += first_paint_time
    if loading_end_time:
        total_time += loading_end_time

    print(f"\n{'='*80}")
    print(f"TEMPO TOTAL: {total_time:.0f}ms")
    print(f"{'='*80}\n")

    # ========================================================================
    # CAPTURAR SCREENSHOT
    # ========================================================================
    screenshot_path = f"screenshot_{page_name.lower().replace(' ', '_')}.png"
    page.screenshot(path=screenshot_path)
    print(f"Screenshot salvo: {screenshot_path}")

    # Retornar resultados
    results.update({
        'navigation_time': navigation_time,
        'dom_ready_time': dom_ready_time,
        'first_paint_time': first_paint_time,
        'loading_end_time': loading_end_time,
        'total_time': total_time,
        'rows': row_count,
        'columns': column_count,
        'cells': cells,
        'browser_metrics': performance_metrics,
        'api_requests': api_requests
    })

    return results


def compare_results(blackbox_results, services_results):
    """
    Compara resultados de ambas as páginas e identifica diferenças
    """
    print(f"\n{'='*80}")
    print("COMPARAÇÃO DETALHADA - BLACKBOX vs SERVICES")
    print(f"{'='*80}\n")

    print("=" * 80)
    print("1. NAVEGAÇÃO INICIAL")
    print("=" * 80)
    print(f"BlackboxTargets: {blackbox_results['navigation_time']:.0f}ms")
    print(f"Services:        {services_results['navigation_time']:.0f}ms")
    diff = services_results['navigation_time'] - blackbox_results['navigation_time']
    print(f"DIFERENCA:       {diff:+.0f}ms ({diff/blackbox_results['navigation_time']*100:+.1f}%)")

    print("\n" + "=" * 80)
    print("2. DOM READY (Tabela aparecer no DOM)")
    print("=" * 80)
    bb_dom = blackbox_results['dom_ready_time'] or 0
    sv_dom = services_results['dom_ready_time'] or 0
    print(f"BlackboxTargets: {bb_dom:.0f}ms")
    print(f"Services:        {sv_dom:.0f}ms")
    if bb_dom > 0:
        diff = sv_dom - bb_dom
        print(f"DIFERENCA:       {diff:+.0f}ms ({diff/bb_dom*100:+.1f}%)")
    else:
        print(f"DIFERENCA:       N/A (BlackboxTargets nao renderizou)")

    print("\n" + "=" * 80)
    print("3. FIRST PAINT (Dados visiveis)")
    print("=" * 80)
    bb_paint = blackbox_results['first_paint_time'] or 0
    sv_paint = services_results['first_paint_time'] or 0
    print(f"BlackboxTargets: {bb_paint:.0f}ms")
    print(f"Services:        {sv_paint:.0f}ms")
    if bb_paint > 0:
        diff = sv_paint - bb_paint
        print(f"DIFERENCA:       {diff:+.0f}ms ({diff/bb_paint*100:+.1f}%)")
    else:
        print(f"DIFERENCA:       N/A (BlackboxTargets nao renderizou)")
        print(f">>> Services levou {sv_paint:.0f}ms para renderizar dados")

    print("\n" + "=" * 80)
    print("4. TEMPO TOTAL (Navegacao ate dados visiveis)")
    print("=" * 80)
    print(f"BlackboxTargets: {blackbox_results['total_time']:.0f}ms")
    print(f"Services:        {services_results['total_time']:.0f}ms")
    diff = services_results['total_time'] - blackbox_results['total_time']
    print(f"DIFERENCA:       {diff:+.0f}ms ({diff/blackbox_results['total_time']*100:+.1f}%)")

    print("\n" + "=" * 80)
    print("5. TAMANHO DA TABELA")
    print("=" * 80)
    print(f"BlackboxTargets: {blackbox_results['rows']} linhas × {blackbox_results['columns']} colunas = {blackbox_results['cells']} celulas")
    print(f"Services:        {services_results['rows']} linhas × {services_results['columns']} colunas = {services_results['cells']} celulas")

    print("\n" + "=" * 80)
    print("6. REQUESTS DE API")
    print("=" * 80)
    print(f"BlackboxTargets: {len(blackbox_results['api_requests'])} requests")
    for req in blackbox_results['api_requests']:
        print(f"  - {req['url'].split('/api/v1/')[-1]}: {req['duration']:.0f}ms")

    print(f"\nServices:        {len(services_results['api_requests'])} requests")
    for req in services_results['api_requests']:
        print(f"  - {req['url'].split('/api/v1/')[-1]}: {req['duration']:.0f}ms")

    print("\n" + "=" * 80)
    print("7. METRICAS DO BROWSER")
    print("=" * 80)
    print("BlackboxTargets:")
    print(f"  DOM Content Loaded: {blackbox_results['browser_metrics']['domContentLoaded']:.0f}ms")
    print(f"  Load Complete:      {blackbox_results['browser_metrics']['loadComplete']:.0f}ms")
    print(f"  First Paint:        {blackbox_results['browser_metrics']['firstPaint']:.0f}ms")
    print(f"  First Contentful:   {blackbox_results['browser_metrics']['firstContentfulPaint']:.0f}ms")

    print("\nServices:")
    print(f"  DOM Content Loaded: {services_results['browser_metrics']['domContentLoaded']:.0f}ms")
    print(f"  Load Complete:      {services_results['browser_metrics']['loadComplete']:.0f}ms")
    print(f"  First Paint:        {services_results['browser_metrics']['firstPaint']:.0f}ms")
    print(f"  First Contentful:   {services_results['browser_metrics']['firstContentfulPaint']:.0f}ms")

    # ========================================================================
    # IDENTIFICAR GARGALO
    # ========================================================================
    print("\n" + "=" * 80)
    print("ANALISE DO GARGALO")
    print("=" * 80)

    total_diff = services_results['total_time'] - blackbox_results['total_time']

    if total_diff < 500:
        print("[OK] Performance SIMILAR (diferenca < 500ms)")
        print("Nao ha gargalo significativo.")
    else:
        print(f"[ALERTA] Services {total_diff:.0f}ms MAIS LENTO!")
        print("\nIdentificando onde esta o problema:\n")

        nav_diff = services_results['navigation_time'] - blackbox_results['navigation_time']
        dom_diff = (services_results['dom_ready_time'] or 0) - (blackbox_results['dom_ready_time'] or 0)
        paint_diff = (services_results['first_paint_time'] or 0) - (blackbox_results['first_paint_time'] or 0)

        print(f"1. Navegacao:    {nav_diff:+.0f}ms ({nav_diff/total_diff*100:.1f}% da diferenca total)")
        print(f"2. DOM Ready:    {dom_diff:+.0f}ms ({dom_diff/total_diff*100:.1f}% da diferenca total)")
        print(f"3. First Paint:  {paint_diff:+.0f}ms ({paint_diff/total_diff*100:.1f}% da diferenca total)")

        # Identificar maior gargalo
        diffs = [
            ('Navegacao (HTTP/Routing)', nav_diff),
            ('DOM Ready (React mounting)', dom_diff),
            ('First Paint (Rendering)', paint_diff)
        ]
        diffs.sort(key=lambda x: x[1], reverse=True)

        print(f"\n>>> GARGALO IDENTIFICADO: {diffs[0][0]}")
        print(f">>> Responsavel por {diffs[0][1]:.0f}ms ({diffs[0][1]/total_diff*100:.1f}%) da diferenca")

        if 'DOM Ready' in diffs[0][0]:
            print("\n>>> CAUSA PROVAVEL: React component mounting/initialization")
            print(">>> SOLUCOES: Otimizar useEffect, memoizacao, lazy loading")
        elif 'First Paint' in diffs[0][0]:
            print("\n>>> CAUSA PROVAVEL: Rendering de componentes (ProTable, colunas)")
            print(">>> SOLUCOES: Virtualizacao, React.memo, reducao de re-renders")
        elif 'Navegacao' in diffs[0][0]:
            print("\n>>> CAUSA PROVAVEL: Requests HTTP ou routing")
            print(">>> SOLUCOES: Cache, reducao de requests, otimizacao de backend")

    print("\n" + "=" * 80)
    print("FIM DA ANALISE")
    print("=" * 80)


def main():
    """
    Executa teste completo de performance
    """
    print("=" * 80)
    print("TESTE COMPLETO DE PERFORMANCE - PLAYWRIGHT")
    print("=" * 80)
    print("Medindo TODOS os aspectos: backend, frontend, rendering, network")
    print()

    with sync_playwright() as p:
        # Iniciar browser
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={'width': 1920, 'height': 1080})
        page = context.new_page()

        # Teste 1: BlackboxTargets
        blackbox_results = measure_page_performance(
            page,
            "BlackboxTargets",
            "/blackbox-targets"
        )

        # Aguardar entre testes
        time.sleep(2)

        # Teste 2: Services
        services_results = measure_page_performance(
            page,
            "Services",
            "/services"
        )

        # Comparar resultados
        compare_results(blackbox_results, services_results)

        # Fechar browser
        browser.close()

    print("\n[CONCLUIDO] Teste completo finalizado!")
    print("Screenshots salvos: screenshot_blackboxtargets.png, screenshot_services.png")


if __name__ == "__main__":
    main()
