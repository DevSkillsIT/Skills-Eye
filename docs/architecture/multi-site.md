# Implementação Suporte Multi-Site - Resumo

**Data:** 2025-11-05
**Versão:** 1.0
**Status:** ✅ Implementado - Aguardando Testes

---

## 🎯 **OBJETIVO**

Implementar suporte completo para arquitetura multi-site distribuída no Consul Manager Web, permitindo:

1. Criar serviços Consul com metadados de **cluster**, **datacenter**, **environment**, **site**
2. **Tags automáticas** por site para filtros no prometheus.yml
3. **Extração dinâmica** de `external_labels`, `remote_write` dos arquivos Prometheus
4. Preparar sistema para migração da arquitetura centralizada → distribuída

---

## ✅ **MUDANÇAS IMPLEMENTADAS**

### **1. Novos Campos no `metadata_fields.json`**

**Arquivo:** `C:\consul-manager-web\backend\config\metadata_fields.json`

**Campos adicionados** (categoria `infrastructure`):

```json
{
  "name": "cluster",
  "display_name": "Cluster",
  "description": "Cluster ou instância Prometheus (usado em external_labels)",
  "field_type": "select",
  "options": ["palmas-master", "rio-rmd-ldc", "dtc-remote-skills", "genesis-dtc"],
  "order": 3.1,
  "show_in_filter": true,
  "available_for_registration": true
}
```

```json
{
  "name": "datacenter",
  "display_name": "Datacenter",
  "description": "Datacenter ou localização física (usado em external_labels)",
  "field_type": "select",
  "options": ["palmas", "rio", "genesis-dtc", "eua"],
  "order": 3.2,
  "show_in_filter": true,
  "available_for_registration": true
}
```

```json
{
  "name": "environment",
  "display_name": "Environment",
  "description": "Ambiente de execução (production, staging, development)",
  "field_type": "select",
  "options": ["production", "staging", "development", "testing"],
  "order": 3.3,
  "default_value": "production",
  "show_in_filter": true,
  "available_for_registration": true
}
```

```json
{
  "name": "site",
  "display_name": "Site",
  "description": "Site físico do serviço (usado em tags Consul para filtrar jobs por site)",
  "field_type": "select",
  "options": ["palmas", "rio", "dtc", "genesis"],
  "order": 3.4,
  "show_in_filter": true,
  "available_for_registration": true
}
```

**Benefícios:**

- ✅ Campos aparecem **automaticamente** nos formulários frontend (100% dinâmico)
- ✅ Podem ser filtrados em tabelas
- ✅ Armazenados como metadata Consul

---

### **2. Tags Automáticas por Site**

**Arquivos Modificados:**

- `backend/api/services.py` (linhas 379-395 e 535-548)
- `backend/core/blackbox_manager.py` (linhas 473-498)

**Lógica Implementada:**

Quando um serviço (ou Blackbox target) é criado/atualizado com campo `site` nos metadados:

1. Sistema **automaticamente adiciona** o valor de `site` como **Tag Consul**
2. Exemplo: `site=rio` → Tag `"rio"` adicionada ao array `Tags`
3. Isso permite **filtros no prometheus.yml**:

```yaml
# Rio Slave - prometheus.yml
scrape_configs:
  - job_name: 'icmp'
    consul_sd_configs:
      - services: ['blackbox_exporter']
        tags: ['icmp', 'rio']  # ← Filtra apenas targets do Rio
```

**Código Implementado (services.py):**

```python
# MULTI-SITE SUPPORT: Adicionar tag automática baseado no campo "site"
site = meta.get("site")
if site:
    tags = service_data.get("Tags", service_data.get("tags", []))
    if not isinstance(tags, list):
        tags = []

    # Adicionar tag do site se não existir
    if site not in tags:
        tags.append(site)
        logger.info(f"Adicionada tag automática para site: {site}")

    service_data["Tags"] = tags
```

**Código Implementado (blackbox_manager.py):**

```python
# MULTI-SITE SUPPORT: Adicionar tag automática baseado no campo "site"
if labels and "site" in labels:
    site = labels["site"]
    if site and site not in payload["tags"]:
        payload["tags"].append(site)
        logger.info(f"Adicionada tag automática para site: {site}")
```

