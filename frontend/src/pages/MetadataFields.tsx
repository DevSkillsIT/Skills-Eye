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
} from 'antd';
import type { CategoryInfo } from '../services/api';

const { Text, Paragraph } = Typography;
import {
  // PlusOutlined, DeleteOutlined removidos - página não cria/deleta campos (vêm do Prometheus)
  // EditOutlined RESTAURADO - edita configurações do campo (display_name, category, show_in_*, etc)
  EditOutlined,
  SyncOutlined,
  CloudSyncOutlined,
  ReloadOutlined,
  CheckCircleOutlined,
  MinusCircleOutlined,
  WarningOutlined,
  CloudServerOutlined,
  InfoCircleOutlined,
  EyeOutlined,
  ThunderboltOutlined,
  FileTextOutlined,
  LoadingOutlined,
} from '@ant-design/icons';
import axios from 'axios';
import { metadataFieldsAPI, consulAPI } from '../services/api';
// metadataDynamicAPI removido - campos vêm 100% do Prometheus agora
import type { PreviewFieldChangeResponse } from '../services/api';

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
  sync_status?: 'synced' | 'outdated' | 'missing' | 'error';  // ← FASE 1: Status de sincronização
  sync_message?: string;  // ← FASE 1: Mensagem do status
  prometheus_target_label?: string;  // ← FASE 1: Label usado no Prometheus
  metadata_source_label?: string;  // ← FASE 1: Label metadata do Consul
}

interface Server {
  id: string;
  hostname: string;
  port: number;
  username: string;
  type: string;
  display_name: string;
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

