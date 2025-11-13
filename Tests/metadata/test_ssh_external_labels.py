#!/usr/bin/env python3
"""
Script de teste para buscar external_labels via SSH
"""
import paramiko
import os
from io import StringIO
from ruamel.yaml import YAML
from dotenv import load_dotenv

load_dotenv()

def test_ssh_external_labels():
    """Testa conexão SSH e extração de external_labels"""

    # Parse PROMETHEUS_CONFIG_HOSTS
    config_hosts_str = os.getenv("PROMETHEUS_CONFIG_HOSTS", "")

    if not config_hosts_str:
        print("❌ PROMETHEUS_CONFIG_HOSTS não configurado no .env")
        return

    print(f"✓ PROMETHEUS_CONFIG_HOSTS encontrado")
    print(f"  Servidores configurados: {len(config_hosts_str.split(';'))}")

    # Parse primeiro servidor
    host_entry = config_hosts_str.split(";")[0]
    print(f"\n📡 Testando primeiro servidor: {host_entry}")

    parts = host_entry.split("/")
    host_port = parts[0]
    host_parts = host_port.split(":")
    hostname = host_parts[0]
    port = int(host_parts[1]) if len(host_parts) > 1 else 22
    username = parts[1] if len(parts) > 1 else "root"
    password = parts[2] if len(parts) > 2 else None

    print(f"  Hostname: {hostname}")
    print(f"  Port: {port}")
    print(f"  Username: {username}")
    print(f"  Password: {'***' if password else 'None (usando chave SSH)'}")

    # Conectar via SSH
    print(f"\n🔐 Conectando via SSH...")
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        if password:
            client.connect(
                hostname=hostname,
                port=port,
                username=username,
                password=password,
                timeout=10
            )
        else:
            client.connect(
                hostname=hostname,
                port=port,
                username=username,
                look_for_keys=True,
                timeout=10
            )

        print(f"✓ Conectado com sucesso!")

        # Ler prometheus.yml
        prometheus_path = "/etc/prometheus/prometheus.yml"
        print(f"\n📄 Lendo arquivo {prometheus_path}...")

        sftp = client.open_sftp()
        with sftp.open(prometheus_path, 'r') as f:
            content = f.read().decode('utf-8')

        sftp.close()
        client.close()

        print(f"✓ Arquivo lido ({len(content)} bytes)")

        # Parse YAML
        print(f"\n🔍 Parseando YAML...")
        yaml = YAML()
        yaml.preserve_quotes = True
        config = yaml.load(StringIO(content))

        print(f"✓ YAML parseado com sucesso")
        print(f"  Keys encontradas: {list(config.keys())}")

        # Extrair external_labels
        global_section = config.get('global', {})
        external_labels = global_section.get('external_labels', {})

        print(f"\n🏷️  External Labels encontrados:")
        if external_labels:
            for key, value in external_labels.items():
                print(f"  - {key}: {value}")
            print(f"\n✅ SUCESSO! {len(external_labels)} external_labels extraídos")
        else:
            print(f"  ⚠️  Nenhum external_label configurado no prometheus.yml")

        return external_labels

    except paramiko.AuthenticationException as e:
        print(f"❌ Erro de autenticação SSH: {e}")
    except paramiko.SSHException as e:
        print(f"❌ Erro SSH: {e}")
    except FileNotFoundError as e:
        print(f"❌ Arquivo não encontrado: {e}")
    except Exception as e:
        print(f"❌ Erro: {e}")
        import traceback
        traceback.print_exc()
    finally:
        try:
            client.close()
        except:
            pass

if __name__ == "__main__":
    print("=" * 60)
    print("TESTE: Buscar external_labels via SSH")
    print("=" * 60)
    test_ssh_external_labels()
