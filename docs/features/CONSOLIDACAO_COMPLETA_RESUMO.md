# ✅ CONSOLIDAÇÃO COMPLETA - Settings.tsx → MetadataFields.tsx

**Data:** 12 de novembro de 2025  
**Sessão:** Merge de funcionalidades + Auto-detecção de Sites

---

## 📊 RESUMO EXECUTIVO

**PROBLEMA ORIGINAL:**
- Funcionalidades duplicadas entre Settings.tsx e MetadataFields.tsx
- Sites cadastrados manualmente (deveria vir do Prometheus)
- External labels buscados 2x (redundância)
- API fragmentada (/settings vs /metadata-fields)

**SOLUÇÃO IMPLEMENTADA:**
- ✅ Consolidação total em MetadataFields.tsx (4 abas)
- ✅ Auto-detecção de sites via external_labels.site
- ✅ Backend unificado (/metadata-fields/config/sites)
- ✅ CRUD manual substituído por sincronização SSH

---

## 🎯 O QUE FOI IMPLEMENTADO

### **BACKEND** (metadata_fields_manager.py)

#### **3 Novos Endpoints:**

```python
# URL BASE: /api/v1/metadata-fields/config/sites

1. GET /config/sites
   - Auto-detecta sites de 3 fontes
   - PROMETHEUS_CONFIG_HOSTS (.env) → lista de servidores
   - skills/eye/metadata/fields (KV) → external_labels extraídos
   - skills/eye/metadata/sites (KV) → configs editáveis do usuário
   
2. PATCH /config/sites/{code}
   - Atualiza APENAS campos editáveis: name, color, is_default
   - Campos readonly: code, prometheus_host, prometheus_port, external_labels
   
3. POST /config/sites/sync
   - Dispara force_extract_fields() (SSH)
   - Auto-detecta sites de external_labels.site
   - Cria configs para sites novos
   - Preserva configs editáveis existentes
```

#### **Fluxo de Dados:**

```
┌─────────────────┐
│ .env            │ PROMETHEUS_CONFIG_HOSTS="ip1:22/u/p;ip2:22/u/p"
└────────┬────────┘
         │
         ├─────► Lista de servidores (hostname, port)
         │
         ▼
┌─────────────────┐
│ SSH Extraction  │ TAR + ruamel.yaml parsing
└────────┬────────┘
         │
         ├─────► prometheus.yml → global.external_labels
         │
         ▼
┌─────────────────────────────────────┐
│ Consul KV                           │
│ skills/eye/metadata/fields          │
│   extraction_status:                │
│     server_status:                  │
│       - hostname: 172.16.1.26       │
│         external_labels:            │
│           site: palmas              │ ◄── site.code vem daqui
│           datacenter: genesis-dtc   │
│           cluster: palmas-master    │
└────────┬────────────────────────────┘
         │
         ├─────► Merge com configs editáveis
         │
         ▼
┌─────────────────────────────────────┐
│ Consul KV                           │
│ skills/eye/metadata/sites           │
│   palmas:                           │
│     name: "Palmas (TO)"             │ ◄── Editável
│     color: "blue"                   │ ◄── Editável
│     is_default: true                │ ◄── Editável
└─────────────────────────────────────┘
         │
         ├─────► Montagem final do site
         │
         ▼
┌─────────────────────────────────────┐
│ Response JSON                       │
│ {                                   │
│   code: "palmas",                   │ ← external_labels.site
│   name: "Palmas (TO)",              │ ← KV user config
│   prometheus_host: "172.16.1.26",  │ ← .env
│   prometheus_port: 9090,            │ ← .env
│   external_labels: {...},           │ ← Prometheus
│   color: "blue",                    │ ← KV user config
│   is_default: true                  │ ← KV user config
│ }                                   │
└─────────────────────────────────────┘
```

### **FRONTEND** (MetadataFields.tsx)

#### **4 Abas Consolidadas:**

