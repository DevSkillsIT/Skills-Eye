import React, { useEffect, useMemo, useState } from 'react';
import {
  Alert,
  Button,
  Card,
  Col,
  Divider,
  Form,
  Input,
  List,
  message,
  Modal,
  Row,
  Select,
  Space,
  Steps,
  Switch,
  Tag,
  Tooltip,
  Typography,
  Upload,
} from 'antd';
import {
  CheckCircleOutlined,
  CloudServerOutlined,
  LinuxOutlined,
  ReloadOutlined,
  SettingOutlined,
  ThunderboltOutlined,
  ToolOutlined,
  UploadOutlined,
  WindowsOutlined,
} from '@ant-design/icons';
import { PageContainer } from '@ant-design/pro-components';
import {
  consulAPI,
  type ConsulNode,
  type InstallStatusResponse,
  type InstallerLogEntry as ApiInstallerLogEntry,
  type InstallerRequest,
} from '../services/api';

type ConnectionMethod = 'ssh' | 'fallback';
type WindowsResolvedMethod = 'psexec' | 'winrm' | 'ssh';

type PrecheckStatus = 'pending' | 'running' | 'success' | 'failed';

interface PrecheckItem {
  key: string;
  label: string;
  description: string;
  status: PrecheckStatus;
  detail?: string;
}
interface CollectorOption {
  value: string;
  label: string;
  description: string;
  targets: Array<'linux' | 'windows'>;
}

interface InstallLogEntry {
  key: string;
  message: string;
  source: 'local' | 'remote';
  level?: string;
  timestamp?: string;
  details?: string;
}

interface NormalizedConsulNode extends ConsulNode {
  node?: string;
  addr?: string;
  status?: string;
  type?: string;
  services_count?: number;
  datacenter?: string;
  tagged_addresses?: Record<string, string>;
  meta?: Record<string, string>;
}

interface WarningModalContent {
  duplicateConsul?: boolean;
  existingInstall?: boolean;
  services: string[];
  portOpen?: boolean;
  serviceRunning?: boolean;
  hasConfig?: boolean;
  targetType: 'linux' | 'windows';
}

interface ConsulServiceInstance {
  service?: string;
  Service?: string;
  ServiceName?: string;
  ServiceID?: string;
  service_name?: string;
  ServiceMeta?: Record<string, string | undefined>;
  Meta?: Record<string, string | undefined>;
  meta?: Record<string, string | undefined>;
  Address?: string;
  address?: string;
  ServiceAddress?: string;
  nodeAddr?: string;
  Node?: {
    Address?: string;
  };
  instance?: string;
  host?: string;
  ip?: string;
}

interface ExistingInstallationCheckRequest {
  host: string;
  port: number;
  username: string;
  password: string;
  exporter_port: number;
  target_type: 'linux' | 'windows';
  domain?: string;
}

interface AxiosErrorLike {
  response?: {
    status?: number;
    data?: Record<string, unknown> | string;
  };
  message?: string;
  stack?: string;
  code?: string;
  timeout?: number;
}

const { Paragraph, Text, Title } = Typography;
const { Option } = Select;

const LOG_LEVEL_COLOR: Record<string, string> = {
  error: 'red',
  warning: 'orange',
  success: 'green',
  progress: 'geekblue',
  info: 'blue',
  debug: 'purple',
};

const formatLogTimestamp = (iso?: string): string | undefined => {
  if (!iso) {
    return undefined;
  }
  const parsed = new Date(iso);
  if (Number.isNaN(parsed.getTime())) {
    return undefined;
  }
  return parsed.toLocaleTimeString('pt-BR', { hour12: false });
};

const buildLogDetails = (data?: Record<string, unknown>): string | undefined => {
  if (!data) {
    return undefined;
  }

  const sections: string[] = [];
  const commandValue = data.command;
  if (typeof commandValue === 'string' && commandValue.trim().length > 0) {
    sections.push(`Comando: ${commandValue}`);
  }

  const exitCodeValue = data.exit_code;
  if (typeof exitCodeValue === 'number') {
    sections.push(`Exit code: ${exitCodeValue}`);
  } else if (typeof exitCodeValue === 'string' && exitCodeValue.trim().length > 0) {
    sections.push(`Exit code: ${exitCodeValue}`);
  }

  const outputValue = data.output;
  if (typeof outputValue === 'string' && outputValue.trim().length > 0) {
    sections.push(`Saída:\n${outputValue.trim()}`);
  }

  const reservedKeys = new Set(['command', 'output', 'exit_code']);
  const extraEntries = Object.entries(data).filter(([key]) => !reservedKeys.has(key));
  if (extraEntries.length > 0) {
    const formattedExtras = extraEntries
      .map(([key, value]) => {
        if (typeof value === 'string' || typeof value === 'number' || typeof value === 'boolean') {
          return `${key}: ${value}`;
        }
        try {
          return `${key}: ${JSON.stringify(value, null, 2)}`;
        } catch {
          return `${key}: ${String(value)}`;
        }
      })
      .join('\n');
    sections.push(formattedExtras);
  }

  return sections.length > 0 ? sections.join('\n') : undefined;
};

const mapBackendLogs = (
  logs: ApiInstallerLogEntry[] | undefined,
  installationId: string,
): InstallLogEntry[] => {
  if (!Array.isArray(logs) || logs.length === 0) {
    return [];
  }

  return logs
    .filter((log) => typeof log.message === 'string' && log.message.trim().length > 0)
    .map((log, index) => {
      const keyBase = log.timestamp && log.timestamp.length > 0 ? log.timestamp : `${installationId}-${index}`;
      const normalizedLevel = typeof log.level === 'string' ? log.level.toLowerCase() : undefined;

      return {
        key: `remote-${keyBase}-${index}`,
        message: log.message,
        source: 'remote',
        level: normalizedLevel,
        timestamp: log.timestamp,
        details: buildLogDetails(log.data),
      };
    });
};

const toStringSafe = (value: unknown): string => (typeof value === 'string' ? value : '');

const DEFAULT_PRECHECKS: PrecheckItem[] = [
  {
    key: 'connectivity',
    label: 'Conectividade',
    description: 'Valida acesso remoto, porta configurada e credenciais fornecidas.',
    status: 'pending',
  },
  {
    key: 'os',
    label: 'Sistema operacional',
    description: 'Detecta distribuição, versão e arquitetura.',
    status: 'pending',
  },
  {
    key: 'ports',
    label: 'Portas reservadas',
    description: 'Confere disponibilidade da porta do exporter (9100/9182).',
    status: 'pending',
  },
  {
    key: 'disk',
    label: 'Espaço em disco',
    description: 'Valida espaço mínimo para binários e logs.',
    status: 'pending',
  },
  {
    key: 'firewall',
    label: 'Firewall',
    description: 'Simula regras de liberação para Prometheus.',
    status: 'pending',
  },
];

const COLLECTOR_OPTIONS: CollectorOption[] = [
  {
    value: 'node',
    label: 'Node exporter padrão',
    description: 'CPU, memória, rede e recursos básicos do host.',
    targets: ['linux'],
  },
  {
    value: 'filesystem',
    label: 'Filesystem',
    description: 'Uso de disco por filesystem, inodes e espaço reservado.',
    targets: ['linux'],
  },
  {
    value: 'systemd',
    label: 'Systemd',
    description: 'Estado de unidades systemd e falhas recentes.',
    targets: ['linux'],
  },
  {
    value: 'textfile',
    label: 'Textfile collector',
    description: 'Permite expor métricas customizadas via arquivos .prom.',
    targets: ['linux'],
  },
  {
    value: 'process',
    label: 'Process collector',
    description: 'Expande métricas de processos, threads e uso de CPU.',
    targets: ['linux'],
  },
  {
    value: 'iostat',
    label: 'iostat collector (Linux)',
    description: 'Métricas detalhadas de IO por dispositivo (requer sysstat).',
    targets: ['linux'],
  },
  {
    value: 'wmi',
    label: 'WMI collectors (Windows)',
    description: 'Grupos padrão do windows_exporter (CPU, memória, discos, serviços).',
    targets: ['windows'],
  },
];

const normalizeConsulNode = (raw: Record<string, unknown>): NormalizedConsulNode => {
  const nodeName = typeof raw['node'] === 'string'
    ? (raw['node'] as string)
    : typeof raw['Node'] === 'string'
    ? (raw['Node'] as string)
    : typeof raw['Name'] === 'string'
    ? (raw['Name'] as string)
    : 'desconhecido';

  const addrValue = typeof raw['addr'] === 'string'
    ? (raw['addr'] as string)
    : typeof raw['Address'] === 'string'
    ? (raw['Address'] as string)
    : typeof raw['address'] === 'string'
    ? (raw['address'] as string)
    : '';

  const statusValue = typeof raw['status'] === 'string'
    ? (raw['status'] as string)
    : typeof raw['Status'] === 'string'
    ? (raw['Status'] as string)
    : undefined;

  const typeValue = typeof raw['type'] === 'string'
    ? (raw['type'] as string)
    : typeof raw['Type'] === 'string'
    ? (raw['Type'] as string)
    : undefined;

  const servicesCountValue = typeof raw['services_count'] === 'number'
    ? (raw['services_count'] as number)
    : typeof raw['servicesCount'] === 'number'
    ? (raw['servicesCount'] as number)
    : undefined;

  const datacenterValue = typeof raw['datacenter'] === 'string'
    ? (raw['datacenter'] as string)
    : typeof raw['Datacenter'] === 'string'
    ? (raw['Datacenter'] as string)
    : undefined;

  const taggedAddressesValue = typeof raw['tagged_addresses'] === 'object' && raw['tagged_addresses'] !== null
    ? (raw['tagged_addresses'] as Record<string, string>)
    : typeof raw['TaggedAddresses'] === 'object' && raw['TaggedAddresses'] !== null
    ? (raw['TaggedAddresses'] as Record<string, string>)
    : undefined;

  const metaValue = typeof raw['meta'] === 'object' && raw['meta'] !== null
    ? (raw['meta'] as Record<string, string>)
    : typeof raw['Meta'] === 'object' && raw['Meta'] !== null
    ? (raw['Meta'] as Record<string, string>)
    : undefined;

  return {
    ...(raw as Record<string, unknown>),
    node: nodeName,
    addr: addrValue,
    status: statusValue,
    type: typeValue,
    services_count: servicesCountValue,
    datacenter: datacenterValue,
    tagged_addresses: taggedAddressesValue,
    meta: metaValue,
  } as unknown as NormalizedConsulNode;
};

