/**
 * PÁGINA DE CONFIGURAÇÃO DE VALORES DE REFERÊNCIA
 *
 * Interface administrativa para gerenciar TODOS os valores usados nos autocompletes do sistema.
 * Permite visualizar, adicionar, editar e deletar valores de forma visual e intuitiva.
 *
 * CAMPOS GERENCIÁVEIS:
 * - company (Empresa)
 * - grupo_monitoramento (Grupo Monitoramento)
 * - localizacao (Localização)
 * - tipo (Tipo)
 * - modelo (Modelo)
 * - cod_localidade (Código Localidade)
 * - tipo_dispositivo_abrev (Tipo Dispositivo)
 * - cidade (Cidade)
 * - provedor (Provedor)
 * - vendor (Fornecedor)
 * - fabricante (Fabricante)
 * - field_category (Categoria de Campo)
 */

import React, { useState, useEffect } from 'react';
import { useConsulDelete } from '../hooks/useConsulDelete';
import {
  PageContainer,
  ProCard,
  ProTable,
  ModalForm,
  ProFormText,
  ProFormTextArea,
} from '@ant-design/pro-components';
import type { ProColumns } from '@ant-design/pro-components';
import {
  Button,
  Space,
  Tag,
  Tooltip,
  Popconfirm,
  message,
  Statistic,
  Row,
  Col,
  Card,
  Badge,
  Select,
  Input,
  Empty,
  Typography,
  Tabs,
} from 'antd';
import {
  PlusOutlined,
  DeleteOutlined,
  EditOutlined,
  ReloadOutlined,
  SearchOutlined,
  InfoCircleOutlined,
  DatabaseOutlined,
  CheckCircleOutlined,
} from '@ant-design/icons';
import { useReferenceValues } from '../hooks/useReferenceValues';

const { Text, Title, Paragraph } = Typography;
const { Search } = Input;

// Organização de campos por categoria (extraídos do Prometheus)
const FIELD_CATEGORIES = {
  basic: {
    label: 'Básico',
    icon: '📝',
    description: 'Campos básicos e obrigatórios',
    fields: [
      { name: 'company', label: 'Empresa', icon: '🏢', color: 'blue' },
      { name: 'tipo_monitoramento', label: 'Tipo Monitoramento', icon: '🎯', color: 'cyan' },
      { name: 'grupo_monitoramento', label: 'Grupo Monitoramento', icon: '📊', color: 'green' },
    ],
  },
  infrastructure: {
    label: 'Infraestrutura',
    icon: '☁️',
    description: 'Campos relacionados à infraestrutura e cloud',
    fields: [
      { name: 'vendor', label: 'Fornecedor', icon: '🏪', color: 'lime' },
      { name: 'group', label: 'Grupo/Cluster', icon: '🔗', color: 'geekblue' },
    ],
  },
  device: {
    label: 'Dispositivo',
    icon: '💻',
    description: 'Campos de hardware e dispositivos',
    fields: [
      { name: 'localizacao', label: 'Localização', icon: '📍', color: 'orange' },
      { name: 'tipo', label: 'Tipo', icon: '🏷️', color: 'purple' },
      { name: 'modelo', label: 'Modelo', icon: '📦', color: 'cyan' },
      { name: 'cod_localidade', label: 'Código Localidade', icon: '🔢', color: 'geekblue' },
      { name: 'tipo_dispositivo_abrev', label: 'Tipo Dispositivo', icon: '💻', color: 'magenta' },
      { name: 'cidade', label: 'Cidade', icon: '🏙️', color: 'volcano' },
      { name: 'fabricante', label: 'Fabricante', icon: '🏭', color: 'red' },
    ],
  },
  extra: {
    label: 'Extras',
    icon: '➕',
    description: 'Campos adicionais e opcionais',
    fields: [
      { name: 'provedor', label: 'Provedor', icon: '🌐', color: 'gold' },
      { name: 'field_category', label: 'Categoria de Campo', icon: '📂', color: 'purple' },
    ],
  },
};

// Lista plana de todos os campos (para compatibilidade)
const AVAILABLE_FIELDS = Object.values(FIELD_CATEGORIES).flatMap((category) => category.fields);

interface ReferenceValue {
  value: string;
  created_at?: string;
  created_by?: string;
  usage_count?: number;
  last_used_at?: string;
  metadata?: Record<string, any>;
}

