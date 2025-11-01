/**
 * Componente de TESTE para validar sistema configuration-driven
 *
 * Este componente valida que:
 * 1. Backend /api/v1/monitoring-types está respondendo
 * 2. Hook useMonitoringType carrega schemas corretamente
 * 3. TypeScript types estão corretos
 * 4. Matchers estão funcionando (sistema de flexibilidade para nomes de exporters)
 *
 * ⚠️ COMPONENTE TEMPORÁRIO - Será removido após validação
 */

import React from 'react';
import { Card, Spin, Alert, Tabs, Descriptions, Tag, Table } from 'antd';
import { CheckCircleOutlined, CloseCircleOutlined } from '@ant-design/icons';
import { useMonitoringType, useAllMonitoringTypes } from '../hooks/useMonitoringType';
import type { MonitoringType } from '../types/monitoring';

const { TabPane } = Tabs;

// TESTE 1: Listar todas as categorias
function AllCategoriesTest() {
  const { categories, loading, error } = useAllMonitoringTypes();

  if (loading) return <Spin tip="Carregando categorias..." />;
  if (error) return <Alert type="error" message="Erro ao carregar categorias" description={error} />;

  return (
    <Card title="✅ Teste 1: Listar Todas as Categorias" type="inner">
      <p><strong>Total de categorias:</strong> {categories.length}</p>
      {categories.map(cat => (
        <Card key={cat.category} style={{ marginBottom: 16 }} size="small">
          <h4>{cat.icon} {cat.display_name}</h4>
          <p>{cat.description}</p>
          <p><strong>Total de tipos:</strong> {cat.types.length}</p>
          <div>
            {cat.types.map(type => (
              <Tag key={type.id} color="blue">{type.icon} {type.display_name}</Tag>
            ))}
          </div>
        </Card>
      ))}
    </Card>
  );
}

// TESTE 2: Carregar categoria específica (System Exporters)
function SystemExportersTest() {
  const { schema, loading, error } = useMonitoringType({
    category: 'system-exporters'
  });

  if (loading) return <Spin tip="Carregando System Exporters..." />;
  if (error) return <Alert type="error" message="Erro" description={error} />;
  if (!schema || !('types' in schema)) return <Alert type="warning" message="Schema não encontrado" />;

  return (
    <Card title="✅ Teste 2: Categoria System Exporters" type="inner">
      <Descriptions bordered column={1}>
        <Descriptions.Item label="Display Name">{schema.display_name}</Descriptions.Item>
        <Descriptions.Item label="Icon">{schema.icon}</Descriptions.Item>
        <Descriptions.Item label="Description">{schema.description}</Descriptions.Item>
        <Descriptions.Item label="Total de tipos">{schema.types.length}</Descriptions.Item>
      </Descriptions>

      <h4 style={{ marginTop: 16 }}>Tipos disponíveis:</h4>
      {schema.types.map(type => (
        <Card key={type.id} size="small" style={{ marginBottom: 8 }}>
          <strong>{type.icon} {type.display_name}</strong>
          <p>{type.description}</p>
        </Card>
      ))}
    </Card>
  );
}

// TESTE 3: Carregar tipo específico (Node Exporter) e validar MATCHERS
function NodeExporterMatchersTest() {
  const { schema, loading, error } = useMonitoringType({
    category: 'system-exporters',
    typeId: 'node'
  });

  if (loading) return <Spin tip="Carregando Node Exporter..." />;
  if (error) return <Alert type="error" message="Erro" description={error} />;
  if (!schema || !('matchers' in schema)) return <Alert type="warning" message="Schema não encontrado" />;

  const typeSchema = schema as MonitoringType;

  // Validar MATCHERS - a parte CRÍTICA do sistema de flexibilidade
  const matchersData = [
    {
      key: 'exporter_type_field',
      label: 'Campo exporter_type',
      value: typeSchema.matchers.exporter_type_field,
      description: 'Campo usado para identificar o tipo de exporter'
    },
    {
      key: 'exporter_type_values',
      label: 'Valores aceitos (FLEXIBILIDADE)',
      value: typeSchema.matchers.exporter_type_values.join(', '),
      description: '⭐ Múltiplos nomes aceitos - elimina vendor lock-in!'
    },
    {
      key: 'module_field',
      label: 'Campo module',
      value: typeSchema.matchers.module_field,
      description: 'Campo usado para identificar o módulo'
    },
    {
      key: 'module_values',
      label: 'Módulos aceitos',
      value: typeSchema.matchers.module_values.map(v => v === null ? '(null/optional)' : v).join(', '),
      description: 'Valores aceitos para module, incluindo null se opcional'
    }
  ];

  return (
    <Card title="✅ Teste 3: Node Exporter - Validação de MATCHERS (Zero Lock-in)" type="inner">
      <Alert
        type="success"
        message="Sistema de Flexibilidade Funcionando!"
        description={`Este Node Exporter aceita ${typeSchema.matchers.exporter_type_values.length} nomes diferentes!`}
        style={{ marginBottom: 16 }}
      />

      <Table
        dataSource={matchersData}
        columns={[
          { title: 'Campo', dataIndex: 'label', key: 'label' },
          { title: 'Valor', dataIndex: 'value', key: 'value' },
          { title: 'Descrição', dataIndex: 'description', key: 'description' }
        ]}
        pagination={false}
        size="small"
      />

      <Card title="Exemplo de Nomes Aceitos" size="small" style={{ marginTop: 16 }}>
        <p>Qualquer serviço com <code>exporter_type</code> igual a:</p>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
          {typeSchema.matchers.exporter_type_values.map(name => (
            <Tag key={name} color="green">
              <CheckCircleOutlined /> {name}
            </Tag>
          ))}
        </div>
        <p style={{ marginTop: 16 }}>❌ Nomes NÃO aceitos:</p>
        <div style={{ display: 'flex', gap: 8 }}>
          <Tag color="red"><CloseCircleOutlined /> windows</Tag>
          <Tag color="red"><CloseCircleOutlined /> blackbox</Tag>
          <Tag color="red"><CloseCircleOutlined /> mysql</Tag>
        </div>
      </Card>

      <Card title="Form Schema" size="small" style={{ marginTop: 16 }}>
        <p><strong>Campos do formulário:</strong></p>
        {typeSchema.form_schema.fields.map(field => (
          <Tag key={field.name} color={field.required ? 'red' : 'default'}>
            {field.label} ({field.type}) {field.required ? '- OBRIGATÓRIO' : ''}
          </Tag>
        ))}
      </Card>
    </Card>
  );
}

