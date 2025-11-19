"""
API FastAPI para Consul Manager
Mantém todas as funcionalidades do script original
"""
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Response
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import asyncio
import json
from typing import Dict, List, Optional
import os
from dotenv import load_dotenv

# SPRINT 2 (2025-11-15): Prometheus metrics scraping
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

# Importações locais
from core.config import Config
from api.services import router as services_router
from api.nodes import router as nodes_router
from api.config import router as config_router
from api.blackbox import router as blackbox_router
from api.kv import router as kv_router
from api.presets import router as presets_router
from api.search import router as search_router
from api.consul_insights import router as consul_insights_router
from api.audit import router as audit_router
from api.dashboard import router as dashboard_router
from api.optimized_endpoints import router as optimized_router
from api.prometheus_config import router as prometheus_config_router
from api.metadata_fields_manager import router as metadata_fields_router
from api.cache import router as cache_router  # SPRINT 2: Cache management
# from api.metadata_dynamic import router as metadata_dynamic_router  # REMOVIDO: Usar prometheus_config em vez disso
from api.monitoring_types_dynamic import router as monitoring_types_dynamic_router  # Tipos extraídos DINAMICAMENTE de Prometheus.yml
from api.monitoring_unified import router as monitoring_unified_router  # ⭐ NOVO: API unificada para páginas dinâmicas (v2.0 2025-11-13)
from api.categorization_rules import router as categorization_rules_router  # ⭐ NOVO: CRUD de regras de categorização (v2.0 2025-11-13)
from api.reference_values import router as reference_values_router  # NOVO: Sistema de auto-cadastro/retroalimentação
from api.service_tags import router as service_tags_router  # NOVO: Sistema de tags retroalimentáveis
from api.settings import router as settings_router  # NOVO: Configurações globais (naming strategy, etc)
try:
    from api.installer import router as installer_router
    from api.health import router as health_router
    HAS_INSTALLER = True
except ImportError:
    HAS_INSTALLER = False

load_dotenv()

# ============================================
# FUNÇÕES DE PRÉ-AQUECIMENTO (PRE-WARMING)
# ============================================

# Status global do PRE-WARM (para sincronização com endpoints)
_prewarm_status = {
    'running': False,
    'completed': False,
    'failed': False,
    'error': None
}

