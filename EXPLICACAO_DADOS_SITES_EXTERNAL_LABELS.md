# 📊 EXPLICAÇÃO: Fluxo de Dados - Sites e External Labels

**Data:** 12 de novembro de 2025  
**Contexto:** Consolidação Settings.tsx → MetadataFields.tsx

---

## 🔍 PERGUNTAS E RESPOSTAS

### 1️⃣ **De onde vêm os dados exatamente?**

#### **External Labels (Global do Servidor)**
**FONTE PRIMÁRIA:** Arquivo `prometheus.yml` de cada servidor Prometheus (seção `global.external_labels`)

**FLUXO:**
```
prometheus.yml (servidor remoto)
    ↓ (SSH + TAR extraction)
skills/eye/metadata/fields (Consul KV)
    ↓ (campo extraction_status.server_status)
Frontend exibe external_labels
```

**EXEMPLO prometheus.yml:**
```yaml
global:
  external_labels:
    site: palmas
    datacenter: genesis-dtc
    cluster: palmas-master
    environment: production
    prometheus_instance: 172.16.1.26
```

#### **Gerenciar Sites**
**FONTES MÚLTIPLAS (MERGE DE 3 ORIGENS):**

1. **Lista de servidores:** `.env` → `PROMETHEUS_CONFIG_HOSTS`
   ```bash
   PROMETHEUS_CONFIG_HOSTS="172.16.1.26:22/user/pass;172.16.200.14:22/user/pass;11.144.0.21:22/user/pass"
   ```

2. **External labels:** `skills/eye/metadata/fields` (KV) → campo `extraction_status.server_status[].external_labels`
   - Extraído via SSH do prometheus.yml
   - Campo `external_labels.site` vira `code` do site

3. **Configurações editáveis:** `skills/eye/metadata/sites` (KV)
   - Salvo quando usuário edita name/color/is_default
   - Se não existir, usa defaults

**CÓDIGO (backend/api/metadata_fields_manager.py:2355):**
```python
@router.get("/config/sites")
async def list_sites():
    # PASSO 1: Buscar configs editáveis do KV
    site_configs = await kv.get_json('skills/eye/metadata/sites') or {}
    
    # PASSO 2: Buscar external_labels extraídos
    fields_data = await load_fields_config()
    server_status_list = fields_data['extraction_status']['server_status']
    
    # PASSO 3: Parsear lista de servidores do .env
    prometheus_hosts_str = os.getenv("PROMETHEUS_CONFIG_HOSTS", "")
    
    # PASSO 4: Merge 3 fontes
    for host in raw_hosts:
        hostname = extract_hostname(host)
        external_labels = find_labels_by_hostname(server_status_list, hostname)
        site_code = external_labels.get('site', hostname)
        user_config = site_configs.get(site_code, {})
        
        # Montar site final
        site = {
            "code": site_code,                           # de external_labels.site
            "prometheus_host": hostname,                 # do .env
            "external_labels": external_labels,          # do prometheus.yml (KV)
            "name": user_config.get("name", site_code),  # do KV ou default
            "color": user_config.get("color", "blue"),   # do KV ou default
            "is_default": user_config.get("is_default")  # do KV ou false
        }
```

---

## ⏰ QUANDO OS DADOS SÃO ATUALIZADOS?

### **A. External Labels (no KV `skills/eye/metadata/fields`)**

#### ✅ **MOMENTOS DE ATUALIZAÇÃO:**

1. **Backend Pre-warm (Startup automático)**
   - Arquivo: `backend/app.py:_prewarm_metadata_fields_cache()`
   - Aguarda 1 segundo após startup
   - Executa `force_extract_fields()` em background
   - **CONDIÇÃO:** Só atualiza se KV vazio OU dados desatualizados (> 5min)
   ```python
   # app.py linha ~50
   async def _prewarm_metadata_fields_cache():
       await asyncio.sleep(1)  # Aguarda servidor subir
       await force_extract_fields()  # Extração SSH
   ```

