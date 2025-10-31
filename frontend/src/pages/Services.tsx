import React, {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react';
import {
  Button,
  Card,
  Descriptions,
  Drawer,
  Input,
  message,
  Popconfirm,
  Select,
  Space,
  Statistic,
  Tag,
  Tooltip,
  Typography,
} from 'antd';
import {
  ClearOutlined,
  CloudOutlined,
  DeleteOutlined,
  DownloadOutlined,
  EditOutlined,
  FilterOutlined,
  InfoCircleOutlined,
  PlusOutlined,
  ReloadOutlined,
} from '@ant-design/icons';
import type { ActionType } from '@ant-design/pro-components';
import {
  ModalForm,
  PageContainer,
  ProDescriptions,
  ProFormDigit,
  ProFormSelect,
  ProFormText,
  ProFormTextArea,
  ProTable,
} from '@ant-design/pro-components';
import { useSearchParams } from 'react-router-dom';
import MetadataFilterBar from '../components/MetadataFilterBar';
import ColumnSelector, { type ColumnConfig } from '../components/ColumnSelector';
import AdvancedSearchPanel, { type SearchCondition } from '../components/AdvancedSearchPanel';
import ResizableTitle from '../components/ResizableTitle';
import { consulAPI } from '../services/api';
import type {
  ConsulServiceRecord,
  ServiceMeta,
  ServiceCreatePayload,
  ServiceQuery,
} from '../services/api';
import { useTableFields, useFormFields, useFilterFields } from '../hooks/useMetadataFields';

const { Option } = Select;
const { Search } = Input;
const { Text } = Typography;

const ALL_NODES = 'ALL';
const DEFAULT_NODE = '__MAIN__';
const DEFAULT_MODULES = [
  'icmp',
  'http_2xx',
  'http_4xx',
  'http_5xx',
  'http_post_2xx',
  'https',
  'tcp_connect',
  'ssh_banner',
  'pop3s_banner',
  'irc_banner',
];

const FORM_ROW_STYLE: React.CSSProperties = {
  display: 'grid',
  gap: 16,
  gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
};

interface ConsulNode {
  node: string;
  addr: string;
  status?: string;
}

interface ServiceTableItem {
  key: string;
  id: string;
  node: string;
  nodeAddr?: string;
  service: string;
  tags: string[];
  address?: string;
  port?: number;
  meta: ServiceMeta;
}

type ServiceColumn<T> = import('@ant-design/pro-components').ProColumns<T>;

interface ServiceFormValues {
  module: string;
  company: string;
  project: string;
  env: string;
  serviceDisplayName: string;
  instance: string;
  consulServiceName?: string;
  tags?: string[];
  address?: string;
  port?: number;
  localizacao?: string;
  tipo?: string;
  cod_localidade?: string;
  cidade?: string;
  provedor?: string;
  fabricante?: string;
  modelo?: string;
  tipo_dispositivo_abrev?: string;
  glpi_url?: string;
  notas?: string;
}

// COLUNAS FIXAS (não metadata) - sempre presentes
const FIXED_COLUMN_PRESETS: ColumnConfig[] = [
  { key: 'node', title: 'Nó', visible: true },
  { key: 'service', title: 'Serviço Consul', visible: true },
  { key: 'id', title: 'ID', visible: true },
  { key: 'address', title: 'Endereço', visible: false },
  { key: 'port', title: 'Porta', visible: false },
  { key: 'tags', title: 'Tags', visible: true },
  { key: 'actions', title: 'Ações', visible: true, locked: true },
];

const SERVICE_ID_SANITIZE_REGEX = /[[ \]`~!\\#$^&*=|"{}\':;?\t\n]+/g;

const sanitizeSegment = (value: string) =>
  value.trim().replace(SERVICE_ID_SANITIZE_REGEX, '_');

const composeServiceId = (values: ServiceFormValues) => {
  const parts = [
    sanitizeSegment(values.module),
    sanitizeSegment(values.company),
    sanitizeSegment(values.project),
    sanitizeSegment(values.env),
  ];
  const display = sanitizeSegment(values.serviceDisplayName);
  return `${parts.join('/')}`.concat(`@${display}`);
};
const buildServicePayload = (
  values: ServiceFormValues,
  id: string,
): ServiceCreatePayload => {
  const meta: Record<string, string> = {
    module: values.module,
    company: values.company,
    project: values.project,
    env: values.env,
    name: values.serviceDisplayName,
    instance: values.instance,
  };

  const optionalFields: Array<keyof ServiceFormValues> = [
    'address',
    'localizacao',
    'tipo',
    'cod_localidade',
    'cidade',
    'provedor',
    'fabricante',
    'modelo',
    'tipo_dispositivo_abrev',
    'glpi_url',
    'notas',
  ];

  optionalFields.forEach((field) => {
    const value = values[field];
    if (value !== undefined && value !== null && value !== '') {
      meta[field] = String(value);
    }
  });

  return {
    id,
    name: values.consulServiceName?.trim() || 'consul_service',
    address: values.address?.trim() || undefined,
    port: values.port,
    tags: values.tags,
    Meta: meta,
  };
};

const mapRecordToFormValues = (record: ServiceTableItem): ServiceFormValues => {
  const meta = record.meta || {};
  return {
    module: meta.module || '',
    company: meta.company || '',
    project: meta.project || '',
    env: meta.env || '',
    serviceDisplayName: meta.name || '',
    instance: meta.instance || '',
    consulServiceName: record.service || '',
    tags: record.tags || [],
    address: record.address || '',
    port: record.port,
    localizacao: meta.localizacao ? String(meta.localizacao) : undefined,
    tipo: meta.tipo ? String(meta.tipo) : undefined,
    cod_localidade: meta.cod_localidade ? String(meta.cod_localidade) : undefined,
    cidade: meta.cidade ? String(meta.cidade) : undefined,
    provedor: meta.provedor ? String(meta.provedor) : undefined,
    fabricante: meta.fabricante ? String(meta.fabricante) : undefined,
    modelo: meta.modelo ? String(meta.modelo) : undefined,
    tipo_dispositivo_abrev: meta.tipo_dispositivo_abrev
      ? String(meta.tipo_dispositivo_abrev)
      : undefined,
    glpi_url: meta.glpi_url ? String(meta.glpi_url) : undefined,
    notas: meta.notas ? String(meta.notas) : undefined,
  };
};
const Services: React.FC = () => {
  const actionRef = useRef<ActionType | null>(null);

  // SISTEMA DINÂMICO: Carregar campos metadata do backend
  const { tableFields, loading: tableFieldsLoading } = useTableFields('services');
  const { formFields, loading: formFieldsLoading } = useFormFields('services');
  const { filterFields, loading: filterFieldsLoading } = useFilterFields('services');

  // SISTEMA DINÂMICO: filters agora é dinâmico (qualquer campo metadata)
  const [filters, setFilters] = useState<Record<string, string | undefined>>({});
  const [metadataLoading, setMetadataLoading] = useState(false);
  const [metadataOptions, setMetadataOptions] = useState<Record<string, string[]>>({});
  const [nodes, setNodes] = useState<ConsulNode[]>([]);
  const [selectedNode, setSelectedNode] = useState<string>(ALL_NODES);
  const [detailRecord, setDetailRecord] = useState<ServiceTableItem | null>(null);
  const [formOpen, setFormOpen] = useState(false);
  const [formMode, setFormMode] = useState<'create' | 'edit'>('create');
  const [formInitialValues, setFormInitialValues] = useState<Partial<ServiceFormValues>>({
    consulServiceName: 'consul_service',
  });
  const [currentRecord, setCurrentRecord] = useState<ServiceTableItem | null>(null);
  const [selectedRowKeys, setSelectedRowKeys] = useState<React.Key[]>([]);
  const [selectedRows, setSelectedRows] = useState<ServiceTableItem[]>([]);
  const [summary, setSummary] = useState<{
    total: number;
    byEnv: Record<string, number>;
    byModule: Record<string, number>;
  }>({ total: 0, byEnv: {}, byModule: {} });
  const [tableSnapshot, setTableSnapshot] = useState<ServiceTableItem[]>([]);
  const [advancedOpen, setAdvancedOpen] = useState(false);
  const [advancedConditions, setAdvancedConditions] = useState<SearchCondition[]>([]);
  const [advancedOperator, setAdvancedOperator] = useState<'and' | 'or'>('and');
  // SISTEMA DINÂMICO: Combinar colunas fixas + campos metadata dinâmicos
  const defaultColumnConfig = useMemo<ColumnConfig[]>(() => {
    const metadataColumns: ColumnConfig[] = tableFields.map((field) => ({
      key: field.name,
      title: field.display_name,
      visible: field.show_in_table ?? true, // Exibir por padrão se show_in_table não definido
      locked: false,
    }));

    // ORDEM: node, service, id → campos metadata → address, port, tags, actions
    return [
      FIXED_COLUMN_PRESETS[0], // node
      FIXED_COLUMN_PRESETS[1], // service
      FIXED_COLUMN_PRESETS[2], // id
      ...metadataColumns,       // campos dinâmicos
      FIXED_COLUMN_PRESETS[3], // address
      FIXED_COLUMN_PRESETS[4], // port
      FIXED_COLUMN_PRESETS[5], // tags
      FIXED_COLUMN_PRESETS[6], // actions
    ];
  }, [tableFields]);

  const [columnConfig, setColumnConfig] = useState<ColumnConfig[]>([]);
  const [columnWidths, setColumnWidths] = useState<Record<string, number>>({});

  // Atualizar columnConfig quando defaultColumnConfig mudar
  useEffect(() => {
    if (defaultColumnConfig.length > 0 && columnConfig.length === 0) {
      setColumnConfig(defaultColumnConfig);
    }
  }, [defaultColumnConfig, columnConfig.length]);

  // Suporte para filtro via URL (ex: /services?service=nome_do_servico)
  const [searchParams, setSearchParams] = useSearchParams();
  const initialSearchValue = searchParams.get('service') || '';

  const [searchValue, setSearchValue] = useState<string>(initialSearchValue);
  const [searchInput, setSearchInput] = useState<string>(initialSearchValue);

  useEffect(() => {
    setSearchInput(searchValue);
  }, [searchValue]);

  const handleSearchSubmit = useCallback(
    (value: string) => {
      setSearchValue(value.trim());
      actionRef.current?.reload();
    },
    [],
  );

  // SISTEMA DINÂMICO: Gerar campos de busca avançada (campos fixos + metadata)
  const advancedFieldOptions = useMemo(() => {
    const fixedFields = [
      { label: 'Nó', value: 'node', type: 'text' },
      { label: 'Serviço Consul', value: 'service', type: 'text' },
      { label: 'Endereço', value: 'address', type: 'text' },
      { label: 'Tags', value: 'tags', type: 'text' },
    ];

    const metadataFields = tableFields.map((field) => ({
      label: field.display_name,
      value: field.name,
      type: 'text',
    }));

    return [...fixedFields, ...metadataFields];
  }, [tableFields]);

  // SISTEMA DINÂMICO: Extrair valor de campo (fixo ou metadata)
  const getFieldValue = useCallback((row: ServiceTableItem, field: string): string => {
    // Campos fixos
    switch (field) {
      case 'node':
        return row.node || '';
      case 'service':
        return row.service || '';
      case 'id':
        return row.id || '';
      case 'address':
        return row.address || '';
      case 'port':
        return typeof row.port === 'number' ? String(row.port) : '';
      case 'tags':
        return (row.tags || []).join(',');
      default:
        // CAMPOS METADATA DINÂMICOS: buscar em record.meta
        return row.meta?.[field] ? String(row.meta[field]) : '';
    }
  }, []);

  const applyAdvancedFilters = useCallback(
    (data: ServiceTableItem[]) => {
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
          const source = getFieldValue(row, condition.field).toLowerCase();
          const target = String(condition.value ?? '').toLowerCase();

          if (!target) {
            return true;
          }

          switch (condition.operator) {
            case 'eq':
              return source === target;
            case 'ne':
              return source !== target;
            case 'starts_with':
              return source.startsWith(target);
            case 'ends_with':
              return source.endsWith(target);
            case 'contains':
            default:
              return source.includes(target);
          }
        });

        return advancedOperator === 'or'
          ? evaluations.some(Boolean)
          : evaluations.every(Boolean);
      });
    },
    [advancedConditions, advancedOperator, getFieldValue],
  );

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

  const handleResize = useCallback(
    (columnKey: string) =>
      (_: React.SyntheticEvent, { size }: { size: { width: number } }) => {
        setColumnWidths((prev) => ({ ...prev, [columnKey]: size.width }));
      },
    [],
  );

  const nodeAddressMap = useMemo(() => {
    const map: Record<string, string> = {};
    nodes.forEach((node) => {
      if (node.node && node.addr) {
        map[node.node] = node.addr;
      }
    });
    return map;
  }, [nodes]);

  // SISTEMA DINÂMICO: Carregar valores dos campos metadata dinamicamente
  const loadMetadataOptions = useCallback(async () => {
    try {
      setMetadataLoading(true);

      // Buscar valores de TODOS os campos com show_in_filter=true
      if (filterFields.length === 0) {
        // Ainda carregando campos dinâmicos
        setMetadataOptions({});
        return;
      }

      // Criar promises para cada campo de filtro
      const promises = filterFields.map((field) =>
        consulAPI.getServiceMetadataValues(field.name),
      );

      const responses = await Promise.all(promises);

      // Montar objeto de opções dinamicamente
      const options: Record<string, string[]> = {};
      filterFields.forEach((field, index) => {
        const values = responses[index].data.values || [];

        // CASO ESPECIAL: campo 'module' inclui módulos padrão
        if (field.name === 'module') {
          options[field.name] = Array.from(new Set([...DEFAULT_MODULES, ...values]));
        } else {
          options[field.name] = values;
        }
      });

      setMetadataOptions(options);
    } catch (error) {
      message.error('Falha ao carregar metadados do Consul');
    } finally {
      setMetadataLoading(false);
    }
  }, [filterFields]);

  const loadNodes = useCallback(async () => {
    try {
      const response = await consulAPI.getNodes();
      const list = response.data?.data || [];
      setNodes(list);
    } catch (error) {
      message.error('Falha ao carregar nos do cluster');
    }
  }, []);

  // Carregar nodes imediatamente
  useEffect(() => {
    loadNodes();
  }, [loadNodes]);

  // Carregar opções de metadata apenas quando filterFields estiver disponível
  useEffect(() => {
    if (!filterFieldsLoading && filterFields.length > 0) {
      loadMetadataOptions();
    }
  }, [filterFields, filterFieldsLoading, loadMetadataOptions]);

  useEffect(() => {
    actionRef.current?.reload();
  }, [filters, selectedNode, advancedConditions, advancedOperator]);

  // SISTEMA DINÂMICO: buildQueryParams aceita filtros dinâmicos
  const buildQueryParams = useCallback((): ServiceQuery => {
    const params: ServiceQuery = { ...filters } as ServiceQuery;
    if (selectedNode === ALL_NODES) {
      params.node_addr = 'ALL';
    } else if (selectedNode === DEFAULT_NODE) {
      delete params.node_addr;
    } else if (selectedNode) {
      params.node_addr = selectedNode;
    }
    return params;
  }, [filters, selectedNode]);

  const flattenServices = useCallback(
    (data: Record<string, Record<string, ConsulServiceRecord>>) => {
      const rows: ServiceTableItem[] = [];
      Object.entries(data || {}).forEach(([nodeName, services]) => {
        Object.entries(services || {}).forEach(([serviceId, rawService]) => {
          const service = rawService || ({} as ConsulServiceRecord);
          rows.push({
            key: `${nodeName}::${serviceId}`,
            id: serviceId,
            node: nodeName,
            nodeAddr: nodeAddressMap[nodeName],
            service: service.Service || '',
            tags: service.Tags || [],
            address: service.Address,
            port: service.Port,
            meta: (service.Meta || {}) as ServiceMeta,
          });
        });
      });
      return rows;
    },
    [nodeAddressMap],
  );

  const requestHandler = useCallback(
    async (params: { current?: number; pageSize?: number; keyword?: string }) => {
      try {
        // 🚀 USAR ENDPOINT OTIMIZADO - Processamento no backend!
        const queryParams = buildQueryParams();
        const nodeAddr = queryParams.node_addr === 'ALL' ? undefined : queryParams.node_addr;

        const response = await consulAPI.getServicesInstancesOptimized(false, nodeAddr);
        const { data: backendRows, summary: backendSummary } = response.data;

        // Converter para formato esperado pela tabela
        let rows: ServiceTableItem[] = backendRows.map((item: any) => ({
          key: item.key,
          id: item.id,
          node: item.node,
          nodeAddr: item.nodeAddr,
          service: item.service,
          tags: item.tags || [],
          address: item.address,
          port: item.port,
          meta: item.meta || {},
        }));

        // Aplicar filtros avançados (se houver)
        const advancedRows = applyAdvancedFilters(rows);

        const nextSummary = advancedRows.reduce(
          (acc, item) => {
            acc.total += 1;
            const envKey = item.meta?.env || 'desconhecido';
            acc.byEnv[envKey] = (acc.byEnv[envKey] || 0) + 1;
            const moduleKey = item.meta?.module || 'desconhecido';
            acc.byModule[moduleKey] = (acc.byModule[moduleKey] || 0) + 1;
            return acc;
          },
          { total: 0, byEnv: {} as Record<string, number>, byModule: {} as Record<string, number> },
        );
        setSummary(nextSummary);

        const keywordRaw = (params?.keyword ?? searchValue) || '';
        const keyword = keywordRaw.trim().toLowerCase();
        let searchedRows = advancedRows;
        if (keyword) {
          searchedRows = advancedRows.filter((item) => {
            const fields = [
              item.service,
              item.id,
              item.meta?.name,
              item.meta?.instance,
              item.meta?.company,
              item.meta?.project,
              item.node,
            ];
            return fields.some(
              (field) =>
                field && String(field).toLowerCase().includes(keyword),
            );
          });
        }

        setTableSnapshot(searchedRows);

        const current = params?.current ?? 1;
        const pageSize = params?.pageSize ?? 25;
        const start = (current - 1) * pageSize;
        const paginatedRows = searchedRows.slice(start, start + pageSize);

        return {
          data: paginatedRows,
          success: true,
          total: searchedRows.length,
        };
      } catch (error) {
        message.error('Falha ao carregar serviços do Consul');
        return {
          data: [],
          success: false,
          total: 0,
        };
      }
    },
    [applyAdvancedFilters, buildQueryParams, flattenServices, nodes, searchValue, selectedNode],
  );
  const openCreateModal = useCallback(() => {
    setFormMode('create');
    setCurrentRecord(null);
    setFormInitialValues({
      consulServiceName: 'consul_service',
      tags: [],
    });
    setFormOpen(true);
  }, []);

  useEffect(() => {
    if (searchParams.get('create') === 'true') {
      openCreateModal();
      const next = new URLSearchParams(searchParams);
      next.delete('create');
      setSearchParams(next, { replace: true });
    }
  }, [searchParams, setSearchParams, openCreateModal]);

  const openEditModal = useCallback((record: ServiceTableItem) => {
    setFormMode('edit');
    setCurrentRecord(record);
    setFormInitialValues(mapRecordToFormValues(record));
    setFormOpen(true);
  }, []);

  const handleDelete = useCallback(
    async (record: ServiceTableItem) => {
      try {
        const nodeAddrParam =
          selectedNode && selectedNode !== ALL_NODES && selectedNode !== DEFAULT_NODE
            ? selectedNode
            : record.nodeAddr;

        const params =
          nodeAddrParam && nodeAddrParam !== ''
            ? { node_addr: nodeAddrParam }
            : undefined;

        await consulAPI.deleteService(record.id, params);
      message.success('Serviço removido com sucesso');
        await loadMetadataOptions();
        actionRef.current?.reload();
      } catch (error: any) {
        const detail =
          error?.response?.data?.detail ||
          error?.response?.data?.error ||
          error?.message;
      message.error(`Falha ao remover serviço: ${detail}`);
      }
    },
    [loadMetadataOptions, selectedNode],
  );

  const handleBatchDelete = useCallback(async () => {
    if (!selectedRows.length) {
      return;
    }
    try {
      await Promise.all(
        selectedRows.map((record) => {
          const nodeAddrParam =
            record.nodeAddr ||
            (selectedNode !== ALL_NODES && selectedNode !== DEFAULT_NODE
              ? selectedNode
              : undefined);
          const params =
            nodeAddrParam && nodeAddrParam !== ''
              ? { node_addr: nodeAddrParam }
              : undefined;
          return consulAPI.deleteService(record.id, params);
        }),
      );
      message.success('Serviços removidos com sucesso');
      setSelectedRowKeys([]);
      setSelectedRows([]);
      await loadMetadataOptions();
      actionRef.current?.reload();
    } catch (error) {
      message.error('Falha ao remover um ou mais serviços');
    }
  }, [loadMetadataOptions, selectedNode, selectedRows]);

  const handleSubmit = useCallback(
    async (values: ServiceFormValues) => {
      try {
        const id =
          formMode === 'edit' && currentRecord
            ? currentRecord.id
            : composeServiceId(values);

        const payload = buildServicePayload(values, id);

        if (formMode === 'create') {
          await consulAPI.createService(payload);
        message.success('Serviço criado com sucesso');
        } else if (currentRecord) {
          const updatePayload = {
            address: payload.address,
            port: payload.port,
            tags: payload.tags,
            Meta: payload.Meta,
            node_addr: currentRecord.nodeAddr || currentRecord.node, // CRITICAL: Necessário para identificar o nó
          };
          await consulAPI.updateService(currentRecord.id, updatePayload);
        message.success('Serviço atualizado com sucesso');
        }

        setFormOpen(false);
        setCurrentRecord(null);
        await loadMetadataOptions();
        actionRef.current?.reload();
        return true;
      } catch (error: any) {
        const detailMessage =
          error?.response?.data?.detail?.detail ||
          error?.response?.data?.detail?.message ||
          error?.response?.data?.detail ||
          error?.message ||
          'Erro desconhecido';
        message.error(`Falha ao salvar serviço: ${detailMessage}`);
        return false;
      }
    },
    [currentRecord, formMode, loadMetadataOptions],
  );
  // SISTEMA DINÂMICO: Gerar columnMap combinando fixas + metadata
  const columnMap = useMemo<Record<string, ServiceColumn<ServiceTableItem>>>(() => {
    // COLUNAS FIXAS com lógica específica
    const fixedColumns: Record<string, ServiceColumn<ServiceTableItem>> = {
      node: {
        title: 'Nó',
        dataIndex: 'node',
        width: 160,
        ellipsis: true,
      },
      service: {
        title: 'Serviço Consul',
        dataIndex: 'service',
        width: 210,
        ellipsis: true,
        render: (_, record) => (
          <Space size={4}>
            <InfoCircleOutlined style={{ color: '#1677ff' }} />
            <Text>{record.service}</Text>
          </Space>
        ),
      },
      id: {
        title: 'ID',
        dataIndex: 'id',
        copyable: true,
        ellipsis: true,
        width: 260,
      },
      address: {
        title: 'Endereço',
        dataIndex: 'address',
        width: 220,
        ellipsis: true,
      },
      port: {
        title: 'Porta',
        dataIndex: 'port',
        width: 100,
        align: 'center',
      },
      tags: {
        title: 'Tags',
        dataIndex: 'tags',
        width: 220,
        render: (_, record) => (
          <Space size={[4, 4]} wrap>
            {(record.tags || []).map((tag) => (
              <Tag key={`${record.id}-${tag}`}>{tag}</Tag>
            ))}
          </Space>
        ),
      },
      actions: {
        title: 'Ações',
        valueType: 'option',
        fixed: 'right',
        width: 140,
        render: (_, record) => [
          <Tooltip title="Ver detalhes" key={`detail-${record.id}`}>
            <Button
              type="link"
              icon={<InfoCircleOutlined />}
              aria-label="Ver detalhes"
              onClick={() => setDetailRecord(record)}
            />
          </Tooltip>,
          <Tooltip title="Editar serviço" key={`edit-${record.id}`}>
            <Button
              type="link"
              icon={<EditOutlined />}
              aria-label="Editar serviço"
              onClick={() => openEditModal(record)}
            />
          </Tooltip>,
          <Popconfirm
            key={`delete-${record.id}`}
            title="Remover este serviço?"
            onConfirm={() => handleDelete(record)}
            okText="Remover"
            cancelText="Cancelar"
          >
            <Tooltip title="Remover serviço">
              <Button
                type="link"
                danger
                icon={<DeleteOutlined />}
                aria-label="Remover serviço"
              />
            </Tooltip>
          </Popconfirm>,
        ],
      },
    };

    // COLUNAS METADATA DINÂMICAS
    const metadataColumns: Record<string, ServiceColumn<ServiceTableItem>> = {};
    tableFields.forEach((field) => {
      metadataColumns[field.name] = {
        title: field.display_name,
        dataIndex: ['meta', field.name],
        width: field.field_type === 'string' ? 200 : 140,
        ellipsis: true,
        tooltip: field.description,
      };
    });

    // Combinar fixas + dinâmicas
    return { ...fixedColumns, ...metadataColumns };
  }, [tableFields, handleDelete, openEditModal]);

  const visibleColumns = useMemo(() => {
    return columnConfig
      .filter((column) => column.visible)
      .map((column) => {
        const col = columnMap[column.key];
        if (!col) return null;
        const width = columnWidths[column.key] || col.width;
        return {
          ...col,
          width,
          onHeaderCell: (col: any) => ({
            width,
            onResize: handleResize(column.key),
          }),
        };
      })
      .filter(Boolean) as ServiceColumn<ServiceTableItem>[];
  }, [columnConfig, columnMap, columnWidths, handleResize]);

  const handleExport = useCallback(() => {
    if (!tableSnapshot.length) {
      message.info('Nao ha dados para exportar');
      return;
    }

    const sanitize = (value: unknown) =>
      String(value ?? '').replace(/[\r\n]+/g, ' ').replace(/;/g, ',');

    const header = [
      'node',
      'service',
      'id',
      'name',
      'module',
      'company',
      'grupo_monitoramento',
      'tipo_monitoramento',
      'instance',
      'address',
      'port',
      'tags',
      'meta_json',
    ];

    const rows = tableSnapshot.map((record) => {
      const meta = record.meta || {};
      return [
        sanitize(record.node),
        sanitize(record.service),
        sanitize(record.id),
        sanitize(meta.name),
        sanitize(meta.module),
        sanitize(meta.company),
        sanitize(meta.project),
        sanitize(meta.env),
        sanitize(meta.instance),
        sanitize(record.address),
        sanitize(record.port),
        sanitize((record.tags || []).join('|')),
        sanitize(JSON.stringify(meta)),
      ].join(';');
    });

    const csvContent = [header.join(';'), ...rows].join('\n');
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `services-${new Date().toISOString()}.csv`;
    link.click();
    URL.revokeObjectURL(url);
  }, [tableSnapshot]);

  const nodeSelector = (
    <Select
      value={selectedNode}
      style={{ minWidth: 220 }}
      onChange={(value) => setSelectedNode(value)}
    >
      <Option value={ALL_NODES}>Todos os nos</Option>
      <Option value={DEFAULT_NODE}>Servidor principal</Option>
      {nodes.map((node) => (
        <Option value={node.addr} key={node.addr}>
          {`${node.node} (${node.addr})`}
        </Option>
      ))}
    </Select>
  );

  const advancedActive = advancedConditions.some(
    (condition) => condition.field && condition.value !== undefined && condition.value !== '',
  );
  return (
    <PageContainer
      header={{
        title: 'Gerenciamento de Serviços',
        subTitle: 'Visualize, filtre e gerencie os serviços registrados no Consul',
      }}
    >
      <Space direction="vertical" size="middle" style={{ width: '100%' }}>
        {/* Summary Cards */}
        <Card>
          <Space size="large" wrap>
            <Statistic
              title="Serviços registrados"
              value={summary.total}
              prefix={<CloudOutlined />}
              valueStyle={{ color: '#3f8600' }}
            />
            <Statistic
              title="Ambientes distintos"
              value={Object.keys(summary.byEnv).length}
              suffix=" ambientes"
            />
            <Statistic
              title="Modulos distintos"
              value={Object.keys(summary.byModule).length}
              suffix=" modulos"
            />
          </Space>
        </Card>

        {/* Filters and Actions */}
        <Card size="small">
          <Space direction="vertical" size="middle" style={{ width: '100%' }}>
            <Space wrap>
              <MetadataFilterBar
                fields={filterFields}
                value={filters}
                options={metadataOptions}
                loading={metadataLoading || filterFieldsLoading}
                onChange={setFilters}
                onReset={() => setFilters({})}
                extra={nodeSelector}
              />
            </Space>

            <Space wrap>
              <Search
                allowClear
                placeholder="Buscar por nome, instancia ou ID"
                enterButton
                style={{ width: 300 }}
                value={searchInput}
                onChange={(event) => {
                  const next = event.target.value;
                  setSearchInput(next);
                  if (!next) {
                    handleSearchSubmit('');
                  }
                }}
                onSearch={handleSearchSubmit}
              />

              <Button
                icon={<FilterOutlined />}
                type={advancedActive ? 'primary' : 'default'}
                onClick={() => setAdvancedOpen(true)}
              >
                Busca Avancada
                {advancedConditions.length > 0 && ` (${advancedConditions.length})`}
              </Button>

              {advancedActive && (
                <Button
                  icon={<ClearOutlined />}
                  onClick={handleAdvancedClear}
                >
                  Limpar Filtros Avancados
                </Button>
              )}

              <ColumnSelector
                columns={columnConfig}
                onChange={setColumnConfig}
                storageKey="services-columns"
              />

              <Button
                icon={<DownloadOutlined />}
                onClick={handleExport}
              >
                Exportar CSV
              </Button>

              <Button
                icon={<ReloadOutlined />}
                onClick={() => actionRef.current?.reload()}
              >
                Atualizar
              </Button>

              <Popconfirm
                title="Remover serviços selecionados?"
                description="Esta acao removera os serviços selecionados do Consul. Tem certeza?"
                onConfirm={handleBatchDelete}
                disabled={!selectedRows.length}
                okText="Sim"
                cancelText="Nao"
              >
                <Tooltip title="Remover serviços selecionados">
                  <Button
                    danger
                    icon={<DeleteOutlined />}
                    disabled={!selectedRows.length}
                  >
                    Remover selecionados ({selectedRows.length})
                  </Button>
                </Tooltip>
              </Popconfirm>

              <Button
                type="primary"
                icon={<PlusOutlined />}
                onClick={openCreateModal}
              >
                Novo serviço
              </Button>
            </Space>

          </Space>
        </Card>

        {/* Table */}
        <ProTable<ServiceTableItem>
          rowKey="key"
          columns={visibleColumns}
          search={false}
          actionRef={actionRef}
          request={requestHandler}
          params={{ keyword: searchValue }}
          pagination={{
            defaultPageSize: 25,
            showSizeChanger: true,
            pageSizeOptions: ['10', '20', '30', '50', '100'],
          }}
          scroll={{ x: 1400 }}
          locale={{ emptyText: 'Nenhum dado disponivel' }}
          options={{ density: true, fullScreen: true, reload: false, setting: false }}
          components={{
            header: {
              cell: ResizableTitle,
            },
          }}
          expandable={{
            expandedRowRender: (record) => (
              <Descriptions size="small" column={2} bordered style={{ margin: 0 }}>
                {Object.entries(record.meta || {}).map(([key, value]) => (
                  <Descriptions.Item label={key} key={`${record.id}-${key}`}>
                    {String(value ?? '')}
                  </Descriptions.Item>
                ))}
                {record.tags?.length ? (
                  <Descriptions.Item label="Tags">
                    <Space size={[4, 4]} wrap>
                      {record.tags.map((tag) => (
                        <Tag key={`${record.id}-expanded-${tag}`}>{tag}</Tag>
                      ))}
                    </Space>
                  </Descriptions.Item>
                ) : null}
              </Descriptions>
            ),
            rowExpandable: (record) =>
              Boolean(record.meta && Object.keys(record.meta || {}).length > 0),
          }}
          rowSelection={{
            selectedRowKeys,
            onChange: (keys, rows) => {
              setSelectedRowKeys(keys);
              setSelectedRows(rows as ServiceTableItem[]);
            },
          }}
          tableAlertRender={({ selectedRowKeys: keys }) =>
            keys.length ? <span>{`${keys.length} serviços selecionados`}</span> : null
          }
        />
      </Space>

      <Drawer
        width={720}
        title="Pesquisa avancada"
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

      <Drawer
        width={520}
        title="Detalhes do serviço"
        open={!!detailRecord}
        destroyOnHidden
        onClose={() => setDetailRecord(null)}
      >
        {detailRecord && (
          <ProDescriptions
            column={1}
            dataSource={{
              ...detailRecord,
              ...detailRecord.meta,
            }}
          >
            <ProDescriptions.Item label="ID">
              {detailRecord.id}
            </ProDescriptions.Item>
            <ProDescriptions.Item label="No">
              {detailRecord.node}
            </ProDescriptions.Item>
            <ProDescriptions.Item label="Serviço Consul">
              {detailRecord.service}
            </ProDescriptions.Item>
            <ProDescriptions.Item label="Endereco">
              {detailRecord.address || 'Nao informado'}
            </ProDescriptions.Item>
            <ProDescriptions.Item label="Porta">
              {detailRecord.port ?? 'Nao informado'}
            </ProDescriptions.Item>
            {Object.entries(detailRecord.meta || {}).map(([key, value]) => (
              <ProDescriptions.Item label={key} key={key}>
                {String(value ?? '')}
              </ProDescriptions.Item>
            ))}
            <ProDescriptions.Item label="Tags">
              <Space size={[4, 4]} wrap>
                {(detailRecord.tags || []).map((tag) => (
                  <Tag key={`${detailRecord.id}-drawer-${tag}`}>{tag}</Tag>
                ))}
              </Space>
            </ProDescriptions.Item>
          </ProDescriptions>
        )}
      </Drawer>

      <ModalForm<ServiceFormValues>
        title={formMode === 'create' ? 'Novo serviço' : 'Editar serviço'}
        width={760}
        open={formOpen}
        initialValues={formInitialValues}
        modalProps={{
          destroyOnHidden: true,
          onCancel: () => {
            setFormOpen(false);
            setCurrentRecord(null);
          },
        }}
        submitter={{
          searchConfig: {
            submitText: formMode === 'create' ? 'Criar serviço' : 'Salvar alteracoes',
          },
        }}
        onFinish={handleSubmit}
      >
        <div style={FORM_ROW_STYLE}>
          <ProFormSelect
            name="module"
            label="Modulo"
            placeholder="Selecione o modulo"
            options={metadataOptions.modules.map((module) => ({
              label: module,
              value: module,
            }))}
            rules={[{ required: true, message: 'Informe o modulo' }]}
            fieldProps={{ showSearch: true }}
          />
          <ProFormText
            name="consulServiceName"
            label="Serviço no Consul"
            placeholder="Ex: blackbox_exporter"
            rules={[{ required: true, message: 'Informe o nome do serviço no Consul' }]}
          />
        </div>

        <div style={FORM_ROW_STYLE}>
          <ProFormText
            name="serviceDisplayName"
            label="Nome exibido"
            placeholder="Nome amigavel do serviço"
            rules={[{ required: true, message: 'Informe o nome do serviço' }]}
          />
          <ProFormText
            name="instance"
            label="Instancia (IP/URL)"
            placeholder="Ex: 192.168.0.1 ou https://exemplo.com"
            rules={[{ required: true, message: 'Informe a instancia' }]}
          />
        </div>

        <div style={FORM_ROW_STYLE}>
          <ProFormText
            name="company"
            label="Empresa"
            placeholder="Organizacao responsavel"
            rules={[{ required: true, message: 'Informe a empresa' }]}
          />
          <ProFormText
            name="grupo_monitoramento"
            label="Grupo Monitoramento"
            placeholder="Grupo de monitoramento (projeto)"
            rules={[{ required: true, message: 'Informe o grupo de monitoramento' }]}
          />
          <ProFormText
            name="tipo_monitoramento"
            label="Tipo Monitoramento"
            placeholder="Ex: prod, dev, homolog"
            rules={[{ required: true, message: 'Informe o tipo de monitoramento' }]}
          />
        </div>

        <div style={FORM_ROW_STYLE}>
          <ProFormText
            name="address"
            label="Endereco"
            placeholder="Opcional - endereco para verificacao"
          />
          <ProFormDigit
            name="port"
            label="Porta"
            placeholder="Porta do serviço"
            min={1}
            max={65535}
          />
        </div>

        <ProFormSelect
          name="tags"
          label="Tags"
          mode="tags"
          placeholder="Adicione tags para classificacao"
          fieldProps={{
            tokenSeparators: [','],
          }}
        />

        <div style={FORM_ROW_STYLE}>
          <ProFormText
            name="localizacao"
            label="Localizacao"
            placeholder="Ex: Data center principal"
          />
          <ProFormText
            name="tipo"
            label="Tipo"
            placeholder="Categoria do recurso"
          />
        </div>

        <div style={FORM_ROW_STYLE}>
          <ProFormText
            name="cod_localidade"
            label="Codigo local"
            placeholder="Identificador interno da localidade"
          />
          <ProFormText
            name="cidade"
            label="Cidade"
            placeholder="Cidade do recurso"
          />
          <ProFormText
            name="provedor"
            label="Provedor"
            placeholder="Provedor do serviço"
          />
        </div>

        <div style={FORM_ROW_STYLE}>
          <ProFormText
            name="fabricante"
            label="Fabricante"
            placeholder="Fabricante do equipamento"
          />
          <ProFormText
            name="modelo"
            label="Modelo"
            placeholder="Modelo do equipamento"
          />
          <ProFormText
            name="tipo_dispositivo_abrev"
            label="Tipo (sigla)"
            placeholder="Ex: RTR, SRV"
          />
        </div>

        <ProFormText
          name="glpi_url"
          label="URL GLPI"
          placeholder="Link para o ativo no GLPI"
        />

        <ProFormTextArea
          name="notas"
          label="Notas"
          placeholder="Informacoes adicionais sobre o serviço"
          fieldProps={{ rows: 3 }}
        />
      </ModalForm>
    </PageContainer>
  );
};

export default Services;

