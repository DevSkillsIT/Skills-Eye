# Regras de Categorização - Documentação Técnica

## Arquitetura

### Componentes Envolvidos

```
Frontend                          Backend                         Storage
┌────────────────────┐    ┌─────────────────────────┐    ┌──────────────┐
│ MonitoringRules.tsx │───▶│ categorization_rules.py │───▶│ Consul KV    │
└────────────────────┘    └─────────────────────────┘    │              │
                                      │                   │ skills/eye/  │
                                      ▼                   │ monitoring-  │
                          ┌─────────────────────────┐    │ types/       │
                          │ categorization_rule_    │    │ categoriz..  │
                          │ engine.py               │    │ /rules       │
                          └─────────────────────────┘    └──────────────┘
```

### Arquivos Principais

| Arquivo | Localização | Responsabilidade |
|---------|-------------|------------------|
| MonitoringRules.tsx | `frontend/src/pages/` | Interface do usuário |
| categorization_rules.py | `backend/api/` | Endpoints REST API |
| categorization_rule_engine.py | `backend/core/` | Motor de categorização |

---

## Estrutura de Dados

### Regra de Categorização

```typescript
interface CategorizationRule {
  id: string;                    // Identificador único
  priority: number;              // 1-100 (maior = aplicada primeiro)
  category: string;              // ID da categoria
  display_name: string;          // Nome amigável
  exporter_type?: string;        // Tipo de exporter
  conditions: {
    job_name_pattern?: string;   // Regex para job_name
    metrics_path?: string;       // /probe ou /metrics
    module_pattern?: string;     // Regex para module
  };
  observations?: string;         // Observações/notas
}
```

### Estrutura no KV

```json
{
  "version": "1.0.0",
  "last_updated": "2025-11-21T10:30:00",
  "total_rules": 48,
  "rules": [...],
  "default_category": "custom-exporters",
  "categories": [
    {"id": "network-probes", "display_name": "Network Probes (Rede)"},
    {"id": "web-probes", "display_name": "Web Probes (Aplicações)"},
    ...
  ]
}
```

**Chave no KV**: `skills/eye/monitoring-types/categorization/rules`

---

## API Endpoints

### GET /api/v1/categorization-rules

Lista todas as regras de categorização.

**Response:**
```json
{
  "success": true,
  "data": {
    "version": "1.0.0",
    "last_updated": "2025-11-21T10:30:00",
    "total_rules": 48,
    "rules": [...],
    "default_category": "custom-exporters",
    "categories": [...]
  }
}
```

### POST /api/v1/categorization-rules

Cria uma nova regra.

**Request Body:**
```json
{
  "id": "blackbox_custom_probe",
  "priority": 90,
  "category": "web-probes",
  "display_name": "Custom HTTP Probe",
  "exporter_type": "blackbox",
  "conditions": {
    "job_name_pattern": "^custom_http.*",
    "metrics_path": "/probe",
    "module_pattern": "^http"
  },
  "observations": "Regra customizada para probes HTTP específicos"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Regra criada com sucesso",
  "rule_id": "blackbox_custom_probe"
}
```

### PUT /api/v1/categorization-rules/{rule_id}

Atualiza uma regra existente.

### DELETE /api/v1/categorization-rules/{rule_id}

Remove uma regra.

### POST /api/v1/categorization-rules/reload

Força recarga das regras do KV.

---

## Motor de Categorização

### Classe CategorizationRuleEngine

```python
class CategorizationRuleEngine:
    """
    Motor de categorização baseado em regras JSON
    """

    def __init__(self, config_manager):
        self.config_manager = config_manager
        self.rules = []
        self.default_category = 'custom-exporters'
        self.rules_loaded = False

    async def load_rules(self, force_reload=False):
        """Carrega regras do KV"""

    def categorize(self, job_data):
        """Categoriza um job baseado nas regras"""

    def get_rules_summary(self):
        """Retorna resumo das regras"""
```

### Fluxo de Categorização

```python
def categorize(self, job_data: Dict) -> tuple:
    """
    1. Extrair module de relabel_configs se necessário
    2. Aplicar regras em ordem de prioridade (maior primeiro)
    3. Primeira regra que faz match é aplicada
    4. Se nenhuma regra aplicar, usa default_category

    Returns:
        (categoria, type_info)
    """
```

### Classe CategorizationRule

```python
class CategorizationRule:
    def __init__(self, rule_data: Dict):
        self.id = rule_data['id']
        self.priority = rule_data.get('priority', 50)
        self.category = rule_data['category']
        self.display_name = rule_data.get('display_name', '')
        self.exporter_type = rule_data.get('exporter_type', '')
        self.conditions = rule_data['conditions']

        # Compilar regex patterns
        self._compiled_patterns = {}
        for key, pattern in self.conditions.items():
            if key.endswith('_pattern'):
                try:
                    self._compiled_patterns[key] = re.compile(pattern, re.IGNORECASE)
                except re.error as e:
                    logger.error(f"Regex inválida em {key}: {e}")

    def matches(self, job_data: Dict) -> bool:
        """Verifica se o job faz match com esta regra"""
```

---

## Frontend - MonitoringRules.tsx

### Estrutura do Componente

