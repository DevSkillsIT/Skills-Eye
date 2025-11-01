import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  Alert,
  Button,
  Card,
  Descriptions,
  Dropdown,
  Drawer,
  Form,
  Input,
  message,
  Popconfirm,
  Space,
  Statistic,
  Tag,
  Tooltip,
  Typography,
} from 'antd';
import type { MenuProps } from 'antd';
import {
  ClearOutlined,
  DeleteOutlined,
  DownloadOutlined,
  EditOutlined,
  FilterOutlined,
  InfoCircleOutlined,
  MoreOutlined,
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
import { NodeSelector, useSelectedNode, type ConsulNode } from '../components/NodeSelector';
import { consulAPI } from '../services/api';
import type {
  MetadataFieldDynamic,
  ServiceUpdatePayload,
  ServiceCreatePayload,
  ServiceMeta,
} from '../services/api';
import { useFilterFields, useTableFields, useFormFields } from '../hooks/useMetadataFields';
import { useBatchEnsure } from '../hooks/useReferenceValues';
import { useServiceTags } from '../hooks/useServiceTags';
import ReferenceValueInput from '../components/ReferenceValueInput';
import TagsInput from '../components/TagsInput';
import FormFieldRenderer from '../components/FormFieldRenderer';

const { Search } = Input;
const { Text } = Typography;

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

// COLUNAS FIXAS (não metadata) - sempre presentes
const FIXED_EXPORTER_COLUMNS: ColumnConfig[] = [
  { key: 'service', title: 'Serviço', visible: true },
  { key: 'id', title: 'ID Consul', visible: true },
  { key: 'exporterType', title: 'Tipo', visible: true },
  { key: 'node', title: 'Nó', visible: true },
  { key: 'address', title: 'Endereço', visible: true },
  { key: 'port', title: 'Porta', visible: true },
  { key: 'tags', title: 'Tags', visible: false },
  { key: 'actions', title: 'Ações', visible: true, locked: true },
];

const Exporters: React.FC = () => {
  const actionRef = useRef<ActionType>(null);

  // SISTEMA DINÂMICO: Carregar campos metadata do backend
  const { tableFields } = useTableFields('exporters');
  const { formFields } = useFormFields('exporters');
  const { filterFields, loading: filterFieldsLoading } = useFilterFields('exporters');

  // SISTEMA DE AUTO-CADASTRO: Hooks para retroalimentação de valores
  const { batchEnsure } = useBatchEnsure();
  const { ensureTags } = useServiceTags({ autoLoad: false });

  const [nodes, setNodes] = useState<any[]>([]);
  const [searchValue, setSearchValue] = useState('');

  // SISTEMA DINÂMICO: filters agora é dinâmico (qualquer campo metadata)
  const [filters, setFilters] = useState<Record<string, string | undefined>>({});
  const [metadataOptions, setMetadataOptions] = useState<Record<string, string[]>>({});
  const [summary, setSummary] = useState<any>({ total: 0, byEnv: {}, byType: {} });

  // SISTEMA DINÂMICO: Combinar colunas fixas + campos metadata dinâmicos
  const defaultColumnConfig = useMemo<ColumnConfig[]>(() => {
    const metadataColumns: ColumnConfig[] = tableFields.map((field: MetadataFieldDynamic) => ({
      key: field.name,
      title: field.display_name,
      visible: field.show_in_table ?? true,
      locked: false,
    }));

    // ORDEM: service, id, exporterType, node → campos metadata → address, port, tags, actions
    return [
      FIXED_EXPORTER_COLUMNS[0], // service
      FIXED_EXPORTER_COLUMNS[1], // id
      FIXED_EXPORTER_COLUMNS[2], // exporterType
      FIXED_EXPORTER_COLUMNS[3], // node
      ...metadataColumns,         // campos dinâmicos
      FIXED_EXPORTER_COLUMNS[4], // address
      FIXED_EXPORTER_COLUMNS[5], // port
      FIXED_EXPORTER_COLUMNS[6], // tags
      FIXED_EXPORTER_COLUMNS[7], // actions
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
  const [masterNodeAddr, setMasterNodeAddr] = useState<string>(''); // Armazena o endereço do nó master
  const createFormRef = useRef<{ setFieldsValue: (values: Record<string, unknown>) => void } | null>(null); // Ref para controlar o formulário de criação

  // Hook para gerenciar nó selecionado na página principal
  const { selectedNode, isAllNodes, selectNode } = useSelectedNode();
  const [selectedNodeAddr, setSelectedNodeAddr] = useState<string>('all');
  const [showNodeAlert, setShowNodeAlert] = useState(false);

  useEffect(() => {
    fetchNodes();
  }, []);

  // AutoClose do Alert de nó selecionado após 5 segundos
  useEffect(() => {
    if (!isAllNodes && selectedNode) {
      setShowNodeAlert(true);
      const timer = setTimeout(() => {
        setShowNodeAlert(false);
      }, 5000);
      return () => clearTimeout(timer);
    } else {
      setShowNodeAlert(false);
    }
  }, [isAllNodes, selectedNode]);

  // Buscar serviços do nó selecionado quando mudar
  useEffect(() => {
    if (selectedNodeForModal) {
      fetchServiceNamesForNode(selectedNodeForModal);
    }
  }, [selectedNodeForModal]);

  // Quando modal CREATE abre, fazer PREFETCH de TODOS os nós em paralelo
  useEffect(() => {
    if (createModalOpen && nodes.length > 0) {
      console.log('[Exporters] Modal CREATE aberto, fazendo prefetch de job_names de TODOS os nós...');

      // Buscar job_names de TODOS os nós em paralelo
      // Isso popula o cache do backend para tornar as trocas instantâneas
      const prefetchPromises = nodes.map(async (node) => {
        try {
          console.log(`[Exporters] Prefetch: buscando job_names de ${node.node} (${node.addr})`);
          await consulAPI.getPrometheusJobNames(node.addr);
          console.log(`[Exporters] ✓ Prefetch completo para ${node.node}`);
        } catch (error) {
          console.warn(`[Exporters] ⚠ Erro no prefetch de ${node.node}:`, error);
          // Não falha se um nó der erro - continua com os outros
        }
      });

      // Executar todos em paralelo (não esperar - fire and forget)
      Promise.all(prefetchPromises).then(() => {
        console.log('[Exporters] ✓ Prefetch de todos os nós concluído - cache populado!');
      });

      // Carregar job_names do master para exibir imediatamente
      if (masterNodeAddr) {
        fetchServiceNamesForNode(masterNodeAddr);
      }
    }
  }, [createModalOpen, nodes, masterNodeAddr]);

  // Quando modal EDIT abre, buscar serviços do nó atual
  useEffect(() => {
    if (editModalOpen && editingExporter) {
      const nodeAddr = editingExporter.nodeAddr || editingExporter.node;
      if (nodeAddr) {
        setSelectedNodeForModal(nodeAddr);
      }
    }
  }, [editModalOpen, editingExporter]);

  // useEffect legado removido - agora usa hook useTableFields

  const fetchNodes = async () => {
    try {
      const response = await consulAPI.getNodes();
      const payload = response.data;
      const nodeList = Array.isArray(payload.data) ? payload.data : [];
      setNodes(nodeList);

      // Identificar o nó master (primeiro da lista) e armazenar seu endereço
      if (nodeList.length > 0) {
        const masterNode = nodeList[0];
        setMasterNodeAddr(masterNode.addr);
        console.log('[Exporters] Nó master identificado:', masterNode.addr, '-', masterNode.node);
      }
    } catch (error) {
      console.error('Error fetching nodes:', error);
    }
  };

  const fetchServiceNamesForNode = async (nodeAddr: string) => {
    try {
      setServiceNamesLoading(true);
      // Buscar job_names do Prometheus para aquele servidor
      // (não mais os serviços do Consul, mas os job_names configurados no prometheus.yml)
      const response = await consulAPI.getPrometheusJobNames(nodeAddr);
      const names = response.data?.job_names || [];
      setServiceNames(names);

      // Definir o primeiro job_name como padrão no campo "service" quando carregar
      if (names.length > 0 && createFormRef.current) {
        createFormRef.current.setFieldsValue({ service: names[0] });
        console.log(`[Exporters] Campo "service" definido como: ${names[0]}`);
      }
    } catch (error) {
      console.error('Error fetching Prometheus job names for node:', error);
      message.error('Erro ao carregar tipos de job do Prometheus para o nó selecionado');
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

        // Aplicar filtro de nó selecionado
        let nodeFilteredRows = rows;
        if (!isAllNodes && selectedNodeAddr && selectedNodeAddr !== 'all') {
          nodeFilteredRows = rows.filter((item) => {
            // Filtrar por node ou nodeAddr
            return item.nodeAddr === selectedNodeAddr || item.node === selectedNodeAddr;
          });
        }

        // Aplicar filtros avançados (se houver)
        const advancedRows = applyAdvancedFilters(nodeFilteredRows);

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
            const metadataValues = tableFields.map((field: MetadataFieldDynamic) => item.meta?.[field.name]);
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
    [applyAdvancedFilters, tableFields, searchValue, isAllNodes, selectedNodeAddr],
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
      // PASSO 1: AUTO-CADASTRO DE VALORES (Retroalimentação)
      // Antes de criar, garantir que valores novos sejam cadastrados automaticamente

      // 1A) Auto-cadastrar TAGS (se houver)
      if (values.tags && Array.isArray(values.tags) && values.tags.length > 0) {
        try {
          await ensureTags(values.tags);
        } catch (err) {
          console.warn('Erro ao auto-cadastrar tags:', err);
          // Não bloqueia o fluxo
        }
      }

      // 1B) Auto-cadastrar METADATA FIELDS de exporters
      // Campos típicos: vendor, account, region, group, name, instance, os
      const metadataValues: Array<{ fieldName: string; value: string }> = [];

      // Lista de campos que devem ser auto-cadastrados (se tiverem valor)
      const fieldsToEnsure: Array<keyof CreateFormValues> = ['vendor', 'account', 'region', 'group', 'name', 'instance', 'os'];

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

      // PASSO 2: CRIAR EXPORTER (lógica original)
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

  // ===========================
  // SISTEMA DINÂMICO: columnMap (fixas + metadata dinâmicas)
  // ===========================
  const columnMap = useMemo<Record<string, ExporterColumn<ExporterTableItem>>>(() => {
    // COLUNAS FIXAS com lógica específica
    const fixedColumns: Record<string, ExporterColumn<ExporterTableItem>> = {
      service: {
        title: 'Servico',
        dataIndex: 'service',
        key: 'service',
        width: 200,
        render: (_, record) => <Text strong>{record.service}</Text>,
        sorter: (a, b) => a.service.localeCompare(b.service),
      },
      id: {
        title: 'ID Consul',
        dataIndex: 'id',
        key: 'id',
        width: 350,
        ellipsis: {
          showTitle: false,
        },
        render: (_, record) => (
          <Tooltip title={record.id}>
            <code
              style={{ fontSize: '11px', cursor: 'pointer' }}
              onClick={() => {
                navigator.clipboard.writeText(record.id);
                message.success('ID copiado para área de transferência');
              }}
            >
              {record.id}
            </code>
          </Tooltip>
        ),
        sorter: (a, b) => a.id.localeCompare(b.id),
      },
      exporterType: {
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
      node: {
        title: 'No',
        dataIndex: 'node',
        key: 'node',
        width: 250,
        sorter: (a, b) => a.node.localeCompare(b.node),
      },
      address: {
        title: 'Endereco',
        dataIndex: 'address',
        key: 'address',
        width: 150,
        render: (_, record) => record.address || '-',
      },
      port: {
        title: 'Porta',
        dataIndex: 'port',
        key: 'port',
        width: 80,
        render: (_, record) => record.port || '-',
      },
      tags: {
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
      actions: {
        title: 'Acoes',
        key: 'actions',
        fixed: 'right',
        width: 80,
        render: (_, record) => {
          const menuItems: MenuProps['items'] = [
            {
              key: 'view',
              icon: <InfoCircleOutlined />,
              label: 'Ver Detalhes',
              onClick: () => handleShowDetails(record),
            },
            {
              key: 'edit',
              icon: <EditOutlined />,
              label: 'Editar',
              onClick: () => handleEditExporter(record),
            },
            {
              type: 'divider',
            },
            {
              key: 'delete',
              icon: <DeleteOutlined />,
              label: 'Remover',
              danger: true,
              onClick: () => {
                if (
                  window.confirm(
                    'Remover este exporter?\n\nEsta ação removerá o exporter do Consul. Tem certeza?',
                  )
                ) {
                  handleDeleteExporter(record);
                }
              },
            },
          ];

          return (
            <Dropdown
              menu={{ items: menuItems }}
              trigger={['click']}
              placement="bottomRight"
            >
              <Button type="text" icon={<MoreOutlined />} size="small" />
            </Dropdown>
          );
        },
      },
    };

    // COLUNAS METADATA DINÂMICAS
    const metadataColumns: Record<string, ExporterColumn<ExporterTableItem>> = {};
    tableFields.forEach((field: MetadataFieldDynamic) => {
      metadataColumns[field.name] = {
        title: field.display_name,
        dataIndex: ['meta', field.name],
        key: field.name,
        width: field.field_type === 'string' ? 200 : 140,
        ellipsis: true,
        tooltip: field.description,
        render: (_, record) => {
          const value = record.meta?.[field.name];

          // Render vazio para valores nulos/vazios
          if (value === undefined || value === null || value === '') {
            return <Text type="secondary">-</Text>;
          }

          // Render especial para tipo_monitoramento
          if (field.name === 'tipo_monitoramento' && typeof value === 'string') {
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

          // Render para arrays
          if (Array.isArray(value)) {
            if (!value.length) {
              return <Text type="secondary">-</Text>;
            }
            return value.join(', ');
          }

          // Render para booleanos
          if (typeof value === 'boolean') {
            return value ? 'Sim' : 'Nao';
          }

          // Render padrão
          return String(value);
        },
        sorter: (a, b) => {
          const valueA = a.meta?.[field.name];
          const valueB = b.meta?.[field.name];
          return String(valueA ?? '').localeCompare(String(valueB ?? ''));
        },
      };
    });

    // Combinar fixas + dinâmicas
    return { ...fixedColumns, ...metadataColumns };
  }, [tableFields, summary, handleDeleteExporter, handleEditExporter, handleShowDetails]);

  // ===========================
  // COLUNAS VISÍVEIS (filtradas por columnConfig)
  // ===========================
  const visibleColumns = useMemo<ExporterColumn<ExporterTableItem>[]>(() => {
    return columnConfig
      .filter((column) => column.visible)
      .map((column) => {
        const col = columnMap[column.key];
        if (!col) return null;
        const width = columnWidths[column.key] || col.width;
        return {
          ...col,
          width,
          onHeaderCell: () => ({
            width,
            onResize: handleResize(column.key),
          }),
        };
      })
      .filter(Boolean) as ExporterColumn<ExporterTableItem>[];
  }, [columnConfig, columnMap, columnWidths, handleResize]);

  // Handler para mudança de nó selecionado
  const handleNodeChange = useCallback((nodeAddr: string, node?: ConsulNode) => {
    selectNode(nodeAddr, node);
    setSelectedNodeAddr(nodeAddr);
    actionRef.current?.reload();
  }, [selectNode]);

  const advancedSearchFields = useMemo(() => {
    const baseFields = [
      { label: 'Servico', value: 'service', type: 'text' as const },
      { label: 'No', value: 'node', type: 'text' as const },
      { label: 'Tipo de Exporter', value: 'exporterType', type: 'text' as const },
    ];

    const metadataFieldOptions = tableFields.map((field: MetadataFieldDynamic) => ({
      label: field.display_name || field.name,
      value: field.name,
      type: 'text' as const,
    }));

    return [...baseFields, ...metadataFieldOptions];
  }, [tableFields]);

  return (
    <PageContainer
      header={{
        title: 'Exporters',
        subTitle: 'Dispositivos monitorados via exporters (Node, Windows, MySQL, Redis, etc.)',
      }}
    >
      <Space direction="vertical" size="middle" style={{ width: '100%' }}>
        {/* NodeSelector e Summary Cards */}
        <Card>
          <Space direction="vertical" size="middle" style={{ width: '100%' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 16, flexWrap: 'wrap' }}>
              <div style={{ flex: '0 0 auto' }}>
                <Text strong style={{ display: 'block', marginBottom: 8 }}>
                  Nó do Consul
                </Text>
                <NodeSelector
                  value={selectedNodeAddr}
                  onChange={handleNodeChange}
                  showAllNodesOption={true}
                  style={{ width: 400 }}
                />
              </div>

              <div style={{ flex: '1 1 auto', display: 'flex', gap: 24, flexWrap: 'wrap' }}>
                <Statistic
                  title="Total de Exporters"
                  value={summary.total}
                  prefix={<CloudServerOutlined />}
                  valueStyle={{ color: '#3f8600' }}
                />
                {Object.entries(summary.byType || {}).slice(0, 4).map(([type, count]) => (
                  <Statistic
                    key={type}
                    title={type}
                    value={count as number}
                  />
                ))}
              </div>
            </div>

            {/* Info de nó selecionado - AutoClose após 5s */}
            {!isAllNodes && selectedNode && showNodeAlert && (
              <Alert
                message={`Visualizando exporters do nó: ${selectedNode.name || selectedNode.addr}`}
                type="info"
                showIcon
                closable
                onClose={() => setShowNodeAlert(false)}
              />
            )}
          </Space>
        </Card>

        {/* Filtros, busca e ações na mesma linha */}
        <Card size="small">
          <Space direction="vertical" size="middle" style={{ width: '100%' }}>
            {/* Linha 1: Filtros metadata + busca + busca avançada */}
            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center' }}>
              <MetadataFilterBar
                fields={filterFields}
                value={filters}
                options={metadataOptions}
                loading={filterFieldsLoading}
                onChange={(newFilters) => {
                  setFilters(newFilters);
                  actionRef.current?.reload();
                }}
                onReset={() => {
                  setFilters({});
                  handleNodeChange('all');
                  actionRef.current?.reload();
                }}
              />

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
            </div>

            {/* Linha 2: Ações principais */}
            <Space wrap>
              <Button
                type="primary"
                icon={<PlusOutlined />}
                onClick={() => setCreateModalOpen(true)}
              >
                Adicionar Exporter
              </Button>

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

            {/* Painel de busca avançada */}
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
          scroll={{ x: 'max-content' }}
          sticky={{ offsetHeader: 0 }}
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
        width={900}
        layout="horizontal"
        grid={true}
        rowProps={{
          gutter: [16, 0],
        }}
        open={createModalOpen}
        onOpenChange={(open) => {
          setCreateModalOpen(open);
          // Limpar estado ao fechar
          if (!open) {
            setSelectedNodeForModal('');
            setGeneratedId('');
          }
        }}
        initialValues={{
          node_addr: masterNodeAddr, // Definir master como padrão
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
        formRef={createFormRef}
        onFinish={handleCreateSubmit}
        onValuesChange={(changedValues, allValues) => {
          // Quando o nó muda, buscar serviços daquele nó E limpar campo "service"
          if (changedValues.node_addr) {
            console.log(`[Exporters] Nó alterado para: ${changedValues.node_addr}`);
            setSelectedNodeForModal(changedValues.node_addr);

            // Limpar o campo "service" para forçar o usuário a selecionar um novo
            // (ou aguardar o fetchServiceNamesForNode definir o primeiro automaticamente)
            if (createFormRef.current) {
              createFormRef.current.setFieldsValue({ service: undefined });
              console.log('[Exporters] Campo "service" limpo');
            }
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
        {/* Seção: Configuração do Nó */}
        <ProFormSelect
          colProps={{ span: 12 }}
          name="node_addr"
          label="Nó do Consul"
          placeholder="Selecione o nó onde o serviço será registrado"
          rules={[{ required: true, message: 'Campo obrigatório' }]}
          fieldProps={{
            size: 'large',
            suffixIcon: <CloudServerOutlined />,
            optionLabelProp: 'label',
          }}
          options={nodes.map((node) => ({
            label: `${node.node} (${node.addr})`,
            value: node.addr,
          }))}
          tooltip="Escolha em qual nó do cluster Consul este exporter será registrado"
        />

        <ProFormSelect
          colProps={{ span: 12 }}
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

        {/* ID Preview */}
        <div style={{ gridColumn: '1 / -1', marginBottom: 16 }}>
          <Alert
            message={
              <span>
                <strong>ID Gerado:</strong> {generatedId || '(preencha os campos abaixo)'}
              </span>
            }
            type="info"
            showIcon
          />
        </div>

        {/* Seção: Campos do ID (Grid 2x3) */}
        <Form.Item
          name="vendor"
          label="Vendor"
          rules={[
            { required: true, message: 'Campo obrigatório' },
            { pattern: /^[a-zA-Z0-9_-]+$/, message: 'Apenas letras, números, _ e -' },
          ]}
          tooltip="Fornecedor ou empresa principal"
          style={{ gridColumn: 'span 12' }}
        >
          <ReferenceValueInput
            fieldName="vendor"
            placeholder="Selecione ou digite vendor (Ex: Skills, GrupoWink)"
            required
          />
        </Form.Item>

        <Form.Item
          name="account"
          label="Account"
          rules={[
            { required: true, message: 'Campo obrigatório' },
            { pattern: /^[a-zA-Z0-9_-]+$/, message: 'Apenas letras, números, _ e -' },
          ]}
          tooltip="Conta ou departamento"
          style={{ gridColumn: 'span 12' }}
        >
          <ReferenceValueInput
            fieldName="account"
            placeholder="Selecione ou digite account (Ex: Aplicacao, AD)"
            required
          />
        </Form.Item>

        <Form.Item
          name="region"
          label="Region"
          rules={[
            { required: true, message: 'Campo obrigatório' },
            { pattern: /^[a-zA-Z0-9_-]+$/, message: 'Apenas letras, números, _ e -' },
          ]}
          tooltip="Região ou localização"
          style={{ gridColumn: 'span 12' }}
        >
          <ReferenceValueInput
            fieldName="region"
            placeholder="Selecione ou digite region (Ex: InfraLocal, Cliente)"
            required
          />
        </Form.Item>

        <Form.Item
          name="group"
          label="Group"
          rules={[
            { required: true, message: 'Campo obrigatório' },
            { pattern: /^[a-zA-Z0-9_-]+$/, message: 'Apenas letras, números, _ e -' },
          ]}
          tooltip="Grupo ou cluster"
          style={{ gridColumn: 'span 12' }}
        >
          <ReferenceValueInput
            fieldName="group"
            placeholder="Selecione ou digite group (Ex: DTC_Cluster_Local)"
            required
          />
        </Form.Item>

        <Form.Item
          name="name"
          label="Name"
          rules={[
            { required: true, message: 'Campo obrigatório' },
            { pattern: /^[a-zA-Z0-9_.-]+$/, message: 'Apenas letras, números, _, . e -' },
          ]}
          tooltip="Nome identificador único do exporter"
          style={{ gridColumn: 'span 24' }}
        >
          <ReferenceValueInput
            fieldName="name"
            placeholder="Selecione ou digite name (Ex: HUDU_172.16.1.25)"
            required
          />
        </Form.Item>

        {/* Seção: Configuração do Exporter */}
        <Form.Item
          name="instance"
          label="Instance"
          rules={[
            { required: true, message: 'Campo obrigatório' },
            { pattern: /^[\w.-]+:\d+$/, message: 'Formato inválido. Use: IP:PORTA' },
          ]}
          tooltip="Endereço no formato IP:PORTA"
          style={{ gridColumn: 'span 16' }}
        >
          <ReferenceValueInput
            fieldName="instance"
            placeholder="Selecione ou digite instance (Ex: 192.168.1.10:9100)"
            required
          />
        </Form.Item>

        <ProFormSelect
          colProps={{ span: 8 }}
          name="os"
          label="Sistema Operacional"
          placeholder="Selecione o SO"
          rules={[{ required: true, message: 'Campo obrigatório' }]}
          options={[
            { label: 'Linux', value: 'linux' },
            { label: 'Windows', value: 'windows' },
          ]}
          tooltip="Sistema operacional do host monitorado"
        />

        <ProFormText
          colProps={{ span: 16 }}
          name="address"
          label="Endereço"
          placeholder="Ex: 192.168.1.10"
          rules={[{ required: true, message: 'Campo obrigatório' }]}
          tooltip="Endereço IP ou hostname"
        />

        <ProFormDigit
          colProps={{ span: 8 }}
          name="port"
          label="Porta"
          placeholder="Ex: 9100"
          min={1}
          max={65535}
          rules={[{ required: true, message: 'Campo obrigatório' }]}
          tooltip="Porta do exporter"
        />

        <Form.Item
          name="tags"
          label="Tags"
          tooltip="Tags devem incluir o vendor e o tipo de OS correspondente"
          style={{ gridColumn: 'span 24' }}
        >
          <TagsInput
            placeholder="Selecione ou digite tags"
          />
        </Form.Item>

        {/* CAMPOS METADATA DINÂMICOS ADICIONAIS */}
        {formFields
          .filter(field => !['vendor', 'account', 'region', 'group', 'name', 'instance', 'tags'].includes(field.name))
          .map(field => (
            <div key={field.name} style={{ gridColumn: 'span 12' }}>
              <FormFieldRenderer
                field={field}
                mode="create"
              />
            </div>
          ))
        }
      </ModalForm>

      {/* Edit Exporter Modal */}
      <ModalForm<EditFormValues>
        title="Editar Exporter"
        width={900}
        layout="horizontal"
        grid={true}
        rowProps={{
          gutter: [16, 0],
        }}
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
        {/* Informações do exporter atual */}
        {editingExporter && (
          <div style={{ gridColumn: '1 / -1', marginBottom: 16 }}>
            <Alert
              message={
                <div>
                  <div><strong>ID Atual:</strong> <code>{editingExporter.id}</code></div>
                  <div><strong>Nó Atual:</strong> {editingExporter.node} ({editingExporter.nodeAddr || editingExporter.node})</div>
                </div>
              }
              description="⚠️ Alterar o nó ou os campos do ID exigirá deregister + register do serviço"
              type="warning"
              showIcon
            />
          </div>
        )}

        {/* Seção: Configuração do Nó */}
        <ProFormSelect
          colProps={{ span: 24 }}
          name="node_addr"
          label="Nó do Consul"
          placeholder="Selecione o nó onde o serviço está/será registrado"
          rules={[{ required: true, message: 'Campo obrigatório' }]}
          fieldProps={{
            size: 'large',
            suffixIcon: <CloudServerOutlined />,
            optionLabelProp: 'label',
          }}
          options={nodes.map((node) => ({
            label: `${node.node} (${node.addr})`,
            value: node.addr,
          }))}
          tooltip="Escolha em qual nó do cluster Consul este exporter ficará registrado. Mudar o nó fará deregister no nó antigo e register no nó novo."
        />

        {/* Seção: Campos do ID */}
        <ProFormText
          colProps={{ span: 12 }}
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
          colProps={{ span: 12 }}
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
          colProps={{ span: 12 }}
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
          colProps={{ span: 12 }}
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
          colProps={{ span: 24 }}
          name="name"
          label="Name"
          placeholder="Ex: HUDU_172.16.1.25"
          rules={[
            { required: true, message: 'Campo obrigatório' },
            { pattern: /^[a-zA-Z0-9_.-]+$/, message: 'Apenas letras, números, _, . e -' },
          ]}
          tooltip="Nome identificador único do exporter"
        />

        {/* Seção: Configuração do Exporter */}
        <Form.Item
          name="instance"
          label="Instance"
          rules={[
            { required: true, message: 'Campo obrigatório' },
            { pattern: /^[\w.-]+:\d+$/, message: 'Formato inválido. Use: IP:PORTA' },
          ]}
          tooltip="Endereço no formato IP:PORTA"
          style={{ gridColumn: 'span 16' }}
        >
          <ReferenceValueInput
            fieldName="instance"
            placeholder="Selecione ou digite instance (Ex: 192.168.1.10:9100)"
            required
          />
        </Form.Item>

        <ProFormSelect
          colProps={{ span: 8 }}
          name="os"
          label="Sistema Operacional"
          placeholder="Selecione o SO"
          rules={[{ required: true, message: 'Campo obrigatório' }]}
          options={[
            { label: 'Linux', value: 'linux' },
            { label: 'Windows', value: 'windows' },
          ]}
          tooltip="Sistema operacional do host monitorado"
        />

        {/* CAMPOS METADATA DINÂMICOS ADICIONAIS */}
        {formFields
          .filter(field => !['vendor', 'account', 'region', 'group', 'name', 'instance', 'tags'].includes(field.name))
          .map(field => (
            <div key={field.name} style={{ gridColumn: 'span 12' }}>
              <FormFieldRenderer
                field={field}
                mode="edit"
              />
            </div>
          ))
        }

        {/* Seção: Configurações do Serviço */}
        <ProFormText
          colProps={{ span: 16 }}
          name="address"
          label="Endereço"
          placeholder="Ex: 192.168.1.10"
          rules={[{ required: true, message: 'Campo obrigatório' }]}
          tooltip="Endereço IP ou hostname"
        />

        <ProFormDigit
          colProps={{ span: 8 }}
          name="port"
          label="Porta"
          placeholder="Ex: 9100"
          min={1}
          max={65535}
          rules={[{ required: true, message: 'Campo obrigatório' }]}
          tooltip="Porta do exporter"
        />

        <ProFormSelect
          colProps={{ span: 24 }}
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
