"""
Simula processamento React para identificar EXATAMENTE onde está a lentidão
"""
import requests
import time
import json

API_URL = "http://localhost:5000/api/v1"

print("=" * 80)
print("TESTE DE PROCESSAMENTO FRONTEND (simulacao)")
print("=" * 80)
print()

# ============================================================================
# TESTE 1: Buscar dados e medir processamento
# ============================================================================
print("TESTE 1: BlackboxTargets")
print("-" * 80)

start = time.time()
response = requests.get(f"{API_URL}/optimized/blackbox-targets?force_refresh=false", timeout=30)
fetch_time = (time.time() - start) * 1000

data = response.json()
records = data.get('data', [])

# Simular processamento React
start_process = time.time()

# 1. Converter dados (como requestHandler faz)
processed_records = []
for item in records:
    processed_records.append({
        'key': item['key'],
        'service': item['service'],
        'meta': item.get('meta', {}),
        'tags': item.get('tags', []),
    })

# 2. Extrair metadataOptions (como faz no código)
options = {}
for item in processed_records:
    for key, value in item.get('meta', {}).items():
        if key not in options:
            options[key] = set()
        if value:
            options[key].add(str(value))

options_arrays = {k: list(v) for k, v in options.items()}

# 3. Calcular summary
summary = {
    'total': len(processed_records),
    'by_module': {},
    'by_env': {},
}

for item in processed_records:
    module = item['meta'].get('module', 'unknown')
    env = item['meta'].get('env', 'unknown')
    summary['by_module'][module] = summary['by_module'].get(module, 0) + 1
    summary['by_env'][env] = summary['by_env'].get(env, 0) + 1

process_time = (time.time() - start_process) * 1000

print(f"Fetch time: {fetch_time:.0f}ms")
print(f"Process time: {process_time:.0f}ms")
print(f"Total time: {(fetch_time + process_time):.0f}ms")
print(f"Records: {len(records)}")
print(f"Metadata fields: {len(options_arrays)}")
print()

# ============================================================================
# TESTE 2: Services
# ============================================================================
print("TESTE 2: Services")
print("-" * 80)

start = time.time()
response = requests.get(f"{API_URL}/optimized/services-instances?force_refresh=false", timeout=30)
fetch_time = (time.time() - start) * 1000

data = response.json()
records = data.get('data', [])

# Simular processamento React (IGUAL ao Services.tsx)
start_process = time.time()

# 1. Converter dados
processed_records = []
for item in records:
    processed_records.append({
        'key': item['key'],
        'id': item['id'],
        'node': item['node'],
        'service': item['service'],
        'meta': item.get('meta', {}),
        'tags': item.get('tags', []),
        'address': item.get('address'),
        'port': item.get('port'),
    })

# 2. Extrair metadataOptions (IDENTICO ao requestHandler de Services)
options = {}
for item in processed_records:
    for key, value in item.get('meta', {}).items():
        if key not in options:
            options[key] = set()
        if value:
            options[key].add(str(value))

options_arrays = {k: list(v) for k, v in options.items()}

# 3. Calcular summary (IGUAL ao Services)
summary = {
    'total': len(processed_records),
    'byEnv': {},
    'byModule': {},
    'byCompany': {},
    'byNode': {},
}

for item in processed_records:
    env_key = item['meta'].get('env') or item['meta'].get('tipo_monitoramento', 'desconhecido')
    summary['byEnv'][env_key] = summary['byEnv'].get(env_key, 0) + 1

    module_key = item['meta'].get('module', 'desconhecido')
    summary['byModule'][module_key] = summary['byModule'].get(module_key, 0) + 1

    company_key = item['meta'].get('company', 'desconhecido')
    summary['byCompany'][company_key] = summary['byCompany'].get(company_key, 0) + 1

    node_key = item.get('node', 'desconhecido')
    summary['byNode'][node_key] = summary['byNode'].get(node_key, 0) + 1

process_time = (time.time() - start_process) * 1000

print(f"Fetch time: {fetch_time:.0f}ms")
print(f"Process time: {process_time:.0f}ms")
print(f"Total time: {(fetch_time + process_time):.0f}ms")
print(f"Records: {len(records)}")
print(f"Metadata fields: {len(options_arrays)}")
print()

# ============================================================================
# COMPARACAO
# ============================================================================
print("=" * 80)
print("CONCLUSAO")
print("=" * 80)
print("Se os tempos sao similares aqui, o problema esta no RENDERING do React")
print("(ProTable, colunas dinamicas, etc), nao no processamento de dados.")
print()
print("PROXIMOS PASSOS:")
print("1. Verificar quantas COLUNAS cada tabela renderiza")
print("2. Verificar se visibleColumns esta recalculando desnecessariamente")
print("3. Verificar memoizacao de callbacks e handlers")
print("=" * 80)
