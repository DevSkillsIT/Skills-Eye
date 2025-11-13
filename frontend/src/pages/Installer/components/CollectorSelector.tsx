/**
 * CollectorSelector Component
 * Allows selection of exporter collectors based on target OS
 */

import React, { useMemo } from 'react';
import { Card, Checkbox, Row, Col, Typography, Tag, Space } from 'antd';
import { LinuxOutlined, WindowsOutlined } from '@ant-design/icons';
import type { TargetType } from '../types';
import { COLLECTOR_OPTIONS, DEFAULT_LINUX_COLLECTORS, DEFAULT_WINDOWS_COLLECTORS } from '../constants';

const { Text, Title } = Typography;

interface CollectorSelectorProps {
  targetType: TargetType;
  selectedCollectors: string[];
  onChange: (collectors: string[]) => void;
  disabled?: boolean;
}

export const CollectorSelector: React.FC<CollectorSelectorProps> = ({
  targetType,
  selectedCollectors,
  onChange,
  disabled = false,
}) => {
  /**
   * Filter collectors based on target type
   */
  const availableCollectors = useMemo(() => {
    return COLLECTOR_OPTIONS.filter((opt) => opt.targets.includes(targetType));
  }, [targetType]);

  /**
   * Get default collectors for target type
   */
  const defaultCollectors = useMemo(() => {
    return targetType === 'linux' ? DEFAULT_LINUX_COLLECTORS : DEFAULT_WINDOWS_COLLECTORS;
  }, [targetType]);

  /**
   * Handle collector toggle
   */
  const handleToggle = (collectorValue: string, checked: boolean) => {
    if (checked) {
      onChange([...selectedCollectors, collectorValue]);
    } else {
      onChange(selectedCollectors.filter((c) => c !== collectorValue));
    }
  };

  /**
   * Select all collectors
   */
  const selectAll = () => {
    onChange(availableCollectors.map((c) => c.value));
  };

  /**
   * Deselect all collectors
   */
  const deselectAll = () => {
    onChange([]);
  };

  /**
   * Reset to defaults
   */
  const resetToDefaults = () => {
    onChange(defaultCollectors);
  };

  return (
    <Card
      title={
        <Space>
          {targetType === 'linux' ? <LinuxOutlined /> : <WindowsOutlined />}
          <span>Collectors ({targetType === 'linux' ? 'Node Exporter' : 'Windows Exporter'})</span>
        </Space>
      }
      size="small"
      extra={
        <Space size="small">
          <a onClick={selectAll} style={{ fontSize: 12 }}>
            Selecionar todos
          </a>
          <a onClick={deselectAll} style={{ fontSize: 12 }}>
            Limpar
          </a>
          <a onClick={resetToDefaults} style={{ fontSize: 12 }}>
            Padrão
          </a>
        </Space>
      }
    >
      <Text type="secondary" style={{ display: 'block', marginBottom: 12, fontSize: 12 }}>
        Selecione os collectors que deseja habilitar no exporter. Collectors padrão já vêm pré-selecionados.
      </Text>

      <Row gutter={[12, 12]}>
        {availableCollectors.map((collector) => {
          const isSelected = selectedCollectors.includes(collector.value);
          const isDefault = defaultCollectors.includes(collector.value);

          return (
            <Col span={24} key={collector.value}>
              <Card
                size="small"
                hoverable={!disabled}
                onClick={() => !disabled && handleToggle(collector.value, !isSelected)}
                style={{
                  cursor: disabled ? 'not-allowed' : 'pointer',
                  borderColor: isSelected ? '#1890ff' : undefined,
                  backgroundColor: isSelected ? '#f0f7ff' : undefined,
                  opacity: disabled ? 0.6 : 1,
                }}
                bodyStyle={{ padding: 12 }}
              >
                <Space direction="vertical" size={4} style={{ width: '100%' }}>
                  {/* Header with checkbox and tags */}
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                    <Space>
                      <Checkbox
                        checked={isSelected}
                        onChange={(e) => handleToggle(collector.value, e.target.checked)}
                        disabled={disabled}
                        onClick={(e) => e.stopPropagation()}
                      />
                      <Text strong>{collector.label}</Text>
                    </Space>

                    {isDefault && (
                      <Tag color="green" style={{ margin: 0 }}>
                        Recomendado
                      </Tag>
                    )}
                  </div>

                  {/* Description */}
                  <div style={{ marginLeft: 24 }}>
                    <Text type="secondary" style={{ fontSize: 12 }}>
                      {collector.description}
                    </Text>
                  </div>
                </Space>
              </Card>
            </Col>
          );
        })}
      </Row>

      {/* Selection summary */}
      <div style={{ marginTop: 12, padding: '8px 12px', backgroundColor: '#f5f5f5', borderRadius: 4 }}>
        <Text style={{ fontSize: 12 }}>
          <strong>{selectedCollectors.length}</strong> de <strong>{availableCollectors.length}</strong> collectors
          selecionados
        </Text>
      </div>
    </Card>
  );
};
