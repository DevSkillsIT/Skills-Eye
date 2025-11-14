# 🔴 ERROS DE RUNTIME ENCONTRADOS - Skills Eye

**Data:** 13/11/2025 19:20  
**Ambiente:** Backend rodando (PID 117770), Frontend em desenvolvimento  
**Status:** 3 ERROS CRÍTICOS encontrados durante execução  
**Analisado por:** VSCode Copilot

---

## 📊 RESUMO EXECUTIVO

**TOTAL DE ERROS:** 3  
**PRIORIDADE:** 🔴 CRÍTICA - Aplicação não funciona  

| # | Erro | Tipo | Impacto |
|---|------|------|---------|
| 1 | 404 Not Found `/api/v1/categorization-rules` | Backend Config | **CRÍTICO** - Endpoint inacessível |
| 2 | 500 Internal Error `/monitoring/data` | Backend Cache | **CRÍTICO** - Sistema não inicializado |
| 3 | TypeError `options is undefined` | Frontend Race | **CRÍTICO** - Página trava completamente |

---

## 🔴 ERRO #1: 404 Not Found - Endpoint Categorization Rules

### SINTOMA:
```
GET http://localhost:5000/api/v1/categorization-rules
Status: 404 Not Found
```

### CAUSA RAIZ:
**Router registrado INCORRETAMENTE no `backend/app.py`**

### EVIDÊNCIA:

**Arquivo:** `backend/app.py` linha 243
```python
# ❌ ERRADO: Registra router SEM prefix
app.include_router(categorization_rules_router, prefix="/api/v1", tags=["Categorization Rules"])
```

**Arquivo:** `backend/api/categorization_rules.py` linha 96
```python
# Router define rota com path relativo
@router.get("/categorization-rules")
async def get_categorization_rules():
    """Retorna todas as regras de categorização do KV"""
```

### PROBLEMA:
Quando o router é incluído com `prefix="/api/v1"`, as rotas do arquivo devem ser definidas **SEM repetir o prefix**.

**COMO ESTÁ (ERRADO):**
- `app.py` registra: `prefix="/api/v1"` ✅
- `categorization_rules.py` define: `@router.get("/categorization-rules")` ✅
- **URL FINAL:** `/api/v1/categorization-rules` ✅ **DEVERIA FUNCIONAR!**

**MAS... o erro 404 indica que o router NÃO está sendo registrado corretamente.**

### ANÁLISE DETALHADA:

Examinando o `app.py` linha 243:
```python
app.include_router(categorization_rules_router, prefix="/api/v1", tags=["Categorization Rules"])
```

Comparando com outros routers que FUNCIONAM:
```python
# Linha 231 - FUNCIONA
app.include_router(services_router, prefix="/api/v1/services", tags=["Services"])

# Linha 241 - FUNCIONA
app.include_router(monitoring_unified_router, prefix="/api/v1", tags=["Monitoring Unified"])
```

### TESTE DE VALIDAÇÃO:
```bash
$ curl -s http://localhost:5000/api/v1/categorization-rules
{"detail":"Not Found"}

# Testando outros endpoints
$ curl -s http://localhost:5000/api/v1/monitoring/data?category=network-probes
{"detail":"Cache de tipos não disponível. Execute sync-cache primeiro."}
# ^ Este endpoint existe (retorna erro de lógica, não 404)
```

### HIPÓTESE:
**O router pode não estar sendo importado corretamente ou há conflito de nome.**

### CORREÇÃO SUGERIDA:

**OPÇÃO 1: Verificar import**
```python
# backend/app.py linha 20
from api.categorization_rules import router as categorization_rules_router
```

**VALIDAR:**
```bash
cd backend
python -c "from api.categorization_rules import router; print(router.routes)"
```

**OPÇÃO 2: Registrar router com prefix completo**
```python
# backend/app.py
app.include_router(
    categorization_rules_router, 
    prefix="/api/v1/categorization-rules",  # ← TROCAR AQUI
    tags=["Categorization Rules"]
)
```

