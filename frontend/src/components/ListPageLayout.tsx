/**
 * Layout compartilhado para páginas de listagem
 * Fornece estrutura consistente com filtros, busca, ações e tabela
 */
import React, { ReactNode } from 'react';
import { Card, Space, Button, Input, Statistic } from 'antd';
import {
  FilterOutlined,
  ClearOutlined,
  DownloadOutlined,
  PlusOutlined,
  DeleteOutlined,
  ReloadOutlined,
} from '@ant-design/icons';
import { PageContainer, ProTable } from '@ant-design/pro-components';
import type { ActionType, ProTableProps } from '@ant-design/pro-components';
import MetadataFilterBar from './MetadataFilterBar';
import AdvancedSearchPanel, { type SearchCondition } from './AdvancedSearchPanel';
import ColumnSelector, { type ColumnConfig } from './ColumnSelector';
import type { MetadataFilters } from '../services/api';

const { Search } = Input;

export interface StatisticCardItem {
  title: string;
  value: number | string;
  prefix?: ReactNode;
  suffix?: ReactNode;
  valueStyle?: React.CSSProperties;
}

export interface ListPageLayoutProps<T> {
  // PageContainer props
  pageTitle: string;
  pageSubTitle?: string;

  // Summary/Statistics (optional)
  statistics?: StatisticCardItem[];
  statisticsExtra?: ReactNode; // Extra content for statistics card

  // Filters
  filters?: MetadataFilters;
  metadataOptions?: any;
  onFiltersChange?: (filters: MetadataFilters) => void;
  onResetFilters?: () => void;
  extraFilters?: ReactNode; // Node selector, etc.

  // Search
  searchValue?: string;
  searchPlaceholder?: string;
  onSearchChange?: (value: string) => void;
  onSearch?: () => void;

  // Advanced Search
  showAdvancedSearch?: boolean;
  advancedSearchFields?: Array<{ label: string; value: string; type?: string }>;
  advancedConditions?: SearchCondition[];
  advancedOperator?: 'and' | 'or';
  onAdvancedSearch?: (conditions: SearchCondition[], operator: string) => void;
  onClearAdvancedSearch?: () => void;

  // Column Selector
  columnConfig?: ColumnConfig[];
  onColumnConfigChange?: (config: ColumnConfig[]) => void;
  columnStorageKey?: string;

  // Actions
  onExport?: () => void;
  onCreate?: () => void;
  onBatchDelete?: () => void;
  onRefresh?: () => void;
  customActions?: ReactNode[];

  // Selection
  selectedCount?: number;

  // Table
  tableProps: Omit<ProTableProps<T, any>, 'search'>;
  actionRef?: React.MutableRefObject<ActionType | undefined>;

  // Extra content (above or below filters)
  extraContentTop?: ReactNode;
  extraContentBottom?: ReactNode;
}

