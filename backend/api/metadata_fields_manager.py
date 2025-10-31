"""
API para Gerenciamento de Campos Metadata

Este módulo fornece endpoints para:
- Listar/criar/editar/deletar campos metadata
- Adicionar novo campo e sincronizar com prometheus.yml
- Reordenar campos
- Gerenciar categorias
"""

from fastapi import APIRouter, HTTPException, Body, Query
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional, cast, Tuple
from pathlib import Path
import json
import logging
import asyncio
from datetime import datetime, timedelta
import re
import yaml  # type: ignore
from yaml import nodes as yaml_nodes  # type: ignore

from core.multi_config_manager import MultiConfigManager
from core.server_utils import get_server_detector, ServerInfo

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
    category: str = Field("extra", description="Categoria do campo")
    editable: bool = Field(True, description="Pode ser editado")
    validation_regex: Optional[str] = Field(None, description="Regex de validação")


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


class AddFieldRequest(BaseModel):
    """Request para adicionar novo campo"""
    field: MetadataFieldModel
    sync_prometheus: bool = Field(True, description="Sincronizar com prometheus.yml")
    apply_to_jobs: Optional[List[str]] = Field(None, description="Jobs específicos (None = todos)")


class FieldSyncStatus(BaseModel):
    """Status de sincronização de um campo"""
    name: str
    display_name: str
    sync_status: str = Field(..., description="synced | outdated | missing | error")
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

def load_fields_config() -> Dict[str, Any]:
    """Carrega configuração de campos do JSON"""
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        logger.error(f"Arquivo de configuração não encontrado: {CONFIG_FILE}")
        raise HTTPException(status_code=500, detail="Arquivo de configuração não encontrado")
    except json.JSONDecodeError as e:
        logger.error(f"Erro ao parsear JSON: {e}")
        raise HTTPException(status_code=500, detail=f"Erro ao parsear configuração: {str(e)}")


