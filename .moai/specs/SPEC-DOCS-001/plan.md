# Plano de Implementacao - SPEC-DOCS-001

---
spec_id: SPEC-DOCS-001
version: 1.0.0
status: draft
created: 2025-11-19
author: spec-builder
---

## Visao Geral do Plano

Este plano detalha a implementacao da reorganizacao completa da documentacao do projeto Skills-Eye em 5 fases distintas, com commits incrementais para facilitar rollback se necessario.

---

## Fase 0: Preparacao (Prioridade: CRITICA)

### Objetivo
Criar ambiente seguro para reorganizacao sem risco de perda de dados.

### Tarefas

| ID | Tarefa | Descricao | Dependencia |
|----|--------|-----------|-------------|
| F0-001 | Criar branch de backup | `git checkout -b backup/docs-pre-reorganization` | - |
| F0-002 | Commit estado atual | Garantir que tudo esta commitado | F0-001 |
| F0-003 | Criar branch de trabalho | `git checkout -b feature/SPEC-DOCS-001-reorganization` | F0-002 |
| F0-004 | Gerar inventario | Listar todos os 112 arquivos da raiz docs/ | F0-003 |
| F0-005 | Exportar lista de arquivos | Salvar em /tmp/docs-inventory.txt | F0-004 |

### Comandos Principais

```bash
# Backup branch
git checkout -b backup/docs-pre-reorganization
git push origin backup/docs-pre-reorganization

# Working branch
git checkout -b feature/SPEC-DOCS-001-reorganization

# Gerar inventario
find /home/adrianofante/projetos/Skills-Eye/docs -maxdepth 1 -type f -name "*.md" > /tmp/docs-inventory.txt
```

### Entregaveis
- [ ] Branch de backup criado e pushed
- [ ] Branch de trabalho criado
- [ ] Inventario de arquivos gerado

---

## Fase 1: Analise e Categorizacao (Prioridade: ALTA)

### Objetivo
Analisar cada um dos 112 arquivos e categoriza-los conforme estrutura alvo.

### Tarefas

| ID | Tarefa | Descricao | Dependencia |
|----|--------|-----------|-------------|
| F1-001 | Criar planilha de categorizacao | Arquivo com: nome, categoria alvo, status | F0-005 |
| F1-002 | Analisar documentos ANALISE_* | ~20 arquivos, categorizar como architecture ou obsolete | F1-001 |
| F1-003 | Analisar documentos RELATORIO_* | ~15 arquivos, categorizar como performance, planning ou obsolete | F1-001 |
| F1-004 | Analisar documentos CORRECOES_* | ~10 arquivos, mover para developer/corrections | F1-001 |
| F1-005 | Analisar documentos SPRINT_* | ~8 arquivos, categorizar como planning ou obsolete | F1-001 |
| F1-006 | Analisar documentos PLANO_* | ~5 arquivos, categorizar como planning | F1-001 |
| F1-007 | Analisar documentos GUIA_* | ~5 arquivos, mover para guides | F1-001 |
| F1-008 | Analisar documentos PROMPT_* | ~3 arquivos, avaliar se manter ou obsolete | F1-001 |
| F1-009 | Analisar documentos restantes | Categorizar individualmente | F1-002 a F1-008 |
| F1-010 | Validar codigo correspondente | Verificar se referencias a codigo existem | F1-009 |
| F1-011 | Finalizar categorizacao | Revisar e confirmar todas categorias | F1-010 |

### Criterios de Decisao

```markdown
## Arvore de Decisao para Categorizacao

1. O documento descreve uma FEATURE ativa?
   - SIM -> docs/features/
   - NAO -> continuar

2. O documento e uma ANALISE TECNICA?
   - SIM -> docs/developer/architecture/
   - NAO -> continuar

3. O documento descreve uma CORRECAO aplicada?
   - SIM -> docs/developer/corrections/
   - NAO -> continuar

4. O documento e um GUIA ou TUTORIAL?
   - SIM -> docs/guides/
   - NAO -> continuar

5. O documento e sobre PERFORMANCE?
   - SIM -> docs/performance/
   - NAO -> continuar

6. O documento e um PLANO ou SPRINT?
   - SIM -> docs/planning/
   - NAO -> continuar

7. O documento e sobre API/ENDPOINTS?
   - SIM -> docs/api/
   - NAO -> continuar

8. O documento esta DESATUALIZADO (>6 meses sem uso)?
   - SIM -> docs/obsolete/
   - NAO -> avaliar individualmente
```

### Entregaveis
- [ ] Planilha de categorizacao completa
- [ ] Todos os 112 arquivos categorizados
- [ ] Lista de arquivos para obsolete identificada
- [ ] Lista de arquivos duplicados identificada

---

## Fase 2: Organizacao - Movimentacao de Arquivos (Prioridade: ALTA)

### Objetivo
Mover todos os arquivos para suas categorias corretas usando git mv.

