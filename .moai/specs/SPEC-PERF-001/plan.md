# Plano de Implementacao - SPEC-PERF-001

## Visao Geral

Este documento detalha o plano de implementacao passo a passo para otimizacao de performance do NodeSelector e endpoint `/api/v1/nodes`.

**Estrategia**: Implementacao em 4 fases:
- **Fase 0**: Baseline e testes de performance (ANTES)
- **Fase 1**: Quick Wins (baixo risco)
- **Fase 2**: Otimizacoes medias
- **Fase 3**: Melhorias de UX

**Validacao**: Testes de baseline antes e depois para gerar relatorio comparativo.

---

## Fase 0: Baseline e Testes de Performance

### Objetivo
Coletar metricas de performance ANTES das otimizacoes para gerar relatorio comparativo ao final.

### Tarefa 0.1: Criar Arquivo de Teste de Baseline

**Arquivo**: `backend/test_performance_nodes.py`

**Codigo Completo**:
```python
"""
Teste de Performance - Endpoint /api/v1/nodes
SPEC-PERF-001: Baseline e Comparacao

Executar ANTES e DEPOIS das otimizacoes para gerar relatorio comparativo.

Uso:
    # Antes das otimizacoes (salvar baseline)
    python test_performance_nodes.py --mode baseline

    # Depois das otimizacoes (comparar)
    python test_performance_nodes.py --mode compare

    # Apenas testar (sem salvar)
    python test_performance_nodes.py --mode test
"""
import asyncio
import time
import json
import argparse
import statistics
from datetime import datetime
from pathlib import Path
import httpx

# Configuracoes
API_URL = "http://localhost:5000/api/v1"
ITERATIONS = 10
BASELINE_FILE = Path("test_results/nodes_baseline.json")


async def test_nodes_endpoint():
    """Testa endpoint /api/v1/nodes multiplas vezes"""
    results = {
        "timestamp": datetime.now().isoformat(),
        "endpoint": f"{API_URL}/nodes",
        "iterations": ITERATIONS,
        "measurements": [],
        "cache_hits": 0,
        "cache_misses": 0,
        "errors": 0
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        # Limpar cache primeiro (se possivel)
        try:
            await client.post(f"{API_URL}/cache/clear/nodes:list:all")
            print("[INFO] Cache limpo antes dos testes")
        except:
            print("[WARN] Nao foi possivel limpar cache")

        for i in range(ITERATIONS):
            start_time = time.time()
            try:
                response = await client.get(f"{API_URL}/nodes")
                elapsed_ms = (time.time() - start_time) * 1000

                if response.status_code == 200:
                    data = response.json()
                    results["measurements"].append({
                        "iteration": i + 1,
                        "time_ms": round(elapsed_ms, 2),
                        "nodes_count": data.get("total", 0),
                        "success": True
                    })

                    # Primeira iteracao eh cache miss, demais sao hits
                    if i == 0:
                        results["cache_misses"] += 1
                    else:
                        results["cache_hits"] += 1

                    print(f"[{i+1}/{ITERATIONS}] {elapsed_ms:.0f}ms - {data.get('total', 0)} nos")
                else:
                    results["errors"] += 1
                    print(f"[{i+1}/{ITERATIONS}] ERRO: Status {response.status_code}")

            except Exception as e:
                results["errors"] += 1
                print(f"[{i+1}/{ITERATIONS}] ERRO: {e}")

        # Esperar 1s entre iteracoes para nao estressar
        await asyncio.sleep(0.1)

    # Calcular estatisticas
    times = [m["time_ms"] for m in results["measurements"] if m.get("success")]
    if times:
        results["statistics"] = {
            "min_ms": round(min(times), 2),
            "max_ms": round(max(times), 2),
            "avg_ms": round(statistics.mean(times), 2),
            "median_ms": round(statistics.median(times), 2),
            "p50_ms": round(statistics.median(times), 2),
            "p95_ms": round(sorted(times)[int(len(times) * 0.95)], 2) if len(times) >= 10 else None,
            "p99_ms": round(sorted(times)[int(len(times) * 0.99)], 2) if len(times) >= 100 else None,
            "first_ms": times[0] if times else None,  # Cache miss
            "rest_avg_ms": round(statistics.mean(times[1:]), 2) if len(times) > 1 else None  # Cache hits
        }

    return results


def save_baseline(results: dict):
    """Salva resultados como baseline"""
    BASELINE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(BASELINE_FILE, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"\n[BASELINE] Salvo em: {BASELINE_FILE}")


def load_baseline() -> dict:
    """Carrega baseline anterior"""
    if not BASELINE_FILE.exists():
        return None
    with open(BASELINE_FILE, 'r') as f:
        return json.load(f)


def generate_comparison_report(baseline: dict, current: dict):
    """Gera relatorio comparativo"""
    print("\n" + "="*80)
    print("RELATORIO DE PERFORMANCE - SPEC-PERF-001")
    print("="*80)

    print(f"\nBaseline: {baseline['timestamp']}")
    print(f"Current:  {current['timestamp']}")

    print("\n" + "-"*80)
    print("METRICAS DE TEMPO")
    print("-"*80)

    b_stats = baseline.get("statistics", {})
    c_stats = current.get("statistics", {})

    metrics = [
        ("Media", "avg_ms"),
        ("Mediana", "median_ms"),
        ("Minimo", "min_ms"),
        ("Maximo", "max_ms"),
        ("P50", "p50_ms"),
        ("P95", "p95_ms"),
        ("1a Req (cache miss)", "first_ms"),
        ("Resto (cache hits)", "rest_avg_ms"),
    ]

    for label, key in metrics:
        b_val = b_stats.get(key)
        c_val = c_stats.get(key)

        if b_val and c_val:
            diff = c_val - b_val
            pct = ((c_val - b_val) / b_val) * 100
            status = "↓" if diff < 0 else "↑" if diff > 0 else "="

            print(f"{label:25} {b_val:>8.0f}ms → {c_val:>8.0f}ms  {status} {abs(pct):>5.1f}%")

    print("\n" + "-"*80)
    print("RESUMO")
    print("-"*80)

    # Calcular ganho total
    b_avg = b_stats.get("avg_ms", 0)
    c_avg = c_stats.get("avg_ms", 0)

    if b_avg > 0:
        improvement = ((b_avg - c_avg) / b_avg) * 100
        if improvement > 0:
            print(f"✅ MELHORIA: {improvement:.1f}% mais rapido")
            print(f"   Tempo medio: {b_avg:.0f}ms → {c_avg:.0f}ms")
        else:
            print(f"❌ REGRESSAO: {abs(improvement):.1f}% mais lento")
            print(f"   Tempo medio: {b_avg:.0f}ms → {c_avg:.0f}ms")

    # Verificar criterios de aceitacao
    print("\n" + "-"*80)
    print("CRITERIOS DE ACEITACAO")
    print("-"*80)

    checks = [
        ("Tempo cache miss < 600ms", c_stats.get("first_ms", 999) < 600),
        ("Tempo cache hit < 50ms", c_stats.get("rest_avg_ms", 999) < 50),
        ("Melhoria > 50%", improvement > 50 if b_avg > 0 else False),
        ("Zero erros", current.get("errors", 0) == 0),
    ]

    for label, passed in checks:
        status = "✅" if passed else "❌"
        print(f"  {status} {label}")

    print("\n" + "="*80)

    # Salvar relatorio
    report_file = Path("test_results/nodes_performance_report.md")
    report_file.parent.mkdir(parents=True, exist_ok=True)

    with open(report_file, 'w') as f:
        f.write(f"# Relatorio de Performance - SPEC-PERF-001\n\n")
        f.write(f"**Baseline**: {baseline['timestamp']}\n")
        f.write(f"**Current**: {current['timestamp']}\n\n")
        f.write(f"## Resultados\n\n")
        f.write(f"| Metrica | Antes | Depois | Variacao |\n")
        f.write(f"|---------|-------|--------|----------|\n")

        for label, key in metrics:
            b_val = b_stats.get(key)
            c_val = c_stats.get(key)
            if b_val and c_val:
                pct = ((c_val - b_val) / b_val) * 100
                f.write(f"| {label} | {b_val:.0f}ms | {c_val:.0f}ms | {pct:+.1f}% |\n")

        if b_avg > 0:
            f.write(f"\n## Conclusao\n\n")
            f.write(f"**Melhoria Total**: {improvement:.1f}%\n")

    print(f"\n[REPORT] Salvo em: {report_file}")


async def main():
    parser = argparse.ArgumentParser(description='Teste de performance do endpoint /nodes')
    parser.add_argument('--mode', choices=['baseline', 'compare', 'test'], default='test',
                        help='Modo: baseline (salvar), compare (comparar), test (apenas testar)')
    args = parser.parse_args()

    print("\n" + "="*80)
    print("TESTE DE PERFORMANCE - /api/v1/nodes")
    print(f"Modo: {args.mode.upper()}")
    print("="*80)

    results = await test_nodes_endpoint()

    if args.mode == 'baseline':
        save_baseline(results)
        print("\nEstatisticas do Baseline:")
        for key, value in results.get("statistics", {}).items():
            print(f"  {key}: {value}")

    elif args.mode == 'compare':
        baseline = load_baseline()
        if baseline:
            generate_comparison_report(baseline, results)
        else:
            print("\n❌ ERRO: Baseline nao encontrado!")
            print(f"   Execute primeiro: python {__file__} --mode baseline")

    else:  # test
        print("\nEstatisticas:")
        for key, value in results.get("statistics", {}).items():
            print(f"  {key}: {value}")


if __name__ == "__main__":
    asyncio.run(main())
```