def save_fields_config(config: Dict[str, Any]) -> bool:
    """Salva configuração de campos no JSON"""
    try:
        # Atualizar timestamp
        config['last_updated'] = datetime.utcnow().isoformat() + 'Z'

        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)

        logger.info(f"Configuração salva: {CONFIG_FILE}")
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

            servers.append({
                "id": f"{hostname}:{port}",
                "hostname": hostname,
                "port": port,
                "username": username,
                "type": server_type,
                "consul_node_name": consul_node_name,
                "display_name": display_name
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

        # Carregar configuração de campos
        try:
            config = load_fields_config()
            fields = config.get('fields', [])
            logger.info(f"[SYNC-STATUS] Carregados {len(fields)} campos do metadata_fields.json")
        except Exception as e:
            logger.error(f"[SYNC-STATUS] Erro ao carregar metadata_fields.json: {e}")
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
        total_error = 0

        for field in fields:
            field_name = field.get('name')
            field_display_name = field.get('display_name', field_name)
            field_source_label = field.get('source_label')

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

            if raw_target is None:
                # Campo não existe no Prometheus
                field_statuses.append(FieldSyncStatus(
                    name=field_name,
                    display_name=field_display_name,
                    sync_status='missing',
                    metadata_source_label=field_source_label,
                    prometheus_target_label=None,
                    message=f'Campo não encontrado no prometheus.yml'
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
            total_error=total_error,
            prometheus_file_path=prometheus_file_path,
            checked_at=datetime.now().isoformat(),
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
        config = load_fields_config()
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
        config = load_fields_config()

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

                            insertion_text = (
                                f"{'\n' if needs_leading_newline else ''}{item_indent}- source_labels: [\"{source_value}\"]\n"
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
    """
    config = load_fields_config()
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

    return FieldsConfigResponse(
        success=True,
        fields=fields,
        categories=config.get('categories', {}),
        total=len(fields),
        version=config.get('version', '1.0.0'),
        last_updated=config.get('last_updated', '')
    )


@router.get("/{field_name}")
async def get_field(field_name: str):
    """Busca campo específico por nome"""
    config = load_fields_config()
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
    config = load_fields_config()

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
    save_fields_config(config)

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


@router.put("/{field_name}")
async def update_field(field_name: str, field_data: MetadataFieldModel):
    """Atualiza campo existente"""
    config = load_fields_config()

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
    save_fields_config(config)

    return {
        "success": True,
        "message": f"Campo '{field_name}' atualizado com sucesso",
        "field": updated_field
    }


@router.delete("/{field_name}")
async def delete_field(
    field_name: str,
    remove_from_prometheus: bool = Query(False, description="Remover do prometheus.yml")
):
    """Deleta campo metadata"""
    config = load_fields_config()

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
    save_fields_config(config)

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
    config = load_fields_config()

    # Atualizar ordem de cada campo
    for field in config['fields']:
        field_name = field['name']
        if field_name in field_orders:
            field['order'] = field_orders[field_name]

    # Salvar
    save_fields_config(config)

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
    config = load_fields_config()
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


# ============================================================================
# REPLICAÇÃO E GERENCIAMENTO DE SERVIDORES
# ============================================================================

@router.post("/replicate-to-slaves")
async def replicate_to_slaves(
    source_server: Optional[str] = Body(None, description="ID do servidor origem (None = master)"),
    target_servers: Optional[List[str]] = Body(None, description="IDs dos servidores destino (None = todos slaves)")
):
    """
    Replica configurações do servidor master (ou especificado) para os slaves

    Copia:
    - prometheus.yml
    - Campos metadata configurados
    - Arquivos de rules
    """
    try:
        multi_config = MultiConfigManager()

        # Determinar servidor de origem
        if source_server:
            source_host = None
            for host in multi_config.hosts:
                if f"{host.hostname}:{host.port}" == source_server:
                    source_host = host
                    break
            if not source_host:
                raise HTTPException(status_code=404, detail=f"Servidor origem não encontrado: {source_server}")
        else:
            # Usar master (primeiro da lista)
            source_host = multi_config.hosts[0]

        # Determinar servidores de destino
        target_hosts = []
        if target_servers:
            for server_id in target_servers:
                for host in multi_config.hosts:
                    if f"{host.hostname}:{host.port}" == server_id:
                        target_hosts.append(host)
        else:
            # Todos os slaves (todos menos o master)
            target_hosts = multi_config.hosts[1:]

        if not target_hosts:
            return {
                "success": True,
                "message": "Nenhum servidor de destino para replicar"
            }

        # Ler prometheus.yml do servidor de origem
        from pathlib import Path
        source_file = None
        for f in multi_config.list_config_files('prometheus'):
            if f.filename == 'prometheus.yml' and f.host == source_host:
                source_file = f
                break

        if not source_file:
            raise HTTPException(status_code=404, detail="prometheus.yml não encontrado no servidor origem")

        source_content = multi_config.get_file_content_raw(source_file.path)

        # Replicar para cada servidor destino
        results = []
        for target_host in target_hosts:
            try:
                # Conectar ao servidor destino
                client = multi_config._get_ssh_client(target_host)
                sftp = client.open_sftp()

                # Fazer backup
                backup_path = f"/etc/prometheus/prometheus.yml.backup_replicated_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
                try:
                    sftp.rename("/etc/prometheus/prometheus.yml", backup_path)
                except:
                    pass  # Arquivo pode não existir

                # Escrever novo conteúdo
                with sftp.open("/etc/prometheus/prometheus.yml", 'w') as f:
                    f.write(source_content.encode('utf-8'))

                # Validar com promtool
                stdin, stdout, stderr = client.exec_command("promtool check config /etc/prometheus/prometheus.yml")
                exit_status = stdout.channel.recv_exit_status()

                sftp.close()
                client.close()

                if exit_status == 0:
                    results.append({
                        "server": f"{target_host.hostname}:{target_host.port}",
                        "success": True,
                        "message": "Configuração replicada com sucesso"
                    })
                else:
                    results.append({
                        "server": f"{target_host.hostname}:{target_host.port}",
                        "success": False,
                        "message": "Replicado mas falhou na validação promtool"
                    })
            except Exception as e:
                results.append({
                    "server": f"{target_host.hostname}:{target_host.port}",
                    "success": False,
                    "error": str(e)
                })

        success_count = sum(1 for r in results if r.get('success', False))

        return {
            "success": success_count > 0,
            "message": f"Replicação concluída: {success_count}/{len(results)} servidores",
            "source": f"{source_host.hostname}:{source_host.port}",
            "results": results
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao replicar: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/restart-prometheus")
async def restart_prometheus(
    server_ids: Optional[List[str]] = Body(None, description="IDs dos servidores (None = todos)")
):
    """
    Reinicia serviço Prometheus em servidores especificados

    Executa: systemctl reload prometheus
    """
    try:
        multi_config = MultiConfigManager()

        # Determinar servidores
        if server_ids:
            hosts = []
            for server_id in server_ids:
                for host in multi_config.hosts:
                    if f"{host.hostname}:{host.port}" == server_id:
                        hosts.append(host)
        else:
            hosts = multi_config.hosts

        results = []
        for host in hosts:
            try:
                client = multi_config._get_ssh_client(host)

                # Executar reload
                stdin, stdout, stderr = client.exec_command("systemctl reload prometheus")
                exit_status = stdout.channel.recv_exit_status()

                # Verificar se está ativo
                stdin, stdout, stderr = client.exec_command("systemctl is-active prometheus")
                is_active = stdout.read().decode('utf-8').strip()

                client.close()

                if exit_status == 0 and is_active == "active":
                    results.append({
                        "server": f"{host.hostname}:{host.port}",
                        "success": True,
                        "message": "Prometheus recarregado com sucesso",
                        "status": "active"
                    })
                else:
                    results.append({
                        "server": f"{host.hostname}:{host.port}",
                        "success": False,
                        "message": f"Serviço não está ativo (status: {is_active})"
                    })
            except Exception as e:
                results.append({
                    "server": f"{host.hostname}:{host.port}",
                    "success": False,
                    "error": str(e)
                })

        success_count = sum(1 for r in results if r.get('success', False))

        return {
            "success": success_count > 0,
            "message": f"Reinicialização concluída: {success_count}/{len(results)} servidores",
            "results": results
        }
    except Exception as e:
        logger.error(f"Erro ao reiniciar: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
