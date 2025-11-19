# Critérios de Aceitação - SPEC-SPRINT-003

---
id: SPEC-SPRINT-003-ACCEPTANCE
version: 1.0.0
status: draft
created: 2025-11-19
parent: SPEC-SPRINT-003
---

## TAG BLOCK

```
[TAG:SPEC-SPRINT-003-ACCEPTANCE]
[PARENT:SPEC-SPRINT-003]
[TYPE:acceptance-criteria]
```

---

## 1. Resumo

Este documento define os critérios de aceitação detalhados para o SPEC-SPRINT-003, utilizando formato Given-When-Then (Gherkin) para garantir testabilidade e clareza.

---

## 2. Funcionalidade: Modal de Criação de Serviços

### Cenário 2.1: Abrir modal de criação
```gherkin
DADO que o usuário está na página DynamicMonitoringPage
QUANDO o usuário clica no botão "Novo registro"
ENTÃO o sistema deve exibir um modal com título "Novo registro"
E o modal deve conter um campo de seleção "Tipo de Monitoramento"
E os campos dinâmicos devem ser carregados baseados na categoria da página
```

### Cenário 2.2: Carregar campos dinâmicos por categoria
```gherkin
DADO que o modal de criação está aberto
E a categoria da página é "network-probes"
QUANDO os campos são carregados
ENTÃO o sistema deve usar o contexto "blackbox" para buscar campos
E apenas campos com show_in_form === true devem ser exibidos
E campos devem estar ordenados pela propriedade "order"
```

### Cenário 2.3: Exibir campos obrigatórios primeiro
```gherkin
DADO que o modal de criação está aberto
QUANDO os campos dinâmicos são renderizados
ENTÃO campos com required === true devem aparecer primeiro
E campos obrigatórios devem ter asterisco (*) no label
E campos opcionais devem aparecer após divisor visual
```

### Cenário 2.4: Validar campos obrigatórios
```gherkin
DADO que o modal de criação está aberto
E existem campos obrigatórios não preenchidos
QUANDO o usuário clica em "Salvar"
ENTÃO o sistema deve impedir o submit
E mensagens de validação devem aparecer nos campos obrigatórios
E a mensagem deve usar validation.required_message se disponível
```

### Cenário 2.5: Usar ReferenceValueInput para campos com autocomplete
```gherkin
DADO que o modal de criação está aberto
E um campo tem available_for_registration === true
E o campo é do tipo "string"
E o campo não está na blacklist de exclusão
QUANDO o campo é renderizado
ENTÃO o sistema deve usar o componente ReferenceValueInput
E o usuário deve poder selecionar valores existentes ou criar novos
```

### Cenário 2.6: Submeter formulário de criação
```gherkin
DADO que o modal de criação está aberto
E todos os campos obrigatórios estão preenchidos
QUANDO o usuário clica em "Salvar"
ENTÃO o sistema deve chamar POST /api/v1/services
E o payload deve conter Meta com os valores dos campos
E o payload deve conter Tags incluindo a categoria
E após sucesso, deve mostrar mensagem com ID gerado
E a tabela deve ser recarregada
E o modal deve ser fechado
```

### Cenário 2.7: Tratar erro na criação
```gherkin
DADO que o usuário submeteu o formulário de criação
QUANDO a API retorna erro
ENTÃO o sistema deve mostrar mensagem de erro
E o modal deve permanecer aberto
E os dados do formulário devem ser preservados
```

---

## 3. Funcionalidade: Modal de Edição de Serviços

### Cenário 3.1: Abrir modal com dados do registro
```gherkin
DADO que o usuário está na página DynamicMonitoringPage
E existe um registro na tabela
QUANDO o usuário clica no ícone de edição do registro
ENTÃO o sistema deve abrir modal com título "Editar: {ID}"
E os campos devem estar preenchidos com dados do registro
E os valores devem vir de record.Meta
```

### Cenário 3.2: Preservar dados não editados
```gherkin
DADO que o modal de edição está aberto
E o usuário alterou apenas alguns campos
QUANDO o usuário clica em "Salvar"
ENTÃO o sistema deve fazer merge dos dados
E campos não alterados devem preservar valores originais
E o payload deve usar PUT /api/v1/services/{service_id}
```

### Cenário 3.3: Validar campos na edição
```gherkin
DADO que o modal de edição está aberto
QUANDO o usuário limpa um campo obrigatório
E clica em "Salvar"
ENTÃO o sistema deve mostrar erro de validação
E o submit deve ser impedido
```

