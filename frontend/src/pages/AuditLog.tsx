import React, { useRef, useState } from 'react';
import {
  ProTable,
} from '@ant-design/pro-components';
import type { ActionType } from '@ant-design/pro-components';
import {
  Alert,
  Card,
  Tag,
  Space,
  Typography,
  Modal,
  Descriptions,
  Timeline,
  Button,
  DatePicker,
  Select,
} from 'antd';
import {
  HistoryOutlined,
  EyeOutlined,
  PlusCircleOutlined,
  EditOutlined,
  DeleteOutlined,
  FileTextOutlined,
} from '@ant-design/icons';
import { consulAPI } from '../services/api';

const { Title, Text, Paragraph } = Typography;
const { RangePicker } = DatePicker;

interface AuditEvent {
  timestamp: string;
  action: string;
  resource_type: string;
  resource_id: string;
  user: string;
  details?: string;
  metadata?: Record<string, any>;
}

type AuditColumn<T> = import('@ant-design/pro-components').ProColumns<T>;

const AuditLog: React.FC = () => {
  const actionRef = useRef<ActionType | null>(null);
  const [selectedEvent, setSelectedEvent] = useState<AuditEvent | null>(null);
  const [modalVisible, setModalVisible] = useState(false);
  const [dateRange, setDateRange] = useState<[string, string] | null>(null);
  const [actionFilter, setActionFilter] = useState<string | undefined>(undefined);
  const [resourceTypeFilter, setResourceTypeFilter] = useState<string | undefined>(undefined);

  const getActionIcon = (action: string) => {
    switch (action) {
      case 'create':
      case 'register':
        return <PlusCircleOutlined style={{ color: '#52c41a' }} />;
      case 'update':
        return <EditOutlined style={{ color: '#1890ff' }} />;
      case 'delete':
        return <DeleteOutlined style={{ color: '#ff4d4f' }} />;
      default:
        return <FileTextOutlined style={{ color: '#8c8c8c' }} />;
    }
  };

  const getActionColor = (action: string): string => {
    switch (action) {
      case 'create':
      case 'register':
        return 'success';
      case 'update':
        return 'processing';
      case 'delete':
        return 'error';
      default:
        return 'default';
    }
  };

  const getActionText = (action: string): string => {
    const actionMap: Record<string, string> = {
      create: 'Criado',
      update: 'Atualizado',
      delete: 'Deletado',
      register: 'Registrado',
      deregister: 'Desregistrado',
      migrate: 'Migrado',
    };
    return actionMap[action] || action;
  };

  const columns: AuditColumn<AuditEvent>[] = [
    {
      title: 'Timestamp',
      dataIndex: 'timestamp',
      width: 180,
      valueType: 'dateTime',
      render: (_, record) => new Date(record.timestamp).toLocaleString('pt-BR'),
      sorter: (a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime(),
      defaultSortOrder: 'descend',
    },
    {
      title: 'Acao',
      dataIndex: 'action',
      width: 120,
      filters: true,
      onFilter: true,
      valueEnum: {
        create: { text: 'Criado', status: 'Success' },
        update: { text: 'Atualizado', status: 'Processing' },
        delete: { text: 'Deletado', status: 'Error' },
        register: { text: 'Registrado', status: 'Success' },
        deregister: { text: 'Desregistrado', status: 'Warning' },
        migrate: { text: 'Migrado', status: 'Default' },
      },
      render: (_, record) => {
        const action = typeof record.action === 'object' ? String(record.action) : record.action;
        return (
          <Space>
            {getActionIcon(action)}
            <Tag color={getActionColor(action)}>{getActionText(action)}</Tag>
          </Space>
        );
      },
    },
    {
      title: 'Tipo de Recurso',
      dataIndex: 'resource_type',
      width: 150,
      filters: true,
      onFilter: true,
      valueEnum: {
        preset: { text: 'Preset', status: 'Default' },
        blackbox_target: { text: 'Blackbox Target', status: 'Default' },
        blackbox_group: { text: 'Blackbox Group', status: 'Default' },
        service: { text: 'Service', status: 'Default' },
        kv: { text: 'KV Store', status: 'Default' },
      },
      render: (_, record) => {
        const typeMap: Record<string, string> = {
          preset: 'Preset',
          blackbox_target: 'Blackbox Target',
          blackbox_group: 'Blackbox Group',
          service: 'Service',
          kv: 'KV Store',
        };
        let resourceType = record.resource_type;
        if (typeof resourceType === 'object' && resourceType !== null) {
          try {
            resourceType = JSON.stringify(resourceType);
          } catch {
            resourceType = String(resourceType);
          }
        }
        return <Tag>{typeMap[resourceType] || resourceType}</Tag>;
      },
    },
    {
      title: 'ID do Recurso',
      dataIndex: 'resource_id',
      ellipsis: true,
      copyable: true,
      render: (text) => <Text code>{String(text || '')}</Text>,
    },
    {
      title: 'Usuario',
      dataIndex: 'user',
      width: 150,
      render: (text) => {
        let userStr = text || 'system';
        if (typeof text === 'object' && text !== null) {
          try {
            userStr = JSON.stringify(text);
          } catch {
            userStr = String(text);
          }
        }
        return <Tag icon={<FileTextOutlined />}>{String(userStr)}</Tag>;
      },
    },
    {
      title: 'Detalhes',
      dataIndex: 'details',
      ellipsis: true,
      render: (text) => {
        if (!text) return <Text type="secondary">-</Text>;
        let detailsStr = text;
        if (typeof text === 'object' && text !== null) {
          try {
            detailsStr = JSON.stringify(text);
          } catch {
            detailsStr = String(text);
          }
        }
        return String(detailsStr);
      },
    },
    {
      title: 'Acoes',
      valueType: 'option',
      width: 120,
      fixed: 'right',
      render: (_, record) => [
        <Button
          key="view"
          type="link"
          size="small"
          icon={<EyeOutlined />}
          onClick={() => handleViewEvent(record)}
        >
          Ver Detalhes
        </Button>,
      ],
    },
  ];

  const handleViewEvent = (event: AuditEvent) => {
    setSelectedEvent(event);
    setModalVisible(true);
  };

  const handleDateRangeChange = (_dates: any, dateStrings: [string, string]) => {
    if (_dates) {
      setDateRange([dateStrings[0], dateStrings[1]]);
    } else {
      setDateRange(null);
    }
    actionRef.current?.reload();
  };

  return (
    <div style={{ padding: 24 }}>
      <Card
        title={
          <Space>
            <HistoryOutlined style={{ fontSize: 24 }} />
            <Title level={2} style={{ margin: 0 }}>
              Audit Log
            </Title>
          </Space>
        }
      >
        <Paragraph>
          Historico completo de todas as operacoes realizadas no sistema. Todas as acoes sao
          registradas para auditoria e rastreabilidade.
        </Paragraph>
      </Card>

      <Alert
        message="Funcionalidade em desenvolvimento"
        description="O endpoint de auditoria ainda não foi implementado no backend. Esta página estará disponível quando o endpoint /api/v1/kv/audit/events for criado."
        type="info"
        showIcon
        style={{ marginTop: 16 }}
      />

      <div style={{ marginTop: 16 }}>
        <ProTable<AuditEvent>
          columns={columns}
          actionRef={actionRef}
          request={async (params) => {
            // Endpoint /api/v1/kv/audit/events não existe no backend
            // TODO: Implementar endpoint no backend quando necessário
            return { data: [], success: true, total: 0 };

            /* try {
              const response = await consulAPI.getAuditEvents({
                start_date: dateRange?.[0],
                end_date: dateRange?.[1],
                action: actionFilter,
                resource_type: resourceTypeFilter,
                limit: params.pageSize || 20,
              });

              return {
                data: response.data.events || [],
                success: true,
                total: response.data.total || 0,
              };
            } catch (error) {
              return { data: [], success: false, total: 0 };
            } */
          }}
          rowKey={(record) => `${record.timestamp}-${record.resource_id}`}
          search={false}
          dateFormatter="string"
          toolbar={{
            title: 'Historico de Atividades',
            filter: (
              <Space>
                <Text>Periodo:</Text>
                <RangePicker
                  onChange={handleDateRangeChange}
                  format="YYYY-MM-DD"
                  placeholder={['Data Inicial', 'Data Final']}
                  style={{ width: 280 }}
                />
                <Select
                  placeholder="Filtrar por acao"
                  allowClear
                  style={{ width: 150 }}
                  value={actionFilter}
                  onChange={(value) => {
                    setActionFilter(value);
                    actionRef.current?.reload();
                  }}
                  options={[
                    { label: 'Criado', value: 'create' },
                    { label: 'Atualizado', value: 'update' },
                    { label: 'Deletado', value: 'delete' },
                    { label: 'Registrado', value: 'register' },
                    { label: 'Desregistrado', value: 'deregister' },
                  ]}
                />
                <Select
                  placeholder="Tipo de recurso"
                  allowClear
                  style={{ width: 180 }}
                  value={resourceTypeFilter}
                  onChange={(value) => {
                    setResourceTypeFilter(value);
                    actionRef.current?.reload();
                  }}
                  options={[
                    { label: 'Preset', value: 'preset' },
                    { label: 'Blackbox Target', value: 'blackbox_target' },
                    { label: 'Blackbox Group', value: 'blackbox_group' },
                    { label: 'Service', value: 'service' },
                    { label: 'KV Store', value: 'kv' },
                  ]}
                />
              </Space>
            ),
          }}
          pagination={{
            defaultPageSize: 20,
            showSizeChanger: true,
            showTotal: (total) => `Total de ${total} eventos`,
          }}
        />
      </div>

      {/* Modal de Detalhes do Evento */}
      <Modal
        title="Detalhes do Evento de Auditoria"
        open={modalVisible}
        onCancel={() => {
          setModalVisible(false);
          setSelectedEvent(null);
        }}
        footer={[
          <Button
            key="close"
            type="primary"
            onClick={() => {
              setModalVisible(false);
              setSelectedEvent(null);
            }}
          >
            Fechar
          </Button>,
        ]}
        width={800}
      >
        {selectedEvent && (
          <>
            <Descriptions column={2} bordered>
              <Descriptions.Item label="Timestamp" span={2}>
                {new Date(selectedEvent.timestamp).toLocaleString('pt-BR', {
                  dateStyle: 'full',
                  timeStyle: 'long',
                })}
              </Descriptions.Item>
              <Descriptions.Item label="Acao">
                <Space>
                  {getActionIcon(selectedEvent.action)}
                  <Tag color={getActionColor(selectedEvent.action)}>
                    {getActionText(selectedEvent.action)}
                  </Tag>
                </Space>
              </Descriptions.Item>
              <Descriptions.Item label="Tipo de Recurso">
                <Tag>{selectedEvent.resource_type}</Tag>
              </Descriptions.Item>
              <Descriptions.Item label="ID do Recurso" span={2}>
                <Text code copyable>
                  {selectedEvent.resource_id}
                </Text>
              </Descriptions.Item>
              <Descriptions.Item label="Usuario" span={2}>
                <Tag icon={<FileTextOutlined />}>{selectedEvent.user || 'system'}</Tag>
              </Descriptions.Item>
              {selectedEvent.details && (
                <Descriptions.Item label="Detalhes" span={2}>
                  {selectedEvent.details}
                </Descriptions.Item>
              )}
            </Descriptions>

            {selectedEvent.metadata && Object.keys(selectedEvent.metadata).length > 0 && (
              <Card
                type="inner"
                title="Metadata Adicional"
                style={{ marginTop: 16 }}
                size="small"
              >
                <pre
                  style={{
                    background: '#f5f5f5',
                    padding: 12,
                    borderRadius: 4,
                    overflow: 'auto',
                    margin: 0,
                    fontFamily: 'Monaco, Menlo, monospace',
                    fontSize: 13,
                  }}
                >
                  {JSON.stringify(selectedEvent.metadata, null, 2)}
                </pre>
              </Card>
            )}

            {/* Timeline visual */}
            <Card
              type="inner"
              title="Linha do Tempo"
              style={{ marginTop: 16 }}
              size="small"
            >
              <Timeline
                items={[
                  {
                    color: getActionColor(selectedEvent.action),
                    children: (
                      <div>
                        <Text strong>
                          {getActionText(selectedEvent.action)} - {selectedEvent.resource_type}
                        </Text>
                        <br />
                        <Text type="secondary">
                          {new Date(selectedEvent.timestamp).toLocaleString('pt-BR')}
                        </Text>
                        <br />
                        <Text>Por: {selectedEvent.user || 'system'}</Text>
                        {selectedEvent.details && (
                          <>
                            <br />
                            <Text italic>{selectedEvent.details}</Text>
                          </>
                        )}
                      </div>
                    ),
                  },
                ]}
              />
            </Card>
          </>
        )}
      </Modal>
    </div>
  );
};

export default AuditLog;





