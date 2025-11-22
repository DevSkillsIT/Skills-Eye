"""
API endpoints para gerenciamento de nos

SPEC-PERF-001: Otimizacoes implementadas:
- Semaphore para limitar chamadas simultaneas a Catalog API
- Timeout configuravel via env (CONSUL_CATALOG_TIMEOUT)
- Retry com backoff para resiliencia
- Logging e metricas Prometheus para observabilidade
- Cache dedicado para sites_map com TTL de 5 minutos
"""
from fastapi import APIRouter, HTTPException
from typing import List, Dict, Optional
from core.consul_manager import ConsulManager
from core.config import Config
from core.cache_manager import get_cache  # SPRINT 2: LocalCache global
from core.metrics import (
    consul_node_enrich_failures,
    consul_node_enrich_duration,
    consul_sites_cache_status,
    consul_server_fallback
)
import asyncio
import time
import logging
import httpx

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Nodes"])

# SPRINT 2 (2025-11-15): Migracao para LocalCache global
# REMOVIDO: _nodes_cache, _nodes_cache_time (variaveis globais)
# NOVO: Usar LocalCache global para integracao com Cache Management
cache = get_cache(ttl_seconds=60)

# SPEC-PERF-001: Cache dedicado para sites_map com TTL de 5 minutos
# Sites raramente mudam, nao precisa buscar do KV a cada requisicao
sites_cache = get_cache(ttl_seconds=Config.SITES_CACHE_TTL)


async def get_consul_manager_with_fallback() -> tuple[ConsulManager, str]:
    """
    Retorna um ConsulManager conectado a um servidor disponível.

    Implementa fallback real entre múltiplos servidores Consul configurados.
    Tenta cada servidor da lista CONSUL_SERVERS em ordem, com timeout.
    Se todos falharem, tenta MAIN_SERVER como último recurso.

    Returns:
        tuple: (ConsulManager conectado, servidor usado)

    Raises:
        Exception: Se todos os servidores falharem
    """
    # Obter lista de servidores configurados
    consul_servers = Config.get_consul_servers()

    # Se não houver servidores configurados, usar MAIN_SERVER
    if not consul_servers:
        logger.debug("[Nodes] CONSUL_SERVERS não configurado, usando MAIN_SERVER")
        return ConsulManager(), Config.MAIN_SERVER

    # Tentar cada servidor da lista em ordem
    errors = []
    for server in consul_servers:
        try:
            # Parsear servidor (pode ter formato IP:PORTA ou apenas IP)
            if ":" in server:
                host, port_str = server.rsplit(":", 1)
                port = int(port_str)
            else:
                host = server
                port = Config.CONSUL_PORT

            logger.debug(f"[Nodes] Tentando servidor Consul: {host}:{port}")

            # Criar manager para este servidor
            consul = ConsulManager(host=host, port=port)

            # Testar conexão com timeout curto (health check)
            # Usa /agent/members que é rápido e sempre disponível
            await asyncio.wait_for(
                consul.get_members(),
                timeout=Config.CONSUL_CATALOG_TIMEOUT
            )

            # Sucesso! Registrar métrica e retornar
            consul_server_fallback.labels(server=server, status="success").inc()
            logger.info(f"[Nodes] Conectado ao servidor Consul: {server}")

            return consul, server

        except asyncio.TimeoutError:
            error_msg = f"Timeout ({Config.CONSUL_CATALOG_TIMEOUT}s) em {server}"
            errors.append(error_msg)
            consul_server_fallback.labels(server=server, status="timeout").inc()
            logger.warning(f"[Nodes] {error_msg}")
            continue

        except Exception as e:
            error_msg = f"Erro em {server}: {str(e)[:100]}"
            errors.append(error_msg)
            consul_server_fallback.labels(server=server, status="failure").inc()
            logger.warning(f"[Nodes] {error_msg}")
            continue

    # Todos os servidores configurados falharam - tentar MAIN_SERVER como último recurso
    try:
        logger.warning(
            f"[Nodes] Todos os {len(consul_servers)} servidores CONSUL_SERVERS falharam. "
            f"Tentando MAIN_SERVER ({Config.MAIN_SERVER}) como último recurso."
        )

        consul = ConsulManager()
        await asyncio.wait_for(
            consul.get_members(),
            timeout=Config.CONSUL_CATALOG_TIMEOUT
        )

        consul_server_fallback.labels(server=Config.MAIN_SERVER, status="success").inc()
        logger.info(f"[Nodes] Conectado ao MAIN_SERVER: {Config.MAIN_SERVER}")

        return consul, Config.MAIN_SERVER

    except Exception as e:
        error_msg = f"Erro em MAIN_SERVER ({Config.MAIN_SERVER}): {str(e)[:100]}"
        errors.append(error_msg)
        consul_server_fallback.labels(server=Config.MAIN_SERVER, status="failure").inc()
        logger.error(f"[Nodes] {error_msg}")

    # Todos falharam - lançar exceção
    raise Exception(
        f"[Nodes] Todos os servidores Consul falharam após {len(consul_servers) + 1} tentativas. "
        f"Erros: {'; '.join(errors)}"
    )

