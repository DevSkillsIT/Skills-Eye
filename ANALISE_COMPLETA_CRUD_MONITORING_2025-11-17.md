# 📊 Análise Completa: Arquitetura CRUD para Páginas Monitoring/*

**Data:** 2025-11-17  
**Autor:** Análise Profissional - Skills Eye  
**Status:** ✅ Análise Completa - Pronto para Implementação

---

## 🎯 Objetivo

Analisar a arquitetura completa do sistema de monitoramento para implementar CRUD nas páginas `monitoring/*`, entendendo:
1. Relação entre `monitoring-types` e `DynamicMonitoringPage`
2. Vínculos com `service-groups`
3. Diferença entre Consul (descoberta) e Prometheus (tipos)
4. Arquitetura 100% dinâmica
5. Componentes compartilhados
6. Documentações técnicas (Consul, Blackbox, SNMP, Prometheus)

---

## 📋 Sumário Executivo

### Descobertas Principais

1. **`monitoring-types` NÃO está integrado ao `DynamicMonitoringPage`**
   - São sistemas **independentes** com propósitos diferentes
   - `monitoring-types`: **Catálogo** de tipos disponíveis (Prometheus.yml)
   - `DynamicMonitoringPage`: **Visualização** de instâncias reais (Consul)

2. **`service-groups` mostra serviços DESCOBERTOS no Consul**
   - ✅ **Comportamento natural do Consul** - não é um gap
   - Consul é apenas descoberta de serviços (service discovery)
   - Mostra apenas serviços com instâncias registradas
   - `service-groups`: "O que **está** sendo monitorado" (instâncias reais)
   - `monitoring-types`: "O que **pode** ser monitorado" (tipos configurados)

3. **Backend CRUD já existe e está funcional**
   - ✅ `backend/api/services.py` - Endpoints completos (POST, PUT, DELETE)
   - ✅ `ConsulManager.register_service()` - Funcional
   - ✅ `ConsulManager.update_service()` - Funcional
   - ✅ `ConsulManager.deregister_service()` - Funcional
   - ✅ `Services.tsx` - Frontend com CRUD funcional (será desativado)

4. **Problema crítico: Campos customizados por exporter_type**
   - SNMP exporter precisa: `snmp_community`, `snmp_module`
   - Windows exporter precisa: `port` (padrão 9182)
   - Node exporter precisa: `port` (padrão 9100)
   - Blackbox precisa: `module`, `target`
   - **Atualmente:** Apenas metadata genéricos são tratados
   - **Solução proposta:** Estender `categorization/rules` com `form_schema`

4. **Componentes compartilhados identificados**
   - `NodeSelector`, `ServerSelector`, `ColumnSelector`
   - `MetadataFilterBar`, `AdvancedSearchPanel`
   - `useMetadataFields`, `useServersContext`

---

## 🔍 Análise Detalhada

### 1. Relação entre `monitoring-types` e `DynamicMonitoringPage`

#### 1.1. `MonitoringTypes.tsx` (Página de Catálogo)

**Propósito:**
- Mostra **tipos de monitoramento disponíveis** extraídos do `prometheus.yml`
- É um **catálogo/referência** dos tipos configurados
- **Fonte:** `prometheus.yml` de cada servidor Prometheus

**Endpoint Backend:**
```
GET /api/v1/monitoring-types-dynamic/from-prometheus
```

**Dados Retornados:**
```json
{
  "success": true,
  "categories": [
    {
      "category": "network-probes",
      "display_name": "Network Probes (Rede)",
      "types": [
        {
          "id": "blackbox-icmp",
          "display_name": "ICMP (Ping)",
          "job_name": "blackbox-icmp",
          "exporter_type": "blackbox",
          "module": "icmp",
          "fields": ["company", "site", "module"],
          "servers": ["172.16.1.26"]
        }
      ]
    }
  ],
  "total_types": 45
}
```

**Características:**
- ✅ **Somente leitura** (catálogo)
- ✅ **Extraído dinamicamente** do `prometheus.yml`
- ✅ **Multi-servidor** (agrega tipos de todos os servidores)
- ❌ **NÃO mostra instâncias reais** (apenas tipos disponíveis)

---

#### 1.2. `DynamicMonitoringPage.tsx` (Página de Instâncias)

**Propósito:**
- Mostra **instâncias reais de serviços** registrados no Consul
- É uma **visualização operacional** dos serviços em execução
- **Fonte:** Consul Service Discovery

**Endpoint Backend:**
```
GET /api/v1/monitoring/data?category=network-probes
```

**Dados Retornados:**
```json
{
  "success": true,
  "category": "network-probes",
  "data": [
    {
      "ID": "icmp-ramada-palmas-01",
      "Service": "blackbox",
      "Address": "10.0.0.1",
      "Port": 9115,
      "Node": "consul-server-1",
      "Meta": {
        "module": "icmp",
        "company": "Ramada",
        "site": "palmas"
      }
    }
  ],
  "total": 150
}
```

**Características:**
- ✅ **Mostra instâncias reais** do Consul
- ✅ **Filtrado por categoria** (network-probes, web-probes, etc)
- ✅ **Colunas dinâmicas** via metadata fields
- ❌ **NÃO tem CRUD** (apenas visualização)

---

#### 1.3. Relação entre os Dois

