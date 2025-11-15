# 🎯 SPRINT 1 - Otimização Consul (V4 - ANÁLISE COMPLETA)
**Data:** 15/11/2025  
**Branch:** `fix/consul-optimization-complete-20251115`  
**Commits:** português-BR, mensagens claras

---

## ⚠️ LEITURA OBRIGATÓRIA ANTES DE INICIAR

**DOCUMENTOS PRÉ-REQUISITO:**
1. `MAPEAMENTO_COMPLETO_CONSUL_INTEGRACAO.md` (TODOS os arquivos/endpoints)
2. `ADENDO_CLAUDE_CODE_PONTOS_ATENCAO.md` (problemas sistêmicos + soluções)

**MUDANÇA DE ESCOPO:**
- ❌ **ANTES:** Otimizar apenas `get_all_services_from_all_nodes()`
- ✅ **AGORA:** Otimizar TODA a infraestrutura Consul (35 métodos, 22 endpoints)

**RAZÃO:**
Análise completa revelou que o problema não é pontual, mas **SISTÊMICO**:
- Timeout de 5s + retry 3x = 22s por node offline (afeta TUDO)
- Mistura Agent/Catalog sem critério = performance inconsistente
- Zero observabilidade = impossível debugar em produção

---

## 🎯 OBJETIVOS SPRINT 1 (AMPLIADO)

### 🔴 CRÍTICO #1: Otimizar `_request()` (Fundação)
**Arquivo:** `backend/core/consul_manager.py` linha 75-92  
**Impacto:** Beneficia TODAS as 35 operações Consul

**Problemas atuais:**
```python
# ❌ PROBLEMA 1: Timeout fixo 5s para TUDO
kwargs.setdefault("timeout", 5)  # Agent (5ms) usa mesmo timeout que KV (500ms)

# ❌ PROBLEMA 2: Retry agressivo SEMPRE
@retry_with_backoff(max_retries=3)  # Agent não precisa 3 retries!

# ❌ PROBLEMA 3: Zero métricas
# Não tem instrumentação Prometheus

# ❌ PROBLEMA 4: Logs inadequados
print(f"Erro: {e}")  # Não tem context, level, structured logging
```

