/**
 * Hook para consumir campos metadata dinâmicos do Prometheus
 *
 * Busca automaticamente os campos configurados no prometheus.yml
 * e permite que formulários sejam gerados dinamicamente
 */

import { useState, useEffect } from 'react';
import axios from 'axios';

const API_URL = import.meta.env?.VITE_API_URL ?? 'http://localhost:5000/api/v1';

export interface MetadataField {
  name: string;
  display_name: string;
  source_label: string;
  field_type: 'string' | 'number' | 'boolean' | 'select';
  required: boolean;
  show_in_table: boolean;
  show_in_dashboard: boolean;
  options?: string[] | null;
  regex?: string | null;
  replacement?: string | null;
}

interface FieldsResponse {
  success: boolean;
  fields: MetadataField[];
  total: number;
  last_updated: string;
}

interface UsePrometheusFieldsReturn {
  fields: MetadataField[];
  loading: boolean;
  error: string | null;
  total: number;
  lastUpdated: string | null;
  reload: () => Promise<void>;

  // Helpers
  getFieldByName: (name: string) => MetadataField | undefined;
  getRequiredFields: () => MetadataField[];
  getTableFields: () => MetadataField[];
  getDashboardFields: () => MetadataField[];
}

/**
 * Hook para buscar e gerenciar campos metadata do Prometheus
 */
export function usePrometheusFields(): UsePrometheusFieldsReturn {
  const [fields, setFields] = useState<MetadataField[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [total, setTotal] = useState<number>(0);
  const [lastUpdated, setLastUpdated] = useState<string | null>(null);

  const fetchFields = async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await axios.get<FieldsResponse>(`${API_URL}/prometheus-config/fields`, {
        timeout: 30000, // 30 segundos (pode precisar consultar múltiplos servidores)
      });

      if (response.data.success) {
        setFields(response.data.fields);
        setTotal(response.data.total);
        setLastUpdated(response.data.last_updated);
      } else {
        setError('Falha ao carregar campos');
      }
    } catch (err: any) {
      console.error('Erro ao buscar campos do Prometheus:', err);

      // Melhor mensagem de erro
      if (err.code === 'ECONNABORTED') {
        setError('Tempo esgotado ao carregar campos (servidor lento)');
      } else {
        setError(err.response?.data?.message || 'Erro ao carregar campos metadata');
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchFields();
  }, []);

  // Buscar campo por nome
  const getFieldByName = (name: string): MetadataField | undefined => {
    return fields.find(f => f.name === name);
  };

  // Obter apenas campos obrigatórios
  const getRequiredFields = (): MetadataField[] => {
    return fields.filter(f => f.required);
  };

  // Obter campos visíveis na tabela
  const getTableFields = (): MetadataField[] => {
    return fields.filter(f => f.show_in_table);
  };

  // Obter campos visíveis no dashboard
  const getDashboardFields = (): MetadataField[] => {
    return fields.filter(f => f.show_in_dashboard);
  };

  return {
    fields,
    loading,
    error,
    total,
    lastUpdated,
    reload: fetchFields,
    getFieldByName,
    getRequiredFields,
    getTableFields,
    getDashboardFields,
  };
}

/**
 * Hook simplificado para apenas obter os nomes dos campos
 */
export function usePrometheusFieldNames(): string[] {
  const { fields } = usePrometheusFields();
  return fields.map(f => f.name);
}

/**
 * Hook para obter campos como options para Select
 */
export function usePrometheusFieldOptions(): Array<{ value: string; label: string }> {
  const { fields } = usePrometheusFields();
  return fields.map(f => ({
    value: f.name,
    label: f.display_name,
  }));
}
