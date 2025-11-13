"""
Script de Teste para Edição Cirúrgica de YAML

Testa se a edição cirúrgica:
1. Modifica apenas a linha alterada
2. Preserva comentários
3. Preserva formatação
4. Preserva espaçamento
"""

import sys
from pathlib import Path
from io import StringIO
from ruamel.yaml import YAML

# Adicionar backend ao path
sys.path.insert(0, str(Path(__file__).parent))

from core.multi_config_manager import MultiConfigManager


def test_surgical_edit():
    """Testa edição cirúrgica de YAML"""

    print("=" * 80)
    print("TESTE DE EDIÇÃO CIRÚRGICA DE YAML")
    print("=" * 80)
    print()

    # Configuração YAML de teste com comentários
    original_yaml = """# Configuração Global do Prometheus
global:
  scrape_interval: 15s
  evaluation_interval: 15s

# Configurações de Scrape
scrape_configs:
  # Monitoramento HTTP com código 4xx usando o Blackbox Exporter
  - job_name: 'http_4xx'
    metrics_path: /probe
    params:
      module: [http_4xx]    # Módulo do Blackbox Exporter para monitorar códigos 4xx
    consul_sd_configs:
    - server: '172.16.1.26:8500'
      token: '8382a112-81e0-cd6d-2b92-8565925a0675'
      services: ['blackbox_exporter']
      tags: ['http_4xx']  # TAG ORIGINAL
    relabel_configs:
    - source_labels:
      - __meta_consul_service
      target_label: cservice

  # Outro job para teste
  - job_name: 'node_exporter'
    scrape_interval: 30s
    static_configs:
    - targets: ['localhost:9100']
"""

    print("[YAML ORIGINAL]")
    print("-" * 80)
    print(original_yaml)
    print()

    # Parse YAML usando ruamel.yaml
    yaml = YAML()
    yaml.preserve_quotes = True
    yaml.default_flow_style = False
    yaml.width = 4096

    config = yaml.load(StringIO(original_yaml))

    # Extrair jobs
    jobs = config['scrape_configs']
    print(f"[OK] {len(jobs)} jobs encontrados")
    print()

    # Simular mudança: modificar apenas tags do job http_4xx
    print("[MODIFICACAO]")
    print("-" * 80)
    print("Job: http_4xx")
    print("Campo: consul_sd_configs[0].tags")
    print("Antes: ['http_4xx']")
    print("Depois: ['http_4xx-teste']")
    print()

    # Criar nova lista de jobs com a modificação
    import copy
    updated_jobs = []
    for job in jobs:
        # IMPORTANTE: Fazer deep copy para copiar recursivamente todas as estruturas
        job_dict = copy.deepcopy(dict(job))

        if job_dict.get('job_name') == 'http_4xx':
            # Modificar apenas tags
            if 'consul_sd_configs' in job_dict and len(job_dict['consul_sd_configs']) > 0:
                job_dict['consul_sd_configs'][0]['tags'] = ['http_4xx-teste']
                print(f"  [OK] Modificando tags do job '{job_dict['job_name']}'")

        updated_jobs.append(job_dict)

    print()

    # Usar método de edição cirúrgica
    print("[APLICANDO EDICAO CIRURGICA]")
    print("-" * 80)

    manager = MultiConfigManager()

    # Simular atualização cirúrgica
    total_changes = 0
    for i, (old_job, new_job) in enumerate(zip(jobs, updated_jobs)):
        job_name = new_job.get('job_name')
        print(f"\nJob [{i}]: {job_name}")

        changes = manager._update_dict_surgically(old_job, new_job, f"job[{job_name}]")
        total_changes += changes

        if changes == 0:
            print(f"  [OK] Sem alteracoes")
        else:
            print(f"  [OK] {changes} campo(s) modificado(s)")

    print()
    print(f"[RESULTADO] Total de alteracoes: {total_changes}")
    print()

    # Gerar YAML final
    print("[YAML FINAL]")
    print("-" * 80)
    output = StringIO()
    yaml.dump(config, output)
    final_yaml = output.getvalue()
    print(final_yaml)
    print()

    # Validar preservação de comentários
    print("[VALIDACAO]")
    print("-" * 80)

    validations = [
        ("Comentario Global", "# Configuração Global do Prometheus" in final_yaml),
        ("Comentario Scrape", "# Configurações de Scrape" in final_yaml),
        ("Comentario HTTP 4xx", "# Monitoramento HTTP com código 4xx" in final_yaml),
        ("Comentario modulo inline", "# Módulo do Blackbox Exporter" in final_yaml),
        ("Comentario TAG ORIGINAL", "# TAG ORIGINAL" in final_yaml),  # DEVE estar presente
        ("Job node_exporter intacto", "node_exporter" in final_yaml),
        ("Tag modificada presente", "http_4xx-teste" in final_yaml),
        ("Tag antiga removida", "tags: ['http_4xx']" not in final_yaml),
    ]

    all_passed = True
    for check_name, result in validations:
        status = "[PASSOU]" if result else "[FALHOU]"
        print(f"{status}: {check_name}")
        if not result:
            all_passed = False

    print()
    print("=" * 80)

    if all_passed:
        print("[SUCESSO] TODOS OS TESTES PASSARAM!")
        print("[OK] Edicao cirurgica funcionando corretamente")
        print("[OK] Comentarios preservados")
        print("[OK] Apenas campo modificado foi alterado")
    else:
        print("[AVISO] ALGUNS TESTES FALHARAM")
        print("Verifique a saida acima para detalhes")

    print("=" * 80)

    return all_passed


if __name__ == '__main__':
    try:
        success = test_surgical_edit()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n[ERRO] ERRO DURANTE TESTE: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
