# Critérios de Aceite - SPEC-PERF-002-FIX

## Metadata

| Campo | Valor |
|-------|-------|
| SPEC | SPEC-PERF-002-FIX |
| Status | PENDENTE |
| Total de Cenários | 18 |

---

## REQ-001: Busca Textual Backend

### AC-001.1: Parâmetro q Enviado ao Backend

**Given** que o usuário está na página de monitoramento dinâmico
**And** existem 500 registros no banco de dados
**When** o usuário digita "Servidor-X" na caixa de busca
**Then** o frontend deve enviar o parâmetro `q=Servidor-X` na requisição
**And** a requisição deve incluir `q` nos query parameters
**And** o DevTools deve mostrar a URL com `?...&q=Servidor-X`

### AC-001.2: Busca Funciona em Todo Dataset

**Given** que existe um registro "Servidor-Producao-001" na página 10 do banco
**And** o usuário está visualizando a página 1
**When** o usuário busca por "Producao-001"
**Then** o sistema deve retornar o registro encontrado
**And** a contagem total deve refletir apenas resultados que batem
**And** o registro NÃO deve estar filtrado localmente

### AC-001.3: Busca Local Removida

**Given** que o código fonte foi atualizado
**When** inspeciono `DynamicMonitoringPage.tsx` linhas 956-972
**Then** o bloco de busca local deve estar REMOVIDO
**And** não deve haver referência a `searchValue.trim().toLowerCase()` para filtro
**And** o processamento deve confiar no retorno do backend

### AC-001.4: api.ts Mapeia Parâmetro Corretamente

**Given** que o código fonte foi atualizado
**When** inspeciono `api.ts` função `getMonitoringData`
**Then** deve existir a linha `if (options.q || options.search_query)`
**And** deve existir `params.q = options.q || options.search_query`

---

## REQ-002: Cache Intermediário Integrado

### AC-002.1: Cache Stats Funcional

**Given** que o cache `monitoring_data_cache` está integrado
**When** faço várias requisições para o mesmo `category`
**And** consulto `/monitoring/cache/stats`
**Then** os contadores de `hits` e `misses` devem estar incrementados
**And** os valores NÃO devem ser zero

### AC-002.2: Cache Invalidate Funcional

**Given** que há dados em cache para category "services"
**When** faço POST para `/monitoring/cache/invalidate` com `category=services`
**Then** a próxima requisição deve buscar dados frescos do backend
**And** o contador de `misses` deve incrementar
**And** a resposta deve confirmar invalidação

### AC-002.3: Código Usa monitoring_data_cache

**Given** que o código fonte foi atualizado
**When** inspeciono `monitoring_unified.py` linha 423-450
**Then** NÃO deve haver chamada para `get_services_cached`
**And** deve haver chamada para `monitoring_data_cache.get_data(category)`
**And** deve haver chamada para `monitoring_data_cache.set_data(category, data)`

---

## REQ-003: Ordenação Sem Conversão

### AC-003.1: Sort Order Enviado Diretamente

**Given** que o usuário clica na coluna "Service" para ordenar
**When** a requisição é enviada ao backend
**Then** o parâmetro `sort_order` deve ser `ascend` ou `descend`
**And** NÃO deve ser `asc` ou `desc`
**And** o DevTools deve mostrar o valor correto na URL

### AC-003.2: Código Sem Conversão

**Given** que o código fonte foi atualizado
**When** inspeciono `api.ts` função `getMonitoringData`
**Then** a linha deve ser `params.sort_order = options.sort_order`
**And** NÃO deve haver ternário `=== 'ascend' ? 'asc' : 'desc'`

---

## REQ-004: Filtros Sem Duplo Disparo

### AC-004.1: Uma Requisição Por Filtro

**Given** que o usuário está na página de monitoramento
**And** o DevTools Network está aberto
**When** o usuário seleciona um valor no MetadataFilterBar
**Then** deve haver APENAS UMA requisição ao backend
**And** essa requisição deve ocorrer após 300ms de debounce
**And** NÃO deve haver duas requisições consecutivas

### AC-004.2: onChange Sem Reload Direto

**Given** que o código fonte foi atualizado
**When** inspeciono MetadataFilterBar onChange (~linha 1374)
**Then** NÃO deve haver `actionRef.current?.reload()` no callback
**And** deve haver apenas `setFilters(newFilters)`

