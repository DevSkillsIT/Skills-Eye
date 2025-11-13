# 📌 NOTA IMPORTANTE - AJUSTES VALIDADOS

**Data:** 13/11/2025  
**Status:** ✅ DOCUMENTO ATUALIZADO COM AJUSTES CRÍTICOS

---

## ⚠️ LEIA ANTES DE IMPLEMENTAR

Este plano foi **REVISADO E AJUSTADO** após discussão com o desenvolvedor sênior. Os ajustes críticos identificados estão documentados em:

📄 **`docs/AJUSTES_CRITICOS_PLANO_V2.md`**

### Principais Ajustes Aplicados:

1. **✅ Estrutura KV Fields**
   - Sistema **JÁ EXISTE** (`show_in_services`, `show_in_exporters`, `show_in_blackbox`)
   - **AÇÃO:** Apenas adicionar 4 novas propriedades para as novas páginas
   - Página Metadata Fields já tem coluna "Páginas" funcionando

2. **✅ Endpoints Duplos (Consul + Prometheus)**
   - `/monitoring/data` → Buscar serviços do Consul (igual Services.tsx)
   - `/monitoring/metrics` → Buscar métricas do Prometheus via PromQL
   - **AÇÃO:** Implementar AMBOS na Fase 1 (Dia 5)

3. **✅ Centralizar API em consulAPI**
   - Adicionar método `getMonitoringData()` em `services/api.ts`
   - DynamicMonitoringPage usa consulAPI, não fetch direto
   - **AÇÃO:** Seguir padrão existente de Services.tsx

4. **✅ Migração de Regras + Página de Gerenciamento**
   - Criar script `migrate_categorization_to_json.py` (Dia 3)
   - Criar página `/monitoring/rules` OU aba em "Tipos de Monitoramento"
   - **AÇÃO:** Implementar migração ANTES de modificar código

5. **✅ Testes de Persistência Integrados**
   - Adicionar **Dia 9.5** ao plano de implementação
   - Executar `run_all_persistence_tests.sh` (já criado)
   - Validar que customizações persistem nas 4 novas páginas
   - **AÇÃO:** Integrar testes existentes ao fluxo

---

## 🎯 REFERÊNCIAS IMPORTANTES

### Código Existente que NÃO deve ser modificado:
- ✅ `metadata_fields_manager.py` - Sistema de `show_in_*` **JÁ FUNCIONA**
- ✅ `consul_manager.py` - Usa httpx async, **NÃO migrar** para python-consul
- ✅ Services.tsx e BlackboxTargets.tsx - **REFERÊNCIAS**, não base de código

### Código Novo que será criado:
- 🆕 `consul_kv_config_manager.py` - Cache KV com TTL
- 🆕 `categorization_rule_engine.py` - Motor de regras JSON
- 🆕 `dynamic_query_builder.py` - Templates PromQL com Jinja2
- 🆕 `monitoring_unified.py` - Endpoints `/data` e `/metrics`
- 🆕 `DynamicMonitoringPage.tsx` - Componente base único
- 🆕 `migrate_categorization_to_json.py` - Script de migração

---

## 📝 VALIDAÇÕES PRÉ-IMPLEMENTAÇÃO

Antes de iniciar a Fase 1, confirmar:

- [ ] Leu `docs/AJUSTES_CRITICOS_PLANO_V2.md` completamente
- [ ] Entendeu que Services.tsx é REFERÊNCIA, não base de código
- [ ] Confirmou que sistema de `show_in_*` já existe
- [ ] Entendeu estratégia dupla (Consul + Prometheus)
- [ ] Revisou script de migração de regras
- [ ] Sabe onde estão os testes de persistência (`backend/test_*.py`)

---

## 🚀 INÍCIO DA IMPLEMENTAÇÃO

Após validar todos os pontos acima:

1. **Fase 1 (Dias 1-2):** Preparação e análise
2. **Fase 2 (Dias 3-5):** Backend (componentes + endpoints)
3. **Fase 3 (Dias 6-8):** Frontend (DynamicMonitoringPage + rotas)
4. **Fase 4 (Dias 9-10):** Testes funcionais
5. **Fase 4.5 (Dia 9.5):** **NOVO** - Testes de persistência
6. **Fase 5 (Dia 11):** Deploy

## 📋 SUMÁRIO DE AJUSTES

Este documento contém os ajustes críticos que devem ser aplicados ao **PLANO DE REFATORAÇÃO SKILLS EYE - VERSÃO COMPLETA 2.0.md** antes de iniciar a implementação.

### Ajustes Necessários:
1. ✅ **Estrutura do KV Fields** - Sistema já existe, apenas adicionar 4 novas páginas
2. ✅ **Endpoint /monitoring/data** - Buscar de Consul + Adicionar /monitoring/metrics
3. ✅ **DynamicMonitoringPage** - Adicionar método em consulAPI
4. ✅ **Categorization Rules** - Adicionar migração + página de gerenciamento
5. ✅ **Testes de Persistência** - Integrar testes existentes ao plano

