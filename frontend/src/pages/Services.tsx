import React, { useEffect, useState } from 'react';
import { Table, Button, Space, message, Popconfirm, Input, Modal, Form, Select } from 'antd';
import { PlusOutlined, EditOutlined, DeleteOutlined, SearchOutlined } from '@ant-design/icons';
import { consulAPI } from '../services/api';

const { Option } = Select;

// Available modules from backend config
const BLACKBOX_MODULES = [
  { value: 'icmp', label: 'ICMP - Ping', description: 'Verifica conectividade básica (ping)' },
  { value: 'http_2xx', label: 'HTTP 2xx', description: 'Site HTTP sem SSL (espera código 2xx)' },
  { value: 'http_4xx', label: 'HTTP 4xx', description: 'Site HTTP (espera código 4xx)' },
  { value: 'https', label: 'HTTPS', description: 'Site com SSL/TLS' },
  { value: 'http_post_2xx', label: 'HTTP POST 2xx', description: 'Requisição HTTP POST' },
  { value: 'tcp_connect', label: 'TCP Connect', description: 'Conexão TCP em porta específica' },
  { value: 'ssh_banner', label: 'SSH Banner', description: 'Verificação de banner SSH' },
  { value: 'pop3s_banner', label: 'POP3S Banner', description: 'Verificação de banner POP3S' },
  { value: 'irc_banner', label: 'IRC Banner', description: 'Verificação de banner IRC' },
];

