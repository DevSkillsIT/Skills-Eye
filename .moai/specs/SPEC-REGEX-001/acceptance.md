# Critérios de Aceitação - SPEC-REGEX-001

## Visão Geral

Este documento define os critérios de aceitação detalhados para validar a implementação do Global Regex Validator e Match Columns.

---

## Feature 1: Global Regex Validator Modal

### Cenário 1.1: Abrir Modal de Teste

```gherkin
Funcionalidade: Abrir modal de teste de categorização

  Cenário: Acessar modal via botão na toolbar
    DADO que estou na página /settings/monitoring-rules
    E existem regras de categorização carregadas (rulesData não vazio)
    QUANDO clico no botão "Testar Categorização"
    ENTÃO o modal "Testar Categorização Global" é aberto
    E vejo um formulário com campos:
      | Campo        | Tipo   | Obrigatório |
      | Job Name     | Input  | Sim         |
      | Module       | Input  | Não         |
      | Metrics Path | Select | Sim         |
    E o campo Metrics Path tem valor padrão "/metrics"
    E vejo o botão "Analisar Categorização" habilitado
```

### Cenário 1.2: Validação de Campo Obrigatório

```gherkin
  Cenário: Tentar analisar sem Job Name
    DADO que o modal de teste está aberto
    E o campo Job Name está vazio
    QUANDO clico em "Analisar Categorização"
    ENTÃO vejo mensagem de erro "Job Name é obrigatório"
    E nenhuma análise é executada
```

### Cenário 1.3: Testar Job Simples com Match

```gherkin
  Cenário: Testar job node_exporter
    DADO que o modal de teste está aberto
    E existe uma regra com job_name_pattern "^node.*" para categoria "system-exporters"
    QUANDO preencho Job Name com "node_exporter"
    E deixo Module vazio
    E seleciono Metrics Path "/metrics"
    E clico em "Analisar Categorização"
    ENTÃO vejo Alert de sucesso "1 regra(s) fizeram match"
    E vejo a regra que será aplicada destacada com tag "APLICADA"
    E vejo a categoria de destino "system-exporters"
    E vejo tag "job_name_pattern match" na regra
```

### Cenário 1.4: Testar Blackbox com Module

```gherkin
  Cenário: Testar blackbox com módulo http_2xx
    DADO que o modal de teste está aberto
    E existe uma regra com:
      | job_name_pattern | ^blackbox.* |
      | module_pattern   | ^http.*     |
      | metrics_path     | /probe      |
      | categoria        | web-probes  |
    QUANDO preencho Job Name com "blackbox"
    E preencho Module com "http_2xx"
    E seleciono Metrics Path "/probe"
    E clico em "Analisar Categorização"
    ENTÃO vejo Alert de sucesso
    E vejo a categoria de destino "web-probes"
    E vejo tags:
      | Tag                    |
      | job_name_pattern match |
      | module_pattern match   |
      | metrics_path: /probe   |
```

### Cenário 1.5: Nenhuma Regra Aplica

```gherkin
  Cenário: Testar job sem match
    DADO que o modal de teste está aberto
    E não existe regra que faça match com "meu_job_customizado"
    QUANDO preencho Job Name com "meu_job_customizado"
    E seleciono Metrics Path "/metrics"
    E clico em "Analisar Categorização"
    ENTÃO vejo Alert de warning "Nenhuma Regra Aplicou"
    E vejo mensagem informando que cairia em "custom-exporters"
    E vejo sugestão para criar nova regra
```

### Cenário 1.6: Múltiplas Regras com Match

```gherkin
  Cenário: Job faz match com várias regras
    DADO que o modal de teste está aberto
    E existem 3 regras que fazem match com "icmp":
      | Regra    | Prioridade | Categoria      |
      | icmp_100 | 100        | network-probes |
      | icmp_80  | 80         | network-probes |
      | icmp_50  | 50         | custom         |
    QUANDO preencho Job Name com "icmp"
    E seleciono Metrics Path "/probe"
    E clico em "Analisar Categorização"
    ENTÃO vejo Alert "3 regra(s) fizeram match"
    E vejo lista ordenada por prioridade (100, 80, 50)
    E apenas a primeira regra (icmp_100) tem tag "APLICADA"
    E as outras regras aparecem sem destaque
```