### Tarefa 0.2: Executar Baseline

**Comandos**:
```bash
# Criar diretorio de resultados
mkdir -p backend/test_results

# Executar teste de baseline ANTES das otimizacoes
cd backend
python test_performance_nodes.py --mode baseline
```

**Saida Esperada**:
```
TESTE DE PERFORMANCE - /api/v1/nodes
Modo: BASELINE
================================================================================
[1/10] 1234ms - 3 nos
[2/10] 45ms - 3 nos
...
[BASELINE] Salvo em: test_results/nodes_baseline.json
```

### Tarefa 0.3: Adicionar Logs de Debug no Backend

**Arquivo**: `backend/api/nodes.py`

**Adicionar logs no inicio do endpoint**:
```python
import logging

logger = logging.getLogger(__name__)

@router.get("/")
async def get_nodes():
    """Retorna todos os nos do cluster com cache de 30s"""

    # ✅ DEBUG: Log inicio da requisicao
    start_time = time.time()
    logger.info("[PERF] /api/v1/nodes - INICIO")

    cache_key = "nodes:list:all"

    # Verificar cache
    cached = await cache.get(cache_key)
    if cached is not None:
        elapsed_ms = (time.time() - start_time) * 1000
        logger.info(f"[PERF] /api/v1/nodes - CACHE HIT em {elapsed_ms:.0f}ms")
        return cached

    logger.info("[PERF] /api/v1/nodes - CACHE MISS - buscando do Consul")

    # ... resto do codigo ...

    # ✅ DEBUG: Log antes de enriquecer
    logger.info(f"[PERF] /api/v1/nodes - {len(members)} membros obtidos, iniciando enriquecimento")

    # ... enriquecimento ...

    # ✅ DEBUG: Log final
    elapsed_ms = (time.time() - start_time) * 1000
    logger.info(f"[PERF] /api/v1/nodes - COMPLETO em {elapsed_ms:.0f}ms - {len(enriched_members)} nos")

    return result
```

