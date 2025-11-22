# Guia de Comandos Alfred - MoAI-ADK

> **Versao**: 0.27.2 | **Ultima Atualizacao**: 2025-11-22

Este guia documenta os comandos principais do Alfred, o SuperAgent do MoAI-ADK para desenvolvimento assistido por IA.

---

## Visao Geral do Workflow

O Alfred segue um workflow de 4 etapas sequenciais:

```
/alfred:0-project → /alfred:1-plan → /alfred:2-run → /alfred:3-sync
     Setup            Planeja           Implementa       Sincroniza
```

---

## Comandos Principais

### /alfred:0-project

**Proposito**: Inicializar ou configurar o projeto

**Sintaxe**:
```bash
/alfred:0-project                    # Inicializacao ou auto-deteccao
/alfred:0-project setting            # Abrir menu de configuracoes
/alfred:0-project setting tab_1      # Configurar tab especifica
/alfred:0-project update             # Atualizar templates apos upgrade
/alfred:0-project --optimize         # Otimizar projeto existente
```

**Quando usar**:
- Primeiro uso do Alfred em um projeto novo
- Alterar configuracoes (idioma, git strategy, etc)
- Apos atualizar o pacote moai-adk
- Revisar estrutura do projeto

**Tabs de configuracao disponiveis**:
1. `tab_1_user_language` - Usuario e idioma
2. `tab_2_project_info` - Informacoes do projeto
3. `tab_3_git_strategy` - Estrategia Git
4. `tab_4_quality_principles` - Principios de qualidade
5. `tab_5_system_github` - Sistema e GitHub

**Exemplo pratico**:
```bash
# Configurar estrategia Git
/alfred:0-project setting tab_3_git_strategy

# Mudar idioma de conversacao
/alfred:0-project setting tab_1_user_language
```

---

### /alfred:1-plan

**Proposito**: Criar especificacoes (SPECs) para novas funcionalidades

**Sintaxe**:
```bash
/alfred:1-plan "Titulo da Feature"
/alfred:1-plan "Feature 1" "Feature 2" "Feature 3"
/alfred:1-plan SPEC-001 "modificacoes"
```

**Quando usar**:
- Planejar nova funcionalidade
- Documentar requisitos antes de implementar
- Criar multiplas SPECs relacionadas
- Modificar SPEC existente

**O que gera**:
- `.moai/specs/SPEC-XXX-NNN/spec.md` - Especificacao EARS
- `.moai/specs/SPEC-XXX-NNN/plan.md` - Plano de implementacao
- `.moai/specs/SPEC-XXX-NNN/acceptance.md` - Criterios de aceitacao
- Branch `feature/SPEC-XXX-NNN` (se configurado)

**Exemplo pratico**:
```bash
# Criar SPEC para nova feature
/alfred:1-plan "Implementar filtro avancado de servicos"

# Criar multiplas SPECs
/alfred:1-plan "API de exportacao" "Dashboard de metricas" "Cache distribuido"

# Modificar SPEC existente
/alfred:1-plan SPEC-PERF-001 "adicionar cache Redis"
```

**Dicas**:
- Use titulos claros e objetivos
- O Alfred fara perguntas para refinar os requisitos
- Revise o spec.md antes de prosseguir para implementacao

---

### /alfred:2-run

**Proposito**: Implementar uma SPEC usando TDD (Test-Driven Development)

**Sintaxe**:
```bash
/alfred:2-run SPEC-XXX-NNN
/alfred:2-run all
```

**Quando usar**:
- Implementar funcionalidade especificada
- Executar ciclo TDD completo
- Implementar todas as SPECs pendentes

**Fases de execucao**:
1. **Fase 1**: Analise da SPEC e planejamento
2. **Fase 2**: Implementacao TDD (RED → GREEN → REFACTOR)
3. **Fase 2.5**: Quality Gate (validacao de qualidade)
4. **Fase 3**: Finalizacao e relatorio

**Exemplo pratico**:
```bash
# Implementar SPEC especifica
/alfred:2-run SPEC-PERF-002

# Implementar todas as SPECs pendentes
/alfred:2-run all
```

**Dicas**:
- Certifique-se que a SPEC esta bem definida antes de rodar
- O Alfred criara testes primeiro (TDD)
- Acompanhe o progresso pelo TodoWrite
- Commits sao feitos automaticamente em cada fase

---

### /alfred:3-sync

**Proposito**: Sincronizar documentacao e finalizar PR

**Sintaxe**:
```bash
/alfred:3-sync                       # Modo auto (padrao)
/alfred:3-sync auto                  # Sincronizacao automatica
/alfred:3-sync force                 # Forcar sincronizacao completa
/alfred:3-sync status                # Verificar status atual
/alfred:3-sync project               # Sincronizar projeto inteiro
/alfred:3-sync auto path/to/file     # Sincronizar arquivo especifico
```

**Quando usar**:
- Apos concluir implementacao
- Atualizar documentacao com mudancas do codigo
- Verificar consistencia docs/codigo
- Preparar merge para branch principal

**O que faz**:
1. Valida qualidade do codigo
2. Atualiza documentacao automaticamente
3. Gera relatorio de sincronizacao
4. Faz push para remoto (se configurado)
5. Cria/atualiza PR (se modo team)

**Exemplo pratico**:
```bash
# Sincronizacao padrao apos implementacao
/alfred:3-sync

# Forcar sync completo
/alfred:3-sync force

# Verificar o que precisa ser sincronizado
/alfred:3-sync status

# Sincronizar arquivo especifico
/alfred:3-sync auto backend/api/services.py
```

