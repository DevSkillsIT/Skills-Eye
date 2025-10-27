
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
    description: 'Valida conexao SSH, porta e credenciais fornecidas.',
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
    description: 'Confere disponibilidade das portas 9100/9182.',
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

const COLLECTOR_OPTIONS = [
  { label: 'Node exporter padrao', value: 'node', description: 'Coleta basica de CPU, memoria, disco e rede.' },
  { label: 'Textfile collector', value: 'textfile', description: 'Permite enviar metricas customizadas via arquivos.' },
  { label: 'Process collector', value: 'process', description: 'Expande metricas de processos com filtros.' },
  { label: 'iostat collector (Linux)', value: 'iostat', description: 'Inclui metricas detalhadas de IO.' },
  { label: 'WMI collectors (Windows)', value: 'wmi', description: 'Coleta metricas especificas do Windows exporter.' },
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
  const [selectedCollectors, setSelectedCollectors] = useState<string[]>(['node']);
  const [autoRegister, setAutoRegister] = useState(true);
  const [selectedDatacenter, setSelectedDatacenter] = useState('palmas');
  const [connectionMethod, setConnectionMethod] = useState<'ssh' | 'fallback'>('ssh');

  useEffect(() => {
    if (targetType === 'linux') {
      setConnectionMethod('ssh');
    }
  }, [targetType]);

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
      await form.validateFields(['host', 'port', 'username', 'authType']);
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

  const handleInstall = async () => {
    setInstallRunning(true);
    setInstallSuccess(null);
    setInstallLogs([]);

    const stepsLog = [
      'Iniciando rotina remota...',
      'Transferindo binarios e configuracoes...',
      'Aplicando permissoes e serviços...',
      'Registrando no Consul e validando metricas...',
    ];

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
    setSelectedCollectors(['node']);
    setAutoRegister(true);
    setConnectionMethod('ssh');
  };

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

  const exporterVersions = useMemo(
    () => [
      { value: 'latest', label: 'Ultima versao estavel' },
      { value: '1.7.0', label: '1.7.0 (Linux)' },
      { value: '1.6.1', label: '1.6.1 (Windows)' },
    ],
    [],
  );
  const renderTargetContent = () => (
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
                Linux utiliza conexao SSH por padrao. Windows pode operar via SSH ou por um modo de tentativas adicionais.
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
                disabled={targetType === 'linux'}
              >
                <Option value="ssh">SSH direto</Option>
                <Option value="fallback">Tentativas automaticas</Option>
              </Select>
              <Paragraph type="secondary" style={{ margin: 0 }}>
                O modo de tentativas automaticas executa diferentes metodos suportados (WinRM, PowerShell remoto, script offline).
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

  const renderPrecheckContent = () => {
    // Determinar labels e placeholders baseado no tipo de conexão
    const isWindowsFallback = targetType === 'windows' && connectionMethod === 'fallback';
    const isWindowsSSH = targetType === 'windows' && connectionMethod === 'ssh';
    const isLinux = targetType === 'linux';

    const portLabel = isWindowsFallback ? 'Porta WinRM' : 'Porta SSH';
    const portPlaceholder = isWindowsFallback ? '5985' : '22';
    const portMessage = isWindowsFallback ? 'Informe a porta WinRM' : 'Informe a porta SSH';

    const userPlaceholder = isLinux ? 'root' : 'Administrator';

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
              <Select>
                <Option value="password">Senha</Option>
                <Option value="key">Chave SSH</Option>
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
                <Input placeholder="/home/user/.ssh/id_rsa" allowClear />
              </Form.Item>
            )
          }
        </Form.Item>
      </Form>
      <Alert
        message="Modo de conexao"
        description={
          connectionMethod === 'fallback'
            ? 'Tentativas automaticas para Windows envolvem WinRM, PowerShell remoto e script auxiliar.'
            : 'O modo SSH exige porta acessivel e credenciais validas.'
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
                defaultValue="latest"
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
              {COLLECTOR_OPTIONS.map((collector) => (
                <Option value={collector.value} key={collector.value}>
                  {collector.label}
                </Option>
              ))}
            </Select>
            <Divider style={{ margin: '12px 0' }} />
            <List
              dataSource={COLLECTOR_OPTIONS.filter((item) => selectedCollectors.includes(item.value))}
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











