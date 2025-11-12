# MetadataFields.tsx - Análise Completa da Página

**Arquivo:** `frontend/src/pages/MetadataFields.tsx`
**Data da análise:** 2025-11-12 (ATUALIZADO)
**Linhas de código:** 3468 linhas (expandida significativamente)

> **✅ DOCUMENTO ATUALIZADO (2025-11-12)**
>
> **Funcionalidades ADICIONADAS desde última análise:**
> - ✅ **Gerenciamento de Sites** - CRUD completo de sites (Palmas, Rio, DTC)
> - ✅ **External Labels** - Gerenciamento global e por servidor
> - ✅ **Naming Strategy** - Configuração option1 vs option2, sufixos automáticos
> - ✅ **Reference Values** - Autocomplete dinâmico de valores
> - ✅ **Sync Status** - Visualização de sincronização KV ↔ Prometheus
> - ✅ **Batch Sync** - Sincronização em lote instantânea
> - ✅ **Force Extract** - Extração forçada de campos via SSH
>
> **Funcionalidades REMOVIDAS:**
> - ❌ Botão "Master → Slaves" (movido para PrometheusConfig)
> - ❌ Botões "Reiniciar Prometheus" (movido para PrometheusConfig)
>
> **Nova Estrutura:**
> A página agora possui **6 abas principais** em formato de tabs:
> 1. 📋 **Campos Metadata** - Gerenciamento de campos (tabela principal)
> 2. 🌍 **Gerenciar Sites** - CRUD de sites (palmas, rio, dtc)
> 3. 🏷️ **External Labels Global** - External labels compartilhados
> 4. 🏷️ **External Labels Todos** - External labels por servidor
> 5. 📚 **Reference Values** - Valores de autocomplete
> 6. 🔄 **Sync Status** - Status de sincronização

---

## 📋 RESUMO EXECUTIVO

### O QUE É A PÁGINA METADATAFIELDS

A página **MetadataFields** é o **centro de controle completo** para gerenciar TODOS os aspectos de metadata no sistema Skills Eye. Ela consolidou funcionalidades que antes estavam espalhadas em `/settings` e outras páginas. Agora permite que o usuário:

#### 🔧 Gerenciamento de Campos Metadata
1. **Adicione novos campos metadata** ao sistema
2. **Edite campos existentes** (display name, tipo, categoria, visibilidade)
3. **Delete campos não obrigatórios**
4. **Sincronize automaticamente** com prometheus.yml em múltiplos servidores
5. **Force Extract** - Extração SSH forçada de campos do Prometheus

#### 🌍 Gerenciamento de Sites (NOVO - 2025-11-12)
1. **CRUD Completo de Sites** - Criar, editar, excluir sites (palmas, rio, dtc)
2. **Cores Customizadas** - Atribuir cores para identificação visual
3. **Site Padrão** - Definir site default (checkbox `is_default`)
4. **Auto-Sync** - Sincroniza sites detectados no Prometheus automaticamente
5. **Naming Strategy** - Configurar option1 (filtros) vs option2 (sufixos)

#### 🏷️ External Labels (NOVO - 2025-11-12)
1. **External Labels Global** - Labels compartilhados por todos os servidores
2. **External Labels por Servidor** - Labels específicos de cada Prometheus
3. **Edição Inline** - Alterar valores diretamente na tabela
4. **Sync com Prometheus** - Reflete configuração real dos servidores

#### 📚 Reference Values (NOVO - 2025-11-12)
1. **Autocomplete Dinâmico** - Valores para dropdowns de formulários
2. **Por Campo** - Company, Project, Env, Tipo, Fabricante, etc
3. **Categorias** - Organização por categorias (basic, device, extra)
4. **CRUD Inline** - Adicionar/remover valores diretamente

#### 🔄 Sync Status (NOVO - 2025-11-12)
1. **Visualização de Status** - KV vs Prometheus (em sync ou não)
2. **Campos Órfãos** - Campos no KV mas não no Prometheus
3. **Campos Missing** - Campos no Prometheus mas não no KV
4. **Batch Sync** - Sincronização em lote de todos os servidores

### POR QUE ESSA PÁGINA FOI CRIADA

**Contexto histórico:** Antes dessa página existir, os campos metadata eram:
- Hardcoded em múltiplos lugares do código
- Difíceis de adicionar (requeriam mudanças em backend + frontend + prometheus.yml)
- Inconsistentes entre diferentes páginas
- Sem sincronização automática entre servidores

**Problema que resolve:**
```
ANTES (Processo Manual):
1. Adicionar campo em backend/config/metadata_fields.json
2. Editar frontend/src/pages/Services.tsx (adicionar coluna)
3. Editar frontend/src/pages/Exporters.tsx (adicionar coluna)
4. SSH em cada servidor Prometheus
5. Editar prometheus.yml manualmente (adicionar relabel_config)
6. Validar YAML
7. Reiniciar Prometheus
8. Repetir para cada servidor slave

   → TEMPO: ~30-40 minutos
   → ERRO PROPENSO: Muito alto

DEPOIS (Com MetadataFields UI):
1. Clicar em "Adicionar Campo"
2. Preencher form (nome, tipo, categoria)
3. Clicar "Salvar"
4. Clicar "Master → Slaves"

   → TEMPO: ~2 minutos
   → ERRO PROPENSO: Mínimo (validações automáticas)
```

**Benefício principal:**
- **Fonte única da verdade** para todos os campos metadata
- **Sincronização automática** com Prometheus
- **Gerenciamento multi-servidor** simplificado
- **Redução de 95% no tempo** de adição de campos

---

## � NOVAS FUNCIONALIDADES (2025-11-12)

### 1. Gerenciamento de Sites

**Localização:** Aba "Gerenciar Sites" na página MetadataFields

**O que faz:**
Gerencia os sites (localizações físicas) do sistema: Palmas (HQ), Rio de Janeiro, DTC.

**KV Namespace:** `skills/eye/metadata/sites`

**Estrutura de Dados:**
```json
{
  "data": {
    "sites": [
      {
        "code": "palmas",
        "name": "Palmas",
        "color": "red",
        "is_default": true
      },
      {
        "code": "rio",
        "name": "Rio de Janeiro",
        "color": "gold",
        "is_default": false
      },
      {
        "code": "dtc",
        "name": "Dtc",
        "color": "blue",
        "is_default": false
      }
    ],
    "naming_config": {
      "strategy": "option2",
      "suffix_enabled": true,
      "description": "option1: Nomes iguais + filtros | option2: Sufixos por site"
    }
  },
  "meta": {
    "updated_at": "2025-11-12T...",
    "version": "2.0.0"
  }
}
```

**Funcionalidades:**
- ✅ **Criar Site:** Botão "Adicionar Site" abre modal com form
- ✅ **Editar Site:** Clique no ícone ✏️ para editar code, name, color, is_default
- ✅ **Excluir Site:** Clique no ícone 🗑️ para remover site (com confirmação)
- ✅ **Auto-Sync:** Botão "Sincronizar Sites" detecta sites do external_labels automaticamente
- ✅ **Naming Strategy:** Card separado com dropdown option1/option2 e switch de sufixos

**Endpoints:**
- `GET /api/v1/metadata-fields/config/sites` - Lista todos os sites
- `POST /api/v1/metadata-fields/config/sites` - Cria novo site
- `PATCH /api/v1/metadata-fields/config/sites/{code}` - Atualiza site
- `DELETE /api/v1/metadata-fields/config/sites/{code}` - Remove site
- `POST /api/v1/metadata-fields/config/sites/sync` - Auto-sync com Prometheus
- `PATCH /api/v1/metadata-fields/config/naming` - Atualiza naming strategy

