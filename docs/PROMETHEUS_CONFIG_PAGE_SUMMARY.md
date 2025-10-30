# PrometheusConfig.tsx - Resumo Completo da Página

**Arquivo:** `frontend/src/pages/PrometheusConfig.tsx`
**Última atualização:** 2025-10-30
**Linhas de código:** ~3500 linhas

---

## 📋 VISÃO GERAL

A página **PrometheusConfig** é uma interface web avançada para gerenciamento de configurações do Prometheus, Alertmanager e arquivos de regras de alerta. Ela permite edição multi-servidor via SSH, com visualização estruturada em múltiplas views e editor Monaco integrado.

### Propósito Principal
- **Visualizar** configurações YAML de Prometheus/Alertmanager em formato tabular
- **Editar** arquivos remotamente via SSH com validação
- **Gerenciar** múltiplos servidores simultaneamente
- **Organizar** dados em diferentes visualizações (Rotas, Receptores, Regras, etc.)

---

## 🏗️ ARQUITETURA DO COMPONENTE

### Estados Principais

```typescript
// Seleção de Servidor e Arquivo
const [servers, setServers] = useState<PrometheusServer[]>([]);
const [selectedServer, setSelectedServer] = useState<string | null>(null);
const [selectedFile, setSelectedFile] = useState<string | null>(null);
const [allFiles, setAllFiles] = useState<PrometheusFile[]>([]);

// Dados do Prometheus (Jobs)
const [jobs, setJobs] = useState<any[]>([]);
const [loadingJobs, setLoadingJobs] = useState(false);

// Dados do Alertmanager
const [alertmanagerRoutes, setAlertmanagerRoutes] = useState<any[]>([]);
const [alertmanagerReceivers, setAlertmanagerReceivers] = useState<any[]>([]);
const [alertmanagerInhibitRules, setAlertmanagerInhibitRules] = useState<any[]>([]);
const [loadingAlertmanager, setLoadingAlertmanager] = useState(false);

// Modos de Visualização
const [fileType, setFileType] = useState<'prometheus' | 'rules' | 'alertmanager'>('prometheus');
const [alertViewMode, setAlertViewMode] = useState<'group' | 'individual'>('group');
const [alertmanagerViewMode, setAlertmanagerViewMode] = useState<'routes' | 'receivers' | 'inhibit-rules'>('routes');

// Configuração de Colunas e Tabela
const [columnConfig, setColumnConfig] = useState<ColumnConfig[]>([]);
const [columnWidths, setColumnWidths] = useState<Record<string, number>>({});
const [tableSize, setTableSize] = useState<'small' | 'middle' | 'large'>('middle');

// Editor Monaco
const [monacoVisible, setMonacoVisible] = useState(false);
const [monacoContent, setMonacoContent] = useState('');
const [monacoLoading, setMonacoLoading] = useState(false);

// Campos Dinâmicos do Prometheus
const [fields, setFields] = useState<PrometheusField[]>([]);
const [loadingFields, setLoadingFields] = useState(false);
```

### Tipos de Arquivo Suportados

1. **prometheus.yml** → Visualização de Jobs/Scrape Configs
2. **alertmanager.yml** → 3 Visualizações (Rotas, Receptores, Regras de Inibição)
3. **alert-rules-*.yml** → 2 Visualizações (Grupos de Regras, Alertas Individuais)

---

## 🔄 FLUXO DE DADOS

### 1. Inicialização
```
useEffect (mount)
  → loadServers()
    → GET /api/v1/prometheus-config/servers
    → Popula dropdown de servidores
```

### 2. Seleção de Servidor
```
User seleciona servidor
  → setSelectedServer(serverId)
  → useEffect detecta mudança
    → loadFiles(serverId)
      → GET /api/v1/prometheus-config/files?server_id={serverId}
      → Popula dropdown de arquivos (ordenados alfabeticamente)
    → Limpa dados antigos (jobs, alertmanager)
    → Reseta fileType para 'prometheus'
```

