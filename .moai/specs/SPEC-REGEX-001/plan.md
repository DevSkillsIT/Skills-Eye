# Plano de Implementação - SPEC-REGEX-001

## Visão Geral

Este documento detalha o plano de implementação passo a passo para o Global Regex Validator e Match Columns.

---

## Fase 1: Preparação e Tipos (Backend + Frontend Types)

### Tarefa 1.1: Atualizar Tipos TypeScript

**Arquivo**: `frontend/src/types/monitoring.ts`

**Adicionar interfaces**:

```typescript
// Interface para informações de match da regra
export interface MatchedRuleInfo {
  id: string;                      // ID da regra que fez match
  priority: number;                // Prioridade da regra
  job_pattern_matched: boolean;    // Se job_name_pattern fez match
  module_pattern_matched: boolean; // Se module_pattern fez match
  job_pattern?: string;            // Pattern de job_name usado
  module_pattern?: string;         // Pattern de module usado
}

// Atualizar MonitoringType para incluir matched_rule
export interface MonitoringType {
  id: string;
  display_name: string;
  category: string;
  job_name: string;
  exporter_type: string;
  module?: string;
  fields?: string[];
  metrics_path: string;
  server?: string;
  servers?: string[];
  form_schema?: FormSchema;
  job_config?: any;
  matched_rule?: MatchedRuleInfo;  // NOVO: Informação da regra que categorizou
}
```

**Localização no arquivo**: Adicionar após a interface FormSchema existente (~linha 30)

---

### Tarefa 1.2: Modificar Engine de Categorização (Backend)

**Arquivo**: `backend/core/categorization_rule_engine.py`

**Modificar método `categorize()`** (linhas 271-349):

```python
def categorize(self, job_data: Dict) -> tuple:
    """
    Categoriza um job baseado nas regras

    Retorna:
        Tupla (categoria, type_info) onde type_info agora inclui matched_rule
    """
    # ... código existente de extração de module ...

    if not self.rules:
        return self._default_categorize(job_data)

    # Aplicar regras em ordem de prioridade
    for rule in self.rules:
        if rule.matches(job_data):
            logger.debug(
                f"[CATEGORIZE] '{job_data.get('job_name')}' → "
                f"'{rule.category}' (regra: {rule.id}, prioridade: {rule.priority})"
            )

            # Determinar quais patterns fizeram match
            job_name = job_data.get('job_name', '').lower()
            module = job_data.get('module', '')

            job_pattern_matched = False
            module_pattern_matched = False

            # Verificar job_name_pattern
            if 'job_name_pattern' in rule.conditions:
                pattern = rule._compiled_patterns.get('job_name_pattern')
                if pattern and pattern.match(job_name):
                    job_pattern_matched = True

            # Verificar module_pattern
            if 'module_pattern' in rule.conditions and module:
                pattern = rule._compiled_patterns.get('module_pattern')
                if pattern and pattern.match(module):
                    module_pattern_matched = True

            type_info = {
                'id': job_data.get('module') or job_data.get('job_name'),
                'display_name': rule.display_name or self._format_display_name(job_data.get('job_name', '')),
                'exporter_type': rule.exporter_type or 'custom',
                'priority': rule.priority,
                # NOVO: Informação detalhada do match
                'matched_rule': {
                    'id': rule.id,
                    'priority': rule.priority,
                    'job_pattern_matched': job_pattern_matched,
                    'module_pattern_matched': module_pattern_matched,
                    'job_pattern': rule.conditions.get('job_name_pattern'),
                    'module_pattern': rule.conditions.get('module_pattern')
                }
            }

            if job_data.get('module'):
                type_info['module'] = job_data['module']

            return rule.category, type_info

    return self._default_categorize(job_data)

def _default_categorize(self, job_data: Dict) -> tuple:
    """Categorização padrão - atualizado para incluir matched_rule vazio"""
    job_name = job_data.get('job_name', 'unknown')

    type_info = {
        'id': job_data.get('module') or job_name,
        'display_name': self._format_display_name(job_name),
        'exporter_type': 'custom',
        # NOVO: matched_rule nulo para categoria padrão
        'matched_rule': None
    }

    if job_data.get('module'):
        type_info['module'] = job_data['module']

    return self.default_category, type_info
```

---

### Tarefa 1.3: Propagar matched_rule nos tipos extraídos (Backend)

**Arquivo**: `backend/api/monitoring_types_dynamic.py`

