/**
 * Página de Gerenciamento de Campos Metadata
 *
 * Permite:
 * - Adicionar novo campo metadata
 * - Editar campos existentes
 * - Sincronizar com prometheus.yml
 * - Replicar para servidores slaves
 * - Reiniciar serviços Prometheus
 */

import React, { useState, useEffect } from 'react';
import {
  PageContainer,
  ProTable,
  ProCard,
  ModalForm,
  ProFormText,
  ProFormSelect,
  ProFormSwitch,
  ProFormTextArea,
  ProFormDigit,
} from '@ant-design/pro-components';
import type { ProColumns } from '@ant-design/pro-components';
import {
  Button,
  Space,
  message,
  Tag,
  Badge,
  Popconfirm,
  Select,
  Tooltip,
  Modal,
  Alert,
  Row,
  Col,
  Card,
  Typography,
} from 'antd';

const { Text } = Typography;
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  SyncOutlined,
  CloudSyncOutlined,
  ReloadOutlined,
  CheckCircleOutlined,
  WarningOutlined,
  CloudServerOutlined,
} from '@ant-design/icons';
import axios from 'axios';

const API_URL = import.meta.env?.VITE_API_URL ?? 'http://localhost:5000/api/v1';

interface MetadataField {
  name: string;
  display_name: string;
  description: string;
  source_label: string;
  field_type: string;
  required: boolean;
  show_in_table: boolean;
  show_in_dashboard: boolean;
  show_in_form: boolean;
  options?: string[];
  order: number;
  category: string;
  editable: boolean;
  validation_regex?: string;
  sync_status?: 'synced' | 'outdated' | 'missing' | 'error';  // ← NOVO: Status de sincronização
  sync_message?: string;  // ← NOVO: Mensagem do status
}

interface Server {
  id: string;
  hostname: string;
  port: number;
  username: string;
  type: string;
  display_name: string;
}

