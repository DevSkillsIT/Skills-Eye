
import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  Button,
  Card,
  Descriptions,
  Drawer,
  Input,
  message,
  Popconfirm,
  Space,
  Spin,
  Statistic,
  Tag,
  Tabs,
  Tooltip,
  Typography,
  Upload,
  Select,
} from 'antd';
import type { UploadProps } from 'antd';
import {
  CloudOutlined,
  DeleteOutlined,
  DownloadOutlined,
  EditOutlined,
  ImportOutlined,
  InfoCircleOutlined,
  PlusOutlined,
  ReloadOutlined,
  FilterOutlined,
  ClearOutlined,
} from '@ant-design/icons';
import type { ActionType } from '@ant-design/pro-components';
import {
  ModalForm,
  PageContainer,
  ProDescriptions,
  ProFormSwitch,
  ProFormText,
  ProFormTextArea,
  ProTable,
} from '@ant-design/pro-components';
import ColumnSelector, { type ColumnConfig } from '../components/ColumnSelector';
import MetadataFilterBar from '../components/MetadataFilterBar';
import AdvancedSearchPanel, { type SearchCondition } from '../components/AdvancedSearchPanel';
import ResizableTitle from '../components/ResizableTitle';
import { consulAPI } from '../services/api';
import type {
  BlackboxListResponse,
  BlackboxTargetPayload,
  BlackboxTargetRecord,
} from '../services/api';
import { useSearchParams } from 'react-router-dom';
import { useTableFields, useFormFields, useFilterFields } from '../hooks/useMetadataFields';
import { useBatchEnsure } from '../hooks/useReferenceValues';
import { useServiceTags } from '../hooks/useServiceTags';

const { Paragraph } = Typography;
const { Search } = Input;

interface BlackboxTableItem extends BlackboxTargetRecord {
  key: string;
}

type TableColumn<T> = import('@ant-design/pro-components').ProColumns<T>;

// COLUNAS FIXAS (não metadata) - sempre presentes
const FIXED_BLACKBOX_COLUMNS: ColumnConfig[] = [
  { key: 'service', title: 'Serviço', visible: true },
  { key: 'node', title: 'Nó', visible: false },
  { key: 'interval', title: 'Intervalo', visible: false },
  { key: 'timeout', title: 'Timeout', visible: false },
  { key: 'enabled', title: 'Ativo', visible: true },
  { key: 'tags', title: 'Tags', visible: false },
  { key: 'actions', title: 'Ações', visible: true, locked: true },
];

