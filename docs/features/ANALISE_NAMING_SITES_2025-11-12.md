## ANÁLISE COMPLETA - NAMING E SITES - 12/11/2025

### 🔍 OBJETIVO
Mapear TODAS as referências a "naming" e "sites" no projeto para entender o contexto completo e identificar possíveis problemas após migração de Settings para MetadataFields.

---

## 📊 RESUMO EXECUTIVO

### Status Atual:
- ✅ **Endpoint `/api/v1/settings/naming-config`** - MANTIDO e funcionando
- ⚠️ **KV `skills/eye/settings/sites`** - PATH ANTIGO ainda usado em 1 script
- ✅ **KV `skills/eye/metadata/sites`** - PATH NOVO usado pela aplicação
- ✅ **Página MonitoringTypes** - NÃO usa sites (apenas servidores Prometheus)

### Ações Necessárias:
1. ⚠️ Migrar `populate_external_labels.py` para usar novo path do KV
2. ✅ Manter endpoint `naming-config` (usado em 5+ lugares)
3. ℹ️ MonitoringTypes não precisa de ajustes (não usa sites)

---

## 🗂️ MAPEAMENTO COMPLETO - NAMING

### 1. Backend - Arquivos Python

#### `backend/api/settings.py` (68 linhas)
**Status:** ✅ REFATORADO (apenas naming-config)
```python
@router.get("/naming-config")
async def get_naming_config():
    # Retorna: naming_strategy, suffix_enabled, default_site
    # Fonte: Variáveis de ambiente (.env)
```

**Usado por:**
- MetadataFields.tsx (linha 971)
- namingUtils.ts (linha 218)
- App.tsx (mount via loadNamingConfig)

---

#### `backend/core/naming_utils.py` (156 linhas)
**Status:** ✅ ATIVO E CRÍTICO
**Funcionalidade:** Lógica de sufixos automáticos em service names

**Funções principais:**
1. `apply_site_suffix(service_name, metadata)` - Aplica sufixo _site
2. `extract_site_from_metadata(metadata)` - Extrai site de Meta/external_labels
3. `get_naming_config()` - Retorna config de .env

**Usado por:**
- `api/services.py` (linhas 9, 399, 567)
- `api/blackbox_manager.py` (linhas 26, 483)
- `test_multisite_integration.py` (linha 13)

**Variáveis de ambiente lidas:**
```bash
NAMING_STRATEGY=option1|option2
SITE_SUFFIX_ENABLED=true|false
DEFAULT_SITE=palmas
```

**Lógica:**
- **option1:** Mesmo nome + filtros externos (sem sufixos)
- **option2:** Nomes diferentes com sufixos (_palmas, _rio, _dtc)

---

### 2. Frontend - Arquivos TypeScript/TSX

#### `frontend/src/utils/namingUtils.ts` (230 linhas)
**Status:** ✅ ATIVO E CRÍTICO
**Funcionalidade:** Lógica de nomenclatura multi-site no frontend

**Funções principais:**
1. `loadNamingConfig()` - Busca config do backend
2. `setNamingConfig()` / `getNamingConfig()` - Gerencia estado global
3. `calculateFinalServiceName()` - Aplica sufixos
4. `extractSiteFromMetadata()` - Extrai site do Meta
5. `getSiteBadgeColor()` - Cores dos badges de sites

**Usado por:**
- App.tsx (mount global)
- Services.tsx
- BlackboxTargets.tsx
- Exporters.tsx
- ServiceNamePreview.tsx
- SiteBadge.tsx

**Endpoint consumido:**
```typescript
const response = await fetch('/api/v1/settings/naming-config');
```

---

#### `frontend/src/pages/MetadataFields.tsx` (3392 linhas)
**Status:** ✅ ATIVO
**Uso de naming:**

