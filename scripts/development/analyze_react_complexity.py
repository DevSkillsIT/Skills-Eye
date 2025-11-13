"""
Analisa complexidade e diferenças entre BlackboxTargets e Services
Identifica o que pode estar deixando Services mais lenta
"""
import re
from pathlib import Path

print("=" * 80)
print("ANALISE DE COMPLEXIDADE REACT: BlackboxTargets vs Services")
print("=" * 80)
print()

frontend_dir = Path("frontend/src/pages")

# Ler arquivos
blackbox_file = frontend_dir / "BlackboxTargets.tsx"
services_file = frontend_dir / "Services.tsx"

blackbox_content = blackbox_file.read_text(encoding='utf-8')
services_content = services_file.read_text(encoding='utf-8')

# ============================================================================
# METRICA 1: Tamanho de arquivo
# ============================================================================
print("METRICA 1: Tamanho de arquivo")
print("-" * 80)
print(f"BlackboxTargets: {len(blackbox_content):,} caracteres ({len(blackbox_content.splitlines()):,} linhas)")
print(f"Services:        {len(services_content):,} caracteres ({len(services_content.splitlines()):,} linhas)")
diff_chars = len(services_content) - len(blackbox_content)
diff_lines = len(services_content.splitlines()) - len(blackbox_content.splitlines())
print(f"Diferença:       +{diff_chars:,} caracteres (+{diff_lines:,} linhas)")
print()

# ============================================================================
# METRICA 2: Hooks React
# ============================================================================
print("METRICA 2: Hooks React")
print("-" * 80)

hooks_pattern = r'\b(useState|useEffect|useMemo|useCallback|useRef|useContext)\('

blackbox_hooks = re.findall(hooks_pattern, blackbox_content)
services_hooks = re.findall(hooks_pattern, services_content)

from collections import Counter

blackbox_hook_counts = Counter(blackbox_hooks)
services_hook_counts = Counter(services_hooks)

print(f"BlackboxTargets:")
for hook, count in sorted(blackbox_hook_counts.items()):
    print(f"  {hook}: {count}x")
print(f"  TOTAL: {len(blackbox_hooks)} hooks")
print()

print(f"Services:")
for hook, count in sorted(services_hook_counts.items()):
    print(f"  {hook}: {count}x")
print(f"  TOTAL: {len(services_hooks)} hooks")
print()

print(f"Diferença: Services tem {len(services_hooks) - len(blackbox_hooks)} hooks a MAIS")
print()

# ============================================================================
# METRICA 3: Iterações pesadas (map, forEach, reduce)
# ============================================================================
print("METRICA 3: Iteracoes pesadas")
print("-" * 80)

iterations_pattern = r'\.(map|forEach|reduce|filter)\('

blackbox_iterations = re.findall(iterations_pattern, blackbox_content)
services_iterations = re.findall(iterations_pattern, services_content)

blackbox_iter_counts = Counter(blackbox_iterations)
services_iter_counts = Counter(services_iterations)

print(f"BlackboxTargets:")
for method, count in sorted(blackbox_iter_counts.items()):
    print(f"  .{method}(): {count}x")
print(f"  TOTAL: {len(blackbox_iterations)} iterações")
print()

print(f"Services:")
for method, count in sorted(services_iter_counts.items()):
    print(f"  .{method}(): {count}x")
print(f"  TOTAL: {len(services_iterations)} iterações")
print()

print(f"Diferença: Services tem {len(services_iterations) - len(blackbox_iterations)} iterações a MAIS")
print()

# ============================================================================
# METRICA 4: Componentes renderizados
# ============================================================================
print("METRICA 4: Componentes JSX")
print("-" * 80)

# Contar tags JSX (aproximação)
jsx_pattern = r'<([A-Z][a-zA-Z0-9.]*)'

blackbox_components = re.findall(jsx_pattern, blackbox_content)
services_components = re.findall(jsx_pattern, services_content)

blackbox_comp_counts = Counter(blackbox_components)
services_comp_counts = Counter(services_components)

print(f"BlackboxTargets: {len(blackbox_components)} componentes renderizados")
print(f"Services:        {len(services_components)} componentes renderizados")
print(f"Diferença:       +{len(services_components) - len(blackbox_components)} componentes")
print()

# Top 5 componentes mais usados em Services (que não estão em Blackbox)
print("Top 5 componentes EXTRAS em Services:")
for comp, count in services_comp_counts.most_common(10):
    blackbox_count = blackbox_comp_counts.get(comp, 0)
    diff = count - blackbox_count
    if diff > 0:
        print(f"  {comp}: {count}x (Blackbox: {blackbox_count}x, diff: +{diff})")
print()

# ============================================================================
# METRICA 5: useMemo dependencies
# ============================================================================
print("METRICA 5: useMemo complexity")
print("-" * 80)

# Encontrar useMemo e contar dependências
usememo_pattern = r'useMemo\([^)]+\),\s*\[([^\]]*)\]'

blackbox_memos = re.findall(usememo_pattern, blackbox_content, re.DOTALL)
services_memos = re.findall(usememo_pattern, services_content, re.DOTALL)

blackbox_memo_deps = [len([d.strip() for d in deps.split(',') if d.strip()]) for deps in blackbox_memos]
services_memo_deps = [len([d.strip() for d in deps.split(',') if d.strip()]) for deps in services_memos]

blackbox_avg_deps = sum(blackbox_memo_deps) / len(blackbox_memo_deps) if blackbox_memo_deps else 0
services_avg_deps = sum(services_memo_deps) / len(services_memo_deps) if services_memo_deps else 0

print(f"BlackboxTargets: {len(blackbox_memos)} useMemo, média de {blackbox_avg_deps:.1f} dependências")
print(f"Services:        {len(services_memos)} useMemo, média de {services_avg_deps:.1f} dependências")
print()

# ============================================================================
# DIAGNOSTICO
# ============================================================================
print("=" * 80)
print("DIAGNOSTICO")
print("=" * 80)

issues = []

if diff_lines > 100:
    issues.append(f"⚠️ Services tem {diff_lines} linhas a MAIS - código mais complexo")

if len(services_hooks) > len(blackbox_hooks) + 5:
    issues.append(f"⚠️ Services tem {len(services_hooks) - len(blackbox_hooks)} hooks a MAIS - mais re-renders")

if len(services_iterations) > len(blackbox_iterations) + 10:
    issues.append(f"⚠️ Services tem {len(services_iterations) - len(blackbox_iterations)} iterações a MAIS - processamento pesado")

if len(services_components) > len(blackbox_components) + 20:
    issues.append(f"⚠️ Services renderiza {len(services_components) - len(blackbox_components)} componentes a MAIS - DOM maior")

if services_avg_deps > blackbox_avg_deps + 1:
    issues.append(f"⚠️ useMemo em Services tem mais dependências - recalcula mais vezes")

if issues:
    for issue in issues:
        print(issue)
else:
    print("✓ Complexidade similar!")

print()
print("=" * 80)
print("FIM DA ANALISE")
print("=" * 80)
