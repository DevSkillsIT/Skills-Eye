# Criterios de Aceitacao - SPEC-PERF-001

## Visao Geral

Este documento define os criterios de aceitacao detalhados para validar a implementacao das otimizacoes de performance do NodeSelector e endpoint `/api/v1/nodes`.

---

## Feature 1: Reducao de Timeout e Aumento de TTL

### Cenario 1.1: Timeout Reduzido para 2s

```gherkin
Funcionalidade: Timeout de conexao reduzido

  Cenario: No responde dentro do timeout
    DADO que o endpoint /api/v1/nodes eh chamado
    E o cluster tem 3 nos ativos
    QUANDO cada no responde em menos de 2s
    ENTAO todos os nos retornam services_count correto
    E o tempo total eh menor que 3s (paralelo)

  Cenario: No nao responde dentro do timeout
    DADO que o endpoint /api/v1/nodes eh chamado
    E um dos nos esta lento (>2s para responder)
    QUANDO o timeout de 2s eh atingido
    ENTAO o no retorna services_count = 0
    E os demais nos retornam services_count correto
    E nenhum erro eh propagado
    E o tempo total nao excede 2.5s
```

### Cenario 1.2: Cache TTL de 60s

```gherkin
Funcionalidade: Cache com TTL aumentado

  Cenario: Cache hit dentro do TTL
    DADO que uma requisicao foi feita ao /api/v1/nodes
    E os dados foram cacheados
    QUANDO uma nova requisicao eh feita em menos de 60s
    ENTAO os dados sao retornados do cache
    E o tempo de resposta eh menor que 50ms
    E nenhuma conexao ao Consul eh feita

  Cenario: Cache miss apos TTL
    DADO que uma requisicao foi feita ao /api/v1/nodes
    E se passaram mais de 60s
    QUANDO uma nova requisicao eh feita
    ENTAO os dados sao buscados do Consul
    E o cache eh atualizado com TTL de 60s
```

---

## Feature 2: Uso de Catalog API

### Cenario 2.1: Contagem de Servicos via Catalog API

```gherkin
Funcionalidade: Catalog API para contagem de servicos

  Cenario: Contagem de servicos com Catalog API
    DADO que o endpoint /api/v1/nodes eh chamado
    E um no tem 5 servicos registrados (excluindo consul)
    QUANDO a contagem de servicos eh feita via Catalog API
    ENTAO services_count retorna 5
    E o tempo de contagem eh menor que 200ms

  Cenario: Servico consul excluido da contagem
    DADO que um no tem servicos: consul, node_exporter, prometheus
    QUANDO a contagem de servicos eh feita
    ENTAO services_count retorna 2
    E o servico "consul" nao eh contado

  Cenario: No sem servicos
    DADO que um no nao tem servicos registrados
    QUANDO a contagem de servicos eh feita
    ENTAO services_count retorna 0
    E nenhum erro ocorre
```

### Cenario 2.2: Fallback para Erros

```gherkin
Funcionalidade: Fallback robusto

  Cenario: Catalog API falha
    DADO que o endpoint /api/v1/nodes eh chamado
    E a Catalog API falha para um no especifico
    QUANDO o erro eh capturado
    ENTAO services_count retorna 0 para este no
    E os demais nos retornam contagem correta
    E a resposta da API eh sucesso (success: true)

  Cenario: No nao existe no Consul
    DADO que o endpoint /api/v1/nodes eh chamado
    E um no listado nao existe mais no Consul
    QUANDO a Catalog API retorna 404
    ENTAO services_count retorna 0
    E nenhum erro eh propagado
```

---

## Feature 3: Memoizacao do NodesContext

### Cenario 3.1: Context Value Memoizado

```gherkin
Funcionalidade: Memoizacao do context value

  Cenario: Sem re-render ao navegar
    DADO que o usuario esta em /monitoring/network-probes
    E o NodeSelector esta renderizado
    QUANDO o usuario navega para /monitoring/web-probes
    ENTAO o NodesContext nao re-renderiza seus consumers
    E o NodeSelector mantem seu estado

  Cenario: Re-render apenas quando dados mudam
    DADO que o NodesContext esta carregado
    E nodes = [{addr: "1.1.1.1", ...}]
    QUANDO reload() eh chamado
    E os dados retornados sao diferentes
    ENTAO o context value eh recriado
    E os consumers sao re-renderizados

  Cenario: Sem re-render quando dados sao iguais
    DADO que o NodesContext esta carregado
    QUANDO reload() eh chamado
    E os dados retornados sao identicos
    ENTAO o context value NAO eh recriado
    E os consumers NAO re-renderizam
```

