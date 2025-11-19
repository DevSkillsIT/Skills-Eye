# 🔍 Análise de Persistência: Categorization Rules

**Data:** 2025-11-18  
**Preocupação:** Mudanças em monitoring/rules serão persistentes?

## 📋 Resumo Executivo

**✅ BOAS NOTÍCIAS:**
- Não há prewarm para categorization rules (apenas para metadata-fields e monitoring-types)
- Script de migração só roda se KV estiver vazio
- Mudanças via frontend são salvas diretamente no KV

**⚠️ RISCOS IDENTIFICADOS:**
- Script de migração SOBRESCREVE tudo se executado manualmente com `force=True`
- Se KV for limpo, migração automática vai sobrescrever customizações

---

## 🔍 Análise Detalhada

### 1. Prewarm para Categorization Rules

**Status:** ❌ NÃO EXISTE

**Prewarms existentes:**
- ✅ `_prewarm_metadata_fields_cache()` - metadata fields (faz merge preservando customizações)
- ✅ `_prewarm_monitoring_types_cache()` - monitoring types (sempre sobrescreve, mas não é editável)
- ❌ **Nenhum prewarm para categorization rules**

**Conclusão:** Não há risco de prewarm sobrescrever suas customizações.

---

### 2. Script de Migração (`migrate_categorization_to_json.py`)

#### 2.1 Função `run_migration(force=False)`

**Localização:** `backend/migrate_categorization_to_json.py:318-355`

**Comportamento:**
```python
async def run_migration(force: bool = False) -> bool:
    # Verificar se regras já existem
    if not force:
        existing_rules = await config_manager.get(key, use_cache=False)
        if existing_rules and existing_rules.get('total_rules', 0) > 0:
            logger.info("Regras já existem - migração não necessária")
            return True  # ✅ NÃO EXECUTA MIGRAÇÃO
    
    # Se force=True ou KV vazio, executa migração
    success = await migrate(silent=True)  # ⚠️ SOBRESCREVE TUDO
```

**Proteção:**
- ✅ Se `force=False` (padrão) e KV tem regras → **NÃO executa migração**
- ⚠️ Se `force=True` → **SOBRESCREVE tudo** (perde customizações)
- ⚠️ Se KV vazio → **Executa migração** (cria regras hardcoded)

#### 2.2 Função `migrate(silent=False)`

**Localização:** `backend/migrate_categorization_to_json.py:128-280`

**Comportamento:**
```python
async def migrate(silent: bool = False):
    # Cria regras hardcoded do zero
    rules = []
    # ... adiciona regras hardcoded ...
    
    # ⚠️ SOBRESCREVE TUDO no KV
    success = await config_manager.put(key, rules_data)
```

**Problema:** Esta função **sempre sobrescreve** o KV. Não faz merge, não preserva customizações.

---

### 3. Migração Automática no Startup

**Localização:** `backend/app.py` (verificar se está implementado)

**Status:** ❓ PRECISA VERIFICAR

**Comportamento esperado:**
- Se KV vazio → Executa `run_migration(force=False)`
- Se KV tem dados → Não executa migração

**Risco:** Se alguém limpar o KV e reiniciar o backend, migração automática vai sobrescrever customizações.

---

### 4. Como Mudanças são Salvas (Frontend → Backend)

**Localização:** `backend/api/categorization_rules.py`

#### 4.1 Criar Regra (`POST /api/v1/categorization-rules`)

```python
# PASSO 1: Buscar regras atuais do KV
rules_data = await config_manager.get('monitoring-types/categorization/rules')

# PASSO 2: Adicionar nova regra
rules_data['rules'].append(new_rule)

# PASSO 3: Salvar tudo de volta no KV
success = await config_manager.put('monitoring-types/categorization/rules', rules_data)
```

**✅ SEGURO:** Busca regras existentes, adiciona nova, salva tudo.

#### 4.2 Atualizar Regra (`PUT /api/v1/categorization-rules/{rule_id}`)

```python
# PASSO 1: Buscar regras atuais do KV
rules_data = await config_manager.get('monitoring-types/categorization/rules')

# PASSO 2: Encontrar e atualizar regra específica
for rule in rules_data['rules']:
    if rule['id'] == rule_id:
        # Atualiza campos fornecidos
        rule.update(updated_data)

# PASSO 3: Salvar tudo de volta no KV
success = await config_manager.put('monitoring-types/categorization/rules', rules_data)
```

