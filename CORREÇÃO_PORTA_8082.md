# 🔧 CORREÇÃO DE PORTAS: 8081 → 8082

## ❌ Problema Identificado

O frontend está rodando na porta **8081** ao invés de **8082** porque o `package.json` sobrescreve a configuração do `vite.config.ts`.

---

## 📋 Arquivos que Precisam ser Alterados

### ✅ **1. frontend/package.json** (CRÍTICO!)

**Linhas 7 e 10** - Comandos npm que sobrescrevem vite.config.ts:

```json
// ANTES:
"dev": "vite --port 8081",
"preview": "vite preview --port 8081"

// DEPOIS:
"dev": "vite --port 8082",
"preview": "vite preview --port 8082"
```

**Prioridade:** 🔴 ALTA - Este é o problema principal!

---

### ✅ **2. vite.config.ts** (JÁ CORRETO!)

```typescript
server: {
  port: 8082,  // ✅ Já está correto
  // ...
}
```

---

### ✅ **3. backend/app.py** (JÁ CORRETO!)

```python
if __name__ == "__main__":
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=5001,  # ✅ Já está correto
        log_level="info"
    )
```

---

### ✅ **4. frontend/src/services/api.ts** (JÁ CORRETO!)

```typescript
const API_URL = import.meta.env?.VITE_API_URL ?? 'http://localhost:5001/api/v1';
// ✅ Já aponta para 5001
```

---

### ⚠️ **5. backend/app.py** (CORS - Linha 90-93)

Verificar se CORS inclui porta 8082:

```python
origins = [
    "http://localhost:8081",  # ← Pode manter (compatibilidade)
    "http://localhost:8082",  # ← Adicionar esta linha
    # ...
]
```

---

## 📝 Arquivos de Documentação (Opcional)

Os seguintes arquivos mencionam 8081 na documentação, mas são opcionais de atualizar:

- `CLAUDE.md`
- `COMANDOS_RAPIDOS.md`
- `README.md`
- `docs/guides/restart-guide.md`
- Scripts em `scripts/deployment/*`

**Recomendação:** Atualizar depois para manter documentação consistente.

---

## ✅ Solução Rápida (Execute no Terminal)

### Windows (PowerShell):

```powershell
cd "D:\Skills IT\SK__Diversos - Documentos\DEV\Skills-Eye"

# 1. Corrigir package.json (substituir 8081 por 8082)
(Get-Content frontend\package.json) -replace '"vite --port 8081"', '"vite --port 8082"' -replace '"vite preview --port 8081"', '"vite preview --port 8082"' | Set-Content frontend\package.json

# 2. Verificar
cat frontend\package.json | Select-String "8082"

# 3. Reiniciar aplicação
cd frontend
npm run dev
# Deve exibir: http://localhost:8082/
```

### Linux/WSL:

```bash
cd /home/user/Skills-Eye

# 1. Corrigir package.json
sed -i 's/"vite --port 8081"/"vite --port 8082"/g' frontend/package.json
sed -i 's/"vite preview --port 8081"/"vite preview --port 8082"/g' frontend/package.json

# 2. Verificar
grep "8082" frontend/package.json

# 3. Reiniciar aplicação
cd frontend
npm run dev
# Deve exibir: http://localhost:8082/
```

---

## 🔍 Verificação Pós-Correção

Após aplicar as mudanças, execute:

```bash
# Backend
cd backend
python app.py
# Deve mostrar: Uvicorn running on http://0.0.0.0:5001

# Frontend (novo terminal)
cd frontend
npm run dev
# Deve mostrar: Local: http://localhost:8082/
```

**Teste no navegador:**
- Frontend: http://localhost:8082
- API Backend: http://localhost:5001/docs

---

## 📊 Resumo

| Arquivo | Status | Linha | Ação |
|---------|--------|-------|------|
| `frontend/package.json` | ❌ Incorreto | 7, 10 | Mudar 8081 → 8082 |
| `vite.config.ts` | ✅ Correto | 7 | Nenhuma |
| `backend/app.py` | ✅ Correto | 398 | Nenhuma |
| `api.ts` | ✅ Correto | 3 | Nenhuma |
| CORS (app.py) | ⚠️ Verificar | 90-93 | Adicionar 8082 |

---

## 🎯 Causa Raiz

O comando `npm run dev` no package.json usa `--port 8081`, que **sobrescreve** a configuração do `vite.config.ts`.

**Prioridade de configuração:**
1. CLI flags (`--port 8081`) ← **Mais alta (estava sobrescrevendo)**
2. vite.config.ts (`port: 8082`)
3. Defaults do Vite

Por isso, mesmo com vite.config.ts correto, o Vite usava 8081!

---

Criado por: Claude Code
Data: 2025-11-13
