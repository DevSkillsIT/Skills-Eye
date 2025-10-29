/**
 * Componente de Selecao de Colunas
 * Permite ao usuario escolher quais colunas exibir e reordena-las via drag & drop
 */
import React, { useState } from 'react';
import {
  Button,
  Checkbox,
  Drawer,
  Space,
  Typography,
  message,
  Divider,
  Tooltip,
} from 'antd';
import {
  SettingOutlined,
  DragOutlined,
  EyeOutlined,
  EyeInvisibleOutlined,
  ReloadOutlined,
} from '@ant-design/icons';
import { DndContext, closestCenter } from '@dnd-kit/core';
import type { DragEndEvent } from '@dnd-kit/core';
import {
  arrayMove,
  SortableContext,
  useSortable,
  verticalListSortingStrategy,
} from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';

const { Text } = Typography;

export interface ColumnConfig {
  key: string;
  title: string;
  visible: boolean;
  locked?: boolean; // Colunas que nao podem ser ocultadas (ex: acoes)
}

interface ColumnSelectorProps {
  columns: ColumnConfig[];
  onChange: (columns: ColumnConfig[]) => void;
  onSave?: (columns: ColumnConfig[]) => void; // Salvar preferencias
  storageKey?: string; // Chave para localStorage
  buttonSize?: 'small' | 'middle' | 'large'; // Tamanho do botão
}

// Componente de item arrastavel
interface SortableItemProps {
  column: ColumnConfig;
  onToggle: (key: string) => void;
}

const SortableItem: React.FC<SortableItemProps> = ({ column, onToggle }) => {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } =
    useSortable({ id: column.key });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
  };

  return (
    <div
      ref={setNodeRef}
      style={style}
      {...attributes}
      className="column-selector-item"
    >
      <Space style={{ width: '100%', justifyContent: 'space-between' }}>
        <Space>
          {/* Drag handle separado */}
          <div {...listeners} style={{ cursor: 'move', padding: '4px' }}>
            <DragOutlined style={{ color: '#999' }} />
          </div>
          <Checkbox
            checked={column.visible}
            onChange={(e) => {
              e.stopPropagation();
              onToggle(column.key);
            }}
            disabled={column.locked}
            onClick={(e) => e.stopPropagation()}
          >
            {column.title}
          </Checkbox>
        </Space>
        {column.visible ? (
          <EyeOutlined style={{ color: '#52c41a' }} />
        ) : (
          <EyeInvisibleOutlined style={{ color: '#999' }} />
        )}
      </Space>
    </div>
  );
};

