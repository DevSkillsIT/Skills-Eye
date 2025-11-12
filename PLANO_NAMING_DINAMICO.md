# PLANO: Migração de Naming Config Hardcoded para 100% Dinâmico

**Data:** 2025-11-12  
**Objetivo:** Eliminar TODOS os hardcodings de sites, cores, clusters e tornar o sistema 100% dinâmico baseado no KV de Sites

---

## 🔴 PROBLEMAS CRÍTICOS IDENTIFICADOS

### 1. **HARDCODING DE SITES EM MÚLTIPLOS LUGARES**

#### Frontend (`namingUtils.ts`)
```typescript
// LINHA 21: Default site hardcoded
default_site: 'palmas',

// LINHAS 76-81: Lista de sites hardcoded
if (clusterLower.includes('rio')) effectiveSite = 'rio';
else if (clusterLower.includes('dtc') || clusterLower.includes('genesis')) effectiveSite = 'dtc';
else if (clusterLower.includes('palmas')) effectiveSite = 'palmas';

// LINHAS 120-125: Extração de site hardcoded
if (cluster.includes('rio')) return 'rio';
if (cluster.includes('dtc') || cluster.includes('genesis')) return 'dtc';
if (cluster.includes('palmas')) return 'palmas';

// LINHAS 174-180: Cores dos badges HARDCODED
export function getSiteBadgeColor(site: string): string {
  const colors: Record<string, string> = {
    palmas: 'blue',    // ❌ ERRADO! No KV palmas tem color='red'
    rio: 'green',      // ❌ ERRADO! No KV rio tem color='gold'
    dtc: 'orange',     // ❌ ERRADO! No KV dtc tem color='blue'
    genesis: 'purple',
  };
  return colors[site.toLowerCase()] || 'default';
}

// LINHA 190: Regex hardcoded com lista de sites
const match = serviceName.match(/^(.+)_(rio|palmas|dtc|genesis)$/);
```

**IMPACTO:**
- ❌ Se adicionar site novo no KV (ex: "saopaulo"), sistema não reconhece
- ❌ Se mudar cor no KV, badges continuam com cor errada
- ❌ Manutenção duplicada: precisa alterar código E KV
- ❌ Inconsistência: KV tem palmas=red mas código mostra blue

#### Frontend (`MetadataFields.tsx`)
```typescript
// LINHAS 1753-1755: IPs e cores HARDCODED
if (hostname.includes('172.16.1.26')) return { displayName: 'Palmas', color: 'green' };
if (hostname.includes('172.16.200.14')) return { displayName: 'Rio', color: 'blue' };
if (hostname.includes('11.144.0.21')) return { displayName: 'DTC', color: 'orange' };

// LINHAS 1886-1894: Fallback hardcoded
if (hostname.includes('172.16.1.26')) {
  displayName = 'Palmas';
  color = 'green';
} else if (hostname.includes('172.16.200.14')) {
  displayName = 'Rio';
  color = 'blue';
} else if (hostname.includes('11.144.0.21')) {
  displayName = 'DTC';
  color = 'orange';
}

// LINHAS 2021-2029: Exemplos nos Cards HARDCODED
<Text code>selfnode_exporter</Text> + <Tag color="blue">site=palmas</Tag>
<Text code>selfnode_exporter</Text> + <Tag color="green">site=rio</Tag>
<Text code>blackbox_exporter</Text> + <Tag color="orange">site=dtc</Tag>
```

**IMPACTO:**
- ❌ Se mudar IP do Prometheus no KV, colunas quebram
- ❌ Cores não batem com KV (palmas no KV é red, código mostra green)
- ❌ Impossível adicionar novo site sem alterar código

