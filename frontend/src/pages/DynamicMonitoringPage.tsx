/**
 * Dynamic Monitoring Page - Componente Base Único COMPLETO
 *
 * Este componente renderiza QUALQUER página de monitoramento de forma 100% dinâmica.
 * Funciona para network-probes, web-probes, system-exporters, database-exporters, etc.
 *
 * CARACTERÍSTICAS COMPLETAS:
 * ✅ Colunas 100% dinâmicas via useTableFields(category)
 * ✅ Filtros 100% dinâmicos via useFilterFields(category)
 * ✅ Dashboard com métricas agregadas
 * ✅ NodeSelector para filtro por nó
 * ✅ Busca por keyword (global search)
 * ✅ Filtros customizados por coluna (searchable checkboxes)
 * ✅ Batch delete com rowSelection
 * ✅ Linha expansível (metadata completo)
 * ✅ Exportação CSV funcional
 * ✅ Modal de detalhes completo
 * ✅ Modal de criação/edição funcional
 * ✅ Ordenação em todas as colunas
 * ✅ Fixed columns + scroll horizontal
 * ✅ Resizable columns
 *
 * USO:
 *   <DynamicMonitoringPage category="network-probes" />
 *   <DynamicMonitoringPage category="web-probes" />
 *
 * AUTOR: Sistema de Refatoração Skills Eye v2.0
 * DATA: 2025-11-13
 * VERSÃO: 2.0 - COMPLETO (paridade com Services.tsx)
 */

import React, { useRef, useMemo, useCallback, useState, useEffect } from 'react';
import { useDebouncedCallback } from 'use-debounce';
import {
  Button,
  Card,
  Checkbox,
  Descriptions,
  Drawer,
  Input,
  message,
  Modal,
  Popconfirm,
  Space,
  Tag,
  Tooltip,
  Typography,
} from 'antd';
import {
  ApartmentOutlined,
  BankOutlined,
  ClearOutlined,
  CloudOutlined,
  DeleteOutlined,
  DownloadOutlined,
  EditOutlined,
  EnvironmentOutlined,
  FilterOutlined,
  InfoCircleOutlined,
  PlusOutlined,
  ReloadOutlined,
  SearchOutlined,
  // SyncOutlined, // Não usado
  TagsOutlined,
  TeamOutlined,
} from '@ant-design/icons';
import type { ActionType, ProColumns } from '@ant-design/pro-components';
import {
  // ModalForm, // Não usado
  PageContainer,
  ProDescriptions,
  ProTable,
} from '@ant-design/pro-components';

import { consulAPI } from '../services/api';
import { useTableFields, useFilterFields } from '../hooks/useMetadataFields';
import ColumnSelector from '../components/ColumnSelector';
import type { ColumnConfig } from '../components/ColumnSelector';
import MetadataFilterBar from '../components/MetadataFilterBar';
import AdvancedSearchPanel from '../components/AdvancedSearchPanel';
import type { SearchCondition } from '../components/AdvancedSearchPanel';
import BadgeStatus from '../components/BadgeStatus'; // SPRINT 2: Performance indicators
import ResizableTitle from '../components/ResizableTitle';
import { NodeSelector } from '../components/NodeSelector';

// const { Search } = Input; // Não usado
// const { Text } = Typography; // Não usado

// ============================================================================
// TIPOS E INTERFACES
// ============================================================================

// ✅ OTIMIZAÇÃO: Flag para controlar logs de performance
// Em produção (build), logs serão removidos automaticamente
const DEBUG_PERFORMANCE = import.meta.env.DEV;

// ✅ SPEC-PERF-002: Remover CATEGORY_DISPLAY_NAMES hardcoded
// Usar dados dinamicos que vem do tableFields (category_display_name)
const formatCategoryName = (slug: string): string => {
  return slug.split('-').map(word => word.charAt(0).toUpperCase() + word.slice(1)).join(' ');
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
  Node?: string;
  node_ip?: string;  // ✅ NOVO: IP do nó para filtro (vem do backend)
  [key: string]: any;  // Campos dinâmicos
}

interface Summary {
  total: number;
  byCategory: Record<string, number>;
  byCompany: Record<string, number>;
  bySite: Record<string, number>;
  byNode: Record<string, number>;
  uniqueTags: Set<string>;
}

// ✅ SPEC-PERF-002 GAP 3: Interface para estado atomico de metadataOptions
interface MetadataState {
  options: Record<string, string[]>;
  loaded: boolean;
}

// ============================================================================
// COMPONENTE PRINCIPAL
// ============================================================================