**Impacto:**
- **Services.tsx:** Adiciona sufixos automáticos aos nomes (ex: `node_exporter_rio`)
- **Exporters.tsx:** Filtra por site, adiciona sufixos
- **BlackboxTargets.tsx:** Filtra por site
- **Backend (naming_utils.py):** Aplica sufixos baseado em `site` ou `cluster`

---

### 2. External Labels

**Localização:** Abas "External Labels Global" e "External Labels Todos"

**O que faz:**
Gerencia `external_labels` do prometheus.yml de cada servidor. Labels são adicionados a TODAS as métricas coletadas pelo Prometheus.

**Aba "External Labels Global":**
- Mostra labels **compartilhados** por todos os servidores
- Exemplo: `site=palmas`, `env=prod`, `datacenter=br-central`
- Edição inline com botão "Salvar"

**Aba "External Labels Todos":**
- Mostra labels **por servidor** (cada linha = 1 servidor)
- Permite visualizar diferenças entre servidores
- Edição inline por servidor

**Origem dos Dados:**
```yaml
# prometheus.yml
global:
  external_labels:
    site: palmas
    env: prod
    datacenter: br-central
    cluster: prod-1
```

**Endpoints:**
- `GET /api/v1/metadata-fields/external-labels/{hostname}` - Labels de servidor específico
- `POST /api/v1/metadata-fields/force-extract` - Extrai via SSH de todos os servidores

**Caso de Uso:**
1. Abrir aba "External Labels Global"
2. Ver que `site=palmas` e `env=prod`
3. Editar inline: `env=staging`
4. Clicar "Salvar"
5. Backend conecta via SSH e edita prometheus.yml
6. Prometheus recarrega automaticamente

---

### 3. Reference Values

**Localização:** Aba "Reference Values"

**O que faz:**
Gerencia valores de autocomplete para dropdowns em formulários de Services, Exporters, etc.

**KV Namespace:** `skills/eye/reference-values/{field_name}.json`

**Estrutura de Dados:**
```json
// skills/eye/reference-values/company.json
{
  "field": "company",
  "values": ["Skills IT", "Cliente A", "Cliente B"],
  "updated_at": "2025-11-12T..."
}
```

**Campos Gerenciados:**
- `company` - Empresas cadastradas
- `project` - Projetos
- `env` - Ambientes (prod, dev, staging)
- `tipo` - Tipos de dispositivo
- `fabricante` - Fabricantes (Cisco, HP, Dell)
- `tipo_dispositivo_abrev` - Abreviações (SW, RT, FW)
- `cod_localidade` - Códigos de localidade

**Funcionalidades:**
- ✅ **Visualizar por Categoria:** Filtro por categoria (basic, device, extra)
- ✅ **Adicionar Valor:** Botão "+" adiciona valor inline
- ✅ **Remover Valor:** Clique no ícone 🗑️ ao lado do valor
- ✅ **Auto-Populate:** Botão "Atualizar" sincroniza com valores existentes no Consul

**Endpoints:**
- `GET /api/v1/metadata-fields/reference-values/{field}` - Lista valores de campo
- `POST /api/v1/metadata-fields/reference-values/{field}` - Adiciona valor
- `DELETE /api/v1/metadata-fields/reference-values/{field}` - Remove valor

**Fluxo de Uso:**
```
Usuário abre Services → Clica "Criar Serviço"
     ↓
Dropdown "Empresa" carrega de reference-values/company.json
     ↓
Usuário digita "Nova Empresa"
     ↓
Frontend detecta valor novo e sugere adicionar
     ↓
POST /reference-values/company → Adiciona ao KV
     ↓
Próxima vez dropdown já tem "Nova Empresa"
```

---

### 4. Sync Status

**Localização:** Aba "Sync Status"

**O que faz:**
Mostra status de sincronização entre KV (Consul) e Prometheus (SSH).

**3 Estados Possíveis:**
1. ✅ **Em Sync** - Campos no KV = Campos no Prometheus
2. ⚠️ **Órfãos** - Campos no KV mas NÃO no Prometheus (pode remover do KV)
3. ⚠️ **Missing** - Campos no Prometheus mas NÃO no KV (deve adicionar ao KV)

**Tabela por Servidor:**
```
┌──────────────────┬─────────┬─────────┬─────────┐
│ Servidor         │ Em Sync │ Órfãos  │ Missing │
├──────────────────┼─────────┼─────────┼─────────┤
│ 172.16.1.26      │ ✅ 18   │ ⚠️ 2    │ ⚠️ 1    │
│ 172.16.200.14    │ ✅ 16   │ ⚠️ 4    │ ⚠️ 0    │
└──────────────────┴─────────┴─────────┴─────────┘
```

**Ações Disponíveis:**
- **Adicionar ao KV:** Clique para adicionar campos missing ao KV
- **Remover do KV:** Clique para remover campos órfãos do KV
- **Batch Sync:** Botão "Sincronizar Todos" executa sync em lote

**Endpoints:**
- `GET /api/v1/metadata-fields/sync-status?server_id={id}` - Status de servidor específico
- `POST /api/v1/metadata-fields/add-to-kv` - Adiciona campos missing ao KV
- `POST /api/v1/metadata-fields/remove-orphans` - Remove campos órfãos do KV
- `POST /api/v1/metadata-fields/batch-sync` - Sync em lote

**Quando Usar:**
- Após adicionar campo manualmente no prometheus.yml (via SSH)
- Após editar prometheus.yml na página PrometheusConfig
- Quando detecção automática falha
- Para validar consistência após mudanças em massa

---

### 5. Naming Strategy (Sistema Dinâmico)

**Localização:** Card "Configuração Global de Naming Strategy" na aba "Gerenciar Sites"

**O que faz:**
Define como serviços são nomeados no sistema multi-site.

**2 Opções:**

**Option 1: Nomes Iguais + Filtros**
```
Palmas: node_exporter  |  Filtros: site=palmas
Rio:    node_exporter  |  Filtros: site=rio
DTC:    node_exporter  |  Filtros: site=dtc
```
- ✅ Nomes idênticos em todos os sites
- ✅ Filtros por site para distinguir
- ❌ Pode causar conflitos no Consul se não filtrar

**Option 2: Sufixos por Site (RECOMENDADO)**
```
Palmas: node_exporter       (sem sufixo - é o default)
Rio:    node_exporter_rio   (sufixo _rio)
DTC:    node_exporter_dtc   (sufixo _dtc)
```
- ✅ Nomes únicos por site
- ✅ Sem conflitos no Consul
- ✅ Fácil identificar site pelo nome
- ❌ Nomes mais longos

**Configuração:**
- **Estratégia:** Dropdown (option1 / option2)
- **Sufixos Habilitados:** Switch (on / off)
- **Salvar:** Botão atualiza KV instantaneamente

**Onde é Aplicado:**
- `backend/core/naming_utils.py` - Função `apply_site_suffix()`
- `backend/api/services.py` - Linhas 403-407, 570-574
- `backend/api/blackbox_manager.py` - Aplica sufixos em targets
- `frontend/src/hooks/useSites.tsx` - Hook disponibiliza naming config
- `frontend/src/utils/namingUtils.ts` - Funções deprecated (usar useSites)

**Endpoint:**
- `PATCH /api/v1/metadata-fields/config/naming` - Atualiza naming strategy

**Cache Dinâmico:**
```python
# backend/core/naming_utils.py
_naming_cache = {}  # Cache global

async def _update_cache():
    """Atualiza cache de sites e naming do KV"""
    kv_data = await kv.get_json("skills/eye/metadata/sites")
    _naming_cache = kv_data["data"]["naming_config"]
    # Sem fallback hardcoded - 100% dinâmico!
```

**Validação:**
```bash
# Teste automatizado
python3 Tests/naming/test_naming_baseline.py
# Resultado: 11/12 testes passando (91.7%)
```

