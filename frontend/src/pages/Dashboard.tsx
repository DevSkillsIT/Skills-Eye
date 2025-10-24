import React, { useEffect, useState } from 'react';
import { Card, Row, Col, Statistic, Progress, List, Tag, Space } from 'antd';
import { ProCard } from '@ant-design/pro-components';
import {
  CheckCircleOutlined,
  WarningOutlined,
  CloseCircleOutlined,
  CloudServerOutlined,
} from '@ant-design/icons';
import { consulAPI } from '../services/api';

const Dashboard: React.FC = () => {
  const [healthData, setHealthData] = useState<any>(null);
  const [nodesData, setNodesData] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 30000); // Atualiza a cada 30s
    return () => clearInterval(interval);
  }, []);

  const fetchData = async () => {
    try {
      const [health, nodes] = await Promise.all([
        consulAPI.getHealthStatus(),
        consulAPI.getNodes(),
      ]);
      
      setHealthData(health.data);
      setNodesData(nodes.data.data);
    } catch (error) {
      console.error('Erro ao buscar dados:', error);
    } finally {
      setLoading(false);
    }
  };

  const getHealthPercentage = () => {
    if (!healthData?.summary) return 0;
    const { passing, total } = healthData.summary;
    return total > 0 ? Math.round((passing / total) * 100) : 0;
  };

  return (
    <div style={{ padding: 24 }}>
      <Row gutter={[16, 16]}>
        <Col span={6}>
          <Card loading={loading}>
            <Statistic
              title="Serviços Saudáveis"
              value={healthData?.summary?.passing || 0}
              valueStyle={{ color: '#3f8600' }}
              prefix={<CheckCircleOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card loading={loading}>
            <Statistic
              title="Alertas"
              value={healthData?.summary?.warning || 0}
              valueStyle={{ color: '#faad14' }}
              prefix={<WarningOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card loading={loading}>
            <Statistic
              title="Críticos"
              value={healthData?.summary?.critical || 0}
              valueStyle={{ color: '#cf1322' }}
              prefix={<CloseCircleOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card loading={loading}>
            <Statistic
              title="Nós Ativos"
              value={nodesData.filter(n => n.status === 'alive').length}
              suffix={`/ ${nodesData.length}`}
              prefix={<CloudServerOutlined />}
            />
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col span={12}>
          <ProCard title="Health Status Geral" loading={loading}>
            <Progress
              percent={getHealthPercentage()}
              strokeColor={{
                '0%': '#108ee9',
                '100%': '#87d068',
              }}
              status={getHealthPercentage() < 80 ? 'exception' : 'active'}
            />
            <Space style={{ marginTop: 16 }}>
              <Tag color="green">Passing: {healthData?.summary?.passing || 0}</Tag>
              <Tag color="orange">Warning: {healthData?.summary?.warning || 0}</Tag>
              <Tag color="red">Critical: {healthData?.summary?.critical || 0}</Tag>
            </Space>
          </ProCard>
        </Col>

        <Col span={12}>
          <ProCard title="Nós do Cluster" loading={loading}>
            <List
              size="small"
              dataSource={nodesData}
              renderItem={(node) => (
                <List.Item>
                  <Space>
                    <Tag color={node.status === 'alive' ? 'green' : 'red'}>
                      {node.status}
                    </Tag>
                    <span>{node.node}</span>
                    <span style={{ color: '#888' }}>{node.addr}</span>
                    <Tag>{node.services_count || 0} serviços</Tag>
                  </Space>
                </List.Item>
              )}
            />
          </ProCard>
        </Col>
      </Row>
    </div>
  );
};

export default Dashboard;