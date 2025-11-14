#!/bin/bash
# Teste de performance do cache de nodes

echo "================================================================================"
echo "TESTE: Performance do Cache de Nodes"
echo "================================================================================"

API_URL="http://localhost:5000/api/v1/monitoring/data?category=network-probes"

echo -e "\n[1] PRIMEIRA CHAMADA (Cache Miss - deve buscar do Consul)"
time1_start=$(date +%s%N)
curl -s "$API_URL" > /dev/null
time1_end=$(date +%s%N)
time1_ms=$(( (time1_end - time1_start) / 1000000 ))

echo "   Tempo: ${time1_ms}ms (com busca ao Consul)"

echo -e "\n[2] SEGUNDA CHAMADA (Cache Hit - deve usar cache)"
time2_start=$(date +%s%N)
curl -s "$API_URL" > /dev/null
time2_end=$(date +%s%N)
time2_ms=$(( (time2_end - time2_start) / 1000000 ))

echo "   Tempo: ${time2_ms}ms (usando cache)"

echo -e "\n[3] TERCEIRA CHAMADA (Cache Hit - deve usar cache)"
time3_start=$(date +%s%N)
curl -s "$API_URL" > /dev/null
time3_end=$(date +%s%N)
time3_ms=$(( (time3_end - time3_start) / 1000000 ))

echo "   Tempo: ${time3_ms}ms (usando cache)"

echo -e "\n================================================================================"
echo "RESULTADOS"
echo "================================================================================"

# Média das chamadas com cache
cache_avg=$(( (time2_ms + time3_ms) / 2 ))
improvement=$(( time1_ms - cache_avg ))
improvement_pct=$(( improvement * 100 / time1_ms ))

echo ""
echo "Cache Miss (1ª chamada):     ${time1_ms}ms"
echo "Cache Hit (2ª chamada):      ${time2_ms}ms"
echo "Cache Hit (3ª chamada):      ${time3_ms}ms"
echo "Média com cache:             ${cache_avg}ms"
echo ""
echo "Melhoria:                    -${improvement}ms (-${improvement_pct}%)"

if [ $improvement -gt 30 ]; then
    echo "Status:                      ✅ CACHE FUNCIONANDO EFETIVAMENTE"
else
    echo "Status:                      ⚠️ Melhoria pequena (rede local rápida)"
fi

echo ""
echo "================================================================================"
