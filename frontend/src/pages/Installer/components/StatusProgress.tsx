import React from 'react';
import { Card, Progress, Space, Typography, Tag, Timeline, Alert } from 'antd';
import {
  LoadingOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  ClockCircleOutlined,
} from '@ant-design/icons';

const { Text, Title } = Typography;

export type InstallationStage =
  | 'idle'
  | 'validating'
  | 'connecting'
  | 'detecting'
  | 'downloading'
  | 'installing'
  | 'configuring'
  | 'validating_install'
  | 'completed'
  | 'failed';

export interface StatusProgressProps {
  stage: InstallationStage;
  progress: number;
  message?: string;
  error?: string;
  elapsedTime?: number;
}

const STAGE_LABELS: Record<InstallationStage, string> = {
  idle: 'Aguardando início',
  validating: 'Validando conexão',
  connecting: 'Estabelecendo conexão',
  detecting: 'Detectando sistema',
  downloading: 'Baixando binários',
  installing: 'Instalando exporter',
  configuring: 'Configurando serviço',
  validating_install: 'Validando instalação',
  completed: 'Concluído',
  failed: 'Falhou',
};

const STAGE_ORDER: InstallationStage[] = [
  'validating',
  'connecting',
  'detecting',
  'downloading',
  'installing',
  'configuring',
  'validating_install',
  'completed',
];

const getStageIcon = (
  currentStage: InstallationStage,
  itemStage: InstallationStage,
  failed: boolean
) => {
  const currentIndex = STAGE_ORDER.indexOf(currentStage);
  const itemIndex = STAGE_ORDER.indexOf(itemStage);

  if (failed && itemStage === currentStage) {
    return <CloseCircleOutlined style={{ color: '#ff4d4f' }} />;
  }

  if (itemIndex < currentIndex || currentStage === 'completed') {
    return <CheckCircleOutlined style={{ color: '#52c41a' }} />;
  }

  if (itemIndex === currentIndex && currentStage !== 'completed') {
    return <LoadingOutlined style={{ color: '#1890ff' }} />;
  }

  return <ClockCircleOutlined style={{ color: '#d9d9d9' }} />;
};

const formatElapsedTime = (seconds: number): string => {
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return mins > 0 ? `${mins}m ${secs}s` : `${secs}s`;
};

export const StatusProgress: React.FC<StatusProgressProps> = ({
  stage,
  progress,
  message,
  error,
  elapsedTime,
}) => {
  const isFailed = stage === 'failed';
  const isCompleted = stage === 'completed';
  const isRunning = !isFailed && !isCompleted && stage !== 'idle';

  const progressStatus = isFailed
    ? 'exception'
    : isCompleted
    ? 'success'
    : 'active';

  return (
    <Card>
      <Space direction="vertical" style={{ width: '100%' }} size="large">
        {/* Header */}
        <div>
          <Space>
            <Title level={4} style={{ margin: 0 }}>
              {STAGE_LABELS[stage]}
            </Title>
            {isRunning && (
              <Tag color="processing" icon={<LoadingOutlined />}>
                Em Andamento
              </Tag>
            )}
            {isCompleted && (
              <Tag color="success" icon={<CheckCircleOutlined />}>
                Concluído
              </Tag>
            )}
            {isFailed && (
              <Tag color="error" icon={<CloseCircleOutlined />}>
                Falhou
              </Tag>
            )}
          </Space>
          {elapsedTime !== undefined && elapsedTime > 0 && (
            <Text type="secondary" style={{ display: 'block', marginTop: 4 }}>
              Tempo decorrido: {formatElapsedTime(elapsedTime)}
            </Text>
          )}
        </div>

        {/* Progress Bar */}
        <div>
          <Progress
            percent={Math.round(progress)}
            status={progressStatus}
            strokeColor={
              isFailed ? '#ff4d4f' : isCompleted ? '#52c41a' : '#1890ff'
            }
          />
          {message && (
            <Text type="secondary" style={{ fontSize: 12 }}>
              {message}
            </Text>
          )}
        </div>

        {/* Error Alert */}
        {error && (
          <Alert
            message="Erro na Instalação"
            description={error}
            type="error"
            showIcon
            closable={false}
          />
        )}

        {/* Stage Timeline */}
        <Timeline
          items={STAGE_ORDER.filter((s) => s !== 'completed').map((itemStage) => ({
            dot: getStageIcon(stage, itemStage, isFailed),
            children: (
              <Text
                type={
                  itemStage === stage && !isFailed
                    ? undefined
                    : itemStage === stage && isFailed
                    ? 'danger'
                    : 'secondary'
                }
                strong={itemStage === stage}
              >
                {STAGE_LABELS[itemStage]}
              </Text>
            ),
          }))}
        />
      </Space>
    </Card>
  );
};
