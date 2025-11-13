# 🧪 BATERIA COMPLETA DE TESTES - PERSISTÊNCIA DE CUSTOMIZAÇÕES

## Objetivo

Garantir que **TODAS** as customizações de campos de metadados (required, auto_register, category, order, description, etc.) **PERSISTAM** em **QUALQUER** cenário de uso, incluindo:

- Reinícios do backend
- Extrações forçadas (botão Sincronizar)
- Edições via API
- Limpeza de cache
- Múltiplas operações simultâneas
- Situações de stress e concorrência
- Interações via UI (frontend)

---

## 📁 Estrutura dos Testes

### 1. **test_fields_merge.py** - Testes Básicos
**Propósito:** Validar o merge básico de customizações

**Cenários:**
- ✅ Aplicar customizações em 3 campos
- ✅ Salvar no KV
- ✅ Reiniciar backend (force reload)
- ✅ Verificar se customizações persistiram

**Execução:**
```bash
cd backend
python3 test_fields_merge.py customize   # Customizar campos
python3 test_fields_merge.py verify      # Verificar após restart
python3 test_fields_merge.py cleanup     # Limpar dados de teste
```

**Campos Testados:**
- `vendor`: required, auto_register, category
- `region`: required, auto_register, category
- `campoextra1`: required, auto_register, category

---

### 2. **test_all_scenarios.py** - Todos os Cenários
**Propósito:** Testar TODOS os fluxos possíveis de uso

**Cenários Testados:**

| # | Cenário | Descrição |
|---|---------|-----------|
| 1 | Reinício Simples | Restart do backend (cache em memória limpo) |
| 2 | Extração Forçada | POST /force-extract (botão Sincronizar) |
| 3 | PATCH Campo | Editar campo via PATCH /metadata-fields/{name} |
| 4 | Múltiplos Reinícios | 3 reinícios consecutivos |
| 5 | Reordenação | POST /reorder (mudar ordem dos campos) |
| 6 | Adicionar Campo | POST /add-to-kv (novo campo) |
| 7 | Remover Órfãos | POST /remove-orphans |
| 8 | **KV Vazio (CRÍTICO)** | Deletar KV e disparar fallback automático |

**Execução:**
```bash
cd backend
python3 test_all_scenarios.py
```

**Verificação:**
- Cada cenário aplica customizações → executa ação → verifica se persistiram
- Relatório final mostra quantos cenários passaram/falharam
- Exit code 0 se todos passaram, 1 se algum falhou

---

### 3. **test_stress_scenarios.py** - Stress Tests
**Propósito:** Testar comportamento sob carga extrema e concorrência

**Cenários de Stress:**

| # | Teste | Descrição |
|---|-------|-----------|
| 1 | 100 GETs Simultâneos | Stress de leitura concorrente |
| 2 | 50 PATCHs Simultâneos | Stress de escrita concorrente |
| 3 | 5 Extrações Consecutivas | Múltiplas extrações forçadas rápidas |
| 4 | Race Condition KV | 20 escritas simultâneas no KV |
| 5 | Large Payload (10KB) | Campos com descrições enormes |
| 6 | Fallback + 50 Acessos | 50 acessos simultâneos com KV vazio |

**Execução:**
```bash
cd backend
python3 test_stress_scenarios.py
```

**Validação:**
- Marcadores únicos (timestamp) em TODOS os campos
- Verificação de integridade após cada teste
- Detecção de race conditions e corrupção de dados

---

### 4. **test_frontend_integration.py** - Integração UI (Playwright)
**Propósito:** Simular interações REAIS de usuário via browser

**Requisitos:**
```bash
pip install playwright pytest-playwright
playwright install chromium
```

**Cenários UI:**

| # | Ação | Descrição |
|---|------|-----------|
| 1 | Customizar via UI | Editar campos pela interface (modal) |
| 2 | Verificar KV | Confirmar que KV foi atualizado |
| 3 | Botão Sincronizar | Clicar em "Sincronizar" (force extract) |
| 4 | Verificar após Sync | Confirmar customizações ainda presentes |
| 5 | Recarregar (F5) | Simular F5 no browser |
| 6 | Verificar após F5 | Customizações visíveis na UI |
| 7 | Limpar Cache | Clear localStorage, sessionStorage, cookies |
| 8 | Verificar após Clear | Customizações AINDA presentes |

**Execução:**
```bash
cd backend
python3 test_frontend_integration.py
```

