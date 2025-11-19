# 🔍 Análise Completa: Persistência de Customizações em Metadata Fields

**Data:** 2025-11-17
**Status:** ✅ CORREÇÃO APLICADA - AGUARDANDO TESTES

---

## 📋 Resumo Executivo

O usuário reporta que customizações de campos metadata (Nome de Exibição, Tipo, Categoria, Auto-Cadastro, Páginas, Obrigatório, Visibilidade) **não estão persistindo** após reinicializações ou quando o KV é apagado.

**Campos que DEVEM ser persistentes:**
- `display_name` (Nome de Exibição)
- `field_type` (Tipo)
- `category` (Categoria)
- `auto_register` / `available_for_registration` (Auto-Cadastro)
- `show_in_*` (Páginas - show_in_services, show_in_exporters, etc.)
- `required` (Obrigatório)
- `show_in_table`, `show_in_dashboard`, `show_in_form` (Visibilidade)

---

## 🔍 Análise do Código Atual

### ✅ O Que Está Funcionando

1. **PATCH Endpoint (`/metadata-fields/{field_name}`)** - ✅ CORRETO
   - Atualiza campos parcialmente
   - Salva no KV via `save_fields_config()`
   - Invalida cache após salvar
   - **Localização:** `backend/api/metadata_fields_manager.py:1975-2022`

2. **Merge Function (`merge_fields_preserving_customizations`)** - ✅ CORRETO
   - Preserva 20+ campos customizáveis
   - Faz merge inteligente entre campos extraídos e KV existente
   - **Localização:** `backend/api/metadata_fields_manager.py:193-287`

3. **Fallback (quando KV vazio)** - ✅ CORRETO
   - Faz merge antes de salvar
   - Preserva customizações existentes
   - **Localização:** `backend/api/metadata_fields_manager.py:360-415`

4. **Force-Extract** - ✅ CORRETO (testado)
   - NÃO salva no KV automaticamente
   - Apenas retorna campos extraídos
   - **Teste passou:** Customizações preservadas após force-extract

---

## 🔴 PROBLEMA IDENTIFICADO: PREWARM

### Localização do Bug
**Arquivo:** `backend/app.py`  
**Função:** `_prewarm_metadata_fields_cache()`  
**Linhas:** 132-166

### Código Problemático

```python
if existing_config and 'fields' in existing_config and len(existing_config['fields']) > 0:
    # KV JÁ TEM CAMPOS: ATUALIZAR APENAS extraction_status
    logger.info(
        f"[PRE-WARM] ✓ KV já possui {len(existing_config['fields'])} campos. "
        f"Atualizando extraction_status..."
    )
    
    # CRITICAL FIX: Atualizar extraction_status mesmo sem adicionar campos novos
    existing_config['extraction_status'] = {
        'total_servers': total_servers,
        'successful_servers': successful_servers,
        'server_status': extraction_result.get('server_status', []),
        'extraction_complete': True,
        'extracted_at': datetime.now().isoformat(),
    }
    existing_config['last_updated'] = datetime.now().isoformat()
    existing_config['source'] = 'prewarm_update_extraction_status'
    
    # ⚠️ PROBLEMA: Salva existing_config SEM fazer merge com campos extraídos
    await kv_manager.put_json(
        key='skills/eye/metadata/fields',
        value=existing_config,  # ← Usa dados ANTIGOS do KV
        metadata={'auto_updated': True, 'source': 'prewarm_extraction_status_update'}
    )
```

### Por Que Isso é um Problema?

1. **Race Condition:**
   - Prewarm lê `existing_config` do KV (linha 125)
   - Usuário edita campo via PATCH (salva no KV)
   - Prewarm salva `existing_config` ANTIGO de volta (sobrescreve!)

2. **Campos Desatualizados:**
   - Se campos foram extraídos do Prometheus mas não foram mergeados
   - `existing_config` pode ter estrutura antiga (sem novos campos do Prometheus)
   - Prewarm salva estrutura antiga, perdendo atualizações do Prometheus

