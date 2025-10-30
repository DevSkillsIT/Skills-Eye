/**
 * Editor de Configurações do Prometheus
 *
 * Página para visualizar e editar arquivos YAML do Prometheus/Blackbox/Alertmanager
 * com extração dinâmica de campos metadata e edição de jobs/relabel_configs
 */

import React, { useState, useEffect, useMemo, useCallback } from 'react';
import {
  PageContainer,
  ProDescriptions,
  ProTable,
} from '@ant-design/pro-components';
import type { ProColumns } from '@ant-design/pro-components';
import ColumnSelector, { type ColumnConfig } from '../components/ColumnSelector';
import ResizableTitle from '../components/ResizableTitle';
import {
  Card,
  Table,
  Tabs,
  Tag,
  Space,
  Button,
  message,
  Spin,
  Empty,
  Tooltip,
  Badge,
  Alert,
  Drawer,
  Form,
  Input,
  InputNumber,
  Select,
  Collapse,
  Popconfirm,
  Modal,
  Typography,
  Result,
  App,
  Steps,
  Row,
  Col,
  Dropdown,
  Timeline,
} from 'antd';
import {
  FileTextOutlined,
  ReloadOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  ClockCircleOutlined,
  DatabaseOutlined,
  CloudServerOutlined,
  EditOutlined,
  DeleteOutlined,
  PlusOutlined,
  SaveOutlined,
  EyeOutlined,
  SettingOutlined,
  ArrowRightOutlined,
  InfoCircleOutlined,
  LoadingOutlined,
  SyncOutlined,
  ColumnHeightOutlined,
  ThunderboltOutlined,
  WarningOutlined,
  FireOutlined,
} from '@ant-design/icons';
import axios from 'axios';
import { usePrometheusFields } from '../hooks/usePrometheusFields';
import { useNavigate } from 'react-router-dom';
import Editor from '@monaco-editor/react';
import * as yaml from 'js-yaml';
import { consulAPI, type RawFileContentResponse, type DirectEditResponse } from '../services/api';

const API_URL = import.meta.env?.VITE_API_URL ?? 'http://localhost:5000/api/v1';

const { TextArea } = Input;
const { Panel } = Collapse;
const { Paragraph, Text } = Typography;

interface ConfigFile {
  path: string;
  service: string;
  filename: string;
  host: string;
  exists: boolean;
}

interface ServerStatus {
  hostname: string;
  success: boolean;
  from_cache: boolean;
  files_count: number;
  fields_count: number;
  error?: string | null;
  duration_ms: number;
}

interface FilesResponse {
  success: boolean;
  files: ConfigFile[];
  total: number;
}

interface JobsResponse {
  success: boolean;
  jobs: any[];
  total: number;
  file_path: string;
}

interface Server {
  id: string;
  hostname: string;
  port: number;
  username: string;
  type: string;
  display_name: string;
}

