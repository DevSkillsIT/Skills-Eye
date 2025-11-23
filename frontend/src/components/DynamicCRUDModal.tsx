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
  message,
  Alert,
  Spin,
  Typography,
  Row,
  Col,
  Switch,
  Steps,
  theme,
  Divider,
  Tag,
} from 'antd';
import {
  InfoCircleOutlined,
  LoadingOutlined,
  ArrowLeftOutlined,
  CloudServerOutlined,
  EditOutlined,
} from '@ant-design/icons';
import axios from 'axios';
import { consulAPI } from '../services/api';
import { useFormFields } from '../hooks/useMetadataFields';
import { useBatchEnsure } from '../hooks/useReferenceValues';
import { useServiceTags } from '../hooks/useServiceTags';
import FormFieldRenderer from './FormFieldRenderer';
import TagsInput from './TagsInput';
import { NodeSelector } from './NodeSelector';
import FloatingFormField from './FloatingFormField';
import type { MonitoringDataItem } from '../types/monitoring';

const { Text } = Typography;
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
  server?: string;         // Servidor único (retornado pelo backend)
  servers?: string[];      // Array de servidores (quando tipo está em múltiplos servidores)
  form_schema?: FormSchema;  // form_schema direto no tipo
}

interface FormSchemaField {
  name: string;
  label?: string;
  type: 'text' | 'number' | 'select' | 'password' | 'textarea' | 'tags' | 'checkbox';
  required?: boolean;
  default?: any;
  placeholder?: string;
  help?: string;
  validation?: {
    min?: number;
    max?: number;
    pattern?: string;
    message?: string;
    type?: 'string' | 'number' | 'boolean' | 'method' | 'regexp' | 'integer' | 'float' | 'object' | 'enum' | 'date' | 'url' | 'hex' | 'email';
  };
  options?: Array<{ value: string; label: string } | string>;
  min?: number;
  max?: number;
  depends_on?: string; // Campo que este campo depende (para campos condicionais)
  col_span?: number;
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
  // ✅ SPRINT 3: Fluxo de 4 steps sequenciais
  const [step, setStep] = useState<'node' | 'type' | 'exporter' | 'metadata'>('node');
  const [selectedNode, setSelectedNode] = useState<string>('');
  const [availableTypes, setAvailableTypes] = useState<MonitoringType[]>([]);
  const [selectedType, setSelectedType] = useState<string>('');
  const [formSchema, setFormSchema] = useState<FormSchema | null>(null);
  const [loadingTypes, setLoadingTypes] = useState(false);
  const [loadingSchema, setLoadingSchema] = useState(false);
  const [typeError, setTypeError] = useState<string | null>(null);
  const [selectedNodeData, setSelectedNodeData] = useState<any>(null);
  const [submittable, setSubmittable] = useState(false);

  // ✅ SPRINT 3: Mapeamento de Steps
  const STEPS = [
    {
      title: 'Selecionar Nó',
      key: 'node',
      description: 'Escolha o servidor',
    },
    {
      title: 'Tipo',
      key: 'type',
      description: 'Selecione o tipo',
    },
    {
      title: 'Configuração',
      key: 'exporter',
      description: 'Dados do exporter',
    },
    {
      title: 'Detalhes',
      key: 'metadata',
      description: 'Metadados e Info',
    },
  ];

  // Mapeamento reverso para índice do Steps
  const currentStepIndex = STEPS.findIndex(s => s.key === step);

  // Tokens de tema para estilização
  const { token } = theme.useToken();

  // Watch all values for validation
  const formValues = Form.useWatch([], form);

  // ✅ REF para rastrear se é seleção automática inicial do NodeSelector
  const isInitialAutoSelect = useRef(true);
  // ✅ REF para rastrear o último nó que foi selecionado automaticamente
  const lastAutoSelectedNode = useRef<string | null>(null);

  // Hooks para campos do formulário (usando useFormFields que filtra por show_in_form=true)
  const { formFields } = useFormFields(category);
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
        // const serviceCategory = meta.category || category;