---

## 1️⃣ AJUSTE: Estrutura do KV Fields

### ✅ SITUAÇÃO CONFIRMADA

O sistema **JÁ TEM** controle de visibilidade por página:

```python
# backend/api/metadata_fields_manager.py (CÓDIGO EXISTENTE)
class MetadataFieldModel(BaseModel):
    show_in_services: bool = Field(True, description="Mostrar na página Services")
    show_in_exporters: bool = Field(True, description="Mostrar na página Exporters")
    show_in_blackbox: bool = Field(True, description="Mostrar na página Blackbox")
```

**Frontend:** Página **Metadata Fields** tem coluna **"Páginas"** (checkbox multi-select).

### 🔧 AJUSTE NECESSÁRIO

**Adicionar apenas as 4 NOVAS propriedades no modelo:**

```python
# backend/api/metadata_fields_manager.py (ADICIONAR)
class MetadataFieldModel(BaseModel):
    # ... propriedades existentes ...
    show_in_services: bool = Field(True, description="Mostrar na página Services")
    show_in_exporters: bool = Field(True, description="Mostrar na página Exporters")
    show_in_blackbox: bool = Field(True, description="Mostrar na página Blackbox")
    
    # ✅ ADICIONAR estas 4 novas propriedades:
    show_in_network_probes: bool = Field(True, description="Mostrar na página Network Probes")
    show_in_web_probes: bool = Field(True, description="Mostrar na página Web Probes")
    show_in_system_exporters: bool = Field(True, description="Mostrar na página System Exporters")
    show_in_database_exporters: bool = Field(True, description="Mostrar na página Database Exporters")
```

### Hook React (MANTER conforme plano original)

```typescript
// frontend/src/hooks/useMetadataFields.ts
export function useTableFields(context: string) {
  const showInKey = `show_in_${context.replace(/-/g, '_')}`;
  
  const filtered = allFields.filter((field) => {
    // Se campo não tem a propriedade, exibe por padrão
    if (!(showInKey in field)) {
      return true;
    }
    return field[showInKey] !== false;
  });
  
  return { tableFields: filtered, loading };
}
```

### Frontend - Atualizar Página Metadata Fields

```typescript
// frontend/src/pages/MetadataFields.tsx (ATUALIZAR)

// Coluna "Páginas" deve incluir checkboxes para as 4 novas páginas:
const pagesColumn = {
  title: 'Páginas',
  dataIndex: 'pages',
  render: (_, record) => {
    const pages = [
      { key: 'services', label: 'Services', value: record.show_in_services },
      { key: 'exporters', label: 'Exporters', value: record.show_in_exporters },
      { key: 'blackbox', label: 'Blackbox', value: record.show_in_blackbox },
      // ✅ ADICIONAR estas 4 novas:
      { key: 'network_probes', label: 'Network Probes', value: record.show_in_network_probes },
      { key: 'web_probes', label: 'Web Probes', value: record.show_in_web_probes },
      { key: 'system_exporters', label: 'System Exporters', value: record.show_in_system_exporters },
      { key: 'database_exporters', label: 'Database Exporters', value: record.show_in_database_exporters },
    ];
    
    return (
      <Space direction="vertical" size={0}>
        {pages.filter(p => p.value).map(p => (
          <Tag key={p.key} color="blue">{p.label}</Tag>
        ))}
      </Space>
    );
  }
};
```

**✅ CONCLUSÃO:** Sistema já existe, apenas adicionar 4 novas propriedades.

---

## 2️⃣ AJUSTE: Endpoint /monitoring/data + /monitoring/metrics

### 🎯 ESTRATÉGIA DUPLA (Implementar AMBOS na Fase 1)

**Opção A: /monitoring/data** - Buscar serviços do Consul (igual Services.tsx)  
**Opção B: /monitoring/metrics** - Buscar métricas do Prometheus via PromQL

### ✅ IMPLEMENTAÇÃO: Opção A (Consul)

