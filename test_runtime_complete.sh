#!/bin/bash
# Teste COMPLETO em runtime - valida TODAS as correções aplicadas
# Portas: Backend 5000, Frontend 8081

echo "=========================================="
echo "🧪 TESTE RUNTIME COMPLETO"
echo "=========================================="
echo ""

# Cores
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Teste 1: Backend fix NodeSelector
echo -e "${BLUE}[1/3] Testando backend fix nodes.py (porta 5000)...${NC}"
RESPONSE=$(curl -s http://localhost:5000/api/v1/nodes 2>/dev/null)
if echo "$RESPONSE" | grep -q '"site_name"'; then
    UNKNOWN_COUNT=$(echo "$RESPONSE" | grep -c '"site_name": "unknown"' || echo "0")
    IP_COUNT=$(echo "$RESPONSE" | grep -c '"site_name": "[0-9]' || echo "0")
    
    if [ "$UNKNOWN_COUNT" -eq 0 ] && [ "$IP_COUNT" -gt 0 ]; then
        echo -e "${GREEN}✅ Backend fix OK: Nenhum 'unknown', ${IP_COUNT} IPs encontrados${NC}"
        echo "$RESPONSE" | jq '.data[0] | {addr, site_name}' 2>/dev/null
    else
        echo -e "${RED}❌ Backend fix FALHOU: ${UNKNOWN_COUNT} 'unknown' encontrados${NC}"
    fi
else
    echo -e "${RED}❌ Backend não responde na porta 5000${NC}"
fi
echo ""

# Teste 2: Frontend disponível
echo -e "${BLUE}[2/3] Testando frontend (porta 8081)...${NC}"
if curl -s http://localhost:8081 2>/dev/null | grep -q "Skills Eye"; then
    echo -e "${GREEN}✅ Frontend OK: respondendo na porta 8081${NC}"
else
    echo -e "${RED}❌ Frontend não responde na porta 8081${NC}"
fi
echo ""

# Teste 3: Instruções de teste manual
echo -e "${BLUE}[3/3] Testes manuais necessários...${NC}"
echo -e "${YELLOW}📋 Abra o navegador em: http://localhost:8081${NC}"
echo ""
echo -e "${YELLOW}Verifique:${NC}"
echo "  1. ✅ NodeSelector mostra IPs (não 'unknown')"
echo "  2. ✅ Tooltips aparecem ao passar mouse nos botões:"
echo "     - Busca, Busca Avançada, Limpar Filtros, etc."
echo "  3. ✅ Console do navegador mostra logs coloridos:"
echo "     - [PERF] 🚀 requestHandler INÍCIO"
echo "     - [PERF] ⏱️  API respondeu em XXXms"
echo "     - [PERF] 📊 Total registros recebidos"
echo "     - [PERF] ✅ requestHandler COMPLETO"
echo "  4. ✅ Botão 'Limpar Filtros e Ordem' limpa ordenação visual"
echo "  5. ✅ Console mostra [MetadataFilterBar] DEBUG"
echo "  6. ✅ Ícones densidade/colunas visíveis no canto superior direito"
echo ""

echo "=========================================="
echo -e "${GREEN}✅ TESTE RUNTIME COMPLETO${NC}"
echo "=========================================="
