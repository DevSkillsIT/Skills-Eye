# Tipos de Monitoramento - Documentação Técnica

## Arquitetura

### Fluxo de Dados

```
                 ┌─────────────────┐
                 │ prometheus.yml  │
                 │ (Servidor SSH)  │
                 └────────┬────────┘
                          │
                    SSH + YAML Parse
                          │
                          ▼
┌──────────────────────────────────────────┐
│ Backend: monitoring_types_dynamic.py     │
│                                          │
│ 1. extract_types_from_prometheus_jobs()  │
│ 2. rule_engine.categorize()              │
│ 3. _group_by_category()                  │
│ 4. Salvar no KV (com merge form_schema)  │
└────────────────────┬─────────────────────┘
                     │
                     ▼
              ┌─────────────┐
              │ Consul KV   │
              │ skills/eye/ │
              │ monitoring- │
              │ types       │
              └──────┬──────┘
                     │
                     ▼
         ┌─────────────────────┐
         │ Frontend:           │
         │ MonitoringTypes.tsx │
         └─────────────────────┘
```

### Arquivos Principais

| Arquivo | Localização | Responsabilidade |
|---------|-------------|------------------|
| MonitoringTypes.tsx | `frontend/src/pages/` | Interface do usuário |
| monitoring_types_dynamic.py | `backend/api/` | Endpoints e extração |
| categorization_rule_engine.py | `backend/core/` | Motor de categorização |
| multi_config_manager.py | `backend/core/` | Acesso SSH aos servidores |

---

## Estrutura de Dados

### MonitoringType

```typescript
interface MonitoringType {
  id: string;              // Identificador único
  display_name: string;    // Nome amigável
  category: string;        // Categoria
  job_name: string;        // Nome do job no Prometheus
  exporter_type: string;   // Tipo de exporter
  module?: string;         // Módulo blackbox
  fields?: string[];       // Labels metadata
  metrics_path: string;    // /probe ou /metrics
  server?: string;         // Servidor de origem
  servers?: string[];      // Lista de servidores
  form_schema?: FormSchema; // Schema do formulário
  job_config?: any;        // Job original do prometheus.yml
}
```

### FormSchema

```typescript
interface FormSchema {
  fields?: FormSchemaField[];
  required_metadata?: string[];
  optional_metadata?: string[];
}

interface FormSchemaField {
  name: string;
  label?: string;
  type: string;           // text, number, select, etc
  required?: boolean;
  default?: any;
  placeholder?: string;
  help?: string;
  validation?: any;
  options?: Array<{ value: string; label: string }>;
  min?: number;
  max?: number;
}
```

### Estrutura no KV

**Chave**: `skills/eye/monitoring-types`

```json
{
  "version": "1.0.0",
  "last_updated": "2025-11-21T10:30:00",
  "source": "force_refresh",
  "total_types": 28,
  "total_servers": 3,
  "successful_servers": 3,
  "servers": {
    "prometheus-master": {
      "types": [...],
      "total": 28
    }
  },
  "all_types": [...],
  "categories": [
    {
      "category": "network-probes",
      "display_name": "Network Probes (Rede)",
      "types": [...]
    }
  ],
  "server_status": [...]
}
```

---

## API Endpoints

### GET /api/v1/monitoring-types-dynamic/from-prometheus

Busca tipos de monitoramento.

**Query Parameters:**

| Parâmetro | Tipo | Descrição |
|-----------|------|-----------|
| server | string | Hostname do servidor (ou "ALL") |
| force_refresh | boolean | Forçar extração via SSH |

**Response:**

```json
{
  "success": true,
  "from_cache": true,
  "categories": [...],
  "all_types": [...],
  "servers": {...},
  "total_types": 28,
  "total_servers": 3,
  "successful_servers": 3,
  "server_status": [...],
  "last_updated": "2025-11-21T10:30:00"
}
```

### PUT /api/v1/monitoring-types-dynamic/type/{type_id}/form-schema

Atualiza o form_schema de um tipo.

**Request Body:**

```json
{
  "form_schema": {
    "fields": [...],
    "required_metadata": ["target", "module"],
    "optional_metadata": ["timeout"]
  }
}
```

---

## Backend - Funções Principais

### extract_types_from_prometheus_jobs()

```python
def extract_types_from_prometheus_jobs(
    jobs: List[Dict],
    server_host: str,
    rule_engine: CategorizationRuleEngine
) -> List[Dict]:
    """
    Extrai tipos de monitoramento dos jobs do prometheus.yml

    Para cada job:
    1. Extrai job_name, metrics_path, relabel_configs
    2. Extrai módulo blackbox (se aplicável)
    3. Extrai campos metadata dos labels
    4. Categoriza usando rule_engine
    5. Monta type_schema

    Returns:
        Lista de type_schema
    """
```

### _extract_types_from_all_servers()