### Tarefas

| ID | Tarefa | Descricao | Dependencia |
|----|--------|-----------|-------------|
| F2-001 | Criar subdiretorios faltantes | Garantir que todas as pastas existem | F1-011 |
| F2-002 | Mover arquivos para developer/architecture | Arquivos ANALISE_ARQUITETURA_* | F2-001 |
| F2-003 | Mover arquivos para developer/corrections | Arquivos CORRECOES_*, FIX_* | F2-001 |
| F2-004 | Mover arquivos para guides | Arquivos GUIA_*, tutoriais | F2-001 |
| F2-005 | Mover arquivos para performance | Arquivos de performance e benchmarks | F2-001 |
| F2-006 | Mover arquivos para planning | Arquivos SPRINT_*, PLANO_* | F2-001 |
| F2-007 | Mover arquivos para api | Documentacao de API | F2-001 |
| F2-008 | Mover arquivos para obsolete | Arquivos desatualizados | F2-001 |
| F2-009 | Commit por categoria | Commit separado por tipo de movimentacao | F2-002 a F2-008 |

### Comandos de Movimentacao

```bash
# Exemplo de movimentacao preservando historico
git mv docs/ANALISE_ARQUITETURA_*.md docs/developer/architecture/
git mv docs/CORRECOES_*.md docs/developer/corrections/
git mv docs/GUIA_*.md docs/guides/
git mv docs/RELATORIO_PERFORMANCE_*.md docs/performance/
git mv docs/SPRINT_*.md docs/planning/
git mv docs/PLANO_*.md docs/planning/

# Commit por categoria
git commit -m "docs: mover arquivos de arquitetura para developer/architecture

- Movidos X arquivos ANALISE_ARQUITETURA_*
- Preservado historico git

Ref: SPEC-DOCS-001"
```

### Entregaveis
- [ ] Todos os arquivos movidos para estrutura alvo
- [ ] Commits organizados por categoria
- [ ] Maximo 10 arquivos na raiz de docs/

---

## Fase 3: Reescrita e Atualizacao (Prioridade: MEDIA)

### Objetivo
Atualizar conteudo dos documentos para refletir estado atual do codigo.

### Tarefas

| ID | Tarefa | Descricao | Dependencia |
|----|--------|-----------|-------------|
| F3-001 | Identificar referencias quebradas | Grep por imports/caminhos antigos | F2-009 |
| F3-002 | Atualizar caminhos em documentos | Corrigir referencias a arquivos movidos | F3-001 |
| F3-003 | Verificar codigo referenciado | Para cada doc, verificar se codigo existe | F3-002 |
| F3-004 | Adicionar warnings onde necessario | Marcar docs desatualizados com aviso | F3-003 |
| F3-005 | Atualizar exemplos de codigo | Corrigir snippets desatualizados | F3-003 |
| F3-006 | Atualizar versoes de dependencias | Onde aplicavel, atualizar versions | F3-005 |
| F3-007 | Remover referencias a features removidas | Limpar mencoes a codigo deletado | F3-006 |
| F3-008 | Commit de atualizacoes | Commit com todas as correcoes | F3-007 |

### Template de Warning para Documentos Desatualizados

```markdown
> **AVISO**: Este documento pode estar desatualizado.
> Ultima atualizacao: YYYY-MM-DD
> Verificar codigo correspondente antes de usar.
```

### Entregaveis
- [ ] Todas as referencias atualizadas
- [ ] Warnings adicionados onde necessario
- [ ] Exemplos de codigo validados

---

## Fase 4: Limpeza e Consolidacao (Prioridade: MEDIA)

### Objetivo
Mesclar documentos duplicados e limpar arquivos desnecessarios.

### Tarefas

| ID | Tarefa | Descricao | Dependencia |
|----|--------|-----------|-------------|
| F4-001 | Identificar duplicatas | Documentos sobre mesmo assunto | F3-008 |
| F4-002 | Mesclar documentos duplicados | Consolidar em documento unico mais recente | F4-001 |
| F4-003 | Deletar arquivos vazios | Remover docs sem conteudo relevante | F4-002 |
| F4-004 | Deletar arquivos irrelevantes | Remover temp files, drafts abandonados | F4-003 |
| F4-005 | Criar CHANGELOG-DOCS.md | Documentar todas as mudancas | F4-004 |
| F4-006 | Commit de limpeza | Commit com todas as remocoes | F4-005 |

### Template de CHANGELOG-DOCS.md

