/**
 * TypeScript type definitions for Installer module
 * Centralized types to avoid duplication
 */

export type ConnectionMethod = 'ssh' | 'fallback';
export type WindowsResolvedMethod = 'psexec' | 'winrm' | 'ssh';
export type PrecheckStatus = 'pending' | 'running' | 'success' | 'failed';
export type TargetType = 'linux' | 'windows';

export interface PrecheckItem {
  key: string;
  label: string;
  description: string;
  status: PrecheckStatus;
  detail?: string;
}

export interface CollectorOption {
  value: string;
  label: string;
  description: string;
  targets: TargetType[];
}

export interface InstallLogEntry {
  key: string;
  message: string;
  source: 'local' | 'remote';
  level?: string;
  timestamp?: string;
  details?: string;
}

export interface ConsulNode {
  name?: string;
  node?: string;
  addr?: string;
  address?: string;
  status?: string | number;
  type?: string;
  services_count?: number;
  datacenter?: string;
  tagged_addresses?: Record<string, string>;
  meta?: Record<string, string>;
  tags?: {
    role?: string;
    dc?: string;
  };
}

export interface WarningModalContent {
  duplicateConsul?: boolean;
  existingInstall?: boolean;
  services: string[];
  portOpen?: boolean;
  serviceRunning?: boolean;
  hasConfig?: boolean;
  targetType: TargetType;
}

export interface ExistingInstallation {
  found: boolean;
  services?: string[];
  portOpen?: boolean;
  serviceRunning?: boolean;
  hasConfig?: boolean;
}

export interface InstallFormData {
  targetType: TargetType;
  host: string;
  port: number;
  username: string;
  password: string;
  domain?: string;
  privateKeyFile?: string;
  connectionMethod: ConnectionMethod;
  selectedCollectors: string[];
  selectedVersion: string;
  useBasicAuth: boolean;
  basicAuthUser: string;
  basicAuthPassword: string;
  autoRegister: boolean;
  selectedNodeAddress: string;
}

export interface InstallationTask {
  id: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  progress: number;
  message: string;
  logs: InstallLogEntry[];
  started_at?: string;
  completed_at?: string;
  error?: string;
}

export interface WebSocketLogMessage {
  timestamp: string;
  level: string;
  message: string;
  data?: Record<string, unknown>;
}