const MetadataFieldsPage: React.FC = () => {
  const [fields, setFields] = useState<MetadataField[]>([]);
  const [servers, setServers] = useState<Server[]>([]);
  const [selectedServer, setSelectedServer] = useState<string>('');
  const [loading, setLoading] = useState(false);
  const [loadingSyncStatus, setLoadingSyncStatus] = useState(false);  // ← NOVO
  const [serverJustChanged, setServerJustChanged] = useState(false);  // ← NOVO: Animação de troca
  const [createModalVisible, setCreateModalVisible] = useState(false);
  const [editModalVisible, setEditModalVisible] = useState(false);
  const [editingField, setEditingField] = useState<MetadataField | null>(null);

  const fetchFields = async () => {
    setLoading(true);
    try {
      const response = await axios.get(`${API_URL}/metadata-fields/`, {
        timeout: 30000, // 30 segundos (pode precisar consultar múltiplos arquivos)
      });
      if (response.data.success) {
        setFields(response.data.fields);
      }
    } catch (error: any) {
      if (error.code === 'ECONNABORTED') {
        message.error('Tempo esgotado ao carregar campos (servidor lento)');
      } else {
        message.error('Erro ao carregar campos: ' + (error.response?.data?.detail || error.message));
      }
    } finally {
      setLoading(false);
    }
  };

  const fetchServers = async () => {
    try {
      const response = await axios.get(`${API_URL}/metadata-fields/servers`, {
        timeout: 15000, // 15 segundos (primeira requisição pode consultar Consul)
      });
      if (response.data.success) {
        setServers(response.data.servers);
        // Selecionar master por padrão
        if (response.data.master) {
          setSelectedServer(response.data.master.id);
        }
      }
    } catch (error: any) {
      if (error.code === 'ECONNABORTED') {
        message.error('Tempo esgotado ao carregar servidores (servidor lento)');
      } else {
        message.error('Erro ao carregar servidores: ' + (error.response?.data?.detail || error.message));
      }
    }
  };

  const fetchSyncStatus = async (serverId: string) => {
    if (!serverId) return;

    setLoadingSyncStatus(true);
    try {
      const response = await axios.get(`${API_URL}/metadata-fields/sync-status`, {
        params: { server_id: serverId },
        timeout: 30000, // 30 segundos (SSH pode ser lento)
      });

      if (response.data.success) {
        // Atualizar campos com status de sincronização
        const syncStatusMap = new Map(
          response.data.fields.map((f: any) => [f.name, {
            sync_status: f.sync_status,
            sync_message: f.message
          }])
        );

        setFields((prevFields) =>
          prevFields.map((field) => ({
            ...field,
            sync_status: syncStatusMap.get(field.name)?.sync_status || 'error',
            sync_message: syncStatusMap.get(field.name)?.sync_message || 'Status desconhecido',
          }))
        );
      }
    } catch (error: any) {
      if (error.code === 'ECONNABORTED') {
        message.error('Tempo esgotado ao verificar sincronização (servidor lento)');
      } else {
        message.error('Erro ao verificar sincronização: ' + (error.response?.data?.detail || error.message));
      }
    } finally {
      setLoadingSyncStatus(false);
    }
  };

  useEffect(() => {
    fetchServers();
  }, []);

  // Recarregar campos e sync status quando trocar de servidor
  useEffect(() => {
    if (selectedServer) {
      // Animação de "servidor alterado"
      setServerJustChanged(true);
      setTimeout(() => setServerJustChanged(false), 2000);

      // Limpar dados antigos IMEDIATAMENTE
      setFields([]);

      // Carregar novos dados
      fetchFields();
      fetchSyncStatus(selectedServer);
    }
  }, [selectedServer]);

  const handleCreateField = async (values: any) => {
    try {
      const response = await axios.post(`${API_URL}/metadata-fields/`, {
        field: {
          ...values,
          source_label: `__meta_consul_service_metadata_${values.name}`,
        },
        sync_prometheus: true
      });

      if (response.data.success) {
        message.success(`Campo '${values.display_name}' criado com sucesso!`);
        fetchFields();
        setCreateModalVisible(false);

        // Perguntar se quer replicar
        Modal.confirm({
          title: 'Replicar para servidores slaves?',
          content: 'Deseja replicar este campo para todos os servidores slaves?',
          okText: 'Sim, replicar',
          cancelText: 'Não',
          onOk: () => handleReplicateToSlaves(),
        });
      }
    } catch (error: any) {
      message.error('Erro ao criar campo: ' + (error.response?.data?.detail || error.message));
    }
  };

  const handleEditField = async (values: any) => {
    if (!editingField) return;

    try {
      const response = await axios.put(`${API_URL}/metadata-fields/${editingField.name}`, values);

      if (response.data.success) {
        message.success(`Campo '${values.display_name}' atualizado com sucesso!`);
        fetchFields();
        setEditModalVisible(false);
        setEditingField(null);
      }
    } catch (error: any) {
      message.error('Erro ao atualizar campo: ' + (error.response?.data?.detail || error.message));
    }
  };

  const handleDeleteField = async (fieldName: string) => {
    try {
      const response = await axios.delete(`${API_URL}/metadata-fields/${fieldName}`);

      if (response.data.success) {
        message.success(`Campo deletado com sucesso!`);
        fetchFields();
      }
    } catch (error: any) {
      message.error('Erro ao deletar campo: ' + (error.response?.data?.detail || error.message));
    }
  };

  const handleReplicateToSlaves = async () => {
    const hide = message.loading('Replicando configurações...', 0);
    try {
      const response = await axios.post(`${API_URL}/metadata-fields/replicate-to-slaves`, {});

      hide();

      if (response.data.success) {
        const successCount = response.data.results.filter((r: any) => r.success).length;
        Modal.success({
          title: 'Replicação Concluída',
          content: (
            <div>
              <p>{response.data.message}</p>
              <ul>
                {response.data.results.map((r: any, idx: number) => (
                  <li key={idx} style={{ color: r.success ? 'green' : 'red' }}>
                    {r.server}: {r.success ? r.message : r.error}
                  </li>
                ))}
              </ul>
            </div>
          ),
        });
      }
    } catch (error: any) {
      hide();
      message.error('Erro ao replicar: ' + (error.response?.data?.detail || error.message));
    }
  };


  const columns: ProColumns<MetadataField>[] = [
    {
      title: 'Ordem',
      dataIndex: 'order',
      width: 70,
      render: (order) => <Badge count={order} style={{ backgroundColor: '#1890ff' }} />,
    },
    {
      title: 'Nome Técnico',
      dataIndex: 'name',
      width: 180,
      render: (name) => <code>{name}</code>,
    },
    {
      title: 'Nome de Exibição',
      dataIndex: 'display_name',
      width: 180,
      render: (text) => <strong>{text}</strong>,
    },
    {
      title: 'Tipo',
      dataIndex: 'field_type',
      width: 100,
      render: (type) => {
        const colors: Record<string, string> = {
          string: 'default',
          number: 'blue',
          select: 'purple',
          text: 'green',
          url: 'orange',
        };
        return <Tag color={colors[type] || 'default'}>{type}</Tag>;
      },
    },
    {
      title: 'Categoria',
      dataIndex: 'category',
      width: 120,
      render: (cat) => <Tag>{cat}</Tag>,
    },
    {
      title: 'Obrigatório',
      dataIndex: 'required',
      width: 100,
      render: (req) => req ? <Tag color="red">Sim</Tag> : <Tag>Não</Tag>,
    },
    {
      title: 'Visibilidade',
      width: 150,
      render: (_, record) => (
        <Space size={4}>
          {record.show_in_table && <Tag color="blue">Tabela</Tag>}
          {record.show_in_dashboard && <Tag color="green">Dashboard</Tag>}
          {record.show_in_form && <Tag color="orange">Form</Tag>}
        </Space>
      ),
    },
    {
      title: 'Status Prometheus',
      dataIndex: 'sync_status',
      width: 160,
      align: 'center' as const,
      render: (status, record) => {
        if (loadingSyncStatus) {
          return <Tag icon={<SyncOutlined spin />} color="processing">Verificando...</Tag>;
        }

        if (!status) {
          return <Tag color="default">-</Tag>;
        }

        const statusConfig = {
          synced: {
            icon: <CheckCircleOutlined />,
            color: 'success',
            text: 'Sincronizado',
          },
          missing: {
            icon: <WarningOutlined />,
            color: 'error',
            text: 'Não Aplicado',
          },
          outdated: {
            icon: <WarningOutlined />,
            color: 'warning',
            text: 'Desatualizado',
          },
          error: {
            icon: <WarningOutlined />,
            color: 'default',
            text: 'Erro',
          },
        };

        const config = statusConfig[status as keyof typeof statusConfig];

        return (
          <Tooltip title={record.sync_message || 'Status de sincronização'}>
            <Tag icon={config.icon} color={config.color}>
              {config.text}
            </Tag>
          </Tooltip>
        );
      },
    },
    {
      title: 'Ações',
      width: 150,
      fixed: 'right',
      render: (_, record) => (
        <Space>
          <Tooltip title="Editar">
            <Button
              type="link"
              icon={<EditOutlined />}
              onClick={() => {
                setEditingField(record);
                setEditModalVisible(true);
              }}
            />
          </Tooltip>
          {!record.required && (
            <Popconfirm
              title="Tem certeza que deseja deletar este campo?"
              onConfirm={() => handleDeleteField(record.name)}
              okText="Sim"
              cancelText="Não"
            >
              <Tooltip title="Deletar">
                <Button type="link" danger icon={<DeleteOutlined />} />
              </Tooltip>
            </Popconfirm>
          )}
        </Space>
      ),
    },
  ];

  const handleRestartSelected = async () => {
    const selectedServerObj = servers.find(s => s.id === selectedServer);
    if (!selectedServerObj) {
      message.error('Nenhum servidor selecionado');
      return;
    }

    Modal.confirm({
      title: 'Confirmar Reinicialização',
      content: `Deseja reiniciar o Prometheus no servidor ${selectedServerObj.hostname}?`,
      okText: 'Sim, reiniciar',
      cancelText: 'Cancelar',
      onOk: async () => {
        const hide = message.loading(`Reiniciando Prometheus em ${selectedServerObj.hostname}...`, 0);
        try {
          const response = await axios.post(`${API_URL}/metadata-fields/restart-prometheus`, {
            server_ids: [selectedServer]
          });

          hide();

          if (response.data.success) {
            message.success(`Prometheus reiniciado com sucesso em ${selectedServerObj.hostname}`);
          }
        } catch (error: any) {
          hide();
          message.error('Erro ao reiniciar: ' + (error.response?.data?.detail || error.message));
        }
      },
    });
  };

  const handleRestartAll = async () => {
    Modal.confirm({
      title: 'Confirmar Reinicialização em Todos os Servidores',
      content: `Deseja reiniciar o Prometheus em TODOS os ${servers.length} servidores (Master + Slaves)?`,
      okText: 'Sim, reiniciar todos',
      cancelText: 'Cancelar',
      onOk: async () => {
        const hide = message.loading('Reiniciando Prometheus em todos os servidores...', 0);
        try {
          const response = await axios.post(`${API_URL}/metadata-fields/restart-prometheus`, {});

          hide();

          if (response.data.success) {
            Modal.success({
              title: 'Reinicialização Concluída',
              content: (
                <div>
                  <p>{response.data.message}</p>
                  <ul>
                    {response.data.results.map((r: any, idx: number) => (
                      <li key={idx} style={{ color: r.success ? 'green' : 'red' }}>
                        {r.server}: {r.success ? r.message : r.error}
                      </li>
                    ))}
                  </ul>
                </div>
              ),
            });
          }
        } catch (error: any) {
          hide();
          message.error('Erro ao reiniciar: ' + (error.response?.data?.detail || error.message));
        }
      },
    });
  };

  return (
    <PageContainer
      title="Gerenciamento de Campos Metadata"
      subTitle="Adicionar, editar e sincronizar campos metadata em todos os servidores"
    >
      {/* Alert de Informações do Servidor - ALTURA FIXA */}
      <div style={{ height: 56, marginBottom: 16, overflow: 'hidden' }}>
        <Alert
          message={
            selectedServer && servers.length > 0 ? (
              <span style={{ display: 'inline-flex', alignItems: 'center', gap: 8, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                <strong>Servidor:</strong>
                <span>{servers.find(s => s.id === selectedServer)?.display_name || 'Carregando...'}</span>
                <Badge
                  status={servers.find(s => s.id === selectedServer)?.type === 'master' ? 'success' : 'processing'}
                  text={servers.find(s => s.id === selectedServer)?.type === 'master' ? 'Master' : 'Slave'}
                />
                <span>•</span>
                <span><strong>{fields.length}</strong> campo(s)</span>
                {serverJustChanged && (
                  <Tag color="success" icon={<CheckCircleOutlined />}>
                    Alterado!
                  </Tag>
                )}
              </span>
            ) : (
              <span>
                <strong>Nenhum servidor selecionado</strong> - Selecione abaixo
              </span>
            )
          }
          type={selectedServer && serverJustChanged ? 'success' : selectedServer ? 'info' : 'warning'}
          showIcon
          style={{
            transition: 'all 0.5s ease',
            ...(serverJustChanged && {
              border: '2px solid #52c41a',
              boxShadow: '0 4px 12px rgba(82, 196, 26, 0.4)',
              backgroundColor: '#f6ffed',
            }),
          }}
        />
      </div>

      {/* Card de Seleção de Servidor e Ações - ALTURA FIXA */}
      <Card style={{ marginBottom: 16, height: 140, overflow: 'hidden' }}>
        <Row gutter={[16, 16]} align="middle">
          {/* Coluna 1: Seletor de Servidor */}
          <Col xs={24} lg={10}>
            <Space direction="vertical" size={4} style={{ width: '100%' }}>
              <Text strong style={{ fontSize: 13 }}>
                <CloudServerOutlined style={{ marginRight: 4 }} />
                Servidor Prometheus
              </Text>
              <Select
                size="large"
                style={{ width: '100%' }}
                value={selectedServer}
                onChange={setSelectedServer}
                placeholder="Selecione o servidor"
              >
                {servers.map(server => (
                  <Select.Option key={server.id} value={server.id}>
                    <Space>
                      <CloudServerOutlined />
                      <span>{server.display_name}</span>
                      <Tag color={server.type === 'master' ? 'green' : 'blue'} style={{ margin: 0 }}>
                        {server.type === 'master' ? 'Master' : 'Slave'}
                      </Tag>
                    </Space>
                  </Select.Option>
                ))}
              </Select>
            </Space>
          </Col>

          {/* Coluna 2: Botão Adicionar Campo */}
          <Col xs={12} lg={4}>
            <Space direction="vertical" size={4} style={{ width: '100%' }}>
              <Text strong style={{ fontSize: 13, opacity: 0 }}>.</Text>
              <Button
                type="primary"
                size="large"
                block
                icon={<PlusOutlined />}
                onClick={() => setCreateModalVisible(true)}
              >
                Adicionar Campo
              </Button>
            </Space>
          </Col>

          {/* Coluna 3: Botão Replicar */}
          <Col xs={12} lg={4}>
            <Space direction="vertical" size={4} style={{ width: '100%' }}>
              <Text strong style={{ fontSize: 13, opacity: 0 }}>.</Text>
              <Tooltip title="Replica configurações do Master para todos os Slaves">
                <Button
                  size="large"
                  block
                  icon={<CloudSyncOutlined />}
                  onClick={handleReplicateToSlaves}
                  disabled={!selectedServer}
                >
                  Master → Slaves
                </Button>
              </Tooltip>
            </Space>
          </Col>

          {/* Coluna 4: Botões Reiniciar */}
          <Col xs={24} lg={6}>
            <Space direction="vertical" size={4} style={{ width: '100%' }}>
              <Text strong style={{ fontSize: 13, opacity: 0 }}>.</Text>
              <Space.Compact size="large" block style={{ width: '100%' }}>
                <Button
                  icon={<ReloadOutlined />}
                  onClick={handleRestartSelected}
                  disabled={!selectedServer}
                  title="Reiniciar Prometheus apenas no servidor selecionado"
                  style={{ flex: 1 }}
                >
                  Reiniciar Selecionado
                </Button>
                <Button
                  icon={<ReloadOutlined />}
                  onClick={handleRestartAll}
                  danger
                  title="Reiniciar Prometheus em todos os servidores"
                  style={{ flex: 1 }}
                >
                  Reiniciar Todos
                </Button>
              </Space.Compact>
            </Space>
          </Col>
        </Row>
      </Card>

      {/* Tabela de Campos */}
      <ProCard>
        <ProTable<MetadataField>
          columns={columns}
          dataSource={fields}
          rowKey="name"
          loading={loading || loadingSyncStatus}
          search={false}
          options={{
            reload: () => {
              fetchFields();
              if (selectedServer) {
                fetchSyncStatus(selectedServer);
              }
            },
          }}
          pagination={{
            defaultPageSize: 20,
            showSizeChanger: true,
            pageSizeOptions: ['10', '20', '30', '50', '100'],
            showTotal: (total) => `Total: ${total} campos`,
          }}
          scroll={{ x: 1600 }}
          toolBarRender={() => [
            <Tooltip key="sync" title="Atualizar status de sincronização">
              <Button
                icon={<SyncOutlined spin={loadingSyncStatus} />}
                onClick={() => selectedServer && fetchSyncStatus(selectedServer)}
                disabled={!selectedServer || loadingSyncStatus}
              >
                {loadingSyncStatus ? 'Verificando...' : 'Verificar Sincronização'}
              </Button>
            </Tooltip>,
          ]}
        />
      </ProCard>

      {/* Modal Criar Campo */}
      <ModalForm
        title="Adicionar Novo Campo Metadata"
        open={createModalVisible}
        onOpenChange={setCreateModalVisible}
        onFinish={handleCreateField}
        modalProps={{
          width: 600,
        }}
      >
        <ProFormText
          name="name"
          label="Nome Técnico"
          placeholder="ex: datacenter"
          rules={[{ required: true, pattern: /^[a-z_]+$/, message: 'Apenas letras minúsculas e underscore' }]}
          tooltip="Nome técnico usado internamente (apenas letras minúsculas e _)"
        />
        <ProFormText
          name="display_name"
          label="Nome de Exibição"
          placeholder="ex: Data Center"
          rules={[{ required: true }]}
          tooltip="Nome amigável que aparece na interface"
        />
        <ProFormTextArea
          name="description"
          label="Descrição"
          placeholder="Descrição do campo"
          rows={2}
        />
        <ProFormSelect
          name="field_type"
          label="Tipo do Campo"
          options={[
            { label: 'Texto (string)', value: 'string' },
            { label: 'Número (number)', value: 'number' },
            { label: 'Seleção (select)', value: 'select' },
            { label: 'Texto Longo (text)', value: 'text' },
            { label: 'URL (url)', value: 'url' },
          ]}
          rules={[{ required: true }]}
        />
        <ProFormSelect
          name="category"
          label="Categoria"
          options={[
            { label: 'Infraestrutura', value: 'infrastructure' },
            { label: 'Básico', value: 'basic' },
            { label: 'Dispositivo', value: 'device' },
            { label: 'Extras', value: 'extra' },
          ]}
          initialValue="extra"
          rules={[{ required: true }]}
        />
        <ProFormDigit
          name="order"
          label="Ordem"
          min={1}
          max={999}
          initialValue={23}
          fieldProps={{ precision: 0 }}
        />
        <ProFormSwitch name="required" label="Campo Obrigatório" initialValue={false} />
        <ProFormSwitch name="show_in_table" label="Mostrar em Tabelas" initialValue={true} />
        <ProFormSwitch name="show_in_dashboard" label="Mostrar no Dashboard" initialValue={false} />
        <ProFormSwitch name="show_in_form" label="Mostrar em Formulários" initialValue={true} />
        <ProFormSwitch name="editable" label="Editável" initialValue={true} />
      </ModalForm>

      {/* Modal Editar Campo */}
      <ModalForm
        title={`Editar Campo: ${editingField?.display_name}`}
        open={editModalVisible}
        onOpenChange={(visible) => {
          setEditModalVisible(visible);
          if (!visible) setEditingField(null);
        }}
        onFinish={handleEditField}
        initialValues={editingField || {}}
        modalProps={{
          width: 600,
        }}
      >
        <ProFormText name="name" label="Nome Técnico" disabled />
        <ProFormText
          name="display_name"
          label="Nome de Exibição"
          rules={[{ required: true }]}
        />
        <ProFormTextArea name="description" label="Descrição" rows={2} />
        <ProFormSelect
          name="field_type"
          label="Tipo do Campo"
          options={[
            { label: 'Texto (string)', value: 'string' },
            { label: 'Número (number)', value: 'number' },
            { label: 'Seleção (select)', value: 'select' },
            { label: 'Texto Longo (text)', value: 'text' },
            { label: 'URL (url)', value: 'url' },
          ]}
          rules={[{ required: true }]}
        />
        <ProFormSelect
          name="category"
          label="Categoria"
          options={[
            { label: 'Infraestrutura', value: 'infrastructure' },
            { label: 'Básico', value: 'basic' },
            { label: 'Dispositivo', value: 'device' },
            { label: 'Extras', value: 'extra' },
          ]}
          rules={[{ required: true }]}
        />
        <ProFormDigit
          name="order"
          label="Ordem"
          min={1}
          max={999}
          fieldProps={{ precision: 0 }}
        />
        <ProFormSwitch name="required" label="Campo Obrigatório" />
        <ProFormSwitch name="show_in_table" label="Mostrar em Tabelas" />
        <ProFormSwitch name="show_in_dashboard" label="Mostrar no Dashboard" />
        <ProFormSwitch name="show_in_form" label="Mostrar em Formulários" />
        <ProFormSwitch name="editable" label="Editável" />
        <ProFormText name="source_label" label="Source Label" disabled />
      </ModalForm>
    </PageContainer>
  );
};

export default MetadataFieldsPage;
