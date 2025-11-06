"""
Script temporário para popular valores de fabricante
"""
import asyncio
import sys
from core.reference_values_manager import ReferenceValuesManager

# Valores a serem cadastrados
VALORES_FABRICANTE = [
    "3COM",
    "ACER",
    "APPLE",
    "ASRock",
    "ASUS",
    "ASUSTeK",
    "BIXOLON",
    "BROTHER",
    "CISCO",
    "CONTROL ID",
    "DAINIPPON",
    "Default String",
    "Dell",
    "D-LINK",
    "EPSON",
    "Google",
    "Grandstream",
    "HIKVISION",
    "HP",
    "HUAWEI",
    "HYPER-V",
    "IBM",
    "Intel",
    "INTELBRAS",
    "IOMEGA",
    "ITAUTEC",
    "JABRA",
    "KingVoice",
    "KODAK",
    "KONICA MINOLTA",
    "Lenovo",
    "LG",
    "LOGITECH",
    "MICROSOFT",
    "Microsoft Hyper-V",
    "MIKROTIK",
    "MULTILASER",
    "OUTRA",
    "PC MONTADO",
    "PCWARE",
    "PLANTRONICS",
    "Positivo",
    "RICOH",
    "SAMSUNG",
    "Semp Toshiba",
    "SKILLS",
    "SKILLS PC",
    "SONY",
    "SYMBOL",
    "System manufacturer",
    "Tenda",
    "TO BE FILLED BY O.E.M.",
    "TOTO LINK",
    "TP-LINK",
    "Ubiquiti",
    "VAIO",
    "Virtualizado",
    "Vmware",
    "ZEBRA",
    "ZYXEL",
    "SAGEMCOM",
    "DATACOM",
    "Goldentec",
]


async def populate_fabricante():
    """Popula valores de fabricante via ReferenceValuesManager"""
    manager = ReferenceValuesManager()

    print(f"[INFO] Cadastrando {len(VALORES_FABRICANTE)} fabricantes...\n")

    created_count = 0
    existing_count = 0

    for valor in VALORES_FABRICANTE:
        created, normalized, message = await manager.ensure_value(
            field_name="fabricante",
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
    print(f"   - Total: {len(VALORES_FABRICANTE)}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    try:
        asyncio.run(populate_fabricante())
        sys.exit(0)
    except KeyboardInterrupt:
        print("\n[CANCEL] Cancelado pelo usuario")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] ERRO: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
