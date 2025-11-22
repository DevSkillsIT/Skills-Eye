#!/usr/bin/env python3
"""
Teste Completo: Todos os Cenários de Persistência de Metadata Fields

Este script testa TODOS os cenários críticos:
1. Race Condition (editar durante prewarm)
2. Estrutura Desatualizada (campos novos do Prometheus)
3. KV Apagado e Restaurado (backup automático)

USO:
    python test_all_persistence_scenarios.py
"""

import asyncio
import sys
import os
from pathlib import Path

backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

import httpx
from datetime import datetime
import time

API_URL = os.getenv("API_URL", "http://localhost:5000/api/v1")
CONSUL_URL = os.getenv("CONSUL_URL", "http://172.16.1.26:8500")
CONSUL_TOKEN = os.getenv("CONSUL_TOKEN", "")

GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
CYAN = "\033[96m"
RESET = "\033[0m"
BOLD = "\033[1m"

class TestResult:
    def __init__(self, name: str):
        self.name = name
        self.passed = False
        self.error = None
        self.details = []

def print_header(text: str):
    print(f"\n{BOLD}{BLUE}{'='*80}{RESET}")
    print(f"{BOLD}{BLUE}{text}{RESET}")
    print(f"{BOLD}{BLUE}{'='*80}{RESET}\n")

def print_success(text: str):
    print(f"{GREEN}✅ {text}{RESET}")

def print_error(text: str):
    print(f"{RED}❌ {text}{RESET}")

def print_warning(text: str):
    print(f"{YELLOW}⚠️  {text}{RESET}")

def print_info(text: str):
    print(f"{CYAN}ℹ️  {text}{RESET}")

async def test_scenario_1_race_condition(client: httpx.AsyncClient) -> TestResult:
    """Cenário 1: Race Condition - Editar campo durante prewarm"""
    result = TestResult("Cenário 1: Race Condition")
    
    try:
        print_info("Aplicando customizações no campo 'company'...")
        
        # Aplicar customizações
        test_values = {
            'display_name': f"🏢 RACE TEST {datetime.now().strftime('%H%M%S')}",
            'category': 'race_test_category',
            'show_in_services': False,
            'required': True,
        }
        
        response = await client.patch(
            f"{API_URL}/metadata-fields/company",
            json=test_values
        )
        
        if response.status_code != 200:
            result.error = f"Erro ao aplicar customizações: {response.status_code}"
            return result
        
        print_success("Customizações aplicadas")
        
        # Aguardar 1 segundo (simular prewarm rodando)
        print_info("Aguardando 1 segundo (simulando prewarm)...")
        await asyncio.sleep(1)
        
        # Verificar se customizações persistiram
        print_info("Verificando se customizações persistiram...")
        response = await client.get(f"{API_URL}/metadata-fields/company")
        
        if response.status_code != 200:
            result.error = f"Erro ao buscar campo: {response.status_code}"
            return result
        
        field = response.json().get('field', {})
        
        all_ok = True
        for key, expected_value in test_values.items():
            actual_value = field.get(key)
            if actual_value != expected_value:
                result.details.append(f"{key}: esperado {expected_value}, obtido {actual_value}")
                all_ok = False
        
        if all_ok:
            result.passed = True
            print_success("Customizações preservadas após race condition!")
        else:
            result.error = "Customizações não foram preservadas"
            result.details.append("Race condition detectada - prewarm sobrescreveu customizações")
        
    except Exception as e:
        result.error = str(e)
    
    return result

async def test_scenario_2_structure_update(client: httpx.AsyncClient) -> TestResult:
    """Cenário 2: Estrutura Desatualizada - Campos novos do Prometheus"""
    result = TestResult("Cenário 2: Estrutura Desatualizada")
    
    try:
        print_info("Aplicando customizações...")
        
        # Aplicar customizações
        test_values = {
            'display_name': f"🏢 STRUCTURE TEST {datetime.now().strftime('%H%M%S')}",
            'category': 'structure_test',
        }
        
        response = await client.patch(
            f"{API_URL}/metadata-fields/company",
            json=test_values
        )
        
        if response.status_code != 200:
            result.error = f"Erro ao aplicar customizações: {response.status_code}"
            return result
        
        print_success("Customizações aplicadas")
        
        # Simular force-extract (atualiza estrutura do Prometheus)
        print_info("Executando force-extract (simula atualização de estrutura)...")
        response = await client.post(f"{API_URL}/metadata-fields/force-extract")
        
        if response.status_code != 200:
            result.error = f"Erro ao executar force-extract: {response.status_code}"
            return result
        
        print_success("Force-extract concluído")
        
        # Aguardar processamento
        await asyncio.sleep(2)
        
        # Verificar se customizações persistiram
        print_info("Verificando se customizações persistiram após atualização de estrutura...")
        response = await client.get(f"{API_URL}/metadata-fields/company")
        
        if response.status_code != 200:
            result.error = f"Erro ao buscar campo: {response.status_code}"
            return result
        
        field = response.json().get('field', {})
        
        all_ok = True
        for key, expected_value in test_values.items():
            actual_value = field.get(key)
            if actual_value != expected_value:
                result.details.append(f"{key}: esperado {expected_value}, obtido {actual_value}")
                all_ok = False
        
        if all_ok:
            result.passed = True
            print_success("Customizações preservadas após atualização de estrutura!")
        else:
            result.error = "Customizações não foram preservadas após atualização de estrutura"
        
    except Exception as e:
        result.error = str(e)
    
    return result

