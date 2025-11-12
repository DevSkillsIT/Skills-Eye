# GUIA DE USO - WSL + TMUX

**Projeto:** Skills Eye - Consul Manager
**Data:** 2025-11-11
**Ambiente:** WSL Ubuntu

---

## 📋 O QUE É TMUX E POR QUE USAMOS?

**tmux** (Terminal Multiplexer) é uma ferramenta que permite:
- ✅ Executar múltiplos processos em **background** (mesmo após fechar o terminal)
- ✅ Manter aplicações rodando **persistentemente**
- ✅ Reconectar a sessões em execução

### Por que o VSCode desconecta?

**Isso é NORMAL e ESPERADO!** 🎯

Quando você executa `./start-app.sh`, o script:
1. Cria uma sessão tmux chamada `skills-eye`
2. Inicia backend e frontend **dentro do tmux** (em background)
3. **Desanexa do terminal atual** (por isso o VSCode desconecta)

Isso **NÃO é um problema** - é o comportamento correto do tmux! As aplicações continuam rodando em background mesmo após a desconexão.

---

## 🚀 SCRIPTS DISPONÍVEIS

### 1. Iniciar Aplicação
```bash
./start-app.sh
```
- Inicia backend (porta 5000) e frontend (porta 8081)
- Cria sessão tmux `skills-eye`
- Terminal desconecta (NORMAL!)

### 2. Parar Aplicação
```bash
./stop-app.sh
```
- Para backend e frontend
- Mata sessão tmux `skills-eye`

### 3. Reiniciar Aplicação
```bash
./restart-app.sh
```
- Para tudo, limpa cache, inicia novamente
- Útil após mudanças no código

---

## 🔧 COMANDOS TMUX ÚTEIS

### Ver Sessões Ativas
```bash
tmux ls
```
Saída esperada:
```
skills-eye: 2 windows (created Sun Nov 11 10:30:00 2025)
```

### Conectar à Sessão (Ver Logs em Tempo Real)
```bash
tmux attach -t skills-eye
```
Agora você vê os logs do backend e frontend!

### Navegar Entre Janelas (dentro do tmux)
- **Ctrl+B, 0** - Ir para janela 0 (backend)
- **Ctrl+B, 1** - Ir para janela 1 (frontend)
- **Ctrl+B, n** - Próxima janela (next)
- **Ctrl+B, p** - Janela anterior (previous)

### Desconectar sem Parar (detach)
```bash
# Dentro do tmux, pressione:
Ctrl+B, d
```
Aplicações continuam rodando em background!

### Matar Sessão
```bash
tmux kill-session -t skills-eye
```
Equivalente a `./stop-app.sh`

---

## ⚡ BASH ALIASES (ATALHOS RECOMENDADOS)

Adicione ao seu `~/.bashrc` para facilitar:

```bash
# Skills Eye - Atalhos tmux
alias eye-start='cd /home/adrianofante/projetos/Skills-Eye && ./start-app.sh'
alias eye-stop='cd /home/adrianofante/projetos/Skills-Eye && ./stop-app.sh'
alias eye-restart='cd /home/adrianofante/projetos/Skills-Eye && ./restart-app.sh'
alias eye-logs='tmux attach -t skills-eye'
alias eye-status='tmux ls | grep skills-eye && echo "✅ Rodando" || echo "❌ Parado"'
alias skills='cd /home/adrianofante/projetos/Skills-Eye'
```

**Aplicar aliases:**
```bash
source ~/.bashrc
```

**Agora você pode usar:**
```bash
eye-start       # Inicia aplicação
eye-logs        # Ver logs em tempo real
eye-status      # Verificar se está rodando
eye-stop        # Parar aplicação
skills          # Ir para diretório do projeto
```

---

## 🔍 TROUBLESHOOTING

### 1. "Terminal desconecta ao rodar start-app.sh"
✅ **COMPORTAMENTO NORMAL!** Aplicação roda em background via tmux.

**Verificar se está rodando:**
```bash
tmux ls
```

**Ver logs:**
```bash
tmux attach -t skills-eye
```

---

### 2. "Não consigo ver os logs"
**Solução:**
```bash
# Conectar à sessão tmux
tmux attach -t skills-eye

# Navegar entre backend (janela 0) e frontend (janela 1)
# Ctrl+B, 0  →  Backend
# Ctrl+B, 1  →  Frontend
```

---

### 3. "Session not found: skills-eye"
Significa que a aplicação **não está rodando**.

**Solução:**
```bash
./start-app.sh
```

---

### 4. "Address already in use (porta 5000 ou 8081)"
Algum processo ainda está usando a porta.

**Solução:**
```bash
# Parar aplicação
./stop-app.sh

# Se não resolver, matar processos manualmente:
pkill -f "python.*app.py"
pkill -f "npm run dev"

# Verificar portas:
lsof -i :5000
lsof -i :8081

# Matar processo específico (se necessário):
kill -9 <PID>
```

---

