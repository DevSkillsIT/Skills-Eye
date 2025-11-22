---
id: SPEC-PERF-002
version: "1.0.0"
status: draft
created: 2025-11-22
updated: 2025-11-22
author: Claude Code
priority: CRITICAL
---

# Criterios de Aceitacao - SPEC-PERF-002

## Visao Geral

Este documento define os criterios de aceitacao detalhados para validar que os problemas de performance do `DynamicMonitoringPage.tsx` foram corrigidos.

---

## Cenarios de Teste - FilterDropdown (AC-001 a AC-004)

### AC-001: FilterDropdown Mantem Estado de Busca

**Dado** que estou em qualquer pagina de monitoramento dinamico
**E** abro o dropdown de filtro de uma coluna
**E** digito "ABC" no campo de busca

**Quando** clico em uma coluna para ordenar
**Ou** navego para outra pagina da tabela
**Ou** altero um filtro em outra coluna

**Entao** o dropdown deve permanecer aberto
**E** o texto "ABC" deve continuar no campo de busca
**E** as opcoes filtradas devem permanecer visiveis

---

### AC-002: FilterDropdown Aplica Filtro Corretamente

**Dado** que estou em qualquer pagina de monitoramento dinamico
**E** abro o dropdown de filtro da coluna "company"
**E** seleciono uma ou mais opcoes

**Quando** clico em "OK"

**Entao** o filtro deve ser aplicado
**E** a tabela deve mostrar apenas registros que correspondem
**E** o icone de filtro deve ficar azul
**E** nao deve haver requisicoes duplicadas

---

### AC-003: FilterDropdown Limpa Filtro Corretamente

**Dado** que tenho um filtro aplicado na coluna "site"
**E** abro o dropdown de filtro dessa coluna

**Quando** clico em "Limpar"

**Entao** todas as selecoes devem ser removidas
**E** o campo de busca deve ser limpo
**E** a tabela deve mostrar todos os registros
**E** o icone de filtro deve voltar a cor padrao

---

### AC-004: FilterDropdown "Selecionar Todos" Funciona

**Dado** que estou no dropdown de filtro
**E** busquei por "prod" (3 resultados visiveis)

**Quando** marco "Selecionar todos"

**Entao** apenas os 3 resultados filtrados devem ser selecionados
**E** outros valores nao visiveis nao devem ser selecionados

---

## Cenarios de Teste - Performance (AC-005 a AC-009)

### AC-005: Re-renders Reduzidos ao Filtrar

**Dado** que estou em qualquer pagina de monitoramento dinamico
**E** React DevTools Profiler esta habilitado

**Quando** aplico um filtro em qualquer coluna

**Entao** o numero de re-renders deve ser <= 3
**E** o componente FilterDropdown nao deve ser remontado
**E** proTableColumns nao deve ser recalculado

---

### AC-006: Re-renders Reduzidos ao Ordenar

**Dado** que estou em qualquer pagina de monitoramento dinamico
**E** React DevTools Profiler esta habilitado

**Quando** clico em uma coluna para ordenar

**Entao** o numero de re-renders deve ser <= 3
**E** proTableColumns nao deve ser recalculado
**E** apenas os dados devem mudar

---

### AC-007: Debounce em Busca Global

**Dado** que estou em qualquer pagina de monitoramento dinamico
**E** Network tab do DevTools esta aberta

**Quando** digito "teste123" rapidamente no campo de busca global (7 caracteres)

**Entao** deve haver apenas 1 requisicao ao backend
**E** a requisicao deve ser feita 300ms apos a ultima tecla
**E** nao deve haver requisicoes intermediarias

---

### AC-008: Debounce em MetadataFilterBar

**Dado** que estou em qualquer pagina de monitoramento dinamico
**E** Network tab do DevTools esta aberta

**Quando** seleciono valores rapidamente em 3 filtros diferentes

**Entao** deve haver no maximo 3 requisicoes (uma por filtro apos debounce)
**E** nao deve haver race conditions nos dados exibidos

---

### AC-009: Tempo de Resposta UI Menor que 100ms

**Dado** que estou em qualquer pagina de monitoramento dinamico

**Quando** interajo com filtros, ordenacao ou paginacao

**Entao** a UI deve responder em menos de 100ms
**E** nao deve haver "travamento" perceptivel
**E** animacoes devem ser fluidas

---

## Cenarios de Teste - Funcionalidades Mantidas (AC-010 a AC-018)

### AC-010: CRUD Completo Funciona

**Dado** que estou em qualquer pagina de monitoramento dinamico

**Quando** executo operacoes de Create, Read, Update e Delete

**Entao** todas as operacoes devem funcionar corretamente
**E** mensagens de sucesso/erro devem aparecer
**E** tabela deve atualizar apos cada operacao

---

### AC-011: Ordenacao em Todas as Colunas

**Dado** que estou em qualquer pagina de monitoramento dinamico

**Quando** clico no cabecalho de qualquer coluna ordenavel

**Entao** a tabela deve ordenar pelos valores dessa coluna
**E** seta de direcao deve aparecer (ascend/descend)
**E** clicar novamente deve inverter a ordem
**E** terceiro clique deve limpar ordenacao

---

### AC-012: Paginacao Funciona

**Dado** que a tabela tem mais de 50 registros

**Quando** navego entre paginas

**Entao** os dados devem mudar corretamente
**E** filtros aplicados devem ser mantidos
**E** ordenacao deve ser mantida
**E** busca deve ser mantida

---

### AC-013: Exportacao CSV

**Dado** que tenho dados na tabela (filtrados ou nao)

**Quando** clico em "Exportar CSV"

**Entao** arquivo CSV deve ser baixado
**E** deve conter os dados visiveis (filtrados)
**E** colunas devem estar corretas

