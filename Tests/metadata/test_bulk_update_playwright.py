#!/usr/bin/env python3
"""
Teste Visual com Playwright - Bulk Update Reference Values

OBJETIVO:
- Testar VISUALMENTE o rename no navegador
- Validar que serviço aparece com novo valor na página Services
- Capturar screenshots ANTES e DEPOIS
- Medir tempos de resposta
"""

import asyncio
import sys
from datetime import datetime
from playwright.async_api import async_playwright, Page

# ============================================================================
# CONFIGURAÇÃO
# ============================================================================

FRONTEND_URL = "http://localhost:8081"
BACKEND_URL = "http://localhost:5000/api/v1"

# Cores para output
RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"

# ============================================================================
# FUNÇÕES AUXILIARES
# ============================================================================

def log_info(msg: str):
    print(f"{BLUE}[INFO]{RESET} {msg}")

def log_success(msg: str):
    print(f"{GREEN}[✓]{RESET} {msg}")

def log_error(msg: str):
    print(f"{RED}[✗]{RESET} {msg}")

def log_warning(msg: str):
    print(f"{YELLOW}[!]{RESET} {msg}")

async def wait_for_network_idle(page: Page, timeout: int = 5000):
    """Aguarda network idle"""
    try:
        await page.wait_for_load_state("networkidle", timeout=timeout)
    except:
        pass  # Ignore timeout

# ============================================================================
# TESTE PLAYWRIGHT
# ============================================================================

