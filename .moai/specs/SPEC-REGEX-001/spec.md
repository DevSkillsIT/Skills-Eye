---
id: SPEC-REGEX-001
version: "1.0.0"
status: draft
created: 2025-11-21
updated: 2025-11-21
author: Alfred SuperAgent
priority: HIGH
---

# HISTORY

| Versão | Data       | Autor            | Descrição                                      |
|--------|------------|------------------|------------------------------------------------|
| 1.0.0  | 2025-11-21 | Alfred SuperAgent | Versão inicial do SPEC                        |

---

# SPEC-REGEX-001: Global Regex Validator e Match Columns para Regras de Categorização

## Resumo Executivo

Este SPEC define a implementação de duas features complementares para melhorar a experiência do usuário no sistema de categorização de tipos de monitoramento:

1. **Global Regex Validator** - Modal na página MonitoringRules que permite testar se um job_name ou module cairia em qual categoria/regra
2. **Match Columns** - Duas novas colunas na tabela MonitoringTypes mostrando qual regra foi usada para categorizar cada tipo

## Contexto e Motivação

### Como Funciona a Lógica de Categorização

**IMPORTANTE**: O sistema usa lógica **AND dentro de cada regra** e **prioridade entre regras**:

1. **Cada regra pode ter múltiplas condições** (job_name_pattern, module_pattern, metrics_path)
2. **TODAS as condições de uma regra precisam bater** para ela ser aplicada
3. **A primeira regra por prioridade** que fizer match completo é a que vale
4. **Apenas UMA regra é aplicada** - nunca cai em duas regras diferentes

**Exemplo de Fluxo**:
```
Regra 1 (prioridade 100): job=^blackbox, module=^icmp, path=/probe → network-probes
Regra 2 (prioridade 90): job=^blackbox, module=^http, path=/probe → web-probes
Regra 3 (prioridade 80): job=^blackbox, path=/probe → web-probes (fallback)

Teste: Job "blackbox" + module "icmp" + path "/probe":
- Regra 1: job OK, module OK, path OK → APLICA (prioridade 100)
- Regras 2 e 3 não são testadas porque Regra 1 já aplicou

Teste: Job "blackbox" + module "tcp_connect" + path "/probe":
- Regra 1: job OK, module FALHA (tcp_connect ≠ icmp) → NÃO APLICA
- Regra 2: job OK, module FALHA (tcp_connect ≠ http) → NÃO APLICA
- Regra 3: job OK, path OK → APLICA (prioridade 80)
```

**Por que Metrics Path é necessário?**
- `/probe` = blackbox exporter (testes remotos)
- `/metrics` = exporters tradicionais (node, postgres, etc)
- Muitas regras usam isso como condição diferenciadora

### Situação Atual:
- A validação de regex existe apenas dentro do modal de criar/editar regra (para cada regra individual)
- Não há forma de testar "dado este job_name e module, em qual categoria ele cairia?"
- A tabela de MonitoringTypes não mostra qual regra foi responsável pela categorização

Problemas:
- Usuários não conseguem prever comportamento antes de criar regras
- Debugging de categorização incorreta é difícil
- Falta visibilidade sobre qual regra causou determinada categorização

---

## Functional Requirements (MUST)

### FR-001: Global Regex Validator Modal
**EARS Format**: O sistema **DEVE** fornecer um botão "Testar Categorização" na toolbar da página MonitoringRules que abre um modal para teste global de regras.

**Detalhes**:
- Botão na toolbar com ícone `ExperimentOutlined` e texto "Testar Categorização"
- Modal com formulário contendo:
  - Input para Job Name (obrigatório)
  - Input para Module (opcional)
  - Select para Metrics Path ('/probe' ou '/metrics')
- Botão "Analisar Categorização" para executar teste

### FR-002: Resultado da Análise
**EARS Format**: QUANDO o usuário clicar em "Analisar Categorização", O sistema **DEVE** mostrar todas as regras que fariam match com os valores informados.

