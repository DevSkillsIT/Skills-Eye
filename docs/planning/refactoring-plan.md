# REFACTORING PLAN - Implementação Configuration-Driven System

**Data:** 2025-10-31
**Versão:** 1.0
**Baseado em:** `REFACTORING_ARCHITECTURE.md`

---

## 🎯 **OBJETIVO**

Transformar o sistema atual em uma arquitetura **configuration-driven** e **plugin-based**, onde novos tipos de monitoramento podem ser adicionados via UI sem alteração de código.

### ⚠️ **REGRA CRÍTICA: ZERO HARDCODING DE NOMES**

```
❌ PROIBIDO: Assumir nomes fixos ("node_exporter", "selfnode", "blackbox")
✅ OBRIGATÓRIO: Tudo via matchers configuráveis em JSON

Exemplo Real:
- Sistema atual usa "selfnode", "SelfNode Exporter"
- Outra empresa pode usar "node", "node-exporter-custom", "linux-metrics"
- Sistema DEVE funcionar com QUALQUER nome via field mapping
```

**Source of Truth:**
- Prometheus `relabel_configs` → `/api/v1/metadata-dynamic/fields` (já implementado!)
- JSON schemas com `matchers` flexíveis (múltiplos valores aceitos)
- Field mapping layer (renomear campos do Prometheus → UI)

**Ver `REFACTORING_ARCHITECTURE.md` seção "ZERO LOCK-IN" para detalhes completos.**

---

## 📅 **TIMELINE GERAL**

```
┌────────────────────────────────────────────────────────────┐
│ FASE 1: FUNDAÇÃO (4-5 dias)                               │
│ └─ Schemas JSON, Backend API, Tipos TypeScript            │
├────────────────────────────────────────────────────────────┤
│ FASE 2: COMPONENTES BASE (4-5 dias)                       │
│ └─ BaseMonitoringPage, Hooks, Rendering Engine            │
├────────────────────────────────────────────────────────────┤
│ FASE 3: PÁGINAS PILOT (3-4 dias)                          │
│ └─ System Exporters + Network Probes                      │
├────────────────────────────────────────────────────────────┤
│ FASE 4: EXPANSÃO (3-4 dias)                               │
│ └─ Web Probes + Database Exporters + Service Browser      │
├────────────────────────────────────────────────────────────┤
│ FASE 5: ADMIN UI (3-4 dias)                               │
│ └─ Gestão de Tipos, Import/Export, Validação              │
├────────────────────────────────────────────────────────────┤
│ FASE 6: REFINAMENTO (2-3 dias)                            │
│ └─ Migração dados, Testes, Docs, Deprecação páginas antigas│
└────────────────────────────────────────────────────────────┘

TOTAL ESTIMADO: 19-25 dias (aprox. 4-5 semanas)
```

---

## 🏗️ **FASE 1: FUNDAÇÃO (4-5 dias)**

### Objetivo
Criar a base de dados (JSON schemas no Consul KV) e APIs backend para gerenciar tipos de monitoramento.

### Checklist Detalhado

#### 1.1 - Definir JSON Schemas (Dia 1)

**Arquivos a criar:**

- [ ] `backend/schemas/monitoring-type-schema.json` - Meta-schema para validação
- [ ] `backend/schemas/field-schema.json` - Schema de campos metadata
- [ ] `backend/schemas/ui-config-schema.json` - Schema de configurações UI

**JSON Schemas Iniciais no Consul KV:**

- [ ] `skills/cm/monitoring-types/network-probes.json`
  - [ ] ICMP (ping)
  - [ ] TCP Connect
  - [ ] DNS Query
  - [ ] SSH Banner

- [ ] `skills/cm/monitoring-types/web-probes.json`
  - [ ] HTTP 2xx
  - [ ] HTTP 4xx
  - [ ] HTTP 5xx
  - [ ] HTTPS
  - [ ] HTTP POST 2xx

- [ ] `skills/cm/monitoring-types/system-exporters.json`
  - [ ] Node Exporter (Linux)
  - [ ] Windows Exporter
  - [ ] SNMP Exporter

- [ ] `skills/cm/monitoring-types/database-exporters.json`
  - [ ] MySQL Exporter
  - [ ] PostgreSQL Exporter
  - [ ] Redis Exporter
  - [ ] MongoDB Exporter

**Ponto de Validação:**
```bash
# Verificar se JSONs foram salvos no Consul KV
curl -H "X-Consul-Token: ${TOKEN}" \
  http://localhost:8500/v1/kv/skills/cm/monitoring-types/?keys

# Deve retornar:
# ["skills/cm/monitoring-types/network-probes.json", ...]
```

---

#### 1.2 - Backend API - Monitoring Types Manager (Dia 2)

**Arquivos a criar/modificar:**

- [ ] `backend/core/monitoring_type_manager.py`
  - [ ] Classe `MonitoringTypeManager`
  - [ ] Método `get_all_categories()`
  - [ ] Método `get_types_by_category(category)`
  - [ ] Método `get_type_by_id(category, type_id)`
  - [ ] Método `create_type(category, schema)` (Admin)
  - [ ] Método `update_type(category, type_id, schema)` (Admin)
  - [ ] Método `delete_type(category, type_id)` (Admin)
  - [ ] Método `_validate_schema(schema)` - JSON Schema validation
  - [ ] Método `_audit_log(action, category, type_id)` - Audit trail

- [ ] `backend/api/monitoring_types.py` - Novos endpoints
  ```python
  @router.get("/monitoring-types")
  @router.get("/monitoring-types/{category}")
  @router.get("/monitoring-types/{category}/{type_id}")
  @router.post("/monitoring-types")  # Admin only
  @router.put("/monitoring-types/{category}/{type_id}")  # Admin only
  @router.delete("/monitoring-types/{category}/{type_id}")  # Admin only
  @router.post("/monitoring-types/validate")  # Validar schema
  ```