const ColumnSelector: React.FC<ColumnSelectorProps> = ({
  columns,
  onChange,
  onSave,
  storageKey,
  buttonSize = 'middle',
}) => {
  const [drawerVisible, setDrawerVisible] = useState(false);
  const [localColumns, setLocalColumns] = useState<ColumnConfig[]>(columns);

  // Carregar preferencias do localStorage ao montar
  React.useEffect(() => {
    if (storageKey) {
      const saved = localStorage.getItem(storageKey);
      if (saved) {
        try {
          const savedColumns = JSON.parse(saved) as ColumnConfig[];
          // Merge com colunas atuais para lidar com novas colunas
          const merged = columns.map((col) => {
            const savedCol = savedColumns.find((s) => s.key === col.key);
            return savedCol ? { ...col, visible: savedCol.visible } : col;
          });
          setLocalColumns(merged);
          onChange(merged);
        } catch (e) {
          console.error('Error loading column preferences:', e);
        }
      } else {
        // Se não tem preferencias salvas, usar as colunas iniciais
        setLocalColumns(columns);
      }
    } else {
      // Se não tem storageKey, usar as colunas iniciais
      setLocalColumns(columns);
    }
  }, [storageKey]); // So executar uma vez ao montar

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;

    if (over && active.id !== over.id) {
      const oldIndex = localColumns.findIndex((col) => col.key === active.id);
      const newIndex = localColumns.findIndex((col) => col.key === over.id);

      const newColumns = arrayMove(localColumns, oldIndex, newIndex);
      setLocalColumns(newColumns);
      onChange(newColumns);
    }
  };

  const handleToggleColumn = (key: string) => {
    const newColumns = localColumns.map((col) =>
      col.key === key ? { ...col, visible: !col.visible } : col,
    );
    setLocalColumns(newColumns);
    onChange(newColumns);
  };

  const handleShowAll = () => {
    const newColumns = localColumns.map((col) => ({ ...col, visible: true }));
    setLocalColumns(newColumns);
    onChange(newColumns);
    message.success('Todas as colunas exibidas');
  };

  const handleHideAll = () => {
    const newColumns = localColumns.map((col) =>
      col.locked ? col : { ...col, visible: false },
    );
    setLocalColumns(newColumns);
    onChange(newColumns);
    message.success('Colunas ocultadas (exceto fixas)');
  };

  const handleReset = () => {
    const defaultColumns = columns.map((col) => ({ ...col, visible: true }));
    setLocalColumns(defaultColumns);
    onChange(defaultColumns);

    if (storageKey) {
      localStorage.removeItem(storageKey);
    }

    message.success('Configuracao redefinida');
  };

  const handleSave = () => {
    if (storageKey) {
      localStorage.setItem(storageKey, JSON.stringify(localColumns));
      message.success('Preferencias salvas');
    }

    if (onSave) {
      onSave(localColumns);
    }

    setDrawerVisible(false);
  };

  const visibleCount = localColumns.filter((col) => col.visible).length;
  const totalCount = localColumns.length;

  return (
    <>
      <Tooltip title="Configurar Colunas">
        <Button
          icon={<SettingOutlined />}
          onClick={() => setDrawerVisible(true)}
          size={buttonSize}
        >
          Colunas ({visibleCount}/{totalCount})
        </Button>
      </Tooltip>

      <Drawer
        title="Configuracao de Colunas"
        placement="right"
        width={400}
        open={drawerVisible}
        onClose={() => setDrawerVisible(false)}
        extra={
          <Space>
            <Button icon={<ReloadOutlined />} onClick={handleReset} size="small">
              Redefinir
            </Button>
          </Space>
        }
        footer={
          <Space style={{ width: '100%', justifyContent: 'space-between' }}>
            <Space>
              <Button size="small" onClick={handleShowAll}>
                Mostrar Todas
              </Button>
              <Button size="small" onClick={handleHideAll}>
                Ocultar Todas
              </Button>
            </Space>
            <Space>
              <Button onClick={() => setDrawerVisible(false)}>Cancelar</Button>
              <Button type="primary" onClick={handleSave}>
                Salvar
              </Button>
            </Space>
          </Space>
        }
      >
        <Space direction="vertical" style={{ width: '100%' }} size="large">
          <div>
            <Text type="secondary">
              Arraste as colunas para reordena-las. Marque/desmarque para
              exibir/ocultar.
            </Text>
          </div>

          <Divider style={{ margin: '12px 0' }} />

          <DndContext collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
            <SortableContext
              items={localColumns.map((col) => col.key)}
              strategy={verticalListSortingStrategy}
            >
              <Space direction="vertical" style={{ width: '100%' }} size="small">
                {localColumns.map((column) => (
                  <SortableItem
                    key={column.key}
                    column={column}
                    onToggle={handleToggleColumn}
                  />
                ))}
              </Space>
            </SortableContext>
          </DndContext>

          <Divider style={{ margin: '12px 0' }} />

          <div>
            <Text type="secondary" style={{ fontSize: 12 }}>
               Dica: Colunas marcadas como fixas nao podem ser ocultadas
            </Text>
          </div>
        </Space>
      </Drawer>

      <style>{`
        .column-selector-item {
          padding: 12px;
          background: #fafafa;
          border-radius: 6px;
          border: 1px solid #f0f0f0;
          margin-bottom: 8px;
          transition: all 0.2s;
        }

        .column-selector-item:hover {
          background: #f0f0f0;
          border-color: #d9d9d9;
        }

        .column-selector-item:active {
          background: #e6e6e6;
        }
      `}</style>
    </>
  );
};

export default ColumnSelector;