async def _prewarm_metadata_fields_cache():
    """
    Pré-aquece o cache de campos metadata em background

    OBJETIVO:
    - Garante que o KV do Consul esteja sempre populado com campos recentes
    - Evita cold start lento na primeira requisição após reiniciar o backend
    - Roda em background para não bloquear o startup da aplicação

    FLUXO:
    1. Aguarda 5 segundos para o servidor terminar de inicializar
    2. Extrai campos de TODOS os servidores Prometheus via SSH
    3. Salva automaticamente no Consul KV (skills/eye/metadata/fields)
    4. Campos ficam disponíveis instantaneamente para requisições HTTP

    PERFORMANCE:
    - Tempo estimado: 20-30 segundos (SSH para 3 servidores)
    - Não bloqueia startup (roda em background via asyncio.create_task)
    - Primeira requisição HTTP após startup será rápida (~2s lendo do KV)

    TRATAMENTO DE ERROS:
    - Erros são logados mas NÃO quebram a aplicação
    - Se falhar, requisições HTTP farão extração sob demanda (fallback)

    BEST PRACTICES (baseado em pesquisa web 2025):
    - Keep startup quick (<3s): ✅ Usa background task
    - Wrap em try-except: ✅ Implementado
    - Log errors without crashing: ✅ Implementado
    """
    global _prewarm_status
    _prewarm_status['running'] = True

    try:
        # PASSO 1: Aguardar servidor terminar de inicializar (REDUZIDO PARA 1s)
        # Garante que todos os módulos estejam carregados antes de usar
        print("[PRE-WARM] Aguardando 1s para servidor inicializar completamente...")
        await asyncio.sleep(1)

        # PASSO 2: Importar dependências (após startup completo)
        from api.prometheus_config import multi_config
        from core.kv_manager import KVManager
        from datetime import datetime
        import logging

        logger = logging.getLogger(__name__)
        logger.info("[PRE-WARM P2] Iniciando extração ULTRA RÁPIDA com AsyncSSH + TAR...")

        # PASSO 3: Extrair campos via AsyncSSH + TAR (P2 - ULTRA RÁPIDO!)
        # Tempo estimado P0: 20-30 segundos
        # Tempo estimado P1: 15 segundos
        # Tempo estimado P2: 2-3 segundos ← GANHO MASSIVO!
        extraction_result = await multi_config.extract_all_fields_with_asyncssh_tar()

        fields = extraction_result['fields']
        successful_servers = extraction_result.get('successful_servers', 0)
        total_servers = extraction_result.get('total_servers', 0)

        logger.info(
            f"[PRE-WARM P2] ✓ Extração ULTRA RÁPIDA completa: {len(fields)} campos de "
            f"{successful_servers}/{total_servers} servidores"
        )

        # PASSO 4: VERIFICAR SE KV JÁ TEM CAMPOS (ou restaurar do backup)
        kv_manager = KVManager()
        existing_config = await kv_manager.get_json('skills/eye/metadata/fields')
        
        # ✅ NOVO: Se KV está vazio, tentar restaurar do backup
        if not existing_config or not existing_config.get('fields'):
            logger.info("[PRE-WARM] ⚠️ KV vazio - tentando restaurar do backup...")
            from core.metadata_fields_backup import get_backup_manager
            backup_manager = get_backup_manager()
            restored_data = await backup_manager.restore_from_backup()
            
            if restored_data:
                logger.info("[PRE-WARM] ✅ Dados restaurados do backup - usando dados restaurados")
                existing_config = restored_data
            else:
                logger.info("[PRE-WARM] ℹ️ Nenhum backup disponível - continuando com extração...")

        # LÓGICA CORRETA: EXTRAIR ≠ SINCRONIZAR
        # - Se KV VAZIO (primeira vez): Popular KV com campos extraídos
        # - Se KV JÁ TEM CAMPOS: NÃO adicionar campos novos automaticamente
        #   (campos novos devem ser adicionados via "Sincronizar Campos" no frontend)

        if existing_config and 'fields' in existing_config and len(existing_config['fields']) > 0:
            # KV JÁ TEM CAMPOS: FAZER MERGE para preservar customizações e atualizar estrutura
            logger.info(
                f"[PRE-WARM] ✓ KV já possui {len(existing_config['fields'])} campos. "
                f"Fazendo merge para preservar customizações e atualizar extraction_status..."
            )
            logger.info(
                f"[PRE-WARM] ℹ️ {len(fields)} campos extraídos do Prometheus. "
                f"Novos campos devem ser adicionados via 'Sincronizar Campos' no frontend."
            )
            
            # ✅ CORREÇÃO CRÍTICA: Fazer merge antes de salvar para preservar customizações
            # Isso evita race conditions e garante que customizações não sejam perdidas
            from api.metadata_fields_manager import merge_fields_preserving_customizations
            from core.metadata_fields_backup import get_backup_manager
            
            # Converter campos extraídos para dict
            extracted_fields_dicts = [f.to_dict() for f in fields]
            
            # Fazer merge preservando customizações do KV
            merged_fields = merge_fields_preserving_customizations(
                extracted_fields=extracted_fields_dicts,
                existing_kv_fields=existing_config['fields']
            )
            
            logger.info(
                f"[PRE-WARM MERGE] ✓ Merge concluído: {len(merged_fields)} campos finais "
                f"(preservou {len(existing_config['fields'])} customizações existentes)"
            )
            
            # Atualizar extraction_status
            existing_config['extraction_status'] = {
                'total_servers': total_servers,
                'successful_servers': successful_servers,
                'server_status': extraction_result.get('server_status', []),
                'extraction_complete': True,
                'extracted_at': datetime.now().isoformat(),
            }
            existing_config['last_updated'] = datetime.now().isoformat()
            existing_config['source'] = 'prewarm_update_with_merge'
            existing_config['fields'] = merged_fields  # ✅ Usar campos merged (não sobrescrever!)
            
            # ✅ NOVO: Criar backup antes de salvar
            backup_manager = get_backup_manager()
            backup_success = await backup_manager.create_backup(existing_config)
            if not backup_success:
                logger.warning("[PRE-WARM] ⚠️ Falha ao criar backup, mas continuando...")
            
            # Salvar campos merged no KV (preserva customizações + atualiza estrutura)
            await kv_manager.put_json(
                key='skills/eye/metadata/fields',
                value=existing_config,
                metadata={'auto_updated': True, 'source': 'prewarm_update_with_merge'}
            )
            
            # ✅ CORREÇÃO: Invalidar cache para garantir que mudanças apareçam imediatamente
            from core.consul_kv_config_manager import ConsulKVConfigManager
            _kv_manager = ConsulKVConfigManager()
            _kv_manager.invalidate('metadata/fields')
            logger.info(f"[PRE-WARM] ✓ Cache invalidado após merge")
            
            print(f"[PRE-WARM] ✓ Merge concluído e extraction_status atualizado com dados de {successful_servers}/{total_servers} servidores")
            # Marcar como concluído
            _prewarm_status['completed'] = True
            _prewarm_status['running'] = False
            return

        # KV VAZIO: POPULAR PELA PRIMEIRA VEZ
        logger.info("[PRE-WARM] 🆕 KV vazio detectado - primeira população")
        print("[PRE-WARM] 🆕 KV vazio - populando pela primeira vez...")

        # Converter MetadataField objects para dict
        fields_dicts = [f.to_dict() for f in fields]

        # Salvar campos extraídos no KV (APENAS PRIMEIRA VEZ)
        await kv_manager.put_json(
            key='skills/eye/metadata/fields',
            value={
                'version': '2.0.0',
                'last_updated': datetime.now().isoformat(),
                'source': 'prewarm_startup_initial',
                'total_fields': len(fields_dicts),
                'fields': fields_dicts,
                'extraction_status': {
                    'total_servers': total_servers,
                    'successful_servers': successful_servers,
                    'server_status': extraction_result.get('server_status', []),
                },
            },
            metadata={'auto_updated': True, 'source': 'startup_prewarm_initial'}
        )

        logger.info(
            f"[PRE-WARM] ✓ KV populado pela PRIMEIRA VEZ com {len(fields_dicts)} campos extraídos do Prometheus"
        )
        print(f"[PRE-WARM] ✓ SUCESSO: {len(fields_dicts)} campos adicionados ao KV (primeira população)")

        # Marcar como concluído com sucesso
        _prewarm_status['completed'] = True
        _prewarm_status['running'] = False

    except asyncio.TimeoutError:
        # Timeout: PRE-WARM demorou muito (>60s)
        _prewarm_status['failed'] = True
        _prewarm_status['running'] = False
        _prewarm_status['error'] = "Timeout ao conectar servidores Prometheus (>60s)"
        import logging
        logger = logging.getLogger(__name__)
        logger.error("[PRE-WARM] ✗ TIMEOUT: PRE-WARM demorou mais de 60s")
        print(f"[PRE-WARM] ✗ TIMEOUT: {_prewarm_status['error']}")
        print("[PRE-WARM] Aplicação continuará funcionando. Tente sincronizar manualmente.")

    except Exception as e:
        # IMPORTANTE: NÃO deixar erro quebrar a aplicação
        # Se falhar, requisições HTTP farão extração sob demanda
        _prewarm_status['failed'] = True
        _prewarm_status['running'] = False
        _prewarm_status['error'] = str(e)
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"[PRE-WARM] ✗ Erro ao pré-aquecer cache: {e}", exc_info=True)
        print(f"[PRE-WARM] ✗ ERRO: {e}")
        print("[PRE-WARM] Aplicação continuará funcionando. Cache será populado na primeira requisição.")

