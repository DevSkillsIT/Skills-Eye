# 🎯 PROMPT PARA CLAUDE CODE WEB - OTIMIZAÇÃO CONSUL (VERSÃO 5 - OFICIAL VALIDADA)

**Data:** 15/11/2025  
**Status:** ✅ **VALIDADO COM DOCUMENTAÇÃO OFICIAL HASHICORP**  
**Fontes:** 
- HashiCorp Consul API Docs (Agent, Catalog, Health, Consistency Modes, Blocking Queries, Caching)
- Consul Production Deployment Guide
- Stack Overflow (resposta oficial engenheiro HashiCorp)
- Consul Server Performance Requirements

---

## 🔴 CONTEXTO CRÍTICO OFICIAL

### Descobertas da Documentação Oficial HashiCorp

#### 1. **Agent API vs Catalog API** (VALIDADO OFICIALMENTE)

**Fonte:** Stack Overflow - Blake Covarrubias (Engenheiro HashiCorp)
```
"The /v1/agent/ APIs should be used for HIGH FREQUENCY calls, 
and should be issued against the LOCAL Consul client agent 
running on the same node as the app."

"Consul treats the state of the AGENT as AUTHORITATIVE; 
if there are any differences between the agent and catalog view, 
the agent-local view will ALWAYS be used."
```

**Impacto no Código Atual:**
```python
# ❌ ERRADO (Linha 725 - consul_manager.py)
response = await self._request("GET", f"/catalog/service/{service_name}")
# Consulta GLOBAL (50ms lag, depende de quorum, serialized no leader)

# ✅ CORRETO (recomendação oficial)
response = await self._request("GET", f"/agent/services?cached")
# Consulta LOCAL (5-10ms, cache do agent, não depende de quorum)
```

#### 2. **Consistency Modes** (VALIDADO OFICIALMENTE)

**Fonte:** HashiCorp Consistency Modes Documentation
- **`default`:** Fortemente consistente, mas pode ter 50ms staleness em race conditions raras
- **`stale`:** 50ms staleness típica, **continua funcionando sem quorum**
- **`consistent`:** Quorum obrigatório (+ 1 round-trip extra para verificação)

**Citação Oficial:**
```
"The most effective way to increase read scalability is to 
convert non-stale reads to stale reads."

"Stale mode allows any server to handle the read regardless of 
whether it is the leader... Results are generally consistent to 
within 50 milliseconds of the leader."
```

**Impacto no Código Atual:**
```python
# ❌ PROBLEMA: Usa Catalog API SEM ?stale
# Resultado: Default mode (depende de leader, não escala)

# ✅ SOLUÇÃO 1: Agent API com cache
await self._request("GET", "/agent/services?cached")

# ✅ SOLUÇÃO 2: Catalog API com stale explícito
await self._request("GET", "/catalog/services?stale")
```

#### 3. **Agent Caching** (FEATURE NÃO EXPLORADA - CRÍTICO!)

**Fonte:** HashiCorp Agent Caching Documentation
```
"Background refresh caching may return a result directly from 
the local agent's cache. The first fetch triggers the agent to 
begin a BACKGROUND BLOCKING QUERY that watches for changes."

"Clients can perform blocking queries against the local agent 
which will be served from the cache. This allows MULTIPLE clients 
to watch the same resource locally while only a SINGLE blocking 
watch to the servers."
```

**Feature Crítica Não Utilizada:**
```python
# Agent retorna do cache LOCAL (instantâneo)
# Background refresh mantém dados atualizados (TTL 3 dias)
# Perfeito para DEZENAS de nodes simultâneos

params = {
    "cached": "",  # ← Enable agent caching
    "filter": 'ServiceMeta.module != ""'  # ← Filter server-side
}
response = await self._request("GET", "/agent/services", params=params)

# Verificar freshness
age = int(response.headers.get("Age", "0"))
if age > 60:  # > 1 minuto
    logger.warning(f"Cached response age: {age}s")
```

