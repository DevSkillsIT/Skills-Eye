/**
 * Context para compartilhar campos metadata entre componentes
 * EVITA múltiplas requisições simultâneas para o mesmo endpoint
 *
 * FEEDBACK VISUAL ADICIONADO (P0.3):
 * - cacheStatus: indica origem dos dados (cache KV, SSH, erro)
 * - lastUpdate: timestamp da última atualização
 * - isInitialLoad: indica se é a primeira carga (fria)
 */

import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import axios from 'axios';
import type { MetadataFieldDynamic } from '../services/api';

const API_URL = import.meta.env?.VITE_API_URL ?? 'http://localhost:5000/api/v1';

export type CacheStatus = 'loading' | 'from-cache' | 'from-ssh' | 'error' | 'idle';

interface MetadataFieldsContextValue {
  fields: MetadataFieldDynamic[];
  loading: boolean;
  error: string | null;
  reload: () => Promise<void>;

  // NOVO: Feedback visual detalhado
  cacheStatus: CacheStatus;
  lastUpdate: Date | null;
  isInitialLoad: boolean;
}

const MetadataFieldsContext = createContext<MetadataFieldsContextValue | undefined>(undefined);

export function MetadataFieldsProvider({ children }: { children: ReactNode }) {
  const [fields, setFields] = useState<MetadataFieldDynamic[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // NOVO: Estados de feedback visual (P0.3)
  const [cacheStatus, setCacheStatus] = useState<CacheStatus>('idle');
  const [lastUpdate, setLastUpdate] = useState<Date | null>(null);
  const [isInitialLoad, setIsInitialLoad] = useState(true);

  const loadFields = async () => {
    try {
      setLoading(true);
      setError(null);
      setCacheStatus('loading');

      // PASSO 1: Registrar início do carregamento
      const startTime = performance.now();
      console.log('[MetadataFieldsContext] 🔄 Iniciando carregamento de campos...');

      // PASSO 2: Fazer requisição ao backend
      // UMA ÚNICA requisição para todos os campos
      const response = await axios.get(`${API_URL}/prometheus-config/fields`, {
        timeout: 60000,
      });

      const endTime = performance.now();
      const duration = ((endTime - startTime) / 1000).toFixed(2);

      if (response.data.success) {
        setFields(response.data.fields);
        setLastUpdate(new Date());

        // PASSO 3: Detectar origem dos dados (cache KV vs SSH)
        // Backend retorna `source` indicando de onde vieram os dados
        const source = response.data.source || 'unknown';

        if (source === 'cache' || duration < 5) {
          // Se veio rápido (<5s), provavelmente veio do cache KV
          setCacheStatus('from-cache');
          console.log(`[MetadataFieldsContext] ✅ Campos carregados do CACHE em ${duration}s`);
        } else {
          // Se demorou mais, provavelmente extraiu via SSH
          setCacheStatus('from-ssh');
          console.log(
            `[MetadataFieldsContext] ✅ Campos extraídos via SSH em ${duration}s`
          );
        }

        // Após primeira carga, não é mais cold start
        if (isInitialLoad) {
          setIsInitialLoad(false);
        }
      }
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : 'Erro desconhecido';
      setError(errorMessage);
      setCacheStatus('error');
      console.error('[MetadataFieldsContext] ❌ Erro ao carregar campos:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadFields();
  }, []);

  return (
    <MetadataFieldsContext.Provider
      value={{
        fields,
        loading,
        error,
        reload: loadFields,
        cacheStatus,
        lastUpdate,
        isInitialLoad,
      }}
    >
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
