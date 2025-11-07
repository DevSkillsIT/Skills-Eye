# Status de Update em TODAS as Páginas

## 📊 RESUMO EXECUTIVO

| Página | Função Update | Endpoint Backend | Status | Observações |
|--------|---------------|------------------|---------|-------------|
| **Services** | `consulAPI.updateService()` | `PUT /api/v1/services/{id}` | ✅ **CORRIGIDO** | Não deleta mais o serviço |
| **Exporters** | `consulAPI.updateService()` | `PUT /api/v1/services/{id}` | ✅ **CORRIGIDO** | Usa mesmo endpoint que Services |
| **BlackboxTargets** | `consulAPI.updateBlackboxTarget()` | `PUT /api/v1/blackbox` | ✅ **OK** | Delete + Add é intencional (ID pode mudar) |
| **BlackboxGroups** | `consulAPI.updateBlackboxGroup()` | `PUT /api/v1/blackbox/groups/{id}` | ✅ **OK** | Armazenado em KV store, não é serviço |
| **Nodes** | ❌ Não tem | - | ✅ **N/A** | Página apenas lista nós, sem edição |
| **Dashboard** | ❌ Não tem | - | ✅ **N/A** | Página apenas exibe métricas |
| **AuditLog** | ❌ Não tem | - | ✅ **N/A** | Página apenas lista logs |

---

## 📄 DETALHAMENTO POR PÁGINA

### 1. **Services.tsx** ✅ CORRIGIDO

**Arquivo**: `frontend/src/pages/Services.tsx` (linha 681)

**Função de Update**:
```typescript
const handleSubmit = async (values: ServiceFormValues) => {
  if (formMode === 'edit' && currentRecord) {
    const updatePayload = {
      address: payload.address,
      port: payload.port,
      tags: payload.tags,
      Meta: payload.Meta,
      node_addr: currentRecord.nodeAddr || currentRecord.node,
    };
    await consulAPI.updateService(currentRecord.id, updatePayload);
  }
};
```

**Endpoint Backend**: `PUT /api/v1/services/{service_id}`

**Correção Aplicada**:
- ✅ Backend corrigido em `backend/core/consul_manager.py` (linha 338-384)
- ✅ **NÃO faz mais deregister** (não deleta o serviço)
- ✅ **Apenas RE-REGISTRA** com mesmo ID (Consul atualiza automaticamente)
- ✅ Converte `Service` → `Name`
- ✅ Remove campos read-only

**Status**: ✅ **FUNCIONANDO**

---

### 2. **Exporters.tsx** ✅ CORRIGIDO

**Arquivo**: `frontend/src/pages/Exporters.tsx` (linha 519)

**Função de Update**:
```typescript
const handleEditSubmit = async (values: any) => {
  if (!editingExporter) return false;

  const updatePayload = {
    address: values.address || editingExporter.address,
    port: values.port || editingExporter.port,
    tags: values.tags || editingExporter.tags || [],
    Meta: {
      ...editingExporter.meta,
      company: values.company || editingExporter.meta?.company,
      project: values.project || editingExporter.meta?.project,
      env: values.env || editingExporter.meta?.env,
    },
    node_addr: editingExporter.nodeAddr || editingExporter.node,
  };

  await consulAPI.updateService(editingExporter.id, updatePayload);
};
```

**Endpoint Backend**: `PUT /api/v1/services/{service_id}` (MESMO que Services)

**Correção Aplicada**:
- ✅ Usa o **mesmo endpoint** que Services.tsx
- ✅ **Mesma correção** aplicada automaticamente
- ✅ Backend não deleta mais o exporter ao editar

**Status**: ✅ **FUNCIONANDO**

---

### 3. **BlackboxTargets.tsx** ✅ OK (Não precisa correção)

**Arquivo**: `frontend/src/pages/BlackboxTargets.tsx` (linha 481)

**Função de Update**:
```typescript
const handleSubmit = async (values: BlackboxFormValues) => {
  if (formMode === 'edit' && currentRecord) {
    const current = mapRecordToPayload(currentRecord);
    await consulAPI.updateBlackboxTarget(current, payload);
  }
};
```

