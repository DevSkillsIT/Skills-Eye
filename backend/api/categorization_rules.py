"""
API de Gerenciamento de Regras de Categorização

RESPONSABILIDADES:
- CRUD completo de regras de categorização
- Validação de regras (regex, prioridade, etc)
- Atualização do KV com novas regras
- Sincronização com CategorizationRuleEngine

ENDPOINTS:
- GET /api/v1/categorization-rules - Listar todas as regras
- POST /api/v1/categorization-rules - Criar nova regra
- PUT /api/v1/categorization-rules/{rule_id} - Atualizar regra
- DELETE /api/v1/categorization-rules/{rule_id} - Deletar regra

AUTOR: Sistema de Refatoração Skills Eye v2.0
DATA: 2025-11-13
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field, field_validator
from typing import Optional, Dict, Any, List
from datetime import datetime
import logging
import re

from core.consul_kv_config_manager import ConsulKVConfigManager
from core.categorization_rule_engine import CategorizationRuleEngine

router = APIRouter()
logger = logging.getLogger(__name__)

# ============================================================================
# MODELOS PYDANTIC
# ============================================================================

class RuleConditions(BaseModel):
    """Condições de matching de uma regra"""
    job_name_pattern: Optional[str] = Field(None, description="Regex para job_name")
    metrics_path: Optional[str] = Field(None, description="Path de métricas (/probe ou /metrics)")
    module_pattern: Optional[str] = Field(None, description="Regex para __param_module (blackbox)")

    @field_validator('job_name_pattern', 'module_pattern')
    @classmethod
    def validate_regex(cls, v):
        """Valida que regex é válido"""
        if v:
            try:
                re.compile(v)
            except re.error as e:
                raise ValueError(f"Regex inválido: {e}")
        return v

    @field_validator('metrics_path')
    @classmethod
    def validate_metrics_path(cls, v):
        """Valida que metrics_path é válido"""
        if v and v not in ['/probe', '/metrics']:
            raise ValueError("metrics_path deve ser '/probe' ou '/metrics'")
        return v


class CategorizationRuleModel(BaseModel):
    """Modelo de regra de categorização"""
    id: str = Field(..., description="ID único da regra", pattern=r"^[a-z0-9_]+$")
    priority: int = Field(..., description="Prioridade (1-100)", ge=1, le=100)
    category: str = Field(..., description="Categoria de destino")
    display_name: str = Field(..., description="Nome amigável para exibição")
    exporter_type: Optional[str] = Field(None, description="Tipo de exporter (opcional)")
    conditions: RuleConditions = Field(..., description="Condições de matching")


class RuleCreateRequest(BaseModel):
    """Request para criar regra"""
    id: str = Field(..., pattern=r"^[a-z0-9_]+$")
    priority: int = Field(..., ge=1, le=100)
    category: str
    display_name: str
    exporter_type: Optional[str] = None
    conditions: RuleConditions


class RuleUpdateRequest(BaseModel):
    """Request para atualizar regra (ID não pode mudar)"""
    priority: Optional[int] = Field(None, ge=1, le=100)
    category: Optional[str] = None
    display_name: Optional[str] = None
    exporter_type: Optional[str] = None
    conditions: Optional[RuleConditions] = None


# ============================================================================
# ENDPOINTS
# ============================================================================

@router.get("/")
async def get_categorization_rules():
    """
    Retorna todas as regras de categorização do KV

    Returns:
        {
            "success": true,
            "data": {
                "version": "1.0.0",
                "last_updated": "2025-11-13T10:30:00",
                "total_rules": 47,
                "rules": [...],
                "default_category": "custom-exporters",
                "categories": [...]
            }
        }
    """
    try:
        config_manager = ConsulKVConfigManager()

        # Buscar regras do KV
        rules_data = await config_manager.get('monitoring-types/categorization/rules')

        if not rules_data:
            raise HTTPException(
                status_code=404,
                detail="Regras não encontradas. Execute o script de migração primeiro."
            )

        return {
            "success": True,
            "data": rules_data
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[GET RULES ERROR] {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/")
async def create_categorization_rule(request: RuleCreateRequest):
    """
    Cria uma nova regra de categorização

    Body:
        {
            "id": "blackbox_new_module",
            "priority": 100,
            "category": "network-probes",
            "display_name": "Novo Módulo",
            "exporter_type": "blackbox",
            "conditions": {
                "job_name_pattern": "^new_module.*",
                "metrics_path": "/probe",
                "module_pattern": "^new_module$"
            }
        }

    Returns:
        {
            "success": true,
            "message": "Regra criada com sucesso",
            "rule_id": "blackbox_new_module"
        }
    """
    try:
        config_manager = ConsulKVConfigManager()

        # PASSO 1: Buscar regras atuais
        rules_data = await config_manager.get('monitoring-types/categorization/rules')

        if not rules_data:
            raise HTTPException(
                status_code=404,
                detail="Regras não encontradas. Execute o script de migração primeiro."
            )

        # PASSO 2: Verificar se ID já existe
        existing_ids = [r['id'] for r in rules_data['rules']]
        if request.id in existing_ids:
            raise HTTPException(
                status_code=409,
                detail=f"Regra com ID '{request.id}' já existe"
            )

        # PASSO 3: Criar nova regra
        new_rule = {
            "id": request.id,
            "priority": request.priority,
            "category": request.category,
            "display_name": request.display_name,
            "exporter_type": request.exporter_type,
            "conditions": request.conditions.dict(exclude_none=True)
        }

        # PASSO 4: Adicionar à lista e reordenar por prioridade
        rules_data['rules'].append(new_rule)
        rules_data['rules'].sort(key=lambda r: r['priority'], reverse=True)
        rules_data['total_rules'] = len(rules_data['rules'])
        rules_data['last_updated'] = datetime.now().isoformat()

        # PASSO 5: Salvar no KV
        success = await config_manager.put('monitoring-types/categorization/rules', rules_data)

        if not success:
            raise HTTPException(status_code=500, detail="Erro ao salvar regra no KV")

        # PASSO 6: Invalidar cache do RuleEngine
        rule_engine = CategorizationRuleEngine()
        await rule_engine.load_rules(force_reload=True)

        logger.info(f"[CREATE RULE] Regra '{request.id}' criada com sucesso")

        return {
            "success": True,
            "message": "Regra criada com sucesso",
            "rule_id": request.id
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[CREATE RULE ERROR] {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/categorization-rules/{rule_id}")
async def update_categorization_rule(rule_id: str, request: RuleUpdateRequest):
    """
    Atualiza uma regra existente

    Path:
        rule_id: ID da regra a ser atualizada

    Body:
        {
            "priority": 90,
            "display_name": "Nome Atualizado",
            "conditions": {
                "job_name_pattern": "^new_pattern.*"
            }
        }

    Returns:
        {
            "success": true,
            "message": "Regra atualizada com sucesso"
        }
    """
    try:
        config_manager = ConsulKVConfigManager()

        # PASSO 1: Buscar regras atuais
        rules_data = await config_manager.get('monitoring-types/categorization/rules')

        if not rules_data:
            raise HTTPException(
                status_code=404,
                detail="Regras não encontradas"
            )

        # PASSO 2: Encontrar regra
        rule_index = None
        for i, rule in enumerate(rules_data['rules']):
            if rule['id'] == rule_id:
                rule_index = i
                break

        if rule_index is None:
            raise HTTPException(
                status_code=404,
                detail=f"Regra '{rule_id}' não encontrada"
            )

        # PASSO 3: Atualizar campos fornecidos
        current_rule = rules_data['rules'][rule_index]

        if request.priority is not None:
            current_rule['priority'] = request.priority
        if request.category is not None:
            current_rule['category'] = request.category
        if request.display_name is not None:
            current_rule['display_name'] = request.display_name
        if request.exporter_type is not None:
            current_rule['exporter_type'] = request.exporter_type
        if request.conditions is not None:
            # Merge conditions (manter campos não fornecidos)
            for key, value in request.conditions.dict(exclude_none=True).items():
                current_rule['conditions'][key] = value

        # PASSO 4: Reordenar por prioridade
        rules_data['rules'].sort(key=lambda r: r['priority'], reverse=True)
        rules_data['last_updated'] = datetime.now().isoformat()

        # PASSO 5: Salvar no KV
        success = await config_manager.put('monitoring-types/categorization/rules', rules_data)

        if not success:
            raise HTTPException(status_code=500, detail="Erro ao salvar regra no KV")

        # PASSO 6: Invalidar cache do RuleEngine
        rule_engine = CategorizationRuleEngine()
        await rule_engine.load_rules(force_reload=True)

        logger.info(f"[UPDATE RULE] Regra '{rule_id}' atualizada com sucesso")

        return {
            "success": True,
            "message": "Regra atualizada com sucesso"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[UPDATE RULE ERROR] {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/categorization-rules/{rule_id}")
async def delete_categorization_rule(rule_id: str):
    """
    Deleta uma regra de categorização

    Path:
        rule_id: ID da regra a ser deletada

    Returns:
        {
            "success": true,
            "message": "Regra deletada com sucesso"
        }
    """
    try:
        config_manager = ConsulKVConfigManager()

        # PASSO 1: Buscar regras atuais
        rules_data = await config_manager.get('monitoring-types/categorization/rules')

        if not rules_data:
            raise HTTPException(
                status_code=404,
                detail="Regras não encontradas"
            )

        # PASSO 2: Encontrar e remover regra
        original_count = len(rules_data['rules'])
        rules_data['rules'] = [r for r in rules_data['rules'] if r['id'] != rule_id]

        if len(rules_data['rules']) == original_count:
            raise HTTPException(
                status_code=404,
                detail=f"Regra '{rule_id}' não encontrada"
            )

        # PASSO 3: Atualizar metadata
        rules_data['total_rules'] = len(rules_data['rules'])
        rules_data['last_updated'] = datetime.now().isoformat()

        # PASSO 4: Salvar no KV
        success = await config_manager.put('monitoring-types/categorization/rules', rules_data)

        if not success:
            raise HTTPException(status_code=500, detail="Erro ao salvar regras no KV")

        # PASSO 5: Invalidar cache do RuleEngine
        rule_engine = CategorizationRuleEngine()
        await rule_engine.load_rules(force_reload=True)

        logger.info(f"[DELETE RULE] Regra '{rule_id}' deletada com sucesso")

        return {
            "success": True,
            "message": "Regra deletada com sucesso"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[DELETE RULE ERROR] {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/categorization-rules/reload")
async def reload_categorization_rules():
    """
    Força recarregamento das regras do KV

    Útil após modificações manuais diretas no Consul KV.

    Returns:
        {
            "success": true,
            "message": "Regras recarregadas",
            "total_rules": 47
        }
    """
    try:
        rule_engine = CategorizationRuleEngine()
        success = await rule_engine.load_rules(force_reload=True)

        if not success:
            raise HTTPException(status_code=500, detail="Erro ao recarregar regras")

        total_rules = len(rule_engine.rules)

        logger.info(f"[RELOAD RULES] {total_rules} regras recarregadas com sucesso")

        return {
            "success": True,
            "message": "Regras recarregadas com sucesso",
            "total_rules": total_rules
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[RELOAD RULES ERROR] {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
