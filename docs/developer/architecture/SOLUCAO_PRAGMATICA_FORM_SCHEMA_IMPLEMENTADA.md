# ✅ Solução Pragmática: Form Schema em Monitoring-Types

**Data:** 2025-11-18
**Status:** 🟡 **PARCIALMENTE IMPLEMENTADO** (Backend 100%, Frontend 30%)
**Próximo:** Cursor continua modal frontend

---

## 🎯 PROBLEMA RESOLVIDO

**Problema Estrutural Identificado:**
- Em `/monitoring/rules` podem existir VÁRIAS regras para mesmo exporter_type (blackbox_icmp, blackbox_http, etc)
- Cada regra com form_schema diferente → AMBIGUIDADE ao criar serviço
- Qual form_schema usar? ❌

**Solução Pragmática:**
- ✅ Usar KV `skills/eye/monitoring-types` como ÚNICA fonte de verdade
- ✅ Cada tipo tem SEU form_schema (sem duplicação, sem ambiguidade)
- ✅ 1 tipo = 1 form_schema (icmp → form_schema único)

---

## ✅ O QUE FOI IMPLEMENTADO (Backend 100%)

### 1. Backend - Endpoint PUT /type/{type_id}/form-schema

**Arquivo:** `backend/api/monitoring_types_dynamic.py`

**Mudanças:**
- ✅ Adicionado modelo Pydantic `FormSchemaUpdateRequest` (linhas 31-33)
- ✅ Adicionado endpoint `PUT /type/{type_id}/form-schema` (linhas 728-820)

**Funcionalidades:**
```python
PUT /api/v1/monitoring-types-dynamic/type/icmp/form-schema
Body: {
  "form_schema": {
    "fields": [
      {
        "name": "target",
        "label": "Alvo (IP ou Hostname)",
        "type": "text",
        "required": true,
        "validation": {"type": "ip_or_hostname"},
        "placeholder": "192.168.1.1",
        "help": "Endereço IP ou hostname a ser monitorado"
      },
      {
        "name": "module",
        "label": "Módulo Blackbox",
        "type": "select",
        "required": true,
        "default": "icmp",
        "options": [
          {"value": "icmp", "label": "ICMP (Ping)"},
          {"value": "tcp_connect", "label": "TCP Connect"}
        ]
      }
    ],
    "required_metadata": ["target", "module"],
    "optional_metadata": []
  }
}
```

**Fluxo do Endpoint:**
1. Busca KV `skills/eye/monitoring-types`
2. Encontra tipo por `type_id` em `all_types[]`
3. Atualiza campo `form_schema` diretamente
4. Atualiza também em `servers[host].types[]` (consistência)
5. Salva de volta no KV
6. Retorna sucesso

**Logs:**
```
[UPDATE-FORM-SCHEMA] Atualizando form_schema para tipo: icmp
[UPDATE-FORM-SCHEMA] ✅ Tipo 'icmp' atualizado com form_schema
[UPDATE-FORM-SCHEMA] ✅ Form schema salvo no KV para tipo 'icmp'
```

### 2. Frontend - API updateTypeFormSchema

**Arquivo:** `frontend/src/services/api.ts` (linhas 1109-1115)

**Função Adicionada:**
```typescript
/**
 * ✅ SOLUÇÃO PRAGMÁTICA: Atualizar form_schema de um tipo
 */
updateTypeFormSchema: (typeId: string, formSchema: any) =>
  api.put(`/monitoring-types-dynamic/type/${typeId}/form-schema`, {
    form_schema: formSchema
  }),
```

**Uso:**
```typescript
await consulAPI.updateTypeFormSchema('icmp', {
  fields: [...],
  required_metadata: ["target", "module"],
  optional_metadata: []
});
```

---

## ⏳ O QUE FALTA IMPLEMENTAR (Frontend 70%)

### Modal de Edição em MonitoringTypes.tsx

**Localização:** `frontend/src/pages/MonitoringTypes.tsx`

**O que precisa:**

#### 1. Estados para Modal

```typescript
// Adicionar após os estados existentes (linha ~95)
const [formSchemaModalVisible, setFormSchemaModalVisible] = useState(false);
const [editingType, setEditingType] = useState<MonitoringType | null>(null);
const [formSchemaJSON, setFormSchemaJSON] = useState<string>('');
const [jsonError, setJsonError] = useState<string | null>(null);
```

#### 2. Handler para Abrir Modal

```typescript
// Adicionar após os handlers existentes (linha ~200)
const handleEditFormSchema = (type: MonitoringType) => {
  setEditingType(type);

  // Carregar form_schema existente ou criar vazio
  const existingSchema = type.form_schema || {
    fields: [],
    required_metadata: [],
    optional_metadata: []
  };

  setFormSchemaJSON(JSON.stringify(existingSchema, null, 2));
  setFormSchemaModalVisible(true);
};
```

#### 3. Handler para Salvar

