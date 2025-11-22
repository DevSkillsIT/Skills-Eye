#!/usr/bin/env python3
"""
Script para adicionar naming_strategy e suffix_enabled ao JSON de sites existente

OBJETIVO: Centralizar TODA configuração no JSON skills/eye/metadata/sites
          ao invés de criar outro KV separado (skills/eye/settings/naming-strategy)

ESTRUTURA FINAL:
{
    "data": {
        "sites": [...],
        "naming_config": {
            "strategy": "option2",
            "suffix_enabled": true,
            "description": "option1: Nomes iguais + filtros | option2: Nomes diferentes por site"
        }
    },
    "meta": {
        "created_at": "...",
        "updated_at": "...",
        "version": "2.0.0"
    }
}
"""
import asyncio
import sys
from datetime import datetime
sys.path.insert(0, '/home/adrianofante/projetos/Skills-Eye/backend')

from core.kv_manager import KVManager


async def main():
    print("=" * 80)
    print("ADICIONAR naming_config AO JSON DE SITES")
    print("=" * 80)
    
    kv = KVManager()
    
    # PASSO 1: Ler JSON atual de sites
    print("\n📖 Lendo JSON atual de sites...")
    sites_data = await kv.get_json("skills/eye/metadata/sites")
    
    if not sites_data:
        print("❌ ERRO: JSON de sites não encontrado no KV")
        return
    
    print(f"✅ JSON carregado: {len(sites_data.get('data', {}).get('sites', []))} sites")
    
    # PASSO 2: Adicionar naming_config na seção data
    if "data" not in sites_data:
        sites_data["data"] = {"sites": []}
    
    sites_data["data"]["naming_config"] = {
        "strategy": "option2",
        "suffix_enabled": True,
        "description": "option1: Nomes iguais + filtros | option2: Nomes diferentes por site"
    }
    
    # PASSO 3: Atualizar meta
    if "meta" not in sites_data:
        sites_data["meta"] = {}
    
    sites_data["meta"]["updated_at"] = datetime.now().isoformat()
    sites_data["meta"]["version"] = "2.0.0"
    sites_data["meta"]["changelog"] = "Adicionado naming_config (strategy, suffix_enabled)"
    
    # PASSO 4: Salvar no KV
    print("\n💾 Salvando JSON atualizado...")
    success = await kv.put_json("skills/eye/metadata/sites", sites_data)
    
    if success:
        print("✅ JSON atualizado com sucesso!")
        print("\n📋 Estrutura final:")
        print(f"   - sites: {len(sites_data['data']['sites'])}")
        print(f"   - naming_config.strategy: {sites_data['data']['naming_config']['strategy']}")
        print(f"   - naming_config.suffix_enabled: {sites_data['data']['naming_config']['suffix_enabled']}")
    else:
        print("❌ ERRO ao salvar JSON")
    
    # PASSO 5: REMOVER o KV desnecessário (se existir)
    print("\n🗑️  Removendo KV desnecessário skills/eye/settings/naming-strategy...")
    try:
        # Não vou implementar delete aqui, mas documenta que deve ser removido
        print("⚠️  MANUAL: Remova skills/eye/settings/naming-strategy via Consul UI")
        print("   Não é mais necessário - tudo está em skills/eye/metadata/sites")
    except Exception as e:
        print(f"⚠️  {e}")


if __name__ == "__main__":
    asyncio.run(main())
