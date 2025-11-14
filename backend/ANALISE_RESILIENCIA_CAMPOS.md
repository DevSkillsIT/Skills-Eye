# Análise de Resiliência dos Campos Editáveis

**Data:** 2025-11-14  
**Objetivo:** Garantir que TODOS os campos editáveis no frontend mantenham seus dados mesmo que o KV seja recriado

---

## 📊 MAPEAMENTO DE CAMPOS EDITÁVEIS

### Campos Visíveis ao Usuário (Frontend)

| # | Nome da Coluna | Campo Backend | Fonte de Dados | Status Resiliência |
|---|----------------|---------------|----------------|-------------------|
| 1 | Ordem | `order` | KV customização | ✅ **SEGURO** |
| 2 | Nome Técnico | `name` | KV/extraction_status | ✅ **SEGURO** (não editável) |
| 3 | Nome de Exibição | `display_name` | KV customização | ✅ **SEGURO** |
| 4 | Tipo | `field_type` | KV customização | ✅ **SEGURO** |
| 5 | Categoria | `category` | KV customização | ✅ **SEGURO** |
| 6 | Auto-Cadastro | `available_for_registration` | KV customização | ✅ **SEGURO** |
| 7 | Páginas | `show_in_*` (9 campos) | KV customização | ✅ **SEGURO** |
| 8 | Obrigatório | `required` | KV customização | ✅ **SEGURO** |
| 9 | Visibilidade | `show_in_table/dashboard/form` | KV customização | ✅ **SEGURO** |
| 10 | **Descoberto Em** | `discovered_in` | **CALCULADO** via `extraction_status` | ⚠️ **VULNERÁVEL** |
| 11 | Status Prometheus | `sync_status` | RUNTIME (não persiste) | 🔄 **OK** (recalculado) |
| 12 | **Origem** | `discovered_in` (filtrado) | **CALCULADO** via `extraction_status` | ⚠️ **VULNERÁVEL** |

### Campos Internos Críticos (Não Visíveis mas Essenciais)

| # | Campo Backend | Fonte de Dados | Status Resiliência |
|---|---------------|----------------|-------------------|
| 13 | **source_label** | `extraction_status.server_status[].fields[]` | ⚠️ **VULNERÁVEL** |
| 14 | regex | extraction_status | ⚠️ **VULNERÁVEL** |
| 15 | replacement | extraction_status | ⚠️ **VULNERÁVEL** |

---

## 🔍 ANÁLISE DE FONTES DE DADOS

### ✅ DADOS SEGUROS (KV Customizações)
Estes dados são salvos em `config.fields[]` e SEMPRE preservados:

```json
{
  "name": "company",
  "display_name": "Empresa",
  "field_type": "select",
  "category": "basic",
  "available_for_registration": true,
  "show_in_services": true,
  "show_in_exporters": true,
  "show_in_blackbox": true,
  "show_in_network_probes": true,
  "show_in_web_probes": true,
  "show_in_system_exporters": true,
  "show_in_database_exporters": true,
  "show_in_infrastructure_exporters": true,
  "show_in_hardware_exporters": true,
  "required": true,
  "show_in_table": true,
  "show_in_dashboard": true,
  "show_in_form": true,
  "order": 5
}
```

**Resiliência:** ✅ **100% SEGURO**  
**Motivo:** Salvos em `save_fields_config()`, não dependem de `extraction_status`

---

### ⚠️ DADOS VULNERÁVEIS (extraction_status)
Estes dados vêm de `extraction_status.server_status[].fields[]`:

```json
{
  "extraction_status": {
    "last_extraction": "2025-11-14T16:30:00Z",
    "total_servers": 3,
    "successful_servers": 3,
    "server_status": [
      {
        "hostname": "172.16.1.26",
        "port": 8500,
        "external_labels": { "site": "SED01", ... },
        "fields": [  // ← SINGLE SOURCE OF TRUTH
          {
            "name": "company",
            "source_label": "__meta_consul_service_metadata_company",
            "regex": "(.+)",
            "replacement": "$1"
          },
          ...
        ]
      },
      ...
    ]
  }
}
```

**Campos que dependem desta estrutura:**
1. **`discovered_in`** → Calculado por `get_discovered_in_for_field(field_name, server_status)`
2. **`source_label`** → `server_status[].fields[].source_label`
3. **`regex`** → `server_status[].fields[].regex`
4. **`replacement`** → `server_status[].fields[].replacement`