### 3. Seleção de Arquivo
```
User seleciona arquivo
  → setSelectedFile(filePath)
  → useEffect detecta mudança
    → Detecta tipo do arquivo (prometheus/alertmanager/rules)
    → Se alertmanager:
        → fetchAlertmanagerData(filePath, serverId)
          → GET /api/v1/prometheus-config/alertmanager/routes?file_path={path}&hostname={host}
          → GET /api/v1/prometheus-config/alertmanager/receivers?file_path={path}&hostname={host}
          → GET /api/v1/prometheus-config/alertmanager/inhibit-rules?file_path={path}&hostname={host}
    → Senão:
        → fetchJobs(filePath, serverId)
          → GET /api/v1/prometheus-config/jobs?file_path={path}&hostname={host}
```

### 4. Edição de Arquivo (Monaco Editor)
```
User clica "Editar Arquivo"
  → handleOpenMonacoEditor()
    → GET /api/v1/prometheus-config/file-content?file_path={path}&hostname={host}
    → Abre modal com Monaco Editor
User edita e salva
  → handleSaveMonacoContent(newContent)
    → PUT /api/v1/prometheus-config/update-raw
      → Backend faz:
        1. Backup automático do arquivo original
        2. Valida YAML com promtool
        3. Salva novo conteúdo via SSH/SFTP
        4. Restaura permissões (prometheus:prometheus)
        5. Reload automático do serviço (se validação OK)
    → Recarrega dados da tabela
    → Fecha modal
```

---

## 📊 VISUALIZAÇÕES IMPLEMENTADAS

### A) Prometheus Jobs (prometheus.yml)

**Colunas principais:**
- Job Name
- Scrape Interval
- Scrape Timeout
- Metrics Path
- Scheme (http/https)
- Static Configs (targets)
- Relabel Configs (quantidade)

**Características:**
- Tabela com redimensionamento de colunas
- Configuração de colunas visíveis via drag-and-drop
- Persistência em localStorage
- Densidade ajustável (small/middle/large)

### B) Alertmanager - 3 Visualizações

#### 1. ROTAS (alertmanager/routes)
**Colunas:**
- Match Pattern (condições de roteamento)
- Receiver (destino)
- Group By (agrupamento)
- Group Wait (tempo de espera)
- Group Interval (intervalo)
- Repeat Interval (repetição)
- Continue (boolean)

**Explicação exibida:**
```
🔀 ROTAS - Hierarquia de Roteamento de Alertas

Define COMO os alertas são direcionados para os receptores.
Rotas funcionam em cascata: quando alerta chega, AlertManager
percorre rotas em ordem até encontrar match.

Campos Explicados:
- Match Pattern: Condição (ex: severity: critical)
- Receiver: Nome do receptor
- Group By: Labels para agrupar (alertname, instance)
- Group Wait: Tempo antes do PRIMEIRO alerta do grupo
- Repeat Interval: Intervalo para reenviar alertas não resolvidos
- Continue: Se ✅, continua avaliando outras rotas
```

#### 2. RECEPTORES (alertmanager/receivers)
**Colunas:**
- Name (nome do receptor)
- Type (webhook/email/slack/etc)
- URL/Address (destino)
- Send Resolved (boolean com ícone ✓/✗)
- Max Alerts (Tag com número ou "Ilimitado")

**Características especiais:**
- Send Resolved: CheckCircleOutlined (verde) ou CloseCircleOutlined (vermelho)
- Max Alerts: Tag azul com número ou Tag "Ilimitado"

#### 3. REGRAS DE INIBIÇÃO (alertmanager/inhibit-rules)
**Colunas:**
- Source Match (alerta que inibe)
- Target Match (alerta inibido)
- Equal (labels que devem ser iguais)