```
┌─────────────────────────────────────────────────────────────┐
│                    PROMETHEUS.YML                            │
│  (Fonte da Verdade: Tipos de Monitoramento)                 │
│                                                              │
│  scrape_configs:                                             │
│    - job_name: 'blackbox-icmp'  ← Tipo disponível           │
│      consul_sd_configs: [...]                               │
│      relabel_configs: [...]                                 │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       │ Extração via SSH
                       ▼
┌─────────────────────────────────────────────────────────────┐
│          MONITORING-TYPES (Catálogo)                        │
│  GET /monitoring-types-dynamic/from-prometheus              │
│                                                              │
│  Mostra: "Existe tipo 'blackbox-icmp' configurado"          │
│  ❌ NÃO mostra se há instâncias rodando                     │
└─────────────────────────────────────────────────────────────┘
                       │
                       │ Referência
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                    CONSUL (Descoberta)                      │
│  Service Discovery: Instâncias reais em execução            │
│                                                              │
│  Services:                                                  │
│    - blackbox (10.0.0.1:9115)  ← Instância real            │
│      Meta: { module: "icmp", company: "Ramada" }          │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       │ Busca via API
                       ▼
┌─────────────────────────────────────────────────────────────┐
│       DYNAMIC-MONITORING-PAGE (Visualização)                │
│  GET /monitoring/data?category=network-probes               │
│                                                              │
│  Mostra: "Existem 150 instâncias de network-probes"         │
│  ✅ Mostra instâncias reais do Consul                      │
│  ❌ NÃO mostra tipos sem instâncias                         │
└─────────────────────────────────────────────────────────────┘
```

**Conclusão:**
- **NÃO há integração direta** entre as duas páginas
- São **complementares**, não dependentes
- `monitoring-types`: "O que **pode** ser monitorado"
- `DynamicMonitoringPage`: "O que **está** sendo monitorado"

---

### 2. Vínculos com `service-groups`

#### 2.1. `ServiceGroups.tsx` (Página de Grupos)

**Propósito:**
- Mostra **serviços agrupados** registrados no Consul
- Visão agregada de serviços com estatísticas
- **Fonte:** Consul Catalog API

**Endpoint Backend:**
```
GET /api/v1/consul/service-groups-optimized
```

**Dados Retornados:**
```json
{
  "data": [
    {
      "Name": "blackbox",
      "Datacenter": "dc1",
      "InstanceCount": 150,
      "ChecksPassing": 145,
      "ChecksCritical": 5,
      "Tags": ["icmp", "network"],
      "Nodes": ["consul-server-1", "consul-server-2"]
    }
  ],
  "summary": {
    "totalInstances": 150,
    "healthy": 145,
    "unhealthy": 5
  }
}
```

**Características:**
- ✅ **Agregação** de serviços do Consul
- ✅ **Estatísticas** (instâncias, health checks)
- ✅ **Navegação** para página de Services
- ❌ **NÃO mostra categorias** (network-probes, web-probes, etc)
- ❌ **NÃO mostra tipos sem instâncias**

---

#### 2.2. Relação com `DynamicMonitoringPage`

```
┌─────────────────────────────────────────────────────────────┐
│                    CONSUL CATALOG                            │
│  Todos os serviços registrados                              │
│                                                              │
│  Services:                                                  │
│    - blackbox (150 instâncias)                              │
│    - node-exporter (200 instâncias)                         │
│    - mysql-exporter (50 instâncias)                         │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       │ Duas visões diferentes
                       │
        ┌──────────────┴──────────────┐
        │                              │
        ▼                              ▼
┌───────────────────────┐   ┌──────────────────────────────┐
│   SERVICE-GROUPS      │   │  DYNAMIC-MONITORING-PAGE     │
│  (Visão Agregada)      │   │  (Visão por Categoria)       │
│                       │   │                              │
│  - blackbox: 150     │   │  - network-probes: 100       │
│  - node: 200         │   │  - system-exporters: 200     │
│  - mysql: 50         │   │  - database-exporters: 50    │
│                       │   │                              │
│  ❌ Sem categorias    │   │  ✅ Com categorias           │
│  ✅ Com estatísticas  │   │  ✅ Com filtros dinâmicos   │
└───────────────────────┘   └──────────────────────────────┘
```

**Conclusão:**
- **Ambas** mostram dados do Consul
- **`service-groups`**: Visão agregada sem categorias
- **`DynamicMonitoringPage`**: Visão categorizada com filtros
- **Complementares**, não concorrentes

---

### 3. Consul vs Prometheus - Comportamento Natural (Não é Gap)

#### 3.1. Arquitetura Correta

**Consul (Service Discovery):**
- ✅ Mostra **apenas serviços com instâncias registradas**
- ✅ **Comportamento esperado** - Consul é descoberta, não catálogo de tipos
- ✅ **Fonte:** Instâncias reais em execução

**Prometheus (Tipos de Monitoramento):**
- ✅ Mostra **todos os tipos** configurados no `prometheus.yml`
- ✅ **Fonte:** Configuração estática (prometheus.yml)
- ✅ **Propósito:** Catálogo de tipos disponíveis

**Relação Correta:**
```
┌─────────────────────────────────────────────────────────────┐
│  TIPO NO PROMETHEUS.YML                                     │
│  job_name: 'postgres-exporter'  ← Configurado               │
│                                                              │
│  Mas NÃO há instâncias no Consul ainda                     │
│                                                              │
│  Resultado (CORRETO):                                        │
│  ✅ Aparece em monitoring-types (catálogo)                  │
│  ❌ NÃO aparece em service-groups (sem instâncias)         │
│  ❌ NÃO aparece em DynamicMonitoringPage (sem instâncias)   │
│                                                              │
│  Isso é ESPERADO! Consul só mostra o que está rodando.      │
└─────────────────────────────────────────────────────────────┘
```

**Conclusão:**
- ✅ **Não é um gap** - é o comportamento natural do Consul
- ✅ **Arquitetura correta** - cada sistema tem seu propósito
- ✅ **Complementares** - não concorrentes

#### 3.2. Arquitetura Atual (Correta)

