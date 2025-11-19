#!/usr/bin/env python3
import requests
import json
from collections import Counter

url = "http://localhost:5000/api/v1/monitoring/data?category=network-probes"
resp = requests.get(url)
resp.raise_for_status()

result = resp.json()
data = result.get('data', [])

print(f"✅ Total de registros: {len(data)}")

if not data:
    print("❌ Nenhum dado retornado")
    exit(1)

# Amostra
sample = data[0]
meta = sample.get('Meta', {})
print(f"\n📄 AMOSTRA - Service: {sample.get('Service')}")
print(f"   Meta.company: {meta.get('company')}")
print(f"   Meta.provedor: {meta.get('provedor')}")
print(f"\n   Todos Meta keys: {sorted(meta.keys())}")

# Estatísticas
provedor_values = []
company_values = []

for item in data:
    m = item.get('Meta', {})
    if m.get('provedor'):
        provedor_values.append(m['provedor'])
    if m.get('company'):
        company_values.append(m['company'])

print(f"\n📊 ESTATÍSTICAS:")
print(f"   Registros com 'provedor': {len(provedor_values)}/{len(data)} ({100*len(provedor_values)/len(data):.1f}%)")
print(f"   Registros com 'company': {len(company_values)}/{len(data)} ({100*len(company_values)/len(data):.1f}%)")

if provedor_values:
    print(f"\n   Valores únicos de 'provedor': {len(set(provedor_values))}")
    counter = Counter(provedor_values)
    print(f"   Top 5 provedores:")
    for val, count in counter.most_common(5):
        print(f"     - {val}: {count}")
else:
    print(f"\n   ❌ NENHUM REGISTRO TEM 'provedor' POPULADO")
    print(f"   ⚠️  Este é o PROBLEMA: dados não têm valores para filtrar!")
