/* eslint-disable @typescript-eslint/no-explicit-any, react-hooks/exhaustive-deps */
/**
 * Página de Gerenciamento de Campos Metadata (SOMENTE LEITURA)
 *
 * Permite:
 * - Visualizar campos metadata extraídos do prometheus.yml
 * - Ver status de sincronização entre servidores
 * - Sincronizar campos (extrai do Prometheus via SSH e atualiza KV)
 * - Replicar configurações do Master para Slaves
 * - Reiniciar serviços Prometheus
 *
 * IMPORTANTE: Campos vêm 100% do prometheus.yml (dinâmico)
 * Para adicionar/remover campos: edite prometheus.yml via PrometheusConfig
 */

import React, { useState, useEffect, useRef } from 'react';
import {
  PageContainer,
  ProTable,
  ProCard,
  ModalForm,
  ProFormText,
  ProFormSelect,
  ProFormSwitch,
  ProFormTextArea,
  ProFormDigit,
  ProDescriptions,
} from '@ant-design/pro-components';
import type { ProColumns } from '@ant-design/pro-components';
import {
  Button,
  Space,
  Tag,
  Badge,
  Select,
  Tooltip,
  Modal,
  Alert,
  Row,
  Col,
  Card,
  Typography,
  Drawer,
  Descriptions,
  Divider,
  App,
  Steps,
  List,
  message,
  Tabs,
  Collapse,
  Checkbox,
  Popover,
  Skeleton,
  Popconfirm,
  Form,
  Switch,
} from 'antd';
import type { CategoryInfo } from '../services/api';
import ExtractionProgressModal from '../components/ExtractionProgressModal';

const { Text, Paragraph } = Typography;
import {
  // EditOutlined RESTAURADO - edita configurações do campo (display_name, category, show_in_*, etc)
  EditOutlined,
  SyncOutlined,
  CloudDownloadOutlined,
  CheckCircleOutlined,
  MinusCircleOutlined,
  CloseCircleOutlined,
  WarningOutlined,
  CloudServerOutlined,
  InfoCircleOutlined,
  EyeOutlined,
  ThunderboltOutlined,
  FileTextOutlined,
  LoadingOutlined,
  ReloadOutlined,
  GlobalOutlined,
  ClusterOutlined,
  DeleteOutlined,
} from '@ant-design/icons';
import axios from 'axios';
import { metadataFieldsAPI, consulAPI } from '../services/api';
// metadataDynamicAPI removido - campos vêm 100% do Prometheus agora
import type { PreviewFieldChangeResponse } from '../services/api';
import type { ActionType } from '@ant-design/pro-components';
import ResizableTitle from '../components/ResizableTitle';

const API_URL = import.meta.env?.VITE_API_URL ?? 'http://localhost:5000/api/v1';

// ============================================================================
// COMPONENTE SEPARADO PARA POPOVER (soluciona erro de hooks em render)
// ============================================================================
interface PageVisibilityPopoverProps {
  record: MetadataField;
  onUpdate: (fieldName: string, updates: Partial<MetadataField>) => void;
}

const PageVisibilityPopover: React.FC<PageVisibilityPopoverProps> = ({ record, onUpdate }) => {
  const [popoverVisible, setPopoverVisible] = useState(false);

  const handleUpdateFieldConfig = async (fieldToUpdate: 'services' | 'exporters' | 'blackbox', newValue: boolean) => {
    try {
      // Preparar payload com apenas o campo que mudou
      const payload: any = {};
      if (fieldToUpdate === 'services') payload.show_in_services = newValue;
      if (fieldToUpdate === 'exporters') payload.show_in_exporters = newValue;
      if (fieldToUpdate === 'blackbox') payload.show_in_blackbox = newValue;

      // Salvar no JSON principal metadata/fields (fonte única da verdade)
      await axios.patch(`${API_URL}/metadata-fields/${record.name}`, payload);

      // Atualizar estado local via callback do pai
      onUpdate(record.name, payload);

      message.success(`Configuração do campo "${record.display_name}" atualizada!`);

      // Fechar Popover (evita cliques múltiplos)
      setPopoverVisible(false);
    } catch (error) {
      console.error('Erro ao atualizar configuração:', error);
      message.error('Erro ao atualizar configuração do campo');
    }
  };

  const content = (
    <div style={{ padding: '8px 0' }}>
      <Space direction="vertical" size="small">
        <Checkbox
          checked={record.show_in_services ?? true}
          onChange={(e) => handleUpdateFieldConfig('services', e.target.checked)}
        >
          <Tag color="blue" style={{ margin: 0 }}>Services</Tag>
        </Checkbox>
        <Checkbox
          checked={record.show_in_exporters ?? true}
          onChange={(e) => handleUpdateFieldConfig('exporters', e.target.checked)}
        >
          <Tag color="green" style={{ margin: 0 }}>Exporters</Tag>
        </Checkbox>
        <Checkbox
          checked={record.show_in_blackbox ?? true}
          onChange={(e) => handleUpdateFieldConfig('blackbox', e.target.checked)}
        >
          <Tag color="orange" style={{ margin: 0 }}>Blackbox</Tag>
        </Checkbox>
      </Space>
    </div>
  );

  return (
    <Popover
      content={content}
      title="Configurar visibilidade"
      trigger="click"
      placement="left"
      open={popoverVisible}
      onOpenChange={setPopoverVisible}
    >
      <Space size={4} wrap style={{ cursor: 'pointer' }}>
        {record.show_in_services !== false && (
          <Tooltip title="Aparece em formulários de Services">
            <Tag color="blue">Services</Tag>
          </Tooltip>
        )}
        {record.show_in_exporters !== false && (
          <Tooltip title="Aparece em formulários de Exporters">
            <Tag color="green">Exporters</Tag>
          </Tooltip>
        )}
        {record.show_in_blackbox !== false && (
          <Tooltip title="Aparece em formulários de Blackbox">
            <Tag color="orange">Blackbox</Tag>
          </Tooltip>
        )}
      </Space>
    </Popover>
  );
};

// ============================================================================

interface MetadataField {
  name: string;
  display_name: string;
  description: string;
  source_label: string;
  field_type: string;
  required: boolean;
  show_in_table: boolean;
  show_in_dashboard: boolean;
  show_in_form: boolean;
  show_in_services?: boolean;
  show_in_exporters?: boolean;
  show_in_blackbox?: boolean;
  options?: string[];
  order: number;
  category: string | string[];  // ← Suporta uma ou múltiplas categorias
  editable: boolean;
  validation_regex?: string;
  available_for_registration?: boolean;  // ← Auto-cadastro em Reference Values
  sync_status?: 'synced' | 'outdated' | 'missing' | 'orphan' | 'error';  // ← FASE 1: Status de sincronização
  sync_message?: string;  // ← FASE 1: Mensagem do status
  prometheus_target_label?: string;  // ← FASE 1: Label usado no Prometheus
  metadata_source_label?: string;  // ← FASE 1: Label metadata do Consul
  discovered_in?: string[];  // Lista de hostnames onde campo foi descoberto (MULTI-SERVER)
}

interface Server {
  id: string;
  hostname: string;
  port: number;
  username: string;
  type: string;
  display_name: string;
}

// Interfaces para gerenciamento de Sites (migrado de Settings.tsx)
interface NamingConfig {
  naming_strategy: 'option1' | 'option2';
  suffix_enabled: boolean;
  default_site: string;
  sites?: Site[];
}

interface PrometheusServer {
  hostname: string;
  port: number;
  external_labels: Record<string, string>;
  external_labels_count: number;
  status: 'success' | 'error';
  error?: string;
}

interface Site {
  code: string;                                   // Readonly: auto-detectado de external_labels.site
  name: string;                                   // Editável: nome descritivo do site
  is_default: boolean;                            // Editável: se true, não adiciona sufixo
  color?: string;                                 // Editável: cor do badge (blue, green, etc)
  prometheus_host?: string;                       // Readonly: auto-detectado de PROMETHEUS_CONFIG_HOSTS
  prometheus_port?: number;                       // Readonly: auto-detectado de PROMETHEUS_CONFIG_HOSTS
  external_labels?: Record<string, string>;       // Readonly: labels do prometheus.yml global
}