#### Backend (`naming_utils.py`)
```python
# LINHAS 57-59: Lê de variáveis de ambiente ao invés do KV
naming_strategy = os.getenv("NAMING_STRATEGY", "option1")
suffix_enabled = os.getenv("SITE_SUFFIX_ENABLED", "false").lower() == "true"
default_site = os.getenv("DEFAULT_SITE", "palmas").lower()

# LINHAS 72-82: Lista de sites hardcoded para inferência
if "rio" in cluster_lower:
    effective_site = "rio"
elif "dtc" in cluster_lower or "genesis" in cluster_lower:
    effective_site = "dtc"
elif "palmas" in cluster_lower:
    effective_site = "palmas"

# LINHAS 120-127: Extração de site do cluster hardcoded
if 'rio' in cluster:
    return 'rio'
elif 'dtc' in cluster or 'genesis' in cluster:
    return 'dtc'
elif 'palmas' in cluster:
    return 'palmas'
```

**IMPACTO:**
- ❌ Backend não sabe sobre sites novos adicionados no KV
- ❌ Configuração fragmentada: .env + KV
- ❌ Inconsistência: default_site pode divergir entre .env e KV

---

## 📊 DADOS DISPONÍVEIS NO KV QUE DEVEM SER USADOS

### KV Path: `skills/eye/metadata/sites`

```json
{
  "code": "palmas",              // ✅ Usar para identificação
  "name": "Palmas",              // ✅ Usar para display
  "is_default": true,            // ✅ Substitui DEFAULT_SITE do .env
  "color": "red",                // ✅ Substitui getSiteBadgeColor()
  "cluster": "palmas-master",    // ✅ Usar para inferência de site
  "datacenter": "skillsit-palmas-to",
  "environment": "production",
  "site": "palmas",
  "prometheus_instance": "172.16.1.26", // ✅ Substitui hardcoding de IPs
  "prometheus_host": "172.16.1.26",
  "ssh_port": 5522,
  "prometheus_port": 9090,
  "external_labels": {
    "cluster": "palmas-master",
    "datacenter": "skillsit-palmas-to",
    "environment": "production",
    "site": "palmas",
    "prometheus_instance": "172.16.1.26"
  }
}
```

**TOTAL DISPONÍVEL:**
- ✅ 3 sites (palmas, rio, dtc) com TODOS os metadados
- ✅ Cores configuradas por site
- ✅ IPs Prometheus por site
- ✅ Clusters e datacenters por site
- ✅ Flag is_default para identificar site padrão

---

## 🎯 ARQUITETURA PROPOSTA

### 1. **Nova Estrutura de Configuração no KV**

```
skills/eye/metadata/sites                    # ✅ JÁ EXISTE
skills/eye/settings/naming-strategy          # 🆕 CRIAR (migrar de .env)
```

#### `skills/eye/settings/naming-strategy`
```json
{
  "naming_strategy": "option2",
  "suffix_enabled": true,
  "description": "option1: Nomes iguais + filtros | option2: Nomes diferentes por site",
  "meta": {
    "created_at": "2025-11-12T00:00:00Z",
    "updated_at": "2025-11-12T00:00:00Z",
    "version": "1.0.0"
  }
}
```

**NOTA:** `default_site` NÃO vai mais existir! Será inferido de `sites[].is_default=true`

---

### 2. **Novo Endpoint Backend**

#### `GET /api/v1/settings/sites-config` (🆕 CRIAR)

**Response:**
```json
{
  "success": true,
  "sites": [
    {
      "code": "palmas",
      "name": "Palmas",
      "is_default": true,
      "color": "red",
      "cluster": "palmas-master",
      "datacenter": "skillsit-palmas-to",
      "prometheus_instance": "172.16.1.26"
    },
    {
      "code": "rio",
      "name": "Rio de Janeiro",
      "is_default": false,
      "color": "gold",
      "cluster": "rmd-ldc-cliente",
      "datacenter": "ramada-barra-rj",
      "prometheus_instance": "172.16.200.14"
    },
    {
      "code": "dtc",
      "name": "Dtc",
      "is_default": false,
      "color": "blue",
      "cluster": "dtc-remote-skills",
      "datacenter": "genesis-dtc",
      "prometheus_instance": "11.144.0.21"
    }
  ],
  "naming": {
    "strategy": "option2",
    "suffix_enabled": true
  },
  "default_site": "palmas",  // Inferido de is_default=true
  "total_sites": 3
}
```

