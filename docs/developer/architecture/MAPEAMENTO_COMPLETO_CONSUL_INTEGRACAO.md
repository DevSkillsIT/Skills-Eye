# 🔍 MAPEAMENTO COMPLETO - INTEGRAÇÕES CONSUL
**Data:** 15/11/2025 (REVISADO - Análise Ampliada)  
**Objetivo:** Identificar TODAS as integrações com Consul no projeto (não apenas `get_all_services_from_all_nodes()`)

---

## 📊 RESUMO EXECUTIVO

### Escopo da Análise AMPLIADO
✅ **TODOS** os arquivos que interagem com Consul API  
✅ **TODAS** as operações: services, KV, health, catalog, agent  
✅ **TODOS** os endpoints HTTP (não apenas funções específicas)  
✅ **TODAS** as bibliotecas e managers que usam ConsulManager  

### Estatísticas Completas
- 🔴 **35 métodos** diretos do ConsulManager que fazem `self._request()`
- 🔴 **22 APIs** (routers) que expõem dados do Consul
- 🔴 **200+ ocorrências** de chamadas Consul no código
- 🔴 **8 managers/libraries** que dependem do ConsulManager
- 🔴 **15+ operações** diferentes (services, KV, health, catalog, etc)

### Impacto da Otimização
- 🎯 **CRÍTICO:** Qualquer mudança em `_request()` afeta TUDO
- 🎯 **CRÍTICO:** Timeout, retry, error handling impactam 35 métodos
- 🟡 **ALTO:** Performance de KV operations (usado por metadata, presets, etc)
- � **ALTO:** Consistência de dados entre Agent API vs Catalog API
- 🟢 **MÉDIO:** Frontend depende indiretamente via endpoints backend

---

## 🏗️ ARQUITETURA CONSUL NO PROJETO

### ConsulManager - Classe Central (`backend/core/consul_manager.py`)
**Localização:** Linha 1-938 (938 linhas total)  
**Função:** Biblioteca central que gerencia TODAS as interações com Consul API

#### Métodos HTTP Diretos (35 operações via `self._request()`)

**AGENT API (Operações Locais - Fast)**
```python
# Linha 112: GET /agent/services - Listar serviços locais (5-10ms)
# Linha 121: GET /internal/ui/services - UI overview
# Linha 215: GET /agent/host - Informações do host
# Linha 260: GET /agent/members - Listar membros do cluster
# Linha 299: GET /agent/services - Buscar serviços (com node_addr)
# Linha 311: PUT /agent/service/register - Registrar serviço
# Linha 324: PUT /agent/service/deregister/{id} - Remover serviço
# Linha 488: GET /agent/checks - Listar health checks
```

**CATALOG API (Operações Globais - Slower)**
```python
# Linha 149: GET /catalog/services - Listar TODOS serviços do cluster
# Linha 350: GET /catalog/services - Get catalog services
# Linha 424: GET /catalog/service/{name} - Detalhes de serviço específico
# Linha 444: GET /catalog/datacenters - Listar datacenters
# Linha 452: GET /catalog/nodes - Listar nodes
# Linha 460: GET /catalog/node/{name} - Detalhes de node específico
# Linha 725: GET /catalog/services - (get_all_services_from_all_nodes)
# Linha 734: GET /catalog/service/{name} - (loop em get_all_services_from_all_nodes)
```

**HEALTH API (Status e Checks)**
```python
# Linha 160: GET /health/service/{name} - Health de serviço específico
# Linha 340: GET /health/service/{name} - Get health status
# Linha 342: GET /health/state/any - Health geral
# Linha 477: GET /health/service/{name} - Com parâmetros
# Linha 486: GET /health/checks/{id} - Health checks de serviço
```

**KEY-VALUE API (Storage Persistente)**
```python
# Linha 496: GET /kv/{key} - Ler valor
# Linha 504: PUT /kv/{key} - Escrever valor
# Linha 512: DELETE /kv/{key} - Deletar chave
# Linha 520: GET /kv/{prefix}?keys - Listar chaves
# Linha 528: GET /kv/{key} - Ler JSON
# Linha 558: PUT /kv/{key} - Escrever JSON
# Linha 577: GET /kv/{prefix}?recurse=true - Árvore completa
```

