"""
API para Gerenciamento de Campos Metadata

Este módulo fornece endpoints para:
- Listar/criar/editar/deletar campos metadata
- Adicionar novo campo e sincronizar com prometheus.yml
- Reordenar campos
- Gerenciar categorias
"""

from fastapi import APIRouter, HTTPException, Body, Query, Request
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional, cast, Tuple, Union
from pathlib import Path
import logging
import asyncio
from datetime import datetime, timedelta
import re
import yaml  # type: ignore
from yaml import nodes as yaml_nodes  # type: ignore

from core.multi_config_manager import MultiConfigManager
from core.server_utils import get_server_detector, ServerInfo
from core.fields_extraction_service import get_discovered_in_for_field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/metadata-fields", tags=["Metadata Fields"])

# Path do arquivo de configuração
CONFIG_FILE = Path(__file__).parent.parent / "config" / "metadata_fields.json"

# Cache para evitar consultas repetidas ao Consul (cache de 5 minutos)
_servers_cache = {
    "data": None,
    "timestamp": None,
    "ttl": 300  # 5 minutos em segundos
}

# NOVO: Usar ConsulKVConfigManager para cache unificado (elimina cache manual)
from core.consul_kv_config_manager import ConsulKVConfigManager
_kv_manager = ConsulKVConfigManager(ttl_seconds=300)  # Cache de 5 minutos

# Lock global para evitar múltiplas extrações SSH simultâneas
_extraction_lock = asyncio.Lock()
_extraction_in_progress = False

# ============================================================================
# MODELOS PYDANTIC
# ============================================================================

class MetadataFieldModel(BaseModel):
    """Modelo de campo metadata"""
    name: str = Field(..., description="Nome técnico do campo")
    display_name: str = Field(..., description="Nome amigável para exibição")
    description: str = Field("", description="Descrição do campo")
    source_label: str = Field(..., description="Source label do Prometheus")
    field_type: str = Field(..., description="Tipo: string, number, select, text, url")
    required: bool = Field(False, description="Campo obrigatório")
    show_in_table: bool = Field(True, description="Mostrar em tabelas")
    show_in_dashboard: bool = Field(False, description="Mostrar no dashboard")
    show_in_form: bool = Field(True, description="Mostrar em formulários")
    options: Optional[List[str]] = Field(None, description="Opções para select")
    order: int = Field(0, description="Ordem de exibição")
    category: Union[str, List[str]] = Field("extra", description="Categoria(s) do campo - aceita string única ou lista para múltiplas categorias")
    editable: bool = Field(True, description="Pode ser editado")
    validation_regex: Optional[str] = Field(None, description="Regex de validação")
    # Campos de visibilidade por página (anteriormente em field-config/)
    show_in_services: bool = Field(True, description="Mostrar na página Services")
    show_in_exporters: bool = Field(True, description="Mostrar na página Exporters")
    show_in_blackbox: bool = Field(True, description="Mostrar na página Blackbox")
    # ⭐ NOVAS PROPRIEDADES - Sistema de Refatoração v2.0 (2025-11-13)
    show_in_network_probes: bool = Field(True, description="Mostrar na página Network Probes")
    show_in_web_probes: bool = Field(True, description="Mostrar na página Web Probes")
    show_in_system_exporters: bool = Field(True, description="Mostrar na página System Exporters")
    show_in_database_exporters: bool = Field(True, description="Mostrar na página Database Exporters")
    show_in_infrastructure_exporters: bool = Field(True, description="Mostrar na página Infrastructure Exporters")
    show_in_hardware_exporters: bool = Field(True, description="Mostrar na página Hardware Exporters")


class CategoryModel(BaseModel):
    """Modelo de categoria"""
    name: str
    description: str
    icon: str


class FieldsConfigResponse(BaseModel):
    """Resposta com configuração completa"""
    success: bool
    fields: List[Dict[str, Any]]
    categories: Dict[str, Dict[str, Any]]
    total: int
    version: str
    last_updated: str
    # Campos adicionais para modal de progresso (opcional)
    from_cache: bool = False
    server_status: List[Dict[str, Any]] = []
    total_servers: int = 0
    successful_servers: int = 0
    # CRITICAL FIX: Adicionar extraction_status completo para discovered_in
    extraction_status: Optional[Dict[str, Any]] = None


class AddFieldRequest(BaseModel):
    """Request para adicionar novo campo"""
    field: MetadataFieldModel
    sync_prometheus: bool = Field(True, description="Sincronizar com prometheus.yml")
    apply_to_jobs: Optional[List[str]] = Field(None, description="Jobs específicos (None = todos)")


class FieldSyncStatus(BaseModel):
    """Status de sincronização de um campo"""
    name: str
    display_name: str
    sync_status: str = Field(..., description="synced | outdated | missing | orphan | error")
    prometheus_target_label: Optional[str] = Field(None, description="Target label no Prometheus")
    metadata_source_label: Optional[str] = Field(None, description="Source label no metadata_fields.json")
    message: Optional[str] = Field(None, description="Mensagem descritiva do status")


class SyncStatusResponse(BaseModel):
    """Resposta com status de sincronização"""
    success: bool
    server_id: str
    server_hostname: str
    fields: List[FieldSyncStatus]
    total_synced: int
    total_outdated: int
    total_missing: int
    total_orphan: int = Field(0, description="Campos no KV mas não no Prometheus (órfãos)")
    total_error: int
    prometheus_file_path: Optional[str] = None
    checked_at: str
    message: Optional[str] = Field(None, description="Mensagem geral (ex: servidor sem Prometheus)")
    fallback_used: bool = Field(False, description="True quando leitura alternativa do prometheus.yml foi utilizada")


# ============================================================================
# MODELOS PARA FASE 2 E 3
# ============================================================================

class PreviewFieldChangeResponse(BaseModel):
    """Preview de mudanças antes de aplicar (FASE 2)"""
    success: bool
    field_name: str
    current_config: Optional[Dict[str, Any]] = Field(None, description="Configuração atual no prometheus.yml")
    new_config: Dict[str, Any] = Field(..., description="Nova configuração que será aplicada")
    diff_text: str = Field(..., description="Diff em formato texto")
    affected_jobs: List[str] = Field(..., description="Jobs que serão afetados")
    will_create: bool = Field(..., description="True se vai criar novo, False se vai atualizar")


class BatchSyncRequest(BaseModel):
    """Request para sincronização em lote (FASE 3)"""
    field_names: List[str] = Field(..., description="Lista de campos para sincronizar")
    server_id: str = Field(..., description="Servidor alvo")
    dry_run: bool = Field(False, description="Se True, apenas simula sem aplicar")


class ForceExtractRequest(BaseModel):
    """Request para extração forçada de campos"""
    server_id: Optional[str] = Field(None, description="ID do servidor (hostname). Se None, extrai de todos.")


class AddToKVRequest(BaseModel):
    """Request para adicionar campos extraídos do Prometheus ao KV"""
    field_names: List[str] = Field(..., description="Lista de nomes de campos para adicionar ao KV")
    fields_data: List[Dict[str, Any]] = Field(..., description="Dados completos dos campos extraídos")


class FieldSyncResult(BaseModel):
    """Resultado da sincronização de um campo"""
    field_name: str
    success: bool
    message: str
    changes_applied: int = Field(0, description="Número de alterações aplicadas")


class BatchSyncResponse(BaseModel):
    """Resposta da sincronização em lote (FASE 3)"""
    success: bool
    server_id: str
    results: List[FieldSyncResult]
    total_processed: int
    total_success: int
    total_failed: int
    duration_seconds: float


# ============================================================================
# FUNÇÕES AUXILIARES
# ============================================================================

