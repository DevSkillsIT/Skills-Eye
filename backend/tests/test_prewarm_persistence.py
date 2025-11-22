#!/usr/bin/env python3
"""
Teste Específico: Persistência após Prewarm (Reiniciar Backend)

Este teste valida se customizações persistem após reiniciar o backend,
quando o prewarm é executado.

USO:
    # Terminal 1: Iniciar backend
    python app.py
    
    # Terminal 2: Executar teste
    python test_prewarm_persistence.py
"""

import asyncio
import sys
import os
from pathlib import Path

backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

import httpx
from datetime import datetime

API_URL = os.getenv("API_URL", "http://localhost:5000/api/v1")

GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"
BOLD = "\033[1m"

async def test_prewarm_persistence():
    """Testa se customizações persistem após prewarm"""
    
    print(f"\n{BOLD}{BLUE}{'='*80}{RESET}")
    print(f"{BOLD}{BLUE}TESTE: PERSISTÊNCIA APÓS PREWARM (Reiniciar Backend){RESET}")
    print(f"{BOLD}{BLUE}{'='*80}{RESET}\n")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        
        # PASSO 1: Verificar se backend está rodando
        print(f"{BOLD}🔍 PASSO 1: Verificando se backend está rodando...{RESET}")
        try:
            response = await client.get(f"{API_URL}/metadata-fields/")
            if response.status_code != 200:
                print(f"{RED}❌ Backend não está respondendo corretamente: {response.status_code}{RESET}")
                print(f"{YELLOW}⚠️  Certifique-se de que o backend está rodando em {API_URL}{RESET}")
                return False
            print(f"{GREEN}✅ Backend está rodando{RESET}\n")
        except Exception as e:
            print(f"{RED}❌ Erro ao conectar ao backend: {e}{RESET}")
            print(f"{YELLOW}⚠️  Certifique-se de que o backend está rodando em {API_URL}{RESET}")
            return False
        
        # PASSO 2: Obter estado ORIGINAL
        print(f"{BOLD}📋 PASSO 2: Obtendo estado ORIGINAL do campo 'company'...{RESET}")
        try:
            response = await client.get(f"{API_URL}/metadata-fields/")
            data = response.json()
            fields = data.get('fields', [])
            company_field = next((f for f in fields if f.get('name') == 'company'), None)
            
            if not company_field:
                print(f"{RED}❌ Campo 'company' não encontrado!{RESET}")
                return False
            
            original = {
                'display_name': company_field.get('display_name'),
                'category': company_field.get('category'),
                'show_in_services': company_field.get('show_in_services'),
                'required': company_field.get('required'),
                'field_type': company_field.get('field_type'),
            }
            
            print(f"{GREEN}✅ Estado original capturado:{RESET}")
            for key, value in original.items():
                print(f"   - {key}: {value}")
            
        except Exception as e:
            print(f"{RED}❌ Erro ao obter estado original: {e}{RESET}")
            return False
        
        # PASSO 3: Aplicar CUSTOMIZAÇÕES
        print(f"\n{BOLD}✏️  PASSO 3: Aplicando CUSTOMIZAÇÕES no campo 'company'...{RESET}")
        test_values = {
            'display_name': f"🏢 EMPRESA PREWARM TEST {datetime.now().strftime('%H%M%S')}",
            'category': 'prewarm_test_category',
            'show_in_services': False,
            'required': True,
            'field_type': 'select',  # Se não for customizado, pode ser 'string'
        }
        
        try:
            response = await client.patch(
                f"{API_URL}/metadata-fields/company",
                json=test_values
            )
            
            if response.status_code != 200:
                print(f"{RED}❌ Erro ao atualizar campo: {response.status_code} - {response.text}{RESET}")
                return False
            
            print(f"{GREEN}✅ Customizações aplicadas:{RESET}")
            for key, value in test_values.items():
                print(f"   - {key}: {value}")
            
        except Exception as e:
            print(f"{RED}❌ Erro ao aplicar customizações: {e}{RESET}")
            return False
        
        # PASSO 4: Verificar que foram SALVAS
        print(f"\n{BOLD}🔍 PASSO 4: Verificando que customizações foram SALVAS no KV...{RESET}")
        await asyncio.sleep(1)
        
        try:
            response = await client.get(f"{API_URL}/metadata-fields/company")
            if response.status_code != 200:
                print(f"{RED}❌ Erro ao buscar campo após atualização: {response.status_code}{RESET}")
                return False
            
            data = response.json()
            field = data.get('field', {})
            
            all_ok = True
            for key, expected_value in test_values.items():
                actual_value = field.get(key)
                if actual_value != expected_value:
                    print(f"{RED}❌ {key}: esperado {expected_value}, obtido {actual_value}{RESET}")
                    all_ok = False
                else:
                    print(f"{GREEN}✅ {key}: {actual_value}{RESET}")
            
            if not all_ok:
                print(f"{RED}❌ Customizações NÃO foram salvas corretamente!{RESET}")
                return False
            
            print(f"{GREEN}✅ Customizações CONFIRMADAS no KV!{RESET}")
            
        except Exception as e:
            print(f"{RED}❌ Erro ao verificar customizações: {e}{RESET}")
            return False
        
        # PASSO 5: INSTRUÇÕES PARA REINICIAR BACKEND
        print(f"\n{BOLD}{YELLOW}{'='*80}{RESET}")
        print(f"{BOLD}{YELLOW}⚠️  PASSO 5: REINICIAR BACKEND MANUALMENTE{RESET}")
        print(f"{BOLD}{YELLOW}{'='*80}{RESET}")
        print(f"\n{YELLOW}Por favor, execute os seguintes passos:{RESET}")
        print(f"1. No terminal onde o backend está rodando, pressione {BOLD}Ctrl+C{RESET}")
        print(f"2. Reinicie o backend: {BOLD}python app.py{RESET}")
        print(f"3. Aguarde o prewarm completar (verifique os logs)")
        print(f"4. Quando o prewarm terminar, pressione {BOLD}Enter{RESET} aqui para continuar o teste")
        print(f"\n{YELLOW}Valores esperados após reiniciar:{RESET}")
        for key, value in test_values.items():
            print(f"   - {key}: {value}")
        
        input(f"\n{BOLD}Pressione Enter quando o backend reiniciar e o prewarm completar...{RESET}")
        
        # PASSO 6: Verificar se customizações foram PRESERVADAS após prewarm
        print(f"\n{BOLD}🔍 PASSO 6: Verificando se customizações foram PRESERVADAS após prewarm...{RESET}")
        await asyncio.sleep(2)  # Aguardar backend estabilizar
        
        try:
            response = await client.get(f"{API_URL}/metadata-fields/company")
            if response.status_code != 200:
                print(f"{RED}❌ Erro ao buscar campo após prewarm: {response.status_code}{RESET}")
                return False
            
            data = response.json()
            field = data.get('field', {})
            
            all_ok = True
            failed_fields = []
            
            for key, expected_value in test_values.items():
                actual_value = field.get(key)
                if actual_value != expected_value:
                    print(f"{RED}❌ {key}: esperado {expected_value}, obtido {actual_value}{RESET}")
                    all_ok = False
                    failed_fields.append((key, expected_value, actual_value))
                else:
                    print(f"{GREEN}✅ {key}: {actual_value}{RESET}")
            
            if not all_ok:
                print(f"\n{RED}❌ FALHA: Customizações NÃO foram preservadas após prewarm!{RESET}")
                print(f"\n{RED}Campos que falharam:{RESET}")
                for key, expected, actual in failed_fields:
                    print(f"   - {key}: esperado '{expected}', obtido '{actual}'")
                print(f"\n{YELLOW}Isso indica que o prewarm está sobrescrevendo customizações!{RESET}")
                return False
            
            print(f"\n{GREEN}✅ SUCESSO: Todas as customizações foram PRESERVADAS após prewarm!{RESET}")
            
        except Exception as e:
            print(f"{RED}❌ Erro ao verificar preservação: {e}{RESET}")
            return False
        
        # PASSO 7: Restaurar estado original
        print(f"\n{BOLD}🧹 PASSO 7: Restaurando estado original (cleanup)...{RESET}")
        try:
            response = await client.patch(
                f"{API_URL}/metadata-fields/company",
                json=original
            )
            
            if response.status_code == 200:
                print(f"{GREEN}✅ Campo restaurado ao estado original{RESET}")
            else:
                print(f"{YELLOW}⚠️  Aviso: Não foi possível restaurar campo (status: {response.status_code}){RESET}")
            
        except Exception as e:
            print(f"{YELLOW}⚠️  Aviso: Erro ao restaurar campo: {e}{RESET}")
        
        print(f"\n{BOLD}{GREEN}{'='*80}{RESET}")
        print(f"{BOLD}{GREEN}🎉 TESTE CONCLUÍDO!{RESET}")
        print(f"{BOLD}{GREEN}{'='*80}{RESET}\n")
        
        return True

if __name__ == "__main__":
    success = asyncio.run(test_prewarm_persistence())
    sys.exit(0 if success else 1)

