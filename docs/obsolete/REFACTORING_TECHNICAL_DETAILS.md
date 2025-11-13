# Refatoração useConsulDelete - Detalhes Técnicos

## Estrutura do Hook useConsulDelete

O hook foi projetado especificamente para operações de DELETE em serviços Consul:

```typescript
export interface ConsulDeletePayload {
  service_id: string;           // ID único (obrigatório)
  service_name?: string;        // Nome do serviço Consul
  node_addr?: string;           // IP do agente
  node_name?: string;           // Nome do node
  datacenter?: string;          // Datacenter
}
```

## Adaptações por Página

Como o hook foi criado para serviços Consul mas é reutilizado em contextos diferentes, foram feitas adaptações:

### 1. ServicePresets.tsx
```typescript
// Hook: deleteFn recebe payload com preset_id
deleteFn: async (payload: any) => consulAPI.deletePreset(payload.preset_id)

// Handler: passa dados da linha específica
const handleDelete = async (presetId: string) => {
  await deleteResource({ preset_id: presetId });
};
```
**Nota**: Usar `{ preset_id: presetId }` em vez de `{ service_id }` pois é um preset, não um serviço.

### 2. ReferenceValues.tsx
```typescript
// Hook: deleteFn recebe payload com value
deleteFn: async (payload: any) => deleteValue(payload.value)

// Handler: passa valor a deletar
const handleDelete = async (value: string) => {
  await deleteResource({ value });
};
```
**Nota**: O valor é o ID único para valores de referência.

### 3. MetadataFields.tsx
```typescript
// Hook: deleteFn recebe payload com field_name e executa DELETE via axios
deleteFn: async (payload: any) => {
  const response = await axios.delete(`${API_URL}/metadata-fields/${payload.field_name}`);
  return response.data;
}

// Handler: passa field_name como service_id (adaptação de tipo)
const handleDelete = async (fieldName: string) => {
  await deleteFieldResource({ service_id: fieldName } as any);
};
```
**Nota**: 
- Renomeado para `deleteFieldResource` para evitar conflito com outras destructurizations
- Usa `{ service_id: fieldName } as any` já que o payload esperado é `ConsulDeletePayload`
- O hook irá tentar usar `payload.field_name`, mas como estamos passando `service_id`, precisamos adaptar o deleteFn

### 4. Settings.tsx
```typescript
// Hook: deleteFn recebe payload com site_code e faz fetch DELETE
deleteFn: async (payload: any) => {
  const response = await fetch(`/api/v1/settings/sites/${payload.site_code}`, {
    method: 'DELETE',
  });
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Erro ao remover site');
  }
  return response.json();
}

// Handler: passa site_code
const handleDelete = async (code: string) => {
  await deleteResource({ service_id: code, site_code: code } as any);
};
```
**Nota**: 
- Passa ambos `service_id` e `site_code` por compatibilidade
- O hook não usa `service_id` se `site_code` estiver no payload

### 5. KvBrowser.tsx
```typescript
// Hook: deleteFn recebe payload com kv_key
deleteFn: async (payload: any) => consulAPI.deleteKV(payload.kv_key)

// Handler: passa key
const handleDelete = async (key: string) => {
  await deleteResource({ service_id: key, kv_key: key } as any);
};
```
**Nota**: Similar ao Settings.tsx, passa ambos os valores para garantir compatibilidade.

## Fluxo de Execução

```
1. User clica botão delete
   ↓
2. handleDelete(id) é chamado
   ↓
3. deleteResource({ ... }) é invocado
   ↓
4. Hook executa deleteFn(payload)
   ↓
5. API DELETE é executada
   ↓
6. Se sucesso → message.success() + onSuccess callback
   Se erro → message.error(detail)
   ↓
7. onSuccess recarrega dados da tabela
```

## Tratamento de Erros

O hook captura e trata erros automaticamente:

```typescript
const detail =
  error?.response?.data?.detail ||
  error?.response?.data?.error ||
  error?.message ||
  'Erro desconhecido';

message.error(`${errorMessage}: ${detail}`);
```

**Prioridade de extração de mensagem**:
1. `error.response.data.detail` (formato FastAPI)
2. `error.response.data.error` (formato alternativo)
3. `error.message` (mensagem genérica)
4. 'Erro desconhecido' (fallback)

## Logging

O hook faz logging automático em console:

```typescript
console.log('[useConsulDelete] Payload enviado:', payload);
console.error('[useConsulDelete] Erro:', error);
```

Útil para debug durante testes.

## Por Que "service_id" em Payload?

O hook usa `service_id` como ID único universal porque:
1. Todos os serviços Consul têm um `service_id` único
2. O hook foi inicialmente projetado para serviços
3. Ao reutilizar em outros contextos, usamos `service_id` como "identificador principal"
4. Cada página específica também passa seu campo específico (preset_id, site_code, etc)

Exemplo:
```typescript
// Para preset
{ service_id: 'node-exporter-linux', preset_id: 'node-exporter-linux' }

// Para site
{ service_id: 'palmas', site_code: 'palmas' }

// Para KV
{ service_id: 'skills/eye/blackbox/targets/1', kv_key: 'skills/eye/blackbox/targets/1' }
```

## Typescript e Type Safety

O hook aceita `ConsulDeletePayload` como tipo esperado:
```typescript
export interface ConsulDeletePayload {
  service_id: string;
  service_name?: string;
  node_addr?: string;
  node_name?: string;
  datacenter?: string;
}
```

Quando usamos em contextos diferentes, usamos `as any` para flexibilidade:
```typescript
await deleteResource({ custom_field: value } as any);
```

**Trade-off**: Perdemos type safety em favor de reutilização. Poderia ser melhorado com:
1. Genéricos: `useConsulDelete<T extends Record<string, any>>`
2. Criação de hooks especializados por tipo
3. Extensão do ConsulDeletePayload para suportar campos customizados

## Callbacks vs Promises

O hook suporta ambos:

```typescript
// Via callback (padrão)
onSuccess: () => {
  tableRef.current?.reload();
  message.success('Recarregado!');
}

// Via promise retornado
const success = await deleteResource(payload);
if (success) {
  console.log('Deletado com sucesso!');
}
```

**Recomendação**: Usar callbacks `onSuccess` para ações automáticas, promises para validações customizadas.

## Otimizações Futuras

1. **Batch Delete**: O hook já suporta `deleteBatch()` para deletar múltiplos items
2. **Cache Invalidation**: Suporta limpeza automática via `clearCacheFn` e `cacheKey`
3. **Undo Operations**: Poderia implementar undo stack
4. **Retry Logic**: Adicionar retry automático para falhas de rede

## Conclusão

O hook `useConsulDelete` é genérico o suficiente para ser reutilizado em múltiplos contextos, com pequenas adaptações por página. O padrão adotado reduz código duplicado, padroniza tratamento de erro e melhora a experiência do desenvolvedor.
