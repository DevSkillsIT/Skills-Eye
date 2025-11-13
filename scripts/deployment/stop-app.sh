#\!/bin/bash

echo "=== PARANDO Skills-Eye e limpando cache ==="

# PASSO 1: Matar processos Python e Node
echo "[1/4] Matando TODOS os processos Python e Node..."
pkill -9 python3 2>/dev/null || true
pkill -9 python 2>/dev/null || true
pkill -9 node 2>/dev/null || true
pkill -9 npm 2>/dev/null || true
sleep 1
echo "   ✓ Processos finalizados"

# PASSO 2: Matar sessão tmux
echo "[2/4] Encerrando sessão tmux..."
if tmux has-session -t skills-eye 2>/dev/null; then
    tmux kill-session -t skills-eye
    echo "   ✓ Sessão tmux encerrada"
else
    echo "   ℹ Nenhuma sessão tmux ativa"
fi

# PASSO 3: Limpar cache Python
echo "[3/4] Limpando cache Python..."
cd ~/projetos/Skills-Eye/backend
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -type f -name "*.pyc" -delete 2>/dev/null || true
find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
echo "   ✓ Cache Python limpo"

# PASSO 4: Limpar cache Vite/Node
echo "[4/4] Limpando cache Vite/Frontend..."
cd ~/projetos/Skills-Eye/frontend
rm -rf node_modules/.vite 2>/dev/null || true
rm -rf dist 2>/dev/null || true
rm -rf .vite 2>/dev/null || true
rm -rf .parcel-cache 2>/dev/null || true
echo "   ✓ Cache Vite limpo"

echo ""
echo "✅ Aplicação parada e cache limpo\!"
echo ""
echo "Para iniciar novamente:"
echo "  eye-start    (ou: ./start-app.sh)"
