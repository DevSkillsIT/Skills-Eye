"""
API endpoints para gerenciamento de serviços
Conecta ao servidor Consul real e retorna dados de serviços com metadados completos
"""
from fastapi import APIRouter, HTTPException, Query, BackgroundTasks, Path
from typing import Dict, List, Optional
from core.consul_manager import ConsulManager
from core.config import Config
from .models import (
    ServiceCreateRequest,
    ServiceUpdateRequest,
    ServiceListResponse,
    ServiceResponse,
    ErrorResponse
)
import logging

router = APIRouter()
logger = logging.getLogger(__name__)


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
            logger.info("Listando serviços de todos os nós do cluster")
            all_services = await consul.get_all_services_from_all_nodes()

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


@router.get("/{service_id}", include_in_schema=True)
async def get_service(
    service_id: str = Path(..., description="ID do serviço"),
    node_addr: Optional[str] = Query(None, description="Endereço do nó onde buscar")
):
    """
    Obtém detalhes de um serviço específico pelo ID

    Retorna todos os dados do serviço incluindo metadados completos
    """
    try:
        consul = ConsulManager()
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

        # Validar dados do serviço
        is_valid, errors = await consul.validate_service_data(service_data)
        if not is_valid:
            raise HTTPException(
                status_code=400,
                detail={
                    "message": "Erros de validação encontrados",
                    "errors": errors
                }
            )

        # Verificar duplicatas
        meta = service_data.get("Meta", {})
        is_duplicate = await consul.check_duplicate_service(
            module=meta.get("module"),
            company=meta.get("company"),
            project=meta.get("project"),
            env=meta.get("env"),
            name=meta.get("name"),
            target_node_addr=service_data.get("node_addr")
        )

        if is_duplicate:
            raise HTTPException(
                status_code=409,
                detail={
                    "message": "Serviço duplicado",
                    "detail": "Já existe um serviço com essa combinação de module/company/project/env/name"
                }
            )

        # Registrar serviço
        logger.info(f"Registrando novo serviço: {service_data.get('id')}")
        success = await consul.register_service(
            service_data,
            service_data.get("node_addr")
        )

        if success:
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


@router.put("/{service_id}", include_in_schema=True)
async def update_service(
    service_id: str = Path(..., description="ID do serviço a atualizar"),
    request: ServiceUpdateRequest = None,
    background_tasks: BackgroundTasks = None
):
    """
    Atualiza um serviço existente

    Nota: Consul não tem endpoint de update nativo, então fazemos:
    1. Deregister do serviço antigo
    2. Register do serviço com novos dados
    """
    try:
        consul = ConsulManager()

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
        updated_service = existing_service.copy()
        if request:
            update_data = request.model_dump(exclude_unset=True)
            for key, value in update_data.items():
                if value is not None and key != "node_addr":
                    updated_service[key] = value

        # Atualizar serviço
        logger.info(f"Atualizando serviço: {service_id}")
        success = await consul.update_service(
            service_id,
            updated_service,
            request.node_addr if request else None
        )

        if success:
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


@router.delete("/{service_id}", include_in_schema=True)
async def delete_service(
    service_id: str = Path(..., description="ID do serviço a remover"),
    node_addr: Optional[str] = Query(None, description="Endereço do nó onde remover"),
    background_tasks: BackgroundTasks = None
):
    """
    Remove um serviço do Consul
    """
    try:
        consul = ConsulManager()

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
            all_services = await consul.get_all_services_from_all_nodes()
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


async def log_action(message: str):
    """Envia log via WebSocket (implementar com manager)"""
    logger.info(f"ACTION: {message}")
