"""
Script para popular o campo 'tipo_dispositivo_abrev' com valores pré-definidos
"""
import asyncio
import sys
from core.reference_values_manager import ReferenceValuesManager

VALORES_TIPO_DISPOSITIVO_ABREV = [
    "ALLIN",
    "DESKT",
    "MINIP",
    "NOTEB",
    "PABXI",
    "SRVFL",
    "SRVFW",
    "SRVRA",
    "SRVTO",
    "SRVLI",
    "SRVWI",
    "VMACH",
    "ACPOI",
    "BIOME",
    "CAMIP",
    "CAMWI",
    "COLDA",
    "DIOUT",
    "DVRIP",
    "FWUTM",
    "HUBHU",
    "MASRV",
    "NOBRE",
    "NVRCA",
    "PABXA",
    "PABXH",
    "POREL",
    "RELPO",
    "ROTEA",
    "ROTWI",
    "STORA",
    "STNAS",
    "SWITC",
    "SWITG",
    "SWIPO",
    "SWIPG",
    "TELEV",
    "APPTP",
    "IMPRE",
    "IMMLT",
    "SCANN",
    "ATFXO",
    "ATFXS",
    "TELIP",
    "TELPO",
    "TELSF",
    "CONAC",
]

async def populate_tipo_dispositivo_abrev():
    manager = ReferenceValuesManager()

    print(f"[INFO] Cadastrando {len(VALORES_TIPO_DISPOSITIVO_ABREV)} tipos de dispositivo (abreviados)...")

    created_count = 0
    existing_count = 0

    for valor in VALORES_TIPO_DISPOSITIVO_ABREV:
        try:
            created, normalized, message = await manager.ensure_value(
                field_name="tipo_dispositivo_abrev",
                value=valor,
                user="admin"
            )

            if created:
                print(f"[OK] CRIADO: {normalized}")
                created_count += 1
            else:
                print(f"[CANCEL] JA EXISTE: {normalized}")
                existing_count += 1

        except Exception as e:
            print(f"[ERROR] Erro ao cadastrar '{valor}': {e}")

    print("\n" + "="*60)
    print("CONCLUIDO!")
    print(f"   - Criados: {created_count}")
    print(f"   - Ja existiam: {existing_count}")
    print(f"   - Total: {len(VALORES_TIPO_DISPOSITIVO_ABREV)}")
    print("="*60)

if __name__ == "__main__":
    asyncio.run(populate_tipo_dispositivo_abrev())
