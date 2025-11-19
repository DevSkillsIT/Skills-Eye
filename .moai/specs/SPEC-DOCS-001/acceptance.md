# Criterios de Aceitacao - SPEC-DOCS-001

---
spec_id: SPEC-DOCS-001
version: 1.0.0
status: draft
created: 2025-11-19
author: spec-builder
---

## Visao Geral

Este documento define os criterios de aceitacao detalhados para a reorganizacao completa da documentacao do projeto Skills-Eye. Cada criterio segue o formato Given-When-Then para clareza e testabilidade.

---

## Criterios de Aceitacao por Fase

### Fase 0: Preparacao

#### AC-F0-001: Branch de Backup Criado

**Given** que existe codigo e documentacao no estado atual
**When** o processo de reorganizacao e iniciado
**Then** um branch de backup `backup/docs-pre-reorganization` DEVE existir
**And** o branch DEVE estar pushed para o remote
**And** o branch DEVE conter exatamente o estado pre-reorganizacao

**Verificacao:**
```bash
git branch -a | grep "backup/docs-pre-reorganization"
# Deve retornar o branch
```

#### AC-F0-002: Branch de Trabalho Criado

**Given** que o branch de backup foi criado
**When** o trabalho de reorganizacao comeca
**Then** um branch `feature/SPEC-DOCS-001-reorganization` DEVE existir
**And** DEVE ser criado a partir de main/master

**Verificacao:**
```bash
git branch | grep "SPEC-DOCS-001"
```

#### AC-F0-003: Inventario Gerado

**Given** que existem 112 arquivos .md na raiz de docs/
**When** a analise inicial e executada
**Then** um arquivo de inventario DEVE ser gerado
**And** DEVE conter a lista completa dos 112 arquivos

---

### Fase 1: Analise e Categorizacao

#### AC-F1-001: Todos os Arquivos Categorizados

**Given** que existem 112 arquivos na raiz de docs/
**When** a analise de categorizacao e completada
**Then** cada arquivo DEVE ter uma categoria alvo definida
**And** a categoria DEVE ser uma das: features, developer/architecture, developer/corrections, guides, api, performance, planning, obsolete, ou manter na raiz

**Verificacao:**
```bash
# Contar arquivos por categoria planejada
# Total deve ser igual a 112
```

#### AC-F1-002: Documentos Obsoletos Identificados

**Given** que existem documentos antigos na raiz de docs/
**When** a verificacao de obsolescencia e executada
**Then** documentos que referenciam codigo inexistente DEVEM ser marcados como obsoletos
**And** documentos com mais de 6 meses sem atualizacao DEVEM ser avaliados

**Criterios de Obsolescencia:**
- Referencia arquivo que nao existe em backend/ ou frontend/
- Descreve feature removida
- Duplicado com versao mais recente
- TODO antigo sem resolucao (>6 meses)

#### AC-F1-003: Duplicatas Identificadas

**Given** que existem multiplos documentos sobre o mesmo assunto
**When** a analise de duplicacao e executada
**Then** pares/grupos de documentos duplicados DEVEM ser identificados
**And** o documento mais recente DEVE ser escolhido como principal

---

### Fase 2: Organizacao - Movimentacao

#### AC-F2-001: Estrutura de Diretorios Completa

**Given** que a estrutura alvo esta definida
**When** a organizacao comeca
**Then** todos os subdiretorios necessarios DEVEM existir:
- docs/developer/architecture/
- docs/developer/corrections/
- docs/developer/troubleshooting/
- docs/guides/
- docs/api/
- docs/performance/
- docs/planning/
- docs/obsolete/

**Verificacao:**
```bash
for dir in developer/architecture developer/corrections developer/troubleshooting guides api performance planning obsolete; do
  test -d "/home/adrianofante/projetos/Skills-Eye/docs/$dir" && echo "OK: $dir" || echo "FALTA: $dir"
done
```

#### AC-F2-002: Arquivos Movidos com Git MV

**Given** que um arquivo precisa ser movido
**When** a movimentacao e executada
**Then** o comando `git mv` DEVE ser usado
**And** o historico git DEVE ser preservado

