import React, { useState } from 'react';
import { Form, Input, Button, Select, Card, Steps, message, Typography } from 'antd';
import { CloudServerOutlined, UserOutlined, KeyOutlined } from '@ant-design/icons';

const { Step } = Steps;
const { Option } = Select;
const { Title, Paragraph, Text } = Typography;

const Installer: React.FC = () => {
  const [currentStep, setCurrentStep] = useState(0);
  const [form] = Form.useForm();
  const [installing, setInstalling] = useState(false);
  const [logs, setLogs] = useState<string[]>([]);

  const onFinish = async (values: any) => {
    setInstalling(true);
    setLogs(['🔍 Conectando ao servidor...']);
    
    // Simular instalação
    setTimeout(() => {
      setLogs(prev => [...prev, '✅ Conexão estabelecida']);
    }, 1000);
    
    setTimeout(() => {
      setLogs(prev => [...prev, '📦 Baixando exporter...']);
    }, 2000);
    
    setTimeout(() => {
      setLogs(prev => [...prev, '✅ Instalação concluída!']);
      setInstalling(false);
      message.success('Exporter instalado com sucesso!');
    }, 3000);
  };

  return (
    <div style={{ padding: 24 }}>
      <Card>
        <Title level={3}>Instalação Remota de Exporters</Title>
        <Paragraph>
          Instale Node Exporter (Linux) ou Windows Exporter remotamente via SSH.
        </Paragraph>
        
        <Steps current={currentStep} style={{ marginBottom: 24 }}>
          <Step title="Conexão" icon={<CloudServerOutlined />} />
          <Step title="Configuração" icon={<UserOutlined />} />
          <Step title="Instalação" icon={<KeyOutlined />} />
        </Steps>

        <Form
          form={form}
          layout="vertical"
          onFinish={onFinish}
          style={{ maxWidth: 600 }}
        >
          <Form.Item
            name="host"
            label="IP/Hostname"
            rules={[{ required: true, message: 'Digite o IP ou hostname' }]}
          >
            <Input placeholder="Ex: 192.168.1.100" />
          </Form.Item>

          <Form.Item
            name="port"
            label="Porta SSH"
            initialValue="22"
            rules={[{ required: true }]}
          >
            <Input placeholder="22" />
          </Form.Item>

          <Form.Item
            name="username"
            label="Usuário"
            rules={[{ required: true }]}
          >
            <Input placeholder="root" />
          </Form.Item>

          <Form.Item
            name="authType"
            label="Tipo de Autenticação"
            rules={[{ required: true }]}
          >
            <Select placeholder="Selecione">
              <Option value="password">Senha</Option>
              <Option value="key">Chave SSH</Option>
            </Select>
          </Form.Item>

          <Form.Item
            name="password"
            label="Senha"
            rules={[{ required: true }]}
          >
            <Input.Password />
          </Form.Item>

          <Form.Item>
            <Button type="primary" htmlType="submit" loading={installing}>
              Iniciar Instalação
            </Button>
          </Form.Item>
        </Form>

        {logs.length > 0 && (
          <Card style={{ backgroundColor: '#1d1d1d', marginTop: 16 }}>
            {logs.map((log, index) => (
              <div key={index}>
                <Text style={{ color: '#00ff00', fontFamily: 'monospace' }}>
                  {log}
                </Text>
              </div>
            ))}
          </Card>
        )}
      </Card>
    </div>
  );
};

export default Installer;