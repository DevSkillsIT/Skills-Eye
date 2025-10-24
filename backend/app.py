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
try:
    from api.installer import router as installer_router
    from api.health import router as health_router
    HAS_INSTALLER = True
except ImportError:
    HAS_INSTALLER = False

load_dotenv()

# Configuração do lifecycle
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("🚀 Iniciando Consul Manager API...")
    yield
    # Shutdown
    print("👋 Desligando Consul Manager API...")

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
    allow_origins=["http://localhost:3000", "http://localhost:3001", f"http://{Config.MAIN_SERVER}:3001"],
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

if HAS_INSTALLER:
    app.include_router(installer_router, prefix="/api/v1/installer", tags=["installer"])
    app.include_router(health_router, prefix="/api/v1/health", tags=["health"])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=5000,
        reload=True,
        log_level="info"
    )