**Lógica:**
1. Busca sites de `skills/eye/metadata/sites`
2. Busca naming de `skills/eye/settings/naming-strategy`
3. Infere `default_site` do site com `is_default=true`
4. Fallback para .env se KV não existir (backward compatibility)

---

### 3. **Novo Hook React: `useSites()`**

#### `frontend/src/hooks/useSites.ts` (🆕 CRIAR)

```typescript
import { useState, useEffect, createContext, useContext } from 'react';

interface Site {
  code: string;
  name: string;
  is_default: boolean;
  color: string;
  cluster: string;
  datacenter: string;
  prometheus_instance: string;
}

interface SitesConfig {
  sites: Site[];
  naming: {
    strategy: 'option1' | 'option2';
    suffix_enabled: boolean;
  };
  default_site: string;
}

interface SitesContextValue {
  sites: Site[];
  naming: SitesConfig['naming'];
  defaultSite: Site | null;
  loading: boolean;
  error: string | null;
  
  // Utility functions
  getSiteByCode: (code: string) => Site | undefined;
  getSiteByHostname: (hostname: string) => Site | undefined;
  getSiteByCluster: (cluster: string) => Site | undefined;
  getSiteColor: (code: string) => string;
  getDefaultSite: () => Site | null;
  isDefaultSite: (code: string) => boolean;
  getAllSiteCodes: () => string[];
  reload: () => Promise<void>;
}

const SitesContext = createContext<SitesContextValue | null>(null);

export function SitesProvider({ children }: { children: React.ReactNode }) {
  const [config, setConfig] = useState<SitesConfig | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadConfig = async () => {
    try {
      setLoading(true);
      const response = await fetch('/api/v1/settings/sites-config');
      if (!response.ok) throw new Error('Falha ao carregar configuração de sites');
      const data = await response.json();
      setConfig(data);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erro desconhecido');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadConfig();
  }, []);

  const value: SitesContextValue = {
    sites: config?.sites || [],
    naming: config?.naming || { strategy: 'option2', suffix_enabled: true },
    defaultSite: config?.sites.find(s => s.is_default) || null,
    loading,
    error,
    
    getSiteByCode: (code) => config?.sites.find(s => s.code === code),
    
    getSiteByHostname: (hostname) => 
      config?.sites.find(s => hostname.includes(s.prometheus_instance)),
    
    getSiteByCluster: (cluster) => {
      const lowerCluster = cluster.toLowerCase();
      return config?.sites.find(s => 
        lowerCluster.includes(s.cluster.toLowerCase()) ||
        lowerCluster.includes(s.code.toLowerCase())
      );
    },
    
    getSiteColor: (code) => {
      const site = config?.sites.find(s => s.code === code);
      return site?.color || 'default';
    },
    
    getDefaultSite: () => config?.sites.find(s => s.is_default) || null,
    
    isDefaultSite: (code) => {
      const site = config?.sites.find(s => s.code === code);
      return site?.is_default || false;
    },
    
    getAllSiteCodes: () => config?.sites.map(s => s.code) || [],
    
    reload: loadConfig,
  };

  return (
    <SitesContext.Provider value={value}>
      {children}
    </SitesContext.Provider>
  );
}

export function useSites() {
  const context = useContext(SitesContext);
  if (!context) {
    throw new Error('useSites deve ser usado dentro de SitesProvider');
  }
  return context;
}
```

