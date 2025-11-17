# 🏗️ ANÁLISE ARQUITETURA CRUD DINÂMICO - Skills Eye

**Data:** 2025-11-17
**Autor:** Claude Code (Sonnet 4.5) - Análise Independente
**Versão:** 1.0 - Análise Profissional Completa

---

## 🎯 OBJETIVO DA ANÁLISE

Analisar profundamente a arquitetura do sistema Skills Eye para implementar **CRUD 100% dinâmico** nas páginas `monitoring/*`, entendendo:

1. ✅ Relação entre `monitoring-types`, `DynamicMonitoringPage` e `service-groups`
2. ✅ Diferença entre Consul (descoberta) e Prometheus (catálogo)
3. ✅ Sistema de categorização via `monitoring/rules`
4. ✅ Campos dinâmicos customizados por `exporter_type`
5. ✅ Backend CRUD existente (services.py) para reutilização
6. ✅ Componentes compartilhados para DRY (Don't Repeat Yourself)
7. ✅ Documentações oficiais (Consul, Prometheus, Blackbox, SNMP)

---

## 📋 SUMÁRIO EXECUTIVO

### ✅ DESCOBERTAS PRINCIPAIS

#### 1. **TRÊS PÁGINAS, TRÊS PROPÓSITOS DISTINTOS**

```
┌────────────────────────────────────────────────────────────────┐
│  MONITORING-TYPES: "O que PODE ser monitorado"                │
│  ✅ Fonte: prometheus.yml (todos os tipos configurados)       │
│  ✅ Propósito: CATÁLOGO de tipos disponíveis                  │
│  ❌ NÃO mostra instâncias                                     │
└────────────────────────────────────────────────────────────────┘
                              │
                              │ Referência (não integração)
                              ▼
┌────────────────────────────────────────────────────────────────┐
│  DYNAMIC-MONITORING-PAGE: "O que ESTÁ sendo monitorado"       │
│  ✅ Fonte: Consul (instâncias reais registradas)              │
│  ✅ Propósito: VISUALIZAÇÃO + CRUD de instâncias              │
│  ✅ Filtrado por categoria (network-probes, web-probes, etc)  │
└────────────────────────────────────────────────────────────────┘
                              │
                              │ Visão alternativa
                              ▼
┌────────────────────────────────────────────────────────────────┐
│  SERVICE-GROUPS: "Grupos de serviços rodando"                 │
│  ✅ Fonte: Consul Catalog (agregação de serviços)             │
│  ✅ Propósito: VISÃO AGREGADA com estatísticas                │
│  ❌ NÃO filtrado por categoria                                │
└────────────────────────────────────────────────────────────────┘
```

**CONCLUSÃO:** São **complementares**, não concorrentes. Cada uma tem seu propósito específico.

---

#### 2. **BACKEND CRUD JÁ EXISTE E ESTÁ FUNCIONAL** ✅

**Localização:** `backend/api/services.py`

**Endpoints Implementados:**
- ✅ `POST /api/v1/services` - Criar serviço (linha 344)
- ✅ `PUT /api/v1/services/{service_id}` - Editar serviço (linha 519)
- ✅ `DELETE /api/v1/services/{service_id}` - Deletar serviço (linha 681)
- ✅ `DELETE /api/v1/services/bulk/deregister` - Batch delete (linha 640)

**Funcionalidades Prontas:**
- ✅ Validação de duplicatas
- ✅ Sanitização de service IDs
- ✅ Suporte multi-site (tags, sufixos automáticos)
- ✅ Auto-cadastro de valores em `reference-values`
- ✅ Integração com `ConsulManager`

**⚠️ IMPORTANTE:** Código testado em `Services.tsx` (página legada que será desativada)

---

#### 3. **PROBLEMA CRÍTICO: CAMPOS CUSTOMIZADOS POR EXPORTER_TYPE** 🔴

**Situação Atual:**
- ✅ Metadata **genéricos** funcionam (company, site, env, etc)
- ❌ Campos **específicos do exporter** não são tratados

**Exemplos de Campos Necessários:**

| Exporter Type | Campos Específicos Necessários |
|---------------|-------------------------------|
| `blackbox` | `module` (icmp, http_2xx, tcp_connect)<br>`target` (URL ou IP a testar) |
| `snmp_exporter` | `snmp_community` (public, private)<br>`snmp_module` (if_mib, juniper, etc)<br>`snmp_version` (v2c, v3) |
| `windows_exporter` | `port` (9182)<br>`metrics_path` (/metrics) |
| `node_exporter` | `port` (9100)<br>`metrics_path` (/metrics) |
| `mysql_exporter` | `port` (9104)<br>`database_name`<br>`connection_string` |
| `postgres_exporter` | `port` (9187)<br>`database_name`<br>`connection_string` |

**Onde Estão Hoje:**
- ✅ `module` para blackbox → `Meta.module` (funcionando)
- ❌ Outros campos específicos → **NÃO implementados**

---

#### 4. **SISTEMA DE CATEGORIZAÇÃO JÁ IMPLEMENTADO** ✅

**Localização:** `skills/eye/monitoring-types/categorization/rules`

**Estrutura Atual:**
```json
{
  "version": "1.0.0",
  "rules": [
    {
      "id": "blackbox_icmp",
      "priority": 100,
      "category": "network-probes",
      "display_name": "ICMP (Ping)",
      "exporter_type": "blackbox",
      "conditions": {
        "job_name_pattern": "^(icmp|ping).*",
        "metrics_path": "/probe",
        "module_pattern": "^(icmp|ping)$"
      },
      "observations": "Detecção de probes ICMP via Blackbox"
    }
  ]
}
```

**Gestão:** Página `MonitoringRules.tsx` (CRUD completo)

**Oportunidade de Extensão:** ⚡ Adicionar `form_schema` nas regras!

---

## 🔍 ANÁLISE DETALHADA

### 1. INTEGRAÇÃO ENTRE PÁGINAS

#### 1.1. monitoring-types ↔ DynamicMonitoringPage

**NÃO HÁ INTEGRAÇÃO DIRETA**, mas há **relação conceitual**:

```typescript
// monitoring-types: Lista tipos DISPONÍVEIS
// Endpoint: GET /monitoring-types-dynamic/from-prometheus
{
  "categories": [
    {
      "category": "network-probes",
      "types": [
        { "id": "blackbox-icmp", "job_name": "blackbox-icmp", "exporter_type": "blackbox" }
      ]
    }
  ]
}

// DynamicMonitoringPage: Lista instâncias REAIS
// Endpoint: GET /monitoring/data?category=network-probes
{
  "category": "network-probes",
  "data": [
    {
      "ID": "icmp-palmas-01",
      "Service": "blackbox",
      "Address": "10.0.0.1",
      "Port": 9115,
      "Meta": { "module": "icmp", "company": "Ramada" }
    }
  ]
}
```

**POSSÍVEL INTEGRAÇÃO NO CRUD:**

Quando usuário clicar em "Criar novo serviço" em `DynamicMonitoringPage`:
1. ✅ Buscar tipos disponíveis de `/monitoring-types-dynamic/from-prometheus`
2. ✅ Filtrar tipos pela categoria atual (ex: `category=network-probes`)
3. ✅ Mostrar dropdown com tipos compatíveis
4. ✅ Ao selecionar tipo → Carregar `form_schema` do tipo (campos específicos)
5. ✅ Renderizar form dinâmico com validações

---

#### 1.2. service-groups ↔ DynamicMonitoringPage

**AMBAS LEEM DO CONSUL**, mas com visões diferentes:

```
CONSUL CATALOG (Fonte única)
        │
        ├─→ service-groups: Agrupa por nome de serviço
        │   Exemplo: "blackbox" (150 instâncias), "node-exporter" (200 instâncias)
        │   Mostra: estatísticas, health checks, nós
        │   NÃO mostra: categorias (network vs web vs system)
        │
        └─→ DynamicMonitoringPage: Filtra por categoria
            Exemplo: "network-probes" (100 instâncias de blackbox+ping)
            Mostra: colunas dinâmicas, filtros metadata, CRUD
            Usa: CategorizationRuleEngine para categorizar
```

**COMPLEMENTARES:**
- `service-groups`: Visão **operacional** (quantos serviços de cada tipo?)
- `DynamicMonitoringPage`: Visão **lógica** (quantos network probes? web probes?)

---

### 2. ARQUITETURA DE DADOS

#### 2.1. FLUXO DE DADOS COMPLETO

```
┌─────────────────────────────────────────────────────────────────┐
│  1. PROMETHEUS.YML (Fonte da Verdade - Tipos)                  │
│     scrape_configs:                                              │
│       - job_name: 'blackbox-icmp'                                │
│         consul_sd_configs: [...]                                 │
│         relabel_configs:                                         │
│           - source_labels: [__meta_consul_service_metadata_*]   │
│             target_label: company                                │
└──────────────────────┬──────────────────────────────────────────┘
                       │
                       │ Extração via SSH (YamlConfigService)
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│  2. BACKEND: MonitoringTypesDynamicAPI                          │
│     GET /monitoring-types-dynamic/from-prometheus               │
│                                                                  │
│     Extrai do prometheus.yml:                                   │
│     - job_name                                                   │
│     - exporter_type                                              │
│     - metrics_path                                               │
│     - relabel_configs → fields disponíveis                       │
└──────────────────────┬──────────────────────────────────────────┘
                       │
                       │ Armazena em
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│  3. CONSUL KV: skills/eye/monitoring-types/categorization/rules │
│     {                                                            │
│       "rules": [                                                 │
│         {                                                        │
│           "id": "blackbox_icmp",                                 │
│           "category": "network-probes",                          │
│           "exporter_type": "blackbox",                           │
│           "form_schema": { ... }  ← ⚡ ADICIONAR AQUI           │
│         }                                                        │
│       ]                                                          │
│     }                                                            │
└──────────────────────┬──────────────────────────────────────────┘
                       │
                       │ Usa para categorizar
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│  4. CONSUL SERVICE REGISTRY (Instâncias Reais)                  │
│     Services:                                                    │
│       - ID: "icmp-palmas-01"                                     │
│         Service: "blackbox"                                      │
│         Port: 9115                                               │
│         Meta:                                                    │
│           module: "icmp"                                         │
│           company: "Ramada"                                      │
│           site: "palmas"                                         │
└──────────────────────┬──────────────────────────────────────────┘
                       │
                       │ Busca + Categoriza
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│  5. BACKEND: MonitoringUnifiedAPI                               │
│     GET /monitoring/data?category=network-probes                │
│                                                                  │
│     Fluxo:                                                       │
│     1. Buscar TODOS os serviços do Consul                        │
│     2. Aplicar CategorizationRuleEngine                          │
│     3. Filtrar por categoria solicitada                          │
│     4. Enriquecer com dados de site (KV metadata/sites)          │
│     5. Aplicar filtros adicionais (company, env, etc)            │
│     6. Retornar dados formatados                                 │
└──────────────────────┬──────────────────────────────────────────┘
                       │
                       │ Renderiza
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│  6. FRONTEND: DynamicMonitoringPage.tsx                         │
│     - Colunas dinâmicas (useTableFields)                         │
│     - Filtros dinâmicos (useFilterFields)                        │
│     - ⚡ CRUD (a implementar)                                    │
└─────────────────────────────────────────────────────────────────┘
```

---

### 3. SOLUÇÃO PARA CAMPOS DINÂMICOS POR EXPORTER

#### 3.1. PROPOSTA: Estender `categorization/rules` com `form_schema`

**Estrutura Proposta:**

```json
{
  "version": "2.0.0",
  "rules": [
    {
      "id": "blackbox_icmp",
      "priority": 100,
      "category": "network-probes",
      "display_name": "ICMP (Ping)",
      "exporter_type": "blackbox",
      "conditions": {
        "job_name_pattern": "^(icmp|ping).*",
        "metrics_path": "/probe",
        "module_pattern": "^(icmp|ping)$"
      },
      "form_schema": {
        "required_fields": ["target", "module"],
        "fields": [
          {
            "name": "target",
            "label": "Alvo (IP ou Hostname)",
            "type": "text",
            "required": true,
            "validation": "ip_or_hostname",
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
              { "value": "icmp", "label": "ICMP (Ping)" },
              { "value": "tcp_connect", "label": "TCP Connect" }
            ],
            "help": "Módulo definido no blackbox.yml"
          }
        ]
      }
    },
    {
      "id": "snmp_switch",
      "priority": 80,
      "category": "network-devices",
      "display_name": "SNMP Switch",
      "exporter_type": "snmp_exporter",
      "conditions": {
        "job_name_pattern": "^snmp.*",
        "metrics_path": "/snmp"
      },
      "form_schema": {
        "required_fields": ["target", "snmp_community", "snmp_module"],
        "fields": [
          {
            "name": "target",
            "label": "IP do Dispositivo",
            "type": "text",
            "required": true,
            "validation": "ipv4",
            "placeholder": "192.168.1.10"
          },
          {
            "name": "snmp_community",
            "label": "Community String",
            "type": "password",
            "required": true,
            "default": "public",
            "help": "Community SNMP (ex: public, private)"
          },
          {
            "name": "snmp_module",
            "label": "Módulo SNMP",
            "type": "select",
            "required": true,
            "options": [
              { "value": "if_mib", "label": "IF-MIB (Interfaces)" },
              { "value": "cisco_ios", "label": "Cisco IOS" },
              { "value": "juniper", "label": "Juniper" },
              { "value": "hp_procurve", "label": "HP Procurve" }
            ],
            "help": "Módulo definido no snmp.yml"
          },
          {
            "name": "snmp_version",
            "label": "Versão SNMP",
            "type": "select",
            "required": false,
            "default": "v2c",
            "options": [
              { "value": "v1", "label": "v1" },
              { "value": "v2c", "label": "v2c (recomendado)" },
              { "value": "v3", "label": "v3 (mais seguro)" }
            ]
          }
        ]
      }
    },
    {
      "id": "windows_exporter",
      "priority": 80,
      "category": "system-exporters",
      "display_name": "Windows Exporter",
      "exporter_type": "windows_exporter",
      "conditions": {
        "job_name_pattern": "^(windows|wmi).*",
        "metrics_path": "/metrics"
      },
      "form_schema": {
        "required_fields": ["target"],
        "fields": [
          {
            "name": "target",
            "label": "IP do Servidor Windows",
            "type": "text",
            "required": true,
            "validation": "ipv4"
          },
          {
            "name": "port",
            "label": "Porta",
            "type": "number",
            "required": false,
            "default": 9182,
            "help": "Porta do windows_exporter (padrão: 9182)"
          }
        ]
      }
    }
  ]
}
```

---

#### 3.2. COMPONENTE FRONTEND: FormFieldRenderer Dinâmico

**Já existe:** `frontend/src/components/FormFieldRenderer.tsx`

**Uso Atual:** Renderiza campos de `metadata-fields`

**Extensão Necessária:**

```typescript
// frontend/src/components/FormFieldRenderer.tsx
// ADICIONAR suporte a form_schema

interface FormFieldSchema {
  name: string;
  label: string;
  type: 'text' | 'number' | 'select' | 'password' | 'textarea';
  required: boolean;
  default?: any;
  options?: Array<{ value: string; label: string }>;
  validation?: 'ip' | 'ipv4' | 'hostname' | 'ip_or_hostname' | 'url';
  placeholder?: string;
  help?: string;
}

const FormFieldRenderer: React.FC<{
  field: FormFieldSchema;
  value: any;
  onChange: (value: any) => void;
  errors?: string[];
}> = ({ field, value, onChange, errors }) => {
  switch (field.type) {
    case 'select':
      return (
        <Form.Item
          label={field.label}
          required={field.required}
          help={field.help}
          validateStatus={errors ? 'error' : ''}
        >
          <Select
            value={value || field.default}
            onChange={onChange}
            placeholder={field.placeholder}
          >
            {field.options?.map((opt) => (
              <Select.Option key={opt.value} value={opt.value}>
                {opt.label}
              </Select.Option>
            ))}
          </Select>
        </Form.Item>
      );

    case 'password':
      return (
        <Form.Item
          label={field.label}
          required={field.required}
          help={field.help}
        >
          <Input.Password
            value={value || field.default}
            onChange={(e) => onChange(e.target.value)}
            placeholder={field.placeholder}
          />
        </Form.Item>
      );

    case 'number':
      return (
        <Form.Item label={field.label} required={field.required} help={field.help}>
          <InputNumber
            value={value || field.default}
            onChange={onChange}
            placeholder={field.placeholder}
            style={{ width: '100%' }}
          />
        </Form.Item>
      );

    case 'text':
    default:
      return (
        <Form.Item label={field.label} required={field.required} help={field.help}>
          <Input
            value={value || field.default}
            onChange={(e) => onChange(e.target.value)}
            placeholder={field.placeholder}
          />
        </Form.Item>
      );
  }
};
```

---

### 4. COMPONENTES COMPARTILHADOS (DRY)

#### 4.1. Componentes Já Existentes para Reutilizar

| Componente | Localização | Uso |
|------------|-------------|-----|
| `useConsulDelete` | `hooks/useConsulDelete.ts` | ✅ Delete com confirmação |
| `NodeSelector` | `components/NodeSelector.tsx` | ✅ Filtro por nó Consul |
| `ServerSelector` | `components/ServerSelector.tsx` | ✅ Seleção multi-servidor |
| `ColumnSelector` | `components/ColumnSelector.tsx` | ✅ Drag-drop de colunas |
| `MetadataFilterBar` | `components/MetadataFilterBar.tsx` | ✅ Filtros rápidos |
| `AdvancedSearchPanel` | `components/AdvancedSearchPanel.tsx` | ✅ Query builder |
| `FormFieldRenderer` | `components/FormFieldRenderer.tsx` | ⚡ Estender para form_schema |
| `ResizableTitle` | `components/ResizableTitle.tsx` | ✅ Colunas redimensionáveis |
| `BadgeStatus` | `components/BadgeStatus.tsx` | ✅ Indicadores performance |

---

#### 4.2. NOVO Componente: DynamicCRUDModal

**Responsabilidade:** Modal de criação/edição 100% dinâmico

**Localização Sugerida:** `frontend/src/components/DynamicCRUDModal.tsx`

**Props:**
```typescript
interface DynamicCRUDModalProps {
  visible: boolean;
  mode: 'create' | 'edit';
  category: string; // network-probes, web-probes, etc
  initialValues?: Record<string, any>;
  onSubmit: (values: Record<string, any>) => Promise<void>;
  onCancel: () => void;
}
```

**Fluxo:**
1. ✅ Buscar tipos disponíveis para a categoria
2. ✅ Usuário seleciona tipo → Carregar `form_schema` da regra
3. ✅ Renderizar campos metadata genéricos (via `useMetadataFields`)
4. ✅ Renderizar campos específicos do exporter (via `form_schema`)
5. ✅ Validar campos obrigatórios
6. ✅ Submeter para `POST /api/v1/services`

---

### 5. BACKEND: APIs Existentes para CRUD

#### 5.1. Endpoints Prontos

**services.py (FUNCIONAL - Testado em Services.tsx):**

```python
# CREATE
@router.post("/")
async def create_service(request: ServiceCreateRequest):
    """
    Cria novo serviço no Consul

    Body:
    {
      "name": "icmp-palmas-01",
      "service": "blackbox",
      "address": "10.0.0.1",
      "port": 9115,
      "meta": {
        "module": "icmp",
        "company": "Ramada",
        "site": "palmas"
      },
      "tags": ["network", "icmp"]
    }
    """
    # Validação, sanitização, registro no Consul
    # ✅ JÁ FUNCIONA

# UPDATE
@router.put("/{service_id}")
async def update_service(service_id: str, request: ServiceUpdateRequest):
    """
    Atualiza serviço existente

    - Re-registro automático (comportamento Consul)
    - Suporte multi-site
    """
    # ✅ JÁ FUNCIONA

# DELETE
@router.delete("/{service_id}")
async def delete_service(service_id: str):
    """
    Remove serviço do Consul
    """
    # ✅ JÁ FUNCIONA

# BATCH DELETE
@router.delete("/bulk/deregister")
async def bulk_deregister(service_ids: List[str]):
    """
    Remove múltiplos serviços
    """
    # ✅ JÁ FUNCIONA
```

**⚠️ ATENÇÃO:** Backend está PRONTO. Foco no frontend!

---

#### 5.2. Nova API Necessária: GET form_schema

**Endpoint:** `GET /api/v1/monitoring-types/form-schema`

**Propósito:** Retornar `form_schema` de um tipo específico

```python
# backend/api/monitoring_types_dynamic.py

@router.get("/form-schema")
async def get_form_schema(
    exporter_type: str = Query(..., description="Tipo do exporter"),
    category: Optional[str] = Query(None, description="Categoria (opcional)")
):
    """
    Retorna form_schema para um exporter_type específico

    Exemplo: GET /form-schema?exporter_type=blackbox&category=network-probes

    Returns:
    {
      "success": true,
      "exporter_type": "blackbox",
      "category": "network-probes",
      "form_schema": {
        "required_fields": ["target", "module"],
        "fields": [...]
      }
    }
    """
    # Buscar regras de categorização
    rules = await categorization_engine.get_rules()

    # Filtrar por exporter_type (e opcionalmente category)
    matching_rule = None
    for rule in rules:
        if rule.get("exporter_type") == exporter_type:
            if category and rule.get("category") != category:
                continue
            matching_rule = rule
            break

    if not matching_rule:
        raise HTTPException(404, f"Nenhuma regra encontrada para {exporter_type}")

    return {
        "success": True,
        "exporter_type": exporter_type,
        "category": matching_rule.get("category"),
        "display_name": matching_rule.get("display_name"),
        "form_schema": matching_rule.get("form_schema", {})
    }
```

---

### 6. DOCUMENTAÇÕES OFICIAIS - RESUMO TÉCNICO

#### 6.1. HashiCorp Consul - Service Discovery

**Fonte:** developer.hashicorp.com/consul/api-docs

**Conceitos-Chave:**

1. **Service Registry:**
   - Serviços registrados com `ID`, `Service`, `Address`, `Port`, `Meta`, `Tags`
   - `Meta`: Map<string, string> - Metadata arbitrário (KV)
   - `Tags`: Array<string> - Filtros para queries

2. **Catalog API:**
   - `/catalog/services` - Lista todos os serviços
   - `/catalog/service/{name}` - Instâncias de um serviço
   - `/catalog/nodes` - Lista todos os nós

3. **Agent API:**
   - `/agent/services` - Serviços do nó local
   - `/agent/service/register` - Registrar serviço
   - `/agent/service/deregister/{id}` - Remover serviço

4. **Health Checks:**
   - HTTP, TCP, TTL, Script
   - Status: `passing`, `warning`, `critical`

**USO NO SKILLS EYE:**
- ✅ `ConsulManager` usa Agent API para registro/remoção
- ✅ `monitoring_unified.py` usa Catalog API para listar serviços
- ✅ `Meta` armazena `company`, `site`, `env`, `module`, etc

---

#### 6.2. Prometheus - Service Discovery & Relabeling

**Fonte:** prometheus.io/docs/prometheus/latest/configuration

**Conceitos-Chave:**

1. **Service Discovery (SD):**
   - `consul_sd_configs`: Integração com Consul
   - Auto-descobre serviços registrados no Consul
   - Labels automáticos: `__meta_consul_service_*`, `__meta_consul_service_metadata_*`

2. **Relabeling:**
   - `relabel_configs`: Transformações de labels ANTES do scrape
   - `metric_relabel_configs`: Transformações de labels APÓS o scrape
   - Ações: `replace`, `keep`, `drop`, `hashmod`, `labelmap`

3. **Multi-Target Exporter Pattern:**
   - Usado por Blackbox, SNMP, etc
   - Target dinâmico via `__param_target`
   - Exporter único para múltiplos alvos

**Exemplo prometheus.yml:**
```yaml
scrape_configs:
  - job_name: 'blackbox-icmp'
    metrics_path: /probe
    params:
      module: [icmp]  # Módulo do blackbox.yml
    consul_sd_configs:
      - server: 'localhost:8500'
        services: ['blackbox']
        tags: ['icmp']
    relabel_configs:
      # Extrair metadata do Consul → Labels Prometheus
      - source_labels: [__meta_consul_service_metadata_company]
        target_label: company
      - source_labels: [__meta_consul_service_metadata_site]
        target_label: site
      - source_labels: [__meta_consul_service_metadata_module]
        target_label: module
      # Multi-target pattern
      - source_labels: [__meta_consul_service_metadata_target]
        target_label: __param_target
      - target_label: __address__
        replacement: localhost:9115  # Blackbox exporter address
```

**USO NO SKILLS EYE:**
- ✅ Extração de `relabel_configs` → `metadata-fields` (campos disponíveis)
- ✅ Detecção de `exporter_type` via `metrics_path` + `job_name`
- ✅ Multi-target pattern usado em Blackbox e SNMP

---

#### 6.3. Blackbox Exporter - Modules

**Fonte:** github.com/prometheus/blackbox_exporter

**Módulos Comuns:**

| Módulo | Prober | Descrição |
|--------|--------|-----------|
| `icmp` | ICMP | Ping |
| `tcp_connect` | TCP | Conectividade TCP |
| `http_2xx` | HTTP | HTTP GET (espera 2xx) |
| `http_post_2xx` | HTTP | HTTP POST |
| `dns` | DNS | Resolução DNS |
| `ssh_banner` | TCP | Banner SSH |

**Configuração blackbox.yml:**
```yaml
modules:
  icmp:
    prober: icmp
    timeout: 5s
  http_2xx:
    prober: http
    timeout: 5s
    http:
      valid_status_codes: []  # Defaults to 2xx
      method: GET
      preferred_ip_protocol: "ip4"
```

**Multi-Target Pattern:**
```
http://blackbox:9115/probe?target=192.168.1.1&module=icmp
```

**USO NO SKILLS EYE:**
- ✅ `module` armazenado em `Meta.module`
- ✅ `target` armazenado em `Meta.target`
- ⚡ `form_schema` deve ter dropdown de módulos disponíveis

---

#### 6.4. SNMP Exporter - Modules

**Fonte:** github.com/prometheus/snmp_exporter

**Módulos Comuns:**

| Módulo | Descrição | Uso |
|--------|-----------|-----|
| `if_mib` | IF-MIB | Interfaces de rede |
| `cisco_ios` | Cisco IOS | Switches Cisco |
| `juniper` | Juniper | Switches Juniper |
| `hp_procurve` | HP Procurve | Switches HP |
| `pdu` | PDU | Power Distribution Units |

**Parâmetros SNMP:**
- `community`: String de autenticação (v1/v2c)
- `version`: v1, v2c, v3
- `auth_protocol`: MD5, SHA (v3)
- `priv_protocol`: DES, AES (v3)

**Multi-Target Pattern:**
```
http://snmp-exporter:9116/snmp?target=192.168.1.1&module=if_mib&auth=public
```

**USO NO SKILLS EYE:**
- ⚡ ADICIONAR campos: `snmp_community`, `snmp_module`, `snmp_version`
- ⚡ Campos sensíveis (`community`) → Tipo `password` no form

---

### 7. ARQUITETURA PROPOSTA - CRUD COMPLETO

#### 7.1. FLUXO COMPLETO: Criar Novo Serviço

```
┌─────────────────────────────────────────────────────────────────┐
│  PASSO 1: Usuário clica "Criar Novo" em DynamicMonitoringPage  │
│  (Ex: category=network-probes)                                  │
└──────────────────────┬──────────────────────────────────────────┘
                       │
                       │ Abre modal
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│  PASSO 2: DynamicCRUDModal carrega tipos disponíveis            │
│  GET /monitoring-types-dynamic/from-prometheus?category=network │
│                                                                  │
│  Retorna:                                                        │
│  - blackbox-icmp (ICMP Ping)                                     │
│  - blackbox-tcp (TCP Connect)                                    │
│  - blackbox-http (HTTP)                                          │
└──────────────────────┬──────────────────────────────────────────┘
                       │
                       │ Usuário seleciona tipo
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│  PASSO 3: Buscar form_schema do tipo selecionado                │
│  GET /monitoring-types/form-schema?exporter_type=blackbox&...   │
│                                                                  │
│  Retorna:                                                        │
│  {                                                               │
│    "form_schema": {                                              │
│      "required_fields": ["target", "module"],                    │
│      "fields": [                                                 │
│        { "name": "target", "type": "text", ... },                │
│        { "name": "module", "type": "select", ... }               │
│      ]                                                           │
│    }                                                             │
│  }                                                               │
└──────────────────────┬──────────────────────────────────────────┘
                       │
                       │ Renderiza form
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│  PASSO 4: Form dinâmico renderizado                             │
│                                                                  │
│  SEÇÃO 1: Campos Específicos do Exporter (form_schema)          │
│    ┌──────────────────────────────────────────────────────┐     │
│    │ Alvo (IP ou Hostname): [192.168.1.1           ]     │     │
│    │ Módulo Blackbox:       [icmp ▼                ]     │     │
│    └──────────────────────────────────────────────────────┘     │
│                                                                  │
│  SEÇÃO 2: Metadata Genéricos (metadata-fields)                  │
│    ┌──────────────────────────────────────────────────────┐     │
│    │ Empresa:   [Ramada ▼           ]                     │     │
│    │ Site:      [palmas ▼           ]                     │     │
│    │ Ambiente:  [prod ▼             ]                     │     │
│    │ Nome:      [Gateway Principal  ]                     │     │
│    └──────────────────────────────────────────────────────┘     │
│                                                                  │
│  [Cancelar]  [Criar Serviço]                                    │
└──────────────────────┬──────────────────────────────────────────┘
                       │
                       │ Submit
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│  PASSO 5: Validação no Frontend                                 │
│  - target: IP ou hostname válido?                                │
│  - module: Selecionado?                                          │
│  - company, site, env: Obrigatórios?                             │
└──────────────────────┬──────────────────────────────────────────┘
                       │
                       │ POST para backend
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│  PASSO 6: Backend - POST /api/v1/services                       │
│  {                                                               │
│    "name": "icmp-ramada-palmas-gw",  // Auto-gerado ou manual   │
│    "service": "blackbox",            // Do exporter_type         │
│    "address": "10.0.0.1",            // Do target                │
│    "port": 9115,                     // Padrão blackbox          │
│    "meta": {                                                     │
│      "module": "icmp",                                           │
│      "target": "192.168.1.1",        // Campo específico         │
│      "company": "Ramada",                                        │
│      "site": "palmas",                                           │
│      "env": "prod",                                              │
│      "name": "Gateway Principal"                                 │
│    },                                                            │
│    "tags": ["network", "icmp", "prod"]                           │
│  }                                                               │
└──────────────────────┬──────────────────────────────────────────┘
                       │
                       │ ConsulManager.register_service()
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│  PASSO 7: Registro no Consul                                    │
│  PUT /v1/agent/service/register                                  │
│                                                                  │
│  Serviço aparece imediatamente em:                               │
│  - DynamicMonitoringPage (após refresh)                          │
│  - Prometheus (após próximo scrape)                              │
│  - Grafana (após dados chegarem)                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

#### 7.2. CÓDIGO FRONTEND: DynamicCRUDModal (Skeleton)

**Novo arquivo:** `frontend/src/components/DynamicCRUDModal.tsx`

```typescript
import React, { useState, useEffect } from 'react';
import { Modal, Form, Select, Spin, message, Tabs, Space } from 'antd';
import { consulAPI } from '../services/api';
import FormFieldRenderer from './FormFieldRenderer';

interface DynamicCRUDModalProps {
  visible: boolean;
  mode: 'create' | 'edit';
  category: string;
  initialValues?: Record<string, any>;
  onSubmit: (values: Record<string, any>) => Promise<void>;
  onCancel: () => void;
}

const DynamicCRUDModal: React.FC<DynamicCRUDModalProps> = ({
  visible,
  mode,
  category,
  initialValues,
  onSubmit,
  onCancel,
}) => {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [availableTypes, setAvailableTypes] = useState<any[]>([]);
  const [selectedType, setSelectedType] = useState<string | null>(null);
  const [formSchema, setFormSchema] = useState<any>(null);
  const [metadataFields, setMetadataFields] = useState<any[]>([]);

  // PASSO 1: Carregar tipos disponíveis para a categoria
  useEffect(() => {
    if (visible && mode === 'create') {
      loadAvailableTypes();
    }
  }, [visible, category, mode]);

  const loadAvailableTypes = async () => {
    setLoading(true);
    try {
      const response = await consulAPI.getMonitoringTypesDynamic({
        category
      });

      if (response.data.success) {
        // Extrair tipos da categoria
        const categoryData = response.data.categories.find(
          (cat: any) => cat.category === category
        );
        setAvailableTypes(categoryData?.types || []);
      }
    } catch (error) {
      message.error('Erro ao carregar tipos disponíveis');
    } finally {
      setLoading(false);
    }
  };

  // PASSO 2: Quando tipo é selecionado, carregar form_schema
  const handleTypeChange = async (typeId: string) => {
    setSelectedType(typeId);
    setLoading(true);

    try {
      const selectedTypeObj = availableTypes.find((t) => t.id === typeId);

      // Buscar form_schema da regra de categorização
      const response = await consulAPI.getFormSchema({
        exporter_type: selectedTypeObj.exporter_type,
        category,
      });

      if (response.data.success) {
        setFormSchema(response.data.form_schema);
      }

      // Carregar metadata fields genéricos
      const metaResponse = await consulAPI.getMetadataFields();
      setMetadataFields(metaResponse.data.fields || []);
    } catch (error) {
      message.error('Erro ao carregar configuração do formulário');
    } finally {
      setLoading(false);
    }
  };

  // PASSO 3: Submit do form
  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      await onSubmit(values);
      form.resetFields();
      onCancel();
    } catch (error) {
      console.error('Erro na validação:', error);
    }
  };

  return (
    <Modal
      title={mode === 'create' ? 'Criar Novo Serviço' : 'Editar Serviço'}
      open={visible}
      onOk={handleSubmit}
      onCancel={onCancel}
      width={800}
      okText={mode === 'create' ? 'Criar' : 'Salvar'}
      cancelText="Cancelar"
    >
      <Spin spinning={loading}>
        <Form form={form} layout="vertical" initialValues={initialValues}>
          {mode === 'create' && (
            <Form.Item
              label="Tipo de Monitoramento"
              name="type_id"
              rules={[{ required: true, message: 'Selecione o tipo' }]}
            >
              <Select
                placeholder="Selecione o tipo de serviço"
                onChange={handleTypeChange}
              >
                {availableTypes.map((type) => (
                  <Select.Option key={type.id} value={type.id}>
                    {type.display_name} ({type.exporter_type})
                  </Select.Option>
                ))}
              </Select>
            </Form.Item>
          )}

          {selectedType && formSchema && (
            <Tabs defaultActiveKey="1">
              {/* TAB 1: Campos Específicos do Exporter */}
              <Tabs.TabPane tab="Configuração do Exporter" key="1">
                <Space direction="vertical" style={{ width: '100%' }}>
                  {formSchema.fields?.map((field: any) => (
                    <FormFieldRenderer
                      key={field.name}
                      field={field}
                      value={form.getFieldValue(field.name)}
                      onChange={(value) => form.setFieldValue(field.name, value)}
                    />
                  ))}
                </Space>
              </Tabs.TabPane>

              {/* TAB 2: Metadata Genéricos */}
              <Tabs.TabPane tab="Metadados" key="2">
                <Space direction="vertical" style={{ width: '100%' }}>
                  {metadataFields.map((field: any) => (
                    <FormFieldRenderer
                      key={field.name}
                      field={field}
                      value={form.getFieldValue(['meta', field.name])}
                      onChange={(value) =>
                        form.setFieldValue(['meta', field.name], value)
                      }
                    />
                  ))}
                </Space>
              </Tabs.TabPane>
            </Tabs>
          )}
        </Form>
      </Spin>
    </Modal>
  );
};

