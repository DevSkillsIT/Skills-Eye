# REFACTORING ARCHITECTURE - Sistema Modular e Customizável

**Data:** 2025-10-31
**Versão:** 1.0
**Objetivo:** Transformar o Consul Manager Web em um sistema **configuration-driven**, **multi-tenant ready** e **100% customizável**

---

## 🎯 **FILOSOFIA DO SISTEMA**

### Princípios Fundamentais

```
❌ HARDCODED → ✅ CONFIGURATION-DRIVEN
❌ MONOLÍTICO → ✅ PLUGIN-BASED
❌ SINGLE-TENANT → ✅ MULTI-TENANT READY
❌ RÍGIDO → ✅ GRANULARMENTE CUSTOMIZÁVEL
```

**"Se um dia surgir um novo tipo de monitoramento, deve ser possível cadastrá-lo via UI sem alterar código"**

---

## 🔓 **ZERO LOCK-IN: FIELD MAPPING & FLEXIBILIDADE TOTAL**

### ⚠️ **CRITICAL: Não assumir NADA sobre nomes**

```
❌ ERRADO: Hardcoded "node_exporter", "selfnode", "blackbox"
✅ CORRETO: Tudo configurável via JSON schemas
```

**Problema Real Encontrado:**
- Código assumia nomes fixos: `exporterType === "Node Exporter"`
- E se empresa usar `"node-exporter-custom"` ou `"selfnode"` ou `"custom-linux-metrics"`?
- Sistema ficaria **quebrado** → **INACEITÁVEL!**

### ✅ **Solução: Field Mapping Layer**

#### **1. Source of Truth: Prometheus Configs**

O sistema **JÁ TEM** mapeamento dos campos via `/api/v1/metadata-dynamic/fields`:
- Lê `prometheus.yml` → `relabel_configs`
- Extrai `target_label` → vira coluna da tabela
- **100% agnóstico** a nomes de exporters/módulos

#### **2. JSON Schema com Mapeamentos Flexíveis**

```json
{
  "id": "icmp",
  "display_name": "ICMP (Ping)",

  // ✅ FLEXÍVEL: Permite múltiplos nomes para o mesmo tipo
  "matchers": {
    "exporter_type_field": "exporter_type",  // Campo no Consul Meta
    "exporter_type_values": [
      "blackbox",
      "blackbox-exporter",
      "bb-exporter",
      "custom-blackbox"
    ],

    "module_field": "module",  // Campo no Consul Meta
    "module_values": [
      "icmp",
      "ping",
      "icmp_ipv4",
      "icmp_ipv6"
    ],

    // ✅ Permite filtrar por qualquer combinação
    "additional_filters": [
      { "field": "job", "values": ["blackbox"] },
      { "field": "probe", "values": ["icmp"] }
    ]
  },

  // ✅ Field Mapping: Renomear campos do Prometheus
  "field_mapping": {
    "instance": "target",           // Prometheus "instance" → UI "target"
    "__meta_consul_service": "service_name",
    "job": "job_name",
    // Suporta nested fields
    "Meta.custom_field": "display_field"
  }
}
```

#### **3. Backend: Query Builder Dinâmico**

```python
# backend/core/monitoring_type_manager.py

def build_filter_query(type_schema: dict) -> dict:
    """Constrói query de filtro baseado em matchers do schema"""

    matchers = type_schema.get('matchers', {})
    filters = []

    # Filtro por exporter_type (múltiplos valores aceitos)
    exporter_field = matchers.get('exporter_type_field', 'exporter_type')
    exporter_values = matchers.get('exporter_type_values', [])
    if exporter_values:
        filters.append({
            'field': f'Meta.{exporter_field}',
            'operator': 'in',
            'values': exporter_values
        })

    # Filtro por module (múltiplos valores aceitos)
    module_field = matchers.get('module_field', 'module')
    module_values = matchers.get('module_values', [])
    if module_values:
        filters.append({
            'field': f'Meta.{module_field}',
            'operator': 'in',
            'values': module_values
        })

    # Filtros adicionais customizados
    for additional in matchers.get('additional_filters', []):
        filters.append(additional)

    return {
        'operator': 'and',
        'conditions': filters
    }
```

#### **4. Admin UI: Configurar Matchers**

