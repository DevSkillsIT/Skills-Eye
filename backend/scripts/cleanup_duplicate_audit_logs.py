"""
Script para limpar audit logs duplicados do Consul KV

Problema: Durante desenvolvimento, o endpoint /api/v1/presets/builtin/create foi chamado
100+ vezes, gerando centenas de audit logs duplicados para os mesmos 4 presets builtin.

Solução: Este script identifica e remove audit logs duplicados, mantendo apenas
o primeiro registro de cada resource_type + resource_id.
"""
import asyncio
import sys
from datetime import datetime
from typing import Dict, List
from collections import defaultdict

# Adicionar backend ao path para importar módulos
sys.path.insert(0, '.')

from core.consul_manager import ConsulManager


async def cleanup_duplicate_audit_logs():
    """
    Limpa audit logs duplicados do Consul KV.

    Estratégia:
    1. Lista todos os audit logs (skills/eye/audit/*)
    2. Agrupa por (resource_type, resource_id)
    3. Para cada grupo, mantém apenas o mais antigo (primeiro created)
    4. Deleta os demais
    """
    print("=" * 80)
    print("LIMPEZA DE AUDIT LOGS DUPLICADOS")
    print("=" * 80)
    print()

    consul = ConsulManager()
    audit_prefix = "skills/eye/audit"

    # PASSO 1: Buscar todos os audit logs
    print(f"[1/5] Buscando todos os audit logs em '{audit_prefix}'...")
    all_logs = await consul.get_kv_tree(audit_prefix)

    if not all_logs:
        print("[OK] Nenhum audit log encontrado. Nada a fazer.")
        return

    print(f"[OK] Encontrados {len(all_logs)} audit logs")
    print()

    # PASSO 2: Agrupar logs por (resource_type, resource_id)
    print("[2/5] Analisando e agrupando logs...")

    # Estrutura: {(resource_type, resource_id): [(key, timestamp, data), ...]}
    groups: Dict[tuple, List[tuple]] = defaultdict(list)

    for key, log_data in all_logs.items():
        if not isinstance(log_data, dict):
            continue

        resource_type = log_data.get("resource_type", "unknown")
        resource_id = log_data.get("resource_id", "unknown")
        timestamp = log_data.get("timestamp", "1970-01-01T00:00:00")

        group_key = (resource_type, resource_id)
        groups[group_key].append((key, timestamp, log_data))

    print(f"[OK] Identificados {len(groups)} recursos unicos")
    print()

    # PASSO 3: Identificar duplicatas
    print("[3/5] Identificando duplicatas...")

    total_duplicates = 0
    duplicates_to_delete = []

    for group_key, logs in groups.items():
        resource_type, resource_id = group_key

        if len(logs) > 1:
            # Ordenar por timestamp (mais antigo primeiro)
            logs.sort(key=lambda x: x[1])

            # Manter o primeiro (mais antigo), deletar o resto
            logs_to_keep = logs[0]
            logs_to_remove = logs[1:]

            duplicates_count = len(logs_to_remove)
            total_duplicates += duplicates_count

            print(f"  • {resource_type}/{resource_id}: {duplicates_count} duplicatas")

            # Adicionar à lista de deleção
            for key, timestamp, _ in logs_to_remove:
                duplicates_to_delete.append(key)

    if total_duplicates == 0:
        print("[OK] Nenhuma duplicata encontrada!")
        print()
        print("=" * 80)
        return

    print()
    print(f"[OK] Total de duplicatas identificadas: {total_duplicates}")
    print()

    # PASSO 4: Confirmar deleção
    print("[4/5] Confirmação necessária")
    print(f"Deseja deletar {total_duplicates} audit logs duplicados? (s/n): ", end="")

    confirmation = input().strip().lower()

    if confirmation != 's':
        print("[CANCELADO] Operacao cancelada pelo usuario")
        return

    print()

    # PASSO 5: Deletar duplicatas
    print(f"[5/5] Deletando {total_duplicates} audit logs duplicados...")

    deleted_count = 0
    failed_count = 0

    for key in duplicates_to_delete:
        try:
            success = await consul.delete_key(key)
            if success:
                deleted_count += 1
                if deleted_count % 50 == 0:
                    print(f"  Progresso: {deleted_count}/{total_duplicates} deletados...")
            else:
                failed_count += 1
        except Exception as exc:
            print(f"  [ERRO] Erro ao deletar {key}: {exc}")
            failed_count += 1

    print()
    print("=" * 80)
    print("RESUMO DA LIMPEZA")
    print("=" * 80)
    print(f"Total de audit logs antes:     {len(all_logs)}")
    print(f"Duplicatas identificadas:      {total_duplicates}")
    print(f"Deletados com sucesso:         {deleted_count}")
    print(f"Falhas:                        {failed_count}")
    print(f"Total de audit logs depois:    {len(all_logs) - deleted_count}")
    print("=" * 80)
    print()

    if failed_count == 0:
        print("[SUCESSO] Limpeza concluida com sucesso!")
    else:
        print(f"[AVISO] Limpeza concluida com {failed_count} falhas")


async def analyze_audit_logs():
    """
    Analisa audit logs para estatísticas detalhadas (modo dry-run).
    """
    print("=" * 80)
    print("ANÁLISE DE AUDIT LOGS")
    print("=" * 80)
    print()

    consul = ConsulManager()
    audit_prefix = "skills/eye/audit"

    print(f"Analisando logs em '{audit_prefix}'...")
    all_logs = await consul.get_kv_tree(audit_prefix)

    if not all_logs:
        print("[OK] Nenhum audit log encontrado.")
        return

    print(f"[OK] Total: {len(all_logs)} logs")
    print()

    # Estatisticas por resource_type
    by_type: Dict[str, int] = defaultdict(int)
    by_action: Dict[str, int] = defaultdict(int)
    by_resource: Dict[tuple, int] = defaultdict(int)

    for key, log_data in all_logs.items():
        if not isinstance(log_data, dict):
            continue

        resource_type = log_data.get("resource_type", "unknown")
        resource_id = log_data.get("resource_id", "unknown")
        action = log_data.get("action", "unknown")

        by_type[resource_type] += 1
        by_action[action] += 1
        by_resource[(resource_type, resource_id)] += 1

    print("ESTATISTICAS POR TIPO:")
    for res_type, count in sorted(by_type.items(), key=lambda x: -x[1]):
        print(f"  - {res_type}: {count} logs")

    print()
    print("ESTATISTICAS POR ACAO:")
    for action, count in sorted(by_action.items(), key=lambda x: -x[1]):
        print(f"  - {action}: {count} logs")

    print()
    print("TOP 10 RECURSOS COM MAIS LOGS:")
    top_resources = sorted(by_resource.items(), key=lambda x: -x[1])[:10]
    for (res_type, res_id), count in top_resources:
        print(f"  - {res_type}/{res_id}: {count} logs")

    print()
    print("=" * 80)


if __name__ == "__main__":
    print()
    print("Escolha uma opção:")
    print("  1) Analisar logs (dry-run, sem modificações)")
    print("  2) Limpar duplicatas (requer confirmação)")
    print()
    print("Opção (1 ou 2): ", end="")

    option = input().strip()

    if option == "1":
        asyncio.run(analyze_audit_logs())
    elif option == "2":
        asyncio.run(cleanup_duplicate_audit_logs())
    else:
        print("Opção inválida")
