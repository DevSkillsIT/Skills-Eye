/**
 * Página de Tipos de Monitoramento
 *
 * Mostra tipos DINÂMICOS extraídos dos prometheus.yml de cada servidor.
 * Esta é uma página DEFINITIVA (não é teste!)
 *
 * FONTE DA VERDADE: prometheus.yml (não JSONs estáticos)
 */

import React, { useState, useEffect, useCallback } from 'react';
import { PageContainer, ProCard } from '@ant-design/pro-components';
import {
  Card,
  Tabs,
  Table,
  Tag,
  Badge,
  Alert,
  Spin,
  Button,
  Space,
  Descriptions,
  Row,
  Col,
  Statistic,
  Typography,
  Empty,
  Radio,
  Dropdown,
  Tooltip,
  type MenuProps,
} from 'antd';
import {
  ReloadOutlined,
  CloudServerOutlined,
  DatabaseOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  InfoCircleOutlined,
  ThunderboltOutlined,
  GlobalOutlined,
  ColumnHeightOutlined,
  SettingOutlined,
  SyncOutlined,
} from '@ant-design/icons';
import axios from 'axios';
import { ServerSelector, type Server } from '../components/ServerSelector';
import ColumnSelector, { type ColumnConfig } from '../components/ColumnSelector';
import { useServersContext } from '../contexts/ServersContext';
import ExtractionProgressModal, { type ServerStatus } from '../components/ExtractionProgressModal';

const API_URL = import.meta.env?.VITE_API_URL ?? 'http://localhost:5000/api/v1';
const { Title, Text, Paragraph } = Typography;

interface MonitoringType {
  id: string;
  display_name: string;
  category: string;
  job_name: string;
  exporter_type: string;
  module?: string;
  fields?: string[]; // ⚠️ Opcional: pode ser undefined quando vem do cache KV
  metrics_path: string;
  server?: string;
  servers?: string[];
}

interface CategoryData {
  category: string;
  display_name: string;
  types: MonitoringType[];
}

interface ServerResult {
  types: MonitoringType[];
  total: number;
  prometheus_file?: string;
  error?: string;
}

