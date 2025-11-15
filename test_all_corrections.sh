#!/bin/bash
# Script de teste completo para validar TODAS as correções aplicadas
# Baseado no arquivo histórico untitled:Untitled-1

echo "=========================================="
echo "🧪 TESTE COMPLETO - TODAS AS CORREÇÕES"
echo "=========================================="
echo ""

# Cores para output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}[1/6] Verificando backend fix (nodes.py)...${NC}"
if grep -q 'member\["addr"\]' backend/api/nodes.py; then
    echo -e "${GREEN}✅ Backend fix aplicado: usa IP ao invés de 'unknown'${NC}"
else
    echo -e "${RED}❌ Backend fix NÃO encontrado${NC}"
    exit 1
fi
echo ""

echo -e "${BLUE}[2/6] Verificando tooltips em botões...${NC}"
tooltip_count=$(grep -c 'Tooltip title=' frontend/src/pages/DynamicMonitoringPage.tsx || true)
if [ "$tooltip_count" -ge 8 ]; then
    echo -e "${GREEN}✅ Tooltips adicionados: $tooltip_count encontrados (esperado: 8+)${NC}"
else
    echo -e "${RED}❌ Tooltips insuficientes: $tooltip_count (esperado: 8+)${NC}"
    exit 1
fi
echo ""

echo -e "${BLUE}[3/6] Verificando performance logs...${NC}"
if grep -q '\[PERF\]' frontend/src/pages/DynamicMonitoringPage.tsx; then
    perf_logs=$(grep -c '\[PERF\]' frontend/src/pages/DynamicMonitoringPage.tsx || true)
    echo -e "${GREEN}✅ Performance logs adicionados: $perf_logs encontrados${NC}"
    
    # Verificar logs específicos
    if grep -q 'API respondeu em' frontend/src/pages/DynamicMonitoringPage.tsx; then
        echo -e "${GREEN}  ✓ Log de API${NC}"
    fi
    if grep -q 'metadataOptions calculado' frontend/src/pages/DynamicMonitoringPage.tsx; then
        echo -e "${GREEN}  ✓ Log de metadataOptions${NC}"
    fi
    if grep -q 'Filtros avançados' frontend/src/pages/DynamicMonitoringPage.tsx; then
        echo -e "${GREEN}  ✓ Log de filtros${NC}"
    fi
    if grep -q 'Ordenação' frontend/src/pages/DynamicMonitoringPage.tsx; then
        echo -e "${GREEN}  ✓ Log de ordenação${NC}"
    fi
    if grep -q 'Paginação' frontend/src/pages/DynamicMonitoringPage.tsx; then
        echo -e "${GREEN}  ✓ Log de paginação${NC}"
    fi
else
    echo -e "${RED}❌ Performance logs NÃO encontrados${NC}"
    exit 1
fi
echo ""

echo -e "${BLUE}[4/6] Verificando fix do botão 'Limpar Filtros e Ordem'...${NC}"
if grep -q 'setSortField(null)' frontend/src/pages/DynamicMonitoringPage.tsx && \
   grep -q 'setSortOrder(null)' frontend/src/pages/DynamicMonitoringPage.tsx; then
    echo -e "${GREEN}✅ Fix do botão aplicado: limpa sortField e sortOrder${NC}"
else
    echo -e "${RED}❌ Fix do botão NÃO encontrado${NC}"
    exit 1
fi
echo ""

echo -e "${BLUE}[5/6] Verificando debug logs MetadataFilterBar...${NC}"
if grep -q 'DEBUG:' frontend/src/components/MetadataFilterBar.tsx; then
    echo -e "${GREEN}✅ Debug logs adicionados ao MetadataFilterBar${NC}"
else
    echo -e "${RED}❌ Debug logs NÃO encontrados${NC}"
    exit 1
fi
echo ""

echo -e "${BLUE}[6/6] Verificando ícones density/columns...${NC}"
if grep -q 'reload: true' frontend/src/pages/DynamicMonitoringPage.tsx && \
   grep -q 'setting: true' frontend/src/pages/DynamicMonitoringPage.tsx && \
   grep -q 'density: true' frontend/src/pages/DynamicMonitoringPage.tsx; then
    echo -e "${GREEN}✅ Ícones habilitados: reload, setting, density${NC}"
else
    echo -e "${RED}❌ Ícones NÃO configurados corretamente${NC}"
    exit 1
fi
echo ""

echo "=========================================="
echo -e "${GREEN}✅ TODOS OS TESTES PASSARAM!${NC}"
echo "=========================================="
echo ""
echo -e "${YELLOW}📝 Resumo das correções aplicadas:${NC}"
echo "  1. Backend nodes.py: IP ao invés de 'unknown'"
echo "  2. Frontend: $tooltip_count tooltips em botões"
echo "  3. Frontend: $perf_logs performance logs"
echo "  4. Frontend: Limpar Filtros e Ordem corrigido"
echo "  5. Frontend: Debug logs MetadataFilterBar"
echo "  6. Frontend: Ícones density/columns habilitados"
echo ""
echo -e "${YELLOW}🚀 Próximos passos:${NC}"
echo "  1. Reiniciar backend e frontend"
echo "  2. Testar NodeSelector (deve mostrar IPs, não 'unknown')"
echo "  3. Verificar tooltips ao passar mouse nos botões"
echo "  4. Abrir console do navegador para ver logs de performance"
echo "  5. Testar botão 'Limpar Filtros e Ordem'"
echo "  6. Verificar se ícones de densidade/colunas aparecem"
echo ""
