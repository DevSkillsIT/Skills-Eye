#!/usr/bin/env python3
"""
Test script para diagnosticar problema de filtros quebrados
========================================================

PROBLEMA REPORTADO:
- ✅ Filtro "empresa" funciona
- ❌ Filtro "provedor" NÃO funciona

OBJETIVO:
1. Chamar endpoint /metadata-fields/categories/{category}
2. Verificar se "provedor" está em show_in_filter=true
3. Chamar endpoint de monitoramento
4. Verificar se dados realmente têm campo "provedor" no Meta
5. Comparar com campo "company" que funciona

DIAGNÓSTICO ESPERADO:
- Se "provedor" não existe em metadata_fields → problema backend
- Se "provedor" existe mas não aparece no frontend → problema frontend
- Se dados não têm "provedor" → problema de dados
"""

import requests
import json
from collections import Counter
from typing import Dict, List, Any

BASE_URL = "http://localhost:5000"

def colorize(text: str, color: str) -> str:
    """Adiciona cor ANSI ao texto"""
    colors = {
        'red': '\033[91m',
        'green': '\033[92m',
        'yellow': '\033[93m',
        'blue': '\033[94m',
        'magenta': '\033[95m',
        'cyan': '\033[96m',
        'white': '\033[97m',
        'reset': '\033[0m',
        'bold': '\033[1m'
    }
    return f"{colors.get(color, '')}{text}{colors['reset']}"

def print_section(title: str):
    """Print section header"""
    print(f"\n{colorize('='*80, 'cyan')}")
    print(colorize(f"  {title}", 'bold'))
    print(colorize('='*80, 'cyan'))

def test_metadata_fields(category: str = "network-probes"):
    """Teste 1: Verificar configuração de metadata fields"""
    print_section(f"TESTE 1: Metadata Fields para '{category}'")
    
    try:
        resp = requests.get(f"{BASE_URL}/metadata-fields/categories/{category}", timeout=5)
        resp.raise_for_status()
        data = resp.json()
        
        filter_fields = [f for f in data if f.get('show_in_filter')]
        table_fields = [f for f in data if f.get('show_in_table')]
        
        print(f"\n{colorize('📋 FIELDS COM show_in_filter=true:', 'green')}")
        for idx, field in enumerate(filter_fields, 1):
            name = field.get('name', 'N/A')
            display = field.get('display_name', 'N/A')
            data_type = field.get('data_type', 'N/A')
            
            # Destacar "provedor" e "company"
            if name == 'provedor':
                print(f"  {colorize(f'{idx}. {name}', 'yellow')} → {display} ({data_type}) {colorize('⭐ CAMPO PROBLEMA', 'red')}")
            elif name == 'company':
                print(f"  {colorize(f'{idx}. {name}', 'green')} → {display} ({data_type}) {colorize('✅ FUNCIONA', 'green')}")
            else:
                print(f"  {idx}. {name} → {display} ({data_type})")
        
        # Verificar se "provedor" existe
        has_provedor = any(f.get('name') == 'provedor' for f in filter_fields)
        has_company = any(f.get('name') == 'company' for f in filter_fields)
        
        print(f"\n{colorize('🔍 DIAGNÓSTICO BACKEND:', 'cyan')}")
        if has_provedor:
            print(f"  ✅ Campo 'provedor' {colorize('EXISTE', 'green')} em metadata_fields")
        else:
            print(f"  ❌ Campo 'provedor' {colorize('NÃO EXISTE', 'red')} em metadata_fields")
            print(f"     {colorize('→ PROBLEMA: Backend não está retornando campo provedor', 'red')}")
        
        if has_company:
            print(f"  ✅ Campo 'company' {colorize('EXISTE', 'green')} em metadata_fields")
        else:
            print(f"  ❌ Campo 'company' {colorize('NÃO EXISTE', 'red')} (improvável)")
        
        return filter_fields, data
        
    except Exception as e:
        print(colorize(f"❌ ERRO ao obter metadata fields: {e}", 'red'))
        return [], []

def test_monitoring_data(category: str = "network-probes"):
    """Teste 2: Verificar dados reais de monitoramento"""
    print_section(f"TESTE 2: Dados de Monitoramento '{category}'")
    
    try:
        resp = requests.get(f"{BASE_URL}/monitoring/{category}", timeout=10)
        resp.raise_for_status()
        data = resp.json()
        
        if not data:
            print(colorize("⚠️  Nenhum dado retornado", 'yellow'))
            return []
        
        print(f"\n{colorize(f'📊 Total de registros: {len(data)}', 'green')}")
        
        # Análise de campos Meta
        provedor_values = []
        company_values = []
        records_with_provedor = 0
        records_with_company = 0
        
        for item in data:
            meta = item.get('Meta', {})
            
            if 'provedor' in meta:
                records_with_provedor += 1
                val = meta['provedor']
                if val:
                    provedor_values.append(val)
            
            if 'company' in meta:
                records_with_company += 1
                val = meta['company']
                if val:
                    company_values.append(val)
        
        # Estatísticas
        print(f"\n{colorize('🔍 ANÁLISE DE DADOS:', 'cyan')}")
        
        print(f"\n  {colorize('Campo: provedor', 'yellow')}")
        print(f"    Registros com campo: {records_with_provedor}/{len(data)} ({100*records_with_provedor/len(data):.1f}%)")
        print(f"    Valores únicos: {len(set(provedor_values))}")
        if provedor_values:
            counter = Counter(provedor_values)
            print(f"    Top 5 valores:")
            for val, count in counter.most_common(5):
                print(f"      - {val}: {count}")
        else:
            print(f"      {colorize('❌ NENHUM VALOR ENCONTRADO', 'red')}")
            print(f"      {colorize('→ PROBLEMA: Dados não têm campo provedor populado', 'red')}")
        
        print(f"\n  {colorize('Campo: company', 'green')}")
        print(f"    Registros com campo: {records_with_company}/{len(data)} ({100*records_with_company/len(data):.1f}%)")
        print(f"    Valores únicos: {len(set(company_values))}")
        if company_values:
            counter = Counter(company_values)
            print(f"    Top 5 valores:")
            for val, count in counter.most_common(5):
                print(f"      - {val}: {count}")
        else:
            print(f"      {colorize('❌ NENHUM VALOR ENCONTRADO', 'red')}")
        
        # Sample record
        print(f"\n{colorize('📄 AMOSTRA DE REGISTRO (primeiro item):', 'cyan')}")
        if data:
            sample = data[0]
            print(f"  Service: {sample.get('Service', 'N/A')}")
            print(f"  Node: {sample.get('Node', 'N/A')}")
            meta = sample.get('Meta', {})
            print(f"  Meta.company: {colorize(meta.get('company', 'N/A'), 'green')}")
            print(f"  Meta.provedor: {colorize(meta.get('provedor', 'N/A'), 'yellow')}")
            print(f"  Meta keys: {', '.join(sorted(meta.keys()))}")
        
        return data
        
    except Exception as e:
        print(colorize(f"❌ ERRO ao obter dados de monitoramento: {e}", 'red'))
        return []

