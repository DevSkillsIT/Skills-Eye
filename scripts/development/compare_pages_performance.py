"""
Script para comparar performance entre BlackboxTargets e Services
Mede tempos de request, tamanho de payload, e identifica diferenças
"""
import requests
import time
import json
from datetime import datetime

API_URL = "http://localhost:5000/api/v1"

print("=" * 80)
print("COMPARACAO DE PERFORMANCE: BlackboxTargets vs Services")
print("=" * 80)
print(f"Data/Hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print()

# ============================================================================
# TESTE 1: BlackboxTargets
# ============================================================================
print("=" * 80)
print("TESTE 1: BlackboxTargets")
print("=" * 80)

blackbox_times = []
for i in range(3):
    start = time.time()
    try:
        response = requests.get(f"{API_URL}/optimized/blackbox-targets?force_refresh=false", timeout=30)
        elapsed = (time.time() - start) * 1000  # ms
        blackbox_times.append(elapsed)

        data = response.json()
        print(f"Request {i+1}:")
        print(f"  Status: {response.status_code}")
        print(f"  Tempo: {elapsed:.0f}ms")
        print(f"  Payload size: {len(response.content):,} bytes")
        print(f"  Registros: {len(data.get('data', []))}")
        print(f"  From cache: {data.get('from_cache', False)}")
        print()

        time.sleep(0.5)  # Pequena pausa entre requests
    except Exception as e:
        print(f"ERRO: {e}")
        break

# ============================================================================
# TESTE 2: Services
# ============================================================================
print("=" * 80)
print("TESTE 2: Services")
print("=" * 80)

services_times = []
for i in range(3):
    start = time.time()
    try:
        response = requests.get(f"{API_URL}/optimized/services-instances?force_refresh=false", timeout=30)
        elapsed = (time.time() - start) * 1000  # ms
        services_times.append(elapsed)

        data = response.json()
        print(f"Request {i+1}:")
        print(f"  Status: {response.status_code}")
        print(f"  Tempo: {elapsed:.0f}ms")
        print(f"  Payload size: {len(response.content):,} bytes")
        print(f"  Registros: {len(data.get('data', []))}")
        print(f"  From cache: {data.get('from_cache', False)}")
        print()

        time.sleep(0.5)  # Pequena pausa entre requests
    except Exception as e:
        print(f"ERRO: {e}")
        break

# ============================================================================
# COMPARACAO
# ============================================================================
print("=" * 80)
print("COMPARACAO DE RESULTADOS")
print("=" * 80)

if blackbox_times and services_times:
    blackbox_avg = sum(blackbox_times) / len(blackbox_times)
    services_avg = sum(services_times) / len(services_times)

    print(f"BlackboxTargets:")
    print(f"  Tempo médio: {blackbox_avg:.0f}ms")
    print(f"  Tempo mínimo: {min(blackbox_times):.0f}ms")
    print(f"  Tempo máximo: {max(blackbox_times):.0f}ms")
    print()

    print(f"Services:")
    print(f"  Tempo médio: {services_avg:.0f}ms")
    print(f"  Tempo mínimo: {min(services_times):.0f}ms")
    print(f"  Tempo máximo: {max(services_times):.0f}ms")
    print()

    diff = services_avg - blackbox_avg
    diff_pct = (diff / blackbox_avg) * 100

    print(f"DIFERENCA:")
    print(f"  Services é {diff:.0f}ms mais {'LENTO' if diff > 0 else 'RAPIDO'}")
    print(f"  Diferença percentual: {abs(diff_pct):.1f}%")
    print()

    if diff > 100:
        print("⚠️ PROBLEMA IDENTIFICADO: Services está MUITO mais lento!")
        print()
        print("PROXIMOS PASSOS:")
        print("1. Verificar processamento no backend (backend/api/services_optimized.py)")
        print("2. Comparar tamanho de payload (Services pode estar retornando mais dados)")
        print("3. Verificar queries SQL/Consul no backend")
    elif diff > 50:
        print("⚠️ Services está um pouco mais lento")
    else:
        print("✓ Performance similar!")

print()
print("=" * 80)
print("FIM DA ANALISE")
print("=" * 80)