**Anti-padrao (NAO fazer):**
```bash
# ERRADO - perde historico
mv docs/ARQUIVO.md docs/developer/architecture/
git add docs/developer/architecture/ARQUIVO.md
```

**Padrao correto:**
```bash
# CORRETO - preserva historico
git mv docs/ARQUIVO.md docs/developer/architecture/
```

#### AC-F2-003: Maximo 10 Arquivos na Raiz

**Given** que 112 arquivos existem na raiz de docs/
**When** a fase de organizacao e completada
**Then** no maximo 10 arquivos DEVEM permanecer na raiz de docs/
**And** estes DEVEM ser: README.md, DOCUMENTATION_INDEX.md, CLAUDE.md, e arquivos essenciais de navegacao

**Verificacao:**
```bash
RAIZ=$(find /home/adrianofante/projetos/Skills-Eye/docs -maxdepth 1 -type f -name "*.md" | wc -l)
[ $RAIZ -le 10 ] && echo "PASS: $RAIZ arquivos" || echo "FAIL: $RAIZ arquivos (max 10)"
```

#### AC-F2-004: Commits Organizados por Categoria

**Given** que multiplos arquivos serao movidos
**When** commits sao criados
**Then** cada commit DEVE ser organizado por categoria
**And** a mensagem DEVE seguir o padrao: `docs: mover arquivos de [categoria] para [destino]`

**Exemplo:**
```bash
git commit -m "docs: mover arquivos de arquitetura para developer/architecture

- Movidos 15 arquivos ANALISE_ARQUITETURA_*
- Preservado historico git

Ref: SPEC-DOCS-001"
```

---

### Fase 3: Reescrita e Atualizacao

#### AC-F3-001: Referencias Atualizadas

**Given** que arquivos foram movidos para novos caminhos
**When** a fase de reescrita e completada
**Then** todas as referencias internas DEVEM apontar para os novos caminhos
**And** nenhum documento DEVE referenciar caminhos antigos

**Verificacao:**
```bash
# Buscar referencias a caminhos antigos
grep -r "docs/ANALISE_" /home/adrianofante/projetos/Skills-Eye/docs --include="*.md"
# Deve retornar vazio (todas atualizadas)
```

#### AC-F3-002: Codigo Correspondente Validado

**Given** que um documento referencia codigo especifico
**When** a validacao e executada
**Then** o codigo referenciado DEVE existir em backend/ ou frontend/
**Or** o documento DEVE ser movido para obsolete/ com warning apropriado

**Verificacao:**
```bash
# Para cada documento, verificar se arquivos referenciados existem
# Exemplo: se doc menciona backend/api/servers.py, verificar existencia
```

#### AC-F3-003: Warnings Adicionados

**Given** que um documento esta desatualizado mas ainda e util
**When** nao e possivel atualizar completamente
**Then** um warning DEVE ser adicionado no topo do documento

**Formato do Warning:**
```markdown
> **AVISO**: Este documento pode estar desatualizado.
> Ultima atualizacao: YYYY-MM-DD
> Verificar codigo correspondente antes de usar.
```

#### AC-F3-004: Exemplos de Codigo Atualizados

**Given** que um documento contem exemplos de codigo
**When** a reescrita e executada
**Then** imports e caminhos nos exemplos DEVEM ser corrigidos
**And** versoes de dependencias DEVEM ser atualizadas onde aplicavel

---

### Fase 4: Limpeza e Consolidacao

#### AC-F4-001: Duplicatas Mescladas

**Given** que documentos duplicados foram identificados
**When** a limpeza e executada
**Then** o conteudo DEVE ser mesclado no documento mais recente
**And** o documento antigo DEVE ser deletado

#### AC-F4-002: Arquivos Vazios Removidos

**Given** que existem arquivos .md sem conteudo relevante
**When** a limpeza e executada
**Then** arquivos vazios ou com menos de 50 caracteres DEVEM ser deletados

**Verificacao:**
```bash
# Encontrar arquivos muito pequenos
find /home/adrianofante/projetos/Skills-Eye/docs -name "*.md" -size -50c
```

