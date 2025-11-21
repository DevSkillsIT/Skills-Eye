/**
 * GlobalRegexValidator - Modal para testar categorizacao global de regras
 *
 * SPEC-REGEX-001: Permite ao usuario informar job_name, module e metrics_path
 * para ver em qual(is) regra(s) o job cairia.
 *
 * FUNCIONALIDADES:
 * - Testa valores contra todas as regras carregadas
 * - Mostra todas as regras que fariam match
 * - Destaca a regra que seria aplicada (maior prioridade)
 * - Mostra qual pattern fez match (job_name e/ou module)
 * - Validacao local sem chamada ao backend
 *
 * AUTOR: Sistema de Refatoracao Skills Eye v2.0
 * DATA: 2025-11-21
 */

import React, { useState } from 'react';
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

const { Text } = Typography;

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
  isApplied: boolean; // Se e a regra que seria aplicada (maior prioridade)
}

interface GlobalRegexValidatorProps {
  visible: boolean;
  onClose: () => void;
  rules: CategorizationRule[];
  categoryColors?: Record<string, string>;
}

// Cores padrao das categorias
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

  // Analisar categorizacao
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

      // Verificar metrics_path primeiro (match exato)
      if (rule.conditions.metrics_path) {
        if (metricsPath !== rule.conditions.metrics_path) {
          conditionsOk = false;
        }
      }

      // Verificar job_name_pattern
      if (conditionsOk && rule.conditions.job_name_pattern) {
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
          // Regex invalida - ignorar esta regra
          conditionsOk = false;
        }
      }

      // Verificar module_pattern
      if (conditionsOk && rule.conditions.module_pattern && module) {
        try {
          const regex = new RegExp(rule.conditions.module_pattern, 'i');
          modulePatternMatched = regex.test(module);
          if (!modulePatternMatched) {
            conditionsOk = false;
          }
        } catch (e) {
          // Regex invalida - ignorar esta regra
          conditionsOk = false;
        }
      }

      // Se pelo menos um pattern fez match e todas as condicoes obrigatorias OK
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
          <span>Testar Categorizacao Global</span>
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
          Analisar Categorizacao
        </Button>,
      ]}
    >
      {/* Formulario de entrada */}
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
            rules={[{ required: true, message: 'Job Name e obrigatorio' }]}
            help="Digite o nome do job que deseja testar"
          >
            <Input placeholder="Ex: icmp, node_exporter, blackbox, http_2xx" />
          </Form.Item>

          <Form.Item
            name="module"
            label={
              <Space>
                Module (opcional)
                <Tooltip title="Modulo do blackbox exporter (ex: icmp, http_2xx, tcp_connect). Deixe vazio se nao for blackbox.">
                  <InfoCircleOutlined style={{ color: '#1890ff' }} />
                </Tooltip>
              </Space>
            }
            help="Preencha apenas se for blackbox exporter com modulo especifico"
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
            help="Selecione o endpoint de metricas"
          >
            <Select>
              <Select.Option value="/metrics">/metrics (padrao)</Select.Option>
              <Select.Option value="/probe">/probe (blackbox)</Select.Option>
            </Select>
          </Form.Item>
        </Form>
      </Card>

      {/* Resultados da analise */}
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
                  <Text>O job informado nao faz match com nenhuma regra cadastrada.</Text>
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
                    A regra aplicada sera: <Tag color="green">{results[0].rule.id}</Tag>
                    {' -> '} Categoria: <Tag color={categoryColors[results[0].rule.category]}>
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
                renderItem={(item) => (
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
          description="Preencha os dados e clique em 'Analisar Categorizacao'"
        />
      )}
    </Modal>
  );
};

export default GlobalRegexValidator;
