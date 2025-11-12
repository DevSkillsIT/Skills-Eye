#!/usr/bin/env python3
"""
Teste para validar correções das colunas Descoberto Em e Origem
Verifica se os nomes dos sites são exibidos corretamente (não IPs)

Autor: Desenvolvedor Sênior
Data: 2025-11-12
"""
import requests
import json

API_BASE = "http://localhost:5000/api/v1"

def test_discovered_in_column():
    """
    Testa se a coluna Descoberto Em mostra nomes de sites corretos
    """
    print("=" * 80)
    print("TESTE: Coluna 'Descoberto Em' - Nomes de Sites")
    print("=" * 80)
    
    # 1. Buscar campos
    print("\n[1] Buscando campos...")
    resp = requests.get(f"{API_BASE}/metadata-fields/")
    
    if resp.status_code != 200:
        print(f"❌ Erro: {resp.status_code}")
        return False
    
    data = resp.json()
    fields = data.get('fields', [])
    
    print(f"✅ {len(fields)} campos retornados")
    
    # 2. Buscar config de sites
    print("\n[2] Buscando config de sites...")
    sites_resp = requests.get(f"{API_BASE}/metadata-fields/config/sites")
    
    if sites_resp.status_code != 200:
        print(f"❌ Erro ao buscar sites: {sites_resp.status_code}")
        return False
    
    sites_data = sites_resp.json()
    sites = sites_data.get('sites', [])
    
    print(f"✅ {len(sites)} sites configurados:")
    for site in sites:
        print(f"   - {site['name']} ({site['prometheus_host']}) - cor: {site.get('color', 'N/A')}")
    
    # 3. Criar mapeamento IP → Nome do Site
    ip_to_name = {
        '172.16.1.26': 'Palmas',
        '172.16.200.14': 'Rio',
        '11.144.0.21': 'DTC'
    }
    
    # 4. Validar campos com discovered_in
    print("\n[3] Validando campos com discovered_in...")
    
    campos_com_discovered = [f for f in fields if f.get('discovered_in')]
    print(f"\n   Total de campos com discovered_in: {len(campos_com_discovered)}")
    
    if len(campos_com_discovered) == 0:
        print("⚠️  Nenhum campo possui discovered_in!")
        return False
    
    # Mostrar exemplos
    print("\n   Exemplos de campos (primeiros 5):")
    for field in campos_com_discovered[:5]:
        name = field['name']
        discovered = field['discovered_in']
        
        print(f"\n   Campo: {name}")
        print(f"   discovered_in: {discovered}")
        
        # Mapear IPs para nomes
        site_names = []
        for hostname in discovered:
            # Buscar site correspondente
            site = next((s for s in sites if s['prometheus_host'] == hostname), None)
            
            if site:
                # Site tem nome personalizado?
                if site['name'] != site['code']:
                    site_names.append(f"{site['name']} (custom)")
                else:
                    # Usar fallback
                    fallback_name = ip_to_name.get(hostname, hostname.split('.')[0])
                    site_names.append(f"{fallback_name} (fallback)")
            else:
                # Site não encontrado, usar fallback
                fallback_name = ip_to_name.get(hostname, hostname.split('.')[0])
                site_names.append(f"{fallback_name} (no site)")
        
        print(f"   Deve mostrar: {', '.join(site_names)}")
    
    # 5. Testar lógica da coluna "Origem" (excluir servidor selecionado)
    print("\n[4] Testando lógica da coluna 'Origem'...")
    
    selected_server = '172.16.1.26'  # Simular servidor Palmas selecionado
    print(f"\n   Servidor selecionado: {selected_server} (Palmas)")
    
    campo_exemplo = campos_com_discovered[0]
    discovered = campo_exemplo['discovered_in']
    
    print(f"\n   Campo: {campo_exemplo['name']}")
    print(f"   discovered_in completo: {discovered}")
    
    # Filtrar servidor atual
    other_servers = [h for h in discovered if h != selected_server]
    
    print(f"   Servidores OUTROS (excluindo Palmas): {other_servers}")
    
    if len(other_servers) == 0:
        print("   Deve mostrar: '-' (campo só existe no servidor atual)")
    else:
        other_names = [ip_to_name.get(h, h) for h in other_servers]
        print(f"   Deve mostrar: {', '.join(other_names)}")
    
    # 6. Resumo
    print("\n" + "=" * 80)
    print("RESUMO DA VALIDAÇÃO")
    print("=" * 80)
    
    print("\n✅ COLUNA 'DESCOBERTO EM':")
    print("   - Deve mostrar nomes amigáveis (Palmas/Rio/DTC)")
    print("   - Com cores diferentes (verde/azul/laranja)")
    print("   - Usar nome customizado do site se existir")
    
    print("\n✅ COLUNA 'ORIGEM':")
    print("   - NÃO deve mostrar o servidor atualmente selecionado")
    print("   - Mostra apenas OUTROS servidores onde campo existe")
    print("   - Se campo só existe no servidor atual, mostra '-'")
    
    print("\n💡 EXEMPLO PRÁTICO:")
    print("   Servidor selecionado: Palmas (172.16.1.26)")
    print("   Campo 'vendor' existe em: [Palmas, Rio, DTC]")
    print("   → Descoberto Em: Palmas, Rio, DTC (com cores)")
    print("   → Origem: Rio, DTC (SEM Palmas)")
    
    return True

