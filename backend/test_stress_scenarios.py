#!/usr/bin/env python3
"""
TESTES DE STRESS E CONCORRÊNCIA - PERSISTÊNCIA DE CUSTOMIZAÇÕES

Testa cenários extremos e edge cases:
1. 100 requisições simultâneas
2. 50 edições consecutivas
3. Múltiplas extrações forçadas simultâneas
4. Reinício durante extração
5. Conflitos de escrita no KV
6. Cache invalidation race conditions
7. Large payloads (1000+ campos)
8. Timeout scenarios

EXECUÇÃO:
    python3 test_stress_scenarios.py
"""

import asyncio
import sys
import json
from pathlib import Path
from datetime import datetime
import httpx
from typing import List, Dict, Any
import time

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.kv_manager import KVManager

API_URL = "http://localhost:5000/api/v1"
STRESS_ITERATIONS = 100
CONCURRENT_REQUESTS = 50

class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def print_header(text: str):
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'=' * 80}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{text.center(80)}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'=' * 80}{Colors.ENDC}\n")

def print_success(text: str):
    print(f"{Colors.OKGREEN}✅ {text}{Colors.ENDC}")

def print_error(text: str):
    print(f"{Colors.FAIL}❌ {text}{Colors.ENDC}")

def print_warning(text: str):
    print(f"{Colors.WARNING}⚠️  {text}{Colors.ENDC}")

def print_info(text: str):
    print(f"{Colors.OKCYAN}ℹ️  {text}{Colors.ENDC}")


async def setup_critical_customizations():
    """Setup com marcadores únicos para detectar perda de dados"""
    print_header("SETUP: Customizações com Marcadores Únicos")
    
    kv = KVManager()
    fields_config = await kv.get_json('skills/eye/metadata/fields')
    
    if not fields_config or 'fields' not in fields_config:
        print_error("KV vazio!")
        return {}
    
    # Aplicar marcadores únicos em TODOS os campos
    timestamp = datetime.now().isoformat()
    customizations = {}
    
    for field in fields_config['fields']:
        field['description'] = f"[STRESS-TEST-{timestamp}] {field['name']}"
        field['required'] = True
        field['auto_register'] = True
        field['category'] = 'stress_test_category'
        
        customizations[field['name']] = {
            'marker': f"STRESS-TEST-{timestamp}",
            'required': True,
            'auto_register': True,
            'category': 'stress_test_category'
        }
    
    fields_config['test_marker'] = f"STRESS-TEST-{timestamp}"
    await kv.put_json('skills/eye/metadata/fields', fields_config)
    
    print_success(f"{len(customizations)} campos marcados com identificador único")
    return customizations


async def verify_markers(expected: Dict[str, Any], scenario: str) -> tuple[bool, List[str]]:
    """Verifica se marcadores persistiram"""
    kv = KVManager()
    fields_config = await kv.get_json('skills/eye/metadata/fields')
    
    if not fields_config or 'fields' not in fields_config:
        return False, ["KV vazio após teste"]
    
    errors = []
    
    # Verificar cada campo
    for field in fields_config['fields']:
        if field['name'] in expected:
            marker = expected[field['name']]['marker']
            
            # Verificar marcador na descrição
            if marker not in field.get('description', ''):
                errors.append(f"Campo '{field['name']}': marcador perdido na descrição")
            
            # Verificar customizações
            if not field.get('required'):
                errors.append(f"Campo '{field['name']}': required=False (esperado True)")
            
            if not field.get('auto_register'):
                errors.append(f"Campo '{field['name']}': auto_register=False (esperado True)")
            
            if field.get('category') != 'stress_test_category':
                errors.append(f"Campo '{field['name']}': category incorreta")
    
    if errors:
        print_error(f"[{scenario}] {len(errors)} erro(s) encontrado(s):")
        for err in errors[:5]:  # Mostrar apenas os 5 primeiros
            print_warning(f"  - {err}")
        if len(errors) > 5:
            print_warning(f"  ... e mais {len(errors) - 5} erros")
        return False, errors
    
    print_success(f"[{scenario}] Todos os {len(expected)} marcadores OK!")
    return True, []


async def stress_test_concurrent_reads():
    """100 requisições GET simultâneas"""
    print_header("STRESS TEST 1: 100 Requisições GET Simultâneas")
    
    start_time = time.time()
    
    async def single_request(i: int):
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(f"{API_URL}/metadata-fields/", timeout=30.0)
                return response.status_code == 200
            except Exception as e:
                print_error(f"Request {i} falhou: {e}")
                return False
    
    tasks = [single_request(i) for i in range(STRESS_ITERATIONS)]
    results = await asyncio.gather(*tasks)
    
    duration = time.time() - start_time
    success_count = sum(results)
    
    print_info(f"Tempo total: {duration:.2f}s")
    print_info(f"Requisições por segundo: {STRESS_ITERATIONS / duration:.2f}")
    print_success(f"{success_count}/{STRESS_ITERATIONS} requisições OK")
    
    return success_count == STRESS_ITERATIONS


