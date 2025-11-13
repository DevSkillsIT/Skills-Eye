#!/bin/bash

# Mata processos Node antigos
pkill -f "npm run dev" 2>/dev/null

# Limpa cache Vite
cd ~/projetos/Skills-Eye/frontend
rm -rf node_modules/.vite dist .vite 2>/dev/null

# Inicia frontend em background
nohup npm run dev > frontend.log 2>&1 &

echo "✅ Frontend reiniciado (porta 8081)"
echo "📋 Logs: tail -f ~/projetos/Skills-Eye/frontend/frontend.log"
