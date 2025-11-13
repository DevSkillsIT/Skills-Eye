import React, { useState, useEffect } from 'react';
import { Form, Button, Space, Steps, message, Card, Alert, Typography } from 'antd';
import {
  ThunderboltOutlined,
  SettingOutlined,
  CheckCircleOutlined,
  ToolOutlined,
} from '@ant-design/icons';
import { PageContainer } from '@ant-design/pro-components';

// Import modularized components
import {
  InstallForm,
  LogViewer,
  PrecheckModal,
  WarningModal,
  StatusProgress,
} from './Installer/components';

// Import custom hooks
import {
  useConsulNodes,
  useWebSocketLogs,
  useInstaller,
} from './Installer/hooks';

// Import types and constants
import type {
  InstallFormData,
  PrecheckItem,
  WarningModalContent,
  InstallationStage,
} from './Installer/types';
import { DEFAULT_PRECHECKS, API_URL } from './Installer/constants';

const { Title, Text } = Typography;

const Installer: React.FC = () => {
  const [form] = Form.useForm<InstallFormData>();
  const [currentStep, setCurrentStep] = useState(0);
  const [prechecks, setPrechecks] = useState<PrecheckItem[]>(DEFAULT_PRECHECKS);
  const [precheckModalVisible, setPrecheckModalVisible] = useState(false);
  const [warningModalVisible, setWarningModalVisible] = useState(false);
  const [warningContent, setWarningContent] = useState<WarningModalContent | null>(null);
  const [installationStage, setInstallationStage] = useState<InstallationStage>('idle');
  const [elapsedTime, setElapsedTime] = useState(0);

  // Custom hooks
  const { nodes, loading: nodesLoading, refetch: refetchNodes } = useConsulNodes();

  const {
    installationId,
    running,
    success,
    failed,
    progress,
    logs,
    startInstallation,
    stopInstallation,
    reset,
    addLog,
  } = useInstaller({
    onSuccess: (data) => {
      message.success('Instalação concluída com sucesso!');
      setInstallationStage('completed');
      setCurrentStep(3);
    },
    onError: (error) => {
      message.error(`Instalação falhou: ${error}`);
      setInstallationStage('failed');
    },
  });

  const { connected, error: wsError } = useWebSocketLogs({
    installationId: installationId || undefined,
    enabled: running,
    onLog: (log) => {
      addLog(log);

      // Update stage based on log messages
      const msg = log.message.toLowerCase();
      if (msg.includes('validando conexão')) setInstallationStage('validating');
      else if (msg.includes('conectando')) setInstallationStage('connecting');
      else if (msg.includes('detectando sistema')) setInstallationStage('detecting');
      else if (msg.includes('baixando')) setInstallationStage('downloading');
      else if (msg.includes('instalando')) setInstallationStage('installing');
      else if (msg.includes('configurando')) setInstallationStage('configuring');
      else if (msg.includes('validando instalação'))
        setInstallationStage('validating_install');
    },
  });

  // Timer for elapsed time
  useEffect(() => {
    if (!running) {
      setElapsedTime(0);
      return;
    }

    const timer = setInterval(() => {
      setElapsedTime((prev) => prev + 1);
    }, 1000);

    return () => clearInterval(timer);
  }, [running]);

  // Handle form submission
  const handleInstall = async () => {
    try {
      const values = await form.validateFields();
      addLog({
        key: `local-${Date.now()}`,
        message: '🚀 Iniciando processo de instalação...',
        source: 'local',
        level: 'info',
      });

      setCurrentStep(2);
      setInstallationStage('validating');

      await startInstallation(values);
    } catch (error: any) {
      message.error('Erro ao validar formulário');
      console.error('Form validation error:', error);
    }
  };

  // Handle precheck execution
  const handleRunPrechecks = async () => {
    try {
      const values = await form.validateFields([
        'host',
        'port',
        'username',
        'password',
        'targetType',
      ]);

      setPrecheckModalVisible(true);
      setPrechecks(DEFAULT_PRECHECKS);

      // Simulate prechecks (in a real scenario, call backend API)
      for (let i = 0; i < DEFAULT_PRECHECKS.length; i++) {
        await new Promise((resolve) => setTimeout(resolve, 1000));
        setPrechecks((prev) =>
          prev.map((p, idx) =>
            idx === i
              ? {
                  ...p,
                  status: Math.random() > 0.2 ? 'success' : 'failed',
                  detail:
                    Math.random() > 0.2
                      ? 'Verificação aprovada'
                      : 'Problema detectado',
                }
              : p
          )
        );
      }
    } catch (error) {
      message.error('Preencha os campos obrigatórios antes de validar');
    }
  };

  // Handle warning modal confirm
  const handleWarningConfirm = () => {
    setWarningModalVisible(false);
    handleInstall();
  };

  // Handle reset
  const handleReset = () => {
    reset();
    setCurrentStep(0);
    setInstallationStage('idle');
    setElapsedTime(0);
    form.resetFields();
    setPrechecks(DEFAULT_PRECHECKS);
  };

  // Steps configuration
  const steps = [
    {
      title: 'Configuração',
      icon: <SettingOutlined />,
    },
    {
      title: 'Validação',
      icon: <CheckCircleOutlined />,
    },
    {
      title: 'Instalação',
      icon: <ToolOutlined />,
    },
    {
      title: 'Concluído',
      icon: <CheckCircleOutlined />,
    },
  ];

  return (
    <PageContainer
      title="Instalador Remoto de Exporters"
      subTitle="Instale Node Exporter (Linux) ou Windows Exporter remotamente via SSH/WinRM"
      extra={[
        <Button key="reset" onClick={handleReset} disabled={running}>
          Resetar
        </Button>,
      ]}
    >
      <Space direction="vertical" style={{ width: '100%' }} size="large">
        {/* Progress Steps */}
        <Card>
          <Steps current={currentStep} items={steps} />
        </Card>

        {/* Configuration Form (Step 0) */}
        {currentStep === 0 && (
          <Space direction="vertical" style={{ width: '100%' }} size="middle">
            <Alert
              message="Instalação Remota"
              description="Configure os parâmetros de conexão e instalação. Após preencher, clique em 'Pré-validar' para verificar requisitos."
              type="info"
              showIcon
              closable
            />

            <InstallForm form={form} disabled={running} />

            <Card>
              <Space>
                <Button
                  type="default"
                  icon={<CheckCircleOutlined />}
                  onClick={handleRunPrechecks}
                  disabled={running}
                >
                  Pré-validar
                </Button>
                <Button
                  type="primary"
                  icon={<ThunderboltOutlined />}
                  onClick={handleInstall}
                  disabled={running}
                  size="large"
                >
                  Instalar Agora
                </Button>
              </Space>
            </Card>
          </Space>
        )}

        {/* Installation Progress (Steps 2+) */}
        {currentStep >= 2 && (
          <Space direction="vertical" style={{ width: '100%' }} size="middle">
            {/* Status Progress */}
            <StatusProgress
              stage={installationStage}
              progress={progress}
              message={running ? 'Instalação em andamento...' : undefined}
              error={failed ? 'Instalação falhou. Verifique os logs.' : undefined}
              elapsedTime={elapsedTime}
            />

            {/* WebSocket Status */}
            {wsError && (
              <Alert
                message="Erro de Conexão WebSocket"
                description={wsError}
                type="warning"
                showIcon
                closable
              />
            )}

            {/* Log Viewer */}
            <LogViewer
              logs={logs}
              height={500}
              autoScroll={running}
              showTimestamp
            />

            {/* Action Buttons */}
            <Card>
              <Space>
                {running && (
                  <Button danger onClick={stopInstallation}>
                    Cancelar Instalação
                  </Button>
                )}
                {(success || failed) && (
                  <Button type="primary" onClick={handleReset}>
                    Nova Instalação
                  </Button>
                )}
              </Space>
            </Card>
          </Space>
        )}

        {/* Success Summary (Step 3) */}
        {currentStep === 3 && success && (
          <Alert
            message="Instalação Concluída!"
            description={
              <Space direction="vertical">
                <Text>
                  O exporter foi instalado com sucesso e está em execução.
                </Text>
                <Text type="secondary">
                  Installation ID: <Text code>{installationId}</Text>
                </Text>
              </Space>
            }
            type="success"
            showIcon
          />
        )}
      </Space>

      {/* Precheck Modal */}
      <PrecheckModal
        visible={precheckModalVisible}
        prechecks={prechecks}
        onCancel={() => setPrecheckModalVisible(false)}
        onRetry={handleRunPrechecks}
      />

      {/* Warning Modal */}
      <WarningModal
        visible={warningModalVisible}
        content={warningContent}
        onConfirm={handleWarningConfirm}
        onCancel={() => setWarningModalVisible(false)}
      />
    </PageContainer>
  );
};

export default Installer;
