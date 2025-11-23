import React from 'react';
import { ConfigProvider, theme, App as AntdApp } from 'antd';
import ptBR from 'antd/locale/pt_BR';
import ProLayout from '@ant-design/pro-layout';
import { BrowserRouter, Route, Routes, Link, useLocation } from 'react-router-dom';
import './styles/sidebar.css';
// ✅ OTIMIZAÇÃO (2025-11-16): Removido import loadNamingConfig
// SitesProvider já carrega naming-config via /settings/sites-config
import { MetadataFieldsProvider } from './contexts/MetadataFieldsContext';
import { SitesProvider } from './hooks/useSites';
import { NodesProvider } from './contexts/NodesContext';
import { ServersProvider } from './contexts/ServersContext';
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
// NOTA: Imports de paginas obsoletas removidos em SPEC-CLEANUP-001 v1.4.0
// Removidos: Services, Exporters, BlackboxTargets, BlackboxGroups, ServicePresets
import ServiceGroups from './pages/ServiceGroups';
import Hosts from './pages/Hosts';
import Installer from './pages/Installer';
import KvBrowser from './pages/KvBrowser';
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

// ✅ CORREÇÃO (2025-11-16): Componente interno para acessar useLocation
const AppContent: React.FC<{ darkMode: boolean; setDarkMode: (value: boolean) => void }> = ({ darkMode, setDarkMode }) => {
  const location = useLocation();

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
        // NOTA: Itens obsoletos removidos em SPEC-CLEANUP-001 v1.4.0
        // Removidos: Services, Exporters, Alvos Blackbox, Grupos Blackbox, Presets de Servicos
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
        // PAGINAS DINAMICAS - v2.0 (2025-11-13)
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
        // ✅ SPEC-ARCH-001: Novas rotas de categorias
        {
          path: '/monitoring/infrastructure-exporters',
          name: 'Infrastructure Exporters',
          icon: <CloudServerOutlined />,
        },
        {
          path: '/monitoring/hardware-exporters',
          name: 'Hardware Exporters',
          icon: <HddOutlined />,
        },
        {
          path: '/monitoring/network-devices',
          name: 'Network Devices',
          icon: <RadarChartOutlined />,
        },
        {
          path: '/monitoring/custom-exporters',
          name: 'Custom Exporters',
          icon: <AppstoreAddOutlined />,
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
        // ✅ SPEC-ARCH-001: MonitoringRules movido para Configurações
        {
          path: '/settings/monitoring-rules',
          name: 'Regras de Categorização',
          icon: <SettingOutlined />,
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
    <>
      <ProLayout
        title="Consul Manager"
        fixedHeader
        fixSiderbar
        location={location}
        menuItemRender={(item, dom) => (
          <Link to={item.path || '/'}>{dom}</Link>
        )}
        route={{
          path: '/',
          routes: menuItems,
        }}
        siderMenuProps={{
          style: {
            backgroundColor: darkMode ? '#001529' : '#ffffff',
            borderRight: darkMode ? '1px solid #1f1f1f' : '1px solid #f0f0f0',
          },
        }}
        logoStyle={{
          padding: '16px 24px',
          fontSize: '18px',
          fontWeight: 600,
          color: darkMode ? '#ffffff' : '#1890ff',
        }}
        rightContentRender={() => (
          <a
            onClick={() => setDarkMode(!darkMode)}
            style={{ marginRight: 16, cursor: 'pointer' }}
          >
            {darkMode ? 'Modo claro' : 'Modo escuro'}
          </a>
        )}
      >
        <Routes>
          <Route path="/" element={<Dashboard />} />
          {/* NOTA: Rotas de paginas obsoletas removidas em SPEC-CLEANUP-001 v1.4.0 */}
          {/* Removidos: /services, /exporters, /blackbox, /blackbox-groups, /presets */}
          <Route path="/service-groups" element={<ServiceGroups />} />
          <Route path="/hosts" element={<Hosts />} />
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
          {/* ✅ SPEC-ARCH-001: Novas rotas de categorias */}
          <Route path="/monitoring/infrastructure-exporters" element={<DynamicMonitoringPage category="infrastructure-exporters" />} />
          <Route path="/monitoring/hardware-exporters" element={<DynamicMonitoringPage category="hardware-exporters" />} />
          <Route path="/monitoring/network-devices" element={<DynamicMonitoringPage category="network-devices" />} />
          <Route path="/monitoring/custom-exporters" element={<DynamicMonitoringPage category="custom-exporters" />} />
          {/* ✅ SPEC-ARCH-001: MonitoringRules movido para Configurações */}
          <Route path="/settings/monitoring-rules" element={<MonitoringRules />} />
          {/* <Route path="/settings" element={<Settings />} /> REMOVIDO */}
          {/* ⭐ SPRINT 2 (2025-11-15) - Observability & Cache */}
          <Route path="/cache-management" element={<CacheManagement />} />
        </Routes>
      </ProLayout>
    </>
  );
};

const App: React.FC = () => {
  const [darkMode, setDarkMode] = React.useState(false);

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
                <ServersProvider>
                  <AppContent darkMode={darkMode} setDarkMode={setDarkMode} />
                </ServersProvider>
              </NodesProvider>
            </MetadataFieldsProvider>
          </SitesProvider>
        </AntdApp>
      </ConfigProvider>
    </BrowserRouter>
  );
};

export default App;