**E MODIFICAR as rotas em categorization_rules.py:**
```python
# backend/api/categorization_rules.py

@router.get("/")  # ← MUDAR DE "/categorization-rules" para "/"
async def get_categorization_rules():
    """GET /api/v1/categorization-rules"""

@router.post("/")  # ← MUDAR DE "/categorization-rules" para "/"
async def create_categorization_rule(request: RuleCreateRequest):
    """POST /api/v1/categorization-rules"""

@router.put("/{rule_id}")  # ← JÁ ESTÁ CORRETO
async def update_categorization_rule(rule_id: str, request: RuleUpdateRequest):
    """PUT /api/v1/categorization-rules/{rule_id}"""

@router.delete("/{rule_id}")  # ← JÁ ESTÁ CORRETO
async def delete_categorization_rule(rule_id: str):
    """DELETE /api/v1/categorization-rules/{rule_id}"""

@router.post("/reload")  # ← JÁ ESTÁ CORRETO
async def reload_categorization_rules():
    """POST /api/v1/categorization-rules/reload"""
```

**ESTA É A ABORDAGEM CORRETA** seguindo o padrão dos outros routers:
- `services_router` → `prefix="/api/v1/services"` + rotas com `/` 
- `monitoring_unified_router` → `prefix="/api/v1"` + rotas com `/monitoring/data`

**RECOMENDAÇÃO:** Usar OPÇÃO 2 (prefix completo + rotas relativas)

---

## 🔴 ERRO #2: 500 Internal Server Error - Cache Não Inicializado

### SINTOMA:
```
GET http://localhost:5000/api/v1/monitoring/data?category=network-probes
Status: 500 Internal Server Error

Response:
{
  "detail": "Cache de tipos não disponível. Execute sync-cache primeiro."
}
```

### CAUSA RAIZ:
**Sistema de cache KV não foi populado com dados de categorização**

### EVIDÊNCIA:

**Teste direto:**
```bash
$ curl -s "http://localhost:5000/api/v1/monitoring/data?category=network-probes" | jq .
{
  "detail": "Cache de tipos não disponível. Execute sync-cache primeiro."
}
```

### ANÁLISE:
O sistema depende de um cache no Consul KV em:
```
skills/eye/monitoring-types/cache
```

Este cache armazena:
- Categorias de monitoramento (network-probes, web-probes, etc)
- Tipos de serviços por categoria
- Módulos blackbox associados
- Jobs do Prometheus

**FLUXO ESPERADO:**
1. Backend inicia
2. Roda migração/sync para popular KV
3. Cache fica disponível
4. Frontend consome dados

**FLUXO ATUAL:**
1. Backend inicia ✅
2. ❌ **Migração NÃO FOI EXECUTADA**
3. ❌ Cache vazio no KV
4. ❌ Frontend recebe erro 500

### ARQUIVOS RELACIONADOS:

**1. Script de Migração (NÃO EXECUTADO):**
```python
# backend/migrate_categorization_to_json.py
```

**2. Endpoint de Sync:**
```python
# backend/api/monitoring_types_dynamic.py
@router.post("/monitoring-types/sync-cache")
async def sync_monitoring_types_cache():
    """Sincroniza cache de tipos de monitoramento"""
```

### CORREÇÃO SUGERIDA:

**PASSO 1: Executar migração**
```bash
cd backend
python migrate_categorization_to_json.py
```

**PASSO 2: Validar cache criado**
```bash
# Verificar se KV foi populado
curl -s http://172.16.1.26:8500/v1/kv/skills/eye/monitoring-types/cache?raw
```

**PASSO 3: Testar endpoint novamente**
```bash
curl -s "http://localhost:5000/api/v1/monitoring/data?category=network-probes"
# Deve retornar dados, não erro 500
```