### Cenário 1.7: Tooltip com Pattern

```gherkin
  Cenário: Ver detalhes do pattern via tooltip
    DADO que a análise foi executada com sucesso
    E a regra "blackbox_http" fez match
    QUANDO passo o mouse sobre a tag "job_name_pattern match"
    ENTÃO vejo tooltip com "Pattern: ^blackbox.*"
```

### Cenário 1.8: Limpar Formulário

```gherkin
  Cenário: Limpar dados do formulário
    DADO que o modal de teste está aberto
    E foram preenchidos valores nos campos
    E existe resultado de análise anterior
    QUANDO clico no botão "Limpar"
    ENTÃO todos os campos são resetados para valores padrão
    E o resultado da análise anterior é removido
    E vejo mensagem "Preencha os dados e clique em 'Analisar Categorização'"
```

### Cenário 1.9: Fechar Modal

```gherkin
  Cenário: Fechar modal preservando dados da página
    DADO que o modal de teste está aberto
    E foi executada uma análise
    QUANDO clico no botão "Fechar"
    ENTÃO o modal é fechado
    E ao reabrir o modal, os campos estão limpos
    E a tabela de regras na página continua inalterada
```

### Cenário 1.10: Lógica AND dentro da Regra

```gherkin
  Cenário: Regra com múltiplas condições (AND)
    DADO que o modal de teste está aberto
    E existe uma regra "blackbox_icmp" com:
      | Condição         | Valor    |
      | job_name_pattern | ^blackbox |
      | module_pattern   | ^icmp    |
      | metrics_path     | /probe   |
    QUANDO preencho Job Name com "blackbox"
    E preencho Module com "icmp"
    E seleciono Metrics Path "/probe"
    E clico em "Analisar Categorização"
    ENTÃO a regra "blackbox_icmp" faz match
    E todas as 3 condições são satisfeitas (AND lógico)
```

### Cenário 1.11: Falha em Uma Condição

```gherkin
  Cenário: Uma condição falha e regra não aplica
    DADO que o modal de teste está aberto
    E existe uma regra "blackbox_icmp" com:
      | Condição         | Valor    |
      | job_name_pattern | ^blackbox |
      | module_pattern   | ^icmp    |
      | metrics_path     | /probe   |
    QUANDO preencho Job Name com "blackbox"
    E preencho Module com "http_2xx"
    E seleciono Metrics Path "/probe"
    E clico em "Analisar Categorização"
    ENTÃO a regra "blackbox_icmp" NÃO faz match
    E vejo que module_pattern falhou (http_2xx ≠ icmp)
```

### Cenário 1.12: Prioridade entre Regras

```gherkin
  Cenário: Regra de maior prioridade é aplicada
    DADO que o modal de teste está aberto
    E existem regras:
      | Regra         | Prioridade | job_pattern | module_pattern |
      | specific_icmp | 100        | ^blackbox   | ^icmp          |
      | generic_probe | 80         | ^blackbox   | .*             |
    QUANDO preencho Job Name com "blackbox"
    E preencho Module com "icmp"
    E seleciono Metrics Path "/probe"
    E clico em "Analisar Categorização"
    ENTÃO ambas as regras fazem match
    E "specific_icmp" é destacada como APLICADA (prioridade 100)
    E "generic_probe" aparece na lista mas não é aplicada
```

### Cenário 1.13: Regra sem Module Pattern

```gherkin
  Cenário: Regra que não exige module
    DADO que o modal de teste está aberto
    E existe uma regra "node_exporter" com:
      | Condição         | Valor      |
      | job_name_pattern | ^node.*    |
      | metrics_path     | /metrics   |
    E a regra não tem module_pattern
    QUANDO preencho Job Name com "node_exporter"
    E deixo Module vazio
    E seleciono Metrics Path "/metrics"
    E clico em "Analisar Categorização"
    ENTÃO a regra "node_exporter" faz match
    E module_pattern é ignorado (não está na regra)
```

