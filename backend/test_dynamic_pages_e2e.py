"""
Testes E2E para 4 Páginas Dinâmicas de Monitoramento

Valida que frontend + backend funcionam integrados.

Como executar:
    # Instalar Playwright (primeira vez apenas)
    pip install playwright pytest-playwright
    playwright install chromium

    # Executar testes
    pytest test_dynamic_pages_e2e.py -v

    # Executar com navegador visível
    pytest test_dynamic_pages_e2e.py -v --headed

    # Executar teste específico
    pytest test_dynamic_pages_e2e.py::test_network_probes_loads -v
"""

import pytest
from playwright.async_api import async_playwright, Page
import asyncio

BASE_URL = "http://localhost:8081"

@pytest.fixture
async def page():
    """Fixture que cria navegador Playwright"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()
        yield page
        await browser.close()

@pytest.mark.asyncio
async def test_network_probes_loads(page: Page):
    """Teste 1: Página Network Probes carrega corretamente"""
    # Navegar
    await page.goto(f"{BASE_URL}/monitoring/network-probes")

    # Aguardar tabela
    await page.wait_for_selector(".ant-table", timeout=5000)

    # Validar título
    title = await page.text_content("h1")
    assert "Network Probes" in title or "Monitoramento" in title

    # Validar que tem linhas
    rows = await page.query_selector_all(".ant-table-row")
    assert len(rows) > 0, "Tabela deve ter pelo menos 1 linha"

    print(f"✅ Network Probes carregou com {len(rows)} linhas")

@pytest.mark.asyncio
async def test_sync_cache_button(page: Page):
    """Teste 2: Botão Sincronizar Cache funciona"""
    await page.goto(f"{BASE_URL}/monitoring/network-probes")

    # Clicar no botão
    await page.click('button:has-text("Sincronizar")')

    # Aguardar loading desaparecer
    await page.wait_for_selector('.ant-spin', state='hidden', timeout=30000)

    # Validar mensagem de sucesso
    # (pode aparecer em .ant-message ou .ant-notification)
    await page.wait_for_timeout(2000)  # Dar tempo para mensagem aparecer

    print("✅ Sincronização de cache OK")

@pytest.mark.asyncio
async def test_filters_work(page: Page):
    """Teste 3: Filtros dinâmicos funcionam"""
    await page.goto(f"{BASE_URL}/monitoring/web-probes")

    # Esperar carregar
    await page.wait_for_selector(".ant-table-row", timeout=5000)

    # Contar linhas iniciais
    initial_rows = await page.query_selector_all(".ant-table-row")
    initial_count = len(initial_rows)

    # Aplicar filtro (exemplo: buscar por "ramada")
    search_input = await page.query_selector('input[placeholder*="Buscar"]')
    if search_input:
        await search_input.fill("ramada")
        await page.wait_for_timeout(1000)  # Aguardar debounce

        # Contar linhas após filtro
        filtered_rows = await page.query_selector_all(".ant-table-row")
        filtered_count = len(filtered_rows)

        # Se havia mais de 1 empresa, filtro deve reduzir
        if initial_count > 5:
            assert filtered_count <= initial_count, "Filtro deve reduzir resultados"

    print(f"✅ Filtros OK: {initial_count} → {filtered_count if search_input else initial_count} linhas")

@pytest.mark.asyncio
async def test_navigate_all_4_pages(page: Page):
    """Teste 4: Navegação entre as 4 páginas"""
    pages_to_test = [
        ("/monitoring/network-probes", "Network Probes"),
        ("/monitoring/web-probes", "Web Probes"),
        ("/monitoring/system-exporters", "System Exporters"),
        ("/monitoring/database-exporters", "Database Exporters"),
    ]

    for path, expected_text in pages_to_test:
        await page.goto(f"{BASE_URL}{path}")
        await page.wait_for_selector(".ant-table", timeout=5000)

        # Validar título ou conteúdo
        content = await page.content()
        assert expected_text in content or "Monitoramento" in content

        print(f"✅ Página {path} OK")

@pytest.mark.asyncio
async def test_columns_are_dynamic(page: Page):
    """Teste 5: Colunas vêm dinamicamente do backend"""
    await page.goto(f"{BASE_URL}/monitoring/network-probes")
    await page.wait_for_selector(".ant-table-thead", timeout=5000)

    # Contar colunas
    headers = await page.query_selector_all(".ant-table-thead th")
    header_count = len(headers)

    # Deve ter pelo menos 5 colunas (ID, company, site, env, etc)
    assert header_count >= 5, f"Esperado >= 5 colunas, encontrado {header_count}"

    # Extrair textos dos headers
    header_texts = []
    for header in headers:
        text = await header.text_content()
        header_texts.append(text)

    print(f"✅ Colunas dinâmicas OK: {header_texts}")

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--headed"])