**Fluxo de Dados:**
```
┌─────────────────────────────────────────────────────────────┐
│              FONTE ÚNICA: PROMETHEUS.YML                    │
│  (Todos os tipos configurados)                              │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       │ Extração via SSH
                       ▼
┌─────────────────────────────────────────────────────────────┐
│         MONITORING-TYPES (Catálogo)                        │
│  GET /monitoring-types-dynamic/from-prometheus              │
│                                                              │
│  Mostra: "Existe tipo 'postgres-exporter' configurado"      │
│  ❌ NÃO mostra instâncias (não é sua responsabilidade)      │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       │ Referência para CRUD
                       ▼
┌─────────────────────────────────────────────────────────────┐
│              CONSUL (Descoberta)                            │
│  Instâncias reais em execução                               │
│                                                              │
│  Mostra: "Existem 50 instâncias de blackbox"                │
│  ❌ NÃO mostra tipos sem instâncias (comportamento natural) │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       │ Visualização + CRUD
                       ▼
┌─────────────────────────────────────────────────────────────┐
│         DYNAMIC-MONITORING-PAGE (CRUD)                      │
│                                                              │
│  Mostrar:                                                    │
│    ✅ Tipos COM instâncias (dados do Consul)               │
│    ℹ️  Tipos SEM instâncias podem ser criados via CRUD      │
│                                                              │
│  Ações CRUD:                                                 │
│    - Criar: Adicionar instância ao Consul                  │
│    - Editar: Modificar metadata do serviço                  │
│    - Excluir: Remover instância do Consul                   │
└─────────────────────────────────────────────────────────────┘
```

**Conclusão:**
- ✅ Arquitetura atual está **correta**
- ✅ Cada sistema tem sua responsabilidade clara
- ✅ CRUD permite criar instâncias de tipos disponíveis

---

### 4. Arquitetura 100% Dinâmica - Estado Atual

#### 4.1. Leitura (READ) - ✅ Implementado

**Backend:**
- `GET /api/v1/monitoring/data` - Busca serviços do Consul
- `GET /api/v1/monitoring-types-dynamic/from-prometheus` - Busca tipos
- Cache em 2 níveis (memória + KV)
- Categorização dinâmica via regras JSON

**Frontend:**
- `DynamicMonitoringPage` - Renderiza dados dinamicamente
- Colunas dinâmicas via `useTableFields(category)`
- Filtros dinâmicos via `useFilterFields(category)`
- Metadata fields configuráveis via UI

**Características:**
- ✅ **100% dinâmico** - Nada hardcoded
- ✅ **Cache inteligente** - TTL de 5 minutos
- ✅ **Multi-servidor** - Agrega dados de todos os servidores
- ✅ **Filtros avançados** - Por categoria, empresa, site, nó

---

#### 4.2. Criação (CREATE) - ✅ Backend Implementado / ❌ Frontend Não Integrado

**Backend já existe:**
- ✅ `POST /api/v1/services` - `backend/api/services.py` (linha 344)
- ✅ `ConsulManager.register_service()` - Funcional
- ✅ Validação de duplicatas
- ✅ Validação de campos obrigatórios
- ✅ Suporte multi-site (tags automáticas, sufixos)

**Frontend antigo (Services.tsx):**
- ✅ `ModalForm` com campos dinâmicos
- ✅ `useFormFields('services')` - Campos metadata
- ✅ `FormFieldRenderer` - Renderização dinâmica
- ✅ Validação e auto-cadastro de valores
- ⚠️ **Será desativado** - não misturar código

**O que falta para DynamicMonitoringPage:**
- ❌ Integrar modal de criação no `DynamicMonitoringPage`
- ❌ Carregar tipos disponíveis de `monitoring-types`
- ❌ Renderizar campos customizados por `exporter_type`
- ❌ Validar campos obrigatórios específicos do tipo

---

#### 4.3. Edição (UPDATE) - ✅ Backend Implementado / ❌ Frontend Não Integrado

**Backend já existe:**
- ✅ `PUT /api/v1/services/{service_id}` - `backend/api/services.py` (linha 519)
- ✅ `ConsulManager.update_service()` - Funcional
- ✅ Re-registro automático (comportamento do Consul)
- ✅ Suporte multi-site

**Frontend antigo (Services.tsx):**
- ✅ `ModalForm` em modo edit
- ✅ Preenchimento automático de valores
- ✅ Validação de campos editáveis
- ⚠️ **Será desativado** - não misturar código

**O que falta para DynamicMonitoringPage:**
- ❌ Integrar modal de edição no `DynamicMonitoringPage`
- ❌ Carregar campos editáveis de `metadata-fields`
- ❌ Validar campos customizados do `exporter_type`

---

#### 4.4. Exclusão (DELETE) - ✅ Backend Implementado / ❌ Frontend Não Integrado

**Backend já existe:**
- ✅ `DELETE /api/v1/services/{service_id}` - `backend/api/services.py` (linha 681)
- ✅ `DELETE /api/v1/services/bulk/deregister` - Batch delete (linha 640)
- ✅ `ConsulManager.deregister_service()` - Funcional
- ✅ Validação de existência

**Frontend antigo (Services.tsx):**
- ✅ `Popconfirm` para confirmação
- ✅ `useConsulDelete` hook compartilhado
- ✅ Batch delete com seleção múltipla
- ✅ Feedback visual (success/error)
- ⚠️ **Será desativado** - não misturar código

**O que falta para DynamicMonitoringPage:**
- ❌ Integrar ações de exclusão no `DynamicMonitoringPage`
- ❌ Implementar batch delete (seleção múltipla)
- ❌ Usar `useConsulDelete` hook compartilhado

---

