#!/usr/bin/env python3
"""
Script para adicionar form_schema em regras principais de categorização

SPRINT 1: Adiciona form_schema em 3-5 regras principais (blackbox, snmp, windows, node)

Uso:
    python scripts/add_form_schema_to_rules.py
"""

import asyncio
import sys
import os
from pathlib import Path

# Adicionar backend ao path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from core.consul_kv_config_manager import ConsulKVConfigManager
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Form schemas para regras principais
FORM_SCHEMAS = {
    "blackbox": {
        "fields": [
            {
                "name": "target",
                "label": "Alvo (IP ou Hostname)",
                "type": "text",
                "required": True,
                "validation": {"type": "ip_or_hostname"},
                "placeholder": "192.168.1.1 ou exemplo.com",
                "help": "Endereço IP ou hostname a ser monitorado"
            },
            {
                "name": "module",
                "label": "Módulo Blackbox",
                "type": "select",
                "required": True,
                "default": "icmp",
                "options": [
                    {"value": "icmp", "label": "ICMP (Ping)"},
                    {"value": "tcp_connect", "label": "TCP Connect"},
                    {"value": "http_2xx", "label": "HTTP 2xx"},
                    {"value": "dns", "label": "DNS"}
                ],
                "help": "Módulo definido no blackbox.yml"
            }
        ],
        "required_metadata": ["target", "module"],
        "optional_metadata": []
    },
    "snmp_exporter": {
        "fields": [
            {
                "name": "target",
                "label": "IP do Dispositivo",
                "type": "text",
                "required": True,
                "validation": {"type": "ipv4"},
                "placeholder": "192.168.1.10"
            },
            {
                "name": "snmp_community",
                "label": "Community String",
                "type": "password",
                "required": True,
                "default": "public",
                "help": "Community SNMP (ex: public, private)"
            },
            {
                "name": "snmp_module",
                "label": "Módulo SNMP",
                "type": "select",
                "required": True,
                "options": [
                    {"value": "if_mib", "label": "IF-MIB (Interfaces)"},
                    {"value": "cisco_ios", "label": "Cisco IOS"},
                    {"value": "juniper", "label": "Juniper"},
                    {"value": "hp_procurve", "label": "HP Procurve"}
                ],
                "help": "Módulo definido no snmp.yml"
            },
            {
                "name": "snmp_version",
                "label": "Versão SNMP",
                "type": "select",
                "required": False,
                "default": "v2c",
                "options": [
                    {"value": "v1", "label": "v1"},
                    {"value": "v2c", "label": "v2c (recomendado)"},
                    {"value": "v3", "label": "v3 (mais seguro)"}
                ]
            }
        ],
        "required_metadata": ["target", "snmp_community", "snmp_module"],
        "optional_metadata": ["snmp_version"]
    },
    "windows_exporter": {
        "fields": [
            {
                "name": "target",
                "label": "IP do Servidor Windows",
                "type": "text",
                "required": True,
                "validation": {"type": "ipv4"}
            },
            {
                "name": "port",
                "label": "Porta",
                "type": "number",
                "required": False,
                "default": 9182,
                "min": 1,
                "max": 65535,
                "help": "Porta do windows_exporter (padrão: 9182)"
            }
        ],
        "required_metadata": ["target"],
        "optional_metadata": ["port"]
    },
    "node_exporter": {
        "fields": [
            {
                "name": "target",
                "label": "IP do Servidor Linux",
                "type": "text",
                "required": True,
                "validation": {"type": "ipv4"}
            },
            {
                "name": "port",
                "label": "Porta",
                "type": "number",
                "required": False,
                "default": 9100,
                "min": 1,
                "max": 65535,
                "help": "Porta do node_exporter (padrão: 9100)"
            }
        ],
        "required_metadata": ["target"],
        "optional_metadata": ["port"]
    }
}


async def add_form_schema_to_rules():
    """
    Adiciona form_schema em regras principais que ainda não têm
    """
    config_manager = ConsulKVConfigManager()
    
    # Buscar regras atuais
    logger.info("📖 Buscando regras do KV...")
    rules_data = await config_manager.get('monitoring-types/categorization/rules')
    
    if not rules_data:
        logger.error("❌ Regras não encontradas no KV. Execute migrate_categorization_to_json.py primeiro.")
        return False
    
    rules = rules_data.get('rules', [])
    logger.info(f"📋 Encontradas {len(rules)} regras")
    
    # Contador de atualizações
    updated_count = 0
    
    # Atualizar regras que correspondem aos exporter_types
    for rule in rules:
        exporter_type = rule.get('exporter_type')
        
        if not exporter_type:
            continue
        
        # Verificar se já tem form_schema
        if rule.get('form_schema'):
            logger.info(f"  ⏭️  Regra '{rule.get('id')}' já tem form_schema, pulando...")
            continue
        
        # Verificar se temos form_schema para este exporter_type
        if exporter_type not in FORM_SCHEMAS:
            continue
        
        # Adicionar form_schema
        rule['form_schema'] = FORM_SCHEMAS[exporter_type]
        updated_count += 1
        logger.info(f"  ✅ Adicionado form_schema em '{rule.get('id')}' (exporter_type: {exporter_type})")
    
    if updated_count == 0:
        logger.info("ℹ️  Nenhuma regra precisou ser atualizada")
        return True
    
    # Atualizar timestamp
    rules_data['last_updated'] = datetime.now().isoformat()
    
    # Salvar no KV
    logger.info(f"💾 Salvando {updated_count} regra(s) atualizada(s) no KV...")
    success = await config_manager.put('monitoring-types/categorization/rules', rules_data)
    
    if success:
        logger.info(f"✅ {updated_count} regra(s) atualizada(s) com sucesso!")
        return True
    else:
        logger.error("❌ Erro ao salvar regras no KV")
        return False


async def main():
    """Função principal"""
    try:
        success = await add_form_schema_to_rules()
        sys.exit(0 if success else 1)
    except Exception as e:
        logger.error(f"❌ Erro: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    asyncio.run(main())

