---
id: SPEC-PERF-001
version: "1.0.0"
status: draft
created: 2025-11-21
updated: 2025-11-21
author: Claude Code
priority: HIGH
---

# HISTORY

| Versao | Data       | Autor       | Descricao                      |
|--------|------------|-------------|--------------------------------|
| 1.0.0  | 2025-11-21 | Claude Code | Versao inicial do SPEC         |

---

# SPEC-PERF-001: Otimizacao de Performance do NodeSelector

## Resumo Executivo

Este SPEC define otimizacoes de performance criticas para o endpoint `/api/v1/nodes` e componentes frontend relacionados. O problema atual causa tempos de resposta de ate 5150ms (cache miss) e 15s no pior caso (3 nos com timeout), impactando diretamente a experiencia do usuario nas 8 paginas de monitoramento.

## Contexto e Motivacao

### Problema Identificado

O endpoint `/api/v1/nodes` demora ate 5s por no para contar servicos, causando:

| Metrica | Valor Atual | Impacto |
|---------|-------------|---------|
| Tempo medio (cache miss) | 250-5150ms | Pagina lenta para carregar |
| Pior caso | 15s (3 nos x 5s timeout) | UX degradada, usuario abandona |
| Cache TTL | 30s | Cache misses frequentes (2/min) |
| Re-renders | 10+ por mudanca de no | Performance frontend degradada |

### Causa Raiz (Backend)

```python
# backend/api/nodes.py - linha 67
services = await asyncio.wait_for(
    temp_consul.get_services(),  # Usa Agent API - LENTO
    timeout=5.0  # Timeout muito alto
)
```

**Problema**: A Agent API (`/agent/services`) requer conexao direta ao agente de cada no, com alta latencia. A Catalog API (`/catalog/node/{node_name}`) eh centralizada e muito mais rapida.

### Causa Raiz (Frontend)

```typescript
// frontend/src/components/NodeSelector.tsx - linha 77
useEffect(() => {
    // ...
}, [loading, nodes, mainServer, selectedNode, showAllNodesOption, onChange]);
// onChange no array causa re-renders desnecessarios
```

```typescript
// frontend/src/contexts/NodesContext.tsx - linha 77-88
// Context value nao memoizado causa re-renders em cascata
```

### Arquivos Afetados

#### Backend
- `backend/api/nodes.py` - endpoint principal com timeout de 5s
- `backend/core/consul_manager.py` - ConsulManager class
- `backend/core/config.py` - configuracoes

#### Frontend
- `frontend/src/components/NodeSelector.tsx` - componente seletor
- `frontend/src/contexts/NodesContext.tsx` - provider de nos

### Paginas Impactadas

As 8 paginas de monitoramento dinamico que usam o NodeSelector:

1. `/monitoring/network-probes`
2. `/monitoring/web-probes`
3. `/monitoring/system-exporters`
4. `/monitoring/database-exporters`
5. `/monitoring/infrastructure-exporters`
6. `/monitoring/hardware-exporters`
7. `/monitoring/network-devices`
8. `/monitoring/custom-exporters`

**NOTA**: As paginas `/exporters` e `/services` serao desativadas (legadas).

---

## Functional Requirements (MUST)

### FR-001: Reducao de Timeout por No
**EARS Format**: O sistema **DEVE** reduzir o timeout de conexao por no de 5s para 2s no endpoint `/api/v1/nodes`.

**Detalhes**:
- Modificar `backend/api/nodes.py` linha 67
- Alterar `timeout=5.0` para `timeout=2.0`
- Manter fallback `services_count = 0` se timeout ocorrer

**Justificativa**: 2s eh suficiente para conexao local em datacenter. Se nao responder em 2s, provavelmente o no esta com problemas.

### FR-002: Uso de Catalog API
**EARS Format**: O sistema **DEVE** usar a Catalog API (`/catalog/node/{node_name}`) ao inves da Agent API (`/agent/services`) para contar servicos.

**Detalhes**:
- Catalog API eh centralizada no servidor Consul lider
- Nao requer conexao direta ao agente do no
- Reduz latencia de 500-5000ms para 50-200ms por no

**Codigo sugerido**:
```python
# ANTES (Agent API - lento)
temp_consul = ConsulManager(host=member["addr"])
services = await temp_consul.get_services()

# DEPOIS (Catalog API - rapido)
node_data = await consul.get_node_services(member["name"])
services_count = len(node_data.get("Services", {}))
```

### FR-003: Aumento de TTL do Cache
**EARS Format**: O sistema **DEVE** aumentar o TTL do cache de 30s para 60s no endpoint `/api/v1/nodes`.

**Detalhes**:
- Modificar `backend/api/nodes.py` linha 86
- Alterar `ttl=30` para `ttl=60`
- Nos raramente mudam em menos de 60s
- Reduz cache misses de 2/min para 1/min

### FR-004: Memoizacao do Context Value
**EARS Format**: O sistema **DEVE** memoizar o value do NodesContext com `useMemo` para evitar re-renders desnecessarios.

**Detalhes**:
- Modificar `frontend/src/contexts/NodesContext.tsx` linhas 77-88
- Envolver `value` com `useMemo` dependendo de `[nodes, mainServer, loading, error, loadNodes]`