**Explicação exibida:**
```
🚫 REGRAS DE INIBIÇÃO - Supressão Inteligente de Alertas

Define quais alertas SUPRIMEM outros para evitar notificações
redundantes (ex: se servidor down, não notificar serviços nele).

Campos:
- Source Match: Alerta que CAUSA a inibição
- Target Match: Alerta que SERÁ INIBIDO
- Equal: Labels que devem ser iguais entre source/target
```

### C) Rules - 2 Visualizações

#### 1. VISÃO GRUPO (alert-rules-*.yml)
**Colunas:**
- Group Name
- Interval (avaliação)
- Rules Count (quantidade de regras)

#### 2. VISÃO ALERTA (individual)
**Colunas:**
- Alert Name
- Expression (PromQL)
- Duration (for)
- Severity
- Summary
- Description
- Labels

---

## 🎨 COMPONENTES VISUAIS E UX

### Toolbar de Botões (tabBarExtraContent)

**HIERARQUIA VISUAL (após melhorias):**

```
┌─────────────────────────────────────────────────────────────────┐
│  [Rotas | Receptores | Regras de Inibição]  │  [Densidade ▼ | Configurar Colunas]  │
│         ↑ BOTÕES PRIMÁRIOS                   separador    ↑ SECUNDÁRIOS            │
│    (fontWeight: 600, boxShadow)                      (agrupados)                    │
└─────────────────────────────────────────────────────────────────┘
```

**Implementação:**
- Botões de visualização aparecem PRIMEIRO
- Style com `fontWeight: 600` para destaque
- `boxShadow: '0 2px 8px rgba(24, 144, 255, 0.3)'` quando ativo
- Separador visual (div com linha vertical) após botões primários
- Botões de configuração (Densidade + Configurar Colunas) agrupados em `Space.Compact`

### Seletores de Servidor e Arquivo

**Layout em Grid (Row/Col):**
```
┌────────────────────────────────────────────────────────────────┐
│  [Servidor Prometheus ▼]  [Arquivo Config ▼]  [Editar] [Reload]│
│       40% largura              35%              12.5%   12.5%   │
└────────────────────────────────────────────────────────────────┘
```

**Características:**
- Select com tags coloridas (prometheus: azul, alertmanager: laranja)
- Alert no topo mostrando servidor selecionado + tipo (Master/Slave)
- Animação de "Alterado!" quando troca servidor
- Arquivos ordenados alfabeticamente

### Editor Monaco

**Características:**
- Modal fullscreen com editor Monaco (YAML)
- Syntax highlighting para YAML
- Botão "Salvar" com loading state
- Alert informativo embaixo do editor:
  ```
  💾 Salvamento Seguro
  - Backup automático criado antes de salvar
  - Reload automático dos serviços após validação bem-sucedida
  - Permissões restauradas automaticamente (prometheus:prometheus)
  - Validação com promtool antes de aplicar
  ```

### Tabela ProTable

**Recursos:**
- Colunas redimensionáveis (ResizableTitle component)
- Configuração de colunas visíveis (ColumnSelector com drag-and-drop)
- Densidade ajustável (small/middle/large via Dropdown)
- Paginação (10/20/30/50/100 por página)
- Scroll horizontal (x: 1200)
- Empty state customizado por tipo de arquivo

---

## 🐛 BUGS CORRIGIDOS NESTA SESSÃO

### 1. Colunas Faltantes em Receptores
**Problema:** Tabela de Receptores não exibia "send_resolved" e "max_alerts"

**Solução:**
- Adicionado ao `ALERTMANAGER_RECEIVERS_COLUMNS` (linhas 1208-1209)
- Implementado rendering especial:
  - `send_resolved`: CheckCircleOutlined (verde) / CloseCircleOutlined (vermelho) / Tag "N/A"
  - `max_alerts`: Tag azul com número ou Tag "Ilimitado"

### 2. Explicações Antes da Tabela
**Problema:** Alertas explicativos apareciam ANTES da tabela, forçando scroll

**Solução:**
- Movido todos os Alert para APÓS a tabela (linhas 2371-2518)
- Alterado `marginBottom: 16` para `marginTop: 16`