function ListPageLayout<T extends Record<string, any>>({
  pageTitle,
  pageSubTitle,
  statistics,
  statisticsExtra,
  filters,
  metadataOptions,
  onFiltersChange,
  onResetFilters,
  extraFilters,
  searchValue,
  searchPlaceholder = 'Buscar...',
  onSearchChange,
  onSearch,
  showAdvancedSearch = false,
  advancedSearchFields = [],
  advancedConditions = [],
  advancedOperator = 'and',
  onAdvancedSearch,
  onClearAdvancedSearch,
  columnConfig,
  onColumnConfigChange,
  columnStorageKey,
  onExport,
  onCreate,
  onBatchDelete,
  onRefresh,
  customActions = [],
  selectedCount = 0,
  tableProps,
  actionRef,
  extraContentTop,
  extraContentBottom,
}: ListPageLayoutProps<T>) {
  const [advancedOpen, setAdvancedOpen] = React.useState(false);

  return (
    <PageContainer
      header={{
        title: pageTitle,
        subTitle: pageSubTitle,
      }}
    >
      <Space direction="vertical" size="middle" style={{ width: '100%' }}>
        {/* Extra content top */}
        {extraContentTop}

        {/* Statistics Card */}
        {statistics && statistics.length > 0 && (
          <Card>
            <Space size="large" wrap>
              {statistics.map((stat, index) => (
                <Statistic
                  key={index}
                  title={stat.title}
                  value={stat.value}
                  prefix={stat.prefix}
                  suffix={stat.suffix}
                  valueStyle={stat.valueStyle}
                />
              ))}
              {statisticsExtra}
            </Space>
          </Card>
        )}

        {/* Filters and Actions Card */}
        <Card size="small">
          <Space direction="vertical" size="middle" style={{ width: '100%' }}>
            {/* Metadata Filters */}
            {(filters !== undefined || extraFilters) && (
              <Space wrap>
                {filters !== undefined && metadataOptions && onFiltersChange && (
                  <MetadataFilterBar
                    value={filters}
                    options={metadataOptions}
                    onChange={onFiltersChange}
                    onReset={onResetFilters}
                    extra={extraFilters}
                  />
                )}
                {!filters && extraFilters && extraFilters}
              </Space>
            )}

            {/* Search and Action Buttons */}
            <Space wrap style={{ width: '100%', justifyContent: 'space-between' }}>
              {/* Left side - Search and Filters */}
              <Space wrap>
                {onSearchChange && onSearch && (
                  <Search
                    placeholder={searchPlaceholder}
                    allowClear
                    enterButton
                    style={{ width: 300 }}
                    value={searchValue}
                    onChange={(e) => onSearchChange(e.target.value)}
                    onSearch={onSearch}
                  />
                )}

                {showAdvancedSearch && onAdvancedSearch && (
                  <Button
                    icon={<FilterOutlined />}
                    onClick={() => setAdvancedOpen(!advancedOpen)}
                  >
                    Busca Avancada
                    {advancedConditions.length > 0 && ` (${advancedConditions.length})`}
                  </Button>
                )}

                {advancedConditions.length > 0 && onClearAdvancedSearch && (
                  <Button
                    icon={<ClearOutlined />}
                    onClick={onClearAdvancedSearch}
                  >
                    Limpar Filtros Avancados
                  </Button>
                )}
              </Space>

              {/* Right side - Action Buttons */}
              <Space wrap>
                {onRefresh && (
                  <Button
                    icon={<ReloadOutlined />}
                    onClick={onRefresh}
                  >
                    Atualizar
                  </Button>
                )}

                {columnConfig && onColumnConfigChange && (
                  <ColumnSelector
                    columns={columnConfig}
                    onChange={onColumnConfigChange}
                    storageKey={columnStorageKey}
                  />
                )}

                {onExport && (
                  <Button
                    icon={<DownloadOutlined />}
                    onClick={onExport}
                  >
                    Exportar CSV
                  </Button>
                )}

                {onBatchDelete && selectedCount > 0 && (
                  <Button
                    danger
                    icon={<DeleteOutlined />}
                    onClick={onBatchDelete}
                  >
                    Remover Selecionados ({selectedCount})
                  </Button>
                )}

                {onCreate && (
                  <Button
                    type="primary"
                    icon={<PlusOutlined />}
                    onClick={onCreate}
                  >
                    Novo
                  </Button>
                )}

                {customActions}
              </Space>
            </Space>

            {/* Advanced Search Panel */}
            {advancedOpen && showAdvancedSearch && onAdvancedSearch && (
              <AdvancedSearchPanel
                availableFields={advancedSearchFields}
                onSearch={(conditions, operator) => {
                  onAdvancedSearch(conditions, operator);
                  setAdvancedOpen(false);
                }}
                onClear={onClearAdvancedSearch}
                initialConditions={advancedConditions}
                initialLogicalOperator={advancedOperator}
              />
            )}
          </Space>
        </Card>

        {/* Extra content bottom */}
        {extraContentBottom}

        {/* Table */}
        <ProTable<T>
          {...tableProps}
          search={false}
          actionRef={actionRef}
        />
      </Space>
    </PageContainer>
  );
}

export default ListPageLayout;
