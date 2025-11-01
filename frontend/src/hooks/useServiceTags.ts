/**
 * Hook para gerenciar Service Tags (Sistema de Auto-Cadastro para Tags)
 *
 * OBJETIVO:
 * - Carregar tags únicas de todos os serviços Consul
 * - Auto-cadastrar tags novas quando usuário adiciona no formulário
 * - Normalizar tags (Title Case)
 *
 * USO:
 * ```typescript
 * const {
 *   tags,            // Lista de tags existentes ["linux", "monitoring", "production"]
 *   loading,         // Estado de carregamento
 *   ensureTag,       // Função para auto-cadastro de tag
 *   refreshTags      // Recarregar lista
 * } = useServiceTags();
 * ```
 *
 * EXEMPLO DE FLUXO:
 * 1. Usuário digita "DATABASE" em campo Tags
 * 2. Ao salvar formulário, chama ensureTag('DATABASE')
 * 3. Backend normaliza para "Database" e cadastra automaticamente
 * 4. Próximo cadastro: "Database" aparece como opção no select
 */

import { useState, useEffect, useCallback } from 'react';
import axios from 'axios';

const API_URL = import.meta.env?.VITE_API_URL ?? 'http://localhost:5000/api/v1';

export interface TagValue {
  value: string;
  created_at: string;
  created_by: string;
  usage_count?: number;
  last_used_at?: string;
}

export interface EnsureTagResult {
  success: boolean;
  created: boolean;
  value: string;  // Tag normalizada
  message: string;
}

export interface UseServiceTagsOptions {
  /** Se True, carrega tags automaticamente ao montar componente */
  autoLoad?: boolean;

  /** Se True, inclui estatísticas de uso (usage_count, last_used_at) */
  includeStats?: boolean;
}

export interface UseServiceTagsReturn {
  /** Lista de tags existentes */
  tags: string[];

  /** Lista completa com metadata (se includeStats=true) */
  tagsWithMetadata: TagValue[];

  /** Estado de carregamento */
  loading: boolean;

  /** Erro se houver */
  error: string | null;

  /** Garante que tag existe (auto-cadastro se necessário) */
  ensureTag: (tag: string, metadata?: Record<string, any>) => Promise<EnsureTagResult>;

  /** Garante que múltiplas tags existem (batch) */
  ensureTags: (tags: string[], metadata?: Record<string, any>) => Promise<EnsureTagResult[]>;

  /** Cria tag manualmente */
  createTag: (tag: string, metadata?: Record<string, any>) => Promise<boolean>;

  /** Deleta tag (bloqueia se em uso) */
  deleteTag: (tag: string, force?: boolean) => Promise<boolean>;

  /** Recarrega lista de tags */
  refreshTags: () => Promise<void>;
}

/**
 * Hook para gerenciar Service Tags com auto-cadastro
 */
