#!/usr/bin/env python3
"""
Diagnóstico COMPLETO do problema de filtros

TESTES:
1. ✅ Backend retorna campo 'provedor' em metadata-fields?
2. ✅ Backend retorna campo com show_in_filter=true?
3. ✅ Dados têm valores de provedor?
4. ❓ Hook useFilterFields inclui provedor (simular lógica)?
5. ❓ MetadataOptions é extraído corretamente (simular extração)?
"""

import requests
import json

BASE_URL = "http://localhost:5000/api/v1"

def test_metadata_fields():
    """Teste 1: Verificar se campo existe em metadata-fields"""
    print("=" * 80)
    print("TESTE 1: Metadata Fields Configuration")
    print("=" * 80)
    
    resp = requests.get(f"{BASE_URL}/metadata-fields/")
    data = resp.json()
    
    # Encontrar campos relevantes
    company_field = next((f for f in data['fields'] if f['name'] == 'company'), None)
    provedor_field = next((f for f in data['fields'] if f['name'] == 'provedor'), None)
    
    print(f"\n📋 Campo 'company':")
    if company_field:
        print(f"   ✅ Existe")
        print(f"   show_in_filter: {company_field.get('show_in_filter')}")
        print(f"   show_in_table: {company_field.get('show_in_table')}")
        print(f"   enabled: {company_field.get('enabled')}")
        print(f"   category: {company_field.get('category')}")
        print(f"   show_in_network_probes: {company_field.get('show_in_network_probes')}")
    
    print(f"\n📋 Campo 'provedor':")
    if provedor_field:
        print(f"   ✅ Existe")
        print(f"   show_in_filter: {provedor_field.get('show_in_filter')}")
        print(f"   show_in_table: {provedor_field.get('show_in_table')}")
        print(f"   enabled: {provedor_field.get('enabled')}")
        print(f"   category: {provedor_field.get('category')}")
        print(f"   show_in_network_probes: {provedor_field.get('show_in_network_probes')}")
    else:
        print(f"   ❌ NÃO EXISTE")
    
    return company_field, provedor_field, data['fields']

def simulate_useFilterFields(all_fields, context='network-probes'):
    """Simula lógica do hook useFilterFields"""
    print("\n" + "=" * 80)
    print(f"TESTE 2: Simulação do Hook useFilterFields('{context}')")
    print("=" * 80)
    
    # Lógica do hook (copiada de useMetadataFields.ts linhas 270-297)
    filtered = []
    
    for f in all_fields:
        # Mapear categorias para campos show_in corretos
        if context == 'network-probes' or context == 'web-probes':
            if f.get('show_in_blackbox') == False:
                continue
        
        # Filtrar por enabled e show_in_filter
        if f.get('enabled') != True:
            continue
        if f.get('show_in_filter') != True:
            continue
        
        filtered.append(f)
    
    # Ordenar por order
    filtered.sort(key=lambda x: x.get('order', 999))
    
    print(f"\n📊 Total de campos após filtros: {len(filtered)}")
    print(f"\nCampos incluídos:")
    for idx, f in enumerate(filtered, 1):
        name = f['name']
        display = f.get('display_name', name)
        marker = "⭐" if name == 'provedor' else ("✅" if name == 'company' else "  ")
        print(f"   {marker} {idx}. {name} ({display})")
    
    has_company = any(f['name'] == 'company' for f in filtered)
    has_provedor = any(f['name'] == 'provedor' for f in filtered)
    
    print(f"\n🔍 Resultado da simulação:")
    print(f"   company incluído? {'✅ SIM' if has_company else '❌ NÃO'}")
    print(f"   provedor incluído? {'✅ SIM' if has_provedor else '❌ NÃO'}")
    
    return filtered

def test_monitoring_data():
    """Teste 3: Verificar dados reais"""
    print("\n" + "=" * 80)
    print("TESTE 3: Dados de Monitoramento")
    print("=" * 80)
    
    resp = requests.get(f"{BASE_URL}/monitoring/data?category=network-probes")
    result = resp.json()
    data = result.get('data', [])
    
    print(f"\n📊 Total de registros: {len(data)}")
    
    # Contar valores
    company_values = set()
    provedor_values = set()
    
    for item in data:
        meta = item.get('Meta', {})
        if meta.get('company'):
            company_values.add(meta['company'])
        if meta.get('provedor'):
            provedor_values.add(meta['provedor'])
    
    print(f"\n🔍 Valores únicos:")
    print(f"   company: {len(company_values)} valores")
    if company_values:
        print(f"      Exemplos: {list(company_values)[:5]}")
    
    print(f"   provedor: {len(provedor_values)} valores")
    if provedor_values:
        print(f"      Exemplos: {list(provedor_values)[:5]}")
    else:
        print(f"      ⚠️  VAZIO - por isso filtro não aparece!")
    
    return data, company_values, provedor_values

