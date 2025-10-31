import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
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
  DeleteOutlined,
  DownloadOutlined,
  EditOutlined,
  FilterOutlined,
  InfoCircleOutlined,
  PlusOutlined,
  ReloadOutlined,
  CloudServerOutlined,
} from '@ant-design/icons';
import type { ActionType } from '@ant-design/pro-components';
import {
  ModalForm,
  PageContainer,
  ProFormDigit,
  ProFormSelect,
  ProFormText,
  ProTable,
} from '@ant-design/pro-components';
import ColumnSelector, { type ColumnConfig } from '../components/ColumnSelector';
import MetadataFilterBar from '../components/MetadataFilterBar';
import AdvancedSearchPanel, { type SearchCondition } from '../components/AdvancedSearchPanel';
import ResizableTitle from '../components/ResizableTitle';
import { consulAPI, metadataFieldsAPI } from '../services/api';
import type {
  MetadataField,
  MetadataFilters,
  ServiceUpdatePayload,
  ServiceCreatePayload,
  ServiceMeta,
} from '../services/api';

const { Option } = Select;
const { Search } = Input;
const { Text } = Typography;

const ALL_NODES = 'ALL';

interface ExporterTableItem {
  key: string;
  id: string;
  node: string;
  nodeAddr?: string;
  service: string;
  tags: string[];
  address?: string;
  port?: number;
  meta: ServiceMeta;
  exporterType?: string; // node, windows, mysql, redis, etc.
}

interface EditFormValues {
  // Nó do Consul (se alterado, requer deregister do nó antigo + register no nó novo)
  node_addr?: string;

  // Campos do ID (se alterados, requer deregister + register)
  vendor?: string;
  account?: string;
  region?: string;
  group?: string;
  name?: string;

  // Outros campos Meta
  instance?: string;
  os?: 'linux' | 'windows';

  // Campos adicionais do Meta (dinâmicos)
  company?: string;
  project?: string;
  env?: string;

  // Campos do serviço
  address?: string;
  port?: number;
  tags?: string[];
}

interface CreateFormValues {
  // Nó do Consul onde o serviço será registrado
  node_addr: string;

  service: string;
  vendor: string;
  account: string;
  region: string;
  group: string;
  name: string;
  instance: string;
  os: 'linux' | 'windows';
  address: string;
  port: number;
  tags?: string[];
}

type ExporterColumn<T> = import('@ant-design/pro-components').ProColumns<T>;

const BASE_COLUMN_PRESETS: ColumnConfig[] = [
  { key: 'service', title: 'Servico', visible: true },
  { key: 'id', title: 'ID Consul', visible: true }, // Coluna estática para mostrar ID do Consul
  { key: 'exporterType', title: 'Tipo', visible: true },
  { key: 'node', title: 'No', visible: true },
  { key: 'address', title: 'Endereco', visible: true },
  { key: 'port', title: 'Porta', visible: true },
  { key: 'tags', title: 'Tags', visible: false },
  { key: 'actions', title: 'Acoes', visible: true, locked: true },
];

