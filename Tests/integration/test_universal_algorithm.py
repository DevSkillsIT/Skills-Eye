#!/usr/bin/env python3
"""
Script de Teste do Algoritmo Universal de Extração de Campos Metadata

OBJETIVO:
Validar que o algoritmo extrai EXATAMENTE 40 campos distintos do arquivo
prometheus-teste-meta.yml usando a mesma lógica da página MetadataFields.

CRITÉRIO DE SUCESSO:
- 40 campos únicos extraídos
- Suporte a TODOS os tipos de service discovery
- YAML anchors resolvidos corretamente
"""

import sys
from pathlib import Path
from typing import List, Dict, Any
from ruamel.yaml import YAML

# Adicionar diretório backend ao path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from core.fields_extraction_service import FieldsExtractionService, MetadataField


def load_prometheus_yml(yml_path: str) -> Dict[str, Any]:
    """
    Carrega arquivo Prometheus YML resolvendo YAML anchors

    IMPORTANTE: Usa ruamel.yaml que preserva e resolve anchors automaticamente
    """
    print(f"\n{'='*80}")
    print(f"CARREGANDO ARQUIVO YML")
    print(f"{'='*80}")
    print(f"Arquivo: {yml_path}\n")

    yaml = YAML()
    yaml.preserve_quotes = True

    with open(yml_path, 'r', encoding='utf-8') as f:
        config = yaml.load(f)

    jobs = config.get('scrape_configs', [])
    print(f"OK: {len(jobs)} jobs carregados")
    print(f"OK: YAML anchors resolvidos automaticamente\n")

    return config


def extract_fields(config: Dict[str, Any]) -> List[MetadataField]:
    """
    Extrai campos usando o algoritmo universal

    USA: FieldsExtractionService.extract_fields_from_jobs()
    ALGORITMO: Mesmo da página MetadataFields (replicado do PrometheusConfig.tsx)
    """
    print(f"{'='*80}")
    print(f"EXECUTANDO ALGORITMO UNIVERSAL")
    print(f"{'='*80}\n")

    service = FieldsExtractionService()
    jobs = config.get('scrape_configs', [])

    print(f"Processando {len(jobs)} jobs...\n")

    fields = service.extract_fields_from_jobs(jobs)

    print(f"\nOK: Extracao completa!")
    print(f"OK: Total de campos unicos extraidos: {len(fields)}\n")

    return fields


def analyze_fields(fields: List[MetadataField]) -> Dict[str, Any]:
    """
    Analisa campos extraídos por tipo de service discovery
    """
    print(f"{'='*80}")
    print(f"ANÁLISE DOS CAMPOS EXTRAÍDOS")
    print(f"{'='*80}\n")

    # Agrupar por tipo de source_label
    by_sd_type = {}

    for field in fields:
        source = field.source_label or 'unknown'

        # Identificar tipo de SD pelo source_label
        if '__meta_consul_' in source:
            sd_type = 'Consul'
        elif '__meta_kubernetes_' in source:
            sd_type = 'Kubernetes'
        elif '__meta_ec2_' in source:
            sd_type = 'EC2'
        elif '__meta_digitalocean_' in source:
            sd_type = 'DigitalOcean'
        elif '__meta_dns_' in source:
            sd_type = 'DNS'
        elif '__meta_dockerswarm_' in source:
            sd_type = 'Docker Swarm'
        elif '__param_' in source:
            sd_type = 'Multi-Target (SNMP/Blackbox)'
        elif '__meta_filepath' in source:
            sd_type = 'File SD'
        elif not source.startswith('__'):
            sd_type = 'Static/Transformation'
        else:
            sd_type = 'Other'

        if sd_type not in by_sd_type:
            by_sd_type[sd_type] = []
        by_sd_type[sd_type].append(field.name)

    # Mostrar por tipo
    for sd_type in sorted(by_sd_type.keys()):
        field_names = sorted(by_sd_type[sd_type])
        print(f"[{sd_type}]: {len(field_names)} campos")
        for i, name in enumerate(field_names, 1):
            print(f"   {i:2d}. {name}")
        print()

    return by_sd_type


