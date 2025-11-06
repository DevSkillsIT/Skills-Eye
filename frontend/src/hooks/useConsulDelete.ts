/**
 * Hook compartilhado para DELETE de serviços/recursos no Consul
 *
 * IMPORTANTE: Usa APENAS dados do record - ZERO valores hardcoded
 *
 * Lógica baseada no DELETE do BlackboxTargets (testado e funcionando)
 */

import { message } from 'antd';

export interface ConsulDeletePayload {
  service_id: string;           // ID único (obrigatório)
  service_name?: string;        // Nome do serviço no Consul (para Método 2 fallback)
  node_addr?: string;           // IP do agente (para Método 1)
  node_name?: string;           // Nome do node (para Método 2 fallback)
  datacenter?: string;          // Datacenter (para Método 2 fallback)
}

export interface ConsulDeleteOptions {
  /**
   * Função da API que faz o DELETE
   */
  deleteFn: (payload: ConsulDeletePayload) => Promise<any>;

  /**
   * Função opcional para limpar cache após deletar
   */
  clearCacheFn?: (key: string) => Promise<any>;

  /**
   * Chave do cache a ser limpa
   */
  cacheKey?: string;

  /**
   * Mensagem de sucesso customizada
   */
  successMessage?: string;

  /**
   * Mensagem de erro customizada
   */
  errorMessage?: string;

  /**
   * Callback após sucesso
   */
  onSuccess?: () => void;

  /**
   * Callback após erro
   */
  onError?: (error: any) => void;
}

/**
 * Hook que retorna função de DELETE reutilizável
 *
 * @example
 * ```tsx
 * const { deleteResource } = useConsulDelete({
 *   deleteFn: consulAPI.deleteBlackboxTarget,
 *   clearCacheFn: consulAPI.clearCache,
 *   cacheKey: 'blackbox-targets',
 *   successMessage: 'Alvo removido com sucesso',
 *   onSuccess: () => actionRef.current?.reload(),
 * });
 *
 * // Usar no handleDelete
 * await deleteResource({
 *   service_id: record.service_id,
 *   service_name: record.service,
 *   node_addr: record.node_addr,
 *   node_name: record.node,
 *   datacenter: record.meta?.datacenter,
 * });
 * ```
 */
export function useConsulDelete(options: ConsulDeleteOptions) {
  const {
    deleteFn,
    clearCacheFn,
    cacheKey,
    successMessage = 'Recurso removido com sucesso',
    errorMessage = 'Falha ao remover recurso',
    onSuccess,
    onError,
  } = options;

  /**
   * Função de DELETE compartilhada
   * Usa APENAS dados do payload - ZERO valores hardcoded
   */
  const deleteResource = async (payload: ConsulDeletePayload): Promise<boolean> => {
    try {
      console.log('[useConsulDelete] Payload enviado:', payload);

      // Chamar a função de DELETE da API
      await deleteFn(payload);

      // Limpar cache se configurado
      if (clearCacheFn && cacheKey) {
        await clearCacheFn(cacheKey);
      }

      message.success(successMessage);

      // Callback de sucesso
      if (onSuccess) {
        onSuccess();
      }

      return true;
    } catch (error: any) {
      const detail =
        error?.response?.data?.detail ||
        error?.response?.data?.error ||
        error?.message ||
        'Erro desconhecido';

      message.error(`${errorMessage}: ${detail}`);
      console.error('[useConsulDelete] Erro:', error);

      // Callback de erro
      if (onError) {
        onError(error);
      }

      return false;
    }
  };

  /**
   * DELETE em lote (batch)
   */
  const deleteBatch = async (payloads: ConsulDeletePayload[]): Promise<boolean> => {
    try {
      console.log('[useConsulDelete] Batch delete:', payloads.length, 'itens');

      await Promise.all(payloads.map((payload) => deleteFn(payload)));

      // Limpar cache se configurado
      if (clearCacheFn && cacheKey) {
        await clearCacheFn(cacheKey);
      }

      message.success(`${payloads.length} recursos removidos com sucesso`);

      // Callback de sucesso
      if (onSuccess) {
        onSuccess();
      }

      return true;
    } catch (error: any) {
      const detail =
        error?.response?.data?.detail ||
        error?.response?.data?.error ||
        error?.message ||
        'Erro desconhecido';

      message.error(`Falha ao remover um ou mais recursos: ${detail}`);
      console.error('[useConsulDelete] Erro no batch:', error);

      // Callback de erro
      if (onError) {
        onError(error);
      }

      return false;
    }
  };

  return {
    deleteResource,
    deleteBatch,
  };
}
