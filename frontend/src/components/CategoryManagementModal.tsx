/**
 * CategoryManagementModal - Modal para gerenciar categorias de campos
 *
 * Categorias são usadas para organizar campos em abas temáticas na página Reference Values.
 * Exemplos: Básico, Infraestrutura, Dispositivo, Localização, etc.
 */
import React, { useRef, useState } from 'react';
import { Modal, message, Popconfirm, Tag, Space, Input, InputNumber, Select, Tooltip } from 'antd';
import { ProTable, ActionType, ProColumns, ModalForm, ProFormText, ProFormDigit, ProFormTextArea, ProForm } from '@ant-design/pro-components';
import { DeleteOutlined, EditOutlined, PlusOutlined, ReloadOutlined, UndoOutlined, InfoCircleOutlined } from '@ant-design/icons';
import { categoryAPI, CategoryInfo, CategoryCreateRequest } from '../services/api';

interface CategoryManagementModalProps {
  open: boolean;
  onCancel: () => void;
}

const CategoryManagementModal: React.FC<CategoryManagementModalProps> = ({ open, onCancel }) => {
  const actionRef = useRef<ActionType>();
  const [editingCategory, setEditingCategory] = useState<CategoryInfo | null>(null);
  const [createModalOpen, setCreateModalOpen] = useState(false);
  const [editModalOpen, setEditModalOpen] = useState(false);

  // Cores disponíveis do Ant Design
  const AVAILABLE_COLORS = [
    { label: 'Azul', value: 'blue' },
    { label: 'Ciano', value: 'cyan' },
    { label: 'Verde', value: 'green' },
    { label: 'Laranja', value: 'orange' },
    { label: 'Roxo', value: 'purple' },
    { label: 'Vermelho', value: 'red' },
    { label: 'Geekblue', value: 'geekblue' },
    { label: 'Magenta', value: 'magenta' },
    { label: 'Volcano', value: 'volcano' },
    { label: 'Dourado', value: 'gold' },
    { label: 'Lime', value: 'lime' },
    { label: 'Padrão', value: 'default' },
  ];

  const columns: ProColumns<CategoryInfo>[] = [
    {
      title: 'Key',
      dataIndex: 'key',
      width: 150,
      copyable: true,
      tooltip: 'ID único da categoria (não pode ser alterado)',
      render: (text) => <code>{text}</code>,
    },
    {
      title: 'Label',
      dataIndex: 'label',
      width: 150,
      tooltip: 'Nome exibido na aba',
    },
    {
      title: 'Ícone',
      dataIndex: 'icon',
      width: 80,
      align: 'center',
      render: (text) => <span style={{ fontSize: 24 }}>{text}</span>,
    },
    {
      title: 'Descrição',
      dataIndex: 'description',
      ellipsis: true,
      tooltip: 'Descrição do que a categoria contém',
    },
    {
      title: 'Ordem',
      dataIndex: 'order',
      width: 80,
      align: 'center',
      tooltip: 'Ordem de exibição (menor = primeiro)',
      sorter: (a, b) => a.order - b.order,
    },
    {
      title: 'Cor',
      dataIndex: 'color',
      width: 120,
      render: (color: string, record) => (
        <Tag color={color}>{record.label}</Tag>
      ),
    },
    {
      title: 'Ações',
      key: 'actions',
      width: 120,
      align: 'center',
      render: (_, record) => (
        <Space>
          <Tooltip title="Editar categoria">
            <a
              onClick={() => {
                setEditingCategory(record);
                setEditModalOpen(true);
              }}
            >
              <EditOutlined />
            </a>
          </Tooltip>
          <Popconfirm
            title="Deletar categoria?"
            description={
              <div style={{ maxWidth: 300 }}>
                <p>Tem certeza que deseja deletar a categoria <strong>{record.label}</strong>?</p>
                <p style={{ color: '#ff4d4f', marginTop: 8 }}>
                  ⚠️ Campos associados a esta categoria ficarão sem categoria.
                </p>
              </div>
            }
            onConfirm={async () => {
              try {
                const response = await categoryAPI.deleteCategory(record.key, false, 'admin');
                if (response.data.success) {
                  message.success(response.data.message);
                  actionRef.current?.reload();
                } else {
                  message.error(response.data.message);
                }
              } catch (error: any) {
                const errorMsg = error.response?.data?.detail || error.message || 'Erro ao deletar categoria';
                message.error(errorMsg);
              }
            }}
            okText="Sim, deletar"
            cancelText="Cancelar"
            okButtonProps={{ danger: true }}
          >
            <a style={{ color: '#ff4d4f' }}>
              <DeleteOutlined />
            </a>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  const handleCreateCategory = async (values: CategoryCreateRequest) => {
    try {
      const response = await categoryAPI.createCategory(values, 'admin');
      if (response.data.success) {
        message.success(response.data.message);
        setCreateModalOpen(false);
        actionRef.current?.reload();
        return true;
      } else {
        message.error(response.data.message);
        return false;
      }
    } catch (error: any) {
      const errorMsg = error.response?.data?.detail || error.message || 'Erro ao criar categoria';
      message.error(errorMsg);
      return false;
    }
  };

  const handleUpdateCategory = async (values: any) => {
    if (!editingCategory) return false;

    try {
      const response = await categoryAPI.updateCategory(editingCategory.key, values, 'admin');
      if (response.data.success) {
        message.success(response.data.message);
        setEditModalOpen(false);
        setEditingCategory(null);
        actionRef.current?.reload();
        return true;
      } else {
        message.error(response.data.message);
        return false;
      }
    } catch (error: any) {
      const errorMsg = error.response?.data?.detail || error.message || 'Erro ao atualizar categoria';
      message.error(errorMsg);
      return false;
    }
  };

  const handleResetToDefaults = async () => {
    try {
      const response = await categoryAPI.resetToDefaults('admin');
      if (response.data.success) {
        message.success(response.data.message);
        actionRef.current?.reload();
      } else {
        message.error(response.data.message);
      }
    } catch (error: any) {
      const errorMsg = error.response?.data?.detail || error.message || 'Erro ao resetar categorias';
      message.error(errorMsg);
    }
  };

  return (
    <>
      <Modal
        title={
          <Space>
            <span>Gerenciar Categorias</span>
            <Tooltip title="Categorias organizam campos em abas temáticas na página Reference Values">
              <InfoCircleOutlined style={{ color: '#1890ff', cursor: 'help' }} />
            </Tooltip>
          </Space>
        }
        open={open}
        onCancel={onCancel}
        width={1000}
        footer={null}
        destroyOnClose
      >
        <ProTable<CategoryInfo>
          columns={columns}
          actionRef={actionRef}
          request={async () => {
            try {
              const response = await categoryAPI.listCategories();
              return {
                data: response.data.categories || [],
                success: true,
                total: response.data.total || 0,
              };
            } catch (error) {
              message.error('Erro ao carregar categorias');
              return {
                data: [],
                success: false,
                total: 0,
              };
            }
          }}
          rowKey="key"
          pagination={false}
          search={false}
          dateFormatter="string"
          headerTitle="Categorias Cadastradas"
          toolBarRender={() => [
            <Popconfirm
              key="reset"
              title="Resetar categorias?"
              description={
                <div style={{ maxWidth: 300 }}>
                  <p>Tem certeza que deseja restaurar categorias padrão?</p>
                  <p style={{ color: '#ff4d4f', marginTop: 8 }}>
                    ⚠️ TODAS as categorias customizadas serão removidas!
                  </p>
                </div>
              }
              onConfirm={handleResetToDefaults}
              okText="Sim, resetar"
              cancelText="Cancelar"
              okButtonProps={{ danger: true }}
            >
              <a style={{ color: '#faad14' }}>
                <UndoOutlined /> Restaurar Padrão
              </a>
            </Popconfirm>,
            <a key="reload" onClick={() => actionRef.current?.reload()}>
              <ReloadOutlined /> Recarregar
            </a>,
            <a
              key="create"
              onClick={() => setCreateModalOpen(true)}
              style={{ color: '#52c41a' }}
            >
              <PlusOutlined /> Nova Categoria
            </a>,
          ]}
        />
      </Modal>

      {/* Modal de Criação */}
      <ModalForm
        title="Nova Categoria"
        open={createModalOpen}
        onOpenChange={setCreateModalOpen}
        onFinish={handleCreateCategory}
        modalProps={{
          destroyOnClose: true,
        }}
      >
        <ProFormText
          name="key"
          label="Key (ID)"
          placeholder="exemplo: monitoring"
          rules={[
            { required: true, message: 'Key é obrigatória' },
            { pattern: /^[a-z_]+$/, message: 'Apenas letras minúsculas e underscore' },
          ]}
          tooltip="ID único, apenas letras minúsculas e underscore (ex: monitoring, cloud_services)"
        />
        <ProFormText
          name="label"
          label="Label"
          placeholder="Monitoramento"
          rules={[{ required: true, message: 'Label é obrigatório' }]}
          tooltip="Nome exibido na aba"
        />
        <ProFormText
          name="icon"
          label="Ícone (Emoji)"
          placeholder="📊"
          initialValue="📝"
          tooltip="Emoji que aparece na aba. Cole um emoji aqui."
        />
        <ProFormTextArea
          name="description"
          label="Descrição"
          placeholder="Campos relacionados a monitoramento e observabilidade"
          tooltip="Descrição do que a categoria contém"
        />
        <ProFormDigit
          name="order"
          label="Ordem"
          placeholder="10"
          initialValue={99}
          min={1}
          max={999}
          tooltip="Ordem de exibição (menor número aparece primeiro)"
        />
        <ProForm.Item
          name="color"
          label="Cor"
          initialValue="default"
          tooltip="Cor da tag (visual)"
        >
          <Select options={AVAILABLE_COLORS} />
        </ProForm.Item>
      </ModalForm>

      {/* Modal de Edição */}
      <ModalForm
        title={`Editar Categoria: ${editingCategory?.label}`}
        open={editModalOpen}
        onOpenChange={setEditModalOpen}
        onFinish={handleUpdateCategory}
        modalProps={{
          destroyOnClose: true,
        }}
        initialValues={editingCategory || undefined}
      >
        <ProFormText
          name="key"
          label="Key (ID)"
          disabled
          tooltip="Key não pode ser alterada. Para mudar, delete e crie uma nova categoria."
        />
        <ProFormText
          name="label"
          label="Label"
          placeholder="Monitoramento"
          rules={[{ required: true, message: 'Label é obrigatório' }]}
          tooltip="Nome exibido na aba"
        />
        <ProFormText
          name="icon"
          label="Ícone (Emoji)"
          placeholder="📊"
          tooltip="Emoji que aparece na aba. Cole um emoji aqui."
        />
        <ProFormTextArea
          name="description"
          label="Descrição"
          placeholder="Campos relacionados a monitoramento e observabilidade"
          tooltip="Descrição do que a categoria contém"
        />
        <ProFormDigit
          name="order"
          label="Ordem"
          placeholder="10"
          min={1}
          max={999}
          tooltip="Ordem de exibição (menor número aparece primeiro)"
        />
        <ProForm.Item
          name="color"
          label="Cor"
          tooltip="Cor da tag (visual)"
        >
          <Select options={AVAILABLE_COLORS} />
        </ProForm.Item>
      </ModalForm>
    </>
  );
};

export default CategoryManagementModal;
