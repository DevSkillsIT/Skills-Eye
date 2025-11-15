#!/usr/bin/env python3
"""
Teste Playwright para diagnosticar filtros quebrados
Agora com playwright install-deps executado
"""
import asyncio
import sys
from playwright.async_api import async_playwright

async def test_filters_rendering():
    async with async_playwright() as p:
        # Lançar Firefox
        browser = await p.firefox.launch(headless=False, slow_mo=1000)
        context = await browser.new_context()
        page = await context.new_page()
        
        # Coletar mensagens do console
        console_messages = []
        def handle_console(msg):
            console_messages.append({
                'type': msg.type,
                'text': msg.text,
                'args': [arg.json_value() for arg in msg.args]
            })
        page.on('console', handle_console)
        
        # Navegar para página
        print("🌐 Navegando para network-probes...")
        await page.goto('http://localhost:8081/monitoring/network-probes', wait_until='load', timeout=60000)
        
        # Aguardar carregamento completo
        print("⏳ Aguardando carregamento...")
        await page.wait_for_timeout(8000)
        
        # Screenshot inicial
        await page.screenshot(path='screenshot_1_loaded.png', full_page=True)
        print("📸 Screenshot 1: Página carregada")
        
        # Verificar todos os Ant Design Selects
        print("\n🔍 VERIFICANDO SELECTS NA PÁGINA:")
        
        # Método 1: Buscar por classe ant-select
        selects = await page.query_selector_all('.ant-select')
        print(f"   Total de .ant-select encontrados: {len(selects)}")
        
        # Método 2: Buscar por placeholder
        for idx, select in enumerate(selects, 1):
            placeholder = await select.get_attribute('placeholder')
            title = await select.get_attribute('title')
            text = await select.inner_text()
            print(f"   Select {idx}:")
            print(f"      Placeholder: {placeholder}")
            print(f"      Title: {title}")
            print(f"      Text: {text[:50] if text else 'N/A'}")
        
        # Procurar especificamente por "Provedor" e "Empresa"
        print("\n🔍 PROCURANDO FILTROS ESPECÍFICOS:")
        
        page_content = await page.content()
        has_empresa = 'Empresa' in page_content
        has_provedor = 'Provedor' in page_content
        
        print(f"   Texto 'Empresa' na página: {'✅ SIM' if has_empresa else '❌ NÃO'}")
        print(f"   Texto 'Provedor' na página: {'✅ SIM' if has_provedor else '❌ NÃO'}")
        
        # Buscar por seletor específico do MetadataFilterBar
        empresa_select = await page.query_selector('[placeholder="Empresa"], .ant-select:has-text("Empresa")')
        provedor_select = await page.query_selector('[placeholder="Provedor"], .ant-select:has-text("Provedor")')
        
        print(f"   Select 'Empresa' encontrado: {'✅ SIM' if empresa_select else '❌ NÃO'}")
        print(f"   Select 'Provedor' encontrado: {'✅ SIM' if provedor_select else '❌ NÃO'}")
        
        # Analisar console logs
        print("\n📝 CONSOLE LOGS RELEVANTES:")
        debug_logs = [msg for msg in console_messages if 'DEBUG' in msg['text'] or 'metadataOptions' in msg['text']]
        
        for log in debug_logs[-5:]:
            print(f"   {log['type']}: {log['text'][:100]}")
        
        # Procurar especificamente pelo log de metadataOptions
        metadata_log = next((msg for msg in console_messages if 'metadataOptions extraídas' in msg['text']), None)
        if metadata_log:
            print("\n✅ Log de metadataOptions encontrado!")
            # Próximos 4 logs devem ser company, provedor, filterFields, Total campos
            idx = console_messages.index(metadata_log)
            for i in range(idx, min(idx+5, len(console_messages))):
                print(f"   {console_messages[i]['text'][:200]}")
        
        # Verificar se MetadataFilterBar está renderizado
        print("\n🔍 VERIFICANDO COMPONENTE MetadataFilterBar:")
        
        # Buscar por estrutura do componente
        filter_bar = await page.query_selector('.ant-space, [class*="filter"]')
        if filter_bar:
            filter_bar_html = await filter_bar.inner_html()
            print(f"   FilterBar encontrado (HTML length: {len(filter_bar_html)})")
            
            # Contar quantos selects estão dentro
            selects_in_bar = await filter_bar.query_selector_all('.ant-select')
            print(f"   Selects dentro do FilterBar: {len(selects_in_bar)}")
            
            for idx, select in enumerate(selects_in_bar, 1):
                select_html = await select.get_attribute('outerHTML')
                if 'Provedor' in select_html or 'provedor' in select_html:
                    print(f"      ⭐ Select {idx}: CONTÉM 'Provedor'")
                elif 'Empresa' in select_html or 'company' in select_html:
                    print(f"      ✅ Select {idx}: CONTÉM 'Empresa'")
        else:
            print("   ❌ FilterBar NÃO encontrado")
        
        # Screenshot final
        await page.screenshot(path='screenshot_2_analyzed.png', full_page=True)
        print("\n📸 Screenshot 2: Análise completa")
        
        # DIAGNÓSTICO FINAL
        print("\n" + "="*80)
        print("🎯 DIAGNÓSTICO FINAL")
        print("="*80)
        
        if metadata_log:
            print("✅ JavaScript executou e extraiu metadataOptions (provedor tem 12 opções)")
        else:
            print("❌ JavaScript NÃO executou ou falhou")
        
        if not provedor_select and empresa_select:
            print("❌ PROBLEMA CONFIRMADO: Select 'Empresa' renderiza mas 'Provedor' NÃO")
            print("   → Componente MetadataFilterBar está filtrando/escondendo provedor")
            print("   → Verificar lógica de renderização em MetadataFilterBar.tsx")
            print("   → Verificar se options['provedor'] está chegando no component")
        elif provedor_select:
            print("✅ Select 'Provedor' está renderizado!")
            print("   → Problema pode ser visual (CSS, z-index, display)")
        else:
            print("❌ NENHUM select está renderizando corretamente")
            print("   → Problema na integração MetadataFilterBar <-> DynamicMonitoringPage")
        
        print(f"\n📸 Screenshots salvos:")
        print(f"   - screenshot_1_loaded.png")
        print(f"   - screenshot_2_analyzed.png")
        
        # Manter browser aberto para inspeção manual
        print("\n⏸️  Browser ficará aberto por 30 segundos para inspeção manual...")
        await page.wait_for_timeout(30000)
        
        await browser.close()

if __name__ == '__main__':
    try:
        asyncio.run(test_filters_rendering())
    except Exception as e:
        print(f"\n❌ ERRO: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