async def _prewarm_monitoring_types_cache():
    """
    Pré-aquece o cache de monitoring-types em background
    
    OBJETIVO:
    - Garante que o KV do Consul esteja sempre populado com tipos recentes
    - Evita cold start lento na primeira requisição após reiniciar o backend
    - Roda em background para não bloquear o startup da aplicação
    
    FLUXO:
    1. Aguarda 2 segundos para o servidor terminar de inicializar
    2. Extrai tipos de TODOS os servidores Prometheus via SSH
    3. Salva automaticamente no Consul KV (skills/eye/monitoring-types)
    4. Tipos ficam disponíveis instantaneamente para requisições HTTP
    
    ⚠️ DIFERENÇA vs metadata-fields:
    - Sempre sobrescreve tipos do Prometheus (extração)
    - ✅ PRECISA backup (form_schema É editável manualmente!)
    - Merge de form_schema: preserva customizações
    
    PERFORMANCE:
    - Tempo estimado: 10-20 segundos (SSH para 3 servidores)
    - Não bloqueia startup (roda em background via asyncio.create_task)
    - Primeira requisição HTTP após startup será rápida (~2s lendo do KV)
    
    TRATAMENTO DE ERROS:
    - Erros são logados mas NÃO quebram a aplicação
    - Se falhar, requisições HTTP farão extração sob demanda (fallback)
    """
    try:
        # PASSO 1: Aguardar servidor terminar de inicializar
        print("[PRE-WARM MONITORING-TYPES] Aguardando 2s para servidor inicializar completamente...")
        await asyncio.sleep(2)
        
        # PASSO 2: Importar dependências (após startup completo)
        from api.monitoring_types_dynamic import _extract_types_from_all_servers
        from core.kv_manager import KVManager
        from core.monitoring_types_backup import get_backup_manager
        from datetime import datetime
        import logging

        logger = logging.getLogger(__name__)
        logger.info("[PRE-WARM MONITORING-TYPES] Iniciando prewarm de monitoring-types...")

        # PASSO 2.5: ✅ Verificar se há backup para restaurar (se KV vazio)
        backup_manager = get_backup_manager()
        kv_manager = KVManager()

        # Tentar restaurar backup se KV estiver vazio
        existing_kv = await kv_manager.get_json('skills/eye/monitoring-types')
        if not existing_kv or not existing_kv.get('data', {}).get('all_types'):
            logger.info("[PRE-WARM MONITORING-TYPES] KV vazio - tentando restaurar backup...")
            restored = await backup_manager.restore_from_backup()
            if restored:
                logger.info("[PRE-WARM MONITORING-TYPES] ✅ Backup restaurado com sucesso!")
            else:
                logger.info("[PRE-WARM MONITORING-TYPES] Sem backup - continuando extração normal...")
        
        # PASSO 3: Extrair tipos de TODOS os servidores
        result = await _extract_types_from_all_servers(server=None)

        # PASSO 3.5: ✅ MERGE de form_schema (preservar customizações manuais)
        # Se tipo já existia com form_schema customizado, PRESERVAR
        existing_kv = await kv_manager.get_json('skills/eye/monitoring-types')
        existing_form_schemas = {}
        if existing_kv and existing_kv.get('data', {}).get('all_types'):
            for existing_type in existing_kv['data']['all_types']:
                if existing_type.get('form_schema'):
                    existing_form_schemas[existing_type['id']] = existing_type['form_schema']

        # PASSO 4: Salvar no KV (sempre sobrescreve - não precisa verificar existência)
        # ⚠️ CRÍTICO: Remover 'fields' de todos os tipos antes de salvar
        # 'fields' são apenas para display e não devem ser salvos no KV
        # A fonte de verdade para campos metadata é metadata-fields KV
        # ✅ PRESERVAR form_schema customizado (merge)
        all_types_without_fields = []
        for type_def in result['all_types']:
            type_def_clean = {k: v for k, v in type_def.items() if k != 'fields'}

            # ✅ MERGE: Se tipo tinha form_schema customizado, PRESERVAR
            if type_def['id'] in existing_form_schemas:
                type_def_clean['form_schema'] = existing_form_schemas[type_def['id']]
                logger.debug(f"[PRE-WARM] Preservando form_schema customizado: {type_def['id']}")

            all_types_without_fields.append(type_def_clean)
        
        # Limpar 'fields' também dos tipos dentro de 'servers' + merge form_schema
        servers_clean = {}
        for server_host, server_data in result['servers'].items():
            if 'types' in server_data:
                types_with_merge = []
                for t in server_data['types']:
                    t_clean = {k: v for k, v in t.items() if k != 'fields'}
                    # ✅ MERGE: Preservar form_schema
                    if t['id'] in existing_form_schemas:
                        t_clean['form_schema'] = existing_form_schemas[t['id']]
                    types_with_merge.append(t_clean)

                servers_clean[server_host] = {
                    **server_data,
                    'types': types_with_merge
                }
            else:
                servers_clean[server_host] = server_data

        # Limpar 'fields' também dos tipos dentro de 'categories' + merge form_schema
        categories_clean = []
        for category in result['categories']:
            types_with_merge = []
            for t in category.get('types', []):
                t_clean = {k: v for k, v in t.items() if k != 'fields'}
                # ✅ MERGE: Preservar form_schema
                if t['id'] in existing_form_schemas:
                    t_clean['form_schema'] = existing_form_schemas[t['id']]
                types_with_merge.append(t_clean)

            categories_clean.append({
                **category,
                'types': types_with_merge
            })
        
        kv_value = {
            'version': '1.0.0',
            'last_updated': datetime.now().isoformat(),
            'source': 'prewarm_startup',
            'total_types': result['total_types'],
            'total_servers': result['total_servers'],
            'successful_servers': result['successful_servers'],
            'servers': servers_clean,
            'all_types': all_types_without_fields,
            'categories': categories_clean,
            'server_status': result['server_status']
        }

        # PASSO 4.5: ✅ CRIAR BACKUP antes de salvar (preservar form_schemas customizados)
        logger.info("[PRE-WARM MONITORING-TYPES] Criando backup antes de salvar...")
        backup_success = await backup_manager.create_backup({'data': kv_value})
        if backup_success:
            logger.info("[PRE-WARM MONITORING-TYPES] ✅ Backup criado com sucesso")
        else:
            logger.warning("[PRE-WARM MONITORING-TYPES] ⚠️ Falha ao criar backup (continuando salvamento)")

        # PASSO 5: Salvar no KV
        # 🐛 BUGFIX: NÃO envolver em {'data': ...} porque KVManager já retorna essa estrutura
        #            ao ler. O kv_value já é o conteúdo completo para salvar.
        await kv_manager.put_json(
            key='skills/eye/monitoring-types',
            value=kv_value,  # ✅ CORRETO: Apenas kv_value, sem wrapper adicional
            metadata={'auto_updated': True, 'source': 'prewarm_startup'}
        )
        
        logger.info(
            f"[PRE-WARM MONITORING-TYPES] ✅ Monitoring-types cache populado: "
            f"{result['total_types']} tipos de {result['successful_servers']}/{result['total_servers']} servidores"
        )
        print(
            f"[PRE-WARM MONITORING-TYPES] ✅ SUCESSO: {result['total_types']} tipos adicionados ao KV "
            f"({result['successful_servers']}/{result['total_servers']} servidores OK)"
        )
        
    except asyncio.TimeoutError:
        import logging
        logger = logging.getLogger(__name__)
        logger.error("[PRE-WARM MONITORING-TYPES] ✗ TIMEOUT: PRE-WARM demorou mais de 60s")
        print("[PRE-WARM MONITORING-TYPES] ✗ TIMEOUT: PRE-WARM demorou mais de 60s")
        print("[PRE-WARM MONITORING-TYPES] Aplicação continuará funcionando. Tente atualizar manualmente.")
        
    except Exception as e:
        # IMPORTANTE: NÃO deixar erro quebrar a aplicação
        # Se falhar, requisições HTTP farão extração sob demanda
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"[PRE-WARM MONITORING-TYPES] ✗ Erro ao pré-aquecer cache: {e}", exc_info=True)
        print(f"[PRE-WARM MONITORING-TYPES] ✗ ERRO: {e}")
        print("[PRE-WARM MONITORING-TYPES] Aplicação continuará funcionando. Cache será populado na primeira requisição.")


