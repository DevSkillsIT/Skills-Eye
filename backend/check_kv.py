"""
Script para verificar se o Consul KV tem os campos salvos
"""
import requests

CONSUL_HOST = "172.16.1.26"
CONSUL_PORT = 8500
CONSUL_TOKEN = "8382a112-81e0-cd6d-2b92-8565925a0675"

url = f"http://{CONSUL_HOST}:{CONSUL_PORT}/v1/kv/skills/cm/metadata/fields"
headers = {"X-Consul-Token": CONSUL_TOKEN}

print("Verificando Consul KV...")
print(f"URL: {url}")
print()

response = requests.get(url, headers=headers)

print(f"Status Code: {response.status_code}")

if response.status_code == 200:
    import base64
    import json

    data = response.json()
    if data and len(data) > 0:
        kv_entry = data[0]
        value_b64 = kv_entry.get('Value', '')

        if value_b64:
            value_json = base64.b64decode(value_b64).decode('utf-8')
            value_data = json.loads(value_json)

            print("[OK] Dados encontrados no Consul KV!")
            print()
            print("=== JSON COMPLETO ===")
            print(json.dumps(value_data, indent=2, ensure_ascii=False)[:1000])  # Primeiros 1000 chars
            print()
            print(f"Version: {value_data.get('version')}")
            print(f"Last Updated: {value_data.get('last_updated')}")
            print(f"Total Fields: {value_data.get('total_fields')}")
            print(f"Source: {value_data.get('source')}")

            if value_data.get('fields'):
                print(f"\n[OK] {len(value_data['fields'])} campos no array 'fields'")
                primeiro = value_data['fields'][0]
                print(f"Primeiro campo: {primeiro.get('name')} - {primeiro.get('display_name')}")
            else:
                print("\n[PROBLEMA] Array 'fields' está vazio!")
        else:
            print("[PROBLEMA] Valor em base64 está vazio!")
    else:
        print("[PROBLEMA] Resposta do Consul está vazia!")
elif response.status_code == 404:
    print("[NOT FOUND] Chave 'skills/cm/metadata/fields' não existe no Consul KV!")
else:
    print(f"[ERRO] Erro ao consultar Consul: {response.text}")
