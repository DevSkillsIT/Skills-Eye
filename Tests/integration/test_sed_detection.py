"""
Teste da detecção de mudanças para SED
"""

# Simular jobs antigos e novos
old_jobs = [
    {
        'job_name': 'http_2xx',
        'metrics_path': '/probe',
        'params': {'module': ['http_2xx']},
        'consul_sd_configs': [
            {
                'server': '172.16.1.26:8500',
                'token': '8382a112-81e0-cd6d-2b92-8565925a0675',
                'services': ['blackbox_exporter'],
                'tags': ['http_2xx']
            }
        ]
    }
]

new_jobs = [
    {
        'job_name': 'http_2xx',
        'metrics_path': '/probe',
        'params': {'module': ['http_2xx']},
        'consul_sd_configs': [
            {
                'server': '172.16.1.26:8500',
                'token': '8382a112-81e0-cd6d-2b92-8565925a0675',
                'services': ['blackbox_exporter'],
                'tags': ['http_2xx-SED-TESTE']  # MUDANÇA AQUI
            }
        ]
    }
]

# Importar função
import sys
sys.path.insert(0, 'c:/consul-manager-web/backend')

try:
    from core.multi_config_manager import MultiConfigManager

    manager = MultiConfigManager()

    print("[TEST] Testando detecção de mudanças...")
    changes = manager._detect_simple_changes(old_jobs, new_jobs)

    print(f"[TEST] Mudanças detectadas: {len(changes)}")
    for change in changes:
        print(f"[TEST] - {change}")

    if len(changes) > 0:
        print("[SUCCESS] Detecção funcionou!")
    else:
        print("[ERROR] Nenhuma mudança detectada!")

except Exception as e:
    print(f"[ERROR] Erro: {e}")
    import traceback
    traceback.print_exc()
