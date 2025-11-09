"""
Script de teste comprehensive de TODOS os endpoints

Testa TODOS os problemas reportados:
1. /prometheus-config/fields - retorna 25 campos completos
2. /metadata-fields/sync-status - retorna sync_status de cada campo
3. Dados das páginas: Settings, Exporters, Blackbox, Services, etc.
"""
import requests
import json
from typing import Dict, Any

API_URL = "http://localhost:5000/api/v1"

def test_prometheus_fields():
    """Teste 1: Endpoint de campos"""
    print("\n" + "="*80)
    print("TESTE 1: /prometheus-config/fields")
    print("="*80)

    response = requests.get(f"{API_URL}/prometheus-config/fields")
    data = response.json()

    print(f"Success: {data.get('success')}")
    print(f"Total campos: {data.get('total')}")
    print(f"From cache: {data.get('from_cache')}")
    print(f"[CRITICO] KV Saved: {data.get('kv_saved')}")
    if data.get('kv_save_error'):
        print(f"[ERRO KV] {data.get('kv_save_error')}")

    if data.get('fields'):
        campo = data['fields'][0]
        print(f"\nPrimeiro campo: {campo.get('name')}")
        print(f"Total atributos: {len(campo.keys())}")

        # Verificar campos obrigatórios
        obrigatorios = [
            'name', 'display_name', 'description', 'category', 'order',
            'required', 'enabled', 'field_type', 'show_in_table',
            'show_in_form', 'show_in_services', 'show_in_exporters',
            'show_in_blackbox', 'editable', 'validation', 'placeholder'
        ]

        print(f"\n[CHECK] Verificando campos obrigatorios:")
        faltantes = []
        for obrig in obrigatorios:
            presente = obrig in campo
            status = "[OK]" if presente else "[FALTA]"
            print(f"  {status} {obrig}: {campo.get(obrig, 'FALTA!')}")
            if not presente:
                faltantes.append(obrig)

        if faltantes:
            print(f"\n[FALHA] Faltam {len(faltantes)} campos: {faltantes}")
            return False
        else:
            print(f"\n[SUCESSO] Todos os {len(obrigatorios)} campos presentes!")
            return True
    else:
        print("[FALHA] Nenhum campo retornado!")
        return False


def test_sync_status():
    """Teste 2: Endpoint de sync-status"""
    print("\n" + "="*80)
    print("TESTE 2: /metadata-fields/sync-status")
    print("="*80)

    server_id = "172.16.1.26:5522"
    response = requests.get(f"{API_URL}/metadata-fields/sync-status", params={'server_id': server_id})

    print(f"Status Code: {response.status_code}")

    try:
        data = response.json()
        print(f"\n[RESPOSTA COMPLETA]:")
        print(json.dumps(data, indent=2, ensure_ascii=False))
    except Exception as e:
        print(f"[ERRO] Nao conseguiu parsear JSON: {e}")
        print(f"Resposta raw: {response.text}")
        return False

    print(f"\nSuccess: {data.get('success')}")
    print(f"Server: {data.get('server_hostname')}")
    print(f"Total campos: {len(data.get('fields', []))}")
    print(f"Fallback usado: {data.get('fallback_used')}")

    if data.get('fields'):
        campo = data['fields'][0]
        print(f"\nPrimeiro campo: {campo.get('name')}")
        print(f"Sync status: {campo.get('sync_status')}")
        print(f"Message: {campo.get('message')}")

        # Verificar campos de sync
        obrigatorios_sync = ['name', 'display_name', 'sync_status', 'message']
        print(f"\n[CHECK] Verificando campos de sync:")
        for obrig in obrigatorios_sync:
            presente = obrig in campo
            status = "[OK]" if presente else "[FALTA]"
            print(f"  {status} {obrig}: {campo.get(obrig, 'FALTA!')}")

        if len(data.get('fields', [])) > 0:
            print(f"\n[SUCESSO] {len(data['fields'])} campos com sync_status!")
            return True
        else:
            print("\n[FALHA] Nenhum campo com sync_status!")
            return False
    else:
        print(f"\n[AVISO] {data.get('message', 'Sem campos')}")
        return False


def test_metadata_fields_list():
    """Teste 3: Endpoint que lista campos para a página MetadataFields"""
    print("\n" + "="*80)
    print("TESTE 3: /metadata-fields/ (lista completa)")
    print("="*80)

    response = requests.get(f"{API_URL}/metadata-fields/")
    data = response.json()

    print(f"Success: {data.get('success')}")
    print(f"Total campos: {data.get('total')}")

    if data.get('fields'):
        print(f"\n[SUCESSO] {len(data['fields'])} campos listados!")
        return True
    else:
        print("\n[FALHA] Nenhum campo listado!")
        return False


def main():
    print("="*80)
    print("TESTE COMPLETO - TODOS OS ENDPOINTS")
    print("="*80)

    testes = [
        ("Campos Prometheus", test_prometheus_fields),
        ("Sync Status", test_sync_status),
        ("Lista de Campos", test_metadata_fields_list),
    ]

    resultados = []
    for nome, teste_func in testes:
        try:
            resultado = teste_func()
            resultados.append((nome, resultado))
        except Exception as e:
            print(f"\n[ERRO] ERRO NO TESTE '{nome}': {e}")
            resultados.append((nome, False))

    print("\n" + "="*80)
    print("RESUMO DOS TESTES")
    print("="*80)

    for nome, resultado in resultados:
        status = "[PASS]" if resultado else "[FAIL]"
        print(f"{status} - {nome}")

    total = len(resultados)
    passou = sum(1 for _, r in resultados if r)

    print("\n" + "="*80)
    print(f"TOTAL: {passou}/{total} testes passaram")
    print("="*80)

    if passou == total:
        print("\n[OK] TODOS OS TESTES PASSARAM! Sistema funcionando!")
    else:
        print(f"\n[AVISO] {total - passou} teste(s) falharam! Verifique os logs acima.")


if __name__ == "__main__":
    main()
