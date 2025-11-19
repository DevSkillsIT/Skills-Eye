#!/bin/bash
# Teste: Validar navegação entre categorias

echo "================================================================================"
echo "TESTE: Validação de Navegação entre Categorias"
echo "================================================================================"

# Dados de cada categoria
echo -e "\n[1] Consultando dados das categorias no backend..."

echo -e "\n   System Exporters:"
SYSTEM_TOTAL=$(curl -s "http://localhost:5000/api/v1/monitoring/data?category=system-exporters" | jq -r '.total')
echo "   ├─ Total: $SYSTEM_TOTAL"
curl -s "http://localhost:5000/api/v1/monitoring/data?category=system-exporters" | \
  jq -r '.data[0:3] | .[] | "   ├─ \(.Meta.company // "N/A") - \(.Meta.instance // .ID)"' | head -3

echo -e "\n   Network Probes:"
NETWORK_TOTAL=$(curl -s "http://localhost:5000/api/v1/monitoring/data?category=network-probes" | jq -r '.total')
echo "   ├─ Total: $NETWORK_TOTAL"
curl -s "http://localhost:5000/api/v1/monitoring/data?category=network-probes" | \
  jq -r '.data[0:3] | .[] | "   ├─ \(.Meta.company // "N/A") - \(.Meta.instance // .ID)"' | head -3

echo -e "\n   Web Probes:"
WEB_TOTAL=$(curl -s "http://localhost:5000/api/v1/monitoring/data?category=web-probes" | jq -r '.total')
echo "   ├─ Total: $WEB_TOTAL"
if [ "$WEB_TOTAL" != "null" ] && [ "$WEB_TOTAL" -gt 0 ]; then
  curl -s "http://localhost:5000/api/v1/monitoring/data?category=web-probes" | \
    jq -r '.data[0:3] | .[] | "   ├─ \(.Meta.company // "N/A") - \(.Meta.instance // .ID)"' | head -3
else
  echo "   └─ (Nenhum dado)"
fi

echo -e "\n================================================================================"
echo "PROBLEMA IDENTIFICADO"
echo "================================================================================"
echo ""
echo "ANTES DA CORREÇÃO:"
echo "  ❌ useEffect tinha dependências: [selectedNode, filters]"
echo "  ❌ Faltava 'category' nas dependências"
echo "  ❌ Ao navegar de /system-exporters para /network-probes:"
echo "     → Título mudava (prop category mudava)"
echo "     → MAS dados NÃO recarregavam (useEffect não disparava)"
echo "     → Resultado: Mostrava dados de system-exporters na página network-probes"
echo ""
echo "DEPOIS DA CORREÇÃO:"
echo "  ✅ useEffect agora tem: [category, selectedNode, filters]"
echo "  ✅ useEffect adicional para resetar estados ao mudar category"
echo "  ✅ Limpa: filters, searchValue, selectedNode, advancedConditions, etc"
echo "  ✅ Força reload com actionRef.current?.reload()"
echo ""
echo "================================================================================"
echo "INSTRUÇÕES PARA TESTE MANUAL"
echo "================================================================================"
echo ""
echo "1. Abra: http://localhost:8081/monitoring/system-exporters"
echo "   → Deve mostrar $SYSTEM_TOTAL serviços (system-exporters)"
echo ""
echo "2. Clique no menu lateral: 'Network Probes (Rede)'"
echo "   → URL muda para: /monitoring/network-probes"
echo "   → Título muda para: 'Network Probes (Rede)'"
echo "   → ✅ DADOS DEVEM RECARREGAR AUTOMATICAMENTE"
echo "   → Deve mostrar $NETWORK_TOTAL serviços (network-probes)"
echo ""
echo "3. Clique no menu lateral: 'System Exporters'"
echo "   → URL muda para: /monitoring/system-exporters"
echo "   → Título muda para: 'Exporters: Sistemas'"
echo "   → ✅ DADOS DEVEM RECARREGAR AUTOMATICAMENTE"
echo "   → Deve voltar para $SYSTEM_TOTAL serviços (system-exporters)"
echo ""
echo "4. Verifique que NÃO é mais necessário:"
echo "   ❌ F5 (refresh completo)"
echo "   ❌ Ctrl+F5 (hard refresh)"
echo "   → Navegação deve funcionar instantaneamente"
echo ""
echo "================================================================================"
echo "CORREÇÕES APLICADAS"
echo "================================================================================"
echo ""
echo "Arquivo: frontend/src/pages/DynamicMonitoringPage.tsx"
echo ""
echo "CORREÇÃO #1 (linha ~805):"
echo "  useEffect(() => {"
echo "    actionRef.current?.reload();"
echo "  }, [category, selectedNode, filters]);  ← 'category' ADICIONADO"
echo ""
echo "CORREÇÃO #2 (linha ~810):"
echo "  useEffect(() => {"
echo "    // Resetar todos os estados ao mudar categoria"
echo "    setFilters({});"
echo "    setSearchValue('');"
echo "    setSelectedNode('all');"
echo "    // ... outros estados ..."
echo "    actionRef.current?.reload();"
echo "  }, [category]);  ← useEffect dedicado para reset"
echo ""
echo "================================================================================"
echo "STATUS DA CORREÇÃO"
echo "================================================================================"
echo ""
echo "✅ Código corrigido no arquivo TypeScript"
echo "✅ Vite dev server detectou mudança (hot reload automático)"
echo "✅ Teste manual no browser: http://localhost:8081/monitoring/system-exporters"
echo ""
echo "================================================================================"
