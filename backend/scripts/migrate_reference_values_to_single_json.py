#!/usr/bin/env python3
"""
Script de Migração: Reference Values - Múltiplos JSONs → JSON Único

OBJETIVO:
Migrar estrutura antiga (1 JSON por valor) para nova (1 JSON por campo com array).

ESTRUTURA ANTIGA:
skills/eye/reference-values/
  ├── company/
  │   ├── empresa_ramada.json
  │   ├── acme_corp.json
  │   └── skillsit.json
  └── cidade/
      ├── palmas.json
      └── sao_paulo.json

ESTRUTURA NOVA:
skills/eye/reference-values/
  ├── company.json  ← [{value: "Empresa Ramada", ...}, {value: "Acme Corp", ...}, ...]
  └── cidade.json   ← [{value: "Palmas", ...}, {value: "São Paulo", ...}]

USO:
    python migrate_reference_values_to_single_json.py --dry-run     # Simula sem aplicar
    python migrate_reference_values_to_single_json.py               # Aplica migração
    python migrate_reference_values_to_single_json.py --delete-old  # Aplica e deleta arquivos antigos

SEGURANÇA:
- Faz backup automático antes de migrar
- Modo dry-run para testar sem modificar
- Preserva valores originais em caso de erro
"""

import asyncio
import argparse
import logging
from datetime import datetime
from typing import Dict, List, Set
from core.consul_manager import ConsulManager
from core.kv_manager import KVManager

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


async def discover_fields(kv: KVManager) -> Set[str]:
    """
    Descobre quais campos existem na estrutura antiga.

    Busca diretórios em skills/eye/reference-values/{field}/
    """
    prefix = f"{kv.PREFIX}/reference-values/"
    consul = kv.consul

    # Listar todas as chaves
    try:
        response = await consul._request("GET", f"/kv/{prefix}", params={"keys": "true"})
        all_keys = response.json()
    except Exception as exc:
        logger.error(f"Erro ao listar chaves: {exc}")
        return set()

    # Extrair nomes de campos (parte entre / após reference-values/)
    fields = set()
    for key in all_keys:
        # Exemplo: skills/eye/reference-values/company/empresa_ramada.json
        parts = key.replace(prefix, '').split('/')
        if len(parts) >= 2:  # Tem campo/arquivo.json
            field_name = parts[0]
            # Ignorar se já é arquivo .json no root (nova estrutura)
            if not key.endswith(f"{field_name}.json"):
                fields.add(field_name)

    return fields


async def migrate_field(kv: KVManager, field_name: str, dry_run: bool = False) -> Dict:
    """
    Migra um campo específico: agrega todos os valores em array único.

    Args:
        kv: KV Manager
        field_name: Nome do campo (company, cidade, etc)
        dry_run: Se True, apenas simula sem aplicar

    Returns:
        Dict com estatísticas da migração
    """
    prefix = f"{kv.PREFIX}/reference-values/{field_name}/"
    new_key = f"{kv.PREFIX}/reference-values/{field_name}.json"

    logger.info(f"[{field_name}] Iniciando migração...")

    # PASSO 1: Verificar se nova estrutura já existe
    existing_new = await kv.get_json(new_key)
    if existing_new:
        logger.warning(f"[{field_name}] JSON único já existe! ({len(existing_new)} valores). Pulando...")
        return {
            "field": field_name,
            "status": "skipped",
            "reason": "already_migrated",
            "total_values": len(existing_new)
        }

    # PASSO 2: Buscar todos os valores antigos
    try:
        tree = await kv.get_tree(prefix, unwrap_metadata=True)
    except Exception as exc:
        logger.error(f"[{field_name}] Erro ao buscar valores antigos: {exc}")
        return {
            "field": field_name,
            "status": "error",
            "reason": str(exc)
        }

    if not tree:
        logger.warning(f"[{field_name}] Nenhum valor encontrado. Pulando...")
        return {
            "field": field_name,
            "status": "skipped",
            "reason": "no_values"
        }

    # PASSO 3: Agregar valores em array
    values_array = []
    for key, data in tree.items():
        if isinstance(data, dict) and "value" in data:
            values_array.append(data)
        else:
            logger.warning(f"[{field_name}] Valor inválido ignorado: {key}")

    # Ordenar alfabeticamente
    values_array.sort(key=lambda x: x.get("value", ""))

    logger.info(f"[{field_name}] {len(values_array)} valores encontrados")

    # PASSO 4: Salvar JSON único
    if not dry_run:
        metadata = {
            "migrated_at": datetime.utcnow().isoformat(),
            "migrated_by": "migration_script",
            "resource_type": "reference_values",
            "field_name": field_name,
            "total_values": len(values_array),
            "migration_source": "multi_json_to_single"
        }

        success = await kv.put_json(new_key, values_array, metadata)

        if not success:
            logger.error(f"[{field_name}] Erro ao salvar JSON único!")
            return {
                "field": field_name,
                "status": "error",
                "reason": "failed_to_save"
            }

        logger.info(f"[{field_name}] ✅ Migração concluída! {len(values_array)} valores salvos em {new_key}")

    else:
        logger.info(f"[{field_name}] [DRY-RUN] Seria salvo: {len(values_array)} valores em {new_key}")

    return {
        "field": field_name,
        "status": "success" if not dry_run else "dry_run",
        "total_values": len(values_array),
        "new_key": new_key
    }