```typescript
const handleSaveFormSchema = async () => {
  if (!editingType) return;

  try {
    // Validar JSON
    const formSchema = JSON.parse(formSchemaJSON);

    // Salvar via API
    await consulAPI.updateTypeFormSchema(editingType.id, formSchema);

    message.success(`Form schema salvo para tipo '${editingType.display_name}'!`);
    setFormSchemaModalVisible(false);

    // Recarregar tipos
    await loadTypes(false, false);
  } catch (e: any) {
    if (e instanceof SyntaxError) {
      message.error('JSON inválido! Corrija os erros de sintaxe.');
      setJsonError(e.message);
    } else {
      message.error('Erro ao salvar: ' + (e.message || e));
    }
  }
};
```

#### 4. Validação JSON em Tempo Real

```typescript
// useEffect para validar JSON enquanto digita
useEffect(() => {
  if (!formSchemaJSON) {
    setJsonError(null);
    return;
  }

  try {
    JSON.parse(formSchemaJSON);
    setJsonError(null);
  } catch (e: any) {
    setJsonError(e.message);
  }
}, [formSchemaJSON]);
```

#### 5. Adicionar Coluna "Ações" na Tabela

Dentro das colunas da tabela (ProTable), adicionar:

```typescript
// Adicionar após as colunas existentes
{
  title: 'Ações',
  key: 'actions',
  width: 120,
  fixed: 'right',
  render: (_, record) => (
    <Space size="small">
      <Tooltip title="Editar Form Schema">
        <Button
          type="link"
          size="small"
          icon={<EditOutlined />}
          onClick={() => handleEditFormSchema(record)}
        >
          Form Schema
        </Button>
      </Tooltip>
    </Space>
  ),
}
```

#### 6. Modal JSX (Adicionar no return, após ExtractionProgressModal)

```tsx
{/* ✅ MODAL: Editar Form Schema */}
<Modal
  title={`Editar Form Schema: ${editingType?.display_name}`}
  open={formSchemaModalVisible}
  onCancel={() => setFormSchemaModalVisible(false)}
  onOk={handleSaveFormSchema}
  width={800}
  okText="Salvar"
  cancelText="Cancelar"
  okButtonProps={{ disabled: !!jsonError }}
>
  <div style={{ marginBottom: 16 }}>
    <Alert
      message="Edite o schema do formulário em formato JSON"
      description="Este schema define quais campos aparecerão ao criar um serviço deste tipo."
      type="info"
      showIcon
    />
  </div>

  {/* Editor JSON */}
  <div style={{ marginBottom: 16 }}>
    <Text strong>Form Schema (JSON):</Text>
    <Input.TextArea
      value={formSchemaJSON}
      onChange={(e) => setFormSchemaJSON(e.target.value)}
      rows={15}
      style={{
        fontFamily: 'monospace',
        fontSize: '12px',
        marginTop: 8
      }}
      placeholder={`{
  "fields": [
    {
      "name": "target",
      "label": "Alvo",
      "type": "text",
      "required": true,
      "placeholder": "192.168.1.1"
    }
  ],
  "required_metadata": ["target"],
  "optional_metadata": []
}`}
    />
  </div>

  {/* Erro de validação JSON */}
  {jsonError && (
    <Alert
      message="Erro no JSON"
      description={jsonError}
      type="error"
      showIcon
    />
  )}

  {/* Ajuda */}
  <div style={{ marginTop: 16 }}>
    <Text type="secondary" style={{ fontSize: '12px' }}>
      💡 <strong>Dica:</strong> Use formato JSON válido. Campos disponíveis:
      <ul style={{ marginTop: 8, marginBottom: 0 }}>
        <li><code>fields</code>: Array de campos do formulário</li>
        <li><code>required_metadata</code>: Campos metadata obrigatórios</li>
        <li><code>optional_metadata</code>: Campos metadata opcionais</li>
      </ul>
    </Text>
  </div>
</Modal>
```

#### 7. Imports Necessários

Adicionar no topo do arquivo:

```typescript
import { EditOutlined } from '@ant-design/icons';  // Se ainda não tiver
import { Input } from 'antd';  // Se ainda não tiver
```

---

## 📊 Estrutura do KV Após Implementação