**Linha 971-985:** Carrega naming config no mount
```typescript
const namingResponse = await fetch('/api/v1/settings/naming-config');
const namingData = await namingResponse.json();
setConfig({
  naming_strategy: namingData.naming_strategy,
  suffix_enabled: namingData.suffix_enabled,
  default_site: namingData.default_site,
  sites: sitesData.sites // Do novo endpoint metadata-fields
});
```

**Linhas 2630-2709:** Card de "Naming Strategy Multi-Site"
- Mostra strategy ativa (option1/option2)
- Explica como funciona
- Mostra variáveis de ambiente
- Lista páginas afetadas

---

### 3. Componentes que Usam Naming

#### `frontend/src/components/ServiceNamePreview.tsx`
**Função:** Preview do nome final com sufixo
**Importa:** `calculateFinalServiceName`, `getSiteBadgeColor`

#### `frontend/src/components/SiteBadge.tsx`
**Função:** Badge colorido de site
**Importa:** `getSiteBadgeColor`, `hasSiteSuffix`

---

## 🗂️ MAPEAMENTO COMPLETO - SITES

### 1. Backend - KV Paths

#### ⚠️ PATH ANTIGO: `skills/eye/settings/sites`
**Status:** DEPRECADO mas ainda usado em 1 lugar

**Onde aparece:**
```python
# backend/populate_external_labels.py (linhas 52, 82)
sites_data = await kv.get_json("skills/eye/settings/sites")  # ❌ PATH ANTIGO
await kv.put_json("skills/eye/settings/sites", {"sites": sites})  # ❌ PATH ANTIGO
```

**Problema:** Script usa path antigo que foi migrado

---

#### ✅ PATH NOVO: `skills/eye/metadata/sites`
**Status:** ATIVO (path correto)

**Onde é usado:**
```python
# backend/api/metadata_fields_manager.py (linhas 2390+)
kv_data = await kv.get_json('skills/eye/metadata/sites')  # ✅ PATH NOVO
await kv.put_json('skills/eye/metadata/sites', save_structure)  # ✅ PATH NOVO
```

**Endpoints que usam:**
- GET `/api/v1/metadata-fields/config/sites`
- PATCH `/api/v1/metadata-fields/config/sites/{code}`
- POST `/api/v1/metadata-fields/config/sites/sync`

---

### 2. Estrutura do KV Sites

**Estrutura Atual (CORRETA):**
```json
{
  "data": {
    "sites": [
      {
        "code": "palmas",
        "name": "Palmas - EDITADO",
        "is_default": true,
        "color": "green",
        "cluster": "palmas-master",
        "datacenter": "skillsit-palmas-to",
        "environment": "production",
        "site": "palmas",
        "prometheus_instance": "172.16.1.26",
        "prometheus_host": "172.16.1.26",
        "ssh_port": 5522,
        "prometheus_port": 9090
      }
    ],
    "meta": {
      "version": "2.0.0",
      "last_sync": "2025-11-12T...",
      "structure": "external_labels_at_root"
    }
  },
  "meta": {
    "created_at": "...",
    "updated_at": "...",
    "source": "auto_sync_from_extraction"
  }
}
```

---

## 📄 ANÁLISE - PÁGINA MONITORING TYPES

### Arquivo: `frontend/src/pages/MonitoringTypes.tsx` (625 linhas)

**Status:** ✅ NÃO USA SITES

**O que usa:**
- ✅ `ServerSelector` component (servidores Prometheus)
- ✅ API `/api/v1/monitoring-types-dynamic/from-prometheus`
- ✅ Parâmetro `?server=ALL` ou `?server=172.16.1.26`

**NÃO usa:**
- ❌ Sites do KV
- ❌ Naming strategy
- ❌ External labels de sites
- ❌ Endpoint `/settings/sites`

**Conclusão:** MonitoringTypes trabalha diretamente com servidores Prometheus, não com o conceito de "sites" da aplicação.

---

