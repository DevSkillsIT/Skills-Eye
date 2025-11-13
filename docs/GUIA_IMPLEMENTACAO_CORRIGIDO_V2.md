# 📘 GUIA DE IMPLEMENTAÇÃO CORRIGIDO - SKILLS EYE V2.0

**Data:** 13/11/2025  
**Versão:** 2.0 - AJUSTADO E VALIDADO  
**Base:** PLANO DE REFATORAÇÃO SKILLS EYE - VERSÃO COMPLETA 2.0.md + AJUSTES_CRITICOS_PLANO_V2.md

---

## 🎯 PROPÓSITO DESTE DOCUMENTO

Este guia **SUBSTITUI** as seções do plano original que tinham inconsistências. Use este documento como referência principal durante a implementação, complementando o plano original onde indicado.

---

## 🔧 SEÇÃO 1: MetadataFieldModel - CÓDIGO CORRETO

### 📝 Arquivo: `backend/api/metadata_fields_manager.py`

**MODIFICAR classe MetadataFieldModel:**

```python
class MetadataFieldModel(BaseModel):
    """Modelo de campo metadata"""
    name: str = Field(..., description="Nome técnico do campo")
    display_name: str = Field(..., description="Nome amigável para exibição")
    description: str = Field("", description="Descrição do campo")
    source_label: str = Field(..., description="Source label do Prometheus")
    field_type: str = Field(..., description="Tipo: string, number, select, text, url")
    required: bool = Field(False, description="Campo obrigatório")
    show_in_table: bool = Field(True, description="Mostrar em tabelas")
    show_in_dashboard: bool = Field(False, description="Mostrar no dashboard")
    show_in_form: bool = Field(True, description="Mostrar em formulários")
    options: Optional[List[str]] = Field(None, description="Opções para select")
    order: int = Field(0, description="Ordem de exibição")
    category: Union[str, List[str]] = Field("extra", description="Categoria(s) do campo")
    editable: bool = Field(True, description="Pode ser editado")
    validation_regex: Optional[str] = Field(None, description="Regex de validação")
    
    # Campos de visibilidade por página (JÁ EXISTEM)
    show_in_services: bool = Field(True, description="Mostrar na página Services")
    show_in_exporters: bool = Field(True, description="Mostrar na página Exporters")
    show_in_blackbox: bool = Field(True, description="Mostrar na página Blackbox")
    
    # ✅ ADICIONAR estas 4 novas propriedades:
    show_in_network_probes: bool = Field(True, description="Mostrar na página Network Probes")
    show_in_web_probes: bool = Field(True, description="Mostrar na página Web Probes")
    show_in_system_exporters: bool = Field(True, description="Mostrar na página System Exporters")
    show_in_database_exporters: bool = Field(True, description="Mostrar na página Database Exporters")
    
    # Campos de filtro
    show_in_filter: bool = Field(True, description="Mostrar em filtros")
```

**LOCALIZAÇÃO NO PLANO ORIGINAL:** Seção 5.1 - Backend Python

**AÇÃO:** Adicionar as 4 linhas marcadas com ✅ no Dia 3 da implementação.

---

## 🔧 SEÇÃO 2: Endpoint /monitoring/data - CÓDIGO CORRETO

### 📝 Arquivo: `backend/api/monitoring_unified.py` (CRIAR)

**Implementar endpoint que busca do CONSUL, não Prometheus:**

