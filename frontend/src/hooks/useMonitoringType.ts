/**
 * Hook para carregar monitoring types configuration-driven
 *
 * Busca schemas JSON do backend e retorna com cache
 */

import { useState, useEffect } from 'react';
import axios from 'axios';
import type {
  MonitoringCategory,
  MonitoringType,
  MonitoringCategoriesResponse,
  MonitoringTypeResponse,
} from '../types/monitoring';

interface UseMonitoringTypeOptions {
  /** ID da categoria (ex: 'network-probes', 'system-exporters') */
  category?: string;

  /** ID do tipo específico (ex: 'icmp', 'node'). Se fornecido, busca apenas este tipo. */
  typeId?: string;

  /** Se false, não carrega automaticamente (útil para lazy loading) */
  autoLoad?: boolean;
}

interface UseMonitoringTypeReturn {
  /** Schema carregado (MonitoringCategory ou MonitoringType) */
  schema: MonitoringCategory | MonitoringType | null;

  /** Estado de carregamento */
  loading: boolean;

  /** Erro (se houver) */
  error: string | null;

  /** Função para recarregar */
  reload: () => Promise<void>;
}

/**
 * Hook para carregar schema de monitoring type
 *
 * @example
 * // Carregar categoria completa
 * const { schema, loading } = useMonitoringType({ category: 'network-probes' });
 *
 * @example
 * // Carregar tipo específico
 * const { schema, loading } = useMonitoringType({
 *   category: 'network-probes',
 *   typeId: 'icmp'
 * });
 *
 * @example
 * // Carregar todas as categorias
 * const { schema, loading } = useMonitoringType();
 */
export function useMonitoringType(
  options: UseMonitoringTypeOptions = {}
): UseMonitoringTypeReturn {
  const { category, typeId, autoLoad = true } = options;

  const [schema, setSchema] = useState<MonitoringCategory | MonitoringType | null>(null);
  const [loading, setLoading] = useState(autoLoad);
  const [error, setError] = useState<string | null>(null);

  const loadSchema = async () => {
    try {
      setLoading(true);
      setError(null);

      let endpoint = '/api/v1/monitoring-types';

      if (category && typeId) {
        // Buscar tipo específico
        endpoint = `/api/v1/monitoring-types/${category}/${typeId}`;
      } else if (category) {
        // Buscar categoria completa
        endpoint = `/api/v1/monitoring-types/${category}`;
      }
      // Senão, busca todas as categorias (endpoint padrão)

      const response = await axios.get<MonitoringTypeResponse | MonitoringCategoriesResponse>(
        endpoint
      );

      if ('data' in response.data) {
        // MonitoringTypeResponse (categoria ou tipo específico)
        setSchema(response.data.data);
      } else if ('categories' in response.data) {
        // MonitoringCategoriesResponse (todas as categorias)
        // Retornar primeira categoria por padrão (ou null)
        const cats = response.data.categories;
        setSchema(cats.length > 0 ? cats[0] : null);
      }
    } catch (err: any) {
      const errorMessage =
        err.response?.data?.error || err.response?.data?.detail || err.message || 'Erro desconhecido';
      setError(errorMessage);
      console.error('[useMonitoringType] Erro ao carregar schema:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (autoLoad) {
      loadSchema();
    }
  }, [category, typeId, autoLoad]);

  return {
    schema,
    loading,
    error,
    reload: loadSchema,
  };
}

/**
 * Hook para carregar TODAS as categorias
 *
 * @example
 * const { categories, loading } = useAllMonitoringTypes();
 */
export function useAllMonitoringTypes() {
  const [categories, setCategories] = useState<MonitoringCategory[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadCategories = async () => {
    try {
      setLoading(true);
      setError(null);

      const response = await axios.get<MonitoringCategoriesResponse>('/api/v1/monitoring-types');

      if (response.data.success) {
        setCategories(response.data.categories);
      } else {
        throw new Error('Falha ao carregar categorias');
      }
    } catch (err: any) {
      const errorMessage = err.message || 'Erro desconhecido';
      setError(errorMessage);
      console.error('[useAllMonitoringTypes] Erro:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadCategories();
  }, []);

  return {
    categories,
    loading,
    error,
    reload: loadCategories,
  };
}
