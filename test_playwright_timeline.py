#!/usr/bin/env python3
"""
Teste Playwright DETALHADO - Captura TODOS os logs com timestamps
"""
import asyncio
from datetime import datetime
from playwright.async_api import async_playwright

async def test_detailed_logs():
    async with async_playwright() as p:
        browser = await p.firefox.launch(headless=False, slow_mo=500)
        page = await browser.new_page()
        
        # Capturar TODOS os console logs com timestamp
        all_logs = []
        def handle_console(msg):
            timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
            all_logs.append({
                'time': timestamp,
                'type': msg.type,
                'text': msg.text
            })
            # Printar ERROS imediatamente
            if msg.type == 'error':
                print(f"❌ ERRO NO CONSOLE [{timestamp}]: {msg.text}")
        page.on('console', handle_console)
        
        print("🌐 Navegando para network-probes...")
        await page.goto('http://localhost:8081/monitoring/network-probes', wait_until='load', timeout=60000)
        
        print("⏳ Aguardando 3 segundos inicial...")
        await page.wait_for_timeout(3000)
        
        # Tentar trigger para ProTable carregar dados
        print("🖱️  Scrollando página para trigger loading...")
        await page.evaluate('window.scrollTo(0, 500)')
        await page.wait_for_timeout(2000)
        
        # Verificar se tabela apareceu
        table = await page.query_selector('.ant-table, .ant-pro-table')
        if table:
            print("✅ Tabela encontrada!")
        else:
            print("❌ Tabela NÃO encontrada - pode estar falhando")
        
        print("⏳ Aguardando mais 10 segundos para carregar dados...")
        await page.wait_for_timeout(10000)
        
        # Análise DETALHADA do timeline
        print("\n" + "="*80)
        print("📊 TIMELINE COMPLETO - Ordem de execução")
        print("="*80)
        
        # Filtrar logs importantes
        important_keywords = [
            'requestHandler',
            'setMetadataOptions',
            'Props atualizadas',
            'MetadataFilterBar',
            'metadataOptions extraídas',
            'company',
            'provedor'
        ]
        
        for log in all_logs:
            # Se contém alguma palavra-chave importante
            if any(keyword in log['text'] for keyword in important_keywords):
                icon = "🔥" if 'setMetadataOptions' in log['text'] else \
                       "📊" if 'Props' in log['text'] else \
                       "⏱️" if 'PERF' in log['text'] else \
                       "⚠️" if 'SEM OPÇÕES' in log['text'] else \
                       "📋"
                
                # Truncar texto muito longo
                text = log['text'][:150]
                print(f"[{log['time']}] {icon} {text}")
        
        # Análise específica
        print("\n" + "="*80)
        print("🔍 ANÁLISE ESPECÍFICA")
        print("="*80)
        
        # 1. Quando setMetadataOptions foi chamado?
        set_metadata_logs = [log for log in all_logs if 'setMetadataOptions chamado' in log['text']]
        print(f"\n1. setMetadataOptions chamado: {len(set_metadata_logs)} vezes")
        for log in set_metadata_logs:
            print(f"   [{log['time']}] {log['text'][:100]}")
        
        # 2. Quando Props foram atualizadas?
        props_logs = [log for log in all_logs if 'Props atualizadas' in log['text']]
        print(f"\n2. Props atualizadas: {len(props_logs)} vezes")
        for log in props_logs:
            print(f"   [{log['time']}] {log['text']}")
        
        # 3. Quantas vezes campos foram verificados SEM OPÇÕES?
        sem_opcoes_logs = [log for log in all_logs if 'SEM OPÇÕES' in log['text']]
        print(f"\n3. Campos SEM OPÇÕES: {len(sem_opcoes_logs)} vezes")
        
        # Contar company e provedor especificamente
        company_sem_opcoes = [log for log in sem_opcoes_logs if 'company' in log['text']]
        provedor_sem_opcoes = [log for log in sem_opcoes_logs if 'provedor' in log['text']]
        print(f"   - company SEM OPÇÕES: {len(company_sem_opcoes)} vezes")
        print(f"   - provedor SEM OPÇÕES: {len(provedor_sem_opcoes)} vezes")
        
        # 4. metadataOptions extraídas
        metadata_extracted = [log for log in all_logs if 'metadataOptions extraídas' in log['text']]
        print(f"\n4. metadataOptions extraídas: {len(metadata_extracted)} vezes")
        for log in metadata_extracted:
            print(f"   [{log['time']}]")
        
        # DIAGNÓSTICO
        print("\n" + "="*80)
        print("🎯 DIAGNÓSTICO")
        print("="*80)
        
        if len(set_metadata_logs) == 0:
            print("\n❌ PROBLEMA CRÍTICO:")
            print("   setMetadataOptions NUNCA foi chamado!")
            print("   → requestHandler pode não estar executando")
            print("   → Ou código está falhando antes de chegar no setMetadataOptions")
        elif len(props_logs) == 0:
            print("\n❌ PROBLEMA CRÍTICO:")
            print("   Props NUNCA foram atualizadas no MetadataFilterBar!")
            print("   → Component não está re-renderizando")
        elif len(set_metadata_logs) > 0 and len(props_logs) > 0:
            # Comparar timestamps
            last_set = set_metadata_logs[-1]['time']
            last_props = props_logs[-1]['time']
            print(f"\n📊 Timing:")
            print(f"   Último setMetadataOptions: {last_set}")
            print(f"   Última Props atualizada: {last_props}")
            
            if 'options={}' in props_logs[-1]['text']:
                print(f"\n❌ PROBLEMA:")
                print(f"   Props chegam com options={{}} VAZIO")
                print(f"   → setMetadataOptions foi chamado mas state não propagou")
                print(f"   → Possível problema de closure/referência")
        
        # Screenshot
        await page.screenshot(path='screenshot_timeline.png', full_page=True)
        print(f"\n📸 Screenshot: screenshot_timeline.png")
        
        print("\n⏸️  Browser aberto por 15s para inspeção manual...")
        await page.wait_for_timeout(15000)
        
        await browser.close()

if __name__ == '__main__':
    asyncio.run(test_detailed_logs())