async def run_visual_test():
    """
    Executa teste visual com Playwright.
    """

    print("=" * 80)
    print(f"{BLUE}TESTE VISUAL (PLAYWRIGHT) - BULK UPDATE{RESET}")
    print("=" * 80)
    print()

    test_passed = False
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    async with async_playwright() as p:
        # Lançar navegador
        log_info("Lançando navegador...")
        browser = await p.chromium.launch(headless=False)  # headless=False para ver
        context = await browser.new_context(viewport={"width": 1920, "height": 1080})
        page = await context.new_page()

        try:
            # ================================================================
            # PASSO 1: Criar serviço de teste via API
            # ================================================================
            log_info("PASSO 1: Criando serviço de teste via API...")

            test_service_id = f"test-visual-{timestamp}"
            test_company = f"VisualTest_{timestamp}"

            # Usar fetch do navegador para chamar API
            create_service_script = f"""
                fetch('{BACKEND_URL}/services', {{
                    method: 'POST',
                    headers: {{'Content-Type': 'application/json'}},
                    body: JSON.stringify({{
                        ID: '{test_service_id}',
                        Name: 'test-visual-service',
                        Address: '127.0.0.1',
                        Port: 9998,
                        Tags: ['test', 'visual'],
                        Meta: {{
                            company: '{test_company}',
                            env: 'test',
                            tipo_monitoramento: 'visual_test'
                        }}
                    }})
                }})
                .then(r => r.json())
                .then(data => data)
            """

            result = await page.evaluate(create_service_script)
            log_success(f"Serviço '{test_service_id}' criado")
            print()

            # Aguardar propagação
            await asyncio.sleep(2)

            # ================================================================
            # PASSO 2: Navegar para página Services
            # ================================================================
            log_info("PASSO 2: Acessando página Services...")

            await page.goto(f"{FRONTEND_URL}/services", wait_until="networkidle")
            await wait_for_network_idle(page)

            log_success("Página Services carregada")
            print()

            # Aguardar tabela carregar
            await page.wait_for_selector(".ant-table-tbody", timeout=10000)
            await asyncio.sleep(2)

            # ================================================================
            # PASSO 3: Buscar serviço na tabela ANTES do rename
            # ================================================================
            log_info("PASSO 3: Buscando serviço na tabela...")

            # Buscar por test_service_id
            search_input = await page.query_selector("input[placeholder*='Buscar']")
            if search_input:
                await search_input.fill(test_service_id)
                await asyncio.sleep(1)

            # Screenshot ANTES
            screenshot_before = f"test_before_{timestamp}.png"
            await page.screenshot(path=screenshot_before, full_page=True)
            log_success(f"Screenshot ANTES salvo: {screenshot_before}")

            # Verificar se serviço aparece
            service_row = await page.query_selector(f"text={test_service_id}")
            if not service_row:
                log_error(f"Serviço '{test_service_id}' NÃO encontrado na tabela!")
                return False

            log_success(f"Serviço '{test_service_id}' encontrado na tabela")
            log_info(f"  Empresa ANTES: {test_company}")
            print()

            # ================================================================
            # PASSO 4: Navegar para Reference Values e fazer rename
            # ================================================================
            log_info("PASSO 4: Navegando para Reference Values...")

            await page.goto(f"{FRONTEND_URL}/reference-values", wait_until="networkidle")
            await wait_for_network_idle(page)

            log_success("Página Reference Values carregada")
            print()

            # Aguardar cards de categorias carregarem
            await page.wait_for_selector(".ant-card", timeout=10000)
            await asyncio.sleep(1)

            # Clicar no card "company" (categoria Básico)
            log_info("Selecionando campo 'company'...")

            company_card = await page.query_selector("text=Empresa")
            if company_card:
                await company_card.click()
                await asyncio.sleep(1)
                log_success("Campo 'company' selecionado")
            else:
                log_error("Card 'Empresa' não encontrado!")
                return False

            print()

            # Aguardar tabela de valores carregar
            await page.wait_for_selector(".ant-table-tbody", timeout=10000)
            await asyncio.sleep(1)

            # Buscar valor test_company
            log_info(f"Buscando valor '{test_company}'...")

            search_values = await page.query_selector("input[placeholder*='Buscar valores']")
            if search_values:
                await search_values.fill(test_company)
                await asyncio.sleep(1)

            # Encontrar linha com test_company e clicar em Editar
            log_info("Clicando em Editar...")

            # Procurar botão Editar (ícone EditOutlined)
            edit_buttons = await page.query_selector_all("button[aria-label='edit']")
            if not edit_buttons:
                # Tentar encontrar qualquer botão com ícone de editar
                edit_buttons = await page.query_selector_all("button >> svg[data-icon='edit']")

            if edit_buttons and len(edit_buttons) > 0:
                await edit_buttons[0].click()
                await asyncio.sleep(1)
                log_success("Modal de edição aberto")
            else:
                log_error("Botão Editar não encontrado!")
                return False

            print()

            # Aguardar modal abrir
            await page.wait_for_selector(".ant-modal", timeout=5000)
            await asyncio.sleep(1)

            # Alterar valor
            new_company = f"{test_company}_RENAMED"
            log_info(f"Alterando valor para '{new_company}'...")

            # Limpar campo e digitar novo valor
            value_input = await page.query_selector(".ant-modal input[id*='value']")
            if value_input:
                await value_input.fill("")  # Limpar
                await value_input.fill(new_company)  # Preencher novo valor
                await asyncio.sleep(1)
                log_success(f"Novo valor digitado: '{new_company}'")
            else:
                log_error("Campo de valor não encontrado no modal!")
                return False

            print()

            # Clicar em OK para salvar (EXECUTAR BULK UPDATE)
            log_warning("EXECUTANDO BULK UPDATE...")

            start_time = datetime.now()

            ok_button = await page.query_selector(".ant-modal button.ant-btn-primary")
            if ok_button:
                await ok_button.click()
            else:
                log_error("Botão OK não encontrado!")
                return False

            # Aguardar modal fechar
            await page.wait_for_selector(".ant-modal", state="hidden", timeout=30000)

            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()

            log_success(f"Bulk update concluído em {duration:.2f}s")
            print()

            # Aguardar tabela atualizar
            await asyncio.sleep(2)

            # ================================================================
            # PASSO 5: Voltar para Services e validar
            # ================================================================
            log_info("PASSO 5: Voltando para página Services...")

            await page.goto(f"{FRONTEND_URL}/services", wait_until="networkidle")
            await wait_for_network_idle(page)

            log_success("Página Services carregada")
            print()

            # Aguardar tabela carregar
            await page.wait_for_selector(".ant-table-tbody", timeout=10000)
            await asyncio.sleep(2)

            # Buscar serviço novamente
            search_input = await page.query_selector("input[placeholder*='Buscar']")
            if search_input:
                await search_input.fill(test_service_id)
                await asyncio.sleep(1)

            # Screenshot DEPOIS
            screenshot_after = f"test_after_{timestamp}.png"
            await page.screenshot(path=screenshot_after, full_page=True)
            log_success(f"Screenshot DEPOIS salvo: {screenshot_after}")
            print()

            # ================================================================
            # PASSO 6: VALIDAR que valor mudou
            # ================================================================
            log_info("PASSO 6: VALIDANDO que empresa mudou na tabela...")

            # Verificar se novo valor aparece
            new_value_element = await page.query_selector(f"text={new_company}")
            old_value_element = await page.query_selector(f"text={test_company}")

            if new_value_element:
                log_success(f"✅ NOVO valor '{new_company}' aparece na tabela!")
            else:
                log_error(f"❌ NOVO valor '{new_company}' NÃO aparece na tabela!")

            if not old_value_element:
                log_success(f"✅ VALOR ANTIGO '{test_company}' NÃO aparece (correto!)")
            else:
                log_warning(f"⚠️ VALOR ANTIGO '{test_company}' ainda aparece (cache?)")

            print()

            if new_value_element and not old_value_element:
                log_success("✅ VALIDAÇÃO VISUAL PASSOU!")
                test_passed = True
            else:
                log_error("❌ VALIDAÇÃO VISUAL FALHOU!")

        except Exception as e:
            log_error(f"ERRO DURANTE TESTE VISUAL: {e}")
            import traceback
            traceback.print_exc()

        finally:
            # Aguardar 5 segundos antes de fechar navegador
            log_info("Aguardando 5 segundos antes de fechar navegador...")
            await asyncio.sleep(5)

            # Fechar navegador
            await browser.close()

    # ====================================================================
    # RESULTADO FINAL
    # ====================================================================
    print()
    print("=" * 80)
    if test_passed:
        print(f"{GREEN}✅ TESTE VISUAL PASSOU{RESET}")
        print(f"{GREEN}✅ Bulk update funciona corretamente no navegador{RESET}")
    else:
        print(f"{RED}❌ TESTE VISUAL FALHOU{RESET}")
        print(f"{RED}❌ Bulk update NÃO funciona corretamente{RESET}")
    print("=" * 80)

    return 0 if test_passed else 1

# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    exit_code = asyncio.run(run_visual_test())
    sys.exit(exit_code)