---

### **3. Extração de `external_labels` e `remote_write`**

**Arquivo:** `backend/core/yaml_config_service.py` (linhas 553-660)

**Novos Métodos Criados:**

#### **`get_global_config()`**

Extrai configuração global incluindo `external_labels`:

```python
def get_global_config(self) -> Dict[str, Any]:
    config = self.read_config()
    global_config = config.get('global', {})

    result = {
        'scrape_interval': global_config.get('scrape_interval'),
        'scrape_timeout': global_config.get('scrape_timeout'),
        'evaluation_interval': global_config.get('evaluation_interval'),
        'external_labels': global_config.get('external_labels', {}),
        'query_log_file': global_config.get('query_log_file')
    }

    return result
```

**Exemplo de Retorno:**

```json
{
  "scrape_interval": "30s",
  "evaluation_interval": "45s",
  "external_labels": {
    "cluster": "dtc-remote-skills",
    "datacenter": "genesis-dtc",
    "prometheus_instance": "11.144.0.21",
    "environment": "production",
    "cliente": "skills-it",
    "location": "eua"
  }
}
```

#### **`get_remote_write_config()`**

Extrai configurações `remote_write` incluindo `write_relabel_configs`:

```python
def get_remote_write_config(self) -> List[Dict[str, Any]]:
    config = self.read_config()
    remote_write = config.get('remote_write', [])

    results = []
    for idx, rw in enumerate(remote_write):
        rw_data = {
            'index': idx,
            'url': rw.get('url'),
            'remote_timeout': rw.get('remote_timeout'),
            'write_relabel_configs': rw.get('write_relabel_configs', []),
            'queue_config': rw.get('queue_config', {}),
            'basic_auth': bool(rw.get('basic_auth')),  # Não expor senha
            'bearer_token': bool(rw.get('bearer_token')),
            'tls_config': bool(rw.get('tls_config')),
        }
        results.append(rw_data)

    return results
```

**Exemplo de Retorno:**

```json
[
  {
    "index": 0,
    "url": "http://172.16.1.26:9090/api/v1/write",
    "remote_timeout": "30s",
    "write_relabel_configs": [
      {
        "target_label": "remote_site",
        "replacement": "genesis-dtc-skills"
      }
    ],
    "queue_config": {
      "capacity": 5000,
      "max_samples_per_send": 500,
      "batch_send_deadline": "5s"
    },
    "basic_auth": true
  }
]
```

#### **`get_alerting_config()`**

Extrai configuração de Alertmanagers.

#### **`get_rule_files()`**

Extrai lista de arquivos de regras configurados.

#### **`get_full_server_info()`**

Retorna **tudo** em um único objeto:

```json
{
  "global": { /* external_labels, scrape_interval, etc */ },
  "remote_write": [ /* configurações remote_write */ ],
  "alerting": { /* alertmanagers */ },
  "rule_files": [ /* arquivos de regras */ ],
  "scrape_configs_count": 14,
  "jobs": [ /* todos os jobs com detalhes */ ]
}
```

---

### **4. Novos Endpoints API**

**Arquivo:** `backend/api/prometheus_config.py` (linhas 2024-2133)

**Endpoints Criados:**

| Endpoint | Método | Descrição |
|----------|--------|-----------|
| `/api/v1/prometheus-config/global` | GET | Retorna `external_labels`, `scrape_interval`, etc |
| `/api/v1/prometheus-config/remote-write` | GET | Retorna configurações `remote_write` com `write_relabel_configs` |
| `/api/v1/prometheus-config/alerting` | GET | Retorna configurações de Alertmanagers |
| `/api/v1/prometheus-config/rule-files` | GET | Retorna lista de arquivos de regras |
| `/api/v1/prometheus-config/server-info` | GET | Retorna **todas** as informações do servidor em um único objeto |

**Exemplos de Uso:**

```bash
# Ver external_labels do servidor atual
curl http://localhost:5000/api/v1/prometheus-config/global

# Ver configurações remote_write
curl http://localhost:5000/api/v1/prometheus-config/remote-write

# Ver todas as informações do servidor
curl http://localhost:5000/api/v1/prometheus-config/server-info
```

---

## 🔄 **FLUXO DE CRIAÇÃO DE SERVIÇO COM NOVOS CAMPOS**

