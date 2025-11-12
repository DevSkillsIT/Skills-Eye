#!/usr/bin/env python3
"""
MIGRAÇÃO: .env → KV (naming-strategy)

Migra configurações de naming do .env para o KV.
Path: skills/eye/settings/naming-strategy

Data: 2025-11-12
"""

import asyncio
import sys
import os
from datetime import datetime

# Adicionar backend ao path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from backend.core.kv_manager import KVManager


async def migrate_naming_strategy_to_kv():
    """
    Migra NAMING_STRATEGY do .env para KV
    
    KV Path: skills/eye/settings/naming-strategy
    
    Estrutura:
    {
      "naming_strategy": "option2",
      "suffix_enabled": true,
      "description": "option1: Nomes iguais + filtros | option2: Nomes diferentes por site",
      "meta": {
        "created_at": "2025-11-12T...",
        "updated_at": "2025-11-12T...",
        "version": "1.0.0",
        "migrated_from": ".env"
      }
    }
    """
    
    print("=" * 80)
    print("MIGRAÇÃO: .env → KV (naming-strategy)")
    print("=" * 80)
    
    # Ler valores atuais do .env
    naming_strategy = os.getenv("NAMING_STRATEGY", "option2")
    suffix_enabled_str = os.getenv("SITE_SUFFIX_ENABLED", "true").lower()
    suffix_enabled = suffix_enabled_str == "true"
    
    print(f"\n📋 Valores do .env:")
    print(f"  NAMING_STRATEGY: {naming_strategy}")
    print(f"  SITE_SUFFIX_ENABLED: {suffix_enabled}")
    
    # Criar estrutura para KV
    now = datetime.now().isoformat()
    naming_config = {
        "naming_strategy": naming_strategy,
        "suffix_enabled": suffix_enabled,
        "description": "option1: Nomes iguais + filtros | option2: Nomes diferentes por site",
        "meta": {
            "created_at": now,
            "updated_at": now,
            "version": "1.0.0",
            "migrated_from": ".env",
            "notes": "Migrado automaticamente do .env para tornar configuração dinâmica"
        }
    }
    
    print(f"\n📦 Estrutura para KV:")
    import json
    print(json.dumps(naming_config, indent=2))
    
    # Verificar se já existe no KV
    kv = KVManager()
    kv_path = "skills/eye/settings/naming-strategy"
    
    try:
        existing = await kv.get_json(kv_path)
        if existing:
            print(f"\n⚠️  AVISO: Configuração já existe no KV!")
            print(f"  Path: {kv_path}")
            print(f"  Valor atual:")
            print(json.dumps(existing, indent=2))
            
            # Perguntar se deseja sobrescrever
            response = input("\n❓ Deseja sobrescrever? (s/N): ")
            if response.lower() != 's':
                print("❌ Migração cancelada pelo usuário")
                return False
    except:
        print(f"\n✅ Path {kv_path} não existe no KV (primeira migração)")
    
    # Salvar no KV
    print(f"\n💾 Salvando no KV...")
    print(f"  Path: {kv_path}")
    
    try:
        await kv.put_json(kv_path, naming_config)
        print(f"✅ Configuração salva com sucesso!")
        
        # Verificar se salvou corretamente
        print(f"\n🔍 Verificando...")
        saved = await kv.get_json(kv_path)
        
        if saved:
            print(f"✅ Verificação OK!")
            print(f"  naming_strategy: {saved.get('naming_strategy')}")
            print(f"  suffix_enabled: {saved.get('suffix_enabled')}")
            print(f"  version: {saved.get('meta', {}).get('version')}")
            
            print(f"\n" + "=" * 80)
            print("✅ MIGRAÇÃO CONCLUÍDA COM SUCESSO!")
            print("=" * 80)
            print(f"\n📌 PRÓXIMOS PASSOS:")
            print(f"  1. Backend usará KV ao invés de .env")
            print(f"  2. Fallback para .env se KV indisponível")
            print(f"  3. Configuração pode ser alterada via API")
            print("=" * 80)
            
            return True
        else:
            print(f"❌ Erro: Não foi possível verificar dados salvos")
            return False
    
    except Exception as e:
        print(f"❌ Erro ao salvar no KV: {e}")
        return False


async def main():
    """Função principal"""
    success = await migrate_naming_strategy_to_kv()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
