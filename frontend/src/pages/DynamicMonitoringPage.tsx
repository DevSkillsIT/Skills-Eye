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
  Radio,
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
import DynamicCRUDModal from '../components/DynamicCRUDModal'; // SPRINT 3: Modal CRUD dinâmico
import type { MonitoringDataItem } from '../types/monitoring'; // Tipos compartilhados

// const { Search } = Input; // Não usado
// const { Text } = Typography; // Não usado

// ============================================================================
// TIPOS E INTERFACES
// ============================================================================

// ✅ OTIMIZAÇÃO: Flag para controlar logs de performance
// Em produção (build), logs serão removidos automaticamente
const DEBUG_PERFORMANCE = import.meta.env.DEV;

// ✅ SPEC-ARCH-001: Mapa de display names para todas as categorias
const CATEGORY_DISPLAY_NAMES: Record<string, string> = {
  'network-probes': 'Network Probes (Rede)',
  'web-probes': 'Web Probes (Aplicações)',
  'system-exporters': 'Exporters: Sistemas',
  'database-exporters': 'Exporters: Bancos de Dados',
  'infrastructure-exporters': 'Exporters: Infraestrutura',
  'hardware-exporters': 'Exporters: Hardware',
  'network-devices': 'Dispositivos de Rede',
  'custom-exporters': 'Exporters: Customizados',
};

// ✅ SPEC-ARCH-001: Subtítulos com exemplos específicos para cada categoria
const CATEGORY_SUBTITLES: Record<string, string> = {
  'network-probes': 'Monitoramento de conectividade de rede: ICMP Ping, TCP Connect, DNS, SSH Banner',
  'web-probes': 'Monitoramento de aplicações web e APIs: HTTP 2xx/4xx/5xx, HTTPS, HTTP POST',
  'system-exporters': 'Métricas de sistemas operacionais: Linux (Node), Windows, VMware ESXi',
  'database-exporters': 'Monitoramento de bancos de dados: MySQL, PostgreSQL, MongoDB, Redis, Elasticsearch',
  'infrastructure-exporters': 'Infraestrutura e serviços: HAProxy, Nginx, Apache, RabbitMQ, Kafka',
  'hardware-exporters': 'Hardware físico e IPMI: iDRAC, HP iLO, IPMI, Dell OMSA',
  'network-devices': 'Dispositivos de rede: MikroTik, Cisco (SNMP), Switches, Roteadores',
  'custom-exporters': 'Exporters customizados: Exporters personalizados não categorizados',
};

interface DynamicMonitoringPageProps {
  category: string;  // 'network-probes', 'web-probes', etc
}