- [ ] `backend/app.py` - Registrar rotas
  ```python
  from api.monitoring_types import router as monitoring_types_router
  app.include_router(monitoring_types_router, prefix="/api/v1")
  ```

**Dependências:**
```bash
# Instalar JSON Schema validator
pip install jsonschema
# Atualizar requirements.txt
pip freeze | grep jsonschema >> requirements.txt
```

**Ponto de Validação:**
```bash
# Testar endpoint GET
curl http://localhost:5000/api/v1/monitoring-types | jq

# Deve retornar:
# {
#   "categories": [
#     {"id": "network-probes", "display_name": "Network Probes (Rede)", ...},
#     ...
#   ]
# }

# Testar validação
curl -X POST http://localhost:5000/api/v1/monitoring-types/validate \
  -H "Content-Type: application/json" \
  -d '{"id": "test", "invalid_field": true}'

# Deve retornar erro de validação
```

---

#### 1.3 - Backend API - Metadata Fields Dynamic (Dia 3)

**Objetivo:** Garantir que o endpoint `/api/v1/metadata-dynamic/fields` retorna campos por contexto

**Modificar:**

- [ ] `backend/api/metadata_fields_manager.py`
  - [ ] Adicionar parâmetro `?monitoring_type=icmp`
  - [ ] Filtrar campos específicos por tipo (se necessário no futuro)
  - [ ] Manter retrocompatibilidade com `?context=exporters`

**Ponto de Validação:**
```bash
# Verificar campos para Network Probes
curl "http://localhost:5000/api/v1/metadata-dynamic/fields?context=network" | jq '.total'

# Deve retornar 19 campos
```

---

#### 1.4 - TypeScript Types Generation (Dia 4)

**Arquivos a criar:**

- [ ] `frontend/src/types/monitoring.ts`
  ```typescript
  export interface MonitoringCategory {
    category: string;
    display_name: string;
    icon: string;
    color: string;
    description: string;
    enabled: boolean;
    order: number;
    types: MonitoringType[];
    page_config: PageConfig;
  }

  export interface MonitoringType {
    id: string;
    display_name: string;
    icon: string;
    description: string;
    exporter_type: string;
    module_name?: string;
    default_port?: number;
    enabled: boolean;
    order: number;
    form_schema: FormSchema;
    table_schema: TableSchema;
    filters: FilterConfig;
    metrics: MetricsConfig;
  }

  export interface FormSchema {
    fields: FormField[];
    required_metadata: string[];
    optional_metadata?: string[];
  }

  export interface FormField {
    name: string;
    label: string;
    type: 'text' | 'number' | 'select' | 'textarea' | 'date';
    required: boolean;
    default?: any;
    options?: string[] | SelectOption[];
    placeholder?: string;
    help?: string;
    validation?: ValidationRules;
  }

  export interface TableSchema {
    default_visible_columns: string[];
    default_sort?: SortConfig;
    row_actions: string[];
    bulk_actions: string[];
  }

  // ... mais interfaces
  ```

- [ ] `frontend/src/services/api.ts` - Adicionar chamadas
  ```typescript
  export const monitoringTypeAPI = {
    getAllCategories: () =>
      axios.get<MonitoringCategoriesResponse>('/api/v1/monitoring-types'),

    getCategory: (category: string) =>
      axios.get<MonitoringCategory>(`/api/v1/monitoring-types/${category}`),

    getType: (category: string, typeId: string) =>
      axios.get<MonitoringType>(`/api/v1/monitoring-types/${category}/${typeId}`),

    createType: (category: string, schema: Partial<MonitoringType>) =>
      axios.post(`/api/v1/monitoring-types`, { category, ...schema }),

    updateType: (category: string, typeId: string, schema: Partial<MonitoringType>) =>
      axios.put(`/api/v1/monitoring-types/${category}/${typeId}`, schema),

    deleteType: (category: string, typeId: string) =>
      axios.delete(`/api/v1/monitoring-types/${category}/${typeId}`),

    validateSchema: (schema: any) =>
      axios.post<ValidationResponse>('/api/v1/monitoring-types/validate', schema),
  };
  ```

**Ponto de Validação:**
```bash
# Compilar TypeScript sem erros
cd frontend && npx tsc --noEmit

# Deve retornar sem erros
```

---

#### 1.5 - Testes Unitários (Dia 5)

**Arquivos a criar:**

- [ ] `backend/tests/test_monitoring_type_manager.py`
  - [ ] Test: `test_get_all_categories()`
  - [ ] Test: `test_get_types_by_category()`
  - [ ] Test: `test_create_type_success()`
  - [ ] Test: `test_create_type_duplicate_error()`
  - [ ] Test: `test_validate_schema_invalid()`

**Executar:**
```bash
cd backend
pytest tests/test_monitoring_type_manager.py -v

# Deve passar 100%
```

**✅ FASE 1 CONCLUÍDA - Checkpoint:**
- [ ] JSON Schemas salvos no Consul KV
- [ ] Backend API funcionando (`/api/v1/monitoring-types`)
- [ ] TypeScript types gerados
- [ ] Testes passando

---

## ⚛️ **FASE 2: COMPONENTES BASE (4-5 dias)**

### Objetivo
Criar componentes React genéricos que renderizam baseado em schemas JSON.

### Checklist Detalhado

#### 2.1 - Hook useMonitoringType (Dia 1)

**Arquivo:**

- [ ] `frontend/src/hooks/useMonitoringType.ts`
  ```typescript
  import { useQuery } from '@tanstack/react-query';
  import { monitoringTypeAPI } from '@/services/api';

  export function useMonitoringType(category: string, typeId?: string) {
    const { data, isLoading, error, refetch } = useQuery({
      queryKey: ['monitoring-type', category, typeId],
      queryFn: async () => {
        if (typeId) {
          const response = await monitoringTypeAPI.getType(category, typeId);
          return response.data;
        }
        const response = await monitoringTypeAPI.getCategory(category);
        return response.data;
      },
      staleTime: 5 * 60 * 1000, // Cache 5 min
      retry: 2,
    });

    return {
      schema: data,
      loading: isLoading,
      error,
      reload: refetch,
    };
  }
  ```