export default DynamicCRUDModal;
```

---

### 8. ROADMAP DE IMPLEMENTAÇÃO

#### 🎯 FASE 1: Backend - Extensão de Rules (2-4 horas)

**Tarefas:**
1. ✅ Adicionar `form_schema` nas regras existentes
2. ✅ Criar endpoint `GET /monitoring-types/form-schema`
3. ✅ Validar estrutura JSON de `form_schema`
4. ✅ Testar com Postman/curl

**Arquivos:**
- `backend/core/categorization_rule_engine.py`
- `backend/api/monitoring_types_dynamic.py`
- `skills/eye/monitoring-types/categorization/rules` (JSON no KV)

---

#### 🎯 FASE 2: Frontend - Componente DynamicCRUDModal (4-6 horas)

**Tarefas:**
1. ✅ Criar `DynamicCRUDModal.tsx`
2. ✅ Integrar com APIs (`getFormSchema`, `getMetadataFields`)
3. ✅ Renderizar form dinâmico com tabs
4. ✅ Validação de campos obrigatórios
5. ✅ Testes unitários

**Arquivos:**
- `frontend/src/components/DynamicCRUDModal.tsx`
- `frontend/src/components/FormFieldRenderer.tsx` (estender)
- `frontend/src/services/api.ts` (adicionar `getFormSchema`)

---

#### 🎯 FASE 3: Integração com DynamicMonitoringPage (3-4 horas)

**Tarefas:**
1. ✅ Adicionar botão "Criar Novo" no header
2. ✅ Adicionar ação "Editar" na linha da tabela
3. ✅ Adicionar ação "Deletar" (usa `useConsulDelete` existente)
4. ✅ Adicionar batch delete (seleção múltipla)
5. ✅ Refresh automático após CRUD

**Arquivos:**
- `frontend/src/pages/DynamicMonitoringPage.tsx`

**Código Snippet:**
```typescript
// DynamicMonitoringPage.tsx
const [crudModalVisible, setCrudModalVisible] = useState(false);
const [crudMode, setCrudMode] = useState<'create' | 'edit'>('create');
const [editingRecord, setEditingRecord] = useState<any>(null);

