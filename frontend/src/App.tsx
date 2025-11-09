import React, { useEffect } from 'react';
import { ConfigProvider, theme, App as AntdApp } from 'antd';
import ptBR from 'antd/locale/pt_BR';
import ProLayout from '@ant-design/pro-layout';
import { BrowserRouter, Route, Routes, Link } from 'react-router-dom';
import { loadNamingConfig } from './utils/namingUtils';
import { MetadataFieldsProvider } from './contexts/MetadataFieldsContext';
import {
  DashboardOutlined,
  DatabaseOutlined,
  CloudServerOutlined,
  HddOutlined,
  RadarChartOutlined,
  ToolOutlined,
  AppstoreOutlined,
  AppstoreAddOutlined,
  FolderOutlined,
  HistoryOutlined,
  SettingOutlined,
} from '@ant-design/icons';
import Dashboard from './pages/Dashboard';
import Services from './pages/Services';
import ServiceGroups from './pages/ServiceGroups';
import Hosts from './pages/Hosts';
import Exporters from './pages/Exporters';
import BlackboxTargets from './pages/BlackboxTargets';
import Installer from './pages/Installer';
import KvBrowser from './pages/KvBrowser';
import ServicePresets from './pages/ServicePresets';
import BlackboxGroups from './pages/BlackboxGroups';
import AuditLog from './pages/AuditLog';
import PrometheusConfig from './pages/PrometheusConfig';
import MetadataFields from './pages/MetadataFields';
import MonitoringTypes from './pages/MonitoringTypes';
import ReferenceValues from './pages/ReferenceValues';
import Settings from './pages/Settings';

const App: React.FC = () => {
  const [darkMode, setDarkMode] = React.useState(false);

  // Carregar configuração de naming multi-site do backend
  useEffect(() => {
    loadNamingConfig().catch((error) => {
      console.warn('[App] Erro ao carregar naming config:', error);
    });
  }, []);

  const menuItems = [
    {
      path: '/',
      name: 'Dashboard',
      icon: <DashboardOutlined />,
    },
    {
      path: '/services',
      name: 'Servicos',
      icon: <DatabaseOutlined />,
    },
    {
      path: '/service-groups',
      name: 'Grupos de Servicos',
      icon: <AppstoreOutlined />,
    },
    {
      path: '/hosts',
      name: 'Hosts',
      icon: <HddOutlined />,
    },
    {
      path: '/exporters',
      name: 'Exporters',
      icon: <CloudServerOutlined />,
    },
    {
      path: '/blackbox',
      name: 'Alvos Blackbox',
      icon: <RadarChartOutlined />,
    },
    {
      path: '/blackbox-groups',
      name: 'Grupos Blackbox',
      icon: <AppstoreAddOutlined />,
    },
    {
      path: '/presets',
      name: 'Presets de Servicos',
      icon: <AppstoreOutlined />,
    },
    {
      path: '/prometheus-config',
      name: 'Config Prometheus',
      icon: <SettingOutlined />,
    },
    {
      path: '/metadata-fields',
      name: 'Campos Metadata',
      icon: <DatabaseOutlined />,
    },
    {
      path: '/kv-browser',
      name: 'Armazenamento KV',
      icon: <FolderOutlined />,
    },
    {
      path: '/audit-log',
      name: 'Log de Auditoria',
      icon: <HistoryOutlined />,
    },
    {
      path: '/installer',
      name: 'Instalar Exporters',
      icon: <ToolOutlined />,
    },
    {
      path: '/monitoring-types',
      name: 'Tipos de Monitoramento',
      icon: <DatabaseOutlined />,
    },
    {
      path: '/reference-values',
      name: 'Valores de Referência',
      icon: <DatabaseOutlined />,
    },
    {
      path: '/settings',
      name: 'Configurações',
      icon: <SettingOutlined />,
    },
  ];

  return (
    <BrowserRouter>
      <ConfigProvider
        locale={ptBR}
        theme={{
          algorithm: darkMode ? theme.darkAlgorithm : theme.defaultAlgorithm,
        }}
      >
        <AntdApp>
        <MetadataFieldsProvider>
        <ProLayout
          title="Consul Manager"
          fixedHeader
          fixSiderbar
          menuItemRender={(item, dom) => (
            <Link to={item.path || '/'}>{dom}</Link>
          )}
          route={{
            path: '/',
            routes: menuItems,
          }}
          rightContentRender={() => (
            <a
              onClick={() => setDarkMode((value) => !value)}
              style={{ marginRight: 16 }}
            >
              {darkMode ? 'Modo claro' : 'Modo escuro'}
            </a>
          )}
        >
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/services" element={<Services />} />
            <Route path="/service-groups" element={<ServiceGroups />} />
            <Route path="/hosts" element={<Hosts />} />
            <Route path="/exporters" element={<Exporters />} />
            <Route path="/blackbox" element={<BlackboxTargets />} />
            <Route path="/blackbox-groups" element={<BlackboxGroups />} />
            <Route path="/presets" element={<ServicePresets />} />
            <Route path="/kv-browser" element={<KvBrowser />} />
            <Route path="/prometheus-config" element={<PrometheusConfig />} />
            <Route path="/metadata-fields" element={<MetadataFields />} />
            <Route path="/audit-log" element={<AuditLog />} />
            <Route path="/installer" element={<Installer />} />
            <Route path="/monitoring-types" element={<MonitoringTypes />} />
            <Route path="/reference-values" element={<ReferenceValues />} />
            <Route path="/settings" element={<Settings />} />
          </Routes>
        </ProLayout>
        </MetadataFieldsProvider>
        </AntdApp>
      </ConfigProvider>
    </BrowserRouter>
  );
};

export default App;
