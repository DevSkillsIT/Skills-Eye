/**
 * Componente ReferenceValueInput - AutoComplete com Auto-Cadastro
 *
 * OBJETIVO:
 * Input inteligente que:
 * 1. Mostra valores existentes como opções de select
 * 2. Permite usuário digitar valor novo
 * 3. Ao salvar formulário, auto-cadastra valores novos automaticamente
 * 4. Normaliza valores (Title Case)
 *
 * USO:
 * ```tsx
 * <ReferenceValueInput
 *   fieldName="company"
 *   value={empresa}
 *   onChange={setEmpresa}
 *   placeholder="Selecione ou digite empresa"
 *   required={true}
 * />
 * ```
 *
 * EXEMPLO DE FLUXO:
 * 1. Usuário abre formulário
 * 2. Select mostra: ["Empresa Ramada", "Acme Corp", "TechCorp"]
 * 3. Usuário digita "nova empresa ltda"
 * 4. Ao salvar formulário pai, chama ensureValue() automaticamente
 * 5. Backend normaliza para "Nova Empresa Ltda" e cadastra
 * 6. Próximo cadastro: "Nova Empresa Ltda" aparece nas opções
 */

import React, { useState, useEffect } from 'react';
import { AutoComplete, Spin, Tag } from 'antd';
import { PlusOutlined, LoadingOutlined } from '@ant-design/icons';
import { useReferenceValues } from '../hooks/useReferenceValues';

export interface ReferenceValueInputProps {
  /** Nome do campo (company, localizacao, cidade, etc) */
  fieldName: string;

  /** Valor atual */
  value?: string;

  /** Callback quando valor muda */
  onChange?: (value: string) => void;

  /** Placeholder do input */
  placeholder?: string;

  /** Se campo é obrigatório */
  required?: boolean;

  /** Desabilitar input */
  disabled?: boolean;

  /** Texto de ajuda exibido abaixo do campo */
  helpText?: string;

  /** Se True, auto-cadastra valor ao mudar (padrão: False, espera salvar formulário pai) */
  autoEnsureOnChange?: boolean;

  /** Estilo customizado */
  style?: React.CSSProperties;

  /** ClassName customizada */
  className?: string;
}

/**
 * Input com auto-complete e auto-cadastro de valores
 */
const ReferenceValueInput: React.FC<ReferenceValueInputProps> = ({
  fieldName,
  value,
  onChange,
  placeholder = 'Selecione ou digite...',
  required = false,
  disabled = false,
  helpText,
  autoEnsureOnChange = false,
  style,
  className
}) => {
  const {
    values,
    loading,
    error,
    ensureValue
  } = useReferenceValues({
    fieldName,
    autoLoad: true,
    includeStats: false
  });

  const [internalValue, setInternalValue] = useState<string>(value || '');
  const [isEnsuring, setIsEnsuring] = useState(false);

  /**
   * Sincronizar valor interno com prop value
   */
  useEffect(() => {
    if (value !== undefined) {
      setInternalValue(value);
    }
  }, [value]);

  /**
   * Handler quando valor muda
   */
  const handleChange = async (newValue: string) => {
    setInternalValue(newValue);

    // Notificar componente pai
    if (onChange) {
      onChange(newValue);
    }

    // Auto-cadastro IMEDIATO se habilitado
    // IMPORTANTE: Na maioria dos casos, NÃO use autoEnsureOnChange=true!
    // Deixe o formulário pai chamar ensureValue() ao salvar.
    if (autoEnsureOnChange && newValue) {
      setIsEnsuring(true);

      try {
        const result = await ensureValue(newValue);

        if (result.success && result.value !== newValue) {
          // Valor foi normalizado, atualizar
          setInternalValue(result.value);

          if (onChange) {
            onChange(result.value);
          }
        }
      } catch (err) {
        console.error(`Erro ao garantir valor ${newValue}:`, err);
      } finally {
        setIsEnsuring(false);
      }
    }
  };

  /**
   * Preparar opções para o AutoComplete
   */
  const options = values.map((val) => ({
    value: val,
    label: (
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <span>{val}</span>
      </div>
    )
  }));

  /**
   * Filtrar opções baseado no que usuário digitou
   */
  const filterOption = (inputValue: string, option: any) => {
    return option.value.toLowerCase().includes(inputValue.toLowerCase());
  };

  return (
    <div style={{ position: 'relative', height: '100%', display: 'flex', alignItems: 'center' }}>
      <AutoComplete
        value={internalValue}
        onChange={handleChange}
        options={options}
        placeholder={placeholder}
        disabled={disabled || loading}
        style={{ width: '100%', ...style }}
        className={className}
        filterOption={filterOption}
        notFoundContent={
          loading ? (
            <div style={{ textAlign: 'center', padding: '8px' }}>
              <Spin size="small" />
              <span style={{ marginLeft: 8 }}>Carregando valores...</span>
            </div>
          ) : (
            <div style={{ textAlign: 'center', padding: '8px', color: '#999' }}>
              <PlusOutlined style={{ marginRight: 4 }} />
              Digite para criar novo valor
            </div>
          )
        }
        suffixIcon={
          isEnsuring ? (
            <LoadingOutlined spin />
          ) : null
        }
      />

      {helpText && (
        <div style={{ fontSize: '12px', color: '#666', marginTop: 4 }}>
          {helpText}
        </div>
      )}

      {error && (
        <div style={{ fontSize: '12px', color: '#ff4d4f', marginTop: 4 }}>
          ⚠ {error}
        </div>
      )}

      {/* Indicador visual quando valor não existe */}
      {internalValue && !loading && !values.includes(internalValue) && (
        <div style={{ marginTop: 4 }}>
          <Tag color="green" icon={<PlusOutlined />} style={{ fontSize: '11px' }}>
            Novo valor será criado: "{internalValue}"
          </Tag>
        </div>
      )}
    </div>
  );
};

export default ReferenceValueInput;
