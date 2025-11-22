#!/usr/bin/env python3
"""
Script para padronizar labels entre todos os jobs do Prometheus

Garante que todos os jobs tenham os mesmos 22 campos metadata:
- cservice, vendor, region, group, account, iid, exp (campos de infraestrutura)
- instance, company, env, name, project (campos básicos)
- localizacao, fabricante, tipo, modelo, cod_localidade (campos de dispositivo)
- tipo_dispositivo_abrev, cidade, notas, glpi_URL, provedor (campos extras)
"""

import paramiko
import sys
from io import StringIO
from ruamel.yaml import YAML

# Configuração SSH
SSH_HOST = "172.16.1.26"
SSH_PORT = 5522
SSH_USER = "root"
SSH_PASS = "Skills@2021,TI"
PROMETHEUS_FILE = "/etc/prometheus/prometheus.yml"

# Lista completa de campos metadata padronizados (na ordem correta)
STANDARD_RELABEL_CONFIGS = [
    # Campos de infraestrutura/cloud (extras para blackbox)
    {'source': '__meta_consul_service', 'target': 'cservice'},
    {'source': '__meta_consul_service_metadata_vendor', 'target': 'vendor'},
    {'source': '__meta_consul_service_metadata_region', 'target': 'region'},
    {'source': '__meta_consul_service_metadata_group', 'target': 'group'},
    {'source': '__meta_consul_service_metadata_account', 'target': 'account'},
    {'source': '__meta_consul_service_metadata_iid', 'target': 'iid'},
    {'source': '__meta_consul_service_metadata_exp', 'target': 'exp'},
    {'source': '__meta_consul_service_metadata_instance', 'target': 'instance'},

    # Campos básicos (comuns a todos)
    {'source': '__meta_consul_service_metadata_company', 'target': 'company'},
    {'source': '__meta_consul_service_metadata_env', 'target': 'env'},
    {'source': '__meta_consul_service_metadata_name', 'target': 'name'},
    {'source': '__meta_consul_service_metadata_project', 'target': 'project'},

    # Campos de dispositivo (comuns a todos)
    {'source': '__meta_consul_service_metadata_localizacao', 'target': 'localizacao'},
    {'source': '__meta_consul_service_metadata_fabricante', 'target': 'fabricante'},
    {'source': '__meta_consul_service_metadata_tipo', 'target': 'tipo'},
    {'source': '__meta_consul_service_metadata_modelo', 'target': 'modelo'},
    {'source': '__meta_consul_service_metadata_cod_localidade', 'target': 'cod_localidade'},
    {'source': '__meta_consul_service_metadata_tipo_dispositivo_abrev', 'target': 'tipo_dispositivo_abrev'},
    {'source': '__meta_consul_service_metadata_cidade', 'target': 'cidade'},

    # Campos extras (faltantes em node_exporter/windows_exporter)
    {'source': '__meta_consul_service_metadata_notas', 'target': 'notas'},
    {'source': '__meta_consul_service_metadata_glpi_url', 'target': 'glpi_URL'},
    {'source': '__meta_consul_service_metadata_provedor', 'target': 'provedor'},
]


def get_ssh_client():
    """Cria conexão SSH"""
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(SSH_HOST, port=SSH_PORT, username=SSH_USER, password=SSH_PASS)
    return client


def read_prometheus_config():
    """Lê prometheus.yml do servidor"""
    client = get_ssh_client()
    sftp = client.open_sftp()

    with sftp.open(PROMETHEUS_FILE, 'r') as f:
        content = f.read().decode('utf-8')

    sftp.close()
    client.close()

    yaml = YAML()
    yaml.preserve_quotes = True
    yaml.width = 4096
    config = yaml.load(StringIO(content))

    return config, yaml