```markdown
# CHANGELOG-DOCS - Reorganizacao 2025-11-19

## Arquivos Movidos

### Para docs/developer/architecture/
- ANALISE_ARQUITETURA_*.md (X arquivos)
- ...

### Para docs/developer/corrections/
- CORRECOES_*.md (X arquivos)
- ...

### Para docs/obsolete/
- OLD_*.md (X arquivos)
- ...

## Arquivos Mesclados
- ANALISE_A.md + ANALISE_B.md -> ANALISE_CONSOLIDATED.md

## Arquivos Deletados
- arquivo_vazio.md (motivo: sem conteudo)
- ...

## Referencias Atualizadas
- Total de links corrigidos: X
- Documentos com warnings: Y

---
Ref: SPEC-DOCS-001
```

### Entregaveis
- [ ] Duplicatas mescladas
- [ ] Arquivos vazios removidos
- [ ] CHANGELOG-DOCS.md criado
- [ ] Commit de limpeza

---

## Fase 5: Validacao e Finalizacao (Prioridade: ALTA)

### Objetivo
Validar toda a reorganizacao e atualizar documentacao indice.

### Tarefas

| ID | Tarefa | Descricao | Dependencia |
|----|--------|-----------|-------------|
| F5-001 | Verificar links internos | Testar todos os links em docs | F4-006 |
| F5-002 | Verificar imports | Garantir que nenhum import esta quebrado | F5-001 |
| F5-003 | Contar arquivos na raiz | Garantir <= 10 arquivos | F5-002 |
| F5-004 | Atualizar DOCUMENTATION_INDEX.md | Refletir nova estrutura | F5-003 |
| F5-005 | Atualizar README.md principal | Adicionar nova navegacao | F5-004 |
| F5-006 | Validacao final | Executar checklist completo | F5-005 |
| F5-007 | Commit final | Commit com atualizacoes de indice | F5-006 |
| F5-008 | PR para main | Criar Pull Request com resumo | F5-007 |

### Checklist de Validacao Final

```bash
# 1. Contar arquivos na raiz de docs/
RAIZ=$(find /home/adrianofante/projetos/Skills-Eye/docs -maxdepth 1 -type f -name "*.md" | wc -l)
echo "Arquivos na raiz: $RAIZ (maximo: 10)"
[ $RAIZ -le 10 ] && echo "OK" || echo "ERRO"

# 2. Verificar links quebrados
# (usar ferramenta como markdown-link-check)

# 3. Verificar estrutura
ls -la /home/adrianofante/projetos/Skills-Eye/docs/

# 4. Contar total por categoria
for dir in features developer/architecture developer/corrections guides api performance planning obsolete; do
  echo "$dir: $(find /home/adrianofante/projetos/Skills-Eye/docs/$dir -type f -name '*.md' 2>/dev/null | wc -l)"
done
```

### Entregaveis
- [ ] 0 links quebrados
- [ ] 0 imports incorretos
- [ ] <= 10 arquivos na raiz de docs/
- [ ] DOCUMENTATION_INDEX.md atualizado
- [ ] README.md atualizado
- [ ] PR criado e revisado

---

## Cronograma Estimado

| Fase | Duracao Estimada | Dependencia |
|------|-----------------|-------------|
| Fase 0: Preparacao | 15 minutos | - |
| Fase 1: Analise | 1-2 horas | Fase 0 |
| Fase 2: Organizacao | 30-45 minutos | Fase 1 |
| Fase 3: Reescrita | 1-2 horas | Fase 2 |
| Fase 4: Limpeza | 30-45 minutos | Fase 3 |
| Fase 5: Validacao | 30 minutos | Fase 4 |
| **TOTAL** | **4-6 horas** | - |

---

## Riscos e Mitigacoes

| Risco | Probabilidade | Impacto | Mitigacao |
|-------|--------------|---------|-----------|
| Links quebrados pos-movimentacao | Alta | Medio | Usar grep para encontrar e atualizar todas referencias |
| Perda de historico git | Media | Alto | SEMPRE usar git mv, nunca rm + add |
| Documento importante classificado como obsoleto | Baixa | Alto | Revisao manual, validar codigo correspondente |
| Commits muito grandes | Media | Baixo | Commits incrementais por categoria |
| Conflitos de merge | Baixa | Medio | Branch dedicado, merge frequente |

---

## Metricas de Sucesso

### Quantitativas

- **Arquivos na raiz de docs/**: De 112 para <= 10
- **Arquivos categorizados**: 100%
- **Links quebrados**: 0
- **Imports incorretos**: 0

### Qualitativas

- Navegacao intuitiva por perfil (Dev/QA/DevOps/User)
- Documentacao reflete estado atual do codigo
- Facilidade de encontrar informacoes
- Estrutura consistente com ORGANIZATIONAL_GUIDE.md

---

## Referencias

<!-- TAG:SPEC-DOCS-001:PLAN:START -->
- spec.md: /home/adrianofante/projetos/Skills-Eye/.moai/specs/SPEC-DOCS-001/spec.md
- acceptance.md: /home/adrianofante/projetos/Skills-Eye/.moai/specs/SPEC-DOCS-001/acceptance.md
<!-- TAG:SPEC-DOCS-001:PLAN:END -->
