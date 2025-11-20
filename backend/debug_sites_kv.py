import asyncio
import logging
from core.kv_manager import KVManager

# Configurar logging
logging.basicConfig(level=logging.INFO)

async def check_sites_kv():
    kv = KVManager()
    try:
        data = await kv.get_json('skills/eye/metadata/sites')
        print("--- CONTEÚDO KV skills/eye/metadata/sites ---")
        import json
        print(json.dumps(data, indent=2))
    except Exception as e:
        print(f"Erro ao ler KV: {e}")

if __name__ == "__main__":
    asyncio.run(check_sites_kv())

