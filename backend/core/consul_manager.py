"""
Classe ConsulManager adaptada do script original
Mantém todas as funcionalidades mas estruturada para API
Versão async para FastAPI
"""
import asyncio
import httpx
from typing import Dict, List, Optional, Set
from urllib.parse import quote
from functools import wraps
from .config import Config

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
                except (httpx.RequestError, httpx.HTTPError, ConnectionError) as e:
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
        self.host = host or Config.MAIN_SERVER
        self.port = port or Config.CONSUL_PORT
        self.token = token or Config.CONSUL_TOKEN
        self.base_url = f"http://{self.host}:{self.port}/v1"
        self.headers = {"X-Consul-Token": self.token}

    @retry_with_backoff()
    async def _request(self, method: str, path: str, **kwargs):
        """Requisição HTTP assíncrona para API do Consul"""
        kwargs.setdefault("headers", self.headers)
        kwargs.setdefault("timeout", 10)
        url = f"{self.base_url}{path}"

        async with httpx.AsyncClient() as client:
            response = await client.request(method, url, **kwargs)
            response.raise_for_status()
            return response

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
        """Obtém serviços de um nó específico ou local"""
        if node_addr and node_addr != self.host:
            # Conectar ao nó específico
            temp_manager = ConsulManager(host=node_addr, token=self.token)
            return await temp_manager.get_services()

        try:
            response = await self._request("GET", "/agent/services")
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
        """Lista todos os serviços do catálogo"""
        try:
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
        Nota: Consul não tem endpoint de update, então fazemos deregister + register
        """
        if node_addr and node_addr != self.host:
            temp_manager = ConsulManager(host=node_addr, token=self.token)
            return await temp_manager.update_service(service_id, service_data)

        try:
            # Primeiro remove o serviço existente
            await self.deregister_service(service_id, node_addr)
            # Aguarda um pouco para garantir que foi removido
            await asyncio.sleep(0.5)
            # Registra novamente com novos dados
            return await self.register_service(service_data, node_addr)
        except Exception as e:
            print(f"Erro ao atualizar serviço: {e}")
            return False

    async def get_service_by_id(self, service_id: str, node_addr: str = None) -> Optional[Dict]:
        """Obtém detalhes de um serviço específico pelo ID"""
        services = await self.get_services(node_addr)
        return services.get(service_id)

    async def get_services_by_name(self, service_name: str) -> List[Dict]:
        """Obtém todos os serviços com um nome específico do catálogo"""
        try:
            response = await self._request("GET", f"/catalog/service/{service_name}")
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
        """Lista todos os datacenters do Consul"""
        try:
            response = await self._request("GET", "/catalog/datacenters")
            return response.json()
        except:
            return []

    async def get_nodes(self) -> List[Dict]:
        """Lista todos os nós do catálogo"""
        try:
            response = await self._request("GET", "/catalog/nodes")
            return response.json()
        except:
            return []

    async def get_node_services(self, node_name: str) -> Dict:
        """Obtém todos os serviços de um nó específico pelo nome"""
        try:
            response = await self._request("GET", f"/catalog/node/{node_name}")
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

    async def get_all_services_from_all_nodes(self) -> Dict[str, Dict]:
        """
        Obtém todos os serviços de todos os nós do cluster

        Returns:
            Dicionário com estrutura: {node_name: {service_id: service_data}}
        """
        all_services = {}

        try:
            members = await self.get_members()

            for member in members:
                node_name = member["node"]
                node_addr = member["addr"]

                try:
                    temp_consul = ConsulManager(host=node_addr, token=self.token)
                    services = await temp_consul.get_services()
                    all_services[node_name] = services
                except Exception as e:
                    print(f"Erro ao obter serviços do nó {node_name}: {e}")
                    all_services[node_name] = {}

            return all_services
        except Exception as e:
            print(f"Erro ao obter serviços de todos os nós: {e}")
            return {}

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