### AC-004.3: useEffect Usa Debounce

**Given** que o código fonte foi atualizado
**When** inspeciono useEffect de filters (~linha 1104-1115)
**Then** deve haver chamada para `debouncedReload()`
**And** NÃO deve haver `actionRef.current?.reload()` direto
**And** `debouncedReload` deve estar nas dependências

---

## REQ-005: Dropdown de Filtros Funcional

### AC-005.1: Estado de Busca Persiste

**Given** que o usuário abriu o dropdown de filtro da coluna "Service"
**And** digitou "Agro" no campo de busca
**When** o usuário clica em ordenar outra coluna (causando re-render)
**Then** ao reabrir o dropdown da coluna "Service"
**And** o campo de busca deve conter "Agro"
**And** NÃO deve estar vazio

### AC-005.2: Ref de Estado Criado

**Given** que o código fonte foi atualizado
**When** inspeciono `DynamicMonitoringPage.tsx` início do componente
**Then** deve existir `const filterSearchTextRef = useRef<Record<string, string>>({})`
**And** o filterDropdown deve usar `filterSearchTextRef.current[colConfig.key]`

### AC-005.3: Múltipla Seleção Funciona

**Given** que o dropdown de filtro tem 10 opções
**And** o usuário clica em "Selecionar todos"
**When** o filtro é aplicado
**Then** TODOS os 10 valores devem ser enviados ao backend
**And** o parâmetro deve ser `coluna=valor1,valor2,valor3,...,valor10`
**And** NÃO deve ser apenas `coluna=valor1`

### AC-005.4: Código Join Implementado

**Given** que o código fonte foi atualizado
**When** inspeciono lógica de seleção (~linha 601-615)
**Then** deve existir `newFilters[colConfig.key] = selectedKeys.join(',')`
**And** NÃO deve haver `selectedKeys[0]` sozinho

---

## REQ-006: Debounce Cancela Requests

### AC-006.1: Request Anterior Cancelada

**Given** que o usuário digita rapidamente "abc" (letra por letra)
**And** o DevTools Network está aberto
**When** observo as requisições
**Then** as requisições de "a" e "ab" devem aparecer como `(canceled)`
**And** apenas a requisição de "abc" deve completar com status 200

### AC-006.2: Console Log de Cancelamento

**Given** que o usuário digita rapidamente
**When** observo o console do browser
**Then** deve aparecer `[DynamicMonitoringPage] Request anterior cancelada`
**And** a mensagem deve aparecer para cada request cancelada

### AC-006.3: Código Abort Implementado

**Given** que o código fonte foi atualizado
**When** inspeciono `debouncedReload` (~linha 318-320)
**Then** deve haver verificação `if (abortControllerRef.current)`
**And** deve haver chamada `abortControllerRef.current.abort()`
**And** deve haver `console.log` de cancelamento

---

## Quality Gate

### QG-001: Testes de Integração

**Given** que todas as correções foram implementadas
**When** executo a suite de testes
**Then** todos os testes existentes devem passar
**And** não deve haver regressões

### QG-002: Performance

**Given** que o cache está integrado
**When** faço 10 requisições consecutivas para o mesmo category
**Then** o tempo médio de resposta deve ser < 100ms após primeiro hit
**And** o cache stats deve mostrar 1 miss e 9 hits

### QG-003: UX Consistente

**Given** que todas as correções foram implementadas
**When** navego pela página de monitoramento por 5 minutos
**Then** não deve haver:
- Duplo loading indicator
- Flicker de dados
- Reset de estado não esperado
- Resultados parciais mostrados como completos

---

## Definition of Done

- [ ] Todos os 18 cenários de aceite passam
- [ ] Código revisado e sem TODOs
- [ ] Console sem warnings/errors
- [ ] DevTools Network mostra requisições corretas
- [ ] Cache stats mostra hits/misses reais
- [ ] Busca funciona em todo dataset
- [ ] Filtros disparam apenas 1 request
- [ ] Dropdown mantém estado

---

## TAGs de Rastreabilidade

<!-- TAG: SPEC-PERF-002-FIX -->
<!-- TAG: ACCEPTANCE-PERF-002-FIX -->

---

*Critérios de aceite criados em 2025-11-22 baseado no documento de consolidação final*