#### AC-F4-003: CHANGELOG-DOCS.md Criado

**Given** que multiplas mudancas foram feitas
**When** a limpeza e finalizada
**Then** um arquivo CHANGELOG-DOCS.md DEVE ser criado
**And** DEVE listar:
- Arquivos movidos (por categoria)
- Arquivos mesclados
- Arquivos deletados
- Referencias atualizadas

---

### Fase 5: Validacao e Finalizacao

#### AC-F5-001: Zero Links Quebrados

**Given** que a reorganizacao foi completada
**When** a validacao de links e executada
**Then** nenhum link interno DEVE estar quebrado
**And** todos os caminhos DEVEM resolver para arquivos existentes

**Verificacao:**
```bash
# Usar ferramenta como markdown-link-check ou script custom
# Exemplo com grep:
grep -r "\]\(./" /home/adrianofante/projetos/Skills-Eye/docs --include="*.md" | while read line; do
  # Verificar se arquivo existe
  echo "Validando: $line"
done
```

#### AC-F5-002: Zero Imports Incorretos

**Given** que documentos referenciam codigo fonte
**When** a validacao e executada
**Then** todos os imports/referencias de codigo DEVEM apontar para arquivos existentes

#### AC-F5-003: DOCUMENTATION_INDEX.md Atualizado

**Given** que arquivos foram reorganizados
**When** a validacao e completada
**Then** DOCUMENTATION_INDEX.md DEVE refletir a nova estrutura
**And** DEVE incluir todos os documentos em suas novas localizacoes
**And** todos os links DEVEM funcionar

#### AC-F5-004: README.md Atualizado

**Given** que a estrutura de documentacao mudou
**When** a finalizacao e completada
**Then** README.md principal DEVE ser atualizado
**And** DEVE incluir navegacao para nova estrutura de docs/

#### AC-F5-005: Pull Request Criado

**Given** que todas as fases foram completadas
**When** a finalizacao e executada
**Then** um PR DEVE ser criado para merge em main
**And** DEVE incluir resumo de todas as mudancas
**And** DEVE referenciar SPEC-DOCS-001

---

## Metricas de Quality Gate

### Criterios Obrigatorios (MUST PASS)

| ID | Criterio | Threshold | Status |
|----|----------|-----------|--------|
| QG-001 | Arquivos na raiz de docs/ | <= 10 | [ ] PASS |
| QG-002 | Links quebrados | = 0 | [ ] PASS |
| QG-003 | Imports incorretos | = 0 | [ ] PASS |
| QG-004 | Arquivos categorizados | = 100% | [ ] PASS |
| QG-005 | DOCUMENTATION_INDEX atualizado | = TRUE | [ ] PASS |
| QG-006 | README.md atualizado | = TRUE | [ ] PASS |
| QG-007 | CHANGELOG-DOCS.md criado | = TRUE | [ ] PASS |
| QG-008 | Branch de backup existe | = TRUE | [ ] PASS |

### Criterios Desejados (SHOULD PASS)

| ID | Criterio | Threshold | Status |
|----|----------|-----------|--------|
| QG-009 | Warnings em docs desatualizados | >= 90% | [ ] PASS |
| QG-010 | Exemplos de codigo atualizados | >= 80% | [ ] PASS |
| QG-011 | Commits organizados por categoria | = TRUE | [ ] PASS |
| QG-012 | Duplicatas mescladas | = 100% | [ ] PASS |

---

## Cenarios de Teste End-to-End

### Cenario 1: Navegacao por Perfil de Usuario

**Given** que sou um desenvolvedor novo no projeto
**When** eu acesso o README.md principal
**Then** eu DEVO encontrar links claros para documentacao de desenvolvedor
**And** eu DEVO conseguir navegar ate docs/developer/architecture em no maximo 2 cliques
**And** todos os links que eu clicar DEVEM funcionar

### Cenario 2: Busca por Documentacao de Feature