**Solução completa:**
```python
from prometheus_client import Histogram, Counter
import time
import logging

logger = logging.getLogger(__name__)

# Métricas Prometheus
consul_request_duration = Histogram(
    'consul_request_duration_seconds',
    'Latência de requisições ao Consul',
    ['method', 'api_type', 'endpoint']
)

consul_requests_total = Counter(
    'consul_requests_total',
    'Total de requisições ao Consul',
    ['method', 'api_type', 'endpoint', 'status']
)

async def _request(self, method: str, path: str, timeout: int = None, max_retries: int = None, **kwargs):
    """
    Requisição HTTP otimizada para Consul com:
    - Timeout variável por tipo de API
    - Retry condicional
    - Métricas Prometheus
    - Logs estruturados
    
    Args:
        timeout: Timeout customizado (default: 2s para Agent, 5s para outros)
        max_retries: Retries customizados (default: 1 para Agent, 2 para outros)
    """
    # Determinar tipo de API
    api_type = 'agent' if '/agent/' in path else \
               'catalog' if '/catalog/' in path else \
               'kv' if '/kv/' in path else \
               'health' if '/health/' in path else 'other'
    
    # Timeout inteligente (Agent é rápido, não precisa 5s)
    if timeout is None:
        timeout = 2 if api_type == 'agent' else 5
    
    # Retry condicional (Agent não precisa múltiplos retries)
    if max_retries is None:
        max_retries = 1 if api_type == 'agent' else 2
    
    kwargs.setdefault("headers", self.headers)
    kwargs.setdefault("timeout", timeout)
    url = f"{self.base_url}{path}"
    
    # Simplificar endpoint para label (max 50 chars)
    endpoint_label = path[:50]
    
    retries = 0
    last_error = None
    
    while retries <= max_retries:
        start_time = time.time()
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.request(method, url, **kwargs)
                response.raise_for_status()
                
                duration = time.time() - start_time
                
                # Registrar métricas
                consul_request_duration.labels(
                    method=method,
                    api_type=api_type,
                    endpoint=endpoint_label
                ).observe(duration)
                
                consul_requests_total.labels(
                    method=method,
                    api_type=api_type,
                    endpoint=endpoint_label,
                    status='success'
                ).inc()
                
                # Alerta se Agent demorou muito (deveria ser <50ms)
                if api_type == 'agent' and duration > 0.05:
                    logger.warning(
                        f"[Consul] Agent API lenta: {method} {path} "
                        f"demorou {duration*1000:.0f}ms (esperado <50ms)"
                    )
                
                logger.debug(
                    f"[Consul] ✅ {method} {path} → {response.status_code} "
                    f"({duration*1000:.0f}ms, retry={retries})"
                )
                
                return response
                
        except httpx.HTTPStatusError as e:
            duration = time.time() - start_time
            last_error = e
            
            # Não fazer retry em erros 4xx (cliente)
            if 400 <= e.response.status_code < 500:
                consul_requests_total.labels(
                    method=method,
                    api_type=api_type,
                    endpoint=endpoint_label,
                    status=f'error_{e.response.status_code}'
                ).inc()
                
                logger.error(
                    f"[Consul] ❌ {method} {path} → {e.response.status_code} "
                    f"({duration*1000:.0f}ms) - Erro cliente, sem retry"
                )
                raise
            
            # Erros 5xx: fazer retry
            retries += 1
            if retries > max_retries:
                consul_requests_total.labels(
                    method=method,
                    api_type=api_type,
                    endpoint=endpoint_label,
                    status='error_5xx'
                ).inc()
                
                logger.error(
                    f"[Consul] ❌ {method} {path} → {e.response.status_code} "
                    f"({duration*1000:.0f}ms, retries={max_retries}) - FALHOU"
                )
                raise
            
            await asyncio.sleep(min(retries * 0.5, 2))  # Backoff: 0.5s, 1s, 2s
            
        except (httpx.RequestError, asyncio.TimeoutError) as e:
            duration = time.time() - start_time
            last_error = e
            
            retries += 1
            if retries > max_retries:
                consul_requests_total.labels(
                    method=method,
                    api_type=api_type,
                    endpoint=endpoint_label,
                    status='error_timeout'
                ).inc()
                
                logger.error(
                    f"[Consul] ⏱️ {method} {path} → Timeout/Network "
                    f"({duration*1000:.0f}ms, retries={max_retries})"
                )
                raise
            
            logger.warning(
                f"[Consul] ⚠️ {method} {path} → {type(e).__name__} "
                f"(retry {retries}/{max_retries})"
            )
            await asyncio.sleep(min(retries * 0.5, 2))
    
    # Nunca deveria chegar aqui
    if last_error:
        raise last_error
```

**Critérios de aceitação:**
- [ ] Agent operations P50 < 20ms, P99 < 50ms
- [ ] Catalog operations P99 < 200ms
- [ ] KV operations P99 < 500ms
- [ ] Métricas `consul_request_duration_seconds` disponíveis em `/metrics`
- [ ] Métricas `consul_requests_total` disponíveis em `/metrics`
- [ ] Logs estruturados com levels corretos (debug/warning/error)

---

### 🔴 CRÍTICO #2: Otimizar `get_all_services_from_all_nodes()`
**Arquivo:** `backend/core/consul_manager.py` linha 691-820

**Problemas atuais:**
```python
# ❌ PROBLEMA 1: Loop SERIAL (não paralelo)
for site in sites:
    try:
        # Cada site demora 5s se offline
        # 3 sites offline = 15s total

# ❌ PROBLEMA 2: Usa Catalog API (lento)
response = await self._request("GET", "/catalog/services")
# 50ms vs 5ms do Agent

# ❌ PROBLEMA 3: Fallback usa Agent (deveria ser contrário!)
# Tenta Catalog primeiro, Agent como fallback
# Lógica invertida!
```

