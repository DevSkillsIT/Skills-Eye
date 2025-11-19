# 🤖 Guia: Como Funcionam Múltiplos Agentes (Worktrees)

**Data:** 2025-11-17  
**Contexto:** Sistema de múltiplos agentes trabalhando em worktrees diferentes

---

## 📚 O Que São Worktrees?

**Worktree** = Árvore de trabalho separada do mesmo repositório Git

**Analogia:**
- **Repositório principal:** A biblioteca central
- **Worktree:** Uma cópia de trabalho separada (como ter 3 mesas diferentes para trabalhar no mesmo projeto)

**Vantagens:**
- ✅ Trabalhar em múltiplas branches simultaneamente
- ✅ Cada worktree tem seu próprio diretório
- ✅ Não precisa fazer `git checkout` para mudar de branch
- ✅ Múltiplos agentes podem trabalhar em paralelo

---

## 🔄 Como Funciona com Múltiplos Agentes?

### Cenário: 3 Agentes em 3 Worktrees

```
Repositório Git (mesmo código-fonte)
│
├── Worktree 1 (Agente 1)
│   └── Branch: dev-adriano
│       └── Mudanças: Correções Fase 0
│
├── Worktree 2 (Agente 2)
│   └── Branch: dev-adriano
│       └── Mudanças: Sprint 1 Backend
│
└── Worktree 3 (Agente 3)
    └── Branch: dev-adriano
        └── Mudanças: Outras funcionalidades
```

**O que acontece:**
1. Cada agente trabalha em seu próprio worktree
2. Cada agente faz commits independentes
3. Cada agente pode ter mudanças diferentes no mesmo arquivo
4. **Você precisa escolher/mergear as melhores mudanças**

---

## ⚠️ O Que Você Precisa Fazer?

### **NÃO há merge automático!**

Você precisa:
1. ✅ **Revisar** as mudanças de cada worktree
2. ✅ **Escolher** qual versão usar (ou combinar)
3. ✅ **Fazer merge manual** se necessário
4. ✅ **Testar** antes de commitar

---

## 📋 Processo Recomendado

### Passo 1: Identificar Worktrees e Mudanças

```bash
# Ver todos os worktrees
git worktree list

# Ver mudanças em cada worktree
cd /caminho/worktree1
git status
git diff

cd /caminho/worktree2
git status
git diff

cd /caminho/worktree3
git status
git diff
```

### Passo 2: Escolher Worktree Principal

**Estratégia 1: Escolher o melhor trabalho**
- Revisar mudanças de cada worktree
- Escolher o que tem as melhores implementações
- Usar esse como base

**Estratégia 2: Combinar o melhor de cada**
- Pegar mudanças específicas de cada worktree
- Combinar manualmente
- Testar tudo junto

### Passo 3: Fazer Merge (se necessário)

```bash
# No worktree principal
cd /caminho/worktree-principal

# Trazer mudanças de outro worktree
git fetch origin dev-adriano
git merge origin/dev-adriano

# OU trazer mudanças específicas
git cherry-pick <commit-hash-do-outro-worktree>
```

### Passo 4: Resolver Conflitos (se houver)

```bash
# Se houver conflitos
git status  # Ver arquivos com conflito
# Editar arquivos manualmente
# Resolver conflitos
git add arquivo-resolvido.py
git commit
```

---

## 🎯 Exemplo Prático: Seu Caso

### Situação Atual:

**Worktree 1 (808d5):**
- ✅ Fase 0 verificada e corrigida
- ✅ Sprint 1 Backend implementado
- ✅ Documentação criada

**Worktree 2 e 3:**
- Podem ter outras mudanças
- Podem ter mudanças conflitantes
- Podem ter melhorias adicionais

### O Que Fazer:

#### Opção 1: Usar Worktree 1 como Principal (Recomendado)