const handleCreate = () => {
  setCrudMode('create');
  setEditingRecord(null);
  setCrudModalVisible(true);
};

const handleEdit = (record: any) => {
  setCrudMode('edit');
  setEditingRecord(record);
  setCrudModalVisible(true);
};

const handleSubmit = async (values: any) => {
  if (crudMode === 'create') {
    await consulAPI.createService(values);
    message.success('Serviço criado com sucesso!');
  } else {
    await consulAPI.updateService(editingRecord.ID, values);
    message.success('Serviço atualizado com sucesso!');
  }
  actionRef.current?.reload();
};

// No render:
<PageContainer
  extra={[
    <Button key="create" type="primary" icon={<PlusOutlined />} onClick={handleCreate}>
      Criar Novo
    </Button>
  ]}
>
  {/* ... ProTable ... */}

  <DynamicCRUDModal
    visible={crudModalVisible}
    mode={crudMode}
    category={category}
    initialValues={editingRecord}
    onSubmit={handleSubmit}
    onCancel={() => setCrudModalVisible(false)}
  />
</PageContainer>
```

---

#### 🎯 FASE 4: Testes e Validação (2-3 horas)

**Tarefas:**
1. ✅ Testar criação de serviço blackbox (ICMP)
2. ✅ Testar criação de serviço SNMP
3. ✅ Testar edição de metadata
4. ✅ Testar exclusão (single e batch)
5. ✅ Validar aparecimento em Prometheus
6. ✅ Validar categorização automática

---

#### 🎯 FASE 5: Documentação (1-2 horas)

**Tarefas:**
1. ✅ Atualizar CLAUDE.md com nova arquitetura
2. ✅ Documentar estrutura `form_schema`
3. ✅ Criar guia de adição de novos exporters
4. ✅ Screenshots do CRUD em ação

---

### 9. PÁGINAS LEGADAS - O QUE REAPROVEITAR

#### 9.1. Services.tsx (SERÁ DESATIVADA)

**O que está pronto e pode ser reutilizado:**

✅ **Modal de Criação:**
```typescript
// services.tsx:450-550
<ModalForm
  title="Criar Novo Serviço"
  open={createModalVisible}
  onFinish={handleCreate}
