/**
 * Página de Gerenciamento de Regras de Categorização
 *
 * Permite visualizar, editar, adicionar e remover regras de categorização
 * de tipos de monitoramento.
 *
 * FUNCIONALIDADES:
 * - CRUD completo de regras
 * - Ordenação por prioridade
 * - Filtros por categoria
 * - Validação de regex patterns com feedback visual
 * - Preview de regras antes de salvar
 * - Teste de Regex em tempo real
 *
 * AUTOR: Sistema de Refatoração Skills Eye v2.0
 * DATA: 2025-11-21
 */

import React, { useState, useRef, useEffect, useMemo } from 'react';
import {
  PageContainer,
  ProTable,
  ProForm,
  ProFormText,
  ProFormDigit,
  ProFormSelect,
  ProFormTextArea,
  ProFormDependency,
} from '@ant-design/pro-components';
import type { ActionType, ProColumns } from '@ant-design/pro-components';
import {
  Button,
  Tag,
  Modal,
  Form,
  Space,
  Tooltip,
  message,
  Popconfirm,
  Badge,
  Descriptions,
  Row,
  Col,
  Input,
  Alert,
  Divider,
  Card,
  Typography,
} from 'antd';
import type { SorterResult, FilterValue } from 'antd/es/table/interface';
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  ReloadOutlined,
  InfoCircleOutlined,
  ClearOutlined,
  FilterOutlined,
  CopyOutlined,
  ExperimentOutlined,
  CheckCircleFilled,
} from '@ant-design/icons';
import { consulAPI } from '../services/api';
import GlobalRegexValidator from '../components/GlobalRegexValidator';

const { Text } = Typography;

// ============================================================================
// INTERFACES
// ============================================================================

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

interface RulesData {
  version: string;
  last_updated: string;
  total_rules: number;
  rules: CategorizationRule[];
  default_category: string;
  categories: Array<{
    id: string;
    display_name: string;
  }>;
}

// ============================================================================
// CONSTANTES
// ============================================================================

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

const PRIORITY_LEVELS = [
  { value: 100, label: '100 - Máxima (Blackbox)', color: 'red' },
  { value: 90, label: '90 - Muito Alta', color: 'volcano' },
  { value: 80, label: '80 - Alta (Exporters)', color: 'orange' },
  { value: 70, label: '70 - Média-Alta', color: 'gold' },
  { value: 60, label: '60 - Média', color: 'lime' },
  { value: 50, label: '50 - Baixa', color: 'green' },
];

// ============================================================================
// HELPERS
// ============================================================================

const validateRegex = (_: any, value: string) => {
  if (!value) return Promise.resolve();
  try {
    new RegExp(value);
    return Promise.resolve();
  } catch (e) {
    return Promise.reject(new Error('Expressão Regular inválida'));
  }
};

const isSimpleRegex = (pattern: string): boolean => {
  if (!pattern) return false;
  // Verifica se contém caracteres especiais comuns de regex
  const specialChars = /[\^$*+?()\[\]{}|\\]/;
  return !specialChars.test(pattern);
};

// ============================================================================
// COMPONENTES AUXILIARES
// ============================================================================

interface RegexTesterProps {
  pattern: string;
  placeholder: string;
  title: string;
}

