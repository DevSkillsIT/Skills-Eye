#!/bin/bash
# Teste simplificado: Validar filtro de nós

echo "================================================================================"
echo "TESTE: Validação do Filtro de Nós (Backend + Dados)"
echo "================================================================================"

# Buscar dados completos
echo -e "\n[1] Buscando dados COMPLETOS (todos os nós)..."
TOTAL=$(curl -s "http://localhost:5000/api/v1/monitoring/data?category=network-probes" | jq -r '.total')
echo "   ✅ Total retornado: $TOTAL"

# Verificar estrutura de 1 item
echo -e "\n[2] Verificando estrutura de dados (1º item)..."
curl -s "http://localhost:5000/api/v1/monitoring/data?category=network-probes" | \
  jq '.data[0] | {ID, Node, node_ip, site_code, company: .Meta.company}'

# Listar nós disponíveis
echo -e "\n[3] Nós disponíveis no sistema..."
curl -s "http://localhost:5000/api/v1/nodes" | \
  jq -r '.data[] | "   - \(.addr) (Nome: \(.name // "N/A"))"'

# Contagem por node_ip
echo -e "\n[4] Distribuição por node_ip..."
curl -s "http://localhost:5000/api/v1/monitoring/data?category=network-probes" | \
  jq -r '.data | group_by(.node_ip) | .[] | "   - \(.[0].node_ip): \(length) serviços"'

echo -e "\n================================================================================"
echo "INSTRUÇÕES PARA TESTE MANUAL NO BROWSER"
echo "================================================================================"
echo ""
echo "1. Abra: http://localhost:8081/monitoring/network-probes"
echo ""
echo "2. Verifique o seletor de nós (canto superior esquerdo)"
echo "   - Deve mostrar 'Todos os nós' por padrão"
echo "   - Total deve ser: $TOTAL serviços"
echo ""
echo "3. Clique no seletor e escolha o nó: 172.16.1.26"
echo "   - Deve filtrar para 133 serviços (Palmas)"
echo ""
echo "4. Clique no seletor e escolha o nó: 11.144.0.21"
echo "   - Deve filtrar para 14 serviços (DTC)"
echo ""
echo "5. Clique no seletor e escolha o nó: 172.16.200.14"
echo "   - Deve filtrar para 8 serviços (Rio)"
echo ""
echo "6. Clique no seletor e escolha: Todos os nós"
echo "   - Deve voltar para $TOTAL serviços"
echo ""
echo "================================================================================"
echo "DEBUGGING"
echo "================================================================================"
echo ""
echo "Se o filtro NÃO funcionar, abra o Console do Browser (F12) e verifique:"
echo ""
echo "1. Erros de JavaScript?"
echo "2. Rede: Endpoint /api/v1/monitoring/data retorna node_ip?"
echo "3. Console.log: Buscar por 'selectedNode' ou 'node_ip'"
echo ""
echo "Código relevante no frontend:"
echo "   - Arquivo: frontend/src/pages/DynamicMonitoringPage.tsx"
echo "   - Linha 518: rows.filter(item => item.node_ip === selectedNode)"
echo ""
echo "================================================================================"