**Dependências:**
```bash
cd frontend
npm install @tanstack/react-query
```

**Ponto de Validação:**
```typescript
// Criar test component
function TestComponent() {
  const { schema, loading } = useMonitoringType('network-probes');
  return <div>{loading ? 'Loading...' : schema?.display_name}</div>;
}

// Deve mostrar "Network Probes (Rede)"
```

---

#### 2.2 - Column Generator Utilities (Dia 2)

**Arquivo:**

- [ ] `frontend/src/utils/columnGenerators.ts`
  ```typescript
  import { ProColumns } from '@ant-design/pro-components';
  import { MonitoringType, TableSchema } from '@/types/monitoring';
  import { MetadataFieldDynamic } from '@/services/api';

  export function generateColumnsFromSchema<T>(
    tableSchema: TableSchema,
    metadataFields: MetadataFieldDynamic[],
    type?: MonitoringType
  ): ProColumns<T>[] {
    const columns: ProColumns<T>[] = [];

    // PASSO 1: Adicionar colunas fixas do tipo
    tableSchema.default_visible_columns.forEach((colKey) => {
      if (colKey in FIXED_COLUMN_GENERATORS) {
        const generator = FIXED_COLUMN_GENERATORS[colKey];
        columns.push(generator(type));
      }
    });

    // PASSO 2: Adicionar colunas metadata dinâmicas
    metadataFields.forEach((field) => {
      if (tableSchema.default_visible_columns.includes(field.name)) {
        columns.push(generateMetadataColumn(field));
      }
    });

    // PASSO 3: Adicionar coluna de ações
    if (tableSchema.row_actions && tableSchema.row_actions.length > 0) {
      columns.push(generateActionsColumn(tableSchema.row_actions));
    }

    return columns;
  }

  // Geradores de colunas fixas
  const FIXED_COLUMN_GENERATORS: Record<string, (type?: MonitoringType) => ProColumns<any>> = {
    target: (type) => ({
      title: 'Alvo',
      dataIndex: 'target',
      key: 'target',
      width: 250,
      ellipsis: true,
      copyable: true,
      render: (text) => <Text strong>{text}</Text>,
    }),

    status: () => ({
      title: 'Status',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (_, record) => (
        <Badge
          status={record.status === 'up' ? 'success' : 'error'}
          text={record.status === 'up' ? 'Online' : 'Offline'}
        />
      ),
    }),

    // ... mais geradores
  };

  function generateMetadataColumn(field: MetadataFieldDynamic): ProColumns<any> {
    return {
      title: field.display_name,
      dataIndex: ['meta', field.name],
      key: field.name,
      width: field.field_type === 'string' ? 200 : 140,
      ellipsis: true,
      tooltip: field.description,
      render: (value) => {
        if (!value) return <Text type="secondary">-</Text>;

        // Render especial para tipo_monitoramento
        if (field.name === 'tipo_monitoramento') {
          const colors = {
            prod: 'red',
            hml: 'orange',
            dev: 'blue',
            test: 'green',
          };
          return <Tag color={colors[value.toLowerCase()]}>{value}</Tag>;
        }

        return String(value);
      },
    };
  }
  ```

**Ponto de Validação:**
```typescript
// Test
const mockSchema = { default_visible_columns: ['target', 'status', 'company'] };
const mockFields = [{ name: 'company', display_name: 'Empresa', ... }];

const columns = generateColumnsFromSchema(mockSchema, mockFields);
console.log(columns.length); // Deve ser 3
```

---

#### 2.3 - Filter Generator Utilities (Dia 2)

**Arquivo:**

- [ ] `frontend/src/utils/filterGenerators.ts`
  ```typescript
  import { FilterConfig } from '@/types/monitoring';
  import { MetadataFieldDynamic } from '@/services/api';

  export function generateFiltersFromSchema(
    filterConfig: FilterConfig,
    metadataFields: MetadataFieldDynamic[]
  ): MetadataFieldDynamic[] {
    // Retorna apenas campos que estão em quick_filters ou advanced_filters
    return metadataFields.filter((field) =>
      filterConfig.quick_filters?.includes(field.name) ||
      filterConfig.advanced_filters?.includes(field.name)
    );
  }
  ```

---

#### 2.4 - BaseMonitoringPage Component (Dia 3-4)

**Arquivo:**

- [ ] `frontend/src/components/base/BaseMonitoringPage.tsx`
  - [ ] Estrutura básica com ProTable
  - [ ] Integração com useMonitoringType hook
  - [ ] Integração com useTableFields hook
  - [ ] Renderização dinâmica de colunas
  - [ ] Renderização dinâmica de filtros
  - [ ] Suporte a bulk actions
  - [ ] Suporte a row actions
  - [ ] Summary cards dinâmicos
  - [ ] Export data

**Implementação:** Ver `REFACTORING_ARCHITECTURE.md` seção "LAYER 3 & 4" para código completo

**Ponto de Validação:**
```typescript
// Criar página de teste
function TestPage() {
  return (
    <BaseMonitoringPage
      category="network-probes"
      typeId="icmp"
      apiEndpoint="/api/v1/services"
    />
  );
}

// Deve renderizar tabela com colunas dinâmicas
// Deve mostrar apenas serviços com module=icmp
```

---

#### 2.5 - Testes de Componentes (Dia 5)

**Arquivos:**

- [ ] `frontend/src/components/base/__tests__/BaseMonitoringPage.test.tsx`
  - [ ] Test: Renderiza loading state
  - [ ] Test: Renderiza colunas baseado em schema
  - [ ] Test: Aplica filtros corretamente
  - [ ] Test: Bulk actions funcionam
  - [ ] Test: Fallback quando schema não carrega

