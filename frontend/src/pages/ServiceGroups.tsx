/**
 * Página de Grupos de Serviços - Visão Agrupada (TenSunS Style)
 * Mostra serviços agrupados com estatísticas, similar ao /consul/services do TenSunS
 */
import React, { useRef, useState } from 'react';
import { Button, Card, Space, Statistic, Tag, Tooltip, App } from 'antd';
import {
  CloudOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  ReloadOutlined,
  InfoCircleOutlined,
} from '@ant-design/icons';
import { PageContainer, ProTable } from '@ant-design/pro-components';
import type { ActionType, ProColumns } from '@ant-design/pro-components';
import ResizableTitle from '../components/ResizableTitle';
import { consulAPI } from '../services/api';
import { useNavigate } from 'react-router-dom';

interface ServiceGroupItem {
  name: string;
  datacenter: string;
  instance_count: number;
  checks_critical: number;
  checks_passing: number;
  tags: string[];
  nodes: string[];
}

const ServiceGroups: React.FC = () => {
  const { message } = App.useApp();
  const actionRef = useRef<ActionType>();
  const navigate = useNavigate();
  const [summary, setSummary] = useState({ total: 0, totalInstances: 0, healthy: 0, unhealthy: 0 });
  const [columnWidths, setColumnWidths] = useState<Record<string, number>>({});

  const requestHandler = async () => {
    try {
      // 🚀 USAR ENDPOINT OTIMIZADO - Cache de 30s, processado no backend
      const response = await consulAPI.getServiceGroupsOptimized();
      const { data: backendServices, summary: backendSummary } = response.data;

      // Converter para formato esperado pela tabela
      const services = backendServices.map((item) => ({
        name: item.Name,
        datacenter: item.Datacenter,
        tags: item.Tags || [],
        nodes: item.Nodes || [],
        instance_count: item.InstanceCount || 0,
        checks_passing: item.ChecksPassing || 0,
        checks_warning: item.ChecksWarning || 0,
        checks_critical: item.ChecksCritical || 0,
      }));

      // Usar summary do backend
      if (backendSummary) {
        setSummary({
          total: backendServices.length,
          totalInstances: backendSummary.totalInstances || 0,
          healthy: backendSummary.healthy || 0,
          unhealthy: backendSummary.unhealthy || 0,
        });
      } else {
        // Fallback: calcular summary
        const totalInstances = services.reduce((sum, s) => sum + (s.instance_count || 0), 0);
        const totalPassing = services.reduce((sum, s) => sum + (s.checks_passing || 0), 0);
        const totalCritical = services.reduce((sum, s) => sum + (s.checks_critical || 0), 0);

        setSummary({
          total: services.length,
          totalInstances,
          healthy: totalPassing,
          unhealthy: totalCritical,
        });
      }

      return {
        data: services,
        success: true,
        total: services.length,
      };
    } catch (error) {
      console.error('Erro ao carregar serviços agrupados:', error);
      message.error('Falha ao carregar serviços');
      return {
        data: [],
        success: false,
        total: 0,
      };
    }
  };

  const handleServiceClick = (serviceName: string) => {
    // Navegar para página de Services com filtro
    navigate(`/services?service=${encodeURIComponent(serviceName)}`);
  };

  const handleResize = React.useCallback(
    (columnKey: string) =>
      (_: React.SyntheticEvent, { size }: { size: { width: number } }) => {
        setColumnWidths((prev) => ({ ...prev, [columnKey]: size.width }));
      },
    [],
  );

  const baseColumns: ProColumns<ServiceGroupItem>[] = [
    {
      title: 'Grupo de Serviço',
      dataIndex: 'name',
      key: 'name',
      width: 250,
      fixed: 'left',
      render: (name) => (
        <Button
          type="link"
          onClick={() => handleServiceClick(name as string)}
          style={{ padding: 0, height: 'auto' }}
        >
          {name}
        </Button>
      ),
      sorter: (a, b) => a.name.localeCompare(b.name),
    },
    {
      title: 'Nós',
      dataIndex: 'nodes',
      key: 'nodes',
      width: 200,
      render: (nodes: string[]) => (
        <Space size={[4, 4]} wrap>
          {nodes?.slice(0, 3).map((node, idx) => (
            <Tag key={idx}>{node}</Tag>
          ))}
          {nodes?.length > 3 && (
            <Tooltip title={nodes.slice(3).join(', ')}>
              <Tag>+{nodes.length - 3}</Tag>
            </Tooltip>
          )}
        </Space>
      ),
    },
    {
      title: 'Datacenter',
      dataIndex: 'datacenter',
      key: 'datacenter',
      width: 150,
      render: (dc) => <Tag color="blue">{dc}</Tag>,
    },
    {
      title: 'Tags',
      dataIndex: 'tags',
      key: 'tags',
      width: 250,
      render: (tags: string[]) =>
        tags?.length ? (
          <Space size={[4, 4]} wrap>
            {tags.slice(0, 3).map((tag, idx) => (
              <Tag key={idx}>{tag}</Tag>
            ))}
            {tags.length > 3 && (
              <Tooltip title={tags.slice(3).join(', ')}>
                <Tag>+{tags.length - 3}</Tag>
              </Tooltip>
            )}
          </Space>
        ) : (
          '-'
        ),
    },
    {
      title: 'Número de Instâncias',
      dataIndex: 'instance_count',
      key: 'instance_count',
      width: 160,
      align: 'center',
      sorter: (a, b) => (a.instance_count || 0) - (b.instance_count || 0),
      render: (count) => (
        <Statistic
          value={count || 0}
          valueStyle={{ fontSize: 16 }}
          prefix={<CloudOutlined />}
        />
      ),
    },
    {
      title: 'Instâncias Saudáveis',
      dataIndex: 'checks_passing',
      key: 'checks_passing',
      width: 180,
      align: 'center',
      sorter: (a, b) => (a.checks_passing || 0) - (b.checks_passing || 0),
      render: (passing) => (
        <Statistic
          value={passing || 0}
          valueStyle={{ fontSize: 16, color: '#52c41a' }}
          prefix={<CheckCircleOutlined />}
        />
      ),
    },
    {
      title: 'Instâncias com Problemas',
      dataIndex: 'checks_critical',
      key: 'checks_critical',
      width: 200,
      align: 'center',
      sorter: (a, b) => (a.checks_critical || 0) - (b.checks_critical || 0),
      render: (critical) => (
        <Statistic
          value={critical || 0}
          valueStyle={{ fontSize: 16, color: critical > 0 ? '#ff4d4f' : undefined }}
          prefix={<CloseCircleOutlined />}
        />
      ),
    },
    {
      title: 'Status da Instância',
      key: 'status',
      width: 150,
      render: (_, record) => {
        const total = record.instance_count || 0;
        const passing = record.checks_passing || 0;
        const critical = record.checks_critical || 0;

        if (total === 0) return <Tag>Sem instâncias</Tag>;
        if (critical > 0) return <Tag color="red">Com problemas</Tag>;
        if (passing === total) return <Tag color="green">Todas saudáveis</Tag>;
        return <Tag color="orange">Parcialmente saudável</Tag>;
      },
    },
    {
      title: 'Ações',
      key: 'actions',
      fixed: 'right',
      width: 80,
      render: (_, record) => (
        <Tooltip title="Ver instâncias">
          <Button
            type="link"
            size="small"
            icon={<InfoCircleOutlined />}
            onClick={() => handleServiceClick(record.name)}
          />
        </Tooltip>
      ),
    },
  ];

  const columns = React.useMemo(() => {
    return baseColumns.map((col) => {
      const key = col.key as string;
      const width = columnWidths[key] || col.width;
      return {
        ...col,
        width,
        onHeaderCell: (col: any) => ({
          width,
          onResize: handleResize(key),
        }),
      };
    });
  }, [baseColumns, columnWidths, handleResize]);

  return (
    <PageContainer
      header={{
        title: 'Grupos de Serviços',
        subTitle: 'Visão agrupada dos serviços registrados no Consul',
      }}
    >
      <Space direction="vertical" size="middle" style={{ width: '100%' }}>
        {/* Summary Cards */}
        <Card>
          <Space size="large" wrap>
            <Statistic
              title="Grupos de Serviços"
              value={summary.total}
              prefix={<CloudOutlined />}
              valueStyle={{ color: '#3f8600' }}
            />
            <Statistic
              title="Total de Instâncias"
              value={summary.totalInstances}
              prefix={<CloudOutlined />}
            />
            <Statistic
              title="Instâncias Saudáveis"
              value={summary.healthy}
              prefix={<CheckCircleOutlined />}
              valueStyle={{ color: '#52c41a' }}
            />
            <Statistic
              title="Instâncias com Problemas"
              value={summary.unhealthy}
              prefix={<CloseCircleOutlined />}
              valueStyle={{ color: summary.unhealthy > 0 ? '#ff4d4f' : undefined }}
            />
          </Space>
        </Card>

        {/* Actions */}
        <Card size="small">
          <Space wrap>
            <Button
              icon={<ReloadOutlined />}
              onClick={() => actionRef.current?.reload()}
            >
              Atualizar
            </Button>
          </Space>
        </Card>

        {/* Table */}
        <ProTable<ServiceGroupItem>
          rowKey="name"
          columns={columns}
          search={false}
          actionRef={actionRef}
          request={requestHandler}
          components={{
            header: {
              cell: ResizableTitle,
            },
          }}
          pagination={{
            defaultPageSize: 20,
            showSizeChanger: true,
            pageSizeOptions: ['10', '20', '30', '50', '100'],
          }}
          scroll={{ x: 'max-content' }}
          locale={{ emptyText: 'Nenhum grupo de serviço disponível' }}
          options={{ density: true, fullScreen: true, reload: false, setting: false }}
        />
      </Space>
    </PageContainer>
  );
};

export default ServiceGroups;
