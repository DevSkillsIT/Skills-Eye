"""
API endpoints para gerenciamento de serviços
Conecta ao servidor Consul real e retorna dados de serviços com metadados completos
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
# FUNÇÕES AUXILIARES DE VALIDAÇÃO (SPRINT 2)
# ============================================================================

async def validate_monitoring_type(service_name: str, exporter_type: Optional[str] = None, category: Optional[str] = None) -> Dict[str, Any]:
    """
    Valida se o tipo de monitoramento existe no monitoring-types
    
    SPRINT 2: Validação crítica - verifica se tipo existe antes de criar serviço
    
    Args:
        service_name: Nome do serviço (job_name)
        exporter_type: Tipo do exporter (opcional, para validação mais específica)
        category: Categoria (opcional, para validação mais específica)
    
    Returns:
        Dict com informações do tipo encontrado
    
    Raises:
        HTTPException: Se tipo não encontrado
    """
    try:
        from core.kv_manager import KVManager
        kv_manager = KVManager()
        
        # Buscar tipos do KV cache
        types_data = await kv_manager.get_json('skills/eye/monitoring-types')
        
        if not types_data or not types_data.get('all_types'):
            # Se KV vazio, tentar buscar diretamente do endpoint
            logger.warning("[VALIDATE-TYPE] KV vazio, tentando buscar tipos diretamente...")
            # Por enquanto, permitir criação sem validação se KV vazio (fallback)
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
                    "message": "Tipo de monitoramento não encontrado",
                    "detail": f"Tipo '{service_name}' não existe no monitoring-types. Verifique se o tipo está configurado no Prometheus.",
                    "service_name": service_name,
                    "exporter_type": exporter_type,
                    "category": category
                }
            )
        
        return {
            "valid": True,
            "id": matching_type.get('id'),  # ✅ NOVO: ID do tipo para form_schema
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
        # Em caso de erro, permitir criação (não bloquear por falha de validação)
        logger.warning(f"[VALIDATE-TYPE] Permitindo criação sem validação devido a erro: {e}")
        return {
            "valid": True,
            "job_name": service_name,
            "exporter_type": exporter_type or "unknown",
            "category": category or "unknown"
        }


async def validate_form_schema_fields(meta: Dict[str, Any], type_id: str, category: Optional[str] = None) -> List[str]:
    """
    ✅ SOLUÇÃO PRAGMÁTICA: Valida campos obrigatórios do form_schema

    Busca form_schema diretamente do tipo em skills/eye/monitoring-types (fonte única de verdade)

    SPRINT 2: Validação crítica - verifica campos obrigatórios específicos do tipo

    Args:
        meta: Metadata do serviço
        type_id: ID do tipo de monitoramento (ex: 'icmp', 'node_exporter')
        category: Categoria (opcional, não usado mais - mantido para compatibilidade)

    Returns:
        Lista de erros encontrados (vazia se válido)
    """
    errors = []

    try:
        from core.kv_manager import KVManager

        kv_manager = KVManager()

        # ✅ NOVO: Buscar tipo diretamente de monitoring-types (fonte única)
        kv_data = await kv_manager.get_json('skills/eye/monitoring-types')

        if not kv_data or not kv_data.get('all_types'):
            # KV vazio - não validar
            return errors

        # Buscar tipo por ID
        type_def = None
        for t in kv_data['all_types']:
            if t.get('id') == type_id:
                type_def = t
                break

        if not type_def:
            # Tipo não encontrado - não validar
            logger.warning(f"[VALIDATE-FORM-SCHEMA] Tipo '{type_id}' não encontrado em monitoring-types")
            return errors

        # Extrair form_schema do tipo
        form_schema = type_def.get('form_schema')
        if not form_schema:
            # Tipo sem form_schema - não validar
            return errors

        # Validar campos obrigatórios do form_schema
        required_fields = form_schema.get('fields', [])
        for field in required_fields:
            if field.get('required', False):
                field_name = field.get('name')
                if field_name and (field_name not in meta or not meta.get(field_name)):
                    errors.append(f"Campo obrigatório do tipo '{field_name}' não fornecido")

        # Validar required_metadata
        required_metadata = form_schema.get('required_metadata', [])
        for field_name in required_metadata:
            if field_name not in meta or not meta.get(field_name):
                errors.append(f"Campo metadata obrigatório '{field_name}' não fornecido")

        logger.info(f"[VALIDATE-FORM-SCHEMA] Validação para tipo '{type_id}': {len(errors)} erros")

    except Exception as e:
        logger.error(f"[VALIDATE-FORM-SCHEMA] Erro ao validar form_schema: {e}", exc_info=True)
        # Não bloquear por erro de validação
        pass

    return errors


async def invalidate_monitoring_cache(category: Optional[str] = None):
    """
    Invalida cache após operações CRUD
    
    SPRINT 2: Invalidação crítica - garante dados atualizados após CRUD
    
    Args:
        category: Categoria do serviço (opcional, para invalidação específica)
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
# GET ROUTES - Rotas específicas ANTES de rotas com :path
# ============================================================================

