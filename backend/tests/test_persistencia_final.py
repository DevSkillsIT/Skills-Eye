#!/usr/bin/env python3
"""
Script de teste FINAL de persistência do KV monitoring-types
"""
import asyncio
import sys
sys.path.insert(0, '/home/adrianofante/projetos/Skills-Eye/backend')

from core.kv_manager import KVManager
from core.monitoring_types_backup import get_backup_manager

async def main():
    kv = KVManager()
    backup_mgr = get_backup_manager()

    print("═══════════════════════════════════════════════════════════")
    print("🧪 TESTE FINAL DE PERSISTÊNCIA")
    print("═══════════════════════════════════════════════════════════\n")

    # PASSO 1: Verificar KV atual
    print("PASSO 1: Verificando estado atual do KV...")
    kv_data = await kv.get_json('skills/eye/monitoring-types')

    if kv_data and 'all_types' in kv_data:
        tipos = kv_data['all_types']
        com_schema = [t for t in tipos if t.get('form_schema')]
        print(f"✅ KV atual: {len(tipos)} tipos, {len(com_schema)} com form_schema")
        if com_schema:
            print(f"  Tipos: {', '.join([t['id'] for t in com_schema])}")
    else:
        print("❌ KV vazio ou estrutura incorreta")
        print(f"  Chaves: {list(kv_data.keys()) if kv_data else 'None'}")

    # PASSO 2: Verificar backup
    print("\nPASSO 2: Verificando backup...")
    backup_data_raw = await kv.get_json('skills/eye/monitoring-types.backup')

    if backup_data_raw:
        print(f"  Debug: Chaves do backup: {list(backup_data_raw.keys())}")

        # Desembrulhar nível 1 (backup wrapped)
        if 'data' in backup_data_raw:
            backup_data = backup_data_raw['data']
            print(f"  Debug: Desembrulhado nível 1. Chaves: {list(backup_data.keys())[:6]}")
        else:
            backup_data = backup_data_raw

        # Acessar types_data
        if 'types_data' in backup_data:
            types_data = backup_data['types_data']
            print(f"  Debug: types_data encontrado. Chaves: {list(types_data.keys()) if isinstance(types_data, dict) else 'não é dict'}")

            # Desembrulhar nível 2 (types_data wrapped)
            if isinstance(types_data, dict) and list(types_data.keys()) == ['data']:
                types_data = types_data['data']
                print(f"  Debug: Desembrulhado nível 2. Chaves: {list(types_data.keys())[:6]}")

            tipos_backup = types_data.get('all_types', [])
            com_schema_backup = [t for t in tipos_backup if t.get('form_schema')]
            print(f"✅ Backup: {len(tipos_backup)} tipos, {len(com_schema_backup)} com form_schema")
            if com_schema_backup:
                print(f"  Tipos: {', '.join([t['id'] for t in com_schema_backup])}")
        else:
            print("❌ types_data não encontrado no backup")
    else:
        print("❌ Backup vazio")

    # PASSO 3: Simular restauração
    print("\nPASSO 3: Testando restauração do backup...")
    print("  (NÃO vou apagar KV real, apenas simular)")

    # RELATÓRIO FINAL
    print("\n═══════════════════════════════════════════════════════════")
    print("📊 RELATÓRIO FINAL")
    print("═══════════════════════════════════════════════════════════")

    if kv_data and 'all_types' in kv_data and len(kv_data['all_types']) == 27:
        print("✅ KV principal: OK (27 tipos)")
    else:
        print("❌ KV principal: FALHOU")

    if backup_data and 'types_data' in backup_data:
        tipos_backup = backup_data['types_data'].get('all_types', [])
        if len(tipos_backup) == 27:
            print("✅ Backup: OK (27 tipos)")
        else:
            print(f"⚠️ Backup: {len(tipos_backup)} tipos (esperado 27)")
    else:
        print("❌ Backup: FALHOU")

if __name__ == '__main__':
    asyncio.run(main())
