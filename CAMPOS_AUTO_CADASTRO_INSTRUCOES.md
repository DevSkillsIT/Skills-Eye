# ⚠️ CAMPOS AUTO-CADASTRO: INSTRUÇÕES IMPORTANTES

**Data:** 2025-11-11
**Contexto:** Correção do sistema Reference Values

---

## 🎯 RESUMO

A partir da correção de 2025-11-11, **novos campos extraídos do Prometheus vêm com auto-cadastro DESABILITADO por padrão**. Isso foi uma solicitação do usuário para maior controle sobre quais campos aparecem em Reference Values.

---

## ❗ RISCO: CAMPOS SEREM DESABILITADOS

### **PERGUNTA: "Corremos o risco disso acontecer de novo e dar problema de desabilitar os campos novamente?"**

### **RESPOSTA: NÃO, mas com ressalvas:**

#### ✅ **Campos EXISTENTES estão seguros**
- Os 6 campos habilitados via script (`company`, `cidade`, `fabricante`, `vendor`, `localizacao`, `provedor`) **estão salvos no Consul KV** com `available_for_registration: true`
- Enquanto o KV não for apagado/resetado, esses campos permanecerão habilitados
- O backend **NÃO sobrescreve** campos que já existem no KV

#### ⚠️ **NOVOS campos virão DESABILITADOS**
- Quando o sistema extrair campos novos do Prometheus, eles virão com `available_for_registration: false` por padrão
- Isso é o comportamento **solicitado** (correção #1)
- Para habilitar novos campos:
  1. Acesse a página **Metadata Fields**
  2. Clique em **Editar** no campo desejado
  3. Ative o toggle **Auto-Cadastro**
  4. Salve

#### 🛡️ **Como o KV está protegido:**
- O processo de pre-warm do app.py **NÃO sobrescreve** se o KV já tem dados
- Linha no código: `if existing_config and existing_config.get('fields'): return` (metadata_fields_manager.py)
- Só popula KV se estiver **completamente vazio**

---

## 📊 CAMPOS HABILITADOS ATUALMENTE

**Total:** 6 campos

| Campo | Status | Categoria | Habilitado Em |
|-------|--------|-----------|---------------|
| company | ✅ Habilitado | basic | 2025-11-11 |
| cidade | ✅ Habilitado | location | 2025-11-11 |
| fabricante | ✅ Habilitado | device | 2025-11-11 |
| vendor | ✅ Habilitado | device | 2025-11-11 |
| localizacao | ✅ Habilitado | location | 2025-11-11 |
| provedor | ✅ Habilitado | infrastructure | 2025-11-11 |

---

## 🔧 COMO HABILITAR NOVOS CAMPOS

### **Método 1: Via Interface Web (RECOMENDADO)**

1. Acesse **http://localhost:8081/metadata-fields**
2. Encontre o campo que deseja habilitar
3. Clique no ícone **✏️ Editar**
4. Na seção "Visibilidade", ative o toggle **Auto-Cadastro**
5. Clique em **Submeter**
6. ✅ Campo habilitado! Ele aparecerá automaticamente em Reference Values

### **Método 2: Via Script Python (AVANÇADO)**

Se você quiser habilitar múltiplos campos de uma vez:

```bash
cd backend
./venv/bin/python3 enable_common_fields.py
```

**IMPORTANTE:** Edite `enable_common_fields.py` antes de executar para adicionar os campos desejados na lista `COMMON_FIELDS_TO_ENABLE`.

---

## 🔄 COMO RESETAR TUDO (SE NECESSÁRIO)

**CUIDADO:** Isso apaga TODAS as customizações!

### **Opção 1: Deletar KV via Consul UI**
1. Acesse http://172.16.1.26:8500/ui
2. Vá em **Key/Value**
3. Delete a chave: `skills/eye/metadata/fields`
4. Reinicie o backend
5. Sistema criará campos padrão (todos desabilitados)

### **Opção 2: Via curl**
```bash
curl -X DELETE \
  -H "X-Consul-Token: 8382a112-81e0-cd6d-2b92-8565925a0675" \
  http://172.16.1.26:8500/v1/kv/skills/eye/metadata/fields
```

---

## 📝 PROCESSO DE PRE-WARM DO BACKEND

Quando o backend inicia (`app.py`):

1. **Verifica se KV tem campos**
   ```python
   existing_config = await kv.get_json('skills/eye/metadata/fields')
   if existing_config and existing_config.get('fields'):
       logger.info("✓ KV já tem campos, não sobrescreve")
       return  # NÃO TOCA NO KV!
   ```

2. **Se KV está vazio:**
   - Extrai campos do Prometheus via SSH
   - **TODOS vêm com `available_for_registration: false`** (padrão definido em `fields_extraction_service.py:46`)
   - Salva no KV

3. **Se KV tem dados:**
   - **NÃO TOCA EM NADA!**
   - Usa cache existente
   - Suas customizações estão seguras

---

## 🎓 BOAS PRÁTICAS

### ✅ **Faça:**
- Use a interface **Metadata Fields** para habilitar novos campos
- Habilite apenas campos que realmente usa
- Documente quais campos habilitou e por quê

### ❌ **Evite:**
- Deletar o KV manualmente sem necessidade
- Habilitar todos os campos de uma vez (poluição visual)
- Modificar o código de extração sem entender o impacto

---

## 🐛 TROUBLESHOOTING

### **Problema: Campos não aparecem em Reference Values**
**Solução:**
1. Verifique se o campo tem `available_for_registration: true` em Metadata Fields
2. Limpe o cache do backend (reinicie ou aguarde 5 minutos)
3. Recarregue a página Reference Values (F5)

### **Problema: Todos os campos sumiram**
**Possível Causa:** KV foi resetado ou deletado

**Solução:**
```bash
cd backend
./venv/bin/python3 enable_common_fields.py
```

Reinicie o backend e recarregue a página.

---

**Criado por:** Claude Code (Anthropic)
**Última atualização:** 2025-11-11