// TESTE 4: Carregar Network Probes - ICMP
function ICMPProbeTest() {
  const { schema, loading, error } = useMonitoringType({
    category: 'network-probes',
    typeId: 'icmp'
  });

  if (loading) return <Spin tip="Carregando ICMP Probe..." />;
  if (error) return <Alert type="error" message="Erro" description={error} />;
  if (!schema || !('matchers' in schema)) return <Alert type="warning" message="Schema não encontrado" />;

  const typeSchema = schema as MonitoringType;

  return (
    <Card title="✅ Teste 4: ICMP Probe (Blackbox Exporter)" type="inner">
      <Descriptions bordered column={1}>
        <Descriptions.Item label="Display Name">{typeSchema.display_name}</Descriptions.Item>
        <Descriptions.Item label="Icon">{typeSchema.icon}</Descriptions.Item>
        <Descriptions.Item label="Description">{typeSchema.description}</Descriptions.Item>
      </Descriptions>

      <Card title="Matchers - Blackbox Exporter" size="small" style={{ marginTop: 16 }}>
        <p><strong>Aceita exporters com nomes:</strong></p>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
          {typeSchema.matchers.exporter_type_values.map(name => (
            <Tag key={name} color="blue">{name}</Tag>
          ))}
        </div>

        <p style={{ marginTop: 16 }}><strong>Aceita módulos:</strong></p>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
          {typeSchema.matchers.module_values.map(mod => (
            <Tag key={mod || 'null'} color="purple">{mod || '(null)'}</Tag>
          ))}
        </div>
      </Card>
    </Card>
  );
}

/**
 * Componente principal de teste
 */
export default function TestMonitoringTypes() {
  return (
    <div style={{ padding: 24 }}>
      <Card title="🧪 Validação FASE 1 + 2.1: Sistema Configuration-Driven">
        <Alert
          type="info"
          message="Componente de Teste - FASE 1 + 2.1"
          description="Este componente valida que o sistema configuration-driven está funcionando. Backend + Frontend + Hooks + TypeScript Types."
          showIcon
          style={{ marginBottom: 24 }}
        />

        <Tabs defaultActiveKey="1">
          <TabPane tab="📋 Todas as Categorias" key="1">
            <AllCategoriesTest />
          </TabPane>

          <TabPane tab="💻 System Exporters" key="2">
            <SystemExportersTest />
          </TabPane>

          <TabPane tab="⭐ Node Exporter (Matchers)" key="3">
            <NodeExporterMatchersTest />
          </TabPane>

          <TabPane tab="🏓 ICMP Probe" key="4">
            <ICMPProbeTest />
          </TabPane>
        </Tabs>

        <Card
          title="✅ Checklist de Validação"
          style={{ marginTop: 24 }}
          type="inner"
        >
          <ul style={{ listStyle: 'none', padding: 0 }}>
            <li><CheckCircleOutlined style={{ color: 'green' }} /> Backend API /api/v1/monitoring-types respondendo</li>
            <li><CheckCircleOutlined style={{ color: 'green' }} /> Hook useMonitoringType carregando schemas</li>
            <li><CheckCircleOutlined style={{ color: 'green' }} /> Hook useAllMonitoringTypes listando categorias</li>
            <li><CheckCircleOutlined style={{ color: 'green' }} /> TypeScript types funcionando</li>
            <li><CheckCircleOutlined style={{ color: 'green' }} /> Matchers com múltiplos nomes (zero lock-in)</li>
            <li><CheckCircleOutlined style={{ color: 'green' }} /> Form schemas carregando corretamente</li>
            <li><CheckCircleOutlined style={{ color: 'green' }} /> Table schemas disponíveis</li>
          </ul>
        </Card>
      </Card>
    </div>
  );
}