**Endpoint Backend**: `PUT /api/v1/blackbox`

**Backend Implementation** (`backend/core/blackbox_manager.py` linha 414):
```python
async def update_target(self, old_target: Dict, new_target: Dict):
    """Updates a target by removing and re-adding it."""
    # 1. Delete old
    delete_ok = await self.delete_target(...)
    # 2. Add new
    add_ok = await self.add_target(...)
```

**Por que Delete + Add é CORRETO aqui?**
- O ID do blackbox target é composto por: `{module}/{company}/{project}/{env}/{name}`
- Se o usuário alterar qualquer um desses campos, **o ID muda completamente**
- Exemplo: `icmp/CompanyA/ProjectX/prod/target1` → `http/CompanyA/ProjectX/prod/target1`
- **Delete do antigo + Add do novo** é a única forma de "renomear" o serviço

**Status**: ✅ **OK - Comportamento intencional e correto**

---

### 4. **BlackboxGroups.tsx** ✅ OK (Armazenamento diferente)

**Arquivo**: `frontend/src/pages/BlackboxGroups.tsx` (linha 239)

**Função de Update**:
```typescript
const handleUpdateGroup = async (values: GroupFormData) => {
  const updates: Partial<BlackboxGroup> = {
    name: values.name,
    description: values.description,
    tags: values.tags ? values.tags.split(',').map((t) => t.trim()) : undefined,
    metadata: values.metadata ? JSON.parse(values.metadata) : undefined,
  };

  await consulAPI.updateBlackboxGroup(selectedGroup.id, updates);
};
```

**Endpoint Backend**: `PUT /api/v1/blackbox/groups/{group_id}`

**Armazenamento**: **Consul KV Store** (não é um serviço!)

**Backend Implementation** (`backend/api/blackbox.py` linha 259):
```python
@router.put("/groups/{group_id}")
async def update_group(group_id: str, updates: GroupUpdate, user: str = Query("system")):
    # Atualiza diretamente no KV store
    success = await kv.update_blackbox_group(group_id, updates.model_dump(exclude_unset=True), user)
```

**Por que não tem o problema?**
- Blackbox Groups são armazenados no **KV Store do Consul** (`consul://kv/blackbox/groups/...`)
- **NÃO são serviços Consul** (não usam `/agent/service/register`)
- Update é direto no KV (não precisa deregister/register)

**Status**: ✅ **OK - Sistema diferente**

---

### 5. **Nodes.tsx** ✅ N/A (Não tem edição)

**Arquivo**: `frontend/src/pages/Nodes.tsx`

**Função de Update**: ❌ Não existe

**Comportamento**: Página apenas **lista nós** do cluster Consul. Nós não podem ser editados pela API (são gerenciados pelo Consul agent).

**Status**: ✅ **N/A**

---

### 6. **Dashboard.tsx** ✅ N/A (Não tem edição)

**Arquivo**: `frontend/src/pages/Dashboard.tsx`

**Função de Update**: ❌ Não existe

**Comportamento**: Página apenas **exibe métricas** agregadas (cards, gráficos, estatísticas).

**Status**: ✅ **N/A**

---

### 7. **AuditLog.tsx** ✅ N/A (Não tem edição)

**Arquivo**: `frontend/src/pages/AuditLog.tsx`

**Função de Update**: ❌ Não existe

**Comportamento**: Página apenas **lista logs** de auditoria do KV store. Logs não podem ser editados (são append-only).

**Status**: ✅ **N/A**

---

## 🔧 CORREÇÕES IMPLEMENTADAS

### Arquivo: `backend/core/consul_manager.py` (linhas 338-384)

**Antes (ERRADO)**:
```python
async def update_service(self, service_id: str, service_data: Dict):
    # ❌ DELETAVA o serviço!
    await self.deregister_service(service_id)  # Deleta
    await asyncio.sleep(0.5)
    await self.register_service(service_data)  # Recria
```