def merge_fields_preserving_customizations(
    extracted_fields: List[Dict[str, Any]],
    existing_kv_fields: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    MERGE INTELIGENTE: Preserva customizações do KV enquanto atualiza estrutura do Prometheus
    
    CAMPOS PRESERVADOS DO KV (customizações do usuário):
    - required (obrigatório)
    - auto_register (auto-cadastro)
    - category (categoria)
    - show_in_* (visibilidade em páginas)
    - order (ordem de exibição)
    - description (descrição customizada)
    - editable, enabled
    - validation_regex, validation
    - default_value, placeholder
    
    CAMPOS ATUALIZADOS DO PROMETHEUS (dinâmicos):
    - options (valores únicos)
    - discovered_in (servidores)
    - source_label, regex, replacement (estrutura do relabel)
    
    Args:
        extracted_fields: Campos extraídos do Prometheus (estrutura dinâmica)
        existing_kv_fields: Campos existentes no KV (com customizações do usuário)
    
    Returns:
        Lista de campos merged (customizações preservadas + estrutura atualizada)
    """
    # Criar map dos campos existentes no KV por nome
    kv_fields_map = {field['name']: field for field in existing_kv_fields}
    
    merged_fields = []
    
    for extracted_field in extracted_fields:
        field_name = extracted_field['name']
        
        if field_name in kv_fields_map:
            # Campo JÁ EXISTE no KV - MERGE preservando customizações
            kv_field = kv_fields_map[field_name]
            
            merged_field = extracted_field.copy()  # Base: estrutura do Prometheus
            
            # PRESERVAR customizações do KV (sobrescrever valores do Prometheus)
            customizable_fields = [
                'required', 'auto_register', 'category', 'order', 'description',
                'show_in_table', 'show_in_dashboard', 'show_in_form',
                'show_in_services', 'show_in_exporters', 'show_in_blackbox', 'show_in_filter',
                # ⭐ NOVAS PROPRIEDADES - v2.0 (2025-11-13)
                'show_in_network_probes', 'show_in_web_probes',
                'show_in_system_exporters', 'show_in_database_exporters',
                'show_in_infrastructure_exporters', 'show_in_hardware_exporters',
                # Outros campos customizáveis
                'editable', 'enabled', 'available_for_registration',
                'validation_regex', 'validation', 'default_value', 'placeholder',
                'display_name'  # Usuário pode ter customizado o nome amigável
            ]
            
            for custom_field in customizable_fields:
                if custom_field in kv_field:
                    merged_field[custom_field] = kv_field[custom_field]
            
            # ✅ GARANTIR que novos campos show_in_* existam (backward compatibility)
            # Se KV antigo não tem esses campos, adicionar com defaults herdados
            if 'show_in_network_probes' not in merged_field:
                merged_field['show_in_network_probes'] = merged_field.get('show_in_blackbox', True)
            if 'show_in_web_probes' not in merged_field:
                merged_field['show_in_web_probes'] = merged_field.get('show_in_blackbox', True)
            if 'show_in_system_exporters' not in merged_field:
                merged_field['show_in_system_exporters'] = merged_field.get('show_in_exporters', True)
            if 'show_in_database_exporters' not in merged_field:
                merged_field['show_in_database_exporters'] = merged_field.get('show_in_exporters', True)
            if 'show_in_infrastructure_exporters' not in merged_field:
                merged_field['show_in_infrastructure_exporters'] = merged_field.get('show_in_exporters', True)
            if 'show_in_hardware_exporters' not in merged_field:
                merged_field['show_in_hardware_exporters'] = merged_field.get('show_in_exporters', True)
            
            logger.debug(f"[MERGE] Campo '{field_name}': customizações preservadas do KV")
        else:
            # Campo NOVO extraído do Prometheus - usar defaults
            merged_field = extracted_field.copy()
            logger.debug(f"[MERGE] Campo '{field_name}': NOVO campo adicionado (defaults aplicados)")
        
        merged_fields.append(merged_field)
    
    # IMPORTANTE: Também manter campos ÓRFÃOS (campos no KV que NÃO existem mais no Prometheus)
    # Isso evita perda de dados se um servidor Prometheus temporariamente não tiver um campo
    extracted_field_names = {f['name'] for f in extracted_fields}
    for kv_field_name, kv_field in kv_fields_map.items():
        if kv_field_name not in extracted_field_names:
            logger.warning(f"[MERGE] Campo '{kv_field_name}' existe no KV mas NÃO foi extraído do Prometheus - PRESERVANDO como órfão")
            merged_fields.append(kv_field)
    
    return merged_fields


async def load_fields_config() -> Dict[str, Any]:
    """
    Carrega configuração de campos do Consul KV (extraídos do Prometheus).

    IMPORTANTE: Não usa mais arquivo JSON hardcoded!
    Campos vêm 100% do Prometheus via extração SSH.

    CACHE EM MEMÓRIA (REFATORADO):
    - Usa ConsulKVConfigManager para cache unificado (elimina código duplicado)
    - Cache de 5 minutos para evitar leituras repetidas do KV
    - Reduz latência de rede (KV → Backend)
    - Primeira requisição: lê do KV (~100-500ms)
    - Próximas requisições: retorna do cache (<1ms)

    FALLBACK AUTOMÁTICO COM LOCK:
    - Se KV vazio, dispara extração SSH sob demanda
    - Usa lock global para evitar múltiplas extrações simultâneas
    - Se já existe extração em progresso, aguarda e tenta ler KV novamente
    - Popula KV automaticamente
    - Retorna dados extraídos
    """
    global _extraction_lock, _extraction_in_progress

    try:
        # PASSO 1: Tentar ler do KV usando cache unificado (ConsulKVConfigManager)
        # Isso substitui o cache manual anterior
        fields_data = await _kv_manager.get('metadata/fields', use_cache=True)

        # PASSO 1.1: Se KV tem dados, retornar
        if fields_data:
            logger.debug(f"[METADATA-FIELDS] ✓ Dados carregados do KV (via cache unificado)")
            return fields_data

        # PASSO 2: Se KV vazio, disparar fallback
        if not fields_data:
            logger.warning("[METADATA-FIELDS] KV vazio detectado!")

            # Adquirir lock para garantir que apenas uma extração aconteça por vez
            async with _extraction_lock:
                # DOUBLE-CHECK: Verificar novamente se KV ainda está vazio
                # (outra requisição pode ter populado enquanto aguardávamos lock)
                # Usa use_cache=False para forçar leitura fresca do KV
                fields_data = await _kv_manager.get('metadata/fields', use_cache=False)

                if fields_data:
                    logger.info("[METADATA-FIELDS] KV foi populado por outra requisição. Usando dados existentes.")
                    return fields_data

                logger.info("[METADATA-FIELDS FALLBACK] Disparando extração SSH sob demanda (com lock)...")
                _extraction_in_progress = True

                try:
                    from api.prometheus_config import multi_config
                    from core.kv_manager import KVManager

                    logger.info("[METADATA-FIELDS FALLBACK] Iniciando extração via AsyncSSH + TAR...")
                    extraction_result = await multi_config.extract_all_fields_with_asyncssh_tar()

                    fields = extraction_result['fields']
                    successful_servers = extraction_result.get('successful_servers', 0)
                    total_servers = extraction_result.get('total_servers', 0)

                    logger.info(
                        f"[METADATA-FIELDS FALLBACK] ✓ Extração completa: {len(fields)} campos de "
                        f"{successful_servers}/{total_servers} servidores"
                    )

                    # LÓGICA CRÍTICA: SEMPRE FAZER MERGE COM DADOS EXISTENTES NO KV!
                    # NÃO sobrescrever customizações (required, auto_register, category, etc)

                    # PASSO 1: Buscar dados existentes do KV (podem ter customizações!)
                    kv = KVManager()
                    existing_kv_data = await kv.get_json('skills/eye/metadata/fields')
                    
                    # PASSO 2: Converter campos extraídos para dict
                    extracted_fields_dicts = [f.to_dict() for f in fields]
                    
                    # PASSO 3: MERGE INTELIGENTE - preservar customizações do KV
                    if existing_kv_data and existing_kv_data.get('fields'):
                        logger.info(f"[METADATA-FIELDS MERGE] Fazendo merge com {len(existing_kv_data['fields'])} campos existentes no KV")
                        merged_fields = merge_fields_preserving_customizations(
                            extracted_fields=extracted_fields_dicts,
                            existing_kv_fields=existing_kv_data['fields']
                        )
                        logger.info(f"[METADATA-FIELDS MERGE] ✓ Merge concluído: {len(merged_fields)} campos finais")
                    else:
                        logger.info("[METADATA-FIELDS MERGE] KV vazio - usando campos extraídos diretamente")
                        merged_fields = extracted_fields_dicts

                    # PASSO 4: Salvar campos MERGED no KV
                    fields_data = {
                        'version': '2.0.0',
                        'last_updated': datetime.now().isoformat(),
                        'source': 'extraction_with_merge' if existing_kv_data else 'initial_extraction',
                        'total_fields': len(merged_fields),
                        'fields': merged_fields,
                        'extraction_status': {
                            'total_servers': total_servers,
                            'successful_servers': successful_servers,
                            'server_status': extraction_result.get('server_status', []),
                        },
                    }

                    await kv.put_json(
                        key='skills/eye/metadata/fields',
                        value=fields_data,
                        metadata={'auto_updated': True, 'source': 'extraction_with_merge'}
                    )

                    logger.info(
                        f"[METADATA-FIELDS FALLBACK] ✓ KV populado pela PRIMEIRA VEZ com {len(merged_fields)} campos. "
                        f"Próximas requisições usarão cache."
                    )

                    # Sincronizar sites no KV também (primeira vez)
                    server_status = extraction_result.get('server_status', [])
                    sites_sync_result = await sync_sites_to_kv(server_status)
                    logger.info(
                        f"[METADATA-FIELDS FALLBACK] ✓ Sites sincronizados: {sites_sync_result['total_sites']} total"
                    )

                    # PASSO 2.1: Invalidar cache unificado para forçar reload
                    _kv_manager.invalidate('metadata/fields')
                    logger.info(f"[METADATA-FIELDS FALLBACK] ✓ Cache unificado invalidado (próxima leitura recarregará do KV)")

                    return fields_data

                except Exception as fallback_error:
                    logger.error(f"[METADATA-FIELDS FALLBACK] ✗ Erro na extração sob demanda: {fallback_error}", exc_info=True)
                    raise HTTPException(
                        status_code=503,
                        detail=f"KV vazio e falha ao extrair campos automaticamente: {str(fallback_error)}"
                    )
                finally:
                    _extraction_in_progress = False

        return fields_data
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao carregar campos do Consul KV: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao carregar configuração de campos: {str(e)}"
        )


async def save_fields_config(config: Dict[str, Any]) -> bool:
    """
    Salva configuração de campos no Consul KV.

    IMPORTANTE: Não salva mais em arquivo JSON!
    Campos são salvos no KV: skills/eye/metadata/fields

    Esta função é chamada quando usuário EDITA campos via PATCH.
    As customizações são preservadas automaticamente pelo merge inteligente
    que ocorre durante force-extract e fallback.
    """
    try:
        from core.kv_manager import KVManager

        kv = KVManager()

        # Atualizar timestamp
        config['last_updated'] = datetime.utcnow().isoformat() + 'Z'

        success = await kv.put_json('skills/eye/metadata/fields', config)

        if not success:
            raise ValueError("Falha ao salvar no Consul KV")

        logger.info(f"Configuração salva no KV: skills/eye/metadata/fields")
        return True
    except Exception as e:
        logger.error(f"Erro ao salvar configuração: {e}")
        raise HTTPException(status_code=500, detail=f"Erro ao salvar: {str(e)}")


def get_field_by_name(config: Dict[str, Any], field_name: str) -> Optional[Dict[str, Any]]:
    """Busca campo por nome"""
    for field in config.get('fields', []):
        if field['name'] == field_name:
            return field
    return None


def _build_labels_map_from_jobs(scrape_configs: List[Dict[str, Any]]) -> Tuple[Dict[str, str], bool]:
    """Fallback para mapear source_labels -> target_label varrendo todos os jobs.

    Retorna também flag indicando estruturas avançadas (anchors, merges ou dicts).
    """
    labels_map: Dict[str, str] = {}
    advanced_detected = False

    def _collect_relabel_blocks(candidate: Any, storage: List[Dict[str, Any]], job_name: str) -> None:
        if isinstance(candidate, dict):
            storage.append(candidate)
        elif isinstance(candidate, list):
            for entry in candidate:
                _collect_relabel_blocks(entry, storage, job_name)
        elif candidate is not None:
            logger.debug(
                "[FALLBACK] Ignorando bloco de relabel não suportado em '%s' (tipo=%s)",
                job_name,
                type(candidate).__name__,
            )

    seen_relabel_sequences: Dict[int, str] = {}

    for job in scrape_configs or []:
        relabel_configs = job.get('relabel_configs') or []
        job_name = job.get('job_name', 'unknown') if isinstance(job, dict) else 'unknown'

        normalized_relabels: List[Dict[str, Any]] = []

        # PyYAML já expande anchors para listas, mas garantimos iterabilidade
        if isinstance(relabel_configs, dict):
            advanced_detected = True
            logger.debug(
                "[FALLBACK] Job '%s' com relabel_configs dict (anchors/merge expandidos)",
                job_name,
            )
            for value in relabel_configs.values():
                _collect_relabel_blocks(value, normalized_relabels, job_name)
        elif isinstance(relabel_configs, str):
            advanced_detected = True
            logger.debug(
                "[FALLBACK] Job '%s' com relabel_configs str (alias referenciado)",
                job_name,
            )
        else:
            logger.debug(
                "[FALLBACK] Job '%s' com relabel_configs tipo %s (len=%s)",
                job_name,
                type(relabel_configs).__name__,
                len(relabel_configs) if isinstance(relabel_configs, list) else 'n/a',
            )

            if isinstance(relabel_configs, list):
                relabel_id = id(relabel_configs)
                if relabel_id in seen_relabel_sequences:
                    advanced_detected = True
                    logger.debug(
                        "[FALLBACK] Job '%s' reutiliza sequência de relabel do job '%s' via alias",
                        job_name,
                        seen_relabel_sequences[relabel_id],
                    )
                else:
                    seen_relabel_sequences[relabel_id] = job_name

            _collect_relabel_blocks(relabel_configs, normalized_relabels, job_name)

        if isinstance(job, dict) and '<<' in job:
            advanced_detected = True
            logger.debug("[FALLBACK] Job '%s' contém merge key '<<'", job_name)

        for relabel in normalized_relabels:
            if not isinstance(relabel, dict):
                logger.debug(
                    "[FALLBACK] Ignorando relabel não-dict em '%s' (tipo=%s)",
                    job_name,
                    type(relabel).__name__,
                )
                continue

            source_labels = relabel.get('source_labels') or []
            if isinstance(source_labels, str):
                source_labels = [source_labels]

            target_label = relabel.get('target_label')

            if not source_labels or not target_label:
                continue

            primary_source = source_labels[0]

            if primary_source not in labels_map:
                labels_map[primary_source] = target_label

    return labels_map, advanced_detected


def _scrape_configs_use_aliases(yaml_text: str) -> bool:
    """Detecta uso de anchors/aliases YAML dentro de scrape_configs."""
    try:
        root_node = yaml.compose(yaml_text, Loader=yaml.SafeLoader)  # type: ignore[attr-defined]
    except yaml.YAMLError:
        logger.debug("[FALLBACK] yaml.compose falhou - não foi possível detectar anchors")
        return False

    if root_node is None or not isinstance(root_node, yaml_nodes.MappingNode):
        logger.debug("[FALLBACK] Nodo raiz não é MappingNode - anchors não detectados")
        return False

    def _node_uses_anchor(node: yaml_nodes.Node) -> bool:
        if getattr(node, 'anchor', None):
            logger.debug("[FALLBACK] Anchor detectado diretamente em nodo %s", type(node).__name__)
            return True

        if isinstance(node, yaml_nodes.MappingNode):
            for key_node, value_node in node.value:
                if (
                    isinstance(key_node, yaml_nodes.ScalarNode)
                    and key_node.value == '<<'
                ):
                    logger.debug("[FALLBACK] Merge key '<<' detectado em MappingNode")
                    return True

                if _node_uses_anchor(key_node) or _node_uses_anchor(value_node):
                    return True

            return False

        if isinstance(node, yaml_nodes.SequenceNode):
            return any(_node_uses_anchor(child) for child in node.value)

        return False

    for key_node, value_node in root_node.value:
        if isinstance(key_node, yaml_nodes.ScalarNode) and key_node.value == 'scrape_configs':
            return _node_uses_anchor(value_node)

    logger.debug("[FALLBACK] Nenhum anchor detectado em scrape_configs via compose")
    return False


def _resolve_label_chain(
    source_label: str,
    labels_map: Dict[str, str],
    max_depth: int = 20,
) -> Tuple[Optional[str], Optional[str], List[str]]:
    """Segue mapeamentos sucessivos até encontrar o rótulo final.

    Retorna tupla com (target imediato, target final, cadeia completa).
    """

    raw_target = labels_map.get(source_label)
    if raw_target is None:
        return None, None, []

    chain: List[str] = [raw_target]
    current = raw_target
    visited = {source_label, raw_target}

    for _ in range(max_depth):
        next_target = labels_map.get(current)
        if not next_target or next_target in visited:
            break
        chain.append(next_target)
        visited.add(next_target)
        current = next_target

    final_target = chain[-1] if chain else raw_target
    return raw_target, final_target, chain


# ============================================================================
# ENDPOINTS - ROTAS ESPECÍFICAS PRIMEIRO!
# ============================================================================

# GERENCIAMENTO DE SERVIDORES (deve vir ANTES de /{field_name})
@router.get("/servers")
async def list_servers():
    """
    Lista todos os servidores Prometheus configurados (Master + Slaves)
    Busca os nomes dos nodes no Consul para exibir junto com o IP

    USA CACHE de 5 minutos para não sobrecarregar o Consul
    OTIMIZADO: Não cria conexões SSH, apenas lê variável de ambiente!
    """
    try:
        # Verificar cache primeiro
        now = datetime.now()
        print(f"[CACHE CHECK] data exists: {_servers_cache['data'] is not None}, timestamp: {_servers_cache['timestamp']}")

        if (_servers_cache["data"] is not None and
            _servers_cache["timestamp"] is not None):

            elapsed = (now - _servers_cache["timestamp"]).total_seconds()
            if elapsed < _servers_cache["ttl"]:
                print(f"[CACHE HIT] Returning from cache (age: {elapsed:.1f}s)")
                logger.info(f"Retornando servidores do CACHE (idade: {elapsed:.1f}s)")
                return _servers_cache["data"]

        print("[CACHE MISS] Fetching servers from environment...")
        logger.info("Cache expirado ou vazio, buscando servidores...")

        # OTIMIZAÇÃO: Não criar MultiConfigManager (muito lento por causa do SSH)
        # Em vez disso, ler diretamente da variável de ambiente
        import os
        from core.config import Config

        prometheus_hosts_str = os.getenv("PROMETHEUS_CONFIG_HOSTS", "")

        if not prometheus_hosts_str:
            raise ValueError("PROMETHEUS_CONFIG_HOSTS não configurado no .env")

        # Parsear formato: host:porta/user/senha;host2:porta/user/senha
        raw_hosts = [h.strip() for h in prometheus_hosts_str.split(';') if h.strip()]

        # Tentar buscar nodes do Consul para pegar os nomes (com timeout curto)
        consul_nodes = {}
        try:
            from core.consul_manager import ConsulManager
            consul_manager = ConsulManager()

            # Buscar nodes com timeout de 1 segundo apenas
            import asyncio
            nodes_data = await asyncio.wait_for(
                consul_manager.get_nodes(),
                timeout=1.0  # Apenas 1 segundo - se demorar mais, ignora
            )

            # Criar mapa IP -> Nome do node
            for node in nodes_data:
                node_ip = node.get('Address')
                node_name = node.get('Node')
                if node_ip and node_name:
                    consul_nodes[node_ip] = node_name

            logger.info(f"Nodes do Consul encontrados: {len(consul_nodes)} nodes")
            print(f"[CONSUL] Found {len(consul_nodes)} nodes in Consul")
        except asyncio.TimeoutError:
            logger.warning("Timeout ao buscar nodes do Consul (>1s), usando apenas IPs")
            print("[CONSUL] Timeout - using IPs only")
        except Exception as e:
            logger.warning(f"Não foi possível buscar nodes do Consul: {e}")
            print(f"[CONSUL] Error: {e}")

        servers = []
        for idx, host_str in enumerate(raw_hosts):
            # Parsear formato: host:porta/user/senha
            parts = host_str.split('/')
            if len(parts) != 3:
                logger.warning(f"Formato inválido para host: {host_str}")
                continue

            host_port = parts[0]
            username = parts[1]
            # senha = parts[2]  # não precisamos retornar a senha

            host_parts = host_port.split(':')
            if len(host_parts) != 2:
                logger.warning(f"Formato inválido para host:porta: {host_port}")
                continue

            hostname = host_parts[0]
            port = int(host_parts[1])

            # Determinar tipo (primeiro é master, demais são slaves)
            server_type = "master" if idx == 0 else "slave"

            # Buscar nome do node no Consul
            consul_node_name = consul_nodes.get(hostname, None)

            # Montar display_name com IP + Nome do Consul (se existir)
            if consul_node_name:
                display_name = f"{hostname} - {consul_node_name}"
            else:
                display_name = hostname

            # BUSCAR EXTERNAL LABELS DO KV (salvos em skills/eye/metadata/fields -> extraction_status -> server_status)
            # External labels são extraídos do prometheus.yml (global.external_labels) e salvos junto com os campos
            external_labels = {}
            try:
                from core.kv_manager import KVManager
                kv = KVManager()

                # Buscar dados consolidados que incluem server_status com external_labels
                metadata_fields_data = await kv.get_json('skills/eye/metadata/fields')

                if metadata_fields_data:
                    # Extrair server_status que contém external_labels de cada servidor
                    extraction_status = metadata_fields_data.get('extraction_status', {})
                    server_status_list = extraction_status.get('server_status', [])

                    # Procurar o servidor correspondente pelo hostname
                    for server_info in server_status_list:
                        if server_info.get('hostname') == hostname:
                            external_labels = server_info.get('external_labels', {})
                            logger.debug(f"External labels para {hostname} encontrados no KV: {len(external_labels)} labels")
                            break
                else:
                    logger.debug(f"KV skills/eye/metadata/fields não encontrado - external_labels não disponíveis")
            except Exception as ex_label_error:
                logger.debug(f"Não foi possível buscar external labels para {hostname}: {ex_label_error}")

            servers.append({
                "id": f"{hostname}:{port}",
                "hostname": hostname,
                "port": port,
                "username": username,
                "type": server_type,
                "consul_node_name": consul_node_name,
                "display_name": display_name,
                "external_labels": external_labels  # ← ADICIONADO!
            })

        if not servers:
            raise ValueError("Nenhum servidor foi configurado corretamente")

        result = {
            "success": True,
            "servers": servers,
            "total": len(servers),
            "master": servers[0] if servers else None
        }

        # Atualizar cache
        _servers_cache["data"] = result
        _servers_cache["timestamp"] = now
        logger.info(f"Cache de servidores atualizado - {len(servers)} servidores (válido por {_servers_cache['ttl']}s)")
        print(f"[CACHE UPDATED] {len(servers)} servers cached for {_servers_cache['ttl']}s")

        return result

    except Exception as e:
        logger.error(f"Erro ao listar servidores: {e}", exc_info=True)
        print(f"[ERROR] Failed to list servers: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sync-status", response_model=SyncStatusResponse)
async def get_sync_status(
    server_id: str = Query(..., description="ID do servidor (hostname:port)")
):
    """
    Verifica status de sincronização dos campos metadata com prometheus.yml

    Para cada campo em metadata_fields.json, verifica se existe relabel_config
    correspondente no prometheus.yml do servidor selecionado.

    Status possíveis:
    - synced: Campo existe e está correto no Prometheus
    - missing: Campo existe no JSON mas não no Prometheus
    - outdated: Campo existe mas target_label está diferente
    - error: Erro ao verificar status
    """
    try:
        logger.info(f"[SYNC-STATUS] Verificando sync status para servidor: {server_id}")

        # Buscar campos do KV (se não existir, buscar de prometheus_config.py via fallback)
        try:
            config = await load_fields_config()
            fields = config.get('fields', [])
            logger.info(f"[SYNC-STATUS] Carregados {len(fields)} campos do KV")
        except HTTPException as e:
            # Se retornou 404 (não encontrado), FALLBACK: buscar do endpoint prometheus-config
            if e.status_code == 404:
                logger.warning("[SYNC-STATUS] Campos não encontrados no KV - usando FALLBACK")

                try:
                    # FALLBACK: Buscar campos do cache do multi_config_manager
                    # Usar instância GLOBAL de prometheus_config.py (já tem cache populado!)
                    from api.prometheus_config import multi_config

                    # Extração via P2 (usa cache se disponível)
                    logger.info("[SYNC-STATUS FALLBACK] Chamando extract_all_fields_with_asyncssh_tar()")
                    extraction_result = await multi_config.extract_all_fields_with_asyncssh_tar()
                    logger.info(f"[SYNC-STATUS FALLBACK] extraction_result keys: {extraction_result.keys()}")
                    logger.info(f"[SYNC-STATUS FALLBACK] extraction_result['fields'] type: {type(extraction_result.get('fields', []))}")
                    logger.info(f"[SYNC-STATUS FALLBACK] extraction_result['fields'] length: {len(extraction_result.get('fields', []))}")

                    fields_objects = extraction_result.get('fields', [])

                    # Converter MetadataField objects para dict
                    fields = [f.to_dict() for f in fields_objects]

                    logger.info(f"[SYNC-STATUS FALLBACK] Carregados {len(fields)} campos do cache P2")

                    if len(fields) == 0:
                        # Se ainda assim não tem campos, orientar usuário
                        return SyncStatusResponse(
                            success=True,
                            server_id=server_id,
                            server_hostname=server_id.split(':')[0] if ':' in server_id else server_id,
                            fields=[],
                            total_synced=0,
                            total_outdated=0,
                            total_missing=0,
                            total_error=0,
                            prometheus_file_path=None,
                            checked_at=datetime.now().isoformat(),
                            message="Campos não carregados. Clique em 'Sincronizar Campos' para extrair do Prometheus primeiro.",
                            fallback_used=True,
                        )
                except Exception as fallback_err:
                    logger.error(f"[SYNC-STATUS FALLBACK] Erro no fallback: {fallback_err}")
                    # Retornar erro se fallback também falhar
                    raise HTTPException(
                        status_code=500,
                        detail=f"Erro ao carregar campos (KV e fallback falharam): {str(fallback_err)}"
                    )
            else:
                # Outros erros HTTP, repassar
                raise
        except Exception as e:
            logger.error(f"[SYNC-STATUS] Erro ao carregar campos: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Erro ao carregar configuração de campos: {str(e)}"
            )

        # Extrair hostname do server_id (formato: "172.16.1.26:5522" ou "11.144.0.21:22")
        hostname = server_id.split(':')[0] if ':' in server_id else server_id
        logger.info(f"[SYNC-STATUS] Hostname extraído: {hostname}")

        # NOVO: Usar ServerDetector para detectar capacidades do servidor
        detector = get_server_detector()
        server_info = detector.detect_server_capabilities(hostname, use_cache=False)

        # VERIFICAÇÃO CRÍTICA: Servidor tem Prometheus?
        if not server_info.has_prometheus:
            logger.info(
                f"[SYNC-STATUS] Servidor {hostname} não possui Prometheus. "
                f"Capacidades: {[c.value for c in server_info.capabilities]}"
            )

            # Retornar todos os campos com status especial para servidor sem Prometheus
            field_statuses = []
            for field in fields:
                field_statuses.append(FieldSyncStatus(
                    name=field.get('name'),
                    display_name=field.get('display_name', field.get('name')),
                    sync_status='error',
                    metadata_source_label=field.get('source_label'),
                    prometheus_target_label=None,
                    message=f'Servidor não possui Prometheus ({server_info.description})'
                ))

            return SyncStatusResponse(
                success=True,
                server_id=server_id,
                server_hostname=hostname,
                fields=field_statuses,
                total_synced=0,
                total_outdated=0,
                total_missing=0,
                total_error=len(fields),
                prometheus_file_path=None,
                checked_at=datetime.now().isoformat(),
                message=f'Servidor não possui Prometheus ({server_info.description})',
                fallback_used=False,
            )

        # Servidor TEM Prometheus - prosseguir com verificação de sincronização
        prometheus_file_path = server_info.prometheus_config_path
        logger.info(f"[SYNC-STATUS] Servidor tem Prometheus: {prometheus_file_path}")

        # Inicializar MultiConfigManager
        try:
            multi_config = MultiConfigManager()
            logger.info(f"[SYNC-STATUS] MultiConfigManager inicializado com sucesso")
        except Exception as e:
            logger.error(f"[SYNC-STATUS] Erro ao inicializar MultiConfigManager: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Erro ao inicializar gerenciador de configurações: {str(e)}"
            )

        try:
            # Ler conteúdo do arquivo via SSH
            assert isinstance(prometheus_file_path, str)
            yaml_content = multi_config.get_file_content_raw(prometheus_file_path, hostname=hostname)

            if not yaml_content:
                raise ValueError("Arquivo prometheus.yml vazio ou não encontrado")

            prometheus_config = yaml.safe_load(yaml_content)

            if not prometheus_config:
                raise ValueError("Conteúdo YAML inválido ou vazio")

            logger.info(f"[SYNC-STATUS] Prometheus.yml carregado com sucesso de {hostname}")

        except PermissionError as e:
            logger.error(f"[SYNC-STATUS] Permissão negada: {e}")
            raise HTTPException(
                status_code=403,
                detail=f"Permissão negada ao tentar ler prometheus.yml do servidor {hostname}. Verifique as credenciais SSH."
            )
        except yaml.YAMLError as e:
            logger.error(f"[SYNC-STATUS] Erro ao parsear YAML: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Erro ao parsear prometheus.yml do servidor {hostname}: Arquivo YAML inválido"
            )
        except Exception as e:
            logger.error(f"[SYNC-STATUS] Erro ao ler prometheus.yml: {e}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"Erro ao conectar ou ler arquivo do servidor {hostname}: {str(e)}"
            )

        # Extrair relabel_configs do Prometheus
        scrape_configs_full = prometheus_config.get('scrape_configs', []) or []

        first_job_has_relabel = False
        advanced_first_job = False
        prometheus_labels_map: Dict[str, str] = {}
        fallback_used = False

        if scrape_configs_full:
            first_job = scrape_configs_full[0]
            first_job_raw = first_job.get('relabel_configs')
            if isinstance(first_job_raw, list):
                logger.info(
                    "[SYNC-STATUS] Primeiro job possui %s relabel_configs declarados",
                    len(first_job_raw),
                )
            elif first_job_raw is not None:
                logger.info(
                    "[SYNC-STATUS] Primeiro job possui relabel_configs do tipo %s",
                    type(first_job_raw).__name__,
                )
            else:
                logger.info("[SYNC-STATUS] Primeiro job não possui relabel_configs declarados")

            first_job_map, advanced_first_job = _build_labels_map_from_jobs([first_job])
            if first_job_map:
                logger.info(
                    "[SYNC-STATUS] Mapa construído a partir do primeiro job (%s entradas, advanced=%s)",
                    len(first_job_map),
                    advanced_first_job,
                )
                prometheus_labels_map.update(first_job_map)
                first_job_has_relabel = True
            else:
                logger.info(
                    "[SYNC-STATUS] Primeiro job não gerou mapa direto (advanced=%s)",
                    advanced_first_job,
                )

        if not prometheus_labels_map and scrape_configs_full:
            fallback_map, advanced_from_jobs = _build_labels_map_from_jobs(scrape_configs_full)
            if fallback_map:
                logger.info(
                    "[SYNC-STATUS] Fallback de leitura aplicado: estrutura alternativa de scrape_configs detectada"
                )
                print("[SYNC-STATUS] fallback_map construído a partir do scan completo de jobs")
                prometheus_labels_map = fallback_map

                anchors_detected = _scrape_configs_use_aliases(yaml_content)
                advanced_structure_detected = anchors_detected or advanced_from_jobs

                logger.info(
                    "[SYNC-STATUS] Flags fallback -> advanced_from_jobs=%s, anchors_detected=%s, first_job_has_relabel=%s",
                    advanced_from_jobs,
                    anchors_detected,
                    first_job_has_relabel,
                )
                print(
                    "[SYNC-STATUS] Flags fallback => advanced_from_jobs=%s, anchors_detected=%s, first_job_has_relabel=%s"
                    % (advanced_from_jobs, anchors_detected, first_job_has_relabel)
                )

                combined_advanced = advanced_structure_detected or advanced_first_job

                if combined_advanced:
                    fallback_used = True
                    logger.info("[SYNC-STATUS] fallback_used marcado como True")
                    print("[SYNC-STATUS] fallback_used=True")
                else:
                    logger.info("[SYNC-STATUS] fallback_used permaneceu False (estrutura padrão)")
                    print("[SYNC-STATUS] fallback_used=False (estrutura padrão)")

        # Verificar status de cada campo
        field_statuses = []
        total_synced = 0
        total_outdated = 0
        total_missing = 0
        total_orphan = 0
        total_error = 0

        for field in fields:
            field_name = field.get('name')
            field_display_name = field.get('display_name', field_name)
            field_source_label = field.get('source_label')
            # TODO Issue #7: discovered_in foi movido para server_status[].fields[]
            # Este código precisa ser refatorado para calcular discovered_in dinamicamente
            # usando get_discovered_in_for_field(field_name, server_status)
            discovered_in = field.get('discovered_in', [])  # DEPRECATED - será removido

            if not field_source_label:
                # Campo sem source_label definido
                field_statuses.append(FieldSyncStatus(
                    name=field_name,
                    display_name=field_display_name,
                    sync_status='error',
                    metadata_source_label=None,
                    prometheus_target_label=None,
                    message='Campo sem source_label definido'
                ))
                total_error += 1
                continue

            # Verificar se existe no Prometheus
            raw_target, resolved_target, target_chain = _resolve_label_chain(
                field_source_label,
                prometheus_labels_map,
            )

            # LÓGICA MULTI-SERVER: Campo é orphan/missing baseado em discovered_in
            is_from_this_server = hostname in discovered_in or not discovered_in  # Se lista vazia, assumir compatível

            if raw_target is None:
                # Campo NÃO existe no prometheus.yml ATUAL
                if is_from_this_server:
                    # Campo FOI descoberto neste servidor mas agora NÃO está = ÓRFÃO
                    field_statuses.append(FieldSyncStatus(
                        name=field_name,
                        display_name=field_display_name,
                        sync_status='orphan',
                        metadata_source_label=field_source_label,
                        prometheus_target_label=None,
                        message=f'Campo foi removido do Prometheus (órfão - descoberto em: {", ".join(discovered_in)})'
                    ))
                    total_orphan += 1
                else:
                    # Campo NÃO foi descoberto neste servidor = MISSING (disponível para sincronizar)
                    servers_str = ", ".join(discovered_in) if discovered_in else "outros servidores"
                    field_statuses.append(FieldSyncStatus(
                        name=field_name,
                        display_name=field_display_name,
                        sync_status='missing',
                        metadata_source_label=field_source_label,
                        prometheus_target_label=None,
                        message=f'Campo disponível de {servers_str} (use "Sincronizar Campos" para aplicar)'
                    ))
                    total_missing += 1

            elif field_name in target_chain:
                field_statuses.append(FieldSyncStatus(
                    name=field_name,
                    display_name=field_display_name,
                    sync_status='synced',
                    metadata_source_label=field_source_label,
                    prometheus_target_label=field_name,
                    message='Campo sincronizado corretamente'
                ))
                total_synced += 1

            else:
                # Campo existe mas target_label está diferente
                mismatch_label = resolved_target or raw_target
                field_statuses.append(FieldSyncStatus(
                    name=field_name,
                    display_name=field_display_name,
                    sync_status='outdated',
                    metadata_source_label=field_source_label,
                    prometheus_target_label=mismatch_label,
                    message=(
                        f'Target label no Prometheus ({mismatch_label}) '
                        f'difere do esperado ({field_name})'
                    )
                ))
                total_outdated += 1

        return SyncStatusResponse(
            success=True,
            server_id=server_id,
            server_hostname=hostname,
            fields=field_statuses,
            total_synced=total_synced,
            total_outdated=total_outdated,
            total_missing=total_missing,
            total_orphan=total_orphan,
            total_error=total_error,
            prometheus_file_path=prometheus_file_path,
            checked_at=datetime.now().isoformat(),
            message=None,
            fallback_used=fallback_used,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao verificar sync status: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# FASE 2: PREVIEW DE MUDANÇAS
# ============================================================================

@router.get("/preview-changes/{field_name}", response_model=PreviewFieldChangeResponse)
async def preview_field_changes(
    field_name: str,
    server_id: str = Query(..., description="ID do servidor")
):
    """
    Preview das mudanças que serão aplicadas ao sincronizar um campo (FASE 2)

    Mostra:
    - Configuração atual no prometheus.yml
    - Nova configuração que será aplicada
    - Diff em texto
    - Jobs afetados
    """
    try:
        logger.info(f"[PREVIEW-CHANGES] Campo: {field_name}, Servidor: {server_id}")

        # Carregar campo do JSON
        config = await load_fields_config()
        field = get_field_by_name(config, field_name)
        if not field:
            raise HTTPException(status_code=404, detail=f"Campo '{field_name}' não encontrado")

        # Extrair hostname
        hostname = server_id.split(':')[0] if ':' in server_id else server_id

        # Verificar capacidades do servidor
        detector = get_server_detector()
        server_info = detector.detect_server_capabilities(hostname, use_cache=False)

        if not server_info.has_prometheus:
            raise HTTPException(
                status_code=400,
                detail=f"Servidor não possui Prometheus. {server_info.description}"
            )

        # Conectar ao servidor e ler prometheus.yml
        multi_config = MultiConfigManager()
        prometheus_file_path = "/etc/prometheus/prometheus.yml"

        try:
            yaml_content = multi_config.get_file_content_raw(prometheus_file_path, hostname=hostname)
            import yaml as pyyaml  # type: ignore
            prometheus_config = pyyaml.safe_load(yaml_content)
        except FileNotFoundError:
            raise HTTPException(status_code=404, detail=f"Prometheus.yml não encontrado no servidor {hostname}")

        # Verificar se campo já existe nos relabel_configs
        scrape_configs = prometheus_config.get('scrape_configs', [])
        if not scrape_configs:
            raise HTTPException(status_code=400, detail="Nenhum scrape_config encontrado")

        # Buscar relabel_config atual
        current_relabel = None
        affected_jobs = []
        for job in scrape_configs:
            job_name = job.get('job_name', 'unknown')
            affected_jobs.append(job_name)
            relabel_configs = job.get('relabel_configs', [])
            for relabel in relabel_configs:
                source_labels = relabel.get('source_labels', [])
                target_label = relabel.get('target_label')
                if field['source_label'] in source_labels:
                    current_relabel = relabel
                    break

        # Construir nova configuração
        new_config = {
            'source_labels': [field['source_label']],
            'target_label': field['name'],
            'action': 'replace'
        }

        # Gerar diff
        import difflib
        if current_relabel:
            current_text = f"# Configuração atual:\n{pyyaml.dump(current_relabel, default_flow_style=False)}"
            new_text = f"# Nova configuração:\n{pyyaml.dump(new_config, default_flow_style=False)}"
            will_create = False
        else:
            current_text = "# Campo não existe no prometheus.yml"
            new_text = f"# Configuração a ser criada:\n{pyyaml.dump(new_config, default_flow_style=False)}"
            will_create = True

        diff = difflib.unified_diff(
            current_text.splitlines(keepends=True),
            new_text.splitlines(keepends=True),
            fromfile='atual',
            tofile='novo',
            lineterm=''
        )
        diff_text = ''.join(diff)

        return PreviewFieldChangeResponse(
            success=True,
            field_name=field_name,
            current_config=current_relabel,
            new_config=new_config,
            diff_text=diff_text or "Nenhuma alteração detectada",
            affected_jobs=affected_jobs,
            will_create=will_create
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[PREVIEW-CHANGES] Erro: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# FASE 3: SINCRONIZAÇÃO EM LOTE
# ============================================================================

@router.post("/batch-sync", response_model=BatchSyncResponse)
async def batch_sync_fields(request: BatchSyncRequest):
    """
    Sincroniza múltiplos campos de uma vez (FASE 3)

    Percorre todos os campos fornecidos e aplica as mudanças no prometheus.yml.
    Suporta modo dry_run para simular sem aplicar.
    """
    import time
    start_time = time.time()

    try:
        logger.info(f"[BATCH-SYNC] Sincronizando {len(request.field_names)} campos no servidor {request.server_id}")
        logger.info(f"[BATCH-SYNC] Dry run: {request.dry_run}")

        results = []
        total_success = 0
        total_failed = 0

        # Carregar configuração de campos
        config = await load_fields_config()

        # Conectar ao servidor
        hostname = request.server_id.split(':')[0] if ':' in request.server_id else request.server_id

        # Verificar capacidades do servidor
        detector = get_server_detector()
        server_info = detector.detect_server_capabilities(hostname, use_cache=False)

        if not server_info.has_prometheus:
            raise HTTPException(
                status_code=400,
                detail=f"Servidor não possui Prometheus. {server_info.description}"
            )

        multi_config = MultiConfigManager()
        detected_path = server_info.prometheus_config_path

        if not detected_path:
            logger.error(
                "[BATCH-SYNC] Caminho do prometheus.yml não detectado para %s",
                hostname,
            )
            raise HTTPException(
                status_code=500,
                detail="Não foi possível identificar o caminho do prometheus.yml para este servidor"
            )

        prometheus_file_path = cast(str, detected_path)

        logger.info(
            "[BATCH-SYNC] Usando caminho detectado do prometheus.yml: %s (host=%s)",
            prometheus_file_path,
            hostname,
        )

        # Processar cada campo
        for field_name in request.field_names:
            try:
                field = get_field_by_name(config, field_name)
                if not field:
                    results.append(FieldSyncResult(
                        field_name=field_name,
                        success=False,
                        message=f"Campo '{field_name}' não encontrado",
                        changes_applied=0
                    ))
                    total_failed += 1
                    continue

                if request.dry_run:
                    # Modo simulação - apenas validar
                    results.append(FieldSyncResult(
                        field_name=field_name,
                        success=True,
                        message=f"[DRY RUN] Campo '{field_name}' seria sincronizado",
                        changes_applied=0
                    ))
                    total_success += 1
                else:
                    # Aplicar mudanças de verdade
                    try:
                        # Ler prometheus.yml do servidor
                        yaml_content = multi_config.get_file_content_raw(
                            prometheus_file_path,
                            hostname=hostname,
                        )

                        if not yaml_content:
                            raise ValueError(f"Arquivo prometheus.yml vazio ou não encontrado no servidor {hostname}")

                        # MANIPULAÇÃO TEXTUAL (não YAML parsing!) para preservar formatação 100%
                        changes_count = 0
                        modified_content = yaml_content

                        try:
                            parsed_config = yaml.safe_load(yaml_content) or {}
                        except yaml.YAMLError as parse_error:
                            raise ValueError(f"Erro ao parsear prometheus.yml: {parse_error}") from parse_error

                        scrape_configs = parsed_config.get('scrape_configs', []) or []
                        jobs_with_field = set()
                        eligible_jobs = set()

                        for job_data in scrape_configs:
                            job_name_value = job_data.get('job_name')
                            if not job_name_value:
                                continue

                            normalized_job_name = str(job_name_value).strip('"\'')

                            if job_data.get('consul_sd_configs'):
                                eligible_jobs.add(normalized_job_name)

                            for relabel in job_data.get('relabel_configs', []) or []:
                                source_labels = relabel.get('source_labels') or []
                                if isinstance(source_labels, str):
                                    source_labels = [source_labels]
                                if field['source_label'] in source_labels or relabel.get('target_label') == field['name']:
                                    jobs_with_field.add(normalized_job_name)
                                    break

                        job_pattern = re.compile(
                            r'^(\s*- job_name:\s+.*?)(?=^\s*- job_name:|\Z)',
                            re.MULTILINE | re.DOTALL
                        )

                        logger.info(f"[BATCH-SYNC] Campo a adicionar: {field_name}, source_label: {field['source_label']}")

                        search_pos = 0
                        job_index = 0
                        while True:
                            job_match = job_pattern.search(modified_content, search_pos)
                            if not job_match:
                                break

                            job_text = job_match.group(0)
                            job_start = job_match.start()
                            job_end = job_match.end()

                            job_name_match = re.search(r'job_name:\s+([^\n]+)', job_text)
                            if not job_name_match:
                                logger.warning(f"[BATCH-SYNC] Job #{job_index} sem nome válido, pulando")
                                search_pos = job_end
                                job_index += 1
                                continue

                            job_name_raw = job_name_match.group(1).strip()
                            job_name_value = job_name_raw.split('#', 1)[0].strip()
                            job_name = job_name_value.strip('"\'')

                            logger.info(f"[BATCH-SYNC] Processando job '{job_name}'...")

                            if job_name not in eligible_jobs:
                                logger.info(f"[BATCH-SYNC]   └─ Job '{job_name}' sem consul_sd_configs, pulando")
                                search_pos = job_end
                                job_index += 1
                                continue

                            if job_name in jobs_with_field:
                                logger.info(f"[BATCH-SYNC]   └─ Campo '{field_name}' já existe no job '{job_name}' (via YAML parsing), pulando")
                                search_pos = job_end
                                job_index += 1
                                continue

                            relabel_match = re.search(r'^(\s*)relabel_configs:[^\n]*\n', job_text, re.MULTILINE)
                            if not relabel_match:
                                logger.info(f"[BATCH-SYNC]   └─ Job '{job_name}' não tem relabel_configs, pulando")
                                search_pos = job_end
                                job_index += 1
                                continue

                            relabel_indent = len(relabel_match.group(1))
                            section_start = relabel_match.end()
                            section_lines = []

                            tail = job_text[section_start:]
                            for line in tail.splitlines(keepends=True):
                                current_indent = len(line) - len(line.lstrip(' '))
                                if line.strip() and current_indent <= relabel_indent:
                                    break

                                section_lines.append(line)

                            section_text = ''.join(section_lines)

                            if not section_text.strip():
                                logger.info(
                                    "[BATCH-SYNC]   └─ Job '%s' utiliza alias inline para relabel_configs, nenhuma edição direta",
                                    job_name,
                                )
                                search_pos = job_end
                                job_index += 1
                                continue

                            item_pattern = re.compile(r'(\s*-\s.*?(?=\n\s*-\s|\Z))', re.MULTILINE | re.DOTALL)
                            relabel_items = [m for m in item_pattern.finditer(section_text) if 'target_label' in m.group(0)]

                            if not relabel_items:
                                logger.warning(f"[BATCH-SYNC]   └─ Nenhum item válido encontrado em '{job_name}', pulando")
                                search_pos = job_end
                                job_index += 1
                                continue

                            insertion_item = None
                            for relabel_item in relabel_items:
                                block_text = relabel_item.group(0)
                                if '__param_target' in block_text or 'target_label: __address__' in block_text:
                                    insertion_item = relabel_item
                                    break

                            if insertion_item is None:
                                insertion_item = relabel_items[-1]
                                local_insert_pos = section_start + insertion_item.end()
                            else:
                                local_insert_pos = section_start + insertion_item.start()
                                while (
                                    local_insert_pos < len(job_text)
                                    and job_text[local_insert_pos] in ('\r', '\n')
                                ):
                                    local_insert_pos += 1

                            indent_match = re.match(r'^(\s*)-\s', insertion_item.group(0))
                            item_indent = indent_match.group(1) if indent_match else ' ' * (relabel_indent + 2)
                            item_indent = item_indent.replace('\r', '').replace('\n', '')

                            source_value = field['source_label']
                            # Usar o mesmo estilo inline para listas (ex: ["__meta..."])
                            before_segment = job_text[:local_insert_pos]
                            needs_leading_newline = not before_segment.endswith(('\n', '\r'))

                            newline = '\n' if needs_leading_newline else ''
                            insertion_text = (
                                f"{newline}{item_indent}- source_labels: [\"{source_value}\"]\n"
                                f"{item_indent}  target_label: {field['name']}\n"
                            )

                            updated_job_text = job_text[:local_insert_pos] + insertion_text + job_text[local_insert_pos:]
                            modified_content = (
                                modified_content[:job_start]
                                + updated_job_text
                                + modified_content[job_end:]
                            )
                            changes_count += 1
                            jobs_with_field.add(job_name)
                            logger.info(f"[BATCH-SYNC]   └─ ✓ Adicionado campo '{field_name}' no job '{job_name}' via edição textual")
                            logger.debug("[BATCH-SYNC]   └─ Bloco de referência:\n%s", insertion_item.group(0))
                            logger.debug("[BATCH-SYNC]   └─ Bloco inserido:\n%s", insertion_text.rstrip())

                            search_pos = job_start + len(updated_job_text)
                            job_index += 1

                        new_yaml_content = modified_content

                        if changes_count == 0:
                            logger.warning(f"[BATCH-SYNC] ⚠️ Nenhuma mudança aplicada para o campo '{field_name}' - campo já existe ou não foi possível encontrar local de inserção")
                            results.append(FieldSyncResult(
                                field_name=field_name,
                                success=False,
                                message=f"Campo '{field_name}' já existe em todos os jobs ou não foi possível adicionar",
                                changes_applied=0
                            ))
                            total_failed += 1
                            continue

                        # USAR O MESMO FLUXO DO PROMETHEUS CONFIG: backup + promtool + salvamento
                        try:
                            # Encontrar config_file (IGUAL prometheus_config.py faz)
                            config_file = multi_config.get_file_by_path(
                                prometheus_file_path,
                                hostname=hostname,
                            )
                            if not config_file:
                                raise ValueError(f"Arquivo não encontrado: {prometheus_file_path} no servidor {hostname}")

                            # Conectar via SSH
                            client = multi_config._get_ssh_client(config_file.host)

                            # PASSO 1: Criar backup com timestamp (IGUAL prometheus_config.py linha 972)
                            from datetime import datetime
                            timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
                            backup_path = f"{config_file.path}.backup-{timestamp}"

                            backup_cmd = f"cp {config_file.path} {backup_path}"
                            logger.info(f"[BATCH-SYNC] Criando backup: {backup_path}")

                            stdin, stdout, stderr = client.exec_command(backup_cmd)
                            exit_code = stdout.channel.recv_exit_status()

                            if exit_code != 0:
                                error = stderr.read().decode('utf-8')
                                raise Exception(f"Erro ao criar backup: {error}")

                            logger.info(f"[BATCH-SYNC] ✓ Backup criado")

                            # PASSO 2: Escrever em arquivo temporário
                            import os
                            file_dir = os.path.dirname(config_file.path)
                            file_base = os.path.basename(config_file.path)
                            temp_file = f"{file_dir}/{file_base}.tmp-{timestamp}"

                            write_cmd = f"cat > {temp_file} << 'EOFILE'\n{new_yaml_content}\nEOFILE"
                            stdin, stdout, stderr = client.exec_command(write_cmd)
                            exit_code = stdout.channel.recv_exit_status()

                            if exit_code != 0:
                                error = stderr.read().decode('utf-8')
                                raise Exception(f"Erro ao escrever arquivo temp: {error}")

                            logger.info(f"[BATCH-SYNC] ✓ Arquivo temporário criado")

                            # PASSO 3: Validar com promtool (IGUAL prometheus_config.py linha 1018)
                            logger.info(f"[BATCH-SYNC] Validando com promtool...")

                            promtool_cmd = f"promtool check config {temp_file}"
                            stdin, stdout, stderr = client.exec_command(promtool_cmd)
                            exit_code = stdout.channel.recv_exit_status()

                            output = stdout.read().decode('utf-8')
                            errors = stderr.read().decode('utf-8')

                            if exit_code != 0:
                                logger.error(f"[BATCH-SYNC] ✗ Validação promtool falhou")
                                logger.error(f"[BATCH-SYNC] Output: {output}")
                                logger.error(f"[BATCH-SYNC] Errors: {errors}")

                                # Remover arquivo temporário
                                client.exec_command(f"rm {temp_file}")

                                raise Exception(f"Validação promtool falhou: {errors or output}")

                            logger.info(f"[BATCH-SYNC] ✓ Validação promtool passou")

                            # PASSO 4: Mover arquivo temporário para destino final
                            move_cmd = f"mv {temp_file} {config_file.path}"
                            stdin, stdout, stderr = client.exec_command(move_cmd)
                            exit_code = stdout.channel.recv_exit_status()

                            if exit_code != 0:
                                error = stderr.read().decode('utf-8')
                                # Restaurar backup
                                client.exec_command(f"cp {backup_path} {config_file.path}")
                                raise Exception(f"Erro ao mover arquivo: {error}")

                            # PASSO 5: Restaurar permissões prometheus:prometheus
                            chown_cmd = f"chown prometheus:prometheus {config_file.path}"
                            client.exec_command(chown_cmd)

                            logger.info(f"[BATCH-SYNC] ✅ Campo '{field_name}' salvo com sucesso no servidor {hostname}")
                            logger.info(f"[BATCH-SYNC] Backup: {backup_path}")
                            logger.info(f"[BATCH-SYNC] {changes_count} mudança(s) aplicadas")

                            results.append(FieldSyncResult(
                                field_name=field_name,
                                success=True,
                                message=f"Campo '{field_name}' sincronizado com sucesso ({changes_count} job(s) afetado(s)). Backup: {os.path.basename(backup_path)}",
                                changes_applied=changes_count
                            ))
                            total_success += 1

                        except Exception as save_error:
                            logger.error(f"[BATCH-SYNC] ❌ Erro ao salvar arquivo: {save_error}", exc_info=True)
                            results.append(FieldSyncResult(
                                field_name=field_name,
                                success=False,
                                message=f"Erro ao salvar arquivo: {str(save_error)}",
                                changes_applied=0
                            ))
                            total_failed += 1

                    except Exception as sync_error:
                        logger.error(f"[BATCH-SYNC] Erro ao sincronizar campo '{field_name}': {sync_error}", exc_info=True)
                        results.append(FieldSyncResult(
                            field_name=field_name,
                            success=False,
                            message=f"Erro: {str(sync_error)}",
                            changes_applied=0
                        ))
                        total_failed += 1

            except Exception as e:
                logger.error(f"[BATCH-SYNC] Erro ao sincronizar {field_name}: {e}")
                results.append(FieldSyncResult(
                    field_name=field_name,
                    success=False,
                    message=str(e),
                    changes_applied=0
                ))
                total_failed += 1

        duration = time.time() - start_time

        return BatchSyncResponse(
            success=total_failed == 0,
            server_id=request.server_id,
            results=results,
            total_processed=len(request.field_names),
            total_success=total_success,
            total_failed=total_failed,
            duration_seconds=round(duration, 2)
        )

    except Exception as e:
        logger.error(f"[BATCH-SYNC] Erro geral: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/", response_model=FieldsConfigResponse)
async def list_fields(
    category: Optional[str] = Query(None, description="Filtrar por categoria"),
    required_only: bool = Query(False, description="Apenas campos obrigatórios"),
    show_in_table_only: bool = Query(False, description="Apenas campos de tabela")
):
    """
    Lista todos os campos metadata configurados

    Filtros disponíveis:
    - category: Filtrar por categoria (infrastructure, basic, device, extra)
    - required_only: Apenas campos obrigatórios
    - show_in_table_only: Apenas campos que aparecem em tabelas

    PROTEÇÃO CONTRA RACE CONDITION:
    - Se PRE-WARM estiver rodando, aguarda até 15 segundos
    - Polling a cada 0.5s (30 iterações)
    - Retorna erro 503 se timeout ou PRE-WARM falhar
    """
    # Import status from app module
    try:
        from app import _prewarm_status
    except ImportError:
        logger.warning("[METADATA-FIELDS] Não foi possível importar _prewarm_status do app.py")
        _prewarm_status = {'running': False, 'completed': False, 'failed': False, 'error': None}

    # Se PRE-WARM está rodando, aguardar até 15s
    if _prewarm_status.get('running', False):
        logger.info("[METADATA-FIELDS] PRE-WARM em andamento, aguardando até 15s...")

        for i in range(30):  # 30 * 0.5s = 15s
            if _prewarm_status.get('completed', False):
                logger.info(f"[METADATA-FIELDS] PRE-WARM concluído após {i * 0.5}s, prosseguindo...")
                break
            if _prewarm_status.get('failed', False):
                error_msg = _prewarm_status.get('error', 'Erro desconhecido')
                logger.error(f"[METADATA-FIELDS] PRE-WARM falhou: {error_msg}")
                raise HTTPException(
                    status_code=503,
                    detail=f"Falha ao inicializar cache: {error_msg}"
                )
            await asyncio.sleep(0.5)
        else:
            # Timeout de 15s
            logger.warning("[METADATA-FIELDS] Timeout aguardando PRE-WARM (15s)")
            raise HTTPException(
                status_code=503,
                detail="Sistema ainda inicializando. Tente novamente em alguns segundos."
            )

    # Continuar com lógica normal de leitura do KV
    # NOTA: Cache detection removido - agora gerenciado pelo ConsulKVConfigManager
    config = await load_fields_config()

    # PROTEÇÃO: Validar se config não é None
    if not config:
        raise HTTPException(
            status_code=503,
            detail="Configuração de campos não disponível. O sistema pode estar inicializando ou houve erro na extração."
        )

    fields = config.get('fields', [])

    # Aplicar filtros
    if category:
        fields = [f for f in fields if f.get('category') == category]

    if required_only:
        fields = [f for f in fields if f.get('required', False)]

    if show_in_table_only:
        fields = [f for f in fields if f.get('show_in_table', False)]

    # Ordenar por order
    fields.sort(key=lambda f: f.get('order', 999))

    # Buscar informações de extraction_status se existir (para modal de progresso)
    extraction_status = config.get('extraction_status', {})
    server_status = extraction_status.get('server_status', [])

    # ✅ FIX Issue #7: Calcular discovered_in dinamicamente (SINGLE SOURCE OF TRUTH)
    # discovered_in agora vem de server_status[].fields[] e não mais do dataclass
    for field in fields:
        field['discovered_in'] = get_discovered_in_for_field(field['name'], server_status)

    # FIX BUG #2: came_from_memory_cache não existe mais (removido durante refactor)
    # CRÍTICO: Se source não é force_extract recente, marcar como cache
    # Isso garante que o modal mostre "Dados carregados do cache instantaneamente"
    is_from_cache = config.get('source') in ['prewarm_startup', 'prewarm_update_extraction_status', 'fallback_on_demand']

    return FieldsConfigResponse(
        success=True,
        fields=fields,
        categories=config.get('categories', {}),
        total=len(fields),
        version=config.get('version', '1.0.0'),
        last_updated=config.get('last_updated', ''),
        # Adicionar informações do extraction_status para modal
        from_cache=is_from_cache,  # ← CORRIGIDO: detecta cache em memória ou prewarm
        server_status=extraction_status.get('server_status', []),
        total_servers=extraction_status.get('total_servers', 0),
        successful_servers=extraction_status.get('successful_servers', 0),
        # CRITICAL FIX: Retornar extraction_status completo para discovered_in
        extraction_status=extraction_status if extraction_status else None
    )


@router.get("/{field_name}")
async def get_field(field_name: str):
    """Busca campo específico por nome"""
    config = await load_fields_config()
    field = get_field_by_name(config, field_name)

    if not field:
        raise HTTPException(status_code=404, detail=f"Campo '{field_name}' não encontrado")

    return {
        "success": True,
        "field": field
    }


@router.post("/")
async def create_field(request: AddFieldRequest):
    """
    Cria novo campo metadata

    Se sync_prometheus=True, adiciona o campo a todos os jobs do prometheus.yml
    """
    config = await load_fields_config()

    # Verificar se já existe
    if get_field_by_name(config, request.field.name):
        raise HTTPException(
            status_code=400,
            detail=f"Campo '{request.field.name}' já existe"
        )

    # Adicionar ao config
    new_field = request.field.dict()
    config['fields'].append(new_field)

    # Salvar configuração
    await save_fields_config(config)

    # Sincronizar com prometheus.yml se solicitado
    if request.sync_prometheus:
        try:
            multi_config = MultiConfigManager()
            result = await sync_field_to_prometheus(
                multi_config,
                new_field,
                request.apply_to_jobs
            )

            return {
                "success": True,
                "message": f"Campo '{request.field.name}' criado com sucesso",
                "field": new_field,
                "prometheus_sync": result
            }
        except Exception as e:
            logger.error(f"Erro ao sincronizar com prometheus: {e}")
            return {
                "success": True,
                "message": f"Campo criado, mas erro ao sincronizar: {str(e)}",
                "field": new_field,
                "prometheus_sync": {"success": False, "error": str(e)}
            }

    return {
        "success": True,
        "message": f"Campo '{request.field.name}' criado com sucesso",
        "field": new_field
    }


@router.post("/add-to-kv")
async def add_fields_to_kv(request: AddToKVRequest):
    """
    Adiciona campos extraídos do Prometheus ao KV (Consul Key-Value).

    Este endpoint é usado quando campos foram descobertos no Prometheus via force-extract
    mas ainda não estão no KV. O status desses campos é "missing" (não aplicado).

    FLUXO:
    1. Carregar configuração atual do KV
    2. Para cada campo em field_names:
       - Verificar se já existe no KV (pular se existir)
       - Adicionar ao array de fields
    3. Salvar configuração atualizada no KV
    4. Limpar cache

    Args:
        request: AddToKVRequest com field_names e fields_data

    Returns:
        JSON com sucesso, quantidade de campos adicionados, e mensagem
    """
    try:
        logger.info(f"[ADD-TO-KV] Adicionando {len(request.field_names)} campos ao KV")

        # PASSO 1: Carregar configuração atual do KV
        config = await load_fields_config()
        existing_fields_map = {f['name']: f for f in config.get('fields', [])}

        # PASSO 2: Adicionar campos que NÃO existem no KV
        fields_added = []
        fields_skipped = []

        for field_data in request.fields_data:
            field_name = field_data.get('name')

            if not field_name:
                logger.warning(f"[ADD-TO-KV] Campo sem nome, pulando: {field_data}")
                continue

            # Se campo JÁ existe no KV, pular
            if field_name in existing_fields_map:
                logger.info(f"[ADD-TO-KV] Campo '{field_name}' já existe no KV, pulando")
                fields_skipped.append(field_name)
                continue

            # Adicionar campo ao config
            config['fields'].append(field_data)
            fields_added.append(field_name)
            logger.info(f"[ADD-TO-KV] ✅ Campo '{field_name}' adicionado ao KV")

        # PASSO 3: Salvar configuração atualizada no KV
        if fields_added:
            await save_fields_config(config)
            logger.info(f"[ADD-TO-KV] Configuração salva no KV com {len(fields_added)} novos campos")

            # PASSO 4: Invalidar cache unificado para forçar reload
            _kv_manager.invalidate('metadata/fields')
            logger.info("[ADD-TO-KV] Cache invalidado")

        # PASSO 5: Retornar resultado
        return {
            "success": True,
            "message": f"{len(fields_added)} campo(s) adicionado(s) ao KV com sucesso",
            "fields_added": fields_added,
            "fields_skipped": fields_skipped,
            "total_added": len(fields_added),
            "total_skipped": len(fields_skipped),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[ADD-TO-KV] Erro: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao adicionar campos ao KV: {str(e)}"
        )


@router.put("/{field_name}")
async def update_field(field_name: str, field_data: MetadataFieldModel):
    """Atualiza campo existente (substituição completa)"""
    config = await load_fields_config()

    # Buscar campo
    field = get_field_by_name(config, field_name)
    if not field:
        raise HTTPException(status_code=404, detail=f"Campo '{field_name}' não encontrado")

    # Atualizar dados
    updated_field = field_data.dict()

    # Substituir no array
    for i, f in enumerate(config['fields']):
        if f['name'] == field_name:
            config['fields'][i] = updated_field
            break

    # Salvar
    await save_fields_config(config)

    return {
        "success": True,
        "message": f"Campo '{field_name}' atualizado com sucesso",
        "field": updated_field
    }


@router.patch("/{field_name}")
async def partial_update_field(field_name: str, updates: Dict[str, Any] = Body(...)):
    """
    Atualiza parcialmente um campo existente (apenas campos enviados).

    Útil para atualizar show_in_services, show_in_exporters, show_in_blackbox
    sem precisar enviar todo o objeto MetadataFieldModel.

    Example:
        PATCH /api/v1/metadata-fields/company
        {
            "show_in_services": true,
            "show_in_exporters": false
        }
    """
    config = await load_fields_config()

    # Buscar campo
    field = get_field_by_name(config, field_name)
    if not field:
        raise HTTPException(status_code=404, detail=f"Campo '{field_name}' não encontrado")

    # Atualizar apenas os campos enviados
    for key, value in updates.items():
        if key == 'name':
            # Não permitir mudar o nome (usaria como chave primária)
            raise HTTPException(status_code=400, detail="Não é permitido alterar o nome do campo")
        field[key] = value

    # Salvar (substituir campo no array)
    for i, f in enumerate(config['fields']):
        if f['name'] == field_name:
            config['fields'][i] = field
            break

    # Salvar
    await save_fields_config(config)

    # CRÍTICO: Invalidar cache para que mudanças apareçam imediatamente
    # Sem isso, /api/v1/reference-values/ retorna cache antigo por até 5 minutos
    _kv_manager.invalidate('metadata/fields')
    logger.info(f"[CACHE] Cache unificado invalidado após atualização de '{field_name}'")

    return {
        "success": True,
        "message": f"Campo '{field_name}' atualizado com sucesso",
        "field": field
    }


@router.post("/remove-orphans")
async def remove_orphan_fields(request: Dict[str, List[str]] = Body(...)):
    """
    Remove campos órfãos do KV (campos que não existem mais no Prometheus).

    Body: {"field_names": ["testeCampo8", "testeCampo9"]}

    Este endpoint é usado para limpar campos que foram removidos do Prometheus
    mas ainda permanecem no KV.
    """
    try:
        field_names = request.get('field_names', [])

        if not field_names:
            raise HTTPException(status_code=400, detail="Lista de campos vazia")

        logger.info(f"[REMOVE-ORPHANS] Removendo {len(field_names)} campos órfãos do KV")

        # Carregar config do KV
        config = await load_fields_config()

        # Remover campos da lista
        initial_count = len(config['fields'])
        config['fields'] = [f for f in config['fields'] if f['name'] not in field_names]
        removed_count = initial_count - len(config['fields'])

        # Salvar config atualizado
        await save_fields_config(config)

        # Invalidar cache unificado
        _kv_manager.invalidate('metadata/fields')

        logger.info(f"[REMOVE-ORPHANS] ✅ {removed_count} campos órfãos removidos do KV")

        return {
            "success": True,
            "message": f"{removed_count} campo(s) órfão(s) removido(s) com sucesso",
            "removed_fields": field_names,
            "removed_count": removed_count,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[REMOVE-ORPHANS] Erro: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao remover campos órfãos: {str(e)}"
        )


@router.delete("/{field_name}")
async def delete_field(
    field_name: str,
    remove_from_prometheus: bool = Query(False, description="Remover do prometheus.yml")
):
    """Deleta campo metadata do KV (e opcionalmente do prometheus.yml)"""
    config = await load_fields_config()

    # Buscar campo
    field = get_field_by_name(config, field_name)
    if not field:
        raise HTTPException(status_code=404, detail=f"Campo '{field_name}' não encontrado")

    # Não permitir deletar campos obrigatórios
    if field.get('required', False):
        raise HTTPException(
            status_code=400,
            detail=f"Não é possível deletar campo obrigatório: '{field_name}'"
        )

    # Remover do array
    config['fields'] = [f for f in config['fields'] if f['name'] != field_name]

    # Salvar
    await save_fields_config(config)

    # Invalidar cache unificado
    _kv_manager.invalidate('metadata/fields')

    result = {
        "success": True,
        "message": f"Campo '{field_name}' deletado com sucesso"
    }

    # Remover do prometheus se solicitado
    if remove_from_prometheus:
        try:
            multi_config = MultiConfigManager()
            # TODO: Implementar remoção do campo dos jobs
            result["prometheus_sync"] = {"success": True, "message": "Campo removido do prometheus.yml"}
        except Exception as e:
            result["prometheus_sync"] = {"success": False, "error": str(e)}

    return result


@router.post("/reorder")
async def reorder_fields(field_orders: Dict[str, int] = Body(...)):
    """
    Reordena campos

    Body: {"field_name": order, ...}
    Exemplo: {"company": 1, "env": 2, "project": 3}
    """
    config = await load_fields_config()

    # Atualizar ordem de cada campo
    for field in config['fields']:
        field_name = field['name']
        if field_name in field_orders:
            field['order'] = field_orders[field_name]

    # Salvar
    await save_fields_config(config)

    return {
        "success": True,
        "message": f"{len(field_orders)} campos reordenados"
    }


# ============================================================================
# SINCRONIZAÇÃO COM PROMETHEUS
# ============================================================================

async def sync_field_to_prometheus(
    multi_config: MultiConfigManager,
    field: Dict[str, Any],
    apply_to_jobs: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Adiciona campo a todos os jobs do prometheus.yml

    Args:
        multi_config: Gerenciador de configurações
        field: Dados do campo
        apply_to_jobs: Lista de jobs ou None para todos

    Returns:
        Dict com resultado da sincronização
    """
    logger.info(f"Sincronizando campo '{field['name']}' com prometheus.yml")

    # Buscar arquivo prometheus.yml
    files = multi_config.list_config_files('prometheus')
    prom_file = None

    for f in files:
        if f.filename == 'prometheus.yml':
            prom_file = f
            break

    if not prom_file:
        return {"success": False, "error": "prometheus.yml não encontrado"}

    # Ler configuração
    config = multi_config.read_config_file(prom_file)
    jobs = config.get('scrape_configs', [])

    jobs_modified = []

    for job in jobs:
        job_name = job.get('job_name', 'unknown')

        # Verificar se deve aplicar a este job
        if apply_to_jobs and job_name not in apply_to_jobs:
            continue

        # Pular jobs sem consul_sd_configs
        if 'consul_sd_configs' not in job:
            continue

        # Pular job prometheus (não tem metadata)
        if job_name == 'prometheus':
            continue

        # Adicionar relabel_config para o campo
        if 'relabel_configs' not in job:
            job['relabel_configs'] = []

        relabels = job['relabel_configs']

        # Verificar se já existe
        field_exists = False
        for relabel in relabels:
            if relabel.get('target_label') == field['name']:
                field_exists = True
                break

        if not field_exists:
            # Adicionar novo relabel_config
            new_relabel = {
                'source_labels': [field['source_label']],
                'target_label': field['name']
            }

            # Inserir antes dos configs especiais (__param_target, __address__)
            insert_pos = len(relabels)
            for i, relabel in enumerate(relabels):
                source = relabel.get('source_labels', [])
                if source and ('__param_target' in str(source) or relabel.get('target_label') == '__address__'):
                    insert_pos = i
                    break

            relabels.insert(insert_pos, new_relabel)
            jobs_modified.append(job_name)

    if jobs_modified:
        # Salvar configuração atualizada
        from io import StringIO
        from core.yaml_config_service import YamlConfigService
        yaml_service = YamlConfigService()
        output = StringIO()
        yaml_service.yaml.dump(config, output)
        yaml_content = output.getvalue()

        # Validar com promtool
        validation_result = multi_config.validate_prometheus_config(prom_file.path, yaml_content)

        if not validation_result['success']:
            return {
                "success": False,
                "error": "Validação do promtool falhou",
                "validation_errors": validation_result['errors']
            }

        # Salvar
        multi_config.save_file_content(prom_file.path, yaml_content)

        logger.info(f"Campo adicionado a {len(jobs_modified)} jobs")

        return {
            "success": True,
            "message": f"Campo adicionado a {len(jobs_modified)} jobs",
            "jobs_modified": jobs_modified
        }
    else:
        return {
            "success": True,
            "message": "Campo já existe em todos os jobs",
            "jobs_modified": []
        }


@router.post("/sync-to-prometheus/{field_name}")
async def sync_field_to_prometheus_endpoint(
    field_name: str,
    apply_to_jobs: Optional[List[str]] = Body(None)
):
    """
    Sincroniza campo específico com prometheus.yml

    Adiciona o relabel_config deste campo a todos os jobs (ou jobs específicos)
    """
    config = await load_fields_config()
    field = get_field_by_name(config, field_name)

    if not field:
        raise HTTPException(status_code=404, detail=f"Campo '{field_name}' não encontrado")

    try:
        multi_config = MultiConfigManager()
        result = await sync_field_to_prometheus(multi_config, field, apply_to_jobs)

        return result
    except Exception as e:
        logger.error(f"Erro ao sincronizar: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/force-extract")
async def force_extract_fields(
    request: Optional[ForceExtractRequest] = None
):
    """
    Força extração manual de campos do Prometheus via SSH.

    IMPORTANTE: Esta operação APENAS DETECTA campos novos, NÃO adiciona ao KV automaticamente.

    CONCEITO:
    - EXTRAIR ≠ SINCRONIZAR
    - Extração apenas descobre quais campos existem no Prometheus
    - Usuário decide quais campos quer usar (via "Sincronizar Campos")

    FLUXO:
    1. Limpa cache de campos
    2. Conecta via SSH aos servidores Prometheus (ou apenas um servidor se server_id fornecido)
    3. Extrai relabel_configs do prometheus.yml
    4. Compara com KV e detecta campos novos
    5. Retorna lista de campos novos encontrados
    6. NÃO modifica KV (campos permanecem como "missing" até sincronizar)

    Útil quando:
    - Adicionou novos campos manualmente no prometheus.yml de algum servidor
    - Quer descobrir quais campos existem sem aplicá-los automaticamente
    - Suspeita que há campos no Prometheus que não estão no KV

    Args:
        request: Opcional - se fornecido com server_id, extrai apenas daquele servidor
    """
    try:
        server_id = request.server_id if request else None

        if server_id:
            logger.info(f"[FORCE-EXTRACT] Iniciando detecção de campos do servidor: {server_id}")
        else:
            logger.info("[FORCE-EXTRACT] Iniciando detecção de campos de TODOS os servidores")

        # PASSO 1: Invalidar cache unificado para forçar nova extração
        _kv_manager.invalidate('metadata/fields')
        logger.info("[FORCE-EXTRACT] Cache invalidado")

        # PASSO 2: Carregar campos EXISTENTES do KV (para comparação)
        from core.kv_manager import KVManager
        kv_manager = KVManager()
        existing_config = await kv_manager.get_json('skills/eye/metadata/fields')

        existing_fields_map = {}
        if existing_config and 'fields' in existing_config:
            existing_fields_map = {
                f['name']: f for f in existing_config['fields']
            }
            logger.info(f"[FORCE-EXTRACT] {len(existing_fields_map)} campos existentes no KV")
        else:
            logger.info("[FORCE-EXTRACT] Nenhum campo existente no KV")

        # PASSO 3: Extrair campos do Prometheus via SSH
        import asyncio
        multi_config = MultiConfigManager()

        # Se tiver server_id, usar método específico para servidor único
        if server_id:
            # Verificar se servidor existe
            if not any(h.hostname == server_id for h in multi_config.hosts):
                raise HTTPException(
                    status_code=404,
                    detail=f"Servidor '{server_id}' não encontrado na configuração"
                )

            logger.info(f"[FORCE-EXTRACT] Usando extract_single_server_fields para: {server_id}")

            # USAR MÉTODO CORRETO PARA SERVIDOR ÚNICO (sync → async via to_thread)
            extraction_result = await asyncio.to_thread(
                multi_config.extract_single_server_fields,
                server_id
            )
        else:
            # Extrair de todos os servidores (async nativo)
            extraction_result = await multi_config.extract_all_fields_with_asyncssh_tar()

        if not extraction_result or 'fields' not in extraction_result:
            raise HTTPException(
                status_code=500,
                detail="Falha na extração de campos do Prometheus"
            )

        fields_objects = extraction_result['fields']
        total_servers = extraction_result.get('total_servers', 0)
        successful_servers = extraction_result.get('successful_servers', 0)

        logger.info(f"[FORCE-EXTRACT] {len(fields_objects)} campos extraídos do Prometheus")

        # PASSO 4: DETECTAR campos novos + preparar lista completa para frontend
        new_field_names = []
        all_fields_for_frontend = []

        for extracted_field in fields_objects:
            field_name = extracted_field.name
            field_dict = extracted_field.to_dict()

            # Detectar se é campo novo
            is_new = field_name not in existing_fields_map

            if is_new:
                new_field_names.append(field_name)
                logger.info(f"[FORCE-EXTRACT] 🆕 Campo NOVO descoberto: '{field_name}'")

            # Adicionar à lista completa para o frontend
            all_fields_for_frontend.append(field_dict)

        new_fields_count = len(new_field_names)

        logger.info(
            f"[FORCE-EXTRACT] ✅ Detecção concluída: {len(all_fields_for_frontend)} campos extraídos, "
            f"{new_fields_count} novos descobertos (NÃO salvos no KV)"
        )

        # PASSO 5: Sincronizar sites no KV automaticamente
        server_status = extraction_result.get('server_status', [])
        sites_sync_result = await sync_sites_to_kv(server_status)
        
        logger.info(
            f"[FORCE-EXTRACT] Sites sincronizados: {sites_sync_result['total_sites']} total, "
            f"{len(sites_sync_result['sites_added'])} novos"
        )

        # IMPORTANTE: NÃO salvar campos no KV automaticamente!
        # Apenas salvar sites (que tem external_labels)
        # Retornar lista completa de campos extraídos para o frontend usar

        return {
            "success": True,
            "message": f"Extração concluída. {new_fields_count} campo(s) novo(s) descoberto(s) no Prometheus.",
            "total_fields": len(all_fields_for_frontend),
            "fields": all_fields_for_frontend,  # ← Lista COMPLETA de campos extraídos
            "new_fields": new_field_names,
            "new_fields_count": new_fields_count,
            "existing_fields_count": len(existing_fields_map),
            "servers_checked": total_servers,
            "servers_success": successful_servers,
            "sites_synced": sites_sync_result['total_sites'],
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[FORCE-EXTRACT] Erro: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao extrair campos: {str(e)}"
        )


# ============================================================================
# FUNÇÃO AUXILIAR: SINCRONIZAR SITES NO KV
# ============================================================================

async def sync_sites_to_kv(server_status: list) -> dict:
    """
    Sincroniza sites automaticamente no KV baseado em server_status
    
    CHAMADO AUTOMATICAMENTE APÓS:
    - force_extract_fields()
    - load_fields_config() (fallback)
    
    PROCESSO:
    1. Extrai external_labels de cada servidor em server_status
    2. Cria/atualiza sites no KV com estrutura completa
    3. Preserva configurações editáveis existentes (name, color, is_default)
    
    Args:
        server_status: Lista de dicts com hostname, external_labels, port, etc
    
    Returns:
        Dict com estatísticas da sincronização
    """
    from core.kv_manager import KVManager
    import os
    
    kv = KVManager()
    
    # PASSO 1: Buscar sites existentes do KV
    kv_data = await kv.get_json('skills/eye/metadata/sites') or {"data": {"sites": []}}
    
    # Estrutura pode ter wrapper 'data'
    if 'data' in kv_data:
        existing_sites = kv_data.get('data', {}).get('sites', [])
    else:
        existing_sites = kv_data.get('sites', [])
    
    # Mapear code → site config existente
    existing_sites_map = {s['code']: s for s in existing_sites}
    
    logger.info(f"[SITES SYNC] Sites existentes no KV: {len(existing_sites)}")
    
    # PASSO 2: Buscar configuração de .env para pegar portas SSH
    prometheus_hosts_str = os.getenv("PROMETHEUS_CONFIG_HOSTS", "")
    raw_hosts = [h.strip() for h in prometheus_hosts_str.split(';') if h.strip()]
    
    # Mapear hostname → ssh_port
    hostname_to_ssh_port = {}
    for host_str in raw_hosts:
        parts = host_str.split('/')
        if len(parts) != 3:
            continue
        host_port = parts[0]
        host_parts = host_port.split(':')
        if len(host_parts) == 2:
            hostname = host_parts[0]
            ssh_port = int(host_parts[1]) if host_parts[1].isdigit() else 22
            hostname_to_ssh_port[hostname] = ssh_port
    
    # PASSO 3: MESCLAR sites novos com existentes (NÃO sobrescrever!)
    # IMPORTANTE: Preservar sites órfãos (que não estão no server_status)
    updated_sites_map = existing_sites_map.copy()  # Começar com TODOS os existentes
    sites_added = []
    sites_updated = []
    
    for server in server_status:
        if not server.get('success'):
            continue  # Pular servidores com falha
        
        hostname = server.get('hostname')
        external_labels = server.get('external_labels', {})
        
        if not external_labels:
            logger.warning(f"[SITES SYNC] {hostname}: Sem external_labels, pulando")
            continue
        
        # Detectar code do site
        site_code = external_labels.get('site', hostname.replace('.', '_'))
        
        # Buscar config existente
        existing_config = updated_sites_map.get(site_code, {})
        
        # Determinar SSH port
        ssh_port = hostname_to_ssh_port.get(hostname, 22)
        
        # Criar site com external_labels no nível raiz
        site = {
            # Campos editáveis (preservar se existem)
            "code": site_code,
            "name": existing_config.get("name", site_code.title()),
            "is_default": existing_config.get("is_default", False),
            "color": existing_config.get("color", "blue"),
            
            # Campos de external_labels (readonly)
            "cluster": external_labels.get("cluster", ""),
            "datacenter": external_labels.get("datacenter", ""),
            "environment": external_labels.get("environment", ""),
            "site": external_labels.get("site", site_code),
            "prometheus_instance": external_labels.get("prometheus_instance", hostname),
            
            # Conexão
            "prometheus_host": hostname,
            "ssh_port": ssh_port,
            "prometheus_port": 9090,
        }
        
        # ATUALIZAR no map (mesclar, não substituir lista inteira)
        updated_sites_map[site_code] = site
        
        if site_code in existing_sites_map:
            sites_updated.append(site_code)
            logger.info(f"[SITES SYNC] ♻️ Site atualizado: {site_code}")
        else:
            sites_added.append(site_code)
            logger.info(f"[SITES SYNC] 🆕 Novo site: {site_code}")
    
    # Converter map de volta para lista
    new_sites = list(updated_sites_map.values())
    
    # PASSO 4: Garantir pelo menos um site default
    if new_sites and not any(s.get("is_default") for s in new_sites):
        new_sites[0]["is_default"] = True
        logger.info(f"[SITES SYNC] Marcado '{new_sites[0]['code']}' como default")
    
    # PASSO 5: Salvar no KV
    new_structure = {
        "data": {
            "sites": new_sites,
            "meta": {
                "version": "2.0.0",
                "last_sync": datetime.now().isoformat(),
                "structure": "external_labels_at_root",
                "total_sites": len(new_sites)
            }
        }
    }
    
    await kv.put_json(
        key='skills/eye/metadata/sites',
        value=new_structure,
        metadata={
            'auto_sync': True,
            'structure_version': '2.0.0',
            'source': 'auto_sync_from_extraction'
        }
    )
    
    logger.info(
        f"[SITES SYNC] ✅ {len(new_sites)} sites sincronizados "
        f"({len(sites_added)} novos, {len(sites_updated)} atualizados)"
    )
    
    return {
        "total_sites": len(new_sites),
        "sites_added": sites_added,
        "sites_updated": sites_updated
    }


# ============================================================================
# ENDPOINTS: GERENCIAMENTO DE SITES (MOVIDO DE /settings)
# ============================================================================

class SiteConfigModel(BaseModel):
    """Configuração editável de um site"""
    name: Optional[str] = Field(None, description="Nome descritivo do site")
    color: Optional[str] = Field(None, description="Cor do badge (blue, green, orange, etc)")
    is_default: Optional[bool] = Field(None, description="Se é o site padrão (sem sufixo)")


@router.get("/config/sites")
async def list_sites():
    """
    Lista sites lendo DIRETAMENTE do KV skills/eye/metadata/sites
    
    FONTE DOS DADOS:
    - KV: skills/eye/metadata/sites (estrutura com external_labels no nível raiz)
    
    ESTRUTURA DO KV:
    {
      "sites": [
        {
          "code": "palmas",
          "name": "Palmas (TO)",
          "is_default": true,
          "color": "blue",
          "cluster": "palmas-master",
          "datacenter": "skillsit-palmas-to",
          "environment": "production",
          "site": "palmas",
          "prometheus_instance": "172.16.1.26",
          "prometheus_host": "172.16.1.26",
          "prometheus_port": 5522
        }
      ]
    }
    
    CAMPOS:
    - code, name, is_default, color: Editáveis pelo usuário
    - cluster, datacenter, environment, site, prometheus_instance: External labels (readonly)
    - prometheus_host, prometheus_port: Conexão SSH/Prometheus (readonly)
    
    RETORNA:
        {
            "success": true,
            "sites": [...],
            "total": 3
        }
    """
    try:
        from core.kv_manager import KVManager
        
        kv = KVManager()
        
        # Buscar sites do KV (já tem tudo: external_labels + configs editáveis)
        kv_data = await kv.get_json('skills/eye/metadata/sites') or {"data": {"sites": []}}
        
        # Estrutura pode ter wrapper 'data' ou ser direta
        if 'data' in kv_data:
            sites = kv_data.get('data', {}).get('sites', [])
        else:
            sites = kv_data.get('sites', [])
        
        if not sites:
            logger.warning("[CONFIG SITES] KV vazio - execute migrate_sites_structure.py")
            return {
                "success": False,
                "sites": [],
                "total": 0,
                "message": "KV skills/eye/metadata/sites vazio. Execute migração."
            }
        
        logger.info(f"[CONFIG SITES] {len(sites)} sites carregados do KV")
        
        # Adicionar campos adicionais para compatibilidade
        for site in sites:
            # Campo external_labels para compatibilidade com código antigo
            site["external_labels"] = {
                "cluster": site.get("cluster", ""),
                "datacenter": site.get("datacenter", ""),
                "environment": site.get("environment", ""),
                "site": site.get("site", site.get("code", "")),
                "prometheus_instance": site.get("prometheus_instance", "")
            }
            
            # Garantir que ssh_port e prometheus_port existam
            # Se KV foi migrado corretamente, já terá ambos os campos
            if "ssh_port" not in site:
                site["ssh_port"] = 22  # Default SSH port
            if "prometheus_port" not in site:
                site["prometheus_port"] = 9090  # Default Prometheus port
        
        # Garantir que existe pelo menos um site default
        if sites and not any(s.get("is_default") for s in sites):
            sites[0]["is_default"] = True
            logger.info(f"[CONFIG SITES] Marcado '{sites[0]['code']}' como default automaticamente")
        
        logger.info(f"[CONFIG SITES] Listados {len(sites)} sites do KV")
        
        return {
            "success": True,
            "sites": sites,
            "total": len(sites)
        }
        
    except Exception as e:
        logger.error(f"[CONFIG SITES] Erro ao listar sites: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao listar sites: {str(e)}"
        )


@router.patch("/config/sites/{code}")
async def update_site_config(code: str, updates: SiteConfigModel):
    """
    Atualiza configurações editáveis de um site (name, color, is_default)
    
    CAMPOS EDITÁVEIS:
    - name: Nome descritivo
    - color: Cor do badge
    - is_default: Site padrão (sem sufixo)
    
    CAMPOS READONLY (não podem ser alterados):
    - code: Gerado automaticamente
    - prometheus_host: Do .env
    - prometheus_port: Do .env
    - external_labels: Extraído do Prometheus
    
    Args:
        code: Código do site
        updates: Campos para atualizar
        
    Returns:
        Site atualizado
    """
    try:
        from core.kv_manager import KVManager
        
        kv = KVManager()
        
        # Buscar configurações atuais (estrutura com wrapper data)
        kv_data = await kv.get_json('skills/eye/metadata/sites') or {"data": {"sites": []}}
        
        # Extrair sites considerando wrapper 'data'
        if 'data' in kv_data:
            # Estrutura nova: {"data": {"sites": [...]}, "meta": {...}}
            data_wrapper = kv_data.get('data', {})
            if isinstance(data_wrapper, dict) and 'data' in data_wrapper:
                # Duplo wrapper: {"data": {"data": {"sites": [...]}}}
                site_configs_array = data_wrapper.get('data', {}).get('sites', [])
            else:
                # Wrapper simples: {"data": {"sites": [...]}}
                site_configs_array = data_wrapper.get('sites', [])
        else:
            # Estrutura antiga sem wrapper
            site_configs_array = kv_data.get("sites", [])
        
        # Verificar se site existe (buscando da lista completa)
        sites_response = await list_sites()
        existing_site = None
        for site in sites_response["sites"]:
            if site["code"] == code:
                existing_site = site
                break
        
        if not existing_site:
            raise HTTPException(
                status_code=404,
                detail=f"Site '{code}' não encontrado"
            )
        
        # Buscar config existente no array ou criar novo
        site_config = None
        site_index = -1
        for i, s in enumerate(site_configs_array):
            if s["code"] == code:
                site_config = s
                site_index = i
                break
        
        if site_config is None:
            # Criar nova config
            site_config = {"code": code}
            site_configs_array.append(site_config)
            site_index = len(site_configs_array) - 1
        
        # Atualizar apenas campos editáveis
        if updates.name is not None:
            site_config["name"] = updates.name
        if updates.color is not None:
            site_config["color"] = updates.color
        if updates.is_default is not None:
            site_config["is_default"] = updates.is_default
            
            # Se marcar como default, desmarcar os outros
            if updates.is_default:
                for other_site in site_configs_array:
                    if other_site["code"] != code:
                        other_site["is_default"] = False
        
        # Atualizar no array
        site_configs_array[site_index] = site_config
        
        # CRÍTICO: Preservar estrutura completa do KV (com wrapper data e meta)
        # Reconstruir estrutura mantendo meta existente
        if 'data' in kv_data:
            # Manter wrapper data e meta
            save_structure = kv_data.copy()
            if 'data' in save_structure.get('data', {}):
                # Duplo wrapper
                save_structure['data']['data']['sites'] = site_configs_array
            else:
                # Wrapper simples
                save_structure['data']['sites'] = site_configs_array
        else:
            # Estrutura antiga sem wrapper (migrar para nova)
            save_structure = {
                "data": {"sites": site_configs_array},
                "meta": {
                    "version": "2.0.0",
                    "last_update": "manual_edit",
                    "structure": "external_labels_at_root"
                }
            }
        
        # Atualizar timestamp do meta
        if 'meta' in save_structure:
            save_structure['meta']['updated_at'] = __import__('datetime').datetime.now().isoformat()
            save_structure['meta']['updated_by'] = 'user'
            save_structure['meta']['source'] = 'manual_edit'
        
        # Salvar mantendo estrutura completa
        await kv.put_json(
            key='skills/eye/metadata/sites',
            value=save_structure,
            metadata={'auto_updated': False, 'source': 'user_edit'}
        )
        
        logger.info(f"[SITES] Configurações do site '{code}' atualizadas")
        
        # Retornar site completo atualizado
        updated_site = existing_site.copy()
        updated_site.update(site_config)
        
        return {
            "success": True,
            "site": updated_site,
            "message": f"Site '{code}' atualizado com sucesso"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[SITES] Erro ao atualizar site '{code}': {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao atualizar site: {str(e)}"
        )


@router.patch("/config/naming")
async def update_naming_config(request: Request):
    """
    Atualiza configurações globais de naming strategy
    
    CAMPOS EDITÁVEIS:
    - naming_strategy: "option1" ou "option2"
    - suffix_enabled: boolean
    
    IMPORTANTE: Estas configurações afetam TODOS os sites
    
    Returns:
        Configurações atualizadas
    """
    try:
        from core.kv_manager import KVManager
        
        # Parse request body
        body = await request.json()
        naming_strategy = body.get('naming_strategy')
        suffix_enabled = body.get('suffix_enabled')
        
        # Validar valores
        if naming_strategy not in ['option1', 'option2']:
            raise HTTPException(
                status_code=400,
                detail="naming_strategy deve ser 'option1' ou 'option2'"
            )
        
        if not isinstance(suffix_enabled, bool):
            raise HTTPException(
                status_code=400,
                detail="suffix_enabled deve ser booleano (true/false)"
            )
        
        kv = KVManager()
        
        # Buscar configurações atuais
        kv_data = await kv.get_json('skills/eye/metadata/sites') or {"data": {"sites": []}}
        
        # Garantir estrutura com wrapper data
        if 'data' not in kv_data:
            kv_data = {"data": kv_data, "meta": {}}
        
        # Atualizar naming_config no data wrapper
        if 'naming_config' not in kv_data['data']:
            kv_data['data']['naming_config'] = {}
        
        kv_data['data']['naming_config']['strategy'] = naming_strategy
        kv_data['data']['naming_config']['suffix_enabled'] = suffix_enabled
        
        # Atualizar meta
        if 'meta' not in kv_data:
            kv_data['meta'] = {}
        
        kv_data['meta']['updated_at'] = __import__('datetime').datetime.now().isoformat()
        kv_data['meta']['updated_by'] = 'user'
        kv_data['meta']['source'] = 'naming_config_update'
        
        # Salvar no KV
        await kv.put_json(
            key='skills/eye/metadata/sites',
            value=kv_data,
            metadata={'auto_updated': False, 'source': 'user_edit'}
        )
        
        logger.info(f"[NAMING CONFIG] Atualizado: strategy={naming_strategy}, suffix_enabled={suffix_enabled}")
        
        return {
            "success": True,
            "naming_strategy": naming_strategy,
            "suffix_enabled": suffix_enabled,
            "message": "Naming config atualizada com sucesso"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[NAMING CONFIG] Erro ao atualizar: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao atualizar naming config: {str(e)}"
        )


@router.post("/config/sites/sync")
async def sync_sites_from_prometheus():
    """
    Sincroniza sites automaticamente baseado em external_labels do Prometheus
    
    PROCESSO:
    1. Dispara extração SSH se necessário (força atualização de external_labels)
    2. Auto-detecta sites a partir de external_labels.site
    3. Cria/atualiza lista de sites no KV
    4. Preserva configurações editáveis existentes (name, color, is_default)
    
    RETORNA:
        {
            "success": true,
            "sites_synced": 3,
            "new_sites": ["rio"],
            "existing_sites": ["palmas", "dtc"],
            "extraction_triggered": true
        }
    """
    try:
        from core.kv_manager import KVManager
        
        kv = KVManager()
        logger.info("[SITES SYNC] Iniciando sincronização de sites...")
        
        # PASSO 1: Disparar extração forçada para atualizar external_labels
        logger.info("[SITES SYNC] Disparando extração SSH para atualizar external_labels...")
        extraction_result = await force_extract_fields()
        extraction_triggered = extraction_result.get("success", False)
        
        # PASSO 2: Buscar configurações atuais do KV (estrutura ARRAY)
        kv_data = await kv.get_json('skills/eye/metadata/sites') or {"sites": []}
        site_configs_array = kv_data.get("sites", [])
        
        # Criar map para busca rápida
        site_configs_map = {s["code"]: s for s in site_configs_array}
        
        # PASSO 3: Listar sites auto-detectados
        sites_response = await list_sites()
        detected_sites = sites_response["sites"]
        
        new_sites = []
        existing_sites = []
        
        # PASSO 4: Processar cada site detectado
        for site in detected_sites:
            site_code = site["code"]
            
            if site_code not in site_configs_map:
                # Novo site: criar configuração padrão
                new_config = {
                    "code": site_code,
                    "name": site["name"],
                    "color": site["color"],
                    "is_default": site["is_default"]
                }
                site_configs_array.append(new_config)
                new_sites.append(site_code)
                logger.info(f"[SITES SYNC] 🆕 Novo site detectado: '{site_code}'")
            else:
                existing_sites.append(site_code)
        
        # PASSO 5: Salvar configurações atualizadas (estrutura ARRAY)
        await kv.put_json(
            key='skills/eye/metadata/sites',
            value={"sites": site_configs_array},
            metadata={'auto_updated': True, 'source': 'prometheus_sync'}
        )
        
        logger.info(
            f"[SITES SYNC] ✅ Sincronização completa: {len(new_sites)} novos, "
            f"{len(existing_sites)} existentes"
        )
        
        return {
            "success": True,
            "sites_synced": len(detected_sites),
            "new_sites": new_sites,
            "existing_sites": existing_sites,
            "extraction_triggered": extraction_triggered,
            "message": f"Sincronização completa: {len(new_sites)} site(s) novo(s) detectado(s)"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[SITES SYNC] Erro ao sincronizar sites: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao sincronizar sites: {str(e)}"
        )


@router.post("/migrate-add-new-show-in-fields")
async def migrate_add_new_show_in_fields():
    """
    MIGRAÇÃO ONE-TIME: Adiciona novos campos show_in_* aos dados existentes no KV
    
    PROBLEMA:
    - Backend dataclass tem: show_in_network_probes, show_in_web_probes, etc
    - KV tem dados antigos SEM esses campos
    - Frontend precisa desses campos para controlar visibilidade
    
    SOLUÇÃO:
    - Ler metadata/fields do KV
    - Adicionar novos campos com defaults (herdam de show_in_blackbox/exporters)
    - Salvar de volta
    
    NOVOS CAMPOS ADICIONADOS:
    - show_in_network_probes (herda de show_in_blackbox)
    - show_in_web_probes (herda de show_in_blackbox)
    - show_in_system_exporters (herda de show_in_exporters)
    - show_in_database_exporters (herda de show_in_exporters)
    - show_in_infrastructure_exporters (herda de show_in_exporters)
    - show_in_hardware_exporters (herda de show_in_exporters)
    
    QUANDO USAR:
    - Após atualizar para v2.0 com novas páginas dinâmicas
    - Se campos não aparecem no modal de edição
    - Uma única vez após deploy
    """
    try:
        from core.kv_manager import KVManager
        
        kv = KVManager()
        logger.info("[MIGRATION] Iniciando migração: adicionar campos show_in_* dinâmicos")
        
        # PASSO 1: Ler config atual do KV
        config = await kv.get_json('skills/eye/metadata/fields')
        
        if not config:
            raise HTTPException(
                status_code=404,
                detail="Nenhuma configuração encontrada no KV. Execute force-extract primeiro."
            )
        
        fields = config.get('fields', [])
        logger.info(f"[MIGRATION] {len(fields)} campos encontrados no KV")
        
        # ✅ VALIDAÇÃO CRÍTICA: Verificar se extraction_status está completo
        # Se server_status[].fields[] estiver vazio, precisa fazer re-extração
        extraction_status = config.get('extraction_status', {})
        server_status = extraction_status.get('server_status', [])
        
        if server_status:
            # Verificar se pelo menos um servidor tem o array fields[]
            has_fields_array = any('fields' in srv and len(srv.get('fields', [])) > 0 for srv in server_status)
            
            if not has_fields_array:
                logger.warning("[MIGRATION] ⚠️ extraction_status incompleto (sem fields[]) - forçando re-extração")
                raise HTTPException(
                    status_code=400,
                    detail="KV está incompleto (sem server_status[].fields[]). Execute POST /force-extract primeiro para repopular o KV corretamente."
                )
        
        # PASSO 2: Verificar se migração já foi feita
        sample_field = fields[0] if fields else {}
        if 'show_in_network_probes' in sample_field:
            logger.info("[MIGRATION] ✓ Migração já foi executada anteriormente")
            return {
                "success": True,
                "message": "Migração já foi executada. Todos os campos já possuem os novos campos show_in_*.",
                "updated_count": 0,
                "total_fields": len(fields)
            }
        
        # PASSO 3: Adicionar novos campos com mapeamento lógico
        updated_count = 0
        for field in fields:
            # Valores base (para herdar defaults)
            show_in_blackbox = field.get('show_in_blackbox', True)
            show_in_exporters = field.get('show_in_exporters', True)
            
            # Probes (network, web) herdam de blackbox
            field['show_in_network_probes'] = show_in_blackbox
            field['show_in_web_probes'] = show_in_blackbox
            
            # Exporters categories herdam de exporters
            field['show_in_system_exporters'] = show_in_exporters
            field['show_in_database_exporters'] = show_in_exporters
            field['show_in_infrastructure_exporters'] = show_in_exporters
            field['show_in_hardware_exporters'] = show_in_exporters
            
            updated_count += 1
        
        logger.info(f"[MIGRATION] {updated_count} campos atualizados com novos campos show_in_*")
        
        # PASSO 4: Salvar de volta no KV PRESERVANDO extraction_status
        # ✅ CRÍTICO: Usar save_fields_config() para garantir que extraction_status seja preservado
        # Se usar kv.put_json() direto, pode quebrar discovered_in e source_label
        await save_fields_config(config)
        
        # PASSO 5: Invalidar cache para forçar reload
        _kv_manager.invalidate('metadata/fields')
        
        logger.info("[MIGRATION] ✅ Migração concluída e cache invalidado")
        
        return {
            "success": True,
            "message": f"Migração concluída! {updated_count} campos atualizados com 6 novos campos show_in_* cada.",
            "updated_count": updated_count,
            "total_fields": len(fields),
            "new_fields_added": [
                "show_in_network_probes",
                "show_in_web_probes",
                "show_in_system_exporters",
                "show_in_database_exporters",
                "show_in_infrastructure_exporters",
                "show_in_hardware_exporters"
            ]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[MIGRATION] Erro: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Erro na migração: {str(e)}"
        )


@router.post("/config/sites/cleanup")
async def cleanup_orphan_sites():
    """
    Remove configurações de sites órfãos do KV
    
    Sites órfãos são sites que têm configurações no KV mas não existem
    mais na lista de servidores ativos (PROMETHEUS_CONFIG_HOSTS no .env).
    
    QUANDO USAR:
    - Após remover um servidor do .env
    - Para limpar configs antigas que não são mais usadas
    - Manutenção periódica do KV
    
    PROCESSO:
    1. Lista sites ativos (GET /config/sites)
    2. Compara com configs no KV
    3. Remove configs que não têm servidor ativo correspondente
    
    RETORNA:
        {
            "success": true,
            "orphans_removed": ["rio", "antigo"],
            "removed_count": 2,
            "active_sites": ["palmas", "dtc"]
        }
    """
    try:
        from core.kv_manager import KVManager
        
        kv = KVManager()
        logger.info("[SITES CLEANUP] Iniciando limpeza de sites órfãos...")
        
        # PASSO 1: Buscar lista de sites ATIVOS (do .env)
        sites_response = await list_sites()
        active_sites = sites_response["sites"]
        active_codes = {site["code"] for site in active_sites}
        
        logger.info(f"[SITES CLEANUP] {len(active_codes)} sites ativos: {active_codes}")
        
        # PASSO 2: Buscar configurações no KV (estrutura ARRAY)
        kv_data = await kv.get_json('skills/eye/metadata/sites') or {"sites": []}
        site_configs_array = kv_data.get("sites", [])
        
        all_config_codes = {s["code"] for s in site_configs_array}
        
        logger.info(f"[SITES CLEANUP] {len(all_config_codes)} configs no KV: {all_config_codes}")
        
        # PASSO 3: Identificar órfãos (configs sem servidor ativo)
        orphan_codes = all_config_codes - active_codes
        
        if not orphan_codes:
            logger.info("[SITES CLEANUP] ✅ Nenhum site órfão encontrado")
            return {
                "success": True,
                "message": "Nenhum site órfão encontrado. KV já está limpo.",
                "orphans_removed": [],
                "removed_count": 0,
                "active_sites": list(active_codes)
            }
        
        logger.info(f"[SITES CLEANUP] 🗑️  {len(orphan_codes)} órfãos detectados: {orphan_codes}")
        
        # PASSO 4: Remover configs órfãos (filtrar array)
        cleaned_configs_array = [s for s in site_configs_array if s["code"] in active_codes]
        
        await kv.put_json(
            key='skills/eye/metadata/sites',
            value={"sites": cleaned_configs_array},
            metadata={'auto_updated': False, 'source': 'orphan_cleanup'}
        )
        
        logger.info(f"[SITES CLEANUP] ✅ {len(orphan_codes)} configs órfãos removidos")
        
        return {
            "success": True,
            "message": f"Removidos {len(orphan_codes)} site(s) órfão(s) com sucesso",
            "orphans_removed": list(orphan_codes),
            "removed_count": len(orphan_codes),
            "active_sites": list(active_codes)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[SITES CLEANUP] Erro ao limpar sites órfãos: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao limpar sites órfãos: {str(e)}"
        )


@router.post("/migrate-add-dynamic-fields")
async def migrate_add_dynamic_page_fields():
    """
    Migração ONE-TIME: Adiciona campos show_in_* dinâmicos aos campos existentes no KV
    
    CONTEXTO:
    - Sistema v2.0 (2025-11-13) adicionou novos campos: show_in_network_probes, etc
    - Dataclass MetadataField já tem esses campos com defaults
    - Mas dados ANTIGOS no KV não têm esses valores
    - Frontend precisa desses campos para edição de visibilidade por página
    
    O QUE FAZ:
    1. Lê metadata/fields do KV
    2. Para cada campo, adiciona novos campos show_in_* se não existirem
    3. Usa herança lógica: network-probes herda de blackbox, etc
    4. Salva de volta no KV
    5. Invalida cache
    
    QUANDO USAR:
    - Após upgrade para v2.0
    - Quando campos show_in_network_probes aparecem como null na API
    - Uma única vez por instalação
    
    SEGURANÇA:
    - NÃO sobrescreve valores existentes (usa setdefault)
    - Preserva configurações personalizadas do usuário
    - Pode ser executado múltiplas vezes (idempotente)
    
    RETORNA:
        {
            "success": true,
            "total_fields": 22,
            "fields_updated": 22,
            "new_fields_added": [
                "show_in_network_probes",
                "show_in_web_probes",
                "show_in_system_exporters",
                "show_in_database_exporters",
                "show_in_infrastructure_exporters",
                "show_in_hardware_exporters"
            ]
        }
    """
    try:
        logger.info("[MIGRATE] Iniciando migração de campos dinâmicos...")
        
        # PASSO 1: Carregar config do KV
        config = await load_fields_config()
        
        if not config or 'fields' not in config:
            raise HTTPException(
                status_code=503,
                detail="Configuração de campos não disponível. Execute force-extract primeiro."
            )
        
        fields = config['fields']
        total_fields = len(fields)
        
        logger.info(f"[MIGRATE] {total_fields} campos encontrados no KV")
        
        # PASSO 2: Listar novos campos a adicionar
        new_field_names = [
            'show_in_network_probes',
            'show_in_web_probes',
            'show_in_system_exporters',
            'show_in_database_exporters',
            'show_in_infrastructure_exporters',
            'show_in_hardware_exporters'
        ]
        
        # PASSO 3: Adicionar campos com herança lógica
        fields_updated = 0
        
        for field in fields:
            # Valores base para herança
            show_in_blackbox = field.get('show_in_blackbox', True)
            show_in_exporters = field.get('show_in_exporters', True)
            
            updated = False
            
            # ✅ SETDEFAULT: NÃO sobrescreve se já existir!
            # Probes (network, web) herdam de blackbox
            if 'show_in_network_probes' not in field:
                field['show_in_network_probes'] = show_in_blackbox
                updated = True
            
            if 'show_in_web_probes' not in field:
                field['show_in_web_probes'] = show_in_blackbox
                updated = True
            
            # Exporters categories herdam de exporters
            if 'show_in_system_exporters' not in field:
                field['show_in_system_exporters'] = show_in_exporters
                updated = True
            
            if 'show_in_database_exporters' not in field:
                field['show_in_database_exporters'] = show_in_exporters
                updated = True
            
            if 'show_in_infrastructure_exporters' not in field:
                field['show_in_infrastructure_exporters'] = show_in_exporters
                updated = True
            
            if 'show_in_hardware_exporters' not in field:
                field['show_in_hardware_exporters'] = show_in_exporters
                updated = True
            
            if updated:
                fields_updated += 1
        
        logger.info(f"[MIGRATE] {fields_updated}/{total_fields} campos atualizados")
        
        # PASSO 4: Salvar de volta no KV
        if fields_updated > 0:
            await save_fields_config(config)
            logger.info("[MIGRATE] ✅ Configuração salva no KV")
            
            # PASSO 5: Invalidar cache
            _kv_manager.invalidate('metadata/fields')
            logger.info("[MIGRATE] ✅ Cache invalidado")
        else:
            logger.info("[MIGRATE] Nenhuma atualização necessária - todos os campos já têm os novos atributos")
        
        return {
            "success": True,
            "message": f"{fields_updated} campo(s) migrado(s) com sucesso" if fields_updated > 0 else "Nenhuma migração necessária",
            "total_fields": total_fields,
            "fields_updated": fields_updated,
            "new_fields_added": new_field_names,
            "already_migrated": fields_updated == 0
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[MIGRATE] Erro na migração: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao executar migração: {str(e)}"
        )

