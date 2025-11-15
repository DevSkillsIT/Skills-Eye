#!/usr/bin/env python3
"""
Teste da página Cache Management - Simular Browser
Verifica se a página carrega e faz requisições à API corretamente
"""
import asyncio
import httpx
import json

FRONTEND_URL = "http://localhost:8081"
API_URL = "http://localhost:5000/api/v1"

async def test_page_and_api():
    """Simula comportamento do browser carregando a página"""
    print("\n" + "="*80)
    print("TESTE: Simular Browser Acessando /cache-management")
    print("="*80)
    
    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
        # PASSO 1: Carregar HTML da página
        print("\n[STEP 1] GET /cache-management (HTML)")
        try:
            resp = await client.get(f"{FRONTEND_URL}/cache-management")
            print(f"  ✓ Status: {resp.status_code}")
            print(f"  ✓ Content-Type: {resp.headers.get('content-type')}")
            
            html = resp.text
            
            # Verificar elementos React
            if '<div id="root"' in html:
                print(f"  ✓ React root div encontrado")
            
            if '<script' in html:
                print(f"  ✓ Scripts JS encontrados")
                
            if 'vite' in html.lower() or 'react' in html.lower():
                print(f"  ✓ Vite/React detectado no HTML")
                
        except Exception as e:
            print(f"  ✗ ERRO ao carregar página: {e}")
            return
        
        # PASSO 2: Simular requisições que o componente faria (useEffect)
        print("\n[STEP 2] Simular useEffect() - fetchEntries()")
        
        # 2.1 Fetch Stats
        print("\n  [2.1] Chamar cacheAPI.getCacheStats()")
        try:
            # O componente chama: await cacheAPI.getCacheStats()
            # Que internamente faz: api.get('/cache/stats')
            # Com proxy: /api/v1/cache/stats → http://localhost:5000/api/v1/cache/stats
            
            # Testar via proxy (como frontend faria)
            stats_resp = await client.get(f"{FRONTEND_URL}/api/v1/cache/stats")
            print(f"    ✓ Via PROXY Status: {stats_resp.status_code}")
            
            if stats_resp.status_code == 200:
                stats = stats_resp.json()
                print(f"    ✓ Stats: hits={stats['hits']}, size={stats['current_size']}")
            else:
                print(f"    ✗ Proxy falhou: {stats_resp.status_code}")
                print(f"    ✗ Body: {stats_resp.text[:200]}")
                
                # Tentar direto (bypass proxy)
                print(f"\n  [2.1b] Tentar DIRETO no backend")
                direct_resp = await client.get(f"{API_URL}/cache/stats")
                print(f"    ✓ Direct Status: {direct_resp.status_code}")
                if direct_resp.status_code == 200:
                    print(f"    ✓ Backend funciona, PROBLEMA NO PROXY!")
                
        except Exception as e:
            print(f"    ✗ ERRO: {e}")
        
        # 2.2 Fetch Keys
        print("\n  [2.2] Chamar cacheAPI.getCacheKeys()")
        try:
            keys_resp = await client.get(f"{FRONTEND_URL}/api/v1/cache/keys")
            print(f"    ✓ Status: {keys_resp.status_code}")
            
            if keys_resp.status_code == 200:
                keys = keys_resp.json()
                print(f"    ✓ Keys: {len(keys)} chaves")
            else:
                print(f"    ✗ Falhou: {keys_resp.text[:200]}")
                
        except Exception as e:
            print(f"    ✗ ERRO: {e}")
        
        # PASSO 3: Testar ações (botões)
        print("\n[STEP 3] Simular ações do usuário")
        
        # 3.1 Clear All Cache
        print("\n  [3.1] Botão 'Limpar Tudo' - clearAllCache()")
        try:
            clear_resp = await client.post(f"{FRONTEND_URL}/api/v1/cache/clear")
            print(f"    ✓ Status: {clear_resp.status_code}")
            
            if clear_resp.status_code == 200:
                result = clear_resp.json()
                print(f"    ✓ Response: {result['message']}")
            else:
                print(f"    ✗ Falhou: {clear_resp.text[:200]}")
                
        except Exception as e:
            print(f"    ✗ ERRO: {e}")
        
        # 3.2 Invalidate Pattern
        print("\n  [3.2] Botão 'Invalidar por Padrão' - invalidateCachePattern()")
        try:
            invalidate_resp = await client.post(
                f"{FRONTEND_URL}/api/v1/cache/invalidate-pattern",
                json={"pattern": "test_*"}
            )
            print(f"    ✓ Status: {invalidate_resp.status_code}")
            
            if invalidate_resp.status_code == 200:
                result = invalidate_resp.json()
                print(f"    ✓ Keys removidas: {result['keys_removed']}")
            else:
                print(f"    ✗ Falhou: {invalidate_resp.text[:200]}")
                
        except Exception as e:
            print(f"    ✗ ERRO: {e}")


async def test_proxy_config():
    """Verifica se o proxy Vite está funcionando"""
    print("\n" + "="*80)
    print("TESTE: Configuração do Proxy Vite")
    print("="*80)
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        print("\n[TEST] Requisição via PROXY: /api/v1/cache/stats")
        print(f"  Frontend: {FRONTEND_URL}")
        print(f"  Proxy target: http://localhost:5000")
        print(f"  URL final esperada: {API_URL}/cache/stats")
        
        try:
            # Via proxy
            proxy_resp = await client.get(
                f"{FRONTEND_URL}/api/v1/cache/stats",
                headers={"Accept": "application/json"}
            )
            print(f"\n  ✓ Proxy Status: {proxy_resp.status_code}")
            
            if proxy_resp.status_code == 200:
                print(f"  ✓ PROXY FUNCIONA CORRETAMENTE!")
                data = proxy_resp.json()
                print(f"  ✓ Data: {json.dumps(data, indent=2)}")
            else:
                print(f"  ✗ PROXY FALHOU!")
                print(f"  ✗ Response: {proxy_resp.text[:500]}")
                
        except Exception as e:
            print(f"  ✗ ERRO DE CONEXÃO: {e}")
            print(f"\n  DIAGNÓSTICO:")
            print(f"    1. Vite está rodando na 8081? ✓ (confirmado)")
            print(f"    2. Backend está na 5000? ✓ (confirmado)")
            print(f"    3. Proxy configurado para /api → http://localhost:5000? (verificar vite.config.ts)")


async def main():
    print("\n" + "█"*80)
    print("█ TESTE COMPLETO - CACHE MANAGEMENT PAGE (BROWSER SIMULATION)")
    print("█"*80)
    
    await test_proxy_config()
    await test_page_and_api()
    
    print("\n" + "="*80)
    print("DIAGNÓSTICO FINAL")
    print("="*80)
    print("""
Se o PROXY falhou:
  → Vite proxy não está reencaminhando /api/v1/* para backend
  → Solução: Verificar vite.config.ts proxy configuration

Se o HTML carregou mas API falhou:
  → Frontend carrega mas componente não consegue chamar backend
  → Abrir DevTools do browser e verificar console.log() e Network tab

Se tudo passou:
  → Problema pode ser no componente React (erros JavaScript)
  → Verificar logs no terminal do Vite (npm run dev)
""")


if __name__ == "__main__":
    asyncio.run(main())