```python
# backend/api/monitoring_unified.py

@router.get("/data")
async def get_monitoring_data(
    category: str = Query(..., description="Categoria: network-probes, web-probes, etc"),
    company: Optional[str] = Query(None, description="Filtrar por empresa"),
    site: Optional[str] = Query(None, description="Filtrar por site")
):
    """
    Endpoint para buscar SERVIÇOS do Consul filtrados por categoria
    
    Este endpoint busca do Consul Service Registry (igual Services.tsx faz),
    NÃO do Prometheus.
    
    Args:
        category: Categoria de monitoramento (ex: network-probes)
        company: Filtro de empresa (opcional)
        site: Filtro de site (opcional)
    
    Returns:
        {
            "success": true,
            "category": "network-probes",
            "data": [
                {
                    "ID": "icmp-ramada-palmas-01",
                    "Service": "blackbox",
                    "Address": "10.0.0.1",
                    "Port": 9115,
                    "Meta": {
                        "module": "icmp",
                        "company": "Empresa Ramada",
                        "site": "palmas",
                        "env": "prod"
                    }
                }
            ],
            "total": 150
        }
    """
    try:
        from core.consul_manager import ConsulManager
        
        consul = ConsulManager()
        
        # STEP 1: Buscar TODOS os serviços do Consul
        all_services = await consul.get_services_list()
        
        # STEP 2: Mapear categoria → módulos
        # Esta lógica deve vir das regras de categorização (KV ou cache)
        modules_map = {
            'network-probes': ['icmp', 'tcp_connect', 'dns', 'ssh'],
            'web-probes': ['http_2xx', 'http_4xx', 'https', 'http_post'],
            'system-exporters': ['node_exporter', 'windows_exporter', 'snmp_exporter'],
            'database-exporters': ['mysqld_exporter', 'postgres_exporter', 'redis_exporter', 'mongodb_exporter'],
        }
        
        target_modules = modules_map.get(category, [])
        
        if not target_modules:
            raise HTTPException(
                status_code=404,
                detail=f"Categoria '{category}' não encontrada"
            )
        
        # STEP 3: Filtrar serviços por módulo
        filtered_services = []
        for svc in all_services:
            module = svc.get('Meta', {}).get('module', '')
            
            # Verificar se módulo está na lista da categoria
            if module in target_modules:
                # Aplicar filtros adicionais se fornecidos
                if company and svc.get('Meta', {}).get('company') != company:
                    continue
                if site and svc.get('Meta', {}).get('site') != site:
                    continue
                
                filtered_services.append(svc)
        
        return {
            "success": True,
            "category": category,
            "data": filtered_services,
            "total": len(filtered_services)
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[MONITORING DATA ERROR] {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
```

### ✅ IMPLEMENTAÇÃO: Opção B (Prometheus) - NOVA

```python
# backend/api/monitoring_unified.py

@router.get("/metrics")
async def get_monitoring_metrics(
    category: str = Query(..., description="Categoria: network-probes, web-probes, etc"),
    server: Optional[str] = Query(None, description="Servidor Prometheus"),
    time_range: str = Query("5m", description="Intervalo de tempo (ex: 5m, 1h)"),
    company: Optional[str] = Query(None),
    site: Optional[str] = Query(None)
):
    """
    Endpoint para buscar MÉTRICAS do Prometheus via PromQL
    
    Este endpoint executa queries PromQL e retorna métricas atuais,
    diferente de /data que busca serviços cadastrados no Consul.
    
    Args:
        category: Categoria de monitoramento
        server: Servidor Prometheus específico (opcional, padrão: primeiro disponível)
        time_range: Intervalo de tempo para métricas (ex: 5m)
        company: Filtro de empresa
        site: Filtro de site
    
    Returns:
        {
            "success": true,
            "category": "network-probes",
            "metrics": [
                {
                    "instance": "10.0.0.1",
                    "job": "blackbox",
                    "module": "icmp",
                    "status": 1,
                    "latency_ms": 25.3,
                    "timestamp": "2025-11-13T10:30:00Z"
                }
            ],
            "query": "probe_success{job='blackbox',__param_module=~'icmp|tcp'}",
            "prometheus_server": "172.16.1.26:9090",
            "total": 45
        }
    """
    try:
        import httpx
        from core.dynamic_query_builder import DynamicQueryBuilder, QUERY_TEMPLATES
        from core.consul_kv_config_manager import ConsulKVConfigManager
        
        config_manager = ConsulKVConfigManager()
        query_builder = DynamicQueryBuilder()
        
        # STEP 1: Determinar servidor Prometheus
        if not server:
            # Buscar lista de servidores do cache de tipos
            types_cache = await config_manager.get('monitoring-types/cache')
            if types_cache and 'servers' in types_cache:
                server = list(types_cache['servers'].keys())[0]
            else:
                raise HTTPException(
                    status_code=500,
                    detail="Nenhum servidor Prometheus configurado"
                )
        
        # STEP 2: Buscar tipos da categoria
        types_cache = await config_manager.get('monitoring-types/cache')
        
        if not types_cache:
            raise HTTPException(
                status_code=500,
                detail="Cache de tipos não disponível"
            )
        
        # Encontrar tipos da categoria
        category_types = []
        for cat_data in types_cache.get('categories', []):
            if cat_data['category'] == category:
                category_types = cat_data['types']
                break
        
        if not category_types:
            raise HTTPException(
                status_code=404,
                detail=f"Categoria '{category}' não encontrada"
            )
        
        # STEP 3: Construir query PromQL baseado na categoria
        if category in ['network-probes', 'web-probes']:
            # Blackbox probes
            modules = [t['module'] for t in category_types if t.get('module')]
            
            query = query_builder.build(
                QUERY_TEMPLATES['network_probe_success'],
                {
                    'modules': modules,
                    'company': company,
                    'site': site
                }
            )
        
        elif category == 'system-exporters':
            # Node/Windows exporters - CPU usage
            jobs = [t['job_name'] for t in category_types]
            
            query = query_builder.build(
                QUERY_TEMPLATES['node_cpu_usage'],
                {
                    'jobs': jobs,
                    'time_range': time_range
                }
            )
        
        elif category == 'database-exporters':
            # Database exporters - up status
            jobs = [t['job_name'] for t in category_types]
            query = f"up{{job=~\"{'|'.join(jobs)}\"}}"
        
        else:
            # Generic query
            jobs = [t['job_name'] for t in category_types]
            query = f"up{{job=~\"{'|'.join(jobs)}\"}}"
        
        # STEP 4: Executar query no Prometheus
        prometheus_url = f"http://{server}:9090"
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{prometheus_url}/api/v1/query",
                params={'query': query},
                timeout=10.0
            )
            response.raise_for_status()
            prom_data = response.json()
        
        if prom_data['status'] != 'success':
            raise HTTPException(
                status_code=500,
                detail=f"Prometheus query failed: {prom_data.get('error')}"
            )
        
        # STEP 5: Processar resultados
        results = prom_data['data']['result']
        
        formatted_metrics = []
        for result in results:
            metric = result['metric']
            value = result['value'][1]  # [timestamp, value]
            
            formatted_metrics.append({
                'instance': metric.get('instance', ''),
                'job': metric.get('job', ''),
                'module': metric.get('__param_module', ''),
                'status': float(value),
                'timestamp': result['value'][0],
                **{k: v for k, v in metric.items() if not k.startswith('__')}
            })
        
        return {
            "success": True,
            "category": category,
            "metrics": formatted_metrics,
            "query": query,
            "prometheus_server": server,
            "total": len(formatted_metrics)
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[MONITORING METRICS ERROR] {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
```

