#!/usr/bin/env python3
"""
Script para validar e popular external_labels no KV
Verifica se external_labels estão sendo salvos corretamente após extração

Autor: Desenvolvedor Sênior
Data: 2025-11-12
"""
import requests
import json
import base64

CONSUL_URL = "http://172.16.1.26:8500"
CONSUL_TOKEN = "8382a112-81e0-cd6d-2b92-8565925a0675"
API_BASE = "http://localhost:5000/api/v1"

def get_kv_value(key):
    """Busca valor do KV Consul"""
    url = f"{CONSUL_URL}/v1/kv/{key}"
    headers = {"X-Consul-Token": CONSUL_TOKEN}
    
    resp = requests.get(url, headers=headers)
    if resp.status_code == 404:
        return None
    
    resp.raise_for_status()
    data = resp.json()[0]
    value_b64 = data['Value']
    value_json = json.loads(base64.b64decode(value_b64).decode())
    return value_json

def put_kv_value(key, value):
    """Salva valor no KV Consul"""
    url = f"{CONSUL_URL}/v1/kv/{key}"
    headers = {"X-Consul-Token": CONSUL_TOKEN}
    
    resp = requests.put(url, headers=headers, json=value)
    resp.raise_for_status()
    return resp.json()

def test_external_labels_in_kv():
    """
    Testa se external_labels estão sendo salvos no KV após extração
    """
    print("=" * 80)
    print("TESTE: External Labels no KV")
    print("=" * 80)
    
    # PASSO 1: Verificar KV atual
    print("\n[1] Verificando KV skills/eye/metadata/fields...")
    
    kv_data = get_kv_value("skills/eye/metadata/fields")
    
    if not kv_data:
        print("❌ KV não existe!")
        return False
    
    print(f"✅ KV existe")
    print(f"   Version: {kv_data.get('version')}")
    print(f"   Total fields: {kv_data.get('total_fields')}")
    print(f"   Last updated: {kv_data.get('last_updated')}")
    
    # PASSO 2: Verificar extraction_status
    print("\n[2] Verificando extraction_status...")
    
    extraction_status = kv_data.get('extraction_status', {})
    server_status = extraction_status.get('server_status', [])
    
    print(f"   Total servers: {extraction_status.get('total_servers')}")
    print(f"   Successful servers: {extraction_status.get('successful_servers')}")
    print(f"   Server status entries: {len(server_status)}")
    
    # PASSO 3: Verificar external_labels em cada servidor
    print("\n[3] Verificando external_labels por servidor...")
    
    has_external_labels = False
    for server in server_status:
        hostname = server.get('hostname')
        external_labels = server.get('external_labels', {})
        
        print(f"\n   Servidor: {hostname}")
        print(f"   Success: {server.get('success')}")
        print(f"   From cache: {server.get('from_cache')}")
        print(f"   External labels: {external_labels}")
        
        if external_labels:
            has_external_labels = True
            print(f"   ✅ External labels encontrados! ({len(external_labels)} labels)")
        else:
            print(f"   ⚠️  External labels vazio!")
    
    if not has_external_labels:
        print("\n❌ PROBLEMA: Nenhum servidor tem external_labels!")
        print("   Isso significa que external_labels não foram extraídos ou não foram salvos no KV")
        return False
    
    print("\n✅ External labels encontrados em pelo menos 1 servidor")
    
    # PASSO 4: Forçar extração e verificar se external_labels são salvos
    print("\n[4] Forçando extração para garantir external_labels...")
    
    try:
        resp = requests.post(f"{API_BASE}/metadata-fields/force-extract", timeout=60)
        
        if resp.status_code != 200:
            print(f"❌ Erro na extração: {resp.status_code}")
            print(f"   Response: {resp.text}")
            return False
        
        data = resp.json()
        print(f"✅ Extração forçada concluída")
        print(f"   Total fields: {data.get('total_fields')}")
        print(f"   Successful servers: {data.get('successful_servers')}")
        
        # Verificar server_status retornado
        server_status_extracted = data.get('server_status', [])
        
        print(f"\n   Verificando external_labels extraídos...")
        for server in server_status_extracted:
            hostname = server.get('hostname')
            external_labels = server.get('external_labels', {})
            
            print(f"\n   Servidor: {hostname}")
            print(f"   External labels: {external_labels}")
            
            if external_labels:
                print(f"   ✅ External labels extraídos! ({len(external_labels)} labels)")
            else:
                print(f"   ⚠️  External labels vazio (servidor pode não ter Prometheus)")
        
    except Exception as e:
        print(f"❌ Erro ao forçar extração: {e}")
        return False
    
    # PASSO 5: Verificar KV novamente após extração
    print("\n[5] Re-verificando KV após extração...")
    
    kv_data_after = get_kv_value("skills/eye/metadata/fields")
    extraction_status_after = kv_data_after.get('extraction_status', {})
    server_status_after = extraction_status_after.get('server_status', [])
    
    all_have_external_labels = True
    for server in server_status_after:
        hostname = server.get('hostname')
        external_labels = server.get('external_labels', {})
        success = server.get('success')
        
        print(f"\n   Servidor: {hostname}")
        print(f"   Success: {success}")
        print(f"   External labels no KV: {external_labels}")
        
        if success and not external_labels:
            print(f"   ⚠️  PROBLEMA: Servidor teve sucesso mas external_labels está vazio no KV!")
            all_have_external_labels = False
    
    if not all_have_external_labels:
        print("\n❌ PROBLEMA: External labels não foram salvos corretamente no KV")
        return False
    
    print("\n✅ External labels salvos corretamente no KV!")
    return True

