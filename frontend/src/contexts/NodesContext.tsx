/**
 * Context para compartilhar nós do Consul entre componentes
 * EVITA múltiplas requisições simultâneas para o mesmo endpoint
 * 
 * OTIMIZAÇÃO (2025-11-16):
 * - Carrega nodes em paralelo com outros providers
 * - Cache local para evitar requests repetidos
 * - Não bloqueia renderização da página
 */

import { createContext, useContext, useState, useEffect, useMemo, useCallback } from 'react';
import type { ReactNode } from 'react';
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
  site_name?: string; // Nome do site/servidor
}

interface NodesContextValue {
  nodes: ConsulNode[];
  mainServer: string | null;
  loading: boolean;
  error: string | null;
  reload: () => Promise<void>;
}

const NodesContext = createContext<NodesContextValue | undefined>(undefined);

export function NodesProvider({ children }: { children: ReactNode }) {
  const [nodes, setNodes] = useState<ConsulNode[]>([]);
  const [mainServer, setMainServer] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // SPEC-PERF-001: Memoizar loadNodes com useCallback para evitar re-renders
  const loadNodes = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      // SPEC-PERF-001: Timeout reduzido (backend tem cache de 60s)
      const response = await axios.get<{ success: boolean; data: ConsulNode[]; main_server: string }>(
        `${API_URL}/nodes`,
        {
          timeout: 10000, // 10s (reduzido de 60s - cache backend eh rapido)
        }
      );

      if (response.data.success) {
        setNodes(response.data.data || []);
        setMainServer(response.data.main_server || null);
        console.log(`[NodesContext] ${response.data.data?.length || 0} nos carregados`);
      }
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : 'Erro desconhecido';
      setError(errorMessage);
      console.error('[NodesContext] Erro ao carregar nos:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadNodes();
  }, [loadNodes]);

  // SPEC-PERF-001: Memoizar context value para evitar re-renders em cascata
  // Sem memoizacao, todos os consumers re-renderizam a cada render do provider
  const contextValue = useMemo(() => ({
    nodes,
    mainServer,
    loading,
    error,
    reload: loadNodes,
  }), [nodes, mainServer, loading, error, loadNodes]);

  return (
    <NodesContext.Provider value={contextValue}>
      {children}
    </NodesContext.Provider>
  );
}

export function useNodesContext() {
  const context = useContext(NodesContext);
  if (!context) {
    throw new Error('useNodesContext deve ser usado dentro de NodesProvider');
  }
  return context;
}

