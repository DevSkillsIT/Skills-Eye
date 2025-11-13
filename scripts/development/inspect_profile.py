import json

print('Inspecionando estrutura do Firefox Profile...')
print()

# Ler o arquivo JSON
with open('docs/Firefox 2025-11-10 16.03 profile.json', 'r', encoding='utf-8') as f:
    profile = json.load(f)

# Extrair threads
threads = profile.get('threads', [])
print(f'Total de threads: {len(threads)}')

# Encontrar thread principal (GeckoMain)
main_thread = None
for thread in threads:
    if thread.get('name') == 'GeckoMain':
        main_thread = thread
        break

if not main_thread:
    print('Thread principal NAO encontrada')
    exit(1)

print(f'Thread principal: {main_thread.get("name")}')
print()

# Extrair markers
markers = main_thread.get('markers', {})
print(f'Tipo de markers: {type(markers)}')
print(f'Keys em markers: {list(markers.keys()) if isinstance(markers, dict) else "N/A"}')
print()

# Ver estrutura de marker_data
marker_data = markers.get('data', [])
print(f'Total de markers: {len(marker_data)}')
print(f'Tipo de marker_data: {type(marker_data)}')

# Inspecionar primeiros markers
print('\nPrimeiros 5 markers:')
for i, marker in enumerate(marker_data[:5]):
    print(f'\nMarker {i}:')
    print(f'  Tipo: {type(marker)}')
    if isinstance(marker, dict):
        print(f'  Keys: {list(marker.keys())}')
        print(f'  Conteudo: {marker}')
    elif isinstance(marker, (list, tuple)):
        print(f'  Tamanho: {len(marker)}')
        print(f'  Conteudo: {marker}')
    else:
        print(f'  Valor: {marker}')

# Verificar schema de markers
schema = markers.get('schema', {})
print(f'\nSchema de markers:')
print(f'  Tipo: {type(schema)}')
if isinstance(schema, dict):
    for key, value in schema.items():
        print(f'  {key}: {value}')
