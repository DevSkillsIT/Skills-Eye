import React, { useState, useRef } from 'react';
import {
  ProTable,
  ModalForm,
  ProFormText,
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
  Typography,
  List,
} from 'antd';
import { useConsulDelete } from '../hooks/useConsulDelete';
import {
  PlusOutlined,
  DownloadOutlined,
  EditOutlined,
  DeleteOutlined,
  EyeOutlined,
  AppstoreAddOutlined,
  FolderOutlined,
  TeamOutlined,
} from '@ant-design/icons';
import { consulAPI } from '../services/api';
import type { BlackboxGroup } from '../services/api';

const { Title, Text, Paragraph } = Typography;

interface GroupFormData {
  id: string;
  name: string;
  description?: string;
  tags?: string;
  metadata?: string;
}

type GroupColumn<T> = import('@ant-design/pro-components').ProColumns<T>;

const BlackboxGroups: React.FC = () => {
  const actionRef = useRef<ActionType | null>(null);
  const [createModalVisible, setCreateModalVisible] = useState(false);
  const [editModalVisible, setEditModalVisible] = useState(false);
  const [viewModalVisible, setViewModalVisible] = useState(false);
  const [selectedGroup, setSelectedGroup] = useState<BlackboxGroup | null>(null);
  const [groupTargets, setGroupTargets] = useState<any[]>([]);
  const [tableSnapshot, setTableSnapshot] = useState<BlackboxGroup[]>([]);

  const handleExport = () => {
    if (!tableSnapshot.length) {
      message.info('Nao ha dados para exportar');
      return;
    }
    const header = ['id','name','description','tags','created_at','created_by'];
    const rows = tableSnapshot.map((group) => [
      group.id,
      group.name,
      group.description || '',
      (group.tags || []).join('|'),
      group.created_at || '',
      group.created_by || 'system',
    ].join(';'));
    const csvContent = [header.join(';'), ...rows].join('\n');
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `blackbox-groups-${new Date().toISOString()}.csv`;
    link.click();
    URL.revokeObjectURL(url);
  };

  const columns: GroupColumn<BlackboxGroup>[] = [
    {
      title: 'ID',
      dataIndex: 'id',
      width: 200,
      ellipsis: true,
      copyable: true,
      render: (_, record) => (
        <Space>
          <FolderOutlined />
          <Text strong>{record.id}</Text>
        </Space>
      ),
    },
    {
      title: 'Nome',
      dataIndex: 'name',
      width: 250,
      ellipsis: true,
      render: (text) => <Text>{text}</Text>,
    },
    {
      title: 'Descricao',
      dataIndex: 'description',
      ellipsis: true,
      render: (text) => text || <Text type="secondary">Sem descricao</Text>,
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
      title: 'Criado em',
      dataIndex: 'created_at',
      width: 180,
      valueType: 'dateTime',
      render: (_, record) =>
        record.created_at ? new Date(record.created_at).toLocaleString('pt-BR') : '-',
    },
    {
      title: 'Criado por',
      dataIndex: 'created_by',
      width: 150,
      render: (text) => <Tag icon={<TeamOutlined />}>{text || 'system'}</Tag>,
    },
    {
      title: 'Acoes',
      valueType: 'option',
      width: 240,
      fixed: 'right',
      render: (_, record) => [
        <Tooltip title="Visualizar grupo" key={`view-${record.id}`}>
          <Button
            type="link"
            icon={<EyeOutlined />}
            aria-label="Visualizar grupo"
            onClick={() => handleViewGroup(record)}
          />
        </Tooltip>,
        <Tooltip title="Editar grupo" key={`edit-${record.id}`}>
          <Button
            type="link"
            icon={<EditOutlined />}
            aria-label="Editar grupo"
            onClick={() => handleEditGroup(record)}
          />
        </Tooltip>,
        <Popconfirm
          key={`delete-${record.id}`}
          title="Tem certeza que deseja deletar este grupo?"
          description="Os alvos do grupo nao serao removidos, apenas desagrupados."
          onConfirm={() => handleDelete(record.id)}
          okText="Remover"
          cancelText="Cancelar"
        >
          <Tooltip title="Remover grupo">
            <Button
              type="link"
              danger
              icon={<DeleteOutlined />}
              aria-label="Remover grupo"
            />
          </Tooltip>
        </Popconfirm>,
      ],
    },
  ];

  const handleViewGroup = async (group: BlackboxGroup) => {
    setSelectedGroup(group);
    setViewModalVisible(true);

    // Buscar targets deste grupo
    try {
      const response = await consulAPI.searchBlackboxTargets({
        group: group.id,
        page: 1,
        page_size: 100,
      });
      setGroupTargets(response.data.data || []);
    } catch (error) {
      console.error('Erro ao buscar targets do grupo:', error);
      setGroupTargets([]);
    }
  };

  const handleEditGroup = (group: BlackboxGroup) => {
    setSelectedGroup(group);
    setEditModalVisible(true);
  };

  // Hook compartilhado para DELETE com lógica padronizada
  const { deleteResource } = useConsulDelete({
    deleteFn: async (payload: any) => consulAPI.deleteBlackboxGroup(payload.group_id),
    successMessage: 'Grupo deletado com sucesso',
    errorMessage: 'Erro ao deletar grupo',
    onSuccess: () => {
      actionRef.current?.reload();
    },
  });

  const handleDelete = async (groupId: string) => {
    await deleteResource({ group_id: groupId });
  };

  const handleCreateGroup = async (values: GroupFormData) => {
    try {
      const payload: BlackboxGroup = {
        id: values.id,
        name: values.name,
        description: values.description,
        tags: values.tags ? values.tags.split(',').map((t) => t.trim()) : undefined,
        metadata: values.metadata ? JSON.parse(values.metadata) : undefined,
      };

      await consulAPI.createBlackboxGroup(payload);
      message.success('Grupo criado com sucesso');
      setCreateModalVisible(false);
      actionRef.current?.reload();
      return true;
    } catch (error: any) {
      message.error(error.response?.data?.detail || 'Erro ao criar grupo');
      return false;
    }
  };

  const handleUpdateGroup = async (values: GroupFormData) => {
    try {
      if (!selectedGroup) return false;

      const updates: Partial<BlackboxGroup> = {
        name: values.name,
        description: values.description,
        tags: values.tags ? values.tags.split(',').map((t) => t.trim()) : undefined,
        metadata: values.metadata ? JSON.parse(values.metadata) : undefined,
      };

      await consulAPI.updateBlackboxGroup(selectedGroup.id, updates);
      message.success('Grupo atualizado com sucesso');
      setEditModalVisible(false);
      setSelectedGroup(null);
      actionRef.current?.reload();
      return true;
    } catch (error: any) {
      message.error(error.response?.data?.detail || 'Erro ao atualizar grupo');
      return false;
    }
  };

  return (
    <div style={{ padding: 24 }}>
      <Card
        title={
          <Space>
            <AppstoreAddOutlined style={{ fontSize: 24 }} />
            <Title level={2} style={{ margin: 0 }}>
              Grupos de Alvos Blackbox
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
              Novo Grupo
            </Button>
          </Space>
        }
      >
        <Paragraph>
          Organize seus alvos Blackbox em grupos logicos para facilitar o gerenciamento e
          monitoramento. Grupos permitem agrupar targets por projeto, ambiente, cliente ou qualquer
          criterio que faca sentido para sua organizacao.
        </Paragraph>
      </Card>

      <div style={{ marginTop: 16 }}>
        <ProTable<BlackboxGroup>
          columns={columns}
          actionRef={actionRef}
          request={async () => {
            try {
              const response = await consulAPI.listBlackboxGroups();
              const groups = response.data.groups || [];
              setTableSnapshot(groups);
              return {
                data: groups,
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
            title: 'Lista de Grupos',
          }}
          pagination={{
            defaultPageSize: 10,
            showSizeChanger: true,
          }}
        />
      </div>

      {/* Modal Criar Grupo */}
      <ModalForm<GroupFormData>
        title="Criar Novo Grupo"
        open={createModalVisible}
        onOpenChange={setCreateModalVisible}
        onFinish={handleCreateGroup}
        width={600}
        layout="vertical"
      >
        <ProFormText
          name="id"
          label="ID do Grupo"
          placeholder="projeto-cliente-prod"
          rules={[
            { required: true, message: 'ID e obrigatorio' },
            {
              pattern: /^[a-z0-9-]+$/,
              message: 'Use apenas letras minusculas, numeros e hifens',
            },
          ]}
          tooltip="Identificador unico (kebab-case)"
        />

        <ProFormText
          name="name"
          label="Nome do Grupo"
          placeholder="Projeto Cliente - Producao"
          rules={[{ required: true, message: 'Nome e obrigatorio' }]}
        />

        <ProFormTextArea
          name="description"
          label="Descricao"
          placeholder="Descricao do grupo"
          fieldProps={{ rows: 3 }}
        />

        <ProFormText
          name="tags"
          label="Tags (separadas por virgula)"
          placeholder="producao, cliente-x, critico"
        />

        <ProFormTextArea
          name="metadata"
          label="Metadata (JSON opcional)"
          placeholder='{"responsible": "equipe-ops", "priority": "high"}'
          fieldProps={{ rows: 4, style: { fontFamily: 'monospace' } }}
        />
      </ModalForm>

      {/* Modal Editar Grupo */}
      <ModalForm<GroupFormData>
        title="Editar Grupo"
        open={editModalVisible}
        onOpenChange={setEditModalVisible}
        onFinish={handleUpdateGroup}
        width={600}
        layout="vertical"
        initialValues={
          selectedGroup
            ? {
                name: selectedGroup.name,
                description: selectedGroup.description,
                tags: selectedGroup.tags?.join(', '),
                metadata: selectedGroup.metadata
                  ? JSON.stringify(selectedGroup.metadata, null, 2)
                  : '',
              }
            : undefined
        }
      >
        <ProFormText
          name="name"
          label="Nome do Grupo"
          rules={[{ required: true, message: 'Nome e obrigatorio' }]}
        />

        <ProFormTextArea
          name="description"
          label="Descricao"
          fieldProps={{ rows: 3 }}
        />

        <ProFormText
          name="tags"
          label="Tags (separadas por virgula)"
        />

        <ProFormTextArea
          name="metadata"
          label="Metadata (JSON opcional)"
          fieldProps={{ rows: 4, style: { fontFamily: 'monospace' } }}
        />
      </ModalForm>

      {/* Modal Visualizar Grupo */}
      <Modal
        title="Detalhes do Grupo"
        open={viewModalVisible}
        onCancel={() => {
          setViewModalVisible(false);
          setSelectedGroup(null);
          setGroupTargets([]);
        }}
        footer={[
          <Button
            key="close"
            onClick={() => {
              setViewModalVisible(false);
              setSelectedGroup(null);
              setGroupTargets([]);
            }}
          >
            Fechar
          </Button>,
        ]}
        width={900}
      >
        {selectedGroup && (
          <>
            <Descriptions column={2} bordered style={{ marginBottom: 24 }}>
              <Descriptions.Item label="ID" span={2}>
                <Text copyable>{selectedGroup.id}</Text>
              </Descriptions.Item>
              <Descriptions.Item label="Nome" span={2}>
                {selectedGroup.name}
              </Descriptions.Item>
              {selectedGroup.description && (
                <Descriptions.Item label="Descricao" span={2}>
                  {selectedGroup.description}
                </Descriptions.Item>
              )}
              <Descriptions.Item label="Tags" span={2}>
                {selectedGroup.tags?.map((tag) => <Tag key={tag}>{tag}</Tag>) || 'Nenhuma'}
              </Descriptions.Item>
              <Descriptions.Item label="Criado em">
                {selectedGroup.created_at
                  ? new Date(selectedGroup.created_at).toLocaleString('pt-BR')
                  : '-'}
              </Descriptions.Item>
              <Descriptions.Item label="Criado por">
                {selectedGroup.created_by || 'system'}
              </Descriptions.Item>
              {selectedGroup.metadata && (
                <Descriptions.Item label="Metadata" span={2}>
                  <pre
                    style={{
                      margin: 0,
                      background: '#f5f5f5',
                      padding: 8,
                      borderRadius: 4,
                    }}
                  >
                    {JSON.stringify(selectedGroup.metadata, null, 2)}
                  </pre>
                </Descriptions.Item>
              )}
            </Descriptions>

            <Card
              title={
                <Space>
                  <TeamOutlined />
                  <span>Alvos neste Grupo</span>
                  <Tag color="blue">{groupTargets.length}</Tag>
                </Space>
              }
              style={{ marginTop: 16 }}
            >
              {groupTargets.length > 0 ? (
                <List
                  size="small"
                  dataSource={groupTargets}
                  renderItem={(target: any) => (
                    <List.Item>
                      <Space>
                        <Tag color={target.Meta?.enabled === 'true' ? 'green' : 'red'}>
                          {target.Meta?.enabled === 'true' ? 'Ativo' : 'Inativo'}
                        </Tag>
                        <Text strong>{target.Meta?.name || target.ID}</Text>
                        <Text type="secondary">
                          {target.Meta?.module || 'N/A'} - {target.Meta?.instance}
                        </Text>
                        {target.Meta?.company && <Tag>{target.Meta.company}</Tag>}
                        {target.Meta?.env && <Tag color="blue">{target.Meta.env}</Tag>}
                      </Space>
                    </List.Item>
                  )}
                  pagination={
                    groupTargets.length > 10
                      ? {
                          pageSize: 10,
                          size: 'small',
                        }
                      : false
                  }
                />
              ) : (
                <Text type="secondary">Nenhum alvo neste grupo ainda.</Text>
              )}
            </Card>
          </>
        )}
      </Modal>
    </div>
  );
};

export default BlackboxGroups;







