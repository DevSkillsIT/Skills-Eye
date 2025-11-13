# 🔧 Troubleshooting - Tela em Branco

## Problema
Frontend mostra tela em branco ao acessar http://localhost:8081

## ✅ Correções Aplicadas

1. ✅ **Porta corrigida para 8081** em `frontend/package.json`
2. ✅ **Warning do regex corrigido** em `backend/core/blackbox_manager.py`

---

## 🔍 Diagnóstico Passo a Passo

### 1. Verificar Console do Navegador

1. Abra http://localhost:8081
2. Pressione **F12** para abrir DevTools
3. Vá na aba **Console**
4. Procure por erros em vermelho

**Erros Comuns:**

#### Erro: "Failed to fetch dynamically imported module"
**Causa:** Vite não compilou corretamente
**Solução:**
```bash
cd frontend
rm -rf node_modules/.vite
npm run dev
```

#### Erro: "Cannot find module '@ant-design/charts'"
**Causa:** Pacotes não instalados
**Solução:**
```bash
cd frontend
npm install
```

#### Erro: "Uncaught SyntaxError: Unexpected token '<'"
**Causa:** Servidor não está servindo JS corretamente
**Solução:** Limpar cache e recompilar
```bash
cd frontend
rm -rf dist node_modules/.vite
npm install
npm run dev
```

---

### 2. Verificar Network Tab

1. Abra DevTools (F12)
2. Vá na aba **Network**
3. Recarregue a página (Ctrl+R)
4. Verifique se há arquivos com status **404** ou **500**

**Se index.html retorna 404:**
- O servidor não está rodando
- Execute: `cd frontend && npm run dev`

**Se arquivos .js retornam 404:**
- Limpe o cache do Vite: `rm -rf node_modules/.vite`

---

### 3. Testar Compilação TypeScript

```bash
cd frontend
npx tsc --noEmit
```

**Se houver erros TypeScript:**
- Verifique os erros mostrados
- Corrija os tipos/imports indicados

**Erros TypeScript Comuns:**

```typescript
// ERRO: Cannot find name 'DashboardMetrics'
// SOLUÇÃO: Verificar se está importado de './services/api'
import { DashboardMetrics } from '../services/api';

// ERRO: Module '"dayjs"' has no exported member 'Dayjs'
// SOLUÇÃO: Usar import correto
import dayjs from 'dayjs';
```

---

### 4. Verificar se Backend está Respondendo

```bash
# Testar se backend está rodando
curl http://localhost:5000/api/v1/services

# Ou no PowerShell
Invoke-WebRequest -Uri http://localhost:5000/api/v1/services
```

**Se retornar erro de conexão:**
1. Verifique se backend está rodando: `cd backend && python app.py`
2. Verifique se Consul está rodando
3. Verifique .env do backend

---

### 5. Limpar Completamente e Reinstalar

Se nada funcionar, limpe tudo e recomece:

```bash
cd frontend

# Windows PowerShell
Remove-Item -Recurse -Force node_modules
Remove-Item -Recurse -Force dist
Remove-Item -Recurse -Force node_modules\.vite
npm install
npm run dev

# Linux/Mac
rm -rf node_modules dist node_modules/.vite
npm install
npm run dev
```

---

## 🧪 Testes Rápidos

### Teste 1: Backend Respondendo

```bash
curl http://localhost:5000/api/v1/services
```

**Esperado:** JSON com lista de serviços ou array vazio `{"services": []}`

### Teste 2: Frontend Compilando

```bash
cd frontend
npm run build
```

**Esperado:** Build success sem erros

### Teste 3: Arquivos Criados Existem

```bash
cd frontend/src/pages
dir
```

**Esperado:** Deve mostrar:
- Dashboard.tsx
- ServicePresets.tsx
- BlackboxGroups.tsx
- KVBrowser.tsx
- AuditLog.tsx

```bash
cd frontend/src/components
dir
```

**Esperado:** Deve mostrar:
- AdvancedSearchPanel.tsx
- ColumnSelector.tsx
- MetadataFilterBar.tsx

---