### 5. Página `monitoring/rules` - Análise e Integração

#### 5.1. `MonitoringRules.tsx` (Gerenciamento de Regras)

**Propósito:**
- CRUD completo de regras de categorização
- Armazenado em: `skills/eye/monitoring-types/categorization/rules`
- Usado por: `CategorizationRuleEngine` para categorizar serviços

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
      }
    }
  ]
}
```

**Oportunidade de Extensão:**
- ✅ Adicionar `form_schema` para campos customizados por `exporter_type`
- ✅ Definir campos obrigatórios específicos
- ✅ Definir campos opcionais específicos
- ✅ Validações customizadas por tipo

**Proposta de Extensão:**
```json
{
  "id": "snmp_exporter",
  "priority": 80,
  "category": "system-exporters",
  "display_name": "SNMP Exporter",
  "exporter_type": "snmp_exporter",
  "conditions": {
    "job_name_pattern": ".*snmp.*"
  },
  "form_schema": {
    "exporter_fields": [
      {
        "name": "snmp_community",
        "label": "SNMP Community",
        "type": "text",
        "required": false,
        "default": "public",
        "help": "SNMP community string (v2c)"
      },
      {
        "name": "snmp_module",
        "label": "Módulo SNMP",
        "type": "select",
        "required": true,
        "options": ["if_mib", "mikrotik", "cisco", "dell", "hp"],
        "default": "if_mib"
      }
    ],
    "required_metadata": ["company", "fabricante"],
    "optional_metadata": ["modelo", "localizacao"]
  }
}
```

**Integração na Arquitetura:**
- ✅ `MonitoringRules.tsx` já permite editar regras
- ✅ Pode ser estendido para editar `form_schema`
- ✅ Fonte única de verdade para campos customizados
- ✅ 100% dinâmico - editável via UI

---

### 6. Componentes Compartilhados Identificados

#### 6.1. Componentes de Seleção

**`NodeSelector.tsx`**
- Seleção de nós do Consul
- Usado em: `DynamicMonitoringPage`, `MetadataFields`, `PrometheusConfig`
- ✅ **Reutilizável** - Já compartilhado

**`ServerSelector.tsx`**
- Seleção de servidores Prometheus
- Usado em: `MonitoringTypes`, `MetadataFields`, `PrometheusConfig`
- ✅ **Reutilizável** - Já compartilhado

**`ColumnSelector.tsx`**
- Seleção de colunas visíveis
- Usado em: `DynamicMonitoringPage`, `MonitoringTypes`, `Services`
- ✅ **Reutilizável** - Já compartilhado

---

#### 6.2. Componentes de Filtro

**`MetadataFilterBar.tsx`**
- Barra de filtros por metadata
- Usado em: `DynamicMonitoringPage`
- ✅ **Reutilizável** - Pode ser usado em outras páginas

**`AdvancedSearchPanel.tsx`**
- Painel de busca avançada
- Usado em: `DynamicMonitoringPage`
- ✅ **Reutilizável** - Pode ser usado em outras páginas

---

#### 6.3. Hooks Compartilhados

**`useMetadataFields.ts`**
- Carrega campos metadata dinamicamente
- Usado em: `DynamicMonitoringPage`, `MetadataFields`
- ✅ **Reutilizável** - Já compartilhado

**`useServersContext.tsx`**
- Context de servidores Prometheus
- Usado em: `MonitoringTypes`, `MetadataFields`, `PrometheusConfig`
- ✅ **Reutilizável** - Já compartilhado

**`useNodesContext.tsx`**
- Context de nós do Consul
- Usado em: `DynamicMonitoringPage`, `Services`
- ✅ **Reutilizável** - Já compartilhado

---

#### 6.4. Componentes de Formulário (Para CRUD)

**Proposta de Componentes Novos:**

**`MonitoringServiceFormModal.tsx`** (Criar/Editar) - **NOVO, não misturar com código antigo**
```typescript
interface ServiceFormModalProps {
  mode: 'create' | 'edit';
  category: string;
  service?: MonitoringDataItem;
  availableTypes: MonitoringType[];
  onSuccess: () => void;
  onCancel: () => void;
}
```

**`BatchDeleteModal.tsx`** (Excluir Múltiplos)
```typescript
interface BatchDeleteModalProps {
  services: MonitoringDataItem[];
  onConfirm: () => void;
  onCancel: () => void;
}
```

**`ServiceTypeSelector.tsx`** (Selecionar Tipo)
```typescript
interface ServiceTypeSelectorProps {
  category: string;
  value?: string;
  onChange: (type: string) => void;
}
```

---

### 7. Problema Crítico: Campos Customizados por Exporter Type

**Contexto:**
O usuário identificou corretamente que cada tipo de exporter precisa de campos específicos que não são apenas metadata genéricos. Por exemplo:
- SNMP exporter precisa de `snmp_community` e `snmp_module`
- Windows exporter precisa de `port` (padrão diferente do Node)
- MySQL/PostgreSQL exporters precisam de credenciais específicas

**Problema:**
Atualmente, apenas metadata genéricos (company, site, env, etc) são tratados via `metadata-fields`. Campos específicos do exporter não têm lugar definido de forma dinâmica.

**Solução Proposta:**
Estender `categorization/rules` (já usado para categorização) para incluir `form_schema` com campos customizados por `exporter_type`. Isso mantém tudo 100% dinâmico e editável via UI (`monitoring/rules`).

#### 7.1. Problema Identificado

**Cada tipo de exporter tem campos específicos:**

| Exporter Type | Campos Específicos | Onde Configurar? |
|---------------|-------------------|------------------|
| **SNMP Exporter** | `snmp_community`, `snmp_module` | ❓ Não definido |
| **Windows Exporter** | `port` (padrão: 9182) | ❓ Não definido |
| **Node Exporter** | `port` (padrão: 9100) | ❓ Não definido |
| **Blackbox** | `module`, `target` | ✅ Já tratado (metadata) |
| **MySQL Exporter** | `port`, `user`, `password` | ❓ Não definido |
| **PostgreSQL Exporter** | `port`, `database` | ❓ Não definido |

**Problema Atual:**
- ✅ Metadata genéricos são tratados via `metadata-fields`
- ❌ Campos específicos do exporter não têm lugar definido
- ❌ JSONs estáticos em `backend/schemas/monitoring-types/` (serão removidos)

#### 7.2. Solução Proposta: Estender `categorization/rules`

**Arquitetura:**
```
┌─────────────────────────────────────────────────────────────┐
│  CATEGORIZATION RULES (KV)                                 │
│  skills/eye/monitoring-types/categorization/rules            │
│                                                              │
│  Estrutura Proposta:                                        │
│  {                                                           │
│    "rules": [                                               │
│      {                                                       │
│        "id": "snmp_exporter",                               │
│        "exporter_type": "snmp_exporter",                    │
│        "category": "system-exporters",                      │
│        "form_schema": {  ← NOVO                             │
│          "exporter_fields": [                               │
│            {                                                 │
│              "name": "snmp_community",                      │
│              "type": "text",                                │
│              "required": false,                             │
│              "default": "public"                            │
│            }                                                 │
│          ]                                                   │
│        }                                                     │
│      }                                                       │
│    ]                                                         │
│  }                                                           │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       │ Usado por
                       ▼
