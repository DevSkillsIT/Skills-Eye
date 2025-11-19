# 📋 PLANO DE REFATORAÇÃO SKILLS EYE - VERSÃO COMPLETA 2.0

**Data:** 13/11/2025  
**Versão:** 2.0 - Baseada no Projeto Real  
**Autor:** Análise Técnica Completa com Pesquisa Web  
**Status:** 🔴 DOCUMENTO DEFINITIVO PARA IMPLEMENTAÇÃO

---

## 📑 ÍNDICE

1. [SUMÁRIO EXECUTIVO](#sumário-executivo)
2. [ANÁLISE DO PROJETO ATUAL](#análise-do-projeto-atual)
3. [RECOMENDAÇÕES TÉCNICAS FUNDAMENTAIS](#recomendações-técnicas-fundamentais)
4. [ARQUITETURA PROPOSTA](#arquitetura-proposta)
5. [COMPONENTES A CRIAR](#componentes-a-criar)
6. [PLANO DE IMPLEMENTAÇÃO DETALHADO](#plano-de-implementação-detalhado)
7. [VALIDAÇÃO E TESTES](#validação-e-testes)
8. [DOCUMENTAÇÃO NECESSÁRIA](#documentação-necessária)

---

## 🎯 SUMÁRIO EXECUTIVO

### Situação Atual

O **Skills Eye** já possui **80% da arquitetura dinâmica necessária** funcionando corretamente:

✅ **Backend com extração dinâmica** via `monitoring_types_dynamic.py`  
✅ **Sistema de metadata fields dinâmicos** via `metadata_fields_manager.py`  
✅ **Páginas Services e BlackboxTargets** funcionais com ProTable  
✅ **Hooks reutilizáveis** `useMetadataFields`, `useReferenceValues`, `useServiceTags`  
✅ **Multi-servidor SSH** para extração de configurações Prometheus  
✅ **Sistema de cache** no Consul KV  

### O Que Precisa Ser Feito

**NÃO é uma refatoração completa** - é uma **EXPANSÃO** do sistema existente para criar 4 novas páginas de monitoramento e melhorar alguns componentes do backend:

1. **4 Páginas Frontend** → NetworkProbes, WebProbes, SystemExporters, DatabaseExporters
2. **Componente React Genérico** → `DynamicMonitoringPage.tsx` (reutilizável)
3. **Melhorias no Backend** → Cache KV dos tipos, categorization rules JSON, query builder
4. **Endpoints Dual** → `/api/v1/monitoring/data` (Consul) + `/api/v1/monitoring/metrics` (Prometheus)

### Objetivos SMART

- ✅ **S**pecífico: Criar 4 páginas de monitoramento 100% dinâmicas
- ✅ **M**ensurável: 0 hardcodes, 100% baseado em KV/Prometheus
- ✅ **A**tingível: Reaproveitar 80% do código existente
- ✅ **R**elevante: Facilitar gestão de diferentes tipos de monitoramento
- ✅ **T**emporal: 12-13 dias de implementação

---

## 🔍 ANÁLISE DO PROJETO ATUAL

### 2.1 Backend Python - O Que JÁ EXISTE

#### ✅ Arquivo: `monitoring_types_dynamic.py` (456 linhas)

**O que FAZ:**
- Extrai tipos de monitoramento **DINAMICAMENTE** do `prometheus.yml`
- Categoriza automaticamente em 8 categorias pré-definidas
- Funciona com múltiplos servidores Prometheus via SSH
- Infere categoria baseado em job_name e metrics_path

**Endpoint disponível:**
```python
GET /api/v1/monitoring-types-dynamic/from-prometheus?server=ALL
```

**Resposta atual:**
```json
{
  "success": true,
  "servers": {
    "172.16.1.26": {
      "types": [
        {
          "id": "icmp",
          "display_name": "ICMP (Ping)",
          "category": "network-probes",
          "job_name": "icmp",
          "exporter_type": "blackbox",
          "module": "icmp",
          "fields": ["company", "project", "env", "name", "instance"],
          "metrics_path": "/probe",
          "server": "172.16.1.26"
        }
      ],
      "total": 15
    }
  },
  "categories": [
    {
      "category": "network-probes",
      "display_name": "Network Probes (Rede)",
      "types": [...]
    }
  ],
  "all_types": [...],
  "total_types": 15
}
```

**Categorias suportadas:**
1. `network-probes` → ICMP, TCP, DNS, SSH
2. `web-probes` → HTTP 2xx, HTTP 4xx, HTTPS, POST
3. `system-exporters` → Node, Windows, SNMP
4. `database-exporters` → MySQL, PostgreSQL, Redis, MongoDB
5. `infrastructure-exporters` → HAProxy, Nginx, Kafka, RabbitMQ
6. `hardware-exporters` → IPMI, Dell HW
7. `network-devices` → MikroTik (MKTXP)
8. `custom-exporters` → Qualquer outro job

**Função de inferência:**
```python
def _infer_category_and_type(job_name: str, job_config: Dict) -> tuple:
    """
    Infere categoria baseado em:
    1. Nome do job (blackbox, node, mysql, etc)
    2. metrics_path (/probe = blackbox, /metrics = exporter)
    3. Padrões conhecidos (haproxy, nginx, kafka, etc)
    """
    job_lower = job_name.lower()
    metrics_path = job_config.get('metrics_path', '/metrics')
    
    # Blackbox detection
    is_blackbox = (
        'blackbox' in job_lower or
        metrics_path == '/probe' or
        job_lower in ['http_2xx', 'icmp', 'tcp_connect', ...]
    )
    
    if is_blackbox:
        module = _extract_blackbox_module(job_config)
        if module in ['icmp', 'tcp', 'dns', 'ssh']:
            return 'network-probes', {...}
        else:
            return 'web-probes', {...}
    
    # Node Exporter
    if 'node' in job_lower or 'selfnode' in job_lower:
        return 'system-exporters', {...}
    
    # ... (continua para outros exporters)
```

**✅ PONTO CRÍTICO:** Este código **JÁ FAZ 90%** do que o documento original propunha! Não precisa ser reescrito, apenas **MELHORADO** e **PERSISTIDO NO KV**.

---

#### ✅ Arquivo: `metadata_fields_manager.py` (122 linhas)

**O que FAZ:**
- Extrai campos metadata dos `relabel_configs` do Prometheus
- Salva no Consul KV: `skills/eye/metadata/fields`
- Sistema de cache com TTL de 5 minutos
- Suporta múltiplos servidores com SSH + TAR (ultra-rápido)

**Endpoint disponível:**
```python
GET /api/v1/metadata-fields/sync-status?server_id=172.16.1.26:5522
```

**⚠️ IMPORTANTE:** O modelo `MetadataFieldModel` **JÁ TEM** 3 propriedades `show_in_*`:
```python
class MetadataFieldModel(BaseModel):
    # ... campos existentes ...
    
    # ✅ JÁ EXISTEM (linhas 72-74):
    show_in_services: bool = Field(True, description="Mostrar na página Services")
    show_in_exporters: bool = Field(True, description="Mostrar na página Exporters")
    show_in_blackbox: bool = Field(True, description="Mostrar na página Blackbox")
```

**🔧 AÇÃO NECESSÁRIA:** Adicionar **4 NOVAS** propriedades (Dia 3):
```python
    # ⭐ ADICIONAR estas 4 novas:
    show_in_network_probes: bool = Field(True, description="Mostrar na página Network Probes")
    show_in_web_probes: bool = Field(True, description="Mostrar na página Web Probes")
    show_in_system_exporters: bool = Field(True, description="Mostrar na página System Exporters")
    show_in_database_exporters: bool = Field(True, description="Mostrar na página Database Exporters")
```

**Estrutura KV atual:**
```json
{
  "version": "2.0.0",
  "last_updated": "2025-11-13T10:30:00",
  "total_fields": 22,
  "fields": [
    {
      "name": "company",
      "display_name": "Empresa",
      "category": "business",
      "field_type": "string",
      "show_in_services": true,
      "show_in_blackbox": true,
      "show_in_table": true,
      "show_in_filter": true,
      "required": true
    }
  ]
}
```

**✅ PONTO CRÍTICO:** Sistema de metadata fields **JÁ É DINÂMICO** e funciona perfeitamente!

---

#### ✅ Arquivo: `consul_manager.py` (1034 linhas)

**O que FAZ:**
- Cliente async do Consul via httpx (não usa biblioteca python-consul)
- Gerencia Services, KV, Nodes, Health Checks
- Sistema de retry com backoff exponencial
- Validação de dados com Pydantic

**Métodos principais:**
```python
class ConsulManager:
    async def get_json(self, key: str) -> Optional[Dict]
    async def put_json(self, key: str, value: Dict) -> bool
    async def get_services_list(self) -> List[Dict]
    async def register_service(self, payload: ServiceCreatePayload) -> bool
```

**✅ PONTO CRÍTICO:** Já usa **API REST direta** com httpx async - **NÃO PRECISA migrar** para biblioteca python-consul!

---

### 2.2 Frontend React - O Que JÁ EXISTE

#### ✅ Arquivo: `Services.tsx` (1552 linhas)

**⚠️ IMPORTANTE:** Services.tsx e BlackboxTargets.tsx são **APENAS REFERÊNCIA** - novas páginas usarão lógica diferente!

**O que FAZ:**
- Lista todos os serviços Consul com metadata dinâmicos
- Usa `useTableFields('services')` para colunas dinâmicas
- Usa `useFormFields('services')` para formulário dinâmico
- Usa `useFilterFields('services')` para filtros dinâmicos
- Sistema de auto-cadastro com `useBatchEnsure` e `useServiceTags`

**Hooks utilizados:**
```typescript
const { tableFields } = useTableFields('services');  // 22 campos dinâmicos
const { formFields } = useFormFields('services');    // Formulário adaptável
const { filterFields } = useFilterFields('services'); // Filtros adaptáveis
```

**Estrutura de colunas dinâmicas:**
```typescript
const defaultColumnConfig = useMemo<ColumnConfig[]>(() => {
  // Combina colunas fixas + campos metadata dinâmicos
  const metadataColumns: ColumnConfig[] = tableFields.map((field) => ({
    key: field.name,
    title: field.display_name,
    visible: field.show_in_table ?? true
  }));
  
  return [
    ...FIXED_COLUMNS,      // node, service, id, address, port, tags, actions
    ...metadataColumns     // company, project, env, name, instance, etc
  ];
}, [tableFields]);
```

**✅ PONTO CRÍTICO:** Services.tsx **JÁ É UM MODELO PERFEITO** de como fazer página dinâmica! As 4 novas páginas devem seguir este padrão.

---

#### ✅ Arquivo: `BlackboxTargets.tsx` (1330 linhas)

**O que FAZ:**
- Lista targets do Blackbox Exporter com metadata dinâmicos
- Mesma estrutura de hooks que Services.tsx
- ProTable com colunas configuráveis via ColumnSelector
- Filtros avançados com AdvancedSearchPanel

**✅ PONTO CRÍTICO:** BlackboxTargets.tsx é praticamente **IDENTICAL** ao Services.tsx em estrutura - confirma que o padrão funciona bem!

---

#### ✅ Arquivo: `useMetadataFields.ts` (478 linhas)

**O que FAZ:**
- Hook customizado que busca campos metadata do backend
- Cache global de 5 minutos para evitar requests repetidos
- Filtra campos baseado em contexto (`services`, `blackbox`, etc)

**Implementação atual:**
```typescript
export function useTableFields(context: 'services' | 'blackbox') {
  const [fields, setFields] = useState<MetadataField[]>([]);
  const [loading, setLoading] = useState(true);
  
  useEffect(() => {
    async function loadFields() {
      const response = await fetch('/api/v1/metadata-fields/fields');
      const data = await response.json();
      
      // Filtrar campos baseado no contexto
      const filtered = data.fields.filter((field) => {
        if (context === 'services') {
          return field.show_in_services !== false;
        } else if (context === 'blackbox') {
          return field.show_in_blackbox !== false;
        }
        return true;
      });
      
      setFields(filtered);
      setLoading(false);
    }
    
    loadFields();
  }, [context]);
  
  return { tableFields: fields, loading };
}
```

**✅ PONTO CRÍTICO:** Hook **JÁ ACEITA CONTEXTO** mas só suporta 'services' e 'blackbox'. Precisa aceitar contextos dinâmicos como 'network-probes', 'web-probes', etc.

---

### 2.3 Multi-Config Manager (SSH + YAML Parsing)

#### ✅ Arquivo: `multi_config_manager.py` (2034 linhas)

**O que FAZ:**
- Conecta via SSH em múltiplos servidores Prometheus
- Lê e escreve arquivos YAML preservando comentários (ruamel.yaml)
- Extração ultra-rápida com AsyncSSH + TAR (2-3 segundos)
- Validação com promtool antes de aplicar mudanças

**Método crítico:**
```python
async def extract_all_fields_with_asyncssh_tar(self) -> Dict:
    """
    Extrai campos de TODOS os servidores Prometheus via AsyncSSH + TAR
    
    Performance:
    - Método antigo (SSH sequencial): 20-30 segundos
    - Método atual (AsyncSSH + TAR): 2-3 segundos
    
    Returns:
        {
            'fields': [MetadataField(...), ...],
            'total_fields': 22,
            'successful_servers': 3,
            'total_servers': 3
        }
    """
```

**✅ PONTO CRÍTICO:** Sistema de extração **JÁ É ALTAMENTE OTIMIZADO** e funciona perfeitamente!

---

## 🔬 RECOMENDAÇÕES TÉCNICAS FUNDAMENTAIS

### 3.1 Biblioteca python-consul vs. API REST Direta

**RECOMENDAÇÃO: MANTER API REST DIRETA (httpx)**

#### Análise da Situação

**Biblioteca python-consul:**
- ❌ **Abandonada desde 2018** - última atualização oficial
- ❌ **Forks fragmentados** - py-consul (Criteo), python-consul2, consulate
- ❌ **Suporte incompleto** - não expõe todas as APIs do Consul 1.15+
- ❌ **Dependência adicional** - aumenta surface de bugs
- ✅ Abstração mais limpa (sintaxe simplificada)

**API REST direta (httpx):**
- ✅ **Sempre atualizada** - segue API oficial do Consul
- ✅ **Controle total** - acesso a TODAS as features
- ✅ **Performance** - httpx async é extremamente rápido
- ✅ **JÁ IMPLEMENTADO** - consul_manager.py usa httpx
- ✅ **Menor dependência** - menos bibliotecas terceiras
- ❌ Código mais verboso (mais linhas)

#### Pesquisa Web - Estado Atual (2025)

Segundo documentação oficial do HashiCorp (Libraries and SDKs - HTTP API):
- Python não tem biblioteca **OFICIALMENTE mantida** pela HashiCorp
- Bibliotecas da comunidade estão **fragmentadas e desatualizadas**
- Recomendação oficial: **usar HTTP API diretamente**

#### Conclusão

**✅ MANTER httpx com API REST direta**

Justificativa:
1. Sistema atual **JÁ FUNCIONA PERFEITAMENTE** com httpx
2. Migrar para biblioteca abandonada é **PIOR** que o atual
3. Controle total sobre requisições e respostas
4. Performance excelente com async/await

**Ação: NENHUMA** - não migrar para python-consul

---

### 3.2 Validação: Sistema Dinâmico Suporta TODOS os Exporters?

**RESPOSTA: SIM, COM RESSALVAS**

#### Análise Baseada em Pesquisa Web

Segundo documentação oficial do Prometheus, existem **100+ exporters** oficiais e da comunidade:

**Exporters Oficiais (mantidos pela Prometheus GitHub org):**
- node_exporter (Linux/Unix)
- blackbox_exporter (probes)
- mysqld_exporter
- postgres_exporter
- redis_exporter
- haproxy_exporter
- memcached_exporter
- consul_exporter
- jmx_exporter
- snmp_exporter

**Exporters Populares da Comunidade:**
- windows_exporter (WMI)
- mongodb_exporter
- elasticsearch_exporter
- kafka_exporter
- nginx_exporter
- rabbitmq_exporter
- mktxp (MikroTik)
- ipmi_exporter

#### Como o Sistema Atual Trata Exporters

O `monitoring_types_dynamic.py` categoriza exporters baseado em:

1. **Job name pattern matching** - detecta palavras-chave (mysql, node, blackbox, etc)
2. **metrics_path** - `/probe` = blackbox, `/metrics` = exporter
3. **Lista de padrões conhecidos** - 40+ padrões hardcoded

```python
exporter_patterns = {
    'haproxy': ('infrastructure-exporters', 'HAProxy Exporter', 'haproxy_exporter'),
    'nginx': ('infrastructure-exporters', 'Nginx Exporter', 'nginx_exporter'),
    'kafka': ('infrastructure-exporters', 'Kafka Exporter', 'kafka_exporter'),
    # ... 40+ padrões
}
```

**Problema:** Novos exporters **NÃO CONHECIDOS** caem em `custom-exporters`

#### Solução Proposta

**Sistema deve ser AGNÓSTICO ao tipo de exporter:**

1. **Regras de categorização no KV** (não hardcoded)
2. **Sistema de "plugin"** onde novos exporters podem ser adicionados via JSON
3. **Fallback inteligente** - se não conhece, usa custom-exporters

**✅ CONCLUSÃO:** Sistema atual **FUNCIONA** mas pode ser **MELHORADO** com regras JSON no KV.

---

### 3.3 Cache KV dos Tipos de Monitoramento

**RECOMENDAÇÃO: IMPLEMENTAR CACHE KV COM TTL**

#### Situação Atual

O `monitoring_types_dynamic.py` **NÃO salva** no KV - extrai sempre do Prometheus via SSH.

**Problema:**
- Cada request faz SSH para servidores Prometheus
- Lento (2-3 segundos por request)
- Sobrecarga desnecessária

**Solução:**

1. **Primeira extração** - salva resultado no KV
2. **Requests subsequentes** - lê do KV (< 100ms)
3. **TTL de 5 minutos** - revalida periodicamente
4. **Botão "Sincronizar"** - força extração nova

**Estrutura KV proposta:**
```
skills/eye/monitoring-types/cache.json
```

```json
{
  "version": "1.0.0",
  "last_updated": "2025-11-13T10:30:00",
  "ttl_seconds": 300,
  "servers": {
    "172.16.1.26": {
      "types": [...],
      "total": 15
    }
  },
  "categories": [...],
  "all_types": [...]
}
```

**Implementação:**

```python
async def get_monitoring_types_cached(server: Optional[str] = None):
    """
    Busca tipos de monitoramento com cache KV
    
    Fluxo:
    1. Tenta ler do KV
    2. Se cache válido (< 5 min), retorna
    3. Se cache expirado ou não existe, extrai do Prometheus
    4. Salva no KV e retorna
    """
    cache_key = 'skills/eye/monitoring-types/cache.json'
    
    # STEP 1: Tentar ler do cache
    cached = await kv_manager.get_json(cache_key)
    
    if cached:
        last_updated = datetime.fromisoformat(cached['last_updated'])
        age_seconds = (datetime.now() - last_updated).total_seconds()
        
        if age_seconds < cached.get('ttl_seconds', 300):
            logger.info(f"[CACHE HIT] Usando tipos em cache (age={age_seconds}s)")
            return cached
    
    # STEP 2: Cache miss ou expirado - extrair do Prometheus
    logger.info("[CACHE MISS] Extraindo tipos do Prometheus via SSH...")
    result = await extract_types_from_all_servers(server)
    
    # STEP 3: Salvar no KV
    cache_data = {
        "version": "1.0.0",
        "last_updated": datetime.now().isoformat(),
        "ttl_seconds": 300,
        **result
    }
    
    await kv_manager.put_json(cache_key, cache_data)
    logger.info("[CACHE WRITE] Tipos salvos no KV")
    
    return cache_data
```

**✅ AÇÃO: IMPLEMENTAR** este cache no `monitoring_types_dynamic.py`

---

### 3.4 Hooks: Genérico vs. Contextos Específicos?

**RECOMENDAÇÃO: HOOK GENÉRICO COM CONTEXTO DINÂMICO**

#### Análise das Opções

**Opção A: Contextos específicos hardcoded**
```typescript
useTableFields('services')
useTableFields('blackbox')
useTableFields('network-probes')  // NOVO
useTableFields('web-probes')      // NOVO
useTableFields('system-exporters')  // NOVO
useTableFields('database-exporters')  // NOVO
```

❌ Problema: Adicionar novo tipo requer mudança no código

**Opção B: Hook genérico que aceita QUALQUER contexto**
```typescript
useTableFields(context: string)  // Aceita QUALQUER string
```

✅ Vantagem: 100% dinâmico, funciona com qualquer categoria

#### Implementação Proposta

**Hook deve:**
1. Aceitar contexto como string genérica
2. Buscar campos do backend
3. Filtrar baseado em convenção: `show_in_{context}`

```typescript
export function useTableFields(context: string) {
  const [fields, setFields] = useState<MetadataField[]>([]);
  const [loading, setLoading] = useState(true);
  
  useEffect(() => {
    async function loadFields() {
      // Buscar campos do backend
      const response = await fetch('/api/v1/metadata-fields/fields');
      const data = await response.json();
      
      // Filtrar baseado em show_in_{context}
      const showInKey = `show_in_${context.replace(/-/g, '_')}`;
      
      const filtered = data.fields.filter((field) => {
        // Se campo não tem a propriedade show_in_{context}, exibe por padrão
        if (!(showInKey in field)) {
          return true;
        }
        return field[showInKey] !== false;
      });
      
      setFields(filtered);
      setLoading(false);
    }
    
    loadFields();
  }, [context]);
  
  return { tableFields: fields, loading };
}
```

**Uso:**
```typescript
// Páginas existentes (mantém compatibilidade)
useTableFields('services')
useTableFields('blackbox')

// Novas páginas (funciona automaticamente)
useTableFields('network-probes')
useTableFields('web-probes')
useTableFields('system-exporters')
useTableFields('database-exporters')

// Futuras categorias (sem código adicional)
useTableFields('custom-exporters')
useTableFields('hardware-exporters')
```

**✅ AÇÃO: IMPLEMENTAR** hook genérico conforme especificação acima

---

## 🏗️ ARQUITETURA PROPOSTA

### 4.1 Diagrama Geral do Sistema

```
┌─────────────────────────────────────────────────────────────────┐
│                    CONSUL KV STORE                               │
│                                                                  │
│  skills/eye/                                                     │
│  ├── monitoring-types/                                           │
│  │   ├── cache.json              ← NOVO: Cache dos tipos        │
│  │   └── categorization/                                         │
│  │       └── rules.json          ← NOVO: Regras JSON            │
│  ├── metadata/                                                   │
│  │   └── fields                  ← JÁ EXISTE: 22 campos         │
│  └── reference-values/            ← JÁ EXISTE: Auto-cadastro    │
└─────────────────────────────────────────────────────────────────┘
                            ↓
                            ↓ (httpx async)
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│              BACKEND PYTHON (FastAPI)                            │
│                                                                  │
│  ┌──────────────────────┐  ┌────────────────────────┐          │
│  │ ConsulKVConfig       │  │ MonitoringTypes        │          │
│  │ Manager (NOVO)       │→ │ Dynamic (MELHORADO)    │          │
│  └──────────────────────┘  └────────────────────────┘          │
│                                                                  │
│  ┌──────────────────────┐  ┌────────────────────────┐          │
│  │ Categorization       │  │ DynamicQuery           │          │
│  │ RuleEngine (NOVO)    │  │ Builder (NOVO)         │          │
│  └──────────────────────┘  └────────────────────────┘          │
│                                                                  │
│  API Endpoints:                                                  │
│  - GET /api/v1/monitoring-types-dynamic/from-prometheus         │
│  - GET /api/v1/monitoring/data?category=network-probes (NOVO)   │
│  - POST /api/v1/monitoring-types-dynamic/sync-cache (NOVO)      │
└─────────────────────────────────────────────────────────────────┘
                            ↓
                            ↓ (JSON)
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│              FRONTEND REACT (Ant Design Pro)                     │
│                                                                  │
│  ┌──────────────────────────────────────────┐                  │
│  │     DynamicMonitoringPage (NOVO)         │                  │
│  │     (Componente Base Único)              │                  │
│  └──────────────────────────────────────────┘                  │
│                                                                  │
│  Páginas Geradas Automaticamente:                               │
│  - /monitoring/network-probes    (NOVA)                         │
│  - /monitoring/web-probes        (NOVA)                         │
│  - /monitoring/system-exporters  (NOVA)                         │
│  - /monitoring/database-exporters (NOVA)                        │
│                                                                  │
│  - /services                     (EXISTENTE - backup)           │
│  - /blackbox-targets             (EXISTENTE - backup)           │
│                                                                  │
│  Features:                                                       │
│  - Colunas 100% dinâmicas via useMetadataFields(context)        │
│  - Filtros 100% dinâmicos via useFilterFields(context)          │
│  - Formulários 100% dinâmicos via useFormFields(context)        │
└─────────────────────────────────────────────────────────────────┘
                            ↓
                            ↓ (PromQL)
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│                    PROMETHEUS SERVERS                            │
│                                                                  │
│  - Palmas: 172.16.1.26:9090                                     │
│  - Rio: 172.16.200.14:9090                                      │
│  - DTC: 11.144.0.21:9090                                        │
└─────────────────────────────────────────────────────────────────┘
```

---

### 4.2 Fluxo de Dados Completo

#### Fluxo 1: Extração de Tipos (Backend Startup)

```
1. Backend inicia → app.py
2. Lifespan startup hook executa
3. Chama _prewarm_metadata_fields_cache()
4. Multi-config manager extrai prometheus.yml via SSH
5. monitoring_types_dynamic.extract_types_from_prometheus_jobs()
6. Categoriza cada job usando _infer_category_and_type()
7. Salva resultado no KV: skills/eye/monitoring-types/cache.json
8. Cache válido por 5 minutos
```

#### Fluxo 2: Requisição de Página (Frontend)

```
1. Usuário acessa /monitoring/network-probes
2. React Router renderiza <DynamicMonitoringPage category="network-probes" />
3. Component chama useTableFields('network-probes')
4. Hook busca: GET /api/v1/metadata-fields/fields
5. Filtra campos onde show_in_network_probes !== false
6. Component chama: GET /api/v1/monitoring/data?category=network-probes
7. Backend lê cache KV de tipos
8. Filtra apenas tipos da categoria network-probes
9. Para cada tipo, executa query PromQL no Prometheus
10. Retorna dados agregados para o frontend
11. ProTable renderiza colunas dinamicamente
```

#### Fluxo 3: Sincronização Manual (Botão no Frontend)

```
1. Usuário clica "Sincronizar Tipos"
2. Frontend chama: POST /api/v1/monitoring-types-dynamic/sync-cache
3. Backend força extração nova do Prometheus via SSH
4. Invalida cache existente
5. Salva novos tipos no KV
6. Retorna status de sucesso
7. Frontend recarrega dados
```

---

## 📦 COMPONENTES A CRIAR

### 5.1 Backend Python

#### 5.1.1 ConsulKVConfigManager (NOVO)

**Arquivo:** `backend/core/consul_kv_config_manager.py`

**Propósito:** Gerenciador centralizado de configurações no KV com cache inteligente

**Funcionalidades:**
- Cache em memória com TTL configurável
- Métodos get/put/delete com validação Pydantic
- Namespace automático para keys (skills/eye/)
- Invalidação de cache seletiva

**Implementação completa:**

```python
"""
Consul KV Config Manager - Gerenciador Central de Configurações

RESPONSABILIDADES:
- Centralizar acesso ao Consul KV
- Cache inteligente com TTL
- Validação de dados com Pydantic
- Namespace automático (skills/eye/)
"""

from typing import Optional, Dict, Any, TypeVar, Type
from datetime import datetime, timedelta
from pydantic import BaseModel
import logging
import json

from core.kv_manager import KVManager

logger = logging.getLogger(__name__)

T = TypeVar('T', bound=BaseModel)


class CachedValue:
    """Valor com timestamp para cache"""
    def __init__(self, value: Any, ttl_seconds: int):
        self.value = value
        self.timestamp = datetime.now()
        self.ttl_seconds = ttl_seconds
    
    def is_expired(self) -> bool:
        age = datetime.now() - self.timestamp
        return age.total_seconds() > self.ttl_seconds


class ConsulKVConfigManager:
    """
    Gerenciador centralizado de configurações no Consul KV
    
    Features:
    - Cache em memória com TTL configurável
    - Validação automática com Pydantic
    - Namespace automático
    - Invalidação de cache seletiva
    
    Exemplo:
        manager = ConsulKVConfigManager(ttl=300)  # 5 minutos
        
        # Salvar config
        await manager.put('monitoring-types/cache', types_data)
        
        # Ler config com cache
        data = await manager.get('monitoring-types/cache')
        
        # Invalidar cache
        manager.invalidate('monitoring-types/cache')
    """
    
    def __init__(self, prefix: str = "skills/eye/", ttl_seconds: int = 300):
        self.prefix = prefix
        self.ttl_seconds = ttl_seconds
        self.kv_manager = KVManager()
        self._cache: Dict[str, CachedValue] = {}
    
    def _full_key(self, key: str) -> str:
        """Adiciona namespace ao key"""
        return f"{self.prefix}{key}"
    
    async def get(
        self, 
        key: str, 
        model: Optional[Type[T]] = None,
        use_cache: bool = True
    ) -> Optional[Any]:
        """
        Busca valor do KV com cache
        
        Args:
            key: Chave (sem namespace)
            model: Modelo Pydantic para validação (opcional)
            use_cache: Se deve usar cache
        
        Returns:
            Valor parseado ou None se não encontrado
        """
        full_key = self._full_key(key)
        
        # Tentar cache primeiro
        if use_cache and full_key in self._cache:
            cached = self._cache[full_key]
            if not cached.is_expired():
                logger.debug(f"[CACHE HIT] {key}")
                return cached.value
            else:
                logger.debug(f"[CACHE EXPIRED] {key}")
                del self._cache[full_key]
        
        # Cache miss - buscar do Consul
        logger.debug(f"[CACHE MISS] {key}")
        value = await self.kv_manager.get_json(full_key)
        
        if value is None:
            return None
        
        # Validar com Pydantic se model fornecido
        if model:
            try:
                value = model(**value)
            except Exception as e:
                logger.error(f"[VALIDATION ERROR] {key}: {e}")
                return None
        
        # Salvar no cache
        if use_cache:
            self._cache[full_key] = CachedValue(value, self.ttl_seconds)
        
        return value
    
    async def put(
        self, 
        key: str, 
        value: Any,
        invalidate_cache: bool = True
    ) -> bool:
        """
        Salva valor no KV
        
        Args:
            key: Chave (sem namespace)
            value: Valor (dict, list ou Pydantic model)
            invalidate_cache: Se deve invalidar cache
        
        Returns:
            True se salvou com sucesso
        """
        full_key = self._full_key(key)
        
        # Converter Pydantic model para dict
        if isinstance(value, BaseModel):
            value = value.dict()
        
        # Salvar no Consul
        success = await self.kv_manager.put_json(full_key, value)
        
        if success and invalidate_cache:
            self.invalidate(key)
        
        return success
    
    async def delete(self, key: str) -> bool:
        """Remove key do KV e invalida cache"""
        full_key = self._full_key(key)
        
        success = await self.kv_manager.delete(full_key)
        
        if success:
            self.invalidate(key)
        
        return success
    
    def invalidate(self, key: str) -> None:
        """Invalida cache de um key específico"""
        full_key = self._full_key(key)
        if full_key in self._cache:
            del self._cache[full_key]
            logger.debug(f"[CACHE INVALIDATED] {key}")
    
    def invalidate_all(self) -> None:
        """Invalida todo o cache"""
        self._cache.clear()
        logger.info("[CACHE] Todos os itens invalidados")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Retorna estatísticas do cache"""
        total_items = len(self._cache)
        expired_items = sum(1 for v in self._cache.values() if v.is_expired())
        
        return {
            "total_items": total_items,
            "active_items": total_items - expired_items,
            "expired_items": expired_items,
            "ttl_seconds": self.ttl_seconds
        }
```

**Uso no código:**

```python
# Criar instância global
config_manager = ConsulKVConfigManager(ttl=300)

# Usar nos endpoints
@router.get("/monitoring-types-dynamic/from-prometheus")
async def get_types():
    # Buscar do cache/KV
    cached = await config_manager.get('monitoring-types/cache')
    
    if cached:
        return cached
    
    # Extrair do Prometheus
    types = await extract_from_prometheus()
    
    # Salvar no KV
    await config_manager.put('monitoring-types/cache', types)
    
    return types
```

---

#### 5.1.2 CategorizationRuleEngine (NOVO)

**Arquivo:** `backend/core/categorization_rule_engine.py`

**Propósito:** Motor de regras para categorização automática baseado em JSON

**JSON de regras (KV):**

```json
{
  "version": "1.0.0",
  "rules": [
    {
      "id": "blackbox_icmp",
      "priority": 100,
      "category": "network-probes",
      "conditions": {
        "job_name_pattern": "^(icmp|ping).*",
        "metrics_path": "/probe",
        "module_pattern": "^(icmp|ping)$"
      }
    },
    {
      "id": "blackbox_tcp",
      "priority": 100,
      "category": "network-probes",
      "conditions": {
        "job_name_pattern": "^tcp.*",
        "metrics_path": "/probe",
        "module_pattern": "^tcp.*"
      }
    },
    {
      "id": "blackbox_http",
      "priority": 100,
      "category": "web-probes",
      "conditions": {
        "job_name_pattern": "^http.*",
        "metrics_path": "/probe"
      }
    },
    {
      "id": "node_exporter",
      "priority": 90,
      "category": "system-exporters",
      "conditions": {
        "job_name_pattern": "^(node|selfnode).*",
        "metrics_path": "/metrics"
      }
    },
    {
      "id": "mysql_exporter",
      "priority": 80,
      "category": "database-exporters",
      "conditions": {
        "job_name_pattern": "^mysql.*"
      }
    }
  ],
  "default_category": "custom-exporters"
}
```

**Implementação:**

```python
"""
Categorization Rule Engine - Motor de Regras Baseado em JSON

RESPONSABILIDADES:
- Carregar regras do Consul KV
- Aplicar regras em ordem de prioridade
- Categorizar jobs automaticamente
"""

import re
from typing import Dict, List, Optional, Any
import logging

logger = logging.getLogger(__name__)


class CategorizationRule:
    """Uma regra de categorização"""
    def __init__(self, rule_data: Dict):
        self.id = rule_data['id']
        self.priority = rule_data.get('priority', 50)
        self.category = rule_data['category']
        self.conditions = rule_data['conditions']
        
        # Pre-compilar regexes
        self._compiled_patterns = {}
        for key, pattern in self.conditions.items():
            if key.endswith('_pattern'):
                try:
                    self._compiled_patterns[key] = re.compile(pattern, re.IGNORECASE)
                except re.error as e:
                    logger.error(f"[RULE {self.id}] Regex inválida em {key}: {e}")
    
    def matches(self, job_data: Dict) -> bool:
        """Verifica se job satisfaz todas as condições (AND)"""
        job_name = job_data.get('job_name', '').lower()
        metrics_path = job_data.get('metrics_path', '/metrics')
        module = job_data.get('module', '')
        
        # Verificar job_name_pattern
        if 'job_name_pattern' in self.conditions:
            pattern = self._compiled_patterns.get('job_name_pattern')
            if pattern and not pattern.match(job_name):
                return False
        
        # Verificar metrics_path
        if 'metrics_path' in self.conditions:
            if metrics_path != self.conditions['metrics_path']:
                return False
        
        # Verificar module_pattern
        if 'module_pattern' in self.conditions:
            pattern = self._compiled_patterns.get('module_pattern')
            if pattern and not pattern.match(module):
                return False
        
        # Todas as condições satisfeitas
        return True


class CategorizationRuleEngine:
    """
    Motor de regras para categorização de jobs Prometheus
    
    Features:
    - Carrega regras do Consul KV
    - Aplica regras em ordem de prioridade (maior primeiro)
    - Suporta regex patterns
    - Categoria padrão para jobs não categorizados
    
    Exemplo:
        engine = CategorizationRuleEngine()
        await engine.load_rules()
        
        category = engine.categorize({
            'job_name': 'icmp',
            'metrics_path': '/probe',
            'module': 'icmp'
        })
        # Returns: 'network-probes'
    """
    
    def __init__(self, config_manager):
        self.config_manager = config_manager
        self.rules: List[CategorizationRule] = []
        self.default_category = 'custom-exporters'
    
    async def load_rules(self) -> bool:
        """
        Carrega regras do Consul KV
        
        Returns:
            True se carregou com sucesso
        """
        try:
            rules_data = await self.config_manager.get('monitoring-types/categorization/rules')
            
            if not rules_data:
                logger.warning("[RULES] Nenhuma regra encontrada no KV, usando fallback")
                return False
            
            # Criar objetos de regra
            self.rules = []
            for rule_data in rules_data.get('rules', []):
                rule = CategorizationRule(rule_data)
                self.rules.append(rule)
            
            # Ordenar por prioridade (maior primeiro)
            self.rules.sort(key=lambda r: r.priority, reverse=True)
            
            # Categoria padrão
            self.default_category = rules_data.get('default_category', 'custom-exporters')
            
            logger.info(f"[RULES] {len(self.rules)} regras carregadas")
            return True
            
        except Exception as e:
            logger.error(f"[RULES] Erro ao carregar regras: {e}")
            return False
    
    def categorize(self, job_data: Dict) -> str:
        """
        Categoriza um job baseado nas regras
        
        Args:
            job_data: {
                'job_name': 'icmp',
                'metrics_path': '/probe',
                'module': 'icmp'  # opcional
            }
        
        Returns:
            Categoria identificada ou default_category
        """
        # Aplicar regras em ordem de prioridade
        for rule in self.rules:
            if rule.matches(job_data):
                logger.debug(
                    f"[CATEGORIZE] '{job_data.get('job_name')}' → "
                    f"'{rule.category}' (rule: {rule.id})"
                )
                return rule.category
        
        # Nenhuma regra aplicou - usar categoria padrão
        logger.debug(
            f"[CATEGORIZE] '{job_data.get('job_name')}' → "
            f"'{self.default_category}' (default)"
        )
        return self.default_category
```

**Como usar no monitoring_types_dynamic.py:**

```python
# Criar engine global
rule_engine = CategorizationRuleEngine(config_manager)

# Carregar regras no startup
@app.on_event("startup")
async def load_categorization_rules():
    await rule_engine.load_rules()

# Usar no lugar da função _infer_category_and_type()
def categorize_job(job_config: Dict) -> str:
    job_data = {
        'job_name': job_config.get('job_name'),
        'metrics_path': job_config.get('metrics_path', '/metrics'),
        'module': _extract_blackbox_module(job_config)
    }
    
    return rule_engine.categorize(job_data)
```

---

#### 5.1.3 DynamicQueryBuilder com Jinja2 (NOVO)

**Arquivo:** `backend/core/dynamic_query_builder.py`

**Propósito:** Construtor de queries PromQL usando templates Jinja2

**Implementação:**

```python
"""
Dynamic Query Builder - Construtor de Queries PromQL com Jinja2

RESPONSABILIDADES:
- Renderizar templates Jinja2 de queries PromQL
- Suportar variáveis dinâmicas (modules, jobs, labels)
- Cache de templates compilados
- Validação de queries
"""

from jinja2 import Environment, Template, TemplateError
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class DynamicQueryBuilder:
    """
    Construtor de queries PromQL dinâmicas usando Jinja2
    
    Features:
    - Templates reutilizáveis
    - Variáveis dinâmicas
    - Cache de templates compilados
    - Validação de sintaxe
    
    Exemplo:
        builder = DynamicQueryBuilder()
        
        template = '''
        probe_success{
            job="blackbox",
            __param_module=~"{{ modules|join('|') }}"
            {% if site %},site="{{ site }}"{% endif %}
        }
        '''
        
        query = builder.build(template, {
            'modules': ['icmp', 'tcp'],
            'site': 'palmas'
        })
        
        # Resultado:
        # probe_success{job="blackbox",__param_module=~"icmp|tcp",site="palmas"}
    """
    
    def __init__(self):
        self.env = Environment(
            trim_blocks=True,
            lstrip_blocks=True,
            autoescape=False  # PromQL não precisa de escape
        )
        self._template_cache: Dict[str, Template] = {}
    
    def build(self, template_str: str, params: Dict[str, Any]) -> str:
        """
        Constrói query PromQL a partir de template
        
        Args:
            template_str: Template Jinja2
            params: Parâmetros para substituição
        
        Returns:
            Query PromQL renderizada
        
        Raises:
            TemplateError: Se template inválido
        """
        try:
            # Buscar template no cache
            if template_str not in self._template_cache:
                self._template_cache[template_str] = self.env.from_string(template_str)
            
            template = self._template_cache[template_str]
            
            # Renderizar com parâmetros
            query = template.render(**params)
            
            # Limpar espaços extras
            query = ' '.join(query.split())
            
            logger.debug(f"[QUERY BUILD] Template renderizado: {query[:100]}...")
            return query
            
        except TemplateError as e:
            logger.error(f"[QUERY BUILD ERROR] Template inválido: {e}")
            raise
        except Exception as e:
            logger.error(f"[QUERY BUILD ERROR] Erro inesperado: {e}")
            raise
    
    def clear_cache(self) -> None:
        """Limpa cache de templates"""
        self._template_cache.clear()
        logger.info("[QUERY BUILDER] Cache de templates limpo")


# Templates predefinidos
QUERY_TEMPLATES = {
    "network_probe_success": """
        probe_success{
            job="blackbox",
            __param_module=~"{{ modules|join('|') }}"
            {% if company %},company="{{ company }}"{% endif %}
            {% if site %},site="{{ site }}"{% endif %}
        }
    """,
    
    "network_probe_duration": """
        probe_duration_seconds{
            job="blackbox",
            __param_module=~"{{ modules|join('|') }}"
            {% if company %},company="{{ company }}"{% endif %}
        }
    """,
    
    "node_cpu_usage": """
        100 - (avg by (instance) (
            rate(node_cpu_seconds_total{
                job=~"{{ jobs|join('|') }}",
                mode="idle"
            }[{{ time_range|default("5m") }}])
        ) * 100)
    """,
    
    "node_memory_usage": """
        (1 - (
            node_memory_MemAvailable_bytes{job=~"{{ jobs|join('|') }}"} / 
            node_memory_MemTotal_bytes{job=~"{{ jobs|join('|') }}"}
        )) * 100
    """
}
```

**Uso:**

```python
# Criar builder
query_builder = DynamicQueryBuilder()

# Construir query para network probes
query = query_builder.build(
    QUERY_TEMPLATES['network_probe_success'],
    {
        'modules': ['icmp', 'tcp'],
        'company': 'Empresa Ramada',
        'site': 'palmas'
    }
)

# Executar query no Prometheus
response = requests.get(
    f"{prometheus_url}/api/v1/query",
    params={'query': query}
)
```

---

#### 5.1.4 Endpoint Unificado `/monitoring/data` (NOVO)

**Arquivo:** `backend/api/monitoring_unified.py`

**Propósito:** Endpoint único que serve dados para todas as 4 páginas de monitoramento

**Implementação:**

```python
"""
API Unificada de Monitoramento - Endpoint Único para Todas as Páginas

RESPONSABILIDADES:
- Endpoint unificado GET /api/v1/monitoring/data
- Filtra por categoria (network-probes, web-probes, etc)
- Executa queries PromQL dinamicamente
- Retorna dados formatados para ProTable
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List, Dict, Any
import logging
import httpx

from core.consul_kv_config_manager import ConsulKVConfigManager
from core.dynamic_query_builder import DynamicQueryBuilder, QUERY_TEMPLATES
from core.multi_config_manager import MultiConfigManager

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/monitoring", tags=["Monitoring Unified"])

# Inicializar componentes
config_manager = ConsulKVConfigManager()
query_builder = DynamicQueryBuilder()
multi_config = MultiConfigManager()


@router.get("/data")
async def get_monitoring_data(
    category: str = Query(..., description="Categoria: network-probes, web-probes, etc"),
    server: Optional[str] = Query(None, description="Servidor Prometheus (opcional)"),
    company: Optional[str] = Query(None, description="Filtrar por empresa"),
    site: Optional[str] = Query(None, description="Filtrar por site")
):
    """
    Endpoint unificado para dados de monitoramento
    
    Este endpoint substitui múltiplos endpoints específicos.
    Funciona com QUALQUER categoria de monitoramento.
    
    Args:
        category: Categoria de monitoramento (ex: network-probes)
        server: Servidor Prometheus específico (opcional)
        company: Filtro de empresa (opcional)
        site: Filtro de site (opcional)
    
    Returns:
        {
            "success": true,
            "category": "network-probes",
            "data": [
                {
                    "id": "...",
                    "instance": "10.0.0.1",
                    "module": "icmp",
                    "status": 1,
                    "latency": 25.3,
                    "company": "Empresa Ramada",
                    "site": "palmas"
                }
            ],
            "total": 150,
            "query": "probe_success{...}"
        }
    
    Example:
        GET /api/v1/monitoring/data?category=network-probes&company=Ramada
        GET /api/v1/monitoring/data?category=system-exporters&site=palmas
    """
    try:
        logger.info(f"[UNIFIED API] Buscando dados para category={category}")
        
        # STEP 1: Buscar tipos de monitoramento do cache
        types_cache = await config_manager.get('monitoring-types/cache')
        
        if not types_cache:
            raise HTTPException(
                status_code=500,
                detail="Cache de tipos não disponível. Execute sync-cache primeiro."
            )
        
        # STEP 2: Filtrar tipos pela categoria solicitada
        category_types = []
        for category_data in types_cache.get('categories', []):
            if category_data['category'] == category:
                category_types = category_data['types']
                break
        
        if not category_types:
            raise HTTPException(
                status_code=404,
                detail=f"Categoria '{category}' não encontrada"
            )
        
        # STEP 3: Determinar servidor Prometheus
        if server:
            prometheus_server = server
        else:
            # Usar primeiro servidor disponível
            prometheus_server = list(types_cache['servers'].keys())[0]
        
        # STEP 4: Construir query PromQL baseado na categoria
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
            # Node/Windows exporters
            jobs = [t['job_name'] for t in category_types]
            
            query = query_builder.build(
                QUERY_TEMPLATES['node_cpu_usage'],
                {
                    'jobs': jobs,
                    'time_range': '5m'
                }
            )
        
        else:
            # Outros exporters - query genérica
            jobs = [t['job_name'] for t in category_types]
            query = f"up{{job=~\"{'|'.join(jobs)}\"}}"
        
        # STEP 5: Executar query no Prometheus
        prometheus_url = f"http://{prometheus_server}:9090"
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{prometheus_url}/api/v1/query",
                params={'query': query},
                timeout=10.0
            )
            response.raise_for_status()
            prom_data = response.json()
        
        # STEP 6: Processar resultados
        if prom_data['status'] != 'success':
            raise HTTPException(
                status_code=500,
                detail=f"Prometheus query failed: {prom_data.get('error')}"
            )
        
        results = prom_data['data']['result']
        
        # Formatar dados para ProTable
        formatted_data = []
        for result in results:
            metric = result['metric']
            value = result['value'][1]  # [timestamp, value]
            
            formatted_data.append({
                'id': f"{metric.get('instance', 'unknown')}_{metric.get('job', 'unknown')}",
                'instance': metric.get('instance', ''),
                'job': metric.get('job', ''),
                'module': metric.get('__param_module', ''),
                'status': float(value),
                'company': metric.get('company', ''),
                'site': metric.get('site', ''),
                **{k: v for k, v in metric.items() if not k.startswith('__')}
            })
        
        return {
            "success": True,
            "category": category,
            "data": formatted_data,
            "total": len(formatted_data),
            "query": query,
            "prometheus_server": prometheus_server
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[UNIFIED API ERROR] {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sync-cache")
async def sync_monitoring_cache():
    """
    Força sincronização do cache de tipos de monitoramento
    
    Este endpoint:
    1. Extrai tipos de TODOS os servidores Prometheus via SSH
    2. Invalida cache existente
    3. Salva novos tipos no KV
    4. Retorna status
    
    Returns:
        {
            "success": true,
            "message": "Cache sincronizado com sucesso",
            "total_types": 45,
            "total_servers": 3
        }
    """
    try:
        logger.info("[SYNC CACHE] Iniciando sincronização forçada...")
        
        # Importar função de extração
        from api.monitoring_types_dynamic import extract_types_from_all_servers
        
        # Extrair tipos de todos os servidores
        result = await extract_types_from_all_servers()
        
        # Adicionar timestamp
        result['last_updated'] = datetime.now().isoformat()
        result['version'] = '1.0.0'
        
        # Salvar no KV (invalidando cache)
        await config_manager.put('monitoring-types/cache', result)
        
        logger.info(f"[SYNC CACHE] ✓ Sincronizado: {result['total_types']} tipos")
        
        return {
            "success": True,
            "message": "Cache sincronizado com sucesso",
            "total_types": result['total_types'],
            "total_servers": result['total_servers']
        }
    
    except Exception as e:
        logger.error(f"[SYNC CACHE ERROR] {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
```

---

### 5.2 Frontend React

#### 5.2.1 DynamicMonitoringPage (NOVO)

**Arquivo:** `frontend/src/pages/DynamicMonitoringPage.tsx`

**Propósito:** Componente base único para todas as 4 páginas de monitoramento

**Implementação completa:**

```typescript
/**
 * Dynamic Monitoring Page - Componente Base Único
 * 
 * Este componente renderiza QUALQUER página de monitoramento de forma 100% dinâmica.
 * Funciona para network-probes, web-probes, system-exporters, database-exporters, etc.
 * 
 * CARACTERÍSTICAS:
 * - Colunas 100% dinâmicas via useMetadataFields(category)
 * - Filtros 100% dinâmicos via useFilterFields(category)
 * - Dados do endpoint /api/v1/monitoring/data?category={category}
 * - Reutiliza componentes: MetadataFilterBar, AdvancedSearchPanel, ColumnSelector
 * 
 * USO:
 *   <DynamicMonitoringPage category="network-probes" />
 *   <DynamicMonitoringPage category="web-probes" />
 */

import React, { useRef, useMemo, useCallback, useState, useEffect } from 'react';
import {
  Button,
  Space,
  Tooltip,
  message,
  Popconfirm,
  Tag
} from 'antd';
import {
  ReloadOutlined,
  SyncOutlined,
  FilterOutlined,
  ClearOutlined,
  DownloadOutlined
} from '@ant-design/icons';
import type { ActionType } from '@ant-design/pro-components';
import {
  PageContainer,
  ProTable,
} from '@ant-design/pro-components';

import { consulAPI } from '../services/api';
import { useTableFields, useFilterFields } from '../hooks/useMetadataFields';
import ColumnSelector, { type ColumnConfig } from '../components/ColumnSelector';
import MetadataFilterBar from '../components/MetadataFilterBar';
import AdvancedSearchPanel, { type SearchCondition } from '../components/AdvancedSearchPanel';
import ResizableTitle from '../components/ResizableTitle';

// MAPA DE TÍTULOS AMIGÁVEIS
const CATEGORY_DISPLAY_NAMES: Record<string, string> = {
  'network-probes': 'Network Probes (Rede)',
  'web-probes': 'Web Probes (Aplicações)',
  'system-exporters': 'Exporters: Sistemas',
  'database-exporters': 'Exporters: Bancos de Dados'
};

interface DynamicMonitoringPageProps {
  category: string;  // 'network-probes', 'web-probes', etc
}

interface MonitoringDataItem {
  id: string;
  instance: string;
  job: string;
  status: number;
  [key: string]: any;  // Campos dinâmicos
}

type MonitoringColumn = import('@ant-design/pro-components').ProColumns<MonitoringDataItem>;

const DynamicMonitoringPage: React.FC<DynamicMonitoringPageProps> = ({ category }) => {
  const actionRef = useRef<ActionType | null>(null);
  
  // SISTEMA DINÂMICO: Carregar campos metadata para esta categoria
  const { tableFields, loading: tableFieldsLoading } = useTableFields(category);
  const { filterFields, loading: filterFieldsLoading } = useFilterFields(category);
  
  // Estados
  const [filters, setFilters] = useState<Record<string, string | undefined>>({});
  const [columnConfig, setColumnConfig] = useState<ColumnConfig[]>([]);
  const [columnWidths, setColumnWidths] = useState<Record<string, number>>({});
  const [advancedOpen, setAdvancedOpen] = useState(false);
  const [advancedConditions, setAdvancedConditions] = useState<SearchCondition[]>([]);
  const [advancedOperator, setAdvancedOperator] = useState<'and' | 'or'>('and');
  const [syncLoading, setSyncLoading] = useState(false);
  
  // SISTEMA DINÂMICO: Combinar colunas fixas + campos metadata
  const defaultColumnConfig = useMemo<ColumnConfig[]>(() => {
    const metadataColumns: ColumnConfig[] = tableFields.map((field) => ({
      key: field.name,
      title: field.display_name,
      visible: field.show_in_table ?? true,
      locked: false
    }));
    
    // Colunas fixas que sempre existem
    const fixedColumns: ColumnConfig[] = [
      { key: 'instance', title: 'Instance', visible: true },
      { key: 'job', title: 'Job', visible: true },
      { key: 'status', title: 'Status', visible: true },
      { key: 'actions', title: 'Ações', visible: true, locked: true }
    ];
    
    return [...fixedColumns, ...metadataColumns];
  }, [tableFields]);
  
  // Atualizar columnConfig quando tableFields carregar
  useEffect(() => {
    if (defaultColumnConfig.length > 0 && columnConfig.length === 0) {
      setColumnConfig(defaultColumnConfig);
    }
  }, [defaultColumnConfig, columnConfig.length]);
  
  // SISTEMA DINÂMICO: Gerar colunas do ProTable
  const proTableColumns = useMemo<MonitoringColumn[]>(() => {
    const visibleConfigs = columnConfig.filter(c => c.visible);
    
    return visibleConfigs.map((colConfig) => {
      const baseColumn: MonitoringColumn = {
        title: () => (
          <ResizableTitle
            title={colConfig.title}
            width={columnWidths[colConfig.key] || 150}
            onResize={(width) => {
              setColumnWidths(prev => ({ ...prev, [colConfig.key]: width }));
            }}
          />
        ),
        dataIndex: colConfig.key,
        key: colConfig.key,
        width: columnWidths[colConfig.key] || 150,
        fixed: colConfig.locked ? 'left' : undefined,
        ellipsis: true,
      };
      
      // Renderização especial para status
      if (colConfig.key === 'status') {
        baseColumn.render = (value: number) => (
          <Tag color={value === 1 ? 'success' : 'error'}>
            {value === 1 ? 'Online' : 'Offline'}
          </Tag>
        );
      }
      
      // Renderização especial para actions
      if (colConfig.key === 'actions') {
        baseColumn.render = (_, record) => (
          <Space>
            <Tooltip title="Ver detalhes">
              <Button
                type="link"
                size="small"
                onClick={() => {
                  message.info(`Detalhes de ${record.instance}`);
                }}
              >
                Detalhes
              </Button>
            </Tooltip>
          </Space>
        );
      }
      
      return baseColumn;
    });
  }, [columnConfig, columnWidths]);
  
  // Request handler - busca dados do backend
  const requestHandler = useCallback(async (params: any) => {
    try {
      // Construir query params
      const queryParams = new URLSearchParams({
        category,
        ...filters
      });
      
      const response = await fetch(`/api/v1/monitoring/data?${queryParams}`);
      const data = await response.json();
      
      if (!data.success) {
        throw new Error(data.detail || 'Erro ao buscar dados');
      }
      
      return {
        data: data.data || [],
        success: true,
        total: data.total || 0
      };
    } catch (error) {
      message.error('Erro ao carregar dados: ' + error);
      return {
        data: [],
        success: false,
        total: 0
      };
    }
  }, [category, filters]);
  
  // Handler de sincronização
  const handleSync = useCallback(async () => {
    setSyncLoading(true);
    try {
      const response = await fetch('/api/v1/monitoring/sync-cache', {
        method: 'POST'
      });
      
      const data = await response.json();
      
      if (data.success) {
        message.success('Cache sincronizado com sucesso!');
        actionRef.current?.reload();
      } else {
        throw new Error(data.detail || 'Erro ao sincronizar');
      }
    } catch (error) {
      message.error('Erro ao sincronizar: ' + error);
    } finally {
      setSyncLoading(false);
    }
  }, []);
  
  // Aplicar filtros avançados
  const applyAdvancedFilters = useCallback(
    (data: MonitoringDataItem[]) => {
      if (!advancedConditions.length) {
        return data;
      }
      
      return data.filter((row) => {
        const evaluations = advancedConditions.map((condition) => {
          const value = row[condition.field];
          const target = condition.value;
          
          switch (condition.operator) {
            case 'eq':
              return value === target;
            case 'ne':
              return value !== target;
            case 'contains':
              return String(value).includes(String(target));
            default:
              return true;
          }
        });
        
        return advancedOperator === 'and'
          ? evaluations.every(Boolean)
          : evaluations.some(Boolean);
      });
    },
    [advancedConditions, advancedOperator]
  );
  
  return (
    <PageContainer
      title={CATEGORY_DISPLAY_NAMES[category] || category}
      extra={[
        <Button
          key="sync"
          icon={<SyncOutlined spin={syncLoading} />}
          onClick={handleSync}
          loading={syncLoading}
        >
          Sincronizar Cache
        </Button>,
        <Button
          key="advanced"
          icon={<FilterOutlined />}
          onClick={() => setAdvancedOpen(true)}
        >
          Filtro Avançado
        </Button>,
        <ColumnSelector
          key="columns"
          columns={columnConfig}
          onChange={setColumnConfig}
        />
      ]}
    >
      {/* Barra de filtros metadata */}
      <MetadataFilterBar
        fields={filterFields}
        filters={filters}
        onChange={(newFilters) => {
          setFilters(newFilters);
          actionRef.current?.reload();
        }}
      />
      
      {/* Tabela principal */}
      <ProTable<MonitoringDataItem>
        actionRef={actionRef}
        rowKey="id"
        columns={proTableColumns}
        request={requestHandler}
        pagination={{
          defaultPageSize: 20,
          showSizeChanger: true,
        }}
        search={false}
        options={{
          reload: true,
          setting: false,
          density: true,
        }}
        toolbar={{
          actions: [
            <Button
              key="clear"
              icon={<ClearOutlined />}
              onClick={() => {
                setFilters({});
                actionRef.current?.reload();
              }}
            >
              Limpar Filtros
            </Button>
          ]
        }}
      />
      
      {/* Painel de busca avançada */}
      <AdvancedSearchPanel
        visible={advancedOpen}
        onClose={() => setAdvancedOpen(false)}
        fields={tableFields.map(f => ({ name: f.name, label: f.display_name }))}
        conditions={advancedConditions}
        operator={advancedOperator}
        onConditionsChange={setAdvancedConditions}
        onOperatorChange={setAdvancedOperator}
        onApply={() => {
          setAdvancedOpen(false);
          actionRef.current?.reload();
        }}
      />
    </PageContainer>
  );
};

export default DynamicMonitoringPage;
```

---

#### 5.2.2 Rotas Dinâmicas (ATUALIZAR)

**Arquivo:** `frontend/src/routes.tsx`

**Adicionar rotas para as 4 novas páginas:**

```typescript
import { lazy } from 'react';
import DynamicMonitoringPage from '@/pages/DynamicMonitoringPage';

// Páginas existentes (backup/referência)
const Services = lazy(() => import('@/pages/Services'));
const BlackboxTargets = lazy(() => import('@/pages/BlackboxTargets'));

// NOVAS PÁGINAS - todas usam DynamicMonitoringPage
const NetworkProbes = () => <DynamicMonitoringPage category="network-probes" />;
const WebProbes = () => <DynamicMonitoringPage category="web-probes" />;
const SystemExporters = () => <DynamicMonitoringPage category="system-exporters" />;
const DatabaseExporters = () => <DynamicMonitoringPage category="database-exporters" />;

export const routes = [
  // ... rotas existentes ...
  
  // BACKUP/REFERÊNCIA - páginas antigas
  {
    path: '/services',
    component: Services,
    name: 'Services (Backup)',
  },
  {
    path: '/blackbox-targets',
    component: BlackboxTargets,
    name: 'Blackbox Targets (Backup)',
  },
  
  // NOVAS PÁGINAS DINÂMICAS
  {
    path: '/monitoring/network-probes',
    component: NetworkProbes,
    name: 'Network Probes',
    icon: 'WifiOutlined',
  },
  {
    path: '/monitoring/web-probes',
    component: WebProbes,
    name: 'Web Probes',
    icon: 'GlobalOutlined',
  },
  {
    path: '/monitoring/system-exporters',
    component: SystemExporters,
    name: 'System Exporters',
    icon: 'DesktopOutlined',
  },
  {
    path: '/monitoring/database-exporters',
    component: DatabaseExporters,
    name: 'Database Exporters',
    icon: 'DatabaseOutlined',
  },
];
```

---

#### 5.2.3 Hook useMetadataFields Melhorado (ATUALIZAR)

**Arquivo:** `frontend/src/hooks/useMetadataFields.ts`

**Modificar para aceitar contexto dinâmico:**

```typescript
/**
 * Hook useTableFields - Versão 2.0 (100% Dinâmica)
 * 
 * Aceita QUALQUER contexto como string e filtra campos automaticamente.
 * Não precisa mais hardcodar contextos como 'services' ou 'blackbox'.
 * 
 * USO:
 *   useTableFields('services')             // Funciona
 *   useTableFields('network-probes')       // Funciona
 *   useTableFields('custom-exporters')     // Funciona
 *   useTableFields('qualquer-categoria')   // Funciona
 */

import { useState, useEffect } from 'react';
import type { MetadataField } from '../services/api';

// Cache global (5 minutos)
const CACHE_TTL = 5 * 60 * 1000;
let cachedFields: MetadataField[] | null = null;
let cacheTimestamp: number = 0;

export function useTableFields(context: string) {
  const [fields, setFields] = useState<MetadataField[]>([]);
  const [loading, setLoading] = useState(true);
  
  useEffect(() => {
    async function loadFields() {
      setLoading(true);
      
      try {
        // Verificar cache
        const now = Date.now();
        if (cachedFields && (now - cacheTimestamp) < CACHE_TTL) {
          console.log('[useMetadataFields] Cache HIT');
          filterAndSetFields(cachedFields, context);
          setLoading(false);
          return;
        }
        
        // Cache miss - buscar do backend
        console.log('[useMetadataFields] Cache MISS - buscando do backend');
        const response = await fetch('/api/v1/metadata-fields/fields');
        const data = await response.json();
        
        if (!data.success || !data.fields) {
          throw new Error('Resposta inválida do backend');
        }
        
        // Atualizar cache global
        cachedFields = data.fields;
        cacheTimestamp = now;
        
        // Filtrar e setar campos
        filterAndSetFields(cachedFields, context);
        
      } catch (error) {
        console.error('[useMetadataFields] Erro ao carregar campos:', error);
        setFields([]);
      } finally {
        setLoading(false);
      }
    }
    
    function filterAndSetFields(allFields: MetadataField[], context: string) {
      // Construir chave de filtro: show_in_{context}
      // Exemplo: 'network-probes' → 'show_in_network_probes'
      const showInKey = `show_in_${context.replace(/-/g, '_')}`;
      
      console.log(`[useMetadataFields] Filtrando campos para context="${context}" (${showInKey})`);
      
      const filtered = allFields.filter((field) => {
        // Se campo não tem a propriedade show_in_{context}, exibe por padrão
        if (!(showInKey in field)) {
          return true;
        }
        
        // Se tem a propriedade, respeitar o valor
        return field[showInKey] !== false;
      });
      
      console.log(`[useMetadataFields] ${filtered.length}/${allFields.length} campos visíveis`);
      setFields(filtered);
    }
    
    loadFields();
  }, [context]);
  
  return { tableFields: fields, loading };
}

// Hooks similares para form e filter
export function useFormFields(context: string) {
  const { tableFields, loading } = useTableFields(context);
  
  const formFields = tableFields.filter(field => {
    const showInKey = `show_in_${context.replace(/-/g, '_')}_form`;
    if (!(showInKey in field)) {
      return field.show_in_form !== false;  // Fallback para propriedade genérica
    }
    return field[showInKey] !== false;
  });
  
  return { formFields, loading };
}

export function useFilterFields(context: string) {
  const { tableFields, loading } = useTableFields(context);
  
  const filterFields = tableFields.filter(field => {
    return field.show_in_filter !== false;
  });
  
  return { filterFields, loading };
}
```

---

## 📋 PLANO DE IMPLEMENTAÇÃO DETALHADO

### FASE 1: Preparação (Dias 1-2)

#### Dia 1: Análise e Setup

**MANHÃ:**
1. ✅ **Revisar documento completo** - garantir entendimento total
2. ✅ **Criar branch Git** - `feature/dynamic-monitoring-pages`
3. ✅ **Backup das páginas existentes** - Services.tsx e BlackboxTargets.tsx
4. ✅ **Setup ambiente de desenvolvimento** - backend + frontend rodando

**Checklist:**
```bash
# Backend
cd backend
source venv/bin/activate
python app.py  # Deve iniciar em http://localhost:5000

# Frontend (outro terminal)
cd frontend
npm run dev  # Deve iniciar em http://localhost:8081

# Git
git checkout -b feature/dynamic-monitoring-pages
git status
```

**TARDE:**
5. ✅ **Criar estrutura de arquivos vazios**
   ```bash
   # Backend
   touch backend/core/consul_kv_config_manager.py
   touch backend/core/categorization_rule_engine.py
   touch backend/core/dynamic_query_builder.py
   touch backend/api/monitoring_unified.py
   
   # Frontend
   touch frontend/src/pages/DynamicMonitoringPage.tsx
   ```

6. ✅ **Configurar JSON de regras no KV**
   ```bash
   # Criar arquivo local
   cat > categorization_rules.json << 'EOF'
   {
     "version": "1.0.0",
     "rules": [...],  # Usar JSON completo da seção 5.1.2
     "default_category": "custom-exporters"
   }
   EOF
   
   # Upload para Consul
   curl -X PUT \
     -H "X-Consul-Token: $CONSUL_TOKEN" \
     --data-binary @categorization_rules.json \
     "http://172.16.1.26:8500/v1/kv/skills/eye/monitoring-types/categorization/rules"
   ```

#### Dia 2: Validação de Prerequisitos

**MANHÃ:**
7. ✅ **Testar endpoint monitoring_types_dynamic existente**
   ```bash
   curl "http://localhost:5000/api/v1/monitoring-types-dynamic/from-prometheus?server=ALL" | jq
   
   # Validar resposta:
   # - success: true
   # - categories[]: deve ter 8 categorias
   # - all_types[]: deve ter 15+ tipos
   ```

8. ✅ **Testar metadata fields existente**
   ```bash
   curl "http://localhost:5000/api/v1/metadata-fields/fields" | jq
   
   # Validar resposta:
   # - success: true
   # - fields[]: deve ter 22 campos
   # - cada campo tem: name, display_name, show_in_services, show_in_blackbox
   ```

**TARDE:**
9. ✅ **Validar hooks React existentes**
   - Abrir DevTools no navegador
   - Ir em /services
   - Verificar no Network tab: GET /api/v1/metadata-fields/fields
   - Confirmar que useMetadataFields está funcionando

10. ✅ **Criar documento de progresso**
    ```bash
    cat > IMPLEMENTACAO_PROGRESSO.md << 'EOF'
    # Progresso da Implementação
    
    ## Fase 1: Preparação
    - [ ] Dia 1: Setup e estrutura
    - [ ] Dia 2: Validação
    
    ## Fase 2: Backend
    - [ ] Dia 3-4: Core components
    - [ ] Dia 5: API endpoints
    
    ## Fase 3: Frontend
    - [ ] Dia 6-7: DynamicMonitoringPage
    - [ ] Dia 8: Rotas e integração
    
    ## Fase 4: Testes
    - [ ] Dia 9-10: Testes completos
    EOF
    ```

---

### FASE 2: Backend (Dias 3-5)

#### Dia 3: Core Components Parte 1

**MANHÃ: ConsulKVConfigManager**

1. ✅ **Implementar ConsulKVConfigManager**
   - Copiar código completo da seção 5.1.1
   - Arquivo: `backend/core/consul_kv_config_manager.py`

2. ✅ **Criar testes unitários**
   ```python
   # backend/tests/test_consul_kv_config_manager.py
   import pytest
   from core.consul_kv_config_manager import ConsulKVConfigManager
   
   @pytest.mark.asyncio
   async def test_get_put():
       manager = ConsulKVConfigManager(ttl=10)
       
       # Salvar
       data = {"test": "value"}
       result = await manager.put('test/key', data)
       assert result == True
       
       # Buscar (deve vir do KV)
       retrieved = await manager.get('test/key')
       assert retrieved == data
       
       # Buscar novamente (deve vir do cache)
       retrieved2 = await manager.get('test/key')
       assert retrieved2 == data
       
       # Verificar cache
       stats = manager.get_cache_stats()
       assert stats['active_items'] == 1
   
   @pytest.mark.asyncio
   async def test_cache_expiration():
       manager = ConsulKVConfigManager(ttl=1)  # 1 segundo
       
       await manager.put('test/expire', {"data": "test"})
       
       # Deve estar no cache
       value1 = await manager.get('test/expire')
       assert value1 is not None
       
       # Aguardar expiração
       await asyncio.sleep(2)
       
       # Deve buscar do KV novamente
       value2 = await manager.get('test/expire')
       assert value2 is not None
   ```

3. ✅ **Executar testes**
   ```bash
   cd backend
   pytest tests/test_consul_kv_config_manager.py -v
   
   # Deve passar todos os testes
   ```

**TARDE: DynamicQueryBuilder**

4. ✅ **Implementar DynamicQueryBuilder**
   - Copiar código completo da seção 5.1.3
   - Arquivo: `backend/core/dynamic_query_builder.py`

5. ✅ **Criar testes unitários**
   ```python
   # backend/tests/test_dynamic_query_builder.py
   from core.dynamic_query_builder import DynamicQueryBuilder, QUERY_TEMPLATES
   
   def test_simple_query():
       builder = DynamicQueryBuilder()
       
       template = 'up{job="{{ job }}"}'
       query = builder.build(template, {'job': 'prometheus'})
       
       assert query == 'up{job="prometheus"}'
   
   def test_network_probe_query():
       builder = DynamicQueryBuilder()
       
       query = builder.build(
           QUERY_TEMPLATES['network_probe_success'],
           {
               'modules': ['icmp', 'tcp'],
               'company': 'Ramada',
               'site': 'palmas'
           }
       )
       
       # Verificar que query tem os elementos corretos
       assert 'icmp|tcp' in query
       assert 'company="Ramada"' in query
       assert 'site="palmas"' in query
   
   def test_optional_params():
       builder = DynamicQueryBuilder()
       
       # Sem site
       query = builder.build(
           QUERY_TEMPLATES['network_probe_success'],
           {
               'modules': ['icmp'],
               'company': 'Ramada'
           }
       )
       
       assert 'site=' not in query  # Site não deve aparecer
   ```

6. ✅ **Executar testes**
   ```bash
   pytest tests/test_dynamic_query_builder.py -v
   ```

#### Dia 4: Core Components Parte 2

**MANHÃ: CategorizationRuleEngine**

7. ✅ **Implementar CategorizationRuleEngine**
   - Copiar código completo da seção 5.1.2
   - Arquivo: `backend/core/categorization_rule_engine.py`

8. ✅ **Criar testes unitários**
   ```python
   # backend/tests/test_categorization_rule_engine.py
   import pytest
   from core.categorization_rule_engine import CategorizationRuleEngine
   from core.consul_kv_config_manager import ConsulKVConfigManager
   
   @pytest.mark.asyncio
   async def test_load_rules():
       config_manager = ConsulKVConfigManager()
       engine = CategorizationRuleEngine(config_manager)
       
       # Carregar regras do KV
       success = await engine.load_rules()
       assert success == True
       assert len(engine.rules) > 0
   
   def test_categorize_icmp():
       # ... (setup engine com regras mockadas)
       
       category = engine.categorize({
           'job_name': 'icmp',
           'metrics_path': '/probe',
           'module': 'icmp'
       })
       
       assert category == 'network-probes'
   
   def test_categorize_http():
       # ...
       
       category = engine.categorize({
           'job_name': 'http_2xx',
           'metrics_path': '/probe',
           'module': 'http_2xx'
       })
       
       assert category == 'web-probes'
   
   def test_categorize_unknown():
       # ...
       
       category = engine.categorize({
           'job_name': 'custom_unknown_job',
           'metrics_path': '/metrics'
       })
       
       assert category == 'custom-exporters'  # Default
   ```

9. ✅ **Executar testes**
   ```bash
   pytest tests/test_categorization_rule_engine.py -v
   ```

**TARDE: Integração com monitoring_types_dynamic.py**

10. ✅ **Modificar monitoring_types_dynamic.py para usar RuleEngine**
    ```python
    # backend/api/monitoring_types_dynamic.py
    
    # ADICIONAR no topo do arquivo:
    from core.consul_kv_config_manager import ConsulKVConfigManager
    from core.categorization_rule_engine import CategorizationRuleEngine
    
    # Criar instâncias globais
    config_manager = ConsulKVConfigManager()
    rule_engine = CategorizationRuleEngine(config_manager)
    
    # MODIFICAR função extract_types_from_prometheus_jobs():
    async def extract_types_from_prometheus_jobs(...):
        # ... código existente ...
        
        for job in scrape_configs:
            job_name = job.get('job_name', 'unknown')
            
            # ... código existente ...
            
            # SUBSTITUIR chamada _infer_category_and_type() por:
            module = _extract_blackbox_module(job)
            
            category = rule_engine.categorize({
                'job_name': job_name,
                'metrics_path': job.get('metrics_path', '/metrics'),
                'module': module
            })
            
            # NOVA função helper para display_name e exporter_type
            type_info = _get_type_info(job_name, category, module)
            
            type_schema = {
                "id": job_name,
                "display_name": type_info['display_name'],
                "category": category,
                "job_name": job_name,
                "exporter_type": type_info['exporter_type'],
                "module": module,
                "fields": fields,
                "metrics_path": job.get('metrics_path', '/metrics'),
                "server": server_host,
            }
            
            types.append(type_schema)
    
    def _get_type_info(job_name: str, category: str, module: Optional[str]) -> Dict:
        """
        Retorna display_name e exporter_type baseado no job_name
        
        Esta função SUBSTITUI a lógica hardcoded de _infer_category_and_type()
        """
        # Para blackbox, usar formatação do módulo
        if category in ['network-probes', 'web-probes']:
            return {
                'display_name': _format_display_name(module or job_name),
                'exporter_type': 'blackbox'
            }
        
        # Para outros exporters, inferir do job_name
        job_lower = job_name.lower()
        
        if 'node' in job_lower:
            return {'display_name': 'Node Exporter (Linux)', 'exporter_type': 'node_exporter'}
        elif 'windows' in job_lower:
            return {'display_name': 'Windows Exporter', 'exporter_type': 'windows_exporter'}
        elif 'mysql' in job_lower:
            return {'display_name': 'MySQL Exporter', 'exporter_type': 'mysql_exporter'}
        # ... etc (usar mesma lógica da função original)
        else:
            # Custom exporter
            return {
                'display_name': job_name.replace('-', ' ').replace('_', ' ').title(),
                'exporter_type': 'custom'
            }
    ```

11. ✅ **Testar modificação**
    ```bash
    # Reiniciar backend
    python app.py
    
    # Testar endpoint
    curl "http://localhost:5000/api/v1/monitoring-types-dynamic/from-prometheus?server=ALL" | jq
    
    # Validar que:
    # 1. Ainda retorna as mesmas categorias
    # 2. Tipos estão corretos
    # 3. Não há erros no log
    ```

#### Dia 5: Implementar Cache KV e Endpoint Unificado

**MANHÃ: Cache KV**

12. ✅ **Adicionar cache KV ao monitoring_types_dynamic.py**
    ```python
    # backend/api/monitoring_types_dynamic.py
    
    @router.get("/from-prometheus")
    async def get_types_from_prometheus(
        server: Optional[str] = Query(None),
        force_refresh: bool = Query(False, description="Forçar extração do Prometheus")
    ):
        """
        Busca tipos de monitoramento com cache KV
        """
        try:
            cache_key = 'monitoring-types/cache'
            
            # Se não forçou refresh, tentar buscar do cache
            if not force_refresh:
                cached = await config_manager.get(cache_key)
                
                if cached:
                    logger.info(f"[CACHE HIT] Usando tipos em cache")
                    
                    # Filtrar por servidor se necessário
                    if server and server != 'ALL':
                        # ... filtrar cached['servers'] ...
                        pass
                    
                    return cached
            
            # Cache miss ou force_refresh - extrair do Prometheus
            logger.info("[CACHE MISS] Extraindo tipos do Prometheus via SSH...")
            
            # ... código existente de extração ...
            result = await extract_types_from_all_servers(server)
            
            # Adicionar metadata
            result['version'] = '1.0.0'
            result['last_updated'] = datetime.now().isoformat()
            result['ttl_seconds'] = 300
            
            # Salvar no cache
            await config_manager.put(cache_key, result)
            logger.info("[CACHE WRITE] Tipos salvos no KV")
            
            return result
            
        except Exception as e:
            logger.error(f"[ERROR] {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=str(e))
    ```

13. ✅ **Testar cache**
    ```bash
    # Primeira chamada (deve extrair do Prometheus)
    time curl "http://localhost:5000/api/v1/monitoring-types-dynamic/from-prometheus?server=ALL"
    # Tempo: ~2-3 segundos
    
    # Segunda chamada (deve vir do cache)
    time curl "http://localhost:5000/api/v1/monitoring-types-dynamic/from-prometheus?server=ALL"
    # Tempo: <100ms
    
    # Forçar refresh
    curl "http://localhost:5000/api/v1/monitoring-types-dynamic/from-prometheus?server=ALL&force_refresh=true"
    # Tempo: ~2-3 segundos novamente
    ```

**TARDE: Endpoint Unificado**

14. ✅ **Implementar monitoring_unified.py**
    - Copiar código completo da seção 5.1.4
    - Arquivo: `backend/api/monitoring_unified.py`

15. ✅ **Registrar router no app.py**
    ```python
    # backend/app.py
    
    # ADICIONAR import
    from api.monitoring_unified import router as monitoring_unified_router
    
    # ADICIONAR router
    app.include_router(monitoring_unified_router, prefix="/api/v1", tags=["Monitoring Unified"])
    ```

16. ✅ **Testar endpoint unificado**
    ```bash
    # Testar network-probes
    curl "http://localhost:5000/api/v1/monitoring/data?category=network-probes" | jq
    
    # Testar web-probes
    curl "http://localhost:5000/api/v1/monitoring/data?category=web-probes" | jq
    
    # Testar system-exporters
    curl "http://localhost:5000/api/v1/monitoring/data?category=system-exporters" | jq
    
    # Validar que:
    # 1. success: true
    # 2. data[]: array com resultados
    # 3. query: query PromQL executada
    # 4. total: número de itens
    ```

17. ✅ **Commit do backend**
    ```bash
    git add backend/
    git commit -m "feat(backend): Implementar componentes dinâmicos e endpoint unificado

    - Adicionar ConsulKVConfigManager com cache TTL
    - Adicionar CategorizationRuleEngine baseado em JSON
    - Adicionar DynamicQueryBuilder com Jinja2
    - Modificar monitoring_types_dynamic para usar cache KV
    - Adicionar endpoint unificado /monitoring/data
    - Testes unitários completos

    BREAKING CHANGE: monitoring_types_dynamic agora usa cache KV"
    ```

---

### FASE 3: Frontend (Dias 6-8)

#### Dia 6: DynamicMonitoringPage Parte 1

**MANHÃ: Componente Base**

18. ✅ **Implementar DynamicMonitoringPage.tsx**
    - Copiar código completo da seção 5.2.1
    - Arquivo: `frontend/src/pages/DynamicMonitoringPage.tsx`

19. ✅ **Modificar useMetadataFields.ts**
    - Copiar código completo da seção 5.2.3
    - Arquivo: `frontend/src/hooks/useMetadataFields.ts`

20. ✅ **Testar componente isoladamente**
    - Criar arquivo temporário de teste:
    ```typescript
    // frontend/src/pages/TestDynamicPage.tsx
    import React from 'react';
    import DynamicMonitoringPage from './DynamicMonitoringPage';
    
    export default function TestDynamicPage() {
      return <DynamicMonitoringPage category="network-probes" />;
    }
    ```
    
    - Adicionar rota temporária em routes.tsx
    - Acessar http://localhost:8081/test-dynamic
    - Validar que página carrega sem erros

**TARDE: Ajustes e Refinamentos**

21. ✅ **Adicionar tratamento de erros**
    - Adicionar ErrorBoundary
    - Adicionar mensagens de erro amigáveis
    - Adicionar loading states

22. ✅ **Adicionar funcionalidades extras**
    - Export para CSV
    - Refresh automático (opcional)
    - Contador de itens online/offline

23. ✅ **Testar responsividade**
    - Testar em diferentes tamanhos de tela
    - Validar que colunas se ajustam
    - Validar que filtros funcionam em mobile

#### Dia 7: Integração com Rotas

**MANHÃ: Rotas e Menu**

24. ✅ **Adicionar rotas em routes.tsx**
    - Copiar código da seção 5.2.2
    - Arquivo: `frontend/src/routes.tsx`

25. ✅ **Atualizar menu de navegação**
    ```typescript
    // frontend/src/layouts/BasicLayout.tsx (ou equivalente)
    
    const menuItems = [
      // ... itens existentes ...
      
      // NOVO GRUPO: Monitoramento por Tipo
      {
        key: 'monitoring-group',
        label: 'Monitoramento por Tipo',
        icon: <DashboardOutlined />,
        children: [
          {
            key: '/monitoring/network-probes',
            label: 'Network Probes',
            icon: <WifiOutlined />,
          },
          {
            key: '/monitoring/web-probes',
            label: 'Web Probes',
            icon: <GlobalOutlined />,
          },
          {
            key: '/monitoring/system-exporters',
            label: 'System Exporters',
            icon: <DesktopOutlined />,
          },
          {
            key: '/monitoring/database-exporters',
            label: 'Database Exporters',
            icon: <DatabaseOutlined />,
          },
        ]
      },
      
      // Grupo de backup (opcional, escondido por padrão)
      {
        key: 'backup-group',
        label: 'Páginas Legacy (Backup)',
        icon: <FileOutlined />,
        children: [
          {
            key: '/services',
            label: 'Services (Antigo)',
          },
          {
            key: '/blackbox-targets',
            label: 'Blackbox Targets (Antigo)',
          },
        ]
      }
    ];
    ```

**TARDE: Testes de Navegação**

26. ✅ **Testar todas as rotas**
    ```
    ✓ http://localhost:8081/monitoring/network-probes
    ✓ http://localhost:8081/monitoring/web-probes
    ✓ http://localhost:8081/monitoring/system-exporters
    ✓ http://localhost:8081/monitoring/database-exporters
    ```

27. ✅ **Validar integração completa**
    - Dados carregam corretamente
    - Filtros funcionam
    - Colunas são dinâmicas
    - Paginação funciona
    - Busca funciona

#### Dia 8: Polish e Documentação

**MANHÃ: Melhorias de UX**

28. ✅ **Adicionar indicadores visuais**
    - Badge com contador de online/offline
    - Indicador de última atualização
    - Indicador de sincronização

29. ✅ **Adicionar tooltips informativos**
    - Explicar o que é cada categoria
    - Explicar botão "Sincronizar Cache"
    - Explicar filtros avançados

30. ✅ **Adicionar ações em lote** (opcional)
    - Selecionar múltiplos itens
    - Exportar selecionados
    - Ações bulk (se aplicável)

**TARDE: Commit do Frontend**

31. ✅ **Commit do frontend**
    ```bash
    git add frontend/
    git commit -m "feat(frontend): Implementar páginas de monitoramento dinâmicas

    - Adicionar DynamicMonitoringPage (componente base único)
    - Modificar useMetadataFields para aceitar contexto dinâmico
    - Adicionar 4 novas rotas: network-probes, web-probes, system-exporters, database-exporters
    - Atualizar menu de navegação
    - Adicionar indicadores visuais e tooltips
    
    Features:
    - 100% dinâmico - funciona com qualquer categoria
    - Reutiliza componentes existentes (MetadataFilterBar, AdvancedSearchPanel)
    - ProTable com colunas configuráveis
    - Cache local de 5 minutos para metadata fields"
    ```

---

### FASE 4: Testes e Validação (Dias 9-10)

#### Dia 9: Testes Funcionais

**MANHÃ: Testes End-to-End**

32. ✅ **Teste 1: Network Probes**
    ```
    Passos:
    1. Acessar /monitoring/network-probes
    2. Validar que tabela carrega
    3. Validar que colunas são: instance, job, status, company, site, etc
    4. Aplicar filtro de company
    5. Validar que dados filtram corretamente
    6. Clicar em "Sincronizar Cache"
    7. Validar que dados atualizam
    
    Resultado esperado: ✓ Tudo funciona
    ```

33. ✅ **Teste 2: Web Probes**
    ```
    Passos:
    1. Acessar /monitoring/web-probes
    2. Validar que mostra apenas probes HTTP/HTTPS
    3. Validar que não mostra probes ICMP/TCP
    4. Aplicar filtro avançado (module = http_2xx)
    5. Validar que filtra corretamente
    
    Resultado esperado: ✓ Tudo funciona
    ```

34. ✅ **Teste 3: System Exporters**
    ```
    Passos:
    1. Acessar /monitoring/system-exporters
    2. Validar que mostra node_exporter, windows_exporter
    3. Não deve mostrar blackbox targets
    4. Validar que colunas são apropriadas (CPU, Memory, etc)
    
    Resultado esperado: ✓ Tudo funciona
    ```

35. ✅ **Teste 4: Database Exporters**
    ```
    Passos:
    1. Acessar /monitoring/database-exporters
    2. Validar que mostra mysql, postgres, redis, mongodb
    3. Validar que colunas são apropriadas
    
    Resultado esperado: ✓ Tudo funciona
    ```

**TARDE: Testes de Performance**

36. ✅ **Teste de cache**
    ```bash
    # Limpar cache
    curl -X DELETE "http://172.16.1.26:8500/v1/kv/skills/eye/monitoring-types/cache?recurse"
    
    # Primeira carga (cold start)
    time curl "http://localhost:5000/api/v1/monitoring/data?category=network-probes"
    # Esperado: 2-3 segundos
    
    # Segunda carga (cache hit)
    time curl "http://localhost:5000/api/v1/monitoring/data?category=network-probes"
    # Esperado: <100ms
    
    # Resultado: ✓ Cache funciona
    ```

37. ✅ **Teste de carga**
    ```bash
    # Instalar apache bench
    sudo apt install apache2-utils
    
    # Teste de carga
    ab -n 100 -c 10 "http://localhost:5000/api/v1/monitoring/data?category=network-probes"
    
    # Validar:
    # - Requests per second: >50
    # - Failed requests: 0
    # - Time per request: <200ms (média)
    ```

#### Dia 9.5: ⭐ Testes de Persistência (NOVO)

**OBJETIVO:** Validar que dados persistem após reinício do backend

**CENÁRIO 1: Verificar cache no Consul KV**
```bash
# 1. Verificar que dados estão no Consul KV
curl "http://172.16.1.26:8500/v1/kv/skills/eye/monitoring-types/cache?recurse&pretty"

# 2. Validar estrutura:
# - skills/eye/monitoring-types/cache/network-probes
# - skills/eye/monitoring-types/cache/web-probes
# - skills/eye/monitoring-types/cache/system-exporters
# - skills/eye/monitoring-types/cache/database-exporters

# 3. Validar que cada chave contém:
# - timestamp (CreatedIndex, ModifiedIndex)
# - data JSON completa
```

**CENÁRIO 2: Reiniciar backend e validar cache**
```bash
# 1. Carregar dados normalmente
curl "http://localhost:5000/api/v1/monitoring/data?category=network-probes"

# 2. Reiniciar backend
cd /home/adrianofante/projetos/Skills-Eye
./restart-backend.sh

# 3. Aguardar 5 segundos

# 4. Requisitar novamente
time curl "http://localhost:5000/api/v1/monitoring/data?category=network-probes"

# Resultado esperado: 
# - Resposta em <100ms (leu do cache)
# - Dados idênticos ao passo 1
```

**CENÁRIO 3: Validar TTL de 5 minutos**
```bash
# 1. Carregar dados
curl "http://localhost:5000/api/v1/monitoring/data?category=network-probes" > /tmp/data1.json

# 2. Aguardar 6 minutos

# 3. Carregar novamente
curl "http://localhost:5000/api/v1/monitoring/data?category=network-probes" > /tmp/data2.json

# 4. Comparar
diff /tmp/data1.json /tmp/data2.json

# Resultado esperado:
# - Dados podem ter mudado (cache foi invalidado)
# - Tempo de resposta no passo 3 > 2 segundos (cache miss)
```

**CRITÉRIO DE SUCESSO:**
- ✅ Cache persiste no Consul KV
- ✅ Backend lê cache após reinício
- ✅ TTL de 5 minutos funciona corretamente

#### Dia 10: Validação Final e Documentação

**MANHÃ: Testes de Compatibilidade**

38. ✅ **Teste de compatibilidade com páginas antigas**
    ```
    1. Acessar /services (página antiga)
    2. Validar que ainda funciona normalmente
    3. Acessar /blackbox-targets (página antiga)
    4. Validar que ainda funciona normalmente
    
    Resultado esperado: ✓ Páginas antigas não foram afetadas
    ```

39. ✅ **Teste de adição de novo exporter**
    ```
    Cenário: Adicionar novo exporter "kafka-exporter" no Prometheus
    
    Passos:
    1. Adicionar job no prometheus.yml:
       ```yaml
       - job_name: 'kafka-exporter'
         consul_sd_configs:
           - server: 'localhost:8500'
             services: ['kafka-exporter']
         relabel_configs:
           - source_labels: [__meta_consul_service_metadata_company]
             target_label: company
       ```
    
    2. Clicar em "Sincronizar Cache" na interface
    
    3. Validar que:
       - Kafka exporter aparece automaticamente
       - É categorizado em "infrastructure-exporters"
       - Campos metadata são detectados
    
    Resultado esperado: ✓ Sistema detecta automaticamente
    ```

**TARDE: Documentação Final**

40. ✅ **Criar documentação de uso**
    ```bash
    cat > docs/DYNAMIC_MONITORING_PAGES.md << 'EOF'
    # Páginas de Monitoramento Dinâmicas
    
    ## Visão Geral
    
    O Skills Eye possui 4 páginas de monitoramento que funcionam 100% dinamicamente:
    
    1. **Network Probes** - Monitoramento de conectividade (ICMP, TCP, DNS)
    2. **Web Probes** - Monitoramento de aplicações web (HTTP, HTTPS)
    3. **System Exporters** - Monitoramento de sistemas (Node, Windows)
    4. **Database Exporters** - Monitoramento de bancos de dados (MySQL, PostgreSQL)
    
    ## Como Funciona
    
    ### Detecção Automática
    
    O sistema detecta automaticamente novos exporters adicionados no Prometheus:
    
    1. Jobs são extraídos do `prometheus.yml` via SSH
    2. Cada job é categorizado usando regras JSON do Consul KV
    3. Campos metadata são extraídos dos `relabel_configs`
    4. Tudo é armazenado em cache no Consul KV (5 minutos)
    
    ### Adicionar Novo Exporter
    
    Para adicionar um novo exporter:
    
    1. Configure no Prometheus:
       ```yaml
       - job_name: 'meu-novo-exporter'
         consul_sd_configs:
           - server: 'localhost:8500'
             services: ['meu-exporter']
         relabel_configs:
           - source_labels: [__meta_consul_service_metadata_company]
             target_label: company
       ```
    
    2. Recarregue o Prometheus:
       ```bash
       curl -X POST http://prometheus:9090/-/reload
       ```
    
    3. Sincronize o cache no Skills Eye:
       - Acesse qualquer página de monitoramento
       - Clique no botão "Sincronizar Cache"
       - Aguarde 2-3 segundos
    
    4. Pronto! O novo exporter aparecerá automaticamente na categoria apropriada.
    
    ### Adicionar Nova Categoria
    
    Se o sistema não categorizar corretamente, adicione uma regra no Consul KV:
    
    ```bash
    # Editar regras
    consul kv get skills/eye/monitoring-types/categorization/rules > rules.json
    
    # Adicionar nova regra
    vim rules.json
    # {
    #   "id": "meu_novo_tipo",
    #   "priority": 85,
    #   "category": "infrastructure-exporters",
    #   "conditions": {
    #     "job_name_pattern": "^meu.*"
    #   }
    # }
    
    # Salvar de volta
    consul kv put skills/eye/monitoring-types/categorization/rules @rules.json
    ```
    
    ## Troubleshooting
    
    ### Página não carrega dados
    
    1. Verificar que backend está rodando:
       ```bash
       curl http://localhost:5000/health
       ```
    
    2. Verificar cache KV:
       ```bash
       consul kv get skills/eye/monitoring-types/cache
       ```
    
    3. Forçar sincronização:
       - Clicar em "Sincronizar Cache"
       - Ou via API: `POST /api/v1/monitoring/sync-cache`
    
    ### Exporter não aparece
    
    1. Verificar que job está no Prometheus:
       ```bash
       curl http://prometheus:9090/api/v1/targets | jq
       ```
    
    2. Verificar categorização:
       ```bash
       curl "http://localhost:5000/api/v1/monitoring-types-dynamic/from-prometheus?server=ALL" | jq '.all_types[] | select(.job_name=="meu-job")'
       ```
    
    3. Se categorizado errado, adicionar regra (ver acima)
    
    ### Campos não aparecem
    
    1. Verificar metadata fields:
       ```bash
       curl http://localhost:5000/api/v1/metadata-fields/fields | jq
       ```
    
    2. Verificar relabel_configs no Prometheus:
       ```yaml
       # prometheus.yml deve ter:
       relabel_configs:
         - source_labels: [__meta_consul_service_metadata_MEU_CAMPO]
           target_label: meu_campo
       ```
    
    3. Sincronizar metadata fields:
       ```bash
       curl -X POST http://localhost:5000/api/v1/metadata-fields/sync
       ```
    EOF
    ```

41. ✅ **Atualizar README.md**
    ```bash
    # Adicionar seção no README.md do projeto
    cat >> README.md << 'EOF'
    
    ## Páginas de Monitoramento Dinâmicas
    
    O Skills Eye possui 4 páginas de monitoramento que funcionam 100% dinamicamente:
    
    - **Network Probes** (`/monitoring/network-probes`) - ICMP, TCP, DNS, SSH
    - **Web Probes** (`/monitoring/web-probes`) - HTTP, HTTPS, POST
    - **System Exporters** (`/monitoring/system-exporters`) - Node, Windows, SNMP
    - **Database Exporters** (`/monitoring/database-exporters`) - MySQL, PostgreSQL, Redis, MongoDB
    
    ### Características
    
    - ✅ **100% Dinâmico** - Detecta automaticamente novos exporters
    - ✅ **Zero Hardcode** - Tudo vem do Prometheus e Consul KV
    - ✅ **Cache Inteligente** - 5 minutos de TTL, sincronização sob demanda
    - ✅ **Regras JSON** - Categorização configurável via KV
    
    Veja [documentação completa](docs/DYNAMIC_MONITORING_PAGES.md) para mais detalhes.
    EOF
    ```

42. ✅ **Commit final**
    ```bash
    git add .
    git commit -m "docs: Adicionar documentação completa das páginas dinâmicas

    - Guia de uso detalhado
    - Troubleshooting
    - Exemplos de adição de novos exporters
    - Atualizar README.md"
    
    git push origin feature/dynamic-monitoring-pages
    ```

---

### FASE 5: Deploy e Produção (Dias 11-12)

#### Dia 11: ⭐ Migração de Categorização (NOVO)

**OBJETIVO:** Migrar sistema de categorização existente para usar regras JSON no Consul KV

**MANHÃ: Análise do Sistema Atual**

43. ✅ **Identificar lógica de categorização atual**
    ```bash
    # Procurar por lógica hardcoded de categorização
    cd /home/adrianofante/projetos/Skills-Eye/backend
    grep -r "categoria" --include="*.py" .
    grep -r "category" --include="*.py" .
    
    # Identificar onde Services e BlackboxTargets categorizam
    # Objetivo: Migrar essa lógica para JSON no KV
    ```

44. ✅ **Mapear categorias existentes**
    ```python
    # Criar mapeamento das categorias atuais:
    categorias_atuais = {
        "services": [
            {"pattern": "node-exporter", "categoria": "system"},
            {"pattern": "mysql-exporter", "categoria": "database"},
            {"pattern": "blackbox", "categoria": "network"},
            # ... etc
        ]
    }
    
    # Salvar em: /tmp/categorias_mapeadas.json
    ```

**TARDE: Implementação da Migração**

45. ✅ **Criar regras JSON no Consul KV**
    ```python
    # Script: migrate_categorization_to_kv.py
    import json
    import httpx
    
    # Ler categorização mapeada
    with open('/tmp/categorias_mapeadas.json') as f:
        categorias = json.load(f)
    
    # Popular no Consul KV
    CONSUL_URL = "http://172.16.1.26:8500"
    for service_type, rules in categorias.items():
        key = f"skills/eye/monitoring-types/rules/{service_type}"
        data = {
            "rules": rules,
            "version": "1.0",
            "migrated_from": "hardcoded_logic",
            "created_at": "2025-01-11"
        }
        
        response = httpx.put(
            f"{CONSUL_URL}/v1/kv/{key}",
            json=data
        )
        print(f"✓ Migrado: {service_type}")
    ```

46. ✅ **Atualizar Services.tsx e BlackboxTargets.tsx**
    ```typescript
    // ANTES (hardcoded):
    const categoria = getCategoriaPorNome(service.name);
    
    // DEPOIS (dinâmico):
    const categoria = await consulAPI.getCategoria(service.name);
    ```

47. ✅ **Testes de regressão**
    ```bash
    # Validar que categorização funciona igual:
    # 1. Abrir /services
    # 2. Validar que todas as categorias aparecem corretamente
    # 3. Comparar com versão anterior (screenshot)
    
    # Critério de sucesso: Zero diferenças visuais
    ```

#### Dia 12: Deploy

**MANHÃ: Preparação para Deploy**

48. ✅ **Criar Pull Request**
    ```
    Título: feat: Implementar páginas de monitoramento 100% dinâmicas
    
    Descrição:
    Este PR adiciona 4 novas páginas de monitoramento que funcionam de forma 100% dinâmica, 
    detectando automaticamente novos exporters do Prometheus.
    
    ## Mudanças
    
    ### Backend
    - Adicionar ConsulKVConfigManager com cache TTL
    - Adicionar CategorizationRuleEngine baseado em JSON
    - Adicionar DynamicQueryBuilder com Jinja2
    - Modificar monitoring_types_dynamic para usar cache KV
    - Adicionar endpoint unificado /monitoring/data
    
    ### Frontend
    - Adicionar DynamicMonitoringPage (componente base único)
    - Modificar useMetadataFields para aceitar contexto dinâmico
    - Adicionar 4 novas rotas
    - Atualizar menu de navegação
    
    ## Testes
    
    - ✅ Testes unitários backend (100% cobertura nos novos módulos)
    - ✅ Testes E2E frontend (todas as 4 páginas)
    - ✅ Teste de performance (cache <100ms, extração ~2s)
    - ✅ Teste de compatibilidade (páginas antigas funcionam)
    
    ## Documentação
    
    - ✅ DYNAMIC_MONITORING_PAGES.md
    - ✅ README.md atualizado
    - ✅ Código comentado em português
    
    ## Breaking Changes
    
    Nenhum. Páginas antigas (Services, BlackboxTargets) continuam funcionando.
    
    ## Closes
    
    Closes #123 (se houver issue)
    ```

44. ✅ **Code review**
    - Solicitar review de pelo menos 2 pessoas
    - Aguardar aprovação
    - Corrigir issues apontados

**TARDE: Deploy em Produção**

45. ✅ **Merge para main**
    ```bash
    # Após aprovação do PR
    git checkout main
    git pull origin main
    git merge feature/dynamic-monitoring-pages
    git push origin main
    ```

46. ✅ **Deploy backend**
    ```bash
    # SSH no servidor
    ssh user@172.16.1.26
    
    # Ir para pasta do projeto
    cd /opt/skills-eye
    
    # Pull da main
    git pull origin main
    
    # Ativar venv e instalar dependências
    source venv/bin/activate
    pip install -r requirements.txt
    
    # Reiniciar backend
    sudo systemctl restart skills-eye-backend
    
    # Verificar logs
    sudo journalctl -u skills-eye-backend -f
    ```

47. ✅ **Deploy frontend**
    ```bash
    # Ainda no servidor
    cd /opt/skills-eye/frontend
    
    # Instalar dependências
    npm install
    
    # Build de produção
    npm run build
    
    # Copiar para nginx (se aplicável)
    sudo cp -r dist/* /var/www/skills-eye/
    
    # Reiniciar nginx
    sudo systemctl restart nginx
    ```

48. ✅ **Validação pós-deploy**
    ```
    ✓ Acessar https://skills-eye.skillsit.com.br
    ✓ Validar que 4 novas páginas carregam
    ✓ Validar que dados são corretos
    ✓ Validar que cache funciona
    ✓ Validar que não há erros no console
    ```

49. ✅ **Monitoramento**
    ```bash
    # Configurar alertas (se aplicável)
    # - Alert se endpoint /monitoring/data > 2s
    # - Alert se cache hit rate < 80%
    # - Alert se extração SSH > 5s
    ```

50. ✅ **Comunicar usuários**
    ```
    Assunto: [Skills Eye] Novas páginas de monitoramento disponíveis!
    
    Olá equipe,
    
    Temos o prazer de anunciar 4 novas páginas de monitoramento no Skills Eye:
    
    1. Network Probes - Monitoramento de conectividade
    2. Web Probes - Monitoramento de aplicações web
    3. System Exporters - Monitoramento de sistemas
    4. Database Exporters - Monitoramento de bancos de dados
    
    Principais features:
    - ✅ 100% dinâmico - detecta automaticamente novos exporters
    - ✅ Filtros avançados
    - ✅ Colunas configuráveis
    - ✅ Cache inteligente
    
    As páginas antigas (Services, Blackbox Targets) continuam disponíveis como backup.
    
    Acesse: https://skills-eye.skillsit.com.br
    
    Dúvidas? Veja a documentação: https://...
    
    Att,
    Equipe Skills Eye
    ```

---

## ✅ VALIDAÇÃO E TESTES

### 7.1 Checklist de Validação Completo

#### Backend

```markdown
- [ ] ConsulKVConfigManager
  - [ ] Salva e recupera dados do KV
  - [ ] Cache funciona (TTL 5min)
  - [ ] Invalidação de cache funciona
  - [ ] Testes unitários passam
  
- [ ] CategorizationRuleEngine
  - [ ] Carrega regras do KV
  - [ ] Categoriza jobs corretamente
  - [ ] Fallback para custom-exporters
  - [ ] Testes unitários passam
  
- [ ] DynamicQueryBuilder
  - [ ] Renderiza templates Jinja2
  - [ ] Substitui variáveis corretamente
  - [ ] Parâmetros opcionais funcionam
  - [ ] Testes unitários passam
  
- [ ] monitoring_types_dynamic.py
  - [ ] Cache KV funciona
  - [ ] Extração SSH funciona
  - [ ] Usa CategorizationRuleEngine
  - [ ] Endpoint /from-prometheus retorna dados corretos
  
- [ ] monitoring_unified.py
  - [ ] Endpoint /data funciona para todas categorias
  - [ ] Filtra por servidor
  - [ ] Executa queries PromQL
  - [ ] Retorna dados formatados
  - [ ] Endpoint /sync-cache funciona
```

#### Frontend

```markdown
- [ ] DynamicMonitoringPage
  - [ ] Renderiza para todas as 4 categorias
  - [ ] Colunas são dinâmicas
  - [ ] Filtros funcionam
  - [ ] Busca avançada funciona
  - [ ] Sincronizar cache funciona
  
- [ ] useMetadataFields
  - [ ] Aceita contexto dinâmico
  - [ ] Cache funciona (5min)
  - [ ] Filtra campos corretamente
  
- [ ] Rotas
  - [ ] /monitoring/network-probes carrega
  - [ ] /monitoring/web-probes carrega
  - [ ] /monitoring/system-exporters carrega
  - [ ] /monitoring/database-exporters carrega
  
- [ ] Menu
  - [ ] Novo grupo "Monitoramento por Tipo" aparece
  - [ ] 4 itens dentro do grupo
  - [ ] Navegação funciona
```

#### Integração

```markdown
- [ ] End-to-End
  - [ ] Usuário acessa /monitoring/network-probes
  - [ ] Dados carregam do backend
  - [ ] Filtro de company funciona
  - [ ] Sincronizar cache atualiza dados
  - [ ] Páginas antigas ainda funcionam
  
- [ ] Performance
  - [ ] Cache hit < 100ms
  - [ ] Cache miss ~ 2-3s
  - [ ] Carga de 100 requests funciona
  
- [ ] Compatibilidade
  - [ ] Firefox
  - [ ] Chrome
  - [ ] Edge
  - [ ] Mobile (responsivo)
```

---

## 📚 DOCUMENTAÇÃO NECESSÁRIA

### 8.1 Documentos a Criar

1. **DYNAMIC_MONITORING_PAGES.md** - Guia completo de uso
2. **API_UNIFIED_ENDPOINT.md** - Documentação da API unificada
3. **CATEGORIZATION_RULES.md** - Como funcionam as regras
4. **TROUBLESHOOTING.md** - Solução de problemas comuns
5. **CHANGELOG.md** - Atualizar com novas features

### 8.2 Documentação em Código

**TODOS os arquivos novos devem ter:**

```python
"""
Nome do Módulo - Descrição Breve

RESPONSABILIDADES:
- Responsabilidade 1
- Responsabilidade 2

DEPENDÊNCIAS:
- Módulo X
- Biblioteca Y

EXEMPLO DE USO:
```python
# Código de exemplo
```

TESTES:
- backend/tests/test_nome_modulo.py
"""
```

---

## 🎉 CONCLUSÃO

Este plano fornece **TODAS as informações necessárias** para implementar o sistema de monitoramento 100% dinâmico do Skills Eye.

### ✅ Checklist Final

- ✅ **Análise do projeto real** - baseado em código existente
- ✅ **Recomendações técnicas** - embasadas em pesquisa web
- ✅ **Componentes detalhados** - código completo fornecido
- ✅ **Plano de implementação** - passo a passo de 11 dias
- ✅ **Testes e validação** - checklists completos
- ✅ **Documentação** - guias e exemplos

### 📊 Estimativas

- **Tempo total:** 11 dias úteis (2,2 semanas)
- **Linhas de código:** ~2000 (backend + frontend)
- **Arquivos novos:** 8 (4 backend + 4 frontend/modificados)
- **Testes unitários:** 15+ cenários
- **Performance esperada:** <100ms (cache hit), ~2s (cache miss)

### 🚀 Próximos Passos

1. **Revisar documento completo** - garantir entendimento
2. **Preparar ambiente** - Fase 1, Dia 1
3. **Começar implementação** - seguir plano passo a passo
4. **Validar constantemente** - após cada fase
5. **Deploy com confiança** - após todos os testes passarem

---

**Este documento é definitivo e está pronto para ser usado por outra IA ou desenvolvedor para implementar o sistema completo.**

**Dúvidas?** Consulte as seções específicas ou entre em contato.

**Boa implementação! 🚀**