**OUTRAS OPERAÇÕES**
```python
# Linha 58: GET /status/leader - Verificar líder (usado em testes)
```

---

## 🔗 DEPENDÊNCIAS DO CONSULMANAGER

### 8 Libraries/Managers que Usam ConsulManager

| Manager | Arquivo | Inicialização | Uso Principal |
|---------|---------|---------------|---------------|
| **KVManager** | `core/kv_manager.py:46` | `ConsulManager()` | Wrapper KV operations |
| **BlackboxManager** | `core/blackbox_manager.py:47` | `ConsulManager()` | Blackbox targets CRUD |
| **ServicePresetManager** | `core/service_preset_manager.py:34` | `ConsulManager()` | Service templates |
| **ReferenceValuesManager** | `core/reference_values_manager.py:67` | `ConsulManager()` | Auto-cadastro valores |
| **FieldsExtractionService** | `core/fields_extraction_service.py:77` | `consul_manager` param | Extração campos Prometheus |
| **MonitoringTypeManager** | `core/monitoring_type_manager.py:29` | `consul_client` param | Tipos de monitoramento |
| **ConsulInsights** | `api/consul_insights.py:21` | `ConsulManager()` | Métricas e insights |
| **MonitoringUnified** | `api/monitoring_unified.py:38` | `ConsulManager()` (global) | Endpoint unificado |

---

## 🔴 ARQUIVOS CRÍTICOS (USAM `get_all_services_from_all_nodes()`)

### 1. `backend/api/monitoring_unified.py` ⭐ **MAIS CRÍTICO**
**Linha:** 214  
**Função:** `get_monitoring_data(category: str)`  
**Uso:**
```python
all_services_dict = await consul_manager.get_all_services_from_all_nodes()

# Converter estrutura aninhada para lista plana
all_services = []
for node_name, services_dict in all_services_dict.items():
    for service_id, service_data in services_dict.items():
        service_data['Node'] = node_name
        service_data['ID'] = service_id
        all_services.append(service_data)
```

**Impacto da Mudança:**
- ❌ **BLOQUEANTE:** Se retorno mudar de `Dict[node, Dict[id, service]]` para formato diferente
- ✅ **OK:** Se mantiver mesma estrutura (apenas otimizar internamente)

**Teste Obrigatório:**
```bash
# Endpoint usado pelo frontend principal (network-probes, web-probes, etc)
curl -s "http://localhost:5000/api/v1/monitoring/data?category=network-probes" | jq '.success'
# Esperado: true + array de serviços
```

**Páginas Frontend Afetadas:**
- `/monitoring/network-probes` (DynamicMonitoringPage.tsx)
- `/monitoring/web-probes`
- `/monitoring/system-exporters`
- `/monitoring/database-exporters`

---

### 2. `backend/api/services.py` ⭐ **CRÍTICO**
**Linha 54:** Endpoint `GET /api/v1/services/` (node_addr="ALL")  
**Linha 248:** Endpoint `POST /api/v1/services/search`

**Uso Linha 54:**
```python
if node_addr == "ALL":
    logger.info("Listando serviços de todos os nós do cluster")
    all_services = await consul.get_all_services_from_all_nodes()
    
    # Aplicar filtros se especificados
    if any([module, company, project, env]):
        filtered_services = {}
        for node_name, services in all_services.items():
            filtered_node_services = {}
            for service_id, service_data in services.items():
                # ...filtrar por metadata
```

**Uso Linha 248:**
```python
# Buscar em todos os nós
all_services = await consul.get_all_services_from_all_nodes()
filtered = {}

for node_name, services in all_services.items():
    node_filtered = {}
    for service_id, service_data in services.items():
        meta = service_data.get("Meta", {})
        matches = all(meta.get(k) == v for k, v in filters.items())
        if matches:
            node_filtered[service_id] = service_data
```

**Impacto da Mudança:**
- ❌ **BLOQUEANTE:** Espera estrutura aninhada `{node: {id: service}}`
- ⚠️ **ATENÇÃO:** Usado pela página DEPRECATED `Services.tsx`

**Teste Obrigatório:**
```bash
# Listar todos (sem filtro)
curl -s "http://localhost:5000/api/v1/services/?node_addr=ALL" | jq '.total'

# Buscar com filtros
curl -X POST "http://localhost:5000/api/v1/services/search" \
  -H "Content-Type: application/json" \
  -d '{"module": "icmp"}' | jq '.total'
```