```typescript
1. 📋 Campos Metadata
   - Visualização de campos extraídos do Prometheus
   - Edição de display_name, category, order, etc
   - Sincronização via SSH
   
2. 🌐 External Labels (Global do Servidor)
   - Mostra external_labels do SERVIDOR SELECIONADO
   - Usa estado externalLabels carregado por servidor
   
3. 🔗 External Labels (Todos Servidores)  ← NOVO
   - Mostra external_labels de TODOS os servidores
   - Usa fieldsData.serverStatus[] (dados já extraídos)
   - Cards por servidor com status (success/error)
   - ProDescriptions com labels em formato Tag
   
4. 🏢 Gerenciar Sites
   - Lista sites auto-detectados
   - Botão "Sincronizar Sites" (substitui "Adicionar Site")
   - Modal de edição com campos readonly + editáveis
   - Tabela com code, name, is_default, prometheus_host
```

#### **Funções Removidas:**

```typescript
// ❌ REMOVIDAS (CRUD manual não faz sentido)
- handleCreateSite()
- handleAutoFillPrometheusHosts()
- handleDeleteSite()
- Modal "Adicionar Novo Site"
- Botão "Auto-preencher Prometheus Hosts"

// ✅ ADICIONADAS (Auto-detecção)
- handleSyncSites() → POST /config/sites/sync
- Modal editável com readonly fields
- Interface Site.external_labels
```

#### **Modal de Edição Atualizado:**

```tsx
CAMPOS READONLY (auto-detectados):
✓ code (de external_labels.site)
✓ prometheus_host (de PROMETHEUS_CONFIG_HOSTS)
✓ prometheus_port (de PROMETHEUS_CONFIG_HOSTS)
✓ external_labels (JSON readonly, extraído do prometheus.yml)

CAMPOS EDITÁVEIS:
✓ name (nome descritivo para UI)
✓ color (cor do badge: blue, green, orange, etc)
✓ is_default (se true, não adiciona sufixo no nome)
```

---

## 📝 RESPOSTAS ÀS DÚVIDAS

### **1. De onde vêm os dados?**

#### **External Labels (Global do Servidor)**
**ORIGEM:** `prometheus.yml` (seção `global.external_labels`) de cada servidor remoto

**FLUXO:**
```
Servidor Prometheus (172.16.1.26)
  → prometheus.yml
    → global.external_labels:
      site: palmas
      datacenter: genesis-dtc
      
  → SSH Extraction (TAR + parsing)
  
  → Consul KV: skills/eye/metadata/fields
    extraction_status.server_status[].external_labels
    
  → Frontend lê do KV
```

#### **Gerenciar Sites**
**MERGE DE 3 ORIGENS:**

1. **.env → PROMETHEUS_CONFIG_HOSTS**
   - Lista de servidores (ip:port/user/pass)
   - Define quais servidores existem

2. **KV → skills/eye/metadata/fields**
   - External labels extraídos via SSH
   - Campo `external_labels.site` vira `code` do site

3. **KV → skills/eye/metadata/sites**
   - Configs editáveis salvos pelo usuário
   - name, color, is_default

---

### **2. Quando os dados são atualizados?**

#### **✅ EXTERNAL LABELS SÃO ATUALIZADOS QUANDO:**

| Ação | Backend Endpoint | Atualiza KV? | Trigger |
|------|-----------------|-------------|---------|
| **Backend Startup (Pre-warm)** | Automático (app.py) | ✅ Sim (se vazio ou > 5min) | Reiniciar backend |
| **Sincronizar com Prometheus** | POST /metadata-fields/force-extract | ✅ SEMPRE | Botão na página |
| **Sincronizar Sites** | POST /metadata-fields/config/sites/sync | ✅ SEMPRE | Botão "Sincronizar Sites" |
| **Batch Sync (modal instantâneo)** | POST /metadata-fields/batch-sync | ✅ Sim | Ao entrar na aba Campos Metadata |

#### **❌ EXTERNAL LABELS NÃO SÃO ATUALIZADOS QUANDO:**

