import React from 'react';
import { ConfigProvider, theme } from 'antd';
import ProLayout from '@ant-design/pro-layout';
import { BrowserRouter, Route, Routes, Link } from 'react-router-dom';
import {
  DashboardOutlined,
  DatabaseOutlined,
  CloudServerOutlined,
  ToolOutlined,
} from '@ant-design/icons';

// Páginas
import Dashboard from './pages/Dashboard';
import Services from './pages/Services';
import Installer from './pages/Installer';

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
      path: '/installer',
      name: 'Instalar Exporters',
      icon: <ToolOutlined />,
    },
  ];

  return (
    <BrowserRouter>
      <ConfigProvider
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
        >
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/services" element={<Services />} />
            <Route path="/installer" element={<Installer />} />
          </Routes>
        </ProLayout>
      </ConfigProvider>
    </BrowserRouter>
  );
};

export default App;