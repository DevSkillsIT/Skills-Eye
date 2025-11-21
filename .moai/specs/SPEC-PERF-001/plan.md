# Plano de Implementacao - SPEC-PERF-001

## Visao Geral

Este documento detalha o plano de implementacao passo a passo para otimizacao de performance do NodeSelector e endpoint `/api/v1/nodes`.

**Estrategia**: Implementacao em 3 fases, do menor risco ao maior, com validacao entre fases.

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

## Proximos Passos Apos SPEC-PERF-001

1. **Monitorar metricas em producao** por 1 semana
2. **Considerar cache distribuido** se multiplas instancias backend
3. **Implementar stale-while-revalidate** para UX ainda melhor
4. **Adicionar metricas Prometheus** para tempo de resposta do endpoint