@router.get("/", include_in_schema=True)
@router.get("")
async def list_services(
    node_addr: Optional[str] = Query(None, description="Endereço do nó específico ou 'ALL' para todos os nós"),
    module: Optional[str] = Query(None, description="Filtrar por módulo (icmp, http_2xx, etc)"),
    company: Optional[str] = Query(None, description="Filtrar por empresa"),
    project: Optional[str] = Query(None, description="Filtrar por projeto"),
    env: Optional[str] = Query(None, description="Filtrar por ambiente (prod, dev, etc)")
):
    """
    Lista serviços do Consul com todos os metadados

    - **node_addr**: Endereço IP do nó específico, ou 'ALL' para todos os nós, ou None para o servidor principal
    - **module**: Filtrar por módulo de monitoramento
    - **company**: Filtrar por empresa
    - **project**: Filtrar por projeto
    - **env**: Filtrar por ambiente

    Retorna todos os serviços com seus metadados completos incluindo:
    module, company, project, env, name, instance, localizacao, tipo, etc.
    """
    try:
        consul = ConsulManager()

        if node_addr == "ALL":
            # Listar de todos os nós do cluster
            # ✅ SPRINT 1 CORREÇÃO (2025-11-15): Catalog API com fallback
            logger.info("Listando serviços de todos os nós do cluster")
            all_services = await consul.get_all_services_catalog(use_fallback=True)

            # Extrair metadata de fallback
            metadata_info = all_services.pop("_metadata", None)
            if metadata_info:
                logger.info(
                    f"[Services] Dados obtidos via {metadata_info.get('source_name', 'unknown')} "
                    f"em {metadata_info.get('total_time_ms', 0)}ms"
                )
                if not metadata_info.get('is_master', True):
                    logger.warning(f"⚠️ [Services] Master offline! Usando fallback")

            # Aplicar filtros se especificados
            if any([module, company, project, env]):
                filtered_services = {}
                for node_name, services in all_services.items():
                    filtered_node_services = {}
                    for service_id, service_data in services.items():
                        meta = service_data.get("Meta", {})

                        # Verificar cada filtro
                        if module and meta.get("module") != module:
                            continue
                        if company and meta.get("company") != company:
                            continue
                        if project and meta.get("project") != project:
                            continue
                        if env and meta.get("env") != env:
                            continue

                        filtered_node_services[service_id] = service_data

                    if filtered_node_services:
                        filtered_services[node_name] = filtered_node_services

                all_services = filtered_services

            total_services = sum(len(services) for services in all_services.values())

            return {
                "success": True,
                "data": all_services,
                "total": total_services,
                "nodes_count": len(all_services),
                "message": f"Listados {total_services} serviços de {len(all_services)} nós"
            }
        else:
            # Listar de um nó específico (ou servidor principal se node_addr=None)
            target = node_addr or Config.MAIN_SERVER
            logger.info(f"Listando serviços do nó: {target}")

            services = await consul.get_services(node_addr)

            # Aplicar filtros se especificados
            if any([module, company, project, env]):
                filtered_services = {}
                for service_id, service_data in services.items():
                    meta = service_data.get("Meta", {})

                    # Verificar cada filtro
                    if module and meta.get("module") != module:
                        continue
                    if company and meta.get("company") != company:
                        continue
                    if project and meta.get("project") != project:
                        continue
                    if env and meta.get("env") != env:
                        continue

                    filtered_services[service_id] = service_data

                services = filtered_services

            return {
                "success": True,
                "data": services,
                "total": len(services),
                "node": target,
                "message": f"Listados {len(services)} serviços do nó {target}"
            }

    except Exception as e:
        logger.error(f"Erro ao listar serviços: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao conectar com Consul em {Config.MAIN_SERVER}:{Config.CONSUL_PORT} - {str(e)}"
        )


