import React, { useEffect, useState } from 'react';
import {
  Card,
  Row,
  Col,
  Statistic,
  Progress,
  Space,
  Button,
  Timeline,
  Empty,
  Typography,
  Spin,
} from 'antd';
import { ProCard } from '@ant-design/pro-components';
import {
  CheckCircleOutlined,
  WarningOutlined,
  CloseCircleOutlined,
  CloudServerOutlined,
  RiseOutlined,
  ReloadOutlined,
  PlusOutlined,
  DatabaseOutlined,
  ApiOutlined,
  BarChartOutlined,
  InfoCircleOutlined,
  ClockCircleOutlined,
} from '@ant-design/icons';
import { Column, Pie } from '@ant-design/charts';
import { consulAPI } from '../services/api';
import type { DashboardMetrics } from '../services/api';
import { useNavigate } from 'react-router-dom';

const { Title, Text } = Typography;

interface PrometheusMetrics {
  cache_hits: number;
  cache_misses: number;
  cache_hit_rate: number;
  stale_responses: number;
  fallback_events: number;
  total_requests: number;
}

const Dashboard: React.FC = () => {
  const [metrics, setMetrics] = useState<DashboardMetrics | null>(null);
  const [prometheusMetrics, setPrometheusMetrics] = useState<PrometheusMetrics | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    fetchMetrics();

    if (autoRefresh) {
      const interval = setInterval(() => {
        fetchMetrics(true);
      }, 30000); // Auto-refresh a cada 30s
      return () => clearInterval(interval);
    }
  }, [autoRefresh]);

  const fetchMetrics = async (silent = false) => {
    if (!silent) setLoading(true);
    else setRefreshing(true);

    try {
      const data = await consulAPI.getDashboardMetrics();
      setMetrics(data);

      // Buscar métricas Prometheus (SPRINT 2)
      try {
        const promResponse = await fetch('http://localhost:5000/api/v1/prometheus-metrics/summary');
        if (promResponse.ok) {
          const promData = await promResponse.json();
          setPrometheusMetrics(promData);
        }
      } catch (promError) {
        console.warn('Erro ao buscar métricas Prometheus:', promError);
      }
    } catch (error) {
      console.error('Erro ao buscar metricas do dashboard:', error);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  const getHealthPercentage = () => {
    if (!metrics?.health) return 0;
    const { passing, warning, critical } = metrics.health;
    const total = passing + warning + critical;
    return total > 0 ? Math.round((passing / total) * 100) : 0;
  };

  const getHealthStatus = () => {
    const percent = getHealthPercentage();
    if (percent >= 95) return { status: 'success', text: 'Excelente' };
    if (percent >= 80) return { status: 'normal', text: 'Bom' };
    if (percent >= 60) return { status: 'exception', text: 'Atencao' };
    return { status: 'exception', text: 'Critico' };
  };

  // Preparar dados para grafico de ambientes
  const getEnvChartData = () => {
    if (!metrics?.by_env) return [];
    return Object.entries(metrics.by_env).map(([env, count]) => ({
      environment: env || 'unknown',
      count,
    }));
  };

  // Preparar dados para grafico de datacenters
  const getDatacenterChartData = () => {
    if (!metrics?.by_datacenter) return [];
    return Object.entries(metrics.by_datacenter).map(([dc, count]) => ({
      datacenter: dc || 'unknown',
      count,
    }));
  };

  // Configuracao do grafico de colunas para ambientes
  const envChartConfig = {
    data: getEnvChartData(),
    xField: 'environment',
    yField: 'count',
    label: {
      position: 'top' as const,
      style: {
        fill: '#000000',
        opacity: 0.6,
      },
    },
    xAxis: {
      label: {
        autoHide: true,
        autoRotate: false,
      },
    },
    meta: {
      environment: { alias: 'Ambiente' },
      count: { alias: 'Quantidade' },
    },
    color: '#1890ff',
  };

  const totalServices = metrics?.total_services ?? 0;

  // Configuracao do grafico de pizza para datacenters
  const dcChartConfig = {
    data: getDatacenterChartData(),
    angleField: 'count',
    colorField: 'datacenter',
    radius: 0.8,
    label: {
      formatter: (datum: any) => {
        if (!datum || !datum.datacenter) return '';
        if (!totalServices) return `${datum.datacenter}: 0%`;
        const percentage = ((datum.count / totalServices) * 100).toFixed(1);
        return `${datum.datacenter}: ${percentage}%`;
      },
    },
    interactions: [{ type: 'element-active' }],
    legend: {
      position: 'bottom' as const,
    },
  };

  if (loading) {
    return (
      <div style={{ paddingTop: 100, paddingLeft: 24, paddingRight: 24, paddingBottom: 24, textAlign: 'center' }}>
        <Spin size="large" tip="Carregando metricas do dashboard...">
          <div style={{ padding: 50 }} />
        </Spin>
      </div>
    );
  }

  if (!metrics) {
    return (
      <div style={{ padding: 24 }}>
        <Empty description="Nenhum dado disponivel" />
      </div>
    );
  }
  return (
    <div style={{ padding: 24, background: '#f0f2f5', minHeight: '100vh' }}>
      {/* Header com titulo e acoes */}
      <div style={{ marginBottom: 24, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <Title level={2} style={{ margin: 0 }}>
            Dashboard
          </Title>
          <Text type="secondary">
            Visao geral do sistema de monitoramento
          </Text>
        </div>
        <Space>
          <Button
            icon={<ReloadOutlined spin={refreshing} />}
            onClick={() => fetchMetrics()}
            loading={refreshing}
          >
            Atualizar
          </Button>
          <Button
            type={autoRefresh ? 'primary' : 'default'}
            onClick={() => setAutoRefresh(!autoRefresh)}
          >
            Auto-refresh: {autoRefresh ? 'ON' : 'OFF'}
          </Button>
        </Space>
      </div>

      {/* Cards de metricas principais */}
      <Row gutter={[16, 16]}>
        <Col xs={24} sm={12} md={6}>
          <Card
            hoverable
            style={{
              borderRadius: 8,
              boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
            }}
          >
            <Statistic
              title="Total de Serviços"
              value={metrics?.total_services || 0}
              valueStyle={{ color: '#1890ff', fontSize: 32 }}
              prefix={<ApiOutlined />}
              suffix={
                <RiseOutlined style={{ fontSize: 16, color: '#52c41a' }} />
              }
            />
            <div style={{ marginTop: 8, fontSize: 12, color: '#8c8c8c' }}>
              Serviços registrados no Consul
            </div>
          </Card>
        </Col>

        <Col xs={24} sm={12} md={6}>
          <Card
            hoverable
            style={{
              borderRadius: 8,
              boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
            }}
          >
            <Statistic
              title="Alvos Blackbox"
              value={metrics?.blackbox_targets || 0}
              valueStyle={{ color: '#722ed1', fontSize: 32 }}
              prefix={<BarChartOutlined />}
            />
            <div style={{ marginTop: 8, fontSize: 12, color: '#8c8c8c' }}>
              Targets de monitoramento ativo
            </div>
          </Card>
        </Col>

        <Col xs={24} sm={12} md={6}>
          <Card
            hoverable
            style={{
              borderRadius: 8,
              boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
            }}
          >
            <Statistic
              title="Exportadores"
              value={metrics?.exporters || 0}
              valueStyle={{ color: '#13c2c2', fontSize: 32 }}
              prefix={<DatabaseOutlined />}
            />
            <div style={{ marginTop: 8, fontSize: 12, color: '#8c8c8c' }}>
              Node, Windows, Redis, etc.
            </div>
          </Card>
        </Col>

        <Col xs={24} sm={12} md={6}>
          <Card
            hoverable
            style={{
              borderRadius: 8,
              boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
            }}
          >
            <Statistic
              title="Nos Ativos"
              value={metrics?.active_nodes || 0}
              valueStyle={{ color: '#52c41a', fontSize: 32 }}
              prefix={<CloudServerOutlined />}
              suffix={`/ ${metrics?.total_nodes || 0}`}
            />
            <div style={{ marginTop: 8, fontSize: 12, color: '#8c8c8c' }}>
              Nodes no cluster Consul
            </div>
          </Card>
        </Col>
      </Row>

      {/* Saude do Sistema e Acoes Rapidas */}
      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col xs={24} lg={16}>
          <ProCard
            title={
              <Space>
                <CheckCircleOutlined />
                <span>Saude do Sistema</span>
              </Space>
            }
            headStyle={{ borderBottom: '2px solid #1890ff' }}
            bordered
            style={{
              borderRadius: 8,
              boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
            }}
          >
            <div style={{ paddingTop: 16, paddingBottom: 16 }}>
              <Progress
                percent={getHealthPercentage()}
                size={20}
                strokeColor={{
                  '0%': '#ff4d4f',
                  '50%': '#faad14',
                  '100%': '#52c41a',
                }}
                status={getHealthStatus().status as any}
                format={(percent) => `${percent}% ${getHealthStatus().text}`}
              />
            </div>

            <Row gutter={16} style={{ marginTop: 24 }}>
              <Col span={8}>
                <Card
                  style={{
                    textAlign: 'center',
                    background: '#f6ffed',
                    border: '1px solid #b7eb8f',
                  }}
                >
                  <CheckCircleOutlined
                    style={{ fontSize: 32, color: '#52c41a', marginBottom: 8 }}
                  />
                  <div style={{ fontSize: 24, fontWeight: 'bold', color: '#52c41a' }}>
                    {metrics?.health?.passing || 0}
                  </div>
                  <div style={{ color: '#52c41a', fontWeight: 500 }}>Saudaveis</div>
                </Card>
              </Col>
              <Col span={8}>
                <Card
                  style={{
                    textAlign: 'center',
                    background: '#fffbe6',
                    border: '1px solid #ffe58f',
                  }}
                >
                  <WarningOutlined
                    style={{ fontSize: 32, color: '#faad14', marginBottom: 8 }}
                  />
                  <div style={{ fontSize: 24, fontWeight: 'bold', color: '#faad14' }}>
                    {metrics?.health?.warning || 0}
                  </div>
                  <div style={{ color: '#faad14', fontWeight: 500 }}>Alertas</div>
                </Card>
              </Col>
              <Col span={8}>
                <Card
                  style={{
                    textAlign: 'center',
                    background: '#fff1f0',
                    border: '1px solid #ffccc7',
                  }}
                >
                  <CloseCircleOutlined
                    style={{ fontSize: 32, color: '#ff4d4f', marginBottom: 8 }}
                  />
                  <div style={{ fontSize: 24, fontWeight: 'bold', color: '#ff4d4f' }}>
                    {metrics?.health?.critical || 0}
                  </div>
                  <div style={{ color: '#ff4d4f', fontWeight: 500 }}>Criticos</div>
                </Card>
              </Col>
            </Row>
          </ProCard>
        </Col>

        <Col xs={24} lg={8}>
          <ProCard
            title="Acoes Rapidas"
            headStyle={{ borderBottom: '2px solid #1890ff' }}
            bordered
            style={{
              borderRadius: 8,
              boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
            }}
          >
            <Space direction="vertical" style={{ width: '100%' }} size="middle">
              {/* NOTA: Botoes de blackbox e services removidos em SPEC-CLEANUP-001 v1.4.0 */}
              {/* As paginas foram substituidas por DynamicMonitoringPage */}
              <Button
                type="primary"
                block
                icon={<PlusOutlined />}
                size="large"
                onClick={() => navigate('/monitoring/network-probes?create=true')}
              >
                Novo alvo de monitoramento
              </Button>
              <Button
                block
                icon={<DatabaseOutlined />}
                size="large"
                onClick={() => navigate('/installer')}
              >
                Instalar Exporter
              </Button>
              <Button
                block
                icon={<BarChartOutlined />}
                size="large"
                onClick={() => navigate('/service-groups')}
              >
                Ver grupos de servicos
              </Button>
            </Space>
          </ProCard>
        </Col>
      </Row>

      {/* Métricas Prometheus (SPRINT 2) */}
      {prometheusMetrics && (
        <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
          <Col xs={24}>
            <ProCard
              title={
                <Space>
                  <BarChartOutlined />
                  <span>Métricas de Cache e Performance (Prometheus)</span>
                </Space>
              }
              headStyle={{ borderBottom: '2px solid #52c41a' }}
              bordered
              style={{
                borderRadius: 8,
                boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
              }}
            >
              <Row gutter={16}>
                <Col xs={24} sm={12} md={6}>
                  <Statistic
                    title="Hit Rate"
                    value={prometheusMetrics.cache_hit_rate}
                    precision={1}
                    suffix="%"
                    valueStyle={{
                      color: prometheusMetrics.cache_hit_rate > 70 ? '#52c41a' : '#faad14',
                      fontSize: 28,
                    }}
                    prefix={
                      prometheusMetrics.cache_hit_rate > 70 ? (
                        <CheckCircleOutlined />
                      ) : (
                        <WarningOutlined />
                      )
                    }
                  />
                  <div style={{ marginTop: 8, fontSize: 12, color: '#8c8c8c' }}>
                    Taxa de acerto do cache local
                  </div>
                </Col>

                <Col xs={24} sm={12} md={6}>
                  <Statistic
                    title="Cache Hits"
                    value={prometheusMetrics.cache_hits}
                    valueStyle={{ color: '#52c41a', fontSize: 28 }}
                    prefix={<RiseOutlined />}
                  />
                  <div style={{ marginTop: 8, fontSize: 12, color: '#8c8c8c' }}>
                    Requisições servidas do cache
                  </div>
                </Col>

                <Col xs={24} sm={12} md={6}>
                  <Statistic
                    title="Stale Responses"
                    value={prometheusMetrics.stale_responses}
                    valueStyle={{
                      color: prometheusMetrics.stale_responses > 10 ? '#faad14' : '#1890ff',
                      fontSize: 28,
                    }}
                    prefix={<ClockCircleOutlined />}
                  />
                  <div style={{ marginTop: 8, fontSize: 12, color: '#8c8c8c' }}>
                    Respostas com dados stale do Consul
                  </div>
                </Col>

                <Col xs={24} sm={12} md={6}>
                  <Statistic
                    title="Fallback Events"
                    value={prometheusMetrics.fallback_events}
                    valueStyle={{
                      color: prometheusMetrics.fallback_events > 0 ? '#ff4d4f' : '#52c41a',
                      fontSize: 28,
                    }}
                    prefix={
                      prometheusMetrics.fallback_events > 0 ? (
                        <WarningOutlined />
                      ) : (
                        <CheckCircleOutlined />
                      )
                    }
                  />
                  <div style={{ marginTop: 8, fontSize: 12, color: '#8c8c8c' }}>
                    Trocas de servidor por timeout
                  </div>
                </Col>
              </Row>

              <div style={{ marginTop: 16, padding: '8px 12px', background: '#f0f2f5', borderRadius: 4 }}>
                <Space>
                  <InfoCircleOutlined style={{ color: '#1890ff' }} />
                  <span style={{ fontSize: 12, color: '#595959' }}>
                    Total de Requisições: <strong>{prometheusMetrics.total_requests}</strong> | Cache
                    reduz latência de ~1289ms para ~10ms (128x mais rápido!)
                  </span>
                </Space>
              </div>
            </ProCard>
          </Col>
        </Row>
      )}

      {/* Graficos de Distribuicao */}
      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col xs={24} lg={12}>
          <ProCard
            title="Distribuicao por Ambiente"
            headStyle={{ borderBottom: '2px solid #1890ff' }}
            bordered
            style={{
              borderRadius: 8,
              boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
            }}
          >
            {getEnvChartData().length > 0 ? (
              <Column {...envChartConfig} height={300} />
            ) : (
              <Empty
                description="Nenhum dado de ambiente disponivel"
                style={{ padding: '40px 0' }}
              />
            )}
          </ProCard>
        </Col>

        <Col xs={24} lg={12}>
          <ProCard
            title="Distribuicao por Datacenter"
            headStyle={{ borderBottom: '2px solid #1890ff' }}
            bordered
            style={{
              borderRadius: 8,
              boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
            }}
          >
            {getDatacenterChartData().length > 0 ? (
              <Pie {...dcChartConfig} height={300} />
            ) : (
              <Empty
                description="Nenhum dado de datacenter disponivel"
                style={{ padding: '40px 0' }}
              />
            )}
          </ProCard>
        </Col>
      </Row>

      {/* Atividade Recente */}
      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col span={24}>
          <ProCard
            title="Atividade Recente"
            headStyle={{ borderBottom: '2px solid #1890ff' }}
            bordered
            style={{
              borderRadius: 8,
              boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
            }}
          >
            {metrics?.recent_changes && metrics.recent_changes.length > 0 ? (
              <Timeline
                mode="left"
                items={metrics.recent_changes.slice(0, 10).map((event: any) => {
                  // Safely convert resource_type to string
                  let resourceType = event.resource_type;
                  if (typeof resourceType === 'object' && resourceType !== null) {
                    try {
                      resourceType = JSON.stringify(resourceType);
                    } catch {
                      resourceType = String(resourceType);
                    }
                  }

                  // Safely convert resource_id to string
                  let resourceId = event.resource_id;
                  if (typeof resourceId === 'object' && resourceId !== null) {
                    try {
                      resourceId = JSON.stringify(resourceId);
                    } catch {
                      resourceId = String(resourceId);
                    }
                  }

                  // Safely convert user to string
                  let user = event.user || 'system';
                  if (typeof user === 'object' && user !== null) {
                    try {
                      user = JSON.stringify(user);
                    } catch {
                      user = String(user);
                    }
                  }

                  // Safely convert details to string
                  let details = event.details;
                  if (details && typeof details === 'object' && details !== null) {
                    try {
                      details = JSON.stringify(details);
                    } catch {
                      details = String(details);
                    }
                  }

                  return {
                    color: event.action === 'create' ? 'green' : event.action === 'delete' ? 'red' : 'blue',
                    children: (
                      <div>
                        <div style={{ fontWeight: 500 }}>
                          {event.action === 'create' && 'Criado'}
                          {event.action === 'update' && 'Atualizado'}
                          {event.action === 'delete' && 'Removido'}
                          {event.action === 'register' && 'Registrado'}
                          : {String(resourceType)} - {String(resourceId)}
                        </div>
                        <div style={{ fontSize: 12, color: '#8c8c8c' }}>
                          por {String(user)}  {new Date(event.timestamp).toLocaleString('pt-BR')}
                        </div>
                        {details && (
                          <div style={{ fontSize: 12, marginTop: 4 }}>
                            {String(details)}
                          </div>
                        )}
                      </div>
                    ),
                  };
                })}
              />
            ) : (
              <Empty
                description="Nenhuma atividade recente"
                style={{ padding: '40px 0' }}
              />
            )}
          </ProCard>
        </Col>
      </Row>

      {/* Footer com informacoes */}
      <div style={{ marginTop: 24, textAlign: 'center', color: '#8c8c8c' }}>
        <Text type="secondary">
          Ultima atualizacao: {new Date().toLocaleString('pt-BR')}
          {autoRefresh && '  Auto-refresh ativo (30s)'}
        </Text>
      </div>
    </div>
  );
};

export default Dashboard;


