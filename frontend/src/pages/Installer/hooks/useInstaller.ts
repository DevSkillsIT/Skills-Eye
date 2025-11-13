/**
 * Hook for managing installation process
 * Handles installation lifecycle, status polling, and log accumulation
 */

import { useState, useRef, useCallback, useEffect } from 'react';
import { App } from 'antd';
import { consulAPI } from '../../../services/api';
import type { InstallLogEntry, InstallFormData, InstallationTask } from '../types';
import { POLL_INTERVAL_MS } from '../constants';

interface UseInstallerOptions {
  onSuccess?: (task: InstallationTask) => void;
  onError?: (error: string) => void;
}

export function useInstaller(options: UseInstallerOptions = {}) {
  const { onSuccess, onError } = options;
  const { message } = App.useApp();

  const [installationId, setInstallationId] = useState<string | null>(null);
  const [running, setRunning] = useState(false);
  const [success, setSuccess] = useState<boolean | null>(null);
  const [progress, setProgress] = useState(0);
  const [statusMessage, setStatusMessage] = useState('');
  const [logs, setLogs] = useState<InstallLogEntry[]>([]);
  const [task, setTask] = useState<InstallationTask | null>(null);

  const pollIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const pollingActiveRef = useRef(false);

  /**
   * Add log entry to accumulated logs
   */
  const addLog = useCallback((log: InstallLogEntry) => {
    setLogs((prev) => [...prev, log]);
  }, []);

  /**
   * Add local log (not from WebSocket)
   */
  const addLocalLog = useCallback((message: string, level: string = 'info') => {
    const log: InstallLogEntry = {
      key: `local-${Date.now()}-${Math.random()}`,
      message,
      source: 'local',
      level,
      timestamp: new Date().toISOString(),
    };
    addLog(log);
  }, [addLog]);

  /**
   * Clear all logs
   */
  const clearLogs = useCallback(() => {
    setLogs([]);
  }, []);

  /**
   * Poll installation status
   */
  const pollStatus = useCallback(async (id: string) => {
    if (!pollingActiveRef.current) return;

    try {
      const response = await consulAPI.getInstallationStatus(id);
      const taskData = response.data;

      setTask(taskData);
      setProgress(taskData.progress || 0);
      setStatusMessage(taskData.message || '');

      // Check if completed or failed
      if (taskData.status === 'completed') {
        setRunning(false);
        setSuccess(true);
        pollingActiveRef.current = false;

        if (pollIntervalRef.current) {
          clearInterval(pollIntervalRef.current);
          pollIntervalRef.current = null;
        }

        message.success('Instalação concluída com sucesso!');
        if (onSuccess) {
          onSuccess(taskData);
        }
      } else if (taskData.status === 'failed') {
        setRunning(false);
        setSuccess(false);
        pollingActiveRef.current = false;

        if (pollIntervalRef.current) {
          clearInterval(pollIntervalRef.current);
          pollIntervalRef.current = null;
        }

        const errorMsg = taskData.error || 'Falha na instalação';
        message.error(errorMsg);
        if (onError) {
          onError(errorMsg);
        }
      }
    } catch (err: any) {
      console.error('[useInstaller] Failed to poll status:', err);

      // Don't stop polling on transient errors
      // Only stop if we get a 404 (installation not found)
      if (err?.response?.status === 404) {
        pollingActiveRef.current = false;
        if (pollIntervalRef.current) {
          clearInterval(pollIntervalRef.current);
          pollIntervalRef.current = null;
        }
        setRunning(false);
        setSuccess(false);
        message.error('Instalação não encontrada');
      }
    }
  }, [message, onSuccess, onError]);

  /**
   * Start installation process
   */
  const startInstallation = useCallback(async (formData: InstallFormData) => {
    try {
      addLocalLog('Iniciando instalação...', 'info');
      setRunning(true);
      setSuccess(null);
      setProgress(0);
      setStatusMessage('Preparando...');

      // Build installation request payload
      const payload: any = {
        host: formData.host,
        port: formData.port,
        username: formData.username,
        password: formData.password,
        target_type: formData.targetType,
        exporter_port: formData.exporterPort,
        connection_method: formData.connectionMethod,
        collector_profile: formData.selectedCollectors.join(','),
        version: formData.selectedVersion,
        register_in_consul: formData.autoRegisterConsul,
        consul_service_name: formData.consulServiceName,
        consul_tags: formData.consulTags,
      };

      // Add optional fields
      if (formData.domain) {
        payload.domain = formData.domain;
      }

      if (formData.privateKeyFile) {
        payload.key_file = formData.privateKeyFile;
      }

      if (formData.enableBasicAuth) {
        payload.basic_auth_user = formData.basicAuthUser;
        payload.basic_auth_password = formData.basicAuthPassword;
      }

      // Call installation API
      const response = await consulAPI.installExporter(payload);
      const installId = response.data.installation_id;

      if (!installId) {
        throw new Error('ID de instalação não retornado pela API');
      }

      setInstallationId(installId);
      addLocalLog(`Instalação iniciada com ID: ${installId}`, 'success');

      // Start polling
      pollingActiveRef.current = true;
      pollIntervalRef.current = setInterval(() => {
        pollStatus(installId);
      }, POLL_INTERVAL_MS);

      // Poll immediately
      pollStatus(installId);

      return installId;
    } catch (err: any) {
      const errorMsg = err?.response?.data?.detail || err?.message || 'Erro ao iniciar instalação';
      message.error(errorMsg);
      addLocalLog(`Erro: ${errorMsg}`, 'error');
      setRunning(false);
      setSuccess(false);

      if (onError) {
        onError(errorMsg);
      }

      throw err;
    }
  }, [addLocalLog, message, pollStatus, onError]);

  /**
   * Stop installation (cleanup)
   */
  const stopInstallation = useCallback(() => {
    pollingActiveRef.current = false;

    if (pollIntervalRef.current) {
      clearInterval(pollIntervalRef.current);
      pollIntervalRef.current = null;
    }

    setRunning(false);
  }, []);

  /**
   * Reset installation state
   */
  const reset = useCallback(() => {
    stopInstallation();
    setInstallationId(null);
    setSuccess(null);
    setProgress(0);
    setStatusMessage('');
    setTask(null);
    clearLogs();
  }, [stopInstallation, clearLogs]);

  /**
   * Cleanup on unmount
   */
  useEffect(() => {
    return () => {
      stopInstallation();
    };
  }, [stopInstallation]);

  return {
    // State
    installationId,
    running,
    success,
    progress,
    statusMessage,
    logs,
    task,

    // Actions
    startInstallation,
    stopInstallation,
    reset,
    addLog,
    addLocalLog,
    clearLogs,
  };
}