```typescript
// Admin pode configurar múltiplos "apelidos" para o mesmo tipo
<ProFormList
  name={['matchers', 'exporter_type_values']}
  label="Valores de Exporter Type aceitos"
  tooltip="Liste todos os nomes possíveis. Ex: blackbox, bb-exporter, custom-blackbox"
>
  <ProFormText placeholder="blackbox" />
</ProFormList>

// Resultado no JSON:
{
  "matchers": {
    "exporter_type_values": [
      "blackbox",           // Nome oficial
      "blackbox-exporter",  // Variação 1
      "bb-exporter",        // Variação 2
      "skillsit-blackbox"   // Nome customizado da empresa
    ]
  }
}
```

#### **5. Exemplo Real: Múltiplos Nomes para Node Exporter**

```json
{
  "id": "node",
  "display_name": "Node Exporter (Linux)",
  "matchers": {
    "exporter_type_values": [
      "node",
      "node_exporter",
      "node-exporter",
      "selfnode",           // Nome usado no projeto atual!
      "linux-metrics",
      "server-metrics",
      "prometheus-node",
      "custom-node-exporter"
    ],
    "module_values": [
      "node",
      "node_exporter",
      null  // Permite ausência do campo module
    ]
  }
}
```

#### **6. Benefícios**

| Cenário | Solução Flexível |
|---------|------------------|
| **Empresa renomeia exporter** | Adicionar novo nome ao array `exporter_type_values` |
| **Migração de nome** | Manter ambos nomes no array durante transição |
| **Exporters customizados** | Cadastrar via Admin UI com matcher específico |
| **Múltiplos Prometheus** | Cada um pode usar nomenclatura diferente |
| **Vendor lock-in** | Zero! Sistema adapta a qualquer nome |

### 🎯 **Regra de Ouro**

```python
# ❌ NUNCA FAZER:
if service['Meta']['exporter_type'] == 'node_exporter':
    # ...

# ✅ SEMPRE FAZER:
if matches_type(service, type_schema['matchers']):
    # ...
```

**TODO código que verifica tipo DEVE usar matchers do schema JSON!**

---

## 📐 **ARQUITETURA EM CAMADAS**

```
┌─────────────────────────────────────────────────────────────────┐
│ LAYER 1: CONFIGURATION STORE (Consul KV)                       │
│ └─ JSON Schemas definem tipos, campos, layouts                 │
├─────────────────────────────────────────────────────────────────┤
│ LAYER 2: BACKEND API (Python/FastAPI)                          │
│ └─ CRUD de configs, validação, agregação                       │
├─────────────────────────────────────────────────────────────────┤
│ LAYER 3: METADATA LAYER (TypeScript Types)                     │
│ └─ Tipos gerados dinamicamente dos schemas                     │
├─────────────────────────────────────────────────────────────────┤
│ LAYER 4: RENDERING ENGINE (React Components)                   │
│ └─ Componentes genéricos renderizam baseado em metadata        │
├─────────────────────────────────────────────────────────────────┤
│ LAYER 5: ADMIN UI (Gestão de Configurações)                    │
│ └─ Interface para cadastrar novos tipos, campos, layouts       │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🗄️ **LAYER 1: CONFIGURATION STORE**

### Estrutura no Consul KV

```
skills/cm/
├── monitoring-types/              # Tipos de monitoramento configuráveis
│   ├── network-probes.json        # ICMP, TCP, DNS, SSH, etc
│   ├── web-probes.json            # HTTP 2xx, 4xx, 5xx, HTTPS, POST
│   ├── system-exporters.json      # Node, Windows, SNMP
│   ├── database-exporters.json    # MySQL, Postgres, Redis, Mongo
│   └── custom/                    # Tipos customizados por tenant
│       └── {tenant_id}/{type_id}.json
│
├── field-schemas/                 # Schemas de campos metadata
│   ├── metadata-fields.json       # 19 campos padrão
│   └── custom-fields.json         # Campos adicionais por tenant
│
├── ui-configs/                    # Configurações de UI
│   ├── page-layouts.json          # Layouts de páginas
│   ├── color-schemes.json         # Paletas de cores
│   └── menu-structure.json        # Estrutura de menu
│
├── validation-rules/              # Regras de validação
│   └── schemas/                   # JSON Schemas para validação
│
└── feature-flags/                 # Feature flags por tenant
    └── {tenant_id}/features.json
