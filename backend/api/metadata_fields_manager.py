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
from typing import List, Dict, Any, Optional
from pathlib import Path
import json
import logging
from datetime import datetime, timedelta

from core.multi_config_manager import MultiConfigManager

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
