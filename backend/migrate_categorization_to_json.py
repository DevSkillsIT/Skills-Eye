"""
Script de Migração: Categorização Hardcoded → JSON no KV

Este script extrai os 40+ padrões de categorização existentes em
monitoring_types_dynamic.py e migra para JSON no Consul KV.

OBJETIVO:
- Substituir código hardcoded por configuração editável
- Permitir adição de novos exporters sem alterar código
- Centralizar regras em um único JSON no KV

EXECUÇÃO:
    python migrate_categorization_to_json.py

RESULTADO:
    JSON salvo em: skills/eye/monitoring-types/categorization/rules

AUTOR: Sistema de Refatoração Skills Eye v2.0
DATA: 2025-11-13
"""

import asyncio
import json
from datetime import datetime
from core.consul_kv_config_manager import ConsulKVConfigManager
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ============================================================================
# PADRÕES EXTRAÍDOS DE monitoring_types_dynamic.py
# ============================================================================

# Módulos Blackbox (Network Probes)
BLACKBOX_NETWORK_MODULES = {
    'icmp': 'ICMP (Ping)',
    'ping': 'ICMP (Ping)',
    'tcp': 'TCP Connect',
    'tcp_connect': 'TCP Connect',
    'dns': 'DNS Query',
    'ssh': 'SSH Banner',
    'ssh_banner': 'SSH Banner',
}

# Módulos Blackbox (Web Probes)
BLACKBOX_WEB_MODULES = {
    'http_2xx': 'HTTP 2xx',
    'http_4xx': 'HTTP 4xx',
    'http_5xx': 'HTTP 5xx',
    'https': 'HTTPS',
    'http_post_2xx': 'HTTP POST 2xx',
    'http_post': 'HTTP POST',
    'http_get': 'HTTP GET',
}

# Padrões de Exporters
# Formato: pattern: (categoria, display_name, exporter_type)
EXPORTER_PATTERNS = {
    # ========================================================================
    # SYSTEM EXPORTERS
    # ========================================================================
    'node': ('system-exporters', 'Node Exporter (Linux)', 'node_exporter'),
    'selfnode': ('system-exporters', 'Node Exporter (Linux)', 'node_exporter'),
    'windows': ('system-exporters', 'Windows Exporter', 'windows_exporter'),
    'snmp': ('system-exporters', 'SNMP Exporter', 'snmp_exporter'),

    # ========================================================================
    # DATABASE EXPORTERS
    # ========================================================================
    'mysql': ('database-exporters', 'MySQL Exporter', 'mysqld_exporter'),
    'postgres': ('database-exporters', 'PostgreSQL Exporter', 'postgres_exporter'),
    'pg': ('database-exporters', 'PostgreSQL Exporter', 'postgres_exporter'),
    'redis': ('database-exporters', 'Redis Exporter', 'redis_exporter'),
    'mongo': ('database-exporters', 'MongoDB Exporter', 'mongodb_exporter'),
    'mongodb': ('database-exporters', 'MongoDB Exporter', 'mongodb_exporter'),
    'elasticsearch': ('database-exporters', 'Elasticsearch Exporter', 'elasticsearch_exporter'),
    'memcached': ('database-exporters', 'Memcached Exporter', 'memcached_exporter'),

    # ========================================================================
    # INFRASTRUCTURE EXPORTERS
    # ========================================================================
    # Web Servers
    'haproxy': ('infrastructure-exporters', 'HAProxy Exporter', 'haproxy_exporter'),
    'nginx': ('infrastructure-exporters', 'Nginx Exporter', 'nginx_exporter'),
    'apache': ('infrastructure-exporters', 'Apache Exporter', 'apache_exporter'),

    # Message Queues
    'kafka': ('infrastructure-exporters', 'Kafka Exporter', 'kafka_exporter'),
    'rabbitmq': ('infrastructure-exporters', 'RabbitMQ Exporter', 'rabbitmq_exporter'),
    'nats': ('infrastructure-exporters', 'NATS Exporter', 'nats_exporter'),

    # Service Discovery / Orchestration
    'consul_exporter': ('infrastructure-exporters', 'Consul Exporter', 'consul_exporter'),
    'consul': ('infrastructure-exporters', 'Consul Exporter', 'consul_exporter'),

    # Monitoring Systems
    'jmx': ('infrastructure-exporters', 'JMX Exporter', 'jmx_exporter'),
    'collectd': ('infrastructure-exporters', 'Collectd Exporter', 'collectd_exporter'),
    'statsd': ('infrastructure-exporters', 'StatsD Exporter', 'statsd_exporter'),
    'graphite': ('infrastructure-exporters', 'Graphite Exporter', 'graphite_exporter'),
    'influxdb': ('infrastructure-exporters', 'InfluxDB Exporter', 'influxdb_exporter'),

    # Cloud Providers
    'cloudwatch': ('infrastructure-exporters', 'AWS CloudWatch Exporter', 'cloudwatch_exporter'),

    # APIs & Development Tools
    'github': ('infrastructure-exporters', 'GitHub Exporter', 'github_exporter'),
    'gitlab': ('infrastructure-exporters', 'GitLab Exporter', 'gitlab_exporter'),
    'jenkins': ('infrastructure-exporters', 'Jenkins Exporter', 'jenkins_exporter'),

    # ========================================================================
    # HARDWARE EXPORTERS
    # ========================================================================
    'ipmi': ('hardware-exporters', 'IPMI Exporter', 'ipmi_exporter'),
    'dellhw': ('hardware-exporters', 'Dell Hardware OMSA Exporter', 'dellhw_exporter'),

    # ========================================================================
    # NETWORK DEVICES
    # ========================================================================
    'mktxp': ('network-devices', 'MikroTik Exporter (MKTXP)', 'mktxp'),
    'mikrotik': ('network-devices', 'MikroTik Exporter (MKTXP)', 'mktxp'),
}