---

### 6. Batch Sync (Modal Instantâneo)

**Localização:** Ao abrir aba "Campos Metadata" pela primeira vez

**O que faz:**
Executa sincronização em lote de TODOS os servidores Prometheus ao mesmo tempo.

**Fluxo:**
1. Usuário abre página MetadataFields
2. Clica na aba "Campos Metadata"
3. Modal aparece automaticamente: "Sincronizando com servidores..."
4. Backend conecta SSH em paralelo em todos os servidores
5. Extrai campos de cada prometheus.yml
6. Atualiza KV com campos encontrados
7. Modal fecha automaticamente (3-5 segundos)

**Endpoints:**
- `POST /api/v1/metadata-fields/batch-sync` - Sync em lote
- `POST /api/v1/metadata-fields/force-extract` - Extração forçada manual

**Benefício:**
- ❌ **ANTES:** Usuário precisava clicar "Sincronizar" em cada servidor
- ✅ **AGORA:** Sincronização automática ao abrir página (experiência fluida)

**Configuração:**
```typescript
// MetadataFields.tsx
useEffect(() => {
  if (activeTab === 'fields' && !batchSyncDone) {
    handleBatchSync();  // Executa apenas 1 vez
    setBatchSyncDone(true);
  }
}, [activeTab]);
```

---

## �🏗️ ARQUITETURA E FLUXO DE DADOS

### Estrutura de Dados (metadata_fields.json)

```json
{
  "version": "1.0.0",
  "last_updated": "2025-10-28T14:00:00Z",
  "fields": [
    {
      "name": "company",                    // Nome técnico (usado internamente)
      "display_name": "Empresa",            // Nome exibido ao usuário
      "description": "Nome da empresa",     // Tooltip/descrição
      "source_label": "__meta_consul_service_metadata_company",  // Prometheus label
      "field_type": "string",               // string, number, select, text, url
      "required": true,                     // Se é obrigatório
      "show_in_table": true,                // Mostrar em tabelas
      "show_in_dashboard": true,            // Mostrar no dashboard
      "show_in_form": true,                 // Mostrar em formulários
      "options": [],                        // Opções para select (se aplicável)
      "order": 9,                           // Ordem de exibição
      "category": "basic",                  // infrastructure, basic, device, extra
      "editable": true,                     // Se pode ser editado
      "validation_regex": ""                // Regex de validação (opcional)
    }
  ],
  "categories": {
    "infrastructure": { "name": "Infraestrutura", "icon": "cloud" },
    "basic": { "name": "Básico", "icon": "info" },
    "device": { "name": "Dispositivo", "icon": "desktop" },
    "extra": { "name": "Extras", "icon": "plus" }
  }
}
```

### Relação com Prometheus (relabel_configs)

Quando você adiciona um campo metadata através da UI, o sistema automaticamente:

```yaml
# prometheus.yml (ANTES - sem o campo)
scrape_configs:
  - job_name: 'consul-services'
    consul_sd_configs:
      - server: '172.16.1.26:8500'
    relabel_configs:
      - source_labels: [__meta_consul_service_metadata_instance]
        target_label: instance
      - source_labels: [__meta_consul_service_metadata_company]
        target_label: company
      # ... outros campos ...

# prometheus.yml (DEPOIS - com novo campo "datacenter")
scrape_configs:
  - job_name: 'consul-services'
    consul_sd_configs:
      - server: '172.16.1.26:8500'
    relabel_configs:
      - source_labels: [__meta_consul_service_metadata_instance]
        target_label: instance
      - source_labels: [__meta_consul_service_metadata_company]
        target_label: company
      - source_labels: [__meta_consul_service_metadata_datacenter]  # ← NOVO!
        target_label: datacenter                                     # ← NOVO!
      # ... outros campos ...
```

**O que acontece por trás:**
1. Frontend envia campo para backend
2. Backend atualiza `metadata_fields.json`
3. Backend conecta via SSH em cada servidor Prometheus
4. Backend lê `prometheus.yml` via SFTP
5. Backend adiciona nova `relabel_config` no lugar certo
6. Backend valida YAML com `promtool check config`
7. Backend salva arquivo e restaura permissões
8. Backend executa `systemctl reload prometheus`
9. Prometheus recarrega e começa a coletar novo label

---

## 📊 ANÁLISE LINHA A LINHA DO CÓDIGO

### IMPORTS E CONFIGURAÇÕES (Linhas 1-50)

```typescript
// Linhas 12-23: Imports do Ant Design Pro
import {
  PageContainer,    // Container da página com header
  ProTable,         // Tabela avançada
  ProCard,          // Card estilizado
  ModalForm,        // Modal com form integrado
  ProFormText,      // Input de texto com validação
  ProFormSelect,    // Select com opções
  ProFormSwitch,    // Switch on/off
  ProFormTextArea,  // Textarea
  ProFormDigit,     // Input numérico
} from '@ant-design/pro-components';

// Linhas 25-36: Imports do Ant Design
import {
  Button, Space, message, Tag, Badge, Popconfirm, Select, Tooltip, Modal, Alert
} from 'antd';

// Linhas 37-47: Ícones utilizados
PlusOutlined,          // Adicionar campo
EditOutlined,          // Editar campo
DeleteOutlined,        // Deletar campo
SyncOutlined,          // Sincronizar
CloudSyncOutlined,     // Replicar Master→Slaves
ReloadOutlined,        // Reiniciar Prometheus
CheckCircleOutlined,   // Sucesso
WarningOutlined,       // Aviso
CloudServerOutlined    // Servidor

// Linha 50: API Base URL
const API_URL = import.meta.env?.VITE_API_URL ?? 'http://localhost:5000/api/v1';
```

### INTERFACES TYPESCRIPT (Linhas 52-76)

```typescript
// Linhas 52-67: Interface do campo metadata
interface MetadataField {
  name: string;                // Nome técnico (ex: "company")
  display_name: string;        // Nome exibido (ex: "Empresa")
  description: string;         // Descrição do campo
  source_label: string;        // Label do Prometheus
  field_type: string;          // string | number | select | text | url
  required: boolean;           // Campo obrigatório?
  show_in_table: boolean;      // Mostrar em tabelas?
  show_in_dashboard: boolean;  // Mostrar no dashboard?
  show_in_form: boolean;       // Mostrar em formulários?
  options?: string[];          // Opções para select (opcional)
  order: number;               // Ordem de exibição (1, 2, 3...)
  category: string;            // infrastructure | basic | device | extra
  editable: boolean;           // Pode ser editado?
  validation_regex?: string;   // Regex de validação (opcional)
}

// Linhas 69-76: Interface do servidor Prometheus
interface Server {
  id: string;          // "172.16.1.26:5522"
  hostname: string;    // "172.16.1.26"
  port: number;        // 5522
  username: string;    // "root"
  type: string;        // "master" ou "slave"
  display_name: string;// "Prometheus Master (1.26)"
}
```

### ESTADOS DO COMPONENTE (Linhas 78-85)

```typescript
const [fields, setFields] = useState<MetadataField[]>([]);
  // ↑ Lista de todos os campos metadata

const [servers, setServers] = useState<Server[]>([]);
  // ↑ Lista de todos os servidores Prometheus (master + slaves)

const [selectedServer, setSelectedServer] = useState<string>('');
  // ↑ Servidor atualmente selecionado (ex: "172.16.1.26:5522")

const [loading, setLoading] = useState(false);
  // ↑ Loading state para tabela

const [createModalVisible, setCreateModalVisible] = useState(false);
  // ↑ Controla visibilidade do modal de criar campo

const [editModalVisible, setEditModalVisible] = useState(false);
  // ↑ Controla visibilidade do modal de editar campo

const [editingField, setEditingField] = useState<MetadataField | null>(null);
  // ↑ Campo sendo editado atualmente
```

