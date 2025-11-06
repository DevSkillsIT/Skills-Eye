"""
Script para popular o campo 'tipo' com valores pré-definidos
"""
import asyncio
import sys
from core.reference_values_manager import ReferenceValuesManager

VALORES_TIPO = [
    "ALL IN ONE",
    "DESKTOP",
    "MINI PC",
    "NOTEBOOK",
    "PABX IP",
    "SERVIDOR FÍSICO LIN.",
    "SERVIDOR FÍSICO WIN.",
    "SERVIDOR RACK",
    "SERVIDOR TORRE",
    "SERVIDOR VIRTUAL - LIN.",
    "SERVIDOR VIRTUAL - WIN.",
    "VM (Virtual Machine)",
    "ACCESS POINT",
    "BIOMETRIA",
    "CAMERA IP",
    "CAMERA IP - WIFI",
    "COLETOR DE DADOS",
    "DIVERSOS/OUTROS",
    "DVR",
    "FIREWALL UTM",
    "HUB",
    "MANAGEMENT SERVER",
    "NOBREAK",
    "NVR",
    "PABX ANALÓGICO",
    "PABX HÍBRIDO",
    "PORTEIRO ELETRONICO",
    "RELÓGIO DE PONTO",
    "ROTEADOR",
    "ROTEADOR WIRELESS",
    "STORAGE",
    "STORAGE NAS",
    "SWITCH",
    "SWITCH GERENCIAVEL",
    "SWITCH POE",
    "SWITCH POE GERENCIAVEL",
    "TV",
    "WIRELESS AP PTP",
    "IMPRESSORA",
    "IMPRESSORA MULTIFUNCIONAL",
    "SCANNER",
    "ATA FXO",
    "ATA FXS",
    "TELEFONE IP",
    "TELEFONE IP - POE",
    "TELEFONE IP SEM FIO",
    "CONTROLE DE ACESSO",
]

async def populate_tipo():
    manager = ReferenceValuesManager()

    print(f"[INFO] Cadastrando {len(VALORES_TIPO)} tipos de dispositivo...")

    created_count = 0
    existing_count = 0

    for valor in VALORES_TIPO:
        try:
            created, normalized, message = await manager.ensure_value(
                field_name="tipo",
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
    print(f"   - Total: {len(VALORES_TIPO)}")
    print("="*60)

if __name__ == "__main__":
    asyncio.run(populate_tipo())