**Páginas Frontend Afetadas:**
- `/services` (Services.tsx - **DEPRECATED, será removida**)

---

### 3. `backend/core/blackbox_manager.py` 🟡 **MÉDIO**
**Linha:** 142  
**Função:** `_fetch_blackbox_services()`

**Uso:**
```python
async def _fetch_blackbox_services(self) -> List[Dict[str, Any]]:
    """Returns the raw Consul service entries for blackbox exporters across the cluster."""
    all_services = await self.consul.get_all_services_from_all_nodes()
    results: List[Dict[str, Any]] = []

    for node_name, services in (all_services or {}).items():
        for service in (services or {}).values():
            if service.get("Service") != "blackbox_exporter":
                continue
            entry = service.copy()
            entry["Node"] = node_name
            results.append(entry)

    if not results:
        # Fallback to local agent if cluster query failed
        response = await self.consul.query_agent_services('Service == "blackbox_exporter"')
```

**Impacto da Mudança:**
- ✅ **OK:** Tem fallback se retornar vazio
- ⚠️ **ATENÇÃO:** Filtra apenas `Service == "blackbox_exporter"`

**Teste Obrigatório:**
```bash
# Verificar se blackbox_manager ainda funciona
curl -s "http://localhost:5000/api/v1/blackbox/targets" | jq '.total'
```

**Páginas Frontend Afetadas:**
- `/blackbox/targets` (BlackboxTargets.tsx - **DEPRECATED**)

---

### 4. `backend/test_categorization_debug.py` 🟢 **BAIXO (Script de Teste)**
**Linha:** 23  
**Uso:**
```python
all_services = await consul_manager.get_all_services_from_all_nodes()
```

**Impacto:** Script de debug, não afeta produção.

---

## 🟡 ARQUIVOS COM CHAMADAS INDIRETAS (VIA `get_services()`)

### Funções do ConsulManager que NÃO precisam mudar
Estas funções já usam Agent API local (`/agent/services`) e estão corretas:

#### `async def get_services(self, node_addr: str = None)` - Linha 291
**API:** `/agent/services` (local)  
**Performance:** ~5-10ms  
**Uso:** Buscar serviços de 1 node específico

**Chamadas:**
1. `backend/api/services.py:95` - Listar serviços de 1 node
2. `backend/api/services.py:230` - Buscar em node específico
3. `backend/api/nodes.py:95` - Listar serviços por node
4. `backend/api/config.py:150` - Testar conexão
5. `backend/api/service_tags.py:73` - Listar tags
6. `backend/api/search.py` (7 ocorrências) - Busca local
7. `backend/api/prometheus_config.py:366, 718` - Geração config

**Status:** ✅ **NÃO PRECISA ALTERAR** (já usa Agent API local, rápida)

---

#### `async def get_members(self)` - Linha 257
**API:** `/agent/members`  
**Performance:** ~10-20ms  
**Uso:** Listar nodes do cluster

**Chamadas:**
1. `backend/api/config.py:149` - Listar nodes disponíveis
2. `backend/api/nodes.py:31` - Endpoint `/nodes/`

**Status:** ✅ **NÃO PRECISA ALTERAR** (lista nodes, não serviços)

---

## 📋 TODOS OS ENDPOINTS BACKEND (22 APIs)

### 🔴 CRÍTICOS - Endpoints que Consultam Consul Services

| Endpoint | Arquivo | Operação Consul | Linha | Impacto |
|----------|---------|-----------------|-------|---------|
| `GET /api/v1/monitoring/data` | `monitoring_unified.py` | `get_all_services_from_all_nodes()` | 214 | 🔴 **CRÍTICO** |
| `GET /api/v1/services/` | `services.py` | `get_all_services_from_all_nodes()` | 54 | 🔴 **CRÍTICO** |
| `POST /api/v1/services/search` | `services.py` | `get_all_services_from_all_nodes()` | 248 | 🔴 **CRÍTICO** |
| `GET /api/v1/blackbox/targets` | `blackbox_manager.py` | `get_all_services_from_all_nodes()` | 142 | � **CRÍTICO** |
| `GET /api/v1/services/` | `services.py` | `get_services(node_addr)` | 95 | 🟡 **ALTO** |
| `POST /api/v1/search/*` | `search.py` | `get_services()` | 110+ | 🟡 **ALTO** |
| `GET /api/v1/nodes/{addr}/services` | `nodes.py` | `get_services(node_addr)` | 95 | 🟡 **ALTO** |
| `GET /api/v1/service-tags/` | `service_tags.py` | `get_services()` | 73 | 🟡 **ALTO** |
| `GET /api/v1/prometheus/config` | `prometheus_config.py` | `get_services()` | 366 | 🟡 **ALTO** |

