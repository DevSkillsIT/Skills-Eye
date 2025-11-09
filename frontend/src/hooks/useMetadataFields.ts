/**
 * Hook para buscar campos metadata dinâmicos
 *
 * Sistema Totalmente Dinâmico - Campos extraídos do Prometheus
 *
 * Uso:
 *   const { fields, loading, error } = useMetadataFields('blackbox');
 *   const tableFields = fields.filter(f => f.show_in_table);
 *   const formFields = fields.filter(f => f.show_in_form);
 *
 * IMPORTANTE: Agora busca 100% do Prometheus (via SSH) + configurações do KV
 */

import { useState, useEffect } from 'react';
import axios from 'axios';
import type { MetadataFieldDynamic } from '../services/api';
import { useMetadataFieldsContext } from '../contexts/MetadataFieldsContext';

const API_URL = import.meta.env?.VITE_API_URL ?? 'http://localhost:5000/api/v1';

// Re-exportar o tipo para facilitar importações
export type { MetadataFieldDynamic } from '../services/api';

export interface UseMetadataFieldsOptions {
  context?: 'blackbox' | 'exporters' | 'services' | 'general';
  enabled?: boolean;
  required?: boolean;
  show_in_table?: boolean;
  show_in_form?: boolean;
  show_in_filter?: boolean;
  category?: string;
  autoLoad?: boolean; // Se false, não carrega automaticamente
}

export interface UseMetadataFieldsReturn {
  fields: MetadataFieldDynamic[];
  loading: boolean;
  error: string | null;
  reload: () => Promise<void>;
}

/**
 * Hook principal para buscar campos metadata
 */
export function useMetadataFields(
  options: UseMetadataFieldsOptions = {}
): UseMetadataFieldsReturn {
  const { autoLoad = true, ...filters } = options;

  const [fields, setFields] = useState<MetadataFieldDynamic[]>([]);
  const [loading, setLoading] = useState(autoLoad);
  const [error, setError] = useState<string | null>(null);

  const loadFields = async () => {
    try {
      setLoading(true);
      setError(null);

      // USAR ENDPOINT OTIMIZADO QUE JÁ FAZ MERGE NO BACKEND
      // Evita fazer 56+ requisições HTTP paralelas (um por campo)
      // Timeout de 60s pois faz SSH para múltiplos servidores no cold start
      const response = await axios.get(`${API_URL}/metadata-fields/`, {
        timeout: 60000,
      });

      if (!response.data.success) {
        throw new Error('Erro ao carregar campos metadata');
      }

      const fieldsWithConfig: MetadataFieldDynamic[] = response.data.fields.map((field: any) => ({
        ...field,
        // Garantir defaults para campos que podem estar ausentes
        show_in_services: field.show_in_services ?? true,
        show_in_exporters: field.show_in_exporters ?? true,
        show_in_blackbox: field.show_in_blackbox ?? true,
      }));

      console.log(`[useMetadataFields] ✅ ${fieldsWithConfig.length} campos carregados (1 requisição otimizada)`);

      // PASSO 3: Filtrar por contexto (services, exporters, blackbox)
      let filteredFields = fieldsWithConfig;

      if (filters.context === 'services') {
        filteredFields = fieldsWithConfig.filter(f => f.show_in_services !== false);
      } else if (filters.context === 'exporters') {
        filteredFields = fieldsWithConfig.filter(f => f.show_in_exporters !== false);
      } else if (filters.context === 'blackbox') {
        filteredFields = fieldsWithConfig.filter(f => f.show_in_blackbox !== false);
      }

      // PASSO 4: Aplicar outros filtros (enabled, show_in_table, etc)
      if (filters.enabled !== undefined) {
        filteredFields = filteredFields.filter(f => f.enabled === filters.enabled);
      }

      if (filters.required !== undefined) {
        filteredFields = filteredFields.filter(f => f.required === filters.required);
      }

      if (filters.show_in_table !== undefined) {
        filteredFields = filteredFields.filter(f => f.show_in_table === filters.show_in_table);
      }

      if (filters.show_in_form !== undefined) {
        filteredFields = filteredFields.filter(f => f.show_in_form === filters.show_in_form);
      }

      if (filters.show_in_filter !== undefined) {
        filteredFields = filteredFields.filter(
          f => f.show_in_filter === filters.show_in_filter
        );
      }

      if (filters.category) {
        filteredFields = filteredFields.filter(f => f.category === filters.category);
      }

      setFields(filteredFields);
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : 'Erro desconhecido';
      setError(errorMessage);
      console.error('[useMetadataFields] Erro ao carregar campos:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (autoLoad) {
      loadFields();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [
    options.context,
    options.enabled,
    options.required,
    options.show_in_table,
    options.show_in_form,
    options.show_in_filter,
    options.category,
    autoLoad,
  ]);

  return {
    fields,
    loading,
    error,
    reload: loadFields,
  };
}

/**
 * Hook para buscar apenas campos obrigatórios
 */
export function useRequiredFields(): {
  requiredFields: string[];
  loading: boolean;
  error: string | null;
} {
  const [requiredFields, setRequiredFields] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadRequiredFields() {
      try {
        setLoading(true);

        // Buscar campos do Prometheus (timeout 60s para cold start)
        const response = await axios.get(`${API_URL}/prometheus-config/fields`, {
          timeout: 60000,
        });

        if (response.data.success) {
          // Filtrar apenas campos obrigatórios
          const required = response.data.fields
            .filter((field: MetadataFieldDynamic) => field.required === true)
            .map((field: MetadataFieldDynamic) => field.name);

          setRequiredFields(required);
        }
      } catch (err: unknown) {
        const errorMessage = err instanceof Error ? err.message : 'Erro desconhecido';
        setError(errorMessage);
        console.error('[useRequiredFields] Erro:', err);
      } finally {
        setLoading(false);
      }
    }

    loadRequiredFields();
  }, []);

  return { requiredFields, loading, error };
}