**Depois (CORRETO)**:
```python
async def update_service(self, service_id: str, service_data: Dict):
    """
    Segundo documentação oficial do Consul:
    - Para atualizar, basta RE-REGISTRAR com mesmo ID
    - NÃO fazer deregister antes
    - Consul substitui automaticamente
    """
    # Normalizar dados
    normalized_data = service_data.copy()

    # Converter Service → Name
    if "Service" in normalized_data:
        normalized_data["Name"] = normalized_data.pop("Service")

    # Garantir ID
    if "ID" not in normalized_data:
        normalized_data["ID"] = service_id

    # Remover campos read-only
    readonly_fields = ["CreateIndex", "ModifyIndex", "ContentHash", "Datacenter", "PeerName"]
    for field in readonly_fields:
        normalized_data.pop(field, None)

    # ✅ Apenas RE-REGISTRAR (não deleta!)
    return await self.register_service(normalized_data)
```

### Arquivo: `backend/api/services.py` (linhas 477-489)

**Antes**:
```python
# Merge direto (causava campos duplicados)
for key, value in update_data.items():
    if value is not None and key != "node_addr":
        updated_service[key] = value
```

**Depois**:
```python
# Mapear campos lowercase → Uppercase
field_mapping = {
    "address": "Address",
    "port": "Port",
    "tags": "Tags",
    "name": "Name",
}

for key, value in update_data.items():
    if value is not None and key != "node_addr":
        consul_key = field_mapping.get(key, key)
        updated_service[consul_key] = value
```

---

## ✅ PÁGINAS QUE PRECISAVAM DE CORREÇÃO

1. ✅ **Services.tsx** - CORRIGIDO
2. ✅ **Exporters.tsx** - CORRIGIDO (usa mesmo endpoint)

## ✅ PÁGINAS QUE JÁ ESTAVAM OK

3. ✅ **BlackboxTargets.tsx** - OK (delete + add é intencional)
4. ✅ **BlackboxGroups.tsx** - OK (KV store, não serviço)
5. ✅ **Nodes.tsx** - N/A (sem edição)
6. ✅ **Dashboard.tsx** - N/A (sem edição)
7. ✅ **AuditLog.tsx** - N/A (sem edição)

---

## 🎯 COMO TESTAR CADA PÁGINA

### Services
1. Ir para http://localhost:8082/services
2. Selecionar um serviço
3. Clicar em **Editar**
4. Alterar Port/Address/Tags
5. Salvar
6. ✅ Verificar que serviço foi **atualizado** (não deletado)

### Exporters
1. Ir para http://localhost:8082/exporters
2. Selecionar um exporter
3. Clicar em **Editar**
4. Alterar company/project/env
5. Salvar
6. ✅ Verificar que exporter foi **atualizado** (não deletado)

### BlackboxTargets
1. Ir para http://localhost:8082/blackbox-targets
2. Selecionar um target
3. Clicar em **Editar**
4. Alterar instance/interval/timeout
5. Salvar
6. ✅ Verificar que target foi atualizado

### BlackboxGroups
1. Ir para http://localhost:8082/blackbox-groups
2. Selecionar um grupo
3. Clicar em **Editar**
4. Alterar name/description
5. Salvar
6. ✅ Verificar que grupo foi atualizado

---

## 📚 DOCUMENTAÇÃO RELACIONADA

- [CONSUL_UPDATE_FIX.md](./CONSUL_UPDATE_FIX.md) - Análise detalhada da correção
- [Consul API Docs](https://developer.hashicorp.com/consul/api-docs/agent/service) - Documentação oficial consultada

---

## 🎉 CONCLUSÃO

**TODAS as páginas foram verificadas:**
- ✅ 2 páginas corrigidas (Services, Exporters)
- ✅ 2 páginas já estavam corretas (BlackboxTargets, BlackboxGroups)
- ✅ 3 páginas não têm edição (Nodes, Dashboard, AuditLog)

**O problema de deletar serviços ao editar foi completamente resolvido.**
