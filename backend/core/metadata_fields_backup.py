"""
Sistema de Backup e Restauração Automática para Metadata Fields

Este módulo implementa:
1. Backup automático antes de salvar no KV
2. Restauração automática se KV for apagado
3. Histórico de backups (últimos N backups)
4. Validação de integridade

IMPORTANTE: Este é um arquivo CRÍTICO - customizações do usuário devem ser preservadas!
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List
from pathlib import Path

from .kv_manager import KVManager

logger = logging.getLogger(__name__)

# Chave principal no KV
KV_KEY = 'skills/eye/metadata/fields'
# Chave de backup no KV (último backup)
KV_BACKUP_KEY = 'skills/eye/metadata/fields.backup'
# Chave de histórico de backups (últimos N backups)
KV_BACKUP_HISTORY_KEY = 'skills/eye/metadata/fields.backup.history'
# Número máximo de backups no histórico
MAX_BACKUP_HISTORY = 10


class MetadataFieldsBackupManager:
    """
    Gerenciador de backup e restauração para metadata fields
    
    Features:
    - Backup automático antes de salvar
    - Restauração automática se KV for apagado
    - Histórico de backups (últimos N)
    - Validação de integridade
    """
    
    def __init__(self):
        self.kv = KVManager()
    
    async def create_backup(self, fields_data: Dict[str, Any]) -> bool:
        """
        Cria backup dos campos metadata antes de salvar no KV
        
        Args:
            fields_data: Dados dos campos para fazer backup
            
        Returns:
            True se backup foi criado com sucesso
        """
        try:
            # Adicionar metadata de backup
            backup_data = {
                'fields_data': fields_data,
                'backup_timestamp': datetime.utcnow().isoformat() + 'Z',
                'backup_version': fields_data.get('version', '1.0.0'),
                'total_fields': len(fields_data.get('fields', [])),
            }
            
            # Salvar backup principal
            success = await self.kv.put_json(
                KV_BACKUP_KEY,
                backup_data,
                metadata={
                    'backup': True,
                    'created_at': backup_data['backup_timestamp'],
                }
            )
            
            if not success:
                logger.error("[BACKUP] ❌ Falha ao criar backup principal")
                return False
            
            # Adicionar ao histórico
            await self._add_to_history(backup_data)
            
            logger.info(
                f"[BACKUP] ✅ Backup criado: {backup_data['total_fields']} campos "
                f"(versão: {backup_data['backup_version']})"
            )
            
            return True
            
        except Exception as e:
            logger.error(f"[BACKUP] ❌ Erro ao criar backup: {e}", exc_info=True)
            return False
    
    async def _add_to_history(self, backup_data: Dict[str, Any]) -> None:
        """Adiciona backup ao histórico (mantém apenas últimos N)"""
        try:
            # Buscar histórico atual
            history = await self.kv.get_json(KV_BACKUP_HISTORY_KEY, default=[])
            
            if not isinstance(history, list):
                history = []
            
            # Adicionar novo backup no início
            history.insert(0, backup_data)
            
            # Manter apenas últimos N backups
            if len(history) > MAX_BACKUP_HISTORY:
                history = history[:MAX_BACKUP_HISTORY]
            
            # Salvar histórico
            await self.kv.put_json(
                KV_BACKUP_HISTORY_KEY,
                history,
                metadata={'backup_history': True}
            )
            
            logger.debug(f"[BACKUP] Histórico atualizado: {len(history)} backups")
            
        except Exception as e:
            logger.warning(f"[BACKUP] Aviso: Não foi possível atualizar histórico: {e}")
    
    async def restore_from_backup(self) -> Optional[Dict[str, Any]]:
        """
        Restaura campos metadata do backup se KV principal estiver vazio
        
        Returns:
            Dados restaurados ou None se não houver backup
        """
        try:
            # Verificar se KV principal está vazio
            main_data = await self.kv.get_json(KV_KEY)
            
            if main_data and main_data.get('fields'):
                logger.info("[BACKUP] KV principal não está vazio - não é necessário restaurar")
                return None
            
            # Buscar backup principal
            backup_data = await self.kv.get_json(KV_BACKUP_KEY)
            
            if not backup_data:
                logger.warning("[BACKUP] ⚠️ Nenhum backup encontrado para restaurar")
                return None
            
            # Extrair dados dos campos
            fields_data = backup_data.get('fields_data')
            
            if not fields_data:
                logger.error("[BACKUP] ❌ Backup corrompido: sem 'fields_data'")
                return None
            
            # Validar integridade
            if not self._validate_backup(fields_data):
                logger.error("[BACKUP] ❌ Backup falhou validação de integridade")
                return None
            
            # Restaurar no KV principal
            success = await self.kv.put_json(
                KV_KEY,
                fields_data,
                metadata={
                    'restored_from_backup': True,
                    'backup_timestamp': backup_data.get('backup_timestamp'),
                    'restored_at': datetime.utcnow().isoformat() + 'Z',
                }
            )
            
            if not success:
                logger.error("[BACKUP] ❌ Falha ao restaurar backup no KV principal")
                return None
            
            logger.info(
                f"[BACKUP] ✅ Backup restaurado: {len(fields_data.get('fields', []))} campos "
                f"(backup de {backup_data.get('backup_timestamp', 'desconhecido')})"
            )
            
            return fields_data
            
        except Exception as e:
            logger.error(f"[BACKUP] ❌ Erro ao restaurar backup: {e}", exc_info=True)
            return None
    
    async def restore_from_history(self, index: int = 0) -> Optional[Dict[str, Any]]:
        """
        Restaura campos metadata do histórico de backups
        
        Args:
            index: Índice do backup no histórico (0 = mais recente)
            
        Returns:
            Dados restaurados ou None se não houver backup no índice
        """
        try:
            # Buscar histórico
            history = await self.kv.get_json(KV_BACKUP_HISTORY_KEY, default=[])
            
            if not isinstance(history, list) or len(history) == 0:
                logger.warning("[BACKUP] ⚠️ Histórico de backups vazio")
                return None
            
            if index >= len(history):
                logger.error(f"[BACKUP] ❌ Índice {index} fora do range do histórico ({len(history)} backups)")
                return None
            
            # Buscar backup do histórico
            backup_data = history[index]
            fields_data = backup_data.get('fields_data')
            
            if not fields_data:
                logger.error(f"[BACKUP] ❌ Backup do histórico (índice {index}) corrompido")
                return None
            
            # Validar integridade
            if not self._validate_backup(fields_data):
                logger.error(f"[BACKUP] ❌ Backup do histórico (índice {index}) falhou validação")
                return None
            
            # Restaurar no KV principal
            success = await self.kv.put_json(
                KV_KEY,
                fields_data,
                metadata={
                    'restored_from_history': True,
                    'history_index': index,
                    'backup_timestamp': backup_data.get('backup_timestamp'),
                    'restored_at': datetime.utcnow().isoformat() + 'Z',
                }
            )
            
            if not success:
                logger.error("[BACKUP] ❌ Falha ao restaurar backup do histórico")
                return None
            
            logger.info(
                f"[BACKUP] ✅ Backup do histórico restaurado (índice {index}): "
                f"{len(fields_data.get('fields', []))} campos "
                f"(backup de {backup_data.get('backup_timestamp', 'desconhecido')})"
            )
            
            return fields_data
            
        except Exception as e:
            logger.error(f"[BACKUP] ❌ Erro ao restaurar do histórico: {e}", exc_info=True)
            return None
    
    def _validate_backup(self, fields_data: Dict[str, Any]) -> bool:
        """
        Valida integridade dos dados do backup
        
        Args:
            fields_data: Dados para validar
            
        Returns:
            True se dados são válidos
        """
        try:
            # Verificar estrutura básica
            if not isinstance(fields_data, dict):
                logger.error("[BACKUP VALIDATION] ❌ Dados não são dict")
                return False
            
            # Verificar se tem campos
            fields = fields_data.get('fields', [])
            if not isinstance(fields, list):
                logger.error("[BACKUP VALIDATION] ❌ 'fields' não é uma lista")
                return False
            
            if len(fields) == 0:
                logger.warning("[BACKUP VALIDATION] ⚠️ Backup vazio (0 campos)")
                # Não é erro crítico - pode ser válido
            
            # Verificar estrutura de cada campo
            for i, field in enumerate(fields):
                if not isinstance(field, dict):
                    logger.error(f"[BACKUP VALIDATION] ❌ Campo {i} não é dict")
                    return False
                
                if 'name' not in field:
                    logger.error(f"[BACKUP VALIDATION] ❌ Campo {i} sem 'name'")
                    return False
            
            logger.debug(f"[BACKUP VALIDATION] ✅ Backup válido: {len(fields)} campos")
            return True
            
        except Exception as e:
            logger.error(f"[BACKUP VALIDATION] ❌ Erro na validação: {e}")
            return False
    
    async def get_backup_info(self) -> Dict[str, Any]:
        """
        Retorna informações sobre backups disponíveis
        
        Returns:
            Dict com informações de backup principal e histórico
        """
        try:
            backup_data = await self.kv.get_json(KV_BACKUP_KEY)
            history = await self.kv.get_json(KV_BACKUP_HISTORY_KEY, default=[])
            
            return {
                'has_backup': backup_data is not None,
                'backup_timestamp': backup_data.get('backup_timestamp') if backup_data else None,
                'backup_version': backup_data.get('backup_version') if backup_data else None,
                'backup_total_fields': backup_data.get('total_fields') if backup_data else None,
                'history_count': len(history) if isinstance(history, list) else 0,
                'history_timestamps': [
                    h.get('backup_timestamp') for h in history[:5]  # Últimos 5
                ] if isinstance(history, list) else [],
            }
            
        except Exception as e:
            logger.error(f"[BACKUP] Erro ao obter informações: {e}")
            return {
                'has_backup': False,
                'error': str(e),
            }


# Instância global do gerenciador de backup
_backup_manager = None

def get_backup_manager() -> MetadataFieldsBackupManager:
    """Retorna instância singleton do gerenciador de backup"""
    global _backup_manager
    if _backup_manager is None:
        _backup_manager = MetadataFieldsBackupManager()
    return _backup_manager