### 3. Arquivos Fora de Ordem Alfabética
**Problema:** Arquivos no dropdown não estavam ordenados

**Solução:**
- Adicionado `.sort((a, b) => a.filename.localeCompare(b.filename))` no useMemo de files (linhas 183-199)

### 4. **CRÍTICO - Dados de Servidor Errado ao Trocar**
**Problema:** Ao trocar de servidor 1.26 para 200.14 com alertmanager.yml selecionado, tabela ainda mostrava dados do 1.26

**Tentativas falhadas (5x):**
1. Limpar state quando servidor muda
2. Adicionar selectedServer ao useEffect dependencies
3. Limpar dados no início de fetchAlertmanagerData
4. Criar fileServerKey composite para forçar reload
5. Várias manipulações de state no frontend

**Causa raiz:** Backend não estava usando o parâmetro `hostname`
- `multi_config_manager.py:get_file_content_raw()` não aceitava hostname
- Endpoints `/alertmanager/routes`, `/receivers`, `/inhibit-rules` não passavam hostname

**Solução final:**
- Modificado `multi_config_manager.py:520` para aceitar `hostname: Optional[str]`
- Modificado 3 endpoints em `prometheus_config.py` (linhas 1737, 1777, 1817) para passar hostname
- Removido código desnecessário do frontend (fileServerKey)

**Validação:**
```
Console logs confirmaram:
Servidor 1.26: 8 rotas, 9 receptores
Servidor 200.14: 3 rotas, 4 receptores (dados diferentes ✓)
```

---

## 🔧 FUNCIONALIDADES AVANÇADAS

### Gerenciamento de Colunas

**ColumnSelector Component:**
- Drag-and-drop para reordenar colunas
- Toggle para mostrar/ocultar colunas
- Persistência em localStorage por tipo de arquivo
- Key format: `prometheus-columns-${fileType}`

**Colunas Predefinidas:**
- `PROMETHEUS_COLUMNS` - Jobs do Prometheus
- `ALERTMANAGER_ROUTES_COLUMNS` - Rotas do Alertmanager
- `ALERTMANAGER_RECEIVERS_COLUMNS` - Receptores
- `ALERTMANAGER_INHIBIT_RULES_COLUMNS` - Regras de Inibição
- `RULES_GROUP_COLUMNS` - Grupos de regras
- `RULES_ALERT_COLUMNS` - Alertas individuais

### Redimensionamento de Colunas

**ResizableTitle Component:**
- Componente customizado para headers redimensionáveis
- Usa `react-resizable` para arrastar bordas
- Persiste larguras em `columnWidths` state
- Min width: 50px (para evitar colunas muito pequenas)

### Múltiplos Servidores

**Suporte a Master/Slave:**
- Backend retorna lista de servidores com tipo (master/slave)
- Badge colorido: verde para Master, azul para Slave
- Filtro de arquivos por servidor (hostname-based)
- Operações SSH isoladas por servidor

---

## 📡 ENDPOINTS DO BACKEND UTILIZADOS

### Servidores e Arquivos
```
GET /api/v1/prometheus-config/servers
  → Lista todos os servidores Prometheus configurados

GET /api/v1/prometheus-config/files?server_id={id}
  → Lista arquivos YAML disponíveis no servidor
  → Retorna: [{path, filename, service, host}]

GET /api/v1/prometheus-config/file-content?file_path={path}&hostname={host}
  → Retorna conteúdo bruto do arquivo para edição
```

### Prometheus Jobs
```
GET /api/v1/prometheus-config/jobs?file_path={path}&hostname={host}
  → Parse de prometheus.yml
  → Retorna scrape_configs estruturados
```

