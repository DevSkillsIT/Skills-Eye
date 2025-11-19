# 📊 Análise Completa: Arquitetura CRUD para Páginas Monitoring/*

**Data:** 2025-11-17  
**Autores:** Análise Profissional (Cursor) + Claude Code (Sonnet 4.5) - Documento Unificado  
**Versão:** 2.0 - Análise Completa e Detalhada  
**Status:** ✅ Análise Completa - Pronto para Implementação

---

## 📝 Nota sobre este Documento

Este documento unifica as análises realizadas por duas IAs independentes:
- **Análise Cursor (Auto):** Foco em arquitetura, diagramas e estrutura
- **Análise Claude Code:** Foco em código detalhado, exemplos práticos e roadmap

**Objetivo:** Criar um documento único e completo que sirva como base definitiva para implementação do CRUD dinâmico nas páginas `monitoring/*`.

**⚠️ ATUALIZAÇÃO CRÍTICA (2025-11-17):**
Este documento foi atualizado com base em feedback do usuário e análise detalhada do código atual. Principais mudanças:
- **Seleção de nó Consul primeiro** no fluxo de criação
- **Cache KV para monitoring-types** (similar ao metadata-fields)
- **Geração de ID 100% dinâmica** baseada em campos obrigatórios do KV
- **Verificação de hardcodes** nos endpoints existentes
- **Correções necessárias** antes de implementar novos endpoints

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