async def test_scenario_3_kv_deleted_restored(client: httpx.AsyncClient) -> TestResult:
    """Cenário 3: KV Apagado e Restaurado - Backup automático"""
    result = TestResult("Cenário 3: KV Apagado e Restaurado")
    
    try:
        print_info("Aplicando customizações...")
        
        # Aplicar customizações
        test_values = {
            'display_name': f"🏢 BACKUP TEST {datetime.now().strftime('%H%M%S')}",
            'category': 'backup_test',
            'show_in_services': False,
            'required': True,
        }
        
        response = await client.patch(
            f"{API_URL}/metadata-fields/company",
            json=test_values
        )
        
        if response.status_code != 200:
            result.error = f"Erro ao aplicar customizações: {response.status_code}"
            return result
        
        print_success("Customizações aplicadas")
        
        # Aguardar backup ser criado
        await asyncio.sleep(1)
        
        # Verificar que backup foi criado
        print_info("Verificando se backup foi criado...")
        from core.metadata_fields_backup import get_backup_manager
        backup_manager = get_backup_manager()
        backup_info = await backup_manager.get_backup_info()
        
        if not backup_info.get('has_backup'):
            result.error = "Backup não foi criado automaticamente"
            return result
        
        print_success(f"Backup criado: {backup_info.get('backup_timestamp')}")
        
        # Apagar KV principal
        print_warning("Apagando KV principal...")
        headers = {}
        if CONSUL_TOKEN:
            headers['X-Consul-Token'] = CONSUL_TOKEN
        
        delete_response = await client.delete(
            f"{CONSUL_URL}/v1/kv/skills/eye/metadata/fields",
            headers=headers
        )
        
        if delete_response.status_code not in [200, 404]:
            result.error = f"Erro ao apagar KV: {delete_response.status_code}"
            return result
        
        print_success("KV principal apagado")
        
        # Aguardar um pouco
        await asyncio.sleep(1)
        
        # Tentar ler campos (deve restaurar do backup automaticamente)
        print_info("Tentando ler campos (deve restaurar do backup automaticamente)...")
        response = await client.get(f"{API_URL}/metadata-fields/company")
        
        if response.status_code != 200:
            result.error = f"Erro ao buscar campo após apagar KV: {response.status_code}"
            return result
        
        field = response.json().get('field', {})
        
        # Verificar se customizações foram restauradas
        all_ok = True
        for key, expected_value in test_values.items():
            actual_value = field.get(key)
            if actual_value != expected_value:
                result.details.append(f"{key}: esperado {expected_value}, obtido {actual_value}")
                all_ok = False
        
        if all_ok:
            result.passed = True
            print_success("Customizações restauradas do backup automaticamente!")
        else:
            result.error = "Customizações não foram restauradas do backup"
            result.details.append("Sistema não restaurou automaticamente do backup")
        
    except Exception as e:
        result.error = str(e)
        import traceback
        result.details.append(traceback.format_exc())
    
    return result

async def run_all_tests():
    """Executa todos os testes"""
    print_header("TESTE COMPLETO: TODOS OS CENÁRIOS DE PERSISTÊNCIA")
    
    results = []
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        # Verificar se backend está rodando
        try:
            response = await client.get(f"{API_URL}/metadata-fields/")
            if response.status_code != 200:
                print_error(f"Backend não está respondendo: {response.status_code}")
                return False
        except Exception as e:
            print_error(f"Erro ao conectar ao backend: {e}")
            print_warning("Certifique-se de que o backend está rodando em http://localhost:5000")
            return False
        
        print_success("Backend está rodando\n")
        
        # Teste 1: Race Condition
        print_header("TESTE 1: RACE CONDITION")
        result1 = await test_scenario_1_race_condition(client)
        results.append(result1)
        
        # Teste 2: Estrutura Desatualizada
        print_header("TESTE 2: ESTRUTURA DESATUALIZADA")
        result2 = await test_scenario_2_structure_update(client)
        results.append(result2)
        
        # Teste 3: KV Apagado e Restaurado
        print_header("TESTE 3: KV APAGADO E RESTAURADO")
        result3 = await test_scenario_3_kv_deleted_restored(client)
        results.append(result3)
    
    # Relatório final
    print_header("RELATÓRIO FINAL")
    
    passed = sum(1 for r in results if r.passed)
    failed = len(results) - passed
    
    for result in results:
        if result.passed:
            print_success(f"{result.name}: PASSOU")
        else:
            print_error(f"{result.name}: FALHOU")
            if result.error:
                print_error(f"  Erro: {result.error}")
            if result.details:
                for detail in result.details:
                    print_warning(f"  - {detail}")
    
    print(f"\n{BOLD}Estatísticas:{RESET}")
    print(f"  Total: {len(results)}")
    print(f"  {GREEN}Passou: {passed}{RESET}")
    print(f"  {RED}Falhou: {failed}{RESET}")
    
    if failed == 0:
        print(f"\n{BOLD}{GREEN}{'='*80}{RESET}")
        print(f"{BOLD}{GREEN}🎉 TODOS OS TESTES PASSARAM!{RESET}")
        print(f"{BOLD}{GREEN}{'='*80}{RESET}\n")
        return True
    else:
        print(f"\n{BOLD}{RED}{'='*80}{RESET}")
        print(f"{BOLD}{RED}❌ ALGUNS TESTES FALHARAM!{RESET}")
        print(f"{BOLD}{RED}{'='*80}{RESET}\n")
        return False

if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)

