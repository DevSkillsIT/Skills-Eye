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
import { Input, Select, InputNumber } from 'antd';
import type { Rule } from 'antd/es/form';
import ReferenceValueInput from './ReferenceValueInput';
import FloatingFormField from './FloatingFormField';
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
  // Cast field to any to avoid TS errors with missing properties in interface
  const fieldAny = field as any;
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
    if (fieldAny.validation_regex) {
      rules.push({
        pattern: new RegExp(fieldAny.validation_regex),
        message: `Formato inválido para ${field.display_name}`
      });
    }

    // URL VALIDATION (para field_type: url)
    if (fieldAny.field_type === 'url') {
      rules.push({
        type: 'url',
        message: 'URL inválida'
      });
    }

    return rules;
  };

  const rules = buildRules();

  /**
   * LISTA DE CAMPOS QUE NUNCA DEVEM USAR AUTOCOMPLETE
   * Mesmo com available_for_registration=true, estes campos são únicos ou especiais
   */
  const EXCLUDE_FROM_AUTOCOMPLETE = [
    'cservice',           // ID interno do Consul
    'serviceDisplayName', // Nome de exibição único
    'name',               // Nome único do serviço
    'instance',           // IP:porta único
    'address',            // IP/hostname único
    'glpi_URL',           // URL única
    'glpi_url',           // URL única (case variation)
    'notas',              // Texto longo livre
    'notes',              // Texto longo livre
  ];

  /**
   * ESTRATÉGIA DE RENDERIZAÇÃO:
   *
   * 1. Se campo tem available_for_registration=true, é string E não está na blacklist → ReferenceValueInput
   * 2. Se campo é select → ProFormSelect
   * 3. Se campo é text → ProFormTextArea
   * 4. Se campo é url → ProFormText com validação
   * 5. Se campo é number → ProFormDigit
   * 6. Caso contrário → ProFormText
   */

  // CASO 1: Campo com auto-cadastro (ReferenceValueInput com autocomplete)
  const shouldUseAutocomplete =
    !forceStandardInput &&
    field.available_for_registration &&
    fieldAny.field_type === 'string' &&
    !EXCLUDE_FROM_AUTOCOMPLETE.includes(field.name);

  if (shouldUseAutocomplete) {
    return (
      <FloatingFormField
        name={field.name}
        label={field.display_name}
        helper={field.description}
        required={field.required}
        rules={rules}
        style={style}
        className={className}
      >
        <ReferenceValueInput
          fieldName={field.name}
          placeholder={field.placeholder || `Selecione ou digite ${field.display_name.toLowerCase()}`}
          required={field.required}
        />
      </FloatingFormField>
    );
  }

  // CASO 2: Select com opções pré-definidas
  if (fieldAny.field_type === 'select' && field.options && field.options.length > 0) {
    return (
      <FloatingFormField
        name={field.name}
        label={field.display_name}
        helper={field.description}
        required={field.required}
        rules={rules}
        style={style}
        className={className}
      >
        <Select
          placeholder={field.placeholder || `Selecione ${field.display_name.toLowerCase()}`}
          options={field.options.map((opt) => ({ label: opt, value: opt }))}
          allowClear={!field.required}
        />
      </FloatingFormField>
    );
  }

  // CASO 3: Textarea para campos de texto longo
  if (fieldAny.field_type === 'text') {
    return (
      <FloatingFormField
        name={field.name}
        label={field.display_name}
        helper={field.description}
        required={field.required}
        rules={rules}
        style={style}
        className={className}
        fixedHeight={false}
      >
        <Input.TextArea
          placeholder={field.placeholder || `Digite ${field.display_name.toLowerCase()}`}
          autoSize={{ minRows: 3, maxRows: 6 }}
          maxLength={fieldAny.validation?.max_length || 1000}
        />
      </FloatingFormField>
    );
  }

  // CASO 4: Número
  if (fieldAny.field_type === 'number') {
    return (
      <FloatingFormField
        name={field.name}
        label={field.display_name}
        helper={field.description}
        required={field.required}
        rules={rules}
        style={style}
        className={className}
      >
        <InputNumber
          placeholder={field.placeholder || `Digite ${field.display_name.toLowerCase()}`}
          min={0}
          style={{ width: '100%' }}
        />
      </FloatingFormField>
    );
  }

  // CASO 5: String padrão (sem auto-cadastro)
  return (
    <FloatingFormField
      name={field.name}
      label={field.display_name}
      helper={field.description}
      required={field.required}
      rules={rules}
      style={style}
      className={className}
    >
      <Input
        placeholder={field.placeholder || `Digite ${field.display_name.toLowerCase()}`}
        maxLength={fieldAny.validation?.max_length || 200}
      />
    </FloatingFormField>
  );
};

export default FormFieldRenderer;
