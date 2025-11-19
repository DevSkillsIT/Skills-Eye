#!/usr/bin/env python3
"""
Script de Teste - Cache Management Page
Testa se a página está carregando corretamente e fazendo chamadas à API
"""
import asyncio
import httpx
import json
from datetime import datetime

BACKEND_URL = "http://localhost:8081/api/v1"
FRONTEND_URL = "http://localhost:5173"

async def test_backend_endpoints():
    """Testa todos os endpoints de cache do backend"""
    print("\n" + "="*80)
    print("TESTE 1: ENDPOINTS DO BACKEND")
    print("="*80)
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        # 1. GET /cache/stats
        print("\n[1/6] GET /cache/stats")
        try:
            resp = await client.get(f"{BACKEND_URL}/cache/stats")
            print(f"  ✓ Status: {resp.status_code}")
            if resp.status_code == 200:
                data = resp.json()
                print(f"  ✓ Hits: {data['hits']}, Misses: {data['misses']}, Size: {data['current_size']}")
        except Exception as e:
            print(f"  ✗ ERRO: {e}")
        
        # 2. GET /cache/keys
        print("\n[2/6] GET /cache/keys")
        try:
            resp = await client.get(f"{BACKEND_URL}/cache/keys")
            print(f"  ✓ Status: {resp.status_code}")
            if resp.status_code == 200:
                keys = resp.json()
                print(f"  ✓ Total keys: {len(keys)}")
                if keys:
                    print(f"  ✓ Primeiras 3 chaves: {keys[:3]}")
        except Exception as e:
            print(f"  ✗ ERRO: {e}")
        
        # 3. POST /cache/invalidate
        print("\n[3/6] POST /cache/invalidate")
        try:
            resp = await client.post(
                f"{BACKEND_URL}/cache/invalidate",
                json={"key": "test_key_does_not_exist"}
            )
            print(f"  ✓ Status: {resp.status_code}")
            if resp.status_code == 200:
                data = resp.json()
                print(f"  ✓ Response: {data['message']}")
        except Exception as e:
            print(f"  ✗ ERRO: {e}")
        
        # 4. POST /cache/invalidate-pattern
        print("\n[4/6] POST /cache/invalidate-pattern")
        try:
            resp = await client.post(
                f"{BACKEND_URL}/cache/invalidate-pattern",
                json={"pattern": "test_*"}
            )
            print(f"  ✓ Status: {resp.status_code}")
            if resp.status_code == 200:
                data = resp.json()
                print(f"  ✓ Keys removed: {data['keys_removed']}")
        except Exception as e:
            print(f"  ✗ ERRO: {e}")
        
        # 5. GET /cache/entry/{key}
        print("\n[5/6] GET /cache/entry/non_existent")
        try:
            resp = await client.get(f"{BACKEND_URL}/cache/entry/non_existent")
            print(f"  ✓ Status: {resp.status_code}")
            if resp.status_code == 404:
                print(f"  ✓ Corretamente retornou 404 para chave inexistente")
        except Exception as e:
            print(f"  ✗ ERRO: {e}")
        
        # 6. POST /cache/clear
        print("\n[6/6] POST /cache/clear")
        try:
            resp = await client.post(f"{BACKEND_URL}/cache/clear")
            print(f"  ✓ Status: {resp.status_code}")
            if resp.status_code == 200:
                data = resp.json()
                print(f"  ✓ Response: {data['message']}")
        except Exception as e:
            print(f"  ✗ ERRO: {e}")


async def test_frontend_route():
    """Testa se a rota frontend está acessível"""
    print("\n" + "="*80)
    print("TESTE 2: ROTA FRONTEND")
    print("="*80)
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        print("\n[1/2] GET /cache-management")
        try:
            resp = await client.get(f"{FRONTEND_URL}/cache-management")
            print(f"  ✓ Status: {resp.status_code}")
            print(f"  ✓ Content-Type: {resp.headers.get('content-type')}")
            
            if resp.status_code == 200:
                content = resp.text
                # Verificar se HTML contém elementos esperados
                if 'id="root"' in content or 'div' in content:
                    print(f"  ✓ HTML válido retornado")
                    
                    # Verificar se tem scripts do React
                    if 'react' in content.lower() or 'vite' in content.lower() or 'script' in content:
                        print(f"  ✓ Scripts React/Vite encontrados")
                    else:
                        print(f"  ⚠ AVISO: Scripts React não encontrados no HTML")
                else:
                    print(f"  ✗ HTML retornado está vazio ou inválido")
                    print(f"  ✗ Primeiros 200 chars: {content[:200]}")
            else:
                print(f"  ✗ Status inesperado: {resp.status_code}")
                
        except Exception as e:
            print(f"  ✗ ERRO: {e}")


