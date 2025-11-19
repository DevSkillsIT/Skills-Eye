#!/usr/bin/env python3
"""
Script para adicionar form_schema nos tipos de monitoring-types KV

Adiciona form_schemas de exemplo para tipos principais:
- blackbox (icmp, http_2xx, http_4xx, tcp_connect, dns)
- snmp_exporter
- windows_exporter
- node_exporter

Uso:
    python scripts/add_form_schema_to_monitoring_types.py
"""

import asyncio
import sys
import os
from pathlib import Path

# Adicionar backend ao path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from core.kv_manager import KVManager
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Form schemas para tipos principais
FORM_SCHEMAS = {
    "icmp": {
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
    "http_2xx": {
        "fields": [
            {
                "name": "target",
                "label": "URL do Site",
                "type": "text",
                "required": True,
                "placeholder": "https://exemplo.com",
                "help": "URL completa do site a ser monitorado"
            },
            {
                "name": "module",
                "label": "Módulo Blackbox",
                "type": "select",
                "required": True,
                "default": "http_2xx",
                "options": [
                    {"value": "http_2xx", "label": "HTTP 2xx"},
                    {"value": "http_post_2xx", "label": "HTTP POST 2xx"},
                    {"value": "http_4xx", "label": "HTTP 4xx"}
                ],
                "help": "Módulo HTTP definido no blackbox.yml"
            }
        ],
        "required_metadata": ["target", "module"],
        "optional_metadata": []
    },
    "tcp_connect": {
        "fields": [
            {
                "name": "target",
                "label": "Host:Porta",
                "type": "text",
                "required": True,
                "placeholder": "192.168.1.1:3306",
                "help": "Endereço IP/hostname e porta (ex: 192.168.1.1:3306)"
            },
            {
                "name": "module",
                "label": "Módulo Blackbox",
                "type": "select",
                "required": True,
                "default": "tcp_connect",
                "options": [
                    {"value": "tcp_connect", "label": "TCP Connect"},
                    {"value": "tcp_connect_v4", "label": "TCP Connect IPv4"},
                    {"value": "tcp_connect_v6", "label": "TCP Connect IPv6"}
                ],
                "help": "Módulo TCP definido no blackbox.yml"
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


async def add_form_schema_to_types():
    """
    Adiciona form_schema em tipos principais que ainda não têm
    """
    kv_manager = KVManager()

    # Buscar KV atual
    logger.info("📖 Buscando monitoring-types do KV...")
    kv_data = await kv_manager.get_json('skills/eye/monitoring-types')

    if not kv_data:
        logger.error("❌ KV monitoring-types não encontrado.")
        return False

    all_types = kv_data.get('all_types', [])
    logger.info(f"📋 Encontrados {len(all_types)} tipos")

    # Contador de atualizações
    updated_count = 0

    # Atualizar tipos que correspondem aos IDs
    for type_def in all_types:
        type_id = type_def.get('id')

        if not type_id:
            continue

        # Verificar se já tem form_schema
        if type_def.get('form_schema'):
            logger.info(f"  ⏭️  Tipo '{type_id}' já tem form_schema, pulando...")
            continue

        # Verificar se temos form_schema para este tipo
        if type_id not in FORM_SCHEMAS:
            continue

        # Adicionar form_schema
        type_def['form_schema'] = FORM_SCHEMAS[type_id]
        updated_count += 1
        logger.info(f"  ✅ Adicionado form_schema em '{type_id}' ({type_def.get('display_name')})")

    # Atualizar também em servers[].types[]
    servers_data = kv_data.get('servers', {})
    for server_host, server_info in servers_data.items():
        server_types = server_info.get('types', [])
        for type_def in server_types:
            type_id = type_def.get('id')
            if type_id and type_id in FORM_SCHEMAS and not type_def.get('form_schema'):
                type_def['form_schema'] = FORM_SCHEMAS[type_id]

    # Atualizar também em categories[].types[]
    categories_data = kv_data.get('categories', [])
    for category in categories_data:
        category_types = category.get('types', [])
        for type_def in category_types:
            type_id = type_def.get('id')
            if type_id and type_id in FORM_SCHEMAS and not type_def.get('form_schema'):
                type_def['form_schema'] = FORM_SCHEMAS[type_id]

    if updated_count == 0:
        logger.info("ℹ️  Nenhum tipo precisou ser atualizado")
        return True

    # Atualizar timestamp
    kv_data['last_updated'] = datetime.now().isoformat()
    kv_data['source'] = 'manual_form_schema_update'

    # Salvar no KV
    logger.info(f"💾 Salvando {updated_count} tipo(s) atualizado(s) no KV...")
    await kv_manager.put_json(
        key='skills/eye/monitoring-types',
        value=kv_data,
        metadata={'manual_update': True, 'source': 'add_form_schema_script'}
    )

    logger.info(f"✅ {updated_count} tipo(s) atualizado(s) com sucesso!")
    return True


async def main():
    """Função principal"""
    try:
        success = await add_form_schema_to_types()
        sys.exit(0 if success else 1)
    except Exception as e:
        logger.error(f"❌ Erro: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    asyncio.run(main())