```

---

## 📋 **JSON SCHEMA - Tipo de Monitoramento**

### Exemplo: `network-probes.json`

```json
{
  "schema_version": "1.0",
  "category": "network-probes",
  "display_name": "Network Probes (Rede)",
  "display_name_singular": "Network Probe",
  "icon": "📡",
  "color": "blue",
  "description": "Testes de conectividade e protocolos de rede",
  "enabled": true,
  "order": 1,

  "types": [
    {
      "id": "icmp",
      "display_name": "ICMP (Ping)",
      "icon": "🏓",
      "description": "Testes de conectividade via ICMP ping",
      "exporter_type": "blackbox",
      "module_name": "icmp",
      "default_port": null,
      "enabled": true,
      "order": 1,

      "form_schema": {
        "fields": [
          {
            "name": "target",
            "label": "Alvo",
            "type": "text",
            "required": true,
            "placeholder": "192.168.1.1 ou hostname.com",
            "validation": {
              "pattern": "^[a-zA-Z0-9.-]+$",
              "message": "Digite um IP ou hostname válido"
            }
          },
          {
            "name": "interval",
            "label": "Intervalo",
            "type": "select",
            "required": true,
            "default": "30s",
            "options": ["15s", "30s", "60s", "5m"],
            "help": "Frequência de verificação"
          },
          {
            "name": "timeout",
            "label": "Timeout",
            "type": "select",
            "required": false,
            "default": "10s",
            "options": ["5s", "10s", "30s"],
            "help": "Tempo máximo de espera por resposta"
          }
        ],
        "required_metadata": ["company", "tipo_monitoramento", "grupo_monitoramento"],
        "optional_metadata": ["localizacao", "notas"]
      },

      "table_schema": {
        "default_visible_columns": [
          "target",
          "status",
          "latency_ms",
          "company",
          "tipo_monitoramento",
          "last_check"
        ],
        "default_sort": {
          "field": "target",
          "order": "asc"
        },
        "row_actions": ["edit", "delete", "view_history", "pause"],
        "bulk_actions": ["delete", "pause", "resume", "export"]
      },

      "filters": {
        "quick_filters": ["company", "tipo_monitoramento", "status"],
        "advanced_filters": ["latency", "uptime_percent", "region"]
      },

      "metrics": {
        "primary": "probe_success",
        "secondary": ["probe_duration_seconds", "probe_http_status_code"]
      }
    },

    {
      "id": "tcp",
      "display_name": "TCP Connect",
      "icon": "🔌",
      "description": "Testes de conectividade TCP em portas específicas",
      "exporter_type": "blackbox",
      "module_name": "tcp_connect",
      "default_port": null,
      "enabled": true,
      "order": 2,

      "form_schema": {
        "fields": [
          {
            "name": "target",
            "label": "Alvo",
            "type": "text",
            "required": true,
            "placeholder": "192.168.1.1:80"
          },
          {
            "name": "port",
            "label": "Porta",
            "type": "number",
            "required": true,
            "min": 1,
            "max": 65535,
            "placeholder": "80"
          }
        ],
        "required_metadata": ["company", "tipo_monitoramento"]
      },

      "table_schema": {
        "default_visible_columns": ["target", "port", "status", "company"]
      }
    },

    {
      "id": "dns",
      "display_name": "DNS Query",
      "icon": "🌐",
      "description": "Testes de resolução DNS",
      "exporter_type": "blackbox",
      "module_name": "dns",
      "default_port": 53,
      "enabled": true,
      "order": 3
      // ... schema similar
    },

    {
      "id": "ssh",
      "display_name": "SSH Banner",
      "icon": "🔐",
      "description": "Verificação de banner SSH (disponibilidade de serviço SSH)",
      "exporter_type": "blackbox",
      "module_name": "ssh_banner",
      "default_port": 22,
      "enabled": true,
      "order": 4
      // ... schema similar
    }
  ],

  "page_config": {
    "title": "Network Probes (Rede)",
    "subtitle": "Monitoramento de conectividade e protocolos de rede",
    "show_summary_cards": true,
    "summary_metrics": ["total", "active", "inactive", "critical"],
    "show_filters": true,
    "show_search": true,
    "show_advanced_search": true,
    "show_column_selector": true,
    "show_export": true,
    "allow_bulk_actions": true
  }
}
```

---

## 🔧 **LAYER 2: BACKEND API**

### Novos Endpoints

```python
# Gestão de Tipos de Monitoramento
GET    /api/v1/monitoring-types                    # Lista todas as categorias
GET    /api/v1/monitoring-types/{category}         # Lista tipos de uma categoria
GET    /api/v1/monitoring-types/{category}/{type}  # Detalhes de um tipo específico
POST   /api/v1/monitoring-types                    # Criar novo tipo (Admin)
PUT    /api/v1/monitoring-types/{category}/{type}  # Atualizar tipo (Admin)
DELETE /api/v1/monitoring-types/{category}/{type}  # Remover tipo (Admin)

