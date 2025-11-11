# 🧪 TESTES AUTOMATIZADOS - BULK UPDATE

## ⚠️ POR QUE TESTAR?

O bulk update é **PERIGOSO** porque:
- Re-registra TODOS os serviços que usam um valor
- Se errado, pode **QUEBRAR todos os serviços** no Consul
- Pode perder ID, Address, Port, Tags, Checks

**NUNCA USE EM PRODUÇÃO SEM TESTAR ANTES!**

---

## 📦 TESTES DISPONÍVEIS

### 1. Teste Backend (Python Puro)
**Arquivo:** `test_bulk_update.py`

**O que faz:**
- ✅ Cria serviço de teste no Consul
- ✅ Cria reference value de teste
- ✅ Executa rename (bulk update)
- ✅ Compara serviço ANTES e DEPOIS
- ✅ Valida que APENAS `Meta.company` mudou
- ✅ Valida que ID, Address, Port, Tags, Checks permanecem intactos
- ✅ Remove serviço de teste

**Resultado esperado:**
```
✅ TESTE PASSOU - BULK UPDATE FUNCIONA CORRETAMENTE
✅ SEGURO PARA USO EM PRODUÇÃO
```

### 2. Teste Visual (Playwright)
**Arquivo:** `test_bulk_update_playwright.py`

**O que faz:**
- ✅ Abre navegador automaticamente
- ✅ Cria serviço de teste
- ✅ Navega para página Services (screenshot ANTES)
- ✅ Navega para Reference Values
- ✅ Faz rename visualmente (clica em botões)
- ✅ Volta para Services (screenshot DEPOIS)
- ✅ Valida que novo valor aparece na tabela

**Resultado esperado:**
```
✅ TESTE VISUAL PASSOU
✅ Bulk update funciona corretamente no navegador
```

---

## 🚀 COMO EXECUTAR

### Pré-requisitos

1. **Backend e Frontend rodando:**
   ```bash
   ./restart-all.sh
   ```

2. **Instalar dependências Python:**
   ```bash
   cd ~/projetos/Skills-Eye
   source backend/venv/bin/activate
   pip install httpx playwright
   ```

3. **Instalar navegadores Playwright (primeira vez):**
   ```bash
   playwright install chromium
   ```

### Executar Teste Backend

```bash
cd ~/projetos/Skills-Eye
python test_bulk_update.py
```

**Duração:** ~10 segundos

**Saída esperada:**
```
================================================================================
TESTE AUTOMATIZADO - BULK UPDATE DE REFERENCE VALUES
================================================================================

[INFO] PASSO 1: Criando reference value 'TestCompany_20251111_190000'...
[✓] Reference value 'TestCompany_20251111_190000' criado

[INFO] PASSO 2: Registrando serviço de teste 'test-bulk-update-20251111_190000'...
[✓] Serviço 'test-bulk-update-20251111_190000' registrado

[INFO] PASSO 3: Buscando serviço ANTES do rename...
[✓] Serviço encontrado
  ID: test-bulk-update-20251111_190000
  Address: 127.0.0.1
  Port: 9999
  Tags: ['test', 'bulk-update']
  Meta.company: TestCompany_20251111_190000

[INFO] PASSO 4: EXECUTANDO BULK UPDATE...
[!] Renomeando 'TestCompany_20251111_190000' → 'TestCompany_20251111_190000_RENAMED'
[✓] Bulk update concluído em 1.23s
  Mensagem: Valor renomeado de 'TestCompany_20251111_190000' para 'TestCompany_20251111_190000_RENAMED' (1 serviços atualizados)

[INFO] PASSO 5: Buscando serviço DEPOIS do rename...
[✓] Serviço encontrado
  ID: test-bulk-update-20251111_190000
  Address: 127.0.0.1
  Port: 9999
  Tags: ['test', 'bulk-update']
  Meta.company: TestCompany_20251111_190000_RENAMED

[INFO] PASSO 6: VALIDANDO resultado do bulk update...

[✓] ✅ VALIDAÇÃO PASSOU!
[✓] ✅ Apenas Meta.company mudou: 'TestCompany_20251111_190000' → 'TestCompany_20251111_190000_RENAMED'
[✓] ✅ ID, Address, Port, Tags, Checks permanecem intactos

================================================================================
✅ TESTE PASSOU - BULK UPDATE FUNCIONA CORRETAMENTE
✅ SEGURO PARA USO EM PRODUÇÃO
================================================================================
```

