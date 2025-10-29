"""
Teste COMPLETO do fluxo SED
Simula exatamente o que acontece quando usuário clica em Salvar
"""
import sys
sys.path.insert(0, 'c:/consul-manager-web/backend')

# Configurar logging
import logging
logging.basicConfig(level=logging.INFO, format='%(message)s')

try:
    from core.multi_config_manager import MultiConfigManager

    # Simular jobs do arquivo (14 jobs reais)
    old_jobs = []
    for i in range(14):
        old_jobs.append({
            'job_name': f'job_{i}',
            'metrics_path': '/metrics',
            'params': {'module': ['test']},
            'consul_sd_configs': [{'tags': ['old_tag']}]
        })

    # Simular mudança do usuário (editou job_5, mudou tags)
    new_jobs = []
    for i in range(14):
        if i == 5:
            # JOB MODIFICADO
            new_jobs.append({
                'job_name': f'job_{i}',
                'metrics_path': '/metrics',
                'params': {'module': ['test']},
                'consul_sd_configs': [{'tags': ['NEW_TAG']}]  # MUDANÇA AQUI
            })
        else:
            # Job não modificado
            new_jobs.append({
                'job_name': f'job_{i}',
                'metrics_path': '/metrics',
                'params': {'module': ['test']},
                'consul_sd_configs': [{'tags': ['old_tag']}]
            })

    print("[TEST] Criando MultiConfigManager...")
    manager = MultiConfigManager()

    print("[TEST] Detectando mudanças...")
    changes = manager._detect_simple_changes(old_jobs, new_jobs)

    print(f"[TEST] Mudancas detectadas: {len(changes)}")

    for i, change in enumerate(changes):
        print(f"[TEST] Mudanca {i+1}:")
        print(f"  Pattern: {change['pattern']}")
        print(f"  Replacement: {change['replacement']}")
        print(f"  Description: {change['description']}")
        print()

    if len(changes) == 1:
        print("[SUCCESS] Detectou exatamente 1 mudanca (job_5)!")
    else:
        print(f"[ERROR] Esperava 1 mudanca, detectou {len(changes)}")

except Exception as e:
    print(f"[ERROR] Erro: {e}")
    import traceback
    traceback.print_exc()
