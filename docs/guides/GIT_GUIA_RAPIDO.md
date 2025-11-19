# Guia Rápido de Git para Iniciantes - Skills-Eye

Este guia foi criado especialmente para você que está começando com Git! 🚀

## Comandos Básicos do Dia a Dia

### 1. Ver o que mudou
```bash
git status
```
**O que faz:** Mostra quais arquivos você modificou

### 2. Adicionar mudanças
```bash
git add .
```
**O que faz:** Prepara TODAS as suas mudanças para o commit

Ou para arquivo específico:
```bash
git add nome-do-arquivo.js
```

### 3. Salvar mudanças (commit)
```bash
git commit -m "descrição curta do que você fez"
```
**Exemplo:**
```bash
git commit -m "Adiciona funcionalidade de login"
```

### 4. Enviar para o GitHub
```bash
git push
```
**O que faz:** Envia seus commits para o repositório remoto

## Fluxo Básico de Trabalho

```
1. Trabalhe no código normalmente
   ↓
2. git status (veja o que mudou)
   ↓
3. git add . (prepare as mudanças)
   ↓
4. git commit -m "descrição" (salve as mudanças)
   ↓
5. git push (envie para o GitHub)
```

## Trabalhando com Branches

### Ver em qual branch você está
```bash
git branch
```

### Criar uma nova branch
```bash
git checkout -b feature/minha-feature
```

### Voltar para a branch principal
```bash
git checkout main
```

## Quando algo der errado...

### Desfazer mudanças antes do commit
```bash
git checkout -- nome-do-arquivo.js
```

### Ver histórico de commits
```bash
git log
```

### Voltar para um commit anterior (cuidado!)
```bash
git checkout hash-do-commit
```

## Dicas Importantes

1. **Commits frequentes:** Faça commits pequenos e frequentes
2. **Mensagens claras:** Use mensagens que expliquem O QUE você fez
3. **Sempre git status:** Antes de fazer qualquer coisa, veja o status
4. **Não tenha medo:** Git guarda tudo, é difícil perder código de verdade

## Comandos de Emergência

### Esqueci de adicionar um arquivo no último commit
```bash
git add arquivo-esquecido.js
git commit --amend --no-edit
```

### Quero desistir de TUDO que fiz (cuidado!)
```bash
git reset --hard HEAD
```

## Recursos Úteis

- **Seu branch de desenvolvimento:** `dev-adriano`
- **Branch principal:** `main`
- **Padrão de branches:** `feature/SPEC-XXX`

## Precisa de Ajuda?

1. Use `git status` - ele sempre te diz o que fazer
2. Pergunte ao Alfred! Ele está aqui para te ajudar
3. Não tenha medo de experimentar em uma branch de teste

---

**Lembre-se:** Git é uma ferramenta para te ajudar, não para te atrapalhar. Com prática, fica natural! 💪