def print_full_report(fields: List[MetadataField], expected_count: int = 40):
    """
    Relatório completo com todos os campos
    """
    print(f"{'='*80}")
    print(f"RELATÓRIO COMPLETO - TODOS OS CAMPOS")
    print(f"{'='*80}\n")

    # Ordenar por nome
    sorted_fields = sorted(fields, key=lambda f: f.name)

    for i, field in enumerate(sorted_fields, 1):
        print(f"{i:2d}. {field.name:25} | source: {field.source_label or 'N/A'}")

    print(f"\n{'='*80}")
    print(f"VALIDAÇÃO FINAL")
    print(f"{'='*80}\n")

    print(f"Total de campos extraídos: {len(fields)}")
    print(f"Total esperado:            {expected_count}")

    if len(fields) == expected_count:
        print(f"\n[PASS] TESTE PASSOU! Exatamente {expected_count} campos unicos extraidos.")
        return True
    else:
        diff = len(fields) - expected_count
        if diff > 0:
            print(f"\n[FAIL] TESTE FALHOU! {diff} campos A MAIS que o esperado.")
        else:
            print(f"\n[FAIL] TESTE FALHOU! {abs(diff)} campos A MENOS que o esperado.")

        # Listar campos esperados vs encontrados
        expected_fields = {
            # Consul base + extended
            'cservice', 'company', 'env', 'region', 'vendor', 'datacenter', 'rack', 'operating_system',
            # Blackbox
            'monitor_type', 'expected_status', 'timeout', 'check_interval', 'instance', 'packet_size', 'ttl',
            # Windows
            'windows_version', 'domain', 'server_role',
            # Kubernetes
            'app', 'version', 'namespace', 'team', 'environment',
            # EC2
            'instance_name', 'cost_center', 'instance_type', 'az',
            # SNMP
            'device_type', 'location',
            # File SD
            'target_group', 'dc', 'rack_id',
            # Static
            'priority', 'responsible_team',
            # DigitalOcean
            'status', 'size',
            # DNS
            'service_name', 'dns_record',
            # Docker Swarm
            'service', 'network',
        }

        found_fields = {f.name for f in fields}

        missing = expected_fields - found_fields
        extra = found_fields - expected_fields

        if missing:
            print(f"\n[MISSING] CAMPOS FALTANDO ({len(missing)}):")
            for field in sorted(missing):
                print(f"   - {field}")

        if extra:
            print(f"\n[EXTRA] CAMPOS EXTRAS ({len(extra)}):")
            for field in sorted(extra):
                print(f"   + {field}")

        return False


def main():
    """
    Executa o teste completo
    """
    print("\n" + "="*80)
    print("TESTE DO ALGORITMO UNIVERSAL DE EXTRAÇÃO DE CAMPOS METADATA")
    print("="*80)
    print("\nArquivo de teste: prometheus-teste-meta.yml")
    print("Algoritmo: FieldsExtractionService.extract_fields_from_jobs()")
    print("Meta: 40 campos únicos\n")

    # Caminho do arquivo de teste
    test_file = Path(__file__).parent.parent / 'docs' / 'Configuracoes-Exemplos-Prometheus-Blackbox' / 'dtc-genesis-slave' / 'prometheus-teste-meta.yml'

    if not test_file.exists():
        print(f"[ERROR] Arquivo de teste nao encontrado: {test_file}")
        sys.exit(1)

    try:
        # PASSO 1: Carregar YML
        config = load_prometheus_yml(str(test_file))

        # PASSO 2: Extrair campos
        fields = extract_fields(config)

        # PASSO 3: Analisar por tipo
        by_sd_type = analyze_fields(fields)

        # PASSO 4: Relatório completo
        success = print_full_report(fields, expected_count=40)

        # PASSO 5: Exit code
        sys.exit(0 if success else 1)

    except Exception as e:
        print(f"\n[ERROR] ERRO DURANTE EXECUCAO:")
        print(f"{e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
