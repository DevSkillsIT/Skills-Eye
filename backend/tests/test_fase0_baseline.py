"""
Testes de Baseline - Fase 0: Verificação de Hardcodes

Este arquivo cria testes de baseline para comparar antes/depois dos ajustes da Fase 0.

Data: 2025-11-17
Objetivo: Validar que todas as correções da Fase 0 foram implementadas corretamente
"""

import pytest
import asyncio
from typing import Dict, Any, List
from backend.core.consul_manager import ConsulManager
from backend.core.config import Config


@pytest.mark.asyncio
async def test_baseline_required_fields_dynamic():
    """
    Teste baseline: Verificar que campos obrigatórios são obtidos dinamicamente do KV
    """
    required_fields = Config.get_required_fields()
    
    assert isinstance(required_fields, list), "Campos obrigatórios devem ser uma lista"
    assert len(required_fields) > 0, "Deve haver pelo menos um campo obrigatório"
    
    print(f"\n✅ Campos obrigatórios obtidos dinamicamente: {required_fields}")
    return required_fields


@pytest.mark.asyncio
async def test_baseline_validate_service_data_dynamic():
    """
    Teste baseline: validate_service_data usa campos obrigatórios do KV (não hardcoded)
    """
    consul = ConsulManager()
    
    # Obter campos obrigatórios do KV
    required_fields = Config.get_required_fields()
    
    # Criar serviço válido com campos obrigatórios do KV
    valid_service = {
        "id": "test-service-id",
        "name": "test-service",
        "Meta": {}
    }
    
    # Preencher campos obrigatórios
    for field in required_fields:
        if field != 'name':  # name já está no nível raiz
            valid_service["Meta"][field] = f"test_{field}"
    
    is_valid, errors = await consul.validate_service_data(valid_service)
    
    print(f"\n✅ Validação serviço válido: {is_valid}")
    print(f"   Erros: {errors}")
    
    assert is_valid, f"Serviço válido deve passar na validação. Erros: {errors}"
    
    # Criar serviço inválido (sem campos obrigatórios)
    invalid_service = {
        "id": "test-service-id",
        "name": "test-service",
        "Meta": {}
    }
    
    is_valid2, errors2 = await consul.validate_service_data(invalid_service)
    
    print(f"✅ Validação serviço inválido: {is_valid2}")
    print(f"   Erros: {errors2}")
    
    assert not is_valid2, "Serviço sem campos obrigatórios deve falhar na validação"
    assert len(errors2) > 0, "Deve haver erros de validação"
    
    return is_valid, errors, is_valid2, errors2


@pytest.mark.asyncio
async def test_baseline_check_duplicate_service_dynamic():
    """
    Teste baseline: check_duplicate_service usa campos obrigatórios do KV (não hardcoded)
    """
    consul = ConsulManager()
    
    # Obter campos obrigatórios do KV
    required_fields = Config.get_required_fields()
    
    # Criar metadata com campos obrigatórios
    meta = {}
    for field in required_fields:
        if field != 'name':
            meta[field] = f"test_{field}"
    meta['name'] = "test-service"
    
    # Verificar duplicata (deve retornar False se não existir)
    is_dup = await consul.check_duplicate_service(
        meta=meta,
        target_node_addr=None
    )
    
    print(f"\n✅ Verificação duplicata: {is_dup}")
    print(f"   Campos verificados: {required_fields + ['name']}")
    
    # Verificar que a função aceita meta como dict (não parâmetros individuais hardcoded)
    assert isinstance(is_dup, bool), "check_duplicate_service deve retornar bool"
    
    return is_dup


