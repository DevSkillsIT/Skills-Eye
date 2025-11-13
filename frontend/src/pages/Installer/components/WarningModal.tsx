import React from 'react';
import { Modal, Alert, Space, Typography, List, Tag } from 'antd';
import {
  ExclamationCircleOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
} from '@ant-design/icons';

const { Text, Paragraph } = Typography;

export interface WarningModalContent {
  duplicateConsul?: boolean;
  existingInstall?: boolean;
  services: string[];
  portOpen?: boolean;
  serviceRunning?: boolean;
  hasConfig?: boolean;
  targetType: 'linux' | 'windows';
}

export interface WarningModalProps {
  visible: boolean;
  content: WarningModalContent | null;
  onConfirm: () => void;
  onCancel: () => void;
}

export const WarningModal: React.FC<WarningModalProps> = ({
  visible,
  content,
  onConfirm,
  onCancel,
}) => {
  if (!content) return null;

  const {
    duplicateConsul,
    existingInstall,
    services,
    portOpen,
    serviceRunning,
    hasConfig,
    targetType,
  } = content;

  const exporterName =
    targetType === 'linux' ? 'Node Exporter' : 'Windows Exporter';
  const exporterPort = targetType === 'linux' ? '9100' : '9182';

  const warnings: Array<{ key: string; message: string; severity: 'warning' | 'error' }> = [];

  if (duplicateConsul) {
    warnings.push({
      key: 'duplicate',
      message: `Já existem ${services.length} serviço(s) registrado(s) no Consul para este host.`,
      severity: 'warning',
    });
  }

  if (existingInstall) {
    warnings.push({
      key: 'existing',
      message: `${exporterName} já está instalado neste host.`,
      severity: 'warning',
    });
  }

  if (portOpen) {
    warnings.push({
      key: 'port',
      message: `A porta ${exporterPort} já está em uso no host.`,
      severity: 'warning',
    });
  }

  if (serviceRunning) {
    warnings.push({
      key: 'service',
      message: `O serviço ${exporterName} já está em execução.`,
      severity: 'warning',
    });
  }

  if (hasConfig) {
    warnings.push({
      key: 'config',
      message: 'Arquivos de configuração existentes serão sobrescritos.',
      severity: 'error',
    });
  }

  const hasErrors = warnings.some((w) => w.severity === 'error');
  const hasWarnings = warnings.some((w) => w.severity === 'warning');

  return (
    <Modal
      title={
        <Space>
          <ExclamationCircleOutlined style={{ color: '#faad14' }} />
          <span>Avisos Detectados</span>
        </Space>
      }
      open={visible}
      onOk={onConfirm}
      onCancel={onCancel}
      okText="Prosseguir Mesmo Assim"
      cancelText="Cancelar"
      okButtonProps={{
        danger: hasErrors,
      }}
      width={600}
    >
      <Space direction="vertical" style={{ width: '100%' }} size="large">
        {/* Summary Alert */}
        <Alert
          message={
            hasErrors
              ? 'Problemas Críticos Detectados'
              : 'Avisos de Instalação'
          }
          description={
            hasErrors
              ? 'Prosseguir pode sobrescrever configurações existentes.'
              : 'O sistema detectou uma instalação prévia ou serviços já registrados.'
          }
          type={hasErrors ? 'error' : 'warning'}
          showIcon
        />

        {/* Warnings List */}
        <div>
          <Text strong style={{ display: 'block', marginBottom: 8 }}>
            Detalhes:
          </Text>
          <List
            dataSource={warnings}
            renderItem={(item) => (
              <List.Item key={item.key}>
                <Space>
                  {item.severity === 'error' ? (
                    <CloseCircleOutlined style={{ color: '#ff4d4f' }} />
                  ) : (
                    <ExclamationCircleOutlined style={{ color: '#faad14' }} />
                  )}
                  <Text>{item.message}</Text>
                  <Tag color={item.severity === 'error' ? 'red' : 'orange'}>
                    {item.severity === 'error' ? 'CRÍTICO' : 'AVISO'}
                  </Tag>
                </Space>
              </List.Item>
            )}
            size="small"
            bordered
          />
        </div>

        {/* Existing Services */}
        {duplicateConsul && services.length > 0 && (
          <div>
            <Text strong style={{ display: 'block', marginBottom: 8 }}>
              Serviços no Consul ({services.length}):
            </Text>
            <List
              dataSource={services}
              renderItem={(service) => (
                <List.Item key={service}>
                  <Space>
                    <CheckCircleOutlined style={{ color: '#52c41a' }} />
                    <Text code>{service}</Text>
                  </Space>
                </List.Item>
              )}
              size="small"
              bordered
              style={{ maxHeight: 200, overflow: 'auto' }}
            />
          </div>
        )}

        {/* Actions to Take */}
        <Alert
          message="O que acontecerá se prosseguir:"
          description={
            <ul style={{ marginBottom: 0, paddingLeft: 20 }}>
              {existingInstall && (
                <li>
                  O {exporterName} existente será atualizado/reinstalado
                </li>
              )}
              {portOpen && (
                <li>
                  O processo atual na porta {exporterPort} será interrompido
                </li>
              )}
              {serviceRunning && (
                <li>O serviço será parado e reiniciado após atualização</li>
              )}
              {hasConfig && (
                <li>
                  Configurações personalizadas serão <strong>substituídas</strong>
                </li>
              )}
              {duplicateConsul && (
                <li>Um novo serviço será registrado no Consul</li>
              )}
            </ul>
          }
          type="info"
          showIcon
        />

        {/* Recommendation */}
        {hasWarnings && !hasErrors && (
          <Paragraph type="secondary" style={{ marginBottom: 0 }}>
            <strong>Recomendação:</strong> Se você tem certeza que deseja
            reinstalar ou atualizar o exporter, clique em "Prosseguir Mesmo
            Assim". Caso contrário, cancele e revise a instalação existente.
          </Paragraph>
        )}
      </Space>
    </Modal>
  );
};