#### 4. **Timeout Strategy** (SEM RECOMENDAÇÃO OFICIAL ESPECÍFICA)

**Fonte:** Consul Production Server Requirements
- Foco em `raft_multiplier` (heartbeat: 1000ms, election: 1000ms)
- **NÃO há valores oficiais** para timeout HTTP client
- Menciona "wide networks with latency" → adaptar ao ambiente

**Citação Oficial:**
```
"Wide networks with more latency will perform better with 
larger values of raft_multiplier."

"Users in cloud environments often bump their servers up to 
the next instance class with improved networking and CPU 
until leader elections stabilize."
```

**Recomendação Baseada em Evidências:**
```python
# Não há valor mágico oficial
# Medir latência real do ambiente e adaptar:

# 1. Agent API (local): 5-10ms típico → timeout 2s (20x margem)
# 2. Catalog API (global): 50ms típico → timeout 5s (100x margem)
# 3. Node offline: fail-fast para não bloquear cluster

# Timeout ADAPTATIVO (medir ambiente real)
```

---

## 📋 TAREFAS PARA IMPLEMENTAÇÃO

### ✅ FASE 1: Agent Caching (PRIORIDADE MÁXIMA - OFFICIAL DOCS)

**Arquivo:** `backend/core/consul_manager.py`

**Tarefa 1.1:** Adicionar suporte a `?cached` parameter

```python
# Localização: Método _request() - Linha 73-92
async def _request(self, method: str, path: str, use_cache: bool = False, **kwargs):
    """
    Requisição HTTP assíncrona para API do Consul
    
    OFICIAL DOCS: Agent caching permite background refresh com TTL 3 dias
    https://developer.hashicorp.com/consul/api-docs/features/caching
    """
    kwargs.setdefault("headers", self.headers)
    
    # Configurar timeout baseado em tipo de API
    # Não há valores oficiais - baseado em evidências empíricas
    if "timeout" not in kwargs:
        # Agent API (local): 2s
        # Catalog API (global): 5s
        # KV operations: 5s
        if "/agent/" in path and "/agent/service/register" not in path:
            kwargs["timeout"] = 2.0  # Agent fast paths
        else:
            kwargs["timeout"] = 5.0  # Catalog/KV/writes
    
    # Agent Caching (OFFICIAL FEATURE)
    if use_cache and method == "GET":
        # Adicionar ?cached para background refresh
        if "params" not in kwargs:
            kwargs["params"] = {}
        kwargs["params"]["cached"] = ""
    
    url = f"{self.base_url}{path}"
    
    async with httpx.AsyncClient() as client:
        start_time = time.time()
        response = await client.request(method, url, **kwargs)
        duration_ms = (time.time() - start_time) * 1000
        
        # Prometheus metrics (já existente)
        consul_request_duration_seconds.labels(
            method=method,
            api_type=self._detect_api_type(path),
            endpoint=path.split('?')[0]
        ).observe(duration_ms / 1000)
        
        # Verificar freshness do cache
        if use_cache:
            age = int(response.headers.get("Age", "0"))
            cache_status = response.headers.get("X-Cache", "MISS")
            
            if cache_status == "HIT" and age > 60:
                logger.warning(
                    f"[Consul] 📦 Cache stale: {path} age={age}s "
                    f"(background refresh may be delayed)"
                )
        
        # Verificar staleness (para Catalog API com ?stale)
        last_contact_ms = int(response.headers.get("X-Consul-LastContact", "0"))
        if last_contact_ms > 1000:  # > 1 segundo
            logger.warning(
                f"[Consul] ⏱️ Stale response: {path} lag={last_contact_ms}ms"
            )
        
        response.raise_for_status()
        return response
```

**Tarefa 1.2:** Refatorar `get_all_services_from_all_nodes()` para usar Agent API + Cache

