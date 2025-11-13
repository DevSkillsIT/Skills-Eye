"""
Deleta TODOS os audit logs de reference_value
"""
import asyncio
import sys
sys.path.insert(0, '.')

from core.consul_manager import ConsulManager


async def delete_rv_logs():
    print("=" * 80)
    print("DELETANDO AUDIT LOGS DE REFERENCE_VALUE")
    print("=" * 80)
    print()

    cm = ConsulManager()

    print("[1/3] Carregando audit logs...")
    logs = await cm.get_kv_tree('skills/eye/audit')
    total = len(logs)

    rv_logs = [(k,v) for k,v in logs.items() if isinstance(v, dict) and v.get('resource_type') == 'reference_value']
    rv_count = len(rv_logs)

    print(f"[OK] Total de audit logs: {total}")
    print(f"[OK] reference_value logs: {rv_count}")
    print()

    if rv_count == 0:
        print("[OK] Nenhum log de reference_value encontrado!")
        return

    print(f"[2/3] Deletando {rv_count} audit logs de reference_value...")

    deleted = 0
    failed = 0

    for key, _ in rv_logs:
        try:
            success = await cm.delete_key(key)
            if success:
                deleted += 1
                if deleted % 50 == 0:
                    print(f"  Progresso: {deleted}/{rv_count}")
            else:
                failed += 1
        except Exception as exc:
            print(f"  [ERRO] {key}: {exc}")
            failed += 1

    print()
    print("[3/3] Verificando resultado...")
    logs_after = await cm.get_kv_tree('skills/eye/audit')
    total_after = len(logs_after)

    print()
    print("=" * 80)
    print("RESULTADO FINAL")
    print("=" * 80)
    print(f"Audit logs antes:       {total}")
    print(f"reference_value logs:   {rv_count}")
    print(f"Deletados:              {deleted}")
    print(f"Falhas:                 {failed}")
    print(f"Audit logs depois:      {total_after}")
    print(f"Reducao:                {((total - total_after) / total * 100):.1f}%")
    print("=" * 80)
    print()

    if failed == 0:
        print("[SUCESSO] Limpeza concluida!")
    else:
        print(f"[AVISO] {failed} falhas durante limpeza")


if __name__ == "__main__":
    asyncio.run(delete_rv_logs())