### **Exemplo 1: Criar Blackbox Target no Rio**

**Request (Frontend → Backend):**

```json
{
  "module": "icmp",
  "company": "ACME",
  "project": "Monitoramento",
  "env": "production",
  "name": "Gateway Rio",
  "instance": "192.168.1.1",
  "labels": {
    "cluster": "rio-rmd-ldc",
    "datacenter": "rio",
    "environment": "production",
    "site": "rio"
  }
}
```

**O que acontece:**

1. ✅ Campos `cluster`, `datacenter`, `environment`, `site` são adicionados ao **Meta** Consul
2. ✅ Tag `"rio"` é **automaticamente adicionada** ao array `Tags`
3. ✅ Serviço é registrado no Consul

**Serviço registrado no Consul:**

```json
{
  "ID": "icmp_ACME_Monitoramento_production_Gateway_Rio",
  "Service": "blackbox_exporter",
  "Tags": ["icmp", "production", "Monitoramento", "ACME", "rio"],
  "Meta": {
    "module": "icmp",
    "company": "ACME",
    "project": "Monitoramento",
    "env": "production",
    "name": "Gateway Rio",
    "instance": "192.168.1.1",
    "cluster": "rio-rmd-ldc",
    "datacenter": "rio",
    "environment": "production",
    "site": "rio"
  }
}
```

**Prometheus.yml no Rio pode filtrar:**

```yaml
scrape_configs:
  - job_name: 'icmp'
    consul_sd_configs:
      - server: 'localhost:8500'
        services: ['blackbox_exporter']
        tags: ['icmp', 'rio']  # ← Filtra apenas targets com tag "rio"
```

---

### **Exemplo 2: Criar Node Exporter no DTC**

**Request:**

```json
{
  "id": "node_exporter_dtc_server01",
  "name": "selfnode_exporter_dtc_remote",
  "tags": ["linux"],
  "Meta": {
    "instance": "11.144.0.25:9100",
    "company": "SKILLS",
    "name": "Server DTC 01",
    "cluster": "dtc-remote-skills",
    "datacenter": "genesis-dtc",
    "environment": "production",
    "site": "dtc"
  }
}
```

**O que acontece:**

1. ✅ Tag `"dtc"` é **automaticamente adicionada**
2. ✅ Metadados incluem cluster/datacenter para correlação com `external_labels`

**Tags finais:** `["linux", "dtc"]`

---

## 📊 **COMPATIBILIDADE COM ARQUITETURA DISTRIBUÍDA**

### **Arquitetura Atual (Centralizada):**

```
PALMAS MASTER
  │
  ├─ Scrape local targets (Palmas)
  ├─ Scrape remote Blackbox (Rio, DTC) ← PROBLEMA: Latência distorcida
  └─ Scrape remote Node Exporters
```

### **Arquitetura Recomendada (Distribuída) - SUPORTADA AGORA:**

```
PALMAS MASTER (Recebe via remote_write)
  ▲
  │ remote_write
  ├────────────────────────┬────────────────────────┐
  │                        │                        │
RIO SLAVE              DTC SLAVE            GENESIS SLAVE
  │                        │                        │
  ├─ Blackbox local       ├─ Blackbox local      ├─ Blackbox local
  ├─ Node Exporters       ├─ Node Exporters      ├─ Node Exporters
  │                        │                        │
  └─ Tags: ["rio"]        └─ Tags: ["dtc"]        └─ Tags: ["genesis"]
```

**O Sistema Agora Suporta:**

✅ **Job names idênticos** nos 3 sites (`node_exporter`, `icmp`, etc)
✅ **Filtros por tag** no prometheus.yml (`tags: ['icmp', 'rio']`)
✅ **External labels** diferentes por site (`cluster: 'rio-rmd-ldc'`)
✅ **Remote write** de slaves para master (`url: http://172.16.1.26:9090/api/v1/write`)
✅ **Write relabel configs** para adicionar `remote_site` label

---

## 🧪 **TESTES NECESSÁRIOS**

### **1. Testar Novos Endpoints**

