import React, { useState, useEffect } from 'react';
import { Form, Tooltip } from 'antd';
import { InfoCircleOutlined } from '@ant-design/icons';
import './FloatingFormField.css';

interface FloatingFormFieldProps {
    name: string;
    label: string;
    children: React.ReactNode;
    helper?: string;
    required?: boolean;
    rules?: any[];
    initialValue?: any;
    style?: React.CSSProperties;
    className?: string;
    value?: any; // Para controlar estado se necessário
    fixedHeight?: boolean; // Se true, força altura de 40px (padrão: true)
}

const FloatingFormField: React.FC<FloatingFormFieldProps> = ({
    name,
    label,
    children,
    helper,
    required,
    rules = [],
    initialValue,
    style,
    className,
    fixedHeight = true,
}) => {
    // Precisamos saber se o campo tem valor para manter o label flutuando mesmo sem foco
    const form = Form.useFormInstance();
    const fieldValue = Form.useWatch(name, form);
    const [hasValue, setHasValue] = useState(false);

    useEffect(() => {
        // Verifica se tem valor (não nulo, não undefined, não string vazia)
        if (fieldValue !== undefined && fieldValue !== null && fieldValue !== '') {
            if (Array.isArray(fieldValue) && fieldValue.length === 0) {
                setHasValue(false);
            } else {
                setHasValue(true);
            }
        } else {
            setHasValue(false);
        }
    }, [fieldValue]);

    return (
        <div className={`floating-form-field ${className || ''}`} style={style}>
            <Form.Item
                name={name}
                rules={rules}
                initialValue={initialValue}
                noStyle // Removemos estilos padrão do Form.Item para controlar layout manualmente
            >
                {/* Renderizamos o Form.Item "invisível" apenas para lógica de validação/registro */}
                {/* Mas a UI real é controlada abaixo */}
                <React.Fragment>
                    {/* Usamos um wrapper para capturar focus-within */}
                    <div className={`floating-input-container ${hasValue ? 'has-value' : ''} ${fixedHeight ? 'fixed-height' : ''}`}>

                        {/* Label Flutuante + Helper Icon */}
                        <label className="floating-label">
                            {label}
                            {required && <span className="required-mark">*</span>}

                            {/* Helper Icon agora faz parte do label container para ficar ao lado */}
                            {helper && (
                                <Tooltip title={helper}>
                                    <InfoCircleOutlined className="floating-helper-icon" />
                                </Tooltip>
                            )}
                        </label>

                        {/* O Componente de Input (Children) */}
                        {/* Injetamos props se necessário, mas geralmente o Form.Item já cuida do onChange/value */}
                        <Form.Item name={name} noStyle>
                            {children}
                        </Form.Item>
                    </div>

                    {/* Mensagem de Erro (precisamos renderizar manualmente pois usamos noStyle no pai) */}
                    <Form.Item
                        name={name}
                        noStyle
                        shouldUpdate={(prev, curr) => prev[name] !== curr[name]}
                    >
                        {({ getFieldError }) => {
                            const errors = getFieldError(name);
                            return errors.length > 0 ? (
                                <div style={{ color: '#ff4d4f', fontSize: '12px', marginTop: '4px' }}>
                                    {errors[0]}
                                </div>
                            ) : null;
                        }}
                    </Form.Item>
                </React.Fragment>
            </Form.Item>
        </div>
    );
};

export default FloatingFormField;
