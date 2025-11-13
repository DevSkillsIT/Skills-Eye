#!/bin/bash

# Script Master para Executar TODOS os Testes de Persistência
# 
# Executa sequencialmente:
# 1. Testes básicos (test_fields_merge.py)
# 2. Testes de todos os cenários (test_all_scenarios.py)
# 3. Testes de stress (test_stress_scenarios.py)
# 4. Testes de integração frontend (test_frontend_integration.py)

set -e  # Parar em qualquer erro

BACKEND_DIR="/home/adrianofante/projetos/Skills-Eye/backend"
LOG_FILE="${BACKEND_DIR}/test_results_$(date +%Y%m%d_%H%M%S).log"

# Cores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

echo -e "${PURPLE}╔════════════════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${PURPLE}║                                                                            ║${NC}"
echo -e "${PURPLE}║          BATERIA COMPLETA DE TESTES - PERSISTÊNCIA DE CUSTOMIZAÇÕES       ║${NC}"
echo -e "${PURPLE}║                                                                            ║${NC}"
echo -e "${PURPLE}╚════════════════════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${BLUE}📅 Data/Hora: $(date '+%Y-%m-%d %H:%M:%S')${NC}"
echo -e "${BLUE}📂 Diretório: ${BACKEND_DIR}${NC}"
echo -e "${BLUE}📄 Log: ${LOG_FILE}${NC}"
echo ""

cd "${BACKEND_DIR}"

# Função para executar teste
run_test() {
    local test_name="$1"
    local test_script="$2"
    local test_number="$3"
    
    echo "" | tee -a "${LOG_FILE}"
    echo -e "${PURPLE}═══════════════════════════════════════════════════════════════════════════${NC}" | tee -a "${LOG_FILE}"
    echo -e "${PURPLE}  TESTE ${test_number}: ${test_name}${NC}" | tee -a "${LOG_FILE}"
    echo -e "${PURPLE}═══════════════════════════════════════════════════════════════════════════${NC}" | tee -a "${LOG_FILE}"
    echo "" | tee -a "${LOG_FILE}"
    
    if python3 "${test_script}" 2>&1 | tee -a "${LOG_FILE}"; then
        echo "" | tee -a "${LOG_FILE}"
        echo -e "${GREEN}✅ ${test_name} - PASSOU${NC}" | tee -a "${LOG_FILE}"
        return 0
    else
        echo "" | tee -a "${LOG_FILE}"
        echo -e "${RED}❌ ${test_name} - FALHOU${NC}" | tee -a "${LOG_FILE}"
        return 1
    fi
}

# Contador de resultados
total_tests=0
passed_tests=0
failed_tests=0

# Array para armazenar resultados
declare -a test_results

echo -e "${YELLOW}⚙️  Verificando backend...${NC}"
if ! curl -s http://localhost:5000/api/v1/metadata-fields/ > /dev/null; then
    echo -e "${RED}❌ Backend não está respondendo em http://localhost:5000${NC}"
    echo -e "${YELLOW}Por favor, inicie o backend antes de executar os testes${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Backend OK${NC}"
echo ""

# ============================================================================
# TESTE 1: Básico (test_fields_merge.py)
# ============================================================================
echo -e "${BLUE}Executando TESTE 1/4: Testes Básicos de Merge...${NC}"
echo ""
read -p "Pressione ENTER para iniciar..."

total_tests=$((total_tests + 1))
if run_test "Testes Básicos de Merge" "test_fields_merge.py" "1/4"; then
    passed_tests=$((passed_tests + 1))
    test_results+=("✅ Testes Básicos de Merge")
else
    failed_tests=$((failed_tests + 1))
    test_results+=("❌ Testes Básicos de Merge")
fi

# ============================================================================
# TESTE 2: Todos os Cenários (test_all_scenarios.py)
# ============================================================================
echo ""
echo -e "${BLUE}Executando TESTE 2/4: Todos os Cenários...${NC}"
echo ""
read -p "Pressione ENTER para iniciar..."

total_tests=$((total_tests + 1))
if run_test "Todos os Cenários" "test_all_scenarios.py" "2/4"; then
    passed_tests=$((passed_tests + 1))
    test_results+=("✅ Todos os Cenários")
else
    failed_tests=$((failed_tests + 1))
    test_results+=("❌ Todos os Cenários")
fi

# ============================================================================
# TESTE 3: Stress Tests (test_stress_scenarios.py)
# ============================================================================
echo ""
echo -e "${BLUE}Executando TESTE 3/4: Stress Tests...${NC}"
echo ""
read -p "Pressione ENTER para iniciar..."

total_tests=$((total_tests + 1))
if run_test "Stress Tests" "test_stress_scenarios.py" "3/4"; then
    passed_tests=$((passed_tests + 1))
    test_results+=("✅ Stress Tests")
else
    failed_tests=$((failed_tests + 1))
    test_results+=("❌ Stress Tests")
fi

