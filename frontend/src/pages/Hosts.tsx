/**
 * Página de Hosts - Dashboard de Métricas do Host Consul
 * Similar ao TenSunS /consul/hosts - mostra métricas de CPU, Memória, Disco, etc.
 */
import React, { useEffect, useState } from 'react';
import {
  Card,
  Row,
  Col,
  Statistic,
  Progress,
  Descriptions,
  Select,
  Space,
  Typography,
  Spin,
  Alert,
  Tag,
} from 'antd';
import {
  CloudServerOutlined,
  HddOutlined,
  DatabaseOutlined,
  FieldTimeOutlined,
  ApiOutlined,
} from '@ant-design/icons';
import { PageContainer } from '@ant-design/pro-components';
import { consulAPI } from '../services/api';

const { Title, Text } = Typography;
const { Option } = Select;

interface HostMetrics {
  host?: {
    hostname?: string;
    uptime?: number;
    os?: string;
    kernel?: string;
  };
  cpu?: {
    cores?: number;
    modelName?: string;
    vendorId?: string;
  };
  memory?: {
    total?: number;
    available?: number;
    used?: number;
    usedPercent?: number;
  };
  disk?: {
    path?: string;
    fstype?: string;
    total?: number;
    free?: number;
    used?: number;
    usedPercent?: number;
  };
  pmem?: number;
  pdisk?: number;
}