---

## 4. Funcionalidade: Exclusão Individual

### Cenário 4.1: Exibir confirmação de exclusão
```gherkin
DADO que o usuário está na página DynamicMonitoringPage
E existe um registro na tabela
QUANDO o usuário clica no ícone de exclusão do registro
ENTÃO o sistema deve exibir Popconfirm
E o título deve ser "Remover serviço?"
E a descrição deve mostrar o ID do serviço
E deve haver botões "Sim" e "Não"
```

### Cenário 4.2: Confirmar exclusão
```gherkin
DADO que o Popconfirm de exclusão está visível
QUANDO o usuário clica em "Sim"
ENTÃO o sistema deve chamar DELETE /api/v1/services/{service_id}
E deve mostrar mensagem de sucesso após exclusão
E a tabela deve ser recarregada
E o registro não deve mais aparecer
```

### Cenário 4.3: Cancelar exclusão
```gherkin
DADO que o Popconfirm de exclusão está visível
QUANDO o usuário clica em "Não"
ENTÃO o Popconfirm deve fechar
E nenhuma API deve ser chamada
E o registro deve permanecer na tabela
```

### Cenário 4.4: Tratar erro na exclusão
```gherkin
DADO que o usuário confirmou a exclusão
QUANDO a API retorna erro 404
ENTÃO o sistema deve mostrar "Serviço não encontrado"

QUANDO a API retorna erro 409
ENTÃO o sistema deve mostrar "Serviço em uso, não pode ser excluído"

QUANDO a API retorna erro genérico
ENTÃO o sistema deve mostrar mensagem de erro com detalhes
```

---

## 5. Funcionalidade: Exclusão em Lote (Batch Delete)

### Cenário 5.1: Selecionar múltiplos registros
```gherkin
DADO que o usuário está na página DynamicMonitoringPage
QUANDO o usuário seleciona múltiplos registros usando checkboxes
ENTÃO o botão "Remover selecionados (N)" deve atualizar contador
E N deve refletir a quantidade de registros selecionados
```

### Cenário 5.2: Desabilitar botão sem seleção
```gherkin
DADO que o usuário está na página DynamicMonitoringPage
E nenhum registro está selecionado
ENTÃO o botão "Remover selecionados (0)" deve estar desabilitado
E deve ter aparência de disabled
```

### Cenário 5.3: Confirmar exclusão em lote
```gherkin
DADO que o usuário selecionou 15 registros
QUANDO o usuário clica em "Remover selecionados (15)"
ENTÃO o sistema deve exibir Popconfirm
E o título deve ser "Remover 15 serviços selecionados?"
E a descrição deve listar os 5 primeiros IDs
E deve indicar "... e mais 10 serviços"
```

### Cenário 5.4: Executar exclusão em lote
```gherkin
DADO que o usuário confirmou exclusão em lote de 100 registros
QUANDO o sistema executa a exclusão
ENTÃO deve processar em batches de 10 requisições paralelas
E deve continuar mesmo se algumas falharem
E deve mostrar resumo final "X sucesso, Y falhas"
E deve limpar seleção após conclusão
E deve recarregar tabela
```

### Cenário 5.5: Todos os registros excluídos com sucesso
```gherkin
DADO que o usuário confirmou exclusão em lote de 10 registros
E todas as exclusões foram bem-sucedidas
QUANDO a operação conclui
ENTÃO deve mostrar "10 serviços excluídos com sucesso"
E a mensagem deve ser do tipo "success"
```

### Cenário 5.6: Exclusão em lote com falhas parciais
```gherkin
DADO que o usuário confirmou exclusão em lote de 10 registros
E 3 exclusões falharam
QUANDO a operação conclui
ENTÃO deve mostrar "7 excluídos, 3 falhas"
E a mensagem deve ser do tipo "warning"
E os IDs com falha devem ser logados no console
```

---

## 6. Funcionalidade: Botão Refresh em MonitoringTypes

### Cenário 6.1: Exibir botão de atualização
```gherkin
DADO que o usuário está na página MonitoringTypes
ENTÃO deve existir um botão "Atualizar" na toolbar
E o botão deve ter ícone de sincronização
E deve ter tooltip explicativo
```

