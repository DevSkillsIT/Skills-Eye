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
} from 'antd';

const { Text, Paragraph } = Typography;
import {
  // PlusOutlined, EditOutlined, DeleteOutlined removidos - página agora é SOMENTE LEITURA
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
import { Checkbox, Popover } from 'antd';
import axios from 'axios';
import { metadataFieldsAPI, consulAPI } from '../services/api';
// metadataDynamicAPI removido - campos vêm 100% do Prometheus agora
import type { PreviewFieldChangeResponse } from '../services/api';
import ReferenceValueInput from '../components/ReferenceValueInput';
import { Form } from 'antd';

const API_URL = import.meta.env?.VITE_API_URL ?? 'http://localhost:5000/api/v1';

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
  category: string;
  editable: boolean;
  validation_regex?: string;
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
  const [createModalVisible, setCreateModalVisible] = useState(false);
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

  const fetchFields = async () => {
    setLoading(true);
    try {
      // PASSO 1: BUSCAR CAMPOS DINAMICAMENTE DO PROMETHEUS.YML VIA SSH
      // Não usa arquivo JSON hardcoded - extrai dos relabel_configs do Prometheus
      const response = await axios.get(`${API_URL}/prometheus-config/fields`, {
        timeout: 30000, // 30 segundos (lê prometheus.yml via SSH de múltiplos servidores)
      });

      if (response.data.success) {
        const prometheusFields = response.data.fields;

        // PASSO 2: BUSCAR CONFIGURAÇÕES DE EXIBIÇÃO POR PÁGINA DO CONSUL KV
        // Para cada campo, buscar sua configuração de show_in_services/exporters/blackbox
        const fieldsWithConfig = await Promise.all(
          prometheusFields.map(async (field: MetadataField) => {
            try {
              // Buscar configuração do campo no KV
              const configResponse = await axios.get(`${API_URL}/kv/metadata/field-config/${field.name}`);

              if (configResponse.data.success && configResponse.data.config) {
                // Merge: dados do Prometheus + configuração do KV
                return {
                  ...field,
                  show_in_services: configResponse.data.config.show_in_services ?? true,
                  show_in_exporters: configResponse.data.config.show_in_exporters ?? true,
                  show_in_blackbox: configResponse.data.config.show_in_blackbox ?? true,
                };
              }
            } catch (error) {
              // Se não existe config no KV, usar valores padrão (todos true)
              console.log(`[DEBUG] Usando config padrão para campo "${field.name}"`);
            }

            // Valores padrão se não houver configuração salva
            return {
              ...field,
              show_in_services: true,
              show_in_exporters: true,
              show_in_blackbox: true,
            };
          })
        );

        setFields(fieldsWithConfig);
      }
    } catch (error: any) {
      if (error.code === 'ECONNABORTED') {
        message.error('Tempo esgotado ao carregar campos (servidor lento)');
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

  useEffect(() => {
    fetchServers();
  }, []);

  // Recarregar campos e sync status quando trocar de servidor
  useEffect(() => {
    if (selectedServer) {
      // Animação de "servidor alterado"
      setServerJustChanged(true);
      setTimeout(() => setServerJustChanged(false), 2000);

      // Limpar dados antigos IMEDIATAMENTE
      setFields([]);
      setServerHasNoPrometheus(false);
      setServerPrometheusMessage('');

      // IMPORTANTE: Buscar external_labels PRIMEIRO, DEPOIS os campos
      // Isso garante que o filtro funcione corretamente
      const loadData = async () => {
        console.log('[DEBUG] Iniciando carregamento de dados...');

        // PASSO 1: Buscar external_labels ANTES (necessário para filtrar campos)
        console.log('[DEBUG] Buscando external_labels...');
        await fetchExternalLabels(selectedServer);
        console.log('[DEBUG] External_labels carregados, agora buscando campos...');

        // PASSO 2: Buscar campos e sync status EM PARALELO
        await Promise.all([
          fetchFields(),
          fetchSyncStatus(selectedServer),
        ]);

        console.log('[DEBUG] Todos os dados carregados!');
      };

      loadData();
    }
  }, [selectedServer]);

  useEffect(() => {
    return () => {
      if (fallbackTimerRef.current) {
        clearTimeout(fallbackTimerRef.current);
      }
    };
  }, []);

  const handleCreateField = async (values: any) => {
    try {
      // PASSO 1: Auto-cadastrar categoria (retroalimentação)
      if (values.category) {
        try {
          await axios.post(`${API_URL}/reference-values/ensure`, {
            field_name: 'field_category',
            value: values.category
          });
        } catch (err) {
          console.warn('Erro ao auto-cadastrar categoria:', err);
          // Não bloqueia criação do campo se falhar
        }
      }

      // PASSO 2: Criar campo metadata
      const response = await axios.post(`${API_URL}/metadata-fields/`, {
        field: {
          ...values,
          source_label: `__meta_consul_service_metadata_${values.name}`,
        },
        sync_prometheus: true
      });

      if (response.data.success) {
        message.success(`Campo '${values.display_name}' criado com sucesso!`);
        fetchFields();
        setCreateModalVisible(false);

        // Perguntar se quer replicar
        modal.confirm({
          title: 'Replicar para servidores slaves?',
          content: 'Deseja replicar este campo para todos os servidores slaves?',
          okText: 'Sim, replicar',
          cancelText: 'Não',
          onOk: () => handleReplicateToSlaves(),
        });
      }
    } catch (error: any) {
      message.error('Erro ao criar campo: ' + (error.response?.data?.detail || error.message));
    }
  };

  const handleEditField = async (values: any) => {
    if (!editingField) return;

    try {
      // PASSO 1: Auto-cadastrar categoria (retroalimentação)
      if (values.category) {
        try {
          await axios.post(`${API_URL}/reference-values/ensure`, {
            field_name: 'field_category',
            value: values.category
          });
        } catch (err) {
          console.warn('Erro ao auto-cadastrar categoria:', err);
          // Não bloqueia edição do campo se falhar
        }
      }

      // PASSO 2: Atualizar campo metadata
      const response = await axios.put(`${API_URL}/metadata-fields/${editingField.name}`, values);

      if (response.data.success) {
        message.success(`Campo '${values.display_name}' atualizado com sucesso!`);
        fetchFields();
        setEditModalVisible(false);
        setEditingField(null);
      }
    } catch (error: any) {
      message.error('Erro ao atualizar campo: ' + (error.response?.data?.detail || error.message));
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
      render: (_, record) => {
        const handleUpdateFieldConfig = async (newPages: {
          show_in_services: boolean;
          show_in_exporters: boolean;
          show_in_blackbox: boolean;
        }) => {
          try {
            // Salvar configuração no Consul KV
            await axios.put(`${API_URL}/kv/metadata/field-config/${record.name}`, {
              show_in_services: newPages.show_in_services,
              show_in_exporters: newPages.show_in_exporters,
              show_in_blackbox: newPages.show_in_blackbox,
            });
            message.success(`Configuração do campo "${record.display_name}" atualizada!`);
            // Recarregar campos
            fetchFields();
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
                onChange={(e) => handleUpdateFieldConfig({
                  show_in_services: e.target.checked,
                  show_in_exporters: record.show_in_exporters ?? true,
                  show_in_blackbox: record.show_in_blackbox ?? true,
                })}
              >
                <Tag color="blue" style={{ margin: 0 }}>Services</Tag>
              </Checkbox>
              <Checkbox
                checked={record.show_in_exporters ?? true}
                onChange={(e) => handleUpdateFieldConfig({
                  show_in_services: record.show_in_services ?? true,
                  show_in_exporters: e.target.checked,
                  show_in_blackbox: record.show_in_blackbox ?? true,
                })}
              >
                <Tag color="green" style={{ margin: 0 }}>Exporters</Tag>
              </Checkbox>
              <Checkbox
                checked={record.show_in_blackbox ?? true}
                onChange={(e) => handleUpdateFieldConfig({
                  show_in_services: record.show_in_services ?? true,
                  show_in_exporters: record.show_in_exporters ?? true,
                  show_in_blackbox: e.target.checked,
                })}
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
      },
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
        <Space size={4}>
          {record.show_in_table && <Tag color="blue">Tabela</Tag>}
          {record.show_in_dashboard && <Tag color="green">Dashboard</Tag>}
          {record.show_in_form && <Tag color="orange">Form</Tag>}
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
      width: 240,
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
          {/* BOTÕES EDIT/DELETE REMOVIDOS - Página agora é SOMENTE LEITURA */}
          {/* Para editar campos: use PrometheusConfig para editar prometheus.yml */}
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

      {/* Modal Criar Campo */}
      <ModalForm
        title="Adicionar Novo Campo Metadata"
        open={createModalVisible}
        onOpenChange={setCreateModalVisible}
        onFinish={handleCreateField}
        modalProps={{
          width: 600,
          destroyOnHidden: true,
        }}
      >
        <ProFormText
          name="name"
          label="Nome Técnico"
          placeholder="ex: datacenter"
          rules={[{ required: true, pattern: /^[a-z_]+$/, message: 'Apenas letras minúsculas e underscore' }]}
          tooltip="Nome técnico usado internamente (apenas letras minúsculas e _)"
        />
        <ProFormText
          name="display_name"
          label="Nome de Exibição"
          placeholder="ex: Data Center"
          rules={[{ required: true }]}
          tooltip="Nome amigável que aparece na interface"
        />
        <ProFormTextArea
          name="description"
          label="Descrição"
          placeholder="Descrição do campo"
          rows={2}
        />
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
          rules={[{ required: true }]}
        />

        {/* Categoria com auto-cadastro via ReferenceValueInput */}
        <Form.Item
          name="category"
          label="Categoria"
          initialValue="extra"
          rules={[{ required: true, message: 'Informe a categoria' }]}
          tooltip="Digite uma categoria existente ou crie uma nova. Valores novos são cadastrados automaticamente."
        >
          <ReferenceValueInput
            fieldName="field_category"
            placeholder="infrastructure, basic, device, extra, network, security..."
            required
          />
        </Form.Item>

        <ProFormDigit
          name="order"
          label="Ordem"
          min={1}
          max={999}
          initialValue={23}
          fieldProps={{ precision: 0 }}
        />
        <ProFormSwitch name="required" label="Campo Obrigatório" initialValue={false} />
        <ProFormSwitch name="show_in_table" label="Mostrar em Tabelas" initialValue={true} />
        <ProFormSwitch name="show_in_dashboard" label="Mostrar no Dashboard" initialValue={false} />
        <ProFormSwitch name="show_in_form" label="Mostrar em Formulários" initialValue={true} />
        <ProFormSwitch name="editable" label="Editável" initialValue={true} />
      </ModalForm>

      {/* Modal Editar Campo */}
      <ModalForm
        key={editingField?.name || 'edit-field-modal'}
        title={`Editar Campo: ${editingField?.display_name}`}
        open={editModalVisible}
        onOpenChange={(visible) => {
          setEditModalVisible(visible);
          if (!visible) setEditingField(null);
        }}
        onFinish={handleEditField}
        initialValues={editingField || {}}
        modalProps={{
          width: 600,
          destroyOnHidden: true,
        }}
      >
        <ProFormText name="name" label="Nome Técnico" disabled />
        <ProFormText
          name="display_name"
          label="Nome de Exibição"
          rules={[{ required: true }]}
        />
        <ProFormTextArea name="description" label="Descrição" rows={2} />
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
          rules={[{ required: true }]}
        />

        {/* Categoria com auto-cadastro via ReferenceValueInput */}
        <Form.Item
          name="category"
          label="Categoria"
          rules={[{ required: true, message: 'Informe a categoria' }]}
          tooltip="Digite uma categoria existente ou crie uma nova. Valores novos são cadastrados automaticamente."
        >
          <ReferenceValueInput
            fieldName="field_category"
            placeholder="infrastructure, basic, device, extra, network, security..."
            required
          />
        </Form.Item>

        <ProFormDigit
          name="order"
          label="Ordem"
          min={1}
          max={999}
          fieldProps={{ precision: 0 }}
        />
        <ProFormSwitch name="required" label="Campo Obrigatório" />
        <ProFormSwitch name="show_in_table" label="Mostrar em Tabelas" />
        <ProFormSwitch name="show_in_dashboard" label="Mostrar no Dashboard" />
        <ProFormSwitch name="show_in_form" label="Mostrar em Formulários" />
        <ProFormSwitch name="editable" label="Editável" />
        <ProFormText name="source_label" label="Source Label" disabled />
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