**Resiliência:** ⚠️ **VULNERÁVEL**  
**Motivo:** Se `extraction_status` for perdido → campos ficam vazios/incompletos

---

## 🚨 CENÁRIOS DE RISCO IDENTIFICADOS

### ❌ CENÁRIO 1: Endpoint POST /add-to-kv
**Problema:**
```python
# PASSO 1: Carregar config atual
config = await load_fields_config()  # ✅ Tem extraction_status

# PASSO 2: Adicionar campos
config['fields'].append(field_data)

# PASSO 3: Salvar (BUG AQUI!)
await save_fields_config(config)  # ❌ Preserva extraction_status? NÃO VALIDA!
```

**Risco:** Se `config` não tiver `extraction_status` → `discovered_in` e `source_label` perdidos

---

### ❌ CENÁRIO 2: Endpoint PATCH /{field_name}
**Problema:**
```python
# PASSO 1: Carregar config
config = await load_fields_config()  # ✅ Tem extraction_status

# PASSO 2: Atualizar campo
field[key] = value

# PASSO 3: Salvar (BUG AQUI!)
await save_fields_config(config)  # ❌ Preserva extraction_status? NÃO VALIDA!
```

**Risco:** Se `config` não tiver `extraction_status` → `discovered_in` e `source_label` perdidos

---

### ❌ CENÁRIO 3: Endpoint POST /force-extract
**Problema:**
```python
# PASSO 1: Extrair campos via SSH
extraction_result = await multi_config.extract_all_fields_with_asyncssh_tar()
# ✅ extraction_result TEM server_status

# PASSO 2: Sincronizar sites
await sync_sites_to_kv(server_status)  # ✅ OK

# CRÍTICO: Force-extract NÃO salva campos no KV!
# Apenas retorna para frontend, mas NÃO preserva extraction_status no KV!
```

**Risco:** Se usuário executar force-extract mas não sincronizar campos → KV desatualizado

---

### ✅ CENÁRIO 4: Endpoint POST /migrate-add-new-show-in-fields (JÁ CORRIGIDO)
**Solução Implementada:**
```python
# ✅ VALIDAÇÃO CRÍTICA: Verificar se extraction_status está completo
extraction_status = config.get('extraction_status', {})
server_status = extraction_status.get('server_status', [])

if server_status:
    has_fields_array = any('fields' in srv and len(srv.get('fields', [])) > 0 for srv in server_status)
    
    if not has_fields_array:
        logger.warning("[MIGRATION] ⚠️ extraction_status incompleto (sem fields[]) - forçando re-extração")
        raise HTTPException(
            status_code=400,
            detail="KV está incompleto (sem server_status[].fields[]). Execute POST /force-extract primeiro..."
        )

# ✅ Usar save_fields_config() que PRESERVA toda a estrutura
await save_fields_config(config)
```

**Resiliência:** ✅ **PROTEGIDO** desde commit c68f0cc4

---

## 🛠️ SOLUÇÃO PROPOSTA

### FASE 1: Validação Preventiva em save_fields_config()

**Modificar função para SEMPRE validar extraction_status:**

```python
async def save_fields_config(config: Dict[str, Any]) -> bool:
    """
    Salva configuração de campos no Consul KV.
    
    ✅ GARANTIA DE RESILIÊNCIA:
    - Valida que extraction_status.server_status[].fields[] existe
    - Previne perda de discovered_in e source_label
    """
    try:
        from core.kv_manager import KVManager
        
        # ✅ VALIDAÇÃO CRÍTICA: Verificar extraction_status
        extraction_status = config.get('extraction_status', {})
        server_status = extraction_status.get('server_status', [])
        
        if not server_status:
            logger.warning("[SAVE] ⚠️ Config SEM extraction_status.server_status - BLOQUEANDO")
            raise HTTPException(
                status_code=400,
                detail="Config inválido: extraction_status.server_status está vazio. Execute force-extract primeiro."
            )
        
        has_fields_array = any('fields' in srv and len(srv.get('fields', [])) > 0 for srv in server_status)
        
        if not has_fields_array:
            logger.warning("[SAVE] ⚠️ extraction_status incompleto (sem fields[]) - BLOQUEANDO")
            raise HTTPException(
                status_code=400,
                detail="Config inválido: server_status[].fields[] vazio. Execute force-extract primeiro."
            )
        
        total_fields_discovered = sum(len(srv.get('fields', [])) for srv in server_status)
        logger.info(f"[SAVE] ✅ Validação OK: {len(server_status)} servidores, {total_fields_discovered} campos descobertos")
        
        kv = KVManager()
        
        # Atualizar timestamp
        config['last_updated'] = datetime.utcnow().isoformat() + 'Z'
        
        success = await kv.put_json('skills/eye/metadata/fields', config)
        
        if not success:
            raise ValueError("Falha ao salvar no Consul KV")
        
        logger.info(f"Configuração salva no KV: skills/eye/metadata/fields")
        return True
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao salvar configuração: {e}")
        raise HTTPException(status_code=500, detail=f"Erro ao salvar: {str(e)}")
```

