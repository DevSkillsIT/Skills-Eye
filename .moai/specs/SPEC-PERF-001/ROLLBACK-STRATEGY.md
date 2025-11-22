# Estrategia de Rollback - SPEC-PERF-001

## Data de Criacao
21/11/2025

## Objetivo
Documentar procedimentos executaveis para reverter as otimizacoes do SPEC-PERF-001 caso ocorram problemas em producao. Define gatilhos claros, ordem de reversao e passos detalhados.

---

## Gatilhos de Rollback

### Metricas de Alerta (disparam rollback automatico ou manual)

| Metrica | Threshold | Janela | Severidade | Acao |
|---------|-----------|--------|------------|------|
| Taxa de timeout | > 5% | 10 min | CRITICAL | Rollback Fase 1 |
| P99 de latencia `/api/v1/nodes` | > 5000ms | 5 min | HIGH | Rollback Fase 2 |
| `consul_node_enrich_failures_total` | > 10/min | 5 min | HIGH | Rollback Fase 2 |
| Erro 5xx em `/api/v1/nodes` | > 1% | 5 min | CRITICAL | Rollback completo |
| `services_status="error"` em todos nos | 100% | 1 min | CRITICAL | Rollback completo |
| Re-renders excessivos frontend | > 20 por mudanca | - | MEDIUM | Rollback Fase 3 |

### Sinais Qualitativos (observacao manual)

- NodeSelector nao carrega ou demora > 10s
- services_count retorna 0 para todos os nos por tempo prolongado
- Logs com mensagens consecutivas de "Timeout ao enriquecer no"
- Usuarios reportando lentidao nas 8 paginas de monitoramento
- Console do browser com erros JavaScript relacionados a NodesContext

---

## Monitoramento Pre-Rollback

### Comandos para Verificar Estado Atual

```bash
# 1. Verificar metricas Prometheus (executar no servidor backend)
curl -s http://localhost:5000/api/prometheus-metrics/parsed | jq '.metrics | keys'

# 2. Verificar taxa de falhas de enriquecimento
curl -s http://localhost:5000/api/prometheus-metrics/parsed | \
  jq '.metrics.consul_node_enrich_failures_total'

# 3. Verificar latencia do endpoint
for i in {1..5}; do
  time curl -s http://localhost:5000/api/v1/nodes > /dev/null
  sleep 1
done

# 4. Verificar logs de timeout
tail -100 /var/log/skills-eye/backend.log | grep -E "Timeout|error|WARN"

# 5. Verificar variaveis de ambiente atuais
grep -E "CONSUL_CATALOG_TIMEOUT|CONSUL_SEMAPHORE_LIMIT|SITES_CACHE_TTL" backend/.env
```

### Dashboard Grafana (se disponivel)

Verificar painel de metricas:
- consul_node_enrich_duration (P50, P95, P99)
- consul_node_enrich_failures_total (rate 5m)
- consul_sites_cache_status (hit/miss ratio)

---

## Ordem de Rollback

**IMPORTANTE**: A ordem de rollback eh INVERSA a ordem de implementacao.
Reverter primeiro as mudancas mais recentes (menor impacto) para mais antigas (maior impacto).

| Ordem | Fase | Descricao | Tempo Est. | Risco |
|-------|------|-----------|------------|-------|
| 1 | Fase 3 | Frontend (NodeSelector onChange, CSS) | 5 min | Baixo |
| 2 | Fase 2 | Catalog API, Semaphore, Retry | 10 min | Medio |
| 3 | Fase 1 | TTL (60s -> 30s), Timeout (2s -> 5s) | 5 min | Baixo |
| 4 | Completo | Todas as fases + restart | 20 min | Medio |

---

## Procedimentos por Fase

### Reverter Fase 3 (Frontend - NodeSelector)

**Quando reverter**: Re-renders excessivos, erros JavaScript, bugs visuais

**Arquivos afetados**:
- `frontend/src/components/NodeSelector.tsx`
- `frontend/src/components/NodeSelector.css` (se criado)
- `frontend/src/contexts/NodesContext.tsx`

**Procedimento**:

```bash
# 1. Navegar para diretorio do projeto
cd /home/adrianofante/projetos/Skills-Eye

# 2. Verificar estado atual dos arquivos frontend
git diff frontend/src/components/NodeSelector.tsx
git diff frontend/src/contexts/NodesContext.tsx

# 3. Reverter NodeSelector para versao anterior
# Identificar commit antes do SPEC-PERF-001
git log --oneline --all -- frontend/src/components/NodeSelector.tsx | head -5

# 4. Fazer checkout do arquivo (substitua COMMIT_HASH pelo hash correto)
git checkout COMMIT_HASH -- frontend/src/components/NodeSelector.tsx

# 5. Reverter NodesContext (se necessario)
git checkout COMMIT_HASH -- frontend/src/contexts/NodesContext.tsx

# 6. Remover CSS criado (se existir)
rm -f frontend/src/components/NodeSelector.css

# 7. Rebuild do frontend
cd frontend
npm run build

# 8. Verificar build sem erros
echo "Build concluido com sucesso? Verificar erros acima."
```