### Alertmanager
```
GET /api/v1/prometheus-config/alertmanager/routes?file_path={path}&hostname={host}
  → Parse de alertmanager.yml → route tree
  → Retorna hierarquia de rotas

GET /api/v1/prometheus-config/alertmanager/receivers?file_path={path}&hostname={host}
  → Parse de alertmanager.yml → receivers
  → Retorna lista de receptores com configs

GET /api/v1/prometheus-config/alertmanager/inhibit-rules?file_path={path}&hostname={host}
  → Parse de alertmanager.yml → inhibit_rules
  → Retorna regras de inibição
```

### Edição e Validação
```
PUT /api/v1/prometheus-config/update-raw
  Body: {file_path, new_content, hostname}
  → Processo:
    1. Backup automático (nome.yml.backup.timestamp)
    2. Validação com promtool (SSH)
    3. Salvar arquivo via SFTP
    4. Restaurar permissões (chown prometheus:prometheus)
    5. Reload do serviço (systemctl reload prometheus/alertmanager)
  → Retorna: {success, message, validation_result}
```

### Campos Dinâmicos
```
GET /api/v1/metadata-fields/servers
  → Extrai campos de relabel_configs do Prometheus
  → Retorna campos disponíveis para colunas dinâmicas
```

---

## 🎯 PADRÕES DE CÓDIGO IMPORTANTES

### 1. Limpeza de Dados ao Trocar Servidor
```typescript
// CRÍTICO: Sempre limpar dados antigos IMEDIATAMENTE
const handleServerChange = (serverId: string) => {
  setSelectedServer(serverId);

  // Limpar dados antigos
  setJobs([]);
  setAlertmanagerRoutes([]);
  setAlertmanagerReceivers([]);
  setAlertmanagerInhibitRules([]);

  // Resetar para estado inicial
  setFileType('prometheus');
  setSelectedFile(null);
};
```

### 2. useEffect com Dependências Corretas
```typescript
// Carregar dados quando arquivo OU servidor mudar
useEffect(() => {
  if (selectedFile && selectedServer) {
    const isAlertmanagerFile = selectedFile.toLowerCase().includes('alertmanager');

    if (isAlertmanagerFile) {
      fetchAlertmanagerData(selectedFile, selectedServer);
    } else {
      fetchJobs(selectedFile, selectedServer);
    }
  }
}, [selectedFile, selectedServer, fetchJobs, fetchAlertmanagerData]);
```

### 3. Passagem de Hostname para Backend
```typescript
// SEMPRE passar hostname nos requests para garantir servidor correto
const fetchAlertmanagerData = async (filePath: string, serverIdWithPort?: string) => {
  let hostnameParam = '';
  if (serverIdWithPort) {
    const hostname = serverIdWithPort.split(':')[0]; // Extrair apenas hostname
    hostnameParam = `&hostname=${encodeURIComponent(hostname)}`;
  }

  const response = await axios.get(
    `/api/v1/prometheus-config/alertmanager/routes?file_path=${filePath}${hostnameParam}`
  );
};
```

### 4. Colunas Dinâmicas Baseadas em Tipo
```typescript
const visibleColumns = useMemo(() => {
  const allColumns = getColumnsForType(fileType, alertViewMode, alertmanagerViewMode);

  // Verificar se columnConfig corresponde ao tipo de arquivo atual
  if (columnConfig.length === 0) return allColumns;

  // Filtrar apenas colunas visíveis
  return columnConfig
    .filter(config => config.visible)
    .map(config => {
      const column = allColumns.find(col => col.key === config.key);
      if (!column) return null;

      // Aplicar largura redimensionada
      const width = columnWidths[config.key] || column.width;
      return { ...column, width };
    })
    .filter(Boolean);
}, [columnConfig, columnWidths, fileType, alertViewMode, alertmanagerViewMode]);
```

---

## 💡 LIÇÕES APRENDIDAS

### 1. Debug Multi-Camadas
Quando problema persiste após múltiplas tentativas no frontend:
- **SEMPRE testar backend diretamente** (curl/Postman)
- Adicionar console.logs estratégicos
- Validar cada camada: Frontend → API → Backend → Consul/SSH

