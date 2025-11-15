#!/usr/bin/env python3
"""
Script Playwright para testar filtros visualmente
"""
import asyncio
from playwright.async_api import async_playwright

async def test_filters():
    async with async_playwright() as p:
        browser = await p.firefox.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()
        
        # Abrir página
        print("🌐 Abrindo página network-probes...")
        await page.goto('http://localhost:5173/monitoring/network-probes')
        
        # Aguardar carregamento
        print("⏳ Aguardando carregamento...")
        await page.wait_for_timeout(5000)
        
        # Capturar todos os selects
        selects = await page.query_selector_all('select, .ant-select')
        print(f"\n📋 Total de selects/filtros encontrados: {len(selects)}")
        
        # Verificar se há select com "Provedor"
        page_content = await page.content()
        
        has_empresa = 'Empresa' in page_content or 'company' in page_content.lower()
        has_provedor = 'Provedor' in page_content or 'provedor' in page_content.lower()
        
        print(f"\n🔍 ANÁLISE:")
        print(f"   Filtro 'Empresa' aparece: {'✅ SIM' if has_empresa else '❌ NÃO'}")
        print(f"   Filtro 'Provedor' aparece: {'✅ SIM' if has_provedor else '❌ NÃO'}")
        
        # Capturar screenshot
        await page.screenshot(path='/home/adrianofante/projetos/Skills-Eye/screenshot_filters.png', full_page=True)
        print(f"\n📸 Screenshot salvo: screenshot_filters.png")
        
        # Verificar console do browser
        console_messages = []
        page.on('console', lambda msg: console_messages.append(f"{msg.type}: {msg.text}"))
        
        await page.wait_for_timeout(2000)
        
        print(f"\n📝 Console do browser ({len(console_messages)} mensagens):")
        for msg in console_messages[-10:]:
            print(f"   {msg}")
        
        await browser.close()

if __name__ == '__main__':
    asyncio.run(test_filters())