**Modificar função `extract_types_from_prometheus_jobs()`** (~linhas 127-250):

Após a chamada de `rule_engine.categorize(job_data)`, garantir que `matched_rule` é incluído no tipo:

```python
# Dentro do loop de jobs
category, type_info = rule_engine.categorize(job_data)

monitoring_type = {
    'id': type_info['id'],
    'display_name': type_info['display_name'],
    'category': category,
    'job_name': job_name,
    'exporter_type': type_info['exporter_type'],
    'module': type_info.get('module'),
    'metrics_path': metrics_path,
    'server': server_host,
    'matched_rule': type_info.get('matched_rule')  # NOVO: Incluir informação do match
}
```

---

## Fase 2: Componente Global Regex Validator (Frontend)

### Tarefa 2.1: Criar Componente GlobalRegexValidator

**Arquivo**: `frontend/src/components/GlobalRegexValidator.tsx` (NOVO)

**Conteúdo completo**:

```typescript
/**
 * GlobalRegexValidator - Modal para testar categorização global de regras
 *
 * Permite ao usuário informar job_name, module e metrics_path para ver
 * em qual(is) regra(s) o job cairia.
 *
 * SPEC-REGEX-001
 */

import React, { useState, useMemo } from 'react';
import {
  Modal,
  Form,
  Input,
  Select,
  Button,
  Alert,
  Tag,
  List,
  Typography,
  Space,
  Tooltip,
  Divider,
  Empty,
  Card,
} from 'antd';
import {
  ExperimentOutlined,
  CheckCircleFilled,
  WarningFilled,
  InfoCircleOutlined,
  SearchOutlined,
  TrophyFilled,
} from '@ant-design/icons';

const { Text, Title } = Typography;

// Interface da regra (reutilizada de MonitoringRules)
interface CategorizationRule {
  id: string;
  priority: number;
  category: string;
  display_name: string;
  exporter_type?: string;
  conditions: {
    job_name_pattern?: string;
    metrics_path?: string;
    module_pattern?: string;
  };
  observations?: string;
}

// Resultado do match
interface MatchResult {
  rule: CategorizationRule;
  jobPatternMatched: boolean;
  modulePatternMatched: boolean;
  isApplied: boolean; // Se é a regra que seria aplicada (maior prioridade)
}

interface GlobalRegexValidatorProps {
  visible: boolean;
  onClose: () => void;
  rules: CategorizationRule[];
  categoryColors?: Record<string, string>;
}

// Cores padrão das categorias
const DEFAULT_CATEGORY_COLORS: Record<string, string> = {
  'network-probes': 'purple',
  'web-probes': 'cyan',
  'system-exporters': 'green',
  'database-exporters': 'magenta',
  'infrastructure-exporters': 'blue',
  'hardware-exporters': 'orange',
  'network-devices': 'gold',
  'custom-exporters': 'default',
};

const GlobalRegexValidator: React.FC<GlobalRegexValidatorProps> = ({
  visible,
  onClose,
  rules,
  categoryColors = DEFAULT_CATEGORY_COLORS,
}) => {
  const [form] = Form.useForm();
  const [results, setResults] = useState<MatchResult[]>([]);
  const [analyzed, setAnalyzed] = useState(false);

  // Analisar categorização
  const handleAnalyze = () => {
    const values = form.getFieldsValue();
    const jobName = (values.job_name || '').toLowerCase();
    const module = (values.module || '').toLowerCase();
    const metricsPath = values.metrics_path || '/metrics';

    if (!jobName) {
      return;
    }

    // Ordenar regras por prioridade (maior primeiro)
    const sortedRules = [...rules].sort((a, b) => b.priority - a.priority);

    const matchResults: MatchResult[] = [];
    let firstMatch = true;

    for (const rule of sortedRules) {
      let jobPatternMatched = false;
      let modulePatternMatched = false;
      let conditionsOk = true;

      // Verificar job_name_pattern
      if (rule.conditions.job_name_pattern) {
        try {
          const regex = new RegExp(rule.conditions.job_name_pattern, 'i');
          jobPatternMatched = regex.test(jobName);

          // Se tem module_pattern e module foi informado, pode ignorar job_name miss
          if (!jobPatternMatched) {
            if (!(rule.conditions.module_pattern && module)) {
              conditionsOk = false;
            }
          }
        } catch (e) {
          conditionsOk = false;
        }
      }

      // Verificar metrics_path
      if (rule.conditions.metrics_path) {
        if (metricsPath !== rule.conditions.metrics_path) {
          conditionsOk = false;
        }
      }

      // Verificar module_pattern
      if (rule.conditions.module_pattern && module) {
        try {
          const regex = new RegExp(rule.conditions.module_pattern, 'i');
          modulePatternMatched = regex.test(module);
          if (!modulePatternMatched) {
            conditionsOk = false;
          }
        } catch (e) {
          conditionsOk = false;
        }
      }

      // Se pelo menos um pattern fez match e todas as condições obrigatórias OK
      if (conditionsOk && (jobPatternMatched || modulePatternMatched)) {
        matchResults.push({
          rule,
          jobPatternMatched,
          modulePatternMatched,
          isApplied: firstMatch,
        });
        firstMatch = false;
      }
    }

    setResults(matchResults);
    setAnalyzed(true);
  };

  // Limpar resultados
  const handleClear = () => {
    form.resetFields();
    setResults([]);
    setAnalyzed(false);
  };

  // Fechar modal
  const handleClose = () => {
    handleClear();
    onClose();
  };

  return (
    <Modal
      title={
        <Space>
          <ExperimentOutlined />
          <span>Testar Categorização Global</span>
        </Space>
      }
      open={visible}
      onCancel={handleClose}
      width={800}
      footer={[
        <Button key="clear" onClick={handleClear}>
          Limpar
        </Button>,
        <Button key="close" onClick={handleClose}>
          Fechar
        </Button>,
        <Button
          key="analyze"
          type="primary"
          icon={<SearchOutlined />}
          onClick={handleAnalyze}
        >
          Analisar Categorização
        </Button>,
      ]}
    >
      {/* Formulário de entrada */}
      <Card size="small" title="Dados para Teste" style={{ marginBottom: 16 }}>
        <Form
          form={form}
          layout="vertical"
          initialValues={{ metrics_path: '/metrics' }}
        >
          <Form.Item
            name="job_name"
            label={
              <Space>
                Job Name
                <Tooltip title="Nome do job no prometheus.yml (ex: icmp, node_exporter, blackbox)">
                  <InfoCircleOutlined style={{ color: '#1890ff' }} />
                </Tooltip>
              </Space>
            }
            rules={[{ required: true, message: 'Job Name é obrigatório' }]}
            help="Digite o nome do job que deseja testar"
          >
            <Input placeholder="Ex: icmp, node_exporter, blackbox, http_2xx" />
          </Form.Item>

          <Form.Item
            name="module"
            label={
              <Space>
                Module (opcional)
                <Tooltip title="Módulo do blackbox exporter (ex: icmp, http_2xx, tcp_connect). Deixe vazio se não for blackbox.">
                  <InfoCircleOutlined style={{ color: '#1890ff' }} />
                </Tooltip>
              </Space>
            }
            help="Preencha apenas se for blackbox exporter com módulo específico"
          >
            <Input placeholder="Ex: icmp, http_2xx, tcp_connect" />
          </Form.Item>

          <Form.Item
            name="metrics_path"
            label={
              <Space>
                Metrics Path
                <Tooltip title="/probe para blackbox exporter, /metrics para outros exporters">
                  <InfoCircleOutlined style={{ color: '#1890ff' }} />
                </Tooltip>
              </Space>
            }
            help="Selecione o endpoint de métricas"
          >
            <Select>
              <Select.Option value="/metrics">/metrics (padrão)</Select.Option>
              <Select.Option value="/probe">/probe (blackbox)</Select.Option>
            </Select>
          </Form.Item>
        </Form>
      </Card>

      {/* Resultados da análise */}
      {analyzed && (
        <>
          <Divider />

          {results.length === 0 ? (
            <Alert
              type="warning"
              showIcon
              icon={<WarningFilled />}
              message="Nenhuma Regra Aplicou"
              description={
                <Space direction="vertical">
                  <Text>O job informado não faz match com nenhuma regra cadastrada.</Text>
                  <Text strong>
                    Categoria de destino: <Tag>custom-exporters</Tag>
                  </Text>
                  <Text type="secondary">
                    Considere criar uma nova regra para categorizar este tipo de job.
                  </Text>
                </Space>
              }
            />
          ) : (
            <>
              <Alert
                type="success"
                showIcon
                icon={<CheckCircleFilled />}
                message={`${results.length} regra(s) fizeram match`}
                description={
                  <Text>
                    A regra aplicada será: <Tag color="green">{results[0].rule.id}</Tag>
                    → Categoria: <Tag color={categoryColors[results[0].rule.category]}>
                      {results[0].rule.category}
                    </Tag>
                  </Text>
                }
                style={{ marginBottom: 16 }}
              />

              <List
                size="small"
                header={
                  <Text strong>
                    Regras que fazem match (ordenadas por prioridade)
                  </Text>
                }
                dataSource={results}
                renderItem={(item, index) => (
                  <List.Item
                    style={{
                      background: item.isApplied ? '#f6ffed' : undefined,
                      padding: '12px',
                      borderRadius: '4px',
                      marginBottom: '8px',
                    }}
                  >
                    <Space direction="vertical" style={{ width: '100%' }}>
                      <Space wrap>
                        {item.isApplied && (
                          <Tag color="success" icon={<TrophyFilled />}>
                            APLICADA
                          </Tag>
                        )}
                        <Text strong>{item.rule.id}</Text>
                        <Tag color="blue">Prioridade: {item.rule.priority}</Tag>
                        <Tag color={categoryColors[item.rule.category]}>
                          {item.rule.category}
                        </Tag>
                      </Space>

                      <Space wrap>
                        {item.rule.display_name && (
                          <Text type="secondary">
                            Display: {item.rule.display_name}
                          </Text>
                        )}
                      </Space>

                      <Space wrap>
                        {item.jobPatternMatched && (
                          <Tooltip title={`Pattern: ${item.rule.conditions.job_name_pattern}`}>
                            <Tag color="green" icon={<CheckCircleFilled />}>
                              job_name_pattern match
                            </Tag>
                          </Tooltip>
                        )}
                        {item.modulePatternMatched && (
                          <Tooltip title={`Pattern: ${item.rule.conditions.module_pattern}`}>
                            <Tag color="green" icon={<CheckCircleFilled />}>
                              module_pattern match
                            </Tag>
                          </Tooltip>
                        )}
                        {item.rule.conditions.metrics_path && (
                          <Tag color="blue">
                            metrics_path: {item.rule.conditions.metrics_path}
                          </Tag>
                        )}
                      </Space>
                    </Space>
                  </List.Item>
                )}
              />
            </>
          )}
        </>
      )}

      {!analyzed && (
        <Empty
          image={Empty.PRESENTED_IMAGE_SIMPLE}
          description="Preencha os dados e clique em 'Analisar Categorização'"
        />
      )}
    </Modal>
  );
};

export default GlobalRegexValidator;
```

