"""
WebSocket Manager para envio de logs em tempo real
"""
from fastapi import WebSocket
from typing import List, Dict
import json
import asyncio
from datetime import datetime

from core.installers.task_state import append_installation_log


class ConnectionManager:
    """Gerenciador de conexões WebSocket para logs em tempo real"""

    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, client_id: str = "default"):
        """Aceita uma nova conexão WebSocket"""
        await websocket.accept()
        async with self._lock:
            if client_id not in self.active_connections:
                self.active_connections[client_id] = []
            self.active_connections[client_id].append(websocket)

        # Enviar mensagem de boas-vindas
        await self.send_log(
            "Conectado ao servidor. Aguardando operações...",
            "info",
            client_id
        )

    async def disconnect(self, websocket: WebSocket, client_id: str = "default"):
        """Remove uma conexão WebSocket"""
        async with self._lock:
            if client_id in self.active_connections:
                if websocket in self.active_connections[client_id]:
                    self.active_connections[client_id].remove(websocket)

                # Limpar lista se vazia
                if not self.active_connections[client_id]:
                    del self.active_connections[client_id]

    async def send_log(
        self,
        message: str,
        level: str = "info",
        client_id: str = "default",
        data: dict = None
    ):
        """
        Envia log para clientes conectados

        Args:
            message: Mensagem de log
            level: Nível do log (info, success, warning, error, debug)
            client_id: ID do cliente ou "all" para broadcast
            data: Dados adicionais opcionais
        """
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "level": level,
            "message": message,
            "data": data or {}
        }

        if client_id != "all":
            append_installation_log(client_id, log_entry)

        if client_id == "all":
            # Broadcast para todos os clientes
            async with self._lock:
                for connections in self.active_connections.values():
                    await self._send_to_connections(connections, log_entry)
        else:
            # Enviar para cliente específico
            async with self._lock:
                if client_id in self.active_connections:
                    await self._send_to_connections(
                        self.active_connections[client_id],
                        log_entry
                    )

    async def _send_to_connections(self, connections: List[WebSocket], message: dict):
        """Envia mensagem para lista de conexões"""
        disconnected = []

        for connection in connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                # Marcar para remoção se houver erro
                disconnected.append(connection)
                print(f"Erro ao enviar para WebSocket: {e}")

        # Remover conexões com erro
        for conn in disconnected:
            if conn in connections:
                connections.remove(conn)

    async def send_progress(
        self,
        current: int,
        total: int,
        message: str = "",
        client_id: str = "default"
    ):
        """Envia atualização de progresso"""
        await self.send_log(
            message or f"Progresso: {current}/{total}",
            "progress",
            client_id,
            data={
                "current": current,
                "total": total,
                "percentage": (current / total * 100) if total > 0 else 0
            }
        )

    async def send_command_output(
        self,
        command: str,
        output: str,
        exit_code: int,
        client_id: str = "default"
    ):
        """Envia saída de comando executado"""
        level = "success" if exit_code == 0 else "error"
        await self.send_log(
            f"Comando executado: {command}",
            level,
            client_id,
            data={
                "command": command,
                "output": output,
                "exit_code": exit_code
            }
        )

    def has_connections(self, client_id: str = None) -> bool:
        """Verifica se há conexões ativas"""
        if client_id:
            return client_id in self.active_connections and len(self.active_connections[client_id]) > 0
        return len(self.active_connections) > 0

    def get_connection_count(self, client_id: str = None) -> int:
        """Retorna número de conexões ativas"""
        if client_id:
            return len(self.active_connections.get(client_id, []))
        return sum(len(conns) for conns in self.active_connections.values())


# Instância global do gerenciador
ws_manager = ConnectionManager()
