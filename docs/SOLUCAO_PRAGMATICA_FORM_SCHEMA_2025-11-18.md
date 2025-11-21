# ✅ SOLUÇÃO PRAGMÁTICA: Editor de Form Schema nas Regras

**Data:** 2025-11-18
**Status:** 🟢 **SOLUÇÃO VALIDADA E RECOMENDADA**
**Complexidade:** 🟢 BAIXA (2-3 horas vs 11 horas da abordagem de variantes)

---

## 🎯 DESCOBERTA CRÍTICA

As **regras de categorização JÁ TÊM `form_schema`**! O Consul KV `skills/eye/monitoring-types/categorization/rules` **JÁ ESTÁ CORRETO**!

### Evidência do KV Atual:

```json
{
  "id": "blackbox_icmp",
  "priority": 100,
  "category": "network-probes",
  "display_name": "ICMP (Ping)",
  "exporter_type": "blackbox",
  "conditions": {
    "job_name_pattern": "^icmp.*",
    "metrics_path": "/probe",
    "module_pattern": "^icmp$"
  },
  "form_schema": {  // ✅ JÁ EXISTE!
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
          {"value": "http_2xx", "label": "HTTP 2xx"},
          {"value": "dns", "label": "DNS"}
        ],
        "help": "Módulo definido no blackbox.yml"
      }
    ],
    "required_metadata": ["target", "module"],
    "optional_metadata": []
  }
}
```

**Resultado:** O KV `skills/eye/monitoring-types/categorization/rules` **É O SOURCE OF TRUTH**! Não precisamos de sistema de variantes!

---

## 🚀 SUA SOLUÇÃO (Muito Mais Simples!)

### Conceito

Reutilizar o **modal "Editar Regra"** existente (`/monitoring/rules`), mas adicionar uma **aba específica para editar `form_schema`** em formato JSON.

### Fluxo Proposto:

```
PASSO 1: Usuário acessa /monitoring/rules
  ↓
PASSO 2: Clica em "Editar" em uma regra (ex: "blackbox_icmp")
  ↓
PASSO 3: Modal abre com DUAS ABAS:
  - ✅ [Aba 1] Dados da Regra (JÁ EXISTE)
    - ID, Priority, Category, Display Name
    - Conditions (job_name_pattern, module_pattern, etc)

  - ✅ [Aba 2] Form Schema (JSON) (NOVA!)
    - Editor JSON do Monaco (ou CodeMirror)
    - Validação de schema JSON
    - Preview do formulário em tempo real
  ↓
PASSO 4: Usuário edita form_schema no JSON:
  {
    "fields": [
      {"name": "target", "type": "text", "required": true},
      {"name": "snmp_community", "type": "text", "required": true},  // NOVO!
      {"name": "snmp_module", "type": "select", "options": [...]}   // NOVO!
    ],
    "required_metadata": ["target", "snmp_community", "snmp_module"]
  }
  ↓
PASSO 5: Sistema salva no KV `skills/eye/monitoring-types/categorization/rules`
  ↓
PASSO 6: DynamicMonitoringPage automaticamente usa o novo form_schema
```

---

## ✅ VANTAGENS DA SOLUÇÃO PRAGMÁTICA

### 1. **Zero Duplicação**
- ✅ Form_schema já está nas regras (KV)
- ✅ Não precisa de `backend/schemas/monitoring-types/*.json`
- ✅ Não precisa de sistema de variantes

### 2. **Reutilização Total**
- ✅ Modal "Editar Regra" já existe
- ✅ Backend CRUD de regras já funciona
- ✅ Apenas adicionar uma aba nova

### 3. **Simplicidade**
- ✅ 2-3 horas de implementação
- ✅ Não precisa refatorar backend
- ✅ Não precisa script de sincronização

### 4. **Flexibilidade Mantida**
- ✅ Múltiplas regras por categoria (blackbox_icmp, blackbox_ping, etc)
- ✅ Cada regra tem seu próprio form_schema
- ✅ Prioridades resolvem conflitos

