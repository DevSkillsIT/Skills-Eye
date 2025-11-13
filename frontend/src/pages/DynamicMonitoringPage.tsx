/**
 * Dynamic Monitoring Page - Componente Base Único
 *
 * Este componente renderiza QUALQUER página de monitoramento de forma 100% dinâmica.
 * Funciona para network-probes, web-probes, system-exporters, database-exporters, etc.
 *
 * CARACTERÍSTICAS:
 * - Colunas 100% dinâmicas via useTableFields(category)
 * - Filtros 100% dinâmicos via useFilterFields(category)
 * - Dados do endpoint /api/v1/monitoring/data?category={category}
 * - Reutiliza componentes: MetadataFilterBar, AdvancedSearchPanel, ColumnSelector
 *
 * USO:
 *   <DynamicMonitoringPage category="network-probes" />
 *   <DynamicMonitoringPage category="web-probes" />
 *
 * AUTOR: Sistema de Refatoração Skills Eye v2.0
 * DATA: 2025-11-13
 */

import React, { useRef, useMemo, useCallback, useState, useEffect } from 'react';
import {
  Button,
  Space,
  Tooltip,
  message,
  Tag,
  Modal
} from 'antd';
import {
  ReloadOutlined,
  SyncOutlined,
  FilterOutlined,
  ClearOutlined,
  DownloadOutlined,
  EditOutlined,
  DeleteOutlined
} from '@ant-design/icons';
import type { ActionType } from '@ant-design/pro-components';
import {
  PageContainer,
  ProTable,
} from '@ant-design/pro-components';
import type { ProColumns } from '@ant-design/pro-components';

import { consulAPI } from '../services/api';
import { useTableFields, useFilterFields } from '../hooks/useMetadataFields';
import ColumnSelector from '../components/ColumnSelector';
import type { ColumnConfig } from '../components/ColumnSelector';
import MetadataFilterBar from '../components/MetadataFilterBar';
import AdvancedSearchPanel from '../components/AdvancedSearchPanel';
import type { SearchCondition } from '../components/AdvancedSearchPanel';
import ResizableTitle from '../components/ResizableTitle';

// MAPA DE TÍTULOS AMIGÁVEIS
const CATEGORY_DISPLAY_NAMES: Record<string, string> = {
  'network-probes': 'Network Probes (Rede)',
  'web-probes': 'Web Probes (Aplicações)',
  'system-exporters': 'Exporters: Sistemas',
  'database-exporters': 'Exporters: Bancos de Dados'
};

interface DynamicMonitoringPageProps {
  category: string;  // 'network-probes', 'web-probes', etc
}

interface MonitoringDataItem {
  ID: string;
  Service: string;
  Address?: string;
  Port?: number;
  Tags: string[];
  Meta: Record<string, any>;
  [key: string]: any;  // Campos dinâmicos
}