### Backend: `backend/api/monitoring_types_dynamic.py` (440 linhas)

**Status:** ✅ NÃO USA SITES

**Funcionalidade:**
- Extrai tipos de monitoramento do `prometheus.yml` via SSH
- Usa `MultiConfigManager` para acessar servidores
- NÃO usa sites do KV

**Endpoint:**
```
GET /api/v1/monitoring-types-dynamic/from-prometheus?server=ALL|<hostname>
```

**Resposta:**
```json
{
  "success": true,
  "categories": [...],
  "servers": {
    "172.16.1.26": { "types": [...] },
    "172.16.200.14": { "types": [...] }
  },
  "total_types": 45,
  "total_servers": 3
}
```

---

## 🔍 SCRIPTS E TESTES

### Scripts que Precisam de Ajuste:

#### 1. `backend/populate_external_labels.py` ⚠️
**Problema:** Usa path antigo do KV
**Linhas afetadas:** 52, 82

**ANTES:**
```python
sites_data = await kv.get_json("skills/eye/settings/sites")
await kv.put_json("skills/eye/settings/sites", {"sites": sites})
```

**DEVE SER:**
```python
sites_data = await kv.get_json("skills/eye/metadata/sites")
await kv.put_json("skills/eye/metadata/sites", {"sites": sites})
```

---

### Scripts que Estão Corretos:

#### ✅ `test_sites_consolidation.py`
- Testa endpoint `/settings/naming-config` (funciona)
- Testa endpoint `/metadata-fields/config/sites` (funciona)

#### ✅ `test_api_performance.py`
- Testa GET `/settings/naming-config`

#### ✅ `backend/test_multisite_integration.py`
- Testa `naming_utils.py` corretamente

---

## 📊 FLUXO DE DADOS - NAMING CONFIG

```
┌─────────────────────────────────────────────────────┐
│                    .env                             │
│  NAMING_STRATEGY=option2                            │
│  SITE_SUFFIX_ENABLED=true                           │
│  DEFAULT_SITE=palmas                                │
└────────────────┬────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────┐
│  backend/api/settings.py                            │
│  GET /api/v1/settings/naming-config                 │
│    → Lê variáveis de ambiente                       │
│    → Retorna JSON                                   │
└────────────────┬────────────────────────────────────┘
                 │
    ┌────────────┴────────────┐
    │                         │
    ▼                         ▼
┌─────────────┐      ┌──────────────────┐
│ App.tsx     │      │ MetadataFields   │
│ (mount)     │      │ (mount)          │
└──────┬──────┘      └────────┬─────────┘
       │                      │
       ▼                      ▼
┌─────────────────────────────────────┐
│  frontend/utils/namingUtils.ts      │
│  - loadNamingConfig()                │
│  - setNamingConfig(config)           │
│  - Armazena em memória               │
└─────────────┬───────────────────────┘
              │
     ┌────────┴─────────┬──────────┬──────────┐
     ▼                  ▼          ▼          ▼
┌──────────┐  ┌──────────────┐  ┌────────┐  ┌──────────┐
│ Services │  │ Blackbox     │  │Export. │  │ Preview  │
│          │  │ Targets      │  │        │  │ Component│
└──────────┘  └──────────────┘  └────────┘  └──────────┘
    │               │                │            │
    ▼               ▼                ▼            ▼
 Aplica sufixos em nomes de serviços conforme strategy
```

---

## 📊 FLUXO DE DADOS - SITES