def standardize_relabel_configs(job):
    """
    Padroniza relabel_configs de um job para ter todos os 22 campos

    Mantém configs especiais como __param_target e __address__ no final
    """
    if 'relabel_configs' not in job:
        return

    current_relabels = job['relabel_configs']

    # Separar configs especiais (que não são metadata simples)
    special_configs = []
    metadata_configs = []

    for config in current_relabels:
        source = config.get('source_labels', [])
        if isinstance(source, list):
            source = source[0] if source else ''

        # Configs especiais ficam no final
        if source == '__param_target' or config.get('target_label') == '__address__':
            special_configs.append(config)
        else:
            metadata_configs.append(config)

    # Criar dict de configs existentes por target_label
    existing_by_target = {}
    for config in metadata_configs:
        target = config.get('target_label')
        if target:
            existing_by_target[target] = config

    # Construir nova lista com ordem padronizada
    new_relabels = []

    for std_config in STANDARD_RELABEL_CONFIGS:
        target = std_config['target']

        if target in existing_by_target:
            # Usar config existente (preserva formatação)
            new_relabels.append(existing_by_target[target])
        else:
            # Adicionar novo config
            new_relabels.append({
                'source_labels': [std_config['source']],
                'target_label': target
            })

    # Adicionar configs especiais no final
    new_relabels.extend(special_configs)

    job['relabel_configs'] = new_relabels


def standardize_all_jobs(config):
    """Padroniza todos os jobs que usam consul_sd_configs"""
    scrape_configs = config.get('scrape_configs', [])

    jobs_modified = []

    for job in scrape_configs:
        job_name = job.get('job_name', 'unknown')

        # Apenas jobs com Consul SD precisam de padronização
        if 'consul_sd_configs' not in job:
            continue

        # Pular job prometheus (não tem metadata)
        if job_name == 'prometheus':
            continue

        print(f"Padronizando job: {job_name}")
        standardize_relabel_configs(job)
        jobs_modified.append(job_name)

    return jobs_modified


def save_prometheus_config(config, yaml_obj):
    """Salva config de volta no servidor"""
    # Converter para string
    output = StringIO()
    yaml_obj.dump(config, output)
    yaml_content = output.getvalue()

    # Enviar para servidor
    client = get_ssh_client()
    sftp = client.open_sftp()

    with sftp.open(PROMETHEUS_FILE, 'w') as f:
        f.write(yaml_content.encode('utf-8'))

    sftp.close()
    client.close()

    print(f"\n[OK] Arquivo salvo: {PROMETHEUS_FILE}")


def validate_with_promtool():
    """Valida configuracao com promtool"""
    print("\nValidando com promtool...")

    client = get_ssh_client()
    stdin, stdout, stderr = client.exec_command(f"promtool check config {PROMETHEUS_FILE}")

    exit_status = stdout.channel.recv_exit_status()
    output = stdout.read().decode('utf-8')
    error = stderr.read().decode('utf-8')

    client.close()

    if exit_status == 0:
        print("[OK] Configuracao valida!")
        print(output)
        return True
    else:
        print("[ERRO] Erro de validacao:")
        print(output + error)
        return False


def main():
    print("=" * 60)
    print("PADRONIZAÇÃO DE LABELS DO PROMETHEUS")
    print("=" * 60)
    print(f"\nServidor: {SSH_USER}@{SSH_HOST}:{SSH_PORT}")
    print(f"Arquivo: {PROMETHEUS_FILE}")
    print(f"\nBackup criado: {PROMETHEUS_FILE}.backup_*")

    # Ler configuração
    print("\n1. Lendo configuração atual...")
    config, yaml = read_prometheus_config()

    # Padronizar
    print("\n2. Padronizando relabel_configs...")
    jobs_modified = standardize_all_jobs(config)

    print(f"\n[OK] {len(jobs_modified)} jobs modificados:")
    for job in jobs_modified:
        print(f"  - {job}")

    # Salvar
    print("\n3. Salvando configuracao...")
    save_prometheus_config(config, yaml)

    # Validar
    print("\n4. Validando configuracao...")
    if validate_with_promtool():
        print("\n" + "=" * 60)
        print("[OK] PADRONIZACAO CONCLUIDA COM SUCESSO!")
        print("=" * 60)
        print("\nTodos os jobs agora tem os mesmos 22 campos metadata.")
        print("\nProximos passos:")
        print("  1. Recarregar Prometheus: systemctl reload prometheus")
        print("  2. Verificar que os campos aparecem nas paginas")
        return 0
    else:
        print("\n" + "=" * 60)
        print("[ERRO] ERRO NA VALIDACAO")
        print("=" * 60)
        print("\nRestaurar backup se necessário:")
        print(f"  cp {PROMETHEUS_FILE}.backup_* {PROMETHEUS_FILE}")
        return 1


if __name__ == '__main__':
    sys.exit(main())
