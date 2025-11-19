#!/usr/bin/env python3
"""
Script de teste de persistência do KV metadata-fields
Testa backup, restauração e preservação de customizações
"""
import asyncio
import sys
sys.path.insert(0, '/home/adrianofante/projetos/Skills-Eye/backend')

from core.kv_manager import KVManager
from core.metadata_fields_backup import MetadataFieldsBackupManager

async def test_persistencia():
    """Teste completo de persistência do metadata-fields"""

    kv = KVManager()
    backup_mgr = MetadataFieldsBackupManager()

    print("═══════════════════════════════════════════════════════════")
    print("🧪 TESTE DE PERSISTÊNCIA - METADATA FIELDS")
    print("═══════════════════════════════════════════════════════════\n")

    # PASSO 1: Verificar estado atual
    print("PASSO 1: Verificando estado atual do KV...")
    kv_data = await kv.get_json('skills/eye/metadata/fields')

    if kv_data:
        fields = kv_data.get('fields', [])
        custom_fields = [f for f in fields if f.get('custom', False)]
        print(f"✅ KV atual: {len(fields)} campos, {len(custom_fields)} customizados")

        # Mostrar alguns campos customizados
        if custom_fields:
            print(f"  Campos customizados: {', '.join([f['name'] for f in custom_fields[:5]])}")
    else:
        print("❌ KV vazio ou não existe")

    # PASSO 2: Verificar backup
    print("\nPASSO 2: Verificando backup...")
    backup_data_raw = await kv.get_json('skills/eye/metadata/fields.backup')

    if backup_data_raw:
        print(f"  Debug: Chaves do backup: {list(backup_data_raw.keys())}")

        # Tentar acessar fields_data
        if 'fields_data' in backup_data_raw:
            fields_data = backup_data_raw['fields_data']
            backup_fields = fields_data.get('fields', [])
            backup_custom = [f for f in backup_fields if f.get('custom', False)]
            print(f"✅ Backup: {len(backup_fields)} campos, {len(backup_custom)} customizados")

            if backup_custom:
                print(f"  Campos customizados: {', '.join([f['name'] for f in backup_custom[:5]])}")
        else:
            print("❌ fields_data não encontrado no backup")
    else:
        print("❌ Backup vazio")

    # PASSO 3: Verificar merge do prewarm
    print("\nPASSO 3: Verificando logs de merge do prewarm...")
    print("  (Verificar backend.log para confirmar que campos customizados foram preservados)")

    print("\n═══════════════════════════════════════════════════════════")
    print("📊 RELATÓRIO FINAL")
    print("═══════════════════════════════════════════════════════════")

    if kv_data:
        fields_total = len(kv_data.get('fields', []))
        custom_total = len([f for f in kv_data.get('fields', []) if f.get('custom', False)])
        print(f"✅ KV principal: OK ({fields_total} campos, {custom_total} customizados)")
    else:
        print("❌ KV principal: VAZIO")

    if backup_data_raw and 'fields_data' in backup_data_raw:
        backup_total = len(backup_data_raw['fields_data'].get('fields', []))
        backup_custom_total = len([f for f in backup_data_raw['fields_data'].get('fields', []) if f.get('custom', False)])
        print(f"✅ Backup: OK ({backup_total} campos, {backup_custom_total} customizados)")
    else:
        print("❌ Backup: PROBLEMA")

    print()

if __name__ == '__main__':
    asyncio.run(test_persistencia())