**USO:**
```typescript
// Em qualquer componente
const { sites, getSiteColor, getSiteByHostname, isDefaultSite } = useSites();

// Exemplo 1: Obter cor de um site
const color = getSiteColor('palmas'); // Retorna "red" do KV

// Exemplo 2: Identificar site por hostname
const site = getSiteByHostname('172.16.1.26'); // Retorna site "palmas"

// Exemplo 3: Verificar se é site padrão
const isDefault = isDefaultSite('palmas'); // Retorna true
```

---

### 4. **Refatoração do Backend `naming_utils.py`**

#### ANTES (hardcoded):
```python
# ❌ Lê de .env
naming_strategy = os.getenv("NAMING_STRATEGY", "option1")
default_site = os.getenv("DEFAULT_SITE", "palmas").lower()

# ❌ Lista hardcoded
if "rio" in cluster_lower:
    effective_site = "rio"
elif "dtc" in cluster_lower or "genesis" in cluster_lower:
    effective_site = "dtc"
```

#### DEPOIS (dinâmico):
```python
"""
Naming Utils - 100% DINÂMICO baseado no KV

Cache de sites em memória para performance
Atualização automática via background task
"""

import asyncio
from typing import Optional, List, Dict
from backend.core.kv_manager import KVManager

# Cache global de sites (atualizado a cada 60s)
_sites_cache: List[Dict] = []
_naming_cache: Dict = {}
_cache_last_update: float = 0
_cache_ttl: int = 60  # segundos

async def _load_sites_from_kv() -> List[Dict]:
    """
    Carrega sites do KV: skills/eye/metadata/sites
    
    Fallback para .env se KV não existir (backward compatibility)
    """
    kv = KVManager()
    
    try:
        # Tentar carregar do KV primeiro
        kv_data = await kv.get_json("skills/eye/metadata/sites")
        
        if kv_data and "data" in kv_data and "sites" in kv_data["data"]:
            sites = kv_data["data"]["sites"]
            logger.info(f"[NAMING] Carregados {len(sites)} sites do KV")
            return sites
    except Exception as e:
        logger.warning(f"[NAMING] Erro ao carregar sites do KV: {e}")
    
    # Fallback para .env (backward compatibility)
    logger.warning("[NAMING] KV indisponível, usando .env como fallback")
    return [
        {
            "code": "palmas",
            "name": "Palmas",
            "is_default": True,
            "color": "blue",
            "cluster": "palmas-master",
            "prometheus_instance": os.getenv("PALMAS_HOST", "172.16.1.26"),
        },
        # ... outros sites do .env
    ]

async def _load_naming_strategy() -> Dict:
    """
    Carrega naming strategy do KV: skills/eye/settings/naming-strategy
    
    Fallback para .env se não existir
    """
    kv = KVManager()
    
    try:
        strategy_data = await kv.get_json("skills/eye/settings/naming-strategy")
        if strategy_data:
            return {
                "naming_strategy": strategy_data.get("naming_strategy", "option2"),
                "suffix_enabled": strategy_data.get("suffix_enabled", True),
            }
    except Exception as e:
        logger.warning(f"[NAMING] Erro ao carregar strategy do KV: {e}")
    
    # Fallback para .env
    return {
        "naming_strategy": os.getenv("NAMING_STRATEGY", "option2"),
        "suffix_enabled": os.getenv("SITE_SUFFIX_ENABLED", "true").lower() == "true",
    }

async def _update_cache():
    """
    Atualiza cache de sites e naming
    Deve ser chamado em background task
    """
    global _sites_cache, _naming_cache, _cache_last_update
    
    import time
    current_time = time.time()
    
    # Verifica se cache expirou
    if current_time - _cache_last_update < _cache_ttl:
        return  # Cache ainda válido
    
    _sites_cache = await _load_sites_from_kv()
    _naming_cache = await _load_naming_strategy()
    _cache_last_update = current_time
    
    logger.debug(f"[NAMING] Cache atualizado: {len(_sites_cache)} sites")

def get_sites_cache() -> List[Dict]:
    """Retorna cache de sites (síncrono para uso em funções síncronas)"""
    return _sites_cache

def get_naming_cache() -> Dict:
    """Retorna cache de naming strategy"""
    return _naming_cache

def get_default_site() -> Optional[str]:
    """
    Retorna código do site padrão
    Busca no cache por is_default=True
    """
    for site in _sites_cache:
        if site.get("is_default", False):
            return site["code"]
    
    # Fallback para .env
    return os.getenv("DEFAULT_SITE", "palmas").lower()

def get_site_by_cluster(cluster: str) -> Optional[Dict]:
    """
    Busca site pelo cluster DINAMICAMENTE
    
    ANTES: if "rio" in cluster: return "rio"  # ❌ Hardcoded
    DEPOIS: Busca em _sites_cache por cluster matching
    """
    cluster_lower = cluster.lower()
    
    # Busca exata primeiro
    for site in _sites_cache:
        if site.get("cluster", "").lower() == cluster_lower:
            return site
    
    # Busca parcial (cluster contém código do site)
    for site in _sites_cache:
        site_code = site["code"].lower()
        cluster_pattern = site.get("cluster", "").lower()
        
        # Verifica se cluster contém o código do site OU o padrão de cluster
        if site_code in cluster_lower or cluster_pattern in cluster_lower:
            return site
    
    return None

def apply_site_suffix(service_name: str, site: Optional[str] = None, cluster: Optional[str] = None) -> str:
    """
    Aplica sufixo de site DINAMICAMENTE
    
    MUDANÇAS:
    - Usa cache ao invés de .env
    - Busca site dinamicamente
    - Default site vem de is_default=True
    """
    # Garantir cache atualizado (async wrapper para contexto síncrono)
    if not _sites_cache:
        # Força carregamento inicial síncrono
        import asyncio
        try:
            asyncio.get_event_loop().run_until_complete(_update_cache())
        except:
            pass  # Fallback para .env
    
    naming_config = get_naming_cache()
    
    # OPÇÃO 1: Não adiciona sufixo
    if naming_config.get("naming_strategy") == "option1":
        return service_name
    
    # OPÇÃO 2: Adiciona sufixo se habilitado
    if naming_config.get("naming_strategy") == "option2" and naming_config.get("suffix_enabled"):
        # Determinar site efetivo
        effective_site = None
        
        if site:
            effective_site = site.lower()
        elif cluster:
            # Buscar site pelo cluster DINAMICAMENTE
            site_obj = get_site_by_cluster(cluster)
            if site_obj:
                effective_site = site_obj["code"]
        
        if not effective_site:
            return service_name
        
        # Verificar se é site padrão (DINÂMICO)
        default_site = get_default_site()
        if effective_site == default_site:
            return service_name
        
        # Adicionar sufixo
        return f"{service_name}_{effective_site}"
    
    return service_name

def extract_site_from_metadata(metadata: dict) -> Optional[str]:
    """
    Extrai site dos metadata DINAMICAMENTE
    
    MUDANÇAS:
    - Busca em _sites_cache ao invés de lista hardcoded
    - Suporta novos sites adicionados no KV
    """
    if not metadata:
        return None
    
    # Primeira prioridade: campo 'site' explícito
    if 'site' in metadata and metadata['site']:
        return metadata['site'].lower()
    
    # Segunda prioridade: inferir do 'cluster' DINAMICAMENTE
    if 'cluster' in metadata and metadata['cluster']:
        site_obj = get_site_by_cluster(metadata['cluster'])
        if site_obj:
            return site_obj["code"]
    
    # Terceira prioridade: 'datacenter'
    if 'datacenter' in metadata and metadata['datacenter']:
        dc = metadata['datacenter'].lower()
        
        # Buscar site por datacenter
        for site in _sites_cache:
            if site.get("datacenter", "").lower() == dc:
                return site["code"]
    
    return None
```

