/**
 * Hook para gerenciar Reference Values (Sistema de Auto-Cadastro/Retroalimentação)
 *
 * OBJETIVO:
 * - Carregar valores existentes de um campo metadata (empresa, localização, etc)
 * - Auto-cadastrar valores novos quando usuário digita no formulário
 * - Normalizar valores (Title Case)
 *
 * USO:
 * ```typescript
 * const {
 *   values,          // Lista de valores existentes ["Empresa Ramada", "Acme Corp"]
 *   loading,         // Estado de carregamento
 *   ensureValue,     // Função para auto-cadastro
 *   refreshValues    // Recarregar lista
 * } = useReferenceValues('company');
 * ```
 *
 * EXEMPLO DE FLUXO:
 * 1. Usuário digita "empresa ramada" em campo Empresa
 * 2. Ao salvar formulário, chama ensureValue('company', 'empresa ramada')
 * 3. Backend normaliza para "Empresa Ramada" e cadastra automaticamente
 * 4. Próximo cadastro: "Empresa Ramada" aparece como opção no select
 */

import { useState, useEffect, useCallback } from 'react';
import axios from 'axios';

const API_URL = import.meta.env?.VITE_API_URL ?? 'http://localhost:5000/api/v1';

// ============================================================================
// CACHE GLOBAL PARA REFERENCE VALUES
// ============================================================================
// Evita que múltiplos componentes ReferenceValueInput façam requisições duplicadas
// para o mesmo campo (exemplo: 5 formulários com campo "company" fazem 5 requests)
//
// ESTRUTURA DO CACHE:
// {
//   "company": { values: [...], timestamp: 1234567890, loading: false },
//   "localizacao": { values: [...], timestamp: 1234567890, loading: false }
// }
//
// TTL: 5 minutos (dados raramente mudam durante uma sessão de edição)
// ============================================================================

interface CacheEntry {
  values: ReferenceValue[];
  timestamp: number;
  loading: boolean;
}

const globalCache: Record<string, CacheEntry> = {};
const CACHE_TTL = 5 * 60 * 1000; // 5 minutos

/**
 * Verifica se cache está válido (não expirou)
 */
function isCacheValid(fieldName: string): boolean {
  const entry = globalCache[fieldName];
  if (!entry) return false;

  const age = Date.now() - entry.timestamp;
  return age < CACHE_TTL;
}

/**
 * Retorna valores do cache se disponível e válido
 */
function getCachedValues(fieldName: string): ReferenceValue[] | null {
  if (!isCacheValid(fieldName)) {
    delete globalCache[fieldName]; // Limpar cache expirado
    return null;
  }

  return globalCache[fieldName]?.values || null;
}

/**
 * Salva valores no cache global
 */
function setCacheValues(fieldName: string, values: ReferenceValue[]): void {
  globalCache[fieldName] = {
    values,
    timestamp: Date.now(),
    loading: false
  };
}

/**
 * Marca campo como "carregando" para evitar requisições duplicadas simultâneas
 */
function markLoading(fieldName: string, loading: boolean): void {
  if (!globalCache[fieldName]) {
    globalCache[fieldName] = {
      values: [],
      timestamp: 0,
      loading
    };
  } else {
    globalCache[fieldName].loading = loading;
  }
}

/**
 * Verifica se campo já está sendo carregado por outro componente
 */
function isLoading(fieldName: string): boolean {
  return globalCache[fieldName]?.loading ?? false;
}

export interface ReferenceValue {
  value: string;
  created_at: string;
  created_by: string;
  usage_count?: number;
  last_used_at?: string;
  metadata?: Record<string, any>;
}

export interface EnsureValueResult {
  success: boolean;
  created: boolean;
  value: string;  // Valor normalizado
  message: string;
}

export interface UseReferenceValuesOptions {
  /** Nome do campo (company, localizacao, cidade, etc) */
  fieldName: string;

  /** Se True, carrega valores automaticamente ao montar componente */
  autoLoad?: boolean;

  /** Se True, inclui estatísticas de uso (usage_count, last_used_at) */
  includeStats?: boolean;
}

export interface UseReferenceValuesReturn {
  /** Lista de valores existentes */
  values: string[];

  /** Lista completa com metadata (se includeStats=true) */
  valuesWithMetadata: ReferenceValue[];

  /** Estado de carregamento */
  loading: boolean;

  /** Erro se houver */
  error: string | null;