const ReferenceValuesPage: React.FC = () => {
  const [selectedField, setSelectedField] = useState<string>('company');
  const [searchText, setSearchText] = useState<string>('');
  const [createModalOpen, setCreateModalOpen] = useState(false);
  const [editModalOpen, setEditModalOpen] = useState(false);
  const [editingValue, setEditingValue] = useState<ReferenceValue | null>(null);

  const {
    valuesWithMetadata,
    loading,
    error,
    ensureValue,
    createValue,
    deleteValue,
    renameValue,
    refreshValues,
  } = useReferenceValues({
    fieldName: selectedField,
    autoLoad: true,
    includeStats: true,
  });

  // Hook para DELETE de valores de referência
  const { deleteResource } = useConsulDelete({
    deleteFn: async (payload: any) => deleteValue(payload.value),
    successMessage: 'Valor deletado com sucesso',
    errorMessage: 'Erro ao deletar valor',
    onSuccess: () => {
      refreshValues();
    },
  });

  // Campo selecionado info
  const selectedFieldInfo = AVAILABLE_FIELDS.find((f) => f.name === selectedField);

  // Filtrar valores com base na busca
  const filteredValues = valuesWithMetadata.filter((v) =>
    v.value?.toLowerCase().includes(searchText.toLowerCase())
  );

  // Estatísticas
  const totalValues = valuesWithMetadata.length;
  const totalUsage = valuesWithMetadata.reduce((sum, v) => sum + (v.usage_count || 0), 0);
  const mostUsed = valuesWithMetadata.reduce(
    (max, v) => ((v.usage_count || 0) > (max?.usage_count || 0) ? v : max),
    valuesWithMetadata[0]
  );

  // Criar novo valor
  const handleCreate = async (formData: { value: string; metadata?: string }) => {
    try {
      await createValue(formData.value, formData.metadata ? JSON.parse(formData.metadata) : {});
      message.success(`Valor "${formData.value}" criado com sucesso!`);
      setCreateModalOpen(false);
      refreshValues();
      return true;
    } catch (err) {
      message.error('Erro ao criar valor');
      return false;
    }
  };

  /**
   * Deleta um valor de referência usando o hook useConsulDelete
   * Usa APENAS dados do record - ZERO valores hardcoded
   */
  const handleDelete = async (value: string) => {
    await deleteResource({ value });
  };

  // Colunas da tabela
  const columns: ProColumns<ReferenceValue>[] = [
    {
      title: 'Valor',
      dataIndex: 'value',
      key: 'value',
      width: 250,
      render: (text) => (
        <Space>
          <Tag color={selectedFieldInfo?.color}>{selectedFieldInfo?.icon}</Tag>
          <Text strong>{text}</Text>
        </Space>
      ),
    },
    {
      title: 'Uso',
      dataIndex: 'usage_count',
      key: 'usage_count',
      width: 100,
      align: 'center',
      sorter: (a, b) => (a.usage_count || 0) - (b.usage_count || 0),
      render: (count) => (
        <Badge
          count={count || 0}
          showZero
          style={{ backgroundColor: count > 0 ? '#52c41a' : '#d9d9d9' }}
        />
      ),
    },
    {
      title: 'Criado em',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 180,
      render: (date) =>
        date ? new Date(date).toLocaleString('pt-BR') : <Text type="secondary">-</Text>,
    },
    {
      title: 'Criado por',
      dataIndex: 'created_by',
      key: 'created_by',
      width: 150,
      render: (user) => user || <Text type="secondary">Sistema</Text>,
    },
    {
      title: 'Último uso',
      dataIndex: 'last_used_at',
      key: 'last_used_at',
      width: 180,
      render: (date) =>
        date ? new Date(date).toLocaleString('pt-BR') : <Text type="secondary">Nunca</Text>,
    },
    {
      title: 'Ações',
      key: 'actions',
      width: 120,
      fixed: 'right',
      render: (_, record) => (
        <Space>
          <Tooltip title="Editar">
            <Button
              type="link"
              size="small"
              icon={<EditOutlined />}
              onClick={() => {
                setEditingValue(record);
                setEditModalOpen(true);
              }}
            />
          </Tooltip>
          <Popconfirm
            title="Deletar valor"
            description={
              record.usage_count && record.usage_count > 0
                ? `Este valor está em uso em ${record.usage_count} registro(s). Tem certeza?`
                : 'Tem certeza que deseja deletar este valor?'
            }
            onConfirm={() => handleDelete(record.value)}
            okText="Sim"
            cancelText="Não"
            okButtonProps={{ danger: true }}
          >
            <Tooltip title="Deletar">
              <Button
                type="link"
                size="small"
                danger
                icon={<DeleteOutlined />}
                disabled={record.usage_count !== undefined && record.usage_count > 0}
              />
            </Tooltip>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <PageContainer
      title="Configuração de Valores de Referência"
      subTitle="Gerencie todos os valores usados nos autocompletes do sistema"
      extra={[
        <Button
          key="reload"
          icon={<ReloadOutlined />}
          onClick={() => {
            console.log(`[ReferenceValues] 🔄 Botão RECARREGAR clicado - Campo selecionado: ${selectedField}`);
            refreshValues();
          }}
          loading={loading}
        >
          Recarregar
        </Button>,
        <Button
          key="add"
          type="primary"
          icon={<PlusOutlined />}
          onClick={() => setCreateModalOpen(true)}
        >
          Adicionar Valor
        </Button>,
      ]}
    >
      {/* Seletor de Campo por Categoria */}
      <ProCard title="📋 Selecione o Campo" bordered style={{ marginBottom: 16 }}>
        <Tabs
          defaultActiveKey="basic"
          type="card"
          size="large"
          items={Object.entries(FIELD_CATEGORIES).map(([key, category]) => ({
            key,
            label: (
              <span>
                {category.icon} {category.label}
              </span>
            ),
            children: (
              <div>
                <Paragraph type="secondary" style={{ marginBottom: 16 }}>
                  {category.description}
                </Paragraph>
                <Row gutter={[16, 16]}>
                  {category.fields.map((field) => (
                    <Col key={field.name} xs={24} sm={12} md={8} lg={6} xl={4}>
                      <Card
                        hoverable
                        style={{
                          borderColor: selectedField === field.name ? field.color : undefined,
                          borderWidth: selectedField === field.name ? 2 : 1,
                          backgroundColor: selectedField === field.name ? `${field.color}10` : undefined,
                        }}
                        onClick={() => setSelectedField(field.name)}
                      >
                        <Space direction="vertical" size="small" style={{ width: '100%' }}>
                          <div style={{ fontSize: 32, textAlign: 'center' }}>{field.icon}</div>
                          <Text strong style={{ textAlign: 'center', display: 'block' }}>
                            {field.label}
                          </Text>
                          <Tag color={field.color} style={{ margin: '0 auto', display: 'block', width: 'fit-content' }}>
                            {field.name}
                          </Tag>
                        </Space>
                      </Card>
                    </Col>
                  ))}
                </Row>
              </div>
            ),
          }))}
        />
      </ProCard>

      {/* Estatísticas */}
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={8}>
          <Card>
            <Statistic
              title="Total de Valores"
              value={totalValues}
              prefix={<DatabaseOutlined />}
              valueStyle={{ color: '#3f8600' }}
            />
          </Card>
        </Col>
        <Col span={8}>
          <Card>
            <Statistic
              title="Total de Usos"
              value={totalUsage}
              prefix={<CheckCircleOutlined />}
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>
        <Col span={8}>
          <Card>
            <Statistic
              title="Mais Usado"
              value={mostUsed?.value || '-'}
              suffix={mostUsed?.usage_count ? `(${mostUsed.usage_count}x)` : ''}
              valueStyle={{ color: '#cf1322', fontSize: 16 }}
            />
          </Card>
        </Col>
      </Row>

      {/* Tabela de Valores */}
      <ProCard
        title={
          <Space>
            {selectedFieldInfo?.icon}
            <span>Valores de {selectedFieldInfo?.label}</span>
            <Tag color={selectedFieldInfo?.color}>{totalValues} valores</Tag>
          </Space>
        }
        extra={
          <Search
            placeholder="Buscar valores..."
            allowClear
            value={searchText}
            onChange={(e) => setSearchText(e.target.value)}
            style={{ width: 250 }}
            prefix={<SearchOutlined />}
          />
        }
      >
        {error ? (
          <Empty
            description={
              <Space direction="vertical">
                <Text type="danger">Erro ao carregar valores</Text>
                <Text type="secondary">{error}</Text>
                <Button onClick={() => refreshValues()}>Tentar Novamente</Button>
              </Space>
            }
          />
        ) : (
          <ProTable<ReferenceValue>
            columns={columns}
            dataSource={filteredValues}
            rowKey="value"
            loading={loading}
            search={false}
            pagination={{
              defaultPageSize: 20,
              showSizeChanger: true,
              showTotal: (total) => `Total: ${total} valores`,
            }}
            options={{
              reload: false,
              density: true,
              setting: true,
            }}
            locale={{
              emptyText: (
                <Empty
                  description={
                    searchText
                      ? `Nenhum valor encontrado para "${searchText}"`
                      : `Nenhum valor cadastrado para ${selectedFieldInfo?.label}`
                  }
                >
                  <Button type="primary" icon={<PlusOutlined />} onClick={() => setCreateModalOpen(true)}>
                    Adicionar Primeiro Valor
                  </Button>
                </Empty>
              ),
            }}
          />
        )}
      </ProCard>

      {/* Modal: Criar Valor */}
      <ModalForm
        title={`➕ Adicionar Novo Valor - ${selectedFieldInfo?.label}`}
        open={createModalOpen}
        onOpenChange={setCreateModalOpen}
        onFinish={handleCreate}
        width={600}
        modalProps={{
          destroyOnHidden: true,
        }}
      >
        <ProFormText
          name="value"
          label="Valor"
          placeholder={`Digite o novo valor para ${selectedFieldInfo?.label}`}
          rules={[
            { required: true, message: 'Valor é obrigatório' },
            { min: 1, message: 'Valor muito curto' },
            { max: 200, message: 'Valor muito longo (máximo 200 caracteres)' },
          ]}
          tooltip="O valor será automaticamente normalizado (primeira letra maiúscula)"
          fieldProps={{
            prefix: selectedFieldInfo?.icon,
            maxLength: 200,
          }}
        />
        <ProFormTextArea
          name="metadata"
          label="Metadata (JSON - Opcional)"
          placeholder='{"key": "value"}'
          fieldProps={{
            rows: 4,
            placeholder: 'Adicione metadata adicional em formato JSON (opcional)',
          }}
          tooltip="Metadata adicional em formato JSON. Exemplo: {&quot;estado&quot;: &quot;SP&quot;, &quot;regiao&quot;: &quot;Sudeste&quot;}"
        />
      </ModalForm>

      {/* Modal: Editar Valor */}
      <ModalForm
        title={`✏️ Editar Valor - ${selectedFieldInfo?.label}`}
        open={editModalOpen}
        onOpenChange={(open) => {
          setEditModalOpen(open);
          if (!open) setEditingValue(null);
        }}
        onFinish={async (formData: { value: string; metadata?: string }) => {
          try {
            if (editingValue) {
              // CRÍTICO: Usa renameValue para PRESERVAR REFERÊNCIAS
              await renameValue(editingValue.value, formData.value);
              message.success(`Valor renomeado de "${editingValue.value}" para "${formData.value}" (referências preservadas)`);
              setEditModalOpen(false);
              setEditingValue(null);
              await refreshValues();
            }
            return true;
          } catch (err: any) {
            const errorMsg = err.message || 'Erro ao renomear valor';
            message.error(errorMsg);
            return false;
          }
        }}
        width={600}
        modalProps={{
          destroyOnHidden: true,
        }}
        initialValues={{
          value: editingValue?.value || '',
          metadata: editingValue?.metadata ? JSON.stringify(editingValue.metadata, null, 2) : '',
        }}
      >
        <ProFormText
          name="value"
          label="Valor"
          placeholder={`Digite o novo valor para ${selectedFieldInfo?.label}`}
          rules={[
            { required: true, message: 'Valor é obrigatório' },
            { min: 1, message: 'Valor muito curto' },
            { max: 200, message: 'Valor muito longo (máximo 200 caracteres)' },
          ]}
          tooltip="O valor será automaticamente normalizado (primeira letra maiúscula)"
          fieldProps={{
            prefix: selectedFieldInfo?.icon,
            maxLength: 200,
          }}
        />
        <ProFormTextArea
          name="metadata"
          label="Metadata (JSON - Opcional)"
          placeholder='{"key": "value"}'
          fieldProps={{
            rows: 4,
            placeholder: 'Adicione metadata adicional em formato JSON (opcional)',
          }}
          tooltip="Metadata adicional em formato JSON. Exemplo: {&quot;estado&quot;: &quot;SP&quot;, &quot;regiao&quot;: &quot;Sudeste&quot;}"
        />
      </ModalForm>
    </PageContainer>
  );
};

export default ReferenceValuesPage;

