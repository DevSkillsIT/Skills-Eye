# Correções Urgentes - Erros de Importação e Variáveis

## Resumo

Corrigi 3 erros críticos que impediam as páginas de abrir.

---

## ✅ 1. Services - Erro "CloudOutlined is not defined"

### Problema
```
Something went wrong.
CloudOutlined is not defined
```

### Causa
O ícone `CloudOutlined` foi usado no código mas não estava importado.

### Solução
Adicionado import do ícone:

**Arquivo:** `frontend/src/pages/Services.tsx` (linha 25)

```typescript
import {
  ClearOutlined,
  CloudOutlined,  // ✅ ADICIONADO
  DeleteOutlined,
  DownloadOutlined,
  EditOutlined,
  FilterOutlined,
  InfoCircleOutlined,
  PlusOutlined,
  ReloadOutlined,
} from '@ant-design/icons';
```

---

## ✅ 2. Services - Erro "advancedLogicalOperator is not defined"

### Problema
```
Something went wrong.
advancedLogicalOperator is not defined
```

### Causa
Uso de nome de variável incorreto no AdvancedSearchPanel.

- **Nome correto:** `advancedOperator`
- **Nome usado:** `advancedLogicalOperator`

### Solução
Corrigido nome da variável:

**Arquivo:** `frontend/src/pages/Services.tsx` (linha 1026)

```typescript
{advancedOpen && (
  <AdvancedSearchPanel
    availableFields={advancedSearchFields}
    onSearch={handleAdvancedSearch}
    onClear={handleAdvancedClear}
    initialConditions={advancedConditions}
    initialLogicalOperator={advancedOperator}  // ✅ CORRIGIDO
  />
)}
```

---

## ✅ 3. BlackboxTargets - Erro "advancedLogicalOperator is not defined"

### Problema
Mesmo erro da página Services.

### Causa
Mesmo problema: nome de variável incorreto.

### Solução
Corrigido nome da variável:

**Arquivo:** `frontend/src/pages/BlackboxTargets.tsx` (linha 953)

```typescript
{advancedOpen && (
  <AdvancedSearchPanel
    availableFields={advancedSearchFields}
    onSearch={handleAdvancedSearch}
    onClear={handleAdvancedClear}
    initialConditions={advancedConditions}
    initialLogicalOperator={advancedOperator}  // ✅ CORRIGIDO
  />
)}
```

---

## 🔍 4. Exporters - Debug do Problema de Resultados Vazios

### Problema
Página continua mostrando "Nenhum exporter disponível".

### Ação Tomada
**DESABILITEI COMPLETAMENTE O FILTRO** temporariamente para debug.

**Arquivo:** `frontend/src/pages/Exporters.tsx` (linhas 151-173)

```typescript
// TEMPORÁRIO: DESABILITADO O FILTRO - RETORNA TUDO EXCETO CONSUL
// Para debug do problema de resultados vazios
const filterOnlyExporters = useCallback((services: any[]): any[] => {
  console.log('[Exporters] filterOnlyExporters - INPUT:', services);

  const filtered = services.filter((s: any) => {
    const serviceName = String(s?.service || '').toLowerCase();

    // Só excluir consul
    if (serviceName === 'consul') {
      console.log('[Exporters] Excluindo consul');
      return false;
    }

    // TEMPORÁRIO: Incluir TUDO o resto
    console.log('[Exporters] Incluindo serviço:', serviceName);
    return true;
  });

  console.log('[Exporters] filterOnlyExporters - OUTPUT:', filtered);
  return filtered;
}, []);
```

### Logs de Debug Adicionados

Agora o console mostra:
1. `[Exporters] Query params` - Parâmetros da query
2. `[Exporters] API Response` - Resposta da API
3. `[Exporters] Payload` - Dados retornados
4. `[Exporters] Payload.data` - Dados dentro de data
5. `[Exporters] Mode: ALL nodes / Single node` - Modo de operação
6. `[Exporters] Total rows before filter` - Quantidade antes do filtro
7. `[Exporters] All services` - Lista completa de serviços
8. `[Exporters] filterOnlyExporters - INPUT` - Entrada do filtro
9. `[Exporters] Incluindo serviço: XXX` - Cada serviço incluído
10. `[Exporters] filterOnlyExporters - OUTPUT` - Saída do filtro
11. `[Exporters] Total rows after exporter filter` - Quantidade depois do filtro

### Como Testar

1. Abra a página `/exporters`
2. Abra o Console do Navegador (F12 → Console)
3. **Copie TODOS os logs** que começam com `[Exporters]`
4. Me envie os logs

Com esses logs vou descobrir:
- ✅ Se a API está retornando dados
- ✅ Se os dados estão na estrutura correta
- ✅ Se o problema é no filtro ou no backend
- ✅ Quantos serviços existem no Consul
- ✅ Por que o filtro original estava excluindo tudo

---

## Status Atual

| Página | Status | Observação |
|--------|--------|------------|
| Services | ✅ CORRIGIDO | CloudOutlined e advancedOperator |
| BlackboxTargets | ✅ CORRIGIDO | advancedOperator |
| Exporters | 🔍 DEBUG | Filtro desabilitado, aguardando logs |
| Hosts | ✅ OK | Funcionando normalmente |

---

## Próximos Passos

1. ✅ Testar páginas Services e BlackboxTargets
2. 🔍 Testar página Exporters e copiar logs do console
3. 📊 Analisar logs para identificar causa raiz
4. ✅ Reabilitar filtro correto após identificar problema

---

## Arquivos Modificados

1. ✅ `frontend/src/pages/Services.tsx`
   - Linha 25: Adicionado import `CloudOutlined`
   - Linha 1026: Corrigido `advancedOperator`

2. ✅ `frontend/src/pages/BlackboxTargets.tsx`
   - Linha 953: Corrigido `advancedOperator`

3. 🔍 `frontend/src/pages/Exporters.tsx`
   - Linhas 151-173: Filtro desabilitado temporariamente
   - Múltiplos console.log adicionados para debug