export default function MonitoringTypes() {
  // ✅ OTIMIZAÇÃO: Usar ServersContext ao invés de fazer request próprio
  const { servers, master, loading: serversLoading } = useServersContext();
  const [loading, setLoading] = useState(true);
  const [categories, setCategories] = useState<CategoryData[]>([]);
  const [serverData, setServerData] = useState<Record<string, ServerResult>>({});
  const [viewMode, setViewMode] = useState<'all' | 'specific'>('all');
  const [selectedServerId, setSelectedServerId] = useState<string>('ALL');
  const [selectedServerInfo, setSelectedServerInfo] = useState<Server | null>(null);
  const [totalTypes, setTotalTypes] = useState(0);
  const [totalServers, setTotalServers] = useState(0);
  const [serverJustChanged, setServerJustChanged] = useState(false);
  const [tableSize, setTableSize] = useState<'small' | 'middle' | 'large'>('middle');
  
  // Estado para modal de progresso
  const [progressModalVisible, setProgressModalVisible] = useState(false);
  const [extractionData, setExtractionData] = useState<{
    loading: boolean;
    fromCache: boolean;
    successfulServers: number;
    totalServers: number;
    serverStatus: ServerStatus[];
    totalTypes: number;
    error: string | null;
  }>({
    loading: false,
    fromCache: false,
    successfulServers: 0,
    totalServers: 0,
    serverStatus: [],
    totalTypes: 0,
    error: null,
  });

  // Configuração de colunas
  const [columnConfig, setColumnConfig] = useState<ColumnConfig[]>([
    { key: 'display_name', title: 'Nome', visible: true, width: 250 },
    { key: 'job_name', title: 'Job Name', visible: true, width: 200 },
    { key: 'exporter_type', title: 'Exporter Type', visible: true, width: 180 },
    { key: 'module', title: 'Módulo', visible: true, width: 120 },
    { key: 'fields', title: 'Campos Metadata', visible: true, width: 300 },
    { key: 'servers', title: 'Servidores', visible: true, width: 200 },
  ]);

  // ✅ OTIMIZAÇÃO: Usar ServersContext - não precisa mais fazer request próprio
  // Setar servidor master quando servidores carregarem do Context
  useEffect(() => {
    if (!serversLoading && servers.length > 0 && master) {
      // Se modo específico e nada selecionado, selecionar master
      if (viewMode === 'specific' && (!selectedServerId || selectedServerId === 'ALL')) {
        setSelectedServerId(master.id);
        setSelectedServerInfo(master);
      }
    }
  }, [serversLoading, servers, master, viewMode, selectedServerId]);

  const loadTypes = useCallback(async (forceRefresh: boolean = false, showModal: boolean = false) => {
    setLoading(true);
    
    // Atualizar estado do modal se necessário
    if (showModal) {
      setProgressModalVisible(true);
      setExtractionData(prev => ({ ...prev, loading: true, error: null }));
    }
    
    try {
      const response = await axios.get(`${API_URL}/monitoring-types-dynamic/from-prometheus`, {
        params: {
          server: viewMode === 'all' ? 'ALL' : (selectedServerInfo?.hostname || 'ALL'),
          force_refresh: forceRefresh
        },
        timeout: 60000, // 60s para permitir extração SSH
      });

      if (response.data.success) {
        setCategories(response.data.categories || []);
        setServerData(response.data.servers || {});
        setTotalTypes(response.data.total_types || 0);
        setTotalServers(response.data.total_servers || 0);
        
        // Atualizar dados do modal
        if (showModal) {
          setExtractionData({
            loading: false,
            fromCache: response.data.from_cache || false,
            successfulServers: response.data.successful_servers || 0,
            totalServers: response.data.total_servers || 0,
            serverStatus: (response.data.server_status || []).map((s: any) => ({
              hostname: s.hostname,
              success: s.success,
              from_cache: s.from_cache || false,
              files_count: s.files_count || 0,
              fields_count: s.fields_count || 0,
              error: s.error || null,
              duration_ms: s.duration_ms || 0,
            })),
            totalTypes: response.data.total_types || 0,
            error: null,
          });
        }
      }
    } catch (error: any) {
      console.error('Erro ao carregar tipos:', error);
      
      const errorMessage = error.code === 'ECONNABORTED'
        ? 'Timeout ao carregar tipos - verifique se o backend está respondendo'
        : error.response
        ? `Erro: ${error.response.status} - ${error.response.data.detail || error.message}`
        : `Erro ao carregar tipos: ${error.message}`;
      
      if (showModal) {
        setExtractionData(prev => ({
          ...prev,
          loading: false,
          error: errorMessage,
        }));
      } else {
        alert(errorMessage);
      }
    } finally {
      setLoading(false);
    }
  }, [viewMode, selectedServerInfo]);
  
  const handleForceRefresh = useCallback(async () => {
    await loadTypes(true, true);
  }, [loadTypes]);
  
  const handleReload = useCallback(async () => {
    await loadTypes(false, false);
  }, [loadTypes]);

  useEffect(() => {
    if (viewMode === 'all' || selectedServerInfo) {
      loadTypes(false, false); // Carregar do cache, sem mostrar modal
    }
  }, [viewMode, selectedServerInfo, loadTypes]);

  const handleServerChange = (serverId: string, server: Server) => {
    setSelectedServerId(serverId);
    setSelectedServerInfo(server);
    setServerJustChanged(true);
    setTimeout(() => setServerJustChanged(false), 2000);
  };

  const handleViewModeChange = (value: 'all' | 'specific') => {
    setViewMode(value);

    if (value === 'all') {
      setSelectedServerId('ALL');
      setSelectedServerInfo(null);
    } else {
      const masterServer = servers.find(s => s.type === 'master');
      if (masterServer) {
        setSelectedServerId(masterServer.id);
        setSelectedServerInfo(masterServer);
      }
    }

    setServerJustChanged(true);
    setTimeout(() => setServerJustChanged(false), 2000);
  };

  const serverList = Object.keys(serverData);
  const successServers = serverList.filter(s => !serverData[s].error);
  const failedServers = serverList.filter(s => serverData[s].error);

  // Colunas visíveis baseadas na configuração
  const visibleColumns = columnConfig.filter(col => col.visible);

  // Definição de todas as colunas
  const allColumns = [
    {
      key: 'display_name',
      title: 'Nome',
      dataIndex: 'display_name',
      width: 250,
      render: (text: string) => (
        <Space>
          <DatabaseOutlined style={{ color: '#1890ff' }} />
          <strong>{text}</strong>
        </Space>
      ),
    },
    {
      key: 'job_name',
      title: 'Job Name',
      dataIndex: 'job_name',
      width: 200,
      render: (text: string) => <Tag color="blue">{text}</Tag>,
    },
    {
      key: 'exporter_type',
      title: 'Exporter Type',
      dataIndex: 'exporter_type',
      width: 180,
      render: (text: string) => <Tag color="purple">{text}</Tag>,
    },
    {
      key: 'module',
      title: 'Módulo',
      dataIndex: 'module',
      width: 120,
      render: (text: string) => (text ? <Tag color="green">{text}</Tag> : <Text type="secondary">-</Text>),
    },
    {
      key: 'fields',
      title: 'Campos Metadata',
      dataIndex: 'fields',
      width: 300,
      render: (fields: string[] | undefined) => {
        // ⚠️ IMPORTANTE: fields pode ser undefined quando vem do cache KV
        // fields são apenas para display e não são salvos no KV
        if (!fields || !Array.isArray(fields) || fields.length === 0) {
          return <Text type="secondary">-</Text>;
        }
        
        const visibleFields = fields.slice(0, 4);
        const hiddenFields = fields.slice(4);

        return (
          <Space wrap>
            {visibleFields.map((field) => (
              <Tag key={field} color="cyan">
                {field}
              </Tag>
            ))}
            {hiddenFields.length > 0 && (
              <Tooltip
                title={
                  <Space wrap>
                    {hiddenFields.map((field) => (
                      <Tag key={field} color="cyan">
                        {field}
                      </Tag>
                    ))}
                  </Space>
                }
                placement="topLeft"
                overlayStyle={{ maxWidth: 500 }}
              >
                <Tag style={{ cursor: 'pointer' }} color="blue">
                  +{hiddenFields.length} mais
                </Tag>
              </Tooltip>
            )}
          </Space>
        );
      },
    },
    {
      key: 'servers',
      title: 'Servidores',
      dataIndex: 'servers',
      width: 200,
      render: (_: any, record: MonitoringType) => {
        const serverList = record.servers || (record.server ? [record.server] : []);
        return (
          <Space wrap>
            {serverList.map((srv: string) => (
              <Tag key={srv} icon={<CloudServerOutlined />} color="orange">
                {srv}
              </Tag>
            ))}
          </Space>
        );
      },
    },
  ];

  // Filtrar apenas colunas visíveis
  const tableColumns = allColumns.filter(col =>
    visibleColumns.some(vc => vc.key === col.key)
  );

  return (
    <PageContainer
      title="Tipos de Monitoramento"
      subTitle="Tipos extraídos DINAMICAMENTE dos arquivos prometheus.yml de cada servidor"
      extra={[
        <Tooltip
          key="reload-tooltip"
          title="Recarrega os dados do cache KV (rápido, sem conexão SSH)"
        >
          <Button
            key="reload"
            icon={<ReloadOutlined />}
            onClick={handleReload}
            loading={loading}
          >
            Recarregar
          </Button>
        </Tooltip>,
        <Tooltip
          key="refresh-tooltip"
          title="Força nova extração via SSH de todos os servidores Prometheus (pode demorar alguns segundos)"
        >
          <Button
            key="refresh"
            icon={<SyncOutlined />}
            onClick={handleForceRefresh}
            loading={loading}
            type="primary"
          >
            Atualizar
          </Button>
        </Tooltip>,
      ]}
    >
      {/* Alert explicativo */}
      <Alert
        message="ℹ️ Fonte da Verdade: Prometheus.yml"
        description={
          <div>
            <Paragraph>
              Os tipos de monitoramento são extraídos <strong>automaticamente</strong> dos jobs
              do arquivo <code>prometheus.yml</code> de cada servidor.
            </Paragraph>
            <Paragraph style={{ marginBottom: 0 }}>
              <strong>Para adicionar/remover tipos:</strong> Edite o prometheus.yml via página{' '}
              <a href="/prometheus-config">Prometheus Config</a> e depois clique em "Recarregar" aqui.
            </Paragraph>
          </div>
        }
        type="info"
        showIcon
        icon={<InfoCircleOutlined />}
        style={{ marginBottom: 16 }}
      />

      {/* Estatísticas Gerais */}
      {!loading && (
        <Row gutter={16} style={{ marginBottom: 16 }}>
          <Col span={6}>
            <Card>
              <Statistic
                title="Total de Tipos"
                value={totalTypes}
                prefix={<DatabaseOutlined />}
                valueStyle={{ color: '#1890ff' }}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic
                title="Categorias"
                value={categories.length}
                prefix={<ThunderboltOutlined />}
                valueStyle={{ color: '#52c41a' }}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic
                title="Servidores OK"
                value={successServers.length}
                prefix={<CheckCircleOutlined />}
                valueStyle={{ color: '#52c41a' }}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic
                title="Servidores Erro"
                value={failedServers.length}
                prefix={<CloseCircleOutlined />}
                valueStyle={{ color: failedServers.length > 0 ? '#ff4d4f' : '#d9d9d9' }}
              />
            </Card>
          </Col>
        </Row>
      )}

      {/* Alert mostrando servidor selecionado ou visualização de todos */}
      <Alert
        message={
          viewMode === 'all' ? (
            <span
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: 8,
                whiteSpace: 'nowrap',
                overflow: 'hidden',
                textOverflow: 'ellipsis',
              }}
            >
              <strong>Visualização:</strong>
              <span>Todos os Servidores</span>
              <Badge status="processing" text={`${totalServers} servidor(es)`} />
              <span>•</span>
              {loading ? (
                <span style={{ color: '#999' }}>
                  <Spin size="small" /> Carregando...
                </span>
              ) : (
                <span>
                  <strong>{totalTypes}</strong> tipo(s) únicos
                </span>
              )}
              {serverJustChanged && (
                <Tag color="success" icon={<CheckCircleOutlined />}>
                  Alterado!
                </Tag>
              )}
            </span>
          ) : selectedServerInfo ? (
            <span
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: 8,
                whiteSpace: 'nowrap',
                overflow: 'hidden',
                textOverflow: 'ellipsis',
              }}
            >
              <strong>Servidor:</strong>
              <span>{selectedServerInfo.display_name}</span>
              <Badge
                status={selectedServerInfo.type === 'master' ? 'success' : 'processing'}
                text={selectedServerInfo.type === 'master' ? 'Master' : 'Slave'}
              />
              <span>•</span>
              {loading ? (
                <span style={{ color: '#999' }}>
                  <Spin size="small" /> Carregando...
                </span>
              ) : (
                <span>
                  <strong>
                    {serverData[selectedServerInfo.hostname]?.total || 0}
                  </strong>{' '}
                  tipo(s)
                </span>
              )}
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
        type={
          serverJustChanged
            ? 'success'
            : (viewMode === 'all' || selectedServerInfo)
            ? 'info'
            : 'warning'
        }
        showIcon
        style={{
          marginBottom: 16,
          transition: 'all 0.5s ease',
          ...(serverJustChanged && {
            border: '2px solid #52c41a',
            boxShadow: '0 4px 12px rgba(82, 196, 26, 0.4)',
            backgroundColor: '#f6ffed',
          }),
        }}
      />

      {/* Controles de Visualização */}
      <ProCard title="Controles de Visualização" style={{ marginBottom: 16 }}>
        <Space direction="vertical" style={{ width: '100%' }}>
          <Space style={{ width: '100%', justifyContent: 'space-between' }}>
            {/* Modo de Visualização */}
            <Radio.Group
              value={viewMode}
              onChange={(e) => handleViewModeChange(e.target.value)}
              size="large"
            >
              <Radio.Button value="all">
                <GlobalOutlined /> Todos os Servidores
              </Radio.Button>
              <Radio.Button value="specific">
                <CloudServerOutlined /> Servidor Específico
              </Radio.Button>
            </Radio.Group>

            {/* Controles de Tabela */}
            <Space.Compact size="large">
              <Dropdown
                menu={{
                  items: [
                    { key: 'small', label: 'Compacto' },
                    { key: 'middle', label: 'Médio' },
                    { key: 'large', label: 'Grande' },
                  ],
                  onClick: ({ key }: { key: string }) => setTableSize(key as 'small' | 'middle' | 'large'),
                  selectedKeys: [tableSize],
                }}
              >
                <Button icon={<ColumnHeightOutlined />} size="large">
                  Densidade
                </Button>
              </Dropdown>
              <ColumnSelector
                columns={columnConfig}
                onChange={setColumnConfig}
                storageKey="monitoring-types-columns"
                buttonSize="large"
              />
            </Space.Compact>
          </Space>

          {/* ServerSelector - apenas quando modo específico */}
          {viewMode === 'specific' && (
            <ServerSelector
              value={selectedServerId}
              onChange={handleServerChange}
              style={{ width: '100%', maxWidth: 500 }}
              placeholder="Selecione o servidor Prometheus"
            />
          )}

          {/* Mostrar erros se houver */}
          {failedServers.length > 0 && (
            <Alert
              message={`${failedServers.length} servidor(es) com erro`}
              description={
                <ul style={{ marginBottom: 0 }}>
                  {failedServers.map((server) => (
                    <li key={server}>
                      <strong>{server}:</strong> {serverData[server].error}
                    </li>
                  ))}
                </ul>
              }
              type="error"
              showIcon
              style={{ marginTop: 8 }}
            />
          )}
        </Space>
      </ProCard>

      {/* Conteúdo Principal */}
      {loading ? (
        <Card>
          <Spin tip="Carregando tipos de monitoramento..." size="large">
            <div style={{ height: 200 }} />
          </Spin>
        </Card>
      ) : categories.length === 0 ? (
        <Card>
          <Empty
            description="Nenhum tipo de monitoramento encontrado"
            image={Empty.PRESENTED_IMAGE_SIMPLE}
          />
        </Card>
      ) : (
        <Tabs
          defaultActiveKey={categories[0]?.category}
          items={categories.map((category) => ({
            key: category.category,
            label: (
              <span>
                {category.display_name} <Badge count={category.types.length} />
              </span>
            ),
            children: (
              <Table<MonitoringType>
                dataSource={category.types}
                rowKey="id"
                size={tableSize}
                pagination={{ pageSize: 10 }}
                columns={tableColumns}
                expandable={{
                  expandedRowRender: (record) => (
                    <Descriptions bordered column={2} size="small">
                      <Descriptions.Item label="ID">{record.id}</Descriptions.Item>
                      <Descriptions.Item label="Categoria">{record.category}</Descriptions.Item>
                      <Descriptions.Item label="Exporter Type">{record.exporter_type}</Descriptions.Item>
                      <Descriptions.Item label="Módulo">{record.module || 'N/A'}</Descriptions.Item>
                      <Descriptions.Item label="Metrics Path">{record.metrics_path}</Descriptions.Item>
                      <Descriptions.Item label="Total Campos">{record.fields?.length || 0}</Descriptions.Item>
                      <Descriptions.Item label="Campos Metadata" span={2}>
                        <Space wrap>
                          {record.fields && record.fields.length > 0 ? (
                            record.fields.map((field) => (
                              <Tag key={field} color="geekblue">
                                {field}
                              </Tag>
                            ))
                          ) : (
                            <Text type="secondary">-</Text>
                          )}
                        </Space>
                      </Descriptions.Item>
                    </Descriptions>
                  ),
                }}
              />
            ),
          }))}
        />
      )}

      {/* Footer com instruções */}
      <Card style={{ marginTop: 16 }} type="inner" title="ℹ️ Como Funciona">
        <Paragraph>
          <strong>1. Editar Prometheus.yml:</strong> Use a página{' '}
          <a href="/prometheus-config">Prometheus Config</a> para adicionar/remover jobs no prometheus.yml
        </Paragraph>
        <Paragraph>
          <strong>2. Recarregar Tipos:</strong> Clique no botão "Recarregar" para carregar do cache ou "Atualizar" para forçar nova extração via SSH
        </Paragraph>
        <Paragraph style={{ marginBottom: 0 }}>
          <strong>3. Zero Configuração:</strong> Não é necessário editar JSONs ou reiniciar o backend!
        </Paragraph>
      </Card>
      
      {/* Modal de Progresso de Extração (COMPONENTE COMPARTILHADO) */}
      <ExtractionProgressModal
        visible={progressModalVisible}
        onClose={() => setProgressModalVisible(false)}
        onRefresh={handleForceRefresh}
        loading={extractionData.loading}
        fromCache={extractionData.fromCache}
        successfulServers={extractionData.successfulServers}
        totalServers={extractionData.totalServers}
        serverStatus={extractionData.serverStatus}
        totalFields={extractionData.totalTypes}
        error={extractionData.error}
      />
    </PageContainer>
  );
}
