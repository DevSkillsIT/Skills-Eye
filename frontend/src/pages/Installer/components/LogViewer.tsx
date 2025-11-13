/**
 * LogViewer Component
 * Real-time log display with color-coded levels and expandable details
 */

import React, { useRef, useEffect } from 'react';
import { Card, List, Tag, Typography, Empty } from 'antd';
import {
  InfoCircleOutlined,
  CheckCircleOutlined,
  WarningOutlined,
  CloseCircleOutlined,
  CodeOutlined,
} from '@ant-design/icons';
import type { InstallLogEntry } from '../types';
import { LOG_LEVEL_COLOR } from '../constants';

const { Text } = Typography;

interface LogViewerProps {
  logs: InstallLogEntry[];
  title?: string;
  height?: number;
  autoScroll?: boolean;
  showTimestamp?: boolean;
}

/**
 * Get icon for log level
 */
function getLogIcon(level?: string) {
  switch (level) {
    case 'error':
      return <CloseCircleOutlined />;
    case 'warning':
      return <WarningOutlined />;
    case 'success':
      return <CheckCircleOutlined />;
    case 'debug':
      return <CodeOutlined />;
    case 'progress':
    case 'info':
    default:
      return <InfoCircleOutlined />;
  }
}

/**
 * Format timestamp for display
 */
function formatTimestamp(iso?: string): string {
  if (!iso) return '';

  const parsed = new Date(iso);
  if (Number.isNaN(parsed.getTime())) return '';

  return parsed.toLocaleTimeString('pt-BR', { hour12: false });
}

export const LogViewer: React.FC<LogViewerProps> = ({
  logs,
  title = 'Logs de Instalação',
  height = 400,
  autoScroll = true,
  showTimestamp = true,
}) => {
  const listEndRef = useRef<HTMLDivElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  /**
   * Auto-scroll to bottom when new logs arrive
   */
  useEffect(() => {
    if (autoScroll && listEndRef.current) {
      listEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [logs, autoScroll]);

  return (
    <Card
      title={title}
      size="small"
      style={{ marginTop: 16 }}
      bodyStyle={{
        padding: 0,
        height,
        overflow: 'auto',
        backgroundColor: '#1f1f1f',
      }}
    >
      <div ref={containerRef} style={{ padding: 12 }}>
        {logs.length === 0 ? (
          <Empty
            description="Nenhum log ainda"
            image={Empty.PRESENTED_IMAGE_SIMPLE}
            style={{ marginTop: 100 }}
          />
        ) : (
          <List
            dataSource={logs}
            split={false}
            renderItem={(log) => {
              const color = LOG_LEVEL_COLOR[log.level || 'info'];
              const icon = getLogIcon(log.level);

              return (
                <List.Item
                  key={log.key}
                  style={{
                    padding: '4px 0',
                    border: 'none',
                    color: '#d4d4d4',
                  }}
                >
                  <div style={{ width: '100%' }}>
                    {/* Main log line */}
                    <div style={{ display: 'flex', alignItems: 'flex-start', gap: 8 }}>
                      {/* Timestamp */}
                      {showTimestamp && log.timestamp && (
                        <Text
                          style={{
                            color: '#666',
                            fontSize: 11,
                            fontFamily: 'monospace',
                            minWidth: 70,
                          }}
                        >
                          {formatTimestamp(log.timestamp)}
                        </Text>
                      )}

                      {/* Level tag */}
                      <Tag
                        color={color}
                        icon={icon}
                        style={{ margin: 0, minWidth: 70, textAlign: 'center' }}
                      >
                        {(log.level || 'info').toUpperCase()}
                      </Tag>

                      {/* Message */}
                      <Text
                        style={{
                          color: log.level === 'error' ? '#ff6b6b' : '#d4d4d4',
                          fontFamily: 'monospace',
                          fontSize: 12,
                          flex: 1,
                          whiteSpace: 'pre-wrap',
                          wordBreak: 'break-word',
                        }}
                      >
                        {log.message}
                      </Text>
                    </div>

                    {/* Details (if present) */}
                    {log.details && (
                      <div
                        style={{
                          marginTop: 4,
                          marginLeft: showTimestamp ? 78 + 78 + 16 : 78 + 8,
                          padding: 8,
                          backgroundColor: '#2d2d2d',
                          borderLeft: `3px solid ${color}`,
                          borderRadius: 2,
                        }}
                      >
                        <Text
                          style={{
                            color: '#999',
                            fontFamily: 'monospace',
                            fontSize: 11,
                            whiteSpace: 'pre-wrap',
                            wordBreak: 'break-word',
                          }}
                        >
                          {log.details}
                        </Text>
                      </div>
                    )}
                  </div>
                </List.Item>
              );
            }}
          />
        )}

        {/* Auto-scroll anchor */}
        <div ref={listEndRef} />
      </div>
    </Card>
  );
};