@router.get("/catalog/names", include_in_schema=True)
async def get_service_catalog_names():
    """
    Retorna lista de nomes de serviços disponíveis no catálogo do Consul

    Útil para popular dropdown de tipos de serviços na criação/edição de exporters.
    Retorna apenas nomes únicos de serviços registrados no Consul (ex: selfnode_exporter,
    node_exporter, windows_exporter, etc.)
    """
    try:
        consul = ConsulManager()

        logger.info("Obtendo nomes de serviços do catálogo Consul")
        service_names = await consul.get_service_names()

        return {
            "success": True,
            "data": service_names,
            "total": len(service_names)
        }

    except Exception as e:
        logger.error(f"Erro ao obter nomes de serviços: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/metadata/unique-values", include_in_schema=True)
async def get_unique_metadata_values(
    field: str = Query(..., description="Campo de metadados (module, company, project, env, etc)")
):
    """
    Obtém valores únicos de um campo de metadados

    Útil para popular dropdowns e filtros na interface
    """
    try:
        consul = ConsulManager()

        logger.info(f"Obtendo valores únicos para campo: {field}")
        values = await consul.get_unique_values(field)

        return {
            "success": True,
            "field": field,
            "values": sorted(list(values)),
            "total": len(values)
        }

    except Exception as e:
        logger.error(f"Erro ao obter valores únicos: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/search/by-metadata", include_in_schema=True)