---

### Tarefa 2.2: Integrar Modal em MonitoringRules

**Arquivo**: `frontend/src/pages/MonitoringRules.tsx`

**Modificações**:

1. **Importar componente** (após outros imports, ~linha 63):
```typescript
import GlobalRegexValidator from '../components/GlobalRegexValidator';
```

2. **Adicionar estado** (após outros estados, ~linha 250):
```typescript
const [globalValidatorVisible, setGlobalValidatorVisible] = useState(false);
```

3. **Adicionar botão na toolbar** (dentro de toolBarRender da ProTable, ~linha 550):
```typescript
toolBarRender={() => [
  <Button
    key="test-global"
    icon={<ExperimentOutlined />}
    onClick={() => setGlobalValidatorVisible(true)}
  >
    Testar Categorização
  </Button>,
  <Button
    key="add"
    type="primary"
    icon={<PlusOutlined />}
    onClick={handleAdd}
  >
    Nova Regra
  </Button>,
  // ... outros botões existentes
]}
```

4. **Adicionar modal** (no final do return, antes do último `</PageContainer>`):
```typescript
{/* Modal de Validação Global */}
<GlobalRegexValidator
  visible={globalValidatorVisible}
  onClose={() => setGlobalValidatorVisible(false)}
  rules={rulesData?.rules || []}
  categoryColors={CATEGORY_COLORS}
/>
```

