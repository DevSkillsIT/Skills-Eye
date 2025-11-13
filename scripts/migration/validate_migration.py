"""
Valida a migração de skills/cm para skills/eye
Busca referências duplicadas ou incorretas
"""
import os
import re
from pathlib import Path
from collections import defaultdict

ROOT_DIR = Path(__file__).parent
IGNORE_DIRS = {'node_modules', '__pycache__', '.vite', 'venv', '.git', 'dist', 'build'}
FILE_EXTENSIONS = {'.py', '.ts', '.tsx', '.md', '.json', '.txt', '.yml', '.yaml'}

def validate_migration():
    """Valida migração completa."""
    print("=" * 80)
    print("VALIDACAO DA MIGRACAO")
    print("=" * 80)
    print()

    issues = []
    stats = {
        'total_files': 0,
        'old_refs': 0,
        'new_refs': 0,
        'mixed_files': 0
    }

    files_with_old = []
    files_with_new = []
    files_with_both = []

    for file_path in ROOT_DIR.rglob('*'):
        if file_path.is_dir():
            continue
        if any(ignore in file_path.parts for ignore in IGNORE_DIRS):
            continue
        if file_path.suffix not in FILE_EXTENSIONS:
            continue

        stats['total_files'] += 1

        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()

            has_old = 'skills/cm' in content
            has_new = 'skills/eye' in content

            if has_old:
                count_old = content.count('skills/cm')
                stats['old_refs'] += count_old
                files_with_old.append((str(file_path.relative_to(ROOT_DIR)), count_old))

            if has_new:
                count_new = content.count('skills/eye')
                stats['new_refs'] += count_new
                files_with_new.append((str(file_path.relative_to(ROOT_DIR)), count_new))

            if has_old and has_new:
                stats['mixed_files'] += 1
                files_with_both.append(str(file_path.relative_to(ROOT_DIR)))
                issues.append(f"ARQUIVO COM REFERENCIAS MISTAS: {file_path.relative_to(ROOT_DIR)}")

        except Exception as e:
            pass

    # RELATORIO
    print("[1] ESTATISTICAS")
    print("-" * 80)
    print(f"  Arquivos escaneados:     {stats['total_files']}")
    print(f"  Referencias a skills/cm: {stats['old_refs']}")
    print(f"  Referencias a skills/eye: {stats['new_refs']}")
    print(f"  Arquivos com AMBOS:      {stats['mixed_files']}")
    print()

    if stats['old_refs'] > 0:
        print("[2] ARQUIVOS COM REFERENCIAS ANTIGAS (skills/cm)")
        print("-" * 80)
        for file_name, count in sorted(files_with_old):
            print(f"  - {file_name} ({count} refs)")
        print()

    if stats['mixed_files'] > 0:
        print("[3] ARQUIVOS COM REFERENCIAS MISTAS (ATENCAO!)")
        print("-" * 80)
        for file_name in files_with_both:
            print(f"  [AVISO] {file_name}")
        print()

    # VALIDACAO FINAL
    print("=" * 80)
    if stats['old_refs'] == 0:
        print("[OK] MIGRACAO 100% COMPLETA!")
        print("Nenhuma referencia antiga encontrada")
    elif stats['old_refs'] == stats['mixed_files']:
        print("[ATENCAO] Existem referencias mistas")
        print(f"{stats['mixed_files']} arquivos precisam de revisao manual")
    else:
        print(f"[AVISO] {stats['old_refs']} referencias antigas ainda existem")
        print(f"Revise os arquivos listados acima")

    print("=" * 80)
    print()

    return stats


if __name__ == '__main__':
    validate_migration()
