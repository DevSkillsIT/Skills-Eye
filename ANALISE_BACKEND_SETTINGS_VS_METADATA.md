# 📊 Análise: Backend Settings vs Metadata Fields API

**Data:** 12 de Novembro de 2025  
**Objetivo:** Identificar redundâncias e oportunidades de consolidação entre `/settings` e `/metadata-fields`

---

## 🔍 1. MAPEAMENTO DE ENDPOINTS

### 📌 API `/settings` (backend/api/settings.py)

| Endpoint | Método | Função | Armazenamento |
|----------|--------|--------|---------------|
| `/settings/naming-config` | GET | Retorna naming strategy do `.env` + sites do KV | `.env` + `skills/eye/settings/sites` |
| `/settings/sites` | GET | Lista todos os sites | `skills/eye/settings/sites` |
| `/settings/sites` | POST | Cria novo site | `skills/eye/settings/sites` |
| `/settings/sites/{code}` | PUT | Atualiza site | `skills/eye/settings/sites` |
| `/settings/sites/{code}` | DELETE | Remove site | `skills/eye/settings/sites` |

**Características:**
- ✅ CRUD completo de sites
- ✅ Gerencia naming strategy (leitura do .env)
- ✅ Dados salvos em `skills/eye/settings/sites` (namespace próprio)
- ❌ **NÃO faz extração SSH** (não precisa)
- ❌ **NÃO gerencia external_labels** (apenas leitura para exibição)

---

### 📌 API `/metadata-fields` (backend/api/metadata_fields_manager.py)

| Endpoint | Método | Função | Armazenamento |
|----------|--------|--------|---------------|
| `/metadata-fields/` | GET | Lista campos metadata extraídos | `skills/eye/metadata/fields` |
| `/metadata-fields/servers` | GET | Lista servidores Prometheus com external_labels | Env vars + `skills/eye/metadata/fields` |
| `/metadata-fields/{name}` | PATCH | Atualiza configuração de campo | `skills/eye/metadata/fields` |
| `/metadata-fields/force-extract` | POST | Extração SSH forçada de campos | SSH → `skills/eye/metadata/fields` |
| `/metadata-fields/sync-status` | GET | Status de sincronização KV ↔ Prometheus | Comparação SSH |
| `/metadata-fields/add-to-kv` | POST | Adiciona campos ao KV | `skills/eye/metadata/fields` |
| `/metadata-fields/remove-orphans` | POST | Remove campos órfãos do KV | `skills/eye/metadata/fields` |

**Características:**
- ✅ **Extração SSH ativa** do prometheus.yml
- ✅ Gerencia campos metadata (relabel_configs)
- ✅ **Extrai external_labels** durante extração SSH
- ✅ Cache em memória (5 minutos)
- ✅ Fallback automático (popula KV se vazio)
- ✅ Pre-warming no startup do backend

---

## 🔄 2. FLUXO DE DADOS

### 🟢 Sites (Gerenciamento)

```
┌─────────────────────────────────────────────────────┐
│  FRONTEND (MetadataFields.tsx → Aba "Gerenciar Sites")
├─────────────────────────────────────────────────────┤
│  • loadConfig()           → GET /settings/naming-config
│  • fetchPrometheusServers() → GET /metadata-fields/servers
│  • handleCreateSite()     → POST /settings/sites
│  • handleUpdateSite()     → PUT /settings/sites/{code}
│  • handleDeleteSite()     → DELETE /settings/sites/{code}
└─────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────┐
│  BACKEND API (FastAPI)                              │
├─────────────────────────────────────────────────────┤
│  /settings/sites          → CRUD sites              │
│    ↓ Salva em: skills/eye/settings/sites            │
│                                                     │
│  /metadata-fields/servers → Lista servidores        │
│    ↓ Lê external_labels de: skills/eye/metadata/fields │
└─────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────┐
│  CONSUL KV (Armazenamento)                          │
├─────────────────────────────────────────────────────┤
│  skills/eye/settings/sites     ← CRUD sites         │
│  skills/eye/metadata/fields    ← External labels    │
└─────────────────────────────────────────────────────┘
```

### 🔵 External Labels (Visualização)