**Alternativa - Reverter apenas onChange deps**:

```typescript
// Em frontend/src/components/NodeSelector.tsx
// ANTES (otimizado - pode causar bugs)
useEffect(() => {
  // ...
}, [loading, nodes, mainServer, selectedNode, showAllNodesOption]);

// DEPOIS (rollback - reintroduzir onChange)
useEffect(() => {
  // ...
}, [loading, nodes, mainServer, selectedNode, showAllNodesOption, onChange]);
```

**Validacao**:
- Abrir React DevTools Profiler
- Navegar entre paginas de monitoramento
- Verificar que nao ha erros JavaScript no console
- Testar mudanca de no selecionado

---

### Reverter Fase 2 (Catalog API, Semaphore, Retry)

**Quando reverter**: Alta taxa de timeout, services_count=0 em massa, P99 > 5000ms

**Arquivos afetados**:
- `backend/api/nodes.py`
- `backend/core/consul_manager.py`
- `backend/core/config.py`

**Procedimento**:

```bash
# 1. Navegar para diretorio do projeto
cd /home/adrianofante/projetos/Skills-Eye

# 2. Verificar estado atual
git diff backend/api/nodes.py

# 3. Identificar commit antes do SPEC-PERF-001
git log --oneline --all -- backend/api/nodes.py | head -10

# 4. Reverter para versao com Agent API
# Opcao A: Checkout completo
git checkout COMMIT_HASH -- backend/api/nodes.py

# Opcao B: Editar manualmente a funcao get_service_count
# Ver codigo abaixo
```

**Codigo para reverter get_service_count (Opcao B)**:

```python
# Em backend/api/nodes.py
# Substituir a funcao get_service_count atual por esta versao anterior:

async def get_service_count(member: dict) -> dict:
    """Conta servicos de um no especifico com timeout de 5s (versao original)"""
    member["services_count"] = 0
    member["site_name"] = sites_map.get(member["addr"], "Nao mapeado")
    try:
        # VERSAO ORIGINAL: Usar Agent API (conexao direta ao no)
        temp_consul = ConsulManager(host=member["addr"])
        services = await asyncio.wait_for(
            temp_consul.get_services(),
            timeout=5.0  # Timeout original de 5s
        )
        member["services_count"] = len(services)
    except Exception as e:
        # Silencioso - se falhar, deixa services_count = 0
        pass
    return member
```

**Remover configuracoes do config.py** (se necessario):

```bash
# As variaveis de ambiente continuam existindo mas nao serao usadas
# Nao eh necessario remover do config.py, apenas nao serao utilizadas
```

**Reiniciar backend**:

```bash
# Parar backend atual
pkill -f "uvicorn app:app"

# Iniciar novamente
cd /home/adrianofante/projetos/Skills-Eye/backend
uvicorn app:app --host 0.0.0.0 --port 5000 --reload

# OU usar script de restart se existir
./restart.sh
```

**Validacao**:
- Executar: `curl http://localhost:5000/api/v1/nodes | jq '.data[].services_count'`
- Verificar que services_count > 0 para nos ativos
- Verificar logs: `tail -f /var/log/skills-eye/backend.log`

---

### Reverter Fase 1 (TTL e Timeout)

**Quando reverter**: Cache muito stale, timeouts excessivos com 2s

**Arquivos afetados**:
- `backend/api/nodes.py` (linhas de cache e timeout)
- `backend/.env` (variaveis de ambiente)

**Procedimento via variaveis de ambiente (recomendado)**:

```bash
# 1. Editar .env do backend
cd /home/adrianofante/projetos/Skills-Eye/backend

# 2. Alterar variaveis para valores originais
cat >> .env << 'EOF'
# ROLLBACK SPEC-PERF-001 - Fase 1
CONSUL_CATALOG_TIMEOUT=5.0
CONSUL_SEMAPHORE_LIMIT=10
SITES_CACHE_TTL=60
CONSUL_MAX_RETRIES=0
CONSUL_RETRY_DELAY=0.5
EOF

# 3. Reiniciar backend para aplicar
pkill -f "uvicorn app:app"
cd /home/adrianofante/projetos/Skills-Eye/backend
uvicorn app:app --host 0.0.0.0 --port 5000 --reload
```

**Procedimento via codigo (alternativo)**:

```python
# Em backend/api/nodes.py, linha do cache.set()
# ANTES (otimizado)
await cache.set(cache_key, result, ttl=60)

# DEPOIS (rollback)
await cache.set(cache_key, result, ttl=30)  # TTL original de 30s
```

**Validacao**:
- Executar 2 requests com 45s de intervalo
- Segundo request deve ser cache miss (> 30s TTL)
- `curl http://localhost:5000/api/v1/nodes && sleep 45 && curl http://localhost:5000/api/v1/nodes`

---

### Rollback Completo (Todas as Fases)

**Quando executar**: Erro 5xx generalizado, sistema inutilizavel

**Procedimento automatizado**:

```bash
#!/bin/bash
# Script: rollback_spec_perf_001.sh
# Uso: ./rollback_spec_perf_001.sh

set -e
echo "=== ROLLBACK SPEC-PERF-001 ==="
echo "Data: $(date)"

PROJECT_DIR="/home/adrianofante/projetos/Skills-Eye"
cd "$PROJECT_DIR"

# Identificar commit anterior ao SPEC-PERF-001
# Usar o commit do revert ja existente ou buscar anterior
REVERT_COMMIT="410a5ad"  # Commit: "revert: reverter mudancas SPEC-PERF-001 para analise"

echo "[1/5] Parando backend..."
pkill -f "uvicorn app:app" || true
sleep 2

echo "[2/5] Revertendo backend/api/nodes.py..."
git checkout "$REVERT_COMMIT" -- backend/api/nodes.py

echo "[3/5] Revertendo frontend/src/components/NodeSelector.tsx..."
git checkout "$REVERT_COMMIT" -- frontend/src/components/NodeSelector.tsx

echo "[4/5] Revertendo frontend/src/contexts/NodesContext.tsx..."
git checkout "$REVERT_COMMIT" -- frontend/src/contexts/NodesContext.tsx

echo "[5/5] Restaurando .env original..."
cat > backend/.env.rollback << 'EOF'
# ROLLBACK - Valores originais
CONSUL_CATALOG_TIMEOUT=5.0
CONSUL_SEMAPHORE_LIMIT=10
SITES_CACHE_TTL=60
CONSUL_MAX_RETRIES=0
EOF

echo ""
echo "=== ROLLBACK CONCLUIDO ==="
echo ""
echo "Proximos passos:"
echo "1. Rebuild frontend: cd frontend && npm run build"
echo "2. Reiniciar backend: cd backend && uvicorn app:app --host 0.0.0.0 --port 5000"
echo "3. Testar endpoint: curl http://localhost:5000/api/v1/nodes"
echo "4. Verificar logs: tail -f backend/logs/app.log"
```

**Para executar**:

```bash
# Salvar script
cat > /home/adrianofante/projetos/Skills-Eye/scripts/rollback_spec_perf_001.sh << 'SCRIPT'
# Conteudo do script acima
SCRIPT

chmod +x /home/adrianofante/projetos/Skills-Eye/scripts/rollback_spec_perf_001.sh

# Executar
./scripts/rollback_spec_perf_001.sh
```

---

## Monitoramento Durante Rollback

### Checklist de Validacao

```markdown
## Checklist Pos-Rollback

### Imediato (0-5 minutos)
- [ ] Backend reiniciado sem erros
- [ ] Endpoint `/api/v1/nodes` responde com status 200
- [ ] services_count > 0 para nos ativos
- [ ] Logs sem erros CRITICAL

### Curto prazo (5-15 minutos)
- [ ] Cache hits funcionando (2a requisicao < 50ms)
- [ ] Todas 8 paginas de monitoramento carregam
- [ ] NodeSelector seleciona no corretamente
- [ ] Metricas Prometheus atualizando

### Medio prazo (15-60 minutos)
- [ ] Nenhum timeout em massa
- [ ] P99 latencia estavel
- [ ] Usuarios nao reportam problemas
- [ ] consul_node_enrich_failures_total estavel
```

### Queries Prometheus para Monitorar

```promql
# Taxa de falhas de enriquecimento (deve diminuir apos rollback)
rate(consul_node_enrich_failures_total[5m])

# Latencia P99 do endpoint
histogram_quantile(0.99, rate(http_request_duration_seconds_bucket{handler="/api/v1/nodes"}[5m]))

# Cache hit rate
sum(rate(consul_sites_cache_status{status="hit"}[5m])) /
sum(rate(consul_sites_cache_status[5m])) * 100

# Timeouts por minuto
rate(consul_node_enrich_failures_total{error_type="timeout"}[1m]) * 60
```

### Comandos de Verificacao Rapida

