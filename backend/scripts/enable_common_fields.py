"""
Script para habilitar auto-cadastro em campos comuns de Reference Values.

Executa UMA VEZ para configurar campos iniciais.
Após isso, use a interface web (Metadata Fields) para gerenciar.
"""

import asyncio
import json
from core.kv_manager import KVManager

# Campos que devem ter auto-cadastro HABILITADO por padrão
COMMON_FIELDS_TO_ENABLE = [
    'company',
    'datacenter',
    'environment',
    'site',
    'cluster',
    'localizacao',
    'cidade',
    'estado',
    'pais',
    'regiao',
    'provedor',
    'vendor',
    'fabricante',
    'tipo_dispositivo',
    'sistema_operacional',
]

async def enable_fields():
    """Habilita auto-cadastro em campos comuns."""
    kv = KVManager()

    # Carregar configuração atual (caminho correto do KV)
    config = await kv.get_json('skills/eye/metadata/fields')

    if not config or 'fields' not in config:
        print("❌ Erro: Configuração de campos não encontrada no KV")
        print("   Execute a extração de campos do Prometheus primeiro!")
        print("   Ou acesse a página Metadata Fields para disparar extração automática")
        return

    fields = config['fields']
    print(f"📋 Total de campos no KV: {len(fields)}")

    # Contar campos habilitados antes
    enabled_before = sum(1 for f in fields if f.get('available_for_registration', False))
    print(f"✅ Campos com auto-cadastro ANTES: {enabled_before}")

    # Habilitar campos comuns
    enabled_count = 0
    for field in fields:
        field_name = field.get('name')

        if field_name in COMMON_FIELDS_TO_ENABLE:
            # Verificar se já está habilitado
            if not field.get('available_for_registration', False):
                field['available_for_registration'] = True
                enabled_count += 1
                print(f"   ✓ Habilitado: {field_name}")
            else:
                print(f"   ⏭️  Já habilitado: {field_name}")

    # Salvar de volta no KV
    if enabled_count > 0:
        metadata = {
            "updated_by": "enable_common_fields.py",
            "action": "bulk_enable_auto_registration",
            "fields_enabled": enabled_count
        }

        success = await kv.put_json('skills/eye/metadata/fields', config, metadata)

        if success:
            print(f"\n✅ SUCESSO: {enabled_count} campos habilitados para auto-cadastro")
            print(f"   Total com auto-cadastro: {enabled_before + enabled_count}")
            print("\n🔄 PRÓXIMO PASSO: Recarregue a página Reference Values no navegador")
        else:
            print("\n❌ Erro ao salvar configuração no KV")
    else:
        print(f"\n⏭️  Nenhum campo novo habilitado (todos já estavam habilitados)")

    # Listar campos que NÃO foram habilitados (para referência)
    disabled_fields = [f['name'] for f in fields if not f.get('available_for_registration', False)]
    if disabled_fields:
        print(f"\nℹ️  Campos ainda DESABILITADOS ({len(disabled_fields)}):")
        for name in disabled_fields[:10]:  # Mostrar apenas primeiros 10
            print(f"   - {name}")
        if len(disabled_fields) > 10:
            print(f"   ... e mais {len(disabled_fields) - 10} campos")
        print("\n   💡 Para habilitar outros campos, use a página Metadata Fields")

if __name__ == '__main__':
    print("=" * 70)
    print("  HABILITANDO CAMPOS COMUNS PARA REFERENCE VALUES")
    print("=" * 70)
    print()

    asyncio.run(enable_fields())

    print("\n" + "=" * 70)
