# SPEC-SPRINT-003: Finalização do Sprint 3 - CRUD Dinâmico Completo

---
id: SPEC-SPRINT-003
version: 1.0.0
status: draft
created: 2025-11-19
author: spec-builder
tags: [sprint3, crud, dynamic, frontend, backend, testing]
priority: high
estimated_effort: 14-18h
---

## TAG BLOCK

```
[TAG:SPEC-SPRINT-003]
[PARENT:SPEC-SPRINT-002]
[DOMAIN:crud-dinamico]
[STATUS:draft]
```

---

## 1. Visão Geral

### 1.1 Contexto

O Skills-Eye é uma aplicação 100% dinâmica para gerenciamento de serviços do HashiCorp Consul. Os Sprints 1 e 2 foram concluídos com sucesso, implementando performance (33s para 2.5s), cache inteligente (hit rate 91.7%), e API de Cache Management.

O Sprint 3 está 60% completo e foca na finalização do CRUD dinâmico com:
- Modal de criação/edição baseado em campos dinâmicos do KV
- Exclusão individual e em lote
- Geração dinâmica de IDs baseada em metadata-fields
- Testes obrigatórios para todas as funcionalidades

### 1.2 Objetivos

1. **Completar CRUD em DynamicMonitoringPage.tsx** - Modal de criação/edição funcional
2. **Implementar exclusão** - Individual e batch delete com confirmação
3. **Refatorar geração de ID** - Baseado em campos obrigatórios do KV (híbrido)
4. **Adicionar botão Refresh** - Em MonitoringTypes.tsx para invalidar cache
5. **Prewarm de tipos** - No startup da aplicação
6. **Testes obrigatórios** - Unitários e integração para cada funcionalidade

### 1.3 Escopo

**Incluído:**
- Frontend: DynamicMonitoringPage.tsx, MonitoringTypes.tsx
- Backend: services.py, consul_manager.py, app.py
- Testes: Jest/Vitest (frontend), Pytest (backend)

**Excluído:**
- Alterações em outras páginas (MonitoringRules, CacheManagement)
- Mudanças na estrutura de cache existente
- Refatoração de componentes que já funcionam

---

## 2. Requisitos Funcionais (EARS Format)

### 2.1 Modal de Criação de Serviços [RF-001]

**WHEN** o usuário clica no botão "Novo registro" na página DynamicMonitoringPage
**THE SYSTEM SHALL** exibir um modal com formulário dinâmico baseado nos campos configurados no KV metadata-fields

**Detalhamento:**

1. **Carregamento de campos dinâmicos**
   - MUST usar hook `useFormFields(category)` para obter campos
   - MUST filtrar campos onde `show_in_form === true` e `enabled === true`
   - MUST ordenar campos por `order` ascendente
   - MUST mapear categoria da página para contexto correto:
     - `network-probes`, `web-probes` → `blackbox`
     - `system-exporters`, `database-exporters` → `exporters`
     - Outros → contexto direto

2. **Renderização de campos**
   - MUST usar componente `FormFieldRenderer` para cada campo
   - MUST aplicar regras de validação do campo (required, min/max length, regex)
   - MUST usar `ReferenceValueInput` para campos com `available_for_registration === true`
   - MUST excluir campos da blacklist de autocomplete (cservice, serviceDisplayName, etc)
   - SHOULD mostrar tooltip com `field.description` em cada campo

3. **Campos obrigatórios**
   - MUST mostrar asterisco (*) em campos onde `field.required === true`
   - MUST impedir submit se campos obrigatórios estiverem vazios
   - MUST mostrar mensagem de validação customizada (`validation.required_message`)

4. **Campos especiais**
   - MUST incluir campo de seleção de tipo (monitoring type)
   - MUST carregar tipos disponíveis via `consulAPI.getMonitoringTypes()`
   - WHEN tipo selecionado mudar, MUST atualizar campos do form_schema se disponível

5. **Submit do formulário**
   - MUST chamar POST `/api/v1/services` com dados formatados
   - MUST gerar ID dinâmico se não fornecido (backend)
   - MUST mostrar mensagem de sucesso com BadgeStatus
   - MUST recarregar tabela após criação bem-sucedida
   - MUST fechar modal após sucesso

