#!/usr/bin/env python3
"""
Teste ultra-simples do Vite Proxy
Testa se o Vite está redirecionando corretamente /api para localhost:5000
"""
import requests
import time

print("=" * 80)
print("TESTE VITE PROXY - Diagnóstico Simplificado")
print("=" * 80)

# URLs para testar
urls_teste = [
    ("Backend Direto", "http://localhost:5000/api/v1/monitoring/data?category=network-probes"),
    ("Vite Proxy", "http://localhost:8081/api/v1/monitoring/data?category=network-probes"),
    ("Backend Nodes", "http://localhost:5000/api/v1/nodes"),
    ("Vite Proxy Nodes", "http://localhost:8081/api/v1/nodes"),
]

print("\n🔍 Testando endpoints...\n")

for nome, url in urls_teste:
    try:
        print(f"📍 {nome}:")
        print(f"   URL: {url}")
        
        inicio = time.time()
        resp = requests.get(url, timeout=10)
        tempo = (time.time() - inicio) * 1000
        
        print(f"   Status: {resp.status_code}")
        print(f"   Tempo: {tempo:.0f}ms")
        
        # Tenta ver se tem dados
        try:
            data = resp.json()
            if isinstance(data, dict):
                total = data.get('total', 'N/A')
                print(f"   Total registros: {total}")
        except:
            print(f"   Tamanho resposta: {len(resp.content)} bytes")
        
        print()
        
    except requests.exceptions.Timeout:
        print(f"   ❌ TIMEOUT após 10s!\n")
    except requests.exceptions.ConnectionError as e:
        print(f"   ❌ ERRO CONEXÃO: {str(e)[:100]}\n")
    except Exception as e:
        print(f"   ❌ ERRO: {type(e).__name__}: {str(e)[:100]}\n")

print("=" * 80)
print("CONCLUSÃO:")
print("=" * 80)
print("Se 'Vite Proxy' funcionar = Proxy OK")
print("Se 'Vite Proxy' falhar mas 'Backend Direto' funcionar = PROXY QUEBRADO")
print("=" * 80)