### 🟢 SEGUROS - Endpoints que Usam Apenas KV Store

| Endpoint | Arquivo | Operação Consul | Linha | Impacto |
|----------|---------|-----------------|-------|---------|
| `GET /api/v1/kv/tree/{prefix}` | `kv.py` | `get_kv_tree()` | 89 | 🟢 **BAIXO** |
| `GET /api/v1/kv/{key}` | `kv.py` | `get_kv_json()` | 102 | 🟢 **BAIXO** |
| `PUT /api/v1/kv/` | `kv.py` | `put_kv_json()` | 117 | 🟢 **BAIXO** |
| `DELETE /api/v1/kv/{key}` | `kv.py` | `delete_key()` | 132 | 🟢 **BAIXO** |
| `GET /api/v1/presets/` | `presets.py` | KV via `ServicePresetManager` | - | 🟢 **BAIXO** |
| `GET /api/v1/metadata-fields/` | `metadata_fields_manager.py` | KV via `MultiConfigManager` | - | 🟢 **BAIXO** |
| `GET /api/v1/reference-values/` | `reference_values.py` | KV + services | - | 🟢 **BAIXO** |
| `GET /api/v1/categorization-rules/` | `categorization_rules.py` | KV only | - | 🟢 **BAIXO** |
| `GET /api/v1/kv/audit` | `audit.py` | KV tree audit logs | - | 🟢 **BAIXO** |

### 🔵 UTILITÁRIOS - Endpoints de Configuração/Health

| Endpoint | Arquivo | Operação Consul | Linha | Impacto |
|----------|---------|-----------------|-------|---------|
| `GET /api/v1/nodes/` | `nodes.py` | `get_members()` | 31 | 🔵 **INFO** |
| `GET /api/v1/config/test` | `config.py` | `get_services()` + `get_members()` | 150 | 🔵 **INFO** |
| `GET /api/v1/health/` | `health.py` | `get_health_status()` | 17 | 🔵 **INFO** |
| `GET /api/v1/consul/host-metrics` | `consul_insights.py` | `get_host_info()` | - | 🔵 **INFO** |
| `GET /api/v1/consul/services-overview` | `consul_insights.py` | `get_services_overview()` | - | 🔵 **INFO** |
| `GET /api/v1/dashboard/stats` | `dashboard.py` | Catalog API direta | 70 | 🔵 **INFO** |
| `GET /api/v1/services-optimized/` | `services_optimized.py` | Catalog API direta | 80 | 🔵 **INFO** |

### ⚠️ DEPRECADOS - Endpoints que Serão Removidos

| Endpoint | Arquivo | Status | Remover? |
|----------|---------|--------|----------|
| `POST /api/v1/installer/` | `installer.py` | Obsoleto | ✅ Mover para instalador externo |
| Vários em `installer_old.py` | `obsolete/installer_old.py` | Deprecated | ✅ Já em pasta obsolete |

---

## 🎨 COMPONENTES FRONTEND MAPEADOS

### Páginas que consomem `/api/v1/monitoring/data` ⭐ **CRÍTICAS**

| Página | Arquivo | Categoria | Status |
|--------|---------|-----------|--------|
| Network Probes | `DynamicMonitoringPage.tsx` | `network-probes` | ✅ **ATIVA** |
| Web Probes | `DynamicMonitoringPage.tsx` | `web-probes` | ✅ **ATIVA** |
| System Exporters | `DynamicMonitoringPage.tsx` | `system-exporters` | ✅ **ATIVA** |
| Database Exporters | `DynamicMonitoringPage.tsx` | `database-exporters` | ✅ **ATIVA** |

**API Call (linha 541):**
```typescript
const axiosResponse = await consulAPI.getMonitoringData(
  category,
  filters,
  advancedSearchConditions
);
```

