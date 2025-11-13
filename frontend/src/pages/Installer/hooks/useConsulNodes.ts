/**
 * Hook for fetching and managing Consul nodes
 * Encapsulates node fetching logic and normalization
 */

import { useState, useEffect } from 'react';
import { App } from 'antd';
import { consulAPI } from '../../../services/api';
import type { ConsulNode } from '../types';

/**
 * Normalize Consul node data from API
 * Handles different field name variations
 */
function normalizeConsulNode(raw: Record<string, unknown>): ConsulNode {
  const nodeName = typeof raw['node'] === 'string'
    ? raw['node'] as string
    : typeof raw['Node'] === 'string'
    ? raw['Node'] as string
    : typeof raw['Name'] === 'string'
    ? raw['Name'] as string
    : 'desconhecido';

  const addrValue = typeof raw['addr'] === 'string'
    ? raw['addr'] as string
    : typeof raw['Address'] === 'string'
    ? raw['Address'] as string
    : typeof raw['address'] === 'string'
    ? raw['address'] as string
    : '';

  const statusValue = typeof raw['status'] === 'string'
    ? raw['status'] as string
    : typeof raw['Status'] === 'string'
    ? raw['Status'] as string
    : undefined;

  const typeValue = typeof raw['type'] === 'string'
    ? raw['type'] as string
    : typeof raw['Type'] === 'string'
    ? raw['Type'] as string
    : undefined;

  const servicesCountValue = typeof raw['services_count'] === 'number'
    ? raw['services_count'] as number
    : typeof raw['ServicesCount'] === 'number'
    ? raw['ServicesCount'] as number
    : 0;

  return {
    node: nodeName,
    addr: addrValue,
    status: statusValue,
    type: typeValue,
    services_count: servicesCountValue,
  };
}

export function useConsulNodes() {
  const { message } = App.useApp();
  const [nodes, setNodes] = useState<ConsulNode[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchNodes = async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await consulAPI.getNodes();

      if (response.data.success) {
        const nodesList = response.data.data || [];
        const normalized = nodesList.map(normalizeConsulNode);
        setNodes(normalized);
      } else {
        throw new Error('Failed to fetch nodes');
      }
    } catch (err: any) {
      const errorMsg = err?.response?.data?.detail || err?.message || 'Erro ao carregar nós';
      setError(errorMsg);
      message.error(`Erro ao carregar nós do Consul: ${errorMsg}`);
      console.error('[useConsulNodes] Error:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchNodes();
  }, []);

  return {
    nodes,
    loading,
    error,
    refetch: fetchNodes,
  };
}
