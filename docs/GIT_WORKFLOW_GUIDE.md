# 📚 Guia Completo de Workflow Git - Skills Eye

> **Autor:** DevSkillsIT
> **Última Atualização:** 06 de Novembro de 2025
> **Projeto:** Skills Eye (antigo Consul Manager Web)

---

## 📋 Índice

1. [Estrutura de Branches](#-estrutura-de-branches)
2. [Workflow Diário](#-workflow-diário)
3. [Boas Práticas de Commits](#-boas-práticas-de-commits)
4. [Pull Requests](#-pull-requests)
5. [Comandos Essenciais](#-comandos-essenciais)
6. [Resolução de Conflitos](#-resolução-de-conflitos)
7. [O Que NUNCA Fazer](#-o-que-nunca-fazer)
8. [Troubleshooting](#-troubleshooting)

---

## 🌳 Estrutura de Branches

### **Arquitetura de Branches do Projeto**

```
main (PRODUÇÃO)
  ↑
  └── dev (DESENVOLVIMENTO GERAL)
       ↑
       ├── dev-adriano (TRABALHO PESSOAL)
       ├── feature/nova-funcionalidade
       ├── feature/correcao-bug
       └── hotfix/correcao-urgente
```

### **Descrição das Branches**

#### **1. `main` - Branch Principal (PRODUÇÃO)**

- ✅ Código **100% estável e testado**
- ✅ Sempre pronto para deploy em produção
- ✅ Todo código aqui passou por revisão (Pull Request)
- ⛔ **NUNCA commitar diretamente nela**
- ⛔ **NUNCA fazer force push**
- 🔒 **Protegida:** Só aceita código via Pull Request

**Quando usar:**
- Apenas para receber código aprovado de `dev` ou `hotfix`

---

#### **2. `dev` - Branch de Desenvolvimento**

- ✅ Integração de todas as funcionalidades em desenvolvimento
- ✅ Código funcional mas pode ter bugs
- ✅ Testes acontecem aqui antes de ir para produção
- ⛔ **Não trabalhar diretamente nela**
- ✅ Recebe código de branches `dev-*` e `feature/*`

**Quando usar:**
- Para integrar funcionalidades antes de enviar para produção

---

#### **3. `dev-adriano` - Branch de Trabalho Pessoal**

- ✅ **Seu espaço de trabalho diário**
- ✅ Commits frequentes e experimentação
- ✅ Pode quebrar temporariamente (está em desenvolvimento)
- ✅ Quando estável → envia para `dev` via Pull Request
- ✅ Sempre baseada na `main` ou `dev`

**Quando usar:**
- **TODO o trabalho diário acontece aqui**
- Desenvolvimento de funcionalidades
- Testes e experimentações
- Correções de bugs

---

#### **4. `feature/*` - Branches de Funcionalidades**

- ✅ Para funcionalidades grandes e específicas
- ✅ Exemplos: `feature/autenticacao`, `feature/dashboard-v2`
- ✅ Criada a partir de `dev`
- ✅ Merge de volta para `dev` quando completa

**Quando usar:**
- Funcionalidades que levam vários dias
- Features que precisam de revisão isolada
- Quando vários desenvolvedores trabalham em partes diferentes

**Como criar:**
```bash
git checkout dev
git pull origin dev
git checkout -b feature/nome-da-funcionalidade
git push -u origin feature/nome-da-funcionalidade
```

---

#### **5. `hotfix/*` - Correções Urgentes**

- 🔥 Para bugs críticos em produção
- ✅ Criada direto da `main`
- ✅ Merge de volta para `main` E `dev`
- ⚡ Deploy imediato após aprovação

**Quando usar:**
- Aplicação quebrada em produção
- Bug crítico que afeta usuários
- Vulnerabilidade de segurança

**Como criar:**
```bash
git checkout main
git pull origin main
git checkout -b hotfix/correcao-critica
# ... fazer correção ...
git push -u origin hotfix/correcao-critica
# Criar PR para main E dev
```

---

## 🚀 Workflow Diário

### **Cenário 1: Começando o Dia**

```bash
# 1. Certifique-se que está no seu branch
git checkout dev-adriano

# 2. Atualize com possíveis mudanças
git pull origin dev-adriano

# 3. (Opcional) Atualize com a main se houve mudanças
git fetch origin main
git merge origin/main

# 4. Comece a trabalhar!
```

---

### **Cenário 2: Durante o Desenvolvimento**

```bash
# 1. Verifique o que mudou
git status

# 2. Veja as diferenças no código
git diff

# 3. Adicione arquivos específicos
git add caminho/arquivo.py
git add caminho/outro-arquivo.tsx

# OU adicione todos os arquivos modificados
git add .

# 4. Faça commit com mensagem descritiva
git commit -m "feat: Adicionar filtro avançado de busca"

# 5. Envie para o GitHub
git push origin dev-adriano
```

---

### **Cenário 3: Fim do Dia / Salvando Trabalho**

```bash
# Mesmo que não esteja 100% pronto, salve seu progresso

git add .
git commit -m "wip: Implementando autenticação (em progresso)"
git push origin dev-adriano

# "wip" = Work In Progress (trabalho em andamento)
```

---

### **Cenário 4: Funcionalidade Pronta → Enviar para DEV/MAIN**

```bash
# 1. Certifique-se que está tudo commitado
git status

# 2. Atualize seu branch com a main
git checkout main
git pull origin main
git checkout dev-adriano
git merge main

# 3. Se houver conflitos, resolva (ver seção de conflitos)

# 4. Teste tudo novamente após o merge

# 5. Envie para o GitHub
git push origin dev-adriano

# 6. Vá no GitHub e crie Pull Request:
#    https://github.com/DevSkillsIT/Skills-Eye/compare/main...dev-adriano

# 7. Aguarde revisão e aprovação

# 8. Após merge, atualize seu branch local
git checkout main
git pull origin main
git checkout dev-adriano
git merge main
```

---

## ✅ Boas Práticas de Commits

### **Padrão Conventional Commits**

Usamos o padrão de mensagens que facilita entender o histórico:

```
<tipo>(<escopo>): <descrição curta>

[corpo opcional: explicação detalhada]

[rodapé opcional: breaking changes, issues relacionadas]
```

### **Tipos de Commit**

| Tipo | Uso | Exemplo |
|------|-----|---------|
| `feat:` | Nova funcionalidade | `feat: Adicionar autenticação JWT` |
| `fix:` | Correção de bug | `fix: Corrigir erro ao deletar serviço` |
| `docs:` | Documentação | `docs: Atualizar README com setup inicial` |
| `style:` | Formatação, ponto e vírgula | `style: Formatar código com Prettier` |
| `refactor:` | Refatoração sem mudar funcionalidade | `refactor: Extrair lógica de validação` |
| `perf:` | Melhoria de performance | `perf: Otimizar query de busca avançada` |
| `test:` | Adicionar/corrigir testes | `test: Adicionar testes para BlackboxManager` |
| `build:` | Sistema de build, dependências | `build: Atualizar React para versão 19` |
| `ci:` | Integração contínua | `ci: Adicionar GitHub Actions workflow` |
| `chore:` | Tarefas gerais | `chore: Limpar arquivos __pycache__` |
| `revert:` | Reverter commit anterior | `revert: Reverter "feat: Nova API"` |
| `wip:` | Trabalho em progresso | `wip: Implementando dashboard (50%)` |

### **Exemplos de Boas Mensagens**

✅ **FAÇA:**

```bash
git commit -m "feat: Adicionar filtro de busca avançada com 12 operadores"
git commit -m "fix: Corrigir erro 403 ao deletar blackbox target"
git commit -m "docs: Adicionar guia de workflow Git"
git commit -m "refactor: Extrair lógica SSH para classe separada"
git commit -m "perf: Reduzir tempo de carregamento do dashboard em 60%"
```

✅ **Com descrição detalhada:**

```bash
git commit -m "feat: Adicionar autenticação Basic Auth para instaladores

- Implementado middleware de autenticação
- Credenciais armazenadas em Consul KV
- Endpoints /installer/* agora protegidos
- Adicionado hash bcrypt para senhas

Closes #45"
```

⛔ **EVITE:**

```bash
git commit -m "mudanças"
git commit -m "fix"
git commit -m "atualizações"
git commit -m "teste"
git commit -m "arrumei umas coisas"
git commit -m "commit"
```

### **Regras de Ouro para Commits**

1. ✅ **Commits frequentes** - Várias vezes ao dia, não espere terminar tudo
2. ✅ **Commits atômicos** - Cada commit é uma unidade lógica de trabalho
3. ✅ **Mensagem clara** - Qualquer pessoa deve entender o que foi feito
4. ✅ **Presente do indicativo** - "Adicionar" não "Adicionado" ou "Adicionando"
5. ✅ **Primeira linha < 72 caracteres** - Resumo curto e direto
6. ⛔ **Não commitar arquivos gerados** - `__pycache__`, `node_modules`, `.env`
7. ⛔ **Não commitar credenciais** - Tokens, senhas, chaves API

---

## 🔄 Pull Requests

### **O Que É Um Pull Request (PR)?**

Pull Request é uma **solicitação de revisão de código** antes de integrar mudanças em uma branch importante (como `main` ou `dev`).

### **Quando Criar Um PR?**

- ✅ Funcionalidade completa e testada
- ✅ Correção de bug verificada
- ✅ Refatoração significativa
- ✅ Qualquer mudança que vai para `main` ou `dev`

### **Como Criar Um PR no GitHub**

#### **Método 1: Via Interface Web**

1. Acesse: https://github.com/DevSkillsIT/Skills-Eye
2. Clique em **"Pull requests"** → **"New pull request"**
3. Selecione:
   - **Base:** `main` (para onde vai)
   - **Compare:** `dev-adriano` (de onde vem)
4. Clique **"Create pull request"**
5. Preencha:
   - **Título:** Resumo claro do que foi feito
   - **Descrição:** Detalhes, screenshots, testes realizados
6. Clique **"Create pull request"**

#### **Método 2: Via Link do Git Push**

Após fazer `git push`, o Git mostra um link:

```bash
git push origin dev-adriano

# Saída:
remote: Create a pull request for 'dev-adriano' on GitHub by visiting:
remote:   https://github.com/DevSkillsIT/Skills-Eye/pull/new/dev-adriano
```

Copie e cole esse link no navegador!

### **Template de Pull Request**

```markdown
## 📝 Descrição

Breve descrição do que foi implementado/corrigido.

## 🎯 Motivação

Por que essa mudança é necessária?

## 🔧 Mudanças Realizadas

- Adicionado X
- Corrigido Y
- Refatorado Z

## 🧪 Como Testar

1. Execute `npm install`
2. Rode `npm run dev`
3. Acesse http://localhost:8081
4. Verifique que...

## 📸 Screenshots (se aplicável)

[Cole screenshots aqui]

## ✅ Checklist

- [ ] Código testado localmente
- [ ] Documentação atualizada
- [ ] Sem conflitos com main
- [ ] Commits seguem padrão Conventional Commits
```

### **Fluxo de Aprovação**

1. **Você cria** o Pull Request
2. **Revisor analisa** o código (pode ser você mesmo em projetos pequenos)
3. **Feedback** é dado (se necessário)
4. **Correções** são feitas (se necessário)
5. **Aprovação** é dada
6. **Merge** é feito para a branch de destino
7. **Branch é deletada** (opcional, para limpeza)

### **Comandos Úteis Após PR Aprovado**

```bash
# Após merge do PR, atualize seu branch local
git checkout main
git pull origin main

# Volte para seu branch e atualize
git checkout dev-adriano
git merge main

# Ou delete seu branch e crie novo
git branch -D dev-adriano
git checkout -b dev-adriano main
git push -u origin dev-adriano
```

---

## 🛠️ Comandos Essenciais

### **Comandos Básicos**

```bash
# Ver status dos arquivos
git status

# Ver histórico de commits
git log
git log --oneline        # Resumido
git log --graph --all    # Visual com branches

# Ver diferenças
git diff                 # Mudanças não staged
git diff --staged        # Mudanças staged
git diff main           # Diferenças com main

# Ver branches
git branch              # Locais
git branch -r           # Remotas
git branch -a           # Todas
git branch -vv          # Com tracking info

# Criar branch
git checkout -b nova-branch
git switch -c nova-branch    # Alternativa moderna

# Mudar de branch
git checkout dev-adriano
git switch dev-adriano       # Alternativa moderna

# Deletar branch
git branch -d nome-branch    # Safe (só se mergeada)
git branch -D nome-branch    # Force (cuidado!)

# Deletar branch remota
git push origin --delete nome-branch
```

### **Comandos de Sincronização**

```bash
# Baixar mudanças do remoto (não aplica)
git fetch origin

# Baixar e aplicar mudanças
git pull origin dev-adriano

# Enviar mudanças
git push origin dev-adriano

# Primeira vez enviando branch nova
git push -u origin dev-adriano
```

### **Comandos de Staging**

```bash
# Adicionar arquivos específicos
git add arquivo.py
git add pasta/

# Adicionar todos arquivos modificados
git add .

# Adicionar interativamente (escolher pedaços)
git add -p

# Remover do staging (antes do commit)
git reset HEAD arquivo.py

# Descartar mudanças locais
git restore arquivo.py
git checkout -- arquivo.py    # Antiga forma
```

### **Comandos de Commit**

```bash
# Commit simples
git commit -m "feat: Nova funcionalidade"

# Commit com descrição detalhada
git commit -m "feat: Nova funcionalidade" -m "Descrição detalhada aqui"

# Commit abrindo editor
git commit

# Emendar último commit (cuidado!)
git commit --amend -m "Nova mensagem"

# Adicionar arquivos ao último commit
git add arquivo-esquecido.py
git commit --amend --no-edit
```

### **Comandos de Merge**

```bash
# Trazer mudanças de outra branch
git merge main

# Merge com estratégia específica
git merge --no-ff feature/nova-func    # Sempre cria commit de merge
git merge --ff-only main               # Só se for fast-forward

# Abortar merge com conflitos
git merge --abort
```

### **Comandos de Desfazer**

```bash
# Desfazer último commit (mantém mudanças)
git reset --soft HEAD~1

# Desfazer último commit (descarta mudanças)
git reset --hard HEAD~1

# Desfazer commit específico criando novo commit
git revert <commit-hash>

# Voltar arquivo para estado de commit específico
git restore --source=<commit-hash> arquivo.py

# Limpar arquivos não rastreados
git clean -n    # Preview
git clean -f    # Executar
git clean -fd   # Incluir diretórios
```

### **Comandos de Stash (Guardar Temporariamente)**

```bash
# Guardar mudanças temporariamente
git stash
git stash save "Descrição das mudanças"

# Listar stashes
git stash list

# Aplicar último stash
git stash apply
git stash pop    # Aplica e remove da lista

# Aplicar stash específico
git stash apply stash@{0}

# Deletar stash
git stash drop stash@{0}
git stash clear    # Limpar todos
```

### **Comandos de Informação**

```bash
# Ver configurações
git config --list
git config user.name
git config user.email

# Ver remotes
git remote -v
git remote show origin

# Ver arquivo em commit específico
git show <commit-hash>:caminho/arquivo.py

# Ver quem modificou cada linha
git blame arquivo.py

# Buscar em commits
git log --grep="palavra-chave"
git log -S"função_especifica"    # Buscar por código
```

---

## ⚔️ Resolução de Conflitos

### **O Que É Um Conflito?**

Conflito ocorre quando duas branches modificam a **mesma linha** de um arquivo e o Git não sabe qual mudança manter.

### **Quando Acontecem Conflitos?**

- Durante `git merge`
- Durante `git pull` (que faz merge automático)
- Durante `git rebase`

### **Como Identificar Conflitos**

```bash
git merge main

# Saída:
Auto-merging backend/app.py
CONFLICT (content): Merge conflict in backend/app.py
Automatic merge failed; fix conflicts and then commit the result.
```

### **Como Resolver Conflitos**

#### **Passo 1: Ver arquivos com conflito**

```bash
git status

# Saída:
On branch dev-adriano
You have unmerged paths.
  (fix conflicts and run "git commit")

Unmerged paths:
  (use "git add <file>..." to mark resolution)
        both modified:   backend/app.py
```

#### **Passo 2: Abrir arquivo e ver marcações**

O Git marca conflitos assim:

```python
@app.get("/")
def read_root():
<<<<<<< HEAD
    # Sua mudança no dev-adriano
    return {"message": "Skills Eye API v2.0"}
=======
    # Mudança que veio da main
    return {"message": "Consul Manager API v1.5"}
>>>>>>> main
```

**Explicação:**
- `<<<<<<< HEAD` → Início do seu código (branch atual)
- `=======` → Separador
- `>>>>>>> main` → Código da branch que está sendo mergeada

#### **Passo 3: Decidir o que manter**

Edite o arquivo e escolha:

**Opção A: Manter apenas sua versão**
```python
@app.get("/")
def read_root():
    return {"message": "Skills Eye API v2.0"}
```

**Opção B: Manter apenas versão da main**
```python
@app.get("/")
def read_root():
    return {"message": "Consul Manager API v1.5"}
```

**Opção C: Manter ambas (refatorar)**
```python
@app.get("/")
def read_root():
    # Novo nome do projeto
    app_name = "Skills Eye"
    version = "2.0"
    return {"message": f"{app_name} API v{version}"}
```

**IMPORTANTE:** Remova TODAS as marcações do Git (`<<<<<<<`, `=======`, `>>>>>>>`)

#### **Passo 4: Marcar como resolvido**

```bash
# Adicionar arquivo resolvido
git add backend/app.py

# Verificar se todos conflitos foram resolvidos
git status

# Se tudo OK, finalizar o merge
git commit -m "merge: Integrar mudanças da main para dev-adriano"
```

#### **Passo 5: Enviar**

```bash
git push origin dev-adriano
```

### **Ferramentas Visuais para Conflitos**

```bash
# Usar ferramenta de merge configurada
git mergetool

# Ferramentas recomendadas:
# - VSCode (built-in)
# - Beyond Compare
# - KDiff3
# - P4Merge
```

### **Abortar Merge em Caso de Problema**

```bash
# Se ficou confuso e quer recomeçar
git merge --abort

# Volta ao estado antes do merge
```

---

## ⛔ O Que NUNCA Fazer

### **1. NUNCA Force Push em Branches Compartilhadas**

❌ **PROIBIDO:**
```bash
git push --force origin main
git push --force origin dev
```

✅ **PERMITIDO:**
```bash
# Apenas no SEU branch pessoal se necessário
git push --force origin dev-adriano
```

**Por quê?** Force push reescreve histórico e pode apagar commits de outras pessoas.

---

### **2. NUNCA Commitar Credenciais**

❌ **NUNCA COMMITE:**
- Arquivos `.env` com senhas
- Tokens de API
- Chaves privadas SSH
- Senhas hardcoded no código
- Arquivos `credentials.json`

✅ **Use `.gitignore`:**
```bash
# Adicione ao .gitignore
.env
*.key
credentials.json
secrets/
```

**Se já commitou credenciais por engano:**
```bash
# Remove do histórico (perigoso, use com cuidado)
git filter-branch --force --index-filter \
  "git rm --cached --ignore-unmatch caminho/arquivo-com-senha.txt" \
  --prune-empty --tag-name-filter cat -- --all

# DEPOIS: Mude as credenciais vazadas!
```

---

### **3. NUNCA Commitar Arquivos Gerados**

❌ **NUNCA COMMITE:**
- `__pycache__/`
- `node_modules/`
- `dist/` ou `build/`
- `.vscode/` ou `.idea/` (configurações pessoais de IDE)
- Logs (`*.log`)
- Arquivos compilados (`.pyc`, `.class`, etc)

✅ **Adicione ao `.gitignore`:**
```bash
# Python
__pycache__/
*.py[cod]
*.egg-info/
venv/
.env

# Node
node_modules/
dist/
.vite/
npm-debug.log

# IDEs
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db
```

---

### **4. NUNCA Rebase Branches Públicas**

❌ **PROIBIDO:**
```bash
git checkout main
git rebase outra-branch
```

✅ **Use merge:**
```bash
git checkout main
git merge outra-branch
```

**Por quê?** Rebase reescreve histórico. Em branches compartilhadas isso causa problemas para todos.

---

### **5. NUNCA Commitar Código Quebrado na Main**

❌ **EVITE:**
- Código que não compila
- Testes falhando
- Funcionalidades pela metade
- TODOs críticos

✅ **FAÇA:**
- Teste antes de fazer PR
- Execute build local
- Rode testes
- Verifique que tudo funciona

---

### **6. NUNCA Usar Reset Hard em Branches Compartilhadas**

❌ **PERIGOSO:**
```bash
git checkout main
git reset --hard HEAD~3
git push --force
```

**Por quê?** Apaga commits do histórico. Pode perder trabalho de outras pessoas.

---

### **7. NUNCA Ignorar Conflitos**

❌ **ERRADO:**
- Aceitar mudanças sem revisar
- Deixar marcações de conflito no código
- Commitar sem testar após resolver conflito

✅ **CORRETO:**
- Entender ambas mudanças
- Testar código após resolver
- Revisar cuidadosamente cada conflito

---

## 🔧 Troubleshooting

### **Problema: "Permission denied" ao fazer push**

```bash
remote: Permission to DevSkillsIT/Skills-Eye.git denied
fatal: unable to access 'https://github.com/...': The requested URL returned error: 403
```

**Solução:**

```bash
# 1. Verificar credenciais
git config user.name
git config user.email

# 2. Usar token de acesso pessoal
# Criar token em: https://github.com/settings/tokens
# Usar token como senha ao fazer push

# 3. Ou configurar remote com token
git remote set-url origin https://TOKEN@github.com/DevSkillsIT/Skills-Eye.git

# 4. Configurar credential helper
git config --global credential.helper store
```

---

### **Problema: Esqueci de criar branch, trabalhei direto na main**

```bash
# Você está na main e já fez mudanças (mas não commitou)

# Solução:
git stash                      # Guarda mudanças
git checkout -b dev-adriano    # Cria branch correto
git stash pop                  # Restaura mudanças
git add .
git commit -m "feat: Minha funcionalidade"
git push -u origin dev-adriano
```

---

### **Problema: Fiz commit no branch errado**

```bash
# Commitou na main mas deveria ser no dev-adriano

# Solução 1: Mover último commit
git log --oneline -1           # Copiar hash do commit
git checkout dev-adriano
git cherry-pick <hash-do-commit>
git checkout main
git reset --hard HEAD~1        # Remove da main

# Solução 2: Criar branch do ponto atual
git branch dev-adriano         # Cria branch mantendo commits
git reset --hard origin/main   # Volta main para origem
git checkout dev-adriano       # Volta para trabalho
```

---

### **Problema: Quero desfazer último commit**

```bash
# Caso 1: Desfazer mas manter mudanças
git reset --soft HEAD~1
# Mudanças voltam para staging area

# Caso 2: Desfazer e descartar tudo
git reset --hard HEAD~1
# CUIDADO: Perde as mudanças!

# Caso 3: Criar commit reverso (mais seguro)
git revert HEAD
# Cria novo commit que desfaz o anterior
```

---

### **Problema: Conflito de merge muito complicado**

```bash
# Abortar e recomeçar
git merge --abort

# Estratégia alternativa: Rebase
git rebase main

# Ou pedir ajuda visual
git mergetool
```

---

### **Problema: Branch local desatualizada**

```bash
# Forçar atualização com remoto (perde mudanças locais!)
git fetch origin
git reset --hard origin/dev-adriano

# Ou atualizar preservando mudanças locais
git stash
git pull origin dev-adriano
git stash pop
```

---

### **Problema: Muitos arquivos não rastreados**

```bash
# Ver o que seria deletado
git clean -n

# Deletar arquivos não rastreados
git clean -f

# Deletar arquivos E diretórios
git clean -fd

# Incluir arquivos ignorados
git clean -fdx
```

---

### **Problema: Ver o que mudou antes de commitar**

```bash
# Ver diferenças gerais
git diff

# Ver diferenças de arquivo específico
git diff backend/app.py

# Ver o que está staged
git diff --staged

# Ver estatísticas
git diff --stat
```

---

### **Problema: Encontrar quando bug foi introduzido**

```bash
# Git bisect - busca binária em commits
git bisect start
git bisect bad                  # Commit atual tem bug
git bisect good <hash-bom>      # Commit antigo sem bug

# Git vai testando e você marca:
# git bisect good  (se não tem bug)
# git bisect bad   (se tem bug)

# Quando encontrar:
git bisect reset
```

---

## 📚 Recursos Adicionais

### **Documentação Oficial**

- Git: https://git-scm.com/doc
- GitHub Docs: https://docs.github.com
- Conventional Commits: https://www.conventionalcommits.org

### **Cheat Sheets**

- Git Cheat Sheet: https://education.github.com/git-cheat-sheet-education.pdf
- Interactive Git Cheatsheet: https://ndpsoftware.com/git-cheatsheet.html

### **Ferramentas Visuais**

- **GitKraken** - Cliente Git visual
- **GitHub Desktop** - Cliente oficial do GitHub
- **SourceTree** - Cliente da Atlassian
- **VSCode Git Integration** - Built-in no VSCode

### **Configurações Recomendadas**

```bash
# Configurar nome e email
git config --global user.name "DevSkillsIT"
git config --global user.email "repositories@skillsit.com.br"

# Editor padrão
git config --global core.editor "code --wait"  # VSCode

# Cores no terminal
git config --global color.ui auto

# Aliases úteis
git config --global alias.st status
git config --global alias.co checkout
git config --global alias.br branch
git config --global alias.ci commit
git config --global alias.unstage 'reset HEAD --'
git config --global alias.last 'log -1 HEAD'
git config --global alias.visual 'log --oneline --graph --all'

# Salvar credenciais
git config --global credential.helper store

# Line endings (Windows)
git config --global core.autocrlf true

# Pull com rebase por padrão (mais limpo)
git config --global pull.rebase true

# Criar branch automaticamente ao push
git config --global push.autoSetupRemote true
```

---

## ✅ Checklist de Boas Práticas

Antes de cada commit, verifique:

- [ ] Código testado localmente?
- [ ] Mensagem de commit segue padrão Conventional Commits?
- [ ] Sem arquivos gerados (`__pycache__`, `node_modules`)?
- [ ] Sem credenciais ou senhas?
- [ ] Código formatado corretamente?
- [ ] Sem `console.log` ou `print` de debug?
- [ ] Sem TODOs ou FIXMEs críticos?

Antes de cada Pull Request, verifique:

- [ ] Branch atualizado com main?
- [ ] Todos commits bem descritos?
- [ ] Funcionalidade 100% completa?
- [ ] Testes passando?
- [ ] Build executado com sucesso?
- [ ] Documentação atualizada (se necessário)?
- [ ] Sem conflitos?

---

## 📞 Contato

**Dúvidas sobre o workflow Git?**

- Abra uma issue no GitHub
- Consulte a documentação oficial
- Peça ajuda ao time

---

**🎯 Lembre-se:** Git é uma ferramenta poderosa. Com essas práticas você vai trabalhar de forma profissional e evitar problemas comuns!

**Happy Coding! 🚀**