### Cenario 3.2: useCallback para reload

```gherkin
Funcionalidade: reload memoizado

  Cenario: reload mantem referencia estavel
    DADO que o componente usa useNodesContext()
    E acessa a funcao reload
    QUANDO o parent re-renderiza
    ENTAO a referencia de reload nao muda
    E o useEffect do consumer nao re-executa
```

---

## Feature 4: Otimizacao do NodeSelector

### Cenario 4.1: Remocao de onChange das Dependencias

```gherkin
Funcionalidade: useEffect sem onChange nas deps

  Cenario: useEffect nao re-executa com novo onChange
    DADO que o NodeSelector esta renderizado
    E selectedNode = "1.1.1.1"
    QUANDO o parent re-renderiza (criando novo onChange)
    ENTAO o useEffect de selecao automatica NAO re-executa
    E selectedNode permanece "1.1.1.1"

  Cenario: useEffect executa quando nodes mudam
    DADO que o NodeSelector esta renderizado
    E nodes esta vazio
    QUANDO nodes carrega com dados
    ENTAO o useEffect de selecao automatica executa
    E seleciona o mainServer automaticamente
```

### Cenario 4.2: CSS Classes (Opcional)

```gherkin
Funcionalidade: Estilos via CSS classes

  Cenario: Estilos aplicados corretamente
    DADO que o NodeSelector esta renderizado
    QUANDO visualizo as opcoes do dropdown
    ENTAO cada opcao tem a classe "node-option"
    E o endereco tem a classe "node-option-addr"
    E os estilos sao identicos aos inline styles anteriores
```

---

## Criterios de Performance

### CP-001: Tempo de Resposta do Backend

```gherkin
Funcionalidade: Performance do endpoint /api/v1/nodes

  Cenario: Cache miss com 3 nos
    DADO que o cache esta vazio
    E o cluster tem 3 nos
    QUANDO o endpoint /api/v1/nodes eh chamado
    ENTAO o tempo de resposta eh menor que 600ms
    E P50 eh menor que 200ms
    E P95 eh menor que 500ms

  Cenario: Cache hit
    DADO que o cache esta populado
    QUANDO o endpoint /api/v1/nodes eh chamado
    ENTAO o tempo de resposta eh menor que 50ms
```

### CP-002: Re-renders do Frontend

```gherkin
Funcionalidade: Reducao de re-renders

  Cenario: Mudanca de no selecionado
    DADO que o NodeSelector esta renderizado
    E o React DevTools Profiler esta ativo
    QUANDO o usuario muda o no selecionado
    ENTAO o NodeSelector re-renderiza 1-2 vezes
    E NAO re-renderiza 10+ vezes

  Cenario: Navegacao entre paginas
    DADO que o usuario esta em /monitoring/network-probes
    QUANDO navega para /monitoring/web-probes
    ENTAO o NodeSelector re-renderiza no maximo 1 vez
    E o NodesContext NAO re-renderiza
```

---

## Criterios de Compatibilidade

### CC-001: Paginas de Monitoramento

```gherkin
Funcionalidade: Compatibilidade com 8 paginas

  Cenario Outline: Pagina funciona corretamente
    DADO que acesso a pagina <pagina>
    E o NodeSelector esta visivel
    QUANDO seleciono um no diferente
    ENTAO os dados sao carregados para o no selecionado
    E nenhum erro aparece no console
    E a pagina funciona normalmente

    Exemplos:
      | pagina                              |
      | /monitoring/network-probes          |
      | /monitoring/web-probes              |
      | /monitoring/system-exporters        |
      | /monitoring/database-exporters      |
      | /monitoring/infrastructure-exporters|
      | /monitoring/hardware-exporters      |
      | /monitoring/network-devices         |
      | /monitoring/custom-exporters        |
```

### CC-002: Contrato de API

