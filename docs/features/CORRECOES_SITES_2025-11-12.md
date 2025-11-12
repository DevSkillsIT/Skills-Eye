## CORREÇÕES IMPLEMENTADAS - 12/11/2025

### 🔴 PROBLEMA ORIGINAL
Usuário reportou 3 problemas críticos:
1. **Extração de servidor único apagava sites** - Ao clicar em "Extrair Campos" com servidor selecionado, sites dos outros servidores sumiam do KV
2. **Colunas "Descoberto Em" e "Origem" com N/A** - Campos não tinham `discovered_in` populado
3. **Gerenciador de Sites apagando outros sites** - Ao editar um site, apenas o editado permanecia no KV

---

## ✅ CORREÇÃO 1: sync_sites_to_kv() - Mesclar em vez de sobrescrever

**Arquivo:** `backend/api/metadata_fields_manager.py` (linhas ~2438-2496)

**Problema:**
```python
# ANTES (ERRADO):
new_sites = []  # ← Cria lista VAZIA
for server in server_status:
    site = {...}
    new_sites.append(site)  # ← Só adiciona sites do server_status
# Resultado: Apaga sites que não estão no server_status
```

**Solução:**
```python
# DEPOIS (CORRETO):
updated_sites_map = existing_sites_map.copy()  # ← Começa com TODOS os existentes
for server in server_status:
    site = {...}
    updated_sites_map[site_code] = site  # ← ATUALIZA no map (mescla)
new_sites = list(updated_sites_map.values())  # ← Converte map para lista
# Resultado: Preserva sites órfãos de outros servidores
```

**Impacto:**
- ✅ Extração de servidor único preserva os 3 sites
- ✅ Sites de servidores offline não são apagados
- ✅ Auto-sync funciona corretamente

---

## ✅ CORREÇÃO 2: extract_single_server_fields() - Popular discovered_in

**Arquivo:** `backend/core/multi_config_manager.py` (linhas ~408-418)

**Problema:**
```python
# ANTES (ERRADO):
fields_map = result.get('fields_map', {})
all_fields = list(fields_map.values())
# discovered_in não era populado → colunas ficavam N/A
```

**Solução:**
```python
# DEPOIS (CORRETO):
fields_map = result.get('fields_map', {})
all_fields = list(fields_map.values())

# CRÍTICO: Adicionar hostname ao discovered_in
for field in all_fields:
    if field.discovered_in is None:
        field.discovered_in = []
    if hostname not in field.discovered_in:
        field.discovered_in.append(hostname)
```

**Impacto:**
- ✅ Colunas "Descoberto Em" e "Origem" mostram dados corretos
- ✅ Campos sabem de quais servidores vieram
- ✅ Filtros de multi-servidor funcionam

---

## ✅ CORREÇÃO 3: update_site_config() - Preservar estrutura KV

**Arquivo:** `backend/api/metadata_fields_manager.py` (linhas ~2665-2735)

**Problema:**
```python
# ANTES (ERRADO):
kv_data = await kv.get_json('...') or {"sites": []}
site_configs_array = kv_data.get("sites", [])  # ← Ignora wrapper 'data'

# Salvar:
await kv.put_json(
    key='...',
    value={"sites": site_configs_array}  # ← Sobrescreve estrutura completa
)
```

**Estrutura REAL do KV:**
```json
{
  "data": {
    "sites": [...],
    "meta": {...}
  },
  "meta": {...}
}
```

**Solução:**
```python
# DEPOIS (CORRETO):
kv_data = await kv.get_json('...') or {"data": {"sites": []}}

# Extrair considerando wrapper
if 'data' in kv_data:
    data_wrapper = kv_data.get('data', {})
    if 'data' in data_wrapper:
        # Duplo wrapper
        site_configs_array = data_wrapper.get('data', {}).get('sites', [])
    else:
        # Wrapper simples
        site_configs_array = data_wrapper.get('sites', [])

# ... modificações ...

# Salvar PRESERVANDO estrutura completa
save_structure = kv_data.copy()  # ← Preserva tudo
if 'data' in save_structure.get('data', {}):
    save_structure['data']['data']['sites'] = site_configs_array
else:
    save_structure['data']['sites'] = site_configs_array

await kv.put_json(key='...', value=save_structure)
```