### Cenário 6.2: Executar refresh
```gherkin
DADO que o usuário está na página MonitoringTypes
QUANDO o usuário clica no botão "Atualizar"
ENTÃO o sistema deve invalidar cache de monitoring types
E deve recarregar dados do KV
E o ícone deve mostrar animação de spin durante loading
E deve mostrar mensagem de sucesso após conclusão
```

### Cenário 6.3: Mostrar timestamp de atualização
```gherkin
DADO que o usuário executou um refresh
QUANDO a operação conclui
ENTÃO deve exibir timestamp da última atualização
E o formato deve ser "Atualizado: HH:mm:ss"
```

---

## 7. Funcionalidade: Geração Dinâmica de ID

### Cenário 7.1: Gerar ID com campos do KV
```gherkin
DADO que um serviço está sendo criado sem ID explícito
E o KV metadata-fields está disponível
QUANDO o backend gera o ID
ENTÃO deve ler campos obrigatórios do KV
E deve ordenar campos por propriedade "order"
E deve gerar ID no formato "{campo1}/{campo2}/.../campoN}@{name}"
E valores devem ser sanitizados (lowercase, sem especiais)
```

### Cenário 7.2: Usar fallback quando KV falha
```gherkin
DADO que um serviço está sendo criado sem ID explícito
E o KV metadata-fields está indisponível
QUANDO o backend gera o ID
ENTÃO deve usar padrão hardcoded
E o padrão deve ser "{module}/{company}/{project}/{env}@{name}"
E deve logar warning sobre uso de fallback
```

### Cenário 7.3: Erro quando campos obrigatórios faltam
```gherkin
DADO que um serviço está sendo criado
E o payload não contém todos os campos obrigatórios
QUANDO o backend tenta gerar o ID
ENTÃO deve retornar erro 400
E a mensagem deve listar campos faltantes
E o formato deve ser "Campos obrigatórios faltando: campo1, campo2"
```

### Cenário 7.4: Sanitização de valores
```gherkin
DADO que os metadados contêm caracteres especiais
E o valor de company é "Test Corp!@#"
QUANDO o backend gera o ID
ENTÃO o valor deve ser sanitizado para "testcorp"
E caracteres especiais devem ser removidos
E letras devem ser convertidas para lowercase
```

### Cenário 7.5: Verificar unicidade do ID
```gherkin
DADO que um serviço está sendo criado
E o ID gerado já existe no Consul
QUANDO o backend tenta criar o serviço
ENTÃO deve retornar erro 409 (Conflict)
E a mensagem deve indicar duplicidade
```

---

## 8. Funcionalidade: Prewarm no Startup

### Cenário 8.1: Executar prewarm no startup
```gherkin
DADO que o backend está iniciando
QUANDO o evento startup é disparado
ENTÃO deve extrair tipos de monitoramento de todos os servidores
E deve popular cache com TTL 60s
E deve logar quantidade de tipos carregados
```

### Cenário 8.2: Continuar startup mesmo com falha no prewarm
```gherkin
DADO que o backend está iniciando
E a extração de tipos falha
QUANDO o evento startup é processado
ENTÃO o erro deve ser logado
E a aplicação deve continuar iniciando
E deve agendar retry em 30 segundos
```

### Cenário 8.3: Retry automático
```gherkin
DADO que o prewarm falhou no startup
QUANDO 30 segundos se passam
ENTÃO o sistema deve tentar prewarm novamente
E se falhar, deve agendar novo retry em 60 segundos
```

---

## 9. Testes Obrigatórios

### 9.1 Testes de Unidade - Frontend

| Teste | Arquivo | Descrição |
|-------|---------|-----------|
| UT-F01 | DynamicMonitoringPage.test.tsx | Modal abre ao clicar em Novo registro |
| UT-F02 | DynamicMonitoringPage.test.tsx | Campos dinâmicos são renderizados |
| UT-F03 | DynamicMonitoringPage.test.tsx | Validação impede submit sem campos obrigatórios |
| UT-F04 | DynamicMonitoringPage.test.tsx | Submit chama API POST corretamente |
| UT-F05 | DynamicMonitoringPage.test.tsx | Modal de edição preenche dados |
| UT-F06 | DynamicMonitoringPage.test.tsx | handleDelete chama API DELETE |
| UT-F07 | DynamicMonitoringPage.test.tsx | handleBatchDelete processa em batches |
| UT-F08 | MonitoringTypes.test.tsx | Botão Refresh chama handleReload |

### 9.2 Testes de Unidade - Backend