2. **Botão "Sincronizar com Prometheus" (MetadataFields página)**
   - Chama: `POST /metadata-fields/force-extract`
   - **SEMPRE** força extração SSH
   - Sobrescreve KV com novos dados
   ```typescript
   // MetadataFields.tsx linha ~1350
   const handleForceExtract = async () => {
       await axios.post(`${API_URL}/metadata-fields/force-extract`);
   };
   ```

3. **Botão "Sincronizar Sites" (aba Gerenciar Sites)**
   - Chama: `POST /metadata-fields/config/sites/sync`
   - Internamente chama `force_extract_fields()`
   - Atualiza external_labels E cria sites novos
   ```python
   # metadata_fields_manager.py linha ~2569
   @router.post("/config/sites/sync")
   async def sync_sites_from_prometheus():
       extraction_result = await force_extract_fields()  # ← Atualiza KV
       sites_response = await list_sites()  # ← Lê KV atualizado
   ```

4. **Batch Sync (modal instantâneo ao abrir página)**
   - Chama: `POST /metadata-fields/batch-sync`
   - Extrai campos de TODOS os servidores
   - Salva em `skills/eye/metadata/fields`
   ```typescript
   // MetadataFields.tsx linha ~1400
   useEffect(() => {
       if (activeTab === 'meta-fields') {
           handleBatchSync();  // Auto-dispara ao entrar na aba
       }
   }, [activeTab]);
   ```

#### ❌ **QUANDO NÃO ATUALIZA:**

- Ao simplesmente LISTAR sites (`GET /config/sites`) → **LÊ do KV**, não extrai
- Ao EDITAR site (`PATCH /config/sites/{code}`) → **Só salva configs editáveis**
- Ao mudar servidor selecionado → **Lê KV existente**

---

### **B. Configurações Editáveis de Sites (no KV `skills/eye/metadata/sites`)**

#### ✅ **ATUALIZADO QUANDO:**

1. **Usuário clica "Salvar" no modal de edição**
   - Chama: `PATCH /metadata-fields/config/sites/{code}`
   - Atualiza APENAS `name`, `color`, `is_default`
   ```python
   # metadata_fields_manager.py linha ~2478
   @router.patch("/config/sites/{code}")
   async def update_site_config(code: str, updates: SiteConfigModel):
       site_configs[code] = {
           "name": updates.name,
           "color": updates.color,
           "is_default": updates.is_default
       }
       await kv.put_json('skills/eye/metadata/sites', site_configs)
   ```

2. **Sincronização de Sites (cria configs para sites novos)**
   - Chama: `POST /metadata-fields/config/sites/sync`
   - Se site não existe, cria config padrão
   - Se já existe, PRESERVA configs existentes
   ```python
   for site in detected_sites:
       if site_code not in site_configs:
           site_configs[site_code] = {
               "name": site_code.title(),
               "color": "blue",
               "is_default": False
           }
   ```

---

## 🗑️ SE REMOVER UM SERVIDOR DO .ENV

### **COMPORTAMENTO ATUAL:**

1. **Reiniciar Backend:**
   - Pre-warm lê novo `.env` (sem o servidor removido)
   - Tenta SSH para servidores restantes
   - **KV É ATUALIZADO** com lista nova (servidor removido some)

2. **External Labels do servidor removido:**
   - **PERMANECEM no KV** até próxima extração
   - Campo `server_status[]` é SUBSTITUÍDO, não merged
   ```python
   # metadata_fields_manager.py linha ~2197
   await kv.put_json(
       key='skills/eye/metadata/fields',
       value={
           'extraction_status': {
               'server_status': new_servers_list  # ← SOBRESCREVE lista antiga
           }
       }
   )
   ```

3. **Site associado ao servidor removido:**
   - **DESAPARECE da lista de sites** (`GET /config/sites`)
   - Motivo: Lista itera servidores do `.env`
   - Config editável (`skills/eye/metadata/sites`) PERMANECE no KV (órfão)