---

### FASE 2: Teste Abrangente de Resiliência

**Expandir `test_discovered_in_resilience.py` para validar:**

```python
#!/usr/bin/env python3
"""
Teste de Resiliência COMPLETO - Metadata Fields

VALIDA:
1. ✅ extraction_status presente no KV
2. ✅ server_status com 3 servidores
3. ✅ server_status[].fields[] presente em todos servidores
4. ✅ discovered_in calculado corretamente
5. ✅ source_label presente em todos os campos
6. ✅ save_fields_config() preserva extraction_status
7. ✅ PATCH /{field_name} preserva extraction_status
8. ✅ POST /add-to-kv preserva extraction_status

PREVINE:
- Perda de discovered_in
- Perda de source_label
- Perda de regex/replacement
- KV corrompido sem extraction_status
"""
```

---

## 📝 CHECKLIST DE IMPLEMENTAÇÃO

### ✅ Já Implementado
- [x] Validação em POST /migrate-add-new-show-in-fields (commit c68f0cc4)
- [x] Teste básico test_discovered_in_resilience.py (commit c41f3ba)
- [x] Cálculo dinâmico de discovered_in via get_discovered_in_for_field()

### 🔲 Pendente (ESTA TAREFA)
- [ ] Adicionar validação em `save_fields_config()`
- [ ] Adicionar validação em PATCH `/{field_name}`
- [ ] Adicionar validação em POST `/add-to-kv`
- [ ] Expandir teste para validar `source_label`
- [ ] Expandir teste para simular PATCH
- [ ] Expandir teste para simular POST /add-to-kv
- [ ] Documentar novos campos em CHANGELOG

---

## 🎯 CRITÉRIO DE SUCESSO

**Sistema será considerado RESILIENTE quando:**

1. ✅ **NENHUM** endpoint puder salvar KV sem `extraction_status.server_status[].fields[]`
2. ✅ `discovered_in` SEMPRE calculado dinamicamente (nunca hardcoded)
3. ✅ `source_label` SEMPRE vindo de `extraction_status`
4. ✅ Teste automatizado validar TODOS os cenários de escrita no KV
5. ✅ Mensagens de erro claras orientando usuário a executar force-extract

---

## 📌 NOTAS TÉCNICAS

### Por que extraction_status é CRÍTICO?

`extraction_status.server_status[].fields[]` é a **SINGLE SOURCE OF TRUTH** porque:

1. **Multi-servidor:** Cada servidor Prometheus pode ter campos diferentes
2. **Rastreabilidade:** Saber ONDE cada campo foi descoberto
3. **Sincronização:** Decidir de qual servidor importar configurações
4. **Auditoria:** Histórico de quando/onde campos foram extraídos

### Por que NÃO podemos permitir KV sem extraction_status?

**Exemplo de KV CORROMPIDO:**
```json
{
  "fields": [
    {
      "name": "company",
      "display_name": "Empresa"
      // ❌ Faltam: source_label, regex, replacement
    }
  ]
  // ❌ Falta: extraction_status
}
```

**Consequências:**
- Frontend mostra "Descoberto Em: N/A"
- Frontend mostra "Origem: -"
- Sincronização com Prometheus QUEBRA (sem source_label)
- Impossível saber de qual servidor importar configurações

---

## 🔗 REFERÊNCIAS

- Issue #7: Migration de discovered_in para server_status[].fields[]
- Commit c68f0cc4: Fix migration validation
- Commit c41f3ba: Teste de resiliência
- Commit f64760f: Mudança para cálculo dinâmico de discovered_in
