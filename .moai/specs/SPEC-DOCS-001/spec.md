# SPEC-DOCS-001: Reorganizacao Completa e Atualizacao da Documentacao

---
spec_id: SPEC-DOCS-001
version: 1.0.0
status: draft
created: 2025-11-19
author: spec-builder
tags: [documentation, reorganization, cleanup, maintenance]
priority: HIGH
estimated_complexity: MEDIUM
---

## Resumo Executivo

Reorganizacao completa e atualizacao de toda a documentacao do projeto Skills-Eye, seguindo as diretrizes do ORGANIZATIONAL_GUIDE.md e estrutura definida no DOCUMENTATION_INDEX.md.

## Analise da Situacao Atual

### Metricas de Documentacao Encontradas

| Metrica | Valor | Status |
|---------|-------|--------|
| Total de arquivos .md no projeto | 223+ | Necessita organizacao |
| Arquivos .md na raiz de docs/ | 112 | CRITICO - Devem ser movidos |
| Arquivos em docs/features/ | 15 | OK |
| Arquivos em docs/obsolete/ | 43 | OK |
| Arquivos em docs/developer/corrections/ | 10 | OK |
| Arquivos em docs/developer/architecture/ | 8 | OK |
| Arquivos em docs/guides/ | 8 | Verificar |
| Arquivos em docs/api/ | 1 | Insuficiente |
| Arquivos em docs/performance/ | 7 | Verificar |
| Arquivos em docs/planning/ | 4 | Verificar |

### Problemas Identificados