### Cenário 1.14: Metrics Path Incorreto

```gherkin
  Cenário: Metrics Path errado impede match
    DADO que o modal de teste está aberto
    E existe uma regra "blackbox_icmp" com metrics_path "/probe"
    QUANDO preencho Job Name com "blackbox"
    E preencho Module com "icmp"
    E seleciono Metrics Path "/metrics"
    E clico em "Analisar Categorização"
    ENTÃO a regra "blackbox_icmp" NÃO faz match
    E vejo que metrics_path falhou (/metrics ≠ /probe)
```

---

## Feature 2: Match Columns em MonitoringTypes

### Cenário 2.1: Visualizar Novas Colunas

```gherkin
Funcionalidade: Visualizar colunas de match na tabela de tipos

  Cenário: Ver colunas de regra na tabela
    DADO que estou na página /monitoring-types
    E existem tipos de monitoramento carregados
    QUANDO visualizo a tabela
    ENTÃO vejo as colunas:
      | Nome Coluna   | Posição |
      | Regra Job     | 7       |
      | Regra Módulo  | 8       |
    E as colunas aparecem após "Servidores" e antes de "Ações"
```

### Cenário 2.2: Tipo com Match em Job Pattern

```gherkin
  Cenário: Tipo categorizado por job_name_pattern
    DADO que existe um tipo "node_exporter"
    E foi categorizado pela regra "node_exporter_rule"
    E o match foi por job_name_pattern
    QUANDO visualizo a linha deste tipo
    ENTÃO vejo na coluna "Regra Job" a tag "node_exporter_rule" em azul
    E vejo na coluna "Regra Módulo" o texto "-"
```

### Cenário 2.3: Tipo com Match em Module Pattern

```gherkin
  Cenário: Tipo categorizado por module_pattern
    DADO que existe um tipo com módulo "http_2xx"
    E foi categorizado pela regra "blackbox_http"
    E o match foi por module_pattern
    QUANDO visualizo a linha deste tipo
    ENTÃO vejo na coluna "Regra Módulo" a tag "blackbox_http" em verde
```

### Cenário 2.4: Tipo com Match em Ambos Patterns

```gherkin
  Cenário: Tipo com match em job e module
    DADO que existe um tipo "blackbox" com módulo "icmp"
    E foi categorizado pela regra "blackbox_icmp"
    E o match foi por job_name_pattern E module_pattern
    QUANDO visualizo a linha deste tipo
    ENTÃO vejo na coluna "Regra Job" a tag "blackbox_icmp" em azul
    E vejo na coluna "Regra Módulo" a tag "blackbox_icmp" em verde
```

### Cenário 2.5: Tooltip com Detalhes do Match

```gherkin
  Cenário: Ver detalhes do match via tooltip
    DADO que existe um tipo com matched_rule
    QUANDO passo o mouse sobre a tag na coluna "Regra Job"
    ENTÃO vejo tooltip com:
      | Informação | Valor                  |
      | Pattern    | ^node.*                |
      | Prioridade | 80                     |
```

### Cenário 2.6: Tipo Sem Match (Categoria Padrão)

```gherkin
  Cenário: Tipo sem regra aplicada
    DADO que existe um tipo que caiu em "custom-exporters" por padrão
    E não há matched_rule associado
    QUANDO visualizo a linha deste tipo
    ENTÃO vejo na coluna "Regra Job" o texto "-"
    E vejo na coluna "Regra Módulo" o texto "-"
```

### Cenário 2.7: Dados Antigos sem matched_rule

```gherkin
  Cenário: Graceful degradation para dados antigos
    DADO que existe um tipo no cache sem a propriedade matched_rule
    QUANDO visualizo a linha deste tipo
    ENTÃO vejo na coluna "Regra Job" o texto "-"
    E vejo na coluna "Regra Módulo" o texto "-"
    E não há erro no console
```

### Cenário 2.8: Colunas no ColumnSelector