┌─────────────────────────────────────────────────────────────┐
│         DYNAMIC-MONITORING-PAGE (CRUD)                      │
│                                                              │
│  Ao criar serviço:                                           │
│    1. Identificar exporter_type do monitoring-type          │
│    2. Buscar regra correspondente em categorization/rules   │
│    3. Renderizar campos do form_schema.exporter_fields      │
│    4. Validar campos obrigatórios                          │
│    5. Salvar no Consul (campos vão para Meta)               │
└─────────────────────────────────────────────────────────────┘
```

**Vantagens:**
- ✅ **100% dinâmico** - Nada hardcoded
- ✅ **Centralizado** - Tudo em `categorization/rules`
- ✅ **Editável via UI** - Página `monitoring/rules`
- ✅ **Extensível** - Adicionar novos tipos sem código

---

### 8. Documentações Técnicas Estudadas

#### 6.1. Consul (Service Discovery)

**Conceitos Principais:**
- **Service Discovery**: Registro automático de serviços
- **Health Checks**: Verificação de saúde dos serviços
- **KV Store**: Armazenamento de configurações
- **Catalog API**: Listagem de serviços e nós
- **Agent API**: Operações no agente local

**Relevância para CRUD:**
- ✅ **CREATE**: Registrar novo serviço via Agent API
- ✅ **UPDATE**: Atualizar metadata via Agent API
- ✅ **DELETE**: Desregistrar serviço via Agent API
- ✅ **READ**: Já implementado via Catalog API

**Endpoints Relevantes:**
```
PUT /v1/agent/service/register     # Criar serviço
PUT /v1/agent/service/deregister   # Excluir serviço
PUT /v1/agent/service/maintenance  # Manutenção
GET /v1/catalog/service/{service}  # Buscar serviço
```

---

#### 8.2. Blackbox Exporter

**Conceitos Principais:**
- **Módulos**: Configurações de probe (icmp, http_2xx, tcp, etc)
- **Targets**: Alvos a serem monitorados
- **Metrics**: Métricas expostas (`probe_success`, `probe_duration_seconds`)
- **Relabeling**: Transformação de labels

**Relevância para CRUD:**
- ✅ **Validação**: Verificar se módulo existe antes de criar
- ✅ **Metadata**: Extrair módulo do `prometheus.yml`
- ✅ **Categorização**: Identificar se é network-probe ou web-probe

**Configuração Típica:**
```yaml
scrape_configs:
  - job_name: 'blackbox-icmp'
    metrics_path: /probe
    params:
      module: [icmp]
    consul_sd_configs:
      - server: '172.16.1.26:8500'
        services: ['blackbox']
    relabel_configs:
      - source_labels: [__meta_consul_service_metadata_module]
        target_label: module
```

---

#### 8.3. SNMP Exporter

**Conceitos Principais:**
- **MIBs**: Management Information Bases (definições de OIDs)
- **Generators**: Geração de configuração a partir de MIBs
- **Walk**: Coleta de dados SNMP
- **OIDs**: Object Identifiers (identificadores únicos)

**Relevância para CRUD:**
- ✅ **Validação**: Verificar se OID é válido
- ✅ **Metadata**: Extrair comunidade SNMP, versão
- ✅ **Categorização**: Identificar como system-exporter

**Configuração Típica:**
```yaml
scrape_configs:
  - job_name: 'snmp-network-devices'
    static_configs:
      - targets:
          - 192.168.1.1:161
        labels:
          community: 'public'
          version: '2'
