/**
 * Componente Compartilhado: Seletor de Nós do Consul
 *
 * Mostra dropdown com nós do cluster Consul (Master + Slaves)
 * Pode ser reutilizado em qualquer página que precise selecionar nó
 * Inclui opção "Todos os nós" para visualização geral
 */

import React, { useState, useEffect } from 'react';
import { Select, Badge, Spin, App } from 'antd';
import { CloudServerOutlined } from '@ant-design/icons';
import axios from 'axios';

const API_URL = import.meta.env?.VITE_API_URL ?? 'http://localhost:5000/api/v1';

export interface ConsulNode {
  name: string;
  addr: string;
  port: number;
  status: number; // 1 = alive
  tags?: {
    role?: string;
    dc?: string;
  };
  services_count?: number;
}

interface NodeSelectorProps {
  value?: string; // "all" ou node_addr
  onChange?: (nodeAddr: string, node?: ConsulNode) => void;
  style?: React.CSSProperties;
  placeholder?: string;
  disabled?: boolean;
  showAllNodesOption?: boolean; // Se true, mostra opção "Todos os nós"
}

export const NodeSelector: React.FC<NodeSelectorProps> = ({
  value,
  onChange,
  style = { width: 350 },
  placeholder = 'Selecionar nó do Consul',
  disabled = false,
  showAllNodesOption = false,
}) => {
  const { message } = App.useApp();
  const [nodes, setNodes] = useState<ConsulNode[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedNode, setSelectedNode] = useState<string | undefined>(value);

  useEffect(() => {
    setSelectedNode(value);
  }, [value]);

  useEffect(() => {
    fetchNodes();
  }, []);

  const fetchNodes = async () => {
    setLoading(true);
    try {
      const response = await axios.get<{ success: boolean; data: ConsulNode[]; main_server: string }>(
        `${API_URL}/nodes`,
        {
          timeout: 60000, // 60 segundos - backend precisa tempo no cold start + cache de 30s
        }
      );

      if (response.data.success) {
        const nodesList = response.data.data || [];
        setNodes(nodesList);

        // Se showAllNodesOption e não tem nada selecionado, selecionar "all"
        // Senão, selecionar o main_server por padrão
        if (!selectedNode) {
          if (showAllNodesOption) {
            setSelectedNode('all');
            if (onChange) {
              onChange('all', undefined);
            }
          } else {
            // Selecionar o main_server (primeiro nó Master)
            const mainNode = nodesList.find(n => n.addr === response.data.main_server) || nodesList[0];
            if (mainNode) {
              setSelectedNode(mainNode.addr);
              if (onChange) {
                onChange(mainNode.addr, mainNode);
              }
            }
          }
        }
      }
    } catch (error: any) {
      console.error('Erro ao carregar nós do Consul:', error);

      // Mensagem de erro mais detalhada
      if (error.code === 'ECONNABORTED') {
        message.error('Timeout ao carregar nós - verifique se o backend está respondendo');
      } else if (error.response) {
        message.error(`Erro ao carregar nós: ${error.response.status} - ${error.response.statusText}`);
      } else if (error.request) {
        message.error('Erro ao carregar nós - backend não está respondendo');
      } else {
        message.error('Erro ao carregar nós do Consul');
      }
    } finally {
      setLoading(false);
    }
  };

  const handleChange = (nodeAddr: string) => {
    setSelectedNode(nodeAddr);

    if (nodeAddr === 'all') {
      if (onChange) {
        onChange('all', undefined);
      }
    } else {
      const node = nodes.find(n => n.addr === nodeAddr);
      if (onChange && node) {
        onChange(nodeAddr, node);
      }
    }
  };

  return (
    <Select
      value={selectedNode}
      onChange={handleChange}
      style={style}
      placeholder={placeholder}
      disabled={disabled}
      loading={loading}
      size="large"
      className="node-selector-large"
      suffixIcon={loading ? <Spin size="small" /> : <CloudServerOutlined />}
    >
      {/* Opção "Todos os nós" se habilitada */}
      {showAllNodesOption && (
        <Select.Option key="all" value="all">
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <CloudServerOutlined />
              <strong>Todos os nós</strong>
            </div>
            <Badge status="default" text="Cluster Completo" />
          </div>
        </Select.Option>
      )}

      {/* Lista de nós */}
      {nodes.map((node, index) => {
        const isMaster = index === 0; // Primeiro nó é o Master
        const displayName = node.name || node.addr;

        return (
          <Select.Option key={node.addr} value={node.addr}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <CloudServerOutlined />
                <strong>{displayName}</strong>
                <span style={{ color: '#8c8c8c', fontSize: '12px' }}>({node.addr})</span>
              </div>
              <Badge
                status={isMaster ? 'success' : 'processing'}
                text={isMaster ? 'Master' : 'Slave'}
              />
            </div>
          </Select.Option>
        );
      })}
    </Select>
  );
};

/**
 * Hook para usar nó selecionado
 * Retorna nó selecionado e função para buscar dados daquele nó
 */
export const useSelectedNode = () => {
  const [selectedNode, setSelectedNode] = useState<ConsulNode | null>(null);
  const [isAllNodes, setIsAllNodes] = useState(false);

  const selectNode = (nodeAddr: string, node?: ConsulNode) => {
    if (nodeAddr === 'all') {
      setIsAllNodes(true);
      setSelectedNode(null);
    } else {
      setIsAllNodes(false);
      setSelectedNode(node || null);
    }
  };

  return {
    selectedNode,
    isAllNodes,
    selectNode,
  };
};
