# CHECKLIST DE TESTE - CONTEXT API

**Data**: 2025-11-06
**Objetivo**: Validar se Context API eliminou requisições duplicadas

---

## ✅ PRÉ-REQUISITOS

- [ ] Backend rodando em http://localhost:5000
- [ ] Frontend rodando em http://localhost:8081
- [ ] Navegador Chrome ou Edge aberto

---

## 📋 PROCEDIMENTO DE TESTE (5 minutos)

### Passo 1: Preparar Ambiente de Teste
```
1. Abrir Chrome/Edge
2. Acessar: http://localhost:8081
3. Pressionar F12 (abrir DevTools)
4. Ir na aba "Network" (Rede)
5. Limpar histórico de requisições (ícone 🚫 ou Ctrl+E)
```

### Passo 2: Configurar Filtro
```
6. Na barra de filtro da aba Network, digitar: fields
7. Isso vai filtrar apenas requisições que contenham "fields" na URL
```

### Passo 3: Executar Teste
```
8. No menu lateral da aplicação, clicar em "Exporters"
9. OBSERVAR: Quantas requisições aparecem para:
   GET /api/v1/prometheus-config/fields
```

### Passo 4: Analisar Resultado

**RESULTADO ESPERADO**: ✅ **1 requisição apenas**
```
Network Tab:
┌────────────────────────────────────────────────────────────┐
│ Name                          Status    Type      Time     │
├────────────────────────────────────────────────────────────┤
│ fields?enrich=true            200       xhr       0.8s     │
└────────────────────────────────────────────────────────────┘

✅ SUCESSO! Context API está funcionando!
```

**RESULTADO PROBLEMÁTICO**: ❌ **3 requisições**
```
Network Tab:
┌────────────────────────────────────────────────────────────┐
│ Name                          Status    Type      Time     │
├────────────────────────────────────────────────────────────┤
│ fields?enrich=true            200       xhr       30.2s    │
│ fields?enrich=true            200       xhr       30.1s    │
│ fields?enrich=true            200       xhr       30.3s    │
└────────────────────────────────────────────────────────────┘

❌ PROBLEMA! Context API NÃO está funcionando!
```

---

## 📊 RESULTADOS DO TESTE

### Resultado Obtido:
- [ ] ✅ 1 requisição (Context API funcionou)
- [ ] ❌ 3 requisições (Context API não funcionou)
- [ ] ❌ Outro resultado: _________________

### Tempo de Carregamento:
- Tempo da(s) requisição(ões): _______ segundos
- Tempo total de carregamento da página: _______ segundos

### Console do Navegador (F12 → Console):
- [ ] Sem erros
- [ ] Com erros (descrever abaixo)

**Erros encontrados**:
```
(Copiar erros do console aqui)
```

---

## 🔧 SE RESULTADO FOI ❌ (3 requisições)

### Debugar Problema

**1. Verificar se Provider está no App.tsx**
```bash
# Verificar linha 140 de App.tsx
grep -n "MetadataFieldsProvider" frontend/src/App.tsx
# Deve aparecer: <MetadataFieldsProvider>
```

**2. Verificar se hooks consomem do Context**
```bash
# Verificar se hooks usam useMetadataFieldsContext
grep -n "useMetadataFieldsContext" frontend/src/hooks/useMetadataFields.ts
# Deve aparecer 3 vezes (linhas 230, 256, 280)
```

**3. Verificar Console do Navegador**
```
Procurar por erro:
"useMetadataFieldsContext deve ser usado dentro de MetadataFieldsProvider"

Se encontrar este erro:
- Provider não está envolvendo os componentes corretamente
```

**4. Limpar Cache do Navegador**
```
1. Ctrl + Shift + Del
2. Limpar "Cached images and files"
3. Recarregar página (Ctrl + Shift + R - hard reload)
4. Testar novamente
```

---

## ✅ SE RESULTADO FOI ✅ (1 requisição)

### Próximos Passos

**SUCESSO! Context API está funcionando corretamente!**

Benefícios COMPROVADOS obtidos:
- ✅ Redução de 67% nas requisições HTTP (3 → 1)
- ✅ Redução de 67% na carga do backend
- ✅ Navegação entre páginas instantânea (usa cache do Context)

**MAS ATENÇÃO**: Isto NÃO resolve completamente o problema de cold start!
- ⚠️ Primeira carga após restart AINDA pode demorar 20-30s (se KV vazio)
- ⚠️ SSH AINDA acontece durante requisição HTTP

**Próximo passo: Implementar Passo 2 (Pré-warming do KV)**

Ver: [ANALISE_COMPLETA_PROBLEMAS_PERFORMANCE.md](ANALISE_COMPLETA_PROBLEMAS_PERFORMANCE.md#passo-2-garantir-kv-sempre-populado-após-validar-passo-1)

**Objetivo do Passo 2**: Garantir que KV está sempre populado no startup do backend
- Adicionar startup event em `backend/app.py`
- Pré-popular cache em background
- **Isso sim vai eliminar cold start lento**

---

## 📝 NOTAS ADICIONAIS

### Teste em Outras Páginas (Opcional)

Para confirmar que Context API funciona em todas as páginas:

1. **Página Services**:
   - Limpar Network tab
   - Clicar em "Servicos"
   - Verificar: 0 novas requisições para `/fields` (usa cache do Context)

2. **Página Blackbox**:
   - Limpar Network tab
   - Clicar em "Alvos Blackbox"
   - Verificar: 0 novas requisições para `/fields` (usa cache do Context)

**ESPERADO**: Apenas a PRIMEIRA página visitada faz a requisição. Páginas seguintes usam cache.

---

## 🎯 CRITÉRIOS DE SUCESSO

- [x] Context API implementado corretamente
- [ ] Teste executado conforme procedimento
- [ ] Resultado: 1 requisição ao invés de 3
- [ ] Tempo de carregamento: <2s (com KV populado)
- [ ] Sem erros no console do navegador

---

**Data do Teste**: __________________

**Testado por**: __________________

**Resultado Final**: ✅ APROVADO / ❌ REPROVADO

**Observações**:
```
(Espaço para observações adicionais)
```
