"""
Script temporário para popular valores de cod_localidade
"""
import asyncio
import sys
from core.reference_values_manager import ReferenceValuesManager

# Valores a serem cadastrados
VALORES_COD_LOCALIDADE = [
    "GSBAL",
    "GSCOLAGENC",
    "GSPMW",
    "GSPONLUZIM",
    "GSSLZ",
    "GSSLZPVALE",
    "GSURU",
    "GWPMWESCSC",
    "GWPONAGAPE",
    "GWPONEASAG",
    "GWPONESEDE",
    "GWPONFPOCE",
    "GWSRTCEDRO",
    "LCRIOESCRI",
    "LCRIOMATRI",
    "MAPMW",
    "RARIOESCRI",
    "RARIOMATRI",
    "RRNAT",
    "SCCHCESCRI",
    "SCPMWESCRI",
    "SKAZURDTC",
    "SKGENESDTC",
    "SKPMW",
    "SKVULTDTC",
    "STPMW",
    "WGPMWESCRI",
]


async def populate_cod_localidade():
    """Popula valores de cod_localidade via ReferenceValuesManager"""
    manager = ReferenceValuesManager()

    print(f"[INFO] Cadastrando {len(VALORES_COD_LOCALIDADE)} codigos de localidade...\n")

    created_count = 0
    existing_count = 0

    for valor in VALORES_COD_LOCALIDADE:
        created, normalized, message = await manager.ensure_value(
            field_name="cod_localidade",
            value=valor,
            user="admin"
        )

        if created:
            print(f"[OK] CRIADO: {normalized}")
            created_count += 1
        else:
            print(f"[INFO] JA EXISTE: {normalized}")
            existing_count += 1

    print(f"\n{'='*60}")
    print(f"CONCLUIDO!")
    print(f"   - Criados: {created_count}")
    print(f"   - Ja existiam: {existing_count}")
    print(f"   - Total: {len(VALORES_COD_LOCALIDADE)}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    try:
        asyncio.run(populate_cod_localidade())
        sys.exit(0)
    except KeyboardInterrupt:
        print("\n[CANCEL] Cancelado pelo usuario")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] ERRO: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
