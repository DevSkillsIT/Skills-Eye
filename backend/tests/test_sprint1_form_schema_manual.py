#!/usr/bin/env python3
"""
Testes Manuais para Sprint 1: Form Schema

Executa testes sem pytest (para validar estrutura)
"""

import sys
from pathlib import Path

# Adicionar backend ao path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

def test_imports():
    """Testa se imports funcionam"""
    try:
        from fastapi.testclient import TestClient
        from app import app
        print("✅ Imports OK")
        return True
    except Exception as e:
        print(f"❌ Erro nos imports: {e}")
        return False

def test_endpoint_exists():
    """Testa se endpoint está registrado"""
    try:
        from app import app
        
        # Verificar rotas registradas
        routes = [route.path for route in app.routes]
        form_schema_route = "/api/v1/monitoring-types/form-schema"
        
        if form_schema_route in routes or any("form-schema" in str(route) for route in routes):
            print(f"✅ Endpoint encontrado nas rotas")
            return True
        else:
            print(f"⚠️  Endpoint não encontrado nas rotas. Rotas disponíveis:")
            for route in routes[:10]:
                print(f"   - {route}")
            return False
    except Exception as e:
        print(f"❌ Erro ao verificar rotas: {e}")
        return False

def test_client_creation():
    """Testa criação do TestClient"""
    try:
        from fastapi.testclient import TestClient
        from app import app
        
        client = TestClient(app)
        print("✅ TestClient criado com sucesso")
        return True
    except Exception as e:
        print(f"❌ Erro ao criar TestClient: {e}")
        return False

def main():
    """Executa todos os testes manuais"""
    print("=" * 80)
    print("TESTES MANUAIS - SPRINT 1 FORM SCHEMA")
    print("=" * 80)
    
    results = []
    
    print("\n1. Testando imports...")
    results.append(("Imports", test_imports()))
    
    print("\n2. Testando se endpoint existe...")
    results.append(("Endpoint existe", test_endpoint_exists()))
    
    print("\n3. Testando criação do TestClient...")
    results.append(("TestClient", test_client_creation()))
    
    print("\n" + "=" * 80)
    print("RESUMO")
    print("=" * 80)
    
    for name, result in results:
        status = "✅ PASSOU" if result else "❌ FALHOU"
        print(f"{status}: {name}")
    
    total = len(results)
    passed = sum(1 for _, r in results if r)
    
    print(f"\nTotal: {passed}/{total} testes passaram")
    
    if passed == total:
        print("\n🎉 TODOS OS TESTES MANUAIS PASSARAM!")
        print("\n💡 Agora você pode executar os testes com pytest:")
        print("   cd backend")
        print("   source venv/bin/activate  # ou . venv/bin/activate")
        print("   pip install pytest pytest-asyncio")
        print("   pytest tests/test_sprint1_form_schema.py -v")
        return 0
    else:
        print("\n⚠️  Alguns testes falharam. Corrija antes de executar pytest.")
        return 1

if __name__ == "__main__":
    sys.exit(main())



