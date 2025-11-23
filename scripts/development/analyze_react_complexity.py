"""
Analisa complexidade de componentes React
Identifica potenciais problemas de performance

NOTA: Este script foi atualizado em SPEC-CLEANUP-001 v1.4.0
Os arquivos BlackboxTargets.tsx e Services.tsx foram removidos
como parte da limpeza de paginas obsoletas.
Agora o script analisa DynamicMonitoringPage como referencia.
"""
import re
from pathlib import Path

print("=" * 80)
print("ANALISE DE COMPLEXIDADE REACT: DynamicMonitoringPage")
print("=" * 80)
print()

frontend_dir = Path("frontend/src/pages")

# Ler arquivo de referencia (DynamicMonitoringPage substituiu as paginas obsoletas)
dynamic_file = frontend_dir / "DynamicMonitoringPage.tsx"

if not dynamic_file.exists():
    print("ERRO: DynamicMonitoringPage.tsx nao encontrado!")
    print("Verifique se o arquivo existe em frontend/src/pages/")
    exit(1)

dynamic_content = dynamic_file.read_text(encoding='utf-8')

# ============================================================================
# METRICA 1: Tamanho de arquivo
# ============================================================================
print("METRICA 1: Tamanho de arquivo")
print("-" * 80)
print(f"DynamicMonitoringPage: {len(dynamic_content):,} caracteres ({len(dynamic_content.splitlines()):,} linhas)")
print()

# ============================================================================
# METRICA 2: Hooks React
# ============================================================================
print("METRICA 2: Hooks React")
print("-" * 80)

hooks_pattern = r'\b(useState|useEffect|useMemo|useCallback|useRef|useContext)\('

from collections import Counter

dynamic_hooks = re.findall(hooks_pattern, dynamic_content)
dynamic_hook_counts = Counter(dynamic_hooks)

print(f"DynamicMonitoringPage:")
for hook, count in sorted(dynamic_hook_counts.items()):
    print(f"  {hook}: {count}x")
print(f"  TOTAL: {len(dynamic_hooks)} hooks")
print()

# ============================================================================
# METRICA 3: Iteracoes pesadas (map, forEach, reduce)
# ============================================================================
print("METRICA 3: Iteracoes pesadas")
print("-" * 80)

iterations_pattern = r'\.(map|forEach|reduce|filter)\('

dynamic_iterations = re.findall(iterations_pattern, dynamic_content)
dynamic_iter_counts = Counter(dynamic_iterations)

print(f"DynamicMonitoringPage:")
for method, count in sorted(dynamic_iter_counts.items()):
    print(f"  .{method}(): {count}x")
print(f"  TOTAL: {len(dynamic_iterations)} iteracoes")
print()

# ============================================================================
# METRICA 4: Componentes renderizados
# ============================================================================
print("METRICA 4: Componentes JSX")
print("-" * 80)

# Contar tags JSX (aproximacao)
jsx_pattern = r'<([A-Z][a-zA-Z0-9.]*)'

dynamic_components = re.findall(jsx_pattern, dynamic_content)
dynamic_comp_counts = Counter(dynamic_components)

print(f"DynamicMonitoringPage: {len(dynamic_components)} componentes renderizados")
print()

# Top 10 componentes mais usados
print("Top 10 componentes mais usados:")
for comp, count in dynamic_comp_counts.most_common(10):
    print(f"  {comp}: {count}x")
print()

# ============================================================================
# METRICA 5: useMemo dependencies
# ============================================================================
print("METRICA 5: useMemo complexity")
print("-" * 80)

# Encontrar useMemo e contar dependencias
usememo_pattern = r'useMemo\([^)]+\),\s*\[([^\]]*)\]'

dynamic_memos = re.findall(usememo_pattern, dynamic_content, re.DOTALL)
dynamic_memo_deps = [len([d.strip() for d in deps.split(',') if d.strip()]) for deps in dynamic_memos]

dynamic_avg_deps = sum(dynamic_memo_deps) / len(dynamic_memo_deps) if dynamic_memo_deps else 0

print(f"DynamicMonitoringPage: {len(dynamic_memos)} useMemo, media de {dynamic_avg_deps:.1f} dependencias")
print()

# ============================================================================
# DIAGNOSTICO
# ============================================================================
print("=" * 80)
print("DIAGNOSTICO")
print("=" * 80)

issues = []

total_lines = len(dynamic_content.splitlines())
if total_lines > 500:
    issues.append(f"Arquivo grande: {total_lines} linhas - considerar dividir em componentes menores")

if len(dynamic_hooks) > 15:
    issues.append(f"Muitos hooks: {len(dynamic_hooks)} - pode causar re-renders excessivos")

if len(dynamic_iterations) > 20:
    issues.append(f"Muitas iteracoes: {len(dynamic_iterations)} - processamento potencialmente pesado")

if len(dynamic_components) > 100:
    issues.append(f"Muitos componentes JSX: {len(dynamic_components)} - DOM potencialmente grande")

if dynamic_avg_deps > 5:
    issues.append(f"useMemo com muitas dependencias (media: {dynamic_avg_deps:.1f}) - recalcula frequentemente")

if issues:
    print("Pontos de atencao:")
    for issue in issues:
        print(f"  - {issue}")
else:
    print("Sem problemas de complexidade identificados")

print()
print("=" * 80)
print("FIM DA ANALISE")
print("=" * 80)
