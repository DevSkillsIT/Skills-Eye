"""
Script de teste COMPLETO de persistência do KV.

Testa se TODOS os 14 campos de customização são preservados:
1. available_for_registration
2. display_name
3. field_type
4. category
5. description
6. order
7. required
8. editable
9. show_in_table
10. show_in_dashboard
11. show_in_form
12. show_in_services
13. show_in_exporters
14. show_in_blackbox
"""

import asyncio
import json
from core.kv_manager import KVManager

# Valores CUSTOMIZADOS que vamos testar (não-padrão)
CUSTOMIZACOES_TESTE = {
    'company': {
        'available_for_registration': True,
        'display_name': 'EMPRESA CUSTOMIZADA',
        'field_type': 'text',  # Mudando de select para text
        'category': 'basic',
        'description': 'Descrição customizada da empresa',
        'order': 100,
        'required': True,
        'editable': False,
        'show_in_table': False,  # Mudando para false
        'show_in_dashboard': True,
        'show_in_form': False,  # Mudando para false
        'show_in_services': False,  # Mudando para false
        'show_in_exporters': True,
        'show_in_blackbox': False,  # Mudando para false
    },
    'vendor': {
        'available_for_registration': True,
        'display_name': 'FORNECEDOR TESTE',
        'field_type': 'string',  # Mudando de select para string
        'category': 'infrastructure',
        'description': 'Teste de descrição do fornecedor',
        'order': 50,
        'required': False,
        'editable': True,
        'show_in_table': True,
        'show_in_dashboard': False,  # Mudando para false
        'show_in_form': True,
        'show_in_services': True,
        'show_in_exporters': False,  # Mudando para false
        'show_in_blackbox': True,
    },
    'cidade': {
        'available_for_registration': True,
        'display_name': 'CIDADE MODIFICADA',
        'field_type': 'select',
        'category': 'location',  # Mudando categoria
        'description': 'Nova descrição cidade',
        'order': 25,
        'required': True,  # Mudando para true
        'editable': False,  # Mudando para false
        'show_in_table': True,
        'show_in_dashboard': True,
        'show_in_form': False,  # Mudando para false
        'show_in_services': False,  # Mudando para false
        'show_in_exporters': False,  # Mudando para false
        'show_in_blackbox': True,
    }
}


async def aplicar_customizacoes():
    """Aplica customizações de teste no KV"""
    kv = KVManager()

    # Carregar config atual
    config = await kv.get_json('skills/eye/metadata/fields')

    if not config or 'fields' not in config:
        print("❌ Erro: KV vazio")
        return False

    fields = config['fields']
    modificados = 0

    print("\n" + "="*70)
    print("  APLICANDO CUSTOMIZAÇÕES DE TESTE")
    print("="*70 + "\n")

    # Aplicar customizações
    for field in fields:
        field_name = field.get('name')

        if field_name in CUSTOMIZACOES_TESTE:
            customizacoes = CUSTOMIZACOES_TESTE[field_name]

            print(f"📝 Customizando campo: {field_name}")
            for key, value in customizacoes.items():
                old_value = field.get(key)
                field[key] = value
                if old_value != value:
                    print(f"   • {key:30} {old_value!r:20} → {value!r}")

            modificados += 1
            print()

    # Salvar de volta
    success = await kv.put_json('skills/eye/metadata/fields', config)

    if success:
        print(f"✅ {modificados} campos customizados salvos no KV\n")
        return True
    else:
        print("❌ Erro ao salvar no KV\n")
        return False


async def verificar_persistencia():
    """Verifica se customizações foram preservadas"""
    kv = KVManager()

    # Carregar config
    config = await kv.get_json('skills/eye/metadata/fields')

    if not config or 'fields' not in config:
        print("❌ Erro: KV vazio")
        return

    fields = config['fields']

    print("\n" + "="*70)
    print("  VERIFICANDO PERSISTÊNCIA DAS CUSTOMIZAÇÕES")
    print("="*70 + "\n")

    total_verificacoes = 0
    erros = 0

    for field in fields:
        field_name = field.get('name')

        if field_name in CUSTOMIZACOES_TESTE:
            esperado = CUSTOMIZACOES_TESTE[field_name]

            print(f"🔍 Verificando: {field_name}")
            campo_ok = True

            for key, valor_esperado in esperado.items():
                valor_atual = field.get(key)
                total_verificacoes += 1

                if valor_atual == valor_esperado:
                    print(f"   ✅ {key:30} = {valor_atual!r}")
                else:
                    print(f"   ❌ {key:30} esperado: {valor_esperado!r}, atual: {valor_atual!r}")
                    erros += 1
                    campo_ok = False

            if campo_ok:
                print(f"   ✓ Campo OK\n")
            else:
                print(f"   ✗ Campo com ERROS\n")

    print("="*70)
    print(f"Total de verificações: {total_verificacoes}")
    print(f"Erros encontrados: {erros}")

    if erros == 0:
        print("\n🎉 SUCESSO: Todas as customizações foram PRESERVADAS!")
    else:
        print(f"\n⚠️  FALHA: {erros} campos NÃO foram preservados!")

    print("="*70 + "\n")

    return erros == 0


async def main():
    import sys

    if len(sys.argv) < 2:
        print("Uso:")
        print("  python test_persistencia_completa.py aplicar   - Aplica customizações de teste")
        print("  python test_persistencia_completa.py verificar - Verifica se persistiram")
        return

    comando = sys.argv[1]

    if comando == 'aplicar':
        await aplicar_customizacoes()
        print("\n🔄 PRÓXIMO PASSO:")
        print("   1. Reinicie o backend")
        print("   2. Execute: python test_persistencia_completa.py verificar\n")

    elif comando == 'verificar':
        sucesso = await verificar_persistencia()
        if not sucesso:
            exit(1)

    else:
        print(f"❌ Comando desconhecido: {comando}")
        print("   Use 'aplicar' ou 'verificar'")


if __name__ == '__main__':
    asyncio.run(main())