const PrometheusConfig: React.FC = () => {
  const navigate = useNavigate();
  const { modal } = App.useApp(); // Hook para usar Modal com contexto
  const [allFiles, setAllFiles] = useState<ConfigFile[]>([]); // TODOS os arquivos
  const [selectedFile, setSelectedFile] = useState<string | null>(null);
  const [jobs, setJobs] = useState<any[]>([]);
  const [fileType, setFileType] = useState<string>('prometheus'); // NOVO: tipo do arquivo
  const [itemKey, setItemKey] = useState<string>('job_name'); // NOVO: chave do item
  const [loadingFiles, setLoadingFiles] = useState(false);
  const [loadingJobs, setLoadingJobs] = useState(false);
  const [editingJob, setEditingJob] = useState<any | null>(null);
  const [drawerVisible, setDrawerVisible] = useState(false);
  const [servers, setServers] = useState<Server[]>([]);
  const [selectedServer, setSelectedServer] = useState<string>('');
  const [previousServer, setPreviousServer] = useState<string>(''); // Para detectar mudança real
  const [serverJustChanged, setServerJustChanged] = useState(false); // Para animação ao trocar servidor
  const [columnConfig, setColumnConfig] = useState<ColumnConfig[]>([]);
  const [columnWidths, setColumnWidths] = useState<Record<string, number>>({});
  const [alertViewMode, setAlertViewMode] = useState<'group' | 'individual'>('group'); // Toggle para visões de alertas
  const [tableSize, setTableSize] = useState<'small' | 'middle' | 'large'>('middle'); // Densidade da tabela
  const [activeTabKey, setActiveTabKey] = useState<string>('jobs'); // Controla qual aba está ativa
  const [alertmanagerViewMode, setAlertmanagerViewMode] = useState<'routes' | 'receivers' | 'inhibit-rules'>('routes'); // Toggle para visões do Alertmanager

  // Alertmanager data states
  const [alertmanagerRoutes, setAlertmanagerRoutes] = useState<any[]>([]);
  const [alertmanagerReceivers, setAlertmanagerReceivers] = useState<any[]>([]);
  const [alertmanagerInhibitRules, setAlertmanagerInhibitRules] = useState<any[]>([]);
  const [loadingAlertmanager, setLoadingAlertmanager] = useState(false);

  // Monaco Editor states
  const [monacoEditorVisible, setMonacoEditorVisible] = useState(false);
  const [monacoContent, setMonacoContent] = useState<string>('');
  const [monacoOriginalContent, setMonacoOriginalContent] = useState<string>('');
  const [monacoLoading, setMonacoLoading] = useState(false);
  const [monacoSaving, setMonacoSaving] = useState(false);
  const [monacoFileInfo, setMonacoFileInfo] = useState<RawFileContentResponse | null>(null);
  const [monacoValidationError, setMonacoValidationError] = useState<string | null>(null);

  // Progress Modal states
  const [progressVisible, setProgressVisible] = useState(false);
  const [currentStep, setCurrentStep] = useState(0);
  const [stepStatus, setStepStatus] = useState<Record<number, 'wait' | 'process' | 'finish' | 'error'>>({});
  const [stepMessages, setStepMessages] = useState<Record<number, string>>({});

  // JSON Editor states
  const [jsonError, setJsonError] = useState<string | null>(null);
  const [editingJobData, setEditingJobData] = useState<Record<string, unknown> | null>(null);

  const [form] = Form.useForm();

  // Handler para redimensionamento de colunas (padrão Blackbox)
  const handleResize = useCallback(
    (columnKey: string) =>
      (_: React.SyntheticEvent, { size }: { size: { width: number } }) => {
        setColumnWidths((prev) => ({ ...prev, [columnKey]: size.width }));
      },
    [],
  );

  // Filtrar arquivos pelo servidor selecionado
  const files = React.useMemo(() => {
    // Ordenar alfabeticamente se não há servidor selecionado
    if (!selectedServer) {
      return [...allFiles].sort((a, b) => a.filename.localeCompare(b.filename));
    }

    // Extrair hostname do selectedServer (formato: "172.16.1.26:5522")
    const serverHostname = selectedServer.split(':')[0];

    // Filtrar arquivos que pertencem ao servidor selecionado e ordenar alfabeticamente
    return allFiles
      .filter(file => {
        // file.host tem formato "root@172.16.1.26:5522"
        return file.host.includes(serverHostname);
      })
      .sort((a, b) => a.filename.localeCompare(b.filename));
  }, [allFiles, selectedServer]);

  // OTIMIZAÇÃO: Carregar fields apenas quando a aba for visualizada
  const [fieldsData, setFieldsData] = useState<{
    fields: any[];
    loading: boolean;
    error: string | null;
    total: number;
    lastUpdated: string | null;
    serverStatus: ServerStatus[];
    totalServers: number;
    successfulServers: number;
    fromCache: boolean;
  }>({
    fields: [],
    loading: false,
    error: null,
    total: 0,
    lastUpdated: null,
    serverStatus: [],
    totalServers: 0,
    successfulServers: 0,
    fromCache: false,
  });

  // Modal de progresso de extração
  const [progressModalVisible, setProgressModalVisible] = useState(false);

  const loadPrometheusFields = async () => {
    // Abrir modal IMEDIATAMENTE ao iniciar carregamento
    setProgressModalVisible(true);

    // PASSO 1: Buscar lista de servidores para mostrar Timeline pré-populada
    try {
      const serversResponse = await axios.get(`${API_URL}/metadata-fields/servers`);
      if (serversResponse.data.success && serversResponse.data.servers) {
        const serversList = serversResponse.data.servers as Array<{ id: string; name: string }>;

        // Inicializar Timeline com todos os servidores em "Processando..."
        const initialStatus: ServerStatus[] = serversList.map((srv) => ({
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
          error: null,
          serverStatus: initialStatus,
          totalServers: initialStatus.length,
          successfulServers: 0,
        }));
      }
    } catch (err) {
      console.error('Erro ao buscar servidores:', err);
    }

    // PASSO 2: Fazer requisição de fields (isso vai demorar)
    try {
      const response = await axios.get(`${API_URL}/prometheus-config/fields`, {
        timeout: 30000,
      });
      if (response.data.success) {
        setFieldsData({
          fields: response.data.fields,
          loading: false,
          error: null,
          total: response.data.total,
          lastUpdated: response.data.last_updated,
          serverStatus: response.data.server_status || [],
          totalServers: response.data.total_servers || 0,
          successfulServers: response.data.successful_servers || 0,
          fromCache: response.data.from_cache || false,
        });
      }
    } catch (err: any) {
      setFieldsData(prev => ({
        ...prev,
        loading: false,
        error: err.response?.data?.message || 'Erro ao carregar campos',
      }));
    }
  };

  const { fields, loading: loadingFields, error: fieldsError, total: totalFields, lastUpdated, serverStatus, totalServers, successfulServers, fromCache } = fieldsData;
  const reloadFields = loadPrometheusFields;

  // Carregar lista de arquivos
  // OTIMIZAÇÃO: useCallback previne recriação da função a cada render
  // IMPORTANTE: NÃO incluir selectedFile nas dependências pois a função o MODIFICA (setSelectedFile)
  // Isso causaria loop infinito: fetchFiles → setSelectedFile → selectedFile muda → fetchFiles recriado → loop
  const fetchFiles = useCallback(async () => {
    // CRÍTICO: Garantir que servidor está selecionado antes de buscar arquivos
    // Isso previne chamadas sem hostname que causariam SSH em TODOS os servidores (5+ segundos)
    if (!selectedServer) {
      console.warn('[fetchFiles] Abortado: nenhum servidor selecionado');
      message.warning('Selecione um servidor primeiro');
      return;
    }

    setLoadingFiles(true);
    // CORREÇÃO: Limpar arquivos antigos DEPOIS de setar loading
    // Isso previne flash de lista vazia com loading=false
    setAllFiles([]);

    try {
      // OTIMIZAÇÃO: Sempre passa hostname para buscar apenas do servidor selecionado
      const hostname = selectedServer.split(':')[0]; // Extrai IP de "172.16.1.26:5522"
      const url = `${API_URL}/prometheus-config/files?hostname=${encodeURIComponent(hostname)}`;

      const response = await axios.get<FilesResponse>(url, {
        timeout: 30000, // 30 segundos (SSH pode ser lento)
      });
      if (response.data.success) {
        setAllFiles(response.data.files);
        // CORREÇÃO: Remover auto-seleção daqui para evitar duplicação
        // A auto-seleção é feita no useEffect (linhas 581-607) que monitora allFiles
        // Isso previne tentativas de carregar arquivos que não existem
      } else {
        message.error('Falha ao carregar arquivos');
      }
    } catch (err: any) {
      if (err.code === 'ECONNABORTED') {
        message.error('Tempo esgotado ao carregar arquivos (conexão SSH lenta)');
      } else {
        message.error(err.response?.data?.message || 'Erro ao carregar arquivos');
      }
    } finally {
      setLoadingFiles(false);
    }
  }, [selectedServer]); // APENAS selectedServer - não incluir selectedFile!

  // Carregar estrutura de um arquivo (NOVO - usa /file/structure)
  // OTIMIZAÇÃO: useCallback previne recriação da função a cada render
  const fetchJobs = useCallback(async (filePath: string, serverIdWithPort?: string) => {
    setLoadingJobs(true);
    try {
      // OTIMIZAÇÃO: Extrair hostname (IP) do selectedServer para passar na query
      // Formato: "172.16.1.26:5522" → "172.16.1.26"
      let url = `${API_URL}/prometheus-config/file/structure?file_path=${encodeURIComponent(filePath)}`;
      if (serverIdWithPort) {
        const hostname = serverIdWithPort.split(':')[0];
        url += `&hostname=${encodeURIComponent(hostname)}`;
      }

      const response = await axios.get(url);
      if (response.data.success) {
        setJobs(response.data.items);
        setFileType(response.data.type); // NOVO: guardar tipo
        setItemKey(response.data.item_key || 'name'); // NOVO: guardar chave
        message.success(`Carregados ${response.data.total_items} items (${response.data.type})`);
      } else {
        message.error('Falha ao carregar configurações');
      }
    } catch (err: any) {
      message.error(err.response?.data?.detail || 'Erro ao carregar configurações');
      setJobs([]);
    } finally {
      setLoadingJobs(false);
    }
  }, []); // Sem dependências: função estável que recebe tudo via parâmetro

  // Carregar dados do Alertmanager (routes, receivers, inhibit_rules)
  const fetchAlertmanagerData = useCallback(async (filePath: string, serverIdWithPort?: string) => {
    // DEBUG: Para debugar, descomente: console.log('fetchAlertmanagerData:', { filePath, serverIdWithPort });
    setLoadingAlertmanager(true);

    // CRÍTICO: Limpar dados antigos IMEDIATAMENTE antes de carregar novos
    // Isso previne mostrar dados do servidor anterior enquanto carrega do novo servidor
    setAlertmanagerRoutes([]);
    setAlertmanagerReceivers([]);
    setAlertmanagerInhibitRules([]);

    try {
      // Extrair hostname para passar ao backend
      let hostnameParam = '';
      if (serverIdWithPort) {
        const hostname = serverIdWithPort.split(':')[0];
        hostnameParam = `&hostname=${encodeURIComponent(hostname)}`;
      }

      // Buscar todas as 3 visões em paralelo
      const [routesRes, receiversRes, inhibitRulesRes] = await Promise.all([
        axios.get(`${API_URL}/prometheus-config/alertmanager/routes?file_path=${encodeURIComponent(filePath)}${hostnameParam}`),
        axios.get(`${API_URL}/prometheus-config/alertmanager/receivers?file_path=${encodeURIComponent(filePath)}${hostnameParam}`),
        axios.get(`${API_URL}/prometheus-config/alertmanager/inhibit-rules?file_path=${encodeURIComponent(filePath)}${hostnameParam}`)
      ]);

      if (routesRes.data.success) {
        setAlertmanagerRoutes(routesRes.data.routes || []);
      }
      if (receiversRes.data.success) {
        setAlertmanagerReceivers(receiversRes.data.receivers || []);
      }
      if (inhibitRulesRes.data.success) {
        setAlertmanagerInhibitRules(inhibitRulesRes.data.inhibit_rules || []);
      }

      setFileType('alertmanager');
      message.success(`Alertmanager carregado: ${routesRes.data.total} rotas, ${receiversRes.data.total} receptores, ${inhibitRulesRes.data.total} regras`);
    } catch (err: any) {
      message.error(err.response?.data?.detail || 'Erro ao carregar Alertmanager');
      setAlertmanagerRoutes([]);
      setAlertmanagerReceivers([]);
      setAlertmanagerInhibitRules([]);
    } finally {
      setLoadingAlertmanager(false);
    }
  }, []);

  // Processar dados para visão de alertas (grupo vs individual)
  const processedJobs = useMemo(() => {
    if (fileType !== 'rules' || alertViewMode === 'group') {
      return jobs; // Retornar dados normais (visão por grupo)
    }

    // Visão individual: "achatar" todos os alertas em uma lista única
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const individualAlerts: any[] = [];

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    jobs.forEach((group: any) => {
      const groupName = group.name || 'Sem nome';
      const rules = group.rules || [];

      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      rules.forEach((rule: any) => {
        if (rule.alert) {
          individualAlerts.push({
            ...rule,
            // Adicionar informações do grupo
            _group_name: groupName,
            _group_interval: group.interval,
            // Usar alert como chave primária
            name: rule.alert,
          });
        }
      });
    });

    return individualAlerts;
  }, [jobs, fileType, alertViewMode]);

  // Processar dados do Alertmanager baseado na visão selecionada
  const processedAlertmanagerData = useMemo(() => {
    if (fileType !== 'alertmanager') {
      return [];
    }

    switch (alertmanagerViewMode) {
      case 'routes':
        return alertmanagerRoutes;
      case 'receivers':
        return alertmanagerReceivers;
      case 'inhibit-rules':
        return alertmanagerInhibitRules;
      default:
        return [];
    }
  }, [fileType, alertmanagerViewMode, alertmanagerRoutes, alertmanagerReceivers, alertmanagerInhibitRules]);

  // OTIMIZAÇÃO: Carregamento inicial - combina carregamento de servidores + arquivos
  useEffect(() => {
    const loadInitialData = async () => {
      try {
        // PASSO 1: Carregar servidores
        const response = await axios.get(`${API_URL}/metadata-fields/servers`, {
          timeout: 15000,
        });

        if (!response.data.success) {
          message.error('Falha ao carregar servidores');
          return;
        }

        const serversList = response.data.servers;
        const masterServer = response.data.master;

        setServers(serversList);

        if (!masterServer) {
          message.warning('Nenhum servidor master encontrado');
          return;
        }

        // PASSO 2: Setar servidor master (isso vai triggar fetchFiles via useEffect abaixo)
        setSelectedServer(masterServer.id);

      } catch (error) {
        console.error('Erro ao carregar dados iniciais:', error);
        // Type guard para Axios error
        if (axios.isAxiosError(error) && error.code === 'ECONNABORTED') {
          message.error('Tempo esgotado ao carregar servidores (servidor lento)');
        } else {
          message.error('Erro ao carregar servidores');
        }
      }
    };

    loadInitialData();
  }, []); // Só executa no mount

  // Recarregar arquivos quando trocar de servidor (inicial ou manual)
  useEffect(() => {
    if (selectedServer) {
      // Só mostrar feedback se houve MUDANÇA (não no carregamento inicial)
      const serverWasChanged = previousServer !== '' && previousServer !== selectedServer;

      if (serverWasChanged) {
        // Buscar informações do servidor selecionado
        const serverInfo = servers.find(s => s.id === selectedServer);

        if (serverInfo) {
          // FEEDBACK VISUAL: Mostrar mensagem de sucesso com destaque
          message.success({
            content: (
              <div>
                <strong>🔄 Servidor alterado com sucesso!</strong>
                <br />
                Conectado em: <strong>{serverInfo.display_name}</strong>
                <br />
                Tipo: <Tag color={serverInfo.type === 'master' ? 'green' : 'blue'} style={{ marginTop: 4 }}>
                  {serverInfo.type === 'master' ? 'Master' : 'Slave'}
                </Tag>
              </div>
            ),
            duration: 3,
            icon: <CheckCircleOutlined style={{ color: '#52c41a' }} />,
          });

          // Ativar animação no Alert por 3 segundos
          setServerJustChanged(true);
          setTimeout(() => setServerJustChanged(false), 3000);
        }
      }

      // Atualizar previousServer
      setPreviousServer(selectedServer);

      // CRÍTICO: Limpar TODOS os dados do servidor anterior IMEDIATAMENTE
      setSelectedFile(null);
      setJobs([]);

      // CORREÇÃO: Limpar também dados do Alertmanager quando muda servidor
      setAlertmanagerRoutes([]);
      setAlertmanagerReceivers([]);
      setAlertmanagerInhibitRules([]);

      // CRÍTICO: Resetar fileType para forçar re-renderização da tabela
      setFileType('prometheus');

      // CORREÇÃO: fetchFiles() agora limpa allFiles internamente (evita flash de lista vazia)
      fetchFiles();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedServer, fetchFiles]);

  // Carregar dados quando arquivo OU servidor mudar
  useEffect(() => {
    if (selectedFile && selectedServer) {
      // Detectar se é arquivo alertmanager
      const isAlertmanagerFile = selectedFile.toLowerCase().includes('alertmanager');

      if (isAlertmanagerFile) {
        // Carregar dados do Alertmanager (routes, receivers, inhibit_rules)
        fetchAlertmanagerData(selectedFile, selectedServer);
      } else {
        // Carregar jobs normalmente (prometheus, blackbox, rules)
        fetchJobs(selectedFile, selectedServer);
      }
    }
  }, [selectedFile, selectedServer, fetchJobs, fetchAlertmanagerData]);

  // Quando arquivos mudarem E servidor estiver selecionado, auto-selecionar prometheus.yml
  useEffect(() => {
    // OTIMIZAÇÃO: Só executar se houver arquivos e servidor selecionado
    if (!selectedServer || allFiles.length === 0) {
      return;
    }

    const serverHostname = selectedServer.split(':')[0];
    const filteredFiles = allFiles.filter(f => f.host.includes(serverHostname));

    if (filteredFiles.length > 0) {
      // IMPORTANTE: Só auto-selecionar se não houver arquivo selecionado
      // Isso previne sobrescrever seleção manual do usuário
      if (!selectedFile) {
        const prometheusFile = filteredFiles.find(f => f.filename === 'prometheus.yml');
        if (prometheusFile) {
          setSelectedFile(prometheusFile.path);
        } else {
          setSelectedFile(filteredFiles[0].path);
        }
      }
    } else {
      // Servidor não tem arquivos, limpar seleção
      setSelectedFile(null);
    }
    // CORREÇÃO: Adicionar selectedServer nas dependências pois é usado na lógica
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [allFiles, selectedServer]); // Monitorar ambos: allFiles E selectedServer

  const handleReload = async () => {
    // CRÍTICO: Garantir que servidor está selecionado antes de recarregar
    if (!selectedServer) {
      message.warning('Selecione um servidor primeiro');
      return;
    }

    try {
      // CRÍTICO: Limpar cache do backend primeiro
      const hideLoading = message.loading('Limpando cache e recarregando...', 0);

      await axios.post(`${API_URL}/prometheus-config/clear-cache`);

      // Recarregar dados (fetchFiles já valida selectedServer internamente)
      await fetchFiles();

      // CORREÇÃO: Só recarregar fields se estiver na aba de Campos Metadata
      if (activeTabKey === 'fields') {
        reloadFields();
      }

      if (selectedFile) {
        await fetchJobs(selectedFile, selectedServer);
      }

      hideLoading();
      message.success('Dados recarregados com sucesso!', 2);
    } catch (error: any) {
      console.error('Erro ao recarregar:', error);
      message.error('Erro ao recarregar dados');
    }
  };

  const handleEditJob = useCallback((job: any) => {
    setEditingJob(job);
    setEditingJobData(job);
    setJsonError(null); // Reset JSON error

    // Configurar form baseado no tipo
    if (fileType === 'prometheus') {
      form.setFieldsValue({
        job_name: job.job_name,
        scrape_interval: job.scrape_interval,
        metrics_path: job.metrics_path,
      });
    } else if (fileType === 'blackbox') {
      form.setFieldsValue({
        module_name: job.module_name,
        prober: job.prober,
        timeout: job.timeout,
      });
    } else {
      form.setFieldsValue({
        name: job.name || job[itemKey],
      });
    }

    setDrawerVisible(true);
  }, [fileType, itemKey, form]);

  // ============================================================================
  // FUNÇÕES PARA EDIÇÃO DIRETA COM MONACO EDITOR
  // ============================================================================

  /**
   * DESCONTINUADO: handleSaveJob, handleDeleteJob, handleAddJob
   *
   * Essas funções foram removidas. Toda edição agora é feita via Monaco Editor.
   */

  /**
   * DEPRECATED - não mais usado
   */
  const handleSaveJob_DEPRECATED = async () => {
    // Validar JSON antes de salvar
    if (jsonError) {
      message.error('Corrija os erros de sintaxe JSON antes de salvar');
      return;
    }

    try {
      await form.validateFields();

      // Usar editingJobData que contém o job completo editado no JSON
      const jobToSave = editingJobData;

      let updatedJobs;
      if (editingJob) {
        // Editar item existente
        updatedJobs = jobs.map(j => j[itemKey] === editingJob[itemKey] ? jobToSave : j);
      } else {
        // Adicionar novo job
        updatedJobs = [...jobs, jobToSave];
      }

      // VALIDAÇÃO CRÍTICA: Verificar se não estamos perdendo jobs
      if (jobs.length > 1 && updatedJobs.length === 1) {
        Modal.error({
          title: '⚠️ Erro Crítico Detectado',
          content: (
            <div>
              <p><strong>PERDA DE DADOS EVITADA!</strong></p>
              <p style={{ marginTop: 12 }}>
                O sistema detectou que esta operação iria DELETAR {jobs.length - 1} jobs do arquivo!
              </p>
              <p style={{ marginTop: 12, color: 'red' }}>
                <strong>Original:</strong> {jobs.length} jobs<br />
                <strong>Seria salvo:</strong> {updatedJobs.length} job(s)
              </p>
              <p style={{ marginTop: 12 }}>
                Por favor, recarregue a página (F5) e tente novamente.
              </p>
            </div>
          ),
          width: 600,
        });
        return; // Abortar salvamento
      }

      // Mostrar modal de progresso
      setSavingInProgress(true);

      const response = await axios.put(
        `${API_URL}/prometheus-config/file/jobs?file_path=${encodeURIComponent(selectedFile!)}`,
        updatedJobs,
        {
          timeout: 30000, // 30 segundos para operações SSH
        }
      );

      // Fechar modal de progresso
      setSavingInProgress(false);

      // CRÍTICO: Atualizar estado IMEDIATAMENTE para prevenir corrupção
      setJobs(updatedJobs);

      // IMPORTANTE: Fechar drawer e limpar estado
      setDrawerVisible(false);
      setEditingJob(null);
      setEditingJobData(null);
      setJsonError(null);
      form.resetFields();

      // Salvar resultado e abrir modal customizado
      setSaveResult({
        file: selectedFile,
        total: response.data.total,
        updatedJobs: updatedJobs,
      });
      setSaveSuccess(true);

      // Mensagem grande e visível
      message.success({
        content: `✅ SALVO COM SUCESSO! ${response.data.total} jobs atualizados. Clique para ver detalhes.`,
        duration: 10,
        style: {
          marginTop: '20vh',
          fontSize: 16,
          fontWeight: 'bold',
        },
        onClick: () => setSaveSuccess(true),
      });
    } catch (err: any) {
      // Fechar modal de progresso se houver erro
      setSavingInProgress(false);

      // Tratar erros de validação do promtool
      if (err.response?.status === 400 && err.response?.data?.validation_errors) {
        const validationErrors = err.response.data.validation_errors;
        const errorMessage = err.response.data.message || 'Validação falhou';

        Modal.error({
          title: 'Erro de Validação do Promtool',
          content: (
            <div>
              <p>{errorMessage}</p>
              <ul style={{ marginTop: 16, paddingLeft: 20 }}>
                {validationErrors.map((error: string, index: number) => (
                  <li key={index} style={{ marginBottom: 8 }}>
                    <Text type="danger">{error}</Text>
                  </li>
                ))}
              </ul>
              {err.response.data.output && (
                <div style={{ marginTop: 16 }}>
                  <Text type="secondary">Output completo:</Text>
                  <pre style={{
                    marginTop: 8,
                    padding: 8,
                    background: '#f5f5f5',
                    overflow: 'auto',
                    maxHeight: 200
                  }}>
                    {err.response.data.output}
                  </pre>
                </div>
              )}
            </div>
          ),
          width: 600,
        });
      } else {
        // Outros erros
        const errorMsg = typeof err.response?.data?.detail === 'string'
          ? err.response.data.detail
          : err.response?.data?.message || 'Erro ao salvar job';
        message.error(errorMsg);
      }
    }
  };

  // ============================================================================
  // FUNÇÕES PARA EDIÇÃO DIRETA COM MONACO EDITOR
  // ============================================================================

  /**
   * Abre o Monaco Editor com o conteúdo RAW do arquivo.
   *
   * Carrega o arquivo diretamente do servidor via SSH, preservando
   * 100% da formatação e comentários originais.
   */
  const handleOpenMonacoEditor = async () => {
    if (!selectedFile) {
      message.warning('Selecione um arquivo primeiro');
      return;
    }

    if (!selectedServer) {
      message.warning('Servidor não selecionado');
      return;
    }

    setMonacoLoading(true);
    setMonacoEditorVisible(true);

    try {
      // CRÍTICO: Extrair hostname do selectedServer para garantir que abre arquivo do servidor correto
      // selectedServer tem formato: "172.16.1.26:5522" -> extrair apenas "172.16.1.26"
      const hostname = selectedServer.split(':')[0];

      const response = await consulAPI.getRawFileContent(selectedFile, hostname);

      setMonacoContent(response.data.content);
      setMonacoOriginalContent(response.data.content);
      setMonacoFileInfo(response.data);
      setMonacoValidationError(null);

      message.success(`Arquivo carregado do servidor ${hostname}`);
    } catch (error: any) {
      console.error('[MONACO] Erro ao carregar arquivo:', error);
      const errorMsg = error.response?.data?.detail || 'Erro ao carregar arquivo';
      message.error(errorMsg);

      // Fechar modal se falhar
      setMonacoEditorVisible(false);
    } finally {
      setMonacoLoading(false);
    }
  };

  /**
   * Valida sintaxe YAML em tempo real enquanto o usuário edita.
   *
   * Usa js-yaml para parse client-side e mostra erros no editor.
   */
  const handleMonacoChange = (value: string | undefined) => {
    if (!value) {
      setMonacoContent('');
      return;
    }

    setMonacoContent(value);

    // Validar sintaxe YAML em tempo real
    try {
      yaml.load(value);
      setMonacoValidationError(null); // YAML válido
    } catch (error: any) {
      // Erro de sintaxe YAML
      const errorMsg = `Linha ${error.mark?.line || '?'}, Coluna ${error.mark?.column || '?'}: ${error.reason || error.message}`;
      setMonacoValidationError(errorMsg);
    }
  };

  /**
   * Salva o conteúdo editado diretamente no arquivo via SSH.
   *
   * FLUXO:
   * 1. Valida sintaxe YAML
   * 2. Envia para backend
   * 3. Backend cria backup, valida com promtool, salva
   * 4. Mostra resultado ao usuário
   */
  const handleSaveMonacoEditor = async () => {
    if (!selectedFile || !monacoFileInfo) {
      message.error('Arquivo não carregado');
      return;
    }

    // VALIDAÇÃO 1: Verificar se houve mudanças
    if (monacoContent === monacoOriginalContent) {
      message.info('Nenhuma mudança detectada');
      return;
    }

    // VALIDAÇÃO 2: Verificar sintaxe YAML
    if (monacoValidationError) {
      modal.error({
        title: 'Erro de Sintaxe YAML',
        content: monacoValidationError,
      });
      return;
    }

    // Determinar se é arquivo prometheus.yml
    const isPrometheusFile = selectedFile.toLowerCase().includes('prometheus.yml');

    // Resetar estados de progresso e abrir modal
    setCurrentStep(0);
    setStepStatus({
      0: 'wait',
      1: 'wait',
      2: 'wait',
      3: 'wait',
      4: 'wait',
    });
    setStepMessages({
      0: '',
      1: '',
      2: '',
      3: '',
      4: '',
    });
    setProgressVisible(true);
    setMonacoSaving(true);

    try {
      // STEP 0: Validar sintaxe YAML (cliente)
      setCurrentStep(0);
      setStepStatus(prev => ({ ...prev, 0: 'process' }));
      setStepMessages(prev => ({ ...prev, 0: 'Validando sintaxe YAML no cliente...' }));

      try {
        yaml.load(monacoContent);
        setStepStatus(prev => ({ ...prev, 0: 'finish' }));
        setStepMessages(prev => ({ ...prev, 0: 'Sintaxe YAML válida ✓' }));
      } catch (error: any) {
        setStepStatus(prev => ({ ...prev, 0: 'error' }));
        setStepMessages(prev => ({ ...prev, 0: `Erro de sintaxe: ${error.message}` }));
        throw error;
      }

      // STEP 1: Salvar arquivo (backend faz backup + validação + save)
      setCurrentStep(1);
      setStepStatus(prev => ({ ...prev, 1: 'process' }));
      setStepMessages(prev => ({ ...prev, 1: 'Enviando arquivo para servidor...' }));

      // Extrair hostname do monacoFileInfo.host (formato: "root@172.16.1.26:5522" -> "172.16.1.26")
      const hostname = monacoFileInfo.host.split('@')[1]?.split(':')[0] || monacoFileInfo.host;

      const response = await consulAPI.saveRawFileContent({
        file_path: selectedFile,
        content: monacoContent,
        hostname: hostname, // CRÍTICO: passar hostname para salvar no servidor correto!
      });

      setStepStatus(prev => ({ ...prev, 1: 'finish' }));
      setStepMessages(prev => ({
        ...prev,
        1: `Arquivo salvo com sucesso! Backup: ${response.data.backup_path?.split('/').pop() || 'N/A'}`
      }));

      // STEP 2: Validação Promtool (apenas para prometheus.yml)
      if (isPrometheusFile && response.data.validation_result) {
        setCurrentStep(2);
        setStepStatus(prev => ({ ...prev, 2: 'process' }));
        setStepMessages(prev => ({ ...prev, 2: 'Validando configuração com promtool...' }));

        if (response.data.validation_result.valid) {
          setStepStatus(prev => ({ ...prev, 2: 'finish' }));
          setStepMessages(prev => ({ ...prev, 2: 'Configuração validada com promtool ✓' }));
        } else {
          setStepStatus(prev => ({ ...prev, 2: 'error' }));
          setStepMessages(prev => ({ ...prev, 2: `Falha na validação: ${response.data.validation_result.message}` }));
          throw new Error('Validação promtool falhou');
        }
      } else {
        // Marcar apenas step 2 como não aplicável (steps 3 e 4 SEMPRE executam para reload)
        setStepStatus(prev => ({ ...prev, 2: 'wait' }));
        setStepMessages(prev => ({ ...prev, 2: 'Não aplicável para este arquivo' }));
      }

      // STEP 3: Recarregar serviços (SEMPRE - backend decide quais serviços baseado no arquivo)
      setCurrentStep(3);
      setStepStatus(prev => ({ ...prev, 3: 'process' }));

      // Mensagem dinâmica baseada no tipo de arquivo
      let reloadMessage = 'Recarregando Prometheus...';
      if (selectedFile.toLowerCase().includes('blackbox')) {
        reloadMessage = 'Recarregando Blackbox Exporter e Prometheus...';
      } else if (selectedFile.toLowerCase().includes('alertmanager')) {
        reloadMessage = 'Recarregando Alertmanager...';
      }
      setStepMessages(prev => ({ ...prev, 3: reloadMessage }));

      try {
        const reloadResponse = await consulAPI.reloadService(monacoFileInfo.host, selectedFile);

        // Separar serviços por tipo: falhados, ignorados (não instalados), processados
        const failedServices = reloadResponse.data.services.filter(s => !s.success && s.method !== 'skipped');
        const skippedServices = reloadResponse.data.services.filter(s => s.method === 'skipped');
        const processedServices = reloadResponse.data.services.filter(s => s.success && s.method !== 'skipped');

        if (failedServices.length > 0) {
          // Algum serviço falhou (erro real)
          setStepStatus(prev => ({ ...prev, 3: 'error' }));
          const errorMsg = failedServices.map(s => `${s.service}: ${s.error || 'falhou'}`).join(', ');
          setStepMessages(prev => ({ ...prev, 3: `Falha ao recarregar: ${errorMsg}` }));

          setStepStatus(prev => ({ ...prev, 4: 'error' }));
          setStepMessages(prev => ({ ...prev, 4: 'Status não verificado devido a falhas anteriores' }));
        } else {
          // Sucesso (incluindo serviços ignorados)
          let successMsg = '';

          if (processedServices.length > 0) {
            const processedNames = processedServices.map(s => s.service).join(', ');
            successMsg = `Serviços recarregados: ${processedNames}`;
          }

          if (skippedServices.length > 0) {
            const skippedMsg = skippedServices
              .map(s => `${s.service}: não instalado neste servidor (ignorado)`)
              .join(', ');

            if (successMsg) {
              successMsg += `\n${skippedMsg}`;
            } else {
              successMsg = skippedMsg;
            }
          }

          setStepStatus(prev => ({ ...prev, 3: 'finish' }));
          setStepMessages(prev => ({ ...prev, 3: successMsg }));

          // STEP 4: Verificar status dos serviços (apenas os processados, não os skipped)
          setCurrentStep(4);
          setStepStatus(prev => ({ ...prev, 4: 'process' }));
          setStepMessages(prev => ({ ...prev, 4: 'Verificando status dos serviços...' }));

          if (processedServices.length === 0) {
            // Todos foram skipped, nada para verificar
            setStepStatus(prev => ({ ...prev, 4: 'finish' }));
            setStepMessages(prev => ({ ...prev, 4: 'Nenhum serviço para verificar (todos ignorados)' }));
          } else {
            // Verificar status apenas dos serviços processados
            const allActive = processedServices.every(s => s.status === 'active' || s.status === 'not_installed');
            if (allActive) {
              const statusMsg = processedServices
                .map(s => `${s.service}: ${s.status}`)
                .join(', ');
              setStepStatus(prev => ({ ...prev, 4: 'finish' }));
              setStepMessages(prev => ({ ...prev, 4: `Serviços ativos ✓ (${statusMsg})` }));
            } else {
              const statusMsg = processedServices
                .map(s => `${s.service}: ${s.status}`)
                .join(', ');
              setStepStatus(prev => ({ ...prev, 4: 'error' }));
              setStepMessages(prev => ({ ...prev, 4: `Status dos serviços: ${statusMsg}` }));
            }
          }
        }

      } catch (reloadError: any) {
        console.error('[MONACO] Erro ao recarregar serviço:', reloadError);
        setStepStatus(prev => ({ ...prev, 3: 'error' }));
        setStepMessages(prev => ({
          ...prev,
          3: reloadError.response?.data?.detail || 'Erro ao recarregar serviço'
        }));

        setStepStatus(prev => ({ ...prev, 4: 'error' }));
        setStepMessages(prev => ({ ...prev, 4: 'Não foi possível verificar status' }));
      }

      // Sucesso - atualizar estados
      setMonacoSaving(false);
      setMonacoOriginalContent(monacoContent);

      // Recarregar dados da página
      await fetchJobs(selectedFile, selectedServer);

    } catch (error: any) {
      console.error('[MONACO] Erro geral:', error);

      // Marcar steps restantes como erro
      setStepStatus(prev => {
        const newStatus = { ...prev };
        for (let i = 0; i <= 4; i++) {
          if (prev[i] === 'wait' || prev[i] === 'process') {
            newStatus[i] = 'error';
          }
        }
        return newStatus;
      });

      // Não fechar modal automaticamente em caso de erro
      setMonacoSaving(false);
    }
  };

  const handleAddJob = () => {
    setEditingJob(null);
    setJsonError(null); // Reset JSON error

    // Criar estrutura inicial baseada no tipo
    let newItem: any = {};

    if (fileType === 'prometheus') {
      newItem = {
        job_name: '',
        scrape_interval: '30s',
        metrics_path: '/metrics',
        relabel_configs: [],
      };
      form.setFieldsValue({
        job_name: '',
        scrape_interval: '30s',
        metrics_path: '/metrics',
      });
    } else if (fileType === 'blackbox') {
      newItem = {
        module_name: '',
        prober: 'http',
        timeout: '5s',
        http: {},
      };
      form.setFieldsValue({
        module_name: '',
        prober: 'http',
        timeout: '5s',
      });
    } else if (fileType === 'alertmanager') {
      newItem = {
        name: '',
        webhook_configs: [],
      };
      form.setFieldsValue({ name: '' });
    } else {
      newItem = { name: '' };
      form.setFieldsValue({ name: '' });
    }

    setEditingJobData(newItem);
    form.resetFields();
    setDrawerVisible(true);
  };

  // Presets de colunas dinâmicos baseados no tipo de arquivo (padrão Blackbox)
  const getColumnPresets = useCallback((): ColumnConfig[] => {
    if (fileType === 'prometheus') {
      return [
        { key: 'job_name', title: 'Job Name', visible: true, locked: true },
        { key: 'scrape_interval', title: 'Intervalo Scrape', visible: true },
        { key: 'metrics_path', title: 'Path', visible: true },
        { key: 'consul_server', title: 'Consul Server', visible: true },
        { key: 'consul_services', title: 'Services Consul', visible: true },
        { key: 'consul_token', title: 'Token Consul', visible: false },
        { key: 'target_mapping', title: 'Target Mapping', visible: true },
        { key: 'actions', title: 'Ações', visible: true, locked: true },
      ];
    } else if (fileType === 'rules') {
      if (alertViewMode === 'group') {
        return [
          { key: 'name', title: 'Name', visible: true, locked: true },
          { key: 'interval', title: 'Intervalo', visible: true },
          { key: 'rules_count', title: 'Total Regras', visible: true },
          { key: 'alerts_detail', title: 'Alertas Configurados', visible: true },
          { key: 'actions', title: 'Ações', visible: true, locked: true },
        ];
      } else {
        // Visão individual
        return [
          { key: 'name', title: 'Alerta', visible: true, locked: true },
          { key: 'group', title: 'Grupo', visible: true },
          { key: 'severity', title: 'Severity', visible: true },
          { key: 'for', title: 'For', visible: true },
          { key: 'summary', title: 'Resumo', visible: true },
          { key: 'description', title: 'Description', visible: true },
          { key: 'expr', title: 'Expression', visible: true },
          { key: 'actions', title: 'Ações', visible: true, locked: true },
        ];
      }
    } else if (fileType === 'blackbox') {
      return [
        { key: 'module_name', title: 'Module Name', visible: true, locked: true },
        { key: 'prober', title: 'Prober', visible: true },
        { key: 'timeout', title: 'Timeout', visible: true },
        { key: 'config', title: 'Configuração', visible: true },
        { key: 'actions', title: 'Ações', visible: true, locked: true },
      ];
    } else if (fileType === 'alertmanager') {
      // Colunas dinâmicas baseadas na visão do Alertmanager
      switch (alertmanagerViewMode) {
        case 'routes':
          return [
            { key: 'match_pattern', title: 'Match Pattern', visible: true, locked: true },
            { key: 'receiver', title: 'Receiver', visible: true },
            { key: 'group_by', title: 'Group By', visible: true },
            { key: 'group_wait', title: 'Group Wait', visible: true },
            { key: 'repeat_interval', title: 'Repeat Interval', visible: true },
            { key: 'continue', title: 'Continue', visible: true },
            { key: 'actions', title: 'Ações', visible: true, locked: true },
          ];
        case 'receivers':
          return [
            { key: 'name', title: 'Nome', visible: true, locked: true },
            { key: 'types', title: 'Tipos', visible: true },
            { key: 'targets', title: 'Destinos', visible: true },
            { key: 'send_resolved', title: 'Send Resolved', visible: true },
            { key: 'max_alerts', title: 'Max Alerts', visible: true },
            { key: 'actions', title: 'Ações', visible: true, locked: true },
          ];
        case 'inhibit-rules':
          return [
            { key: 'source_pattern', title: 'Source Alert', visible: true, locked: true },
            { key: 'target_pattern', title: 'Target Alert', visible: true },
            { key: 'equal', title: 'Equal Labels', visible: true },
            { key: 'actions', title: 'Ações', visible: true, locked: true },
          ];
        default:
          return [
            { key: 'name', title: 'Name', visible: true, locked: true },
            { key: 'actions', title: 'Ações', visible: true, locked: true },
          ];
      }
    }
    return [
      { key: 'name', title: 'Name', visible: true, locked: true },
      { key: 'actions', title: 'Ações', visible: true, locked: true },
    ];
  }, [fileType, alertViewMode, alertmanagerViewMode]);

  // Atualizar columnConfig quando o tipo de arquivo ou modo de visão mudar
  useEffect(() => {
    setColumnConfig(getColumnPresets());
  }, [fileType, alertViewMode, alertmanagerViewMode, getColumnPresets]);

  // NOVO: Colunas dinâmicas baseadas no tipo de arquivo
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const getColumnsForType = useCallback((): ProColumns<any>[] => {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const baseColumns: ProColumns<any>[] = [];

    // Primeira coluna: Nome do item (job_name, module_name, name)
    // CORREÇÃO: Não adicionar coluna genérica para Alertmanager (já tem colunas específicas)
    if (fileType !== 'alertmanager') {
      baseColumns.push({
        title: itemKey === 'job_name' ? 'Job Name' : itemKey === 'module_name' ? 'Module Name' : 'Name',
        dataIndex: itemKey,
        key: itemKey,
        width: 200,
        fixed: 'left',
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        render: (_: any, record: any) => (
          <Text strong style={{ fontSize: 13 }}>
            {record[itemKey]}
          </Text>
        ),
      });
    }

    // Colunas específicas por tipo
    if (fileType === 'prometheus') {
      baseColumns.push(
        {
          title: 'Intervalo Scrape',
          dataIndex: 'scrape_interval',
          key: 'scrape_interval',
          width: 120,
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          render: (_: any, record: any) => (
            <Tag color="blue" icon={<ClockCircleOutlined />}>
              {record.scrape_interval || '15s'}
            </Tag>
          ),
        },
        {
          title: 'Path',
          dataIndex: 'metrics_path',
          key: 'metrics_path',
          width: 130,
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          render: (_: any, record: any) => (
            <code style={{ fontSize: 12 }}>{record.metrics_path || '/metrics'}</code>
          ),
        },
        {
          title: 'Consul Server',
          dataIndex: 'consul_sd_configs',
          key: 'consul_server',
          width: 200,
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          render: (_: any, record: any) => {
            const configs = record.consul_sd_configs;
            if (!configs || configs.length === 0) return <Tag>Sem Consul SD</Tag>;
            const config = configs[0];
            return (
              <Tooltip title={`Server completo: ${config.server}`}>
                <Tag color="green" icon={<CloudServerOutlined />}>
                  {config.server}
                </Tag>
              </Tooltip>
            );
          },
        },
        {
          title: 'Services Consul',
          dataIndex: 'consul_sd_configs',
          key: 'consul_services',
          width: 220,
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          render: (_: any, record: any) => {
            const configs = record.consul_sd_configs;
            if (!configs || configs.length === 0) return <Tag>-</Tag>;
            const config = configs[0];
            const services = config.services || [];

            if (services.length === 0) return <Tag>Todos os serviços</Tag>;

            return (
              <Space size={4} wrap>
                {services.slice(0, 2).map((svc: string, idx: number) => (
                  <Tag key={idx} color="cyan" style={{ fontSize: 11 }}>
                    {svc}
                  </Tag>
                ))}
                {services.length > 2 && (
                  <Tooltip title={services.slice(2).join(', ')}>
                    <Tag color="default" style={{ fontSize: 11 }}>
                      +{services.length - 2}
                    </Tag>
                  </Tooltip>
                )}
              </Space>
            );
          },
        },
        {
          title: 'Token Consul',
          dataIndex: 'consul_sd_configs',
          key: 'consul_token',
          width: 140,
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          render: (_: any, record: any) => {
            const configs = record.consul_sd_configs;
            if (!configs || configs.length === 0) return <Tag>-</Tag>;
            const config = configs[0];
            const token = config.token || '';

            if (!token) return <Tag color="orange">Sem token</Tag>;

            // Truncar token para exibição (primeiros e últimos 4 caracteres)
            const truncated = token.length > 12
              ? `${token.substring(0, 6)}...${token.substring(token.length - 4)}`
              : token;

            return (
              <Tooltip title={`Token completo: ${token}`}>
                <Tag color="purple" style={{ fontFamily: 'monospace', fontSize: 11 }}>
                  {truncated}
                </Tag>
              </Tooltip>
            );
          },
        },
        {
          title: 'Target Mapping',
          dataIndex: 'relabel_configs',
          key: 'target_mapping',
          width: 250,
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          render: (_: any, record: any) => {
            const relabelConfigs = record.relabel_configs;
            if (!relabelConfigs || relabelConfigs.length === 0) {
              return <Tag>Sem mapeamento</Tag>;
            }

            // Procurar configurações de target_label e replacement
            const targetConfigs = relabelConfigs.filter(
              (rc: any) => rc.target_label && rc.replacement
            );

            if (targetConfigs.length === 0) {
              return <Badge count={relabelConfigs.length} style={{ backgroundColor: '#52c41a' }} />;
            }

            // Melhor visualização: mostrar de forma mais compacta e legível
            const mainMapping = targetConfigs[0];

            return (
              <Tooltip
                title={
                  <div>
                    <div style={{ marginBottom: 8, fontWeight: 'bold' }}>
                      Configurações de Mapeamento ({relabelConfigs.length} total)
                    </div>
                    {targetConfigs.map((rc: any, idx: number) => (
                      <div key={idx} style={{
                        marginBottom: 8,
                        padding: 8,
                        background: 'rgba(255,255,255,0.1)',
                        borderRadius: 4
                      }}>
                        <div><strong>Target:</strong> {rc.target_label}</div>
                        <div><strong>Replacement:</strong> {rc.replacement}</div>
                        {rc.source_labels && (
                          <div><strong>Source:</strong> {rc.source_labels.join(', ')}</div>
                        )}
                        {rc.action && (
                          <div><strong>Action:</strong> {rc.action}</div>
                        )}
                      </div>
                    ))}
                    {relabelConfigs.length > targetConfigs.length && (
                      <div style={{ marginTop: 8, opacity: 0.7 }}>
                        +{relabelConfigs.length - targetConfigs.length} outras configurações
                      </div>
                    )}
                  </div>
                }
              >
                <Space size={4} wrap>
                  <Badge
                    count={relabelConfigs.length}
                    style={{ backgroundColor: '#52c41a' }}
                    showZero
                  />
                  {mainMapping && (
                    <>
                      <Text code style={{ fontSize: 11 }}>
                        {mainMapping.target_label}
                      </Text>
                      <Text type="secondary" style={{ fontSize: 11 }}>→</Text>
                      <Text code style={{ fontSize: 11 }}>
                        {mainMapping.replacement}
                      </Text>
                    </>
                  )}
                </Space>
              </Tooltip>
            );
          },
        }
      );
    } else if (fileType === 'blackbox') {
      baseColumns.push(
        {
          title: 'Prober',
          dataIndex: 'prober',
          key: 'prober',
          width: 100,
          render: (text: string) => <Tag color="orange">{text}</Tag>,
        },
        {
          title: 'Timeout',
          dataIndex: 'timeout',
          key: 'timeout',
          width: 100,
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          render: (_: any, record: any) => (
            <Tag color="blue" icon={<ClockCircleOutlined />}>
              {record.timeout}
            </Tag>
          ),
        },
        {
          title: 'Configuração',
          key: 'config',
          width: 200,
          render: (_: any, record: any) => {
            const configKey = record.prober; // http, icmp, tcp
            const config = record[configKey];
            if (!config) return <Tag>Sem config</Tag>;

            const keys = Object.keys(config);

            return (
              <Tooltip
                title={
                  <pre style={{ margin: 0, fontSize: 11 }}>
                    {JSON.stringify(config, null, 2)}
                  </pre>
                }
              >
                <Space size={4}>
                  <Tag color="blue">{keys.length} propriedades</Tag>
                  {config.method && <Tag color="green">{config.method}</Tag>}
                  {config.preferred_ip_protocol && (
                    <Tag color="cyan">IPv{config.preferred_ip_protocol}</Tag>
                  )}
                </Space>
              </Tooltip>
            );
          },
        }
      );
    } else if (fileType === 'alertmanager') {
      // Colunas dinâmicas baseadas na visão selecionada
      if (alertmanagerViewMode === 'routes') {
        // VISÃO: ROTAS
        baseColumns.push(
          {
            title: 'Match Pattern',
            dataIndex: 'match_pattern',
            key: 'match_pattern',
            width: 250,
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            render: (_: any, record: any) => (
              <Space direction="vertical" size={2}>
                <Text strong>{record.match_pattern}</Text>
                {record.match_type === 'regex' && (
                  <Tag color="purple" style={{ fontSize: 10 }}>REGEX</Tag>
                )}
              </Space>
            ),
          },
          {
            title: 'Receiver',
            dataIndex: 'receiver',
            key: 'receiver',
            width: 180,
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            render: (_: any, record: any) => (
              <Tag color="blue" icon={<CloudServerOutlined />}>
                {record.receiver}
              </Tag>
            ),
          },
          {
            title: 'Group By',
            dataIndex: 'group_by',
            key: 'group_by',
            width: 200,
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            render: (_: any, record: any) => (
              record.group_by?.length > 0 ? (
                <Space size={4} wrap>
                  {record.group_by.map((label: string, idx: number) => (
                    <Tag key={idx} color="cyan">{label}</Tag>
                  ))}
                </Space>
              ) : <Tag>Nenhum</Tag>
            ),
          },
          {
            title: 'Group Wait',
            dataIndex: 'group_wait',
            key: 'group_wait',
            width: 110,
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            render: (_: any, record: any) => record.group_wait ? <Tag color="orange">{record.group_wait}</Tag> : <Tag>Padrão</Tag>,
          },
          {
            title: 'Repeat Interval',
            dataIndex: 'repeat_interval',
            key: 'repeat_interval',
            width: 140,
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            render: (_: any, record: any) => record.repeat_interval ? <Tag color="green">{record.repeat_interval}</Tag> : <Tag>Padrão</Tag>,
          },
          {
            title: 'Continue',
            dataIndex: 'continue',
            key: 'continue',
            width: 90,
            align: 'center',
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            render: (_: any, record: any) => record.continue ? (
              <CheckCircleOutlined style={{ color: '#52c41a', fontSize: 16 }} />
            ) : (
              <CloseCircleOutlined style={{ color: '#d9d9d9', fontSize: 16 }} />
            ),
          }
        );
      } else if (alertmanagerViewMode === 'receivers') {
        // VISÃO: RECEPTORES
        baseColumns.push(
          {
            title: 'Nome',
            dataIndex: 'name',
            key: 'name',
            width: 200,
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            render: (_: any, record: any) => (
              <Text strong style={{ color: '#1890ff' }}>{record.name}</Text>
            ),
          },
          {
            title: 'Tipos',
            dataIndex: 'types',
            key: 'types',
            width: 250,
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            render: (_: any, record: any) => {
              const typeList = record.types.split(', ');
              return (
                <Space size={4} wrap>
                  {typeList.map((type: string, idx: number) => {
                    const color = type.includes('webhook') ? 'purple' :
                                  type.includes('email') ? 'green' :
                                  type.includes('telegram') ? 'cyan' :
                                  type.includes('slack') ? 'orange' : 'default';
                    return <Tag key={idx} color={color}>{type}</Tag>;
                  })}
                </Space>
              );
            },
          },
          {
            title: 'Destinos',
            dataIndex: 'targets',
            key: 'targets',
            width: 400,
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            render: (_: any, record: any) => (
              record.targets?.length > 0 ? (
                <Space direction="vertical" size={2} style={{ width: '100%' }}>
                  {record.targets.slice(0, 2).map((target: string, idx: number) => (
                    <Text key={idx} code copyable style={{ fontSize: 11 }}>
                      {target}
                    </Text>
                  ))}
                  {record.targets.length > 2 && (
                    <Text type="secondary" style={{ fontSize: 11 }}>
                      +{record.targets.length - 2} mais...
                    </Text>
                  )}
                </Space>
              ) : <Tag>Nenhum destino</Tag>
            ),
          },
          {
            title: 'Send Resolved',
            dataIndex: 'send_resolved',
            key: 'send_resolved',
            width: 130,
            align: 'center' as const,
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            render: (_: any, record: any) => (
              record.send_resolved === true ? (
                <CheckCircleOutlined style={{ color: '#52c41a', fontSize: 16 }} />
              ) : record.send_resolved === false ? (
                <CloseCircleOutlined style={{ color: '#ff4d4f', fontSize: 16 }} />
              ) : (
                <Tag>N/A</Tag>
              )
            ),
          },
          {
            title: 'Max Alerts',
            dataIndex: 'max_alerts',
            key: 'max_alerts',
            width: 110,
            align: 'center' as const,
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            render: (_: any, record: any) => (
              record.max_alerts ? (
                <Tag color="blue">{record.max_alerts}</Tag>
              ) : (
                <Tag>Ilimitado</Tag>
              )
            ),
          }
        );
      } else if (alertmanagerViewMode === 'inhibit-rules') {
        // VISÃO: REGRAS DE INIBIÇÃO
        baseColumns.push(
          {
            title: 'Source Alert',
            dataIndex: 'source_pattern',
            key: 'source_pattern',
            width: 280,
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            render: (_: any, record: any) => (
              <Space direction="vertical" size={2}>
                <Text strong style={{ color: '#ff4d4f' }}>{record.source_pattern}</Text>
                {record.source_type === 'regex' && (
                  <Tag color="purple" style={{ fontSize: 10 }}>REGEX</Tag>
                )}
              </Space>
            ),
          },
          {
            title: 'Target Alert',
            dataIndex: 'target_pattern',
            key: 'target_pattern',
            width: 280,
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            render: (_: any, record: any) => (
              <Space direction="vertical" size={2}>
                <Text>{record.target_pattern}</Text>
                {record.target_type === 'regex' && (
                  <Tag color="purple" style={{ fontSize: 10 }}>REGEX</Tag>
                )}
              </Space>
            ),
          },
          {
            title: 'Equal Labels',
            dataIndex: 'equal',
            key: 'equal',
            width: 200,
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            render: (_: any, record: any) => (
              record.equal?.length > 0 ? (
                <Space size={4} wrap>
                  {record.equal.map((label: string, idx: number) => (
                    <Tag key={idx} color="geekblue" icon={<DatabaseOutlined />}>
                      {label}
                    </Tag>
                  ))}
                </Space>
              ) : <Tag>Nenhum</Tag>
            ),
          }
        );
      }
    } else if (fileType === 'rules') {
      // Visão por grupo (padrão)
      if (alertViewMode === 'group') {
        baseColumns.push(
          {
            title: 'Intervalo',
            dataIndex: 'interval',
            key: 'interval',
            width: 100,
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            render: (_: any, record: any) => record.interval ? (
              <Tag color="blue" icon={<ClockCircleOutlined />}>
                {record.interval}
              </Tag>
            ) : <Tag>Padrão</Tag>,
          },
          {
            title: 'Total Regras',
            dataIndex: 'rules',
            key: 'rules_count',
            width: 110,
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            render: (_: any, record: any) => {
              const rules = record.rules || [];
              return rules.length > 0 ? (
                <Badge count={rules.length} showZero style={{ backgroundColor: '#ff4d4f' }} />
              ) : (
                <Tag>0</Tag>
              );
            },
          },
          {
            title: 'Alertas Configurados',
            key: 'alerts_detail',
            width: 500,
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            render: (_: any, record: any) => {
            const alerts = record.rules?.filter((r: any) => r.alert) || [];
            if (alerts.length === 0) return <Tag>Nenhum alerta</Tag>;

            return (
              <Space direction="vertical" size={6} style={{ width: '100%' }}>
                {alerts.slice(0, 3).map((alert: any, idx: number) => (
                  <div
                    key={idx}
                    style={{
                      padding: '6px 8px',
                      background: '#fafafa',
                      borderRadius: 4,
                      border: '1px solid #f0f0f0'
                    }}
                  >
                    <Space size={8} wrap style={{ marginBottom: 4 }}>
                      <Tag color="red" style={{ margin: 0 }}>
                        {alert.alert}
                      </Tag>
                      {alert.labels?.severity && (
                        <Tag
                          color={
                            alert.labels.severity === 'critical' ? 'red' :
                            alert.labels.severity === 'warning' ? 'orange' :
                            'blue'
                          }
                          style={{ margin: 0 }}
                        >
                          {alert.labels.severity}
                        </Tag>
                      )}
                      {alert.for && (
                        <Tag color="blue" icon={<ClockCircleOutlined />} style={{ margin: 0 }}>
                          {alert.for}
                        </Tag>
                      )}
                    </Space>

                    {alert.annotations?.summary && (
                      <div style={{ fontSize: 11, color: '#595959', marginBottom: 2 }}>
                        <strong>Resumo:</strong> {alert.annotations.summary}
                      </div>
                    )}

                    {alert.expr && (
                      <Tooltip title={alert.expr}>
                        <code
                          style={{
                            fontSize: 10,
                            color: '#1890ff',
                            display: 'block',
                            overflow: 'hidden',
                            textOverflow: 'ellipsis',
                            whiteSpace: 'nowrap',
                            maxWidth: '450px'
                          }}
                        >
                          expr: {alert.expr}
                        </code>
                      </Tooltip>
                    )}
                  </div>
                ))}
                {alerts.length > 3 && (
                  <Tag color="default">
                    +{alerts.length - 3} alertas adicionais (clique em "Visualizar" para ver todos)
                  </Tag>
                )}
              </Space>
            );
          },
        }
      );
      } else {
        // Visão individual: mostrar cada alerta como linha separada
        baseColumns.push(
          {
            title: 'Grupo',
            dataIndex: '_group_name',
            key: 'group',
            width: 150,
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            render: (_: any, record: any) => (
              <Tag color="purple">{record._group_name}</Tag>
            ),
          },
          {
            title: 'Severity',
            dataIndex: ['labels', 'severity'],
            key: 'severity',
            width: 120,
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            render: (_: any, record: any) => {
              const severity = record.labels?.severity;
              if (!severity) return <Tag>N/A</Tag>;
              return (
                <Tag
                  color={
                    severity === 'critical' ? 'red' :
                    severity === 'warning' ? 'orange' :
                    'blue'
                  }
                >
                  {severity}
                </Tag>
              );
            },
          },
          {
            title: 'For',
            dataIndex: 'for',
            key: 'for',
            width: 100,
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            render: (_: any, record: any) => record.for ? (
              <Tag color="blue" icon={<ClockCircleOutlined />}>
                {record.for}
              </Tag>
            ) : <Tag>-</Tag>,
          },
          {
            title: 'Resumo',
            dataIndex: ['annotations', 'summary'],
            key: 'summary',
            width: 300,
            ellipsis: {
              showTitle: false,
            },
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            render: (_: any, record: any) => {
              const summary = record.annotations?.summary || '-';
              return (
                <Tooltip
                  title={summary}
                  overlayStyle={{ maxWidth: 500 }}
                  overlayInnerStyle={{ whiteSpace: 'pre-wrap' }}
                >
                  <span>{summary}</span>
                </Tooltip>
              );
            },
          },
          {
            title: 'Description',
            dataIndex: ['annotations', 'description'],
            key: 'description',
            width: 400,
            ellipsis: {
              showTitle: false,
            },
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            render: (_: any, record: any) => {
              const description = record.annotations?.description || '-';
              return (
                <Tooltip
                  title={description}
                  overlayStyle={{ maxWidth: 600 }}
                  overlayInnerStyle={{ whiteSpace: 'pre-wrap' }}
                >
                  <Text type="secondary" style={{ fontSize: 12 }}>
                    {description}
                  </Text>
                </Tooltip>
              );
            },
          },
          {
            title: 'Expression',
            dataIndex: 'expr',
            key: 'expr',
            width: 400,
            ellipsis: {
              showTitle: false,
            },
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            render: (_: any, record: any) => {
              const expr = record.expr || '-';
              return (
                <Tooltip
                  title={<code style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-all' }}>{expr}</code>}
                  overlayStyle={{ maxWidth: 700 }}
                >
                  <code style={{ fontSize: 11 }}>{expr}</code>
                </Tooltip>
              );
            },
          }
        );
      }
    }

    // Coluna de ações (sempre no final)
    baseColumns.push({
      title: 'Ações',
      key: 'actions',
      width: 120,
      fixed: 'right',
      render: (_: any, record: any) => (
        <Tooltip title="Visualizar detalhes deste job em formato JSON">
          <Button
            type="primary"
            icon={<EyeOutlined />}
            onClick={() => handleEditJob(record)}
            size="small"
          >
            Visualizar
          </Button>
        </Tooltip>
      ),
    });

    return baseColumns;
  }, [itemKey, fileType, handleEditJob, alertViewMode, alertmanagerViewMode]);

  // Colunas visíveis com configuração e redimensionamento (padrão Blackbox)
  const visibleColumns = useMemo(() => {
    const allColumns = getColumnsForType();

    // Se columnConfig ainda está vazio, retornar todas as colunas
    if (columnConfig.length === 0) return allColumns;

    // IMPORTANTE: Verificar se columnConfig corresponde ao tipo de arquivo atual
    // Comparar a primeira coluna (exceto actions) para verificar compatibilidade
    const firstConfigKey = columnConfig.find(c => c.key !== 'actions')?.key;
    const firstColumnKey = allColumns.find(c => c.key !== 'actions')?.key;

    // Se as keys não correspondem, retornar todas as colunas (arquivo mudou de tipo)
    if (firstConfigKey && firstColumnKey && firstConfigKey !== firstColumnKey) {
      return allColumns;
    }

    // Filtrar apenas colunas visíveis baseado em columnConfig
    return columnConfig
      .filter(config => config.visible)
      .map(config => {
        const column = allColumns.find(col => col.key === config.key);
        if (!column) return null;

        // Aplicar largura redimensionada se existir
        const width = columnWidths[config.key] || column.width;

        return {
          ...column,
          width,
          onHeaderCell: () => ({
            width,
            onResize: handleResize(config.key),
          }),
        };
      })
      .filter(Boolean) as ProColumns<any>[];
  }, [columnConfig, columnWidths, handleResize, getColumnsForType]);

  // Colunas da tabela de campos
  const fieldsColumns = [
    {
      title: 'Campo',
      dataIndex: 'name',
      key: 'name',
      width: 200,
      render: (name: string) => <code>{name}</code>,
    },
    {
      title: 'Nome Exibição',
      dataIndex: 'display_name',
      key: 'display_name',
    },
    {
      title: 'Tipo',
      dataIndex: 'field_type',
      key: 'field_type',
      render: (type: string) => {
        const colors: Record<string, string> = {
          string: 'default',
          number: 'blue',
          boolean: 'green',
          select: 'purple',
        };
        return <Tag color={colors[type]}>{type}</Tag>;
      },
    },
    {
      title: 'Obrigatório',
      dataIndex: 'required',
      key: 'required',
      render: (required: boolean) =>
        required ? <Tag color="red">Sim</Tag> : <Tag>Não</Tag>,
    },
  ];

  return (
      <PageContainer
        title="Configurações do Prometheus"
        subTitle="Editar jobs, relabel_configs e campos metadata dinamicamente"
      >
      {/* Informações do Servidor - ALTURA FIXA 56px */}
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
                {loadingFiles ? (
                  <span style={{ color: '#999' }}>
                    <LoadingOutlined /> Carregando...
                  </span>
                ) : (
                  <span><strong>{files.length}</strong> arquivo(s)</span>
                )}
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

      {/* Seleção de Servidor e Arquivo - ALTURA FIXA 140px */}
      <Card style={{ marginBottom: 16, height: 140, overflow: 'hidden' }}>
        <Row gutter={[16, 16]} align="middle">
          {/* Coluna 1: Seletor de Servidor (40%) */}
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

          {/* Coluna 2: Seletor de Arquivo (35%) */}
          <Col xs={24} lg={8}>
            <Space direction="vertical" size={4} style={{ width: '100%' }}>
              <Text strong style={{ fontSize: 13 }}>
                <FileTextOutlined style={{ marginRight: 4 }} />
                Arquivo de Configuração
              </Text>
              <Select
                size="large"
                style={{ width: '100%' }}
                placeholder="Selecione o arquivo YAML"
                value={selectedFile}
                onChange={(value) => setSelectedFile(value)}
                loading={loadingFiles}
                disabled={!selectedServer}
                notFoundContent={<Empty description="Nenhum arquivo encontrado" />}
              >
                {files.map(file => {
                  // Determinar tags baseado no serviço e nome do arquivo
                  const isAlertFile = file.filename.toLowerCase().includes('alert');

                  return (
                    <Select.Option key={file.path} value={file.path}>
                      <Space size="small">
                        <FileTextOutlined />
                        <span>{file.filename}</span>

                        {/* Lógica de múltiplas tags */}
                        {file.service === 'alertmanager' ? (
                          // Arquivos de /etc/alertmanager → apenas tag [Alertmanager]
                          <Tag color="orange" style={{ margin: 0, fontSize: 11 }}>
                            alertmanager
                          </Tag>
                        ) : file.service === 'prometheus' && isAlertFile ? (
                          // Arquivos do prometheus com "alert" no nome → tags [prometheus] [alert]
                          <>
                            <Tag color="blue" style={{ margin: 0, fontSize: 11 }}>
                              prometheus
                            </Tag>
                            <Tag color="red" style={{ margin: 0, fontSize: 11 }}>
                              alert
                            </Tag>
                          </>
                        ) : (
                          // Outros arquivos → tag padrão do serviço
                          <Tag color={file.service === 'prometheus' ? 'blue' : 'orange'} style={{ margin: 0, fontSize: 11 }}>
                            {file.service}
                          </Tag>
                        )}
                      </Space>
                    </Select.Option>
                  );
                })}
              </Select>
            </Space>
          </Col>

          {/* Coluna 3: Botão Editar Arquivo */}
          <Col xs={12} lg={3}>
            <Space direction="vertical" size={4} style={{ width: '100%' }}>
              <Text strong style={{ fontSize: 13, opacity: 0 }}>.</Text>
              <Button
                type="primary"
                size="large"
                block
                icon={<EditOutlined />}
                onClick={handleOpenMonacoEditor}
                loading={monacoLoading}
                disabled={!selectedFile}
              >
                Editar Arquivo
              </Button>
            </Space>
          </Col>

          {/* Coluna 4: Botão Recarregar */}
          <Col xs={12} lg={3}>
            <Space direction="vertical" size={4} style={{ width: '100%' }}>
              <Text strong style={{ fontSize: 13, opacity: 0 }}>.</Text>
              <Tooltip title="Recarregar arquivos e dados do servidor">
                <Button
                  size="large"
                  block
                  icon={<ReloadOutlined />}
                  onClick={handleReload}
                  disabled={!selectedServer}
                >
                  Recarregar
                </Button>
              </Tooltip>
            </Space>
          </Col>
        </Row>
      </Card>

      <Tabs
        activeKey={activeTabKey}
        onChange={(activeKey) => {
          // CORREÇÃO: Atualizar state da aba ativa
          setActiveTabKey(activeKey);

          // OTIMIZAÇÃO: Carregar fields apenas quando a aba for visualizada
          if (activeKey === 'fields' && fields.length === 0 && !loadingFields) {
            loadPrometheusFields();
          }
        }}
        tabBarExtraContent={
          <Space size="middle" align="center" style={{ marginBottom: 8, marginRight: 8 }}>
            {/* BOTÕES DE VISUALIZAÇÃO - Destaque Principal */}
            {fileType === 'rules' && (
              <>
                <Space.Compact size="large">
                  <Button
                    type={alertViewMode === 'group' ? 'primary' : 'default'}
                    size="large"
                    onClick={() => setAlertViewMode('group')}
                    style={{
                      fontWeight: 600,
                      boxShadow: alertViewMode === 'group' ? '0 2px 8px rgba(24, 144, 255, 0.3)' : undefined,
                    }}
                  >
                    Visão Grupo
                  </Button>
                  <Button
                    type={alertViewMode === 'individual' ? 'primary' : 'default'}
                    size="large"
                    onClick={() => setAlertViewMode('individual')}
                    style={{
                      fontWeight: 600,
                      boxShadow: alertViewMode === 'individual' ? '0 2px 8px rgba(24, 144, 255, 0.3)' : undefined,
                    }}
                  >
                    Visão Alerta
                  </Button>
                </Space.Compact>
                <div style={{ width: 1, height: 32, background: '#d9d9d9', margin: '0 4px' }} />
              </>
            )}

            {fileType === 'alertmanager' && (
              <>
                <Space.Compact size="large">
                  <Button
                    type={alertmanagerViewMode === 'routes' ? 'primary' : 'default'}
                    size="large"
                    onClick={() => setAlertmanagerViewMode('routes')}
                    style={{
                      fontWeight: 600,
                      boxShadow: alertmanagerViewMode === 'routes' ? '0 2px 8px rgba(24, 144, 255, 0.3)' : undefined,
                    }}
                  >
                    Rotas
                  </Button>
                  <Button
                    type={alertmanagerViewMode === 'receivers' ? 'primary' : 'default'}
                    size="large"
                    onClick={() => setAlertmanagerViewMode('receivers')}
                    style={{
                      fontWeight: 600,
                      boxShadow: alertmanagerViewMode === 'receivers' ? '0 2px 8px rgba(24, 144, 255, 0.3)' : undefined,
                    }}
                  >
                    Receptores
                  </Button>
                  <Button
                    type={alertmanagerViewMode === 'inhibit-rules' ? 'primary' : 'default'}
                    size="large"
                    onClick={() => setAlertmanagerViewMode('inhibit-rules')}
                    style={{
                      fontWeight: 600,
                      boxShadow: alertmanagerViewMode === 'inhibit-rules' ? '0 2px 8px rgba(24, 144, 255, 0.3)' : undefined,
                    }}
                  >
                    Regras de Inibição
                  </Button>
                </Space.Compact>
                <div style={{ width: 1, height: 32, background: '#d9d9d9', margin: '0 4px' }} />
              </>
            )}

            {/* BOTÕES DE CONFIGURAÇÃO - Secundários */}
            <Space.Compact size="large">
              <Dropdown
                menu={{
                  items: [
                    { key: 'small', label: 'Compacto' },
                    { key: 'middle', label: 'Médio' },
                    { key: 'large', label: 'Grande' },
                  ],
                  onClick: ({ key }: { key: string }) => setTableSize(key as 'small' | 'middle' | 'large'),
                  selectedKeys: [tableSize],
                }}
              >
                <Button icon={<ColumnHeightOutlined />} size="large">
                  Densidade
                </Button>
              </Dropdown>
              <ColumnSelector
                columns={columnConfig}
                onChange={setColumnConfig}
                storageKey={`prometheus-columns-${fileType}`}
                buttonSize="large"
              />
            </Space.Compact>
          </Space>
        }
        items={[
          {
            key: 'jobs',
            label: (
              <span>
                <DatabaseOutlined />
                Jobs / Scrape Configs ({jobs.length})
                {selectedServer && <Tag color="orange" style={{ marginLeft: 8 }}>Por Servidor</Tag>}
              </span>
            ),
            children: (
              <Card style={{ minHeight: 600 }}>
                <div style={{ minHeight: 500 }}>
                  <ProTable
                  columns={visibleColumns}
                  dataSource={fileType === 'alertmanager' ? processedAlertmanagerData : processedJobs}
                  rowKey={
                    fileType === 'alertmanager' ?
                      (alertmanagerViewMode === 'routes' ? 'index' :
                       alertmanagerViewMode === 'receivers' ? 'index' : 'index') :
                    fileType === 'rules' && alertViewMode === 'individual' ? 'name' : itemKey
                  }
                  loading={fileType === 'alertmanager' ? loadingAlertmanager : loadingJobs}
                  search={false}
                  size={tableSize}
                  options={false}
                  pagination={{
                    defaultPageSize: 20,
                    showSizeChanger: true,
                    pageSizeOptions: ['10', '20', '30', '50', '100'],
                    showTotal: (total) => `Total: ${total} jobs`,
                  }}
                  scroll={{ x: 1200 }}
                  components={{
                    header: {
                      cell: ResizableTitle,
                    },
                  }}
                  locale={{
                    emptyText: selectedFile ? (
                      <Empty description="Nenhum job encontrado neste arquivo" />
                    ) : (
                      <Empty description="Selecione um arquivo para visualizar os jobs" />
                    ),
                  }}
                />
                </div>

                {/* Explicações dinâmicas baseadas no tipo de arquivo - APÓS A TABELA */}
                {fileType === 'alertmanager' ? (
                  // Explicações específicas para Alertmanager
                  <>
                    {alertmanagerViewMode === 'routes' && (
                      <Alert
                        message="🔀 ROTAS - Hierarquia de Roteamento de Alertas"
                        description={
                          <div>
                            <p style={{ marginBottom: 12 }}>
                              <strong>Define COMO os alertas são direcionados para os receptores.</strong> As rotas funcionam em cascata: quando um alerta chega, o AlertManager percorre as rotas em ordem até encontrar um match.
                            </p>

                            <div style={{ background: '#f0f5ff', padding: 12, borderRadius: 4, marginBottom: 12 }}>
                              <strong>📊 Campos Explicados:</strong>
                              <ul style={{ marginBottom: 0, marginTop: 8 }}>
                                <li><strong>Match Pattern:</strong> Condição para rotear o alerta (ex: severity: critical). Badge REGEX indica uso de expressões regulares.</li>
                                <li><strong>Receiver:</strong> Nome do receptor que receberá os alertas que derem match nesta rota.</li>
                                <li><strong>Group By:</strong> Labels usadas para agrupar alertas similares e evitar spam (ex: alertname, instance).</li>
                                <li><strong>Group Wait:</strong> Tempo de espera antes de enviar o PRIMEIRO alerta de um novo grupo (permite agrupar alertas que chegam juntos).</li>
                                <li><strong>Repeat Interval:</strong> Intervalo para reenviar alertas não resolvidos (evita notificações excessivas).</li>
                                <li><strong>Continue:</strong> Se ✅, continua avaliando outras rotas mesmo após dar match (permite enviar para múltiplos destinos).</li>
                              </ul>
                            </div>

                            <div style={{ background: '#fff7e6', padding: 12, borderRadius: 4, marginBottom: 12 }}>
                              <strong>⚡ Hierarquia de Prioridade:</strong>
                              <ol style={{ marginBottom: 0, marginTop: 8 }}>
                                <li><strong>CRÍTICOS:</strong> Resposta imediata (Group Wait: 10s, Repeat: 2h)</li>
                                <li><strong>VIP:</strong> Clientes prioritários (Group Wait: 10s, Repeat: 1h)</li>
                                <li><strong>ESPECÍFICOS:</strong> Windows, Linux, Rede, SSL (Group Wait: 1-5m, Repeat: 4-24h)</li>
                                <li><strong>WARNINGS:</strong> Menor prioridade (Group Wait: 5m, Repeat: 24h)</li>
                              </ol>
                            </div>

                            <p style={{ marginBottom: 0 }}>
                              💡 <strong>Dica:</strong> Rotas no topo têm prioridade. Alertas críticos devem vir antes de warnings para garantir resposta rápida. Use <code>continue: true</code> quando quiser enviar o mesmo alerta para múltiplos receptores.
                            </p>
                          </div>
                        }
                        type="info"
                        showIcon
                        closable
                        style={{ marginTop: 16 }}
                      />
                    )}

                    {alertmanagerViewMode === 'receivers' && (
                      <Alert
                        message="📡 RECEPTORES - Destinos dos Alertas"
                        description={
                          <div>
                            <p style={{ marginBottom: 12 }}>
                              <strong>Define PARA ONDE os alertas são enviados.</strong> Cada receptor pode ter múltiplas configurações (webhooks, emails, Telegram, Slack) e será ativado quando uma rota direcioná-lo.
                            </p>

                            <div style={{ background: '#f0f5ff', padding: 12, borderRadius: 4, marginBottom: 12 }}>
                              <strong>📊 Campos Explicados:</strong>
                              <ul style={{ marginBottom: 0, marginTop: 8 }}>
                                <li><strong>Nome:</strong> Identificador único do receptor, referenciado pelas rotas.</li>
                                <li><strong>Tipos:</strong> Métodos de notificação configurados:
                                  <ul style={{ marginTop: 4 }}>
                                    <li><Tag color="purple">webhook</Tag> - Envia HTTP POST para uma URL (ex: outro AlertManager, sistemas de tickets)</li>
                                    <li><Tag color="green">email</Tag> - Envia e-mail via SMTP</li>
                                    <li><Tag color="cyan">telegram</Tag> - Envia mensagem para bot do Telegram</li>
                                    <li><Tag color="orange">slack</Tag> - Envia para canal do Slack</li>
                                  </ul>
                                </li>
                                <li><strong>Destinos:</strong> URLs, e-mails ou IDs dos canais/chats configurados.</li>
                              </ul>
                            </div>

                            <div style={{ background: '#f6ffed', padding: 12, borderRadius: 4, marginBottom: 12 }}>
                              <strong>✅ Receptores Configurados:</strong>
                              <ul style={{ marginBottom: 0, marginTop: 8 }}>
                                <li><strong>alertmanager-palmas:</strong> Receptor padrão (webhook para AlertManager central)</li>
                                <li><strong>critical-alerts:</strong> Alertas críticos (webhook + possibilidade de Telegram/Slack)</li>
                                <li><strong>vip-alerts:</strong> Clientes VIP (webhook + email para gestão)</li>
                                <li><strong>*-team:</strong> Equipes específicas (Windows, Linux, Rede, SSL, SLA)</li>
                                <li><strong>warning-alerts:</strong> Warnings menos urgentes (webhook sem send_resolved)</li>
                              </ul>
                            </div>

                            <p style={{ marginBottom: 0 }}>
                              💡 <strong>Dica:</strong> Configure webhooks para integração com sistemas de tickets, Telegram/Slack para notificações em tempo real da equipe, e e-mail para relatórios e gestão. Use <code>send_resolved: false</code> em warnings para reduzir ruído.
                            </p>
                          </div>
                        }
                        type="success"
                        showIcon
                        closable
                        style={{ marginTop: 16 }}
                      />
                    )}

                    {alertmanagerViewMode === 'inhibit-rules' && (
                      <Alert
                        message="🚫 REGRAS DE INIBIÇÃO - Prevenção de Duplicatas e Spam"
                        description={
                          <div>
                            <p style={{ marginBottom: 12 }}>
                              <strong>Define O QUE deve ser suprimido para evitar spam.</strong> Quando um alerta "source" está ativo, os alertas "target" com labels iguais são automaticamente silenciados.
                            </p>

                            <div style={{ background: '#f0f5ff', padding: 12, borderRadius: 4, marginBottom: 12 }}>
                              <strong>📊 Campos Explicados:</strong>
                              <ul style={{ marginBottom: 0, marginTop: 8 }}>
                                <li><strong>Source Alert:</strong> Alerta que SUPRIME outros (em vermelho). Quando ativo, impede envio dos targets. Badge REGEX indica pattern com expressões regulares.</li>
                                <li><strong>Target Alert:</strong> Alerta SUPRIMIDO. Não será enviado enquanto source estiver ativo e labels forem iguais.</li>
                                <li><strong>Equal Labels:</strong> Labels que devem ter VALORES IGUAIS entre source e target para a inibição funcionar (geralmente <Tag color="geekblue">instance</Tag> ou <Tag color="geekblue">company</Tag>).</li>
                              </ul>
                            </div>

                            <div style={{ background: '#fff1f0', padding: 12, borderRadius: 4, marginBottom: 12 }}>
                              <strong>🔥 Hierarquia de Supressão (em ordem de prioridade):</strong>
                              <ol style={{ marginBottom: 0, marginTop: 8 }}>
                                <li><strong>Host Offline → Tudo:</strong> Se host está completamente indisponível, não alertar CPU/RAM/Disco/Disponibilidade</li>
                                <li><strong>VIP → Genérico:</strong> Alerta VIP suprime host indisponível genérico (evita duplicata com mais urgência)</li>
                                <li><strong>SLA Mensal → Períodos Menores:</strong> SLA mensal violado suprime alertas de disponibilidade de 24h/1h</li>
                                <li><strong>Critical → Warning:</strong> Severidade crítica suprime warnings do mesmo tipo</li>
                                <li><strong>Exporter Down → InstanceDown:</strong> Alerta específico suprime genérico</li>
                                <li><strong>Disponibilidade 24h → 1h:</strong> Período maior suprime menor</li>
                              </ol>
                            </div>

                            <div style={{ background: '#fff7e6', padding: 12, borderRadius: 4, marginBottom: 12 }}>
                              <strong>💡 Benefícios da Configuração Atual:</strong>
                              <ul style={{ marginBottom: 0, marginTop: 8 }}>
                                <li>✅ Zero duplicatas de "Host Indisponível" vs "Disponibilidade Baixa"</li>
                                <li>✅ Host offline não gera spam de CPU/RAM/Disco</li>
                                <li>✅ SLA mensal suprime alertas menores de disponibilidade</li>
                                <li>✅ Alertas de rede agrupados (RX/TX não duplicam)</li>
                                <li>✅ Hierarquia clara: Critical → Warning → Info</li>
                              </ul>
                            </div>

                            <p style={{ marginBottom: 0 }}>
                              💡 <strong>Dica:</strong> Regras de inibição evitam que você receba 10 alertas dizendo a mesma coisa. Se um host está offline, não faz sentido alertar sobre CPU alta naquele host. A ordem importa: regras mais específicas devem vir primeiro!
                            </p>
                          </div>
                        }
                        type="warning"
                        showIcon
                        closable
                        style={{ marginTop: 16 }}
                      />
                    )}
                  </>
                ) : fileType !== 'rules' && (
                  // Alert genérico para outros tipos (não mostrar para rules pois já tem explicação)
                  <Alert
                    message="📋 Visualização dos Jobs - Somente Leitura"
                    description={
                      <div>
                        <p style={{ marginBottom: 8 }}>
                          <strong>Esta tabela é somente para consulta.</strong> Para editar o arquivo YAML completo com preservação de comentários, clique no botão <strong>"Editar Arquivo"</strong> acima.
                        </p>
                        <p style={{ marginBottom: 0 }}>
                          Use o botão <strong>"Visualizar"</strong> na coluna de ações para ver os detalhes completos de cada job em formato JSON.
                        </p>
                      </div>
                    }
                    type="info"
                    showIcon
                    closable
                    style={{ marginTop: 16 }}
                  />
                )}
              </Card>
            ),
          },
          {
            key: 'fields',
            label: (
              <span>
                <DatabaseOutlined />
                Campos Metadata ({totalFields}) <Tag color="blue">GLOBAL</Tag>
              </span>
            ),
            children: (
              <Card style={{ minHeight: 400 }}>
                <Alert
                  message="💡 Campos Metadata - Configuração Global"
                  description={
                    <div>
                      <p style={{ marginBottom: 12 }}>
                        <strong>Esta visualização é somente para consulta.</strong> Os campos metadata são configurações <strong>globais da aplicação</strong> que definem quais metadados podem ser utilizados nos relabel_configs de todos os jobs em todos os servidores.
                      </p>
                      <p style={{ marginBottom: 12 }}>
                        Para <strong>criar, editar ou excluir</strong> campos metadata, acesse a página de configuração dedicada:
                      </p>
                      <Button
                        type="primary"
                        icon={<SettingOutlined />}
                        onClick={() => navigate('/metadata-fields')}
                      >
                        Ir para Gerenciamento de Campos Metadata
                        <ArrowRightOutlined style={{ marginLeft: 8 }} />
                      </Button>
                    </div>
                  }
                  type="info"
                  showIcon
                  closable
                  style={{ marginBottom: 16 }}
                />

                <Table
                  dataSource={fields}
                  columns={fieldsColumns}
                  rowKey="name"
                  loading={loadingFields}
                  pagination={{
                    defaultPageSize: 30,
                    showSizeChanger: true,
                    pageSizeOptions: ['10', '20', '30', '50', '100'],
                    showTotal: (total) => `Total: ${total} campos`,
                  }}
                  locale={{
                    emptyText: 'Nenhum campo metadata configurado'
                  }}
                />
              </Card>
            ),
          },
        ]}
      />

      {/* Modal de Progresso de Extração dos Campos Metadata */}
      <Modal
        title={
          <Space>
            {loadingFields ? (
              <LoadingOutlined style={{ color: '#1890ff' }} spin />
            ) : fromCache ? (
              <ThunderboltOutlined style={{ color: '#52c41a' }} />
            ) : (
              <CheckCircleOutlined style={{ color: '#52c41a' }} />
            )}
            <span>
              {loadingFields
                ? 'Extraindo Campos Metadata dos Servidores...'
                : fromCache
                ? 'Campos Metadata Carregados (Cache)'
                : `Extração Concluída (${successfulServers}/${totalServers} servidores)`}
            </span>
          </Space>
        }
        open={progressModalVisible}
        onCancel={() => setProgressModalVisible(false)}
        width={700}
        footer={
          <Button
            type="primary"
            onClick={() => setProgressModalVisible(false)}
            disabled={loadingFields}
          >
            {loadingFields ? 'Aguarde...' : 'OK'}
          </Button>
        }
      >
        <div style={{ marginBottom: 16 }}>
          {loadingFields ? (
            <Alert
              message="Processando servidores..."
              description="Conectando via SSH e extraindo campos metadata de cada servidor. Isso pode levar alguns segundos."
              type="info"
              showIcon
              icon={<SyncOutlined spin />}
            />
          ) : fromCache ? (
            <Alert
              message={
                <Space>
                  <ThunderboltOutlined />
                  Dados carregados do cache instantaneamente
                </Space>
              }
              description="Todos os servidores já foram processados anteriormente. Nenhuma conexão SSH foi necessária."
              type="success"
              showIcon
            />
          ) : fieldsError ? (
            <Alert
              message="Erro ao carregar campos"
              description={fieldsError}
              type="error"
              showIcon
            />
          ) : successfulServers === totalServers ? (
            <Alert
              message={
                <Space>
                  <CheckCircleOutlined />
                  Todos os servidores processados com sucesso
                </Space>
              }
              description={`Extraídos ${totalFields} campos únicos de ${totalServers} servidores.`}
              type="success"
              showIcon
            />
          ) : (
            <Alert
              message={
                <Space>
                  <WarningOutlined />
                  Alguns servidores falharam
                </Space>
              }
              description={`${successfulServers} de ${totalServers} servidores processados com sucesso. Verifique os detalhes abaixo.`}
              type="warning"
              showIcon
            />
          )}
        </div>

        {/* Timeline com Status de Cada Servidor */}
        {serverStatus.length > 0 && (
          <div>
            <div style={{ marginBottom: 12, fontWeight: 500, fontSize: 14 }}>
              Status dos Servidores:
            </div>
            <Timeline
              items={serverStatus.map((server: ServerStatus) => {
                // Determinar se servidor está sendo processado
                const isProcessing = loadingFields && server.duration_ms === 0 && !server.success && !server.error;

                return {
                  color: isProcessing ? 'blue' : server.success ? 'green' : 'red',
                  dot: isProcessing ? (
                    <LoadingOutlined style={{ fontSize: 16 }} spin />
                  ) : server.success ? (
                    <CheckCircleOutlined style={{ fontSize: 16 }} />
                  ) : (
                    <CloseCircleOutlined style={{ fontSize: 16 }} />
                  ),
                  children: (
                    <div>
                      <Space>
                        <CloudServerOutlined />
                        <strong>{server.hostname}</strong>
                        {isProcessing ? (
                          <Tag color="processing" icon={<SyncOutlined spin />}>
                            Processando...
                          </Tag>
                        ) : server.from_cache ? (
                          <Tag color="cyan" icon={<ThunderboltOutlined />}>
                            Cache
                          </Tag>
                        ) : server.success ? (
                          <Tag color="green">Sucesso</Tag>
                        ) : (
                          <Tag color="red">Falha</Tag>
                        )}
                        {server.duration_ms > 0 && (
                          <Tag icon={<ClockCircleOutlined />}>
                            {server.duration_ms}ms
                          </Tag>
                        )}
                      </Space>
                      <div style={{ marginTop: 4, fontSize: 12, color: '#666' }}>
                        {isProcessing ? (
                          <span style={{ color: '#1890ff' }}>
                            Conectando via SSH e extraindo campos metadata...
                          </span>
                        ) : server.success ? (
                          server.from_cache ? (
                            <span style={{ color: '#52c41a' }}>
                              Dados carregados do cache (processado anteriormente)
                            </span>
                          ) : (
                            <>
                              {server.files_count} arquivos processados,{' '}
                              {server.fields_count} campos novos encontrados
                            </>
                          )
                        ) : (
                          <span style={{ color: '#ff4d4f' }}>
                            <WarningOutlined /> Erro:{' '}
                            {server.error || 'Servidor offline ou inacessível'}
                          </span>
                        )}
                      </div>
                    </div>
                  ),
                };
              })}
            />
          </div>
        )}

        {loadingFields && serverStatus.length === 0 && (
          <div style={{ textAlign: 'center', padding: '40px 0' }}>
            <Spin size="large" />
            <div style={{ marginTop: 16, color: '#666' }}>
              Iniciando extração dos servidores...
            </div>
          </div>
        )}
      </Modal>

      {/* Drawer de Visualização de Job - SOMENTE LEITURA */}
      <Drawer
        title={
          <div>
            <div style={{ fontSize: 16, fontWeight: 500 }}>
              {editingJob ? editingJob[itemKey] : ''}
            </div>
            <Text type="secondary" style={{ fontSize: 12 }}>
              Somente visualização - Para editar, use o "Editar Arquivo"
            </Text>
          </div>
        }
        width={750}
        open={drawerVisible}
        onClose={() => {
          setDrawerVisible(false);
          setEditingJob(null);
        }}
        extra={
          <Button type="primary" onClick={() => setDrawerVisible(false)}>
            Fechar
          </Button>
        }
      >
        <Alert
          message="📄 Visualização do Job"
          description="Esta é uma visualização do job selecionado. Para editar o arquivo completo com todos os comentários preservados, use o botão 'Editar Arquivo'."
          type="info"
          showIcon
          style={{ marginBottom: 16 }}
          closable
        />
        <TextArea
          rows={30}
          value={editingJob ? JSON.stringify(editingJob, null, 2) : ''}
          readOnly
          style={{
            fontFamily: 'Consolas, Monaco, "Courier New", monospace',
            fontSize: 13,
            backgroundColor: '#fafafa',
          }}
        />
      </Drawer>

      {/* Modal do Monaco Editor - Edição Direta do Arquivo */}
      <Modal
        open={monacoEditorVisible}
        onCancel={() => {
          if (monacoContent !== monacoOriginalContent) {
            modal.confirm({
              title: 'Descartar Mudanças?',
              content: 'Você tem mudanças não salvas. Deseja realmente fechar?',
              okText: 'Sim, Descartar',
              cancelText: 'Não, Continuar Editando',
              okButtonProps: { danger: true },
              width: 500,
              onOk: () => {
                setMonacoEditorVisible(false);
                setMonacoContent('');
                setMonacoValidationError(null);
              },
            });
          } else {
            setMonacoEditorVisible(false);
          }
        }}
        width="90%"
        style={{ top: 20 }}
        footer={null}
        closeIcon={<CloseCircleOutlined style={{ fontSize: 20 }} />}
        title={
          <Row gutter={16} align="middle" style={{ width: '100%' }}>
            {/* Coluna 1: Nome do Arquivo (30%) */}
            <Col span={7}>
              <Space size="small">
                <FileTextOutlined />
                <Text strong ellipsis style={{ maxWidth: 300 }}>
                  {monacoFileInfo?.file_path || selectedFile}
                </Text>
              </Space>
              {monacoFileInfo && (
                <div>
                  <Text type="secondary" style={{ fontSize: 11 }}>
                    {monacoFileInfo.host} | {(monacoFileInfo.size_bytes / 1024).toFixed(1)} KB
                  </Text>
                </div>
              )}
            </Col>

            {/* Coluna 2: Alertas e Validações (40%) */}
            <Col span={10}>
              {monacoValidationError ? (
                <Alert
                  message="Erro de Sintaxe YAML"
                  description={monacoValidationError}
                  type="error"
                  showIcon
                  icon={<CloseCircleOutlined />}
                  style={{ padding: '4px 8px', fontSize: 12 }}
                  banner
                />
              ) : monacoContent !== monacoOriginalContent ? (
                <Alert
                  message="Arquivo Modificado"
                  description="Clique em Salvar para aplicar as alterações"
                  type="warning"
                  showIcon
                  icon={<InfoCircleOutlined />}
                  style={{ padding: '4px 8px', fontSize: 12 }}
                  banner
                />
              ) : (
                <Tag color="success" icon={<CheckCircleOutlined />} style={{ fontSize: 13, padding: '4px 12px' }}>
                  YAML Válido
                </Tag>
              )}
            </Col>

            {/* Coluna 3: Botões (30%) */}
            <Col span={7} style={{ textAlign: 'right' }}>
              <Space>
                <Button
                  onClick={() => {
                    if (monacoContent !== monacoOriginalContent) {
                      modal.confirm({
                        title: 'Descartar Mudanças?',
                        content: 'Você tem mudanças não salvas. Deseja realmente cancelar?',
                        okText: 'Sim, Descartar',
                        cancelText: 'Não',
                        okButtonProps: { danger: true },
                        width: 500,
                        onOk: () => {
                          setMonacoEditorVisible(false);
                          setMonacoContent('');
                          setMonacoValidationError(null);
                        },
                      });
                    } else {
                      setMonacoEditorVisible(false);
                    }
                  }}
                  disabled={monacoSaving}
                >
                  Cancelar
                </Button>
                <Button
                  type="primary"
                  icon={<SaveOutlined />}
                  onClick={handleSaveMonacoEditor}
                  loading={monacoSaving}
                  disabled={monacoValidationError !== null || monacoContent === monacoOriginalContent}
                  size="middle"
                >
                  {monacoSaving ? 'Salvando...' : 'Salvar Alterações'}
                </Button>
              </Space>
            </Col>
          </Row>
        }
      >
        {monacoLoading ? (
          <div style={{ textAlign: 'center', padding: 60 }}>
            <Spin size="large" />
            <div style={{ marginTop: 16, fontSize: 16 }}>
              Carregando arquivo do servidor...
            </div>
          </div>
        ) : (
          <>
            {/* Editor Monaco */}
            <div style={{ height: '70vh', marginBottom: 16 }}>
              <Editor
                height="100%"
                language="yaml"
                value={monacoContent}
                onChange={handleMonacoChange}
                theme="vs-dark"
                options={{
                  minimap: { enabled: true },
                  fontSize: 14,
                  lineNumbers: 'on',
                  rulers: [80, 120],
                  wordWrap: 'off',
                  scrollBeyondLastLine: false,
                  automaticLayout: true,
                  tabSize: 2,
                  insertSpaces: true,
                  formatOnPaste: true,
                  formatOnType: true,
                }}
                loading={<Spin size="large" />}
              />
            </div>

            {/* Alertas Informativos EMBAIXO do Editor */}
            <div style={{ marginTop: 8 }}>
              <Row gutter={[8, 8]}>
                <Col span={24}>
                  <Alert
                    message="💾 Salvamento Seguro"
                    description={
                      <ul style={{ margin: 0, paddingLeft: 20 }}>
                        <li>Backup automático criado antes de salvar</li>
                        <li>Reload automático dos serviços após validação bem-sucedida</li>
                        <li>Permissões restauradas automaticamente (prometheus:prometheus)</li>
                        <li>Validação com promtool antes de aplicar</li>
                      </ul>
                    }
                    type="info"
                    showIcon
                    closable
                    style={{ fontSize: 12 }}
                  />
                </Col>
              </Row>
            </div>
          </>
        )}
      </Modal>

      {/* Modal de Progresso - 5 Steps */}
      <Modal
        open={progressVisible}
        title="Salvando Configuração"
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
              title: 'Validação YAML',
              status: stepStatus[0],
              description: stepMessages[0],
              icon: stepStatus[0] === 'process' ? <LoadingOutlined /> : undefined,
            },
            {
              title: 'Salvamento',
              status: stepStatus[1],
              description: stepMessages[1],
              icon: stepStatus[1] === 'process' ? <LoadingOutlined /> : undefined,
            },
            {
              title: 'Validação Promtool',
              status: stepStatus[2],
              description: stepMessages[2],
              icon: stepStatus[2] === 'process' ? <LoadingOutlined /> : undefined,
            },
            {
              title: 'Reload de Serviços',
              status: stepStatus[3],
              description: stepMessages[3],
              icon: stepStatus[3] === 'process' ? <SyncOutlined spin /> : undefined,
            },
            {
              title: 'Verificação de Status',
              status: stepStatus[4],
              description: stepMessages[4],
              icon: stepStatus[4] === 'process' ? <LoadingOutlined /> : undefined,
            },
          ]}
        />

        <div style={{ marginTop: 24, textAlign: 'right' }}>
          {/* Mostrar botão apenas quando terminou (sucesso ou erro) */}
          {(Object.values(stepStatus).every(s => s === 'finish' || s === 'error' || s === 'wait')) &&
           (stepStatus[0] === 'finish' || stepStatus[0] === 'error') && (
            <Button
              type={stepStatus[3] === 'finish' && stepStatus[4] === 'finish' ? 'primary' : 'default'}
              danger={stepStatus[3] === 'error' || stepStatus[4] === 'error'}
              onClick={() => {
                setProgressVisible(false);
                setMonacoEditorVisible(false);
                setMonacoContent('');
                setMonacoValidationError(null);
              }}
            >
              {stepStatus[3] === 'finish' && stepStatus[4] === 'finish' ? 'Concluído' : 'Fechar'}
            </Button>
          )}
        </div>
      </Modal>
      </PageContainer>
  );
};

export default PrometheusConfig;