  const fetchFields = async () => {
    setLoading(true);
    try {
      // USAR ENDPOINT OTIMIZADO QUE JÁ FAZ MERGE NO BACKEND
      // Evita fazer 56+ requisições HTTP paralelas (um por campo)
      const response = await axios.get(`${API_URL}/metadata-fields/`, {
        timeout: 30000,
      });

      if (response.data.success) {
        const fields = response.data.fields.map((field: any) => ({
          ...field,
          // Garantir defaults para campos que podem estar ausentes
          show_in_services: field.show_in_services ?? true,
          show_in_exporters: field.show_in_exporters ?? true,
          show_in_blackbox: field.show_in_blackbox ?? true,
        }));

        console.log(`[METADATA-FIELDS] ✅ ${fields.length} campos carregados (1 requisição)`);
        setFields(fields);
      }
    } catch (error: any) {
      if (error.code === 'ECONNABORTED') {
        message.error('Tempo esgotado ao carregar campos');
      } else {
        message.error('Erro ao carregar campos: ' + (error.response?.data?.detail || error.message));
      }
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
        timeout: 10000,
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
      const response = await axios.get(`${API_URL}/metadata-fields/sync-status`, {
        params: { server_id: serverId },
        timeout: 30000, // 30 segundos (SSH pode ser lento)
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
          prevFields.map((field): MetadataField => ({
            ...field,
            sync_status: syncStatusMap.get(field.name)?.sync_status || 'error',
            sync_message: syncStatusMap.get(field.name)?.sync_message || 'Status desconhecido',
          }))
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

  // Carregamento inicial: servidores + campos + categorias + sync status (UMA VEZ APENAS)
  useEffect(() => {
    const initializeData = async () => {
      // PASSO 1: Carregar servidores
      await fetchServers();

      // PASSO 2: Carregar campos (UMA VEZ - não depende do servidor selecionado)
      // fetchFields() busca de todos os servidores e carrega configs do KV
      await fetchFields();

      // PASSO 2.5: Carregar categorias (para o dropdown de categoria no edit modal)
      await fetchCategories();

      // PASSO 3: Após carregar servidores e campos, carregar external_labels e sync status do servidor selecionado
      // IMPORTANTE: selectedServer já foi setado por fetchServers() no passo 1
      if (selectedServer) {
        console.log('[DEBUG INIT] Carregando external_labels e sync status inicial...');
        await fetchExternalLabels(selectedServer);
        await fetchSyncStatus(selectedServer);
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

  const handleReplicateToSlaves = async () => {
    const hide = message.loading('Replicando configurações...', 0);
    try {
      const response = await axios.post(`${API_URL}/metadata-fields/replicate-to-slaves`, {});

      hide();

      if (response.data.success) {
        Modal.success({
          title: 'Replicação Concluída',
          content: (
            <div>
              <p>{response.data.message}</p>
              <ul>
                {response.data.results.map((r: any, idx: number) => (
                  <li key={idx} style={{ color: r.success ? 'green' : 'red' }}>
                    {r.server}: {r.success ? r.message : r.error}
                  </li>
                ))}
              </ul>
            </div>
          ),
        });
      }
    } catch (error: any) {
      hide();
      message.error('Erro ao replicar: ' + (error.response?.data?.detail || error.message));
    }
  };

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

    // Detectar campos desatualizados ou não aplicados
    const fieldsToSync = fields.filter(
      (f) => f.sync_status === 'outdated' || f.sync_status === 'missing'
    );

    if (fieldsToSync.length === 0) {
      message.info('Todos os campos já estão sincronizados');
      return;
    }

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
                <Tag color="orange">{field.sync_status === 'missing' ? 'Não Aplicado' : 'Desatualizado'}</Tag>
                <strong>{field.display_name}</strong> <code>({field.name})</code>
              </List.Item>
            )}
          />
          <Alert
            message="Processo de Sincronização"
            description="Os campos serão adicionados/atualizados no arquivo prometheus.yml do servidor selecionado. O Prometheus será recarregado automaticamente."
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

      const fieldNames = fieldsToSync.map((f) => f.name);

      // STEP 0: Preparação (com delay visual)
      setCurrentStep(0);
      setStepStatus(prev => ({ ...prev, 0: 'process' }));
      setStepMessages(prev => ({ ...prev, 0: `Preparando sincronização de ${fieldNames.length} campo(s)...` }));

      await new Promise(resolve => setTimeout(resolve, 500)); // Delay visual

      setStepStatus(prev => ({ ...prev, 0: 'finish' }));
      setStepMessages(prev => ({ ...prev, 0: `Campos preparados: ${fieldNames.join(', ')} ✓` }));

      await new Promise(resolve => setTimeout(resolve, 300)); // Delay entre steps

      // STEP 1: Backend faz TUDO (ler, alterar com ruamel.yaml, salvar)
      setCurrentStep(1);
      setStepStatus(prev => ({ ...prev, 1: 'process' }));
      setStepMessages(prev => ({ ...prev, 1: `Conectando ao servidor e aplicando mudanças...` }));

      const batchSyncResponse = await metadataFieldsAPI.batchSync({
        field_names: fieldNames,
        server_id: selectedServer,
        dry_run: false
      });

      const { success: backendSuccess, results } = batchSyncResponse.data;
      const successCount = results.filter(r => r.success).length;
      const failCount = results.filter(r => !r.success).length;

      if (failCount > 0) {
        setStepStatus(prev => ({ ...prev, 1: 'error' }));
        const errors = results.filter(r => !r.success).map(r => r.message).join('; ');
        setStepMessages(prev => ({ ...prev, 1: `Erros: ${errors}` }));
        if (successCount === 0) {
          message.error('Nenhum campo foi sincronizado. Verifique os erros e tente novamente.');
          return;
        }
      } else {
        setStepStatus(prev => ({ ...prev, 1: 'finish' }));
        const totalChanges = results.reduce((sum, r) => sum + r.changes_applied, 0);
        setStepMessages(prev => ({ ...prev, 1: `${successCount} campo(s) sincronizado(s), ${totalChanges} mudança(s) aplicada(s) ✓` }));
      }

      if (!backendSuccess) {
        console.warn('[BATCH-SYNC] Backend retornou sucesso parcial', batchSyncResponse.data);
      }

      await new Promise(resolve => setTimeout(resolve, 400)); // Delay entre steps

      // STEP 2: Reload Prometheus
      setCurrentStep(2);
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
            color: 'error',
            text: 'Não Aplicado',
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
          {/* Botão DELETE removido - campos vêm do Prometheus (não podem ser deletados manualmente) */}
        </Space>
      ),
    },
  ];

  const handleRestartSelected = async () => {
    const selectedServerObj = servers.find(s => s.id === selectedServer);
    if (!selectedServerObj) {
      message.error('Nenhum servidor selecionado');
      return;
    }

    modal.confirm({
      title: 'Confirmar Reinicialização',
      content: `Deseja reiniciar o Prometheus no servidor ${selectedServerObj.hostname}?`,
      okText: 'Sim, reiniciar',
      cancelText: 'Cancelar',
      onOk: async () => {
        const hide = message.loading(`Reiniciando Prometheus em ${selectedServerObj.hostname}...`, 0);
        try {
          const response = await axios.post(`${API_URL}/metadata-fields/restart-prometheus`, {
            server_ids: [selectedServer]
          });

          hide();

          if (response.data.success) {
            message.success(`Prometheus reiniciado com sucesso em ${selectedServerObj.hostname}`);
          }
        } catch (error: any) {
          hide();
          message.error('Erro ao reiniciar: ' + (error.response?.data?.detail || error.message));
        }
      },
    });
  };

  const handleRestartAll = async () => {
    modal.confirm({
      title: 'Confirmar Reinicialização em Todos os Servidores',
      content: `Deseja reiniciar o Prometheus em TODOS os ${servers.length} servidores (Master + Slaves)?`,
      okText: 'Sim, reiniciar todos',
      cancelText: 'Cancelar',
      onOk: async () => {
        const hide = message.loading('Reiniciando Prometheus em todos os servidores...', 0);
        try {
          const response = await axios.post(`${API_URL}/metadata-fields/restart-prometheus`, {});

          hide();

          if (response.data.success) {
            Modal.success({
              title: 'Reinicialização Concluída',
              content: (
                <div>
                  <p>{response.data.message}</p>
                  <ul>
                    {response.data.results.map((r: any, idx: number) => (
                      <li key={idx} style={{ color: r.success ? 'green' : 'red' }}>
                        {r.server}: {r.success ? r.message : r.error}
                      </li>
                    ))}
                  </ul>
                </div>
              ),
            });
          }
        } catch (error: any) {
          hide();
          message.error('Erro ao reiniciar: ' + (error.response?.data?.detail || error.message));
        }
      },
    });
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

      {/* Card de Seleção de Servidor e Ações - ALTURA FIXA */}
      <Card style={{ marginBottom: 16, height: 140, overflow: 'hidden' }}>
        <Row gutter={[16, 16]} align="middle">
          {/* Coluna 1: Seletor de Servidor */}
          <Col xs={24} lg={10}>
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

          {/* BOTÃO "Adicionar Campo" REMOVIDO - Página agora é SOMENTE LEITURA */}
          {/* Para adicionar campos: edite prometheus.yml via PrometheusConfig */}

          {/* Coluna 3: Botão Replicar */}
          <Col xs={12} lg={4}>
            <Space direction="vertical" size={4} style={{ width: '100%' }}>
              <Text strong style={{ fontSize: 13, opacity: 0 }}>.</Text>
              <Tooltip title="Replica configurações do Master para todos os Slaves">
                <Button
                  size="large"
                  block
                  icon={<CloudSyncOutlined />}
                  onClick={handleReplicateToSlaves}
                  disabled={!selectedServer}
                >
                  Master → Slaves
                </Button>
              </Tooltip>
            </Space>
          </Col>

          {/* Coluna 4: Botões Reiniciar */}
          <Col xs={24} lg={6}>
            <Space direction="vertical" size={4} style={{ width: '100%' }}>
              <Text strong style={{ fontSize: 13, opacity: 0 }}>.</Text>
              <Space.Compact size="large" block style={{ width: '100%' }}>
                <Button
                  icon={<ReloadOutlined />}
                  onClick={handleRestartSelected}
                  disabled={!selectedServer}
                  title="Reiniciar Prometheus apenas no servidor selecionado"
                  style={{ flex: 1 }}
                >
                  Reiniciar Selecionado
                </Button>
                <Button
                  icon={<ReloadOutlined />}
                  onClick={handleRestartAll}
                  danger
                  title="Reiniciar Prometheus em todos os servidores"
                  style={{ flex: 1 }}
                >
                  Reiniciar Todos
                </Button>
              </Space.Compact>
            </Space>
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
            // IMPORTANTE: Filtrar external_labels ANTES de contar outdated
            // External labels NÃO devem ser contados aqui (são globais do servidor)
            const metaFieldsOnly = fields.filter((field) => {
              const isExternalLabel = Object.keys(externalLabels).includes(field.name);
              return !isExternalLabel; // Manter apenas campos de meta (relabel_configs)
            });

            const outdatedCount = metaFieldsOnly.filter(
              (f) => f.sync_status === 'outdated' || f.sync_status === 'missing'
            ).length;

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

            toolbarItems.push(
              <Tooltip key="batch-sync" title="Sincronizar campos desatualizados em lote (FASE 3)">
                <Button
                  type="primary"
                  icon={<ThunderboltOutlined />}
                  onClick={handleBatchSync}
                  disabled={!selectedServer || outdatedCount === 0}
                >
                  Sincronizar Campos {outdatedCount > 0 && `(${outdatedCount})`}
                </Button>
              </Tooltip>
            );

            toolbarItems.push(
              <Tooltip key="sync" title="Atualizar status de sincronização">
                <Button
                  icon={<SyncOutlined spin={loadingSyncStatus} />}
                  onClick={() => selectedServer && fetchSyncStatus(selectedServer)}
                  disabled={!selectedServer || loadingSyncStatus}
                >
                  {loadingSyncStatus ? 'Verificando...' : 'Verificar Sincronização'}
                </Button>
              </Tooltip>
            );

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
    </PageContainer>
  );
};

export default MetadataFieldsPage;