**Detalhes**:
- Lista de regras que fariam match, ordenadas por prioridade (maior primeiro)
- Para cada regra mostrar:
  - ID da regra
  - Prioridade
  - Categoria de destino
  - Display Name
  - Qual pattern fez match (job_name_pattern e/ou module_pattern)
- Destacar a regra que seria aplicada (primeira da lista por prioridade)
- Se nenhuma regra aplicar, mostrar Alert informando que cairia em "custom-exporters"

### FR-003: Match Columns em MonitoringTypes
**EARS Format**: O sistema **DEVE** exibir duas novas colunas na tabela de MonitoringTypes: "Regra Job" e "Regra Módulo".

**Detalhes**:
- Coluna "Regra Job": mostra ID da regra cujo job_name_pattern fez match
- Coluna "Regra Módulo": mostra ID da regra cujo module_pattern fez match
- Mostrar "-" se não houve match para aquele pattern específico
- Tooltip em cada célula com:
  - Pattern que fez match
  - Prioridade da regra

### FR-004: Atualização do Backend
**EARS Format**: O sistema **DEVE** retornar informações sobre qual regra foi usada na categorização de cada tipo.

**Detalhes**:
- Modificar retorno de `extract_types_from_prometheus_jobs`
- Incluir `matched_rule` com:
  - `id`: ID da regra
  - `job_pattern_matched`: boolean
  - `module_pattern_matched`: boolean
  - `job_pattern`: string do pattern
  - `module_pattern`: string do pattern
  - `priority`: prioridade da regra

---

## Non-Functional Requirements (SHOULD)

### NFR-001: Performance
O sistema **DEVERIA** executar a análise de regras em menos de 100ms para até 100 regras.

### NFR-002: Feedback Visual
O sistema **DEVERIA** mostrar feedback visual imediato durante análise (loading state).

### NFR-003: Responsividade
O modal **DEVERIA** ser responsivo e funcionar bem em diferentes tamanhos de tela.

### NFR-004: Acessibilidade
O sistema **DEVERIA** seguir diretrizes WCAG 2.1 AA para acessibilidade.

---

## Interface Requirements (SHALL)

### IR-001: Reutilização de Componentes
O GlobalRegexValidator **UTILIZARÁ** a lógica existente do componente RegexTester (MonitoringRules.tsx linhas 145-218).

### IR-002: Consistência Visual
O modal **UTILIZARÁ** os mesmos padrões visuais do Ant Design Pro já utilizados no projeto (ProCard, ProForm, etc).

### IR-003: API Interna
O frontend **UTILIZARÁ** as regras já carregadas no estado `rulesData` para fazer a análise localmente.

---

## Design Constraints (MUST)

### DC-001: Validação Local
A validação do Global Regex Validator **DEVE** ser feita localmente no frontend usando JavaScript regex (new RegExp), sem chamada ao backend.

### DC-002: Case Insensitive
A validação **DEVE** usar case-insensitive match (flag `i`) para consistência com o backend.

### DC-003: Graceful Degradation
SE tipos existentes no cache não tiverem `matched_rule`, O sistema **DEVE** mostrar "-" nas colunas sem erro.

### DC-004: Sem Novas APIs
O Global Regex Validator **NÃO DEVE** criar novas APIs REST - a análise é feita com dados já carregados.

---

## Acceptance Criteria (GIVEN/WHEN/THEN)

### AC-001: Testar Job Name Simples
```gherkin
DADO que estou na página /settings/monitoring-rules
E existem regras de categorização carregadas
QUANDO clico no botão "Testar Categorização"
E informo Job Name "icmp" e Metrics Path "/probe"
E clico em "Analisar Categorização"
ENTÃO vejo a lista de regras que fazem match
E a primeira regra é destacada como "Regra Aplicada"
E vejo a categoria de destino (ex: "network-probes")
```

