/**
 * Componente Compartilhado: Seletor de Servidores
 *
 * Mostra dropdown com servidores (Master + Slaves) incluindo nomes do Consul
 * Pode ser reutilizado em qualquer página que precise selecionar servidor
 *
 * ✅ OTIMIZAÇÃO (2025-11-16):
 * - Usa ServersContext ao invés de fazer request próprio
 * - Não bloqueia renderização (loading state)
 * - Reduz latência (usa cache do Context)
 * - Elimina requests duplicados
 */

import React, { useState, useEffect, useMemo, useCallback, memo } from 'react';
import { Select, Badge, Spin, App } from 'antd';
import { CloudServerOutlined } from '@ant-design/icons';
import { useServersContext } from '../contexts/ServersContext';

export interface Server {
  id: string;
  hostname: string;
  port: number;
  username: string;
  type: 'master' | 'slave';
  consul_node_name?: string;
  display_name: string;
}

interface ServerSelectorProps {
  value?: string;
  onChange?: (serverId: string, server: Server) => void;
  style?: React.CSSProperties;
  placeholder?: string;
  disabled?: boolean;
}

export const ServerSelector: React.FC<ServerSelectorProps> = memo(({
  value,
  onChange,
  style = { width: 350 },
  placeholder = 'Selecionar servidor',
  disabled = false,
}) => {
  const { message } = App.useApp();
  // ✅ OTIMIZAÇÃO: Usar ServersContext ao invés de fazer request próprio
  const { servers, master, loading, error: serversError } = useServersContext();
  const [selectedServer, setSelectedServer] = useState<string | undefined>(value);

  useEffect(() => {
    setSelectedServer(value);
  }, [value]);

  // ✅ OTIMIZAÇÃO: Selecionar servidor master quando servidores carregarem
  useEffect(() => {
    if (!loading && servers.length > 0 && master && !selectedServer) {
      setSelectedServer(master.id);
      if (onChange) {
        onChange(master.id, master);
      }
    }
  }, [loading, servers, master, selectedServer, onChange]);

  // Mostrar erro se houver
  useEffect(() => {
    if (serversError) {
      message.error(`Erro ao carregar servidores: ${serversError}`);
    }
  }, [serversError, message]);

  // ✅ OTIMIZAÇÃO: useCallback para evitar re-renders
  const handleChange = useCallback((serverId: string) => {
    const server = servers.find(s => s.id === serverId);
    setSelectedServer(serverId);
    if (onChange && server) {
      onChange(serverId, server);
    }
  }, [servers, onChange]);

  // ✅ OTIMIZAÇÃO: useMemo para processar servidores apenas quando necessário
  const serverOptions = useMemo(() => {
    return servers.map(server => ({
      key: server.id,
      value: server.id,
      server,
      isMaster: server.type === 'master',
    }));
  }, [servers]);

  return (
    <Select
      value={selectedServer}
      onChange={handleChange}
      style={style}
      placeholder={placeholder}
      disabled={disabled}
      loading={loading}
      suffixIcon={loading ? <Spin size="small" /> : <CloudServerOutlined />}
    >
      {/* Lista de servidores - usando serverOptions memoizado */}
      {serverOptions.map((option) => (
        <Select.Option key={option.key} value={option.value}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <CloudServerOutlined />
              <strong>{option.server.display_name}</strong>
            </div>
            <Badge
              status={option.isMaster ? 'success' : 'processing'}
              text={option.isMaster ? 'Master' : 'Slave'}
            />
          </div>
        </Select.Option>
      ))}
    </Select>
  );
}, (prevProps, nextProps) => {
  // ✅ OTIMIZAÇÃO: Comparação customizada para React.memo
  // Só re-renderiza se props relevantes mudarem
  return (
    prevProps.value === nextProps.value &&
    prevProps.disabled === nextProps.disabled &&
    prevProps.placeholder === nextProps.placeholder
  );
});

ServerSelector.displayName = 'ServerSelector';

/**
 * Hook para usar servidor selecionado
 * Retorna servidor selecionado e função para buscar dados daquele servidor
 */
export const useSelectedServer = () => {
  const [selectedServer, setSelectedServer] = useState<Server | null>(null);

  const selectServer = (serverId: string, server: Server) => {
    setSelectedServer(server);
  };

  return {
    selectedServer,
    selectServer,
  };
};