export function useServiceTags(
  options: UseServiceTagsOptions = {}
): UseServiceTagsReturn {
  const { autoLoad = true, includeStats = false } = options;

  const [tags, setTags] = useState<string[]>([]);
  const [tagsWithMetadata, setTagsWithMetadata] = useState<TagValue[]>([]);
  const [loading, setLoading] = useState(autoLoad);
  const [error, setError] = useState<string | null>(null);

  /**
   * Carrega lista de tags únicas de todos os serviços Consul
   */
  const loadTags = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      // ESTRATÉGIA DUPLA:
      // 1. Carregar tags únicas dos serviços Consul (fonte primária)
      const uniqueResponse = await axios.get(
        `${API_URL}/service-tags/unique`,
        { timeout: 10000 }
      );

      // 2. Carregar tags cadastradas no reference values (pode ter tags que ainda não estão em serviços)
      const referenceResponse = await axios.get(
        `${API_URL}/reference-values/service_tag`,
        {
          params: { include_stats: includeStats },
          timeout: 10000
        }
      );

      // Combinar ambas as fontes (união)
      const uniqueTags = new Set<string>();

      // Tags dos serviços
      if (uniqueResponse.data.success) {
        (uniqueResponse.data.tags || []).forEach((tag: string) => uniqueTags.add(tag));
      }

      // Tags cadastradas
      if (referenceResponse.data.success) {
        const referenceValues = referenceResponse.data.values || [];
        referenceValues.forEach((v: TagValue) => uniqueTags.add(v.value));
        setTagsWithMetadata(referenceValues);
      }

      // Ordenar alfabeticamente
      const sortedTags = Array.from(uniqueTags).sort();
      setTags(sortedTags);

    } catch (err: any) {
      const errorMsg = err.response?.data?.detail || err.message || 'Erro ao carregar tags';
      setError(errorMsg);
      console.error('Erro ao carregar service tags:', err);
    } finally {
      setLoading(false);
    }
  }, [includeStats]);

  /**
   * Garante que uma tag existe (auto-cadastro)
   *
   * CRÍTICO: Esta função é chamada automaticamente ao salvar formulários!
   */
  const ensureTag = useCallback(
    async (tag: string, metadata?: Record<string, any>): Promise<EnsureTagResult> => {
      if (!tag) {
        return {
          success: false,
          created: false,
          value: tag || '',
          message: 'Tag vazia'
        };
      }

      try {
        const response = await axios.post(
          `${API_URL}/service-tags/ensure`,
          { tag, metadata },
          { timeout: 10000 }
        );

        if (response.data.success) {
          // Se foi criado, recarregar lista
          if (response.data.created) {
            await loadTags();
          }

          return {
            success: true,
            created: response.data.created,
            value: response.data.value,  // Tag normalizada
            message: response.data.message
          };
        }

        return {
          success: false,
          created: false,
          value: tag,
          message: 'Falha ao garantir tag'
        };
      } catch (err: any) {
        const errorMsg = err.response?.data?.detail || err.message;
        console.error(`Erro ao garantir tag ${tag}:`, err);

        return {
          success: false,
          created: false,
          value: tag,
          message: errorMsg
        };
      }
    },
    [loadTags]
  );

  /**
   * Garante que múltiplas tags existem (batch)
   *
   * Útil ao processar array de tags de um formulário
   */
  const ensureTags = useCallback(
    async (tagsList: string[], metadata?: Record<string, any>): Promise<EnsureTagResult[]> => {
      if (!tagsList || tagsList.length === 0) {
        return [];
      }

      try {
        const response = await axios.post(
          `${API_URL}/service-tags/batch-ensure`,
          {
            tags: tagsList,
            metadata
          },
          { timeout: 15000 }
        );

        if (response.data.success) {
          const results = response.data.results || [];

          // Se alguma tag foi criada, recarregar lista
          const anyCreated = results.some((r: EnsureTagResult) => r.created);
          if (anyCreated) {
            await loadTags();
          }

          return results;
        }

        return [];
      } catch (err: any) {
        console.error('Erro ao fazer batch ensure de tags:', err);
        return [];
      }
    },
    [loadTags]
  );

  /**
   * Cria tag manualmente (cadastro via página de administração)
   */
  const createTag = useCallback(
    async (tag: string, metadata?: Record<string, any>): Promise<boolean> => {
      if (!tag) {
        return false;
      }

      try {
        const response = await axios.post(
          `${API_URL}/reference-values/`,
          {
            field_name: 'service_tag',
            value: tag,
            metadata
          },
          { timeout: 10000 }
        );

        if (response.data.success) {
          await loadTags();
          return true;
        }

        return false;
      } catch (err: any) {
        console.error(`Erro ao criar tag ${tag}:`, err);
        return false;
      }
    },
    [loadTags]
  );

  /**
   * Deleta tag
   *
   * PROTEÇÃO: Bloqueia se tag em uso (a menos que force=true)
   */
  const deleteTag = useCallback(
    async (tag: string, force = false): Promise<boolean> => {
      if (!tag) {
        return false;
      }

      try {
        await axios.delete(
          `${API_URL}/reference-values/service_tag/${encodeURIComponent(tag)}`,
          {
            params: { force },
            timeout: 10000
          }
        );

        await loadTags();
        return true;
      } catch (err: any) {
        console.error(`Erro ao deletar tag ${tag}:`, err);
        throw new Error(err.response?.data?.detail || 'Erro ao deletar tag');
      }
    },
    [loadTags]
  );

  /**
   * Auto-load ao montar componente
   */
  useEffect(() => {
    if (autoLoad) {
      loadTags();
    }
  }, [autoLoad, loadTags]);

  return {
    tags,
    tagsWithMetadata,
    loading,
    error,
    ensureTag,
    ensureTags,
    createTag,
    deleteTag,
    refreshTags: loadTags
  };
}