async def _prewarm_with_timeout():
    """
    Wrapper para adicionar timeout de 60s ao PRE-WARM

    IMPORTANTE: Timeout de 60s para evitar que a aplicação trave
    se algum servidor Prometheus estiver inacessível na inicialização.
    
    Executa prewarm de metadata-fields e monitoring-types em paralelo.
    """
    try:
        # Executar ambos os prewarms em paralelo
        await asyncio.wait_for(
            asyncio.gather(
                _prewarm_metadata_fields_cache(),
                _prewarm_monitoring_types_cache(),
                return_exceptions=True  # Não falhar se um falhar
            ),
            timeout=60.0
        )
    except asyncio.TimeoutError:
        # Timeout já é tratado dentro das funções individuais
        # mas garantimos aqui também caso a função não trate
        import logging
        logger = logging.getLogger(__name__)
        logger.error("[PRE-WARM-WRAPPER] Timeout de 60s excedido (wrapper)")
        print("[PRE-WARM-WRAPPER] ✗ TIMEOUT de 60s excedido")

# ============================================
# CONFIGURAÇÃO DO LIFECYCLE
# ============================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Gerencia o ciclo de vida da aplicação FastAPI

    STARTUP:
    - Inicializa sistema de auditoria com eventos de exemplo
    - Auto-migração de regras de categorização (se KV vazio)
    - Pré-aquece cache de campos metadata (background task)

    SHUTDOWN:
    - Finaliza recursos (futuro: fechar conexões, etc)
    """
    # ============================================
    # STARTUP - Inicialização da Aplicação
    # ============================================
    print(">> Iniciando Consul Manager API...")

    # PASSO 1: Inicializar sistema de auditoria com eventos de exemplo
    from core.audit_manager import audit_manager
    from datetime import datetime, timedelta

    # Adicionar eventos de exemplo para demonstração
    base_time = datetime.utcnow()

    # Eventos dos últimos 7 dias
    for i in range(20):
        days_ago = i // 3
        event_time = (base_time - timedelta(days=days_ago)).isoformat() + "Z"

        if i % 3 == 0:
            event = audit_manager.log_event(
                action="create",
                resource_type="service",
                resource_id=f"blackbox_exporter_{i}",
                user="admin",
                details=f"Criado serviço de monitoramento {i}",
                metadata={"module": "blackbox", "env": "prod"}
            )
            event["timestamp"] = event_time
        elif i % 3 == 1:
            event = audit_manager.log_event(
                action="update",
                resource_type="kv",
                resource_id=f"config/service_{i}",
                user="operator",
                details=f"Atualizada configuração do serviço {i}",
                metadata={"key": f"config/service_{i}"}
            )
            event["timestamp"] = event_time
        else:
            event = audit_manager.log_event(
                action="delete",
                resource_type="blackbox_target",
                resource_id=f"target_{i}",
                user="system",
                details=f"Removido target de monitoramento {i}",
                metadata={"reason": "deprecated"}
            )
            event["timestamp"] = event_time

    print(f">> Sistema de auditoria inicializado com {len(audit_manager.events)} eventos de exemplo")

    # PASSO 2: Auto-migração de regras de categorização
    # Popula KV com regras padrão se não existirem (40+ regras)
    from migrate_categorization_to_json import run_migration as migrate_categorization
    migration_success = await migrate_categorization(force=False)
    if migration_success:
        print(">> Regras de categorização disponíveis no KV (auto-migração OK)")
    else:
        print(">> ⚠️  AVISO: Falha na auto-migração de regras de categorização")

    # PASSO 3: Pré-aquecer cache de campos metadata (BACKGROUND TASK)
    # IMPORTANTE: Roda em background para não bloquear o startup
    # Best Practice: Manter startup rápido (<3s), jobs longos vão para background
    # Timeout de 60s para evitar que servidores inacessíveis travem a aplicação
    asyncio.create_task(_prewarm_with_timeout())
    print(">> Background task de pré-aquecimento do cache iniciado (timeout: 60s)")

    yield

    # ============================================
    # SHUTDOWN - Finalização da Aplicação
    # ============================================
    print(">> Desligando Consul Manager API...")

# Criar aplicação FastAPI
app = FastAPI(
    title="Consul Manager API",
    description="API para gerenciamento do Consul e serviços de monitoramento",
    version="2.2.0",
    lifespan=lifespan
)

# Configurar CORS - Permitir qualquer origem em desenvolvimento
# CORS flexível para permitir acesso de qualquer servidor/IP durante desenvolvimento
cors_allow_all = os.getenv("CORS_ALLOW_ALL", "true").lower() == "true"

if cors_allow_all:
    # Desenvolvimento: Aceitar requisições de qualquer origem
    app.add_middleware(
        CORSMiddleware,
        allow_origin_regex=r"http://.*",  # Aceita qualquer http://IP:PORTA
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    print(">> CORS configurado para aceitar QUALQUER origem (modo desenvolvimento)")
else:
    # Produção: Lista restrita de origens permitidas
    allowed_origins = [
        "http://localhost:3000",
        "http://localhost:3001",
        "http://localhost:8081",
        "http://localhost:8082",
        "http://localhost:8083",
        "http://localhost:8084",
        f"http://{Config.MAIN_SERVER}:3001",
        f"http://{Config.MAIN_SERVER}:8081",
    ]
    
    # Adicionar origens extras do .env se definidas
    env_origins = os.getenv("CORS_ORIGINS", "")
    if env_origins:
        import json
        try:
            extra_origins = json.loads(env_origins)
            allowed_origins.extend(extra_origins)
        except:
            pass
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    print(f">> CORS configurado com {len(allowed_origins)} origens permitidas (modo produção)")

# Importar WebSocket manager
from core.websocket_manager import ws_manager

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, client_id: str = "default"):
    """WebSocket genérico para logs"""
    await ws_manager.connect(websocket, client_id)
    try:
        while True:
            data = await websocket.receive_text()
            # Echo ou processar comandos via WebSocket
            await ws_manager.send_log(f"Echo: {data}", "info", client_id)
    except WebSocketDisconnect:
        await ws_manager.disconnect(websocket, client_id)

@app.websocket("/ws/installer/{installation_id}")
async def installer_websocket(websocket: WebSocket, installation_id: str):
    """WebSocket para logs de instalação em tempo real"""
    await ws_manager.connect(websocket, installation_id)
    try:
        # Manter conexão aberta para receber logs
        while True:
            # Aguardar mensagens (ping/pong para manter conexão viva)
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=1.0)
                if data == "ping":
                    await websocket.send_text("pong")
            except asyncio.TimeoutError:
                # Timeout normal, continuar loop
                pass
    except WebSocketDisconnect:
        await ws_manager.disconnect(websocket, installation_id)

# Rotas principais
@app.get("/")
async def root():
    return {
        "name": "Consul Manager API",
        "version": "2.2.0",
        "status": "running",
        "documentation": "/docs",
        "consul_server": Config.MAIN_SERVER
    }

# Incluir routers
app.include_router(services_router, prefix="/api/v1/services", tags=["Services"])
app.include_router(nodes_router, prefix="/api/v1/nodes", tags=["Nodes"])
app.include_router(config_router, prefix="/api/v1/config", tags=["Config"])
app.include_router(blackbox_router, prefix="/api/v1/blackbox", tags=["Blackbox"])
app.include_router(kv_router, prefix="/api/v1/kv", tags=["Key-Value Store"])
app.include_router(presets_router, prefix="/api/v1/presets", tags=["Service Presets"])
app.include_router(search_router, prefix="/api/v1/search", tags=["Search"])
app.include_router(consul_insights_router, prefix="/api/v1/consul", tags=["Consul Insights"])
app.include_router(audit_router, prefix="/api/v1", tags=["Audit Logs"])
app.include_router(dashboard_router, prefix="/api/v1", tags=["Dashboard"])
app.include_router(optimized_router, prefix="/api/v1", tags=["Optimized Endpoints"])
app.include_router(prometheus_config_router, prefix="/api/v1", tags=["Prometheus Config"])
app.include_router(metadata_fields_router, prefix="/api/v1", tags=["Metadata Fields"])
# app.include_router(metadata_dynamic_router, prefix="/api/v1", tags=["Dynamic Metadata"])  # REMOVIDO: Usar prometheus-config
app.include_router(monitoring_types_dynamic_router, prefix="/api/v1", tags=["Monitoring Types"])  # Tipos extraídos DINAMICAMENTE de Prometheus.yml
app.include_router(monitoring_unified_router, prefix="/api/v1", tags=["Monitoring Unified"])  # ⭐ NOVO: API unificada (v2.0 2025-11-13)
app.include_router(categorization_rules_router, prefix="/api/v1", tags=["Categorization Rules"])  # ⭐ NOVO: CRUD de regras (v2.0 2025-11-13)
app.include_router(reference_values_router, prefix="/api/v1/reference-values", tags=["Reference Values"])  # NOVO: Auto-cadastro
app.include_router(service_tags_router, prefix="/api/v1/service-tags", tags=["Service Tags"])  # NOVO: Tags retroalimentáveis
app.include_router(settings_router, prefix="/api/v1", tags=["Settings"])  # NOVO: Configurações globais
app.include_router(cache_router, prefix="/api/v1", tags=["Cache"])  # SPRINT 2: Cache management

# SPRINT 2 (2025-11-15): Prometheus metrics parsed para dashboard frontend
from api.prometheus_metrics import router as prometheus_metrics_router
app.include_router(prometheus_metrics_router, prefix="/api/v1", tags=["Prometheus"])

if HAS_INSTALLER:
    app.include_router(installer_router, prefix="/api/v1/installer", tags=["Installer"])
    app.include_router(health_router, prefix="/api/v1/health", tags=["Health Check"])


# ============================================================================
# ENDPOINT PROMETHEUS METRICS - SPRINT 2 (2025-11-15)
# ============================================================================

@app.get("/metrics", tags=["Metrics"], include_in_schema=False)
async def metrics_endpoint():
    """
    Endpoint para Prometheus scraping.

    Retorna métricas no formato Prometheus:
    - Consul API performance (latência, erros, fallbacks)
    - Cache hits/misses (Agent Caching + LocalCache)
    - Serviços descobertos
    - Blackbox targets
    - API endpoint performance

    IMPORTANTE: Este endpoint NÃO requer autenticação para permitir
    scraping do Prometheus sem configurar Basic Auth.

    FORMATO: Prometheus exposition format
    EXEMPLO:
    ```
    # HELP consul_request_duration_seconds Tempo de resposta das requisições
    # TYPE consul_request_duration_seconds histogram
    consul_request_duration_seconds_sum{method="GET",endpoint="/catalog/services",node="master"} 1.234
    ```
    """
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=5000,
        log_level="info"
    )