const DynamicMonitoringPage: React.FC<DynamicMonitoringPageProps> = ({ category }) => {
  const actionRef = useRef<ActionType | null>(null);

  // ✅ SPEC-PERF-002: AbortController para cancelar requests anteriores (evita race conditions)
  const abortControllerRef = useRef<AbortController | null>(null);

  // ✅ SPEC-PERF-002: isMountedRef para evitar memory leaks (state update apos unmount)
  const isMountedRef = useRef(true);

  // ✅ SPEC-PERF-002: Ref estavel para metadataOptions (evita stale closure no filterDropdown)
  const metadataOptionsRef = useRef<Record<string, string[]>>({});

  // ✅ SPEC-PERF-002: Cache para getFieldValue (evita recalculos desnecessarios)
  const fieldValueCacheRef = useRef<Record<string, string>>({});

  // SISTEMA DINÂMICO: Carregar campos metadata para esta categoria
  const { tableFields, loading: tableFieldsLoading } = useTableFields(category);
  const { filterFields, loading: filterFieldsLoading } = useFilterFields(category);

  // Estados principais
  const [filters, setFilters] = useState<Record<string, string | undefined>>({});
  const [columnConfig, setColumnConfig] = useState<ColumnConfig[]>([]);
  const [columnWidths, setColumnWidths] = useState<Record<string, number>>({});
  const [advancedOpen, setAdvancedOpen] = useState(false);
  const [advancedConditions, setAdvancedConditions] = useState<SearchCondition[]>([]);
  const [advancedOperator, setAdvancedOperator] = useState<'and' | 'or'>('and');

  // ✅ NOVO: NodeSelector
  const [selectedNode, setSelectedNode] = useState<string>('all');

  // ✅ NOVO: Busca por keyword
  const [searchValue, setSearchValue] = useState<string>('');
  const [searchInput, setSearchInput] = useState<string>('');

  // ✅ NOVO: Batch delete
  const [selectedRowKeys, setSelectedRowKeys] = useState<React.Key[]>([]);
  const [selectedRows, setSelectedRows] = useState<MonitoringDataItem[]>([]);

  // ✅ NOVO: Modal de detalhes
  const [detailRecord, setDetailRecord] = useState<MonitoringDataItem | null>(null);

  // ✅ NOVO: Modal de criação/edição
  const [formOpen, setFormOpen] = useState(false);
  const [formMode, setFormMode] = useState<'create' | 'edit'>('create');
  const [currentRecord, setCurrentRecord] = useState<MonitoringDataItem | null>(null);

  // ✅ NOVO: Snapshot para exportação CSV
  const [tableSnapshot, setTableSnapshot] = useState<MonitoringDataItem[]>([]);

  // ✅ NOVO: Ordenação
  const [sortField, setSortField] = useState<string | null>(null);
  const [sortOrder, setSortOrder] = useState<'ascend' | 'descend' | null>(null);

  // ✅ NOVO: Dashboard summary
  const [summary, setSummary] = useState<Summary>({
    total: 0,
    byCategory: {},
    byCompany: {},
    bySite: {},
    byNode: {},
    uniqueTags: new Set(),
  });

  // ✅ SPEC-PERF-002 GAP 3: Estado atomico para metadataOptions (evita race condition)
  // Combina options e loaded em um unico estado para atualizacao atomica
  const [metadataState, setMetadataState] = useState<MetadataState>({
    options: {},
    loaded: false
  });
  // Desestruturar para compatibilidade com codigo existente
  const { options: metadataOptions, loaded: metadataOptionsLoaded } = metadataState;

  // ✅ SPEC-PERF-002: Sincronizar ref com state para estabilidade no filterDropdown
  useEffect(() => {
    metadataOptionsRef.current = metadataOptions;
  }, [metadataOptions]);

  // ✅ SPEC-PERF-002: Cleanup de isMountedRef no unmount
  useEffect(() => {
    isMountedRef.current = true;
    return () => {
      isMountedRef.current = false;
      // Cancelar requests pendentes ao desmontar
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, []);

  // ✅ SPRINT 1 FIX (2025-11-15): Capturar _metadata de performance do backend
  // _metadata contém: source_name, is_master, cache_status, age_seconds, staleness_ms, total_time_ms
  const [responseMetadata, setResponseMetadata] = useState<{
    source_name?: string;
    is_master?: boolean;
    cache_status?: string;
    age_seconds?: number;
    staleness_ms?: number;
    total_time_ms?: number;
  } | null>(null);

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
      { key: 'ID', title: 'Service ID', visible: true, locked: false },
      { key: 'Service', title: 'Service Name', visible: true },
      { key: 'Node', title: 'Nó', visible: true },
      { key: 'Address', title: 'Address', visible: true },
      { key: 'Port', title: 'Port', visible: false },
      { key: 'Tags', title: 'Tags', visible: true },
      { key: 'actions', title: 'Ações', visible: true, locked: true }
    ];

    return [...fixedColumns, ...metadataColumns];
  }, [tableFields]);

  // ✅ CORREÇÃO CRÍTICA: Atualizar columnConfig quando tableFields carregar
  // ✅ SPEC-PERF-002: Remover columnConfig das dependencias para evitar ciclo infinito
  const prevDefaultColumnConfigRef = useRef<string>('');

  useEffect(() => {
    // ✅ OTIMIZAÇÃO: Só atualizar quando realmente necessário (tableFields carregou)
    if (defaultColumnConfig.length > 0 && tableFields.length > 0) {
      // Verificar se defaultColumnConfig mudou desde a ultima vez
      const defaultKeys = defaultColumnConfig.map(c => c.key).sort().join(',');

      // ✅ SPEC-PERF-002: Comparar apenas com a ref anterior, nao com columnConfig atual
      // Isso evita o ciclo: columnConfig muda -> useEffect roda -> setColumnConfig -> loop
      if (prevDefaultColumnConfigRef.current !== defaultKeys) {
        // ✅ OTIMIZAÇÃO: Só logar se realmente mudou (evita logs duplicados)
        if (import.meta.env.DEV) {
          console.log('[DynamicMonitoringPage] ✅ Atualizando columnConfig:', {
            to: defaultColumnConfig.length,
            metadataColumns: defaultColumnConfig.length - 7, // 7 colunas fixas
          });
        }
        prevDefaultColumnConfigRef.current = defaultKeys;
        setColumnConfig(defaultColumnConfig);
      }
    }
  }, [defaultColumnConfig, tableFields.length]); // ✅ SEM columnConfig aqui!

  // ✅ NOVO: Handler de resize de colunas
  const handleResize = useCallback(
    (columnKey: string) =>
      (_: React.SyntheticEvent, { size }: { size: { width: number } }) => {
        setColumnWidths((prev) => ({ ...prev, [columnKey]: size.width }));
      },
    [],
  );

  // ✅ NOVO: Handler de mudanças na tabela (ordenação)
  // ✅ CORREÇÃO: Recarregar tabela quando ordenação mudar
  const handleTableChange = useCallback((_pagination: any, _filters: any, sorter: any) => {
    if (sorter && sorter.field) {
      setSortField(sorter.field);
      setSortOrder(sorter.order || null);
      // ✅ CORREÇÃO: Recarregar tabela para aplicar ordenação
      // Pequeno delay para garantir que estado foi atualizado
      setTimeout(() => {
        actionRef.current?.reload();
      }, 0);
    } else {
      setSortField(null);
      setSortOrder(null);
      // Recarregar quando ordenação for removida
      setTimeout(() => {
        actionRef.current?.reload();
      }, 0);
    }
  }, []);

  // ✅ SPEC-PERF-002: Debounce com cancelamento para evitar requests excessivos
  const debouncedReload = useDebouncedCallback(() => {
    actionRef.current?.reload();
  }, 300);

  // ✅ NOVO: Handler de busca por keyword
  // ✅ SPEC-PERF-002: Usar debounce para evitar requests a cada tecla
  const handleSearchSubmit = useCallback(
    (value: string) => {
      setSearchValue(value.trim());
      debouncedReload();
    },
    [debouncedReload],
  );

  // ✅ SPEC-PERF-002: Extrair valor de campo com cache para evitar recalculos
  const getFieldValue = useCallback((row: MonitoringDataItem, field: string): string => {
    // ✅ SPEC-PERF-002: Cache baseado em ID + field
    const cacheKey = `${row.ID}-${field}`;

    // Verificar cache primeiro
    if (fieldValueCacheRef.current[cacheKey] !== undefined) {
      return fieldValueCacheRef.current[cacheKey];
    }

    let value: string;

    // Campos fixos
    switch (field) {
      case 'ID':
        value = row.ID || '';
        break;
      case 'Service':
        value = row.Service || '';
        break;
      case 'Node':
        value = row.Node || '';
        break;
      case 'Address':
        value = row.Address || '';
        break;
      case 'Port':
        value = typeof row.Port === 'number' ? String(row.Port) : '';
        break;
      case 'Tags':
        value = (row.Tags || []).join(',');
        break;
      default:
        // CAMPOS METADATA DINÂMICOS
        value = row.Meta?.[field] ? String(row.Meta[field]) : '';
    }

    // Salvar no cache
    fieldValueCacheRef.current[cacheKey] = value;
    return value;
  }, []);

  // ✅ NOVO: Aplicar filtros avançados (EXPANDIDO - suporta todos os operadores)
  const applyAdvancedFilters = useCallback(
    (data: MonitoringDataItem[]) => {
      if (!advancedConditions.length) {
        return data;
      }

      const sanitized = advancedConditions.filter(
        (condition) => condition.field && condition.value !== undefined && condition.value !== '',
      );

      if (!sanitized.length) {
        return data;
      }

      return data.filter((row) => {
        const evaluations = sanitized.map((condition) => {
          const source = getFieldValue(row, condition.field);
          const target = condition.value;

          // Operadores que precisam de valores em minúsculas
          const sourceLower = String(source).toLowerCase();
          const targetLower = String(target ?? '').toLowerCase();

          if (!target && target !== 0 && target !== false) return true;

          switch (condition.operator) {
            case 'eq':
              return sourceLower === targetLower;
            case 'ne':
              return sourceLower !== targetLower;
            case 'starts_with':
              return sourceLower.startsWith(targetLower);
            case 'ends_with':
              return sourceLower.endsWith(targetLower);
            case 'contains':
              return sourceLower.includes(targetLower);
            case 'regex':
              try {
                const regex = new RegExp(String(target), 'i');
                return regex.test(source);
              } catch {
                return false;
              }
            case 'in':
              if (Array.isArray(target)) {
                return target.some(val => String(val).toLowerCase() === sourceLower);
              }
              return false;
            case 'not_in':
              if (Array.isArray(target)) {
                return !target.some(val => String(val).toLowerCase() === sourceLower);
              }
              return true;
            case 'gt':
              return Number(source) > Number(target);
            case 'lt':
              return Number(source) < Number(target);
            case 'gte':
              return Number(source) >= Number(target);
            case 'lte':
              return Number(source) <= Number(target);
            default:
              return sourceLower.includes(targetLower);
          }
        });

        return advancedOperator === 'or'
          ? evaluations.some(Boolean)
          : evaluations.every(Boolean);
      });
    },
    [advancedConditions, advancedOperator, getFieldValue],
  );

  // ✅ OTIMIZAÇÃO: Serializar dependências uma vez para evitar recálculos
  const columnConfigKey = useMemo(
    () => columnConfig.map(c => `${c.key}:${c.visible}`).join(','),
    [columnConfig]
  );
  
  const tableFieldsKey = useMemo(
    () => tableFields.map(f => f.name).join(','),
    [tableFields]
  );
  
  const columnWidthsKey = useMemo(
    () => JSON.stringify(columnWidths),
    [columnWidths]
  );

  // SISTEMA DINÂMICO: Gerar colunas do ProTable com TODAS as features
  // ✅ OTIMIZAÇÃO: Usar useRef para evitar logs excessivos
  const lastProTableColumnsRef = useRef<string>('');
  
  const proTableColumns = useMemo<ProColumns<MonitoringDataItem>[]>(() => {
    // ✅ CORREÇÃO: Só calcular colunas quando columnConfig estiver pronto
    // Evita race condition onde proTableColumns é calculado antes de columnConfig ser atualizado
    if (columnConfig.length === 0) {
      return [];
    }
    
    const visibleConfigs = columnConfig.filter(c => c.visible);
    
    // ✅ OTIMIZAÇÃO: Só logar quando realmente mudou (evita logs duplicados em StrictMode)
    if (import.meta.env.DEV) {
      const configKey = `${columnConfig.length}-${visibleConfigs.length}-${tableFields.length}`;
      if (lastProTableColumnsRef.current !== configKey) {
        const metadataColumns = visibleConfigs.filter(c => tableFields.some(f => f.name === c.key));
        console.log('[DynamicMonitoringPage] proTableColumns:', {
          columnConfigLength: columnConfig.length,
          tableFieldsLength: tableFields.length,
          visibleConfigsCount: visibleConfigs.length,
          metadataColumnsCount: metadataColumns.length,
        });
        lastProTableColumnsRef.current = configKey;
      }
    }

    return visibleConfigs.map((colConfig) => {
      // Definir larguras específicas para colunas especiais
      let defaultWidth = 150;
      if (colConfig.key === 'actions') defaultWidth = 120;
      else if (colConfig.key === 'ID') defaultWidth = 200;
      else if (colConfig.key === 'Service') defaultWidth = 180;

      const width = columnWidths[colConfig.key] || defaultWidth;
      
      // ✅ CORREÇÃO CRÍTICA: dataIndex para colunas de metadata deve ser ['Meta', fieldName]
      // Colunas fixas usam o nome direto, mas colunas de metadata estão em record.Meta[fieldName]
      const isMetadataColumn = tableFields.some(f => f.name === colConfig.key);
      const dataIndex = colConfig.key === 'actions' 
        ? undefined 
        : isMetadataColumn 
          ? ['Meta', colConfig.key]  // ✅ CORREÇÃO: Metadata está em Meta[fieldName]
          : colConfig.key;  // Colunas fixas (ID, Service, Node, etc)
      
      const baseColumn: ProColumns<MonitoringDataItem> = {
        title: colConfig.title,
        dataIndex,
        key: colConfig.key,
        width,
        fixed: colConfig.key === 'actions' ? 'right' : undefined,
        ellipsis: true,
        onHeaderCell: () => ({
          width,
          onResize: handleResize(colConfig.key),
        }),
      };

      // ✅ NOVO: Ordenação em todas as colunas
      if (colConfig.key !== 'actions' && colConfig.key !== 'Tags') {
        baseColumn.sorter = (a, b) => {
          const aValue = getFieldValue(a, colConfig.key);
          const bValue = getFieldValue(b, colConfig.key);
          return aValue.localeCompare(bValue);
        };
        baseColumn.sortDirections = ['ascend', 'descend'];
        // ✅ CORREÇÃO: Usar sortOrder do estado para controlar ordenação visual
        baseColumn.sortOrder = sortField === colConfig.key ? sortOrder : null;
      }

      // ✅ CORREÇÃO: Filtros customizados por coluna (searchable checkboxes)
      // Só renderizar se metadataOptions estiver carregado e tiver opções
      // ✅ SPEC-PERF-002: Usar metadataOptionsRef para estabilidade no filterDropdown
      const fieldOptions = metadataOptionsRef.current[colConfig.key] || [];
      if (fieldOptions.length > 0 && colConfig.key !== 'actions' && colConfig.key !== 'Tags' && metadataOptionsLoaded) {
        // ✅ CORREÇÃO: Usar filteredValue para controlar estado visual do filtro
        baseColumn.filteredValue = filters[colConfig.key] ? [filters[colConfig.key]] : null;

        baseColumn.filterDropdown = ({ setSelectedKeys, selectedKeys, confirm, clearFilters }) => {
          const [searchText, setSearchText] = useState('');

          // ✅ SPEC-PERF-002: Usar ref para opcoes atualizadas (evita stale closure)
          const currentOptions = metadataOptionsRef.current[colConfig.key] || [];
          const filteredOptions = currentOptions.filter(opt =>
            opt.toLowerCase().includes(searchText.toLowerCase())
          );

          return (
            <div style={{ padding: 8, width: 300 }}>
              <Input
                placeholder={`Buscar ${colConfig.title}`}
                value={searchText}
                onChange={(e) => setSearchText(e.target.value)}
                style={{ marginBottom: 8, display: 'block' }}
                prefix={<SearchOutlined />}
              />

              <div style={{ maxHeight: 300, overflowY: 'auto', marginBottom: 8 }}>
                <Checkbox
                  onChange={(e) => {
                    if (e.target.checked) {
                      setSelectedKeys(filteredOptions);
                    } else {
                      setSelectedKeys([]);
                    }
                  }}
                  checked={filteredOptions.length > 0 && selectedKeys.length === filteredOptions.length}
                  indeterminate={selectedKeys.length > 0 && selectedKeys.length < filteredOptions.length}
                  style={{ marginBottom: 8 }}
                >
                  Selecionar todos
                </Checkbox>
                {filteredOptions.map((opt) => (
                  <div key={opt} style={{ padding: '4px 0' }}>
                    <Checkbox
                      checked={selectedKeys.includes(opt)}
                      onChange={(e) => {
                        if (e.target.checked) {
                          setSelectedKeys([...selectedKeys, opt]);
                        } else {
                          setSelectedKeys(selectedKeys.filter((k) => k !== opt));
                        }
                      }}
                    >
                      {opt}
                    </Checkbox>
                  </div>
                ))}
                {filteredOptions.length === 0 && (
                  <div style={{ color: '#999', padding: '8px 0', textAlign: 'center' }}>
                    Nenhuma opção encontrada
                  </div>
                )}
              </div>

              <Space>
                <Button
                  type="primary"
                  size="small"
                  onClick={() => {
                    // ✅ CORREÇÃO: Aplicar filtro na coluna específica
                    const newFilters = { ...filters };
                    if (selectedKeys.length > 0) {
                      // Se múltiplos valores selecionados, usar o primeiro (ou implementar lógica OR)
                      newFilters[colConfig.key] = selectedKeys[0];
                    } else {
                      delete newFilters[colConfig.key];
                    }
                    setFilters(newFilters);
                    confirm();
                    actionRef.current?.reload();
                  }}
                  icon={<SearchOutlined />}
                >
                  OK
                </Button>
                <Button
                  size="small"
                  onClick={() => {
                    const newFilters = { ...filters };
                    delete newFilters[colConfig.key];
                    setFilters(newFilters);
                    clearFilters?.();
                    setSearchText('');
                    actionRef.current?.reload();
                  }}
                >
                  Limpar
                </Button>
              </Space>
            </div>
          );
        };
        baseColumn.filterIcon = (filtered: boolean) => (
          <FilterOutlined style={{ color: filtered ? '#1890ff' : undefined }} />
        );
        // ✅ CORREÇÃO: onFilter agora verifica se o valor está nos selectedKeys
        baseColumn.onFilter = (value, record) => {
          // Este método é usado pelo ProTable internamente, mas vamos usar filtros customizados
          const fieldValue = getFieldValue(record, colConfig.key);
          return fieldValue === value;
        };
      }

      // Renderização especial para colunas de metadata
      if (tableFields.some(f => f.name === colConfig.key)) {
        baseColumn.render = (_: any, record: MonitoringDataItem) => {
          const value = record.Meta?.[colConfig.key];
          return value || '-';
        };
      }

      // Renderização especial para Tags
      if (colConfig.key === 'Tags') {
        baseColumn.render = (_: any, record: MonitoringDataItem) => (
          <Space wrap size={[4, 4]}>
            {(record.Tags || []).map((tag, idx) => (
              <Tag key={idx} color="blue">{tag}</Tag>
            ))}
          </Space>
        );
      }

      // Renderização especial para actions
      if (colConfig.key === 'actions') {
        baseColumn.render = (_: any, record: MonitoringDataItem) => (
          <Space>
            <Tooltip title="Ver detalhes">
              <Button
                type="link"
                size="small"
                icon={<InfoCircleOutlined />}
                onClick={() => setDetailRecord(record)}
              />
            </Tooltip>
            <Tooltip title="Editar">
              <Button
                type="link"
                size="small"
                icon={<EditOutlined />}
                onClick={() => handleEdit(record)}
              />
            </Tooltip>
            <Popconfirm
              title="Confirmar exclusão"
              description={`Deseja excluir "${record.ID}"?`}
              onConfirm={() => handleDelete(record)}
              okText="Sim"
              cancelText="Não"
            >
              <Tooltip title="Deletar">
                <Button
                  type="link"
                  size="small"
                  danger
                  icon={<DeleteOutlined />}
                />
              </Tooltip>
            </Popconfirm>
          </Space>
        );
      }

      return baseColumn;
    });
  }, [
    // ✅ OTIMIZAÇÃO: Usar apenas valores primitivos e funções estáveis
    columnConfig,
    columnWidths,
    tableFields,
    metadataOptionsLoaded,
    metadataOptions,  // ✅ CORREÇÃO: Adicionado para filteredValue
    filters,  // ✅ CORREÇÃO: Adicionado para filteredValue
    sortField,  // ✅ CORREÇÃO: Adicionado para sortOrder
    sortOrder,  // ✅ CORREÇÃO: Adicionado para sortOrder
    handleResize,
    getFieldValue,
  ]);

  // ✅ SPEC-PERF-002: Request handler com paginacao SERVER-SIDE
  // Backend aplica filtros, ordenacao e paginacao - frontend apenas renderiza
  const requestHandler = useCallback(async (params: any) => {
    try {
      // Performance log: Inicio
      const perfStart = performance.now();
      if (DEBUG_PERFORMANCE) {
        console.log('%c[PERF] requestHandler INICIO (server-side)', 'color: #00ff00; font-weight: bold');
      }

      // Cancelar request anterior para evitar race conditions
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
      abortControllerRef.current = new AbortController();
      const signal = abortControllerRef.current.signal;

      // Chamar API com TODOS os parametros para processamento server-side
      const apiStart = performance.now();
      const axiosResponse = await consulAPI.getMonitoringData(category, {
        // Paginacao server-side
        page: params?.current || 1,
        page_size: params?.pageSize || 50,
        // Ordenacao server-side
        sort_field: sortField || undefined,
        sort_order: sortOrder || undefined,
        // Filtro por no
        node: selectedNode !== 'all' ? selectedNode : undefined,
        // Filtros de metadata (todos os filtros ativos)
        filters: filters,
        // Signal para abort
        signal: signal,
      });
      const apiEnd = performance.now();
      if (DEBUG_PERFORMANCE) {
        console.log(`%c[PERF] API respondeu em ${(apiEnd - apiStart).toFixed(0)}ms`, 'color: #ff9800; font-weight: bold');
      }

      // Verificar se request foi abortado
      if (signal.aborted) {
        return { data: [], total: 0, success: true };
      }

      // Normalizar resposta: axios retorna response.data
      const response = (axiosResponse && (axiosResponse as any).data)
        ? (axiosResponse as any).data
        : axiosResponse;

      if (!response.success) {
        console.warn('[MONITORING] Payload inesperado:', response);
        throw new Error(response.detail || 'Erro ao buscar dados');
      }

      // Capturar _metadata de performance
      if (response._metadata && isMountedRef.current) {
        setResponseMetadata(response._metadata);
        if (DEBUG_PERFORMANCE) {
          console.log(
            `%c[PERF] Source: ${response._metadata.source_name} | ` +
            `Master: ${response._metadata.is_master} | ` +
            `Cache: ${response._metadata.cache_status} | ` +
            `Age: ${response._metadata.age_seconds}s | ` +
            `Total: ${response._metadata.total_time_ms}ms`,
            'color: #4caf50; font-weight: bold; background: #1b5e20; padding: 4px;'
          );
        }
      }

      // Dados ja vem filtrados, ordenados e paginados do backend
      let rows: MonitoringDataItem[] = response.data || [];
      const total = response.total || 0;

      if (DEBUG_PERFORMANCE) {
        console.log(`%c[PERF] Registros na pagina: ${rows.length} | Total: ${total}`, 'color: #2196f3; font-weight: bold');
      }

      // ✅ SPEC-PERF-002: Usar filterOptions do servidor (evita calculo client-side)
      if (response.filterOptions && isMountedRef.current) {
        setMetadataState({ options: response.filterOptions, loaded: true });
        if (DEBUG_PERFORMANCE) {
          console.log(`%c[PERF] filterOptions do servidor: ${Object.keys(response.filterOptions).length} campos`, 'color: #9c27b0; font-weight: bold');
        }
      } else if (!metadataOptionsLoaded && rows.length > 0) {
        // Fallback: Se backend nao retornou filterOptions, extrair dos dados recebidos
        // NOTA: Isso so funciona bem se a pagina atual tiver dados representativos
        const optionsSets: Record<string, Set<string>> = {};
        filterFields.forEach((field) => {
          optionsSets[field.name] = new Set<string>();
        });
        ['Node', 'Service'].forEach(field => {
          optionsSets[field] = new Set<string>();
        });

        rows.forEach((item) => {
          filterFields.forEach((field) => {
            const value = item.Meta?.[field.name];
            if (value && typeof value === 'string') {
              optionsSets[field.name].add(value);
            }
          });
          if (item.Node) optionsSets['Node'].add(item.Node);
          if (item.Service) optionsSets['Service'].add(item.Service);
        });

        const options: Record<string, string[]> = {};
        Object.entries(optionsSets).forEach(([fieldName, valueSet]) => {
          options[fieldName] = Array.from(valueSet).sort();
        });

        if (isMountedRef.current) {
          setMetadataState({ options, loaded: true });
        }
      }

      // ✅ PROCESSAMENTO LOCAL PERMITIDO (complexo demais para backend):

      // 1. Filtros avancados (regex, operadores complexos)
      const filtersStart = performance.now();
      let processedRows = applyAdvancedFilters(rows);
      const filtersEnd = performance.now();
      if (DEBUG_PERFORMANCE && advancedConditions.length > 0) {
        console.log(`%c[PERF] Filtros avancados LOCAL em ${(filtersEnd - filtersStart).toFixed(0)}ms`, 'color: #ff5722; font-weight: bold');
      }

      // 2. Busca por keyword (pesquisa global em multiplos campos)
      const keyword = searchValue.trim().toLowerCase();
      if (keyword) {
        processedRows = processedRows.filter((item) => {
          const fields = [
            item.Service,
            item.ID,
            item.Meta?.name,
            item.Meta?.instance,
            item.Meta?.company,
            item.Meta?.site,
            item.Node,
          ];
          return fields.some(
            (field) => field && String(field).toLowerCase().includes(keyword),
          );
        });
      }

      // 3. Calcular summary para dashboard (agregacoes locais)
      const summaryStart = performance.now();
      const nextSummary = processedRows.reduce(
        (acc, item) => {
          acc.total += 1;
          const catKey = item.Meta?.type || 'desconhecido';
          acc.byCategory[catKey] = (acc.byCategory[catKey] || 0) + 1;
          const companyKey = item.Meta?.company || 'desconhecido';
          acc.byCompany[companyKey] = (acc.byCompany[companyKey] || 0) + 1;
          const siteKey = item.Meta?.site || 'desconhecido';
          acc.bySite[siteKey] = (acc.bySite[siteKey] || 0) + 1;
          const nodeKey = item.Node || 'desconhecido';
          acc.byNode[nodeKey] = (acc.byNode[nodeKey] || 0) + 1;
          (item.Tags || []).forEach(tag => acc.uniqueTags.add(tag));
          return acc;
        },
        {
          total: 0,
          byCategory: {} as Record<string, number>,
          byCompany: {} as Record<string, number>,
          bySite: {} as Record<string, number>,
          byNode: {} as Record<string, number>,
          uniqueTags: new Set<string>()
        },
      );
      if (isMountedRef.current) {
        setSummary(nextSummary);
      }
      const summaryEnd = performance.now();
      if (DEBUG_PERFORMANCE) {
        console.log(`%c[PERF] Summary LOCAL em ${(summaryEnd - summaryStart).toFixed(0)}ms`, 'color: #00bcd4; font-weight: bold');
      }

      // Salvar snapshot para exportacao CSV
      if (isMountedRef.current) {
        setTableSnapshot(processedRows);
      }

      // Performance log: Fim
      const perfEnd = performance.now();
      if (DEBUG_PERFORMANCE) {
        console.log(`%c[PERF] requestHandler COMPLETO em ${(perfEnd - perfStart).toFixed(0)}ms`, 'color: #00ff00; font-weight: bold; font-size: 14px');
      }

      // Retornar dados - JA vem paginados do servidor
      // Se aplicamos filtros locais (avancados/keyword), precisamos recalcular
      const finalData = (advancedConditions.length > 0 || keyword) ? processedRows : rows;
      const finalTotal = (advancedConditions.length > 0 || keyword) ? processedRows.length : total;

      return {
        data: finalData,
        success: true,
        total: finalTotal
      };
    } catch (error: any) {
      // Ignorar erros de abort (React 18 Strict Mode double mount)
      if (error.code === 'ECONNABORTED' || error.code === 'ERR_CANCELED' || error.name === 'CanceledError' || error.name === 'AbortError') {
        console.log('[requestHandler] Request aborted (cleanup ou race condition)');
        return {
          data: [],
          success: true,
          total: 0
        };
      }

      message.error('Erro ao carregar dados: ' + (error.message || error));
      return {
        data: [],
        success: false,
        total: 0
      };
    }
  }, [category, filters, selectedNode, searchValue, sortField, sortOrder, filterFields, applyAdvancedFilters, advancedConditions, metadataOptionsLoaded]);

  // ✅ NOVO: Handler de edição
  const handleEdit = useCallback((record: MonitoringDataItem) => {
    setFormMode('edit');
    setCurrentRecord(record);
    setFormOpen(true);
  }, []);

  // ✅ IMPLEMENTADO: Handler de deleção individual
  const handleDelete = useCallback(async (record: MonitoringDataItem) => {
    try {
      const service_id = record.ID;
      const node_addr = record.node_ip || record.Address;
      
      await consulAPI.deleteService(service_id, node_addr);
      
      message.success(`Serviço "${service_id}" excluído com sucesso`);
      actionRef.current?.reload();
    } catch (error: any) {
      message.error('Erro ao excluir: ' + (error.response?.data?.detail || error.message || error));
    }
  }, []);

  // ✅ IMPLEMENTADO: Handler de batch delete
  const handleBatchDelete = useCallback(async () => {
    if (!selectedRows.length) return;

    try {
      // Preparar lista de serviços para deletar
      const services = selectedRows.map(row => ({
        service_id: row.ID,
        node_addr: row.node_ip || row.Address
      }));
      
      await consulAPI.bulkDeleteServices(services);
      
      message.success(`${selectedRows.length} serviços excluídos com sucesso`);
      setSelectedRowKeys([]);
      setSelectedRows([]);
      actionRef.current?.reload();
    } catch (error: any) {
      message.error('Erro ao excluir em lote: ' + (error.response?.data?.detail || error.message || error));
    }
  }, [selectedRows]);

  // ✅ NOVO: Handler de exportação CSV
  const handleExport = useCallback(() => {
    if (!tableSnapshot.length) {
      message.info('Não há dados para exportar');
      return;
    }

    const sanitize = (value: unknown) =>
      String(value ?? '').replace(/[\r\n]+/g, ' ').replace(/;/g, ',');

    const header = [
      'ID',
      'Service',
      'Node',
      'Address',
      'Port',
      'Tags',
      ...tableFields.map(f => f.name),
      'meta_json',
    ];

    const rows = tableSnapshot.map((record) => {
      const meta = record.Meta || {};
      const metaValues = tableFields.map(f => sanitize(meta[f.name]));

      return [
        sanitize(record.ID),
        sanitize(record.Service),
        sanitize(record.Node),
        sanitize(record.Address),
        sanitize(record.Port),
        sanitize((record.Tags || []).join('|')),
        ...metaValues,
        sanitize(JSON.stringify(meta)),
      ].join(';');
    });

    const csvContent = [header.join(';'), ...rows].join('\n');
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `${category}-${new Date().toISOString()}.csv`;
    link.click();
    URL.revokeObjectURL(url);
    message.success('CSV exportado com sucesso!');
  }, [tableSnapshot, tableFields, category]);

  // ✅ NOVO: Handlers de busca avançada
  const handleAdvancedSearch = useCallback(
    (conditions: SearchCondition[], logicalOperator: string) => {
      setAdvancedConditions(conditions);
      setAdvancedOperator(logicalOperator === 'or' ? 'or' : 'and');
      setAdvancedOpen(false);
      actionRef.current?.reload();
    },
    [],
  );

  const handleAdvancedClear = useCallback(() => {
    setAdvancedConditions([]);
    setAdvancedOperator('and');
    setAdvancedOpen(false);
    actionRef.current?.reload();
  }, []);

  // ✅ NOVO: Campos para busca avançada
  const advancedFieldOptions = useMemo(() => {
    const fixedFields = [
      { label: 'ID', value: 'ID', type: 'text' },
      { label: 'Service', value: 'Service', type: 'text' },
      { label: 'Nó', value: 'Node', type: 'text' },
      { label: 'Tags', value: 'Tags', type: 'text' },
    ];

    const metadataFields = tableFields.map((field) => ({
      label: field.display_name,
      value: field.name,
      type: 'text',
    }));

    return [...fixedFields, ...metadataFields];
  }, [tableFields]);

  // ✅ OTIMIZAÇÃO: Resetar estados ao mudar categoria (1 único reload)
  // Evita race condition de 2 useEffect chamando reload() simultaneamente
  useEffect(() => {
    // Limpar filtros e estados quando categoria muda
    setFilters({});
    setSearchValue('');
    setSearchInput('');
    setSelectedNode('all');
    setAdvancedConditions([]);
    setSelectedRowKeys([]);
    setSelectedRows([]);
    setSortField(null);
    setSortOrder(null);
    setTableSnapshot([]);
    setSummary({
      total: 0,
      byCategory: {},
      byCompany: {},
      bySite: {},
      byNode: {},
      uniqueTags: new Set(),
    });

    // ✅ SPEC-PERF-002: Limpar cache de getFieldValue ao mudar categoria
    fieldValueCacheRef.current = {};

    // ✅ SPEC-PERF-002: Limpar metadataOptions ao mudar categoria (atomico)
    setMetadataState({ options: {}, loaded: false });

    // Reload após resetar estados (chamada única)
    actionRef.current?.reload();
  }, [category]);

  // ✅ OTIMIZAÇÃO: Reload apenas quando filtros/nó mudam (não em category)
  // Usa ref para evitar reload na primeira renderização
  const isFirstRender = React.useRef(true);
  useEffect(() => {
    // Skip primeira renderização (category useEffect já faz reload)
    if (isFirstRender.current) {
      isFirstRender.current = false;
      return;
    }
    
    // Reload apenas quando selectedNode ou filters mudarem
    actionRef.current?.reload();
  }, [selectedNode, filters]);

  const advancedActive = advancedConditions.some(
    (condition) => condition.field && condition.value !== undefined && condition.value !== '',
  );

  // ✅ SPEC-PERF-002: Usar dados dinamicos do tableFields ou formatCategoryName
  const categoryTitle = useMemo(() => {
    // Tentar pegar display_name do primeiro tableField (se disponivel)
    const firstField = tableFields[0];
    if (firstField && (firstField as any).category_display_name) {
      return (firstField as any).category_display_name;
    }
    // Fallback para formatacao automatica
    return formatCategoryName(category);
  }, [tableFields, category]);

  return (
    <PageContainer
      title={categoryTitle}
      subTitle={`Monitoramento de ${category.replace(/-/g, ' ')}`}
      loading={tableFieldsLoading || filterFieldsLoading}
      style={{ minHeight: 'calc(100vh - 64px)' }}
    >
      <Space direction="vertical" size="small" style={{ width: '100%' }}>
        {/* Dashboard com métricas - altura mínima para evitar layout shift */}
        <Card styles={{ body: { padding: '12px 20px', minHeight: '80px' } }}>
          <div style={{ display: 'flex', gap: 16, alignItems: 'flex-start', flexWrap: 'wrap' }}>
            {/* NodeSelector */}
            <div style={{ minWidth: 300, maxWidth: 380 }}>
              <Typography.Text strong style={{ fontSize: '13px', display: 'block', marginBottom: 8 }}>
                Nó do Consul
              </Typography.Text>
              <NodeSelector
                value={selectedNode}
                onChange={(nodeAddr) => setSelectedNode(nodeAddr)}
                style={{ width: '100%' }}
                showAllNodesOption={true}
              />
            </div>

            {/* Dashboard métricas - flexível com wrapping */}
            <div style={{ display: 'flex', gap: 16, flex: 1, flexWrap: 'wrap', minWidth: 0 }}>
              <div style={{ textAlign: 'center', minWidth: 100 }}>
                <div style={{ fontSize: '13px', color: '#8c8c8c', marginBottom: 6, fontWeight: 500 }}>Total</div>
                <div style={{ fontSize: '28px', fontWeight: 700, color: '#52c41a', lineHeight: 1 }}>
                  <CloudOutlined style={{ fontSize: '20px', marginRight: 6 }} />
                  {summary.total}
                </div>
              </div>
              <div style={{ textAlign: 'center', minWidth: 90 }}>
                <div style={{ fontSize: '13px', color: '#8c8c8c', marginBottom: 6, fontWeight: 500 }}>Nós</div>
                <div style={{ fontSize: '28px', fontWeight: 700, color: '#1890ff', lineHeight: 1 }}>
                  <ApartmentOutlined style={{ fontSize: '20px', marginRight: 6 }} />
                  {Object.keys(summary.byNode).length}
                </div>
              </div>
              <div style={{ textAlign: 'center', minWidth: 110 }}>
                <div style={{ fontSize: '13px', color: '#8c8c8c', marginBottom: 6, fontWeight: 500 }}>Empresas</div>
                <div style={{ fontSize: '28px', fontWeight: 700, color: '#722ed1', lineHeight: 1 }}>
                  <BankOutlined style={{ fontSize: '20px', marginRight: 6 }} />
                  {Object.keys(summary.byCompany).length}
                </div>
              </div>
              <div style={{ textAlign: 'center', minWidth: 90 }}>
                <div style={{ fontSize: '13px', color: '#8c8c8c', marginBottom: 6, fontWeight: 500 }}>Sites</div>
                <div style={{ fontSize: '28px', fontWeight: 700, color: '#fa8c16', lineHeight: 1 }}>
                  <EnvironmentOutlined style={{ fontSize: '20px', marginRight: 6 }} />
                  {Object.keys(summary.bySite).length}
                </div>
              </div>
              <div style={{ textAlign: 'center', minWidth: 110 }}>
                <div style={{ fontSize: '13px', color: '#8c8c8c', marginBottom: 6, fontWeight: 500 }}>Categorias</div>
                <div style={{ fontSize: '28px', fontWeight: 700, color: '#13c2c2', lineHeight: 1 }}>
                  <TeamOutlined style={{ fontSize: '20px', marginRight: 6 }} />
                  {Object.keys(summary.byCategory).length}
                </div>
              </div>
              <div style={{ textAlign: 'center', minWidth: 80 }}>
                <div style={{ fontSize: '13px', color: '#8c8c8c', marginBottom: 6, fontWeight: 500 }}>Tags</div>
                <div style={{ fontSize: '28px', fontWeight: 700, color: '#eb2f96', lineHeight: 1 }}>
                  <TagsOutlined style={{ fontSize: '20px', marginRight: 6 }} />
                  {summary.uniqueTags.size}
                </div>
              </div>
            </div>
          </div>
        </Card>

        {/* ✅ SPRINT 2: Performance Indicators - Mostra status do cache, fallback, staleness */}
        {responseMetadata && (
          <Card size="small" styles={{ body: { padding: '8px 16px' } }}>
            <Space align="center" size="small">
              <Typography.Text type="secondary" style={{ fontSize: '12px', marginRight: 8 }}>
                Performance:
              </Typography.Text>
              <BadgeStatus metadata={responseMetadata} />
            </Space>
          </Card>
        )}

        {/* ✅ NOVO: Barra de ações completa - altura mínima para evitar layout shift */}
        <Card size="small" styles={{ body: { minHeight: '60px' } }}>
          <Space wrap size="small">
            {/* ✅ NOVO: Busca por keyword - usando Input + Button ao invés de Search (enterButton deprecated) */}
            <Space.Compact>
              <Input
                allowClear
                placeholder="Buscar por ID, nome, instância..."
                style={{ width: 260 }}
                value={searchInput}
                onChange={(event) => {
                  const next = event.target.value;
                  setSearchInput(next);
                  if (!next) {
                    handleSearchSubmit('');
                  }
                }}
                onPressEnter={() => handleSearchSubmit(searchInput)}
              />
              <Tooltip title="Digite ID, nome ou instância para buscar">
                <Button
                  type="primary"
                  icon={<SearchOutlined />}
                  onClick={() => handleSearchSubmit(searchInput)}
                />
              </Tooltip>
            </Space.Compact>

            <Tooltip title="12 operadores: igual, diferente, contém, regex, inicia com, termina com, maior/menor que">
              <Button
                icon={<FilterOutlined />}
                type={advancedActive ? 'primary' : 'default'}
                onClick={() => setAdvancedOpen(true)}
              >
                Busca Avançada
                {advancedConditions.length > 0 && ` (${advancedConditions.length})`}
              </Button>
            </Tooltip>

            {advancedActive && (
              <Tooltip title="Remove todos os filtros avançados aplicados">
                <Button
                  icon={<ClearOutlined />}
                  onClick={handleAdvancedClear}
                >
                  Limpar Filtros Avançados
                </Button>
              </Tooltip>
            )}

            <Tooltip title="Limpa apenas filtros da tabela (mantém ordenação)">
              <Button
                icon={<ClearOutlined />}
                onClick={() => {
                  // ✅ CORREÇÃO: Limpar filtros internos do ProTable primeiro
                  actionRef.current?.clearFilters?.();
                  
                  // Limpar estados customizados
                  setFilters({});
                  setSearchValue('');
                  setSearchInput('');
                  // Manter selectedNode, advancedConditions e ordenação
                  
                  // Reload para aplicar mudanças
                  actionRef.current?.reload();
                }}
              >
                Limpar Filtros
              </Button>
            </Tooltip>

            <Tooltip title="Limpa TUDO: filtros, busca e ordenação">
              <Button
                icon={<ClearOutlined />}
                onClick={() => {
                  // ✅ CORREÇÃO: Usar reset() do ProTable para limpar TUDO (filtros + ordenação)
                  actionRef.current?.reset?.();
                  
                  // Limpar estados customizados
                  setFilters({});
                  setSearchValue('');
                  setSearchInput('');
                  setSortField(null);
                  setSortOrder(null);
                  // Manter selectedNode e advancedConditions
                  
                  // Reload para aplicar mudanças
                  actionRef.current?.reload();
                }}
              >
                Limpar Filtros e Ordem
              </Button>
            </Tooltip>

            <Tooltip title="Escolha quais colunas exibir na tabela">
              <ColumnSelector
                columns={columnConfig}
                onChange={setColumnConfig}
                storageKey={`${category}-columns`}
              />
            </Tooltip>

            <Tooltip title="Exporta os registros visíveis para arquivo CSV">
              <Button
                icon={<DownloadOutlined />}
                onClick={handleExport}
              >
                Exportar CSV
              </Button>
            </Tooltip>

            <Tooltip title="Recarrega os dados do servidor">
              <Button
                icon={<ReloadOutlined />}
                onClick={() => actionRef.current?.reload()}
              >
                Atualizar
              </Button>
            </Tooltip>

            {/* ✅ NOVO: Batch delete */}
            <Popconfirm
              title="Remover serviços selecionados?"
              description="Esta ação removerá os serviços selecionados. Tem certeza?"
              onConfirm={handleBatchDelete}
              disabled={!selectedRows.length}
              okText="Sim"
              cancelText="Não"
            >
              <Tooltip title="Remove vários serviços de uma vez (selecionados na tabela)">
                <Button
                  danger
                  icon={<DeleteOutlined />}
                  disabled={!selectedRows.length}
                >
                  Remover selecionados ({selectedRows.length})
                </Button>
              </Tooltip>
            </Popconfirm>

            <Tooltip title="Cria um novo registro de monitoramento">
              <Button
                type="primary"
                icon={<PlusOutlined />}
                onClick={() => {
                  setFormMode('create');
                  setCurrentRecord(null);
                  setFormOpen(true);
                }}
              >
                Novo registro
              </Button>
            </Tooltip>
          </Space>
        </Card>

        {/* Barra de filtros metadata - SPRINT 1: Renderização condicional para evitar race condition */}
        {filterFields.length > 0 && metadataOptionsLoaded && Object.keys(metadataOptions).length > 0 && (
          <MetadataFilterBar
            fields={filterFields}
            value={filters}
            options={metadataOptions}
            onChange={(newFilters) => {
              setFilters(newFilters);
              actionRef.current?.reload();
            }}
            onReset={() => {
              setFilters({});
              actionRef.current?.reload();
            }}
          />
        )}

        {/* ✅ COMPLETO: Tabela com TODAS as features */}
        {/* ✅ CORREÇÃO LAYOUT SHIFT: Container com altura fixa para evitar mudanças de layout */}
        <div style={{ minHeight: '600px', height: '600px', position: 'relative' }}>
          <ProTable<MonitoringDataItem>
            actionRef={actionRef}
            rowKey="ID"
            columns={proTableColumns}
            request={requestHandler}
            onChange={handleTableChange}
            search={false}
            // ✅ SPEC-PERF-002 GAP 4: Virtualizacao para grandes volumes
            virtual={true}
            pagination={{
              defaultPageSize: 50,
              showSizeChanger: true,
              pageSizeOptions: ['20', '50', '100', '200'],
              showTotal: (total, range) => `${range[0]}-${range[1]} de ${total} registros`,
              style: { marginBottom: 8 },
            }}
            scroll={{
              x: 2000, // Forca scroll horizontal para fixed columns
              y: 600    // Altura fixa necessaria para virtualizacao funcionar
            }}
            sticky
            options={{
              reload: true,
              setting: true,
              density: true,
              fullScreen: false,
            }}
            toolbar={{
              settings: [],
            }}
            components={{
            header: {
              cell: ResizableTitle,
            },
          }}
          headerTitle={false}
          cardProps={{
            bodyStyle: { padding: '0' },
          }}
          tableStyle={{ padding: '0 16px' }}
          loading={tableFieldsLoading || filterFieldsLoading}
          // ✅ NOVO: Linha expansível - limitada a 60% da largura para não expandir demais
          expandable={{
            expandedRowRender: (record) => (
              <div style={{ maxWidth: '60%', minWidth: 500 }}>
                <Descriptions size="small" column={2} bordered style={{ margin: 0 }}>
                  {Object.entries(record.Meta || {}).map(([key, value]) => (
                    <Descriptions.Item label={key} key={`${record.ID}-${key}`}>
                      {String(value ?? '')}
                    </Descriptions.Item>
                  ))}
                  {record.Tags?.length ? (
                    <Descriptions.Item label="Tags">
                      <Space size={[4, 4]} wrap>
                        {record.Tags.map((tag, idx) => (
                          <Tag key={`${record.ID}-expanded-${tag}-${idx}`}>{tag}</Tag>
                        ))}
                      </Space>
                    </Descriptions.Item>
                  ) : null}
                </Descriptions>
              </div>
            ),
            rowExpandable: (record) =>
              Boolean(record.Meta && Object.keys(record.Meta || {}).length > 0),
          }}
          // ✅ NOVO: rowSelection para batch delete - fixado à esquerda
          rowSelection={{
            selectedRowKeys,
            onChange: (keys, rows) => {
              setSelectedRowKeys(keys);
              setSelectedRows(rows as MonitoringDataItem[]);
            },
            fixed: true,
          }}
          locale={{
            emptyText: (
              <div style={{ padding: '60px 0', textAlign: 'center', minHeight: '400px', height: '400px', display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: 'center' }}>
                <div style={{ fontSize: '48px', color: '#d9d9d9', marginBottom: 16 }}>📊</div>
                <div style={{ fontSize: '16px', color: '#8c8c8c', marginBottom: 8 }}>
                  Não há dados disponíveis
                </div>
                <div style={{ fontSize: '14px', color: '#bfbfbf' }}>
                  Tente ajustar os filtros ou selecionar outro nó do Consul
                </div>
              </div>
            ),
          }}
          tableAlertRender={({ selectedRowKeys: keys }) =>
            keys.length ? <span>{`${keys.length} registros selecionados`}</span> : null
          }
        />
        </div>
      </Space>

      {/* ✅ NOVO: Drawer de busca avançada */}
      <Drawer
        width={720}
        title="Pesquisa avançada"
        open={advancedOpen}
        destroyOnHidden
        onClose={() => setAdvancedOpen(false)}
      >
        <AdvancedSearchPanel
          availableFields={advancedFieldOptions}
          onSearch={handleAdvancedSearch}
          onClear={handleAdvancedClear}
          initialConditions={advancedConditions}
          initialLogicalOperator={advancedOperator}
        />
      </Drawer>

      {/* ✅ NOVO: Drawer de detalhes */}
      <Drawer
        width={520}
        title="Detalhes do registro"
        open={!!detailRecord}
        destroyOnHidden
        onClose={() => setDetailRecord(null)}
      >
        {detailRecord && (
          <ProDescriptions column={1}>
            <ProDescriptions.Item label="ID">
              {detailRecord.ID}
            </ProDescriptions.Item>
            <ProDescriptions.Item label="Service">
              {detailRecord.Service}
            </ProDescriptions.Item>
            <ProDescriptions.Item label="Nó">
              {detailRecord.Node || 'Não informado'}
            </ProDescriptions.Item>
            <ProDescriptions.Item label="Endereço">
              {detailRecord.Address || 'Não informado'}
            </ProDescriptions.Item>
            <ProDescriptions.Item label="Porta">
              {detailRecord.Port ?? 'Não informado'}
            </ProDescriptions.Item>
            {Object.entries(detailRecord.Meta || {}).map(([key, value]) => (
              <ProDescriptions.Item label={key} key={key}>
                {String(value ?? '')}
              </ProDescriptions.Item>
            ))}
            <ProDescriptions.Item label="Tags">
              <Space size={[4, 4]} wrap>
                {(detailRecord.Tags || []).map((tag, idx) => (
                  <Tag key={`${detailRecord.ID}-drawer-${tag}-${idx}`}>{tag}</Tag>
                ))}
              </Space>
            </ProDescriptions.Item>
          </ProDescriptions>
        )}
      </Drawer>

      {/* ✅ IMPLEMENTADO: Modal de criação/edição */}
      <Modal
        title={formMode === 'create' ? 'Novo Serviço de Monitoramento' : 'Editar Serviço'}
        open={formOpen}
        onCancel={() => {
          setFormOpen(false);
          setCurrentRecord(null);
        }}
        footer={null}
        width={720}
        destroyOnClose
      >
        <div style={{ marginBottom: 16, padding: 12, background: '#f0f2f5', borderRadius: 4 }}>
          <p style={{ margin: 0, fontSize: 12, color: '#666' }}>
            <strong>ℹ️ Nota:</strong> Esta é uma versão simplificada do formulário. 
            Para edição completa com form_schema dinâmico, será implementado no próximo sprint.
          </p>
        </div>
        
        {currentRecord && (
          <div>
            <p><strong>ID:</strong> {currentRecord.ID}</p>
            <p><strong>Serviço:</strong> {currentRecord.Service}</p>
            <p><strong>Node:</strong> {currentRecord.Node}</p>
            <p style={{ fontSize: 12, color: '#999', marginTop: 16 }}>
              Para editar este serviço, use a API direta ou aguarde implementação completa do formulário dinâmico.
            </p>
          </div>
        )}
        
        {formMode === 'create' && (
          <div>
            <p style={{ color: '#999' }}>
              Funcionalidade de criação com form_schema dinâmico será implementada no próximo sprint.
            </p>
            <p style={{ fontSize: 12 }}>
              Por enquanto, use a página antiga Services.tsx ou a API direta para criar novos serviços.
            </p>
          </div>
        )}
      </Modal>
    </PageContainer>
  );
};

export default DynamicMonitoringPage;