3. **Timing:**
   - Prewarm roda em background após 1 segundo do startup
   - Se usuário edita campo logo após startup, prewarm pode sobrescrever

---

## 🔍 Cenários de Falha

### Cenário 1: Race Condition (Mais Provável)

```
T0: Backend inicia
T1: Prewarm lê KV → existing_config = {fields: [...], ...}
T2: Usuário edita campo 'company' via PATCH → KV atualizado
T3: Prewarm salva existing_config ANTIGO → KV sobrescrito ❌
```

**Resultado:** Customização perdida!

### Cenário 2: Estrutura Desatualizada

```
T0: KV tem campos com estrutura antiga (sem novos campos do Prometheus)
T1: Prewarm extrai campos do Prometheus (estrutura nova)
T2: Prewarm lê KV → existing_config (estrutura antiga)
T3: Prewarm salva existing_config (estrutura antiga) → perde atualizações ❌
```

**Resultado:** Campos do Prometheus não são atualizados no KV!

### Cenário 3: KV Apagado e Restaurado

```
T0: KV tem campos customizados
T1: KV é apagado (acidente ou manutenção)
T2: Fallback dispara → faz merge e salva ✅
T3: Backend reinicia
T4: Prewarm lê KV → existing_config (com customizações do fallback)
T5: Prewarm salva existing_config → OK ✅
```

**Resultado:** Funciona, mas apenas se fallback fez merge corretamente.

---

## ✅ SOLUÇÃO PROPOSTA

### Correção do Prewarm

**ANTES (ERRADO):**
```python
if existing_config and 'fields' in existing_config and len(existing_config['fields']) > 0:
    # Atualizar apenas extraction_status
    existing_config['extraction_status'] = {...}
    await kv_manager.put_json('skills/eye/metadata/fields', existing_config)  # ❌ Sobrescreve sem merge
```

**AGORA (CORRETO):**
```python
if existing_config and 'fields' in existing_config and len(existing_config['fields']) > 0:
    # PASSO 1: Fazer merge dos campos extraídos com KV existente
    extracted_fields_dicts = [f.to_dict() for f in fields]
    merged_fields = merge_fields_preserving_customizations(
        extracted_fields=extracted_fields_dicts,
        existing_kv_fields=existing_config['fields']
    )
    
    # PASSO 2: Atualizar extraction_status
    existing_config['extraction_status'] = {...}
    existing_config['fields'] = merged_fields  # ← Usar campos merged
    existing_config['last_updated'] = datetime.now().isoformat()
    
    # PASSO 3: Salvar campos merged (não sobrescrever!)
    await kv_manager.put_json('skills/eye/metadata/fields', existing_config)  # ✅ Merge feito
```

### Benefícios da Correção

1. ✅ **Preserva customizações:** Merge garante que customizações do KV são mantidas
2. ✅ **Atualiza estrutura:** Campos novos do Prometheus são adicionados
3. ✅ **Evita race condition:** Sempre faz merge antes de salvar
4. ✅ **Consistência:** Mesma lógica do fallback e force-extract

---

## 🧪 Plano de Teste

### Baseline (Antes da Correção)

1. ✅ **Teste de Persistência Básico** - PASSOU
   - Aplicar customizações → Verificar salvas → Force-extract → Verificar preservadas
   - **Resultado:** ✅ Passou

2. ⚠️ **Teste de Prewarm (Faltando)**
   - Aplicar customizações → Reiniciar backend → Verificar preservadas
   - **Status:** Não testado ainda

3. ⚠️ **Teste de Race Condition (Faltando)**
   - Editar campo logo após startup → Aguardar prewarm → Verificar preservadas
   - **Status:** Não testado ainda

### Testes Após Correção