**Solução completa:**
```python
async def get_all_services_from_all_nodes(self) -> Dict[str, Dict]:
    """
    Busca serviços de TODOS os nodes do cluster Consul
    
    OTIMIZAÇÃO v3.0 (15/11/2025):
    ────────────────────────────────────────────────────────
    ESTRATÉGIA:
    1. Tentar /agent/services no MASTER (timeout 2s, retry 1x)
    2. Se falhar → tentar CLIENTS em PARALELO (não serial!)
    3. Retornar no PRIMEIRO sucesso
    4. GARANTIR formato compatível: {node: {id: service}}
    
    PERFORMANCE:
    - Antes: 150ms (3 online) | 44s (2 offline c/ retry 3x)
    - Depois: 10ms (3 online) | 4s (2 offline c/ retry 1x paralelo)
    - GANHO: 15x (online) | 11x (offline)
    
    COMPATIBILIDADE:
    - Retorno IDÊNTICO ao código original
    - Campos 'Node' e 'ID' adicionados em cada service
    - Estrutura {node_name: {service_id: service_data}}
    
    Returns:
        Dict[str, Dict]: Serviços agrupados por node
        {
            "Palmas": {
                "service-id-1": {
                    "ID": "service-id-1",
                    "Service": "blackbox_exporter",
                    "Node": "Palmas",  # ← CRÍTICO: 4 arquivos dependem
                    "Meta": {...},
                    "Tags": [...],
                    ...
                }
            },
            "Rio": {...}
        }
    """
    sites = await self._load_sites_config()
    
    # Ordenar: master primeiro (is_default: true)
    sites.sort(key=lambda s: (not s.get("is_default"), s.get("name")))
    
    errors = []
    
    # ═══════════════════════════════════════════════════════
    # PASSO 1: Tentar MASTER primeiro (mais provável de estar online)
    # ═══════════════════════════════════════════════════════
    master_site = sites[0]
    try:
        logger.info(f"[Consul] Tentando master {master_site['name']}...")
        result = await self._fetch_services_from_node(master_site, timeout=2)
        
        if result:
            logger.info(
                f"[Consul] ✅ Sucesso via master {master_site['name']} "
                f"({len(list(result.values())[0])} serviços)"
            )
            return result
            
    except Exception as e:
        error_msg = f"Master {master_site['name']}: {str(e)[:100]}"
        errors.append(error_msg)
        logger.warning(f"[Consul] ⚠️ {error_msg}")
        logger.info(f"[Consul] Tentando clients em paralelo...")
    
    # ═══════════════════════════════════════════════════════
    # PASSO 2: Master falhou → tentar CLIENTS em PARALELO
    # ═══════════════════════════════════════════════════════
    client_sites = sites[1:]
    
    if not client_sites:
        raise HTTPException(
            status_code=503,
            detail=f"Apenas 1 node configurado e está offline: {errors[0]}"
        )
    
    # ✅ OTIMIZAÇÃO: Paralelizar requisições (2-3x mais rápido)
    tasks = [
        self._fetch_services_from_node(site, timeout=2)
        for site in client_sites
    ]
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Processar resultados
    for site, result in zip(client_sites, results):
        if isinstance(result, Exception):
            error_msg = f"{site['name']}: {str(result)[:100]}"
            errors.append(error_msg)
            logger.warning(f"[Consul] ⚠️ {error_msg}")
            continue
        
        if result:
            logger.info(
                f"[Consul] ✅ Sucesso via client {site['name']} "
                f"({len(list(result.values())[0])} serviços)"
            )
            return result
    
    # ═══════════════════════════════════════════════════════
    # PASSO 3: Nenhum node respondeu
    # ═══════════════════════════════════════════════════════
    logger.error(
        f"[Consul] ❌ TODOS os nodes falharam ({len(sites)} nodes). "
        f"Erros: {'; '.join(errors)}"
    )
    
    raise HTTPException(
        status_code=503,
        detail=f"Nenhum node Consul acessível ({len(sites)} tentados). "
               f"Erros: {'; '.join(errors)}"
    )


async def _fetch_services_from_node(
    self,
    site: dict,
    timeout: int = 2
) -> Optional[Dict[str, Dict]]:
    """
    Helper: Busca serviços de um node específico via Agent API
    
    Args:
        site: Dict com name, prometheus_instance
        timeout: Timeout em segundos (default: 2s)
    
    Returns:
        Dict no formato compatível {node: {id: service}}
        ou None se falhar
    """
    node_name = site['name']
    node_addr = site['prometheus_instance']
    
    # Conectar ao node específico
    temp_consul = ConsulManager(host=node_addr, token=self.token)
    
    # ✅ USA AGENT API (5-10ms) ao invés de Catalog (50ms)
    # Agent mantém vista completa via Gossip Protocol
    response = await asyncio.wait_for(
        temp_consul._request("GET", "/agent/services"),
        timeout=timeout
    )
    
    services_flat = response.json()  # Dict[service_id, service_data]
    
    # ═══════════════════════════════════════════════════════
    # CONVERTER para formato legado {node: {id: service}}
    # ═══════════════════════════════════════════════════════
    result = {node_name: {}}
    
    for service_id, service_data in services_flat.items():
        # ✅ ADICIONAR campos obrigatórios (compatibilidade)
        service_data['Node'] = node_name  # Usado por monitoring_unified.py:217
        service_data['ID'] = service_id   # Usado por monitoring_unified.py:220
        
        result[node_name][service_id] = service_data
    
    logger.debug(
        f"[Consul] Fetched {len(services_flat)} services from {node_name} "
        f"(timeout={timeout}s)"
    )
    
    return result
```

