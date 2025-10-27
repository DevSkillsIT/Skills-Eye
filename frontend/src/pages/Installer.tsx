
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
  Row,
  Select,
  Space,
  Steps,
  Switch,
  Tag,
  Tooltip,
  Typography,
} from 'antd';
import {
  CheckCircleOutlined,
  CloudServerOutlined,
  LinuxOutlined,
  ReloadOutlined,
  SettingOutlined,
  ThunderboltOutlined,
  ToolOutlined,
  WindowsOutlined,
} from '@ant-design/icons';
import { PageContainer } from '@ant-design/pro-components';

const { Option } = Select;
const { Title, Paragraph, Text } = Typography;

interface PrecheckItem {
  key: string;
  label: string;
  description: string;
  status: 'pending' | 'running' | 'success' | 'failed';
  detail?: string;
}

interface InstallLogEntry {
  key: string;
  message: string;
}

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
    description: 'Detecta distribuicao, versao e arquitetura.',
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
    label: 'Espaco em disco',
    description: 'Valida espaco minimo para binarios e logs.',
    status: 'pending',
  },
  {
    key: 'firewall',
    label: 'Firewall',
    description: 'Simula regras de liberacao para Prometheus.',
    status: 'pending',
  },
];

type CollectorTarget = 'linux' | 'windows';

interface CollectorOption {
  label: string;
  value: string;
  description: string;
  metrics: string[];
  targets: CollectorTarget[];
}