### Executar Teste Visual (Playwright)

```bash
cd ~/projetos/Skills-Eye
python test_bulk_update_playwright.py
```

**Duração:** ~30 segundos

**O que você vai ver:**
1. Navegador Chrome abre automaticamente
2. Acessa página Services
3. Tira screenshot ANTES
4. Acessa Reference Values
5. Clica para editar valor
6. Digita novo valor
7. Salva (executa bulk update)
8. Volta para Services
9. Tira screenshot DEPOIS
10. Navegador fecha

**Screenshots salvos:**
- `test_before_TIMESTAMP.png` - Página Services ANTES do rename
- `test_after_TIMESTAMP.png` - Página Services DEPOIS do rename

**Saída esperada:**
```
================================================================================
TESTE VISUAL (PLAYWRIGHT) - BULK UPDATE
================================================================================

[INFO] Lançando navegador...
[INFO] PASSO 1: Criando serviço de teste via API...
[✓] Serviço 'test-visual-20251111_190000' criado

[INFO] PASSO 2: Acessando página Services...
[✓] Página Services carregada

[INFO] PASSO 3: Buscando serviço na tabela...
[✓] Screenshot ANTES salvo: test_before_20251111_190000.png
[✓] Serviço 'test-visual-20251111_190000' encontrado na tabela
[INFO]   Empresa ANTES: VisualTest_20251111_190000

[INFO] PASSO 4: Navegando para Reference Values...
[✓] Página Reference Values carregada
[INFO] Selecionando campo 'company'...
[✓] Campo 'company' selecionado
[INFO] Buscando valor 'VisualTest_20251111_190000'...
[INFO] Clicando em Editar...
[✓] Modal de edição aberto
[INFO] Alterando valor para 'VisualTest_20251111_190000_RENAMED'...
[✓] Novo valor digitado: 'VisualTest_20251111_190000_RENAMED'

[!] EXECUTANDO BULK UPDATE...
[✓] Bulk update concluído em 2.45s

[INFO] PASSO 5: Voltando para página Services...
[✓] Página Services carregada
[✓] Screenshot DEPOIS salvo: test_after_20251111_190000.png

[INFO] PASSO 6: VALIDANDO que empresa mudou na tabela...
[✓] ✅ NOVO valor 'VisualTest_20251111_190000_RENAMED' aparece na tabela!
[✓] ✅ VALOR ANTIGO 'VisualTest_20251111_190000' NÃO aparece (correto!)

[✓] ✅ VALIDAÇÃO VISUAL PASSOU!

================================================================================
✅ TESTE VISUAL PASSOU
✅ Bulk update funciona corretamente no navegador
================================================================================
```

---

## 🔍 O QUE OS TESTES VALIDAM

### Teste Backend (`test_bulk_update.py`)

**Valida que NÃO muda:**
- ❌ ID do serviço
- ❌ Name do serviço
- ❌ Address
- ❌ Port
- ❌ Tags
- ❌ Checks (HTTP, Interval, etc)
- ❌ Outros campos Meta (env, tipo_monitoramento, etc)

**Valida que MUDA:**
- ✅ Meta.company (de valor antigo para novo)

### Teste Visual (`test_bulk_update_playwright.py`)

**Valida que:**
- ✅ Novo valor aparece na página Services
- ✅ Valor antigo NÃO aparece mais
- ✅ Bulk update não trava/quebra o frontend
- ✅ Interface funciona normalmente

---

## ❌ SE TESTE FALHAR

### Teste Backend Falha

```
❌ TESTE FALHOU - NÃO USE BULK UPDATE EM PRODUÇÃO!
❌ CÓDIGO TEM PROBLEMAS E PODE QUEBRAR SERVIÇOS
```

**Possíveis problemas:**
1. `❌ CAMPO 'ID' MUDOU` - CRÍTICO! Serviço está sendo recriado com novo ID
2. `❌ CAMPO 'Address' MUDOU` - Endereço foi perdido
3. `❌ CAMPO 'Port' MUDOU` - Porta foi perdida
4. `❌ TAGS mudaram` - Tags foram perdidas
5. `❌ CHECKS mudaram` - Health checks foram perdidos