/**
 * Hook para buscar campos para tabela (colunas)
 * OTIMIZADO: Usa context compartilhado - UMA única requisição
 */
export function useTableFields(context?: string): {
  tableFields: MetadataFieldDynamic[];
  loading: boolean;
  error: string | null;
} {
  const { fields: allFields, loading, error } = useMetadataFieldsContext();

  // Filtrar por contexto e show_in_table
  const tableFields = allFields
    .filter((f: MetadataFieldDynamic) => {
      // Filtrar por contexto
      if (context === 'services') return f.show_in_services !== false;
      if (context === 'exporters') return f.show_in_exporters !== false;
      if (context === 'blackbox') return f.show_in_blackbox !== false;
      return true;
    })
    .filter((f: MetadataFieldDynamic) => f.enabled === true && f.show_in_table === true)
    .sort((a: MetadataFieldDynamic, b: MetadataFieldDynamic) => a.order - b.order);

  return { tableFields, loading, error };
}

/**
 * Hook para buscar campos para formulário
 * OTIMIZADO: Usa context compartilhado - UMA única requisição
 */
export function useFormFields(context?: string): {
  formFields: MetadataFieldDynamic[];
  loading: boolean;
  error: string | null;
} {
  const { fields: allFields, loading, error } = useMetadataFieldsContext();

  const formFields = allFields
    .filter((f: MetadataFieldDynamic) => {
      if (context === 'services') return f.show_in_services !== false;
      if (context === 'exporters') return f.show_in_exporters !== false;
      if (context === 'blackbox') return f.show_in_blackbox !== false;
      return true;
    })
    .filter((f: MetadataFieldDynamic) => f.enabled === true && f.show_in_form === true)
    .sort((a: MetadataFieldDynamic, b: MetadataFieldDynamic) => a.order - b.order);

  return { formFields, loading, error };
}

/**
 * Hook para buscar campos para filtros
 * OTIMIZADO: Usa context compartilhado - UMA única requisição
 */
export function useFilterFields(context?: string): {
  filterFields: MetadataFieldDynamic[];
  loading: boolean;
  error: string | null;
} {
  const { fields: allFields, loading, error } = useMetadataFieldsContext();

  const filterFields = allFields
    .filter((f: MetadataFieldDynamic) => {
      if (context === 'services') return f.show_in_services !== false;
      if (context === 'exporters') return f.show_in_exporters !== false;
      if (context === 'blackbox') return f.show_in_blackbox !== false;
      return true;
    })
    .filter((f: MetadataFieldDynamic) => f.enabled === true && f.show_in_filter === true)
    .sort((a: MetadataFieldDynamic, b: MetadataFieldDynamic) => a.order - b.order);

  return { filterFields, loading, error };
}

/**
 * Helper: Gera colunas ProTable a partir de fields
 */
export function generateProTableColumns(fields: MetadataFieldDynamic[]) {
  return fields.map((field) => ({
    title: field.display_name,
    dataIndex: ['meta', field.name],
    key: field.name,
    width: field.field_type === 'string' ? 200 : 140,
    ellipsis: true,
    tooltip: field.description,
  }));
}

/**
 * Helper: Gera rules de validação para formulário
 */
export function generateFormRules(field: MetadataFieldDynamic) {
  const rules: Array<Record<string, unknown>> = [];

  if (field.required) {
    rules.push({
      required: true,
      message:
        field.validation?.required_message ||
        `Informe ${field.display_name.toLowerCase()}`,
    });
  }

  if (field.validation?.min_length) {
    rules.push({
      min: field.validation.min_length,
      message: `Mínimo ${field.validation.min_length} caracteres`,
    });
  }

  if (field.validation?.max_length) {
    rules.push({
      max: field.validation.max_length,
      message: `Máximo ${field.validation.max_length} caracteres`,
    });
  }

  if (field.validation?.regex) {
    rules.push({
      pattern: new RegExp(field.validation.regex as string),
      message: field.validation.pattern_message || 'Formato inválido',
    });
  }

  return rules;
}