# Validação de Schemas
POST   /api/v1/monitoring-types/validate           # Validar schema antes de salvar

# Gestão de Campos Metadata
GET    /api/v1/field-schemas                       # Lista schemas de campos
POST   /api/v1/field-schemas                       # Criar campo customizado (Admin)

# Tenant Configuration (Multi-tenancy future)
GET    /api/v1/tenant-config                       # Config do tenant atual
PUT    /api/v1/tenant-config                       # Atualizar config do tenant

# Admin - Import/Export configs
GET    /api/v1/admin/export-config                 # Exportar todas configs
POST   /api/v1/admin/import-config                 # Importar configs (backup/restore)
```

### Backend Service Layer

```python
# backend/core/monitoring_type_manager.py
class MonitoringTypeManager:
    """Gerencia tipos de monitoramento configuráveis"""

    def __init__(self, consul_client):
        self.consul = consul_client
        self.kv_prefix = "skills/cm/monitoring-types/"

    async def get_all_categories(self) -> List[MonitoringCategory]:
        """Retorna todas as categorias de monitoramento"""
        keys = await self.consul.kv_get_keys(self.kv_prefix)
        categories = []
        for key in keys:
            data = await self.consul.kv_get(key)
            schema = json.loads(data)
            categories.append(self._parse_category(schema))
        return sorted(categories, key=lambda x: x.order)

    async def get_types_by_category(self, category: str) -> List[MonitoringType]:
        """Retorna tipos de uma categoria específica"""
        data = await self.consul.kv_get(f"{self.kv_prefix}{category}.json")
        schema = json.loads(data)
        return [self._parse_type(t) for t in schema['types'] if t['enabled']]

    async def create_type(self, category: str, type_schema: dict) -> MonitoringType:
        """Cria novo tipo de monitoramento (validação + persistência)"""
        # 1. Validar schema com JSON Schema
        self._validate_schema(type_schema)

        # 2. Verificar conflitos (id duplicado)
        existing = await self.get_types_by_category(category)
        if any(t.id == type_schema['id'] for t in existing):
            raise ValueError(f"Tipo {type_schema['id']} já existe")

        # 3. Salvar no Consul KV
        category_data = await self.consul.kv_get(f"{self.kv_prefix}{category}.json")
        category_schema = json.loads(category_data)
        category_schema['types'].append(type_schema)

        await self.consul.kv_put(
            f"{self.kv_prefix}{category}.json",
            json.dumps(category_schema, indent=2)
        )

        # 4. Registrar auditoria
        await self._audit_log("CREATE_TYPE", category, type_schema['id'])

        return self._parse_type(type_schema)

    def _validate_schema(self, schema: dict):
        """Valida schema com JSON Schema padrão"""
        from jsonschema import validate, ValidationError

        # Schema de validação (meta-schema)
        with open('backend/schemas/monitoring-type-schema.json') as f:
            meta_schema = json.load(f)

        try:
            validate(instance=schema, schema=meta_schema)
        except ValidationError as e:
            raise ValueError(f"Schema inválido: {e.message}")
```

---

## ⚛️ **LAYER 3 & 4: FRONTEND - RENDERING ENGINE**

### Componente Genérico Base

```typescript
// frontend/src/components/base/BaseMonitoringPage.tsx

