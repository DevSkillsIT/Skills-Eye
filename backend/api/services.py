"""
API endpoints para gerenciamento de servicos
Conecta ao servidor Consul real e retorna dados de servicos com metadados completos

NOTA: Refatorado em SPEC-CLEANUP-001 v1.4.0
- Removidos endpoints GET de listagem (substituidos por monitoring-types/monitoring-data)
- Mantidos apenas endpoints CRUD (POST, PUT, DELETE) e bulk operations
- Endpoints removidos:
  - GET / (list_services)
  - GET /catalog/names (get_service_catalog_names)
  - GET /metadata/unique-values (get_unique_metadata_values)
  - GET /search/by-metadata (search_services)
  - GET /{service_id} (get_service)
"""
from fastapi import APIRouter, HTTPException, Query, BackgroundTasks, Path
from typing import Dict, List, Optional, Any
from core.consul_manager import ConsulManager
from core.config import Config
from core.naming_utils import apply_site_suffix, extract_site_from_metadata
from core.consul_kv_config_manager import ConsulKVConfigManager
from core.cache_manager import LocalCache
from .models import (
    ServiceCreateRequest,
    ServiceUpdateRequest,
    ServiceListResponse,
    ServiceResponse,
    ErrorResponse
)
import logging

router = APIRouter(tags=["Services"])
logger = logging.getLogger(__name__)

# Singleton do cache local (SPRINT 2)
_catalog_cache = LocalCache(default_ttl_seconds=60)


# ============================================================================
# FUNCOES AUXILIARES DE VALIDACAO (SPRINT 2)
# ============================================================================