```gherkin
  Cenário: Ocultar/mostrar colunas de match
    DADO que estou na página /monitoring-types
    QUANDO clico no botão de configuração de colunas
    ENTÃO vejo as opções:
      | Coluna        | Visível |
      | Regra Job     | Sim     |
      | Regra Módulo  | Sim     |
    QUANDO desmarco "Regra Job"
    E clico fora do seletor
    ENTÃO a coluna "Regra Job" não aparece na tabela
    E a configuração é salva no localStorage
```

---

## Critérios Técnicos

### CT-001: Performance da Análise

```gherkin
  Cenário: Performance com muitas regras
    DADO que existem 100 regras de categorização
    QUANDO executo uma análise no GlobalRegexValidator
    ENTÃO a análise completa em menos de 100ms
    E não há travamento da interface
```

### CT-002: Consistência de Regex

```gherkin
  Cenário: Regex JavaScript consistente com Python
    DADO que uma regra tem job_name_pattern "^node.*"
    QUANDO testo "node_exporter" no GlobalRegexValidator (JavaScript)
    E testo o mesmo valor no backend (Python)
    ENTÃO ambos retornam match positivo
    E a categorização é a mesma
```

### CT-003: Case Insensitive

```gherkin
  Cenário: Match case insensitive
    DADO que uma regra tem job_name_pattern "^node.*"
    QUANDO testo "NODE_EXPORTER" (maiúsculo)
    ENTÃO o match é positivo
    E a categorização funciona corretamente
```

### CT-004: Tratamento de Regex Inválida

```gherkin
  Cenário: Regra com regex inválida
    DADO que uma regra tem job_name_pattern "[invalid(regex"
    QUANDO executo análise
    ENTÃO a regra inválida é ignorada
    E não há erro na interface
    E outras regras válidas são processadas normalmente
```

---

## Critérios de UX

### UX-001: Helpers e Tooltips

```gherkin
  Cenário: Todos os campos têm ajuda contextual
    DADO que o modal está aberto
    QUANDO visualizo os campos do formulário
    ENTÃO todos os campos têm:
      | Campo        | Helper Text                                      | Tooltip |
      | Job Name     | "Digite o nome do job que deseja testar"         | Sim     |
      | Module       | "Preencha apenas se for blackbox..."             | Sim     |
      | Metrics Path | "Selecione o endpoint de métricas"               | Sim     |
```

### UX-002: Feedback Visual de Loading

```gherkin
  Cenário: Loading durante análise
    DADO que cliquei em "Analisar Categorização"
    E a análise está em progresso
    ENTÃO vejo indicador de loading no botão
    E os campos ficam desabilitados durante a análise
```

### UX-003: Mensagens de Erro Claras

```gherkin
  Cenário: Mensagens de erro compreensíveis
    DADO que ocorreu um erro durante a análise
    QUANDO vejo a mensagem de erro
    ENTÃO a mensagem explica o que aconteceu
    E sugere uma ação para resolver
```

---

## Checklist de Validação Final

### Frontend

- [ ] Botão "Testar Categorização" aparece na toolbar de MonitoringRules
- [ ] Modal abre corretamente com formulário
- [ ] Todos os campos têm helpers e tooltips
- [ ] Análise retorna resultados corretos
- [ ] Regra aplicada é destacada
- [ ] Múltiplas regras são listadas por prioridade
- [ ] Alerta aparece quando nenhuma regra aplica
- [ ] Botão Limpar funciona
- [ ] Modal fecha corretamente
- [ ] Colunas "Regra Job" e "Regra Módulo" aparecem em MonitoringTypes
- [ ] Tags mostram ID da regra
- [ ] Tooltips mostram pattern e prioridade
- [ ] "-" é mostrado quando não há match
- [ ] Colunas aparecem no ColumnSelector
- [ ] LocalStorage salva configuração de colunas

### Backend

- [ ] categorize() retorna matched_rule
- [ ] matched_rule contém todos os campos necessários
- [ ] Tipos extraídos incluem matched_rule
- [ ] Dados antigos não causam erro (graceful degradation)

### Geral

- [ ] Performance aceitável (<100ms para 100 regras)
- [ ] Regex case insensitive funcionando
- [ ] Sem erros no console
- [ ] Acessibilidade básica (navegação por teclado, ARIA labels)