```bash
cd frontend
npm test -- BaseMonitoringPage
# Deve passar 100%
```

**✅ FASE 2 CONCLUÍDA - Checkpoint:**
- [ ] Hook useMonitoringType funcionando
- [ ] Column generators criados
- [ ] BaseMonitoringPage implementado
- [ ] Testes de componentes passando

---

## 🚀 **FASE 3: PÁGINAS PILOT (3-4 dias)**

### Objetivo
Criar primeiras páginas reais usando BaseMonitoringPage para validar arquitetura.

### Checklist Detalhado

#### 3.1 - System Exporters Page (Dia 1)

**Arquivos a criar:**

- [ ] `frontend/src/pages/SystemExporters.tsx`
  ```typescript
  import React from 'react';
  import { BaseMonitoringPage } from '@/components/base/BaseMonitoringPage';

  interface SystemExporterData {
    id: string;
    node: string;
    exporterType: 'node' | 'windows' | 'snmp';
    address: string;
    port: number;
    meta: Record<string, any>;
  }

  export default function SystemExporters() {
    return (
      <BaseMonitoringPage<SystemExporterData>
        category="system-exporters"
        apiEndpoint="/api/v1/services"
        onRowClick={(record) => {
          // Abrir drawer de detalhes
          Modal.info({
            title: 'Detalhes do Exporter',
            content: <pre>{JSON.stringify(record, null, 2)}</pre>,
          });
        }}
        onBulkAction={async (action, selectedRows) => {
          if (action === 'delete') {
            Modal.confirm({
              title: `Remover ${selectedRows.length} exporters?`,
              content: 'Esta ação não pode ser desfeita.',
              onOk: async () => {
                // Implementar remoção em lote
                await Promise.all(
                  selectedRows.map(row => consulAPI.deregisterService({
                    node_addr: row.node,
                    service_id: row.id,
                  }))
                );
                message.success(`${selectedRows.length} exporters removidos`);
              },
            });
          }
        }}
      />
    );
  }
  ```

- [ ] `frontend/src/App.tsx` - Adicionar rota
  ```typescript
  import SystemExporters from './pages/SystemExporters';

  <Route path="/system-exporters" element={<SystemExporters />} />
  ```

**Ponto de Validação:**
- [ ] Abrir `http://localhost:8081/system-exporters`
- [ ] Verificar que mostra Node, Windows e SNMP exporters
- [ ] Testar filtros por tipo
- [ ] Testar seleção e bulk delete
- [ ] Verificar que colunas metadata aparecem

---

#### 3.2 - Network Probes Page (Dia 2)

**Arquivos a criar:**

- [ ] `frontend/src/pages/NetworkProbes.tsx`
  - Similar a SystemExporters, mas `category="network-probes"`
  - Deve mostrar ICMP, TCP, DNS, SSH

**Sub-páginas (opcional):**

- [ ] `frontend/src/pages/NetworkProbes/IcmpProbes.tsx`
  - `category="network-probes"`, `typeId="icmp"`
  - Mostra apenas pings

- [ ] `frontend/src/pages/NetworkProbes/TcpProbes.tsx`
  - `typeId="tcp"`

**Menu Structure:**
```
Network Probes (Rede)
├─ Todos
├─ ICMP (Ping)
├─ TCP Connect
├─ DNS Query
└─ SSH Banner
```

**Ponto de Validação:**
- [ ] Abrir `http://localhost:8081/network-probes`
- [ ] Verificar que mostra todos os tipos
- [ ] Filtrar por tipo específico
- [ ] Testar cadastro de novo ICMP target
- [ ] Verificar que status (up/down) aparece corretamente

---

#### 3.3 - Form Creation Modal (Dia 3)

**Problema:** BaseMonitoringPage precisa de modal de criação/edição dinâmico

**Arquivo a criar:**

- [ ] `frontend/src/components/base/MonitoringFormModal.tsx`
  ```typescript
  import { ModalForm, ProFormField } from '@ant-design/pro-components';
  import { FormSchema } from '@/types/monitoring';

  interface MonitoringFormModalProps {
    visible: boolean;
    schema: FormSchema;
    initialValues?: Record<string, any>;
    onSubmit: (values: Record<string, any>) => Promise<void>;
    onCancel: () => void;
  }

  export function MonitoringFormModal({
    visible,
    schema,
    initialValues,
    onSubmit,
    onCancel,
  }: MonitoringFormModalProps) {
    return (
      <ModalForm
        title={initialValues ? 'Editar' : 'Adicionar'}
        open={visible}
        modalProps={{ onCancel }}
        onFinish={onSubmit}
        initialValues={initialValues}
      >
        {/* Renderizar campos dinamicamente do schema */}
        {schema.fields.map((field) => (
          <ProFormField
            key={field.name}
            name={field.name}
            label={field.label}
            {...getFieldProps(field)}
          />
        ))}

        {/* Campos metadata obrigatórios */}
        {schema.required_metadata.map((metaField) => (
          <ProFormText
            key={metaField}
            name={['meta', metaField]}
            label={getMetadataFieldLabel(metaField)}
            required
          />
        ))}
      </ModalForm>
    );
  }

  function getFieldProps(field: FormField) {
    const commonProps = {
      rules: [
        { required: field.required, message: `${field.label} é obrigatório` },
        ...(field.validation ? [field.validation] : []),
      ],
      placeholder: field.placeholder,
      tooltip: field.help,
    };

    switch (field.type) {
      case 'select':
        return {
          ...commonProps,
          valueType: 'select',
          options: field.options,
        };
      case 'number':
        return {
          ...commonProps,
          valueType: 'digit',
        };
      case 'textarea':
        return {
          ...commonProps,
          valueType: 'textarea',
        };
      default:
        return commonProps;
    }
  }
  ```