---

### 5. **Refatoração do Frontend `namingUtils.ts`**

#### ANTES (hardcoded):
```typescript
// ❌ Hardcoded
const colors: Record<string, string> = {
  palmas: 'blue',
  rio: 'green',
  dtc: 'orange',
};

// ❌ Regex hardcoded
const match = serviceName.match(/^(.+)_(rio|palmas|dtc|genesis)$/);
```

#### DEPOIS (dinâmico):
```typescript
import { useSites } from '../hooks/useSites';

/**
 * REMOVIDA: getSiteBadgeColor() hardcoded
 * USAR: useSites().getSiteColor(code)
 */

/**
 * Aplica sufixo de site ao service name DINAMICAMENTE
 */
export function applySiteSuffix(
  serviceName: string,
  site?: string,
  cluster?: string
): string {
  const { naming, getSiteByCluster, getDefaultSite } = useSites();
  
  // OPÇÃO 1: Não adiciona sufixo
  if (naming.strategy === 'option1') {
    return serviceName;
  }
  
  // OPÇÃO 2: Adiciona sufixo se habilitado
  if (naming.strategy === 'option2' && naming.suffix_enabled) {
    let effectiveSite: string | undefined = undefined;
    
    if (site) {
      effectiveSite = site.toLowerCase();
    } else if (cluster) {
      // DINÂMICO: Busca site pelo cluster usando dados do KV
      const siteObj = getSiteByCluster(cluster);
      effectiveSite = siteObj?.code;
    }
    
    if (!effectiveSite) {
      return serviceName;
    }
    
    // Verificar se é site padrão DINAMICAMENTE
    const defaultSite = getDefaultSite();
    if (effectiveSite === defaultSite?.code) {
      return serviceName;
    }
    
    return `${serviceName}_${effectiveSite}`;
  }
  
  return serviceName;
}

/**
 * Extrai site dos metadata DINAMICAMENTE
 */
export function extractSiteFromMetadata(metadata: Record<string, any>): string | undefined {
  const { getSiteByCluster } = useSites();
  
  if (!metadata) return undefined;
  
  // Primeira prioridade: campo 'site' explícito
  if (metadata.site) {
    return metadata.site.toLowerCase();
  }
  
  // Segunda prioridade: inferir do 'cluster' DINAMICAMENTE
  if (metadata.cluster) {
    const site = getSiteByCluster(metadata.cluster);
    return site?.code;
  }
  
  // Terceira prioridade: 'datacenter'
  if (metadata.datacenter) {
    const dc = metadata.datacenter.toLowerCase();
    const { sites } = useSites();
    
    for (const site of sites) {
      if (site.datacenter.toLowerCase() === dc) {
        return site.code;
      }
    }
  }
  
  return undefined;
}

/**
 * Verifica se um service name tem sufixo de site DINAMICAMENTE
 */
export function hasSiteSuffix(serviceName: string): {
  hasSuffix: boolean;
  baseName: string;
  site: string | undefined;
} {
  const { getAllSiteCodes } = useSites();
  const siteCodes = getAllSiteCodes(); // ['palmas', 'rio', 'dtc']
  
  // Criar regex dinâmico: /^(.+)_(palmas|rio|dtc)$/
  const pattern = `^(.+)_(${siteCodes.join('|')})$`;
  const regex = new RegExp(pattern);
  const match = serviceName.match(regex);
  
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
```

