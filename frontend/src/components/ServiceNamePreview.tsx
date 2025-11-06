import React, { useMemo } from 'react';
import { Alert, Space, Tag, Typography } from 'antd';
import { InfoCircleOutlined, CheckCircleOutlined } from '@ant-design/icons';
import { calculateFinalServiceName, getSiteBadgeColor } from '../utils/namingUtils';

const { Text } = Typography;

interface ServiceNamePreviewProps {
  /**
   * Nome base do serviço (ex: "selfnode_exporter", "blackbox_exporter")
   */
  baseName: string;

  /**
   * Metadata do serviço (deve conter campos site, cluster, datacenter)
   */
  metadata: Record<string, any>;

  /**
   * Se true, exibe em formato compacto (sem alert)
   */
  compact?: boolean;

  /**
   * Se true, exibe somente quando houver sufixo
   */
  showOnlyWithSuffix?: boolean;
}

/**
 * Componente que exibe preview do nome final do serviço
 * Mostra o nome que será registrado no Consul após aplicar sufixos de site
 *
 * Usado em formulários de criação/edição de services/exporters
 */
const ServiceNamePreview: React.FC<ServiceNamePreviewProps> = ({
  baseName,
  metadata,
  compact = false,
  showOnlyWithSuffix = false,
}) => {
  const preview = useMemo(() => {
    if (!baseName) {
      return null;
    }

    return calculateFinalServiceName(baseName, metadata || {});
  }, [baseName, metadata]);

  // Não renderizar se nome não foi definido
  if (!preview) {
    return null;
  }

  // Não renderizar se showOnlyWithSuffix=true e não há sufixo
  if (showOnlyWithSuffix && !preview.hasSuffix) {
    return null;
  }

  // Modo compacto: apenas o nome com tag
  if (compact) {
    return (
      <Space size="small">
        <Text strong>{preview.finalName}</Text>
        {preview.site && (
          <Tag color={getSiteBadgeColor(preview.site)}>
            {preview.site.toUpperCase()}
          </Tag>
        )}
      </Space>
    );
  }

  // Modo completo: Alert com informações detalhadas
  const alertType = preview.hasSuffix ? 'info' : 'success';
  const icon = preview.hasSuffix ? <InfoCircleOutlined /> : <CheckCircleOutlined />;

  return (
    <Alert
      type={alertType}
      icon={icon}
      showIcon
      message={
        <Space direction="vertical" size="small" style={{ width: '100%' }}>
          <Space size="middle">
            <Text strong>Nome no Consul:</Text>
            <Text code style={{ fontSize: '14px' }}>
              {preview.finalName}
            </Text>
            {preview.site && (
              <Tag color={getSiteBadgeColor(preview.site)}>
                SITE: {preview.site.toUpperCase()}
              </Tag>
            )}
          </Space>

          <Text type="secondary" style={{ fontSize: '12px' }}>
            {preview.reason}
          </Text>

          {preview.hasSuffix && (
            <Text type="secondary" style={{ fontSize: '12px' }}>
              💡 <strong>Prometheus do {preview.site?.toUpperCase()}</strong> deve usar:{' '}
              <Text code>services: ['{preview.finalName}']</Text>
            </Text>
          )}
        </Space>
      }
      style={{ marginTop: 16, marginBottom: 16 }}
    />
  );
};

export default ServiceNamePreview;