### FUNÇÃO fetchFields (Linhas 87-105)

**Propósito:** Buscar lista de campos metadata do backend

```typescript
const fetchFields = async () => {
  setLoading(true);
  try {
    const response = await axios.get(`${API_URL}/metadata-fields/`, {
      timeout: 30000,  // 30 segundos (pode consultar múltiplos arquivos SSH)
    });

    if (response.data.success) {
      setFields(response.data.fields);
    }
  } catch (error: any) {
    if (error.code === 'ECONNABORTED') {
      // Tratamento específico para timeout
      message.error('Tempo esgotado ao carregar campos (servidor lento)');
    } else {
      message.error('Erro ao carregar campos: ' + error.message);
    }
  } finally {
    setLoading(false);
  }
};
```

**Observação:** Timeout de 30 segundos porque pode precisar consultar múltiplos servidores via SSH.

### FUNÇÃO fetchServers (Linhas 107-126)

**Propósito:** Buscar lista de servidores Prometheus (master + slaves)

```typescript
const fetchServers = async () => {
  try {
    const response = await axios.get(`${API_URL}/metadata-fields/servers`, {
      timeout: 15000,  // 15 segundos (consulta Consul + SSH)
    });

    if (response.data.success) {
      setServers(response.data.servers);

      // Selecionar master por padrão
      if (response.data.master) {
        setSelectedServer(response.data.master.id);
      }
    }
  } catch (error: any) {
    // Tratamento de erro similar
  }
};
```

**Fluxo:**
1. Busca servidores Prometheus configurados
2. Identifica qual é o master
3. Seleciona master automaticamente no dropdown

### HOOKS useEffect (Linhas 128-137)

```typescript
// Linha 128-130: Carregar servidores ao montar componente
useEffect(() => {
  fetchServers();
}, []);

// Linhas 132-137: Recarregar campos quando trocar de servidor
useEffect(() => {
  if (selectedServer) {
    fetchFields();
  }
}, [selectedServer]);
```

**Comportamento:**
- Ao abrir a página → busca lista de servidores
- Ao trocar servidor no dropdown → recarrega campos daquele servidor

### FUNÇÃO handleCreateField (Linhas 139-166)

**Propósito:** Criar novo campo metadata e sincronizar com Prometheus

```typescript
const handleCreateField = async (values: any) => {
  try {
    const response = await axios.post(`${API_URL}/metadata-fields/`, {
      field: {
        ...values,
        // Gera automaticamente source_label baseado no nome
        source_label: `__meta_consul_service_metadata_${values.name}`,
      },
      sync_prometheus: true  // Sincroniza com prometheus.yml
    });

    if (response.data.success) {
      message.success(`Campo '${values.display_name}' criado com sucesso!`);
      fetchFields();  // Recarrega lista
      setCreateModalVisible(false);  // Fecha modal

      // Pergunta se quer replicar para slaves
      Modal.confirm({
        title: 'Replicar para servidores slaves?',
        content: 'Deseja replicar este campo para todos os servidores slaves?',
        okText: 'Sim, replicar',
        cancelText: 'Não',
        onOk: () => handleReplicateToSlaves(),
      });
    }
  } catch (error: any) {
    message.error('Erro ao criar campo: ' + error.message);
  }
};
```

**Fluxo após criar campo:**
1. Salva no `metadata_fields.json`
2. Adiciona `relabel_config` no prometheus.yml do master
3. Valida e recarrega Prometheus
4. Pergunta se quer replicar para slaves
5. Se sim → repete processo em todos os slaves

### FUNÇÃO handleEditField (Linhas 168-183)

**Propósito:** Atualizar campo metadata existente

```typescript
const handleEditField = async (values: any) => {
  if (!editingField) return;

  try {
    const response = await axios.put(
      `${API_URL}/metadata-fields/${editingField.name}`,
      values
    );

    if (response.data.success) {
      message.success(`Campo '${values.display_name}' atualizado com sucesso!`);
      fetchFields();
      setEditModalVisible(false);
      setEditingField(null);
    }
  } catch (error: any) {
    message.error('Erro ao atualizar campo: ' + error.message);
  }
};
```

**Limitação:** Edição **NÃO** modifica `source_label` (apenas metadata do campo)

### FUNÇÃO handleDeleteField (Linhas 185-196)

**Propósito:** Deletar campo metadata (apenas não obrigatórios)

```typescript
const handleDeleteField = async (fieldName: string) => {
  try {
    const response = await axios.delete(`${API_URL}/metadata-fields/${fieldName}`);

    if (response.data.success) {
      message.success(`Campo deletado com sucesso!`);
      fetchFields();
    }
  } catch (error: any) {
    message.error('Erro ao deletar campo: ' + error.message);
  }
};
```

**Proteção:** Campos com `required: true` não podem ser deletados (botão delete desabilitado na UI)

### FUNÇÃO handleReplicateToSlaves (Linhas 198-227)

**Propósito:** Replicar configurações do Master para todos os Slaves

```typescript
const handleReplicateToSlaves = async () => {
  const hide = message.loading('Replicando configurações...', 0);

  try {
    const response = await axios.post(`${API_URL}/metadata-fields/replicate-to-slaves`, {});

    hide();

    if (response.data.success) {
      const successCount = response.data.results.filter(r => r.success).length;

      // Modal com resultado detalhado de cada servidor
      Modal.success({
        title: 'Replicação Concluída',
        content: (
          <div>
            <p>{response.data.message}</p>
            <ul>
              {response.data.results.map((r: any, idx: number) => (
                <li key={idx} style={{ color: r.success ? 'green' : 'red' }}>
                  {r.server}: {r.success ? r.message : r.error}
                </li>
              ))}
            </ul>
          </div>
        ),
      });
    }
  } catch (error: any) {
    hide();
    message.error('Erro ao replicar: ' + error.message);
  }
};
```

**O que faz:**
1. Pega `prometheus.yml` do master
2. Copia `relabel_configs` para cada slave
3. Valida em cada slave com `promtool`
4. Salva se validação OK
5. Recarrega Prometheus em cada slave
6. Retorna resultado individual de cada servidor

### CONFIGURAÇÃO DE COLUNAS DA TABELA (Linhas 230-318)

