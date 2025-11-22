#!/usr/bin/env python3
"""
Script para padronizar tags do Swagger em Title Case
Corrige inconsistências entre definições de routers e registros em app.py

EXECUÇÃO SEGURA:
1. Faz backup de todos os arquivos antes de modificar
2. Aplica correções consistentes
3. Valida mudanças
"""

import re
import os
from pathlib import Path

# ==============================================================================
# MAPEAMENTO COMPLETO: kebab-case → Title Case
# ==============================================================================

TAG_MAPPING = {
    # Tags já em kebab-case que precisam virar Title Case
    'services': 'Services',
    'nodes': 'Nodes', 
    'config': 'Config',
    'blackbox': 'Blackbox',
    'kv': 'Key-Value Store',  # Melhor nome descritivo
    'presets': 'Service Presets',
    'search': 'Search',
    'consul': 'Consul Insights',
    'audit': 'Audit Logs',
    'dashboard': 'Dashboard',
    'optimized': 'Optimized Endpoints',
    'prometheus-config': 'Prometheus Config',
    'metadata-fields': 'Metadata Fields',
    'monitoring-types-dynamic': 'Monitoring Types',
    'reference-values': 'Reference Values',
    'service-tags': 'Service Tags',
    'settings': 'Settings',
    'installer': 'Installer',
    'health': 'Health Check',
    'metadata-dynamic': 'Dynamic Metadata',
    
    # Tags que já estão em Title Case mas precisam ser padronizadas
    'Metadata Fields': 'Metadata Fields',
    'Monitoring Types Dynamic': 'Monitoring Types',
    'Prometheus Config': 'Prometheus Config',
    'services-optimized': 'Services (Optimized)',
    'Settings': 'Settings'
}

# Routers que precisam de tags adicionadas
ROUTERS_MISSING_TAGS = {
    'blackbox.py': 'Blackbox',
    'config.py': 'Config',
    'consul_insights.py': 'Consul Insights',
    'health.py': 'Health Check',
    'installer.py': 'Installer',
    'kv.py': 'Key-Value Store',
    'nodes.py': 'Nodes',
    'presets.py': 'Service Presets',
    'reference_values.py': 'Reference Values',
    'search.py': 'Search',
    'service_tags.py': 'Service Tags',
    'services.py': 'Services'
}

# ==============================================================================
# FUNÇÕES DE PROCESSAMENTO
# ==============================================================================

def backup_file(filepath: str) -> str:
    """Cria backup do arquivo antes de modificar"""
    backup_path = f"{filepath}.backup"
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    with open(backup_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"  ✅ Backup criado: {backup_path}")
    return backup_path

def fix_router_tags_in_file(filepath: str, expected_tag: str) -> bool:
    """
    Corrige tags em arquivos de API
    
    Casos tratados:
    1. Router sem tags → adiciona tags=[expected_tag]
    2. Router com tags incorretas → substitui pela correta
    """
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original_content = content
    modified = False
    
    # CASO 1: Router SEM tags definidas
    # Procura: router = APIRouter() ou router = APIRouter(prefix="/algo")
    # Adiciona: tags=["Expected Tag"]
    pattern_no_tags = r'(router\s*=\s*APIRouter\([^)]*?)(\))'
    
    def add_tags_if_missing(match):
        nonlocal modified
        router_def = match.group(1)
        
        # Verifica se já tem tags
        if 'tags=' in router_def:
            return match.group(0)  # Já tem tags, não mexe
        
        # Adiciona tags
        modified = True
        if router_def.strip().endswith('('):
            # Caso: APIRouter()
            return f'{router_def}tags=["{expected_tag}"])'
        else:
            # Caso: APIRouter(prefix="/algo")
            return f'{router_def}, tags=["{expected_tag}"])'
    
    content = re.sub(pattern_no_tags, add_tags_if_missing, content)
    
    # CASO 2: Router COM tags incorretas
    # Procura: tags=["Qualquer Coisa"]
    # Substitui: tags=["Expected Tag"]
    pattern_with_tags = r'tags=\[(["\'])([^"\']+)\1\]'
    
    def fix_existing_tags(match):
        nonlocal modified
        quote_type = match.group(1)
        current_tag = match.group(2)
        
        if current_tag != expected_tag:
            modified = True
            return f'tags=[{quote_type}{expected_tag}{quote_type}]'
        return match.group(0)
    
    content = re.sub(pattern_with_tags, fix_existing_tags, content)
    
    # Salva se houve modificações
    if modified and content != original_content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        return True
    
    return False

