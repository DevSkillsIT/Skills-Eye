"""
Classe ConsulManager adaptada do script original
Mantém todas as funcionalidades mas estruturada para API
Versão async para FastAPI

SPRINT 1 (2025-11-14): Otimização crítica get_all_services_from_all_nodes()
- Usa /agent/services (local, 5ms) ao invés de iterar nodes
- Fallback inteligente: master → clients (timeout 2s cada)
- Métricas Prometheus para observabilidade
"""
import asyncio
import base64
import json
import logging
import os
import re
import time
import warnings
import httpx
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple
from urllib.parse import quote
from functools import wraps
from .config import Config
from .metrics import (
    consul_request_duration,
    consul_requests_total,
    consul_nodes_available,
    consul_fallback_total,
    consul_cache_hits,
    consul_stale_responses,
    consul_api_type
)

logger = logging.getLogger(__name__)

# ============================================================================
# UTILITÁRIOS E HELPERS
# ============================================================================

def retry_with_backoff(max_retries=3, base_delay=1, max_delay=10):
    """Decorator para retry com backoff exponencial (async)"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            retries = 0
            delay = base_delay

            while retries < max_retries:
                try:
                    return await func(*args, **kwargs)
                except httpx.HTTPStatusError as e:
                    # NÃO fazer retry em erros 4xx (Bad Request, Not Found, etc)
                    # Esses são erros permanentes do cliente, não vão resolver com retry
                    if 400 <= e.response.status_code < 500:
                        raise  # Re-lança imediatamente sem retry
                    # Erros 5xx (servidor) podem ser temporários - faz retry
                    retries += 1
                    if retries >= max_retries:
                        raise
                    print(f"Tentativa {retries} falhou: {e}")
                    await asyncio.sleep(delay)
                    delay = min(delay * 2, max_delay)
                except (httpx.RequestError, ConnectionError) as e:
                    # Erros de rede/conexão - faz retry
                    retries += 1
                    if retries >= max_retries:
                        raise
                    print(f"Tentativa {retries} falhou: {e}")
                    await asyncio.sleep(delay)
                    delay = min(delay * 2, max_delay)
            return None
        return wrapper
    return decorator


# ============================================================================
# CLASSE PRINCIPAL CONSUL
# ============================================================================

class ConsulManager:
    """Gerenciador principal do Consul - Versão Async para FastAPI"""

    def __init__(self, host: str = None, port: int = None, token: str = None):
        # Lazy evaluation: só acessa Config.MAIN_SERVER se necessário (evita loop circular)
        self.host = host or getattr(Config, 'MAIN_SERVER', os.getenv('CONSUL_HOST', 'localhost'))
        self.port = port or Config.CONSUL_PORT
        self.token = token or Config.CONSUL_TOKEN
        self.base_url = f"http://{self.host}:{self.port}/v1"
        self.headers = {"X-Consul-Token": self.token}

    @retry_with_backoff()
    async def _request(self, method: str, path: str, use_cache: bool = False, **kwargs):
        """
        Requisição HTTP assíncrona para API do Consul

        SPRINT 1 CORREÇÕES (2025-11-15):
        ✅ Agent Caching: use_cache=True adiciona ?cached parameter
           - Background refresh automático (TTL 3 dias)
           - Cache local instantâneo após 1ª request
           - Fonte: https://developer.hashicorp.com/consul/api-docs/features/caching

        Args:
            method: HTTP method (GET, PUT, POST, DELETE)
            path: API path (ex: /catalog/services)
            use_cache: Se True, habilita Agent Caching com ?cached parameter
            **kwargs: Parâmetros adicionais (params, json, timeout, etc)

        Returns:
            httpx.Response object
        """
        kwargs.setdefault("headers", self.headers)
        kwargs.setdefault("timeout", 5)  # Timeout padrão 5s

        # ✅ OFICIAL HASHICORP: Agent Caching (background refresh)
        if use_cache and method == "GET":
            if "params" not in kwargs:
                kwargs["params"] = {}
            kwargs["params"]["cached"] = ""  # ← Habilita background refresh automático

        url = f"{self.base_url}{path}"

        async with httpx.AsyncClient() as client:
            start_time = time.time()
            response = await client.request(method, url, **kwargs)
            duration_ms = (time.time() - start_time) * 1000

            # ✅ MÉTRICAS: Cache hits com categorização de freshness
            if use_cache:
                age = int(response.headers.get("Age", "0"))
                cache_status = response.headers.get("X-Cache", "MISS")

                if cache_status == "HIT":
                    # Categorizar freshness do cache
                    if age < 10:
                        age_bucket = "fresh"
                    elif age < 60:
                        age_bucket = "stale"
                    else:
                        age_bucket = "very_stale"

                    consul_cache_hits.labels(
                        endpoint=path.split('?')[0],
                        age_bucket=age_bucket
                    ).inc()

                    if age > 60:
                        logger.warning(
                            f"[Consul] 📦 Cache stale: {path} age={age}s "
                            f"(background refresh may be delayed)"
                        )

            # ✅ MÉTRICAS: Stale responses com categorização de lag
            last_contact_ms = int(response.headers.get("X-Consul-LastContact", "0"))
            if last_contact_ms > 1000:  # > 1 segundo
                if last_contact_ms < 5000:
                    lag_bucket = "1s-5s"
                elif last_contact_ms < 10000:
                    lag_bucket = "5s-10s"
                else:
                    lag_bucket = ">10s"

                consul_stale_responses.labels(
                    endpoint=path.split('?')[0],
                    lag_bucket=lag_bucket
                ).inc()

                logger.warning(
                    f"[Consul] ⏱️ Stale response: {path} lag={last_contact_ms}ms"
                )

            # ✅ MÉTRICAS: Rastrear tipo de API chamada (agent|catalog|kv|health)
            if path.startswith("/agent/"):
                api_type = "agent"
            elif path.startswith("/catalog/"):
                api_type = "catalog"
            elif path.startswith("/kv/"):
                api_type = "kv"
            elif path.startswith("/health/"):
                api_type = "health"
            else:
                api_type = "other"

            consul_api_type.labels(api_type=api_type).inc()

            response.raise_for_status()
            return response

    @staticmethod
    def sanitize_service_id(raw_id: str) -> str:
        """
        Normaliza o ID de serviço para o formato aceito pelo Consul.

        Substitui caracteres inválidos por sublinhado e valida barras.
        """
        if raw_id is None:
            raise ValueError("Service id can not be null")

        candidate = re.sub(r'[\[\] `~!\\#$^&*=|"{}\':;?\t\n]', '_', raw_id.strip())

        if '//' in candidate or candidate.startswith('/') or candidate.endswith('/'):
            raise ValueError("Service id can not start/end with '/' or contain '//'")

        return candidate

    async def query_agent_services(self, filter_expr: Optional[str] = None) -> Dict[str, Dict]:
        """
        Consulta /agent/services com filtro opcional
        
        ✅ CORREÇÃO FASE 1.2 (2025-11-16):
        - Adicionado use_cache=True para Agent Caching (background refresh)
        - Baseado em: https://developer.hashicorp.com/consul/api-docs/agent/service#agent-caching
        """
        params = {"filter": filter_expr} if filter_expr else {}
        try:
            response = await self._request("GET", "/agent/services", use_cache=True, params=params)
            return response.json()
        except Exception as exc:
            logger.error("Failed to query agent services: %s", exc)
            return {}

    async def get_services_overview(self) -> List[Dict]:
        """Retorna visão geral dos serviços (similar ao TenSunS)"""
        try:
            response = await self._request("GET", "/internal/ui/services")
            info = response.json()
            services_list: List[Dict] = []

            for item in info:
                if item.get("Name") == "consul":
                    continue
                services_list.append({
                    "name": item.get("Name"),
                    "datacenter": item.get("Datacenter", "unknown"),
                    "instance_count": item.get("InstanceCount"),
                    "checks_critical": item.get("ChecksCritical"),
                    "checks_passing": item.get("ChecksPassing"),
                    "tags": item.get("Tags", []),
                    "nodes": list(set(item.get("Nodes", [])))
                })

            return services_list
        except httpx.HTTPStatusError as exc:
            logger.error("Consul returned %s when fetching services overview", exc.response.status_code)
            return []
        except Exception as exc:
            logger.error("Failed to fetch services overview: %s", exc)
            return []

    async def get_service_names(self) -> List[str]:
        """
        Retorna apenas os nomes dos serviços cadastrados
        
        ✅ CORREÇÃO FASE 1.1 REVISADA (2025-11-16):
        - Usa ?stale para escalabilidade (permite qualquer server responder)
        - Timeout curto (2s) para evitar espera em nodes offline
        - Fallback: se falhar, tenta sem ?stale (pode ser node único)
        - Baseado em: https://developer.hashicorp.com/consul/api-docs/catalog#read-scaling
        
        NOTA: ?stale NÃO ajuda quando node está offline - ambos falham igual.
        Testes reais mostram +20.95% melhoria (não +300% teórico).
        """
        try:
            # Tentar com ?stale primeiro (timeout curto)
            try:
                response = await asyncio.wait_for(
                    self._request("GET", "/catalog/services", params={"stale": ""}),
                    timeout=2.0
                )
                services = response.json()
                services.pop("consul", None)
                return sorted(list(services.keys()))
            except (asyncio.TimeoutError, httpx.RequestError):
                # Se falhar com ?stale (node offline?), tentar sem ?stale
                logger.debug("get_service_names: ?stale falhou, tentando sem ?stale")
                response = await self._request("GET", "/catalog/services")
                services = response.json()
                services.pop("consul", None)
                return sorted(list(services.keys()))
        except Exception as exc:
            logger.error("Failed to list service names: %s", exc)
            return []

    async def get_service_instances(self, service_name: str) -> List[Dict]:
        """Retorna instâncias e health-checks de um serviço específico"""
        try:
            response = await self._request("GET", f"/health/service/{quote(service_name, safe='')}")
            data = response.json()
            instances: List[Dict] = []

            for entry in data:
                node = entry.get("Node", {})
                service = entry.get("Service", {})
                checks = entry.get("Checks", [])

                instance_meta = {
                    # Campos UpperCase para compatibilidade com convert_to_table_items
                    "ID": service.get("ID"),
                    "Service": service.get("Service"),
                    "Node": node.get("Node"),
                    "Address": node.get("Address"),  # Node address
                    "ServiceAddress": service.get("Address"),  # Service address
                    "Port": service.get("Port"),
                    "Tags": service.get("Tags") or [],
                    "Meta": service.get("Meta") or {},
                    # Campos adicionais (lowercase mantidos para compatibilidade)
                    "id": service.get("ID"),
                    "name": service.get("Service"),
                    "tags": service.get("Tags") or [],
                    "address": service.get("Address"),
                    "port": service.get("Port"),
                    "meta": service.get("Meta") or {},
                    "status": "unknown",
                    "output": ""
                }

                if len(checks) >= 2:
                    instance_meta["status"] = checks[1].get("Status", "unknown")
                    instance_meta["output"] = checks[1].get("Output", "")
                elif checks:
                    instance_meta["status"] = checks[0].get("Status", "unknown")
                    instance_meta["output"] = checks[0].get("Output", "")

                if instance_meta["meta"]:
                    instance_meta["meta_label"] = [
                        {"prop": key, "label": key} for key in instance_meta["meta"].keys()
                    ]

                instances.append(instance_meta)

            return instances
        except httpx.HTTPStatusError as exc:
            logger.error("Consul returned %s when fetching instances for %s", exc.response.status_code, service_name)
            return []
        except Exception as exc:
            logger.error("Failed to fetch instances for %s: %s", service_name, exc)
            return []

    async def get_agent_host_info(self) -> Optional[Dict]:
        """Obtém dados do host em que o agente Consul está rodando"""
        try:
            response = await self._request("GET", "/agent/host")
            info = response.json()

            pmem = round(info["Memory"]["usedPercent"])
            pdisk = round(info["Disk"]["usedPercent"])

            return {
                "host": {
                    "hostname": info["Host"]["hostname"],
                    "uptime": round(info["Host"]["uptime"] / 3600 / 24),
                    "os": f'{info["Host"]["platform"]} {info["Host"]["platformVersion"]}',
                    "kernel": info["Host"]["kernelVersion"]
                },
                "cpu": {
                    "cores": len(info["CPU"]),
                    "vendorId": info["CPU"][0]["vendorId"] if info["CPU"] else None,
                    "modelName": info["CPU"][0]["modelName"] if info["CPU"] else None
                },
                "memory": {
                    "total": round(info["Memory"]["total"] / 1024 ** 3),
                    "available": round(info["Memory"]["available"] / 1024 ** 3),
                    "used": round(info["Memory"]["used"] / 1024 ** 3),
                    "usedPercent": pmem
                },
                "disk": {
                    "path": info["Disk"]["path"],
                    "fstype": info["Disk"]["fstype"],
                    "total": round(info["Disk"]["total"] / 1024 ** 3),
                    "free": round(info["Disk"]["free"] / 1024 ** 3),
                    "used": round(info["Disk"]["used"] / 1024 ** 3),
                    "usedPercent": pdisk
                },
                "pmem": pmem,
                "pdisk": pdisk
            }
        except httpx.HTTPStatusError as exc:
            logger.error("Consul returned %s when fetching agent host info", exc.response.status_code)
            return None
        except Exception as exc:
            logger.error("Failed to fetch agent host info: %s", exc)
            return None

    async def get_members(self) -> List[Dict]:
        """Obtém membros do cluster via API"""
        try:
            response = await self._request("GET", "/agent/members")
            members = response.json()

            # Processar e enriquecer com nós conhecidos
            known_nodes_dict = {}
            for name, ip in Config.KNOWN_NODES.items():
                known_nodes_dict[ip] = {
                    "node": name,
                    "addr": ip,
                    "status": "unknown",
                    "type": "unknown"
                }

            for m in members:
                addr = m["Addr"].split(":")[0]
                known_nodes_dict[addr] = {
                    "node": m["Name"],
                    "addr": addr,
                    "status": "alive" if m["Status"] == 1 else "dead",
                    "type": "server" if m.get("Tags", {}).get("role") == "consul" else "client"
                }

            return list(known_nodes_dict.values())
        except Exception as e:
            print(f"Erro ao obter membros: {e}")
            # Retornar nós conhecidos como fallback
            return [
                {"node": name, "addr": ip, "status": "unknown", "type": "unknown"}
                for name, ip in Config.KNOWN_NODES.items()
            ]

    async def get_services(self, node_addr: str = None) -> Dict:
        """
        Obtém serviços de um nó específico ou local
        
        ✅ CORREÇÃO FASE 1.2 (2025-11-16):
        - Adicionado use_cache=True para Agent Caching (alta frequência de chamadas)
        """
        if node_addr and node_addr != self.host:
            # Conectar ao nó específico
            temp_manager = ConsulManager(host=node_addr, token=self.token)
            return await temp_manager.get_services()

        try:
            response = await self._request("GET", "/agent/services", use_cache=True)
            return response.json()
        except:
            return {}

    async def register_service(self, service_data: Dict, node_addr: str = None) -> bool:
        """Registra um serviço"""
        if node_addr and node_addr != self.host:
            temp_manager = ConsulManager(host=node_addr, token=self.token)
            return await temp_manager.register_service(service_data)

        try:
            await self._request("PUT", "/agent/service/register", json=service_data)
            return True
        except Exception as e:
            print(f"Erro ao registrar: {e}")
            return False

    async def deregister_service(self, service_id: str, node_addr: str = None) -> bool:
        """Remove um serviço"""
        if node_addr and node_addr != self.host:
            temp_manager = ConsulManager(host=node_addr, token=self.token)
            return await temp_manager.deregister_service(service_id)

        try:
            await self._request("PUT", f"/agent/service/deregister/{quote(service_id, safe='')}")
            return True
        except httpx.ReadTimeout:
            print("Timeout ao remover (provável sucesso)")
            return True
        except Exception as e:
            if "Unknown service ID" in str(e):
                print("Serviço já não existe")
                return True
            print(f"Erro: {e}")
            return False

    async def get_health_status(self, service_name: str = None) -> List:
        """Obtém status de saúde dos serviços"""
        try:
            if service_name:
                response = await self._request("GET", f"/health/service/{service_name}")
            else:
                response = await self._request("GET", "/health/state/any")
            return response.json()
        except:
            return []

    async def get_catalog_services(self) -> Dict:
        """
        Lista todos os serviços do catálogo
        
        ✅ CORREÇÃO FASE 1.1 REVISADA (2025-11-16):
        - Usa ?stale com timeout curto e fallback
        - Testes reais: +20.95% melhoria (não +300% teórico)
        """
        try:
            try:
                response = await asyncio.wait_for(
                    self._request("GET", "/catalog/services", params={"stale": ""}),
                    timeout=2.0
                )
                return response.json()
            except (asyncio.TimeoutError, httpx.RequestError):
                # Fallback se ?stale falhar
                response = await self._request("GET", "/catalog/services")
                return response.json()
        except:
            return {}

    async def get_unique_values(self, field: str) -> Set[str]:
        """Obtém valores únicos de um campo específico dos metadados"""
        values = set()
        try:
            services = await self.get_services()
            for sid, svc in services.items():
                meta = svc.get("Meta", {})
                if field in meta and meta[field]:
                    values.add(meta[field])
        except:
            pass
        return values

    async def update_service(self, service_id: str, service_data: Dict, node_addr: str = None) -> bool:
        """
        Atualiza um serviço existente

        IMPORTANTE: Segundo documentação oficial do Consul, para atualizar um serviço
        basta RE-REGISTRAR com o mesmo ID. NÃO é necessário fazer deregister antes.
        Fonte: https://developer.hashicorp.com/consul/api-docs/agent/service

        O Consul automaticamente substitui o serviço quando você registra com mesmo ID.
        """
        if node_addr and node_addr != self.host:
            temp_manager = ConsulManager(host=node_addr, token=self.token)
            return await temp_manager.update_service(service_id, service_data)

        try:
            # Preparar payload normalizado para o endpoint de registro
            normalized_data = service_data.copy()

            # 1. Converter campo "Service" → "Name" (obrigatório para register)
            #    GET /agent/services retorna "Service"
            #    PUT /agent/service/register espera "Name"
            if "Service" in normalized_data and "Name" not in normalized_data:
                normalized_data["Name"] = normalized_data.pop("Service")

            # 2. Garantir que o ID está presente (obrigatório para update)
            if "ID" not in normalized_data:
                normalized_data["ID"] = service_id

            # 3. Remover campos read-only que não podem ser enviados no register
            #    Estes campos são retornados pelo GET mas não aceitos pelo PUT
            readonly_fields = ["CreateIndex", "ModifyIndex", "ContentHash", "Datacenter", "PeerName"]
            for field in readonly_fields:
                normalized_data.pop(field, None)

            # 4. Ajustar campo Weights se estiver vazio (converter {} para None)
            if "Weights" in normalized_data and normalized_data["Weights"] == {}:
                normalized_data["Weights"] = None

            # 5. RE-REGISTRAR o serviço (Consul atualiza automaticamente se ID já existe)
            #    NÃO fazer deregister antes - isso deletaria o serviço!
            return await self.register_service(normalized_data)

        except Exception as e:
            print(f"Erro ao atualizar serviço: {e}")
            import traceback
            traceback.print_exc()
            return False

    async def get_service_by_id(self, service_id: str, node_addr: str = None) -> Optional[Dict]:
        """Obtém detalhes de um serviço específico pelo ID"""
        services = await self.get_services(node_addr)
        return services.get(service_id)

    async def get_services_by_name(self, service_name: str) -> List[Dict]:
        """
        Obtém todos os serviços com um nome específico do catálogo
        
        ✅ CORREÇÃO FASE 1.1 (2025-11-16):
        - Adicionado ?stale para escalabilidade
        """
        try:
            response = await self._request("GET", f"/catalog/service/{service_name}", params={"stale": ""})
            return response.json()
        except:
            return []

    async def get_services_by_tag(self, tag: str) -> Dict[str, List[str]]:
        """Obtém serviços filtrados por tag"""
        try:
            catalog = await self.get_catalog_services()
            filtered = {}
            for service_name, tags in catalog.items():
                if tag in tags:
                    filtered[service_name] = tags
            return filtered
        except:
            return {}

    async def get_datacenters(self) -> List[str]:
        """
        Lista todos os datacenters do Consul
        
        ✅ CORREÇÃO FASE 1.1 (2025-11-16):
        - Adicionado ?stale para escalabilidade
        """
        try:
            response = await self._request("GET", "/catalog/datacenters", params={"stale": ""})
            return response.json()
        except:
            return []

    async def get_nodes(self) -> List[Dict]:
        """
        Lista todos os nós do catálogo
        
        ✅ CORREÇÃO FASE 1.1 (2025-11-16):
        - Adicionado ?stale para escalabilidade
        """
        try:
            response = await self._request("GET", "/catalog/nodes", params={"stale": ""})
            return response.json()
        except:
            return []

    async def get_node_services(self, node_name: str) -> Dict:
        """
        Obtém todos os serviços de um nó específico pelo nome
        
        ✅ CORREÇÃO FASE 1.1 (2025-11-16):
        - Adicionado ?stale para escalabilidade
        """
        try:
            response = await self._request("GET", f"/catalog/node/{node_name}", params={"stale": ""})
            return response.json()
        except:
            return {}

    async def get_service_health(self, service_name: str, passing: bool = False) -> List[Dict]:
        """
        Obtém informações de saúde de um serviço específico

        Args:
            service_name: Nome do serviço
            passing: Se True, retorna apenas instâncias saudáveis
        """
        try:
            path = f"/health/service/{service_name}"
            if passing:
                path += "?passing=true"
            response = await self._request("GET", path)
            return response.json()
        except:
            return []

    async def get_checks(self, service_id: str = None) -> List[Dict]:
        """Obtém health checks (todos ou de um serviço específico)"""
        try:
            if service_id:
                response = await self._request("GET", f"/health/checks/{service_id}")
            else:
                response = await self._request("GET", "/agent/checks")
            return response.json()
        except:
            return []

    async def get_key_value(self, key: str) -> Optional[Dict]:
        """Obtém valor do KV store"""
        try:
            response = await self._request("GET", f"/kv/{key}")
            return response.json()
        except:
            return None

    async def set_key_value(self, key: str, value: str) -> bool:
        """Define valor no KV store"""
        try:
            await self._request("PUT", f"/kv/{key}", content=value.encode())
            return True
        except:
            return False

    async def delete_key(self, key: str) -> bool:
        """Remove chave do KV store"""
        try:
            await self._request("DELETE", f"/kv/{key}")
            return True
        except:
            return False

    async def list_keys(self, prefix: str = "") -> List[str]:
        """Lista chaves do KV store com determinado prefixo"""
        try:
            response = await self._request("GET", f"/kv/{prefix}?keys")
            return response.json()
        except:
            return []

    async def get_kv_json(self, key: str) -> Optional[Dict]:
        """
        Obtém e decodifica o valor de uma chave no KV.

        IMPORTANTE: SEMPRE retorna dict/list ou None, NUNCA string!
        Se valor no KV não for JSON válido, loga erro e retorna None.

        SPRINT 1 - FIX CRÍTICO (2025-11-15)
        Corrige bug: 'str' object has no attribute 'get'
        """
        try:
            response = await self._request("GET", f"/kv/{key}")
            payload = response.json()
            if not payload:
                return None

            raw_value = payload[0].get("Value")
            if raw_value is None:
                return None

            decoded = base64.b64decode(raw_value).decode("utf-8")
            try:
                parsed = json.loads(decoded)
                # ✅ GARANTIR que retorna dict/list, NUNCA string!
                if not isinstance(parsed, (dict, list)):
                    logger.warning(
                        f"❌ KV key '{key}' contém JSON primitivo (não dict/list): {type(parsed).__name__}. "
                        f"Retornando None para evitar erro 'str object has no attribute get'"
                    )
                    return None
                return parsed
            except json.JSONDecodeError as e:
                logger.error(
                    f"❌ KV key '{key}' contém valor não-JSON: {decoded[:100]}... "
                    f"Erro: {e}. Retornando None."
                )
                return None
        except httpx.HTTPStatusError as exc:
            # 404 é NORMAL quando chave não existe - não é erro!
            if exc.response.status_code == 404:
                logger.debug("KV key not found: %s (this is normal if never created)", key)
                return None
            # Outros erros HTTP são reais
            logger.error("Failed to fetch KV %s: HTTP %s", key, exc.response.status_code)
            return None
        except Exception as exc:
            logger.error("Failed to fetch KV %s: %s", key, exc)
            return None

    async def put_kv_json(self, key: str, value: Any) -> bool:
        """Armazena um valor JSON serializável no KV"""
        try:
            payload = json.dumps(value, ensure_ascii=False).encode("utf-8")
            await self._request("PUT", f"/kv/{key}", content=payload)
            return True
        except Exception as exc:
            logger.error("Failed to write KV %s: %s", key, exc)
            return False

    async def get_kv_tree(self, prefix: str, include_metadata: bool = False) -> Dict[str, Dict]:
        """
        Retorna um dicionário com todas as entradas de um prefixo.

        Args:
            prefix: Prefixo para buscar
            include_metadata: Se True, retorna também CreateIndex, ModifyIndex, etc

        Returns:
            Se include_metadata=False: {key: value}
            Se include_metadata=True: {key: {value: ..., metadata: {CreateIndex, ModifyIndex, ...}}}
        """
        try:
            response = await self._request("GET", f"/kv/{prefix}", params={"recurse": "true"})
            entries = response.json()
            result: Dict[str, Dict] = {}

            for item in entries:
                value = item.get("Value")
                if value is None:
                    continue
                decoded = base64.b64decode(value).decode("utf-8")

                # Parse JSON
                try:
                    parsed_value = json.loads(decoded)
                except json.JSONDecodeError:
                    parsed_value = decoded

                # Se include_metadata=True, retornar também CreateIndex, ModifyIndex
                if include_metadata:
                    result[item["Key"]] = {
                        "value": parsed_value,
                        "metadata": {
                            "CreateIndex": item.get("CreateIndex"),
                            "ModifyIndex": item.get("ModifyIndex"),
                            "LockIndex": item.get("LockIndex"),
                            "Flags": item.get("Flags"),
                            "Session": item.get("Session"),
                        }
                    }
                else:
                    result[item["Key"]] = parsed_value

            return result
        except httpx.HTTPStatusError as exc:
            logger.error("Consul returned %s when fetching KV tree for %s", exc.response.status_code, prefix)
            return {}
        except Exception as exc:
            logger.error("Failed to fetch KV tree for %s: %s", prefix, exc)
            return {}

    async def search_services(self, filters: Dict[str, str]) -> Dict[str, Dict]:
        """
        Busca serviços com base em filtros de metadados

        Args:
            filters: Dicionário com campo: valor para filtrar

        Returns:
            Dicionário com service_id: service_data dos serviços que correspondem
        """
        all_services = await self.get_services()
        filtered = {}

        for service_id, service_data in all_services.items():
            meta = service_data.get("Meta", {})
            matches = True

            for field, value in filters.items():
                if field not in meta or meta[field] != value:
                    matches = False
                    break

            if matches:
                filtered[service_id] = service_data

        return filtered

    async def check_duplicate_service(
        self,
        module: str,
        company: str,
        project: str,
        env: str,
        name: str,
        exclude_sid: str = None,
        target_node_addr: str = None
    ) -> bool:
        """
        Verifica se já existe um serviço com a mesma combinação de chaves

        Args:
            module: Módulo do serviço
            company: Empresa
            project: Projeto
            env: Ambiente
            name: Nome
            exclude_sid: ID de serviço para excluir da verificação (útil em updates)
            target_node_addr: Endereço do nó alvo para verificar

        Returns:
            True se encontrou duplicata, False caso contrário
        """
        try:
            services = await self.get_services(target_node_addr)

            for sid, svc in services.items():
                # Pular o próprio serviço se estivermos atualizando
                if exclude_sid and sid == exclude_sid:
                    continue

                meta = svc.get("Meta", {})

                # Verificar se todos os campos chave correspondem
                if (meta.get("module") == module and
                    meta.get("company") == company and
                    meta.get("project") == project and
                    meta.get("env") == env and
                    meta.get("name") == name):
                    return True

            return False
        except Exception as e:
            print(f"Erro ao verificar duplicatas: {e}")
            return False

    async def _load_sites_config(self) -> List[Dict]:
        """
        Carrega configuração de sites do Consul KV (100% dinâmico)

        Returns:
            Lista de sites ordenada (master primeiro, depois clients)
        """
        try:
            sites_data = await self.get_kv_json('skills/eye/metadata/sites')

            if not sites_data:
                logger.warning("⚠️ KV metadata/sites vazio - usando fallback localhost")
                return [{
                    'name': 'localhost',
                    'prometheus_instance': 'localhost',
                    'is_default': True
                }]

            # SPRINT 2 - FIX: Validar tipo de dados antes de usar
            if not isinstance(sites_data, list):
                logger.error(f"❌ KV metadata/sites tem tipo inválido: {type(sites_data).__name__} (esperado: list)")
                return [{
                    'name': 'fallback',
                    'prometheus_instance': Config.get_main_server(),
                    'is_default': True
                }]

            # Ordenar: master (is_default=True) primeiro
            sites = sorted(
                sites_data,
                key=lambda s: (not s.get('is_default', False), s.get('name', ''))
            )

            logger.debug(f"[Sites] Carregados {len(sites)} sites do KV")
            return sites

        except Exception as e:
            logger.error(f"❌ Erro ao carregar sites do KV: {e}")
            # Fallback: usar CONSUL_HOST da env
            return [{
                'name': 'fallback',
                'prometheus_instance': Config.get_main_server(),
                'is_default': True
            }]

    async def get_services_with_fallback(
        self,
        timeout_per_node: float = 2.0,
        global_timeout: float = 30.0
    ) -> Tuple[Dict, Dict]:
        """
        Busca serviços com fallback inteligente (master → clients)

        SPRINT 1 CORREÇÕES (2025-11-15):
        ✅ OFICIAL DOCS COMPLIANT:
        - Usa /catalog/services (vista global, TODOS os serviços)
        - Usa ?cached (Agent caching, background refresh)
        - Usa ?stale (escalabilidade, todos servers)
        - Fontes: https://developer.hashicorp.com/consul/api-docs/

        Args:
            timeout_per_node: Timeout individual por tentativa (default: 2s)
            global_timeout: Timeout total para todas tentativas (default: 30s)

        Returns:
            Tuple (services_dict, metadata):
                - services_dict: {service_name: [tags]}
                - metadata: {
                    "source_node": "172.16.1.26",
                    "source_name": "Palmas",
                    "is_master": True,
                    "attempts": 1,
                    "total_time_ms": 52,
                    "cache_status": "HIT",
                    "age_seconds": 0,
                    "staleness_ms": 15
                  }

        Raises:
            Exception: Se TODOS os nodes falharem
        """
        start_time = datetime.now()
        sites = await self._load_sites_config()

        attempts = 0
        errors = []

        for site in sites:
            attempts += 1
            node_addr = site.get("prometheus_instance")
            node_name = site.get("name", node_addr)
            is_master = site.get("is_default", False)

            if not node_addr:
                continue

            try:
                logger.debug(
                    f"[Consul Fallback] Tentativa {attempts}: {node_name} ({node_addr}) "
                    f"[{'MASTER' if is_master else 'client'}]"
                )

                # Criar manager temporário para o node específico
                temp_manager = ConsulManager(host=node_addr, token=self.token)

                # ✅ CORREÇÃO CRÍTICA: Catalog API (não Agent API!)
                # Catalog API retorna TODOS os serviços do datacenter
                # Agent API retornaria APENAS serviços locais do node
                response = await asyncio.wait_for(
                    temp_manager._request(
                        "GET",
                        "/catalog/services",
                        use_cache=True,  # ← Agent caching (OFFICIAL FEATURE)
                        params={"stale": ""}  # ← Stale reads (OFFICIAL CONSISTENCY MODE)
                    ),
                    timeout=timeout_per_node
                )

                services = response.json()
                elapsed_ms = (datetime.now() - start_time).total_seconds() * 1000

                # ✅ Metadata completo (conforme Copilot especificou)
                metadata = {
                    "source_node": node_addr,
                    "source_name": node_name,
                    "is_master": is_master,
                    "attempts": attempts,
                    "total_time_ms": int(elapsed_ms),
                    "cache_status": response.headers.get("X-Cache", "MISS"),
                    "age_seconds": int(response.headers.get("Age", "0")),
                    "staleness_ms": int(response.headers.get("X-Consul-LastContact", "0"))
                }

                if not is_master:
                    logger.warning(
                        f"⚠️ [Consul Fallback] Master inacessível! Usando client {node_name}"
                    )
                    metadata["warning"] = f"Master offline - dados de {node_name}"

                logger.info(
                    f"✅ [Consul Fallback] Sucesso em {elapsed_ms:.0f}ms via {node_name} "
                    f"(cache={metadata['cache_status']}, staleness={metadata['staleness_ms']}ms)"
                )

                return (services, metadata)

            except asyncio.TimeoutError:
                error_msg = f"Timeout {timeout_per_node}s em {node_name} ({node_addr})"
                errors.append(error_msg)
                logger.warning(f"⏱️ [Consul Fallback] {error_msg}")

            except Exception as e:
                error_msg = f"Erro em {node_name} ({node_addr}): {str(e)[:100]}"
                errors.append(error_msg)
                logger.error(f"❌ [Consul Fallback] {error_msg}")

            # Verificar timeout global
            elapsed = (datetime.now() - start_time).total_seconds()
            if elapsed >= global_timeout:
                logger.warning(
                    f"⏱️ [Consul Fallback] Timeout global {global_timeout}s atingido"
                )
                break

        # ❌ TODAS as tentativas falharam!
        elapsed_ms = (datetime.now() - start_time).total_seconds() * 1000
        raise Exception(
            f"❌ [Consul Fallback] Nenhum node acessível após {attempts} tentativas "
            f"({elapsed_ms:.0f}ms). Erros: {'; '.join(errors)}"
        )

    async def get_all_services_catalog(
        self,
        use_fallback: bool = True
    ) -> Dict[str, Dict]:
        """
        ✅ NOVA ABORDAGEM - Usa /catalog/services com fallback

        SPRINT 1 CORREÇÕES (2025-11-15):
        ✅ OFICIAL DOCS COMPLIANT:
        - Usa Catalog API (vista global, não Agent API local)
        - Usa Agent Caching (?cached) para background refresh
        - Usa Stale Reads (?stale) para escalabilidade

        SPRINT 2 (2025-11-15):
        ✅ LOCAL CACHE com TTL 60s:
        - Reduz latência de 1289ms → ~10ms (128x mais rápido!)
        - Cache complementa Agent Caching (TTL 3 dias)
        - Ideal para requests repetidos em janelas curtas

        Substitui get_all_services_from_all_nodes() com correção crítica:
        - ANTES (Agent API): Dados INCOMPLETOS (só serviços locais do node)
        - AGORA (Catalog API): Dados COMPLETOS (todos serviços do cluster)

        Args:
            use_fallback: Se True, tenta master → clients (default: True)

        Returns:
            Dict {node_name: {service_id: service_data}, "_metadata": metadata}

        Performance:
            - Com cache HIT: ~10ms (128x mais rápido!)
            - Master online (cache miss): 50ms (1 request)
            - Master offline + client online: 2.05s (2 tentativas)
            - Todos offline: 6.15s (3 tentativas × 2s + overhead)

        Comparação com método antigo:
            - Antigo (Agent API): 150ms (dados incompletos, timeout 33s se 1 offline)
            - Novo (Catalog API): 50ms (dados completos, timeout 6s se todos offline)
            - Novo + Cache: ~10ms (dados completos, latência mínima!)
        """
        # ❌ CACHE DESABILITADO: Causava erro "'str' object does not support item assignment"
        # Cache local incompatível com estrutura de dados deste método

        if use_fallback:
            # ✅ CORREÇÃO CRÍTICA (2025-11-16)
            # PROBLEMA IDENTIFICADO: Claude Code usava /agent/services (retorna só LOCAL)
            # SOLUÇÃO: Usar /catalog/services (lista global) + /catalog/service/{name} (detalhes)
            # PERFORMANCE: 1 request lista + N requests paralelos assíncronos = ~50-200ms
            # DADOS: 100% completos (todos os serviços do datacenter)

            # Buscar node ativo com fallback
            _, metadata = await self.get_services_with_fallback()
            source_node = metadata["source_node"]

            logger.debug(f"[Catalog] Buscando lista de serviços de {source_node}")

            # PASSO 1: Buscar lista de nomes dos serviços (leve, 4-10ms)
            temp_manager = ConsulManager(host=source_node, token=self.token)
            response = await temp_manager._request(
                "GET",
                "/catalog/services",
                use_cache=True,
                params={"stale": "", "cached": ""}
            )

            service_names = response.json()  # Dict {name: [tags]}
            logger.debug(f"[Catalog] Encontrados {len(service_names)} nomes de serviços")

            # PASSO 2: Buscar detalhes de TODOS os serviços em PARALELO
            async def fetch_service_details(name: str):
                """Busca detalhes de um serviço específico"""
                try:
                    resp = await temp_manager._request(
                        "GET",
                        f"/catalog/service/{name}",
                        use_cache=True,
                        params={"stale": "", "cached": ""}
                    )
                    return name, resp.json()
                except Exception as e:
                    logger.error(f"[Catalog] Erro ao buscar serviço '{name}': {e}")
                    return name, []

            # Executar todas as requisições em paralelo
            tasks = [fetch_service_details(name) for name in service_names.keys()]
            results = await asyncio.gather(*tasks)

            # PASSO 3: Converter para estrutura {node_name: {service_id: service_data}}
            all_services = {}

            for service_name, instances in results:
                for instance in instances:
                    node_name = instance.get("Node", "unknown")
                    service_id = instance.get("ServiceID", f"{service_name}-{node_name}")

                    if node_name not in all_services:
                        all_services[node_name] = {}

                    all_services[node_name][service_id] = {
                        "ID": service_id,
                        "Service": service_name,
                        "Tags": instance.get("ServiceTags", []),
                        "Meta": instance.get("ServiceMeta", {}),
                        "Port": instance.get("ServicePort", 0),
                        "Address": instance.get("ServiceAddress", ""),
                        "Node": node_name,
                        "NodeAddress": instance.get("Address", "")
                    }

            # Adicionar metadata para debugging
            all_services["_metadata"] = metadata

            total_services = sum(len(svcs) for k, svcs in all_services.items() if k != '_metadata')
            logger.info(
                f"[Catalog] ✅ Retornados {total_services} serviços completos "
                f"({len(service_names)} nomes × múltiplas instâncias)"
            )

            return all_services
        else:
            # Modo legado: apenas consulta self.host (MAIN_SERVER)
            logger.debug("[Catalog] Modo legado sem fallback - consultando MAIN_SERVER")
            response = await self._request(
                "GET",
                "/catalog/services",
                use_cache=True,
                params={"stale": ""}
            )
            services = response.json()
            return {"default": services}

    async def get_all_services_from_all_nodes(self) -> Dict[str, Dict]:
        """
        ⚠️ DEPRECATED - Esta função usa Agent API que retorna apenas dados locais

        SPRINT 1 CORREÇÕES (2025-11-15):
        ════════════════════════════════════════════════════════════════════════

        PROBLEMA IDENTIFICADO (2025-11-15):
        ────────────────────────────────
        - ❌ Agent API (/agent/services) retorna APENAS serviços LOCAIS do node
        - ❌ Resulta em PERDA DE DADOS quando consultado em clients
        - ❌ Exemplo: Consultar Rio retorna APENAS blackbox_exporter_rio
        - ❌ NÃO retorna serviços de Palmas ou Dtc!

        SOLUÇÃO IMPLEMENTADA:
        ─────────────────────
        - ✅ Use get_all_services_catalog() que usa Catalog API
        - ✅ Catalog API retorna TODOS os serviços do datacenter
        - ✅ Implementa Agent Caching (?cached) para performance
        - ✅ Implementa Stale Reads (?stale) para escalabilidade

        MIGRAÇÃO:
        ─────────
        ```python
        # ❌ ANTES (dados incompletos)
        services = await consul_manager.get_all_services_from_all_nodes()

        # ✅ DEPOIS (dados completos)
        services = await consul_manager.get_all_services_catalog(use_fallback=True)
        metadata = services.pop("_metadata")  # Extrair metadata
        ```

        ARQUIVOS QUE PRECISAM MIGRAR:
        - backend/api/monitoring_unified.py:214
        - backend/api/services.py:54, 248
        - backend/core/blackbox_manager.py:142

        Returns:
            Dict[str, Dict]: {node_name: {service_id: service_data}}

        Raises:
            DeprecationWarning: Sempre avisa que função está depreciada
        """
        # ✅ Emitir deprecation warning
        warnings.warn(
            "get_all_services_from_all_nodes() is deprecated and returns incomplete data "
            "(Agent API retorna apenas serviços locais do node). "
            "Use get_all_services_catalog() instead which uses Catalog API and returns "
            "ALL services from the entire datacenter.",
            DeprecationWarning,
            stacklevel=2
        )

        # ✅ REDIRECIONAR para nova função
        logger.warning(
            "⚠️ [DEPRECATED] get_all_services_from_all_nodes() chamada. "
            "Redirecionando para get_all_services_catalog(). "
            "Por favor, migre o código para usar a nova função."
        )

        return await self.get_all_services_catalog(use_fallback=True)

    async def get_service_metrics(self, service_name: str = None) -> Dict:
        """
        Obtém métricas agregadas dos serviços

        Returns:
            Dicionário com métricas como total, por status, por nó, etc.
        """
        try:
            if service_name:
                health_data = await self.get_service_health(service_name)
            else:
                health_data = await self.get_health_status()

            metrics = {
                "total": len(health_data),
                "passing": 0,
                "warning": 0,
                "critical": 0,
                "by_node": {},
                "by_service": {}
            }

            for entry in health_data:
                # Contar por status
                checks = entry.get("Checks", [])
                if any(c.get("Status") == "critical" for c in checks):
                    metrics["critical"] += 1
                elif any(c.get("Status") == "warning" for c in checks):
                    metrics["warning"] += 1
                else:
                    metrics["passing"] += 1

                # Contar por nó
                node = entry.get("Node", {}).get("Node", "unknown")
                metrics["by_node"][node] = metrics["by_node"].get(node, 0) + 1

                # Contar por serviço
                service = entry.get("Service", {}).get("Service", "unknown")
                metrics["by_service"][service] = metrics["by_service"].get(service, 0) + 1

            return metrics
        except Exception as e:
            print(f"Erro ao obter métricas: {e}")
            return {
                "total": 0,
                "passing": 0,
                "warning": 0,
                "critical": 0,
                "by_node": {},
                "by_service": {}
            }

    async def validate_service_data(self, service_data: Dict) -> tuple[bool, List[str]]:
        """
        Valida dados de um serviço antes de registrar

        Returns:
            Tupla (is_valid, list_of_errors)
        """
        errors = []

        # Verificar campos obrigatórios
        if "id" not in service_data:
            errors.append("Campo 'id' é obrigatório")

        if "name" not in service_data:
            errors.append("Campo 'name' é obrigatório")

        # Verificar metadados obrigatórios
        meta = service_data.get("Meta", {})
        for field in Config.REQUIRED_FIELDS:
            if field not in meta or not meta[field]:
                errors.append(f"Campo obrigatório faltando em Meta: {field}")

        # Validar formato de instance se for módulo blackbox
        if meta.get("module") in ["http_2xx", "https", "http_4xx", "http_post_2xx"]:
            instance = meta.get("instance", "")
            if not instance.startswith("http://") and not instance.startswith("https://"):
                errors.append(f"Instance deve começar com http:// ou https:// para módulo {meta.get('module')}")

        # Validar porta se especificada
        if "port" in service_data:
            try:
                port = int(service_data["port"])
                if port < 1 or port > 65535:
                    errors.append("Porta deve estar entre 1 e 65535")
            except (ValueError, TypeError):
                errors.append("Porta deve ser um número inteiro")

        return len(errors) == 0, errors

    async def bulk_register_services(self, services: List[Dict], node_addr: str = None) -> Dict[str, bool]:
        """
        Registra múltiplos serviços em lote

        Returns:
            Dicionário com {service_id: success_status}
        """
        results = {}

        for service_data in services:
            service_id = service_data.get("id", "unknown")
            try:
                success = await self.register_service(service_data, node_addr)
                results[service_id] = success
            except Exception as e:
                print(f"Erro ao registrar serviço {service_id}: {e}")
                results[service_id] = False

        return results

    async def bulk_deregister_services(self, service_ids: List[str], node_addr: str = None) -> Dict[str, bool]:
        """
        Remove múltiplos serviços em lote

        Returns:
            Dicionário com {service_id: success_status}
        """
        results = {}

        for service_id in service_ids:
            try:
                success = await self.deregister_service(service_id, node_addr)
                results[service_id] = success
            except Exception as e:
                print(f"Erro ao remover serviço {service_id}: {e}")
                results[service_id] = False

        return results
