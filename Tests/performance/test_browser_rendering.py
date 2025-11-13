"""
Teste automatizado de performance de RENDERING no browser
Mede tempo total desde navegacao ate tabela completamente renderizada
"""
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options

FRONTEND_URL = "http://localhost:8081"

def test_page_rendering(page_name, page_path, wait_selector):
    """
    Testa tempo de rendering completo de uma pagina

    Args:
        page_name: Nome da pagina (para logs)
        page_path: Caminho da rota (ex: /blackbox-targets)
        wait_selector: Seletor CSS para aguardar elemento estar visivel

    Returns:
        dict com tempos medidos
    """
    # Configurar Chrome headless (sem interface grafica)
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--window-size=1920,1080')

    driver = webdriver.Chrome(options=options)

    try:
        print(f"\nTestando {page_name}...")
        print("-" * 80)

        # MEDICAO 1: Tempo ate navegacao completa
        start_navigation = time.time()
        driver.get(f"{FRONTEND_URL}{page_path}")
        navigation_time = (time.time() - start_navigation) * 1000

        # MEDICAO 2: Tempo ate primeira tabela aparecer (DOM ready)
        start_dom = time.time()
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.CLASS_NAME, "ant-pro-table"))
        )
        dom_ready_time = (time.time() - start_dom) * 1000

        # MEDICAO 3: Tempo ate tabela COMPLETAMENTE renderizada (dados visiveis)
        start_render = time.time()
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, wait_selector))
        )
        render_complete_time = (time.time() - start_render) * 1000

        # MEDICAO 4: Tempo total (desde navegacao ate render completo)
        total_time = navigation_time + dom_ready_time + render_complete_time

        # Contar linhas renderizadas
        rows = driver.find_elements(By.CSS_SELECTOR, "tbody tr.ant-table-row")
        row_count = len(rows)

        # Contar colunas (headers)
        headers = driver.find_elements(By.CSS_SELECTOR, "thead th")
        column_count = len(headers)

        results = {
            'page': page_name,
            'navigation_time': navigation_time,
            'dom_ready_time': dom_ready_time,
            'render_complete_time': render_complete_time,
            'total_time': total_time,
            'rows': row_count,
            'columns': column_count,
            'cells': row_count * column_count
        }

        print(f"Navegacao: {navigation_time:.0f}ms")
        print(f"DOM Ready: {dom_ready_time:.0f}ms")
        print(f"Render Completo: {render_complete_time:.0f}ms")
        print(f"TOTAL: {total_time:.0f}ms")
        print(f"Linhas: {row_count}")
        print(f"Colunas: {column_count}")
        print(f"Celulas: {row_count * column_count}")

        return results

    finally:
        driver.quit()


def compare_pages():
    """
    Compara performance de BlackboxTargets vs Services
    """
    print("=" * 80)
    print("TESTE DE PERFORMANCE DE RENDERING NO BROWSER")
    print("=" * 80)
    print("Medindo tempo REAL desde navegacao ate tabela completamente renderizada")
    print()

    # Teste BlackboxTargets (3 vezes)
    print("\n" + "=" * 80)
    print("TESTE 1: BlackboxTargets")
    print("=" * 80)
    blackbox_results = []
    for i in range(3):
        print(f"\nRodada {i+1}/3:")
        result = test_page_rendering(
            "BlackboxTargets",
            "/blackbox-targets",
            "tbody tr.ant-table-row td"  # Aguarda primeira celula de dados
        )
        blackbox_results.append(result)
        time.sleep(2)  # Pausa entre testes

    # Teste Services (3 vezes) - SEM ResizableTitle
    print("\n" + "=" * 80)
    print("TESTE 2: Services (SEM ResizableTitle)")
    print("=" * 80)
    services_results = []
    for i in range(3):
        print(f"\nRodada {i+1}/3:")
        result = test_page_rendering(
            "Services",
            "/services",
            "tbody tr.ant-table-row td"  # Aguarda primeira celula de dados
        )
        services_results.append(result)
        time.sleep(2)  # Pausa entre testes

    # COMPARACAO
    print("\n" + "=" * 80)
    print("COMPARACAO DE RESULTADOS")
    print("=" * 80)

    blackbox_avg = sum(r['total_time'] for r in blackbox_results) / len(blackbox_results)
    services_avg = sum(r['total_time'] for r in services_results) / len(services_results)

    print(f"\nBlackboxTargets:")
    print(f"  Tempo medio total: {blackbox_avg:.0f}ms")
    print(f"  Tempo minimo: {min(r['total_time'] for r in blackbox_results):.0f}ms")
    print(f"  Tempo maximo: {max(r['total_time'] for r in blackbox_results):.0f}ms")
    print(f"  Linhas: {blackbox_results[0]['rows']}")
    print(f"  Colunas: {blackbox_results[0]['columns']}")
    print(f"  Celulas: {blackbox_results[0]['cells']}")

    print(f"\nServices (SEM ResizableTitle):")
    print(f"  Tempo medio total: {services_avg:.0f}ms")
    print(f"  Tempo minimo: {min(r['total_time'] for r in services_results):.0f}ms")
    print(f"  Tempo maximo: {max(r['total_time'] for r in services_results):.0f}ms")
    print(f"  Linhas: {services_results[0]['rows']}")
    print(f"  Colunas: {services_results[0]['columns']}")
    print(f"  Celulas: {services_results[0]['cells']}")

    diff = services_avg - blackbox_avg
    diff_pct = (diff / blackbox_avg) * 100

    print(f"\nDIFERENCA:")
    print(f"  Services e {abs(diff):.0f}ms {'MAIS LENTO' if diff > 0 else 'MAIS RAPIDO'}")
    print(f"  Diferenca percentual: {abs(diff_pct):.1f}%")

    if abs(diff) < 500:
        print("\n[OK] Performance similar! ResizableTitle NAO era o gargalo principal.")
    elif diff > 0:
        print("\n[ALERTA] Services ainda mais lento! Investigar outros fatores:")
        print("  - columnMap/visibleColumns recalculando")
        print("  - handleResize ainda presente nas colunas")
        print("  - Outros callbacks nao memoizados")
    else:
        print("\n[SUCESSO] Services MAIS RAPIDO! Otimizacao funcionou.")

    print("\n" + "=" * 80)
    print("FIM DO TESTE")
    print("=" * 80)


if __name__ == "__main__":
    try:
        compare_pages()
    except Exception as e:
        print(f"\nERRO ao executar teste: {e}")
        print("\nVerifique se:")
        print("1. Chrome/Chromium esta instalado")
        print("2. ChromeDriver esta instalado (pip install webdriver-manager)")
        print("3. Frontend esta rodando em http://localhost:8081")
        print("4. Backend esta rodando em http://localhost:5000")