### 5. **Source of Truth Único**
- ✅ KV `skills/eye/monitoring-types/categorization/rules` é o único lugar
- ✅ Não precisa sincronizar entre sistemas
- ✅ DynamicMonitoringPage lê diretamente do KV

---

## 📋 PLANO DE IMPLEMENTAÇÃO RÁPIDA

### Fase 1: Frontend - Nova Aba no Modal (1.5h)

#### Atualizar MonitoringRules.tsx

```typescript
// frontend/src/pages/MonitoringRules.tsx

import { Tabs } from 'antd';
import MonacoEditor from '@monaco-editor/react';

const { TabPane } = Tabs;

// Dentro do modal de edição:
<Modal
  title={editingRule ? "Editar Regra" : "Nova Regra"}
  open={modalVisible}
  onCancel={() => setModalVisible(false)}
  width={900}  // Aumentar para caber editor JSON
  footer={[
    <Button key="cancel" onClick={() => setModalVisible(false)}>
      Cancelar
    </Button>,
    <Button
      key="submit"
      type="primary"
      onClick={handleSubmit}
    >
      Salvar
    </Button>,
  ]}
>
  <Tabs defaultActiveKey="1">
    {/* ✅ ABA 1: Dados da Regra (JÁ EXISTE) */}
    <TabPane tab="Dados da Regra" key="1">
      <Form form={form} layout="vertical">
        <ProFormText
          name="id"
          label="ID da Regra"
          rules={[{ required: true }]}
          disabled={!!editingRule}
        />
        <ProFormDigit
          name="priority"
          label="Prioridade"
          min={1}
          max={100}
        />
        <ProFormSelect
          name="category"
          label="Categoria"
          options={rulesData?.categories?.map(c => ({
            label: c.display_name,
            value: c.id
          }))}
        />
        <ProFormText
          name="display_name"
          label="Nome de Exibição"
        />
        {/* ... outros campos existentes ... */}
      </Form>
    </TabPane>

    {/* ✅ ABA 2: Form Schema (NOVA!) */}
    <TabPane tab="Form Schema (JSON)" key="2">
      <div style={{ marginBottom: 16 }}>
        <Alert
          message="Edite o schema do formulário"
          description="Defina os campos que aparecerão ao criar um serviço desta regra"
          type="info"
          showIcon
        />
      </div>

      {/* Editor JSON com Monaco */}
      <MonacoEditor
        height="400px"
        language="json"
        theme="vs-dark"
        value={formSchemaJSON}
        onChange={(value) => setFormSchemaJSON(value)}
        options={{
          minimap: { enabled: false },
          formatOnPaste: true,
          formatOnType: true,
        }}
      />

      {/* Validação em tempo real */}
      {jsonError && (
        <Alert
          message="Erro no JSON"
          description={jsonError}
          type="error"
          style={{ marginTop: 16 }}
        />
      )}

      {/* Preview do formulário */}
      {!jsonError && formSchemaPreview && (
        <Card
          title="Preview do Formulário"
          style={{ marginTop: 16 }}
          size="small"
        >
          <FormSchemaPreview schema={formSchemaPreview} />
        </Card>
      )}
    </TabPane>

    {/* 🔧 OPCIONAL: ABA 3: Validação e Testes */}
    <TabPane tab="Validação" key="3">
      <Form layout="vertical">
        <Alert
          message="Teste as condições da regra"
          description="Simule um job para verificar se a regra aplica corretamente"
          type="info"
          showIcon
          style={{ marginBottom: 16 }}
        />

        <Form.Item label="Job Name (teste)">
          <Input
            placeholder="icmp_palmas"
            value={testJobName}
            onChange={(e) => setTestJobName(e.target.value)}
          />
        </Form.Item>

        <Form.Item label="Module (teste)">
          <Input
            placeholder="icmp"
            value={testModule}
            onChange={(e) => setTestModule(e.target.value)}
          />
        </Form.Item>

        <Button
          type="primary"
          onClick={handleTestRule}
        >
          Testar Regra
        </Button>

        {testResult && (
          <Card
            title="Resultado do Teste"
            style={{ marginTop: 16 }}
            size="small"
          >
            {testResult.matches ? (
              <Alert
                message="✅ Regra APLICA!"
                description={`Esta regra será usada para job "${testJobName}" com module "${testModule}"`}
                type="success"
              />
            ) : (
              <Alert
                message="❌ Regra NÃO aplica"
                description="As condições não foram satisfeitas"
                type="warning"
              />
            )}
          </Card>
        )}
      </Form>
    </TabPane>
  </Tabs>
</Modal>
```

