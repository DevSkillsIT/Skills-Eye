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
} from 'antd';
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  ReloadOutlined,
  InfoCircleOutlined,
} from '@ant-design/icons';
import { consulAPI } from '../services/api';

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
    });
    setModalVisible(true);
  };

  const handleDelete = async (ruleId: string) => {
    try {
      const response = await consulAPI.deleteCategorizationRule(ruleId);

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
      };

      let response;
      if (editingRule) {
        response = await consulAPI.updateCategorizationRule(rule.id, rule);
      } else {
        response = await consulAPI.createCategorizationRule(rule);
      }

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
      filters: rulesData?.categories.map(c => ({
        text: c.display_name,
        value: c.id,
      })),
      onFilter: (value, record) => record.category === value,
      render: (category: string) => (
        <Tag color={CATEGORY_COLORS[category] || 'default'}>
          {rulesData?.categories.find(c => c.id === category)?.display_name || category}
        </Tag>
      ),
    },
    {
      title: 'Display Name',
      dataIndex: 'display_name',
      width: 250,
      ellipsis: true,
    },
    {
      title: 'Exporter Type',
      dataIndex: 'exporter_type',
      width: 180,
      ellipsis: true,
      render: (text) => text ? <Tag color="blue">{text}</Tag> : '-',
    },
    {
      title: 'Job Pattern',
      dataIndex: ['conditions', 'job_name_pattern'],
      width: 180,
      ellipsis: true,
      render: (text) => text ? <code style={{ fontSize: '11px' }}>{text}</code> : '-',
    },
    {
      title: 'Metrics Path',
      dataIndex: ['conditions', 'metrics_path'],
      width: 120,
      render: (text) => <Tag color={text === '/probe' ? 'orange' : 'green'}>{text || '-'}</Tag>,
    },
    {
      title: 'Module Pattern',
      dataIndex: ['conditions', 'module_pattern'],
      width: 150,
      ellipsis: true,
      render: (text) => text ? <code style={{ fontSize: '11px' }}>{text}</code> : '-',
    },
    {
      title: 'Ações',
      width: 120,
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
      extra={[
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
      ]}
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
          defaultPageSize: 20,
          showSizeChanger: true,
          showTotal: (total) => `Total: ${total} regras`,
        }}
        options={{
          reload: true,
          density: true,
          setting: true,
        }}
        scroll={{ x: 1500 }}
      />

      {/* Modal de Edição/Criação */}
      <Modal
        title={editingRule ? `Editar Regra: ${editingRule.id}` : 'Nova Regra'}
        open={modalVisible}
        onCancel={() => setModalVisible(false)}
        onOk={handleSave}
        width={700}
        okText={editingRule ? 'Salvar' : 'Criar'}
        cancelText="Cancelar"
      >
        <Form
          form={form}
          layout="vertical"
          style={{ marginTop: 24 }}
        >
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

          <ProFormSelect
            name="category"
            label="Categoria"
            rules={[{ required: true, message: 'Categoria é obrigatória' }]}
            options={rulesData?.categories.map(c => ({
              label: c.display_name,
              value: c.id,
            }))}
            tooltip="Categoria para a qual este tipo de monitoramento será classificado"
          />

          <ProFormText
            name="display_name"
            label="Nome de Exibição"
            placeholder="ex: ICMP (Ping), Node Exporter (Linux)"
            rules={[{ required: true, message: 'Nome de exibição é obrigatório' }]}
            tooltip="Nome amigável que aparecerá na interface"
          />

          <ProFormText
            name="exporter_type"
            label="Tipo de Exporter (Opcional)"
            placeholder="ex: blackbox, node_exporter, mysqld_exporter"
            tooltip="Nome técnico do exporter (ex: node_exporter, blackbox)"
          />

          <ProFormText
            name="job_name_pattern"
            label="Regex de Job Name"
            placeholder="ex: ^icmp.*, ^node.*, ^mysql.*"
            rules={[
              { required: true, message: 'Pattern de job_name é obrigatório' },
            ]}
            tooltip="Expressão regular para matching no nome do job do Prometheus"
          />

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

          <ProFormText
            name="module_pattern"
            label="Regex de Module (Opcional)"
            placeholder="ex: ^icmp$, ^http_2xx$"
            tooltip="Expressão regular para matching em __param_module (apenas para Blackbox)"
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