### 🔄 DynamicMonitoringPage - Escolher Fonte de Dados

```typescript
// frontend/src/pages/DynamicMonitoringPage.tsx

interface DynamicMonitoringPageProps {
  category: string;
  dataSource?: 'consul' | 'prometheus';  // ✅ NOVO: Escolher fonte
}

const DynamicMonitoringPage: React.FC<DynamicMonitoringPageProps> = ({ 
  category,
  dataSource = 'consul'  // Padrão: buscar do Consul (serviços)
}) => {
  
  const requestHandler = useCallback(async (params: any) => {
    try {
      const queryParams = new URLSearchParams({
        category,
        ...filters
      });
      
      // Escolher endpoint baseado na fonte
      const endpoint = dataSource === 'consul' 
        ? `/api/v1/monitoring/data?${queryParams}`      // Serviços Consul
        : `/api/v1/monitoring/metrics?${queryParams}`;  // Métricas Prometheus
      
      const response = await fetch(endpoint);
      const data = await response.json();
      
      return {
        data: dataSource === 'consul' ? data.data : data.metrics,
        success: true,
        total: data.total
      };
    } catch (error) {
      message.error('Erro ao carregar dados: ' + error);
      return { data: [], success: false, total: 0 };
    }
  }, [category, filters, dataSource]);
  
  // ... resto do componente
};
```

**✅ CONCLUSÃO:** Implementar AMBOS endpoints na Fase 1 (Dia 5).

---

## 3️⃣ AJUSTE: DynamicMonitoringPage - Método em consulAPI

### 🔧 ADICIONAR em services/api.ts

```typescript
// frontend/src/services/api.ts

export const consulAPI = {
  // ... métodos existentes ...
  
  /**
   * ✅ NOVO: Método genérico para buscar dados de monitoramento
   * 
   * Pode buscar de Consul (serviços) ou Prometheus (métricas)
   */
  getMonitoringData: async (
    category: string,
    source: 'consul' | 'prometheus' = 'consul',
    filters?: Record<string, string>
  ): Promise<MonitoringDataResponse> => {
    const params = new URLSearchParams({ category, ...filters });
    
    const endpoint = source === 'consul'
      ? `/api/v1/monitoring/data?${params}`
      : `/api/v1/monitoring/metrics?${params}`;
    
    const response = await httpClient.get(endpoint);
    return response.data;
  },
  
  /**
   * ✅ NOVO: Sincronizar cache de tipos de monitoramento
   */
  syncMonitoringCache: async (): Promise<{ success: boolean; message: string }> => {
    const response = await httpClient.post('/api/v1/monitoring/sync-cache');
    return response.data;
  }
};

// Tipos TypeScript
interface MonitoringDataResponse {
  success: boolean;
  category: string;
  data?: any[];      // Para endpoint /data (Consul)
  metrics?: any[];   // Para endpoint /metrics (Prometheus)
  total: number;
  query?: string;    // Query PromQL (só para /metrics)
}
```

### 🔄 DynamicMonitoringPage usa consulAPI