const RegexTester: React.FC<RegexTesterProps> = ({ pattern, placeholder, title }) => {
  const [result, setResult] = useState<{ match: boolean; value: string } | null>(null);
  const [testValue, setTestValue] = useState('');

  // Limpa o resultado quando o padrão muda
  useEffect(() => {
    setResult(null);
  }, [pattern]);

  const handleSearch = () => {
    if (!testValue) {
      setResult(null);
      return;
    }
    try {
      const regex = new RegExp(pattern);
      const match = regex.test(testValue);
      setResult({ match, value: testValue });
    } catch (e) {
      message.error('Regex inválido para teste');
    }
  };

  return (
    <Card size="small" type="inner" title={title} style={{ marginTop: 8 }}>
      <Space.Compact style={{ width: '100%' }}>
        <Input
          placeholder={placeholder}
          size="small"
          value={testValue}
          onChange={(e) => setTestValue(e.target.value)}
          onPressEnter={handleSearch}
        />
        <Button
          icon={<ExperimentOutlined />}
          size="small"
          onClick={handleSearch}
        >
          Testar
        </Button>
      </Space.Compact>
      {result && (
        <Alert
          style={{ marginTop: 12 }}
          type={result.match ? 'success' : 'warning'}
          showIcon
          message={result.match ? "Match Confirmado!" : "Nenhum Match"}
          description={
            <Space direction="vertical" size={0}>
              <Text style={{ fontSize: '12px' }}>
                {result.match
                  ? 'O valor testado corresponde ao padrão configurado.'
                  : 'O valor testado NÃO corresponde ao padrão.'
                }
              </Text>
              <div style={{ marginTop: 4, fontSize: '12px' }}>
                <strong>Valor:</strong> <Text code>{result.value}</Text>
              </div>
              <div style={{ fontSize: '12px' }}>
                <strong>Padrão:</strong> <Text code>{pattern}</Text>
              </div>
            </Space>
          }
        />
      )}
    </Card>
  );
};

// ============================================================================
// COMPONENTE PRINCIPAL
// ============================================================================