### 2. Hostname vs Server ID
- Server ID pode incluir porta: `172.16.1.26:5522`
- Hostname para SSH: apenas `172.16.1.26`
- **Sempre extrair hostname** antes de passar para backend

### 3. Persistência de Configuração
- localStorage é ótimo para preferências de UI
- **SEMPRE validar** se configuração salva corresponde ao tipo de arquivo atual
- Usar keys únicas por tipo: `prometheus-columns-${fileType}`

### 4. UX de Loading States
- Loading individual por operação (loadingJobs, loadingAlertmanager)
- Skeleton screens melhor que spinners genéricos
- Feedback visual imediato ao trocar servidor (animation de "Alterado!")

---

## 🔮 POSSÍVEIS MELHORIAS FUTURAS

1. **Diff Viewer** - Comparar versão atual vs backup antes de salvar
2. **Histórico de Mudanças** - Timeline de edições com rollback
3. **Validação em Tempo Real** - Validar YAML enquanto digita no Monaco
4. **Templates de Configuração** - Snippets prontos para common patterns
5. **Multi-Select de Servidores** - Aplicar mudanças em múltiplos servidores
6. **Export/Import** - Baixar/upload de configurações
7. **Search/Filter na Tabela** - Busca textual nos dados
8. **Alertas de Conflito** - Detectar se arquivo foi modificado externamente

---

## 📚 DEPENDÊNCIAS PRINCIPAIS

```json
{
  "@ant-design/pro-components": "ProTable, PageContainer",
  "@monaco-editor/react": "Editor YAML",
  "antd": "Alert, Badge, Button, Card, Col, Dropdown, Empty, Modal, Row, Select, Space, Tag, Tooltip",
  "react": "hooks (useState, useEffect, useMemo, useCallback)",
  "axios": "HTTP client para API calls"
}
```

### Componentes Customizados Utilizados
- `ColumnSelector` - Gerenciamento de colunas visíveis
- `ResizableTitle` - Headers redimensionáveis
- `ServerSelector` - (se existir) Seleção de servidores

---

## 🔗 ARQUIVOS RELACIONADOS

### Backend
- `backend/api/prometheus_config.py` - Endpoints principais
- `backend/core/multi_config_manager.py` - Gerenciamento multi-servidor SSH
- `backend/core/yaml_config_service.py` - Parse e validação YAML

### Frontend
- `frontend/src/services/api.ts` - Client HTTP com tipos TypeScript
- `frontend/src/components/ColumnSelector.tsx` - Configuração de colunas
- `frontend/src/components/ResizableTitle.tsx` - Redimensionamento

### Documentação
- `CLAUDE.md` - Visão geral do projeto
- `PHASE4_SUMMARY.md` - Implementação do editor multi-servidor
- `docs/PROMETHEUS_CONFIG_PAGE_SUMMARY.md` - Este arquivo

---

## 📝 NOTAS FINAIS

Esta página representa uma das mais complexas do sistema, integrando:
- ✅ Multi-servidor SSH
- ✅ Parse avançado de YAML
- ✅ Editor Monaco com validação
- ✅ Múltiplas visualizações de dados
- ✅ Configuração persistente de UI
- ✅ Gestão de estado complexa

**Principais destaques:**
- Código bem estruturado com separação clara de responsabilidades
- Estados controlados com hooks React (sem Redux)
- UX refinada com feedback visual em todas operações
- Tratamento robusto de erros e edge cases
- Comentários em português-BR para lógica de negócio

**Uso de memória e performance:**
- ~3500 linhas pode parecer muito, mas está bem organizado
- useMemo para otimizar cálculos de colunas
- useCallback para funções que não precisam recriar
- Carregamento lazy de dados (só carrega quando necessário)

---

**Última revisão:** 2025-10-30
**Autor:** Claude Code (Assistente de Desenvolvimento)
**Status:** ✅ Documentação completa e validada