import React, { useMemo } from 'react';
import { ProTable } from '@ant-design/pro-components';
import { useMonitoringType } from '@/hooks/useMonitoringType';
import { useTableFields } from '@/hooks/useMetadataFields';
import { MonitoringTypeSchema, MonitoringData } from '@/types/monitoring';

interface BaseMonitoringPageProps<T extends MonitoringData> {
  /** Categoria do tipo de monitoramento (ex: 'network-probes') */
  category: string;

  /** ID do tipo específico (ex: 'icmp', 'tcp'). Se não fornecido, mostra todos da categoria */
  typeId?: string;

  /** API endpoint para buscar dados */
  apiEndpoint: string;

  /** Callbacks customizados */
  onRowClick?: (record: T) => void;
  onBulkAction?: (action: string, selectedRows: T[]) => Promise<void>;
}

export function BaseMonitoringPage<T extends MonitoringData>({
  category,
  typeId,
  apiEndpoint,
  onRowClick,
  onBulkAction,
}: BaseMonitoringPageProps<T>) {

  // LAYER 1: Carregar schema do tipo de monitoramento
  const { schema, loading: schemaLoading } = useMonitoringType(category, typeId);

  // LAYER 2: Carregar campos metadata dinâmicos
  const { tableFields } = useTableFields(category);

  // LAYER 3: Gerar colunas dinamicamente do schema
  const columns = useMemo(() => {
    if (!schema) return [];

    return generateColumnsFromSchema(
      schema.table_schema,
      tableFields,
      schema.types.find(t => t.id === typeId)
    );
  }, [schema, tableFields, typeId]);

  // LAYER 4: Configurar filtros dinâmicos
  const filters = useMemo(() => {
    if (!schema) return [];
    return generateFiltersFromSchema(schema.filters, tableFields);
  }, [schema, tableFields]);

  // LAYER 5: Renderizar tabela
  return (
    <PageContainer
      title={schema?.display_name}
      subTitle={schema?.description}
      extra={[
        <Button key="add" type="primary" icon={<PlusOutlined />}>
          Adicionar {schema?.display_name_singular}
        </Button>
      ]}
    >
      <ProTable<T>
        columns={columns}
        request={async (params) => {
          // Buscar dados do backend com filtros aplicados
          const response = await fetch(
            `${apiEndpoint}?${buildQueryString(params, typeId)}`
          );
          return response.json();
        }}
        rowKey="id"
        toolBarRender={() => [
          <MetadataFilterBar
            key="filters"
            fields={filters}
            onChange={handleFilterChange}
          />,
          <ColumnSelector
            key="columns"
            columns={columns}
            onChange={handleColumnChange}
          />
        ]}
        rowSelection={{
          onChange: (_, selectedRows) => setSelectedRows(selectedRows),
        }}
        tableAlertRender={({ selectedRowKeys }) => (
          <Space>
            <span>{selectedRowKeys.length} selecionados</span>
            {schema?.table_schema.bulk_actions?.map(action => (
              <Button
                key={action}
                onClick={() => onBulkAction?.(action, selectedRows)}
              >
                {action}
              </Button>
            ))}
          </Space>
        )}
      />
    </PageContainer>
  );
}

// Função auxiliar: gerar colunas do schema
function generateColumnsFromSchema(
  tableSchema: any,
  metadataFields: MetadataFieldDynamic[],
  type: any
): ProColumns<any>[] {
  const columns: ProColumns<any>[] = [];

  // Colunas fixas do tipo
  tableSchema.default_visible_columns.forEach((colKey: string) => {
    if (colKey in FIXED_COLUMN_GENERATORS) {
      columns.push(FIXED_COLUMN_GENERATORS[colKey](type));
    }
  });

  // Colunas metadata dinâmicas
  metadataFields.forEach(field => {
    if (tableSchema.default_visible_columns.includes(field.name)) {
      columns.push({
        title: field.display_name,
        dataIndex: ['meta', field.name],
        key: field.name,
        width: field.field_type === 'string' ? 200 : 140,
        ellipsis: true,
        tooltip: field.description,
      });
    }
  });

  // Coluna de ações
  columns.push({
    title: 'Ações',
    key: 'actions',
    fixed: 'right',
    render: (_, record) => (
      <ActionMenu
        actions={tableSchema.row_actions}
        record={record}
        onAction={handleAction}
      />
    ),
  });

  return columns;
}
```

### Hook para Carregar Tipo de Monitoramento

```typescript
// frontend/src/hooks/useMonitoringType.ts

