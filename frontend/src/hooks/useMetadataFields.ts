/**
 * Hook para buscar campos metadata dinâmicos
 *
 * Sistema Totalmente Dinâmico - Campos carregados do metadata_fields.json
 *
 * Uso:
 *   const { fields, loading, error } = useMetadataFields('blackbox');
 *   const tableFields = fields.filter(f => f.show_in_table);
 *   const formFields = fields.filter(f => f.show_in_form);
 */

import { useState, useEffect } from 'react';
import { metadataDynamicAPI, type MetadataFieldDynamic } from '../services/api';

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

      const { data } = await metadataDynamicAPI.getFields(filters);

      if (data.success) {
        setFields(data.fields);
      } else {
        setError('Erro ao carregar campos');
      }
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
        const { data } = await metadataDynamicAPI.getRequiredFields();

        if (data.success) {
          setRequiredFields(data.required_fields);
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
 */
export function useTableFields(context?: string): {
  tableFields: MetadataFieldDynamic[];
  loading: boolean;
  error: string | null;
} {
  const { fields, loading, error } = useMetadataFields({
    context: context as 'blackbox' | 'exporters' | 'services',
    enabled: true,
    show_in_table: true,
  });

  // Ordenar por order
  const tableFields = [...fields].sort((a, b) => a.order - b.order);

  return { tableFields, loading, error };
}

/**
 * Hook para buscar campos para formulário
 */
export function useFormFields(context?: string): {
  formFields: MetadataFieldDynamic[];
  loading: boolean;
  error: string | null;
} {
  const { fields, loading, error } = useMetadataFields({
    context: context as 'blackbox' | 'exporters' | 'services',
    enabled: true,
    show_in_form: true,
  });

  // Ordenar por order
  const formFields = [...fields].sort((a, b) => a.order - b.order);

  return { formFields, loading, error };
}

/**
 * Hook para buscar campos para filtros
 */
export function useFilterFields(context?: string): {
  filterFields: MetadataFieldDynamic[];
  loading: boolean;
  error: string | null;
} {
  const { fields, loading, error } = useMetadataFields({
    context: context as 'blackbox' | 'exporters' | 'services',
    enabled: true,
    show_in_filter: true,
  });

  // Ordenar por order
  const filterFields = [...fields].sort((a, b) => a.order - b.order);

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
