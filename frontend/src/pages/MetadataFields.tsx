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
} from 'antd';
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

  useEffect(() => {
    fetchServers();
  }, []);

  // Recarregar campos quando trocar de servidor
  useEffect(() => {
    if (selectedServer) {
      fetchFields();
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
      title={
        <div>
          <div style={{ fontSize: 20, fontWeight: 500, marginBottom: 4 }}>
            Gerenciamento de Campos Metadata
          </div>
          <div style={{ fontSize: 14, fontWeight: 400, color: 'rgba(0, 0, 0, 0.45)' }}>
            Adicionar, editar e sincronizar campos metadata em todos os servidores
          </div>
        </div>
      }
      extra={[
        <Select
          key="server-select"
          style={{ width: 350 }}
          value={selectedServer}
          onChange={setSelectedServer}
          placeholder="Selecionar servidor"
        >
          {servers.map(server => (
            <Select.Option key={server.id} value={server.id}>
              <CloudServerOutlined style={{ marginRight: 8 }} />
              <strong>{server.display_name}</strong>
              <span style={{ marginLeft: 8, color: '#999', fontSize: 12 }}>
                ({server.type === 'master' ? '🟢 Master' : '🔵 Slave'})
              </span>
            </Select.Option>
          ))}
        </Select>,
        <Button
          key="replicate"
          icon={<CloudSyncOutlined />}
          onClick={handleReplicateToSlaves}
          type="default"
          title="Replica configurações do Master para todos os Slaves"
        >
          Master → Slaves
        </Button>,
        <Space.Compact key="restart-group">
          <Button
            icon={<ReloadOutlined />}
            onClick={handleRestartSelected}
            type="default"
            title="Reiniciar Prometheus apenas no servidor selecionado"
          >
            Reiniciar Selecionado
          </Button>
          <Button
            icon={<ReloadOutlined />}
            onClick={handleRestartAll}
            type="default"
            danger
            title="Reiniciar Prometheus em todos os servidores"
          >
            Reiniciar Todos
          </Button>
        </Space.Compact>,
        <Button
          key="add"
          type="primary"
          icon={<PlusOutlined />}
          onClick={() => setCreateModalVisible(true)}
        >
          Adicionar Campo
        </Button>,
      ]}
    >
      {selectedServer && servers.length > 0 && (
        <Alert
          message={
            <span>
              <strong>Servidor Ativo:</strong> {servers.find(s => s.id === selectedServer)?.display_name || 'Carregando...'}
              <Badge
                status={servers.find(s => s.id === selectedServer)?.type === 'master' ? 'success' : 'processing'}
                text={servers.find(s => s.id === selectedServer)?.type === 'master' ? 'Master' : 'Slave'}
                style={{ marginLeft: 16 }}
              />
            </span>
          }
          description={`Total de servidores disponíveis: ${servers.length} (1 master + ${servers.length - 1} slaves)`}
          type="info"
          showIcon
          style={{ marginBottom: 16 }}
        />
      )}

      <ProCard>
        <ProTable<MetadataField>
          columns={columns}
          dataSource={fields}
          rowKey="name"
          loading={loading}
          search={false}
          options={{
            reload: fetchFields,
          }}
          pagination={{
            defaultPageSize: 20,
            showSizeChanger: true,
            pageSizeOptions: ['10', '20', '30', '50', '100'],
          }}
          scroll={{ x: 1400 }}
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
