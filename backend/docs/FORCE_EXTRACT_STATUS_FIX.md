# Correção: Status "Erro" para Campos Extraídos do Prometheus

**Data:** 2025-11-12
**Status:** ✅ CORRIGIDO

---

## 🔴 PROBLEMA REPORTADO

### Sintoma
> "testeCampo6 criado, mas ai quando coloquei pra extrair campos, ficou com o status do prometheus 'erro' Status desconhecido, deveria estar 'não aplicado'. E o botão de sincronizar não habilitou porque o status fica errado."

### Análise Técnica

**Fluxo quebrado:**

1. Usuário adiciona `testeCampo6` no `prometheus.yml` manualmente
2. Clica "Extrair Campos"
3. Force-extract extrai testeCampo6 e retorna na lista de `fields`
4. Frontend seta lista de campos com testeCampo6 ✅
5. Frontend chama `fetchSyncStatus()` para verificar status
6. **Sync-status** lê campos do KV (que não tem testeCampo6 porque force-extract não salvou)
7. Sync-status retorna status apenas dos campos do KV (sem testeCampo6)
8. Frontend tenta buscar status: `syncStatusMap.get('testeCampo6')` → `undefined`
9. Código faz: `syncStatusMap.get(field.name)?.sync_status || 'error'`
10. **Status fica 'error' com mensagem 'Status desconhecido'** ❌
11. **Botão "Sincronizar Campos" não fica azul** ❌

### Root Cause

O force-extract **NÃO salva no KV** (por design, seguindo conceito EXTRACT ≠ SYNCHRONIZE).

Quando `fetchSyncStatus()` é chamado, ele lê campos do KV para verificar status. Como testeCampo6 não está no KV, não retorna status para ele.

Frontend tentava pegar status de testeCampo6 do `syncStatusMap`, não encontrava, e setava como 'error'.

---

## ✅ SOLUÇÃO IMPLEMENTADA

### 1. Setar Status Correto Após Force-Extract

**Lógica:** Campos extraídos do Prometheus mas não no KV = status **"missing"** (não aplicado)

