# 🚀 Skills-Eye - Comandos Rápidos

## ⚡ Comandos Principais



## 📋 Detalhamento dos Comandos

### 🛑 eye-stop
**O que faz:**
- Mata TODOS os processos Python/Node relacionados (pkill -9)
- Encerra sessão tmux se existir
- Limpa cache Python (__pycache__, *.pyc, *.egg-info)
- Limpa cache Vite (.vite, dist, node_modules/.vite, .parcel-cache)
- **NÃO reinicia** a aplicação

**Use quando:**
- Terminou de trabalhar no projeto
- Precisa liberar portas 5000/8081
- Quer garantir que NADA está rodando

### ▶️ eye-start
**O que faz:**
- Verifica se já está rodando (evita duplicação)
- Verifica se portas 5000/8081 estão livres
- Cria sessão tmux "skills-eye"
- Inicia Backend (painel esquerdo) + Frontend (painel direito)
- Mostra URLs de acesso

**Use quando:**
- Iniciar trabalho no projeto
- Após usar eye-stop
- Primeira vez após boot do PC

### 🔄 eye-restart
**O que faz:**
- Executa eye-stop (para tudo e limpa cache)
- Aguarda 2 segundos
- Executa eye-start (reinicia tudo)
- Mostra atalhos do tmux

**Use quando:**
- Fez mudanças que exigem restart
- Cache está causando problemas
- Quer garantir ambiente limpo

### 👁️ skills
**O que faz:**
- Conecta na sessão tmux existente
- Mostra logs do Backend e Frontend lado a lado

**Use quando:**
- Quer ver logs em tempo real
- Precisa debugar algo
- Quer verificar se está rodando

## 🎯 Fluxo de Trabalho Típico

### Início do Dia


### Durante Desenvolvimento


### Fim do Dia


## ⌨️ Atalhos do tmux (quando conectado com skills)

| Ação | Atalho |
|------|--------|
| Navegar painéis |  |
| Desconectar |  depois  |
| Fechar painel |  depois  |
| Recarregar config |  depois  |
| Split vertical |  depois  |
| Split horizontal |  depois  |

## 🔧 Comandos Manuais (avançado)