```typescript
const columns: ProColumns<MetadataField>[] = [
  // COLUNA 1: Ordem (Linhas 231-236)
  {
    title: 'Ordem',
    dataIndex: 'order',
    width: 70,
    render: (order) => <Badge count={order} style={{ backgroundColor: '#1890ff' }} />,
    // Exibe número em badge azul
  },

  // COLUNA 2: Nome Técnico (Linhas 237-242)
  {
    title: 'Nome Técnico',
    dataIndex: 'name',
    width: 180,
    render: (name) => <code>{name}</code>,
    // Exibe com estilo monospace (ex: company, env, project)
  },

  // COLUNA 3: Nome de Exibição (Linhas 243-248)
  {
    title: 'Nome de Exibição',
    dataIndex: 'display_name',
    width: 180,
    render: (text) => <strong>{text}</strong>,
    // Exibe em negrito (ex: Empresa, Ambiente, Projeto)
  },

  // COLUNA 4: Tipo (Linhas 249-263)
  {
    title: 'Tipo',
    dataIndex: 'field_type',
    width: 100,
    render: (type) => {
      const colors: Record<string, string> = {
        string: 'default',  // cinza
        number: 'blue',     // azul
        select: 'purple',   // roxo
        text: 'green',      // verde
        url: 'orange',      // laranja
      };
      return <Tag color={colors[type] || 'default'}>{type}</Tag>;
    },
  },

  // COLUNA 5: Categoria (Linhas 264-269)
  {
    title: 'Categoria',
    dataIndex: 'category',
    width: 120,
    render: (cat) => <Tag>{cat}</Tag>,
    // infrastructure, basic, device, extra
  },

  // COLUNA 6: Obrigatório (Linhas 270-275)
  {
    title: 'Obrigatório',
    dataIndex: 'required',
    width: 100,
    render: (req) => req ? <Tag color="red">Sim</Tag> : <Tag>Não</Tag>,
  },

  // COLUNA 7: Visibilidade (Linhas 276-286)
  {
    title: 'Visibilidade',
    width: 150,
    render: (_, record) => (
      <Space size={4}>
        {record.show_in_table && <Tag color="blue">Tabela</Tag>}
        {record.show_in_dashboard && <Tag color="green">Dashboard</Tag>}
        {record.show_in_form && <Tag color="orange">Form</Tag>}
      </Space>
    ),
    // Mostra onde o campo aparece no sistema
  },

  // COLUNA 8: Ações (Linhas 287-318)
  {
    title: 'Ações',
    width: 150,
    fixed: 'right',
    render: (_, record) => (
      <Space>
        {/* BOTÃO EDITAR */}
        <Tooltip title="Editar">
          <Button
            type="link"
            icon={<EditOutlined />}
            onClick={() => {
              setEditingField(record);
              setEditModalVisible(true);
            }}
          />
        </Tooltip>

        {/* BOTÃO DELETAR (só se NÃO for obrigatório) */}
        {!record.required && (
          <Popconfirm
            title="Tem certeza que deseja deletar este campo?"
            onConfirm={() => handleDeleteField(record.name)}
            okText="Sim"
            cancelText="Não"
          >
            <Tooltip title="Deletar">
              <Button type="link" danger icon={<DeleteOutlined />} />
            </Tooltip>
          </Popconfirm>
        )}
      </Space>
    ),
  },
];
```

### FUNÇÕES DE REINICIALIZAÇÃO (Linhas 320-388)

#### handleRestartSelected (Linhas 320-350)

**Propósito:** Reiniciar Prometheus apenas no servidor selecionado

```typescript
const handleRestartSelected = async () => {
  const selectedServerObj = servers.find(s => s.id === selectedServer);

  if (!selectedServerObj) {
    message.error('Nenhum servidor selecionado');
    return;
  }

  Modal.confirm({
    title: 'Confirmar Reinicialização',
    content: `Deseja reiniciar o Prometheus no servidor ${selectedServerObj.hostname}?`,
    okText: 'Sim, reiniciar',
    cancelText: 'Cancelar',
    onOk: async () => {
      const hide = message.loading(`Reiniciando Prometheus em ${selectedServerObj.hostname}...`, 0);

      try {
        const response = await axios.post(`${API_URL}/metadata-fields/restart-prometheus`, {
          server_ids: [selectedServer]  // Apenas 1 servidor
        });

        hide();

        if (response.data.success) {
          message.success(`Prometheus reiniciado com sucesso em ${selectedServerObj.hostname}`);
        }
      } catch (error: any) {
        hide();
        message.error('Erro ao reiniciar: ' + error.message);
      }
    },
  });
};
```

**Comando executado:** `ssh root@hostname "systemctl restart prometheus"`

#### handleRestartAll (Linhas 352-388)

**Propósito:** Reiniciar Prometheus em TODOS os servidores (master + slaves)

```typescript
const handleRestartAll = async () => {
  Modal.confirm({
    title: 'Confirmar Reinicialização em Todos os Servidores',
    content: `Deseja reiniciar o Prometheus em TODOS os ${servers.length} servidores (Master + Slaves)?`,
    okText: 'Sim, reiniciar todos',
    cancelText: 'Cancelar',
    onOk: async () => {
      const hide = message.loading('Reiniciando Prometheus em todos os servidores...', 0);

      try {
        const response = await axios.post(`${API_URL}/metadata-fields/restart-prometheus`, {});
          // ↑ Sem server_ids = reinicia TODOS

        hide();

        if (response.data.success) {
          // Modal com resultado individual de cada servidor
          Modal.success({
            title: 'Reinicialização Concluída',
            content: (
              <div>
                <p>{response.data.message}</p>
                <ul>
                  {response.data.results.map((r: any, idx: number) => (
                    <li key={idx} style={{ color: r.success ? 'green' : 'red' }}>
                      {r.server}: {r.success ? r.message : r.error}
                    </li>
                  ))}
                </ul>
              </div>
            ),
          });
        }
      } catch (error: any) {
        hide();
        message.error('Erro ao reiniciar: ' + error.message);
      }
    },
  });
};
```

**Uso típico:** Após adicionar novo campo ou fazer mudanças em massa

### RENDERIZAÇÃO DA UI (Linhas 390-625)

#### PageContainer Header (Linhas 391-401)

```typescript
<PageContainer
  title={
    <div>
      <div style={{ fontSize: 20, fontWeight: 500, marginBottom: 4 }}>
        Gerenciamento de Campos Metadata
      </div>
      <div style={{ fontSize: 14, fontWeight: 400, color: 'rgba(0, 0, 0, 0.45)' }}>
        Adicionar, editar e sincronizar campos metadata em todos os servidores
      </div>
    </div>
  }
```

**Visual:** Título grande + subtítulo cinza

#### Barra de Ações (extra) (Linhas 402-456)

```typescript
extra={[
  // BOTÃO 1: Seletor de Servidor (Linhas 403-419)
  <Select
    key="server-select"
    style={{ width: 350 }}
    value={selectedServer}
    onChange={setSelectedServer}
  >
    {servers.map(server => (
      <Select.Option key={server.id} value={server.id}>
        <CloudServerOutlined /> <strong>{server.display_name}</strong>
        <span style={{ marginLeft: 8, color: '#999' }}>
          ({server.type === 'master' ? '🟢 Master' : '🔵 Slave'})
        </span>
      </Select.Option>
    ))}
  </Select>,

  // BOTÃO 2: Replicar Master → Slaves (Linhas 420-428)
  <Button
    key="replicate"
    icon={<CloudSyncOutlined />}
    onClick={handleReplicateToSlaves}
    title="Replica configurações do Master para todos os Slaves"
  >
    Master → Slaves
  </Button>,

  // BOTÕES 3 e 4: Reiniciar Prometheus (Linhas 429-447)
  <Space.Compact key="restart-group">
    <Button
      icon={<ReloadOutlined />}
      onClick={handleRestartSelected}
      title="Reiniciar Prometheus apenas no servidor selecionado"
    >
      Reiniciar Selecionado
    </Button>
    <Button
      icon={<ReloadOutlined />}
      onClick={handleRestartAll}
      danger  // ← Botão vermelho (ação perigosa)
      title="Reiniciar Prometheus em todos os servidores"
    >
      Reiniciar Todos
    </Button>
  </Space.Compact>,

  // BOTÃO 5: Adicionar Campo (Linhas 448-455)
  <Button
    key="add"
    type="primary"
    icon={<PlusOutlined />}
    onClick={() => setCreateModalVisible(true)}
  >
    Adicionar Campo
  </Button>,
]}
```

**Organização visual:**
```
[Dropdown Servidor] [Master→Slaves] [Reiniciar Selecionado|Reiniciar Todos] [➕ Adicionar Campo]
     350px              120px                 190px + 140px                         140px
```

#### Alert de Informação (Linhas 458-475)

