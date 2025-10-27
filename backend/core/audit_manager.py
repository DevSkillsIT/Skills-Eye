"""
Gerenciador de Auditoria
Sistema simples de log de auditoria para rastrear operações no sistema
"""
from datetime import datetime
from typing import List, Dict, Optional
from collections import deque
import json

class AuditManager:
    """Gerenciador de eventos de auditoria"""

    def __init__(self, max_events: int = 1000):
        """
        Inicializa o gerenciador de auditoria
        Args:
            max_events: Número máximo de eventos a manter em memória
        """
        self.events: deque = deque(maxlen=max_events)
        self._event_id_counter = 0

    def log_event(
        self,
        action: str,
        resource_type: str,
        resource_id: str,
        user: str = "system",
        details: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> Dict:
        """
        Registra um evento de auditoria

        Args:
            action: Ação realizada (create, update, delete, read, etc.)
            resource_type: Tipo de recurso (service, kv, node, etc.)
            resource_id: ID do recurso afetado
            user: Usuário que realizou a ação
            details: Detalhes adicionais da ação
            metadata: Metadados adicionais

        Returns:
            Dict com o evento registrado
        """
        self._event_id_counter += 1

        event = {
            "id": self._event_id_counter,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "action": action,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "user": user,
            "details": details or f"{action} on {resource_type}: {resource_id}",
            "metadata": metadata or {}
        }

        self.events.append(event)
        return event

    def get_events(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        resource_type: Optional[str] = None,
        action: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> tuple[List[Dict], int]:
        """
        Recupera eventos de auditoria com filtros

        Args:
            start_date: Data inicial (ISO format)
            end_date: Data final (ISO format)
            resource_type: Filtrar por tipo de recurso
            action: Filtrar por ação
            limit: Número máximo de eventos a retornar
            offset: Número de eventos a pular

        Returns:
            Tupla (lista de eventos, total de eventos)
        """
        # Converter deque para lista para facilitar filtros
        all_events = list(self.events)

        # Aplicar filtros
        filtered_events = all_events

        if resource_type:
            filtered_events = [
                e for e in filtered_events
                if e.get("resource_type") == resource_type
            ]

        if action:
            filtered_events = [
                e for e in filtered_events
                if e.get("action") == action
            ]

        if start_date:
            filtered_events = [
                e for e in filtered_events
                if e.get("timestamp", "") >= start_date
            ]

        if end_date:
            filtered_events = [
                e for e in filtered_events
                if e.get("timestamp", "") <= end_date
            ]

        # Ordenar por timestamp decrescente (mais recentes primeiro)
        filtered_events.sort(key=lambda x: x.get("timestamp", ""), reverse=True)

        total = len(filtered_events)

        # Aplicar paginação
        paginated_events = filtered_events[offset:offset + limit]

        return paginated_events, total

    def clear_events(self):
        """Limpa todos os eventos de auditoria"""
        self.events.clear()
        self._event_id_counter = 0

    def get_statistics(self) -> Dict:
        """
        Retorna estatísticas sobre os eventos de auditoria

        Returns:
            Dict com estatísticas
        """
        all_events = list(self.events)

        actions_count = {}
        resource_types_count = {}
        users_count = {}

        for event in all_events:
            action = event.get("action", "unknown")
            resource_type = event.get("resource_type", "unknown")
            user = event.get("user", "unknown")

            actions_count[action] = actions_count.get(action, 0) + 1
            resource_types_count[resource_type] = resource_types_count.get(resource_type, 0) + 1
            users_count[user] = users_count.get(user, 0) + 1

        return {
            "total_events": len(all_events),
            "by_action": actions_count,
            "by_resource_type": resource_types_count,
            "by_user": users_count
        }


# Instância global do gerenciador de auditoria
audit_manager = AuditManager(max_events=5000)


# Funções auxiliares para facilitar o uso
def log_service_create(service_id: str, user: str = "system", metadata: Optional[Dict] = None):
    """Log de criação de serviço"""
    return audit_manager.log_event("create", "service", service_id, user, metadata=metadata)

def log_service_update(service_id: str, user: str = "system", metadata: Optional[Dict] = None):
    """Log de atualização de serviço"""
    return audit_manager.log_event("update", "service", service_id, user, metadata=metadata)

def log_service_delete(service_id: str, user: str = "system", metadata: Optional[Dict] = None):
    """Log de remoção de serviço"""
    return audit_manager.log_event("delete", "service", service_id, user, metadata=metadata)

def log_kv_create(key: str, user: str = "system", metadata: Optional[Dict] = None):
    """Log de criação de KV"""
    return audit_manager.log_event("create", "kv", key, user, metadata=metadata)

def log_kv_update(key: str, user: str = "system", metadata: Optional[Dict] = None):
    """Log de atualização de KV"""
    return audit_manager.log_event("update", "kv", key, user, metadata=metadata)

def log_kv_delete(key: str, user: str = "system", metadata: Optional[Dict] = None):
    """Log de remoção de KV"""
    return audit_manager.log_event("delete", "kv", key, user, metadata=metadata)

def log_blackbox_create(target_id: str, user: str = "system", metadata: Optional[Dict] = None):
    """Log de criação de blackbox target"""
    return audit_manager.log_event("create", "blackbox_target", target_id, user, metadata=metadata)

def log_blackbox_update(target_id: str, user: str = "system", metadata: Optional[Dict] = None):
    """Log de atualização de blackbox target"""
    return audit_manager.log_event("update", "blackbox_target", target_id, user, metadata=metadata)

def log_blackbox_delete(target_id: str, user: str = "system", metadata: Optional[Dict] = None):
    """Log de remoção de blackbox target"""
    return audit_manager.log_event("delete", "blackbox_target", target_id, user, metadata=metadata)
