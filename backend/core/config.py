"""
Configuração central adaptada do consul-manager.py original
"""
import os
import asyncio
from typing import Dict, List, Set, Coroutine, Any
from dotenv import load_dotenv

load_dotenv()


def _run_async_safe(coro: Coroutine[Any, Any, Any]) -> Any:
    """
    Executa corrotina de forma segura, detectando se há event loop rodando.
    
    ✅ CORREÇÃO FASE 1.3 (2025-11-16):
    - Remove uso de asyncio.run() que pode causar RuntimeError em contextos async
    - Baseado em: https://docs.python.org/3/library/asyncio-task.html#asyncio.run
    
    Args:
        coro: Corrotina a ser executada
        
    Returns:
        Resultado da corrotina
    """
    try:
        # Tentar obter event loop existente
        loop = asyncio.get_running_loop()
        # Já existe event loop - usar ThreadPoolExecutor para executar em thread separada
        import concurrent.futures
        
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(asyncio.run, coro)
            return future.result()
    except RuntimeError:
        # Não há event loop - usar asyncio.run() normalmente
        return asyncio.run(coro)

class Config:
    """Configuração central do ambiente Skills IT

    NOTA: META_FIELDS e REQUIRED_FIELDS agora são carregados DINAMICAMENTE
    do metadata_fields.json via metadata_loader!
    """

    # Consul - Configurações básicas
    CONSUL_TOKEN = os.getenv("CONSUL_TOKEN", "8382a112-81e0-cd6d-2b92-8565925a0675")
    CONSUL_PORT = int(os.getenv("CONSUL_PORT", "8500"))

    # Lista de servidores Consul para fallback (separados por vírgula)
    # Formato: "172.16.1.26:8500,172.16.1.27:8500,172.16.1.28:8500"
    # Se vazio, usa apenas MAIN_SERVER derivado do KV metadata/sites
    @staticmethod
    def get_consul_servers() -> list:
        """
        Retorna lista de servidores Consul para fallback.

        FONTE: Variável de ambiente CONSUL_SERVERS
        Formato: "IP1:PORTA1,IP2:PORTA2,IP3:PORTA3"

        Se CONSUL_SERVERS estiver vazio, retorna lista vazia.
        O código que usa deve fazer fallback para MAIN_SERVER.
        """
        servers_env = os.getenv("CONSUL_SERVERS", "")
        if not servers_env.strip():
            return []

        # Parsear lista de servidores separados por vírgula
        servers = []
        for server in servers_env.split(","):
            server = server.strip()
            if server:
                servers.append(server)

        return servers

    # SPEC-PERF-001: Configurações de performance e resiliência
    # Timeout para chamadas à Catalog API (segundos)
    CONSUL_CATALOG_TIMEOUT = float(os.getenv("CONSUL_CATALOG_TIMEOUT", "2.0"))
    # Número máximo de chamadas simultâneas à Catalog API (evita tempestade de requisições)
    CONSUL_SEMAPHORE_LIMIT = int(os.getenv("CONSUL_SEMAPHORE_LIMIT", "5"))
    # TTL do cache de sites (segundos) - dados do KV mudam raramente
    SITES_CACHE_TTL = int(os.getenv("SITES_CACHE_TTL", "300"))
    # Número máximo de retries para chamadas ao Consul
    CONSUL_MAX_RETRIES = int(os.getenv("CONSUL_MAX_RETRIES", "1"))
    # Delay base para backoff exponencial (segundos)
    CONSUL_RETRY_DELAY = float(os.getenv("CONSUL_RETRY_DELAY", "0.5"))

    @staticmethod
    def get_main_server() -> str:
        """
        Retorna IP do servidor principal.

        FONTE: Primeiro nó do KV metadata/sites
        ZERO HARDCODE - Se KV vazio, usa variável de ambiente ou localhost
        """
        nodes = Config.get_known_nodes()
        if nodes:
            # Retornar primeiro IP do dicionário
            return list(nodes.values())[0]
        # Fallback: variável de ambiente ou localhost (ZERO IPs hardcoded)
        return os.getenv("CONSUL_HOST", "localhost")

    @staticmethod
    def get_main_server_name() -> str:
        """
        Retorna nome do servidor principal.

        FONTE: Primeiro hostname do KV metadata/sites
        ZERO HARDCODE - Se KV vazio, retorna "localhost"
        """
        nodes = Config.get_known_nodes()
        if nodes:
            # Retornar primeiro hostname do dicionário
            return list(nodes.keys())[0]
        return "localhost"

    @staticmethod
    def get_known_nodes() -> Dict[str, str]:
        """
        Retorna mapa de nós conhecidos (hostname → IP).

        FONTE: Consul KV (skills/eye/metadata/sites)
        ZERO HARDCODE - Se KV vazio/falhar, retorna dict vazio
        """
        try:
            from core.kv_manager import KVManager
            kv = KVManager()

            # ✅ CORREÇÃO FASE 1.3: Usar helper seguro ao invés de asyncio.run()
            sites_data = _run_async_safe(kv.get_json('skills/eye/metadata/sites'))

            if sites_data:
                # ESTRUTURA DO KV: {"data": {"sites": [...]}} (duplo wrap após auto_sync)
                # Extrair array de sites
                if isinstance(sites_data, dict) and 'data' in sites_data:
                    # Estrutura dupla: {"data": {"sites": [...]}}
                    sites_list = sites_data['data'].get('sites', [])
                elif isinstance(sites_data, dict) and 'sites' in sites_data:
                    # Estrutura simples: {"sites": [...]}
                    sites_list = sites_data.get('sites', [])
                elif isinstance(sites_data, list):
                    # Estrutura array direto: [...]
                    sites_list = sites_data
                else:
                    logger.warning(f"❌ KV sites estrutura desconhecida: {type(sites_data)}")
                    sites_list = []

                # Converter lista de sites para dict {hostname: prometheus_instance}
                nodes = {}
                for site in sites_list:
                    if not isinstance(site, dict):
                        continue
                    # Usar hostname se disponível, senão usar name
                    hostname = site.get('hostname') or site.get('name', 'unknown')
                    ip = site.get('prometheus_instance')
                    if ip:
                        nodes[hostname] = ip
                return nodes

            # KV vazio: retornar dict vazio (ZERO HARDCODE)
            return {}
        except Exception as e:
            # Falha ao acessar KV: retornar dict vazio (ZERO HARDCODE)
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"❌ Erro ao carregar sites do KV: {e}")
            return {}

    # Service Names
    SERVICE_NAMES = {
        "blackbox_exporter": "Blackbox local no nó selecionado",
        "blackbox_remote_dtc_skills": "Blackbox remoto DTC Skills",
        "blackbox_remote_rmd_ldc": "Blackbox remoto RMD LDC Rio",
        "selfnode_exporter": "Selfnode (requer agente no host remoto)",
        "selfnode_exporter_rio": "Selfnode RMD"
    }

    # Módulos Blackbox
    BLACKBOX_MODULES = [
        "icmp", "http_2xx", "http_4xx", "https",
        "http_post_2xx", "tcp_connect", "ssh_banner",
        "pop3s_banner", "irc_banner"
    ]

    # ========================================================================
    # CAMPOS METADATA - AGORA 100% DINÂMICOS DO PROMETHEUS
    # ========================================================================
    # Campos são extraídos do prometheus.yml via SSH e salvos no Consul KV
    # Não mais usa JSON hardcoded - tudo vem do Prometheus!
    # ========================================================================

    @staticmethod
    def get_meta_fields() -> List[str]:
        """
        Retorna todos os campos metadata extraídos do Prometheus.

        NOTA: Agora busca do Consul KV (skills/eye/metadata/fields)
        Os campos são extraídos dinamicamente do prometheus.yml via SSH
        """
        try:
            from core.kv_manager import KVManager
            kv = KVManager()

            # Buscar do KV (dados extraídos do Prometheus)
            # ✅ CORREÇÃO FASE 1.3: Usar helper seguro ao invés de asyncio.run()
            fields_data = _run_async_safe(kv.get_json('skills/eye/metadata/fields'))

            if fields_data and 'fields' in fields_data:
                return [field['name'] for field in fields_data['fields']]

            # Fallback: retornar lista vazia se KV não disponível
            return []
        except Exception:
            # Se falhar, retornar lista vazia (campos serão carregados sob demanda)
            return []

    @staticmethod
    def get_required_fields() -> List[str]:
        """
        Retorna campos obrigatórios extraídos do Prometheus.

        NOTA: Campos obrigatórios agora são definidos pelo flag 'required' no KV
        """
        try:
            from core.kv_manager import KVManager
            kv = KVManager()

            # ✅ CORREÇÃO FASE 1.3: Usar helper seguro ao invés de asyncio.run()
            fields_data = _run_async_safe(kv.get_json('skills/eye/metadata/fields'))

            if fields_data and 'fields' in fields_data:
                return [
                    field['name']
                    for field in fields_data['fields']
                    if field.get('required', False)
                ]

            return []
        except Exception:
            return []

    # Propriedades para compatibilidade com código legado
    # (deprecated - usar get_meta_fields() e get_required_fields())
    @property
    def META_FIELDS(self) -> List[str]:
        """DEPRECATED: Use Config.get_meta_fields() - Agora busca do Prometheus/KV"""
        return Config.get_meta_fields()

    @property
    def REQUIRED_FIELDS(self) -> List[str]:
        """DEPRECATED: Use Config.get_required_fields() - Agora busca do Prometheus/KV"""
        return Config.get_required_fields()


# Inicializar ao carregar módulo (compatibilidade legado)
Config.KNOWN_NODES = Config.get_known_nodes()
Config.MAIN_SERVER = Config.get_main_server()
Config.MAIN_SERVER_NAME = Config.get_main_server_name()