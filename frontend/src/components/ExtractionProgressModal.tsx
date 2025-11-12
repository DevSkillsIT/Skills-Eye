/**
 * Modal de Progresso de Extração de Campos Metadata
 *
 * Componente compartilhado entre PrometheusConfig e MetadataFields
 * Mostra status de extração SSH de campos dos servidores
 */

import React from 'react';
import {
  Modal,
  Button,
  Space,
  Alert,
  Tag,
  Timeline,
  Tooltip,
} from 'antd';
import {
  LoadingOutlined,
  ThunderboltOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  WarningOutlined,
  SyncOutlined,
  ReloadOutlined,
  CloudServerOutlined,
  ClockCircleOutlined,
  CheckOutlined,
} from '@ant-design/icons';

export interface ServerStatus {
  hostname: string;
  success: boolean;
  from_cache: boolean;
  files_count: number;
  fields_count: number;
  error?: string | null;
  duration_ms: number;
}

export interface ExtractionProgressModalProps {
  visible: boolean;
  onClose: () => void;
  onRefresh: () => Promise<void>;
  loading: boolean;
  fromCache: boolean;
  successfulServers: number;
  totalServers: number;
  serverStatus: ServerStatus[];
  totalFields: number;
  error: string | null;
}

const ExtractionProgressModal: React.FC<ExtractionProgressModalProps> = ({
  visible,
  onClose,
  onRefresh,
  loading,
  fromCache,
  successfulServers,
  totalServers,
  serverStatus,
  totalFields,
  error,
}) => {
  return (
    <Modal
      title={
        <Space>
          {loading ? (
            <LoadingOutlined style={{ color: '#1890ff' }} spin />
          ) : fromCache ? (
            <ThunderboltOutlined style={{ color: '#52c41a' }} />
          ) : (
            <CheckCircleOutlined style={{ color: '#52c41a' }} />
          )}
          <span>
            {loading
              ? 'Extraindo Campos Metadata dos Servidores...'
              : fromCache
              ? 'Configurações Carregadas (Cache)'
              : `Extração Concluída (${successfulServers}/${totalServers} servidores)`}
          </span>
        </Space>
      }
      open={visible}
      onCancel={onClose}
      width={700}
      footer={
        <div style={{
          display: 'flex',
          justifyContent: 'flex-end',
          gap: '12px',
          padding: '4px 0'
        }}>
          {/* Botão Atualizar Dados - PRIMEIRO */}
          <Tooltip
            title={
              <div style={{ textAlign: 'center' }}>
                <div style={{ fontWeight: 600, marginBottom: 4 }}>
                  Forçar Extração SSH
                </div>
                <div style={{ fontSize: 12, opacity: 0.9 }}>
                  Conecta em todos os servidores Prometheus<br/>
                  e extrai os campos metadata mais recentes<br/>
                  dos arquivos prometheus.yml via SSH
                </div>
              </div>
            }
            placement="topRight"
          >
            <Button
              type="primary"
              size="large"
              icon={<SyncOutlined spin={loading} />}
              onClick={async () => {
                onClose();
                await onRefresh();
              }}
              disabled={loading}
              style={{
                background: loading ? '#d9d9d9' : 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                border: 'none',
                borderRadius: '8px',
                height: '44px',
                padding: '0 24px',
                fontWeight: 600,
                fontSize: '15px',
                boxShadow: loading ? 'none' : '0 4px 12px rgba(102, 126, 234, 0.4)',
                transition: 'all 0.3s cubic-bezier(0.645, 0.045, 0.355, 1)',
              }}
              onMouseEnter={(e) => {
                if (!loading) {
                  e.currentTarget.style.transform = 'translateY(-2px)';
                  e.currentTarget.style.boxShadow = '0 6px 20px rgba(102, 126, 234, 0.6)';
                }
              }}
              onMouseLeave={(e) => {
                if (!loading) {
                  e.currentTarget.style.transform = 'translateY(0)';
                  e.currentTarget.style.boxShadow = '0 4px 12px rgba(102, 126, 234, 0.4)';
                }
              }}
            >
              {loading ? 'Extraindo...' : 'Atualizar Dados'}
            </Button>
          </Tooltip>

          {/* Botão OK - SEGUNDO */}
          <Button
            size="large"
            icon={<CheckOutlined />}
            onClick={onClose}
            disabled={loading}
            style={{
              borderRadius: '8px',
              height: '44px',
              padding: '0 24px',
              fontWeight: 500,
              fontSize: '15px',
              border: '2px solid #d9d9d9',
              transition: 'all 0.3s cubic-bezier(0.645, 0.045, 0.355, 1)',
            }}
            onMouseEnter={(e) => {
              if (!loading) {
                e.currentTarget.style.borderColor = '#40a9ff';
                e.currentTarget.style.color = '#40a9ff';
                e.currentTarget.style.transform = 'translateY(-1px)';
              }
            }}
            onMouseLeave={(e) => {
              if (!loading) {
                e.currentTarget.style.borderColor = '#d9d9d9';
                e.currentTarget.style.color = 'rgba(0, 0, 0, 0.88)';
                e.currentTarget.style.transform = 'translateY(0)';
              }
            }}
          >
            OK
          </Button>
        </div>
      }
    >
      <div style={{ marginBottom: 16 }}>
        {loading ? (
          <Alert
            message="Processando servidores..."
            description="Conectando via SSH e extraindo campos metadata de cada servidor. Isso pode levar alguns segundos."
            type="info"
            showIcon
            icon={<SyncOutlined spin />}
          />
        ) : fromCache ? (
          <Alert
            message={
              <Space>
                <ThunderboltOutlined />
                Dados carregados do cache instantaneamente
              </Space>
            }
            description="Todos os servidores já foram processados anteriormente. Nenhuma conexão SSH foi necessária."
            type="success"
            showIcon
          />
        ) : error ? (
          <Alert
            message="Erro ao carregar campos"
            description={error}
            type="error"
            showIcon
          />
        ) : successfulServers === totalServers ? (
          <Alert
            message={
              <Space>
                <CheckCircleOutlined />
                Todos os servidores processados com sucesso
              </Space>
            }
            description={`Extraídos ${totalFields} campos únicos de ${totalServers} servidores.`}
            type="success"
            showIcon
          />
        ) : (
          <Alert
            message={
              <Space>
                <WarningOutlined />
                Alguns servidores falharam
              </Space>
            }
            description={`${successfulServers} de ${totalServers} servidores processados com sucesso. Verifique os detalhes abaixo.`}
            type="warning"
            showIcon
          />
        )}
      </div>

      {/* Timeline com Status de Cada Servidor */}
      {serverStatus.length > 0 && (
        <div>
          <div style={{ marginBottom: 12, fontWeight: 500, fontSize: 14 }}>
            Status dos Servidores:
          </div>
          <Timeline
            items={serverStatus.map((server) => {
              const isProcessing = loading && server.duration_ms === 0 && !server.success && !server.error;

              return {
                color: isProcessing ? 'blue' : server.success ? 'green' : 'red',
                dot: isProcessing ? (
                  <LoadingOutlined style={{ fontSize: 16 }} spin />
                ) : server.success ? (
                  <CheckCircleOutlined style={{ fontSize: 16 }} />
                ) : (
                  <CloseCircleOutlined style={{ fontSize: 16 }} />
                ),
                children: (
                  <div>
                    <Space>
                      <CloudServerOutlined />
                      <strong>{server.hostname}</strong>
                      {isProcessing ? (
                        <Tag color="processing" icon={<SyncOutlined spin />}>
                          Processando...
                        </Tag>
                      ) : server.from_cache ? (
                        <Tag color="cyan" icon={<ThunderboltOutlined />}>
                          Cache
                        </Tag>
                      ) : server.success ? (
                        <Tag color="green">Sucesso</Tag>
                      ) : (
                        <Tag color="red">Falha</Tag>
                      )}
                      {server.duration_ms > 0 && (
                        <Tag icon={<ClockCircleOutlined />}>
                          {server.duration_ms}ms
                        </Tag>
                      )}
                    </Space>
                    <div style={{ marginTop: 4, fontSize: 12, color: '#666' }}>
                      {isProcessing ? (
                        <span style={{ color: '#1890ff' }}>
                          Conectando via SSH e extraindo campos metadata...
                        </span>
                      ) : server.success ? (
                        server.from_cache ? (
                          <span style={{ color: '#52c41a' }}>
                            Dados carregados do cache (processado anteriormente)
                          </span>
                        ) : (
                          <>
                            {server.files_count} arquivos processados,{' '}
                            {server.fields_count} campos novos encontrados
                          </>
                        )
                      ) : (
                        <span style={{ color: '#ff4d4f' }}>
                          <WarningOutlined /> Erro:{' '}
                          {server.error || 'Servidor offline ou inacessível'}
                        </span>
                      )}
                    </div>
                  </div>
                ),
              };
            })}
          />
        </div>
      )}
    </Modal>
  );
};

export default ExtractionProgressModal;