        if (exporterType) {
          setSelectedType(exporterType);
          // Em modo edição, ir direto para metadata (último step)
          setStep('metadata');
          // Carregar form_schema para ter os campos disponíveis
          loadFormSchema(exporterType);
        } else {
          // Se não tem exporter_type, ir direto para metadata
          setStep('metadata');
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
      // ✅ SPRINT 3: Buscar todos os tipos do KV filtrado por servidor específico
      // O backend já faz o filtro por servidor quando passamos o parâmetro server
      const response = await axios.get(`${API_URL}/monitoring-types-dynamic/from-prometheus`, {
        params: { server: nodeAddr },
        timeout: 30000, // 30s timeout (busca do KV é rápida)
      });

      if (response.data.success) {
        // O backend já filtra por servidor, agora filtrar por categoria no frontend
        const allTypes: MonitoringType[] = response.data.all_types || [];
        const serverInfo = response.data.servers?.[nodeAddr];

        // DEBUG: Verificar estrutura exata recebida
        console.log(`[DynamicCRUDModal] 🔍 ServerInfo para ${nodeAddr}:`, serverInfo);
        console.log(`[DynamicCRUDModal] 🔍 Site Data:`, serverInfo?.site);

        // ✅ ENRIQUECIMENTO DE DADOS DO NÓ
        // Atualizar selectedNodeData com informações precisas do site vindas do backend
        if (serverInfo && serverInfo.site) {
          const isDefault = serverInfo.site.is_default === true; // Garantir booleano
          console.log(`[DynamicCRUDModal] 🌍 Site: ${serverInfo.site.name}, Default/Master: ${isDefault}`);

          setSelectedNodeData((prev: any) => ({
            ...prev, // Manter dados anteriores (addr, tags originais, etc)
            site_name: serverInfo.site.name,
            isMaster: isDefault, // Sobrescrever com a verdade do backend
            type: isDefault ? 'master' : 'slave', // Atualizar tipo para compatibilidade
            tags: {
              ...prev?.tags,
              role: isDefault ? 'master' : 'slave'
            }
          }));
        } else {
          console.warn(`[DynamicCRUDModal] ⚠️ Nenhuma info de site encontrada no backend para ${nodeAddr}. Mantendo dados locais.`);
          // Não resetar selectedNodeData aqui, manter o que veio do NodeSelector
        }

        // DEBUG: Log detalhado dos tipos recebidos
        console.log(`[DynamicCRUDModal] Total tipos recebidos do servidor ${nodeAddr}: ${allTypes.length}`);
        console.log(`[DynamicCRUDModal] Filtrando por categoria='${category}'`);

        // Listar todas as categorias disponíveis para debug
        const availableCategories = [...new Set(allTypes.map(t => t.category))];
        console.log(`[DynamicCRUDModal] Categorias disponíveis neste servidor:`, availableCategories);

        console.log(`[DynamicCRUDModal] Tipos da categoria '${category}':`,
          allTypes.filter(t => t.category === category).map(t => ({
            id: t.id,
            display_name: t.display_name,
            server: t.server,
            servers: t.servers,
            hasSchema: !!t.form_schema
          })));

        // Filtrar apenas por categoria (servidor já filtrado pelo backend)
        const filteredTypes = allTypes.filter((type) => {
          return type.category === category;
        });

        console.log(`[DynamicCRUDModal] ✅ Tipos filtrados para categoria '${category}':`,
          filteredTypes.map(t => ({
            id: t.id,
            display_name: t.display_name,
            hasSchema: !!t.form_schema,
            schemaFields: t.form_schema?.fields?.length || 0
          })));

        if (filteredTypes.length === 0) {
          setTypeError(`Nenhum tipo de monitoramento encontrado para a categoria "${category}" no servidor "${nodeAddr}". Categorias disponíveis: ${availableCategories.join(', ')}`);
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
      console.log(`[DynamicCRUDModal] loadFormSchema chamado para typeId='${typeId}'`);
      console.log(`[DynamicCRUDModal] availableTypes (${availableTypes.length} tipos):`,
        availableTypes.map(t => ({
          id: t.id,
          display_name: t.display_name,
          hasSchema: !!t.form_schema,
          schemaFields: t.form_schema?.fields?.length || 0
        })));

      // Buscar tipo por id, job_name ou exporter_type (múltiplos critérios para garantir match)
      const selectedTypeData = availableTypes.find(t =>
        t.id === typeId ||
        t.job_name === typeId ||
        t.exporter_type === typeId
      );

      if (!selectedTypeData) {
        console.error(`[DynamicCRUDModal] ❌ Tipo '${typeId}' NÃO ENCONTRADO em availableTypes!`);
        console.log(`[DynamicCRUDModal] IDs disponíveis:`, availableTypes.map(t => t.id));
        message.warning(`Tipo '${typeId}' não encontrado. Usando formulário padrão.`);
        setFormSchema({ fields: [] });
        setStep('exporter');
        return;
      }

      console.log(`[DynamicCRUDModal] ✅ Tipo encontrado:`, {
        id: selectedTypeData.id,
        display_name: selectedTypeData.display_name,
        exporter_type: selectedTypeData.exporter_type,
        module: selectedTypeData.module,
        form_schema: selectedTypeData.form_schema,
        hasFields: selectedTypeData.form_schema?.fields?.length || 0
      });

      if (selectedTypeData.form_schema && selectedTypeData.form_schema.fields?.length > 0) {
        // Tipo tem form_schema configurado com campos
        console.log(`[DynamicCRUDModal] ✅ form_schema encontrado para '${typeId}': ${selectedTypeData.form_schema.fields.length} campos`);
        console.log(`[DynamicCRUDModal] Campos do schema:`, selectedTypeData.form_schema.fields.map(f => ({
          name: f.name,
          label: f.label,
          type: f.type,
          required: f.required
        })));
        setFormSchema(selectedTypeData.form_schema as FormSchema);
        // ✅ SPRINT 3: Ir para step 'exporter' (campos do schema)
        setStep('exporter');
      } else {
        // Tipo não tem form_schema: pular direto para metadata
        console.log(`[DynamicCRUDModal] ⚠️ Tipo '${typeId}' sem form_schema configurado`);
        console.log(`[DynamicCRUDModal] ℹ️ Pulando para step metadata (sem campos de exporter)`);
        setFormSchema({ fields: [] });
        // ✅ SPRINT 3: Pular direto para metadata se não tem campos de exporter
        setStep('metadata');
      }
    } catch (error: any) {
      console.error('[DynamicCRUDModal] Erro ao carregar form_schema:', error);
      message.warning('Usando formulário padrão (schema não encontrado)');
      setFormSchema({ fields: [] });
      // ✅ SPRINT 3: Ir direto para metadata em caso de erro
      setStep('metadata');
    } finally {
      setLoadingSchema(false);
    }
  }, [availableTypes]);  // ✅ Dependência corrigida

