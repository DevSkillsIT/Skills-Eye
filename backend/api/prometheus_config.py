"""
API para Gerenciamento de Configurações do Prometheus

Endpoints para:
- Listar/criar/editar/deletar jobs
- Extrair campos metadata dinâmicos
- Preview de YAML
- Backup e restore
- Aplicar configurações e recarregar Prometheus
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks, Query, Body
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging
import paramiko
import os
from io import StringIO
from ruamel.yaml import YAML

from core.yaml_config_service import YamlConfigService
from core.fields_extraction_service import FieldsExtractionService, MetadataField
from core.consul_manager import ConsulManager
from core.multi_config_manager import MultiConfigManager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/prometheus-config", tags=["Prometheus Config"])

# Instâncias dos serviços
yaml_service = YamlConfigService()
fields_service = FieldsExtractionService()
multi_config = MultiConfigManager()  # NOVO - Gerenciador de múltiplos arquivos

# Cache para job_names (evitar SSH toda vez) - TTL de 5 minutos
_job_names_cache: Dict[str, Dict[str, Any]] = {}


# ============================================================================
# MODELOS PYDANTIC
# ============================================================================

class JobResponse(BaseModel):
    """Resposta com dados de um job"""
    success: bool
    job: Dict[str, Any]


class JobsListResponse(BaseModel):
    """Resposta com lista de jobs"""
    success: bool
    jobs: List[Dict[str, Any]]
    total: int


class ServerStatus(BaseModel):
    """Status de processamento de um servidor"""
    hostname: str
    success: bool
    from_cache: bool = False
    files_count: int = 0
    fields_count: int = 0
    error: Optional[str] = None
    duration_ms: int = 0


class FieldsResponse(BaseModel):
    """Resposta com campos metadata + status de cada servidor"""
    success: bool
    fields: List[Dict[str, Any]]
    total: int
    last_updated: str
    server_status: Optional[List[ServerStatus]] = None
    total_servers: Optional[int] = None
    successful_servers: Optional[int] = None
    from_cache: bool = False


class BackupResponse(BaseModel):
    """Resposta com lista de backups"""
    success: bool
    backups: List[Dict[str, Any]]
    total: int


class PreviewResponse(BaseModel):
    """Resposta com preview do YAML"""
    success: bool
    yaml_content: str


class ApplyResponse(BaseModel):
    """Resposta de aplicação de config"""
    success: bool
    message: str
    backup_created: Optional[str] = None
    prometheus_reloaded: bool


# ============================================================================
# ENDPOINTS - LISTAGEM E LEITURA
# ============================================================================

@router.get("/jobs", response_model=JobsListResponse)
async def list_jobs():
    """
    Lista todos os scrape jobs configurados

    Returns:
        Lista de jobs com todas as configurações
    """
    try:
        jobs = yaml_service.get_all_jobs()

        return JobsListResponse(
            success=True,
            jobs=jobs,
            total=len(jobs)
        )

    except Exception as e:
        logger.error(f"Erro ao listar jobs: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/jobs/{job_name}", response_model=JobResponse)
async def get_job(job_name: str):
    """
    Obtém detalhes de um job específico

    Args:
        job_name: Nome do job

    Returns:
        Dados completos do job
    """
    try:
        job = yaml_service.get_job_by_name(job_name)

        if not job:
            raise HTTPException(
                status_code=404,
                detail=f"Job '{job_name}' não encontrado"
            )

        return JobResponse(success=True, job=job)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao buscar job {job_name}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/files")
async def list_config_files(
    service: Optional[str] = Query(None),
    hostname: Optional[str] = Query(None, description="Filtrar por hostname específico (ex: 172.16.1.26)")
):
    """
    Lista arquivos de configuração disponíveis

    Args:
        service: Filtrar por serviço ('prometheus', 'blackbox', 'alertmanager')
        hostname: Filtrar por hostname específico (carrega apenas de um servidor)

    Returns:
        Lista de arquivos .yml encontrados
    """
    try:
        print(f"[/files] service={service}, hostname={hostname}")
        # OTIMIZAÇÃO CRÍTICA: Passar hostname para evitar SSH em todos os servidores
        files = multi_config.list_config_files(service, hostname=hostname)

        files_list = [
            {
                'path': str(f.path),
                'service': f.service,
                'filename': f.filename,
                'host': f"{f.host.username}@{f.host.hostname}:{f.host.port}",
                'exists': f.exists
            }
            for f in files
        ]

        return {
            "success": True,
            "files": files_list,
            "total": len(files_list)
        }

    except Exception as e:
        logger.error(f"Erro ao listar arquivos: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/summary")
async def get_config_summary():
    """
    Retorna resumo de todas as configurações

    Returns:
        Estatísticas dos arquivos e campos
    """
    try:
        summary = multi_config.get_config_summary()

        return {
            "success": True,
            **summary
        }

    except Exception as e:
        logger.error(f"Erro ao gerar resumo: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/fields", response_model=FieldsResponse)
async def get_available_fields(enrich_with_values: bool = Query(True), force_refresh: bool = Query(False)):
    """
    Retorna TODOS os campos metadata extraídos de TODOS os arquivos de TODOS os servidores

    **OTIMIZAÇÃO COLD START**: Lê do Consul KV primeiro (INSTANTÂNEO), só extrai via SSH se forçado ou KV vazio

    Extrai campos de:
    - prometheus.yml
    - blackbox.yml
    - alertmanager.yml
    - Qualquer outro .yml nas pastas padrão

    Processa os 3 servidores EM PARALELO usando ThreadPoolExecutor.

    Estes campos são usados para gerar formulários dinâmicos no frontend.

    Args:
        enrich_with_values: Se True, adiciona valores únicos do Consul
        force_refresh: Se True, força re-extração via SSH ignorando KV

    Returns:
        Lista consolidada de campos metadata de TODOS os servidores
    """
    try:
        # OTIMIZAÇÃO: Tentar ler do KV primeiro (evita SSH no cold start)
        if not force_refresh:
            try:
                from core.kv_manager import KVManager
                kv_manager = KVManager()

                kv_data = await kv_manager.get_json('skills/cm/metadata/fields')

                if kv_data and kv_data.get('fields'):
                    logger.info(f"[FIELDS] Retornando {len(kv_data['fields'])} campos do KV (cache) - EVITANDO SSH")
                    return FieldsResponse(
                        success=True,
                        fields=kv_data['fields'],
                        total=len(kv_data['fields']),
                        last_updated=kv_data.get('last_updated', datetime.now().isoformat()),
                        server_status=kv_data.get('extraction_status', {}).get('server_status', []),
                        total_servers=kv_data.get('extraction_status', {}).get('total_servers', 0),
                        successful_servers=kv_data.get('extraction_status', {}).get('successful_servers', 0),
                        from_cache=True,
                    )
            except Exception as e:
                logger.warning(f"[FIELDS] KV não disponível, extraindo via SSH: {e}")
        else:
            # CORREÇÃO CRÍTICA: force_refresh=true DEVE limpar cache em memória E fechar conexões SSH
            # Sem isso, mesmo com force_refresh, o MultiConfigManager retorna cache antigo
            # Problema identificado no RELATORIO_REAL_PERFORMANCE.md
            # OTIMIZAÇÃO P1: Fechar conexões SSH antigas para garantir dados frescos
            logger.info("[FIELDS] force_refresh=true - Limpando cache e fechando conexões SSH")
            multi_config.clear_cache(close_connections=True)

        # Extrair de TODOS os servidores EM PARALELO COM STATUS de cada servidor
        logger.info(f"[FIELDS] Extração completa via SSH - TODOS os 3 servidores em PARALELO")
        extraction_result = multi_config.extract_all_fields_with_status()

        fields = extraction_result['fields']

        # Enriquecer com valores do Consul se solicitado
        if enrich_with_values:
            try:
                consul = ConsulManager()
                fields = await fields_service.enrich_fields_with_values(fields)
            except Exception as e:
                logger.warning(f"Não foi possível enriquecer campos com valores do Consul: {e}")
                print(f"ConsulManager não disponível para enriquecer campos")

        # Converter para dict
        fields_dict = [field.to_dict() for field in fields]

        # SALVAR AUTOMATICAMENTE NO CONSUL KV
        # O KV é a fonte de verdade - campos vêm do Prometheus e são salvos no KV
        try:
            from core.kv_manager import KVManager
            kv_manager = KVManager()

            # Salvar no KV: skills/cm/metadata/fields
            await kv_manager.put_json(
                key='skills/cm/metadata/fields',
                value={
                    'version': '2.0.0',
                    'last_updated': datetime.now().isoformat(),
                    'source': 'prometheus_yml_dynamic_extraction',
                    'total_fields': len(fields_dict),
                    'fields': fields_dict,
                    'extraction_status': {
                        'total_servers': extraction_result.get('total_servers'),
                        'successful_servers': extraction_result.get('successful_servers'),
                        'server_status': extraction_result.get('server_status'),
                    }
                },
                metadata={'auto_updated': True, 'source': 'prometheus_config_api'}
            )
            logger.info(f"[KV-SAVE] Campos salvos automaticamente no Consul KV: {len(fields_dict)} campos")
        except Exception as e:
            logger.warning(f"[KV-SAVE] Não foi possível salvar campos no KV: {e}")
            # Não bloqueia a resposta se falhar o salvamento

        return FieldsResponse(
            success=True,
            fields=fields_dict,
            total=len(fields_dict),
            last_updated=datetime.now().isoformat(),
            server_status=extraction_result.get('server_status'),
            total_servers=extraction_result.get('total_servers'),
            successful_servers=extraction_result.get('successful_servers'),
            from_cache=extraction_result.get('from_cache', False),
        )

    except Exception as e:
        logger.error(f"Erro ao extrair campos: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/fields/{field_name}/values")
async def get_field_values(field_name: str):
    """
    Retorna valores únicos de um campo específico

    Args:
        field_name: Nome do campo (ex: "company", "env")

    Returns:
        Lista de valores únicos e estatísticas
    """
    try:
        consul = ConsulManager()
        services = await consul.get_services()

        stats = fields_service.get_field_statistics(services, field_name)

        return {
            "success": True,
            **stats
        }

    except Exception as e:
        logger.error(f"Erro ao buscar valores do campo {field_name}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# ENDPOINTS - CRUD DE JOBS
# ============================================================================

@router.post("/jobs", response_model=JobResponse)
async def create_job(job_data: Dict[str, Any]):
    """
    Cria um novo scrape job

    Args:
        job_data: Dados do job a criar

    Returns:
        Job criado
    """
    try:
        # Validar job_name
        if 'job_name' not in job_data:
            raise HTTPException(
                status_code=400,
                detail="Campo 'job_name' é obrigatório"
            )

        # Criar job
        success = yaml_service.create_job(job_data)

        if success:
            return JobResponse(success=True, job=job_data)
        else:
            raise HTTPException(
                status_code=500,
                detail="Falha ao criar job"
            )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao criar job: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/jobs/{job_name}", response_model=JobResponse)
async def update_job(job_name: str, job_data: Dict[str, Any]):
    """
    Atualiza um job existente

    Args:
        job_name: Nome do job a atualizar
        job_data: Novos dados do job

    Returns:
        Job atualizado
    """
    try:
        success = yaml_service.update_job(job_name, job_data)

        if success:
            return JobResponse(success=True, job=job_data)
        else:
            raise HTTPException(
                status_code=500,
                detail="Falha ao atualizar job"
            )

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao atualizar job {job_name}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/jobs/{job_name}")
async def delete_job(job_name: str):
    """
    Remove um job

    Args:
        job_name: Nome do job a remover

    Returns:
        Confirmação de remoção
    """
    try:
        success = yaml_service.delete_job(job_name)

        if success:
            return {
                "success": True,
                "message": f"Job '{job_name}' removido com sucesso"
            }
        else:
            raise HTTPException(
                status_code=500,
                detail="Falha ao remover job"
            )

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao remover job {job_name}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# ENDPOINTS - PREVIEW E APLICAÇÃO
# ============================================================================

@router.get("/preview", response_model=PreviewResponse)
async def preview_config():
    """
    Gera preview do YAML atual

    Returns:
        YAML formatado da configuração atual
    """
    try:
        config = yaml_service.read_config()
        yaml_content = yaml_service.get_preview(config)

        return PreviewResponse(
            success=True,
            yaml_content=yaml_content
        )

    except Exception as e:
        logger.error(f"Erro ao gerar preview: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/apply", response_model=ApplyResponse)
async def apply_config(
    config: Dict[str, Any],
    reload_prometheus: bool = Query(True),
    background_tasks: BackgroundTasks = None
):
    """
    Aplica nova configuração

    1. Valida com promtool
    2. Cria backup
    3. Salva arquivo
    4. Recarrega Prometheus (opcional)

    Args:
        config: Configuração completa a aplicar
        reload_prometheus: Se deve recarregar Prometheus após salvar

    Returns:
        Status da aplicação
    """
    try:
        # Salvar (já faz backup e validação)
        backup_path = yaml_service.create_backup("Aplicação via API")
        success = yaml_service.save_config(config, "Aplicado via API")

        # Recarregar Prometheus se solicitado
        prometheus_reloaded = False
        if reload_prometheus and success:
            prometheus_reloaded = yaml_service.reload_prometheus()

        return ApplyResponse(
            success=success,
            message="Configuração aplicada com sucesso",
            backup_created=str(backup_path),
            prometheus_reloaded=prometheus_reloaded
        )

    except RuntimeError as e:
        # Erro de validação
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Erro ao aplicar configuração: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/reload")
async def reload_prometheus():
    """
    Recarrega Prometheus sem mudar configuração

    Returns:
        Status do reload
    """
    try:
        success = yaml_service.reload_prometheus()

        if success:
            return {
                "success": True,
                "message": "Prometheus recarregado com sucesso"
            }
        else:
            raise HTTPException(
                status_code=500,
                detail="Falha ao recarregar Prometheus"
            )

    except Exception as e:
        logger.error(f"Erro ao recarregar Prometheus: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# ENDPOINTS - BACKUPS
# ============================================================================

@router.get("/backups", response_model=BackupResponse)
async def list_backups():
    """
    Lista todos os backups disponíveis

    Returns:
        Lista de backups com metadados
    """
    try:
        backups = yaml_service.list_backups()

        return BackupResponse(
            success=True,
            backups=backups,
            total=len(backups)
        )

    except Exception as e:
        logger.error(f"Erro ao listar backups: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/backups/create")
async def create_backup(reason: str = Query("Manual backup")):
    """
    Cria backup manual da configuração atual

    Args:
        reason: Motivo do backup

    Returns:
        Path do backup criado
    """
    try:
        backup_path = yaml_service.create_backup(reason)

        return {
            "success": True,
            "message": "Backup criado com sucesso",
            "backup_path": str(backup_path)
        }

    except Exception as e:
        logger.error(f"Erro ao criar backup: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/backups/{backup_filename}/restore")
async def restore_backup(backup_filename: str):
    """
    Restaura um backup

    Args:
        backup_filename: Nome do arquivo de backup

    Returns:
        Status da restauração
    """
    try:
        success = yaml_service.restore_backup(backup_filename)

        if success:
            return {
                "success": True,
                "message": f"Backup '{backup_filename}' restaurado com sucesso"
            }
        else:
            raise HTTPException(
                status_code=500,
                detail="Falha ao restaurar backup"
            )

    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Erro ao restaurar backup: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# ENDPOINTS - VALIDAÇÃO E UTILITÁRIOS
# ============================================================================

@router.post("/validate")
async def validate_config(config: Dict[str, Any]):
    """
    Valida uma configuração sem salvá-la

    Args:
        config: Configuração a validar

    Returns:
        Resultado da validação
    """
    try:
        is_valid = yaml_service.validate_config(config)

        return {
            "success": True,
            "valid": is_valid,
            "message": "Configuração válida" if is_valid else "Configuração inválida"
        }

    except RuntimeError as e:
        return {
            "success": True,
            "valid": False,
            "message": str(e)
        }
    except Exception as e:
        logger.error(f"Erro ao validar configuração: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/suggest-fields")
async def suggest_fields():
    """
    Analisa serviços do Consul e sugere campos metadata

    Útil para configuração inicial ou descoberta de novos campos.

    Returns:
        Lista de campos sugeridos baseados em serviços existentes
    """
    try:
        consul = ConsulManager()
        services = await consul.get_services()

        suggested_fields = fields_service.suggest_fields_from_services(services)

        fields_dict = [field.to_dict() for field in suggested_fields]

        return {
            "success": True,
            "fields": fields_dict,
            "total": len(fields_dict),
            "message": f"Sugeridos {len(fields_dict)} campos baseados em serviços existentes"
        }

    except Exception as e:
        logger.error(f"Erro ao sugerir campos: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# NOVOS ENDPOINTS - EDIÇÃO DE ARQUIVOS
# ============================================================================

@router.get("/file/content")
async def get_file_content(file_path: str = Query(..., description="Path do arquivo")):
    """
    Retorna conteúdo bruto (YAML) de um arquivo

    Args:
        file_path: Path completo do arquivo (ex: /etc/prometheus/prometheus.yml)

    Returns:
        Conteúdo do arquivo como string
    """
    try:
        content = multi_config.get_file_content_raw(file_path)

        return {
            "success": True,
            "content": content,
            "file_path": file_path
        }

    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Erro ao ler arquivo: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/file/structure")
async def get_file_structure(
    file_path: str = Query(..., description="Path do arquivo"),
    hostname: Optional[str] = Query(None, description="Hostname do servidor (OTIMIZAÇÃO - evita SSH em múltiplos servidores)")
):
    """
    Retorna a estrutura completa de um arquivo, detectando automaticamente o tipo

    Suporta:
    - prometheus.yml (scrape_configs)
    - blackbox.yml (modules)
    - alertmanager.yml (route, receivers)
    - *_rules.yml (groups)

    Args:
        file_path: Path completo do arquivo
        hostname: Hostname do servidor (opcional, para otimização de performance)

    Returns:
        Estrutura detectada com type, items, editable_sections
    """
    try:
        structure = multi_config.get_config_structure(file_path, hostname=hostname)

        # Não retornar raw_config completo (pode ser muito grande)
        structure_response = {
            'success': True,
            'file_path': structure['file_path'],
            'filename': structure['filename'],
            'type': structure['type'],
            'main_key': structure.get('main_key'),
            'item_key': structure.get('item_key'),
            'items': structure['items'],
            'editable_sections': structure['editable_sections'],
            'total_items': len(structure['items'])
        }

        return structure_response

    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Erro ao obter estrutura: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/file/jobs")
async def get_file_jobs(file_path: str = Query(..., description="Path do arquivo")):
    """
    Lista todos os jobs/scrape_configs de um arquivo

    DEPRECATED: Use /file/structure para suporte a múltiplos tipos

    Args:
        file_path: Path completo do arquivo

    Returns:
        Lista de jobs com todas as configurações
    """
    try:
        jobs = multi_config.get_jobs_from_file(file_path)

        return {
            "success": True,
            "jobs": jobs,
            "total": len(jobs),
            "file_path": file_path
        }

    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Erro ao listar jobs: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# ENDPOINTS - EDIÇÃO DIRETA DE ARQUIVO (Nova Abordagem)
# ============================================================================

class DirectEditRequest(BaseModel):
    """Request para edição direta de arquivo"""
    file_path: str = Field(..., description="Path completo do arquivo no servidor")
    content: str = Field(..., description="Conteúdo completo do arquivo")
    hostname: Optional[str] = Field(None, description="Hostname do servidor (para desambiguação quando múltiplos servidores têm o mesmo arquivo)")


class DirectEditResponse(BaseModel):
    """Response da edição direta"""
    success: bool
    message: str
    validation_result: Optional[Dict[str, Any]] = None
    backup_path: Optional[str] = None


@router.get("/file/raw-content")
async def get_raw_file_content(
    file_path: str = Query(..., description="Path completo do arquivo"),
    hostname: Optional[str] = Query(None, description="Hostname do servidor (para desambiguação)")
):
    """
    Lê o conteúdo RAW do arquivo diretamente do servidor via SSH.

    **NOVA ABORDAGEM - Edição Direta:**
    Este endpoint retorna o arquivo EXATAMENTE como está no servidor,
    preservando 100% da formatação, comentários, espaçamento, etc.

    O frontend usará um editor web (Monaco Editor) para editar
    o conteúdo diretamente, e depois salvará de volta via POST.

    **VANTAGENS:**
    - Preserva TODOS os comentários YAML
    - Preserva formatação original
    - Não faz parse/dump (zero risco de corrupção)
    - Usuário vê exatamente o que está no arquivo

    Args:
        file_path: Path completo do arquivo no servidor
        hostname: Hostname do servidor (opcional, usado quando há arquivos com mesmo path em servidores diferentes)

    Returns:
        Conteúdo RAW do arquivo como string

    Example:
        GET /file/raw-content?file_path=/etc/prometheus/prometheus.yml&hostname=172.16.1.26

        Response:
        {
            "success": true,
            "file_path": "/etc/prometheus/prometheus.yml",
            "content": "# Global config\\nglobal:\\n  scrape_interval: 15s...",
            "size_bytes": 12345,
            "last_modified": "2025-10-28T23:45:00"
        }
    """
    try:
        logger.info(f"[RAW CONTENT] Lendo arquivo: {file_path} (hostname: {hostname})")

        # PASSO 1: Obter informações do arquivo via MultiConfigManager
        config_file = multi_config.get_file_by_path(file_path, hostname=hostname)
        if not config_file:
            raise HTTPException(
                status_code=404,
                detail=f"Arquivo não encontrado no gerenciador: {file_path}" + (f" no servidor {hostname}" if hostname else "")
            )

        # PASSO 2: Conectar via SSH e ler arquivo RAW
        client = multi_config._get_ssh_client(config_file.host)

        # Comando para ler arquivo E obter informações com marcador
        # Usa um marcador único para separar conteúdo do arquivo das informações do stat
        marker = "<<<EOF_MARKER>>>"
        read_cmd = f"cat {config_file.path} && echo '{marker}' && stat -c '%s %Y' {config_file.path}"

        stdin, stdout, stderr = client.exec_command(read_cmd)
        exit_code = stdout.channel.recv_exit_status()

        if exit_code != 0:
            error = stderr.read().decode('utf-8')
            logger.error(f"[RAW CONTENT] Erro ao ler arquivo: {error}")
            raise HTTPException(
                status_code=500,
                detail=f"Erro ao ler arquivo: {error}"
            )

        # Ler conteúdo completo
        output = stdout.read().decode('utf-8')

        # Separar conteúdo do arquivo e informações do stat usando o marcador
        if marker not in output:
            logger.error(f"[RAW CONTENT] Marcador não encontrado no output")
            raise HTTPException(
                status_code=500,
                detail="Erro ao processar conteúdo do arquivo"
            )

        parts = output.split(marker)
        content = parts[0].rstrip('\n')  # Remove apenas o \n final antes do marcador
        stat_line = parts[1].strip()
        stat_info = stat_line.split()

        if len(stat_info) < 2:
            logger.error(f"[RAW CONTENT] Stat info inválido: {stat_info}")
            raise HTTPException(
                status_code=500,
                detail="Erro ao obter informações do arquivo"
            )

        size_bytes = int(stat_info[0])
        last_modified_timestamp = int(stat_info[1])

        # Converter timestamp para datetime
        from datetime import datetime
        last_modified = datetime.fromtimestamp(last_modified_timestamp).isoformat()

        logger.info(f"[RAW CONTENT] Arquivo lido com sucesso. Tamanho: {size_bytes} bytes")

        return {
            "success": True,
            "file_path": file_path,
            "content": content,
            "size_bytes": size_bytes,
            "last_modified": last_modified,
            "host": config_file.host.hostname,
            "port": config_file.host.port
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[RAW CONTENT] Erro inesperado: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao ler conteúdo do arquivo: {str(e)}"
        )


@router.post("/file/raw-content")
async def save_raw_file_content(request: DirectEditRequest):
    """
    Salva o conteúdo RAW diretamente no arquivo via SSH.

    **NOVA ABORDAGEM - Edição Direta:**
    Este endpoint recebe o conteúdo completo do arquivo editado
    pelo usuário no Monaco Editor e salva DIRETAMENTE no servidor.

    **FLUXO DE SEGURANÇA:**
    1. Cria backup automático (timestamped)
    2. Valida sintaxe YAML antes de salvar
    3. Se for prometheus.yml, valida com promtool
    4. Salva arquivo com permissões corretas
    5. Se validação falhar, restaura backup

    **PRESERVAÇÃO 100%:**
    Como salvamos o arquivo RAW sem parse/dump, comentários
    e formatação são preservados EXATAMENTE como o usuário editou.

    Args:
        request: DirectEditRequest com file_path e content

    Returns:
        Confirmação de sucesso com validação

    Example:
        POST /file/raw-content
        {
            "file_path": "/etc/prometheus/prometheus.yml",
            "content": "# Global config\\nglobal:\\n  scrape_interval: 15s..."
        }

        Response:
        {
            "success": true,
            "message": "Arquivo salvo com sucesso",
            "backup_path": "/etc/prometheus/prometheus.yml.backup-20251028-234500",
            "validation_result": {
                "valid": true,
                "message": "Validação promtool passou"
            }
        }
    """
    try:
        logger.info(f"[RAW SAVE] Salvando arquivo: {request.file_path}")
        logger.info(f"[RAW SAVE] Hostname: {request.hostname}")
        logger.info(f"[RAW SAVE] Tamanho do conteúdo: {len(request.content)} caracteres")

        # PASSO 1: Validar que o arquivo existe (com hostname para desambiguação)
        config_file = multi_config.get_file_by_path(request.file_path, hostname=request.hostname)
        if not config_file:
            detail_msg = f"Arquivo não encontrado: {request.file_path}"
            if request.hostname:
                detail_msg += f" no servidor {request.hostname}"
            raise HTTPException(
                status_code=404,
                detail=detail_msg
            )

        # PASSO 2: Validar sintaxe YAML ANTES de salvar
        import yaml as pyyaml
        try:
            pyyaml.safe_load(request.content)
            logger.info(f"[RAW SAVE] ✓ Sintaxe YAML válida")
        except Exception as yaml_error:
            logger.error(f"[RAW SAVE] ✗ Sintaxe YAML inválida: {yaml_error}")
            raise HTTPException(
                status_code=400,
                detail=f"Sintaxe YAML inválida: {str(yaml_error)}"
            )

        # PASSO 3: Conectar via SSH
        client = multi_config._get_ssh_client(config_file.host)

        # PASSO 4: Criar backup com timestamp
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        backup_path = f"{config_file.path}.backup-{timestamp}"

        backup_cmd = f"cp {config_file.path} {backup_path}"
        logger.info(f"[RAW SAVE] Criando backup: {backup_path}")

        stdin, stdout, stderr = client.exec_command(backup_cmd)
        exit_code = stdout.channel.recv_exit_status()

        if exit_code != 0:
            error = stderr.read().decode('utf-8')
            logger.error(f"[RAW SAVE] Erro ao criar backup: {error}")
            raise HTTPException(
                status_code=500,
                detail=f"Erro ao criar backup: {error}"
            )

        logger.info(f"[RAW SAVE] ✓ Backup criado")

        # PASSO 5: Escrever conteúdo em arquivo temporário
        # IMPORTANTE: Criar arquivo temp no MESMO DIRETÓRIO do arquivo original
        # para que caminhos relativos de arquivos rule_files funcionem no promtool
        import os
        file_dir = os.path.dirname(config_file.path)
        file_base = os.path.basename(config_file.path)
        temp_file = f"{file_dir}/{file_base}.tmp-{timestamp}"

        # Usar cat com heredoc para escrever arquivo (evita problemas de escape)
        write_cmd = f"cat > {temp_file} << 'EOFILE'\n{request.content}\nEOFILE"

        stdin, stdout, stderr = client.exec_command(write_cmd)
        exit_code = stdout.channel.recv_exit_status()

        if exit_code != 0:
            error = stderr.read().decode('utf-8')
            logger.error(f"[RAW SAVE] Erro ao escrever arquivo temp: {error}")
            raise HTTPException(
                status_code=500,
                detail=f"Erro ao escrever arquivo temporário: {error}"
            )

        logger.info(f"[RAW SAVE] ✓ Arquivo temporário criado: {temp_file}")

        # PASSO 6: Validar com promtool se for prometheus.yml
        validation_result = {"valid": True, "message": "Sintaxe YAML válida"}

        if 'prometheus.yml' in request.file_path.lower():
            logger.info(f"[RAW SAVE] Validando com promtool...")

            promtool_cmd = f"promtool check config {temp_file}"
            stdin, stdout, stderr = client.exec_command(promtool_cmd)
            exit_code = stdout.channel.recv_exit_status()

            output = stdout.read().decode('utf-8')
            errors = stderr.read().decode('utf-8')

            if exit_code != 0:
                logger.error(f"[RAW SAVE] ✗ Validação promtool falhou")
                logger.error(f"[RAW SAVE] Output: {output}")
                logger.error(f"[RAW SAVE] Errors: {errors}")

                # Remover arquivo temporário
                client.exec_command(f"rm {temp_file}")

                raise HTTPException(
                    status_code=400,
                    detail={
                        "message": "Validação promtool falhou",
                        "errors": errors or output,
                        "validation_result": {
                            "valid": False,
                            "output": output,
                            "errors": errors
                        }
                    }
                )

            logger.info(f"[RAW SAVE] ✓ Validação promtool passou")
            validation_result = {
                "valid": True,
                "message": "Validação promtool passou",
                "output": output
            }

        # PASSO 7: Mover arquivo temporário para destino final
        move_cmd = f"mv {temp_file} {config_file.path}"
        stdin, stdout, stderr = client.exec_command(move_cmd)
        exit_code = stdout.channel.recv_exit_status()

        if exit_code != 0:
            error = stderr.read().decode('utf-8')
            logger.error(f"[RAW SAVE] Erro ao mover arquivo: {error}")

            # Restaurar backup
            client.exec_command(f"cp {backup_path} {config_file.path}")

            raise HTTPException(
                status_code=500,
                detail=f"Erro ao salvar arquivo: {error}"
            )

        # PASSO 8: Restaurar permissões (prometheus:prometheus)
        chown_cmd = f"chown prometheus:prometheus {config_file.path}"
        client.exec_command(chown_cmd)

        logger.info(f"[RAW SAVE] ✅ Arquivo salvo com sucesso!")

        return DirectEditResponse(
            success=True,
            message="Arquivo salvo com sucesso",
            backup_path=backup_path,
            validation_result=validation_result
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[RAW SAVE] Erro inesperado: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao salvar arquivo: {str(e)}"
        )


@router.post("/service/reload")
async def reload_service(request: Dict[str, str]):
    """
    Recarrega serviços (Prometheus, Blackbox Exporter, Alertmanager) via SSH.

    IMPORTANTE: Usa 'reload' ao invés de 'restart' para evitar downtime.

    Lógica de reload baseada no arquivo editado:
    - Arquivos em /etc/prometheus/ (prometheus.yml, rules, etc): reload prometheus
    - blackbox.yml: reload blackbox_exporter E prometheus (pois prometheus usa os módulos)
    - alertmanager.yml: reload alertmanager

    Args:
        request: {
            "host": "172.16.1.26",
            "file_path": "/etc/prometheus/prometheus.yml"
        }

    Returns:
        Status do reload com detalhes de cada serviço recarregado
    """
    try:
        host_str = request.get("host")
        file_path = request.get("file_path", "")

        if not host_str:
            raise HTTPException(status_code=400, detail="Host não informado")

        if not file_path:
            raise HTTPException(status_code=400, detail="file_path não informado")

        logger.info(f"[RELOAD] Host: {host_str}, Arquivo: {file_path}")

        # Encontrar a configuração do host
        config_host = None
        for host in multi_config.hosts:  # CORRIGIDO: era config_hosts, agora é hosts
            if host.hostname == host_str:
                config_host = host
                break

        if not config_host:
            raise HTTPException(status_code=404, detail=f"Host não encontrado: {host_str}")

        # Conectar via SSH
        client = multi_config._get_ssh_client(config_host)

        # Determinar quais serviços recarregar baseado no arquivo
        services_to_reload = []
        file_path_lower = file_path.lower()

        if 'blackbox' in file_path_lower:
            # Blackbox.yml: reload prometheus-blackbox-exporter E prometheus
            services_to_reload = ['prometheus-blackbox-exporter', 'prometheus']
            logger.info(f"[RELOAD] Arquivo blackbox.yml detectado - recarregando prometheus-blackbox-exporter + prometheus")
        elif 'alertmanager' in file_path_lower:
            # Alertmanager.yml: reload apenas alertmanager
            services_to_reload = ['alertmanager']
            logger.info(f"[RELOAD] Arquivo alertmanager.yml detectado - recarregando alertmanager")
        elif '/etc/prometheus/' in file_path:
            # Qualquer arquivo em /etc/prometheus/: reload prometheus
            services_to_reload = ['prometheus']
            logger.info(f"[RELOAD] Arquivo do Prometheus detectado - recarregando prometheus")
        else:
            # Fallback: reload prometheus
            services_to_reload = ['prometheus']
            logger.warning(f"[RELOAD] Tipo de arquivo desconhecido, usando fallback (reload prometheus)")

        # IMPORTANTE: Filtrar serviços que realmente existem no servidor
        # Isso evita erros quando, por exemplo, o servidor tem apenas blackbox sem prometheus
        services_that_exist = []
        reload_results = []

        logger.info(f"[RELOAD] Verificando quais serviços existem no servidor...")

        for service_name in services_to_reload:
            # Verificar se o serviço existe usando systemctl list-unit-files
            check_cmd = f"systemctl list-unit-files {service_name}.service 2>/dev/null | grep -q '{service_name}.service'"
            stdin, stdout, stderr = client.exec_command(check_cmd)
            exit_code = stdout.channel.recv_exit_status()

            if exit_code == 0:
                logger.info(f"[RELOAD] ✓ Serviço {service_name} existe no servidor")
                services_that_exist.append(service_name)
            else:
                logger.warning(f"[RELOAD] ⚠ Serviço {service_name} NÃO existe no servidor - será ignorado")
                # Adicionar resultado indicando que foi ignorado
                reload_results.append({
                    "service": service_name,
                    "success": True,
                    "method": "skipped",
                    "status": "not_installed",
                    "message": f"Serviço {service_name} não está instalado neste servidor"
                })

        if not services_that_exist:
            logger.warning(f"[RELOAD] ⚠ Nenhum serviço para recarregar encontrado no servidor!")
            return {
                "success": True,
                "message": "Nenhum serviço encontrado para recarregar neste servidor",
                "services": reload_results,
                "file_path": file_path
            }

        logger.info(f"[RELOAD] Serviços a serem recarregados: {', '.join(services_that_exist)}")

        # Executar reload apenas para serviços que existem
        all_success = True

        for service_name in services_that_exist:
            try:
                # PASSO 1: Verificar se o serviço está ativo ANTES de tentar reload
                status_check_cmd = f"systemctl is-active {service_name}"
                logger.info(f"[RELOAD] Verificando status de {service_name}...")

                stdin, stdout, stderr = client.exec_command(status_check_cmd)
                current_status = stdout.read().decode('utf-8').strip()

                logger.info(f"[RELOAD] Status atual de {service_name}: {current_status}")

                # PASSO 2: Decidir ação baseada no status
                if current_status == 'active':
                    # Serviço está rodando - usar RELOAD (sem downtime)
                    reload_cmd = f"systemctl reload {service_name}"
                    logger.info(f"[RELOAD] Serviço ativo - executando reload: {reload_cmd}")

                    stdin, stdout, stderr = client.exec_command(reload_cmd)
                    exit_code = stdout.channel.recv_exit_status()

                    if exit_code != 0:
                        # Reload falhou, tentar restart como fallback
                        error_msg = stderr.read().decode('utf-8')
                        logger.warning(f"[RELOAD] Reload falhou para {service_name}, tentando restart: {error_msg}")

                        restart_cmd = f"systemctl restart {service_name}"
                        stdin, stdout, stderr = client.exec_command(restart_cmd)
                        exit_code = stdout.channel.recv_exit_status()

                        if exit_code != 0:
                            error = stderr.read().decode('utf-8')
                            logger.error(f"[RELOAD] Restart também falhou para {service_name}: {error}")
                            reload_results.append({
                                "service": service_name,
                                "success": False,
                                "method": "restart",
                                "error": error,
                                "status": "failed"
                            })
                            all_success = False
                            continue
                        else:
                            method = "restart (fallback)"
                    else:
                        method = "reload"

                elif current_status in ['inactive', 'failed', 'unknown']:
                    # Serviço está parado - usar START
                    start_cmd = f"systemctl start {service_name}"
                    logger.warning(f"[RELOAD] Serviço está {current_status} - executando start: {start_cmd}")

                    stdin, stdout, stderr = client.exec_command(start_cmd)
                    exit_code = stdout.channel.recv_exit_status()

                    if exit_code != 0:
                        error = stderr.read().decode('utf-8')
                        logger.error(f"[RELOAD] Start falhou para {service_name}: {error}")
                        reload_results.append({
                            "service": service_name,
                            "success": False,
                            "method": "start",
                            "error": error,
                            "status": current_status
                        })
                        all_success = False
                        continue
                    else:
                        method = "start"

                else:
                    # Status desconhecido - tentar restart como segurança
                    restart_cmd = f"systemctl restart {service_name}"
                    logger.warning(f"[RELOAD] Status desconhecido ({current_status}) - executando restart: {restart_cmd}")

                    stdin, stdout, stderr = client.exec_command(restart_cmd)
                    exit_code = stdout.channel.recv_exit_status()

                    if exit_code != 0:
                        error = stderr.read().decode('utf-8')
                        logger.error(f"[RELOAD] Restart falhou para {service_name}: {error}")
                        reload_results.append({
                            "service": service_name,
                            "success": False,
                            "method": "restart",
                            "error": error,
                            "status": current_status
                        })
                        all_success = False
                        continue
                    else:
                        method = "restart"

                # PASSO 3: Verificar status final do serviço
                status_cmd = f"systemctl is-active {service_name}"
                stdin, stdout, stderr = client.exec_command(status_cmd)
                final_status = stdout.read().decode('utf-8').strip()

                logger.info(f"[RELOAD] ✅ Serviço {service_name} processado via {method}. Status final: {final_status}")

                reload_results.append({
                    "service": service_name,
                    "success": True,
                    "method": method,
                    "status": final_status,
                    "previous_status": current_status
                })

            except Exception as svc_error:
                logger.error(f"[RELOAD] Erro ao recarregar {service_name}: {svc_error}")
                reload_results.append({
                    "service": service_name,
                    "success": False,
                    "error": str(svc_error),
                    "status": "error"
                })
                all_success = False

        # Construir mensagem de resposta
        if all_success:
            services_str = ", ".join([r["service"] for r in reload_results])
            message = f"Serviço(s) {services_str} recarregado(s) com sucesso no host {host_str}"
        else:
            failed = [r["service"] for r in reload_results if not r["success"]]
            message = f"Falha ao recarregar alguns serviços: {', '.join(failed)}"

        return {
            "success": all_success,
            "message": message,
            "services": reload_results,
            "file_path": file_path
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[RELOAD] Erro inesperado: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao recarregar serviço: {str(e)}"
        )


@router.put("/file/jobs")
async def update_file_jobs(
    file_path: str = Query(..., description="Path do arquivo"),
    jobs: List[Dict[str, Any]] = Body(..., description="Lista completa de jobs")
):
    """
    Atualiza a lista completa de jobs em um arquivo

    IMPORTANTE: Para arquivos Prometheus, valida com promtool antes de salvar

    Args:
        file_path: Path completo do arquivo
        jobs: Nova lista de jobs/scrape_configs

    Returns:
        Confirmação de sucesso
    """
    try:
        print(f"[UPDATE JOBS] file_path: {file_path}")
        print(f"[UPDATE JOBS] Recebidos {len(jobs)} jobs")

        # Para arquivos prometheus, validar com promtool antes de salvar
        config_file = multi_config.get_file_by_path(file_path)
        print(f"[UPDATE JOBS] config_file encontrado: {config_file is not None}")

        if config_file and config_file.service == 'prometheus':
            print(f"[UPDATE JOBS] Validando arquivo prometheus...")

            # Ler configuração atual para preservar outras seções
            config = multi_config.read_config_file(config_file)
            print(f"[UPDATE JOBS] Configuração lida - chaves: {list(config.keys())}")

            # IMPORTANTE: Atualizar scrape_configs preservando estrutura ruamel.yaml
            config['scrape_configs'] = jobs
            print(f"[UPDATE JOBS] scrape_configs atualizado com {len(jobs)} jobs")

            # Converter para YAML para validar
            from io import StringIO
            from core.yaml_config_service import YamlConfigService
            yaml_service = YamlConfigService()

            # IMPORTANTE: Para validação, criar nova instância YAML sem rule_files
            # NÃO usar .copy() pois destrói metadados do ruamel.yaml!
            from ruamel.yaml import YAML
            validation_yaml = YAML()
            validation_yaml.preserve_quotes = True
            validation_yaml.default_flow_style = False

            # Criar config temporário apenas para validação
            temp_config = {
                'global': config.get('global', {}),
                'alerting': config.get('alerting', {}),
                'scrape_configs': config['scrape_configs'],
                'rule_files': []  # Vazio para validação
            }

            output = StringIO()
            validation_yaml.dump(temp_config, output)
            yaml_content = output.getvalue()
            print(f"[UPDATE JOBS] YAML gerado para validação - tamanho: {len(yaml_content)} bytes")

            # Validar com promtool
            print(f"[UPDATE JOBS] Validando com promtool...")
            validation_result = multi_config.validate_prometheus_config(file_path, yaml_content)
            print(f"[UPDATE JOBS] Validação: success={validation_result.get('success')}")

            if not validation_result['success']:
                # Retornar erro de validação
                print(f"[UPDATE JOBS] ERRO DE VALIDAÇÃO: {validation_result.get('errors')}")
                raise HTTPException(
                    status_code=400,
                    detail={
                        "message": "Validação do promtool falhou",
                        "validation_errors": validation_result['errors'],
                        "output": validation_result.get('output', '')
                    }
                )

        # Se validação passou ou não é prometheus, salvar
        success = multi_config.update_jobs_in_file(file_path, jobs)

        return {
            "success": success,
            "message": f"Jobs atualizados em {file_path}",
            "total": len(jobs)
        }

    except HTTPException:
        raise
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Erro ao atualizar jobs: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/file/save")
async def save_file_content(
    file_path: str = Query(..., description="Path do arquivo"),
    content: str = Body(..., description="Conteúdo completo do arquivo")
):
    """
    Salva conteúdo completo em um arquivo

    Args:
        file_path: Path completo do arquivo
        content: Conteúdo YAML completo

    Returns:
        Confirmação de sucesso
    """
    try:
        success = multi_config.save_file_content(file_path, content)

        return {
            "success": success,
            "message": f"Arquivo salvo: {file_path}"
        }

    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Erro ao salvar arquivo: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/clear-cache")
async def clear_cache():
    """
    Limpa o cache de configurações do backend

    Use este endpoint quando precisar forçar a releitura dos arquivos
    """
    try:
        multi_config.clear_cache()
        return {
            "success": True,
            "message": "Cache limpo com sucesso"
        }
    except Exception as e:
        logger.error(f"Erro ao limpar cache: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/file/validate")
async def validate_prometheus_config(
    file_path: str = Query(..., description="Path do arquivo"),
    content: str = Body(..., description="Conteúdo YAML a validar")
):
    """
    Valida configuração do Prometheus usando promtool

    Args:
        file_path: Path completo do arquivo (usado para identificar o host)
        content: Conteúdo YAML a ser validado

    Returns:
        Resultado da validação com success, message, errors
    """
    try:
        result = multi_config.validate_prometheus_config(file_path, content)

        if not result['success']:
            # Retornar 400 para erro de validação
            raise HTTPException(
                status_code=400,
                detail={
                    "message": result['message'],
                    "errors": result['errors'],
                    "output": result.get('output', '')
                }
            )

        return {
            "success": True,
            "message": result['message'],
            "output": result.get('output', '')
        }

    except HTTPException:
        raise
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Erro ao validar configuração: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# ENDPOINTS - ALERTMANAGER
# ============================================================================

class AlertmanagerRoute(BaseModel):
    """Modelo para rota do Alertmanager"""
    match: Optional[Dict[str, str]] = None
    match_re: Optional[Dict[str, str]] = None
    receiver: str
    group_by: List[str] = []
    group_wait: Optional[str] = None
    group_interval: Optional[str] = None
    repeat_interval: Optional[str] = None
    continue_route: bool = False
    routes: List[Dict[str, Any]] = []


class AlertmanagerReceiver(BaseModel):
    """Modelo para receptor do Alertmanager"""
    name: str
    webhook_configs: List[Dict[str, Any]] = []
    email_configs: List[Dict[str, Any]] = []
    telegram_configs: List[Dict[str, Any]] = []
    slack_configs: List[Dict[str, Any]] = []


class AlertmanagerInhibitRule(BaseModel):
    """Modelo para regra de inibição"""
    source_match: Optional[Dict[str, str]] = None
    source_match_re: Optional[Dict[str, str]] = None
    target_match: Optional[Dict[str, str]] = None
    target_match_re: Optional[Dict[str, str]] = None
    equal: List[str] = []


def _parse_alertmanager_routes(config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Extrai rotas do alertmanager config

    Args:
        config: Dicionário com configuração completa do alertmanager

    Returns:
        Lista de rotas processadas para exibição
    """
    routes = []

    # Obter rota raiz
    root_route = config.get('route', {})

    # Processar sub-rotas
    sub_routes = root_route.get('routes', [])

    for idx, route in enumerate(sub_routes):
        # Determinar padrão de match
        match_pattern = None
        if 'match' in route:
            match_pattern = ', '.join([f"{k}: {v}" for k, v in route['match'].items()])
        elif 'match_re' in route:
            match_pattern = ', '.join([f"{k}: {v}" for k, v in route['match_re'].items()])

        routes.append({
            'index': idx,
            'match_pattern': match_pattern or 'default',
            'match_type': 'regex' if 'match_re' in route else 'exact',
            'receiver': route.get('receiver', root_route.get('receiver', 'unknown')),
            'group_by': route.get('group_by', root_route.get('group_by', [])),
            'group_wait': route.get('group_wait', root_route.get('group_wait')),
            'group_interval': route.get('group_interval', root_route.get('group_interval')),
            'repeat_interval': route.get('repeat_interval', root_route.get('repeat_interval')),
            'continue': route.get('continue', False),
            'raw': route
        })

    return routes


