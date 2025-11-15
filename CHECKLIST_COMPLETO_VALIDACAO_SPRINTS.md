# ✅ CHECKLIST COMPLETO DE VALIDAÇÃO - SPRINTS 1 E 2

**Data de Criação:** 2025-11-15
**Objetivo:** Validar TUDO que foi mencionado nos documentos de SPRINT 1 e SPRINT 2
**Como Usar:** Marque [x] conforme valida cada item no código

---

## 📚 ÍNDICE

- [SPRINT 1 - BACKEND](#sprint-1---backend)
- [SPRINT 1 - FRONTEND](#sprint-1---frontend)
- [SPRINT 1 - CORREÇÕES PÓS-IMPLEMENTAÇÃO](#sprint-1---correções-pós-implementação)
- [SPRINT 2 - BACKEND](#sprint-2---backend)
- [SPRINT 2 - FRONTEND](#sprint-2---frontend)
- [CORREÇÕES CRÍTICAS PÓS-SPRINT 2](#correções-críticas-pós-sprint-2)
- [TESTES DE VALIDAÇÃO](#testes-de-validação)

---

## SPRINT 1 - BACKEND

### 📁 Arquivo: `backend/requirements.txt`

- [ ] **Dependência prometheus-client adicionada**
  - Arquivo: `backend/requirements.txt`
  - Linha: 26
  - Deve conter: `prometheus-client==0.21.0`
  - Validação: `grep "prometheus-client" backend/requirements.txt`

---

### 📁 Arquivo: `backend/core/metrics.py` (NOVO)

- [ ] **Arquivo metrics.py foi criado**
  - Arquivo: `backend/core/metrics.py`
  - Deve existir
  - Validação: `ls backend/core/metrics.py`

- [ ] **Import prometheus_client no topo**
  - Arquivo: `backend/core/metrics.py`
  - Linhas: 1-11
  - Deve importar: `Histogram, Counter, Gauge, Info`
  - Validação: `grep "from prometheus_client import" backend/core/metrics.py`

- [ ] **Métrica consul_request_duration (Histogram)**
  - Arquivo: `backend/core/metrics.py`
  - Linhas: ~13-16
  - Deve ter labels: `['method', 'endpoint', 'node']`
  - Nome: `consul_request_duration_seconds`
  - Validação: `grep "consul_request_duration_seconds" backend/core/metrics.py`

- [ ] **Métrica consul_requests_total (Counter)**
  - Arquivo: `backend/core/metrics.py`
  - Linhas: ~18-22
  - Deve ter labels: `['method', 'endpoint', 'node', 'status']`
  - Nome: `consul_requests_total`
  - Validação: `grep "consul_requests_total" backend/core/metrics.py`

- [ ] **Métrica consul_nodes_available (Gauge)**
  - Arquivo: `backend/core/metrics.py`
  - Linhas: ~24-27
  - Nome: `consul_nodes_available`
  - Descrição: Número de nodes Consul disponíveis
  - Validação: `grep "consul_nodes_available" backend/core/metrics.py`

- [ ] **Métrica consul_fallback_total (Counter)**
  - Arquivo: `backend/core/metrics.py`
  - Linhas: ~29-33
  - Deve ter labels: `['from_node', 'to_node']`
  - Nome: `consul_fallback_total`
  - Validação: `grep "consul_fallback_total" backend/core/metrics.py`

- [ ] **Métrica consul_cache_hits (Counter)**
  - Arquivo: `backend/core/metrics.py`
  - Linhas: ~41-45
  - Deve ter labels: `['endpoint', 'age_bucket']`
  - Nome: `consul_cache_hits_total`
  - Comentário menciona: SPRINT 1 CORREÇÕES (2025-11-15)
  - Validação: `grep "consul_cache_hits_total" backend/core/metrics.py`

- [ ] **Métrica consul_stale_responses (Counter)**
  - Arquivo: `backend/core/metrics.py`
  - Linhas: ~47-51
  - Deve ter labels: `['endpoint', 'lag_bucket']`
  - Nome: `consul_stale_responses_total`
  - Comentário menciona: SPRINT 1 CORREÇÕES
  - Validação: `grep "consul_stale_responses_total" backend/core/metrics.py`

- [ ] **Métrica consul_api_type (Counter)**
  - Arquivo: `backend/core/metrics.py`
  - Linhas: ~53-57
  - Deve ter labels: `['api_type']`
  - Nome: `consul_api_calls_total`
  - Comentário menciona: agent|catalog|kv|health
  - Validação: `grep "consul_api_calls_total" backend/core/metrics.py`

---

### 📁 Arquivo: `backend/core/consul_manager.py`

#### Imports e Docstring

- [ ] **Import time adicionado**
  - Arquivo: `backend/core/consul_manager.py`
  - Linha: ~12
  - Deve conter: `import time`
  - Validação: `grep "^import time" backend/core/consul_manager.py`

- [ ] **Imports de métricas adicionados**
  - Arquivo: `backend/core/consul_manager.py`
  - Linhas: ~18-23
  - Deve importar de `.metrics`: `consul_request_duration, consul_requests_total, consul_nodes_available, consul_fallback_total`
  - Validação: `grep "from .metrics import" backend/core/consul_manager.py`

- [ ] **Docstring atualizado com SPRINT 1**
  - Arquivo: `backend/core/consul_manager.py`
  - Linhas: ~1-6
  - Deve mencionar: "SPRINT 1 (2025-11-14): Otimização crítica"
  - Deve mencionar: "/agent/services com fallback inteligente"
  - Validação: `grep "SPRINT 1" backend/core/consul_manager.py | head -1`

#### Método _request() - Agent Caching

- [ ] **Parâmetro use_cache adicionado**
  - Arquivo: `backend/core/consul_manager.py`
  - Linha: ~88
  - Assinatura deve incluir: `use_cache: bool = False`
  - Validação: `grep "def _request.*use_cache" backend/core/consul_manager.py`

- [ ] **Implementação Agent Caching**
  - Arquivo: `backend/core/consul_manager.py`
  - Linhas: ~95-100
  - Deve verificar: `if use_cache and method == "GET"`
  - Deve adicionar: `kwargs["params"]["cached"] = ""`
  - Comentário deve mencionar: "OFICIAL HASHICORP: Agent Caching"
  - Validação: `grep -A5 "if use_cache" backend/core/consul_manager.py | grep "cached"`

- [ ] **Tracking de cache hits**
  - Arquivo: `backend/core/consul_manager.py`
  - Linhas: ~150-165
  - Deve ler headers: `Age`, `X-Cache`
  - Deve incrementar: `consul_cache_hits.labels(...).inc()`
  - Deve calcular age_bucket: fresh|stale|very_stale
  - Validação: `grep "consul_cache_hits" backend/core/consul_manager.py`

- [ ] **Tracking de stale responses**
  - Arquivo: `backend/core/consul_manager.py`
  - Linhas: ~155-165
  - Deve ler header: `X-Consul-LastContact`
  - Deve incrementar: `consul_stale_responses.labels(...).inc()`
  - Deve calcular lag_bucket
  - Validação: `grep "consul_stale_responses" backend/core/consul_manager.py`

- [ ] **Tracking de API type**
  - Arquivo: `backend/core/consul_manager.py`
  - Linhas: ~170-182
  - Deve detectar: agent|catalog|kv|health
  - Deve incrementar: `consul_api_type.labels(api_type=...).inc()`
  - Validação: `grep "consul_api_type" backend/core/consul_manager.py`

#### Função _load_sites_config() (NOVA)

- [ ] **Função _load_sites_config existe**
  - Arquivo: `backend/core/consul_manager.py`
  - Linhas: ~773-807
  - Assinatura: `async def _load_sites_config(self) -> List[Dict]`
  - Validação: `grep "def _load_sites_config" backend/core/consul_manager.py`

- [ ] **Carrega sites do KV**
  - Arquivo: `backend/core/consul_manager.py`
  - Linha: ~781
  - Deve chamar: `await self.get_kv_json('skills/eye/metadata/sites')`
  - Validação: `grep "get_kv_json.*metadata/sites" backend/core/consul_manager.py`

- [ ] **Fallback para localhost se KV vazio**
  - Arquivo: `backend/core/consul_manager.py`
  - Linhas: ~783-789
  - Deve retornar: `[{'name': 'localhost', 'prometheus_instance': 'localhost', 'is_default': True}]`
  - Validação: `grep -A3 "KV metadata/sites vazio" backend/core/consul_manager.py`

- [ ] **Ordenação: master primeiro**
  - Arquivo: `backend/core/consul_manager.py`
  - Linhas: ~791-795
  - Deve usar: `sorted(..., key=lambda s: (not s.get('is_default', False), ...))`
  - Validação: `grep "sorted.*is_default" backend/core/consul_manager.py`

- [ ] **Fallback para Config.get_main_server() em exceção**
  - Arquivo: `backend/core/consul_manager.py`
  - Linhas: ~797-805
  - Deve retornar: `[{'name': 'fallback', 'prometheus_instance': Config.get_main_server(), ...}]`
  - Validação: `grep "Config.get_main_server()" backend/core/consul_manager.py`

- [ ] **Logs adequados (debug, warning, error)**
  - Arquivo: `backend/core/consul_manager.py`
  - Deve ter: `logger.debug`, `logger.warning`, `logger.error`
  - Validação: `grep "logger\.\(debug\|warning\|error\)" backend/core/consul_manager.py | grep -i "site"`

#### Função get_services_with_fallback() (NOVA)

- [ ] **Função get_services_with_fallback existe**
  - Arquivo: `backend/core/consul_manager.py`
  - Linhas: ~809-933
  - Assinatura: `async def get_services_with_fallback(self, timeout_per_node: float = 2.0, global_timeout: float = 30.0) -> Tuple[Dict, Dict]`
  - Validação: `grep "def get_services_with_fallback" backend/core/consul_manager.py`

- [ ] **Usa /catalog/services (NÃO /agent/services)**
  - Arquivo: `backend/core/consul_manager.py`
  - Linha: ~847
  - Deve chamar: `_request("GET", "/catalog/services", use_cache=True, params={"stale": ""})`
  - **CRÍTICO**: NÃO pode ser `/agent/services`
  - Validação: `grep -A5 "get_services_with_fallback" backend/core/consul_manager.py | grep "/catalog/services"`

- [ ] **Timeout por node configurável (padrão 2s)**
  - Arquivo: `backend/core/consul_manager.py`
  - Linha: ~845
  - Deve usar: `asyncio.wait_for(..., timeout=timeout_per_node)`
  - Validação: `grep "timeout_per_node" backend/core/consul_manager.py`

- [ ] **Retorna tuple (services, metadata)**
  - Arquivo: `backend/core/consul_manager.py`
  - Linhas: ~891-902
  - Deve retornar: `return (services, metadata)`
  - Metadata deve incluir: source_node, source_name, is_master, attempts, total_time_ms, cache_status, age_seconds, staleness_ms
  - Validação: `grep "return (services, metadata)" backend/core/consul_manager.py`

- [ ] **Warning quando master offline**
  - Arquivo: `backend/core/consul_manager.py`
  - Linhas: ~899-900
  - Deve adicionar: `metadata["warning"] = f"Master offline - dados de {node_name}"`
  - Validação: `grep "Master offline" backend/core/consul_manager.py`

#### Função get_all_services_catalog() (NOVA)

- [ ] **Função get_all_services_catalog existe**
  - Arquivo: `backend/core/consul_manager.py`
  - Linhas: ~935-1031
  - Assinatura: `async def get_all_services_catalog(self, use_fallback: bool = True) -> Dict[str, Dict]`
  - Validação: `grep "def get_all_services_catalog" backend/core/consul_manager.py`

- [ ] **Chama get_services_with_fallback()**
  - Arquivo: `backend/core/consul_manager.py`
  - Linha: ~961
  - Deve chamar: `services_catalog, metadata = await self.get_services_with_fallback()`
  - Validação: `grep "await self.get_services_with_fallback" backend/core/consul_manager.py`

- [ ] **Loop em service_names (NÃO sequencial, PARALELO)**
  - Arquivo: `backend/core/consul_manager.py`
  - Linhas: ~977-1026
  - Deve usar: `asyncio.gather()` para paralelização
  - Deve definir: `async def fetch_service_details(service_name: str)`
  - Comentário deve mencionar: "SPRINT 1 - PARALELIZAÇÃO"
  - Validação: `grep "asyncio.gather" backend/core/consul_manager.py`

- [ ] **Retorna _metadata no dict**
  - Arquivo: `backend/core/consul_manager.py`
  - Linha: ~1029
  - Deve adicionar: `all_services["_metadata"] = metadata`
  - Validação: `grep "_metadata.*=.*metadata" backend/core/consul_manager.py`

#### Função get_all_services_from_all_nodes() (DEPRECATED)

- [ ] **Função marcada como DEPRECATED**
  - Arquivo: `backend/core/consul_manager.py`
  - Linhas: ~1033-1050
  - Docstring deve conter: "⚠️ DEPRECATED"
  - Deve explicar: "Agent API retorna apenas dados locais"
  - Validação: `grep -A5 "def get_all_services_from_all_nodes" backend/core/consul_manager.py | grep "DEPRECATED"`

- [ ] **warnings.warn() adicionado**
  - Arquivo: `backend/core/consul_manager.py`
  - Linhas: ~1062-1067
  - Deve chamar: `warnings.warn(..., DeprecationWarning, stacklevel=2)`
  - Validação: `grep "warnings.warn" backend/core/consul_manager.py`

- [ ] **logger.warning() adicionado**
  - Arquivo: `backend/core/consul_manager.py`
  - Linhas: ~1068-1071
  - Deve ter: `logger.warning("⚠️ [DEPRECATED] get_all_services_from_all_nodes() chamada.")`
  - Validação: `grep "DEPRECATED.*get_all_services_from_all_nodes" backend/core/consul_manager.py`

- [ ] **Redireciona para get_all_services_catalog()**
  - Arquivo: `backend/core/consul_manager.py`
  - Linha: ~1073
  - Deve retornar: `return await self.get_all_services_catalog(use_fallback=True)`
  - Validação: `grep "return await self.get_all_services_catalog" backend/core/consul_manager.py`

---

### 📁 Arquivo: `backend/api/monitoring_unified.py`

- [ ] **Linha 214 atualizada para get_all_services_catalog()**
  - Arquivo: `backend/api/monitoring_unified.py`
  - Linha: ~215 (antes era 214)
  - Deve chamar: `await consul_manager.get_all_services_catalog(use_fallback=True)`
  - Validação: `grep "get_all_services_catalog" backend/api/monitoring_unified.py`

- [ ] **Extração de _metadata**
  - Arquivo: `backend/api/monitoring_unified.py`
  - Linhas: ~217-243
  - Deve ter: `metadata_info = all_services_dict.pop("_metadata", None)`
  - Validação: `grep "_metadata" backend/api/monitoring_unified.py`

- [ ] **Logs de metadata adicionados**
  - Arquivo: `backend/api/monitoring_unified.py`
  - Linhas: ~219-242
  - Deve ter: `logger.info(f"[Monitoring] Dados obtidos via {metadata_info.get('source_name', 'unknown')}")`
  - Deve ter: `logger.warning` quando master offline
  - Deve logar: cache_status, age_seconds, staleness_ms
  - Validação: `grep "logger.info.*Monitoring.*metadata" backend/api/monitoring_unified.py`

---

### 📁 Arquivo: `backend/api/services.py`

- [ ] **Linha 54 atualizada para get_all_services_catalog()**
  - Arquivo: `backend/api/services.py`
  - Linha: ~55
  - Deve chamar: `await consul.get_all_services_catalog(use_fallback=True)`
  - Comentário deve mencionar: "SPRINT 1 CORREÇÃO (2025-11-15)"
  - Validação: `sed -n '50,60p' backend/api/services.py | grep get_all_services_catalog`

- [ ] **Extração de _metadata (primeira ocorrência)**
  - Arquivo: `backend/api/services.py`
  - Linhas: ~57-67
  - Deve ter: `metadata_info = all_services.pop("_metadata", None)`
  - Deve logar metadata_info
  - Validação: `sed -n '55,70p' backend/api/services.py | grep "_metadata"`

- [ ] **Linha 248 atualizada para get_all_services_catalog()**
  - Arquivo: `backend/api/services.py`
  - Linha: ~261
  - Deve chamar: `await consul.get_all_services_catalog(use_fallback=True)`
  - Comentário deve mencionar: "SPRINT 1 CORREÇÃO"
  - Validação: `sed -n '260,265p' backend/api/services.py | grep get_all_services_catalog`

- [ ] **Extração de _metadata (segunda ocorrência)**
  - Arquivo: `backend/api/services.py`
  - Linhas: ~263-273
  - Deve ter: `metadata_info = all_services.pop("_metadata", None)`
  - Deve logar: "[Services Search] Dados via ..."
  - Validação: `sed -n '260,275p' backend/api/services.py | grep "_metadata"`

---

### 📁 Arquivo: `backend/core/blackbox_manager.py`

- [ ] **Linha 142 atualizada para get_all_services_catalog()**
  - Arquivo: `backend/core/blackbox_manager.py`
  - Linha: ~146
  - Deve chamar: `await self.consul.get_all_services_catalog(use_fallback=True)`
  - Comentário deve mencionar: "SPRINT 1 CORREÇÃO"
  - Validação: `sed -n '140,150p' backend/core/blackbox_manager.py | grep get_all_services_catalog`

- [ ] **Extração de _metadata**
  - Arquivo: `backend/core/blackbox_manager.py`
  - Linhas: ~148-159
  - Deve ter: `metadata_info = all_services.pop("_metadata", None)`
  - Deve logar: "[Blackbox] Dados obtidos via ..."
  - Validação: `sed -n '145,160p' backend/core/blackbox_manager.py | grep "_metadata"`

---

### 📁 Arquivo: `backend/test_categorization_debug.py`

- [ ] **Linha 23 atualizada para get_all_services_catalog()**
  - Arquivo: `backend/test_categorization_debug.py`
  - Linha: ~24
  - Deve chamar: `await consul_manager.get_all_services_catalog(use_fallback=True)`
  - Comentário deve mencionar: "SPRINT 1 CORREÇÃO"
  - Validação: `sed -n '20,30p' backend/test_categorization_debug.py | grep get_all_services_catalog`

- [ ] **Remove _metadata antes de processar**
  - Arquivo: `backend/test_categorization_debug.py`
  - Linha: ~26
  - Deve ter: `all_services.pop("_metadata", None)`
  - Validação: `sed -n '24,30p' backend/test_categorization_debug.py | grep "_metadata"`

---

### 📁 Arquivos de Teste (NOVOS)

- [ ] **test_agent_caching.py existe**
  - Arquivo: `backend/test_agent_caching.py`
  - Deve validar: cache HIT/MISS via headers
  - Deve calcular: ganho de performance
  - Validação: `ls backend/test_agent_caching.py`

- [ ] **test_catalog_stale_mode.py existe**
  - Arquivo: `backend/test_catalog_stale_mode.py`
  - Deve validar: Catalog API retornando todos serviços
  - Deve testar: Stale Reads distribuindo carga
  - Deve comparar: fallback vs não-fallback
  - Validação: `ls backend/test_catalog_stale_mode.py`

- [ ] **test_fallback_strategy.py existe**
  - Arquivo: `backend/test_fallback_strategy.py`
  - Deve validar: estratégia master → clients
  - Deve testar: timeout fail-fast (2s)
  - Deve validar: consistência de múltiplas chamadas
  - Validação: `ls backend/test_fallback_strategy.py`

- [ ] **test_performance_parallel.py existe**
  - Arquivo: `backend/test_performance_parallel.py`
  - Deve comparar: sequencial vs paralelo
  - Deve medir: speedup
  - Validação: `ls backend/test_performance_parallel.py`

---

## SPRINT 1 - FRONTEND

### 📁 Arquivo: `frontend/src/pages/DynamicMonitoringPage.tsx`

- [ ] **Estado metadataOptionsLoaded adicionado**
  - Arquivo: `frontend/src/pages/DynamicMonitoringPage.tsx`
  - Linhas: ~183-185
  - Deve declarar: `const [metadataOptionsLoaded, setMetadataOptionsLoaded] = useState(false);`
  - Comentário deve mencionar: "SPRINT 1 (2025-11-14)"
  - Validação: `grep "metadataOptionsLoaded.*useState" frontend/src/pages/DynamicMonitoringPage.tsx`

- [ ] **setMetadataOptionsLoaded(true) após setMetadataOptions**
  - Arquivo: `frontend/src/pages/DynamicMonitoringPage.tsx`
  - Linha: ~604
  - Deve chamar: `setMetadataOptionsLoaded(true);`
  - Deve estar logo após: `setMetadataOptions(options);`
  - Comentário deve mencionar: "SPRINT 1: Marcar como carregado"
  - Validação: `grep -A1 "setMetadataOptions(options)" frontend/src/pages/DynamicMonitoringPage.tsx | grep "setMetadataOptionsLoaded(true)"`

- [ ] **Renderização condicional tripla de MetadataFilterBar**
  - Arquivo: `frontend/src/pages/DynamicMonitoringPage.tsx`
  - Linhas: ~1149-1150
  - Condição deve incluir: `filterFields.length > 0 && metadataOptionsLoaded && Object.keys(metadataOptions).length > 0`
  - Comentário deve mencionar: "SPRINT 1: Renderização condicional para evitar race condition"
  - Validação: `grep -B2 "MetadataFilterBar" frontend/src/pages/DynamicMonitoringPage.tsx | grep "metadataOptionsLoaded"`

---

### 📁 Arquivo: `frontend/src/components/MetadataFilterBar.tsx`

- [ ] **Comentário SPRINT 1 na linha 72-73**
  - Arquivo: `frontend/src/components/MetadataFilterBar.tsx`
  - Linha: ~72-73
  - Comentário deve mencionar: "SPRINT 1 (2025-11-14): Validação defensiva com optional chaining"
  - Código: `const fieldOptions = options?.[field.name] ?? [];`
  - Validação: `sed -n '70,75p' frontend/src/components/MetadataFilterBar.tsx | grep "SPRINT 1"`

- [ ] **Comentários atualizados linhas 76-80**
  - Arquivo: `frontend/src/components/MetadataFilterBar.tsx`
  - Linhas: ~76-80
  - Comentário deve mencionar: "SPRINT 1: Não renderizar select sem opções (evita race condition)"
  - Comentário deve mencionar: "Protege contra TypeError quando options ainda não foi carregado"
  - Validação: `sed -n '75,82p' frontend/src/components/MetadataFilterBar.tsx | grep "race condition"`

---

## SPRINT 1 - CORREÇÕES PÓS-IMPLEMENTAÇÃO

### 📁 Arquivo: `backend/core/consul_manager.py` (Paralelização)

- [ ] **Função fetch_service_details interna**
  - Arquivo: `backend/core/consul_manager.py`
  - Linhas: ~982-993
  - Deve ser: `async def fetch_service_details(service_name: str)`
  - Comentário deve mencionar: "SPRINT 1 - PARALELIZAÇÃO (2025-11-15)"
  - Validação: `grep "async def fetch_service_details" backend/core/consul_manager.py`

- [ ] **asyncio.gather() para chamadas paralelas**
  - Arquivo: `backend/core/consul_manager.py`
  - Linhas: ~1000-1003
  - Deve usar: `results = await asyncio.gather(*[fetch_service_details(svc_name) for svc_name in service_names], return_exceptions=False)`
  - Validação: `grep "asyncio.gather.*fetch_service_details" backend/core/consul_manager.py`

- [ ] **Log de paralelização confirmado**
  - Arquivo: Logs de execução
  - Deve mostrar: timestamps com diferença de ~8ms entre todas as chamadas
  - Validação: Executar teste e verificar logs

---

### 📁 Arquivo: `backend/core/consul_manager.py` (API Type Tracking)

- [ ] **Detecção de tipo de API**
  - Arquivo: `backend/core/consul_manager.py`
  - Linhas: ~170-181
  - Deve detectar: `/agent/`, `/catalog/`, `/kv/`, `/health/`
  - Deve incrementar: `consul_api_type.labels(api_type=api_type).inc()`
  - Validação: `grep -A10 "if path.startswith" backend/core/consul_manager.py | grep "consul_api_type"`

---

## SPRINT 2 - BACKEND

### 📁 Arquivo: `backend/core/cache_manager.py` (NOVO)

- [ ] **Arquivo cache_manager.py foi criado**
  - Arquivo: `backend/core/cache_manager.py`
  - Deve ter ~228 linhas
  - Validação: `ls backend/core/cache_manager.py`

- [ ] **Classe LocalCache definida**
  - Arquivo: `backend/core/cache_manager.py`
  - Linhas: ~1-228
  - Deve ter: `class LocalCache`
  - Docstring deve mencionar: TTL configurável
  - Validação: `grep "class LocalCache" backend/core/cache_manager.py`

- [ ] **Método __init__ com TTL**
  - Arquivo: `backend/core/cache_manager.py`
  - Deve aceitar: `ttl_seconds: int = 60`
  - Deve inicializar: `self._cache`, `self._lock`, `self.ttl_seconds`
  - Validação: `grep "def __init__.*ttl_seconds" backend/core/cache_manager.py`

- [ ] **Método get() async**
  - Arquivo: `backend/core/cache_manager.py`
  - Deve usar: `async with self._lock`
  - Deve verificar: TTL expirado
  - Deve retornar: `Optional[Any]`
  - Validação: `grep "async def get" backend/core/cache_manager.py`

- [ ] **Método set() async**
  - Arquivo: `backend/core/cache_manager.py`
  - Deve armazenar: `(value, datetime.now())`
  - Deve usar: `async with self._lock`
  - Validação: `grep "async def set" backend/core/cache_manager.py`

- [ ] **Método invalidate() async**
  - Arquivo: `backend/core/cache_manager.py`
  - Deve remover: chave específica
  - Validação: `grep "async def invalidate" backend/core/cache_manager.py`

- [ ] **Método invalidate_pattern() async**
  - Arquivo: `backend/core/cache_manager.py`
  - Deve suportar: wildcards
  - Deve usar: `fnmatch` para pattern matching
  - Validação: `grep "async def invalidate_pattern" backend/core/cache_manager.py`

- [ ] **Método clear() async**
  - Arquivo: `backend/core/cache_manager.py`
  - Deve limpar: `self._cache.clear()`
  - Validação: `grep "async def clear" backend/core/cache_manager.py`

- [ ] **Método get_stats() async**
  - Arquivo: `backend/core/cache_manager.py`
  - Deve retornar: hits, misses, evictions, invalidations, hit_rate_percent, total_requests, current_size, ttl_seconds
  - Validação: `grep "async def get_stats" backend/core/cache_manager.py`

- [ ] **Método get_keys() async**
  - Arquivo: `backend/core/cache_manager.py`
  - Deve retornar: lista de chaves
  - Validação: `grep "async def get_keys" backend/core/cache_manager.py`

- [ ] **Singleton _catalog_cache criado**
  - Arquivo: `backend/core/cache_manager.py`
  - Final do arquivo
  - Deve ter: `_catalog_cache = LocalCache(ttl_seconds=60)`
  - Validação: `grep "_catalog_cache = LocalCache" backend/core/cache_manager.py`

---

### 📁 Arquivo: `backend/api/cache.py` (NOVO)

- [ ] **Arquivo cache.py foi criado**
  - Arquivo: `backend/api/cache.py`
  - Deve ter ~189 linhas
  - Validação: `ls backend/api/cache.py`

- [ ] **Router APIRouter criado**
  - Arquivo: `backend/api/cache.py`
  - Deve ter: `router = APIRouter(prefix="/cache", tags=["Cache Management"])`
  - Validação: `grep "APIRouter.*cache" backend/api/cache.py`

- [ ] **Endpoint GET /stats**
  - Arquivo: `backend/api/cache.py`
  - Path: `/api/v1/cache/stats`
  - Deve retornar: stats do _catalog_cache
  - Validação: `grep "@router.get.*stats" backend/api/cache.py`

- [ ] **Endpoint GET /keys**
  - Arquivo: `backend/api/cache.py`
  - Path: `/api/v1/cache/keys`
  - Deve retornar: lista de chaves
  - Validação: `grep "@router.get.*keys" backend/api/cache.py`

- [ ] **Endpoint GET /entry/{key}**
  - Arquivo: `backend/api/cache.py`
  - Path: `/api/v1/cache/entry/{key}`
  - Deve retornar: detalhes da entrada
  - Validação: `grep "@router.get.*entry" backend/api/cache.py`

- [ ] **Endpoint POST /invalidate**
  - Arquivo: `backend/api/cache.py`
  - Path: `/api/v1/cache/invalidate`
  - Deve aceitar: `{"key": "..."}`
  - Validação: `grep "@router.post.*invalidate" backend/api/cache.py | head -1`

- [ ] **Endpoint POST /invalidate-pattern**
  - Arquivo: `backend/api/cache.py`
  - Path: `/api/v1/cache/invalidate-pattern`
  - Deve aceitar: `{"pattern": "..."}`
  - Validação: `grep "@router.post.*invalidate-pattern" backend/api/cache.py`

- [ ] **Endpoint POST /clear**
  - Arquivo: `backend/api/cache.py`
  - Path: `/api/v1/cache/clear`
  - Deve limpar: todo o cache
  - Validação: `grep "@router.post.*clear" backend/api/cache.py`

---

### 📁 Arquivo: `backend/app.py`

- [ ] **Import cache router**
  - Arquivo: `backend/app.py`
  - Deve ter: `from api.cache import router as cache_router`
  - Validação: `grep "from api.cache import" backend/app.py`

- [ ] **Include cache router**
  - Arquivo: `backend/app.py`
  - Deve ter: `app.include_router(cache_router, prefix="/api/v1")`
  - Validação: `grep "include_router.*cache_router" backend/app.py`

- [ ] **Endpoint /metrics para Prometheus**
  - Arquivo: `backend/app.py`
  - Deve ter: `@app.get("/metrics")`
  - Deve retornar: `Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)`
  - Validação: `grep "@app.get.*metrics" backend/app.py`

---

### 📁 Arquivo: `backend/test_cache_performance.py` (NOVO)

- [ ] **Arquivo test_cache_performance.py foi criado**
  - Arquivo: `backend/test_cache_performance.py`
  - Deve ter ~185 linhas
  - Validação: `ls backend/test_cache_performance.py`

- [ ] **Teste 1: Cache MISS**
  - Arquivo: `backend/test_cache_performance.py`
  - Deve simular: primeira chamada (sem cache)
  - Deve medir: tempo ~1290ms
  - Validação: `grep "TESTE 1.*CACHE MISS" backend/test_cache_performance.py`

- [ ] **Teste 2: Cache HIT**
  - Arquivo: `backend/test_cache_performance.py`
  - Deve simular: segunda chamada (com cache)
  - Deve medir: tempo ~0ms
  - Deve calcular: speedup infinito
  - Validação: `grep "TESTE 2.*CACHE HIT" backend/test_cache_performance.py`

- [ ] **Teste 3: Warming (10 chamadas)**
  - Arquivo: `backend/test_cache_performance.py`
  - Deve executar: 10 chamadas consecutivas
  - Deve calcular: hit rate >= 90%
  - Validação: `grep "TESTE 3.*WARMING" backend/test_cache_performance.py`

- [ ] **Teste 4: Invalidação**
  - Arquivo: `backend/test_cache_performance.py`
  - Deve testar: invalidação manual
  - Validação: `grep "TESTE 4.*INVALIDAÇÃO" backend/test_cache_performance.py`

---

### 📁 Cleanup de Código Obsoleto (Backend)

- [ ] **backend/api/dashboard.py - import obsoleto removido**
  - Arquivo: `backend/api/dashboard.py`
  - NÃO deve ter: `from core.cache_manager import ...` (se existia antes)
  - Validação: `grep "from core.cache_manager" backend/api/dashboard.py` (deve retornar vazio)

- [ ] **backend/api/optimized_endpoints.py - import obsoleto removido**
  - Arquivo: `backend/api/optimized_endpoints.py`
  - NÃO deve ter imports não utilizados de cache
  - Validação: Verificar imports no topo do arquivo

- [ ] **backend/api/services_optimized.py - código de cache antigo removido**
  - Arquivo: `backend/api/services_optimized.py`
  - NÃO deve ter: código duplicado de cache manual
  - Validação: Verificar ausência de cache manual inline

---

## SPRINT 2 - FRONTEND

### 📁 Arquivo: `frontend/src/components/BadgeStatus.tsx` (NOVO)

- [ ] **Arquivo BadgeStatus.tsx foi criado**
  - Arquivo: `frontend/src/components/BadgeStatus.tsx`
  - Deve ter ~85 linhas
  - Validação: `ls frontend/src/components/BadgeStatus.tsx`

- [ ] **Interface BadgeStatusProps definida**
  - Arquivo: `frontend/src/components/BadgeStatus.tsx`
  - Deve incluir: metadata com source_name, is_master, cache_status, age_seconds, staleness_ms, total_time_ms
  - Validação: `grep "interface BadgeStatusProps" frontend/src/components/BadgeStatus.tsx`

- [ ] **Badge Source (Master/Fallback)**
  - Arquivo: `frontend/src/components/BadgeStatus.tsx`
  - Deve renderizar: Tag com ícone CheckCircleOutlined ou WarningOutlined
  - Cor: green (master) ou orange (fallback)
  - Validação: `grep "isMaster.*green.*orange" frontend/src/components/BadgeStatus.tsx`

- [ ] **Badge Cache (HIT/MISS)**
  - Arquivo: `frontend/src/components/BadgeStatus.tsx`
  - Deve renderizar: Tag com ícone ClockCircleOutlined
  - Cor: blue (HIT) ou default (MISS)
  - Validação: `grep "cache_status.*HIT.*blue" frontend/src/components/BadgeStatus.tsx`

- [ ] **Badge Staleness (condicional)**
  - Arquivo: `frontend/src/components/BadgeStatus.tsx`
  - Deve renderizar: apenas se staleness > 1000ms
  - Cor: warning
  - Validação: `grep "staleness > 1000" frontend/src/components/BadgeStatus.tsx`

- [ ] **Badge Performance (tempo de resposta)**
  - Arquivo: `frontend/src/components/BadgeStatus.tsx`
  - Deve renderizar: Tag com total_time_ms
  - Cor: success (<500ms) ou default
  - Validação: `grep "responseTime < 500" frontend/src/components/BadgeStatus.tsx`

---

### 📁 Arquivo: `frontend/src/pages/CacheManagement.tsx` (NOVO)

- [ ] **Arquivo CacheManagement.tsx foi criado**
  - Arquivo: `frontend/src/pages/CacheManagement.tsx`
  - Deve ter ~312 linhas
  - Validação: `ls frontend/src/pages/CacheManagement.tsx`

- [ ] **Estado metrics definido**
  - Arquivo: `frontend/src/pages/CacheManagement.tsx`
  - Deve ter: `const [metrics, setMetrics] = useState<any>(null);`
  - Validação: `grep "useState.*metrics" frontend/src/pages/CacheManagement.tsx`

- [ ] **Auto-refresh a cada 10s**
  - Arquivo: `frontend/src/pages/CacheManagement.tsx`
  - Deve usar: `setInterval(fetchMetrics, 10000)`
  - Validação: `grep "setInterval.*10000" frontend/src/pages/CacheManagement.tsx`

- [ ] **KPI: Hit Rate**
  - Arquivo: `frontend/src/pages/CacheManagement.tsx`
  - Deve calcular: `(hits / total) * 100`
  - Ícone: DatabaseOutlined
  - Validação: `grep "Hit Rate" frontend/src/pages/CacheManagement.tsx`

- [ ] **KPI: Total Hits**
  - Arquivo: `frontend/src/pages/CacheManagement.tsx`
  - Ícone: ClockCircleOutlined
  - Validação: `grep "Total.*Hits" frontend/src/pages/CacheManagement.tsx`

- [ ] **KPI: Total Misses**
  - Arquivo: `frontend/src/pages/CacheManagement.tsx`
  - Validação: `grep "Total.*Misses" frontend/src/pages/CacheManagement.tsx`

- [ ] **KPI: Cache Size**
  - Arquivo: `frontend/src/pages/CacheManagement.tsx`
  - Validação: `grep "Cache Size" frontend/src/pages/CacheManagement.tsx`

- [ ] **Tabela de chaves armazenadas**
  - Arquivo: `frontend/src/pages/CacheManagement.tsx`
  - Deve usar: ProTable ou Table
  - Colunas: key, age, actions
  - Validação: `grep "ProTable\|Table" frontend/src/pages/CacheManagement.tsx`

- [ ] **Ação: Invalidar chave individual**
  - Arquivo: `frontend/src/pages/CacheManagement.tsx`
  - Deve chamar: POST `/api/v1/cache/invalidate`
  - Validação: `grep "invalidate" frontend/src/pages/CacheManagement.tsx`

- [ ] **Ação: Invalidar por padrão**
  - Arquivo: `frontend/src/pages/CacheManagement.tsx`
  - Deve chamar: POST `/api/v1/cache/invalidate-pattern`
  - Validação: `grep "invalidate-pattern" frontend/src/pages/CacheManagement.tsx`

- [ ] **Ação: Limpar todo cache**
  - Arquivo: `frontend/src/pages/CacheManagement.tsx`
  - Deve chamar: POST `/api/v1/cache/clear`
  - Deve ter: confirmação (Modal/Popconfirm)
  - Validação: `grep "clear.*cache" frontend/src/pages/CacheManagement.tsx`

---

### 📁 Arquivo: `frontend/src/App.tsx`

- [ ] **Import CacheManagement**
  - Arquivo: `frontend/src/App.tsx`
  - Deve ter: `import CacheManagement from './pages/CacheManagement';`
  - Validação: `grep "import.*CacheManagement" frontend/src/App.tsx`

- [ ] **Rota /cache-management adicionada**
  - Arquivo: `frontend/src/App.tsx`
  - Path: `/cache-management`
  - Nome: "Cache Management"
  - Ícone: DatabaseOutlined
  - Validação: `grep "cache-management" frontend/src/App.tsx`

---

### 📁 Integração de BadgeStatus (3 páginas)

- [ ] **DynamicMonitoringPage.tsx integra BadgeStatus**
  - Arquivo: `frontend/src/pages/DynamicMonitoringPage.tsx`
  - Linha: ~45
  - Deve importar: `import { BadgeStatus } from '../components/BadgeStatus';`
  - Deve usar: `<BadgeStatus metadata={responseMetadata} />`
  - Header extra deve incluir BadgeStatus
  - Validação: `grep "BadgeStatus" frontend/src/pages/DynamicMonitoringPage.tsx`

- [ ] **Services.tsx integra BadgeStatus**
  - Arquivo: `frontend/src/pages/Services.tsx`
  - Linha: ~531
  - Deve importar BadgeStatus
  - Deve usar no header
  - Validação: `grep "BadgeStatus" frontend/src/pages/Services.tsx`

- [ ] **BlackboxTargets.tsx integra BadgeStatus**
  - Arquivo: `frontend/src/pages/BlackboxTargets.tsx`
  - Linha: ~298
  - Deve importar BadgeStatus
  - Deve usar no header
  - Validação: `grep "BadgeStatus" frontend/src/pages/BlackboxTargets.tsx`

---

### 📁 Cleanup de Código Obsoleto (Frontend)

- [ ] **frontend/src/services/api.ts - método _old_getDashboardMetrics removido**
  - Arquivo: `frontend/src/services/api.ts`
  - Linhas: ~743-899 (removidas)
  - NÃO deve existir: `_old_getDashboardMetrics`
  - Validação: `grep "_old_getDashboardMetrics" frontend/src/services/api.ts` (deve retornar vazio)

- [ ] **frontend/src/services/api.ts - código duplicado de cache removido**
  - Arquivo: `frontend/src/services/api.ts`
  - Linhas: ~1560-1594 (removidas)
  - NÃO deve ter: código duplicado de cache
  - Validação: Verificar ausência de duplicação

---

## CORREÇÕES CRÍTICAS PÓS-SPRINT 2

### 📁 Arquivo: `backend/core/config.py`

- [ ] **Bug KV 'str' object has no attribute 'get' corrigido**
  - Arquivo: `backend/core/config.py`
  - Linhas: ~65-91
  - Deve tratar: estrutura dupla `{"data": {"sites": [...]}}`
  - Deve ter: `if isinstance(sites_data, dict) and 'data' in sites_data`
  - Deve ter: `elif isinstance(sites_data, dict) and 'sites' in sites_data`
  - Deve ter: `elif isinstance(sites_data, list)`
  - Validação: `sed -n '65,91p' backend/core/config.py | grep "isinstance.*dict.*data"`

- [ ] **Logging de erro detalhado adicionado**
  - Arquivo: `backend/core/config.py`
  - Linhas: ~78-83
  - Deve ter: `logger.warning(f"❌ KV sites estrutura desconhecida: {type(sites_data)}")`
  - Validação: `grep "estrutura desconhecida" backend/core/config.py`

- [ ] **Conversão para dict {hostname: ip}**
  - Arquivo: `backend/core/config.py`
  - Linhas: ~85-91
  - Deve iterar: `for site in sites_list`
  - Deve extrair: hostname (ou name), prometheus_instance
  - Deve retornar: `nodes[hostname] = ip`
  - Validação: `sed -n '85,91p' backend/core/config.py | grep "nodes\[hostname\]"`

---

### 📁 Arquivo: `backend/core/consul_manager.py`

- [ ] **Import os adicionado**
  - Arquivo: `backend/core/consul_manager.py`
  - Linha: ~15
  - Deve ter: `import os`
  - Validação: `grep "^import os" backend/core/consul_manager.py`

- [ ] **Lazy evaluation no __init__ com getattr()**
  - Arquivo: `backend/core/consul_manager.py`
  - Linhas: ~84-86
  - Deve usar: `self.host = host or getattr(Config, 'MAIN_SERVER', os.getenv('CONSUL_HOST', 'localhost'))`
  - Comentário deve mencionar: "Lazy evaluation: evita loop circular"
  - Validação: `grep "getattr.*MAIN_SERVER" backend/core/consul_manager.py`

---

### 📁 Cache Vite Limpo (Processo Manual)

- [ ] **node_modules/.vite foi limpo**
  - Comando executado: `rmdir /S /Q frontend/node_modules/.vite`
  - Validação: Verificar que pasta não existe ou foi recriada após `npm run dev`

- [ ] **Processos Node.js foram killados antes de reiniciar**
  - Comando executado: `taskkill /F /IM node.exe`
  - Validação: Verificar que `npm run dev` inicia sem erros de porta em uso

---

## TESTES DE VALIDAÇÃO

### Testes Backend

- [ ] **test_agent_caching.py executa sem erros**
  - Comando: `cd backend && python test_agent_caching.py`
  - Resultado esperado: Cache HIT detectado, ganho de performance 1.3x
  - Validação: `python backend/test_agent_caching.py`

- [ ] **test_catalog_stale_mode.py executa sem erros**
  - Comando: `cd backend && python test_catalog_stale_mode.py`
  - Resultado esperado: 164 serviços de 3 nodes, staleness 0ms
  - Validação: `python backend/test_catalog_stale_mode.py`

- [ ] **test_fallback_strategy.py executa sem erros**
  - Comando: `cd backend && python test_fallback_strategy.py`
  - Resultado esperado: Fail-fast funcionando, consistência 100%
  - Validação: `python backend/test_fallback_strategy.py`

- [ ] **test_performance_parallel.py executa sem erros**
  - Comando: `cd backend && python test_performance_parallel.py`
  - Resultado esperado: Speedup 1.02x (limitado por cache), integridade 100%
  - Validação: `python backend/test_performance_parallel.py`

- [ ] **test_cache_performance.py executa sem erros**
  - Comando: `cd backend && python test_cache_performance.py`
  - Resultado esperado: Hit rate >= 90%, cache HIT instantâneo
  - Validação: `python backend/test_cache_performance.py`

---

### Testes de API

- [ ] **Endpoint /api/v1/cache/stats retorna 200**
  - Comando: `curl http://localhost:5000/api/v1/cache/stats`
  - Resultado esperado: JSON com hits, misses, hit_rate_percent, etc
  - Validação: `curl -s http://localhost:5000/api/v1/cache/stats | jq .`

- [ ] **Endpoint /metrics retorna métricas Prometheus**
  - Comando: `curl http://localhost:5000/metrics`
  - Resultado esperado: Métricas em formato texto Prometheus
  - Deve incluir: `consul_cache_hits_total`, `consul_stale_responses_total`, `consul_api_calls_total`
  - Validação: `curl -s http://localhost:5000/metrics | grep consul_cache_hits`

- [ ] **Endpoint /api/v1/monitoring/data retorna dados com metadata**
  - Comando: `curl "http://localhost:5000/api/v1/monitoring/data?category=network-probes"`
  - Resultado esperado: JSON com success=true, total >= 100
  - Validação: `curl -s "http://localhost:5000/api/v1/monitoring/data?category=network-probes" | jq '{success, total: (.data | length)}'`

- [ ] **Endpoint /api/v1/services/?node_addr=ALL retorna todos serviços**
  - Comando: `curl "http://localhost:5000/api/v1/services/?node_addr=ALL"`
  - Resultado esperado: JSON com success=true, total >= 100
  - Validação: `curl -s "http://localhost:5000/api/v1/services/?node_addr=ALL" | jq '{success, total}'`

---

### Testes Frontend

- [ ] **TypeScript compila sem erros (arquivos do SPRINT 1/2)**
  - Comando: `cd frontend && npx tsc --noEmit`
  - Resultado esperado: Sem erros em BadgeStatus.tsx, CacheManagement.tsx, DynamicMonitoringPage.tsx (linhas modificadas)
  - Validação: `npx tsc --noEmit 2>&1 | grep -E "(BadgeStatus|CacheManagement|DynamicMonitoring)"`

- [ ] **Frontend dev server inicia sem erros**
  - Comando: `cd frontend && npm run dev`
  - Resultado esperado: Vite roda em http://localhost:8082/
  - Validação: Verificar console sem erros de parsing

- [ ] **Página /cache-management carrega**
  - Acessar: http://localhost:8082/cache-management
  - Resultado esperado: Dashboard visual com KPIs, tabela de chaves
  - Validação: Verificar visualmente

- [ ] **BadgeStatus aparece em DynamicMonitoringPage**
  - Acessar: http://localhost:8082/monitoring/network-probes (ou categoria existente)
  - Resultado esperado: Badges no header (Master/Fallback, Cache HIT/MISS, tempo de resposta)
  - Validação: Verificar visualmente

- [ ] **BadgeStatus aparece em Services**
  - Acessar: http://localhost:8082/services
  - Resultado esperado: Badges no header
  - Validação: Verificar visualmente

- [ ] **BadgeStatus aparece em BlackboxTargets**
  - Acessar: http://localhost:8082/blackbox/targets
  - Resultado esperado: Badges no header
  - Validação: Verificar visualmente

---

### Testes de Integração (Sistema Completo)

- [ ] **Backend inicia sem erros**
  - Comando: `cd backend && python app.py`
  - Resultado esperado: `INFO: Uvicorn running on http://0.0.0.0:5000`
  - Sem erros: `'str' object has no attribute 'get'`, `MAIN_SERVER`, `DEPRECATED`
  - Validação: Verificar logs de inicialização

- [ ] **Config carrega sites do KV corretamente**
  - Logs devem mostrar: `{'Palmas': '172.16.1.26', 'Rio_RMD': '172.16.200.14', 'Dtc': '11.144.0.21'}`
  - Config.MAIN_SERVER deve ser: `172.16.1.26`
  - Config.MAIN_SERVER_NAME deve ser: `Palmas`
  - Validação: `python -c "from core.config import Config; print(Config.MAIN_SERVER, Config.MAIN_SERVER_NAME)"`

- [ ] **Métricas Prometheus funcionam**
  - Executar algumas requests ao backend
  - Acessar: http://localhost:5000/metrics
  - Verificar: `consul_api_calls_total{api_type="catalog"}` > 0
  - Validação: `curl -s http://localhost:5000/metrics | grep consul_api_calls_total`

- [ ] **Cache local funciona (1290ms → ~0ms)**
  - Executar: `python backend/test_cache_performance.py`
  - Verificar: Segunda chamada é instantânea
  - Verificar: Hit rate >= 90%
  - Validação: Ver output do teste

- [ ] **Fallback strategy funciona (master → client)**
  - Simular: Master offline (desligar temporariamente 172.16.1.26)
  - Executar: Request ao backend
  - Logs devem mostrar: Tentativa master timeout, fallback para Rio
  - Tempo deve ser: ~2-4s (não 33s)
  - Validação: Verificar logs backend

---

### Testes de Regressão

- [ ] **Função get_all_services_from_all_nodes() ainda existe**
  - Arquivo: `backend/core/consul_manager.py`
  - Deve existir mas com warning
  - Validação: `grep "def get_all_services_from_all_nodes" backend/core/consul_manager.py`

- [ ] **Chamadas antigas ainda funcionam (backward compatibility)**
  - Código antigo que chama `get_all_services_from_all_nodes()` deve funcionar
  - Deve emitir: DeprecationWarning
  - Deve logar: "⚠️ [DEPRECATED] get_all_services_from_all_nodes() chamada."
  - Validação: Executar código antigo e verificar logs

- [ ] **Formato de retorno mantido**
  - Retorno deve ser: `Dict[str, Dict]` (compatível com código existente)
  - Estrutura: `{node_name: {service_id: service_data}}`
  - Código existente NÃO deve quebrar
  - Validação: Verificar que monitoring_unified.py, services.py, blackbox_manager.py funcionam

---

### Testes de Documentação

- [ ] **SPRINT1_RELATORIO_FINAL_IMPLEMENTACAO.md existe**
  - Arquivo: `SPRINT1_RELATORIO_FINAL_IMPLEMENTACAO.md`
  - Deve ter seção: RESUMO EXECUTIVO, ARQUIVOS MODIFICADOS, RESULTADOS DOS TESTES
  - Validação: `ls SPRINT1_RELATORIO_FINAL_IMPLEMENTACAO.md`

- [ ] **SPRINT1_DOCUMENTACAO_DETALHADA_COMPLETA.md existe**
  - Arquivo: `SPRINT1_DOCUMENTACAO_DETALHADA_COMPLETA.md`
  - Deve ter ~2334 linhas
  - Validação: `wc -l SPRINT1_DOCUMENTACAO_DETALHADA_COMPLETA.md`

- [ ] **ANALISE_GAPS_SPRINT1.md existe**
  - Arquivo: `ANALISE_GAPS_SPRINT1.md`
  - Deve documentar: 6 gaps críticos identificados
  - Validação: `ls ANALISE_GAPS_SPRINT1.md`

- [ ] **PLANO_FINAL_CORRECOES_SPRINT1_OFICIAL.md existe**
  - Arquivo: `PLANO_FINAL_CORRECOES_SPRINT1_OFICIAL.md`
  - Deve consolidar: 5 fontes de análise
  - Deve ter: 12 fases de implementação
  - Validação: `ls PLANO_FINAL_CORRECOES_SPRINT1_OFICIAL.md`

- [ ] **SPRINT2_PLANO_CONSOLIDADO_OFICIAL.md existe**
  - Arquivo: `SPRINT2_PLANO_CONSOLIDADO_OFICIAL.md`
  - Deve documentar: LocalCache, Cache Management, BadgeStatus
  - Validação: `ls SPRINT2_PLANO_CONSOLIDADO_OFICIAL.md`

- [ ] **SPRINT2_RELATORIO_FINAL.md existe**
  - Arquivo: `SPRINT2_RELATORIO_FINAL.md`
  - Deve ter: status ✅ CONCLUÍDO COM SUCESSO
  - Deve documentar: performance 128x, hit rate 91.7%
  - Validação: `ls SPRINT2_RELATORIO_FINAL.md`

- [ ] **CORRECOES_CRITICAS_POS_SPRINT2.md existe**
  - Arquivo: `CORRECOES_CRITICAS_POS_SPRINT2.md`
  - Deve documentar: 3 bugs corrigidos (KV, loop circular, cache Vite)
  - Validação: `ls CORRECOES_CRITICAS_POS_SPRINT2.md`

---

## 📊 RESUMO DE VALIDAÇÃO

### Contadores

- **SPRINT 1 - Backend**: [ ] / 75 itens
- **SPRINT 1 - Frontend**: [ ] / 10 itens
- **SPRINT 1 - Correções**: [ ] / 5 itens
- **SPRINT 2 - Backend**: [ ] / 40 itens
- **SPRINT 2 - Frontend**: [ ] / 30 itens
- **Correções Críticas**: [ ] / 5 itens
- **Testes**: [ ] / 35 itens

**TOTAL**: [ ] / 200 itens

---

## 🎯 CRITÉRIOS DE ACEITAÇÃO

### Sprint 1

- [ ] **Performance**: Timeout reduzido de 33s → <2.5s
- [ ] **Latência**: 150ms → <50ms (todos nodes online)
- [ ] **Race Condition**: 0 crashes frontend
- [ ] **Métricas**: 4+ métricas Prometheus funcionando
- [ ] **Backward Compatibility**: 100% mantida
- [ ] **Documentação**: Todos arquivos MD criados
- [ ] **Testes**: Todos 4 testes passando

### Sprint 2

- [ ] **Cache Local**: Hit rate >= 90%
- [ ] **Performance Cache**: 1290ms → <10ms
- [ ] **API Cache**: 6 endpoints funcionando
- [ ] **Dashboard Visual**: Página Cache Management carregando
- [ ] **BadgeStatus**: Integrado em 3 páginas
- [ ] **Cleanup**: ~320 linhas de código obsoleto removidas
- [ ] **Bug KV**: Corrigido e testado

### Correções Críticas

- [ ] **Loop Circular**: Backend inicia sem erros
- [ ] **KV Parsing**: Sites carregam corretamente
- [ ] **Cache Vite**: Frontend compila sem erros de parsing

---

**FIM DO CHECKLIST**

**Como Usar Este Checklist:**
1. Copie este arquivo para sua área de trabalho
2. Marque [x] conforme valida cada item
3. Execute os comandos de validação fornecidos
4. Documente quaisquer discrepâncias encontradas
5. Repita validação após correções

**Boa sorte na validação!** 🚀
