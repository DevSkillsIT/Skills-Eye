#\!/bin/bash

echo "=== REINICIANDO Skills-Eye com limpeza de cache ==="

# PASSO 1: Matar processos Python e Node
echo "[1/5] Matando processos Python e Node..."
pkill -9 python3 2>/dev/null || true
pkill -9 node 2>/dev/null || true
sleep 1

# PASSO 2: Limpar cache Python
echo "[2/5] Limpando cache Python..."
cd ~/projetos/Skills-Eye/backend
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -type f -name "*.pyc" -delete 2>/dev/null || true
echo "   ✓ Cache Python limpo"

# PASSO 3: Limpar cache Vite/Node
echo "[3/5] Limpando cache Vite/Frontend..."
cd ~/projetos/Skills-Eye/frontend
rm -rf node_modules/.vite 2>/dev/null || true
rm -rf dist 2>/dev/null || true
rm -rf .vite 2>/dev/null || true
echo "   ✓ Cache Vite limpo"

# PASSO 4: Aguardar liberação de portas
echo "[4/5] Aguardando portas 5000 e 8081..."
sleep 2

# PASSO 5: Reiniciar com tmux
echo "[5/5] Reiniciando aplicação no tmux..."

# Verificar se sessão existe
if tmux has-session -t skills-eye 2>/dev/null; then
    echo "   Matando sessão tmux antiga..."
    tmux kill-session -t skills-eye
    sleep 1
fi

# Criar nova sessão tmux
tmux new-session -d -s skills-eye

# Painel 1: Backend
tmux send-keys -t skills-eye "cd ~/projetos/Skills-Eye/backend && source venv/bin/activate && python app.py" C-m

# Painel 2: Frontend (split horizontal)
tmux split-window -t skills-eye -h
tmux send-keys -t skills-eye "cd ~/projetos/Skills-Eye/frontend && npm run dev" C-m

echo ""
echo "✅ Aplicação reiniciada com sucesso\!"
echo ""
echo "┌─────────────────────────────────────────────────┐"
echo "│  Backend:  http://localhost:5000                │"
echo "│  Frontend: http://localhost:8081                │"
echo "└─────────────────────────────────────────────────┘"
echo ""
echo "📌 Para conectar ao tmux:"
echo "   tmux attach -t skills-eye"
echo "   OU digite: skills"
echo ""
echo "⌨️  Atalhos do tmux (NOVO\!):"
echo "   Alt + ← →     : Navegar entre Backend/Frontend"
echo "   Ctrl+A depois D : Desconectar (deixa rodando)"
echo "   Ctrl+A depois X : Fechar painel atual"
echo "   Ctrl+A depois R : Recarregar config tmux"
echo "   Ctrl+A depois | : Split vertical"
echo "   Ctrl+A depois - : Split horizontal"
echo ""
echo "💡 Dica: Use o mouse para clicar, redimensionar e scroll\!"
echo ""
