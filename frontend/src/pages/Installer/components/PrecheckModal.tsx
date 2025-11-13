import React from 'react';
import { Modal, List, Tag, Space, Progress, Typography, Alert } from 'antd';
import {
  CheckCircleOutlined,
  CloseCircleOutlined,
  LoadingOutlined,
  ClockCircleOutlined,
} from '@ant-design/icons';
import type { PrecheckItem, PrecheckStatus } from '../types';

const { Text } = Typography;

export interface PrecheckModalProps {
  visible: boolean;
  prechecks: PrecheckItem[];
  onCancel?: () => void;
  onRetry?: () => void;
}

const getStatusIcon = (status: PrecheckStatus) => {
  switch (status) {
    case 'success':
      return <CheckCircleOutlined style={{ color: '#52c41a' }} />;
    case 'failed':
      return <CloseCircleOutlined style={{ color: '#ff4d4f' }} />;
    case 'running':
      return <LoadingOutlined style={{ color: '#1890ff' }} />;
    default:
      return <ClockCircleOutlined style={{ color: '#d9d9d9' }} />;
  }
};

const getStatusColor = (status: PrecheckStatus): string => {
  switch (status) {
    case 'success':
      return 'success';
    case 'failed':
      return 'error';
    case 'running':
      return 'processing';
    default:
      return 'default';
  }
};

const getStatusText = (status: PrecheckStatus): string => {
  switch (status) {
    case 'success':
      return 'OK';
    case 'failed':
      return 'Falhou';
    case 'running':
      return 'Verificando...';
    default:
      return 'Pendente';
  }
};

export const PrecheckModal: React.FC<PrecheckModalProps> = ({
  visible,
  prechecks,
  onCancel,
  onRetry,
}) => {
  const totalChecks = prechecks.length;
  const completedChecks = prechecks.filter(
    (p) => p.status === 'success' || p.status === 'failed'
  ).length;
  const failedChecks = prechecks.filter((p) => p.status === 'failed').length;
  const successChecks = prechecks.filter((p) => p.status === 'success').length;
  const isRunning = prechecks.some((p) => p.status === 'running');
  const allComplete = completedChecks === totalChecks;
  const allSuccess = successChecks === totalChecks;

  const progressPercent = totalChecks > 0 ? (completedChecks / totalChecks) * 100 : 0;

  return (
    <Modal
      title="Pré-validação de Instalação"
      open={visible}
      onCancel={onCancel}
      footer={null}
      width={700}
      maskClosable={!isRunning}
      closable={!isRunning}
    >
      <Space direction="vertical" style={{ width: '100%' }} size="large">
        {/* Progress Summary */}
        <div>
          <div style={{ marginBottom: 8 }}>
            <Text strong>
              Progresso: {completedChecks}/{totalChecks} verificações
            </Text>
            {failedChecks > 0 && (
              <Text type="danger" style={{ marginLeft: 16 }}>
                ({failedChecks} falhas)
              </Text>
            )}
          </div>
          <Progress
            percent={Math.round(progressPercent)}
            status={
              isRunning ? 'active' : failedChecks > 0 ? 'exception' : 'success'
            }
            strokeColor={failedChecks > 0 ? '#ff4d4f' : '#52c41a'}
          />
        </div>

        {/* Results Alert */}
        {allComplete && (
          <>
            {allSuccess ? (
              <Alert
                message="Todas verificações passaram"
                description="O sistema está pronto para instalação."
                type="success"
                showIcon
              />
            ) : (
              <Alert
                message={`${failedChecks} verificação(ões) falharam`}
                description="Corrija os problemas antes de continuar com a instalação."
                type="error"
                showIcon
              />
            )}
          </>
        )}

        {/* Precheck List */}
        <List
          dataSource={prechecks}
          renderItem={(item) => (
            <List.Item key={item.key}>
              <List.Item.Meta
                avatar={getStatusIcon(item.status)}
                title={
                  <Space>
                    <Text strong>{item.label}</Text>
                    <Tag color={getStatusColor(item.status)}>
                      {getStatusText(item.status)}
                    </Tag>
                  </Space>
                }
                description={
                  <Space direction="vertical" size={4}>
                    <Text type="secondary">{item.description}</Text>
                    {item.detail && (
                      <Text
                        type={item.status === 'failed' ? 'danger' : 'secondary'}
                        style={{ fontSize: 12 }}
                      >
                        {item.detail}
                      </Text>
                    )}
                  </Space>
                }
              />
            </List.Item>
          )}
          bordered
        />

        {/* Action Buttons */}
        {allComplete && !allSuccess && onRetry && (
          <Alert
            message="Dica"
            description="Após corrigir os problemas identificados, clique em 'Repetir Validação'."
            type="info"
            showIcon
          />
        )}
      </Space>
    </Modal>
  );
};
