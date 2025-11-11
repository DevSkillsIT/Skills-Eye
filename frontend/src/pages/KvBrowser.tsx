import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { useConsulDelete } from '../hooks/useConsulDelete';
import {
  Button,
  Drawer,
  Input,
  App,
  Popconfirm,
  Tag,
  Space,
  Card,
  Statistic,
  Row,
  Col,
  Tooltip,
  Select,
  Descriptions,
} from 'antd';
import {
  PageContainer,
  ProTable,
  ModalForm,
  ProFormText,
  ProFormTextArea,
} from '@ant-design/pro-components';
import {
  EyeOutlined,
  ReloadOutlined,
  SaveOutlined,
  DeleteOutlined,
  PlusOutlined,
  SearchOutlined,
  FolderOutlined,
  FileTextOutlined,
  FileOutlined,
  HomeOutlined,
  CopyOutlined,
  DownloadOutlined,
} from '@ant-design/icons';
import { consulAPI } from '../services/api';
import type { KVTreeResponse } from '../services/api';

interface KVEntry {
  key: string;
  preview: string;
  type: 'json' | 'text';
  raw: any;
  size: number;
  createIndex?: number;
  modifyIndex?: number;
}

const DEFAULT_PREFIX = 'skills/eye/';
const COMMON_PREFIXES = [
  { label: 'Skills CM (padrão)', value: 'skills/eye/' },
  { label: 'ConsulManager (sistema)', value: 'ConsulManager/' },
  { label: 'Root (todos os KVs)', value: '' },
];

type TableColumn<T> = import('@ant-design/pro-components').ProColumns<T>;