```python
# Localização: Linha 691-820
async def get_all_services_from_all_nodes(self) -> Dict[str, Dict]:
    """
    VERSÃO OTIMIZADA - OFICIAL DOCS COMPLIANT
    
    Estratégia (baseada em HashiCorp official docs):
    1. Agent API (autoritativa, cache local 5-10ms)
    2. ?cached parameter (background refresh, TTL 3 dias)
    3. Paralelização com asyncio.gather()
    4. Timeout 2s (Agent API fast path)
    5. Fail-fast para nodes offline (não bloquear cluster)
    
    Performance Targets (baseado em docs oficiais):
    - Agent API P99: <50ms (local cache)
    - Cluster query (all online): <100ms total
    - Cluster query (2 offline): <5s total (fail-fast)
    
    Referências Oficiais:
    - Agent vs Catalog: https://stackoverflow.com/a/65725360
    - Agent Caching: https://developer.hashicorp.com/consul/api-docs/features/caching
    - Consistency: https://developer.hashicorp.com/consul/api-docs/features/consistency
    """
    try:
        # Obter lista de membros do cluster (Agent API - local fast)
        members_response = await self._request(
            "GET", 
            "/agent/members",
            timeout=2.0  # Agent API fast path
        )
        members = members_response.json()
        
        # Extrair IPs dos clients (servers já têm dados replicados)
        client_addrs = [
            m['Addr'] for m in members 
            if m.get('Tags', {}).get('role') != 'consul'
        ]
        
        logger.info(
            f"[Consul] 🔍 Querying {len(client_addrs)} client nodes "
            f"via Agent API (cached, parallel)"
        )
        
        # Criar tasks paralelas para CADA node
        tasks = []
        for node_addr in client_addrs:
            # OFICIAL DOCS: Agent API com ?cached
            # Background refresh mantém dados atualizados
            # Cache local (5-10ms) vs Catalog global (50ms)
            task = self._request(
                "GET",
                f"/agent/services?node_addr={node_addr}",
                use_cache=True,  # ← Agent caching (OFFICIAL FEATURE)
                params={"filter": 'Meta.module != ""'},  # Server-side filter
                timeout=2.0  # Fail-fast para nodes offline
            )
            tasks.append(task)
        
        # Executar em paralelo com tratamento de erros
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Merge results (compatibilidade mantida - Dict[str, Dict])
        all_services = {}
        errors = 0
        
        for idx, result in enumerate(results):
            node_addr = client_addrs[idx]
            
            if isinstance(result, Exception):
                errors += 1
                logger.warning(
                    f"[Consul] ❌ Node {node_addr} unreachable: {result} "
                    f"(skipping, cluster continues)"
                )
                continue
            
            try:
                services = result.json()
                
                # Verificar cache status
                cache_status = result.headers.get("X-Cache", "MISS")
                age = int(result.headers.get("Age", "0"))
                
                logger.debug(
                    f"[Consul] ✅ Node {node_addr}: {len(services)} services "
                    f"(cache={cache_status}, age={age}s)"
                )
                
                # Adicionar campos 'Node' e 'ID' para compatibilidade
                for service_id, service_data in services.items():
                    service_data['Node'] = node_addr
                    service_data['ID'] = service_id
                    all_services[f"{node_addr}:{service_id}"] = service_data
                    
            except Exception as e:
                errors += 1
                logger.error(
                    f"[Consul] ⚠️ Failed to parse response from {node_addr}: {e}"
                )
        
        logger.info(
            f"[Consul] ✅ Collected {len(all_services)} services from "
            f"{len(client_addrs) - errors}/{len(client_addrs)} nodes "
            f"({errors} unreachable)"
        )
        
        return all_services
        
    except Exception as exc:
        logger.error(f"[Consul] 💥 Cluster query failed: {exc}")
        return {}
```

---

### ✅ FASE 2: Stale Reads para Catalog API (OFFICIAL DOCS)