import { useQuery } from '@tanstack/react-query';
import { monitoringTypeAPI } from '@/services/api';
import { MonitoringTypeSchema } from '@/types/monitoring';

export function useMonitoringType(category: string, typeId?: string) {
  const { data, isLoading, error } = useQuery({
    queryKey: ['monitoring-type', category, typeId],
    queryFn: async () => {
      if (typeId) {
        return monitoringTypeAPI.getType(category, typeId);
      }
      return monitoringTypeAPI.getCategory(category);
    },
    staleTime: 5 * 60 * 1000, // Cache 5 min (configs mudam pouco)
  });

  return {
    schema: data as MonitoringTypeSchema,
    loading: isLoading,
    error,
  };
}
```

---

## 📱 **PÁGINAS ESPECÍFICAS - Implementação Simplificada**

### Exemplo: Network Probes

```typescript
// frontend/src/pages/NetworkProbes.tsx

import React from 'react';
import { BaseMonitoringPage } from '@/components/base/BaseMonitoringPage';
import { NetworkProbeData } from '@/types/monitoring';

export default function NetworkProbes() {
  return (
    <BaseMonitoringPage<NetworkProbeData>
      category="network-probes"
      // typeId não fornecido = mostra todos (ICMP, TCP, DNS, SSH)
      apiEndpoint="/api/v1/services"
      onRowClick={(record) => {
        // Abrir drawer de detalhes
        console.log('Ver detalhes:', record);
      }}
      onBulkAction={async (action, rows) => {
        if (action === 'delete') {
          // Confirmar e deletar
        }
      }}
    />
  );
}
```

### Exemplo: ICMP Only (Sub-página)

```typescript
// frontend/src/pages/NetworkProbes/IcmpProbes.tsx

export default function IcmpProbes() {
  return (
    <BaseMonitoringPage<IcmpProbeData>
      category="network-probes"
      typeId="icmp"  // Filtra apenas ICMP
      apiEndpoint="/api/v1/services"
    />
  );
}
```

**Resultado:**
- ✅ Apenas 10-15 linhas de código por página
- ✅ Todo comportamento vem do schema JSON
- ✅ Novos tipos = adicionar no Consul KV, zero código

---

## 🛠️ **LAYER 5: ADMIN UI - Gestão de Tipos**

### Tela de Administração

```typescript
// frontend/src/pages/Admin/MonitoringTypes.tsx

export default function MonitoringTypesAdmin() {
  const [categories, setCategories] = useState<MonitoringCategory[]>([]);
  const [editingType, setEditingType] = useState<MonitoringType | null>(null);

  return (
    <PageContainer title="Gestão de Tipos de Monitoramento">
      <Card>
        <Tabs>
          <TabPane tab="Network Probes" key="network">
            <TypesTable
              category="network-probes"
              onEdit={setEditingType}
              onCreate={() => setEditingType({ category: 'network-probes' })}
            />
          </TabPane>

          <TabPane tab="Web Probes" key="web">
            <TypesTable category="web-probes" />
          </TabPane>

          {/* ... outras categorias */}
        </Tabs>
      </Card>

      {/* Modal de Edição - Form gerado do schema */}
      <MonitoringTypeFormModal
        visible={!!editingType}
        type={editingType}
        onSave={handleSave}
        onCancel={() => setEditingType(null)}
      />
    </PageContainer>
  );
}
```

### Form Builder Dinâmico

```typescript
// frontend/src/components/admin/MonitoringTypeFormModal.tsx