```typescript
{selectedServer && servers.length > 0 && (
  <Alert
    message={
      <span>
        <strong>Servidor Ativo:</strong> {servers.find(s => s.id === selectedServer)?.display_name}
        <Badge
          status={servers.find(s => s.id === selectedServer)?.type === 'master' ? 'success' : 'processing'}
          text={servers.find(s => s.id === selectedServer)?.type === 'master' ? 'Master' : 'Slave'}
          style={{ marginLeft: 16 }}
        />
      </span>
    }
    description={`Total de servidores disponíveis: ${servers.length} (1 master + ${servers.length - 1} slaves)`}
    type="info"
    showIcon
    style={{ marginBottom: 16 }}
  />
)}
```

**Exibe:**
- Servidor atualmente ativo
- Badge verde (Master) ou azul (Slave)
- Total de servidores disponíveis

#### ProTable (Linhas 477-494)

```typescript
<ProCard>
  <ProTable<MetadataField>
    columns={columns}           // Colunas definidas anteriormente
    dataSource={fields}         // Dados carregados do backend
    rowKey="name"               // Key única (nome técnico)
    loading={loading}           // Loading spinner
    search={false}              // Desabilita barra de busca
    options={{
      reload: fetchFields,      // Botão reload chama fetchFields
    }}
    pagination={{
      defaultPageSize: 20,
      showSizeChanger: true,
      pageSizeOptions: ['10', '20', '30', '50', '100'],
    }}
    scroll={{ x: 1400 }}        // Scroll horizontal se necessário
  />
</ProCard>
```

#### Modal Criar Campo (Linhas 496-563)

```typescript
<ModalForm
  title="Adicionar Novo Campo Metadata"
  open={createModalVisible}
  onOpenChange={setCreateModalVisible}
  onFinish={handleCreateField}
  modalProps={{ width: 600 }}
>
  {/* CAMPO 1: Nome Técnico */}
  <ProFormText
    name="name"
    label="Nome Técnico"
    placeholder="ex: datacenter"
    rules={[{
      required: true,
      pattern: /^[a-z_]+$/,  // Apenas letras minúsculas e underscore
      message: 'Apenas letras minúsculas e underscore'
    }]}
    tooltip="Nome técnico usado internamente (apenas letras minúsculas e _)"
  />

  {/* CAMPO 2: Nome de Exibição */}
  <ProFormText
    name="display_name"
    label="Nome de Exibição"
    placeholder="ex: Data Center"
    rules={[{ required: true }]}
    tooltip="Nome amigável que aparece na interface"
  />

  {/* CAMPO 3: Descrição */}
  <ProFormTextArea
    name="description"
    label="Descrição"
    placeholder="Descrição do campo"
    rows={2}
  />

  {/* CAMPO 4: Tipo do Campo */}
  <ProFormSelect
    name="field_type"
    label="Tipo do Campo"
    options={[
      { label: 'Texto (string)', value: 'string' },
      { label: 'Número (number)', value: 'number' },
      { label: 'Seleção (select)', value: 'select' },
      { label: 'Texto Longo (text)', value: 'text' },
      { label: 'URL (url)', value: 'url' },
    ]}
    rules={[{ required: true }]}
  />

  {/* CAMPO 5: Categoria */}
  <ProFormSelect
    name="category"
    label="Categoria"
    options={[
      { label: 'Infraestrutura', value: 'infrastructure' },
      { label: 'Básico', value: 'basic' },
      { label: 'Dispositivo', value: 'device' },
      { label: 'Extras', value: 'extra' },
    ]}
    initialValue="extra"
    rules={[{ required: true }]}
  />

  {/* CAMPO 6: Ordem */}
  <ProFormDigit
    name="order"
    label="Ordem"
    min={1}
    max={999}
    initialValue={23}  // Próximo campo depois dos existentes
    fieldProps={{ precision: 0 }}  // Sem decimais
  />

  {/* SWITCHES DE CONFIGURAÇÃO */}
  <ProFormSwitch name="required" label="Campo Obrigatório" initialValue={false} />
  <ProFormSwitch name="show_in_table" label="Mostrar em Tabelas" initialValue={true} />
  <ProFormSwitch name="show_in_dashboard" label="Mostrar no Dashboard" initialValue={false} />
  <ProFormSwitch name="show_in_form" label="Mostrar em Formulários" initialValue={true} />
  <ProFormSwitch name="editable" label="Editável" initialValue={true} />
</ModalForm>
```

**Validações:**
- `name`: Apenas `[a-z_]` (ex: datacenter, cod_localidade)
- `display_name`: Obrigatório
- `field_type`: Obrigatório (um dos 5 tipos)
- `category`: Obrigatório (uma das 4 categorias)
- `order`: Numérico de 1 a 999

#### Modal Editar Campo (Linhas 565-622)

```typescript
<ModalForm
  title={`Editar Campo: ${editingField?.display_name}`}
  open={editModalVisible}
  onOpenChange={(visible) => {
    setEditModalVisible(visible);
    if (!visible) setEditingField(null);  // Limpa ao fechar
  }}
  onFinish={handleEditField}
  initialValues={editingField || {}}  // Preenche com valores atuais
  modalProps={{ width: 600 }}
>
  {/* Nome Técnico - READONLY */}
  <ProFormText name="name" label="Nome Técnico" disabled />

  {/* Campos editáveis (mesmos do modal criar) */}
  <ProFormText name="display_name" label="Nome de Exibição" rules={[{ required: true }]} />
  <ProFormTextArea name="description" label="Descrição" rows={2} />
  <ProFormSelect name="field_type" label="Tipo do Campo" {...} />
  <ProFormSelect name="category" label="Categoria" {...} />
  <ProFormDigit name="order" label="Ordem" {...} />
  <ProFormSwitch name="required" label="Campo Obrigatório" />
  <ProFormSwitch name="show_in_table" label="Mostrar em Tabelas" />
  <ProFormSwitch name="show_in_dashboard" label="Mostrar no Dashboard" />
  <ProFormSwitch name="show_in_form" label="Mostrar em Formulários" />
  <ProFormSwitch name="editable" label="Editável" />

  {/* Source Label - READONLY */}
  <ProFormText name="source_label" label="Source Label" disabled />
</ModalForm>
```

**Diferenças do modal criar:**
- `name` é readonly (não pode mudar nome técnico)
- `source_label` é readonly (gerado automaticamente)
- Valores pré-preenchidos com dados atuais

---

## 🔄 CASOS DE USO E FLUXOS

### CASO 1: Adicionar Novo Campo "datacenter"

**Cenário:** Empresa tem múltiplos datacenters e quer rastrear isso no Prometheus

**Passo a passo:**

1. **Usuário clica "Adicionar Campo"**
   ```typescript
   onClick={() => setCreateModalVisible(true)}
   ```

2. **Preenche formulário:**
   ```
   Nome Técnico: datacenter
   Nome de Exibição: Data Center
   Descrição: Localização do datacenter (SP, RJ, US-EAST)
   Tipo: select
   Categoria: infrastructure
   Ordem: 23
   Switches:
     ✅ show_in_table
     ✅ show_in_form
     ❌ show_in_dashboard
     ❌ required
   ```

3. **Clica "Salvar" → handleCreateField é chamado**
   ```typescript
   POST /api/v1/metadata-fields/
   Body: {
     field: {
       name: "datacenter",
       display_name: "Data Center",
       description: "...",
       source_label: "__meta_consul_service_metadata_datacenter",  // ← Gerado automaticamente
       field_type: "select",
       // ... outros campos
     },
     sync_prometheus: true
   }
   ```