---

### 6. **Refatoração do `MetadataFields.tsx`**

#### ANTES (hardcoded):
```typescript
// LINHAS 1753-1755: ❌ Hardcoded
if (hostname.includes('172.16.1.26')) return { displayName: 'Palmas', color: 'green' };
if (hostname.includes('172.16.200.14')) return { displayName: 'Rio', color: 'blue' };
if (hostname.includes('11.144.0.21')) return { displayName: 'DTC', color: 'orange' };
```

#### DEPOIS (dinâmico):
```typescript
import { useSites } from '../hooks/useSites';

// COLUNA "Descoberto Em"
const { getSiteByHostname } = useSites();

const getDisplayInfo = (hostname: string) => {
  // Busca site DINAMICAMENTE pelo hostname
  const site = getSiteByHostname(hostname);
  
  if (site) {
    return {
      displayName: site.name,    // "Palmas", "Rio de Janeiro", "Dtc"
      color: site.color,         // "red", "gold", "blue" (do KV)
    };
  }
  
  // Fallback se não encontrar
  return {
    displayName: hostname,
    color: 'default',
  };
};

// COLUNA "Origem"
const { sites, getSiteColor } = useSites();

const getDisplayInfo = (hostname: string) => {
  // Buscar site DINAMICAMENTE
  const site = sites.find(s => hostname.includes(s.prometheus_instance));
  
  if (site) {
    const color = getSiteColor(site.code);  // Cor do KV
    return { displayName: site.name, color };
  }
  
  return { displayName: hostname, color: 'default' };
};

// CARD DE EXEMPLOS (LINHAS 2021-2029)
const { sites } = useSites();

// Gerar exemplos DINAMICAMENTE dos sites reais
{sites.map(site => (
  <div key={site.code}>
    <Text code>selfnode_exporter</Text> + 
    <Tag color={site.color}>site={site.code}</Tag> → 
    <Text code>{site.is_default ? 'selfnode_exporter' : `selfnode_exporter_${site.code}`}</Text>
  </div>
))}
```

