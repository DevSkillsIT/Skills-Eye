/**
 * SISTEMA DINÂMICO: MetadataFilterBar gera filtros baseado em filterFields do backend
 *
 * Antes: Campos hardcoded (module, company, grupo_monitoramento, etc)
 * Depois: Campos carregados de metadata_fields.json via API
 *
 * Props:
 * - fields: Array de MetadataFieldDynamic com show_in_filter=true
 * - value: Estado atual dos filtros (Record<string, string>)
 * - options: Valores disponíveis para cada campo (Record<string, string[]>)
 * - loading: Estado de carregamento
 * - onChange: Callback para mudança de filtro
 * - onReset: Callback para limpar filtros
 * - extra: Componentes extras (ex: seletor de nó)
 */

import React from 'react';
import { Button, Select, Space, Tooltip } from 'antd';
import { ReloadOutlined } from '@ant-design/icons';
import type { MetadataFieldDynamic } from '../services/api';

const { Option } = Select;

export interface MetadataFilterBarProps {
  // Campos dinâmicos do backend (com show_in_filter=true)
  fields?: MetadataFieldDynamic[];
  // Estado atual dos filtros (chave=nome_campo, valor=valor_selecionado)
  value: Record<string, string | undefined>;
  // Opções disponíveis para cada campo (chave=nome_campo, valor=array de valores)
  options: Record<string, string[]>;
  loading?: boolean;
  onChange: (value: Record<string, string | undefined>) => void;
  onReset?: () => void;
  extra?: React.ReactNode;
}

const MetadataFilterBar: React.FC<MetadataFilterBarProps> = ({
  fields = [],
  value,
  options,
  loading = false,
  onChange,
  onReset,
  extra,
}) => {
  // ✅ OTIMIZAÇÃO: Remover console.log para reduzir ruído (usar apenas em debug)
  // console.log('[MetadataFilterBar] DEBUG:', { ... });

  const handleChange = (fieldName: string, nextValue?: string) => {
    onChange({
      ...value,
      [fieldName]: nextValue || undefined,
    });
  };

  return (
    <Space wrap align="center">
      {/* GERAÇÃO DINÂMICA: Um Select para cada campo com show_in_filter=true */}
      {fields.map((field) => {
        // ✅ SPRINT 1 (2025-11-14): Validação defensiva com optional chaining
        const fieldOptions = options?.[field.name] ?? [];
        const minWidth = field.display_name.length > 15 ? 200 : 150;

        // ✅ SPRINT 1: Não renderizar select sem opções (evita race condition)
        // Protege contra TypeError quando options ainda não foi carregado
        if (!fieldOptions || fieldOptions.length === 0) {
          return null;
        }

        return (
          <Select
            key={field.name}
            allowClear
            showSearch
            placeholder={field.placeholder || field.display_name}
            style={{ minWidth }}
            loading={loading}
            value={value?.[field.name]}
            onChange={(val) => handleChange(field.name, val)}
          >
            {fieldOptions.map((item) => (
              <Option value={item} key={`${field.name}-${item}`}>
                {item}
              </Option>
            ))}
          </Select>
        );
      })}

      {onReset && (
        <Tooltip title="Limpar filtros">
          <Button icon={<ReloadOutlined />} onClick={() => onReset()} />
        </Tooltip>
      )}

      {extra}
    </Space>
  );
};

// ✅ OTIMIZAÇÃO: React.memo para evitar re-renders desnecessários
// Só re-renderiza se fields, value, options ou loading mudarem
export default React.memo(MetadataFilterBar, (prevProps, nextProps) => {
  // Comparação customizada para evitar re-renders desnecessários
  return (
    prevProps.loading === nextProps.loading &&
    prevProps.fields === nextProps.fields &&
    prevProps.options === nextProps.options &&
    JSON.stringify(prevProps.value) === JSON.stringify(nextProps.value)
  );
});