**Impacto:**
- ✅ Edição de site preserva os outros sites
- ✅ Estrutura do KV mantida íntegra
- ✅ Meta-informações preservadas

---

## ✅ CORREÇÃO 4: Frontend - Usar cores do KV

**Arquivo:** `frontend/src/pages/MetadataFields.tsx` (linhas ~1742-1755, ~1868-1895)

**Problema:**
```typescript
// ANTES (ERRADO):
const hasCustomName = site && site.name && site.name !== site.code;

if (hasCustomName) {
  return { displayName: site.name, color: site.color || 'blue' };
}
// ← Só usava cores do KV se nome fosse customizado
// Fallback sempre usava cores hardcoded
```

**Solução:**
```typescript
// DEPOIS (CORRETO):
if (site) {
  const displayName = site.name || site.code;
  const color = site.color || 'blue';
  return { displayName, color };  // ← SEMPRE usa dados do KV
}
// Fallback só é usado se site não existir
```

**Impacto:**
- ✅ Tags sempre usam cores configuradas no KV
- ✅ Mudanças de cor no gerenciador refletem imediatamente
- ✅ Consistência visual entre abas

---

## 📊 VALIDAÇÃO DOS TESTES

Teste automatizado executado com sucesso:

```bash
bash test_single_server_extraction.sh

✅ PASSO 1: Extração completa (3 servidores)
   - Sites sincronizados: 3
   
✅ PASSO 2: Extração de servidor único (172.16.1.26)
   - Sites sincronizados: 3
   - Campos extraídos: 21
   - Sites no KV: 3 (PRESERVADOS!)
   
✅ PASSO 3: discovered_in dos campos
   - vendor: 3 servidor(es)
   - region: 3 servidor(es)
   - campoextra1: 3 servidor(es)
   
✅ PASSO 4: Cores dos sites
   - palmas: green ✅
   - rio: cyan ✅
   - dtc: blue ✅
```

**Validação adicional do gerenciador:**
- Editado site "palmas" → 3 sites permaneceram ✅
- Editado site "rio" → 3 sites permaneceram ✅
- Cores atualizadas corretamente ✅

---

## 🎯 PRÓXIMAS AÇÕES

### Para o Usuário:
1. **Recarregar página no navegador** (Ctrl+Shift+R)
2. Verificar que colunas "Descoberto Em" e "Origem" mostram dados
3. Confirmar que cores dos sites estão corretas
4. Testar edição de sites no gerenciador

### Comandos de Teste Manual:
```bash
# Extrair de servidor único
curl -X POST http://localhost:5000/api/v1/metadata-fields/force-extract \
  -H "Content-Type: application/json" \
  -d '{"server_id": "172.16.1.26"}'

# Verificar sites
curl http://localhost:5000/api/v1/metadata-fields/config/sites

# Editar site
curl -X PATCH http://localhost:5000/api/v1/metadata-fields/config/sites/palmas \
  -H "Content-Type: application/json" \
  -d '{"name": "Palmas Teste", "color": "green"}'
```

---

## 🔍 ARQUIVOS MODIFICADOS

1. **backend/api/metadata_fields_manager.py**
   - `sync_sites_to_kv()`: Mesclar sites em vez de sobrescrever
   - `update_site_config()`: Preservar estrutura completa do KV

2. **backend/core/multi_config_manager.py**
   - `extract_single_server_fields()`: Popular discovered_in

3. **frontend/src/pages/MetadataFields.tsx**
   - Colunas "Descoberto Em" e "Origem": Sempre usar cores do KV

4. **test_single_server_extraction.sh** (novo)
   - Script de validação automatizada

---

## ⚠️ OBSERVAÇÕES IMPORTANTES

1. **Backend reiniciado** - Código novo está ativo
2. **Estrutura KV validada** - Wrapper `{"data": {...}, "meta": {...}}` preservado
3. **Multi-servidor funcionando** - Extração parcial não quebra dados globais
4. **Cores configuráveis** - Frontend usa KV como fonte única da verdade

---

**Status:** ✅ TODAS AS CORREÇÕES IMPLEMENTADAS E TESTADAS
**Data:** 12/11/2025
**Validação:** Automática + Manual