## 🔥 Solução Rápida (90% dos casos)

Execute isso no PowerShell/CMD:

```powershell
# Matar processos na porta 8081 (se houver)
netstat -ano | findstr :8081
# Anote o PID e mate: taskkill /PID <numero> /F

# Ir para frontend
cd frontend

# Limpar cache do Vite
Remove-Item -Recurse -Force node_modules\.vite -ErrorAction SilentlyContinue

# Rodar dev server
npm run dev
```

Depois abra: **http://localhost:8081**

---

## ✅ Checklist de Verificação

- [ ] Backend rodando na porta 5000
- [ ] Frontend rodando na porta 8081
- [ ] Consul rodando (verifique com `consul members`)
- [ ] Sem erros no console do navegador (F12)
- [ ] Sem erros 404 na aba Network
- [ ] `npm install` executado com sucesso
- [ ] Arquivo `frontend/src/App.tsx` existe e tem as rotas
- [ ] Arquivo `frontend/src/services/api.ts` existe
- [ ] Todas as páginas em `frontend/src/pages/` existem

---

## 🐛 Erros Específicos e Soluções

### Erro: "require is not defined"

**Causa:** Código CommonJS em projeto ES Module

**Solução:** Verificar se algum arquivo usa `require()` e trocar por `import`

```javascript
// ❌ ERRADO
const axios = require('axios');

// ✅ CORRETO
import axios from 'axios';
```

---

### Erro: "Top-level await is not available"

**Causa:** Await fora de função async

**Solução:** Envolver em função async

```javascript
// ❌ ERRADO
const data = await fetch('/api');

// ✅ CORRETO
async function getData() {
  const data = await fetch('/api');
}
```

---

### Erro: "Module not found: @dnd-kit/core"

**Causa:** Pacotes não instalados

**Solução:**
```bash
cd frontend
npm install @dnd-kit/core @dnd-kit/sortable @dnd-kit/utilities
```

---

### Erro: "Cannot read property 'charts' of undefined"

**Causa:** @ant-design/charts não instalado

**Solução:**
```bash
cd frontend
npm install @ant-design/charts
```

---

## 📞 Última Tentativa

Se **NADA** funcionar, execute este script completo:

```powershell
# Ir para o diretório do projeto
cd <project-directory>

# Parar tudo
taskkill /F /IM node.exe /T 2>$null
taskkill /F /IM python.exe /T 2>$null

# Limpar frontend
cd frontend
Remove-Item -Recurse -Force node_modules -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force dist -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force .vite -ErrorAction SilentlyContinue
Remove-Item package-lock.json -ErrorAction SilentlyContinue

# Reinstalar
npm install

# Verificar se instalou tudo
npm list @ant-design/charts
npm list @dnd-kit/core
npm list react
npm list typescript

# Iniciar backend (em outro terminal)
# cd backend
# python app.py

# Iniciar frontend
npm run dev
```

Depois acesse: **http://localhost:8081**

---

## 📸 Como Deve Aparecer

Quando funcionar, você verá:

1. **Console do navegador (F12):**
   - Sem erros vermelhos
   - Pode ter alguns warnings amarelos (ok)

2. **Tela:**
   - Menu lateral com: Dashboard, Serviços, Alvos Blackbox, etc.
   - Dashboard com cards de métricas
   - Gráficos (se houver dados)

3. **Network tab:**
   - `index.html` - Status 200
   - Vários arquivos `.js` - Status 200
   - Chamadas para `/api/v1/*` - Status 200 ou 404 (ok)

---

## 🆘 Ainda não funcionou?

**Envie essas informações:**

1. Output do console do navegador (F12 > Console)
2. Output do terminal do frontend (`npm run dev`)
3. Output do terminal do backend (`python app.py`)
4. Screenshot da tela em branco
5. Output de `npm list` no frontend

**Comando para coletar info:**
```powershell
cd frontend
npm run dev > frontend-log.txt 2>&1

cd ..\backend
python app.py > backend-log.txt 2>&1
```

Envie os arquivos `frontend-log.txt` e `backend-log.txt`.

---

**Boa sorte! 🚀**
