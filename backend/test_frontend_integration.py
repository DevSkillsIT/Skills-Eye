#!/usr/bin/env python3
"""
TESTES DE INTEGRAÇÃO FRONTEND - PERSISTÊNCIA DE CUSTOMIZAÇÕES

Usa Playwright para simular interações reais do usuário:
1. Abrir página Metadata Fields
2. Customizar campos via UI
3. Clicar em "Sincronizar"
4. Recarregar página (F5)
5. Limpar cache do browser
6. Verificar se customizações persistiram

REQUISITOS:
    pip install playwright pytest-playwright
    playwright install chromium

EXECUÇÃO:
    python3 test_frontend_integration.py
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime
import json

sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from playwright.async_api import async_playwright, Page, Browser
except ImportError:
    print("❌ Playwright não instalado!")
    print("Execute: pip install playwright pytest-playwright")
    print("Execute: playwright install chromium")
    sys.exit(1)

from core.kv_manager import KVManager

FRONTEND_URL = "http://localhost:3000"
TEST_FIELDS = ['vendor', 'region', 'campoextra1']

class Colors:
    HEADER = '\033[95m'
    OKGREEN = '\033[92m'
    FAIL = '\033[91m'
    WARNING = '\033[93m'
    OKCYAN = '\033[96m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def print_header(text: str):
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'=' * 80}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{text.center(80)}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'=' * 80}{Colors.ENDC}\n")

def print_success(text: str):
    print(f"{Colors.OKGREEN}✅ {text}{Colors.ENDC}")

def print_error(text: str):
    print(f"{Colors.FAIL}❌ {text}{Colors.ENDC}")

def print_warning(text: str):
    print(f"{Colors.WARNING}⚠️  {text}{Colors.ENDC}")

def print_info(text: str):
    print(f"{Colors.OKCYAN}ℹ️  {text}{Colors.ENDC}")


async def setup_browser() -> tuple[Browser, Page]:
    """Inicia browser e navega para página"""
    print_info("Iniciando Chromium...")
    
    playwright = await async_playwright().start()
    browser = await playwright.chromium.launch(headless=False)  # headless=False para ver
    context = await browser.new_context()
    page = await context.new_page()
    
    print_info(f"Navegando para {FRONTEND_URL}/metadata-fields")
    await page.goto(f"{FRONTEND_URL}/metadata-fields")
    
    # Aguardar carregamento
    await page.wait_for_load_state('networkidle')
    
    return browser, page


async def test_ui_customize_fields(page: Page):
    """Customiza campos via UI"""
    print_header("UI TEST 1: Customizar Campos via Interface")
    
    for field_name in TEST_FIELDS:
        print_info(f"Customizando campo '{field_name}'...")
        
        # Procurar linha do campo na tabela
        row_locator = page.locator(f'tr:has-text("{field_name}")').first
        
        # Clicar em botão "Editar" (ícone de edição)
        edit_button = row_locator.locator('button[aria-label="edit"], button:has(svg[data-icon="edit"])').first
        await edit_button.click()
        
        # Aguardar modal abrir
        await page.wait_for_selector('.ant-modal', state='visible', timeout=5000)
        
        # Marcar "Required"
        required_checkbox = page.locator('input[type="checkbox"]').filter(has_text='Required')
        if not await required_checkbox.is_checked():
            await required_checkbox.click()
        
        # Marcar "Auto Register"
        auto_register_checkbox = page.locator('input[type="checkbox"]').filter(has_text='Auto Register')
        if not await auto_register_checkbox.is_checked():
            await auto_register_checkbox.click()
        
        # Alterar categoria
        category_input = page.locator('input[placeholder*="Category"], select[name="category"]').first
        await category_input.fill('ui_test_category')
        
        # Salvar
        save_button = page.locator('button:has-text("Salvar"), button:has-text("Save"), button:has-text("OK")').first
        await save_button.click()
        
        # Aguardar modal fechar
        await page.wait_for_selector('.ant-modal', state='hidden', timeout=5000)
        
        print_success(f"Campo '{field_name}' customizado via UI")
        
        # Aguardar 1 segundo entre edições
        await asyncio.sleep(1)
    
    return True


async def test_ui_sync_button(page: Page):
    """Clica no botão Sincronizar"""
    print_header("UI TEST 2: Botão Sincronizar")
    
    # Procurar botão "Sincronizar" ou "Force Extract"
    sync_button = page.locator('button:has-text("Sincronizar"), button:has-text("Force"), button:has-text("Sync")').first
    
    print_info("Clicando em 'Sincronizar'...")
    await sync_button.click()
    
    # Aguardar confirmação (se houver)
    confirm_button = page.locator('button:has-text("Confirmar"), button:has-text("OK"), button:has-text("Sim")')
    if await confirm_button.count() > 0:
        await confirm_button.first.click()
    
    # Aguardar loading/spinner desaparecer
    await page.wait_for_load_state('networkidle')
    
    print_success("Sincronização concluída")
    return True


async def test_ui_page_reload(page: Page):
    """Recarrega página (F5)"""
    print_header("UI TEST 3: Recarregar Página (F5)")
    
    print_info("Recarregando página...")
    await page.reload()
    await page.wait_for_load_state('networkidle')
    
    print_success("Página recarregada")
    return True


async def test_ui_clear_cache(page: Page, browser: Browser):
    """Limpa cache e cookies do browser"""
    print_header("UI TEST 4: Limpar Cache e Cookies")
    
    print_info("Limpando cache do browser...")
    
    # Limpar cookies e storage
    context = page.context
    await context.clear_cookies()
    await page.evaluate('() => localStorage.clear()')
    await page.evaluate('() => sessionStorage.clear()')
    
    # Recarregar
    await page.reload()
    await page.wait_for_load_state('networkidle')
    
    print_success("Cache limpo e página recarregada")
    return True


async def verify_ui_customizations(page: Page):
    """Verifica customizações via UI"""
    print_header("VERIFICAÇÃO: Customizações na UI")
    
    errors = []
    
    for field_name in TEST_FIELDS:
        print_info(f"Verificando campo '{field_name}'...")
        
        # Procurar linha do campo
        row_locator = page.locator(f'tr:has-text("{field_name}")').first
        
        # Clicar em "Editar"
        edit_button = row_locator.locator('button[aria-label="edit"], button:has(svg[data-icon="edit"])').first
        await edit_button.click()
        
        # Aguardar modal
        await page.wait_for_selector('.ant-modal', state='visible', timeout=5000)
        
        # Verificar "Required"
        required_checkbox = page.locator('input[type="checkbox"]').filter(has_text='Required').first
        if not await required_checkbox.is_checked():
            errors.append(f"Campo '{field_name}': Required não está marcado")
        
        # Verificar "Auto Register"
        auto_register_checkbox = page.locator('input[type="checkbox"]').filter(has_text='Auto Register').first
        if not await auto_register_checkbox.is_checked():
            errors.append(f"Campo '{field_name}': Auto Register não está marcado")
        
        # Verificar categoria
        category_input = page.locator('input[placeholder*="Category"], select[name="category"]').first
        category_value = await category_input.input_value()
        if category_value != 'ui_test_category':
            errors.append(f"Campo '{field_name}': Category incorreta (esperado 'ui_test_category', obtido '{category_value}')")
        
        # Fechar modal
        close_button = page.locator('button:has-text("Cancelar"), button:has-text("Cancel"), button.ant-modal-close').first
        await close_button.click()
        await page.wait_for_selector('.ant-modal', state='hidden', timeout=5000)
        
        if not errors:
            print_success(f"Campo '{field_name}' OK")
        
        await asyncio.sleep(1)
    
    if errors:
        print_error(f"{len(errors)} erro(s) encontrado(s):")
        for err in errors:
            print_warning(f"  - {err}")
        return False
    
    print_success("Todas customizações PRESERVADAS na UI!")
    return True


async def verify_kv_customizations():
    """Verifica customizações diretamente no KV"""
    print_header("VERIFICAÇÃO: Customizações no KV")
    
    kv = KVManager()
    fields_config = await kv.get_json('skills/eye/metadata/fields')
    
    if not fields_config or 'fields' not in fields_config:
        print_error("KV vazio!")
        return False
    
    errors = []
    
    for field in fields_config['fields']:
        if field['name'] in TEST_FIELDS:
            if not field.get('required'):
                errors.append(f"Campo '{field['name']}': required=False no KV")
            
            if not field.get('auto_register'):
                errors.append(f"Campo '{field['name']}': auto_register=False no KV")
            
            if field.get('category') != 'ui_test_category':
                errors.append(f"Campo '{field['name']}': category incorreta no KV")
    
    if errors:
        print_error(f"{len(errors)} erro(s) no KV:")
        for err in errors:
            print_warning(f"  - {err}")
        return False
    
    print_success("Customizações OK no KV!")
    return True


async def cleanup_ui_test_data():
    """Limpar dados de teste da UI"""
    print_header("CLEANUP: Remover Dados de Teste UI")
    
    kv = KVManager()
    fields_config = await kv.get_json('skills/eye/metadata/fields')
    
    if not fields_config or 'fields' not in fields_config:
        print_warning("KV vazio, nada para limpar")
        return
    
    cleaned = 0
    for field in fields_config['fields']:
        if field.get('category') == 'ui_test_category':
            field['required'] = False
            field['auto_register'] = False
            field['category'] = 'extra'
            cleaned += 1
    
    fields_config['last_updated'] = datetime.now().isoformat()
    await kv.put_json('skills/eye/metadata/fields', fields_config)
    
    print_success(f"{cleaned} customizações removidas")


async def main():
    """Executa testes de integração frontend"""
    
    print_header("🌐 TESTES DE INTEGRAÇÃO FRONTEND - PLAYWRIGHT")
    print_info(f"Data/Hora: {datetime.now()}")
    print_info(f"URL: {FRONTEND_URL}")
    print()
    
    browser = None
    page = None
    
    try:
        # Iniciar browser
        browser, page = await setup_browser()
        
        # Lista de testes
        ui_tests = [
            ("Customizar Campos via UI", lambda: test_ui_customize_fields(page)),
            ("Verificar KV após UI", verify_kv_customizations),
            ("Botão Sincronizar", lambda: test_ui_sync_button(page)),
            ("Verificar após Sync", verify_kv_customizations),
            ("Recarregar Página (F5)", lambda: test_ui_page_reload(page)),
            ("Verificar após F5", lambda: verify_ui_customizations(page)),
            ("Limpar Cache", lambda: test_ui_clear_cache(page, browser)),
            ("Verificar após Clear Cache", lambda: verify_ui_customizations(page)),
        ]
        
        results = {}
        
        # Executar cada teste
        for test_name, test_func in ui_tests:
            print()
            input(f"Pressione ENTER para executar: {test_name}...")
            
            try:
                test_ok = await test_func()
                results[test_name] = test_ok
            except Exception as e:
                print_error(f"Teste '{test_name}' exception: {e}")
                results[test_name] = False
            
            await asyncio.sleep(2)
        
        # RELATÓRIO FINAL
        print_header("📊 RELATÓRIO DE TESTES UI")
        
        total = len(results)
        passed = sum(1 for r in results.values() if r)
        failed = total - passed
        
        print(f"\nTotal de Testes: {total}")
        print(f"{Colors.OKGREEN}Passou: {passed}{Colors.ENDC}")
        print(f"{Colors.FAIL}Falhou: {failed}{Colors.ENDC}")
        print()
        
        for test_name, result in results.items():
            status = "✅ PASSOU" if result else "❌ FALHOU"
            color = Colors.OKGREEN if result else Colors.FAIL
            print(f"{color}{status}{Colors.ENDC} - {test_name}")
        
        print()
        
        # Cleanup
        await cleanup_ui_test_data()
        
        # Fechar browser
        if browser:
            await browser.close()
        
        sys.exit(0 if failed == 0 else 1)
    
    except Exception as e:
        print_error(f"Erro fatal: {e}")
        
        if browser:
            await browser.close()
        
        sys.exit(1)


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n❌ Testes UI interrompidos")
        sys.exit(1)