>
  {/* Renderização dinâmica de campos via FormFieldRenderer */}
  {formFields.map((field) => (
    <FormFieldRenderer key={field.name} field={field} />
  ))}
</ModalForm>
```

✅ **Validação de Duplicatas:**
```typescript
// services.tsx:120
const handleCreate = async (values: any) => {
  // Verificar se já existe serviço com mesmo nome
  const existingService = data.find(
    (s) => s.Service === values.service && s.Meta.name === values.meta.name
  );

  if (existingService) {
    message.warning('Já existe um serviço com esse nome');
    return false;
  }

  await consulAPI.createService(values);
  message.success('Serviço criado!');
  actionRef.current?.reload();
};
```

✅ **Auto-Cadastro de Valores:**
```typescript
// services.tsx:180
// Quando usuário digita novo valor em campo select
// → Adiciona automaticamente em reference-values
const handleNewValue = async (fieldName: string, newValue: string) => {
  await consulAPI.createReferenceValue({ field: fieldName, value: newValue });
  message.success(`Valor "${newValue}" adicionado!`);
  // Recarregar options do campo
};
```

✅ **Batch Delete:**
```typescript
// services.tsx:250
const [selectedRowKeys, setSelectedRowKeys] = useState<string[]>([]);

const handleBatchDelete = async () => {
  await consulAPI.bulkDeregisterServices(selectedRowKeys);
  message.success(`${selectedRowKeys.length} serviços removidos`);
  setSelectedRowKeys([]);
  actionRef.current?.reload();
};