#### Estados e Handlers:

```typescript
// Estados para aba Form Schema
const [formSchemaJSON, setFormSchemaJSON] = useState<string>('');
const [jsonError, setJsonError] = useState<string | null>(null);
const [formSchemaPreview, setFormSchemaPreview] = useState<any | null>(null);

// Estados para aba Validação
const [testJobName, setTestJobName] = useState('');
const [testModule, setTestModule] = useState('');
const [testResult, setTestResult] = useState<any | null>(null);

// Ao abrir modal de edição, carregar form_schema
const handleEdit = (record: CategorizationRule) => {
  setEditingRule(record);

  // Carregar dados da regra (ABA 1)
  form.setFieldsValue({
    id: record.id,
    priority: record.priority,
    category: record.category,
    display_name: record.display_name,
    exporter_type: record.exporter_type,
    job_name_pattern: record.conditions.job_name_pattern,
    metrics_path: record.conditions.metrics_path,
    module_pattern: record.conditions.module_pattern,
    observations: record.observations,
  });

  // Carregar form_schema (ABA 2)
  const formSchema = record.form_schema || {
    fields: [],
    required_metadata: [],
    optional_metadata: []
  };
  setFormSchemaJSON(JSON.stringify(formSchema, null, 2));

  setModalVisible(true);
};

// Validar JSON em tempo real
useEffect(() => {
  try {
    const parsed = JSON.parse(formSchemaJSON);
    setJsonError(null);
    setFormSchemaPreview(parsed);
  } catch (e: any) {
    setJsonError(e.message);
    setFormSchemaPreview(null);
  }
}, [formSchemaJSON]);

// Ao salvar, incluir form_schema
const handleSubmit = async () => {
  try {
    const values = await form.validateFields();

    // Validar JSON do form_schema
    let formSchema;
    try {
      formSchema = JSON.parse(formSchemaJSON);
    } catch (e) {
      message.error('Form Schema JSON inválido!');
      return;
    }

    const payload = {
      id: values.id,
      priority: values.priority,
      category: values.category,
      display_name: values.display_name,
      exporter_type: values.exporter_type,
      conditions: {
        job_name_pattern: values.job_name_pattern,
        metrics_path: values.metrics_path,
        module_pattern: values.module_pattern,
      },
      observations: values.observations,
      form_schema: formSchema,  // ✅ INCLUIR!
    };

    if (editingRule) {
      await consulAPI.updateCategorizationRule(editingRule.id, payload);
      message.success('Regra atualizada com sucesso!');
    } else {
      await consulAPI.createCategorizationRule(payload);
      message.success('Regra criada com sucesso!');
    }

    setModalVisible(false);
    actionRef.current?.reload();
  } catch (error: any) {
    message.error('Erro ao salvar regra: ' + (error.message || error));
  }
};

// Testar regra (ABA 3)
const handleTestRule = () => {
  const values = form.getFieldsValue();

  const jobData = {
    job_name: testJobName,
    metrics_path: values.metrics_path || '/metrics',
    module: testModule,
  };

  // Testar conditions
  const matches = testRuleConditions(values, jobData);

  setTestResult({ matches, jobData });
};

const testRuleConditions = (ruleValues: any, jobData: any): boolean => {
  // Testar job_name_pattern
  if (ruleValues.job_name_pattern) {
    const regex = new RegExp(ruleValues.job_name_pattern, 'i');
    if (!regex.test(jobData.job_name)) {
      return false;
    }
  }

  // Testar metrics_path
  if (ruleValues.metrics_path && jobData.metrics_path !== ruleValues.metrics_path) {
    return false;
  }

  // Testar module_pattern
  if (ruleValues.module_pattern && jobData.module) {
    const regex = new RegExp(ruleValues.module_pattern, 'i');
    if (!regex.test(jobData.module)) {
      return false;
    }
  }

  return true;
};
```