**Codigo sugerido**:
```typescript
const contextValue = useMemo(() => ({
  nodes,
  mainServer,
  loading,
  error,
  reload: loadNodes,
}), [nodes, mainServer, loading, error]);
```

---

## Non-Functional Requirements (SHOULD)

### NFR-001: Tempo de Resposta
O sistema **DEVERIA** responder em menos de 600ms (cache miss) para o endpoint `/api/v1/nodes`.

**Metricas alvo**:
- P50: < 200ms
- P95: < 500ms
- P99: < 600ms

### NFR-002: Reducao de Re-renders
O sistema **DEVERIA** reduzir re-renders em 80% ao mudar no selecionado.

**Estado atual**: 10+ re-renders por mudanca
**Alvo**: 1-2 re-renders por mudanca

### NFR-003: Compatibilidade
O sistema **DEVERIA** manter compatibilidade com todas as 8 paginas de monitoramento sem alteracoes em seus codigos.

### NFR-004: Cache Hits
O sistema **DEVERIA** aumentar taxa de cache hits de 50% para 80%+.

---

## Interface Requirements (SHALL)

### IR-001: Contrato de API Mantido
O endpoint `/api/v1/nodes` **MANTERA** o mesmo contrato de resposta:

```json
{
  "success": true,
  "data": [
    {
      "name": "string",
      "addr": "string",
      "port": "number",
      "status": "number",
      "tags": {},
      "services_count": "number",
      "site_name": "string"
    }
  ],
  "total": "number",
  "main_server": "string"
}
```

### IR-002: Interface de Props Mantida
O componente `NodeSelector` **MANTERA** a mesma interface de props:

```typescript
interface NodeSelectorProps {
  value?: string;
  onChange?: (nodeAddr: string, node?: ConsulNode) => void;
  style?: React.CSSProperties;
  placeholder?: string;
  disabled?: boolean;
  showAllNodesOption?: boolean;
}
```

---

## Design Constraints (MUST)

### DC-001: Fallback Obrigatorio
**SE** a contagem de servicos falhar para um no, O sistema **DEVE** retornar `services_count = 0` sem erro.

**Justificativa**: Um no com problema nao deve impedir a listagem dos demais.

### DC-002: Sem Quebra de Funcionalidade
O sistema **NAO DEVE** quebrar funcionalidade existente das 8 paginas de monitoramento.

### DC-003: Estrutura de Dados Preservada
O sistema **NAO DEVE** alterar a estrutura de dados retornada pela API.

### DC-004: Sem Dependencias Externas
As otimizacoes **NAO DEVEM** adicionar novas dependencias ao projeto.

---

## Arquivos a Serem Modificados

### Backend

| Arquivo | Modificacao | Linhas Estimadas | Risco |
|---------|-------------|------------------|-------|
| `backend/api/nodes.py` | Reduzir timeout, aumentar TTL, usar Catalog API | ~20 linhas | Baixo |
| `backend/core/consul_manager.py` | Adicionar metodo get_node_services se nao existir | ~10 linhas | Baixo |

### Frontend

| Arquivo | Modificacao | Linhas Estimadas | Risco |
|---------|-------------|------------------|-------|
| `frontend/src/contexts/NodesContext.tsx` | Memoizar context value | ~5 linhas | Baixo |
| `frontend/src/components/NodeSelector.tsx` | Remover onChange do useEffect deps | ~2 linhas | Baixo |

---

## Ganhos Esperados

| Metrica | Antes | Depois | Ganho |
|---------|-------|--------|-------|
| Tempo (cache miss) | 250-5150ms | 150-600ms | 75-88% |
| Pior caso | 5150ms | 600ms | 88% |
| Cache misses | 2/min | 1/min | 50% |
| Re-renders | 10+ | 1-2 | 80%+ |
| Taxa cache hit | ~50% | ~80%+ | 60%+ |

---

## Riscos e Mitigacoes

| Risco | Probabilidade | Impacto | Mitigacao |
|-------|---------------|---------|-----------|
| Catalog API retorna dados incompletos | Baixa | Media | Testar com cluster real, manter fallback |
| TTL alto causa dados stale | Baixa | Baixa | 60s ainda eh aceitavel para lista de nos |
| Memoizacao causa bugs | Baixa | Media | Testar todas as 8 paginas apos mudanca |
| Timeout baixo causa mais zeros | Media | Baixa | 2s eh suficiente para LAN, monitorar metricas |

---

## Dependencias Tecnicas

1. **ConsulManager.get_node_services()** - Metodo para Catalog API
2. **LocalCache** - Sistema de cache existente (ja implementado)
3. **NodesContext** - Provider de nos (ja implementado)
4. **React.useMemo** - Hook nativo do React

---

## Estimativa de Complexidade

- **Total**: Baixa-Media
- **Backend**: Baixa (modificacoes pontuais)
- **Frontend**: Baixa (otimizacoes simples)
- **Testes**: Media (validar 8 paginas)

---

## Notas de Implementacao

1. **Implementar em fases**: Quick wins primeiro (timeout + TTL), depois Catalog API
2. **Testar cada fase**: Validar metricas antes de prosseguir
3. **Monitorar logs**: Verificar se timeouts estao ocorrendo com 2s
4. **Rollback facil**: Mudancas sao reversiveis com alteracao de valores
5. **Nao alterar DynamicMonitoringPage**: As 8 rotas usam o mesmo componente base
