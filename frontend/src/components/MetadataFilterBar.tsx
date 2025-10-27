import React from 'react';
import { Button, Select, Space, Tooltip } from 'antd';
import { ReloadOutlined } from '@ant-design/icons';
import type { MetadataFilters } from '../services/api';

const { Option } = Select;

export interface MetadataFilterOptions {
  modules?: string[];
  companies?: string[];
  projects?: string[];
  envs?: string[];
  groups?: string[];
}

interface MetadataFilterBarProps {
  value: MetadataFilters;
  options: MetadataFilterOptions;
  loading?: boolean;
  onChange: (value: MetadataFilters) => void;
  onReset?: () => void;
  extra?: React.ReactNode;
}

const MetadataFilterBar: React.FC<MetadataFilterBarProps> = ({
  value,
  options,
  loading = false,
  onChange,
  onReset,
  extra,
}) => {
  const handleChange = (key: keyof MetadataFilters, next?: string) => {
    onChange({
      ...value,
      [key]: next || undefined,
    });
  };

  return (
    <Space wrap align="center">
      <Select
        allowClear
        showSearch
        placeholder="Modulo"
        style={{ minWidth: 150 }}
        loading={loading}
        value={value.module}
        onChange={(val) => handleChange('module', val)}
      >
        {(options.modules || []).map((item) => (
          <Option value={item} key={item}>
            {item}
          </Option>
        ))}
      </Select>

      <Select
        allowClear
        showSearch
        placeholder="Empresa"
        style={{ minWidth: 150 }}
        loading={loading}
        value={value.company}
        onChange={(val) => handleChange('company', val)}
      >
        {(options.companies || []).map((item) => (
          <Option value={item} key={item}>
            {item}
          </Option>
        ))}
      </Select>

      <Select
        allowClear
        showSearch
        placeholder="Projeto"
        style={{ minWidth: 170 }}
        loading={loading}
        value={value.project}
        onChange={(val) => handleChange('project', val)}
      >
        {(options.projects || []).map((item) => (
          <Option value={item} key={item}>
            {item}
          </Option>
        ))}
      </Select>

      <Select
        allowClear
        showSearch
        placeholder="Ambiente"
        style={{ minWidth: 140 }}
        loading={loading}
        value={value.env}
        onChange={(val) => handleChange('env', val)}
      >
        {(options.envs || []).map((item) => (
          <Option value={item} key={item}>
            {item}
          </Option>
        ))}
      </Select>

      <Select
        allowClear
        showSearch
        placeholder="Grupo"
        style={{ minWidth: 150 }}
        loading={loading}
        value={value.group}
        onChange={(val) => handleChange('group', val)}
      >
        {(options.groups || []).map((item) => (
          <Option value={item} key={item}>
            {item}
          </Option>
        ))}
      </Select>

      {onReset && (
        <Tooltip title="Limpar filtros">
          <Button icon={<ReloadOutlined />} onClick={() => onReset()} />
        </Tooltip>
      )}

      {extra}
    </Space>
  );
};

export default MetadataFilterBar;