**✅ SEGURO:** Busca regras existentes, atualiza regra específica, salva tudo.

#### 4.3 Deletar Regra (`DELETE /api/v1/categorization-rules/{rule_id}`)

```python
# PASSO 1: Buscar regras atuais do KV
rules_data = await config_manager.get('monitoring-types/categorization/rules')

# PASSO 2: Remover regra específica
rules_data['rules'] = [r for r in rules_data['rules'] if r['id'] != rule_id]

# PASSO 3: Salvar tudo de volta no KV
success = await config_manager.put('monitoring-types/categorization/rules', rules_data)
```

**✅ SEGURO:** Busca regras existentes, remove regra específica, salva tudo.

---

## ⚠️ Riscos Identificados

### Risco 1: Execução Manual do Script de Migração

**Cenário:**
```bash
# Alguém executa manualmente com force=True
python migrate_categorization_to_json.py --force
```

**Impacto:** ❌ **PERDE TODAS AS CUSTOMIZAÇÕES**

**Proteção:** Nenhuma. O script não verifica se há customizações.

**Recomendação:** Adicionar confirmação ou backup automático antes de sobrescrever.

---

### Risco 2: KV Limpo + Reinicialização

**Cenário:**
1. KV é limpo (acidentalmente ou propositalmente)
2. Backend reinicia
3. Migração automática detecta KV vazio
4. Executa `run_migration(force=False)` → `migrate()`
5. **SOBRESCREVE tudo com regras hardcoded**

**Impacto:** ❌ **PERDE TODAS AS CUSTOMIZAÇÕES**

**Proteção:** Nenhuma. Se KV estiver vazio, migração roda automaticamente.

**Recomendação:** Adicionar backup automático antes de migração.

---

### Risco 3: Race Condition (Baixo Risco)

**Cenário:**
1. Usuário edita regra no frontend
2. Ao mesmo tempo, alguém executa migração manual
3. Último `PUT` vence

**Impacto:** ⚠️ **Pode perder mudança recente**

**Proteção:** Consul KV é atômico, mas não há lock.

---

## ✅ O Que É Seguro

1. **Editar regras via frontend** → ✅ Salva diretamente no KV, persiste
2. **Criar novas regras** → ✅ Adiciona à lista existente, persiste
3. **Deletar regras** → ✅ Remove da lista, persiste
4. **Reiniciar backend** → ✅ Regras ficam no KV, não são sobrescritas
5. **Prewarm** → ✅ Não existe para categorization rules

---

## 🛡️ Recomendações de Proteção

### 1. Adicionar Backup Automático

**Antes de executar migração:**
```python
async def migrate(silent: bool = False):
    # PASSO 0: Fazer backup antes de sobrescrever
    existing_rules = await config_manager.get(key, use_cache=False)
    if existing_rules:
        backup_key = f"{key}.backup.{datetime.now().isoformat()}"
        await config_manager.put(backup_key, existing_rules)
        logger.info(f"Backup criado: {backup_key}")
    
    # ... resto da migração ...
```

### 2. Adicionar Confirmação para `force=True`

**No script de migração:**
```python
if force:
    print("⚠️ ATENÇÃO: force=True vai SOBRESCREVER todas as regras existentes!")
    confirm = input("Digite 'SIM' para confirmar: ")
    if confirm != 'SIM':
        print("Migração cancelada.")
        return False
```

### 3. Adicionar Flag de Customização

**Estrutura JSON:**
```json
{
  "version": "1.0.0",
  "last_updated": "2025-11-18T...",
  "has_customizations": true,  // ← Nova flag
  "rules": [...]
}
```

**Na migração:**
```python
if existing_rules and existing_rules.get('has_customizations'):
    logger.warning("⚠️ KV tem customizações! Migração cancelada.")
    return False
```

---

## 📊 Conclusão

**Resposta direta:** Sim, suas mudanças em monitoring/rules **SÃO PERSISTENTES**, mas há riscos:

✅ **Seguro:**
- Editar via frontend
- Reiniciar backend
- Prewarm não afeta (não existe)

⚠️ **Risco:**
- Executar migração manual com `force=True`
- Limpar KV e reiniciar backend

**Recomendação:** Implementar backup automático antes de migrações.