async def test_cors():
    """Testa se CORS está configurado corretamente"""
    print("\n" + "="*80)
    print("TESTE 3: CORS CONFIGURATION")
    print("="*80)
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        print("\n[1/1] OPTIONS /cache/stats (CORS preflight)")
        try:
            resp = await client.options(
                f"{BACKEND_URL}/cache/stats",
                headers={
                    "Origin": "http://localhost:5173",
                    "Access-Control-Request-Method": "GET"
                }
            )
            print(f"  ✓ Status: {resp.status_code}")
            
            allow_origin = resp.headers.get('access-control-allow-origin')
            allow_methods = resp.headers.get('access-control-allow-methods')
            
            if allow_origin:
                print(f"  ✓ Access-Control-Allow-Origin: {allow_origin}")
            else:
                print(f"  ⚠ CORS não configurado (pode causar problemas)")
            
            if allow_methods:
                print(f"  ✓ Access-Control-Allow-Methods: {allow_methods}")
                
        except Exception as e:
            print(f"  ✗ ERRO: {e}")


async def test_integration():
    """Simula fluxo completo da página"""
    print("\n" + "="*80)
    print("TESTE 4: INTEGRAÇÃO COMPLETA (Simular comportamento da página)")
    print("="*80)
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        # Simular useEffect inicial da página
        print("\n[STEP 1] useEffect - Fetch initial data")
        
        try:
            # 1. Fetch stats
            stats_resp = await client.get(f"{BACKEND_URL}/cache/stats")
            stats = stats_resp.json()
            print(f"  ✓ Stats carregados: {stats['current_size']} entradas")
            
            # 2. Fetch keys
            keys_resp = await client.get(f"{BACKEND_URL}/cache/keys")
            keys = keys_resp.json()
            print(f"  ✓ Keys carregados: {len(keys)} chaves")
            
            # 3. Fetch entries details (paralelo)
            if keys:
                print(f"\n[STEP 2] Fetch entry details (primeiras 3)")
                for i, key in enumerate(keys[:3]):
                    try:
                        entry_resp = await client.get(
                            f"{BACKEND_URL}/cache/entry/{key}"
                        )
                        if entry_resp.status_code == 200:
                            entry = entry_resp.json()
                            print(f"  ✓ Entry {i+1}: {key[:50]}... (age: {entry.get('age_seconds', 0):.1f}s)")
                    except Exception as e:
                        print(f"  ✗ Entry {i+1} ERRO: {e}")
            else:
                print(f"\n[STEP 2] SKIP - Nenhuma chave no cache")
            
            print(f"\n✓ Integração completa SUCESSO!")
            
        except Exception as e:
            print(f"  ✗ Integração FALHOU: {e}")


async def main():
    """Executa todos os testes"""
    print("\n")
    print("█" * 80)
    print("█ TESTE COMPLETO - CACHE MANAGEMENT PAGE")
    print("█ Data: " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("█" * 80)
    
    await test_backend_endpoints()
    await test_frontend_route()
    await test_cors()
    await test_integration()
    
    print("\n" + "="*80)
    print("CONCLUSÃO")
    print("="*80)
    print("\n1. Se todos os testes do BACKEND passaram: ✓ API está OK")
    print("2. Se rota FRONTEND retornou HTML vazio: ✗ Problema no React Router ou build")
    print("3. Se CORS não está configurado: ⚠ Adicionar configuração CORS no FastAPI")
    print("4. Se INTEGRAÇÃO falhou: ✗ Verificar logs do browser console\n")


if __name__ == "__main__":
    asyncio.run(main())