  /** Garante que valor existe (auto-cadastro se necessário) */
  ensureValue: (value: string, metadata?: Record<string, any>) => Promise<EnsureValueResult>;

  /** Cria valor manualmente (cadastro direto via página admin) */
  createValue: (value: string, metadata?: Record<string, any>) => Promise<boolean>;

  /** Deleta valor (bloqueia se em uso) */
  deleteValue: (value: string, force?: boolean) => Promise<boolean>;

  /** Recarrega lista de valores */
  refreshValues: () => Promise<void>;
}

/**
 * Hook para gerenciar Reference Values de um campo metadata específico
 */
export function useReferenceValues(
  options: UseReferenceValuesOptions
): UseReferenceValuesReturn {
  const { fieldName, autoLoad = true, includeStats = false } = options;

  const [values, setValues] = useState<string[]>([]);
  const [valuesWithMetadata, setValuesWithMetadata] = useState<ReferenceValue[]>([]);
  const [loading, setLoading] = useState(autoLoad);
  const [error, setError] = useState<string | null>(null);

  /**
   * Limpa estado quando o campo muda (evita exibir valores do campo anterior)
   */
  useEffect(() => {
    setValues([]);
    setValuesWithMetadata([]);
    setError(null);
  }, [fieldName]);

  /**
   * Carrega lista de valores existentes do backend (COM CACHE GLOBAL)
   *
   * OTIMIZAÇÃO:
   * - Verifica cache global primeiro (evita requisições duplicadas)
   * - Se outro componente já está carregando, aguarda
   * - Cache válido por 5 minutos (dados raramente mudam durante sessão)
   */
  const loadValues = useCallback(async () => {
    if (!fieldName) {
      return;
    }

    try {
      setLoading(true);
      setError(null);

      // PASSO 1: Verificar se valores já estão em cache válido
      const cached = getCachedValues(fieldName);
      if (cached) {
        console.log(`[useReferenceValues] Cache HIT para ${fieldName} (${cached.length} valores)`);

        // Extrair apenas os valores (strings)
        const valueStrings = cached.map((v: ReferenceValue) => v.value);
        setValues(valueStrings);
        setValuesWithMetadata(cached);
        setLoading(false);
        return; // Usar cache, não fazer requisição HTTP
      }

      // PASSO 2: Se outro componente já está carregando este campo, aguardar
      if (isLoading(fieldName)) {
        console.log(`[useReferenceValues] Aguardando carregamento em andamento para ${fieldName}...`);

        // Aguardar 100ms e tentar novamente
        await new Promise(resolve => setTimeout(resolve, 100));

        // Verificar cache novamente (outro componente já carregou?)
        const cachedAfterWait = getCachedValues(fieldName);
        if (cachedAfterWait) {
          const valueStrings = cachedAfterWait.map((v: ReferenceValue) => v.value);
          setValues(valueStrings);
          setValuesWithMetadata(cachedAfterWait);
          setLoading(false);
          return;
        }
      }

      // PASSO 3: Marcar como "carregando" para evitar requisições duplicadas simultâneas
      markLoading(fieldName, true);

      console.log(`[useReferenceValues] Cache MISS para ${fieldName} - fazendo requisição HTTP`);

      const response = await axios.get(
        `${API_URL}/reference-values/${fieldName}`,
        {
          params: { include_stats: includeStats },
          timeout: 10000
        }
      );

      if (response.data.success) {
        const loadedValues = response.data.values || [];

        // Extrair apenas os valores (strings)
        const valueStrings = loadedValues.map((v: ReferenceValue) => v.value);
        setValues(valueStrings);

        // Guardar valores completos com metadata
        setValuesWithMetadata(loadedValues);

        // PASSO 4: Salvar no cache global para outros componentes reutilizarem
        setCacheValues(fieldName, loadedValues);
        console.log(`[useReferenceValues] Cache SAVED para ${fieldName} (${loadedValues.length} valores)`);
      }
    } catch (err: any) {
      const errorMsg = err.response?.data?.detail || err.message || 'Erro ao carregar valores';
      setError(errorMsg);
      console.error(`Erro ao carregar reference values para ${fieldName}:`, err);

      // Desmarcar loading em caso de erro
      markLoading(fieldName, false);
    } finally {
      setLoading(false);
      markLoading(fieldName, false);
    }
  }, [fieldName, includeStats]);

  /**
   * Garante que valor existe (auto-cadastro)
   *
   * CRÍTICO: Esta função é chamada automaticamente ao salvar formulários!
   */
  const ensureValue = useCallback(
    async (value: string, metadata?: Record<string, any>): Promise<EnsureValueResult> => {
      if (!value || !fieldName) {
        return {
          success: false,
          created: false,
          value: value || '',
          message: 'Valor ou campo vazio'
        };
      }

      try {
        const response = await axios.post(
          `${API_URL}/reference-values/ensure`,
          {
            field_name: fieldName,
            value,
            metadata
          },
          { timeout: 10000 }
        );

        if (response.data.success) {
          // Se foi criado, invalidar cache e recarregar lista
          if (response.data.created) {
            delete globalCache[fieldName]; // Invalidar cache
            await loadValues();
          }

          return {
            success: true,
            created: response.data.created,
            value: response.data.value,  // Valor normalizado
            message: response.data.message
          };
        }

        return {
          success: false,
          created: false,
          value,
          message: 'Falha ao garantir valor'
        };
      } catch (err: any) {
        const errorMsg = err.response?.data?.detail || err.message;
        console.error(`Erro ao garantir valor ${value} para ${fieldName}:`, err);

        return {
          success: false,
          created: false,
          value,
          message: errorMsg
        };
      }
    },
    [fieldName, loadValues]
  );

  /**
   * Cria valor manualmente (cadastro via página de administração)
   */
  const createValue = useCallback(
    async (value: string, metadata?: Record<string, any>): Promise<boolean> => {
      if (!value || !fieldName) {
        return false;
      }

      try {
        const response = await axios.post(
          `${API_URL}/reference-values/`,
          {
            field_name: fieldName,
            value,
            metadata
          },
          { timeout: 10000 }
        );

        if (response.data.success) {
          // Invalidar cache e recarregar lista
          delete globalCache[fieldName];
          await loadValues();
          return true;
        }

        return false;
      } catch (err: any) {
        console.error(`Erro ao criar valor ${value} para ${fieldName}:`, err);
        return false;
      }
    },
    [fieldName, loadValues]
  );

  /**
   * Deleta valor
   *
   * PROTEÇÃO: Bloqueia se valor em uso (a menos que force=true)
   */
  const deleteValue = useCallback(
    async (value: string, force = false): Promise<boolean> => {
      if (!value || !fieldName) {
        return false;
      }

      try {
        await axios.delete(
          `${API_URL}/reference-values/${fieldName}/${encodeURIComponent(value)}`,
          {
            params: { force },
            timeout: 10000
          }
        );

        // Invalidar cache e recarregar lista
        delete globalCache[fieldName];
        await loadValues();
        return true;
      } catch (err: any) {
        console.error(`Erro ao deletar valor ${value} de ${fieldName}:`, err);
        throw new Error(err.response?.data?.detail || 'Erro ao deletar valor');
      }
    },
    [fieldName, loadValues]
  );

  /**
   * Auto-load ao montar componente
   */
  useEffect(() => {
    if (autoLoad) {
      loadValues();
    }
  }, [fieldName, autoLoad, loadValues]);

  return {
    values,
    valuesWithMetadata,
    loading,
    error,
    ensureValue,
    createValue,
    deleteValue,
    refreshValues: loadValues
  };
}