```gherkin
Funcionalidade: Contrato de API mantido

  Cenario: Estrutura de resposta
    DADO que o endpoint /api/v1/nodes eh chamado
    QUANDO a resposta eh retornada
    ENTAO a estrutura eh:
      | Campo       | Tipo     | Obrigatorio |
      | success     | boolean  | Sim         |
      | data        | array    | Sim         |
      | total       | number   | Sim         |
      | main_server | string   | Sim         |
    E cada item em data tem:
      | Campo          | Tipo   | Obrigatorio |
      | name           | string | Sim         |
      | addr           | string | Sim         |
      | port           | number | Sim         |
      | status         | number | Sim         |
      | services_count | number | Sim         |
      | site_name      | string | Sim         |
```

---

## Criterios Tecnicos

### CT-001: Memoizacao Correta

```gherkin
Funcionalidade: useMemo e useCallback corretos

  Cenario: Dependencies array correto
    DADO que NodesContext usa useMemo para contextValue
    QUANDO inspeciono o codigo
    ENTAO as dependencias sao [nodes, mainServer, loading, error, reload]
    E nao inclui funcoes nao memoizadas

  Cenario: useCallback para reload
    DADO que NodesContext define reload
    QUANDO inspeciono o codigo
    ENTAO reload usa useCallback
    E dependencias sao array vazio []
```

### CT-002: Catalog API Implementada

```gherkin
Funcionalidade: ConsulManager com Catalog API

  Cenario: Metodo get_node_services existe
    DADO que inspeciono ConsulManager
    QUANDO procuro o metodo get_node_services
    ENTAO o metodo existe
    E aceita node_name como parametro
    E retorna dict com Node e Services

  Cenario: Endpoint correto
    DADO que get_node_services eh chamado
    QUANDO a requisicao eh feita
    ENTAO o endpoint eh /v1/catalog/node/{node_name}
    E o metodo HTTP eh GET
```

---

## Checklist de Validacao Final

### Backend
- [ ] Timeout reduzido de 5s para 2s
- [ ] TTL aumentado de 30s para 60s
- [ ] Catalog API implementada e em uso
- [ ] Fallback para services_count = 0 funcionando
- [ ] Contrato de API mantido
- [ ] Sem erros nos logs

### Frontend
- [ ] Context value memoizado com useMemo
- [ ] reload memoizado com useCallback
- [ ] onChange removido das dependencias do useEffect
- [ ] Re-renders reduzidos para 1-2
- [ ] Todas as 8 paginas funcionando

### Performance
- [ ] Tempo de resposta (cache miss) < 600ms
- [ ] Tempo de resposta (cache hit) < 50ms
- [ ] Re-renders por mudanca de no: 1-2
- [ ] Cache hits > 80%

### Geral
- [ ] Testes manuais passando em todas as paginas
- [ ] Nenhum erro no console do browser
- [ ] Metricas coletadas antes e depois
- [ ] Documentacao atualizada se necessario

---

## Metricas de Aceitacao

| Metrica | Valor Minimo Aceitavel | Valor Ideal |
|---------|------------------------|-------------|
| Tempo resposta (cache miss) | < 800ms | < 600ms |
| Tempo resposta (cache hit) | < 100ms | < 50ms |
| Re-renders por mudanca | < 5 | 1-2 |
| Reducao tempo total | > 50% | > 75% |
| Taxa cache hits | > 70% | > 80% |

---

## Testes de Regressao

### Funcionalidades que NAO devem quebrar:

1. **Selecao automatica do mainServer** ao carregar pagina
2. **Opcao "Todos os nos"** quando habilitada
3. **Badge Master/Slave** nos nos
4. **site_name** mapeado corretamente
5. **Loading state** durante carregamento
6. **Mensagem de erro** quando Consul falha
7. **Reload manual** via contexto
8. **Persistencia de selecao** ao navegar

---

## Criterios de Rollback

O rollback deve ser executado se:

1. Tempo de resposta > 1000ms (pior que antes)
2. Erros em mais de 1 das 8 paginas
3. services_count sempre 0 (Catalog API falhando)
4. Re-renders aumentaram (>15 por mudanca)
5. Cache hit rate < 50% (antes era ~50%)