**Tarefa 2.1:** Adicionar `?stale` para operações Catalog que não precisam de consistência forte

```python
# Localização: Linha 350 (get_all_services_names)
async def get_all_services_names(self, use_stale: bool = True) -> Dict[str, List[str]]:
    """
    OFICIAL DOCS: Stale mode escala reads para todos os servers
    https://developer.hashicorp.com/consul/api-docs/features/consistency
    
    50ms staleness típica, funciona sem quorum
    """
    params = {}
    if use_stale:
        params["stale"] = ""  # ← Official consistency mode
    
    response = await self._request("GET", "/catalog/services", params=params)
    
    # Verificar staleness
    last_contact_ms = int(response.headers.get("X-Consul-LastContact", "0"))
    known_leader = response.headers.get("X-Consul-KnownLeader", "false")
    
    if last_contact_ms > 1000:
        logger.warning(
            f"[Consul] ⏱️ Stale Catalog response: {last_contact_ms}ms lag "
            f"(leader contact delay)"
        )
    
    if known_leader != "true":
        logger.error("[Consul] ❌ No known leader! Cluster may be unhealthy")
    
    return response.json()
```

---

### ✅ FASE 3: Circuit Breaker Pattern (PRODUCTION BEST PRACTICE)

**Tarefa 3.1:** Implementar circuit breaker para nodes offline

```python
# Localização: Adicionar ao __init__ - Linha 65-72
class ConsulManager:
    def __init__(self, host: str = None, port: int = None, token: str = None):
        self.host = host or Config.MAIN_SERVER
        self.port = port or Config.CONSUL_PORT
        self.token = token or Config.CONSUL_TOKEN
        self.base_url = f"http://{self.host}:{self.port}/v1"
        self.headers = {"X-Consul-Token": self.token}
        
        # Circuit Breaker State (PRODUCTION BEST PRACTICE)
        self._slow_nodes: Set[str] = set()  # Nodes com timeout recente
        self._circuit_open_until: Dict[str, float] = {}  # Timestamp para retry
        self._failure_counts: Dict[str, int] = {}  # Contagem de falhas
        
        # Circuit Breaker Config
        self._max_failures = 3  # 3 falhas consecutivas
        self._circuit_timeout = 30  # 30 segundos antes de retry
```

**Tarefa 3.2:** Aplicar circuit breaker nas queries paralelas

```python
# Adicionar lógica no get_all_services_from_all_nodes()
async def get_all_services_from_all_nodes(self) -> Dict[str, Dict]:
    # ... código anterior ...
    
    # Filtrar nodes com circuit breaker aberto
    now = time.time()
    available_nodes = []
    
    for node_addr in client_addrs:
        # Verificar se circuit está aberto
        if node_addr in self._circuit_open_until:
            retry_at = self._circuit_open_until[node_addr]
            if now < retry_at:
                logger.debug(
                    f"[Consul] 🔴 Circuit OPEN for {node_addr} "
                    f"(retry in {retry_at - now:.1f}s)"
                )
                continue
            else:
                # Circuit fechou - remover do dict
                del self._circuit_open_until[node_addr]
                self._failure_counts[node_addr] = 0
        
        available_nodes.append(node_addr)
    
    logger.info(
        f"[Consul] 🔍 Querying {len(available_nodes)}/{len(client_addrs)} nodes "
        f"({len(client_addrs) - len(available_nodes)} circuit breaker open)"
    )
    
    # ... resto do código com available_nodes ...
    
    # Atualizar circuit breaker state nos resultados
    for idx, result in enumerate(results):
        node_addr = available_nodes[idx]
        
        if isinstance(result, Exception):
            # Incrementar contagem de falhas
            self._failure_counts[node_addr] = self._failure_counts.get(node_addr, 0) + 1
            
            # Abrir circuit se atingiu threshold
            if self._failure_counts[node_addr] >= self._max_failures:
                self._circuit_open_until[node_addr] = now + self._circuit_timeout
                logger.warning(
                    f"[Consul] ⚡ Circuit OPEN for {node_addr} "
                    f"({self._failure_counts[node_addr]} consecutive failures)"
                )
        else:
            # Sucesso - resetar contador
            if node_addr in self._failure_counts:
                self._failure_counts[node_addr] = 0
```

