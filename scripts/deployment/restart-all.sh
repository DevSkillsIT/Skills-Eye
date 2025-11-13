#!/bin/bash

echo "🔄 REINICIANDO SKILLS EYE - Limpeza segura..."

# ============================================================================
# PASSO 1: MATAR APENAS PROCESSOS DO SKILLS EYE (não tudo!)
# ============================================================================

echo "[1/5] 🔪 Matando processos do Skills Eye..."

# Matar APENAS Python app.py do Skills Eye (não todos os Python!)
pkill -f "python.*Skills-Eye.*app.py" 2>/dev/null
pkill -f "python.*projetos/Skills-Eye.*app.py" 2>/dev/null

# Matar APENAS npm/vite do Skills Eye (não todos os Node!)
pkill -f "npm.*Skills-Eye" 2>/dev/null
pkill -f "vite.*Skills-Eye" 2>/dev/null
pkill -f "node.*Skills-Eye.*vite" 2>/dev/null

# Aguardar 2 segundos
sleep 2

# Verificar portas específicas do Skills Eye e matar se ainda estiverem em uso
echo "   → Verificando portas 5000, 8081, 8082, 8083..."

for port in 5000 8081 8082 8083; do
  PID=$(lsof -ti:$port 2>/dev/null)
  if [ ! -z "$PID" ]; then
    # Verificar se é processo do Skills Eye antes de matar
    PROC_INFO=$(ps -p $PID -o cmd= 2>/dev/null)
    if [[ "$PROC_INFO" == *"Skills-Eye"* ]] || [[ "$PROC_INFO" == *"app.py"* ]] || [[ "$PROC_INFO" == *"vite"* ]]; then
      echo "   → Matando processo Skills Eye na porta $port (PID: $PID)"
      kill -9 $PID 2>/dev/null
    else
      echo "   ⚠ Porta $port em uso por processo não-Skills Eye (ignorando)"
    fi
  fi
done

echo "   ✓ Processos do Skills Eye finalizados"

# ============================================================================
# PASSO 2: LIMPAR CACHE BACKEND
# ============================================================================

echo "[2/5] 🗑️  Limpando cache backend..."
cd ~/projetos/Skills-Eye/backend

# Remover __pycache__ recursivamente (apenas no projeto!)
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null
find . -type f -name "*.pyc" -delete 2>/dev/null
find . -type f -name "*.pyo" -delete 2>/dev/null

# Remover logs antigos
rm -f backend.log 2>/dev/null
rm -f nohup.out 2>/dev/null

echo "   ✓ Cache backend limpo"

# ============================================================================
# PASSO 3: LIMPAR CACHE FRONTEND
# ============================================================================

echo "[3/5] 🗑️  Limpando cache frontend..."
cd ~/projetos/Skills-Eye/frontend

# Remover cache Vite
rm -rf node_modules/.vite 2>/dev/null
rm -rf dist 2>/dev/null
rm -rf .vite 2>/dev/null

# Remover logs antigos
rm -f frontend.log 2>/dev/null
rm -f nohup.out 2>/dev/null

echo "   ✓ Cache frontend limpo"

# ============================================================================
# PASSO 4: INICIAR BACKEND
# ============================================================================

echo "[4/5] 🚀 Iniciando backend (porta 5000)..."
cd ~/projetos/Skills-Eye/backend

# Ativar venv e iniciar backend em background
source venv/bin/activate
nohup python app.py > backend.log 2>&1 &
BACKEND_PID=$!

echo "   ✓ Backend iniciado (PID: $BACKEND_PID)"

# ============================================================================
# PASSO 5: INICIAR FRONTEND
# ============================================================================

echo "[5/5] 🚀 Iniciando frontend (porta 8081)..."
cd ~/projetos/Skills-Eye/frontend

# Iniciar frontend em background
nohup npm run dev > frontend.log 2>&1 &
FRONTEND_PID=$!

echo "   ✓ Frontend iniciado (PID: $FRONTEND_PID)"

# ============================================================================
# RESUMO
# ============================================================================

echo ""
echo "✅ Skills Eye reiniciado com sucesso!"
echo ""
echo "📊 Processos:"
echo "   Backend:  PID $BACKEND_PID (porta 5000)"
echo "   Frontend: PID $FRONTEND_PID (porta 8081)"
echo ""
echo "📋 Logs:"
echo "   Backend:  tail -f ~/projetos/Skills-Eye/backend/backend.log"
echo "   Frontend: tail -f ~/projetos/Skills-Eye/frontend/frontend.log"
echo ""
echo "⏳ Aguardando 5 segundos para verificar se processos estão rodando..."
sleep 5

# Verificar se processos ainda estão vivos
if ps -p $BACKEND_PID > /dev/null 2>&1; then
  echo "   ✅ Backend rodando OK"
else
  echo "   ❌ Backend FALHOU! Ver logs: tail -f backend/backend.log"
fi

if ps -p $FRONTEND_PID > /dev/null 2>&1; then
  echo "   ✅ Frontend rodando OK"
else
  echo "   ❌ Frontend FALHOU! Ver logs: tail -f frontend/frontend.log"
fi

echo ""
echo "🌐 URLs:"
echo "   Backend:  http://localhost:5000/docs"
echo "   Frontend: http://localhost:8081"
echo ""
