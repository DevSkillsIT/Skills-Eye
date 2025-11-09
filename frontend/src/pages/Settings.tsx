import React, { useEffect, useState, useRef, useCallback } from 'react';
import { useConsulDelete } from '../hooks/useConsulDelete';
import {
  PageContainer,
  ProCard,
  ProDescriptions,
  ProTable,
  ModalForm,
  ProFormText,
  ProFormSwitch,
  ProFormSelect,
  ProFormDigit,
  ProFormTextArea,
} from '@ant-design/pro-components';
import type { ActionType, ProColumns } from '@ant-design/pro-components';
import {
  Alert,
  App,
  Badge,
  Button,
  Divider,
  Space,
  Spin,
  Skeleton,
  Tag,
  Tabs,
  Typography,
  Popconfirm,
  Tooltip,
} from 'antd';
import {
  ReloadOutlined,
  CheckCircleOutlined,
  WarningOutlined,
  InfoCircleOutlined,
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  SyncOutlined,
} from '@ant-design/icons';
import ResizableTitle from '../components/ResizableTitle';

const { Text, Paragraph } = Typography;

interface NamingConfig {
  naming_strategy: 'option1' | 'option2';
  suffix_enabled: boolean;
  default_site: string;
  sites?: Site[];
}

interface PrometheusServer {
  hostname: string;
  port: number;
  external_labels: Record<string, string>;
  external_labels_count: number;
  status: 'success' | 'error';
  error?: string;
}

interface Site {
  code: string;
  name: string;
  is_default: boolean;
  color?: string;
  prometheus_host?: string;
  prometheus_port?: number;
}

