#!/usr/bin/env python3
"""
Teste de enriquecimento de monitoring-types com dados de sites
"""
import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.kv_manager import KVManager
from api.monitoring_types_dynamic import _enrich_servers_with_sites_data

async def test_enrichment():
    """Testa enriquecimento de servidores com dados de sites"""
    print("=" * 80)
    print("TESTE: Enriquecimento de monitoring-types com dados de sites")
    print("=" * 80)
    
    # Dados de exemplo (simulando servidores extraídos)
    servers_data = {
        "172.16.1.26": {
            "types": [],
            "total": 10,
            "prometheus_file": "/etc/prometheus/prometheus.yml"
        },
        "172.16.200.14": {
            "types": [],
            "total": 15,
            "prometheus_file": "/etc/prometheus/prometheus.yml"
        }
    }
    
    print("\n[1] Dados de servidores ANTES do enriquecimento:")
    for host, data in servers_data.items():
        print(f"  - {host}: {data}")
    
    # Testar enriquecimento
    print("\n[2] Executando enriquecimento...")
    enriched = await _enrich_servers_with_sites_data(servers_data)
    
    print("\n[3] Dados de servidores DEPOIS do enriquecimento:")
    for host, data in enriched.items():
        site_info = data.get('site', {})
        if site_info:
            print(f"  - {host}:")
            print(f"    Site: {site_info.get('name')} ({site_info.get('code')})")
            print(f"    Cluster: {site_info.get('cluster')}")
            print(f"    Datacenter: {site_info.get('datacenter')}")
            print(f"    Environment: {site_info.get('environment')}")
        else:
            print(f"  - {host}: Nenhum site encontrado")
    
    # Verificar se KV de sites existe
    print("\n[4] Verificando KV de sites...")
    kv = KVManager()
    sites_kv = await kv.get_json('skills/eye/metadata/sites')
    
    if sites_kv:
        if 'data' in sites_kv:
            sites = sites_kv.get('data', {}).get('sites', [])
        else:
            sites = sites_kv.get('sites', [])
        print(f"  ✅ {len(sites)} sites encontrados no KV")
        for site in sites:
            print(f"    - {site.get('code')}: {site.get('name')} (host: {site.get('prometheus_host') or site.get('prometheus_instance')})")
    else:
        print("  ⚠️  KV de sites vazio")
    
    print("\n" + "=" * 80)
    print("TESTE CONCLUÍDO")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(test_enrichment())