@router.get("/", include_in_schema=True)
@router.get("")
async def get_nodes():
    """Retorna todos os nos do cluster com cache de 60s

    SPEC-PERF-001: Otimizacoes implementadas:
    - Semaphore para limitar chamadas simultaneas (CONSUL_SEMAPHORE_LIMIT)
    - Timeout configuravel via env (CONSUL_CATALOG_TIMEOUT)
    - Retry com backoff para resiliencia
    - Logging e metricas Prometheus para observabilidade
    - Cache dedicado para sites_map com TTL de 5 minutos
    - services_status indica erro quando timeout ocorre
    """

    # SPRINT 2: Usar LocalCache global
    cache_key = "nodes:list:all"

    # Verificar cache
    cached = await cache.get(cache_key)
    if cached is not None:
        return cached

    try:
        # Usar fallback para múltiplos servidores Consul
        consul, active_server = await get_consul_manager_with_fallback()
        members = await consul.get_members()

        # INVALIDACAO AUTOMATICA: Verificar se membership mudou
        # Compara numero de members atual com valor salvo no cache
        # Se houver alteracao, invalida cache para forcar nova busca
        member_count_key = "nodes:member_count"
        cached_member_count = await cache.get(member_count_key)
        current_count = len(members)

        if cached_member_count is not None and cached_member_count != current_count:
            logger.info(
                f"[Nodes] Membership mudou: {cached_member_count} -> {current_count}. "
                f"Invalidando cache '{cache_key}' para garantir dados atualizados."
            )
            await cache.invalidate(cache_key)

        # Salvar contagem atual com TTL longo (3600s = 1 hora)
        # TTL longo porque so serve para detectar mudancas, nao precisa expirar rapido
        await cache.set(member_count_key, current_count, ttl=3600)

        # SPEC-PERF-001: Cache dedicado para sites_map com TTL de 5 minutos
        # Problema 6: Metadados de sites sem cache dedicado
        sites_cache_key = "sites:map:all"
        sites_map = await sites_cache.get(sites_cache_key)

        if sites_map is None:
            # Cache miss - buscar do KV
            consul_sites_cache_status.labels(status="miss").inc()

            from core.kv_manager import KVManager
            kv = KVManager()

            try:
                sites_data = await kv.get_json('skills/eye/metadata/sites')

                # Criar mapa IP -> site_name
                sites_map = {}
                if sites_data:
                    # Estrutura KV: data.data.sites (dois niveis de 'data')
                    inner_data = sites_data.get('data', {})
                    sites_list = inner_data.get('sites', []) if isinstance(inner_data, dict) else []

                    for site in sites_list:
                        if isinstance(site, dict):
                            ip = site.get('prometheus_instance') or site.get('prometheus_host')
                            name = site.get('name') or site.get('code', 'unknown')
                            if ip:
                                sites_map[ip] = name

                # Salvar no cache com TTL de 5 minutos
                await sites_cache.set(sites_cache_key, sites_map, ttl=Config.SITES_CACHE_TTL)
                logger.debug(f"[Nodes] Sites map cacheado: {len(sites_map)} sites")

            except Exception as e:
                # Problema 6: Manter ultimo valor valido para evitar regressoes
                logger.warning(f"[Nodes] Erro ao carregar sites do KV: {e}. Usando mapa vazio.")
                consul_sites_cache_status.labels(status="error").inc()
                sites_map = {}
        else:
            # Cache hit
            consul_sites_cache_status.labels(status="hit").inc()

        # SPEC-PERF-001: Semaphore para limitar chamadas simultaneas
        # Problema 3: Gargalo por tempestade de requisicoes a Catalog API
        semaphore = asyncio.Semaphore(Config.CONSUL_SEMAPHORE_LIMIT)

        async def get_service_count(member: dict) -> dict:
            """
            Conta servicos de um no especifico usando Catalog API

            SPEC-PERF-001: Otimizacoes implementadas:
            - Timeout configuravel via env (CONSUL_CATALOG_TIMEOUT)
            - Retry com backoff curto para resiliencia
            - Semaphore para limitar concorrencia
            - Logging e metricas para observabilidade
            - services_status para frontend sinalizar erro

            Args:
                member: Dicionario com dados do membro do cluster

            Returns:
                member enriquecido com services_count, site_name e services_status
            """
            # Inicializar valores padrao
            member["services_count"] = 0
            member["site_name"] = sites_map.get(member["addr"], "Nao mapeado")
            member["services_status"] = "ok"  # Problema 4: Status para frontend

            node_name = member.get("node", "unknown")
            start_time = time.time()

            # Problema 3: Usar semaphore para controlar concorrencia
            async with semaphore:
                # Problema 1: Retry com backoff curto
                max_retries = Config.CONSUL_MAX_RETRIES
                retry_delay = Config.CONSUL_RETRY_DELAY

                for attempt in range(max_retries + 1):
                    try:
                        # SPEC-PERF-001: Usar Catalog API centralizada (muito mais rapida)
                        # Problema 1: Timeout configuravel via env
                        node_data = await asyncio.wait_for(
                            consul.get_node_services(node_name),
                            timeout=Config.CONSUL_CATALOG_TIMEOUT
                        )

                        services = node_data.get("Services", {})
                        # Excluir servico "consul" da contagem
                        services_count = sum(1 for s in services.values() if s.get("Service") != "consul")
                        member["services_count"] = services_count

                        # Registrar duracao de sucesso
                        duration = time.time() - start_time
                        consul_node_enrich_duration.labels(
                            node_name=node_name,
                            status="success"
                        ).observe(duration)

                        return member

                    except asyncio.TimeoutError:
                        # Problema 4: Registrar warning com detalhes
                        if attempt < max_retries:
                            logger.warning(
                                f"[Nodes] Timeout ao enriquecer no '{node_name}' "
                                f"(IP: {member['addr']}) - tentativa {attempt + 1}/{max_retries + 1}. "
                                f"Timeout: {Config.CONSUL_CATALOG_TIMEOUT}s. Retentando..."
                            )
                            await asyncio.sleep(retry_delay * (attempt + 1))  # Backoff
                        else:
                            # Problema 4: Registrar metrica e log final
                            logger.warning(
                                f"[Nodes] Timeout ao enriquecer no '{node_name}' "
                                f"(IP: {member['addr']}) apos {max_retries + 1} tentativas. "
                                f"Timeout: {Config.CONSUL_CATALOG_TIMEOUT}s. Razao: Catalog API nao respondeu."
                            )
                            consul_node_enrich_failures.labels(
                                node_name=node_name,
                                error_type="timeout"
                            ).inc()
                            # Problema 4: Status para frontend sinalizar erro
                            member["services_status"] = "error"

                    except httpx.ConnectError as e:
                        # Problema 4: Registrar warning com detalhes
                        logger.warning(
                            f"[Nodes] Erro de conexao ao enriquecer no '{node_name}' "
                            f"(IP: {member['addr']}). Razao: {str(e)[:100]}"
                        )
                        consul_node_enrich_failures.labels(
                            node_name=node_name,
                            error_type="connection"
                        ).inc()
                        member["services_status"] = "error"
                        break

                    except httpx.HTTPStatusError as e:
                        # Problema 4: Registrar warning com detalhes
                        logger.warning(
                            f"[Nodes] Erro HTTP ao enriquecer no '{node_name}' "
                            f"(IP: {member['addr']}). Status: {e.response.status_code}. "
                            f"Razao: {str(e)[:100]}"
                        )
                        consul_node_enrich_failures.labels(
                            node_name=node_name,
                            error_type="http_error"
                        ).inc()
                        member["services_status"] = "error"
                        break

                    except Exception as e:
                        # Problema 4: Registrar warning com detalhes
                        logger.warning(
                            f"[Nodes] Erro desconhecido ao enriquecer no '{node_name}' "
                            f"(IP: {member['addr']}). Tipo: {type(e).__name__}. "
                            f"Razao: {str(e)[:100]}"
                        )
                        consul_node_enrich_failures.labels(
                            node_name=node_name,
                            error_type="unknown"
                        ).inc()
                        member["services_status"] = "error"
                        break

                # Registrar duracao de erro
                duration = time.time() - start_time
                consul_node_enrich_duration.labels(
                    node_name=node_name,
                    status="error"
                ).observe(duration)

            return member

        # Executar todas as requisicoes em paralelo (controladas por semaphore)
        enriched_members = await asyncio.gather(*[get_service_count(m) for m in members])

        result = {
            "success": True,
            "data": enriched_members,
            "total": len(enriched_members),
            "main_server": Config.MAIN_SERVER,
            "active_server": active_server  # Servidor Consul ativo usado (fallback)
        }

        # SPEC-PERF-001: Atualizar LocalCache global (TTL aumentado de 30s para 60s)
        # Nos raramente mudam em menos de 60s, reduz cache misses de 2/min para 1/min
        await cache.set(cache_key, result, ttl=60)

        return result
    except Exception as e:
        logger.error(f"[Nodes] Erro ao buscar nos: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{node_addr}/services")