const Exporters: React.FC = () => {
  const actionRef = useRef<ActionType>(null);
  const [nodes, setNodes] = useState<any[]>([]);
  const [selectedNode, setSelectedNode] = useState<string>(ALL_NODES);
  const [searchValue, setSearchValue] = useState('');
  const [filters, setFilters] = useState<MetadataFilters>({});
  const [metadataOptions, setMetadataOptions] = useState<any>({});
  const [summary, setSummary] = useState<any>({ total: 0, byEnv: {}, byType: {} });
  const [metadataFields, setMetadataFields] = useState<MetadataField[]>([]);
  const [metadataLoading, setMetadataLoading] = useState(false);
  const [columnConfig, setColumnConfig] = useState<ColumnConfig[]>(BASE_COLUMN_PRESETS);
  const [columnWidths, setColumnWidths] = useState<Record<string, number>>({});
  const [detailsDrawerVisible, setDetailsDrawerVisible] = useState(false);
  const [selectedExporter, setSelectedExporter] = useState<ExporterTableItem | null>(null);
  const [advancedOpen, setAdvancedOpen] = useState(false);
  const [advancedConditions, setAdvancedConditions] = useState<SearchCondition[]>([]);
  const [advancedOperator, setAdvancedOperator] = useState<'and' | 'or'>('and');
  const [tableSnapshot, setTableSnapshot] = useState<ExporterTableItem[]>([]);
  const [selectedRows, setSelectedRows] = useState<ExporterTableItem[]>([]);
  const [editModalOpen, setEditModalOpen] = useState(false);
  const [editingExporter, setEditingExporter] = useState<ExporterTableItem | null>(null);
  const [createModalOpen, setCreateModalOpen] = useState(false);
  const [generatedId, setGeneratedId] = useState<string>('');
  const [serviceNames, setServiceNames] = useState<string[]>([]);
  const [serviceNamesLoading, setServiceNamesLoading] = useState(false);
  const [selectedNodeForModal, setSelectedNodeForModal] = useState<string>('');

  useEffect(() => {
    fetchNodes();
  }, []);

  // Buscar serviços do nó selecionado quando mudar
  useEffect(() => {
    if (selectedNodeForModal) {
      fetchServiceNamesForNode(selectedNodeForModal);
    }
  }, [selectedNodeForModal]);

  useEffect(() => {
    const fetchMetadata = async () => {
      try {
        setMetadataLoading(true);
        const response = await metadataFieldsAPI.listFields({ show_in_table_only: true });
        const fields = response?.data?.fields || [];
        const visibleFields = fields
          .filter((field) => field.show_in_table)
          .sort((a, b) => (a.order ?? 0) - (b.order ?? 0));

        setMetadataFields(visibleFields);

        setColumnConfig((prev) => {
          const visibilityMap = prev.reduce<Record<string, boolean>>((acc, col) => {
            acc[col.key] = col.visible;
            return acc;
          }, {});

          const baseColumns = BASE_COLUMN_PRESETS.map((col) => ({
            ...col,
            visible: visibilityMap[col.key] ?? col.visible,
          }));

          const dynamicColumns = visibleFields.map<ColumnConfig>((field) => ({
            key: field.name,
            title: field.display_name || field.name,
            visible: visibilityMap[field.name] ?? true,
          }));

          if (!dynamicColumns.length) {
            return baseColumns;
          }

          const nextConfig: ColumnConfig[] = [];
          let metadataInserted = false;

          baseColumns.forEach((col) => {
            if (!metadataInserted && col.key === 'tags') {
              nextConfig.push(...dynamicColumns);
              metadataInserted = true;
            }
            nextConfig.push(col);
          });

          if (!metadataInserted) {
            nextConfig.push(...dynamicColumns);
          }

          return nextConfig;
        });
      } catch (error) {
        console.error('Erro ao carregar campos metadata:', error);
      } finally {
        setMetadataLoading(false);
      }
    };

    fetchMetadata();
  }, []);

  const fetchNodes = async () => {
    try {
      const response = await consulAPI.getNodes();
      const payload = response.data;
      const nodeList = Array.isArray(payload.data) ? payload.data : [];
      setNodes(nodeList);
    } catch (error) {
      console.error('Error fetching nodes:', error);
    }
  };

  const fetchServiceNamesForNode = async (nodeAddr: string) => {
    try {
      setServiceNamesLoading(true);
      const response = await consulAPI.getNodeServiceNames(nodeAddr);
      const names = response.data?.data || [];
      setServiceNames(names);
    } catch (error) {
      console.error('Error fetching service names for node:', error);
      message.error('Erro ao carregar tipos de serviços do nó selecionado');
    } finally {
      setServiceNamesLoading(false);
    }
  };

  const applyAdvancedFilters = useCallback(
    (data: ExporterTableItem[]) => {
      if (!advancedConditions.length) return data;

      return data.filter((item) => {
        const results = advancedConditions.map((condition) => {
          let fieldValue: any;

          switch (condition.field) {
            case 'service':
              fieldValue = item.service;
              break;
            case 'node':
              fieldValue = item.node;
              break;
            case 'exporterType':
              fieldValue = item.exporterType;
              break;
            default:
              fieldValue = item.meta?.[condition.field];
          }

          const valueStr = String(fieldValue || '').toLowerCase();
          const condValueStr = String(condition.value || '').toLowerCase();

          switch (condition.operator) {
            case 'eq':
              return valueStr === condValueStr;
            case 'ne':
              return valueStr !== condValueStr;
            case 'contains':
              return valueStr.includes(condValueStr);
            case 'starts_with':
              return valueStr.startsWith(condValueStr);
            case 'ends_with':
              return valueStr.endsWith(condValueStr);
            case 'in':
              return Array.isArray(condition.value)
                ? condition.value.some((v) => String(v).toLowerCase() === valueStr)
                : false;
            case 'not_in':
              return Array.isArray(condition.value)
                ? !condition.value.some((v) => String(v).toLowerCase() === valueStr)
                : true;
            default:
              return false;
          }
        });

        return advancedOperator === 'and'
          ? results.every((r) => r)
          : results.some((r) => r);
      });
    },
    [advancedConditions, advancedOperator],
  );

  const requestHandler = useCallback(
    async (params: { current?: number; pageSize?: number; keyword?: string }) => {
      try {
        // 🚀 USAR ENDPOINT OTIMIZADO - Cache de 20s, processado no backend
        const response = await consulAPI.getExportersOptimized();
        const { data: backendRows, summary: backendSummary } = response.data;

        // Converter para formato esperado pela tabela
        const rows: ExporterTableItem[] = backendRows.map((item) => ({
          key: item.key,
          id: item.id,
          node: item.node,
          nodeAddr: item.nodeAddr,
          service: item.service,
          tags: item.tags || [],
          address: item.address,
          port: item.port,
          meta: item.meta || {},
          exporterType: item.exporterType || 'unknown',
        }));

        // Aplicar filtros avançados (se houver)
        const advancedRows = applyAdvancedFilters(rows);

        // Usar summary do backend ou recalcular se houve filtros
        if (advancedRows.length === rows.length && backendSummary) {
          setSummary({
            total: backendRows.length,
            byEnv: backendSummary.by_env || {},
            byType: backendSummary.by_type || {},
          });
        } else {
          const nextSummary = advancedRows.reduce(
            (acc, item) => {
              acc.total += 1;
              const envKey = item.meta?.env || 'desconhecido';
              acc.byEnv[envKey] = (acc.byEnv[envKey] || 0) + 1;
              const typeKey = item.exporterType || 'desconhecido';
              acc.byType[typeKey] = (acc.byType[typeKey] || 0) + 1;
              return acc;
            },
            { total: 0, byEnv: {} as Record<string, number>, byType: {} as Record<string, number> },
          );
          setSummary(nextSummary);
        }

        // Extrair metadataOptions
        const companies = new Set<string>();
        const projects = new Set<string>();
        const envs = new Set<string>();
        const types = new Set<string>();

        advancedRows.forEach((item) => {
          if (item.meta?.company) companies.add(item.meta.company);
          if (item.meta?.project) projects.add(item.meta.project);
          if (item.meta?.env) envs.add(item.meta.env);
          if (item.exporterType) types.add(item.exporterType);
        });

        setMetadataOptions({
          companies: Array.from(companies),
          projects: Array.from(projects),
          envs: Array.from(envs),
          types: Array.from(types),
        });

        // Aplicar busca por keyword
        const keywordRaw = (params?.keyword ?? searchValue) || '';
        const keyword = keywordRaw.trim().toLowerCase();
        let searchedRows = advancedRows;
        if (keyword) {
          searchedRows = advancedRows.filter((item) => {
            const metadataValues = metadataFields.map((field) => item.meta?.[field.name]);
            const fields = [
              item.service,
              item.id,
              item.node,
              item.exporterType,
              ...metadataValues,
            ];
            return fields.some(
              (field) =>
                field && String(field).toLowerCase().includes(keyword),
            );
          });
        }

        setTableSnapshot(searchedRows);

        // Paginação
        const current = params?.current ?? 1;
        const pageSize = params?.pageSize ?? 20;
        const start = (current - 1) * pageSize;
        const paginatedRows = searchedRows.slice(start, start + pageSize);

        return {
          data: paginatedRows,
          success: true,
          total: searchedRows.length,
        };
      } catch (error) {
        console.error('Falha ao carregar exporters:', error);
        message.error('Falha ao carregar exporters');
        return {
          data: [],
          success: false,
          total: 0,
        };
      }
    },
    [applyAdvancedFilters, metadataFields, searchValue],
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

  const handleClearAdvancedSearch = useCallback(() => {
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

  const handleShowDetails = useCallback((record: ExporterTableItem) => {
    setSelectedExporter(record);
    setDetailsDrawerVisible(true);
  }, []);

  const handleExportData = () => {
    const dataStr = JSON.stringify(tableSnapshot, null, 2);
    const blob = new Blob([dataStr], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `exporters-${new Date().toISOString().slice(0, 10)}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    message.success('Dados exportados com sucesso');
  };

  const handleBatchDelete = async () => {
    try {
      const deleteTasks = selectedRows.map((row) =>
        consulAPI.deregisterService({
          node_addr: row.nodeAddr || row.node,
          service_id: row.id,
        })
      );

      await Promise.all(deleteTasks);
      message.success(`${selectedRows.length} exporter(s) removido(s) com sucesso`);
      setSelectedRows([]);
      actionRef.current?.reload();
    } catch (error) {
      console.error('Erro ao remover exporters:', error);
      message.error('Falha ao remover alguns exporters');
    }
  };

  const handleDeleteExporter = useCallback(async (record: ExporterTableItem) => {
    try {
      await consulAPI.deregisterService({
        node_addr: record.nodeAddr || record.node,
        service_id: record.id,
      });

      // Limpar cache após deletar
      await consulAPI.clearCache('exporters');

      message.success('Exporter removido com sucesso');
      actionRef.current?.reload();
    } catch (error) {
      console.error('Erro ao remover exporter:', error);
      message.error('Falha ao remover exporter');
    }
  }, []);

  const handleEditExporter = useCallback((record: ExporterTableItem) => {
    setEditingExporter(record);
    setEditModalOpen(true);
  }, []);

  const handleEditSubmit = async (values: EditFormValues) => {
    if (!editingExporter) return false;

    try {
      // Verificar se o nó mudou
      const oldNodeAddr = editingExporter.nodeAddr || editingExporter.node;
      const newNodeAddr = values.node_addr ?? oldNodeAddr;
      const nodeChanged = newNodeAddr !== oldNodeAddr;

      // Verificar se campos do ID mudaram
      const newVendor = values.vendor ?? editingExporter.meta?.vendor;
      const newAccount = values.account ?? editingExporter.meta?.account;
      const newRegion = values.region ?? editingExporter.meta?.region;
      const newGroup = values.group ?? editingExporter.meta?.group;
      const newName = values.name ?? editingExporter.meta?.name;

      const oldVendor = editingExporter.meta?.vendor;
      const oldAccount = editingExporter.meta?.account;
      const oldRegion = editingExporter.meta?.region;
      const oldGroup = editingExporter.meta?.group;
      const oldName = editingExporter.meta?.name;

      const idChanged =
        newVendor !== oldVendor ||
        newAccount !== oldAccount ||
        newRegion !== oldRegion ||
        newGroup !== oldGroup ||
        newName !== oldName;

      // Construir novo Meta com todos os campos
      const metaPayload = {
        ...editingExporter.meta,
        vendor: newVendor,
        account: newAccount,
        region: newRegion,
        group: newGroup,
        name: newName,
        instance: values.instance ?? editingExporter.meta?.instance,
        os: values.os ?? editingExporter.meta?.os,
        company: values.company ?? editingExporter.meta?.company,
        project: values.project ?? editingExporter.meta?.project,
        env: values.env ?? editingExporter.meta?.env,
      };

      if (nodeChanged || idChanged) {
        // CASO 1: Nó mudou OU ID mudou - usar padrão deregister + register
        const newId = `${newVendor}/${newAccount}/${newRegion}/${newGroup}@${newName}`;

        // Validar novo ID
        if (newId.includes('//') || newId.startsWith('/') || newId.endsWith('/')) {
          message.error('ID inválido: não pode conter "//" ou começar/terminar com "/"');
          return false;
        }

        // 1. Deregister serviço do nó antigo
        await consulAPI.deregisterService({
          service_id: editingExporter.id,
          node_addr: oldNodeAddr,
        });

        // 2. Register serviço no nó novo (ou mesmo nó com ID novo)
        const createPayload: ServiceCreatePayload = {
          id: newId,
          name: editingExporter.service,
          address: values.address ?? editingExporter.address,
          port: values.port ?? editingExporter.port,
          tags: values.tags ?? editingExporter.tags ?? [],
          Meta: metaPayload as unknown as Record<string, string>,
          node_addr: newNodeAddr, // Registrar no nó novo
        };

        await consulAPI.createService(createPayload);

        if (nodeChanged && idChanged) {
          message.success(`Exporter movido para nó ${newNodeAddr} com novo ID: ${newId}`);
        } else if (nodeChanged) {
          message.success(`Exporter movido para nó ${newNodeAddr}`);
        } else {
          message.success(`Exporter atualizado com novo ID: ${newId}`);
        }
      } else {
        // CASO 2: Nó e ID não mudaram - usar update simples
        const updatePayload: ServiceUpdatePayload = {
          address: values.address ?? editingExporter.address,
          port: values.port ?? editingExporter.port,
          tags: values.tags ?? editingExporter.tags ?? [],
          Meta: metaPayload as unknown as Record<string, string>,
          node_addr: newNodeAddr,
        };

        await consulAPI.updateService(editingExporter.id, updatePayload);

        message.success('Exporter atualizado com sucesso');
      }

      // Limpar cache após atualizar
      await consulAPI.clearCache('exporters');

      setEditModalOpen(false);
      setEditingExporter(null);
      actionRef.current?.reload();
      return true;
    } catch (error: unknown) {
      let errorMsg = 'Erro ao atualizar exporter';
      if (typeof error === 'object' && error !== null) {
        const maybeResponse = error as { response?: { data?: { detail?: string } } };
        errorMsg = maybeResponse.response?.data?.detail
          || (error as { message?: string }).message
          || errorMsg;
      }
      message.error(errorMsg);
      return false;
    }
  };

  const handleCreateSubmit = async (values: CreateFormValues) => {
    try {
      // Gerar ID no formato: {vendor}/{account}/{region}/{group}@{name}
      const serviceId = `${values.vendor}/${values.account}/${values.region}/${values.group}@${values.name}`;

      // Validar formato do ID (sem // e sem / no início/fim)
      if (serviceId.includes('//') || serviceId.startsWith('/') || serviceId.endsWith('/')) {
        message.error('ID inválido: não pode conter "//" ou começar/terminar com "/"');
        return false;
      }

      // Validar formato instance (IP:PORT)
      const instanceRegex = /^[\w.-]+:\d+$/;
      if (!instanceRegex.test(values.instance)) {
        message.error('Formato de instance inválido. Use: IP:PORTA (ex: 192.168.1.10:9100)');
        return false;
      }

      // Construir payload de registro - usar ServiceCreatePayload
      const createPayload: ServiceCreatePayload = {
        id: serviceId,
        name: values.service,
        address: values.address,
        port: values.port,
        tags: values.tags || [],
        Meta: {
          vendor: values.vendor,
          account: values.account,
          region: values.region,
          group: values.group,
          name: values.name,
          instance: values.instance,
          os: values.os,
        },
        node_addr: values.node_addr, // Nó onde o serviço será registrado
      };

      // Registrar serviço via API no nó especificado
      await consulAPI.createService(createPayload);

      // Limpar cache após criar
      await consulAPI.clearCache('exporters');

      message.success('Exporter criado com sucesso');
      setCreateModalOpen(false);
      setGeneratedId('');
      actionRef.current?.reload();
      return true;
    } catch (error: unknown) {
      let errorMsg = 'Erro ao criar exporter';
      if (typeof error === 'object' && error !== null) {
        const maybeResponse = error as { response?: { data?: { detail?: string } } };
        errorMsg = maybeResponse.response?.data?.detail
          || (error as { message?: string }).message
          || errorMsg;
      }
      message.error(errorMsg);
      return false;
    }
  };

  const renderMetadataCell = useCallback(
    (field: MetadataField, record: ExporterTableItem) => {
      const value = record.meta?.[field.name];

      if (value === undefined || value === null || value === '') {
        return '-';
      }

      if (field.name === 'env' && typeof value === 'string') {
        const colorMap: Record<string, string> = {
          prd: 'red',
          prod: 'red',
          hml: 'orange',
          homolog: 'orange',
          dev: 'blue',
          lab: 'green',
        };
        return <Tag color={colorMap[value.toLowerCase()] || 'default'}>{value}</Tag>;
      }

      if (Array.isArray(value)) {
        if (!value.length) {
          return '-';
        }
        return value.join(', ');
      }

      if (typeof value === 'boolean') {
        return value ? 'Sim' : 'Nao';
      }

      return String(value);
    },
    [],
  );

  const metadataColumns = useMemo<ExporterColumn<ExporterTableItem>[]>(
    () =>
      metadataFields.map((field) => ({
        title: field.display_name || field.name,
        dataIndex: ['meta', field.name],
        key: field.name,
        width: 150,
        ellipsis: true,
        render: (_, record) => renderMetadataCell(field, record),
        sorter: (a, b) => {
          const valueA = a.meta?.[field.name];
          const valueB = b.meta?.[field.name];
          return String(valueA ?? '').localeCompare(String(valueB ?? ''));
        },
      })),
    [metadataFields, renderMetadataCell],
  );

  const allColumns: ExporterColumn<ExporterTableItem>[] = useMemo(() => {
    const baseColumns: ExporterColumn<ExporterTableItem>[] = [
      {
        title: 'Servico',
        dataIndex: 'service',
        key: 'service',
        width: 200,
        render: (_, record) => <Text strong>{record.service}</Text>,
        sorter: (a, b) => a.service.localeCompare(b.service),
      },
      {
        title: 'ID Consul',
        dataIndex: 'id',
        key: 'id',
        width: 350,
        ellipsis: {
          showTitle: false,
        },
        render: (_, record) => (
          <Tooltip title={record.id}>
            <code style={{ fontSize: '11px', cursor: 'pointer' }} onClick={() => {
              navigator.clipboard.writeText(record.id);
              message.success('ID copiado para área de transferência');
            }}>
              {record.id}
            </code>
          </Tooltip>
        ),
        sorter: (a, b) => a.id.localeCompare(b.id),
      },
      {
        title: 'Tipo',
        dataIndex: 'exporterType',
        key: 'exporterType',
        width: 150,
        render: (_, record) => {
          const text = record.exporterType || '-';
          const colorMap: Record<string, string> = {
            'Node Exporter': 'blue',
            'Windows Exporter': 'cyan',
            'MySQL Exporter': 'orange',
            'Redis Exporter': 'red',
            'PostgreSQL Exporter': 'purple',
            'MongoDB Exporter': 'green',
            'Blackbox Exporter': 'magenta',
            'SelfNode Exporter': 'blue',
            'Other Exporter': 'default',
          };
          return <Tag color={colorMap[text] || 'default'}>{text}</Tag>;
        },
        filters: Object.keys(summary.byType || {}).map((type) => ({
          text: type,
          value: type,
        })),
        onFilter: (value, record) => record.exporterType === value,
      },
      {
        title: 'No',
        dataIndex: 'node',
        key: 'node',
        width: 250,
        sorter: (a, b) => a.node.localeCompare(b.node),
      },
      {
        title: 'Endereco',
        dataIndex: 'address',
        key: 'address',
        width: 150,
        render: (_, record) => record.address || '-',
      },
      {
        title: 'Porta',
        dataIndex: 'port',
        key: 'port',
        width: 80,
        render: (_, record) => record.port || '-',
      },
      {
        title: 'Tags',
        dataIndex: 'tags',
        key: 'tags',
        width: 150,
        render: (_, record) =>
          record.tags?.length ? (
            <Space size={[4, 4]} wrap>
              {record.tags.slice(0, 3).map((tag, idx) => (
                <Tag key={idx}>{tag}</Tag>
              ))}
              {record.tags.length > 3 && <Tag>+{record.tags.length - 3}</Tag>}
            </Space>
          ) : (
            '-'
          ),
      },
      {
        title: 'Acoes',
        key: 'actions',
        fixed: 'right',
        width: 140,
        render: (_, record) => (
          <Space size="small">
            <Tooltip title="Ver detalhes">
              <Button
                type="link"
                size="small"
                icon={<InfoCircleOutlined />}
                onClick={() => handleShowDetails(record)}
              />
            </Tooltip>
            <Tooltip title="Editar exporter">
              <Button
                type="link"
                size="small"
                icon={<EditOutlined />}
                onClick={() => handleEditExporter(record)}
              />
            </Tooltip>
            <Popconfirm
              title="Remover este exporter?"
              description="Esta acao removera o exporter do Consul. Tem certeza?"
              onConfirm={() => handleDeleteExporter(record)}
              okText="Sim"
              cancelText="Nao"
            >
              <Tooltip title="Remover exporter">
                <Button
                  type="link"
                  size="small"
                  danger
                  icon={<DeleteOutlined />}
                />
              </Tooltip>
            </Popconfirm>
          </Space>
        ),
      },
    ];

    if (!metadataColumns.length) {
      return baseColumns;
    }

    const tagsIndex = baseColumns.findIndex((column) => column.key === 'tags');
    if (tagsIndex === -1) {
      return [...baseColumns, ...metadataColumns];
    }

    const beforeTags = baseColumns.slice(0, tagsIndex);
    const afterTags = baseColumns.slice(tagsIndex);
    return [...beforeTags, ...metadataColumns, ...afterTags];
  }, [metadataColumns, summary, handleDeleteExporter, handleEditExporter, handleShowDetails]);

  const visibleColumns = useMemo(() => {
    const visibleKeys = columnConfig.filter((c) => c.visible).map((c) => c.key);
    return allColumns.filter((col) => visibleKeys.includes(col.key as string)).map((col) => {
      const key = col.key as string;
      const width = columnWidths[key] || col.width;
      return {
        ...col,
        width,
        onHeaderCell: () => ({
          width,
          onResize: handleResize(key),
        }),
      };
    });
  }, [allColumns, columnConfig, columnWidths, handleResize]);

  const nodeSelector = useMemo(
    () => (
      <Select
        value={selectedNode}
        style={{ minWidth: 180 }}
        onChange={(value) => setSelectedNode(value)}
      >
        <Option value={ALL_NODES}>Todos os nos</Option>
        {nodes.map((node) => (
          <Option key={node.node} value={node.addr}>
            {node.node}
          </Option>
        ))}
      </Select>
    ),
    [nodes, selectedNode],
  );

  const advancedSearchFields = useMemo(() => {
    const baseFields = [
      { label: 'Servico', value: 'service', type: 'text' as const },
      { label: 'No', value: 'node', type: 'text' as const },
      { label: 'Tipo de Exporter', value: 'exporterType', type: 'text' as const },
    ];

    const metadataFieldOptions = metadataFields.map((field) => ({
      label: field.display_name || field.name,
      value: field.name,
      type: 'text' as const,
    }));

    return [...baseFields, ...metadataFieldOptions];
  }, [metadataFields]);

  return (
    <PageContainer
      header={{
        title: 'Exporters',
        subTitle: 'Dispositivos monitorados via exporters (Node, Windows, MySQL, Redis, etc.)',
      }}
    >
      <Space direction="vertical" size="middle" style={{ width: '100%' }}>
        {/* Summary Cards */}
        <Card>
          <Space size="large" wrap>
            <Statistic
              title="Total de Exporters"
              value={summary.total}
              prefix={<CloudServerOutlined />}
              valueStyle={{ color: '#3f8600' }}
            />
            {Object.entries(summary.byType || {}).map(([type, count]) => (
              <Statistic
                key={type}
                title={type}
                value={count as number}
              />
            ))}
          </Space>
        </Card>

        {/* Filters */}
        <Card size="small">
          <Space direction="vertical" size="middle" style={{ width: '100%' }}>
            <Space wrap>
              <MetadataFilterBar
                value={filters}
                options={metadataOptions}
                loading={metadataLoading}
                onChange={(newFilters) => {
                  setFilters(newFilters);
                  actionRef.current?.reload();
                }}
                onReset={() => {
                  setFilters({});
                  setSelectedNode(ALL_NODES);
                  actionRef.current?.reload();
                }}
                extra={nodeSelector}
              />
            </Space>

            <Space wrap>
              <Button
                type="primary"
                icon={<PlusOutlined />}
                onClick={() => setCreateModalOpen(true)}
              >
                Adicionar Exporter
              </Button>

              <Search
                placeholder="Buscar por nome, no, tipo..."
                allowClear
                enterButton
                style={{ width: 300 }}
                value={searchValue}
                onChange={(e) => setSearchValue(e.target.value)}
                onSearch={() => actionRef.current?.reload()}
              />

              <Button
                icon={<FilterOutlined />}
                onClick={() => setAdvancedOpen(!advancedOpen)}
              >
                Busca Avancada
                {advancedConditions.length > 0 && ` (${advancedConditions.length})`}
              </Button>

              {advancedConditions.length > 0 && (
                <Button
                  icon={<ClearOutlined />}
                  onClick={handleClearAdvancedSearch}
                >
                  Limpar Filtros Avancados
                </Button>
              )}

              <ColumnSelector
                columns={columnConfig}
                onChange={setColumnConfig}
                storageKey="exporters-columns-config"
              />

              <Button
                icon={<DownloadOutlined />}
                onClick={handleExportData}
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
                title="Remover exporters selecionados?"
                description="Esta acao removera os exporters selecionados do Consul. Tem certeza?"
                onConfirm={handleBatchDelete}
                okText="Sim"
                cancelText="Nao"
              >
                <Tooltip title="Remover exporters selecionados">
                  <Button
                    danger
                    icon={<DeleteOutlined />}
                    disabled={!selectedRows.length}
                  >
                    Remover selecionados ({selectedRows.length})
                  </Button>
                </Tooltip>
              </Popconfirm>
            </Space>

            {advancedOpen && (
              <AdvancedSearchPanel
                availableFields={advancedSearchFields}
                onSearch={handleAdvancedSearch}
                onClear={handleClearAdvancedSearch}
                initialConditions={advancedConditions}
                initialLogicalOperator={advancedOperator}
              />
            )}
          </Space>
        </Card>

        {/* Table */}
        <ProTable<ExporterTableItem>
          rowKey="key"
          columns={visibleColumns}
          search={false}
          actionRef={actionRef}
          request={requestHandler}
          params={{ keyword: searchValue }}
          components={{
            header: {
              cell: ResizableTitle,
            },
          }}
          rowSelection={{
            selectedRowKeys: selectedRows.map((r) => r.key),
            onChange: (_keys, rows) => setSelectedRows(rows),
          }}
          pagination={{
            defaultPageSize: 20,
            showSizeChanger: true,
            pageSizeOptions: ['10', '20', '30', '50', '100'],
          }}
          scroll={{ x: 1400 }}
          locale={{ emptyText: 'Nenhum exporter disponivel' }}
          options={{ density: true, fullScreen: true, reload: false, setting: false }}
          expandable={{
            expandedRowRender: (record) => (
              <Descriptions size="small" column={2} bordered style={{ margin: 0 }}>
                <Descriptions.Item label="ID">{record.id}</Descriptions.Item>
                <Descriptions.Item label="No">{record.node}</Descriptions.Item>
                <Descriptions.Item label="Endereco No">{record.nodeAddr || '-'}</Descriptions.Item>
                <Descriptions.Item label="Tipo">{record.exporterType}</Descriptions.Item>
                {Object.entries(record.meta || {}).map(([key, value]) => (
                  <Descriptions.Item label={key} key={`${record.id}-${key}`}>
                    {String(value ?? '')}
                  </Descriptions.Item>
                ))}
                {record.tags?.length ? (
                  <Descriptions.Item label="Tags" span={2}>
                    <Space size={[4, 4]} wrap>
                      {record.tags.map((tag, idx) => (
                        <Tag key={`${record.id}-expanded-${idx}`}>{tag}</Tag>
                      ))}
                    </Space>
                  </Descriptions.Item>
                ) : null}
              </Descriptions>
            ),
          }}
        />
      </Space>

      {/* Details Drawer */}
      <Drawer
        title="Detalhes do Exporter"
        placement="right"
        width={600}
        open={detailsDrawerVisible}
        onClose={() => setDetailsDrawerVisible(false)}
      >
        {selectedExporter && (
          <Descriptions column={1} bordered>
            <Descriptions.Item label="Servico">{selectedExporter.service}</Descriptions.Item>
            <Descriptions.Item label="Tipo">{selectedExporter.exporterType}</Descriptions.Item>
            <Descriptions.Item label="ID">{selectedExporter.id}</Descriptions.Item>
            <Descriptions.Item label="No">{selectedExporter.node}</Descriptions.Item>
            <Descriptions.Item label="Endereco No">{selectedExporter.nodeAddr || '-'}</Descriptions.Item>
            <Descriptions.Item label="Endereco">{selectedExporter.address || '-'}</Descriptions.Item>
            <Descriptions.Item label="Porta">{selectedExporter.port || '-'}</Descriptions.Item>
            {Object.entries(selectedExporter.meta || {}).map(([key, value]) => (
              <Descriptions.Item label={key} key={key}>
                {String(value ?? '')}
              </Descriptions.Item>
            ))}
            {selectedExporter.tags?.length ? (
              <Descriptions.Item label="Tags">
                <Space size={[4, 4]} wrap>
                  {selectedExporter.tags.map((tag, idx) => (
                    <Tag key={idx}>{tag}</Tag>
                  ))}
                </Space>
              </Descriptions.Item>
            ) : null}
          </Descriptions>
        )}
      </Drawer>

      {/* Advanced Search Drawer */}
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
          onClear={handleClearAdvancedSearch}
          initialConditions={advancedConditions}
          initialLogicalOperator={advancedOperator}
        />
      </Drawer>

      {/* Create Exporter Modal */}
      <ModalForm<CreateFormValues>
        title="Adicionar Novo Exporter"
        width={700}
        open={createModalOpen}
        onOpenChange={setCreateModalOpen}
        initialValues={{
          service: 'selfnode_exporter',
          port: 9100,
          os: 'linux',
        }}
        modalProps={{
          destroyOnHidden: true,
          onCancel: () => {
            setCreateModalOpen(false);
            setGeneratedId('');
          },
        }}
        submitter={{
          searchConfig: {
            submitText: 'Criar Exporter',
            resetText: 'Limpar',
          },
        }}
        onFinish={handleCreateSubmit}
        onValuesChange={(changedValues, allValues) => {
          // Quando o nó muda, buscar serviços daquele nó
          if (changedValues.node_addr) {
            setSelectedNodeForModal(changedValues.node_addr);
          }

          // Atualizar ID gerado conforme usuário preenche os campos
          if (allValues.vendor && allValues.account && allValues.region && allValues.group && allValues.name) {
            const id = `${allValues.vendor}/${allValues.account}/${allValues.region}/${allValues.group}@${allValues.name}`;
            setGeneratedId(id);
          } else {
            setGeneratedId('');
          }
        }}
      >
        <ProFormSelect
          name="node_addr"
          label="Nó do Consul"
          placeholder="Selecione o nó onde o serviço será registrado"
          rules={[{ required: true, message: 'Campo obrigatório' }]}
          options={nodes.map((node) => ({
            label: `${node.node} (${node.addr})`,
            value: node.addr,
          }))}
          tooltip="Escolha em qual nó do cluster Consul este exporter será registrado"
        />

        <ProFormSelect
          name="service"
          label="Tipo de Serviço"
          placeholder="Selecione o tipo de exporter"
          rules={[{ required: true, message: 'Campo obrigatório' }]}
          options={serviceNames.map((name) => ({
            label: name,
            value: name,
          }))}
          fieldProps={{
            loading: serviceNamesLoading,
          }}
          tooltip="Tipos de serviços disponíveis no catálogo do Consul"
        />

        <Text type="secondary" style={{ display: 'block', marginBottom: 16 }}>
          <strong>Campos para construção do ID:</strong> {generatedId || '(preencha os campos abaixo)'}
        </Text>

        <ProFormText
          name="vendor"
          label="Vendor"
          placeholder="Ex: Skills, GrupoWink"
          rules={[
            { required: true, message: 'Campo obrigatório' },
            { pattern: /^[a-zA-Z0-9_-]+$/, message: 'Apenas letras, números, _ e -' },
          ]}
          tooltip="Fornecedor ou empresa principal"
        />

        <ProFormText
          name="account"
          label="Account"
          placeholder="Ex: Aplicacao, AD, Monit_Print"
          rules={[
            { required: true, message: 'Campo obrigatório' },
            { pattern: /^[a-zA-Z0-9_-]+$/, message: 'Apenas letras, números, _ e -' },
          ]}
          tooltip="Conta ou departamento"
        />

        <ProFormText
          name="region"
          label="Region"
          placeholder="Ex: InfraLocal, Cliente"
          rules={[
            { required: true, message: 'Campo obrigatório' },
            { pattern: /^[a-zA-Z0-9_-]+$/, message: 'Apenas letras, números, _ e -' },
          ]}
          tooltip="Região ou localização"
        />

        <ProFormText
          name="group"
          label="Group"
          placeholder="Ex: DTC_Cluster_Local"
          rules={[
            { required: true, message: 'Campo obrigatório' },
            { pattern: /^[a-zA-Z0-9_-]+$/, message: 'Apenas letras, números, _ e -' },
          ]}
          tooltip="Grupo ou cluster"
        />

        <ProFormText
          name="name"
          label="Name"
          placeholder="Ex: HUDU_172.16.1.25"
          rules={[
            { required: true, message: 'Campo obrigatório' },
            { pattern: /^[a-zA-Z0-9_.-]+$/, message: 'Apenas letras, números, _, . e -' },
          ]}
          tooltip="Nome identificador único do exporter"
        />

        <ProFormText
          name="instance"
          label="Instance"
          placeholder="Ex: 192.168.1.10:9100"
          rules={[
            { required: true, message: 'Campo obrigatório' },
            { pattern: /^[\w.-]+:\d+$/, message: 'Formato inválido. Use: IP:PORTA' },
          ]}
          tooltip="Endereço no formato IP:PORTA"
        />

        <ProFormSelect
          name="os"
          label="Sistema Operacional"
          placeholder="Selecione o sistema operacional"
          rules={[{ required: true, message: 'Campo obrigatório' }]}
          options={[
            { label: 'Linux', value: 'linux' },
            { label: 'Windows', value: 'windows' },
          ]}
          tooltip="Sistema operacional do host monitorado"
        />

        <ProFormText
          name="address"
          label="Endereço"
          placeholder="Ex: 192.168.1.10"
          rules={[{ required: true, message: 'Campo obrigatório' }]}
          tooltip="Endereço IP ou hostname"
        />

        <ProFormDigit
          name="port"
          label="Porta"
          placeholder="Ex: 9100"
          min={1}
          max={65535}
          rules={[{ required: true, message: 'Campo obrigatório' }]}
          tooltip="Porta do exporter"
        />

        <ProFormSelect
          name="tags"
          label="Tags"
          mode="tags"
          placeholder="Adicione tags para classificação (opcional)"
          fieldProps={{
            tokenSeparators: [','],
          }}
          tooltip="Tags devem incluir o vendor e o tipo de OS correspondente"
        />
      </ModalForm>

      {/* Edit Exporter Modal */}
      <ModalForm<EditFormValues>
        title="Editar Exporter"
        width={700}
        open={editModalOpen}
        onOpenChange={setEditModalOpen}
        initialValues={editingExporter ? {
          node_addr: editingExporter.nodeAddr || editingExporter.node,
          vendor: editingExporter.meta?.vendor,
          account: editingExporter.meta?.account,
          region: editingExporter.meta?.region,
          group: editingExporter.meta?.group,
          name: editingExporter.meta?.name,
          instance: editingExporter.meta?.instance,
          os: (editingExporter.meta?.os as 'linux' | 'windows') || 'linux',
          address: editingExporter.address,
          port: editingExporter.port,
          tags: editingExporter.tags,
          company: editingExporter.meta?.company,
          project: editingExporter.meta?.project,
          env: editingExporter.meta?.env,
        } : {}}
        modalProps={{
          destroyOnHidden: true,
          onCancel: () => {
            setEditModalOpen(false);
            setEditingExporter(null);
          },
        }}
        submitter={{
          searchConfig: {
            submitText: 'Salvar alterações',
            resetText: 'Cancelar',
          },
        }}
        onFinish={handleEditSubmit}
        onValuesChange={(changedValues) => {
          // Quando o nó muda no EDIT, buscar serviços daquele nó
          if (changedValues.node_addr) {
            setSelectedNodeForModal(changedValues.node_addr);
          }
        }}
      >
        {editingExporter && (
          <>
            <Text type="secondary" style={{ display: 'block', marginBottom: 8 }}>
              <strong>ID Atual:</strong> <code>{editingExporter.id}</code>
            </Text>
            <Text type="secondary" style={{ display: 'block', marginBottom: 16 }}>
              <strong>Nó Atual:</strong> {editingExporter.node} ({editingExporter.nodeAddr || editingExporter.node})
            </Text>
          </>
        )}

        <Text type="warning" style={{ display: 'block', marginBottom: 16 }}>
          ⚠️ Alterar o nó ou os campos abaixo exigirá deregister + register do serviço
        </Text>

        <ProFormSelect
          name="node_addr"
          label="Nó do Consul"
          placeholder="Selecione o nó onde o serviço está/será registrado"
          rules={[{ required: true, message: 'Campo obrigatório' }]}
          options={nodes.map((node) => ({
            label: `${node.node} (${node.addr})`,
            value: node.addr,
          }))}
          tooltip="Escolha em qual nó do cluster Consul este exporter ficará registrado. Mudar o nó fará deregister no nó antigo e register no nó novo."
        />

        <ProFormText
          name="vendor"
          label="Vendor"
          placeholder="Ex: Skills, GrupoWink"
          rules={[
            { required: true, message: 'Campo obrigatório' },
            { pattern: /^[a-zA-Z0-9_-]+$/, message: 'Apenas letras, números, _ e -' },
          ]}
          tooltip="Fornecedor ou empresa principal"
        />

        <ProFormText
          name="account"
          label="Account"
          placeholder="Ex: Aplicacao, AD, Monit_Print"
          rules={[
            { required: true, message: 'Campo obrigatório' },
            { pattern: /^[a-zA-Z0-9_-]+$/, message: 'Apenas letras, números, _ e -' },
          ]}
          tooltip="Conta ou departamento"
        />

        <ProFormText
          name="region"
          label="Region"
          placeholder="Ex: InfraLocal, Cliente"
          rules={[
            { required: true, message: 'Campo obrigatório' },
            { pattern: /^[a-zA-Z0-9_-]+$/, message: 'Apenas letras, números, _ e -' },
          ]}
          tooltip="Região ou localização"
        />

        <ProFormText
          name="group"
          label="Group"
          placeholder="Ex: DTC_Cluster_Local"
          rules={[
            { required: true, message: 'Campo obrigatório' },
            { pattern: /^[a-zA-Z0-9_-]+$/, message: 'Apenas letras, números, _ e -' },
          ]}
          tooltip="Grupo ou cluster"
        />

        <ProFormText
          name="name"
          label="Name"
          placeholder="Ex: HUDU_172.16.1.25"
          rules={[
            { required: true, message: 'Campo obrigatório' },
            { pattern: /^[a-zA-Z0-9_.-]+$/, message: 'Apenas letras, números, _, . e -' },
          ]}
          tooltip="Nome identificador único do exporter"
        />

        <ProFormText
          name="instance"
          label="Instance"
          placeholder="Ex: 192.168.1.10:9100"
          rules={[
            { required: true, message: 'Campo obrigatório' },
            { pattern: /^[\w.-]+:\d+$/, message: 'Formato inválido. Use: IP:PORTA' },
          ]}
          tooltip="Endereço no formato IP:PORTA"
        />

        <ProFormSelect
          name="os"
          label="Sistema Operacional"
          placeholder="Selecione o sistema operacional"
          rules={[{ required: true, message: 'Campo obrigatório' }]}
          options={[
            { label: 'Linux', value: 'linux' },
            { label: 'Windows', value: 'windows' },
          ]}
          tooltip="Sistema operacional do host monitorado"
        />

        <Text type="secondary" style={{ display: 'block', marginBottom: 16, marginTop: 16 }}>
          <strong>Campos adicionais do Meta:</strong>
        </Text>

        <ProFormText
          name="company"
          label="Empresa"
          placeholder="Organização responsável"
          tooltip="Campo adicional de metadata"
        />

        <ProFormText
          name="project"
          label="Projeto"
          placeholder="Projeto associado"
          tooltip="Campo adicional de metadata"
        />

        <ProFormText
          name="env"
          label="Ambiente"
          placeholder="Ex: prod, dev, homolog"
          tooltip="Campo adicional de metadata"
        />

        <Text type="secondary" style={{ display: 'block', marginBottom: 16, marginTop: 16 }}>
          <strong>Configurações do serviço:</strong>
        </Text>

        <ProFormText
          name="address"
          label="Endereço"
          placeholder="Ex: 192.168.1.10"
          rules={[{ required: true, message: 'Campo obrigatório' }]}
          tooltip="Endereço IP ou hostname"
        />

        <ProFormDigit
          name="port"
          label="Porta"
          placeholder="Ex: 9100"
          min={1}
          max={65535}
          rules={[{ required: true, message: 'Campo obrigatório' }]}
          tooltip="Porta do exporter"
        />

        <ProFormSelect
          name="tags"
          label="Tags"
          mode="tags"
          placeholder="Adicione tags para classificação"
          fieldProps={{
            tokenSeparators: [','],
          }}
          tooltip="Tags para classificação do serviço"
        />
      </ModalForm>
    </PageContainer>
  );
};

export default Exporters;