// ✅ Re-exportar MonitoringDataItem de types/monitoring para compatibilidade
export type { MonitoringDataItem } from '../types/monitoring';

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
  fieldStats?: Record<string, number>;  // Contagem de valores por campo para ordenar colunas
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

  // ✅ CORREÇÃO: Ref para persistir estado de busca do filterDropdown (evita reset a cada render)
  const filterSearchTextRef = useRef<Record<string, string>>({});

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
  const { options: metadataOptions, loaded: metadataOptionsLoaded, fieldStats } = metadataState;

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

  // ✅ PERF-002 FIX: Modal de confirmação de exportação com preview
  const [exportModalOpen, setExportModalOpen] = useState(false);
  const [exportInfo, setExportInfo] = useState<{
    totalRecords: number;
    totalColumns: number;
    estimatedSize: string;
    columns: string[];
  } | null>(null);

  // ✅ PERF-002 FIX: Escopo de exportação (página atual ou todos os registros)
  const [exportScope, setExportScope] = useState<'current' | 'all'>('current');
  const [exportLoading, setExportLoading] = useState(false);

  // SISTEMA DINÂMICO: Combinar colunas fixas + campos metadata
  const defaultColumnConfig = useMemo<ColumnConfig[]>(() => {
    // Campos de metadata que vem do backend
    let metadataColumns: ColumnConfig[] = tableFields
      // Filtrar campos que já estão nas fixedColumns para evitar duplicação
      .filter(field => !['name', 'instance'].includes(field.name.toLowerCase()))
      .map((field) => ({
        key: field.name,
        title: field.display_name,
        visible: field.show_in_table ?? true,
        locked: false
      }));

    // SPEC-PERF-002 FIX: Ordenar colunas com valores vazios por ultimo
    // Usar fieldStats do backend para saber quais campos tem valores
    if (fieldStats && Object.keys(fieldStats).length > 0) {
      // Criar copia para ordenar (sort modifica o array original)
      metadataColumns = [...metadataColumns].sort((a, b) => {
        const aCount = fieldStats[a.key] || 0;
        const bCount = fieldStats[b.key] || 0;
        // Campos com valores vem primeiro, vazios por ultimo
        if (aCount > 0 && bCount === 0) return -1;
        if (aCount === 0 && bCount > 0) return 1;
        // Se ambos tem ou nao tem valores, ordenar por quantidade (maior primeiro)
        return bCount - aCount;
      });

      if (import.meta.env.DEV) {
        const withValues = metadataColumns.filter(c => (fieldStats[c.key] || 0) > 0).length;
        const withoutValues = metadataColumns.length - withValues;
        console.log(`[DynamicMonitoringPage] Ordenacao de colunas: ${withValues} com valores, ${withoutValues} vazias`);
      }
    }

    // SPEC-PERF-002 FIX: Ordem fixa das colunas principais
    // Service ID, Service Name, Nó, Name, Instance, Tags - sempre nessa ordem
    const fixedColumns: ColumnConfig[] = [
      { key: 'ID', title: 'Service ID', visible: true, locked: false },
      { key: 'Service', title: 'Service Name', visible: true },
      { key: 'Node', title: 'Nó', visible: true },
      { key: 'name', title: 'Name', visible: true },
      { key: 'instance', title: 'Instance', visible: true },
      { key: 'Tags', title: 'Tags', visible: true },
      { key: 'Address', title: 'Address', visible: false },
      { key: 'Port', title: 'Port', visible: false },
      { key: 'actions', title: 'Ações', visible: true, locked: true }
    ];

    return [...fixedColumns, ...metadataColumns];
  }, [tableFields, fieldStats]);

  // ✅ CORREÇÃO CRÍTICA: Atualizar columnConfig quando tableFields carregar
  // ✅ SPEC-PERF-002: Remover columnConfig das dependencias para evitar ciclo infinito
  const prevDefaultColumnConfigRef = useRef<string>('');

  useEffect(() => {
    // ✅ OTIMIZAÇÃO: Só atualizar quando realmente necessário (tableFields carregou)
    if (defaultColumnConfig.length > 0 && tableFields.length > 0) {
      // SPEC-PERF-002 FIX: Verificar se defaultColumnConfig mudou (INCLUINDO ORDEM)
      // Não usar .sort() para detectar mudança de ordem das colunas
      const defaultKeys = defaultColumnConfig.map(c => c.key).join(',');

      // ✅ SPEC-PERF-002: Comparar apenas com a ref anterior, nao com columnConfig atual
      // Isso evita o ciclo: columnConfig muda -> useEffect roda -> setColumnConfig -> loop
      if (prevDefaultColumnConfigRef.current !== defaultKeys) {
        // ✅ OTIMIZAÇÃO: Só logar se realmente mudou (evita logs duplicados)
        if (import.meta.env.DEV) {
          console.log('[DynamicMonitoringPage] ✅ Atualizando columnConfig:', {
            to: defaultColumnConfig.length,
            metadataColumns: defaultColumnConfig.length - 9, // 9 colunas fixas
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
  // ✅ SPEC-PERF-002 FIX: Apenas atualizar estados, o useEffect fará o reload
  const handleTableChange = useCallback((_pagination: any, _filters: any, sorter: any) => {
    if (sorter && sorter.field) {
      // SPEC-PERF-002 FIX: Converter array de campo para string
      // ProTable envia field como array para colunas com dataIndex=['Meta', 'company']
      // Backend espera string como 'Meta.company' ou apenas 'company'
      let field = sorter.field;
      if (Array.isArray(field)) {
        // Se é ['Meta', 'fieldName'], enviar apenas 'fieldName'
        // O backend já sabe procurar no Meta
        field = field[field.length - 1];
      }
      setSortField(field);
      setSortOrder(sorter.order || null);
      // NÃO chamar reload() aqui - o useEffect[sortField, sortOrder] fará isso
    } else {
      setSortField(null);
      setSortOrder(null);
    }
  }, []);

  // ✅ SPEC-PERF-002: Debounce com cancelamento para evitar requests excessivos
  const debouncedReload = useDebouncedCallback(() => {
    // ✅ SPEC-PERF-002-FIX REQ-006: Cancelar request anterior antes de disparar novo reload
    // Isso evita race conditions quando usuário digita rápido
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      console.log('[DynamicMonitoringPage] Request anterior cancelada');
    }
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
    // ✅ CORREÇÃO CRÍTICA: Usar defaultColumnConfig como fallback quando columnConfig estiver vazio
    // Isso evita race condition onde proTableColumns retorna [] se columnConfig não carregou ainda
    // O defaultColumnConfig já tem as colunas fixas e será atualizado quando tableFields carregar
    const configToUse = columnConfig.length > 0 ? columnConfig : defaultColumnConfig;

    // Só retorna vazio se REALMENTE não há configuração disponível
    if (configToUse.length === 0) {
      return [];
    }

    // ✅ CORREÇÃO: Usar configToUse ao invés de columnConfig para filtrar visíveis
    const visibleConfigs = configToUse.filter(c => c.visible);

    // ✅ OTIMIZAÇÃO: Só logar quando realmente mudou (evita logs duplicados em StrictMode)
    if (import.meta.env.DEV) {
      const configKey = `${configToUse.length}-${visibleConfigs.length}-${tableFields.length}`;
      if (lastProTableColumnsRef.current !== configKey) {
        const metadataColumns = visibleConfigs.filter(c => tableFields.some(f => f.name === c.key));
        console.log('[DynamicMonitoringPage] proTableColumns:', {
          columnConfigLength: configToUse.length,
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
      // ✅ SPEC-PERF-002 FIX: Usar metadataOptionsRef.current para evitar recalculos desnecessarios
      // O flag metadataOptionsLoaded garante que o useMemo seja recalculado quando as opcoes carregarem
      const currentMetadataOptions = metadataOptionsRef.current;
      let fieldOptions = currentMetadataOptions[colConfig.key] || [];
      let actualOptionsKey = colConfig.key; // Guardar a chave real usada para buscar opcoes

      // Se nao encontrou pela key exata, tentar encontrar uma correspondencia aproximada
      // Isso resolve casos onde o frontend usa 'Node' mas backend retorna 'node_ip'
      if (fieldOptions.length === 0) {
        const lowerKey = colConfig.key.toLowerCase();
        const matchingKey = Object.keys(currentMetadataOptions).find(
          key => key.toLowerCase() === lowerKey ||
                 key.toLowerCase().includes(lowerKey) ||
                 lowerKey.includes(key.toLowerCase())
        );
        if (matchingKey) {
          fieldOptions = currentMetadataOptions[matchingKey];
          actualOptionsKey = matchingKey; // Usar a chave real do backend
        }
      }

      // ✅ SPEC-PERF-002 FIX: Remover condicao metadataOptionsLoaded redundante
      // Se fieldOptions.length > 0, ja temos opcoes para mostrar
      if (fieldOptions.length > 0 && colConfig.key !== 'actions' && colConfig.key !== 'Tags') {
        // ✅ CORREÇÃO: Usar filteredValue para controlar estado visual do filtro
        baseColumn.filteredValue = filters[colConfig.key] ? [filters[colConfig.key]] : null;

        // Capturar a chave real para usar no closure do filterDropdown
        const optionsKeyForDropdown = actualOptionsKey;

        baseColumn.filterDropdown = ({ setSelectedKeys, selectedKeys, confirm, clearFilters }) => {
          // ✅ CORREÇÃO: Usar ref para persistir estado de busca (evita reset a cada render)
          const [searchText, setSearchText] = useState(filterSearchTextRef.current[colConfig.key] || '');

          // ✅ SPEC-PERF-002 FIX: Usar fieldOptions capturado no closure (ja tem os valores corretos)
          const filteredOptions = fieldOptions.filter(opt =>
            opt.toLowerCase().includes(searchText.toLowerCase())
          );

          // ✅ CORREÇÃO: Atualizar ref quando searchText mudar
          const handleSearchChange = (e: React.ChangeEvent<HTMLInputElement>) => {
            const newValue = e.target.value;
            setSearchText(newValue);
            filterSearchTextRef.current[colConfig.key] = newValue;
          };

          return (
            <div style={{ padding: 8, width: 300 }}>
              <Input
                placeholder={`Buscar ${colConfig.title}`}
                value={searchText}
                onChange={handleSearchChange}
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
                    // ✅ CORREÇÃO: Suportar múltipla seleção - usar array se mais de um valor
                    const newFilters = { ...filters };
                    if (selectedKeys.length > 0) {
                      // Se múltiplos valores selecionados, enviar como string separada por vírgula
                      // O backend deve suportar filtros com múltiplos valores
                      newFilters[colConfig.key] = selectedKeys.join(',');
                    } else {
                      delete newFilters[colConfig.key];
                    }
                    setFilters(newFilters);
                    confirm();
                    // ✅ CORREÇÃO: NÃO chamar reload() aqui - o useEffect[filters] já faz isso
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
                    // ✅ CORREÇÃO: Limpar ref também
                    setSearchText('');
                    filterSearchTextRef.current[colConfig.key] = '';
                    // ✅ CORREÇÃO: NÃO chamar reload() aqui - o useEffect[filters] já faz isso
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
    defaultColumnConfig,  // ✅ CORREÇÃO: Adicionado para fallback quando columnConfig vazio
    columnWidths,
    tableFields,
    metadataOptionsLoaded,  // ✅ SPEC-PERF-002: Apenas flag boolean, não o objeto completo
    // metadataOptions removido - usar metadataOptionsRef.current dentro do useMemo
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
        // ✅ SPEC-PERF-002-FIX REQ-001: Busca textual enviada ao backend
        // Backend processa em TODO o dataset ANTES da paginação
        q: searchValue || undefined,
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
      // ✅ CORREÇÃO CRÍTICA: Adicionar campos fixos (Node, Service) ao filterOptions
      // O backend retorna campos de metadata, mas precisamos também dos campos fixos
      if (response.filterOptions && isMountedRef.current) {
        // Mesclar filterOptions do backend com campos fixos
        const enhancedOptions = { ...response.filterOptions };

        // Adicionar opcoes para campos fixos se nao vierem do backend
        if (!enhancedOptions['Node']) {
          const nodeSet = new Set<string>();
          rows.forEach(item => {
            if (item.Node) nodeSet.add(item.Node);
          });
          if (nodeSet.size > 0) {
            enhancedOptions['Node'] = Array.from(nodeSet).sort();
          }
        }

        if (!enhancedOptions['Service']) {
          const serviceSet = new Set<string>();
          rows.forEach(item => {
            if (item.Service) serviceSet.add(item.Service);
          });
          if (serviceSet.size > 0) {
            enhancedOptions['Service'] = Array.from(serviceSet).sort();
          }
        }

        // SPEC-PERF-002 FIX: Pegar _fieldStats do backend para ordenar colunas vazias por ultimo
        const fieldStats = response._fieldStats || {};
        setMetadataState({ options: enhancedOptions, loaded: true, fieldStats });
        if (DEBUG_PERFORMANCE) {
          console.log(`%c[PERF] filterOptions do servidor: ${Object.keys(enhancedOptions).length} campos`, 'color: #9c27b0; font-weight: bold');
          console.log('[PERF] Chaves filterOptions:', Object.keys(enhancedOptions));
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

      // ✅ SPEC-PERF-002-FIX REQ-001: Busca textual REMOVIDA do frontend
      // A busca agora é feita 100% no backend via parâmetro 'q'
      // Isso permite buscar em TODO o dataset, não apenas na página atual
      // Código anterior removido conforme especificação

      // 3. ✅ SPEC-PERF-002 CORREÇÃO: Buscar summary do backend (totais de TODO o dataset)
      // O backend retorna estatisticas sem paginacao, mostrando totais reais
      const summaryStart = performance.now();
      try {
        const summaryResponse = await consulAPI.getMonitoringSummary(category, {
          node: selectedNode !== 'all' ? selectedNode : undefined,
          company: filters.company,
          site: filters.site,
          env: filters.env,
        });

        if (summaryResponse.data.success && isMountedRef.current) {
          const backendSummary = summaryResponse.data.summary;

          // Extrair tags unicos dos dados da pagina (backend nao retorna tags no summary)
          const tagsSet = new Set<string>();
          processedRows.forEach(item => {
            (item.Tags || []).forEach(tag => tagsSet.add(tag));
          });

          setSummary({
            total: backendSummary.total,
            byCategory: backendSummary.byEnv || {},  // Usar env como categoria
            byCompany: backendSummary.byCompany || {},
            bySite: backendSummary.bySite || {},
            byNode: backendSummary.byNode || {},
            uniqueTags: tagsSet
          });

          if (DEBUG_PERFORMANCE) {
            console.log(`%c[PERF] Summary do BACKEND: total=${backendSummary.total}`, 'color: #00bcd4; font-weight: bold');
          }
        }
      } catch (summaryError) {
        // Fallback: Se endpoint /summary falhar, usar calculo local (apenas pagina atual)
        console.warn('[PERF] Erro ao buscar summary do backend, usando calculo local:', summaryError);

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
      }
      const summaryEnd = performance.now();
      if (DEBUG_PERFORMANCE) {
        console.log(`%c[PERF] Summary total em ${(summaryEnd - summaryStart).toFixed(0)}ms`, 'color: #00bcd4; font-weight: bold');
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
      // Se aplicamos filtros locais (avancados), precisamos recalcular
      // ✅ SPEC-PERF-002-FIX REQ-001: keyword removido - busca agora é server-side
      const finalData = (advancedConditions.length > 0) ? processedRows : rows;
      const finalTotal = (advancedConditions.length > 0) ? processedRows.length : total;

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
  /**
   * Função auxiliar para calcular tamanho estimado do CSV
   * Baseado no número de registros e colunas (estimativa conservadora)
   */
  const estimateCsvSize = (recordCount: number, columnCount: number): string => {
    // Aproximação: ~150 bytes por registro + 100 bytes de header
    const estimatedBytes = (recordCount * 150) + 100;
    if (estimatedBytes < 1024) return `${estimatedBytes} B`;
    if (estimatedBytes < 1024 * 1024) return `${(estimatedBytes / 1024).toFixed(2)} KB`;
    return `${(estimatedBytes / (1024 * 1024)).toFixed(2)} MB`;
  };

  /**
   * Abre o modal de confirmação com preview das informações de exportação
   * Permite escolher entre exportar página atual ou todos os registros
   */
  const handleExport = useCallback(() => {
    if (!tableSnapshot.length && summary.total === 0) {
      message.info('Não há dados para exportar');
      return;
    }

    // Coletas de informações sobre a exportação
    const columns = [
      'ID',
      'Service',
      'Node',
      'Address',
      'Port',
      'Tags',
      ...tableFields.map(f => f.name),
      'meta_json',
    ];

    // Por padrão, mostra informações da página atual
    // O usuário pode escolher exportar todos
    const exportData = {
      totalRecords: tableSnapshot.length,
      totalColumns: columns.length,
      estimatedSize: estimateCsvSize(tableSnapshot.length, columns.length),
      columns: columns,
    };

    // Reset do escopo para página atual ao abrir modal
    setExportScope('current');
    setExportInfo(exportData);
    setExportModalOpen(true);
  }, [tableSnapshot, tableFields, summary.total]);

  /**
   * Atualiza informações de preview quando usuário muda escopo de exportação
   */
  const handleExportScopeChange = useCallback((scope: 'current' | 'all') => {
    setExportScope(scope);

    const columns = [
      'ID',
      'Service',
      'Node',
      'Address',
      'Port',
      'Tags',
      ...tableFields.map(f => f.name),
      'meta_json',
    ];

    // Atualizar preview baseado no escopo selecionado
    const recordCount = scope === 'current' ? tableSnapshot.length : summary.total;

    setExportInfo({
      totalRecords: recordCount,
      totalColumns: columns.length,
      estimatedSize: estimateCsvSize(recordCount, columns.length),
      columns: columns,
    });
  }, [tableSnapshot, tableFields, summary.total]);

  /**
   * Executa a exportação CSV após confirmação do usuário
   * Suporta exportação da página atual ou de todos os registros
   */
  const performCsvExport = useCallback(async () => {
    if (!exportInfo) {
      message.error('Nenhum dado para exportar');
      return;
    }

    // Função auxiliar para sanitizar valores do CSV
    const sanitize = (value: unknown) =>
      String(value ?? '').replace(/[\r\n]+/g, ' ').replace(/;/g, ',');

    // Função auxiliar para gerar linhas CSV a partir dos dados
    const generateCsvRows = (data: MonitoringDataItem[]) => {
      return data.map((record) => {
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
    };

    // Função auxiliar para download do CSV
    const downloadCsv = (rows: string[], recordCount: number) => {
      const csvContent = [exportInfo.columns.join(';'), ...rows].join('\n');
      const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `${category}-${exportScope === 'all' ? 'completo' : 'pagina'}-${new Date().toISOString().slice(0, 19)}.csv`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);

      // Fechar modal e informar sucesso
      setExportModalOpen(false);
      setExportInfo(null);
      setExportLoading(false);
      message.success(`CSV exportado com sucesso! (${recordCount} registros)`);
    };

    // Se exportar apenas página atual, usar tableSnapshot
    if (exportScope === 'current') {
      if (!tableSnapshot.length) {
        message.error('Nenhum dado na página atual para exportar');
        return;
      }
      const rows = generateCsvRows(tableSnapshot);
      downloadCsv(rows, tableSnapshot.length);
      return;
    }

    // Se exportar todos, buscar dados completos do backend
    setExportLoading(true);

    try {
      console.log('[Export] Buscando todos os registros...');
      console.log('[Export] Parametros:', {
        category,
        page: 1,
        page_size: 10000,
        sort_field: sortField,
        sort_order: sortOrder,
        node: selectedNode !== 'all' ? selectedNode : undefined,
        filters,
      });

      // Buscar TODOS os registros do backend
      // IMPORTANTE: Nao passar page e page_size para obter todos os registros
      // A API tem limite de 200 por pagina, mas retorna todos se omitir paginacao
      const exportOptions: {
        page?: number;
        page_size?: number;
        sort_field?: string;
        sort_order?: 'ascend' | 'descend';
        node?: string;
        filters?: Record<string, string | undefined>;
      } = {};

      // NAO incluir page e page_size para buscar todos os registros
      // Adicionar apenas campos com valores definidos
      if (sortField) exportOptions.sort_field = sortField;
      if (sortOrder) exportOptions.sort_order = sortOrder;
      if (selectedNode && selectedNode !== 'all') exportOptions.node = selectedNode;
      if (filters && Object.keys(filters).length > 0) exportOptions.filters = filters;

      console.log('[Export] Options construidas (sem paginacao para buscar todos):', exportOptions);

      const response = await consulAPI.getMonitoringData(category, exportOptions);

      console.log('[Export] Resposta raw da API:', response);

      // Normalizar resposta: axios retorna response.data que contem a resposta da API
      const normalizedResponse = (response && (response as any).data)
        ? (response as any).data
        : response;

      console.log('[Export] Resposta normalizada:', normalizedResponse);

      // API retorna { success: true, data: [...], total: N }
      if (!normalizedResponse.success || !normalizedResponse.data) {
        console.error('[Export] Resposta invalida:', normalizedResponse);
        throw new Error('Erro ao buscar dados completos');
      }

      // Processar dados retornados (API retorna em "data", nao "items")
      const allData = normalizedResponse.data as MonitoringDataItem[];
      console.log('[Export] Total de registros recebidos:', allData.length);

      if (!allData.length) {
        setExportLoading(false);
        message.error('Nenhum dado encontrado para exportar');
        return;
      }

      const rows = generateCsvRows(allData);
      downloadCsv(rows, allData.length);

    } catch (error) {
      setExportLoading(false);
      console.error('[Export] Erro ao buscar todos os registros:', error);
      message.error('Erro ao buscar dados completos. Tente exportar apenas a página atual.');
    }
  }, [tableSnapshot, tableFields, exportInfo, category, exportScope, sortField, sortOrder, selectedNode, filters]);

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

  // ✅ OTIMIZAÇÃO: Reload apenas quando filtros/nó/ordenação mudam (não em category)
  // Usa ref para evitar reload na primeira renderização
  const isFirstRender = React.useRef(true);
  useEffect(() => {
    // Skip primeira renderização (category useEffect já faz reload)
    if (isFirstRender.current) {
      isFirstRender.current = false;
      return;
    }

    // ✅ SPEC-PERF-002-FIX REQ-004: Usar debouncedReload para evitar duplo disparo
    // Isso garante que múltiplas mudanças de estado em sequência disparem apenas UMA requisição
    debouncedReload();
  }, [selectedNode, filters, sortField, sortOrder, debouncedReload]);

  const advancedActive = advancedConditions.some(
    (condition) => condition.field && condition.value !== undefined && condition.value !== '',
  );

  return (
    <PageContainer
      title={CATEGORY_DISPLAY_NAMES[category] || category}
      subTitle={CATEGORY_SUBTITLES[category] || `Monitoramento de ${category.replace(/-/g, ' ')}`}
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

            {/* ✅ SPRINT 2: Performance Indicators - Alinhado à direita no dashboard */}
            {responseMetadata && (
              <div style={{
                marginLeft: 'auto',
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'flex-end',
                alignSelf: 'center',
                gap: 4
              }}>
                <Typography.Text type="secondary" style={{ fontSize: '10px', whiteSpace: 'nowrap' }}>
                  Performance
                </Typography.Text>
                <BadgeStatus metadata={responseMetadata} />
              </div>
            )}
          </div>
        </Card>

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
                  // ✅ SPEC-PERF-002 FIX: Limpar todos os estados de filtro e ordenacao
                  // O useEffect[selectedNode, filters, sortField, sortOrder] fara o reload automaticamente
                  setFilters({});
                  setSearchValue('');
                  setSearchInput('');
                  setSortField(null);
                  setSortOrder(null);
                  // Limpar refs de busca dos filtros
                  filterSearchTextRef.current = {};
                  // Limpar condicoes avancadas tambem
                  setAdvancedConditions([]);
                  setAdvancedOperator('and');
                  // Manter selectedNode
                }}
              >
                Limpar Filtros e Ordem
              </Button>
            </Tooltip>

            <Tooltip title="Escolha quais colunas exibir na tabela">
              <ColumnSelector
                columns={columnConfig.length > 0 ? columnConfig : defaultColumnConfig}
                onChange={setColumnConfig}
                storageKey={`${category}-columns`}
              />
            </Tooltip>

            <Tooltip title={`Exporta ${tableSnapshot.length} registros da página atual${summary.total > tableSnapshot.length ? ` (de ${summary.total} total)` : ''}`}>
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
              // ✅ CORREÇÃO: NÃO chamar reload() aqui - o useEffect[selectedNode, filters] já faz isso
              // Isso evita requisições duplas (uma do onChange + uma do useEffect)
              setFilters(newFilters);
            }}
            onReset={() => {
              // ✅ CORREÇÃO: NÃO chamar reload() aqui - o useEffect[selectedNode, filters] já faz isso
              setFilters({});
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

      {/* ✅ SPRINT 3: Modal CRUD dinâmico reutilizando componente existente */}
      <DynamicCRUDModal
        mode={formMode}
        category={category}
        service={currentRecord}
        visible={formOpen}
        onSuccess={() => {
          setFormOpen(false);
          setCurrentRecord(null);
          actionRef.current?.reload();
        }}
        onCancel={() => {
          setFormOpen(false);
          setCurrentRecord(null);
        }}
      />

      {/* ✅ PERF-002 FIX: Modal de confirmação de exportação CSV com preview */}
      <Modal
        title="Confirmar Exportação CSV"
        open={exportModalOpen}
        onCancel={() => {
          setExportModalOpen(false);
          setExportInfo(null);
          setExportLoading(false);
        }}
        onOk={performCsvExport}
        okText={exportLoading ? 'Exportando...' : 'Confirmar Exportação'}
        okButtonProps={{ loading: exportLoading, disabled: exportLoading }}
        cancelText="Cancelar"
        cancelButtonProps={{ disabled: exportLoading }}
        width={600}
        destroyOnHidden
        closable={!exportLoading}
        maskClosable={!exportLoading}
      >
        {exportInfo && (
          <Space direction="vertical" size="large" style={{ width: '100%' }}>
            {/* 🎯 Seleção do escopo de exportação */}
            {summary.total > tableSnapshot.length && (
              <Card
                size="small"
                style={{
                  background: '#fffbe6',
                  border: '1px solid #ffe58f',
                }}
              >
                <div style={{ marginBottom: 12 }}>
                  <strong>Escopo da Exportação:</strong>
                </div>
                <Radio.Group
                  value={exportScope}
                  onChange={(e) => handleExportScopeChange(e.target.value)}
                  style={{ width: '100%' }}
                >
                  <Space direction="vertical" style={{ width: '100%' }}>
                    <Radio value="current">
                      <span>
                        <strong>Página Atual</strong> - {tableSnapshot.length} registros visíveis
                      </span>
                    </Radio>
                    <Radio value="all">
                      <span>
                        <strong>Todos os Registros</strong> - {summary.total} registros no total
                      </span>
                    </Radio>
                  </Space>
                </Radio.Group>
              </Card>
            )}

            {/* ℹ️ Resumo da exportação */}
            <Card
              size="small"
              style={{
                background: '#f6f8fa',
                border: '1px solid #e1e4e8',
              }}
            >
              <Space direction="vertical" size="small" style={{ width: '100%' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 0' }}>
                  <span><strong>Total de Registros:</strong></span>
                  <span style={{ color: '#0366d6', fontWeight: 'bold' }}>{exportInfo.totalRecords.toLocaleString('pt-BR')}</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 0' }}>
                  <span><strong>Número de Colunas:</strong></span>
                  <span style={{ color: '#0366d6', fontWeight: 'bold' }}>{exportInfo.totalColumns}</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 0' }}>
                  <span><strong>Tamanho Estimado:</strong></span>
                  <span style={{ color: '#28a745', fontWeight: 'bold' }}>{exportInfo.estimatedSize}</span>
                </div>
              </Space>
            </Card>

            {/* 📋 Lista de colunas que serão exportadas */}
            <div>
              <strong style={{ display: 'block', marginBottom: 8 }}>
                Colunas que serão exportadas:
              </strong>
              <div
                style={{
                  maxHeight: '300px',
                  overflowY: 'auto',
                  padding: '12px',
                  background: '#f9f9f9',
                  border: '1px solid #d9d9d9',
                  borderRadius: '4px',
                }}
              >
                <ul style={{ margin: 0, paddingLeft: '20px' }}>
                  {exportInfo.columns.map((col, idx) => (
                    <li key={idx} style={{ marginBottom: '4px', fontSize: '13px' }}>
                      <code style={{ background: '#f5f5f5', padding: '2px 6px', borderRadius: '2px' }}>
                        {col}
                      </code>
                    </li>
                  ))}
                </ul>
              </div>
            </div>

            {/* ✅ Avisos e informações adicionais */}
            <div
              style={{
                padding: '12px',
                background: '#e6f4ff',
                border: '1px solid #91caff',
                borderRadius: '4px',
                fontSize: '13px',
              }}
            >
              <strong>ℹ️ Informações:</strong>
              <ul style={{ margin: '8px 0 0 0', paddingLeft: '20px' }}>
                <li>O arquivo será salvo em formato CSV (semicolon-separated)</li>
                <li>Quebras de linha serão removidas dos valores</li>
                <li>Um backup completo em JSON está incluído na coluna "meta_json"</li>
              </ul>
            </div>
          </Space>
        )}
      </Modal>
    </PageContainer>
  );
};

export default DynamicMonitoringPage;
