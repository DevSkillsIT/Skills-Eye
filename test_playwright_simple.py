#!/usr/bin/env python3
"""
Teste Playwright SIMPLIFICADO - apenas captura console logs
"""
import asyncio
from playwright.async_api import async_playwright

async def test_console_logs():
    async with async_playwright() as p:
        browser = await p.firefox.launch(headless=False, slow_mo=500)
        page = await browser.new_page()
        
        # Capturar TODOS os console logs
        all_logs = []
        def handle_console(msg):
            all_logs.append(f"[{msg.type}] {msg.text}")
        page.on('console', handle_console)
        
        print("🌐 Navegando para network-probes...")
        await page.goto('http://localhost:8081/monitoring/network-probes', wait_until='load', timeout=60000)
        
        print("⏳ Aguardando 10 segundos para carregar dados...")
        await page.wait_for_timeout(10000)
        
        # Filtrar logs relevantes
        print("\n📝 CONSOLE LOGS - MetadataFilterBar:")
        filter_logs = [log for log in all_logs if 'MetadataFilterBar' in log]
        for log in filter_logs:
            print(f"   {log}")
        
        print("\n📝 CONSOLE LOGS - metadataOptions:")
        metadata_logs = [log for log in all_logs if 'metadataOptions' in log or 'DEBUG' in log]
        for log in metadata_logs[-10:]:
            print(f"   {log}")
        
        # Screenshot
        await page.screenshot(path='screenshot_debug.png', full_page=True)
        print("\n📸 Screenshot: screenshot_debug.png")
        
        print("\n⏸️  Browser aberto por 20s para inspeção...")
        await page.wait_for_timeout(20000)
        
        await browser.close()

if __name__ == '__main__':
    asyncio.run(test_console_logs())