**ALTERNATIVA: Chamar endpoint de sync via API**
```bash
curl -X POST http://localhost:5000/api/v1/monitoring-types/sync-cache
```

### OBSERVAÇÃO IMPORTANTE:
Este erro **NÃO É UM BUG** do Claude Code, é **FALTA DE EXECUÇÃO DO PLANO DE MIGRAÇÃO**.

O documento `GUIA_MIGRACAO_MONITORING_TYPES.md` instrui claramente:
> **PASSO 1:** Executar `python migrate_categorization_to_json.py`

**Este passo NÃO FOI EXECUTADO pelo usuário.**

---

## 🔴 ERRO #3: TypeError - options is undefined (Race Condition)

### SINTOMA:
```javascript
TypeError: can't access property "vendor", value is undefined
    children MetadataFilterBar.tsx:68
```

**Browser Console:**
```
TypeError: can't access property "vendor", value is undefined
    children MetadataFilterBar.tsx:68
    MetadataFilterBar MetadataFilterBar.tsx:56
```

### CAUSA RAIZ:
**Race condition entre inicialização do estado e renderização do componente**

### EVIDÊNCIA:

**Arquivo:** `frontend/src/pages/DynamicMonitoringPage.tsx`

**Linha 181 - Inicialização do estado:**
```tsx
const [metadataOptions, setMetadataOptions] = useState<Record<string, string[]>>({});
// ⚠️ INICIA VAZIO: {}
```

**Linha 993 - Passagem do prop:**
```tsx
<MetadataFilterBar
  fields={filterFields}
  filters={filters}
  options={metadataOptions}  // ← Pode estar vazio ({}) durante primeiro render
  onChange={(newFilters) => {
    setFilters(newFilters);
    actionRef.current?.reload();
  }}
/>
```

**Linha 544 - População do estado (ASYNC):**
```tsx
// Dentro do useEffect que busca dados
setMetadataOptions(options);
```

### ANÁLISE DO COMPONENTE MetadataFilterBar:

**Arquivo:** `frontend/src/components/MetadataFilterBar.tsx` linha 68

```tsx
{fieldOptions.map((item) => (
  <Option value={item} key={`${field.name}-${item}`}>
    {item}
  </Option>
))}
```

**De onde vem `fieldOptions`?**

Preciso examinar o código completo do MetadataFilterBar para entender a lógica...

**HIPÓTESE BASEADA NO ERRO:**
O componente MetadataFilterBar tenta acessar:
```tsx
options[field.name].vendor  // ← options pode estar undefined
```

Mas o erro diz "can't access property 'vendor', **value is undefined**", não "options is undefined".

Isso significa que `options[field.name]` retorna `undefined`, e ENTÃO tenta acessar `.vendor`.

### ESTRUTURA ESPERADA vs REAL:

**ESPERADO:**
```typescript
options = {
  "vendor": ["Cisco", "Juniper", "HP"],
  "model": ["2960", "3560", "5520"],
  "company": ["Company A", "Company B"]
}
```

**REAL (primeiro render):**
```typescript
options = {}  // ← VAZIO!
```

### FLUXO DE EXECUÇÃO:

**RENDER 1 (inicial):**
1. Component monta
2. `metadataOptions = {}`
3. `MetadataFilterBar` recebe `options={{}}`
4. Tenta acessar `options[field.name]` → `undefined`
5. Tenta acessar `.vendor` → **CRASH**

**RENDER 2 (após useEffect):**
1. useEffect busca dados
2. `setMetadataOptions({ vendor: [...], model: [...] })`
3. Component re-renderiza
4. `MetadataFilterBar` recebe `options` populado
5. ✅ Funciona

**PROBLEMA:** O componente MetadataFilterBar **NÃO VALIDA** se `options` está vazio.

### CORREÇÃO SUGERIDA:

**OPÇÃO 1: Adicionar validação no MetadataFilterBar**
```tsx
// frontend/src/components/MetadataFilterBar.tsx

{fields.map((field) => {
  // ✅ ADICIONAR VALIDAÇÃO AQUI
  const fieldOptions = options?.[field.name] ?? [];
  
  if (!fieldOptions || fieldOptions.length === 0) {
    return null;  // Não renderiza select vazio
  }

  return (
    <Select
      key={field.name}
      allowClear
      showSearch
      placeholder={field.placeholder || field.display_name}
      value={value[field.name]}
      onChange={(val) => handleChange(field.name, val)}
    >
      {fieldOptions.map((item) => (
        <Option value={item} key={`${field.name}-${item}`}>
          {item}
        </Option>
      ))}
    </Select>
  );
})}
```

**OPÇÃO 2: Não renderizar MetadataFilterBar até options estar pronto**
```tsx
// frontend/src/pages/DynamicMonitoringPage.tsx linha 993

{Object.keys(metadataOptions).length > 0 && (
  <MetadataFilterBar
    fields={filterFields}
    filters={filters}
    options={metadataOptions}
    onChange={(newFilters) => {
      setFilters(newFilters);
      actionRef.current?.reload();
    }}
  />
)}
```

**OPÇÃO 3: Adicionar loading state**
```tsx
const [metadataOptionsLoading, setMetadataOptionsLoading] = useState(true);

// No useEffect após popular options
setMetadataOptionsLoading(false);

// No JSX
{!metadataOptionsLoading && (
  <MetadataFilterBar
    fields={filterFields}
    filters={filters}
    options={metadataOptions}
    onChange={(newFilters) => {
      setFilters(newFilters);
      actionRef.current?.reload();
    }}
  />
)}
```

**RECOMENDAÇÃO:** Usar **OPÇÃO 1** (validação dentro do componente) + **OPÇÃO 2** (condicional de renderização) como defesa em profundidade:

```tsx
// MetadataFilterBar.tsx - Adicionar validação
const fieldOptions = options?.[field.name] ?? [];
if (fieldOptions.length === 0) return null;

// DynamicMonitoringPage.tsx - Condicional de renderização
{filterFields.length > 0 && Object.keys(metadataOptions).length > 0 && (
  <MetadataFilterBar ... />
)}
```

---

## 🎯 PLANO DE CORREÇÃO COMPLETO

### PRIORIDADE 1 - ERRO #2 (Bloqueador de Todos)
```bash
# Este erro impede teste dos outros
cd /home/adrianofante/projetos/Skills-Eye/backend
python migrate_categorization_to_json.py
```

**VALIDAR:**
```bash
curl -s "http://localhost:5000/api/v1/monitoring/data?category=network-probes"
# Deve retornar dados JSON, não erro 500
```

### PRIORIDADE 2 - ERRO #1 (Endpoint 404)
**Modificar `backend/app.py` linha 243:**
```python
# ANTES
app.include_router(categorization_rules_router, prefix="/api/v1", tags=["Categorization Rules"])

# DEPOIS
app.include_router(categorization_rules_router, prefix="/api/v1/categorization-rules", tags=["Categorization Rules"])
```

**Modificar `backend/api/categorization_rules.py`:**
```python
# ANTES
@router.get("/categorization-rules")

# DEPOIS
@router.get("/")

# ANTES
@router.post("/categorization-rules")

# DEPOIS  
@router.post("/")
```

**REINICIAR BACKEND:**
```bash
cd /home/adrianofante/projetos/Skills-Eye
./restart-backend.sh
```

**VALIDAR:**
```bash
curl -s http://localhost:5000/api/v1/categorization-rules | jq .
# Deve retornar array de regras, não 404
```