### 2.2 Modal de Edição de Serviços [RF-002]

**WHEN** o usuário clica no ícone de edição em uma linha da tabela
**THE SYSTEM SHALL** exibir modal com formulário preenchido com dados atuais do serviço

**Detalhamento:**

1. **Carregamento de dados**
   - MUST preencher formulário com `currentRecord` passado via estado
   - MUST mapear campos do `record.Meta` para os campos do formulário
   - MUST preservar campos não editáveis (ID, timestamps)

2. **Validação e submit**
   - MUST aplicar mesmas regras de validação da criação
   - MUST chamar PUT `/api/v1/services/{service_id}` com dados atualizados
   - MUST preservar metadata não alterado (merge, não replace)
   - MUST mostrar diff de alterações antes de confirmar (opcional)

3. **Tratamento de erros**
   - MUST mostrar erro se serviço foi modificado por outro usuário (conflito)
   - SHOULD permitir refresh do registro antes de editar

### 2.3 Exclusão Individual de Serviços [RF-003]

**WHEN** o usuário clica no ícone de exclusão em uma linha da tabela
**THE SYSTEM SHALL** exibir Popconfirm de confirmação e executar exclusão

**Detalhamento:**

1. **Confirmação**
   - MUST mostrar Popconfirm com título "Remover serviço?"
   - MUST mostrar descrição com ID do serviço a ser removido
   - MUST ter botões "Sim" e "Não" com cores adequadas

2. **Execução**
   - MUST chamar DELETE `/api/v1/services/{service_id}`
   - MUST mostrar loading durante requisição
   - MUST mostrar mensagem de sucesso após exclusão
   - MUST recarregar tabela após exclusão
   - MUST invalidar cache local do serviço excluído

3. **Tratamento de erros**
   - MUST mostrar erro se serviço não existir (404)
   - MUST mostrar erro se serviço estiver em uso (409)
   - SHOULD oferecer opção de forçar exclusão

### 2.4 Exclusão em Lote (Batch Delete) [RF-004]

**WHEN** o usuário seleciona múltiplos registros e clica em "Remover selecionados"
**THE SYSTEM SHALL** excluir todos os registros selecionados com confirmação única

**Detalhamento:**

1. **Seleção**
   - MUST usar rowSelection da ProTable
   - MUST atualizar contador no botão "Remover selecionados (N)"
   - MUST desabilitar botão se nenhum registro selecionado

2. **Confirmação**
   - MUST mostrar Popconfirm com quantidade de registros
   - MUST listar IDs dos primeiros 5 registros (se > 5, mostrar "+N mais")
   - MUST alertar sobre irreversibilidade da ação

3. **Execução**
   - MUST chamar DELETE para cada serviço em paralelo (Promise.all)
   - MUST limitar concorrência a 10 requisições simultâneas
   - MUST mostrar progresso (N de M excluídos)
   - MUST continuar mesmo se alguns falharem
   - MUST mostrar resumo final (X sucesso, Y falhas)

4. **Após execução**
   - MUST limpar seleção (setSelectedRowKeys([]))
   - MUST recarregar tabela
   - MUST mostrar erros individuais se houver

### 2.5 Botão Refresh em MonitoringTypes [RF-005]

**WHEN** o usuário clica no botão "Atualizar" em MonitoringTypes.tsx
**THE SYSTEM SHALL** invalidar cache e recarregar tipos de monitoramento

**Detalhamento:**

1. **Invalidação de cache**
   - MUST invalidar cache local de monitoring types
   - MUST forçar nova extração do KV
   - SHOULD mostrar indicador de loading durante operação

2. **Feedback**
   - MUST mostrar timestamp da última atualização
   - MUST mostrar BadgeStatus com status do cache (hit/miss/stale)

### 2.6 Geração Dinâmica de ID (Híbrido) [RF-006]

**WHEN** um serviço é criado sem ID explícito
**THE SYSTEM SHALL** gerar ID baseado nos campos obrigatórios do KV metadata-fields

**Detalhamento:**

1. **Leitura de campos obrigatórios**
   - MUST obter lista de campos obrigatórios do KV
   - MUST usar endpoint GET `/api/v1/metadata-fields/required`
   - MUST cachear resultado com TTL 5 minutos

