"""
Sistema de Backup e Restauração Automática para Monitoring Types

Este módulo implementa:
1. Backup automático antes de salvar no KV
2. Restauração automática se KV for apagado
3. Histórico de backups (últimos N backups)
4. Validação de integridade (incluindo form_schema)

IMPORTANTE: Este é um arquivo CRÍTICO - preserva configurações de form_schema customizadas!
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List

from .kv_manager import KVManager

logger = logging.getLogger(__name__)

# Chave principal no KV
KV_KEY = 'skills/eye/monitoring-types'
# Chave de backup no KV (último backup)
KV_BACKUP_KEY = 'skills/eye/monitoring-types.backup'
# Chave de histórico de backups (últimos N backups)
KV_BACKUP_HISTORY_KEY = 'skills/eye/monitoring-types.backup.history'
# Número máximo de backups no histórico
MAX_BACKUP_HISTORY = 10


class MonitoringTypesBackupManager:
    """
    Gerenciador de backup e restauração para monitoring types

    Features:
    - Backup automático antes de salvar
    - Restauração automática se KV for apagado
    - Histórico de backups (últimos N)
    - Validação de integridade (incluindo form_schema)
    """

    def __init__(self):
        self.kv = KVManager()

    async def create_backup(self, types_data: Dict[str, Any]) -> bool:
        """
        Cria backup dos monitoring types antes de salvar no KV

        Args:
            types_data: Dados dos tipos para fazer backup

        Returns:
            True se backup foi criado com sucesso
        """
        try:
            # Adicionar metadata de backup
            backup_data = {
                'types_data': types_data,
                'backup_timestamp': datetime.utcnow().isoformat() + 'Z',
                'backup_version': types_data.get('version', '1.0.0'),
                'total_types': types_data.get('total_types', 0),
                'total_servers': types_data.get('total_servers', 0),
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
                logger.error("[MONITORING-TYPES-BACKUP] ❌ Falha ao criar backup principal")
                return False

            # Adicionar ao histórico
            await self._add_to_history(backup_data)

            logger.info(
                f"[MONITORING-TYPES-BACKUP] ✅ Backup criado: {backup_data['total_types']} tipos "
                f"de {backup_data['total_servers']} servidores (versão: {backup_data['backup_version']})"
            )

            return True

        except Exception as e:
            logger.error(f"[MONITORING-TYPES-BACKUP] ❌ Erro ao criar backup: {e}", exc_info=True)
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

            logger.debug(f"[MONITORING-TYPES-BACKUP] Histórico atualizado: {len(history)} backups")

        except Exception as e:
            logger.warning(f"[MONITORING-TYPES-BACKUP] Aviso: Não foi possível atualizar histórico: {e}")

    async def restore_from_backup(self) -> Optional[Dict[str, Any]]:
        """
        Restaura monitoring types do backup se KV principal estiver vazio

        Returns:
            Dados restaurados ou None se não houver backup
        """
        try:
            # Verificar se KV principal está vazio
            main_data = await self.kv.get_json(KV_KEY)

            if main_data and main_data.get('data', {}).get('all_types'):
                logger.info("[MONITORING-TYPES-BACKUP] KV principal não está vazio - não é necessário restaurar")
                return None

            # Buscar backup principal
            backup_data = await self.kv.get_json(KV_BACKUP_KEY)

            if not backup_data:
                logger.warning("[MONITORING-TYPES-BACKUP] ⚠️ Nenhum backup encontrado para restaurar")
                return None

            # Extrair dados dos tipos
            types_data = backup_data.get('types_data')

            if not types_data:
                logger.error("[MONITORING-TYPES-BACKUP] ❌ Backup corrompido: sem 'types_data'")
                return None

            # Validar integridade
            if not self._validate_backup(types_data):
                logger.error("[MONITORING-TYPES-BACKUP] ❌ Backup falhou validação de integridade")
                return None

            # Restaurar no KV principal
            success = await self.kv.put_json(
                KV_KEY,
                types_data,
                metadata={
                    'restored_from_backup': True,
                    'backup_timestamp': backup_data.get('backup_timestamp'),
                    'restored_at': datetime.utcnow().isoformat() + 'Z',
                }
            )

            if not success:
                logger.error("[MONITORING-TYPES-BACKUP] ❌ Falha ao restaurar backup no KV principal")
                return None

            logger.info(
                f"[MONITORING-TYPES-BACKUP] ✅ Backup restaurado: {types_data.get('total_types', 0)} tipos "
                f"(backup de {backup_data.get('backup_timestamp', 'desconhecido')})"
            )

            return types_data

        except Exception as e:
            logger.error(f"[MONITORING-TYPES-BACKUP] ❌ Erro ao restaurar backup: {e}", exc_info=True)
            return None

    async def restore_from_history(self, index: int = 0) -> Optional[Dict[str, Any]]:
        """
        Restaura monitoring types do histórico de backups

        Args:
            index: Índice do backup no histórico (0 = mais recente)

        Returns:
            Dados restaurados ou None se não houver backup no índice
        """
        try:
            # Buscar histórico
            history = await self.kv.get_json(KV_BACKUP_HISTORY_KEY, default=[])

            if not isinstance(history, list) or len(history) == 0:
                logger.warning("[MONITORING-TYPES-BACKUP] ⚠️ Histórico de backups vazio")
                return None

            if index >= len(history):
                logger.error(f"[MONITORING-TYPES-BACKUP] ❌ Índice {index} fora do range do histórico ({len(history)} backups)")
                return None

            # Buscar backup do histórico
            backup_data = history[index]
            types_data = backup_data.get('types_data')

            if not types_data:
                logger.error(f"[MONITORING-TYPES-BACKUP] ❌ Backup do histórico (índice {index}) corrompido")
                return None

            # Validar integridade
            if not self._validate_backup(types_data):
                logger.error(f"[MONITORING-TYPES-BACKUP] ❌ Backup do histórico (índice {index}) falhou validação")
                return None

            # Restaurar no KV principal
            success = await self.kv.put_json(
                KV_KEY,
                types_data,
                metadata={
                    'restored_from_history': True,
                    'history_index': index,
                    'backup_timestamp': backup_data.get('backup_timestamp'),
                    'restored_at': datetime.utcnow().isoformat() + 'Z',
                }
            )

            if not success:
                logger.error("[MONITORING-TYPES-BACKUP] ❌ Falha ao restaurar backup do histórico")
                return None

            logger.info(
                f"[MONITORING-TYPES-BACKUP] ✅ Backup do histórico restaurado (índice {index}): "
                f"{types_data.get('total_types', 0)} tipos "
                f"(backup de {backup_data.get('backup_timestamp', 'desconhecido')})"
            )

            return types_data

        except Exception as e:
            logger.error(f"[MONITORING-TYPES-BACKUP] ❌ Erro ao restaurar do histórico: {e}", exc_info=True)
            return None

    def _validate_backup(self, types_data: Dict[str, Any]) -> bool:
        """
        Valida integridade dos dados do backup

        Args:
            types_data: Dados para validar

        Returns:
            True se dados são válidos
        """
        try:
            # Verificar estrutura básica
            if not isinstance(types_data, dict):
                logger.error("[MONITORING-TYPES-BACKUP-VALIDATION] ❌ Dados não são dict")
                return False

            # Verificar estrutura 'data'
            data = types_data.get('data', {})
            if not isinstance(data, dict):
                logger.error("[MONITORING-TYPES-BACKUP-VALIDATION] ❌ 'data' não é um dict")
                return False

            # Verificar se tem all_types
            all_types = data.get('all_types', [])
            if not isinstance(all_types, list):
                logger.error("[MONITORING-TYPES-BACKUP-VALIDATION] ❌ 'all_types' não é uma lista")
                return False

            if len(all_types) == 0:
                logger.warning("[MONITORING-TYPES-BACKUP-VALIDATION] ⚠️ Backup vazio (0 tipos)")
                # Não é erro crítico - pode ser válido

            # Verificar estrutura de cada tipo
            for i, type_def in enumerate(all_types):
                if not isinstance(type_def, dict):
                    logger.error(f"[MONITORING-TYPES-BACKUP-VALIDATION] ❌ Tipo {i} não é dict")
                    return False

                # Verificar campos obrigatórios
                required_fields = ['id', 'display_name', 'job_name', 'exporter_type']
                for field in required_fields:
                    if field not in type_def:
                        logger.error(f"[MONITORING-TYPES-BACKUP-VALIDATION] ❌ Tipo {i} sem campo '{field}'")
                        return False

                # Validar form_schema se presente
                if 'form_schema' in type_def and type_def['form_schema']:
                    if not self._validate_form_schema(type_def['form_schema'], i):
                        logger.error(f"[MONITORING-TYPES-BACKUP-VALIDATION] ❌ Tipo {i} com form_schema inválido")
                        return False

            logger.debug(f"[MONITORING-TYPES-BACKUP-VALIDATION] ✅ Backup válido: {len(all_types)} tipos")
            return True

        except Exception as e:
            logger.error(f"[MONITORING-TYPES-BACKUP-VALIDATION] ❌ Erro na validação: {e}")
            return False

    def _validate_form_schema(self, form_schema: Dict[str, Any], type_index: int) -> bool:
        """
        Valida integridade do form_schema

        Args:
            form_schema: Schema para validar
            type_index: Índice do tipo (para logging)

        Returns:
            True se form_schema é válido
        """
        try:
            if not isinstance(form_schema, dict):
                logger.error(f"[FORM-SCHEMA-VALIDATION] ❌ Tipo {type_index}: form_schema não é dict")
                return False

            # Verificar fields (opcional, mas se presente deve ser lista)
            if 'fields' in form_schema:
                fields = form_schema['fields']
                if not isinstance(fields, list):
                    logger.error(f"[FORM-SCHEMA-VALIDATION] ❌ Tipo {type_index}: fields não é lista")
                    return False

                # Validar cada field
                for j, field in enumerate(fields):
                    if not isinstance(field, dict):
                        logger.error(f"[FORM-SCHEMA-VALIDATION] ❌ Tipo {type_index}, field {j}: não é dict")
                        return False

                    if 'name' not in field or 'type' not in field:
                        logger.error(f"[FORM-SCHEMA-VALIDATION] ❌ Tipo {type_index}, field {j}: sem 'name' ou 'type'")
                        return False

            # Verificar required_metadata (opcional, mas se presente deve ser lista)
            if 'required_metadata' in form_schema:
                if not isinstance(form_schema['required_metadata'], list):
                    logger.error(f"[FORM-SCHEMA-VALIDATION] ❌ Tipo {type_index}: required_metadata não é lista")
                    return False

            # Verificar optional_metadata (opcional, mas se presente deve ser lista)
            if 'optional_metadata' in form_schema:
                if not isinstance(form_schema['optional_metadata'], list):
                    logger.error(f"[FORM-SCHEMA-VALIDATION] ❌ Tipo {type_index}: optional_metadata não é lista")
                    return False

            return True

        except Exception as e:
            logger.error(f"[FORM-SCHEMA-VALIDATION] ❌ Tipo {type_index}: Erro na validação: {e}")
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
                'backup_total_types': backup_data.get('total_types') if backup_data else None,
                'backup_total_servers': backup_data.get('total_servers') if backup_data else None,
                'history_count': len(history) if isinstance(history, list) else 0,
                'history_timestamps': [
                    h.get('backup_timestamp') for h in history[:5]  # Últimos 5
                ] if isinstance(history, list) else [],
            }

        except Exception as e:
            logger.error(f"[MONITORING-TYPES-BACKUP] Erro ao obter informações: {e}")
            return {
                'has_backup': False,
                'error': str(e),
            }


# Instância global do gerenciador de backup
_backup_manager = None

def get_backup_manager() -> MonitoringTypesBackupManager:
    """Retorna instância singleton do gerenciador de backup"""
    global _backup_manager
    if _backup_manager is None:
        _backup_manager = MonitoringTypesBackupManager()
    return _backup_manager
