/**
 * Componente de Feedback Visual para campos metadata (P0.3)
 *
 * PROPÓSITO:
 * - Mostrar status de carregamento durante cold start
 * - Indicar origem dos dados (cache KV vs SSH)
 * - Exibir timestamp da última atualização
 * - Alertar sobre erros de conexão
 *
 * USO:
 * Adicione no topo de páginas que dependem de metadata:
 *   <MetadataFieldsStatus />
 */

import React from 'react';
import { Alert, Space, Tag, Spin } from 'antd';
import {
  LoadingOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
  WarningOutlined,
  ThunderboltOutlined,
} from '@ant-design/icons';
import { useMetadataFieldsContext } from '../contexts/MetadataFieldsContext';

interface MetadataFieldsStatusProps {
  /** Mostrar apenas quando estiver carregando (oculta quando completo) */
  onlyWhileLoading?: boolean;
  /** Estilo compacto (apenas ícone + texto curto) */
  compact?: boolean;
}

export default function MetadataFieldsStatus({
  onlyWhileLoading = false,
  compact = false,
}: MetadataFieldsStatusProps) {
  const { loading, error, cacheStatus, lastUpdate, isInitialLoad } =
    useMetadataFieldsContext();

  // Se onlyWhileLoading=true e não está carregando, não renderiza nada
  if (onlyWhileLoading && !loading) {
    return null;
  }

  // CASO 1: Carregando (cold start)
  if (loading && isInitialLoad) {
    return (
      <Alert
        type="info"
        showIcon
        icon={<Spin indicator={<LoadingOutlined spin />} />}
        message={
          compact ? (
            'Carregando campos...'
          ) : (
            <Space direction="vertical" size={0}>
              <strong>Carregando campos metadata...</strong>
              <small>
                Primeira carga pode demorar até 30 segundos (extração via SSH de múltiplos
                servidores Prometheus)
              </small>
            </Space>
          )
        }
        style={{ marginBottom: 16 }}
      />
    );
  }

  // CASO 2: Recarregando (não é cold start)
  if (loading && !isInitialLoad) {
    return (
      <Alert
        type="info"
        showIcon
        icon={<LoadingOutlined spin />}
        message="Atualizando campos metadata..."
        style={{ marginBottom: 16 }}
      />
    );
  }

  // CASO 3: Erro
  if (error) {
    return (
      <Alert
        type="error"
        showIcon
        message="Erro ao carregar campos metadata"
        description={
          <Space direction="vertical" size={0}>
            <span>{error}</span>
            <small>
              Verifique a conexão com o backend e servidores Prometheus (SSH). O sistema
              funcionará com campos básicos.
            </small>
          </Space>
        }
        style={{ marginBottom: 16 }}
      />
    );
  }

  // CASO 4: Sucesso - Mostrar origem dos dados
  if (!compact) {
    return (
      <Space style={{ marginBottom: 16 }} size="middle">
        {/* Tag indicando origem dos dados */}
        {cacheStatus === 'from-cache' && (
          <Tag icon={<ThunderboltOutlined />} color="success">
            Dados do Cache KV (rápido)
          </Tag>
        )}

        {cacheStatus === 'from-ssh' && (
          <Tag icon={<CheckCircleOutlined />} color="processing">
            Extraído via SSH (atualizado)
          </Tag>
        )}

        {/* Timestamp da última atualização */}
        {lastUpdate && (
          <Tag icon={<ClockCircleOutlined />} color="default">
            Atualizado: {lastUpdate.toLocaleTimeString('pt-BR')}
          </Tag>
        )}
      </Space>
    );
  }

  // Modo compacto: apenas indicador pequeno
  return null;
}