```python
@router.get("/data")
async def get_monitoring_data(
    category: str = Query(..., description="Categoria: network-probes, web-probes, etc"),
    company: Optional[str] = Query(None, description="Filtrar por empresa"),
    site: Optional[str] = Query(None, description="Filtrar por site"),
    env: Optional[str] = Query(None, description="Filtrar por ambiente")
):
    """
    Endpoint para buscar SERVIÇOS do Consul filtrados por categoria
    
    IMPORTANTE: Este endpoint busca SERVIÇOS cadastrados no Consul Service Registry,
    NÃO métricas do Prometheus. Para métricas, use /monitoring/metrics.
    
    Funcionamento:
    1. Busca TODOS os serviços do Consul (via consul_manager.get_services_list())
    2. Filtra por módulo baseado na categoria solicitada
    3. Aplica filtros adicionais (company, site, env)
    4. Retorna lista de serviços filtrada
    
    Diferença de Services.tsx:
    - Services.tsx mostra TODOS os serviços
    - Este endpoint filtra por CATEGORIA (network-probes, web-probes, etc)
    
    Args:
        category: Categoria de monitoramento (ex: network-probes)
        company: Filtro de empresa (opcional)
        site: Filtro de site (opcional)
        env: Filtro de ambiente (opcional)
    
    Returns:
        {
            "success": true,
            "category": "network-probes",
            "data": [
                {
                    "ID": "icmp-ramada-palmas-01",
                    "Service": "blackbox",
                    "Node": "consul-server-1",
                    "Address": "10.0.0.1",
                    "Port": 9115,
                    "Meta": {
                        "module": "icmp",
                        "company": "Empresa Ramada",
                        "site": "palmas",
                        "env": "prod",
                        "name": "Gateway Principal"
                    },
                    "Tags": ["blackbox", "icmp", "palmas"]
                }
            ],
            "total": 150,
            "filters_applied": {
                "category": "network-probes",
                "company": "Empresa Ramada",
                "site": "palmas"
            }
        }
    
    Example:
        GET /api/v1/monitoring/data?category=network-probes&company=Ramada
    """
    try:
        from core.consul_manager import ConsulManager
        from core.consul_kv_config_manager import ConsulKVConfigManager
        
        logger.info(f"[MONITORING DATA] Buscando dados para category={category}")
        
        consul = ConsulManager()
        config_manager = ConsulKVConfigManager()
        
        # STEP 1: Buscar mapeamento categoria → módulos do cache de tipos
        types_cache = await config_manager.get('monitoring-types/cache')
        
        if not types_cache:
            # Fallback: usar mapeamento hardcoded temporário
            logger.warning("[MONITORING DATA] Cache de tipos não disponível, usando fallback")
            modules_map = {
                'network-probes': ['icmp', 'tcp_connect', 'tcp', 'dns', 'ssh', 'ping'],
                'web-probes': ['http_2xx', 'http_4xx', 'https', 'http_post', 'http_get'],
                'system-exporters': ['node_exporter', 'windows_exporter', 'snmp_exporter', 'selfnode'],
                'database-exporters': ['mysqld_exporter', 'postgres_exporter', 'redis_exporter', 'mongodb_exporter'],
            }
        else:
            # Extrair módulos do cache baseado na categoria
            modules_map = {}
            for cat_data in types_cache.get('categories', []):
                cat_id = cat_data['category']
                modules = [t.get('module') or t.get('id') for t in cat_data.get('types', [])]
                modules_map[cat_id] = [m for m in modules if m]  # Remove None
        
        target_modules = modules_map.get(category, [])
        
        if not target_modules:
            raise HTTPException(
                status_code=404,
                detail=f"Categoria '{category}' não encontrada ou sem módulos"
            )
        
        logger.info(f"[MONITORING DATA] Módulos da categoria '{category}': {target_modules}")
        
        # STEP 2: Buscar TODOS os serviços do Consul
        all_services = await consul.get_services_list()
        logger.info(f"[MONITORING DATA] Total de serviços no Consul: {len(all_services)}")
        
        # STEP 3: Filtrar serviços
        filtered_services = []
        
        for svc in all_services:
            meta = svc.get('Meta', {})
            module = meta.get('module', '')
            
            # Filtro 1: Verificar se módulo está na lista da categoria
            if module not in target_modules:
                continue
            
            # Filtro 2: Company (se fornecido)
            if company:
                svc_company = meta.get('company', '')
                if company.lower() not in svc_company.lower():
                    continue
            
            # Filtro 3: Site (se fornecido)
            if site:
                svc_site = meta.get('site', '')
                if site.lower() not in svc_site.lower():
                    continue
            
            # Filtro 4: Env (se fornecido)
            if env:
                svc_env = meta.get('env', '')
                if env.lower() != svc_env.lower():
                    continue
            
            # Serviço passou por todos os filtros
            filtered_services.append(svc)
        
        logger.info(f"[MONITORING DATA] Serviços após filtros: {len(filtered_services)}")
        
        return {
            "success": True,
            "category": category,
            "data": filtered_services,
            "total": len(filtered_services),
            "filters_applied": {
                "category": category,
                "company": company,
                "site": site,
                "env": env
            },
            "available_modules": target_modules
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[MONITORING DATA ERROR] {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
```