**Critérios de aceitação:**
- [ ] Estrutura retorno: `Dict[str, Dict[str, Any]]` (INEGOCIÁVEL)
- [ ] Campo `'Node'` em cada service (OBRIGATÓRIO)
- [ ] Campo `'ID'` em cada service (OBRIGATÓRIO)
- [ ] Paralelização de clients implementada
- [ ] Timeout 2s por node (vs 5s antes)
- [ ] Performance: <100ms (todos online), <5s (2 offline)

---

### 🟡 ALTO #3: Frontend Race Condition (MANTIDO)
**Arquivos:**
- `frontend/src/pages/DynamicMonitoringPage.tsx` (linhas 183, 601, 1148)
- `frontend/src/components/MetadataFilterBar.tsx` (linha ~40)

**Implementar conforme prompt V2** (sem mudanças).

---

### 🟡 ALTO #4: source_label (MANTIDO)
**Arquivo:** `backend/core/multi_config_manager.py` (linha ~776)

**Implementar conforme prompt V2** (sem mudanças).

---

## 📋 TESTES OBRIGATÓRIOS (COMPLETOS)

### Testes Backend Unit
```bash
cd backend
python test_phase1.py
python test_phase2.py
python test_full_field_resilience.py
# ✅ Esperado: TODOS passando
```

### Testes Performance (NOVOS)
```bash
# Teste 1: Latência com todos nodes ONLINE
time curl -s "http://localhost:5000/api/v1/monitoring/data?category=network-probes" > /dev/null
# ✅ Esperado: <100ms (real time)

# Teste 2: Latência com master OFFLINE (simular)
# 1. Backup sites.json
cp backend/skills/eye/settings/sites.json /tmp/sites.json.bak

# 2. Editar sites.json - trocar IP master (is_default:true) para 192.0.2.1
# 3. Reiniciar backend
./restart-backend.sh

# 4. Medir latência
time curl -s "http://localhost:5000/api/v1/monitoring/data?category=network-probes" > /dev/null
# ✅ Esperado: <3s (timeout 2s + 1 sucesso)

# 5. Restaurar
cp /tmp/sites.json.bak backend/skills/eye/settings/sites.json
./restart-backend.sh

# Teste 3: Latência com 2 nodes OFFLINE
# Repetir acima mas deixar apenas 1 IP válido
# ✅ Esperado: <5s (2 timeouts em paralelo + 1 sucesso)
```

### Testes Métricas Prometheus (NOVOS)
```bash
# Verificar métricas disponíveis
curl -s http://localhost:5000/metrics | grep consul_request

# ✅ Esperado:
# consul_request_duration_seconds_bucket{api_type="agent",endpoint="/agent/services",method="GET",le="0.005"}
# consul_request_duration_seconds_count{api_type="agent",...}
# consul_requests_total{api_type="agent",endpoint="/agent/services",method="GET",status="success"}

# Fazer algumas requests e verificar métricas
curl -s "http://localhost:5000/api/v1/monitoring/data?category=network-probes" > /dev/null
curl -s http://localhost:5000/metrics | grep 'consul_request.*success'
# ✅ Esperado: Counters incrementados
```