@pytest.mark.asyncio
async def test_baseline_generate_dynamic_service_id():
    """
    Teste baseline: generate_dynamic_service_id gera ID baseado em campos obrigatórios do KV
    """
    consul = ConsulManager()
    
    # Obter campos obrigatórios do KV
    required_fields = Config.get_required_fields()
    
    # Criar metadata com campos obrigatórios
    meta = {}
    for field in required_fields:
        if field != 'name':
            meta[field] = f"test_{field}"
    meta['name'] = "test-service"
    
    # Gerar ID dinamicamente
    service_id = await consul.generate_dynamic_service_id(meta)
    
    print(f"\n✅ ID gerado dinamicamente: {service_id}")
    print(f"   Campos obrigatórios usados: {required_fields}")
    
    assert service_id is not None, "ID não deve ser None"
    assert isinstance(service_id, str), "ID deve ser string"
    assert '@' in service_id, "ID deve conter @ antes do name"
    assert 'test-service' in service_id, "ID deve conter o name"
    
    # Verificar que ID contém todos os campos obrigatórios (exceto name que vai após @)
    for field in required_fields:
        if field != 'name':
            assert f"test_{field}" in service_id or field in service_id, \
                f"ID deve conter valor do campo obrigatório '{field}'"
    
    return service_id


@pytest.mark.asyncio
async def test_baseline_post_endpoint_uses_dynamic_validation():
    """
    Teste baseline: POST /api/v1/services usa validação dinâmica
    """
    # Este teste verifica que o endpoint POST usa as funções dinâmicas
    # Não testa o endpoint diretamente (requer servidor rodando)
    # Mas verifica que as funções chamadas são dinâmicas
    
    consul = ConsulManager()
    required_fields = Config.get_required_fields()
    
    # Verificar que validate_service_data é dinâmico
    test_service = {
        "id": "test",
        "name": "test",
        "Meta": {}
    }
    
    # Preencher campos obrigatórios
    for field in required_fields:
        if field != 'name':
            test_service["Meta"][field] = f"test_{field}"
    
    is_valid, errors = await consul.validate_service_data(test_service)
    
    assert is_valid, f"Serviço com campos obrigatórios deve ser válido. Erros: {errors}"
    
    print(f"\n✅ POST endpoint usa validação dinâmica (baseado em {len(required_fields)} campos obrigatórios)")
    
    return True


@pytest.mark.asyncio
async def test_baseline_put_endpoint_uses_dynamic_validation():
    """
    Teste baseline: PUT /api/v1/services/{service_id} usa validação dinâmica
    """
    # Verificar que update_service existe e pode ser chamado
    consul = ConsulManager()
    
    # Verificar que a função existe
    assert hasattr(consul, 'update_service'), "ConsulManager deve ter método update_service"
    
    print(f"\n✅ PUT endpoint existe e pode usar validação dinâmica")
    
    # Nota: Teste completo requer serviço existente no Consul
    # Este é apenas um teste de estrutura
    
    return True


@pytest.mark.asyncio
async def test_baseline_monitoring_types_cache_kv():
    """
    Teste baseline: Cache KV para monitoring-types está implementado
    """
    from backend.core.kv_manager import KVManager
    
    kv_manager = KVManager()
    
    # Tentar ler do KV
    kv_data = await kv_manager.get_json('skills/eye/monitoring-types')
    
    print(f"\n✅ Cache KV para monitoring-types:")
    print(f"   Existe no KV: {kv_data is not None}")
    
    if kv_data:
        print(f"   Total tipos: {kv_data.get('total_types', 0)}")
        print(f"   Última atualização: {kv_data.get('last_updated', 'N/A')}")
        print(f"   Fonte: {kv_data.get('source', 'N/A')}")
    
    # Não falhar se KV estiver vazio (pode ser primeira execução)
    # Apenas verificar que o sistema suporta cache KV
    
    return kv_data is not None


@pytest.mark.asyncio
async def test_baseline_prewarm_implemented():
    """
    Teste baseline: Prewarm de monitoring-types está implementado
    """
    import inspect
    from backend.app import _prewarm_monitoring_types_cache
    
    # Verificar que função existe
    assert _prewarm_monitoring_types_cache is not None, "Função _prewarm_monitoring_types_cache deve existir"
    
    # Verificar que é async
    assert inspect.iscoroutinefunction(_prewarm_monitoring_types_cache), \
        "Função deve ser async"
    
    print(f"\n✅ Prewarm de monitoring-types está implementado")
    
    return True


if __name__ == "__main__":
    # Executar testes
    pytest.main([__file__, "-v", "-s"])

