#!/usr/bin/env python3
"""
Script para deletar arquivos antigos de reference-values (formato multi-JSON).
Executa APÓS a migração bem-sucedida para o formato JSON único.
"""

import asyncio
import logging
from core.consul_manager import ConsulManager
from core.kv_manager import KVManager

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def delete_old_reference_values():
    """Deleta TODOS os arquivos antigos de reference-values (formato multi-JSON)."""

    logger.info("=" * 80)
    logger.info("DELETANDO ARQUIVOS ANTIGOS DE REFERENCE-VALUES")
    logger.info("=" * 80)

    consul = ConsulManager()
    kv = KVManager(consul)

    # Campos conhecidos (extraídos da migração)
    fields = [
        'cidade', 'cod_localidade', 'company', 'fabricante', 'field_category',
        'grupo_monitoramento', 'localizacao', 'provedor', 'tipo',
        'tipo_dispositivo_abrev', 'tipo_monitoramento', 'vendor'
    ]

    total_deleted = 0

    for field_name in fields:
        prefix = f"{kv.PREFIX}/reference-values/{field_name}/"
        logger.info(f"[{field_name}] Verificando arquivos antigos em {prefix}...")

        try:
            # Listar todos os arquivos antigos (formato: skills/eye/reference-values/campo/valor.json)
            response = await consul._request("GET", f"/kv/{prefix}", params={"keys": "true"})
            old_keys = response.json()

            if not old_keys:
                logger.info(f"[{field_name}] Nenhum arquivo antigo encontrado")
                continue

            logger.info(f"[{field_name}] Encontrados {len(old_keys)} arquivos antigos")

            # Deletar cada arquivo
            for key in old_keys:
                try:
                    success = await kv.delete_key(key)
                    if success:
                        total_deleted += 1
                        logger.debug(f"  ✅ Deletado: {key}")
                    else:
                        logger.warning(f"  ⚠️  Falha ao deletar: {key}")
                except Exception as exc:
                    logger.error(f"  ❌ Erro ao deletar {key}: {exc}")

            logger.info(f"[{field_name}] ✅ {len(old_keys)} arquivos deletados")

        except Exception as exc:
            if "404" in str(exc):
                logger.info(f"[{field_name}] Prefixo vazio (já limpo)")
            else:
                logger.error(f"[{field_name}] Erro ao listar arquivos: {exc}")

    logger.info("=" * 80)
    logger.info(f"TOTAL: {total_deleted} arquivos antigos deletados")
    logger.info("=" * 80)


if __name__ == "__main__":
    asyncio.run(delete_old_reference_values())