**Comportamento:**
- Abre Chromium em modo **não-headless** (você vê o browser)
- Executa ações passo-a-passo com confirmação do usuário
- Verifica UI e KV após cada ação

---

### 5. **run_all_persistence_tests.sh** - Script Master
**Propósito:** Executar TODOS os testes sequencialmente

**Execução:**
```bash
cd backend
./run_all_persistence_tests.sh
```

**Fluxo:**
1. Verifica se backend está rodando (http://localhost:5000)
2. Executa test_fields_merge.py
3. Executa test_all_scenarios.py
4. Executa test_stress_scenarios.py
5. Pergunta se quer executar test_frontend_integration.py
6. Gera relatório final consolidado
7. Salva log completo em `test_results_YYYYMMDD_HHMMSS.log`

**Relatório Final:**
```
╔════════════════════════════════════════════════════════════════════════════╗
║                          RELATÓRIO FINAL DE TESTES                         ║
╚════════════════════════════════════════════════════════════════════════════╝

📊 Estatísticas:
   Total de Suítes: 4
   Passou: 4
   Falhou: 0

📋 Resultados por Suíte:
   ✅ Testes Básicos de Merge
   ✅ Todos os Cenários
   ✅ Stress Tests
   ✅ Integração Frontend

╔════════════════════════════════════════════════════════════════════════════╗
║                    ✅ TODOS OS TESTES PASSARAM! ✅                         ║
║          Customizações de campos estão TOTALMENTE PROTEGIDAS!             ║
╚════════════════════════════════════════════════════════════════════════════╝
```

---

## 🔍 O Que é Verificado

### Campos Customizáveis (DEVEM PERSISTIR):
- ✅ `required` (Boolean)
- ✅ `auto_register` (Boolean)
- ✅ `category` (String)
- ✅ `order` (Integer)
- ✅ `description` (String)
- ✅ `show_in_table` (Boolean)
- ✅ `show_in_dashboard` (Boolean)
- ✅ `show_in_filters` (Boolean)
- ✅ `show_in_form` (Boolean)
- ✅ `validation_regex` (String)
- ✅ `default_value` (String)
- ✅ `placeholder` (String)
- ✅ `help_text` (String)
- ✅ `display_name` (String)
- ✅ `field_type` (String - se customizado)

### Campos Dinâmicos (PODEM SER ATUALIZADOS):
- 🔄 `options` (List) - atualizado do Prometheus
- 🔄 `discovered_in` (List) - sites onde foi encontrado
- 🔄 `source_label` (String) - se não customizado

---

## 🚨 Cenários Críticos

### ❌ **KV Vazio (Fallback Automático)**
**Mais CRÍTICO de todos!**

**O que acontece:**
1. KV `skills/eye/metadata/fields` é deletado
2. Backend recebe requisição GET /metadata-fields/
3. Não encontra dados no KV
4. Dispara **fallback automático** (extração do Prometheus)
5. **DEVE FAZER MERGE** com customizações existentes (se houver backup)

**Verificação:**
```python
# ANTES: Campos customizados com required=True, category='test'
# DELETAR KV
# FAZER GET (dispara fallback)
# DEPOIS: Customizações DEVEM ter voltado
```

---

### ⚠️ **Race Condition (Escritas Simultâneas)**
**Cenário:** 20 threads escrevendo no mesmo KV ao mesmo tempo

**Risco:**
- Última escrita "ganha" → customizações anteriores perdidas
- KV corrompido (JSON inválido)

**Proteção Necessária:**
- Lock/semáforo em escritas no KV
- Merge inteligente (não overwrite cego)

---

### 💥 **Extração Forçada (Botão Sincronizar)**
**Cenário:** Usuário clica "Sincronizar" → POST /force-extract

**O que DEVE acontecer:**
1. Extrair dados novos do Prometheus
2. **MERGE** com customizações no KV
3. Salvar resultado merged

**O que NÃO DEVE acontecer:**
1. ❌ Overwrite completo do KV (perde customizações)
2. ❌ Ignorar dados do Prometheus (fica desatualizado)

---

## 📊 Métricas de Sucesso

### Critérios de Aprovação:

| Métrica | Meta | Crítico |
|---------|------|---------|
| Testes Básicos | 100% passando | ✅ SIM |
| Todos os Cenários | 100% passando | ✅ SIM |
| Stress Tests | ≥90% passando | ⚠️ Desejável |
| Integração UI | 100% passando | ✅ SIM |
| KV Vazio (Fallback) | DEVE PASSAR | ✅ **CRÍTICO** |

---

## 🛠️ Troubleshooting

### ❌ Teste "KV Vazio" Falha

**Sintoma:** Customizações são PERDIDAS após fallback

**Causa Raiz:**
```python
# ERRADO (backend/api/metadata_fields_manager.py)
fields_dicts = [f.to_dict() for f in fields]
await kv.put_json('skills/eye/metadata/fields', {'fields': fields_dicts})  # OVERWRITE!
```

**Correção:**
```python
# CORRETO
existing_kv_data = await kv.get_json('skills/eye/metadata/fields')
merged_fields = merge_fields_preserving_customizations(
    extracted_fields=fields_dicts,
    existing_kv_fields=existing_kv_data.get('fields', [])
)
await kv.put_json('skills/eye/metadata/fields', {'fields': merged_fields})  # MERGE!
```

---

### ❌ Stress Test "Race Condition" Falha

**Sintoma:** KV corrompido ou customizações perdidas sob carga

**Causa:** Múltiplas escritas simultâneas sem lock

**Correção:**
```python
# Adicionar lock em metadata_fields_manager.py
_kv_write_lock = asyncio.Lock()

async def update_fields_config(...):
    async with _kv_write_lock:
        # Operações no KV aqui
        ...
```

---

### ❌ UI Test Falha

**Sintomas Comuns:**
1. Playwright não encontra elementos
2. Modal não abre
3. Timeouts

**Soluções:**
```bash
# 1. Verificar frontend rodando
curl http://localhost:3000

# 2. Verificar seletores CSS
# - Usar DevTools do Chrome para confirmar seletores
# - Ajustar locators em test_frontend_integration.py

# 3. Aumentar timeouts
await page.wait_for_selector('.ant-modal', timeout=10000)  # 10s
```

---

## 📝 Logs e Debugging

### Arquivos de Log:
```
backend/test_results_20250113_153045.log  # Log consolidado
backend/backend.log                        # Log do backend
```

### Debug Markers:
Todos os testes usam marcadores únicos para rastrear dados:

```python
# test_all_scenarios.py
field['description'] = f"[STRESS-TEST-{timestamp}] {field['name']}"

# test_stress_scenarios.py
field['description'] = f"[STRESS-TEST-{timestamp}] {field['name']}"

# test_frontend_integration.py
field['category'] = 'ui_test_category'
```

**Buscar no KV:**
```bash
curl http://localhost:8500/v1/kv/skills/eye/metadata/fields?raw | jq '.fields[] | select(.description | contains("STRESS-TEST"))'
```

---

## 🎯 Próximos Passos

### Testes Adicionais (Futuro):

1. **Testes de Migração**
   - Migrar de namespace antigo (`blackbox/`) para novo (`skills/eye/`)
   - Preservar customizações durante migração

2. **Testes de Backup/Restore**
   - Backup de customizações
   - Restore após desastre

3. **Testes de Versioning**
   - Múltiplas versões de schema de fields
   - Migração entre versões

4. **Testes de Performance**
   - Medir tempo de merge com 1000+ campos
   - Benchmark de leitura/escrita no KV

---

## 📞 Contato e Suporte

**Problemas? Falhas?**

1. Verificar logs em `backend/test_results_*.log`
2. Verificar KV: `curl http://localhost:8500/v1/kv/skills/eye/metadata/fields?raw`
3. Verificar backend logs: `tail -100 backend/backend.log`
4. Executar teste individual para isolar problema

**Contribuir:**
- Adicionar novos cenários em `test_all_scenarios.py`
- Adicionar stress tests em `test_stress_scenarios.py`
- Melhorar seletores UI em `test_frontend_integration.py`

---

## ✅ Checklist de Execução

Antes de considerar problema RESOLVIDO:

- [ ] `test_fields_merge.py` - 100% passando
- [ ] `test_all_scenarios.py` - 100% passando (especialmente "KV Vazio")
- [ ] `test_stress_scenarios.py` - ≥90% passando
- [ ] `test_frontend_integration.py` - 100% passando
- [ ] `run_all_persistence_tests.sh` - Exit code 0
- [ ] Customizações persistem após restart REAL do servidor
- [ ] Customizações persistem após limpar cache do browser
- [ ] Customizações persistem após múltiplas extrações forçadas

**Só então considere o bug DEFINITIVAMENTE RESOLVIDO! 🎉**