const MonitoringRules: React.FC = () => {
  const actionRef = useRef<ActionType>(undefined);
  // @ts-ignore - Form.useForm signature mismatch in some versions
  const [form] = Form.useForm();

  // Estados
  const [modalVisible, setModalVisible] = useState(false);
  const [editingRule, setEditingRule] = useState<CategorizationRule | null>(null);
  const [previewVisible, setPreviewVisible] = useState(false);
  const [rulesData, setRulesData] = useState<RulesData | null>(null);
  const [showModalInfo, setShowModalInfo] = useState(false);
  // SPEC-REGEX-001: Estado para modal de teste global
  const [globalValidatorVisible, setGlobalValidatorVisible] = useState(false);

  // Estados para controle de filtros e ordenação
  const [filteredInfo, setFilteredInfo] = useState<Record<string, FilterValue | null>>({});
  const [sortedInfo, setSortedInfo] = useState<SorterResult<CategorizationRule>>({
    columnKey: 'priority',
    order: 'descend',
  });

  // Auto-dismiss do alerta do modal
  useEffect(() => {
    let timer: ReturnType<typeof setTimeout>;
    if (showModalInfo) {
      timer = setTimeout(() => {
        setShowModalInfo(false);
      }, 15000);
    }
    return () => clearTimeout(timer);
  }, [showModalInfo]);

  const clearFilters = () => {
    setFilteredInfo({});
    actionRef.current?.reload();
  };

  const clearAll = () => {
    setFilteredInfo({});
    setSortedInfo({});
    // Força um reload limpo, confiando no estado controlado das colunas
    setTimeout(() => {
      actionRef.current?.reload();
    }, 0);
  };

  // =========================================================================
  // CARREGAMENTO DE DADOS
  // =========================================================================

  const loadRules = async () => {
    try {
      const response = await consulAPI.getCategorizationRules();
      const payload = (response && (response as any).data) ? (response as any).data : response;

      if (payload && payload.success && payload.data) {
        setRulesData(payload.data);
        // Garantir ordenação padrão por prioridade (decrescente)
        const rules = payload.data.rules || [];
        const sortedRules = [...rules].sort((a: CategorizationRule, b: CategorizationRule) => b.priority - a.priority);

        return {
          data: sortedRules,
          success: true,
          total: payload.data.total_rules || 0,
        };
      }

      console.warn('getCategorizationRules: payload inesperado', payload);
      throw new Error('Erro ao carregar regras');
    } catch (error: any) {
      message.error('Erro ao carregar regras: ' + (error.message || error));
      return {
        data: [],
        success: false,
        total: 0,
      };
    }
  };

  // =========================================================================
  // HANDLERS
  // =========================================================================

  const handleAdd = () => {
    setEditingRule(null);
    setShowModalInfo(true);
    setModalVisible(true);
  };

  const handleEdit = (record: CategorizationRule) => {
    setEditingRule(record);
    setShowModalInfo(true);
    setModalVisible(true);
  };

  const handleDuplicate = (record: CategorizationRule) => {
    setEditingRule({
      ...record,
      id: `${record.id}_copy`,
      display_name: `${record.display_name} (Cópia)`,
    });
    setShowModalInfo(true);
    setModalVisible(true);
  };

  const handleDelete = async (ruleId: string) => {
    try {
      const axiosResponse = await consulAPI.deleteCategorizationRule(ruleId);
      const response = (axiosResponse && (axiosResponse as any).data)
        ? (axiosResponse as any).data
        : axiosResponse;

      if (response.success) {
        message.success('Regra excluída com sucesso');
        actionRef.current?.reload();
      } else {
        throw new Error(response.message || 'Erro ao excluir regra');
      }
    } catch (error: any) {
      message.error('Erro ao excluir: ' + (error.message || error));
    }
  };

  const handleSave = async () => {
    try {
      const values = await form.validateFields();

      const rule: CategorizationRule = {
        id: values.id,
        priority: values.priority,
        category: values.category,
        display_name: values.display_name,
        exporter_type: values.exporter_type,
        conditions: {
          job_name_pattern: values.job_name_pattern,
          metrics_path: values.metrics_path,
          module_pattern: values.module_pattern,
        },
        observations: values.observations,
      };

      let axiosResponse;
      // Simplificação: Se o ID existe no backend, é update? Não, o ID é a chave.
      // Vamos confiar no editingRule.id vs values.id?
      // Se eu clico em editar, editingRule tem o ID original. O form tem o ID original (disabled).
      // Se eu clico em duplicar, editingRule tem ID _copy. O form tem ID _copy.
      // Então se editingRule.id == values.id E não é _copy... mas o usuário pode mudar o ID no duplicar.

      // Vamos assumir: Create se não existir, Update se existir? A API decide?
      // Geralmente: POST para criar, PUT para atualizar.
      // Vamos manter a lógica: se editingRule existe E o ID dele é igual ao do form (e não estamos no modo duplicação explícito)...
      // Na verdade, o handleDuplicate seta editingRule.

      // Ajuste: handleDuplicate deve setar editingRule como null mas preencher o form?
      // Não, pois mudamos para initialValues.
      // Então handleDuplicate deve setar um estado "initialValues" ou usar editingRule como "template".

      // Vamos usar uma flag "isEditMode".

      // Revertendo para a lógica simples:
      // Se o ID do form já existe na lista (e não estamos criando um novo com esse ID), é update.
      // Mas a API de update pede o ID na URL.

      // Vamos simplificar:
      // Se editingRule não é null E editingRule.id === values.id, é update.
      // Caso contrário (incluindo duplicar onde mudamos o ID), é create.

      if (editingRule && editingRule.id === values.id) {
        axiosResponse = await consulAPI.updateCategorizationRule(rule.id, rule);
      } else {
        axiosResponse = await consulAPI.createCategorizationRule(rule);
      }

      const response = (axiosResponse && (axiosResponse as any).data)
        ? (axiosResponse as any).data
        : axiosResponse;

      if (response.success) {
        message.success('Operação realizada com sucesso');
        setModalVisible(false);
        actionRef.current?.reload();
      } else {
        throw new Error(response.message || 'Erro ao salvar regra');
      }
    } catch (error: any) {
      if (error.errorFields) {
        message.error('Preencha todos os campos obrigatórios');
      } else {
        message.error('Erro ao salvar: ' + (error.message || error));
      }
    }
  };

  const handlePreview = () => {
    setPreviewVisible(true);
  };

  // =========================================================================
  // COLUNAS DA TABELA
  // =========================================================================

  const columns: ProColumns<CategorizationRule>[] = useMemo(() => [
    {
      title: 'ID',
      dataIndex: 'id',
      key: 'id',
      width: 180,
      fixed: 'left',
      ellipsis: true,
      render: (text) => <code style={{ fontSize: '12px' }}>{text}</code>,
      filteredValue: null, // Para satisfazer o warning de "all or nothing"
    },
    {
      title: 'Prioridade',
      dataIndex: 'priority',
      key: 'priority',
      width: 120,
      sorter: (a, b) => b.priority - a.priority,
      sortOrder: sortedInfo.columnKey === 'priority' ? sortedInfo.order : null,
      render: (_, record) => {
        const level = PRIORITY_LEVELS.find(l => l.value === record.priority);
        return (
          <Tooltip title={level?.label || `Prioridade ${record.priority}`}>
            <Tag color={level?.color || 'default'}>{record.priority}</Tag>
          </Tooltip>
        );
      },
      filteredValue: null,
    },
    {
      title: 'Categoria',
      dataIndex: 'category',
      key: 'category',
      width: 200,
      sorter: (a, b) => (a.category || '').localeCompare(b.category || ''),
      sortOrder: sortedInfo.columnKey === 'category' ? sortedInfo.order : null,
      filters: rulesData?.categories?.map(c => ({
        text: c.display_name,
        value: c.id,
      })) || [],
      filteredValue: filteredInfo.category || null,
      onFilter: (value, record) => record.category === value,
      render: (_, record) => (
        <Tag color={CATEGORY_COLORS[record.category] || 'default'}>
          {rulesData?.categories?.find(c => c.id === record.category)?.display_name || record.category}
        </Tag>
      ),
    },
    {
      title: 'Display Name',
      dataIndex: 'display_name',
      key: 'display_name',
      width: 250,
      ellipsis: true,
      sorter: (a, b) => (a.display_name || '').localeCompare(b.display_name || ''),
      sortOrder: sortedInfo.columnKey === 'display_name' ? sortedInfo.order : null,
      filters: Array.from(new Set(rulesData?.rules?.map(r => r.display_name) || [])).map(name => ({
        text: name,
        value: name,
      })),
      filteredValue: filteredInfo.display_name || null,
      onFilter: (value, record) => record.display_name === value,
    },
    {
      title: 'Exporter Type',
      dataIndex: 'exporter_type',
      key: 'exporter_type',
      width: 180,
      ellipsis: true,
      sorter: (a, b) => (a.exporter_type || '').localeCompare(b.exporter_type || ''),
      sortOrder: sortedInfo.columnKey === 'exporter_type' ? sortedInfo.order : null,
      filters: Array.from(new Set((rulesData?.rules?.map(r => r.exporter_type) || []).filter(Boolean))).map(type => ({
        text: type as string,
        value: type as string,
      })),
      filteredValue: filteredInfo.exporter_type || null,
      onFilter: (value, record) => record.exporter_type === value,
      render: (text) => text ? <Tag color="blue">{text}</Tag> : '-',
    },
    {
      title: 'Job Pattern',
      dataIndex: ['conditions', 'job_name_pattern'],
      key: 'job_name_pattern',
      width: 180,
      ellipsis: true,
      filters: Array.from(new Set((rulesData?.rules?.map(r => r.conditions.job_name_pattern) || []).filter(Boolean))).map(pattern => ({
        text: pattern as string,
        value: pattern as string,
      })),
      filteredValue: filteredInfo.job_name_pattern || null,
      onFilter: (value, record) => record.conditions.job_name_pattern === value,
      render: (text) => text ? <code style={{ fontSize: '11px' }}>{text}</code> : '-',
    },
    {
      title: 'Metrics Path',
      dataIndex: ['conditions', 'metrics_path'],
      key: 'metrics_path',
      width: 120,
      filters: [
        { text: '/probe', value: '/probe' },
        { text: '/metrics', value: '/metrics' },
      ],
      filteredValue: filteredInfo.metrics_path || null,
      onFilter: (value, record) => record.conditions.metrics_path === value,
      render: (text) => <Tag color={text === '/probe' ? 'orange' : 'green'}>{text || '-'}</Tag>,
    },
    {
      title: 'Module Pattern',
      dataIndex: ['conditions', 'module_pattern'],
      key: 'module_pattern',
      width: 150,
      ellipsis: true,
      filters: Array.from(new Set((rulesData?.rules?.map(r => r.conditions.module_pattern) || []).filter(Boolean))).map(pattern => ({
        text: pattern as string,
        value: pattern as string,
      })),
      filteredValue: filteredInfo.module_pattern || null,
      onFilter: (value, record) => record.conditions.module_pattern === value,
      render: (text) => text ? <code style={{ fontSize: '11px' }}>{text}</code> : '-',
    },
    {
      title: 'Observações',
      dataIndex: 'observations',
      key: 'observations',
      ellipsis: true,
      filteredValue: null,
    },
    {
      title: 'Ações',
      valueType: 'option',
      key: 'option',
      width: 150,
      fixed: 'right',
      filteredValue: null,
      render: (_, record) => (
        <Space size="small">
          <Tooltip title="Editar">
            <Button
              type="link"
              size="small"
              icon={<EditOutlined />}
              onClick={() => handleEdit(record)}
            />
          </Tooltip>
          <Tooltip title="Duplicar">
            <Button
              type="link"
              size="small"
              icon={<CopyOutlined />}
              onClick={() => handleDuplicate(record)}
            />
          </Tooltip>
          <Popconfirm
            title="Confirmar exclusão"
            description={`Deseja realmente excluir a regra "${record.id}"?`}
            onConfirm={() => handleDelete(record.id)}
            okText="Sim"
            cancelText="Não"
            okType="danger"
          >
            <Tooltip title="Deletar">
              <Button
                type="link"
                size="small"
                danger
                icon={<DeleteOutlined />}
              />
            </Tooltip>
          </Popconfirm>
        </Space>
      ),
    },
  ], [rulesData, filteredInfo, sortedInfo]);

  // =========================================================================
  // RENDER
  // =========================================================================

  return (
    <PageContainer
      title="Regras de Categorização"
      subTitle="Defina regras inteligentes para identificar e categorizar automaticamente seus targets do Prometheus baseando-se em padrões de nomes e labels."
    >
      {/* Estatísticas */}
      {rulesData && (
        <div style={{ marginBottom: 16 }}>
          <Space size="large" style={{ marginBottom: 8 }}>
            <Badge count={rulesData.total_rules} showZero color="blue" overflowCount={999}>
              <span style={{ marginRight: 8 }}>Total de Regras</span>
            </Badge>
            <Badge count={rulesData.categories.length} showZero color="green">
              <span style={{ marginRight: 8 }}>Categorias</span>
            </Badge>
            <span style={{ color: '#666', fontSize: '12px' }}>
              Última atualização: {new Date(rulesData.last_updated).toLocaleString('pt-BR')}
            </span>
          </Space>

          {/* Detalhamento por Categoria */}
          <div style={{ marginTop: 4 }}>
            <Space wrap size={[4, 8]}>
              {rulesData.categories.map(cat => {
                const count = rulesData.rules.filter(r => r.category === cat.id).length;
                if (count === 0) return null;
                return (
                  <Tag key={cat.id} color={CATEGORY_COLORS[cat.id] || 'default'} style={{ margin: 0 }}>
                    {cat.display_name}: <strong>{count}</strong>
                  </Tag>
                );
              })}
            </Space>
          </div>
        </div>
      )}

      {/* Tabela de Regras */}
      <ProTable<CategorizationRule>
        actionRef={actionRef}
        columns={columns}
        request={loadRules}
        rowKey="id"
        search={false}
        onChange={(_pagination, filters, sorter) => {
          setFilteredInfo(filters);
          setSortedInfo(sorter as SorterResult<CategorizationRule>);
        }}
        pagination={{
          defaultPageSize: 50,
          showSizeChanger: true,
          pageSizeOptions: ['20', '50', '100', '200'],
          showTotal: (total, range) => `${range[0]}-${range[1]} de ${total} regras`,
        }}
        options={{
          reload: true,
          density: true,
          setting: true,
        }}
        scroll={{ x: 1500 }}
        toolbar={{
          actions: [
            // SPEC-REGEX-001: Botao para testar categorizacao global
            <Button
              key="test-global"
              icon={<ExperimentOutlined />}
              onClick={() => setGlobalValidatorVisible(true)}
            >
              Testar Categorizacao
            </Button>,
            <Button
              key="add"
              type="primary"
              icon={<PlusOutlined />}
              onClick={handleAdd}
            >
              Adicionar Regra
            </Button>,
            <Button
              key="preview"
              icon={<InfoCircleOutlined />}
              onClick={handlePreview}
            >
              Visualizar Resumo
            </Button>,
            <Button
              key="reload"
              icon={<ReloadOutlined />}
              onClick={() => actionRef.current?.reload()}
            >
              Recarregar
            </Button>,
            <Button
              key="clearFilters"
              icon={<FilterOutlined />}
              onClick={clearFilters}
            >
              Limpar Filtros
            </Button>,
            <Button
              key="clearAll"
              icon={<ClearOutlined />}
              onClick={clearAll}
            >
              Limpar Filtros e Ordem
            </Button>,
          ],
        }}
      />

      {/* Modal de Edição/Criação */}
      <Modal
        title={editingRule && !editingRule.id.endsWith('_copy') ? `Editar Regra: ${editingRule.id}` : 'Nova Regra de Categorização'}
        open={modalVisible}
        onCancel={() => setModalVisible(false)}
        onOk={handleSave}
        width={1000}
        okText={editingRule && !editingRule.id.endsWith('_copy') ? 'Salvar Alterações' : 'Criar Regra'}
        cancelText="Cancelar"
        destroyOnHidden
        styles={{ body: { padding: '24px 0 0 0' } }}
      >
        {showModalInfo && (
          <Alert
            message="Como funcionam as Regras"
            description="As regras são avaliadas sequencialmente pela Prioridade (maior primeiro). O primeiro match confirmado no 'Job Name' ou 'Module' aplicará a categoria definida ao target."
            type="info"
            showIcon
            closable
            onClose={() => setShowModalInfo(false)}
            style={{ marginBottom: 24 }}
          />
        )}

        <ProForm
          form={form}
          layout="vertical"
          submitter={false}
          initialValues={editingRule ? {
            id: editingRule.id,
            priority: editingRule.priority,
            category: editingRule.category,
            display_name: editingRule.display_name,
            exporter_type: editingRule.exporter_type,
            job_name_pattern: editingRule.conditions.job_name_pattern,
            metrics_path: editingRule.conditions.metrics_path,
            module_pattern: editingRule.conditions.module_pattern,
            observations: editingRule.observations,
          } : {
            priority: 80,
            metrics_path: '/metrics',
          }}
        >
          <Space direction="vertical" size="small" style={{ width: '100%' }}>

            {/* LINHA 1: Identificação Básica (Compacto) */}
            <Row gutter={16}>
              <Col span={4}>
                <ProFormText
                  name="id"
                  label="ID"
                  placeholder="ex: blackbox_icmp"
                  tooltip="Identificador único e imutável para esta regra no sistema."
                  rules={[
                    { required: true, message: 'Obrigatório' },
                    { pattern: /^[a-z0-9_]+$/, message: 'Inválido' },
                  ]}
                  disabled={!!editingRule && !editingRule.id.endsWith('_copy')}
                  fieldProps={{ size: 'small' }}
                />
              </Col>
              <Col span={8}>
                <ProFormText
                  name="display_name"
                  label="Nome de Exibição"
                  placeholder="ex: ICMP (Ping)"
                  tooltip="Nome amigável que aparecerá nos relatórios e dashboards para representar este grupo de monitores."
                  rules={[{ required: true, message: 'Obrigatório' }]}
                  fieldProps={{ size: 'small' }}
                />
              </Col>
              <Col span={8}>
                <ProFormSelect
                  name="category"
                  label="Categoria"
                  tooltip="Grupo funcional ao qual este monitor pertence (ex: Banco de Dados, Rede, Web Server)."
                  rules={[{ required: true, message: 'Obrigatória' }]}
                  options={rulesData?.categories.map(c => ({
                    label: c.display_name,
                    value: c.id,
                  }))}
                  fieldProps={{ size: 'small' }}
                />
              </Col>
              <Col span={4}>
                <ProFormDigit
                  name="priority"
                  label="Prioridade"
                  tooltip="Define a ordem de avaliação. Regras com maior prioridade vencem conflitos."
                  min={1}
                  max={100}
                  rules={[{ required: true, message: 'Obrigatória' }]}
                  fieldProps={{ size: 'small' }}
                />
              </Col>
            </Row>

            {/* LINHA 2: Detalhes Técnicos */}
            <Row gutter={16}>
              <Col span={6}>
                <ProFormText
                  name="exporter_type"
                  label="Tipo de Exporter"
                  placeholder="ex: blackbox"
                  tooltip="O tipo de exporter que coleta estas métricas (ex: node, blackbox, mysqld)."
                  fieldProps={{ size: 'small' }}
                />
              </Col>
              <Col span={6}>
                <ProFormSelect
                  name="metrics_path"
                  label="Metrics Path"
                  tooltip="O caminho HTTP onde as métricas são expostas pelo target."
                  rules={[{ required: true, message: 'Obrigatório' }]}
                  options={[
                    { label: '/probe', value: '/probe' },
                    { label: '/metrics', value: '/metrics' },
                  ]}
                  fieldProps={{ size: 'small' }}
                />
              </Col>
              <Col span={12}>
                <ProFormTextArea
                  name="observations"
                  label="Observações"
                  placeholder="Anotações opcionais"
                  tooltip="Notas internas para documentar o propósito ou detalhes desta regra."
                  fieldProps={{ rows: 1, size: 'small' }}
                />
              </Col>
            </Row>

            <Divider dashed style={{ margin: '8px 0' }} />

            {/* LINHA 3: Regras de Matching (Lado a Lado) */}
            <Row gutter={16}>
              {/* JOB NAME PATTERN */}
              <Col span={12}>
                <div style={{ background: '#fafafa', padding: '12px', borderRadius: '6px' }}>
                  <ProFormDependency name={['job_name_pattern']}>
                    {({ job_name_pattern }) => {
                      let valid = false;
                      try { if (job_name_pattern) { new RegExp(job_name_pattern); valid = true; } } catch (e) { }

                      return (
                        <ProFormText
                          name="job_name_pattern"
                          label={
                            <Space>
                              <span>Regex de Job Name</span>
                              {valid && <CheckCircleFilled style={{ color: '#52c41a' }} />}
                            </Space>
                          }
                          placeholder="ex: ^icmp.*"
                          tooltip="Expressão Regular para identificar o target pelo nome do job no Prometheus."
                          rules={[
                            { required: true, message: 'Obrigatório' },
                            { validator: validateRegex },
                          ]}
                          fieldProps={{
                            size: 'small'
                          }}
                        />
                      );
                    }}
                  </ProFormDependency>

                  {/* ALERTA DE REGEX SIMPLES - JOB NAME */}
                  <ProFormDependency name={['job_name_pattern']}>
                    {({ job_name_pattern }) => {
                      if (isSimpleRegex(job_name_pattern)) {
                        return (
                          <Alert
                            message="Regex Simples"
                            type="warning"
                            showIcon
                            style={{ marginBottom: 8, fontSize: '12px', padding: '4px 8px' }}
                          />
                        );
                      }
                      return null;
                    }}
                  </ProFormDependency>

                  {/* TESTE DE REGEX - JOB NAME */}
                  <ProFormDependency name={['job_name_pattern']}>
                    {({ job_name_pattern }) => {
                      let isValid = false;
                      try { if (job_name_pattern) { new RegExp(job_name_pattern); isValid = true; } } catch (e) { }

                      if (!isValid) return null;

                      return (
                        <RegexTester
                          pattern={job_name_pattern}
                          title="Testar Regex (Job Name)"
                          placeholder="Teste (ex: node_exporter_linux)"
                        />
                      );
                    }}
                  </ProFormDependency>
                </div>
              </Col>

              {/* MODULE PATTERN */}
              <Col span={12}>
                <div style={{ background: '#fafafa', padding: '12px', borderRadius: '6px' }}>
                  <ProFormDependency name={['module_pattern']}>
                    {({ module_pattern }) => {
                      let valid = false;
                      try { if (module_pattern) { new RegExp(module_pattern); valid = true; } } catch (e) { }

                      return (
                        <ProFormText
                          name="module_pattern"
                          label={
                            <Space>
                              <span>Regex de Module</span>
                              {valid && <CheckCircleFilled style={{ color: '#52c41a' }} />}
                            </Space>
                          }
                          placeholder="ex: ^icmp$"
                          tooltip="Expressão Regular para identificar o target pelo parâmetro 'module' (usado em Blackbox/Snmp Exporters)."
                          rules={[{ validator: validateRegex }]}
                          fieldProps={{
                            size: 'small'
                          }}
                        />
                      );
                    }}
                  </ProFormDependency>

                  {/* ALERTA DE REGEX SIMPLES - MODULE */}
                  <ProFormDependency name={['module_pattern']}>
                    {({ module_pattern }) => {
                      if (isSimpleRegex(module_pattern)) {
                        return (
                          <Alert
                            message="Regex Simples"
                            type="warning"
                            showIcon
                            style={{ marginBottom: 8, fontSize: '12px', padding: '4px 8px' }}
                          />
                        );
                      }
                      return null;
                    }}
                  </ProFormDependency>

                  {/* TESTE DE REGEX - MODULE */}
                  <ProFormDependency name={['module_pattern']}>
                    {({ module_pattern }) => {
                      let isValid = false;
                      try { if (module_pattern) { new RegExp(module_pattern); isValid = true; } } catch (e) { }

                      if (!isValid) return null;

                      return (
                        <RegexTester
                          pattern={module_pattern}
                          title="Testar Regex (Module)"
                          placeholder="Teste (ex: icmp)"
                        />
                      );
                    }}
                  </ProFormDependency>
                </div>
              </Col>
            </Row>

          </Space>
        </ProForm>
      </Modal>

      {/* Modal de Preview */}
      <Modal
        title="Resumo de Regras"
        open={previewVisible}
        onCancel={() => setPreviewVisible(false)}
        footer={[
          <Button key="close" onClick={() => setPreviewVisible(false)}>
            Fechar
          </Button>,
        ]}
        width={800}
      >
        {rulesData && (
          <Descriptions bordered column={2} size="small">
            <Descriptions.Item label="Versão">{rulesData.version}</Descriptions.Item>
            <Descriptions.Item label="Total de Regras">{rulesData.total_rules}</Descriptions.Item>
            <Descriptions.Item label="Categoria Padrão">
              <Tag color={CATEGORY_COLORS[rulesData.default_category]}>
                {rulesData.default_category}
              </Tag>
            </Descriptions.Item>
            <Descriptions.Item label="Última Atualização">
              {new Date(rulesData.last_updated).toLocaleString('pt-BR')}
            </Descriptions.Item>
            <Descriptions.Item label="Categorias" span={2}>
              <Space wrap>
                {rulesData.categories.map(cat => (
                  <Tag key={cat.id} color={CATEGORY_COLORS[cat.id]}>
                    {cat.display_name}
                  </Tag>
                ))}
              </Space>
            </Descriptions.Item>
          </Descriptions>
        )}
      </Modal>

      {/* SPEC-REGEX-001: Modal de Validacao Global */}
      <GlobalRegexValidator
        visible={globalValidatorVisible}
        onClose={() => setGlobalValidatorVisible(false)}
        rules={rulesData?.rules || []}
        categoryColors={CATEGORY_COLORS}
      />
    </PageContainer>
  );
};

export default MonitoringRules;