const Hosts: React.FC = () => {
  const [loading, setLoading] = useState(true);
  const [metrics, setMetrics] = useState<HostMetrics | null>(null);
  const [nodes, setNodes] = useState<any[]>([]);
  const [selectedNode, setSelectedNode] = useState<string>('');

  useEffect(() => {
    fetchNodes();
  }, []);

  useEffect(() => {
    if (selectedNode) {
      fetchHostMetrics(selectedNode);
    } else if (nodes.length > 0) {
      // Selecionar primeiro nó por padrão
      setSelectedNode(nodes[0]?.addr || '');
    }
  }, [selectedNode, nodes]);

  const fetchNodes = async () => {
    try {
      const response = await consulAPI.getNodes();
      const nodeList = Array.isArray(response?.data?.data) ? response.data.data : [];
      setNodes(nodeList);

      if (nodeList.length > 0 && !selectedNode) {
        setSelectedNode(nodeList[0]?.addr || '');
      }
    } catch (error) {
      console.error('Error fetching nodes:', error);
    }
  };

  const fetchHostMetrics = async (nodeAddr?: string) => {
    setLoading(true);
    try {
      const response = await consulAPI.getConsulHostMetrics(nodeAddr);
      const data = response.data;
      setMetrics(data as any);
    } catch (error) {
      console.error('Error fetching host metrics:', error);
    } finally {
      setLoading(false);
    }
  };

  const formatBytes = (bytes?: number): string => {
    if (!bytes) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return `${(bytes / Math.pow(k, i)).toFixed(2)} ${sizes[i]} `;
  };

  const getProgressColor = (percent?: number) => {
    if (!percent) return '#52c41a';
    if (percent >= 90) return '#ff4d4f';
    if (percent >= 75) return '#faad14';
    return '#52c41a';
  };

  if (loading && !metrics) {
    return (
      <PageContainer>
        <div style={{ textAlign: 'center', padding: 50 }}>
          <Spin size="large" tip="Carregando métricas do host...">
            <div style={{ minHeight: 50 }} />
          </Spin>
        </div>
      </PageContainer>
    );
  }

  return (
    <PageContainer
      header={{
        title: 'Hosts',
        subTitle: 'Métricas e informações do host Consul',
        extra: nodes.length > 1 ? (
          <Space>
            <Text>Selecionar Nó:</Text>
            <Select
              style={{ width: 250 }}
              value={selectedNode}
              onChange={(value) => setSelectedNode(value)}
              loading={loading}
            >
              {nodes.map((node) => (
                <Option key={node.addr} value={node.addr}>
                  {node.node} ({node.addr})
                </Option>
              ))}
            </Select>
          </Space>
        ) : null,
      }}
    >
      {!metrics ? (
        <Alert
          message="Nenhuma métrica disponível"
          description="Não foi possível obter métricas do host Consul."
          type="warning"
          showIcon
        />
      ) : (
        <Space direction="vertical" size="large" style={{ width: '100%' }}>
          {/* Resumo Rápido */}
          <Card>
            <Row gutter={[24, 24]}>
              <Col xs={24} sm={12} md={6}>
                <Statistic
                  title="Uso de Memória"
                  value={metrics.pmem || 0}
                  suffix="%"
                  valueStyle={{
                    color: getProgressColor(metrics.pmem),
                    fontSize: 32,
                  }}
                  prefix={<DatabaseOutlined />}
                />
                <Progress
                  percent={metrics.pmem || 0}
                  strokeColor={getProgressColor(metrics.pmem)}
                  showInfo={false}
                  style={{ marginTop: 8 }}
                />
              </Col>
              <Col xs={24} sm={12} md={6}>
                <Statistic
                  title="Uso de Disco"
                  value={metrics.pdisk || 0}
                  suffix="%"
                  valueStyle={{
                    color: getProgressColor(metrics.pdisk),
                    fontSize: 32,
                  }}
                  prefix={<HddOutlined />}
                />
                <Progress
                  percent={metrics.pdisk || 0}
                  strokeColor={getProgressColor(metrics.pdisk)}
                  showInfo={false}
                  style={{ marginTop: 8 }}
                />
              </Col>
              <Col xs={24} sm={12} md={6}>
                <Statistic
                  title="CPU Cores"
                  value={metrics.cpu?.cores || 0}
                  suffix="núcleos"
                  valueStyle={{ fontSize: 32 }}
                  prefix={<ApiOutlined />}
                />
              </Col>
              <Col xs={24} sm={12} md={6}>
                <Statistic
                  title="Tempo Ativo"
                  value={metrics.host?.uptime || 0}
                  suffix="dias"
                  valueStyle={{ fontSize: 32 }}
                  prefix={<FieldTimeOutlined />}
                />
              </Col>
            </Row>
          </Card>

          {/* Informações do Host */}
          <Row gutter={[16, 16]}>
            <Col xs={24} lg={12}>
              <Card
                title={
                  <Space>
                    <CloudServerOutlined style={{ fontSize: 24, color: '#1890ff' }} />
                    <span>Hospedar</span>
                  </Space>
                }
                variant="outlined"
                style={{ height: '100%' }}
              >
                <Descriptions column={1} size="small">
                  <Descriptions.Item label="nome do host">
                    <Text strong>{metrics.host?.hostname || 'N/A'}</Text>
                  </Descriptions.Item>
                  <Descriptions.Item label="tempo de atividade">
                    {metrics.host?.uptime ? `${metrics.host.uptime} dias` : 'N/A'}
                  </Descriptions.Item>
                  <Descriptions.Item label="sistema operacional">
                    {metrics.host?.os || 'N/A'}
                  </Descriptions.Item>
                  <Descriptions.Item label="núcleo">
                    {metrics.host?.kernel || 'N/A'}
                  </Descriptions.Item>
                </Descriptions>
              </Card>
            </Col>

            {/* CPU */}
            <Col xs={24} lg={12}>
              <Card
                title={
                  <Space>
                    <ApiOutlined style={{ fontSize: 24, color: '#52c41a' }} />
                    <span>CPU</span>
                  </Space>
                }
                variant="outlined"
                style={{ height: '100%' }}
              >
                <Descriptions column={1} size="small">
                  <Descriptions.Item label="núcleos">
                    <Tag color="blue">{metrics.cpu?.cores || 0} núcleos</Tag>
                  </Descriptions.Item>
                  <Descriptions.Item label="ID do fornecedor">
                    {metrics.cpu?.vendorId || 'N/A'}
                  </Descriptions.Item>
                  <Descriptions.Item label="nome do modelo">
                    {metrics.cpu?.modelName || 'N/A'}
                  </Descriptions.Item>
                </Descriptions>
              </Card>
            </Col>
          </Row>

          {/* Memória */}
          <Row gutter={[16, 16]}>
            <Col xs={24} lg={12}>
              <Card
                title={
                  <Space>
                    <DatabaseOutlined style={{ fontSize: 24, color: '#fa8c16' }} />
                    <span>Memória</span>
                  </Space>
                }
                variant="outlined"
              >
                <Row gutter={16} style={{ marginBottom: 16 }}>
                  <Col span={12}>
                    <Statistic
                      title="total"
                      value={`${metrics.memory?.total || 0} GB`}
                      valueStyle={{ fontSize: 18 }}
                    />
                  </Col>
                  <Col span={12}>
                    <Statistic
                      title="disponível"
                      value={`${metrics.memory?.available || 0} GB`}
                      valueStyle={{ fontSize: 18, color: '#52c41a' }}
                    />
                  </Col>
                </Row>

                <Row gutter={16} style={{ marginBottom: 16 }}>
                  <Col span={12}>
                    <Statistic
                      title="usado"
                      value={`${metrics.memory?.used || 0} GB`}
                      valueStyle={{ fontSize: 18 }}
                    />
                  </Col>
                  <Col span={12}>
                    <Statistic
                      title="usadoPorcentagem"
                      value={`${(metrics.memory?.usedPercent || 0).toFixed(0)}%`}
                      valueStyle={{
                        fontSize: 18,
                        color: getProgressColor(metrics.memory?.usedPercent),
                      }}
                    />
                  </Col>
                </Row>

                <Progress
                  percent={Math.round(metrics.memory?.usedPercent || 0)}
                  strokeColor={getProgressColor(metrics.memory?.usedPercent)}
                  showInfo={false}
                />
              </Card>
            </Col>

            {/* Disco */}
            <Col xs={24} lg={12}>
              <Card
                title={
                  <Space>
                    <HddOutlined style={{ fontSize: 24, color: '#722ed1' }} />
                    <span>disco</span>
                  </Space>
                }
                variant="outlined"
              >
                {metrics.disk ? (
                  <div>
                    <Row gutter={16} style={{ marginBottom: 8 }}>
                      <Col span={8}>
                        <Text type="secondary">caminho</Text>
                        <div>
                          <Text strong>{metrics.disk.path || '/'}</Text>
                        </div>
                      </Col>
                      <Col span={8}>
                        <Text type="secondary">tipo de fs</Text>
                        <div>
                          <Tag>{metrics.disk.fstype || 'N/A'}</Tag>
                        </div>
                      </Col>
                      <Col span={8}>
                        <Text type="secondary">total</Text>
                        <div>
                          <Text strong>{metrics.disk.total} GB</Text>
                        </div>
                      </Col>
                    </Row>

                    <Row gutter={16} style={{ marginBottom: 8 }}>
                      <Col span={8}>
                        <Text type="secondary">livre</Text>
                        <div>
                          <Text style={{ color: '#52c41a' }}>{metrics.disk.free} GB</Text>
                        </div>
                      </Col>
                      <Col span={8}>
                        <Text type="secondary">usado</Text>
                        <div>
                          <Text>{metrics.disk.used} GB</Text>
                        </div>
                      </Col>
                      <Col span={8}>
                        <Text type="secondary">usadoPorcentagem</Text>
                        <div>
                          <Text
                            style={{
                              color: getProgressColor(metrics.disk.usedPercent),
                              fontWeight: 'bold',
                            }}
                          >
                            {(metrics.disk.usedPercent || 0).toFixed(0)}%
                          </Text>
                        </div>
                      </Col>
                    </Row>

                    <Progress
                      percent={Math.round(metrics.disk.usedPercent || 0)}
                      strokeColor={getProgressColor(metrics.disk.usedPercent)}
                      showInfo={false}
                    />
                  </div>
                ) : (
                  <Text type="secondary">Nenhuma informação de disco disponível</Text>
                )}
              </Card>
            </Col>
          </Row>
        </Space>
      )}
    </PageContainer>
  );
};

export default Hosts;
