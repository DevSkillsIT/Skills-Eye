#!/bin/bash

echo "⏹️  PARANDO SKILLS EYE - Limpeza segura..."

# Matar APENAS processos do Skills Eye (não tudo!)
echo "[1/3] 🔪 Matando processos do Skills Eye..."

# Python app.py do Skills Eye
pkill -f "python.*Skills-Eye.*app.py" 2>/dev/null
pkill -f "python.*projetos/Skills-Eye.*app.py" 2>/dev/null

# npm/vite do Skills Eye
pkill -f "npm.*Skills-Eye" 2>/dev/null
pkill -f "vite.*Skills-Eye" 2>/dev/null
pkill -f "node.*Skills-Eye.*vite" 2>/dev/null

echo "[2/3] 🔍 Verificando portas 5000, 8081, 8082, 8083..."
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

echo "[3/3] ✅ Skills Eye parado!"
echo ""