4. **Backend faz (automaticamente):**
   ```python
   # 1. Salva em metadata_fields.json
   config["fields"].append(new_field)
   save_json(config)

   # 2. SSH no servidor master
   ssh_client = connect_ssh("172.16.1.26", 5522, "root")

   # 3. Lê prometheus.yml
   prometheus_yml = read_file_via_sftp("/etc/prometheus/prometheus.yml")

   # 4. Adiciona relabel_config
   prometheus_yml["scrape_configs"][0]["relabel_configs"].append({
     "source_labels": ["__meta_consul_service_metadata_datacenter"],
     "target_label": "datacenter"
   })

   # 5. Valida YAML
   exec_ssh("promtool check config /etc/prometheus/prometheus.yml")

   # 6. Salva arquivo
   write_file_via_sftp("/etc/prometheus/prometheus.yml", prometheus_yml)

   # 7. Restaura permissões
   exec_ssh("chown prometheus:prometheus /etc/prometheus/prometheus.yml")

   # 8. Recarrega Prometheus
   exec_ssh("systemctl reload prometheus")
   ```

5. **Modal de confirmação aparece:**
   ```
   ┌─────────────────────────────────────────┐
   │ Replicar para servidores slaves?        │
   │                                         │
   │ Deseja replicar este campo para        │
   │ todos os servidores slaves?            │
   │                                         │
   │        [Não]        [Sim, replicar]    │
   └─────────────────────────────────────────┘
   ```

6. **Se usuário clicar "Sim, replicar":**
   ```typescript
   POST /api/v1/metadata-fields/replicate-to-slaves

   // Backend repete passos 3-8 para cada servidor slave
   ```

7. **Resultado:**
   ```
   ┌─────────────────────────────────────────┐
   │ ✓ Replicação Concluída                 │
   │                                         │
   │ Campos replicados com sucesso!         │
   │                                         │
   │ • 172.16.1.26 (Master): ✓ Sucesso      │
   │ • 172.16.200.14 (Slave): ✓ Sucesso     │
   │                                         │
   │                          [OK]           │
   └─────────────────────────────────────────┘
   ```

8. **Agora o campo está disponível em:**
   - ✅ Página Services (coluna "Data Center")
   - ✅ Página Exporters (coluna "Data Center")
   - ✅ Formulários de criar/editar serviço
   - ✅ Queries Prometheus (`datacenter="SP"`)
   - ✅ Dashboards Grafana

### CASO 2: Editar Campo Existente "company"

**Cenário:** Mudar nome de exibição de "Empresa" para "Cliente"

**Passo a passo:**

1. **Usuário clica ícone ✏️ na linha do campo "company"**
   ```typescript
   onClick={() => {
     setEditingField(record);  // record = campo company
     setEditModalVisible(true);
   }}
   ```

2. **Modal abre com valores atuais pré-preenchidos**
   ```
   Nome Técnico: company (readonly)
   Nome de Exibição: Empresa ← MUDA PARA "Cliente"
   Descrição: Nome da empresa
   Tipo: string
   ... outros campos ...
   Source Label: __meta_consul_service_metadata_company (readonly)
   ```

3. **Clica "Salvar" → handleEditField é chamado**
   ```typescript
   PUT /api/v1/metadata-fields/company
   Body: {
     display_name: "Cliente",  // ← Valor alterado
     // ... outros valores iguais
   }
   ```

4. **Backend atualiza apenas metadata_fields.json**
   ```python
   # NÃO modifica prometheus.yml
   # NÃO reinicia Prometheus
   # Apenas atualiza JSON local
   ```

5. **Próxima vez que usuário recarregar página Services:**
   ```
   Coluna "Empresa" → agora aparece "Cliente"
   ```

**Limitação:** Edição **não** altera `source_label` no Prometheus. Para isso, precisa deletar e recriar campo.

### CASO 3: Deletar Campo "notas"

**Cenário:** Campo "notas" não está sendo usado, quer remover

**Passo a passo:**

1. **Usuário clica ícone 🗑️ na linha do campo "notas"**
   ```typescript
   <Popconfirm
     title="Tem certeza que deseja deletar este campo?"
     onConfirm={() => handleDeleteField("notas")}
   >
   ```

2. **Confirmação aparece:**
   ```
   ┌─────────────────────────────────────────┐
   │ ⚠ Tem certeza que deseja deletar       │
   │   este campo?                           │
   │                                         │
   │        [Não]        [Sim]              │
   └─────────────────────────────────────────┘
   ```

3. **Se clicar "Sim" → handleDeleteField é chamado**
   ```typescript
   DELETE /api/v1/metadata-fields/notas
   ```

4. **Backend faz:**
   ```python
   # 1. Remove de metadata_fields.json
   config["fields"] = [f for f in config["fields"] if f["name"] != "notas"]
   save_json(config)

   # 2. Remove relabel_config do prometheus.yml (se existir)
   # 3. Recarrega Prometheus
   ```

5. **Campo desaparece da tabela e de todas as páginas do sistema**

**Proteção:** Campos com `required: true` não podem ser deletados (botão desabilitado)

### CASO 4: Replicar Master → Slaves

**Cenário:** Após adicionar vários campos no Master, quer sincronizar com Slaves

**Passo a passo:**

1. **Usuário clica botão "Master → Slaves"**
   ```typescript
   onClick={handleReplicateToSlaves}
   ```

2. **Loader aparece:**
   ```
   ⏳ Replicando configurações...
   ```

3. **Backend faz (para cada slave):**
   ```python
   for slave in slaves:
     # 1. Conecta via SSH
     ssh = connect_ssh(slave.hostname, slave.port, slave.username)

     # 2. Lê prometheus.yml do master
     master_yml = read_prometheus_yml(master)

     # 3. Extrai relabel_configs do master
     master_relabels = master_yml["scrape_configs"][0]["relabel_configs"]

     # 4. Lê prometheus.yml do slave
     slave_yml = read_prometheus_yml(slave)

     # 5. Substitui relabel_configs do slave pelos do master
     slave_yml["scrape_configs"][0]["relabel_configs"] = master_relabels

     # 6. Valida YAML
     validate_yaml(slave_yml)

     # 7. Salva se validação OK
     write_prometheus_yml(slave, slave_yml)

     # 8. Recarrega Prometheus
     exec_ssh(slave, "systemctl reload prometheus")
   ```

4. **Modal com resultado aparece:**
   ```
   ┌─────────────────────────────────────────┐
   │ ✓ Replicação Concluída                 │
   │                                         │
   │ Campos replicados com sucesso!         │
   │                                         │
   │ • 172.16.1.26 (Master): ✓ Sucesso      │
   │ • 172.16.200.14 (Slave 1): ✓ Sucesso   │
   │ • 172.16.200.15 (Slave 2): ✓ Sucesso   │
   │                                         │
   │                          [OK]           │
   └─────────────────────────────────────────┘
   ```

5. **Agora todos os slaves têm os mesmos campos do master**

### CASO 5: Reiniciar Prometheus

**Cenário:** Após fazer mudanças manuais em prometheus.yml, quer reiniciar serviço

**Opção A: Reiniciar apenas servidor selecionado**

1. **Seleciona servidor no dropdown** (ex: 172.16.200.14)
2. **Clica "Reiniciar Selecionado"**
3. **Confirmação aparece:**
   ```
   ┌─────────────────────────────────────────┐
   │ ⚠ Confirmar Reinicialização            │
   │                                         │
   │ Deseja reiniciar o Prometheus no       │
   │ servidor 172.16.200.14?                │
   │                                         │
   │     [Cancelar]    [Sim, reiniciar]     │
   └─────────────────────────────────────────┘
   ```
4. **Se confirmar:**
   ```
   ⏳ Reiniciando Prometheus em 172.16.200.14...
   ✓ Prometheus reiniciado com sucesso em 172.16.200.14
   ```

**Opção B: Reiniciar TODOS os servidores**

1. **Clica "Reiniciar Todos" (botão vermelho)**
2. **Confirmação aparece:**
   ```
   ┌─────────────────────────────────────────┐
   │ ⚠ Confirmar Reinicialização em Todos   │
   │                                         │
   │ Deseja reiniciar o Prometheus em       │
   │ TODOS os 3 servidores (Master + Slaves)?│
   │                                         │
   │     [Cancelar]    [Sim, reiniciar todos]│
   └─────────────────────────────────────────┘
   ```