| Teste | Arquivo | Descrição |
|-------|---------|-----------|
| UT-B01 | test_id_generation.py | Gera ID com campos do KV |
| UT-B02 | test_id_generation.py | Fallback quando KV falha |
| UT-B03 | test_id_generation.py | Erro com campos faltantes |
| UT-B04 | test_id_generation.py | Sanitização de caracteres |
| UT-B05 | test_services_crud.py | POST cria serviço |
| UT-B06 | test_services_crud.py | PUT atualiza serviço |
| UT-B07 | test_services_crud.py | DELETE remove serviço |
| UT-B08 | test_startup.py | Prewarm executa no startup |

### 9.3 Testes de Integração

| Teste | Arquivo | Descrição |
|-------|---------|-----------|
| IT-01 | test_integration.py | Fluxo completo de criação |
| IT-02 | test_integration.py | Fluxo completo de edição |
| IT-03 | test_integration.py | Exclusão e reload da tabela |
| IT-04 | test_integration.py | Batch delete com 20 registros |
| IT-05 | test_integration.py | ID gerado é único |

### 9.4 Testes E2E (Opcional mas Recomendado)

| Teste | Arquivo | Descrição |
|-------|---------|-----------|
| E2E-01 | e2e/crud.spec.ts | Criar serviço via UI |
| E2E-02 | e2e/crud.spec.ts | Editar serviço via UI |
| E2E-03 | e2e/crud.spec.ts | Excluir serviço via UI |
| E2E-04 | e2e/crud.spec.ts | Batch delete via UI |

---

## 10. Métricas de Sucesso

### 10.1 Cobertura de Código
- **Frontend:** >= 80% de cobertura nos componentes modificados
- **Backend:** >= 80% de cobertura nas funções modificadas

### 10.2 Performance
- Modal deve abrir em < 500ms
- Campos dinâmicos devem carregar em < 1s
- Batch delete de 100 registros em < 5s
- Geração de ID em < 50ms

### 10.3 Qualidade
- Zero erros no console do navegador
- Zero warnings de TypeScript
- Todos os TODOs removidos
- Todas as validações funcionando

### 10.4 Usabilidade
- Mensagens de feedback em todas as ações
- Loading indicators em todas as operações assíncronas
- Tratamento de erro claro e informativo

---

## 11. Definition of Done

A funcionalidade estará completa quando:

- [ ] Todos os cenários de teste passarem
- [ ] Cobertura de testes >= 80%
- [ ] Nenhum erro no console
- [ ] Nenhum warning de TypeScript
- [ ] Documentação inline completa (comentários em PT-BR)
- [ ] Code review aprovado
- [ ] Testes manuais aprovados pelo usuário
- [ ] Performance dentro dos limites
- [ ] Fallbacks funcionando corretamente

---

## 12. Casos de Borda

### 12.1 Modal de Criação
- Campo dinâmico não existe no KV
- Tipo de monitoramento sem form_schema
- Timeout ao carregar campos
- Campos com validação regex inválida

### 12.2 Exclusão
- Excluir registro que não existe mais
- Excluir último registro da tabela
- Rede cai durante batch delete
- Usuário cancela durante batch delete

### 12.3 Geração de ID
- KV com schema corrompido
- Campos obrigatórios mudaram após inicio da criação
- ID gerado com 500+ caracteres
- Colisão de ID após sanitização

---

## 13. Checklist de Aceitação Final

### Frontend
- [ ] Modal de criação abre corretamente
- [ ] Campos dinâmicos renderizam por categoria
- [ ] Validação de campos obrigatórios
- [ ] Submit chama API correta
- [ ] Modal de edição preenche dados
- [ ] Exclusão individual com Popconfirm
- [ ] Batch delete com limite de concorrência
- [ ] Mensagens de feedback em todas as ações
- [ ] Loading states em operações assíncronas

### Backend
- [ ] generate_dynamic_service_id lê do KV
- [ ] Fallback funciona quando KV falha
- [ ] Sanitização de IDs
- [ ] Validação de campos obrigatórios
- [ ] Prewarm no startup
- [ ] Retry de prewarm

### Testes
- [ ] Testes unitários frontend passando
- [ ] Testes unitários backend passando
- [ ] Testes de integração passando
- [ ] Cobertura >= 80%

### Documentação
- [ ] Comentários em português-BR
- [ ] Funções documentadas
- [ ] Tipos TypeScript corretos

---

**[END:SPEC-SPRINT-003-ACCEPTANCE]**