---

## 📋 CHECKLIST DE IMPLEMENTAÇÃO

### FASE 1: Backend - Infraestrutura
- [ ] Criar KV `skills/eye/settings/naming-strategy` com dados do .env
- [ ] Implementar cache de sites em `naming_utils.py`
- [ ] Criar `_load_sites_from_kv()` com fallback para .env
- [ ] Criar `_load_naming_strategy()` com fallback para .env
- [ ] Implementar `_update_cache()` com TTL de 60s
- [ ] Refatorar `apply_site_suffix()` para usar cache
- [ ] Refatorar `extract_site_from_metadata()` para usar cache
- [ ] Criar `get_site_by_cluster()` dinâmico
- [ ] Implementar background task para atualizar cache

### FASE 2: Backend - API
- [ ] Criar endpoint `GET /api/v1/settings/sites-config`
- [ ] Endpoint retorna: sites, naming, default_site (inferido)
- [ ] Adicionar testes para endpoint
- [ ] Atualizar `GET /api/v1/settings/naming-config` para ler do KV

### FASE 3: Frontend - Infraestrutura
- [ ] Criar `frontend/src/hooks/useSites.ts`
- [ ] Implementar `SitesProvider` com Context
- [ ] Implementar utility functions: `getSiteByCode()`, `getSiteByHostname()`, etc
- [ ] Adicionar `<SitesProvider>` no `App.tsx`

### FASE 4: Frontend - Refatoração
- [ ] Refatorar `namingUtils.ts`:
  - [ ] Remover `getSiteBadgeColor()` hardcoded
  - [ ] Refatorar `applySiteSuffix()` para usar `useSites()`
  - [ ] Refatorar `extractSiteFromMetadata()` para usar `useSites()`
  - [ ] Refatorar `hasSiteSuffix()` para regex dinâmico
  
- [ ] Refatorar `MetadataFields.tsx`:
  - [ ] Coluna "Descoberto Em" usar `getSiteByHostname()`
  - [ ] Coluna "Origem" usar `getSiteByHostname()`
  - [ ] Card de exemplos usar `sites.map()` dinâmico
  - [ ] Remover hardcoding de IPs (linhas 1753-1755, 1886-1894)

### FASE 5: Testes
- [ ] Testar adição de novo site no KV
- [ ] Testar mudança de cor no KV
- [ ] Testar mudança de default_site
- [ ] Testar mudança de naming_strategy
- [ ] Testar fallback para .env quando KV indisponível
- [ ] Testar cache expirando após 60s

