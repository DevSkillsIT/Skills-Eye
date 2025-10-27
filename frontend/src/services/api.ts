import axios from 'axios';

const API_URL = import.meta.env?.VITE_API_URL ?? 'http://localhost:5000/api/v1';

// ============================================================================
// Type Definitions - ALL EXPORTED
// ============================================================================

export interface MetadataFilters {
  module?: string;
  company?: string;
  project?: string;
  env?: string;
  group?: string;
  node?: string;
}

export interface ServiceMeta extends MetadataFilters {
  name?: string;
  instance?: string;
  datacenter?: string;
  hostname?: string;
  interval?: string;
  timeout?: string;
  enabled?: boolean;
  labels?: Record<string, string>;
  notes?: string;
  [key: string]: string | number | boolean | Record<string, any> | undefined;
}

export interface ConsulServiceRecord {
  ID: string;
  Service: string;
  Tags: string[];
  Meta: ServiceMeta;
  Address?: string;
  Port?: number;
  Datacenter?: string;
  node?: string;
}

export interface ServiceQuery extends MetadataFilters {
  node_addr?: string;
}

export interface ServiceCreatePayload {
  id: string;
  name: string;
  address?: string;
  port?: number;
  tags?: string[];
  Meta: Record<string, string>;
  node_addr?: string;
}

export interface ServiceUpdatePayload {
  address?: string;
  port?: number;
  tags?: string[];
  Meta?: Record<string, string>;
  node_addr?: string;
}

export interface ServiceListResponse {
  success: boolean;
  data: any;
  total: number;
  node?: string;
  nodes_count?: number;
}

export interface MetadataResponse {
  success: boolean;
  field: string;
  values: string[];
}

export interface BlackboxTargetPayload {
  module: string;
  company: string;
  project: string;
  env: string;
  name: string;
  instance: string;
  group?: string;
  interval?: string;
  timeout?: string;
  enabled?: boolean;
  labels?: Record<string, string>;
  notes?: string;
}

export interface BlackboxTargetRecord {
  service_id: string;
  service: string;
  node?: string;
  tags: string[];
  address?: string;
  port?: number;
  meta: ServiceMeta;
  kv?: Record<string, any>;
}

export interface BlackboxTargetEnhanced extends BlackboxTargetPayload {
  group?: string;
  labels?: Record<string, string>;
  interval?: string;
  timeout?: string;
  enabled?: boolean;
  notes?: string;
}

export interface BlackboxListResponse {
  success: boolean;
  services: BlackboxTargetRecord[];
  module_list?: string[];
  company_list?: string[];
  project_list?: string[];
  env_list?: string[];
  group_list?: string[];
  summary?: {
    total: number;
    enabled: number;
    disabled: number;
    by_module: Record<string, number>;
    by_group: Record<string, number>;
  };
}

export interface KVTreeResponse {
  success: boolean;
  prefix: string;
  data: Record<string, any>;
}

export interface KVValueResponse {
  success: boolean;
  key: string;
  value: any;
}

export interface BlackboxGroup {
  id: string;
  name: string;
  description?: string;
  tags?: string[];
  metadata?: Record<string, any>;
  created_at?: string;
  created_by?: string;
}

export interface BlackboxGroupResponse {
  success: boolean;
  group: BlackboxGroup;
}

export interface ConfigHost {
  id: string;
  name: string;
  description?: string;
}

export interface ConfigFileInfo {
  path: string;
  size?: number;
  modified?: string;
}

export interface ServicePreset {
  id: string;
  name: string;
  service_name: string;
  port?: number;
  tags?: string[];
  meta_template?: Record<string, string>;
  checks?: any[];
  description?: string;
  category: string;
}

export interface PresetListResponse {
  success: boolean;
  presets: ServicePreset[];
  total: number;
}

export interface RegisterFromPreset {
  preset_id: string;
  variables: Record<string, string>;
  node_addr?: string;
}

export interface SearchCondition {
  field: string;
  operator: string;
  value: any;
}

export interface SearchQuery {
  conditions: SearchCondition[];
  logical_operator: 'and' | 'or';
}

export interface AdvancedSearchRequest {
  conditions: SearchCondition[];
  logical_operator?: 'and' | 'or';
  page?: number;
  page_size?: number;
  sort_by?: string;
  sort_order?: 'asc' | 'desc';
}

export interface SearchResponse {
  success: boolean;
  data: any[];
  total: number;
  page: number;
  page_size: number;
}

export interface AuditEvent {
  timestamp: string;
  action: string;
  resource_type: string;
  resource_id: string;
  user: string;
  details?: string;
  metadata?: Record<string, any>;
}

export interface AuditLogResponse {
  success: boolean;
  events: AuditEvent[];
  total: number;
  count: number;
  filters?: any;
}

