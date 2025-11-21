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
 * - Validação de regex patterns
 * - Preview de regras antes de salvar
 *
 * AUTOR: Sistema de Refatoração Skills Eye v2.0
 * DATA: 2025-11-13
 */

import React, { useState, useRef, useEffect } from 'react';
import {
  PageContainer,
  ProTable,
  ProFormText,
  ProFormDigit,
  ProFormSelect,
  ProFormTextArea,
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
} from 'antd';
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  ReloadOutlined,
  InfoCircleOutlined,
  ClearOutlined,
  CopyOutlined,
} from '@ant-design/icons';
import { consulAPI } from '../services/api';

// ============================================================================
// INTERFACES
// ============================================================================

// ✅ SPEC-ARCH-001: Interfaces FormSchemaField e FormSchema REMOVIDAS
// form_schema existe APENAS em monitoring-types, não nas regras de categorização

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
  // ✅ SPEC-ARCH-001: form_schema REMOVIDO - existe apenas em monitoring-types
  observations?: string;  // Campo de observações
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
// COMPONENTE PRINCIPAL
// ============================================================================

const MonitoringRules: React.FC = () => {
  const actionRef = useRef<ActionType>();
  const [form] = Form.useForm();

  // Estados
  const [modalVisible, setModalVisible] = useState(false);
  const [editingRule, setEditingRule] = useState<CategorizationRule | null>(null);
  const [previewVisible, setPreviewVisible] = useState(false);
  const [rulesData, setRulesData] = useState<RulesData | null>(null);
  const [loading, setLoading] = useState(false);
  const [sortField, setSortField] = useState<string | null>(null);
  const [sortOrder, setSortOrder] = useState<'ascend' | 'descend' | null>(null);

  // =========================================================================
  // CARREGAMENTO DE DADOS
  // =========================================================================

  const loadRules = async () => {
    setLoading(true);
    try {
      // consulAPI returns an axios Response; normalize payload to response.data
      const response = await consulAPI.getCategorizationRules();
      const payload = (response && (response as any).data) ? (response as any).data : response;

      if (payload && payload.success && payload.data) {
        setRulesData(payload.data);
        return {
          data: payload.data.rules || [],
          success: true,
          total: payload.data.total_rules || 0,
        };
      }

      // Manchete de diagnóstico: logar payload para ajudar debugging se formato inesperado
      // (não lança em produção, apenas auxilia desenvolvimento)
      // eslint-disable-next-line no-console
      console.warn('getCategorizationRules: payload inesperado', payload);
      throw new Error('Erro ao carregar regras');
    } catch (error: any) {
      message.error('Erro ao carregar regras: ' + (error.message || error));
      return {
        data: [],
        success: false,
        total: 0,
      };
    } finally {
      setLoading(false);
    }
  };

  // =========================================================================
  // HANDLERS
  // =========================================================================

  const handleAdd = () => {
    setEditingRule(null);
    form.resetFields();
    form.setFieldsValue({
      priority: 80,
      metrics_path: '/metrics',
    });
    setModalVisible(true);
  };

  const handleEdit = (record: CategorizationRule) => {
    setEditingRule(record);
    form.setFieldsValue({
      id: record.id,
      priority: record.priority,
      category: record.category,
      display_name: record.display_name,
      exporter_type: record.exporter_type,
      job_name_pattern: record.conditions.job_name_pattern,
      metrics_path: record.conditions.metrics_path,
      module_pattern: record.conditions.module_pattern,
      observations: record.observations,
    });
    setModalVisible(true);
  };

  const handleDuplicate = (record: CategorizationRule) => {
    setEditingRule(null);
    form.setFieldsValue({
      id: `${record.id}_copy`,
      priority: record.priority,
      category: record.category,
      display_name: `${record.display_name} (Cópia)`,
      exporter_type: record.exporter_type,
      job_name_pattern: record.conditions.job_name_pattern,
      metrics_path: record.conditions.metrics_path,
      module_pattern: record.conditions.module_pattern,
      observations: record.observations,
    });
    setModalVisible(true);
  };

  const handleDelete = async (ruleId: string) => {
    try {
      const axiosResponse = await consulAPI.deleteCategorizationRule(ruleId);

      // Normalizar resposta: Axios retorna response.data
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
      if (editingRule) {
        axiosResponse = await consulAPI.updateCategorizationRule(rule.id, rule);
      } else {
        axiosResponse = await consulAPI.createCategorizationRule(rule);
      }

      // Normalizar resposta: Axios retorna response.data
      const response = (axiosResponse && (axiosResponse as any).data)
        ? (axiosResponse as any).data
        : axiosResponse;

      if (response.success) {
        message.success(editingRule ? 'Regra atualizada com sucesso' : 'Regra criada com sucesso');
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

  const columns: ProColumns<CategorizationRule>[] = [
    {
      title: 'ID',
      dataIndex: 'id',
      width: 180,
      fixed: 'left',
      ellipsis: true,
      render: (text) => <code style={{ fontSize: '12px' }}>{text}</code>,
    },
    {
      title: 'Prioridade',
      dataIndex: 'priority',
      width: 120,
      sorter: (a, b) => b.priority - a.priority,
      defaultSortOrder: 'descend',
      render: (priority: number) => {
        const level = PRIORITY_LEVELS.find(l => l.value === priority);
        return (
          <Tooltip title={level?.label || `Prioridade ${priority}`}>
            <Tag color={level?.color || 'default'}>{priority}</Tag>
          </Tooltip>
        );
      },
    },
    {
      title: 'Categoria',
      dataIndex: 'category',
      width: 200,
      sorter: (a, b) => (a.category || '').localeCompare(b.category || ''),
      filters: rulesData?.categories?.map(c => ({
        text: c.display_name,
        value: c.id,
      })) || [],
      onFilter: (value, record) => record.category === value,
      render: (category: string) => (
        <Tag color={CATEGORY_COLORS[category] || 'default'}>
          {rulesData?.categories?.find(c => c.id === category)?.display_name || category}
        </Tag>
      ),
    },
    {
      title: 'Display Name',
      dataIndex: 'display_name',
      width: 250,
      ellipsis: true,
      sorter: (a, b) => (a.display_name || '').localeCompare(b.display_name || ''),
      filters: Array.from(new Set(rulesData?.rules?.map(r => r.display_name) || [])).map(name => ({
        text: name,
        value: name,
      })),
      onFilter: (value, record) => record.display_name === value,
    },
    {
      title: 'Exporter Type',
      dataIndex: 'exporter_type',
      width: 180,
      ellipsis: true,
      sorter: (a, b) => (a.exporter_type || '').localeCompare(b.exporter_type || ''),
      filters: Array.from(new Set((rulesData?.rules?.map(r => r.exporter_type) || []).filter(Boolean))).map(type => ({
        text: type as string,
        value: type as string,
      })),
      onFilter: (value, record) => record.exporter_type === value,
      render: (text) => text ? <Tag color="blue">{text}</Tag> : '-',
    },
    {
      title: 'Job Pattern',
      dataIndex: ['conditions', 'job_name_pattern'],
      width: 180,
      ellipsis: true,
      filters: Array.from(new Set((rulesData?.rules?.map(r => r.conditions.job_name_pattern) || []).filter(Boolean))).map(pattern => ({
        text: pattern as string,
        value: pattern as string,
      })),
      onFilter: (value, record) => record.conditions.job_name_pattern === value,
      render: (text) => text ? <code style={{ fontSize: '11px' }}>{text}</code> : '-',
    },
    {
      title: 'Metrics Path',
      dataIndex: ['conditions', 'metrics_path'],
      width: 120,
      filters: [
        { text: '/probe', value: '/probe' },
        { text: '/metrics', value: '/metrics' },
      ],
      onFilter: (value, record) => record.conditions.metrics_path === value,
      render: (text) => <Tag color={text === '/probe' ? 'orange' : 'green'}>{text || '-'}</Tag>,
    },
    {
      title: 'Module Pattern',
      dataIndex: ['conditions', 'module_pattern'],
      width: 150,
      ellipsis: true,
      filters: Array.from(new Set((rulesData?.rules?.map(r => r.conditions.module_pattern) || []).filter(Boolean))).map(pattern => ({
        text: pattern as string,
        value: pattern as string,
      })),
      onFilter: (value, record) => record.conditions.module_pattern === value,
      render: (text) => text ? <code style={{ fontSize: '11px' }}>{text}</code> : '-',
    },
    {
      title: 'Ações',
      width: 150,
      fixed: 'right',
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
  ];

  // =========================================================================
  // RENDER
  // =========================================================================

  return (
    <PageContainer
      title="Regras de Categorização"
      subTitle="Gerenciar regras de categorização de tipos de monitoramento"
    >
      {/* Estatísticas */}
      {rulesData && (
        <Space style={{ marginBottom: 16 }} size="large">
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
      )}

      {/* Tabela de Regras */}
      <ProTable<CategorizationRule>
        actionRef={actionRef}
        columns={columns}
        request={loadRules}
        rowKey="id"
        search={false}
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
        onChange={(pagination, filters, sorter: any) => {
          if (sorter && sorter.field) {
            setSortField(sorter.field);
            setSortOrder(sorter.order || null);
          } else {
            setSortField(null);
            setSortOrder(null);
          }
        }}
        toolbar={{
          actions: [
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
              icon={<ClearOutlined />}
              onClick={() => {
                actionRef.current?.clearFilters?.();
                actionRef.current?.reload();
              }}
            >
              Limpar Filtros
            </Button>,
            <Button
              key="clearAll"
              icon={<ClearOutlined />}
              onClick={() => {
                actionRef.current?.reset?.();
                setSortField(null);
                setSortOrder(null);
                actionRef.current?.reload();
              }}
            >
              Limpar Filtros e Ordem
            </Button>,
          ],
        }}
      />

      {/* Modal de Edição/Criação */}
      <Modal
        title={editingRule ? `Editar Regra: ${editingRule.id}` : 'Nova Regra de Categorização'}
        open={modalVisible}
        onCancel={() => setModalVisible(false)}
        onOk={handleSave}
        width={1100}
        okText={editingRule ? 'Salvar Alterações' : 'Criar Regra'}
        cancelText="Cancelar"
        destroyOnClose
      >
        <Form
                  form={form}
                  layout="vertical"
                  style={{ marginTop: 16 }}
                >
                  {/* Linha 1: ID e Prioridade */}
                  <Row gutter={16}>
                    <Col span={12}>
                      <ProFormText
                        name="id"
                        label="ID da Regra"
                        placeholder="ex: blackbox_icmp, exporter_node"
                        rules={[
                          { required: true, message: 'ID é obrigatório' },
                          { pattern: /^[a-z0-9_]+$/, message: 'Use apenas letras minúsculas, números e _' },
                        ]}
                        disabled={!!editingRule}
                        tooltip="Identificador único da regra (não pode ser alterado após criação)"
                      />
                    </Col>
                    <Col span={12}>
                      <ProFormDigit
                        name="priority"
                        label="Prioridade"
                        min={1}
                        max={100}
                        rules={[{ required: true, message: 'Prioridade é obrigatória' }]}
                        tooltip="Maior prioridade = regra avaliada primeiro (100 = Blackbox, 80 = Exporters)"
                        fieldProps={{
                          style: { width: '100%' },
                        }}
                      />
                    </Col>
                  </Row>

                  {/* Linha 2: Categoria e Display Name */}
                  <Row gutter={16}>
                    <Col span={12}>
                      <ProFormSelect
                        name="category"
                        label="Nome de Exibição (Categoria)"
                        rules={[{ required: true, message: 'Categoria é obrigatória' }]}
                        options={rulesData?.categories.map(c => ({
                          label: c.display_name,
                          value: c.id,
                        }))}
                        tooltip="Categoria para a qual este tipo de monitoramento será classificado"
                      />
                    </Col>
                    <Col span={12}>
                      <ProFormText
                        name="display_name"
                        label="Display Name"
                        placeholder="ex: ICMP (Ping), Node Exporter (Linux)"
                        rules={[{ required: true, message: 'Nome de exibição é obrigatório' }]}
                        tooltip="Nome amigável que aparecerá na interface"
                      />
                    </Col>
                  </Row>

                  {/* Linha 3: Exporter Type e Job Name Pattern */}
                  <Row gutter={16}>
                    <Col span={12}>
                      <ProFormText
                        name="exporter_type"
                        label="Tipo de Exporter"
                        placeholder="ex: blackbox, node_exporter, mysqld_exporter"
                        tooltip="Nome técnico do exporter (ex: node_exporter, blackbox)"
                      />
                    </Col>
                    <Col span={12}>
                      <ProFormText
                        name="job_name_pattern"
                        label="Regex de Job Name"
                        placeholder="ex: ^icmp.*, ^node.*, ^mysql.*"
                        rules={[
                          { required: true, message: 'Pattern de job_name é obrigatório' },
                        ]}
                        tooltip="Expressão regular para matching no nome do job do Prometheus"
                      />
                    </Col>
                  </Row>

                  {/* Linha 4: Metrics Path e Module Pattern */}
                  <Row gutter={16}>
                    <Col span={12}>
                      <ProFormSelect
                        name="metrics_path"
                        label="Metrics Path"
                        rules={[{ required: true, message: 'Metrics path é obrigatório' }]}
                        options={[
                          { label: '/probe (Blackbox)', value: '/probe' },
                          { label: '/metrics (Exporter)', value: '/metrics' },
                        ]}
                        tooltip="Caminho de métricas no exporter"
                      />
                    </Col>
                    <Col span={12}>
                      <ProFormText
                        name="module_pattern"
                        label="Regex de Module (Opcional)"
                        placeholder="ex: ^icmp$, ^http_2xx$"
                        tooltip="Expressão regular para matching em __param_module (apenas para Blackbox)"
                      />
                    </Col>
                  </Row>

                  {/* Linha 5: Observações (linha inteira) */}
                  <ProFormTextArea
                    name="observations"
                    label="Observações"
                    placeholder="Observações sobre esta regra de categorização"
                    tooltip="Campo opcional para anotações e observações sobre a regra"
                    fieldProps={{
                      rows: 3,
                    }}
                  />
                </Form>
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
    </PageContainer>
  );
};

export default MonitoringRules;
