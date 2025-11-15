/**
 * Cache Management Page - Gerenciamento Visual do LocalCache
 *
 * SPRINT 2 (2025-11-15)
 *
 * Funcionalidades:
 * - Visualizar estatísticas do cache (hits, misses, hit rate)
 * - Listar todas as chaves cacheadas
 * - Ver detalhes de cada entrada (idade, TTL, tamanho)
 * - Invalidar chaves individuais
 * - Invalidar por padrão (wildcards)
 * - Limpar todo o cache
 * - Atualização em tempo real (auto-refresh)
 */
import React, { useState, useEffect } from 'react';
import {
  Card,
  Button,
  Space,
  Statistic,
  Table,
  message,
  Modal,
  Input,
  Popconfirm,
  Tag,
  Progress,
  Typography,
  Row,
  Col,
  Alert,
} from 'antd';
import {
  ReloadOutlined,
  DeleteOutlined,
  ClearOutlined,
  InfoCircleOutlined,
  SearchOutlined,
  ClockCircleOutlined,
} from '@ant-design/icons';
import { PageContainer } from '@ant-design/pro-components';
import { cacheAPI } from '../services/api';

const { Text, Paragraph } = Typography;

interface CacheStats {
  hits: number;
  misses: number;
  evictions: number;
  invalidations: number;
  hit_rate_percent: number;
  total_requests: number;
  current_size: number;
  ttl_seconds: number;
}

interface CacheEntry {
  key: string;
  age_seconds: number;
  ttl_seconds: number;
  remaining_seconds: number;
  is_expired: boolean;
  timestamp: string;
  value_type: string;
  value_size_bytes: number;
}

