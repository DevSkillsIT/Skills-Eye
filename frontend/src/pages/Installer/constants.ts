/**
 * Constants for Installer module
 * Centralized configuration and static data
 */

import type { PrecheckItem, CollectorOption } from './types';

export const API_URL = import.meta.env?.VITE_API_URL ?? 'http://localhost:5001/api/v1';

export const LOG_LEVEL_COLOR: Record<string, string> = {
  error: 'red',
  warning: 'orange',
  success: 'green',
  progress: 'geekblue',
  info: 'blue',
  debug: 'purple',
};

export const DEFAULT_PRECHECKS: PrecheckItem[] = [
  {
    key: 'connectivity',
    label: 'Conectividade',
    description: 'Valida acesso remoto, porta configurada e credenciais fornecidas.',
    status: 'pending',
  },
  {
    key: 'os',
    label: 'Sistema operacional',
    description: 'Detecta distribuição, versão e arquitetura.',
    status: 'pending',
  },
  {
    key: 'ports',
    label: 'Portas reservadas',
    description: 'Confere disponibilidade da porta do exporter (9100/9182).',
    status: 'pending',
  },
  {
    key: 'disk',
    label: 'Espaço em disco',
    description: 'Valida espaço mínimo para binários e logs.',
    status: 'pending',
  },
  {
    key: 'firewall',
    label: 'Firewall',
    description: 'Simula regras de liberação para Prometheus.',
    status: 'pending',
  },
];

export const COLLECTOR_OPTIONS: CollectorOption[] = [
  // Linux collectors
  {
    value: 'node',
    label: 'Node exporter padrão',
    description: 'CPU, memória, rede e recursos básicos do host.',
    targets: ['linux'],
  },
  {
    value: 'filesystem',
    label: 'Filesystem',
    description: 'Uso de disco por filesystem, inodes e espaço reservado.',
    targets: ['linux'],
  },
  {
    value: 'systemd',
    label: 'Systemd',
    description: 'Estado de unidades systemd e falhas recentes.',
    targets: ['linux'],
  },
  {
    value: 'textfile',
    label: 'Textfile collector',
    description: 'Permite expor métricas customizadas via arquivos .prom.',
    targets: ['linux'],
  },
  {
    value: 'process',
    label: 'Process collector',
    description: 'Expande métricas de processos, threads e uso de CPU.',
    targets: ['linux'],
  },
  {
    value: 'iostat',
    label: 'iostat collector (Linux)',
    description: 'Métricas detalhadas de IO por dispositivo (requer sysstat).',
    targets: ['linux'],
  },

  // Windows collectors
  {
    value: 'ad',
    label: 'Active Directory Domain Services',
    description: 'Métricas de serviços de domínio do Active Directory.',
    targets: ['windows'],
  },
  {
    value: 'cpu',
    label: 'CPU usage',
    description: 'Uso de CPU e estatísticas detalhadas.',
    targets: ['windows'],
  },
  {
    value: 'logical_disk',
    label: 'Logical disks, disk I/O',
    description: 'Discos lógicos e I/O de disco.',
    targets: ['windows'],
  },
  {
    value: 'memory',
    label: 'Memory usage metrics',
    description: 'Métricas de uso de memória.',
    targets: ['windows'],
  },
  {
    value: 'net',
    label: 'Network interface I/O',
    description: 'I/O de interfaces de rede.',
    targets: ['windows'],
  },
  {
    value: 'os',
    label: 'OS metrics',
    description: 'Métricas do sistema operacional (memória, processos, usuários).',
    targets: ['windows'],
  },
  {
    value: 'service',
    label: 'Service state metrics',
    description: 'Métricas de estado de serviços.',
    targets: ['windows'],
  },
  {
    value: 'system',
    label: 'System calls',
    description: 'Chamadas do sistema.',
    targets: ['windows'],
  },
  {
    value: 'tcp',
    label: 'TCP connections',
    description: 'Conexões TCP.',
    targets: ['windows'],
  },
];

export const DEFAULT_LINUX_COLLECTORS = ['node', 'filesystem', 'systemd'];
export const DEFAULT_WINDOWS_COLLECTORS = ['cpu', 'memory', 'logical_disk', 'os'];

export const LINUX_SSH_PORT = 22;
export const WINDOWS_SSH_PORT = 22;
export const WINDOWS_WINRM_PORT = 5985;
export const NODE_EXPORTER_PORT = 9100;
export const WINDOWS_EXPORTER_PORT = 9182;

export const POLL_INTERVAL_MS = 2000;  // 2 seconds
export const WEBSOCKET_RECONNECT_DELAY_MS = 3000;  // 3 seconds
