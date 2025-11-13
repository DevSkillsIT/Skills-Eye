#!/usr/bin/env python3
"""
Popula KV skills/eye/metadata/sites com estrutura correta
Migra external_labels para nível raiz de cada site

Autor: Desenvolvedor Sênior
Data: 2025-11-12
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

import asyncio
from core.kv_manager import KVManager
from core.multi_config_manager import MultiConfigManager
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def migrate_sites_structure():
    """
    Migra estrutura do KV sites para ter external_labels no nível raiz
    
    ESTRUTURA ANTIGA (ERRADA):
    {
      "sites": [
        {
          "code": "palmas",
          "name": "Palmas",
          "color": "blue",
          "is_default": true
        }
      ]
    }
    
    ESTRUTURA NOVA (CORRETA):
    {
      "sites": [
        {
          "code": "palmas",
          "name": "Palmas (TO)",
          "is_default": true,
          "color": "blue",
          "cluster": "palmas-master",
          "datacenter": "skillsit-palmas-to",
          "environment": "production",
          "site": "palmas",
          "prometheus_instance": "172.16.1.26",
          "prometheus_port": 5522
        }
      ]
    }
    """
    kv = KVManager()
    
    print("=" * 80)
    print("MIGRAÇÃO: Estrutura do KV skills/eye/metadata/sites")
    print("=" * 80)
    
    # PASSO 1: Buscar external_labels do KV fields
    print("\n[1] Buscando external_labels do KV fields...")
    
    fields_data = await kv.get_json('skills/eye/metadata/fields')
    
    if not fields_data:
        print("❌ KV fields não existe!")
        return False
    
    # Estrutura pode ter wrapper 'data' ou ser direta
    # Tentar ambos os formatos
    if 'data' in fields_data:
        extraction_status = fields_data.get('data', {}).get('extraction_status', {})
    else:
        extraction_status = fields_data.get('extraction_status', {})
    
    server_status = extraction_status.get('server_status', [])
    
    print(f"✅ {len(server_status)} servidores encontrados no KV fields")
    
    # Mapear hostname → external_labels
    hostname_to_labels = {}
    for server in server_status:
        hostname = server.get('hostname')
        external_labels = server.get('external_labels', {})
        
        if hostname and external_labels:
            hostname_to_labels[hostname] = external_labels
            print(f"   {hostname}: {len(external_labels)} labels")
    
    if not hostname_to_labels:
        print("❌ Nenhum external_label encontrado!")
        return False
    
    # PASSO 2: Buscar sites atuais do KV
    print("\n[2] Buscando sites atuais do KV...")
    
    sites_data = await kv.get_json('skills/eye/metadata/sites') or {"sites": []}
    current_sites = sites_data.get('sites', [])
    
    print(f"✅ {len(current_sites)} sites encontrados no KV sites")
    
    # Mapear code → site config
    code_to_site = {s['code']: s for s in current_sites}
    
    # PASSO 3: Buscar configuração de servidores (.env)
    print("\n[3] Buscando configuração de servidores do .env...")
    
    prometheus_hosts_str = os.getenv("PROMETHEUS_CONFIG_HOSTS", "")
    raw_hosts = [h.strip() for h in prometheus_hosts_str.split(';') if h.strip()]
    
    print(f"✅ {len(raw_hosts)} servidores no .env")
    
    # PASSO 4: Criar nova estrutura de sites
    print("\n[4] Criando nova estrutura de sites...")
    
    new_sites = []
    
    for host_str in raw_hosts:
        parts = host_str.split('/')
        if len(parts) != 3:
            continue
        
        host_port = parts[0]
        host_parts = host_port.split(':')
        if len(host_parts) != 2:
            continue
        
        hostname = host_parts[0]
        ssh_port = int(host_parts[1]) if host_parts[1].isdigit() else 22
        
        # Buscar external_labels deste servidor
        external_labels = hostname_to_labels.get(hostname, {})
        
        if not external_labels:
            print(f"⚠️  {hostname}: Sem external_labels, pulando...")
            continue
        
        # Detectar code do site
        site_code = external_labels.get('site', hostname.replace('.', '_'))
        
        # Buscar config existente
        existing_config = code_to_site.get(site_code, {})
        
        # Montar novo site com external_labels no nível raiz
        new_site = {
            # Campos editáveis (preservar se existem)
            "code": site_code,
            "name": existing_config.get("name", site_code.title()),
            "is_default": existing_config.get("is_default", False),
            "color": existing_config.get("color", "blue"),
            
            # Campos de external_labels (readonly)
            "cluster": external_labels.get("cluster", ""),
            "datacenter": external_labels.get("datacenter", ""),
            "environment": external_labels.get("environment", ""),
            "site": external_labels.get("site", site_code),
            "prometheus_instance": external_labels.get("prometheus_instance", hostname),
            
            # Conexão (hostname é o mesmo para SSH e Prometheus)
            "prometheus_host": hostname,
            "ssh_port": ssh_port,  # Porta SSH (22, 5522, etc)
            "prometheus_port": 9090,  # Porta Prometheus (sempre 9090)
        }
        
        new_sites.append(new_site)
        
        print(f"\n   ✅ Site: {site_code}")
        print(f"      Nome: {new_site['name']}")
        print(f"      Cluster: {new_site['cluster']}")
        print(f"      Datacenter: {new_site['datacenter']}")
        print(f"      Environment: {new_site['environment']}")
        print(f"      Host: {new_site['prometheus_host']}")
        print(f"      SSH Port: {new_site['ssh_port']}")
        print(f"      Prometheus Port: {new_site['prometheus_port']}")
    
    # PASSO 5: Salvar nova estrutura no KV
    print(f"\n[5] Salvando nova estrutura no KV...")
    
    new_structure = {
        "sites": new_sites,
        "meta": {
            "version": "2.0.0",
            "migrated_at": "2025-11-12",
            "structure": "external_labels_at_root",
            "total_sites": len(new_sites)
        }
    }
    
    success = await kv.put_json(
        key='skills/eye/metadata/sites',
        value=new_structure,
        metadata={
            'migrated': True,
            'structure_version': '2.0.0',
            'source': 'migration_script'
        }
    )
    
    if success:
        print(f"✅ Nova estrutura salva com sucesso!")
        print(f"   Total de sites: {len(new_sites)}")
    else:
        print(f"❌ Erro ao salvar no KV!")
        return False
    
    # PASSO 6: Validar
    print(f"\n[6] Validando estrutura salva...")
    
    saved_data = await kv.get_json('skills/eye/metadata/sites')
    saved_sites = saved_data.get('sites', [])
    
    print(f"✅ Validação: {len(saved_sites)} sites salvos")
    
    for site in saved_sites:
        required_fields = ['code', 'name', 'cluster', 'datacenter', 'environment', 
                          'site', 'prometheus_instance', 'prometheus_host', 'ssh_port', 'prometheus_port']
        missing = [f for f in required_fields if not site.get(f)]
        
        if missing:
            print(f"⚠️  Site {site['code']}: Campos faltando: {missing}")
        else:
            print(f"✅ Site {site['code']}: Estrutura completa")
    
    print("\n" + "=" * 80)
    print("✅ MIGRAÇÃO COMPLETA!")
    print("=" * 80)
    print("\nESTRUTURA FINAL:")
    
    import json
    print(json.dumps(new_structure, indent=2, ensure_ascii=False))
    
    return True

async def main():
    try:
        success = await migrate_sites_structure()
        
        if success:
            print("\n🎉 MIGRAÇÃO CONCLUÍDA COM SUCESSO!")
            print("\nPRÓXIMOS PASSOS:")
            print("1. Reiniciar backend para recarregar KV")
            print("2. Verificar abas External Labels e Gerenciar Sites")
        else:
            print("\n❌ MIGRAÇÃO FALHOU!")
            
    except Exception as e:
        print(f"\n❌ ERRO: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