```bash
# Teste rapido de saude
curl -s http://localhost:5000/api/v1/nodes | jq '{
  success: .success,
  total: .total,
  main_server: .main_server,
  services_counts: [.data[].services_count]
}'

# Verificar erros nos logs (ultimos 5 minutos)
journalctl -u skills-eye-backend --since "5 minutes ago" | grep -E "ERROR|CRITICAL"

# Teste de performance (5 requisicoes)
for i in {1..5}; do
  START=$(date +%s%N)
  curl -s http://localhost:5000/api/v1/nodes > /dev/null
  END=$(date +%s%N)
  echo "Request $i: $(( (END - START) / 1000000 ))ms"
done
```

---

## Comunicacao Durante Incidente

### Template de Notificacao

```markdown
## [INCIDENTE] Rollback SPEC-PERF-001 em Andamento

**Status**: EM ANDAMENTO / CONCLUIDO
**Inicio**: YYYY-MM-DD HH:MM
**Fim**: YYYY-MM-DD HH:MM (estimado/real)

### Impacto
- Paginas de monitoramento podem apresentar lentidao temporaria
- Contagem de servicos pode mostrar 0 temporariamente

### Causa
[Descrever o gatilho do rollback]
- Ex: Taxa de timeout > 5% por 10 minutos
- Ex: P99 latencia > 5000ms

### Acoes Tomadas
1. [X] Identificado problema em metricas
2. [X] Iniciado procedimento de rollback Fase X
3. [ ] Validacao pos-rollback
4. [ ] Monitoramento por 60 minutos

### Proxima Atualizacao
[Horario da proxima atualizacao]

### Contato
[Nome do responsavel pelo incidente]
```

---

## Pos-Mortem

Apos qualquer rollback, criar documento de pos-mortem:

```markdown
# Pos-Mortem: Rollback SPEC-PERF-001

## Data do Incidente
YYYY-MM-DD

## Timeline
- HH:MM - Detectado problema [metrica]
- HH:MM - Iniciado rollback
- HH:MM - Rollback concluido
- HH:MM - Sistema estabilizado

## Causa Raiz
[Analise tecnica detalhada]

## Impacto
- Duracao: X minutos
- Usuarios afetados: X
- Funcionalidades degradadas: [lista]

## Licoes Aprendidas
1. [Licao 1]
2. [Licao 2]

## Acoes de Follow-up
- [ ] [Acao 1 - responsavel - prazo]
- [ ] [Acao 2 - responsavel - prazo]
```

---

## Resumo dos Valores de Configuracao

### Valores Originais (Pre-SPEC-PERF-001)

| Configuracao | Valor Original | Arquivo |
|--------------|----------------|---------|
| Timeout | 5.0s | backend/api/nodes.py |
| TTL Cache Nodes | 30s | backend/api/nodes.py |
| API | Agent API | backend/api/nodes.py |
| Semaphore | N/A | N/A |
| Retry | N/A | N/A |
| Sites Cache TTL | N/A | N/A |

### Valores Otimizados (SPEC-PERF-001)

| Configuracao | Valor | Variavel Env |
|--------------|-------|--------------|
| CONSUL_CATALOG_TIMEOUT | 2.0s | CONSUL_CATALOG_TIMEOUT |
| TTL Cache Nodes | 60s | (hardcoded) |
| API | Catalog API | (hardcoded) |
| CONSUL_SEMAPHORE_LIMIT | 5 | CONSUL_SEMAPHORE_LIMIT |
| CONSUL_MAX_RETRIES | 1 | CONSUL_MAX_RETRIES |
| CONSUL_RETRY_DELAY | 0.5s | CONSUL_RETRY_DELAY |
| SITES_CACHE_TTL | 300s | SITES_CACHE_TTL |

---

## Anexos

### A. Commits Relevantes

```bash
# Commit do revert existente
410a5ad - revert: reverter mudancas SPEC-PERF-001 para analise

# Commit da implementacao
266c17c - feat(perf): implementar otimizacoes SPEC-PERF-001 para NodeSelector

# Para ver todas as mudancas
git log --oneline | grep -i "SPEC-PERF"
```

### B. Arquivos Modificados pelo SPEC-PERF-001

- `backend/api/nodes.py`
- `backend/core/config.py`
- `backend/core/metrics.py` (novas metricas)
- `backend/.env`
- `frontend/src/components/NodeSelector.tsx`
- `frontend/src/contexts/NodesContext.tsx`
- `frontend/src/services/prometheus.ts` (se criado)

### C. Metricas Prometheus Relacionadas

- `consul_node_enrich_failures_total{node_name, error_type}`
- `consul_node_enrich_duration{node_name, status}`
- `consul_sites_cache_status{status}`

---

**Documento criado em**: 21/11/2025
**Ultima atualizacao**: 21/11/2025
**Responsavel**: Claude Code (SPEC-PERF-001)