### Testes Endpoints Críticos
```bash
# 4 arquivos que dependem de get_all_services_from_all_nodes()
curl -s "http://localhost:5000/api/v1/monitoring/data?category=network-probes" | jq '.success'
# ✅ Esperado: true

curl -s "http://localhost:5000/api/v1/services/?node_addr=ALL" | jq '.success'
# ✅ Esperado: true

curl -X POST "http://localhost:5000/api/v1/services/search" \
  -H "Content-Type: application/json" \
  -d '{"module": "icmp"}' | jq '.success'
# ✅ Esperado: true

curl -s "http://localhost:5000/api/v1/blackbox/targets" | jq '.success'
# ✅ Esperado: true
```

### Testes Frontend Smoke
```bash
# Abrir cada página e verificar console
# 1. http://localhost:8081/monitoring/network-probes
# 2. http://localhost:8081/monitoring/web-probes
# 3. http://localhost:8081/monitoring/system-exporters

# ✅ Esperado:
# - Tabelas carregam com dados
# - Filtros funcionam
# - Console: 0 erros TypeError
# - Performance: Carregamento <2s
```

---

## 📋 CHECKLIST FINAL PRÉ-PR

### Código
- [ ] `_request()` com timeout variável (2s Agent, 5s outros)
- [ ] `_request()` com retry condicional (1x Agent, 2x outros)
- [ ] `_request()` com métricas Prometheus completas
- [ ] `_request()` com logs estruturados (debug/warning/error)
- [ ] `get_all_services_from_all_nodes()` com paralelização
- [ ] `_fetch_services_from_node()` helper implementado
- [ ] Frontend: `optionsLoaded` state adicionado
- [ ] Frontend: renderização condicional MetadataFilterBar
- [ ] Backend: source_label populado corretamente

### Compatibilidade (INEGOCIÁVEL)
- [ ] Estrutura retorno: `Dict[str, Dict]` preservada
- [ ] Campos `'Node'` e `'ID'` presentes
- [ ] 4 endpoints críticos funcionando (200 OK)

### Performance
- [ ] Agent API P50 < 20ms, P99 < 50ms
- [ ] `/monitoring/data` todos online < 100ms
- [ ] `/monitoring/data` 1 offline < 3s
- [ ] `/monitoring/data` 2 offline < 5s

### Observabilidade
- [ ] Métricas `consul_request_duration_seconds` OK
- [ ] Métricas `consul_requests_total` OK
- [ ] Logs estruturados implementados
- [ ] Dashboard Grafana criado (opcional)

### Testes
- [ ] `test_phase1.py` → PASS
- [ ] `test_phase2.py` → PASS
- [ ] `test_full_field_resilience.py` → 8/8 PASS
- [ ] Frontend: 0 erros console

---

## 🚨 SINAIS DE ALERTA

### Backend Quebrou
```bash
# ❌ HTTP 500 em endpoints críticos
# ❌ TypeError: 'list' object is not subscriptable
# ❌ AttributeError: 'NoneType' object has no attribute 'items'

# AÇÃO: Reverter imediatamente
git checkout HEAD~1 -- backend/core/consul_manager.py
```

### Performance Piorou
```bash
# ❌ Agent API > 100ms consistentemente
# ❌ Timeout em nodes online

# AÇÃO: Revisar timeout/retry
# Possível causa: Timeout muito agressivo
```

### Frontend Quebrou
```bash
# ❌ TypeError: Cannot read property 'length' of undefined
# ❌ Tabela vazia (dados carregam mas não renderizam)

# AÇÃO: Verificar estrutura de retorno da API
# Possível causa: Formato incompatível
```

---

## 🎯 ENTREGÁVEIS NA PR

1. **Código otimizado:**
   - `backend/core/consul_manager.py` (métodos `_request()` e `get_all_services_from_all_nodes()`)
   - `frontend/src/pages/DynamicMonitoringPage.tsx` (race condition fix)
   - `frontend/src/components/MetadataFilterBar.tsx` (validação)
   - `backend/core/multi_config_manager.py` (source_label)

2. **Logs de testes:**
   - `test_phase1.log`
   - `test_phase2.log`
   - `test_resilience.log`
   - `performance_before_after.txt`

3. **Screenshots:**
   - Console limpo (0 errors)
   - Métricas Prometheus

4. **Checklist preenchido** (cópia deste documento com ✅)

---

**IMPLEMENTAR COM CAUTELA - TESTES COMPLETOS OBRIGATÓRIOS! 🚀**

**Em caso de dúvida:** PARAR e pedir clarificação. Não improvisar em código crítico.

**BOA SORTE! 🎯**