def simulate_metadata_options_extraction(data, filter_fields):
    """Simula extração de metadataOptions (lógica do requestHandler)"""
    print("\n" + "=" * 80)
    print("TESTE 4: Simulação de extração de metadataOptions")
    print("=" * 80)
    
    # Lógica copiada de DynamicMonitoringPage.tsx linhas 570-601
    options_sets = {}
    
    # Inicializar sets para cada filterField
    for field in filter_fields:
        options_sets[field['name']] = set()
    
    # Extrair valores
    for item in data:
        meta = item.get('Meta', {})
        for field in filter_fields:
            value = meta.get(field['name'])
            if value and isinstance(value, str):
                options_sets[field['name']].add(value)
    
    # Converter para arrays ordenados
    options = {}
    for field_name, value_set in options_sets.items():
        options[field_name] = sorted(list(value_set))
    
    print(f"\n📊 metadataOptions extraídas:")
    for field in filter_fields:
        field_name = field['name']
        opts = options.get(field_name, [])
        marker = "⭐" if field_name == 'provedor' else ("✅" if field_name == 'company' else "  ")
        
        print(f"   {marker} {field['display_name']} ({field_name}): {len(opts)} opções")
        if opts:
            print(f"      Valores: {opts[:5]}{' ...' if len(opts) > 5 else ''}")
        else:
            print(f"      ⚠️  VAZIO - Select NÃO será renderizado!")
    
    return options

def main():
    print("\n" + "=" * 80)
    print("🔍 DIAGNÓSTICO COMPLETO - FILTROS QUEBRADOS")
    print("=" * 80)
    
    # Teste 1: Metadata fields configuration
    company_field, provedor_field, all_fields = test_metadata_fields()
    
    # Teste 2: Simular hook useFilterFields
    filter_fields = simulate_useFilterFields(all_fields, 'network-probes')
    
    # Teste 3: Dados reais
    data, company_values, provedor_values = test_monitoring_data()
    
    # Teste 4: Simular extração de metadataOptions
    options = simulate_metadata_options_extraction(data, filter_fields)
    
    # DIAGNÓSTICO FINAL
    print("\n" + "=" * 80)
    print("🎯 DIAGNÓSTICO FINAL")
    print("=" * 80)
    
    has_provedor_in_config = provedor_field is not None
    has_provedor_in_filter_fields = any(f['name'] == 'provedor' for f in filter_fields)
    has_provedor_values = len(provedor_values) > 0
    has_provedor_in_options = len(options.get('provedor', [])) > 0
    
    print(f"\n✅/❌ Checklist:")
    print(f"   {'✅' if has_provedor_in_config else '❌'} Campo 'provedor' existe em metadata-fields")
    print(f"   {'✅' if has_provedor_in_filter_fields else '❌'} Campo 'provedor' passa pelo filtro do hook (show_in_filter=true)")
    print(f"   {'✅' if has_provedor_values else '❌'} Dados têm valores de 'provedor'")
    print(f"   {'✅' if has_provedor_in_options else '❌'} metadataOptions['provedor'] tem valores")
    
    print(f"\n🔍 Conclusão:")
    if not has_provedor_in_config:
        print(f"   ❌ PROBLEMA: Campo não existe no backend")
    elif not has_provedor_in_filter_fields:
        print(f"   ❌ PROBLEMA: Campo não passa pelo filtro show_in_filter ou enabled")
    elif not has_provedor_values:
        print(f"   ❌ PROBLEMA: Dados não têm valores para extrair ({len(provedor_values)} valores)")
        print(f"      → Apenas {len([1 for d in data if d.get('Meta',{}).get('provedor')])} de {len(data)} registros têm provedor")
        print(f"      → MetadataFilterBar não renderiza select sem opções (by design)")
    elif not has_provedor_in_options:
        print(f"   ❌ PROBLEMA: Extração falhou (bug na lógica)")
    else:
        print(f"   ⚠️  Backend está OK, problema pode estar no FRONTEND")
        print(f"      → Verifique console do browser")
        print(f"      → Verifique se component re-renderiza quando metadataOptions muda")

if __name__ == '__main__':
    main()
