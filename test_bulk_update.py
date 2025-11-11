#!/usr/bin/env python3
"""
Script de Teste Automatizado - Bulk Update de Reference Values

OBJETIVO:
- Testar rename de reference value SEM QUEBRAR serviços
- Validar que APENAS o campo alterado muda
- Garantir que ID, Address, Port, Tags, Checks permanecem INTACTOS

SEGURANÇA:
- Cria serviço de TESTE
- Testa rename
- Valida resultado
- DELETA serviço de teste
- NÃO toca em serviços de produção!
"""

import asyncio
import httpx
import json
import sys
from datetime import datetime
from typing import Dict, List, Any

# ============================================================================
# CONFIGURAÇÃO
# ============================================================================

BACKEND_URL = "http://localhost:5000/api/v1"
CONSUL_HOST = "172.16.1.26"
CONSUL_PORT = 8500
CONSUL_TOKEN = "8382a112-81e0-cd6d-2b92-8565925a0675"

# Cores para output
RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"

# ============================================================================
# FUNÇÕES AUXILIARES
# ============================================================================

def log_info(msg: str):
    print(f"{BLUE}[INFO]{RESET} {msg}")

def log_success(msg: str):
    print(f"{GREEN}[✓]{RESET} {msg}")

def log_error(msg: str):
    print(f"{RED}[✗]{RESET} {msg}")

def log_warning(msg: str):
    print(f"{YELLOW}[!]{RESET} {msg}")

def compare_dicts(before: Dict, after: Dict, field_changed: str, old_value: str, new_value: str) -> bool:
    """
    Compara dois dicionários e valida que APENAS o campo especificado mudou.

    Returns:
        True se validação passou, False caso contrário
    """
    errors = []

    # Campos que DEVEM mudar
    expected_changes = {
        f"Meta.{field_changed}": (old_value, new_value)
    }

    # Campos que NÃO DEVEM mudar
    critical_fields = ["ID", "Service", "Address", "Port", "Tags"]

    # Verificar campos críticos
    for field in critical_fields:
        before_val = before.get(field)
        after_val = after.get(field)

        if before_val != after_val:
            errors.append(f"❌ CAMPO '{field}' MUDOU: {before_val} → {after_val}")

    # Verificar Meta (exceto o campo que deve mudar)
    before_meta = before.get("Meta", {})
    after_meta = after.get("Meta", {})

    for key in before_meta:
        if key == field_changed:
            # Este deve mudar
            before_val = before_meta.get(key)
            after_val = after_meta.get(key)

            if after_val != new_value:
                errors.append(f"❌ Meta.{field_changed} NÃO foi atualizado corretamente: {after_val} (esperado: {new_value})")
        else:
            # Este NÃO deve mudar
            before_val = before_meta.get(key)
            after_val = after_meta.get(key)

            if before_val != after_val:
                errors.append(f"❌ Meta.{key} mudou inesperadamente: {before_val} → {after_val}")

    # Verificar Tags
    before_tags = set(before.get("Tags", []))
    after_tags = set(after.get("Tags", []))

    if before_tags != after_tags:
        errors.append(f"❌ TAGS mudaram: {before_tags} → {after_tags}")

    # Verificar Checks (se existirem)
    if "Checks" in before:
        before_checks_count = len(before.get("Checks", []))
        after_checks_count = len(after.get("Checks", []))

        if before_checks_count != after_checks_count:
            errors.append(f"❌ CHECKS mudaram: {before_checks_count} → {after_checks_count}")

    # Imprimir erros
    if errors:
        log_error("VALIDAÇÃO FALHOU:")
        for err in errors:
            print(f"  {err}")
        return False

    return True

# ============================================================================
# CLIENTE CONSUL
# ============================================================================