```

---

#### 8.4. Prometheus

**Conceitos Principais:**
- **Scrape Configs**: Configuração de coleta de métricas
- **Service Discovery**: Descoberta automática de targets
- **Relabeling**: Transformação de labels antes de armazenar
- **Recording Rules**: Regras de agregação de métricas

**Relevância para CRUD:**
- ✅ **Validação**: Verificar se job_name existe no prometheus.yml
- ✅ **Sincronização**: Garantir que serviço no Consul corresponde a job no Prometheus
- ✅ **Metadata**: Extrair campos de relabel_configs

**Fluxo Típico:**
```
1. Prometheus consulta Consul (service discovery)
2. Consul retorna lista de serviços
3. Prometheus faz scrape de cada serviço
4. Métricas são armazenadas com labels do Consul
```

---

## 🎯 Proposta de Implementação CRUD

### Fase 1: Backend - Endpoints CRUD

#### 1.1. CREATE - Registrar Serviço

**Endpoint:**
```python
POST /api/v1/monitoring/services
{
  "service_name": "blackbox",
  "address": "10.0.0.1",
  "port": 9115,
  "node": "consul-server-1",
  "tags": ["icmp", "network"],
  "meta": {
    "module": "icmp",
    "company": "Ramada",
    "site": "palmas",
    "env": "prod"
  }
}
```

**Implementação:**
```python
@router.post("/services")
async def create_service(service_data: ServiceCreateRequest):
    """
    Registra novo serviço no Consul
    
    Validações:
    1. Verificar se tipo existe no monitoring-types
    2. Validar metadata obrigatórios
    3. Registrar no Consul via Agent API
    4. Invalidar cache
    """
    # 1. Validar tipo
    monitoring_type = await validate_monitoring_type(
        service_data.service_name,
        service_data.meta.get('module')
    )
    
    # 2. Validar metadata obrigatórios
    required_fields = await get_required_fields(monitoring_type.category)
    validate_metadata(service_data.meta, required_fields)
    
    # 3. Registrar no Consul
    consul_service = {
        "ID": generate_service_id(service_data),
        "Name": service_data.service_name,
        "Address": service_data.address,
        "Port": service_data.port,
        "Tags": service_data.tags,
        "Meta": service_data.meta
    }
    
    await consul_manager.register_service(
        node=service_data.node,
        service=consul_service
    )
    
    # 4. Invalidar cache
    cache.invalidate(f"monitoring:services:{monitoring_type.category}")
    
    return {"success": True, "service_id": consul_service["ID"]}
```

---

#### 1.2. Endpoint para Buscar Schema de Formulário

**Novo Endpoint:**
```python
# backend/api/monitoring_unified.py

@router.get("/form-schema/{exporter_type}")
async def get_form_schema(exporter_type: str):
    """
    Retorna schema de formulário para um exporter_type específico
    
    Busca em:
    1. categorization/rules (form_schema.exporter_fields)
    2. metadata-fields (campos genéricos)
    
    Returns:
        {
            "exporter_type": "snmp_exporter",
            "exporter_fields": [
                {"name": "snmp_community", "type": "text", ...}
            ],
            "metadata_fields": [
                {"name": "company", "required": true, ...}
            ]
        }
    """
    # 1. Buscar regra de categorização
    rules = await kv_manager.get('monitoring-types/categorization/rules')
    rule = next((r for r in rules['rules'] if r.get('exporter_type') == exporter_type), None)
    
    # 2. Buscar metadata fields
    metadata_fields = await load_fields_config()
    
    # 3. Combinar
    return {
        "exporter_type": exporter_type,
        "exporter_fields": rule.get('form_schema', {}).get('exporter_fields', []) if rule else [],
        "required_metadata": rule.get('form_schema', {}).get('required_metadata', []) if rule else [],
        "optional_metadata": rule.get('form_schema', {}).get('optional_metadata', []) if rule else [],
        "metadata_fields": metadata_fields.get('fields', [])
    }
```

---

### Fase 2: Frontend - Componentes CRUD

#### 2.1. Modal de Criação

**Componente Novo (não misturar com código antigo):**
```typescript
// frontend/src/components/MonitoringServiceFormModal.tsx

interface MonitoringServiceFormModalProps {
  mode: 'create' | 'edit';
  category: string;
  service?: MonitoringDataItem;
  availableTypes: MonitoringType[];  // Do monitoring-types
  visible: boolean;
  onSuccess: () => void;
  onCancel: () => void;
}

