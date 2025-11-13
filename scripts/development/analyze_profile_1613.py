import json
import sys
from collections import Counter

print('=' * 70)
print('ANALISE DE PERFORMANCE - Firefox Profile 16.13 (NOVO)')
print('=' * 70)
print()

# Ler o arquivo JSON
with open('docs/Firefox 2025-11-10 16.13 profile.json', 'r', encoding='utf-8') as f:
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

# Verificar URL da pagina capturada PRIMEIRO
pages = profile.get('pages', [])
print('=' * 70)
print('PAGINAS CAPTURADAS NO PROFILE:')
print('=' * 70)
if pages:
    for i, page in enumerate(pages, 1):
        url = page.get('url', 'N/A')
        inner_window_id = page.get('innerWindowID', 'N/A')
        is_embedder_inner_window_id = page.get('isEmbedderInnerWindowID', False)
        print(f'{i}. URL: {url}')
        print(f'   InnerWindowID: {inner_window_id}')
        print(f'   IsEmbedder: {is_embedder_inner_window_id}')
        print()

    # Verificar se capturou a pagina correta
    correct_page = any('localhost:8081' in page.get('url', '') for page in pages)
    if correct_page:
        print('>>> OK! Profile capturou http://localhost:8081/services')
    else:
        print('!!! ATENCAO: Profile NAO capturou localhost:8081')
        print('!!! Pode ter capturado apenas paginas internas do Firefox')
else:
    print('!!! NENHUMA pagina capturada!')
print()
print('=' * 70)

# Contar tipos de markers
marker_types = Counter()
paint_markers = []
style_markers = []
layout_markers = []
dom_events = []
lcp_markers = []
network_markers = []

for marker in marker_data:
    if not isinstance(marker, dict):
        continue

    marker_type = marker.get('type', marker.get('name', 'Unknown'))
    marker_name = str(marker.get('name', ''))
    marker_types[marker_type] += 1

    # Coletar markers importantes
    if 'Paint' in str(marker_type) or 'paint' in marker_name.lower():
        paint_markers.append(marker)
    if 'Style' in str(marker_type) or 'style' in marker_name.lower():
        style_markers.append(marker)
    if 'Layout' in str(marker_type) or 'Reflow' in str(marker_type):
        layout_markers.append(marker)
    if 'DOM' in str(marker_type):
        dom_events.append(marker)
    if 'contentful paint' in marker_name.lower():
        lcp_markers.append(marker)
    if 'Network' in str(marker_type) or 'http' in marker_name.lower():
        network_markers.append(marker)

print('METRICAS DE RENDERING:')
print('=' * 70)
print(f'Paint operations: {len(paint_markers)}')
print(f'Style recalculations: {len(style_markers)}')
print(f'Layout/Reflow operations: {len(layout_markers)}')
print(f'DOM events: {len(dom_events)}')
print(f'Largest Contentful Paint events: {len(lcp_markers)}')
print(f'Network requests: {len(network_markers)}')
print()

# Detalhes LCP
if lcp_markers:
    print('DETALHES - Largest Contentful Paint:')
    print('-' * 70)
    for i, lcp in enumerate(lcp_markers[:10], 1):
        name = lcp.get('name', 'N/A')
        print(f'  {i}. {name}')
    print()

# Top 20 tipos de markers mais frequentes
print('TOP 20 EVENTOS MAIS FREQUENTES:')
print('=' * 70)
for i, (marker_type, count) in enumerate(marker_types.most_common(20), 1):
    print(f'{i:2d}. {str(marker_type):<40s} {count:>6,}x')
print()

# Buscar por markers de performance
print('ANALISE DE PROBLEMAS:')
print('=' * 70)

# GC
gc_markers = [m for m in marker_data if isinstance(m, dict) and
              ('GC' in str(m.get('type', '')) or 'GarbageCollection' in str(m.get('type', '')))]
print(f'Garbage Collection events: {len(gc_markers)}')

# Blocking
blocking_markers = [m for m in marker_data if isinstance(m, dict) and
                   ('Blocking' in str(m.get('type', '')) or
                    'blocking' in str(m.get('name', '')).lower())]
print(f'Operacoes bloqueantes: {len(blocking_markers)}')

# Long tasks (se houver)
long_task_markers = [m for m in marker_data if isinstance(m, dict) and
                    'long' in str(m.get('name', '')).lower()]
print(f'Long tasks: {len(long_task_markers)}')

print()

# Comparacao com analise anterior
print('=' * 70)
print('COMPARACAO COM PROFILE ANTERIOR (16.03):')
print('=' * 70)
print(f'Paint operations: 124 (antes) -> {len(paint_markers)} (agora)')
print(f'Style recalcs: 588 (antes) -> {len(style_markers)} (agora)')
print(f'Network requests: 2,909 (antes) -> {len(network_markers)} (agora)')
print()

if len(paint_markers) < 124:
    improvement = ((124 - len(paint_markers)) / 124) * 100
    print(f'MELHORIA: -{improvement:.1f}% em paint operations')
elif len(paint_markers) > 124:
    worsening = ((len(paint_markers) - 124) / 124) * 100
    print(f'PIORA: +{worsening:.1f}% em paint operations')
else:
    print('SEM MUDANCA em paint operations')

if len(style_markers) < 588:
    improvement = ((588 - len(style_markers)) / 588) * 100
    print(f'MELHORIA: -{improvement:.1f}% em style recalculations')
elif len(style_markers) > 588:
    worsening = ((len(style_markers) - 588) / 588) * 100
    print(f'PIORA: +{worsening:.1f}% em style recalculations')

print()
print('=' * 70)

# Analisar timing de LCP especificamente
if lcp_markers:
    print()
    print('ANALISE DETALHADA - Timing de LCP:')
    print('=' * 70)

    for i, lcp in enumerate(lcp_markers[:5], 1):
        name = lcp.get('name', 'N/A')
        # Extrair tempo (ex: "after 250ms")
        if 'after' in name and 'ms' in name:
            try:
                time_str = name.split('after ')[1].split('ms')[0]
                time_ms = int(time_str)
                print(f'{i}. {name} ({time_ms}ms)')

                if time_ms < 100:
                    print(f'   >>> EXCELENTE (< 100ms)')
                elif time_ms < 250:
                    print(f'   >> BOM (< 250ms)')
                elif time_ms < 2500:
                    print(f'   > ACEITAVEL (< 2.5s)')
                else:
                    print(f'   ! RUIM (> 2.5s) - necessita otimizacao')
            except:
                print(f'{i}. {name}')
    print()

print('=' * 70)
print('FIM DA ANALISE')
print('=' * 70)