**Given** que preciso entender o sistema de naming
**When** eu busco por "naming" nos documentos
**Then** eu DEVO encontrar documentos em docs/features/
**And** o documento principal DEVE ser NAMING_SYSTEM_COMPLETE.md
**And** o documento NAO DEVE referenciar codigo inexistente

### Cenario 3: Acesso a Documentacao de Performance

**Given** que preciso otimizar performance
**When** eu navego para docs/performance/
**Then** eu DEVO encontrar documentos de analise e relatorios
**And** cada documento DEVE ter metricas validas
**And** referencias a codigo de backend/ DEVEM existir

### Cenario 4: Encontrar Correcoes Aplicadas

**Given** que preciso entender uma correcao anterior
**When** eu navego para docs/developer/corrections/
**Then** eu DEVO encontrar documentos CORRECOES_*.md
**And** cada documento DEVE ter data e descricao clara
**And** o codigo corrigido DEVE existir (ou warning se removido)

### Cenario 5: Acesso a Documentos Obsoletos

**Given** que preciso consultar documentacao historica
**When** eu navego para docs/obsolete/
**Then** eu DEVO encontrar documentos antigos
**And** cada documento DEVE ter warning de obsolescencia
**And** eu NAO DEVO usar esta documentacao como referencia atual

---

## Validacao Automatizada

### Script de Validacao Completa

```bash
#!/bin/bash
# validate-docs-reorganization.sh

echo "=== VALIDACAO SPEC-DOCS-001 ==="

# QG-001: Arquivos na raiz
RAIZ=$(find /home/adrianofante/projetos/Skills-Eye/docs -maxdepth 1 -type f -name "*.md" | wc -l)
if [ $RAIZ -le 10 ]; then
  echo "OK QG-001: Arquivos na raiz = $RAIZ (max 10)"
else
  echo "FAIL QG-001: Arquivos na raiz = $RAIZ (max 10)"
fi

# QG-005: DOCUMENTATION_INDEX existe e foi atualizado
if [ -f "/home/adrianofante/projetos/Skills-Eye/docs/DOCUMENTATION_INDEX.md" ]; then
  echo "OK QG-005: DOCUMENTATION_INDEX.md existe"
else
  echo "FAIL QG-005: DOCUMENTATION_INDEX.md NAO existe"
fi

# QG-007: CHANGELOG-DOCS existe
if [ -f "/home/adrianofante/projetos/Skills-Eye/docs/CHANGELOG-DOCS.md" ]; then
  echo "OK QG-007: CHANGELOG-DOCS.md existe"
else
  echo "FAIL QG-007: CHANGELOG-DOCS.md NAO existe"
fi

# QG-008: Branch de backup existe
if git branch -a | grep -q "backup/docs-pre-reorganization"; then
  echo "OK QG-008: Branch de backup existe"
else
  echo "FAIL QG-008: Branch de backup NAO existe"
fi

# Contagem por categoria
echo ""
echo "=== DISTRIBUICAO POR CATEGORIA ==="
for dir in features developer/architecture developer/corrections guides api performance planning obsolete; do
  COUNT=$(find /home/adrianofante/projetos/Skills-Eye/docs/$dir -type f -name "*.md" 2>/dev/null | wc -l)
  echo "$dir: $COUNT arquivos"
done

echo ""
echo "=== VALIDACAO COMPLETA ==="
```

---

## Definition of Done

A SPEC-DOCS-001 sera considerada COMPLETA quando:

- [ ] Todos os criterios obrigatorios (QG-001 a QG-008) passarem
- [ ] Pelo menos 80% dos criterios desejaveis passarem
- [ ] PR criado e aprovado
- [ ] Branch merged em main
- [ ] Branch de backup mantido por 30 dias

---

## Referencias

<!-- TAG:SPEC-DOCS-001:ACCEPTANCE:START -->
- spec.md: /home/adrianofante/projetos/Skills-Eye/.moai/specs/SPEC-DOCS-001/spec.md
- plan.md: /home/adrianofante/projetos/Skills-Eye/.moai/specs/SPEC-DOCS-001/plan.md
<!-- TAG:SPEC-DOCS-001:ACCEPTANCE:END -->
