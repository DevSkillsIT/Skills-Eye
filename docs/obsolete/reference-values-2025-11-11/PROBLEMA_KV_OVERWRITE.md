# ⚠️ PROBLEMA IDENTIFICADO: KV OVERWRITE NO PRE-WARM

**Data:** 2025-11-11
**Status:** 🔴 **CRÍTICO** - Perde customizações do usuário a cada restart

---

## 🐛 DESCRIÇÃO DO PROBLEMA

O backend possui uma função `_prewarm_metadata_fields_cache()` que roda automaticamente ao iniciar (`app.py:55-170`). Esta função:

1. Extrai campos do Prometheus via SSH
2. **SOBRESCREVE completamente** o KV `skills/eye/metadata/fields`
3. **PERDE todas as customizações** do usuário

### Código Problemático (app.py:119-134):

```python
await kv_manager.put_json(
    key='skills/eye/metadata/fields',
    value={
        'version': '2.0.0',
        'last_updated': datetime.now().isoformat(),
        'source': 'prewarm_startup',
        'total_fields': len(fields),
        'fields': [f.to_dict() for f in fields],  # ← PROBLEMA AQUI!
        ...
    },
    metadata={'auto_updated': True, 'source': 'startup_prewarm'}
)
```

**PROBLEMA:** `[f.to_dict() for f in fields]` cria novos objetos de campo extraídos do Prometheus, que têm `available_for_registration: false` por padrão (conforme solicitado).

---

## 💥 IMPACTO

### **Customizações Perdidas:**

- ✅ `available_for_registration` → ❌ Resetado para `false`
- ✅ `display_name` → ❌ Resetado para nome técnico
- ✅ `category` → ❌ Resetado para categoria padrão
- ✅ `order` → ❌ Resetado para ordem padrão
- ✅ `description` → ❌ Resetado para descrição padrão
- ✅ Outras configurações de UI → ❌ Perdidas

### **Campos que PARECEM Preservados:**

- ✅ `show_in_services` / `show_in_exporters` / `show_in_blackbox`

**POR QUÊ?** Porque esses campos são extraídos **do Prometheus** (se estiverem configurados no relabel_configs), então vêm nos novos objetos extraídos.

---

## 🎯 SOLUÇÃO NECESSÁRIA

Implementar **MERGE INTELIGENTE** ao invés de overwrite completo:

### **Estratégia:**

1. **Carregar campos existentes do KV** (se houver)
2. **Extrair novos campos do Prometheus**
3. **MERGE:**
   - **Campos NOVOS (não existem no KV):** Adicionar com valores padrão
   - **Campos EXISTENTES (já no KV):** Preservar customizações do usuário
   - **Campos OBSOLETOS (não existem mais no Prometheus):** Marcar como removidos (opcional)

### **Algoritmo de Merge:**

```python
async def _prewarm_metadata_fields_cache():
    # ... (código existente)

    # PASSO 1: Carregar configuração EXISTENTE do KV
    kv_manager = KVManager()
    existing_config = await kv_manager.get_json('skills/eye/metadata/fields')
    existing_fields_map = {}

    if existing_config and 'fields' in existing_config:
        # Criar mapa de campos existentes (key = field.name)
        existing_fields_map = {
            f['name']: f for f in existing_config['fields']
        }
        logger.info(f"[PRE-WARM] Campos existentes no KV: {len(existing_fields_map)}")

    # PASSO 2: Extrair novos campos do Prometheus
    extraction_result = await multi_config.extract_all_fields_with_asyncssh_tar()
    extracted_fields = extraction_result['fields']

    # PASSO 3: MERGE INTELIGENTE
    merged_fields = []
    for extracted_field in extracted_fields:
        field_name = extracted_field.name
        field_dict = extracted_field.to_dict()

        if field_name in existing_fields_map:
            # CAMPO EXISTE: PRESERVAR CUSTOMIZAÇÕES DO USUÁRIO
            existing_field = existing_fields_map[field_name]

            # PRESERVAR campos de customização do usuário
            field_dict['available_for_registration'] = existing_field.get('available_for_registration', False)
            field_dict['display_name'] = existing_field.get('display_name', field_dict['display_name'])
            field_dict['category'] = existing_field.get('category', field_dict['category'])
            field_dict['description'] = existing_field.get('description', field_dict['description'])
            field_dict['order'] = existing_field.get('order', field_dict['order'])
            field_dict['required'] = existing_field.get('required', field_dict['required'])
            field_dict['editable'] = existing_field.get('editable', field_dict['editable'])
            field_dict['show_in_table'] = existing_field.get('show_in_table', field_dict['show_in_table'])
            field_dict['show_in_dashboard'] = existing_field.get('show_in_dashboard', field_dict['show_in_dashboard'])
            field_dict['show_in_form'] = existing_field.get('show_in_form', field_dict['show_in_form'])

            logger.debug(f"[PRE-WARM] Campo '{field_name}' existe - customizações preservadas")
        else:
            # CAMPO NOVO: USAR VALORES PADRÃO (available_for_registration=false)
            logger.info(f"[PRE-WARM] Campo NOVO detectado: '{field_name}' (auto-cadastro desabilitado)")

        merged_fields.append(field_dict)

    # PASSO 4: Salvar campos MERGED no KV
    await kv_manager.put_json(
        key='skills/eye/metadata/fields',
        value={
            'version': '2.0.0',
            'last_updated': datetime.now().isoformat(),
            'source': 'prewarm_startup',
            'total_fields': len(merged_fields),
            'fields': merged_fields,  # ← AGORA USA CAMPOS MERGED!
            'extraction_status': {...}
        },
        metadata={'auto_updated': True, 'source': 'startup_prewarm'}
    )

    logger.info(f"[PRE-WARM] ✓ Cache atualizado com MERGE: {len(merged_fields)} campos (customizações preservadas)")
```

---

## ✅ BENEFÍCIOS DA SOLUÇÃO

1. ✅ **Preserva customizações** do usuário (`available_for_registration`, `display_name`, etc.)
2. ✅ **Adiciona novos campos** automaticamente (com auto-cadastro desabilitado)
3. ✅ **Atualiza campos técnicos** do Prometheus (source_label, prometheus_target_label)
4. ✅ **Mantém comportamento solicitado** - novos campos vêm desabilitados
5. ✅ **Não quebra funcionalidade** existente

---

## 🧪 TESTE

**Cenário de Teste:**

1. Habilitar campo "company" via Metadata Fields
2. Definir `available_for_registration: true`
3. Customizar `display_name: "Empresa"`
4. Reiniciar backend
5. **Verificar:** Campo "company" deve manter customizações ✅

---

## 📝 NOTAS TÉCNICAS

### **Campos a SEMPRE Preservar (customizações do usuário):**
- `available_for_registration`
- `display_name`
- `category`
- `description`
- `order`
- `required`
- `editable`
- `show_in_table`
- `show_in_dashboard`
- `show_in_form`
- `show_in_services`
- `show_in_exporters`
- `show_in_blackbox`

### **Campos a SEMPRE Atualizar (técnicos do Prometheus):**
- `name` (key)
- `source_label`
- `field_type`
- `prometheus_target_label`
- `metadata_source_label`

---

**Criado por:** Claude Code (Anthropic)
**Última atualização:** 2025-11-11
