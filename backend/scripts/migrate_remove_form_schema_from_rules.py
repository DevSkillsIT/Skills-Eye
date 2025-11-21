#!/usr/bin/env python3
"""
Script de Migração: Remover form_schema das Regras de Categorização

SPEC-ARCH-001: Este script remove form_schema de todas as regras existentes no KV.
O form_schema deve existir APENAS em monitoring-types, não nas regras.

Uso:
    python scripts/migrate_remove_form_schema_from_rules.py
    python scripts/migrate_remove_form_schema_from_rules.py --dry-run

AUTOR: Sistema de Refatoração Skills Eye v2.0
DATA: 2025-11-20
"""

import asyncio
import argparse
import logging
import sys
import os

# Adicionar o diretório pai ao path para importar módulos do projeto
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.consul_kv_config_manager import ConsulKVConfigManager

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def migrate_remove_form_schema(dry_run: bool = False):
    """
    Remove form_schema de todas as regras no KV

    Args:
        dry_run: Se True, apenas mostra o que seria feito sem salvar

    Returns:
        Número de regras modificadas
    """
    logger.info("=" * 60)
    logger.info("SPEC-ARCH-001: Migração - Remover form_schema das Regras")
    logger.info("=" * 60)

    if dry_run:
        logger.info("🔍 MODO DRY-RUN: Nenhuma alteração será salva")

    config_manager = ConsulKVConfigManager()

    # PASSO 1: Buscar regras atuais
    logger.info("\n📥 Buscando regras do KV...")
    rules_data = await config_manager.get('monitoring-types/categorization/rules')

    if not rules_data:
        logger.error("❌ Regras não encontradas no KV. Execute o script de migração primeiro.")
        return 0

    rules = rules_data.get('rules', [])
    logger.info(f"✅ Encontradas {len(rules)} regras no KV")

    # PASSO 2: Identificar regras com form_schema
    rules_with_schema = []
    rules_without_schema = []

    for rule in rules:
        if 'form_schema' in rule and rule['form_schema'] is not None:
            rules_with_schema.append(rule)
        else:
            rules_without_schema.append(rule)

    logger.info(f"\n📊 Estatísticas:")
    logger.info(f"   - Regras com form_schema: {len(rules_with_schema)}")
    logger.info(f"   - Regras sem form_schema: {len(rules_without_schema)}")

    if not rules_with_schema:
        logger.info("\n✅ Nenhuma regra com form_schema encontrada. Migração não necessária.")
        return 0

    # PASSO 3: Listar regras que serão modificadas
    logger.info(f"\n🔧 Regras que terão form_schema removido:")
    for rule in rules_with_schema:
        schema_info = rule.get('form_schema', {})
        fields_count = len(schema_info.get('fields', [])) if schema_info else 0
        logger.info(f"   - {rule['id']} ({fields_count} campos)")

    # PASSO 4: Remover form_schema
    modified_count = 0
    for rule in rules:
        if 'form_schema' in rule:
            del rule['form_schema']
            modified_count += 1
            logger.info(f"   ✅ Removido form_schema da regra: {rule['id']}")

    # PASSO 5: Salvar no KV (se não for dry-run)
    if not dry_run:
        logger.info(f"\n💾 Salvando {modified_count} regras modificadas no KV...")

        success = await config_manager.put('monitoring-types/categorization/rules', rules_data)

        if success:
            logger.info(f"✅ Migração concluída: {modified_count} regras atualizadas")
        else:
            logger.error("❌ Erro ao salvar no KV")
            return 0
    else:
        logger.info(f"\n🔍 DRY-RUN: {modified_count} regras seriam modificadas")

    logger.info("\n" + "=" * 60)
    logger.info(f"MIGRAÇÃO CONCLUÍDA: {modified_count} regras processadas")
    logger.info("=" * 60)

    return modified_count


def main():
    """Função principal"""
    parser = argparse.ArgumentParser(
        description='Remove form_schema das regras de categorização no KV (SPEC-ARCH-001)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Mostra o que seria feito sem salvar alterações'
    )

    args = parser.parse_args()

    try:
        result = asyncio.run(migrate_remove_form_schema(dry_run=args.dry_run))
        sys.exit(0 if result >= 0 else 1)
    except Exception as e:
        logger.error(f"❌ Erro durante migração: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