### 5. "Quero rodar SEM tmux (para ver logs direto no VSCode)"
**Opção A: Terminal 1 (Backend)**
```bash
cd backend
source venv/bin/activate
python app.py
```

**Opção B: Terminal 2 (Frontend)**
```bash
cd frontend
npm run dev
```

**Vantagem:** Logs direto no VSCode
**Desvantagem:** Precisa manter 2 terminais abertos

---

### 6. "Como saber se backend/frontend estão respondendo?"
**Testar Backend:**
```bash
curl http://localhost:5000/health
```
Resposta esperada:
```json
{"healthy": true, "message": "Consul Manager API is healthy"}
```

**Testar Frontend:**
```bash
curl http://localhost:8081
```
Deve retornar HTML da página.

**Ou abrir no navegador:**
- Backend: http://localhost:5000/docs (Swagger UI)
- Frontend: http://localhost:8081

---

## 📁 ESTRUTURA DO PROJETO

```
Skills-Eye/
├── backend/
│   ├── app.py              # ← Aplicação FastAPI (porta 5000)
│   ├── venv/               # ← Ambiente virtual Python
│   └── requirements.txt
├── frontend/
│   ├── package.json
│   └── src/
├── start-app.sh            # ← Inicia backend + frontend (tmux)
├── stop-app.sh             # ← Para tudo
├── restart-app.sh          # ← Reinicia tudo
└── GUIA_WSL.md             # ← Este arquivo
```

---

## 🎯 WORKFLOW RECOMENDADO

### Desenvolvimento Diário

**1. Iniciar aplicação:**
```bash
cd /home/adrianofante/projetos/Skills-Eye
./start-app.sh
```
Terminal desconecta → **NORMAL!**

**2. Verificar se está rodando:**
```bash
# Opção A: Checar sessão tmux
tmux ls

# Opção B: Testar endpoints
curl http://localhost:5000/health
```

**3. Ver logs em tempo real (quando necessário):**
```bash
tmux attach -t skills-eye
# Ctrl+B, 0 → Backend logs
# Ctrl+B, 1 → Frontend logs
# Ctrl+B, d → Desconectar (sem parar)
```

**4. Após mudanças no código:**
```bash
./restart-app.sh
```

**5. Fim do dia:**
```bash
./stop-app.sh
```

---

### Desenvolvimento com Logs no VSCode (SEM tmux) - RECOMENDADO

**⚠️ IMPORTANTE**: Se o VSCode está desconectando ao usar os scripts com tmux, use esta opção!

**Terminal 1 (Backend):**
```bash
./start-backend.sh
```
OU manualmente:
```bash
cd backend
source venv/bin/activate
python app.py
```

**Terminal 2 (Frontend):**
```bash
./start-frontend.sh
```
OU manualmente:
```bash
cd frontend
npm run dev
```

**Para parar**: `Ctrl+C` em cada terminal.

**Vantagens:**
- ✅ Logs visíveis direto no VSCode
- ✅ Sem desconexão do terminal
- ✅ Fácil de debugar

**Desvantagens:**
- ❌ Precisa manter 2 terminais abertos
- ❌ Para ao fechar o VSCode

---

## 🔐 VARIÁVEIS DE AMBIENTE

O backend precisa do arquivo `backend/.env`:

```bash
CONSUL_HOST=172.16.1.26
CONSUL_PORT=8500
CONSUL_TOKEN=8382a112-81e0-cd6d-2b92-8565925a0675
PROMETHEUS_USER=prometheus
PROMETHEUS_PASSWORD=***
PROMETHEUS_CONFIG_HOSTS=172.16.1.26:5522/root/***
```

**NUNCA COMMITAR .env NO GIT!**

---

## 📊 PORTAS UTILIZADAS

| Serviço | Porta | Descrição |
|---------|-------|-----------|
| Backend API | 5000 | FastAPI + Swagger UI |
| Frontend Dev | 8081 | Vite dev server |
| Consul | 8500 | Consul UI/API |
| Prometheus | 9090 | Prometheus UI |
| Grafana | 3000 | Grafana UI |
| Blackbox Exporter | 9115 | Blackbox metrics |
| AlertManager | 9093 | AlertManager UI |

---

## 📚 REFERÊNCIAS

- **tmux Cheat Sheet:** https://tmuxcheatsheet.com/
- **Documentação tmux:** `man tmux`
- **Skills Eye Docs:** `CLAUDE.md`, `IMPLEMENTACAO_COMPLETA.md`

---

## 💡 DICAS FINAIS

1. **Use os aliases** - Muito mais rápido que comandos completos
2. **tmux attach** - Use quando precisar debugar logs
3. **Ctrl+B, d** - Sempre desconecte (não feche), para não matar sessão
4. **restart-app.sh** - Use após mudanças no código (limpa cache)
5. **VSCode desconecta** - É normal! Aplicação continua rodando

---

**Criado por:** Claude Code (Anthropic)
**Atualizado:** 2025-11-11
