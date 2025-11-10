"""
API FastAPI para Consul Manager
Mantém todas as funcionalidades do script original
"""
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import asyncio
import json
from typing import Dict, List, Optional
import os
from dotenv import load_dotenv

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
# from api.metadata_dynamic import router as metadata_dynamic_router  # REMOVIDO: Usar prometheus_config em vez disso
from api.monitoring_types import router as monitoring_types_router  # NOVO: Configuration-driven types
from api.monitoring_types_dynamic import router as monitoring_types_dynamic_router  # NOVO: Tipos extraídos de Prometheus.yml
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

        # PASSO 4: Salvar no Consul KV para acesso rápido
        kv_manager = KVManager()
        await kv_manager.put_json(
            key='skills/eye/metadata/fields',
            value={
                'version': '2.0.0',
                'last_updated': datetime.now().isoformat(),
                'source': 'prewarm_startup',
                'total_fields': len(fields),
                'fields': [f.to_dict() for f in fields],
                'extraction_status': {
                    'total_servers': total_servers,
                    'successful_servers': successful_servers,
                    'server_status': extraction_result.get('server_status', []),
                }
            },
            metadata={'auto_updated': True, 'source': 'startup_prewarm'}
        )

        logger.info(
            f"[PRE-WARM] ✓ Cache populado no KV: {len(fields)} campos salvos. "
            f"Próximas requisições serão instantâneas (<2s)!"
        )
        print(f"[PRE-WARM] ✓ SUCESSO: Cache KV populado com {len(fields)} campos")

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

async def _prewarm_with_timeout():
    """
    Wrapper para adicionar timeout de 60s ao PRE-WARM

    IMPORTANTE: Timeout de 60s para evitar que a aplicação trave
    se algum servidor Prometheus estiver inacessível na inicialização.
    """
    try:
        await asyncio.wait_for(
            _prewarm_metadata_fields_cache(),
            timeout=60.0
        )
    except asyncio.TimeoutError:
        # Timeout já é tratado dentro da função _prewarm_metadata_fields_cache
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

    # PASSO 2: Pré-aquecer cache de campos metadata (BACKGROUND TASK)
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

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "http://localhost:8081",
        "http://localhost:8082",
        "http://localhost:8083",
        "http://localhost:8084",
        f"http://{Config.MAIN_SERVER}:3001",
        f"http://{Config.MAIN_SERVER}:8081",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
app.include_router(services_router, prefix="/api/v1/services", tags=["services"])
app.include_router(nodes_router, prefix="/api/v1/nodes", tags=["nodes"])
app.include_router(config_router, prefix="/api/v1/config", tags=["config"])
app.include_router(blackbox_router, prefix="/api/v1/blackbox", tags=["blackbox"])
app.include_router(kv_router, prefix="/api/v1/kv", tags=["kv"])
app.include_router(presets_router, prefix="/api/v1/presets", tags=["presets"])
app.include_router(search_router, prefix="/api/v1/search", tags=["search"])
app.include_router(consul_insights_router, prefix="/api/v1/consul", tags=["consul"])
app.include_router(audit_router, prefix="/api/v1", tags=["audit"])
app.include_router(dashboard_router, prefix="/api/v1", tags=["dashboard"])
app.include_router(optimized_router, prefix="/api/v1", tags=["optimized"])
app.include_router(prometheus_config_router, prefix="/api/v1", tags=["prometheus-config"])
app.include_router(metadata_fields_router, prefix="/api/v1", tags=["metadata-fields"])
# app.include_router(metadata_dynamic_router, prefix="/api/v1", tags=["metadata-dynamic"])  # REMOVIDO: Usar prometheus-config
app.include_router(monitoring_types_router, prefix="/api/v1", tags=["monitoring-types"])  # NOVO: Configuration-driven
app.include_router(monitoring_types_dynamic_router, prefix="/api/v1", tags=["monitoring-types-dynamic"])  # NOVO: Tipos de Prometheus.yml
app.include_router(reference_values_router, prefix="/api/v1/reference-values", tags=["reference-values"])  # NOVO: Auto-cadastro
app.include_router(service_tags_router, prefix="/api/v1/service-tags", tags=["service-tags"])  # NOVO: Tags retroalimentáveis
app.include_router(settings_router, prefix="/api/v1", tags=["settings"])  # NOVO: Configurações globais

if HAS_INSTALLER:
    app.include_router(installer_router, prefix="/api/v1/installer", tags=["installer"])
    app.include_router(health_router, prefix="/api/v1/health", tags=["health"])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=5000,
        log_level="info"
    )