**Teste Frontend:**
```bash
# Abrir cada página e verificar:
# 1. http://localhost:8081/monitoring/network-probes
# 2. http://localhost:8081/monitoring/web-probes
# 3. http://localhost:8081/monitoring/system-exporters
# 4. http://localhost:8081/monitoring/database-exporters

# Console deve ter 0 erros
# Tabela deve renderizar com dados
```

---

### Páginas DEPRECATED (usam `/api/v1/services`) 🟡 **MÉDIO**

| Página | Arquivo | Endpoint | Remover? |
|--------|---------|----------|----------|
| Services | `Services.tsx:518` | `/services/?node_addr=ALL` | ✅ **SIM** (em breve) |
| Exporters | `Exporters.tsx` | `/services/?module=*` | ✅ **SIM** |
| Blackbox Targets | `BlackboxTargets.tsx` | `/blackbox/targets` | ✅ **SIM** |

**Nota:** Estas páginas serão removidas conforme `ANALISE_CONSUL_ARQUITETURA_DESCOBERTA.md`. Não investir tempo em otimizações.

---

## 🧪 PLANO DE TESTES COMPLETO

### FASE 1: Testes Backend Unitários
```bash
cd /home/adrianofante/projetos/Skills-Eye/backend

# Teste 1: Suite completa
python test_phase1.py
python test_phase2.py
python test_full_field_resilience.py

# Resultado esperado: TODOS passando
```

### FASE 2: Testes Backend - Endpoints Críticos
```bash
# Teste 2.1: Monitoring Data (MAIS CRÍTICO)
curl -s "http://localhost:5000/api/v1/monitoring/data?category=network-probes" | jq '{success, total: (.data | length)}'
# Esperado: {"success": true, "total": 100+}

# Teste 2.2: Services (ALL nodes)
curl -s "http://localhost:5000/api/v1/services/?node_addr=ALL" | jq '{success, total}'
# Esperado: {"success": true, "total": 100+}

# Teste 2.3: Services Search
curl -X POST "http://localhost:5000/api/v1/services/search" \
  -H "Content-Type: application/json" \
  -d '{"module": "icmp"}' | jq '{success, total}'
# Esperado: {"success": true, "total": 50+}

# Teste 2.4: Blackbox Targets
curl -s "http://localhost:5000/api/v1/blackbox/targets" | jq '{success, total}'
# Esperado: {"success": true, "total": 20+}
```

### FASE 3: Testes Frontend - Smoke Test
```bash
# Abrir navegador e testar manualmente:

# 1. Network Probes
open http://localhost:8081/monitoring/network-probes
# Verificar: Tabela carrega, filtros funcionam, 0 erros console

# 2. Web Probes
open http://localhost:8081/monitoring/web-probes
# Verificar: Tabela carrega, filtros funcionam, 0 erros console

# 3. System Exporters
open http://localhost:8081/monitoring/system-exporters
# Verificar: Tabela carrega, filtros funcionam, 0 erros console

# 4. Services (DEPRECATED - apenas smoke)
open http://localhost:8081/services
# Verificar: Não quebrou (pode ter warning "deprecated")
```

### FASE 4: Testes de Performance
```bash
# Teste 4.1: Latência com todos nodes ONLINE
time curl -s "http://localhost:5000/api/v1/monitoring/data?category=network-probes" > /dev/null
# Esperado: <100ms (real time)

# Teste 4.2: Latência com master OFFLINE (simular)
# 1. Editar sites.json - trocar IP master para 192.0.2.1 (inválido)
# 2. Reiniciar backend
# 3. Executar:
time curl -s "http://localhost:5000/api/v1/monitoring/data?category=network-probes" > /dev/null
# Esperado: <2.5s (timeout 2s + 1 sucesso)

# 4. Restaurar sites.json original
```

### FASE 5: Testes de Regressão (Garantir que nada quebrou)
```bash
# Teste 5.1: Endpoints locais (não devem ter mudado)
curl -s "http://localhost:5000/api/v1/services/?node_addr=172.16.1.26" | jq '.success'
# Esperado: true

curl -s "http://localhost:5000/api/v1/nodes/" | jq '.success'
# Esperado: true

curl -s "http://localhost:5000/api/v1/prometheus/config" | jq '. | length'
# Esperado: > 0

# Teste 5.2: Health Check
curl -s "http://localhost:5000/health" | jq '.healthy'
# Esperado: true
```