async def validate_monitoring_type(service_name: str, exporter_type: Optional[str] = None, category: Optional[str] = None) -> Dict[str, Any]:
    """
    Valida se o tipo de monitoramento existe no monitoring-types

    SPRINT 2: Validacao critica - verifica se tipo existe antes de criar servico

    Args:
        service_name: Nome do servico (job_name)
        exporter_type: Tipo do exporter (opcional, para validacao mais especifica)
        category: Categoria (opcional, para validacao mais especifica)

    Returns:
        Dict com informacoes do tipo encontrado

    Raises:
        HTTPException: Se tipo nao encontrado
    """
    try:
        from core.kv_manager import KVManager
        kv_manager = KVManager()

        # Buscar tipos do KV cache
        types_data = await kv_manager.get_json('skills/eye/monitoring-types')

        if not types_data or not types_data.get('all_types'):
            # Se KV vazio, tentar buscar diretamente do endpoint
            logger.warning("[VALIDATE-TYPE] KV vazio, tentando buscar tipos diretamente...")
            # Por enquanto, permitir criacao sem validacao se KV vazio (fallback)
            return {
                "valid": True,
                "job_name": service_name,
                "exporter_type": exporter_type or "unknown",
                "category": category or "unknown"
            }

        all_types = types_data.get('all_types', [])

        # Buscar tipo correspondente
        matching_type = None
        for type_def in all_types:
            if type_def.get('job_name') == service_name:
                # Verificar exporter_type se fornecido
                if exporter_type and type_def.get('exporter_type') != exporter_type:
                    continue
                # Verificar category se fornecido
                if category and type_def.get('category') != category:
                    continue
                matching_type = type_def
                break

        if not matching_type:
            raise HTTPException(
                status_code=400,
                detail={
                    "message": "Tipo de monitoramento nao encontrado",
                    "detail": f"Tipo '{service_name}' nao existe no monitoring-types. Verifique se o tipo esta configurado no Prometheus.",
                    "service_name": service_name,
                    "exporter_type": exporter_type,
                    "category": category
                }
            )

        return {
            "valid": True,
            "id": matching_type.get('id'),  # ID do tipo para form_schema
            "job_name": matching_type.get('job_name'),
            "exporter_type": matching_type.get('exporter_type'),
            "category": matching_type.get('category'),
            "display_name": matching_type.get('display_name'),
            "module": matching_type.get('module')
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[VALIDATE-TYPE] Erro ao validar tipo: {e}", exc_info=True)
        # Em caso de erro, permitir criacao (nao bloquear por falha de validacao)
        logger.warning(f"[VALIDATE-TYPE] Permitindo criacao sem validacao devido a erro: {e}")
        return {
            "valid": True,
            "job_name": service_name,
            "exporter_type": exporter_type or "unknown",
            "category": category or "unknown"
        }


async def validate_form_schema_fields(meta: Dict[str, Any], type_id: str, category: Optional[str] = None) -> List[str]:
    """
    Valida campos obrigatorios do form_schema

    Busca form_schema diretamente do tipo em skills/eye/monitoring-types (fonte unica de verdade)

    SPRINT 2: Validacao critica - verifica campos obrigatorios especificos do tipo

    Args:
        meta: Metadata do servico
        type_id: ID do tipo de monitoramento (ex: 'icmp', 'node_exporter')
        category: Categoria (opcional, nao usado mais - mantido para compatibilidade)

    Returns:
        Lista de erros encontrados (vazia se valido)
    """
    errors = []

    try:
        from core.kv_manager import KVManager

        kv_manager = KVManager()

        # Buscar tipo diretamente de monitoring-types (fonte unica)
        kv_data = await kv_manager.get_json('skills/eye/monitoring-types')

        if not kv_data or not kv_data.get('all_types'):
            # KV vazio - nao validar
            return errors

        # Buscar tipo por ID
        type_def = None
        for t in kv_data['all_types']:
            if t.get('id') == type_id:
                type_def = t
                break

        if not type_def:
            # Tipo nao encontrado - nao validar
            logger.warning(f"[VALIDATE-FORM-SCHEMA] Tipo '{type_id}' nao encontrado em monitoring-types")
            return errors

        # Extrair form_schema do tipo
        form_schema = type_def.get('form_schema')
        if not form_schema:
            # Tipo sem form_schema - nao validar
            return errors

        # Validar campos obrigatorios do form_schema
        required_fields = form_schema.get('fields', [])
        for field in required_fields:
            if field.get('required', False):
                field_name = field.get('name')
                if field_name and (field_name not in meta or not meta.get(field_name)):
                    errors.append(f"Campo obrigatorio do tipo '{field_name}' nao fornecido")

        # Validar required_metadata
        required_metadata = form_schema.get('required_metadata', [])
        for field_name in required_metadata:
            if field_name not in meta or not meta.get(field_name):
                errors.append(f"Campo metadata obrigatorio '{field_name}' nao fornecido")

        logger.info(f"[VALIDATE-FORM-SCHEMA] Validacao para tipo '{type_id}': {len(errors)} erros")

    except Exception as e:
        logger.error(f"[VALIDATE-FORM-SCHEMA] Erro ao validar form_schema: {e}", exc_info=True)
        # Nao bloquear por erro de validacao
        pass

    return errors


async def invalidate_monitoring_cache(category: Optional[str] = None):
    """
    Invalida cache apos operacoes CRUD

    SPRINT 2: Invalidacao critica - garante dados atualizados apos CRUD

    Args:
        category: Categoria do servico (opcional, para invalidacao especifica)
    """
    try:
        # Invalidar cache local (LocalCache)
        if category:
            await _catalog_cache.invalidate_pattern(f"catalog:*{category}*")
        else:
            await _catalog_cache.invalidate_pattern("catalog:*")

        logger.info(f"[CACHE] Cache invalidado para categoria: {category or 'all'}")
    except Exception as e:
        logger.error(f"[CACHE] Erro ao invalidar cache: {e}", exc_info=True)


# ============================================================================
# POST ROUTES - Criar servicos
# ============================================================================

@router.post("/", include_in_schema=True)
@router.post("")
async def create_service(
    request: ServiceCreateRequest,
    background_tasks: BackgroundTasks
):
    """
    Cria um novo servico no Consul com validacoes completas

    Valida:
    - Campos obrigatorios (module, company, project, env, name, instance)
    - Formato correto do instance baseado no modulo
    - Duplicatas (mesma combinacao de module/company/project/env/name)

    Retorna o ID do servico criado
    """
    try:
        consul = ConsulManager()

        # Converter request para dict
        service_data = request.model_dump()

        # CRITICAL: Sanitizar o ID antes de processar (similar ao BlackboxManager)
        # Isso garante que IDs com caracteres especiais sejam normalizados
        if 'id' in service_data and service_data['id']:
            service_data['id'] = ConsulManager.sanitize_service_id(service_data['id'])
            logger.info(f"ID sanitizado para: {service_data['id']}")

        # SPRINT 2: Validar tipo de monitoramento (CRITICO)
        meta = service_data.get("Meta", {})
        service_name = service_data.get("service") or service_data.get("name", "")
        exporter_type = meta.get("exporter_type")
        category = meta.get("category")
        type_id = None  # ID do tipo para validacao de form_schema

        if service_name:
            try:
                type_info = await validate_monitoring_type(service_name, exporter_type, category)
                type_id = type_info.get('id')  # Capturar ID do tipo
                logger.info(f"[VALIDATE-TYPE] Tipo validado: {type_info.get('display_name')} ({type_info.get('id')})")
            except HTTPException as e:
                # Re-raise HTTPException (tipo nao encontrado)
                raise e
            except Exception as e:
                logger.warning(f"[VALIDATE-TYPE] Erro ao validar tipo (permitindo criacao): {e}")

        # SPRINT 2: Validar campos obrigatorios do form_schema (SOLUCAO PRAGMATICA)
        if type_id:
            form_schema_errors = await validate_form_schema_fields(meta, type_id, category)
            if form_schema_errors:
                raise HTTPException(
                    status_code=400,
                    detail={
                        "message": "Erros de validacao do form_schema",
                        "errors": form_schema_errors
                    }
                )

        # Validar dados do servico (validacao generica)
        is_valid, errors = await consul.validate_service_data(service_data)
        if not is_valid:
            raise HTTPException(
                status_code=400,
                detail={
                    "message": "Erros de validacao encontrados",
                    "errors": errors
                }
            )

        # CORRECAO: Gerar ID dinamicamente se nao fornecido
        if 'id' not in service_data or not service_data.get('id'):
            meta = service_data.get("Meta", {})
            try:
                service_data['id'] = await consul.generate_dynamic_service_id(meta)
                logger.info(f"ID gerado dinamicamente: {service_data['id']}")
            except ValueError as e:
                raise HTTPException(
                    status_code=400,
                    detail={
                        "message": "Erro ao gerar ID do servico",
                        "error": str(e)
                    }
                )

        # CORRECAO: Verificar duplicatas usando campos obrigatorios do KV
        is_duplicate = await consul.check_duplicate_service(
            meta=meta,
            target_node_addr=service_data.get("node_addr")
        )

        if is_duplicate:
            # Buscar campos obrigatorios para mensagem de erro
            required_fields = Config.get_required_fields()
            fields_str = "/".join(required_fields + ['name'])
            raise HTTPException(
                status_code=409,
                detail={
                    "message": "Servico duplicado",
                    "detail": f"Ja existe um servico com a mesma combinacao de campos obrigatorios ({fields_str})"
                }
            )

        # MULTI-SITE SUPPORT: Adicionar tag automatica baseado no campo "site"
        # Se o metadata contem campo "site", adicionar como tag para filtros no prometheus.yml
        site = meta.get("site")
        if site:
            tags = service_data.get("Tags", service_data.get("tags", []))
            if not isinstance(tags, list):
                tags = []

            # Adicionar tag do site se nao existir
            if site not in tags:
                tags.append(site)
                logger.info(f"Adicionada tag automatica para site: {site}")

            # Garantir que o campo Tags esta correto (Consul usa "Tags" com T maiusculo)
            service_data["Tags"] = tags
            if "tags" in service_data:
                del service_data["tags"]

        # MULTI-SITE SUPPORT: Aplicar sufixo ao service name (Opcao 2)
        # Se NAMING_STRATEGY=option2 e site != DEFAULT_SITE, adiciona sufixo _site
        # Exemplo: selfnode_exporter + site=rio -> selfnode_exporter_rio
        if "name" in service_data and service_data["name"]:
            original_name = service_data["name"]
            site = extract_site_from_metadata(meta)
            cluster = meta.get("cluster")

            # Aplicar sufixo baseado na configuracao
            suffixed_name = apply_site_suffix(original_name, site=site, cluster=cluster)

            if suffixed_name != original_name:
                service_data["name"] = suffixed_name
                logger.info(f"[MULTI-SITE] Service name alterado: {original_name} -> {suffixed_name} (site={site})")

        # Registrar servico
        logger.info(f"Registrando novo servico: {service_data.get('id')}")
        success = await consul.register_service(
            service_data,
            service_data.get("node_addr")
        )

        if success:
            # SPRINT 2: Invalidar cache apos criacao
            background_tasks.add_task(
                invalidate_monitoring_cache,
                category
            )

            # Log assincrono
            background_tasks.add_task(
                log_action,
                f"Servico criado: {service_data.get('id')} - {meta.get('name')}"
            )

            return {
                "success": True,
                "message": "Servico criado com sucesso",
                "service_id": service_data.get("id"),
                "data": service_data
            }
        else:
            raise HTTPException(
                status_code=500,
                detail="Falha ao registrar servico no Consul"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao criar servico: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/bulk/register", include_in_schema=True)
async def bulk_register_services(
    services: List[ServiceCreateRequest],
    node_addr: Optional[str] = Query(None, description="Endereco do no onde registrar"),
    background_tasks: BackgroundTasks = None
):
    """
    Registra multiplos servicos em lote

    Preservado para importacao em massa e automacao futura.
    Retorna resultado individual para cada servico.
    """
    try:
        consul = ConsulManager()

        services_data = [s.model_dump() for s in services]
        for service_data in services_data:
            if node_addr:
                service_data["node_addr"] = node_addr

        logger.info(f"Registrando {len(services_data)} servicos em lote")
        results = await consul.bulk_register_services(services_data, node_addr)

        success_count = sum(1 for v in results.values() if v)
        failed_count = len(results) - success_count

        background_tasks.add_task(
            log_action,
            f"Registro em lote: {success_count} sucessos, {failed_count} falhas"
        )

        return {
            "success": True,
            "message": f"Registrados {success_count}/{len(results)} servicos",
            "results": results,
            "summary": {
                "total": len(results),
                "success": success_count,
                "failed": failed_count
            }
        }

    except Exception as e:
        logger.error(f"Erro no registro em lote: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# PUT ROUTES - Atualizar servicos
# ============================================================================

@router.put("/{service_id:path}", include_in_schema=True)
async def update_service(
    service_id: str = Path(..., description="ID do servico a atualizar"),
    request: ServiceUpdateRequest = None,
    background_tasks: BackgroundTasks = None
):
    """
    Atualiza um servico existente

    IMPORTANTE: O service_id pode conter caracteres especiais (/, @) que devem ser codificados na URL

    Nota: Consul nao tem endpoint de update nativo, entao fazemos:
    1. Deregister do servico antigo
    2. Register do servico com novos dados
    """
    try:
        consul = ConsulManager()

        # CRITICAL: Sanitizar o service_id recebido da URL
        # Garante que mesmo IDs com caracteres especiais sejam normalizados
        service_id = ConsulManager.sanitize_service_id(service_id)
        logger.info(f"Atualizando servico com ID sanitizado: {service_id}")

        # Buscar servico existente
        existing_service = await consul.get_service_by_id(
            service_id,
            request.node_addr if request else None
        )

        if not existing_service:
            raise HTTPException(
                status_code=404,
                detail=f"Servico '{service_id}' nao encontrado"
            )

        # Mesclar dados existentes com novos dados
        # IMPORTANTE: Normalizar campos para formato do Consul (Uppercase)
        updated_service = existing_service.copy()
        if request:
            update_data = request.model_dump(exclude_unset=True)

            # Mapear campos lowercase (frontend) para Uppercase (Consul)
            field_mapping = {
                "address": "Address",
                "port": "Port",
                "tags": "Tags",
                "name": "Name",
            }

            for key, value in update_data.items():
                if value is not None and key != "node_addr":
                    # Usar o nome correto do campo (Uppercase se estiver no mapeamento)
                    consul_key = field_mapping.get(key, key)
                    updated_service[consul_key] = value

        # MULTI-SITE SUPPORT: Atualizar tag automatica baseado no campo "site"
        meta = updated_service.get("Meta", {})
        site = meta.get("site")
        if site:
            tags = updated_service.get("Tags", [])
            if not isinstance(tags, list):
                tags = []

            # Adicionar tag do site se nao existir
            if site not in tags:
                tags.append(site)
                logger.info(f"Adicionada tag automatica para site: {site}")

            updated_service["Tags"] = tags

        # MULTI-SITE SUPPORT: Aplicar sufixo ao service name (Opcao 2)
        # Se NAMING_STRATEGY=option2 e site != DEFAULT_SITE, adiciona sufixo _site
        if "Name" in updated_service and updated_service["Name"]:
            original_name = updated_service["Name"]
            site = extract_site_from_metadata(meta)
            cluster = meta.get("cluster")

            # Aplicar sufixo baseado na configuracao
            suffixed_name = apply_site_suffix(original_name, site=site, cluster=cluster)

            if suffixed_name != original_name:
                updated_service["Name"] = suffixed_name
                logger.info(f"[MULTI-SITE] Service name alterado: {original_name} -> {suffixed_name} (site={site})")

        # CORRECAO FASE 0: Validar dados do servico antes de atualizar (usando validacao dinamica)
        is_valid, errors = await consul.validate_service_data(updated_service)
        if not is_valid:
            raise HTTPException(
                status_code=400,
                detail={
                    "message": "Erros de validacao encontrados",
                    "errors": errors
                }
            )

        # CORRECAO FASE 0: Verificar duplicatas usando campos obrigatorios do KV (excluindo o proprio servico)
        is_duplicate = await consul.check_duplicate_service(
            meta=meta,
            exclude_sid=service_id,
            target_node_addr=request.node_addr if request else None
        )

        if is_duplicate:
            # Buscar campos obrigatorios para mensagem de erro
            required_fields = Config.get_required_fields()
            fields_str = "/".join(required_fields + ['name'])
            raise HTTPException(
                status_code=409,
                detail={
                    "message": "Servico duplicado",
                    "detail": f"Ja existe outro servico com a mesma combinacao de campos obrigatorios ({fields_str})"
                }
            )

        # Atualizar servico
        logger.info(f"Atualizando servico: {service_id}")
        success = await consul.update_service(
            service_id,
            updated_service,
            request.node_addr if request else None
        )

        if success:
            # SPRINT 2: Invalidar cache apos atualizacao
            meta = updated_service.get("Meta", {})
            category = meta.get("category")
            background_tasks.add_task(
                invalidate_monitoring_cache,
                category
            )

            background_tasks.add_task(
                log_action,
                f"Servico atualizado: {service_id}"
            )

            return {
                "success": True,
                "message": "Servico atualizado com sucesso",
                "service_id": service_id,
                "data": updated_service
            }
        else:
            raise HTTPException(
                status_code=500,
                detail="Falha ao atualizar servico no Consul"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao atualizar servico {service_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# DELETE ROUTES - Remover servicos
# ============================================================================

@router.delete("/bulk/deregister", include_in_schema=True)
async def bulk_deregister_services(
    service_ids: List[str],
    node_addr: Optional[str] = Query(None, description="Endereco do no onde remover"),
    background_tasks: BackgroundTasks = None
):
    """
    Remove multiplos servicos em lote

    Preservado para limpeza em massa e automacao futura.
    Retorna resultado individual para cada servico.
    """
    try:
        consul = ConsulManager()

        logger.info(f"Removendo {len(service_ids)} servicos em lote")
        results = await consul.bulk_deregister_services(service_ids, node_addr)

        success_count = sum(1 for v in results.values() if v)
        failed_count = len(results) - success_count

        background_tasks.add_task(
            log_action,
            f"Remocao em lote: {success_count} sucessos, {failed_count} falhas"
        )

        return {
            "success": True,
            "message": f"Removidos {success_count}/{len(results)} servicos",
            "results": results,
            "summary": {
                "total": len(results),
                "success": success_count,
                "failed": failed_count
            }
        }

    except Exception as e:
        logger.error(f"Erro na remocao em lote: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{service_id:path}", include_in_schema=True)
async def delete_service(
    service_id: str = Path(..., description="ID do servico a remover"),
    node_addr: Optional[str] = Query(None, description="Endereco do no onde remover"),
    background_tasks: BackgroundTasks = None
):
    """
    Remove um servico do Consul

    IMPORTANTE: O service_id pode conter caracteres especiais (/, @) que devem ser codificados na URL
    """
    try:
        consul = ConsulManager()

        # CRITICAL: Sanitizar o service_id recebido da URL
        # Garante que mesmo IDs com caracteres especiais sejam normalizados
        service_id = ConsulManager.sanitize_service_id(service_id)
        logger.info(f"Removendo servico com ID sanitizado: {service_id}")

        # Verificar se servico existe
        existing_service = await consul.get_service_by_id(service_id, node_addr)
        if not existing_service:
            raise HTTPException(
                status_code=404,
                detail=f"Servico '{service_id}' nao encontrado"
            )

        # Remover servico
        logger.info(f"Removendo servico: {service_id}")
        success = await consul.deregister_service(service_id, node_addr)

        if success:
            # SPRINT 2: Invalidar cache apos exclusao
            meta = existing_service.get("Meta", {})
            category = meta.get("category")
            background_tasks.add_task(
                invalidate_monitoring_cache,
                category
            )

            background_tasks.add_task(
                log_action,
                f"Servico removido: {service_id}"
            )

            return {
                "success": True,
                "message": "Servico removido com sucesso",
                "service_id": service_id
            }
        else:
            raise HTTPException(
                status_code=500,
                detail="Falha ao remover servico do Consul"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao remover servico {service_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


async def log_action(message: str):
    """Envia log via WebSocket (implementar com manager)"""
    logger.info(f"ACTION: {message}")