2. **Geração do ID**
   - MUST usar padrão: `{campo1}/{campo2}/.../{campoN}@{name}`
   - MUST ordenar campos pela propriedade `order`
   - MUST excluir campo `name` da parte antes do @
   - MUST sanitizar valores (remover caracteres especiais)

3. **Fallback (modo híbrido)**
   - IF leitura do KV falhar, MUST usar padrão hardcoded
   - Padrão fallback: `{module}/{company}/{project}/{env}@{name}`
   - MUST logar warning quando usar fallback
   - SHOULD tentar reconectar ao KV em background

4. **Validação**
   - MUST verificar unicidade do ID gerado
   - MUST retornar erro 409 se ID já existir
   - MUST sugerir sufixo numérico se duplicado

### 2.7 Prewarm de Monitoring Types [RF-007]

**WHEN** a aplicação backend inicia (startup)
**THE SYSTEM SHALL** carregar tipos de monitoramento em cache para primeira requisição rápida

**Detalhamento:**

1. **Execução no startup**
   - MUST executar em `app.py` no evento `startup`
   - MUST chamar extração de tipos de todos os servidores
   - MUST popular cache com TTL 60s

2. **Tratamento de falhas**
   - IF extração falhar, MUST logar erro mas não impedir startup
   - SHOULD usar dados stale se disponíveis
   - MUST tentar novamente em 30 segundos

---

## 3. Requisitos Não-Funcionais

### 3.1 Performance [RNF-001]

- SHOULD carregar modal em < 500ms
- MUST executar batch delete em < 5s para 100 registros
- SHOULD gerar ID em < 50ms

### 3.2 Usabilidade [RNF-002]

- MUST manter consistência visual com restante do sistema
- MUST usar componentes Ant Design Pro existentes
- SHOULD mostrar feedback em todas as ações (loading, success, error)

### 3.3 Confiabilidade [RNF-003]

- MUST ter fallback para geração de ID
- MUST preservar dados em caso de falha de rede
- SHOULD permitir retry de operações falhadas

### 3.4 Manutenibilidade [RNF-004]

- MUST documentar código com comentários em português-BR
- MUST seguir padrões existentes no projeto
- MUST ter cobertura de testes >= 80%

---

## 4. Requisitos de Interface

### 4.1 Modal de Criação/Edição

```
┌─────────────────────────────────────────┐
│ [Título: Novo registro / Editar ...]    │
├─────────────────────────────────────────┤
│                                         │
│ Tipo de Monitoramento: [Select    v]    │
│                                         │
│ ─────── Campos Obrigatórios ─────────   │
│                                         │
│ Module *:     [Input/Autocomplete    ]  │
│ Company *:    [Input/Autocomplete    ]  │
│ Project *:    [Input/Autocomplete    ]  │
│ Environment *:[Input/Autocomplete    ]  │
│ Name *:       [Input                 ]  │
│                                         │
│ ─────── Campos Opcionais ────────────   │
│                                         │
│ Site:         [Input/Autocomplete    ]  │
│ Description:  [TextArea              ]  │
│ Tags:         [Select multiple       ]  │
│                                         │
├─────────────────────────────────────────┤
│              [Cancelar]   [Salvar]      │
└─────────────────────────────────────────┘
```

### 4.2 Popconfirm de Exclusão

```
┌─────────────────────────────────┐
│ Remover serviço?                │
│                                 │
│ ID: network-probes/company/...  │
│                                 │
│ Esta ação é irreversível.       │
│                                 │
│     [Não]        [Sim]          │
└─────────────────────────────────┘
```

### 4.3 Batch Delete Confirm

```
┌─────────────────────────────────────┐
│ Remover 15 serviços selecionados?   │
│                                     │
│ • service-1                         │
│ • service-2                         │
│ • service-3                         │
│ • service-4                         │
│ • service-5                         │
│ ... e mais 10 serviços              │
│                                     │
│ Esta ação é irreversível.           │
│                                     │
│       [Não]        [Sim]            │
└─────────────────────────────────────┘
```

---

## 5. Restrições de Design