**Integrar em BaseMonitoringPage:**
```typescript
const [formVisible, setFormVisible] = useState(false);
const [editingRecord, setEditingRecord] = useState<T | null>(null);

// Botão "Adicionar"
extra={[
  <Button
    key="add"
    type="primary"
    icon={<PlusOutlined />}
    onClick={() => setFormVisible(true)}
  >
    Adicionar {schema?.display_name_singular}
  </Button>
]}

// Modal
<MonitoringFormModal
  visible={formVisible}
  schema={schema?.form_schema}
  initialValues={editingRecord}
  onSubmit={handleSubmit}
  onCancel={() => {
    setFormVisible(false);
    setEditingRecord(null);
  }}
/>
```

**Ponto de Validação:**
- [ ] Clicar em "Adicionar" abre modal
- [ ] Modal renderiza campos do schema JSON
- [ ] Validações funcionam
- [ ] Submit envia para backend

---

#### 3.4 - Backend Filtering by Type (Dia 4)

**Problema:** `/api/v1/services` retorna TODOS os serviços, precisa filtrar por tipo

**Modificar:**

- [ ] `backend/api/services.py`
  ```python
  @router.get("/services")
  async def get_services(
      node_addr: Optional[str] = None,
      monitoring_type: Optional[str] = None,  # NOVO
      exporter_type: Optional[str] = None,    # NOVO
  ):
      services = await consul_manager.get_all_services(node_addr)

      # Filtrar por monitoring_type (ex: 'icmp', 'tcp')
      if monitoring_type:
          services = [
              s for s in services
              if s.get('Meta', {}).get('module') == monitoring_type
          ]

      # Filtrar por exporter_type (ex: 'blackbox', 'node')
      if exporter_type:
          services = [
              s for s in services
              if s.get('Meta', {}).get('exporter_type') == exporter_type
          ]

      return {"services": services, "total": len(services)}
  ```

**Atualizar Frontend:**
```typescript
// BaseMonitoringPage.tsx
const queryParams = useMemo(() => {
  const params: Record<string, any> = { ...tableParams };

  // Adicionar filtro por tipo
  if (typeId) {
    params.monitoring_type = typeId;
  }

  // Adicionar filtro por exporter_type da categoria
  if (schema?.types[0]?.exporter_type) {
    params.exporter_type = schema.types[0].exporter_type;
  }

  return params;
}, [typeId, schema, tableParams]);
```

**Ponto de Validação:**
```bash
# Testar filtro por tipo
curl "http://localhost:5000/api/v1/services?monitoring_type=icmp" | jq '.total'

# Deve retornar apenas serviços ICMP
```

---

**✅ FASE 3 CONCLUÍDA - Checkpoint:**
- [ ] System Exporters page funcionando
- [ ] Network Probes page funcionando
- [ ] Form modal dinâmico implementado
- [ ] Backend filtrando por tipo corretamente

---

## 🌐 **FASE 4: EXPANSÃO (3-4 dias)**

### Objetivo
Criar as páginas restantes e consolidar padrões.

### Checklist Detalhado

#### 4.1 - Web Probes Page (Dia 1)

- [ ] `frontend/src/pages/WebProbes.tsx`
  - `category="web-probes"`
  - Tipos: http_2xx, http_4xx, http_5xx, https, http_post_2xx

**Ponto de Validação:**
- [ ] Página renderiza corretamente
- [ ] Filtros por tipo HTTP funcionam
- [ ] Cadastro de novo HTTP check funciona

---

#### 4.2 - Database Exporters Page (Dia 2)

- [ ] `frontend/src/pages/DatabaseExporters.tsx`
  - `category="database-exporters"`
  - Tipos: mysql, postgresql, redis, mongodb

**Ponto de Validação:**
- [ ] Mostra apenas database exporters
- [ ] Bulk actions funcionam

---

#### 4.3 - Service Browser (Admin) (Dia 3)

**Objetivo:** Página raw de TODOS os serviços Consul (troubleshooting)

- [ ] `frontend/src/pages/ServiceBrowser.tsx`
  - Não usa BaseMonitoringPage (é raw)
  - Mostra TODOS os serviços sem filtro
  - Colunas: id, service, node, address, port, tags, meta (expandido)
  - Busca avançada por qualquer campo
  - Export JSON completo

**Ponto de Validação:**
- [ ] Mostra 100% dos serviços cadastrados
- [ ] Busca por qualquer campo funciona
- [ ] Export JSON funciona

---

#### 4.4 - Menu & Routing (Dia 4)

**Atualizar menu principal:**

```typescript
// frontend/src/layouts/MainLayout.tsx

const menuItems = [
  {
    key: 'network',
    icon: <RadarChartOutlined />,
    label: 'Network Probes (Rede)',
    children: [
      { key: '/network-probes', label: 'Todos' },
      { key: '/network-probes/icmp', label: 'ICMP (Ping)' },
      { key: '/network-probes/tcp', label: 'TCP Connect' },
      { key: '/network-probes/dns', label: 'DNS Query' },
      { key: '/network-probes/ssh', label: 'SSH Banner' },
    ],
  },
  {
    key: 'web',
    icon: <GlobalOutlined />,
    label: 'Web Probes (Aplicações)',
    children: [
      { key: '/web-probes', label: 'Todos' },
      { key: '/web-probes/http-2xx', label: 'HTTP 2xx' },
      { key: '/web-probes/https', label: 'HTTPS' },
    ],
  },
  {
    key: 'system',
    icon: <DatabaseOutlined />,
    label: 'Exporters: Sistemas',
    children: [
      { key: '/system-exporters', label: 'Todos' },
      { key: '/system-exporters/node', label: 'Node (Linux)' },
      { key: '/system-exporters/windows', label: 'Windows' },
      { key: '/system-exporters/snmp', label: 'SNMP' },
    ],
  },
  {
    key: 'database',
    icon: <DatabaseOutlined />,
    label: 'Exporters: Bancos',
    children: [
      { key: '/database-exporters', label: 'Todos' },
      { key: '/database-exporters/mysql', label: 'MySQL' },
      { key: '/database-exporters/postgresql', label: 'PostgreSQL' },
      { key: '/database-exporters/redis', label: 'Redis' },
      { key: '/database-exporters/mongodb', label: 'MongoDB' },
    ],
  },
  {
    type: 'divider',
  },
  {
    key: 'admin',
    icon: <ToolOutlined />,
    label: 'Administração',
    children: [
      { key: '/service-browser', label: 'Service Browser (Debug)' },
      { key: '/admin/monitoring-types', label: 'Gestão de Tipos' },
    ],
  },
];
```

