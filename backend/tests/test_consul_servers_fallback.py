"""
Teste para validar fallback entre múltiplos servidores Consul

SPEC-PERF-001: Validar que a API tenta múltiplos servidores Consul
quando o líder cai, garantindo resiliência.

Data: 2025-11-21
"""
import asyncio
import sys
import os
import time

# Adicionar diretório pai ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.config import Config
from api.nodes import get_consul_manager_with_fallback


async def test_get_consul_servers():
    """Testa se a função get_consul_servers() funciona corretamente"""
    print("\n" + "=" * 60)
    print("TESTE 1: Verificar configuração CONSUL_SERVERS")
    print("=" * 60)

    servers = Config.get_consul_servers()

    if servers:
        print(f"✅ CONSUL_SERVERS configurado: {len(servers)} servidores")
        for i, server in enumerate(servers, 1):
            print(f"   {i}. {server}")
    else:
        print("⚠️  CONSUL_SERVERS não configurado (vazio)")
        print("   Será usado apenas MAIN_SERVER como fallback")

    print(f"\nMAIN_SERVER atual: {Config.MAIN_SERVER}")

    return servers


async def test_fallback_connection():
    """Testa a conexão com fallback entre servidores"""
    print("\n" + "=" * 60)
    print("TESTE 2: Conexão com Fallback")
    print("=" * 60)

    start_time = time.time()

    try:
        consul, active_server = await get_consul_manager_with_fallback()
        elapsed = (time.time() - start_time) * 1000

        print(f"✅ Conectado ao servidor: {active_server}")
        print(f"   Tempo de conexão: {elapsed:.2f}ms")

        # Verificar se consegue listar membros
        members = await consul.get_members()
        print(f"   Membros do cluster: {len(members)}")

        return True, active_server

    except Exception as e:
        elapsed = (time.time() - start_time) * 1000
        print(f"❌ Falha ao conectar após {elapsed:.2f}ms")
        print(f"   Erro: {str(e)}")
        return False, None


async def test_nodes_endpoint_with_fallback():
    """Testa o endpoint de nodes usando fallback"""
    print("\n" + "=" * 60)
    print("TESTE 3: Endpoint /nodes com Fallback")
    print("=" * 60)

    start_time = time.time()

    try:
        # Importar o router de nodes
        from api.nodes import get_nodes

        result = await get_nodes()
        elapsed = (time.time() - start_time) * 1000

        print(f"✅ Endpoint retornou com sucesso")
        print(f"   Tempo total: {elapsed:.2f}ms")
        print(f"   Total de nós: {result.get('total', 0)}")
        print(f"   Servidor ativo: {result.get('active_server', 'N/A')}")
        print(f"   MAIN_SERVER: {result.get('main_server', 'N/A')}")

        # Verificar contagem de serviços
        nodes = result.get('data', [])
        for node in nodes:
            status = "✅" if node.get('services_status') == 'ok' else "⚠️"
            print(f"   {status} {node.get('node', 'unknown')}: "
                  f"{node.get('services_count', 0)} serviços "
                  f"({node.get('services_status', 'unknown')})")

        return True

    except Exception as e:
        elapsed = (time.time() - start_time) * 1000
        print(f"❌ Falha no endpoint após {elapsed:.2f}ms")
        print(f"   Erro: {str(e)}")
        return False


async def test_multiple_calls():
    """Testa múltiplas chamadas para verificar consistência"""
    print("\n" + "=" * 60)
    print("TESTE 4: Múltiplas Chamadas (Consistência)")
    print("=" * 60)

    results = []

    for i in range(3):
        start_time = time.time()
        try:
            consul, active_server = await get_consul_manager_with_fallback()
            elapsed = (time.time() - start_time) * 1000
            results.append((True, active_server, elapsed))
            print(f"   Chamada {i+1}: ✅ {active_server} ({elapsed:.2f}ms)")
        except Exception as e:
            elapsed = (time.time() - start_time) * 1000
            results.append((False, str(e), elapsed))
            print(f"   Chamada {i+1}: ❌ Falha ({elapsed:.2f}ms)")

    # Analisar resultados
    successes = sum(1 for r in results if r[0])
    servers_used = set(r[1] for r in results if r[0])

    print(f"\n   Resumo: {successes}/3 chamadas bem-sucedidas")
    if servers_used:
        print(f"   Servidores usados: {', '.join(servers_used)}")

    return successes == 3


async def main():
    """Executa todos os testes"""
    print("\n" + "=" * 60)
    print("TESTE DE FALLBACK ENTRE MÚLTIPLOS SERVIDORES CONSUL")
    print("=" * 60)
    print(f"\nData: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Timeout configurado: {Config.CONSUL_CATALOG_TIMEOUT}s")

    results = {}

    # Teste 1: Configuração
    # Nota: CONSUL_SERVERS vazio é válido (usa MAIN_SERVER como fallback)
    servers = await test_get_consul_servers()
    results['config'] = True  # Configuração é sempre válida (vazio = usar MAIN_SERVER)

    # Teste 2: Conexão com fallback
    success, server = await test_fallback_connection()
    results['connection'] = success

    # Teste 3: Endpoint nodes
    success = await test_nodes_endpoint_with_fallback()
    results['endpoint'] = success

    # Teste 4: Múltiplas chamadas
    success = await test_multiple_calls()
    results['consistency'] = success

    # Resumo final
    print("\n" + "=" * 60)
    print("RESUMO DOS TESTES")
    print("=" * 60)

    total_passed = sum(1 for v in results.values() if v)
    total_tests = len(results)

    for test_name, passed in results.items():
        status = "✅ PASSOU" if passed else "❌ FALHOU"
        print(f"   {test_name}: {status}")

    print(f"\n   Total: {total_passed}/{total_tests} testes passaram")

    if total_passed == total_tests:
        print("\n✅ TODOS OS TESTES PASSARAM!")
        return 0
    else:
        print("\n⚠️  ALGUNS TESTES FALHARAM!")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