  // Handler: Nó selecionado - APENAS atualiza o estado, NÃO avança automaticamente
  const handleNodeSelect = useCallback((nodeAddr: string, node?: any) => {
    console.log('[DynamicCRUDModal] handleNodeSelect chamado:', { nodeAddr, node });

    // Apenas atualizar o selectedNode - o botão "Avançar" é quem carrega os tipos
    if (nodeAddr && nodeAddr !== 'all') {
      setSelectedNode(nodeAddr);
      // Se node for passado (do Select.Option), guardamos para o header
      // O NodeSelector geralmente passa { value, label, ... }
      setSelectedNodeData(node);
      setTypeError(null);
    } else {
      setSelectedNode('');
      setSelectedNodeData(null);
    }
  }, []);

  // Handler: Avançar do passo node para type (chamado pelo botão "Avançar")
  const handleAdvanceFromNode = useCallback(async () => {
    if (!selectedNode || selectedNode === 'all') {
      setTypeError('Por favor, selecione um nó específico do Consul');
      return;
    }

    // Carregar tipos e avançar para próximo passo
    await loadAvailableTypes(selectedNode);
  }, [selectedNode, loadAvailableTypes]);

  // Handler: Tipo selecionado
  // ✅ CORREÇÃO: Apenas define o selectedType, não avança automaticamente
  // O botão "Avançar" é responsável por carregar o form_schema e avançar para o passo 'form'
  const handleTypeSelect = useCallback((typeId: string) => {
    console.log('[DynamicCRUDModal] handleTypeSelect chamado:', { typeId });
    setSelectedType(typeId);
    // NÃO chama loadFormSchema aqui - o botão "Avançar" faz isso
  }, []);

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

      formFields.forEach((field) => {
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

      // Identificar campos do formSchema dinamicamente
      const formSchemaFieldNames = new Set<string>();
      if (formSchema && formSchema.fields) {
        formSchema.fields.forEach((field) => {
          formSchemaFieldNames.add(field.name);
        });
      }

      // Separar campos: formSchema → exporterFields, outros → metadataFields
      // Tudo que vem de values vai para Meta (formSchema → exporterFields, outros → metadataFields)
      Object.keys(values).forEach((key) => {
        if (formSchemaFieldNames.has(key)) {
          // Campo do formSchema → exporterFields
          exporterFields[key] = values[key];
        } else {
          // Campo não está no formSchema → metadataFields
          metadataFields[key] = values[key];
        }
      });

      // Montar payload para o backend
      // ⚠️ CRÍTICO: Campo 'name' é sempre obrigatório (vem do metadata fields)
      if (!values.name && !metadataFields.name) {
        message.error('Campo "name" é obrigatório');
        return;
      }

      // ✅ OPÇÃO 1: Remover campos duplicados de metadataFields (formSchema tem prioridade)
      // Isso evita que campos do formSchema sejam sobrescritos por campos genéricos
      const filteredMetadataFields = { ...metadataFields };
      Object.keys(exporterFields).forEach((key) => {
        delete filteredMetadataFields[key];
      });

      const payload: any = {
        name: values.name || metadataFields.name || selectedTypeObj?.job_name,
        service: selectedTypeObj?.job_name || values.service_name,
        address: values.address,
        port: values.port,
        node_addr: selectedNode,
        tags: values.tags,
        Meta: {
          ...exporterFields,           // Prioridade: campos do formSchema
          ...filteredMetadataFields,    // Campos genéricos (sem duplicatas)
          name: values.name || metadataFields.name,
          exporter_type: selectedTypeObj?.exporter_type,
          module: selectedTypeObj?.module || exporterFields.module,
        },
      };

      // Montar Check do Consul dinamicamente baseado nos campos do schema
      // O Check será montado apenas se enable_check estiver ativo e houver campos de check
      if (formSchema && values.enable_check === true) {
        const checkConfig: any = {};

        // Buscar todos os campos que começam com "check_" do form_schema
        // O schema define os nomes dos campos, não assumimos valores padrão
        formSchema.fields.forEach((field) => {
          if (field.name.startsWith('check_')) {
            const checkKey = field.name.replace('check_', '');
            // Converter check_interval -> Interval, check_timeout -> Timeout, etc.
            const consulKey = checkKey.charAt(0).toUpperCase() + checkKey.slice(1);
            const value = values[field.name];
            // Apenas adicionar se o valor foi preenchido pelo usuário
            if (value !== undefined && value !== null && value !== '') {
              checkConfig[consulKey] = value;
            }
          }
        });

        // Adicionar Check ao payload apenas se houver pelo menos um campo configurado
        if (Object.keys(checkConfig).length > 0) {
          payload.Check = checkConfig;
        }
      }

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
  }, [form, mode, service, selectedNode, selectedType, availableTypes, formSchema, formFields, batchEnsure, ensureTags, onSuccess]);

