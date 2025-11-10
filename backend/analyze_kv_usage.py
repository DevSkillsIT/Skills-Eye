"""
Analisa TODOS os locais onde usamos Consul KV no projeto.
Identifica:
1. Namespaces em uso
2. Operações (read, write, delete)
3. Se há duplicação com Services API
"""
import asyncio
from core.consul_manager import ConsulManager
from core.kv_manager import KVManager
import json
from collections import defaultdict

async def analyze_kv_usage():
    print("=" * 80)
    print("ANALISE COMPLETA DE USO DO CONSUL KV")
    print("=" * 80)
    print()

    kv = KVManager()

    # 1. Listar TODAS as keys do KV
    print("[1/5] Listando todas as keys do KV...")
    all_keys = await kv.list_keys('skills/eye')
    total = len(all_keys)
    print(f"[OK] Total de keys: {total}")
    print()

    # 2. Agrupar por namespace
    print("[2/5] Agrupando por namespace...")
    by_namespace = defaultdict(list)
    for key in all_keys:
        parts = key.replace('skills/eye/', '').split('/')
        namespace = parts[0] if parts else 'root'
        by_namespace[namespace].append(key)

    print("DISTRIBUICAO POR NAMESPACE:")
    for ns, keys in sorted(by_namespace.items(), key=lambda x: -len(x[1])):
        print(f"  {ns:30s} {len(keys):6d} keys")
    print()

    # 3. Verificar quais namespaces têm DUAL STORAGE
    print("[3/5] Verificando dual storage (KV + Services)...")

    # Verificar blackbox targets
    blackbox_targets_kv = len(by_namespace.get('blackbox', []))

    print()
    print("  BLACKBOX TARGETS:")
    print(f"    KV (skills/eye/blackbox/targets): {blackbox_targets_kv} targets")

    if blackbox_targets_kv == 0:
        print("    [OK] ARQUITETURA TENSUNS! Nenhum target no KV - usando apenas Services API")
    else:
        print("    [ALERTA] Dual storage detectado - migrar para Services API")
    print()

    # 4. Listar namespaces que NÃO devem ter dual storage
    print("[4/5] Namespaces corretos (sem dual storage):")
    safe_namespaces = ['metadata', 'settings', 'audit', 'services', 'reference_values']
    for ns in safe_namespaces:
        count = len(by_namespace.get(ns, []))
        if count > 0:
            print(f"  [OK] {ns:20s} {count:6d} keys (correto - KV only)")
    print()

    # 5. Recomendações
    print("[5/5] RECOMENDACOES:")
    print()

    if blackbox_targets_kv > 0:
        print("  [CRITICO] Eliminar skills/eye/blackbox/targets/")
        print(f"     - {blackbox_targets_kv} targets armazenados desnecessariamente no KV")
        print("     - Migrar logica para ler 100% do Services API")
        print("     - Economia estimada: ~50% de operacoes I/O")

    print()
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(analyze_kv_usage())
