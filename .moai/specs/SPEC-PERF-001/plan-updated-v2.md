# Plano de Implementacao CORRIGIDO - SPEC-PERF-001

## Data: 2025-11-21
## Versao: 3.0 (Correcao do bug identificado)

---

## BUG IDENTIFICADO NA IMPLEMENTACAO ANTERIOR

### Causa do Revert (commit 410a5ad)

A implementacao anterior (commit 266c17c) usou `member["name"]` que **NAO EXISTE** no retorno de `get_members()`.

**Codigo ERRADO (commit 266c17c):**
```python
node_data = await consul.get_node_services(member["name"])  # "name" nao existe!
```

**Retorno real de get_members():**
```python
{
    "node": m["Name"],    # <-- ESTE eh o nome do no
    "addr": addr,         # IP
    "status": ...,
    "type": ...
}
```

**Codigo CORRETO:**
```python
node_data = await consul.get_node_services(member["node"])  # Usar "node", nao "name"
```

### Impacto do Bug

Como `member["name"]` nao existe (KeyError silenciado pelo try/except), todos os nos retornavam `services_count = 0`, causando:
- Contadores de servicos zerados
- Falsa impressao de que a Catalog API nao funciona

---

## Plano de Implementacao Corrigido

### Fase 1: Quick Wins (Baixo Risco)

#### 1.1 Reduzir Timeout (5s -> 2s)
**Arquivo**: `backend/api/nodes.py` linha 67

```python
# ANTES
timeout=5.0

# DEPOIS
timeout=2.0
```

#### 1.2 Aumentar TTL (30s -> 60s)
**Arquivo**: `backend/api/nodes.py` linha 86

```python
# ANTES
await cache.set(cache_key, result, ttl=30)

# DEPOIS
await cache.set(cache_key, result, ttl=60)
```

#### 1.3 Memoizar Context Value
**Arquivo**: `frontend/src/contexts/NodesContext.tsx`

```typescript
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
```

---

### Fase 2: Catalog API (Risco Medio - CORRIGIDO)

#### 2.1 Substituir Agent API por Catalog API
**Arquivo**: `backend/api/nodes.py` linhas 56-73

```python
async def get_service_count(member: dict) -> dict:
    """
    Conta servicos de um no especifico usando Catalog API

    SPEC-PERF-001: Otimizacoes implementadas:
    - Timeout reduzido de 5s para 2s (suficiente para LAN)
    - Usa Catalog API centralizada ao inves de Agent API
    - Catalog API eh muito mais rapida (50-200ms vs 500-5000ms)

    CORRECAO: Usar member["node"] (nao member["name"])
    """
    member["services_count"] = 0
    member["site_name"] = sites_map.get(member["addr"], "Nao mapeado")

    try:
        # CORRIGIDO: Usar member["node"] que contem o nome do no
        # ANTES (ERRADO): consul.get_node_services(member["name"])
        node_data = await asyncio.wait_for(
            consul.get_node_services(member["node"]),  # CORRETO!
            timeout=2.0
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

**Validacao**:
- Testar que services_count > 0 para nos com servicos
- Comparar com contagem anterior da Agent API

---

### Fase 3: Melhorias Frontend (Baixo Risco)

#### 3.1 Remover onChange das Dependencias
**Arquivo**: `frontend/src/components/NodeSelector.tsx` linha 77

```typescript
// ANTES
}, [loading, nodes, mainServer, selectedNode, showAllNodesOption, onChange]);

// DEPOIS
// eslint-disable-next-line react-hooks/exhaustive-deps
}, [loading, nodes, mainServer, selectedNode, showAllNodesOption]);
```

---

### Fase 4: Validacao Final

1. Executar teste de comparacao: `python test_performance_nodes.py --mode compare`
2. Validar 8 paginas de monitoramento
3. Verificar que services_count > 0 para nos ativos

---

## Checklist de Validacao

### Backend
- [ ] Timeout reduzido de 5s para 2s
- [ ] TTL aumentado de 30s para 60s
- [ ] Catalog API usando `member["node"]` (CORRECAO CRITICA)
- [ ] services_count > 0 para nos com servicos

### Frontend
- [ ] Context value memoizado com useMemo
- [ ] loadNodes memoizado com useCallback
- [ ] onChange removido das dependencias

### Performance
- [ ] Tempo (cache miss) < 600ms
- [ ] services_count correto (nao zerado)

---

## Riscos Mitigados

| Risco Original | Mitigacao |
|----------------|-----------|
| member["name"] nao existe | Usar member["node"] (CORRIGIDO) |
| services_count = 0 | Validar apos implementacao |

---

## Ordem de Execucao Recomendada

1. **Fase 1.1-1.2** - Timeout e TTL (5 min, sem risco)
2. **Fase 1.3** - Memoizacao frontend (10 min, baixo risco)
3. **Fase 2.1** - Catalog API CORRIGIDA (15 min, risco medio)
4. **Fase 3.1** - Remover onChange deps (5 min, baixo risco)
5. **Fase 4** - Validacao completa (15 min)

**Tempo total estimado**: 50 minutos

---

## Conclusao

O bug `member["name"]` (que deveria ser `member["node"]`) foi identificado como causa do revert anterior. Com esta correcao, a implementacao da Catalog API sera funcional.

**Recomendacao**: Implementar em fases, validando services_count apos Fase 2.
