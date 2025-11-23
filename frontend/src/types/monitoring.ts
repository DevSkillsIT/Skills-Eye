/**
 * TypeScript types para sistema configuration-driven de monitoring types
 *
 * Estes tipos refletem os JSON schemas armazenados no backend.
 */

export interface MonitoringCategory {
  schema_version: string;
  category: string;
  display_name: string;
  display_name_singular: string;
  icon: string;
  color: string;
  description: string;
  enabled: boolean;
  order: number;
  types: MonitoringType[];
  page_config: PageConfig;
}

export interface MonitoringType {
  id: string;
  display_name: string;
  icon: string;
  description: string;
  enabled: boolean;
  order: number;

  /** Matchers flexíveis - suporta múltiplos nomes para mesmo tipo */
  matchers: TypeMatchers;

  /** Schema do formulário de criação/edição */
  form_schema: FormSchema;

  /** Schema da tabela (colunas, ações) */
  table_schema: TableSchema;

  /** Configuração de filtros */
  filters: FilterConfig;

  /** Métricas Prometheus associadas */
  metrics: MetricsConfig;

  /** Contexto da categoria (adicionado pela API) */
  category?: string;
  category_display_name?: string;
  category_icon?: string;
}

/**
 * Matchers - Sistema que elimina vendor lock-in
 *
 * Permite que mesmo tipo funcione com múltiplos nomes de exporters/módulos
 */
export interface TypeMatchers {
  /** Campo no Consul Meta usado para identificar exporter_type */
  exporter_type_field: string;

  /**
   * Múltiplos valores aceitos para exporter_type
   * Exemplo: ["node", "selfnode", "node-exporter", "custom-node"]
   */
  exporter_type_values: string[];

  /** Campo no Consul Meta usado para identificar module */
  module_field: string;

  /**
   * Múltiplos valores aceitos para module (null = aceita ausência)
   * Exemplo: ["node", "node_exporter", null]
   */
  module_values: (string | null)[];

  /** Filtros adicionais customizados */
  additional_filters?: AdditionalFilter[];
}

export interface AdditionalFilter {
  field: string;
  values: any[];
}

/**
 * SPEC-REGEX-001: Interface para informacoes de match da regra de categorizacao
 *
 * Contém detalhes sobre qual regra foi usada para categorizar um tipo
 * e quais patterns especificos fizeram match.
 */
export interface MatchedRuleInfo {
  id: string;                      // ID da regra que fez match
  priority: number;                // Prioridade da regra
  job_pattern_matched: boolean;    // Se job_name_pattern fez match
  module_pattern_matched: boolean; // Se module_pattern fez match
  job_pattern?: string;            // Pattern de job_name usado
  module_pattern?: string;         // Pattern de module usado
}

export interface FormSchema {
  /** Campos do formulário */
  fields: FormField[];

  /** Campos metadata obrigatórios */
  required_metadata: string[];

  /** Campos metadata opcionais */
  optional_metadata?: string[];
}

export interface FormField {
  name: string;
  label: string;
  type: 'text' | 'number' | 'select' | 'textarea' | 'date';
  required: boolean;
  default?: any;
  options?: string[] | SelectOption[];
  placeholder?: string;
  help?: string;
  min?: number;
  max?: number;
  validation?: ValidationRules;
}

export interface SelectOption {
  label: string;
  value: any;
}

export interface ValidationRules {
  pattern?: string;
  message?: string;
  min_length?: number;
  max_length?: number;
  required_message?: string;
}

export interface TableSchema {
  /** Colunas visíveis por padrão */
  default_visible_columns: string[];

  /** Ordenação padrão */
  default_sort?: SortConfig;

  /** Ações disponíveis por linha */
  row_actions: string[];

  /** Ações em lote (múltiplas linhas) */
  bulk_actions: string[];
}

export interface SortConfig {
  field: string;
  order: 'asc' | 'desc';
}

export interface FilterConfig {
  /** Filtros rápidos (sempre visíveis) */
  quick_filters: string[];

  /** Filtros avançados (busca avançada) */
  advanced_filters: string[];
}

export interface MetricsConfig {
  /** Métrica principal (ex: "probe_success", "up") */
  primary: string;

  /** Métricas secundárias */
  secondary: string[];
}

export interface PageConfig {
  title: string;
  subtitle: string;
  show_summary_cards: boolean;
  summary_metrics: string[];
  show_filters: boolean;
  show_search: boolean;
  show_advanced_search: boolean;
  show_column_selector: boolean;
  show_export: boolean;
  allow_bulk_actions: boolean;
  default_page_size?: number;
}

/**
 * Response types da API
 */

export interface MonitoringCategoriesResponse {
  success: boolean;
  categories: MonitoringCategory[];
  total: number;
}

export interface MonitoringTypeResponse {
  success: boolean;
  data: MonitoringType | MonitoringCategory;
}

export interface FilterQueryResponse {
  success: boolean;
  query: {
    operator: 'and' | 'or';
    conditions: QueryCondition[];
  };
}

export interface QueryCondition {
  field: string;
  operator: 'eq' | 'ne' | 'in' | 'contains' | 'gt' | 'lt';
  values?: any[];
  value?: any;
}

/**
 * Data types para tabelas
 */

export interface MonitoringData {
  id: string;
  [key: string]: any;
}

/**
 * MonitoringDataItem - Estrutura de dados de um item de monitoramento do Consul
 *
 * Usada em:
 * - DynamicMonitoringPage.tsx (tabela principal)
 * - DynamicCRUDModal.tsx (criação/edição)
 */
export interface MonitoringDataItem {
  ID: string;
  Service: string;
  Address?: string;
  Port?: number;
  Tags: string[];
  Meta: Record<string, any>;
  Node?: string;
  node_ip?: string;  // IP do nó para filtro (vem do backend)
  [key: string]: any;  // Campos dinâmicos
}

export interface NetworkProbeData extends MonitoringData {
  target: string;
  module: string;
  status: 'up' | 'down';
  latency_ms?: number;
  last_check?: string;
  uptime_percent?: number;
  meta: Record<string, any>;
}

export interface SystemExporterData extends MonitoringData {
  node_name: string;
  address: string;
  port: number;
  exporterType: string;
  status: 'up' | 'down';
  last_scrape?: string;
  meta: Record<string, any>;
}