---

## Fase 3: Match Columns em MonitoringTypes (Frontend)

### Tarefa 3.1: Adicionar Colunas no columnConfig

**Arquivo**: `frontend/src/pages/MonitoringTypes.tsx`

**Modificar array columnConfig** (~linha 145):

```typescript
// Adicionar após a coluna 'servers' e antes de 'actions'
const [columnConfig, setColumnConfig] = useState<ColumnConfig[]>([
  { key: 'display_name', title: 'Nome', visible: true, width: 250 },
  { key: 'job_name', title: 'Job Name', visible: true, width: 200 },
  { key: 'exporter_type', title: 'Exporter Type', visible: true, width: 180 },
  { key: 'module', title: 'Módulo', visible: true, width: 120 },
  { key: 'fields', title: 'Campos Metadata', visible: true, width: 300 },
  { key: 'servers', title: 'Servidores', visible: true, width: 200 },
  // NOVAS COLUNAS - SPEC-REGEX-001
  { key: 'matched_rule_job', title: 'Regra Job', visible: true, width: 150 },
  { key: 'matched_rule_module', title: 'Regra Módulo', visible: true, width: 150 },
  { key: 'actions', title: 'Ações', visible: true, width: 280 },
]);
```

---

### Tarefa 3.2: Implementar Renderização das Colunas

