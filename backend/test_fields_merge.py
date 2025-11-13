#!/usr/bin/env python3
"""
Script para testar persistência de customizações de FIELDS no KV

TESTE:
1. Customiza campos com required=True, auto_register=True, etc
2. Força extração do Prometheus (simula reinício)
3. Verifica se customizações foram PRESERVADAS após merge

USO:
    python3 test_fields_merge.py
"""

import asyncio
import sys
from pathlib import Path

# Adicionar backend ao path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.kv_manager import KVManager


async def test_merge_preservation():
    """Testa se merge preserva customizações"""
    
    kv = KVManager()
    
    print("=" * 80)
    print("TESTE DE PERSISTÊNCIA DE CUSTOMIZAÇÕES - FIELDS KV")
    print("=" * 80)
    print()
    
    # PASSO 1: Buscar configuração atual
    print("📋 PASSO 1: Buscar configuração atual do KV...")
    fields_config = await kv.get_json('skills/eye/metadata/fields')
    
    if not fields_config or 'fields' not in fields_config:
        print("❌ ERRO: KV vazio ou sem estrutura 'fields'")
        return False
    
    fields = fields_config['fields']
    print(f"✅ {len(fields)} campos encontrados no KV")
    print()
    
    # PASSO 2: Selecionar 3 campos para customizar
    print("📋 PASSO 2: Customizar 3 campos de teste...")
    
    test_customizations = []
    
    for i, field in enumerate(fields[:3]):  # Primeiros 3 campos
        field_name = field['name']
        
        # Salvar estado original
        original = {
            'name': field_name,
            'required': field.get('required', False),
            'auto_register': field.get('auto_register', False),
            'category': field.get('category', 'extra'),
            'order': field.get('order', 999),
            'description': field.get('description', ''),
        }
        
        # Aplicar customizações de teste
        field['required'] = True
        field['auto_register'] = True
        field['category'] = 'test_category'
        field['order'] = 100 + i
        field['description'] = f'TESTE: Customização persistente do campo {field_name}'
        
        test_customizations.append({
            'field_name': field_name,
            'original': original,
            'customized': {
                'required': True,
                'auto_register': True,
                'category': 'test_category',
                'order': 100 + i,
                'description': f'TESTE: Customização persistente do campo {field_name}',
            }
        })
        
        print(f"  ✅ Campo '{field_name}' customizado:")
        print(f"     - required: {original['required']} → True")
        print(f"     - auto_register: {original['auto_register']} → True")
        print(f"     - category: {original['category']} → test_category")
        print(f"     - order: {original['order']} → {100 + i}")
    
    print()
    
    # PASSO 3: Salvar configuração customizada
    print("📋 PASSO 3: Salvar configuração customizada no KV...")
    
    fields_config['fields'] = fields
    fields_config['last_updated'] = __import__('datetime').datetime.now().isoformat()
    fields_config['source'] = 'test_script_customization'
    
    success = await kv.put_json('skills/eye/metadata/fields', fields_config)
    
    if not success:
        print("❌ ERRO: Falha ao salvar no KV")
        return False
    
    print("✅ Configuração customizada salva no KV")
    print()
    
    # PASSO 4: Simular extração do Prometheus (que fará merge)
    print("📋 PASSO 4: Simular extração do Prometheus (merge)...")
    print("   ⚠️  Este passo requer que o backend execute o merge")
    print("   💡 Solução: Limpar cache e fazer requisição ao /metadata-fields/")
    print()
    
    # Limpar cache em memória do backend (forçar reload)
    print("📋 PASSO 5: Verificar se customizações PERSISTEM após merge...")
    print("   Execute manualmente:")
    print("   1. Reiniciar backend: bash scripts/deployment/restart-backend.sh")
    print("   2. Acessar: curl http://localhost:5000/api/v1/metadata-fields/")
    print("   3. Verificar logs do backend para mensagens [MERGE]")
    print()
    
    # PASSO 6: Mostrar resumo do teste
    print("=" * 80)
    print("RESUMO DO TESTE")
    print("=" * 80)
    print()
    print("✅ Customizações aplicadas nos seguintes campos:")
    for custom in test_customizations:
        print(f"   - {custom['field_name']}")
    print()
    print("📝 PRÓXIMOS PASSOS MANUAIS:")
    print("   1. Reiniciar backend")
    print("   2. Verificar logs: tail -f backend/backend.log | grep MERGE")
    print("   3. Fazer requisição: curl http://localhost:5000/api/v1/metadata-fields/")
    print("   4. Verificar se campos ainda têm required=True, auto_register=True")
    print()
    print("🔍 VALIDAÇÃO:")
    print("   Se merge funcionou corretamente, você verá nos logs:")
    print("   - [MERGE] Fazendo merge com X campos existentes no KV")
    print("   - [MERGE] Campo 'X': customizações preservadas do KV")
    print()
    
    return True