```typescript
const MonitoringRules: React.FC = () => {
  // Estados principais
  const [modalVisible, setModalVisible] = useState(false);
  const [editingRule, setEditingRule] = useState<CategorizationRule | null>(null);
  const [rulesData, setRulesData] = useState<RulesData | null>(null);
  const [filteredInfo, setFilteredInfo] = useState<Record<string, FilterValue | null>>({});
  const [sortedInfo, setSortedInfo] = useState<SorterResult<CategorizationRule>>({});

  // Handlers
  const loadRules = async () => {...}
  const handleAdd = () => {...}
  const handleEdit = (record) => {...}
  const handleDuplicate = (record) => {...}
  const handleDelete = async (ruleId) => {...}
  const handleSave = async () => {...}

  // Render
  return (
    <PageContainer>
      <ProTable columns={columns} request={loadRules} />
      <Modal>{/* Form de edição */}</Modal>
    </PageContainer>
  );
}
```

### Componente RegexTester

```typescript
const RegexTester: React.FC<RegexTesterProps> = ({ pattern, placeholder, title }) => {
  const [testValue, setTestValue] = useState('');
  const [result, setResult] = useState<{ match: boolean; value: string } | null>(null);

  const handleSearch = () => {
    try {
      const regex = new RegExp(pattern);
      const match = regex.test(testValue);
      setResult({ match, value: testValue });
    } catch (e) {
      message.error('Regex inválido');
    }
  };

  return (
    <Card>
      <Input.Search onSearch={handleSearch} />
      {result && <Alert type={result.match ? 'success' : 'warning'} />}
    </Card>
  );
};
```

### Validação de Regex

```typescript
const validateRegex = (_: any, value: string) => {
  if (!value) return Promise.resolve();
  try {
    new RegExp(value);
    return Promise.resolve();
  } catch (e) {
    return Promise.reject(new Error('Expressão Regular inválida'));
  }
};
```

---

## Constantes e Configurações

### Cores de Categorias

```typescript
const CATEGORY_COLORS: Record<string, string> = {
  'network-probes': 'purple',
  'web-probes': 'cyan',
  'system-exporters': 'green',
  'database-exporters': 'magenta',
  'infrastructure-exporters': 'blue',
  'hardware-exporters': 'orange',
  'network-devices': 'gold',
  'custom-exporters': 'default',
};
```

### Níveis de Prioridade

```typescript
const PRIORITY_LEVELS = [
  { value: 100, label: '100 - Máxima (Blackbox)', color: 'red' },
  { value: 90, label: '90 - Muito Alta', color: 'volcano' },
  { value: 80, label: '80 - Alta (Exporters)', color: 'orange' },
  { value: 70, label: '70 - Média-Alta', color: 'gold' },
  { value: 60, label: '60 - Média', color: 'lime' },
  { value: 50, label: '50 - Baixa', color: 'green' },
];
```

---

## Fluxo de Dados

### Criar Regra

```
1. Usuário preenche formulário
2. Frontend valida campos (regex, campos obrigatórios)
3. POST /api/v1/categorization-rules
4. Backend valida e salva no KV
5. Frontend recarrega tabela
```

### Aplicar Regras (Categorização)

```
1. Tipo é extraído do prometheus.yml
2. Engine carrega regras do KV
3. Para cada tipo:
   a. Percorre regras em ordem de prioridade
   b. Verifica match de job_name_pattern
   c. Verifica match de metrics_path
   d. Verifica match de module_pattern (se aplicável)
   e. Primeira regra que faz match é usada
   f. Se nenhuma, usa default_category
4. Retorna (categoria, type_info)
```

---

## Testes

### Testes de Integração

```python
# backend/test_spec_arch_001_integration.py

async def test_engine_loads_rules():
    """Verifica que engine carrega regras do KV"""

async def test_categorization_blackbox_icmp():
    """Verifica categorização de ICMP"""

async def test_form_schema_not_in_rules():
    """Verifica que form_schema não está nas regras"""
```

### Script de Validação

```python
# backend/scripts/validate_categorization.py

EXPECTED_CATEGORIZATIONS = [
    {'job_data': {...}, 'expected_category': 'network-probes'},
    ...
]

async def validate_categorization():
    """Valida categorização contra casos esperados"""
```

---

## Manutenção

### Adicionar Nova Categoria

1. Atualizar `CATEGORY_COLORS` no frontend
2. Adicionar ao array `categories` no script de migração
3. Atualizar documentação

### Debug de Categorização

```python
# Habilitar log debug no engine
logger.setLevel(logging.DEBUG)

# Verificar regras carregadas
summary = engine.get_rules_summary()
print(f"Regras: {summary['total_rules']}")
print(f"Fonte: {summary['source']}")
```

### Resetar Regras

```bash
# Executar script de migração para resetar regras
cd backend
python migrate_categorization_to_json.py
```

---

## Performance

- Regras são carregadas do KV uma vez e cacheadas
- Patterns de regex são compilados no `__init__` da regra
- Categorização de 1000 tipos: ~5ms (benchmark)

---

**Versão**: 2.0.0
**Última atualização**: 2025-11-21
**Autor**: Sistema Skills Eye