---

## ⚠️ CHECKLIST DE VALIDAÇÃO PRÉ-MERGE

Antes de fazer merge da otimização `get_all_services_from_all_nodes()`, validar:

### Backend
- [ ] Função mantém MESMA ASSINATURA de retorno: `Dict[str, Dict[str, Any]]`
- [ ] Estrutura aninhada preservada: `{node_name: {service_id: service_data}}`
- [ ] Campo `Node` adicionado em cada `service_data` (usado pelo frontend)
- [ ] Timeout total máximo: 6s (3 nodes × 2s)
- [ ] Logs informativos em cada tentativa (sucesso/timeout/erro)
- [ ] Métricas Prometheus implementadas

### Testes
- [ ] `test_phase1.py` → ✅ PASS
- [ ] `test_phase2.py` → ✅ PASS
- [ ] `test_full_field_resilience.py` → ✅ 8/8 PASS
- [ ] Endpoint `/monitoring/data?category=network-probes` → 200 OK
- [ ] Endpoint `/services/?node_addr=ALL` → 200 OK
- [ ] Endpoint `/services/search` → 200 OK
- [ ] Endpoint `/blackbox/targets` → 200 OK

### Frontend
- [ ] `/monitoring/network-probes` carrega sem erros
- [ ] `/monitoring/web-probes` carrega sem erros
- [ ] `/monitoring/system-exporters` carrega sem erros
- [ ] Console browser: 0 erros TypeError
- [ ] Tabelas renderizam colunas corretamente
- [ ] Filtros metadata funcionam

### Performance
- [ ] Latência com todos online: <100ms
- [ ] Latência com master offline: <2.5s
- [ ] Latência com todos offline: erro 503 em <6s

---

## 📚 REFERÊNCIAS CRUZADAS

### Documentos Relacionados
1. `ANALISE_CONSUL_ARQUITETURA_DESCOBERTA.md` - Análise completa da arquitetura
2. `PLANO_CORRECOES_MELHORIAS_CLAUDE_CODE.md` - Plano de implementação
3. `ERROS_ENCONTRADOS_CLAUDE_CODE.md` - Problemas identificados
4. `CLAUDE.md` - Instruções para IA (seção Consul)

### Commits Relevantes
- `e8d3f0c` - Fix useEffect columnConfig (frontend)
- `736d50e` - Implementação Catalog API (Claude Code)
- `4be3934` - Documento análise Consul

### Issues/PRs Relacionadas
- PR pendente: `fix/consul-agent-refactor-20251114` (Claude Code trabalhando)

---

---

## 🚨 PONTOS DE ATENÇÃO CRÍTICOS

### 1. Timeout Global (`_request()` linha 85)
**Atual:** `timeout=5` segundos  
**Impacto:** TODAS as 35 operações Consul usam este timeout  
**Risco:** Se aumentar/diminuir, afeta TUDO (services, KV, health, catalog)

**Operações afetadas:**
- ✅ Agent API (local): 5s é generoso (responde em ~5-10ms)
- ⚠️ Catalog API (global): 5s pode ser justo se cluster grande
- 🔴 KV operations: 5s pode causar timeout em get_kv_tree grandes

**Recomendação:**
- Manter 5s para Agent/Catalog
- Considerar timeout variável para KV tree operations (10-15s)

---

### 2. Retry Logic (`@retry_with_backoff` linha 23)
**Atual:** max_retries=3, base_delay=1s, max_delay=10s  
**Impacto:** TODAS as operações Consul fazem retry automático

**Comportamento:**
```python
# Tentativa 1: Falha → aguarda 1s
# Tentativa 2: Falha → aguarda 2s  
# Tentativa 3: Falha → aguarda 4s
# Total: 7s adicionais em caso de falha
```

**Risco:**
- 🔴 `get_all_services_from_all_nodes()` com 3 nodes offline:
  - Timeout 5s × 3 retries = 15s por node
  - 15s × 3 nodes = **45s total** (INACEITÁVEL)

**Recomendação:**
- Reduzir max_retries para operações de cluster (1-2 ao invés de 3)
- Usar retry mais agressivo apenas para KV operations críticas

