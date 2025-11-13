#!/bin/bash

# Mata processos Python antigos
pkill -f "python.*app.py" 2>/dev/null

# Limpa cache Python
cd ~/projetos/Skills-Eye/backend
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null
find . -type f -name "*.pyc" -delete 2>/dev/null

# Inicia backend em background
source venv/bin/activate
nohup python app.py > backend.log 2>&1 &

echo "✅ Backend reiniciado (porta 5000)"
echo "📋 Logs: tail -f ~/projetos/Skills-Eye/backend/backend.log"
