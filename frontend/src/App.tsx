import React, { useEffect } from 'react';
import { ConfigProvider, theme, App as AntdApp } from 'antd';
import ptBR from 'antd/locale/pt_BR';
import ProLayout from '@ant-design/pro-layout';
import { BrowserRouter, Route, Routes, Link } from 'react-router-dom';
import { loadNamingConfig } from './utils/namingUtils';
import { MetadataFieldsProvider } from './contexts/MetadataFieldsContext';
import { SitesProvider } from './hooks/useSites';
import { NodesProvider } from './contexts/NodesContext';
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
// ⭐ NOVO - Sistema de Refatoração v2.0 (2025-11-13)
import DynamicMonitoringPage from './pages/DynamicMonitoringPage';
import MonitoringRules from './pages/MonitoringRules';
// import Settings from './pages/Settings'; // REMOVIDO - Funcionalidades migradas para MetadataFields
// ⭐ SPRINT 2 (2025-11-15) - Observability & Cache Management
import CacheManagement from './pages/CacheManagement';

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
      path: '/monitoramento',
      name: 'Monitoramento',
      icon: <RadarChartOutlined />,
      children: [
        {
          path: '/services',
          name: 'Services',
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
        // ⭐ NOVAS PÁGINAS DINÂMICAS - v2.0 (2025-11-13)
        {
          path: '/monitoring/network-probes',
          name: 'Network Probes',
          icon: <RadarChartOutlined />,
        },
        {
          path: '/monitoring/web-probes',
          name: 'Web Probes',
          icon: <RadarChartOutlined />,
        },
        {
          path: '/monitoring/system-exporters',
          name: 'System Exporters',
          icon: <CloudServerOutlined />,
        },
        {
          path: '/monitoring/database-exporters',
          name: 'Database Exporters',
          icon: <DatabaseOutlined />,
        },
        {
          path: '/monitoring/rules',
          name: 'Regras de Categorização',
          icon: <SettingOutlined />,
        },
      ],
    },
    {
      path: '/configuracoes',
      name: 'Configurações',
      icon: <SettingOutlined />,
      children: [
        {
          path: '/metadata-fields',
          name: 'Campos Metadata',
          icon: <DatabaseOutlined />,
        },
        {
          path: '/prometheus-config',
          name: 'Prometheus Config',
          icon: <SettingOutlined />,
        },
        {
          path: '/monitoring-types',
          name: 'Tipos de Monitoramento',
          icon: <RadarChartOutlined />,
        },
        {
          path: '/reference-values',
          name: 'Valores de Referência',
          icon: <DatabaseOutlined />,
        },
        // REMOVIDO: Settings (Sites e External Labels)
        // Funcionalidades agora disponíveis em:
        // - /metadata-fields (aba "Gerenciar Sites")
        // - /metadata-fields (aba "External Labels")
      ],
    },
    {
      path: '/ferramentas',
      name: 'Ferramentas',
      icon: <ToolOutlined />,
      children: [
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
        // ⭐ SPRINT 2 (2025-11-15)
        {
          path: '/cache-management',
          name: 'Gerenciar Cache',
          icon: <DatabaseOutlined />,
        },
      ],
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
        <SitesProvider>
        <MetadataFieldsProvider>
        <NodesProvider>
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
            {/* ⭐ NOVAS ROTAS DINÂMICAS - v2.0 (2025-11-13) */}
            <Route path="/monitoring/network-probes" element={<DynamicMonitoringPage category="network-probes" />} />
            <Route path="/monitoring/web-probes" element={<DynamicMonitoringPage category="web-probes" />} />
            <Route path="/monitoring/system-exporters" element={<DynamicMonitoringPage category="system-exporters" />} />
            <Route path="/monitoring/database-exporters" element={<DynamicMonitoringPage category="database-exporters" />} />
            <Route path="/monitoring/rules" element={<MonitoringRules />} />
            {/* <Route path="/settings" element={<Settings />} /> REMOVIDO */}
            {/* ⭐ SPRINT 2 (2025-11-15) - Observability & Cache */}
            <Route path="/cache-management" element={<CacheManagement />} />
          </Routes>
        </ProLayout>
        </NodesProvider>
        </MetadataFieldsProvider>
        </SitesProvider>
        </AntdApp>
      </ConfigProvider>
    </BrowserRouter>
  );
};

export default App;