async def get_node_services(node_addr: str):
    """Retorna serviços de um nó específico"""
    try:
        # Usar fallback para múltiplos servidores Consul
        consul, active_server = await get_consul_manager_with_fallback()
        services = await consul.get_services(node_addr)

        return {
            "success": True,
            "node": node_addr,
            "services": services,
            "total": len(services),
            "active_server": active_server
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{node_addr}/service-names")
async def get_node_service_names(node_addr: str):
    """Retorna apenas os nomes únicos de serviços REGISTRADOS em um nó específico

    Útil para popular dropdown de tipos de serviços baseado no nó selecionado.
    Retorna apenas nomes de serviços únicos (ex: selfnode_exporter, windows_exporter, node_exporter_rio, etc)

    IMPORTANTE: Conecta ao Consul e busca serviços do catálogo que estão registrados neste nó.
    node_addr pode ser IP (172.16.1.26) ou hostname (glpi-grafana-prometheus)
    """
    try:
        # Usar fallback para múltiplos servidores Consul
        consul, active_server = await get_consul_manager_with_fallback()

        # Primeiro, precisamos descobrir o node_name correspondente ao node_addr
        # Buscar todos os nós do catálogo
        all_nodes = await consul.get_nodes()

        # Encontrar o nó que corresponde ao node_addr
        target_node_name = None
        for node in all_nodes:
            # node tem: {"ID", "Node", "Address", "Datacenter", ...}
            if node.get("Address") == node_addr or node.get("Node") == node_addr:
                target_node_name = node.get("Node")
                break

        if not target_node_name:
            # Se não encontrou, assume que node_addr já é o nome
            target_node_name = node_addr

        # Buscar serviços deste nó específico usando /catalog/node/{node_name}
        node_data = await consul.get_node_services(target_node_name)

        # Extrair nomes únicos de serviços
        service_names_set = set()

        # node_data tem formato: {"Node": {...}, "Services": {...}}
        services_dict = node_data.get("Services", {})
        for service_id, service_info in services_dict.items():
            # service_info tem: {"ID", "Service", "Tags", "Address", "Port", ...}
            service_name = service_info.get("Service", "")
            if service_name and service_name != "consul":
                service_names_set.add(service_name)

        service_names = sorted(list(service_names_set))

        return {
            "success": True,
            "node": node_addr,
            "node_name": target_node_name,
            "data": service_names,
            "total": len(service_names),
            "active_server": active_server
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))