  // Renderizar campos do form_schema (exporter_fields) em layout de 2 colunas
  const renderExporterFields = useMemo(() => {
    // ✅ OTIMIZAÇÃO: Não executar logs quando modal está fechado
    if (!visible) return null;

    if (import.meta.env.DEV) {
      console.log('[DynamicCRUDModal] renderExporterFields useMemo executando, formSchema:', formSchema);
    }

    if (!formSchema || !formSchema.fields || formSchema.fields.length === 0) {
      if (import.meta.env.DEV) {
        console.log('[DynamicCRUDModal] renderExporterFields retornando null (sem campos)');
      }
      return null;
    }

    if (import.meta.env.DEV) {
      console.log('[DynamicCRUDModal] renderExporterFields renderizando', formSchema.fields.length, 'campos');
      console.log('[DynamicCRUDModal] Campos a renderizar:', formSchema.fields);
    }

    const fieldItems = formSchema.fields.map((field) => {

      // Regras de validação
      const rules: any[] = [];

      // Required
      if (field.required) {
        rules.push({
          required: true,
          message: `${field.label || field.name} é obrigatório`,
        });
      }

      // Regex Pattern
      if (field.validation?.pattern) {
        rules.push({
          pattern: new RegExp(field.validation.pattern),
          message: field.validation.message || `Formato inválido para ${field.label || field.name}`,
        });
      }

      // Type Validation (URL, Email, etc)
      if (field.validation?.type) {
        rules.push({
          type: field.validation.type,
          message: field.validation.message || `Formato inválido para ${field.label || field.name}`,
        });
      }

      // Min/Max Length (para strings) ou Value (para numbers)
      if (field.validation?.min !== undefined || field.validation?.max !== undefined) {
        if (field.type === 'number') {
          // Para input number, min/max são controlados via props, mas regra ajuda
          rules.push({
            type: 'number',
            min: field.validation.min,
            max: field.validation.max,
            message: `Valor deve estar entre ${field.validation.min} e ${field.validation.max}`,
          });
        } else {
          // Para strings
          rules.push({
            min: field.validation.min,
            max: field.validation.max,
            message: `Deve ter entre ${field.validation.min} e ${field.validation.max} caracteres`,
          });
        }
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
              rows={3}
            />
          );
          break;

        case 'tags':
          // Usar TagsInput para campos de tags (multi-select com escrita e tags coloridas)
          inputComponent = (
            <TagsInput
              placeholder={field.placeholder}
              required={field.required}
              helpText={field.help}
            />
          );
          break;

        case 'checkbox':
          // Usar Switch para campos booleanos (checkbox)
          // O valor será controlado pelo Form.Item, não pelo checked prop
          inputComponent = (
            <Switch
              checkedChildren="Ativado"
              unCheckedChildren="Desativado"
            />
          );
          break;

        default:
          inputComponent = (
            <Input placeholder={field.placeholder} />
          );
      }

      // Normalizar initialValue para campos do tipo 'tags' (garantir que seja array)
      // Normalizar initialValue para campos do tipo 'checkbox' (garantir que seja boolean)
      let normalizedInitialValue = field.default;
      if (field.type === 'tags') {
        if (Array.isArray(field.default)) {
          normalizedInitialValue = field.default;
        } else if (typeof field.default === 'string') {
          normalizedInitialValue = [field.default];
        } else {
          normalizedInitialValue = [];
        }
      } else if (field.type === 'checkbox') {
        normalizedInitialValue = field.default === true || field.default === 'true';
      }

      // Verificar se campo tem dependência (depends_on)
      const dependsOn = (field as any).depends_on;

      return (
        <Form.Item noStyle shouldUpdate={(prevValues, currentValues) => {
          if (!dependsOn) return false;
          return prevValues[dependsOn] !== currentValues[dependsOn];
        }}>
          {({ getFieldValue }) => {
            const dependsOnValue = dependsOn ? getFieldValue(dependsOn) : true;
            const shouldShow = !dependsOn || dependsOnValue === true;

            if (!shouldShow) {
              return null;
            }

            // Determinar span: Prioriza col_span do schema > tipo tags/checkbox/textarea (24) > padrão (12)
            let span = 12;
            if (field.col_span) {
              span = field.col_span;
            } else if (field.type === 'textarea' || field.type === 'tags' || field.type === 'checkbox') {
              span = 24;
            }

            const isFullWidth = span === 24;

            return (
              <FloatingFormField
                key={field.name}
                name={field.name}
                label={field.label || field.name}
                helper={field.help}
                required={field.required}
                rules={rules}
                initialValue={normalizedInitialValue}
                className={isFullWidth ? 'span-full' : ''}
              >
                {inputComponent}
              </FloatingFormField>
            );
          }}
        </Form.Item>
      );
    });

    return <div className="form-grid-layout">{fieldItems}</div>;
  }, [formSchema, visible]);

  // Renderizar campos metadata genéricos em layout de 2 colunas
  // ✅ FILTRAR: Excluir campos que já estão no form_schema (evitar duplicação)
  const renderMetadataFields = useMemo(() => {
    // ✅ OTIMIZAÇÃO: Não executar quando modal está fechado
    if (!visible) return null;

    // Criar Set com nomes dos campos do form_schema
    const formSchemaFieldNames = new Set<string>();
    if (formSchema && formSchema.fields) {
      formSchema.fields.forEach((field) => {
        formSchemaFieldNames.add(field.name);
      });
    }

    // Filtrar formFields: excluir campos que estão no form_schema
    const filteredFields = formFields.filter((field) => {
      const isInFormSchema = formSchemaFieldNames.has(field.name);
      if (isInFormSchema && import.meta.env.DEV) {
        console.log(`[DynamicCRUDModal] ⚠️ Campo '${field.name}' excluído de metadata (já está no form_schema)`);
      }
      return !isInFormSchema;
    });

    if (import.meta.env.DEV) {
      console.log(`[DynamicCRUDModal] 📊 Metadata fields: ${formFields.length} total, ${filteredFields.length} após filtro (${formFields.length - filteredFields.length} excluídos)`);
    }

    const fieldItems = filteredFields.map((field) => {
      // Determinar span baseado no tipo: text/textarea ocupa linha inteira
      // Usar type assertion porque o TypeScript pode não ter todos os tipos atualizados
      const fieldType = (field as any).field_type || field.field_type;
      const fieldNameLower = field.name.toLowerCase();
      const isFullWidth = fieldType === 'text' || fieldType === 'textarea' || fieldNameLower === 'notas' || fieldNameLower === 'notes' || fieldNameLower === 'description' || fieldNameLower === 'observacao';

      return (
        <FormFieldRenderer
          key={field.name}
          field={field}
          mode={mode}
          className={isFullWidth ? 'span-full' : ''}
        />
      );
    });

    return <div className="form-grid-layout">{fieldItems}</div>;
  }, [formFields, formSchema, mode, visible]);

  // Determinar título do modal
  const modalTitle = mode === 'create' ? 'Criar Novo Serviço' : 'Editar Serviço';

  // Determinar botão de submit
  const submitButtonText = mode === 'create' ? 'Criar Serviço' : 'Atualizar Serviço';

  // Debug: log do step atual - APENAS em DEV e quando modal está visível
  useEffect(() => {
    if (import.meta.env.DEV && visible) {
      console.log('[DynamicCRUDModal] Step atual:', step, 'Mode:', mode, 'Visible:', visible);
    }
  }, [step, mode, visible]);

  // Debug: log do formSchema - APENAS em DEV e quando modal está visível
  useEffect(() => {
    if (!import.meta.env.DEV || !visible) return;

    console.log('[DynamicCRUDModal] formSchema atualizado:', formSchema);
    if (formSchema) {
      console.log('[DynamicCRUDModal] formSchema.fields:', formSchema.fields?.length, 'campos');
      if (formSchema.fields && formSchema.fields.length > 0) {
        console.log('[DynamicCRUDModal] ✅ CAMPOS DO SCHEMA:',
          formSchema.fields.map(f => ({
            name: f.name,
            label: f.label,
            type: f.type,
            hasOptions: !!(f.options && f.options.length > 0)
          }))
        );
      }
    }
  }, [formSchema, visible]);

  // Debug: log quando step muda para 'exporter' ou 'metadata' - APENAS em DEV e quando modal está visível
  useEffect(() => {
    if (!import.meta.env.DEV || !visible) return;

    if (step === 'exporter') {
      console.log('[DynamicCRUDModal] 🎯 STEP=exporter - Campos do form_schema:');
      console.log('[DynamicCRUDModal]   - formSchema existe:', !!formSchema);
      console.log('[DynamicCRUDModal]   - formSchema.fields.length:', formSchema?.fields?.length || 0);
    }
    if (step === 'metadata') {
      console.log('[DynamicCRUDModal] 🎯 STEP=metadata - Campos genéricos do KV');
      console.log('[DynamicCRUDModal]   - formFields.length:', formFields.length);
    }
  }, [step, formSchema, formFields, visible]);

  // Efeito para validar campos do passo atual em tempo real
  useEffect(() => {
    const validateCurrentStep = async () => {
      let fieldsToCheck: string[] = [];

      if (step === 'node') {
        setSubmittable(!!selectedNode && selectedNode !== 'all');
        return;
      }

      if (step === 'type') {
        setSubmittable(!!selectedType);
        return;
      }

      if (step === 'exporter') {
        // Validar campos do form_schema
        fieldsToCheck = formSchema?.fields?.map(f => f.name) || [];
      } else if (step === 'metadata') {
        // Validar campos de metadata + name (obrigatório)
        // Filtrar campos que já foram preenchidos no step anterior (do form_schema)
        const schemaFields = new Set(formSchema?.fields?.map(f => f.name) || []);
        const metaFields = formFields
          .filter(f => !schemaFields.has(f.name))
          .map(f => f.name);

        // 'name' é sempre obrigatório e geralmente está nos metadados ou values
        fieldsToCheck = [...metaFields, 'name'];
      }

      // Se não há campos para validar neste step, permite avançar
      if (fieldsToCheck.length === 0) {
        setSubmittable(true);
        return;
      }

      try {
        // validateOnly: true não mostra erro na UI, apenas verifica
        // @ts-ignore - validateOnly disponível no AntD 5.x
        await form.validateFields(fieldsToCheck, { validateOnly: true });
        setSubmittable(true);
      } catch (e) {
        setSubmittable(false);
      }
    };

    validateCurrentStep();
  }, [formValues, step, selectedNode, selectedType, formSchema, formFields]);

  // Handler para voltar ao passo anterior
  const handleBack = () => {
    if (step === 'type') setStep('node');
    else if (step === 'exporter') setStep('type');
    else if (step === 'metadata') {
      if (formSchema && formSchema.fields && formSchema.fields.length > 0) {
        setStep('exporter');
      } else {
        setStep('type'); // Pula exporter se vazio
      }
    }
  };

  // Renderiza o Header com informações do Nó
  const renderHeader = () => {
    if (step === 'node' || !selectedNode) return null;

    // Tentar obter label amigável
    // Suporta tanto objeto ConsulNode (do NodeSelector) quanto Option do Select
    let nodeLabelRaw = '';

    if (selectedNodeData) {
      if ('site_name' in selectedNodeData) {
        nodeLabelRaw = selectedNodeData.site_name;
      } else if ('name' in selectedNodeData) {
        nodeLabelRaw = selectedNodeData.name;
      } else if ('label' in selectedNodeData) {
        nodeLabelRaw = selectedNodeData.label;
      } else if ('children' in selectedNodeData) {
        // children pode ser complexo (ReactNode), tentar extrair string se possível
        if (typeof selectedNodeData.children === 'string') {
          nodeLabelRaw = selectedNodeData.children;
        }
      }
    }

    const nodeIp = selectedNode;

    // Se não tiver label, usa o IP como label
    let displayLabel: string = nodeLabelRaw || nodeIp;
    let displayIp: string | null = nodeIp;

    // Limpeza básica
    if (displayLabel && typeof displayLabel === 'string') {
      const cleanLabel = displayLabel.trim();
      const cleanIp = nodeIp.trim();

      // Se o label for exatamente o IP, não mostra IP secundário
      if (cleanLabel === cleanIp) {
        displayIp = null;
      }
      // Se o label contiver " - IP" ou " (IP)", simplifica para mostrar só o nome
      else if (cleanLabel.includes(cleanIp)) {
        const possibleName = cleanLabel.replace(cleanIp, '').replace(/[()-]/g, '').trim();
        if (possibleName) {
          displayLabel = possibleName;
        } else {
          displayLabel = cleanIp;
          displayIp = null;
        }
      }
    }

    // Lógica para determinar Master/Slave
    let isMaster = false;
    if (selectedNodeData) {
      if (typeof selectedNodeData.isMaster === 'boolean') {
        isMaster = selectedNodeData.isMaster;
      } else if (selectedNodeData.type === 'master') {
        isMaster = true;
      } else if (selectedNodeData.tags?.role === 'master') {
        isMaster = true;
      }
    }

    return (
      <div style={{
        marginBottom: 24,
        background: '#fff',
        border: `1px solid ${token.colorBorderSecondary}`,
        borderRadius: token.borderRadiusLG,
        padding: '16px',
        boxShadow: '0 2px 8px rgba(0,0,0,0.02)',
        display: 'flex',
        alignItems: 'center',
        gap: 16
      }}>
        <div style={{
          width: 40,
          height: 40,
          borderRadius: '50%',
          background: token.colorInfoBg,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          border: `1px solid ${token.colorInfoBorder}`
        }}>
          <CloudServerOutlined style={{ color: token.colorInfo, fontSize: 20 }} />
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', flex: 1 }}>
          <Text type="secondary" style={{ fontSize: 12 }}>SERVIDOR SELECIONADO</Text>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
            <Text strong style={{ fontSize: 16 }}>
              {displayLabel}
            </Text>

            {displayIp && displayIp !== displayLabel && (
              <Tag style={{ margin: 0, fontFamily: 'monospace' }}>
                {displayIp}
              </Tag>
            )}

            {/* Badge Master/Slave */}
            <Tag
              color={isMaster ? 'green' : 'blue'}
              style={{ margin: 0, textTransform: 'capitalize' }}
            >
              {isMaster ? 'Master' : 'Slave'}
            </Tag>
          </div>
        </div>

        <Button
          type="text"
          icon={<EditOutlined />}
          onClick={() => setStep('node')}
          title="Alterar servidor"
        />
      </div>
    );
  };

  return (
    <Modal
      title={
        <Space>
          {mode === 'create' ? 'Novo Serviço de Monitoramento' : 'Editar Serviço'}
          {service && <Text type="secondary" style={{ fontSize: 14 }}>#{service.Service}</Text>}
        </Space>
      }
      open={visible}
      onCancel={onCancel}
      width={900}
      footer={null}
      destroyOnHidden
      maskClosable={false}
    >
      {/* Stepper Visual */}
      <div style={{ marginBottom: 32, marginTop: 16 }}>
        <Steps
          current={currentStepIndex}
          items={STEPS}
          size="small"
        />
      </div>

      <Form
        form={form}
        layout="vertical"
        onFinish={handleSubmit}
      >
        {/* Header com info do nó (exceto no passo 1) */}
        {renderHeader()}

        {/* Container do conteúdo com transição suave */}
        <div style={{ minHeight: 300 }}>

          {/* PASSO 1: Seleção de Nó */}
          <div style={{ display: step === 'node' ? 'block' : 'none' }}>
            <div style={{ marginBottom: 24, textAlign: 'center', maxWidth: 600, margin: '0 auto 32px' }}>
              <Typography.Title level={4}>Onde você quer monitorar?</Typography.Title>
              <Text type="secondary">
                Selecione o nó do Consul (servidor) onde este serviço será registrado.
                Os tipos de monitoramento disponíveis dependem do servidor escolhido.
              </Text>
            </div>

            <Row justify="center">
              <Col span={16}>
                <Form.Item
                  name="node"
                  rules={[{ required: true, message: 'Selecione um nó do Consul' }]}
                >
                  <NodeSelector
                    value={selectedNode || undefined}
                    onChange={handleNodeSelect}
                    showAllNodesOption={false}
                    style={{ width: '100%', height: 50 }}
                    placeholder="Selecione ou busque um servidor..."
                  />
                </Form.Item>
              </Col>
            </Row>

            {loadingTypes && (
              <div style={{ textAlign: 'center', padding: '40px' }}>
                <Spin indicator={<LoadingOutlined style={{ fontSize: 24 }} spin />} />
                <div style={{ marginTop: 16, color: token.colorTextSecondary }}>
                  Carregando catálogo de tipos disponíveis...
                </div>
              </div>
            )}

            {typeError && (
              <Alert
                message="Erro ao carregar catálogo"
                description={typeError}
                type="error"
                showIcon
                style={{ marginTop: 24 }}
              />
            )}
          </div>

          {/* PASSO 2: Seleção de Tipo */}
          <div style={{ display: step === 'type' ? 'block' : 'none' }}>
            <div style={{ marginBottom: 24 }}>
              <Typography.Title level={5}>Selecione o Tipo</Typography.Title>
              <Text type="secondary">Escolha qual tipo de monitoramento deseja configurar neste servidor.</Text>
            </div>

            <Form.Item
              name="service_name"
              rules={[{ required: true, message: 'Selecione um tipo de monitoramento' }]}
            >
              <Select
                placeholder="Busque por nome, job ou tipo..."
                value={selectedType}
                onChange={handleTypeSelect}
                loading={loadingTypes}
                showSearch
                size="large"
                optionFilterProp="data-search"
                optionLabelProp="label" // ✅ CORREÇÃO: Usar label simples quando selecionado
                style={{ width: '100%' }}
                listHeight={300}
              >
                {availableTypes.map((type) => (
                  <Select.Option
                    key={type.id || type.job_name}
                    value={type.id || type.job_name}
                    label={type.display_name} // ✅ Label simples para o input
                    data-search={`${type.display_name} ${type.exporter_type} ${type.category}`}
                  >
                    <div style={{
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center',
                      width: '100%',
                      padding: '4px 0'
                    }}>
                      <div style={{ display: 'flex', flexDirection: 'column', overflow: 'hidden', marginRight: 12 }}>
                        <Text strong style={{ fontSize: 15, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                          {type.display_name}
                        </Text>
                        <Text type="secondary" style={{ fontSize: 12 }}>{type.exporter_type}</Text>
                      </div>
                      <div style={{
                        background: token.colorBgLayout,
                        padding: '2px 8px',
                        borderRadius: 4,
                        fontSize: 10, // Reduzido levemente
                        color: token.colorTextTertiary,
                        whiteSpace: 'nowrap',
                        flexShrink: 0,
                        marginLeft: 8, // Espaço fixo da esquerda
                        maxWidth: '30%', // Limitar largura máxima
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                        textAlign: 'right'
                      }}>
                        {type.category}
                      </div>
                    </div>
                  </Select.Option>
                ))}
              </Select>
            </Form.Item>

            {loadingSchema && (
              <div style={{ textAlign: 'center', padding: '60px' }}>
                <Spin indicator={<LoadingOutlined style={{ fontSize: 24 }} spin />} />
                <div style={{ marginTop: 16, color: token.colorTextSecondary }}>
                  Carregando esquema do formulário...
                </div>
              </div>
            )}
          </div>

          {/* PASSO 3: Configuração do Exporter */}
          <div style={{ display: step === 'exporter' ? 'block' : 'none' }}>
            <div style={{ marginBottom: 24 }}>
              <Typography.Title level={5}>Configuração do Exporter</Typography.Title>
              <Text type="secondary">
                Preencha os campos específicos para <strong>{availableTypes.find(t => t.id === selectedType)?.display_name}</strong>.
              </Text>
            </div>

            <div style={{
              background: token.colorBgLayout,
              padding: 24,
              borderRadius: token.borderRadiusLG,
              border: `1px solid ${token.colorBorderSecondary}`
            }}>
              {formSchema && formSchema.fields && formSchema.fields.length > 0 ? (
                renderExporterFields
              ) : (
                <div style={{ textAlign: 'center', padding: 24, color: token.colorTextSecondary }}>
                  <InfoCircleOutlined style={{ fontSize: 24, marginBottom: 8, display: 'block' }} />
                  Este tipo não requer configurações específicas. Pode avançar.
                </div>
              )}
            </div>
          </div>

          {/* PASSO 4: Metadata */}
          <div style={{ display: step === 'metadata' ? 'block' : 'none' }}>
            <div style={{ marginBottom: 24 }}>
              <Typography.Title level={5}>Detalhes e Metadados</Typography.Title>
              <Text type="secondary">Informações adicionais para categorização e filtros.</Text>
            </div>

            <div style={{
              background: token.colorBgLayout,
              padding: 24,
              borderRadius: token.borderRadiusLG,
              border: `1px solid ${token.colorBorderSecondary}`
            }}>
              {renderMetadataFields}
            </div>
          </div>

        </div>

        <Divider />

        {/* Footer com botões */}
        <div style={{ marginTop: 32, textAlign: 'right', borderTop: `1px solid ${token.colorBorderSecondary}`, paddingTop: 16 }}>
          <Space size="middle"> {/* Aumentar espaçamento entre botões */}
            <Button onClick={onCancel} size="large">Cancelar</Button>

            {/* Botão Voltar */}
            {step !== 'node' && (
              <Button
                onClick={handleBack}
                icon={<ArrowLeftOutlined />}
                size="large"
              >
                Voltar
              </Button>
            )}

            {step === 'node' && (
              <Button
                type="primary"
                onClick={handleAdvanceFromNode}
                loading={loadingTypes}
                disabled={!submittable}
                size="large" // Botão grande
                style={{ minWidth: 120 }} // Largura mínima
              >
                Avançar
              </Button>
            )}
            {step === 'type' && (
              <Button
                type="primary"
                disabled={!submittable}
                loading={loadingSchema}
                onClick={() => {
                  if (selectedType) {
                    const type = availableTypes.find((t) => t.id === selectedType || t.job_name === selectedType);
                    if (type) {
                      loadFormSchema(type.id);
                    }
                  }
                }}
                size="large"
                style={{ minWidth: 120 }}
              >
                Avançar
              </Button>
            )}
            {step === 'exporter' && (
              <Button
                type="primary"
                htmlType="button"
                disabled={!submittable}
                onClick={(e) => {
                  e.preventDefault();
                  e.stopPropagation();
                  setStep('metadata');
                }}
                size="large"
                style={{ minWidth: 120 }}
              >
                Avançar
              </Button>
            )}
            {step === 'metadata' && (
              <Button
                type="primary"
                htmlType="submit"
                loading={loading}
                disabled={!submittable}
                size="large"
                style={{ minWidth: 140 }} // Um pouco maior para o submit final
              >
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

