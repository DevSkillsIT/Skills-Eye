import React from 'react';
import { Tag, Tooltip } from 'antd';
import { EnvironmentOutlined } from '@ant-design/icons';
import { getSiteBadgeColor, hasSiteSuffix } from '../utils/namingUtils';

interface SiteBadgeProps {
  /**
   * Site do serviço (ex: "rio", "palmas", "dtc")
   * Se não fornecido, tenta extrair do serviceName
   */
  site?: string;

  /**
   * Service name completo (para extrair site do sufixo)
   */
  serviceName?: string;

  /**
   * Se true, exibe ícone de localização
   */
  showIcon?: boolean;

  /**
   * Tamanho do badge
   */
  size?: 'small' | 'default' | 'large';
}

/**
 * Badge visual indicando o site de um serviço
 *
 * Exibe tag colorida com nome do site e tooltip explicativo
 * Usado em listagens e detalhes de services/exporters
 */
const SiteBadge: React.FC<SiteBadgeProps> = ({
  site,
  serviceName,
  showIcon = false,
  size = 'default',
}) => {
  // Se site não foi fornecido, tentar extrair do service name
  let effectiveSite = site;
  if (!effectiveSite && serviceName) {
    const parsed = hasSiteSuffix(serviceName);
    if (parsed.hasSuffix) {
      effectiveSite = parsed.site;
    }
  }

  // Se não tem site definido, não renderizar
  if (!effectiveSite) {
    return null;
  }

  const color = getSiteBadgeColor(effectiveSite);

  const siteLabels: Record<string, string> = {
    palmas: 'Palmas (Master)',
    rio: 'Rio (RMD/LDC)',
    dtc: 'DTC/Genesis',
    genesis: 'Genesis',
  };

  const label = siteLabels[effectiveSite.toLowerCase()] || effectiveSite.toUpperCase();

  const badge = (
    <Tag
      color={color}
      icon={showIcon ? <EnvironmentOutlined /> : undefined}
      style={{
        fontSize: size === 'small' ? '11px' : '12px',
        padding: size === 'small' ? '0 4px' : '2px 8px',
        margin: '0 4px',
      }}
    >
      {effectiveSite.toUpperCase()}
    </Tag>
  );

  return (
    <Tooltip title={label} placement="top">
      {badge}
    </Tooltip>
  );
};

export default SiteBadge;