```typescript
// frontend/src/pages/DynamicMonitoringPage.tsx

import { consulAPI } from '../services/api';

const DynamicMonitoringPage: React.FC<DynamicMonitoringPageProps> = ({ 
  category,
  dataSource = 'consul'
}) => {
  
  // ✅ USAR consulAPI em vez de fetch direto
  const requestHandler = useCallback(async (params: any) => {
    try {
      const data = await consulAPI.getMonitoringData(category, dataSource, filters);
      
      return {
        data: data.data || data.metrics || [],
        success: true,
        total: data.total
      };
    } catch (error) {
      message.error('Erro ao carregar dados: ' + error);
      return { data: [], success: false, total: 0 };
    }
  }, [category, filters, dataSource]);
  
  // Sincronizar cache
  const handleSync = useCallback(async () => {
    setSyncLoading(true);
    try {
      const result = await consulAPI.syncMonitoringCache();
      message.success(result.message || 'Cache sincronizado!');
      actionRef.current?.reload();
    } catch (error) {
      message.error('Erro ao sincronizar: ' + error);
    } finally {
      setSyncLoading(false);
    }
  }, []);
  
  // ... resto do componente
};
```

**✅ CONCLUSÃO:** Centralizar chamadas API em `services/api.ts` para reutilização.

---

## 4️⃣ AJUSTE: Categorization Rules - Migração + Página de Gerenciamento

### 📝 IMPLEMENTAR Script de Migração (Dia 3)

