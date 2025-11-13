"""
Teste da edição TEXT-BASED de YAML
"""

# Simular conteúdo YAML real
yaml_content = """
# Monitoramento HTTP com código 2xx usando o Blackbox Exporter
- job_name: 'http_2xx'
  metrics_path: /probe
  params:
    module: [http_2xx]    # Módulo do Blackbox Exporter para monitorar HTTP
  consul_sd_configs:
  - server: '172.16.1.26:8500'      # Servidor Consul central
    token: '8382a112-81e0-cd6d-2b92-8565925a0675'
    services: ['blackbox_exporter']
    tags: ['http_2xx']      # Tag específica para identificar o serviço
"""

# Valores antigo e novo
old_value = ['http_2xx']
new_value = ['http_2xx-teste']
job_name = 'http_2xx'
field_name = 'tags'

import re

def value_to_yaml_text(value):
    """Converter valor para texto YAML"""
    if isinstance(value, list):
        items = [f"'{item}'" if isinstance(item, str) else str(item) for item in value]
        return f"[{', '.join(items)}]"
    return str(value)

# Converter valores
old_yaml = value_to_yaml_text(old_value)
new_yaml = value_to_yaml_text(new_value)

print(f"[DEBUG] old_yaml: {old_yaml}")
print(f"[DEBUG] new_yaml: {new_yaml}")

# Encontrar seção do job
job_pattern = rf"(- job_name:\s*['\"]?{re.escape(job_name)}['\"]?.*?)(\n- job_name:|\nrule_files:|\Z)"
job_match = re.search(job_pattern, yaml_content, re.DOTALL)

if not job_match:
    print("[ERROR] Não encontrou o job!")
else:
    print("[OK] Job encontrado!")
    job_section = job_match.group(1)
    print(f"[DEBUG] Job section:\n{job_section}")

    # Tentar substituir
    field_pattern = rf"(\s+{re.escape(field_name)}:\s*){re.escape(old_yaml)}"
    print(f"[DEBUG] Pattern: {field_pattern}")

    if re.search(field_pattern, job_section):
        print("[OK] Pattern encontrado no job section!")

        replacement = rf"\1{new_yaml}"
        modified_section = re.sub(field_pattern, replacement, job_section, count=1)

        print(f"[DEBUG] Modified section:\n{modified_section}")

        # Verificar se mudou
        if modified_section != job_section:
            print("[SUCCESS] Substituição funcionou!")
        else:
            print("[ERROR] Substituição NÃO funcionou!")
    else:
        print("[ERROR] Pattern NÃO encontrado no job section!")

        # Tentar encontrar a linha manualmente
        for line in job_section.split('\n'):
            if 'tags:' in line:
                print(f"[DEBUG] Linha tags encontrada: '{line}'")
