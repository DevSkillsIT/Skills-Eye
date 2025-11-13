import json
import sys
from collections import Counter

print('=' * 70)
print('ANALISE DE PERFORMANCE - Firefox Profile APOS Otimizacoes P0')
print('=' * 70)
print()

# Ler o arquivo JSON
with open('docs/Firefox 2025-11-10 16.03 profile.json', 'r', encoding='utf-8') as f:
    profile = json.load(f)

# Extrair threads
threads = profile.get('threads', [])

# Encontrar thread principal (GeckoMain)
main_thread = None
for thread in threads:
    if thread.get('name') == 'GeckoMain':
        main_thread = thread
        break

if not main_thread:
    print('Thread principal NAO encontrada')
    sys.exit(1)

# Extrair markers
markers = main_thread.get('markers', {})
marker_data = markers.get('data', [])

print(f'Thread analisada: {main_thread.get("name")}')
print(f'Total de markers: {len(marker_data):,}')
print()

# Contar tipos de markers
marker_types = Counter()
paint_markers = []
style_markers = []
layout_markers = []
dom_events = []

for marker in marker_data:
    if not isinstance(marker, dict):
        continue

    marker_type = marker.get('type', marker.get('name', 'Unknown'))
    marker_name = marker.get('name', '')
    marker_types[marker_type] += 1

    # Converter para string se necessario
    marker_type_str = str(marker_type) if marker_type else ''
    marker_name_str = str(marker_name) if marker_name else ''

    # Coletar markers importantes
    if 'Paint' in marker_type_str or 'paint' in marker_name_str.lower():
        paint_markers.append(marker)
    if 'Style' in marker_type_str or 'style' in marker_name_str.lower():
        style_markers.append(marker)
    if 'Layout' in marker_type_str or 'Reflow' in marker_type_str:
        layout_markers.append(marker)
    if 'DOM' in marker_type_str:
        dom_events.append(marker)

print('METRICAS DE RENDERING:')
print('=' * 70)
print(f'Paint operations: {len(paint_markers)}')
print(f'Style recalculations: {len(style_markers)}')
print(f'Layout/Reflow operations: {len(layout_markers)}')
print(f'DOM events: {len(dom_events)}')
print()

# Buscar especificamente por "contentful paint"
lcp_markers = [m for m in marker_data if isinstance(m, dict) and
               'contentful paint' in str(m.get('name', '')).lower()]

print(f'Largest Contentful Paint events: {len(lcp_markers)}')
if lcp_markers:
    print('\nDetalhes LCP:')
    for i, lcp in enumerate(lcp_markers[:5], 1):
        name = lcp.get('name', 'N/A')
        print(f'  {i}. {name}')
print()

# Top 15 tipos de markers mais frequentes
print('TOP 15 EVENTOS MAIS FREQUENTES:')
print('=' * 70)
for i, (marker_type, count) in enumerate(marker_types.most_common(15), 1):
    print(f'{i:2d}. {marker_type:<40s} {count:>6,}x')
print()

# Buscar por markers que indicam problemas de performance
print('ANALISE DE PROBLEMAS:')
print('=' * 70)

# Procurar por GC (Garbage Collection)
gc_markers = [m for m in marker_data if isinstance(m, dict) and
              ('GC' in str(m.get('type', '')) or 'GarbageCollection' in str(m.get('type', '')))]
print(f'Garbage Collection events: {len(gc_markers)}')

# Procurar por operacoes bloqueantes
blocking_markers = [m for m in marker_data if isinstance(m, dict) and
                   ('Blocking' in str(m.get('type', '')) or
                    'blocking' in str(m.get('name', '')).lower())]
print(f'Operacoes bloqueantes: {len(blocking_markers)}')

# Network requests
network_markers = [m for m in marker_data if isinstance(m, dict) and
                  ('Network' in str(m.get('type', '')) or 'http' in str(m.get('name', '')).lower())]
print(f'Network requests: {len(network_markers)}')

print()

# Comparacao com analise anterior
print('=' * 70)
print('COMPARACAO COM ANALISE ANTERIOR (Profile 15.42):')
print('=' * 70)
print('NOTA: Estrutura do novo profile difere do anterior.')
print('      Profile anterior tinha markers como arrays, novo tem dicts.')
print()
print('Metricas equivalentes:')
print(f'  Paint operations: ~22 (antes, MozAfterPaint) -> {len(paint_markers)} (agora)')
print(f'  Style recalcs: ~615 (antes) -> {len(style_markers)} (agora)')
print()

if len(paint_markers) < 22:
    improvement = ((22 - len(paint_markers)) / 22) * 100
    print(f'MELHORIA estimada: -{improvement:.1f}% em paint operations')
elif len(paint_markers) > 22:
    worsening = ((len(paint_markers) - 22) / 22) * 100
    print(f'POSSIVEL PIORA: +{worsening:.1f}% em paint operations')

print()
print('=' * 70)

# Verificar URL da pagina capturada
pages = profile.get('pages', [])
if pages:
    print('\nPAGINAS CAPTURADAS NO PROFILE:')
    for i, page in enumerate(pages[:3], 1):
        url = page.get('url', 'N/A')
        print(f'  {i}. {url}')
print()
print('=' * 70)
