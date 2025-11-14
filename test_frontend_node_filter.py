#!/usr/bin/env python3
"""
Teste automatizado: Filtro de nós no frontend
Usa Playwright para testar comportamento real no browser
"""

import asyncio
import sys
from playwright.async_api import async_playwright

async def test_node_filter():
    print("=" * 80)
    print("TESTE AUTOMATIZADO: Filtro de Nós no Frontend")
    print("=" * 80)
    
    async with async_playwright() as p:
        # Abrir browser
        print("\n[1] Iniciando browser...")
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        
        # Navegar para página de network-probes
        url = "http://localhost:8081/monitoring/network-probes"
        print(f"[2] Abrindo página: {url}")
        
        try:
            await page.goto(url, wait_until="networkidle", timeout=30000)
            print("✅ Página carregada")
        except Exception as e:
            print(f"❌ ERRO ao carregar página: {e}")
            await browser.close()
            return False
        
        # Aguardar carregamento da tabela
        print("\n[3] Aguardando carregamento da tabela...")
        try:
            await page.wait_for_selector('.ant-pro-table', timeout=10000)
            print("✅ Tabela carregada")
        except:
            print("⚠️ Tabela não encontrada, continuando...")
        
        await asyncio.sleep(2)  # Aguardar processamento
        
        # TESTE 1: Verificar total com "Todos os nós"
        print("\n[4] TESTE 1: Verificando 'Todos os nós'...")
        
        # Verificar se selector de nó existe
        node_selector = page.locator('.ant-select').first
        if await node_selector.count() > 0:
            print("✅ NodeSelector encontrado")
            
            # Pegar texto do seletor (deve estar em "Todos os nós")
            selector_text = await node_selector.inner_text()
            print(f"   Valor atual: {selector_text[:50]}...")
        else:
            print("⚠️ NodeSelector não encontrado")
        
        # Contar linhas da tabela
        rows = page.locator('.ant-table-tbody tr:not(.ant-table-placeholder)')
        row_count_all = await rows.count()
        print(f"   Linhas na tabela: {row_count_all}")
        
        expected_total = 155
        if row_count_all == expected_total:
            print(f"   ✅ CORRETO: {row_count_all} linhas (esperado: {expected_total})")
        else:
            print(f"   ⚠️ DIVERGÊNCIA: {row_count_all} linhas (esperado: {expected_total})")
        
        # TESTE 2: Filtrar por nó específico (172.16.1.26 - Palmas - 133 itens)
        print("\n[5] TESTE 2: Filtrando por nó 172.16.1.26 (Palmas)...")
        
        try:
            # Clicar no selector de nó
            await node_selector.click()
            await asyncio.sleep(1)
            
            # Procurar opção com IP 172.16.1.26
            option = page.locator('.ant-select-item').filter(has_text='172.16.1.26')
            
            if await option.count() > 0:
                print("✅ Opção encontrada")
                await option.click()
                await asyncio.sleep(2)  # Aguardar filtro aplicar
                
                # Contar linhas após filtro
                row_count_palmas = await rows.count()
                print(f"   Linhas após filtro: {row_count_palmas}")
                
                expected_palmas = 133
                if row_count_palmas == expected_palmas:
                    print(f"   ✅ CORRETO: {row_count_palmas} linhas (esperado: {expected_palmas})")
                else:
                    print(f"   ❌ ERRO: {row_count_palmas} linhas (esperado: {expected_palmas})")
            else:
                print("   ⚠️ Opção com IP 172.16.1.26 não encontrada")
                
                # Listar opções disponíveis
                all_options = page.locator('.ant-select-item')
                option_count = await all_options.count()
                print(f"   Opções disponíveis: {option_count}")
                
                for i in range(min(option_count, 5)):
                    opt_text = await all_options.nth(i).inner_text()
                    print(f"      - {opt_text[:60]}")
        except Exception as e:
            print(f"   ❌ ERRO ao filtrar: {e}")
        
        # TESTE 3: Filtrar por outro nó (11.144.0.21 - DTC - 14 itens)
        print("\n[6] TESTE 3: Filtrando por nó 11.144.0.21 (DTC)...")
        
        try:
            await node_selector.click()
            await asyncio.sleep(1)
            
            option = page.locator('.ant-select-item').filter(has_text='11.144.0.21')
            
            if await option.count() > 0:
                print("✅ Opção encontrada")
                await option.click()
                await asyncio.sleep(2)
                
                row_count_dtc = await rows.count()
                print(f"   Linhas após filtro: {row_count_dtc}")
                
                expected_dtc = 14
                if row_count_dtc == expected_dtc:
                    print(f"   ✅ CORRETO: {row_count_dtc} linhas (esperado: {expected_dtc})")
                else:
                    print(f"   ❌ ERRO: {row_count_dtc} linhas (esperado: {expected_dtc})")
            else:
                print("   ⚠️ Opção com IP 11.144.0.21 não encontrada")
        except Exception as e:
            print(f"   ❌ ERRO ao filtrar: {e}")
        
        # TESTE 4: Voltar para "Todos os nós"
        print("\n[7] TESTE 4: Voltando para 'Todos os nós'...")
        
        try:
            await node_selector.click()
            await asyncio.sleep(1)
            
            option = page.locator('.ant-select-item').filter(has_text='Todos os nós')
            
            if await option.count() > 0:
                print("✅ Opção encontrada")
                await option.click()
                await asyncio.sleep(2)
                
                row_count_final = await rows.count()
                print(f"   Linhas após voltar: {row_count_final}")
                
                if row_count_final == expected_total:
                    print(f"   ✅ CORRETO: {row_count_final} linhas (esperado: {expected_total})")
                else:
                    print(f"   ⚠️ DIVERGÊNCIA: {row_count_final} linhas (esperado: {expected_total})")
            else:
                print("   ⚠️ Opção 'Todos os nós' não encontrada")
        except Exception as e:
            print(f"   ❌ ERRO: {e}")
        
        # Screenshot para debug
        print("\n[8] Salvando screenshot...")
        await page.screenshot(path='/tmp/node_filter_test.png')
        print("✅ Screenshot salvo: /tmp/node_filter_test.png")
        
        await browser.close()
        
        print("\n" + "=" * 80)
        print("TESTE CONCLUÍDO")
        print("=" * 80)
        
        return True

if __name__ == '__main__':
    try:
        asyncio.run(test_node_filter())
    except KeyboardInterrupt:
        print("\n⚠️ Teste interrompido pelo usuário")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERRO FATAL: {e}")
        sys.exit(1)