export const MonitoringServiceFormModal: React.FC<MonitoringServiceFormModalProps> = ({
  mode,
  category,
  service,
  availableTypes,
  visible,
  onSuccess,
  onCancel
}) => {
  const [form] = Form.useForm();
  const [exporterFields, setExporterFields] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const { filterFields } = useFilterFields(category);
  
  // Carregar form_schema quando exporter_type mudar
  useEffect(() => {
    const exporterType = form.getFieldValue('exporter_type');
    if (exporterType) {
      loadFormSchema(exporterType);
    }
  }, [form.getFieldValue('exporter_type')]);
  
  const loadFormSchema = async (exporterType: string) => {
    try {
      setLoading(true);
      const response = await axios.get(`/api/v1/monitoring/form-schema/${exporterType}`);
      setExporterFields(response.data.exporter_fields || []);
    } catch (error) {
      console.error('Erro ao carregar form_schema:', error);
      setExporterFields([]);
    } finally {
      setLoading(false);
    }
  };
  
  // Preencher form se modo edit
  useEffect(() => {
    if (mode === 'edit' && service) {
      form.setFieldsValue({
        service_name: service.Service,
        address: service.Address,
        port: service.Port,
        node: service.Node,
        tags: service.Tags,
        exporter_type: service.Meta?.exporter_type || service.Meta?.job,
        ...service.Meta
      });
      // Carregar form_schema se tiver exporter_type
      if (service.Meta?.exporter_type || service.Meta?.job) {
        loadFormSchema(service.Meta?.exporter_type || service.Meta?.job);
      }
    }
  }, [mode, service, form]);
  
  const handleSubmit = async (values: any) => {
    try {
      if (mode === 'create') {
        await consulAPI.createService({
          ...values,
          category
        });
      } else {
        await consulAPI.updateService(service!.ID, {
          meta: values
        });
      }
      
      message.success(`Serviço ${mode === 'create' ? 'criado' : 'atualizado'} com sucesso!`);
      onSuccess();
    } catch (error) {
      message.error(`Erro ao ${mode === 'create' ? 'criar' : 'atualizar'} serviço`);
    }
  };
  
  return (
    <Modal
      title={mode === 'create' ? 'Criar Serviço' : 'Editar Serviço'}
      visible={visible}
      onCancel={onCancel}
      onOk={() => form.submit()}
      width={800}
    >
      <Form form={form} onFinish={handleSubmit} layout="vertical">
        {/* Campos básicos */}
        <Form.Item name="service_name" label="Nome do Serviço" rules={[{ required: true }]}>
          <Select>
            {availableTypes
              .filter(t => t.category === category)
              .map(type => (
                <Select.Option key={type.id} value={type.job_name}>
                  {type.display_name}
                </Select.Option>
              ))}
          </Select>
        </Form.Item>
        
        <Form.Item name="address" label="Endereço IP" rules={[{ required: true }]}>
          <Input />
        </Form.Item>
        
        <Form.Item name="port" label="Porta" rules={[{ required: true }]}>
          <InputNumber min={1} max={65535} />
        </Form.Item>
        
        <Form.Item name="node" label="Nó do Consul" rules={[{ required: true }]}>
          <NodeSelector />
        </Form.Item>
        
        {/* Campos customizados do exporter_type (do form_schema) */}
        {exporterFields.map(field => (
          <Form.Item
            key={field.name}
            name={field.name}
            label={field.label}
            rules={field.required ? [{ required: true, message: `${field.label} é obrigatório` }] : []}
            tooltip={field.help}
            initialValue={field.default}
          >
            {field.type === 'select' ? (
              <Select placeholder={`Selecione ${field.label}`}>
                {field.options?.map(opt => (
                  <Select.Option key={opt} value={opt}>{opt}</Select.Option>
                ))}
              </Select>
            ) : (
              <Input placeholder={field.help} />
            )}
          </Form.Item>
        ))}
        
        {/* Metadata dinâmico (campos genéricos) */}
        {filterFields.map(field => (
          <Form.Item
            key={field.name}
            name={field.name}
            label={field.display_name}
            rules={field.required ? [{ required: true }] : []}
          >
            {field.type === 'select' ? (
              <Select>
                {field.options?.map(opt => (
                  <Select.Option key={opt} value={opt}>{opt}</Select.Option>
                ))}
              </Select>
            ) : (
              <Input />
            )}
          </Form.Item>
        ))}
      </Form>
    </Modal>
  );
};
```

---

#### 2.2. Integração no DynamicMonitoringPage

**Adicionar botões e modais (usando componentes novos):**
```typescript
// frontend/src/pages/DynamicMonitoringPage.tsx

const DynamicMonitoringPage: React.FC<DynamicMonitoringPageProps> = ({ category }) => {
  const [createModalVisible, setCreateModalVisible] = useState(false);
  const [editModalVisible, setEditModalVisible] = useState(false);
  const [selectedService, setSelectedService] = useState<MonitoringDataItem | null>(null);
  
  // Hook compartilhado para DELETE (reutilizar de Services.tsx)
  const { deleteResource, deleteBatch } = useConsulDelete({
    deleteFn: async (payload: any) => {
      return consulAPI.deleteService(payload.service_id, {
        node_addr: payload.node_addr
      });
    },
    successMessage: 'Serviço removido com sucesso',
    errorMessage: 'Falha ao remover serviço',
    onSuccess: () => {
      actionRef.current?.reload();
    },
  });
  
  const handleCreate = () => {
    setCreateModalVisible(true);
  };
  
  const handleEdit = (service: MonitoringDataItem) => {
    setSelectedService(service);
    setEditModalVisible(true);
  };
  
  const handleDelete = async (service: MonitoringDataItem) => {
    await deleteResource({
      service_id: service.ID,
      node_addr: service.node_ip || service.Node
    });
  };
  
  return (
    <PageContainer>
      {/* Botão Criar */}
      <Button
        type="primary"
        icon={<PlusOutlined />}
        onClick={handleCreate}
      >
        Criar Serviço
      </Button>
      
      {/* Tabela com ações (adicionar coluna de ações) */}
      <ProTable
        // ... configurações existentes ...
        columns={[
          // ... colunas existentes ...
          {
            title: 'Ações',
            key: 'actions',
            width: 150,
            fixed: 'right',
            render: (_: any, record: MonitoringDataItem) => (
              <Space>
                <Button
                  type="link"
                  icon={<EditOutlined />}
                  onClick={() => handleEdit(record)}
                >
                  Editar
                </Button>
                <Popconfirm
                  title="Deseja realmente excluir este serviço?"
                  onConfirm={() => handleDelete(record)}
                >
                  <Button
                    type="link"
                    danger
                    icon={<DeleteOutlined />}
                  >
                    Excluir
                  </Button>
                </Popconfirm>
              </Space>
            )
          }
        ]}
      />
      
      {/* Modais (componentes novos) */}
      <MonitoringServiceFormModal
        mode="create"
        category={category}
        visible={createModalVisible}
        onSuccess={() => {
          setCreateModalVisible(false);
          actionRef.current?.reload();
        }}
        onCancel={() => setCreateModalVisible(false)}
      />
      
      <MonitoringServiceFormModal
        mode="edit"
        category={category}
        service={selectedService}
        visible={editModalVisible}
        onSuccess={() => {
          setEditModalVisible(false);
          setSelectedService(null);
          actionRef.current?.reload();
        }}
        onCancel={() => {
          setEditModalVisible(false);
          setSelectedService(null);
        }}
      />
    </PageContainer>
  );
};
```

---

## 📊 Resumo da Arquitetura Proposta

### Fluxo Completo CRUD

```
┌─────────────────────────────────────────────────────────────┐
│              FRONTEND: DynamicMonitoringPage                │
│                                                              │
│  Ações:                                                      │
│    ✅ Criar → Modal → POST /monitoring/services            │
│    ✅ Editar → Modal → PATCH /monitoring/services/{id}     │
│    ✅ Excluir → Popconfirm → DELETE /monitoring/services/{id} │
│    ✅ Batch Delete → Modal → DELETE /monitoring/services/batch │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       │ HTTP Requests
                       ▼