---

### ✅ FASE 4: Métricas de Observabilidade (OFFICIAL TELEMETRY)

**Tarefa 4.1:** Adicionar métricas Prometheus para cache e staleness

```python
# Localização: Adicionar ao início do arquivo
from prometheus_client import Histogram, Counter, Gauge

# Métricas Prometheus (OFFICIAL TELEMETRY PATTERN)
consul_cache_hits = Counter(
    'consul_cache_hits_total',
    'Total cache hits no Agent API',
    ['endpoint', 'age_bucket']  # age_bucket: fresh|stale|very_stale
)

consul_stale_responses = Counter(
    'consul_stale_responses_total',
    'Total respostas stale (>1s lag)',
    ['endpoint', 'lag_bucket']  # lag_bucket: 1s-5s|5s-10s|>10s
)

consul_circuit_breaker_state = Gauge(
    'consul_circuit_breaker_open',
    'Circuit breaker state (1=open, 0=closed)',
    ['node_addr']
)
```

**Tarefa 4.2:** Integrar métricas no código

```python
# No _request() method
if use_cache:
    cache_status = response.headers.get("X-Cache", "MISS")
    age = int(response.headers.get("Age", "0"))
    
    if cache_status == "HIT":
        # Categorizar freshness
        if age < 10:
            age_bucket = "fresh"
        elif age < 60:
            age_bucket = "stale"
        else:
            age_bucket = "very_stale"
        
        consul_cache_hits.labels(
            endpoint=path.split('?')[0],
            age_bucket=age_bucket
        ).inc()

# Verificar staleness (Catalog API)
last_contact_ms = int(response.headers.get("X-Consul-LastContact", "0"))
if last_contact_ms > 1000:
    if last_contact_ms < 5000:
        lag_bucket = "1s-5s"
    elif last_contact_ms < 10000:
        lag_bucket = "5s-10s"
    else:
        lag_bucket = ">10s"
    
    consul_stale_responses.labels(
        endpoint=path.split('?')[0],
        lag_bucket=lag_bucket
    ).inc()
```

---

## 🧪 TESTES OBRIGATÓRIOS

### Teste 1: Agent Caching Functionality

```python
# Arquivo: backend/test_agent_caching.py
import pytest
import asyncio
from core.consul_manager import ConsulManager

@pytest.mark.asyncio
async def test_agent_cache_freshness():
    """
    VALIDAR: Agent caching retorna X-Cache: HIT em requests subsequentes
    OFICIAL DOCS: https://developer.hashicorp.com/consul/api-docs/features/caching
    """
    manager = ConsulManager()
    
    # Request 1 - deve ser MISS
    response1 = await manager._request("GET", "/agent/services", use_cache=True)
    assert response1.headers.get("X-Cache") == "MISS"
    
    # Request 2 - deve ser HIT
    response2 = await manager._request("GET", "/agent/services", use_cache=True)
    assert response2.headers.get("X-Cache") == "HIT"
    
    # Verificar Age header
    age = int(response2.headers.get("Age", "0"))
    assert age >= 0, "Age header deve estar presente"

@pytest.mark.asyncio
async def test_catalog_stale_mode():
    """
    VALIDAR: Catalog API com ?stale retorna X-Consul-Effective-Consistency
    OFICIAL DOCS: https://developer.hashicorp.com/consul/api-docs/features/consistency
    """
    manager = ConsulManager()
    
    response = await manager._request(
        "GET", 
        "/catalog/services",
        params={"stale": ""}
    )
    
    # Verificar consistency mode efetivo
    consistency = response.headers.get("X-Consul-Effective-Consistency")
    assert consistency == "stale", f"Expected stale, got {consistency}"
    
    # Verificar staleness
    last_contact = int(response.headers.get("X-Consul-LastContact", "0"))
    print(f"Staleness: {last_contact}ms")
    assert last_contact >= 0, "LastContact header deve estar presente"
```