```json
{
  "all_types": [
    {
      "id": "icmp",
      "display_name": "ICMP (Ping)",
      "category": "network-probes",
      "job_name": "icmp",
      "exporter_type": "blackbox",
      "module": "icmp",
      "metrics_path": "/probe",
      "server": "172.16.1.26",
      "form_schema": {  // ✅ ADICIONADO!
        "fields": [
          {
            "name": "target",
            "label": "Alvo (IP ou Hostname)",
            "type": "text",
            "required": true,
            "validation": {"type": "ip_or_hostname"},
            "placeholder": "192.168.1.1 ou exemplo.com",
            "help": "Endereço IP ou hostname a ser monitorado"
          },
          {
            "name": "module",
            "label": "Módulo Blackbox",
            "type": "select",
            "required": true,
            "default": "icmp",
            "options": [
              {"value": "icmp", "label": "ICMP (Ping)"},
              {"value": "tcp_connect", "label": "TCP Connect"},
              {"value": "http_2xx", "label": "HTTP 2xx"}
            ]
          }
        ],
        "required_metadata": ["target", "module"],
        "optional_metadata": []
      }
    },
    {
      "id": "node_exporter",
      "display_name": "Node Exporter (Linux)",
      "category": "system-exporters",
      "job_name": "node_exporter",
      "exporter_type": "node_exporter",
      "module": null,
      "metrics_path": "/metrics",
      "server": "172.16.1.26",
      "form_schema": {  // ✅ Pode ser adicionado depois
        "fields": [
          {
            "name": "target",
            "label": "IP do Servidor",
            "type": "text",
            "required": true
          },
          {
            "name": "port",
            "label": "Porta",
            "type": "number",
            "required": false,
            "default": 9100,
            "min": 1,
            "max": 65535
          }
        ],
        "required_metadata": ["target"],
        "optional_metadata": ["port"]
      }
    }
  ]
}
```

---

## 🚀 Próximos Passos (Para Cursor Continuar)

### PASSO 1: Implementar Modal em MonitoringTypes.tsx (30 min)

1. ✅ Adicionar estados (formSchemaModalVisible, editingType, formSchemaJSON, jsonError)
2. ✅ Adicionar handlers (handleEditFormSchema, handleSaveFormSchema)
3. ✅ Adicionar validação JSON (useEffect)
4. ✅ Adicionar coluna "Ações" na tabela
5. ✅ Adicionar Modal JSX
6. ✅ Adicionar imports necessários

### PASSO 2: Testar Funcionalidade (10 min)

```bash
# 1. Iniciar backend
cd backend
python app.py

# 2. Iniciar frontend
cd frontend
npm run dev

# 3. Acessar http://localhost:8081/monitoring-types

# 4. Clicar em "Form Schema" em um tipo (ex: icmp)

# 5. Editar JSON:
{
  "fields": [
    {
      "name": "target",
      "label": "Alvo (IP ou Hostname)",
      "type": "text",
      "required": true,
      "placeholder": "192.168.1.1"
    }
  ],
  "required_metadata": ["target"],
  "optional_metadata": []
}

# 6. Salvar

# 7. Verificar no KV:
curl -H "X-Consul-Token: 8382a112-81e0-cd6d-2b92-8565925a0675" \
  http://172.16.1.26:8500/v1/kv/skills/eye/monitoring-types?raw | \
  jq '.all_types[] | select(.id == "icmp") | .form_schema'
```

### PASSO 3: Integrar com DynamicCRUDModal (Sprint 2)

Quando criar serviço em DynamicMonitoringPage:

```typescript
// 1. Usuário seleciona tipo (ex: icmp)
const selectedType = allTypes.find(t => t.id === 'icmp');

// 2. Buscar form_schema do tipo
const formSchema = selectedType.form_schema;

// 3. Renderizar campos dinamicamente
formSchema.fields.map(field => (
  <FormFieldRenderer field={field} />
))
```

---

## ✅ Vantagens da Solução

1. **✅ Zero Duplicação** - 1 tipo = 1 form_schema (sem ambiguidade)
2. **✅ KV como Fonte Única** - Não precisa sincronizar com rules
3. **✅ Backend Pronto** - Endpoint funcional e testável
4. **✅ API Simples** - Uma função, fácil de usar
5. **✅ Rápido** - 2-3h total vs 11h da solução complexa

---

## 📝 Resumo de Arquivos Modificados

### Backend
- ✅ `backend/api/monitoring_types_dynamic.py` (+107 linhas)
  - Modelo `FormSchemaUpdateRequest`
  - Endpoint `PUT /type/{type_id}/form-schema`

### Frontend
- ✅ `frontend/src/services/api.ts` (+8 linhas)
  - Função `updateTypeFormSchema()`

- ⏳ `frontend/src/pages/MonitoringTypes.tsx` (PENDENTE)
  - Estados para modal
  - Handlers
  - Validação JSON
  - Coluna "Ações"
  - Modal JSX

---

## 🎯 Para o Cursor Continuar

**Cursor, por favor:**

1. Implemente o modal em `MonitoringTypes.tsx` conforme especificado acima
2. Teste a funcionalidade localmente
3. Verifique que form_schema é salvo no KV corretamente
4. Continue com Sprint 2 (DynamicCRUDModal) usando form_schema dos tipos

**Estrutura clara:**
- ✅ Backend: 100% pronto
- ✅ API: 100% pronta
- ⏳ UI: Falta apenas o modal (30 min)

---

**Documento criado em:** 2025-11-18
**Implementação backend:** Claude Code (Sonnet 4.5)
**Próxima etapa:** Cursor AI completa frontend modal
**Status:** 🟢 Pronto para continuar