- Listar sites (GET /config/sites) → Apenas lê KV
- Editar site (PATCH /config/sites/{code}) → Apenas salva configs editáveis
- Mudar servidor selecionado → Lê KV existente
- Abrir modal de edição → Não dispara extração

---

### **3. Quando o KV é atualizado?**

#### **skills/eye/metadata/fields (external_labels):**
- ✅ Pre-warm startup (1x ao iniciar backend, se necessário)
- ✅ Force Extract (botão "Sincronizar com Prometheus")
- ✅ Sites Sync (botão "Sincronizar Sites")
- ✅ Batch Sync (modal instantâneo ao entrar na aba)

**ESTRUTURA DO KV:**
```json
{
  "extraction_status": {
    "last_extraction": "2025-11-12T14:30:00Z",
    "server_status": [
      {
        "hostname": "172.16.1.26",
        "port": 22,
        "status": "success",
        "external_labels": {
          "site": "palmas",
          "datacenter": "genesis-dtc",
          "cluster": "palmas-master"
        }
      }
    ]
  }
}
```

#### **skills/eye/metadata/sites (configs editáveis):**
- ✅ Ao salvar modal de edição (PATCH /config/sites/{code})
- ✅ Ao sincronizar sites (POST /config/sites/sync) → Cria configs para sites novos

**ESTRUTURA DO KV:**
```json
{
  "palmas": {
    "name": "Palmas (TO)",
    "color": "blue",
    "is_default": true
  },
  "rio": {
    "name": "Rio de Janeiro (RJ)",
    "color": "green",
    "is_default": false
  }
}
```

---

### **4. Se remover um servidor do .env, o KV é atualizado?**

**SIM, mas com comportamento específico:**

#### **CENÁRIO: Remover servidor "rio" do .env**

**ANTES:**
```bash
PROMETHEUS_CONFIG_HOSTS="palmas:22/u/p;rio:22/u/p;dtc:22/u/p"
```
- GET /config/sites retorna: `[palmas, rio, dtc]`
- KV `skills/eye/metadata/fields` tem external_labels de todos 3
- KV `skills/eye/metadata/sites` tem configs de todos 3

**DEPOIS de remover "rio":**
```bash
PROMETHEUS_CONFIG_HOSTS="palmas:22/u/p;dtc:22/u/p"
```

**AO REINICIAR BACKEND OU SINCRONIZAR:**
- ✅ Pre-warm/Force Extract/Sync Sites → SSH apenas para palmas e dtc
- ✅ KV `skills/eye/metadata/fields` é SOBRESCRITO (remove rio)
  ```json
  "server_status": [
    {"hostname": "palmas", ...},  // ✅ Mantém
    // ❌ "rio" REMOVIDO
    {"hostname": "dtc", ...}      // ✅ Mantém
  ]
  ```

- ⚠️  KV `skills/eye/metadata/sites` MANTÉM config de "rio" (órfão)
  ```json
  {
    "palmas": {...},  // ✅ Ativo
    "rio": {...},     // ⚠️  Órfão (não deletado automaticamente)
    "dtc": {...}      // ✅ Ativo
  }
  ```

- ✅ GET /config/sites NÃO retorna "rio" (itera apenas servidores do .env)
  ```json
  "sites": [
    {"code": "palmas", ...},  // ✅ Aparece
    // ❌ "rio" NÃO aparece (servidor removido)
    {"code": "dtc", ...}      // ✅ Aparece
  ]
  ```

**IMPACTO:**
- ✅ Interface NÃO mostra site removido
- ⚠️  Config do site removido ocupa ~200 bytes no KV (não é problema)
- ✅ Se re-adicionar servidor no futuro, config volta automaticamente

**RECOMENDAÇÃO:**
Implementar endpoint de limpeza (futuro):
```python
@router.post("/config/sites/cleanup")
async def cleanup_orphan_sites():
    """Remove configs de sites que não existem mais no .env"""
    active_codes = {s['code'] for s in list_sites()['sites']}
    site_configs = await kv.get_json('skills/eye/metadata/sites')
    cleaned = {k: v for k, v in site_configs.items() if k in active_codes}
    await kv.put_json('skills/eye/metadata/sites', cleaned)
```