export function MonitoringTypeFormModal({ type, onSave }: Props) {
  return (
    <ModalForm
      title={type.id ? 'Editar Tipo' : 'Novo Tipo'}
      onFinish={onSave}
    >
      <ProFormText
        name="id"
        label="ID"
        rules={[{ required: true, pattern: /^[a-z_]+$/ }]}
        disabled={!!type.id}
      />

      <ProFormText name="display_name" label="Nome de Exibição" required />

      <ProFormSelect
        name="exporter_type"
        label="Tipo de Exporter"
        options={[
          { label: 'Blackbox', value: 'blackbox' },
          { label: 'Node Exporter', value: 'node' },
          { label: 'SNMP Exporter', value: 'snmp' },
          { label: 'Custom', value: 'custom' },
        ]}
        required
      />

      <ProFormTextArea
        name="description"
        label="Descrição"
        placeholder="Descreva o propósito deste tipo de monitoramento"
      />

      {/* Editor JSON para form_schema */}
      <ProFormField
        name="form_schema"
        label="Schema do Formulário"
      >
        <JSONEditor
          value={type.form_schema}
          onChange={handleSchemaChange}
          schema={FORM_SCHEMA_META_SCHEMA}
        />
      </ProFormField>

      {/* Validação em tempo real */}
      <Alert
        message="Schema válido"
        type="success"
        showIcon
        style={{ marginTop: 16 }}
      />
    </ModalForm>
  );
}
```

---

## 🔐 **MULTI-TENANCY (Futuro)**

### Isolamento por Tenant

```python
# backend/core/tenant_manager.py

class TenantContext:
    """Context manager para operações tenant-específicas"""

    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id

    def get_kv_prefix(self, base_path: str) -> str:
        """Retorna path do KV com tenant_id"""
        return f"skills/cm/tenants/{self.tenant_id}/{base_path}"

    async def get_monitoring_types(self) -> List[MonitoringType]:
        """Busca tipos do tenant + tipos globais"""
        global_types = await self._get_global_types()
        custom_types = await self._get_tenant_types()

        # Merge com prioridade para custom
        return self._merge_types(global_types, custom_types)
```

### Feature Flags por Tenant

```json
// skills/cm/tenants/{tenant_id}/features.json
{
  "features": {
    "custom_monitoring_types": true,
    "advanced_search": true,
    "bulk_actions": true,
    "export_to_csv": true,
    "api_access": false,
    "multi_user": false
  },
  "limits": {
    "max_services": 1000,
    "max_custom_types": 5,
    "max_users": 10
  }
}
```

---

## 📊 **BENEFÍCIOS DA ARQUITETURA**

### ✅ Para Desenvolvedores

- **DRY Principle**: Componente base reutilizado em todas as páginas
- **Type Safety**: TypeScript types gerados dos schemas JSON
- **Easy Testing**: Mocks baseados em schemas, não em implementações
- **Low Maintenance**: Mudanças em configs, não em código

### ✅ Para Analistas/Usuários

- **Self-Service**: Cadastrar novos tipos sem depender de dev
- **Customização Total**: Cada empresa pode ter seus próprios tipos
- **Consistência**: UX uniforme em todas as telas
- **Escalabilidade**: Adicionar 100 tipos novos = 100 JSONs, zero código

### ✅ Para a Empresa

- **Multi-Tenant Ready**: Preparado para SaaS desde o início
- **Vendor Lock-in Free**: Configs em JSON standard, fácil migração
- **Audit Trail**: Toda mudança em config é versionada no Consul
- **Rollback Simples**: Consul KV tem versionamento built-in

---

## 🚀 **PRÓXIMOS PASSOS**

Ver **`REFACTORING_PLAN.md`** para plano de implementação detalhado.

---

## 📚 **REFERÊNCIAS**

- **Configuration-Driven UI**: [Metadata-Driven Architecture](https://medium.com/@kharshith53/designing-scalable-metadata-driven-uis-for-dynamic-data-systems-c0b3fb7271ce)
- **Plugin Architecture**: [Grafana Plugin System](https://grafana.com/developers/plugin-tools/)
- **Multi-Tenancy Patterns**: [AWS Multi-Tenant SaaS](https://aws.amazon.com/blogs/mt/using-aws-appconfig-to-manage-multi-tenant-saas-configurations/)
- **JSON Schema**: [JSON Schema Spec](https://json-schema.org/)
- **React Composition**: [React Design Patterns 2025](https://www.telerik.com/blogs/react-design-patterns-best-practices)

---

**Autor:** Claude Code (Anthropic)
**Revisão:** Adriano Fante
**Status:** 🔄 Em Revisão → Aguardando Aprovação
