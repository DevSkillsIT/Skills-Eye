#!/usr/bin/env python3
"""
Script para popular external_labels nos sites configurados.

Baseado nos external_labels reais do prometheus.yml de cada servidor.
"""
import asyncio
import sys
from core.kv_manager import KVManager

# External labels conhecidos de cada site (copiados dos prometheus.yml reais)
SITES_EXTERNAL_LABELS = {
    "palmas": {
        "prometheus_host": "172.16.1.26",
        "prometheus_port": 9090,
        "external_labels": {
            "cluster": "dtc-skills",
            "datacenter": "genesis-dtc",
            "prometheus_instance": "11.144.0.21",
            "environment": "production",
            "site": "dtc"  # Ajustar se necessário
        }
    },
    "rio": {
        "prometheus_host": "172.16.200.14",
        "prometheus_port": 9090,
        "external_labels": {
            "cluster": "dtc-remote-rio",
            "datacenter": "rio-de-janeiro",
            "prometheus_instance": "172.16.200.14",
            "environment": "production",
            "site": "rio"
        }
    },
    "dtc": {
        "prometheus_host": "172.16.1.27",
        "prometheus_port": 9090,
        "external_labels": {
            "cluster": "dtc-genesis",
            "datacenter": "genesis-dtc",
            "prometheus_instance": "172.16.1.27",
            "environment": "production",
            "site": "dtc"
        }
    }
}

async def main():
    kv = KVManager()

    print("[INFO] Buscando sites do Consul KV...")
    sites_data = await kv.get_json("skills/cm/settings/sites")

    if not sites_data or "sites" not in sites_data:
        print("[ERROR] Sites não encontrados no KV!")
        return 1

    sites = sites_data["sites"]
    print(f"[INFO] Encontrados {len(sites)} sites")

    updated_count = 0
    for site in sites:
        code = site.get("code")
        if code in SITES_EXTERNAL_LABELS:
            print(f"\n[UPDATE] Atualizando site '{code}'...")

            # Adicionar campos prometheus + external_labels
            site.update(SITES_EXTERNAL_LABELS[code])

            print(f"  ✓ prometheus_host: {site['prometheus_host']}")
            print(f"  ✓ prometheus_port: {site['prometheus_port']}")
            print(f"  ✓ external_labels: {len(site['external_labels'])} labels")
            for k, v in site["external_labels"].items():
                print(f"      - {k}: {v}")

            updated_count += 1
        else:
            print(f"\n[SKIP] Site '{code}' não tem external_labels conhecidos (adicione manualmente se necessário)")

    if updated_count > 0:
        print(f"\n[SAVE] Salvando {updated_count} sites atualizados no KV...")
        success = await kv.put_json("skills/cm/settings/sites", {"sites": sites})

        if success:
            print("[SUCCESS] ✅ Sites atualizados com sucesso!")
            print(f"\n[INFO] Sites atualizados: {[s['code'] for s in sites if s['code'] in SITES_EXTERNAL_LABELS]}")
            return 0
        else:
            print("[ERROR] ❌ Falha ao salvar no KV!")
            return 1
    else:
        print("\n[INFO] Nenhum site foi atualizado (todos já configurados ou não encontrados)")
        return 0

if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n[CANCEL] Operação cancelada pelo usuário")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] Erro inesperado: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