```
┌─────────────────────────────────────────────────────┐
│  EXTRAÇÃO SSH (Automática no startup)              │
├─────────────────────────────────────────────────────┤
│  1. Backend inicia → Pre-warming task               │
│  2. SSH para todos os servidores Prometheus         │
│  3. Extrai prometheus.yml via TAR + AsyncSSH        │
│  4. Parseia global.external_labels de cada servidor │
│  5. Salva em skills/eye/metadata/fields             │
└─────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────┐
│  GET /metadata-fields/servers                       │
├─────────────────────────────────────────────────────┤
│  • Lê de skills/eye/metadata/fields                 │
│  • Extrai extraction_status.server_status[]         │
│  • Retorna hostname, port, external_labels          │
│  • Cache de 5 minutos                               │
└─────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────┐
│  FRONTEND (MetadataFields.tsx)                      │
├─────────────────────────────────────────────────────┤
│  • fetchPrometheusServers() carrega lista           │
│  • Aba "External Labels (Todos Servidores)"         │
│    exibe ProCard com ProDescriptions                │
│  • Aba "Gerenciar Sites" usa getExternalLabelsForHost() │
│    para exibir colunas site/datacenter/cluster      │
└─────────────────────────────────────────────────────┘
```

---

## ⚠️ 3. REDUNDÂNCIAS IDENTIFICADAS

### 🔴 PROBLEMA #1: Dois endpoints retornam external_labels

**Endpoint 1:** `/settings/naming-config`
```python
# GET /api/v1/settings/naming-config
{
  "naming_strategy": "option2",
  "suffix_enabled": true,
  "default_site": "palmas",
  "sites": [
    {
      "code": "palmas",
      "name": "Palmas (TO)",
      "prometheus_host": "10.0.0.1",
      "prometheus_port": 9090,
      "external_labels": {...}  # ← ADICIONADO mas NÃO USADO
    }
  ]
}
```

**Endpoint 2:** `/metadata-fields/servers`
```python
# GET /api/v1/metadata-fields/servers
{
  "success": true,
  "servers": [
    {
      "hostname": "10.0.0.1",
      "port": 9090,
      "type": "master",
      "external_labels": {...}  # ← USADO no frontend
    }
  ]
}
```

**Análise:**
- ❌ **Duplicação:** External labels vêm da mesma fonte (KV)
- ❌ **Inconsistência:** `/settings/sites` retorna por site, `/metadata-fields/servers` retorna por servidor
- ✅ **Solução:** Usar APENAS `/metadata-fields/servers` para external_labels

---

### 🔴 PROBLEMA #2: Sites sem external_labels salvos

**Atual:**
```python
# /settings/sites POST/PUT
# Campos salvos no KV:
{
  "code": "palmas",
  "name": "Palmas (TO)",
  "prometheus_host": "10.0.0.1",  # ← Salvo
  "prometheus_port": 9090,        # ← Salvo
  # external_labels NÃO salvos (apenas leitura em tempo real)
}
```

**Problema:**
- ❌ External labels **NÃO são persistidos** em `skills/eye/settings/sites`
- ❌ Precisam ser buscados de `skills/eye/metadata/fields` toda vez
- ❌ Relação site ↔ servidor feita por `prometheus_host` (string match)

**Solução possível:**
- Salvar `external_labels` em `skills/eye/settings/sites` durante auto-fill
- OU manter como está (leitura em tempo real é mais atualizada)

---

### 🔴 PROBLEMA #3: Auto-fill faz matching por hostname

**Atual:**
```typescript
// frontend/src/pages/MetadataFields.tsx
const handleAutoFillPrometheusHosts = async () => {
  for (const site of config.sites) {
    // Procura servidor com external_labels.site === site.code
    const matchingServer = prometheusServers.find(
      server => server.external_labels?.site === site.code
    );
    if (matchingServer) {
      site.prometheus_host = matchingServer.hostname;
      site.prometheus_port = matchingServer.port;
    }
  }
  // Atualiza TODOS os sites via PUT
}
```

**Problema:**
- ❌ Matching frágil (depende de `external_labels.site` existir)
- ❌ Não funciona se external_labels não tiver campo `site`
- ❌ Atualização em lote (N requisições PUT)

**Solução:**
- Criar endpoint `/settings/sites/auto-fill` que faz matching no backend
- Retornar preview antes de aplicar
- Single transaction

---

## ✅ 4. OPORTUNIDADES DE MELHORIA

### 🟢 Consolidação Recomendada

#### Opção A: Mover tudo para `/metadata-fields` ⭐ RECOMENDADO

**Vantagens:**
- ✅ Endpoint único para gerenciamento de configurações
- ✅ External labels já estão sendo extraídos aqui
- ✅ Cache e pre-warming já implementados
- ✅ Lógica de SSH já existe

