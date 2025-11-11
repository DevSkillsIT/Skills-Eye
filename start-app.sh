#\!/bin/bash

echo "=== INICIANDO Skills-Eye ==="

# PASSO 1: Verificar se já está rodando
if tmux has-session -t skills-eye 2>/dev/null; then
    echo "⚠️  Aplicação já está rodando\!"
    echo ""
    echo "Opções:"
    echo "  eye-stop      - Parar a aplicação"
    echo "  eye-restart   - Reiniciar com limpeza"
    echo "  skills        - Conectar no tmux"
    exit 1
fi

# PASSO 2: Verificar se portas estão livres
if lsof -Pi :5000 -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo "⚠️  Porta 5000 ocupada\! Limpando..."
    lsof -ti:5000 | xargs kill -9 2>/dev/null || true
    sleep 1
fi

if lsof -Pi :8081 -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo "⚠️  Porta 8081 ocupada\! Limpando..."
    lsof -ti:8081 | xargs kill -9 2>/dev/null || true
    sleep 1
fi

# PASSO 3: Criar sessão tmux
echo "[1/2] Criando sessão tmux..."
tmux new-session -d -s skills-eye

# Painel 1: Backend
tmux send-keys -t skills-eye "cd ~/projetos/Skills-Eye/backend && source venv/bin/activate && python app.py" C-m

# Painel 2: Frontend (split horizontal)
tmux split-window -t skills-eye -h
tmux send-keys -t skills-eye "cd ~/projetos/Skills-Eye/frontend && npm run dev" C-m

echo "[2/2] Aguardando inicialização..."
sleep 2

echo ""
echo "✅ Aplicação iniciada com sucesso\!"
echo ""
echo "┌─────────────────────────────────────────────────┐"
echo "│  Backend:  http://localhost:5000                │"
echo "│  Frontend: http://localhost:8081                │"
echo "└─────────────────────────────────────────────────┘"
echo ""
echo "📌 Para ver logs:"
echo "   skills    (ou: tmux attach -t skills-eye)"
echo ""
echo "⌨️  Navegação: Alt + ← → (entre painéis)"
echo "   Desconectar: Ctrl+A depois D"
