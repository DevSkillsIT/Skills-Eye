"""
Análise profunda de dependências dos métodos blackbox_target.
Verifica TODAS as chamadas e identifica padrões similares em services/exporters.
"""
import os
import re
import ast
from pathlib import Path
from collections import defaultdict
import json

class DependencyAnalyzer:
    def __init__(self, backend_dir):
        self.backend_dir = Path(backend_dir)
        self.findings = {
            'blackbox_target_calls': [],
            'similar_patterns': [],
            'kv_usage': [],
            'service_patterns': [],
            'exporter_patterns': []
        }

    def analyze(self):
        """Executa análise completa."""
        print("=" * 80)
        print("ANALISE PROFUNDA DE DEPENDENCIAS")
        print("=" * 80)
        print()

        # 1. Encontrar todas as chamadas aos métodos blackbox_target
        print("[1/5] Analisando chamadas aos metodos blackbox_target...")
        self._find_blackbox_target_calls()
        print(f"  [OK] Encontradas {len(self.findings['blackbox_target_calls'])} chamadas")
        print()

        # 2. Buscar padrões similares em services
        print("[2/5] Buscando padroes similares em services...")
        self._find_service_patterns()
        print(f"  [OK] Encontrados {len(self.findings['service_patterns'])} padroes")
        print()

        # 3. Buscar padrões similares em exporters
        print("[3/5] Buscando padroes similares em exporters...")
        self._find_exporter_patterns()
        print(f"  [OK] Encontrados {len(self.findings['exporter_patterns'])} padroes")
        print()

        # 4. Mapear uso de KV
        print("[4/5] Mapeando uso de KV...")
        self._map_kv_usage()
        print(f"  [OK] Encontrados {len(self.findings['kv_usage'])} usos")
        print()

        # 5. Identificar código compartilhável
        print("[5/5] Identificando codigo compartilhavel...")
        self._identify_sharable_code()
        print()

        return self.findings

    def _find_blackbox_target_calls(self):
        """Encontra todas as chamadas aos métodos blackbox_target."""
        patterns = [
            r'\.get_blackbox_target\(',
            r'\.put_blackbox_target\(',
            r'\.delete_blackbox_target\(',
            r'\.list_blackbox_targets\('
        ]

        for py_file in self.backend_dir.rglob('*.py'):
            if '__pycache__' in str(py_file) or 'venv' in str(py_file):
                continue

            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    lines = content.splitlines()

                for i, line in enumerate(lines, 1):
                    for pattern in patterns:
                        if re.search(pattern, line):
                            # Capturar contexto (3 linhas antes e depois)
                            start = max(0, i - 4)
                            end = min(len(lines), i + 3)
                            context = '\n'.join(f"  {j+1:4d}: {lines[j]}" for j in range(start, end))

                            self.findings['blackbox_target_calls'].append({
                                'file': str(py_file.relative_to(self.backend_dir)),
                                'line': i,
                                'method': pattern.replace('\\', '').replace('(', ''),
                                'code': line.strip(),
                                'context': context
                            })
            except Exception as e:
                print(f"  [ERRO] Falha ao ler {py_file}: {e}")

    def _find_service_patterns(self):
        """Busca padrões de gerenciamento de services."""
        service_keywords = ['service', 'exporter', 'node_exporter', 'prometheus']

        for py_file in self.backend_dir.rglob('*.py'):
            if '__pycache__' in str(py_file) or 'venv' in str(py_file):
                continue

            filename = py_file.name.lower()
            if any(kw in filename for kw in service_keywords):
                try:
                    with open(py_file, 'r', encoding='utf-8') as f:
                        content = f.read()

                    # Buscar funções async def que lidam com services
                    pattern = r'async def (get|list|create|delete|update)_\w+\('
                    matches = re.finditer(pattern, content)

                    for match in matches:
                        self.findings['service_patterns'].append({
                            'file': str(py_file.relative_to(self.backend_dir)),
                            'function': match.group(0),
                            'type': 'service_management'
                        })
                except Exception:
                    pass

    def _find_exporter_patterns(self):
        """Busca padrões específicos de exporters."""
        exporter_files = []

        for py_file in self.backend_dir.rglob('*.py'):
            if 'exporter' in py_file.name.lower():
                exporter_files.append(py_file)

        for py_file in exporter_files:
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()

                # Buscar padrões de CRUD
                if 'register' in content or 'deregister' in content:
                    self.findings['exporter_patterns'].append({
                        'file': str(py_file.relative_to(self.backend_dir)),
                        'has_crud': True
                    })
            except Exception:
                pass

    def _map_kv_usage(self):
        """Mapeia uso de KV Manager."""
        for py_file in self.backend_dir.rglob('*.py'):
            if '__pycache__' in str(py_file) or 'venv' in str(py_file):
                continue

            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()

                # Buscar constantes do KVManager
                kv_constants = [
                    'BLACKBOX_TARGETS', 'BLACKBOX_GROUPS', 'BLACKBOX_MODULES',
                    'SERVICE_PRESETS', 'SERVICE_TEMPLATES',
                    'UI_SETTINGS', 'USER_PREFERENCES',
                    'IMPORTS_LAST', 'EXPORTS_HISTORY',
                    'AUDIT_LOG'
                ]

                for constant in kv_constants:
                    if constant in content:
                        lines = content.splitlines()
                        for i, line in enumerate(lines, 1):
                            if constant in line and not line.strip().startswith('#'):
                                self.findings['kv_usage'].append({
                                    'file': str(py_file.relative_to(self.backend_dir)),
                                    'line': i,
                                    'constant': constant,
                                    'code': line.strip()
                                })
            except Exception:
                pass

    def _identify_sharable_code(self):
        """Identifica código que pode ser compartilhado."""
        # Buscar padrões duplicados
        crud_patterns = defaultdict(list)

        for py_file in self.backend_dir.rglob('*.py'):
            if '__pycache__' in str(py_file) or 'venv' in str(py_file):
                continue

            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()

                # Identificar funções de listagem
                if re.search(r'async def .*list.*\(', content):
                    crud_patterns['list'].append(str(py_file.relative_to(self.backend_dir)))

                # Identificar funções de criação
                if re.search(r'async def .*(create|add).*\(', content):
                    crud_patterns['create'].append(str(py_file.relative_to(self.backend_dir)))

                # Identificar funções de deleção
                if re.search(r'async def .*delete.*\(', content):
                    crud_patterns['delete'].append(str(py_file.relative_to(self.backend_dir)))
            except Exception:
                pass

        self.findings['similar_patterns'] = dict(crud_patterns)

    def print_report(self):
        """Imprime relatório detalhado."""
        print()
        print("=" * 80)
        print("RELATORIO DE DEPENDENCIAS")
        print("=" * 80)
        print()

        # 1. Chamadas aos métodos blackbox_target
        print("[1] CHAMADAS AOS METODOS BLACKBOX_TARGET")
        print("-" * 80)
        if not self.findings['blackbox_target_calls']:
            print("  [OK] Nenhuma chamada encontrada - SEGURO REMOVER")
        else:
            for call in self.findings['blackbox_target_calls']:
                print(f"\n  Arquivo: {call['file']}:{call['line']}")
                print(f"  Metodo: {call['method']}")
                print(f"  Codigo: {call['code']}")
                print(f"\n  Contexto:")
                print(call['context'])
        print()

        # 2. Constantes KV usadas
        print("[2] USO DE CONSTANTES KV")
        print("-" * 80)
        used_constants = set(c['constant'] for c in self.findings['kv_usage'])
        all_constants = [
            'BLACKBOX_TARGETS', 'BLACKBOX_GROUPS', 'BLACKBOX_MODULES',
            'SERVICE_PRESETS', 'SERVICE_TEMPLATES',
            'UI_SETTINGS', 'USER_PREFERENCES',
            'IMPORTS_LAST', 'EXPORTS_HISTORY',
            'AUDIT_LOG'
        ]

        for const in all_constants:
            if const in used_constants:
                count = len([c for c in self.findings['kv_usage'] if c['constant'] == const])
                print(f"  [USADO] {const:25s} - {count} ocorrencias")
            else:
                print(f"  [NAO USADO] {const:25s} - SEGURO REMOVER")
        print()

        # 3. Padrões similares
        print("[3] PADROES SIMILARES IDENTIFICADOS")
        print("-" * 80)
        for pattern_type, files in self.findings['similar_patterns'].items():
            print(f"\n  Tipo: {pattern_type}")
            print(f"  Arquivos com padrao similar ({len(files)}):")
            for f in files[:5]:  # Mostrar apenas primeiros 5
                print(f"    - {f}")
            if len(files) > 5:
                print(f"    ... e mais {len(files) - 5} arquivos")
        print()

        print("=" * 80)

    def save_report(self, output_file):
        """Salva relatório em JSON."""
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(self.findings, f, indent=2, ensure_ascii=False)
        print(f"\n[OK] Relatorio salvo em: {output_file}")


if __name__ == "__main__":
    backend_dir = Path(__file__).parent
    analyzer = DependencyAnalyzer(backend_dir)

    # Executar análise
    analyzer.analyze()

    # Imprimir relatório
    analyzer.print_report()

    # Salvar em JSON
    docs_dir = backend_dir / 'docs'
    docs_dir.mkdir(exist_ok=True)
    analyzer.save_report(docs_dir / 'dependency_analysis.json')
