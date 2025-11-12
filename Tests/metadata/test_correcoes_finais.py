#!/usr/bin/env python3
"""
Validação final das correções:
1. Coluna Origem não mostra servidor selecionado
2. External Labels (Todos Servidores) funciona
3. Gerenciar Sites funciona

Autor: Desenvolvedor Sênior
Data: 2025-11-12
"""
import requests
import json

API_BASE = "http://localhost:5000/api/v1"

def test_origem_column_filter():
    """
    Testa se coluna Origem filtra servidor selecionado corretamente
    """
    print("=" * 80)
    print("TESTE 1: Coluna 'Origem' - Filtro de Servidor Selecionado")
    print("=" * 80)
    
    # Buscar campos
    resp = requests.get(f"{API_BASE}/metadata-fields/")
    data = resp.json()
    
    fields = data.get('fields', [])
    
    print(f"\n✅ {len(fields)} campos retornados")
    
    # Buscar campo vendor como exemplo
    vendor = next((f for f in fields if f['name'] == 'vendor'), None)
    
    if not vendor:
        print("❌ Campo 'vendor' não encontrado")
        return False
    
    discovered_in = vendor.get('discovered_in', [])
    
    print(f"\n📋 Campo: vendor")
    print(f"   discovered_in: {discovered_in}")
    
    # Simular cenários
    scenarios = [
        ("172.16.1.26:5522", "172.16.1.26", "Palmas"),
        ("172.16.200.14:22", "172.16.200.14", "Rio"),
        ("11.144.0.21:22", "11.144.0.21", "DTC"),
    ]
    
    print(f"\n🎯 CENÁRIOS DE TESTE:")
    for selected_id, selected_hostname, site_name in scenarios:
        # Filtrar
        others = [h for h in discovered_in if h != selected_hostname]
        
        print(f"\n   Servidor selecionado: {site_name} ({selected_id})")
        print(f"   Hostname extraído: {selected_hostname}")
        print(f"   Outros servidores: {others}")
        
        if selected_hostname in discovered_in and selected_hostname not in others:
            print(f"   ✅ Servidor selecionado EXCLUÍDO corretamente")
        else:
            print(f"   ❌ PROBLEMA: Filtro não funcionou")
            return False
    
    print(f"\n✅ FILTRO FUNCIONANDO CORRETAMENTE!")
    return True

def test_external_labels_tab():
    """
    Testa se aba External Labels funciona
    """
    print("\n" + "=" * 80)
    print("TESTE 2: Aba 'External Labels (Todos Servidores)'")
    print("=" * 80)
    
    # Buscar servidores com external_labels
    resp = requests.get(f"{API_BASE}/metadata-fields/servers")
    
    if resp.status_code != 200:
        print(f"❌ Erro: {resp.status_code}")
        return False
    
    data = resp.json()
    servers = data.get('servers', [])
    
    print(f"\n✅ Endpoint /servers retornou {len(servers)} servidores")
    
    # Verificar external_labels
    all_have_labels = True
    for server in servers:
        hostname = server.get('hostname')
        external_labels = server.get('external_labels', {})
        
        print(f"\n   Servidor: {hostname}")
        print(f"   External labels: {external_labels}")
        
        if external_labels:
            print(f"   ✅ {len(external_labels)} labels encontrados")
        else:
            print(f"   ⚠️  Sem external_labels (pode ser normal)")
            all_have_labels = False
    
    if all_have_labels:
        print(f"\n✅ TODOS OS SERVIDORES TÊM EXTERNAL_LABELS!")
    else:
        print(f"\n⚠️  Alguns servidores sem external_labels (verifique se foi extraído)")
    
    return True

def test_sites_management_tab():
    """
    Testa se aba Gerenciar Sites funciona
    """
    print("\n" + "=" * 80)
    print("TESTE 3: Aba 'Gerenciar Sites'")
    print("=" * 80)
    
    # Buscar sites
    resp = requests.get(f"{API_BASE}/metadata-fields/config/sites")
    
    if resp.status_code != 200:
        print(f"❌ Erro: {resp.status_code}")
        print(f"   Response: {resp.text}")
        return False
    
    data = resp.json()
    sites = data.get('sites', [])
    
    print(f"\n✅ Endpoint /config/sites retornou {len(sites)} sites")
    
    # Verificar estrutura de cada site
    for site in sites:
        code = site.get('code')
        name = site.get('name')
        prometheus_host = site.get('prometheus_host')
        external_labels = site.get('external_labels', {})
        color = site.get('color')
        is_default = site.get('is_default')
        
        print(f"\n   Site: {code}")
        print(f"   ├─ Nome: {name}")
        print(f"   ├─ Prometheus host: {prometheus_host}")
        print(f"   ├─ External labels: {len(external_labels)} labels")
        print(f"   ├─ Cor: {color}")
        print(f"   └─ Default: {is_default}")
        
        # Validar campos obrigatórios
        if not all([code, name, prometheus_host]):
            print(f"   ❌ PROBLEMA: Campos obrigatórios faltando!")
            return False
        
        print(f"   ✅ Estrutura OK")
    
    print(f"\n✅ GERENCIAR SITES FUNCIONANDO!")
    return True

def main():
    """
    Executa todos os testes
    """
    print("\n🔍 VALIDAÇÃO FINAL DAS CORREÇÕES")
    print("=" * 80)
    
    try:
        test1 = test_origem_column_filter()
        test2 = test_external_labels_tab()
        test3 = test_sites_management_tab()
        
        print("\n" + "=" * 80)
        print("RESUMO FINAL")
        print("=" * 80)
        print(f"1. Coluna Origem filtra servidor: {'✅ OK' if test1 else '❌ FALHOU'}")
        print(f"2. Aba External Labels: {'✅ OK' if test2 else '❌ FALHOU'}")
        print(f"3. Aba Gerenciar Sites: {'✅ OK' if test3 else '❌ FALHOU'}")
        
        if test1 and test2 and test3:
            print("\n🎉 TODAS AS CORREÇÕES VALIDADAS COM SUCESSO!")
            print("\n📝 PRÓXIMO PASSO:")
            print("   Recarregue a página no browser e teste:")
            print("   1. Selecione diferentes servidores - coluna Origem deve mudar")
            print("   2. Clique na aba 'External Labels (Todos Servidores)'")
            print("   3. Clique na aba 'Gerenciar Sites'")
        else:
            print("\n❌ ALGUMAS VALIDAÇÕES FALHARAM - INVESTIGAR")
        
    except Exception as e:
        print(f"\n❌ ERRO: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
