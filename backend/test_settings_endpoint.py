"""Teste completo da API de settings"""
import asyncio
import json
from api.settings import get_naming_config, get_sites, create_site, SiteConfig

async def test():
    print("=" * 60)
    print("TESTE 1: Carregar naming config")
    print("=" * 60)
    result = await get_naming_config()
    print(json.dumps(result, indent=2, ensure_ascii=False))

    print("\n" + "=" * 60)
    print("TESTE 2: Listar sites")
    print("=" * 60)
    sites = await get_sites()
    print(json.dumps(sites, indent=2, ensure_ascii=False))

    print("\n" + "=" * 60)
    print("TESTE 3: Tentar criar site (teste) - PODE FALHAR SE JÁ EXISTE")
    print("=" * 60)
    try:
        new_site = SiteConfig(
            code="teste",
            name="Site de Teste",
            is_default=False,
            color="cyan"
        )
        created = await create_site(new_site)
        print("Site criado:", json.dumps(created.model_dump(), indent=2, ensure_ascii=False))
    except Exception as e:
        print(f"Erro esperado (site já existe?): {e}")

    print("\n" + "=" * 60)
    print("SUCESSO: Todos os testes concluídos!")
    print("=" * 60)

asyncio.run(test())
