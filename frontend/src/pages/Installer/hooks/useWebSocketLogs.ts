/**
 * Hook for managing WebSocket log connections
 * Handles real-time log streaming from installation process
 */

import { useEffect, useRef, useState, useCallback } from 'react';
import type { InstallLogEntry, WebSocketLogMessage } from '../types';
import { API_URL, WEBSOCKET_RECONNECT_DELAY_MS } from '../constants';

interface UseWebSocketLogsOptions {
  installationId: string | null;
  enabled: boolean;
  onLog?: (log: InstallLogEntry) => void;
}

/**
 * Format timestamp from ISO string to locale time
 */
function formatLogTimestamp(iso?: string): string | undefined {
  if (!iso) return undefined;

  const parsed = new Date(iso);
  if (Number.isNaN(parsed.getTime())) return undefined;

  return parsed.toLocaleTimeString('pt-BR', { hour12: false });
}

/**
 * Build details string from log data
 */
function buildLogDetails(data?: Record<string, unknown>): string | undefined {
  if (!data) return undefined;

  const sections: string[] = [];

  // Command
  const commandValue = data.command;
  if (typeof commandValue === 'string' && commandValue.trim().length > 0) {
    sections.push(`Comando: ${commandValue}`);
  }

  // Exit code
  const exitCodeValue = data.exit_code;
  if (typeof exitCodeValue === 'number') {
    sections.push(`Exit code: ${exitCodeValue}`);
  } else if (typeof exitCodeValue === 'string' && exitCodeValue.trim().length > 0) {
    sections.push(`Exit code: ${exitCodeValue}`);
  }

  // Output
  const outputValue = data.output;
  if (typeof outputValue === 'string' && outputValue.trim().length > 0) {
    sections.push(`Saída:\n${outputValue.trim()}`);
  }

  // Extra data
  const reservedKeys = new Set(['command', 'output', 'exit_code']);
  const extraEntries = Object.entries(data).filter(([key]) => !reservedKeys.has(key));

  if (extraEntries.length > 0) {
    const formattedExtras = extraEntries
      .map(([key, value]) => {
        if (typeof value === 'string' || typeof value === 'number' || typeof value === 'boolean') {
          return `${key}: ${value}`;
        }
        try {
          return `${key}: ${JSON.stringify(value, null, 2)}`;
        } catch {
          return `${key}: ${String(value)}`;
        }
      })
      .join('\n');
    sections.push(formattedExtras);
  }

  return sections.length > 0 ? sections.join('\n') : undefined;
}

/**
 * Convert WebSocket message to InstallLogEntry
 */
function messageToLogEntry(msg: WebSocketLogMessage, index: number): InstallLogEntry {
  const normalizedLevel = typeof msg.level === 'string' ? msg.level.toLowerCase() : undefined;

  return {
    key: `ws-${msg.timestamp}-${index}`,
    message: msg.message,
    source: 'remote',
    level: normalizedLevel,
    timestamp: msg.timestamp,
    details: buildLogDetails(msg.data),
  };
}

export function useWebSocketLogs(options: UseWebSocketLogsOptions) {
  const { installationId, enabled, onLog } = options;

  const [connected, setConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const logIndexRef = useRef(0);

  const connect = useCallback(() => {
    if (!installationId || !enabled) return;

    // Clear any existing reconnect timeout
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }

    // Close existing connection
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }

    try {
      // Build WebSocket URL (replace http with ws)
      const wsUrl = API_URL.replace(/^http/, 'ws').replace('/api/v1', '');
      const ws = new WebSocket(`${wsUrl}/ws/installer/${installationId}`);

      ws.onopen = () => {
        console.log('[useWebSocketLogs] Connected to WebSocket');
        setConnected(true);
        setError(null);
      };

      ws.onmessage = (event) => {
        try {
          const msg: WebSocketLogMessage = JSON.parse(event.data);
          const logEntry = messageToLogEntry(msg, logIndexRef.current++);

          if (onLog) {
            onLog(logEntry);
          }
        } catch (err) {
          console.error('[useWebSocketLogs] Failed to parse message:', err);
        }
      };

      ws.onerror = (event) => {
        console.error('[useWebSocketLogs] WebSocket error:', event);
        setError('Erro na conexão WebSocket');
        setConnected(false);
      };

      ws.onclose = (event) => {
        console.log('[useWebSocketLogs] WebSocket closed:', event.code, event.reason);
        setConnected(false);

        // Auto-reconnect if not a normal closure and still enabled
        if (event.code !== 1000 && enabled) {
          console.log(`[useWebSocketLogs] Reconnecting in ${WEBSOCKET_RECONNECT_DELAY_MS}ms...`);
          reconnectTimeoutRef.current = setTimeout(() => {
            connect();
          }, WEBSOCKET_RECONNECT_DELAY_MS);
        }
      };

      wsRef.current = ws;
    } catch (err) {
      console.error('[useWebSocketLogs] Failed to create WebSocket:', err);
      setError('Falha ao criar conexão WebSocket');
      setConnected(false);
    }
  }, [installationId, enabled, onLog]);

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }

    if (wsRef.current) {
      wsRef.current.close(1000, 'Client disconnect');
      wsRef.current = null;
    }

    setConnected(false);
  }, []);

  // Connect when enabled and installationId is set
  useEffect(() => {
    if (enabled && installationId) {
      connect();
    } else {
      disconnect();
    }

    return () => {
      disconnect();
    };
  }, [installationId, enabled, connect, disconnect]);

  return {
    connected,
    error,
    reconnect: connect,
    disconnect,
  };
}
