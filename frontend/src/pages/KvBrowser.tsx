import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { useConsulDelete } from '../hooks/useConsulDelete';
import { Button, Drawer, Input, App, Popconfirm, Tag } from 'antd';
import { PageContainer, ProTable, ModalForm, ProFormText, ProFormTextArea } from '@ant-design/pro-components';
import { EyeOutlined, ReloadOutlined, SaveOutlined, DeleteOutlined, PlusOutlined } from '@ant-design/icons';
import { consulAPI } from '../services/api';
import type { KVTreeResponse } from '../services/api';

interface KVEntry {
  key: string;
  preview: string;
  type: 'json' | 'text';
  raw: any;
}

const DEFAULT_PREFIX = 'skills/cm/';
type TableColumn<T> = import('@ant-design/pro-components').ProColumns<T>;

const KvBrowser: React.FC = () => {
  const { message } = App.useApp();
  const [prefix, setPrefix] = useState<string>(DEFAULT_PREFIX);
  const [loading, setLoading] = useState(false);
  const [entries, setEntries] = useState<KVEntry[]>([]);
  const [selectedEntry, setSelectedEntry] = useState<KVEntry | null>(null);
  const [editorOpen, setEditorOpen] = useState(false);
  const [editorKey, setEditorKey] = useState<string>('');
  const [editorValue, setEditorValue] = useState<string>('');

  // Hook para DELETE de chaves KV
  const { deleteResource } = useConsulDelete({
    deleteFn: async (payload: any) => consulAPI.deleteKV(payload.kv_key),
    successMessage: 'Chave removida com sucesso',
    errorMessage: 'Erro ao remover chave',
    onSuccess: () => {
      fetchTree(prefix);
    },
  });

  const fetchTree = useCallback(async (currentPrefix: string) => {
    setLoading(true);
    try {
      const response = await consulAPI.getKVTree(currentPrefix);
      const data = response.data as KVTreeResponse;
      const rows: KVEntry[] = Object.entries(data.data || {}).map(([key, value]) => {
        let type: KVEntry['type'] = 'text';
        let preview = '';
        if (typeof value === 'object' && value !== null) {
          type = 'json';
          preview = JSON.stringify(value);
        } else if (value !== undefined && value !== null) {
          preview = String(value);
        }
        if (preview.length > 80) {
          preview = `${preview.slice(0, 77)}...`;
        }
        return {
          key,
          preview,
          type,
          raw: value,
        };
      });
      setEntries(rows);
    } catch (error: any) {
      message.error(error?.response?.data?.detail || 'Falha ao carregar chaves KV');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchTree(prefix);
  }, [fetchTree, prefix]);

  const openViewer = (record: KVEntry) => {
    setSelectedEntry(record);
  };

  const openEditor = (record?: KVEntry) => {
    if (record) {
      setEditorKey(record.key);
      setEditorValue(
        typeof record.raw === 'object' && record.raw !== null
          ? JSON.stringify(record.raw, null, 2)
          : String(record.raw ?? ''),
      );
    } else {
      setEditorKey('');
      setEditorValue('');
    }
    setEditorOpen(true);
  };

  const handleSave = async (values: { key: string; value: string }) => {
    try {
      let parsed: any = values.value;
      const trimmed = values.value.trim();
      if (trimmed.startsWith('{') || trimmed.startsWith('[')) {
        parsed = JSON.parse(values.value);
      }
      await consulAPI.putKV(values.key, parsed);
      message.success('Valor salvo no Consul');
      setEditorOpen(false);
      fetchTree(prefix);
      return true;
    } catch (error: any) {
      const detail = error?.response?.data?.detail || error?.message || 'Erro desconhecido';
      message.error(`Falha ao salvar chave: ${detail}`);
      return false;
    }
  };

  /**
   * Deleta uma chave KV usando o hook useConsulDelete
   * Usa APENAS dados do record - ZERO valores hardcoded
   */
  const handleDelete = async (key: string) => {
    await deleteResource({ service_id: key, kv_key: key } as any);
  };

  const columns = useMemo<TableColumn<KVEntry>[]>(
    () => [
      {
        title: 'Chave',
        dataIndex: 'key',
        ellipsis: true,
        copyable: true,
      },
      {
        title: 'Tipo',
        dataIndex: 'type',
        width: 120,
        render: (_, record) => (
          <Tag color={record.type === 'json' ? 'blue' : 'default'}>
            {record.type === 'json' ? 'JSON' : 'Texto'}
          </Tag>
        ),
      },
      {
        title: 'Pre-visualizacao',
        dataIndex: 'preview',
        ellipsis: true,
      },
      {
        title: 'Acoes',
        valueType: 'option',
        width: 200,
        render: (_, record) => [
          <Button
            key="view"
            type="link"
            icon={<EyeOutlined />}
            onClick={() => openViewer(record)}
          >
            Visualizar
          </Button>,
          <Button
            key="edit"
            type="link"
            icon={<SaveOutlined />}
            onClick={() => openEditor(record)}
          >
            Editar
          </Button>,
          <Popconfirm
            key="delete"
            title="Remover esta chave?"
            onConfirm={() => handleDelete(record.key)}
            okText="Remover"
            cancelText="Cancelar"
          >
            <Button type="link" danger icon={<DeleteOutlined />}>
              Remover
            </Button>
          </Popconfirm>,
        ],
      },
    ],
    [prefix],
  );

  return (
    <PageContainer
      header={{
        title: 'Consul KV Browser',
        subTitle: 'Gerencie valores dentro do namespace skills/cm/',
      }}
      extra={[
        <Input
          key="prefix"
          value={prefix}
          onChange={(event) => setPrefix(event.target.value)}
          placeholder="Prefixo (ex.: skills/cm/)"
          style={{ width: 260 }}
        />,
        <Button key="refresh" icon={<ReloadOutlined />} onClick={() => fetchTree(prefix)}>
          Atualizar
        </Button>,
        <Button key="create" type="primary" icon={<PlusOutlined />} onClick={() => openEditor()}>
          Nova chave
        </Button>,
      ]}
    >
      <ProTable<KVEntry>
        rowKey="key"
        loading={loading}
        search={false}
        pagination={{ pageSize: 10 }}
        columns={columns}
        dataSource={entries}
        options={{ reload: false, setting: { draggable: true } }}
      />

      <Drawer
        width={520}
        title={selectedEntry?.key}
        open={!!selectedEntry}
        onClose={() => setSelectedEntry(null)}
      >
        <pre style={{ whiteSpace: 'pre-wrap' }}>
          {selectedEntry && selectedEntry.raw
            ? typeof selectedEntry.raw === 'object'
              ? JSON.stringify(selectedEntry.raw, null, 2)
              : String(selectedEntry.raw)
            : ''}
        </pre>
      </Drawer>

      <ModalForm<{ key: string; value: string }>
        title={editorKey ? 'Editar chave' : 'Criar chave'}
        width={520}
        open={editorOpen}
        initialValues={{ key: editorKey, value: editorValue }}
        onFinish={handleSave}
        modalProps={{
          destroyOnHidden: true,
          onCancel: () => setEditorOpen(false),
        }}
      >
        <ProFormText
          name="key"
          label="Chave"
          placeholder="skills/cm/..."
          rules={[{ required: true, message: 'Informe a chave completa' }]}
          disabled={Boolean(editorKey)}
        />
        <ProFormTextArea
          name="value"
          label="Valor"
          fieldProps={{ autoSize: { minRows: 6, maxRows: 12 } }}
          placeholder="JSON ou texto simples"
          rules={[{ required: true, message: 'Informe um valor' }]}
        />
      </ModalForm>
    </PageContainer>
  );
};

export default KvBrowser;

