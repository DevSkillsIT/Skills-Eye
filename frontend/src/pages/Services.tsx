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
  MetadataFilters,
  ServiceMeta,
  ServiceCreatePayload,
  ServiceQuery,
} from '../services/api';

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

const SERVICE_COLUMN_PRESETS: ColumnConfig[] = [
  { key: 'node', title: 'No', visible: true },
  { key: 'service', title: 'Serviço Consul', visible: true },
  { key: 'id', title: 'ID', visible: true },
  { key: 'name', title: 'Nome exibido', visible: true },
  { key: 'module', title: 'Modulo', visible: true },
  { key: 'company', title: 'Empresa', visible: true },
  { key: 'project', title: 'Projeto', visible: true },
  { key: 'env', title: 'Ambiente', visible: true },
  { key: 'instance', title: 'Instancia', visible: true },
  { key: 'address', title: 'Endereco', visible: false },
  { key: 'port', title: 'Porta', visible: false },
  { key: 'tags', title: 'Tags', visible: true },
  { key: 'actions', title: 'Acoes', visible: true, locked: true },
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
  const [filters, setFilters] = useState<MetadataFilters>({});
  const [metadataLoading, setMetadataLoading] = useState(false);
  const [metadataOptions, setMetadataOptions] = useState({
    modules: [] as string[],
    companies: [] as string[],
    projects: [] as string[],
    envs: [] as string[],
  });
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
  const [columnConfig, setColumnConfig] = useState<ColumnConfig[]>(() =>
    SERVICE_COLUMN_PRESETS.map((column) => ({ ...column })),
  );
  const [columnWidths, setColumnWidths] = useState<Record<string, number>>({});

  // Suporte para filtro via URL (ex: /services?service=nome_do_servico)
  const [searchParams] = useSearchParams();
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

  const advancedFieldOptions = useMemo(
    () => [
      { label: 'Nome exibido', value: 'name', type: 'text' },
      { label: 'Modulo', value: 'module', type: 'text' },
      { label: 'Empresa', value: 'company', type: 'text' },
      { label: 'Projeto', value: 'project', type: 'text' },
      { label: 'Ambiente', value: 'env', type: 'text' },
      { label: 'Instancia', value: 'instance', type: 'text' },
      { label: 'Endereco', value: 'address', type: 'text' },
      { label: 'Tags', value: 'tags', type: 'text' },
      { label: 'No', value: 'node', type: 'text' },
      { label: 'Serviço Consul', value: 'service', type: 'text' },
    ],
    [],
  );

  const getFieldValue = useCallback((row: ServiceTableItem, field: string): string => {
    switch (field) {
      case 'node':
        return row.node || '';
      case 'service':
        return row.service || '';
      case 'id':
        return row.id || '';
      case 'name':
        return row.meta?.name || '';
      case 'module':
        return row.meta?.module || '';
      case 'company':
        return row.meta?.company || '';
      case 'project':
        return row.meta?.project || '';
      case 'env':
        return row.meta?.env || '';
      case 'instance':
        return row.meta?.instance || '';
      case 'address':
        return row.address || '';
      case 'port':
        return typeof row.port === 'number' ? String(row.port) : '';
      case 'tags':
        return (row.tags || []).join(',');
      default:
        return '';
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

  const loadMetadataOptions = useCallback(async () => {
    try {
      setMetadataLoading(true);
      const [modulesRes, companiesRes, projectsRes, envsRes] = await Promise.all([
        consulAPI.getServiceMetadataValues('module'),
        consulAPI.getServiceMetadataValues('company'),
        consulAPI.getServiceMetadataValues('project'),
        consulAPI.getServiceMetadataValues('env'),
      ]);

      setMetadataOptions({
        modules: Array.from(
          new Set([
            ...DEFAULT_MODULES,
            ...(modulesRes.data.values || []),
          ]),
        ),
        companies: companiesRes.data.values || [],
        projects: projectsRes.data.values || [],
        envs: envsRes.data.values || [],
      });
    } catch (error) {
      message.error('Falha ao carregar metadados do Consul');
    } finally {
      setMetadataLoading(false);
    }
  }, []);

  const loadNodes = useCallback(async () => {
    try {
      const response = await consulAPI.getNodes();
      const list = response.data?.data || [];
      setNodes(list);
    } catch (error) {
      message.error('Falha ao carregar nos do cluster');
    }
  }, []);

  useEffect(() => {
    loadMetadataOptions();
    loadNodes();
  }, [loadMetadataOptions, loadNodes]);

  useEffect(() => {
    actionRef.current?.reload();
  }, [filters, selectedNode, advancedConditions, advancedOperator]);

  const buildQueryParams = useCallback((): ServiceQuery => {
    const params: ServiceQuery = { ...filters };
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
        const queryParams = buildQueryParams();
        const response = await consulAPI.listServices(queryParams);
        const payload = response.data;
        let rows: ServiceTableItem[] = [];

        if (queryParams.node_addr === 'ALL') {
          rows = flattenServices(payload.data || {});
        } else {
          const nodeName =
            payload.node ||
            selectedNode ||
            (nodes[0]?.node ? nodes[0].node : 'Servidor principal');
          const nodeServices = payload.data || {};
          rows = flattenServices({ [nodeName]: nodeServices });
        }

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
  const columnMap = useMemo<Record<string, ServiceColumn<ServiceTableItem>>>(
    () => ({
      node: {
        title: 'No',
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
      name: {
        title: 'Nome exibido',
        dataIndex: ['meta', 'name'],
        width: 220,
        ellipsis: true,
      },
      module: {
        title: 'Modulo',
        dataIndex: ['meta', 'module'],
        width: 150,
      },
      company: {
        title: 'Empresa',
        dataIndex: ['meta', 'company'],
        width: 200,
        ellipsis: true,
      },
      project: {
        title: 'Projeto',
        dataIndex: ['meta', 'project'],
        width: 200,
        ellipsis: true,
      },
      env: {
        title: 'Ambiente',
        dataIndex: ['meta', 'env'],
        width: 140,
      },
      instance: {
        title: 'Instancia',
        dataIndex: ['meta', 'instance'],
        width: 220,
        ellipsis: true,
      },
      address: {
        title: 'Endereco',
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
        title: 'Acoes',
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
          <Tooltip title="Editar servico" key={`edit-${record.id}`}>
            <Button
              type="link"
              icon={<EditOutlined />}
              aria-label="Editar servico"
              onClick={() => openEditModal(record)}
            />
          </Tooltip>,
          <Popconfirm
            key={`delete-${record.id}`}
            title="Remover este servico?"
            onConfirm={() => handleDelete(record)}
            okText="Remover"
            cancelText="Cancelar"
          >
            <Tooltip title="Remover servico">
              <Button
                type="link"
                danger
                icon={<DeleteOutlined />}
                aria-label="Remover servico"
              />
            </Tooltip>
          </Popconfirm>,
        ],
      },
    }),
    [handleDelete, openEditModal],
  );

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
      'project',
      'env',
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

  const advancedSearchFields = useMemo(
    () => [
      { label: 'Servico', value: 'service', type: 'text' },
      { label: 'No', value: 'node', type: 'text' },
      { label: 'Modulo', value: 'module', type: 'text' },
      { label: 'Empresa', value: 'company', type: 'text' },
      { label: 'Projeto', value: 'project', type: 'text' },
      { label: 'Ambiente', value: 'env', type: 'text' },
      { label: 'Instancia', value: 'instance', type: 'text' },
    ],
    [],
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
                value={filters}
                options={metadataOptions}
                loading={metadataLoading}
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
          availableFields={advancedSearchFields}
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
            name="project"
            label="Projeto"
            placeholder="Projeto associado"
            rules={[{ required: true, message: 'Informe o projeto' }]}
          />
          <ProFormText
            name="env"
            label="Ambiente"
            placeholder="Ex: prod, dev, homolog"
            rules={[{ required: true, message: 'Informe o ambiente' }]}
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