// No ProTable:
<ProTable
  rowSelection={{
    selectedRowKeys,
    onChange: setSelectedRowKeys,
  }}
/>
```

**⚠️ NÃO COPIAR DIRETO:**
- Código misturado com lógica específica de Services.tsx
- Criar componentes novos baseados nestes padrões
- DRY: Extrair para `DynamicCRUDModal` e hooks compartilhados

---

#### 9.2. Exporters.tsx e BlackboxTargets.tsx (SERÃO DESATIVADAS)

**O que aprender:**

✅ **Padrão de colunas dinâmicas:**
```typescript
// Similar ao que já temos em DynamicMonitoringPage
const columns = useMemo(() => {
  return [
    { title: 'Nome', dataIndex: 'name', fixed: 'left' },
    // Colunas dinâmicas baseadas em metadados
    ...dynamicColumns,
  ];
}, [dynamicColumns]);
```

✅ **Exportação CSV:**
```typescript
// exporters.tsx:300
const handleExportCSV = () => {
  const csv = data.map((item) => ({
    ID: item.ID,
    Service: item.Service,
    Address: item.Address,
    Port: item.Port,
    ...item.Meta,
  }));

  downloadCSV(csv, `exporters-${Date.now()}.csv`);
};
```

**⚠️ ATENÇÃO:**
- Não copiar código legado
- Usar padrões já estabelecidos em `DynamicMonitoringPage`

---

### 10. COMPARAÇÃO: Documento Cursor vs Claude Code

#### 10.1. PONTOS EM COMUM ✅

1. ✅ **monitoring-types e DynamicMonitoringPage não estão integrados**
2. ✅ **Backend CRUD já existe em services.py**
3. ✅ **Problema de campos customizados por exporter**
4. ✅ **service-groups mostra apenas serviços com instâncias (comportamento natural Consul)**

---

#### 10.2. DIFERENÇAS E COMPLEMENTOS

| Aspecto | Documento Cursor | Documento Claude Code |
|---------|------------------|----------------------|
| **Solução para campos dinâmicos** | Menciona problema | ✅ **Proposta completa com `form_schema`** |
| **Estrutura JSON form_schema** | ❌ Não detalha | ✅ **JSON completo com validações** |
| **Componente DynamicCRUDModal** | ❌ Não mostra código | ✅ **Código skeleton completo** |
| **Integração com DynamicMonitoringPage** | Menciona necessidade | ✅ **Código de integração detalhado** |
| **API form-schema** | ❌ Não menciona | ✅ **Endpoint novo com código Python** |
| **Docs oficiais (Consul, Prometheus, etc)** | Menciona | ✅ **Resumo técnico com links e exemplos** |
| **Roadmap de implementação** | ❌ Não estruturado | ✅ **Fases detalhadas com horas estimadas** |
| **Código reutilizável de Services.tsx** | Menciona existência | ✅ **Snippets específicos para reaproveitar** |

---

### 11. RECOMENDAÇÕES FINAIS

#### 11.1. PRIORIDADES IMEDIATAS

**🥇 PRIORIDADE 1:** Implementar `form_schema` em categorization/rules
- **Tempo:** 2-4 horas
- **Impacto:** **CRÍTICO** - Sem isso, não há CRUD dinâmico real
- **Arquivos:** `skills/eye/monitoring-types/categorization/rules` (JSON)

**🥈 PRIORIDADE 2:** Criar endpoint `GET /monitoring-types/form-schema`
- **Tempo:** 1-2 horas
- **Impacto:** **ALTO** - Frontend depende disto
- **Arquivos:** `backend/api/monitoring_types_dynamic.py`

**🥉 PRIORIDADE 3:** Criar componente `DynamicCRUDModal`
- **Tempo:** 4-6 horas
- **Impacto:** **ALTO** - Core do CRUD
- **Arquivos:** `frontend/src/components/DynamicCRUDModal.tsx`

**4️⃣ PRIORIDADE 4:** Integrar com `DynamicMonitoringPage`
- **Tempo:** 3-4 horas
- **Impacto:** **MÉDIO** - Finaliza CRUD
- **Arquivos:** `frontend/src/pages/DynamicMonitoringPage.tsx`

---

#### 11.2. ARQUITETURA 100% DINÂMICA - CHECKLIST

✅ **Leitura (READ):**
- ✅ Tipos dinâmicos de prometheus.yml
- ✅ Categorização dinâmica via rules
- ✅ Colunas dinâmicas via metadata-fields
- ✅ Filtros dinâmicos via useFilterFields

✅ **Criação (CREATE):**
- ⚡ Form dinâmico baseado em `form_schema` ← **IMPLEMENTAR**
- ⚡ Validações dinâmicas por tipo ← **IMPLEMENTAR**
- ✅ Backend já funcional

✅ **Atualização (UPDATE):**
- ⚡ Modal de edição dinâmico ← **IMPLEMENTAR**
- ✅ Backend já funcional

✅ **Exclusão (DELETE):**
- ⚡ Confirmação + feedback ← **USAR `useConsulDelete` existente**
- ⚡ Batch delete ← **IMPLEMENTAR seleção múltipla**
- ✅ Backend já funcional

---

#### 11.3. PRÓXIMOS PASSOS (Sugestão de Ordem)

**SPRINT 1 (1 semana):**
1. ✅ Adicionar `form_schema` em 3-5 regras principais (blackbox, snmp, windows, node)
2. ✅ Criar endpoint `/monitoring-types/form-schema`
3. ✅ Testar endpoint com Postman

**SPRINT 2 (1 semana):**
1. ✅ Criar `DynamicCRUDModal.tsx` básico
2. ✅ Testar com 1 tipo (ex: blackbox-icmp)
3. ✅ Validar criação end-to-end (frontend → backend → Consul → Prometheus)

**SPRINT 3 (1 semana):**
1. ✅ Integrar modal com `DynamicMonitoringPage`
2. ✅ Implementar edição
3. ✅ Implementar exclusão (single + batch)
4. ✅ Testar com múltiplos tipos de exporters

**SPRINT 4 (1 semana):**
1. ✅ Testes completos em todas as categorias
2. ✅ Documentação
3. ✅ Desativar páginas legadas (Services, Exporters, BlackboxTargets)
4. ✅ Celebrar! 🎉

---

## 🎉 CONCLUSÃO

Este documento fornece uma **análise completa e independente** da arquitetura CRUD dinâmico do Skills Eye, com:

✅ **Diagnóstico preciso** dos componentes atuais
✅ **Solução concreta** para campos dinâmicos (form_schema)
✅ **Código de exemplo** pronto para implementar
✅ **Roadmap claro** com estimativas de tempo
✅ **Reutilização inteligente** de código existente
✅ **Documentação técnica** de Consul, Prometheus, Blackbox, SNMP

**Diferenciais vs Documento Cursor:**
- ⚡ Proposta estruturada de `form_schema` com JSON completo
- ⚡ Código skeleton de `DynamicCRUDModal` e endpoint backend
- ⚡ Integração detalhada com `DynamicMonitoringPage`
- ⚡ Resumo técnico de documentações oficiais
- ⚡ Roadmap por sprints com horas estimadas

**Próximo Passo:** Iniciar SPRINT 1 - Extensão de `categorization/rules` com `form_schema`

---

**Documento criado por:** Claude Code (Sonnet 4.5)
**Data:** 2025-11-17
**Versão:** 1.0 - Análise Completa Independente
**Status:** ✅ Pronto para Implementação