**Dicas**:
- Execute apos cada SPEC completada
- Use `status` para preview antes de sincronizar
- O push remoto so ocorre se `push_to_remote: true`

---

### /alfred:9-feedback

**Proposito**: Criar issues no GitHub rapidamente

**Sintaxe**:
```bash
/alfred:9-feedback
```

**Quando usar**:
- Reportar bug encontrado
- Sugerir melhoria
- Documentar problema para resolver depois

**O que faz**:
- Coleta informacoes automaticamente
- Aplica template padrao
- Sugere labels apropriadas
- Cria issue no repositorio

---

## Skills Uteis

Alem dos comandos, o Alfred possui Skills que podem ser invocadas:

### Skills de Configuracao
- `moai-alfred-config-schema` - Validacao de configuracoes
- `moai-alfred-language-detection` - Deteccao de linguagem do projeto

### Skills de Desenvolvimento
- `moai-alfred-code-reviewer` - Revisao de codigo com TRUST 5
- `moai-alfred-clone-pattern` - Padroes de clonagem para tarefas complexas
- `moai-alfred-todowrite-pattern` - Padroes de gerenciamento de tarefas

### Skills de Qualidade
- `moai-alfred-practices` - Boas praticas de desenvolvimento
- `moai-alfred-proactive-suggestions` - Sugestoes proativas

---

## Configuracoes Importantes

### Git Strategy (Personal Mode)

```json
{
  "git_strategy": {
    "personal": {
      "push_to_remote": true,        // Habilita push automatico
      "auto_commit": true,           // Commits automaticos
      "branch_prefix": "feature/SPEC-",
      "develop_branch": "dev-adriano",
      "main_branch": "main"
    }
  }
}
```

### Idioma

```json
{
  "language": {
    "conversation_language": "pt-BR",    // Idioma das respostas
    "agent_prompt_language": "en"        // Idioma interno dos agentes
  }
}
```

### Relatorios

```json
{
  "reports": {
    "generation": {
      "auto_generate": true,
      "trigger": "sprint_complete_validated"
    },
    "storage": {
      "location": "docs/reports/"
    }
  }
}
```

---

## Fluxo de Trabalho Recomendado

### Para Nova Feature

```bash
# 1. Planejar a feature
/alfred:1-plan "Nome da Feature"

# 2. Revisar spec gerada
# Editar .moai/specs/SPEC-XXX-NNN/spec.md se necessario

# 3. Implementar
/alfred:2-run SPEC-XXX-NNN

# 4. Sincronizar e finalizar
/alfred:3-sync
```

### Para Bug Fix

```bash
# 1. Criar SPEC para o fix
/alfred:1-plan "Corrigir bug de validacao no formulario"

# 2. Implementar correcao
/alfred:2-run SPEC-FIX-NNN

# 3. Sincronizar
/alfred:3-sync
```

### Para Refatoracao

```bash
# 1. Documentar refatoracao
/alfred:1-plan "Refatorar modulo de cache"

# 2. Executar refatoracao
/alfred:2-run SPEC-REFACTOR-NNN

# 3. Sincronizar
/alfred:3-sync
```

---

## Dicas Avancadas

### 1. Use Titulos Descritivos nas SPECs

```bash
# Ruim
/alfred:1-plan "Cache"

# Bom
/alfred:1-plan "Implementar cache Redis para consultas de servicos"
```

### 2. Revise Sempre o Plan

Antes de executar `/alfred:2-run`, revise:
- `.moai/specs/SPEC-XXX/spec.md` - Requisitos corretos?
- `.moai/specs/SPEC-XXX/plan.md` - Abordagem adequada?
- `.moai/specs/SPEC-XXX/acceptance.md` - Criterios claros?

### 3. Acompanhe o Progresso

O Alfred usa TodoWrite para rastrear tarefas. Acompanhe o progresso na interface.

### 4. Commits Atomicos

O Alfred faz commits automaticos em pontos criticos:
- Apos criar testes
- Apos implementacao passar
- Apos refatoracao
- Apos documentacao

### 5. Mantenha Configuracoes Atualizadas

```bash
# Apos atualizar moai-adk
/alfred:0-project update

# Revisar configuracoes
/alfred:0-project setting
```

---

## Troubleshooting

### SPEC nao encontrada

```bash
# Verificar SPECs existentes
ls .moai/specs/

# Recriar se necessario
/alfred:1-plan "Titulo da Feature"
```

### Push remoto nao funciona

```bash
# Verificar configuracao
/alfred:0-project setting tab_3_git_strategy

# Habilitar push_to_remote: true
```

### Sync nao atualiza docs

```bash
# Forcar sincronizacao completa
/alfred:3-sync force
```

### Erro de validacao

```bash
# Verificar status
/alfred:3-sync status

# Revisar relatorio em .moai/reports/
```

---

## Estrutura de Arquivos

```
.moai/
├── config/
│   └── config.json          # Configuracoes do projeto
├── specs/
│   └── SPEC-XXX-NNN/
│       ├── spec.md          # Especificacao EARS
│       ├── plan.md          # Plano de implementacao
│       └── acceptance.md    # Criterios de aceitacao
├── reports/
│   └── *.md                 # Relatorios gerados
├── logs/
│   └── sessions/            # Historico de sessoes
└── memory/
    └── *.json               # Contexto persistente
```

---

## Referencias

- [MoAI-ADK Documentation](https://github.com/moai-adk)
- [EARS Requirements Syntax](https://en.wikipedia.org/wiki/EARS_notation)
- [TDD Best Practices](https://en.wikipedia.org/wiki/Test-driven_development)

---

**Autor**: Alfred SuperAgent
**Projeto**: Skills-Eye
**Empresa**: SKILLS IT - Solucoes em TI