### AC-002: Testar com Module
```gherkin
DADO que estou na página /settings/monitoring-rules
E existem regras de categorização carregadas
QUANDO clico no botão "Testar Categorização"
E informo Job Name "blackbox", Module "http_2xx" e Metrics Path "/probe"
E clico em "Analisar Categorização"
ENTÃO vejo regras que fazem match por job_name_pattern e module_pattern
E entendo qual pattern foi responsável pelo match
```

### AC-003: Nenhuma Regra Aplica
```gherkin
DADO que estou na página /settings/monitoring-rules
E existem regras de categorização carregadas
QUANDO clico no botão "Testar Categorização"
E informo Job Name "meu_job_customizado" e Metrics Path "/metrics"
E clico em "Analisar Categorização"
ENTÃO vejo um Alert informando "Nenhuma regra aplicou"
E vejo que o job cairia em "custom-exporters" (categoria padrão)
```

### AC-004: Visualizar Match Columns
```gherkin
DADO que estou na página /monitoring-types
E existem tipos de monitoramento carregados
QUANDO visualizo a tabela de tipos
ENTÃO vejo as colunas "Regra Job" e "Regra Módulo"
E cada célula mostra o ID da regra que fez match
E ao passar o mouse vejo tooltip com o pattern e prioridade
```

### AC-005: Tipo Sem Module
```gherkin
DADO que estou na página /monitoring-types
E existe um tipo sem módulo (ex: node_exporter)
QUANDO visualizo a coluna "Regra Módulo" para este tipo
ENTÃO vejo "-" indicando que não há match de module
```

---

## Arquivos a Serem Modificados

### Frontend

| Arquivo | Modificação | Linhas Estimadas |
|---------|-------------|------------------|
| `frontend/src/pages/MonitoringRules.tsx` | Adicionar botão e modal GlobalRegexValidator | +200 linhas |
| `frontend/src/pages/MonitoringTypes.tsx` | Adicionar 2 colunas de match | +80 linhas |
| `frontend/src/components/GlobalRegexValidator.tsx` | **NOVO** - Componente do modal | ~250 linhas |

### Backend

| Arquivo | Modificação | Linhas Estimadas |
|---------|-------------|------------------|
| `backend/core/categorization_rule_engine.py` | Modificar retorno de categorize() | +30 linhas |
| `backend/api/monitoring_types_dynamic.py` | Incluir matched_rule no tipo | +20 linhas |

### Tipos TypeScript

| Arquivo | Modificação | Linhas Estimadas |
|---------|-------------|------------------|
| `frontend/src/types/monitoring.ts` | Adicionar interface MatchedRule | +15 linhas |

---

## Dependências Técnicas

1. **Componente RegexTester** - Lógica de validação a ser reutilizada
2. **CategorizationRuleEngine** - Método matches() para validar patterns
3. **rulesData state** - Regras já carregadas no frontend
4. **Ant Design Components** - Modal, Form, Input, Alert, Tag, Tooltip

---

## Riscos e Mitigações

| Risco | Probabilidade | Impacto | Mitigação |
|-------|--------------|---------|-----------|
| Performance com muitas regras | Baixa | Média | Limitar análise a 100 regras, usar lazy evaluation |
| Regex JavaScript vs Python | Média | Alta | Testar ambos engines com mesmos patterns, usar apenas features comuns |
| Dados antigos sem matched_rule | Alta | Baixa | Graceful fallback mostrando "-", sem erro |

---

## Estimativa de Complexidade

- **Total**: Média-Alta
- **Frontend**: Média (reutiliza lógica existente)
- **Backend**: Baixa (modificação pontual)
- **Testes**: Média (cenários diversos de regex)

---

## Notas de Implementação

1. O componente GlobalRegexValidator deve ser criado como arquivo separado para reutilização futura
2. A lógica de match deve ser idêntica ao backend (case-insensitive, mesma precedência)
3. Considerar adicionar "Copiar como JSON" no resultado para debug
4. As novas colunas de MonitoringTypes devem respeitar o ColumnSelector existente
