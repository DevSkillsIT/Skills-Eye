import React from 'react';
import { ConfigProvider, theme } from 'antd';
import ptBR from 'antd/locale/pt_BR';
import ProLayout from '@ant-design/pro-layout';
import { BrowserRouter, Route, Routes, Link } from 'react-router-dom';
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
  FileTextOutlined,
} from '@ant-design/icons';
import ConfigFiles from './pages/ConfigFiles';
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

const App: React.FC = () => {
  const [darkMode, setDarkMode] = React.useState(false);

  const menuItems = [
    {
      path: '/',
      name: 'Dashboard',
      icon: <DashboardOutlined />,
    },
    {
      path: '/services',
      name: 'Serviços',
      icon: <DatabaseOutlined />,
    },
    {
      path: '/service-groups',
      name: 'Grupos de Serviços',
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
      name: 'Presets de Serviços',
      icon: <AppstoreOutlined />,
    },
    {
      path: '/config-files',
      name: 'Arquivos de Configuração',
      icon: <FileTextOutlined />,
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
  ];

  return (
    <BrowserRouter>
      <ConfigProvider
        locale={ptBR}
        theme={{
          algorithm: darkMode ? theme.darkAlgorithm : theme.defaultAlgorithm,
        }}
      >
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
            <Route path="/config-files" element={<ConfigFiles />} />
            <Route path="/audit-log" element={<AuditLog />} />
            <Route path="/installer" element={<Installer />} />
          </Routes>
        </ProLayout>
      </ConfigProvider>
    </BrowserRouter>
  );
};

export default App;