export interface UISettings {
  [key: string]: any;
}

export interface Statistics {
  total_services: number;
  by_company: Record<string, number>;
  by_env: Record<string, number>;
  by_module: Record<string, number>;
  by_datacenter: Record<string, number>;
  by_service_name: Record<string, number>;
}

export interface DashboardMetrics {
  total_services: number;
  blackbox_targets: number;
  exporters: number;
  active_nodes?: number;
  total_nodes?: number;
  health: {
    passing: number;
    warning: number;
    critical: number;
  };
  by_env: Record<string, number>;
  by_datacenter: Record<string, number>;
  recent_changes: AuditEvent[];
}

export interface ConsulHostMetrics {
  host: {
    hostname: string;
    uptime: number;
    os: string;
    kernel: string;
  };
  cpu: {
    cores: number;
    vendorId?: string;
    modelName?: string;
  };
  memory: {
    total: number;
    available: number;
    used: number;
    usedPercent: number;
  };
  disk: {
    path: string;
    fstype: string;
    total: number;
    free: number;
    used: number;
    usedPercent: number;
  };
  pmem: number;
  pdisk: number;
}

export interface ConsulServiceOverviewItem {
  name: string;
  datacenter: string;
  instance_count: number;
  checks_critical: number;
  checks_passing: number;
  tags: string[];
  nodes: string[];
}

// ============================================================================
// Axios Instance
// ============================================================================

