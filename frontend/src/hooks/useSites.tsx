/**
 * Hook useSites - Configuração dinâmica de sites
 * 
 * ✅ SUBSTITUI hardcoding de sites, cores, clusters
 * 
 * ANTES:
 * - Sites hardcoded em namingUtils.ts (palmas, rio, dtc)
 * - Cores hardcoded em MetadataFields.tsx
 * - IPs hardcoded em vários lugares
 * 
 * AGORA:
 * - TUDO vem do backend via /api/v1/settings/sites-config
 * - Single source of truth: skills/eye/metadata/sites (KV)
 * - Gerenciador de Sites controla tudo dinamicamente
 * 
 * USO:
 * ```tsx
 * const { sites, getSiteByCode, getSiteColor, defaultSite, isLoading } = useSites();
 * 
 * // Buscar site por código
 * const site = getSiteByCode('palmas');
 * 
 * // Buscar cor para badge
 * const color = getSiteColor('rio'); // 'gold'
 * 
 * // Buscar site por cluster
 * const site = getSiteByCluster('palmas-master'); // { code: 'palmas', ... }
 * ```
 */

import React, { createContext, useContext, useEffect, useState } from 'react';
import type { ReactNode } from 'react';
import axios from 'axios';

// Criar instância axios para este hook (usar mesma baseURL da API principal)
const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:5000/api/v1';
const api = axios.create({
  baseURL: API_URL,
  timeout: 60000, // 60s - StrictMode causa requisições duplicadas em dev
});

// ============================================================================
// TIPOS E INTERFACES
// ============================================================================

export interface Site {
  code: string;
  name: string;
  is_default: boolean;
  color: string;
  cluster: string;
  datacenter: string;
  prometheus_instance: string;
}

export interface NamingConfig {
  strategy: 'option1' | 'option2';
  suffix_enabled: boolean;
}

export interface SitesConfig {
  sites: Site[];
  naming: NamingConfig;
  default_site: string;
  total_sites: number;
}

interface SitesContextValue {
  // Dados
  sites: Site[];
  naming: NamingConfig;
  defaultSite: string | null;
  isLoading: boolean;
  error: string | null;
  
  // Funções utilitárias
  getSiteByCode: (code: string) => Site | undefined;
  getSiteByCluster: (cluster: string) => Site | undefined;
  getSiteColor: (code: string) => string;
  getSitePrometheusInstance: (code: string) => string | undefined;
  getAllSiteCodes: () => string[];
  getAllSiteColors: () => Record<string, string>;
  
  // Refresh manual
  refresh: () => Promise<void>;
}

// ============================================================================
// CONTEXT
// ============================================================================

const SitesContext = createContext<SitesContextValue | undefined>(undefined);

// ============================================================================
// PROVIDER
// ============================================================================

interface SitesProviderProps {
  children: ReactNode;
}

export const SitesProvider: React.FC<SitesProviderProps> = ({ children }) => {
  const [sites, setSites] = useState<Site[]>([]);
  const [naming, setNaming] = useState<NamingConfig>({ strategy: 'option2', suffix_enabled: true });
  const [defaultSite, setDefaultSite] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // FUNÇÃO: Carregar configuração do backend
  const loadSitesConfig = async () => {
    try {
      setIsLoading(true);
      setError(null);
      
      const response = await api.get<{success: boolean} & SitesConfig>('/settings/sites-config');
      
      if (response.data.success) {
        setSites(response.data.sites);
        setNaming(response.data.naming);
        setDefaultSite(response.data.default_site);
      } else {
        throw new Error('Falha ao carregar configuração de sites');
      }
    } catch (err: any) {
      console.error('[useSites] Erro ao carregar sites:', err);
      setError(err.message || 'Erro ao carregar sites');
      
      // Fallback: valores padrão (só para não quebrar UI)
      setSites([]);
      setNaming({ strategy: 'option2', suffix_enabled: true });
      setDefaultSite('palmas');
    } finally {
      setIsLoading(false);
    }
  };

  // EFFECT: Carregar ao montar
  useEffect(() => {
    loadSitesConfig();
  }, []);

  // FUNÇÃO: Buscar site por código
  const getSiteByCode = (code: string): Site | undefined => {
    return sites.find(site => site.code.toLowerCase() === code.toLowerCase());
  };

  // FUNÇÃO: Buscar site por cluster
  const getSiteByCluster = (cluster: string): Site | undefined => {
    const clusterLower = cluster.toLowerCase();
    return sites.find(site => 
      site.cluster.toLowerCase() === clusterLower || 
      clusterLower.includes(site.code.toLowerCase())
    );
  };

  // FUNÇÃO: Buscar cor por código de site
  const getSiteColor = (code: string): string => {
    const site = getSiteByCode(code);
    return site?.color || 'default';
  };

  // FUNÇÃO: Buscar Prometheus instance por código
  const getSitePrometheusInstance = (code: string): string | undefined => {
    const site = getSiteByCode(code);
    return site?.prometheus_instance;
  };

  // FUNÇÃO: Retornar todos os códigos de sites
  const getAllSiteCodes = (): string[] => {
    return sites.map(site => site.code);
  };

  // FUNÇÃO: Retornar mapa de cores (code -> color)
  const getAllSiteColors = (): Record<string, string> => {
    const colors: Record<string, string> = {};
    sites.forEach(site => {
      colors[site.code] = site.color;
    });
    return colors;
  };

  const value: SitesContextValue = {
    sites,
    naming,
    defaultSite,
    isLoading,
    error,
    getSiteByCode,
    getSiteByCluster,
    getSiteColor,
    getSitePrometheusInstance,
    getAllSiteCodes,
    getAllSiteColors,
    refresh: loadSitesConfig,
  };

  return <SitesContext.Provider value={value}>{children}</SitesContext.Provider>;
};

// ============================================================================
// HOOK
// ============================================================================

export const useSites = (): SitesContextValue => {
  const context = useContext(SitesContext);
  
  if (context === undefined) {
    throw new Error('useSites deve ser usado dentro de <SitesProvider>');
  }
  
  return context;
};

// ============================================================================
// EXPORT DEFAULT
// ============================================================================

export default useSites;
