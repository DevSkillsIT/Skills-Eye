# 🔧 Correção: Filtro "Servidor Específico" em Monitoring Types

**Data:** 2025-11-18  
**Problema:** Filtro por "Servidor Específico" não funcionava mais

## 🐛 Problema Identificado

O backend retorna todos os dados do cache KV sem filtrar por servidor (comentário diz "frontend faz o filtro"), mas o frontend não estava implementando esse filtro quando `viewMode === 'specific'`.

### Código Problemático

**Backend** (`monitoring_types_dynamic.py:607-619`):
```python
# Retornar dados do cache (sem filtrar - frontend faz o filtro)
return {
    "success": True,
    "from_cache": True,
    "categories": kv_data.get('categories', []),  # ← TODOS os tipos
    "all_types": kv_data.get('all_types', []),    # ← TODOS os tipos
    "servers": kv_data.get('servers', {}),
    ...
}
```

**Frontend** (`MonitoringTypes.tsx:155-159`):
```typescript
if (response.data.success) {
  setCategories(response.data.categories || []);  // ← Sem filtro!
  setServerData(response.data.servers || {});
  setTotalTypes(response.data.total_types || 0);
  ...
}
```

## ✅ Solução Implementada

Adicionado filtro no frontend quando `viewMode === 'specific'` e `selectedServerInfo` está definido.

### Código Corrigido

```typescript
if (response.data.success) {
  // ✅ CORREÇÃO: Filtrar por servidor quando viewMode === 'specific'
  let categoriesData = response.data.categories || [];
  let serverDataResult = response.data.servers || {};
  
  // Se modo específico e servidor selecionado, filtrar dados
  if (viewMode === 'specific' && selectedServerInfo?.hostname) {
    const serverHostname = selectedServerInfo.hostname;
    
    // Filtrar categorias para mostrar apenas tipos do servidor selecionado
    categoriesData = categoriesData.map((category: CategoryData) => ({
      ...category,
      types: category.types.filter((type: MonitoringType) => {
        // Verificar se o tipo pertence ao servidor selecionado
        // Tipos podem ter 'server' (string) ou 'servers' (array)
        if (type.server === serverHostname) return true;
        if (type.servers && Array.isArray(type.servers)) {
          return type.servers.includes(serverHostname);
        }
        // Se não tem server/servers, verificar se está no serverData do servidor
        if (serverDataResult[serverHostname]) {
          return serverDataResult[serverHostname].types?.some(
            (serverType: MonitoringType) => serverType.id === type.id
          );
        }
        return false;
      })
    })).filter((category: CategoryData) => category.types.length > 0); // Remover categorias vazias
    
    // Atualizar totalTypes para refletir apenas o servidor selecionado
    const filteredTotal = categoriesData.reduce(
      (sum: number, cat: CategoryData) => sum + cat.types.length,
      0
    );
    setTotalTypes(filteredTotal);
  } else {
    setTotalTypes(response.data.total_types || 0);
  }
  
  setCategories(categoriesData);
  setServerData(serverDataResult);
  setTotalServers(response.data.total_servers || 0);
  ...
}
```

## 🔍 Como Funciona

1. **Modo "Todos os Servidores"** (`viewMode === 'all'`):
   - Mostra todos os tipos de todos os servidores
   - Sem filtro aplicado

2. **Modo "Servidor Específico"** (`viewMode === 'specific'`):
   - Filtra tipos que pertencem ao servidor selecionado
   - Verifica três condições:
     - `type.server === serverHostname` (tipo tem servidor único)
     - `type.servers.includes(serverHostname)` (tipo está em array de servidores)
     - Tipo existe em `serverData[serverHostname].types` (fallback)
   - Remove categorias vazias após filtro
   - Atualiza `totalTypes` para refletir apenas o servidor selecionado

## ✅ Teste

1. Acesse `http://localhost:8081/monitoring-types`
2. Clique em "Servidor Específico"
3. Selecione um servidor no dropdown
4. Verifique que apenas os tipos daquele servidor são exibidos
5. Verifique que o contador de tipos reflete apenas o servidor selecionado

## 📝 Notas

- O filtro funciona tanto para dados do cache quanto para dados recém-extraídos
- O backend continua retornando todos os dados (otimização: evita múltiplas requisições)
- O frontend faz o filtro client-side (rápido, não impacta performance)