### **EXEMPLO PRÁTICO:**

**Antes (3 servidores):**
```bash
PROMETHEUS_CONFIG_HOSTS="palmas:22/u/p;rio:22/u/p;dtc:22/u/p"
```
- Sites: `[palmas, rio, dtc]`
- KV `skills/eye/metadata/sites`: `{palmas: {...}, rio: {...}, dtc: {...}}`

**Depois (remove "rio"):**
```bash
PROMETHEUS_CONFIG_HOSTS="palmas:22/u/p;dtc:22/u/p"
```
- Sites: `[palmas, dtc]` ← "rio" SOME da lista
- KV `skills/eye/metadata/sites`: `{palmas: {...}, rio: {...}, dtc: {...}}` ← config "rio" PERMANECE (órfão)

**IMPACTO:**
- ✅ Site "rio" NÃO aparece mais na interface
- ⚠️  Config de "rio" ocupa espaço no KV (não é deletado automaticamente)
- ✅ Se re-adicionar "rio" no futuro, config volta a funcionar

---

## 📋 RESUMO - MATRIZ DE ATUALIZAÇÃO

| Ação | External Labels (KV) | Configs Sites (KV) | Origem dos Dados |
|------|---------------------|-------------------|------------------|
| **Backend Startup** | ✅ Atualiza (pre-warm) | ❌ Não altera | SSH → prometheus.yml |
| **Sincronizar com Prometheus** | ✅ SEMPRE atualiza | ❌ Não altera | SSH → prometheus.yml |
| **Sincronizar Sites** | ✅ SEMPRE atualiza | ✅ Cria configs novos | SSH → prometheus.yml + .env |
| **Batch Sync (modal)** | ✅ Atualiza | ❌ Não altera | SSH → prometheus.yml |
| **Editar Site (modal)** | ❌ Não altera | ✅ Atualiza config | User input |
| **Listar Sites (GET)** | ❌ Só lê KV | ❌ Só lê KV | KV existente |
| **Mudar servidor selecionado** | ❌ Só lê KV | ❌ Não aplicável | KV existente |
| **Remover servidor .env** | ✅ Na próxima extração | ⚠️ Fica órfão | .env (PROMETHEUS_CONFIG_HOSTS) |

---

## 🎯 RECOMENDAÇÕES

### **Para Evitar Dados Órfãos:**

1. **Implementar limpeza automática:**
   ```python
   # Após sincronizar sites, remover configs órfãos
   active_site_codes = {s['code'] for s in sites}
   site_configs = {k: v for k, v in site_configs.items() if k in active_site_codes}
   ```

2. **Adicionar endpoint de manutenção:**
   ```python
   @router.post("/config/sites/cleanup")
   async def cleanup_orphan_sites():
       """Remove configs de sites que não existem mais no .env"""
   ```

### **Para Garantir Dados Atualizados:**

1. **Frontend sempre verificar timestamp:**
   ```typescript
   const isStale = (lastUpdate: Date) => {
       return Date.now() - lastUpdate.getTime() > 5 * 60 * 1000;  // 5min
   };
   ```

2. **Backend adicionar campo `last_extraction`:**
   ```python
   {
       "extraction_status": {
           "last_extraction": "2025-11-12T14:30:00Z",
           "server_status": [...]
       }
   }
   ```

---

## 📌 CONCLUSÃO

**External Labels:**
- ✅ Vêm do `prometheus.yml` (SSH extraction)
- ✅ Salvos em `skills/eye/metadata/fields`
- ✅ Atualizados via SSH em 4 momentos (startup, force-extract, sites-sync, batch-sync)
- ⚠️  Dados podem ficar órfãos se remover servidor do `.env`

**Sites:**
- ✅ MERGE de 3 fontes (.env + external_labels + user configs)
- ✅ Lista baseada no `.env` (só mostra servidores ativos)
- ✅ Configs editáveis persistem mesmo se servidor removido
- ⚠️  Recomenda-se implementar limpeza de órfãos
