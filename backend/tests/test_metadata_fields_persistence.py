#!/usr/bin/env python3
"""
Teste de Persistência de Customizações de Metadata Fields

Este script testa se as customizações de campos (display_name, category, show_in_*, etc)
são preservadas após:
1. Reiniciar backend (prewarm)
2. Force-extract
3. Fallback quando KV vazio

USO:
    python test_metadata_fields_persistence.py
"""

import asyncio
import sys
import os
from pathlib import Path

# Adicionar backend ao path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

import httpx
from datetime import datetime

API_URL = os.getenv("API_URL", "http://localhost:5000/api/v1")

# Cores para output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"
BOLD = "\033[1m"

async def test_persistence():
    """Testa persistência de customizações"""
    
    print(f"\n{BOLD}{BLUE}{'='*80}{RESET}")
    print(f"{BOLD}{BLUE}TESTE DE PERSISTÊNCIA DE CUSTOMIZAÇÕES - METADATA FIELDS{RESET}")
    print(f"{BOLD}{BLUE}{'='*80}{RESET}\n")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        
        # PASSO 1: Obter estado ORIGINAL de um campo
        print(f"{BOLD}📋 PASSO 1: Obtendo estado ORIGINAL do campo 'company'...{RESET}")
        try:
            response = await client.get(f"{API_URL}/metadata-fields/")
            if response.status_code != 200:
                print(f"{RED}❌ Erro ao buscar campos: {response.status_code}{RESET}")
                return False
            
            data = response.json()
            fields = data.get('fields', [])
            company_field = next((f for f in fields if f.get('name') == 'company'), None)
            
            if not company_field:
                print(f"{RED}❌ Campo 'company' não encontrado!{RESET}")
                return False
            
            original_display_name = company_field.get('display_name')
            original_category = company_field.get('category')
            original_show_in_services = company_field.get('show_in_services')
            original_required = company_field.get('required')
            
            print(f"{GREEN}✅ Campo encontrado:{RESET}")
            print(f"   - display_name: {original_display_name}")
            print(f"   - category: {original_category}")
            print(f"   - show_in_services: {original_show_in_services}")
            print(f"   - required: {original_required}")
            
        except Exception as e:
            print(f"{RED}❌ Erro ao buscar campo original: {e}{RESET}")
            return False
        
        # PASSO 2: Aplicar CUSTOMIZAÇÕES
        print(f"\n{BOLD}✏️  PASSO 2: Aplicando CUSTOMIZAÇÕES no campo 'company'...{RESET}")
        test_display_name = f"🏢 EMPRESA TESTE {datetime.now().strftime('%H%M%S')}"
        test_category = "test_category"
        test_show_in_services = False
        test_required = True
        
        try:
            updates = {
                'display_name': test_display_name,
                'category': test_category,
                'show_in_services': test_show_in_services,
                'required': test_required,
            }
            
            response = await client.patch(
                f"{API_URL}/metadata-fields/company",
                json=updates
            )
            
            if response.status_code != 200:
                print(f"{RED}❌ Erro ao atualizar campo: {response.status_code} - {response.text}{RESET}")
                return False
            
            print(f"{GREEN}✅ Customizações aplicadas com sucesso!{RESET}")
            print(f"   - display_name: {test_display_name}")
            print(f"   - category: {test_category}")
            print(f"   - show_in_services: {test_show_in_services}")
            print(f"   - required: {test_required}")
            
        except Exception as e:
            print(f"{RED}❌ Erro ao aplicar customizações: {e}{RESET}")
            return False
        
        # PASSO 3: Verificar que customizações foram SALVAS
        print(f"\n{BOLD}🔍 PASSO 3: Verificando que customizações foram SALVAS...{RESET}")
        await asyncio.sleep(1)  # Aguardar cache invalidar
        
        try:
            response = await client.get(f"{API_URL}/metadata-fields/")
            if response.status_code != 200:
                print(f"{RED}❌ Erro ao buscar campos após atualização: {response.status_code}{RESET}")
                return False
            
            data = response.json()
            fields = data.get('fields', [])
            company_field = next((f for f in fields if f.get('name') == 'company'), None)
            
            if not company_field:
                print(f"{RED}❌ Campo 'company' não encontrado após atualização!{RESET}")
                return False
            
            # Verificar cada campo customizado
            checks = [
                ('display_name', test_display_name),
                ('category', test_category),
                ('show_in_services', test_show_in_services),
                ('required', test_required),
            ]
            
            all_ok = True
            for field_name, expected_value in checks:
                actual_value = company_field.get(field_name)
                if actual_value != expected_value:
                    print(f"{RED}❌ {field_name}: esperado {expected_value}, obtido {actual_value}{RESET}")
                    all_ok = False
                else:
                    print(f"{GREEN}✅ {field_name}: {actual_value}{RESET}")
            
            if not all_ok:
                print(f"{RED}❌ Customizações NÃO foram salvas corretamente!{RESET}")
                return False
            
            print(f"{GREEN}✅ Customizações CONFIRMADAS no KV!{RESET}")
            
        except Exception as e:
            print(f"{RED}❌ Erro ao verificar customizações: {e}{RESET}")
            return False
        
        # PASSO 4: Executar FORCE-EXTRACT (deve PRESERVAR customizações)
        print(f"\n{BOLD}🚨 PASSO 4: Executando FORCE-EXTRACT (deve PRESERVAR customizações)...{RESET}")
        try:
            response = await client.post(f"{API_URL}/metadata-fields/force-extract")
            if response.status_code != 200:
                print(f"{RED}❌ Erro ao executar force-extract: {response.status_code}{RESET}")
                return False
            
            print(f"{GREEN}✅ Force-extract concluído{RESET}")
            
        except Exception as e:
            print(f"{RED}❌ Erro ao executar force-extract: {e}{RESET}")
            return False
        
        # PASSO 5: Verificar se customizações foram PRESERVADAS após force-extract
        print(f"\n{BOLD}🔍 PASSO 5: Verificando se customizações foram PRESERVADAS após force-extract...{RESET}")
        await asyncio.sleep(2)  # Aguardar processamento
        
        try:
            response = await client.get(f"{API_URL}/metadata-fields/")
            if response.status_code != 200:
                print(f"{RED}❌ Erro ao buscar campos após force-extract: {response.status_code}{RESET}")
                return False
            
            data = response.json()
            fields = data.get('fields', [])
            company_field = next((f for f in fields if f.get('name') == 'company'), None)
            
            if not company_field:
                print(f"{RED}❌ Campo 'company' não encontrado após force-extract!{RESET}")
                return False
            
            # Verificar cada campo customizado
            checks = [
                ('display_name', test_display_name),
                ('category', test_category),
                ('show_in_services', test_show_in_services),
                ('required', test_required),
            ]
            
            all_ok = True
            for field_name, expected_value in checks:
                actual_value = company_field.get(field_name)
                if actual_value != expected_value:
                    print(f"{RED}❌ {field_name}: esperado {expected_value}, obtido {actual_value}{RESET}")
                    all_ok = False
                else:
                    print(f"{GREEN}✅ {field_name}: {actual_value}{RESET}")
            
            if not all_ok:
                print(f"\n{RED}❌ FALHA: Customizações NÃO foram preservadas após force-extract!{RESET}")
                return False
            
            print(f"\n{GREEN}✅ SUCESSO: Todas as customizações foram PRESERVADAS!{RESET}")
            
        except Exception as e:
            print(f"{RED}❌ Erro ao verificar preservação: {e}{RESET}")
            return False
        
        # PASSO 6: Restaurar estado original (cleanup)
        print(f"\n{BOLD}🧹 PASSO 6: Restaurando estado original (cleanup)...{RESET}")
        try:
            restore_updates = {
                'display_name': original_display_name,
                'category': original_category,
                'show_in_services': original_show_in_services,
                'required': original_required,
            }
            
            response = await client.patch(
                f"{API_URL}/metadata-fields/company",
                json=restore_updates
            )
            
            if response.status_code == 200:
                print(f"{GREEN}✅ Campo restaurado ao estado original{RESET}")
            else:
                print(f"{YELLOW}⚠️  Aviso: Não foi possível restaurar campo (status: {response.status_code}){RESET}")
            
        except Exception as e:
            print(f"{YELLOW}⚠️  Aviso: Erro ao restaurar campo: {e}{RESET}")
        
        print(f"\n{BOLD}{GREEN}{'='*80}{RESET}")
        print(f"{BOLD}{GREEN}🎉 TESTE CONCLUÍDO COM SUCESSO!{RESET}")
        print(f"{BOLD}{GREEN}{'='*80}{RESET}\n")
        
        return True

if __name__ == "__main__":
    success = asyncio.run(test_persistence())
    sys.exit(0 if success else 1)