async def migrate():
    """Executa migração de regras hardcoded para JSON no KV"""

    print("=" * 80)
    print(" MIGRAÇÃO: CATEGORIZAÇÃO HARDCODED → JSON NO KV")
    print("=" * 80)
    print()

    rules = []

    # ========================================================================
    # PASSO 1: Regras de Blackbox (prioridade alta: 100)
    # ========================================================================
    print("📦 Convertendo regras de Blackbox...")

    # Network Probes
    for module, display_name in BLACKBOX_NETWORK_MODULES.items():
        rules.append({
            "id": f"blackbox_{module}",
            "priority": 100,
            "category": "network-probes",
            "display_name": display_name,
            "exporter_type": "blackbox",
            "conditions": {
                "job_name_pattern": f"^{module}.*",
                "metrics_path": "/probe",
                "module_pattern": f"^{module}$"
            }
        })

    # Web Probes
    for module, display_name in BLACKBOX_WEB_MODULES.items():
        rules.append({
            "id": f"blackbox_{module}",
            "priority": 100,
            "category": "web-probes",
            "display_name": display_name,
            "exporter_type": "blackbox",
            "conditions": {
                "job_name_pattern": f"^{module}.*",
                "metrics_path": "/probe",
                "module_pattern": f"^{module}$"
            }
        })

    print(f"  ✅ {len(BLACKBOX_NETWORK_MODULES)} regras de Network Probes")
    print(f"  ✅ {len(BLACKBOX_WEB_MODULES)} regras de Web Probes")

    # ========================================================================
    # PASSO 2: Regras de Exporters (prioridade média: 80)
    # ========================================================================
    print("\n📦 Convertendo regras de Exporters...")

    for pattern_name, (category, display_name, exporter_type) in EXPORTER_PATTERNS.items():
        rules.append({
            "id": f"exporter_{pattern_name}",
            "priority": 80,
            "category": category,
            "display_name": display_name,
            "exporter_type": exporter_type,
            "conditions": {
                "job_name_pattern": f"^{pattern_name}.*",
                "metrics_path": "/metrics"
            }
        })

    print(f"  ✅ {len(EXPORTER_PATTERNS)} regras de Exporters")

    # ========================================================================
    # PASSO 3: Ordenar por prioridade (maior primeiro)
    # ========================================================================
    rules.sort(key=lambda r: r['priority'], reverse=True)

    # ========================================================================
    # PASSO 4: Criar estrutura JSON completa
    # ========================================================================
    rules_data = {
        "version": "1.0.0",
        "last_updated": datetime.now().isoformat(),
        "total_rules": len(rules),
        "rules": rules,
        "default_category": "custom-exporters",
        "categories": [
            {"id": "network-probes", "display_name": "Network Probes (Rede)"},
            {"id": "web-probes", "display_name": "Web Probes (Aplicações)"},
            {"id": "system-exporters", "display_name": "Exporters: Sistemas"},
            {"id": "database-exporters", "display_name": "Exporters: Bancos de Dados"},
            {"id": "infrastructure-exporters", "display_name": "Exporters: Infraestrutura"},
            {"id": "hardware-exporters", "display_name": "Exporters: Hardware"},
            {"id": "network-devices", "display_name": "Dispositivos de Rede"},
            {"id": "custom-exporters", "display_name": "Exporters Customizados"},
        ]
    }

    # ========================================================================
    # PASSO 5: Salvar no Consul KV
    # ========================================================================
    print("\n💾 Salvando no Consul KV...")

    config_manager = ConsulKVConfigManager()
    key = 'monitoring-types/categorization/rules'

    success = await config_manager.put(key, rules_data)

    if success:
        print(f"  ✅ Regras salvas em: skills/eye/{key}")
        print(f"\n📊 RESUMO:")
        print(f"  - Total de regras: {len(rules)}")
        print(f"  - Blackbox Network: {len(BLACKBOX_NETWORK_MODULES)}")
        print(f"  - Blackbox Web: {len(BLACKBOX_WEB_MODULES)}")
        print(f"  - Exporters: {len(EXPORTER_PATTERNS)}")
        print(f"  - Categorias: {len(rules_data['categories'])}")
        print(f"\n✅ MIGRAÇÃO CONCLUÍDA COM SUCESSO!")

        # Exibir preview das primeiras 5 regras
        print(f"\n📋 Preview das primeiras 5 regras:")
        for rule in rules[:5]:
            print(f"  - {rule['id']} (prioridade {rule['priority']}) → {rule['category']}")

        return True
    else:
        print(f"  ❌ ERRO ao salvar regras no KV")
        return False