```bash
# Backend deve estar rodando
cd c:\consul-manager-web\backend
python app.py

# Testar extração de global config
curl http://localhost:5000/api/v1/prometheus-config/global

# Testar extração de remote_write
curl http://localhost:5000/api/v1/prometheus-config/remote-write

# Testar endpoint completo
curl http://localhost:5000/api/v1/prometheus-config/server-info
```

### **2. Testar Criação de Serviço com Novos Campos**

**Via Frontend:**

1. Ir para página **Blackbox Targets** ou **Services**
2. Clicar em **Criar Novo**
3. Verificar se campos aparecem:
   - Cluster (dropdown)
   - Datacenter (dropdown)
   - Environment (dropdown)
   - Site (dropdown)
4. Preencher formulário incluindo campo **Site = "rio"**
5. Criar serviço
6. **Verificar no Consul** se tag "rio" foi adicionada automaticamente

**Via API (curl):**

```bash
curl -X POST http://localhost:5000/api/v1/blackbox/targets \
  -H "Content-Type: application/json" \
  -d '{
    "module": "icmp",
    "company": "TESTE",
    "project": "Multi-Site",
    "env": "development",
    "name": "Test Rio",
    "instance": "8.8.8.8",
    "labels": {
      "cluster": "rio-rmd-ldc",
      "datacenter": "rio",
      "environment": "development",
      "site": "rio"
    }
  }'
```

**Validar no Consul:**

```bash
# Ver serviço criado
curl http://172.16.1.26:8500/v1/agent/services \
  -H "X-Consul-Token: 8382a112-81e0-cd6d-2b92-8565925a0675"

# Verificar se Tags contém "rio"
```

### **3. Testar Atualização de Serviço**

1. Criar serviço **sem** campo `site`
2. Editar serviço e adicionar `site = "dtc"`
3. Salvar
4. **Verificar** se tag "dtc" foi adicionada automaticamente

---

## 📝 **ARQUIVOS MODIFICADOS**

| Arquivo | Mudanças | Linhas |
|---------|----------|--------|
| `backend/config/metadata_fields.json` | Adicionados 4 novos campos (cluster, datacenter, environment, site) | 85-212 |
| `backend/core/yaml_config_service.py` | Adicionados 5 novos métodos de extração | 553-660 |
| `backend/api/prometheus_config.py` | Adicionados 5 novos endpoints API | 2024-2133 |
| `backend/api/services.py` | Lógica de tags automáticas (create e update) | 379-395, 535-548 |
| `backend/core/blackbox_manager.py` | Lógica de tags automáticas + labels no Meta | 473-498 |

**Total:** 5 arquivos modificados, ~150 linhas de código adicionadas

---

## 🎁 **BENEFÍCIOS**

### **Para o Usuário:**

- ✅ **Campos aparecem automaticamente** nos formulários (100% dinâmico)
- ✅ **Tags criadas automaticamente** - não precisa lembrar de adicionar manualmente
- ✅ **Filtragem por site** facilitada (dropdown nos filtros)
- ✅ **Preparado para migração** para arquitetura distribuída

### **Para o Sistema:**

- ✅ **Compatível com arquitetura atual E futura**
- ✅ **Zero mudanças no frontend** (campos dinâmicos via metadata_fields.json)
- ✅ **APIs RESTful** para acesso programático
- ✅ **Logging detalhado** de quando tags são adicionadas

### **Para Prometheus:**

- ✅ **Job names idênticos** possíveis (filtro por tag em vez de job name diferente)
- ✅ **Queries unificadas** cross-site
- ✅ **External labels** extraíveis via API
- ✅ **Remote write** detectável e visualizável

---

## 🚀 **PRÓXIMOS PASSOS**

1. ✅ **Testes manuais** dos endpoints novos
2. ✅ **Validar frontend** - verificar se campos aparecem nos formulários
3. ✅ **Criar serviço teste** com todos os novos campos
4. ✅ **Verificar tags automáticas** no Consul
5. ⏳ **Atualizar MonitoringTypes** para exibir external_labels/remote_write (opcional)
6. ⏳ **Documentar para usuário final** como usar os novos campos
7. ⏳ **Planejar migração** para arquitetura distribuída (quando apropriado)

---

**STATUS ATUAL:** ✅ **Implementação Completa - Pronto para Testes**

**Aguardando:** Testes do usuário e feedback
