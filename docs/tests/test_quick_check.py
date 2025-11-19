#!/usr/bin/env python3
"""
Script rápido para verificar se requestHandler está sendo chamado
"""
from playwright.sync_api import sync_playwright
import time

def test_request_handler():
    print("🚀 Iniciando teste rápido do requestHandler...")
    
    with sync_playwright() as p:
        browser = p.firefox.launch(headless=False)
        page = browser.new_page()
        
        # Capturar TODOS os logs incluindo erros
        logs = []
        errors = []
        
        def handle_console(msg):
            text = msg.text
            logs.append(text)
            
            # Print apenas logs relevantes
            if any(keyword in text for keyword in ['DEBUG', 'PERF', 'ERROR', 'ERRO', 'Failed', 'extraindo', 'company', 'provedor']):
                timestamp = time.strftime('%H:%M:%S')
                print(f"[{timestamp}] {text}")
            
            # Capturar erros separadamente
            if msg.type in ['error', 'warning']:
                timestamp = time.strftime('%H:%M:%S')
                error_msg = f"[{timestamp}] [{msg.type.upper()}] {text}"
                print(error_msg)
                errors.append(error_msg)
        
        page.on('console', handle_console)
        
        print("📍 Navegando para http://localhost:8081/monitoring/network-probes")
        page.goto('http://localhost:8081/monitoring/network-probes', wait_until='load', timeout=30000)
        
        print("⏳ Aguardando 20 segundos para requestHandler completar...")
        time.sleep(20)
        
        # Verificações - processar logs capturados ATÉ AGORA
        time.sleep(2) # Aguardar mais um pouco para logs atrasados
        
        has_debug = any('DEBUG' in log for log in logs)
        has_perf = any('PERF' in log for log in logs)
        has_extract = any('extraindo metadataOptions' in log for log in logs)
        has_company_with_data = any('company' in log and not 'Opções: 0' in log for log in logs)
        
        print(f"\n📊 RESULTADO:")
        print(f"   DEBUG logs: {'✅' if has_debug else '❌'}")
        print(f"   PERF logs: {'✅' if has_perf else '❌'}")
        print(f"   Extract metadata: {'✅' if has_extract else '❌'}")
        print(f"   Company with data: {'✅' if has_company_with_data else '❌'}")
        print(f"   Errors: {len(errors)}")
        
        if errors:
            print("\n🔴 ERROS CAPTURADOS:")
            for error in errors[:10]:  # Mostrar apenas primeiros 10
                print(f"   {error}")
        
        if has_perf and has_company_with_data:
            print("\n✅✅ SUCESSO TOTAL - requestHandler executou E metadataOptions populado!")
        elif has_perf:
            print("\n⚠️  requestHandler INICIOU mas não completou (sem logs de extração)")
        else:
            print("\n❌ requestHandler NÃO FOI EXECUTADO")
        
        browser.close()

if __name__ == '__main__':
    test_request_handler()
