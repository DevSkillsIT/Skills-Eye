/**
 * Componente TagsInput - Select Multi-Tag com Auto-Cadastro
 *
 * OBJETIVO:
 * Input inteligente para gerenciar ARRAY de tags que:
 * 1. Mostra tags existentes como opções de select
 * 2. Permite usuário digitar novas tags
 * 3. Ao salvar formulário, auto-cadastra tags novas automaticamente
 * 4. Normaliza tags (Title Case)
 *
 * USO:
 * ```tsx
 * <TagsInput
 *   value={tags}                    // ["linux", "monitoring", "production"]
 *   onChange={setTags}
 *   placeholder="Selecione ou digite tags"
 *   required={true}
 * />
 * ```
 *
 * EXEMPLO DE FLUXO:
 * 1. Usuário abre formulário
 * 2. Select mostra opções: ["linux", "windows", "monitoring", "production"]
 * 3. Usuário seleciona "linux" e "monitoring"
 * 4. Usuário digita nova tag "DATABASE" e pressiona Enter
 * 5. Tags ficam: ["linux", "monitoring", "DATABASE"]
 * 6. Ao salvar formulário pai, chama ensureTags() automaticamente
 * 7. Backend normaliza "DATABASE" → "Database" e cadastra
 * 8. Próximo cadastro: "Database" aparece nas opções
 */

import React, { useState, useEffect } from 'react';
import { Select, Spin, Tag, Space } from 'antd';
import { PlusOutlined, LoadingOutlined, TagOutlined } from '@ant-design/icons';
import { useServiceTags } from '../hooks/useServiceTags';

export interface TagsInputProps {
  /** Valor atual (array de tags) */
  value?: string[];

  /** Callback quando tags mudam */
  onChange?: (tags: string[]) => void;

  /** Placeholder do input */
  placeholder?: string;

  /** Se campo é obrigatório */
  required?: boolean;

  /** Desabilitar input */
  disabled?: boolean;

  /** Texto de ajuda exibido abaixo do campo */
  helpText?: string;

  /** Se True, auto-cadastra tags ao mudar (padrão: False, espera salvar formulário pai) */
  autoEnsureOnChange?: boolean;

  /** Estilo customizado */
  style?: React.CSSProperties;

  /** ClassName customizada */
  className?: string;

  /** Limite máximo de tags (padrão: sem limite) */
  maxTags?: number;
}

/**
 * Input com select multi-tag e auto-cadastro
 */