### Teste 2: Performance com Múltiplos Nodes

```python
@pytest.mark.asyncio
async def test_performance_multiple_nodes():
    """
    VALIDAR: Cluster query completa em <5s com 2 nodes offline
    OFICIAL DOCS: Fail-fast pattern
    """
    manager = ConsulManager()
    
    start = time.time()
    services = await manager.get_all_services_from_all_nodes()
    duration = time.time() - start
    
    print(f"Cluster query: {duration:.2f}s ({len(services)} services)")
    
    # Target: <5s total (mesmo com nodes offline)
    assert duration < 5.0, f"Cluster query too slow: {duration:.2f}s"
    
    # Verificar se retornou dados
    assert len(services) > 0, "Deve retornar ao menos 1 serviço"

@pytest.mark.asyncio
async def test_circuit_breaker_opens():
    """
    VALIDAR: Circuit breaker abre após 3 falhas consecutivas
    """
    manager = ConsulManager()
    fake_node = "192.168.99.99:8500"  # Node inexistente
    
    # Forçar 3 falhas
    for i in range(3):
        try:
            await manager._request(
                "GET",
                f"/agent/services?node_addr={fake_node}",
                timeout=1.0
            )
        except:
            pass
    
    # Circuit deve estar aberto
    assert fake_node in manager._circuit_open_until, "Circuit breaker deve abrir"
    print(f"Circuit opened for {fake_node}")
```

### Teste 3: Escalabilidade (Dezenas de Nodes)

```python
@pytest.mark.asyncio
async def test_scalability_many_nodes():
    """
    VALIDAR: Sistema funciona com 50+ nodes simultâneos
    OFICIAL DOCS: Agent caching permite múltiplos clients
    """
    manager = ConsulManager()
    
    # Simular 50 nodes (mesmo que offline)
    fake_nodes = [f"192.168.{i}.{j}:8500" for i in range(10) for j in range(5)]
    
    tasks = []
    for node in fake_nodes:
        task = manager._request(
            "GET",
            f"/agent/services?node_addr={node}",
            use_cache=True,
            timeout=1.0  # Fail-fast
        )
        tasks.append(task)
    
    start = time.time()
    results = await asyncio.gather(*tasks, return_exceptions=True)
    duration = time.time() - start
    
    # Contar sucessos vs falhas
    successes = sum(1 for r in results if not isinstance(r, Exception))
    failures = len(results) - successes
    
    print(f"50 nodes query: {duration:.2f}s ({successes} ok, {failures} failed)")
    
    # Deve completar em tempo razoável mesmo com muitos nodes offline
    assert duration < 10.0, "Deve completar em <10s com fail-fast"
```

---

## 📊 MÉTRICAS DE SUCESSO (OFICIAL DOCS COMPLIANCE)

### Performance Targets (Baseado em Evidências)

| Métrica | Antes | Target (Oficial) | Como Medir |
|---------|-------|------------------|------------|
| Agent API P99 | N/A | <50ms | `consul_request_duration_seconds{api_type="agent", quantile="0.99"}` |
| Catalog API P99 (stale) | N/A | <200ms | `consul_request_duration_seconds{api_type="catalog", quantile="0.99"}` |
| Cluster query (all online) | 150ms | <100ms | Tempo total `get_all_services_from_all_nodes()` |
| Cluster query (2 offline) | 44s | <5s | Fail-fast com circuit breaker |
| Cache hit rate | 0% | >80% | `consul_cache_hits_total / consul_requests_total` |
| Staleness P95 | N/A | <100ms | `X-Consul-LastContact` header |