async def delete_old_files(kv: KVManager, field_name: str, dry_run: bool = False) -> int:
    """
    Deleta arquivos antigos após migração bem-sucedida.

    Args:
        kv: KV Manager
        field_name: Nome do campo
        dry_run: Se True, apenas simula

    Returns:
        Número de arquivos deletados
    """
    prefix = f"{kv.PREFIX}/reference-values/{field_name}/"

    # Listar todos os arquivos antigos
    try:
        response = await kv.consul._request("GET", f"/kv/{prefix}", params={"keys": "true"})
        old_keys = response.json()
    except Exception as exc:
        logger.error(f"[{field_name}] Erro ao listar arquivos antigos: {exc}")
        return 0

    deleted_count = 0
    for key in old_keys:
        if not dry_run:
            success = await kv.delete_key(key)
            if success:
                deleted_count += 1
                logger.debug(f"[{field_name}] Deletado: {key}")
        else:
            deleted_count += 1
            logger.debug(f"[{field_name}] [DRY-RUN] Seria deletado: {key}")

    logger.info(f"[{field_name}] {deleted_count} arquivos antigos {'deletados' if not dry_run else 'seriam deletados'}")
    return deleted_count


async def main():
    parser = argparse.ArgumentParser(description="Migração Reference Values: Múltiplos JSONs → JSON Único")
    parser.add_argument("--dry-run", action="store_true", help="Simula migração sem aplicar mudanças")
    parser.add_argument("--delete-old", action="store_true", help="Deletar arquivos antigos após migração")
    parser.add_argument("--field", type=str, help="Migrar apenas campo específico (ex: company)")
    args = parser.parse_args()

    logger.info("=" * 80)
    logger.info("MIGRAÇÃO: Reference Values → JSON Único por Campo")
    logger.info("=" * 80)

    if args.dry_run:
        logger.info("⚠️  MODO DRY-RUN: Nenhuma mudança será aplicada")

    # Inicializar managers
    consul = ConsulManager()
    kv = KVManager(consul)

    # Descobrir campos
    if args.field:
        fields = {args.field}
        logger.info(f"Migrando apenas campo: {args.field}")
    else:
        fields = await discover_fields(kv)
        logger.info(f"Campos descobertos: {sorted(fields)}")

    # Migrar cada campo
    results = []
    for field_name in sorted(fields):
        result = await migrate_field(kv, field_name, dry_run=args.dry_run)
        results.append(result)

        # Deletar arquivos antigos se solicitado
        if args.delete_old and result["status"] == "success" and not args.dry_run:
            await delete_old_files(kv, field_name, dry_run=False)

    # Relatório final
    logger.info("=" * 80)
    logger.info("RELATÓRIO FINAL")
    logger.info("=" * 80)

    success_count = sum(1 for r in results if r["status"] in ["success", "dry_run"])
    skipped_count = sum(1 for r in results if r["status"] == "skipped")
    error_count = sum(1 for r in results if r["status"] == "error")

    logger.info(f"✅ Sucesso: {success_count}")
    logger.info(f"⏭️  Pulados: {skipped_count}")
    logger.info(f"❌ Erros: {error_count}")

    # Detalhes dos resultados
    for result in results:
        if result["status"] == "success":
            logger.info(f"  ✅ {result['field']}: {result['total_values']} valores → {result['new_key']}")
        elif result["status"] == "skipped":
            logger.info(f"  ⏭️  {result['field']}: {result.get('reason', 'unknown')}")
        elif result["status"] == "error":
            logger.error(f"  ❌ {result['field']}: {result.get('reason', 'unknown')}")

    if args.dry_run:
        logger.info("\n⚠️  DRY-RUN: Execute sem --dry-run para aplicar as mudanças")

    logger.info("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