```python
async def _extract_types_from_all_servers(server: Optional[str] = None) -> Dict:
    """
    Orquestra extração de todos os servidores

    1. Carrega regras de categorização
    2. Para cada servidor:
       a. Busca prometheus.yml via SSH
       b. Extrai tipos dos jobs
    3. Agrega tipos (deduplica)
    4. Busca display_name das categorias do KV
    5. Agrupa por categoria
    6. Calcula estatísticas

    Returns:
        {
            "servers": {...},
            "all_types": [...],
            "categories": [...],
            "total_types": int,
            "total_servers": int,
            "successful_servers": int,
            "server_status": [...]
        }
    """
```

### Merge Seletivo de form_schema

```python
# PASSO 4: Merge seletivo para preservar form_schema existente
existing_kv = await kv_manager.get_json('skills/eye/monitoring-types')

# Criar mapeamento de form_schema existentes
existing_form_schemas = {}
if existing_kv:
    for type_data in existing_kv.get('all_types', []):
        type_id = type_data.get('id')
        if type_id and 'form_schema' in type_data:
            existing_form_schemas[type_id] = type_data['form_schema']

# Aplicar form_schema existente nos novos tipos
for type_data in result['all_types']:
    type_id = type_data.get('id')
    if type_id in existing_form_schemas:
        type_data['form_schema'] = existing_form_schemas[type_id]
```

---

## Frontend - MonitoringTypes.tsx

### Estrutura do Componente

```typescript
export default function MonitoringTypes() {
  // Estados de dados
  const [categories, setCategories] = useState<CategoryData[]>([]);
  const [serverData, setServerData] = useState<Record<string, ServerResult>>({});
  const [totalTypes, setTotalTypes] = useState(0);

  // Estados de UI
  const [viewMode, setViewMode] = useState<'all' | 'specific'>('all');
  const [selectedServerId, setSelectedServerId] = useState<string>('ALL');
  const [tableSize, setTableSize] = useState<'small' | 'middle' | 'large'>('middle');
  const [columnConfig, setColumnConfig] = useState<ColumnConfig[]>([...]);

  // Estados de modais
  const [jsonModalVisible, setJsonModalVisible] = useState(false);
  const [formSchemaModalVisible, setFormSchemaModalVisible] = useState(false);
  const [jobConfigModalVisible, setJobConfigModalVisible] = useState(false);
  const [selectedType, setSelectedType] = useState<MonitoringType | null>(null);

  // Carregamento
  const loadTypes = useCallback(async (forceRefresh, showModal) => {...});

  // Handlers de modal
  const handleViewJson = (type) => {...};
  const handleEditFormSchema = (type) => {...};
  const handleViewJobConfig = (type) => {...};
  const handleSaveFormSchema = async () => {...};
}
```

### useServersContext

O componente usa o contexto de servidores para evitar requests duplicados:

```typescript
const { servers, master, loading: serversLoading } = useServersContext();

useEffect(() => {
  if (!serversLoading && servers.length > 0 && master) {
    if (viewMode === 'specific' && (!selectedServerId || selectedServerId === 'ALL')) {
      setSelectedServerId(master.id);
      setSelectedServerInfo(master);
    }
  }
}, [serversLoading, servers, master, viewMode, selectedServerId]);
```

### ExtractionProgressModal

Componente separado para mostrar progresso da extração:

```typescript
interface ServerStatus {
  hostname: string;
  success: boolean;
  from_cache: boolean;
  files_count: number;
  fields_count: number;
  error: string | null;
  duration_ms: number;
}

<ExtractionProgressModal
  visible={progressModalVisible}
  loading={extractionData.loading}
  fromCache={extractionData.fromCache}
  successfulServers={extractionData.successfulServers}
  totalServers={extractionData.totalServers}
  serverStatus={extractionData.serverStatus}
  totalTypes={extractionData.totalTypes}
  error={extractionData.error}
  onClose={() => setProgressModalVisible(false)}
/>
```

### Editor Monaco para Form Schema

```typescript
<Modal title="Editar Form Schema" visible={formSchemaModalVisible}>
  <Editor
    height="400px"
    defaultLanguage="json"
    value={formSchemaJson}
    onChange={(value) => setFormSchemaJson(value || '')}
    options={{
      minimap: { enabled: false },
      formatOnPaste: true,
      formatOnType: true,
    }}
  />
</Modal>
```

---

## Fluxos de Dados

### Carregamento Inicial (Cache)

```
1. Frontend chama GET /from-prometheus?server=ALL
2. Backend verifica KV skills/eye/monitoring-types
3. Se existe e não é force_refresh, retorna do cache
4. Frontend renderiza categorias e tipos
```

### Force Refresh