---

## Fase 1: Quick Wins (Baixo Risco)

### Objetivo
Ganhos imediatos com mudancas minimas e risco baixissimo.

### Tarefa 1.1: Reduzir Timeout de 5s para 2s

**Arquivo**: `backend/api/nodes.py`

**Localizacao**: Linha 67 (dentro da funcao `get_service_count`)

**Modificacao**:
```python
# ANTES
services = await asyncio.wait_for(
    temp_consul.get_services(),
    timeout=5.0  # <- ALTERAR AQUI
)

# DEPOIS
services = await asyncio.wait_for(
    temp_consul.get_services(),
    timeout=2.0  # Reduzido de 5s para 2s
)
```

**Justificativa**:
- 2s eh suficiente para conexao em datacenter local
- Se nao responder em 2s, provavelmente o no esta offline
- Pior caso cai de 15s (3 nos x 5s) para 6s (3 nos x 2s)

**Teste de validacao**:
```bash
# Medir tempo de resposta
time curl http://localhost:5000/api/v1/nodes

# Verificar que services_count eh populado
curl http://localhost:5000/api/v1/nodes | jq '.data[].services_count'
```

---

### Tarefa 1.2: Aumentar TTL do Cache de 30s para 60s

**Arquivo**: `backend/api/nodes.py`