**Arquivo**: `frontend/src/pages/MonitoringTypes.tsx`

**Adicionar colunas na função que gera tableColumns** (provavelmente dentro de useMemo ou getColumns):

```typescript
// Coluna: Regra Job
{
  title: 'Regra Job',
  dataIndex: ['matched_rule', 'id'],
  key: 'matched_rule_job',
  width: 150,
  render: (_: any, record: MonitoringType) => {
    if (!record.matched_rule || !record.matched_rule.job_pattern_matched) {
      return <Text type="secondary">-</Text>;
    }
    return (
      <Tooltip
        title={
          <Space direction="vertical" size={0}>
            <Text style={{ color: 'white' }}>
              Pattern: {record.matched_rule.job_pattern || 'N/A'}
            </Text>
            <Text style={{ color: 'white' }}>
              Prioridade: {record.matched_rule.priority}
            </Text>
          </Space>
        }
      >
        <Tag color="blue">{record.matched_rule.id}</Tag>
      </Tooltip>
    );
  },
},

// Coluna: Regra Módulo
{
  title: 'Regra Módulo',
  dataIndex: ['matched_rule', 'id'],
  key: 'matched_rule_module',
  width: 150,
  render: (_: any, record: MonitoringType) => {
    if (!record.matched_rule || !record.matched_rule.module_pattern_matched) {
      return <Text type="secondary">-</Text>;
    }
    return (
      <Tooltip
        title={
          <Space direction="vertical" size={0}>
            <Text style={{ color: 'white' }}>
              Pattern: {record.matched_rule.module_pattern || 'N/A'}
            </Text>
            <Text style={{ color: 'white' }}>
              Prioridade: {record.matched_rule.priority}
            </Text>
          </Space>
        }
      >
        <Tag color="green">{record.matched_rule.id}</Tag>
      </Tooltip>
    );
  },
},
```

---

## Fase 4: Testes e Validação COMPLETOS

### Tarefa 4.1: Testes do Global Regex Validator

#### Teste 1: Job Simples (node_exporter)
```
Input: Job Name = "node_exporter", Module = vazio, Metrics Path = "/metrics"
Esperado: Match com regra de system-exporters
Validar: Tag "APLICADA" na regra correta
```

#### Teste 2: Blackbox ICMP
```
Input: Job Name = "icmp", Module = "icmp", Metrics Path = "/probe"
Esperado: Match com regra de network-probes
Validar: Tags "job_name_pattern match" e "module_pattern match"
```

#### Teste 3: Blackbox HTTP
```
Input: Job Name = "blackbox", Module = "http_2xx", Metrics Path = "/probe"
Esperado: Match com regra de web-probes
Validar: Prioridade mostrada, categoria correta
```

#### Teste 4: Job Sem Match
```
Input: Job Name = "meu_job_customizado", Module = vazio, Metrics Path = "/metrics"
Esperado: Nenhuma regra aplica
Validar: Alert "Nenhuma Regra Aplicou", mensagem de custom-exporters
```

#### Teste 5: Lógica AND (Todas Condições)
```
Input: Job Name = "blackbox", Module = "icmp", Metrics Path = "/probe"
Regra: job=^blackbox, module=^icmp, path=/probe
Esperado: Match porque TODAS condições batem
Validar: Todas as tags de match aparecem
```

#### Teste 6: Lógica AND (Uma Falha)
```
Input: Job Name = "blackbox", Module = "tcp_connect", Metrics Path = "/probe"
Regra: job=^blackbox, module=^icmp, path=/probe
Esperado: NÃO match porque module_pattern falhou
Validar: Regra não aparece na lista de matches
```

