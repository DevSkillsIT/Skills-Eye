#!/bin/bash
# Script de teste simples para validar correções
# Usa apenas curl + jq

echo "=================================="
echo "🔍 TESTE 1: Backend Nodes Endpoint"
echo "=================================="

echo -e "\n📡 Testando /api/v1/nodes..."
response=$(curl -s "http://localhost:5000/api/v1/nodes")

# Verificar se retornou success
success=$(echo "$response" | jq -r '.success')
if [ "$success" == "true" ]; then
    echo "✅ Backend respondeu com success=true"
else
    echo "❌ Backend NÃO retornou success=true"
    exit 1
fi

# Verificar nodes
nodes_count=$(echo "$response" | jq '.data | length')
echo "✅ Backend retornou $nodes_count nós"

# Verificar se site_name é diferente de addr (não usa IP como fallback)
echo -e "\n📊 Verificando site_name vs addr em cada nó:"
echo "$response" | jq -r '.data[] | "Nó: \(.node)\n  site_name: \(.site_name)\n  addr: \(.addr)\n  Status: \(if .site_name == .addr then "⚠️  USANDO IP" else "✅ OK" end)\n"'

echo -e "\n=================================="
echo "🔍 TESTE 2: Frontend Accessibility"  
echo "=================================="

echo -e "\n📡 Testando http://localhost:8081..."
frontend_status=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:8081")

if [ "$frontend_status" == "200" ]; then
    echo "✅ Frontend acessível (HTTP $frontend_status)"
else
    echo "❌ Frontend não acessível (HTTP $frontend_status)"
    exit 1
fi

echo -e "\n=================================="
echo "🔍 TESTE 3: API Performance"
echo "=================================="

echo -e "\n⏱️  Medindo tempo de resposta do backend..."
start_time=$(date +%s%N)
curl -s "http://localhost:5000/api/v1/nodes" > /dev/null
end_time=$(date +%s%N)
elapsed_ms=$(( (end_time - start_time) / 1000000 ))

echo "⏱️  Tempo de resposta: ${elapsed_ms}ms"

if [ $elapsed_ms -lt 1000 ]; then
    echo "✅ Performance BOA (< 1000ms)"
elif [ $elapsed_ms -lt 2000 ]; then
    echo "⚠️  Performance aceitável (< 2000ms)"
else
    echo "❌ Performance RUIM (> 2000ms)"
fi

echo -e "\n=================================="
echo "📊 RESUMO"
echo "=================================="
echo "✅ Backend nodes endpoint: OK"
echo "✅ Frontend acessível: OK"
echo "✅ Performance: ${elapsed_ms}ms"
echo ""
echo "🎯 PRÓXIMOS PASSOS:"
echo "1. Abra http://localhost:8081/monitoring/network-probes"
echo "2. Verifique se NodeSelector mostra 'Nome (IP)'"
echo "3. Ordene uma coluna e clique em 'Limpar Filtros e Ordem'"
echo "4. Verifique se indicador de ordenação sumiu"
echo "5. Teste filtros de metadata (empresa, provedor, etc)"
echo ""