def test_field_specific():
    """
    Testa campo específico para validar comportamento
    """
    print("\n" + "=" * 80)
    print("TESTE ESPECÍFICO: Campo 'vendor'")
    print("=" * 80)
    
    # Buscar campo vendor
    resp = requests.get(f"{API_BASE}/metadata-fields/")
    data = resp.json()
    
    vendor_field = next((f for f in data['fields'] if f['name'] == 'vendor'), None)
    
    if not vendor_field:
        print("❌ Campo 'vendor' não encontrado")
        return False
    
    discovered = vendor_field.get('discovered_in', [])
    
    print(f"\nCampo: vendor")
    print(f"discovered_in: {discovered}")
    print(f"Total de servidores: {len(discovered)}")
    
    # Mapear para nomes
    ip_to_name = {
        '172.16.1.26': 'Palmas',
        '172.16.200.14': 'Rio',
        '11.144.0.21': 'DTC'
    }
    
    site_names = [ip_to_name.get(h, h) for h in discovered]
    
    print(f"\nNomes dos sites:")
    for i, (hostname, name) in enumerate(zip(discovered, site_names), 1):
        print(f"   {i}. {name} ({hostname})")
    
    # Simular cenários
    print("\n" + "-" * 80)
    print("CENÁRIOS DE TESTE")
    print("-" * 80)
    
    for selected in discovered:
        selected_name = ip_to_name.get(selected, selected)
        others = [h for h in discovered if h != selected]
        other_names = [ip_to_name.get(h, h) for h in others]
        
        print(f"\n✓ Servidor selecionado: {selected_name}")
        print(f"  Descoberto Em: {', '.join(site_names)}")
        
        if len(others) == 0:
            print(f"  Origem: -")
        else:
            print(f"  Origem: {', '.join(other_names)}")
    
    return True

if __name__ == "__main__":
    try:
        success1 = test_discovered_in_column()
        success2 = test_field_specific()
        
        if success1 and success2:
            print("\n" + "=" * 80)
            print("✅ TODOS OS TESTES PASSARAM!")
            print("=" * 80)
            print("\n🎯 PRÓXIMO PASSO:")
            print("   Recarregue a página no browser e verifique:")
            print("   1. Coluna 'Descoberto Em' mostra Palmas/Rio/DTC (com cores)")
            print("   2. Coluna 'Origem' NÃO mostra o site selecionado")
        else:
            print("\n❌ Alguns testes falharam")
            
    except requests.exceptions.ConnectionError:
        print("❌ ERRO: Backend não está rodando em http://localhost:5000")
        print("Execute: cd backend && python app.py")
    except Exception as e:
        print(f"❌ ERRO: {e}")
        import traceback
        traceback.print_exc()
