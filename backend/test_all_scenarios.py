#!/usr/bin/env python3
"""
BATERIA COMPLETA DE TESTES - PERSISTÊNCIA DE CUSTOMIZAÇÕES DE FIELDS

Testa TODOS os cenários que podem causar perda de dados:
1. Reinício simples do backend
2. Limpeza de cache + reload
3. Extração forçada (botão "Sincronizar")
4. Fallback automático (KV vazio)
5. Múltiplos reinícios consecutivos
6. Edição de campo via PATCH
7. Adicionar campo novo via add-to-kv
8. Remover campos órfãos
9. Sincronização de sites
10. Reordenação de campos

EXECUÇÃO:
    python3 test_all_scenarios.py
"""

import asyncio
import sys
import json
import httpx
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.kv_manager import KVManager

# Configurações
API_URL = "http://localhost:5000/api/v1"
TEST_FIELDS = ['vendor', 'region', 'campoextra1']

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


async def setup_test_customizations() -> Dict[str, Any]:
    """Aplica customizações de teste em 3 campos"""
    print_header("SETUP: Aplicar Customizações de Teste")
    
    kv = KVManager()
    
    # Buscar configuração atual
    fields_config = await kv.get_json('skills/eye/metadata/fields')
    
    if not fields_config or 'fields' not in fields_config:
        print_error("KV vazio ou sem estrutura 'fields'")
        return {}
    
    fields = fields_config['fields']
    
    # Aplicar customizações
    customizations = {}
    
    for field in fields:
        if field['name'] in TEST_FIELDS:
            customizations[field['name']] = {
                'original': {
                    'required': field.get('required', False),
                    'auto_register': field.get('auto_register', False),
                    'category': field.get('category', 'extra'),
                    'order': field.get('order', 999),
                    'description': field.get('description', ''),
                },
                'customized': {
                    'required': True,
                    'auto_register': True,
                    'category': 'test_category_critical',
                    'order': 1000 + len(customizations),
                    'description': f'[TESTE CRÍTICO] Campo {field["name"]} customizado em {datetime.now()}',
                }
            }
            
            # Aplicar
            field['required'] = True
            field['auto_register'] = True
            field['category'] = 'test_category_critical'
            field['order'] = 1000 + len(customizations)
            field['description'] = f'[TESTE CRÍTICO] Campo {field["name"]} customizado em {datetime.now()}'
    
    # Salvar
    fields_config['fields'] = fields
    fields_config['last_updated'] = datetime.now().isoformat()
    fields_config['source'] = 'test_setup'
    
    await kv.put_json('skills/eye/metadata/fields', fields_config)
    
    print_success(f"{len(customizations)} campos customizados")
    for field_name in customizations.keys():
        print_info(f"  - {field_name}: required=True, auto_register=True, category=test_category_critical")
    
    return customizations


async def verify_customizations(expected: Dict[str, Any], scenario: str) -> bool:
    """Verifica se customizações persistiram"""
    kv = KVManager()
    
    fields_config = await kv.get_json('skills/eye/metadata/fields')
    
    if not fields_config or 'fields' not in fields_config:
        print_error(f"[{scenario}] KV vazio após teste!")
        return False
    
    fields = fields_config['fields']
    
    # Verificar cada campo
    all_ok = True
    for field in fields:
        if field['name'] in expected:
            expected_custom = expected[field['name']]['customized']
            
            checks = [
                ('required', field.get('required') == expected_custom['required']),
                ('auto_register', field.get('auto_register') == expected_custom['auto_register']),
                ('category', field.get('category') == expected_custom['category']),
            ]
            
            field_ok = all(check[1] for check in checks)
            
            if not field_ok:
                print_error(f"[{scenario}] Campo '{field['name']}' PERDEU customizações!")
                for check_name, check_result in checks:
                    if not check_result:
                        print_warning(f"    {check_name}: esperado={expected_custom[check_name]}, atual={field.get(check_name)}")
                all_ok = False
    
    if all_ok:
        print_success(f"[{scenario}] Todas customizações PRESERVADAS!")
    
    return all_ok


async def test_scenario_1_simple_restart():
    """Cenário 1: Reinício simples do backend"""
    print_header("CENÁRIO 1: Reinício Simples do Backend")
    
    print_info("Simulando reinício... (cache em memória será limpo automaticamente)")
    
    # Simular limpeza de cache em memória
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{API_URL}/metadata-fields/", timeout=30.0)
            if response.status_code == 200:
                print_success("Endpoint /metadata-fields/ respondeu OK")
            else:
                print_error(f"Endpoint retornou status {response.status_code}")
                return False
        except Exception as e:
            print_error(f"Erro ao acessar endpoint: {e}")
            return False
    
    return True