root         206  0.0  0.5 107028 21880 ?        Ssl  09:16   0:00 /usr/bin/python3 /usr/share/unattended-upgrades/unattended-upgrade-shutdown --wait-for-signal
adriano+    5715  0.8  4.0 1240612 168504 pts/2  Sl+  10:03   0:05 python app.py
adriano+    5849  0.0  0.0   4756  3328 pts/4    Ss+  10:05   0:00 /bin/bash -c bash -c "cd ~/projetos/Skills-Eye && cat > GUIA_WSL.md << 'EOF' # 🚀 Skills-Eye - Guia Rápido WSL  ## ⚡ Comandos Principais  ```bash restart    # Reinicia app com limpeza de cache skills     # Conecta no tmux ```  ## 🎯 Atalhos do tmux  ### Navegação (FÁCIL\!) - `Alt + ← →` - Navegar entre Backend/Frontend (SEM precisar de Ctrl+A\!) - `Alt + ↑ ↓` - Navegar vertical se tiver mais painéis  ### Comandos (Ctrl+A depois...) - `Ctrl+A` depois `D` - Desconectar (deixa rodando) - `Ctrl+A` depois `X` - Fechar painel atual - `Ctrl+A` depois `R` - Recarregar config tmux - `Ctrl+A` depois `|` - Split vertical - `Ctrl+A` depois `-` - Split horizontal  ### Mouse 🖱️ - ✅ Clicar para trocar de painel - ✅ Arrastar borda para redimensionar - ✅ Scroll com roda do mouse  ## 📊 URLs  - Backend: http://localhost:5000 - Frontend: http://localhost:8081 - API Docs: http://localhost:5000/docs  ## 🔧 Comandos de Manutenção  ```bash # Backend (manual) cd ~/projetos/Skills-Eye/backend source venv/bin/activate python app.py  # Frontend (manual) cd ~/projetos/Skills-Eye/frontend npm run dev  # Atualizar dependências Python cd ~/projetos/Skills-Eye/backend source venv/bin/activate pip install -r requirements.txt  # Atualizar dependências Node cd ~/projetos/Skills-Eye/frontend npm install  # Ver processos rodando ps aux | grep python ps aux | grep node  # Matar processos manualmente pkill -9 python3 pkill -9 node ```  ## 📝 Git  ```bash cd ~/projetos/Skills-Eye  # Status git status  # Commit git add . git commit -m \"feat: sua mensagem aqui\"  # Push git push  # Pull git pull ```  ## 🐛 Troubleshooting  ### Porta 5000 ocupada ```bash lsof -ti:5000 | xargs kill -9 ```  ### Porta 8081 ocupada ```bash lsof -ti:8081 | xargs kill -9 ```  ### Limpar TUDO e recomeçar ```bash cd ~/projetos/Skills-Eye pkill -9 python3 pkill -9 node tmux kill-session -t skills-eye ./restart-app.sh ```  ## 💡 Dicas  1. **Sempre use `restart`** para garantir cache limpo 2. **Use `Alt + Setas`** para navegar - é mais rápido\! 3. **Mouse funciona\!** Clique e arraste à vontade 4. **`Ctrl+A D`** para desconectar sem parar a app 5. **`skills`** para voltar pro tmux  ## 📚 Comparativo Windows vs WSL  | Ação | Windows | WSL | |------|---------|-----| | Reiniciar | `restart-app.bat` | `restart` | | Ver logs | Janelas separadas | `skills` (tmux) | | Performance | Lento (~20s SSH) | Rápido (~2-3s) | | Cache | Múltiplas pastas | `__pycache__` + `.vite` |  ---  **Dúvidas?** Consulte: `~/projetos/Skills-Eye/MIGRACAO_WSL_PLANO_COMPLETO.md` EOF echo \"✓ Guia criado em ~/projetos/Skills-Eye/GUIA_WSL.md\""
adriano+    5865  0.0  0.0   4888  2092 pts/4    S+   10:05   0:00 /bin/bash -c bash -c "cd ~/projetos/Skills-Eye && cat > GUIA_WSL.md << 'EOF' # 🚀 Skills-Eye - Guia Rápido WSL  ## ⚡ Comandos Principais  ```bash restart    # Reinicia app com limpeza de cache skills     # Conecta no tmux ```  ## 🎯 Atalhos do tmux  ### Navegação (FÁCIL\!) - `Alt + ← →` - Navegar entre Backend/Frontend (SEM precisar de Ctrl+A\!) - `Alt + ↑ ↓` - Navegar vertical se tiver mais painéis  ### Comandos (Ctrl+A depois...) - `Ctrl+A` depois `D` - Desconectar (deixa rodando) - `Ctrl+A` depois `X` - Fechar painel atual - `Ctrl+A` depois `R` - Recarregar config tmux - `Ctrl+A` depois `|` - Split vertical - `Ctrl+A` depois `-` - Split horizontal  ### Mouse 🖱️ - ✅ Clicar para trocar de painel - ✅ Arrastar borda para redimensionar - ✅ Scroll com roda do mouse  ## 📊 URLs  - Backend: http://localhost:5000 - Frontend: http://localhost:8081 - API Docs: http://localhost:5000/docs  ## 🔧 Comandos de Manutenção  ```bash # Backend (manual) cd ~/projetos/Skills-Eye/backend source venv/bin/activate python app.py  # Frontend (manual) cd ~/projetos/Skills-Eye/frontend npm run dev  # Atualizar dependências Python cd ~/projetos/Skills-Eye/backend source venv/bin/activate pip install -r requirements.txt  # Atualizar dependências Node cd ~/projetos/Skills-Eye/frontend npm install  # Ver processos rodando ps aux | grep python ps aux | grep node  # Matar processos manualmente pkill -9 python3 pkill -9 node ```  ## 📝 Git  ```bash cd ~/projetos/Skills-Eye  # Status git status  # Commit git add . git commit -m \"feat: sua mensagem aqui\"  # Push git push  # Pull git pull ```  ## 🐛 Troubleshooting  ### Porta 5000 ocupada ```bash lsof -ti:5000 | xargs kill -9 ```  ### Porta 8081 ocupada ```bash lsof -ti:8081 | xargs kill -9 ```  ### Limpar TUDO e recomeçar ```bash cd ~/projetos/Skills-Eye pkill -9 python3 pkill -9 node tmux kill-session -t skills-eye ./restart-app.sh ```  ## 💡 Dicas  1. **Sempre use `restart`** para garantir cache limpo 2. **Use `Alt + Setas`** para navegar - é mais rápido\! 3. **Mouse funciona\!** Clique e arraste à vontade 4. **`Ctrl+A D`** para desconectar sem parar a app 5. **`skills`** para voltar pro tmux  ## 📚 Comparativo Windows vs WSL  | Ação | Windows | WSL | |------|---------|-----| | Reiniciar | `restart-app.bat` | `restart` | | Ver logs | Janelas separadas | `skills` (tmux) | | Performance | Lento (~20s SSH) | Rápido (~2-3s) | | Cache | Múltiplas pastas | `__pycache__` + `.vite` |  ---  **Dúvidas?** Consulte: `~/projetos/Skills-Eye/MIGRACAO_WSL_PLANO_COMPLETO.md` EOF echo \"✓ Guia criado em ~/projetos/Skills-Eye/GUIA_WSL.md\""
adriano+    6247  0.0  0.0   4756  3328 pts/7    Ss+  10:15   0:00 /bin/bash -c bash -c "cd ~/projetos/Skills-Eye && cat > COMANDOS_RAPIDOS.md << 'EOF' # 🚀 Skills-Eye - Comandos Rápidos  ## ⚡ Comandos Principais  ```bash eye-stop      # Para aplicação e limpa cache (SEM reiniciar) eye-start     # Inicia aplicação no tmux eye-restart   # Reinicia com limpeza total de cache skills        # Conecta no tmux para ver logs ```  ## 📋 Detalhamento dos Comandos  ### 🛑 eye-stop **O que faz:** - Mata TODOS os processos Python/Node relacionados (pkill -9) - Encerra sessão tmux se existir - Limpa cache Python (__pycache__, *.pyc, *.egg-info) - Limpa cache Vite (.vite, dist, node_modules/.vite, .parcel-cache) - **NÃO reinicia** a aplicação  **Use quando:** - Terminou de trabalhar no projeto - Precisa liberar portas 5000/8081 - Quer garantir que NADA está rodando  ### ▶️ eye-start **O que faz:** - Verifica se já está rodando (evita duplicação) - Verifica se portas 5000/8081 estão livres - Cria sessão tmux \"skills-eye\" - Inicia Backend (painel esquerdo) + Frontend (painel direito) - Mostra URLs de acesso  **Use quando:** - Iniciar trabalho no projeto - Após usar eye-stop - Primeira vez após boot do PC  ### 🔄 eye-restart **O que faz:** - Executa eye-stop (para tudo e limpa cache) - Aguarda 2 segundos - Executa eye-start (reinicia tudo) - Mostra atalhos do tmux  **Use quando:** - Fez mudanças que exigem restart - Cache está causando problemas - Quer garantir ambiente limpo  ### 👁️ skills **O que faz:** - Conecta na sessão tmux existente - Mostra logs do Backend e Frontend lado a lado  **Use quando:** - Quer ver logs em tempo real - Precisa debugar algo - Quer verificar se está rodando  ## 🎯 Fluxo de Trabalho Típico  ### Início do Dia ```bash eye-start    # Inicia tudo skills       # Vê se subiu OK # Ctrl+A D   # Desconecta (deixa rodando) ```  ### Durante Desenvolvimento ```bash # Trabalha normalmente... # Se precisar ver logs: skills       # Conecta no tmux # Alt + ←→   # Navega entre painéis # Ctrl+A D   # Desconecta  # Se fez mudanças grandes: eye-restart  # Reinicia com cache limpo ```  ### Fim do Dia ```bash eye-stop     # Para tudo e limpa cache ```  ## ⌨️ Atalhos do tmux (quando conectado com skills)  | Ação | Atalho | |------|--------| | Navegar painéis | `Alt + ← →` | | Desconectar | `Ctrl+A` depois `D` | | Fechar painel | `Ctrl+A` depois `X` | | Recarregar config | `Ctrl+A` depois `R` | | Split vertical | `Ctrl+A` depois `\|` | | Split horizontal | `Ctrl+A` depois `-` |  ## 🔧 Comandos Manuais (avançado)  ```bash # Ver processos rodando ps aux | grep python ps aux | grep node tmux ls  # Listar sessões tmux  # Verificar portas ocupadas lsof -i :5000 lsof -i :8081  # Matar processos manualmente pkill -9 python3 pkill -9 node tmux kill-session -t skills-eye  # Limpar cache manualmente cd ~/projetos/Skills-Eye/backend find . -type d -name \"__pycache__\" -exec rm -rf {} +  cd ~/projetos/Skills-Eye/frontend rm -rf node_modules/.vite dist .vite ```  ## 📊 Comparação de Comandos  | Preciso... | Comando | |-----------|---------| | Iniciar projeto | `eye-start` | | Parar projeto | `eye-stop` | | Reiniciar com cache limpo | `eye-restart` | | Ver logs | `skills` | | Desconectar logs (deixar rodando) | `Ctrl+A` depois `D` | | Navegar entre Backend/Frontend | `Alt + ← →` |  ## 🐛 Troubleshooting  ### \"Aplicação já está rodando\" ```bash eye-stop eye-start ```  ### \"Porta 5000/8081 ocupada\" ```bash eye-stop    # Já limpa as portas eye-start ```  ### \"tmux session not found\" ```bash eye-start   # Cria nova sessão ```  ### Cache não limpa ```bash eye-stop    # Para e limpa # Verifica manualmente: cd ~/projetos/Skills-Eye/backend find . -name \"__pycache__\" -type d  # Deve estar vazio cd ~/projetos/Skills-Eye/frontend ls -la node_modules/.vite  # Deve dar erro (não existe) ```  ## 💡 Dicas  1. **Use `eye-restart`** quando em dúvida - é o mais seguro 2. **`Alt + Setas`** para navegar - não precisa de Ctrl+A 3. **Mouse funciona** no tmux - clique e redimensione à vontade 4. **`Ctrl+A D`** para deixar rodando e voltar ao terminal 5. **`eye-stop`** antes de pull/merge do Git  ---  **Aliases disponíveis:** - `eye-stop` → ~/projetos/Skills-Eye/stop-app.sh - `eye-start` → ~/projetos/Skills-Eye/start-app.sh - `eye-restart` → ~/projetos/Skills-Eye/restart-app.sh - `skills` → tmux attach -t skills-eye - `restart` → (legado, usa eye-restart) EOF echo \"✓ COMANDOS_RAPIDOS.md criado\""
adriano+    6273  0.0  0.0   4756  1732 pts/7    S+   10:15   0:00 /bin/bash -c bash -c "cd ~/projetos/Skills-Eye && cat > COMANDOS_RAPIDOS.md << 'EOF' # 🚀 Skills-Eye - Comandos Rápidos  ## ⚡ Comandos Principais  ```bash eye-stop      # Para aplicação e limpa cache (SEM reiniciar) eye-start     # Inicia aplicação no tmux eye-restart   # Reinicia com limpeza total de cache skills        # Conecta no tmux para ver logs ```  ## 📋 Detalhamento dos Comandos  ### 🛑 eye-stop **O que faz:** - Mata TODOS os processos Python/Node relacionados (pkill -9) - Encerra sessão tmux se existir - Limpa cache Python (__pycache__, *.pyc, *.egg-info) - Limpa cache Vite (.vite, dist, node_modules/.vite, .parcel-cache) - **NÃO reinicia** a aplicação  **Use quando:** - Terminou de trabalhar no projeto - Precisa liberar portas 5000/8081 - Quer garantir que NADA está rodando  ### ▶️ eye-start **O que faz:** - Verifica se já está rodando (evita duplicação) - Verifica se portas 5000/8081 estão livres - Cria sessão tmux \"skills-eye\" - Inicia Backend (painel esquerdo) + Frontend (painel direito) - Mostra URLs de acesso  **Use quando:** - Iniciar trabalho no projeto - Após usar eye-stop - Primeira vez após boot do PC  ### 🔄 eye-restart **O que faz:** - Executa eye-stop (para tudo e limpa cache) - Aguarda 2 segundos - Executa eye-start (reinicia tudo) - Mostra atalhos do tmux  **Use quando:** - Fez mudanças que exigem restart - Cache está causando problemas - Quer garantir ambiente limpo  ### 👁️ skills **O que faz:** - Conecta na sessão tmux existente - Mostra logs do Backend e Frontend lado a lado  **Use quando:** - Quer ver logs em tempo real - Precisa debugar algo - Quer verificar se está rodando  ## 🎯 Fluxo de Trabalho Típico  ### Início do Dia ```bash eye-start    # Inicia tudo skills       # Vê se subiu OK # Ctrl+A D   # Desconecta (deixa rodando) ```  ### Durante Desenvolvimento ```bash # Trabalha normalmente... # Se precisar ver logs: skills       # Conecta no tmux # Alt + ←→   # Navega entre painéis # Ctrl+A D   # Desconecta  # Se fez mudanças grandes: eye-restart  # Reinicia com cache limpo ```  ### Fim do Dia ```bash eye-stop     # Para tudo e limpa cache ```  ## ⌨️ Atalhos do tmux (quando conectado com skills)  | Ação | Atalho | |------|--------| | Navegar painéis | `Alt + ← →` | | Desconectar | `Ctrl+A` depois `D` | | Fechar painel | `Ctrl+A` depois `X` | | Recarregar config | `Ctrl+A` depois `R` | | Split vertical | `Ctrl+A` depois `\|` | | Split horizontal | `Ctrl+A` depois `-` |  ## 🔧 Comandos Manuais (avançado)  ```bash # Ver processos rodando ps aux | grep python ps aux | grep node tmux ls  # Listar sessões tmux  # Verificar portas ocupadas lsof -i :5000 lsof -i :8081  # Matar processos manualmente pkill -9 python3 pkill -9 node tmux kill-session -t skills-eye  # Limpar cache manualmente cd ~/projetos/Skills-Eye/backend find . -type d -name \"__pycache__\" -exec rm -rf {} +  cd ~/projetos/Skills-Eye/frontend rm -rf node_modules/.vite dist .vite ```  ## 📊 Comparação de Comandos  | Preciso... | Comando | |-----------|---------| | Iniciar projeto | `eye-start` | | Parar projeto | `eye-stop` | | Reiniciar com cache limpo | `eye-restart` | | Ver logs | `skills` | | Desconectar logs (deixar rodando) | `Ctrl+A` depois `D` | | Navegar entre Backend/Frontend | `Alt + ← →` |  ## 🐛 Troubleshooting  ### \"Aplicação já está rodando\" ```bash eye-stop eye-start ```  ### \"Porta 5000/8081 ocupada\" ```bash eye-stop    # Já limpa as portas eye-start ```  ### \"tmux session not found\" ```bash eye-start   # Cria nova sessão ```  ### Cache não limpa ```bash eye-stop    # Para e limpa # Verifica manualmente: cd ~/projetos/Skills-Eye/backend find . -name \"__pycache__\" -type d  # Deve estar vazio cd ~/projetos/Skills-Eye/frontend ls -la node_modules/.vite  # Deve dar erro (não existe) ```  ## 💡 Dicas  1. **Use `eye-restart`** quando em dúvida - é o mais seguro 2. **`Alt + Setas`** para navegar - não precisa de Ctrl+A 3. **Mouse funciona** no tmux - clique e redimensione à vontade 4. **`Ctrl+A D`** para deixar rodando e voltar ao terminal 5. **`eye-stop`** antes de pull/merge do Git  ---  **Aliases disponíveis:** - `eye-stop` → ~/projetos/Skills-Eye/stop-app.sh - `eye-start` → ~/projetos/Skills-Eye/start-app.sh - `eye-restart` → ~/projetos/Skills-Eye/restart-app.sh - `skills` → tmux attach -t skills-eye - `restart` → (legado, usa eye-restart) EOF echo \"✓ COMANDOS_RAPIDOS.md criado\""
adriano+    6276  0.0  0.0   4088  1920 pts/7    S+   10:15   0:00 grep python
adriano+    5732  1.1 25.7 25766296 1084148 pts/3 Sl+ 10:03   0:08 node /home/adrianofante/projetos/Skills-Eye/frontend/node_modules/.bin/vite --port 8081
adriano+    5849  0.0  0.0   4756  3328 pts/4    Ss+  10:05   0:00 /bin/bash -c bash -c "cd ~/projetos/Skills-Eye && cat > GUIA_WSL.md << 'EOF' # 🚀 Skills-Eye - Guia Rápido WSL  ## ⚡ Comandos Principais  ```bash restart    # Reinicia app com limpeza de cache skills     # Conecta no tmux ```  ## 🎯 Atalhos do tmux  ### Navegação (FÁCIL\!) - `Alt + ← →` - Navegar entre Backend/Frontend (SEM precisar de Ctrl+A\!) - `Alt + ↑ ↓` - Navegar vertical se tiver mais painéis  ### Comandos (Ctrl+A depois...) - `Ctrl+A` depois `D` - Desconectar (deixa rodando) - `Ctrl+A` depois `X` - Fechar painel atual - `Ctrl+A` depois `R` - Recarregar config tmux - `Ctrl+A` depois `|` - Split vertical - `Ctrl+A` depois `-` - Split horizontal  ### Mouse 🖱️ - ✅ Clicar para trocar de painel - ✅ Arrastar borda para redimensionar - ✅ Scroll com roda do mouse  ## 📊 URLs  - Backend: http://localhost:5000 - Frontend: http://localhost:8081 - API Docs: http://localhost:5000/docs  ## 🔧 Comandos de Manutenção  ```bash # Backend (manual) cd ~/projetos/Skills-Eye/backend source venv/bin/activate python app.py  # Frontend (manual) cd ~/projetos/Skills-Eye/frontend npm run dev  # Atualizar dependências Python cd ~/projetos/Skills-Eye/backend source venv/bin/activate pip install -r requirements.txt  # Atualizar dependências Node cd ~/projetos/Skills-Eye/frontend npm install  # Ver processos rodando ps aux | grep python ps aux | grep node  # Matar processos manualmente pkill -9 python3 pkill -9 node ```  ## 📝 Git  ```bash cd ~/projetos/Skills-Eye  # Status git status  # Commit git add . git commit -m \"feat: sua mensagem aqui\"  # Push git push  # Pull git pull ```  ## 🐛 Troubleshooting  ### Porta 5000 ocupada ```bash lsof -ti:5000 | xargs kill -9 ```  ### Porta 8081 ocupada ```bash lsof -ti:8081 | xargs kill -9 ```  ### Limpar TUDO e recomeçar ```bash cd ~/projetos/Skills-Eye pkill -9 python3 pkill -9 node tmux kill-session -t skills-eye ./restart-app.sh ```  ## 💡 Dicas  1. **Sempre use `restart`** para garantir cache limpo 2. **Use `Alt + Setas`** para navegar - é mais rápido\! 3. **Mouse funciona\!** Clique e arraste à vontade 4. **`Ctrl+A D`** para desconectar sem parar a app 5. **`skills`** para voltar pro tmux  ## 📚 Comparativo Windows vs WSL  | Ação | Windows | WSL | |------|---------|-----| | Reiniciar | `restart-app.bat` | `restart` | | Ver logs | Janelas separadas | `skills` (tmux) | | Performance | Lento (~20s SSH) | Rápido (~2-3s) | | Cache | Múltiplas pastas | `__pycache__` + `.vite` |  ---  **Dúvidas?** Consulte: `~/projetos/Skills-Eye/MIGRACAO_WSL_PLANO_COMPLETO.md` EOF echo \"✓ Guia criado em ~/projetos/Skills-Eye/GUIA_WSL.md\""
adriano+    5865  0.0  0.0   4888  2092 pts/4    S+   10:05   0:00 /bin/bash -c bash -c "cd ~/projetos/Skills-Eye && cat > GUIA_WSL.md << 'EOF' # 🚀 Skills-Eye - Guia Rápido WSL  ## ⚡ Comandos Principais  ```bash restart    # Reinicia app com limpeza de cache skills     # Conecta no tmux ```  ## 🎯 Atalhos do tmux  ### Navegação (FÁCIL\!) - `Alt + ← →` - Navegar entre Backend/Frontend (SEM precisar de Ctrl+A\!) - `Alt + ↑ ↓` - Navegar vertical se tiver mais painéis  ### Comandos (Ctrl+A depois...) - `Ctrl+A` depois `D` - Desconectar (deixa rodando) - `Ctrl+A` depois `X` - Fechar painel atual - `Ctrl+A` depois `R` - Recarregar config tmux - `Ctrl+A` depois `|` - Split vertical - `Ctrl+A` depois `-` - Split horizontal  ### Mouse 🖱️ - ✅ Clicar para trocar de painel - ✅ Arrastar borda para redimensionar - ✅ Scroll com roda do mouse  ## 📊 URLs  - Backend: http://localhost:5000 - Frontend: http://localhost:8081 - API Docs: http://localhost:5000/docs  ## 🔧 Comandos de Manutenção  ```bash # Backend (manual) cd ~/projetos/Skills-Eye/backend source venv/bin/activate python app.py  # Frontend (manual) cd ~/projetos/Skills-Eye/frontend npm run dev  # Atualizar dependências Python cd ~/projetos/Skills-Eye/backend source venv/bin/activate pip install -r requirements.txt  # Atualizar dependências Node cd ~/projetos/Skills-Eye/frontend npm install  # Ver processos rodando ps aux | grep python ps aux | grep node  # Matar processos manualmente pkill -9 python3 pkill -9 node ```  ## 📝 Git  ```bash cd ~/projetos/Skills-Eye  # Status git status  # Commit git add . git commit -m \"feat: sua mensagem aqui\"  # Push git push  # Pull git pull ```  ## 🐛 Troubleshooting  ### Porta 5000 ocupada ```bash lsof -ti:5000 | xargs kill -9 ```  ### Porta 8081 ocupada ```bash lsof -ti:8081 | xargs kill -9 ```  ### Limpar TUDO e recomeçar ```bash cd ~/projetos/Skills-Eye pkill -9 python3 pkill -9 node tmux kill-session -t skills-eye ./restart-app.sh ```  ## 💡 Dicas  1. **Sempre use `restart`** para garantir cache limpo 2. **Use `Alt + Setas`** para navegar - é mais rápido\! 3. **Mouse funciona\!** Clique e arraste à vontade 4. **`Ctrl+A D`** para desconectar sem parar a app 5. **`skills`** para voltar pro tmux  ## 📚 Comparativo Windows vs WSL  | Ação | Windows | WSL | |------|---------|-----| | Reiniciar | `restart-app.bat` | `restart` | | Ver logs | Janelas separadas | `skills` (tmux) | | Performance | Lento (~20s SSH) | Rápido (~2-3s) | | Cache | Múltiplas pastas | `__pycache__` + `.vite` |  ---  **Dúvidas?** Consulte: `~/projetos/Skills-Eye/MIGRACAO_WSL_PLANO_COMPLETO.md` EOF echo \"✓ Guia criado em ~/projetos/Skills-Eye/GUIA_WSL.md\""
adriano+    5903  0.0  2.2 24406684 94452 pts/4  Sl+  10:05   0:00 node /home/adrianofante/projetos/Skills-Eye/frontend/node_modules/.bin/vite --port 8081
adriano+    6247  0.0  0.0   4888  3328 pts/7    Ss+  10:15   0:00 /bin/bash -c bash -c "cd ~/projetos/Skills-Eye && cat > COMANDOS_RAPIDOS.md << 'EOF' # 🚀 Skills-Eye - Comandos Rápidos  ## ⚡ Comandos Principais  ```bash eye-stop      # Para aplicação e limpa cache (SEM reiniciar) eye-start     # Inicia aplicação no tmux eye-restart   # Reinicia com limpeza total de cache skills        # Conecta no tmux para ver logs ```  ## 📋 Detalhamento dos Comandos  ### 🛑 eye-stop **O que faz:** - Mata TODOS os processos Python/Node relacionados (pkill -9) - Encerra sessão tmux se existir - Limpa cache Python (__pycache__, *.pyc, *.egg-info) - Limpa cache Vite (.vite, dist, node_modules/.vite, .parcel-cache) - **NÃO reinicia** a aplicação  **Use quando:** - Terminou de trabalhar no projeto - Precisa liberar portas 5000/8081 - Quer garantir que NADA está rodando  ### ▶️ eye-start **O que faz:** - Verifica se já está rodando (evita duplicação) - Verifica se portas 5000/8081 estão livres - Cria sessão tmux \"skills-eye\" - Inicia Backend (painel esquerdo) + Frontend (painel direito) - Mostra URLs de acesso  **Use quando:** - Iniciar trabalho no projeto - Após usar eye-stop - Primeira vez após boot do PC  ### 🔄 eye-restart **O que faz:** - Executa eye-stop (para tudo e limpa cache) - Aguarda 2 segundos - Executa eye-start (reinicia tudo) - Mostra atalhos do tmux  **Use quando:** - Fez mudanças que exigem restart - Cache está causando problemas - Quer garantir ambiente limpo  ### 👁️ skills **O que faz:** - Conecta na sessão tmux existente - Mostra logs do Backend e Frontend lado a lado  **Use quando:** - Quer ver logs em tempo real - Precisa debugar algo - Quer verificar se está rodando  ## 🎯 Fluxo de Trabalho Típico  ### Início do Dia ```bash eye-start    # Inicia tudo skills       # Vê se subiu OK # Ctrl+A D   # Desconecta (deixa rodando) ```  ### Durante Desenvolvimento ```bash # Trabalha normalmente... # Se precisar ver logs: skills       # Conecta no tmux # Alt + ←→   # Navega entre painéis # Ctrl+A D   # Desconecta  # Se fez mudanças grandes: eye-restart  # Reinicia com cache limpo ```  ### Fim do Dia ```bash eye-stop     # Para tudo e limpa cache ```  ## ⌨️ Atalhos do tmux (quando conectado com skills)  | Ação | Atalho | |------|--------| | Navegar painéis | `Alt + ← →` | | Desconectar | `Ctrl+A` depois `D` | | Fechar painel | `Ctrl+A` depois `X` | | Recarregar config | `Ctrl+A` depois `R` | | Split vertical | `Ctrl+A` depois `\|` | | Split horizontal | `Ctrl+A` depois `-` |  ## 🔧 Comandos Manuais (avançado)  ```bash # Ver processos rodando ps aux | grep python ps aux | grep node tmux ls  # Listar sessões tmux  # Verificar portas ocupadas lsof -i :5000 lsof -i :8081  # Matar processos manualmente pkill -9 python3 pkill -9 node tmux kill-session -t skills-eye  # Limpar cache manualmente cd ~/projetos/Skills-Eye/backend find . -type d -name \"__pycache__\" -exec rm -rf {} +  cd ~/projetos/Skills-Eye/frontend rm -rf node_modules/.vite dist .vite ```  ## 📊 Comparação de Comandos  | Preciso... | Comando | |-----------|---------| | Iniciar projeto | `eye-start` | | Parar projeto | `eye-stop` | | Reiniciar com cache limpo | `eye-restart` | | Ver logs | `skills` | | Desconectar logs (deixar rodando) | `Ctrl+A` depois `D` | | Navegar entre Backend/Frontend | `Alt + ← →` |  ## 🐛 Troubleshooting  ### \"Aplicação já está rodando\" ```bash eye-stop eye-start ```  ### \"Porta 5000/8081 ocupada\" ```bash eye-stop    # Já limpa as portas eye-start ```  ### \"tmux session not found\" ```bash eye-start   # Cria nova sessão ```  ### Cache não limpa ```bash eye-stop    # Para e limpa # Verifica manualmente: cd ~/projetos/Skills-Eye/backend find . -name \"__pycache__\" -type d  # Deve estar vazio cd ~/projetos/Skills-Eye/frontend ls -la node_modules/.vite  # Deve dar erro (não existe) ```  ## 💡 Dicas  1. **Use `eye-restart`** quando em dúvida - é o mais seguro 2. **`Alt + Setas`** para navegar - não precisa de Ctrl+A 3. **Mouse funciona** no tmux - clique e redimensione à vontade 4. **`Ctrl+A D`** para deixar rodando e voltar ao terminal 5. **`eye-stop`** antes de pull/merge do Git  ---  **Aliases disponíveis:** - `eye-stop` → ~/projetos/Skills-Eye/stop-app.sh - `eye-start` → ~/projetos/Skills-Eye/start-app.sh - `eye-restart` → ~/projetos/Skills-Eye/restart-app.sh - `skills` → tmux attach -t skills-eye - `restart` → (legado, usa eye-restart) EOF echo \"✓ COMANDOS_RAPIDOS.md criado\""
adriano+    6273  0.0  0.0   4756  1732 pts/7    S+   10:15   0:00 /bin/bash -c bash -c "cd ~/projetos/Skills-Eye && cat > COMANDOS_RAPIDOS.md << 'EOF' # 🚀 Skills-Eye - Comandos Rápidos  ## ⚡ Comandos Principais  ```bash eye-stop      # Para aplicação e limpa cache (SEM reiniciar) eye-start     # Inicia aplicação no tmux eye-restart   # Reinicia com limpeza total de cache skills        # Conecta no tmux para ver logs ```  ## 📋 Detalhamento dos Comandos  ### 🛑 eye-stop **O que faz:** - Mata TODOS os processos Python/Node relacionados (pkill -9) - Encerra sessão tmux se existir - Limpa cache Python (__pycache__, *.pyc, *.egg-info) - Limpa cache Vite (.vite, dist, node_modules/.vite, .parcel-cache) - **NÃO reinicia** a aplicação  **Use quando:** - Terminou de trabalhar no projeto - Precisa liberar portas 5000/8081 - Quer garantir que NADA está rodando  ### ▶️ eye-start **O que faz:** - Verifica se já está rodando (evita duplicação) - Verifica se portas 5000/8081 estão livres - Cria sessão tmux \"skills-eye\" - Inicia Backend (painel esquerdo) + Frontend (painel direito) - Mostra URLs de acesso  **Use quando:** - Iniciar trabalho no projeto - Após usar eye-stop - Primeira vez após boot do PC  ### 🔄 eye-restart **O que faz:** - Executa eye-stop (para tudo e limpa cache) - Aguarda 2 segundos - Executa eye-start (reinicia tudo) - Mostra atalhos do tmux  **Use quando:** - Fez mudanças que exigem restart - Cache está causando problemas - Quer garantir ambiente limpo  ### 👁️ skills **O que faz:** - Conecta na sessão tmux existente - Mostra logs do Backend e Frontend lado a lado  **Use quando:** - Quer ver logs em tempo real - Precisa debugar algo - Quer verificar se está rodando  ## 🎯 Fluxo de Trabalho Típico  ### Início do Dia ```bash eye-start    # Inicia tudo skills       # Vê se subiu OK # Ctrl+A D   # Desconecta (deixa rodando) ```  ### Durante Desenvolvimento ```bash # Trabalha normalmente... # Se precisar ver logs: skills       # Conecta no tmux # Alt + ←→   # Navega entre painéis # Ctrl+A D   # Desconecta  # Se fez mudanças grandes: eye-restart  # Reinicia com cache limpo ```  ### Fim do Dia ```bash eye-stop     # Para tudo e limpa cache ```  ## ⌨️ Atalhos do tmux (quando conectado com skills)  | Ação | Atalho | |------|--------| | Navegar painéis | `Alt + ← →` | | Desconectar | `Ctrl+A` depois `D` | | Fechar painel | `Ctrl+A` depois `X` | | Recarregar config | `Ctrl+A` depois `R` | | Split vertical | `Ctrl+A` depois `\|` | | Split horizontal | `Ctrl+A` depois `-` |  ## 🔧 Comandos Manuais (avançado)  ```bash # Ver processos rodando ps aux | grep python ps aux | grep node tmux ls  # Listar sessões tmux  # Verificar portas ocupadas lsof -i :5000 lsof -i :8081  # Matar processos manualmente pkill -9 python3 pkill -9 node tmux kill-session -t skills-eye  # Limpar cache manualmente cd ~/projetos/Skills-Eye/backend find . -type d -name \"__pycache__\" -exec rm -rf {} +  cd ~/projetos/Skills-Eye/frontend rm -rf node_modules/.vite dist .vite ```  ## 📊 Comparação de Comandos  | Preciso... | Comando | |-----------|---------| | Iniciar projeto | `eye-start` | | Parar projeto | `eye-stop` | | Reiniciar com cache limpo | `eye-restart` | | Ver logs | `skills` | | Desconectar logs (deixar rodando) | `Ctrl+A` depois `D` | | Navegar entre Backend/Frontend | `Alt + ← →` |  ## 🐛 Troubleshooting  ### \"Aplicação já está rodando\" ```bash eye-stop eye-start ```  ### \"Porta 5000/8081 ocupada\" ```bash eye-stop    # Já limpa as portas eye-start ```  ### \"tmux session not found\" ```bash eye-start   # Cria nova sessão ```  ### Cache não limpa ```bash eye-stop    # Para e limpa # Verifica manualmente: cd ~/projetos/Skills-Eye/backend find . -name \"__pycache__\" -type d  # Deve estar vazio cd ~/projetos/Skills-Eye/frontend ls -la node_modules/.vite  # Deve dar erro (não existe) ```  ## 💡 Dicas  1. **Use `eye-restart`** quando em dúvida - é o mais seguro 2. **`Alt + Setas`** para navegar - não precisa de Ctrl+A 3. **Mouse funciona** no tmux - clique e redimensione à vontade 4. **`Ctrl+A D`** para deixar rodando e voltar ao terminal 5. **`eye-stop`** antes de pull/merge do Git  ---  **Aliases disponíveis:** - `eye-stop` → ~/projetos/Skills-Eye/stop-app.sh - `eye-start` → ~/projetos/Skills-Eye/start-app.sh - `eye-restart` → ~/projetos/Skills-Eye/restart-app.sh - `skills` → tmux attach -t skills-eye - `restart` → (legado, usa eye-restart) EOF echo \"✓ COMANDOS_RAPIDOS.md criado\""
adriano+    6278  0.0  0.0   4088  1920 pts/7    S+   10:15   0:00 grep node
skills-eye: 1 windows (created Tue Nov 11 10:03:20 2025)
COMMAND  PID         USER   FD   TYPE DEVICE SIZE/OFF NODE NAME
python  5715 adrianofante   13u  IPv4  24194      0t0  TCP *:5000 (LISTEN)
COMMAND  PID         USER   FD   TYPE DEVICE SIZE/OFF NODE NAME
node    5732 adrianofante   24u  IPv6  24970      0t0  TCP *:tproxy (LISTEN)
node    5732 adrianofante   32u  IPv6  20346      0t0  TCP ip6-localhost:tproxy->ip6-localhost:43350 (ESTABLISHED)
node    5732 adrianofante   33u  IPv6  24977      0t0  TCP 172.19.116.74:tproxy->172.19.112.1:19722 (ESTABLISHED)
node    5732 adrianofante   34u  IPv6  21399      0t0  TCP ip6-localhost:tproxy->ip6-localhost:43364 (ESTABLISHED)

