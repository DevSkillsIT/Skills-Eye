# ANÁLISE COMPLETA - Sistemas de Cache Internos
**Data:** 2025-11-15 16:50
**Objetivo:** Identificar todos os caches internos que deveriam usar LocalCache global

---

## 🔍 ARQUIVOS IDENTIFICADOS

### 1. ✅ **monitoring_unified.py** - JÁ CORRIGIDO
- **Caches:** `_nodes_cache`, `_services_cache`
- **Status:** ✅ Migrado para LocalCache global
- **Commit:** Realizado hoje

---

### 2. ❌ **metadata_fields_manager.py** - PRECISA CORREÇÃO
**Localização:** `backend/api/metadata_fields_manager.py`

**Cache Interno:**
```python
_servers_cache = {
    "data": None,
    "timestamp": None,
    "ttl": 300  # 5 minutos
}
```

**Uso:**
- Linha 665-674: Verificação de cache
- Linha 801-804: Atualização de cache
- **Função:** `get_servers_from_env()`
- **Finalidade:** Cache de servidores Prometheus (5 minutos)

**Impacto:**
- ⚠️ NÃO aparece no Cache Management
- ⚠️ Impossível invalidar via UI
- ⚠️ Dificulta debugging

**Prioridade:** 🔴 ALTA (usado pela página de Metadata Fields)

---

### 3. ❌ **nodes.py** - PRECISA CORREÇÃO
**Localização:** `backend/api/nodes.py`

**Cache Interno:**
```python
_nodes_cache: Optional[Dict] = None
_nodes_cache_time: float = 0
NODES_CACHE_TTL = 30  # 30 segundos
```

**Uso:**
- Linha 13-15: Declaração de cache
- Linha 21-24: Verificação de cache
- Linha 83: Atualização de cache
- **Endpoint:** `GET /nodes/`
- **Finalidade:** Cache de nós do Consul (30 segundos)

**Impacto:**
- ⚠️ NÃO aparece no Cache Management
- ⚠️ Impossível invalidar via UI
- ⚠️ Usa timestamp manual (menos preciso)

**Prioridade:** 🔴 ALTA (usado pela página de Nodes)

---

### 4. ✅ **dashboard.py** - CACHE COMENTADO (OK)
**Localização:** `backend/api/dashboard.py`

```python
# from core.cache_manager import cache_manager  # COMENTADO
```

**Status:** ✅ Não usa cache interno
**Ação:** Nenhuma necessária

---

### 5. ✅ **optimized_endpoints.py** - CACHE COMENTADO (OK)
**Localização:** `backend/api/optimized_endpoints.py`

```python
# from core.cache_manager import cache_manager  # COMENTADO
CACHE_TTL = {  # Apenas constantes de TTL
    'services': 60,
    'nodes': 300,
    # ...
}
```

**Status:** ✅ Não usa cache interno
**Ação:** Nenhuma necessária

---

## 📊 RESUMO

| Arquivo | Cache Interno | Status | Prioridade |
|---------|--------------|--------|------------|
| monitoring_unified.py | `_nodes_cache`, `_services_cache` | ✅ Corrigido | - |
| metadata_fields_manager.py | `_servers_cache` | ❌ Precisa migrar | 🔴 Alta |
| nodes.py | `_nodes_cache` | ❌ Precisa migrar | 🔴 Alta |
| dashboard.py | - | ✅ OK | - |
| optimized_endpoints.py | - | ✅ OK | - |

---

## 🎯 PLANO DE MIGRAÇÃO

### Prioridade 1: **metadata_fields_manager.py**
```python
# ANTES:
_servers_cache = {
    "data": None,
    "timestamp": None,
    "ttl": 300
}

# DEPOIS:
from core.cache_manager import get_cache
cache = get_cache(ttl_seconds=60)

# Usar chave: "metadata:servers:all"
```

**Benefícios:**
- ✅ Aparece no Cache Management
- ✅ Pode invalidar via UI
- ✅ Estatísticas unificadas

---

### Prioridade 2: **nodes.py**
```python
# ANTES:
_nodes_cache: Optional[Dict] = None
_nodes_cache_time: float = 0

# DEPOIS:
from core.cache_manager import get_cache
cache = get_cache(ttl_seconds=60)

# Usar chave: "nodes:list:all"
```

**Benefícios:**
- ✅ Aparece no Cache Management
- ✅ Cache thread-safe (asyncio.Lock)
- ✅ Controle de TTL centralizado

---

## 🔧 PRÓXIMOS PASSOS

1. ✅ Migrar `metadata_fields_manager.py`
2. ✅ Migrar `nodes.py`
3. ✅ Reiniciar backend
4. ✅ Testar Cache Management
5. ✅ Validar páginas afetadas

---

## 📝 CHAVES DE CACHE PROPOSTAS

```
Estrutura: {domínio}:{recurso}:{filtros}

Exemplos:
- monitoring:nodes:all
- monitoring:services:network-probes:all:all:all
- metadata:servers:all
- nodes:list:all
- nodes:services:{node_addr}
```

---

**Total de migrações necessárias:** 2 arquivos
**Impacto:** Médio (páginas específicas)
**Tempo estimado:** 20 minutos