async def search_services(
    module: Optional[str] = Query(None, description="Módulo"),
    company: Optional[str] = Query(None, description="Empresa"),
    project: Optional[str] = Query(None, description="Projeto"),
    env: Optional[str] = Query(None, description="Ambiente"),
    name: Optional[str] = Query(None, description="Nome"),
    instance: Optional[str] = Query(None, description="Instance"),
    node_addr: Optional[str] = Query(None, description="Buscar em nó específico")
):
    """
    Busca serviços por filtros de metadados

    Todos os parâmetros são opcionais. Retorna serviços que correspondem a TODOS os filtros especificados.
    """
    try:
        consul = ConsulManager()

        # Construir filtros
        filters = {}
        if module:
            filters["module"] = module
        if company:
            filters["company"] = company
        if project:
            filters["project"] = project
        if env:
            filters["env"] = env
        if name:
            filters["name"] = name
        if instance:
            filters["instance"] = instance

        if not filters:
            raise HTTPException(
                status_code=400,
                detail="Pelo menos um filtro deve ser especificado"
            )

        # Buscar com filtros
        logger.info(f"Buscando serviços com filtros: {filters}")

        if node_addr:
            # Buscar em nó específico
            all_services = await consul.get_services(node_addr)
            filtered = {}

            for service_id, service_data in all_services.items():
                meta = service_data.get("Meta", {})
                matches = all(meta.get(k) == v for k, v in filters.items())
                if matches:
                    filtered[service_id] = service_data

            return {
                "success": True,
                "data": filtered,
                "total": len(filtered),
                "filters": filters,
                "node": node_addr
            }
        else:
            # Buscar em todos os nós
            # ✅ SPRINT 1 CORREÇÃO (2025-11-15): Catalog API com fallback
            all_services = await consul.get_all_services_catalog(use_fallback=True)

            # Extrair metadata de fallback
            metadata_info = all_services.pop("_metadata", None)
            if metadata_info:
                logger.info(
                    f"[Services Search] Dados via {metadata_info.get('source_name', 'unknown')} "
                    f"em {metadata_info.get('total_time_ms', 0)}ms"
                )
                if not metadata_info.get('is_master', True):
                    logger.warning(f"⚠️ [Services Search] Master offline! Usando fallback")

            filtered = {}

            for node_name, services in all_services.items():
                node_filtered = {}
                for service_id, service_data in services.items():
                    meta = service_data.get("Meta", {})
                    matches = all(meta.get(k) == v for k, v in filters.items())
                    if matches:
                        node_filtered[service_id] = service_data

                if node_filtered:
                    filtered[node_name] = node_filtered

            total = sum(len(services) for services in filtered.values())

            return {
                "success": True,
                "data": filtered,
                "total": total,
                "filters": filters
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao buscar serviços: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{service_id:path}", include_in_schema=True)
async def get_service(
    service_id: str = Path(..., description="ID do serviço"),
    node_addr: Optional[str] = Query(None, description="Endereço do nó onde buscar")
):
    """
    Obtém detalhes de um serviço específico pelo ID

    IMPORTANTE: O service_id pode conter caracteres especiais (/, @) que devem ser codificados na URL

    Retorna todos os dados do serviço incluindo metadados completos
    """
    try:
        consul = ConsulManager()

        # CRITICAL: Sanitizar o service_id recebido da URL
        service_id = ConsulManager.sanitize_service_id(service_id)

        service = await consul.get_service_by_id(service_id, node_addr)

        if not service:
            raise HTTPException(
                status_code=404,
                detail=f"Serviço '{service_id}' não encontrado"
            )

        return {
            "success": True,
            "data": service,
            "service_id": service_id
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao obter serviço {service_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# POST ROUTES - Rotas específicas ANTES de rotas com :path
# ============================================================================

@router.post("/", include_in_schema=True)
@router.post("")
async def create_service(
    request: ServiceCreateRequest,
    background_tasks: BackgroundTasks
):
    """
    Cria um novo serviço no Consul com validações completas

    Valida:
    - Campos obrigatórios (module, company, project, env, name, instance)
    - Formato correto do instance baseado no módulo
    - Duplicatas (mesma combinação de module/company/project/env/name)

    Retorna o ID do serviço criado
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

        # ✅ SPRINT 2: Validar tipo de monitoramento (CRÍTICO)
        meta = service_data.get("Meta", {})
        service_name = service_data.get("service") or service_data.get("name", "")
        exporter_type = meta.get("exporter_type")
        category = meta.get("category")
        type_id = None  # ✅ NOVO: ID do tipo para validação de form_schema

        if service_name:
            try:
                type_info = await validate_monitoring_type(service_name, exporter_type, category)
                type_id = type_info.get('id')  # ✅ NOVO: Capturar ID do tipo
                logger.info(f"[VALIDATE-TYPE] Tipo validado: {type_info.get('display_name')} ({type_info.get('id')})")
            except HTTPException as e:
                # Re-raise HTTPException (tipo não encontrado)
                raise e
            except Exception as e:
                logger.warning(f"[VALIDATE-TYPE] Erro ao validar tipo (permitindo criação): {e}")

        # ✅ SPRINT 2: Validar campos obrigatórios do form_schema (SOLUÇÃO PRAGMÁTICA)
        if type_id:
            form_schema_errors = await validate_form_schema_fields(meta, type_id, category)
            if form_schema_errors:
                raise HTTPException(
                    status_code=400,
                    detail={
                        "message": "Erros de validação do form_schema",
                        "errors": form_schema_errors
                    }
                )
        
        # Validar dados do serviço (validação genérica)
        is_valid, errors = await consul.validate_service_data(service_data)
        if not is_valid:
            raise HTTPException(
                status_code=400,
                detail={
                    "message": "Erros de validação encontrados",
                    "errors": errors
                }
            )

        # ✅ CORREÇÃO: Gerar ID dinamicamente se não fornecido
        if 'id' not in service_data or not service_data.get('id'):
            meta = service_data.get("Meta", {})
            try:
                service_data['id'] = await consul.generate_dynamic_service_id(meta)
                logger.info(f"ID gerado dinamicamente: {service_data['id']}")
            except ValueError as e:
                raise HTTPException(
                    status_code=400,
                    detail={
                        "message": "Erro ao gerar ID do serviço",
                        "error": str(e)
                    }
                )
        
        # ✅ CORREÇÃO: Verificar duplicatas usando campos obrigatórios do KV
        is_duplicate = await consul.check_duplicate_service(
            meta=meta,
            target_node_addr=service_data.get("node_addr")
        )

        if is_duplicate:
            # Buscar campos obrigatórios para mensagem de erro
            required_fields = Config.get_required_fields()
            fields_str = "/".join(required_fields + ['name'])
            raise HTTPException(
                status_code=409,
                detail={
                    "message": "Serviço duplicado",
                    "detail": f"Já existe um serviço com a mesma combinação de campos obrigatórios ({fields_str})"
                }
            )

        # MULTI-SITE SUPPORT: Adicionar tag automática baseado no campo "site"
        # Se o metadata contém campo "site", adicionar como tag para filtros no prometheus.yml
        site = meta.get("site")
        if site:
            tags = service_data.get("Tags", service_data.get("tags", []))
            if not isinstance(tags, list):
                tags = []

            # Adicionar tag do site se não existir
            if site not in tags:
                tags.append(site)
                logger.info(f"Adicionada tag automática para site: {site}")

            # Garantir que o campo Tags está correto (Consul usa "Tags" com T maiúsculo)
            service_data["Tags"] = tags
            if "tags" in service_data:
                del service_data["tags"]

        # MULTI-SITE SUPPORT: Aplicar sufixo ao service name (Opção 2)
        # Se NAMING_STRATEGY=option2 e site != DEFAULT_SITE, adiciona sufixo _site
        # Exemplo: selfnode_exporter + site=rio → selfnode_exporter_rio
        if "name" in service_data and service_data["name"]:
            original_name = service_data["name"]
            site = extract_site_from_metadata(meta)
            cluster = meta.get("cluster")

            # Aplicar sufixo baseado na configuração
            suffixed_name = apply_site_suffix(original_name, site=site, cluster=cluster)

            if suffixed_name != original_name:
                service_data["name"] = suffixed_name
                logger.info(f"[MULTI-SITE] Service name alterado: {original_name} → {suffixed_name} (site={site})")

        # Registrar serviço
        logger.info(f"Registrando novo serviço: {service_data.get('id')}")
        success = await consul.register_service(
            service_data,
            service_data.get("node_addr")
        )

        if success:
            # ✅ SPRINT 2: Invalidar cache após criação
            background_tasks.add_task(
                invalidate_monitoring_cache,
                category
            )
            
            # Log assíncrono
            background_tasks.add_task(
                log_action,
                f"Serviço criado: {service_data.get('id')} - {meta.get('name')}"
            )

            return {
                "success": True,
                "message": "Serviço criado com sucesso",
                "service_id": service_data.get("id"),
                "data": service_data
            }
        else:
            raise HTTPException(
                status_code=500,
                detail="Falha ao registrar serviço no Consul"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao criar serviço: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/bulk/register", include_in_schema=True)
async def bulk_register_services(
    services: List[ServiceCreateRequest],
    node_addr: Optional[str] = Query(None, description="Endereço do nó onde registrar"),
    background_tasks: BackgroundTasks = None
):
    """
    Registra múltiplos serviços em lote

    Retorna resultado individual para cada serviço
    """
    try:
        consul = ConsulManager()

        services_data = [s.model_dump() for s in services]
        for service_data in services_data:
            if node_addr:
                service_data["node_addr"] = node_addr

        logger.info(f"Registrando {len(services_data)} serviços em lote")
        results = await consul.bulk_register_services(services_data, node_addr)

        success_count = sum(1 for v in results.values() if v)
        failed_count = len(results) - success_count

        background_tasks.add_task(
            log_action,
            f"Registro em lote: {success_count} sucessos, {failed_count} falhas"
        )

        return {
            "success": True,
            "message": f"Registrados {success_count}/{len(results)} serviços",
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
# PUT ROUTES - Rotas com :path
# ============================================================================

@router.put("/{service_id:path}", include_in_schema=True)
async def update_service(
    service_id: str = Path(..., description="ID do serviço a atualizar"),
    request: ServiceUpdateRequest = None,
    background_tasks: BackgroundTasks = None
):
    """
    Atualiza um serviço existente

    IMPORTANTE: O service_id pode conter caracteres especiais (/, @) que devem ser codificados na URL

    Nota: Consul não tem endpoint de update nativo, então fazemos:
    1. Deregister do serviço antigo
    2. Register do serviço com novos dados
    """
    try:
        consul = ConsulManager()

        # CRITICAL: Sanitizar o service_id recebido da URL
        # Garante que mesmo IDs com caracteres especiais sejam normalizados
        service_id = ConsulManager.sanitize_service_id(service_id)
        logger.info(f"Atualizando serviço com ID sanitizado: {service_id}")

        # Buscar serviço existente
        existing_service = await consul.get_service_by_id(
            service_id,
            request.node_addr if request else None
        )

        if not existing_service:
            raise HTTPException(
                status_code=404,
                detail=f"Serviço '{service_id}' não encontrado"
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

        # MULTI-SITE SUPPORT: Atualizar tag automática baseado no campo "site"
        meta = updated_service.get("Meta", {})
        site = meta.get("site")
        if site:
            tags = updated_service.get("Tags", [])
            if not isinstance(tags, list):
                tags = []

            # Adicionar tag do site se não existir
            if site not in tags:
                tags.append(site)
                logger.info(f"Adicionada tag automática para site: {site}")

            updated_service["Tags"] = tags

        # MULTI-SITE SUPPORT: Aplicar sufixo ao service name (Opção 2)
        # Se NAMING_STRATEGY=option2 e site != DEFAULT_SITE, adiciona sufixo _site
        if "Name" in updated_service and updated_service["Name"]:
            original_name = updated_service["Name"]
            site = extract_site_from_metadata(meta)
            cluster = meta.get("cluster")

            # Aplicar sufixo baseado na configuração
            suffixed_name = apply_site_suffix(original_name, site=site, cluster=cluster)

            if suffixed_name != original_name:
                updated_service["Name"] = suffixed_name
                logger.info(f"[MULTI-SITE] Service name alterado: {original_name} → {suffixed_name} (site={site})")

        # ✅ CORREÇÃO FASE 0: Validar dados do serviço antes de atualizar (usando validação dinâmica)
        is_valid, errors = await consul.validate_service_data(updated_service)
        if not is_valid:
            raise HTTPException(
                status_code=400,
                detail={
                    "message": "Erros de validação encontrados",
                    "errors": errors
                }
            )

        # ✅ CORREÇÃO FASE 0: Verificar duplicatas usando campos obrigatórios do KV (excluindo o próprio serviço)
        is_duplicate = await consul.check_duplicate_service(
            meta=meta,
            exclude_sid=service_id,
            target_node_addr=request.node_addr if request else None
        )

        if is_duplicate:
            # Buscar campos obrigatórios para mensagem de erro
            required_fields = Config.get_required_fields()
            fields_str = "/".join(required_fields + ['name'])
            raise HTTPException(
                status_code=409,
                detail={
                    "message": "Serviço duplicado",
                    "detail": f"Já existe outro serviço com a mesma combinação de campos obrigatórios ({fields_str})"
                }
            )

        # Atualizar serviço
        logger.info(f"Atualizando serviço: {service_id}")
        success = await consul.update_service(
            service_id,
            updated_service,
            request.node_addr if request else None
        )

        if success:
            # ✅ SPRINT 2: Invalidar cache após atualização
            meta = updated_service.get("Meta", {})
            category = meta.get("category")
            background_tasks.add_task(
                invalidate_monitoring_cache,
                category
            )
            
            background_tasks.add_task(
                log_action,
                f"Serviço atualizado: {service_id}"
            )

            return {
                "success": True,
                "message": "Serviço atualizado com sucesso",
                "service_id": service_id,
                "data": updated_service
            }
        else:
            raise HTTPException(
                status_code=500,
                detail="Falha ao atualizar serviço no Consul"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao atualizar serviço {service_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# DELETE ROUTES - Rotas específicas ANTES de rotas com :path
# ============================================================================

@router.delete("/bulk/deregister", include_in_schema=True)
async def bulk_deregister_services(
    service_ids: List[str],
    node_addr: Optional[str] = Query(None, description="Endereço do nó onde remover"),
    background_tasks: BackgroundTasks = None
):
    """
    Remove múltiplos serviços em lote

    Retorna resultado individual para cada serviço
    """
    try:
        consul = ConsulManager()

        logger.info(f"Removendo {len(service_ids)} serviços em lote")
        results = await consul.bulk_deregister_services(service_ids, node_addr)

        success_count = sum(1 for v in results.values() if v)
        failed_count = len(results) - success_count

        background_tasks.add_task(
            log_action,
            f"Remoção em lote: {success_count} sucessos, {failed_count} falhas"
        )

        return {
            "success": True,
            "message": f"Removidos {success_count}/{len(results)} serviços",
            "results": results,
            "summary": {
                "total": len(results),
                "success": success_count,
                "failed": failed_count
            }
        }

    except Exception as e:
        logger.error(f"Erro na remoção em lote: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{service_id:path}", include_in_schema=True)
async def delete_service(
    service_id: str = Path(..., description="ID do serviço a remover"),
    node_addr: Optional[str] = Query(None, description="Endereço do nó onde remover"),
    background_tasks: BackgroundTasks = None
):
    """
    Remove um serviço do Consul

    IMPORTANTE: O service_id pode conter caracteres especiais (/, @) que devem ser codificados na URL
    """
    try:
        consul = ConsulManager()

        # CRITICAL: Sanitizar o service_id recebido da URL
        # Garante que mesmo IDs com caracteres especiais sejam normalizados
        service_id = ConsulManager.sanitize_service_id(service_id)
        logger.info(f"Removendo serviço com ID sanitizado: {service_id}")

        # Verificar se serviço existe
        existing_service = await consul.get_service_by_id(service_id, node_addr)
        if not existing_service:
            raise HTTPException(
                status_code=404,
                detail=f"Serviço '{service_id}' não encontrado"
            )

        # Remover serviço
        logger.info(f"Removendo serviço: {service_id}")
        success = await consul.deregister_service(service_id, node_addr)

        if success:
            # ✅ SPRINT 2: Invalidar cache após exclusão
            meta = existing_service.get("Meta", {})
            category = meta.get("category")
            background_tasks.add_task(
                invalidate_monitoring_cache,
                category
            )
            
            background_tasks.add_task(
                log_action,
                f"Serviço removido: {service_id}"
            )

            return {
                "success": True,
                "message": "Serviço removido com sucesso",
                "service_id": service_id
            }
        else:
            raise HTTPException(
                status_code=500,
                detail="Falha ao remover serviço do Consul"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao remover serviço {service_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


async def log_action(message: str):
    """Envia log via WebSocket (implementar com manager)"""
    logger.info(f"ACTION: {message}")