export default function CacheManagement() {
  const [stats, setStats] = useState<CacheStats | null>(null);
  const [keys, setKeys] = useState<string[]>([]);
  const [entries, setEntries] = useState<CacheEntry[]>([]);
  const [loading, setLoading] = useState(false);
  const [autoRefresh, setAutoRefresh] = useState(false);
  const [invalidateModalOpen, setInvalidateModalOpen] = useState(false);
  const [invalidatePattern, setInvalidatePattern] = useState('');

  // Buscar estatísticas do cache
  const fetchStats = async () => {
    try {
      const response = await cacheAPI.getCacheStats();
      setStats(response.data);
    } catch (error) {
      console.error('Erro ao buscar estatísticas do cache:', error);
      message.error('Erro ao buscar estatísticas do cache');
    }
  };

  // Buscar lista de chaves
  const fetchKeys = async () => {
    try {
      const response = await cacheAPI.getCacheKeys();
      setKeys(response.data);
    } catch (error) {
      console.error('Erro ao buscar chaves do cache:', error);
      message.error('Erro ao buscar chaves do cache');
    }
  };

  // Buscar detalhes de todas as entradas
  const fetchEntries = async () => {
    setLoading(true);
    try {
      await fetchStats();
      await fetchKeys();

      // Buscar detalhes de cada chave em paralelo
      const keysResponse = await cacheAPI.getCacheKeys();
      const keysList = keysResponse.data;

      const entriesPromises = keysList.map(async (key: string) => {
        try {
          const response = await cacheAPI.getCacheEntry(key);
          return response.data;
        } catch (error) {
          return null;
        }
      });

      const entriesData = await Promise.all(entriesPromises);
      setEntries(entriesData.filter((e): e is CacheEntry => e !== null));
    } catch (error) {
      console.error('Erro ao buscar entradas do cache:', error);
      message.error('Erro ao buscar entradas do cache');
    } finally {
      setLoading(false);
    }
  };

  // Invalidar chave específica
  const handleInvalidateKey = async (key: string) => {
    try {
      await cacheAPI.invalidateCacheKey(key);
      message.success(`Chave '${key}' invalidada com sucesso`);
      fetchEntries();
    } catch (error) {
      console.error('Erro ao invalidar chave:', error);
      message.error('Erro ao invalidar chave');
    }
  };

  // Invalidar por padrão
  const handleInvalidatePattern = async () => {
    if (!invalidatePattern.trim()) {
      message.warning('Digite um padrão de busca');
      return;
    }

    try {
      const response = await cacheAPI.invalidateCachePattern(invalidatePattern);
      message.success(response.data.message);
      setInvalidateModalOpen(false);
      setInvalidatePattern('');
      fetchEntries();
    } catch (error) {
      console.error('Erro ao invalidar por padrão:', error);
      message.error('Erro ao invalidar por padrão');
    }
  };

  // Limpar todo o cache
  const handleClearAll = async () => {
    try {
      const response = await cacheAPI.clearAllCache();
      message.success(response.data.message);
      fetchEntries();
    } catch (error) {
      console.error('Erro ao limpar cache:', error);
      message.error('Erro ao limpar cache');
    }
  };

  // Auto-refresh a cada 5 segundos
  useEffect(() => {
    fetchEntries();
  }, []);

  useEffect(() => {
    let interval: NodeJS.Timeout;
    if (autoRefresh) {
      interval = setInterval(() => {
        fetchEntries();
      }, 5000);
    }
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [autoRefresh]);

  // Colunas da tabela
  const columns = [
    {
      title: 'Chave',
      dataIndex: 'key',
      key: 'key',
      width: 300,
      ellipsis: true,
      render: (key: string) => (
        <Text code copyable style={{ fontSize: '12px' }}>
          {key}
        </Text>
      ),
    },
    {
      title: 'Idade',
      dataIndex: 'age_seconds',
      key: 'age',
      width: 100,
      render: (age: number) => (
        <Tag color="blue">{age < 60 ? `${age}s` : `${Math.floor(age / 60)}m`}</Tag>
      ),
    },
    {
      title: 'TTL Restante',
      dataIndex: 'remaining_seconds',
      key: 'remaining',
      width: 120,
      render: (remaining: number, record: CacheEntry) => {
        const percent = (remaining / record.ttl_seconds) * 100;
        return (
          <Space direction="vertical" size="small" style={{ width: '100%' }}>
            <Progress
              percent={percent}
              size="small"
              status={percent < 20 ? 'exception' : 'active'}
              showInfo={false}
            />
            <Text type="secondary" style={{ fontSize: '11px' }}>
              {remaining < 60 ? `${remaining.toFixed(0)}s` : `${Math.floor(remaining / 60)}m`}
            </Text>
          </Space>
        );
      },
    },
    {
      title: 'Tipo',
      dataIndex: 'value_type',
      key: 'type',
      width: 80,
      render: (type: string) => <Tag>{type}</Tag>,
    },
    {
      title: 'Tamanho',
      dataIndex: 'value_size_bytes',
      key: 'size',
      width: 100,
      render: (bytes: number) => {
        if (bytes < 1024) return `${bytes} B`;
        if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
        return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
      },
    },
    {
      title: 'Ações',
      key: 'actions',
      width: 100,
      render: (_: unknown, record: CacheEntry) => (
        <Popconfirm
          title="Invalidar esta chave?"
          description="Os dados serão recarregados do Consul na próxima requisição."
          onConfirm={() => handleInvalidateKey(record.key)}
          okText="Sim"
          cancelText="Não"
        >
          <Button
            type="link"
            danger
            size="small"
            icon={<DeleteOutlined />}
          >
            Invalidar
          </Button>
        </Popconfirm>
      ),
    },
  ];

  return (
    <PageContainer
      title="Gerenciamento de Cache"
      subTitle="Monitore e controle o cache local da aplicação"
    >
      <Space direction="vertical" size="large" style={{ width: '100%' }}>
        {/* Alert de informação */}
        <Alert
          message="Cache Local com TTL 60s"
          description="Este cache reduz a latência de 1289ms para ~10ms (128x mais rápido!) ao evitar requisições repetidas ao Consul em janelas curtas de tempo."
          type="info"
          showIcon
          icon={<InfoCircleOutlined />}
        />

        {/* Estatísticas */}
        {stats && (
          <Card title="Estatísticas do Cache">
            <Row gutter={16}>
              <Col span={4}>
                <Statistic
                  title="Hit Rate"
                  value={stats.hit_rate_percent}
                  precision={2}
                  suffix="%"
                  valueStyle={{
                    color: stats.hit_rate_percent > 50 ? '#3f8600' : '#cf1322',
                  }}
                />
              </Col>
              <Col span={4}>
                <Statistic title="Hits" value={stats.hits} valueStyle={{ color: '#3f8600' }} />
              </Col>
              <Col span={4}>
                <Statistic title="Misses" value={stats.misses} valueStyle={{ color: '#cf1322' }} />
              </Col>
              <Col span={4}>
                <Statistic title="Total Requests" value={stats.total_requests} />
              </Col>
              <Col span={4}>
                <Statistic title="Entradas" value={stats.current_size} />
              </Col>
              <Col span={4}>
                <Statistic
                  title="TTL Padrão"
                  value={stats.ttl_seconds}
                  suffix="s"
                  prefix={<ClockCircleOutlined />}
                />
              </Col>
            </Row>
          </Card>
        )}

        {/* Ações */}
        <Card size="small">
          <Space wrap>
            <Button
              type="primary"
              icon={<ReloadOutlined />}
              onClick={fetchEntries}
              loading={loading}
            >
              Atualizar
            </Button>

            <Button
              type={autoRefresh ? 'primary' : 'default'}
              icon={<ReloadOutlined spin={autoRefresh} />}
              onClick={() => setAutoRefresh(!autoRefresh)}
            >
              {autoRefresh ? 'Auto-Refresh ON' : 'Auto-Refresh OFF'}
            </Button>

            <Button
              icon={<SearchOutlined />}
              onClick={() => setInvalidateModalOpen(true)}
            >
              Invalidar por Padrão
            </Button>

            <Popconfirm
              title="Limpar TODO o cache?"
              description={`Isso removerá ${entries.length} entradas. As próximas requisições serão mais lentas.`}
              onConfirm={handleClearAll}
              okText="Sim, limpar tudo"
              cancelText="Cancelar"
              okButtonProps={{ danger: true }}
            >
              <Button danger icon={<ClearOutlined />}>
                Limpar Tudo
              </Button>
            </Popconfirm>
          </Space>
        </Card>

        {/* Tabela de entradas */}
        <Card title={`Entradas do Cache (${entries.length})`}>
          <Table
            columns={columns}
            dataSource={entries}
            rowKey="key"
            loading={loading}
            size="small"
            pagination={{
              defaultPageSize: 20,
              showSizeChanger: true,
              showTotal: (total) => `Total: ${total} entradas`,
            }}
            scroll={{ x: 800 }}
          />
        </Card>
      </Space>

      {/* Modal de invalidação por padrão */}
      <Modal
        title="Invalidar por Padrão"
        open={invalidateModalOpen}
        onOk={handleInvalidatePattern}
        onCancel={() => {
          setInvalidateModalOpen(false);
          setInvalidatePattern('');
        }}
        okText="Invalidar"
        cancelText="Cancelar"
      >
        <Space direction="vertical" style={{ width: '100%' }}>
          <Paragraph>
            Use wildcards (*) para invalidar múltiplas chaves de uma vez:
          </Paragraph>
          <ul>
            <li>
              <Text code>services:*</Text> - Todas as chaves começando com "services:"
            </li>
            <li>
              <Text code>*:catalog</Text> - Todas as chaves terminando com ":catalog"
            </li>
            <li>
              <Text code>*blackbox*</Text> - Todas as chaves contendo "blackbox"
            </li>
          </ul>
          <Input
            placeholder="Digite o padrão (ex: services:*)"
            value={invalidatePattern}
            onChange={(e) => setInvalidatePattern(e.target.value)}
            prefix={<SearchOutlined />}
          />
        </Space>
      </Modal>
    </PageContainer>
  );
}