### 5.1 Tecnologias Obrigatórias

- **Frontend**: React 18, TypeScript, Ant Design Pro, Monaco Editor
- **Backend**: FastAPI, Python 3.11+, Consul KV
- **Testes**: Jest/Vitest (frontend), Pytest (backend)

### 5.2 Componentes a Reutilizar

- `FormFieldRenderer` - Renderização dinâmica de campos
- `ReferenceValueInput` - Autocomplete com cadastro
- `BadgeStatus` - Indicador de status de cache
- `useFormFields` - Hook para campos de formulário
- `useMetadataFieldsContext` - Contexto compartilhado

### 5.3 Padrões a Seguir

- Comentários detalhados em português-BR
- Tratamento de erro em todas as operações assíncronas
- Loading states em todas as ações de usuário
- Mensagens de feedback via `message` do Ant Design

### 5.4 Restrições de Implementação

- NÃO criar novos componentes se existir similar
- NÃO duplicar lógica de validação (usar FormFieldRenderer)
- NÃO hardcodar IDs de campos (sempre ler do KV)
- NÃO ignorar erros de API (sempre mostrar ao usuário)

---

## 6. Dependências

### 6.1 Internas

| Componente | Localização | Uso |
|------------|-------------|-----|
| FormFieldRenderer | /frontend/src/components/ | Renderização de campos |
| useFormFields | /frontend/src/hooks/ | Obter campos para form |
| consulAPI | /frontend/src/services/api.ts | Chamadas de API |
| BadgeStatus | /frontend/src/components/ | Indicador de cache |

### 6.2 Externas

| Biblioteca | Versão | Uso |
|------------|--------|-----|
| @monaco-editor/react | ^4.7.0 | Editor JSON (já instalado) |
| antd | ^5.x | Componentes UI |
| @ant-design/pro-components | ^2.x | ProTable, ProForm |

---

## 7. Riscos e Mitigações

| Risco | Probabilidade | Impacto | Mitigação |
|-------|---------------|---------|-----------|
| KV indisponível durante geração de ID | Média | Alto | Implementar fallback híbrido |
| Performance degradada em batch delete | Média | Médio | Limitar concorrência a 10 |
| Campos dinâmicos inconsistentes | Baixa | Alto | Validar schema antes de render |
| Conflito de edição simultânea | Baixa | Médio | Implementar versioning/ETag |

---

## 8. Rastreabilidade

### 8.1 Conexões com Sprints Anteriores

- `[REF:SPEC-SPRINT-001]` - Performance e LocalCache
- `[REF:SPEC-SPRINT-002]` - Cache inteligente e BadgeStatus

### 8.2 Arquivos Impactados

**Frontend:**
- `/frontend/src/pages/DynamicMonitoringPage.tsx` - Modal CRUD
- `/frontend/src/pages/MonitoringTypes.tsx` - Botão Refresh
- `/frontend/src/services/api.ts` - Novos endpoints (se necessário)

**Backend:**
- `/backend/api/services.py` - Geração dinâmica de ID
- `/backend/core/consul_manager.py` - Método generate_dynamic_service_id
- `/backend/app.py` - Prewarm no startup

**Testes:**
- `/frontend/src/__tests__/DynamicMonitoringPage.test.tsx` - Testes do modal
- `/backend/tests/test_services.py` - Testes de ID generation
- `/backend/tests/test_integration.py` - Testes E2E

---

## 9. Glossário

| Termo | Definição |
|-------|-----------|
| **CRUD** | Create, Read, Update, Delete - operações básicas de dados |
| **KV** | Key-Value store do Consul |
| **metadata-fields** | Campos dinâmicos extraídos do Prometheus |
| **form_schema** | Schema JSON que define campos do formulário por tipo |
| **Prewarm** | Pré-carregamento de dados no startup |
| **Batch Delete** | Exclusão de múltiplos registros em uma operação |

---

## 10. Aprovações

| Papel | Nome | Data | Status |
|-------|------|------|--------|
| Autor | spec-builder | 2025-11-19 | Draft |
| Revisor | - | - | Pendente |
| Aprovador | - | - | Pendente |

---

**[END:SPEC-SPRINT-003]**