const Installer: React.FC = () => {
  const [form] = Form.useForm();
  const watchedPort = Form.useWatch('port', form);
  const [currentStep, setCurrentStep] = useState(0);
  const [targetType, setTargetType] = useState<'linux' | 'windows'>('linux');
  const [prechecks, setPrechecks] = useState<PrecheckItem[]>(DEFAULT_PRECHECKS);
  const [precheckRunning, setPrecheckRunning] = useState(false);
  const [installLogs, setInstallLogs] = useState<InstallLogEntry[]>([]);
  const [installRunning, setInstallRunning] = useState(false);
  const [installSuccess, setInstallSuccess] = useState<boolean | null>(null);
  const [selectedCollectors, setSelectedCollectors] = useState<string[]>(['node', 'filesystem', 'systemd']);
  const [selectedVersion, setSelectedVersion] = useState<string>('latest');
  const [useBasicAuth, setUseBasicAuth] = useState(true);
  const [basicAuthUser, setBasicAuthUser] = useState('prometheus');
  const [basicAuthPassword, setBasicAuthPassword] = useState('');
  const [autoRegister, setAutoRegister] = useState(true);
  const [selectedNodeAddress, setSelectedNodeAddress] = useState('');
  const [nodes, setNodes] = useState<NormalizedConsulNode[]>([]);
  const [loadingNodes, setLoadingNodes] = useState(false);
  const [connectionMethod, setConnectionMethod] = useState<ConnectionMethod>('ssh');
  const [resolvedWindowsMethod, setResolvedWindowsMethod] = useState<WindowsResolvedMethod | null>(null);
  const [privateKeyFile, setPrivateKeyFile] = useState<string>('');
  const [existingInstallation, setExistingInstallation] = useState<{
    detected: boolean;
    portOpen: boolean;
    serviceRunning: boolean;
    hasConfig: boolean;
  } | null>(null);
  const [logModalVisible, setLogModalVisible] = useState(false);
  const [errorModalVisible, setErrorModalVisible] = useState(false);
  const [errorModalTitle, setErrorModalTitle] = useState('');
  const [errorModalContent, setErrorModalContent] = useState('');
  const [errorModalIcon, setErrorModalIcon] = useState('');
  const [errorCategory, setErrorCategory] = useState('');
  const [warningModalVisible, setWarningModalVisible] = useState(false);
  const [warningModalTitle, setWarningModalTitle] = useState('');
  const [warningModalContent, setWarningModalContent] = useState<WarningModalContent | null>(null);
  const [warningModalMode, setWarningModalMode] = useState<'precheck-warning' | 'toggle-auto-register' | null>(
    null,
  );

  const warningModalFooter = useMemo(() => {
    if (warningModalMode === 'toggle-auto-register') {
      return [
        <Button
          key="cancel"
          onClick={() => {
            setWarningModalVisible(false);
            setWarningModalContent(null);
            setWarningModalMode(null);
            message.info('Switch mantido DESLIGADO', 3);
          }}
        >
          ❌ Cancelar
        </Button>,
        <Button
          key="continue"
          type="primary"
          danger
          onClick={() => {
            setWarningModalVisible(false);
            setWarningModalContent(null);
            setWarningModalMode(null);
            setAutoRegister(true);
            message.success('✅ Registro no Consul ATIVADO (com IP duplicado)', 5);
          }}
        >
          ⚠️ Registrar Mesmo Assim
        </Button>,
      ];
    }

    return [
      <Button
        key="cancel"
        onClick={() => {
          setWarningModalVisible(false);
          setWarningModalContent(null);
          setWarningModalMode(null);
          message.info('Operação cancelada. Revise os dados e tente novamente.');
        }}
      >
        ❌ Cancelar
      </Button>,
      <Button
        key="continue"
        type="primary"
        danger
        onClick={() => {
          setWarningModalVisible(false);
          setWarningModalContent(null);
          setWarningModalMode(null);
          setCurrentStep(2);
          message.warning('⚠️ Prosseguindo com avisos. Tenha cuidado!', 5);
        }}
      >
        ⚠️ Continuar Mesmo Assim
      </Button>,
    ];
  }, [warningModalMode]);

  useEffect(() => {
    const desired: ConnectionMethod = targetType === 'linux' ? 'ssh' : 'fallback';
    setConnectionMethod((prev) => (prev === desired ? prev : desired));
    if (targetType === 'windows') {
      setResolvedWindowsMethod(null);
    }
    form.setFieldsValue({
      authType: 'password',
      password: undefined,
      keyPath: undefined,
    });
  }, [targetType, form]);

  useEffect(() => {
    const isWindowsFallback = targetType === 'windows' && connectionMethod === 'fallback';
    const defaultPort = isWindowsFallback ? 5985 : 22;
    const currentPort = form.getFieldValue('port');
    if (!currentPort || currentPort === 22 || currentPort === 5985) {
      form.setFieldsValue({ port: defaultPort });
    }
  }, [targetType, connectionMethod, form]);

  useEffect(() => {
    if (connectionMethod === 'fallback') {
      form.setFieldsValue({
        authType: 'password',
        keyPath: undefined,
      });
    }
  }, [connectionMethod, form]);

  const steps = useMemo(
    () => [
      { key: 'target', title: 'Destino', icon: <CloudServerOutlined /> },
      { key: 'prechecks', title: 'Pre-checks', icon: <ToolOutlined /> },
      { key: 'config', title: 'Configuracao', icon: <SettingOutlined /> },
      { key: 'install', title: 'Instalacao', icon: <ThunderboltOutlined /> },
      { key: 'validacao', title: 'Validacao', icon: <CheckCircleOutlined /> },
    ],
    [],
  );

  const selectedNodeLabel = useMemo(() => {
    if (!selectedNodeAddress) {
      return 'Não selecionado';
    }
    const match = nodes.find((node) => node.addr === selectedNodeAddress);
    return match ? `${match.node} (${match.addr})` : selectedNodeAddress;
  }, [nodes, selectedNodeAddress]);

  const appendLog = (messageText: string, level: string = 'info', details?: string) => {
      setInstallLogs((prev) => [
        ...prev,
        {
          key: `${Date.now()}-${prev.length}`,
          message: messageText,
          source: 'local',
          level,
          timestamp: new Date().toISOString(),
          details,
        },
      ]);
  };

  const buildLogRow = (entry: InstallLogEntry, variant: 'dark' | 'light' = 'dark') => {
    const levelKey = entry.level ?? 'info';
    const levelColor = LOG_LEVEL_COLOR[levelKey] ?? 'default';
    const sourceColor = entry.source === 'remote' ? 'geekblue' : 'cyan';
    const baseTextColor = variant === 'dark' ? '#f5f5f5' : '#262626';
    const detailsColor = variant === 'dark' ? '#c5c5c5' : '#595959';
    const detailsBackground = variant === 'dark' ? 'rgba(255,255,255,0.04)' : '#fafafa';

    return (
      <div key={entry.key} style={{ marginBottom: 8 }}>
        <Space align="start" wrap size={4} style={{ lineHeight: 1.4 }}>
          {entry.timestamp && (
            <Tag color="default" style={{ marginBottom: 0 }}>
              {formatLogTimestamp(entry.timestamp)}
            </Tag>
          )}
          <Tag color={levelColor} style={{ marginBottom: 0 }}>
            {levelKey.toUpperCase()}
          </Tag>
          <Tag color={sourceColor} style={{ marginBottom: 0 }}>
            {entry.source === 'remote' ? 'Backend' : 'Local'}
          </Tag>
          <span style={{ color: baseTextColor }}>{entry.message}</span>
        </Space>
        {entry.details && (
          <pre
            style={{
              margin: '4px 0 0',
              color: detailsColor,
              background: detailsBackground,
              borderRadius: 4,
              padding: 8,
              whiteSpace: 'pre-wrap',
              fontFamily: 'Consolas, Monaco, monospace',
              fontSize: 12,
            }}
          >
            {entry.details}
          </pre>
        )}
      </div>
    );
  };

  const normalizeWindowsMethod = (method?: string | null): WindowsResolvedMethod | null => {
    if (!method) {
      return null;
    }

    const normalized = method.toLowerCase();
    if (normalized === 'psexec' || normalized === 'winrm' || normalized === 'ssh') {
      return normalized;
    }

    return null;
  };

  // Função auxiliar para verificar se é IP ou hostname
  const isIPAddress = (str: string): boolean => {
    const ipv4Pattern = /^(\d{1,3}\.){3}\d{1,3}$/;
    const ipv6Pattern = /^([0-9a-fA-F]{0,4}:){2,7}[0-9a-fA-F]{0,4}$/;
    return ipv4Pattern.test(str) || ipv6Pattern.test(str);
  };

  const runPrechecks = async () => {
    try {
      const authType = form.getFieldValue('authType');
      const fields: Array<string> = ['host', 'port', 'username', 'authType'];
      if (authType === 'password') {
        fields.push('password');
      } else if (authType === 'key') {
        fields.push('keyPath');
      }
      await form.validateFields(fields);
    } catch {
      message.error('Preencha os campos obrigatorios do alvo.');
      return;
    }

    setPrecheckRunning(true);
    setPrechecks(
      DEFAULT_PRECHECKS.map((item) => ({
        ...item,
        status: 'pending',
        detail: undefined,
      })),
    );
    
    setExistingInstallation(null);
    setResolvedWindowsMethod(null);

    // Obter valores do formulário
    const host = form.getFieldValue('host');
    const port = form.getFieldValue('port');
    const username = form.getFieldValue('username');
    const password = form.getFieldValue('password');
    const keyPath = form.getFieldValue('keyPath');
    const authType = form.getFieldValue('authType');
    const useDomain = form.getFieldValue('useDomain');
    const domain = form.getFieldValue('domain');

    // Validar DNS se for hostname (não IP)
    if (!isIPAddress(host)) {
      setPrechecks((prev) =>
        prev.map((entry) =>
          entry.key === 'connectivity'
            ? { ...entry, status: 'running', detail: `Resolvendo hostname ${host} via DNS...` }
            : entry,
        ),
      );

      // Tentar resolver o hostname via backend (test-connection já faz isso)
      console.log(`🔍 Hostname detectado: ${host}, será resolvido durante teste de conexão`);
    }

    // 1. Teste de conectividade (REAL com backend)
    setPrechecks((prev) =>
      prev.map((entry) =>
        entry.key === 'connectivity'
          ? { ...entry, status: 'running', detail: targetType === 'windows' ? 'Testando conexão Windows (PSExec/WinRM/SSH)...' : 'Testando conexão SSH...' }
          : entry,
      ),
    );

    try {
      const methodToSend = 'auto';  // Backend decide automaticamente
      
      const testRequest: Partial<InstallerRequest> = {
        os_type: targetType,
        method: methodToSend,
        host,
        username,
        ssh_port: parseInt(port as string, 10) || 22,
      };

      // Adicionar domínio se estiver usando conta de domínio (Windows)
      if (targetType === 'windows' && useDomain && domain) {
        testRequest.domain = domain;
      }

      // Adicionar autenticação
      if (authType === 'password') {
        testRequest.password = password;
        testRequest.use_sudo = true;
      } else {
        testRequest.key_file = privateKeyFile || keyPath;
        testRequest.use_sudo = true;
      }

      const connectionTest = await consulAPI.testConnection(testRequest);

      if (connectionTest.data.success) {
        // Construir mensagem de sucesso
        let successDetail = `✅ Conectado com sucesso!`;
        
        // Se tem resumo de conexão (Windows multi-método)
        if (connectionTest.data.connection_summary) {
          const summary = connectionTest.data.connection_summary;
          successDetail += `\n\n🎯 Método usado: ${summary.successful_method?.toUpperCase()}`;
          successDetail += `\n📊 Tentativas: ${summary.total_attempts}`;
          
          // Listar tentativas
          const attempts = summary.attempts ?? [];
          if (attempts.length > 0) {
            successDetail += `\n\n📋 Histórico:`;
            attempts.forEach((attempt, index) => {
              const status = attempt.success ? '✅' : '❌';
              successDetail += `\n${index + 1}. ${attempt.method.toUpperCase()}: ${status}`;
            });
          }
        }

        if (targetType === 'windows') {
          const summaryMethod = normalizeWindowsMethod(connectionTest.data.connection_summary?.successful_method);
          const detailsMethod = normalizeWindowsMethod(connectionTest.data.details?.method);
          const resolvedMethod = summaryMethod ?? detailsMethod ?? 'psexec';

          setResolvedWindowsMethod(resolvedMethod);
          successDetail += `\n⚙️ Método configurado para instalação: ${resolvedMethod.toUpperCase()}`;
        } else {
          setResolvedWindowsMethod(null);
        }
        
        successDetail += `\n\n💻 Host: ${connectionTest.data.details.hostname}`;
        
        setPrechecks((prev) =>
          prev.map((entry) =>
            entry.key === 'connectivity'
              ? { 
                  ...entry, 
                  status: 'success', 
                  detail: successDetail
                }
              : entry,
          ),
        );

        // 2. Verificação de IP/Hostname duplicado no Consul (apenas selfnode*)
        await new Promise((resolve) => setTimeout(resolve, 300));
        setPrechecks((prev) =>
          prev.map((entry) =>
            entry.key === 'os'
              ? { ...entry, status: 'running', detail: 'Verificando IP/Hostname no Consul (selfnode) e detectando SO...' }
              : entry,
          ),
        );

        // Buscar apenas serviços selfnode* para verificar se o host já existe
        let ipDuplicado = false;
        const servicosComIp: string[] = [];
        
        try {
          const servicesResponse = await consulAPI.getServicesInstancesOptimized(false);
          console.log('🔍 Resposta do Consul:', servicesResponse.data);
          
          if (servicesResponse.data.data && Array.isArray(servicesResponse.data.data)) {
            console.log(`🔍 Total de instâncias: ${servicesResponse.data.data.length}`);

            // DEBUG: Mostrar estrutura dos primeiros 3 itens completos
            console.log(
              '🔍 Amostra de dados (primeiros 3 itens COMPLETOS):',
              JSON.stringify(servicesResponse.data.data.slice(0, 3), null, 2),
            );

            const normalizedHost = host.toLowerCase();
            const rawInstances = servicesResponse.data.data ?? [];
            const serviceInstances = rawInstances as unknown as ConsulServiceInstance[];

            // Primeiro, filtrar APENAS serviços selfnode* para análise
            const selfnodeServices = serviceInstances.filter((service) => {
              const nameCandidates = [
                toStringSafe(service.service),
                toStringSafe(service.Service),
                toStringSafe(service.ServiceName),
                toStringSafe(service.ServiceID),
                toStringSafe(service.service_name),
                toStringSafe(service.meta?.name),
                toStringSafe(service.Meta?.name),
              ];
              const serviceName = nameCandidates.find(Boolean) ?? '';
              console.log(`🔍 Analisando: serviceName="${serviceName}"`);
              return serviceName.toLowerCase().startsWith('selfnode');
            });

            console.log(
              `🔍 Serviços selfnode encontrados: ${selfnodeServices.length} de ${servicesResponse.data.data.length} total`,
            );

            if (selfnodeServices.length > 0) {
              console.log(
                '🔍 Primeiro serviço selfnode (estrutura completa):',
                JSON.stringify(selfnodeServices[0], null, 2),
              );
            }

            // Agora verificar cada serviço selfnode
            selfnodeServices.forEach((service) => {
              const nameCandidates = [
                toStringSafe(service.service),
                toStringSafe(service.Service),
                toStringSafe(service.ServiceName),
                toStringSafe(service.ServiceID),
                toStringSafe(service.Meta?.name),
                toStringSafe(service.meta?.name),
                toStringSafe(service.service_name),
              ];
              const serviceName = nameCandidates.find(Boolean) ?? '';

              // Coletar TODOS os campos que podem conter IP/hostname
              const possibleIPFields: Record<string, string | undefined> = {
                'meta.instance': service.meta?.instance,
                Address: service.address ?? service.Address,
                ServiceAddress: service.ServiceAddress,
                NodeAddress: service.nodeAddr,
                'Node.Address': service.Node?.Address,
                'Meta.instance': service.Meta?.instance,
                'ServiceMeta.instance': service.ServiceMeta?.instance,
                instance: service.instance,
                host: service.host,
                ip: service.ip,
                'Meta.host': service.Meta?.host,
                'Meta.ip': service.Meta?.ip,
              };

              // Filtrar apenas valores não vazios
              const possibleIPs = Object.entries(possibleIPFields)
                .filter(([, value]) => Boolean(value))
                .map(([field, value]) => ({ field, value: value ?? '' }));

              console.log(`🔍 Serviço: ${serviceName}`);
              console.log('   Campos com valores:', possibleIPs);
              console.log(`   Procurando: ${host}`);

              // Verificar se algum campo corresponde ao host procurado
              const foundMatch = possibleIPs.find(
                ({ value }) => value.toLowerCase() === normalizedHost,
              );

              if (foundMatch) {
                ipDuplicado = true;
                if (!servicosComIp.includes(serviceName)) {
                  servicosComIp.push(serviceName);
                  console.log(
                    `❌ IP/Host ENCONTRADO! Serviço: ${serviceName}, Campo: ${foundMatch.field}, Valor: ${foundMatch.value}`,
                  );
                }
              }
            });

            console.log(
              `🔍 Resultado final: ipDuplicado=${ipDuplicado}, serviços=${servicosComIp.join(', ')}`,
            );
          }
        } catch (error) {
          console.error('❌ Erro ao verificar IP duplicado:', error);
        }

        await new Promise((resolve) => setTimeout(resolve, 500));
        
        // Variáveis para acumular todos os problemas encontrados
        let hasDuplicateConsul = false;
        let consulServices: string[] = [];
        
        if (ipDuplicado) {
          hasDuplicateConsul = true;
          consulServices = servicosComIp;
          
          setPrechecks((prev) =>
            prev.map((entry) =>
              entry.key === 'os'
                ? { 
                    ...entry, 
                    status: 'failed', 
                    detail: `⚠️ IP/Host ${host} JÁ EXISTE no Consul!\n\nServiços encontrados: ${servicosComIp.join(', ')}\n\nSistema detectado: ${connectionTest.data.details.os} ${connectionTest.data.details.version} (${connectionTest.data.details.architecture})\n\n⚠️ ATENÇÃO: Instalar novamente pode causar conflitos de dados no Consul!` 
                  }
                : entry,
            ),
          );
          
          message.warning(`⚠️ IP/Host ${host} já existe no Consul! Serviços: ${servicosComIp.join(', ')}`, 8);
        } else {
          setPrechecks((prev) =>
            prev.map((entry) =>
              entry.key === 'os'
                ? { 
                    ...entry, 
                    status: 'success', 
                    detail: `✅ IP/Host ${host} não existe no Consul (OK para instalar)\n\nSistema detectado: ${connectionTest.data.details.os} ${connectionTest.data.details.version} (${connectionTest.data.details.architecture})` 
                  }
                : entry,
            ),
          );
        }

        // 3. Verificação de portas e instalação existente
        await new Promise((resolve) => setTimeout(resolve, 300));
        setPrechecks((prev) =>
          prev.map((entry) =>
            entry.key === 'ports'
              ? { ...entry, status: 'running', detail: 'Verificando porta do exporter e instalação existente...' }
              : entry,
          ),
        );

        const exporterPort = targetType === 'windows' ? 9182 : 9100;
        
        // ===== VERIFICAÇÃO REAL DE INSTALAÇÃO EXISTENTE =====
        let portOpen = false;
        let serviceRunning = false;
        let hasConfig = false;
        let hasExistingInstall = false;
        
        try {
          // Buscar dados do formulário
          const sshHost = form.getFieldValue('host');
          const sshPort = form.getFieldValue('port');
          const sshUsername = form.getFieldValue('username');
          const sshPassword = form.getFieldValue('password');
          const useDomain = form.getFieldValue('useDomain');
          const domain = form.getFieldValue('domain');
          
          // Montar payload com domain se necessário
          const parsedPort =
            typeof sshPort === 'number'
              ? sshPort
              : Number(sshPort) || (targetType === 'windows' ? 5985 : 22);

          const checkPayload: ExistingInstallationCheckRequest = {
            host: sshHost,
            port: parsedPort,
            username: sshUsername,
            password: sshPassword ?? '',
            exporter_port: exporterPort,
            target_type: targetType,
          };
          
          // Adicionar domain para Windows se ativo
          if (targetType === 'windows' && useDomain && domain) {
            checkPayload.domain = domain;
          }
          
          // Verificar porta e instalação via backend
          const checkResponse = await consulAPI.checkExistingInstallation(checkPayload);
          
          if (checkResponse) {
            portOpen = checkResponse.port_open || false;
            serviceRunning = checkResponse.service_running || false;
            hasConfig = checkResponse.has_config || false;
          }
        } catch (error) {
          console.error('Erro ao verificar instalação existente:', error);
          // Não bloquear por erro de verificação - continuar sem detecção
        }
        
        if (portOpen || serviceRunning || hasConfig) {
          hasExistingInstall = true;
          
          const existingDetails = {
            detected: true,
            portOpen,
            serviceRunning,
            hasConfig
          };
          
          setExistingInstallation(existingDetails);
          
          // Construir mensagem detalhada
          const exporterName = targetType === 'windows' ? 'windows_exporter' : 'node_exporter';
          let warningDetails = `⚠️ Instalação existente detectada em ${host}:\n\n`;
          if (portOpen) warningDetails += `• Porta ${exporterPort} está em uso\n`;
          if (serviceRunning) warningDetails += `• Serviço ${exporterName} está rodando\n`;
          if (hasConfig) warningDetails += `• Arquivo de configuração encontrado\n`;
          warningDetails += `\n⚠️ Continuar irá substituir a instalação existente!`;
          
          setPrechecks((prev) =>
            prev.map((entry) =>
              entry.key === 'ports'
                ? { 
                    ...entry, 
                    status: 'failed', 
                    detail: warningDetails
                  }
                : entry,
            ),
          );
          
          message.warning(`Instalação existente encontrada em ${host}. Revisar antes de continuar.`, 6);
        } else {
          setExistingInstallation(null);
          
          setPrechecks((prev) =>
            prev.map((entry) =>
              entry.key === 'ports'
                ? { 
                    ...entry, 
                    status: 'success', 
                    detail: `✅ Porta ${exporterPort} disponível\n✅ Nenhuma instalação anterior detectada` 
                  }
                : entry,
            ),
          );
        }
        
        // APÓS TODAS AS VERIFICAÇÕES: Tratar apenas INSTALAÇÃO EXISTENTE primeiro
        
        // 🎯 CENÁRIO 1: SEMPRE mostrar instalação existente PRIMEIRO (se detectada)
        if (hasExistingInstall) {
          // Atualizar estado de instalação existente
          setExistingInstallation({
            detected: true,
            portOpen: portOpen,
            serviceRunning: serviceRunning,
            hasConfig: hasConfig
          });
          
          // 🔥 DESMARCAR "Registrar no Consul" automaticamente
          setAutoRegister(false);
          message.warning('⚠️ "Registrar no Consul" foi DESMARCADO automaticamente (instalação existente detectada)', 6);
          
          // Mostrar modal APENAS de instalação existente
          setWarningModalTitle('⚙️ Instalação existente detectada no servidor');
          setWarningModalContent({
            duplicateConsul: false, // NÃO mostrar IP duplicado neste modal
            existingInstall: true,
            services: [],
            portOpen: portOpen,
            serviceRunning: serviceRunning,
            hasConfig: hasConfig,
            targetType: targetType
          });
          setWarningModalMode('precheck-warning');
          setWarningModalVisible(true);
        }
        // 🎯 CENÁRIO 2: Se NÃO tem instalação existente mas TEM IP duplicado
        else if (hasDuplicateConsul) {
          setAutoRegister(false);
          message.warning('⚠️ "Registrar no Consul" foi DESMARCADO automaticamente (IP duplicado)', 6);
          
          setWarningModalTitle('🚫 IP/Host já existe no Consul');
          setWarningModalContent({
            duplicateConsul: true,
            existingInstall: false,
            services: consulServices,
            portOpen: false,
            serviceRunning: false,
            hasConfig: false,
            targetType: targetType
          });
          setWarningModalMode('precheck-warning');
          setWarningModalVisible(true);
        }
        
        // 📝 GUARDAR informação de IP duplicado para verificação posterior
        // (quando usuário MARCAR o switch de Registrar no Consul)
        if (hasDuplicateConsul) {
          console.log('💾 Guardando IP duplicado no sessionStorage para verificação futura');
          sessionStorage.setItem('consulIPDuplicate', 'true');
          sessionStorage.setItem('consulIPServices', JSON.stringify(consulServices));
        } else {
          sessionStorage.removeItem('consulIPDuplicate');
          sessionStorage.removeItem('consulIPServices');
        }

        // 4. Espaço em disco (simulado - TODO: implementar verificação real)
        await new Promise((resolve) => setTimeout(resolve, 300));
        setPrechecks((prev) =>
          prev.map((entry) =>
            entry.key === 'disk'
              ? { ...entry, status: 'running', detail: 'Verificando espaço em disco...' }
              : entry,
          ),
        );

        await new Promise((resolve) => setTimeout(resolve, 500));
        setPrechecks((prev) =>
          prev.map((entry) =>
            entry.key === 'disk'
              ? { 
                  ...entry, 
                  status: 'success', 
                  detail: '✅ Espaço em disco suficiente (simulado)\n\nNOTA: Verificação real será implementada futuramente.' 
                }
              : entry,
          ),
        );

        // 5. Firewall (simulado - informativo apenas)
        await new Promise((resolve) => setTimeout(resolve, 300));
        setPrechecks((prev) =>
          prev.map((entry) =>
            entry.key === 'firewall'
              ? { ...entry, status: 'running', detail: 'Verificando requisitos de firewall...' }
              : entry,
          ),
        );

        await new Promise((resolve) => setTimeout(resolve, 500));
        setPrechecks((prev) =>
          prev.map((entry) =>
            entry.key === 'firewall'
              ? { 
                  ...entry, 
                  status: 'success', 
                  detail: `✅ Firewall (informativo)\n\nCertifique-se de que a porta ${exporterPort} está liberada no firewall do ${host} para acesso do Prometheus.` 
                }
              : entry,
          ),
        );

      } else {
        throw new Error(connectionTest.data.message || 'Falha na conexão');
      }

      setPrecheckRunning(false);
      
      // Verificar se há avisos que impedem avanço automático
      const hasWarnings = existingInstallation?.detected || warningModalVisible;
      
      if (!hasWarnings) {
        message.success('Pre-checks concluído com sucesso. Avançando...');
        setCurrentStep(2);
      } else {
        message.warning('Pre-checks concluído com avisos. Revise antes de continuar.', 6);
      }

    } catch (error: unknown) {
      console.error('Erro no pre-check de conectividade:', error);
      try {
        console.log('🔍 Erro completo:', JSON.stringify(error, null, 2));
      } catch {
        console.log('🔍 Erro completo indisponível para serialização');
      }

      // Análise detalhada do erro para fornecer feedback específico
      let errorTitle = 'Falha na conexão';
      let errorDetails = 'Verifique host, porta, usuário e senha.';
      let errorCategory = 'GERAL';
      let errorCode = 'UNKNOWN';

      const axiosError =
        typeof error === 'object' && error !== null ? (error as AxiosErrorLike) : undefined;

      // Verificar se é um erro HTTP do backend
      if (axiosError?.response) {
        const status = axiosError.response.status ?? 0;
        const responseData = axiosError.response.data;
        const backendMessage =
          typeof responseData === 'string'
            ? responseData
            : responseData?.message ?? responseData?.detail ?? '';

        console.log(`🔍 Status HTTP: ${status}`);
        console.log('🔍 Mensagem backend:', backendMessage);

        // Parse structured error from backend (format: ERROR_CODE|Message|Category)
        errorCode = 'UNKNOWN';
        let errorMsg = String(backendMessage);

        if (typeof backendMessage === 'string' && backendMessage.includes('|')) {
          const parts = backendMessage.split('|');
          errorCode = parts[0] || 'UNKNOWN';
          errorMsg = parts[1] || backendMessage;
          errorCategory = parts[2] || 'GERAL';
        }

        console.log(`🔍 Parsed - Code: ${errorCode}, Category: ${errorCategory}`);

        // 503 = Backend não conseguiu conectar no host remoto
        if (status === 503) {
          if (errorCode === 'ALL_METHODS_FAILED') {
            // Erro específico do multi-connector Windows
            errorTitle = `❌ Todas as conexões falharam - ${host}`;
            
            // Tentar extrair detalhes das tentativas do backend
            let attemptsText = '';
            const fullMessage = String(backendMessage);
            if (fullMessage.includes('Tentativas realizadas:')) {
              const match = fullMessage.match(/Tentativas realizadas:([\s\S]+)/);
              if (match) {
                attemptsText = match[1].trim();
              }
            }
            
            errorDetails = `O sistema tentou conectar usando TODOS os métodos disponíveis, mas nenhum funcionou.\n\n📋 TENTATIVAS REALIZADAS:\n${attemptsText}\n\n✅ AÇÕES NECESSÁRIAS:\n\n🔧 PSEXEC (SMB/445):\n• Usuário precisa estar no grupo 'Administradores'\n• Execute no servidor:\n  net localgroup Administradores ${domain ? domain + '\\' : ''}${username} /add\n• Verifique se serviço 'Netlogon' está rodando\n• Porta 445 deve estar aberta no firewall\n\n🔧 WINRM (5985/5986):\n• Habilite WinRM no servidor:\n  Enable-PSRemoting -Force\n  Set-Item WSMan:\\localhost\\Client\\TrustedHosts -Value "${host}" -Force\n• Configure firewall:\n  New-NetFirewallRule -DisplayName "WinRM HTTP" -Direction Inbound -LocalPort 5985 -Protocol TCP -Action Allow\n\n🔧 SSH (22):\n• Instale OpenSSH Server:\n  Add-WindowsCapability -Online -Name OpenSSH.Server\n  Start-Service sshd\n  Set-Service sshd -StartupType Automatic\n\n💡 RECOMENDAÇÃO:\nComece habilitando WinRM (mais fácil) ou adicione o usuário ao grupo Administradores para PSExec funcionar.`;
          } else if (errorCode === 'CONNECTION_REFUSED') {
            errorTitle = `🚫 Conexão recusada em ${host}:${port}`;
            errorDetails = `${errorMsg}\n\n✅ VERIFICAÇÕES:\n• Execute: ping ${host}\n• O host está online?\n• SSH/WinRM está instalado e rodando?\n• Porta ${port} está aberta no firewall?\n• Tente: telnet ${host} ${port}\n\n📋 COMANDOS ÚTEIS:\n  sudo systemctl status sshd\n  sudo systemctl start sshd`;
          } else if (errorCode === 'PORT_CLOSED') {
            errorTitle = `🚪 Porta ${port} fechada em ${host}`;
            errorDetails = `${errorMsg}\n\nHost respondeu, mas porta ${port} está fechada/filtrada.\n\n✅ VERIFICAÇÕES:\n• SSH está rodando?\n  sudo systemctl status sshd\n• Porta SSH está correta? (padrão: 22)\n• Firewall bloqueando?\n  sudo ufw status\n  sudo ufw allow ${port}/tcp\n• Tente conectar:\n  telnet ${host} ${port}`;
          } else if (errorCode === 'DNS_ERROR') {
            errorTitle = `🌐 DNS não resolveu ${host}`;
            errorDetails = `${errorMsg}\n\n✅ VERIFICAÇÕES:\n• Hostname está correto?\n• DNS está acessível?\n• Tente: nslookup ${host}\n• Alternativa: use o endereço IP diretamente`;
          } else if (errorCode === 'NETWORK_UNREACHABLE') {
            errorTitle = `📡 Rede inacessível - ${host}`;
            errorDetails = `${errorMsg}\n\n✅ VERIFICAÇÕES:\n• Existe rota de rede até ${host}?\n• VPN está ativa (se necessário)?\n• Execute: tracert ${host} (Windows) ou traceroute ${host} (Linux)\n• Firewall corporativo bloqueando?\n• Segmentação de rede permite a comunicação?`;
          } else if (errorCode === 'NETWORK_ERROR') {
            errorTitle = `⚠️ Erro de rede`;
            errorDetails = `${errorMsg}\n\n✅ VERIFICAÇÕES:\n• Conectividade de rede OK?\n• Firewall local/remoto bloqueando?\n• Execute: ping ${host}\n• Cable/Wi-Fi funcionando?`;
          } else if (errorCode === 'TIMEOUT') {
            errorTitle = `⏱️ Timeout ao conectar em ${host}`;
            errorDetails = `${errorMsg}\n\nHost não respondeu em tempo hábil.\n\n✅ POSSÍVEIS CAUSAS:\n• Host ${host} está OFFLINE\n• Host não alcançável pela rede\n• Firewall bloqueando completamente\n• IP incorreto ou não existe na rede\n\n🔍 VERIFIQUE:\n• Execute: ping ${host}\n• Host está ligado?\n• IP/hostname está correto?`;
          } else {
            // Genérico 503
            errorTitle = `❌ Host ${host} inacessível`;
            errorDetails = `O backend não conseguiu estabelecer conexão.\n\n🔌 CONECTIVIDADE:\n• Execute: ping ${host}\n• Host está online e acessível?\n• Porta ${port} está aberta no firewall?\n\n🔐 SERVIÇO:\n• SSH/WinRM está ativo?\n• Porta ${port} é a correta?\n  - SSH padrão: 22\n  - WinRM HTTP: 5985\n  - WinRM HTTPS: 5986\n\n📡 REDE:\n• Existe rota de rede entre backend e ${host}?\n• VPN está ativa (se necessário)?\n• Segurança de rede permite a conexão?`;
          }
        }
        // 401 = Autenticação falhou
        else if (status === 401) {
          errorTitle = `🔐 Autenticação falhou`;
          errorDetails = `${errorMsg || `Usuário '${username}' ou senha incorretos.`}\n\n✅ VERIFICAÇÕES:\n• Usuário '${username}' existe no ${host}?\n• Senha está correta? (atenção a maiúsculas/minúsculas)\n• Usuário está bloqueado ou expirado?\n• Execute no servidor:\n  Linux: id ${username}\n  Windows: net user ${username}\n\n💡 DICA SSH:\n• Teste manual: ssh ${username}@${host} -p ${port}\n• Verifique logs: /var/log/auth.log (Linux)`;
        }
        // 403 = Permissão negada
        else if (status === 403) {
          if (errorCode === 'PERMISSION_DENIED') {
            errorTitle = `🚷 Permissão negada`;
            errorDetails = `${errorMsg}\n\n✅ VERIFICAÇÕES:\n• Chave SSH autorizada? Arquivo: ~/.ssh/authorized_keys\n• Permissões corretas:\n  chmod 700 ~/.ssh\n  chmod 600 ~/.ssh/authorized_keys\n• Usuário '${username}' tem acesso SSH/WinRM?\n• SELinux/AppArmor bloqueando? (Linux)\n• Política de grupo bloqueando? (Windows)\n\n📋 COMANDOS ÚTEIS:\n  Ver permissões: ls -la ~/.ssh/\n  Verificar grupo: groups ${username}`;
          } else {
            errorTitle = `🚷 Acesso negado`;
            errorDetails = `Usuário '${username}' não tem permissões suficientes.\n\n✅ VERIFICAÇÕES:\n• Usuário tem acesso SSH/WinRM?\n• Usuário tem privilégios sudo/administrador?\n• Arquivo authorized_keys configurado?\n• Grupo correto: sudo (Linux) / Administrators (Windows)`;
          }
        }
        // 504 = Timeout
        else if (status === 504) {
          errorTitle = `⏱️ Timeout (>60s)`;
          errorDetails = `${errorMsg || `Host ${host} não respondeu em tempo hábil.`}\n\n✅ VERIFICAÇÕES:\n• Host ${host} está muito lento?\n• Latência de rede alta?\n• Execute: ping ${host} -t (verificar latência)\n• Serviço SSH/WinRM travado?\n• Host sobrecarregado (CPU/memória)?\n\n💡 DICA:\n• Teste com timeout maior\n• Verifique carga do servidor\n• Reinicie o serviço SSH/WinRM se necessário`;
        }
        // 500 = Erro interno do backend
        else if (status === 500) {
          errorTitle = `⚙️ Erro interno do backend`;
          errorDetails = `${errorMsg || 'O backend encontrou um erro inesperado.'}\n\n📋 AÇÃO NECESSÁRIA:\n• Verifique os logs do backend (console do servidor)\n• Pode ser:\n  - Biblioteca SSH/WinRM com problema\n  - Permissões do usuário do backend\n  - Dependência faltando\n\n🔧 DEBUG:\n• Restart do backend pode resolver\n• Verifique requirements.txt instalados`;
        }
        // Outros erros HTTP
        else {
          errorTitle = `❌ Erro HTTP ${status}`;
          errorDetails = errorMsg || 'Erro desconhecido do servidor.\n\nVerifique os logs do backend para mais detalhes.';
        }
      }
      // Erros de rede do cliente (frontend → backend)
      else if (
        axiosError?.code === 'ECONNABORTED' ||
        (axiosError?.message && axiosError.message.includes('timeout'))
      ) {
        const timeoutSeconds = axiosError?.timeout ?? 60;
        errorTitle = `⏱️ Timeout na requisição (> ${timeoutSeconds}s)`;
        errorDetails = `A requisição ao backend demorou muito.\n\n✅ POSSÍVEIS CAUSAS:\n• O host ${host} está muito lento para responder\n• Backend está processando por mais de ${timeoutSeconds}s\n• Conexão SSH/WinRM demorando muito\n• Host pode estar offline ou rede instável\n\n💡 TENTE:\n1. Verificar se o host responde: ping ${host}\n2. Testar conexão manual: ssh ${username}@${host}\n3. Restart do backend se estiver travado`;
      }
      // Erro de conexão frontend → backend
      else if (
        axiosError?.code === 'ERR_NETWORK' ||
        (axiosError?.message && axiosError.message.includes('Network Error'))
      ) {
        errorTitle = `🔌 Backend não responde`;
        errorDetails = `Não foi possível conectar ao backend.\n\n✅ VERIFICAÇÕES:\n• Backend está rodando?\n  URL: http://localhost:5000\n• Execute: cd backend && python app.py\n• Firewall local bloqueando porta 5000?\n• CORS configurado corretamente?\n\n📋 TESTE:\n• Abra: http://localhost:5000/api/v1/health\n• Deve retornar status OK`;
      }
      // Erro JavaScript genérico
      else if (error instanceof Error) {
        errorTitle = `⚠️ ${error.message}`;
        errorDetails = `Erro inesperado no frontend.\n\n🔍 DETALHES:\n${error.message}\n\n💡 AÇÃO:\n• Verifique console do navegador (F12)\n• Compartilhe o erro completo para suporte`;
      }
      // Erro completamente desconhecido
      else {
        let serializedError = '';
        try {
          serializedError = JSON.stringify(error, null, 2);
        } catch {
          serializedError = String(error);
        }
        errorTitle = `❓ Erro desconhecido`;
        errorDetails = `Tipo de erro não reconhecido.\n\n🔍 DEBUG:\nAbra o console (F12) e compartilhe o erro completo.\n\nErro: ${serializedError}`;
      }
      
      // Mostrar modal de erro detalhado
      setErrorModalIcon(errorCode);
      setErrorModalTitle(errorTitle);
      setErrorModalContent(errorDetails);
      setErrorCategory(errorCategory);
      setErrorModalVisible(true);
      
      setPrechecks((prev) =>
        prev.map((entry) =>
          entry.key === 'connectivity'
            ? { 
                ...entry, 
                status: 'failed', 
                detail: `❌ ${errorTitle}` 
              }
            : entry.status === 'running' || entry.status === 'pending'
            ? { ...entry, status: 'pending', detail: 'Cancelado devido à falha de conexão.' }
            : entry,
        ),
      );

      setPrecheckRunning(false);
      message.error(`Falha na conexão - veja detalhes no modal`, 5);
    }
  };

  const buildInstallPlan = (): string[] => {
    const host = form.getFieldValue('host') || '<host>';
    const port = form.getFieldValue('port') || (connectionMethod === 'fallback' ? 5985 : 22);
    const username = form.getFieldValue('username') || '<usuario>';
    const exporterPort = targetType === 'windows' ? '9182' : '9100';
    const sshPrefix = `ssh -p ${port} ${username}@${host}`;
    const versionToken = selectedVersion === 'latest' ? '\\${VERSION}' : selectedVersion;
    const plan: string[] = [];

    if (targetType === 'linux') {
      const extraCollectors = selectedCollectors.filter((collector) => collector !== 'node');
      if (selectedVersion === 'latest') {
        plan.push(
          '[LINUX] Detectar release mais recente: VERSION=$(curl -s https://api.github.com/repos/prometheus/node_exporter/releases/latest | jq -r ".tag_name")',
        );
      } else {
        plan.push(`[LINUX] Utilizar release ${selectedVersion} do node_exporter.`);
      }
      plan.push(
        `[LINUX] Criar usuario dedicado: ${sshPrefix} "sudo useradd --system --no-create-home --shell /usr/sbin/nologin node_exporter || true"`,
      );
      plan.push(
        `[LINUX] Baixar binarios: ${sshPrefix} "curl -fsSL https://github.com/prometheus/node_exporter/releases/download/${selectedVersion === 'latest' ? '\\${VERSION}' : selectedVersion}/node_exporter-${versionToken}.linux-amd64.tar.gz -o /tmp/node_exporter.tar.gz"`,
      );
      plan.push(
        `[LINUX] Instalar binario: ${sshPrefix} "sudo tar -xf /tmp/node_exporter.tar.gz -C /usr/local/bin --strip-components=1 node_exporter-${versionToken}.linux-amd64/node_exporter && sudo chown node_exporter:node_exporter /usr/local/bin/node_exporter"`,
      );
      
      if (useBasicAuth && basicAuthPassword) {
        plan.push(
          `[LINUX] Criar diretorio de configuracao: ${sshPrefix} "sudo mkdir -p /etc/node_exporter"`,
        );
        plan.push(
          `[LINUX] Gerar senha bcrypt: ${sshPrefix} "htpasswd -nbBC 10 ${basicAuthUser} '${basicAuthPassword}' | sudo tee /etc/node_exporter/htpasswd"`,
        );
        plan.push(
          `[LINUX] Criar config.yml com Basic Auth: ${sshPrefix} "cat <<'EOF' | sudo tee /etc/node_exporter/config.yml
basic_auth_users:
  ${basicAuthUser}: <bcrypt_hash>
EOF"`,
        );
        plan.push(
          `[LINUX] Ajustar permissoes: ${sshPrefix} "sudo chown -R node_exporter:node_exporter /etc/node_exporter && sudo chmod 640 /etc/node_exporter/config.yml"`,
        );
      }
      
      plan.push(
        `[LINUX] Publicar unit systemd: ${sshPrefix} "cat <<'EOF' | sudo tee /etc/systemd/system/node_exporter.service >/dev/null
[Unit]
Description=Prometheus Node Exporter
After=network-online.target

[Service]
User=node_exporter
Group=node_exporter
Type=simple
ExecStart=/usr/local/bin/node_exporter --web.listen-address=':${exporterPort}'${useBasicAuth ? ' --web.config.file=/etc/node_exporter/config.yml' : ''}${extraCollectors.length ? ' --collector.' + extraCollectors.join(' --collector.') : ''}
Restart=on-failure

[Install]
WantedBy=multi-user.target
EOF"`,
      );
      if (extraCollectors.includes('textfile')) {
        plan.push(
          `[LINUX] Preparar diretorio textfile: ${sshPrefix} "sudo mkdir -p /var/lib/node_exporter/textfile && sudo chown node_exporter:node_exporter /var/lib/node_exporter/textfile"`,
        );
      }
      if (extraCollectors.includes('iostat')) {
        plan.push(
          `[LINUX] Habilitar sysstat para collector iostat: ${sshPrefix} "sudo apt-get install -y sysstat || sudo yum install -y sysstat"`,
        );
      }
      plan.push(
        `[LINUX] Ativar servico: ${sshPrefix} "sudo systemctl daemon-reload && sudo systemctl enable node_exporter && sudo systemctl start node_exporter"`,
      );
      plan.push(
        `[LINUX] Ajustar firewall (ufw/firewalld): ${sshPrefix} "sudo ufw allow ${exporterPort}/tcp || sudo firewall-cmd --add-port=${exporterPort}/tcp --permanent && sudo firewall-cmd --reload"`,
      );
      plan.push(
        `[LINUX] Validar metricas: ${sshPrefix} "curl ${useBasicAuth ? `-u ${basicAuthUser}:${basicAuthPassword}` : ''} -fsSL http://127.0.0.1:${exporterPort}/metrics | head"`,
      );
    } else if (connectionMethod === 'fallback') {
      const extraCollectors = selectedCollectors
        .filter((collector) => collector !== 'wmi')
        .map((collector) => collector.replace(/_/g, ''));
      const enabledCollectors = ['cpu', 'logical_disk', 'os', 'system'].concat(extraCollectors);
      if (selectedVersion === 'latest') {
        plan.push(
          '[WINRM] Detectar release: $Version = (Invoke-RestMethod -Uri "https://api.github.com/repos/prometheus-community/windows_exporter/releases/latest").tag_name',
        );
      } else {
        plan.push(`[WINRM] Utilizar release ${selectedVersion} do windows_exporter.`);
      }
      plan.push(
        `[WINRM] Validar WinRM: Test-WSMan -ComputerName ${host} -Port ${port} -Authentication Default`,
      );
      plan.push(
        `[WINRM] Garantir diretorio temporario: New-Item -ItemType Directory -Path 'C:\\Temp' -Force`,
      );
      plan.push(
        `[WINRM] Baixar instalador: Invoke-WebRequest -Uri "https://github.com/prometheus-community/windows_exporter/releases/download/${selectedVersion === 'latest' ? '$Version' : selectedVersion}/windows_exporter-${selectedVersion === 'latest' ? '$Version' : selectedVersion}-amd64.msi" -OutFile "C:\\Temp\\windows_exporter.msi"`,
      );
      plan.push(
        `[WINRM] Instalar via msiexec: Start-Process msiexec.exe -Wait -ArgumentList '/i C:\\Temp\\windows_exporter.msi ENABLED_COLLECTORS=${enabledCollectors.join(',')} LISTEN_PORT=${exporterPort} /qn'`,
      );
      plan.push(
        `[WINRM] Garantir inicializacao automatica: Set-Service -Name windows_exporter -StartupType Automatic`,
      );
      plan.push(
        `[WINRM] Liberar firewall: New-NetFirewallRule -DisplayName "windows_exporter ${exporterPort}" -Direction Inbound -Action Allow -Protocol TCP -LocalPort ${exporterPort}`,
      );
      plan.push(
        `[WINRM] Validar metricas: Invoke-WebRequest -UseBasicParsing -Uri "http://localhost:${exporterPort}/metrics" | Select-Object -First 20`,
      );
    } else {
      const extraCollectors = selectedCollectors
        .filter((collector) => collector !== 'wmi')
        .map((collector) => collector.replace(/_/g, ''));
      const enabledCollectors = ['cpu', 'logical_disk', 'os', 'system'].concat(extraCollectors);
      if (selectedVersion === 'latest') {
        plan.push(
          '[WIN-SSH] Detectar release: $Version = (Invoke-RestMethod -Uri "https://api.github.com/repos/prometheus-community/windows_exporter/releases/latest").tag_name',
        );
      } else {
        plan.push(`[WIN-SSH] Utilizar release ${selectedVersion} do windows_exporter.`);
      }
      plan.push(
        `[WIN-SSH] Criar diretorio temporario: ${sshPrefix} "powershell.exe -Command \\"New-Item -ItemType Directory -Path 'C:/Temp' -Force\\""`,
      );
      plan.push(
        `[WIN-SSH] Copiar instalador via SCP: scp -P ${port} windows_exporter-${selectedVersion === 'latest' ? '$Version' : selectedVersion}-amd64.msi ${username}@${host}:"C:/Temp/"`,
      );
      plan.push(
        `[WIN-SSH] Instalar exporter: ${sshPrefix} "powershell.exe -Command \\"Start-Process msiexec.exe -ArgumentList '/i C:\\\\Temp\\\\windows_exporter-${selectedVersion === 'latest' ? '$Version' : selectedVersion}-amd64.msi ENABLED_COLLECTORS=${enabledCollectors.join(',')} LISTEN_PORT=${exporterPort} /qn' -Wait\\""`,
      );
      plan.push(
        `[WIN-SSH] Abrir firewall: ${sshPrefix} "powershell.exe -Command \\"New-NetFirewallRule -DisplayName 'windows_exporter ${exporterPort}' -Direction Inbound -Action Allow -Protocol TCP -LocalPort ${exporterPort}\\""`,
      );
      plan.push(
        `[WIN-SSH] Validar servico: ${sshPrefix} "powershell.exe -Command \\"Get-Service -Name windows_exporter\\""`,
      );
      plan.push(
        `[WIN-SSH] Validar metricas: ${sshPrefix} "powershell.exe -Command \\"Invoke-WebRequest -UseBasicParsing -Uri 'http://localhost:${exporterPort}/metrics' | Select-Object -First 10\\""`,
      );
    }

    if (autoRegister) {
      // Preparar metadata do Consul incluindo informações de autenticação
      const consulMeta = {
        datacenter: selectedNodeAddress,
        module: targetType === 'linux' ? 'selfnode_exporter' : 'windows_exporter',
        env: 'production',
        ...(useBasicAuth && basicAuthUser && basicAuthPassword ? {
          basic_auth_enabled: 'true',
          basic_auth_user: basicAuthUser
        } : {})
      };
      
      // Health check com ou sem autenticação (funciona para Linux e Windows)
      const healthCheckConfig = useBasicAuth && basicAuthUser && basicAuthPassword
        ? `"Check":{"HTTP":"http://${host}:${exporterPort}/metrics","Interval":"30s","Header":{"Authorization":["Basic $(echo -n '${basicAuthUser}:${basicAuthPassword}' | base64)"]}}`
        : `"Check":{"HTTP":"http://${host}:${exporterPort}/metrics","Interval":"30s"}`;
      
      plan.push(
        `[CONSUL] Registrar servico (datacenter=${selectedNodeAddress}): curl -X PUT http://CONSUL_API/v1/agent/service/register -d '{"ID":"${targetType}-exporter-${host}","Name":"${targetType}-exporter","Address":"${host}","Port":${exporterPort},"Meta":${JSON.stringify(consulMeta)},${healthCheckConfig}}'`,
      );
    }

    plan.push(
      `[VERIFICACAO] Confirmar scraping no Prometheus apontando para http://${host}:${exporterPort}/metrics${useBasicAuth ? ` (com Basic Auth: ${basicAuthUser})` : ''}.`,
    );

    return plan;
  };

  void buildInstallPlan;

  const handleInstall = async () => {
    setInstallRunning(true);
    setInstallSuccess(null);
    setInstallLogs([]);

    try {
      // Validar campos obrigatórios
      const authType = form.getFieldValue('authType');
      const host = form.getFieldValue('host');
      const port = form.getFieldValue('port');
      const username = form.getFieldValue('username');
      const password = form.getFieldValue('password');
      const keyPath = form.getFieldValue('keyPath');
      const useDomain = form.getFieldValue('useDomain');
      const domain = form.getFieldValue('domain');

      if (!host || !port || !username) {
        message.error('Preencha todos os campos obrigatórios');
        setInstallRunning(false);
        return;
      }

      if (authType === 'password' && !password) {
        message.error('Senha é obrigatória para autenticação por senha');
        setInstallRunning(false);
        return;
      }

      if (authType === 'key' && !keyPath && !privateKeyFile) {
        message.error('Chave SSH é obrigatória para autenticação por chave');
        setInstallRunning(false);
        return;
      }

    appendLog('🚀 Iniciando instalação remota...');
    appendLog(`📡 Conectando em ${host}:${port} como ${username}...`, 'progress');
      
      // Abrir modal de logs automaticamente
      setLogModalVisible(true);

      if (selectedNodeAddress) {
        appendLog(`🏢 Nó Consul selecionado: ${selectedNodeLabel}`);
      }

      // Preparar request para o backend
      const methodToSend: InstallerRequest['method'] =
        targetType === 'windows'
          ? (resolvedWindowsMethod ?? 'psexec')
          : connectionMethod === 'fallback'
          ? 'winrm'
          : 'ssh';

      appendLog(`🛠️ Método de instalação selecionado: ${methodToSend.toUpperCase()}`);

      const installRequest: InstallerRequest = {
        os_type: targetType,
        method: methodToSend,
        host,
        username,
        collector_profile: selectedCollectors.join(','),
        register_in_consul: autoRegister,
      };

      if (selectedNodeAddress) {
        installRequest.consul_node = selectedNodeAddress;
      }

      if (targetType === 'linux') {
        const parsedPort = parseInt(String(port ?? '22'), 10);
        installRequest.ssh_port = Number.isNaN(parsedPort) ? 22 : parsedPort;

        if (authType === 'password') {
          installRequest.password = password;
        } else {
          installRequest.key_file = privateKeyFile || keyPath;
        }

        installRequest.use_sudo = true;

        if (useBasicAuth && basicAuthUser && basicAuthPassword) {
          installRequest.basic_auth_user = basicAuthUser;
          installRequest.basic_auth_password = basicAuthPassword;
          appendLog(`🔒 Basic Auth habilitado (usuário: ${basicAuthUser})`, 'info');
        }
      } else {
        if (authType === 'password' && password) {
          installRequest.password = password;
        }

        if (useDomain && domain) {
          installRequest.domain = domain;
          appendLog(`🏢 Usando conta de domínio: ${domain}\\${username}`, 'info');
        }

        if (methodToSend === 'winrm') {
          const winrmPort = parseInt(String(port ?? '5985'), 10);
          installRequest.port = Number.isNaN(winrmPort) ? 5985 : winrmPort;
          installRequest.use_ssl = false;
        } else if (methodToSend === 'ssh') {
          const sshPort = parseInt(String(port ?? '22'), 10);
          installRequest.ssh_port = Number.isNaN(sshPort) ? 22 : sshPort;
        } else if (!installRequest.psexec_path) {
          installRequest.psexec_path = 'psexec.exe';
        }

        if (useBasicAuth && basicAuthUser && basicAuthPassword) {
          installRequest.basic_auth_user = basicAuthUser;
          installRequest.basic_auth_password = basicAuthPassword;
          appendLog(`🔒 Basic Auth habilitado (usuário: ${basicAuthUser})`, 'info');
        }
      }

  appendLog('📤 Enviando requisição para o backend...', 'progress');

      // Chamar API de instalação
      const response = await consulAPI.startInstallation(installRequest);

      if (!response.data.success) {
        throw new Error(response.data.message || 'Erro ao iniciar instalação');
      }

  const installationId = response.data.installation_id;
  appendLog(`✅ Instalação iniciada (ID: ${installationId})`, 'success');
  appendLog('📊 Acompanhando progresso...', 'progress');

      // Polling do status (poderia ser WebSocket no futuro)
      const pollStatus = async () => {
        try {
          const statusResponse = await consulAPI.getInstallationStatus(installationId);
          const status: InstallStatusResponse = statusResponse.data;

          // Processar logs do backend se existirem
          if (Array.isArray(status.logs) && status.logs.length > 0) {
            const remoteEntries = mapBackendLogs(status.logs, installationId);

            setInstallLogs((prev) => {
              if (remoteEntries.length === 0) {
                return prev;
              }

              // Separar logs locais e remotos existentes
              const localLogs = prev.filter((log) => log.source === 'local');
              const remoteLogs = prev.filter((log) => log.source === 'remote');
              
              // Criar mapa de logs remotos existentes para merge
              const remoteLogsByKey = new Map(remoteLogs.map((log) => [log.key, log]));
              
              // Atualizar/adicionar logs remotos
              const updatedRemoteLogs: InstallLogEntry[] = [];
              remoteEntries.forEach((entry) => {
                const existing = remoteLogsByKey.get(entry.key);
                if (existing) {
                  // Atualizar se mudou
                  if (
                    existing.message !== entry.message ||
                    existing.level !== entry.level ||
                    existing.details !== entry.details ||
                    existing.timestamp !== entry.timestamp
                  ) {
                    updatedRemoteLogs.push(entry);
                  } else {
                    updatedRemoteLogs.push(existing);
                  }
                } else {
                  // Novo log remoto
                  updatedRemoteLogs.push(entry);
                }
              });

              // Combinar logs locais + logs remotos atualizados
              const combined = [...localLogs, ...updatedRemoteLogs];
              
              // Ordenar por timestamp
              return combined.sort((a, b) => {
                const timeA = a.timestamp ?? a.key;
                const timeB = b.timestamp ?? b.key;
                if (timeA === timeB) {
                  return a.key.localeCompare(b.key);
                }
                return timeA.localeCompare(timeB);
              });
            });
          }

          // Verificar se completou
          if (status.status === 'completed') {
            appendLog('✅ Instalação concluída com sucesso!', 'success');
            setInstallSuccess(true);
            setInstallRunning(false);
            setCurrentStep(4); // Ir para tela de validação
            message.success('Exporter instalado e validado!');
            return;
          }

          if (status.status === 'failed') {
            appendLog(`❌ Instalação falhou: ${status.message}`, 'error');
            if (status.error_code) {
              appendLog(`📛 Código do erro: ${status.error_code}`, 'error');
            }
            if (status.error_details) {
              appendLog(`📝 Detalhes: ${status.error_details}`, 'error');
            }
            setInstallSuccess(false);
            setInstallRunning(false);
            setCurrentStep(4); // Ir para tela de validação mesmo com falha
            const userMessage = status.message?.replace(/^Erro:\s*/i, '') ?? 'Falha na instalação';
            message.error(userMessage || 'Falha na instalação');
            return;
          }

          // Continuar polling se ainda estiver rodando
          if (status.status === 'running' || status.status === 'pending') {
            appendLog(`⏳ Progresso: ${status.progress}% - ${status.message}`, 'progress');
            setTimeout(pollStatus, 2000); // Poll a cada 2 segundos
          }
        } catch (error) {
          console.error('Erro ao verificar status:', error);
          appendLog(`⚠️ Erro ao verificar status: ${error}`, 'warning');
          setTimeout(pollStatus, 3000); // Retry após 3 segundos
        }
      };

      // Iniciar polling
      setTimeout(pollStatus, 1000);

    } catch (error) {
      console.error('Erro na instalação:', error);
      const errorMessage = error instanceof Error ? error.message : 'Erro desconhecido';
  appendLog(`❌ Erro: ${errorMessage}`, 'error');
      setInstallSuccess(false);
      setInstallRunning(false);
      message.error('Erro ao iniciar instalação');
    }
  };

  const handleReset = () => {
    form.resetFields();
    setTargetType('linux');
    setCurrentStep(0);
    setPrechecks(
      DEFAULT_PRECHECKS.map((item) => ({
        ...item,
        status: 'pending',
        detail: undefined,
      })),
    );
    setInstallLogs([]);
    setInstallSuccess(null);
    setInstallRunning(false);
    setSelectedCollectors(['node', 'filesystem', 'systemd']);
    setSelectedVersion('latest');
    setUseBasicAuth(true);
    setBasicAuthUser('prometheus');
    setBasicAuthPassword('');
    setAutoRegister(true);
    setSelectedNodeAddress(nodes[0]?.addr ?? '');
    setConnectionMethod('ssh');
    setResolvedWindowsMethod(null);
    setPrivateKeyFile('');
    setExistingInstallation(null);
  };

  const availableCollectorOptions = useMemo(
    () => COLLECTOR_OPTIONS.filter((item) => item.targets.includes(targetType)),
    [targetType],
  );

  const collectorHelpText = selectedCollectors.length
    ? `${selectedCollectors.length} coletor(es) selecionado(s)`
    : 'Nenhum coletor selecionado';

  // Buscar nós do Consul para o seletor
  useEffect(() => {
    const fetchNodes = async () => {
      setLoadingNodes(true);
      try {
        const response = await consulAPI.getNodes();
        const payload = response.data?.data ?? response.data ?? [];
        const rawNodes = Array.isArray(payload) ? payload : [];
        const normalizedNodes = rawNodes
          .map((item) => normalizeConsulNode(item as Record<string, unknown>))
          .filter((node) => Boolean(node.addr));

        const activeNodes = normalizedNodes
          .filter((node) => (node.status ?? 'alive') === 'alive')
          .sort((a, b) => (a.node ?? '').localeCompare(b.node ?? ''));
        
        setNodes(activeNodes);

        // Auto-selecionar o primeiro nó se nenhum estiver selecionado ainda
        setSelectedNodeAddress((previous) => {
          if (previous || activeNodes.length === 0) {
            return previous;
          }
          return activeNodes[0]?.addr ?? '';
        });
      } catch (error) {
        console.error('Erro ao buscar nós do Consul:', error);
        message.error('Falha ao carregar nós do Consul. Verifique a conexão com o backend.');
      } finally {
        setLoadingNodes(false);
      }
    };

    fetchNodes();
  }, []);

  useEffect(() => {
    const allowedValues = new Set(availableCollectorOptions.map((option) => option.value));
    setSelectedCollectors((prev) => {
      const filtered = prev.filter((value) => allowedValues.has(value));
      if (filtered.length === prev.length && filtered.length > 0) {
        return prev;
      }
      if (filtered.length > 0) {
        return filtered;
      }
      return targetType === 'windows' ? ['wmi'] : ['node'];
    });
  }, [availableCollectorOptions, targetType]);

  const exporterVersions = useMemo(
    () => [
      { value: 'latest', label: 'Ultima versao estavel' },
      { value: '1.7.0', label: '1.7.0 (Linux)' },
      { value: '1.6.1', label: '1.6.1 (Windows)' },
    ],
    [],
  );
  const renderTargetContent = () => {
    const connectionOptions =
      targetType === 'linux'
        ? [
            {
              value: 'ssh' as const,
              label: 'SSH (porta 22)',
            },
          ]
        : [];  // Windows não tem opções - é automático

    const connectionHint =
      targetType === 'linux'
        ? 'O instalador executa todos os comandos via SSH com privilégios elevados via sudo.'
        : '🔄 O instalador tenta automaticamente múltiplos métodos de conexão:\n\n1️⃣ PSExec (porta 445/SMB) - Mais comum\n2️⃣ WinRM (porta 5985) - Se PSExec falhar\n3️⃣ SSH/OpenSSH (porta 22) - Último recurso\n\nNão é necessário configurar nada manualmente - o sistema escolhe o melhor método disponível!';

    return (
      <Space direction="vertical" size="large" style={{ width: '100%' }}>
        <Paragraph>
          Escolha o sistema alvo. Para Windows, o instalador tenta automaticamente todos os métodos de conexão disponíveis.
        </Paragraph>

        <Row gutter={16}>
          <Col xs={24} md={targetType === 'linux' ? 12 : 24}>
            <Card title="Sistema operacional" size="small" variant="borderless" style={{ background: '#fafafa' }}>
              <Space direction="vertical" size="middle" style={{ width: '100%' }}>
                <Select
                  value={targetType}
                  onChange={(value: 'linux' | 'windows') => {
                    setTargetType(value);
                    form.setFieldsValue({ targetType: value });
                  }}
                  style={{ width: '100%' }}
                >
                  <Option value="linux">
                    <Space>
                      <LinuxOutlined />
                      Linux (via SSH)
                    </Space>
                  </Option>
                  <Option value="windows">
                    <Space>
                      <WindowsOutlined />
                      Windows (conexão automática)
                    </Space>
                  </Option>
                </Select>
                <Paragraph type="secondary" style={{ margin: 0, whiteSpace: 'pre-line' }}>
                  {connectionHint}
                </Paragraph>
              </Space>
            </Card>
          </Col>

          {/* Só mostrar seleção de método se for Linux */}
          {targetType === 'linux' && (
            <Col xs={24} md={12}>
              <Card title="Método de conexão" size="small" variant="borderless" style={{ background: '#fafafa' }}>
                <Space direction="vertical" size="middle" style={{ width: '100%' }}>
                  <Select
                    value={connectionMethod}
                    onChange={(value: 'ssh' | 'fallback') => setConnectionMethod(value)}
                    style={{ width: '100%' }}
                    disabled={connectionOptions.length === 1}
                  >
                    {connectionOptions.map((option) => (
                      <Option value={option.value} key={option.value}>
                        {option.label}
                      </Option>
                    ))}
                  </Select>
                  <Paragraph type="secondary" style={{ margin: 0 }}>
                    SSH é o método padrão para servidores Linux.
                  </Paragraph>
                </Space>
              </Card>
            </Col>
          )}
        </Row>

        <Space>
          <Button type="primary" icon={<CloudServerOutlined />} onClick={() => setCurrentStep(1)}>
            Ir para pre-checks
          </Button>
        </Space>
      </Space>
    );
  };

  const renderPrecheckContent = () => {
    // Determinar labels e placeholders baseado no tipo de conexão
    const isWindows = targetType === 'windows';
    const isLinux = targetType === 'linux';

    const portLabel = 'Porta SSH';
    const portPlaceholder = '22';
    const portMessage = 'Informe a porta SSH';

    const userPlaceholder = isLinux ? 'root' : 'Administrator';
    const keyPathPlaceholder =
      targetType === 'windows'
        ? 'C:\\Users\\Administrator\\.ssh\\id_rsa'
        : '/home/user/.ssh/id_rsa';
    
    // Windows: apenas senha (multi-connector cuida de tudo)
    // Linux: senha ou chave SSH
    const authOptions = isWindows
      ? [{ value: 'password', label: 'Senha (conexão automática)' }]
      : [
          { value: 'password', label: 'Senha' },
          { value: 'key', label: 'Chave SSH' },
        ];

    return (
      <Space direction="vertical" size="large" style={{ width: '100%' }}>
        <Paragraph>
          Informe o alvo e execute os pre-checks para validar conectividade, sistema
          operacional e dependências antes de instalar o exporter.
        </Paragraph>

        {isWindows && (
          <Alert
            message="🔄 Conexão Automática Multi-Método"
            description="Para Windows, o sistema tenta automaticamente PSExec → WinRM → SSH. Você só precisa fornecer IP e credenciais!"
            type="info"
            showIcon
            style={{ marginBottom: 16 }}
          />
        )}

        <Form
          layout="vertical"
          form={form}
          initialValues={{ port: 22, authType: 'password' }}
          style={{ maxWidth: 920 }}
        >
          {/* Linha 1: IP/Hostname, Porta (só Linux), Tipo de Autenticação */}
          <Row gutter={16}>
            <Col xs={24} md={isWindows ? 14 : 10}>
              <Form.Item
                name="host"
                label="IP ou hostname"
                rules={[{ required: true, message: 'Informe o IP ou hostname' }]}
              >
                <Input placeholder="Ex: 192.168.1.20" allowClear />
              </Form.Item>
            </Col>
            
            {/* Porta: apenas para Linux */}
            {isLinux && (
              <Col xs={24} md={6}>
                <Form.Item
                  name="port"
                  label={portLabel}
                  rules={[{ required: true, message: portMessage }]}
                >
                  <Input placeholder={portPlaceholder} allowClear />
                </Form.Item>
              </Col>
            )}
            
            <Col xs={24} md={isWindows ? 10 : 8}>
              <Form.Item
                name="authType"
                label="Autenticação"
                rules={[{ required: true, message: 'Selecione o método de autenticação' }]}
              >
                <Select disabled={authOptions.length === 1}>
                  {authOptions.map((option) => (
                    <Option value={option.value} key={option.value}>
                      {option.label}
                    </Option>
                  ))}
                </Select>
              </Form.Item>
            </Col>
          </Row>

          {/* Linha 2: Switch de Domínio ANTES + Domínio/Usuário/Senha na mesma linha */}
          <Form.Item noStyle shouldUpdate={(prev, cur) => prev.authType !== cur.authType || prev.targetType !== cur.targetType}>
            {({ getFieldValue }) => {
              const authType = getFieldValue('authType');
              const currentTargetType = getFieldValue('targetType');
              const isWindowsTarget = currentTargetType === 'windows';
              
              if (authType === 'password') {
                return (
                  <>
                    {/* Switch de Domínio ANTES dos campos (apenas Windows) */}
                    {isWindowsTarget && (
                      <Row gutter={16} style={{ marginBottom: 16 }}>
                        <Col xs={24}>
                          <Card size="small" style={{ background: '#f0f5ff', border: '1px solid #adc6ff' }}>
                            <Space>
                              <Form.Item
                                name="useDomain"
                                valuePropName="checked"
                                style={{ marginBottom: 0 }}
                              >
                                <Switch />
                              </Form.Item>
                              <span style={{ fontWeight: 500 }}>
                                Conta de Domínio (Active Directory)
                              </span>
                              <Tooltip title="Ative esta opção se o usuário pertence a um domínio Windows">
                                <span style={{ color: '#8c8c8c', cursor: 'help' }}>ℹ️</span>
                              </Tooltip>
                            </Space>
                          </Card>
                        </Col>
                      </Row>
                    )}
                    
                    {/* Campos de Autenticação: Domínio | Usuário | Senha na mesma linha */}
                    <Form.Item noStyle shouldUpdate={(prev, cur) => prev.useDomain !== cur.useDomain}>
                      {({ getFieldValue }) => {
                        const useDomain = getFieldValue('useDomain');
                        
                        return (
                          <Row gutter={16}>
                            {/* Campo Domínio - só aparece se Switch ativo */}
                            {isWindowsTarget && useDomain && (
                              <Col xs={24} md={8}>
                                <Form.Item
                                  name="domain"
                                  label="Domínio"
                                  rules={[
                                    { required: true, message: 'Informe o domínio' },
                                    { pattern: /^[a-zA-Z0-9.-]+$/, message: 'Domínio inválido' }
                                  ]}
                                  tooltip="Nome NetBIOS (ex: GRUPOWINK) ou FQDN (ex: grupowink.local)"
                                  normalize={(value) => value?.toUpperCase()}
                                >
                                  <Input 
                                    placeholder="Ex: GRUPOWINK" 
                                    allowClear
                                  />
                                </Form.Item>
                              </Col>
                            )}
                            
                            {/* Campo Usuário */}
                            <Col xs={24} md={isWindowsTarget && useDomain ? 8 : 12}>
                              <Form.Item
                                name="username"
                                label="Usuário"
                                rules={[{ required: true, message: 'Informe o usuário' }]}
                                tooltip={
                                  isWindowsTarget && !useDomain
                                    ? "Conta local (sem domínio)"
                                    : isWindowsTarget && useDomain
                                    ? "Apenas o nome do usuário (sem DOMINIO\\)"
                                    : undefined
                                }
                              >
                                <Input 
                                  placeholder={
                                    isWindowsTarget && useDomain 
                                      ? "usuario.silva" 
                                      : userPlaceholder
                                  } 
                                  allowClear 
                                />
                              </Form.Item>
                            </Col>
                            
                            {/* Campo Senha */}
                            <Col xs={24} md={isWindowsTarget && useDomain ? 8 : 12}>
                              <Form.Item
                                name="password"
                                label="Senha"
                                rules={[{ required: true, message: 'Informe a senha' }]}
                              >
                                <Input.Password placeholder="Senha do usuário" allowClear />
                              </Form.Item>
                            </Col>
                          </Row>
                        );
                      }}
                    </Form.Item>
                  </>
                );
              } else {
                return (
                  <Row gutter={16}>
                    <Col xs={24} md={12}>
                      <Form.Item
                        name="username"
                        label="Usuario"
                        rules={[{ required: true, message: 'Informe o usuario remoto' }]}
                      >
                        <Input placeholder={userPlaceholder} allowClear />
                      </Form.Item>
                    </Col>
                    <Col xs={24} md={12}>
                      <Form.Item
                        name="keyPath"
                        label="Chave privada SSH"
                        rules={[{ required: !privateKeyFile, message: 'Faça upload da chave ou informe o caminho' }]}
                      >
                        <Input 
                          placeholder={keyPathPlaceholder} 
                          allowClear
                          value={privateKeyFile || undefined}
                          disabled={!!privateKeyFile}
                          addonAfter={
                            <Upload
                              beforeUpload={(file) => {
                                const reader = new FileReader();
                                reader.onload = () => {
                                  // TODO: Enviar para backend e receber caminho
                                  setPrivateKeyFile(`/tmp/${file.name}`);
                                  form.setFieldsValue({ keyPath: `/tmp/${file.name}` });
                                  message.success(`Chave ${file.name} carregada`);
                                };
                                reader.readAsText(file);
                                return false; // Prevenir upload automático
                              }}
                              showUploadList={false}
                              maxCount={1}
                            >
                              <Button icon={<UploadOutlined />} size="small">
                                Upload
                              </Button>
                            </Upload>
                          }
                        />
                      </Form.Item>
                    </Col>
                  </Row>
                );
              }
            }}
          </Form.Item>
        </Form>
      <Alert
        message="Modo de conexão"
        description={
          isWindows
            ? '🔄 Para Windows, o sistema tenta automaticamente: PSExec (SMB/445) → WinRM (5985) → SSH (22). Logs detalhados de cada tentativa aparecem no console do backend.'
            : `SSH utiliza sudo para aplicar configurações; garanta que a porta ${watchedPort || '22'} esteja acessível.`
        }
        type="info"
        showIcon
        style={{ marginBottom: 16 }}
      />

      <Card size="small" title="Status dos pre-checks">
        <List
          dataSource={prechecks}
          renderItem={(item) => (
            <List.Item key={item.key}>
              <List.Item.Meta
                title={
                  <Space>
                    <Text strong>{item.label}</Text>
                    <Tag
                      color={
                        item.status === 'success'
                          ? 'green'
                          : item.status === 'failed'
                          ? 'red'
                          : item.status === 'running'
                          ? 'blue'
                          : 'default'
                      }
                    >
                      {item.status}
                    </Tag>
                  </Space>
                }
                description={item.description}
              />
              {item.detail && (
                <div style={{ 
                  marginTop: 8,
                  padding: 12,
                  background: item.status === 'failed' ? '#fff2f0' : '#fafafa',
                  border: `1px solid ${item.status === 'failed' ? '#ffccc7' : '#f0f0f0'}`,
                  borderRadius: 4,
                  whiteSpace: 'pre-wrap',
                  fontFamily: 'monospace',
                  fontSize: '12px',
                  lineHeight: '1.6'
                }}>
                  <Text type={item.status === 'failed' ? 'danger' : 'secondary'}>
                    {item.detail}
                  </Text>
                </div>
              )}
            </List.Item>
          )}
        />
      </Card>

      <Space>
        <Button
          type="primary"
          icon={<CloudServerOutlined />}
          loading={precheckRunning}
          onClick={runPrechecks}
        >
          Executar pre-checks
        </Button>
        <Button icon={<ReloadOutlined />} onClick={() => setPrechecks(DEFAULT_PRECHECKS)}>
          Limpar status
        </Button>
      </Space>
    </Space>
    );
  };
  const renderConfigContent = () => (
    <Space direction="vertical" size="large" style={{ width: '100%' }}>
      <Paragraph>
        Ajuste as opcoes da instalacao, selecione coletores e defina como o exporter
        sera registrado no Consul apos a conclusao.
      </Paragraph>

      <Row gutter={16}>
        <Col xs={24} md={12}>
          <Card title="Sistema alvo" size="small" variant="borderless" style={{ background: '#fafafa' }}>
            <Space direction="vertical" size="middle" style={{ width: '100%' }}>
              <Alert
                message={targetType === 'linux' ? 'Linux' : 'Windows'}
                description={`Sistema operacional selecionado na etapa 1: ${targetType === 'linux' ? 'Linux' : 'Windows Server'}`}
                type="info"
                showIcon
                icon={targetType === 'linux' ? <LinuxOutlined /> : <WindowsOutlined />}
              />
              <Paragraph type="secondary" style={{ margin: 0 }}>
                Para mudar o sistema operacional, volte para a etapa 1.
              </Paragraph>

              <Select
                value={selectedVersion}
                onChange={setSelectedVersion}
                style={{ width: '100%' }}
                placeholder="Selecione a versão"
                options={exporterVersions.filter(v => {
                  // Filtrar apenas versões compatíveis com o OS selecionado
                  if (targetType === 'linux') {
                    return !v.label.includes('Windows');
                  } else {
                    return !v.label.includes('Linux') || v.value === 'latest';
                  }
                })}
              />

              <Select
                showSearch
                loading={loadingNodes}
                value={selectedNodeAddress}
                onChange={(value) => setSelectedNodeAddress(value)}
                style={{ width: '100%' }}
                placeholder={
                  loadingNodes ? 'Carregando nós do Consul...' : 'Selecione um nó do Consul'
                }
                optionFilterProp="label"
                filterOption={(input, option) => {
                  const label = option?.label;
                  const labelText = typeof label === 'string' ? label : String(label ?? '');
                  return labelText.toLowerCase().includes(input.toLowerCase());
                }}
                options={nodes.map((node) => ({
                  value: node.addr,
                  label: `${node.node} (${node.addr})`,
                }))}
                disabled={loadingNodes || nodes.length === 0}
                notFoundContent={loadingNodes ? 'Carregando...' : 'Nenhum nó ativo encontrado'}
              />

              <Space>
                <Text>Registrar automaticamente no Consul</Text>
                <Switch 
                  checked={autoRegister} 
                  onChange={(checked) => {
                    // ⚠️ FLUXO CORRETO: Verificar IP duplicado SOMENTE quando MARCAR o switch
                    if (checked) {
                      // Verificar se existe IP duplicado guardado do pre-check
                      const hasIPDuplicate = sessionStorage.getItem('consulIPDuplicate') === 'true';
                      const duplicateServices = JSON.parse(sessionStorage.getItem('consulIPServices') || '[]');
                      
                      if (hasIPDuplicate && duplicateServices.length > 0) {
                        // 🚨 Mostrar modal reutilizando layout padrão de alertas
                        setWarningModalTitle('🚫 IP/Host já existe no Consul');
                        setWarningModalContent({
                          duplicateConsul: true,
                          existingInstall: false,
                          services: duplicateServices,
                          portOpen: false,
                          serviceRunning: false,
                          hasConfig: false,
                          targetType: targetType
                        });
                        setWarningModalMode('toggle-auto-register');
                        setWarningModalVisible(true);
                        // NÃO marcar aqui, esperar confirmação do modal
                        return;
                      }
                    }
                    
                    // Se chegou aqui, pode marcar/desmarcar normalmente (sem IP duplicado)
                    setAutoRegister(checked);
                    if (checked) {
                      message.success('✅ Registro no Consul ATIVADO', 3);
                    } else {
                      message.info('Registro automático DESATIVADO', 3);
                    }
                  }} 
                />
              </Space>
            </Space>
          </Card>
        </Col>

        <Col xs={24} md={12}>
          <Card title="Coletores" size="small" variant="borderless" style={{ background: '#fafafa' }}>
            <Paragraph type="secondary">{collectorHelpText}</Paragraph>
            <Select
              mode="multiple"
              value={selectedCollectors}
              style={{ width: '100%' }}
              placeholder="Selecione coletores adicionais"
              onChange={(value) => setSelectedCollectors(value)}
            >
              {availableCollectorOptions.map((collector) => (
                <Option value={collector.value} key={collector.value}>
                  <Tooltip title={collector.description} placement="right">
                    <span>{collector.label}</span>
                  </Tooltip>
                </Option>
              ))}
            </Select>
            <Divider style={{ margin: '12px 0' }} />
            <List
              dataSource={availableCollectorOptions.filter((item) => selectedCollectors.includes(item.value))}
              locale={{ emptyText: 'Nenhum coletor selecionado' }}
              renderItem={(item) => (
                <List.Item key={item.value}>
                  <List.Item.Meta
                    title={item.label}
                    description={<Text type="secondary">{item.description}</Text>}
                  />
                </List.Item>
              )}
              size="small"
            />
          </Card>
        </Col>
      </Row>

      <Row gutter={16}>
        <Col xs={24}>
          <Card 
            title={`Autenticação Basic Auth (${targetType === 'linux' ? 'Node Exporter' : 'Windows Exporter'})`} 
            size="small" 
            variant="borderless" 
            style={{ background: '#fafafa' }}
          >
            <Space direction="vertical" size="middle" style={{ width: '100%' }}>
              <Alert
                message="Segurança das Métricas"
                description={
                  targetType === 'linux' 
                    ? "Basic Auth protege o endpoint /metrics do Node Exporter. O Prometheus será configurado automaticamente no Consul com as credenciais fornecidas."
                    : "Basic Auth protege o endpoint /metrics do Windows Exporter na porta 9182. O Prometheus será configurado automaticamente no Consul com as credenciais fornecidas."
                }
                type="info"
                showIcon
              />
              <Space style={{ width: '100%' }}>
                <Text strong>Habilitar Basic Auth:</Text>
                <Switch checked={useBasicAuth} onChange={setUseBasicAuth} />
              </Space>
              
              {useBasicAuth && (
                <Row gutter={16}>
                  <Col xs={24} md={12}>
                    <Space direction="vertical" size="small" style={{ width: '100%' }}>
                      <Text>Usuário:</Text>
                      <Input
                        value={basicAuthUser}
                        onChange={(e) => setBasicAuthUser(e.target.value)}
                        placeholder="prometheus"
                        disabled={!useBasicAuth}
                      />
                    </Space>
                  </Col>
                  <Col xs={24} md={12}>
                    <Space direction="vertical" size="small" style={{ width: '100%' }}>
                      <Text>Senha:</Text>
                      <Input.Password
                        value={basicAuthPassword}
                        onChange={(e) => setBasicAuthPassword(e.target.value)}
                        placeholder="Senha forte para acesso às métricas"
                        disabled={!useBasicAuth}
                      />
                    </Space>
                  </Col>
                </Row>
              )}
            </Space>
          </Card>
        </Col>
      </Row>

      {existingInstallation?.detected && (
        <Alert
          message="Instalação Existente Detectada"
          description={
            <Space direction="vertical" size="small">
              <Text>Foi detectada uma instalação existente do exporter neste host:</Text>
              {existingInstallation.portOpen && <Text>• Porta {targetType === 'windows' ? '9182' : '9100'} está em uso</Text>}
              {existingInstallation.serviceRunning && <Text>• Serviço está em execução</Text>}
              {existingInstallation.hasConfig && <Text>• Configurações existentes encontradas</Text>}
              <Text strong style={{ marginTop: 8, display: 'block' }}>
                Prosseguir irá sobrescrever a instalação atual. Use esta opção se deseja atualizar configurações (ex: adicionar Basic Auth).
              </Text>
            </Space>
          }
          type="warning"
          showIcon
          style={{ marginBottom: 16 }}
        />
      )}

      <Space>
        <Button onClick={() => setCurrentStep(0)}>Voltar</Button>
        <Button type="primary" icon={<SettingOutlined />} onClick={() => setCurrentStep(3)}>
          Prosseguir para instalacao
        </Button>
      </Space>
    </Space>
  );
  const renderInstallContent = () => {
    const methodSummary =
      targetType === 'windows'
        ? resolvedWindowsMethod
          ? resolvedWindowsMethod.toUpperCase()
          : 'Automático (PSExec → WinRM → SSH)'
        : 'SSH';

    return (
    <Space direction="vertical" size="large" style={{ width: '100%' }}>
      <Paragraph>
        Revise as configuracoes e acompanhe o progresso da instalacao em tempo real.
      </Paragraph>

      <Card size="small" title="Resumo da configuracao" variant="outlined">
        <List size="small">
          <List.Item>
            <Text strong>Destino:</Text> <Text type="secondary">{form.getFieldValue('host')}:{form.getFieldValue('port')}</Text>
          </List.Item>
          <List.Item>
            <Text strong>Usuario:</Text> <Text type="secondary">{form.getFieldValue('username')}</Text>
          </List.Item>
          <List.Item>
            <Text strong>Sistema:</Text> <Text type="secondary">{targetType.toUpperCase()}</Text>
          </List.Item>
          <List.Item>
            <Text strong>Nó Consul:</Text> <Text type="secondary">{selectedNodeLabel}</Text>
          </List.Item>
          <List.Item>
            <Text strong>Metodo:</Text>{' '}
            <Text type="secondary">{methodSummary}</Text>
          </List.Item>
          <List.Item>
            <Text strong>Versao do exporter:</Text>{' '}
            <Text type="secondary">{selectedVersion}</Text>
          </List.Item>
          <List.Item>
            <Text strong>Coletores:</Text>{' '}
            <Text type="secondary">
              {selectedCollectors.length ? selectedCollectors.join(', ') : 'Padrao'}
            </Text>
          </List.Item>
          <List.Item>
            <Text strong>Basic Auth:</Text>{' '}
            <Text type="secondary">
              {useBasicAuth ? `Habilitado (usuario: ${basicAuthUser})` : 'Desabilitado'}
            </Text>
          </List.Item>
          <List.Item>
            <Text strong>Auto registrar:</Text> <Text type="secondary">{autoRegister ? 'Sim' : 'Nao'}</Text>
          </List.Item>
        </List>
      </Card>

      <Card
        size="small"
        title="Logs da instalacao"
        extra={
          <Button
            type="link"
            icon={<ReloadOutlined />}
            disabled={installRunning}
            onClick={() => setInstallLogs([])}
          >
            Limpar
          </Button>
        }
      >
        <div style={{
          background: '#111',
          color: '#0f0',
          padding: 12,
          borderRadius: 8,
          minHeight: 200,
          fontFamily: 'monospace',
          whiteSpace: 'pre-wrap',
          overflowY: 'auto',
        }}>
          {installLogs.length === 0 ? (
            <Text type="secondary" style={{ color: '#999' }}>
              Nenhum log ainda. Clique em "Iniciar instalacao" para comecar.
            </Text>
          ) : (
            installLogs.map((log) => buildLogRow(log, 'dark'))
          )}
        </div>
      </Card>

      <Space>
        <Button onClick={() => setCurrentStep(1)} disabled={installRunning || installSuccess !== null}>
          Voltar
        </Button>
        {installSuccess === null && (
          <Button
            type="primary"
            icon={<ThunderboltOutlined />}
            loading={installRunning}
            onClick={handleInstall}
            disabled={installRunning}
          >
            Iniciar instalacao
          </Button>
        )}
        {installSuccess !== null && (
          <Button
            type="default"
            onClick={() => setLogModalVisible(true)}
          >
            Ver Logs
          </Button>
        )}
      </Space>
    </Space>
  );
  };
  const renderValidationContent = () => (
    <Space direction="vertical" size="large" style={{ width: '100%' }}>
      <Paragraph>
        Resultado da instalacao remota. Caso necessario, volte ao inicio e repita o
        processo para outro host.
      </Paragraph>

      {installSuccess ? (
        <Alert
          message="Instalacao concluida"
          description="O exporter respondeu ao health check e foi registrado conforme configurado."
          type="success"
          showIcon
        />
      ) : (
        <Alert
          message="Instalacao nao confirmada"
          description="Nao ha confirmacao de sucesso. Revise os logs e tente novamente."
          type="warning"
          showIcon
        />
      )}

      <Card size="small" title="Acoes sugeridas">
        <List
          size="small"
          dataSource={[
            'Acessar /metrics do exporter para validar as metricas.',
            'Atualizar o scrape config do Prometheus e aplicar.',
            'Adicionar dashboards no Grafana e vincular tags do Consul.',
          ]}
          renderItem={(item, index) => <List.Item key={index}>{item}</List.Item>}
        />
      </Card>

      <Space>
        <Button icon={<ToolOutlined />} onClick={handleReset}>
          Nova instalacao
        </Button>
        <Button type="primary" onClick={() => setLogModalVisible(true)}>
          Ver logs novamente
        </Button>
      </Space>
    </Space>
  );
  const renderStepContent = () => {
    switch (currentStep) {
      case 0:
        return renderTargetContent();
      case 1:
        return renderPrecheckContent();
      case 2:
        return renderConfigContent();
      case 3:
        return renderInstallContent();
      case 4:
      default:
        return renderValidationContent();
    }
  };

  return (
    <PageContainer
      header={{
        title: 'Instalar exporters',
        subTitle: 'Execucao guiada com pre-checks, configuracao e validacao automatica',
      }}
    >
      <Card>
        <Title level={4}>Assistente de instalacao remota</Title>
        <Paragraph type="secondary">
          Utilize o wizard para validar o servidor, escolher parametros de implantacao e seguir a instalacao passo a passo.
        </Paragraph>

        <Steps
          current={currentStep}
          items={steps.map((item) => ({
            key: item.key,
            title: item.title,
            icon: item.icon,
          }))}
          responsive
          style={{ marginBottom: 24 }}
        />

        <Divider />

        {renderStepContent()}
      </Card>

      {/* Modal de Logs de Instalação */}
      <Modal
        title="Logs de Instalação em Tempo Real"
        open={logModalVisible}
        onCancel={() => setLogModalVisible(false)}
        width={900}
        footer={[
          <Button key="close" onClick={() => setLogModalVisible(false)}>
            Fechar
          </Button>,
        ]}
        style={{ top: 50 }}
      >
        <div
          style={{
            height: '600px',
            overflowY: 'auto',
            background: '#001529',
            color: '#fff',
            padding: '16px',
            fontFamily: 'monospace',
            fontSize: '13px',
            borderRadius: '4px',
          }}
        >
          {installLogs.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '20px', color: '#888' }}>
              Aguardando início da instalação...
            </div>
          ) : (
            installLogs.map((log) => buildLogRow(log, 'dark'))
          )}
        </div>
      </Modal>

      {/* Modal de Confirmação de Instalação Existente/Duplicada */}
      <Modal
        title={<span style={{ fontSize: '18px', fontWeight: 600 }}>{warningModalTitle}</span>}
        open={warningModalVisible}
        onCancel={() => {
          setWarningModalVisible(false);
          setWarningModalContent(null);
          setWarningModalMode(null);
        }}
        width={750}
        footer={warningModalFooter}
      >
        <div style={{ marginTop: 16 }}>
          {/* Alerta combinado quando AMBOS os problemas são detectados */}
          {warningModalContent?.duplicateConsul && warningModalContent?.existingInstall && (
            <Alert
              message="🔥 SITUAÇÃO CRÍTICA: Múltiplos Problemas"
              description={
                <div style={{ fontSize: '13px' }}>
                  <Text strong style={{ color: '#cf1322' }}>
                    Este host apresenta DOIS problemas simultâneos:
                  </Text>
                  <div style={{ marginTop: 8, marginBottom: 8 }}>
                    <Text>1️⃣ IP já registrado no Consul</Text><br />
                    <Text>2️⃣ Instalação existente no servidor</Text>
                  </div>
                  <Text type="danger">
                    Prosseguir pode causar sérios problemas de monitoramento!
                  </Text>
                </div>
              }
              type="error"
              showIcon
              banner
              style={{ marginBottom: 16 }}
            />
          )}
          
          {/* Duplicação no Consul */}
          {warningModalContent?.duplicateConsul && (
            <Alert
              message="🚫 IP/Host já existe no Consul"
              description={
                <Space direction="vertical" size="small" style={{ width: '100%' }}>
                  <Text>
                    O IP/Host já está registrado no Consul com os seguintes serviços:
                  </Text>
                  <div style={{
                    background: '#fff',
                    border: '1px solid #ffccc7',
                    borderRadius: 4,
                    padding: 12,
                    marginTop: 8
                  }}>
                    {warningModalContent.services.map((service, idx) => (
                      <div key={idx} style={{ 
                        fontFamily: 'monospace',
                        fontSize: '13px',
                        color: '#cf1322',
                        marginBottom: 4
                      }}>
                        • {service}
                      </div>
                    ))}
                  </div>
                  <Text strong style={{ color: '#ff4d4f', marginTop: 12, display: 'block' }}>
                    ⚠️ RISCO: Continuar irá criar entradas duplicadas e pode causar:
                  </Text>
                  <ul style={{ marginTop: 4, color: '#8c8c8c' }}>
                    <li>Conflitos de dados no monitoramento</li>
                    <li>Métricas duplicadas no Prometheus</li>
                    <li>Confusão na identificação de hosts</li>
                    <li>Alertas incorretos ou duplicados</li>
                  </ul>
                </Space>
              }
              type="error"
              showIcon
              style={{ marginBottom: 16 }}
            />
          )}

          {/* Instalação existente no servidor */}
          {warningModalContent?.existingInstall && (
            <Alert
              message="⚙️ Instalação existente detectada no servidor"
              description={
                <Space direction="vertical" size="small" style={{ width: '100%' }}>
                  <Text>
                    Detectamos componentes já instalados no servidor remoto:
                  </Text>
                  <div style={{
                    background: '#fffbe6',
                    border: '1px solid #ffe58f',
                    borderRadius: 4,
                    padding: 12,
                    marginTop: 8
                  }}>
                    {warningModalContent.portOpen && (
                      <div style={{ marginBottom: 4, color: '#d46b08' }}>
                        ✓ Porta do exporter está em uso
                      </div>
                    )}
                    {warningModalContent.serviceRunning && (
                      <div style={{ marginBottom: 4, color: '#d46b08' }}>
                        ✓ Serviço {warningModalContent.targetType === 'windows' ? 'windows_exporter' : 'node_exporter'} está rodando
                      </div>
                    )}
                    {warningModalContent.hasConfig && (
                      <div style={{ marginBottom: 4, color: '#d46b08' }}>
                        ✓ Arquivo de configuração encontrado
                      </div>
                    )}
                  </div>
                  <Text strong style={{ color: '#fa8c16', marginTop: 12, display: 'block' }}>
                    ⚠️ ATENÇÃO: Continuar irá sobrescrever:
                  </Text>
                  <ul style={{ marginTop: 4, color: '#8c8c8c' }}>
                    {warningModalContent.targetType === 'windows' ? (
                      <>
                        <li>Configurações personalizadas existentes</li>
                        <li>Coletores habilitados anteriormente</li>
                        <li>Serviço Windows (será recriado)</li>
                        <li>Parâmetros de linha de comando</li>
                      </>
                    ) : (
                      <>
                        <li>Configurações personalizadas existentes</li>
                        <li>Coletores habilitados anteriormente</li>
                        <li>Autenticação básica (se configurada)</li>
                        <li>Serviço systemd (será recriado)</li>
                      </>
                    )}
                  </ul>
                </Space>
              }
              type="warning"
              showIcon
            />
          )}

          {/* Recomendações */}
          <div style={{
            marginTop: 16,
            padding: 16,
            background: '#e6f7ff',
            border: '1px solid #91d5ff',
            borderRadius: 6
          }}>
            <Text strong style={{ fontSize: '14px', color: '#0050b3' }}>
              💡 Recomendações:
            </Text>
            <ul style={{ marginTop: 8, marginBottom: 0, color: '#595959' }}>
              {/* Cenário: AMBOS os problemas */}
              {warningModalContent?.duplicateConsul && warningModalContent?.existingInstall && (
                <>
                  <li><Text type="danger" strong>CRÍTICO: Dois problemas simultâneos detectados!</Text></li>
                  <li><Text strong>Opção 1 (Recomendada):</Text> Use outro host/IP para a instalação</li>
                  <li><Text strong>Opção 2:</Text> Desmarque "Registrar no Consul" para apenas ATUALIZAR o exporter existente (mantém registro atual)</li>
                  <li><Text strong>Opção 3:</Text> Desregistre manualmente do Consul E remova instalação antiga completamente</li>
                  <li>Documente as alterações para referência futura</li>
                </>
              )}
              
              {/* Cenário: APENAS IP duplicado no Consul */}
              {warningModalContent?.duplicateConsul && !warningModalContent?.existingInstall && (
                <>
                  <li><Text strong>Verifique se o IP/hostname está correto</Text></li>
                  <li>Considere usar outro IP/hostname ou remover o registro duplicado do Consul</li>
                  <li>Se for instalação nova, certifique-se de usar IP único</li>
                  <li>Se for reinstalação, desmarque "Registrar no Consul" para manter o registro atual</li>
                </>
              )}
              
              {/* Cenário: APENAS instalação existente no servidor */}
              {!warningModalContent?.duplicateConsul && warningModalContent?.existingInstall && (
                <>
                  <li><Text strong>✅ CENÁRIO DE ATUALIZAÇÃO:</Text> Este é um caso normal de atualização/reinstalação</li>
                  <li><Text strong>Faça backup das configurações existentes</Text> (se houver personalizações importantes)</li>
                  {warningModalContent.targetType === 'windows' ? (
                    <>
                      <li>Pare o serviço antes: <Text code>Stop-Service windows_exporter</Text> (opcional, o instalador faz isso)</li>
                      <li>Considere documentar coletores habilitados atuais para reconfigurar depois</li>
                      <li>A instalação substituirá o serviço Windows existente</li>
                    </>
                  ) : (
                    <>
                      <li>Pare o serviço antes: <Text code>sudo systemctl stop node_exporter</Text> (opcional, o instalador faz isso)</li>
                      <li>Backup de autenticação básica: <Text code>/etc/node_exporter/config.yml</Text> (se configurada)</li>
                      <li>A instalação substituirá o serviço systemd existente</li>
                    </>
                  )}
                  <li><Text type="success">💡 Pode continuar com segurança se marcar/desmarcar "Registrar no Consul" conforme necessário</Text></li>
                </>
              )}
            </ul>
          </div>
          
          {/* Nota sobre "Registrar no Consul" */}
          {warningModalContent?.duplicateConsul && (
            <Alert
              message="ℹ️ Campo 'Registrar no Consul' foi DESMARCADO automaticamente"
              description="Como o IP já existe no Consul, a opção foi desabilitada para evitar duplicação. Você pode marcá-la novamente se desejar sobrescrever o registro existente."
              type="info"
              showIcon
              style={{ marginTop: 12 }}
            />
          )}
        </div>
      </Modal>

      {/* Modal de Erro de Conexão */}
      <Modal
        title={<span style={{ fontSize: '18px', fontWeight: 600 }}>{errorModalTitle}</span>}
        open={errorModalVisible}
        onCancel={() => setErrorModalVisible(false)}
        width={700}
        footer={[
          <Button key="close" type="primary" onClick={() => setErrorModalVisible(false)}>
            Entendi
          </Button>,
        ]}
      >
        <div style={{ marginTop: 16 }}>
          <div style={{
            background: '#f6f6f6',
            border: '1px solid #e8e8e8',
            borderRadius: 6,
            padding: 16,
            maxHeight: '500px',
            overflowY: 'auto'
          }}>
            {errorModalContent.split('\n').map((line, index) => {
              // Identificar seções importantes
              const isHeader = line.startsWith('✅') || line.startsWith('📋') || line.startsWith('💡') || line.startsWith('🔍');
              const isCommand = line.startsWith('•') || line.trim().startsWith('sudo') || line.trim().startsWith('ping') || line.trim().startsWith('telnet') || line.trim().startsWith('ssh') || line.trim().startsWith('nslookup') || line.trim().startsWith('tracert') || line.trim().startsWith('id') || line.trim().startsWith('chmod') || line.trim().startsWith('ls');
              
              return (
                <div key={index} style={{
                  marginBottom: isHeader ? 12 : (isCommand ? 4 : 8),
                  lineHeight: '1.6'
                }}>
                  {isHeader ? (
                    <Text strong style={{ fontSize: '14px', color: '#1890ff' }}>{line}</Text>
                  ) : isCommand ? (
                    <Text code style={{ 
                      display: 'block',
                      background: '#fff',
                      padding: '4px 8px',
                      borderRadius: 4,
                      fontSize: '13px',
                      fontFamily: 'Consolas, Monaco, monospace',
                      color: '#d63031'
                    }}>{line}</Text>
                  ) : line.trim() === '' ? (
                    <div style={{ height: 8 }} />
                  ) : (
                    <Text style={{ fontSize: '13px', color: '#595959' }}>{line}</Text>
                  )}
                </div>
              );
            })}
          </div>
          
          {errorCategory && (
            <div style={{
              marginTop: 16,
              padding: '8px 12px',
              background: '#e6f7ff',
              border: '1px solid #91d5ff',
              borderRadius: 4,
              fontSize: '12px',
              color: '#096dd9'
            }}>
              <Text strong>Categoria:</Text> {errorCategory} | <Text strong>Código:</Text> {errorModalIcon}
            </div>
          )}
        </div>
      </Modal>
    </PageContainer>
  );
};

export default Installer;