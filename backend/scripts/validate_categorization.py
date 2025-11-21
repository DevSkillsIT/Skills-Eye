#!/usr/bin/env python3
"""
Script de Validação de Categorização - SPEC-ARCH-001

Valida que o sistema de categorização dinâmica via KV está funcionando
corretamente, comparando resultados esperados com os obtidos pelo engine.

RESPONSABILIDADES:
- Validar categorização de tipos conhecidos
- Gerar relatório de conformidade
- Identificar possíveis regressões

AUTOR: Sistema de Refatoração Skills Eye v2.0
DATA: 2025-11-21
"""

import asyncio
import sys
import os
import json
from datetime import datetime

# Adicionar o diretório pai ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.consul_kv_config_manager import ConsulKVConfigManager
from core.categorization_rule_engine import CategorizationRuleEngine


# Casos de teste esperados (ground truth)
EXPECTED_CATEGORIZATIONS = [
    # Network Probes
    {
        'job_data': {'job_name': 'icmp', 'metrics_path': '/probe', 'module': 'icmp'},
        'expected_category': 'network-probes',
        'description': 'ICMP Ping'
    },
    {
        'job_data': {'job_name': 'tcp_connect', 'metrics_path': '/probe', 'module': 'tcp_connect'},
        'expected_category': 'network-probes',
        'description': 'TCP Connect'
    },
    {
        'job_data': {'job_name': 'dns_lookup', 'metrics_path': '/probe', 'module': 'dns'},
        'expected_category': 'network-probes',
        'description': 'DNS Lookup'
    },
    # Web Probes
    {
        'job_data': {'job_name': 'http_2xx', 'metrics_path': '/probe', 'module': 'http_2xx'},
        'expected_category': 'web-probes',
        'description': 'HTTP 2xx'
    },
    {
        'job_data': {'job_name': 'https_check', 'metrics_path': '/probe', 'module': 'https'},
        'expected_category': 'web-probes',
        'description': 'HTTPS Check'
    },
    # System Exporters
    {
        'job_data': {'job_name': 'node_exporter', 'metrics_path': '/metrics', 'module': None},
        'expected_category': 'system-exporters',
        'description': 'Node Exporter'
    },
    {
        'job_data': {'job_name': 'windows_exporter', 'metrics_path': '/metrics', 'module': None},
        'expected_category': 'system-exporters',
        'description': 'Windows Exporter'
    },
    # Database Exporters
    {
        'job_data': {'job_name': 'mysql_exporter', 'metrics_path': '/metrics', 'module': None},
        'expected_category': 'database-exporters',
        'description': 'MySQL Exporter'
    },
    {
        'job_data': {'job_name': 'postgres_exporter', 'metrics_path': '/metrics', 'module': None},
        'expected_category': 'database-exporters',
        'description': 'PostgreSQL Exporter'
    },
    # Infrastructure Exporters
    {
        'job_data': {'job_name': 'snmp_exporter', 'metrics_path': '/snmp', 'module': None},
        'expected_category': 'infrastructure-exporters',
        'description': 'SNMP Exporter'
    },
    # Unknown (deve ir para custom-exporters)
    {
        'job_data': {'job_name': 'unknown_custom_job', 'metrics_path': '/metrics', 'module': None},
        'expected_category': 'custom-exporters',
        'description': 'Job desconhecido (fallback)'
    },
]


async def validate_categorization():
    """
    Executa validação de categorização e gera relatório
    """
    print("\n" + "=" * 70)
    print("SPEC-ARCH-001: VALIDAÇÃO DE CATEGORIZAÇÃO")
    print("=" * 70)
    print(f"Data: {datetime.now().isoformat()}")
    print("=" * 70)

    # Inicializar engine
    config_manager = ConsulKVConfigManager()
    engine = CategorizationRuleEngine(config_manager)

    # Carregar regras
    success = await engine.load_rules(force_reload=True)

    if not success:
        print("\n❌ ERRO CRÍTICO: Não foi possível carregar regras do KV!")
        print("   Execute migrate_categorization_to_json.py para popular o KV")
        return False

    summary = engine.get_rules_summary()
    print(f"\n✅ Engine carregado: {summary['total_rules']} regras")
    print(f"   Fonte: {summary['source']}")
    print(f"   Categorias: {list(summary['categories'].keys())}")

    # Executar validação
    results = []
    passed = 0
    failed = 0

    print("\n" + "-" * 70)
    print("RESULTADOS DA VALIDAÇÃO")
    print("-" * 70)

    for test_case in EXPECTED_CATEGORIZATIONS:
        job_data = test_case['job_data']
        expected = test_case['expected_category']
        description = test_case['description']

        # Categorizar
        actual_category, type_info = engine.categorize(job_data)

        # Verificar resultado
        is_pass = actual_category == expected

        result = {
            'description': description,
            'job_name': job_data['job_name'],
            'expected': expected,
            'actual': actual_category,
            'passed': is_pass,
            'display_name': type_info.get('display_name', ''),
            'exporter_type': type_info.get('exporter_type', '')
        }
        results.append(result)

        if is_pass:
            passed += 1
            status = "✅ PASS"
        else:
            failed += 1
            status = "❌ FAIL"

        print(f"{status}: {description}")
        print(f"       Job: {job_data['job_name']}")
        print(f"       Esperado: {expected}")
        print(f"       Obtido: {actual_category}")
        if not is_pass:
            print(f"       ⚠️  DIVERGÊNCIA DETECTADA!")
        print()

    # Resumo final
    print("=" * 70)
    print("RESUMO DA VALIDAÇÃO")
    print("=" * 70)
    print(f"✅ Passed: {passed}")
    print(f"❌ Failed: {failed}")
    total = passed + failed
    success_rate = (passed / total * 100) if total > 0 else 0
    print(f"Taxa de sucesso: {success_rate:.1f}%")

    # Gerar relatório JSON
    report = {
        'timestamp': datetime.now().isoformat(),
        'engine_summary': summary,
        'total_tests': total,
        'passed': passed,
        'failed': failed,
        'success_rate': success_rate,
        'results': results
    }

    report_path = os.path.join(
        os.path.dirname(__file__),
        f'validate_categorization_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
    )

    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print(f"\n📄 Relatório salvo em: {report_path}")

    if failed > 0:
        print("\n⚠️  ATENÇÃO: Existem divergências na categorização!")
        print("   Verifique as regras no KV e ajuste conforme necessário.")
        return False
    else:
        print("\n✅ VALIDAÇÃO CONCLUÍDA COM SUCESSO!")
        return True


if __name__ == '__main__':
    success = asyncio.run(validate_categorization())
    sys.exit(0 if success else 1)
