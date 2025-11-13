import json
import sys
from collections import Counter

print('=' * 70)
print('ANALISE DE PERFORMANCE - Firefox Profile 16.33 (APOS DEBOUNCE)')
print('=' * 70)
print()

# Ler o arquivo JSON
with open('docs/Firefox 2025-11-10 16.33 profile.json', 'r', encoding='utf-8') as f:
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

localhost_pages = []
if pages:
    for i, page in enumerate(pages, 1):
        url = page.get('url', 'N/A')
        if 'localhost:8081' in url:
            localhost_pages.append(url)
            print(f'>>> {url}')

    if localhost_pages:
        print(f'\n>>> OK! Profile capturou {len(localhost_pages)} pagina(s) localhost:8081')
    else:
        print('\n!!! ATENCAO: Profile NAO capturou localhost:8081')
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

# Comparacao com analise anterior (16.13)
print('=' * 70)
print('COMPARACAO COM PROFILE ANTERIOR (16.13 - ANTES DEBOUNCE):')
print('=' * 70)
print(f'Paint operations: 122 (antes) -> {len(paint_markers)} (agora)')
print(f'Style recalcs: 512 (antes) -> {len(style_markers)} (agora)')
print(f'GC events: 18 (antes) -> {len(gc_markers)} (agora)')
print(f'Network requests: 3,024 (antes) -> {len(network_markers)} (agora)')
print()

# Calcular melhorias
def calc_improvement(before, after):
    if before == 0:
        return 0
    return ((before - after) / before) * 100

paint_improvement = calc_improvement(122, len(paint_markers))
style_improvement = calc_improvement(512, len(style_markers))
gc_improvement = calc_improvement(18, len(gc_markers))

print('RESULTADOS DO DEBOUNCE (P1.1):')
print('=' * 70)

if paint_improvement > 0:
    print(f'Paint operations: MELHORIA de {paint_improvement:.1f}%')
elif paint_improvement < 0:
    print(f'Paint operations: PIORA de {abs(paint_improvement):.1f}%')
else:
    print(f'Paint operations: SEM MUDANCA')

if style_improvement > 0:
    print(f'Style recalcs: MELHORIA de {style_improvement:.1f}%')
elif style_improvement < 0:
    print(f'Style recalcs: PIORA de {abs(style_improvement):.1f}%')
else:
    print(f'Style recalcs: SEM MUDANCA')

if gc_improvement > 0:
    print(f'GC events: MELHORIA de {gc_improvement:.1f}%')
elif gc_improvement < 0:
    print(f'GC events: PIORA de {abs(gc_improvement):.1f}%')
else:
    print(f'GC events: SEM MUDANCA')

print()

# Verificar se atingiu metas
print('=' * 70)
print('VERIFICACAO DE METAS:')
print('=' * 70)
print(f'Meta Paint operations < 20: {" ATINGIDA" if len(paint_markers) < 20 else f" NAO ATINGIDA ({len(paint_markers)} ops)"}')
print(f'Meta Style recalcs < 300: {" ATINGIDA" if len(style_markers) < 300 else f" NAO ATINGIDA ({len(style_markers)} recalcs)"}')
print(f'Meta GC events < 10: {" ATINGIDA" if len(gc_markers) < 10 else f" NAO ATINGIDA ({len(gc_markers)} events)"}')
print()

# Analisar timing de LCP especificamente
if lcp_markers:
    print()
    print('ANALISE DETALHADA - Timing de LCP:')
    print('=' * 70)

    lcp_times = []
    for i, lcp in enumerate(lcp_markers[:5], 1):
        name = lcp.get('name', 'N/A')
        # Extrair tempo (ex: "after 250ms")
        if 'after' in name and 'ms' in name:
            try:
                time_str = name.split('after ')[1].split('ms')[0]
                time_ms = int(time_str)
                lcp_times.append(time_ms)

                status = ''
                if time_ms < 100:
                    status = ' EXCELENTE'
                elif time_ms < 250:
                    status = ' BOM'
                elif time_ms < 2500:
                    status = ' ACEITAVEL'
                else:
                    status = ' RUIM'

                print(f'{i}. {time_ms}ms - {status}')
            except:
                print(f'{i}. {name}')

    if lcp_times:
        avg_lcp = sum(lcp_times) / len(lcp_times)
        print(f'\nLCP medio: {avg_lcp:.0f}ms')
        print(f'Meta LCP < 2500ms: {" ATINGIDA" if avg_lcp < 2500 else " NAO ATINGIDA"}')
    print()

print('=' * 70)
print('DIAGNOSTICO:')
print('=' * 70)

# Diagnostico automatico
issues = []

if len(paint_markers) > 20:
    issues.append(f' Paint operations ALTO ({len(paint_markers)} ops)')
    issues.append('   Causa provavel: Re-renders excessivos ou visibleColumns recalculando')
    issues.append('   Solucao: Implementar P1.2 (Estabilizar visibleColumns)')

if len(style_markers) > 300:
    issues.append(f' Style recalculations ALTO ({len(style_markers)} recalcs)')
    issues.append('   Causa provavel: CSS dinamico ou mudancas de DOM frequentes')

if len(gc_markers) > 10:
    issues.append(f' Garbage Collection ALTO ({len(gc_markers)} events)')
    issues.append('   Causa provavel: Criacao excessiva de objetos ainda presente')
    issues.append('   Nota: Debounce pode nao ter sido suficiente')

if len(network_markers) > 2000:
    issues.append(f' Network requests ALTO ({len(network_markers)} requests)')
    issues.append('   Causa provavel: StrictMode duplicando + extensoes Firefox')
    issues.append('   Nota: Normal em dev, verificar em producao')

if issues:
    for issue in issues:
        print(issue)
else:
    print(' Todas as metricas dentro do esperado!')

print()
print('=' * 70)
print('PROXIMOS PASSOS RECOMENDADOS:')
print('=' * 70)

# Recomendar proximos passos baseado em metricas
if len(paint_markers) > 20:
    print('1. Implementar P1.2: Estabilizar visibleColumns (2h)')
    print('   - Memoizar handleResize sem dependencias')
    print('   - Usar useRef para columnWidths')
    print('   - Reducao esperada: Paint ops -60%')
    print()

if len(style_markers) > 300:
    print('2. Investigar recalculos de estilo excessivos')
    print('   - Verificar CSS dinamico')
    print('   - Verificar animacoes CSS')
    print()

if len(gc_markers) > 10:
    print('3. Otimizar criacao de objetos')
    print('   - Considerar memoizacao adicional')
    print('   - Usar objetos reutilizaveis')
    print()

print('=' * 70)
print('FIM DA ANALISE')
print('=' * 70)