---

### AC-014: Busca Global

**Dado** que a tabela tem dados carregados

**Quando** digito "teste" na busca global

**Entao** apenas registros contendo "teste" devem aparecer
**E** busca deve considerar Service, ID, name, instance, company, site, Node
**E** limpar busca deve mostrar todos os registros

---

### AC-015: Filtros Avancados (AdvancedSearchPanel)

**Dado** que abro o painel de busca avancada

**Quando** configuro condicoes complexas (AND/OR)

**Entao** os resultados devem corresponder as condicoes
**E** indicador de filtro avancado ativo deve aparecer
**E** limpar deve remover todas as condicoes

---

### AC-016: Selecao em Batch

**Dado** que seleciono multiplos registros na tabela

**Quando** clico em "Excluir selecionados"

**Entao** confirmacao deve ser solicitada
**E** todos os registros selecionados devem ser excluidos
**E** tabela deve atualizar

---

### AC-017: Linha Expansivel

**Dado** que clico para expandir uma linha

**Quando** a linha expande

**Entao** metadata completo deve ser exibido
**E** layout deve estar correto
**E** colapsar deve funcionar

---

### AC-018: Modal de Detalhes

**Dado** que clico no icone de detalhes de um registro

**Quando** o modal abre

**Entao** todas as informacoes devem ser exibidas
**E** formatacao deve estar correta
**E** fechar modal deve funcionar

---

## Cenarios de Teste - Compatibilidade (AC-019 a AC-020)

### AC-019: Todas as 8 Paginas Funcionam

**Dado** que as correcoes foram implementadas

**Quando** acesso cada uma das 8 paginas:
- `/monitoring/network-probes`
- `/monitoring/web-probes`
- `/monitoring/system-exporters`
- `/monitoring/database-exporters`
- `/monitoring/infrastructure-exporters`
- `/monitoring/hardware-exporters`
- `/monitoring/network-devices`
- `/monitoring/custom-exporters`

**Entao** todas devem carregar corretamente
**E** todas as funcionalidades devem funcionar
**E** nenhum erro deve aparecer no console

---

### AC-020: NodeSelector Integrado

**Dado** que seleciono um no especifico no NodeSelector

**Quando** a selecao eh aplicada

**Entao** a tabela deve filtrar por esse no
**E** filtros de coluna devem continuar funcionando
**E** mudar de no deve atualizar os dados

---

## Cenarios de Teste - Backend (AC-021 a AC-024)

### AC-021: Testes de Baseline Passam

**Dado** que executo `pytest backend/tests/test_monitoring_unified_baseline.py -v`

**Quando** os testes rodam

**Entao** todos os testes devem passar
**E** cobertura deve ser >= 80%
**E** nenhum warning critico

---

### AC-022: Performance P50 Aceitavel

**Dado** que o teste de performance P50 roda

**Quando** sao feitas 100 requisicoes

**Entao** P50 deve ser < 200ms
**E** resultados devem ser consistentes

---

### AC-023: Performance P95 Aceitavel

**Dado** que o teste de performance P95 roda

**Quando** sao feitas 100 requisicoes

**Entao** P95 deve ser < 500ms
**E** outliers devem ser raros

---

### AC-024: Cache Funciona

**Dado** que faco uma requisicao (cache miss)

**Quando** faco a mesma requisicao novamente

**Entao** cache hit deve ocorrer
**E** tempo de resposta deve ser significativamente menor
**E** dados devem ser identicos

---

## Definition of Done

### Checklist Obrigatorio

- [ ] Todos os cenarios AC-001 a AC-024 passam
- [ ] React DevTools Profiler mostra <= 3 re-renders por interacao
- [ ] Nenhum erro no console do browser
- [ ] Todas as 8 paginas testadas manualmente
- [ ] Testes backend passam com cobertura >= 80%
- [ ] Codigo revisado e sem TODO/FIXME
- [ ] Arquivo `FilterDropdown.tsx` criado e funcional
- [ ] `DynamicMonitoringPage.tsx` refatorado
- [ ] Debounce implementado (300ms)
- [ ] Race conditions eliminadas

### Metricas de Sucesso

| Metrica | Valor Alvo | Como Medir |
|---------|------------|------------|
| Re-renders por interacao | <= 3 | React DevTools Profiler |
| Requisicoes por digitacao rapida | 1 | Network tab |
| Tempo resposta UI | < 100ms | Percepcao + Performance tab |
| Cobertura testes backend | >= 80% | pytest --cov |
| Paginas funcionando | 8/8 | Teste manual |

---

## Metodos de Verificacao

### React DevTools Profiler

1. Instalar extensao React DevTools
2. Abrir aba Profiler
3. Clicar em Record
4. Executar interacao (filtro, sort)
5. Parar gravacao
6. Verificar numero de commits

### Network Tab

1. Abrir DevTools > Network
2. Filtrar por XHR/Fetch
3. Executar interacoes
4. Verificar numero de requisicoes
5. Verificar timing

### Console Errors

1. Abrir DevTools > Console
2. Navegar por todas as paginas
3. Executar todas as funcionalidades
4. Nenhum erro vermelho deve aparecer

### pytest Coverage

```bash
cd backend
pytest tests/test_monitoring_unified_baseline.py -v --cov=api --cov-report=term-missing
```

---

## Notas de Teste

1. **Ambiente**: Testar em dev e staging
2. **Dados**: Usar dataset com pelo menos 100 registros
3. **Browser**: Chrome (React DevTools melhor suporte)
4. **Documentar**: Screenshots de antes/depois no Profiler

---

## Traceability

- **Relacionado a**: SPEC-PERF-001
- **Tags**: acceptance, testing, performance, qa, critical