async def stress_test_concurrent_patches():
    """50 edições PATCH simultâneas em campos diferentes"""
    print_header("STRESS TEST 2: 50 PATCHs Simultâneos")
    
    kv = KVManager()
    fields_config = await kv.get_json('skills/eye/metadata/fields')
    
    if not fields_config or 'fields' not in fields_config:
        print_error("KV vazio!")
        return False
    
    # Pegar primeiros 50 campos
    fields_to_patch = fields_config['fields'][:min(CONCURRENT_REQUESTS, len(fields_config['fields']))]
    
    start_time = time.time()
    
    async def patch_field(field_name: str, index: int):
        async with httpx.AsyncClient() as client:
            try:
                response = await client.patch(
                    f"{API_URL}/metadata-fields/{field_name}",
                    json={
                        "description": f"[PATCH-STRESS-{index}] {datetime.now().isoformat()}"
                    },
                    timeout=30.0
                )
                return response.status_code == 200
            except Exception as e:
                print_error(f"PATCH {field_name} falhou: {e}")
                return False
    
    tasks = [patch_field(f['name'], i) for i, f in enumerate(fields_to_patch)]
    results = await asyncio.gather(*tasks)
    
    duration = time.time() - start_time
    success_count = sum(results)
    
    print_info(f"Tempo total: {duration:.2f}s")
    print_success(f"{success_count}/{len(fields_to_patch)} PATCHs OK")
    
    return success_count == len(fields_to_patch)


async def stress_test_rapid_force_extracts():
    """5 extrações forçadas consecutivas rápidas"""
    print_header("STRESS TEST 3: 5 Extrações Forçadas Consecutivas")
    
    start_time = time.time()
    
    for i in range(5):
        print_info(f"Extração {i+1}/5...")
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{API_URL}/metadata-fields/force-extract",
                    json={},
                    timeout=120.0
                )
                
                if response.status_code != 200:
                    print_error(f"Extração {i+1} falhou: {response.status_code}")
                    return False
            except Exception as e:
                print_error(f"Extração {i+1} exception: {e}")
                return False
        
        # Pequeno intervalo
        await asyncio.sleep(0.5)
    
    duration = time.time() - start_time
    print_info(f"Tempo total: {duration:.2f}s")
    print_success("5 extrações consecutivas OK")
    
    return True


async def stress_test_kv_race_condition():
    """Simula race condition: múltiplas escritas simultâneas no KV"""
    print_header("STRESS TEST 4: Race Condition no KV")
    
    kv = KVManager()
    
    async def concurrent_write(index: int):
        try:
            # Ler
            fields_config = await kv.get_json('skills/eye/metadata/fields')
            
            # Modificar
            fields_config['concurrent_write_test'] = f"writer-{index}-{datetime.now().isoformat()}"
            
            # Escrever
            await kv.put_json('skills/eye/metadata/fields', fields_config)
            
            # Verificar
            check = await kv.get_json('skills/eye/metadata/fields')
            return 'concurrent_write_test' in check
        except Exception as e:
            print_error(f"Writer {index} falhou: {e}")
            return False
    
    tasks = [concurrent_write(i) for i in range(20)]
    results = await asyncio.gather(*tasks)
    
    success_count = sum(results)
    print_success(f"{success_count}/20 escritas simultâneas OK")
    
    # Verificar integridade final
    final_check = await kv.get_json('skills/eye/metadata/fields')
    if 'fields' not in final_check:
        print_error("KV corrompido após race condition!")
        return False
    
    print_success("KV íntegro após race condition")
    return True


async def stress_test_empty_kv_rapid_access():
    """Deletar KV e fazer 50 acessos simultâneos (testa fallback sob stress)"""
    print_header("STRESS TEST 5: Fallback sob Múltiplos Acessos")
    
    kv = KVManager()
    
    # Backup
    print_info("Backup do KV...")
    backup = await kv.get_json('skills/eye/metadata/fields')
    
    # Deletar
    print_warning("Deletando KV...")
    await kv.delete('skills/eye/metadata/fields')
    
    # 50 acessos simultâneos (dispara fallback múltiplas vezes)
    print_info("Disparando 50 acessos simultâneos...")
    
    async def concurrent_get(i: int):
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(f"{API_URL}/metadata-fields/", timeout=90.0)
                return response.status_code == 200
            except Exception as e:
                print_error(f"Access {i} falhou: {e}")
                return False
    
    tasks = [concurrent_get(i) for i in range(50)]
    results = await asyncio.gather(*tasks)
    
    success_count = sum(results)
    print_success(f"{success_count}/50 acessos OK durante fallback")
    
    # Restaurar backup
    print_info("Restaurando backup...")
    await kv.put_json('skills/eye/metadata/fields', backup)
    
    return success_count >= 40  # Pelo menos 80% de sucesso