**Deprecar páginas antigas (opcional):**
```typescript
// Adicionar banner de deprecação
{/* Páginas antigas */}
<Route path="/services" element={
  <>
    <Alert
      type="warning"
      message="Esta página está obsoleta. Use 'Service Browser' no menu Admin."
      closable
    />
    <ServicesOLD />
  </>
} />
```

---

**✅ FASE 4 CONCLUÍDA - Checkpoint:**
- [ ] Todas as 5 páginas principais criadas
- [ ] Menu atualizado
- [ ] Routing configurado
- [ ] Service Browser (admin) funcionando

---

## 🛠️ **FASE 5: ADMIN UI (3-4 dias)**

### Objetivo
Criar interface de administração para gerenciar tipos de monitoramento.

### Checklist Detalhado

#### 5.1 - Monitoring Types Management Page (Dia 1-2)

**Arquivo:**

- [ ] `frontend/src/pages/Admin/MonitoringTypes.tsx`
  ```typescript
  import { ProTable } from '@ant-design/pro-components';
  import { monitoringTypeAPI } from '@/services/api';

  export default function MonitoringTypesAdmin() {
    const [categories, setCategories] = useState<MonitoringCategory[]>([]);
    const [selectedCategory, setSelectedCategory] = useState('network-probes');

    useEffect(() => {
      loadCategories();
    }, []);

    async function loadCategories() {
      const response = await monitoringTypeAPI.getAllCategories();
      setCategories(response.data.categories);
    }

    return (
      <PageContainer title="Gestão de Tipos de Monitoramento">
        <Card>
          <Tabs activeKey={selectedCategory} onChange={setSelectedCategory}>
            {categories.map(category => (
              <TabPane tab={category.display_name} key={category.category}>
                <TypesTable
                  category={category.category}
                  types={category.types}
                  onEdit={handleEdit}
                  onCreate={handleCreate}
                  onDelete={handleDelete}
                />
              </TabPane>
            ))}
          </Tabs>
        </Card>
      </PageContainer>
    );
  }

  function TypesTable({ category, types, onEdit, onCreate, onDelete }) {
    return (
      <>
        <Button
          type="primary"
          icon={<PlusOutlined />}
          onClick={() => onCreate(category)}
          style={{ marginBottom: 16 }}
        >
          Adicionar Novo Tipo
        </Button>

        <Table
          dataSource={types}
          columns={[
            {
              title: 'ID',
              dataIndex: 'id',
              key: 'id',
            },
            {
              title: 'Nome',
              dataIndex: 'display_name',
              key: 'display_name',
              render: (text, record) => (
                <Space>
                  <span>{record.icon}</span>
                  <Text strong>{text}</Text>
                </Space>
              ),
            },
            {
              title: 'Exporter',
              dataIndex: 'exporter_type',
              key: 'exporter_type',
              render: (text) => <Tag>{text}</Tag>,
            },
            {
              title: 'Módulo',
              dataIndex: 'module_name',
              key: 'module_name',
            },
            {
              title: 'Status',
              dataIndex: 'enabled',
              key: 'enabled',
              render: (enabled) => (
                <Badge
                  status={enabled ? 'success' : 'default'}
                  text={enabled ? 'Ativo' : 'Inativo'}
                />
              ),
            },
            {
              title: 'Ações',
              key: 'actions',
              render: (_, record) => (
                <Space>
                  <Button
                    type="link"
                    icon={<EditOutlined />}
                    onClick={() => onEdit(category, record)}
                  >
                    Editar
                  </Button>
                  <Popconfirm
                    title="Remover este tipo?"
                    description="Esta ação não pode ser desfeita."
                    onConfirm={() => onDelete(category, record.id)}
                  >
                    <Button
                      type="link"
                      danger
                      icon={<DeleteOutlined />}
                    >
                      Remover
                    </Button>
                  </Popconfirm>
                </Space>
              ),
            },
          ]}
        />
      </>
    );
  }
  ```

**Ponto de Validação:**
- [ ] Listar todos os tipos configurados
- [ ] Editar um tipo existente
- [ ] Ver mudanças refletidas imediatamente nas páginas

---

#### 5.2 - Type Form Modal (Dia 3)

**Arquivo:**

- [ ] `frontend/src/pages/Admin/MonitoringTypeFormModal.tsx`
  - Form para criar/editar tipo
  - Campos: id, display_name, icon, description, exporter_type, module_name
  - JSON Editor para form_schema e table_schema
  - Validação em tempo real

**JSON Editor Component:**

```bash
npm install react-ace ace-builds
```

```typescript
import AceEditor from 'react-ace';
import 'ace-builds/src-noconflict/mode-json';
import 'ace-builds/src-noconflict/theme-monokai';

<AceEditor
  mode="json"
  theme="monokai"
  value={JSON.stringify(formSchema, null, 2)}
  onChange={handleSchemaChange}
  name="schema-editor"
  editorProps={{ $blockScrolling: true }}
  setOptions={{
    useWorker: true,
    showLineNumbers: true,
    tabSize: 2,
  }}
  style={{ width: '100%', height: '400px' }}
/>
```