def test_sites_endpoint():
    """
    Testa se endpoint /config/sites retorna external_labels corretamente
    """
    print("\n" + "=" * 80)
    print("TESTE: Endpoint /config/sites")
    print("=" * 80)
    
    print("\n[1] Buscando sites do endpoint...")
    
    resp = requests.get(f"{API_BASE}/metadata-fields/config/sites")
    
    if resp.status_code != 200:
        print(f"❌ Erro: {resp.status_code}")
        return False
    
    data = resp.json()
    sites = data.get('sites', [])
    
    print(f"✅ {len(sites)} sites retornados")
    
    # Verificar external_labels em cada site
    print("\n[2] Verificando external_labels por site...")
    
    for site in sites:
        code = site.get('code')
        name = site.get('name')
        prometheus_host = site.get('prometheus_host')
        external_labels = site.get('external_labels', {})
        
        print(f"\n   Site: {code}")
        print(f"   Name: {name}")
        print(f"   Prometheus host: {prometheus_host}")
        print(f"   External labels: {external_labels}")
        
        if external_labels:
            print(f"   ✅ External labels encontrados! ({len(external_labels)} labels)")
        else:
            print(f"   ⚠️  External labels vazio (pode ser normal se servidor não tem Prometheus)")
    
    return True

def test_external_labels_endpoint():
    """
    Testa endpoint específico de external_labels
    """
    print("\n" + "=" * 80)
    print("TESTE: Endpoint /external-labels/{hostname}")
    print("=" * 80)
    
    hostnames = ['172.16.1.26', '172.16.200.14', '11.144.0.21']
    
    for hostname in hostnames:
        print(f"\n[{hostname}] Buscando external_labels...")
        
        resp = requests.get(f"{API_BASE}/metadata-fields/external-labels/{hostname}")
        
        if resp.status_code == 404:
            print(f"   ⚠️  Endpoint não existe (404)")
            continue
        
        if resp.status_code != 200:
            print(f"   ❌ Erro: {resp.status_code}")
            continue
        
        data = resp.json()
        external_labels = data.get('external_labels', {})
        
        print(f"   External labels: {external_labels}")
        
        if external_labels:
            print(f"   ✅ External labels encontrados! ({len(external_labels)} labels)")
        else:
            print(f"   ⚠️  External labels vazio")
    
    return True

def main():
    """
    Executa todos os testes
    """
    print("🔍 DIAGNÓSTICO: External Labels e Sites")
    print("=" * 80)
    
    try:
        # Teste 1: KV
        test1_ok = test_external_labels_in_kv()
        
        # Teste 2: Sites endpoint
        test2_ok = test_sites_endpoint()
        
        # Teste 3: External labels endpoint
        test3_ok = test_external_labels_endpoint()
        
        # Resumo
        print("\n" + "=" * 80)
        print("RESUMO DOS TESTES")
        print("=" * 80)
        print(f"✓ External labels no KV: {'✅ OK' if test1_ok else '❌ FALHOU'}")
        print(f"✓ Endpoint /config/sites: {'✅ OK' if test2_ok else '❌ FALHOU'}")
        print(f"✓ Endpoint /external-labels: {'✅ OK' if test3_ok else '❌ FALHOU'}")
        
        if test1_ok and test2_ok:
            print("\n🎉 TODOS OS TESTES PRINCIPAIS PASSARAM!")
        else:
            print("\n❌ ALGUNS TESTES FALHARAM - INVESTIGAR")
        
    except Exception as e:
        print(f"\n❌ ERRO: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