async def validate_migration():
    """Valida que regras foram salvas corretamente"""

    print("\n🔍 Validando migração...")

    config_manager = ConsulKVConfigManager()
    key = 'monitoring-types/categorization/rules'

    rules_data = await config_manager.get(key)

    if not rules_data:
        print("  ❌ Regras não encontradas no KV!")
        return False

    print(f"  ✅ Regras encontradas no KV")
    print(f"  ✅ Versão: {rules_data.get('version')}")
    print(f"  ✅ Total de regras: {rules_data.get('total_rules')}")
    print(f"  ✅ Última atualização: {rules_data.get('last_updated')}")

    # Verificar estrutura de algumas regras
    if 'rules' in rules_data and len(rules_data['rules']) > 0:
        first_rule = rules_data['rules'][0]
        required_keys = ['id', 'priority', 'category', 'conditions']
        missing_keys = [k for k in required_keys if k not in first_rule]

        if missing_keys:
            print(f"  ⚠️  Regra com chaves faltando: {missing_keys}")
            return False

        print(f"  ✅ Estrutura de regras válida")

    return True


async def main():
    """Executa migração e validação"""

    try:
        # Migrar
        success = await migrate()

        if not success:
            print("\n❌ Migração FALHOU!")
            return

        # Validar
        validated = await validate_migration()

        if validated:
            print("\n✅ MIGRAÇÃO E VALIDAÇÃO OK!")
            print("\n📝 PRÓXIMOS PASSOS:")
            print("  1. Modificar monitoring_types_dynamic.py para usar CategorizationRuleEngine")
            print("  2. Testar que categorização produz mesmos resultados")
            print("  3. Remover código hardcoded após validação")
            print("\n💡 DICA:")
            print("  Para editar regras, use a interface web ou edite diretamente no Consul KV:")
            print("  http://172.16.1.26:8500/ui/dc1/kv/skills/eye/monitoring-types/categorization/rules")
        else:
            print("\n⚠️  Migração OK mas validação FALHOU - verificar KV")

    except KeyboardInterrupt:
        print("\n\n❌ Migração cancelada pelo usuário")
    except Exception as e:
        print(f"\n❌ ERRO: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    asyncio.run(main())