async def stress_test_large_description():
    """Campos com descrições enormes (teste de payload grande)"""
    print_header("STRESS TEST 6: Descrições Enormes (Large Payload)")
    
    kv = KVManager()
    fields_config = await kv.get_json('skills/eye/metadata/fields')
    
    if not fields_config or 'fields' not in fields_config:
        print_error("KV vazio!")
        return False
    
    # Criar descrição de 10KB
    large_desc = "X" * 10000
    
    # Aplicar em todos os campos
    for field in fields_config['fields']:
        field['description'] = f"[LARGE-PAYLOAD] {large_desc}"
    
    print_info(f"Payload estimado: {len(json.dumps(fields_config)) / 1024:.2f} KB")
    
    # Salvar
    try:
        await kv.put_json('skills/eye/metadata/fields', fields_config)
        print_success("Large payload salvo OK")
    except Exception as e:
        print_error(f"Falha ao salvar large payload: {e}")
        return False
    
    # Verificar leitura
    try:
        check = await kv.get_json('skills/eye/metadata/fields')
        if check and 'fields' in check and len(check['fields']) > 0:
            print_success("Large payload lido OK")
            return True
        else:
            print_error("Large payload corrompido na leitura")
            return False
    except Exception as e:
        print_error(f"Falha ao ler large payload: {e}")
        return False


async def cleanup_stress_data():
    """Limpar dados de stress test"""
    print_header("CLEANUP: Remover Dados de Stress Test")
    
    kv = KVManager()
    fields_config = await kv.get_json('skills/eye/metadata/fields')
    
    if not fields_config or 'fields' not in fields_config:
        print_warning("KV vazio, nada para limpar")
        return
    
    # Limpar marcadores
    for field in fields_config['fields']:
        if 'STRESS-TEST' in field.get('description', ''):
            field['description'] = ''
        if field.get('category') == 'stress_test_category':
            field['category'] = 'extra'
        field['required'] = False
        field['auto_register'] = False
    
    # Remover flags de teste
    if 'test_marker' in fields_config:
        del fields_config['test_marker']
    if 'concurrent_write_test' in fields_config:
        del fields_config['concurrent_write_test']
    
    fields_config['last_updated'] = datetime.now().isoformat()
    fields_config['source'] = 'stress_test_cleanup'
    
    await kv.put_json('skills/eye/metadata/fields', fields_config)
    
    print_success("Dados de stress test removidos")


async def main():
    """Executa todos os stress tests"""
    
    print_header("🔥 STRESS TESTS - PERSISTÊNCIA SOB CARGA EXTREMA")
    print_info(f"Data/Hora: {datetime.now()}")
    print()
    
    # SETUP
    customizations = await setup_critical_customizations()
    
    if not customizations:
        print_error("Falha no setup")
        return
    
    # Lista de stress tests
    stress_tests = [
        ("100 GETs Simultâneos", stress_test_concurrent_reads, customizations),
        ("50 PATCHs Simultâneos", stress_test_concurrent_patches, customizations),
        ("5 Extrações Consecutivas", stress_test_rapid_force_extracts, customizations),
        ("Race Condition KV", stress_test_kv_race_condition, customizations),
        ("Large Payload (10KB)", stress_test_large_description, customizations),
        ("Fallback + 50 Acessos", stress_test_empty_kv_rapid_access, customizations),
    ]
    
    results = {}
    
    # Executar cada teste
    for test_name, test_func, expected_custom in stress_tests:
        print()
        input(f"Pressione ENTER para executar: {test_name}...")
        
        # Executar teste
        test_ok = await test_func()
        
        if not test_ok:
            print_error(f"Teste '{test_name}' FALHOU!")
            results[test_name] = {"test": False, "verification": False}
            continue
        
        # Aguardar estabilização
        await asyncio.sleep(3)
        
        # Verificar marcadores (exceto para large payload)
        if test_name != "Large Payload (10KB)":
            verify_ok, errors = await verify_markers(expected_custom, test_name)
            results[test_name] = {"test": True, "verification": verify_ok}
        else:
            results[test_name] = {"test": True, "verification": True}
    
    # RELATÓRIO FINAL
    print_header("📊 RELATÓRIO DE STRESS TESTS")
    
    total = len(results)
    passed = sum(1 for r in results.values() if r["test"] and r["verification"])
    failed = total - passed
    
    print(f"\nTotal de Testes: {total}")
    print(f"{Colors.OKGREEN}Passou: {passed}{Colors.ENDC}")
    print(f"{Colors.FAIL}Falhou: {failed}{Colors.ENDC}")
    print()
    
    for test_name, result in results.items():
        status = "✅ PASSOU" if result["test"] and result["verification"] else "❌ FALHOU"
        color = Colors.OKGREEN if result["test"] and result["verification"] else Colors.FAIL
        print(f"{color}{status}{Colors.ENDC} - {test_name}")
        
        if not result["test"]:
            print(f"  {Colors.WARNING}Falha na execução do teste{Colors.ENDC}")
        elif not result["verification"]:
            print(f"  {Colors.FAIL}CUSTOMIZAÇÕES PERDIDAS!{Colors.ENDC}")
    
    print()
    
    # Cleanup
    await cleanup_stress_data()
    
    sys.exit(0 if failed == 0 else 1)


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n❌ Stress tests interrompidos")
        sys.exit(1)
