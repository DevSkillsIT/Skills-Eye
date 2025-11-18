"""
Testes de Baseline - Hardcodes em Services API
Testa comportamento ANTES das correções
"""
import pytest
import asyncio
from backend.core.consul_manager import ConsulManager
from backend.core.config import Config

@pytest.mark.asyncio
async def test_baseline_required_fields():
    """Teste baseline: Verificar campos obrigatórios do KV"""
    required = Config.get_required_fields()
    print(f"\n✅ Campos obrigatórios do KV: {required}")
    assert isinstance(required, list)
    return required

@pytest.mark.asyncio
async def test_baseline_validate_service_data():
    """Teste baseline: validate_service_data com campos hardcoded"""
    consul = ConsulManager()
    
    # Serviço válido (com campos hardcoded)
    valid_service = {
        "id": "test-service",
        "name": "test",
        "Meta": {
            "module": "icmp",
            "company": "Test",
            "project": "test",
            "env": "prod",
            "name": "test-service"
        }
    }
    
    is_valid, errors = await consul.validate_service_data(valid_service)
    print(f"\n✅ Validação serviço válido: {is_valid}, erros: {errors}")
    
    # Serviço inválido (sem campos obrigatórios)
    invalid_service = {
        "id": "test-service",
        "name": "test",
        "Meta": {}
    }
    
    is_valid2, errors2 = await consul.validate_service_data(invalid_service)
    print(f"✅ Validação serviço inválido: {is_valid2}, erros: {errors2}")
    
    return is_valid, errors, is_valid2, errors2

@pytest.mark.asyncio
async def test_baseline_check_duplicate():
    """Teste baseline: check_duplicate_service com campos hardcoded"""
    consul = ConsulManager()
    
    # Verificar duplicata (usa campos hardcoded)
    is_dup = await consul.check_duplicate_service(
        module="icmp",
        company="Test",
        project="test",
        env="prod",
        name="test-service"
    )
    
    print(f"\n✅ Verificação duplicata: {is_dup}")
    return is_dup

@pytest.mark.asyncio
async def test_baseline_id_generation():
    """Teste baseline: Como IDs são gerados atualmente"""
    # Verificar se existe função de geração de ID
    consul = ConsulManager()
    
    # ID esperado (hardcoded): module/company/project/env@name
    meta = {
        "module": "icmp",
        "company": "Test",
        "project": "test",
        "env": "prod",
        "name": "test-service"
    }
    
    # Verificar se há função de geração
    has_method = hasattr(consul, 'generate_dynamic_service_id')
    print(f"\n✅ Método generate_dynamic_service_id existe: {has_method}")
    
    if has_method:
        service_id = await consul.generate_dynamic_service_id(meta)
        print(f"✅ ID gerado: {service_id}")
    else:
        # ID hardcoded esperado
        expected_id = f"{meta['module']}/{meta['company']}/{meta['project']}/{meta['env']}@{meta['name']}"
        print(f"✅ ID esperado (hardcoded): {expected_id}")
    
    return has_method

if __name__ == "__main__":
    asyncio.run(test_baseline_required_fields())
    asyncio.run(test_baseline_validate_service_data())
    asyncio.run(test_baseline_check_duplicate())
    asyncio.run(test_baseline_id_generation())
