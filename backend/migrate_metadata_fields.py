"""
Script para migrar metadata_fields.json para o novo schema

Adiciona as novas propriedades:
- enabled
- show_in_filter
- show_in_blackbox
- show_in_exporters
- show_in_services
- available_for_registration
- placeholder
- default_value
- validation
"""

import json
from pathlib import Path
from datetime import datetime

# Caminho do arquivo
json_path = Path(__file__).parent / 'config' / 'metadata_fields.json'

# Carregar JSON atual
with open(json_path, 'r', encoding='utf-8') as f:
    data = json.load(f)

# Campos que aparecem apenas em contextos específicos
BLACKBOX_ONLY_FIELDS = ['module']  # module só em blackbox
EXPORTERS_ONLY_FIELDS = ['os']  # os só em exporters

# Campos obrigatórios
REQUIRED_FIELDS = ['company', 'tipo_monitoramento', 'grupo_monitoramento', 'name', 'instance']

# Campos que aparecem em filtros
FILTER_FIELDS = ['company', 'tipo_monitoramento', 'grupo_monitoramento', 'module', 'vendor', 'env', 'instance']

# Migrar cada campo
for field in data['fields']:
    field_name = field['name']

    # Adicionar propriedades novas (com defaults inteligentes)
    if 'enabled' not in field:
        field['enabled'] = True

    if 'show_in_filter' not in field:
        field['show_in_filter'] = field_name in FILTER_FIELDS

    if 'show_in_blackbox' not in field:
        # Se for campo específico de exporters, não mostrar em blackbox
        if field_name in EXPORTERS_ONLY_FIELDS:
            field['show_in_blackbox'] = False
        else:
            field['show_in_blackbox'] = True

    if 'show_in_exporters' not in field:
        # Se for campo específico de blackbox (module), não mostrar em exporters
        if field_name in BLACKBOX_ONLY_FIELDS:
            field['show_in_exporters'] = False
        else:
            field['show_in_exporters'] = True

    if 'show_in_services' not in field:
        field['show_in_services'] = True

    if 'available_for_registration' not in field:
        # Campos com opções pré-definidas geralmente não permitem novos valores
        has_options = 'options' in field and field['options']
        field['available_for_registration'] = not has_options

    if 'placeholder' not in field:
        # Gerar placeholder baseado no tipo
        if field.get('field_type') == 'select':
            field['placeholder'] = f"Selecione {field['display_name'].lower()}"
        else:
            field['placeholder'] = field['display_name']

    if 'default_value' not in field:
        field['default_value'] = None

    if 'validation' not in field:
        validation = {}

        # Campos obrigatórios têm mensagem de required
        if field.get('required'):
            validation['required_message'] = f"Informe {field['display_name'].lower()}"

        # Campos string têm limites de tamanho
        if field.get('field_type') == 'string':
            validation['min_length'] = 1
            validation['max_length'] = 200

        field['validation'] = validation

    # Garantir que required está correto
    if 'required' in field:
        field['required'] = field_name in REQUIRED_FIELDS

# Atualizar metadata do arquivo
data['version'] = '2.0.0'
data['last_updated'] = datetime.now().isoformat() + 'Z'
data['_comment'] = 'Sistema TOTALMENTE DINÂMICO - Campos controlam sua própria visibilidade'
data['_schema_version'] = '2.0'

# Backup do arquivo original
backup_path = json_path.with_suffix('.json.backup')
with open(backup_path, 'w', encoding='utf-8') as f:
    with open(json_path, 'r', encoding='utf-8') as original:
        f.write(original.read())

print(f"[OK] Backup criado: {backup_path}")

# Salvar novo JSON
with open(json_path, 'w', encoding='utf-8') as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

print(f"[OK] Arquivo migrado: {json_path}")
print(f"[OK] Total de campos: {len(data['fields'])}")
print(f"[OK] Versao: {data['version']}")

# Mostrar alguns campos como exemplo
print("\n[EXEMPLO] Campos migrados:")
for field in data['fields'][:3]:
    print(f"\n  {field['name']}:")
    print(f"    - enabled: {field['enabled']}")
    print(f"    - show_in_blackbox: {field['show_in_blackbox']}")
    print(f"    - show_in_exporters: {field['show_in_exporters']}")
    print(f"    - show_in_filter: {field['show_in_filter']}")
    print(f"    - available_for_registration: {field['available_for_registration']}")
