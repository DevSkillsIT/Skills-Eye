#!/usr/bin/env python3
"""
Teste completo dos endpoints de SITES
Valida que Consul está ONLINE e API funcionando
"""
import requests
import json

API_URL = "http://localhost:5000/api/v1/metadata-fields"
CONSUL_URL = "http://172.16.1.26:8500/v1"
CONSUL_TOKEN = "8382a112-81e0-cd6d-2b92-8565925a0675"

print("=" * 80)
print("TESTE COMPLETO: ENDPOINTS DE SITES")
print("=" * 80)

# TESTE 1: Consul direto via API
print("\n[1] TESTANDO CONSUL DIRETO VIA API")
print("-" * 80)
try:
    response = requests.get(
        f"{CONSUL_URL}/kv/skills/eye/metadata/sites?raw",
        headers={"X-Consul-Token": CONSUL_TOKEN},
        timeout=5
    )
    if response.status_code == 200:
        data = response.json()
        sites = data.get("data", {}).get("sites", [])
        print(f"✅ Consul ONLINE - {len(sites)} sites no KV")
        print(f"   Estrutura: {json.dumps(data, indent=2)[:200]}...")
    else:
        print(f"❌ Consul retornou status {response.status_code}")
except Exception as e:
    print(f"❌ Erro ao acessar Consul: {e}")

# TESTE 2: GET /config/sites
print("\n[2] TESTANDO GET /config/sites")
print("-" * 80)
try:
    response = requests.get(f"{API_URL}/config/sites", timeout=10)
    if response.status_code == 200:
        data = response.json()
        sites = data.get("sites", [])
        print(f"✅ GET /config/sites - {len(sites)} sites listados")
        for site in sites:
            print(f"   - {site['code']}: {site['name']} (default={site['is_default']})")
    else:
        print(f"❌ Status: {response.status_code}")
        print(f"   Resposta: {response.text[:200]}")
except Exception as e:
    print(f"❌ Erro: {e}")

# TESTE 3: PATCH /config/sites/palmas
print("\n[3] TESTANDO PATCH /config/sites/palmas")
print("-" * 80)
try:
    payload = {"name": "TESTE - Palmas Atualizado", "color": "green"}
    response = requests.patch(
        f"{API_URL}/config/sites/palmas",
        json=payload,
        timeout=10
    )
    if response.status_code == 200:
        data = response.json()
        print(f"✅ PATCH /config/sites/palmas - Site atualizado")
        print(f"   {json.dumps(data, indent=2)[:300]}")
    else:
        print(f"❌ Status: {response.status_code}")
        print(f"   Resposta: {response.text[:200]}")
except Exception as e:
    print(f"❌ Erro: {e}")

# TESTE 4: POST /config/sites/sync
print("\n[4] TESTANDO POST /config/sites/sync")
print("-" * 80)
try:
    response = requests.post(f"{API_URL}/config/sites/sync", timeout=30)
    if response.status_code == 200:
        data = response.json()
        print(f"✅ POST /config/sites/sync - Sincronização completa")
        print(f"   Sites sincronizados: {data.get('sites_synced')}")
        print(f"   Novos: {data.get('new_sites')}")
        print(f"   Existentes: {data.get('existing_sites')}")
    else:
        print(f"❌ Status: {response.status_code}")
        print(f"   Resposta: {response.text[:200]}")
except Exception as e:
    print(f"❌ Erro: {e}")

# TESTE 5: POST /config/sites/cleanup
print("\n[5] TESTANDO POST /config/sites/cleanup")
print("-" * 80)
try:
    response = requests.post(f"{API_URL}/config/sites/cleanup", timeout=10)
    if response.status_code == 200:
        data = response.json()
        print(f"✅ POST /config/sites/cleanup - Limpeza completa")
        print(f"   Órfãos removidos: {data.get('removed_count')}")
        print(f"   Sites ativos: {len(data.get('active_sites', []))}")
    else:
        print(f"❌ Status: {response.status_code}")
        print(f"   Resposta: {response.text[:200]}")
except Exception as e:
    print(f"❌ Erro: {e}")

# VALIDAÇÃO FINAL DO KV
print("\n[6] VALIDAÇÃO FINAL DO KV")
print("-" * 80)
try:
    response = requests.get(
        f"{CONSUL_URL}/kv/skills/eye/metadata/sites?raw",
        headers={"X-Consul-Token": CONSUL_TOKEN},
        timeout=5
    )
    if response.status_code == 200:
        data = response.json()
        sites = data.get("data", {}).get("sites", [])
        print(f"✅ KV FINAL: {len(sites)} sites")
        for site in sites:
            print(f"   - {site['code']}: {site.get('name')} (default={site.get('is_default')})")
    else:
        print(f"❌ Status: {response.status_code}")
except Exception as e:
    print(f"❌ Erro: {e}")

print("\n" + "=" * 80)
print("TESTES CONCLUÍDOS")
print("=" * 80)
