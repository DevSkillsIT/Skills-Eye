"""
Testes para Solução Pragmática: Form Schema em Monitoring-Types

Testa o endpoint PUT /type/{type_id}/form-schema que salva form_schema
diretamente nos tipos do KV skills/eye/monitoring-types.

Data: 2025-11-18
"""

import pytest
import asyncio
import json
import sys
from pathlib import Path

# Adicionar backend ao path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from app import app
from core.kv_manager import KVManager


@pytest.fixture(scope="function")
def kv_manager():
    """Fixture para KVManager"""
    return KVManager()


@pytest.fixture(scope="function")
def client():
    """Fixture para cliente HTTP async"""
    # Removido async - não precisa para este teste
    return None


@pytest.mark.asyncio
async def test_update_type_form_schema_success(kv_manager):
    """
    Teste 1: Atualizar form_schema de um tipo com sucesso
    """
    # PASSO 1: Verificar que KV existe
    kv_data = await kv_manager.get_json('skills/eye/monitoring-types')

    if not kv_data or not kv_data.get('all_types'):
        pytest.skip("KV monitoring-types vazio. Execute force_refresh=true primeiro.")

    # PASSO 2: Pegar primeiro tipo disponível
    first_type = kv_data['all_types'][0]
    type_id = first_type['id']

    print(f"\n✅ Testando tipo: {type_id} ({first_type.get('display_name')})")

    # PASSO 3: Criar form_schema de teste
    test_form_schema = {
        "fields": [
            {
                "name": "target",
                "label": "Alvo de Teste",
                "type": "text",
                "required": True,
                "placeholder": "192.168.1.1",
                "help": "Endereço IP ou hostname de teste"
            },
            {
                "name": "port",
                "label": "Porta",
                "type": "number",
                "required": False,
                "default": 9090,
                "min": 1,
                "max": 65535
            }
        ],
        "required_metadata": ["target"],
        "optional_metadata": ["port", "company"]
    }

    # PASSO 4: Chamar endpoint de atualização
    from api.monitoring_types_dynamic import update_type_form_schema, FormSchemaUpdateRequest

    request = FormSchemaUpdateRequest(form_schema=test_form_schema)
    response = await update_type_form_schema(type_id, request)

    # PASSO 5: Verificar resposta
    assert response['success'] == True, "Deve retornar success=True"
    assert response['type_id'] == type_id, f"Deve retornar type_id '{type_id}'"
    assert 'last_updated' in response, "Deve retornar last_updated"

    print(f"✅ Form schema atualizado com sucesso!")
    print(f"   Response: {json.dumps(response, indent=2)}")

    # PASSO 6: Verificar que foi salvo no KV
    kv_data_updated = await kv_manager.get_json('skills/eye/monitoring-types')

    # Buscar tipo atualizado
    updated_type = next(
        (t for t in kv_data_updated['all_types'] if t['id'] == type_id),
        None
    )

    assert updated_type is not None, f"Tipo '{type_id}' deve existir no KV"
    assert 'form_schema' in updated_type, "Tipo deve ter campo form_schema"
    assert updated_type['form_schema'] == test_form_schema, "Form schema deve ser igual ao enviado"

    print(f"✅ Form schema verificado no KV!")
    print(f"   Schema: {json.dumps(updated_type['form_schema'], indent=2)}")

    return True


@pytest.mark.asyncio
async def test_update_type_form_schema_tipo_nao_existe(kv_manager):
    """
    Teste 2: Tentar atualizar form_schema de tipo que não existe
    """
    from api.monitoring_types_dynamic import update_type_form_schema, FormSchemaUpdateRequest
    from fastapi import HTTPException

    # Tipo que não existe
    fake_type_id = "tipo_inexistente_xyz_123"

    request = FormSchemaUpdateRequest(form_schema={"fields": []})

    # Deve lançar HTTPException 404
    with pytest.raises(HTTPException) as exc_info:
        await update_type_form_schema(fake_type_id, request)

    assert exc_info.value.status_code == 404, "Deve retornar 404"
    assert fake_type_id in str(exc_info.value.detail).lower() or 'não encontrado' in str(exc_info.value.detail).lower()

    print(f"✅ Erro 404 retornado corretamente para tipo inexistente")

    return True