---

### 3. Agent API vs Catalog API (Consistência)
**Problema:** Código mistura ambas APIs sem critério claro

**Agent API (`/agent/services`):**
- ✅ Rápida: ~5-10ms
- ✅ Cache local mantido via Gossip
- ❌ Vista local do node (mas replicada via Gossip)

**Catalog API (`/catalog/services`):**
- ❌ Mais lenta: ~50ms
- ✅ Vista global consolidada
- ❌ Requer query no servidor

**Arquivos com MISTURA problemática:**
- `consul_manager.py:725` - usa Catalog em `get_all_services_from_all_nodes()`
- `consul_manager.py:299` - usa Agent em `get_services()`
- `consul_manager.py:779` - fallback Agent quando Catalog falha

**Recomendação:**
- **REGRA:** Agent API para queries frequentes/rápidas
- **REGRA:** Catalog API apenas quando precisa vista consolidada garantida
- **IMPLEMENTAR:** Estratégia fail-fast: Agent primeiro, Catalog como fallback

---

### 4. KV Operations em Loop (Performance)
**Problema:** Várias operações fazem loops sobre KV sem batch

**Exemplos:**
- `kv_manager.py:164` - `get_kv_tree()` pode retornar 1000+ chaves
- `metadata_fields_manager.py` - extrai campos de múltiplos Prometheus
- `reference_values_manager.py` - auto-cadastro em loop

**Risco:**
- 🔴 1000 chaves × 5s timeout = potencial travamento
- 🔴 Sem paralelização = lento demais

**Recomendação:**
- Usar `?recurse=true` para pegar árvore de uma vez
- Implementar batch operations onde possível
- Adicionar pagination para KV tree grandes

---

### 5. Error Handling Inconsistente
**Problema:** Alguns arquivos tratam erros, outros não

**Bom (monitoring_unified.py:214):**
```python
try:
    all_services_dict = await consul_manager.get_all_services_from_all_nodes()
except Exception as e:
    logger.error(f"Erro: {e}")
    raise HTTPException(status_code=503, detail="Consul indisponível")
```

**Ruim (search.py:110):**
```python
# Sem try/except - se Consul cair, endpoint quebra silenciosamente
services_dict = await consul.get_services()
```

**Recomendação:**
- Padronizar error handling em TODOS endpoints
- Retornar HTTPException 503 com detalhe quando Consul falhar
- Implementar circuit breaker para evitar cascata de falhas

---

### 6. Falta de Métricas/Observabilidade
**Problema:** ZERO instrumentação nas operações Consul

**O que está faltando:**
- ❌ Nenhuma métrica Prometheus sobre latência Consul
- ❌ Nenhum log estruturado de performance
- ❌ Nenhum contador de erros/sucessos
- ❌ Nenhum alerta quando Consul degrada

**Recomendação URGENTE:**
```python
from prometheus_client import Histogram, Counter

consul_request_duration = Histogram(
    'consul_request_duration_seconds',
    'Latência de requests ao Consul',
    ['method', 'endpoint', 'operation']
)

consul_errors_total = Counter(
    'consul_errors_total',
    'Total de erros Consul',
    ['method', 'endpoint', 'error_type']
)
```

---

### 7. Dependência Circular Potencial
**Problema:** KVManager depende de ConsulManager que pode depender de KV

**Arquivos com risco:**
- `kv_manager.py:46` - `self.consul = ConsulManager()`
- `consul_manager.py` - pode precisar ler config do KV
- `multi_config_manager.py` - mistura Consul services + KV

**Recomendação:**
- Revisar arquitetura para evitar circular imports
- Separar concerns: ConsulManager para API, KVManager para storage

---

## 🎯 PRÓXIMOS PASSOS

1. **Aguardar conclusão** do Claude Code no SPRINT 1
2. **Revisar PR** com foco nos 4 arquivos críticos
3. **Executar bateria completa** de testes (FASE 1-5)
4. **Validar performance** antes/depois
5. **Merge** apenas se TODOS os critérios atendidos
6. **Monitorar** produção por 24h após deploy

---

**FIM DO MAPEAMENTO**

**Última atualização:** 15/11/2025  
**Responsável:** GitHub Copilot (análise automática)  
**Validação:** Pendente (aguardar PR do Claude Code)
