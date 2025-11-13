"""
Script de migração do namespace Consul KV de skills/eye/ para skills/eye/
"""
import os
import re
from pathlib import Path
from collections import defaultdict

# Diretório raiz do projeto
ROOT_DIR = Path(__file__).parent

# Pastas a ignorar
IGNORE_DIRS = {'node_modules', '__pycache__', '.vite', 'venv', '.git', 'dist', 'build'}

# Extensões de arquivo para processar
FILE_EXTENSIONS = {'.py', '.ts', '.tsx', '.md', '.json', '.txt', '.yml', '.yaml', '.sh', '.bat', '.js', '.jsx'}

def find_all_occurrences():
    """Busca todas as ocorrências de 'skills/eye' nos arquivos."""
    occurrences = defaultdict(list)
    total_files_scanned = 0

    print("=" * 80)
    print("BUSCANDO TODAS AS OCORRÊNCIAS DE 'skills/eye'")
    print("=" * 80)
    print()

    for file_path in ROOT_DIR.rglob('*'):
        # Ignorar diretórios
        if file_path.is_dir():
            continue

        # Ignorar pastas blacklist
        if any(ignore in file_path.parts for ignore in IGNORE_DIRS):
            continue

        # Processar apenas extensões permitidas
        if file_path.suffix not in FILE_EXTENSIONS:
            continue

        total_files_scanned += 1

        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                for line_num, line in enumerate(f, 1):
                    if 'skills/eye' in line:
                        rel_path = file_path.relative_to(ROOT_DIR)
                        occurrences[str(rel_path)].append({
                            'line': line_num,
                            'content': line.strip()
                        })
        except Exception as e:
            print(f"[ERRO] Falha ao ler {file_path}: {e}")

    print(f"Arquivos escaneados: {total_files_scanned}")
    print(f"Arquivos com ocorrências: {len(occurrences)}")
    print()

    return occurrences

def print_occurrences(occurrences):
    """Imprime todas as ocorrências encontradas."""
    print("=" * 80)
    print("OCORRÊNCIAS ENCONTRADAS")
    print("=" * 80)
    print()

    total_lines = 0
    for file_path, lines in sorted(occurrences.items()):
        print(f"\n[FILE] {file_path} ({len(lines)} ocorrencias)")
        for item in lines[:10]:  # Mostrar primeiras 10 linhas
            # Remove caracteres não-ASCII para evitar erros de encoding no Windows
            safe_content = item['content'][:100].encode('ascii', errors='replace').decode('ascii')
            print(f"   Linha {item['line']:4d}: {safe_content}")
            total_lines += 1
        if len(lines) > 10:
            print(f"   ... e mais {len(lines) - 10} linhas")
            total_lines += len(lines) - 10

    print()
    print(f"TOTAL: {total_lines} linhas em {len(occurrences)} arquivos")
    print()

def replace_in_files(occurrences, dry_run=True):
    """Substitui 'skills/eye' por 'skills/eye' em todos os arquivos."""
    print("=" * 80)
    if dry_run:
        print("MODO DRY-RUN: Simulando substituições")
    else:
        print("APLICANDO SUBSTITUIÇÕES")
    print("=" * 80)
    print()

    files_modified = 0
    total_replacements = 0

    for file_path_str in sorted(occurrences.keys()):
        file_path = ROOT_DIR / file_path_str

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Contar quantas vezes vai substituir
            count = content.count('skills/eye')

            if count > 0:
                new_content = content.replace('skills/eye', 'skills/eye')

                if dry_run:
                    print(f"[DRY-RUN] {file_path_str}: {count} substituições")
                else:
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(new_content)
                    print(f"[MODIFICADO] {file_path_str}: {count} substituições")

                files_modified += 1
                total_replacements += count

        except Exception as e:
            print(f"[ERRO] Falha ao processar {file_path_str}: {e}")

    print()
    print(f"Arquivos modificados: {files_modified}")
    print(f"Total de substituições: {total_replacements}")
    print()

def main():
    print("\nFASE 1: BUSCA DE OCORRENCIAS\n")
    occurrences = find_all_occurrences()

    if not occurrences:
        print("[OK] Nenhuma ocorrencia de 'skills/eye' encontrada!")
        return

    print_occurrences(occurrences)

    print("\nFASE 2: DRY-RUN (Simulacao)\n")
    replace_in_files(occurrences, dry_run=True)

    print("\n[AVISO] FASE 3: APLICACAO REAL")
    print("Para aplicar as mudancas, execute:")
    print("  python migrate_namespace.py --apply")
    print()

if __name__ == '__main__':
    import sys

    if '--apply' in sys.argv:
        print("\nEXECUTANDO MIGRACAO REAL\n")
        occurrences = find_all_occurrences()
        replace_in_files(occurrences, dry_run=False)
        print("\n[OK] MIGRACAO DE CODIGO CONCLUIDA!")
        print("\n[AVISO] PROXIMO PASSO: Migrar dados do Consul KV")
        print("Execute: python migrate_consul_kv.py")
    else:
        main()