const Services: React.FC = () => {
  const [services, setServices] = useState([]);
  const [loading, setLoading] = useState(false);
  const [searchText, setSearchText] = useState('');
  const [isModalVisible, setIsModalVisible] = useState(false);
  const [form] = Form.useForm();

  useEffect(() => {
    fetchServices();
  }, []);

  const fetchServices = async () => {
    setLoading(true);
    try {
      const response = await consulAPI.getServices();
      const servicesArray = Object.entries(response.data.data || {}).map(([id, service]: any) => ({
        id,
        ...service,
        ...service.Meta
      }));
      setServices(servicesArray);
    } catch (error) {
      message.error('Erro ao carregar serviços');
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await consulAPI.deleteService(id);
      message.success('Serviço removido com sucesso');
      fetchServices();
    } catch (error) {
      message.error('Erro ao remover serviço');
    }
  };

  const showModal = () => {
    setIsModalVisible(true);
  };

  const handleCancel = () => {
    setIsModalVisible(false);
    form.resetFields();
  };

  const handleOk = async () => {
    try {
      const values = await form.validateFields();
      setLoading(true);

      // Generate service ID from metadata
      const serviceId = `${values.module}/${values.company}/${values.project}/${values.env}@${values.name}_${values.instance.replace(/[^a-zA-Z0-9]/g, '_')}`;

      // Prepare metadata
      const metadata: any = {
        module: values.module,
        company: values.company,
        project: values.project,
        env: values.env,
        name: values.name,
        instance: values.instance,
      };

      // Add optional fields if provided
      if (values.localizacao) metadata.localizacao = values.localizacao;
      if (values.tipo) metadata.tipo = values.tipo;
      if (values.cod_localidade) metadata.cod_localidade = values.cod_localidade;
      if (values.cidade) metadata.cidade = values.cidade;
      if (values.provedor) metadata.provedor = values.provedor;
      if (values.fabricante) metadata.fabricante = values.fabricante;
      if (values.modelo) metadata.modelo = values.modelo;
      if (values.tipo_dispositivo_abrev) metadata.tipo_dispositivo_abrev = values.tipo_dispositivo_abrev;
      if (values.glpi_url) metadata.glpi_url = values.glpi_url;
      if (values.notas) metadata.notas = values.notas;

      // Format request according to backend ServiceCreateRequest
      const serviceData = {
        id: serviceId,
        name: `${values.module}_${values.company}_${values.project}_${values.env}`,
        tags: [values.module, values.company, values.env],
        Meta: metadata,
      };

      // Call API to create service
      await consulAPI.createService(serviceData);

      message.success('Serviço adicionado com sucesso!');
      setIsModalVisible(false);
      form.resetFields();
      fetchServices();
    } catch (error: any) {
      if (error.errorFields) {
        message.error('Por favor, preencha todos os campos obrigatórios');
      } else {
        message.error('Erro ao adicionar serviço: ' + (error.response?.data?.detail || error.message));
      }
    } finally {
      setLoading(false);
    }
  };

  const columns = [
    {
      title: 'Name',
      dataIndex: 'name',
      key: 'name',
    },
    {
      title: 'Module',
      dataIndex: 'module',
      key: 'module',
    },
    {
      title: 'Instance',
      dataIndex: 'instance',
      key: 'instance',
    },
    {
      title: 'Company',
      dataIndex: 'company',
      key: 'company',
    },
    {
      title: 'Environment',
      dataIndex: 'env',
      key: 'env',
    },
    {
      title: 'Ações',
      key: 'action',
      render: (_: any, record: any) => (
        <Space size="middle">
          <Button icon={<EditOutlined />} size="small" />
          <Popconfirm
            title="Confirma a exclusão?"
            onConfirm={() => handleDelete(record.id)}
          >
            <Button danger icon={<DeleteOutlined />} size="small" />
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <div style={{ padding: 24 }}>
      <div style={{ marginBottom: 16 }}>
        <Space>
          <Button type="primary" icon={<PlusOutlined />} onClick={showModal}>
            Adicionar Serviço
          </Button>
          <Input
            placeholder="Buscar serviços"
            prefix={<SearchOutlined />}
            onChange={(e) => setSearchText(e.target.value)}
            style={{ width: 200 }}
          />
        </Space>
      </div>
      <Table
        columns={columns}
        dataSource={services}
        loading={loading}
        rowKey="id"
      />

      <Modal
        title="Adicionar Novo Serviço"
        open={isModalVisible}
        onOk={handleOk}
        onCancel={handleCancel}
        width={800}
        confirmLoading={loading}
        okText="Adicionar"
        cancelText="Cancelar"
      >
        <Form
          form={form}
          layout="vertical"
          name="add_service_form"
        >
          <Form.Item
            name="module"
            label="Módulo de Monitoramento"
            rules={[{ required: true, message: 'Por favor, selecione o módulo!' }]}
            tooltip="Tipo de verificação que será realizada"
          >
            <Select
              placeholder="Selecione o tipo de monitoramento"
              showSearch
              optionFilterProp="children"
            >
              {BLACKBOX_MODULES.map((module) => (
                <Option key={module.value} value={module.value}>
                  <div>
                    <strong>{module.label}</strong>
                    <div style={{ fontSize: '12px', color: '#888' }}>{module.description}</div>
                  </div>
                </Option>
              ))}
            </Select>
          </Form.Item>

          <Form.Item
            name="company"
            label="Empresa"
            rules={[{ required: true, message: 'Por favor, informe a empresa!' }]}
          >
            <Input placeholder="Ex: SkillsIT, ClienteX" />
          </Form.Item>

          <Form.Item
            name="project"
            label="Projeto"
            rules={[{ required: true, message: 'Por favor, informe o projeto!' }]}
          >
            <Input placeholder="Ex: Monitor, API, Infrastructure" />
          </Form.Item>

          <Form.Item
            name="env"
            label="Ambiente"
            rules={[{ required: true, message: 'Por favor, informe o ambiente!' }]}
          >
            <Select placeholder="Selecione o ambiente">
              <Option value="Prod">Produção (Prod)</Option>
              <Option value="Dev">Desenvolvimento (Dev)</Option>
              <Option value="Homolog">Homologação (Homolog)</Option>
              <Option value="Test">Teste (Test)</Option>
            </Select>
          </Form.Item>

          <Form.Item
            name="name"
            label="Nome do Serviço"
            rules={[{ required: true, message: 'Por favor, informe o nome!' }]}
            tooltip="Nome descritivo do serviço ou recurso"
          >
            <Input placeholder="Ex: gateway, api_principal, servidor_web" />
          </Form.Item>

          <Form.Item
            name="instance"
            label="Instance (IP/URL/Hostname)"
            rules={[{ required: true, message: 'Por favor, informe a instância!' }]}
            tooltip="Endereço IP, URL ou hostname do recurso a ser monitorado"
          >
            <Input placeholder="Ex: 192.168.1.1, http://example.com, server.domain.com" />
          </Form.Item>

          <Form.Item
            name="localizacao"
            label="Localização"
          >
            <Input placeholder="Ex: Datacenter Principal, Escritório São Paulo" />
          </Form.Item>

          <Form.Item
            name="tipo"
            label="Tipo"
          >
            <Input placeholder="Ex: Router, Switch, Server, Website" />
          </Form.Item>

          <Form.Item
            name="cod_localidade"
            label="Código da Localidade"
          >
            <Input placeholder="Ex: SP01, RJ02" />
          </Form.Item>

          <Form.Item
            name="cidade"
            label="Cidade"
          >
            <Input placeholder="Ex: São Paulo, Rio de Janeiro" />
          </Form.Item>

          <Form.Item
            name="provedor"
            label="Provedor"
          >
            <Input placeholder="Ex: AWS, Azure, OVH" />
          </Form.Item>

          <Form.Item
            name="fabricante"
            label="Fabricante"
          >
            <Input placeholder="Ex: Cisco, Dell, HP" />
          </Form.Item>

          <Form.Item
            name="modelo"
            label="Modelo"
          >
            <Input placeholder="Ex: Catalyst 2960, PowerEdge R740" />
          </Form.Item>

          <Form.Item
            name="tipo_dispositivo_abrev"
            label="Tipo de Dispositivo (Abreviação)"
          >
            <Input placeholder="Ex: RTR, SWT, SRV" />
          </Form.Item>

          <Form.Item
            name="glpi_url"
            label="URL GLPI"
          >
            <Input placeholder="Ex: http://glpi.example.com/item/123" />
          </Form.Item>

          <Form.Item
            name="notas"
            label="Notas"
          >
            <Input.TextArea
              rows={3}
              placeholder="Informações adicionais sobre o serviço"
            />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default Services;