**Validação:**
```typescript
async function validateAndSave(values: any) {
  try {
    // 1. Validar schema com backend
    await monitoringTypeAPI.validateSchema(values);

    // 2. Salvar
    await monitoringTypeAPI.createType(category, values);

    message.success('Tipo criado com sucesso!');
    reload();
  } catch (error) {
    Modal.error({
      title: 'Erro de Validação',
      content: <pre>{error.message}</pre>,
    });
  }
}
```

---

#### 5.3 - Import/Export Configs (Dia 4)

**Funcionalidade:** Backup e restore de todas as configurações

**Backend:**

- [ ] `backend/api/admin_config.py`
  ```python
  @router.get("/admin/export-config")
  async def export_all_configs():
      """Exporta TODAS as configs do Consul KV"""
      all_configs = {}

      # Export monitoring types
      types_keys = await consul.kv_get_keys("skills/cm/monitoring-types/")
      all_configs['monitoring_types'] = {}
      for key in types_keys:
          data = await consul.kv_get(key)
          all_configs['monitoring_types'][key] = json.loads(data)

      # Export field schemas
      fields = await consul.kv_get("skills/cm/field-schemas/metadata-fields.json")
      all_configs['field_schemas'] = json.loads(fields)

      # Export UI configs
      ui_config = await consul.kv_get("skills/cm/ui-configs/page-layouts.json")
      all_configs['ui_configs'] = json.loads(ui_config)

      return {
          "export_date": datetime.now().isoformat(),
          "version": "1.0",
          "configs": all_configs
      }

  @router.post("/admin/import-config")
  async def import_configs(config: dict):
      """Importa configs (restore de backup)"""
      # Validar estrutura
      if 'configs' not in config:
          raise HTTPException(400, "Invalid config structure")

      # Restaurar monitoring types
      for key, value in config['configs']['monitoring_types'].items():
          await consul.kv_put(key, json.dumps(value))

      # Restaurar outros configs
      # ...

      return {"success": True, "message": "Configs imported successfully"}
  ```

**Frontend:**

- [ ] Botão "Export" na página admin
  ```typescript
  async function handleExport() {
    const response = await axios.get('/api/v1/admin/export-config');
    const blob = new Blob([JSON.stringify(response.data, null, 2)], {
      type: 'application/json',
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `consul-manager-config-${Date.now()}.json`;
    a.click();
  }
  ```

- [ ] Botão "Import" com upload
  ```typescript
  <Upload
    accept=".json"
    beforeUpload={(file) => {
      const reader = new FileReader();
      reader.onload = async (e) => {
        const config = JSON.parse(e.target.result as string);
        await axios.post('/api/v1/admin/import-config', config);
        message.success('Configs importadas com sucesso!');
        reload();
      };
      reader.readAsText(file);
      return false; // Prevent auto upload
    }}
  >
    <Button icon={<UploadOutlined />}>Import Config</Button>
  </Upload>
  ```

---

**✅ FASE 5 CONCLUÍDA - Checkpoint:**
- [ ] Admin UI para gestão de tipos funcionando
- [ ] Criar, editar, deletar tipos via UI
- [ ] Import/Export de configs implementado
- [ ] Validação de schemas funcionando

---

## 🧹 **FASE 6: REFINAMENTO (2-3 dias)**

### Objetivo
Finalizar migração, testes, documentação e deprecação de código legado.

### Checklist Detalhado

#### 6.1 - Migração de Dados Legados (Dia 1)

**Script de migração:**

- [ ] `backend/scripts/migrate_to_config_driven.py`
  ```python
  """
  Migra dados existentes para novo sistema configuration-driven
  """

  async def migrate_existing_data():
      # 1. Criar schemas JSON iniciais no Consul KV
      await create_initial_schemas()

      # 2. Migrar metadata fields (se necessário)
      await migrate_metadata_fields()

      # 3. Verificar integridade
      await verify_migration()

      print("✅ Migração concluída com sucesso!")
  ```

**Executar:**
```bash
cd backend
python scripts/migrate_to_config_driven.py
```

---

#### 6.2 - Testes End-to-End (Dia 2)

**Cenários de teste:**

- [ ] **Test 1:** Criar novo tipo via Admin UI
  1. Acessar `/admin/monitoring-types`
  2. Criar novo tipo "HTTP 3xx"
  3. Verificar que aparece no menu automaticamente
  4. Acessar página e verificar funcionamento

- [ ] **Test 2:** Editar schema existente
  1. Editar form_schema de "ICMP"
  2. Adicionar novo campo "ttl"
  3. Verificar que campo aparece no form de cadastro

- [ ] **Test 3:** Desabilitar tipo
  1. Marcar tipo "SSH Banner" como `enabled: false`
  2. Verificar que desaparece do menu

- [ ] **Test 4:** Export/Import config
  1. Exportar todas configs
  2. Deletar um tipo
  3. Importar backup
  4. Verificar que tipo voltou

- [ ] **Test 5:** Cadastrar serviço via nova página
  1. Acessar `/network-probes`
  2. Clicar "Adicionar"
  3. Preencher form dinamicamente gerado
  4. Verificar que serviço foi criado no Consul

---

#### 6.3 - Documentação (Dia 3)

**Atualizar documentos:**

- [ ] `CLAUDE.md`
  - Adicionar seção sobre sistema configuration-driven
  - Documentar estrutura do Consul KV
  - Explicar como adicionar novos tipos

- [ ] `README.md`
  - Atualizar screenshots
  - Adicionar guia rápido: "Como adicionar um novo tipo de monitoramento"

