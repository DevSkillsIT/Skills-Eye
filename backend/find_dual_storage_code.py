"""
Busca TODOS os arquivos que acessam skills/eye/blackbox/targets
Para planejar refatoração
"""
import os
import re
from pathlib import Path

def find_kv_targets_usage():
    print("=" * 80)
    print("BUSCA DE CODIGO USANDO skills/eye/blackbox/targets")
    print("=" * 80)
    print()

    backend_dir = Path(__file__).parent
    patterns = [
        r'blackbox/targets',
        r'BLACKBOX_TARGETS',
        r'get_blackbox_target',
        r'create_blackbox_target',
        r'update_blackbox_target',
        r'delete_blackbox_target',
    ]

    findings = []

    for py_file in backend_dir.rglob('*.py'):
        if '__pycache__' in str(py_file) or 'venv' in str(py_file):
            continue

        with open(py_file, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            lines = content.splitlines()

        for pattern in patterns:
            for i, line in enumerate(lines, 1):
                if re.search(pattern, line, re.IGNORECASE):
                    findings.append({
                        'file': str(py_file.relative_to(backend_dir)),
                        'line': i,
                        'code': line.strip(),
                        'pattern': pattern
                    })

    # Agrupar por arquivo
    by_file = {}
    for f in findings:
        file_path = f['file']
        if file_path not in by_file:
            by_file[file_path] = []
        by_file[file_path].append(f)

    print(f"Total de arquivos afetados: {len(by_file)}")
    print()

    for file_path, matches in sorted(by_file.items()):
        print(f"[ARQUIVO] {file_path} ({len(matches)} ocorrencias)")
        for match in matches:
            print(f"   Linha {match['line']}: {match['code'][:80]}")
        print()

    # Salvar em JSON para processamento posterior
    import json

    # Criar diretório docs se não existir
    docs_dir = backend_dir / 'docs'
    docs_dir.mkdir(exist_ok=True)

    output = {
        'total_files': len(by_file),
        'total_occurrences': len(findings),
        'files': by_file
    }

    output_path = docs_dir / 'dual_storage_code_locations.json'
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print("=" * 80)
    print(f"Relatorio salvo em: docs/dual_storage_code_locations.json")
    print("=" * 80)

if __name__ == "__main__":
    find_kv_targets_usage()