**Localizacao**: Linha 86

**Modificacao**:
```python
# ANTES
await cache.set(cache_key, result, ttl=30)

# DEPOIS
await cache.set(cache_key, result, ttl=60)  # Aumentado de 30s para 60s
```

**Justificativa**:
- Nos raramente mudam em menos de 60s
- Reduz cache misses de 2/min para 1/min
- Impacto visual minimo (dados stale por ate 60s eh aceitavel)

**Teste de validacao**:
```bash
# Primeira requisicao (cache miss)
curl http://localhost:5000/api/v1/nodes

# Aguardar 45s e fazer segunda requisicao
# Deve retornar do cache (resposta rapida)
sleep 45 && time curl http://localhost:5000/api/v1/nodes

# Verificar logs do backend para "cache hit"
```

---

### Tarefa 1.3: Memoizar Context Value do NodesContext

**Arquivo**: `frontend/src/contexts/NodesContext.tsx`

**Localizacao**: Linhas 77-88 (dentro do Provider)

**Modificacao**:
```typescript
// ANTES
return (
  <NodesContext.Provider
    value={{
      nodes,
      mainServer,
      loading,
      error,
      reload: loadNodes,
    }}
  >
    {children}
  </NodesContext.Provider>
);

// DEPOIS
import { createContext, useContext, useState, useEffect, useMemo, useCallback } from 'react';

// Dentro do NodesProvider:
const reload = useCallback(async () => {
  await loadNodes();
}, []);

const contextValue = useMemo(() => ({
  nodes,
  mainServer,
  loading,
  error,
  reload,
}), [nodes, mainServer, loading, error, reload]);

return (
  <NodesContext.Provider value={contextValue}>
    {children}
  </NodesContext.Provider>
);
```

**Justificativa**:
- Sem memoizacao, o context value eh recriado a cada render
- Todos os consumers re-renderizam desnecessariamente
- Com useMemo, so re-renderiza quando dados realmente mudam

**Teste de validacao**:
- Usar React DevTools Profiler
- Verificar que NodeSelector nao re-renderiza ao navegar entre paginas
- Contar renders ao mudar no selecionado (deve ser 1-2, nao 10+)

---

## Fase 2: Otimizacoes Medias

### Objetivo
Melhorias significativas com modificacoes moderadas.

### Tarefa 2.1: Usar Catalog API ao inves de Agent API

**Arquivo**: `backend/api/nodes.py`

**Localizacao**: Linhas 56-73 (funcao `get_service_count`)

**Modificacao Completa**:
```python
# ANTES - Agent API (lento, requer conexao direta ao agente)
async def get_service_count(member: dict) -> dict:
    """Conta servicos de um no especifico com timeout de 5s"""
    member["services_count"] = 0
    member["site_name"] = sites_map.get(member["addr"], "Nao mapeado")
    try:
        temp_consul = ConsulManager(host=member["addr"])
        services = await asyncio.wait_for(
            temp_consul.get_services(),
            timeout=5.0
        )
        member["services_count"] = len(services)
    except Exception as e:
        pass
    return member

# DEPOIS - Catalog API (rapido, centralizado)
async def get_service_count(member: dict) -> dict:
    """Conta servicos de um no especifico usando Catalog API"""
    member["services_count"] = 0
    member["site_name"] = sites_map.get(member["addr"], "Nao mapeado")
    try:
        # Usar Catalog API centralizada (muito mais rapida)
        # /catalog/node/{node_name} retorna servicos registrados
        node_data = await asyncio.wait_for(
            consul.get_node_services(member["name"]),
            timeout=2.0  # Timeout reduzido
        )
        services = node_data.get("Services", {})
        # Excluir servico "consul" da contagem
        services_count = sum(1 for s in services.values() if s.get("Service") != "consul")
        member["services_count"] = services_count
    except Exception as e:
        # Silencioso - se falhar, deixa services_count = 0
        pass
    return member
```

