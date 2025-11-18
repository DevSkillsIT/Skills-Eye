"""
Testes para Sprint 1: Form Schema

Testa:
1. Endpoint GET /api/v1/monitoring-types/form-schema
2. CRUD de regras com form_schema
3. Validação de form_schema

Conforme: ANALISE_COMPLETA_CRUD_MONITORING_2025-11-17.md (Sprint 1)
"""

import pytest
import sys
from pathlib import Path

# Adicionar backend ao path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from fastapi.testclient import TestClient
from app import app

client = TestClient(app)


def test_get_form_schema_blackbox():
    """Testa obter form_schema para blackbox"""
    response = client.get("/api/v1/monitoring-types/form-schema?exporter_type=blackbox")
    
    # Endpoint pode retornar 200 mesmo se regra não tiver form_schema ainda
    assert response.status_code in [200, 404], f"Status code inesperado: {response.status_code}"
    
    if response.status_code == 404:
        pytest.skip("Regras de categorização não encontradas no KV. Execute migrate_categorization_to_json.py primeiro.")
    
    data = response.json()
    
    assert data["success"] is True
    assert data["exporter_type"] == "blackbox"
    assert "form_schema" in data
    assert "fields" in data["form_schema"]
    assert "metadata_fields" in data


def test_get_form_schema_snmp():
    """Testa obter form_schema para snmp_exporter"""
    response = client.get("/api/v1/monitoring-types/form-schema?exporter_type=snmp_exporter")
    
    assert response.status_code in [200, 404], f"Status code inesperado: {response.status_code}"
    
    if response.status_code == 404:
        pytest.skip("Regras de categorização não encontradas no KV.")
    
    data = response.json()
    
    assert data["success"] is True
    assert data["exporter_type"] == "snmp_exporter"
    assert "form_schema" in data


def test_get_form_schema_not_found():
    """Testa obter form_schema para exporter_type inexistente"""
    response = client.get("/api/v1/monitoring-types/form-schema?exporter_type=inexistente")
    
    # Endpoint retorna 200 com schema vazio se regra não encontrada (não erro 404)
    assert response.status_code in [200, 404], f"Status code inesperado: {response.status_code}"
    
    if response.status_code == 404:
        pytest.skip("Regras de categorização não encontradas no KV.")
    
    data = response.json()
    
    assert data["success"] is True
    assert data["form_schema"]["fields"] == []


def test_create_rule_with_form_schema():
    """Testa criar regra com form_schema"""
    # Limpar regra de teste se já existir
    try:
        client.delete("/api/v1/categorization-rules/test_form_schema")
    except Exception:
        pass  # Ignorar se não existir
    
    rule_data = {
        "id": "test_form_schema",
        "priority": 50,
        "category": "custom-exporters",
        "display_name": "Test Form Schema",
        "exporter_type": "test_exporter",
        "conditions": {
            "job_name_pattern": "^test.*",
            "metrics_path": "/metrics"
        },
        "form_schema": {
            "fields": [
                {
                    "name": "test_field",
                    "label": "Test Field",
                    "type": "text",
                    "required": True
                }
            ],
            "required_metadata": ["company"],
            "optional_metadata": []
        }
    }
    
    response = client.post("/api/v1/categorization-rules", json=rule_data)
    
    # Pode retornar 404 se KV não existe, ou 200 se sucesso
    if response.status_code == 404:
        pytest.skip("Regras de categorização não encontradas no KV. Execute migrate_categorization_to_json.py primeiro.")
    
    assert response.status_code == 200, f"Erro ao criar regra: {response.text}"
    data = response.json()
    
    assert data["success"] is True
    assert data["rule_id"] == "test_form_schema"
    
    # Verificar se regra foi criada com form_schema
    get_response = client.get("/api/v1/categorization-rules")
    assert get_response.status_code == 200
    rules_data = get_response.json()
    
    rule = next((r for r in rules_data["data"]["rules"] if r["id"] == "test_form_schema"), None)
    assert rule is not None, "Regra não foi encontrada após criação"
    assert "form_schema" in rule, "Regra criada sem form_schema"
    assert rule["form_schema"]["fields"][0]["name"] == "test_field"
    
    # Limpar: deletar regra de teste
    try:
        client.delete(f"/api/v1/categorization-rules/test_form_schema")
    except Exception:
        pass  # Ignorar erro se já foi deletado


def test_update_rule_with_form_schema():
    """Testa atualizar regra adicionando form_schema"""
    # Limpar regra de teste se já existir
    try:
        client.delete("/api/v1/categorization-rules/test_update_form_schema")
    except Exception:
        pass  # Ignorar se não existir
    
    # Criar regra sem form_schema
    rule_data = {
        "id": "test_update_form_schema",
        "priority": 50,
        "category": "custom-exporters",
        "display_name": "Test Update Form Schema",
        "exporter_type": "test_exporter",
        "conditions": {
            "job_name_pattern": "^test.*",
            "metrics_path": "/metrics"
        }
    }
    
    create_response = client.post("/api/v1/categorization-rules", json=rule_data)
    
    if create_response.status_code == 404:
        pytest.skip("Regras de categorização não encontradas no KV.")
    
    assert create_response.status_code == 200, f"Erro ao criar regra: {create_response.text}"
    
    # Atualizar adicionando form_schema
    update_data = {
        "form_schema": {
            "fields": [
                {
                    "name": "updated_field",
                    "label": "Updated Field",
                    "type": "text",
                    "required": False
                }
            ]
        }
    }
    
    update_response = client.put("/api/v1/categorization-rules/test_update_form_schema", json=update_data)
    assert update_response.status_code == 200, f"Erro ao atualizar regra: {update_response.text}"
    
    # Verificar se form_schema foi adicionado
    get_response = client.get("/api/v1/categorization-rules")
    assert get_response.status_code == 200
    rules_data = get_response.json()
    
    rule = next((r for r in rules_data["data"]["rules"] if r["id"] == "test_update_form_schema"), None)
    assert rule is not None, "Regra não foi encontrada após atualização"
    assert "form_schema" in rule, "Regra atualizada sem form_schema"
    assert rule["form_schema"]["fields"][0]["name"] == "updated_field"
    
    # Limpar
    try:
        client.delete("/api/v1/categorization-rules/test_update_form_schema")
    except Exception:
        pass  # Ignorar erro se já foi deletado


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