**Mudanças necessárias:**
```python
# backend/api/metadata_fields_manager.py

# ADICIONAR:
@router.get("/sites")
async def get_sites():
    """Lista sites (move de /settings/sites)"""
    # Ler de skills/eye/settings/sites
    pass

@router.post("/sites")
async def create_site(site: SiteConfig):
    """Cria site (move de /settings/sites)"""
    pass

@router.put("/sites/{code}")
async def update_site(code: str, site: SiteConfig):
    """Atualiza site (move de /settings/sites)"""
    pass

@router.delete("/sites/{code}")
async def delete_site(code: str):
    """Remove site (move de /settings/sites)"""
    pass

@router.get("/naming-config")
async def get_naming_config():
    """Naming strategy (move de /settings/naming-config)"""
    pass

@router.post("/sites/auto-fill")
async def auto_fill_prometheus_hosts():
    """Auto-preenche prometheus_host baseado em external_labels"""
    # Lógica de matching inteligente
    pass
```

**Resultado:**
- ✅ `/api/v1/metadata-fields/*` gerencia TUDO
- ✅ Depreciar `/api/v1/settings/*`
- ✅ Página única (`MetadataFields.tsx`)
- ✅ Remover `Settings.tsx` do projeto

---

#### Opção B: Manter separado mas integrar melhor

**Vantagens:**
- ✅ Separação de responsabilidades clara
- ✅ `/settings` = configurações estáticas (sites, naming)
- ✅ `/metadata-fields` = dados dinâmicos (campos, external_labels)

**Mudanças necessárias:**
```python
# backend/api/settings.py

@router.get("/sites")
async def get_sites():
    """
    Retorna sites COM external_labels já integrados
    """
    sites = await get_sites_from_kv()
    
    # Buscar external_labels de /metadata-fields
    from api.metadata_fields_manager import _fields_config_cache
    fields_data = _fields_config_cache["data"]
    
    if fields_data:
        server_status = fields_data.get('extraction_status', {}).get('server_status', [])
        
        # Enriquecer sites com external_labels
        for site in sites:
            for server_info in server_status:
                if server_info['hostname'] == site.get('prometheus_host'):
                    site['external_labels'] = server_info.get('external_labels', {})
                    break
    
    return {"sites": sites}

@router.post("/sites/auto-fill")
async def auto_fill_prometheus_hosts():
    """
    Auto-preenche prometheus_host baseado em external_labels
    """
    # Lógica inteligente de matching
    pass
```

**Resultado:**
- ✅ `/settings` enriquecido com external_labels
- ✅ Frontend faz apenas `/settings/sites` (sem precisar de `/metadata-fields/servers`)
- ⚠️ Mantém duas APIs separadas

---

### 🟢 Novo Endpoint: Auto-fill Inteligente

**Criar:** `POST /settings/sites/auto-fill` ou `POST /metadata-fields/sites/auto-fill`

```python
@router.post("/sites/auto-fill")
async def auto_fill_prometheus_hosts():
    """
    Auto-preenche prometheus_host/port dos sites baseado em external_labels
    
    MATCHING INTELIGENTE:
    1. Procura external_labels.site === site.code
    2. Se não encontrar, procura external_labels.datacenter contém site.code
    3. Se não encontrar, procura external_labels.cluster contém site.code
    4. Retorna preview antes de aplicar
    """
    sites = await get_sites_from_kv()
    
    # Buscar servers com external_labels
    from api.metadata_fields_manager import load_fields_config
    fields_data = await load_fields_config()
    server_status = fields_data.get('extraction_status', {}).get('server_status', [])
    
    preview = []
    updates = []
    
    for site in sites:
        # Matching inteligente
        matched_server = None
        
        # Estratégia 1: site exato
        for server in server_status:
            if server.get('external_labels', {}).get('site') == site['code']:
                matched_server = server
                break
        
        # Estratégia 2: datacenter contém
        if not matched_server:
            for server in server_status:
                datacenter = server.get('external_labels', {}).get('datacenter', '')
                if site['code'] in datacenter.lower():
                    matched_server = server
                    break
        
        if matched_server:
            preview.append({
                "site_code": site['code'],
                "site_name": site['name'],
                "current_host": site.get('prometheus_host'),
                "new_host": matched_server['hostname'],
                "new_port": matched_server['port'],
                "matched_by": "exact_site" if matched_server.get('external_labels', {}).get('site') == site['code'] else "datacenter_fuzzy",
                "external_labels": matched_server.get('external_labels', {})
            })
            
            # Preparar update
            updates.append({
                "code": site['code'],
                "prometheus_host": matched_server['hostname'],
                "prometheus_port": matched_server['port']
            })
    
    return {
        "success": True,
        "preview": preview,
        "total_matches": len(updates),
        "total_sites": len(sites),
        "updates": updates  # Frontend pode aplicar via PUT /sites/{code}
    }
```

