/**
 * Componente Compartilhado: Seletor de Servidores
 *
 * Mostra dropdown com servidores (Master + Slaves) incluindo nomes do Consul
 * Pode ser reutilizado em qualquer página que precise selecionar servidor
 */

import React, { useState, useEffect } from 'react';
import { Select, Badge, Spin, message } from 'antd';
import { CloudServerOutlined, CheckCircleOutlined } from '@ant-design/icons';
import axios from 'axios';

const API_URL = import.meta.env?.VITE_API_URL ?? 'http://localhost:5000/api/v1';

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

export const ServerSelector: React.FC<ServerSelectorProps> = ({
  value,
  onChange,
  style = { width: 350 },
  placeholder = 'Selecionar servidor',
  disabled = false,
}) => {
  const [servers, setServers] = useState<Server[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedServer, setSelectedServer] = useState<string | undefined>(value);

  useEffect(() => {
    setSelectedServer(value);
  }, [value]);

  useEffect(() => {
    fetchServers();
  }, []);

  const fetchServers = async () => {
    setLoading(true);
    try {
      const response = await axios.get<{ success: boolean; servers: Server[]; master: Server }>
        (`${API_URL}/metadata-fields/servers`, {
          timeout: 5000, // 5 segundos - se demorar mais, usa cache
        });

      if (response.data.success) {
        setServers(response.data.servers);

        // Se não tem servidor selecionado, selecionar master por padrão
        if (!selectedServer && response.data.master) {
          setSelectedServer(response.data.master.id);
          if (onChange) {
            onChange(response.data.master.id, response.data.master);
          }
        }
      }
    } catch (error: any) {
      console.error('Erro ao carregar servidores:', error);
      // Não exibir erro, apenas log - servidor pode estar offline
    } finally {
      setLoading(false);
    }
  };

  const handleChange = (serverId: string) => {
    const server = servers.find(s => s.id === serverId);
    setSelectedServer(serverId);
    if (onChange && server) {
      onChange(serverId, server);
    }
  };

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
      {servers.map(server => (
        <Select.Option key={server.id} value={server.id}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <CloudServerOutlined />
              <strong>{server.display_name}</strong>
            </div>
            <Badge
              status={server.type === 'master' ? 'success' : 'processing'}
              text={server.type === 'master' ? 'Master' : 'Slave'}
            />
          </div>
        </Select.Option>
      ))}
    </Select>
  );
};

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