const Settings: React.FC = () => {
  const { message } = App.useApp();
  const [loading, setLoading] = useState(false);
  const [config, setConfig] = useState<NamingConfig | null>(null);
  const [lastSync, setLastSync] = useState<Date | null>(null);
  const [createModalOpen, setCreateModalOpen] = useState(false);
  const [editModalOpen, setEditModalOpen] = useState(false);
  const [editingSite, setEditingSite] = useState<Site | null>(null);
  const [prometheusServers, setPrometheusServers] = useState<PrometheusServer[]>([]);
  const [loadingServers, setLoadingServers] = useState(false);
  const tableRef = useRef<ActionType>();
  const [columnWidths, setColumnWidths] = useState<Record<string, number>>({});

  // Callback para redimensionar colunas
  const handleResize = useCallback(
    (columnKey: string) =>
      (_: React.SyntheticEvent, { size }: { size: { width: number } }) => {
        setColumnWidths((prev) => ({ ...prev, [columnKey]: size.width }));
      },
    [],
  );

  // Hook para DELETE de sites
  const { deleteResource } = useConsulDelete({
    deleteFn: async (payload: any) => {
      const response = await fetch(`/api/v1/settings/sites/${payload.site_code}`, {
        method: 'DELETE',
      });
      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Erro ao remover site');
      }
      return response.json();
    },
    successMessage: 'Site removido com sucesso',
    errorMessage: 'Erro ao remover site',
    onSuccess: () => {
      loadConfig();
      tableRef.current?.reload();
    },
  });

  const loadConfig = async () => {
    setLoading(true);
    try {
      const response = await fetch('/api/v1/settings/naming-config');
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
      const data = await response.json();
      setConfig(data);
      setLastSync(new Date());
      message.success('Configurações carregadas com sucesso');
    } catch (error) {
      console.error('[Settings] Erro ao carregar configurações:', error);
      message.error(`Erro ao carregar configurações: ${error}`);
    } finally {
      setLoading(false);
    }
  };

  const fetchPrometheusServers = async () => {
    setLoadingServers(true);
    try {
      // OTIMIZAÇÃO: Não faz SSH! Apenas busca lista de servidores do .env (rápido)
      const serversResponse = await fetch('/api/v1/metadata-fields/servers');

      if (!serversResponse.ok) {
        throw new Error(`Erro ao buscar servidores: ${serversResponse.statusText}`);
      }

      const serversData = await serversResponse.json();
      const serverList = serversData.servers || [];

      if (serverList.length === 0) {
        message.warning('Nenhum servidor Prometheus configurado no .env');
        setPrometheusServers([]);
        return;
      }

      // OTIMIZAÇÃO: NÃO faz SSH para buscar external_labels!
      // External labels devem ser extraídos via MetadataFields primeiro
      // Aqui apenas mostramos aviso se não estiverem disponíveis
      console.log('[Settings] Servidores carregados (sem SSH):', serverList);
      setPrometheusServers(serverList.map((server: any) => ({
        hostname: server.hostname,
        port: server.port,
        external_labels: server.external_labels || {},  // Se existir no KV/cache
        external_labels_count: Object.keys(server.external_labels || {}).length,
        status: Object.keys(server.external_labels || {}).length > 0 ? 'success' : 'pending'
      })));

    } catch (error: any) {
      console.error('[Settings] Erro ao carregar servidores:', error);
      message.error(`Erro: ${error.message}`);
      setPrometheusServers([]);
    } finally {
      setLoadingServers(false);
    }
  };

  useEffect(() => {
    loadConfig();
    fetchPrometheusServers();  // Buscar lista de servidores (SEM SSH, apenas .env + cache)
  }, []);

  // Helper: Buscar external_labels para um prometheus_host específico
  const getExternalLabelsForHost = (prometheus_host: string | undefined): Record<string, string> => {
    if (!prometheus_host) return {};
    const server = prometheusServers.find(s => s.hostname === prometheus_host);
    return server?.external_labels || {};
  };

  // ============================================================================
  // CRUD DE SITES
  // ============================================================================

  const handleCreateSite = async (values: Site) => {
    try {
      const response = await fetch('/api/v1/settings/sites', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(values),
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Erro ao criar site');
      }

      message.success('Site criado com sucesso');
      setCreateModalOpen(false);
      loadConfig();
      tableRef.current?.reload();
      return true;
    } catch (error: any) {
      message.error(`Erro: ${error.message}`);
      return false;
    }
  };

  const handleUpdateSite = async (values: Site) => {
    if (!editingSite) return false;

    try {
      const response = await fetch(`/api/v1/settings/sites/${editingSite.code}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(values),
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Erro ao atualizar site');
      }

      message.success('Site atualizado com sucesso');
      setEditModalOpen(false);
      setEditingSite(null);
      loadConfig();
      tableRef.current?.reload();
      return true;
    } catch (error: any) {
      message.error(`Erro: ${error.message}`);
      return false;
    }
  };

  /**
   * Deleta um site usando o hook useConsulDelete
   * Usa APENAS dados do record - ZERO valores hardcoded
   */
  const handleDeleteSite = async (code: string) => {
    await deleteResource({ service_id: code, site_code: code } as any);
  };

  /**
   * Auto-preenche prometheus_host dos sites baseado nos external_labels
   * Mapeia site.code -> servidor com external_labels.site == site.code
   */
  const handleAutoFillPrometheusHosts = async () => {
    if (prometheusServers.length === 0) {
      message.warning('Nenhum servidor Prometheus encontrado. Execute "Sincronizar com Prometheus" primeiro.');
      return;
    }

    if (!config?.sites || config.sites.length === 0) {
      message.warning('Nenhum site cadastrado.');
      return;
    }

    setLoadingServers(true);
    let updated = 0;
    let errors = 0;

    try {
      for (const site of config.sites) {
        // Buscar servidor que tem external_labels.site == site.code
        const matchingServer = prometheusServers.find(
          server => server.external_labels?.site?.toLowerCase() === site.code.toLowerCase()
        );

        if (matchingServer) {
          try {
            // Atualizar site com prometheus_host
            const response = await fetch(`/api/v1/settings/sites/${site.code}`, {
              method: 'PUT',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({
                ...site,
                prometheus_host: matchingServer.hostname,
                prometheus_port: matchingServer.port || 9090,
              }),
            });

            if (response.ok) {
              updated++;
              console.log(`[AutoFill] ${site.code} -> ${matchingServer.hostname}`);
            } else {
              errors++;
            }
          } catch (error) {
            console.error(`[AutoFill] Erro ao atualizar ${site.code}:`, error);
            errors++;
          }
        } else {
          console.log(`[AutoFill] Nenhum servidor encontrado para site "${site.code}"`);
        }
      }

      if (updated > 0) {
        message.success(`${updated} site(s) atualizado(s) com prometheus_host`);
        loadConfig();
        tableRef.current?.reload();
      } else {
        message.info('Nenhum site foi atualizado (códigos não batem com external_labels.site)');
      }

      if (errors > 0) {
        message.error(`${errors} erro(s) ao atualizar sites`);
      }
    } catch (error) {
      console.error('[AutoFill] Erro geral:', error);
      message.error('Erro ao auto-preencher prometheus_host');
    } finally {
      setLoadingServers(false);
    }
  };

  // External labels são buscados AUTOMATICAMENTE no loadConfig()
  // NÃO precisa de função separada de sync manual

  // ============================================================================
  // RENDER HELPERS
  // ============================================================================

  const renderNamingStrategyExplanation = () => {
    if (!config) return null;

    if (config.naming_strategy === 'option2') {
      return (
        <Alert
          type="info"
          showIcon
          icon={<InfoCircleOutlined />}
          message="Estratégia Ativa: Opção 2 (Nomes diferentes por site)"
          description={
            <div>
              <Paragraph>
                <Text strong>Comportamento:</Text> Serviços em sites diferentes do padrão ({config.default_site}) recebem sufixo automático.
              </Paragraph>
              <Paragraph>
                <Text strong>Exemplos:</Text>
                <ul style={{ marginBottom: 0 }}>
                  <li>
                    <Text code>selfnode_exporter</Text> + <Tag color="blue">site=palmas</Tag> →{' '}
                    <Text code strong>selfnode_exporter</Text> (sem sufixo, é o default)
                  </li>
                  <li>
                    <Text code>selfnode_exporter</Text> + <Tag color="green">site=rio</Tag> →{' '}
                    <Text code strong>selfnode_exporter_rio</Text>
                  </li>
                  <li>
                    <Text code>blackbox_exporter</Text> + <Tag color="orange">site=dtc</Tag> →{' '}
                    <Text code strong>blackbox_exporter_dtc</Text>
                  </li>
                </ul>
              </Paragraph>
            </div>
          }
        />
      );
    } else {
      return (
        <Alert
          type="warning"
          showIcon
          icon={<WarningOutlined />}
          message="Estratégia Ativa: Opção 1 (Mesmo nome + filtros)"
          description={
            <div>
              <Paragraph>
                <Text strong>Comportamento:</Text> Todos os serviços mantêm o mesmo nome, independente do site.
                Filtragem deve ser feita via <Text code>relabel_configs</Text> no Prometheus.
              </Paragraph>
              <Paragraph>
                <Text strong>Exemplo:</Text> Todos os <Text code>selfnode_exporter</Text> têm o mesmo nome,
                use metadata <Text code>site</Text> para distinguir.
              </Paragraph>
            </div>
          }
        />
      );
    }
  };

  // Aplicar larguras redimensionáveis nas colunas
  const applyResizableWidth = (col: any, key: string) => {
    const width = columnWidths[key] || col.width;
    return {
      ...col,
      width,
      onHeaderCell: () => ({
        width,
        onResize: handleResize(key),
      }),
    };
  };

  return (
    <PageContainer
      title="Configurações do Sistema"
    >
      <Space direction="vertical" size="large" style={{ width: '100%' }}>
        {/* Status de Sincronização - Linha única */}
        {loading ? (
          <Alert
            type="info"
            showIcon
            message="Carregando configurações do backend..."
            banner
          />
        ) : config ? (
          <Alert
            type="success"
            showIcon
            message={
              <>
                Backend sincronizado • Última atualização: <Text strong>{lastSync?.toLocaleString('pt-BR')}</Text>
              </>
            }
            banner
            closable
          />
        ) : (
          <Alert
            type="error"
            showIcon
            message="Erro ao carregar configurações. Verifique se o backend está rodando."
            banner
          />
        )}

        {/* ABAS: Gerenciar Sites + External Labels */}
        {loading || !config ? (
          <ProCard bordered>
            <Skeleton active paragraph={{ rows: 12 }} />
          </ProCard>
        ) : (
          <ProCard bordered>
            <Tabs
              defaultActiveKey="sites"
              items={[
              {
                key: 'sites',
                label: 'Gerenciar Sites',
                children: config && config.sites ? (
                  <div style={{ padding: '16px 0' }}>
                    <div style={{ marginBottom: 16, display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
                      <Button
                        icon={<SyncOutlined />}
                        onClick={handleAutoFillPrometheusHosts}
                        loading={loadingServers}
                        title="Preenche automaticamente prometheus_host dos sites baseado nos external_labels"
                      >
                        Auto-preencher Prometheus Hosts
                      </Button>
                      <Button
                        type="primary"
                        icon={<PlusOutlined />}
                        onClick={() => setCreateModalOpen(true)}
                      >
                        Adicionar Site
                      </Button>
                    </div>
                    <ProTable<Site>
              actionRef={tableRef}
              columns={[
                applyResizableWidth({
                  title: 'Código',
                  dataIndex: 'code',
                  width: 100,
                  render: (_, record) => (
                    <Tag color={record.color || 'default'}>{record.code.toUpperCase()}</Tag>
                  ),
                }, 'code'),
                applyResizableWidth({
                  title: 'Nome',
                  dataIndex: 'name',
                  width: 200,
                  ellipsis: true,
                }, 'name'),
                applyResizableWidth({
                  title: 'Site Padrão',
                  dataIndex: 'is_default',
                  width: 150,
                  render: (_, record) => (
                    record.is_default ? (
                      <Badge status="success" text="Sim (sem sufixo)" />
                    ) : (
                      <Badge status="default" text="Não" />
                    )
                  ),
                }, 'is_default'),
                applyResizableWidth({
                  title: 'Cor do Badge',
                  dataIndex: 'color',
                  width: 120,
                  render: (_, record) => (
                    <Tag color={record.color || 'default'}>
                      {record.color || 'default'}
                    </Tag>
                  ),
                }, 'color'),
                applyResizableWidth({
                  title: 'Prometheus',
                  dataIndex: 'prometheus_host',
                  width: 200,
                  ellipsis: true,
                  render: (_, record) => {
                    if (!record.prometheus_host) {
                      return <Text type="secondary">-</Text>;
                    }
                    const port = record.prometheus_port || 9090;
                    return (
                      <Text code style={{ fontSize: '12px' }}>
                        {record.prometheus_host}:{port}
                      </Text>
                    );
                  },
                }, 'prometheus_host'),
                applyResizableWidth({
                  title: 'Site',
                  dataIndex: 'site',
                  width: 120,
                  render: (_, record) => {
                    const labels = getExternalLabelsForHost(record.prometheus_host);
                    return labels.site ? <Tag color="blue">{labels.site}</Tag> : <Text type="secondary">-</Text>;
                  },
                }, 'site'),
                applyResizableWidth({
                  title: 'Datacenter',
                  dataIndex: 'datacenter',
                  width: 140,
                  ellipsis: true,
                  render: (_, record) => {
                    const labels = getExternalLabelsForHost(record.prometheus_host);
                    return labels.datacenter ? <Tag color="green">{labels.datacenter}</Tag> : <Text type="secondary">-</Text>;
                  },
                }, 'datacenter'),
                applyResizableWidth({
                  title: 'Cluster',
                  dataIndex: 'cluster',
                  width: 140,
                  ellipsis: true,
                  render: (_, record) => {
                    const labels = getExternalLabelsForHost(record.prometheus_host);
                    return labels.cluster ? <Tag color="purple">{labels.cluster}</Tag> : <Text type="secondary">-</Text>;
                  },
                }, 'cluster'),
                applyResizableWidth({
                  title: 'Environment',
                  dataIndex: 'environment',
                  width: 130,
                  render: (_, record) => {
                    const labels = getExternalLabelsForHost(record.prometheus_host);
                    return labels.environment ? <Tag color="orange">{labels.environment}</Tag> : <Text type="secondary">-</Text>;
                  },
                }, 'environment'),
                applyResizableWidth({
                  title: 'Ações',
                  width: 120,
                  valueType: 'option',
                  render: (_, record) => [
                    <Button
                      key="edit"
                      type="link"
                      icon={<EditOutlined />}
                      onClick={() => {
                        setEditingSite(record);
                        setEditModalOpen(true);
                      }}
                    >
                      Editar
                    </Button>,
                    <Popconfirm
                      key="delete"
                      title="Remover site"
                      description={`Tem certeza que deseja remover o site "${record.name}"?`}
                      onConfirm={() => handleDeleteSite(record.code)}
                      okText="Sim"
                      cancelText="Não"
                    >
                      <Button
                        type="link"
                        danger
                        icon={<DeleteOutlined />}
                      >
                        Remover
                      </Button>
                    </Popconfirm>,
                  ],
                }, 'actions'),
              ]}
              dataSource={config.sites}
              rowKey="code"
              search={false}
              pagination={false}
              toolBarRender={false}
              scroll={{ x: 1600 }}
              components={{
                header: {
                  cell: ResizableTitle,
                },
              }}
            />
            <Alert
              type="info"
              showIcon
              message="Informações Importantes"
              description={
                <div>
                  <p>• Adicione ou remova sites conforme sua infraestrutura cresce</p>
                  <p>• O site marcado como padrão não receberá sufixo nos nomes de serviço</p>
                  <p>• <strong>Colunas External Labels:</strong> As colunas Site, Datacenter, Cluster e Environment mostram os external_labels configurados no prometheus.yml de cada servidor</p>
                  <p>• <strong>Atualização Automática:</strong> Os external_labels são buscados automaticamente ao carregar a página</p>
                </div>
              }
              style={{ marginTop: 16 }}
            />
                  </div>
                ) : null,
              },
            {
              key: 'external-labels',
              label: 'External Labels',
              children: (
                <div style={{ padding: '16px 0' }}>
                  {loadingServers ? (
                    <Skeleton active paragraph={{ rows: 6 }} />
                  ) : prometheusServers.length === 0 ? (
            <Alert
              type="warning"
              showIcon
              icon={<InfoCircleOutlined />}
              message="Dados não disponíveis - Sincronização necessária"
              description={
                <div>
                  <Paragraph>
                    <Text strong>Os external_labels ainda não foram extraídos do Prometheus.</Text>
                  </Paragraph>
                  <Paragraph>
                    Para visualizar os external_labels dos servidores:
                  </Paragraph>
                  <ol style={{ marginBottom: 0 }}>
                    <li>Vá para a página <Text strong code>MetadataFields</Text></li>
                    <li>Clique no botão <Text strong>"Sincronizar com Prometheus"</Text></li>
                    <li>Aguarde a extração dos campos via SSH</li>
                    <li>Volte para esta página e clique em <Text strong>"Atualizar"</Text></li>
                  </ol>
                </div>
              }
            />
          ) : (
            <>
              <Alert
                type="info"
                showIcon
                message="O que são External Labels?"
                description={
                  <div>
                    <p><strong>External labels</strong> são labels globais configurados em <code>global.external_labels</code> do prometheus.yml</p>
                    <p>São aplicados automaticamente a <strong>TODAS as métricas coletadas</strong> pelo Prometheus para identificar qual servidor/site coletou a métrica</p>
                    <p><strong>IMPORTANTE:</strong> Estes NÃO são campos para cadastrar em serviços! São globais do servidor.</p>
                  </div>
                }
                style={{ marginBottom: 16 }}
              />

              <Space direction="vertical" size="middle" style={{ width: '100%' }}>
                {prometheusServers.map((server, index) => (
                  <ProCard
                    key={index}
                    type="inner"
                    title={
                      <Space>
                        <Badge status={server.status === 'success' ? 'success' : 'error'} />
                        <Text strong>{server.hostname}:{server.port}</Text>
                      </Space>
                    }
                  >
                    {server.status === 'error' ? (
                      <Alert
                        type="error"
                        showIcon
                        message="Erro ao buscar external_labels"
                        description={server.error}
                      />
                    ) : Object.keys(server.external_labels).length === 0 ? (
                      <Alert
                        type="warning"
                        message="Nenhum external_label configurado neste servidor"
                      />
                    ) : (
                      <ProDescriptions
                        column={2}
                        size="small"
                        bordered
                      >
                        {Object.entries(server.external_labels).map(([key, value]) => (
                          <ProDescriptions.Item
                            key={key}
                            label={<Text strong>{key}</Text>}
                          >
                            <Tag color="blue">{value}</Tag>
                          </ProDescriptions.Item>
                        ))}
                      </ProDescriptions>
                    )}
                  </ProCard>
                ))}
              </Space>
            </>
          )}
                </div>
              ),
            },
          ]}
            />
          </ProCard>
        )}

        {/* CARD: Naming Strategy Multi-Site */}
        {loading || !config ? (
          <ProCard
            title="Naming Strategy Multi-Site"
            bordered
            headerBordered
          >
            <Skeleton active paragraph={{ rows: 6 }} />
          </ProCard>
        ) : (
          <ProCard
            title="Naming Strategy Multi-Site"
            bordered
            headerBordered
            extra={
              <Badge
                status={config.suffix_enabled ? 'processing' : 'default'}
                text={config.suffix_enabled ? 'Ativo' : 'Desativado'}
              />
            }
          >
            <Space direction="vertical" size="large" style={{ width: '100%' }}>
              <ProDescriptions
                column={2}
                bordered
                size="small"
              >
                <ProDescriptions.Item label="Estratégia" span={1}>
                  <Tag color={config.naming_strategy === 'option2' ? 'blue' : 'orange'}>
                    {config.naming_strategy === 'option2' ? 'Opção 2 - Nomes diferentes' : 'Opção 1 - Mesmo nome + filtros'}
                  </Tag>
                </ProDescriptions.Item>
                <ProDescriptions.Item label="Sufixo Automático" span={1}>
                  <Badge
                    status={config.suffix_enabled ? 'success' : 'default'}
                    text={config.suffix_enabled ? 'Habilitado' : 'Desabilitado'}
                  />
                </ProDescriptions.Item>
                <ProDescriptions.Item label="Site Padrão (sem sufixo)" span={2}>
                  <Tag color="blue">{config.default_site.toUpperCase()}</Tag>
                  <Text type="secondary"> (serviços neste site não recebem sufixo)</Text>
                </ProDescriptions.Item>
              </ProDescriptions>

              <Divider orientation="left">Como Funciona</Divider>
              {renderNamingStrategyExplanation()}

              <Divider orientation="left">Configuração no Backend</Divider>
              <Alert
                type="info"
                showIcon
                message="Arquivo de Configuração"
                description={
                  <div>
                    <Paragraph>
                      Estas configurações são carregadas do arquivo <Text code>backend/.env</Text>:
                    </Paragraph>
                    <pre style={{
                      background: '#f5f5f5',
                      padding: '12px',
                      borderRadius: '4px',
                      fontSize: '12px',
                    }}>
{`NAMING_STRATEGY=${config.naming_strategy}
SITE_SUFFIX_ENABLED=${config.suffix_enabled}
DEFAULT_SITE=${config.default_site}`}
                    </pre>
                    <Paragraph type="secondary" style={{ marginBottom: 0 }}>
                      Para alterar, edite o arquivo .env e reinicie o backend.
                    </Paragraph>
                  </div>
                }
              />
            </Space>
          </ProCard>
        )}

        {/* CARD: Informações Adicionais */}
        {loading || !config ? (
          <ProCard
            title="Páginas Afetadas"
            bordered
            headerBordered
          >
            <Skeleton active paragraph={{ rows: 4 }} />
          </ProCard>
        ) : (
          <ProCard
            title="Páginas Afetadas"
            bordered
            headerBordered
          >
            <Paragraph>
              A naming strategy afeta automaticamente as seguintes páginas:
            </Paragraph>
            <ul>
              <li><Text strong>Services:</Text> Criação e atualização de serviços</li>
              <li><Text strong>Exporters:</Text> Registro de exporters no Consul</li>
              <li><Text strong>Blackbox Targets:</Text> Criação de alvos de monitoramento</li>
            </ul>
            <Alert
              type="success"
              showIcon
              message="Sincronização Automática"
              description="O frontend carrega estas configurações automaticamente ao iniciar, garantindo que a lógica de nomenclatura seja consistente entre backend e frontend."
            />
          </ProCard>
        )}
      </Space>

      {/* MODAL: Criar Site */}
      <ModalForm<Site>
        title="Adicionar Novo Site"
        open={createModalOpen}
        onOpenChange={setCreateModalOpen}
        onFinish={handleCreateSite}
        width={600}
        modalProps={{
          destroyOnHidden: true,
        }}
      >
        <ProFormText
          name="code"
          label="Código do Site"
          placeholder="Ex: saopaulo, brasilia, etc"
          rules={[
            { required: true, message: 'Código obrigatório' },
            { pattern: /^[a-z0-9_-]+$/, message: 'Apenas letras minúsculas, números, _ e -' },
          ]}
          tooltip="Código único para identificar o site (usado nos sufixos)"
        />
        <ProFormText
          name="name"
          label="Nome Descritivo"
          placeholder="Ex: São Paulo (SP)"
          rules={[{ required: true, message: 'Nome obrigatório' }]}
          tooltip="Nome completo do site para exibição"
        />
        <ProFormSwitch
          name="is_default"
          label="Site Padrão"
          tooltip="Se marcado, este site NÃO receberá sufixo nos nomes de serviço"
        />
        <ProFormSelect
          name="color"
          label="Cor do Badge"
          options={[
            { label: 'Azul', value: 'blue' },
            { label: 'Verde', value: 'green' },
            { label: 'Laranja', value: 'orange' },
            { label: 'Roxo', value: 'purple' },
            { label: 'Vermelho', value: 'red' },
            { label: 'Ciano', value: 'cyan' },
            { label: 'Magenta', value: 'magenta' },
            { label: 'Dourado', value: 'gold' },
          ]}
          placeholder="Selecione uma cor"
          tooltip="Cor do badge visual que aparecerá nas listagens"
        />
      </ModalForm>

      {/* MODAL: Editar Site */}
      <ModalForm<Site>
        key={editingSite?.code || 'edit-modal'}
        title="Editar Site"
        open={editModalOpen}
        onOpenChange={(visible) => {
          setEditModalOpen(visible);
          if (!visible) {
            setEditingSite(null);
          }
        }}
        onFinish={handleUpdateSite}
        initialValues={editingSite || undefined}
        width={600}
        modalProps={{
          destroyOnHidden: true,
        }}
      >
        <ProFormText
          name="code"
          label="Código do Site"
          disabled
          tooltip="O código não pode ser alterado após criação"
        />
        <ProFormText
          name="name"
          label="Nome Descritivo"
          placeholder="Ex: São Paulo (SP)"
          rules={[{ required: true, message: 'Nome obrigatório' }]}
        />
        <ProFormSwitch
          name="is_default"
          label="Site Padrão"
          tooltip="Se marcado, este site NÃO receberá sufixo nos nomes de serviço"
        />
        <ProFormSelect
          name="color"
          label="Cor do Badge"
          options={[
            { label: 'Azul', value: 'blue' },
            { label: 'Verde', value: 'green' },
            { label: 'Laranja', value: 'orange' },
            { label: 'Roxo', value: 'purple' },
            { label: 'Vermelho', value: 'red' },
            { label: 'Ciano', value: 'cyan' },
            { label: 'Magenta', value: 'magenta' },
            { label: 'Dourado', value: 'gold' },
          ]}
          placeholder="Selecione uma cor"
        />
      </ModalForm>
    </PageContainer>
  );
};

export default Settings;