async def verify_customizations():
    """Verifica se customizações persistiram"""
    
    kv = KVManager()
    
    print("=" * 80)
    print("VERIFICAÇÃO DE CUSTOMIZAÇÕES")
    print("=" * 80)
    print()
    
    fields_config = await kv.get_json('skills/eye/metadata/fields')
    
    if not fields_config or 'fields' not in fields_config:
        print("❌ ERRO: KV vazio")
        return False
    
    fields = fields_config['fields']
    
    # Buscar campos com category='test_category' (customizações do teste)
    test_fields = [f for f in fields if f.get('category') == 'test_category']
    
    if not test_fields:
        print("❌ Nenhum campo com customizações de teste encontrado")
        print("   Isso significa que o merge NÃO preservou as customizações!")
        return False
    
    print(f"✅ {len(test_fields)} campo(s) com customizações de teste encontrado(s):")
    print()
    
    for field in test_fields:
        print(f"📌 Campo: {field['name']}")
        print(f"   - required: {field.get('required', False)}")
        print(f"   - auto_register: {field.get('auto_register', False)}")
        print(f"   - category: {field.get('category', 'N/A')}")
        print(f"   - order: {field.get('order', 'N/A')}")
        print(f"   - description: {field.get('description', 'N/A')[:80]}...")
        print()
    
    # Verificar se valores estão corretos
    all_correct = True
    for field in test_fields:
        if not field.get('required'):
            print(f"❌ Campo '{field['name']}': required deveria ser True")
            all_correct = False
        if not field.get('auto_register'):
            print(f"❌ Campo '{field['name']}': auto_register deveria ser True")
            all_correct = False
        if field.get('category') != 'test_category':
            print(f"❌ Campo '{field['name']}': category deveria ser 'test_category'")
            all_correct = False
    
    if all_correct:
        print("✅ SUCESSO: Todas as customizações foram PRESERVADAS após merge!")
    else:
        print("❌ FALHA: Algumas customizações foram PERDIDAS!")
    
    return all_correct


async def cleanup_test():
    """Remove customizações de teste"""
    
    kv = KVManager()
    
    print("=" * 80)
    print("LIMPEZA DAS CUSTOMIZAÇÕES DE TESTE")
    print("=" * 80)
    print()
    
    fields_config = await kv.get_json('skills/eye/metadata/fields')
    
    if not fields_config or 'fields' not in fields_config:
        print("❌ ERRO: KV vazio")
        return False
    
    fields = fields_config['fields']
    
    # Remover category='test_category'
    modified = 0
    for field in fields:
        if field.get('category') == 'test_category':
            field['category'] = 'extra'  # Voltar ao padrão
            field['required'] = False
            field['auto_register'] = False
            field['order'] = 999
            field['description'] = ''
            modified += 1
    
    if modified > 0:
        fields_config['last_updated'] = __import__('datetime').datetime.now().isoformat()
        fields_config['source'] = 'test_cleanup'
        await kv.put_json('skills/eye/metadata/fields', fields_config)
        print(f"✅ {modified} campo(s) limpo(s)")
    else:
        print("ℹ️  Nenhum campo de teste para limpar")
    
    return True


async def main():
    """Menu principal"""
    
    if len(sys.argv) > 1:
        action = sys.argv[1]
    else:
        print("Escolha uma ação:")
        print("  1. Aplicar customizações de teste")
        print("  2. Verificar se customizações persistiram")
        print("  3. Limpar customizações de teste")
        print()
        choice = input("Opção (1-3): ").strip()
        
        action = {'1': 'customize', '2': 'verify', '3': 'cleanup'}.get(choice)
    
    if action == 'customize':
        success = await test_merge_preservation()
    elif action == 'verify':
        success = await verify_customizations()
    elif action == 'cleanup':
        success = await cleanup_test()
    else:
        print("❌ Ação inválida. Use: customize, verify ou cleanup")
        sys.exit(1)
    
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    asyncio.run(main())