const KvBrowser: React.FC = () => {
  const { message } = App.useApp();
  const [prefix, setPrefix] = useState<string>(DEFAULT_PREFIX);
  const [searchText, setSearchText] = useState<string>('');
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

  /**
   * PASSO 1: Busca as chaves do Consul KV
   * Agora aceita QUALQUER prefixo, não apenas skills/eye/
   */
  const fetchTree = useCallback(
    async (currentPrefix: string) => {
      setLoading(true);
      try {
        // IMPORTANTE: Remove validação de prefixo para permitir navegação livre
        const response = await consulAPI.getKVTree(currentPrefix || '');
        const data = response.data as KVTreeResponse;
        const rows: KVEntry[] = Object.entries(data.data || {}).map(([key, item]: [string, any]) => {
          let type: KVEntry['type'] = 'text';
          let preview = '';

          // Backend agora retorna: {value: ..., metadata: {CreateIndex, ModifyIndex, ...}}
          const value = item.value !== undefined ? item.value : item; // Fallback para formato antigo
          const metadata = item.metadata || {};
          const rawValue = value;

          // PASSO 1.1: Detectar tipo do valor
          if (typeof value === 'object' && value !== null) {
            type = 'json';
            preview = JSON.stringify(value);
          } else if (value !== undefined && value !== null) {
            preview = String(value);
          }

          // PASSO 1.2: Truncar preview longo
          if (preview.length > 120) {
            preview = `${preview.slice(0, 117)}...`;
          }

          return {
            key,
            preview,
            type,
            raw: rawValue,
            size: new Blob([JSON.stringify(value)]).size, // Tamanho aproximado em bytes
            createIndex: metadata.CreateIndex,
            modifyIndex: metadata.ModifyIndex,
          };
        });
        setEntries(rows);
      } catch (error: unknown) {
        // Se erro 403 (prefixo proibido), avisar mas não bloquear
        const err = error as { response?: { status?: number; data?: { detail?: string } } };
        const detail = err?.response?.data?.detail || 'Falha ao carregar chaves KV';
        if (err?.response?.status === 403) {
          message.warning(
            `Prefixo restrito pelo backend: ${detail}. Algumas chaves podem não estar acessíveis.`,
          );
        } else {
          message.error(detail);
        }
      } finally {
        setLoading(false);
      }
    },
    [message],
  );

  useEffect(() => {
    fetchTree(prefix);
  }, [fetchTree, prefix]);

  /**
   * PASSO 2: Filtrar entries baseado na busca
   * Busca por chave OU valor (case-insensitive)
   */
  const filteredEntries = useMemo(() => {
    if (!searchText.trim()) return entries;

    const lowerSearch = searchText.toLowerCase();
    return entries.filter((entry) => {
      const keyMatch = entry.key.toLowerCase().includes(lowerSearch);
      const valueMatch = entry.preview.toLowerCase().includes(lowerSearch);
      return keyMatch || valueMatch;
    });
  }, [entries, searchText]);

  /**
   * PASSO 3: Estatísticas
   */
  const stats = useMemo(() => {
    const totalKeys = filteredEntries.length;
    const jsonKeys = filteredEntries.filter((e) => e.type === 'json').length;
    const textKeys = filteredEntries.filter((e) => e.type === 'text').length;
    const totalSize = filteredEntries.reduce((acc, e) => acc + e.size, 0);

    return { totalKeys, jsonKeys, textKeys, totalSize };
  }, [filteredEntries]);

  /**
   * PASSO 4: Navegação por breadcrumb
   */
  const breadcrumbItems = useMemo(() => {
    if (!prefix) return [{ title: <HomeOutlined /> }];

    const parts = prefix.split('/').filter(Boolean);
    const items = [
      {
        title: <HomeOutlined />,
        onClick: () => setPrefix(''),
      },
    ];

    parts.forEach((part, index) => {
      const path = parts.slice(0, index + 1).join('/') + '/';
      items.push({
        title: <span>{part}</span>,
        onClick: () => setPrefix(path),
      });
    });

    return items;
  }, [prefix]);

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
      // Nova chave - sugerir prefixo atual
      setEditorKey(prefix);
      setEditorValue('');
    }
    setEditorOpen(true);
  };

  const handleSave = async (values: { key: string; value: string }) => {
    try {
      let parsed: any = values.value;
      const trimmed = values.value.trim();

      // Tentar parsear JSON
      if (trimmed.startsWith('{') || trimmed.startsWith('[')) {
        try {
          parsed = JSON.parse(values.value);
        } catch {
          message.warning('Valor parece JSON mas não é válido. Salvando como texto.');
        }
      }

      await consulAPI.putKV(values.key, parsed);
      message.success('Valor salvo no Consul KV');
      setEditorOpen(false);
      fetchTree(prefix);
      return true;
    } catch (error: any) {
      const detail = error?.response?.data?.detail || error?.message || 'Erro desconhecido';
      message.error(`Falha ao salvar chave: ${detail}`);
      return false;
    }
  };

  const handleDelete = async (key: string) => {
    await deleteResource({ service_id: key, kv_key: key } as any);
  };

  /**
   * PASSO 5: Copiar valor para clipboard
   */
  const handleCopy = (text: string) => {
    navigator.clipboard.writeText(text);
    message.success('Copiado para área de transferência');
  };

  /**
   * PASSO 6: Exportar dados como JSON
   */
  const handleExport = () => {
    const dataStr = JSON.stringify(
      filteredEntries.map((e) => ({ key: e.key, value: e.raw })),
      null,
      2,
    );
    const blob = new Blob([dataStr], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `consul-kv-${prefix.replace(/\//g, '-') || 'root'}-${Date.now()}.json`;
    a.click();
    URL.revokeObjectURL(url);
    message.success('Dados exportados com sucesso');
  };

  const columns = useMemo<TableColumn<KVEntry>[]>(
    () => [
      {
        title: 'Chave',
        dataIndex: 'key',
        ellipsis: true,
        width: '40%',
        render: (_, record) => (
          <Space>
            {record.type === 'json' ? (
              <FileTextOutlined style={{ color: '#1890ff' }} />
            ) : (
              <FileOutlined style={{ color: '#8c8c8c' }} />
            )}
            <Tooltip title={record.key}>
              <span style={{ fontFamily: 'monospace' }}>{record.key}</span>
            </Tooltip>
            <Tooltip title="Copiar chave">
              <Button
                type="text"
                size="small"
                icon={<CopyOutlined />}
                onClick={() => handleCopy(record.key)}
              />
            </Tooltip>
          </Space>
        ),
      },
      {
        title: 'Tipo',
        dataIndex: 'type',
        width: 100,
        filters: [
          { text: 'JSON', value: 'json' },
          { text: 'Texto', value: 'text' },
        ],
        onFilter: (value, record) => record.type === value,
        render: (_, record) => (
          <Tag color={record.type === 'json' ? 'blue' : 'default'}>
            {record.type === 'json' ? 'JSON' : 'Texto'}
          </Tag>
        ),
      },
      {
        title: 'Tamanho',
        dataIndex: 'size',
        width: 120,
        sorter: (a, b) => a.size - b.size,
        render: (_: unknown, record: KVEntry) => {
          const size = record.size;
          if (size < 1024) return `${size} B`;
          if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`;
          return `${(size / (1024 * 1024)).toFixed(1)} MB`;
        },
      },
      {
        title: 'Versão',
        dataIndex: 'modifyIndex',
        width: 140,
        sorter: (a, b) => (a.modifyIndex || 0) - (b.modifyIndex || 0),
        render: (_: unknown, record: KVEntry) => {
          if (!record.modifyIndex) return '-';
          const isModified = record.modifyIndex !== record.createIndex;
          const edits = record.modifyIndex - (record.createIndex || 0);
          return (
            <Tooltip title={
              isModified
                ? `Modificado ${edits} vez(es) - Versão ${record.modifyIndex}`
                : `Original - Versão ${record.createIndex}`
            }>
              <Space size={4} direction="vertical" style={{ width: '100%' }}>
                <Tag color={isModified ? 'orange' : 'green'} style={{ margin: 0, width: 'fit-content' }}>
                  v{record.modifyIndex}
                </Tag>
                {isModified && edits > 0 && (
                  <Tag color="blue" style={{ fontSize: '10px', margin: 0, width: 'fit-content' }}>
                    {edits} ediç{edits === 1 ? 'ão' : 'ões'}
                  </Tag>
                )}
              </Space>
            </Tooltip>
          );
        },
      },
      {
        title: 'Pré-visualização',
        dataIndex: 'preview',
        ellipsis: true,
        render: (_: unknown, record: KVEntry) => (
          <Tooltip title={record.preview}>
            <span style={{ fontFamily: 'monospace', fontSize: '0.9em', color: '#595959' }}>
              {record.preview}
            </span>
          </Tooltip>
        ),
      },
      {
        title: 'Ações',
        valueType: 'option',
        width: 140,
        fixed: 'right',
        render: (_, record) => {
          // IMPORTANTE: Edição/remoção permitida APENAS em skills/eye/
          const isEditable = record.key.startsWith('skills/eye/');

          return [
            <Tooltip key="view" title="Visualizar conteúdo completo">
              <Button
                type="text"
                size="large"
                icon={<EyeOutlined style={{ fontSize: '18px' }} />}
                onClick={() => openViewer(record)}
              />
            </Tooltip>,
            isEditable && (
              <Tooltip key="edit" title="Editar valor">
                <Button
                  type="text"
                  size="large"
                  icon={<SaveOutlined style={{ fontSize: '18px', color: '#1890ff' }} />}
                  onClick={() => openEditor(record)}
                />
              </Tooltip>
            ),
            isEditable && (
              <Popconfirm
                key="delete"
                title="Remover esta chave?"
                description="Esta ação não pode ser desfeita."
                onConfirm={() => handleDelete(record.key)}
                okText="Remover"
                cancelText="Cancelar"
              >
                <Tooltip title="Remover chave">
                  <Button
                    type="text"
                    size="large"
                    danger
                    icon={<DeleteOutlined style={{ fontSize: '18px' }} />}
                  />
                </Tooltip>
              </Popconfirm>
            ),
          ].filter(Boolean); // Remove itens null/undefined
        },
      },
    ],
    [prefix],
  );

  return (
    <PageContainer
      header={{
        title: 'Consul KV Browser',
        subTitle: 'Navegue e gerencie chaves/valores do Consul Key-Value Store',
        breadcrumb: {
          items: breadcrumbItems,
        },
      }}
      extra={[
        <Button
          key="export"
          icon={<DownloadOutlined />}
          onClick={handleExport}
          disabled={filteredEntries.length === 0}
        >
          Exportar JSON
        </Button>,
        <Button
          key="refresh"
          icon={<ReloadOutlined />}
          onClick={() => {
            console.log(`[KvBrowser] 🔄 Botão ATUALIZAR clicado - Prefixo atual: "${prefix}"`);
            fetchTree(prefix);
          }}
        >
          Atualizar
        </Button>,
        <Button key="create" type="primary" icon={<PlusOutlined />} onClick={() => openEditor()}>
          Nova chave
        </Button>,
      ]}
    >
      {/* ESTATÍSTICAS */}
      <Card style={{ marginBottom: 16 }}>
        <Row gutter={16}>
          <Col span={6}>
            <Statistic
              title="Total de Chaves"
              value={stats.totalKeys}
              prefix={<FolderOutlined />}
            />
          </Col>
          <Col span={6}>
            <Statistic
              title="JSON"
              value={stats.jsonKeys}
              valueStyle={{ color: '#1890ff' }}
              prefix={<FileTextOutlined />}
            />
          </Col>
          <Col span={6}>
            <Statistic
              title="Texto"
              value={stats.textKeys}
              valueStyle={{ color: '#8c8c8c' }}
              prefix={<FileOutlined />}
            />
          </Col>
          <Col span={6}>
            <Statistic
              title="Tamanho Total"
              value={
                stats.totalSize < 1024
                  ? `${stats.totalSize} B`
                  : stats.totalSize < 1024 * 1024
                  ? `${(stats.totalSize / 1024).toFixed(1)} KB`
                  : `${(stats.totalSize / (1024 * 1024)).toFixed(1)} MB`
              }
            />
          </Col>
        </Row>
      </Card>

      {/* FILTROS E NAVEGAÇÃO */}
      <Card style={{ marginBottom: 16 }}>
        <Space direction="vertical" style={{ width: '100%' }} size="middle">
          <Row gutter={16}>
            <Col span={12}>
              <Space.Compact style={{ width: '100%' }}>
                <Select
                  style={{ width: 200 }}
                  value={prefix}
                  onChange={setPrefix}
                  options={COMMON_PREFIXES}
                  placeholder="Prefixo rápido"
                />
                <Input
                  value={prefix}
                  onChange={(e) => setPrefix(e.target.value)}
                  placeholder="Digite o prefixo personalizado (ex: apps/myapp/)"
                  prefix={<FolderOutlined />}
                />
              </Space.Compact>
            </Col>
            <Col span={12}>
              <Input
                value={searchText}
                onChange={(e) => setSearchText(e.target.value)}
                placeholder="Buscar por chave ou valor..."
                prefix={<SearchOutlined />}
                allowClear
              />
            </Col>
          </Row>
          {searchText && (
            <div style={{ color: '#8c8c8c', fontSize: '0.9em' }}>
              Mostrando {filteredEntries.length} de {entries.length} chaves
            </div>
          )}
        </Space>
      </Card>

      {/* TABELA */}
      <ProTable<KVEntry>
        rowKey="key"
        loading={loading}
        search={false}
        pagination={{
          defaultPageSize: 20,
          defaultCurrent: 1,
          pageSizeOptions: [10, 20, 50, 100, 200],
          showSizeChanger: true,
          showQuickJumper: true,
          showTotal: (total, range) => {
            console.log(`[KvBrowser] 📊 Paginação renderizada: ${range[0]}-${range[1]} de ${total} itens`);
            return `${range[0]}-${range[1]} de ${total} chaves`;
          },
          onChange: (page, pageSize) => {
            console.log(`[KvBrowser] 📄 Página mudou para: ${page} (tamanho: ${pageSize})`);
          },
          onShowSizeChange: (current, size) => {
            console.log(`[KvBrowser] 📏 Tamanho alterado para: ${size} itens/página`);
          },
        }}
        columns={columns}
        dataSource={filteredEntries}
        options={{
          reload: false,
          setting: { draggable: true },
          density: true,
        }}
        toolBarRender={false}
        locale={{
          emptyText: !loading && entries.length === 0 ? (
            <div style={{ padding: '48px 0', textAlign: 'center' }}>
              <FolderOutlined style={{ fontSize: '48px', color: '#d9d9d9', marginBottom: 16 }} />
              <div style={{ fontSize: '16px', color: '#8c8c8c', marginBottom: 8 }}>
                Namespace vazio
              </div>
              <div style={{ fontSize: '14px', color: '#bfbfbf' }}>
                Não há chaves armazenadas no prefixo <strong>{prefix || 'root'}</strong>
              </div>
              <div style={{ fontSize: '12px', color: '#d9d9d9', marginTop: 8 }}>
                Selecione outro namespace ou crie uma nova chave
              </div>
            </div>
          ) : undefined,
        }}
      />

      {/* DRAWER DE VISUALIZAÇÃO */}
      <Drawer
        width={720}
        title={
          <Space>
            <FileTextOutlined />
            Visualizar Chave
          </Space>
        }
        open={!!selectedEntry}
        onClose={() => setSelectedEntry(null)}
        extra={
          <Space>
            <Button
              icon={<CopyOutlined />}
              onClick={() =>
                selectedEntry &&
                handleCopy(
                  typeof selectedEntry.raw === 'object'
                    ? JSON.stringify(selectedEntry.raw, null, 2)
                    : String(selectedEntry.raw),
                )
              }
            >
              Copiar
            </Button>
            <Button type="primary" icon={<SaveOutlined />} onClick={() => {
              if (selectedEntry) {
                setSelectedEntry(null);
                openEditor(selectedEntry);
              }
            }}>
              Editar
            </Button>
          </Space>
        }
      >
        {selectedEntry && (
          <>
            <Descriptions column={1} bordered size="small" style={{ marginBottom: 16 }}>
              <Descriptions.Item label="Chave">
                <span style={{ fontFamily: 'monospace' }}>{selectedEntry.key}</span>
              </Descriptions.Item>
              <Descriptions.Item label="Tipo">
                <Tag color={selectedEntry.type === 'json' ? 'blue' : 'default'}>
                  {selectedEntry.type === 'json' ? 'JSON' : 'Texto'}
                </Tag>
              </Descriptions.Item>
              <Descriptions.Item label="Tamanho">
                {selectedEntry.size < 1024
                  ? `${selectedEntry.size} bytes`
                  : `${(selectedEntry.size / 1024).toFixed(2)} KB`}
              </Descriptions.Item>
            </Descriptions>
            <div
              style={{
                background: '#f5f5f5',
                padding: 16,
                borderRadius: 4,
                border: '1px solid #d9d9d9',
              }}
            >
              <pre
                style={{
                  whiteSpace: 'pre-wrap',
                  wordBreak: 'break-all',
                  margin: 0,
                  fontFamily: 'Consolas, Monaco, monospace',
                  fontSize: '0.9em',
                }}
              >
                {selectedEntry.raw
                  ? typeof selectedEntry.raw === 'object'
                    ? JSON.stringify(selectedEntry.raw, null, 2)
                    : String(selectedEntry.raw)
                  : '(vazio)'}
              </pre>
            </div>
          </>
        )}
      </Drawer>

      {/* MODAL DE EDIÇÃO/CRIAÇÃO */}
      <ModalForm<{ key: string; value: string }>
        title={editorKey ? 'Editar chave' : 'Criar nova chave'}
        width={720}
        open={editorOpen}
        initialValues={{ key: editorKey, value: editorValue }}
        onFinish={handleSave}
        modalProps={{
          destroyOnClose: true,
          onCancel: () => setEditorOpen(false),
        }}
      >
        <ProFormText
          name="key"
          label="Chave"
          placeholder="Ex: skills/eye/config/settings"
          rules={[{ required: true, message: 'Informe a chave completa' }]}
          disabled={Boolean(editorKey)} // Não permite editar chave existente
          tooltip="Caminho completo da chave no Consul KV"
        />
        <ProFormTextArea
          name="value"
          label="Valor"
          fieldProps={{ autoSize: { minRows: 8, maxRows: 20 } }}
          placeholder='JSON: {"key": "value"} ou texto simples'
          rules={[{ required: true, message: 'Informe um valor' }]}
          tooltip="Pode ser JSON (objeto/array) ou texto simples"
        />
      </ModalForm>
    </PageContainer>
  );
};

export default KvBrowser;
