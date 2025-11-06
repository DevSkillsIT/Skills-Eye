/**
 * Context para compartilhar campos metadata entre componentes
 * EVITA múltiplas requisições simultâneas para o mesmo endpoint
 */

import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import axios from 'axios';
import type { MetadataFieldDynamic } from '../services/api';

const API_URL = import.meta.env?.VITE_API_URL ?? 'http://localhost:5000/api/v1';

interface MetadataFieldsContextValue {
  fields: MetadataFieldDynamic[];
  loading: boolean;
  error: string | null;
  reload: () => Promise<void>;
}

const MetadataFieldsContext = createContext<MetadataFieldsContextValue | undefined>(undefined);

export function MetadataFieldsProvider({ children }: { children: ReactNode }) {
  const [fields, setFields] = useState<MetadataFieldDynamic[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadFields = async () => {
    try {
      setLoading(true);
      setError(null);

      // UMA ÚNICA requisição para todos os campos
      const response = await axios.get(`${API_URL}/prometheus-config/fields`, {
        timeout: 60000,
      });

      if (response.data.success) {
        setFields(response.data.fields);
      }
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : 'Erro desconhecido';
      setError(errorMessage);
      console.error('[MetadataFieldsContext] Erro ao carregar campos:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadFields();
  }, []);

  return (
    <MetadataFieldsContext.Provider value={{ fields, loading, error, reload: loadFields }}>
      {children}
    </MetadataFieldsContext.Provider>
  );
}

export function useMetadataFieldsContext() {
  const context = useContext(MetadataFieldsContext);
  if (!context) {
    throw new Error('useMetadataFieldsContext deve ser usado dentro de MetadataFieldsProvider');
  }
  return context;
}
