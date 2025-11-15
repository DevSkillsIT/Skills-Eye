#!/usr/bin/env python3
"""
Teste REAL da página Cache Management usando requests
Verifica se há erros ao acessar a página
"""
import requests
import json

def test_page():
    """Testa a página completa"""
    print("\n" + "="*80)
    print("TESTE FINAL: Acesso Real à Página")
    print("="*80)
    
    session = requests.Session()
    
    # 1. Acessar a página HTML
    print("\n[1] GET http://localhost:8081/cache-management")
    try:
        resp = session.get("http://localhost:8081/cache-management", timeout=5)
        print(f"  Status: {resp.status_code}")
        print(f"  Content-Type: {resp.headers.get('content-type')}")
        
        if resp.status_code == 200:
            html = resp.text
            
            # Verificar se tem conteúdo
            print(f"  HTML Size: {len(html)} bytes")
            
            # Procurar por erros comuns
            if 'Cannot GET' in html:
                print(f"  ✗ ERRO: Rota não encontrada no servidor")
                return False
            
            if '<div id="root"' in html:
                print(f"  ✓ React root div presente")
            else:
                print(f"  ✗ React root div NÃO encontrado!")
                return False
            
            if '</script>' in html:
                print(f"  ✓ Scripts carregados")
            else:
                print(f"  ⚠ Nenhum script encontrado")
            
            # Procurar por título
            if '<title>' in html:
                import re
                title_match = re.search(r'<title>(.*?)</title>', html)
                if title_match:
                    print(f"  ✓ Título: '{title_match.group(1)}'")
            
            print(f"\n  ✓ Página HTML carregada com sucesso!")
            
    except Exception as e:
        print(f"  ✗ ERRO: {e}")
        return False
    
    # 2. Testar chamadas API que o componente faria
    print("\n[2] Testar API calls do componente")
    
    # 2.1 getCacheStats
    print("\n  [2.1] GET /api/v1/cache/stats (via proxy)")
    try:
        resp = session.get("http://localhost:8081/api/v1/cache/stats", timeout=5)
        print(f"    Status: {resp.status_code}")
        
        if resp.status_code == 200:
            data = resp.json()
            print(f"    ✓ Data: {json.dumps(data, indent=6)}")
        else:
            print(f"    ✗ Falhou: {resp.text[:200]}")
            return False
            
    except Exception as e:
        print(f"    ✗ ERRO: {e}")
        return False
    
    # 2.2 getCacheKeys
    print("\n  [2.2] GET /api/v1/cache/keys (via proxy)")
    try:
        resp = session.get("http://localhost:8081/api/v1/cache/keys", timeout=5)
        print(f"    Status: {resp.status_code}")
        
        if resp.status_code == 200:
            keys = resp.json()
            print(f"    ✓ Keys: {len(keys)} chaves")
            if keys:
                print(f"    ✓ Primeiras 3: {keys[:3]}")
        else:
            print(f"    ✗ Falhou: {resp.text[:200]}")
            return False
            
    except Exception as e:
        print(f"    ✗ ERRO: {e}")
        return False
    
    print("\n" + "="*80)
    print("✓ TODOS OS TESTES PASSARAM!")
    print("="*80)
    print("""
CONCLUSÃO:
- Backend: ✓ Funcionando (porta 5000)
- Frontend: ✓ Servindo HTML (porta 8081)
- Proxy: ✓ Funcionando (/api → localhost:5000)
- API Calls: ✓ Todas respondendo corretamente

Se a página ainda não funciona no BROWSER:
1. Abrir http://localhost:8081/cache-management no browser
2. Abrir DevTools (F12)
3. Ir na aba Console - verificar erros JavaScript
4. Ir na aba Network - verificar requisições falhadas

Possíveis causas se falhar:
- Erro de compilação do React (ver console do Vite)
- Erro JavaScript no componente (ver browser console)
- CORS bloqueando requisições (ver network tab)
- Componente não está exportado corretamente
""")
    
    return True


if __name__ == "__main__":
    test_page()