```python
# backend/migrate_categorization_to_json.py

"""
Script de Migração: Categorização Hardcoded → JSON no KV

Este script extrai os 40+ padrões de categorização existentes em
monitoring_types_dynamic.py e migra para JSON no Consul KV.

EXECUÇÃO:
    python migrate_categorization_to_json.py
"""

import asyncio
import json
from datetime import datetime
from core.kv_manager import KVManager

# Extrair padrões existentes de monitoring_types_dynamic.py
EXPORTER_PATTERNS = {
    # Infrastructure
    'haproxy': ('infrastructure-exporters', 'HAProxy Exporter', 'haproxy_exporter'),
    'nginx': ('infrastructure-exporters', 'Nginx Exporter', 'nginx_exporter'),
    'kafka': ('infrastructure-exporters', 'Kafka Exporter', 'kafka_exporter'),
    'rabbitmq': ('infrastructure-exporters', 'RabbitMQ Exporter', 'rabbitmq_exporter'),
    
    # Databases
    'mysql': ('database-exporters', 'MySQL Exporter', 'mysqld_exporter'),
    'postgres': ('database-exporters', 'PostgreSQL Exporter', 'postgres_exporter'),
    'redis': ('database-exporters', 'Redis Exporter', 'redis_exporter'),
    'mongodb': ('database-exporters', 'MongoDB Exporter', 'mongodb_exporter'),
    
    # System
    'node': ('system-exporters', 'Node Exporter (Linux)', 'node_exporter'),
    'windows': ('system-exporters', 'Windows Exporter', 'windows_exporter'),
    'snmp': ('system-exporters', 'SNMP Exporter', 'snmp_exporter'),
    
    # Hardware
    'ipmi': ('hardware-exporters', 'IPMI Exporter', 'ipmi_exporter'),
    
    # Network Devices
    'mktxp': ('network-devices', 'MikroTik Exporter (MKTXP)', 'mktxp'),
    
    # Adicionar TODOS os 40+ padrões restantes aqui...
}

# Módulos Blackbox
BLACKBOX_MODULES = {
    'icmp': 'network-probes',
    'ping': 'network-probes',
    'tcp_connect': 'network-probes',
    'tcp': 'network-probes',
    'dns': 'network-probes',
    'ssh': 'network-probes',
    'http_2xx': 'web-probes',
    'http_4xx': 'web-probes',
    'https': 'web-probes',
    'http_post': 'web-probes',
    'http_get': 'web-probes',
}


async def migrate():
    """Executa migração"""
    print("🔄 Iniciando migração de regras de categorização...")
    
    rules = []
    
    # 1. Regras de Blackbox (prioridade alta: 100)
    print("\n📦 Convertendo regras de Blackbox...")
    for module, category in BLACKBOX_MODULES.items():
        rules.append({
            "id": f"blackbox_{module}",
            "priority": 100,
            "category": category,
            "display_name": f"Blackbox: {module.upper()}",
            "conditions": {
                "job_name_pattern": f"^{module}.*",
                "metrics_path": "/probe",
                "module_pattern": f"^{module}$"
            }
        })
    print(f"  ✅ {len(BLACKBOX_MODULES)} regras de Blackbox")
    
    # 2. Regras de Exporters (prioridade média: 80)
    print("\n📦 Convertendo regras de Exporters...")
    for pattern_name, (category, display_name, exporter_type) in EXPORTER_PATTERNS.items():
        rules.append({
            "id": f"exporter_{pattern_name}",
            "priority": 80,
            "category": category,
            "display_name": display_name,
            "exporter_type": exporter_type,
            "conditions": {
                "job_name_pattern": f"^{pattern_name}.*",
                "metrics_path": "/metrics"
            }
        })
    print(f"  ✅ {len(EXPORTER_PATTERNS)} regras de Exporters")
    
    # 3. Ordenar por prioridade (maior primeiro)
    rules.sort(key=lambda r: r['priority'], reverse=True)
    
    # 4. Criar estrutura JSON
    rules_data = {
        "version": "1.0.0",
        "last_updated": datetime.now().isoformat(),
        "total_rules": len(rules),
        "rules": rules,
        "default_category": "custom-exporters",
        "categories": [
            {"id": "network-probes", "display_name": "Network Probes (Rede)"},
            {"id": "web-probes", "display_name": "Web Probes (Aplicações)"},
            {"id": "system-exporters", "display_name": "Exporters: Sistemas"},
            {"id": "database-exporters", "display_name": "Exporters: Bancos de Dados"},
            {"id": "infrastructure-exporters", "display_name": "Exporters: Infraestrutura"},
            {"id": "hardware-exporters", "display_name": "Exporters: Hardware"},
            {"id": "network-devices", "display_name": "Dispositivos de Rede"},
            {"id": "custom-exporters", "display_name": "Exporters Customizados"},
        ]
    }
    
    # 5. Salvar no Consul KV
    print("\n💾 Salvando no Consul KV...")
    kv = KVManager()
    
    key = 'skills/eye/monitoring-types/categorization/rules'
    success = await kv.put_json(key, rules_data)
    
    if success:
        print(f"  ✅ Regras salvas em: {key}")
        print(f"\n📊 RESUMO:")
        print(f"  - Total de regras: {len(rules)}")
        print(f"  - Blackbox: {len(BLACKBOX_MODULES)}")
        print(f"  - Exporters: {len(EXPORTER_PATTERNS)}")
        print(f"  - Categorias: {len(rules_data['categories'])}")
        print(f"\n✅ MIGRAÇÃO CONCLUÍDA COM SUCESSO!")
        
        # Exibir preview das regras
        print(f"\n📋 Preview das primeiras 3 regras:")
        for rule in rules[:3]:
            print(f"  - {rule['id']} (prioridade {rule['priority']}) → {rule['category']}")
        
        return True
    else:
        print(f"  ❌ ERRO ao salvar regras no KV")
        return False


async def validate_migration():
    """Valida que regras foram salvas corretamente"""
    print("\n🔍 Validando migração...")
    
    kv = KVManager()
    key = 'skills/eye/monitoring-types/categorization/rules'
    
    rules_data = await kv.get_json(key)
    
    if not rules_data:
        print("  ❌ Regras não encontradas no KV!")
        return False
    
    print(f"  ✅ Regras encontradas no KV")
    print(f"  ✅ Versão: {rules_data.get('version')}")
    print(f"  ✅ Total de regras: {rules_data.get('total_rules')}")
    print(f"  ✅ Última atualização: {rules_data.get('last_updated')}")
    
    return True


async def main():
    """Executa migração e validação"""
    print("=" * 80)
    print(" MIGRAÇÃO: CATEGORIZAÇÃO HARDCODED → JSON NO KV")
    print("=" * 80)
    
    # Migrar
    success = await migrate()
    
    if not success:
        print("\n❌ Migração FALHOU!")
        return
    
    # Validar
    validated = await validate_migration()
    
    if validated:
        print("\n✅ MIGRAÇÃO E VALIDAÇÃO OK!")
        print("\n📝 PRÓXIMOS PASSOS:")
        print("  1. Modificar monitoring_types_dynamic.py para usar CategorizationRuleEngine")
        print("  2. Testar que categorização produz mesmos resultados")
        print("  3. Remover código hardcoded após validação")
    else:
        print("\n⚠️  Migração OK mas validação FALHOU - verificar KV")


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n❌ Migração cancelada pelo usuário")
    except Exception as e:
        print(f"\n❌ ERRO: {e}")
        import traceback
        traceback.print_exc()
```

### 🎨 FRONTEND: Página de Gerenciamento de Regras

**Opção 1: Nova Página `/monitoring/rules`**