**O que fazer:**
- ❌ **NÃO USE bulk update em produção**
- 🐛 **REPORTAR BUG** - Código tem erro crítico
- 🔧 **CORRIGIR** método `_bulk_update_services()` no backend

### Teste Visual Falha

```
❌ TESTE VISUAL FALHOU
❌ Bulk update NÃO funciona corretamente
```

**Possíveis problemas:**
1. Novo valor NÃO aparece na tabela Services
2. Valor antigo ainda aparece
3. Cache do frontend não foi limpo

**O que fazer:**
- 🔍 Ver screenshots: `test_before_*.png` e `test_after_*.png`
- 🐛 Verificar logs do backend: `tail -f backend/backend.log`
- 🔍 Verificar console do navegador (F12)

---

## 🎯 QUANDO RODAR OS TESTES

### SEMPRE rodar antes de:
- ✅ Usar bulk update em produção pela primeira vez
- ✅ Modificar código de `_bulk_update_services()`
- ✅ Modificar código de `rename_value()`
- ✅ Atualizar biblioteca do Consul

### NÃO precisa rodar:
- ❌ A cada rename (só na primeira vez)
- ❌ Depois de mudanças no frontend (só backend)

---

## 📊 PERFORMANCE ESPERADA

### Teste Backend
- **Tempo:** 5-15 segundos
- **Requisições:** ~10
- **Serviços criados:** 1 (temporário)

### Teste Visual
- **Tempo:** 20-40 segundos
- **Screenshots:** 2
- **Interações:** ~15 (cliques, digitação)

---

## 🛡️ SEGURANÇA DOS TESTES

### Testes são SEGUROS porque:
- ✅ Criam serviços com ID único (timestamp)
- ✅ Usam valores únicos (não colidem com produção)
- ✅ DELETAM tudo ao final (cleanup automático)
- ✅ NÃO tocam em serviços de produção
- ✅ Testam apenas com 1 serviço

### Testes NÃO afetam:
- ❌ Serviços de produção existentes
- ❌ Reference values de produção
- ❌ KV store de produção
- ❌ Prometheus (serviço de teste não é monitorado)

---

## 🔧 TROUBLESHOOTING

### Erro: "Backend não está rodando"
```bash
./restart-all.sh
sleep 5
python test_bulk_update.py
```

### Erro: "Consul não está acessível"
- Verificar: http://172.16.1.26:8500/ui
- Verificar token: `8382a112-81e0-cd6d-2b92-8565925a0675`

### Erro: "Module 'playwright' not found"
```bash
pip install playwright
playwright install chromium
```

### Erro: "Module 'httpx' not found"
```bash
pip install httpx
```

### Playwright: Navegador não abre
```bash
# Reinstalar navegadores
playwright install --force chromium
```

### Teste sempre falha
```bash
# Limpar cache e reiniciar
./stop-all.sh
sleep 3
./restart-all.sh
sleep 10
python test_bulk_update.py
```

---

## 📝 EXEMPLO DE EXECUÇÃO COMPLETA

```bash
# 1. Parar tudo
./stop-all.sh

# 2. Aguardar
sleep 3

# 3. Reiniciar
./restart-all.sh

# 4. Aguardar backend iniciar
sleep 10

# 5. Ativar venv
source backend/venv/bin/activate

# 6. Instalar dependências (primeira vez)
pip install httpx playwright
playwright install chromium

# 7. Rodar teste backend
python test_bulk_update.py

# 8. Se passou, rodar teste visual
python test_bulk_update_playwright.py

# 9. Ver screenshots
ls -lh test_*.png
```

---

## ✅ RESULTADO ESPERADO

Se **AMBOS** os testes passarem:

```
✅ TESTE BACKEND PASSOU
✅ TESTE VISUAL PASSOU
✅ BULK UPDATE FUNCIONA CORRETAMENTE
✅ SEGURO PARA USO EM PRODUÇÃO
```

**Então:**
- ✅ Código está correto
- ✅ Bulk update funciona
- ✅ **SEGURO usar em produção**

Se **QUALQUER** teste falhar:

```
❌ TESTE FALHOU
❌ NÃO USE EM PRODUÇÃO
```

**Então:**
- ❌ Código tem bug crítico
- ❌ **NÃO USE em produção**
- 🐛 Reportar problema

---

**Criado por:** Claude Code (Anthropic)
**Data:** 2025-11-11
**Versão:** 1.0