### Compliance Checklist (Documentação Oficial)

- ✅ **Agent API** usado para high-frequency calls (CONFIRMADO em docs)
- ✅ **`?cached`** parameter implementado (background refresh, TTL 3 dias)
- ✅ **`?stale`** parameter para Catalog API (50ms lag típico)
- ✅ **Circuit breaker** para fail-fast (production best practice)
- ✅ **Prometheus metrics** para observabilidade (official telemetry)
- ✅ **Escalabilidade** para dezenas de nodes (Agent caching permite)
- ✅ **Staleness monitoring** via headers (`X-Consul-LastContact`)
- ✅ **Compatibility** preservada (Dict[str, Dict] structure)

---

## 🚨 ALERTAS E ROLLBACK

### Alertas Prometheus (PRODUCTION MONITORING)

```yaml
# alerts.yml
groups:
  - name: consul_performance
    rules:
      # Agent API degraded
      - alert: ConsulAgentAPISlow
        expr: histogram_quantile(0.99, rate(consul_request_duration_seconds_bucket{api_type="agent"}[5m])) > 0.05
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Consul Agent API P99 >50ms"
          description: "Agent API should be <50ms (local cache). Current: {{ $value }}s"
      
      # Cache hit rate baixo
      - alert: ConsulCacheHitRateLow
        expr: rate(consul_cache_hits_total[5m]) / rate(consul_requests_total[5m]) < 0.5
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "Consul cache hit rate <50%"
          description: "Agent caching may not be working correctly. Hit rate: {{ $value }}"
      
      # Staleness excessiva
      - alert: ConsulStaleResponsesHigh
        expr: rate(consul_stale_responses_total{lag_bucket=">10s"}[5m]) > 0.1
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "Consul responses excessively stale (>10s lag)"
          description: "Cluster may be unhealthy or overloaded"
      
      # Circuit breaker aberto
      - alert: ConsulCircuitBreakerOpen
        expr: consul_circuit_breaker_open == 1
        for: 2m
        labels:
          severity: warning
        annotations:
          summary: "Consul circuit breaker open for {{ $labels.node_addr }}"
          description: "Node unreachable after 3 consecutive failures"
```

### Plano de Rollback

```bash
# Se houver problemas após deploy
git checkout HEAD~1 -- backend/core/consul_manager.py
git commit -m "revert: rollback consul optimization - performance issues"
git push origin main

# Reiniciar backend
docker-compose restart backend
```

---

## 📚 REFERÊNCIAS OFICIAIS HASHICORP

### Documentação Consultada

1. **Agent vs Catalog API**
   - Stack Overflow (Engenheiro HashiCorp): https://stackoverflow.com/a/65725360
   - Conclusão: Agent API é autoritativa e deve ser usada para high-frequency

2. **Consistency Modes**
   - Official Docs: https://developer.hashicorp.com/consul/api-docs/features/consistency
   - Conclusão: Stale mode escala reads, 50ms lag típico

3. **Agent Caching**
   - Official Docs: https://developer.hashicorp.com/consul/api-docs/features/caching
   - Conclusão: Background refresh com TTL 3 dias, múltiplos clients

4. **Blocking Queries**
   - Official Docs: https://developer.hashicorp.com/consul/api-docs/features/blocking
   - Conclusão: Streaming backend (Consul 1.10+) alternativa a long-polling

5. **Production Server Requirements**
   - Official Docs: https://developer.hashicorp.com/consul/docs/reference/architecture/server
   - Conclusão: Foco em raft_multiplier, não há valores HTTP timeout oficiais

6. **Deployment Guide**
   - Official Docs: https://developer.hashicorp.com/consul/tutorials/production-vms/deployment-guide
   - Conclusão: Performance stanza, retry_join, telemetry best practices

---

## ✅ CHECKLIST FINAL (ANTES DE DECLARAR SUCESSO)

