import React, { useState } from 'react';
import {
  Card,
  Select,
  Input,
  Button,
  Space,
  Tag,
  Divider,
  Typography,
  Row,
  Col,
  Alert,
} from 'antd';
import {
  PlusOutlined,
  DeleteOutlined,
  SearchOutlined,
  ClearOutlined,
  FilterOutlined,
} from '@ant-design/icons';

const { Option } = Select;
const { Text } = Typography;

export interface SearchCondition {
  field: string;
  operator: string;
  value: any;
}

interface AdvancedSearchPanelProps {
  availableFields: Array<{ label: string; value: string; type?: string }>;
  onSearch: (conditions: SearchCondition[], logicalOperator: string) => void;
  onClear?: () => void;
  initialConditions?: SearchCondition[];
  initialLogicalOperator?: string;
}

const AdvancedSearchPanel: React.FC<AdvancedSearchPanelProps> = ({
  availableFields,
  onSearch,
  onClear,
  initialConditions = [],
  initialLogicalOperator = 'and',
}) => {
  const [conditions, setConditions] = useState<SearchCondition[]>(
    initialConditions.length > 0
      ? initialConditions
      : [{ field: '', operator: 'eq', value: '' }]
  );
  const [logicalOperator, setLogicalOperator] = useState<string>(initialLogicalOperator);

  const operators = [
    { label: 'Igual (=)', value: 'eq' },
    { label: 'Diferente (=)', value: 'ne' },
    { label: 'Contem', value: 'contains' },
    { label: 'Comeca com', value: 'starts_with' },
    { label: 'Termina com', value: 'ends_with' },
    { label: 'Regex', value: 'regex' },
    { label: 'Em lista (in)', value: 'in' },
    { label: 'Nao em lista (not in)', value: 'not_in' },
    { label: 'Maior que (>)', value: 'gt' },
    { label: 'Menor que (<)', value: 'lt' },
    { label: 'Maior ou igual ()', value: 'gte' },
    { label: 'Menor ou igual ()', value: 'lte' },
  ];

  const addCondition = () => {
    setConditions([...conditions, { field: '', operator: 'eq', value: '' }]);
  };

  const removeCondition = (index: number) => {
    const newConditions = conditions.filter((_, i) => i !== index);
    setConditions(newConditions.length > 0 ? newConditions : [{ field: '', operator: 'eq', value: '' }]);
  };

  const updateCondition = (index: number, key: keyof SearchCondition, value: any) => {
    const newConditions = [...conditions];
    newConditions[index][key] = value;
    setConditions(newConditions);
  };

  const handleSearch = () => {
    const validConditions = conditions.filter(
      (c) => c.field && c.value !== '' && c.value !== null && c.value !== undefined
    );
    onSearch(validConditions, logicalOperator);
  };

  const handleClear = () => {
    setConditions([{ field: '', operator: 'eq', value: '' }]);
    setLogicalOperator('and');
    if (onClear) onClear();
  };

  const renderValueInput = (condition: SearchCondition, index: number) => {
    // Para operadores 'in' e 'not_in', usar Select com modo tags
    if (condition.operator === 'in' || condition.operator === 'not_in') {
      return (
        <Select
          mode="tags"
          style={{ width: '100%' }}
          placeholder="Digite valores e pressione Enter"
          value={Array.isArray(condition.value) ? condition.value : []}
          onChange={(value) => updateCondition(index, 'value', value)}
        />
      );
    }

    // Para outros operadores, usar Input simples
    return (
      <Input
        placeholder="Valor"
        value={condition.value}
        onChange={(e) => updateCondition(index, 'value', e.target.value)}
        onPressEnter={handleSearch}
      />
    );
  };

  return (
    <Card
      title={
        <Space>
          <FilterOutlined />
          <span>Busca Avancada</span>
        </Space>
      }
      size="small"
      style={{ marginBottom: 16 }}
    >
      <Alert
        message="Dica"
        description="Use multiplas condicoes para refinar sua busca. Combine com AND para resultados que atendem todas as condicoes, ou OR para qualquer uma delas."
        type="info"
        showIcon
        closable
        style={{ marginBottom: 16 }}
      />

      <Space direction="vertical" style={{ width: '100%' }} size="middle">
        {/* Operador logico */}
        <Row gutter={8} align="middle">
          <Col>
            <Text strong>Combinar condicoes com:</Text>
          </Col>
          <Col>
            <Select
              value={logicalOperator}
              onChange={setLogicalOperator}
              style={{ width: 100 }}
            >
              <Option value="and">
                <Tag color="blue">AND</Tag>
              </Option>
              <Option value="or">
                <Tag color="green">OR</Tag>
              </Option>
            </Select>
          </Col>
          <Col flex="auto">
            <Text type="secondary">
              {logicalOperator === 'and'
                ? 'Todas as condicoes devem ser verdadeiras'
                : 'Pelo menos uma condicao deve ser verdadeira'}
            </Text>
          </Col>
        </Row>

        <Divider style={{ margin: '8px 0' }} />

        {/* Condicoes */}
        {conditions.map((condition, index) => (
          <Row key={index} gutter={8} align="middle">
            <Col xs={24} sm={7}>
              <Select
                placeholder="Selecione um campo"
                style={{ width: '100%' }}
                value={condition.field || undefined}
                onChange={(value) => updateCondition(index, 'field', value)}
                showSearch
                optionFilterProp="children"
              >
                {availableFields.map((field) => (
                  <Option key={field.value} value={field.value}>
                    {field.label}
                  </Option>
                ))}
              </Select>
            </Col>

            <Col xs={24} sm={6}>
              <Select
                placeholder="Operador"
                style={{ width: '100%' }}
                value={condition.operator}
                onChange={(value) => updateCondition(index, 'operator', value)}
              >
                {operators.map((op) => (
                  <Option key={op.value} value={op.value}>
                    {op.label}
                  </Option>
                ))}
              </Select>
            </Col>

            <Col xs={24} sm={9}>
              {renderValueInput(condition, index)}
            </Col>

            <Col xs={24} sm={2}>
              <Space>
                {index === conditions.length - 1 && (
                  <Button
                    type="dashed"
                    size="small"
                    icon={<PlusOutlined />}
                    onClick={addCondition}
                  />
                )}
                {conditions.length > 1 && (
                  <Button
                    danger
                    size="small"
                    icon={<DeleteOutlined />}
                    onClick={() => removeCondition(index)}
                  />
                )}
              </Space>
            </Col>
          </Row>
        ))}

        <Divider style={{ margin: '8px 0' }} />

        {/* Botoes de acao */}
        <Row justify="end">
          <Space>
            <Button icon={<ClearOutlined />} onClick={handleClear}>
              Limpar
            </Button>
            <Button type="primary" icon={<SearchOutlined />} onClick={handleSearch}>
              Buscar
            </Button>
          </Space>
        </Row>

        {/* Preview das condicoes */}
        {conditions.filter((c) => c.field && c.value).length > 0 && (
          <>
            <Divider style={{ margin: '8px 0' }}>Preview</Divider>
            <div
              style={{
                background: '#f5f5f5',
                padding: 12,
                borderRadius: 4,
                fontFamily: 'monospace',
                fontSize: 12,
              }}
            >
              {conditions
                .filter((c) => c.field && c.value)
                .map((c, i) => (
                  <div key={i}>
                    {i > 0 && (
                      <Text strong style={{ color: '#1890ff' }}>
                        {' '}
                        {logicalOperator.toUpperCase()}{' '}
                      </Text>
                    )}
                    <Text>
                      {availableFields.find((f) => f.value === c.field)?.label || c.field}{' '}
                      <Text type="secondary">
                        {operators.find((o) => o.value === c.operator)?.label}
                      </Text>{' '}
                      <Text code>
                        {Array.isArray(c.value) ? `[${c.value.join(', ')}]` : c.value}
                      </Text>
                    </Text>
                  </div>
                ))}
            </div>
          </>
        )}
      </Space>
    </Card>
  );
};

export default AdvancedSearchPanel;