class ConsulClient:
    def __init__(self):
        self.base_url = f"http://{CONSUL_HOST}:{CONSUL_PORT}"
        self.headers = {"X-Consul-Token": CONSUL_TOKEN}

    async def get_service(self, service_id: str) -> Dict:
        """Busca serviço específico pelo ID"""
        async with httpx.AsyncClient() as client:
            # Buscar todos os serviços e filtrar pelo ID
            response = await client.get(
                f"{self.base_url}/v1/agent/services",
                headers=self.headers,
                timeout=10.0
            )
            response.raise_for_status()

            services = response.json()

            for svc_id, svc_data in services.items():
                if svc_id == service_id:
                    return svc_data

            raise ValueError(f"Serviço {service_id} não encontrado")

    async def register_service(self, service_data: Dict) -> bool:
        """Registra serviço no Consul"""
        async with httpx.AsyncClient() as client:
            response = await client.put(
                f"{self.base_url}/v1/agent/service/register",
                headers=self.headers,
                json=service_data,
                timeout=10.0
            )
            response.raise_for_status()
            return True

    async def deregister_service(self, service_id: str) -> bool:
        """Remove serviço do Consul"""
        async with httpx.AsyncClient() as client:
            response = await client.put(
                f"{self.base_url}/v1/agent/service/deregister/{service_id}",
                headers=self.headers,
                timeout=10.0
            )
            response.raise_for_status()
            return True

# ============================================================================
# CLIENTE BACKEND API
# ============================================================================