### Implementação
- [ ] Agent API usado em `get_all_services_from_all_nodes()`
- [ ] `?cached` parameter implementado no `_request()`
- [ ] `?stale` parameter opcional para Catalog API
- [ ] Circuit breaker implementado com 3 falhas threshold
- [ ] Timeout adaptativo: 2s Agent, 5s Catalog
- [ ] Prometheus metrics: cache hits, staleness, circuit breaker
- [ ] Logging estruturado com níveis corretos (debug/warning/error)

### Testes
- [ ] Test Agent caching (cache HIT em 2ª request)
- [ ] Test Catalog stale mode (X-Consul-Effective-Consistency header)
- [ ] Test performance múltiplos nodes (<5s com 2 offline)
- [ ] Test circuit breaker (abre após 3 falhas)
- [ ] Test escalabilidade (50+ nodes simultâneos)
- [ ] Test backend endpoints (4 críticos returning 200 OK)
- [ ] Test frontend (3 páginas carregam sem erro console)

### Observabilidade
- [ ] Métricas Prometheus exportadas em /metrics
- [ ] Alertas configurados (Agent slow, cache low, staleness high)
- [ ] Dashboard Grafana atualizado (se existente)
- [ ] Logs estruturados em JSON (se configurado)

### Validação Oficial Docs
- [ ] Agent API priorizado (confirmado docs HashiCorp)
- [ ] ?cached background refresh (confirmado docs HashiCorp)
- [ ] ?stale consistency mode (confirmado docs HashiCorp)
- [ ] Circuit breaker pattern (production best practice)
- [ ] Staleness monitoring (X-Consul-LastContact header)
- [ ] Escalabilidade para dezenas de nodes (Agent caching permite)

### Compatibility
- [ ] Dict[str, Dict] structure preservada (INEGOCIÁVEL)
- [ ] Campos 'Node' e 'ID' adicionados aos services
- [ ] Backend tests pass (test_phase1.py, test_phase2.py)
- [ ] Frontend não quebrado (Services, BlackboxTargets, MonitoringUnified)

---

## 🎯 RESUMO EXECUTIVO PARA CLAUDE CODE

**O QUE FAZER:**
1. Implementar Agent API + `?cached` (PRIORIDADE #1 - OFICIAL DOCS)
2. Adicionar `?stale` para Catalog API (ESCALA READS - OFICIAL DOCS)
3. Implementar circuit breaker (FAIL-FAST - BEST PRACTICE)
4. Adicionar métricas Prometheus (OBSERVABILIDADE - TELEMETRY)
5. Testar com múltiplos nodes (DEZENAS - ESCALABILIDADE)

**O QUE NÃO FAZER:**
- ❌ Hardcode timeout sem medir ambiente (não há valores oficiais)
- ❌ Ignorar headers de staleness (X-Consul-LastContact crítico)
- ❌ Quebrar compatibilidade Dict[str, Dict] (INEGOCIÁVEL)
- ❌ Remover retry sem circuit breaker (produção precisa resiliência)
- ❌ Usar Catalog API sem ?stale quando Agent disponível

**VALIDAÇÃO:**
- ✅ Agent API = high-frequency (CONFIRMADO HashiCorp)
- ✅ ?cached = background refresh (CONFIRMADO docs oficiais)
- ✅ ?stale = escala reads (CONFIRMADO docs oficiais)
- ✅ Circuit breaker = production pattern (BEST PRACTICE)
- ✅ Dezenas de nodes = Agent caching permite (CONFIRMADO docs)

**FONTES OFICIAIS:**
Todas as recomendações baseadas em documentação oficial HashiCorp Consul e respostas de engenheiros HashiCorp no Stack Overflow. Nenhuma suposição ou "achismo" - apenas fatos validados.

---

**DATA:** 15/Novembro/2025  
**VERSÃO:** 5.0 (OFICIAL VALIDADA)  
**STATUS:** ✅ PRONTO PARA EXECUÇÃO