```
┌─────────────────────────────────────────────────────┐
│  Extração de Campos (SSH → Prometheus.yml)          │
│  POST /api/v1/metadata-fields/force-extract          │
└────────────────┬────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────┐
│  backend/api/metadata_fields_manager.py             │
│  sync_sites_to_kv(server_status)                    │
│    → Extrai external_labels de cada servidor        │
│    → Cria/atualiza sites                            │
│    → Salva em skills/eye/metadata/sites             │
└────────────────┬────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────┐
│  Consul KV: skills/eye/metadata/sites               │
│  {                                                   │
│    "data": {                                         │
│      "sites": [                                      │
│        {                                             │
│          "code": "palmas",                           │
│          "name": "Palmas",                           │
│          "cluster": "palmas-master",                 │
│          "datacenter": "skillsit-palmas-to",         │
│          "prometheus_host": "172.16.1.26",           │
│          "ssh_port": 5522,                           │
│          "prometheus_port": 9090                     │
│        }                                             │
│      ]                                               │
│    }                                                 │
│  }                                                   │
└────────────────┬────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────┐
│  GET /api/v1/metadata-fields/config/sites           │
│    → Le skills/eye/metadata/sites                   │
│    → Retorna lista de sites                         │
└────────────────┬────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────┐
│  MetadataFields.tsx                                 │
│  - Aba "Gerenciar Sites"                            │
│  - Aba "External Labels"                            │
│  - Colunas "Descoberto Em" / "Origem"               │
└─────────────────────────────────────────────────────┘
```

---

## ⚠️ PROBLEMAS IDENTIFICADOS

### 1. Script `populate_external_labels.py` Usa Path Antigo
**Severidade:** 🟡 MÉDIA
**Impacto:** Script falha ao tentar popular external_labels

**Solução:**
```python
# MUDAR DE:
sites_data = await kv.get_json("skills/eye/settings/sites")
await kv.put_json("skills/eye/settings/sites", {"sites": sites})

# PARA:
sites_data = await kv.get_json("skills/eye/metadata/sites")
await kv.put_json("skills/eye/metadata/sites", {"sites": sites})

# E ajustar para estrutura com wrapper:
sites = kv_data.get('data', {}).get('sites', [])
```

---

## ✅ RECOMENDAÇÕES

### 1. Imediatas (Fazer Agora):
- ✅ Atualizar `populate_external_labels.py` para novo path do KV
- ✅ Ajustar para estrutura com wrapper `data`

### 2. Manter Como Está:
- ✅ Endpoint `/api/v1/settings/naming-config` (necessário)
- ✅ `naming_utils.py` backend e frontend (críticos)
- ✅ MonitoringTypes (não usa sites)

### 3. Monitorar:
- ℹ️ Uso de naming strategy em produção
- ℹ️ Performance de extração de sites
- ℹ️ Sincronização automática funcionando

---

## 📋 CHECKLIST DE VALIDAÇÃO

### Naming Config:
- [x] Endpoint `/settings/naming-config` funciona
- [x] App.tsx carrega config no mount
- [x] MetadataFields mostra card de Naming Strategy
- [x] Services aplica sufixos corretamente
- [x] Blackbox aplica sufixos corretamente

### Sites:
- [x] Sites são criados automaticamente na extração
- [x] Sites preservam edições do usuário
- [x] External labels são extraídos corretamente
- [x] Colunas "Descoberto Em" / "Origem" funcionam
- [ ] Script `populate_external_labels.py` usa path correto

### MonitoringTypes:
- [x] Página funciona independentemente de sites
- [x] Extração via SSH funciona
- [x] Nenhum ajuste necessário

---

## 🎯 CONCLUSÃO

### Status Geral: ✅ BOM (1 ajuste necessário)

**Naming Strategy:**
- ✅ Funcionando perfeitamente
- ✅ Endpoint mantido e usado corretamente
- ✅ Lógica frontend/backend sincronizada

**Sites:**
- ✅ Migração bem-sucedida para metadata-fields
- ✅ Auto-sync funcionando
- ⚠️ 1 script precisa de ajuste (populate_external_labels.py)

**MonitoringTypes:**
- ✅ Nenhum problema identificado
- ✅ Não depende de sites

**Próxima Ação:**
Corrigir `populate_external_labels.py` para usar `skills/eye/metadata/sites`