const api = axios.create({
  baseURL: API_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// ============================================================================
// API Methods Object
// ============================================================================

export const consulAPI = {
  // Nodes
  getNodes: () => api.get('/nodes'),
  getNodeServices: (nodeAddr: string) => api.get(`/nodes/${nodeAddr}/services`),

  // Services
  listServices: (params?: ServiceQuery) =>
    api.get<ServiceListResponse>('/services', { params }),

  getService: (serviceId: string, params?: ServiceQuery) =>
    api.get(`/services/${encodeURIComponent(serviceId)}`, { params }),

  createService: (serviceData: ServiceCreatePayload) =>
    api.post('/services', serviceData),

  updateService: (serviceId: string, payload: ServiceUpdatePayload) =>
    api.put(`/services/${encodeURIComponent(serviceId)}`, payload),

  deleteService: (serviceId: string, params?: ServiceQuery) =>
    api.delete(`/services/${encodeURIComponent(serviceId)}`, { params }),

  getServiceMetadataValues: (field: string) =>
    api.get<MetadataResponse>('/services/metadata/unique-values', {
      params: { field },
    }),

  // Blackbox Targets
  listBlackboxTargets: (filters?: MetadataFilters) =>
    api.get<BlackboxListResponse>('/blackbox', { params: filters }),

  createBlackboxTarget: (payload: BlackboxTargetPayload) =>
    api.post('/blackbox', payload),

  createBlackboxTargetEnhanced: (payload: BlackboxTargetEnhanced, user = 'web-user') =>
    api.post('/blackbox/enhanced', payload, { params: { user } }),

  updateBlackboxTarget: (current: BlackboxTargetPayload, replacement: BlackboxTargetPayload) =>
    api.put('/blackbox', { current, replacement }),

  deleteBlackboxTarget: (payload: Omit<BlackboxTargetPayload, 'instance'>) =>
    api.delete('/blackbox', { data: payload }),

  importBlackboxTargets: (file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    return api.post('/blackbox/import', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  },

  getBlackboxRules: () =>
    api.get('/blackbox/config/rules', { responseType: 'text' }),

  getBlackboxConfig: () =>
    api.get('/blackbox/config/blackbox', { responseType: 'text' }),

  getBlackboxPrometheusConfig: (consulServer?: string, consulToken?: string) =>
    api.get('/blackbox/config/prometheus', {
      params: { consul_server: consulServer, consul_token: consulToken },
      responseType: 'text',
    }),

  // Blackbox Groups
  createBlackboxGroup: (group: BlackboxGroup, user = 'web-user') =>
    api.post('/blackbox/groups', group, { params: { user } }),

  listBlackboxGroups: () =>
    api.get<{ success: boolean; groups: BlackboxGroup[]; total: number }>('/blackbox/groups'),

  getBlackboxGroup: (groupId: string) =>
    api.get<BlackboxGroupResponse>(`/blackbox/groups/${groupId}`),

  updateBlackboxGroup: (groupId: string, updates: Partial<BlackboxGroup>, user = 'web-user') =>
    api.put(`/blackbox/groups/${groupId}`, updates, { params: { user } }),

  deleteBlackboxGroup: (groupId: string, user = 'web-user') =>
    api.delete(`/blackbox/groups/${groupId}`, { params: { user } }),

  searchBlackboxTargets: (params: any) =>
    api.get('/search/blackbox', { params }),

  // Service Presets
  createPreset: (preset: ServicePreset, user = 'web-user') =>
    api.post('/presets', preset, { params: { user } }),

  listPresets: (category?: string) =>
    api.get<PresetListResponse>('/presets', { params: { category } }),

  getPreset: (presetId: string) =>
    api.get<{ success: boolean; preset: ServicePreset }>(`/presets/${presetId}`),

  updatePreset: (presetId: string, updates: Partial<ServicePreset>, user = 'web-user') =>
    api.put(`/presets/${presetId}`, updates, { params: { user } }),

  deletePreset: (presetId: string, user = 'web-user') =>
    api.delete(`/presets/${presetId}`, { params: { user } }),

  registerFromPreset: (request: RegisterFromPreset, user = 'web-user') =>
    api.post('/presets/register', request, { params: { user } }),

  previewPreset: (request: RegisterFromPreset) =>
    api.post('/presets/preview', request),

  createBuiltinPresets: (user = 'web-user') =>
    api.post('/presets/builtin/create', null, { params: { user } }),

  // Advanced Search
  advancedSearch: (request: AdvancedSearchRequest) =>
    api.post<SearchResponse>('/search/advanced', request),

  textSearch: (text: string, fields?: string[], page = 1, pageSize = 20) =>
    api.post<SearchResponse>('/search/text', { text, fields, page, page_size: pageSize }),

  getFilterOptions: () =>
    api.get<{ success: boolean; filters: Record<string, string[]>; total_services: number }>('/search/filters'),

  getSearchStats: () =>
    api.get<{ success: boolean; statistics: Statistics }>('/search/stats'),

  // Config files
  listConfigHosts: () =>
    api.get<{ success: boolean; hosts: ConfigHost[] }>('/config-files/hosts'),

  listConfigFiles: (hostId: string) =>
    api.get<{ success: boolean; files: ConfigFileInfo[] }>(
      `/config-files/${encodeURIComponent(hostId)}`,
    ),

  getConfigFile: (hostId: string, filePath: string) =>
    api.get<{ success: boolean; content: string }>(
      `/config-files/${encodeURIComponent(hostId)}/content`,
      { params: { path: filePath } },
    ),

  // KV Store
  getKV: (key: string) =>
    api.get<KVValueResponse>('/kv/value', { params: { key } }),

  putKV: (key: string, value: any) =>
    api.post('/kv/value', { key, value }),

  deleteKV: (key: string) =>
    api.delete('/kv/value', { params: { key } }),

  getKVTree: (prefix: string) =>
    api.get<KVTreeResponse>('/kv/tree', { params: { prefix } }),

  // Audit Log
  getAuditEvents: (params?: { start_date?: string; end_date?: string; resource_type?: string; action?: string; limit?: number }) =>
    api.get<AuditLogResponse>('/kv/audit/events', { params }),

  // Health & Status
  getHealthStatus: () => api.get('/health/status'),
  getConnectivity: () => api.get('/health/connectivity'),
  getConsulHostMetrics: (nodeAddr?: string) =>
    api.get<{ success: boolean } & ConsulHostMetrics>('/consul/hosts', {
      params: nodeAddr ? { node_addr: nodeAddr } : undefined,
    }),
  getConsulServicesOverview: () =>
    api.get<{ success: boolean; services: ConsulServiceOverviewItem[] }>('/consul/services/overview'),

  // Dashboard Metrics - COMPOSED METHOD
  getDashboardMetrics: async function(): Promise<DashboardMetrics> {
    try {
      const [servicesRes, healthRes, statsRes, blackboxRes, nodesRes] = await Promise.all([
        consulAPI.listServices().catch(() => ({ data: { data: [], count: 0 } })),
        consulAPI.getHealthStatus().catch(() => ({ data: { summary: { passing: 0, warning: 0, critical: 0 } } })),
        consulAPI.getSearchStats().catch(() => ({ data: { statistics: {} } })),
        // consulAPI.getAuditEvents({ limit: 10 }).catch(() => ({ data: { events: [], total: 0, count: 0 } })), // Endpoint não existe
        consulAPI.listBlackboxTargets().catch(() => ({ data: { summary: { total: 0, enabled: 0, disabled: 0 } } })),
        consulAPI.getNodes().catch(() => ({ data: { data: [], total: 0 } })),
      ]);

      const flattenServices = (data: any): any[] => {
        if (!data) return [];
        const result: any[] = [];
        const pushService = (service: any) => {
          if (service && typeof service === 'object') {
            result.push(service);
          }
        };

        const processValue = (value: any) => {
          if (!value) return;
          if (Array.isArray(value)) {
            value.forEach(pushService);
            return;
          }
          if (typeof value === 'object') {
            if ('Service' in value || 'Meta' in value || 'Tags' in value) {
              pushService(value);
              return;
            }
            Object.values(value).forEach((inner) => {
              if (Array.isArray(inner)) {
                inner.forEach(pushService);
              } else if (inner && typeof inner === 'object') {
                if ('Service' in inner || 'Meta' in inner || 'Tags' in inner) {
                  pushService(inner);
                } else {
                  Object.values(inner).forEach(pushService);
                }
              }
            });
          }
        };

        if (Array.isArray(data)) {
          data.forEach(pushService);
        } else if (typeof data === 'object') {
          Object.values(data).forEach(processValue);
        }

        return result;
      };

      const servicesPayload: any = servicesRes?.data ?? {};
      const servicesList = flattenServices(servicesPayload.data);
      const totalServices = typeof servicesPayload.total === 'number'
        ? servicesPayload.total
        : servicesList.length;

      const blackboxSummary = (blackboxRes.data as any)?.summary || { total: 0, enabled: 0 };
      const blackboxTargets = blackboxSummary.total;

      // Lista de modulos conhecidos de exporters (nao blackbox)
      const EXPORTER_MODULES = [
        'node_exporter',
        'windows_exporter',
        'mysqld_exporter',
        'redis_exporter',
        'postgres_exporter',
        'mongodb_exporter',
        'blackbox_exporter', // Este é o exporter, não os targets
      ];

      // Lista de modulos blackbox (NÃO são exporters)
      const BLACKBOX_MODULES = [
        'icmp',
        'http_2xx',
        'http_4xx',
        'http_5xx',
        'http_post_2xx',
        'https',
        'tcp_connect',
        'ssh_banner',
        'pop3s_banner',
        'irc_banner',
      ];

      const exporters = servicesList.filter(
        (s: any) => {
          const serviceName = String(s?.Service || s?.service || '').toLowerCase();
          const moduleName = String(s?.Meta?.module || '').toLowerCase();
          const metaName = String(s?.Meta?.name || '').toLowerCase();

          // Excluir se for modulo blackbox
          if (BLACKBOX_MODULES.some(bm => moduleName.includes(bm))) {
            return false;
          }

          // Incluir se for modulo exporter conhecido
          if (EXPORTER_MODULES.some(em => moduleName.includes(em) || serviceName.includes(em) || metaName.includes(em))) {
            return true;
          }

          // Incluir se tiver 'exporter' no nome mas NAO for blackbox
          const hasExporterKeyword = (
            serviceName.includes('exporter') ||
            metaName.includes('exporter')
          );

          return hasExporterKeyword && !moduleName.includes('blackbox');
        }
      ).length;

      const statsPayload: any = statsRes?.data ?? {};
      const stats: any = statsPayload.statistics || {};
      let datacenterStats: Record<string, number> = stats.by_datacenter || {};

      if (!Object.keys(datacenterStats).length || Object.keys(datacenterStats).every((key) => !key || key === 'unknown')) {
        const fallback: Record<string, number> = {};
        servicesList.forEach((service: any) => {
          const meta = service?.Meta || {};
          const dc =
            meta.datacenter ||
            meta.dc ||
            service?.Datacenter ||
            service?.datacenter ||
            'unknown';
          const key = (dc || 'unknown') as string;
          fallback[key] = (fallback[key] || 0) + 1;
        });
        if (Object.keys(fallback).length) {
          datacenterStats = fallback;
        }
      }

      const health: any = healthRes.data.summary || { passing: 0, warning: 0, critical: 0 };
      const recentEvents: any[] = []; // auditRes.data.events?.slice(0, 10) || []; // Endpoint não existe
      const nodesData: any[] = Array.isArray(nodesRes?.data?.data) ? nodesRes.data.data : [];
      const totalNodes = typeof nodesRes?.data?.total === 'number' ? nodesRes.data.total : nodesData.length;
      const activeNodes = nodesData.filter((node) => {
        const status = String(node?.status || node?.Status || '').toLowerCase();
        return status === 'alive' || status === 'passing' || status === 'online';
      }).length;

      return {
        total_services: totalServices,
        blackbox_targets: blackboxTargets,
        exporters,
        active_nodes: activeNodes,
        total_nodes: totalNodes,
        health: {
          passing: health.passing || 0,
          warning: health.warning || 0,
          critical: health.critical || 0,
        },
        by_env: stats.by_env || {},
        by_datacenter: datacenterStats,
        recent_changes: recentEvents,
      };
    } catch (error) {
      console.error('Error fetching dashboard metrics:', error);
      return {
        total_services: 0,
        blackbox_targets: 0,
        exporters: 0,
        active_nodes: 0,
        total_nodes: 0,
        health: { passing: 0, warning: 0, critical: 0 },
        by_env: {},
        by_datacenter: {},
        recent_changes: [],
      };
    }
  },
};

export default api;