**Pre-requisito**: Verificar se `ConsulManager.get_node_services()` existe. Se nao, adicionar:

**Arquivo**: `backend/core/consul_manager.py`

```python
async def get_node_services(self, node_name: str) -> dict:
    """
    Retorna servicos registrados em um no especifico via Catalog API

    Args:
        node_name: Nome do no (nao IP)

    Returns:
        Dict com Node e Services

    Endpoint Consul: /v1/catalog/node/{node_name}
    """
    url = f"{self.base_url}/v1/catalog/node/{node_name}"
    async with httpx.AsyncClient(timeout=5.0) as client:
        response = await client.get(url)
        response.raise_for_status()
        return response.json()
```

**Justificativa**:
- Agent API: Cada requisicao vai ao agente do no (latencia alta)
- Catalog API: Centralizada no lider Consul (latencia baixa)
- Reducao de 500-5000ms para 50-200ms por no

**Teste de validacao**:
```bash
# Testar Catalog API diretamente
curl http://consul-server:8500/v1/catalog/node/node-name

# Medir tempo de resposta do endpoint
time curl http://localhost:5000/api/v1/nodes

# Comparar services_count com valor anterior (deve ser igual)
```

---

### Tarefa 2.2: Remover onChange do Array de Dependencias

**Arquivo**: `frontend/src/components/NodeSelector.tsx`

**Localizacao**: Linha 77

**Modificacao**:
```typescript
// ANTES
useEffect(() => {
  if (!loading && nodes.length > 0 && !selectedNode) {
    // ... logica de selecao automatica
  }
}, [loading, nodes, mainServer, selectedNode, showAllNodesOption, onChange]);
// onChange causa re-execucao desnecessaria

// DEPOIS
useEffect(() => {
  if (!loading && nodes.length > 0 && !selectedNode) {
    // ... logica de selecao automatica
  }
  // eslint-disable-next-line react-hooks/exhaustive-deps
}, [loading, nodes, mainServer, selectedNode, showAllNodesOption]);
// onChange removido - eh uma funcao callback que nao deve triggar efeito
```

**Justificativa**:
- `onChange` eh uma funcao passada como prop
- Se o parent re-renderiza, `onChange` eh recriada (nova referencia)
- Isso causa re-execucao do useEffect desnecessariamente
- ESLint warning eh aceitavel aqui (comportamento intencional)

**Teste de validacao**:
- Usar React DevTools Profiler
- Mudar no selecionado
- Verificar que useEffect nao re-executa multiplas vezes

---

## Fase 3: Melhorias de UX

### Objetivo
Polimento final e otimizacoes visuais.

### Tarefa 3.1: Converter Inline Styles para CSS Classes

**Arquivo**: `frontend/src/components/NodeSelector.tsx`

**Localizacao**: Linhas 135-159 (renderizacao das opcoes)

**Motivacao**:
- Inline styles sao recriados a cada render
- CSS classes sao estaticas (zero overhead)

**Criacao de arquivo CSS**:

**Arquivo**: `frontend/src/components/NodeSelector.css`

```css
/* Estilos otimizados para NodeSelector */

.node-option {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.node-option-content {
  display: flex;
  align-items: center;
  gap: 8px;
}

.node-option-addr {
  color: #8c8c8c;
  font-size: 12px;
}
```

**Modificacao no componente**:
```typescript
// Importar CSS
import './NodeSelector.css';

// Usar classes ao inves de inline styles
<Select.Option key={option.key} value={option.value}>
  <div className="node-option">
    <div className="node-option-content">
      <CloudServerOutlined />
      <strong>{option.siteName}</strong>
      <span className="node-option-addr">* {option.node.addr}</span>
    </div>
    <Badge
      status={option.isMaster ? 'success' : 'processing'}
      text={option.isMaster ? 'Master' : 'Slave'}
    />
  </div>
</Select.Option>
```

