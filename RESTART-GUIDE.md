# 🔄 Guia de Restart da Aplicação

## Scripts Disponíveis

### 1. **restart-app.bat** (Windows Batch)
```cmd
restart-app.bat
```
- Mais compatível com Windows antigos
- Abre janelas CMD separadas para Backend e Frontend
- Colorização básica

### 2. **restart-app.ps1** (PowerShell)
```powershell
.\restart-app.ps1
```
- Recomendado para Windows 10+
- Interface mais moderna com cores
- Melhor feedback de progresso

---

## O que os Scripts Fazem

### 🛑 Fase 1: Encerramento
1. **Para todos os processos Node.js** (Frontend)
2. **Para todos os processos Python** (Backend)

### 🧹 Fase 2: Limpeza de Cache
3. **Backend Python:**
   - `backend/__pycache__/`
   - `backend/api/__pycache__/`
   - `backend/core/__pycache__/`
   - `backend/core/installers/__pycache__/`

4. **Frontend Node:**
   - `frontend/node_modules/.vite/`
   - `frontend/dist/`

### ⏸️ Fase 3: Aguardo
5. **Espera 3 segundos** para garantir que tudo foi encerrado

### 🚀 Fase 4: Reinício
6. **Inicia Backend** em nova janela
   - Porta: `5000`
   - URL: http://localhost:5000

7. **Inicia Frontend** em nova janela
   - Porta: `8081`
   - URL: http://localhost:8081

---

## Quando Usar

### ✅ Use os scripts quando:
- Aplicação está com comportamento estranho
- Cache parece corrompido
- Após atualizar código do backend/frontend
- Após trocar de branch no Git
- Processos Node/Python travados

### ⚠️ NÃO use quando:
- Aplicação está funcionando normalmente
- Apenas quer recarregar dados (use o botão "Recarregar" na interface)

---

## Botão Recarregar na Interface

O botão **"Recarregar"** na página Prometheus Config agora:

1. ✅ Limpa o cache do backend automaticamente
2. ✅ Recarrega arquivos do servidor
3. ✅ Recarrega jobs/configurações
4. ✅ Mostra feedback visual

**Use este botão** quando restaurar um backup ou fazer alterações manuais no servidor!

---

## Troubleshooting

### Problema: "Script não executa"
**Solução:**
```powershell
# PowerShell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
.\restart-app.ps1
```

### Problema: "Porta 5000 ou 8081 em uso"
**Solução:**
```cmd
REM Ver o que está usando a porta
netstat -ano | findstr "5000"
netstat -ano | findstr "8081"

REM Matar processo por PID
taskkill /F /PID <PID>
```

### Problema: "Backend não inicia"
**Verificações:**
1. Python está instalado? `python --version`
2. Dependências instaladas? `cd backend && pip install -r requirements.txt`
3. Arquivo `.env` existe em `backend/`?

### Problema: "Frontend não inicia"
**Verificações:**
1. Node.js está instalado? `node --version`
2. Dependências instaladas? `cd frontend && npm install`

---

## Monitoramento

Após executar o script, você verá **2 janelas**:

### Janela 1: Backend (Python)
```
>> Iniciando Consul Manager API...
>> Sistema de auditoria inicializado
INFO: Application startup complete.
INFO: Uvicorn running on http://0.0.0.0:5000
```

### Janela 2: Frontend (Vite)
```
VITE v5.x.x ready in XXX ms

➜  Local:   http://localhost:8081/
➜  Network: http://192.168.x.x:8081/
```

---

## Acesso Rápido

Após o restart:
- **Frontend:** http://localhost:8081
- **Backend API:** http://localhost:5000
- **API Docs:** http://localhost:5000/docs

---

## Suporte

Em caso de problemas persistentes:
1. Verifique os logs nas janelas do Backend/Frontend
2. Verifique se não há firewall bloqueando as portas
3. Execute o script de restart novamente
4. Se necessário, reinicie o computador

---

**Última atualização:** 2025-10-28
**Versão:** 1.0.0