---

### **5. Em todos os casos os dados são atualizados?**

#### **MATRIZ DE ATUALIZAÇÃO:**

| Ação | External Labels (KV) | Sites Configs (KV) | Quando Executa |
|------|---------------------|-------------------|----------------|
| ✅ **Backend Startup** | SIM (se vazio/velho) | NÃO | Automático (pre-warm) |
| ✅ **"Sincronizar com Prometheus"** | SIM (sempre) | NÃO | Botão na aba Campos |
| ✅ **"Sincronizar Sites"** | SIM (sempre) | SIM (novos) | Botão na aba Sites |
| ✅ **Batch Sync (modal)** | SIM | NÃO | Ao entrar na aba |
| ✅ **"Extrair Campos"** | SIM (sempre) | NÃO | Botão force-extract |
| ❌ **Editar Site** | NÃO | SIM (atualiza) | Salvar modal |
| ❌ **Listar Sites** | NÃO (só lê) | NÃO (só lê) | GET endpoint |
| ❌ **Mudar servidor selecionado** | NÃO (lê cache) | N/A | Select dropdown |

**RESUMO:**
- **SSH é disparado em:** Startup, Sincronizar Prometheus, Sincronizar Sites, Batch Sync, Extrair Campos
- **KV de external_labels atualiza:** Sempre que SSH roda
- **KV de sites configs atualiza:** Ao sincronizar sites (novos) ou editar (existentes)

---

## 🎯 PRÓXIMOS PASSOS

### **FASE 4: Deprecar /settings API** (próxima tarefa)
```bash
mkdir backend/api/_deprecated
mv backend/api/settings.py backend/api/_deprecated/
# Remover de app.py linha 387
```

### **FASE 5: Remover Settings.tsx**
```bash
mkdir frontend/src/pages/_deprecated
mv frontend/src/pages/Settings.tsx frontend/src/pages/_deprecated/Settings.tsx.bak
```

### **FASE 6: Testes Finais**
- [ ] Sincronizar sites via SSH
- [ ] Editar name/color/is_default
- [ ] Verificar external_labels na nova aba "Todos Servidores"
- [ ] Validar Naming Strategy exibição
- [ ] Remover servidor do .env e verificar desaparecimento

---

## 📚 DOCUMENTAÇÃO ADICIONAL

**Arquivos Criados:**
- ✅ `EXPLICACAO_DADOS_SITES_EXTERNAL_LABELS.md` (fluxo de dados detalhado)
- ✅ `CONSOLIDACAO_COMPLETA_RESUMO.md` (este arquivo)

**Arquivos Modificados:**
- ✅ `backend/api/metadata_fields_manager.py` (+310 linhas)
- ✅ `frontend/src/pages/MetadataFields.tsx` (consolidação completa)

**Arquivos para Deprecar (FASE 4-5):**
- ⏳ `backend/api/settings.py` → `_deprecated/`
- ⏳ `frontend/src/pages/Settings.tsx` → `_deprecated/`

---

## ✅ CHECKLIST DE VALIDAÇÃO

**Backend:**
- [x] Endpoints /config/sites criados e funcionando
- [x] GET lista 3 sites com external_labels corretos
- [x] PATCH atualiza campos editáveis
- [x] POST sync detecta sites novos
- [x] KV é atualizado corretamente

**Frontend:**
- [x] Aba "External Labels (Todos Servidores)" adicionada
- [x] Botão "Sincronizar Sites" funcionando
- [x] Modal de edição com campos readonly
- [x] Interface Site.external_labels implementada
- [x] Compilação TypeScript sem erros

**Testes:**
- [x] Script test_sites_consolidation.py passa 100%
- [x] GET retorna 3 sites (palmas, rio, dtc)
- [x] PATCH atualiza nome e cor
- [x] POST sync detecta sites novos
- [x] /settings/naming-config mantém compatibilidade

---

**🎉 CONSOLIDAÇÃO FASE 1-3 COMPLETA E VALIDADA!**
