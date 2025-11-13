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
      // ❌ REMOVIDO HARDCODING - Função precisa receber lista de sites como parâmetro
      // Para usar esta função dinamicamente, components devem passar sites do useSites()
      // Exemplo: applySiteSuffix(name, site, cluster, sites)
      console.warn('[namingUtils] applySiteSuffix: cluster fornecido mas sem lista de sites. Use useSites() e passe sites como parâmetro.');
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

  // ❌ REMOVIDO HARDCODING
  // Components devem usar useSites() e passar sites como parâmetro
  // Segunda e terceira prioridade (cluster/datacenter) requerem lista dinâmica de sites
  
  console.warn('[namingUtils] extractSiteFromMetadata: metadata fornecido mas sem lista de sites. Use useSites() e passe sites como parâmetro.');

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
 * 
 * ❌ DEPRECATED: Use useSites().getSiteColor() ao invés desta função
 * Esta função mantida apenas para compatibilidade temporária
 */
export function getSiteBadgeColor(_site: string): string {
  console.warn('[namingUtils] getSiteBadgeColor DEPRECATED: Use useSites().getSiteColor() para cores dinâmicas');
  return 'default';  // Retorna cor neutra - force uso do hook
}

/**
 * Verifica se um service name tem sufixo de site
 * 
 * ❌ DEPRECATED: Regex hardcoded removido
 * Components devem usar lógica dinâmica com useSites()
 */
export function hasSiteSuffix(_serviceName: string): {
  hasSuffix: boolean;
  baseName: string;
  site: string | undefined;
} {
  console.warn('[namingUtils] hasSiteSuffix DEPRECATED: Use lógica dinâmica com useSites().sites');
  
  return {
    hasSuffix: false,
    baseName: _serviceName,
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