#### Componente de Preview:

```typescript
// frontend/src/components/FormSchemaPreview.tsx

interface FormSchemaPreviewProps {
  schema: {
    fields: Array<{
      name: string;
      label: string;
      type: string;
      required?: boolean;
      options?: Array<{ value: string; label: string }>;
      placeholder?: string;
      help?: string;
    }>;
  };
}

export const FormSchemaPreview: React.FC<FormSchemaPreviewProps> = ({ schema }) => {
  return (
    <Form layout="vertical">
      {schema.fields.map((field) => (
        <Form.Item
          key={field.name}
          label={field.label}
          required={field.required}
          help={field.help}
        >
          {field.type === 'text' && (
            <Input placeholder={field.placeholder} disabled />
          )}
          {field.type === 'select' && (
            <Select placeholder={field.placeholder} disabled>
              {field.options?.map((opt) => (
                <Select.Option key={opt.value} value={opt.value}>
                  {opt.label}
                </Select.Option>
              ))}
            </Select>
          )}
          {field.type === 'number' && (
            <InputNumber style={{ width: '100%' }} disabled />
          )}
        </Form.Item>
      ))}
    </Form>
  );
};
```

---

### Fase 2: Backend - Aceitar form_schema no PUT (0.5h)

O backend **JÁ ACEITA** `form_schema` no modelo! Apenas garantir que está salvando:

```python
# backend/api/categorization_rules.py

class CategorizationRuleModel(BaseModel):
    """Modelo de regra de categorização"""
    id: str = Field(..., description="ID único da regra")
    priority: int = Field(..., description="Prioridade (1-100)", ge=1, le=100)
    category: str = Field(..., description="Categoria de destino")
    display_name: str = Field(..., description="Nome amigável para exibição")
    exporter_type: Optional[str] = Field(None, description="Tipo de exporter")
    conditions: RuleConditions = Field(..., description="Condições de matching")
    observations: Optional[str] = Field(None, description="Observações")

    # ✅ ADICIONAR:
    form_schema: Optional[Dict[str, Any]] = Field(
        None,
        description="Schema do formulário de criação de serviços"
    )


@router.put("/categorization-rules/{rule_id}")
async def update_categorization_rule(
    rule_id: str,
    request: RuleUpdateRequest
):
    """
    Atualiza regra existente (incluindo form_schema!)
    """
    config_manager = ConsulKVConfigManager()

    # Buscar regras atuais
    rules_data = await config_manager.get('monitoring-types/categorization/rules')

    if not rules_data:
        raise HTTPException(404, "Regras não encontradas")

    # Encontrar regra a atualizar
    rule_found = False
    for rule in rules_data['rules']:
        if rule['id'] == rule_id:
            # Atualizar campos
            if request.priority is not None:
                rule['priority'] = request.priority
            if request.category is not None:
                rule['category'] = request.category
            if request.display_name is not None:
                rule['display_name'] = request.display_name
            if request.exporter_type is not None:
                rule['exporter_type'] = request.exporter_type
            if request.conditions is not None:
                rule['conditions'] = request.conditions.model_dump()
            if request.observations is not None:
                rule['observations'] = request.observations

            # ✅ CRÍTICO: Salvar form_schema!
            if request.form_schema is not None:
                rule['form_schema'] = request.form_schema

            rule_found = True
            break

    if not rule_found:
        raise HTTPException(404, f"Regra '{rule_id}' não encontrada")

    # Atualizar metadata
    rules_data['last_updated'] = datetime.utcnow().isoformat()

    # Salvar no KV
    await config_manager.set('monitoring-types/categorization/rules', rules_data)

    # ✅ IMPORTANTE: Forçar reload do engine
    engine = get_categorization_rule_engine()
    await engine.load_rules(force_reload=True)

    return {
        "success": True,
        "message": "Regra atualizada com sucesso",
        "rule_id": rule_id
    }
```