/**
 * Hook para carregar lista de todos os campos que suportam reference values
 */
export function useSupportedFields() {
  const [fields, setFields] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const loadFields = async () => {
      try {
        const response = await axios.get(`${API_URL}/reference-values/`, {
          timeout: 10000
        });

        if (response.data.success) {
          setFields(response.data.fields || []);
        }
      } catch (err) {
        console.error('Erro ao carregar campos suportados:', err);
      } finally {
        setLoading(false);
      }
    };

    loadFields();
  }, []);

  return { fields, loading };
}

/**
 * Hook para batch ensure (garantir múltiplos valores de uma vez)
 *
 * Útil para processar formulários com múltiplos campos metadata.
 */
export function useBatchEnsure() {
  const batchEnsure = useCallback(
    async (values: Array<{ fieldName: string; value: string; metadata?: Record<string, any> }>) => {
      try {
        const response = await axios.post(
          `${API_URL}/reference-values/batch-ensure`,
          values.map(v => ({
            field_name: v.fieldName,
            value: v.value,
            metadata: v.metadata
          })),
          { timeout: 15000 }
        );

        return response.data;
      } catch (err: any) {
        console.error('Erro ao fazer batch ensure:', err);
        throw err;
      }
    },
    []
  );

  return { batchEnsure };
}