```
1. Frontend chama GET /from-prometheus?force_refresh=true
2. Backend:
   a. Carrega regras de categorização
   b. Para cada servidor:
      - Conecta via SSH
      - Busca /etc/prometheus/prometheus.yml
      - Parse YAML
      - Extrai jobs
   c. Categoriza todos os tipos
   d. Preserva form_schema existentes (merge)
   e. Salva no KV
3. Frontend atualiza UI com novos dados
```

### Salvar Form Schema

```
1. Usuário edita JSON no modal
2. Frontend chama PUT /type/{id}/form-schema
3. Backend:
   a. Busca KV atual
   b. Encontra tipo pelo ID
   c. Atualiza form_schema
   d. Salva no KV
4. Frontend mostra mensagem de sucesso
```

---

## Extração SSH

### MultiConfigManager

```python
class MultiConfigManager:
    """
    Gerencia acesso a configurações de múltiplos servidores via SSH
    """

    def list_config_files(self, service, hostname):
        """Lista arquivos de configuração de um serviço"""

    def read_prometheus_config(self, hostname):
        """Lê e parseia prometheus.yml"""

    def clear_cache(self, close_connections=True):
        """Limpa cache e fecha conexões SSH"""
```

### Processo de Extração

```python
# 1. Buscar arquivos
prom_files = multi_config.list_config_files(
    service='prometheus',
    hostname=server_host
)

# 2. Ler configuração
config = multi_config.read_prometheus_config(server_host)

# 3. Extrair jobs
jobs = config.get('scrape_configs', [])

# 4. Processar cada job
for job in jobs:
    # Filtrar jobs com consul_sd_configs
    if 'consul_sd_configs' in job:
        types.extend(
            extract_types_from_prometheus_jobs([job], server_host, rule_engine)
        )
```

---

## Performance

### Benchmarks

| Operação | Tempo |
|----------|-------|
| Cache hit | ~100ms |
| Force refresh (1 servidor) | ~5-10s |
| Force refresh (3 servidores) | ~15-30s |
| Salvar form_schema | ~200ms |

### Otimizações

- **Cache no KV**: Evita extrações desnecessárias
- **Merge seletivo**: Preserva form_schema sem re-extrair tudo
- **ServersContext**: Evita requests duplicados de servidores
- **Regex compilado**: Patterns compilados no init das regras

---

## Componentes Auxiliares

### ServerSelector

```typescript
<ServerSelector
  servers={servers}
  selectedId={selectedServerId}
  onSelect={(server) => {
    setSelectedServerId(server.id);
    setSelectedServerInfo(server);
  }}
/>
```

### ColumnSelector

```typescript
<ColumnSelector
  columns={columnConfig}
  onChange={setColumnConfig}
/>
```

---

## Tratamento de Erros

### Erros de SSH

```python
try:
    config = multi_config.read_prometheus_config(server_host)
except Exception as e:
    logger.error(f"Erro ao ler prometheus.yml de {server_host}: {e}")
    return {
        "hostname": server_host,
        "success": False,
        "error": str(e),
        "types": []
    }
```

### Erros de Parse

```python
try:
    jobs = config.get('scrape_configs', [])
except Exception as e:
    logger.error(f"Erro ao parsear scrape_configs: {e}")
    jobs = []
```

### Feedback no Frontend

```typescript
if (response.data.success) {
  setCategories(response.data.categories || []);
  // ...
} else {
  message.error('Erro ao carregar tipos');
  setExtractionData(prev => ({
    ...prev,
    error: response.data.message || 'Erro desconhecido'
  }));
}
```

---

## Testes

### Testes de Integração

```python
# backend/test_spec_arch_001_integration.py

async def test_engine_loads_rules():
    """Verifica carregamento de regras"""

async def test_categorization_blackbox_icmp():
    """Verifica categorização de ICMP"""

async def test_performance_1000_types():
    """Benchmark de categorização"""
```

### Debug

```python
# Habilitar logs detalhados
import logging
logging.getLogger('backend.api.monitoring_types_dynamic').setLevel(logging.DEBUG)

# Verificar extração
curl "http://localhost:5000/api/v1/monitoring-types-dynamic/from-prometheus?force_refresh=true" | jq
```

---

## Manutenção

### Limpar Cache

```bash
# Via Consul UI
http://172.16.1.26:8500/ui/dc1/kv/skills/eye/monitoring-types

# Via API
curl -X DELETE "http://172.16.1.26:8500/v1/kv/skills/eye/monitoring-types"
```

### Forçar Re-extração

```bash
curl "http://localhost:5000/api/v1/monitoring-types-dynamic/from-prometheus?force_refresh=true"
```

### Debug de Tipos Faltando

1. Verificar se o job tem `consul_sd_configs`
2. Verificar se o servidor está acessível via SSH
3. Verificar logs do backend
4. Verificar regras de categorização

---

**Versão**: 2.0.0
**Última atualização**: 2025-11-21
**Autor**: Sistema Skills Eye
