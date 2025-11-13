#!/bin/bash
# Test script para validar extração de servidor único

API_URL="http://localhost:5000/api/v1/metadata-fields"

echo "========================================"
echo "TESTE: Extração de Servidor Único"
echo "========================================"
echo ""

# PASSO 1: Extrair de TODOS os servidores para popular 3 sites
echo "📋 PASSO 1: Extração completa (3 servidores)..."
RESULT=$(curl -s -X POST "$API_URL/force-extract")
SITES=$(echo "$RESULT" | python3 -c "import sys, json; d=json.load(sys.stdin); print(d.get('sites_synced', 0))")
echo "   ✅ Sites sincronizados: $SITES"

# Verificar sites no KV
TOTAL_SITES=$(curl -s "$API_URL/config/sites" | python3 -c "import sys, json; d=json.load(sys.stdin); print(d['total'])")
echo "   ✅ Sites no KV: $TOTAL_SITES"

if [ "$TOTAL_SITES" != "3" ]; then
    echo "   ❌ ERRO: Esperado 3 sites, encontrado $TOTAL_SITES"
    exit 1
fi

echo ""

# PASSO 2: Extrair APENAS de um servidor (172.16.1.26)
echo "📋 PASSO 2: Extração de servidor único (172.16.1.26)..."
RESULT=$(curl -s -X POST "$API_URL/force-extract" \
    -H "Content-Type: application/json" \
    -d '{"server_id": "172.16.1.26"}')

SITES_AFTER=$(echo "$RESULT" | python3 -c "import sys, json; d=json.load(sys.stdin); print(d.get('sites_synced', 0))")
FIELDS=$(echo "$RESULT" | python3 -c "import sys, json; d=json.load(sys.stdin); print(d.get('total_fields', 0))")
echo "   ✅ Sites sincronizados: $SITES_AFTER"
echo "   ✅ Campos extraídos: $FIELDS"

# PASSO 3: Verificar se AINDA tem 3 sites no KV (não sobrescreveu!)
TOTAL_SITES_AFTER=$(curl -s "$API_URL/config/sites" | python3 -c "import sys, json; d=json.load(sys.stdin); print(d['total'])")
echo "   ✅ Sites no KV após extração única: $TOTAL_SITES_AFTER"

if [ "$TOTAL_SITES_AFTER" != "3" ]; then
    echo "   ❌ ERRO: Sites foram sobrescritos! Esperado 3, encontrado $TOTAL_SITES_AFTER"
    exit 1
fi

echo ""

# PASSO 4: Verificar discovered_in de alguns campos
echo "📋 PASSO 3: Verificando discovered_in dos campos..."
curl -s "$API_URL/" | python3 -c "
import sys, json
d = json.load(sys.stdin)
fields = d.get('fields', [])

# Verificar primeiros 3 campos
for f in fields[:3]:
    name = f['name']
    disc = f.get('discovered_in', [])
    print(f'   Campo: {name:30} | Descoberto em: {len(disc)} servidor(es)')
    
    if not disc or len(disc) == 0:
        print(f'   ❌ ERRO: Campo {name} sem discovered_in!')
        sys.exit(1)
"

if [ $? -ne 0 ]; then
    exit 1
fi

echo ""

# PASSO 5: Verificar cores dos sites
echo "📋 PASSO 4: Verificando cores dos sites..."
curl -s "$API_URL/config/sites" | python3 -c "
import sys, json
d = json.load(sys.stdin)
sites = d.get('sites', [])

print('   🎨 Cores configuradas:')

# Validar que TODAS as cores estão definidas (não podem ser None ou vazias)
all_have_colors = True
for s in sites:
    code = s['code']
    name = s.get('name', code)
    color = s.get('color', None)
    
    if not color or color == 'N/A':
        print(f'      ❌ {code:10} | Cor: AUSENTE!')
        all_have_colors = False
    else:
        print(f'      ✅ {code:10} | Cor: {color:10} | Nome: {name}')

if not all_have_colors:
    print('      ❌ ERRO: Sites sem cor definida!')
    sys.exit(1)
"

if [ $? -ne 0 ]; then
    exit 1
fi

echo ""
echo "========================================"
echo "✅ TODOS OS TESTES PASSARAM!"
echo "========================================"
echo ""
echo "Resumo:"
echo "  - Extração de servidor único NÃO sobrescreve sites"
echo "  - discovered_in é populado corretamente"
echo "  - Sites permanecem íntegros no KV"
echo "  - Cores dos sites estão definidas corretamente no KV"
echo ""
echo "⚠️  AÇÃO NECESSÁRIA:"
echo "  - Recarregue a página no navegador para aplicar correções de cores"
echo "  - Verifique colunas 'Descoberto Em' e 'Origem' usam cores do KV"
