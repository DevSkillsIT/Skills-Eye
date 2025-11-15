#!/usr/bin/env python3
"""
Script para abrir browser real e capturar TODOS os logs console
incluindo estado de metadataOptions e props do MetadataFilterBar
"""

import asyncio
from playwright.async_api import async_playwright
import json
from datetime import datetime

async def test_manual_browser():
    """Abre browser real e captura logs detalhados"""
    
    async with async_playwright() as p:
        # Usar Firefox (user está usando)
        browser = await p.firefox.launch(headless=False)  # headless=False mostra browser
        context = await browser.new_context()
        page = await context.new_page()
        
        # Estrutura para armazenar logs
        logs = {
            "requestHandler": [],
            "setMetadataOptions": [],
            "metadataFilterBar": [],
            "props_updates": [],
            "errors": []
        }
        
        def categorize_log(msg):
            """Categoriza e salva logs"""
            text = msg.text
            timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
            
            # Categorizar por conteúdo
            if "[PERF]" in text:
                logs["requestHandler"].append(f"[{timestamp}] {text}")
                print(f"✅ {text}")
            elif "setMetadataOptions" in text or "metadataOptions calculado" in text:
                logs["setMetadataOptions"].append(f"[{timestamp}] {text}")
                print(f"🔧 {text}")
            elif "MetadataFilterBar" in text or "Campo:" in text:
                logs["metadataFilterBar"].append(f"[{timestamp}] {text}")
                print(f"📊 {text}")
            elif "Props atualizadas" in text:
                logs["props_updates"].append(f"[{timestamp}] {text}")
                print(f"🔄 {text}")
            elif msg.type == "error":
                logs["errors"].append(f"[{timestamp}] ERROR: {text}")
                print(f"❌ ERROR: {text}")
            else:
                # Outros logs
                print(f"ℹ️  [{timestamp}] {text}")
        
        # Capturar TODOS os console logs
        page.on("console", categorize_log)
        
        print("\n" + "="*80)
        print("🌐 ABRINDO BROWSER REAL - Firefox")
        print("="*80)
        print(f"URL: http://localhost:8081/monitoring/network-probes")
        print("Aguardando carregamento completo da página de monitoramento...")
        print("="*80 + "\n")
        
        try:
            # Navegar DIRETO para página de monitoramento
            await page.goto("http://localhost:8081/monitoring/network-probes", wait_until="networkidle", timeout=30000)
            
            # Aguardar ProTable renderizar
            print("\n⏳ Aguardando ProTable carregar...")
            await page.wait_for_selector('.ant-pro-table', timeout=20000)
            print("✅ ProTable detectado!\n")
            
            # Aguardar alguns segundos para garantir que todos os logs apareçam
            print("⏳ Aguardando 5 segundos para capturar todos os logs...")
            await asyncio.sleep(5)
            
            # Análise final
            print("\n" + "="*80)
            print("📊 ANÁLISE DE LOGS CAPTURADOS")
            print("="*80)
            
            print(f"\n[requestHandler] logs: {len(logs['requestHandler'])}")
            for log in logs['requestHandler']:
                print(f"  {log}")
            
            print(f"\n[setMetadataOptions] logs: {len(logs['setMetadataOptions'])}")
            for log in logs['setMetadataOptions']:
                print(f"  {log}")
            
            print(f"\n[MetadataFilterBar] logs: {len(logs['metadataFilterBar'])}")
            for log in logs['metadataFilterBar']:
                print(f"  {log}")
            
            print(f"\n[Props Updates] logs: {len(logs['props_updates'])}")
            for log in logs['props_updates']:
                print(f"  {log}")
            
            print(f"\n[Errors] logs: {len(logs['errors'])}")
            for log in logs['errors']:
                print(f"  {log}")
            
            # VERIFICAÇÃO CRÍTICA
            print("\n" + "="*80)
            print("🔍 VERIFICAÇÃO CRÍTICA")
            print("="*80)
            
            if len(logs['requestHandler']) == 0:
                print("❌ PROBLEMA: requestHandler NÃO executou!")
                print("   Causa: ProTable não iniciou request")
            else:
                print("✅ requestHandler executou normalmente")
            
            if len(logs['setMetadataOptions']) == 0:
                print("❌ PROBLEMA: setMetadataOptions NUNCA foi chamado!")
                print("   Causa: Cálculo de options falhou")
            else:
                print("✅ setMetadataOptions foi chamado")
            
            if len(logs['metadataFilterBar']) > 0:
                # Verificar se há mensagens de "0 opções"
                zero_options = [log for log in logs['metadataFilterBar'] if "Opções: 0" in log]
                if zero_options:
                    print(f"⚠️  PROBLEMA: {len(zero_options)} campos com 0 opções")
                    for log in zero_options[:3]:  # Mostrar primeiros 3
                        print(f"     {log}")
                else:
                    print("✅ Todos os campos têm opções")
            
            # Salvar relatório
            report_path = "/home/adrianofante/projetos/Skills-Eye/test_manual_browser_report.json"
            with open(report_path, 'w') as f:
                json.dump(logs, f, indent=2, ensure_ascii=False)
            
            print(f"\n📝 Relatório completo salvo em: {report_path}")
            
            # Manter browser aberto para inspeção manual
            print("\n" + "="*80)
            print("🔍 BROWSER PERMANECERÁ ABERTO PARA INSPEÇÃO MANUAL")
            print("="*80)
            print("Pressione CTRL+C para fechar")
            print("="*80 + "\n")
            
            # Aguardar indefinidamente até user fechar
            await asyncio.sleep(999999)
            
        except KeyboardInterrupt:
            print("\n👋 Fechando browser...")
        except Exception as e:
            print(f"\n❌ ERRO durante execução: {e}")
            import traceback
            traceback.print_exc()
        finally:
            await browser.close()

if __name__ == "__main__":
    print("\n🚀 Iniciando teste com browser real\n")
    asyncio.run(test_manual_browser())