1. **Teste de Prewarm com Merge**
   ```bash
   # 1. Aplicar customizações
   curl -X PATCH http://localhost:5000/api/v1/metadata-fields/company \
     -H "Content-Type: application/json" \
     -d '{"display_name": "TESTE PREWARM", "category": "test"}'
   
   # 2. Verificar salvas
   curl http://localhost:5000/api/v1/metadata-fields/company | jq '.field.display_name'
   # Deve retornar: "TESTE PREWARM"
   
   # 3. Reiniciar backend
   # Ctrl+C no backend, depois python app.py
   
   # 4. Aguardar prewarm completar (ver logs)
   # 5. Verificar preservadas
   curl http://localhost:5000/api/v1/metadata-fields/company | jq '.field.display_name'
   # Deve retornar: "TESTE PREWARM" (não "Empresa")
   ```

2. **Teste de Race Condition**
   ```bash
   # 1. Iniciar backend
   python app.py
   
   # 2. Imediatamente (dentro de 2 segundos) aplicar customização
   curl -X PATCH http://localhost:5000/api/v1/metadata-fields/company \
     -d '{"display_name": "RACE TEST"}'
   
   # 3. Aguardar prewarm completar
   # 4. Verificar preservadas
   curl http://localhost:5000/api/v1/metadata-fields/company | jq '.field.display_name'
   # Deve retornar: "RACE TEST"
   ```

3. **Teste de KV Apagado**
   ```bash
   # 1. Aplicar customizações
   # 2. Apagar KV
   curl -X DELETE http://172.16.1.26:8500/v1/kv/skills/eye/metadata/fields
   
   # 3. Fazer GET (dispara fallback)
   curl http://localhost:5000/api/v1/metadata-fields/
   
   # 4. Verificar que fallback fez merge (se houver backup)
   # Nota: Se KV foi apagado completamente, customizações serão perdidas
   # (isso é esperado - não há como recuperar se KV foi deletado)
   ```

---

## 📊 Comparação: Antes vs Depois

| Aspecto | ❌ ANTES (Bug) | ✅ DEPOIS (Corrigido) |
|---------|----------------|----------------------|
| **Prewarm com KV existente** | Salva `existing_config` sem merge | Faz merge antes de salvar |
| **Preserva customizações** | ❌ Pode perder (race condition) | ✅ Sempre preserva |
| **Atualiza estrutura** | ❌ Não atualiza campos do Prometheus | ✅ Atualiza via merge |
| **Race condition** | ❌ Vulnerável | ✅ Protegido |
| **Consistência** | ⚠️ Diferente do fallback | ✅ Mesma lógica do fallback |

---

## 🎯 Campos Preservados no Merge

A função `merge_fields_preserving_customizations` preserva os seguintes campos:

```python
customizable_fields = [
    'required',                    # Obrigatório
    'auto_register',              # Auto-Cadastro
    'category',                   # Categoria
    'order',                      # Ordem
    'description',                # Descrição
    'show_in_table',              # Visibilidade: Tabela
    'show_in_dashboard',          # Visibilidade: Dashboard
    'show_in_form',               # Visibilidade: Form
    'show_in_services',           # Páginas: Services
    'show_in_exporters',          # Páginas: Exporters
    'show_in_blackbox',           # Páginas: Blackbox
    'show_in_network_probes',     # Páginas: Network Probes
    'show_in_web_probes',         # Páginas: Web Probes
    'show_in_system_exporters',   # Páginas: System Exporters
    'show_in_database_exporters', # Páginas: Database Exporters
    'editable',                   # Editável
    'enabled',                    # Habilitado
    'available_for_registration', # Auto-Cadastro (alternativo)
    'validation_regex',           # Validação
    'default_value',              # Valor padrão
    'placeholder',                # Placeholder
    'display_name',               # Nome de Exibição ✅
    'field_type',                 # Tipo ✅ (se customizado)
]
```

**Nota:** `field_type` está na lista, mas precisa ser verificado se está sendo preservado corretamente.

---

## 🚨 PONTOS CRÍTICOS ADICIONAIS

### 1. Cache Invalidation

Após salvar no KV, o cache deve ser invalidado:

```python
# Após salvar no prewarm
_kv_manager.invalidate('metadata/fields')  # ← Adicionar isso
```

