#!/usr/bin/env python3
"""
Script de teste: Validar filtro de nós no frontend
Simula comportamento do NodeSelector + filtro client-side
"""

import requests
import json

API_URL = "http://localhost:5000/api/v1"

def test_node_filter():
    print("=" * 80)
    print("TESTE: Filtro de Nós - Frontend vs Backend")
    print("=" * 80)
    
    # PASSO 1: Buscar lista de nós (como NodeSelector faz)
    print("\n[1] Buscando nós do Consul...")
    nodes_response = requests.get(f"{API_URL}/nodes")
    nodes_data = nodes_response.json()
    
    if not nodes_data.get('success'):
        print("❌ ERRO ao buscar nós")
        return
    
    nodes = nodes_data['data']
    print(f"✅ Encontrados {len(nodes)} nós:")
    for node in nodes:
        print(f"   - {node.get('name', 'N/A'):40} | IP: {node['addr']}")
    
    # PASSO 2: Buscar dados de monitoramento (como useEffect faz)
    print("\n[2] Buscando dados de monitoramento...")
    monitoring_response = requests.get(f"{API_URL}/monitoring/data?category=network-probes")
    monitoring_data = monitoring_response.json()
    
    if not monitoring_data.get('success'):
        print("❌ ERRO ao buscar dados de monitoramento")
        return
    
    all_items = monitoring_data['data']
    print(f"✅ Total de itens retornados: {len(all_items)}")
    
    # Verificar se node_ip existe
    sample_item = all_items[0] if all_items else {}
    has_node_ip = 'node_ip' in sample_item
    print(f"   Campo 'node_ip' presente? {has_node_ip}")
    
    if has_node_ip:
        print(f"   Exemplo: Node='{sample_item.get('Node')}', node_ip='{sample_item.get('node_ip')}'")
    
    # PASSO 3: Simular filtro client-side para cada nó
    print("\n[3] Simulando filtro client-side (como linha 518 do frontend)...")
    print("-" * 80)
    
    for node in nodes:
        node_addr = node['addr']
        
        # FILTRO CLIENT-SIDE: item.node_ip === selectedNode
        filtered_items = [item for item in all_items if item.get('node_ip') == node_addr]
        
        node_name = node.get('name', 'N/A')
        print(f"\n   Nó selecionado: {node_name:40} ({node_addr})")
        print(f"   ├─ Itens filtrados: {len(filtered_items)}")
        
        if filtered_items:
            # Mostrar alguns exemplos
            print(f"   └─ Exemplos:")
            for item in filtered_items[:3]:
                company = item.get('Meta', {}).get('company', 'N/A')
                instance = item.get('Meta', {}).get('instance', 'N/A')
                print(f"      • {company:20} | {instance}")
    
    # PASSO 4: Testar opção "Todos os nós"
    print("\n" + "-" * 80)
    print(f"\n   Nó selecionado: 'all' (Todos os nós)")
    print(f"   ├─ Itens filtrados: {len(all_items)} (sem filtro)")
    print(f"   └─ Total esperado: {len(all_items)}")
    
    print("\n" + "=" * 80)
    print("RESULTADO DO TESTE")
    print("=" * 80)
    
    # Validação
    total_by_node = sum(
        len([item for item in all_items if item.get('node_ip') == node['addr']])
        for node in nodes
    )
    
    if total_by_node == len(all_items):
        print(f"✅ SUCESSO: Todos os {len(all_items)} itens foram contabilizados")
        print(f"✅ Filtro por nó está funcionando corretamente")
    else:
        print(f"⚠️ ATENÇÃO: Contagem não bate!")
        print(f"   Total de itens: {len(all_items)}")
        print(f"   Soma por nós: {total_by_node}")
        print(f"   Diferença: {len(all_items) - total_by_node}")
    
    # Verificar se há itens sem node_ip
    items_without_ip = [item for item in all_items if not item.get('node_ip')]
    if items_without_ip:
        print(f"\n⚠️ AVISO: {len(items_without_ip)} itens SEM node_ip (não serão filtrados)")
    
    print("=" * 80)

if __name__ == '__main__':
    test_node_filter()