## 📊 Comparação de Comandos

| Preciso... | Comando |
|-----------|---------|
| Iniciar projeto |  |
| Parar projeto |  |
| Reiniciar com cache limpo |  |
| Ver logs |  |
| Desconectar logs (deixar rodando) |  depois  |
| Navegar entre Backend/Frontend |  |

## 🐛 Troubleshooting

### "Aplicação já está rodando"


### "Porta 5000/8081 ocupada"


### "tmux session not found"


### Cache não limpa
./venv/lib/python3.12/site-packages/pip/_vendor/rich/__pycache__
./venv/lib/python3.12/site-packages/pip/_vendor/certifi/__pycache__
./venv/lib/python3.12/site-packages/pip/_vendor/pygments/__pycache__
./venv/lib/python3.12/site-packages/pip/_vendor/pygments/filters/__pycache__
./venv/lib/python3.12/site-packages/pip/_vendor/pygments/styles/__pycache__
./venv/lib/python3.12/site-packages/pip/_vendor/pygments/lexers/__pycache__
./venv/lib/python3.12/site-packages/pip/_vendor/distro/__pycache__
./venv/lib/python3.12/site-packages/pip/_vendor/pyproject_hooks/__pycache__
./venv/lib/python3.12/site-packages/pip/_vendor/pyproject_hooks/_in_process/__pycache__
./venv/lib/python3.12/site-packages/pip/_vendor/requests/__pycache__
./venv/lib/python3.12/site-packages/pip/_vendor/distlib/__pycache__
./venv/lib/python3.12/site-packages/pip/_vendor/packaging/__pycache__
./venv/lib/python3.12/site-packages/pip/_vendor/cachecontrol/__pycache__
./venv/lib/python3.12/site-packages/pip/_vendor/cachecontrol/caches/__pycache__
./venv/lib/python3.12/site-packages/pip/_vendor/resolvelib/__pycache__
./venv/lib/python3.12/site-packages/pip/_vendor/resolvelib/resolvers/__pycache__
./venv/lib/python3.12/site-packages/pip/_vendor/idna/__pycache__
./venv/lib/python3.12/site-packages/pip/_vendor/truststore/__pycache__
./venv/lib/python3.12/site-packages/pip/_vendor/dependency_groups/__pycache__
./venv/lib/python3.12/site-packages/pip/_vendor/urllib3/__pycache__
./venv/lib/python3.12/site-packages/pip/_vendor/urllib3/contrib/__pycache__
./venv/lib/python3.12/site-packages/pip/_vendor/urllib3/util/__pycache__
./venv/lib/python3.12/site-packages/pip/_vendor/urllib3/packages/__pycache__
./venv/lib/python3.12/site-packages/pip/_vendor/msgpack/__pycache__
./venv/lib/python3.12/site-packages/pip/_vendor/platformdirs/__pycache__
./venv/lib/python3.12/site-packages/pip/_internal/locations/__pycache__
./venv/lib/python3.12/site-packages/pip/_internal/__pycache__
./venv/lib/python3.12/site-packages/pip/_internal/utils/__pycache__
./venv/lib/python3.12/site-packages/pip/_internal/cli/__pycache__
./venv/lib/python3.12/site-packages/pip/_internal/resolution/__pycache__
./venv/lib/python3.12/site-packages/pip/_internal/resolution/resolvelib/__pycache__
./venv/lib/python3.12/site-packages/pip/_internal/commands/__pycache__
./venv/lib/python3.12/site-packages/pip/_internal/operations/__pycache__
./venv/lib/python3.12/site-packages/pip/_internal/operations/build/__pycache__
./venv/lib/python3.12/site-packages/pip/_internal/operations/install/__pycache__
./venv/lib/python3.12/site-packages/pip/_internal/req/__pycache__
./venv/lib/python3.12/site-packages/pip/_internal/index/__pycache__
./venv/lib/python3.12/site-packages/pip/_internal/models/__pycache__
./venv/lib/python3.12/site-packages/pip/_internal/network/__pycache__
./venv/lib/python3.12/site-packages/pip/_internal/metadata/__pycache__
./venv/lib/python3.12/site-packages/pip/_internal/metadata/importlib/__pycache__
./venv/lib/python3.12/site-packages/pip/_internal/vcs/__pycache__
./venv/lib/python3.12/site-packages/pip/_internal/distributions/__pycache__

## 💡 Dicas

1. **Use ** quando em dúvida - é o mais seguro
2. **** para navegar - não precisa de Ctrl+A
3. **Mouse funciona** no tmux - clique e redimensione à vontade
4. **** para deixar rodando e voltar ao terminal
5. **** antes de pull/merge do Git

---

**Aliases disponíveis:**
-  → ~/projetos/Skills-Eye/stop-app.sh
-  → ~/projetos/Skills-Eye/start-app.sh
-  → ~/projetos/Skills-Eye/restart-app.sh
-  → tmux attach -t skills-eye
-  → (legado, usa eye-restart)