def _parse_alertmanager_receivers(config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Extrai receptores do alertmanager config

    Args:
        config: Dicionário com configuração completa do alertmanager

    Returns:
        Lista de receptores processados para exibição
    """
    receivers = []

    receivers_list = config.get('receivers', [])

    for idx, receiver in enumerate(receivers_list):
        name = receiver.get('name', f'receiver-{idx}')

        # Contar configurações de cada tipo
        webhook_count = len(receiver.get('webhook_configs', []))
        email_count = len(receiver.get('email_configs', []))
        telegram_count = len(receiver.get('telegram_configs', []))
        slack_count = len(receiver.get('slack_configs', []))

        # Determinar tipo principal
        types = []
        if webhook_count > 0:
            types.append(f'webhook ({webhook_count})')
        if email_count > 0:
            types.append(f'email ({email_count})')
        if telegram_count > 0:
            types.append(f'telegram ({telegram_count})')
        if slack_count > 0:
            types.append(f'slack ({slack_count})')

        # Extrair targets (URLs, emails, etc)
        targets = []
        for wh in receiver.get('webhook_configs', []):
            targets.append(wh.get('url', 'N/A'))
        for em in receiver.get('email_configs', []):
            targets.append(em.get('to', 'N/A'))

        # Extrair send_resolved e max_alerts (do primeiro webhook_config se existir)
        send_resolved = None
        max_alerts = None
        webhook_configs = receiver.get('webhook_configs', [])
        if webhook_configs and len(webhook_configs) > 0:
            first_webhook = webhook_configs[0]
            send_resolved = first_webhook.get('send_resolved', None)
            max_alerts = first_webhook.get('max_alerts', None)

        receivers.append({
            'index': idx,
            'name': name,
            'types': ', '.join(types) if types else 'none',
            'targets': targets,
            'send_resolved': send_resolved,
            'max_alerts': max_alerts,
            'webhook_configs': receiver.get('webhook_configs', []),
            'email_configs': receiver.get('email_configs', []),
            'telegram_configs': receiver.get('telegram_configs', []),
            'slack_configs': receiver.get('slack_configs', []),
            'raw': receiver
        })

    return receivers


def _parse_alertmanager_inhibit_rules(config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Extrai regras de inibição do alertmanager config

    Args:
        config: Dicionário com configuração completa do alertmanager

    Returns:
        Lista de regras processadas para exibição
    """
    rules = []

    inhibit_rules = config.get('inhibit_rules', [])

    for idx, rule in enumerate(inhibit_rules):
        # Source match
        source_pattern = None
        if 'source_match' in rule:
            source_pattern = ', '.join([f"{k}: {v}" for k, v in rule['source_match'].items()])
        elif 'source_match_re' in rule:
            source_pattern = ', '.join([f"{k}: {v}" for k, v in rule['source_match_re'].items()])

        # Target match
        target_pattern = None
        if 'target_match' in rule:
            target_pattern = ', '.join([f"{k}: {v}" for k, v in rule['target_match'].items()])
        elif 'target_match_re' in rule:
            target_pattern = ', '.join([f"{k}: {v}" for k, v in rule['target_match_re'].items()])

        rules.append({
            'index': idx,
            'source_pattern': source_pattern or 'N/A',
            'source_type': 'regex' if 'source_match_re' in rule else 'exact',
            'target_pattern': target_pattern or 'N/A',
            'target_type': 'regex' if 'target_match_re' in rule else 'exact',
            'equal': rule.get('equal', []),
            'raw': rule
        })

    return rules


@router.get("/alertmanager/routes")
async def get_alertmanager_routes(
    file_path: str = Query(..., description="Path do arquivo alertmanager.yml"),
    hostname: Optional[str] = Query(None, description="Hostname do servidor")
):
    """
    Extrai rotas (routes) do alertmanager.yml

    Args:
        file_path: Path completo do arquivo (ex: /etc/alertmanager/alertmanager.yml)
        hostname: Hostname do servidor (opcional)

    Returns:
        Lista de rotas processadas
    """
    try:
        # Ler arquivo usando método correto COM hostname para ler do servidor correto
        content = multi_config.get_file_content_raw(file_path, hostname=hostname)

        # Parsear YAML
        import yaml as pyyaml
        config = pyyaml.safe_load(content)

        # Extrair rotas
        routes = _parse_alertmanager_routes(config)

        return {
            "success": True,
            "routes": routes,
            "total": len(routes),
            "file_path": file_path
        }

    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Erro ao extrair rotas: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/alertmanager/receivers")
async def get_alertmanager_receivers(
    file_path: str = Query(..., description="Path do arquivo alertmanager.yml"),
    hostname: Optional[str] = Query(None, description="Hostname do servidor")
):
    """
    Extrai receptores (receivers) do alertmanager.yml

    Args:
        file_path: Path completo do arquivo (ex: /etc/alertmanager/alertmanager.yml)
        hostname: Hostname do servidor (opcional)

    Returns:
        Lista de receptores processados
    """
    try:
        # Ler arquivo usando método correto COM hostname para ler do servidor correto
        content = multi_config.get_file_content_raw(file_path, hostname=hostname)

        # Parsear YAML
        import yaml as pyyaml
        config = pyyaml.safe_load(content)

        # Extrair receptores
        receivers = _parse_alertmanager_receivers(config)

        return {
            "success": True,
            "receivers": receivers,
            "total": len(receivers),
            "file_path": file_path
        }

    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Erro ao extrair receptores: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/alertmanager/inhibit-rules")
async def get_alertmanager_inhibit_rules(
    file_path: str = Query(..., description="Path do arquivo alertmanager.yml"),
    hostname: Optional[str] = Query(None, description="Hostname do servidor")
):
    """
    Extrai regras de inibição (inhibit_rules) do alertmanager.yml

    Args:
        file_path: Path completo do arquivo (ex: /etc/alertmanager/alertmanager.yml)
        hostname: Hostname do servidor (opcional)

    Returns:
        Lista de regras processadas
    """
    try:
        # Ler arquivo usando método correto COM hostname para ler do servidor correto
        content = multi_config.get_file_content_raw(file_path, hostname=hostname)

        # Parsear YAML
        import yaml as pyyaml
        config = pyyaml.safe_load(content)

        # Extrair regras de inibição
        rules = _parse_alertmanager_inhibit_rules(config)

        return {
            "success": True,
            "inhibit_rules": rules,
            "total": len(rules),
            "file_path": file_path
        }

    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Erro ao extrair regras de inibição: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/job-names")
async def get_prometheus_job_names(
    hostname: Optional[str] = Query(None, description="Hostname do servidor Prometheus (opcional, usa master se não fornecido)")
):
    """
    Extrai todos os job_names configurados no prometheus.yml de um servidor específico

    Retorna apenas jobs que possuem consul_sd_configs (service discovery do Consul).
    Isso é usado no frontend para popular o dropdown de "Tipo de Serviço" ao criar exporters.

    **Performance**: Usa cache de 5 minutos para evitar SSH repetidos.

    Args:
        hostname: IP ou hostname do servidor Prometheus (ex: 172.16.1.26)
                 Se não fornecido, usa o servidor master (primeiro da lista)

    Returns:
        Lista de job_names disponíveis para aquele servidor

    Example:
        GET /api/v1/prometheus-config/job-names?hostname=172.16.1.26

        Response:
        {
            "success": true,
            "job_names": ["selfnode_exporter_rio", "blackbox_remote_rmd_ldc", ...],
            "total": 5,
            "hostname": "172.16.1.26",
            "file_path": "/etc/prometheus/prometheus.yml",
            "from_cache": false
        }
    """
    try:
        # Detectar caminho do prometheus.yml no servidor
        from core.server_utils import get_server_detector
        import time

        # Se hostname não fornecido, usar o master (primeiro servidor)
        if not hostname:
            import os
            prometheus_hosts_str = os.getenv("PROMETHEUS_CONFIG_HOSTS", "")
            if not prometheus_hosts_str:
                raise HTTPException(
                    status_code=500,
                    detail="PROMETHEUS_CONFIG_HOSTS não configurado no .env"
                )

            # Pegar primeiro host (master)
            first_host = prometheus_hosts_str.split(';')[0]
            hostname = first_host.split(':')[0]

        # VERIFICAR CACHE PRIMEIRO (TTL de 5 minutos = 300 segundos)
        cache_ttl = 300
        now = time.time()
        cache_key = hostname

        if cache_key in _job_names_cache:
            cached_entry = _job_names_cache[cache_key]
            cached_time = cached_entry.get('timestamp', 0)
            age = now - cached_time

            if age < cache_ttl:
                logger.info(f"[JOB-NAMES] ✓ Cache HIT para {hostname} (idade: {age:.1f}s)")
                result = cached_entry['data']
                result['from_cache'] = True
                return result

        logger.info(f"[JOB-NAMES] Cache MISS para {hostname}, buscando do servidor via SSH...")

        # Detectar capacidades do servidor
        detector = get_server_detector()
        server_info = detector.detect_server_capabilities(hostname, use_cache=False)

        if not server_info.has_prometheus:
            raise HTTPException(
                status_code=400,
                detail=f"Servidor {hostname} não possui Prometheus instalado. {server_info.description}"
            )

        prometheus_file_path = server_info.prometheus_config_path
        if not prometheus_file_path:
            raise HTTPException(
                status_code=500,
                detail=f"Não foi possível detectar o caminho do prometheus.yml no servidor {hostname}"
            )

        logger.info(f"[JOB-NAMES] Arquivo detectado: {prometheus_file_path}")

        # Ler conteúdo do prometheus.yml
        yaml_content = multi_config.get_file_content_raw(prometheus_file_path, hostname=hostname)

        if not yaml_content:
            raise HTTPException(
                status_code=404,
                detail=f"Arquivo prometheus.yml não encontrado ou vazio no servidor {hostname}"
            )

        # Parsear YAML
        import yaml as pyyaml
        try:
            config = pyyaml.safe_load(yaml_content)
        except pyyaml.YAMLError as e:
            raise HTTPException(
                status_code=500,
                detail=f"Erro ao parsear prometheus.yml: {str(e)}"
            )

        # Extrair job_names dos scrape_configs
        scrape_configs = config.get('scrape_configs', [])
        if not scrape_configs:
            logger.warning(f"[JOB-NAMES] Nenhum scrape_config encontrado no prometheus.yml de {hostname}")
            return {
                "success": True,
                "job_names": [],
                "total": 0,
                "hostname": hostname,
                "file_path": prometheus_file_path,
                "message": "Nenhum job configurado no prometheus.yml"
            }

        job_names = []
        jobs_with_consul_sd = []

        for job in scrape_configs:
            if not isinstance(job, dict):
                continue

            job_name = job.get('job_name')
            if not job_name:
                continue

            # Filtrar apenas jobs com consul_sd_configs (os que fazem service discovery)
            has_consul_sd = job.get('consul_sd_configs') is not None

            if has_consul_sd:
                jobs_with_consul_sd.append({
                    'job_name': job_name,
                    'has_consul_sd': True,
                    'scrape_interval': job.get('scrape_interval', 'default'),
                    'metrics_path': job.get('metrics_path', '/metrics')
                })
                job_names.append(job_name)
            else:
                logger.debug(f"[JOB-NAMES] Job '{job_name}' ignorado (sem consul_sd_configs)")

        logger.info(f"[JOB-NAMES] Encontrados {len(job_names)} jobs com consul_sd_configs em {hostname}")

        result = {
            "success": True,
            "job_names": sorted(job_names),  # Ordenar alfabeticamente
            "total": len(job_names),
            "hostname": hostname,
            "file_path": prometheus_file_path,
            "jobs_details": jobs_with_consul_sd,  # Detalhes extras (opcional para debug)
            "from_cache": False
        }

        # SALVAR NO CACHE
        _job_names_cache[cache_key] = {
            'data': result,
            'timestamp': now
        }
        logger.info(f"[JOB-NAMES] ✓ Cache atualizado para {hostname} (TTL: {cache_ttl}s)")

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[JOB-NAMES] Erro ao buscar job_names: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# ENDPOINTS - CONFIGURAÇÕES GLOBAL, REMOTE_WRITE, ALERTING
# ============================================================================

@router.get("/test-version")
async def test_version():
    """Endpoint de teste para verificar se código foi atualizado"""
    return {"version": "2.0-SSH-direct", "timestamp": datetime.now().isoformat()}


@router.get("/global")
async def get_global_config(
    hostname: Optional[str] = Query(None, description="Hostname do servidor Prometheus (opcional)")
):
    """
    Obtém configuração global do prometheus.yml de um servidor específico
    Inclui external_labels, scrape_interval, evaluation_interval

    Args:
        hostname: Hostname do servidor (ex: 172.16.1.26). Se não fornecido, usa configuração padrão.

    Returns:
        Dict com configuração global incluindo external_labels

    Example:
        GET /prometheus-config/global?hostname=172.16.1.26

        Response:
        {
            "success": true,
            "scrape_interval": "15s",
            "evaluation_interval": "15s",
            "external_labels": {
                "site": "palmas",
                "datacenter": "genesis-dtc",
                "cluster": "prometheus"
            }
        }
    """
    try:
        # Se hostname fornecido, buscar de servidor específico via SSH
        if hostname:
            logger.info(f"[GLOBAL CONFIG] Buscando configuração de {hostname} via SSH")

            # Parse PROMETHEUS_CONFIG_HOSTS do .env para encontrar credenciais do servidor
            config_hosts_str = os.getenv("PROMETHEUS_CONFIG_HOSTS", "")

            if not config_hosts_str:
                raise HTTPException(
                    status_code=500,
                    detail="PROMETHEUS_CONFIG_HOSTS não configurado no .env"
                )

            # Format: host:porta/usuario/senha;host2:porta/usuario/senha
            server_config = None
            for host_entry in config_hosts_str.split(";"):
                if hostname in host_entry:
                    parts = host_entry.split("/")
                    host_port = parts[0]
                    host_parts = host_port.split(":")
                    server_hostname = host_parts[0]
                    server_port = int(host_parts[1]) if len(host_parts) > 1 else 22
                    username = parts[1] if len(parts) > 1 else "root"
                    password = parts[2] if len(parts) > 2 else None

                    if server_hostname == hostname:
                        server_config = {
                            "hostname": server_hostname,
                            "port": server_port,
                            "username": username,
                            "password": password
                        }
                        break

            if not server_config:
                raise HTTPException(
                    status_code=404,
                    detail=f"Servidor {hostname} não encontrado em PROMETHEUS_CONFIG_HOSTS"
                )

            logger.info(f"[GLOBAL CONFIG] Conectando via SSH: {username}@{hostname}:{server_config['port']}")

            # PASSO 1: Conectar via SSH
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

            try:
                if server_config["password"]:
                    client.connect(
                        hostname=server_config["hostname"],
                        port=server_config["port"],
                        username=server_config["username"],
                        password=server_config["password"],
                        timeout=10
                    )
                else:
                    # Tentar com chave SSH
                    client.connect(
                        hostname=server_config["hostname"],
                        port=server_config["port"],
                        username=server_config["username"],
                        look_for_keys=True,
                        timeout=10
                    )

                logger.info(f"[GLOBAL CONFIG] Conectado com sucesso via SSH")

                # PASSO 2: Ler arquivo prometheus.yml
                prometheus_path = "/etc/prometheus/prometheus.yml"
                logger.info(f"[GLOBAL CONFIG] Lendo arquivo {prometheus_path}")

                sftp = client.open_sftp()
                with sftp.open(prometheus_path, 'r') as f:
                    content = f.read().decode('utf-8')
                sftp.close()
                client.close()

                logger.info(f"[GLOBAL CONFIG] Arquivo lido com sucesso ({len(content)} bytes)")

                # PASSO 3: Parsear YAML
                yaml = YAML()
                yaml.preserve_quotes = True
                config = yaml.load(StringIO(content))

                logger.info(f"[GLOBAL CONFIG] YAML parseado. Keys: {list(config.keys())}")

                # PASSO 4: Extrair seção 'global'
                global_section = config.get('global', {})

                # PASSO 5: Retornar external_labels e outras configs globais
                return {
                    "success": True,
                    "scrape_interval": global_section.get('scrape_interval', '15s'),
                    "evaluation_interval": global_section.get('evaluation_interval', '15s'),
                    "external_labels": global_section.get('external_labels', {}),
                    "hostname": hostname,
                    "file_path": prometheus_path
                }

            except paramiko.AuthenticationException as e:
                logger.error(f"[GLOBAL CONFIG] Erro de autenticação SSH: {e}")
                raise HTTPException(status_code=401, detail=f"Falha na autenticação SSH: {e}")
            except paramiko.SSHException as e:
                logger.error(f"[GLOBAL CONFIG] Erro SSH: {e}")
                raise HTTPException(status_code=500, detail=f"Erro SSH: {e}")
            except FileNotFoundError as e:
                logger.error(f"[GLOBAL CONFIG] Arquivo não encontrado: {e}")
                raise HTTPException(status_code=404, detail=f"Arquivo prometheus.yml não encontrado no servidor {hostname}")
            finally:
                try:
                    client.close()
                except:
                    pass

        # Se hostname NÃO fornecido, usar serviço padrão (YamlConfigService)
        else:
            global_config = yaml_service.get_global_config()

            return {
                "success": True,
                "data": global_config
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao obter configuração global: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/remote-write")
async def get_remote_write_config():
    """
    Obtém configuração de remote_write do prometheus.yml
    Inclui URL, write_relabel_configs, queue_config

    Returns:
        Lista de configurações remote_write
    """
    try:
        remote_write = yaml_service.get_remote_write_config()

        return {
            "success": True,
            "data": remote_write,
            "total": len(remote_write)
        }

    except Exception as e:
        logger.error(f"Erro ao obter configuração remote_write: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/alerting")
async def get_alerting_config():
    """
    Obtém configuração de alerting (alertmanagers)

    Returns:
        Dict com configuração de alertmanagers
    """
    try:
        alerting = yaml_service.get_alerting_config()

        return {
            "success": True,
            "data": alerting
        }

    except Exception as e:
        logger.error(f"Erro ao obter configuração alerting: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/rule-files")
async def get_rule_files():
    """
    Obtém lista de arquivos de regras configurados

    Returns:
        Lista de caminhos dos arquivos de regras
    """
    try:
        rule_files = yaml_service.get_rule_files()

        return {
            "success": True,
            "data": rule_files,
            "total": len(rule_files)
        }

    except Exception as e:
        logger.error(f"Erro ao obter rule_files: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/server-info")
async def get_full_server_info():
    """
    Obtém informações completas do servidor Prometheus
    Inclui global, remote_write, alerting, rule_files, jobs

    Útil para dashboard e análise completa da configuração

    Returns:
        Dict com todas as informações relevantes
    """
    try:
        server_info = yaml_service.get_full_server_info()

        return {
            "success": True,
            "data": server_info
        }

    except Exception as e:
        logger.error(f"Erro ao obter informações do servidor: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
