import React, { useState, useRef, useEffect } from 'react';
import { useConsulDelete } from '../hooks/useConsulDelete';
import {
  ProTable,
  ModalForm,
  ProFormText,
  ProFormDigit,
  ProFormSelect,
  ProFormTextArea,
} from '@ant-design/pro-components';
import type { ActionType } from '@ant-design/pro-components';
import {
  Button,
  Space,
  Tag,
  Modal,
  message,
  Popconfirm,
  Tooltip,
  Descriptions,
  Card,
  Input,
  Form,
  Typography,
  Divider,
  Alert,
} from 'antd';
import {
  PlusOutlined,
  DownloadOutlined,
  DeleteOutlined,
  EyeOutlined,
  RocketOutlined,
  AppstoreOutlined,
} from '@ant-design/icons';
import { consulAPI } from '../services/api';
import type { ServicePreset, RegisterFromPreset } from '../services/api';

const { Title, Text, Paragraph } = Typography;

interface PresetFormData {
  id: string;
  name: string;
  service_name: string;
  port?: number;
  tags?: string;
  meta_template?: string;
  checks?: string;
  description?: string;
  category: string;
}

type PresetColumn<T> = import('@ant-design/pro-components').ProColumns<T>;

const ServicePresets: React.FC = () => {
  const actionRef = useRef<ActionType | null>(null);
  const [createModalVisible, setCreateModalVisible] = useState(false);
  const [registerModalVisible, setRegisterModalVisible] = useState(false);
  const [previewModalVisible, setPreviewModalVisible] = useState(false);
  const [selectedPreset, setSelectedPreset] = useState<ServicePreset | null>(null);
  const [previewData, setPreviewData] = useState<any>(null);
  const [tableSnapshot, setTableSnapshot] = useState<ServicePreset[]>([]);
  const [registerForm] = Form.useForm();
  const [categoryFilter, setCategoryFilter] = useState<string | undefined>(undefined);

  // Hook para DELETE de presets
  const { deleteResource } = useConsulDelete({
    deleteFn: async (payload: any) => consulAPI.deletePreset(payload.preset_id),
    successMessage: 'Preset deletado com sucesso',
    errorMessage: 'Erro ao deletar preset',
    onSuccess: () => {
      actionRef.current?.reload();
    },
  });

  // Criar presets built-in ao montar o componente
  useEffect(() => {
    createBuiltinPresets();
  }, []);

  const createBuiltinPresets = async () => {
    try {
      await consulAPI.createBuiltinPresets();
    } catch (error) {
      console.error('Erro ao criar presets built-in:', error);
    }
  };

  const handleExport = () => {
    if (!tableSnapshot.length) {
      message.info('Nao ha dados para exportar');
      return;
    }

    const header = [
      'id',
      'name',
      'service_name',
      'port',
      'category',
      'tags',
      'description',
    ];

    const rows = tableSnapshot.map((preset) => [
      preset.id,
      preset.name,
      preset.service_name,
      preset.port ?? '',
      preset.category,
      (preset.tags || []).join('|'),
      preset.description || '',
    ].join(';'));

    const csvContent = [header.join(';'), ...rows].join('\n');
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `service-presets-${new Date().toISOString()}.csv`;
    link.click();
    URL.revokeObjectURL(url);
  };

  const columns: PresetColumn<ServicePreset>[] = [
    {
      title: 'ID',
      dataIndex: 'id',
      width: 200,
      ellipsis: true,
      copyable: true,
    },
    {
      title: 'Nome',
      dataIndex: 'name',
      width: 250,
      ellipsis: true,
      render: (_, record) => (
        <Space>
          <AppstoreOutlined />
          <strong>{record.name}</strong>
        </Space>
      ),
    },
    {
      title: 'Servico',
      dataIndex: 'service_name',
      width: 180,
      ellipsis: true,
    },
    {
      title: 'Categoria',
      dataIndex: 'category',
      width: 150,
      filters: true,
      onFilter: true,
      valueEnum: {
        exporter: { text: 'Exporter', status: 'Processing' },
        application: { text: 'Application', status: 'Success' },
        database: { text: 'Database', status: 'Default' },
        custom: { text: 'Custom', status: 'Warning' },
      },
      render: (_, record) => {
        const colorMap: Record<string, string> = {
          exporter: 'blue',
          application: 'green',
          database: 'purple',
          custom: 'orange',
        };
        return <Tag color={colorMap[record.category] || 'default'}>{record.category}</Tag>;
      },
    },
    {
      title: 'Porta',
      dataIndex: 'port',
      width: 100,
      align: 'center',
      render: (port) => port || '-',
    },
    {
      title: 'Tags',
      dataIndex: 'tags',
      width: 200,
      ellipsis: true,
      render: (_, record) =>
        record.tags?.length
          ? record.tags.map((tag) => <Tag key={`${record.id}-${tag}`}>{tag}</Tag>)
          : '-',
    },
    {
      title: 'Descricao',
      dataIndex: 'description',
      ellipsis: true,
      hideInTable: true,
    },
    {
      title: 'Acoes',
      valueType: 'option',
      width: 200,
      fixed: 'right',
      render: (_, record) => [
        <Tooltip title="Visualizar preset" key={`view-${record.id}`}>
          <Button
            type="link"
            icon={<EyeOutlined />}
            aria-label="Visualizar preset"
            onClick={() => handleViewPreset(record)}
          />
        </Tooltip>,
        <Tooltip title="Registrar a partir do preset" key={`register-${record.id}`}>
          <Button
            type="link"
            icon={<RocketOutlined />}
            aria-label="Registrar a partir do preset"
            onClick={() => handleOpenRegisterModal(record)}
          />
        </Tooltip>,
        <Popconfirm
          key={`delete-${record.id}`}
          title="Tem certeza que deseja deletar este preset?"
          description="Esta acao nao pode ser desfeita."
          onConfirm={() => handleDelete(record.id)}
          okText="Remover"
          cancelText="Cancelar"
        >
          <Tooltip title="Remover preset">
            <Button
              type="link"
              danger
              icon={<DeleteOutlined />}
              aria-label="Remover preset"
            />
          </Tooltip>
        </Popconfirm>,
      ],
    },
  ];

  const handleViewPreset = (preset: ServicePreset) => {
    setSelectedPreset(preset);
  };

  const handleOpenRegisterModal = (preset: ServicePreset) => {
    setSelectedPreset(preset);
    setRegisterModalVisible(true);
    registerForm.resetFields();
  };

  /**
   * Deleta um preset usando o hook useConsulDelete
   * Usa APENAS dados do record - ZERO valores hardcoded
   */
  const handleDelete = async (presetId: string) => {
    await deleteResource({ preset_id: presetId });
  };

  const handleCreatePreset = async (values: PresetFormData) => {
    try {
      const payload = {
        id: values.id,
        name: values.name,
        service_name: values.service_name,
        port: values.port,
        tags: values.tags ? values.tags.split(',').map((t) => t.trim()) : undefined,
        meta_template: values.meta_template ? JSON.parse(values.meta_template) : undefined,
        checks: values.checks ? JSON.parse(values.checks) : undefined,
        description: values.description,
        category: values.category,
      };

      await consulAPI.createPreset(payload);
      message.success('Preset criado com sucesso');
      setCreateModalVisible(false);
      actionRef.current?.reload();
      return true;
    } catch (error: any) {
      message.error(error.response?.data?.detail || 'Erro ao criar preset');
      return false;
    }
  };

  const handleRegisterFromPreset = async (values: any) => {
    try {
      if (!selectedPreset) return;

      // Montar variaveis do formulario
      const variables: Record<string, string> = {};
      Object.keys(values).forEach((key) => {
        if (values[key]) {
          variables[key] = values[key].toString();
        }
      });

      const request: RegisterFromPreset = {
        preset_id: selectedPreset.id,
        variables,
        node_addr: values.node_addr || undefined,
      };

      const response = await consulAPI.registerFromPreset(request);
      message.success(`Servico registrado com sucesso: ${response.data.service_id}`);
      setRegisterModalVisible(false);
      registerForm.resetFields();
    } catch (error: any) {
      message.error(error.response?.data?.detail || 'Erro ao registrar servico');
    }
  };

  const handlePreview = async () => {
    try {
      if (!selectedPreset) return;

      const values = registerForm.getFieldsValue();
      const variables: Record<string, string> = {};
      Object.keys(values).forEach((key) => {
        if (values[key]) {
          variables[key] = values[key].toString();
        }
      });

      const request: RegisterFromPreset = {
        preset_id: selectedPreset.id,
        variables,
      };

      const response = await consulAPI.previewPreset(request);
      setPreviewData(response.data.preview);
      setPreviewModalVisible(true);
    } catch (error: any) {
      message.error(error.response?.data?.detail || 'Erro ao gerar preview');
    }
  };

  // Extrair variaveis do meta_template
  const extractVariables = (preset: ServicePreset): string[] => {
    const vars = new Set<string>();
    const regex = /\$\{(\w+)(?::([^}]+))?\}/g;

    const metaStr = JSON.stringify(preset.meta_template || {});
    let match;
    while ((match = regex.exec(metaStr)) !== null) {
      vars.add(match[1]);
    }

    return Array.from(vars);
  };

  return (
    <div style={{ padding: 24 }}>
      <Card
        title={
          <Space>
            <AppstoreOutlined style={{ fontSize: 24 }} />
            <Title level={2} style={{ margin: 0 }}>
              Service Presets
            </Title>
          </Space>
        }
        extra={
          <Space>
            <Button
              type="primary"
              icon={<PlusOutlined />}
              onClick={() => setCreateModalVisible(true)}
            >
              Novo Preset
            </Button>
          </Space>
        }
      >
        <Paragraph>
        Gerencie templates reutilizaveis para registro de serviços. Use variaveis como{' '}
          <Text code>${'var'}</Text> ou <Text code>${'var:default'}</Text> para criar templates
          flexiveis.
        </Paragraph>
      </Card>

      <div style={{ marginTop: 16 }}>
        <ProTable<ServicePreset>
          columns={columns}
          actionRef={actionRef}
          request={async () => {
            try {
              const response = await consulAPI.listPresets(categoryFilter);
              const presets = response.data.presets || [];
              setTableSnapshot(presets);
              return {
                data: presets,
                success: true,
                total: response.data.total || 0,
              };
            } catch (error) {
              return { data: [], success: false, total: 0 };
            }
          }}
          rowKey="id"
          search={false}
          dateFormatter="string"
          options={{ setting: { draggable: true, checkable: true } }}
          toolBarRender={() => [
            <Button key="export" icon={<DownloadOutlined />} onClick={handleExport}>
              Exportar CSV
            </Button>
          ]}
          toolbar={{
            title: 'Lista de Presets',
            filter: (
              <Space>
                <Text>Categoria:</Text>
                <ProFormSelect
                  name="category"
                  options={[
                    { label: 'Todos', value: undefined },
                    { label: 'Exporter', value: 'exporter' },
                    { label: 'Application', value: 'application' },
                    { label: 'Database', value: 'database' },
                    { label: 'Custom', value: 'custom' },
                  ]}
                  fieldProps={{
                    value: categoryFilter,
                    onChange: (value) => {
                      setCategoryFilter(value);
                      actionRef.current?.reload();
                    },
                    style: { width: 150 },
                  }}
                />
              </Space>
            ),
          }}
          pagination={{
            defaultPageSize: 10,
            showSizeChanger: true,
          }}
        />
      </div>

      {/* Modal Criar Preset */}
      <ModalForm<PresetFormData>
        title="Criar Novo Preset"
        open={createModalVisible}
        onOpenChange={setCreateModalVisible}
        onFinish={handleCreatePreset}
        width={700}
        layout="vertical"
      >
        <Alert
          message="Dica"
          description="Use ${variavel} ou ${variavel:valor_padrao} nos campos JSON para criar templates dinamicos."
          type="info"
          showIcon
          style={{ marginBottom: 16 }}
        />

        <ProFormText
          name="id"
          label="ID do Preset"
          placeholder="node-exporter-linux"
          rules={[{ required: true, message: 'ID e obrigatorio' }]}
          tooltip="Identificador unico (kebab-case)"
        />

        <ProFormText
          name="name"
          label="Nome"
          placeholder="Node Exporter (Linux)"
          rules={[{ required: true }]}
        />

        <ProFormText
          name="service_name"
          label="Nome do Servico Consul"
          placeholder="node_exporter"
          rules={[{ required: true }]}
        />

        <ProFormDigit
          name="port"
          label="Porta Padrao"
          placeholder="9100"
          fieldProps={{ style: { width: '100%' } }}
        />

        <ProFormSelect
          name="category"
          label="Categoria"
          options={[
            { label: 'Exporter', value: 'exporter' },
            { label: 'Application', value: 'application' },
            { label: 'Database', value: 'database' },
            { label: 'Custom', value: 'custom' },
          ]}
          rules={[{ required: true }]}
        />

        <ProFormText
          name="tags"
          label="Tags (separadas por virgula)"
          placeholder="monitoring, linux"
        />

        <ProFormTextArea
          name="meta_template"
          label="Meta Template (JSON)"
          placeholder='{"env": "${env}", "datacenter": "${datacenter:unknown}"}'
          fieldProps={{ rows: 4, style: { fontFamily: 'monospace' } }}
        />

        <ProFormTextArea
          name="checks"
          label="Health Checks (JSON Array)"
          placeholder='[{"HTTP": "http://${address}:${port}/metrics", "Interval": "30s"}]'
          fieldProps={{ rows: 4, style: { fontFamily: 'monospace' } }}
        />

        <ProFormTextArea name="description" label="Descricao" placeholder="Descricao do preset" />
      </ModalForm>

      {/* Modal Visualizar Preset */}
      <Modal
        title="Detalhes do Preset"
        open={!!selectedPreset && !registerModalVisible}
        onCancel={() => setSelectedPreset(null)}
        footer={[
          <Button key="close" onClick={() => setSelectedPreset(null)}>
            Fechar
          </Button>,
          <Button
            key="register"
            type="primary"
            icon={<RocketOutlined />}
            onClick={() => {
              if (selectedPreset) handleOpenRegisterModal(selectedPreset);
            }}
          >
            Registrar Servico
          </Button>,
        ]}
        width={800}
      >
        {selectedPreset && (
          <Descriptions column={2} bordered>
            <Descriptions.Item label="ID" span={2}>
              <Text copyable>{selectedPreset.id}</Text>
            </Descriptions.Item>
            <Descriptions.Item label="Nome" span={2}>
              {selectedPreset.name}
            </Descriptions.Item>
            <Descriptions.Item label="Servico">{selectedPreset.service_name}</Descriptions.Item>
            <Descriptions.Item label="Categoria">
              <Tag color="blue">{selectedPreset.category}</Tag>
            </Descriptions.Item>
            <Descriptions.Item label="Porta">
              {selectedPreset.port || 'N/A'}
            </Descriptions.Item>
            <Descriptions.Item label="Tags">
              {selectedPreset.tags?.map((tag) => <Tag key={tag}>{tag}</Tag>) || 'N/A'}
            </Descriptions.Item>
            <Descriptions.Item label="Meta Template" span={2}>
              <pre style={{ margin: 0, background: '#f5f5f5', padding: 8, borderRadius: 4 }}>
                {JSON.stringify(selectedPreset.meta_template, null, 2)}
              </pre>
            </Descriptions.Item>
            {selectedPreset.checks && (
              <Descriptions.Item label="Health Checks" span={2}>
                <pre style={{ margin: 0, background: '#f5f5f5', padding: 8, borderRadius: 4 }}>
                  {JSON.stringify(selectedPreset.checks, null, 2)}
                </pre>
              </Descriptions.Item>
            )}
            {selectedPreset.description && (
              <Descriptions.Item label="Descricao" span={2}>
                {selectedPreset.description}
              </Descriptions.Item>
            )}
          </Descriptions>
        )}
      </Modal>

      {/* Modal Registrar Servico */}
      <Modal
        title={`Registrar Servico: ${selectedPreset?.name}`}
        open={registerModalVisible}
        onCancel={() => {
          setRegisterModalVisible(false);
          registerForm.resetFields();
        }}
        footer={null}
        width={700}
      >
        {selectedPreset && (
          <>
            <Alert
              message="Preencha as variaveis"
              description={`Este preset requer as seguintes variaveis: ${extractVariables(selectedPreset).join(', ')}`}
              type="info"
              showIcon
              style={{ marginBottom: 16 }}
            />

            <Form form={registerForm} layout="vertical" onFinish={handleRegisterFromPreset}>
              <Form.Item
                name="address"
                label="Endereco IP/Hostname"
                rules={[{ required: true, message: 'Endereco e obrigatorio' }]}
              >
                <Input placeholder="10.0.0.5 ou hostname.domain.com" />
              </Form.Item>

              {extractVariables(selectedPreset).map((varName) => {
                if (varName === 'address') return null; // Ja adicionado acima
                return (
                  <Form.Item key={varName} name={varName} label={varName}>
                    <Input placeholder={`Valor para ${varName}`} />
                  </Form.Item>
                );
              })}

              <Form.Item name="node_addr" label="Node Address (opcional)">
                <Input placeholder="Deixe em branco para usar servidor principal" />
              </Form.Item>

              <Divider />

              <Space style={{ width: '100%', justifyContent: 'flex-end' }}>
                <Button onClick={handlePreview}>Preview</Button>
                <Button
                  onClick={() => {
                    setRegisterModalVisible(false);
                    registerForm.resetFields();
                  }}
                >
                  Cancelar
                </Button>
                <Button type="primary" htmlType="submit" icon={<RocketOutlined />}>
                  Registrar Servico
                </Button>
              </Space>
            </Form>
          </>
        )}
      </Modal>

      {/* Modal Preview */}
      <Modal
        title="Preview do Servico"
        open={previewModalVisible}
        onCancel={() => setPreviewModalVisible(false)}
        footer={[
          <Button key="close" onClick={() => setPreviewModalVisible(false)}>
            Fechar
          </Button>,
        ]}
        width={800}
      >
        <Alert
          message="Este e apenas um preview"
          description="O servico ainda nao foi registrado. Use o botao 'Registrar Servico' para efetuar o registro."
          type="warning"
          showIcon
          style={{ marginBottom: 16 }}
        />
        <pre
          style={{
            background: '#f5f5f5',
            padding: 16,
            borderRadius: 4,
            overflow: 'auto',
            maxHeight: 500,
          }}
        >
          {JSON.stringify(previewData, null, 2)}
        </pre>
      </Modal>
    </div>
  );
};

export default ServicePresets;







