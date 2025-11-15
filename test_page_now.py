#!/usr/bin/env python3
"""
Teste DIRETO da página para ver os ERROS REAIS no console
"""
from playwright.sync_api import sync_playwright
import time

print("🌐 Abrindo página http://localhost:8081/monitoring/network-probes")
print("=" * 80)

with sync_playwright() as p:
    browser = p.firefox.launch(headless=False, slow_mo=500)
    page = browser.new_page()
    
    # Capturar TODOS os logs do console
    console_logs = []
    page.on("console", lambda msg: console_logs.append(f"[{msg.type().upper()}] {msg.text()}"))
    
    # Capturar erros
    errors = []
    page.on("pageerror", lambda err: errors.append(str(err)))
    
    print("📍 Navegando para a página...")
    page.goto('http://localhost:8081/monitoring/network-probes')
    
    print("⏳ Aguardando 10 segundos para carregar...")
    time.sleep(10)
    
    print("\n" + "=" * 80)
    print("📋 CONSOLE LOGS:")
    print("=" * 80)
    for log in console_logs[-30:]:  # Últimos 30 logs
        print(log)
    
    if errors:
        print("\n" + "=" * 80)
        print("❌ ERROS:")
        print("=" * 80)
        for err in errors:
            print(err)
    
    print("\n" + "=" * 80)
    print("🔍 Verificando elementos na página...")
    print("=" * 80)
    
    # Verificar NodeSelector
    try:
        node_selector = page.locator('div:has-text("Nó do Consul")').first
        if node_selector.is_visible():
            print("✅ NodeSelector visível")
            # Pegar texto do select
            select_text = page.locator('.ant-select-selection-item').first.text_content()
            print(f"   Texto atual: {select_text}")
        else:
            print("❌ NodeSelector NÃO visível")
    except Exception as e:
        print(f"❌ Erro ao verificar NodeSelector: {e}")
    
    # Verificar tabela
    try:
        table = page.locator('.ant-table-tbody tr')
        count = table.count()
        print(f"📊 Linhas na tabela: {count}")
        if count == 0:
            print("   ⚠️  TABELA VAZIA!")
    except Exception as e:
        print(f"❌ Erro ao verificar tabela: {e}")
    
    print("\n" + "=" * 80)
    print("✋ Navegador aberto - VOCÊ pode interagir agora!")
    print("   Pressione CTRL+C para fechar")
    print("=" * 80)
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n👋 Fechando...")
    
    browser.close()
