"""
Analisa audit logs restantes e propõe política de retenção

Objetivo:
- Identificar logs antigos que podem ser removidos
- Propor política de retenção (exemplo: manter apenas últimos 30/90 dias)
- Calcular economia de armazenamento
"""
import asyncio
import sys
from datetime import datetime, timedelta
from collections import defaultdict
from typing import Dict, List

sys.path.insert(0, '.')

from core.consul_manager import ConsulManager


async def analyze_retention():
    """
    Analisa distribuição temporal de audit logs e propõe retenção
    """
    print("=" * 80)
    print("ANALISE DE RETENCAO DE AUDIT LOGS")
    print("=" * 80)
    print()

    consul = ConsulManager()
    audit_prefix = "skills/eye/audit"

    print("[1/4] Carregando todos os audit logs...")
    all_logs = await consul.get_kv_tree(audit_prefix)

    if not all_logs:
        print("[OK] Nenhum audit log encontrado.")
        return

    total = len(all_logs)
    print(f"[OK] Total: {total} logs")
    print()

    # Análise temporal
    print("[2/4] Analisando distribuicao temporal...")

    now = datetime.utcnow()
    by_age: Dict[str, List[tuple]] = {
        "24h": [],
        "7d": [],
        "30d": [],
        "90d": [],
        "180d": [],
        "1y": [],
        ">1y": []
    }

    oldest_timestamp = None
    newest_timestamp = None

    for key, log_data in all_logs.items():
        if not isinstance(log_data, dict):
            continue

        timestamp_str = log_data.get("timestamp", "1970-01-01T00:00:00")

        try:
            # Remover 'Z' do final se presente
            if timestamp_str.endswith('Z'):
                timestamp_str = timestamp_str[:-1]

            timestamp = datetime.fromisoformat(timestamp_str)

            if oldest_timestamp is None or timestamp < oldest_timestamp:
                oldest_timestamp = timestamp

            if newest_timestamp is None or timestamp > newest_timestamp:
                newest_timestamp = timestamp

            age = now - timestamp

            # Categorizar por idade
            if age.total_seconds() < 86400:  # 24 horas
                by_age["24h"].append((key, timestamp, log_data))
            elif age.days <= 7:
                by_age["7d"].append((key, timestamp, log_data))
            elif age.days <= 30:
                by_age["30d"].append((key, timestamp, log_data))
            elif age.days <= 90:
                by_age["90d"].append((key, timestamp, log_data))
            elif age.days <= 180:
                by_age["180d"].append((key, timestamp, log_data))
            elif age.days <= 365:
                by_age["1y"].append((key, timestamp, log_data))
            else:
                by_age[">1y"].append((key, timestamp, log_data))

        except Exception as exc:
            print(f"  [AVISO] Erro ao processar timestamp de {key}: {exc}")

    print()
    print("DISTRIBUICAO POR IDADE:")
    print(f"  - Ultimas 24 horas:     {len(by_age['24h'])} logs")
    print(f"  - Ultimos 7 dias:       {len(by_age['7d'])} logs")
    print(f"  - Ultimos 30 dias:      {len(by_age['30d'])} logs")
    print(f"  - Ultimos 90 dias:      {len(by_age['90d'])} logs")
    print(f"  - Ultimos 180 dias:     {len(by_age['180d'])} logs")
    print(f"  - Ultimos 365 dias:     {len(by_age['1y'])} logs")
    print(f"  - Mais de 1 ano:        {len(by_age['>1y'])} logs")
    print()

    if oldest_timestamp and newest_timestamp:
        age_span = newest_timestamp - oldest_timestamp
        print(f"Log mais antigo:  {oldest_timestamp.isoformat()}")
        print(f"Log mais recente: {newest_timestamp.isoformat()}")
        print(f"Periodo total:    {age_span.days} dias")
        print()

    # Análise de tipos de eventos
    print("[3/4] Analisando tipos de eventos...")

    by_type: Dict[str, int] = defaultdict(int)
    by_action: Dict[str, int] = defaultdict(int)

    for key, log_data in all_logs.items():
        if not isinstance(log_data, dict):
            continue

        resource_type = log_data.get("resource_type", "unknown")
        action = log_data.get("action", "unknown")

        by_type[resource_type] += 1
        by_action[action] += 1

    print()
    print("TIPOS DE RECURSOS:")
    for res_type, count in sorted(by_type.items(), key=lambda x: -x[1]):
        print(f"  - {res_type}: {count} logs")

    print()
    print("TIPOS DE ACOES:")
    for action, count in sorted(by_action.items(), key=lambda x: -x[1]):
        print(f"  - {action}: {count} logs")

    print()

    # Propor políticas de retenção
    print("[4/4] Propondo politicas de retencao...")
    print()
    print("=" * 80)
    print("SIMULACAO DE POLITICAS DE RETENCAO")
    print("=" * 80)

    policies = {
        "30 dias": by_age["24h"] + by_age["7d"] + by_age["30d"],
        "90 dias": by_age["24h"] + by_age["7d"] + by_age["30d"] + by_age["90d"],
        "180 dias": by_age["24h"] + by_age["7d"] + by_age["30d"] + by_age["90d"] + by_age["180d"],
        "1 ano": by_age["24h"] + by_age["7d"] + by_age["30d"] + by_age["90d"] + by_age["180d"] + by_age["1y"],
    }

    for policy_name, kept_logs in policies.items():
        kept_count = len(kept_logs)
        removed_count = total - kept_count
        reduction_pct = (removed_count / total * 100) if total > 0 else 0

        print(f"\nPOLITICA: Manter ultimos {policy_name}")
        print(f"  - Logs mantidos:        {kept_count}")
        print(f"  - Logs removidos:       {removed_count}")
        print(f"  - Reducao:              {reduction_pct:.1f}%")

    print()
    print("=" * 80)
    print()

    # Recomendação
    print("RECOMENDACAO:")
    print()

    # Contar reference_value logs vs outros
    reference_value_count = by_type.get("reference_value", 0)
    other_count = total - reference_value_count

    print(f"ANALISE DE UTILIDADE:")
    print(f"  - reference_value logs: {reference_value_count} ({reference_value_count/total*100:.1f}%)")
    print(f"    Utilidade: BAIXA - auto-cadastro de valores repetidos")
    print()
    print(f"  - Outros logs: {other_count} ({other_count/total*100:.1f}%)")
    print(f"    Utilidade: MEDIA/ALTA - operacoes criticas do sistema")
    print()

    # Contar eventos > 30 dias
    old_logs_30d = len(by_age["90d"]) + len(by_age["180d"]) + len(by_age["1y"]) + len(by_age[">1y"])

    if old_logs_30d > 0:
        print(f"OPCAO 1 - RETENCAO DE 30 DIAS:")
        print(f"  - Manter: {total - old_logs_30d} logs")
        print(f"  - Deletar: {old_logs_30d} logs antigos (> 30 dias)")
        print(f"  - Reducao: {old_logs_30d/total*100:.1f}%")
        print(f"  - Justificativa: Logs > 30 dias raramente sao consultados")
        print()

    # Opção alternativa: remover apenas reference_value logs antigos
    reference_value_old = sum(1 for key, ts, data in by_age["90d"] + by_age["180d"] + by_age["1y"] + by_age[">1y"]
                               if data.get("resource_type") == "reference_value")

    if reference_value_old > 0:
        print(f"OPCAO 2 - LIMPAR APENAS REFERENCE_VALUE ANTIGOS:")
        print(f"  - Manter: {total - reference_value_old} logs")
        print(f"  - Deletar: {reference_value_old} logs reference_value > 90 dias")
        print(f"  - Reducao: {reference_value_old/total*100:.1f}%")
        print(f"  - Justificativa: Reference values sao menos criticos")
        print()

    # Opção 3: desabilitar audit logs para reference_value
    print(f"OPCAO 3 - DESABILITAR AUDIT PARA REFERENCE_VALUE (PERMANENTE):")
    print(f"  - Impacto imediato: {reference_value_count} logs a menos")
    print(f"  - Reducao atual: {reference_value_count/total*100:.1f}%")
    print(f"  - Beneficio futuro: 0 novos logs para reference_value")
    print(f"  - Justificativa: Auto-cadastro nao precisa de auditoria")

    print()
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(analyze_retention())
