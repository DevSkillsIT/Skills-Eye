/**
 * Formulário Dinâmico de Serviço
 * 
 * Renderiza campos baseados em form_schema do backend
 * Suporta campos específicos do exporter + campos de metadata
 */

import React, { useState, useEffect } from 'react';
import { Form, Input, InputNumber, Select, message } from 'antd';
import { consulAPI } from '../services/api';

interface FormSchemaField {
  name: string;
  label?: string;
  type: string;
  required?: boolean;
  default?: any;
  placeholder?: string;
  help?: string;
  options?: Array<{ value: string; label: string }>;
  min?: number;
  max?: number;
}

interface FormSchema {
  fields?: FormSchemaField[];
  required_metadata?: string[];
  optional_metadata?: string[];
}

interface DynamicServiceFormProps {
  category: string;
  exporterType?: string;
  initialValues?: Record<string, any>;
  onFinish: (values: Record<string, any>) => void | Promise<void>;
}

export const DynamicServiceForm: React.FC<DynamicServiceFormProps> = ({
  category,
  exporterType,
  initialValues,
  onFinish,
}) => {
  const [form] = Form.useForm();
  const [formSchema, setFormSchema] = useState<FormSchema | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const loadFormSchema = async () => {
      if (!exporterType) {
        setLoading(false);
        return;
      }

      try {
        const response = await consulAPI.getFormSchema(exporterType, category);
        const data = (response as any).data || response;
        
        if (data && data.success && data.form_schema) {
          setFormSchema(data.form_schema);
        } else {
          // Sem schema específico, apenas campos de metadata
          setFormSchema(null);
        }
      } catch (error: any) {
        console.error('Erro ao carregar form_schema:', error);
        message.warning('Não foi possível carregar schema do formulário');
      } finally {
        setLoading(false);
      }
    };

    loadFormSchema();
  }, [exporterType, category]);

  useEffect(() => {
    if (initialValues) {
      form.setFieldsValue(initialValues);
    }
  }, [initialValues, form]);

  const renderField = (field: FormSchemaField) => {
    const commonProps = {
      label: field.label || field.name,
      name: field.name,
      rules: [
        {
          required: field.required || false,
          message: `${field.label || field.name} é obrigatório`,
        },
      ],
      extra: field.help,
      initialValue: field.default,
    };

    switch (field.type) {
      case 'number':
        return (
          <Form.Item key={field.name} {...commonProps}>
            <InputNumber
              style={{ width: '100%' }}
              placeholder={field.placeholder}
              min={field.min}
              max={field.max}
            />
          </Form.Item>
        );

      case 'select':
        return (
          <Form.Item key={field.name} {...commonProps}>
            <Select
              placeholder={field.placeholder || `Selecione ${field.label || field.name}`}
              options={field.options}
            />
          </Form.Item>
        );

      case 'password':
        return (
          <Form.Item key={field.name} {...commonProps}>
            <Input.Password placeholder={field.placeholder} />
          </Form.Item>
        );

      case 'text':
      default:
        return (
          <Form.Item key={field.name} {...commonProps}>
            <Input placeholder={field.placeholder} />
          </Form.Item>
        );
    }
  };

  if (loading) {
    return <div>Carregando formulário...</div>;
  }

  return (
    <Form
      form={form}
      layout="vertical"
      onFinish={onFinish}
      initialValues={initialValues}
    >
      {/* Renderizar campos do form_schema */}
      {formSchema?.fields?.map(field => renderField(field))}

      {/* Campos de metadata comuns */}
      <Form.Item
        label="Nome do Serviço"
        name="name"
        rules={[{ required: true, message: 'Nome é obrigatório' }]}
      >
        <Input placeholder="Nome descritivo do serviço" />
      </Form.Item>

      <Form.Item
        label="Empresa"
        name="company"
      >
        <Input placeholder="Nome da empresa" />
      </Form.Item>

      <Form.Item
        label="Ambiente"
        name="env"
      >
        <Select
          placeholder="Selecione o ambiente"
          options={[
            { value: 'prod', label: 'Produção' },
            { value: 'dev', label: 'Desenvolvimento' },
            { value: 'test', label: 'Teste' },
          ]}
        />
      </Form.Item>
    </Form>
  );
};

export default DynamicServiceForm;