```typescript
// frontend/src/pages/MonitoringRules.tsx

/**
 * Página de Gerenciamento de Regras de Categorização
 * 
 * Permite visualizar, editar, adicionar e remover regras de categorização
 * de tipos de monitoramento.
 */

import React, { useState, useRef } from 'react';
import { ProTable } from '@ant-design/pro-components';
import { Button, Tag, Modal, Form, Input, Select, InputNumber, message } from 'antd';

interface CategorizationRule {
  id: string;
  priority: number;
  category: string;
  display_name: string;
  conditions: {
    job_name_pattern?: string;
    metrics_path?: string;
    module_pattern?: string;
  };
}

const MonitoringRules: React.FC = () => {
  const [rules, setRules] = useState<CategorizationRule[]>([]);
  const [modalVisible, setModalVisible] = useState(false);
  const [editingRule, setEditingRule] = useState<CategorizationRule | null>(null);
  
  const columns = [
    {
      title: 'ID',
      dataIndex: 'id',
      width: 200,
    },
    {
      title: 'Prioridade',
      dataIndex: 'priority',
      width: 100,
      sorter: (a, b) => b.priority - a.priority,
      render: (priority) => <Tag color={priority >= 100 ? 'red' : 'blue'}>{priority}</Tag>
    },
    {
      title: 'Categoria',
      dataIndex: 'category',
      width: 200,
      render: (category) => {
        const colors = {
          'network-probes': 'cyan',
          'web-probes': 'blue',
          'system-exporters': 'green',
          'database-exporters': 'purple',
        };
        return <Tag color={colors[category] || 'default'}>{category}</Tag>;
      }
    },
    {
      title: 'Display Name',
      dataIndex: 'display_name',
      width: 250,
    },
    {
      title: 'Job Pattern',
      dataIndex: ['conditions', 'job_name_pattern'],
      width: 200,
      render: (pattern) => <code>{pattern || '-'}</code>
    },
    {
      title: 'Ações',
      width: 150,
      render: (_, record) => (
        <Button.Group>
          <Button size="small" onClick={() => handleEdit(record)}>Editar</Button>
          <Button size="small" danger onClick={() => handleDelete(record.id)}>Deletar</Button>
        </Button.Group>
      )
    }
  ];
  
  return (
    <PageContainer
      title="Regras de Categorização"
      extra={[
        <Button key="add" type="primary" onClick={() => setModalVisible(true)}>
          + Adicionar Regra
        </Button>,
        <Button key="reload" onClick={loadRules}>Recarregar</Button>
      ]}
    >
      <ProTable
        columns={columns}
        dataSource={rules}
        rowKey="id"
        search={false}
      />
      
      {/* Modal de Edição */}
      <Modal
        title={editingRule ? 'Editar Regra' : 'Nova Regra'}
        visible={modalVisible}
        onCancel={() => setModalVisible(false)}
        onOk={handleSave}
      >
        <Form layout="vertical">
          <Form.Item label="ID" required>
            <Input placeholder="ex: blackbox_icmp" />
          </Form.Item>
          
          <Form.Item label="Prioridade" required>
            <InputNumber min={1} max={999} />
          </Form.Item>
          
          <Form.Item label="Categoria" required>
            <Select>
              <Select.Option value="network-probes">Network Probes</Select.Option>
              <Select.Option value="web-probes">Web Probes</Select.Option>
              <Select.Option value="system-exporters">System Exporters</Select.Option>
              <Select.Option value="database-exporters">Database Exporters</Select.Option>
            </Select>
          </Form.Item>
          
          <Form.Item label="Job Name Pattern (Regex)">
            <Input placeholder="ex: ^icmp.*" />
          </Form.Item>
          
          <Form.Item label="Metrics Path">
            <Select>
              <Select.Option value="/probe">/ probe (Blackbox)</Select.Option>
              <Select.Option value="/metrics">/metrics (Exporter)</Select.Option>
            </Select>
          </Form.Item>
        </Form>
      </Modal>
    </PageContainer>
  );
};
```

**Opção 2: Aba na Página "Tipos de Monitoramento"**

```typescript
// frontend/src/pages/MonitoringTypes.tsx (ATUALIZAR)

<Tabs defaultActiveKey="types">
  <TabPane tab="Tipos Detectados" key="types">
    {/* Conteúdo existente */}
  </TabPane>
  
  {/* ✅ NOVA ABA */}
  <TabPane tab="Regras de Categorização" key="rules">
    <MonitoringRulesTable />
  </TabPane>
  
  <TabPane tab="Cache" key="cache">
    {/* Informações sobre cache */}
  </TabPane>
</Tabs>
```

**✅ CONCLUSÃO:** Implementar script de migração (Dia 3) + Página de gerenciamento (Dia 8).

---

## 5️⃣ AJUSTE: Testes de Persistência - Integração ao Plano

### 📝 ADICIONAR Fase 4.5 ao Plano de Implementação

Inserir APÓS **Dia 9: Testes Funcionais**:

```markdown
#### Dia 9.5: Testes de Persistência de Customizações

**MANHÃ: Validar Merge de Fields**

**Contexto:** Implementamos bateria completa de testes de persistência de customizações
de campos metadata. Estes testes validam que modificações (required, auto_register,
category, order) NÃO SÃO PERDIDAS após reinícios, sincronizações, etc.

38.5 ✅ **Executar bateria completa de testes**
    ```bash
    cd backend
    ./run_all_persistence_tests.sh
    
    # Este script executa sequencialmente:
    # 1. test_fields_merge.py          - Testes básicos de merge
    # 2. test_all_scenarios.py          - 8 cenários de uso
    # 3. test_stress_scenarios.py       - 6 testes de stress/concorrência
    # 4. test_frontend_integration.py   - Testes via Playwright (UI)
    
    # Resultado esperado: TODOS PASSANDO (100%)
    ```

**TARDE: Validar Integração com Novas Páginas**

38.6 ✅ **Testar persistência nas novas páginas**
    ```
    Cenário: Verificar que customizações de fields persistem nas 4 novas páginas
    
    Passos:
    1. Acessar /metadata-fields
    2. Customizar campo "company":
       - Marcar "Required" = true
       - Marcar "Auto Register" = true
       - Category = "business"
       - Adicionar checkbox "Network Probes" na coluna "Páginas"
    3. Salvar
    
    4. Acessar /monitoring/network-probes
    5. Validar que campo "company" aparece na tabela
    6. Validar que campo é obrigatório no formulário
    
    7. Clicar em "Sincronizar Cache" (novo botão)
    8. Aguardar 3 segundos
    9. Recarregar página (F5)
    
    10. Validar que customizações AINDA ESTÃO LÁ:
        - Campo aparece na tabela
        - Campo é obrigatório
        - Category = "business"
    
    11. Reiniciar backend:
        bash scripts/deployment/restart-backend.sh
    
    12. Aguardar backend reiniciar (10s)
    13. Acessar /monitoring/network-probes novamente
    14. Validar que TODAS customizações persistiram
    
    Resultado esperado: ✓ Customizações PRESERVADAS
    ```

38.7 ✅ **Validar que merge funciona com novos campos**
    ```
    Cenário: Adicionar novo campo via add-to-kv e validar que não perde customizações
    
    Passos:
    1. Customizar campo "vendor" existente
    2. Adicionar novo campo "test_field" via POST /add-to-kv
    3. Validar que campo "vendor" mantém customizações
    4. Sincronizar cache
    5. Validar que ambos os campos estão OK
    
    Resultado esperado: ✓ Merge preserva campos existentes
    ```

38.8 ✅ **Documentar testes no CHANGELOG**
    ```bash
    cat >> CHANGELOG-SESSION.md << 'EOF'
    
    ## 2025-11-13 - Testes de Persistência
    
    ### Validações Executadas
    
    - ✅ Bateria completa de testes (run_all_persistence_tests.sh)
    - ✅ 8 cenários de uso (reinício, sync, PATCH, etc)
    - ✅ 6 testes de stress (100 GETs, race conditions, etc)
    - ✅ Testes UI com Playwright
    - ✅ Validação em 4 novas páginas de monitoramento
    - ✅ Merge de campos durante add-to-kv
    
    ### Resultados
    
    - **Todos os testes passaram (100%)**
    - Customizações persistem após:
      - Reinícios do backend
      - Sincronizações de cache
      - Extrações forçadas
      - Limpeza de cache do browser
      - Múltiplas operações simultâneas
    
    ### Cobertura
    
    - Campos testados: vendor, region, campoextra1
    - Propriedades validadas: required, auto_register, category, order, description
    - Páginas validadas: Services, Exporters, Blackbox, Network Probes
    EOF
    ```

**RESULTADO ESPERADO:**
- ✅ Todos os testes de persistência passando
- ✅ Customizações preservadas nas 4 novas páginas
- ✅ Merge funciona corretamente com novos campos
- ✅ Documentação atualizada

**TEMPO ESTIMADO:** 3-4 horas
```

**✅ CONCLUSÃO:** Integrar testes existentes no Dia 9.5 do plano de implementação.

---

## 📊 RESUMO DOS AJUSTES

| # | Ajuste | Status | Impacto |
|---|--------|--------|---------|
| 1 | Estrutura KV Fields | ✅ Ajustado | Adicionar 4 propriedades no modelo |
| 2 | Endpoint /monitoring/data + /metrics | ✅ Ajustado | Implementar AMBOS (Consul + Prometheus) |
| 3 | DynamicMonitoringPage + consulAPI | ✅ Ajustado | Centralizar em services/api.ts |
| 4 | Categorization Rules + Página | ✅ Ajustado | Script migração + página gerenciamento |
| 5 | Testes de Persistência | ✅ Ajustado | Adicionar Dia 9.5 ao plano |

---

## 🎯 PRÓXIMOS PASSOS

1. ✅ **Revisar este documento** - Confirmar que ajustes estão corretos
2. ✅ **Atualizar plano principal** - Aplicar ajustes no documento original
3. ✅ **Iniciar Fase 1** - Preparação e setup (Dia 1-2)
4. ✅ **Seguir plano ajustado** - Implementação das fases 2-5

---

**DOCUMENTO APROVADO E PRONTO PARA IMPLEMENTAÇÃO! 🚀**

**Data de Aprovação:** 13/11/2025  
**Responsável:** Desenvolvedor Sênior + AI Assistant  
**Status:** ✅ VALIDADO E AJUSTADO