**Benefícios:**
- ✅ Preview antes de aplicar
- ✅ Matching inteligente (múltiplas estratégias)
- ✅ Feedback visual no frontend
- ✅ Single endpoint (não precisa fazer N requisições)

---

## 🎯 5. RECOMENDAÇÃO FINAL

### ⭐ PLANO RECOMENDADO: Opção A (Consolidação em `/metadata-fields`)

**Fase 1: Mover endpoints de sites**
1. Copiar CRUD de sites de `settings.py` para `metadata_fields_manager.py`
2. Adicionar `/metadata-fields/sites/*` com mesma lógica
3. Manter `/settings/sites/*` temporariamente (deprecated)
4. Atualizar frontend para usar novos endpoints

**Fase 2: Implementar auto-fill inteligente**
1. Criar `POST /metadata-fields/sites/auto-fill`
2. Lógica de matching com preview
3. Atualizar frontend com modal de confirmação

**Fase 3: Depreciar `/settings`**
1. Remover rota `/settings` do `app.py`
2. Remover arquivo `backend/api/settings.py`
3. Remover `frontend/src/pages/Settings.tsx`
4. Documentar migração

**Fase 4: Limpeza de KV**
1. Considerar mover `skills/eye/settings/sites` para `skills/eye/metadata/sites`
2. Namespace unificado: tudo em `skills/eye/metadata/*`
3. Migração automática no startup (one-time)

---

## 📦 6. ESTRUTURA FINAL PROPOSTA

```
Backend API
├── /api/v1/metadata-fields/
│   ├── GET  /                    # Lista campos
│   ├── PATCH /{name}             # Atualiza campo
│   ├── POST /force-extract       # Extração SSH
│   ├── GET  /sync-status         # Status sincronização
│   ├── POST /add-to-kv           # Adiciona ao KV
│   ├── POST /remove-orphans      # Remove órfãos
│   ├── GET  /servers             # Lista servidores (COM external_labels)
│   ├── GET  /sites               # Lista sites ← NOVO
│   ├── POST /sites               # Cria site ← NOVO
│   ├── PUT  /sites/{code}        # Atualiza site ← NOVO
│   ├── DELETE /sites/{code}      # Remove site ← NOVO
│   ├── POST /sites/auto-fill     # Auto-fill inteligente ← NOVO
│   └── GET  /naming-config       # Naming strategy ← NOVO

Frontend
└── MetadataFields.tsx
    ├── Aba 1: Campos de Meta (Relabel Configs)
    ├── Aba 2: External Labels (Global do Servidor)
    ├── Aba 3: Gerenciar Sites
    └── Aba 4: External Labels (Todos Servidores)

Consul KV
└── skills/eye/metadata/
    ├── fields.json        # Campos + external_labels
    └── sites.json         # Sites (migrado de settings/)
```

---

## 🚀 7. BENEFÍCIOS DA CONSOLIDAÇÃO

### Performance
- ✅ Cache único (5 minutos)
- ✅ Pre-warming único no startup
- ✅ Menos requisições HTTP (frontend faz menos calls)

### Manutenção
- ✅ Código em um único arquivo
- ✅ Lógica unificada (SSH, KV, cache)
- ✅ Menos redundância

### User Experience
- ✅ Página única (`MetadataFields.tsx`)
- ✅ Navegação mais intuitiva (4 abas relacionadas)
- ✅ Loading states consistentes

### Arquitetura
- ✅ Namespace unificado (`skills/eye/metadata/*`)
- ✅ API RESTful consistente
- ✅ Separação clara: extração (SSH) + gerenciamento (CRUD)

---

## 📝 8. PRÓXIMOS PASSOS

### Imediato (Hoje)
1. ✅ Análise completa (FEITO)
2. ⏳ **Decisão:** Opção A ou B?
3. ⏳ Planejar implementação

### Curto Prazo (Esta Semana)
1. Implementar novos endpoints em `/metadata-fields`
2. Criar endpoint `/sites/auto-fill`
3. Atualizar frontend para usar novos endpoints
4. Testes completos

### Médio Prazo (Próxima Semana)
1. Depreciar `/settings` API
2. Remover `Settings.tsx` do frontend
3. Migrar namespace KV
4. Documentação final

---

## 🤔 PERGUNTAS PARA DECISÃO

1. **Preferência de arquitetura:** Opção A (consolidar) ou B (manter separado)?
2. **Namespace KV:** Manter `skills/eye/settings/*` ou migrar para `skills/eye/metadata/*`?
3. **Auto-fill:** Implementar com preview ou aplicar direto?
4. **Deprecação:** Remover `/settings` imediatamente ou manter compatibilidade temporária?

**Aguardando instruções para prosseguir!** 🎯