3. **Se confirmar:**
   ```
   ⏳ Reiniciando Prometheus em todos os servidores...

   ┌─────────────────────────────────────────┐
   │ ✓ Reinicialização Concluída            │
   │                                         │
   │ Serviços reiniciados:                  │
   │                                         │
   │ • 172.16.1.26 (Master): ✓ Sucesso      │
   │ • 172.16.200.14 (Slave 1): ✓ Sucesso   │
   │ • 172.16.200.15 (Slave 2): ✓ Sucesso   │
   │                                         │
   │                          [OK]           │
   └─────────────────────────────────────────┘
   ```

---

## 🔗 INTEGRAÇÃO COM OUTRAS PÁGINAS

### Services.tsx

```typescript
// Services.tsx usa os campos definidos em MetadataFields para:

// 1. Gerar colunas da tabela dinamicamente
const columns = metadataFields
  .filter(field => field.show_in_table)
  .map(field => ({
    title: field.display_name,
    dataIndex: field.name,
    // ...
  }));

// 2. Gerar campos do formulário de criar/editar
const formFields = metadataFields
  .filter(field => field.show_in_form)
  .map(field => (
    <ProFormText
      name={field.name}
      label={field.display_name}
      required={field.required}
      // ...
    />
  ));

// 3. Validar dados obrigatórios
const validateService = (data) => {
  const requiredFields = metadataFields.filter(f => f.required);

  for (const field of requiredFields) {
    if (!data[field.name]) {
      throw new Error(`Campo ${field.display_name} é obrigatório`);
    }
  }
};
```

### Dashboard.tsx

```typescript
// Dashboard.tsx usa os campos para:

// 1. Gerar filtros dinâmicos
const filters = metadataFields
  .filter(field => field.show_in_dashboard)
  .map(field => ({
    label: field.display_name,
    value: field.name,
    type: field.field_type,
    options: field.options,
  }));

// 2. Agrupar métricas por campo
const groupByField = metadataFields.find(f => f.name === groupBy);
const metrics = await fetchMetrics({ groupBy: groupByField.source_label });
```

### Exporters.tsx

```typescript
// Similar ao Services.tsx, usa campos para tabela e formulários
```

### PrometheusConfig.tsx

```typescript
// PrometheusConfig.tsx lê os relabel_configs gerados automaticamente
// Não edita metadata_fields.json diretamente
```

---

## 💡 PADRÕES E BEST PRACTICES IDENTIFICADOS

### 1. Timeout Generoso para Operações SSH

```typescript
const response = await axios.get(`${API_URL}/metadata-fields/servers`, {
  timeout: 15000,  // 15 segundos
});
```

**Motivo:** Operações SSH podem ser lentas, especialmente se:
- Servidor remoto está sobrecarregado
- Rede está com latência alta
- Precisa consultar múltiplos servidores

### 2. Modal de Confirmação para Ações Destrutivas

```typescript
<Popconfirm
  title="Tem certeza que deseja deletar este campo?"
  onConfirm={() => handleDeleteField(record.name)}
>
```

**Proteções:**
- Delete de campo → Popconfirm
- Reiniciar servidor → Modal.confirm
- Reiniciar todos → Modal.confirm com texto destacado

### 3. Feedback Detalhado de Operações Multi-Servidor

```typescript
Modal.success({
  content: (
    <ul>
      {results.map(r => (
        <li style={{ color: r.success ? 'green' : 'red' }}>
          {r.server}: {r.success ? r.message : r.error}
        </li>
      ))}
    </ul>
  ),
});
```

**Benefício:** Usuário vê exatamente qual servidor teve sucesso/falha

### 4. Geração Automática de source_label

```typescript
source_label: `__meta_consul_service_metadata_${values.name}`,
```

**Convenção Prometheus:**
- Campos Consul metadata sempre começam com `__meta_consul_service_metadata_`
- Target label é o nome do campo sem prefixo
- Exemplo: `__meta_consul_service_metadata_company` → `company`

### 5. Validação Regex para Nome Técnico

```typescript
rules={[{
  required: true,
  pattern: /^[a-z_]+$/,
  message: 'Apenas letras minúsculas e underscore'
}]}
```

**Motivo:** Prometheus labels devem seguir convenção `[a-z_]`

### 6. Auto-Seleção do Master

```typescript
if (response.data.master) {
  setSelectedServer(response.data.master.id);
}
```

**UX:** Usuário não precisa selecionar master manualmente, já vem selecionado

### 7. Desabilitar Delete para Campos Obrigatórios

```typescript
{!record.required && (
  <Popconfirm {...}>
    <Button type="link" danger icon={<DeleteOutlined />} />
  </Popconfirm>
)}
```

**Proteção:** Campos como `instance`, `company`, `env` não podem ser deletados

---

## 🎯 POSSÍVEIS MELHORIAS FUTURAS

### 1. **Bulk Edit**
Editar múltiplos campos de uma vez (ex: mudar categoria de 5 campos)

### 2. **Import/Export**
Exportar configuração de campos para JSON e importar em outro ambiente

### 3. **Histórico de Mudanças**
Log de quem adicionou/editou/deletou cada campo e quando

### 4. **Preview de Impacto**
Antes de adicionar campo, mostrar:
- Quantos serviços serão afetados
- Quais jobs do Prometheus receberão o campo
- Estimativa de tempo de replicação

### 5. **Validação de Duplicados**
Impedir criação de campo com nome já existente

### 6. **Opções Dinâmicas para Select**
Buscar opções de um endpoint (ex: lista de datacenters do Consul)

### 7. **Reorder via Drag-and-Drop**
Arrastar campos para reordenar (atualiza campo `order`)

### 8. **Rollback**
Desfazer última mudança (adicionar/editar/deletar campo)

### 9. **Dry-Run Mode**
Simular operação sem realmente executar (útil para testar replicação)

### 10. **Notificações**
Email/Slack quando campo é adicionado ou replicação falha

---

## 🔍 PERGUNTAS PARA O USUÁRIO

Agora que analisei completamente a página, tenho algumas perguntas para entender melhor o que você quer fazer:

### Perguntas Técnicas

1. **Qual funcionalidade está faltando** na página MetadataFields que você gostaria de adicionar?

2. **Há algum bug ou comportamento inesperado** que você notou?

3. **A UX está intuitiva** ou há alguma parte confusa para o usuário final (analista de infraestrutura)?

### Perguntas de Melhorias

4. **Quer implementar algo similar ao PrometheusConfig?**
   - Editor Monaco para editar metadata_fields.json?
   - Visualização de diff antes/depois?
   - Múltiplas visualizações (tabela, JSON, YAML)?

5. **Precisa de funcionalidades multi-servidor mais avançadas?**
   - Comparar campos entre master e slaves?
   - Detectar inconsistências?
   - Sincronização seletiva (apenas alguns campos)?

6. **Quer melhorar a parte de reinicialização?**
   - Adicionar validação antes de reiniciar?
   - Mostrar logs em tempo real do systemctl?
   - Rollback automático se reinicialização falhar?

### Perguntas de Priorização

7. **Qual é a tarefa MAIS IMPORTANTE** que você quer que eu faça nesta página?

8. **Há algo urgente** que precisa ser corrigido/implementado?

9. **Você quer que eu:**
   - 🔧 Corrija bugs
   - ✨ Adicione features novas
   - 🎨 Melhore a UI/UX
   - 📝 Adicione documentação
   - ⚡ Otimize performance

---

**Estou pronto para prosseguir com as tarefas! Me diga o que você precisa nesta página. 🚀**
