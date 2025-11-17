/**
 * Context para compartilhar servidores Prometheus entre componentes
 * EVITA múltiplas requisições simultâneas para o mesmo endpoint
 * 
 * OTIMIZAÇÃO (2025-11-16):
 * - Carrega servidores em paralelo com outros providers
 * - Cache local para evitar requests repetidos
 * - Não bloqueia renderização da página
 * - Segue padrão do NodesContext para consistência
 */

import { createContext, useContext, useState, useEffect } from 'react';
import type { ReactNode } from 'react';
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

interface ServersContextValue {
  servers: Server[];
  master: Server | null;
  loading: boolean;
  error: string | null;
  reload: () => Promise<void>;
}

const ServersContext = createContext<ServersContextValue | undefined>(undefined);

export function ServersProvider({ children }: { children: ReactNode }) {
  const [servers, setServers] = useState<Server[]>([]);
  const [master, setMaster] = useState<Server | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadServers = async () => {
    try {
      setLoading(true);
      setError(null);

      // ✅ OTIMIZAÇÃO: Timeout reduzido (backend tem cache de 5 minutos)
      const response = await axios.get<{ success: boolean; servers: Server[]; master: Server }>(
        `${API_URL}/metadata-fields/servers`,
        {
          timeout: 10000, // 10s (reduzido de 15s - cache backend é rápido)
        }
      );

      if (response.data.success) {
        setServers(response.data.servers || []);
        setMaster(response.data.master || null);
        console.log(`[ServersContext] ✅ ${response.data.servers?.length || 0} servidores carregados`);
      }
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : 'Erro desconhecido';
      setError(errorMessage);
      console.error('[ServersContext] ❌ Erro ao carregar servidores:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadServers();
  }, []);

  return (
    <ServersContext.Provider
      value={{
        servers,
        master,
        loading,
        error,
        reload: loadServers,
      }}
    >
      {children}
    </ServersContext.Provider>
  );
}

export function useServersContext() {
  const context = useContext(ServersContext);
  if (!context) {
    throw new Error('useServersContext deve ser usado dentro de ServersProvider');
  }
  return context;
}