#### Teste 7: Prioridade entre Regras
```
Regras:
  - specific_icmp (prioridade 100): job=^blackbox, module=^icmp
  - generic_blackbox (prioridade 80): job=^blackbox

Input: Job Name = "blackbox", Module = "icmp", Metrics Path = "/probe"
Esperado: Ambas fazem match, mas specific_icmp é APLICADA
Validar: Lista mostra 2 regras, apenas a primeira com tag APLICADA
```

#### Teste 8: Metrics Path Errado
```
Input: Job Name = "blackbox", Module = "icmp", Metrics Path = "/metrics"
Regra: job=^blackbox, module=^icmp, path=/probe
Esperado: NÃO match porque metrics_path ≠ /probe
Validar: Regra não aparece na lista
```

#### Teste 9: Case Insensitive
```
Input: Job Name = "NODE_EXPORTER", Module = vazio, Metrics Path = "/metrics"
Esperado: Match com regra ^node.* (case insensitive)
Validar: Match funciona independente de maiúsculas
```

#### Teste 10: Regex Complexo
```
Input: Job Name = "postgres_exporter_db1", Module = vazio, Metrics Path = "/metrics"
Regra: job=^(postgres|mysql)_exporter.*
Esperado: Match com regra de database-exporters
Validar: Regex com grupos funciona corretamente
```

### Tarefa 4.2: Testes das Match Columns

#### Teste 1: Colunas Visíveis
1. Acessar `/monitoring-types`
2. Verificar colunas "Regra Job" e "Regra Módulo" aparecem
3. Verificar posição (após Servidores, antes de Ações)

#### Teste 2: Tooltip com Detalhes
1. Passar mouse sobre tag na coluna "Regra Job"
2. Verificar tooltip mostra Pattern e Prioridade

#### Teste 3: Tipo com Módulo
1. Encontrar tipo com módulo (ex: http_2xx)
2. Verificar ambas colunas preenchidas
3. Verificar cores das tags (azul para job, verde para module)

#### Teste 4: Tipo sem Módulo
1. Encontrar tipo sem módulo (ex: node_exporter)
2. Verificar "Regra Job" preenchida
3. Verificar "Regra Módulo" mostra "-"

#### Teste 5: ColumnSelector
1. Abrir seletor de colunas
2. Verificar novas colunas aparecem
3. Ocultar uma coluna e verificar persistência

### Tarefa 4.3: Testes de Graceful Degradation

1. Limpar cache KV de monitoring-types
2. Forçar nova extração via SSH
3. Verificar tipos novos têm matched_rule
4. Simular dados antigos (sem matched_rule) e verificar "-" nas colunas

### Tarefa 4.4: Testes de Performance

1. Criar 50+ regras no sistema
2. Executar análise no GlobalRegexValidator
3. Medir tempo de resposta (<100ms aceitável)
4. Verificar sem travamento da interface

---

## Resumo dos Arquivos

| Arquivo | Operação | Descrição |
|---------|----------|-----------|
| `frontend/src/types/monitoring.ts` | EDITAR | Adicionar interface MatchedRuleInfo |
| `backend/core/categorization_rule_engine.py` | EDITAR | Modificar categorize() para retornar matched_rule |
| `backend/api/monitoring_types_dynamic.py` | EDITAR | Propagar matched_rule nos tipos |
| `frontend/src/components/GlobalRegexValidator.tsx` | **CRIAR** | Novo componente do modal |
| `frontend/src/pages/MonitoringRules.tsx` | EDITAR | Integrar botão e modal |
| `frontend/src/pages/MonitoringTypes.tsx` | EDITAR | Adicionar 2 colunas de match |

---

## Ordem de Execução Recomendada

1. **Fase 1** (Backend + Types) - ~30 min
2. **Fase 2** (GlobalRegexValidator) - ~45 min
3. **Fase 3** (Match Columns) - ~30 min
4. **Fase 4** (Testes) - ~30 min

**Tempo total estimado**: ~2h 15min

---

## Checklist de Implementação

- [ ] Tipos TypeScript atualizados
- [ ] Backend retornando matched_rule
- [ ] Componente GlobalRegexValidator criado
- [ ] Botão na toolbar de MonitoringRules
- [ ] Modal funcional com análise
- [ ] Colunas adicionadas em MonitoringTypes
- [ ] Tooltips com patterns
- [ ] Testes manuais passando
- [ ] Graceful degradation funcionando