---

### Tarefa 3.2: Habilitar Virtualizacao (Opcional)

**Condicao**: Aplicar apenas se houver muitos nos (10+)

**Arquivo**: `frontend/src/components/NodeSelector.tsx`

**Modificacao**:
```typescript
<Select
  value={selectedNode}
  onChange={handleChange}
  style={style}
  placeholder={placeholder}
  disabled={disabled}
  loading={loading}
  size="large"
  className="node-selector-large"
  suffixIcon={loading ? <Spin size="small" /> : <CloudServerOutlined />}
  virtual={nodes.length > 10}  // Habilitar virtualizacao para muitos nos
  listHeight={256}  // Altura da lista virtual
>
```

**Justificativa**:
- Virtualizacao evita renderizar todos os itens de uma vez
- Util se houver 10+ nos no cluster
- Ant Design Select suporta nativamente

---

## Resumo dos Arquivos Modificados

| Arquivo | Operacao | Fase | Risco |
|---------|----------|------|-------|
| `backend/api/nodes.py` | EDITAR | 1, 2 | Baixo |
| `backend/core/consul_manager.py` | EDITAR/ADICIONAR | 2 | Baixo |
| `frontend/src/contexts/NodesContext.tsx` | EDITAR | 1 | Baixo |
| `frontend/src/components/NodeSelector.tsx` | EDITAR | 2, 3 | Baixo |
| `frontend/src/components/NodeSelector.css` | **CRIAR** | 3 | Baixo |

---

## Ordem de Execucao Recomendada

### Prioridade Alta
1. **Fase 1.1** - Reduzir timeout (5min)
2. **Fase 1.2** - Aumentar TTL (5min)
3. **Fase 1.3** - Memoizar context (15min)

### Prioridade Media
4. **Fase 2.1** - Catalog API (30min)
5. **Fase 2.2** - Remover onChange deps (10min)

### Prioridade Baixa
6. **Fase 3.1** - CSS classes (20min)
7. **Fase 3.2** - Virtualizacao (10min - opcional)

---

## Metricas de Sucesso

### Antes da Implementacao
Coletar baseline:
```bash
# Backend
for i in {1..10}; do
  time curl -s http://localhost:5000/api/v1/nodes > /dev/null
done

# Frontend (React DevTools)
# Contar renders do NodeSelector ao mudar no
```

### Apos Cada Fase
Validar melhorias:

| Fase | Metrica | Alvo |
|------|---------|------|
| 1 | Tempo resposta (cache miss) | < 3000ms |
| 2 | Tempo resposta (cache miss) | < 600ms |
| 3 | Re-renders | < 3 |

### Apos Conclusao
Validar ganhos totais:

| Metrica | Antes | Depois | Ganho |
|---------|-------|--------|-------|
| Tempo (cache miss) | 250-5150ms | 150-600ms | 75-88% |
| Pior caso | 5150ms | 600ms | 88% |
| Cache misses | 2/min | 1/min | 50% |
| Re-renders | 10+ | 1-2 | 80%+ |

---

## Checklist de Implementacao

### Fase 1 - Quick Wins
- [ ] Timeout reduzido de 5s para 2s
- [ ] TTL aumentado de 30s para 60s
- [ ] Context value memoizado com useMemo
- [ ] Testes de validacao passando

### Fase 2 - Otimizacoes Medias
- [ ] Metodo get_node_services adicionado ao ConsulManager
- [ ] get_service_count usando Catalog API
- [ ] onChange removido do array de deps
- [ ] Testes de validacao passando

### Fase 3 - Melhorias de UX
- [ ] Arquivo NodeSelector.css criado
- [ ] Inline styles convertidos para classes
- [ ] Virtualizacao habilitada (se aplicavel)
- [ ] Testes visuais passando

### Validacao Final
- [ ] Todas as 8 paginas de monitoramento funcionando
- [ ] Metricas de performance atingidas
- [ ] Nenhum erro no console
- [ ] Contrato de API mantido