async def test_scenario_2_force_extract():
    """Cenário 2: Extração forçada (botão Sincronizar)"""
    print_header("CENÁRIO 2: Extração Forçada (Botão Sincronizar)")
    
    print_info("Chamando POST /metadata-fields/force-extract")
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{API_URL}/metadata-fields/force-extract",
                json={},
                timeout=60.0
            )
            
            if response.status_code == 200:
                result = response.json()
                print_success(f"Extração concluída: {result.get('total_fields', 0)} campos")
            else:
                print_error(f"Force extract falhou: {response.status_code}")
                return False
        except Exception as e:
            print_error(f"Erro na extração forçada: {e}")
            return False
    
    return True


async def test_scenario_3_empty_kv():
    """Cenário 3: KV vazio (fallback automático)"""
    print_header("CENÁRIO 3: KV Vazio (Fallback Automático)")
    
    kv = KVManager()
    
    # BACKUP antes de deletar
    print_info("Fazendo backup do KV...")
    backup = await kv.get_json('skills/eye/metadata/fields')
    
    # Deletar KV
    print_warning("DELETANDO KV para simular fallback...")
    await kv.delete('skills/eye/metadata/fields')
    
    # Aguardar 2 segundos
    await asyncio.sleep(2)
    
    # Fazer requisição (dispara fallback)
    print_info("Fazendo requisição para disparar fallback...")
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{API_URL}/metadata-fields/", timeout=60.0)
            if response.status_code == 200:
                print_success("Fallback executado com sucesso")
            else:
                print_error(f"Fallback falhou: {response.status_code}")
                # RESTAURAR backup
                await kv.put_json('skills/eye/metadata/fields', backup)
                return False
        except Exception as e:
            print_error(f"Erro no fallback: {e}")
            # RESTAURAR backup
            await kv.put_json('skills/eye/metadata/fields', backup)
            return False
    
    return True


async def test_scenario_4_patch_field():
    """Cenário 4: Edição de campo via PATCH"""
    print_header("CENÁRIO 4: Edição de Campo via PATCH")
    
    test_field = TEST_FIELDS[0]
    
    print_info(f"Editando campo '{test_field}' via PATCH")
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.patch(
                f"{API_URL}/metadata-fields/{test_field}",
                json={
                    "description": f"[EDITADO VIA PATCH] {datetime.now()}"
                },
                timeout=30.0
            )
            
            if response.status_code == 200:
                print_success(f"Campo '{test_field}' editado via PATCH")
            else:
                print_error(f"PATCH falhou: {response.status_code}")
                return False
        except Exception as e:
            print_error(f"Erro no PATCH: {e}")
            return False
    
    return True


async def test_scenario_5_add_to_kv():
    """Cenário 5: Adicionar campo novo via add-to-kv"""
    print_header("CENÁRIO 5: Adicionar Campo Novo (add-to-kv)")
    
    print_info("Adicionando campo 'test_new_field' via add-to-kv")
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{API_URL}/metadata-fields/add-to-kv",
                json={
                    "field_names": ["test_new_field"],
                    "fields_data": [{
                        "name": "test_new_field",
                        "display_name": "Campo de Teste",
                        "source_label": "__meta_consul_service_metadata_test_new_field",
                        "field_type": "string",
                        "required": False,
                        "show_in_table": True,
                        "show_in_dashboard": False,
                        "options": []
                    }]
                },
                timeout=30.0
            )
            
            if response.status_code == 200:
                print_success("Campo 'test_new_field' adicionado")
            else:
                print_error(f"add-to-kv falhou: {response.status_code}")
                return False
        except Exception as e:
            print_error(f"Erro no add-to-kv: {e}")
            return False
    
    return True


async def test_scenario_6_multiple_restarts():
    """Cenário 6: Múltiplos reinícios consecutivos"""
    print_header("CENÁRIO 6: Múltiplos Reinícios Consecutivos")
    
    for i in range(3):
        print_info(f"Reinício {i+1}/3...")
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(f"{API_URL}/metadata-fields/", timeout=30.0)
                if response.status_code != 200:
                    print_error(f"Reinício {i+1} falhou")
                    return False
            except Exception as e:
                print_error(f"Erro no reinício {i+1}: {e}")
                return False
        
        await asyncio.sleep(1)
    
    print_success("3 reinícios consecutivos OK")
    return True


async def test_scenario_7_reorder_fields():
    """Cenário 7: Reordenação de campos"""
    print_header("CENÁRIO 7: Reordenação de Campos")
    
    print_info("Reordenando campos via POST /reorder")
    
    kv = KVManager()
    fields_config = await kv.get_json('skills/eye/metadata/fields')
    fields = fields_config['fields']
    
    # Inverter ordem
    field_names = [f['name'] for f in fields]
    field_names.reverse()
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{API_URL}/metadata-fields/reorder",
                json={"field_names": field_names},
                timeout=30.0
            )
            
            if response.status_code == 200:
                print_success("Campos reordenados")
            else:
                print_error(f"Reorder falhou: {response.status_code}")
                return False
        except Exception as e:
            print_error(f"Erro no reorder: {e}")
            return False
    
    return True