**LOCALIZAÇÃO NO PLANO ORIGINAL:** Seção 5.1.4 - Endpoint Unificado

**AÇÃO:** Substituir código do endpoint `/monitoring/data` no Dia 5.

---

## 🔧 SEÇÃO 3: Endpoint /monitoring/metrics - CÓDIGO NOVO

### 📝 Arquivo: `backend/api/monitoring_unified.py` (ADICIONAR)

**Implementar SEGUNDO endpoint para métricas Prometheus:**

```python
@router.get("/metrics")
async def get_monitoring_metrics(
    category: str = Query(..., description="Categoria: network-probes, web-probes, etc"),
    server: Optional[str] = Query(None, description="Servidor Prometheus (ex: 172.16.1.26:9090)"),
    time_range: str = Query("5m", description="Intervalo de tempo (ex: 5m, 1h, 3h)"),
    metric_type: str = Query("status", description="Tipo de métrica: status, latency, cpu, memory"),
    company: Optional[str] = Query(None),
    site: Optional[str] = Query(None)
):
    """
    Endpoint para buscar MÉTRICAS do Prometheus via PromQL
    
    IMPORTANTE: Este endpoint executa queries PromQL e retorna métricas atuais/históricas,
    diferente de /monitoring/data que busca serviços cadastrados no Consul.
    
    Funcionamento:
    1. Busca tipos da categoria do cache
    2. Constrói query PromQL apropriada (usando DynamicQueryBuilder)
    3. Executa query no Prometheus
    4. Processa e retorna resultados
    
    Quando usar:
    - Para dashboards com gráficos de métricas
    - Para alertas baseados em thresholds
    - Para análise de performance/latência
    - Para histórico de disponibilidade
    
    Args:
        category: Categoria de monitoramento
        server: Servidor Prometheus (opcional, usa primeiro disponível)
        time_range: Intervalo de tempo para queries range
        metric_type: Tipo de métrica a buscar
        company: Filtro de label company
        site: Filtro de label site
    
    Returns:
        {
            "success": true,
            "category": "network-probes",
            "metric_type": "status",
            "metrics": [
                {
                    "instance": "10.0.0.1",
                    "job": "blackbox",
                    "module": "icmp",
                    "status": 1,
                    "timestamp": 1699876543,
                    "labels": {
                        "company": "Empresa Ramada",
                        "site": "palmas"
                    }
                }
            ],
            "query": "probe_success{job='blackbox',__param_module=~'icmp|tcp'}",
            "prometheus_server": "172.16.1.26:9090",
            "time_range": "5m",
            "total": 45
        }
    
    Example:
        GET /api/v1/monitoring/metrics?category=network-probes&metric_type=latency&time_range=1h
    """
    try:
        import httpx
        from core.dynamic_query_builder import DynamicQueryBuilder, QUERY_TEMPLATES
        from core.consul_kv_config_manager import ConsulKVConfigManager
        
        logger.info(f"[MONITORING METRICS] category={category}, metric_type={metric_type}")
        
        config_manager = ConsulKVConfigManager()
        query_builder = DynamicQueryBuilder()
        
        # STEP 1: Determinar servidor Prometheus
        if not server:
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
                detail="Cache de tipos não disponível. Execute /monitoring/sync-cache."
            )
        
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
        
        # STEP 3: Construir query PromQL baseado na categoria e metric_type
        if category in ['network-probes', 'web-probes']:
            # Blackbox probes
            modules = [t['module'] for t in category_types if t.get('module')]
            
            if metric_type == 'status':
                template = QUERY_TEMPLATES['network_probe_success']
            elif metric_type == 'latency':
                template = QUERY_TEMPLATES['network_probe_duration']
            else:
                raise HTTPException(
                    status_code=400,
                    detail=f"metric_type '{metric_type}' não suportado para {category}"
                )
            
            query = query_builder.build(template, {
                'modules': modules,
                'company': company,
                'site': site
            })
        
        elif category == 'system-exporters':
            jobs = [t['job_name'] for t in category_types]
            
            if metric_type == 'cpu':
                template = QUERY_TEMPLATES['node_cpu_usage']
            elif metric_type == 'memory':
                template = QUERY_TEMPLATES['node_memory_usage']
            elif metric_type == 'status':
                query = f"up{{job=~\"{'|'.join(jobs)}\"}}"
                template = None
            else:
                raise HTTPException(
                    status_code=400,
                    detail=f"metric_type '{metric_type}' não suportado para {category}"
                )
            
            if template:
                query = query_builder.build(template, {
                    'jobs': jobs,
                    'time_range': time_range
                })
        
        else:
            # Outras categorias: query genérica
            jobs = [t['job_name'] for t in category_types]
            query = f"up{{job=~\"{'|'.join(jobs)}\"}}"
        
        logger.info(f"[MONITORING METRICS] Query: {query}")
        
        # STEP 4: Executar query no Prometheus
        prometheus_url = f"http://{server}:9090" if ':' not in server else f"http://{server}"
        
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
            timestamp = result['value'][0]
            
            formatted_metrics.append({
                'instance': metric.get('instance', ''),
                'job': metric.get('job', ''),
                'module': metric.get('__param_module', ''),
                'value': float(value),
                'timestamp': timestamp,
                'labels': {k: v for k, v in metric.items() if not k.startswith('__')}
            })
        
        return {
            "success": True,
            "category": category,
            "metric_type": metric_type,
            "metrics": formatted_metrics,
            "query": query,
            "prometheus_server": server,
            "time_range": time_range,
            "total": len(formatted_metrics)
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[MONITORING METRICS ERROR] {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
```

