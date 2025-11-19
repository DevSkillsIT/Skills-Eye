/**
 * DynamicCRUDModal - Modal Dinâmico de Criação/Edição de Serviços de Monitoramento
 *
 * SPRINT 2: Componente para CRUD dinâmico de serviços nas páginas monitoring/*
 *
 * CARACTERÍSTICAS:
 * ✅ Seleção de nó Consul primeiro (obrigatório)
 * ✅ Carregamento dinâmico de tipos disponíveis (monitoring-types)
 * ✅ Carregamento de form_schema baseado em exporter_type
 * ✅ Renderização dinâmica de campos específicos do exporter
 * ✅ Renderização dinâmica de campos metadata genéricos
 * ✅ Auto-cadastro de valores (useBatchEnsure + useServiceTags)
 * ✅ Validação de campos obrigatórios
 * ✅ Suporte a modo create e edit
 *
 * USO:
 *   <DynamicCRUDModal
 *     mode="create"
 *     category="network-probes"
 *     visible={true}
 *     onSuccess={() => {}}
 *     onCancel={() => {}}
 *   />
 *
 * AUTOR: Sprint 2 - CRUD Dinâmico
 * DATA: 2025-11-18
 */

import React, { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import {
  Modal,
  Form,
  Select,
  Input,
  InputNumber,
  Button,
  Space,
  Tabs,
  message,
  Alert,
  Spin,
  Tooltip,
  Typography,
} from 'antd';
import {
  InfoCircleOutlined,
  LoadingOutlined,
  CheckCircleOutlined,
} from '@ant-design/icons';
import axios from 'axios';
import { consulAPI } from '../services/api';
import { useFilterFields } from '../hooks/useMetadataFields';
import { useBatchEnsure } from '../hooks/useReferenceValues';
import { useServiceTags } from '../hooks/useServiceTags';
import FormFieldRenderer from './FormFieldRenderer';
import { NodeSelector } from './NodeSelector';
import type { MonitoringDataItem } from '../pages/DynamicMonitoringPage';

const { Text } = Typography;
const { TabPane } = Tabs;
const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:5000/api/v1';

// ============================================================================
// TIPOS E INTERFACES
// ============================================================================

interface DynamicCRUDModalProps {
  mode: 'create' | 'edit';
  category: string;
  service?: MonitoringDataItem | null;
  visible: boolean;
  onSuccess: () => void;
  onCancel: () => void;
}

interface MonitoringType {
  id: string;
  display_name: string;
  job_name: string;
  exporter_type: string;
  module?: string;
  category: string;
  fields?: string[];
  servers?: string[];
  form_schema?: FormSchema;  // ✅ NOVO: form_schema direto no tipo
}

interface FormSchemaField {
  name: string;
  label?: string;
  type: 'text' | 'number' | 'select' | 'password' | 'textarea';
  required?: boolean;
  default?: any;
  placeholder?: string;
  help?: string;
  validation?: {
    min?: number;
    max?: number;
    pattern?: string;
  };
  options?: Array<{ value: string; label: string } | string>;
  min?: number;
  max?: number;
}

interface FormSchema {
  fields: FormSchemaField[];
  required_metadata?: string[];
  optional_metadata?: string[];
}

// ============================================================================
// COMPONENTE PRINCIPAL
// ============================================================================

const DynamicCRUDModal: React.FC<DynamicCRUDModalProps> = ({
  mode,
  category,
  service,
  visible,
  onSuccess,
  onCancel,
}) => {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [step, setStep] = useState<'node' | 'type' | 'form'>('node');
  const [selectedNode, setSelectedNode] = useState<string>('');
  const [availableTypes, setAvailableTypes] = useState<MonitoringType[]>([]);
  const [selectedType, setSelectedType] = useState<string>('');
  const [formSchema, setFormSchema] = useState<FormSchema | null>(null);
  const [loadingTypes, setLoadingTypes] = useState(false);
  const [loadingSchema, setLoadingSchema] = useState(false);
  const [typeError, setTypeError] = useState<string | null>(null);
  
  // ✅ REF para rastrear se é seleção automática inicial do NodeSelector
  const isInitialAutoSelect = useRef(true);
  // ✅ REF para rastrear o último nó que foi selecionado automaticamente
  const lastAutoSelectedNode = useRef<string | null>(null);

  // Hooks para auto-cadastro
  const { filterFields } = useFilterFields(category);
  const { batchEnsure } = useBatchEnsure();
  const { ensureTags } = useServiceTags({ autoLoad: false });

  // Resetar estados quando modal abrir/fechar
  useEffect(() => {
    if (visible) {
      if (mode === 'edit' && service) {
        // Modo edição: preencher form com dados do serviço
        const nodeAddr = service.node_ip || service.Node || '';
        setSelectedNode(nodeAddr);
        
        // Preencher form com dados do serviço
        const meta = service.Meta || {};
        form.setFieldsValue({
          node: nodeAddr,
          service_name: service.Service,
          address: service.Address,
          port: service.Port,
          tags: service.Tags || [],
          ...meta,
        });

        // Detectar exporter_type do serviço
        const exporterType = meta.exporter_type || 
                            meta.job || 
                            service.Service;
        
        // Detectar categoria do serviço (pode estar no meta ou inferir)
        const serviceCategory = meta.category || category;
        
        if (exporterType) {
          setSelectedType(exporterType);
          setStep('form');
          // Carregar form_schema diretamente
          loadFormSchema(exporterType);
        } else {
          // Se não tem exporter_type, ir direto para form
          setStep('form');
        }
      } else {
        // ✅ Modo criação: SEMPRE começar no passo 'node' (seleção de nó Consul)
        console.log('[DynamicCRUDModal] Modo criação - definindo step para "node"');
        setStep('node');
        setSelectedNode('');
        setSelectedType('');
        setAvailableTypes([]);
        setFormSchema(null);
        setTypeError(null);
        form.resetFields();
        // ✅ CRÍTICO: Resetar flags para ignorar primeira seleção automática do NodeSelector
        isInitialAutoSelect.current = true;
        lastAutoSelectedNode.current = null;
      }
    } else {
      // Fechar modal: limpar estados
      setStep('node');
      setSelectedNode('');
      setSelectedType('');
      setFormSchema(null);
      setTypeError(null);
      form.resetFields();
    }
  }, [visible, mode, service, form, category]);

  // Carregar tipos disponíveis quando nó for selecionado
  const loadAvailableTypes = useCallback(async (nodeAddr: string) => {
    if (!nodeAddr || nodeAddr === 'all') {
      setTypeError('Por favor, selecione um nó específico do Consul');
      return;
    }

    setLoadingTypes(true);
    setTypeError(null);

    try {
      // ✅ SPRINT 2: Mapear nó Consul → servidor Prometheus (100% dinâmico do KV)
      // Tipos estão no KV, não precisa fallback de servidores
      const response = await axios.get(`${API_URL}/monitoring-types-dynamic/from-prometheus`, {
        params: {
          consul_node: nodeAddr, // Mapeia nó Consul para servidor Prometheus
        },
        timeout: 30000, // 30s timeout (busca do KV é rápida)
      });

      if (response.data.success) {
        // Filtrar tipos pela categoria atual
        const allTypes: MonitoringType[] = response.data.all_types || [];
        const filteredTypes = allTypes.filter(
          (type) => type.category === category
        );

        if (filteredTypes.length === 0) {
          setTypeError(`Nenhum tipo de monitoramento encontrado para a categoria "${category}" no servidor selecionado`);
        } else {
          setAvailableTypes(filteredTypes);
          setStep('type');
        }
      } else {
        setTypeError('Erro ao carregar tipos de monitoramento');
      }
    } catch (error: any) {
      console.error('[DynamicCRUDModal] Erro ao carregar tipos:', error);
      const errorMsg = error.response?.data?.detail || error.message || 'Erro desconhecido';
      setTypeError(`Erro ao carregar tipos: ${errorMsg}`);
    } finally {
      setLoadingTypes(false);
    }
  }, [category]);

  // ✅ SOLUÇÃO PRAGMÁTICA: Carregar form_schema diretamente do tipo (não de categorization/rules)
  const loadFormSchema = useCallback(async (typeId: string) => {
    if (!typeId) return;

    setLoadingSchema(true);

    try {
      // ✅ NOVO: Buscar form_schema diretamente do tipo selecionado em availableTypes
      const selectedTypeData = availableTypes.find(t => t.id === typeId || t.exporter_type === typeId);

      if (selectedTypeData && selectedTypeData.form_schema) {
        // Tipo tem form_schema configurado
        setFormSchema(selectedTypeData.form_schema as FormSchema);
        setStep('form');
      } else {
        // Tipo não tem form_schema: usar formulário vazio
        console.warn(`[DynamicCRUDModal] Tipo '${typeId}' não tem form_schema configurado`);
        message.info('Este tipo não tem campos customizados. Usando apenas metadata.');
        setFormSchema({ fields: [] });
        setStep('form');
      }
    } catch (error: any) {
      console.error('[DynamicCRUDModal] Erro ao carregar form_schema:', error);
      message.warning('Usando formulário padrão (schema não encontrado)');
      setFormSchema({ fields: [] });
      setStep('form');
    } finally {
      setLoadingSchema(false);
    }
  }, [availableTypes]);  // ✅ Dependência corrigida

  // Handler: Nó selecionado
  const handleNodeSelect = useCallback((nodeAddr: string, node?: any) => {
    console.log('[DynamicCRUDModal] handleNodeSelect chamado:', {
      nodeAddr,
      step,
      selectedNode,
      isInitialAutoSelect: isInitialAutoSelect.current
    });
    
    // ✅ CORREÇÃO CRÍTICA: Ignorar primeira seleção automática do NodeSelector
    // O NodeSelector seleciona automaticamente quando carrega (useEffect linhas 59-77)
    // Mas não queremos que isso avance o passo automaticamente
    if (isInitialAutoSelect.current) {
      console.log('[DynamicCRUDModal] Ignorando seleção automática inicial do NodeSelector:', nodeAddr);
      isInitialAutoSelect.current = false;
      lastAutoSelectedNode.current = nodeAddr; // Guardar qual nó foi selecionado automaticamente
      // ✅ CRÍTICO: Não atualizar selectedNode nem avançar passo
      // Manter selectedNode vazio para que o usuário tenha que selecionar manualmente
      return;
    }
    
    // ✅ CORREÇÃO ADICIONAL: Se o nó selecionado é o mesmo que foi selecionado automaticamente
    // E selectedNode ainda está vazio, significa que é uma segunda chamada da seleção automática
    // Ignorar também
    if (!selectedNode && lastAutoSelectedNode.current === nodeAddr) {
      console.log('[DynamicCRUDModal] Ignorando segunda chamada da seleção automática:', nodeAddr);
      return;
    }
    
    // ✅ Validações normais
    if (!nodeAddr || nodeAddr === 'all') {
      setSelectedNode('');
      setTypeError('Por favor, selecione um nó específico do Consul');
      return;
    }
    
    // ✅ Só processar se estiver no passo 'node'
    if (step !== 'node') {
      console.log('[DynamicCRUDModal] Ignorando seleção - não está no passo node, step atual:', step);
      return;
    }
    
    // ✅ CRÍTICO: Só processar se selectedNode estava vazio (primeira seleção real do usuário)
    // Se já tinha um nó selecionado, não fazer nada (evita múltiplas chamadas)
    if (selectedNode && selectedNode === nodeAddr) {
      console.log('[DynamicCRUDModal] Ignorando seleção - mesmo nó já selecionado');
      return;
    }
    
    // ✅ Processar seleção do usuário (selectedNode estava vazio)
    console.log('[DynamicCRUDModal] ✅ Processando seleção do usuário:', nodeAddr);
    setSelectedNode(nodeAddr);
    loadAvailableTypes(nodeAddr);
  }, [loadAvailableTypes, step, selectedNode]);

  // Handler: Tipo selecionado
  const handleTypeSelect = useCallback((typeId: string) => {
    setSelectedType(typeId);
    const type = availableTypes.find((t) => t.id === typeId || t.job_name === typeId);
    if (type) {
      loadFormSchema(type.exporter_type);
    }
  }, [availableTypes, loadFormSchema]);

  // Handler: Submit do formulário
  const handleSubmit = useCallback(async () => {
    try {
      const values = await form.validateFields();
      setLoading(true);

      // PASSO 1: AUTO-CADASTRO DE VALORES (igual Services.tsx)
      
      // 1A) Auto-cadastrar TAGS
      if (values.tags && Array.isArray(values.tags) && values.tags.length > 0) {
        try {
          await ensureTags(values.tags);
        } catch (err) {
          console.warn('Erro ao auto-cadastrar tags:', err);
        }
      }

      // 1B) Auto-cadastrar METADATA FIELDS
      const metadataValues: Array<{ fieldName: string; value: string }> = [];
      
      filterFields.forEach((field) => {
        if (field.available_for_registration) {
          const fieldValue = values[field.name];
          if (fieldValue && typeof fieldValue === 'string' && fieldValue.trim()) {
            metadataValues.push({
              fieldName: field.name,
              value: fieldValue.trim(),
            });
          }
        }
      });

      if (metadataValues.length > 0) {
        try {
          await batchEnsure(metadataValues);
          console.log(`[Auto-Cadastro] ${metadataValues.length} valores auto-cadastrados`);
        } catch (err) {
          console.warn('Erro ao auto-cadastrar metadata fields:', err);
        }
      }

      // PASSO 2: PREPARAR PAYLOAD DO SERVIÇO
      const selectedTypeObj = availableTypes.find(
        (t) => t.id === selectedType || t.job_name === selectedType
      );

      // Separar campos específicos do exporter dos metadata genéricos
      const exporterFields: Record<string, any> = {};
      const metadataFields: Record<string, any> = {};

      if (formSchema) {
        formSchema.fields.forEach((field) => {
          if (values[field.name] !== undefined) {
            exporterFields[field.name] = values[field.name];
          }
        });
      }

      // Metadata genéricos (todos os outros campos exceto os básicos)
      const basicFields = ['node', 'service_name', 'address', 'port', 'tags'];
      Object.keys(values).forEach((key) => {
        if (!basicFields.includes(key) && !exporterFields.hasOwnProperty(key)) {
          metadataFields[key] = values[key];
        }
      });

      // Montar payload para o backend
      // ⚠️ CRÍTICO: Campo 'name' é sempre obrigatório (vem do metadata fields)
      if (!values.name && !metadataFields.name) {
        message.error('Campo "name" é obrigatório');
        return;
      }

      const payload: any = {
        name: values.name || metadataFields.name || selectedTypeObj?.job_name || 'service',
        service: selectedTypeObj?.job_name || values.service_name || 'blackbox',
        address: values.address || '',
        port: values.port || 9115,
        node_addr: selectedNode,
        tags: values.tags || [],
        Meta: {
          ...exporterFields,
          ...metadataFields,
          name: values.name || metadataFields.name, // Garantir que name está no Meta
          exporter_type: selectedTypeObj?.exporter_type,
          module: selectedTypeObj?.module || exporterFields.module,
        },
      };

      // PASSO 3: SALVAR SERVIÇO
      if (mode === 'create') {
        await consulAPI.createService(payload);
        message.success('Serviço criado com sucesso!');
      } else if (service) {
        await consulAPI.updateService(service.ID, {
          address: payload.address,
          port: payload.port,
          tags: payload.tags,
          Meta: payload.Meta,
          node_addr: selectedNode,
        });
        message.success('Serviço atualizado com sucesso!');
      }

      // Fechar modal e recarregar dados
      form.resetFields();
      onSuccess();
    } catch (error: any) {
      console.error('[DynamicCRUDModal] Erro ao salvar:', error);
      const detailMessage =
        error?.response?.data?.detail?.detail ||
        error?.response?.data?.detail?.message ||
        error?.response?.data?.detail ||
        error?.message ||
        'Erro desconhecido';
      message.error(`Falha ao salvar serviço: ${detailMessage}`);
    } finally {
      setLoading(false);
    }
  }, [form, mode, service, selectedNode, selectedType, availableTypes, formSchema, filterFields, batchEnsure, ensureTags, onSuccess]);

  // Renderizar campos do form_schema (exporter_fields)
  const renderExporterFields = useMemo(() => {
    if (!formSchema || !formSchema.fields || formSchema.fields.length === 0) {
      return null;
    }

    return formSchema.fields.map((field) => {
      const rules: any[] = [];
      if (field.required) {
        rules.push({
          required: true,
          message: `${field.label || field.name} é obrigatório`,
        });
      }

      let inputComponent: React.ReactNode;

      switch (field.type) {
        case 'select':
          const options = field.options?.map((opt) =>
            typeof opt === 'string' ? { value: opt, label: opt } : opt
          ) || [];
          inputComponent = (
            <Select
              placeholder={field.placeholder || `Selecione ${field.label || field.name}`}
              options={options}
            />
          );
          break;

        case 'number':
          inputComponent = (
            <InputNumber
              placeholder={field.placeholder}
              min={field.min}
              max={field.max}
              style={{ width: '100%' }}
            />
          );
          break;

        case 'password':
          inputComponent = (
            <Input.Password placeholder={field.placeholder} />
          );
          break;

        case 'textarea':
          inputComponent = (
            <Input.TextArea
              placeholder={field.placeholder}
              rows={4}
            />
          );
          break;

        default:
          inputComponent = (
            <Input placeholder={field.placeholder} />
          );
      }

      return (
        <Form.Item
          key={field.name}
          name={field.name}
          label={
            <Space size="small">
              <span>{field.label || field.name}</span>
              {(field.help || field.required) && (
                <Tooltip 
                  title={
                    <div>
                      {field.help && <div>{field.help}</div>}
                      {field.required && <div style={{ marginTop: 4, fontWeight: 'bold' }}>Campo obrigatório</div>}
                      {field.validation?.pattern && (
                        <div style={{ marginTop: 4, fontSize: '11px' }}>
                          Validação: {field.validation.pattern}
                        </div>
                      )}
                    </div>
                  }
                >
                  <InfoCircleOutlined style={{ color: field.required ? '#ff4d4f' : '#1890ff' }} />
                </Tooltip>
              )}
            </Space>
          }
          rules={rules}
          initialValue={field.default}
          tooltip={field.help}
        >
          {inputComponent}
        </Form.Item>
      );
    });
  }, [formSchema]);

  // Renderizar campos metadata genéricos
  const renderMetadataFields = useMemo(() => {
    return filterFields.map((field) => (
      <FormFieldRenderer
        key={field.name}
        field={field}
        mode={mode}
      />
    ));
  }, [filterFields, mode]);

  // Determinar título do modal
  const modalTitle = mode === 'create' ? 'Criar Novo Serviço' : 'Editar Serviço';

  // Determinar botão de submit
  const submitButtonText = mode === 'create' ? 'Criar Serviço' : 'Atualizar Serviço';

  // Debug: log do step atual
  useEffect(() => {
    console.log('[DynamicCRUDModal] Step atual:', step, 'Mode:', mode, 'Visible:', visible);
  }, [step, mode, visible]);

  return (
    <Modal
      title={modalTitle}
      open={visible}
      onCancel={onCancel}
      width={900}
      footer={null}
      destroyOnClose
    >
      <Form
        form={form}
        layout="vertical"
        onFinish={handleSubmit}
      >
        {/* PASSO 1: Seleção de Nó */}
        {step === 'node' && (
          <Space direction="vertical" size="large" style={{ width: '100%' }}>
            <Alert
              message="Seleção de Nó Consul"
              description={
                <div>
                  <Text>
                    Selecione o nó do Consul onde o serviço será registrado.
                    <br />
                    <Text type="secondary" style={{ fontSize: '12px' }}>
                      ⚠️ Tipos disponíveis variam por servidor Prometheus associado ao nó.
                    </Text>
                  </Text>
                </div>
              }
              type="info"
              showIcon
            />

            <Form.Item
              name="node"
              label="Nó do Consul"
              rules={[{ required: true, message: 'Selecione um nó do Consul' }]}
            >
              <NodeSelector
                value={selectedNode || undefined}
                onChange={handleNodeSelect}
                showAllNodesOption={false}
                style={{ width: '100%' }}
                placeholder="Selecione um nó do Consul"
              />
            </Form.Item>

            {loadingTypes && (
              <div style={{ textAlign: 'center', padding: '20px' }}>
                <Spin indicator={<LoadingOutlined spin />} />
                <div style={{ marginTop: 8 }}>Carregando tipos disponíveis...</div>
              </div>
            )}

            {typeError && (
              <Alert
                message="Erro ao carregar tipos"
                description={typeError}
                type="error"
                showIcon
              />
            )}
          </Space>
        )}

        {/* PASSO 2: Seleção de Tipo */}
        {step === 'type' && (
          <Space direction="vertical" size="large" style={{ width: '100%' }}>
            <Alert
              message="Seleção de Tipo de Monitoramento"
              description="Escolha o tipo de monitoramento que deseja criar."
              type="info"
              showIcon
            />

            <Form.Item
              name="service_name"
              label="Tipo de Monitoramento"
              rules={[{ required: true, message: 'Selecione um tipo de monitoramento' }]}
            >
              <Select
                placeholder="Selecione o tipo de monitoramento"
                value={selectedType}
                onChange={handleTypeSelect}
                loading={loadingTypes}
                showSearch
                filterOption={(input, option) =>
                  (option?.label ?? '').toLowerCase().includes(input.toLowerCase())
                }
                options={availableTypes.map((type) => ({
                  value: type.id || type.job_name,
                  label: (
                    <Space>
                      <span>{type.display_name}</span>
                      <Text type="secondary" style={{ fontSize: '12px' }}>
                        ({type.exporter_type})
                      </Text>
                    </Space>
                  ),
                }))}
              />
            </Form.Item>

            {loadingSchema && (
              <div style={{ textAlign: 'center', padding: '20px' }}>
                <Spin indicator={<LoadingOutlined spin />} />
                <div style={{ marginTop: 8 }}>Carregando configuração do formulário...</div>
              </div>
            )}
          </Space>
        )}

        {/* PASSO 3: Formulário Completo */}
        {step === 'form' && (
          <Tabs defaultActiveKey="exporter">
            {/* Aba: Campos Específicos do Exporter */}
            <TabPane
              tab={
                <Space>
                  <span>Configuração do Exporter</span>
                  {formSchema && formSchema.fields.length > 0 && (
                    <CheckCircleOutlined style={{ color: '#52c41a' }} />
                  )}
                </Space>
              }
              key="exporter"
            >
              <Space direction="vertical" size="middle" style={{ width: '100%' }}>
                {formSchema && formSchema.fields.length > 0 ? (
                  <>
                    <Alert
                      message="Campos Específicos do Exporter"
                      description="Configure os parâmetros específicos deste tipo de exporter."
                      type="info"
                      showIcon
                      style={{ marginBottom: 16 }}
                    />
                    {renderExporterFields}
                  </>
                ) : (
                  <Alert
                    message="Nenhum campo específico"
                    description="Este tipo de exporter não possui campos específicos configurados."
                    type="info"
                    showIcon
                  />
                )}
              </Space>
            </TabPane>

            {/* Aba: Metadata Genéricos */}
            <TabPane
              tab={
                <Space>
                  <span>Metadata</span>
                  {filterFields.length > 0 && (
                    <CheckCircleOutlined style={{ color: '#52c41a' }} />
                  )}
                </Space>
              }
              key="metadata"
            >
              <Space direction="vertical" size="middle" style={{ width: '100%' }}>
                <Alert
                  message="Campos de Metadata"
                  description="Configure os campos de metadata genéricos do serviço."
                  type="info"
                  showIcon
                  style={{ marginBottom: 16 }}
                />
                {renderMetadataFields}
              </Space>
            </TabPane>

            {/* Aba: Configurações Básicas */}
            <TabPane tab="Configurações Básicas" key="basic">
              <Space direction="vertical" size="middle" style={{ width: '100%' }}>
                <Alert
                  message="Configurações Básicas do Serviço"
                  description="Configure os parâmetros básicos de conexão e identificação do serviço."
                  type="info"
                  showIcon
                  style={{ marginBottom: 16 }}
                />
                
                <Form.Item
                  name="address"
                  label={
                    <Space size="small">
                      <span>Endereço IP ou Hostname</span>
                      <Tooltip title="IP ou hostname do alvo a ser monitorado. Exemplo: 192.168.1.1 ou exemplo.com">
                        <InfoCircleOutlined style={{ color: '#1890ff' }} />
                      </Tooltip>
                    </Space>
                  }
                  rules={[{ required: true, message: 'Endereço é obrigatório' }]}
                >
                  <Input placeholder="192.168.1.1 ou exemplo.com" />
                </Form.Item>

                <Form.Item
                  name="port"
                  label={
                    <Space size="small">
                      <span>Porta</span>
                      <Tooltip title="Porta do exporter. Padrões: Blackbox=9115, Node=9100, Windows=9182, SNMP=9116">
                        <InfoCircleOutlined style={{ color: '#1890ff' }} />
                      </Tooltip>
                    </Space>
                  }
                  rules={[{ required: true, message: 'Porta é obrigatória' }]}
                >
                  <InputNumber 
                    min={1} 
                    max={65535} 
                    style={{ width: '100%' }}
                    placeholder="9115"
                  />
                </Form.Item>

                <Form.Item
                  name="tags"
                  label={
                    <Space size="small">
                      <span>Tags</span>
                      <Tooltip title="Tags para organização e filtros no Prometheus. Exemplo: ['icmp', 'network', 'prod']. Tags são usadas para agrupar e filtrar serviços no Prometheus.">
                        <InfoCircleOutlined style={{ color: '#1890ff' }} />
                      </Tooltip>
                    </Space>
                  }
                >
                  <Select
                    mode="tags"
                    placeholder="Digite tags e pressione Enter"
                    style={{ width: '100%' }}
                  />
                </Form.Item>
              </Space>
            </TabPane>
          </Tabs>
        )}

        {/* Footer com botões */}
        <div style={{ marginTop: 24, textAlign: 'right' }}>
          <Space>
            <Button onClick={onCancel}>Cancelar</Button>
            {step === 'form' && (
              <Button type="primary" htmlType="submit" loading={loading}>
                {submitButtonText}
              </Button>
            )}
          </Space>
        </div>
      </Form>
    </Modal>
  );
};

export default DynamicCRUDModal;