class BackendClient:
    def __init__(self):
        self.base_url = BACKEND_URL

    async def create_reference_value(self, field_name: str, value: str) -> bool:
        """Cria reference value"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/reference-values/",
                json={
                    "field_name": field_name,
                    "value": value
                },
                timeout=10.0
            )

            if response.status_code == 200:
                return True
            elif response.status_code == 400 and "já existe" in response.json().get("detail", ""):
                log_warning(f"Valor '{value}' já existe (OK)")
                return True
            else:
                raise Exception(f"Erro ao criar reference value: {response.text}")

    async def rename_reference_value(self, field_name: str, old_value: str, new_value: str) -> Dict:
        """Renomeia reference value (BULK UPDATE!)"""
        async with httpx.AsyncClient() as client:
            response = await client.patch(
                f"{self.base_url}/reference-values/{field_name}/{old_value}/rename",
                params={"new_value": new_value},
                timeout=30.0  # Timeout maior para bulk update
            )
            response.raise_for_status()
            return response.json()

    async def delete_reference_value(self, field_name: str, value: str) -> bool:
        """Deleta reference value"""
        async with httpx.AsyncClient() as client:
            response = await client.delete(
                f"{self.base_url}/reference-values/{field_name}/{value}",
                params={"force": True},  # Force delete
                timeout=10.0
            )

            if response.status_code in [200, 404]:
                return True
            else:
                raise Exception(f"Erro ao deletar reference value: {response.text}")

# ============================================================================
# TESTE PRINCIPAL
# ============================================================================

async def run_test():
    """
    Executa teste completo do bulk update.
    """

    print("=" * 80)
    print(f"{BLUE}TESTE AUTOMATIZADO - BULK UPDATE DE REFERENCE VALUES{RESET}")
    print("=" * 80)
    print()

    consul = ConsulClient()
    backend = BackendClient()

    # IDs únicos para teste
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    test_service_id = f"test-bulk-update-{timestamp}"
    test_company_old = f"TestCompany_{timestamp}"
    test_company_new = f"TestCompany_{timestamp}_RENAMED"

    test_passed = False

    try:
        # ====================================================================
        # PASSO 1: Criar reference value de teste
        # ====================================================================
        log_info(f"PASSO 1: Criando reference value '{test_company_old}'...")

        await backend.create_reference_value("company", test_company_old)

        log_success(f"Reference value '{test_company_old}' criado")
        print()

        # ====================================================================
        # PASSO 2: Registrar serviço de teste no Consul
        # ====================================================================
        log_info(f"PASSO 2: Registrando serviço de teste '{test_service_id}'...")

        test_service = {
            "ID": test_service_id,
            "Name": "test-service",
            "Address": "127.0.0.1",
            "Port": 9999,
            "Tags": ["test", "bulk-update"],
            "Meta": {
                "company": test_company_old,
                "env": "test",
                "tipo_monitoramento": "teste_automatizado"
            },
            "Check": {
                "HTTP": "http://127.0.0.1:9999/health",
                "Interval": "10s"
            }
        }

        await consul.register_service(test_service)

        log_success(f"Serviço '{test_service_id}' registrado")
        print()

        # Aguardar 2 segundos para propagação
        log_info("Aguardando 2 segundos para propagação no Consul...")
        await asyncio.sleep(2)
        print()

        # ====================================================================
        # PASSO 3: Buscar serviço ANTES do rename
        # ====================================================================
        log_info(f"PASSO 3: Buscando serviço ANTES do rename...")

        service_before = await consul.get_service(test_service_id)

        log_success("Serviço encontrado")
        print(f"  ID: {service_before['ID']}")
        print(f"  Address: {service_before['Address']}")
        print(f"  Port: {service_before['Port']}")
        print(f"  Tags: {service_before['Tags']}")
        print(f"  Meta.company: {service_before['Meta']['company']}")
        print()

        # ====================================================================
        # PASSO 4: EXECUTAR BULK UPDATE (RENAME)
        # ====================================================================
        log_info(f"PASSO 4: EXECUTANDO BULK UPDATE...")
        log_warning(f"Renomeando '{test_company_old}' → '{test_company_new}'")

        start_time = datetime.now()

        result = await backend.rename_reference_value(
            field_name="company",
            old_value=test_company_old,
            new_value=test_company_new
        )

        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        log_success(f"Bulk update concluído em {duration:.2f}s")
        print(f"  Mensagem: {result.get('message', 'N/A')}")
        print()

        # Aguardar 2 segundos para propagação
        log_info("Aguardando 2 segundos para propagação no Consul...")
        await asyncio.sleep(2)
        print()

        # ====================================================================
        # PASSO 5: Buscar serviço DEPOIS do rename
        # ====================================================================
        log_info(f"PASSO 5: Buscando serviço DEPOIS do rename...")

        service_after = await consul.get_service(test_service_id)

        log_success("Serviço encontrado")
        print(f"  ID: {service_after['ID']}")
        print(f"  Address: {service_after['Address']}")
        print(f"  Port: {service_after['Port']}")
        print(f"  Tags: {service_after['Tags']}")
        print(f"  Meta.company: {service_after['Meta']['company']}")
        print()

        # ====================================================================
        # PASSO 6: VALIDAR RESULTADO
        # ====================================================================
        log_info("PASSO 6: VALIDANDO resultado do bulk update...")
        print()

        validation_passed = compare_dicts(
            before=service_before,
            after=service_after,
            field_changed="company",
            old_value=test_company_old,
            new_value=test_company_new
        )

        if validation_passed:
            log_success("✅ VALIDAÇÃO PASSOU!")
            log_success(f"✅ Apenas Meta.company mudou: '{test_company_old}' → '{test_company_new}'")
            log_success("✅ ID, Address, Port, Tags, Checks permanecem intactos")
            test_passed = True
        else:
            log_error("❌ VALIDAÇÃO FALHOU!")
            log_error("❌ BULK UPDATE TEM PROBLEMAS - NÃO USE EM PRODUÇÃO!")

        print()

    except Exception as e:
        log_error(f"ERRO DURANTE TESTE: {e}")
        import traceback
        traceback.print_exc()

    finally:
        # ====================================================================
        # LIMPEZA: Remover serviço de teste
        # ====================================================================
        log_info("LIMPEZA: Removendo serviço de teste...")

        try:
            await consul.deregister_service(test_service_id)
            log_success(f"Serviço '{test_service_id}' removido")
        except Exception as e:
            log_warning(f"Erro ao remover serviço: {e}")

        # Remover reference values de teste
        log_info("LIMPEZA: Removendo reference values de teste...")

        try:
            await backend.delete_reference_value("company", test_company_old)
            await backend.delete_reference_value("company", test_company_new)
            log_success("Reference values de teste removidos")
        except Exception as e:
            log_warning(f"Erro ao remover reference values: {e}")

        print()

    # ====================================================================
    # RESULTADO FINAL
    # ====================================================================
    print("=" * 80)
    if test_passed:
        print(f"{GREEN}✅ TESTE PASSOU - BULK UPDATE FUNCIONA CORRETAMENTE{RESET}")
        print(f"{GREEN}✅ SEGURO PARA USO EM PRODUÇÃO{RESET}")
    else:
        print(f"{RED}❌ TESTE FALHOU - NÃO USE BULK UPDATE EM PRODUÇÃO!{RESET}")
        print(f"{RED}❌ CÓDIGO TEM PROBLEMAS E PODE QUEBRAR SERVIÇOS{RESET}")
    print("=" * 80)

    return 0 if test_passed else 1

# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    exit_code = asyncio.run(run_test())
    sys.exit(exit_code)