const TagsInput: React.FC<TagsInputProps> = ({
  value = [],
  onChange,
  placeholder = 'Selecione ou digite tags...',
  required = false,
  disabled = false,
  helpText,
  autoEnsureOnChange = false,
  style,
  className,
  maxTags
}) => {
  const {
    tags: availableTags,
    loading,
    error,
    ensureTags
  } = useServiceTags({
    autoLoad: true,
    includeStats: false
  });

  const [internalValue, setInternalValue] = useState<string[]>(value || []);
  const [isEnsuring, setIsEnsuring] = useState(false);

  /**
   * Sincronizar valor interno com prop value
   */
  useEffect(() => {
    if (value !== undefined) {
      setInternalValue(value);
    }
  }, [value]);

  /**
   * Handler quando tags mudam
   */
  const handleChange = async (newTags: string[]) => {
    // Aplicar limite de tags se definido
    const limitedTags = maxTags ? newTags.slice(0, maxTags) : newTags;

    setInternalValue(limitedTags);

    // Notificar componente pai
    if (onChange) {
      onChange(limitedTags);
    }

    // Auto-cadastro IMEDIATO se habilitado
    // IMPORTANTE: Na maioria dos casos, NÃO use autoEnsureOnChange=true!
    // Deixe o formulário pai chamar ensureTags() ao salvar.
    if (autoEnsureOnChange && limitedTags.length > 0) {
      setIsEnsuring(true);

      try {
        const results = await ensureTags(limitedTags);

        // Verificar se alguma tag foi normalizada
        const normalizedTags = results
          .filter(r => r.success)
          .map(r => r.value);

        if (normalizedTags.length > 0 && JSON.stringify(normalizedTags) !== JSON.stringify(limitedTags)) {
          // Atualizar com valores normalizados
          setInternalValue(normalizedTags);

          if (onChange) {
            onChange(normalizedTags);
          }
        }
      } catch (err) {
        console.error('Erro ao garantir tags:', err);
      } finally {
        setIsEnsuring(false);
      }
    }
  };

  /**
   * Identificar tags novas (que ainda não existem na lista)
   */
  const getNewTags = () => {
    return internalValue.filter(tag => !availableTags.includes(tag));
  };

  const newTags = getNewTags();

  /**
   * Preparar opções para o Select
   */
  const options = availableTags.map((tag) => ({
    value: tag,
    label: (
      <Space>
        <TagOutlined style={{ color: '#1890ff' }} />
        <span>{tag}</span>
      </Space>
    )
  }));

  /**
   * Renderizar tag customizada
   */
  const tagRender = (props: any) => {
    const { label, value: tagValue, closable, onClose } = props;
    const isNew = !availableTags.includes(tagValue);

    return (
      <Tag
        color={isNew ? 'green' : 'blue'}
        closable={closable}
        onClose={onClose}
        style={{ marginRight: 3 }}
        icon={isNew ? <PlusOutlined /> : <TagOutlined />}
      >
        {tagValue}
      </Tag>
    );
  };

  return (
    <div style={{ position: 'relative' }}>
      <Select
        mode="tags"
        value={internalValue}
        onChange={handleChange}
        options={options}
        placeholder={placeholder}
        disabled={disabled || loading}
        loading={loading || isEnsuring}
        style={{ width: '100%', ...style }}
        className={className}
        tagRender={tagRender}
        maxTagCount={maxTags}
        maxTagPlaceholder={(omittedValues) => (
          <span>+{omittedValues.length} tags...</span>
        )}
        suffixIcon={
          isEnsuring ? (
            <LoadingOutlined spin />
          ) : loading ? (
            <Spin size="small" />
          ) : null
        }
        filterOption={(input, option) => {
          return (option?.value as string)?.toLowerCase().includes(input.toLowerCase());
        }}
        notFoundContent={
          loading ? (
            <div style={{ textAlign: 'center', padding: '8px' }}>
              <Spin size="small" />
              <span style={{ marginLeft: 8 }}>Carregando tags...</span>
            </div>
          ) : null
        }
        popupRender={(menu) => (
          <>
            {menu}
            {!loading && (
              <div style={{
                padding: '8px 12px',
                borderTop: '1px solid #f0f0f0',
                color: '#999',
                fontSize: '12px'
              }}>
                <PlusOutlined style={{ marginRight: 4 }} />
                Digite e pressione Enter para criar nova tag
              </div>
            )}
          </>
        )}
      />

      {helpText && (
        <div style={{ fontSize: '12px', color: '#666', marginTop: 4 }}>
          {helpText}
        </div>
      )}

      {error && (
        <div style={{ fontSize: '12px', color: '#ff4d4f', marginTop: 4 }}>
          ⚠ {error}
        </div>
      )}

      {/* Indicador visual quando existem tags novas */}
      {newTags.length > 0 && !loading && (
        <div style={{ marginTop: 8, padding: '8px 12px', backgroundColor: '#f6ffed', border: '1px solid #b7eb8f', borderRadius: 4 }}>
          <Space direction="vertical" size={4} style={{ width: '100%' }}>
            <div style={{ fontSize: '12px', color: '#52c41a', fontWeight: 500 }}>
              <PlusOutlined style={{ marginRight: 4 }} />
              {newTags.length === 1 ? 'Nova tag será criada' : `${newTags.length} novas tags serão criadas`}:
            </div>
            <div>
              {newTags.map(tag => (
                <Tag key={tag} color="green" icon={<PlusOutlined />} style={{ fontSize: '11px', marginBottom: 4 }}>
                  {tag}
                </Tag>
              ))}
            </div>
          </Space>
        </div>
      )}

      {/* Indicador de limite de tags */}
      {maxTags && internalValue.length >= maxTags && (
        <div style={{ marginTop: 4, fontSize: '12px', color: '#faad14' }}>
          ⚠ Limite de {maxTags} tags atingido
        </div>
      )}
    </div>
  );
};

export default TagsInput;