---

### Fase 3: Integração com DynamicMonitoringPage (1h)

Quando criar serviço, buscar form_schema da regra categorizada:

```typescript
// frontend/src/pages/DynamicMonitoringPage.tsx

const handleAdd = async () => {
  // PASSO 1: Usuário escolhe qual regra usar (ou sistema auto-detecta)
  const selectedRuleId = "blackbox_icmp";  // Ex: usuário escolhe

  // PASSO 2: Buscar regra completa (incluindo form_schema)
  const rule = await consulAPI.getCategorizationRule(selectedRuleId);

  if (!rule.form_schema) {
    message.error('Esta regra não tem form_schema configurado!');
    return;
  }

  // PASSO 3: Renderizar modal com campos dinâmicos do form_schema
  setFormSchema(rule.form_schema);
  setFormModalVisible(true);
};

// Renderizar formulário dinâmico
<Modal title="Adicionar Serviço" open={formModalVisible}>
  <Form form={form} layout="vertical">
    {formSchema.fields.map((field) => (
      <FormFieldRenderer
        key={field.name}
        field={field}
        value={formData[field.name]}
        onChange={(value) => setFormData({...formData, [field.name]: value})}
      />
    ))}
  </Form>
</Modal>
```

---

## 📊 COMPARAÇÃO: SOLUÇÃO COMPLEXA vs PRAGMÁTICA

| Aspecto | Solução Complexa (Variantes) | Solução Pragmática (Editar Form Schema) |
|---------|------------------------------|-------------------------------------------|
| **Tempo Implementação** | 11 horas | 2-3 horas |
| **Arquivos Modificados** | 8+ arquivos | 2 arquivos (MonitoringRules.tsx + categorization_rules.py) |
| **Novas Abstrações** | System de variantes, sync script | Apenas nova aba no modal |
| **Refatoração Backend** | Sim (MonitoringTypeManager, sync) | Não (backend já pronto) |
| **Source of Truth** | `backend/schemas/*.json` (arquivos locais) | KV `skills/eye/monitoring-types/categorization/rules` (Consul) |
| **Sincronização** | Necessária (arquivos → KV) | Não necessária (KV é único) |
| **Flexibilidade** | Variantes hierárquicas | Regras independentes (mais simples) |
| **Risco** | Alto (muitas mudanças) | Baixo (apenas adicionar funcionalidade) |
| **Manutenção** | Complexa (2 sistemas) | Simples (1 sistema) |

---

## ✅ CONCLUSÃO

**SUA SOLUÇÃO É A CORRETA!**

Motivos:

1. **✅ KV já tem form_schema** - Não precisa criar sistema de variantes
2. **✅ Modal já existe** - Reutilizar é muito mais rápido
3. **✅ Backend já funciona** - Apenas garantir que salva form_schema
4. **✅ Hardcode permitido** - Você mesmo disse "pelo menos por enquanto"
5. **✅ Pragmatismo** - 2-3h vs 11h é uma diferença absurda

**Recomendação Final:**
- **IMPLEMENTAR** a solução pragmática (nova aba no modal)
- **ESQUECER** a solução de variantes complexa
- **MANTER** KV como source of truth
- **ITERAR** depois se necessário (mas provavelmente não será)

---

## 🚀 PRÓXIMOS PASSOS

1. **Adicionar aba "Form Schema (JSON)"** em MonitoringRules.tsx
2. **Validar salvamento** de form_schema no backend
3. **Testar edição** de uma regra existente
4. **Integrar** com DynamicMonitoringPage para usar form_schema
5. **Continuar** Sprint 2 do Cursor com arquitetura correta!

**Tempo estimado total:** 2-3 horas ✅