**LOCALIZAÇÃO NO PLANO ORIGINAL:** NOVO - Adicionar após endpoint `/data`

**AÇÃO:** Implementar no Dia 5, imediatamente após `/monitoring/data`.

---

## 🔧 SEÇÃO 4: DynamicMonitoringPage - CÓDIGO CORRETO

### 📝 Arquivo: `frontend/src/pages/DynamicMonitoringPage.tsx`

**Modificar requestHandler para usar consulAPI:**

```typescript
interface DynamicMonitoringPageProps {
  category: string;
  dataSource?: 'consul' | 'prometheus';  // Escolher fonte de dados
}

const DynamicMonitoringPage: React.FC<DynamicMonitoringPageProps> = ({ 
  category,
  dataSource = 'consul'  // Padrão: buscar serviços do Consul
}) => {
  const actionRef = useRef<ActionType | null>(null);
  
  // ... estados ...
  
  // ✅ USAR consulAPI, NÃO fetch direto
  const requestHandler = useCallback(async (params: any) => {
    try {
      // Chamar método do consulAPI
      const data = await consulAPI.getMonitoringData(category, dataSource, filters);
      
      return {
        data: data.data || data.metrics || [],
        success: true,
        total: data.total
      };
    } catch (error: any) {
      message.error(`Erro ao carregar dados: ${error.message || error}`);
      return {
        data: [],
        success: false,
        total: 0
      };
    }
  }, [category, filters, dataSource]);
  
  // ✅ Sincronizar cache usando consulAPI
  const handleSync = useCallback(async () => {
    setSyncLoading(true);
    try {
      const result = await consulAPI.syncMonitoringCache();
      message.success(result.message || 'Cache sincronizado com sucesso!');
      actionRef.current?.reload();
    } catch (error: any) {
      message.error(`Erro ao sincronizar: ${error.message || error}`);
    } finally {
      setSyncLoading(false);
    }
  }, []);
  
  // ... resto do componente igual ao plano original ...
};
```

**LOCALIZAÇÃO NO PLANO ORIGINAL:** Seção 5.2.1 - DynamicMonitoringPage

**AÇÃO:** Substituir `requestHandler` e `handleSync` no Dia 6.

---

## 🔧 SEÇÃO 5: consulAPI - Métodos Novos

### 📝 Arquivo: `frontend/src/services/api.ts`

**Adicionar métodos ao objeto consulAPI:**

