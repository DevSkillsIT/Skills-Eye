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
from core.kv_manager import KVManager

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


class FormSchemaField(BaseModel):
    """Campo do form_schema"""
    name: str = Field(..., description="Nome do campo")
    label: Optional[str] = Field(None, description="Label para exibição")
    type: str = Field(..., description="Tipo do campo (text, number, select, etc)")
    required: bool = Field(False, description="Campo obrigatório")
    default: Optional[Any] = Field(None, description="Valor padrão")
    placeholder: Optional[str] = Field(None, description="Placeholder")
    help: Optional[str] = Field(None, description="Texto de ajuda")
    validation: Optional[Dict[str, Any]] = Field(None, description="Regras de validação")
    options: Optional[List[Dict[str, str]]] = Field(None, description="Opções para select")
    min: Optional[float] = Field(None, description="Valor mínimo (para number)")
    max: Optional[float] = Field(None, description="Valor máximo (para number)")


class FormSchema(BaseModel):
    """Schema de formulário para exporter_type"""
    fields: Optional[List[FormSchemaField]] = Field(None, description="Campos específicos do exporter")
    required_metadata: Optional[List[str]] = Field(None, description="Campos metadata obrigatórios")
    optional_metadata: Optional[List[str]] = Field(None, description="Campos metadata opcionais")


class CategorizationRuleModel(BaseModel):
    """Modelo de regra de categorização"""
    id: str = Field(..., description="ID único da regra", pattern=r"^[a-z0-9_]+$")
    priority: int = Field(..., description="Prioridade (1-100)", ge=1, le=100)
    category: str = Field(..., description="Categoria de destino")
    display_name: str = Field(..., description="Nome amigável para exibição")
    exporter_type: Optional[str] = Field(None, description="Tipo de exporter (opcional)")
    conditions: RuleConditions = Field(..., description="Condições de matching")
    form_schema: Optional[FormSchema] = Field(None, description="Schema de formulário para este exporter_type")
    observations: Optional[str] = Field(None, description="Observações sobre a regra")


class RuleCreateRequest(BaseModel):
    """Request para criar regra"""
    id: str = Field(..., pattern=r"^[a-z0-9_]+$")
    priority: int = Field(..., ge=1, le=100)
    category: str
    display_name: str
    exporter_type: Optional[str] = None
    conditions: RuleConditions
    form_schema: Optional[FormSchema] = None
    observations: Optional[str] = None


class RuleUpdateRequest(BaseModel):
    """Request para atualizar regra (ID não pode mudar)"""
    priority: Optional[int] = Field(None, ge=1, le=100)
    category: Optional[str] = None
    display_name: Optional[str] = None
    exporter_type: Optional[str] = None
    conditions: Optional[RuleConditions] = None
    form_schema: Optional[FormSchema] = None
    observations: Optional[str] = None


# ============================================================================
# ENDPOINTS
# ============================================================================

@router.get("/categorization-rules")
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


@router.post("/categorization-rules")
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
            "conditions": request.conditions.dict(exclude_none=True),
            "form_schema": request.form_schema.dict(exclude_none=True) if request.form_schema else None,
            "observations": request.observations
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
        rule_engine = CategorizationRuleEngine(config_manager)
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
        if request.observations is not None:
            current_rule['observations'] = request.observations
        if request.form_schema is not None:
            current_rule['form_schema'] = request.form_schema.dict(exclude_none=True)
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
        rule_engine = CategorizationRuleEngine(config_manager)
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
        rule_engine = CategorizationRuleEngine(config_manager)
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
        config_manager = ConsulKVConfigManager()
        rule_engine = CategorizationRuleEngine(config_manager)
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


# ============================================================================
# ENDPOINT FORM-SCHEMA (SPRINT 1)
# ============================================================================

@router.get("/monitoring-types/form-schema")
async def get_form_schema(
    exporter_type: str = Query(..., description="Tipo de exporter (ex: blackbox, snmp_exporter, node_exporter)"),
    category: Optional[str] = Query(None, description="Categoria (opcional, para filtro)")
):
    """
    ⚠️ DEPRECATED: Este endpoint usa o método antigo de categorization/rules

    ✅ NOVO MÉTODO: Use form_schema diretamente dos tipos em /monitoring-types-dynamic/
    O form_schema agora está armazenado em skills/eye/monitoring-types (fonte única).

    SPRINT 1: Endpoint para obter form_schema das regras de categorização (LEGADO)
    
    Busca em:
    1. categorization/rules (form_schema da regra correspondente)
    2. metadata-fields (campos genéricos do KV)
    
    Args:
        exporter_type: Tipo de exporter (blackbox, snmp_exporter, node_exporter, windows_exporter, etc)
        category: Categoria opcional para filtro
    
    Returns:
        {
            "success": true,
            "exporter_type": "snmp_exporter",
            "form_schema": {
                "fields": [
                    {
                        "name": "snmp_community",
                        "label": "SNMP Community",
                        "type": "text",
                        "required": false,
                        "default": "public"
                    }
                ],
                "required_metadata": ["company", "tipo_monitoramento"],
                "optional_metadata": ["localizacao", "notas"]
            },
            "metadata_fields": [...]
        }
    
    Example:
        GET /api/v1/monitoring-types/form-schema?exporter_type=blackbox
        GET /api/v1/monitoring-types/form-schema?exporter_type=snmp_exporter&category=system-exporters
    """
    try:
        config_manager = ConsulKVConfigManager()
        kv_manager = KVManager()
        
        # PASSO 1: Buscar regra de categorização pelo exporter_type
        rules_data = await config_manager.get('monitoring-types/categorization/rules')
        
        if not rules_data:
            raise HTTPException(
                status_code=404,
                detail="Regras de categorização não encontradas no KV"
            )
        
        # Buscar regra correspondente
        rule = None
        for r in rules_data.get('rules', []):
            if r.get('exporter_type') == exporter_type:
                # Se category foi especificado, verificar se corresponde
                if category and r.get('category') != category:
                    continue
                rule = r
                break
        
        if not rule:
            # Retornar schema vazio se regra não encontrada
            logger.warning(f"[FORM-SCHEMA] Regra não encontrada para exporter_type={exporter_type}, category={category}")
            return {
                "success": True,
                "exporter_type": exporter_type,
                "form_schema": {
                    "fields": [],
                    "required_metadata": [],
                    "optional_metadata": []
                },
                "metadata_fields": []
            }
        
        # PASSO 2: Extrair form_schema da regra
        form_schema = rule.get('form_schema', {})
        
        # PASSO 3: Buscar metadata fields do KV
        metadata_fields_kv = await kv_manager.get_json('skills/eye/metadata/fields')
        metadata_fields = []
        
        if metadata_fields_kv:
            # Estrutura pode ter wrapper 'data' ou ser direta
            if 'data' in metadata_fields_kv:
                metadata_fields = metadata_fields_kv.get('data', {}).get('fields', [])
            else:
                metadata_fields = metadata_fields_kv.get('fields', [])
        
        # PASSO 4: Retornar resposta
        return {
            "success": True,
            "exporter_type": exporter_type,
            "category": rule.get('category'),
            "display_name": rule.get('display_name'),
            "form_schema": {
                "fields": form_schema.get('fields', []),
                "required_metadata": form_schema.get('required_metadata', []),
                "optional_metadata": form_schema.get('optional_metadata', [])
            },
            "metadata_fields": metadata_fields
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[FORM-SCHEMA ERROR] {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