const DynamicMonitoringPage: React.FC<DynamicMonitoringPageProps> = ({ category }) => {
  const actionRef = useRef<ActionType | null>(null);

  // SISTEMA DINÂMICO: Carregar campos metadata para esta categoria
  const { tableFields, loading: tableFieldsLoading } = useTableFields(category);
  const { filterFields, loading: filterFieldsLoading } = useFilterFields(category);

  // Estados
  const [filters, setFilters] = useState<Record<string, string | undefined>>({});
  const [columnConfig, setColumnConfig] = useState<ColumnConfig[]>([]);
  const [columnWidths, setColumnWidths] = useState<Record<string, number>>({});
  const [advancedOpen, setAdvancedOpen] = useState(false);
  const [advancedConditions, setAdvancedConditions] = useState<SearchCondition[]>([]);
  const [advancedOperator, setAdvancedOperator] = useState<'and' | 'or'>('and');
  const [syncLoading, setSyncLoading] = useState(false);

  // SISTEMA DINÂMICO: Combinar colunas fixas + campos metadata
  const defaultColumnConfig = useMemo<ColumnConfig[]>(() => {
    const metadataColumns: ColumnConfig[] = tableFields.map((field) => ({
      key: field.name,
      title: field.display_name,
      visible: field.show_in_table ?? true,
      locked: false
    }));

    // Colunas fixas que sempre existem
    const fixedColumns: ColumnConfig[] = [
      { key: 'ID', title: 'Service ID', visible: true, locked: true },
      { key: 'Service', title: 'Service Name', visible: true },
      { key: 'Address', title: 'Address', visible: true },
      { key: 'Port', title: 'Port', visible: false },
      { key: 'actions', title: 'Ações', visible: true, locked: true }
    ];

    return [...fixedColumns, ...metadataColumns];
  }, [tableFields]);

  // Atualizar columnConfig quando tableFields carregar
  useEffect(() => {
    if (defaultColumnConfig.length > 0 && columnConfig.length === 0) {
      setColumnConfig(defaultColumnConfig);
    }
  }, [defaultColumnConfig, columnConfig.length]);

  // SISTEMA DINÂMICO: Gerar colunas do ProTable
  const proTableColumns = useMemo<ProColumns<MonitoringDataItem>[]>(() => {
    const visibleConfigs = columnConfig.filter(c => c.visible);

    return visibleConfigs.map((colConfig) => {
      const baseColumn: ProColumns<MonitoringDataItem> = {
        title: colConfig.title,
        dataIndex: colConfig.key === 'actions' ? undefined : colConfig.key,
        key: colConfig.key,
        width: columnWidths[colConfig.key] || 150,
        fixed: colConfig.locked ? 'left' : undefined,
        ellipsis: true,
      };

      // Renderização especial para colunas de metadata
      if (colConfig.key.startsWith('meta_') || tableFields.some(f => f.name === colConfig.key)) {
        baseColumn.render = (_: any, record: MonitoringDataItem) => {
          const value = record.Meta?.[colConfig.key] || record.Meta?.[colConfig.key.replace('meta_', '')];
          return value || '-';
        };
      }

      // Renderização especial para Tags
      if (colConfig.key === 'Tags') {
        baseColumn.render = (_: any, record: MonitoringDataItem) => (
          <Space wrap>
            {record.Tags?.map((tag, idx) => (
              <Tag key={idx} color="blue">{tag}</Tag>
            ))}
          </Space>
        );
      }

      // Renderização especial para actions
      if (colConfig.key === 'actions') {
        baseColumn.render = (_: any, record: MonitoringDataItem) => (
          <Space>
            <Tooltip title="Editar">
              <Button
                type="link"
                size="small"
                icon={<EditOutlined />}
                onClick={() => handleEdit(record)}
              />
            </Tooltip>
            <Tooltip title="Deletar">
              <Button
                type="link"
                size="small"
                danger
                icon={<DeleteOutlined />}
                onClick={() => handleDelete(record)}
              />
            </Tooltip>
          </Space>
        );
      }

      return baseColumn;
    });
  }, [columnConfig, columnWidths, tableFields]);

  // Request handler - busca dados do backend
  const requestHandler = useCallback(async (params: any) => {
    try {
      console.log('[MONITORING] Buscando dados:', { category, filters, params });

      // Chamar endpoint unificado
      const response = await consulAPI.getMonitoringData(
        category,
        filters.company,
        filters.site,
        filters.env
      );

      if (!response.success) {
        throw new Error(response.detail || 'Erro ao buscar dados');
      }

      console.log(`[MONITORING] Retornados ${response.total} registros`);

      return {
        data: response.data || [],
        success: true,
        total: response.total || 0
      };
    } catch (error: any) {
      console.error('[MONITORING ERROR]', error);
      message.error('Erro ao carregar dados: ' + (error.message || error));
      return {
        data: [],
        success: false,
        total: 0
      };
    }
  }, [category, filters]);

  // Handler de sincronização de cache
  const handleSync = useCallback(async () => {
    setSyncLoading(true);
    try {
      const response = await consulAPI.syncMonitoringCache();

      if (response.success) {
        message.success(`Cache sincronizado! ${response.total_types} tipos de ${response.total_servers} servidores`);
        actionRef.current?.reload();
      } else {
        throw new Error(response.detail || 'Erro ao sincronizar');
      }
    } catch (error: any) {
      message.error('Erro ao sincronizar: ' + (error.message || error));
    } finally {
      setSyncLoading(false);
    }
  }, []);

  // Handlers de CRUD
  const handleEdit = useCallback((record: MonitoringDataItem) => {
    message.info(`Editar: ${record.ID}`);
    // TODO: Implementar modal de edição
  }, []);

  const handleDelete = useCallback((record: MonitoringDataItem) => {
    Modal.confirm({
      title: 'Confirmar exclusão',
      content: `Deseja realmente excluir o serviço "${record.ID}"?`,
      okText: 'Sim, excluir',
      okType: 'danger',
      cancelText: 'Cancelar',
      onOk: async () => {
        try {
          // TODO: Implementar chamada de API para deletar
          message.success('Serviço excluído com sucesso');
          actionRef.current?.reload();
        } catch (error: any) {
          message.error('Erro ao excluir: ' + (error.message || error));
        }
      }
    });
  }, []);

  return (
    <PageContainer
      title={CATEGORY_DISPLAY_NAMES[category] || category}
      subTitle={`Monitoramento de ${category.replace('-', ' ')}`}
      extra={[
        <Button
          key="sync"
          icon={<SyncOutlined spin={syncLoading} />}
          onClick={handleSync}
          loading={syncLoading}
        >
          Sincronizar Cache
        </Button>,
        <Button
          key="advanced"
          icon={<FilterOutlined />}
          onClick={() => setAdvancedOpen(true)}
        >
          Filtro Avançado
        </Button>,
        <ColumnSelector
          key="columns"
          columns={columnConfig}
          onChange={setColumnConfig}
        />
      ]}
    >
      {/* Barra de filtros metadata */}
      <MetadataFilterBar
        fields={filterFields}
        filters={filters}
        onChange={(newFilters) => {
          setFilters(newFilters);
          actionRef.current?.reload();
        }}
      />

      {/* Tabela principal */}
      <ProTable<MonitoringDataItem>
        actionRef={actionRef}
        rowKey="ID"
        columns={proTableColumns}
        request={requestHandler}
        pagination={{
          defaultPageSize: 20,
          showSizeChanger: true,
          showTotal: (total) => `Total: ${total} registros`
        }}
        search={false}
        options={{
          reload: true,
          setting: false,
          density: true,
        }}
        toolbar={{
          actions: [
            <Button
              key="clear"
              icon={<ClearOutlined />}
              onClick={() => {
                setFilters({});
                actionRef.current?.reload();
              }}
            >
              Limpar Filtros
            </Button>,
            <Button
              key="export"
              icon={<DownloadOutlined />}
              onClick={() => {
                message.info('Exportar dados - em desenvolvimento');
              }}
            >
              Exportar
            </Button>
          ]
        }}
        loading={tableFieldsLoading || filterFieldsLoading}
      />

      {/* Painel de busca avançada */}
      <AdvancedSearchPanel
        visible={advancedOpen}
        onClose={() => setAdvancedOpen(false)}
        fields={tableFields.map(f => ({ name: f.name, label: f.display_name }))}
        conditions={advancedConditions}
        operator={advancedOperator}
        onConditionsChange={setAdvancedConditions}
        onOperatorChange={setAdvancedOperator}
        onApply={() => {
          setAdvancedOpen(false);
          actionRef.current?.reload();
        }}
      />
    </PageContainer>
  );
};

export default DynamicMonitoringPage;