```typescript
// frontend/src/services/api.ts

export const consulAPI = {
  // ... métodos existentes (getServicesList, getBlackboxTargets, etc) ...
  
  /**
   * ✅ NOVO: Buscar dados de monitoramento (Consul ou Prometheus)
   * 
   * @param category - Categoria: network-probes, web-probes, etc
   * @param source - Fonte: 'consul' (serviços) ou 'prometheus' (métricas)
   * @param filters - Filtros adicionais (company, site, env)
   */
  getMonitoringData: async (
    category: string,
    source: 'consul' | 'prometheus' = 'consul',
    filters?: Record<string, string | undefined>
  ): Promise<MonitoringDataResponse> => {
    const params = new URLSearchParams({ category });
    
    // Adicionar filtros (remover undefined)
    if (filters) {
      Object.entries(filters).forEach(([key, value]) => {
        if (value !== undefined && value !== '') {
          params.append(key, value);
        }
      });
    }
    
    // Escolher endpoint baseado na fonte
    const endpoint = source === 'consul'
      ? `/api/v1/monitoring/data?${params}`      // Serviços do Consul
      : `/api/v1/monitoring/metrics?${params}`;  // Métricas do Prometheus
    
    try {
      const response = await httpClient.get(endpoint, {
        timeout: 30000  // 30 segundos
      });
      
      return response.data;
    } catch (error) {
      console.error('[consulAPI.getMonitoringData] Erro:', error);
      throw error;
    }
  },
  
  /**
   * ✅ NOVO: Sincronizar cache de tipos de monitoramento
   * 
   * Força extração nova do Prometheus via SSH e atualiza KV.
   */
  syncMonitoringCache: async (): Promise<SyncCacheResponse> => {
    try {
      const response = await httpClient.post('/api/v1/monitoring/sync-cache', {}, {
        timeout: 60000  // 60 segundos (extração SSH pode demorar)
      });
      
      return response.data;
    } catch (error) {
      console.error('[consulAPI.syncMonitoringCache] Erro:', error);
      throw error;
    }
  },
};

// ✅ ADICIONAR interfaces TypeScript
interface MonitoringDataResponse {
  success: boolean;
  category: string;
  data?: any[];              // Para /monitoring/data (Consul)
  metrics?: any[];           // Para /monitoring/metrics (Prometheus)
  total: number;
  filters_applied?: Record<string, any>;
  available_modules?: string[];
  query?: string;            // Query PromQL (só para /metrics)
  prometheus_server?: string;
}

interface SyncCacheResponse {
  success: boolean;
  message: string;
  total_types?: number;
  total_servers?: number;
}
```

**LOCALIZAÇÃO NO PLANO ORIGINAL:** NOVO - Adicionar em services/api.ts

**AÇÃO:** Implementar no Dia 6, antes de criar DynamicMonitoringPage.

---

## 📊 RESUMO DE SUBSTITUIÇÕES

| Seção Original | Substituir Por | Quando |
|----------------|----------------|--------|
| 5.1 - MetadataFieldModel | Seção 1 deste guia | Dia 3 |
| 5.1.4 - Endpoint /monitoring/data | Seções 2 e 3 deste guia | Dia 5 |
| 5.2.1 - DynamicMonitoringPage (requestHandler) | Seção 4 deste guia | Dia 6 |
| services/api.ts (novo) | Seção 5 deste guia | Dia 6 |

---

## 🎯 CHECKLIST DE VALIDAÇÃO

Antes de mergir para produção:

- [ ] MetadataFieldModel tem 7 propriedades `show_in_*` (3 antigas + 4 novas)
- [ ] Endpoint `/monitoring/data` busca do Consul (não Prometheus)
- [ ] Endpoint `/monitoring/metrics` implementado (queries PromQL)
- [ ] DynamicMonitoringPage usa `consulAPI.getMonitoringData()`
- [ ] DynamicMonitoringPage usa `consulAPI.syncMonitoringCache()`
- [ ] consulAPI tem interfaces TypeScript para responses

---

**✅ GUIA VALIDADO E PRONTO PARA USO NA IMPLEMENTAÇÃO**

**Use este documento em conjunto com o plano original para implementação precisa!**