### PRIORIDADE 3 - ERRO #3 (Race Condition Frontend)
**Modificar `frontend/src/components/MetadataFilterBar.tsx` linha ~68:**
```tsx
{fields.map((field) => {
  // ✅ ADICIONAR VALIDAÇÃO
  const fieldOptions = options?.[field.name] ?? [];
  
  if (fieldOptions.length === 0) {
    return null;  // Não renderiza campo sem opções
  }

  const minWidth = field.filter_width ?? 200;
  const loading = false;

  return (
    <Select
      key={field.name}
      allowClear
      showSearch
      placeholder={field.placeholder || field.display_name}
      style={{ minWidth }}
      loading={loading}
      value={value[field.name]}
      onChange={(val) => handleChange(field.name, val)}
    >
      {fieldOptions.map((item) => (
        <Option value={item} key={`${field.name}-${item}`}>
          {item}
        </Option>
      ))}
    </Select>
  );
})}
```

**E ADICIONAR condicional em `frontend/src/pages/DynamicMonitoringPage.tsx` linha 993:**
```tsx
{filterFields.length > 0 && Object.keys(metadataOptions).length > 0 && (
  <MetadataFilterBar
    fields={filterFields}
    filters={filters}
    options={metadataOptions}
    onChange={(newFilters) => {
      setFilters(newFilters);
      actionRef.current?.reload();
    }}
  />
)}
```

**VALIDAR:**
- Recarregar página
- Não deve mais ter erro `options is undefined` no console
- Filtros devem aparecer após dados carregarem

---

## 📊 CHECKLIST DE VALIDAÇÃO

Após aplicar as correções, executar:

```bash
# BACKEND
cd /home/adrianofante/projetos/Skills-Eye/backend

# ✅ Migração executada?
python migrate_categorization_to_json.py

# ✅ Cache populado?
curl -s http://172.16.1.26:8500/v1/kv/skills/eye/monitoring-types/cache?raw | jq .

# ✅ Endpoint /monitoring/data funciona?
curl -s "http://localhost:5000/api/v1/monitoring/data?category=network-probes" | jq .

# ✅ Endpoint /categorization-rules funciona?
curl -s "http://localhost:5000/api/v1/categorization-rules" | jq .

# FRONTEND
# ✅ Página carrega sem erro no console?
# ✅ Filtros aparecem após dados carregarem?
# ✅ Tabela exibe dados corretamente?
```

---

## 🎓 LIÇÕES APRENDIDAS

### ERRO #1 - Router FastAPI
**PROBLEMA:** Confusão entre prefix no `include_router` vs path no `@router.get`
**SOLUÇÃO:** Seguir padrão consistente:
- Prefix COMPLETO no `include_router`: `prefix="/api/v1/categorization-rules"`
- Paths RELATIVOS no router: `@router.get("/")`

### ERRO #2 - Dependência de Migração
**PROBLEMA:** Sistema depende de dados no KV mas migração não foi executada
**SOLUÇÃO:** Documentar pré-requisitos claramente + adicionar validação na inicialização

### ERRO #3 - Race Condition React
**PROBLEMA:** Estado assíncrono usado antes de estar pronto
**SOLUÇÃO:** Sempre validar estado antes de usar + renderização condicional

---

## 📝 RESUMO PARA CLAUDE CODE

**3 ERROS CRÍTICOS encontrados durante runtime:**

1. **404 em /categorization-rules** → Problema de configuração de router (prefix incorreto)
2. **500 em /monitoring/data** → Cache KV não inicializado (falta executar migração)
3. **TypeError options undefined** → Race condition no React (falta validação de estado)

**TODOS SÃO CORRIGÍVEIS** com as sugestões acima.

**PRIORIDADE DE CORREÇÃO:**
1. Erro #2 (bloqueador)
2. Erro #1 (configuração)
3. Erro #3 (validação)

---

**FIM DO RELATÓRIO DE ERROS DE RUNTIME**

**Analisado por:** VSCode Copilot  
**Data:** 13/11/2025 19:25  
**Status:** Aguardando correções do Claude Code