def fix_app_py_registrations():
    """Corrige todas as registrações de routers em app.py para Title Case"""
    app_path = 'app.py'
    
    print("\n📝 Corrigindo app.py...")
    backup_file(app_path)
    
    with open(app_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original_content = content
    
    # Substitui todas as tags nas registrações de routers
    def replace_tag(match):
        router_var = match.group(1)
        prefix = match.group(2)
        current_tag = match.group(3).strip('"\'')
        
        # Converte para Title Case usando o mapeamento
        new_tag = TAG_MAPPING.get(current_tag, current_tag)
        
        return f'app.include_router({router_var}, prefix="{prefix}", tags=["{new_tag}"]'
    
    # Pattern para capturar include_router com tags
    pattern = r'app\.include_router\((\w+),\s*prefix="([^"]*)",\s*tags=\[([^\]]+)\]'
    content = re.sub(pattern, replace_tag, content)
    
    if content != original_content:
        with open(app_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print("  ✅ app.py atualizado com sucesso!")
        return True
    else:
        print("  ℹ️  app.py já estava correto")
        return False

def fix_api_files():
    """Corrige todos os arquivos em backend/api/"""
    api_dir = Path('api')
    
    print("\n📝 Corrigindo arquivos em api/...")
    
    files_modified = 0
    
    for filename, expected_tag in ROUTERS_MISSING_TAGS.items():
        filepath = api_dir / filename
        
        if not filepath.exists():
            print(f"  ⚠️  Arquivo não encontrado: {filename}")
            continue
        
        print(f"\n  📄 Processando {filename}...")
        backup_file(str(filepath))
        
        if fix_router_tags_in_file(str(filepath), expected_tag):
            print(f"    ✅ Tags corrigidas para '{expected_tag}'")
            files_modified += 1
        else:
            print(f"    ℹ️  Nenhuma modificação necessária")
    
    # Corrige também arquivos que JÁ TEM tags mas estão inconsistentes
    inconsistent_files = {
        'metadata_fields_manager.py': 'Metadata Fields',
        'monitoring_types_dynamic.py': 'Monitoring Types',
        'prometheus_config.py': 'Prometheus Config',
        'services_optimized.py': 'Services (Optimized)',
        'settings.py': 'Settings'
    }
    
    for filename, expected_tag in inconsistent_files.items():
        filepath = api_dir / filename
        
        if not filepath.exists():
            continue
        
        print(f"\n  📄 Padronizando {filename}...")
        backup_file(str(filepath))
        
        if fix_router_tags_in_file(str(filepath), expected_tag):
            print(f"    ✅ Tag padronizada para '{expected_tag}'")
            files_modified += 1
        else:
            print(f"    ℹ️  Já estava correto")
    
    return files_modified

def validate_changes():
    """Valida que todas as mudanças foram aplicadas corretamente"""
    print("\n🔍 Validando mudanças...")
    
    # Ler app.py e extrair todas as tags
    with open('app.py', 'r') as f:
        app_content = f.read()
    
    app_tags = re.findall(r'tags=\[(["\'])([^"\']+)\1\]', app_content)
    
    print("\n📊 Tags registradas em app.py:")
    for _, tag in sorted(set(app_tags), key=lambda x: x[1]):
        print(f"  - {tag}")
    
    # Verificar se há tags em kebab-case
    kebab_found = [tag for _, tag in app_tags if '-' in tag and tag[0].islower()]
    
    if kebab_found:
        print(f"\n⚠️  AVISO: Tags em kebab-case encontradas:")
        for tag in kebab_found:
            print(f"  - '{tag}' (deveria ser Title Case)")
        return False
    else:
        print("\n✅ Todas as tags estão em Title Case!")
        return True

# ==============================================================================
# EXECUÇÃO PRINCIPAL
# ==============================================================================

def main():
    print("=" * 80)
    print("PADRONIZAÇÃO DE TAGS DO SWAGGER - Title Case")
    print("=" * 80)
    
    # Verifica se está no diretório correto
    if not os.path.exists('app.py'):
        print("\n❌ ERRO: Execute este script no diretório backend/")
        return 1
    
    print("\n📋 Operações que serão realizadas:")
    print("  1. Backup de todos os arquivos antes de modificar")
    print("  2. Atualizar app.py para usar Title Case nas tags")
    print("  3. Adicionar tags em routers sem definição")
    print("  4. Padronizar tags inconsistentes")
    print("  5. Validar todas as mudanças")
    
    input("\n⏸️  Pressione ENTER para continuar ou Ctrl+C para cancelar...")
    
    try:
        # Passo 1: Corrigir app.py
        fix_app_py_registrations()
        
        # Passo 2: Corrigir arquivos API
        files_modified = fix_api_files()
        
        # Passo 3: Validar
        validation_ok = validate_changes()
        
        print("\n" + "=" * 80)
        print("RESUMO DA EXECUÇÃO")
        print("=" * 80)
        print(f"✅ app.py corrigido")
        print(f"✅ {files_modified} arquivos API modificados")
        print(f"{'✅' if validation_ok else '⚠️ '} Validação: {'Sucesso' if validation_ok else 'Verificar warnings'}")
        
        print("\n💡 PRÓXIMOS PASSOS:")
        print("  1. Reiniciar o backend: cd .. && ./restart-backend.sh")
        print("  2. Acessar http://localhost:5000/docs")
        print("  3. Verificar se não há duplicatas no Swagger UI")
        print("  4. Testar alguns endpoints")
        print("  5. Commit: git add . && git commit -m 'refactor: Padronizar tags Swagger para Title Case'")
        
        return 0
        
    except Exception as e:
        print(f"\n❌ ERRO durante execução: {e}")
        print("\n🔧 Para reverter mudanças:")
        print("  find . -name '*.backup' -exec bash -c 'mv \"$1\" \"${1%.backup}\"' _ {} \\;")
        return 1

if __name__ == '__main__':
    exit(main())