---

## Rollback Plan

Se houver problemas apos deploy:

### Fase 1
```python
# Reverter timeout
timeout=5.0  # Voltar para 5s

# Reverter TTL
ttl=30  # Voltar para 30s
```

### Fase 2
```python
# Reverter para Agent API
temp_consul = ConsulManager(host=member["addr"])
services = await temp_consul.get_services()
```

### Fase 3
- Remover import do CSS
- Reverter para inline styles

---

## Fase 4: Validacao Final e Relatorio

### Objetivo
Executar testes de comparacao e gerar relatorio de melhorias.

### Tarefa 4.1: Executar Teste de Comparacao

**Comandos**:
```bash
# Executar teste de comparacao DEPOIS das otimizacoes
cd backend
python test_performance_nodes.py --mode compare
```

**Saida Esperada**:
```
================================================================================
RELATORIO DE PERFORMANCE - SPEC-PERF-001
================================================================================

Baseline: 2025-11-21T10:00:00
Current:  2025-11-21T14:00:00

--------------------------------------------------------------------------------
METRICAS DE TEMPO
--------------------------------------------------------------------------------
Media                      1234ms →    456ms  ↓  63.1%
Mediana                    1100ms →    420ms  ↓  61.8%
...

--------------------------------------------------------------------------------
RESUMO
--------------------------------------------------------------------------------
✅ MELHORIA: 63.1% mais rapido
   Tempo medio: 1234ms → 456ms

--------------------------------------------------------------------------------
CRITERIOS DE ACEITACAO
--------------------------------------------------------------------------------
  ✅ Tempo cache miss < 600ms
  ✅ Tempo cache hit < 50ms
  ✅ Melhoria > 50%
  ✅ Zero erros

================================================================================

[REPORT] Salvo em: test_results/nodes_performance_report.md
```

### Tarefa 4.2: Validar 8 Paginas de Monitoramento

**Checklist de validacao manual**:

```markdown
## Checklist de Validacao - SPEC-PERF-001

### Paginas de Monitoramento
- [ ] /monitoring/network-probes - NodeSelector carrega rapido
- [ ] /monitoring/web-probes - Mudanca de no funciona
- [ ] /monitoring/system-exporters - Dados atualizam ao mudar no
- [ ] /monitoring/database-exporters - services_count correto
- [ ] /monitoring/infrastructure-exporters - Badge Master/Slave correto
- [ ] /monitoring/hardware-exporters - site_name mapeado
- [ ] /monitoring/network-devices - Sem erros no console
- [ ] /monitoring/custom-exporters - Opcao "Todos os nos" funciona

### Console do Browser
- [ ] Sem erros JavaScript
- [ ] Sem warnings de React (exceto StrictMode duplicados)
- [ ] NodesContext carrega antes da tabela

### Logs do Backend
- [ ] [PERF] logs aparecem corretamente
- [ ] CACHE HIT em requisicoes subsequentes
- [ ] Tempo < 600ms em cache miss
```

### Tarefa 4.3: Gerar Relatorio Final

**Arquivo**: `backend/test_results/nodes_performance_report.md`

O relatorio eh gerado automaticamente pelo teste de comparacao e inclui:
- Tabela comparativa de metricas
- Porcentagem de melhoria
- Criterios de aceitacao atendidos
- Timestamp de baseline e current

---

## Resumo Completo das Fases

| Fase | Descricao | Tarefas | Tempo Estimado |
|------|-----------|---------|----------------|
| **0** | Baseline e Testes | 3 | 30 min |
| **1** | Quick Wins | 3 | 30 min |
| **2** | Otimizacoes Medias | 2 | 1 hora |
| **3** | Melhorias de UX | 2 | 30 min |
| **4** | Validacao Final | 3 | 30 min |
| **Total** | | 13 | ~3 horas |

---

## Proximos Passos Apos SPEC-PERF-001

1. **Monitorar metricas em producao** por 1 semana
2. **Considerar cache distribuido** se multiplas instancias backend
3. **Implementar stale-while-revalidate** para UX ainda melhor
4. **Adicionar metricas Prometheus** para tempo de resposta do endpoint
