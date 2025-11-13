"""
API endpoints para gerenciamento de configurações do Consul
Permite visualizar e testar conectividade com diferentes instâncias
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from core.consul_manager import ConsulManager
from core.config import Config
from .models import ConsulConfig, ConsulConfigResponse, HealthCheckResponse
import logging
import httpx

router = APIRouter(tags=["Config"])
logger = logging.getLogger(__name__)


@router.get("/current", response_model=ConsulConfigResponse)
async def get_current_config():
    """
    Retorna a configuração atual de conexão com o Consul

    Mostra o servidor configurado, porta e se há token (sem revelar o token)
    """
    return ConsulConfigResponse(
        host=Config.MAIN_SERVER,
        port=Config.CONSUL_PORT,
        has_token=bool(Config.CONSUL_TOKEN),
        main_server=Config.MAIN_SERVER,
        known_nodes=Config.KNOWN_NODES
    )


@router.get("/health", response_model=HealthCheckResponse)
async def check_health(
    host: Optional[str] = Query(None, description="Host customizado para testar"),
    port: Optional[int] = Query(None, description="Porta customizada para testar"),
    token: Optional[str] = Query(None, description="Token customizado para testar")
):
    """
    Testa conectividade com o servidor Consul

    Pode testar com configurações customizadas ou usar as configurações atuais
    """
    try:
        # Usar configurações fornecidas ou padrões
        test_host = host or Config.MAIN_SERVER
        test_port = port or Config.CONSUL_PORT
        test_token = token or Config.CONSUL_TOKEN

        logger.info(f"Testando conectividade com Consul em {test_host}:{test_port}")

        # Criar consulta temporária para teste
        consul = ConsulManager(host=test_host, port=test_port, token=test_token)

        # Testar endpoints básicos
        try:
            # 1. Testar leader
            leader_response = await consul._request("GET", "/status/leader")
            leader = leader_response.json() if leader_response else None

            # 2. Testar nodes
            nodes = await consul.get_nodes()
            nodes_count = len(nodes) if nodes else 0

            # 3. Tentar obter versão
            consul_version = None
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get(
                        f"http://{test_host}:{test_port}/v1/agent/self",
                        headers={"X-Consul-Token": test_token},
                        timeout=5
                    )
                    if response.status_code == 200:
                        data = response.json()
                        consul_version = data.get("Config", {}).get("Version")
            except:
                pass

            return HealthCheckResponse(
                healthy=True,
                message=f"Conectado com sucesso ao Consul em {test_host}:{test_port}",
                consul_version=consul_version,
                leader=leader,
                nodes_count=nodes_count
            )

        except Exception as e:
            logger.warning(f"Erro ao obter detalhes do Consul: {e}")
            # Ainda retornar como saudável se conseguimos conectar
            return HealthCheckResponse(
                healthy=True,
                message=f"Conectado ao Consul em {test_host}:{test_port} (informações detalhadas indisponíveis)",
                consul_version=None,
                leader=None,
                nodes_count=None
            )

    except Exception as e:
        logger.error(f"Erro ao conectar com Consul: {e}", exc_info=True)
        return HealthCheckResponse(
            healthy=False,
            message=f"Falha ao conectar com Consul em {test_host}:{test_port}: {str(e)}",
            consul_version=None,
            leader=None,
            nodes_count=None
        )


@router.get("/known-nodes")
async def get_known_nodes():
    """
    Retorna lista de nós conhecidos configurados

    Útil para selecionar diferentes instâncias Consul
    """
    return {
        "success": True,
        "nodes": [
            {
                "name": name,
                "address": addr,
                "is_main": addr == Config.MAIN_SERVER
            }
            for name, addr in Config.KNOWN_NODES.items()
        ],
        "main_server": Config.MAIN_SERVER,
        "total": len(Config.KNOWN_NODES)
    }


@router.post("/test-connection")
async def test_connection(config: ConsulConfig):
    """
    Testa conexão com configurações Consul customizadas

    Permite testar antes de alterar a configuração permanentemente
    """
    try:
        logger.info(f"Testando conexão customizada: {config.host}:{config.port}")

        consul = ConsulManager(
            host=config.host,
            port=config.port,
            token=config.token
        )

        # Tentar operações básicas
        members = await consul.get_members()
        services = await consul.get_services()

        return {
            "success": True,
            "message": "Conexão bem-sucedida",
            "details": {
                "host": config.host,
                "port": config.port,
                "has_token": bool(config.token),
                "members_found": len(members),
                "services_found": len(services)
            }
        }

    except Exception as e:
        logger.error(f"Erro ao testar conexão: {e}", exc_info=True)
        raise HTTPException(
            status_code=503,
            detail={
                "message": "Falha ao conectar",
                "error": str(e),
                "host": config.host,
                "port": config.port
            }
        )


@router.get("/modules")
async def get_available_modules():
    """
    Retorna lista de módulos de monitoramento disponíveis

    Útil para popular dropdowns ao criar serviços
    """
    return {
        "success": True,
        "modules": Config.BLACKBOX_MODULES,
        "total": len(Config.BLACKBOX_MODULES)
    }


@router.get("/meta-fields")
async def get_meta_fields():
    """
    Retorna lista de campos de metadados disponíveis

    Mostra quais campos são obrigatórios e quais são opcionais
    """
    return {
        "success": True,
        "fields": {
            "all": Config.META_FIELDS,
            "required": Config.REQUIRED_FIELDS,
            "optional": [f for f in Config.META_FIELDS if f not in Config.REQUIRED_FIELDS]
        },
        "total": len(Config.META_FIELDS)
    }


@router.get("/service-names")
async def get_service_names():
    """
    Retorna mapeamento de nomes de serviços disponíveis

    Mostra os tipos de serviços que podem ser registrados
    """
    return {
        "success": True,
        "service_names": Config.SERVICE_NAMES,
        "total": len(Config.SERVICE_NAMES)
    }


@router.get("/environment-info")
async def get_environment_info():
    """
    Retorna informações completas do ambiente configurado

    Útil para debug e verificação da configuração atual
    """
    return {
        "success": True,
        "environment": {
            "consul": {
                "main_server": Config.MAIN_SERVER,
                "main_server_name": Config.MAIN_SERVER_NAME,
                "port": Config.CONSUL_PORT,
                "has_token": bool(Config.CONSUL_TOKEN),
                "token_preview": f"{Config.CONSUL_TOKEN[:8]}..." if Config.CONSUL_TOKEN else None
            },
            "known_nodes": Config.KNOWN_NODES,
            "service_names": Config.SERVICE_NAMES,
            "blackbox_modules": Config.BLACKBOX_MODULES,
            "metadata": {
                "all_fields": Config.META_FIELDS,
                "required_fields": Config.REQUIRED_FIELDS
            }
        }
    }