const DEFAULT_BLACKBOX_MODULES = [
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

const ALL_NODES = 'ALL';
const DEFAULT_PAGE_SIZE = 20;

const FORM_ROW_STYLE: React.CSSProperties = {
  display: 'grid',
  gap: 16,
  gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
};

const mapRecordToPayload = (record: BlackboxTargetRecord): BlackboxTargetPayload => ({
  module: record.meta?.module || '',
  company: record.meta?.company || '',
  project: record.meta?.project || '',
  env: record.meta?.env || '',
  name: record.meta?.name || '',
  instance: record.meta?.instance || '',
  group: record.meta?.group || (record.kv as any)?.group || undefined,
  interval: record.meta?.interval || (record.kv as any)?.interval || '30s',
  timeout: record.meta?.timeout || (record.kv as any)?.timeout || '10s',
  enabled: record.meta?.enabled ?? ((record.kv as any)?.enabled ?? true),
  labels:
    (record.meta?.labels as Record<string, string> | undefined) ||
    ((record.kv as any)?.labels as Record<string, string> | undefined) ||
    undefined,
  notes: (record.meta as any)?.notes || (record.kv as any)?.notes || undefined,
});

const stringifyLabels = (labels?: Record<string, string>) => {
  if (!labels || Object.keys(labels).length === 0) {
    return '';
  }
  return JSON.stringify(labels, null, 2);
};

const parseLabelsText = (input?: string): Record<string, string> | undefined => {
  if (!input) return undefined;
  const trimmed = input.trim();
  if (!trimmed) return undefined;

  if (trimmed.startsWith('{')) {
    try {
      const parsed = JSON.parse(trimmed) as Record<string, unknown>;
      const normalized: Record<string, string> = {};
      Object.entries(parsed || {}).forEach(([key, value]) => {
        if (typeof key === 'string' && value !== undefined && value !== null) {
          normalized[key] = String(value);
        }
      });
      return Object.keys(normalized).length ? normalized : undefined;
    } catch (error) {
      // fallback to plain parsing below
    }
  }

  const entries = trimmed
    .split(/[\n;,]+/)
    .map((part) => part.trim())
    .filter(Boolean);

  const labels: Record<string, string> = {};
  entries.forEach((entry) => {
    const [key, value] = entry.split('=');
    if (key && value) {
      labels[key.trim()] = value.trim();
    }
  });

  return Object.keys(labels).length ? labels : undefined;
};
interface BlackboxFormValues extends BlackboxTargetPayload {

  labelsText?: string;
}

const BlackboxTargets: React.FC = () => {
  const actionRef = useRef<ActionType | null>(null);

  // SISTEMA DINÂMICO: Carregar campos metadata do backend
  const { tableFields } = useTableFields('blackbox');
  // TODO: Implementar formulário dinâmico com formFields
  // const { formFields, loading: formFieldsLoading } = useFormFields('blackbox');
  const { filterFields, loading: filterFieldsLoading } = useFilterFields('blackbox');

  // SISTEMA DE AUTO-CADASTRO: Hooks para retroalimentação de valores
  const { batchEnsure } = useBatchEnsure();
  const { ensureTags } = useServiceTags({ autoLoad: false });

  // SISTEMA DINÂMICO: filters agora é dinâmico (qualquer campo metadata)
  const [filters, setFilters] = useState<Record<string, string | undefined>>({});
  const [metadataOptions, setMetadataOptions] = useState<Record<string, string[]>>({});
  const [selectedNode, setSelectedNode] = useState<string>(ALL_NODES);
  const [formOpen, setFormOpen] = useState(false);
  const [formMode, setFormMode] = useState<'create' | 'edit'>('create');
  const [currentRecord, setCurrentRecord] =
    useState<BlackboxTargetRecord | null>(null);
  const [tableSnapshot, setTableSnapshot] = useState<BlackboxTableItem[]>([]);
  const [summary, setSummary] = useState<BlackboxListResponse['summary'] | null>(null);
  const [selectedRowKeys, setSelectedRowKeys] = useState<React.Key[]>([]);
  const [selectedRows, setSelectedRows] = useState<BlackboxTargetRecord[]>([]);
  const [searchValue, setSearchValue] = useState<string>('');
  const [searchInput, setSearchInput] = useState<string>('');
  const [advancedOpen, setAdvancedOpen] = useState(false);
  const [advancedConditions, setAdvancedConditions] = useState<SearchCondition[]>([]);
  const [advancedOperator, setAdvancedOperator] = useState<'and' | 'or'>('and');
  // SISTEMA DINÂMICO: Combinar colunas fixas + campos metadata dinâmicos
  const defaultColumnConfig = useMemo<ColumnConfig[]>(() => {
    const metadataColumns: ColumnConfig[] = tableFields.map((field) => ({
      key: field.name,
      title: field.display_name,
      visible: field.show_in_table ?? true,
      locked: false,
    }));

    // ORDEM: service → campos metadata → interval, timeout, enabled, tags, actions
    return [
      FIXED_BLACKBOX_COLUMNS[0], // service
      ...metadataColumns,        // campos dinâmicos
      FIXED_BLACKBOX_COLUMNS[1], // node
      FIXED_BLACKBOX_COLUMNS[2], // interval
      FIXED_BLACKBOX_COLUMNS[3], // timeout
      FIXED_BLACKBOX_COLUMNS[4], // enabled
      FIXED_BLACKBOX_COLUMNS[5], // tags
      FIXED_BLACKBOX_COLUMNS[6], // actions
    ];
  }, [tableFields]);

  const [columnConfig, setColumnConfig] = useState<ColumnConfig[]>([]);
  const [columnWidths, setColumnWidths] = useState<Record<string, number>>({});

  // Atualizar columnConfig quando tableFields carregar (evitar loop infinito)
  useEffect(() => {
    if (defaultColumnConfig.length > 0 && defaultColumnConfig.length !== columnConfig.length) {
      setColumnConfig(defaultColumnConfig);
    }
  }, [defaultColumnConfig, columnConfig.length]); // Verificar length previne loop infinito
  const [detailRecord, setDetailRecord] =
    useState<BlackboxTargetRecord | null>(null);
  const [configDrawerOpen, setConfigDrawerOpen] = useState(false);
  const [configLoading, setConfigLoading] = useState(false);
  const [configContent, setConfigContent] = useState({
    rules: '',
    blackbox: '',
    prometheus: '',
  });
  const [searchParams, setSearchParams] = useSearchParams();
  const initialFormValues = useMemo<Partial<BlackboxFormValues>>(() => {
    if (formMode === 'edit' && currentRecord) {
      const target = mapRecordToPayload(currentRecord);
      return {
        ...target,
        labelsText: stringifyLabels(target.labels),
      };
    }
    return {
      interval: '30s',
      timeout: '10s',
      enabled: true,
    };
  }, [formMode, currentRecord]);

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

  const getFieldValue = useCallback((row: BlackboxTableItem, field: string): string => {
    switch (field) {
      case 'service':
        return row.service || '';
      case 'module':
        return row.meta?.module || '';
      case 'company':
        return row.meta?.company || '';
      case 'grupo_monitoramento':
        return row.meta?.grupo_monitoramento || '';
      case 'tipo_monitoramento':
        return row.meta?.tipo_monitoramento || '';
      case 'name':
        return row.meta?.name || '';
      case 'instance':
        return row.meta?.instance || '';
      case 'group':
        return row.meta?.group || '';
      case 'node':
        return (row as any).node || '';
      default:
        return '';
    }
  }, []);

  const applyAdvancedFilters = useCallback(
    (data: BlackboxTableItem[]) => {
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
            case 'contains':
              return source.includes(target);
            case 'starts_with':
              return source.startsWith(target);
            case 'ends_with':
              return source.endsWith(target);
            default:
              return true;
          }
        });

        if (advancedOperator === 'and') {
          return evaluations.every(Boolean);
        }
        return evaluations.some(Boolean);
      });
    },
    [advancedConditions, advancedOperator, getFieldValue],
  );

  // SISTEMA DINÂMICO: buildQueryParams retorna filtros dinâmicos
  const buildQueryParams = useCallback((): Record<string, string | undefined> => {
    const query: Record<string, string | undefined> = { ...filters };
    if (selectedNode !== ALL_NODES) {
      query.node = selectedNode;
    } else {
      delete query.node;
    }
    return query;
  }, [filters, selectedNode]);

  const requestHandler = useCallback(
    async (params: { current?: number; pageSize?: number; keyword?: string }) => {
      try {
        // 🚀 USAR ENDPOINT OTIMIZADO - Cache de 15s, processado no backend
        const response = await consulAPI.getBlackboxTargetsOptimized();
        const { data: backendRows, summary: backendSummary } = response.data;

        // Converter para formato esperado pela tabela
        const services = backendRows.map<BlackboxTableItem>((item) => ({
          service_id: item.id,
          key: item.key,
          service: item.service,
          node: item.node,
          node_addr: item.nodeAddr,
          tags: item.tags || [],
          meta: {
            ...item.meta,
            module: item.module,
            instance: item.instance,
            company: item.company,
            project: item.project,
            env: item.env,
          },
        }));

        // SISTEMA DINÂMICO: Extrair metadataOptions dinamicamente de filterFields
        const optionsSets: Record<string, Set<string>> = {};

        // Inicializar Set para cada filterField
        filterFields.forEach((field) => {
          optionsSets[field.name] = new Set<string>();
        });

        // Extrair valores de todos os registros
        backendRows.forEach((item) => {
          filterFields.forEach((field) => {
            const value = item[field.name as keyof typeof item] || item.meta?.[field.name];
            if (value && typeof value === 'string') {
              optionsSets[field.name].add(value);
            }
          });

          // CAMPO ESPECIAL: node (não é metadata)
          if (item.node) {
            if (!optionsSets['node']) optionsSets['node'] = new Set();
            optionsSets['node'].add(item.node);
          }
        });

        // Converter Sets para Arrays
        const options: Record<string, string[]> = {};
        Object.entries(optionsSets).forEach(([fieldName, valueSet]) => {
          // CASO ESPECIAL: campo 'module' inclui módulos padrão
          if (fieldName === 'module') {
            options[fieldName] = Array.from(new Set([...DEFAULT_BLACKBOX_MODULES, ...valueSet]));
          } else {
            options[fieldName] = Array.from(valueSet);
          }
        });

        setMetadataOptions(options);

        // Usar summary do backend
        if (backendSummary) {
          setSummary({
            total: backendRows.length,
            by_module: backendSummary.by_module || {},
            by_env: backendSummary.by_env || {},
          });
        }

        const advancedRows = applyAdvancedFilters(services);

        const keywordRaw = (params?.keyword ?? searchValue) || '';
        const keyword = keywordRaw.trim().toLowerCase();
        let searchedRows = advancedRows;
        if (keyword) {
          searchedRows = advancedRows.filter((item) => {
            const fields = [
              item.service,
              item.meta?.name,
              item.meta?.instance,
              item.meta?.company,
              item.meta?.project,
              item.meta?.group,
              item.node,
            ];
            return fields.some(
              (field) => field && String(field).toLowerCase().includes(keyword),
            );
          });
        }

        setTableSnapshot(searchedRows);

        const current = params?.current ?? 1;
        const pageSize = params?.pageSize ?? DEFAULT_PAGE_SIZE;
        const start = (current - 1) * pageSize;
        const pageData = searchedRows.slice(start, start + pageSize);

        return {
          data: pageData,
          success: true,
          total: searchedRows.length,
        };
      } catch (error) {
        message.error('Falha ao carregar alvos Blackbox');
        return {
          data: [],
          success: false,
          total: 0,
        };
      }
    },
    [applyAdvancedFilters, searchValue],
  );
  const handleAdvancedSearch = useCallback(
    (conditions: SearchCondition[], operator: string) => {
      setAdvancedConditions(conditions);
      setAdvancedOperator(operator as 'and' | 'or');
      setAdvancedOpen(false);
      actionRef.current?.reload();
    },
    [],
  );

  const handleAdvancedClear = useCallback(() => {
    setAdvancedConditions([]);
    setAdvancedOperator('and');
    actionRef.current?.reload();
  }, []);

  const handleResize = useCallback(
    (columnKey: string) =>
      (_: React.SyntheticEvent, { size }: { size: { width: number } }) => {
        setColumnWidths((prev) => ({ ...prev, [columnKey]: size.width }));
      },
    [],
  );

  const openCreateModal = useCallback(() => {
    setFormMode('create');
    setCurrentRecord(null);
    setFormOpen(true);
  }, []);

  const openEditModal = useCallback((record: BlackboxTargetRecord) => {
    setFormMode('edit');
    setCurrentRecord(record);
    setFormOpen(true);
  }, []);

  const handleSubmit = async (values: BlackboxFormValues) => {
    try {
      // PASSO 1: AUTO-CADASTRO DE VALORES (Retroalimentação)
      // Antes de salvar, garantir que valores novos sejam cadastrados automaticamente

      // 1A) Auto-cadastrar METADATA FIELDS de blackbox targets
      const metadataValues: Array<{ fieldName: string; value: string }> = [];

      // Lista de campos que devem ser auto-cadastrados (se tiverem valor)
      const fieldsToEnsure: Array<keyof BlackboxTargetPayload> = ['module', 'company', 'project', 'env', 'name', 'instance', 'group'];

      fieldsToEnsure.forEach((fieldName) => {
        const fieldValue = values[fieldName];
        if (fieldValue && typeof fieldValue === 'string' && fieldValue.trim()) {
          metadataValues.push({
            fieldName: fieldName as string,
            value: fieldValue.trim()
          });
        }
      });

      // Executar batch ensure se houver valores
      if (metadataValues.length > 0) {
        try {
          await batchEnsure(metadataValues);
        } catch (err) {
          console.warn('Erro ao auto-cadastrar metadata fields:', err);
          // Não bloqueia o fluxo
        }
      }

      // PASSO 2: SALVAR BLACKBOX TARGET (lógica original)
      const payload: BlackboxTargetPayload = {
        module: values.module,
        company: values.company,
        project: values.project,
        env: values.env,
        name: values.name,
        instance: values.instance,
        group: values.group,
        interval: values.interval || '30s',
        timeout: values.timeout || '10s',
        enabled: values.enabled ?? true,
        labels: parseLabelsText(values.labelsText),
        notes: values.notes,
      };

      if (formMode === 'create') {
        await consulAPI.createBlackboxTarget(payload);
        message.success('Alvo blackbox criado com sucesso');
      } else if (currentRecord) {
        const current = mapRecordToPayload(currentRecord);
        await consulAPI.updateBlackboxTarget(current, payload);
        message.success('Alvo blackbox atualizado');
      }

      // Limpar cache após criar/atualizar
      await consulAPI.clearCache('blackbox-targets');

      setFormOpen(false);
      setCurrentRecord(null);
      actionRef.current?.reload();
      return true;
    } catch (error: any) {
      const detail =
        error?.response?.data?.detail ||
        error?.response?.data?.error ||
        error?.message ||
        'Erro desconhecido';
      message.error(`Falha ao salvar alvo: ${detail}`);
      return false;
    }
  };

  const handleDelete = async (record: BlackboxTargetRecord) => {
    try {
      await consulAPI.deleteBlackboxTarget({
        module: record.meta?.module || '',
        company: record.meta?.company || '',
        project: record.meta?.project || '',
        env: record.meta?.env || '',
        name: record.meta?.name || '',
        group: record.meta?.group || undefined,
      });

      // Limpar cache após deletar
      await consulAPI.clearCache('blackbox-targets');

      message.success('Alvo removido com sucesso');
      actionRef.current?.reload();
    } catch (error: any) {
      const detail =
        error?.response?.data?.detail ||
        error?.response?.data?.error ||
        error?.message ||
        'Erro desconhecido';
      message.error(`Falha ao remover alvo: ${detail}`);
    }
  };

  const handleBatchDelete = async () => {
    if (!selectedRows.length) {
      return;
    }
    try {
      await Promise.all(
        selectedRows.map((record) =>
          consulAPI.deleteBlackboxTarget({
            module: record.meta?.module || '',
            company: record.meta?.company || '',
            project: record.meta?.project || '',
            env: record.meta?.env || '',
            name: record.meta?.name || '',
            group: record.meta?.group || undefined,
          }),
        ),
      );
      message.success('Alvos removidos com sucesso');
      setSelectedRowKeys([]);
      setSelectedRows([]);
      actionRef.current?.reload();
    } catch (error) {
      message.error('Falha ao remover um ou mais alvos');
    }
  };

  const handleImport: UploadProps['beforeUpload'] = async (file) => {
    try {
      await consulAPI.importBlackboxTargets(file);
      message.success('Importacao concluida');
      actionRef.current?.reload();
    } catch (error: any) {
      const detail =
        error?.response?.data?.detail ||
        error?.response?.data?.error ||
        error?.message ||
        'Erro desconhecido';
      message.error(`Falha na importacao: ${detail}`);
    }
    return false;
  };

  const handleExport = () => {
    if (!tableSnapshot.length) {
      message.info('Nao ha dados para exportar');
      return;
    }

    const header = [
      'module',
      'company',
      'grupo_monitoramento',
      'tipo_monitoramento',
      'name',
      'instance',
      'group',
      'interval',
      'timeout',
      'enabled',
    ];
    const rows = tableSnapshot.map((record) => {
      const payload = {
        module: record.meta?.module || '',
        company: record.meta?.company || '',
        project: record.meta?.project || '',
        env: record.meta?.env || '',
        name: record.meta?.name || '',
        instance: record.meta?.instance || '',
        group: record.meta?.group || '',
        interval: record.meta?.interval || '30s',
        timeout: record.meta?.timeout || '10s',
        enabled: record.meta?.enabled ?? true,
      };
      return [
        payload.module,
        payload.company,
        payload.project,
        payload.env,
        payload.name,
        payload.instance,
        payload.group,
        payload.interval,
        payload.timeout,
        payload.enabled ? 'true' : 'false',
      ].join(';');
    });

    const csvContent = [header.join(';'), ...rows].join('\n');
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `blackbox-targets-${new Date().toISOString()}.csv`;
    link.click();
    URL.revokeObjectURL(url);
  };

  useEffect(() => {
    if (searchParams.get('create') === 'true') {
      openCreateModal();
      const next = new URLSearchParams(searchParams);
      next.delete('create');
      setSearchParams(next, { replace: true });
    }
  }, [searchParams, setSearchParams, openCreateModal]);

  const openConfigDrawer = async () => {
    try {
      setConfigLoading(true);
      const [rulesRes, blackboxRes, promRes] = await Promise.all([
        consulAPI.getBlackboxRules(),
        consulAPI.getBlackboxConfig(),
        consulAPI.getBlackboxPrometheusConfig(),
      ]);
      setConfigContent({
        rules: rulesRes.data,
        blackbox: blackboxRes.data,
        prometheus: promRes.data,
      });
      setConfigDrawerOpen(true);
    } catch (error) {
      message.error('Falha ao carregar configuracoes');
    } finally {
      setConfigLoading(false);
    }
  };

  useEffect(() => {
    actionRef.current?.reload();
  }, [filters, selectedNode]);

  const advancedFieldOptions = useMemo(
    () => [
      { label: 'Nome', value: 'name', type: 'text' },
      { label: 'Modulo', value: 'module', type: 'text' },
      { label: 'Empresa', value: 'company', type: 'text' },
      { label: 'Grupo Monitoramento', value: 'grupo_monitoramento', type: 'text' },
      { label: 'Tipo Monitoramento', value: 'tipo_monitoramento', type: 'text' },
      { label: 'Instancia', value: 'instance', type: 'text' },
      { label: 'Grupo', value: 'group', type: 'text' },
      { label: 'No', value: 'node', type: 'text' },
    ],
    [],
  );

  // SISTEMA DINÂMICO: Gerar columnMap combinando fixas + metadata
  const columnMap = useMemo<Record<string, TableColumn<BlackboxTableItem>>>(() => {
    // COLUNAS FIXAS com lógica específica
    const fixedColumns: Record<string, TableColumn<BlackboxTableItem>> = {
      service: {
        title: 'Serviço',
        dataIndex: 'service',
        width: 220,
        ellipsis: true,
        render: (_, record) => (
          <Space size={4}>
            <InfoCircleOutlined style={{ color: '#1677ff' }} />
            <span>{record.service}</span>
          </Space>
        ),
      },
      node: {
        title: 'Nó',
        dataIndex: 'node',
        width: 180,
        ellipsis: true,
        render: (_, record) => (record as any).node || '-',
      },
      interval: {
        title: 'Intervalo',
        dataIndex: ['meta', 'interval'],
        width: 120,
      },
      timeout: {
        title: 'Timeout',
        dataIndex: ['meta', 'timeout'],
        width: 120,
      },
      enabled: {
        title: 'Ativo',
        dataIndex: ['meta', 'enabled'],
        width: 100,
        render: (_, record) =>
          record.meta?.enabled ? (
            <Tag color="green">Ativo</Tag>
          ) : (
            <Tag color="red">Inativo</Tag>
          ),
      },
      tags: {
        title: 'Tags',
        dataIndex: 'tags',
        width: 220,
        render: (_, record) => (
          <Space size={[4, 4]} wrap>
            {(record.tags || []).map((tag) => (
              <Tag key={`${record.service_id}-${tag}`}>{tag}</Tag>
            ))}
          </Space>
        ),
      },
      actions: {
        title: 'Ações',
        valueType: 'option',
        width: 140,
        render: (_, record) => [
          <Tooltip title="Ver detalhes" key={`${record.service_id}-detail`}>
            <Button
              type="link"
              icon={<InfoCircleOutlined />}
              aria-label="Ver detalhes"
              onClick={() => setDetailRecord(record)}
            />
          </Tooltip>,
          <Tooltip title="Editar alvo" key={`${record.service_id}-edit`}>
            <Button
              type="link"
              icon={<EditOutlined />}
              aria-label="Editar alvo"
              onClick={() => openEditModal(record)}
            />
          </Tooltip>,
          <Popconfirm
            key={`${record.service_id}-delete`}
            title="Remover este alvo?"
            onConfirm={() => handleDelete(record)}
            okText="Remover"
            cancelText="Cancelar"
          >
            <Tooltip title="Remover alvo">
              <Button
                type="link"
                danger
                icon={<DeleteOutlined />}
                aria-label="Remover alvo"
              />
            </Tooltip>
          </Popconfirm>,
        ],
      },
    };

    // COLUNAS METADATA DINÂMICAS
    const metadataColumns: Record<string, TableColumn<BlackboxTableItem>> = {};
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

  const visibleColumns = useMemo(
    () =>
      columnConfig
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
        .filter(Boolean) as TableColumn<BlackboxTableItem>[],
    [columnConfig, columnMap, columnWidths, handleResize],
  );

  const nodeSelector = useMemo(
    () => (
      <Select
        value={selectedNode}
        style={{ minWidth: 200 }}
        onChange={(value) => setSelectedNode(value)}
      >
        <Select.Option value={ALL_NODES}>Todos os nos</Select.Option>
        {(metadataOptions['node'] || []).map((node) => (
          <Select.Option key={node} value={node}>
            {node}
          </Select.Option>
        ))}
      </Select>
    ),
    [metadataOptions, selectedNode],
  );

  const renderExpandedRow = useCallback(
    (record: BlackboxTableItem) => (
      <Descriptions size="small" column={2} bordered style={{ margin: 0 }}>
        {Object.entries(record.meta || {}).map(([key, value]) => (
          <Descriptions.Item label={key} key={`${record.service_id}-${key}`}>
            {String(value ?? '')}
          </Descriptions.Item>
        ))}
        {record.tags?.length ? (
          <Descriptions.Item label="Tags">
            <Space size={[4, 4]} wrap>
              {record.tags.map((tag) => (
                <Tag key={`${record.service_id}-expanded-${tag}`}>{tag}</Tag>
              ))}
            </Space>
          </Descriptions.Item>
        ) : null}
      </Descriptions>
    ),
    [],
  );

  const advancedSearchFields = useMemo(
    () => [
      { label: 'Target', value: 'target', type: 'text' },
      { label: 'No', value: 'node', type: 'text' },
      { label: 'Modulo', value: 'module', type: 'text' },
      { label: 'Empresa', value: 'company', type: 'text' },
      { label: 'Grupo Monitoramento', value: 'grupo_monitoramento', type: 'text' },
      { label: 'Tipo Monitoramento', value: 'tipo_monitoramento', type: 'text' },
      { label: 'Grupo', value: 'group', type: 'text' },
    ],
    [],
  );

  return (
    <PageContainer
      header={{
        title: 'Alvos Blackbox',
        subTitle:
          'Gerencie os alvos monitorados pelo Blackbox Exporter com sincronizacao via Consul',
      }}
    >
      <Space direction="vertical" size="middle" style={{ width: '100%' }}>
        {/* Summary Cards */}
        <Card>
          <Space size="large" wrap>
            <Statistic
              title="Alvos monitorados"
              value={summary?.total || 0}
              prefix={<CloudOutlined />}
              valueStyle={{ color: '#3f8600' }}
            />
            <Statistic title="Ativos" value={summary?.enabled || 0} />
            <Statistic
              title="Desativados"
              value={summary?.disabled || 0}
              valueStyle={{ color: '#cf1322' }}
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
                loading={filterFieldsLoading}
                onChange={setFilters}
                onReset={() => {
                  setFilters({});
                  setSelectedNode(ALL_NODES);
                }}
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
                type={advancedConditions.length ? 'primary' : 'default'}
                onClick={() => setAdvancedOpen(true)}
              >
                Busca Avancada
                {advancedConditions.length > 0 && ` (${advancedConditions.length})`}
              </Button>

              {advancedConditions.length > 0 && (
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
                storageKey="blackbox-columns"
              />

              <Button
                icon={<DownloadOutlined />}
                onClick={handleExport}
                disabled={!tableSnapshot.length}
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
                title="Remover alvos selecionados?"
                description="Esta acao removera os alvos selecionados do Consul. Tem certeza?"
                onConfirm={handleBatchDelete}
                disabled={!selectedRows.length}
                okText="Sim"
                cancelText="Nao"
              >
                <Tooltip title="Remover alvos selecionados">
                  <Button
                    danger
                    icon={<DeleteOutlined />}
                    disabled={!selectedRows.length}
                  >
                    Remover selecionados ({selectedRows.length})
                  </Button>
                </Tooltip>
              </Popconfirm>

              <Upload
                accept=".csv,.xlsx"
                showUploadList={false}
                beforeUpload={handleImport}
              >
                <Button icon={<ImportOutlined />}>Importar</Button>
              </Upload>

              <Button
                icon={<CloudOutlined />}
                onClick={openConfigDrawer}
              >
                Configuracoes
              </Button>

              <Button
                type="primary"
                icon={<PlusOutlined />}
                onClick={openCreateModal}
              >
                Novo alvo
              </Button>
            </Space>

          </Space>
        </Card>

        {/* Table */}
        <ProTable<BlackboxTableItem>
          rowKey="key"
          columns={visibleColumns}
          search={false}
          actionRef={actionRef}
          request={requestHandler}
          params={{ keyword: searchValue }}
          pagination={{
            defaultPageSize: DEFAULT_PAGE_SIZE,
            showSizeChanger: true,
            pageSizeOptions: ['10', '20', '30', '50', '100'],
          }}
          locale={{ emptyText: 'Nenhum dado disponivel' }}
          components={{
            header: {
              cell: ResizableTitle,
            },
          }}
          rowSelection={{
            selectedRowKeys,
            onChange: (keys, rows) => {
              setSelectedRowKeys(keys);
              setSelectedRows(rows as BlackboxTargetRecord[]);
            },
          }}
          options={{ density: true, fullScreen: true, reload: false, setting: false }}
          scroll={{ x: 1400 }}
          expandable={{
            expandedRowRender: renderExpandedRow,
            rowExpandable: (record) =>
              Boolean(record.meta && Object.keys(record.meta || {}).length > 0),
          }}
        />
      </Space>

      <Drawer
        width={520}
        open={!!detailRecord}
        destroyOnHidden
        title="Detalhes do alvo"
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
            <ProDescriptions.Item label="Servico ID">
              {detailRecord.service_id}
            </ProDescriptions.Item>
            <ProDescriptions.Item label="Servico Consul">
              {detailRecord.service}
            </ProDescriptions.Item>
            <ProDescriptions.Item label="Modulo">
              {detailRecord.meta?.module}
            </ProDescriptions.Item>
            <ProDescriptions.Item label="Empresa">
              {detailRecord.meta?.company}
            </ProDescriptions.Item>
            <ProDescriptions.Item label="Projeto">
              {detailRecord.meta?.project}
            </ProDescriptions.Item>
            <ProDescriptions.Item label="Ambiente">
              {detailRecord.meta?.env}
            </ProDescriptions.Item>
            <ProDescriptions.Item label="Nome">
              {detailRecord.meta?.name}
            </ProDescriptions.Item>
            <ProDescriptions.Item label="Instancia">
              {detailRecord.meta?.instance}
            </ProDescriptions.Item>
            <ProDescriptions.Item label="Grupo">
              {detailRecord.meta?.group || '-'}
            </ProDescriptions.Item>
            <ProDescriptions.Item label="Intervalo">
              {detailRecord.meta?.interval}
            </ProDescriptions.Item>
            <ProDescriptions.Item label="Timeout">
              {detailRecord.meta?.timeout}
            </ProDescriptions.Item>
            <ProDescriptions.Item label="Ativo">
              {detailRecord.meta?.enabled ? 'Sim' : 'Nao'}
            </ProDescriptions.Item>
            <ProDescriptions.Item label="Tags">
              <Space size={[4, 4]} wrap>
                {(detailRecord.tags || []).map((tag) => (
                  <Tag key={`${detailRecord.service_id}-drawer-${tag}`}>{tag}</Tag>
                ))}
              </Space>
            </ProDescriptions.Item>
          </ProDescriptions>
        )}
      </Drawer>

      <Drawer
        width={720}
        title="Configuracoes auxiliares"
        open={configDrawerOpen}
        destroyOnHidden
        onClose={() => setConfigDrawerOpen(false)}
      >
        <Spin spinning={configLoading}>
          <Tabs
            defaultActiveKey="rules"
            items={[
              {
                key: 'rules',
                label: 'Regras de alerta',
                children: (
                  <Paragraph style={{ whiteSpace: 'pre-wrap' }}>
                    {configContent.rules || 'Nenhum conteudo disponivel'}
                  </Paragraph>
                ),
              },
              {
                key: 'blackbox',
                label: 'blackbox.yml',
                children: (
                  <Paragraph style={{ whiteSpace: 'pre-wrap' }}>
                    {configContent.blackbox || 'Nenhum conteudo disponivel'}
                  </Paragraph>
                ),
              },
              {
                key: 'prometheus',
                label: 'prometheus.yml',
                children: (
                  <Paragraph style={{ whiteSpace: 'pre-wrap' }}>
                    {configContent.prometheus || 'Nenhum conteudo disponivel'}
                  </Paragraph>
                ),
              },
            ]}
          />
        </Spin>
      </Drawer>

      <ModalForm<BlackboxFormValues>
        title={formMode === 'create' ? 'Novo alvo' : 'Editar alvo'}
        width={760}
        open={formOpen}
        initialValues={initialFormValues}
        modalProps={{
          destroyOnHidden: true,
          onCancel: () => {
            setFormOpen(false);
            setCurrentRecord(null);
          },
        }}
        submitter={{
          searchConfig: {
            submitText: formMode === 'create' ? 'Criar alvo' : 'Salvar alteracoes',
          },
        }}
        onFinish={handleSubmit}
      >
        <div style={FORM_ROW_STYLE}>
          <ProFormText
            name="module"
            label="Modulo"
            placeholder="Selecione o modulo"
            rules={[{ required: true, message: 'Informe o modulo' }]}
          />
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
        </div>

        <div style={FORM_ROW_STYLE}>
          <ProFormText
            name="tipo_monitoramento"
            label="Tipo Monitoramento"
            placeholder="Ex: prod, dev, homolog"
            rules={[{ required: true, message: 'Informe o tipo de monitoramento' }]}
          />
          <ProFormText
            name="name"
            label="Nome"
            placeholder="Nome amigavel do alvo"
            rules={[{ required: true, message: 'Informe o nome' }]}
          />
          <ProFormText
            name="instance"
            label="Instancia (URL/IP)"
            placeholder="Ex: https://www.example.com"
            rules={[{ required: true, message: 'Informe a instancia' }]}
          />
        </div>

        <div style={FORM_ROW_STYLE}>
          <ProFormText
            name="group"
            label="Grupo"
            placeholder="Grupo opcional"
          />
          <ProFormText
            name="interval"
            label="Intervalo"
            placeholder="Ex: 30s"
          />
          <ProFormText
            name="timeout"
            label="Timeout"
            placeholder="Ex: 10s"
          />
        </div>

        <ProFormSwitch
          name="enabled"
          label="Alvo ativo"
          fieldProps={{ defaultChecked: true }}
        />

        <ProFormTextArea
          name="labelsText"
          label="Labels (JSON ou chave=valor)"
          placeholder='Ex: { "empresa": "Skills" } ou chave=valor'
          fieldProps={{ rows: 4 }}
        />

        <ProFormTextArea
          name="notes"
          label="Notas"
          placeholder="Informacoes adicionais"
          fieldProps={{ rows: 3 }}
        />
      </ModalForm>

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
    </PageContainer>
  );
};

export default BlackboxTargets;