### FASE 6: Migração e Documentação
- [ ] Criar script de migração `.env` → KV
- [ ] Documentar como adicionar novo site
- [ ] Documentar backward compatibility com .env
- [ ] Criar testes end-to-end

---

## 🚀 BENEFÍCIOS APÓS IMPLEMENTAÇÃO

### ✅ 100% Dinâmico
- Adicionar novo site: APENAS editar KV
- Mudar cor de site: APENAS editar KV
- Mudar site padrão: APENAS editar KV
- Mudar naming strategy: APENAS editar KV

### ✅ Consistência Total
- Cores vêm do KV (única fonte de verdade)
- IPs vêm do KV
- Clusters vêm do KV
- Não há divergência entre código e dados

### ✅ Manutenção Simplificada
- Código não precisa ser alterado para novos sites
- Testes não precisam ser atualizados
- Deploy não requer mudança de .env

### ✅ Backward Compatibility
- Fallback automático para .env se KV indisponível
- Migração gradual possível
- Rollback fácil

### ✅ Performance
- Cache em memória no backend (60s TTL)
- Context no frontend (carrega uma vez)
- Sem requisições desnecessárias

---

## 🔧 EXEMPLO DE USO APÓS IMPLEMENTAÇÃO

### Adicionar Novo Site (São Paulo)

#### 1. Adicionar no KV via UI
```json
{
  "code": "saopaulo",
  "name": "São Paulo",
  "is_default": false,
  "color": "purple",
  "cluster": "sp-datacenter",
  "datacenter": "saopaulo-alphaville",
  "environment": "production",
  "site": "saopaulo",
  "prometheus_instance": "10.0.0.100",
  "prometheus_host": "10.0.0.100",
  "ssh_port": 22,
  "prometheus_port": 9090
}
```

#### 2. Sistema Reconhece Automaticamente
- ✅ Backend cache atualiza em 60s
- ✅ Frontend recarrega ao reabrir página
- ✅ `extractSiteFromMetadata()` reconhece cluster "sp-datacenter"
- ✅ `getSiteBadgeColor('saopaulo')` retorna "purple"
- ✅ `applySiteSuffix('node_exporter', site='saopaulo')` retorna "node_exporter_saopaulo"
- ✅ Colunas "Descoberto Em" e "Origem" mostram "São Paulo" com cor roxa

**NENHUMA LINHA DE CÓDIGO ALTERADA!**

---

## 📝 ORDEM DE EXECUÇÃO

1. **FASE 1** (Backend - Infraestrutura): 2-3 horas
2. **FASE 2** (Backend - API): 1 hora
3. **FASE 3** (Frontend - Infraestrutura): 2 horas
4. **FASE 4** (Frontend - Refatoração): 3-4 horas
5. **FASE 5** (Testes): 2 horas
6. **FASE 6** (Migração e Docs): 1 hora

**TOTAL ESTIMADO: 11-13 horas**

---

## ⚠️ RISCOS E MITIGAÇÕES

### RISCO 1: Cache desatualizado
**Mitigação:** TTL de 60s + endpoint `/api/v1/settings/sites-config/reload` para forçar atualização

### RISCO 2: KV indisponível
**Mitigação:** Fallback automático para .env (backward compatibility)

### RISCO 3: Performance de múltiplas requisições
**Mitigação:** Cache em memória (backend) + Context (frontend)

### RISCO 4: Migração com downtime
**Mitigação:** Implementar fallback primeiro, depois migrar dados, remover .env por último

---

## 🎯 CONCLUSÃO

**TODOS os hardcodings de sites, cores, clusters e IPs serão eliminados.**

Sistema será **100% dinâmico** baseado no KV de Sites, permitindo:
- Adicionar/remover sites sem alterar código
- Mudar configurações via UI
- Manutenção simplificada
- Consistência total entre dados e apresentação

**PRÓXIMO PASSO:** Começar implementação FASE 1 (Backend - Infraestrutura)