- [ ] Criar `docs/ADDING_NEW_MONITORING_TYPE.md`
  ```markdown
  # Como Adicionar um Novo Tipo de Monitoramento

  ## Via Admin UI (Recomendado)

  1. Acesse `/admin/monitoring-types`
  2. Selecione a categoria desejada
  3. Clique em "Adicionar Novo Tipo"
  4. Preencha os campos:
     - **ID**: Identificador único (ex: `http_3xx`)
     - **Nome**: Nome de exibição (ex: `HTTP 3xx`)
     - **Exporter Type**: `blackbox`
     - **Module Name**: `http_3xx`
  5. Configure o form_schema:
     ```json
     {
       "fields": [
         {"name": "target", "label": "URL", "type": "text", "required": true}
       ]
     }
     ```
  6. Salve e teste!

  ## Via API (Avançado)

  ```bash
  curl -X POST http://localhost:5000/api/v1/monitoring-types \
    -H "Content-Type: application/json" \
    -d @new-type.json
  ```

  ## Via Consul KV (Direto)

  Edite o arquivo JSON diretamente no Consul KV:
  ```
  skills/cm/monitoring-types/web-probes.json
  ```

  Adicione novo objeto ao array `types`.
  ```

---

#### 6.4 - Deprecar Código Legado (Dia 3)

**Páginas a deprecar:**

- [ ] `frontend/src/pages/Services.tsx` → Renomear para `ServicesLegacy.tsx`
- [ ] `frontend/src/pages/BlackboxTargets.tsx` → Renomear para `BlackboxTargetsLegacy.tsx`
- [ ] `frontend/src/pages/Exporters.tsx` → Renomear para `ExportersLegacy.tsx`

**Adicionar banners de deprecação:**
```typescript
<Alert
  type="warning"
  banner
  message="⚠️ Esta página está obsoleta e será removida em breve."
  description={
    <span>
      Use as novas páginas organizadas por tipo:{' '}
      <a href="/network-probes">Network Probes</a>,{' '}
      <a href="/system-exporters">System Exporters</a>, etc.
    </span>
  }
  closable
  style={{ marginBottom: 16 }}
/>
```

**Marcar para remoção futura:**
```typescript
// @deprecated Use /network-probes instead
// TODO: Remove after 2025-12-01
export default function ServicesLegacy() {
  // ...
}
```

---

**✅ FASE 6 CONCLUÍDA - Checkpoint:**
- [ ] Dados migrados para novo sistema
- [ ] Testes E2E passando
- [ ] Documentação atualizada
- [ ] Código legado deprecado

---

## ✅ **CRITÉRIOS DE SUCESSO FINAL**

### Funcionais

- [ ] **Admin pode cadastrar novo tipo via UI sem tocar em código**
- [ ] **Todas as 5 páginas principais renderizando dinamicamente**
- [ ] **Filtros e buscas funcionando corretamente**
- [ ] **Forms de cadastro gerados dinamicamente dos schemas**
- [ ] **Export/Import de configs funcionando**

### Técnicos

- [ ] **Zero hardcoding de tipos (tudo vem do Consul KV)**
- [ ] **TypeScript sem erros de tipo**
- [ ] **Testes unitários > 80% coverage**
- [ ] **Build do frontend sem warnings**
- [ ] **Documentação completa e atualizada**

### UX

- [ ] **Navegação intuitiva entre páginas**
- [ ] **Performance: Tabelas carregam < 2s**
- [ ] **Responsivo (funciona em tablet)**
- [ ] **Feedback claro de ações (success/error messages)**

---

## 🚨 **ROLLBACK PLAN**

### Se algo der errado:

**Passo 1:** Manter páginas legadas funcionando durante toda a migração

**Passo 2:** Feature flag no backend
```python
# .env
ENABLE_CONFIG_DRIVEN_UI=false

# Código
if os.getenv("ENABLE_CONFIG_DRIVEN_UI") == "true":
    # Usar novo sistema
else:
    # Usar sistema legado
```

**Passo 3:** Backup do Consul KV antes de qualquer mudança
```bash
# Backup
consul kv export skills/cm/ > backup-$(date +%Y%m%d).json

# Restore
consul kv import @backup-20251031.json
```

**Passo 4:** Git branches separados por fase
```
main (produção)
└─ feat/config-driven-phase1
   └─ feat/config-driven-phase2
      └─ feat/config-driven-phase3
         └─ ...
```

Merge apenas quando fase estiver 100% validada.

---

## 📊 **MÉTRICAS DE ACOMPANHAMENTO**

### Rastrear durante implementação:

| Métrica | Meta | Como Medir |
|---------|------|------------|
| **Linhas de código por página** | < 50 linhas | `wc -l pages/*.tsx` |
| **Tempo de carregamento** | < 2s | Chrome DevTools Network tab |
| **Erros TypeScript** | 0 | `npx tsc --noEmit` |
| **Coverage de testes** | > 80% | `npm test -- --coverage` |
| **Tamanho do bundle** | < 500KB | `npm run build` + análise |
| **Tempo para adicionar novo tipo** | < 5 min | Cronometrar via Admin UI |

---

## 🎓 **LIÇÕES APRENDIDAS**

### Durante implementação, documentar:

- [ ] **Decisões de arquitetura** e por quê
- [ ] **Problemas encontrados** e soluções
- [ ] **Performance bottlenecks** e otimizações
- [ ] **UX feedback** do usuário final

Criar `docs/LESSONS_LEARNED.md` ao final.

---

## 📞 **PONTOS DE DECISÃO**

### Quando buscar aprovação antes de prosseguir:

1. **Antes de FASE 3:** Validar que componente base funciona perfeitamente
2. **Antes de FASE 5:** Confirmar se Admin UI terá autenticação/permissões
3. **Antes de FASE 6:** Decidir data de remoção do código legado

---

## 🎯 **PRÓXIMO PASSO IMEDIATO**

**Iniciar FASE 1.1** - Criar JSON schemas e salvá-los no Consul KV.

Quer que eu:
1. Crie os 4 JSONs iniciais (`network-probes.json`, `web-probes.json`, etc)?
2. Implemente o script Python para salvar no Consul KV?
3. Comece a criar o `MonitoringTypeManager`?

**Aguardando sua aprovação para começar! 🚀**

---

**Autor:** Claude Code (Anthropic)
**Revisão:** Adriano Fante
**Status:** 🔄 Aguardando Aprovação → Pronto para Iniciar