def test_filter_functionality(data: List[Dict], filter_fields: List[Dict]):
    """Teste 3: Simular lógica de filtro do frontend"""
    print_section("TESTE 3: Simulação de Filtro Frontend")
    
    if not data or not filter_fields:
        print(colorize("⚠️  Sem dados para testar", 'yellow'))
        return
    
    # Simular extração de metadataOptions (igual ao código frontend)
    print(f"\n{colorize('🔧 Simulando extração de metadataOptions:', 'cyan')}")
    
    options_sets: Dict[str, set] = {}
    for field in filter_fields:
        options_sets[field['name']] = set()
    
    for item in data:
        meta = item.get('Meta', {})
        for field in filter_fields:
            field_name = field['name']
            value = meta.get(field_name)
            if value and isinstance(value, str):
                options_sets[field_name].add(value)
    
    # Converter para arrays ordenados
    options: Dict[str, List[str]] = {}
    for field_name, value_set in options_sets.items():
        options[field_name] = sorted(list(value_set))
    
    # Resultados
    print(f"\n{colorize('📊 OPÇÕES EXTRAÍDAS:', 'cyan')}")
    for field in filter_fields:
        field_name = field['name']
        field_display = field.get('display_name', field_name)
        opts = options.get(field_name, [])
        
        if field_name == 'provedor':
            color = 'yellow'
            status = colorize('⭐ CAMPO PROBLEMA', 'red')
        elif field_name == 'company':
            color = 'green'
            status = colorize('✅ FUNCIONA', 'green')
        else:
            color = 'white'
            status = ''
        
        print(f"  {colorize(field_display, color)}: {len(opts)} opções {status}")
        if opts:
            print(f"    Valores: {', '.join(opts[:5])}{' ...' if len(opts) > 5 else ''}")
        else:
            print(f"    {colorize('❌ VAZIO (Select não será renderizado!)', 'red')}")

def run_diagnosis():
    """Executa diagnóstico completo"""
    print(colorize("\n" + "="*80, 'bold'))
    print(colorize("  🔍 DIAGNÓSTICO DE FILTROS QUEBRADOS", 'bold'))
    print(colorize("="*80 + "\n", 'bold'))
    
    category = "network-probes"
    
    # Teste 1: Backend metadata fields
    filter_fields, all_fields = test_metadata_fields(category)
    
    # Teste 2: Dados reais
    data = test_monitoring_data(category)
    
    # Teste 3: Simulação frontend
    test_filter_functionality(data, filter_fields)
    
    # DIAGNÓSTICO FINAL
    print_section("🎯 DIAGNÓSTICO FINAL")
    
    has_provedor_in_config = any(f.get('name') == 'provedor' for f in filter_fields)
    has_provedor_in_data = False
    provedor_count = 0
    
    if data:
        for item in data:
            meta = item.get('Meta', {})
            if meta.get('provedor'):
                has_provedor_in_data = True
                provedor_count += 1
    
    print()
    if not has_provedor_in_config:
        print(colorize("❌ PROBLEMA IDENTIFICADO: Campo 'provedor' não existe em metadata_fields", 'red'))
        print(colorize("   → Solução: Adicionar campo 'provedor' em backend/metadata_fields.json", 'yellow'))
        print(colorize("   → Arquivo: backend/metadata_fields.json", 'yellow'))
        print(colorize("   → Propriedades necessárias: show_in_filter=true, show_in_table=true", 'yellow'))
    elif not has_provedor_in_data:
        print(colorize("❌ PROBLEMA IDENTIFICADO: Dados não têm campo 'provedor' populado", 'red'))
        print(colorize(f"   → {provedor_count}/{len(data)} registros têm provedor", 'yellow'))
        print(colorize("   → Solução: Verificar se serviços têm Meta.provedor nos dados do Consul", 'yellow'))
    else:
        print(colorize("✅ Campo 'provedor' existe na configuração E nos dados", 'green'))
        print(colorize(f"   → {provedor_count}/{len(data)} registros têm provedor", 'green'))
        print(colorize("   → Problema pode estar no frontend (renderização ou estado)", 'yellow'))
        print(colorize("   → Verifique console do browser para erros JavaScript", 'yellow'))
    
    print()

if __name__ == '__main__':
    run_diagnosis()