5. **⚠️ CRÍTICO: Monitoring-types precisa de cache KV + prewarm (PRIORIDADE #1)**
   - **Problema atual:** `monitoring-types-dynamic/from-prometheus` sempre faz SSH
   - **Problema:** Tipos variam por servidor Prometheus (Palmas pode ter HTTP_2xx, Rio pode não ter)
   - **Solução:** Implementar cache KV seguindo padrão existente (`metadata-fields`, `metadata/sites`):
     - **KV único:** `skills/eye/monitoring-types` (NÃO separado por nó, igual `metadata/fields`)
     - **Prewarm no startup:** Extrai tipos de TODOS os servidores Prometheus e salva no KV
     - **Menos resiliente:** Não precisa backup/restore (é só cópia do prometheus.yml)
     - **Frontend pode forçar refresh:** Botão "Atualizar" na página monitoring-types
     - **Fallback rígido:** Se KV vazio, extrai do Prometheus + salva no KV (com mensagem clara no frontend)
   - **⚠️ BLOQUEADOR:** Sem este KV implementado, não é possível avançar com CRUD

6. **⚠️ CRÍTICO: Hardcodes encontrados no backend CRUD**
   - **`validate_service_data()`:** Usa `Config.REQUIRED_FIELDS` (hardcoded)
   - **`check_duplicate_service()`:** Valida `module, company, project, env, name` (hardcoded)
   - **`create_service()`:** Gera ID baseado em `module/company/project/env@name` (hardcoded)
   - **Solução:** Tornar tudo dinâmico baseado em `metadata-fields` KV:
     - Campos obrigatórios vêm do KV (`required: true`)
     - Validação de duplicatas usa campos obrigatórios do KV
     - Geração de ID usa campos obrigatórios do KV (ordem do KV)

7. **⚠️ CRÍTICO: Geração de ID deve ser 100% dinâmica**
   - **Problema atual:** ID usa `module/company/project/env@name` (hardcoded)
   - **Realidade Consul:** ID usa `module/company/grupo_monitoramento/tipo_monitoramento@name`
   - **Solução:** ID = todos os campos obrigatórios (ordem do KV) + `@name`
   - **Exemplo:** Se obrigatórios são `["module", "company", "grupo_monitoramento", "tipo_monitoramento"]`
     - ID: `icmp/Agro Xingu/Servidores/Status_Server@AX_DTC_AXMTGVM001-SISTEMA`

8. **Componentes compartilhados identificados**
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

#### 7.2. Solução Proposta: Estender `categorization/rules` com `form_schema` Completo

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

#### 7.3. Estrutura JSON Completa do `form_schema` (Exemplos Detalhados)

**Exemplo 1: Blackbox Exporter (ICMP)**
```json
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
          { "value": "tcp_connect", "label": "TCP Connect" },
          { "value": "http_2xx", "label": "HTTP 2xx" },
          { "value": "dns", "label": "DNS" }
        ],
        "help": "Módulo definido no blackbox.yml"
      }
    ]
  }
}
```

**Exemplo 2: SNMP Exporter (Switch)**
```json
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
}
```

**Exemplo 3: Windows Exporter**
```json
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
```

**Tipos de Campo Suportados:**
- `text` - Campo de texto simples
- `number` - Campo numérico
- `select` - Dropdown com opções
- `password` - Campo de senha (oculto)
- `textarea` - Área de texto multilinha

**Validações Suportadas:**
- `ipv4` - Validação de IPv4
- `ip_or_hostname` - IP ou hostname válido
- `url` - URL válida
- `hostname` - Hostname válido

---

### 8. Documentações Técnicas Estudadas

**⚠️ IMPORTANTE:** Ao reutilizar componentes e funções existentes de editar, deletar, criar, será necessário buscar mais informações na **documentação oficial da API do Consul**:
- **Fonte:** https://developer.hashicorp.com/consul/api-docs
- **Endpoints relevantes:** 
  - `/v1/agent/service/register` - Registrar serviço
  - `/v1/agent/service/deregister/{id}` - Remover serviço
  - `/v1/catalog/service/{name}` - Buscar serviço
  - `/v1/agent/service/{id}` - Atualizar serviço

#### 8.1. Consul (Service Discovery)

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

### Fluxo Completo: Criar Novo Serviço (Passo a Passo)

**⚠️ ATUALIZAÇÃO CRÍTICA (2025-11-17):** Este fluxo foi revisado com base em feedback do usuário e análise do código atual. Principais mudanças:

1. **Seleção de nó Consul primeiro** - Tipos disponíveis variam por servidor Prometheus
2. **Cache KV para monitoring-types** - KV único (`skills/eye/monitoring-types`), não separado por nó (igual `metadata-fields`)
3. **ID dinâmico baseado em campos obrigatórios** - Não mais hardcoded
4. **Validação dinâmica** - Campos obrigatórios vêm do KV metadata-fields
5. **Tooltips e informações relevantes** - Máximo de informações no frontend
6. **Fallbacks rígidos com mensagens claras** - Frontend intuitivo e moderno
7. **Metadata fields controlam visibilidade** - Campos aparecem/ocultam baseado em `show_in_*` configurado em `metadata-fields`

```
┌─────────────────────────────────────────────────────────────────┐
│  PASSO 1: Usuário clica "Criar Novo" em DynamicMonitoringPage  │
│  (Ex: category=network-probes)                                  │
└──────────────────────┬──────────────────────────────────────────┘
                       │
                       │ Abre modal
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│  PASSO 1.5: Selecionar Nó Consul (OBRIGATÓRIO PRIMEIRO)        │
│  ┌──────────────────────────────────────────────────────┐     │
│  │ Nó Consul: [Palmas (172.16.1.26) ▼          ]       │     │
│  └──────────────────────────────────────────────────────┘     │
│                                                                  │
│  ⚠️ IMPORTANTE: Tipos disponíveis variam por servidor Prometheus!│
│  - Palmas pode ter HTTP_2xx                                     │
│  - Rio pode NÃO ter HTTP_2xx                                    │
│  - Tipos vêm do KV cache único (skills/eye/monitoring-types)   │
│  - KV contém tipos de TODOS os servidores (agregado)            │
└──────────────────────┬──────────────────────────────────────────┘
                       │
                       │ Nó selecionado
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│  PASSO 2: DynamicCRUDModal carrega tipos disponíveis            │
│  GET /api/v1/monitoring-types-dynamic/from-prometheus?category=network│
│                                                                  │
│  ⚠️ MUDANÇA: Busca do KV cache (não mais SSH direto)            │
│  - KV: skills/eye/monitoring-types (único, não separado por nó) │
│  - Se vazio: força extração do Prometheus + salva no KV          │
│  - Frontend pode forçar refresh (botão "Atualizar")             │
│  - Mensagens claras no frontend se falhar                        │
│                                                                  │
│  Retorna (do KV cache):                                         │
│  - blackbox-icmp (ICMP Ping)                                    │
│  - blackbox-tcp (TCP Connect)                                   │
│  - blackbox-http (HTTP)                                         │
│  - blackbox-https (HTTPS)                                       │
└──────────────────────┬──────────────────────────────────────────┘
                       │
                       │ Usuário seleciona tipo
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│  PASSO 3: Buscar form_schema do tipo selecionado                │
│  GET /api/v1/monitoring-types/form-schema?                     │
│    exporter_type=blackbox&                                      │
│    job_name=blackbox-icmp&                                      │
│    node=172.16.1.26                                             │
│                                                                  │
│  ⚠️ MUDANÇA: form_schema vem de categorization/rules             │
│  KV: skills/eye/monitoring-types/categorization/rules          │
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
│    │ Grupo:     [Monitora_VPN ▼     ]                     │     │
│    │ Tipo:      [VPN_Link_Ativo ▼  ]                     │     │
│    └──────────────────────────────────────────────────────┘     │
│                                                                  │
│  ⚠️ Campos obrigatórios vêm do KV metadata-fields               │
│  - Se "required": true → campo obrigatório                      │
│  - Se "required": false → campo opcional                        │
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
│  - Campos obrigatórios (do KV metadata-fields): Validados?       │
│  - name: Sempre obrigatório (não pode ser vazio)                │
└──────────────────────┬──────────────────────────────────────────┘
                       │
                       │ POST para backend
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│  PASSO 6: Backend - POST /api/v1/services                       │
│  {                                                               │
│    "name": "Gateway Principal",     // Campo obrigatório         │
│    "service": "blackbox_exporter",   // Do exporter_type         │
│    "address": "",                    // Vazio (Consul resolve)   │
│    "port": 9115,                     // Padrão blackbox          │
│    "node_addr": "172.16.1.26",      // Nó selecionado           │
│    "meta": {                                                     │
│      "module": "icmp",                                           │
│      "target": "192.168.1.1",        // Campo específico        │
│      "company": "Ramada",                                        │
│      "site": "palmas",                                           │
│      "env": "prod",                                              │
│      "name": "Gateway Principal",                                │
│      "grupo_monitoramento": "Monitora_VPN",                      │
│      "tipo_monitoramento": "VPN_Link_Ativo"                      │
│    },                                                            │
│    "tags": ["icmp", "network", "prod"]                           │
│  }                                                               │
│                                                                  │
│  ⚠️ MUDANÇA: ID será gerado dinamicamente                        │
│  - Buscar campos obrigatórios do KV metadata-fields             │
│  - Ordem: module + campos obrigatórios (ordem do KV) + @name     │
│  - Exemplo: icmp/Ramada/Monitora_VPN/VPN_Link_Ativo@Gateway... │
└──────────────────────┬──────────────────────────────────────────┘
                       │
                       │ ConsulManager.register_service()
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│  PASSO 7: Geração de ID Dinâmico                                 │
│                                                                  │
│  ⚠️ NOVO: ID baseado em campos obrigatórios do KV               │
│                                                                  │
│  1. Buscar campos obrigatórios do KV:                            │
│     GET /api/v1/metadata-fields → filtrar required=true         │
│                                                                  │
│  2. Ordenar campos obrigatórios (ordem do KV)                   │
│     Ex: ["module", "company", "grupo_monitoramento",            │
│          "tipo_monitoramento"]                                   │
│                                                                  │
│  3. Montar ID:                                                   │
│     parts = [meta[field] for field in required_fields]          │
│     service_id = "/".join(parts) + "@" + meta["name"]            │
│                                                                  │
│  4. Sanitizar ID:                                                │
│     ConsulManager.sanitize_service_id(service_id)                │
│                                                                  │
│  Exemplo:                                                        │
│  - Campos obrigatórios: module, company, grupo_monitoramento,    │
│    tipo_monitoramento                                            │
│  - Meta: {                                                       │
│      module: "icmp",                                             │
│      company: "Agro Xingu",                                      │
│      grupo_monitoramento: "Servidores",                          │
│      tipo_monitoramento: "Status_Server",                         │
│      name: "AX_DTC_AXMTGVM001-SISTEMA"                          │
│    }                                                             │
│  - ID gerado:                                                    │
│    "icmp/Agro Xingu/Servidores/Status_Server@AX_DTC_AXMTGVM001-SISTEMA"│
│                                                                  │
│  ⚠️ Isso corresponde ao formato real do Consul!                 │
└──────────────────────┬──────────────────────────────────────────┘
                       │
                       │ ID gerado
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│  PASSO 8: Registro no Consul                                    │
│  PUT /v1/agent/service/register                                  │
│                                                                  │
│  Serviço aparece imediatamente em:                               │
│  - DynamicMonitoringPage (após refresh)                          │
│  - Prometheus (após próximo scrape)                              │
│  - Grafana (após dados chegarem)                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

### ⚠️ Fase 0: Verificação e Correção de Hardcodes (CRÍTICO)

**ANTES de implementar novos endpoints, é necessário corrigir hardcodes nos endpoints existentes:**

#### 0.1. Endpoints Existentes que Precisam de Ajuste

**Arquivo:** `backend/api/services.py`

**1. `POST /api/v1/services` (linha 344)**
- ❌ **Hardcode:** Valida `module, company, project, env, name` (linha 385-391)
- ❌ **Hardcode:** `check_duplicate_service()` usa campos hardcoded
- ✅ **Correção:** Buscar campos obrigatórios do KV `metadata-fields`
- ✅ **Correção:** Usar `Config.get_required_fields()` (já dinâmico, mas precisa garantir uso)

**2. `PUT /api/v1/services/{service_id}` (linha 519)**
- ⚠️ **Verificar:** Se usa validação hardcoded
- ✅ **Correção:** Mesma lógica do POST

**3. `DELETE /api/v1/services/{service_id}` (linha 681)**
- ✅ **OK:** Não precisa de ajuste (apenas deleta)

**4. `DELETE /api/v1/services/bulk/deregister` (linha 640)**
- ✅ **OK:** Não precisa de ajuste (apenas deleta)

#### 0.2. Funções do ConsulManager que Precisam de Ajuste

**Arquivo:** `backend/core/consul_manager.py`

**1. `validate_service_data()` (linha 1349)**
- ❌ **Hardcode:** Usa `Config.REQUIRED_FIELDS` (linha 1367)
- ✅ **Correção:** Buscar campos obrigatórios do KV `metadata-fields` dinamicamente
- ✅ **Correção:** Usar `Config.get_required_fields()` (já existe, mas precisa garantir uso)

**2. `check_duplicate_service()` (linha 819)**
- ❌ **Hardcode:** Valida `module, company, project, env, name` (linha 855-859)
- ✅ **Correção:** Buscar campos obrigatórios do KV e usar para validação
- ✅ **Correção:** Tornar função genérica baseada em campos obrigatórios

**3. Geração de ID (não existe função dedicada)**
- ❌ **Hardcode:** `BlackboxManager._compose_service_id()` usa `module/company/project/env@name`
- ✅ **Correção:** Criar função `generate_dynamic_service_id()` em `ConsulManager`:
  ```python
  async def generate_dynamic_service_id(self, meta: Dict[str, Any]) -> str:
      """
      Gera ID dinamicamente baseado em campos obrigatórios do KV metadata-fields
      
      Ordem: campos obrigatórios (ordem do KV) + @name
      """
      # 1. Buscar campos obrigatórios do KV
      required_fields = Config.get_required_fields()
      
      # 2. Montar partes do ID (ordem do KV)
      parts = []
      for field in required_fields:
          if field in meta and meta[field]:
              parts.append(str(meta[field]))
      
      # 3. Adicionar name (sempre obrigatório)
      if 'name' not in meta or not meta['name']:
          raise ValueError("Campo 'name' é obrigatório para gerar ID")
      
      # 4. Montar ID: parts + @name
      raw_id = "/".join(parts) + "@" + meta['name']
      
      # 5. Sanitizar
      return self.sanitize_service_id(raw_id)
  ```

#### 0.3. Implementação de Cache KV para Monitoring-Types (PRIORIDADE #1 - BLOQUEADOR)

**⚠️ CRÍTICO:** Esta implementação é **BLOQUEADORA** para avançar com CRUD. Deve ser feita PRIMEIRO.

**Arquivo:** `backend/api/monitoring_types_dynamic.py`

**Padrão a seguir:** Igual `metadata-fields` e `metadata/sites` (KV único, não separado por nó)

**Problema atual:**
- ❌ Sempre faz SSH para extrair tipos do Prometheus
- ❌ Não cacheia em KV
- ❌ Tipos variam por servidor Prometheus (Palmas pode ter HTTP_2xx, Rio pode não ter)

**Solução (seguindo padrão existente):**

1. **KV único:** `skills/eye/monitoring-types` (igual `skills/eye/metadata/fields`)
   ```json
   {
     "version": "1.0.0",
     "last_updated": "2025-11-17T10:00:00",
     "source": "prewarm_startup",
     "total_types": 45,
     "servers": {
       "172.16.1.26": {
         "types": [...],
         "total": 20
       },
       "172.16.200.14": {
         "types": [...],
         "total": 25
       }
     },
     "all_types": [...],  // União de todos os tipos (sem duplicatas)
     "categories": {...}  // Agrupado por categoria
   }
   ```

2. **Endpoint com cache KV (seguindo padrão `metadata-fields`):**
   ```python
   @router.get("/from-prometheus")
   async def get_types_from_prometheus(
       server: Optional[str] = Query(None, description="Filtrar por servidor"),
       force_refresh: bool = Query(False, description="Forçar re-extração via SSH")
   ):
       """
       Extrai tipos de monitoramento com cache KV
       
       Fluxo (igual metadata-fields):
       1. Se force_refresh=False: Buscar do KV primeiro (skills/eye/monitoring-types)
       2. Se KV vazio OU force_refresh=True: Extrair do Prometheus + salvar no KV
       3. Retornar dados do KV (rápido) ou recém-extraídos
       
       ⚠️ DIFERENÇA vs metadata-fields:
       - Não precisa backup/restore (é só cópia do prometheus.yml)
       - Se não tem no Prometheus, não tem no KV (simples)
       - Menos resiliente (não é editável via frontend)
       """
       # 1. Tentar ler do KV primeiro (se não forçar refresh)
       if not force_refresh:
           kv_data = await kv_manager.get_json('skills/eye/monitoring-types')
           if kv_data and kv_data.get('all_types'):
               logger.info(f"[MONITORING-TYPES] Retornando {len(kv_data['all_types'])} tipos do KV (cache)")
               return {
                   "success": True,
                   "from_cache": True,
                   "categories": kv_data.get('categories', {}),
                   "all_types": kv_data.get('all_types', []),
                   "servers": kv_data.get('servers', {}),
                   "last_updated": kv_data.get('last_updated')
               }
       
       # 2. KV vazio ou force_refresh: Extrair do Prometheus
       logger.info("[MONITORING-TYPES] Extraindo tipos do Prometheus via SSH...")
       # ... código de extração existente ...
       
       # 3. Salvar no KV (sobrescrever - não precisa merge como metadata-fields)
       await kv_manager.put_json(
           key='skills/eye/monitoring-types',
           value={
               'version': '1.0.0',
               'last_updated': datetime.now().isoformat(),
               'source': 'force_refresh' if force_refresh else 'fallback_empty_kv',
               'total_types': len(all_types),
               'servers': result_servers,
               'all_types': all_types,
               'categories': categories
           }
       )
       
       return {
           "success": True,
           "from_cache": False,
           "categories": categories,
           "all_types": all_types,
           "servers": result_servers
       }
   ```

3. **Prewarm no startup (similar ao `_prewarm_metadata_fields_cache`):**
   ```python
   # backend/app.py
   async def _prewarm_monitoring_types_cache():
       """
       Prewarm cache de monitoring-types
       
       ⚠️ DIFERENÇA vs metadata-fields:
       - Não precisa verificar se KV já tem dados (sempre sobrescreve)
       - Não precisa merge (é só cópia do prometheus.yml)
       - Não precisa backup (não é editável)
       
       FLUXO:
       1. Aguardar servidor inicializar (1-2s)
       2. Extrair tipos de TODOS os servidores Prometheus via SSH
       3. Salvar no KV: skills/eye/monitoring-types
       4. Tipos ficam disponíveis instantaneamente
       """
       global _prewarm_status
       _prewarm_status['monitoring_types'] = {'running': True}
       
       try:
           # Aguardar servidor inicializar
           await asyncio.sleep(2)
           
           logger.info("[PRE-WARM] Iniciando prewarm de monitoring-types...")
           
           # Extrair tipos de TODOS os servidores
           from api.monitoring_types_dynamic import extract_types_from_all_servers
           result = await extract_types_from_all_servers()
           
           # Salvar no KV (sempre sobrescreve - não precisa verificar existência)
           await kv_manager.put_json(
               key='skills/eye/monitoring-types',
               value={
                   'version': '1.0.0',
                   'last_updated': datetime.now().isoformat(),
                   'source': 'prewarm_startup',
                   'total_types': len(result['all_types']),
                   'servers': result['servers'],
                   'all_types': result['all_types'],
                   'categories': result['categories']
               }
           )
           
           logger.info(f"[PRE-WARM] ✓ Monitoring-types cache populado: {len(result['all_types'])} tipos")
           _prewarm_status['monitoring_types'] = {'completed': True, 'running': False}
           
       except Exception as e:
           logger.error(f"[PRE-WARM] ❌ Erro ao prewarm monitoring-types: {e}", exc_info=True)
           _prewarm_status['monitoring_types'] = {'failed': True, 'error': str(e), 'running': False}
   ```

4. **Frontend pode forçar refresh:**
   ```typescript
   // Botão "Atualizar" na página monitoring-types
   const handleForceRefresh = async () => {
     setLoading(true);
     try {
       const response = await axios.get('/api/v1/monitoring-types-dynamic/from-prometheus', {
         params: { force_refresh: true }
       });
       message.success('Tipos atualizados com sucesso!');
       // Recarregar dados
       loadTypes();
     } catch (error) {
       message.error('Erro ao atualizar tipos. Verifique logs do backend.');
     } finally {
       setLoading(false);
     }
   };
   ```

5. **Fallback rígido com mensagem clara no frontend:**
   ```typescript
   // Se KV vazio e extração falhar
   if (!data.success && data.error === 'KV_EMPTY_AND_EXTRACTION_FAILED') {
     // Mostrar mensagem clara
     notification.error({
       message: 'Tipos de Monitoramento Indisponíveis',
       description: 'Não foi possível carregar tipos do Prometheus. Verifique: 1) Conexão SSH com servidores, 2) Arquivo prometheus.yml existe, 3) Logs do backend.',
       duration: 10
     });
   }
   ```

---

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

#### 2.0. Sistema de Auto-Cadastro (CRÍTICO - Já Implementado)

**⚠️ IMPORTANTE:** O sistema de auto-cadastro já está implementado e funcionando em `Services.tsx`. Deve ser **reutilizado** no CRUD dinâmico.

**Como Funciona:**

1. **Configuração em `metadata-fields`:**
   - Cada campo tem propriedade `available_for_registration` (boolean)
   - Se `true`, campo aparece na página `ReferenceValues` e suporta auto-cadastro
   - Valores pré-cadastrados aparecem como opções no formulário

2. **Componente `FormFieldRenderer`:**
   - Se `field.available_for_registration === true` E `field.field_type === 'string'` → Usa `ReferenceValueInput`
   - Caso contrário → Usa componentes padrão (ProFormText, ProFormSelect, etc)

3. **Componente `ReferenceValueInput`:**
   ```typescript
   // frontend/src/components/ReferenceValueInput.tsx
   
   // Carrega valores existentes do backend
   const { values, ensureValue } = useReferenceValues({ fieldName: 'cidade' });
   
   // Mostra autocomplete com valores existentes
   <AutoComplete
     value={internalValue}
     options={values.map(v => ({ value: v, label: v }))}
     onChange={handleChange}
     notFoundContent={
       <div>
         <PlusOutlined />
         Digite para criar novo valor
       </div>
     }
   />
   
   // ⚡ INDICADOR VISUAL: Tag verde quando valor novo é digitado
   {internalValue && !values.includes(internalValue) && (
     <Tag color="green" icon={<PlusOutlined />}>
       Novo valor será criado: "{internalValue}"
     </Tag>
   )}
   ```

4. **Auto-cadastro no `handleSubmit` (Services.tsx):**
   ```typescript
   // frontend/src/pages/Services.tsx (linhas 790-832)
   
   const handleSubmit = async (values: ServiceFormValues) => {
     // PASSO 1: AUTO-CADASTRO DE VALORES (Retroalimentação)
     
     // 1A) Auto-cadastrar TAGS (se houver)
     if (values.tags && values.tags.length > 0) {
       await ensureTags(values.tags);
     }
     
     // 1B) Auto-cadastrar METADATA FIELDS (campos com available_for_registration=true)
     const metadataValues: Array<{ fieldName: string; value: string }> = [];
     
     formFields.forEach((field) => {
       if (field.available_for_registration) {  // ← Verifica flag
         const fieldValue = (values as any)[field.name];
         
         if (fieldValue && typeof fieldValue === 'string' && fieldValue.trim()) {
           metadataValues.push({
             fieldName: field.name,
             value: fieldValue.trim()
           });
         }
       }
     });
     
     // Executar batch ensure (cadastra todos de uma vez)
     if (metadataValues.length > 0) {
       await batchEnsure(metadataValues);  // ← POST /reference-values/batch-ensure
     }
     
     // PASSO 2: SALVAR SERVIÇO (após auto-cadastro)
     await consulAPI.createService(payload);
   };
   ```

5. **Hook `useBatchEnsure`:**
   ```typescript
   // frontend/src/hooks/useReferenceValues.ts
   
   export function useBatchEnsure() {
     const batchEnsure = useCallback(
       async (values: Array<{ fieldName: string; value: string }>) => {
         const response = await axios.post(
           `${API_URL}/reference-values/batch-ensure`,
           values.map(v => ({
             field_name: v.fieldName,
             value: v.value
           }))
         );
         return response.data;
       },
       []
     );
     return { batchEnsure };
   }
   ```

**Fluxo Completo de Auto-Cadastro:**

```
┌─────────────────────────────────────────────────────────────────┐
│  1. USUÁRIO ABRE FORMULÁRIO                                     │
│     Campo "Cidade" tem available_for_registration=true          │
│     FormFieldRenderer detecta → Usa ReferenceValueInput         │
└──────────────────────┬──────────────────────────────────────────┘
                       │
                       │ Carrega valores existentes
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│  2. ReferenceValueInput carrega valores do backend              │
│     GET /api/v1/reference-values/cidade                        │
│     Retorna: ["Palmas", "Rio de Janeiro", "São Paulo", ...]    │
└──────────────────────┬──────────────────────────────────────────┘
                       │
                       │ Usuário digita valor novo
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│  3. USUÁRIO DIGITA "Balsas" (valor novo)                       │
│     AutoComplete mostra: "Digite para criar novo valor"         │
│     Tag verde aparece: "Novo valor será criado: Balsas"        │
└──────────────────────┬──────────────────────────────────────────┘
                       │
                       │ Usuário clica "Salvar"
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│  4. handleSubmit executa                                        │
│     a) batchEnsure([{ fieldName: "cidade", value: "Balsas" }]) │
│     b) POST /reference-values/batch-ensure                     │
│     c) Backend normaliza e cadastra "Balsas"                   │
│     d) Depois salva serviço no Consul                          │
└──────────────────────┬──────────────────────────────────────────┘
                       │
                       │ Próximo formulário
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│  5. PRÓXIMO FORMULÁRIO                                          │
│     Campo "Cidade" agora mostra:                               │
│     ["Palmas", "Rio", "São Paulo", "Balsas" ← NOVO!]          │
│     "Balsas" aparece na página ReferenceValues                 │
└─────────────────────────────────────────────────────────────────┘
```

**Exemplo Real (Campo "Cidade"):**

1. **Estado Inicial:**
   - Campo "Cidade" tem `available_for_registration: true`
   - Valores cadastrados: `["Palmas", "Rio de Janeiro", "São Paulo"]`
   - Usuário vê dropdown com essas 3 opções

2. **Usuário Digita Valor Novo:**
   - Usuário digita "Balsas" (não está na lista)
   - `ReferenceValueInput` detecta que valor não existe
   - Mostra tag verde: **"Novo valor será criado: Balsas"**

3. **Ao Salvar Formulário:**
   - `handleSubmit` detecta que "cidade" tem `available_for_registration: true`
   - Chama `batchEnsure([{ fieldName: "cidade", value: "Balsas" }])`
   - Backend cadastra "Balsas" em `reference-values`
   - Serviço é salvo no Consul

4. **Próximo Uso:**
   - Campo "Cidade" agora mostra: `["Palmas", "Rio", "São Paulo", "Balsas"]`
   - "Balsas" aparece na página `ReferenceValues` (aba "Cidade")

**Integração no CRUD Dinâmico:**

O `DynamicCRUDModal` deve seguir **exatamente o mesmo padrão**:

```typescript
// frontend/src/components/MonitoringServiceFormModal.tsx