1. **112 arquivos na raiz de docs/** - Violacao do principio de organizacao
2. **Documentacao potencialmente desatualizada** - Muitos documentos de analise/sprint antigos
3. **Duplicacao provavel** - Multiplos arquivos ANALISE_*, RELATORIO_*, CORRECOES_*
4. **Falta de estrutura clara** - Documentos misturados sem categoria

---

## Requisitos EARS

### Requisitos Ubiquos (Sempre Verdadeiros)

**REQ-UBI-001**: O sistema de documentacao DEVERA manter no maximo 10 arquivos .md na raiz do diretorio docs/.

**REQ-UBI-002**: O sistema DEVERA seguir a estrutura de pastas definida em ORGANIZATIONAL_GUIDE.md.

**REQ-UBI-003**: Todo documento .md DEVERA ter codigo correspondente OU ser marcado como obsoleto.

**REQ-UBI-004**: O sistema DEVERA manter um DOCUMENTATION_INDEX.md atualizado com todos os documentos.

**REQ-UBI-005**: Nenhum link interno DEVERA estar quebrado apos a reorganizacao.

### Requisitos Event-Driven (QUANDO Gatilho)

**REQ-EVT-001**: QUANDO um documento referencia codigo que nao existe mais, ENTAO o documento DEVERA ser movido para docs/obsolete/ com warning apropriado.

**REQ-EVT-002**: QUANDO dois ou mais documentos tratam do mesmo assunto, ENTAO DEVERAO ser mesclados no mais recente.

**REQ-EVT-003**: QUANDO um documento estiver desatualizado por mais de 6 meses, ENTAO DEVERA ser marcado com warning de desatualizacao.

**REQ-EVT-004**: QUANDO um arquivo for movido, ENTAO o git mv DEVERA ser usado para preservar historico.

### Requisitos Unwanted (SE Condicao Ruim ENTAO Prevenir)

**REQ-UNW-001**: SE um documento estiver vazio ou irrelevante, ENTAO DEVERA ser deletado do repositorio.

**REQ-UNW-002**: SE houver imports/caminhos incorretos nos documentos, ENTAO DEVERAO ser corrigidos antes do commit.

**REQ-UNW-003**: SE um documento contiver informacoes sensiveis (credenciais, tokens), ENTAO NAO DEVERA ser commitado.

### Requisitos State-Driven (ENQUANTO Estado)

**REQ-STD-001**: ENQUANTO a reorganizacao estiver em andamento, DEVERAO ser feitos commits incrementais por fase.

**REQ-STD-002**: ENQUANTO documentos estiverem sendo movidos, DEVERA existir um backup da estrutura original.

### Requisitos Opcionais (ONDE Escolha do Usuario)

**REQ-OPT-001**: ONDE o usuario solicitar, documentos muito antigos PODERAO ser permanentemente deletados em vez de movidos para obsolete/.

**REQ-OPT-002**: ONDE aplicavel, documentos PODERAO ser convertidos para formato mais moderno (Markdown estendido, Mermaid diagrams).

---

## Especificacoes Tecnicas

### Estrutura Alvo de Documentacao

```
docs/
├── README.md                    # Indice de documentacao
├── features/                    # Funcionalidades atuais (user-facing)
│   └── *.md                     # Documentos de features ativas
├── developer/                   # Para desenvolvedores
│   ├── architecture/            # Analises tecnicas
│   ├── corrections/             # Correcoes aplicadas
│   └── troubleshooting/         # Solucoes de problemas
├── guides/                      # Guias praticos
│   └── *.md                     # Tutoriais e how-tos
├── api/                         # Documentacao de API
│   └── *.md                     # Endpoints, schemas
├── performance/                 # Performance e otimizacoes
│   └── *.md                     # Relatorios de performance
├── planning/                    # Roadmap e planejamento
│   └── *.md                     # Planos futuros
├── obsolete/                    # Documentos antigos
│   └── *.md                     # Mantidos apenas para historico
├── history/                     # Historico de implementacoes
│   └── session-summaries/       # Resumos de sessoes
├── incidents/                   # Incidentes resolvidos
├── research/                    # Pesquisas tecnicas
├── ssh-optimization/            # Otimizacoes SSH
└── user/                        # Para usuarios finais
```

### Criterios de Classificacao

| Categoria | Criterios | Exemplos |
|-----------|-----------|----------|
| **features/** | Funcionalidades ativas, user-facing | NAMING_SYSTEM_COMPLETE.md |
| **developer/architecture/** | Analises tecnicas, decisoes de design | ANALISE_ARQUITETURA_*.md |
| **developer/corrections/** | Correcoes aplicadas, changelogs | CORRECOES_*.md, FIX_*.md |
| **guides/** | Tutoriais, how-tos, quick-starts | restart-guide.md, quick-start.md |
| **api/** | Documentacao de endpoints, schemas | API_DOCUMENTATION.md |
| **performance/** | Metricas, otimizacoes, benchmarks | RELATORIO_PERFORMANCE_*.md |
| **planning/** | Roadmaps, sprints, planos | SPRINT*_PLANO_*.md |
| **obsolete/** | Desatualizado, sem codigo correspondente | OLD_*.md, DEPRECATED_*.md |

### Criterios para Classificar como Obsoleto

1. Referencia codigo que nao existe mais no repositorio
2. Descreve processo antigo nao utilizado
3. Duplicado com documento mais recente
4. Marcado com TODO ha mais de 6 meses sem resolucao
5. Data de criacao superior a 6 meses sem atualizacao

---

## Rastreabilidade

### Dependencias

- ORGANIZATIONAL_GUIDE.md - Guia principal de organizacao
- DOCUMENTATION_INDEX.md - Indice atual a ser atualizado
- backend/ - Codigo fonte para validacao de referencias
- frontend/src/ - Codigo fonte para validacao de referencias

### Impactos

- README.md principal devera ser atualizado
- .gitignore pode precisar de ajustes
- Links externos em outros projetos podem quebrar (minor)

### TAGs de Rastreabilidade

```
<!-- TAG:SPEC-DOCS-001:START -->
<!-- TAG:SPEC-DOCS-001:END -->
```

---

## Notas de Implementacao

### Ferramentas Recomendadas

- `git mv` - Para mover arquivos preservando historico
- `grep -r` - Para buscar referencias a arquivos movidos
- `find` - Para localizar arquivos por padrao

### Ordem de Execucao Recomendada

1. **Backup**: Criar branch de backup antes de iniciar
2. **Analise**: Categorizar todos os 112 arquivos da raiz de docs/
3. **Organizacao**: Mover arquivos para estrutura alvo
4. **Atualizacao**: Atualizar referencias e links
5. **Limpeza**: Mesclar duplicados, remover vazios
6. **Validacao**: Verificar links, imports, referencias

### Riscos Identificados

| Risco | Probabilidade | Impacto | Mitigacao |
|-------|--------------|---------|-----------|
| Links quebrados apos movimentacao | Alta | Medio | Usar grep para atualizar referencias |
| Perda de historico git | Media | Alto | Sempre usar git mv |
| Documentos importantes marcados como obsoleto | Baixa | Alto | Revisao manual antes de mover |
| Commits muito grandes | Media | Baixo | Commits incrementais por fase |

---

## Validacao

### Criterios de Aceite Resumidos

1. Maximo 10 arquivos na raiz de docs/
2. Todos os 112 arquivos categorizados e movidos
3. DOCUMENTATION_INDEX.md atualizado
4. Nenhum link quebrado
5. README.md com nova estrutura
6. CHANGELOG-DOCS.md criado com todas mudancas

### Metricas de Sucesso

- Reducao de 112 para <=10 arquivos na raiz de docs/
- 100% dos documentos categorizados
- 0 links quebrados
- 0 imports incorretos

---

## Referencias

- [ORGANIZATIONAL_GUIDE.md](/home/adrianofante/projetos/Skills-Eye/ORGANIZATIONAL_GUIDE.md)
- [DOCUMENTATION_INDEX.md](/home/adrianofante/projetos/Skills-Eye/docs/DOCUMENTATION_INDEX.md)
- [Write the Docs - Documentation as Code](https://www.writethedocs.org/guide/docs-as-code/)
- [Best Practices for Monorepo Structure](https://monorepo.tools/)
