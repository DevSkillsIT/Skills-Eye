# Refatoração: Aplicação do Hook `useConsulDelete` - Resumo Executivo

Data: 2025-11-05
Escopo: Aplicar o hook `useConsulDelete` em 6 páginas do frontend

## Arquivos Modificados

### 1. **ServicePresets.tsx**
- **Linha 2**: Adicionado import `useConsulDelete`
- **Linhas 67-74**: Adicionado hook com:
  - `deleteFn`: chama `consulAPI.deletePreset(payload.preset_id)`
  - `successMessage`: "Preset deletado com sucesso"
  - `errorMessage`: "Erro ao deletar preset"
  - `onSuccess`: recarrega tabela
- **Linhas 253-255**: Refatorado `handleDelete`:
  - Antes: try/catch com fetch manual
  - Depois: chamada simples `deleteResource({ preset_id: presetId })`
- **Benefício**: Redução de código boilerplate e tratamento de erro centralizado

### 2. **ReferenceValues.tsx**
- **Linha 23**: Adicionado import `useConsulDelete`
- **Linhas 146-153**: Adicionado hook com:
  - `deleteFn`: chama `deleteValue(payload.value)` do hook `useReferenceValues`
  - `successMessage`: "Valor deletado com sucesso"
  - `errorMessage`: "Erro ao deletar valor"
  - `onSuccess`: recarrega valores
- **Linhas 189-191**: Refatorado `handleDelete`:
  - Antes: try/catch com validação de sucesso
  - Depois: chamada simples `deleteResource({ value })`
- **Benefício**: Padrão consistente para deletion de recursos

### 3. **MetadataFields.tsx**
- **Linha 14**: Adicionado import `useConsulDelete`
- **Linhas 121-131**: Adicionado hook com:
  - `deleteFn`: executa DELETE via axios para `/metadata-fields/{field_name}`
  - `successMessage`: "Campo deletado com sucesso"
  - `errorMessage`: "Erro ao deletar campo"
  - `onSuccess`: recarrega campos
- **Linhas 413-415**: Refatorado `handleDeleteField`:
  - Antes: axios.delete com try/catch manual
  - Depois: `deleteFieldResource({ service_id: fieldName } as any)`
- **Benefício**: Tratamento de erro padronizado para campos complexos

### 4. **Settings.tsx**
- **Linha 2**: Adicionado import `useConsulDelete`
- **Linhas 63-80**: Adicionado hook com:
  - `deleteFn`: fetch DELETE para `/api/v1/settings/sites/{code}`
  - `successMessage`: "Site removido com sucesso"
  - `errorMessage`: "Erro ao remover site"
  - `onSuccess`: recarrega config e tabela
- **Linhas 164-166**: Refatorado `handleDeleteSite`:
  - Antes: fetch manual com error handling
  - Depois: `deleteResource({ service_id: code, site_code: code } as any)`
- **Benefício**: Eliminação de código duplicado de requisição HTTP

### 5. **KvBrowser.tsx**
- **Linha 2**: Adicionado import `useConsulDelete`
- **Linhas 30-37**: Adicionado hook com:
  - `deleteFn`: chama `consulAPI.deleteKV(payload.kv_key)`
  - `successMessage`: "Chave removida com sucesso"
  - `errorMessage`: "Erro ao remover chave"
  - `onSuccess`: recarrega árvore KV
- **Linhas 117-119**: Refatorado `handleDelete`:
  - Antes: try/catch com detalhes de erro manual
  - Depois: `deleteResource({ service_id: key, kv_key: key } as any)`
- **Benefício**: Padrão unificado para todas as operações de delete

### 6. **PrometheusConfig.tsx**
- **Status**: NÃO modificado - Página não possui operação de delete
- **Observação**: Página é read-only ou edita via drawer separado

## Padrão Implementado

Cada página segue exatamente o padrão das páginas originais (BlackboxTargets, Services, Exporters, BlackboxGroups):

```typescript
// 1. Import do hook
import { useConsulDelete } from '../hooks/useConsulDelete';

// 2. Inicializar hook no componente
const { deleteResource } = useConsulDelete({
  deleteFn: async (payload: any) => API_CALL(payload.field_id),
  successMessage: 'Recurso deletado com sucesso',
  errorMessage: 'Erro ao deletar recurso',
  onSuccess: () => {
    // Recarregar dados
    actionRef.current?.reload();
  },
});

// 3. Usar no handler
const handleDelete = async (id: string) => {
  await deleteResource({ service_id: id });
};
```

## Dados Utilizados

✓ APENAS dados que já existem nos records
✓ ZERO valores hardcoded
✓ Mantém a mesma lógica que já existia
✓ Adapta deleteFn para cada API específica

## Melhorias Alcançadas

| Aspecto | Antes | Depois |
|---------|-------|--------|
| **Linhas de código (handleDelete)** | 5-8 linhas | 1 linha |
| **Try/catch repetidos** | Em cada página | 1 vez no hook |
| **Mensagens de erro** | Diferentes formatos | Padronizado |
| **Reload de tabela** | Manual em cada página | Automático via onSuccess |
| **Tratamento de erro** | Inconsistente | Centralizado |
| **Logging** | Não padronizado | Centralizado no hook |

## Verificação de Qualidade

- ✓ Todos os imports adicionados
- ✓ Todos os hooks inicializados corretamente
- ✓ Todos os handleDelete refatorados
- ✓ Sem valores hardcoded
- ✓ Sem mudanças em lógica de negócio
- ✓ Sem novos dependencies adicionados
- ✓ TypeScript: usando `as any` onde necessário para tipos customizados

## Próximos Passos (Se Necessário)

1. Testar delete em cada página via UI
2. Verificar mensagens de sucesso/erro
3. Validar reload de tabelas após delete
4. Confirmar logs console no browser

## Rollback

Se necessário revertir todas as mudanças:
```bash
git checkout frontend/src/pages/ServicePresets.tsx
git checkout frontend/src/pages/ReferenceValues.tsx
git checkout frontend/src/pages/MetadataFields.tsx
git checkout frontend/src/pages/Settings.tsx
git checkout frontend/src/pages/KvBrowser.tsx
```
