/**
 * Naming Utils - Utilitários de nomenclatura multi-site
 *
 * Replica a lógica do backend para calcular nomes de services com sufixos
 * baseado na estratégia de naming configurada
 */

export interface NamingConfig {
  naming_strategy: 'option1' | 'option2';
  suffix_enabled: boolean;
  default_site: string;
}

/**
 * Configuração atual (será carregada do backend via API)
 * Por padrão assume option2 (sufixos habilitados)
 */
let currentConfig: NamingConfig = {
  naming_strategy: 'option2',
  suffix_enabled: true,
  default_site: 'palmas',
};

/**
 * Atualiza configuração de naming
 * Deve ser chamado ao iniciar a aplicação
 */
export function setNamingConfig(config: NamingConfig) {
  currentConfig = config;
}

/**
 * Obtém configuração atual
 */
export function getNamingConfig(): NamingConfig {
  return currentConfig;
}

/**
 * Aplica sufixo de site ao service name baseado na estratégia configurada
 *
 * OPÇÃO 2 (naming_strategy=option2):
 * - Services em sites diferentes do default_site recebem sufixo _site
 * - Exemplo: selfnode_exporter → selfnode_exporter_rio (se site="rio")
 * - Palmas (default_site) não recebe sufixo: selfnode_exporter
 *
 * OPÇÃO 1 (naming_strategy=option1):
 * - Nenhum sufixo é adicionado
 * - Nomes iguais em todos os sites
 *
 * @param serviceName Nome base do serviço
 * @param site Site físico do serviço
 * @param cluster Cluster Prometheus (alternativa ao site)
 * @returns Service name com sufixo aplicado se necessário
 */
export function applySiteSuffix(
  serviceName: string,
  site?: string,
  cluster?: string
): string {
  // OPÇÃO 1: Não adiciona sufixo
  if (currentConfig.naming_strategy === 'option1') {
    return serviceName;
  }

  // OPÇÃO 2: Adiciona sufixo se habilitado
  if (currentConfig.naming_strategy === 'option2' && currentConfig.suffix_enabled) {
    // Determinar site efetivo (prioriza 'site' sobre 'cluster')
    let effectiveSite: string | undefined = undefined;

    if (site) {
      effectiveSite = site.toLowerCase();
    } else if (cluster) {
      // Extrair site do cluster se possível
      const clusterLower = cluster.toLowerCase();
      if (clusterLower.includes('rio')) {
        effectiveSite = 'rio';
      } else if (clusterLower.includes('dtc') || clusterLower.includes('genesis')) {
        effectiveSite = 'dtc';
      } else if (clusterLower.includes('palmas')) {
        effectiveSite = 'palmas';
      }
    }

    // Se não conseguiu determinar site, não adiciona sufixo
    if (!effectiveSite) {
      return serviceName;
    }

    // Se é o site padrão, não adiciona sufixo
    if (effectiveSite === currentConfig.default_site.toLowerCase()) {
      return serviceName;
    }

    // Adicionar sufixo do site
    return `${serviceName}_${effectiveSite}`;
  }

  // Fallback: retornar nome original
  return serviceName;
}

/**
 * Extrai site dos metadata
 * Procura em ordem: site → cluster → datacenter
 */
export function extractSiteFromMetadata(metadata: Record<string, any>): string | undefined {
  if (!metadata) {
    return undefined;
  }

  // Primeira prioridade: campo 'site' explícito
  if (metadata.site) {
    return metadata.site.toLowerCase();
  }

  // Segunda prioridade: inferir do 'cluster'
  if (metadata.cluster) {
    const cluster = metadata.cluster.toLowerCase();
    if (cluster.includes('rio')) return 'rio';
    if (cluster.includes('dtc') || cluster.includes('genesis')) return 'dtc';
    if (cluster.includes('palmas')) return 'palmas';
  }

  // Terceira prioridade: 'datacenter'
  if (metadata.datacenter) {
    const dc = metadata.datacenter.toLowerCase();
    if (['rio', 'palmas', 'dtc', 'genesis', 'genesis-dtc'].includes(dc)) {
      return dc.replace('genesis-dtc', 'dtc');
    }
  }

  return undefined;
}

/**
 * Calcula o nome final que será registrado no Consul
 * Útil para preview antes de salvar
 */
export function calculateFinalServiceName(
  baseName: string,
  metadata: Record<string, any>
): {
  finalName: string;
  hasSuffix: boolean;
  site: string | undefined;
  reason: string;
} {
  const site = extractSiteFromMetadata(metadata);
  const cluster = metadata.cluster;
  const finalName = applySiteSuffix(baseName, site, cluster);
  const hasSuffix = finalName !== baseName;

  let reason = '';
  if (currentConfig.naming_strategy === 'option1') {
    reason = 'Opção 1: Nomes iguais em todos os sites';
  } else if (!site) {
    reason = 'Site não definido - sem sufixo';
  } else if (site === currentConfig.default_site) {
    reason = `Site padrão (${currentConfig.default_site}) - sem sufixo`;
  } else {
    reason = `Site remoto (${site}) - adicionado sufixo _${site}`;
  }

  return {
    finalName,
    hasSuffix,
    site,
    reason,
  };
}

/**
 * Obtém cor do badge baseado no site
 */
export function getSiteBadgeColor(site: string): string {
  const colors: Record<string, string> = {
    palmas: 'blue',
    rio: 'green',
    dtc: 'orange',
    genesis: 'purple',
  };
  return colors[site.toLowerCase()] || 'default';
}

/**
 * Verifica se um service name tem sufixo de site
 */
export function hasSiteSuffix(serviceName: string): {
  hasSuffix: boolean;
  baseName: string;
  site: string | undefined;
} {
  const match = serviceName.match(/^(.+)_(rio|palmas|dtc|genesis)$/);

  if (match) {
    return {
      hasSuffix: true,
      baseName: match[1],
      site: match[2],
    };
  }

  return {
    hasSuffix: false,
    baseName: serviceName,
    site: undefined,
  };
}

/**
 * Carrega configuração de naming do backend
 */
export async function loadNamingConfig(): Promise<NamingConfig> {
  try {
    // TODO: Criar endpoint no backend para retornar configuração
    // Por enquanto, assume option2 (sufixos habilitados)
    const response = await fetch('/api/v1/settings/naming-config');

    if (response.ok) {
      const config = await response.json();
      setNamingConfig(config);
      return config;
    }
  } catch (error) {
    console.warn('Não foi possível carregar naming config do backend, usando padrão', error);
  }

  // Fallback: configuração padrão
  return currentConfig;
}