# ============================================================================
# TESTE 4: Integração Frontend (test_frontend_integration.py)
# ============================================================================
echo ""
echo -e "${BLUE}Executando TESTE 4/4: Integração Frontend (Playwright)...${NC}"
echo ""
echo -e "${YELLOW}⚠️  Este teste requer frontend rodando em http://localhost:3000${NC}"
echo -e "${YELLOW}⚠️  E Playwright instalado (pip install playwright; playwright install chromium)${NC}"
echo ""
read -p "Deseja executar os testes de integração frontend? (s/N): " run_ui_tests

if [[ "$run_ui_tests" =~ ^[Ss]$ ]]; then
    # Verificar frontend
    if ! curl -s http://localhost:3000 > /dev/null; then
        echo -e "${RED}❌ Frontend não está respondendo em http://localhost:3000${NC}"
        echo -e "${YELLOW}Pulando testes de integração frontend${NC}"
        test_results+=("⚠️  Integração Frontend - PULADO")
    else
        total_tests=$((total_tests + 1))
        if run_test "Integração Frontend" "test_frontend_integration.py" "4/4"; then
            passed_tests=$((passed_tests + 1))
            test_results+=("✅ Integração Frontend")
        else
            failed_tests=$((failed_tests + 1))
            test_results+=("❌ Integração Frontend")
        fi
    fi
else
    echo -e "${YELLOW}⚠️  Testes de integração frontend PULADOS${NC}" | tee -a "${LOG_FILE}"
    test_results+=("⚠️  Integração Frontend - PULADO")
fi

# ============================================================================
# RELATÓRIO FINAL
# ============================================================================
echo "" | tee -a "${LOG_FILE}"
echo "" | tee -a "${LOG_FILE}"
echo -e "${PURPLE}╔════════════════════════════════════════════════════════════════════════════╗${NC}" | tee -a "${LOG_FILE}"
echo -e "${PURPLE}║                                                                            ║${NC}" | tee -a "${LOG_FILE}"
echo -e "${PURPLE}║                          RELATÓRIO FINAL DE TESTES                         ║${NC}" | tee -a "${LOG_FILE}"
echo -e "${PURPLE}║                                                                            ║${NC}" | tee -a "${LOG_FILE}"
echo -e "${PURPLE}╚════════════════════════════════════════════════════════════════════════════╝${NC}" | tee -a "${LOG_FILE}"
echo "" | tee -a "${LOG_FILE}"

echo -e "${BLUE}📊 Estatísticas:${NC}" | tee -a "${LOG_FILE}"
echo -e "   Total de Suítes: ${total_tests}" | tee -a "${LOG_FILE}"
echo -e "   ${GREEN}Passou: ${passed_tests}${NC}" | tee -a "${LOG_FILE}"
echo -e "   ${RED}Falhou: ${failed_tests}${NC}" | tee -a "${LOG_FILE}"
echo "" | tee -a "${LOG_FILE}"

echo -e "${BLUE}📋 Resultados por Suíte:${NC}" | tee -a "${LOG_FILE}"
for result in "${test_results[@]}"; do
    echo "   ${result}" | tee -a "${LOG_FILE}"
done
echo "" | tee -a "${LOG_FILE}"

if [ ${failed_tests} -eq 0 ]; then
    echo -e "${GREEN}╔════════════════════════════════════════════════════════════════════════════╗${NC}" | tee -a "${LOG_FILE}"
    echo -e "${GREEN}║                                                                            ║${NC}" | tee -a "${LOG_FILE}"
    echo -e "${GREEN}║                    ✅ TODOS OS TESTES PASSARAM! ✅                         ║${NC}" | tee -a "${LOG_FILE}"
    echo -e "${GREEN}║                                                                            ║${NC}" | tee -a "${LOG_FILE}"
    echo -e "${GREEN}║          Customizações de campos estão TOTALMENTE PROTEGIDAS!             ║${NC}" | tee -a "${LOG_FILE}"
    echo -e "${GREEN}║                                                                            ║${NC}" | tee -a "${LOG_FILE}"
    echo -e "${GREEN}╚════════════════════════════════════════════════════════════════════════════╝${NC}" | tee -a "${LOG_FILE}"
    exit 0
else
    echo -e "${RED}╔════════════════════════════════════════════════════════════════════════════╗${NC}" | tee -a "${LOG_FILE}"
    echo -e "${RED}║                                                                            ║${NC}" | tee -a "${LOG_FILE}"
    echo -e "${RED}║                     ❌ ALGUNS TESTES FALHARAM! ❌                          ║${NC}" | tee -a "${LOG_FILE}"
    echo -e "${RED}║                                                                            ║${NC}" | tee -a "${LOG_FILE}"
    echo -e "${RED}║        Há problemas de persistência que precisam ser corrigidos!          ║${NC}" | tee -a "${LOG_FILE}"
    echo -e "${RED}║                                                                            ║${NC}" | tee -a "${LOG_FILE}"
    echo -e "${RED}╚════════════════════════════════════════════════════════════════════════════╝${NC}" | tee -a "${LOG_FILE}"
    exit 1
fi