```bash
# 1. Verificar se worktree 1 está completo
cd /home/adrianofante/.cursor/worktrees/Skills-Eye__WSL__Ubuntu_/808d5
git status
git log --oneline -10

# 2. Ver mudanças dos outros worktrees
cd /caminho/worktree2
git diff origin/dev-adriano

cd /caminho/worktree3
git diff origin/dev-adriano

# 3. Se houver mudanças úteis nos outros, trazer para worktree 1
cd /home/adrianofante/.cursor/worktrees/Skills-Eye__WSL__Ubuntu_/808d5
git fetch origin dev-adriano
git merge origin/dev-adriano  # Ou cherry-pick específico
```

#### Opção 2: Combinar Melhorias

```bash
# 1. Identificar commits úteis de cada worktree
cd /caminho/worktree2
git log --oneline

cd /caminho/worktree3
git log --oneline

# 2. Trazer commits específicos para worktree principal
cd /home/adrianofante/.cursor/worktrees/Skills-Eye__WSL__Ubuntu_/808d5
git cherry-pick <commit-hash-1>
git cherry-pick <commit-hash-2>
```

---

## 🔍 Como Identificar Qual Worktree Usar?

### Checklist de Decisão:

1. **Qual tem mais mudanças completas?**
   - ✅ Worktree com implementações 100% funcionais

2. **Qual tem melhor qualidade de código?**
   - ✅ Worktree com menos bugs
   - ✅ Worktree com testes passando

3. **Qual tem documentação melhor?**
   - ✅ Worktree com documentação completa

4. **Qual tem menos conflitos?**
   - ✅ Worktree mais atualizado com main/dev

### No Seu Caso:

**Worktree 1 (808d5) parece ser o melhor porque:**
- ✅ Fase 0 completa e verificada
- ✅ Sprint 1 Backend completo
- ✅ Documentação criada
- ✅ Testes de baseline criados
- ✅ Código validado (sem erros de lint)

---

## 🛠️ Comandos Úteis

### Ver Diferenças Entre Worktrees

```bash
# Comparar worktree 1 com worktree 2
cd /caminho/worktree1
git diff /caminho/worktree2

# Ver commits únicos de cada worktree
cd /caminho/worktree1
git log origin/dev-adriano..HEAD  # Commits só neste worktree
```

### Trazer Mudanças Específicas

```bash
# Trazer arquivo específico de outro worktree
git checkout /caminho/worktree2 -- caminho/arquivo.py

# Trazer commit específico
git cherry-pick <commit-hash>
```

### Limpar Worktrees Não Usados

```bash
# Remover worktree (após mergear mudanças importantes)
git worktree remove /caminho/worktree-antigo
```

---

## ⚡ Resumo Rápido

1. **Múltiplos agentes = múltiplos worktrees**
2. **NÃO há merge automático** - você decide
3. **Revisar mudanças** de cada worktree
4. **Escolher o melhor** ou combinar
5. **Fazer merge manual** se necessário
6. **Testar tudo** antes de commitar

---

## 🎯 Recomendação para Seu Caso

**Use Worktree 1 (808d5) como principal porque:**
- ✅ Trabalho completo e verificado
- ✅ Documentação criada
- ✅ Código validado

**Depois:**
1. Verificar se outros worktrees têm melhorias úteis
2. Trazer apenas o que for relevante
3. Testar tudo junto
4. Fazer commit final

---

## 📝 Próximos Passos

1. ✅ Revisar mudanças do worktree 1 (808d5)
2. ⏳ Verificar mudanças dos outros worktrees
3. ⏳ Decidir se precisa trazer algo dos outros
4. ⏳ Fazer merge se necessário
5. ⏳ Testar tudo
6. ⏳ Fazer commit final

---

## ❓ Dúvidas Comuns

**P: Preciso usar todos os worktrees?**  
R: Não! Escolha o melhor e descarte os outros (após verificar se não há nada útil).

**P: E se houver conflitos?**  
R: Resolva manualmente, escolhendo a melhor solução ou combinando ambas.

**P: Posso deletar worktrees?**  
R: Sim, após garantir que as mudanças importantes foram mergeadas.

**P: Qual worktree é o "oficial"?**  
R: Não há um oficial. Você escolhe qual usar como base.