┌─────────────────────────────────────────────────────────────┐
│              BACKEND: monitoring_unified.py                │
│                                                              │
│  Endpoints:                                                  │
│    POST /monitoring/services                                │
│    PATCH /monitoring/services/{id}                         │
│    DELETE /monitoring/services/{id}                         │
│    DELETE /monitoring/services/batch                         │
│                                                              │
│  Validações:                                                 │
│    1. Verificar tipo em monitoring-types                    │
│    2. Validar metadata obrigatórios                         │
│    3. Registrar/Atualizar/Remover no Consul                │
│    4. Invalidar cache                                        │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       │ Consul Agent API
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                    CONSUL (Service Discovery)                │
│                                                              │
│  Operações:                                                  │
│    PUT /v1/agent/service/register     (CREATE)             │
│    PUT /v1/agent/service/deregister    (DELETE)             │
│    GET /v1/catalog/service/{service}   (READ)               │
│                                                              │
│  Resultado:                                                   │
│    Serviço registrado/atualizado/removido                   │
│    Prometheus descobre automaticamente                      │
└─────────────────────────────────────────────────────────────┘
```

---

## ✅ Checklist de Implementação

### Backend
- [x] Endpoint `POST /api/v1/services` já existe (reutilizar)
- [x] Endpoint `PUT /api/v1/services/{service_id}` já existe (reutilizar)
- [x] Endpoint `DELETE /api/v1/services/{service_id}` já existe (reutilizar)
- [x] Endpoint `DELETE /api/v1/services/bulk/deregister` já existe (reutilizar)
- [ ] **NOVO:** Criar endpoint `GET /api/v1/monitoring/form-schema/{exporter_type}`
- [ ] Estender `categorization/rules` com `form_schema` (via `monitoring/rules` UI)
- [ ] Implementar validação de tipos (monitoring-types)
- [ ] Implementar validação de metadata obrigatórios
- [ ] Implementar integração com Consul Agent API
- [ ] Implementar invalidação de cache
- [ ] Adicionar testes unitários
- [ ] Adicionar testes de integração

### Frontend
- [ ] Criar componente `ServiceFormModal.tsx`
- [ ] Criar componente `BatchDeleteModal.tsx`
- [ ] Integrar modais no `DynamicMonitoringPage`
- [ ] Adicionar botão "Criar Serviço"
- [ ] Adicionar ações "Editar" e "Excluir" na tabela
- [ ] Implementar batch delete (seleção múltipla)
- [ ] Adicionar validação de formulários
- [ ] Adicionar feedback visual (success/error)
- [ ] Adicionar loading states
- [ ] Testar fluxo completo

### Integração
- [ ] Testar criação de serviço
- [ ] Testar edição de metadata
- [ ] Testar exclusão de serviço
- [ ] Testar batch delete
- [ ] Validar sincronização com Consul
- [ ] Validar cache invalidation
- [ ] Validar que Prometheus descobre novos serviços

### Documentação
- [ ] Atualizar README com endpoints CRUD
- [ ] Documentar fluxo de criação
- [ ] Documentar validações
- [ ] Adicionar exemplos de uso
- [ ] Atualizar diagramas de arquitetura

---

## 🎯 Próximos Passos

1. **Revisar esta análise** com o time
2. **Aprovar arquitetura proposta** (especialmente extensão de `categorization/rules`)
3. **Priorizar funcionalidades:**
   - Fase 1: Estender `categorization/rules` com `form_schema`
   - Fase 2: Criar endpoint `GET /monitoring/form-schema/{exporter_type}`
   - Fase 3: Criar componente `MonitoringServiceFormModal.tsx`
   - Fase 4: Integrar CRUD no `DynamicMonitoringPage`
4. **Migrar campos de JSONs estáticos** para `categorization/rules`
5. **Implementar frontend** (backend já está pronto)
6. **Testes completos** antes de deploy

---

## 📝 Notas Importantes

### ✅ O que JÁ existe e pode ser reutilizado:
- Backend CRUD completo (`backend/api/services.py`)
- `ConsulManager` com métodos funcionais
- `Services.tsx` como referência (não misturar código)
- `useConsulDelete` hook compartilhado
- `FormFieldRenderer` para metadata fields
- `NodeSelector`, `ColumnSelector` componentes compartilhados

### ⚠️ O que NÃO fazer:
- ❌ Não misturar código de `Services.tsx` com `DynamicMonitoringPage`
- ❌ Não usar JSONs estáticos (`backend/schemas/monitoring-types/`)
- ❌ Não hardcodar campos por exporter_type
- ❌ Não criar componentes duplicados

### ✅ O que fazer:
- ✅ Criar componentes novos baseados nos antigos
- ✅ Usar `categorization/rules` como fonte única de verdade
- ✅ Manter 100% dinâmico
- ✅ Reutilizar hooks e componentes compartilhados

---

**Documento criado em:** 2025-11-17  
**Última atualização:** 2025-11-17 (Revisão completa)  
**Status:** ✅ Análise Completa e Corrigida - Aguardando Aprovação

