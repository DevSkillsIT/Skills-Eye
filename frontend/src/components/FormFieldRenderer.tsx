/**
 * FormFieldRenderer - Renderizador Dinâmico de Campos de Formulário
 *
 * OBJETIVO:
 * Componente que renderiza dinamicamente qualquer campo metadata baseado em sua configuração.
 * Elimina necessidade de hardcoding de campos nos formulários.
 *
 * FUNCIONAMENTO:
 * 1. Recebe configuração completa do campo (MetadataFieldDynamic)
 * 2. Determina tipo de componente baseado em field_type e available_for_registration
 * 3. Renderiza Form.Item com componente apropriado
 * 4. Aplica validações, placeholders, e propriedades automaticamente
 *
 * USO:
 * ```tsx
 * const formFields = useFormFields({ context: 'services', enabled: true, show_in_form: true });
 *
 * {formFields.map(field => (
 *   <FormFieldRenderer key={field.name} field={field} />
 * ))}
 * ```
 *
 * TIPOS DE CAMPO SUPORTADOS:
 * - string + available_for_registration → ReferenceValueInput (autocomplete)
 * - string → ProFormText
 * - select → ProFormSelect
 * - text → ProFormTextArea
 * - url → ProFormText (com validação URL)
 * - number → ProFormDigit
 */

import React from 'react';
import { Form } from 'antd';
import type { Rule } from 'antd/es/form';
import {
  ProFormText,
  ProFormSelect,
  ProFormTextArea,
  ProFormDigit
} from '@ant-design/pro-components';
import ReferenceValueInput from './ReferenceValueInput';
import type { MetadataFieldDynamic } from '../services/api';

export interface FormFieldRendererProps {
  /** Configuração completa do campo */
  field: MetadataFieldDynamic;

  /** Modo do formulário (opcional - pode afetar renderização) */
  mode?: 'create' | 'edit';

  /** Estilo customizado para o Form.Item */
  style?: React.CSSProperties;

  /** ClassName customizada */
  className?: string;

  /** Se True, força uso de ProForm ao invés de componentes visuais */
  forceStandardInput?: boolean;
}

/**
 * Componente que renderiza dinamicamente um campo baseado em sua configuração
 */
const FormFieldRenderer: React.FC<FormFieldRendererProps> = ({
  field,
  mode = 'create',
  style,
  className,
  forceStandardInput = false
}) => {
  /**
   * Construir regras de validação baseadas na configuração do campo
   */
  const buildRules = (): Rule[] => {
    const rules: Rule[] = [];

    // REQUIRED
    if (field.required) {
      rules.push({
        required: true,
        message: field.validation?.required_message || `${field.display_name} é obrigatório`
      });
    }

    // MIN/MAX LENGTH
    if (field.validation?.min_length || field.validation?.max_length) {
      rules.push({
        min: field.validation.min_length,
        max: field.validation.max_length,
        message: `${field.display_name} deve ter entre ${field.validation.min_length || 0} e ${field.validation.max_length || 200} caracteres`
      });
    }

    // REGEX VALIDATION
    if (field.validation_regex) {
      rules.push({
        pattern: new RegExp(field.validation_regex),
        message: `Formato inválido para ${field.display_name}`
      });
    }

    // URL VALIDATION (para field_type: url)
    if (field.field_type === 'url') {
      rules.push({
        type: 'url',
        message: 'URL inválida'
      });
    }

    return rules;
  };

  const rules = buildRules();

  /**
   * ESTRATÉGIA DE RENDERIZAÇÃO:
   *
   * 1. Se campo tem available_for_registration=true e é string → ReferenceValueInput (autocomplete)
   * 2. Se campo é select → ProFormSelect
   * 3. Se campo é text → ProFormTextArea
   * 4. Se campo é number → ProFormDigit
   * 5. Caso contrário → ProFormText
   */

  // CASO 1: Campo com auto-cadastro (ReferenceValueInput com autocomplete)
  if (
    !forceStandardInput &&
    field.available_for_registration &&
    (field.field_type === 'string' || field.field_type === 'url')
  ) {
    return (
      <Form.Item
        name={field.name}
        label={field.display_name}
        rules={rules}
        tooltip={field.description}
        style={style}
        className={className}
      >
        <ReferenceValueInput
          fieldName={field.name}
          placeholder={field.placeholder || `Selecione ou digite ${field.display_name.toLowerCase()}`}
          required={field.required}
        />
      </Form.Item>
    );
  }

  // CASO 2: Select com opções pré-definidas
  if (field.field_type === 'select' && field.options && field.options.length > 0) {
    return (
      <ProFormSelect
        name={field.name}
        label={field.display_name}
        placeholder={field.placeholder || `Selecione ${field.display_name.toLowerCase()}`}
        tooltip={field.description}
        options={field.options.map((opt) => ({ label: opt, value: opt }))}
        rules={rules}
        fieldProps={{
          allowClear: !field.required
        }}
        style={style}
        className={className}
      />
    );
  }

  // CASO 3: Textarea para campos de texto longo
  if (field.field_type === 'text') {
    return (
      <ProFormTextArea
        name={field.name}
        label={field.display_name}
        placeholder={field.placeholder || `Digite ${field.display_name.toLowerCase()}`}
        tooltip={field.description}
        rules={rules}
        fieldProps={{
          rows: 4,
          maxLength: field.validation?.max_length || 1000
        }}
        style={style}
        className={className}
      />
    );
  }

  // CASO 4: Número
  if (field.field_type === 'number') {
    return (
      <ProFormDigit
        name={field.name}
        label={field.display_name}
        placeholder={field.placeholder || `Digite ${field.display_name.toLowerCase()}`}
        tooltip={field.description}
        rules={rules}
        fieldProps={{
          min: 0
        }}
        style={style}
        className={className}
      />
    );
  }

  // CASO 5: String padrão (sem auto-cadastro)
  return (
    <ProFormText
      name={field.name}
      label={field.display_name}
      placeholder={field.placeholder || `Digite ${field.display_name.toLowerCase()}`}
      tooltip={field.description}
      rules={rules}
      fieldProps={{
        maxLength: field.validation?.max_length || 200
      }}
      style={style}
      className={className}
    />
  );
};

export default FormFieldRenderer;
