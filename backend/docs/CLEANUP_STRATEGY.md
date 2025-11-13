# ESTRATÉGIA DE LIMPEZA DE CÓDIGO LEGACY

**Data**: 2025-01-09
**Status**: PRONTO PARA EXECUÇÃO
**Impacto Estimado**: ZERO (código nunca usado)

---

## RESUMO DA ANÁLISE

### Descoberta Principal
TODO código relacionado a `blackbox/targets` no KV é OBSOLETO:
- 0 targets armazenados no KV
- Todos os métodos retornam valores vazios/None
- Nenhum endpoint depende desses métodos para funcionar

---

## LOCAIS DE CÓDIGO A REMOVER

### 1. KVManager (`core/kv_manager.py`)

#### Constante (linha 26):
```python
BLACKBOX_TARGETS = f"{PREFIX}/blackbox/targets"  # ← REMOVER
```

#### Métodos (linhas 181-227):
```python
async def get_blackbox_target(self, target_id: str) -> Optional[Dict]:  # ← REMOVER COMPLETO
async def put_blackbox_target(self, target_id: str, target_data: Dict, user: str = "system") -> bool:  # ← REMOVER COMPLETO
async def delete_blackbox_target(self, target_id: str) -> bool:  # ← REMOVER COMPLETO
async def list_blackbox_targets(self, filters: Optional[Dict[str, str]] = None) -> List[Dict]:  # ← REMOVER COMPLETO
```

**Linhas a deletar**: 26, 181-227 (~50 linhas)

---

### 2. BlackboxManager (`core/blackbox_manager.py`)

#### Flag de Feature (linha 43):
```python
ENABLE_KV_STORAGE = True  # Feature flag for dual storage mode  # ← REMOVER
```

#### Bloco de código na lista de targets (linhas 81-83):
```python
kv_filters = {k: v for k, v in filters.items() if v}
kv_targets = await self.kv.list_blackbox_targets(kv_filters or None)  # ← REMOVER
kv_map = {target.get("id"): target for target in kv_targets}  # ← REMOVER
```

E depois remover uso de `kv_data` na linha 93:
```python
kv_data = kv_map.get(target_id, {})  # ← REMOVER
```

#### Bloco de KV Storage no `add_target()` (linhas 337-370):
```python
# Also store in KV if dual storage is enabled
if self.ENABLE_KV_STORAGE:  # ← REMOVER TODO ESTE BLOCO
    kv_data = {
        "id": service_id,
        "group": group,
        ...
    }
    await self.kv.put_blackbox_target(service_id, kv_data, user)
    ...
```

#### Bloco de KV Storage no `delete_target()` (linhas 404-420):
```python
# Also delete from KV if dual storage is enabled
if self.ENABLE_KV_STORAGE:  # ← REMOVER TODO ESTE BLOCO
    await self.kv.delete_blackbox_target(service_id)
    ...
```

#### Método `get_targets_by_group()` (linhas 718-729):
```python
async def get_targets_by_group(self, group_id: str) -> List[Dict]:
    return await self.kv.list_blackbox_targets(filters={"group": group_id})  # ← SUBSTITUIR por consulta ao Services API
```

**Ação**: Reimplementar para buscar do Services API usando filtro de grupo via tags/meta

#### Método `bulk_enable_disable()` (linhas 754-768):
Remover chamadas KV:
```python
# Linha 756:
target = await self.kv.get_blackbox_target(tid)  # ← REMOVER

# Linha 766:
await self.kv.put_blackbox_target(target["id"], target, user)  # ← REMOVER
```

**Ação**: Reimplementar usando apenas Services API (enabled/disabled via tags ou Meta)

---

### 3. API Blackbox (`api/blackbox.py`)

#### Linha 159:
```python
await kv.delete_blackbox_target(request.service_id)  # ← REMOVER
```

#### Linha 238:
```python
await kv.delete_blackbox_target(request.service_id)  # ← REMOVER
```

---

## RESUMO DE LINHAS A REMOVER

| Arquivo | Linhas Aproximadas | Descrição |
|---------|-------------------|-----------|
| `core/kv_manager.py` | ~50 linhas | 4 métodos + constante |
| `core/blackbox_manager.py` | ~80 linhas | 3 blocos if + flag |
| `api/blackbox.py` | 2 linhas | 2 chamadas delete |
| **TOTAL** | **~132 linhas** | Código morto removido |

---

## FUNCIONALIDADES A REIMPLEMENTAR

### 1. `get_targets_by_group()` em BlackboxManager

**Antes (KV)**:
```python
async def get_targets_by_group(self, group_id: str) -> List[Dict]:
    return await self.kv.list_blackbox_targets(filters={"group": group_id})
```

**Depois (Services API)**:
```python
async def get_targets_by_group(self, group_id: str) -> List[Dict]:
    """
    Busca targets por grupo consultando Services API.

    IMPORTANTE: Grupos agora são armazenados em:
    - skills/eye/blackbox/groups/{group_id}.json (mantido - metadados apenas)
    - Services API com Meta.group (source of truth)
    """
    # Buscar todos os services blackbox
    services = await self.get_targets(group=group_id)

    # Filtrar por grupo
    return [s for s in services if s.get('Meta', {}).get('group') == group_id]
```

### 2. `bulk_enable_disable()` em BlackboxManager

**Estratégia**: Usar tags `enabled`/`disabled` no Services API ou campo Meta.enabled

---

## VALIDAÇÃO PRÉ-LIMPEZA

- [x] Confirmado: 0 targets no KV `skills/eye/blackbox/targets`
- [x] Confirmado: Todos endpoints usam Services API
- [x] Confirmado: Métodos KV retornam vazio/None
- [x] Mapeado: Todas as chamadas aos métodos obsoletos
- [ ] Reimplementar: `get_targets_by_group()` e `bulk_enable_disable()`
- [ ] Testar: Endpoints críticos após limpeza

---

## ORDEM DE EXECUÇÃO

1. ✅ **Análise completa** (CONCLUÍDA)
2. 🔶 **Reimplementar funcionalidades** (EM ANDAMENTO)
   - `get_targets_by_group()`
   - `bulk_enable_disable()`
3. ⏳ **Remover código legacy**
   - KVManager
   - BlackboxManager
   - API Blackbox
4. ⏳ **Testar endpoints críticos**
5. ⏳ **Validar integridade**

---

## RISCOS IDENTIFICADOS

### ZERO RISCOS DE QUEBRA
- Métodos nunca retornam dados úteis (KV vazio)
- Endpoints não dependem dos métodos KV para funcionar
- Todas as operações reais usam Services API

### ÚNICO PONTO DE ATENÇÃO
- Métodos `get_targets_by_group()` e `bulk_enable_disable()` precisam ser reimplementados ANTES da remoção

---

**Próximo Passo**: Reimplementar `get_targets_by_group()` e `bulk_enable_disable()` usando Services API.
