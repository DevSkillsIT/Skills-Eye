import axios from 'axios';

// CRÍTICO: Usar proxy do Vite em desenvolvimento para evitar CORS
// Em produção, VITE_API_URL deve ser definido com a URL real do backend
const API_URL = import.meta.env?.VITE_API_URL ?? '/api/v1';

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

/**
 * INTERFACES PARA EDIÇÃO DIRETA DE ARQUIVO
 *
 * Nova abordagem que edita o arquivo RAW diretamente no servidor via SSH,
 * preservando 100% dos comentários e formatação YAML.
 */

export interface RawFileContentResponse {
  success: boolean;
  file_path: string;
  content: string;
  size_bytes: number;
  last_modified: string;
  host: string;
  port: number;
}

export interface DirectEditRequest {
  file_path: string;
  content: string;
  hostname?: string;
}

export interface DirectEditResponse {
  success: boolean;
  message: string;
  validation_result?: {
    valid: boolean;
    message?: string;
    output?: string;
    errors?: string;
  };
  backup_path?: string;
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

// Installer Types
export interface InstallerRequest {
  os_type: 'linux' | 'windows';
  method: 'ssh' | 'winrm' | 'psexec' | 'auto';  // 'auto' para Windows multi-connector
  host: string;
  username: string;
  password?: string;
  key_file?: string;
  ssh_port?: number;
  port?: number;
  use_sudo?: boolean;
  collector_profile?: string;
  register_in_consul?: boolean;
  consul_node?: string;
  basic_auth_user?: string;
  basic_auth_password?: string;
  domain?: string;
  use_ssl?: boolean;
  psexec_path?: string;
}

export interface InstallerLogEntry {
  timestamp: string;
  level: string;
  message: string;
  data?: Record<string, unknown>;
}

export interface InstallerResponse {
  success: boolean;
  message: string;
  installation_id: string;
  websocket_url: string;
  details: {
    host: string;
    os_type: string;
    method: string;
    collector_profile: string;
  };
}

export interface InstallStatusResponse {
  installation_id: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  progress: number;
  message: string;
  host: string;
  os_type: string;
  method: string;
  started_at?: string;
  completed_at?: string;
  logs?: InstallerLogEntry[];
  error_code?: string;
  error_category?: string;
  error_details?: string;
}

export interface TestConnectionResponse {
  success: boolean;
  message: string;
  details: {
    os: string;
    version: string;
    architecture: string;
    hostname: string;
    method: string;
  };
  connection_summary?: {
    host: string;
    successful_method: string;
    attempts: Array<{
      method: string;
      success: boolean;
      message: string;
    }>;
    total_attempts: number;
  };
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

// Optimized Endpoints Response Types
export interface OptimizedExporterItem {
  key: string;
  id: string;
  node: string;
  nodeAddr?: string;
  service: string;
  tags: string[];
  address?: string;
  port?: number;
  meta: ServiceMeta;
  exporterType: string;
  company?: string;
  project?: string;
  env: string;
}

export interface OptimizedExportersResponse {
  data: OptimizedExporterItem[];
  total: number;
  summary: {
    by_type: Record<string, number>;
    by_env: Record<string, number>;
  };
  load_time_ms: number;
  from_cache: boolean;
}

export interface OptimizedBlackboxTargetItem {
  key: string;
  id: string;
  node: string;
  nodeAddr?: string;
  service: string;
  tags: string[];
  meta: ServiceMeta;
  module: string;
  instance?: string;
  company?: string;
  project?: string;
  env: string;
}

export interface OptimizedBlackboxTargetsResponse {
  data: OptimizedBlackboxTargetItem[];
  total: number;
  summary: {
    by_module: Record<string, number>;
    by_env: Record<string, number>;
  };
  load_time_ms: number;
  from_cache: boolean;
}

export interface OptimizedServiceGroupItem {
  Name: string;
  Datacenter: string;
  Tags: string[];
  Nodes: string[];
  InstanceCount: number;
  ChecksPassing: number;
  ChecksWarning: number;
  ChecksCritical: number;
}

export interface OptimizedServiceGroupsResponse {
  data: OptimizedServiceGroupItem[];
  total: number;
  summary: {
    totalInstances: number;
    healthy: number;
    unhealthy: number;
  };
  load_time_ms: number;
  from_cache: boolean;
}

export interface OptimizedServiceItem {
  Name: string;
  Datacenter: string;
  InstanceCount: number;
  ChecksPassing: number;
  ChecksCritical: number;
  ChecksWarning: number;
  Tags: string[];
  Nodes: string[];
  NodesCount: number;
}

export interface OptimizedServicesResponse {
  data: OptimizedServiceItem[];
  total: number;
  summary: {
    total_services: number;
    total_instances: number;
    total_passing: number;
    total_critical: number;
    by_datacenter: Record<string, number>;
    by_tag: Record<string, number>;
  };
  load_time_ms: number;
  from_cache: boolean;
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

export interface ConsulNode {
  ID: string;
  Node: string;
  Address: string;
  Status?: string;
  Datacenter?: string;
  TaggedAddresses?: { [key: string]: string };
  Meta?: { [key: string]: string };
}

// ============================================================================
// Axios Instance
// ============================================================================

const api = axios.create({
  baseURL: API_URL,
  timeout: 30000, // 30s
  headers: {
    'Content-Type': 'application/json',
  },
});

// ============================================================================
// API Methods Object
// ============================================================================

export const consulAPI = {
  // Nodes (timeout aumentado para 45s devido a cold start do backend)
  getNodes: () => api.get('/nodes', { timeout: 45000 }),
  getNodeServices: (nodeAddr: string) => api.get(`/nodes/${nodeAddr}/services`),
  getNodeServiceNames: (nodeAddr: string) =>
    api.get<{ success: boolean; node: string; data: string[]; total: number }>(`/nodes/${nodeAddr}/service-names`),

  // Prometheus Config - busca job_names configurados no prometheus.yml
  getPrometheusJobNames: (hostname?: string) =>
    api.get<{
      success: boolean;
      job_names: string[];
      total: number;
      hostname: string;
      file_path: string;
      jobs_details?: Array<{
        job_name: string;
        has_consul_sd: boolean;
        scrape_interval: string;
        metrics_path: string;
      }>;
    }>('/prometheus-config/job-names', { params: hostname ? { hostname } : {} }),

  // Services
  listServices: (params?: ServiceQuery) =>
    api.get<ServiceListResponse>('/services', { params }),

  getService: (serviceId: string, params?: ServiceQuery) =>
    api.get(`/services/${encodeURIComponent(serviceId)}`, { params }),

  // Service Catalog - busca nomes de serviços disponíveis no Consul
  getServiceCatalogNames: () => api.get<{ success: boolean; data: string[]; total: number }>('/services/catalog/names'),

  createService: (serviceData: ServiceCreatePayload) =>
    api.post('/services/', serviceData),

  updateService: (serviceId: string, payload: ServiceUpdatePayload) =>
    api.put(`/services/${encodeURIComponent(serviceId)}`, payload),

  deleteService: (serviceId: string, params?: ServiceQuery) =>
    api.delete(`/services/${encodeURIComponent(serviceId)}`, { params }),

  // Deregister service (Consul native API) - usado para exporters
  deregisterService: (params: { service_id: string; node_addr?: string }) =>
    api.delete(`/services/${encodeURIComponent(params.service_id)}`, {
      params: { node_addr: params.node_addr },
    }),

  getServiceMetadataValues: (field: string) =>
    api.get<MetadataResponse>('/services/metadata/unique-values', {
      params: { field },
    }),

  // Blackbox Targets
  listBlackboxTargets: (filters?: MetadataFilters) =>
    api.get<BlackboxListResponse>('/blackbox', { params: filters }),

  createBlackboxTarget: (payload: BlackboxTargetPayload) =>
    api.post('/blackbox/', payload),

  createBlackboxTargetEnhanced: (payload: BlackboxTargetEnhanced, user = 'web-user') =>
    api.post('/blackbox/enhanced', payload, { params: { user } }),

  updateBlackboxTarget: (current: BlackboxTargetPayload, replacement: BlackboxTargetPayload) =>
    api.put('/blackbox/', { current, replacement }),

  deleteBlackboxTarget: (payload: {
    service_id: string;
    service_name?: string;
    node_addr?: string;
    node_name?: string;
    datacenter?: string;
  }) => api.delete('/blackbox/', { data: payload }),

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
    api.post('/presets/', preset, { params: { user } }),

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

  // Dashboard Metrics - SUPER OTIMIZADO! Um único endpoint rápido
  getDashboardMetrics: async function(): Promise<DashboardMetrics> {
    try {
      // NOVO ENDPOINT OTIMIZADO - 1 única chamada, cache de 30s, processado no backend
      // Retorna em ~13ms (com cache) ao invés de segundos!
      const response = await api.get<DashboardMetrics>('/dashboard/metrics');
      return response.data;
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

  // CÓDIGO OBSOLETO REMOVIDO - Não precisa mais processar no frontend!
  _old_getDashboardMetrics: async function(): Promise<DashboardMetrics> {
    try {
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
      const recentEvents = auditRes.data.events?.slice(0, 10) || [];
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
      // Código obsoleto - não é mais usado!
      return {} as DashboardMetrics;
    }
  },

  // ============================================================================
  // OPTIMIZED ENDPOINTS - Cache-enabled for better performance
  // ============================================================================

  // Exporters Optimized (20s cache)
  getExportersOptimized: (forceRefresh = false) =>
    api.get<OptimizedExportersResponse>('/optimized/exporters', {
      params: { force_refresh: forceRefresh },
    }),

  // Blackbox Targets Optimized (15s cache)
  getBlackboxTargetsOptimized: (forceRefresh = false) =>
    api.get<OptimizedBlackboxTargetsResponse>('/optimized/blackbox-targets', {
      params: { force_refresh: forceRefresh },
    }),

  // Service Groups Optimized (30s cache)
  getServiceGroupsOptimized: (forceRefresh = false) =>
    api.get<OptimizedServiceGroupsResponse>('/optimized/service-groups', {
      params: { force_refresh: forceRefresh },
    }),

  // Services Optimized (25s cache) - Mesma estratégia do TenSunS!
  getServicesOptimized: (forceRefresh = false) =>
    api.get<OptimizedServicesResponse>('/optimized/services', {
      params: { force_refresh: forceRefresh },
    }),

  // Services Instances Optimized (25s cache) - TODAS as instâncias processadas no backend
  getServicesInstancesOptimized: (forceRefresh = false, nodeAddr?: string) =>
    api.get<OptimizedServicesResponse>('/optimized/services-instances', {
      params: { force_refresh: forceRefresh, node_addr: nodeAddr },
    }),

  // Clear Cache (call after CREATE/UPDATE/DELETE operations)
  clearCache: (cacheType?: string) =>
    api.post<{ success: boolean; message: string }>('/optimized/clear-cache', null, {
      params: { cache_type: cacheType },
    }),

  // Installer - Remote exporter installation
  startInstallation: (request: InstallerRequest) =>
    api.post<InstallerResponse>('/installer/install', request),

  getInstallationStatus: (installationId: string) =>
    api.get<InstallStatusResponse>(`/installer/install/${installationId}/status`),

  testConnection: (request: Partial<InstallerRequest>) =>
    api.post<TestConnectionResponse>('/installer/test-connection', request, {
      timeout: 60000, // 60 segundos para testar conexão SSH/WinRM remota
    }),

  checkExistingInstallation: (request: {
    host: string;
    port: number;
    username: string;
    password: string;
    exporter_port: number;
    target_type: string;
  }) =>
    api.post<{
      port_open: boolean;
      service_running: boolean;
      has_config: boolean;
    }>('/installer/check-existing', request, {
      timeout: 30000, // 30 segundos para verificação
    }).then(response => response.data),

  // ============================================================================
  // Prometheus Config - Edição Direta de Arquivo
  // ============================================================================

  /**
   * Lê o conteúdo RAW do arquivo diretamente do servidor via SSH.
   *
   * Nova abordagem que preserva 100% dos comentários e formatação YAML.
   * O arquivo é lido EXATAMENTE como está no servidor, sem nenhum
   * parse/dump que pudesse alterar comentários ou formatação.
   *
   * @param filePath - Path completo do arquivo no servidor
   * @param hostname - Hostname do servidor (opcional, para desambiguação quando há arquivos com mesmo path)
   * @returns Conteúdo RAW do arquivo + metadados
   */
  getRawFileContent: (filePath: string, hostname?: string) =>
    api.get<RawFileContentResponse>('/prometheus-config/file/raw-content', {
      params: { file_path: filePath, hostname },
      timeout: 30000, // 30 segundos para operações SSH
    }),

  /**
   * Salva o conteúdo RAW diretamente no arquivo via SSH.
   *
   * Fluxo de segurança:
   * 1. Cria backup automático com timestamp
   * 2. Valida sintaxe YAML antes de salvar
   * 3. Se prometheus.yml, valida com promtool
   * 4. Salva arquivo com permissões corretas
   * 5. Se validação falhar, restaura backup automaticamente
   *
   * Como não há parse/dump, comentários e formatação são
   * preservados EXATAMENTE como o usuário editou no Monaco Editor.
   *
   * @param request - file_path e content completo
   * @returns Confirmação com validação e backup path
   */
  saveRawFileContent: (request: DirectEditRequest) =>
    api.post<DirectEditResponse>('/prometheus-config/file/raw-content', request, {
      timeout: 60000, // 60 segundos para validação promtool + SSH
    }),

  /**
   * Recarrega serviços (Prometheus, Blackbox, Alertmanager) via SSH.
   *
   * Usa 'reload' ao invés de 'restart' para evitar downtime.
   * Determina automaticamente quais serviços recarregar baseado no arquivo.
   *
   * @param host - Hostname do servidor (ex: "172.16.1.26")
   * @param filePath - Path do arquivo editado para determinar serviço
   * @returns Status do reload com detalhes de cada serviço
   */
  reloadService: (host: string, filePath: string) =>
    api.post<{
      success: boolean;
      message: string;
      services: Array<{
        service: string;
        success: boolean;
        method: string;
        status: string;
        error?: string;
      }>;
      file_path: string;
    }>(
      '/prometheus-config/service/reload',
      { host, file_path: filePath },
      { timeout: 30000 }
    ),

  // ⭐ NOVOS MÉTODOS - Sistema de Refatoração v2.0 (2025-11-13)
  // API Unificada de Monitoramento

  /**
   * Busca dados de monitoramento do Consul filtrados por categoria
   *
   * @param category - Categoria: network-probes, web-probes, system-exporters, database-exporters
   * @param company - Filtro opcional de empresa
   * @param site - Filtro opcional de site
   * @param env - Filtro opcional de ambiente
   * @returns Dados de serviços filtrados
   */
  getMonitoringData: (
    category: string,
    company?: string,
    site?: string,
    env?: string
  ) =>
    api.get<{
      success: boolean;
      category: string;
      data: any[];
      total: number;
      modules?: string[];
      job_names?: string[];
      cache_age_seconds?: number;
      filters_applied?: Record<string, any>;
      detail?: string;
    }>('/monitoring/data', {
      params: { category, company, site, env }
    }),

  /**
   * Busca métricas do Prometheus via PromQL
   *
   * @param category - Categoria de monitoramento
   * @param server - Servidor Prometheus (opcional)
   * @param timeRange - Intervalo de tempo (ex: 5m, 1h)
   * @param company - Filtro de empresa
   * @param site - Filtro de site
   * @returns Métricas do Prometheus
   */
  getMonitoringMetrics: (
    category: string,
    server?: string,
    timeRange = '5m',
    company?: string,
    site?: string
  ) =>
    api.get<{
      success: boolean;
      category: string;
      metrics: Array<{
        instance: string;
        job: string;
        module?: string;
        status: number;
        latency_ms?: number;
        timestamp: string;
        [key: string]: any;
      }>;
      query: string;
      prometheus_server: string;
      total: number;
    }>('/monitoring/metrics', {
      params: { category, server, time_range: timeRange, company, site }
    }),

  /**
   * Força sincronização do cache de tipos de monitoramento
   *
   * @returns Status da sincronização
   */
  syncMonitoringCache: () =>
    api.post<{
      success: boolean;
      message: string;
      total_types: number;
      total_servers: number;
      categories: Array<{
        category: string;
        count: number;
      }>;
      duration_seconds: number;
      detail?: string;
    }>('/monitoring/sync-cache'),

  // =========================================================================
  // ⭐ CATEGORIZATION RULES API - Gerenciamento de Regras (v2.0)
  // =========================================================================

  /**
   * Listar todas as regras de categorização
   */
  getCategorizationRules: () =>
    api.get<{
      success: boolean;
      data: {
        version: string;
        last_updated: string;
        total_rules: number;
        rules: Array<{
          id: string;
          priority: number;
          category: string;
          display_name: string;
          exporter_type?: string;
          conditions: {
            job_name_pattern?: string;
            metrics_path?: string;
            module_pattern?: string;
          };
        }>;
        default_category: string;
        categories: Array<{
          id: string;
          display_name: string;
        }>;
      };
    }>('/categorization-rules'),

  /**
   * Criar nova regra de categorização
   */
  createCategorizationRule: (rule: {
    id: string;
    priority: number;
    category: string;
    display_name: string;
    exporter_type?: string;
    conditions: {
      job_name_pattern?: string;
      metrics_path?: string;
      module_pattern?: string;
    };
  }) =>
    api.post<{
      success: boolean;
      message: string;
      rule_id: string;
    }>('/categorization-rules', rule),

  /**
   * Atualizar regra existente
   */
  updateCategorizationRule: (
    ruleId: string,
    updates: {
      priority?: number;
      category?: string;
      display_name?: string;
      exporter_type?: string;
      conditions?: {
        job_name_pattern?: string;
        metrics_path?: string;
        module_pattern?: string;
      };
    }
  ) =>
    api.put<{
      success: boolean;
      message: string;
    }>(`/categorization-rules/${ruleId}`, updates),

  /**
   * Deletar regra
   */
  deleteCategorizationRule: (ruleId: string) =>
    api.delete<{
      success: boolean;
      message: string;
    }>(`/categorization-rules/${ruleId}`),

  /**
   * Recarregar regras do KV
   */
  reloadCategorizationRules: () =>
    api.post<{
      success: boolean;
      message: string;
      total_rules: number;
    }>('/categorization-rules/reload'),
};

// ============================================================================
// METADATA FIELDS API
// ============================================================================

export interface MetadataField {
  name: string;
  display_name: string;
  category: string;
  data_type?: string;
  field_type?: string;
  order?: number;
  required: boolean;
  show_in_table: boolean;
  show_in_form?: boolean;
  show_in_dashboard?: boolean;
  show_in_filters: boolean;
  show_in_services?: boolean;
  show_in_exporters?: boolean;
  show_in_blackbox?: boolean;
  // ⭐ PÁGINAS DINÂMICAS - v2.0 (2025-11-13)
  show_in_network_probes?: boolean;
  show_in_web_probes?: boolean;
  show_in_system_exporters?: boolean;
  show_in_database_exporters?: boolean;
  show_in_infrastructure_exporters?: boolean;
  show_in_hardware_exporters?: boolean;
  editable: boolean;
  source_label: string;
  description?: string;
  default_value?: string;
  validation_regex?: string;
  options?: string[];
  // Campos de sincronização (FASE 1)
  sync_status?: 'synced' | 'outdated' | 'missing' | 'error';
  sync_message?: string;
  prometheus_target_label?: string;
  metadata_source_label?: string;
}

export interface FieldsConfigResponse {
  success: boolean;
  fields: MetadataField[];
  total: number;
  categories: string[];
}

export interface SyncStatusResponse {
  success: boolean;
  server_id: string;
  server_hostname: string;
  fields: MetadataField[];
  total_synced: number;
  total_outdated: number;
  total_missing: number;
  total_error: number;
  message?: string;
}

// FASE 2: Preview de Mudanças
export interface PrometheusRelabelConfig {
  source_labels?: string[];
  target_label?: string;
  action?: string;
  regex?: string;
  replacement?: string;
  separator?: string;
  [key: string]: string | string[] | undefined;
}

export interface PreviewFieldChangeResponse {
  success: boolean;
  field_name: string;
  current_config: PrometheusRelabelConfig | null;
  new_config: PrometheusRelabelConfig;
  diff_text: string;
  affected_jobs: string[];
  will_create: boolean;
}

// FASE 3: Sincronização em Lote
export interface FieldSyncResult {
  field_name: string;
  success: boolean;
  message: string;
  changes_applied: number;
}

export interface BatchSyncRequest {
  field_names: string[];
  server_id: string;
  dry_run?: boolean;
}

export interface BatchSyncResponse {
  success: boolean;
  server_id: string;
  results: FieldSyncResult[];
  total_processed: number;
  total_success: number;
  total_failed: number;
  duration_seconds: number;
}

// ============================================================================
// CATEGORY API - Gerenciamento de Categorias (Abas Reference Values)
// ============================================================================

export interface CategoryInfo {
  key: string;
  label: string;
  icon: string;
  description: string;
  order: number;
  color: string;
}

export interface CategoriesResponse {
  success: boolean;
  total: number;
  categories: CategoryInfo[];
}

export interface CategoryCreateRequest {
  key: string;
  label: string;
  icon?: string;
  description?: string;
  order?: number;
  color?: string;
}

export interface CategoryUpdateRequest {
  label?: string;
  icon?: string;
  description?: string;
  order?: number;
  color?: string;
}

export const categoryAPI = {
  /**
   * Lista todas as categorias
   */
  listCategories: () =>
    api.get<CategoriesResponse>('/reference-values/categories'),

  /**
   * Cria nova categoria
   */
  createCategory: (data: CategoryCreateRequest, user: string = 'system') =>
    api.post<{ success: boolean; message: string }>(
      '/reference-values/categories',
      data,
      { params: { user } }
    ),

  /**
   * Atualiza categoria existente
   */
  updateCategory: (key: string, data: CategoryUpdateRequest, user: string = 'system') =>
    api.put<{ success: boolean; message: string }>(
      `/reference-values/categories/${key}`,
      data,
      { params: { user } }
    ),

  /**
   * Deleta categoria
   */
  deleteCategory: (key: string, force: boolean = false, user: string = 'system') =>
    api.delete<{ success: boolean; message: string }>(
      `/reference-values/categories/${key}`,
      { params: { force, user } }
    ),

  /**
   * Restaura categorias padrão
   */
  resetToDefaults: (user: string = 'system') =>
    api.post<{ success: boolean; message: string }>(
      '/reference-values/categories/reset',
      {},
      { params: { user } }
    ),
};

// ============================================================================
// METADATA FIELDS API - Configuração de Campos Dinâmicos
// ============================================================================

export const metadataFieldsAPI = {
  /**
   * Lista todos os campos metadata configurados
   */
  listFields: (params?: {
    category?: string;
    required_only?: boolean;
    show_in_table_only?: boolean;
  }) => api.get<FieldsConfigResponse>('/metadata-fields/', { params }),

  /**
   * FASE 1: Verifica status de sincronização de campos com prometheus.yml
   */
  getSyncStatus: (serverId: string) =>
    api.get<SyncStatusResponse>('/metadata-fields/sync-status', {
      params: { server_id: serverId },
      timeout: 15000,
    }),

  /**
   * FASE 2: Preview das mudanças antes de sincronizar
   */
  previewChanges: (fieldName: string, serverId: string) =>
    api.get<PreviewFieldChangeResponse>(
      `/metadata-fields/preview-changes/${fieldName}`,
      {
        params: { server_id: serverId },
        timeout: 15000,
      }
    ),

  /**
   * FASE 3: Sincroniza múltiplos campos de uma vez
   */
  batchSync: (request: BatchSyncRequest) =>
    api.post<BatchSyncResponse>('/metadata-fields/batch-sync', request, {
      timeout: 60000,
    }),
};

// ============================================================================
// METADATA DYNAMIC API - Sistema Totalmente Dinâmico
// ============================================================================

export interface MetadataFieldDynamic {
  name: string;
  display_name: string;
  description: string;
  source_label: string;
  field_type: 'string' | 'select' | 'number' | 'boolean';
  required: boolean;
  enabled: boolean;
  show_in_table: boolean;
  show_in_dashboard: boolean;
  show_in_form: boolean;
  show_in_filter: boolean;
  show_in_blackbox: boolean;
  show_in_exporters: boolean;
  show_in_services: boolean;
  // ⭐ NOVOS CAMPOS - Sistema de Refatoração v2.0 (2025-11-13)
  show_in_network_probes?: boolean;
  show_in_web_probes?: boolean;
  show_in_system_exporters?: boolean;
  show_in_database_exporters?: boolean;
  show_in_infrastructure_exporters?: boolean;
  show_in_hardware_exporters?: boolean;
  // Outros campos
  editable: boolean;
  available_for_registration: boolean;
  options: string[];
  default_value: unknown;
  placeholder: string;
  order: number;
  category: string;
  validation: Record<string, unknown>;
}

export interface MetadataFieldsResponse {
  success: boolean;
  fields: MetadataFieldDynamic[];
  total: number;
  context?: string;
  filters_applied: Record<string, unknown>;
}

export interface FieldNamesResponse {
  success: boolean;
  field_names: string[];
  total: number;
  context?: string;
}

export interface RequiredFieldsResponse {
  success: boolean;
  required_fields: string[];
  total: number;
}

// ============================================================================
// DEPRECATED - SISTEMA HARDCODED JSON REMOVIDO
// ============================================================================
// Campos agora vêm 100% do Prometheus via /prometheus-config/fields
// Configurações de visibilidade salvas em /kv/metadata/field-config/{name}
// Use hooks: useMetadataFields, useTableFields, useFormFields, useFilterFields
// ============================================================================
/*
export const metadataDynamicAPI = {
  // REMOVIDO: Endpoint /metadata-dynamic não existe mais
  // Use: GET /prometheus-config/fields
  getFields: (params?: {
    context?: 'blackbox' | 'exporters' | 'services' | 'general';
    enabled?: boolean;
    required?: boolean;
    show_in_table?: boolean;
    show_in_form?: boolean;
    show_in_filter?: boolean;
    category?: string;
  }) => api.get<MetadataFieldsResponse>('/metadata-dynamic/fields', { params }),

  // REMOVIDO: Use GET /prometheus-config/fields
  getFieldNames: (params?: {
    context?: string;
    enabled?: boolean;
    required?: boolean;
  }) => api.get<FieldNamesResponse>('/metadata-dynamic/fields/names', { params }),

  // REMOVIDO: Use GET /prometheus-config/fields com filtro required=true
  getRequiredFields: () =>
    api.get<RequiredFieldsResponse>('/metadata-dynamic/fields/required'),

  // REMOVIDO: Não há mais cache JSON
  reloadCache: () => api.post('/metadata-dynamic/reload'),

  // REMOVIDO: Validação agora dinâmica do Prometheus
  validateMetadata: (metadata: Record<string, unknown>, context: string = 'general') =>
    api.post('/metadata-dynamic/validate', metadata, { params: { context } }),

  // REMOVIDO: Use PUT /kv/metadata/field-config/{name}
  updateFieldPages: (fieldName: string, pages: {
    show_in_services: boolean;
    show_in_exporters: boolean;
    show_in_blackbox: boolean;
  }) =>
    api.put(`/metadata-dynamic/fields/${fieldName}/pages`, pages),
};
*/

export default api;