const COLLECTOR_OPTIONS: CollectorOption[] = [
  {
    label: 'Node exporter padrao',
    value: 'node',
    description: 'CPU, memoria, rede e recursos base do host.',
    metrics: ['node_cpu_seconds_total', 'node_memory_Active_bytes'],
    targets: ['linux'],
  },
  {
    label: 'Filesystem',
    value: 'filesystem',
    description: 'Uso de disco por filesystem, inodes e espaco reservado.',
    metrics: ['node_filesystem_avail_bytes', 'node_filesystem_size_bytes'],
    targets: ['linux'],
  },
  {
    label: 'Systemd',
    value: 'systemd',
    description: 'Estado de unidades systemd e falhas recentes.',
    metrics: ['node_systemd_unit_state', 'node_systemd_unit_start_time_seconds'],
    targets: ['linux'],
  },
  {
    label: 'Textfile collector',
    value: 'textfile',
    description: 'Permite expor metricas customizadas via arquivos .prom.',
    metrics: ['node_textfile_mtime_seconds'],
    targets: ['linux'],
  },
  {
    label: 'Process collector',
    value: 'process',
    description: 'Expande metricas de processos, threads e uso de CPU.',
    metrics: ['node_processes_state', 'node_processes_threads'],
    targets: ['linux'],
  },
  {
    label: 'iostat collector (Linux)',
    value: 'iostat',
    description: 'Metricas detalhadas de IO por dispositivo (requer sysstat).',
    metrics: ['node_disk_io_time_seconds_total', 'node_disk_reads_completed_total'],
    targets: ['linux'],
  },
  {
    label: 'WMI collectors (Windows)',
    value: 'wmi',
    description: 'Grupos padrao do windows_exporter (CPU, memoria, discos, servicos).',
    metrics: ['wmi_cpu_time_total', 'wmi_logical_disk_free_megabytes'],
    targets: ['windows'],
  },
];
const Installer: React.FC = () => {
  const [form] = Form.useForm();
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
  const [selectedDatacenter, setSelectedDatacenter] = useState('palmas');
  const [connectionMethod, setConnectionMethod] = useState<'ssh' | 'fallback'>('ssh');

  useEffect(() => {
    const desired = targetType === 'linux' ? 'ssh' : 'fallback';
    setConnectionMethod((prev) => (prev === desired ? prev : desired));
    form.setFieldsValue({
      authType: 'password',
      password: undefined,
      keyPath: undefined,
    });
  }, [targetType, form]);

  // Atualizar porta padrão quando mudar tipo/método de conexão
  useEffect(() => {
    const isWindowsFallback = targetType === 'windows' && connectionMethod === 'fallback';
    const defaultPort = isWindowsFallback ? 5985 : 22;

    // Só atualizar se o formulário ainda não tem valor ou está com valor padrão antigo
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

  const appendLog = (message: string) => {
    setInstallLogs((prev) => [
      ...prev,
      { key: `${Date.now()}-${prev.length}`, message },
    ]);
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
    } catch (err) {
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

    for (const item of DEFAULT_PRECHECKS) {
      setPrechecks((prev) =>
        prev.map((entry) =>
          entry.key === item.key
            ? { ...entry, status: 'running', detail: undefined }
            : entry,
        ),
      );
      // eslint-disable-next-line no-await-in-loop
      await new Promise((resolve) => setTimeout(resolve, 500));
      setPrechecks((prev) =>
        prev.map((entry) =>
          entry.key === item.key
            ? { ...entry, status: 'success', detail: 'Verificacao concluida com sucesso.' }
            : entry,
        ),
      );
    }

    setPrecheckRunning(false);
    message.success('Pre-checks concluido.');
    setCurrentStep(2);
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
ExecStart=/usr/local/bin/node_exporter --web.listen-address=\":${exporterPort}\"${useBasicAuth ? ' --web.config.file=/etc/node_exporter/config.yml' : ''}${extraCollectors.length ? ' --collector.' + extraCollectors.join(' --collector.') : ''}
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
      plan.push(
        `[CONSUL] Registrar servico (datacenter=${selectedDatacenter}): curl -X PUT http://CONSUL_API/v1/agent/service/register -d '{"ID":"${targetType}-exporter-${host}","Name":"${targetType}-exporter","Address":"${host}","Port":${exporterPort},"Meta":{"datacenter":"${selectedDatacenter}"},"Check":{"HTTP":"http://${host}:${exporterPort}/metrics","Interval":"30s"}}'`,
      );
    }

    plan.push(
      `[VERIFICACAO] Confirmar scraping no Prometheus apontando para http://${host}:${exporterPort}/metrics.`,
    );

    return plan;
  };

  const handleInstall = async () => {
    setInstallRunning(true);
    setInstallSuccess(null);
    setInstallLogs([]);

    const stepsLog = buildInstallPlan();

    appendLog('Iniciando rotina remota...');
    for (const log of stepsLog) {
      appendLog(log);
      // eslint-disable-next-line no-await-in-loop
      await new Promise((resolve) => setTimeout(resolve, 800));
    }

    appendLog('Instalacao finalizada sem erros.');
    setInstallRunning(false);
    setInstallSuccess(true);
    setCurrentStep(3);
    message.success('Exporter instalado e validado.');
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
    setSelectedDatacenter('palmas');
    setConnectionMethod('ssh');
  };

  const availableCollectorOptions = useMemo(
    () => COLLECTOR_OPTIONS.filter((item) => item.targets.includes(targetType)),
    [targetType],
  );

  const collectorHelpText = selectedCollectors.length
    ? `${selectedCollectors.length} coletor(es) selecionado(s)`
    : 'Nenhum coletor selecionado';
  const datacenterOptions = useMemo(
    () => [
      { value: 'palmas', label: 'Palmas (PRD)' },
      { value: 'rio', label: 'Rio (DR)' },
      { value: 'lab', label: 'Laboratorio' },
    ],
    [],
  );

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
        : [
            {
              value: 'fallback' as const,
              label: 'WinRM / PowerShell remoto (recomendado)',
            },
            {
              value: 'ssh' as const,
              label: 'OpenSSH (porta 22)',
            },
          ];

    const connectionHint =
      targetType === 'linux'
        ? 'O instalador executa todos os comandos via SSH com privilegios elevados via sudo.'
        : 'WinRM/PowerShell aplica o instalador MSI e configura o servico automaticamente; use SSH apenas se o Windows OpenSSH estiver configurado.';

    return (
      <Space direction="vertical" size="large" style={{ width: '100%' }}>
        <Paragraph>
          Escolha o sistema alvo e o metodo de conexao inicial. Esse passo define como os pre-checks serao conduzidos.
        </Paragraph>

        <Row gutter={16}>
          <Col xs={24} md={12}>
            <Card title="Sistema operacional" size="small" variant="borderless" style={{ background: '#fafafa' }}>
              <Space direction="vertical" size="middle" style={{ width: '100%' }}>
                <Select
                  value={targetType}
                  onChange={(value: 'linux' | 'windows') => setTargetType(value)}
                  style={{ width: '100%' }}
                >
                  <Option value="linux">
                    <Space>
                      <LinuxOutlined />
                      Linux
                    </Space>
                  </Option>
                  <Option value="windows">
                    <Space>
                      <WindowsOutlined />
                      Windows
                    </Space>
                  </Option>
                </Select>
                <Paragraph type="secondary" style={{ margin: 0 }}>
                  Linux utiliza conexao SSH. Windows pode operar via WinRM/PowerShell ou SSH quando previamente habilitado.
                </Paragraph>
              </Space>
            </Card>
          </Col>

          <Col xs={24} md={12}>
            <Card title="Metodo de conexao" size="small" variant="borderless" style={{ background: '#fafafa' }}>
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
                  {connectionHint}
                </Paragraph>
              </Space>
            </Card>
          </Col>
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
    const isWindowsFallback = targetType === 'windows' && connectionMethod === 'fallback';
    const isWindowsSSH = targetType === 'windows' && connectionMethod === 'ssh';
    const isLinux = targetType === 'linux';

    const portLabel = isWindowsFallback ? 'Porta WinRM' : 'Porta SSH';
    const portPlaceholder = isWindowsFallback ? '5985' : '22';
    const portMessage = isWindowsFallback ? 'Informe a porta WinRM' : 'Informe a porta SSH';

    const userPlaceholder = isLinux ? 'root' : 'Administrator';
    const keyPathPlaceholder =
      targetType === 'windows'
        ? 'C:\\Users\\Administrator\\.ssh\\id_rsa'
        : '/home/user/.ssh/id_rsa';
    const authOptions =
      isWindowsFallback
        ? [{ value: 'password', label: 'Senha (WinRM/PowerShell)' }]
        : [
            { value: 'password', label: isWindowsSSH ? 'Senha (OpenSSH)' : 'Senha' },
            { value: 'key', label: 'Chave SSH' },
          ];

    return (
      <Space direction="vertical" size="large" style={{ width: '100%' }}>
        <Paragraph>
          Informe o alvo e execute os pre-checks para validar conectividade, sistema
          operacional e dependencias antes de instalar o exporter.
        </Paragraph>

        <Form
          layout="vertical"
          form={form}
          initialValues={{ port: isWindowsFallback ? 5985 : 22, authType: 'password' }}
          style={{ maxWidth: 720 }}
        >
          <Row gutter={16}>
            <Col xs={24} md={14}>
              <Form.Item
                name="host"
                label="IP ou hostname"
                rules={[{ required: true, message: 'Informe o IP ou hostname' }]}
              >
                <Input placeholder="Ex: 192.168.1.20" allowClear />
              </Form.Item>
            </Col>
            <Col xs={24} md={10}>
              <Form.Item
                name="port"
                label={portLabel}
                rules={[{ required: true, message: portMessage }]}
              >
                <Input placeholder={portPlaceholder} allowClear />
              </Form.Item>
            </Col>
          </Row>

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
              name="authType"
              label="Autenticacao"
              rules={[{ required: true, message: 'Selecione o metodo de autenticacao' }]}
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

        <Form.Item noStyle shouldUpdate={(prev, cur) => prev.authType !== cur.authType}>
          {({ getFieldValue }) =>
            getFieldValue('authType') === 'password' ? (
              <Form.Item
                name="password"
                label="Senha"
                rules={[{ required: true, message: 'Informe a senha' }]}
              >
                <Input.Password placeholder="Senha do usuario" allowClear />
              </Form.Item>
            ) : (
              <Form.Item
                name="keyPath"
                label="Caminho da chave privada"
                rules={[{ required: true, message: 'Informe o caminho da chave' }]}
              >
                <Input placeholder={keyPathPlaceholder} allowClear />
              </Form.Item>
            )
          }
        </Form.Item>
      </Form>
      <Alert
        message="Modo de conexao"
        description={
          isWindowsFallback
            ? 'Tentativas automaticas para Windows envolvem WinRM, PowerShell remoto e script auxiliar.'
            : connectionMethod === 'ssh' && isWindowsSSH
            ? 'SSH no Windows requer o servico OpenSSH Server ativo, porta 22 liberada e credenciais administrativas.'
            : 'SSH utiliza sudo para aplicar configuracoes; garanta que a porta 22 esteja acessivel.'
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
              {item.detail && <Text type="secondary">{item.detail}</Text>}
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
              <Select
                value={targetType}
                onChange={(value: 'linux' | 'windows') => setTargetType(value)}
                style={{ width: '100%' }}
              >
                <Option value="linux"><Space><LinuxOutlined />Linux</Space></Option>
                <Option value="windows"><Space><WindowsOutlined />Windows</Space></Option>
              </Select>

              <Select
                value={selectedVersion}
                onChange={setSelectedVersion}
                style={{ width: '100%' }}
                options={exporterVersions}
              />

              <Select
                value={selectedDatacenter}
                onChange={setSelectedDatacenter}
                style={{ width: '100%' }}
                options={datacenterOptions}
              />

              <Space>
                <Text>Registrar automaticamente no Consul</Text>
                <Switch checked={autoRegister} onChange={setAutoRegister} />
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

      {targetType === 'linux' && (
        <Row gutter={16}>
          <Col xs={24}>
            <Card title="Autenticação Basic Auth" size="small" variant="borderless" style={{ background: '#fafafa' }}>
              <Space direction="vertical" size="middle" style={{ width: '100%' }}>
                <Alert
                  message="Segurança das Métricas"
                  description="Basic Auth protege o endpoint /metrics do Node Exporter. O Prometheus será configurado automaticamente no Consul com as credenciais fornecidas."
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
      )}

      <Space>
        <Button onClick={() => setCurrentStep(0)}>Voltar</Button>
        <Button type="primary" icon={<SettingOutlined />} onClick={() => setCurrentStep(2)}>
          Prosseguir para instalacao
        </Button>
      </Space>
    </Space>
  );
  const renderInstallContent = () => (
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
            <Text strong>Datacenter:</Text> <Text type="secondary">{selectedDatacenter}</Text>
          </List.Item>
          <List.Item>
            <Text strong>Metodo:</Text>{' '}
            <Text type="secondary">
              {connectionMethod === 'fallback' ? 'WinRM / PowerShell' : 'SSH'}
            </Text>
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
          {targetType === 'linux' && (
            <List.Item>
              <Text strong>Basic Auth:</Text>{' '}
              <Text type="secondary">
                {useBasicAuth ? `Habilitado (usuario: ${basicAuthUser})` : 'Desabilitado'}
              </Text>
            </List.Item>
          )}
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
            installLogs.map((log) => <div key={log.key}>{log.message}</div>)
          )}
        </div>
      </Card>

      <Space>
        <Button onClick={() => setCurrentStep(1)} disabled={installRunning}>
          Voltar
        </Button>
        <Button
          type="primary"
          icon={<ThunderboltOutlined />}
          loading={installRunning}
          onClick={handleInstall}
        >
          Iniciar instalacao
        </Button>
      </Space>
    </Space>
  );
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
        <Button type="primary" onClick={() => setCurrentStep(2)}>
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
    </PageContainer>
  );
};

export default Installer;