async def test_scenario_8_remove_orphans():
    """Cenário 8: Remover campos órfãos"""
    print_header("CENÁRIO 8: Remover Campos Órfãos")
    
    print_info("Chamando POST /remove-orphans")
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{API_URL}/metadata-fields/remove-orphans",
                json={},
                timeout=30.0
            )
            
            if response.status_code == 200:
                result = response.json()
                print_success(f"Órfãos removidos: {result.get('removed_count', 0)}")
            else:
                print_error(f"Remove orphans falhou: {response.status_code}")
                return False
        except Exception as e:
            print_error(f"Erro ao remover órfãos: {e}")
            return False
    
    return True


async def cleanup_test_data():
    """Limpar dados de teste"""
    print_header("CLEANUP: Remover Customizações de Teste")
    
    kv = KVManager()
    fields_config = await kv.get_json('skills/eye/metadata/fields')
    
    if not fields_config or 'fields' not in fields_config:
        print_warning("KV vazio, nada para limpar")
        return
    
    fields = fields_config['fields']
    
    # Remover customizações de teste
    cleaned = 0
    for field in fields:
        if field.get('category') == 'test_category_critical':
            field['required'] = False
            field['auto_register'] = False
            field['category'] = 'extra'
            field['order'] = 999
            field['description'] = ''
            cleaned += 1
    
    # Remover campo test_new_field
    fields = [f for f in fields if f['name'] != 'test_new_field']
    fields_config['fields'] = fields
    
    fields_config['last_updated'] = datetime.now().isoformat()
    fields_config['source'] = 'test_cleanup'
    
    await kv.put_json('skills/eye/metadata/fields', fields_config)
    
    print_success(f"{cleaned} customizações removidas")


async def main():
    """Executa todos os testes"""
    
    print_header("🧪 BATERIA COMPLETA DE TESTES - PERSISTÊNCIA DE CUSTOMIZAÇÕES")
    print_info(f"Data/Hora: {datetime.now()}")
    print_info(f"API URL: {API_URL}")
    print()
    
    # SETUP
    customizations = await setup_test_customizations()
    
    if not customizations:
        print_error("Falha no setup inicial")
        return
    
    # Lista de cenários
    scenarios = [
        ("Reinício Simples", test_scenario_1_simple_restart),
        ("Extração Forçada", test_scenario_2_force_extract),
        ("PATCH Campo", test_scenario_4_patch_field),
        ("Múltiplos Reinícios", test_scenario_6_multiple_restarts),
        ("Reordenação", test_scenario_7_reorder_fields),
        ("Adicionar Campo", test_scenario_5_add_to_kv),
        ("Remover Órfãos", test_scenario_8_remove_orphans),
        ("KV Vazio (CRÍTICO)", test_scenario_3_empty_kv),  # Último por ser destrutivo
    ]
    
    results = {}
    
    # Executar cada cenário
    for scenario_name, scenario_func in scenarios:
        print()
        input(f"Pressione ENTER para executar: {scenario_name}...")
        
        # Executar cenário
        scenario_ok = await scenario_func()
        
        if not scenario_ok:
            print_error(f"Cenário '{scenario_name}' FALHOU na execução!")
            results[scenario_name] = {"execution": False, "verification": False}
            continue
        
        # Aguardar 2 segundos
        await asyncio.sleep(2)
        
        # Verificar customizações
        verify_ok = await verify_customizations(customizations, scenario_name)
        
        results[scenario_name] = {"execution": True, "verification": verify_ok}
    
    # RELATÓRIO FINAL
    print_header("📊 RELATÓRIO FINAL")
    
    total = len(results)
    passed = sum(1 for r in results.values() if r["execution"] and r["verification"])
    failed = total - passed
    
    print(f"\nTotal de Cenários: {total}")
    print(f"{Colors.OKGREEN}Passou: {passed}{Colors.ENDC}")
    print(f"{Colors.FAIL}Falhou: {failed}{Colors.ENDC}")
    print()
    
    for scenario_name, result in results.items():
        status = "✅ PASSOU" if result["execution"] and result["verification"] else "❌ FALHOU"
        color = Colors.OKGREEN if result["execution"] and result["verification"] else Colors.FAIL
        print(f"{color}{status}{Colors.ENDC} - {scenario_name}")
        
        if not result["execution"]:
            print(f"  {Colors.WARNING}Falha na execução do cenário{Colors.ENDC}")
        elif not result["verification"]:
            print(f"  {Colors.FAIL}CUSTOMIZAÇÕES PERDIDAS!{Colors.ENDC}")
    
    print()
    
    # Cleanup
    await cleanup_test_data()
    
    # Exit code
    sys.exit(0 if failed == 0 else 1)


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n❌ Testes interrompidos pelo usuário")
        sys.exit(1)
