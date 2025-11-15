/**
 * BadgeStatus - Componente para exibir indicadores visuais de performance
 *
 * SPRINT 1 FIX (2025-11-15)
 *
 * Exibe badges com informações de:
 * - Fonte (Master vs Fallback)
 * - Cache (HIT/MISS)
 * - Staleness (idade dos dados)
 * - Performance (tempo total de resposta)
 *
 * IMPORTANTE: Este componente consome _metadata retornado pelo backend,
 * NÃO confundir com metadata/fields do KV (campos de configuração)!
 */
import React from 'react';
import { Badge, Space, Tag, Tooltip } from 'antd';
import {
  CheckCircleOutlined,
  ClockCircleOutlined,
  CloudServerOutlined,
  DatabaseOutlined,
  ThunderboltOutlined,
  WarningOutlined,
} from '@ant-design/icons';

export interface ResponseMetadata {
  /** Nome do servidor que respondeu (ex: "172.16.1.26") */
  source_name?: string;

  /** Se true, resposta veio do servidor master */
  is_master?: boolean;

  /** Status do cache: "hit", "miss", "disabled" */
  cache_status?: string;

  /** Idade do cache em segundos (se cache hit) */
  age_seconds?: number;

  /** Staleness dos dados em ms (quanto tempo os dados têm de atraso) */
  staleness_ms?: number;

  /** Tempo total da requisição em ms */
  total_time_ms?: number;
}

export interface BadgeStatusProps {
  /** Metadata retornado pelo backend */
  metadata: ResponseMetadata | null;

  /** Se true, exibe versão compacta (apenas ícones) */
  compact?: boolean;

  /** Se true, mostra warning se staleness > threshold */
  showStalenessWarning?: boolean;

  /** Threshold de staleness em ms para exibir warning (padrão: 5000ms) */
  stalenessThreshold?: number;
}

/**
 * Componente BadgeStatus - Indicadores visuais de performance
 *
 * @example
 * ```tsx
 * const [responseMetadata, setResponseMetadata] = useState<ResponseMetadata | null>(null);
 *
 * // No requestHandler:
 * if (response._metadata) {
 *   setResponseMetadata(response._metadata);
 * }
 *
 * // No render:
 * <BadgeStatus metadata={responseMetadata} />
 * ```
 */
export const BadgeStatus: React.FC<BadgeStatusProps> = ({
  metadata,
  compact = false,
  showStalenessWarning = true,
  stalenessThreshold = 5000,
}) => {
  if (!metadata) {
    return null;
  }

  const {
    source_name,
    is_master,
    cache_status,
    age_seconds,
    staleness_ms,
    total_time_ms,
  } = metadata;

  // BADGE 1: Master vs Fallback
  const renderMasterBadge = () => {
    if (is_master === undefined) return null;

    return (
      <Tooltip
        title={
          is_master
            ? `Servidor Master: ${source_name}`
            : `Servidor Fallback: ${source_name}`
        }
      >
        <Tag
          icon={<CloudServerOutlined />}
          color={is_master ? 'green' : 'orange'}
        >
          {compact ? '' : (is_master ? 'Master' : 'Fallback')}
        </Tag>
      </Tooltip>
    );
  };

  // BADGE 2: Cache Status
  const renderCacheBadge = () => {
    if (!cache_status || cache_status === 'disabled') return null;

    const isHit = cache_status === 'hit';
    const ageText = age_seconds !== undefined
      ? ` (${age_seconds < 60 ? `${age_seconds}s` : `${Math.floor(age_seconds / 60)}m`})`
      : '';

    return (
      <Tooltip
        title={
          isHit
            ? `Cache HIT - Dados em cache há ${age_seconds}s`
            : 'Cache MISS - Dados buscados do Consul'
        }
      >
        <Tag
          icon={isHit ? <DatabaseOutlined /> : <ThunderboltOutlined />}
          color={isHit ? 'blue' : 'default'}
        >
          {compact ? '' : `Cache ${isHit ? 'HIT' : 'MISS'}${isHit ? ageText : ''}`}
        </Tag>
      </Tooltip>
    );
  };

  // BADGE 3: Staleness Warning
  const renderStalenessBadge = () => {
    if (!showStalenessWarning || staleness_ms === undefined) return null;

    const isStale = staleness_ms > stalenessThreshold;
    if (!isStale && compact) return null; // Não exibir se tudo OK no modo compacto

    const staleSec = (staleness_ms / 1000).toFixed(1);

    return (
      <Tooltip
        title={
          isStale
            ? `⚠️ Dados podem estar desatualizados (staleness: ${staleSec}s)`
            : `✓ Dados atualizados (staleness: ${staleSec}s)`
        }
      >
        <Tag
          icon={isStale ? <WarningOutlined /> : <CheckCircleOutlined />}
          color={isStale ? 'red' : 'green'}
        >
          {compact ? '' : `Staleness: ${staleSec}s`}
        </Tag>
      </Tooltip>
    );
  };

  // BADGE 4: Performance (tempo total)
  const renderPerformanceBadge = () => {
    if (total_time_ms === undefined) return null;

    // Definir cor baseado em performance
    let color = 'green';
    if (total_time_ms > 3000) color = 'red';
    else if (total_time_ms > 1000) color = 'orange';

    const timeText = total_time_ms < 1000
      ? `${total_time_ms}ms`
      : `${(total_time_ms / 1000).toFixed(2)}s`;

    return (
      <Tooltip title={`Tempo total de resposta: ${timeText}`}>
        <Tag
          icon={<ClockCircleOutlined />}
          color={color}
        >
          {compact ? '' : timeText}
        </Tag>
      </Tooltip>
    );
  };

  return (
    <Space size="small" wrap>
      {renderMasterBadge()}
      {renderCacheBadge()}
      {renderStalenessBadge()}
      {renderPerformanceBadge()}
    </Space>
  );
};

export default BadgeStatus;
