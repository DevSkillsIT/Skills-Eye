# API Reference - Skills Eye

**Data de Atualização:** 2025-11-06
**Versão da API:** v1
**Base URL:** `http://localhost:5000/api/v1`

---

## Índice

- [Introdução](#introdução)
- [Filosofia do Sistema](#filosofia-do-sistema)
- [Autenticação](#autenticação)
- [Endpoints por Módulo](#endpoints-por-módulo)
  - [Services](#services-services)
  - [Monitoring Types (Dinâmico)](#monitoring-types-monitoring-types-dynamic)
  - [Metadata Fields](#metadata-fields-metadata-fields)
  - [Blackbox Targets](#blackbox-targets-blackbox)
  - [Search (Busca Avançada)](#search-search)
  - [Prometheus Config](#prometheus-config-prometheus-config)
  - [Dashboard](#dashboard-dashboard)
  - [Health & Status](#health-health)
  - [Reference Values](#reference-values-reference-values)
  - [Audit](#audit-audit)
  - [KV Store](#kv-store-kv)
  - [Presets](#presets-presets)
  - [Nodes](#nodes-nodes)
  - [Settings](#settings-settings)
  - [Installer](#installer-installer)
  - [Optimized Endpoints](#optimized-endpoints-optimized-endpoints)

---

## Introdução

A API do Skills Eye é uma API RESTful desenvolvida em FastAPI (Python 3.12) que fornece gerenciamento completo de serviços Consul e infraestrutura de monitoramento Prometheus.

**Principais Características:**
- API assíncrona com alta performance
- Documentação Swagger automática: `http://localhost:5000/docs`
- Validação de dados com Pydantic
- Cache inteligente para reduzir latência
- Operações em lote (bulk operations)
- Sincronização automática com Prometheus via SSH

---

## Filosofia do Sistema

**⚡ SISTEMA 100% DINÂMICO - ZERO HARDCODE**

O Skills Eye segue uma filosofia fundamental que o diferencia de sistemas tradicionais:

### Princípios Fundamentais:

1. **Extração Dinâmica do Prometheus**
   - Campos metadata são extraídos DIRETAMENTE dos arquivos `prometheus.yml`, `blackbox.yml`, etc
   - Sistema detecta automaticamente novos campos quando o Prometheus é atualizado
   - Não há JSONs hardcoded - tudo vem do próprio Prometheus

2. **Tipos de Monitoramento Auto-Detectados**
   - Monitoring types são inferidos dos `scrape_configs` do prometheus.yml
   - Sistema categoriza automaticamente: blackbox probes, exporters, custom jobs
   - Adicionar novo tipo = adicionar job no Prometheus (sem tocar no código)

3. **Multi-Servidor com SSH**
   - Conecta via SSH em múltiplos servidores Prometheus
   - Edita configurações YAML preservando 100% comentários
   - Valida mudanças com `promtool` antes de aplicar

4. **Cache Inteligente**
   - Campos metadata salvos no Consul KV após extração
   - Cold start evita SSH repetidos (lê do KV primeiro)
   - TTL configurável para refresh automático

**Resultado:** Sistema sempre sincronizado com o Prometheus, sem manutenção manual de metadados!

---

## Autenticação

### Endpoints Públicos
A maioria dos endpoints **não requer autenticação** para consultas.

### Endpoints Protegidos
Apenas endpoints de **instalação remota** (`/installer/*`) requerem HTTP Basic Auth:

```http
Authorization: Basic base64(username:password)
```

**Credenciais:** Configuradas no Consul KV: `skills/cm/settings/credentials`

---

## Endpoints por Módulo

---

## Services (`/services`)

Gerenciamento de serviços registrados no Consul.

### `GET /services`
Lista todos os serviços com metadados completos.

**Query Parameters:**
- `node_addr` (optional): IP do nó ou `ALL` para todos os nós
- `module` (optional): Filtrar por módulo (icmp, http_2xx, etc)
- `company` (optional): Filtrar por empresa
- `project` (optional): Filtrar por projeto
- `env` (optional): Filtrar por ambiente (prod, dev, staging)

**Response:**
```json
{
  "success": true,
  "data": {
    "service-id-1": {
      "ID": "service-id-1",
      "Service": "blackbox_exporter",
      "Tags": ["icmp", "prod"],
      "Meta": {
        "module": "icmp",
        "company": "Ramada",
        "env": "prod",
        "name": "gateway-principal"
      },
      "Address": "172.16.1.1",
      "Port": 9115
    }
  },
  "total": 150,
  "message": "Listados 150 serviços"
}
```

---

### `GET /services/catalog/names`
Retorna lista de nomes de serviços únicos do catálogo Consul.

**Response:**
```json
{
  "success": true,
  "data": ["selfnode_exporter", "blackbox_exporter", "node_exporter"],
  "total": 3
}
```

---

### `GET /services/metadata/unique-values`
Obtém valores únicos de um campo metadata.

**Query Parameters:**
- `field` (required): Campo (module, company, project, env)

**Response:**
```json
{
  "success": true,
  "field": "company",
  "values": ["Ramada", "ACME", "Skillsit"],
  "total": 3
}
```

---

### `GET /services/search/by-metadata`
Busca serviços por filtros de metadados.

**Query Parameters:**
- `module`, `company`, `project`, `env`, `name`, `instance`, `node_addr` (all optional)

**Response:** Similar ao `GET /services` mas filtrado

---

### `GET /services/{service_id:path}`
Obtém detalhes de um serviço específico.

**Path Parameters:**
- `service_id`: ID do serviço (pode conter `/`, `@`, caracteres especiais)

**Query Parameters:**
- `node_addr` (optional): Nó onde buscar

**Response:**
```json
{
  "success": true,
  "data": { /* service details */ },
  "service_id": "blackbox/ramada/prod/gateway"
}
```

---

### `POST /services`
Cria novo serviço no Consul.

**Request Body:**
```json
{
  "id": "optional-custom-id",
  "name": "blackbox_exporter",
  "address": "172.16.1.100",
  "port": 9115,
  "tags": ["prod", "icmp"],
  "Meta": {
    "module": "icmp",
    "company": "Ramada",
    "project": "infraestrutura",
    "env": "prod",
    "name": "firewall-principal",
    "instance": "192.168.1.1"
  },
  "node_addr": "172.16.1.26"
}
```

**Validações Automáticas:**
- Campos obrigatórios (module, company, project, env, name, instance)
- Formato correto do instance (URL/IP/hostname baseado no módulo)
- Detecção de duplicatas (mesma combinação de campos)
- Sanitização automática do ID (remove caracteres inválidos)

**Response:**
```json
{
  "success": true,
  "message": "Serviço criado com sucesso",
  "service_id": "blackbox_ramada_prod_firewall-principal",
  "data": { /* service data */ }
}
```

---

### `PUT /services/{service_id:path}`
Atualiza serviço existente.

**Request Body:** Campos a atualizar (parcial ou completo)

**Response:** Similar ao POST

---

### `DELETE /services/{service_id:path}`
Remove serviço do Consul.

**Query Parameters:**
- `node_addr` (optional): Nó onde remover

**Response:**
```json
{
  "success": true,
  "message": "Serviço removido com sucesso",
  "service_id": "blackbox/..."
}
```

---

### `POST /services/bulk/register`
Registra múltiplos serviços em lote.

**Request Body:**
```json
[
  { /* service 1 */ },
  { /* service 2 */ }
]
```

**Response:**
```json
{
  "success": true,
  "message": "Registrados 5/6 serviços",
  "results": {
    "service-1": true,
    "service-2": false
  },
  "summary": {
    "total": 6,
    "success": 5,
    "failed": 1
  }
}
```

---

### `DELETE /services/bulk/deregister`
Remove múltiplos serviços em lote.

**Request Body:**
```json
{
  "service_ids": ["service-1", "service-2"],
  "node_addr": "172.16.1.26"
}
```

---

## Monitoring Types (`/monitoring-types-dynamic`)

**SISTEMA DINÂMICO:** Tipos de monitoramento extraídos DIRETAMENTE do prometheus.yml!

### `GET /monitoring-types-dynamic/from-prometheus`
Extrai tipos de monitoramento dos jobs do Prometheus.

**Query Parameters:**
- `server` (optional): Hostname do servidor ou `ALL` para todos

**Response:**
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
      "total": 15,
      "prometheus_file": "/etc/prometheus/prometheus.yml"
    }
  },
  "categories": [
    {
      "category": "network-probes",
      "display_name": "Network Probes (Rede)",
      "types": [ /* ... */ ]
    },
    {
      "category": "system-exporters",
      "display_name": "Exporters: Sistemas",
      "types": [ /* ... */ ]
    }
  ],
  "all_types": [ /* união de todos os tipos */ ],
  "total_types": 15,
  "total_servers": 3
}
```

**Categorias Auto-Detectadas:**
- `network-probes`: ICMP, TCP, DNS, SSH
- `web-probes`: HTTP 2xx, HTTP 4xx, HTTPS, POST
- `system-exporters`: Node Exporter, Windows Exporter, SNMP
- `database-exporters`: MySQL, PostgreSQL, Redis, MongoDB
- `infrastructure-exporters`: HAProxy, Nginx, Kafka, RabbitMQ
- `hardware-exporters`: IPMI, Dell HW
- `network-devices`: MikroTik (MKTXP)
- `custom-exporters`: Outros

**Como Funciona:**
1. Conecta via SSH nos servidores Prometheus
2. Lê `prometheus.yml` de cada servidor
3. Para cada job em `scrape_configs`:
   - Verifica se tem `consul_sd_configs` (service discovery)
   - Extrai `relabel_configs` para descobrir campos metadata
   - Infere categoria baseado no job_name/metrics_path
   - Detecta módulo blackbox (se aplicável)
4. Retorna tipos consolidados de todos os servidores

**Adicionar Novo Tipo:**
```yaml
# Basta adicionar job no prometheus.yml:
scrape_configs:
  - job_name: 'meu-custom-exporter'
    consul_sd_configs:
      - server: 'localhost:8500'
        services: ['meu-custom-exporter']
    relabel_configs:
      - source_labels: [__meta_consul_service_metadata_company]
        target_label: company
      - source_labels: [__meta_consul_service_metadata_env]
        target_label: env
```

O sistema detecta automaticamente na próxima chamada!

---

### `GET /monitoring-types-dynamic/health`
Health check do sistema de tipos dinâmicos.

**Response:**
```json
{
  "success": true,
  "status": "healthy",
  "servers_configured": 3,
  "message": "Monitoring Types Dynamic API is operational"
}
```

---

## Metadata Fields (`/metadata-fields`)

**SISTEMA DINÂMICO:** Campos extraídos dos `relabel_configs` do Prometheus!

### `GET /metadata-fields/servers`
Lista servidores Prometheus configurados.

**Cache:** 5 minutos (evita SSH repetidos)

**Response:**
```json
{
  "success": true,
  "servers": [
    {
      "id": "172.16.1.26:5522",
      "hostname": "172.16.1.26",
      "port": 5522,
      "username": "root",
      "type": "master",
      "consul_node_name": "glpi-grafana-prometheus",
      "display_name": "172.16.1.26 - glpi-grafana-prometheus"
    },
    {
      "id": "172.16.200.14:22",
      "hostname": "172.16.200.14",
      "port": 22,
      "username": "root",
      "type": "slave",
      "consul_node_name": "prometheus-slave-1",
      "display_name": "172.16.200.14 - prometheus-slave-1"
    }
  ],
  "total": 3,
  "master": { /* primeiro servidor */ }
}
```

---

### `GET /metadata-fields/sync-status`
Verifica sincronização de campos com prometheus.yml.

**Query Parameters:**
- `server_id` (required): ID do servidor (ex: `172.16.1.26:5522`)

**Response:**
```json
{
  "success": true,
  "server_id": "172.16.1.26:5522",
  "server_hostname": "172.16.1.26",
  "fields": [
    {
      "name": "company",
      "display_name": "Empresa",
      "sync_status": "synced",
      "prometheus_target_label": "company",
      "metadata_source_label": "__meta_consul_service_metadata_company",
      "message": "Campo sincronizado corretamente"
    },
    {
      "name": "new_field",
      "display_name": "Novo Campo",
      "sync_status": "missing",
      "prometheus_target_label": null,
      "metadata_source_label": "__meta_consul_service_metadata_new_field",
      "message": "Campo não encontrado no prometheus.yml"
    }
  ],
  "total_synced": 15,
  "total_outdated": 2,
  "total_missing": 1,
  "total_error": 0,
  "prometheus_file_path": "/etc/prometheus/prometheus.yml",
  "checked_at": "2025-11-06T10:30:00",
  "fallback_used": false
}
```

**Status Possíveis:**
- `synced`: Campo sincronizado corretamente
- `missing`: Campo existe no JSON mas não no Prometheus
- `outdated`: target_label diferente do esperado
- `error`: Erro ao verificar (ex: servidor sem Prometheus)

---

### `GET /metadata-fields/preview-changes/{field_name}`
Preview de mudanças antes de sincronizar campo.

**Query Parameters:**
- `server_id` (required): ID do servidor

**Response:**
```json
{
  "success": true,
  "field_name": "new_field",
  "current_config": null,
  "new_config": {
    "source_labels": ["__meta_consul_service_metadata_new_field"],
    "target_label": "new_field",
    "action": "replace"
  },
  "diff_text": "...",
  "affected_jobs": ["icmp", "http_2xx", "node-exporter"],
  "will_create": true
}
```

---

### `POST /metadata-fields/batch-sync`
Sincroniza múltiplos campos de uma vez.

**Request Body:**
```json
{
  "field_names": ["company", "env", "new_field"],
  "server_id": "172.16.1.26:5522",
  "dry_run": false
}
```

**Response:**
```json
{
  "success": true,
  "server_id": "172.16.1.26:5522",
  "results": [
    {
      "field_name": "new_field",
      "success": true,
      "message": "Campo 'new_field' sincronizado com sucesso (3 job(s) afetado(s))",
      "changes_applied": 3
    }
  ],
  "total_processed": 3,
  "total_success": 3,
  "total_failed": 0,
  "duration_seconds": 2.5
}
```

**Processo de Sincronização:**
1. Lê prometheus.yml via SSH
2. Usa **manipulação textual** (não YAML parsing) para preservar 100% formatação
3. Insere `relabel_configs` nos jobs que tem `consul_sd_configs`
4. Cria backup com timestamp
5. Valida com `promtool check config`
6. Aplica mudanças (move arquivo temporário)
7. Restaura permissões `prometheus:prometheus`

---

### `GET /metadata-fields/`
Lista todos os campos metadata configurados.

**Query Parameters:**
- `category` (optional): Filtrar por categoria
- `required_only` (optional): Apenas obrigatórios
- `show_in_table_only` (optional): Apenas visíveis em tabelas

**Response:**
```json
{
  "success": true,
  "fields": [
    {
      "name": "company",
      "display_name": "Empresa",
      "description": "Nome da empresa",
      "source_label": "__meta_consul_service_metadata_company",
      "field_type": "string",
      "required": true,
      "show_in_table": true,
      "show_in_form": true,
      "order": 1,
      "category": "infrastructure"
    }
  ],
  "categories": {
    "infrastructure": { "name": "Infraestrutura", "icon": "🏗️" }
  },
  "total": 20,
  "version": "2.0.0",
  "last_updated": "2025-11-06T10:00:00"
}
```

---

### `POST /metadata-fields/`
Cria novo campo metadata.

**Request Body:**
```json
{
  "field": {
    "name": "new_field",
    "display_name": "Novo Campo",
    "source_label": "__meta_consul_service_metadata_new_field",
    "field_type": "string",
    "required": false,
    "show_in_table": true
  },
  "sync_prometheus": true,
  "apply_to_jobs": null
}
```

---

### `POST /metadata-fields/sync-to-prometheus/{field_name}`
Sincroniza campo específico com prometheus.yml.

**Request Body:**
```json
{
  "apply_to_jobs": ["icmp", "http_2xx"]
}
```

---

### `POST /metadata-fields/replicate-to-slaves`
Replica configurações do master para slaves.

**Request Body:**
```json
{
  "source_server": null,
  "target_servers": ["172.16.200.14:22"]
}
```

---

### `POST /metadata-fields/restart-prometheus`
Reinicia Prometheus em servidores.

**Request Body:**
```json
{
  "server_ids": ["172.16.1.26:5522"]
}
```

---

## Blackbox Targets (`/blackbox`)

Gerenciamento de alvos Blackbox Exporter.

### `GET /blackbox/`
Lista targets com filtros.

**Query Parameters:**
- `module`, `company`, `project`, `env`, `group`, `node`

---

### `POST /blackbox/`
Cria novo target blackbox.

**Request Body:**
```json
{
  "module": "icmp",
  "company": "Ramada",
  "project": "infraestrutura",
  "env": "prod",
  "name": "gateway-principal",
  "instance": "192.168.1.1",
  "group": "network-devices",
  "interval": "30s",
  "timeout": "10s",
  "enabled": true
}
```

---

### `POST /blackbox/import`
Importa targets de CSV/XLSX.

**Request:** Multipart form-data com arquivo

---

### `POST /blackbox/groups`
Cria grupo de organização.

---

### `POST /blackbox/bulk/enable-disable`
Habilita/desabilita múltiplos targets.

---

## Search (`/search`)

Busca avançada com múltiplos operadores.

### `POST /search/advanced`
Busca com condições complexas.

**Request Body:**
```json
{
  "conditions": [
    {"field": "Meta.company", "operator": "eq", "value": "Ramada"},
    {"field": "Meta.env", "operator": "in", "value": ["prod", "staging"]}
  ],
  "logical_operator": "and",
  "sort_by": "Meta.name",
  "page": 1,
  "page_size": 20
}
```

**Operadores Suportados:**
- `eq`, `ne`: Igualdade
- `contains`, `starts_with`, `ends_with`: String
- `regex`: Expressão regular
- `in`, `not_in`: Valores em lista
- `gt`, `lt`, `gte`, `lte`: Comparação numérica

---

### `POST /search/text`
Busca full-text.

**Request Body:**
```json
{
  "text": "ramada",
  "page": 1,
  "page_size": 20
}
```

---

### `GET /search/filters`
Retorna opções de filtros disponíveis.

---

### `GET /search/unique-values`
Valores únicos de um campo.

**Query Parameters:**
- `field`: Campo (ex: `Meta.company`)

---

### `GET /search/by-company/{company}`
Busca rápida por empresa.

---

### `GET /search/by-env/{env}`
Busca rápida por ambiente.

---

### `GET /search/stats`
Estatísticas agregadas.

---

## Prometheus Config (`/prometheus-config`)

Editor multi-servidor de configurações YAML via SSH.

### `GET /prometheus-config/files`
Lista arquivos de configuração disponíveis.

**Query Parameters:**
- `service` (optional): prometheus, blackbox, alertmanager
- `hostname` (optional): Filtrar por servidor específico

---

### `GET /prometheus-config/file/raw-content`
Lê conteúdo RAW do arquivo via SSH.

**Query Parameters:**
- `file_path` (required): Path completo (ex: `/etc/prometheus/prometheus.yml`)
- `hostname` (optional): Servidor específico

**Response:**
```json
{
  "success": true,
  "file_path": "/etc/prometheus/prometheus.yml",
  "content": "# Global config\nglobal:\n  scrape_interval: 15s...",
  "size_bytes": 12345,
  "last_modified": "2025-10-28T23:45:00",
  "host": "172.16.1.26",
  "port": 5522
}
```

---

### `POST /prometheus-config/file/raw-content`
Salva conteúdo RAW no arquivo via SSH.

**Request Body:**
```json
{
  "file_path": "/etc/prometheus/prometheus.yml",
  "content": "# Edited config...",
  "hostname": "172.16.1.26"
}
```

**Fluxo de Segurança:**
1. Valida sintaxe YAML
2. Cria backup timestamped
3. Escreve arquivo temporário
4. Valida com `promtool check config`
5. Move para destino final
6. Restaura permissões

**Response:**
```json
{
  "success": true,
  "message": "Arquivo salvo com sucesso",
  "backup_path": "/etc/prometheus/prometheus.yml.backup-20251106-103000",
  "validation_result": {
    "valid": true,
    "message": "Validação promtool passou"
  }
}
```

---

### `POST /prometheus-config/service/reload`
Recarrega serviços Prometheus/Blackbox/Alertmanager.

**Request Body:**
```json
{
  "host": "172.16.1.26",
  "file_path": "/etc/prometheus/prometheus.yml"
}
```

**Lógica de Reload:**
- `prometheus.yml` → reload prometheus
- `blackbox.yml` → reload prometheus-blackbox-exporter + prometheus
- `alertmanager.yml` → reload alertmanager

**Response:**
```json
{
  "success": true,
  "message": "Serviço(s) prometheus recarregado(s) com sucesso",
  "services": [
    {
      "service": "prometheus",
      "success": true,
      "method": "reload",
      "status": "active",
      "previous_status": "active"
    }
  ]
}
```

---

### `GET /prometheus-config/fields`
Extrai campos metadata de TODOS os servidores.

**Query Parameters:**
- `enrich_with_values` (optional, default: true): Adicionar valores únicos do Consul
- `force_refresh` (optional, default: false): Forçar re-extração (ignora KV cache)

**Otimização Cold Start:**
1. Tenta ler do Consul KV primeiro (instantâneo)
2. Se não existir ou `force_refresh=true`, extrai via SSH
3. Processa 3 servidores EM PARALELO (ThreadPoolExecutor)
4. Salva automaticamente no KV para próximas chamadas

**Response:**
```json
{
  "success": true,
  "fields": [
    {
      "name": "company",
      "display_name": "Empresa",
      "source_label": "__meta_consul_service_metadata_company",
      "field_type": "string",
      "available_values": ["Ramada", "ACME", "Skillsit"]
    }
  ],
  "total": 20,
  "last_updated": "2025-11-06T10:00:00",
  "server_status": [
    {
      "hostname": "172.16.1.26",
      "success": true,
      "from_cache": false,
      "files_count": 3,
      "fields_count": 15,
      "duration_ms": 250
    }
  ],
  "total_servers": 3,
  "successful_servers": 3,
  "from_cache": false
}
```

---

### `GET /prometheus-config/job-names`
Lista job_names do prometheus.yml.

**Query Parameters:**
- `hostname` (optional): Servidor específico (default: master)

**Cache:** 5 minutos

**Response:**
```json
{
  "success": true,
  "job_names": ["selfnode_exporter_rio", "blackbox_remote_rmd_ldc", "icmp"],
  "total": 15,
  "hostname": "172.16.1.26",
  "file_path": "/etc/prometheus/prometheus.yml",
  "from_cache": false
}
```

---

### `GET /prometheus-config/global`
Configuração global do prometheus.yml.

**Query Parameters:**
- `hostname` (optional): Servidor específico

**Response:**
```json
{
  "success": true,
  "scrape_interval": "15s",
  "evaluation_interval": "15s",
  "external_labels": {
    "site": "palmas",
    "datacenter": "genesis-dtc",
    "cluster": "prometheus"
  },
  "hostname": "172.16.1.26",
  "file_path": "/etc/prometheus/prometheus.yml"
}
```

---

### `GET /prometheus-config/alertmanager/routes`
Extrai rotas do alertmanager.yml.

---

### `GET /prometheus-config/alertmanager/receivers`
Extrai receptores do alertmanager.yml.

---

## Dashboard (`/dashboard`)

Métricas agregadas para dashboard.

### `GET /dashboard/metrics`
Endpoint super otimizado com cache de 30s.

**Response:**
```json
{
  "total_services": 150,
  "blackbox_targets": 80,
  "exporters": 70,
  "active_nodes": 3,
  "total_nodes": 3,
  "health": {
    "passing": 140,
    "warning": 8,
    "critical": 2
  },
  "by_env": {
    "prod": 100,
    "dev": 30,
    "staging": 20
  },
  "by_datacenter": {
    "dc1": 150
  },
  "recent_changes": [ /* últimos 10 eventos */ ],
  "load_time_ms": 15
}
```

---

### `POST /dashboard/clear-cache`
Limpa cache do dashboard.

---

## Health (`/health`)

### `GET /health/status`
Status geral do sistema.

---

### `GET /health/connectivity`
Testa conectividade com Consul, Prometheus, Grafana, Blackbox.

**Response:**
```json
{
  "success": true,
  "services": {
    "consul": {"status": "online", "code": 200},
    "prometheus": {"status": "online", "code": 200},
    "grafana": {"status": "online", "code": 200},
    "blackbox": {"status": "offline", "code": 0}
  },
  "main_server": "172.16.1.26"
}
```

---

## Reference Values (`/reference-values`)

Sistema de auto-cadastro/retroalimentação para valores de campos.

### `POST /reference-values/ensure`
Garante que valor existe (auto-cadastro).

**Request Body:**
```json
{
  "field_name": "company",
  "value": "empresa ramada"
}
```

**Response:**
```json
{
  "success": true,
  "created": true,
  "value": "Empresa Ramada",
  "message": "Valor 'Empresa Ramada' cadastrado automaticamente"
}
```

**Comportamento:**
- Se valor existe → retorna normalizado
- Se não existe → cria automaticamente com Title Case

---

### `GET /reference-values/{field_name}`
Lista valores disponíveis de um campo.

**Query Parameters:**
- `include_stats` (optional): Incluir estatísticas de uso

---

### `POST /reference-values/batch-ensure`
Garante múltiplos valores de uma vez.

---

## Audit (`/audit`)

### `GET /audit/events`
Lista eventos de auditoria.

**Query Parameters:**
- `limit`, `offset`, `action`, `user`, `resource_type`, `start_date`, `end_date`

---

### `GET /audit/statistics`
Estatísticas de auditoria.

---

## KV Store (`/kv`)

Acesso direto ao Consul KV.

### `GET /kv/tree`
Navegação em árvore.

**Query Parameters:**
- `prefix` (optional): Prefixo da chave

---

### `GET /kv/value`
Obtém valor de chave.

**Query Parameters:**
- `key` (required)

---

### `POST /kv/value`
Salva valor.

---

### `DELETE /kv/value`
Remove chave.

---

## Presets (`/presets`)

Templates de serviços reutilizáveis.

### `GET /presets/`
Lista presets.

---

### `POST /presets/`
Cria preset.

---

### `POST /presets/preview`
Preview de preset renderizado.

---

### `POST /presets/register`
Registra serviço a partir de preset.

---

## Nodes (`/nodes`)

### `GET /nodes/`
Lista nós do cluster Consul.

---

### `GET /nodes/{node_addr}/services`
Serviços de um nó específico.

---

## Settings (`/settings`)

### `GET /settings/naming-config`
Configuração de nomenclatura.

---

### `GET /settings/sites`
Lista sites configurados.

---

## Installer (`/installer`)

**AUTENTICAÇÃO REQUERIDA:** HTTP Basic Auth

### `POST /installer/install`
Inicia instalação remota de exporter.

**Conectores Suportados:**
- SSH (Linux/Windows)
- WinRM (Windows)
- PSExec (Windows)

**Prioridade:** SSH → WinRM → PSExec

---

### `GET /installer/install/{installation_id}/status`
Status de instalação.

---

### `POST /installer/test-connection`
Testa conectividade antes de instalar.

---

### `POST /installer/check-existing`
Verifica se exporter já está instalado.

---

### `GET /installer/methods`
Lista métodos de conexão disponíveis.

---

## Optimized Endpoints (`/optimized-endpoints`)

Endpoints otimizados para reduzir latência.

### `GET /optimized-endpoints/exporters`
Lista exporters otimizada.

---

### `GET /optimized-endpoints/blackbox-targets`
Lista blackbox targets otimizada.

---

---

## Conceitos Importantes

### Dual Storage Pattern
Serviços blackbox são armazenados em 2 locais:
1. **Consul Services** (source of truth para Prometheus)
2. **Consul KV** (metadata adicional e grupos)

### Service ID Sanitization
IDs são sanitizados automaticamente:
- Remove: `[ ]` ` ` `~` `!` `#` `$` `^` `&` `*` `=` `|` `"` `{` `}` `'` `:` `;` `?` `\t` `\n`
- Substitui por: `_`
- Valida barras (não permite `//`, `/` no início/fim)

### WebSocket para Logs
Instalações remotas usam WebSocket para streaming de logs:
```
ws://localhost:5000/ws/installer/{session_id}
```

### Multi-Site Support
Sistema suporta sufixos automáticos baseados no site:
- NAMING_STRATEGY=option1: Tag automática
- NAMING_STRATEGY=option2: Sufixo no nome (ex: `selfnode_exporter_rio`)

---

## Documentação Interativa

**Swagger UI:** http://localhost:5000/docs
**ReDoc:** http://localhost:5000/redoc

---

## Exemplos de Uso

### Criar Serviço Blackbox
```bash
curl -X POST http://localhost:5000/api/v1/services \
  -H "Content-Type: application/json" \
  -d '{
    "name": "blackbox_exporter",
    "address": "172.16.1.26",
    "port": 9115,
    "tags": ["icmp", "prod"],
    "Meta": {
      "module": "icmp",
      "company": "Ramada",
      "project": "infraestrutura",
      "env": "prod",
      "name": "gateway-principal",
      "instance": "192.168.1.1"
    }
  }'
```

### Buscar Serviços por Empresa
```bash
curl "http://localhost:5000/api/v1/search/by-company/Ramada"
```

### Extrair Tipos de Monitoramento
```bash
curl "http://localhost:5000/api/v1/monitoring-types-dynamic/from-prometheus?server=ALL"
```

### Sincronizar Campo com Prometheus
```bash
curl -X POST http://localhost:5000/api/v1/metadata-fields/batch-sync \
  -H "Content-Type: application/json" \
  -d '{
    "field_names": ["company", "env"],
    "server_id": "172.16.1.26:5522",
    "dry_run": false
  }'
```

---

## Suporte e Contribuição

Para reportar bugs ou sugerir melhorias, consulte a documentação completa no diretório `/docs`.

**Versão:** 2.0
**Última Atualização:** 2025-11-06