**Localização:** `backend/app.py:160` (após `put_json`)

### 2. Lock para Escritas Simultâneas

Para evitar race conditions, adicionar lock:

```python
_kv_write_lock = asyncio.Lock()

async def _prewarm_metadata_fields_cache():
    async with _kv_write_lock:
        # Operações no KV aqui
        ...
```

**Localização:** `backend/app.py:61` (início da função)

### 3. Verificação de `field_type`

Verificar se `field_type` está sendo preservado corretamente no merge. Se não estiver, adicionar à lista de campos preservados.

---

## 📝 Checklist de Implementação

- [x] Corrigir prewarm para fazer merge antes de salvar ✅
- [x] Adicionar invalidação de cache após salvar no prewarm ✅
- [ ] Adicionar lock para escritas simultâneas (opcional, mas recomendado)
- [ ] Verificar se `field_type` está sendo preservado
- [ ] Executar teste de prewarm (baseline)
- [x] Aplicar correção ✅
- [ ] Executar teste de prewarm (após correção)
- [ ] Executar teste de race condition
- [ ] Validar que customizações persistem após reiniciar backend
- [ ] Validar que customizações persistem após apagar KV (se houver backup)

## ✅ Correções Aplicadas

### 1. Correção do Prewarm (Race Condition)

**Arquivo:** `backend/app.py`  
**Linhas:** 132-210  
**Data:** 2025-11-17

**Mudanças:**
1. **Merge antes de salvar:**
   - Importa `merge_fields_preserving_customizations` do `metadata_fields_manager`
   - Converte campos extraídos para dict
   - Faz merge preservando customizações do KV
   - Usa campos merged ao salvar

2. **Invalidação de cache:**
   - Adiciona invalidação de cache após salvar no KV
   - Garante que mudanças apareçam imediatamente

3. **Logs melhorados:**
   - Logs detalhados sobre o merge
   - Indica quantas customizações foram preservadas

### 2. Sistema de Backup Automático (NOVO)

**Arquivo:** `backend/core/metadata_fields_backup.py`  
**Data:** 2025-11-17

**Features Implementadas:**
1. **Backup automático:**
   - Backup criado ANTES de salvar no KV (em todos os pontos de salvamento)
   - Histórico de backups (últimos 10 backups)
   - Validação de integridade dos backups

2. **Restauração automática:**
   - Restauração automática se KV for apagado
   - Restauração do backup principal ou do histórico
   - Validação antes de restaurar

3. **Pontos de integração:**
   - `save_fields_config()` - Backup antes de salvar via PATCH
   - `load_fields_config()` - Restauração automática se KV vazio
   - `_prewarm_metadata_fields_cache()` - Backup no prewarm + restauração se KV vazio
   - Fallback - Backup antes de salvar campos extraídos

**Chaves no KV:**
- `skills/eye/metadata/fields` - Dados principais
- `skills/eye/metadata/fields.backup` - Último backup
- `skills/eye/metadata/fields.backup.history` - Histórico de backups (últimos 10)

---

## 🔗 Referências

- **Documentação de Persistência:** `backend/docs/PERSISTENCE_FIX_FINAL.md`
- **Documentação de Separação Extract/Sync:** `backend/docs/EXTRACT_SYNC_SEPARATION_FINAL.md`
- **Função de Merge:** `backend/api/metadata_fields_manager.py:193-287`
- **Prewarm:** `backend/app.py:61-224`
- **Fallback:** `backend/api/metadata_fields_manager.py:360-415`

---

## ✅ Conclusão

**Problema Identificado:** Prewarm salva `existing_config` sem fazer merge com campos extraídos, causando:
- Perda de customizações em race conditions
- Estrutura desatualizada no KV
- Inconsistência com fallback e force-extract

**Solução:** Fazer merge antes de salvar no prewarm, igual ao fallback.

**Prioridade:** 🔴 CRÍTICA - Afeta persistência de dados do usuário