import { useBatchEnsure } from '../hooks/useReferenceValues';
import FormFieldRenderer from './FormFieldRenderer';

const MonitoringServiceFormModal: React.FC<Props> = ({ ... }) => {
  const { batchEnsure } = useBatchEnsure();
  const { formFields } = useFormFields(category);
  
  const handleSubmit = async (values: any) => {
    // PASSO 1: AUTO-CADASTRO (igual Services.tsx)
    const metadataValues: Array<{ fieldName: string; value: string }> = [];
    
    formFields.forEach((field) => {
      if (field.available_for_registration) {  // ← Verifica flag
        const fieldValue = values[field.name];
        if (fieldValue && typeof fieldValue === 'string' && fieldValue.trim()) {
          metadataValues.push({
            fieldName: field.name,
            value: fieldValue.trim()
          });
        }
      }
    });
    
    if (metadataValues.length > 0) {
      await batchEnsure(metadataValues);  // ← Auto-cadastra antes de salvar
    }
    
    // PASSO 2: SALVAR SERVIÇO
    await consulAPI.createService(payload);
  };
  
  return (
    <Form onFinish={handleSubmit}>
      {/* Campos específicos do exporter (form_schema) */}
      {exporterFields.map(field => (
        <Form.Item name={field.name} label={field.label}>
          {/* Renderização baseada em field.type */}
        </Form.Item>
      ))}
      
      {/* Metadata genéricos (usa FormFieldRenderer - já tem auto-cadastro) */}
      {formFields.map(field => (
        <FormFieldRenderer key={field.name} field={field} />
        // ↑ Se available_for_registration=true → ReferenceValueInput
        // ↑ Se false → ProFormText/Select padrão
      ))}
    </Form>
  );
};
```

**⚠️ IMPORTANTE:**
- ✅ **Reutilizar `FormFieldRenderer`** - Já implementa auto-cadastro automaticamente
- ✅ **Reutilizar `useBatchEnsure`** - Hook já testado e funcional
- ✅ **Seguir padrão de `Services.tsx`** - Não reinventar a roda
- ✅ **Auto-cadastro acontece ANTES de salvar serviço** - Garante valores existem
- ✅ **Valores novos aparecem imediatamente** - Próximo formulário já mostra

---

#### 2.1. Modal de Criação

**Componente Novo (não misturar com código antigo):**
```typescript
// frontend/src/components/MonitoringServiceFormModal.tsx
import { Tooltip, QuestionCircleOutlined } from 'antd';
import { notification } from 'antd';
import { useBatchEnsure } from '../hooks/useReferenceValues';
import { useServiceTags } from '../hooks/useServiceTags';
import FormFieldRenderer from './FormFieldRenderer';

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
  
  // ⚡ SISTEMA DE AUTO-CADASTRO: Hooks para retroalimentação de valores
  const { batchEnsure } = useBatchEnsure();
  const { ensureTags } = useServiceTags({ autoLoad: false });
  
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
      // ⚡ PASSO 1: AUTO-CADASTRO DE VALORES (igual Services.tsx)
      // Antes de salvar, garantir que valores novos sejam cadastrados automaticamente
      
      // 1A) Auto-cadastrar TAGS (se houver)
      if (values.tags && Array.isArray(values.tags) && values.tags.length > 0) {
        try {
          await ensureTags(values.tags);
        } catch (err) {
          console.warn('Erro ao auto-cadastrar tags:', err);
          // Não bloqueia o fluxo
        }
      }
      
      // 1B) Auto-cadastrar METADATA FIELDS (campos com available_for_registration=true)
      const metadataValues: Array<{ fieldName: string; value: string }> = [];
      
      // Percorrer filterFields (metadata genéricos) para identificar campos com auto-cadastro
      filterFields.forEach((field) => {
        if (field.available_for_registration) {  // ← Verifica flag
          const fieldValue = values[field.name];
          
          // Só cadastrar se valor não for vazio
          if (fieldValue && typeof fieldValue === 'string' && fieldValue.trim()) {
            metadataValues.push({
              fieldName: field.name,
              value: fieldValue.trim()
            });
          }
        }
      });
      
      // Executar batch ensure se houver valores
      if (metadataValues.length > 0) {
        try {
          await batchEnsure(metadataValues);
          console.log(`[Auto-Cadastro] ${metadataValues.length} valores auto-cadastrados`);
        } catch (err) {
          console.warn('Erro ao auto-cadastrar metadata fields:', err);
          // Não bloqueia o fluxo
        }
      }
      
      // ⚡ PASSO 2: SALVAR SERVIÇO (após auto-cadastro)
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
        
        {/* Metadata dinâmico (campos genéricos) - USA FormFieldRenderer (já tem auto-cadastro) */}
        {filterFields.map(field => (
          <FormFieldRenderer
            key={field.name}
            field={field}
            mode={mode}
          />
          {/* 
            ⚡ FormFieldRenderer detecta automaticamente:
            - Se field.available_for_registration === true → ReferenceValueInput (autocomplete + auto-cadastro)
            - Se false → ProFormText/Select padrão
            
            ⚡ ReferenceValueInput mostra:
            - Valores existentes como opções
            - Tag verde "Novo valor será criado: {valor}" quando valor não existe
            - Auto-cadastro acontece no handleSubmit via batchEnsure()
          */}
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

## ✅ Checklist de Implementação Detalhado

### Backend
- [x] Endpoint `POST /api/v1/services` já existe (reutilizar) - `backend/api/services.py:344`
- [x] Endpoint `PUT /api/v1/services/{service_id}` já existe (reutilizar) - `backend/api/services.py:519`
- [x] Endpoint `DELETE /api/v1/services/{service_id}` já existe (reutilizar) - `backend/api/services.py:681`
- [x] Endpoint `DELETE /api/v1/services/bulk/deregister` já existe (reutilizar) - `backend/api/services.py:640`
- [ ] **NOVO:** Criar endpoint `GET /api/v1/monitoring-types/form-schema?exporter_type={type}&category={cat}`
- [ ] Estender `categorization/rules` com `form_schema` (via `monitoring/rules` UI)
- [ ] Implementar validação de tipos (monitoring-types) no CREATE
- [ ] Implementar validação de campos obrigatórios do `form_schema`
- [ ] Implementar validação de metadata obrigatórios
- [ ] Implementar integração com Consul Agent API (já existe, apenas reutilizar)
- [ ] Implementar invalidação de cache após CRUD
- [ ] Adicionar testes unitários para `form_schema` parsing
- [ ] Adicionar testes de integração end-to-end

### Frontend
- [ ] **BLOQUEADOR:** Adicionar botão "Atualizar" em `MonitoringTypes.tsx` para forçar refresh
- [ ] **BLOQUEADOR:** Implementar mensagens claras de erro (tooltips, notifications)
- [ ] **BLOQUEADOR:** Testes frontend para carregamento, refresh e tratamento de erros
- [ ] **BLOQUEADOR:** Validar que metadata fields controlam visibilidade por página (já funciona)
- [ ] Criar componente `DynamicCRUDModal.tsx` (ou `MonitoringServiceFormModal.tsx`)
- [ ] Estender `FormFieldRenderer.tsx` para suportar campos do `form_schema`
- [ ] Adicionar tooltips e informações relevantes em TODOS os campos do formulário
- [ ] Criar componente `BatchDeleteModal.tsx` (opcional, pode usar Popconfirm)
- [ ] Integrar modais no `DynamicMonitoringPage.tsx`
- [ ] Adicionar botão "Criar Serviço" no header do `DynamicMonitoringPage`
- [ ] Adicionar coluna "Ações" com botões "Editar" e "Excluir" na tabela
- [ ] Implementar batch delete (seleção múltipla com `rowSelection` do ProTable)
- [ ] Adicionar validação de formulários (frontend + backend)
- [ ] Adicionar feedback visual (success/error messages)
- [ ] Adicionar loading states durante carregamento de `form_schema`
- [ ] Manter padrão visual atual (não fugir do design existente)
- [ ] Testar fluxo completo de criação (blackbox, SNMP, windows)
- [ ] Testar fluxo completo de edição
- [ ] Testar fluxo completo de exclusão (single + batch)

### Integração
- [ ] Testar criação de serviço blackbox (ICMP) end-to-end
- [ ] Testar criação de serviço SNMP end-to-end
- [ ] Testar criação de serviço Windows Exporter end-to-end
- [ ] Testar edição de metadata (campos genéricos)
- [ ] Testar edição de campos específicos do exporter
- [ ] Testar exclusão de serviço (single)
- [ ] Testar batch delete (múltiplos serviços)
- [ ] Validar sincronização com Consul (serviço aparece imediatamente)
- [ ] Validar cache invalidation (dados atualizados após CRUD)
- [ ] Validar que Prometheus descobre novos serviços (após próximo scrape)
- [ ] Validar categorização automática (serviço aparece na categoria correta)

### Documentação
- [ ] Atualizar README com endpoints CRUD
- [ ] Documentar estrutura `form_schema` completa
- [ ] Documentar fluxo de criação passo a passo
- [ ] Documentar validações (frontend + backend)
- [ ] Adicionar exemplos de uso para cada exporter type
- [ ] Atualizar diagramas de arquitetura
- [ ] Criar guia de adição de novos exporters
- [ ] Adicionar screenshots do CRUD em ação

---

## 🎯 Roadmap de Implementação Estruturado por Sprints

### 🎯 SPRINT 0 (BLOQUEADOR - 1-2 dias): Cache KV para Monitoring-Types

**⚠️ CRÍTICO:** Este sprint é **BLOQUEADOR** para todos os outros. Deve ser feito PRIMEIRO.

**Objetivo:** Implementar cache KV para monitoring-types seguindo padrão existente (`metadata-fields`)

**Tarefas:**
1. ✅ Criar função `_prewarm_monitoring_types_cache()` em `backend/app.py`
2. ✅ Modificar endpoint `GET /monitoring-types-dynamic/from-prometheus` para usar KV
3. ✅ Estrutura KV: `skills/eye/monitoring-types` (único, não separado por nó)
4. ✅ Implementar fallback rígido (se KV vazio, extrai + salva)
5. ✅ Adicionar botão "Atualizar" no frontend (`MonitoringTypes.tsx`)
6. ✅ Mensagens claras de erro no frontend (tooltips, notifications)
7. ✅ **Testes backend:** Validar prewarm, cache, fallback
8. ✅ **Testes frontend:** Validar carregamento, refresh, mensagens de erro

**Arquivos a Modificar:**
- `backend/app.py` - Adicionar `_prewarm_monitoring_types_cache()`
- `backend/api/monitoring_types_dynamic.py` - Modificar endpoint para usar KV
- `frontend/src/pages/MonitoringTypes.tsx` - Adicionar botão "Atualizar" e mensagens

**Estimativa:** 1-2 dias (8-16 horas)

**Critério de Sucesso:**
- ✅ Prewarm popula KV no startup
- ✅ Endpoint retorna dados do KV (rápido)
- ✅ Fallback funciona se KV vazio
- ✅ Frontend mostra mensagens claras em caso de erro
- ✅ Botão "Atualizar" força re-extração
- ✅ Testes backend e frontend passam

**⚠️ IMPORTANTE:** Sem este sprint completo, não é possível avançar para CRUD.

---

### 🎯 SPRINT 1 (1 semana): Backend - Extensão de Rules

**Objetivo:** Preparar backend para suportar `form_schema` nas regras de categorização

**Tarefas:**
1. ✅ Adicionar `form_schema` em 3-5 regras principais (blackbox, snmp, windows, node)
2. ✅ Criar endpoint `GET /api/v1/monitoring-types/form-schema?exporter_type={type}&category={cat}`
3. ✅ Validar estrutura JSON de `form_schema` (schema validation)
4. ✅ Atualizar `MonitoringRules.tsx` para permitir edição de `form_schema` via UI
5. ✅ Testar endpoint com Postman/curl

**Arquivos a Modificar:**
- `backend/core/categorization_rule_engine.py` - Adicionar parsing de `form_schema`
- `backend/api/monitoring_types_dynamic.py` - Criar endpoint `get_form_schema`
- `skills/eye/monitoring-types/categorization/rules` (JSON no KV) - Adicionar `form_schema`
- `frontend/src/pages/MonitoringRules.tsx` - Adicionar editor de `form_schema`

**Estimativa:** 2-4 horas

**Critério de Sucesso:**
- Endpoint retorna `form_schema` correto para cada exporter_type
- Validação de schema funciona
- UI permite editar `form_schema` nas regras

---

### 🎯 SPRINT 2 (1 semana): Frontend - Componente DynamicCRUDModal

**Objetivo:** Criar modal dinâmico de criação/edição de serviços

**Tarefas:**
1. ✅ Criar `DynamicCRUDModal.tsx` básico
2. ✅ Estender `FormFieldRenderer.tsx` para suportar campos do `form_schema`
3. ✅ Integrar com APIs (`getFormSchema`, `getMetadataFields`, `getMonitoringTypesDynamic`)
4. ✅ Renderizar form dinâmico com tabs (Exporter Config + Metadata)
5. ✅ Validação de campos obrigatórios (frontend)
6. ✅ Testar com 1 tipo (ex: blackbox-icmp)
7. ✅ Validar criação end-to-end (frontend → backend → Consul → Prometheus)

**Arquivos a Criar/Modificar:**
- `frontend/src/components/DynamicCRUDModal.tsx` - **NOVO**
- `frontend/src/components/FormFieldRenderer.tsx` - **ESTENDER**
- `frontend/src/services/api.ts` - Adicionar `getFormSchema()`

**Estimativa:** 4-6 horas

**Critério de Sucesso:**
- Modal carrega tipos disponíveis
- Modal carrega `form_schema` ao selecionar tipo
- Form renderiza campos dinâmicos corretamente
- Validação funciona
- Serviço é criado no Consul e aparece no Prometheus

---

### 🎯 SPRINT 3 (1 semana): Integração com DynamicMonitoringPage

**Objetivo:** Integrar CRUD completo no `DynamicMonitoringPage`

**Tarefas:**
1. ✅ Integrar modal com `DynamicMonitoringPage`
2. ✅ Adicionar botão "Criar Novo" no header
3. ✅ Adicionar ação "Editar" na linha da tabela
4. ✅ Adicionar ação "Deletar" (usa `useConsulDelete` existente)
5. ✅ Implementar batch delete (seleção múltipla)
6. ✅ Testar com múltiplos tipos de exporters

**Arquivos a Modificar:**
- `frontend/src/pages/DynamicMonitoringPage.tsx` - **INTEGRAR CRUD**

**Estimativa:** 3-4 horas

**Critério de Sucesso:**
- Botão "Criar" abre modal
- Botão "Editar" preenche modal com dados do serviço
- Botão "Excluir" remove serviço do Consul
- Batch delete remove múltiplos serviços
- Tabela atualiza automaticamente após CRUD

---

### 🎯 SPRINT 4 (1 semana): Testes e Documentação

**Objetivo:** Validar funcionalidade completa e documentar

**Tarefas:**
1. ✅ Testes completos em todas as categorias
2. ✅ Testar criação de serviço blackbox (ICMP) end-to-end
3. ✅ Testar criação de serviço SNMP end-to-end
4. ✅ Testar criação de serviço Windows Exporter end-to-end
5. ✅ Testar edição de metadata e campos específicos
6. ✅ Testar exclusão (single + batch)
7. ✅ Validar sincronização com Consul e Prometheus
8. ✅ Documentação completa
9. ✅ Desativar páginas legadas (Services, Exporters, BlackboxTargets)

**Estimativa:** 2-3 horas (testes) + 1-2 horas (documentação)

**Critério de Sucesso:**
- Todos os testes passam
- Documentação completa e atualizada
- Páginas legadas desativadas
- Sistema 100% funcional

---

## 🎯 Próximos Passos Imediatos

1. **Revisar esta análise** com o time
2. **Aprovar arquitetura proposta** (especialmente extensão de `categorization/rules`)
3. **Iniciar SPRINT 1:**
   - Adicionar `form_schema` em 3-5 regras principais
   - Criar endpoint `GET /monitoring-types/form-schema`
   - Testar endpoint com Postman
4. **Seguir roadmap estruturado** por sprints
5. **Migrar campos de JSONs estáticos** para `categorization/rules` (durante Sprint 1)
6. **Testes completos** antes de deploy (Sprint 4)

---

## 📚 Páginas Legadas - Snippets de Código Reutilizável

### Services.tsx (SERÁ DESATIVADA) - Padrões para Reutilizar

**⚠️ IMPORTANTE:** Não copiar código direto. Usar como referência para criar componentes novos.

#### ✅ Padrão 1: Modal de Criação com FormFieldRenderer

```typescript
// services.tsx:450-550
// Padrão de renderização dinâmica de campos

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

**Aplicação:** Usar no `DynamicCRUDModal` para renderizar campos metadata genéricos.

---

#### ✅ Padrão 2: Validação de Duplicatas

```typescript
// services.tsx:120
// Verificar se já existe serviço antes de criar

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

**Aplicação:** Adicionar validação no `handleSubmit` do `DynamicCRUDModal` antes de chamar `consulAPI.createService()`.

---

#### ✅ Padrão 3: Auto-Cadastro de Valores em Reference-Values (CRÍTICO - Já Implementado)

**⚠️ IMPORTANTE:** Este padrão é **CRÍTICO** e já está implementado. Deve ser **reutilizado** no CRUD dinâmico.

**Como Funciona:**

1. **Configuração em `metadata-fields`:**
   - Campo tem propriedade `available_for_registration: true`
   - Campo aparece na página `ReferenceValues`
   - Valores pré-cadastrados aparecem como opções

2. **FormFieldRenderer detecta automaticamente:**
   ```typescript
   // frontend/src/components/FormFieldRenderer.tsx (linhas 144-167)
   
   // Se campo tem available_for_registration=true → ReferenceValueInput
   const shouldUseAutocomplete =
     field.available_for_registration &&
     field.field_type === 'string' &&
     !EXCLUDE_FROM_AUTOCOMPLETE.includes(field.name);
   
   if (shouldUseAutocomplete) {
     return (
       <Form.Item name={field.name} label={field.display_name}>
         <ReferenceValueInput
           fieldName={field.name}
           placeholder={`Selecione ou digite ${field.display_name.toLowerCase()}`}
           required={field.required}
         />
       </Form.Item>
     );
   }
   ```

3. **ReferenceValueInput mostra indicador visual:**
   ```typescript
   // frontend/src/components/ReferenceValueInput.tsx (linhas 205-211)
   
   // Tag verde quando valor novo é digitado
   {internalValue && !loading && !values.includes(internalValue) && (
     <Tag color="green" icon={<PlusOutlined />} style={{ fontSize: '11px' }}>
       Novo valor será criado: "{internalValue}"
     </Tag>
   )}
   ```

4. **Auto-cadastro no handleSubmit:**
   ```typescript
   // frontend/src/pages/Services.tsx (linhas 806-832)
   
   // 1B) Auto-cadastrar METADATA FIELDS
   const metadataValues: Array<{ fieldName: string; value: string }> = [];
   
   formFields.forEach((field) => {
     if (field.available_for_registration) {  // ← Verifica flag
       const fieldValue = (values as any)[field.name];
       if (fieldValue && typeof fieldValue === 'string' && fieldValue.trim()) {
         metadataValues.push({
           fieldName: field.name,
           value: fieldValue.trim()
         });
       }
     }
   });
   
   // Executar batch ensure
   if (metadataValues.length > 0) {
     await batchEnsure(metadataValues);  // ← POST /reference-values/batch-ensure
   }
   ```

**Aplicação no CRUD Dinâmico:**
- ✅ **Reutilizar `FormFieldRenderer`** - Já implementa auto-cadastro
- ✅ **Reutilizar `useBatchEnsure`** - Hook já testado
- ✅ **Seguir padrão de `Services.tsx`** - Não reinventar
- ✅ **Auto-cadastro ANTES de salvar serviço** - Garante valores existem
- ✅ **Tag verde "Novo valor será criado"** - Feedback visual imediato

---

#### ✅ Padrão 4: Batch Delete com Seleção Múltipla

```typescript
// services.tsx:250
// Seleção múltipla e exclusão em lote

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

**Aplicação:** Adicionar `rowSelection` no `ProTable` do `DynamicMonitoringPage` e usar `useConsulDelete` hook para batch delete.

---

#### ✅ Padrão 5: Uso do Hook useConsulDelete

```typescript
// Padrão de uso do hook compartilhado (já testado e funcional)

const { deleteResource, deleteBatch } = useConsulDelete({
  deleteFn: async (payload: any) => {
    return consulAPI.deleteService(payload.service_id, {
      node_addr: payload.node_addr
    });
  },
  clearCacheFn: consulAPI.clearCache,
  cacheKey: 'monitoring-services',
  successMessage: 'Serviço removido com sucesso',
  errorMessage: 'Falha ao remover serviço',
  onSuccess: () => {
    actionRef.current?.reload();
  },
});

// Uso:
await deleteResource({
  service_id: record.ID,
  node_addr: record.node_ip || record.Node
});
```

**Aplicação:** Reutilizar exatamente este padrão no `DynamicMonitoringPage` para exclusão.

---

### Exporters.tsx e BlackboxTargets.tsx (SERÃO DESATIVADAS) - Padrões para Aprender

#### ✅ Padrão de Colunas Dinâmicas

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

**Aplicação:** Já implementado no `DynamicMonitoringPage`. Manter padrão.

---

#### ✅ Padrão de Exportação CSV

```typescript
// exporters.tsx:300
// Exportar dados da tabela para CSV

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

**Aplicação:** Adicionar botão "Exportar CSV" no `DynamicMonitoringPage` (opcional, mas útil).

---

**⚠️ ATENÇÃO:**
- Não copiar código legado diretamente
- Usar padrões já estabelecidos em `DynamicMonitoringPage`
- Criar componentes novos baseados nestes padrões
- DRY: Extrair para `DynamicCRUDModal` e hooks compartilhados

---

## 📝 Notas Importantes

### ✅ O que JÁ existe e pode ser reutilizado:

**Backend:**
- ✅ Backend CRUD completo (`backend/api/services.py`)
  - `POST /api/v1/services` (linha 344) - Criar serviço
  - `PUT /api/v1/services/{service_id}` (linha 519) - Editar serviço
  - `DELETE /api/v1/services/{service_id}` (linha 681) - Deletar serviço
  - `DELETE /api/v1/services/bulk/deregister` (linha 640) - Batch delete
- ✅ `ConsulManager` com métodos funcionais
  - `register_service()` - Funcional
  - `update_service()` - Funcional (re-registro automático)
  - `deregister_service()` - Funcional
- ✅ Validação de duplicatas
- ✅ Sanitização de service IDs
- ✅ Suporte multi-site (tags automáticas, sufixos)
- ✅ Auto-cadastro de valores em `reference-values`

**Frontend:**
- ✅ `Services.tsx` como referência (não misturar código, mas usar padrões)
- ✅ `useConsulDelete` hook compartilhado (`hooks/useConsulDelete.ts`)
- ✅ `FormFieldRenderer` para metadata fields (`components/FormFieldRenderer.tsx`)
- ✅ `NodeSelector`, `ServerSelector`, `ColumnSelector` componentes compartilhados
- ✅ `MetadataFilterBar`, `AdvancedSearchPanel` componentes de filtro
- ✅ `useMetadataFields`, `useServersContext`, `useNodesContext` hooks compartilhados

**Padrões de Código Reutilizáveis (de Services.tsx):**
- ✅ Validação de duplicatas antes de criar
- ✅ Auto-cadastro de valores em `reference-values`
- ✅ Batch delete com seleção múltipla
- ✅ Feedback visual (success/error messages)

### ⚠️ O que NÃO fazer:
- ❌ **NÃO misturar código** de `Services.tsx` com `DynamicMonitoringPage`
- ❌ **NÃO usar JSONs estáticos** (`backend/schemas/monitoring-types/`) - serão removidos
- ❌ **NÃO hardcodar campos** por exporter_type - usar `form_schema`
- ❌ **NÃO criar componentes duplicados** - reutilizar existentes
- ❌ **NÃO copiar código direto** de páginas legadas - criar novos baseados nos padrões

### ✅ O que fazer:
- ✅ Criar componentes novos baseados nos antigos (DRY)
- ✅ Usar `categorization/rules` como fonte única de verdade para `form_schema`
- ✅ Manter 100% dinâmico - nada hardcoded
- ✅ Reutilizar hooks e componentes compartilhados
- ✅ Estender `FormFieldRenderer` para suportar campos do `form_schema`
- ✅ Usar `useConsulDelete` para exclusão (já testado e funcional)
- ✅ Seguir padrões estabelecidos em `Services.tsx` (mas criar código novo)

---

## 🔄 Comparação: Análise Cursor vs Claude Code

### Pontos em Comum ✅

1. ✅ **monitoring-types e DynamicMonitoringPage não estão integrados** - Confirmado por ambos
2. ✅ **Backend CRUD já existe em services.py** - Confirmado por ambos
3. ✅ **Problema de campos customizados por exporter** - Identificado por ambos
4. ✅ **service-groups mostra apenas serviços com instâncias (comportamento natural Consul)** - Confirmado por ambos
5. ✅ **Solução: Estender `categorization/rules` com `form_schema`** - Proposta por ambos

---

### Diferenças e Complementos

| Aspecto | Análise Cursor | Análise Claude Code | Documento Unificado |
|---------|----------------|---------------------|---------------------|
| **Solução para campos dinâmicos** | Menciona problema | ✅ Proposta completa com `form_schema` | ✅ **JSON completo com validações** |
| **Estrutura JSON form_schema** | ❌ Não detalha | ✅ JSON completo com validações | ✅ **Exemplos detalhados (3 exporters)** |
| **Componente Modal** | `MonitoringServiceFormModal` | `DynamicCRUDModal` | ✅ **Ambas opções documentadas** |
| **Código skeleton** | Parcial | ✅ Código completo | ✅ **Código completo incluído** |
| **Integração DynamicMonitoringPage** | Menciona necessidade | ✅ Código de integração detalhado | ✅ **Código completo incluído** |
| **API form-schema** | Endpoint básico | ✅ Endpoint completo com código Python | ✅ **Endpoint completo documentado** |
| **Docs oficiais** | Menciona | ✅ Resumo técnico com links e exemplos | ✅ **Resumo técnico completo** |
| **Roadmap** | Não estruturado | ✅ Fases detalhadas com horas estimadas | ✅ **Roadmap por sprints completo** |
| **Código reutilizável** | Menciona existência | ✅ Snippets específicos | ✅ **Snippets completos incluídos** |
| **Fluxo passo a passo** | Diagramas | ✅ Fluxo detalhado com 7 passos | ✅ **Fluxo completo documentado** |

**Conclusão:** O documento unificado combina o melhor de ambos, com arquitetura clara (Cursor) + código detalhado (Claude Code).

---

## 🎉 Conclusão Final

Este documento unificado fornece uma **análise completa e detalhada** da arquitetura CRUD dinâmico do Skills Eye, combinando:

✅ **Diagnóstico preciso** dos componentes atuais (ambas análises)
✅ **Solução concreta** para campos dinâmicos (`form_schema` completo)
✅ **Código de exemplo** pronto para implementar (skeleton completo)
✅ **Roadmap claro** com estimativas de tempo por sprints
✅ **Reutilização inteligente** de código existente (snippets específicos)
✅ **Documentação técnica** de Consul, Prometheus, Blackbox, SNMP (resumo completo)
✅ **Fluxo passo a passo** detalhado de criação de serviço
✅ **Comparação entre análises** para garantir completude

**Diferenciais deste Documento Unificado:**
- ⚡ Proposta estruturada de `form_schema` com JSON completo e 3 exemplos detalhados
- ⚡ Código skeleton completo de `DynamicCRUDModal` e endpoint backend
- ⚡ Integração detalhada com `DynamicMonitoringPage` (código completo)
- ⚡ Resumo técnico de documentações oficiais com exemplos práticos
- ⚡ Roadmap por sprints com horas estimadas e tarefas específicas
- ⚡ Snippets de código reutilizável de `Services.tsx` documentados
- ⚡ Extensão do `FormFieldRenderer` para suportar `form_schema`
- ⚡ Checklist completo de implementação

**Próximo Passo:** Iniciar **SPRINT 0 (BLOQUEADOR)** - Cache KV para monitoring-types

**⚠️ CRÍTICO:** Sem o Sprint 0 completo, não é possível avançar para CRUD. O cache KV é bloqueador.

---

**Documento criado em:** 2025-11-17  
**Última atualização:** 2025-11-17 (Documento Unificado - Versão 2.0)  
**Autores:** Análise Profissional (Cursor) + Claude Code (Sonnet 4.5)  
**Status:** ✅ Análise Completa e Detalhada - Pronto para Implementação

