import React, { useEffect, useMemo, useState } from 'react';
import {
  Button,
  Card,
  Empty,
  List,
  Select,
  Space,
  Spin,
  Typography,
  message,
} from 'antd';
import {
  CloudServerOutlined,
  FileOutlined,
  ReloadOutlined,
} from '@ant-design/icons';
import { PageContainer, ProCard } from '@ant-design/pro-components';
import { consulAPI } from '../services/api';

interface ConfigHost {
  id: string;
  name: string;
  description?: string;
}

interface ConfigFileInfo {
  path: string;
  size?: number;
  modified?: string;
}

const { Text, Paragraph } = Typography;

const ConfigFiles: React.FC = () => {
  const [hosts, setHosts] = useState<ConfigHost[]>([]);
  const [selectedHost, setSelectedHost] = useState<string>();
  const [files, setFiles] = useState<ConfigFileInfo[]>([]);
  const [selectedFile, setSelectedFile] = useState<string>();
  const [fileContent, setFileContent] = useState<string>('');
  const [loadingHosts, setLoadingHosts] = useState(false);
  const [loadingFiles, setLoadingFiles] = useState(false);
  const [loadingContent, setLoadingContent] = useState(false);

  const fetchHosts = async () => {
    try {
      setLoadingHosts(true);
      const response = await consulAPI.listConfigHosts();
      const hostList = response.data.hosts || [];
      setHosts(hostList);
      if (!selectedHost && hostList.length) {
        setSelectedHost(hostList[0].id);
      }
    } catch (error: any) {
      const detail =
        error?.response?.data?.detail ||
        error?.message ||
        'Falha ao obter servidores';
      message.error(detail);
    } finally {
      setLoadingHosts(false);
    }
  };

  const fetchFiles = async (hostId: string) => {
    if (!hostId) return;
    try {
      setLoadingFiles(true);
      setSelectedFile(undefined);
      setFileContent('');
      const response = await consulAPI.listConfigFiles(hostId);
      setFiles(response.data.files || []);
    } catch (error: any) {
      const detail =
        error?.response?.data?.detail ||
        error?.message ||
        'Falha ao listar arquivos';
      message.error(detail);
      setFiles([]);
    } finally {
      setLoadingFiles(false);
    }
  };

  const fetchContent = async (hostId: string, path: string) => {
    if (!hostId || !path) return;
    try {
      setLoadingContent(true);
      const response = await consulAPI.getConfigFile(hostId, path);
      setFileContent(response.data.content || '');
    } catch (error: any) {
      const detail =
        error?.response?.data?.detail ||
        error?.message ||
        'Falha ao carregar arquivo';
      message.error(detail);
      setFileContent('');
    } finally {
      setLoadingContent(false);
    }
  };

  useEffect(() => {
    fetchHosts();
  }, []);

  useEffect(() => {
    if (selectedHost) {
      fetchFiles(selectedHost);
    } else {
      setFiles([]);
      setSelectedFile(undefined);
      setFileContent('');
    }
  }, [selectedHost]);

  const hostOptions = useMemo(
    () =>
      hosts.map((host) => ({
        label: host.name,
        value: host.id,
      })),
    [hosts],
  );

  return (
    <PageContainer
      header={{
        title: 'Arquivos de configuracao',
        subTitle: 'Visualize as configuracoes implementadas nos servidores monitorados',
      }}
    >
      <Space direction="vertical" size="large" style={{ width: '100%' }}>
        <Card>
          <Space size="large" wrap>
            <Space direction="vertical" size={4}>
              <Text strong>Servidor alvo</Text>
              <Select
                style={{ minWidth: 220 }}
                placeholder="Selecione um servidor"
                value={selectedHost}
                loading={loadingHosts}
                onChange={setSelectedHost}
                options={hostOptions}
                suffixIcon={<CloudServerOutlined />}
              />
            </Space>
            <Button
              icon={<ReloadOutlined />}
              onClick={() => {
                if (selectedHost) {
                  fetchFiles(selectedHost);
                } else {
                  fetchHosts();
                }
              }}
            >
              Atualizar
            </Button>
            <Paragraph type="secondary" style={{ maxWidth: 420, marginBottom: 0 }}>
              As credenciais de acesso ao servidor devem estar configuradas no backend a partir de variaveis de ambiente.
              Por padrao, utilize `CONFIG_HOSTS` para listar destinos permitidos.
            </Paragraph>
          </Space>
        </Card>

        <Space
          align="start"
          size="large"
          style={{ width: '100%', flexWrap: 'wrap' }}
        >
          <Card
            title="Arquivos disponiveis"
            style={{ flex: '0 0 320px', minHeight: 420 }}
            styles={{ body: { padding: 0 } }}
          >
            {loadingFiles ? (
              <div style={{ padding: 24, textAlign: 'center' }}>
                <Spin tip="Carregando lista de arquivos..." />
              </div>
            ) : files.length ? (
              <List
                dataSource={files}
                renderItem={(item) => (
                  <List.Item
                    key={item.path}
                    onClick={() => {
                      setSelectedFile(item.path);
                      if (selectedHost) {
                        fetchContent(selectedHost, item.path);
                      }
                    }}
                    style={{
                      cursor: 'pointer',
                      background:
                        selectedFile === item.path ? '#f0f7ff' : undefined,
                    }}
                  >
                    <Space direction="vertical" size={2} style={{ width: '100%' }}>
                      <Space>
                        <FileOutlined />
                        <span>{item.path}</span>
                      </Space>
                      <Text type="secondary" style={{ fontSize: 12 }}>
                        {item.size ? `${item.size} bytes` : ''}{' '}
                        {item.modified ? `| ${item.modified}` : ''}
                      </Text>
                    </Space>
                  </List.Item>
                )}
              />
            ) : (
              <div style={{ padding: 24 }}>
                <Empty description="Nenhum arquivo encontrado" />
              </div>
            )}
          </Card>

          <ProCard
            title={selectedFile || 'Selecione um arquivo'}
            extra={
              selectedFile && (
                <Space size="middle">
                  <Text type="secondary">
                    Visualizando conteudo somente leitura
                  </Text>
                </Space>
              )
            }
            style={{ flex: '1 1 520px', minHeight: 420 }}
            styles={{ body: { height: '100%', padding: 0 } }}
          >
            {loadingContent ? (
              <div style={{ padding: 48, textAlign: 'center' }}>
                <Spin tip="Carregando arquivo..." />
              </div>
            ) : selectedFile ? (
              <pre
                style={{
                  margin: 0,
                  padding: 16,
                  minHeight: 420,
                  maxHeight: 620,
                  overflow: 'auto',
                  background: '#0f172a',
                  color: '#e2e8f0',
                  fontFamily: 'monospace',
                  fontSize: 13,
                  lineHeight: 1.5,
                }}
              >
                {fileContent || '# Arquivo vazio ou nao acessivel'}
              </pre>
            ) : (
              <div style={{ padding: 48 }}>
                <Empty description="Selecione um arquivo para visualizar" />
              </div>
            )}
          </ProCard>
        </Space>
      </Space>
    </PageContainer>
  );
};

export default ConfigFiles;