const MetadataFieldsPage: React.FC = () => {
  const { modal, message } = App.useApp();  // Hook para usar modal e message com contexto
  const [fields, setFields] = useState<MetadataField[]>([]);
  const [servers, setServers] = useState<Server[]>([]);
  const [selectedServer, setSelectedServer] = useState<string>('');
  const [loading, setLoading] = useState(false);
  const [loadingSyncStatus, setLoadingSyncStatus] = useState(false);
  const [serverJustChanged, setServerJustChanged] = useState(false);
  const [activeTab, setActiveTab] = useState<string>('meta-fields');  // Aba ativa
  const [externalLabels, setExternalLabels] = useState<Record<string, string>>({});  // External labels do servidor
  const [loadingExternalLabels, setLoadingExternalLabels] = useState(false);

  // Estado para categorias dinâmicas (carregadas da API)
  const [categories, setCategories] = useState<CategoryInfo[]>([]);
  const [loadingCategories, setLoadingCategories] = useState(false);

  // Hook para DELETE de campos metadata - REMOVIDO (página agora é SOMENTE LEITURA)
  // const { deleteResource: deleteFieldResource } = useConsulDelete({
  //   deleteFn: async (payload: any) => {
  //     const response = await axios.delete(`${API_URL}/metadata-fields/${payload.field_name}`);
  //     return response.data;
  //   },
  //   successMessage: 'Campo deletado com sucesso',
  //   errorMessage: 'Erro ao deletar campo',
  //   onSuccess: () => {
  //     fetchFields();
  //   },
  // });
  const [serverHasNoPrometheus, setServerHasNoPrometheus] = useState(false);  // ← NOVO: Detecta servidor sem Prometheus
  const [serverPrometheusMessage, setServerPrometheusMessage] = useState('');  // ← NOVO: Mensagem do servidor
  // createModalVisible REMOVIDO - não criamos mais campos manualmente (vêm do Prometheus)
  const [editModalVisible, setEditModalVisible] = useState(false);
  const [editingField, setEditingField] = useState<MetadataField | null>(null);
  const [fallbackWarningVisible, setFallbackWarningVisible] = useState(false);
  const [fallbackWarningMessage, setFallbackWarningMessage] = useState('');
  const fallbackTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // FASE 2: Preview de Mudanças
  const [previewModalVisible, setPreviewModalVisible] = useState(false);
  const [previewData, setPreviewData] = useState<PreviewFieldChangeResponse | null>(null);
  const [loadingPreview, setLoadingPreview] = useState(false);

  // FASE 3: Sincronização em Lote - MODAL COM ETAPAS
  const [batchSyncModalVisible, setBatchSyncModalVisible] = useState(false);
  const [currentStep, setCurrentStep] = useState(0);
  const [stepStatus, setStepStatus] = useState<Record<number, 'wait' | 'process' | 'finish' | 'error'>>({
    0: 'wait', // Preparação
    1: 'wait', // Sincronização (backend com ruamel.yaml)
    2: 'wait', // Reload Prometheus
    3: 'wait', // Verificação final
  });
  const [stepMessages, setStepMessages] = useState<Record<number, string>>({
    0: '',
    1: '',
    2: '',
    3: '',
  });

  // FASE 4: Drawer de Visualização
  const [drawerVisible, setDrawerVisible] = useState(false);
  const [drawerField, setDrawerField] = useState<MetadataField | null>(null);

  // Modal de progresso de extração (igual ao PrometheusConfig)
  const [progressModalVisible, setProgressModalVisible] = useState(false);
  const [fieldsData, setFieldsData] = useState<{
    fromCache: boolean;
    loading: boolean;
    successfulServers: number;
    totalServers: number;
    serverStatus: Array<{
      hostname: string;
      port?: number;
      status?: string;
      success: boolean;
      from_cache: boolean;
      files_count: number;
      fields_count: number;
      error?: string | null;
      duration_ms: number;
      external_labels?: Record<string, string>;
    }>;
    totalFields: number;
    fieldsError: string | null;
  }>({
    fromCache: false,
    loading: false,
    successfulServers: 0,
    totalServers: 0,
    serverStatus: [],
    totalFields: 0,
    fieldsError: null,
  });

  // ============================================================================
  // ESTADOS PARA GERENCIAMENTO DE SITES (consolidado com /metadata-fields)
  // ============================================================================
  const [config, setConfig] = useState<NamingConfig | null>(null);
  const [editModalOpen, setEditModalOpen] = useState(false);
  const [editingSite, setEditingSite] = useState<Site | null>(null);
  const [prometheusServers, setPrometheusServers] = useState<PrometheusServer[]>([]);
  const [loadingServers, setLoadingServers] = useState(false);
  const [columnWidths, setColumnWidths] = useState<Record<string, number>>({});
  const tableRef = useRef<ActionType>(null);

  // Callback para redimensionar colunas
  const handleResize = React.useCallback(
    (columnKey: string) =>
      (_: React.SyntheticEvent, { size }: { size: { width: number } }) => {
        setColumnWidths((prev) => ({ ...prev, [columnKey]: size.width }));
      },
    [],
  );

  // Callback para atualizar campo específico no estado (usado pelo Popover)
  const handleFieldUpdate = (fieldName: string, updates: Partial<MetadataField>) => {
    setFields(prevFields =>
      prevFields.map(f =>
        f.name === fieldName
          ? { ...f, ...updates }
          : f
      )
    );
  };

  /**
   * Carrega campos do backend (sem abrir modal)
   * Apenas atualiza os dados silenciosamente
   */
  const fetchFields = async () => {
    setLoading(true);

    try {
      // USAR ENDPOINT OTIMIZADO QUE JÁ FAZ MERGE NO BACKEND
      // CACHE-BUSTING: Adicionar timestamp para evitar cache do navegador
      const response = await axios.get(`${API_URL}/metadata-fields/?_t=${Date.now()}`, {
        timeout: 30000,
        headers: {
          'Cache-Control': 'no-cache',
          'Pragma': 'no-cache',
        }
      });

      if (response.data.success) {
        const fields = response.data.fields.map((field: any) => ({
          ...field,
          show_in_services: field.show_in_services ?? true,
          show_in_exporters: field.show_in_exporters ?? true,
          show_in_blackbox: field.show_in_blackbox ?? true,
        }));

        console.log(`[METADATA-FIELDS] ✅ ${fields.length} campos carregados`);

        // Detectar se veio do cache
        const fromCache = response.data.from_cache || false;
        const serverStatus = response.data.server_status || [];
        const successfulServers = response.data.successful_servers || 0;
        const totalServers = response.data.total_servers || 0;

        setFields(fields);

        // Atualizar estado (sem abrir modal)
        setFieldsData({
          fromCache,
          loading: false,
          successfulServers,
          totalServers,
          serverStatus,
          totalFields: fields.length,
          fieldsError: null,
        });

        if (fromCache) {
          console.log('[METADATA-FIELDS] ⚡ Campos carregados do CACHE (sem SSH)');
        } else {
          console.log(`[METADATA-FIELDS] 🔌 Campos extraídos via SSH de ${totalServers} servidores`);
        }
      }
    } catch (error: any) {
      const errorMsg = error.code === 'ECONNABORTED'
        ? 'Tempo esgotado ao carregar campos'
        : 'Erro ao carregar campos: ' + (error.response?.data?.detail || error.message);

      message.error(errorMsg);

      // Atualizar estado com erro
      setFieldsData(prev => ({
        ...prev,
        loading: false,
        fieldsError: errorMsg,
      }));
    } finally {
      setLoading(false);
    }
  };

  /**
   * Carrega campos E abre modal de progresso (usado no carregamento inicial)
   */
  const loadFieldsWithModal = async () => {
    console.log('[METADATA-FIELDS] 🔄 Carregando campos com modal...');

    // RESETAR estados ANTES de abrir o modal
    setFieldsData({
      fromCache: false,
      loading: true,
      successfulServers: 0,
      totalServers: 0,
      serverStatus: [],
      totalFields: 0,
      fieldsError: null,
    });

    // Abrir modal com estados limpos
    setProgressModalVisible(true);
    setLoading(true);

    // PASSO 1: Buscar lista de servidores para inicializar Timeline pré-populada
    // (igual PrometheusConfig - isso garante que SEMPRE mostra 3 servidores no modal)
    try {
      const serversResponse = await axios.get(`${API_URL}/metadata-fields/servers`);
      if (serversResponse.data.success && serversResponse.data.servers) {
        const serversList = serversResponse.data.servers as Array<{ id: string; name: string }>;

        // Inicializar Timeline com TODOS os servidores em "Processando..."
        const initialStatus = serversList.map((srv) => ({
          hostname: srv.id.split(':')[0], // Extrair IP de "172.16.1.26:8500"
          success: false,
          from_cache: false,
          files_count: 0,
          fields_count: 0,
          error: null,
          duration_ms: 0,
        }));

        setFieldsData(prev => ({
          ...prev,
          loading: true,
          serverStatus: initialStatus,
          totalServers: initialStatus.length,
          successfulServers: 0,
        }));

        console.log('[METADATA-FIELDS] ✅ Timeline inicializada com', initialStatus.length, 'servidores');
      }
    } catch (err) {
      console.error('[METADATA-FIELDS] Erro ao buscar servidores:', err);
    }

    // PASSO 2: Buscar campos (usa cache se disponível)
    try {
      const response = await axios.get(`${API_URL}/metadata-fields/?_t=${Date.now()}`, {
        timeout: 30000,
        headers: {
          'Cache-Control': 'no-cache',
          'Pragma': 'no-cache',
        }
      });

      if (response.data.success) {
        const fields = response.data.fields.map((field: any) => ({
          ...field,
          show_in_services: field.show_in_services ?? true,
          show_in_exporters: field.show_in_exporters ?? true,
          show_in_blackbox: field.show_in_blackbox ?? true,
        }));

        console.log(`[METADATA-FIELDS] ✅ ${fields.length} campos carregados`);

        // Detectar se veio do cache
        const fromCache = response.data.from_cache || false;
        const serverStatus = response.data.server_status || [];
        const successfulServers = response.data.successful_servers || 0;
        const totalServers = response.data.total_servers || 0;

        setFields(fields);

        // Atualizar estado do modal com dados reais
        setFieldsData({
          fromCache,
          loading: false,
          successfulServers,
          totalServers,
          serverStatus,
          totalFields: fields.length,
          fieldsError: null,
        });

        if (fromCache) {
          console.log('[METADATA-FIELDS] ⚡ Campos carregados do CACHE (sem SSH)');
        } else {
          console.log(`[METADATA-FIELDS] 🔌 Campos extraídos via SSH de ${totalServers} servidores`);
        }
      }
    } catch (error: any) {
      const errorMsg = error.code === 'ECONNABORTED'
        ? 'Tempo esgotado ao carregar campos'
        : 'Erro ao carregar campos: ' + (error.response?.data?.detail || error.message);

      message.error(errorMsg);

      setFieldsData(prev => ({
        ...prev,
        loading: false,
        fieldsError: errorMsg,
      }));
    } finally {
      setLoading(false);
    }
  };

  /**
   * Força extração SSH de TODOS os servidores (para botão "Atualizar Dados" do modal)
   */
  const forceRefreshFields = async () => {
    console.log('[METADATA-FIELDS] 🔄 FORCE REFRESH - Forçando extração SSH de TODOS os servidores...');

    // RESETAR estados ANTES de abrir o modal
    setFieldsData(prev => ({
      ...prev,
      loading: true,
      fromCache: false,
      successfulServers: 0,
      totalServers: 0,
      serverStatus: [],
      totalFields: 0,
      fieldsError: null,
    }));

    // Abrir modal com estados limpos
    setProgressModalVisible(true);
    setLoading(true);

    try {
      // CHAMAR FORCE-EXTRACT SEM server_id = extrai de TODOS os servidores
      const response = await axios.post(
        `${API_URL}/metadata-fields/force-extract`,
        {}, // ← SEM server_id = TODOS os servidores
        {
          timeout: 60000, // 60 segundos
          headers: {
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache',
          }
        }
      );

      console.log('[METADATA-FIELDS] ✅ Force extract concluído:', response.data);

      if (response.data.success) {
        // IMPORTANTE: Usar campos retornados pelo force-extract DIRETAMENTE
        // NÃO buscar do KV porque force-extract não salva no KV (EXTRAIR ≠ SINCRONIZAR)

        const extractedFields = response.data.fields || [];

        // Criar set de campos novos para identificação
        const newFieldsSet = new Set(response.data.new_fields || []);

        const fields = extractedFields.map((field: any) => {
          const isNewField = newFieldsSet.has(field.name);

          return {
            ...field,
            show_in_services: field.show_in_services ?? true,
            show_in_exporters: field.show_in_exporters ?? true,
            show_in_blackbox: field.show_in_blackbox ?? true,
            // Campos NOVOS extraídos do Prometheus = status "missing"
            sync_status: isNewField ? 'missing' : undefined,
            sync_message: isNewField ? 'Campo encontrado no Prometheus mas não aplicado no KV' : undefined,
          };
        });

        console.log(`[METADATA-FIELDS] ✅ ${fields.length} campos extraídos diretamente do force-extract`);
        console.log(`[METADATA-FIELDS] 🆕 ${response.data.new_fields_count || 0} campos novos descobertos`);

        setFields(fields);

        // Atualizar estado do modal usando dados da resposta do force-extract
        setFieldsData({
          fromCache: false, // SEMPRE false porque acabamos de extrair via SSH
          loading: false,
          successfulServers: response.data.servers_success || 0,
          totalServers: response.data.servers_checked || 0,
          serverStatus: [], // Force-extract não retorna server_status detalhado
          totalFields: fields.length,
          fieldsError: null,
        });

        const newFieldsCount = response.data.new_fields_count || 0;
        if (newFieldsCount > 0) {
          message.success(
            `Extração forçada concluída! ${fields.length} campos extraídos, ${newFieldsCount} novos descobertos.`,
            8
          );
        } else {
          message.success(`Extração forçada concluída! ${fields.length} campos extraídos, nenhum campo novo.`);
        }
      }
    } catch (error: any) {
      const errorMsg = error.code === 'ECONNABORTED'
        ? 'Timeout ao forçar extração (60s)'
        : 'Erro ao forçar extração: ' + (error.response?.data?.detail || error.message);

      message.error(errorMsg);

      // Atualizar estado com erro
      setFieldsData(prev => ({
        ...prev,
        loading: false,
        fieldsError: errorMsg,
      }));
    } finally {
      setLoading(false);
    }
  };

  const fetchExternalLabels = async (serverId: string) => {
    if (!serverId) {
      setExternalLabels({});
      return;
    }

    setLoadingExternalLabels(true);
    try {
      // Buscar servidor para pegar hostname
      const server = servers.find(s => s.id === serverId);
      if (!server) {
        setExternalLabels({});
        return;
      }

      // REUTILIZAR endpoint /prometheus-config/global
      const response = await axios.get(`${API_URL}/prometheus-config/global`, {
        params: { hostname: server.hostname },
        timeout: 15000,
      });

      const labels = response.data?.external_labels || {};
      console.log('[DEBUG] External labels carregados:', labels);
      console.log('[DEBUG] Keys:', Object.keys(labels));
      setExternalLabels(labels);
    } catch (error: any) {
      console.error('Erro ao buscar external_labels:', error);
      setExternalLabels({});
    } finally {
      setLoadingExternalLabels(false);
    }
  };

  const fetchServers = async () => {
    try {
      const response = await axios.get(`${API_URL}/metadata-fields/servers`, {
        timeout: 15000, // 15 segundos (primeira requisição pode consultar Consul)
      });
      if (response.data.success) {
        setServers(response.data.servers);
        // Selecionar master por padrão
        if (response.data.master) {
          setSelectedServer(response.data.master.id);
        }
      }
    } catch (error: any) {
      if (error.code === 'ECONNABORTED') {
        message.error('Tempo esgotado ao carregar servidores (servidor lento)');
      } else {
        message.error('Erro ao carregar servidores: ' + (error.response?.data?.detail || error.message));
      }
    }
  };

  const fetchCategories = async () => {
    setLoadingCategories(true);
    try {
      const response = await axios.get(`${API_URL}/reference-values/categories`, {
        timeout: 60000, // 60s - StrictMode causa requisições duplicadas em dev
      });
      if (response.data.success && response.data.categories) {
        setCategories(response.data.categories);
        console.log(`[METADATA-FIELDS] ✅ ${response.data.categories.length} categorias carregadas`);
      }
    } catch (error: any) {
      console.error('[METADATA-FIELDS] Erro ao carregar categorias:', error);
      message.error('Erro ao carregar categorias: ' + (error.response?.data?.detail || error.message));
      // Fallback vazio (permitir digitar manualmente)
      setCategories([]);
    } finally {
      setLoadingCategories(false);
    }
  };

  const fetchSyncStatus = async (serverId: string) => {
    if (!serverId) return;

    setLoadingSyncStatus(true);
    try {
      // CACHE-BUSTING: Adicionar timestamp para evitar cache do navegador
      const response = await axios.get(`${API_URL}/metadata-fields/sync-status`, {
        params: {
          server_id: serverId,
          _t: Date.now()  // ← Cache-busting
        },
        timeout: 30000, // 30 segundos (SSH pode ser lento)
        headers: {
          'Cache-Control': 'no-cache',
          'Pragma': 'no-cache',
        }
      });

      if (response.data.success) {
        // Detectar se servidor tem Prometheus
        const hasNoPrometheus = response.data.message &&
          response.data.message.toLowerCase().includes('não possui prometheus');

        setServerHasNoPrometheus(hasNoPrometheus);
        setServerPrometheusMessage(hasNoPrometheus ? response.data.message : '');

        if (response.data.fallback_used) {
          if (fallbackTimerRef.current) {
            clearTimeout(fallbackTimerRef.current);
          }
          setFallbackWarningMessage('Estrutura avançada detectada no prometheus.yml (fallback aplicado)');
          setFallbackWarningVisible(true);
          fallbackTimerRef.current = setTimeout(() => {
            setFallbackWarningVisible(false);
            setFallbackWarningMessage('');
          }, 10000);
        } else if (fallbackWarningVisible) {
          if (fallbackTimerRef.current) {
            clearTimeout(fallbackTimerRef.current);
            fallbackTimerRef.current = null;
          }
          setFallbackWarningVisible(false);
          setFallbackWarningMessage('');
        }

        // Atualizar campos com status de sincronização
        const syncStatusMap = new Map<string, {
          sync_status: 'synced' | 'outdated' | 'missing' | 'error';
          sync_message: string;
        }>(
          response.data.fields.map((f: any) => [f.name, {
            sync_status: f.sync_status as 'synced' | 'outdated' | 'missing' | 'error',
            sync_message: f.message as string
          }])
        );

        setFields((prevFields) =>
          prevFields.map((field): MetadataField => {
            const statusFromSync = syncStatusMap.get(field.name);

            // Se tem status do sync-status, usar ele
            if (statusFromSync) {
              return {
                ...field,
                sync_status: statusFromSync.sync_status,
                sync_message: statusFromSync.sync_message,
              };
            }

            // Se NÃO tem status do sync-status, PRESERVAR status atual
            // (isso é importante para campos novos que foram setados como "missing" no force-extract)
            return {
              ...field,
              sync_status: field.sync_status || 'error',
              sync_message: field.sync_message || 'Status desconhecido',
            };
          })
        );

        if (!hasNoPrometheus) {
          message.success(`Status verificado: ${response.data.total_synced} sincronizado(s), ${response.data.total_missing} faltando`);
        }
      }
    } catch (error: any) {
      console.error('[SYNC-STATUS] Erro ao verificar sincronização:', error);

      // Limpar status de sincronização em caso de erro
      setFields((prevFields) =>
        prevFields.map((field) => ({
          ...field,
          sync_status: 'error',
          sync_message: 'Erro ao verificar status',
        }))
      );

      if (fallbackTimerRef.current) {
        clearTimeout(fallbackTimerRef.current);
        fallbackTimerRef.current = null;
      }
      setFallbackWarningVisible(false);
      setFallbackWarningMessage('');

      if (error.code === 'ECONNABORTED') {
        message.error('Tempo esgotado ao verificar sincronização (mais de 30 segundos). Verifique a conexão SSH.');
      } else if (error.response?.status === 404) {
        message.error(
          error.response?.data?.detail ||
          'Servidor não encontrado ou arquivo prometheus.yml não existe.'
        );
      } else if (error.response?.status === 403) {
        message.error('Permissão negada. Verifique as credenciais SSH no arquivo .env');
      } else if (error.response?.data?.detail) {
        message.error('Erro: ' + error.response.data.detail, 5); // 5 segundos
      } else {
        message.error('Erro ao verificar sincronização: ' + error.message);
      }
    } finally {
      setLoadingSyncStatus(false);
    }
  };

  /**
   * Força extração manual de campos do Prometheus via SSH
   * Extrai APENAS do servidor selecionado (não de todos)
   */
  const [loadingForceExtract, setLoadingForceExtract] = useState(false);

  const handleForceExtract = async () => {
    if (!selectedServer) {
      message.warning('Selecione um servidor primeiro');
      return;
    }

    try {
      setLoadingForceExtract(true);

      // Buscar servidor no array para pegar o hostname (sem porta)
      const server = servers.find(s => s.id === selectedServer);
      if (!server) {
        message.error('Servidor não encontrado');
        setLoadingForceExtract(false);
        return;
      }

      const serverName = server.display_name || server.hostname;

      message.loading({
        content: `Extraindo campos do servidor ${serverName} via SSH...`,
        key: 'force-extract',
        duration: 0
      });

      const response = await axios.post(`${API_URL}/metadata-fields/force-extract`, {
        server_id: server.hostname  // ← Extrai APENAS deste servidor
      }, {
        timeout: 60000
      });

      message.destroy('force-extract');

      if (response.data.success) {
        const { new_fields_count, total_fields, new_fields, fields } = response.data;

        if (new_fields_count > 0) {
          message.success(
            `✅ ${new_fields_count} campo(s) novo(s) encontrado(s) no servidor ${serverName}! Total: ${total_fields} campos.`,
            8
          );

          if (new_fields && new_fields.length > 0) {
            console.log('[FORCE-EXTRACT] Novos campos:', new_fields);
          }
        } else {
          message.info(`Nenhum campo novo encontrado no servidor ${serverName}. Total: ${total_fields} campos.`, 5);
        }

        // IMPORTANTE: Usar campos retornados pelo force-extract (dados ATUAIS do Prometheus)
        // NÃO buscar do KV porque KV pode ter dados antigos
        if (fields && fields.length > 0) {
          // Criar set de campos novos para identificação rápida
          const newFieldsSet = new Set(new_fields || []);

          const fieldsWithDefaults = fields.map((field: any) => {
            const isNewField = newFieldsSet.has(field.name);

            return {
              ...field,
              show_in_services: field.show_in_services ?? true,
              show_in_exporters: field.show_in_exporters ?? true,
              show_in_blackbox: field.show_in_blackbox ?? true,
              // Campos NOVOS extraídos do Prometheus mas não no KV = status "missing"
              sync_status: isNewField ? 'missing' : undefined,
              sync_message: isNewField ? 'Campo encontrado no Prometheus mas não aplicado no KV' : undefined,
            };
          });

          setFields(fieldsWithDefaults);
          console.log('[FORCE-EXTRACT] ✅ Lista de campos atualizada:', {
            total: fieldsWithDefaults.length,
            novos: new_fields_count,
            novos_com_status_missing: fieldsWithDefaults.filter((f: any) => f.sync_status === 'missing').length
          });
        }

        // Atualizar sync status dos campos EXISTENTES (não novos)
        // Isso atualiza o status dos campos que já estavam no KV
        if (selectedServer) {
          await fetchSyncStatus(selectedServer);
        }

        // CRÍTICO: Recarregar external_labels após extração
        // Garante que aba "External Labels (Todos Servidores)" mostre dados atualizados
        await fetchPrometheusServers();
      }
    } catch (error: any) {
      message.destroy('force-extract');
      console.error('[FORCE-EXTRACT] Erro:', error);

      if (error.code === 'ECONNABORTED') {
        message.error('⏱️ Timeout: Extração demorou mais de 60s. Tente novamente.', 10);
      } else if (error.response?.data?.detail) {
        message.error('Erro: ' + error.response.data.detail, 8);
      } else {
        message.error('Erro ao extrair campos: ' + error.message, 8);
      }
    } finally {
      setLoadingForceExtract(false);
    }
  };

  // ============================================================================
  // FUNÇÕES PARA GERENCIAMENTO DE SITES (migrado de Settings.tsx)
  // ============================================================================

  const loadConfig = async () => {
    setLoading(true);
    try {
      // PASSO 1: Buscar naming strategy do backend (.env)
      const namingResponse = await fetch('/api/v1/settings/naming-config');
      if (!namingResponse.ok) {
        throw new Error(`HTTP ${namingResponse.status}: ${namingResponse.statusText}`);
      }
      const namingData = await namingResponse.json();
      
      // PASSO 2: Buscar sites auto-detectados (NOVO ENDPOINT - metadata-fields/config/sites)
      const sitesResponse = await axios.get(`${API_URL}/metadata-fields/config/sites`);
      const sitesData = sitesResponse.data;
      
      // PASSO 3: Mesclar dados
      setConfig({
        naming_strategy: namingData.naming_strategy,
        suffix_enabled: namingData.suffix_enabled,
        default_site: namingData.default_site,
        sites: sitesData.sites || []
      });
      message.success('Configurações carregadas com sucesso');
    } catch (error) {
      console.error('[Settings] Erro ao carregar configurações:', error);
      message.error(`Erro ao carregar configurações: ${error}`);
    } finally {
      setLoading(false);
    }
  };

  const fetchPrometheusServers = async () => {
    setLoadingServers(true);
    try {
      // Busca servidores com external_labels do KV (já extraídos via SSH)
      const serversResponse = await fetch('/api/v1/metadata-fields/servers');

      if (!serversResponse.ok) {
        throw new Error(`Erro ao buscar servidores: ${serversResponse.statusText}`);
      }

      const serversData = await serversResponse.json();
      const serverList = serversData.servers || [];

      if (serverList.length === 0) {
        message.warning('Nenhum servidor Prometheus configurado no .env');
        setPrometheusServers([]);
        return;
      }

      // Mapear servidores com external_labels do endpoint
      // O endpoint /servers JÁ retorna external_labels extraídos do KV
      setPrometheusServers(serverList.map((server: any) => ({
        hostname: server.hostname,
        port: server.port || 22,
        external_labels: server.external_labels || {},
        external_labels_count: Object.keys(server.external_labels || {}).length,
        status: Object.keys(server.external_labels || {}).length > 0 ? 'success' : 'pending'
      })));

      console.log('[External Labels] Servidores carregados:', serverList.length);

    } catch (error: any) {
      console.error('[External Labels] Erro ao carregar servidores:', error);
      message.error(`Erro: ${error.message}`);
      setPrometheusServers([]);
    } finally {
      setLoadingServers(false);
    }
  };

  // Helper: Buscar external_labels para um prometheus_host específico
  const getExternalLabelsForHost = (prometheus_host: string | undefined): Record<string, string> => {
    if (!prometheus_host) return {};
    const server = prometheusServers.find(s => s.hostname === prometheus_host);
    return server?.external_labels || {};
  };

  // ============================================================================
  // CRUD DE SITES (CONSOLIDADO - USA /metadata-fields)
  // ============================================================================

  /**
   * Sincroniza sites automaticamente do Prometheus
   * Dispara extração SSH e auto-detecta sites de external_labels
   */
  const handleSyncSites = async () => {
    setLoadingServers(true);
    try {
      const response = await axios.post(`${API_URL}/metadata-fields/config/sites/sync`);
      const data = response.data;
      
      if (data.success) {
        const newCount = data.new_sites?.length || 0;
        const totalCount = data.sites_synced || 0;
        
        if (newCount > 0) {
          message.success(
            `Sincronização completa! ${newCount} site(s) novo(s) detectado(s) de ${totalCount} total(is).`
          );
        } else {
          message.info(`Sincronização completa. ${totalCount} site(s) encontrado(s), nenhum novo.`);
        }
        
        // Recarregar configurações e tabela
        await loadConfig();
        tableRef.current?.reload();
      } else {
        throw new Error(data.message || 'Erro na sincronização');
      }
    } catch (error: any) {
      console.error('Erro ao sincronizar sites:', error);
      message.error(`Erro ao sincronizar sites: ${error.message || error}`);
    } finally {
      setLoadingServers(false);
    }
  };

  /**
   * Remove campo órfão do KV
   * Campos órfãos são campos que existem no KV mas não no Prometheus (status 'missing')
   */
  const handleRemoveOrphanField = async (fieldName: string) => {
    try {
      const response = await axios.post(
        `${API_URL}/metadata-fields/remove-orphans`,
        { field_names: [fieldName] }
      );

      if (response.data.success) {
        message.success(`Campo órfão "${fieldName}" removido com sucesso`);
        
        // Recarregar lista de campos
        await loadFields();
        
        // Se tiver servidor selecionado, recarregar sync status também
        if (selectedServer) {
          await fetchSyncStatus(selectedServer);
        }
      } else {
        message.error('Erro ao remover campo órfão');
      }
    } catch (error: any) {
      console.error('Erro ao remover campo órfão:', error);
      message.error(`Erro ao remover campo órfão: ${error.response?.data?.detail || error.message}`);
    }
  };

  /**
   * Atualiza configurações editáveis de um site (name, color, is_default)
   * Campos readonly (code, prometheus_host, external_labels) não podem ser alterados
   */
  const handleUpdateSite = async (values: Site) => {
    if (!editingSite) return false;

    try {
      // PATCH apenas campos editáveis (NOVO ENDPOINT)
      const response = await axios.patch(
        `${API_URL}/metadata-fields/config/sites/${editingSite.code}`,
        {
          name: values.name,
          color: values.color,
          is_default: values.is_default
        }
      );

      if (response.data.success) {
        message.success('Site atualizado com sucesso');
        setEditModalOpen(false);
        setEditingSite(null);
        await loadConfig();
        tableRef.current?.reload();
        return true;
      } else {
        throw new Error(response.data.message || 'Erro ao atualizar site');
      }
    } catch (error: any) {
      console.error('Erro ao atualizar site:', error);
      message.error(`Erro: ${error.response?.data?.detail || error.message}`);
      return false;
    }
  };

  /**
   * REMOVIDO: handleDeleteSite
   * Sites são auto-detectados do Prometheus, não podem ser deletados manualmente
   * Se um site não deve aparecer, remova-o do Prometheus ou de PROMETHEUS_CONFIG_HOSTS
   */

  /**
   * REMOVIDO: handleCreateSite
   * Sites são auto-detectados automaticamente via sincronização
   * Não faz sentido criar sites manualmente
   */

  /**
   * REMOVIDO: handleAutoFillPrometheusHosts
   * prometheus_host agora é readonly, vem automaticamente do .env (PROMETHEUS_CONFIG_HOSTS)
   * Não precisa preencher manualmente
   */

  // Aplicar larguras redimensionáveis nas colunas
  const applyResizableWidth = (col: any, key: string) => {
    const width = columnWidths[key] || col.width;
    return {
      ...col,
      width,
      onHeaderCell: () => ({
        width,
        onResize: handleResize(key),
      }),
    };
  };

  // ============================================================================
  // CARREGAMENTO INICIAL
  // ============================================================================

  // Carregamento inicial: servidores + campos + categorias + sync status + config + prometheusServers (UMA VEZ APENAS)
  useEffect(() => {
    const initializeData = async () => {
      // OTIMIZAÇÃO: Executar chamadas independentes em PARALELO
      // PASSO 1: Carregar servidores, categorias, config e prometheus servers em paralelo
      await Promise.all([
        fetchServers(),
        fetchCategories(),
        loadConfig(),
        fetchPrometheusServers(), // Necessário para aba "External Labels (Todos Servidores)"
      ]);

      // PASSO 2: Carregar campos COM modal (depende de servidores estarem carregados)
      // loadFieldsWithModal() busca de todos os servidores e abre modal automaticamente
      await loadFieldsWithModal();

      // PASSO 3: Após carregar servidores e campos, carregar external_labels e sync status do servidor selecionado
      // IMPORTANTE: selectedServer já foi setado por fetchServers() no passo 1
      if (selectedServer) {
        console.log('[DEBUG INIT] Carregando external_labels e sync status inicial...');
        // OTIMIZAÇÃO: Carregar em paralelo
        await Promise.all([
          fetchExternalLabels(selectedServer),
          fetchSyncStatus(selectedServer)
        ]);
        console.log('[DEBUG INIT] Carregamento inicial completo!');
      }
    };

    initializeData();
  }, []); // Array vazio = executa apenas no mount

  // Quando trocar de servidor: APENAS atualizar sync status (não recarrega campos)
  useEffect(() => {
    if (selectedServer && fields.length > 0) {
      // Animação de "servidor alterado"
      setServerJustChanged(true);
      setTimeout(() => setServerJustChanged(false), 2000);

      setServerHasNoPrometheus(false);
      setServerPrometheusMessage('');

      // IMPORTANTE: Buscar external_labels PRIMEIRO, DEPOIS sync status
      // Isso garante que o filtro funcione corretamente
      const loadData = async () => {
        console.log('[DEBUG] Servidor alterado, atualizando external_labels e sync status...');

        // PASSO 1: Buscar external_labels (necessário para filtrar campos)
        await fetchExternalLabels(selectedServer);

        // PASSO 2: Buscar sync status (atualiza status nos fields existentes)
        // NÃO chama fetchFields() novamente!
        await fetchSyncStatus(selectedServer);

        console.log('[DEBUG] Todos os dados carregados!');
      };

      loadData();
    }
  }, [selectedServer]);

  // CORREÇÃO: Carregar external labels quando a aba é selecionada
  // Problema identificado: fetchExternalLabels() só era chamado quando servidor mudava
  // Solução: Adicionar listener para mudança de aba
  useEffect(() => {
    if (activeTab === 'external-labels' && selectedServer) {
      console.log('[DEBUG] Aba External Labels selecionada, carregando dados...');
      fetchExternalLabels(selectedServer);
    }
  }, [activeTab, selectedServer]);

  useEffect(() => {
    return () => {
      if (fallbackTimerRef.current) {
        clearTimeout(fallbackTimerRef.current);
      }
    };
  }, []);

  /**
   * FUNÇÃO REMOVIDA - handleCreateField
   *
   * MOTIVO: Campos agora vêm 100% do prometheus.yml (dinâmico via SSH)
   * Para adicionar campos: edite prometheus.yml via página PrometheusConfig
   *
   * CÓDIGO ANTERIOR TINHA:
   * - Hardcode Consul: source_label: `__meta_consul_service_metadata_${values.name}`
   * - Criação manual de campos (não é mais necessário)
   */

  const handleEditField = async (values: any) => {
    if (!editingField) return;

    try {
      // NOTA: Categorias são gerenciadas via modal "Gerenciar Categorias"
      // Não fazemos auto-cadastro aqui. Se usuário digitar categoria nova,
      // ela será salva no campo mas não criará categoria completa (com icon, order, etc).
      // Para criar categoria completa, usar Reference Values > Gerenciar Categorias.

      // Salvar CONFIGURAÇÕES DO CAMPO no JSON principal metadata/fields
      // IMPORTANTE: Salva apenas configurações de UI (display_name, category, show_in_*, etc)
      // NÃO edita o prometheus.yml (para isso, use página PrometheusConfig)

      // SUPORTE A MÚLTIPLAS CATEGORIAS: mode="tags" retorna array
      // Um campo pode participar de múltiplas categorias (será exibido em várias abas em Reference Values)
      const configToSave = {
        display_name: values.display_name,
        description: values.description,
        category: values.category,  // ← Agora aceita string[] (múltiplas categorias)
        field_type: values.field_type,
        order: values.order,
        required: values.required,
        show_in_table: values.show_in_table,
        show_in_dashboard: values.show_in_dashboard,
        show_in_form: values.show_in_form,
        editable: values.editable,
        available_for_registration: values.available_for_registration ?? false,  // NOVO: Auto-cadastro em Reference Values
        // show_in_* para filtros de página (Services, Exporters, Blackbox, futuras...)
        show_in_services: values.show_in_services ?? true,
        show_in_exporters: values.show_in_exporters ?? true,
        show_in_blackbox: values.show_in_blackbox ?? true,
      };

      await axios.patch(`${API_URL}/metadata-fields/${editingField.name}`, configToSave);

      // PASSO 3: Atualizar estado local DIRETAMENTE (não recarrega do Prometheus)
      setFields(prevFields =>
        prevFields.map(f =>
          f.name === editingField.name
            ? { ...f, ...configToSave }
            : f
        )
      );

      message.success(`Configurações do campo '${values.display_name}' atualizadas com sucesso!`);
      setEditModalVisible(false);
      setEditingField(null);
    } catch (error: any) {
      message.error('Erro ao atualizar configurações: ' + (error.response?.data?.detail || error.message));
    }
  };

  /**
   * FUNÇÃO REMOVIDA - Página agora é SOMENTE LEITURA
   * Para remover campos: edite prometheus.yml via PrometheusConfig
   */
  // const handleDeleteField = async (fieldName: string) => {
  //   await deleteFieldResource({ service_id: fieldName } as any);
  // };

  // ============================================================================
  // FASE 2: PREVIEW DE MUDANÇAS
  // ============================================================================
  const handlePreviewChanges = async (fieldName: string) => {
    if (!selectedServer) {
      message.warning('Selecione um servidor primeiro');
      return;
    }

    setLoadingPreview(true);
    setPreviewModalVisible(true);
    setPreviewData(null);

    try {
      const response = await metadataFieldsAPI.previewChanges(fieldName, selectedServer);
      setPreviewData(response.data);
    } catch (error: any) {
      message.error('Erro ao gerar preview: ' + (error.response?.data?.detail || error.message));
      setPreviewModalVisible(false);
    } finally {
      setLoadingPreview(false);
    }
  };

  // ============================================================================
  // FASE 3: SINCRONIZAÇÃO EM LOTE
  // ============================================================================
  const handleBatchSync = async () => {
    if (!selectedServer) {
      message.warning('Selecione um servidor primeiro');
      return;
    }

    // Detectar campos desatualizados, não aplicados e órfãos
    const fieldsToSync = fields.filter(
      (f) => f.sync_status === 'outdated' || f.sync_status === 'missing' || f.sync_status === 'orphan'
    );

    if (fieldsToSync.length === 0) {
      message.info('Todos os campos já estão sincronizados');
      return;
    }

    // Separar campos por tipo de sincronização
    const missingFields = fieldsToSync.filter(f => f.sync_status === 'missing');
    const outdatedFields = fieldsToSync.filter(f => f.sync_status === 'outdated');
    const orphanFields = fieldsToSync.filter(f => f.sync_status === 'orphan');

    // Mensagem explicativa baseada no tipo de sincronização
    let syncDescription = '';
    const descriptions = [];

    if (missingFields.length > 0) {
      descriptions.push(`${missingFields.length} campo(s) serão adicionados ao KV`);
    }
    if (outdatedFields.length > 0) {
      descriptions.push(`${outdatedFields.length} campo(s) serão aplicados no Prometheus`);
    }
    if (orphanFields.length > 0) {
      descriptions.push(`${orphanFields.length} campo(s) órfão(s) serão REMOVIDOS do KV`);
    }

    syncDescription = descriptions.join(', ') + '.';

    // Modal de confirmação
    modal.confirm({
      title: 'Sincronizar Campos',
      content: (
        <div>
          <p>Deseja sincronizar os seguintes {fieldsToSync.length} campo(s)?</p>
          <List
            size="small"
            dataSource={fieldsToSync}
            renderItem={(field) => (
              <List.Item>
                <Tag color={
                  field.sync_status === 'missing' ? 'blue' :
                  field.sync_status === 'orphan' ? 'error' :
                  'orange'
                }>
                  {field.sync_status === 'missing' ? 'Não Aplicado' :
                   field.sync_status === 'orphan' ? 'Órfão' :
                   'Desatualizado'}
                </Tag>
                <strong>{field.display_name}</strong> <code>({field.name})</code>
              </List.Item>
            )}
          />
          <Alert
            message="Processo de Sincronização"
            description={syncDescription}
            type="info"
            showIcon
            style={{ marginTop: 16 }}
          />
        </div>
      ),
      okText: 'Sim, sincronizar',
      cancelText: 'Cancelar',
      width: 700,
      onOk: () => {
        // CRÍTICO: Capturar fieldsToSync ANTES de setTimeout para evitar escopo perdido
        const fieldsToCopy = fieldsToSync;
        // Fechar modal.confirm e abrir modal de progresso após delay
        setTimeout(() => {
          executeBatchSync(fieldsToCopy);
        }, 300); // 300ms para garantir que modal.confirm fechou
      },
    });
  };

  // Função separada para executar sincronização COM DELAYS VISUAIS entre steps
  const executeBatchSync = async (fieldsToSync: MetadataField[]) => {
    try {
      // RESETAR Estados e abrir modal de progresso
      setCurrentStep(0);
      setStepStatus({ 0: 'wait', 1: 'wait', 2: 'wait', 3: 'wait' });
      setStepMessages({ 0: '', 1: '', 2: '', 3: '' });
      setBatchSyncModalVisible(true);

      // Separar campos por tipo de sincronização
      const missingFields = fieldsToSync.filter(f => f.sync_status === 'missing');
      const outdatedFields = fieldsToSync.filter(f => f.sync_status === 'outdated');
      const orphanFields = fieldsToSync.filter(f => f.sync_status === 'orphan');

      const fieldNames = fieldsToSync.map((f) => f.name);

      // STEP 0: Preparação (com delay visual)
      setCurrentStep(0);
      setStepStatus(prev => ({ ...prev, 0: 'process' }));
      setStepMessages(prev => ({ ...prev, 0: `Preparando sincronização de ${fieldNames.length} campo(s)...` }));

      await new Promise(resolve => setTimeout(resolve, 500)); // Delay visual

      setStepStatus(prev => ({ ...prev, 0: 'finish' }));
      const prepMsg = [];
      if (missingFields.length > 0) prepMsg.push(`${missingFields.length} para KV`);
      if (outdatedFields.length > 0) prepMsg.push(`${outdatedFields.length} para Prometheus`);
      if (orphanFields.length > 0) prepMsg.push(`${orphanFields.length} órfãos para remover`);
      setStepMessages(prev => ({ ...prev, 0: `Campos preparados: ${prepMsg.join(', ')} ✓` }));

      await new Promise(resolve => setTimeout(resolve, 300)); // Delay entre steps

      // STEP 1: Sincronizar campos (KV e/ou Prometheus)
      setCurrentStep(1);
      setStepStatus(prev => ({ ...prev, 1: 'process' }));

      let step1Message = '';
      let totalSuccess = 0;
      let needsPrometheusReload = false;

      // SUBSTEP 1A: Adicionar campos "missing" ao KV
      if (missingFields.length > 0) {
        setStepMessages(prev => ({ ...prev, 1: `Adicionando ${missingFields.length} campo(s) ao KV...` }));

        const addToKVResponse = await axios.post(`${API_URL}/metadata-fields/add-to-kv`, {
          field_names: missingFields.map(f => f.name),
          fields_data: missingFields.map(f => ({
            name: f.name,
            display_name: f.display_name,
            source_label: f.source_label,
            field_type: f.field_type,
            description: f.description,
            required: f.required,
            show_in_table: f.show_in_table,
            show_in_dashboard: f.show_in_dashboard,
            show_in_form: f.show_in_form,
            show_in_services: f.show_in_services,
            show_in_exporters: f.show_in_exporters,
            show_in_blackbox: f.show_in_blackbox,
            available_for_registration: f.available_for_registration,
            order: f.order,
            category: f.category,
            editable: f.editable,
          }))
        });

        if (addToKVResponse.data.success) {
          totalSuccess += addToKVResponse.data.total_added;
          step1Message += `${addToKVResponse.data.total_added} campo(s) adicionado(s) ao KV. `;
        }

        await new Promise(resolve => setTimeout(resolve, 300));
      }

      // SUBSTEP 1B: Remover campos "orphan" do KV
      if (orphanFields.length > 0) {
        setStepMessages(prev => ({ ...prev, 1: `Removendo ${orphanFields.length} campo(s) órfão(s) do KV...` }));

        const removeOrphansResponse = await axios.post(`${API_URL}/metadata-fields/remove-orphans`, {
          field_names: orphanFields.map(f => f.name)
        });

        if (removeOrphansResponse.data.success) {
          totalSuccess += removeOrphansResponse.data.removed_count;
          step1Message += `${removeOrphansResponse.data.removed_count} campo(s) órfão(s) removido(s) do KV. `;
        }

        await new Promise(resolve => setTimeout(resolve, 300));
      }

      // SUBSTEP 1C: Aplicar campos "outdated" no Prometheus
      if (outdatedFields.length > 0) {
        setStepMessages(prev => ({ ...prev, 1: `Aplicando ${outdatedFields.length} campo(s) no Prometheus...` }));

        const batchSyncResponse = await metadataFieldsAPI.batchSync({
          field_names: outdatedFields.map(f => f.name),
          server_id: selectedServer,
          dry_run: false
        });

        const { success: backendSuccess, results } = batchSyncResponse.data;
        const successCount = results.filter(r => r.success).length;
        const failCount = results.filter(r => !r.success).length;

        if (failCount > 0) {
          const errors = results.filter(r => !r.success).map(r => r.message).join('; ');
          step1Message += `ERRO: ${errors}`;
          if (successCount === 0) {
            setStepStatus(prev => ({ ...prev, 1: 'error' }));
            setStepMessages(prev => ({ ...prev, 1: step1Message }));
            message.error('Nenhum campo foi sincronizado no Prometheus. Verifique os erros.');
            return;
          }
        }

        totalSuccess += successCount;
        const totalChanges = results.reduce((sum, r) => sum + r.changes_applied, 0);
        step1Message += `${successCount} campo(s) aplicado(s) no Prometheus (${totalChanges} mudanças).`;
        needsPrometheusReload = successCount > 0;

        await new Promise(resolve => setTimeout(resolve, 300));
      }

      setStepStatus(prev => ({ ...prev, 1: 'finish' }));
      setStepMessages(prev => ({ ...prev, 1: step1Message + ' ✓' }));

      await new Promise(resolve => setTimeout(resolve, 400)); // Delay entre steps

      // STEP 2: Reload Prometheus (apenas se houver campos outdated aplicados)
      setCurrentStep(2);

      if (needsPrometheusReload) {
        setStepStatus(prev => ({ ...prev, 2: 'process' }));
        setStepMessages(prev => ({ ...prev, 2: 'Recarregando Prometheus...' }));

        const hostname = selectedServer.split(':')[0];
        const reloadResponse = await consulAPI.reloadService(hostname, '/etc/prometheus/prometheus.yml');

        const failedServices = reloadResponse.data.services.filter(s => !s.success && s.method !== 'skipped');
        const processedServices = reloadResponse.data.services.filter(s => s.success && s.method !== 'skipped');

        if (failedServices.length > 0) {
          setStepStatus(prev => ({ ...prev, 2: 'error' }));
          const errorMsg = failedServices.map(s => `${s.service}: ${s.error || 'falhou'}`).join(', ');
          setStepMessages(prev => ({ ...prev, 2: `Falha ao recarregar: ${errorMsg}` }));
        } else {
          setStepStatus(prev => ({ ...prev, 2: 'finish' }));
          const processedNames = processedServices.map(s => s.service).join(', ');
          setStepMessages(prev => ({ ...prev, 2: `Serviços recarregados: ${processedNames} ✓` }));
        }

        await new Promise(resolve => setTimeout(resolve, 400)); // Delay entre steps
      } else {
        // Pular STEP 2 se apenas adicionou campos ao KV (não precisa reload)
        setStepStatus(prev => ({ ...prev, 2: 'finish' }));
        setStepMessages(prev => ({ ...prev, 2: 'Reload do Prometheus não necessário (apenas campos adicionados ao KV) ✓' }));

        await new Promise(resolve => setTimeout(resolve, 200));
      }

      // STEP 3: Verificar status final
      setCurrentStep(3);
      setStepStatus(prev => ({ ...prev, 3: 'process' }));
      setStepMessages(prev => ({ ...prev, 3: 'Verificando status de sincronização...' }));

      await fetchSyncStatus(selectedServer);

      setStepStatus(prev => ({ ...prev, 3: 'finish' }));
      setStepMessages(prev => ({ ...prev, 3: `Sincronização concluída! ${fieldNames.length} campo(s) aplicado(s) ✓` }));

    } catch (error: any) {
      console.error('[BATCH-SYNC] Erro:', error);

      // Marcar steps restantes como erro
      const currentStepValue = currentStep;
      for (let i = currentStepValue; i <= 3; i++) {
        setStepStatus(prev => {
          if (prev[i] === 'wait' || prev[i] === 'process') {
            return { ...prev, [i]: 'error' };
          }
          return prev;
        });
        setStepMessages(prev => {
          if (!prev[i] || prev[i].includes('...')) {
            return { ...prev, [i]: 'Não executado devido a erro anterior' };
          }
          return prev;
        });
      }

      message.error('Erro ao sincronizar: ' + (error.response?.data?.detail || error.message));
    }
  };

  // ============================================================================
  // FASE 4: DRAWER DE VISUALIZAÇÃO
  // ============================================================================
  const handleViewField = (field: MetadataField) => {
    setDrawerField(field);
    setDrawerVisible(true);
  };


  const columns: ProColumns<MetadataField>[] = [
    {
      title: 'Ordem',
      dataIndex: 'order',
      width: 70,
      render: (order) => <Badge count={order} style={{ backgroundColor: '#1890ff' }} />,
    },
    {
      title: 'Nome Técnico',
      dataIndex: 'name',
      width: 180,
      render: (name) => <code>{name}</code>,
    },
    {
      title: 'Nome de Exibição',
      dataIndex: 'display_name',
      width: 180,
      render: (text) => <strong>{text}</strong>,
    },
    {
      title: 'Tipo',
      dataIndex: 'field_type',
      width: 100,
      render: (_: unknown, record: MetadataField) => {
        const colors: Record<string, string> = {
          string: 'default',
          number: 'blue',
          select: 'purple',
          text: 'green',
          url: 'orange',
        };
        return <Tag color={colors[record.field_type] || 'default'}>{record.field_type}</Tag>;
      },
    },
    {
      title: 'Categoria',
      dataIndex: 'category',
      width: 120,
      render: (cat) => <Tag>{cat}</Tag>,
    },
    {
      title: 'Auto-Cadastro',
      dataIndex: 'available_for_registration',
      width: 130,
      align: 'center' as const,
      render: (available) =>
        available ? (
          <Tooltip title="Este campo suporta retroalimentação (valores novos são cadastrados automaticamente)">
            <Tag color="green" icon={<CheckCircleOutlined />}>Sim</Tag>
          </Tooltip>
        ) : (
          <Tooltip title="Valores pré-definidos ou campo não suporta auto-cadastro">
            <Tag icon={<MinusCircleOutlined />}>Não</Tag>
          </Tooltip>
        ),
    },
    {
      title: 'Páginas',
      width: 250,
      render: (_, record) => (
        <PageVisibilityPopover record={record} onUpdate={handleFieldUpdate} />
      ),
    },
    {
      title: 'Obrigatório',
      dataIndex: 'required',
      width: 100,
      render: (req) => req ? <Tag color="red">Sim</Tag> : <Tag>Não</Tag>,
    },
    {
      title: 'Visibilidade',
      width: 150,
      render: (_, record) => (
        <Space size={4} wrap>
          {record.show_in_table && <Tag color="blue">Tabela</Tag>}
          {record.show_in_dashboard && <Tag color="green">Dashboard</Tag>}
          {record.show_in_form && <Tag color="orange">Form</Tag>}
          {record.available_for_registration && <Tag color="purple">Auto-Cadastro</Tag>}
          {!record.show_in_table && !record.show_in_dashboard && !record.show_in_form && !record.available_for_registration && (
            <Tag color="default">Nenhuma</Tag>
          )}
        </Space>
      ),
    },
    {
      title: 'Descoberto Em',
      dataIndex: 'discovered_in',
      width: 200,
      render: (_: any, record: MetadataField) => {
        const servers = record.discovered_in || [];
        
        if (!servers || servers.length === 0) {
          return <Tag color="default">N/A</Tag>;
        }

        // Helper: Gerar nome amigável e cor baseado no hostname
        const getDisplayInfo = (hostname: string, site?: Site) => {
          // SEMPRE usar dados do KV se site existir (nome E cor)
          if (site) {
            const displayName = site.name || site.code;
            const color = site.color || 'blue';
            return { displayName, color };
          }
          
          // Fallback: usar apenas primeiros octetos do IP (genérico, sem hardcoding)
          // Se site não foi encontrado no KV, algo está errado na configuração
          const shortName = hostname.split('.').slice(0, 2).join('.');
          return { displayName: shortName, color: 'default' };
        };

        // Buscar nomes de sites com cores
        const siteTags = servers.slice(0, 2).map((hostname: string, idx: number) => {
          const site = config?.sites?.find((s: Site) => s.prometheus_host === hostname);
          const { displayName, color } = getDisplayInfo(hostname, site);
          
          return (
            <Tag key={idx} color={color} style={{ margin: 0 }}>
              {displayName}
            </Tag>
          );
        });

        // Tooltip com hostnames completos
        const tooltipText = servers.map((hostname: string) => {
          const site = config?.sites?.find((s: Site) => s.prometheus_host === hostname);
          const { displayName } = getDisplayInfo(hostname, site);
          return `${displayName} (${hostname})`;
        }).join(', ');

        return (
          <Tooltip title={tooltipText}>
            <Space size={4} wrap>
              {siteTags}
              {servers.length > 2 && (
                <Tag color="default">+{servers.length - 2}</Tag>
              )}
            </Space>
          </Tooltip>
        );
      },
    },
    {
      title: 'Status Prometheus',
      dataIndex: 'sync_status',
      width: 160,
      align: 'center' as const,
      render: (status, record) => {
        if (loadingSyncStatus) {
          return <Tag icon={<SyncOutlined spin />} color="processing">Verificando...</Tag>;
        }

        if (!status) {
          return <Tag color="default">-</Tag>;
        }

        // Detectar se é erro específico de servidor sem Prometheus
        const isNoPrometheus = record.sync_message?.includes('não possui Prometheus');

        const statusConfig = {
          synced: {
            icon: <CheckCircleOutlined />,
            color: 'success',
            text: 'Sincronizado',
          },
          missing: {
            icon: <WarningOutlined />,
            color: 'blue',
            text: 'Não Aplicado',
          },
          orphan: {
            icon: <CloseCircleOutlined />,
            color: 'error',
            text: 'Órfão',
          },
          outdated: {
            icon: <WarningOutlined />,
            color: 'warning',
            text: 'Desatualizado',
          },
          error: {
            icon: isNoPrometheus ? <InfoCircleOutlined /> : <WarningOutlined />,
            color: isNoPrometheus ? 'blue' : 'default',
            text: isNoPrometheus ? 'N/A' : 'Erro',
          },
        };

        const config = statusConfig[status as keyof typeof statusConfig];

        // Validação: se config não existe, retorna tag padrão
        if (!config) {
          return <Tag color="default">-</Tag>;
        }

        return (
          <Tooltip title={record.sync_message || 'Status de sincronização'}>
            <Tag icon={config.icon} color={config.color}>
              {config.text}
            </Tag>
          </Tooltip>
        );
      },
    },
    {
      title: 'Origem',
      dataIndex: 'discovered_in',
      width: 250,
      render: (_: any, record: MetadataField) => {
        const discovered_in = record.discovered_in;
        
        if (!discovered_in || discovered_in.length === 0) {
          return <Tag color="default">-</Tag>;
        }

        // FILTRAR: Remover o servidor atualmente selecionado
        // selectedServer está no formato "172.16.1.26:8500", mas discovered_in tem apenas "172.16.1.26"
        // Extrair apenas o hostname para comparação
        const currentHostname = selectedServer ? selectedServer.split(':')[0] : '';
        const otherServers = discovered_in.filter((hostname: string) => hostname !== currentHostname);

        // Se campo só existe no servidor atual, mostrar "-"
        if (otherServers.length === 0) {
          return <Tag color="default">-</Tag>;
        }

        // Helper: Gerar nome amigável e cor baseado no hostname
        const getDisplayInfo = (hostname: string, site?: Site) => {
          // SEMPRE usar dados do KV se site existir (nome E cor)
          if (site) {
            const displayName = site.name || site.code;
            const color = site.color || 'blue';
            return { displayName, color };
          }
          
          // Fallback: usar apenas primeiros octetos do IP (genérico, sem hardcoding)
          // Se site não foi encontrado no KV, algo está errado na configuração
          const shortName = hostname.split('.').slice(0, 2).join('.');
          return { displayName: shortName, color: 'default' };
        };

        // Buscar site correspondente a cada hostname (EXCLUINDO servidor atual)
        const serverTags = otherServers.map((hostname: string) => {
          const site = config?.sites?.find(
            (s: Site) => s.prometheus_host === hostname
          );

          const { displayName, color } = getDisplayInfo(hostname, site);

          return (
            <Tag 
              key={hostname} 
              color={color}
              style={{ marginBottom: 4 }}
            >
              {displayName}
            </Tag>
          );
        });

        // Tooltip mostra os hostnames completos (exceto o atual)
        const tooltipText = otherServers.map((hostname: string) => {
          const site = config?.sites?.find((s: Site) => s.prometheus_host === hostname);
          const { displayName } = getDisplayInfo(hostname, site);
          return `${displayName} (${hostname})`;
        }).join(', ');

        return (
          <Tooltip title={`Disponível para sincronizar de: ${tooltipText}`}>
            <Space size={4} wrap>
              {serverTags}
            </Space>
          </Tooltip>
        );
      },
    },
    {
      title: 'Ações',
      width: 300,
      fixed: 'right',
      render: (_, record) => (
        <Space size="small">
          <Tooltip title="Visualizar Detalhes (FASE 4)">
            <Button
              type="link"
              size="small"
              icon={<EyeOutlined />}
              onClick={() => handleViewField(record)}
            />
          </Tooltip>
          <Tooltip title="Preview de Mudanças">
            <Button
              type="link"
              size="small"
              icon={<FileTextOutlined />}
              onClick={() => handlePreviewChanges(record.name)}
              disabled={!selectedServer || record.sync_status === 'error'}
            />
          </Tooltip>
          <Tooltip title="Editar Configurações do Campo">
            <Button
              type="link"
              size="small"
              icon={<EditOutlined />}
              onClick={() => {
                setEditingField(record);
                setEditModalVisible(true);
              }}
            />
          </Tooltip>
          {/* Botão REMOVER ÓRFÃO - apenas para campos com status 'orphan' */}
          {record.sync_status === 'orphan' && (
            <Popconfirm
              title="Remover Campo Órfão?"
              description={`O campo "${record.name}" foi removido do Prometheus. Deseja removê-lo do KV também?`}
              onConfirm={() => handleRemoveOrphanField(record.name)}
              okText="Sim, remover"
              cancelText="Cancelar"
              okButtonProps={{ danger: true }}
            >
              <Tooltip title="Remover campo órfão do KV">
                <Button
                  type="link"
                  danger
                  size="small"
                  icon={<DeleteOutlined />}
                >
                  Remover
                </Button>
              </Tooltip>
            </Popconfirm>
          )}
        </Space>
      ),
    },
  ];

  // ============================================================================
  // FUNÇÃO: Renderizar explicação da Naming Strategy
  // ============================================================================
  const renderNamingStrategyExplanation = () => {
    if (!config) return null;

    if (config.naming_strategy === 'option2') {
      return (
        <Alert
          type="info"
          showIcon
          icon={<InfoCircleOutlined />}
          message="Estratégia Ativa: Opção 2 (Nomes diferentes por site)"
          description={
            <div>
              <Paragraph>
                <Text strong>Comportamento:</Text> Serviços em sites diferentes do padrão 
                {config.default_site ? ` (${config.default_site})` : ''} recebem sufixo automático.
              </Paragraph>
              <Paragraph>
                <Text strong>Exemplos:</Text>
                <ul style={{ marginBottom: 0 }}>
                  <li>
                    <Text code>selfnode_exporter</Text> + <Tag color="blue">site padrão</Tag> →{' '}
                    <Text code strong>selfnode_exporter</Text> (sem sufixo, é o default)
                  </li>
                  <li>
                    <Text code>selfnode_exporter</Text> + <Tag color="green">site remoto</Tag> →{' '}
                    <Text code strong>selfnode_exporter_[site]</Text>
                  </li>
                  <li>
                    <Text code>blackbox_exporter</Text> + <Tag color="orange">outro site</Tag> →{' '}
                    <Text code strong>blackbox_exporter_[site]</Text>
                  </li>
                </ul>
              </Paragraph>
            </div>
          }
        />
      );
    } else {
      return (
        <Alert
          type="warning"
          showIcon
          icon={<WarningOutlined />}
          message="Estratégia Ativa: Opção 1 (Mesmo nome + filtros)"
          description={
            <div>
              <Paragraph>
                <Text strong>Comportamento:</Text> Todos os serviços mantêm o mesmo nome, independente do site.
                Filtragem deve ser feita via <Text code>relabel_configs</Text> no Prometheus.
              </Paragraph>
              <Paragraph>
                <Text strong>Exemplo:</Text> Todos os <Text code>selfnode_exporter</Text> têm o mesmo nome,
                use metadata <Text code>site</Text> para distinguir.
              </Paragraph>
            </div>
          }
        />
      );
    }
  };

  return (
    <PageContainer
      title="Gerenciamento de Campos Metadata"
      subTitle="Adicionar, editar e sincronizar campos metadata em todos os servidores"
    >
      {/* Alert de Informações do Servidor - ALTURA FIXA */}
      <div style={{ height: 56, marginBottom: 16, overflow: 'hidden' }}>
        <Alert
          message={
            selectedServer && servers.length > 0 ? (
              <span style={{ display: 'inline-flex', alignItems: 'center', gap: 8, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                <strong>Servidor:</strong>
                <span>{servers.find(s => s.id === selectedServer)?.display_name || 'Carregando...'}</span>
                <Badge
                  status={servers.find(s => s.id === selectedServer)?.type === 'master' ? 'success' : 'processing'}
                  text={servers.find(s => s.id === selectedServer)?.type === 'master' ? 'Master' : 'Slave'}
                />
                <span>•</span>
                <span><strong>{fields.length}</strong> campo(s)</span>
                {serverJustChanged && (
                  <Tag color="success" icon={<CheckCircleOutlined />}>
                    Alterado!
                  </Tag>
                )}
              </span>
            ) : (
              <span>
                <strong>Nenhum servidor selecionado</strong> - Selecione abaixo
              </span>
            )
          }
          type={selectedServer && serverJustChanged ? 'success' : selectedServer ? 'info' : 'warning'}
          showIcon
          style={{
            transition: 'all 0.5s ease',
            ...(serverJustChanged && {
              border: '2px solid #52c41a',
              boxShadow: '0 4px 12px rgba(82, 196, 26, 0.4)',
              backgroundColor: '#f6ffed',
            }),
          }}
        />
      </div>

      {/* Alert de Aviso: Servidor SEM Prometheus */}
      {serverHasNoPrometheus && (
        <Alert
          message="Servidor sem Prometheus"
          description={
            <div>
              <p style={{ marginBottom: 8 }}>
                <strong>⚠️ Este servidor NÃO possui Prometheus instalado</strong>
              </p>
              <p style={{ marginBottom: 8 }}>
                {serverPrometheusMessage || 'O servidor selecionado não possui o arquivo prometheus.yml e não pode ser usado para sincronização de campos metadata.'}
              </p>
              <p style={{ marginBottom: 0, fontSize: 12, color: '#8c8c8c' }}>
                <strong>O que você PODE fazer neste servidor:</strong>
                <br />
                • Visualizar campos metadata configurados (FASE 4 - Drawer)
                <br />
                <strong>O que você NÃO PODE fazer:</strong>
                <br />
                • Preview de mudanças (FASE 2) - desabilitado
                <br />
                • Sincronização de campos (FASE 3) - desabilitado
                <br />
                • Status de sincronização aparecerá como "N/A" (azul)
              </p>
            </div>
          }
          type="warning"
          showIcon
          closable
          style={{ marginBottom: 16 }}
        />
      )}

      {/* Card de Seleção de Servidor e Ações */}
      <Card style={{ marginBottom: 16 }}>
        <Row gutter={[16, 16]} align="middle">
          {/* Seletor de Servidor */}
          <Col xs={24} lg={6}>
            <Space direction="vertical" size={4} style={{ width: '100%' }}>
              <Text strong style={{ fontSize: 13 }}>
                <CloudServerOutlined style={{ marginRight: 4 }} />
                Servidor Prometheus
              </Text>
              <Select
                size="large"
                style={{ width: '100%' }}
                value={selectedServer}
                onChange={setSelectedServer}
                placeholder="Selecione o servidor"
              >
                {servers.map(server => (
                  <Select.Option key={server.id} value={server.id}>
                    <Space>
                      <CloudServerOutlined />
                      <span>{server.display_name}</span>
                      <Tag color={server.type === 'master' ? 'green' : 'blue'} style={{ margin: 0 }}>
                        {server.type === 'master' ? 'Master' : 'Slave'}
                      </Tag>
                    </Space>
                  </Select.Option>
                ))}
              </Select>
            </Space>
          </Col>

          {/* Botões de Gerenciamento de Campos */}
          <Col xs={24} lg={6}>
            <Tooltip title="Sincronizar campos desatualizados em lote">
              <Button
                type="primary"
                size="large"
                block
                icon={<ThunderboltOutlined />}
                onClick={handleBatchSync}
                disabled={
                  !selectedServer ||
                  fields.filter((f) => {
                    const isExternalLabel = Object.keys(externalLabels).includes(f.name);
                    return !isExternalLabel && (f.sync_status === 'outdated' || f.sync_status === 'missing');
                  }).length === 0
                }
                style={{ height: 48 }}
              >
                Sincronizar Campos
                {fields.filter((f) => {
                  const isExternalLabel = Object.keys(externalLabels).includes(f.name);
                  return !isExternalLabel && (f.sync_status === 'outdated' || f.sync_status === 'missing');
                }).length > 0 && (
                  <Badge
                    count={fields.filter((f) => {
                      const isExternalLabel = Object.keys(externalLabels).includes(f.name);
                      return !isExternalLabel && (f.sync_status === 'outdated' || f.sync_status === 'missing');
                    }).length}
                    style={{ marginLeft: 8 }}
                  />
                )}
              </Button>
            </Tooltip>
          </Col>

          <Col xs={24} lg={6}>
            <Tooltip
              title={
                !selectedServer
                  ? "Selecione um servidor primeiro"
                  : "Extrair novos campos do Prometheus via SSH (sem reiniciar backend). Use quando adicionar novos campos no prometheus.yml do servidor selecionado."
              }
            >
              <Button
                size="large"
                block
                icon={<CloudDownloadOutlined spin={loadingForceExtract} />}
                onClick={handleForceExtract}
                disabled={!selectedServer || loadingForceExtract}
                loading={loadingForceExtract}
                style={{ height: 48 }}
              >
                {loadingForceExtract ? 'Extraindo...' : 'Extrair Campos'}
              </Button>
            </Tooltip>
          </Col>

          <Col xs={24} lg={6}>
            <Tooltip title="Atualizar status de sincronização (apenas verifica, não extrai novos campos)">
              <Button
                size="large"
                block
                icon={<SyncOutlined spin={loadingSyncStatus} />}
                onClick={() => selectedServer && fetchSyncStatus(selectedServer)}
                disabled={!selectedServer || loadingSyncStatus}
                style={{ height: 48 }}
              >
                {loadingSyncStatus ? 'Verificando...' : 'Verificar Sincronização'}
              </Button>
            </Tooltip>
          </Col>
        </Row>
      </Card>

      {/* ABAS: Campos de Meta vs External Labels */}
      <ProCard>
        <Tabs
          activeKey={activeTab}
          onChange={setActiveTab}
          items={[
            {
              key: 'meta-fields',
              label: (
                <span>
                  <FileTextOutlined /> Campos de Meta (Relabel Configs)
                </span>
              ),
              children: (
                <ProTable<MetadataField>
          columns={columns}
          dataSource={fields.filter((field) => {
            // FILTRAR: Remover external_labels desta aba
            // External labels são campos globais do servidor (global.external_labels)
            // São extraídos do prometheus.yml via SSH e armazenados em externalLabels state
            const isExternalLabel = Object.keys(externalLabels).includes(field.name);

            // Retornar FALSE se for external_label (remove da lista de campos de meta)
            return !isExternalLabel;
          })}
          rowKey="name"
          loading={loading || loadingSyncStatus || loadingExternalLabels}
          search={false}
          options={{
            reload: () => {
              fetchFields();
              if (selectedServer) {
                fetchSyncStatus(selectedServer);
              }
            },
          }}
          pagination={{
            defaultPageSize: 30,
            showSizeChanger: true,
            pageSizeOptions: ['10', '20', '30', '50', '100'],
            showTotal: (total) => `Total: ${total} campos`,
          }}
          scroll={{ x: 1600 }}
          toolBarRender={() => {
            const toolbarItems = [] as React.ReactNode[];

            if (fallbackWarningVisible && fallbackWarningMessage) {
              toolbarItems.push(
                <Tooltip key="fallback-info" title={fallbackWarningMessage}>
                  <Alert
                    type="warning"
                    showIcon
                    message="Leitura alternativa aplicada"
                    style={{
                      display: 'inline-flex',
                      alignItems: 'center',
                      height: 32,
                      padding: '0 12px',
                      margin: 0,
                      whiteSpace: 'nowrap',
                    }}
                  />
                </Tooltip>
              );
            }

            return toolbarItems;
          }}
        />
              ),
            },
            {
              key: 'external-labels',
              label: (
                <span>
                  <CloudServerOutlined /> External Labels (Global do Servidor)
                </span>
              ),
              children: (
                <Card>
                  <Alert
                    type="info"
                    showIcon
                    message="External Labels - Identificam o Servidor Prometheus"
                    description={
                      <div>
                        <p><strong>O que são:</strong> Labels globais configurados no <code>global.external_labels</code> do prometheus.yml</p>
                        <p><strong>Aplicados por:</strong> Próprio Prometheus automaticamente a TODAS as métricas coletadas</p>
                        <p><strong>Finalidade:</strong> Identificar qual servidor Prometheus coletou a métrica (ex: site=palmas, datacenter=genesis-dtc)</p>
                        <p><strong>IMPORTANTE:</strong> NÃO são campos para cadastrar em serviços! São apenas para VISUALIZAÇÃO.</p>
                      </div>
                    }
                    style={{ marginBottom: 16 }}
                  />

                  {loadingExternalLabels ? (
                    <div style={{ textAlign: 'center', padding: 40 }}>
                      <LoadingOutlined style={{ fontSize: 24 }} spin />
                      <p>Carregando external labels...</p>
                    </div>
                  ) : Object.keys(externalLabels).length === 0 ? (
                    <Alert
                      type="warning"
                      message="Nenhum External Label Configurado"
                      description={
                        selectedServer
                          ? "Este servidor não possui external_labels configurados no prometheus.yml"
                          : "Selecione um servidor acima para ver os external labels"
                      }
                    />
                  ) : (
                    <Descriptions
                      bordered
                      column={1}
                      size="small"
                      title={`External Labels do Servidor (${servers.find(s => s.id === selectedServer)?.display_name || 'Desconhecido'})`}
                    >
                      {Object.entries(externalLabels).map(([key, value]) => (
                        <Descriptions.Item key={key} label={<Text strong>{key}</Text>}>
                          <Tag color="blue">{value}</Tag>
                        </Descriptions.Item>
                      ))}
                    </Descriptions>
                  )}
                </Card>
              ),
            },
            {
              key: 'external-labels-all',
              label: (
                <span>
                  <ClusterOutlined /> External Labels (Todos Servidores)
                </span>
              ),
              children: (
                <div style={{ padding: '16px 0' }}>
                  {loadingServers ? (
                    <Skeleton active paragraph={{ rows: 6 }} />
                  ) : !prometheusServers || prometheusServers.length === 0 ? (
                    <Alert
                      type="warning"
                      showIcon
                      icon={<InfoCircleOutlined />}
                      message="Dados não disponíveis - Sincronização necessária"
                      description={
                        <div>
                          <Paragraph>
                            <Text strong>Os external_labels ainda não foram extraídos do Prometheus.</Text>
                          </Paragraph>
                          <Paragraph>
                            Para visualizar os external_labels dos servidores:
                          </Paragraph>
                          <ol style={{ marginBottom: 0 }}>
                            <li>Clique no botão <Text strong>"Sincronizar com Prometheus"</Text> acima</li>
                            <li>Aguarde a extração dos campos via SSH</li>
                            <li>Os dados aparecerão automaticamente após conclusão</li>
                          </ol>
                        </div>
                      }
                    />
                  ) : (
                    <>
                      <Alert
                        type="info"
                        showIcon
                        message="O que são External Labels?"
                        description={
                          <div>
                            <p><strong>External labels</strong> são labels globais configurados em <code>global.external_labels</code> do prometheus.yml</p>
                            <p>São aplicados automaticamente a <strong>TODAS as métricas coletadas</strong> pelo Prometheus para identificar qual servidor/site coletou a métrica</p>
                            <p><strong>IMPORTANTE:</strong> Estes NÃO são campos para cadastrar em serviços! São globais do servidor.</p>
                          </div>
                        }
                        style={{ marginBottom: 16 }}
                      />

                      <Space direction="vertical" size="middle" style={{ width: '100%' }}>
                        {prometheusServers.map((server, index) => (
                          <ProCard
                            key={index}
                            type="inner"
                            title={
                              <Space>
                                <Badge status={server.status === 'success' ? 'success' : 'error'} />
                                <Text strong>{server.hostname}:{server.port}</Text>
                              </Space>
                            }
                          >
                            {server.status === 'error' ? (
                              <Alert
                                type="error"
                                showIcon
                                message="Erro ao buscar external_labels"
                                description={server.error}
                              />
                            ) : Object.keys(server.external_labels).length === 0 ? (
                              <Alert
                                type="warning"
                                message="Nenhum external_label configurado neste servidor"
                              />
                            ) : (
                              <ProDescriptions
                                column={2}
                                size="small"
                                bordered
                              >
                                {Object.entries(server.external_labels).map(([key, value]) => (
                                  <ProDescriptions.Item
                                    key={key}
                                    label={<Text strong>{key}</Text>}
                                  >
                                    <Tag color="blue">{value}</Tag>
                                  </ProDescriptions.Item>
                                ))}
                              </ProDescriptions>
                            )}
                          </ProCard>
                        ))}
                      </Space>
                    </>
                  )}
                </div>
              ),
            },
            {
              key: 'manage-sites',
              label: (
                <span>
                  <GlobalOutlined /> Gerenciar Sites
                </span>
              ),
              children: config && config.sites ? (
                <div style={{ padding: '16px 0' }}>
                  {/* CARD: Configuração Global de Naming Strategy */}
                  <ProCard
                    title="Configuração Global de Naming Strategy"
                    bordered
                    headerBordered
                    style={{ marginBottom: 16 }}
                    extra={
                      <Badge
                        status={config.suffix_enabled ? 'processing' : 'default'}
                        text={config.suffix_enabled ? 'Sufixos Ativos' : 'Sufixos Desabilitados'}
                      />
                    }
                  >
                    <Alert
                      type="info"
                      showIcon
                      message="Configuração Global"
                      description="Estas configurações afetam a nomenclatura de serviços em TODOS os sites. Altere apenas se souber o impacto."
                      style={{ marginBottom: 16 }}
                    />
                    <Form
                      layout="vertical"
                      initialValues={{
                        naming_strategy: config.naming_strategy,
                        suffix_enabled: config.suffix_enabled,
                      }}
                      onFinish={async (values) => {
                        try {
                          const response = await axios.patch(
                            `${API_URL}/metadata-fields/config/naming`,
                            {
                              naming_strategy: values.naming_strategy,
                              suffix_enabled: values.suffix_enabled,
                            }
                          );
                          if (response.data.success) {
                            message.success('Naming Strategy atualizada com sucesso!');
                            await loadConfig(); // Recarregar configuração
                          } else {
                            throw new Error(response.data.message || 'Erro ao atualizar');
                          }
                        } catch (error: any) {
                          console.error('Erro ao atualizar naming config:', error);
                          message.error(`Erro: ${error.response?.data?.detail || error.message}`);
                        }
                      }}
                    >
                      <Row gutter={16}>
                        <Col span={12}>
                          <Form.Item
                            name="naming_strategy"
                            label="Estratégia de Nomenclatura"
                            rules={[{ required: true, message: 'Selecione uma estratégia' }]}
                          >
                            <Select>
                              <Select.Option value="option1">
                                Opção 1 - Mesmo nome + filtros Prometheus
                              </Select.Option>
                              <Select.Option value="option2">
                                Opção 2 - Nomes diferentes por site (com sufixo)
                              </Select.Option>
                            </Select>
                          </Form.Item>
                        </Col>
                        <Col span={12}>
                          <Form.Item
                            name="suffix_enabled"
                            label="Sufixos Automáticos"
                            valuePropName="checked"
                          >
                            <Switch
                              checkedChildren="Habilitado"
                              unCheckedChildren="Desabilitado"
                            />
                          </Form.Item>
                        </Col>
                      </Row>
                      <Form.Item>
                        <Button type="primary" htmlType="submit">
                          Salvar Configuração Global
                        </Button>
                      </Form.Item>
                    </Form>
                  </ProCard>

                  <div style={{ marginBottom: 16, display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
                    <Button
                      type="primary"
                      icon={<SyncOutlined />}
                      onClick={handleSyncSites}
                      loading={loadingServers}
                      title="Sincroniza sites automaticamente extraindo external_labels do Prometheus"
                    >
                      Sincronizar Sites
                    </Button>
                  </div>
                  <ProTable<Site>
                    actionRef={tableRef}
                    columns={[
                      applyResizableWidth({
                        title: 'Código',
                        dataIndex: 'code',
                        width: 100,
                        render: (_: any, record: Site) => (
                          <Tag color={record.color || 'default'}>{record.code.toUpperCase()}</Tag>
                        ),
                      }, 'code'),
                      applyResizableWidth({
                        title: 'Nome',
                        dataIndex: 'name',
                        width: 200,
                        ellipsis: true,
                      }, 'name'),
                      applyResizableWidth({
                        title: 'Site Padrão',
                        dataIndex: 'is_default',
                        width: 150,
                        render: (_: any, record: Site) => (
                          record.is_default ? (
                            <Badge status="success" text="Sim (sem sufixo)" />
                          ) : (
                            <Badge status="default" text="Não" />
                          )
                        ),
                      }, 'is_default'),
                      applyResizableWidth({
                        title: 'Cor do Badge',
                        dataIndex: 'color',
                        width: 120,
                        render: (_: any, record: Site) => (
                          <Tag color={record.color || 'default'}>
                            {record.color || 'default'}
                          </Tag>
                        ),
                      }, 'color'),
                      applyResizableWidth({
                        title: 'Prometheus',
                        dataIndex: 'prometheus_host',
                        width: 200,
                        ellipsis: true,
                        render: (_: any, record: Site) => {
                          if (!record.prometheus_host) {
                            return <Text type="secondary">-</Text>;
                          }
                          const port = record.prometheus_port || 9090;
                          return (
                            <Text code style={{ fontSize: '12px' }}>
                              {record.prometheus_host}:{port}
                            </Text>
                          );
                        },
                      }, 'prometheus_host'),
                      applyResizableWidth({
                        title: 'Site',
                        dataIndex: 'site',
                        width: 120,
                        render: (_: any, record: Site) => {
                          const labels = getExternalLabelsForHost(record.prometheus_host);
                          return labels.site ? <Tag color="blue">{labels.site}</Tag> : <Text type="secondary">-</Text>;
                        },
                      }, 'site'),
                      applyResizableWidth({
                        title: 'Datacenter',
                        dataIndex: 'datacenter',
                        width: 140,
                        ellipsis: true,
                        render: (_: any, record: Site) => {
                          const labels = getExternalLabelsForHost(record.prometheus_host);
                          return labels.datacenter ? <Tag color="green">{labels.datacenter}</Tag> : <Text type="secondary">-</Text>;
                        },
                      }, 'datacenter'),
                      applyResizableWidth({
                        title: 'Cluster',
                        dataIndex: 'cluster',
                        width: 140,
                        ellipsis: true,
                        render: (_: any, record: Site) => {
                          const labels = getExternalLabelsForHost(record.prometheus_host);
                          return labels.cluster ? <Tag color="purple">{labels.cluster}</Tag> : <Text type="secondary">-</Text>;
                        },
                      }, 'cluster'),
                      applyResizableWidth({
                        title: 'Environment',
                        dataIndex: 'environment',
                        width: 130,
                        render: (_: any, record: Site) => {
                          const labels = getExternalLabelsForHost(record.prometheus_host);
                          return labels.environment ? <Tag color="orange">{labels.environment}</Tag> : <Text type="secondary">-</Text>;
                        },
                      }, 'environment'),
                      applyResizableWidth({
                        title: 'Ações',
                        width: 80,
                        valueType: 'option',
                        render: (_: any, record: Site) => [
                          <Button
                            key="edit"
                            type="link"
                            icon={<EditOutlined />}
                            onClick={() => {
                              setEditingSite(record);
                              setEditModalOpen(true);
                            }}
                          >
                            Editar
                          </Button>,
                        ],
                      }, 'actions'),
                    ]}
                    dataSource={config.sites}
                    rowKey="code"
                    search={false}
                    pagination={false}
                    toolBarRender={false}
                    scroll={{ x: 1600 }}
                    components={{
                      header: {
                        cell: ResizableTitle,
                      },
                    }}
                  />
                  <Alert
                    type="info"
                    showIcon
                    message="Informações Importantes"
                    description={
                      <div>
                        <p>• Adicione ou remova sites conforme sua infraestrutura cresce</p>
                        <p>• O site marcado como padrão não receberá sufixo nos nomes de serviço</p>
                        <p>• <strong>Colunas External Labels:</strong> As colunas Site, Datacenter, Cluster e Environment mostram os external_labels configurados no prometheus.yml de cada servidor</p>
                        <p>• <strong>Atualização Automática:</strong> Os external_labels são buscados automaticamente ao carregar a página</p>
                      </div>
                    }
                    style={{ marginTop: 16 }}
                  />

                  {/* CARD: Naming Strategy Multi-Site */}
                  {config && (
                    <ProCard
                      title="Naming Strategy Multi-Site"
                      bordered
                      headerBordered
                      style={{ marginTop: 16 }}
                      extra={
                        <Badge
                          status={config.suffix_enabled ? 'processing' : 'default'}
                          text={config.suffix_enabled ? 'Ativo' : 'Desativado'}
                        />
                      }
                    >
                      <Space direction="vertical" size="large" style={{ width: '100%' }}>
                        <ProDescriptions
                          column={2}
                          bordered
                          size="small"
                        >
                          <ProDescriptions.Item label="Estratégia" span={1}>
                            <Tag color={config.naming_strategy === 'option2' ? 'blue' : 'orange'}>
                              {config.naming_strategy === 'option2' ? 'Opção 2 - Nomes diferentes' : 'Opção 1 - Mesmo nome + filtros'}
                            </Tag>
                          </ProDescriptions.Item>
                          <ProDescriptions.Item label="Sufixo Automático" span={1}>
                            <Badge
                              status={config.suffix_enabled ? 'success' : 'default'}
                              text={config.suffix_enabled ? 'Habilitado' : 'Desabilitado'}
                            />
                          </ProDescriptions.Item>
                          <ProDescriptions.Item label="Site Padrão (sem sufixo)" span={2}>
                            {config.default_site ? (
                              <>
                                <Tag color="blue">{config.default_site.toUpperCase()}</Tag>
                                <Text type="secondary"> (serviços neste site não recebem sufixo)</Text>
                              </>
                            ) : (
                              <Text type="secondary">Nenhum site marcado como padrão</Text>
                            )}
                          </ProDescriptions.Item>
                        </ProDescriptions>

                        <Divider orientation="left">Como Funciona</Divider>
                        {renderNamingStrategyExplanation()}

                        <Divider orientation="left">Configuração no Backend</Divider>
                        <Alert
                          type="info"
                          showIcon
                          message="Arquivo de Configuração"
                          description={
                            <div>
                              <Paragraph>
                                Estas configurações são carregadas do arquivo <Text code>backend/.env</Text>:
                              </Paragraph>
                              <pre style={{
                                background: '#f5f5f5',
                                padding: '12px',
                                borderRadius: '4px',
                                fontSize: '12px',
                              }}>
{`NAMING_STRATEGY=${config.naming_strategy}
SITE_SUFFIX_ENABLED=${config.suffix_enabled}
DEFAULT_SITE=${config.default_site || 'null (nenhum site padrão)'}`}
                              </pre>
                              <Paragraph type="secondary" style={{ marginBottom: 0 }}>
                                Para alterar, edite o arquivo .env e reinicie o backend.
                              </Paragraph>
                            </div>
                          }
                        />
                      </Space>
                    </ProCard>
                  )}

                  {/* CARD: Informações Adicionais - Páginas Afetadas */}
                  {config && (
                    <ProCard
                      title="Páginas Afetadas"
                      bordered
                      headerBordered
                      style={{ marginTop: 16 }}
                    >
                      <Paragraph>
                        A naming strategy afeta automaticamente as seguintes páginas:
                      </Paragraph>
                      <ul>
                        <li><Text strong>Services:</Text> Criação e atualização de serviços</li>
                        <li><Text strong>Exporters:</Text> Registro de exporters no Consul</li>
                        <li><Text strong>Blackbox Targets:</Text> Criação de alvos de monitoramento</li>
                      </ul>
                      <Alert
                        type="success"
                        showIcon
                        message="Sincronização Automática"
                        description="O frontend carrega estas configurações automaticamente ao iniciar, garantindo que a lógica de nomenclatura seja consistente entre backend e frontend."
                      />
                    </ProCard>
                  )}
                </div>
              ) : null,
            },
          ]}
        />
      </ProCard>

      {/* Modal Criar Campo REMOVIDO - Campos vêm 100% do prometheus.yml */}
      {/* Para adicionar campos: edite prometheus.yml via página PrometheusConfig */}

      {/* Modal Editar Campo - REORGANIZADO COM COLLAPSE */}
      <ModalForm
        key={editingField?.name || 'edit-field-modal'}
        title={
          <Space>
            <EditOutlined />
            {`Editar Configurações: ${editingField?.display_name || editingField?.name}`}
          </Space>
        }
        open={editModalVisible}
        onOpenChange={(visible) => {
          setEditModalVisible(visible);
          if (!visible) setEditingField(null);
        }}
        onFinish={handleEditField}
        initialValues={editingField || {}}
        modalProps={{
          width: 720,
          destroyOnHidden: true,
        }}
      >
        {/* Metadados Somente-Leitura */}
        <Alert
          message={<><strong>Campo Metadata:</strong> {editingField?.name}</>}
          description={
            <div style={{ fontSize: 12, marginTop: 4 }}>
              <div><strong>Source Label:</strong> <code>{editingField?.source_label || 'N/A'}</code></div>
              <div style={{ marginTop: 4, color: '#666' }}>
                ℹ️ Estes campos vêm do prometheus.yml e não podem ser alterados aqui.
                Use a página "Configuração Prometheus" para editar o prometheus.yml.
              </div>
            </div>
          }
          type="info"
          showIcon
          style={{ marginBottom: 24 }}
        />

        {/* Collapse para organizar campos - USANDO NOVA API 'items' */}
        <Collapse
          defaultActiveKey={['basic', 'visibility-pages']}
          style={{ marginBottom: 16 }}
          items={[
            // PAINEL 1: Informações Básicas
            {
              key: 'basic',
              label: '📝 Informações Básicas',
              children: (
                <>
                  {/* LINHA 1: Nome de Exibição + Categoria */}
                  <Row gutter={16}>
                    <Col span={12}>
                      <ProFormText
                        name="display_name"
                        label="Nome de Exibição"
                        rules={[{ required: true, message: 'Nome de exibição é obrigatório' }]}
                        placeholder="Ex: Sistema Operacional, Empresa..."
                        tooltip="Nome amigável exibido nas tabelas e formulários"
                      />
                    </Col>
                    <Col span={12}>
                      <ProFormSelect
                        name="category"
                        label="Categoria"
                        rules={[{ required: true, message: 'Informe ao menos uma categoria' }]}
                        placeholder="Selecione ou digite novas categorias..."
                        tooltip="Selecione categorias existentes ou digite novas. Um campo pode pertencer a múltiplas categorias. Categorias são gerenciadas em Reference Values > Gerenciar Categorias."
                        fieldProps={{
                          loading: loadingCategories,
                          showSearch: true,
                          mode: 'tags', // Permite criar nova categoria digitando e selecionar múltiplas
                          filterOption: (input, option) =>
                            (option?.label ?? '').toLowerCase().includes(input.toLowerCase()),
                        }}
                        options={categories.map((cat) => ({
                          label: `${cat.icon || ''} ${cat.label}`.trim(),
                          value: cat.key,
                        }))}
                      />
                    </Col>
                  </Row>

                  {/* LINHA 2: Descrição (campo grande, ocupa linha inteira) */}
                  <ProFormTextArea
                    name="description"
                    label="Descrição"
                    rows={2}
                    placeholder="Descreva o propósito deste campo..."
                    tooltip="Descrição que aparecerá em tooltips e documentação"
                  />
                </>
              ),
            },
            // PAINEL 2: Configurações de Campo
            {
              key: 'config',
              label: '⚙️ Configurações de Campo',
              children: (
                <>
                  {/* LINHA 1: Tipo do Campo + Ordem de Exibição */}
                  <Row gutter={16}>
                    <Col span={16}>
                      <ProFormSelect
                        name="field_type"
                        label="Tipo do Campo"
                        options={[
                          { label: 'Texto (string)', value: 'string' },
                          { label: 'Número (number)', value: 'number' },
                          { label: 'Seleção (select)', value: 'select' },
                          { label: 'Texto Longo (text)', value: 'text' },
                          { label: 'URL (url)', value: 'url' },
                        ]}
                        rules={[{ required: true, message: 'Selecione o tipo do campo' }]}
                        tooltip="Define o tipo de entrada e validação do campo"
                      />
                    </Col>
                    <Col span={8}>
                      <ProFormDigit
                        name="order"
                        label="Ordem de Exibição"
                        min={1}
                        max={999}
                        fieldProps={{ precision: 0 }}
                        tooltip="Ordem em que o campo aparece (menor = primeiro)"
                      />
                    </Col>
                  </Row>

                  {/* LINHA 2: Switches Obrigatório + Editável + Auto-Cadastro */}
                  <Space size="large" style={{ width: '100%', justifyContent: 'space-between' }}>
                    <ProFormSwitch
                      name="required"
                      label="Obrigatório"
                      tooltip="Campo deve ser preenchido obrigatoriamente"
                    />
                    <ProFormSwitch
                      name="editable"
                      label="Editável"
                      tooltip="Usuário pode editar o valor após criação"
                    />
                    <ProFormSwitch
                      name="available_for_registration"
                      label={
                        <Space>
                          Auto-Cadastro
                          <Tooltip
                            title={
                              <div style={{ maxWidth: 350 }}>
                                <div style={{ fontWeight: 'bold', marginBottom: 8 }}>ℹ️ O que é Auto-Cadastro?</div>
                                <div style={{ marginBottom: 8 }}>
                                  Quando <strong>HABILITADO</strong>:
                                  <ul style={{ paddingLeft: 20, marginTop: 4 }}>
                                    <li>Campo aparece na página <strong>Reference Values</strong></li>
                                    <li>Novos valores são <strong>cadastrados automaticamente</strong> ao salvar formulários</li>
                                    <li>Usuário pode gerenciar valores existentes (editar, deletar, renomear)</li>
                                    <li>Ideal para campos dinâmicos (ex: empresa, cidade, provedor)</li>
                                  </ul>
                                </div>
                                <div>
                                  Quando <strong>DESABILITADO</strong>:
                                  <ul style={{ paddingLeft: 20, marginTop: 4 }}>
                                    <li>Campo <strong>NÃO</strong> aparece em Reference Values</li>
                                    <li>Valores devem ser pré-definidos em <strong>"Opções"</strong></li>
                                    <li>Usuário escolhe apenas entre valores fixos (dropdown)</li>
                                    <li>Ideal para campos com valores controlados (ex: env: prod/dev/staging)</li>
                                  </ul>
                                </div>
                              </div>
                            }
                            placement="right"
                          >
                            <InfoCircleOutlined style={{ color: '#1890ff', cursor: 'help' }} />
                          </Tooltip>
                        </Space>
                      }
                      tooltip="Clique no ℹ️ para mais informações"
                      fieldProps={{
                        onChange: (checked: boolean) => {
                          Modal.info({
                            title: checked ? '✅ Auto-Cadastro HABILITADO' : '⛔ Auto-Cadastro DESABILITADO',
                            width: 500,
                            content: (
                              <div>
                                <div style={{ marginBottom: 16, fontSize: 16 }}>
                                  {checked ? (
                                    <div>
                                      <div style={{ marginBottom: 12 }}>
                                        <strong>O que vai acontecer:</strong>
                                      </div>
                                      <ul style={{ paddingLeft: 20 }}>
                                        <li>Campo <strong>aparecerá</strong> na página Reference Values</li>
                                        <li>Novos valores serão <strong>cadastrados automaticamente</strong> ao salvar formulários</li>
                                        <li>Usuários poderão gerenciar valores (editar, deletar, renomear)</li>
                                      </ul>
                                      <div style={{ marginTop: 12, padding: 12, background: '#e6f7ff', borderLeft: '3px solid #1890ff' }}>
                                        <strong>💡 Ideal para:</strong> Campos dinâmicos como empresa, cidade, provedor
                                      </div>
                                    </div>
                                  ) : (
                                    <div>
                                      <div style={{ marginBottom: 12 }}>
                                        <strong>O que vai acontecer:</strong>
                                      </div>
                                      <ul style={{ paddingLeft: 20 }}>
                                        <li>Campo <strong>NÃO aparecerá</strong> em Reference Values</li>
                                        <li>Valores devem ser pré-definidos em <strong>"Opções"</strong></li>
                                        <li>Usuários escolhem apenas entre valores fixos (dropdown)</li>
                                      </ul>
                                      <div style={{ marginTop: 12, padding: 12, background: '#fff7e6', borderLeft: '3px solid #faad14' }}>
                                        <strong>💡 Ideal para:</strong> Campos controlados como env (prod/dev/staging)
                                      </div>
                                    </div>
                                  )}
                                </div>
                              </div>
                            ),
                            okText: 'Entendi',
                          });
                        },
                      }}
                    />
                  </Space>
                </>
              ),
            },
            // PAINEL 3: Visibilidade Geral
            {
              key: 'visibility-general',
              label: '👁️ Visibilidade Geral (UI)',
              children: (
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 16 }}>
                  <ProFormSwitch
                    name="show_in_table"
                    label="Tabelas"
                    tooltip="Exibir como coluna em tabelas"
                  />
                  <ProFormSwitch
                    name="show_in_dashboard"
                    label="Dashboard"
                    tooltip="Exibir em dashboards e resumos"
                  />
                  <ProFormSwitch
                    name="show_in_form"
                    label="Formulários"
                    tooltip="Exibir em formulários de cadastro/edição"
                  />
                </div>
              ),
            },
            // PAINEL 4: Visibilidade por Página (CRÍTICO)
            {
              key: 'visibility-pages',
              label: '🎯 Visibilidade por Página (Filtros)',
              children: (
                <>
                  <Alert
                    message="Controle de Contexto"
                    description="Configure em quais páginas este campo deve aparecer nos formulários. Ex: 'sistema_operacional' não faz sentido em monitoramento HTTP, então pode desmarcar 'Blackbox'."
                    type="info"
                    showIcon
                    style={{ marginBottom: 16 }}
                  />
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 16 }}>
                    <ProFormSwitch
                      name="show_in_services"
                      label={<Space><Tag color="blue">Services</Tag></Space>}
                      tooltip="Campo aparecerá nos formulários de serviços"
                    />
                    <ProFormSwitch
                      name="show_in_exporters"
                      label={<Space><Tag color="green">Exporters</Tag></Space>}
                      tooltip="Campo aparecerá nos formulários de exporters"
                    />
                    <ProFormSwitch
                      name="show_in_blackbox"
                      label={<Space><Tag color="orange">Blackbox</Tag></Space>}
                      tooltip="Campo aparecerá nos formulários de targets blackbox"
                    />
                  </div>
                </>
              ),
            },
          ]}
        />
      </ModalForm>

      {/* FASE 2: Modal de Preview de Mudanças */}
      <Modal
        title="Preview de Mudanças"
        open={previewModalVisible}
        onCancel={() => setPreviewModalVisible(false)}
        width={800}
        footer={[
          <Button key="cancel" onClick={() => setPreviewModalVisible(false)}>
            Fechar
          </Button>,
        ]}
      >
        {loadingPreview ? (
          <div style={{ textAlign: 'center', padding: '40px 0' }}>
            <SyncOutlined spin style={{ fontSize: 32, color: '#1890ff' }} />
            <p style={{ marginTop: 16 }}>Gerando preview...</p>
          </div>
        ) : previewData ? (
          <div>
            <Alert
              message={previewData.will_create ? '🆕 Campo será CRIADO no prometheus.yml' : '✏️ Campo será ATUALIZADO no prometheus.yml'}
              description={
                previewData.will_create
                  ? 'O campo não existe no arquivo prometheus.yml deste servidor. Ao sincronizar, uma nova entrada relabel_config será adicionada.'
                  : 'O campo já existe no prometheus.yml deste servidor, mas pode estar desatualizado. O preview abaixo mostra as diferenças entre a configuração atual e a configuração esperada do metadata_fields.json. Sincronizar irá aplicar essas mudanças.'
              }
              type={previewData.will_create ? 'info' : 'warning'}
              showIcon
              style={{ marginBottom: 16 }}
            />

            <Descriptions title="Informações" bordered size="small" column={2}>
              <Descriptions.Item label="Campo">{previewData.field_name}</Descriptions.Item>
              <Descriptions.Item label="Ação">
                {previewData.will_create ? 'Criar' : 'Atualizar'}
              </Descriptions.Item>
              <Descriptions.Item label="Jobs Afetados" span={2}>
                <Space wrap>
                  {previewData.affected_jobs.map((job: string) => (
                    <Tag key={job}>{job}</Tag>
                  ))}
                </Space>
              </Descriptions.Item>
            </Descriptions>

            <Divider>Diferenças (Diff)</Divider>
            <Card size="small">
              <pre
                style={{
                  backgroundColor: '#f5f5f5',
                  padding: 12,
                  borderRadius: 4,
                  overflow: 'auto',
                  maxHeight: 400,
                  fontSize: 12,
                  fontFamily: 'monospace',
                }}
              >
                {previewData.diff_text}
              </pre>
            </Card>

            <Alert
              message="ℹ️ Sobre a Comparação"
              description={
                <div>
                  <p style={{ marginBottom: 4 }}>
                    <strong>Fonte de Verdade Única:</strong> O arquivo <code>metadata_fields.json</code> é a configuração mestre.
                  </p>
                  <p style={{ marginBottom: 4 }}>
                    <strong>Comparação:</strong> O preview compara o prometheus.yml do <strong>servidor atual selecionado</strong> com a configuração esperada no metadata_fields.json.
                  </p>
                  <p style={{ marginBottom: 0 }}>
                    <strong>Jobs Afetados:</strong> A lista mostra TODOS os jobs (scrape_configs) encontrados neste servidor. Cada servidor pode ter jobs diferentes. A sincronização irá aplicar o campo em todos os jobs deste servidor.
                  </p>
                </div>
              }
              type="info"
              showIcon
              style={{ marginTop: 16 }}
            />
          </div>
        ) : null}
      </Modal>

      {/* FASE 3: Modal de Sincronização em Lote - COM ETAPAS */}
      <Modal
        open={batchSyncModalVisible}
        title="Sincronizando Campos no Prometheus"
        footer={null}
        closable={false}
        maskClosable={false}
        width={700}
      >
        <Steps
          current={currentStep}
          direction="vertical"
          items={[
            {
              title: 'Preparação',
              status: stepStatus[0],
              description: stepMessages[0],
              icon: stepStatus[0] === 'process' ? <LoadingOutlined /> : undefined,
            },
            {
              title: 'Sincronização no Prometheus',
              status: stepStatus[1],
              description: stepMessages[1],
              icon: stepStatus[1] === 'process' ? <LoadingOutlined /> : undefined,
            },
            {
              title: 'Reload do Prometheus',
              status: stepStatus[2],
              description: stepMessages[2],
              icon: stepStatus[2] === 'process' ? <SyncOutlined spin /> : undefined,
            },
            {
              title: 'Verificação Final',
              status: stepStatus[3],
              description: stepMessages[3],
              icon: stepStatus[3] === 'process' ? <LoadingOutlined /> : undefined,
            },
          ]}
        />

        <div style={{ marginTop: 24, textAlign: 'right' }}>
          {/* Mostrar botão apenas quando terminou (sucesso ou erro) */}
          {(Object.values(stepStatus).every(s => s === 'finish' || s === 'error' || s === 'wait')) &&
           (stepStatus[0] === 'finish' || stepStatus[0] === 'error') && (
            <Button
              type={stepStatus[2] === 'finish' && stepStatus[3] === 'finish' ? 'primary' : 'default'}
              danger={stepStatus[2] === 'error' || stepStatus[3] === 'error'}
              onClick={() => {
                setBatchSyncModalVisible(false);
                // Refresh da tabela após sincronização
                fetchSyncStatus(selectedServer);
              }}
            >
              {stepStatus[2] === 'finish' && stepStatus[3] === 'finish' ? 'Concluído' : 'Fechar'}
            </Button>
          )}
        </div>
      </Modal>

      {/* FASE 4: Drawer de Visualização de Campo */}
      <Drawer
        title={`Detalhes do Campo: ${drawerField?.display_name || ''}`}
        placement="right"
        width={600}
        onClose={() => setDrawerVisible(false)}
        open={drawerVisible}
      >
        {drawerField && (
          <div>
            <Descriptions title="Informações Gerais" bordered column={1} size="small">
              <Descriptions.Item label="Nome Técnico">
                <code>{drawerField.name}</code>
              </Descriptions.Item>
              <Descriptions.Item label="Nome de Exibição">
                {drawerField.display_name}
              </Descriptions.Item>
              <Descriptions.Item label="Descrição">
                {drawerField.description || '-'}
              </Descriptions.Item>
              <Descriptions.Item label="Categoria">
                <Tag>{drawerField.category}</Tag>
              </Descriptions.Item>
              <Descriptions.Item label="Tipo">{drawerField.field_type}</Descriptions.Item>
              <Descriptions.Item label="Ordem">
                <Badge count={drawerField.order} style={{ backgroundColor: '#1890ff' }} />
              </Descriptions.Item>
              <Descriptions.Item label="Source Label">
                <code style={{ fontSize: 11 }}>{drawerField.source_label}</code>
              </Descriptions.Item>
            </Descriptions>

            <Divider />

            <Descriptions title="Configurações" bordered column={2} size="small">
              <Descriptions.Item label="Obrigatório">
                {drawerField.required ? <Tag color="red">Sim</Tag> : <Tag>Não</Tag>}
              </Descriptions.Item>
              <Descriptions.Item label="Editável">
                {drawerField.editable ? <Tag color="green">Sim</Tag> : <Tag>Não</Tag>}
              </Descriptions.Item>
              <Descriptions.Item label="Em Tabelas">
                {drawerField.show_in_table ? <Tag color="blue">Sim</Tag> : <Tag>Não</Tag>}
              </Descriptions.Item>
              <Descriptions.Item label="Em Dashboard">
                {drawerField.show_in_dashboard ? <Tag color="blue">Sim</Tag> : <Tag>Não</Tag>}
              </Descriptions.Item>
              <Descriptions.Item label="Em Formulários" span={2}>
                {drawerField.show_in_form ? <Tag color="blue">Sim</Tag> : <Tag>Não</Tag>}
              </Descriptions.Item>
            </Descriptions>

            <Divider />

            <Descriptions title="Status de Sincronização" bordered column={1} size="small">
              <Descriptions.Item label="Status">
                {drawerField.sync_status === 'synced' && (
                  <Tag color="success" icon={<CheckCircleOutlined />}>
                    Sincronizado
                  </Tag>
                )}
                {drawerField.sync_status === 'outdated' && (
                  <Tag color="warning" icon={<WarningOutlined />}>
                    Desatualizado
                  </Tag>
                )}
                {drawerField.sync_status === 'missing' && (
                  <Tag color="error" icon={<WarningOutlined />}>
                    Não Aplicado
                  </Tag>
                )}
                {drawerField.sync_status === 'error' && (
                  <Tag color="default" icon={<WarningOutlined />}>
                    Erro
                  </Tag>
                )}
                {!drawerField.sync_status && <Tag>-</Tag>}
              </Descriptions.Item>
              <Descriptions.Item label="Mensagem">
                <Paragraph
                  style={{ marginBottom: 0, fontSize: 12 }}
                  type={drawerField.sync_status === 'synced' ? 'success' : 'warning'}
                >
                  {drawerField.sync_message || '-'}
                </Paragraph>
              </Descriptions.Item>
              <Descriptions.Item label="Target Label (Prometheus)">
                <code>{drawerField.prometheus_target_label || '-'}</code>
              </Descriptions.Item>
              <Descriptions.Item label="Source Label (Metadata)">
                <code style={{ fontSize: 11 }}>
                  {drawerField.metadata_source_label || drawerField.source_label}
                </code>
              </Descriptions.Item>
            </Descriptions>

            {drawerField.validation_regex && (
              <>
                <Divider />
                <Descriptions title="Validação" bordered column={1} size="small">
                  <Descriptions.Item label="Regex">
                    <code style={{ fontSize: 11 }}>{drawerField.validation_regex}</code>
                  </Descriptions.Item>
                </Descriptions>
              </>
            )}

            {drawerField.options && drawerField.options.length > 0 && (
              <>
                <Divider />
                <Descriptions title="Opções" bordered column={1} size="small">
                  <Descriptions.Item label="Valores">
                    <Space wrap>
                      {drawerField.options.map((opt, idx) => (
                        <Tag key={idx}>{opt}</Tag>
                      ))}
                    </Space>
                  </Descriptions.Item>
                </Descriptions>
              </>
            )}
          </div>
        )}
      </Drawer>

      {/* Modal de Progresso de Extração (COMPONENTE COMPARTILHADO) */}
      <ExtractionProgressModal
        visible={progressModalVisible}
        onClose={() => setProgressModalVisible(false)}
        onRefresh={forceRefreshFields}
        loading={fieldsData.loading}
        fromCache={fieldsData.fromCache}
        successfulServers={fieldsData.successfulServers}
        totalServers={fieldsData.totalServers}
        serverStatus={fieldsData.serverStatus}
        totalFields={fieldsData.totalFields}
        error={fieldsData.fieldsError}
      />

      {/* MODAL: Editar Site (apenas name, color, is_default editáveis) */}
      <ModalForm<Site>
        key={editingSite?.code || 'edit-modal'}
        title={`Editar Site: ${editingSite?.code || ''}`}
        open={editModalOpen}
        onOpenChange={(visible) => {
          setEditModalOpen(visible);
          if (!visible) {
            setEditingSite(null);
          }
        }}
        onFinish={handleUpdateSite}
        initialValues={editingSite || undefined}
        width={700}
        modalProps={{
          destroyOnHidden: true,
        }}
      >
        {/* CAMPOS READONLY (auto-detectados do Prometheus) */}
        <ProFormText
          name="code"
          label="Código do Site"
          disabled
          tooltip="Auto-detectado de external_labels.site no prometheus.yml"
        />
        <ProFormText
          name="prometheus_host"
          label="Servidor Prometheus"
          disabled
          tooltip="Auto-detectado de PROMETHEUS_CONFIG_HOSTS no .env"
        />
        <ProFormDigit
          name="prometheus_port"
          label="Porta Prometheus"
          disabled
          tooltip="Auto-detectado de PROMETHEUS_CONFIG_HOSTS no .env"
        />
        
        {/* Exibir external_labels como JSON readonly */}
        {editingSite?.external_labels && (
          <ProFormTextArea
            name="external_labels"
            label="External Labels (Prometheus)"
            disabled
            fieldProps={{
              value: JSON.stringify(editingSite.external_labels, null, 2),
              autoSize: { minRows: 3, maxRows: 8 },
            }}
            tooltip="Labels extraídos automaticamente da configuração global do Prometheus"
          />
        )}

        {/* CAMPOS EDITÁVEIS */}
        <Divider orientation="left">Configurações Editáveis</Divider>
        
        <ProFormText
          name="name"
          label="Nome Descritivo"
          placeholder="Ex: São Paulo (SP)"
          rules={[{ required: true, message: 'Nome obrigatório' }]}
          tooltip="Nome amigável para exibição na interface"
        />
        <ProFormSelect
          name="color"
          label="Cor do Badge"
          options={[
            { label: 'Azul', value: 'blue' },
            { label: 'Verde', value: 'green' },
            { label: 'Laranja', value: 'orange' },
            { label: 'Roxo', value: 'purple' },
            { label: 'Vermelho', value: 'red' },
            { label: 'Ciano', value: 'cyan' },
            { label: 'Magenta', value: 'magenta' },
            { label: 'Dourado', value: 'gold' },
          ]}
          placeholder="Selecione uma cor"
          tooltip="Cor visual que aparecerá nos badges do site"
        />
        <ProFormSwitch
          name="is_default"
          label="Site Padrão"
          tooltip="Site padrão NÃO recebe sufixo nos nomes de serviço (ex: se habilitado, 'router' em vez de 'router-sp')"
        />
      </ModalForm>
    </PageContainer>
  );
};

export default MetadataFieldsPage;
