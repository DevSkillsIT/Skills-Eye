import React from 'react';
import { Form, Input, Select, Switch, Card, Space, Typography, Divider } from 'antd';
import { LinuxOutlined, WindowsOutlined } from '@ant-design/icons';
import type { InstallFormData } from '../types';
import { CollectorSelector } from './CollectorSelector';

const { Text } = Typography;
const { Option } = Select;

export interface InstallFormProps {
  form: any;
  onValuesChange?: (changedValues: any, allValues: InstallFormData) => void;
  disabled?: boolean;
}

export const InstallForm: React.FC<InstallFormProps> = ({
  form,
  onValuesChange,
  disabled = false,
}) => {
  const targetType = Form.useWatch('targetType', form);
  const connectionMethod = Form.useWatch('connectionMethod', form);

  return (
    <Form
      form={form}
      layout="vertical"
      onValuesChange={onValuesChange}
      disabled={disabled}
      initialValues={{
        targetType: 'linux',
        connectionMethod: 'ssh',
        port: 22,
        exporterPort: 9100,
        enableBasicAuth: false,
        selectedCollectors: [],
        autoRegisterConsul: true,
      }}
    >
      {/* Target Type */}
      <Form.Item
        name="targetType"
        label="Tipo de Alvo"
        rules={[{ required: true, message: 'Selecione o tipo de sistema' }]}
      >
        <Select size="large">
          <Option value="linux">
            <Space>
              <LinuxOutlined />
              <span>Linux (Node Exporter)</span>
            </Space>
          </Option>
          <Option value="windows">
            <Space>
              <WindowsOutlined />
              <span>Windows (Windows Exporter)</span>
            </Space>
          </Option>
        </Select>
      </Form.Item>

      <Divider />

      {/* Connection Details */}
      <Card title="Conexão" size="small" style={{ marginBottom: 16 }}>
        <Form.Item
          name="host"
          label="Host"
          rules={[
            { required: true, message: 'Host obrigatório' },
            {
              pattern: /^[a-zA-Z0-9.-]+$/,
              message: 'Host inválido (apenas letras, números, . e -)',
            },
          ]}
        >
          <Input placeholder="192.168.1.10 ou hostname.local" />
        </Form.Item>

        {targetType === 'windows' && (
          <Form.Item
            name="connectionMethod"
            label="Método de Conexão"
            rules={[{ required: true }]}
          >
            <Select>
              <Option value="ssh">SSH (OpenSSH for Windows)</Option>
              <Option value="fallback">
                Auto (PSExec → WinRM → SSH)
              </Option>
            </Select>
          </Form.Item>
        )}

        <Space style={{ width: '100%' }} size="large">
          <Form.Item
            name="port"
            label="Porta"
            rules={[
              { required: true, message: 'Porta obrigatória' },
              {
                type: 'number',
                min: 1,
                max: 65535,
                message: 'Porta inválida (1-65535)',
              },
            ]}
          >
            <Input type="number" placeholder="22" style={{ width: 120 }} />
          </Form.Item>

          <Form.Item
            name="exporterPort"
            label="Porta do Exporter"
            rules={[
              { required: true },
              { type: 'number', min: 1, max: 65535 },
            ]}
          >
            <Input
              type="number"
              placeholder={targetType === 'linux' ? '9100' : '9182'}
              style={{ width: 120 }}
            />
          </Form.Item>
        </Space>

        <Form.Item
          name="username"
          label="Usuário"
          rules={[{ required: true, message: 'Usuário obrigatório' }]}
        >
          <Input placeholder="root / Administrator" />
        </Form.Item>

        <Form.Item
          name="password"
          label="Senha"
          rules={[{ required: true, message: 'Senha obrigatória' }]}
        >
          <Input.Password placeholder="••••••••" />
        </Form.Item>

        {targetType === 'windows' && connectionMethod !== 'ssh' && (
          <Form.Item name="domain" label="Domínio (opcional)">
            <Input placeholder="DOMAIN (para contas de domínio)" />
          </Form.Item>
        )}
      </Card>

      {/* Collectors */}
      <Card title="Coletores" size="small" style={{ marginBottom: 16 }}>
        <Form.Item name="selectedCollectors" noStyle>
          <CollectorSelector targetType={targetType} />
        </Form.Item>
      </Card>

      {/* Basic Auth */}
      <Card title="Basic Authentication" size="small" style={{ marginBottom: 16 }}>
        <Form.Item
          name="enableBasicAuth"
          label="Habilitar Basic Auth"
          valuePropName="checked"
        >
          <Switch />
        </Form.Item>

        <Form.Item noStyle shouldUpdate>
          {({ getFieldValue }) => {
            const enabled = getFieldValue('enableBasicAuth');
            if (!enabled) return null;

            return (
              <>
                <Text type="secondary" style={{ display: 'block', marginBottom: 12 }}>
                  Protege o endpoint /metrics com autenticação HTTP Basic
                </Text>
                <Form.Item
                  name="basicAuthUser"
                  label="Usuário"
                  rules={[
                    { required: enabled, message: 'Usuário obrigatório' },
                  ]}
                >
                  <Input placeholder="prometheus" />
                </Form.Item>

                <Form.Item
                  name="basicAuthPassword"
                  label="Senha"
                  rules={[
                    { required: enabled, message: 'Senha obrigatória' },
                    { min: 8, message: 'Mínimo 8 caracteres' },
                  ]}
                >
                  <Input.Password placeholder="••••••••" />
                </Form.Item>
              </>
            );
          }}
        </Form.Item>
      </Card>

      {/* Consul Registration */}
      <Card title="Registro no Consul" size="small">
        <Form.Item
          name="autoRegisterConsul"
          label="Registrar automaticamente após instalação"
          valuePropName="checked"
        >
          <Switch />
        </Form.Item>

        <Form.Item noStyle shouldUpdate>
          {({ getFieldValue }) => {
            const autoRegister = getFieldValue('autoRegisterConsul');
            if (!autoRegister) return null;

            return (
              <>
                <Form.Item
                  name="consulServiceName"
                  label="Nome do Serviço"
                  rules={[
                    { required: autoRegister, message: 'Nome obrigatório' },
                  ]}
                >
                  <Input placeholder={`${targetType}-exporter`} />
                </Form.Item>

                <Form.Item name="consulTags" label="Tags (opcional)">
                  <Select
                    mode="tags"
                    placeholder="production, monitoring, etc."
                  />
                </Form.Item>
              </>
            );
          }}
        </Form.Item>
      </Card>
    </Form>
  );
};