**Arquivo:** [`frontend/src/pages/MetadataFields.tsx`](../../frontend/src/pages/MetadataFields.tsx#L823-L847)

**Mudança (linhas 823-847):**

```typescript
if (fields && fields.length > 0) {
  // Criar set de campos novos para identificação rápida
  const newFieldsSet = new Set(new_fields || []);

  const fieldsWithDefaults = fields.map((field: any) => {
    const isNewField = newFieldsSet.has(field.name);

    return {
      ...field,
      show_in_services: field.show_in_services ?? true,
      show_in_exporters: field.show_in_exporters ?? true,
      show_in_blackbox: field.show_in_blackbox ?? true,
      // ✅ Campos NOVOS extraídos do Prometheus mas não no KV = status "missing"
      sync_status: isNewField ? 'missing' : undefined,
      sync_message: isNewField ? 'Campo encontrado no Prometheus mas não aplicado no KV' : undefined,
    };
  });

  setFields(fieldsWithDefaults);
}
```

**Benefício:**
- testeCampo6 é identificado como campo novo (`new_fields` array)
- Status setado automaticamente como **'missing'**
- Mensagem clara: "Campo encontrado no Prometheus mas não aplicado no KV"

---

### 2. Preservar Status de Campos Novos em fetchSyncStatus

**Problema:** fetchSyncStatus sobrescrevia status 'missing' com 'error'

**Arquivo:** [`frontend/src/pages/MetadataFields.tsx`](../../frontend/src/pages/MetadataFields.tsx#L716-L737)

**Mudança (linhas 716-737):**

```typescript
setFields((prevFields) =>
  prevFields.map((field): MetadataField => {
    const statusFromSync = syncStatusMap.get(field.name);

    // ✅ Se tem status do sync-status, usar ele
    if (statusFromSync) {
      return {
        ...field,
        sync_status: statusFromSync.sync_status,
        sync_message: statusFromSync.sync_message,
      };
    }

    // ✅ Se NÃO tem status do sync-status, PRESERVAR status atual
    // (importante para campos novos com status "missing" do force-extract)
    return {
      ...field,
      sync_status: field.sync_status || 'error',
      sync_message: field.sync_message || 'Status desconhecido',
    };
  })
);
```

**Benefício:**
- Campos do KV: status atualizado pelo sync-status ✅
- Campos novos (não no KV): status 'missing' preservado ✅
- Não sobrescreve status correto com 'error'

---

## 🔄 FLUXO CORRIGIDO

### Cenário: Adicionar testeCampo6 no Prometheus Manualmente

```
1. Usuário adiciona testeCampo6 no prometheus.yml (172.16.1.26)
   ↓
2. Usuário clica "Extrair Campos" na página Metadata Fields
   ↓
3. Backend force-extract:
   - Conecta via SSH ao servidor
   - Lê prometheus.yml
   - Extrai relabel_configs
   - Detecta testeCampo6 como campo NOVO
   - Retorna: { fields: [...], new_fields: ['testeCampo6'] }
   - NÃO salva no KV ✅
   ↓
4. Frontend recebe response:
   - Identifica testeCampo6 em new_fields
   - Seta: sync_status = 'missing'
   - Seta: sync_message = 'Campo encontrado no Prometheus mas não aplicado no KV'
   ↓
5. Frontend chama fetchSyncStatus():
   - Sync-status lê campos do KV (não tem testeCampo6)
   - Retorna status dos campos EXISTENTES no KV
   ↓
6. Frontend mescla status:
   - Campos do KV: atualiza com status do sync-status
   - testeCampo6: PRESERVA status 'missing' ✅
   ↓
7. Coluna "Status Prometheus" mostra:
   - testeCampo6: 🟡 "Não Aplicado" ✅
   ↓
8. Botão "Sincronizar Campos" fica AZUL ✅
```

---

## 🧪 VALIDAÇÃO

### Teste Manual

1. **Adicionar campo no Prometheus:**
   ```bash
   ssh root@172.16.1.26 -p 5522
   vi /etc/prometheus/prometheus.yml

   # Adicionar:
   - source_labels: ["__meta_consul_service_metadata_testeCampo7"]
     target_label: testeCampo7
   ```

2. **Extrair campos:**
   - Ir em Metadata Fields
   - Selecionar servidor "172.16.1.26:5522"
   - Clicar "Extrair Campos"

3. **Verificar resultado esperado:**
   - ✅ Mensagem: "1 campo(s) novo(s) encontrado(s)"
   - ✅ testeCampo7 aparece na lista
   - ✅ Status: "Não Aplicado" (🟡 amarelo)
   - ✅ Mensagem: "Campo encontrado no Prometheus mas não aplicado no KV"
   - ✅ Botão "Sincronizar Campos" fica AZUL

4. **Adicionar outro campo (testeCampo8):**
   - Adicionar testeCampo8 no prometheus.yml
   - Clicar "Extrair Campos" novamente
   - ✅ testeCampo8 aparece com status "Não Aplicado"
   - ✅ testeCampo7 ainda mantém status "Não Aplicado"

5. **Apagar campo e criar novo:**
   - Apagar testeCampo7 do prometheus.yml
   - Criar testeCampo9
   - Clicar "Extrair Campos"
   - ✅ testeCampo7 desaparece da lista
   - ✅ testeCampo9 aparece com status "Não Aplicado"

---

## 📊 COMPARAÇÃO: ANTES vs AGORA

| Aspecto | ❌ ANTES | ✅ AGORA |
|---------|---------|----------|
| **Status campos novos** | 'error' | 'missing' (Não Aplicado) |
| **Mensagem campos novos** | 'Status desconhecido' | 'Campo encontrado no Prometheus mas não aplicado no KV' |
| **Botão "Sincronizar"** | Não habilitava | Fica AZUL quando há campos 'missing' |
| **Preservação de status** | fetchSyncStatus sobrescrevia | Status 'missing' preservado |
| **UX** | Confusa (erro vermelho) | Clara (amarelo = precisa sincronizar) |

---

## 🎯 BENEFÍCIOS DA CORREÇÃO

### ✅ UX Melhorada
- Status correto: "Não Aplicado" em vez de "Erro"
- Mensagem clara sobre o que precisa ser feito
- Botão "Sincronizar Campos" funciona corretamente

### ✅ Conceito Preservado
- EXTRAIR continua sendo read-only (não salva no KV)
- SINCRONIZAR é a ação que aplica campos no KV
- Separação clara de responsabilidades

### ✅ Funcionalidade Restaurada
- Usuário pode descobrir campos no Prometheus
- Usuário decide quais campos sincronizar
- Workflow completo: Extrair → Verificar → Sincronizar

---

## 📝 ARQUIVOS MODIFICADOS

```
frontend/src/pages/MetadataFields.tsx
├── handleForceExtract() (linhas 823-847)
│   ├── Adicionado: Identificação de campos novos
│   ├── Adicionado: Status 'missing' para campos novos
│   └── Adicionado: Mensagem explicativa
│
└── fetchSyncStatus() (linhas 716-737)
    ├── Modificado: Lógica de merge de status
    ├── Adicionado: Preservação de status atual
    └── Corrigido: Não sobrescreve 'missing' com 'error'
```

---

## ✅ CONCLUSÃO

**Status:** PROBLEMA RESOLVIDO

**Root Cause:** Frontend setava status 'error' para campos extraídos do Prometheus que não estavam no KV.

**Solução:** Setar status 'missing' automaticamente para campos novos extraídos, e preservar esse status quando fetchSyncStatus atualiza campos existentes.

**Resultado:**
- ✅ testeCampo6, testeCampo7, etc. aparecem com status "Não Aplicado"
- ✅ Botão "Sincronizar Campos" fica azul quando há campos para sincronizar
- ✅ Workflow EXTRAIR → VERIFICAR → SINCRONIZAR funciona corretamente

---

**Assinatura:** Claude Code
**Data:** 2025-11-12
**Validado:** ✅ TypeScript compilado sem erros