@pytest.mark.asyncio
async def test_update_type_form_schema_vazio(kv_manager):
    """
    Teste 3: Atualizar form_schema com schema vazio (remover schema)
    """
    # Buscar KV
    kv_data = await kv_manager.get_json('skills/eye/monitoring-types')

    if not kv_data or not kv_data.get('all_types'):
        pytest.skip("KV monitoring-types vazio.")

    # Pegar primeiro tipo
    first_type = kv_data['all_types'][0]
    type_id = first_type['id']

    print(f"\n✅ Testando atualização com schema vazio para: {type_id}")

    # Form schema vazio (null)
    from api.monitoring_types_dynamic import update_type_form_schema, FormSchemaUpdateRequest

    request = FormSchemaUpdateRequest(form_schema=None)
    response = await update_type_form_schema(type_id, request)

    assert response['success'] == True

    # Verificar no KV
    kv_data_updated = await kv_manager.get_json('skills/eye/monitoring-types')
    updated_type = next(
        (t for t in kv_data_updated['all_types'] if t['id'] == type_id),
        None
    )

    assert updated_type['form_schema'] is None, "Form schema deve ser None"

    print(f"✅ Form schema removido com sucesso (None)")

    return True


@pytest.mark.asyncio
async def test_form_schema_consistencia_servers(kv_manager):
    """
    Teste 4: Verificar que form_schema é atualizado em all_types E em servers[].types[]
    """
    kv_data = await kv_manager.get_json('skills/eye/monitoring-types')

    if not kv_data or not kv_data.get('all_types'):
        pytest.skip("KV monitoring-types vazio.")

    # Pegar primeiro tipo
    first_type = kv_data['all_types'][0]
    type_id = first_type['id']

    print(f"\n✅ Testando consistência para tipo: {type_id}")

    # Schema de teste
    test_schema = {
        "fields": [
            {"name": "consistency_test", "type": "text", "required": True}
        ],
        "required_metadata": ["consistency_test"]
    }

    # Atualizar
    from api.monitoring_types_dynamic import update_type_form_schema, FormSchemaUpdateRequest

    request = FormSchemaUpdateRequest(form_schema=test_schema)
    await update_type_form_schema(type_id, request)

    # Verificar consistência
    kv_data_updated = await kv_manager.get_json('skills/eye/monitoring-types')

    # 1. Verificar em all_types
    type_in_all = next(
        (t for t in kv_data_updated['all_types'] if t['id'] == type_id),
        None
    )
    assert type_in_all['form_schema'] == test_schema, "Form schema em all_types deve ser igual"

    # 2. Verificar em servers[].types[]
    for server_host, server_data in kv_data_updated.get('servers', {}).items():
        for server_type in server_data.get('types', []):
            if server_type['id'] == type_id:
                assert server_type.get('form_schema') == test_schema, \
                    f"Form schema em servers[{server_host}].types[] deve ser igual"
                print(f"✅ Consistência OK em servidor: {server_host}")

    print(f"✅ Form schema consistente em all_types e servers[]!")

    return True


@pytest.mark.asyncio
async def test_multiple_types_form_schema(kv_manager):
    """
    Teste 5: Atualizar form_schema de múltiplos tipos (não há conflito/ambiguidade)
    """
    kv_data = await kv_manager.get_json('skills/eye/monitoring-types')

    if not kv_data or len(kv_data.get('all_types', [])) < 2:
        pytest.skip("Precisa de pelo menos 2 tipos no KV.")

    # Pegar 2 tipos diferentes
    types_to_test = kv_data['all_types'][:2]

    from api.monitoring_types_dynamic import update_type_form_schema, FormSchemaUpdateRequest

    for idx, tipo in enumerate(types_to_test):
        type_id = tipo['id']

        # Schema diferente para cada tipo
        schema = {
            "fields": [
                {
                    "name": f"field_type_{idx}",
                    "label": f"Campo do Tipo {idx}",
                    "type": "text",
                    "required": True
                }
            ],
            "required_metadata": [f"field_type_{idx}"]
        }

        request = FormSchemaUpdateRequest(form_schema=schema)
        response = await update_type_form_schema(type_id, request)

        assert response['success'] == True
        print(f"✅ Tipo '{type_id}' atualizado com schema único")

    # Verificar que cada tipo tem seu próprio schema (sem ambiguidade)
    kv_data_final = await kv_manager.get_json('skills/eye/monitoring-types')

    for idx, tipo in enumerate(types_to_test):
        type_id = tipo['id']
        updated_type = next(
            (t for t in kv_data_final['all_types'] if t['id'] == type_id),
            None
        )

        # Verificar que tem o campo específico
        field_name = f"field_type_{idx}"
        assert updated_type['form_schema']['fields'][0]['name'] == field_name, \
            f"Tipo deve ter campo único '{field_name}'"

        print(f"✅ Tipo '{type_id}' mantém schema único (sem conflito)")

    print(f"✅ Múltiplos tipos com schemas únicos (SEM AMBIGUIDADE)!")

    return True


if __name__ == "__main__":
    # Executar testes
    pytest.main([__file__, "-v", "-s"])
