# 📊 Sistema de Páginas Dinâmicas de Monitoramento v2.0

**Autor:** Sistema de Refatoração Skills Eye
**Data:** 2025-11-13
**Versão:** 2.0

---

## 🎯 VISÃO GERAL

Este documento descreve o **Sistema de Páginas Dinâmicas de Monitoramento**, uma refatoração completa que substitui 4 páginas estáticas por **1 componente React reutilizável** totalmente dinâmico.

### 🌟 PRINCIPAIS BENEFÍCIOS

1. **100% Dinâmico** - Colunas, filtros e dados vêm do backend
2. **1 Componente = 4 Páginas** - DRY (Don't Repeat Yourself)
3. **Cache Inteligente** - TTL de 5 minutos, extração SSH otimizada
4. **Regras Editáveis** - Categorização via JSON no Consul KV
5. **Query Builder** - Templates PromQL com Jinja2

---

## 📂 ESTRUTURA DE ARQUIVOS

### Backend (Python + FastAPI)

```
backend/
├── core/
│   ├── consul_kv_config_manager.py    # ✨ NOVO - Cache KV com TTL
│   ├── categorization_rule_engine.py  # ✨ NOVO - Regras JSON
│   └── dynamic_query_builder.py       # ✨ NOVO - Templates PromQL
│
├── api/
│   ├── monitoring_unified.py          # ✨ NOVO - API unificada
│   └── metadata_fields_manager.py     # 🔄 ATUALIZADO - 4 propriedades
│
└── migrate_categorization_to_json.py  # ✨ NOVO - Script de migração
```

### Frontend (React 19 + TypeScript)

```
frontend/src/
├── pages/
│   ├── DynamicMonitoringPage.tsx      # ✨ NOVO - Componente base único
│   └── MetadataFields.tsx             # 🔄 ATUALIZADO - 4 checkboxes
│
├── services/
│   └── api.ts                         # 🔄 ATUALIZADO - 3 métodos
│
├── hooks/
│   └── useMetadataFields.ts           # ✅ JÁ SUPORTAVA 4 contextos
│
└── App.tsx                            # 🔄 ATUALIZADO - 4 rotas
```

---

## 🚀 INSTALAÇÃO E SETUP

### 1️⃣ Adicionar Dependência Jinja2

```bash
cd backend
echo "Jinja2==3.1.4" >> requirements.txt
pip install Jinja2==3.1.4
```

### 2️⃣ Executar Script de Migração

**IMPORTANTE:** Este script deve ser executado **UMA ÚNICA VEZ** antes de usar o sistema.

```bash
cd backend
python migrate_categorization_to_json.py
```

**O que o script faz:**
- Extrai 50+ padrões de categorização do código hardcoded
- Converte para JSON estruturado
- Salva no Consul KV: `skills/eye/monitoring-types/categorization/rules`
- Valida a migração automaticamente

**Saída esperada:**
```
📦 Convertendo regras de Blackbox...
  ✅ 7 regras de Network Probes
  ✅ 8 regras de Web Probes

📦 Convertendo regras de Exporters...
  ✅ 40 regras de Exporters

💾 Salvando no Consul KV...
  ✅ Regras salvas em: skills/eye/monitoring-types/categorization/rules

✅ MIGRAÇÃO CONCLUÍDA COM SUCESSO!
```

### 3️⃣ Iniciar Backend e Frontend

```bash
# Terminal 1 - Backend
cd backend
python app.py
# Deve iniciar em http://localhost:5000

# Terminal 2 - Frontend
cd frontend
npm run dev
# Deve iniciar em http://localhost:8081
```

### 4️⃣ Sincronizar Cache (Primeira Vez)

Acesse qualquer uma das 4 novas páginas e clique no botão **"Sincronizar Cache"**:

- http://localhost:8081/monitoring/network-probes
- http://localhost:8081/monitoring/web-probes
- http://localhost:8081/monitoring/system-exporters
- http://localhost:8081/monitoring/database-exporters

**O que acontece:**
1. Backend conecta via SSH nos servidores Prometheus
2. Lê `prometheus.yml` de cada servidor
3. Extrai tipos de monitoramento (jobs, módulos)
4. Categoriza automaticamente usando regras JSON
5. Salva cache no KV: `skills/eye/monitoring-types/cache`
6. Cache válido por 5 minutos

---

## 🔧 ARQUITETURA TÉCNICA

### Fluxo de Dados - Endpoint `/monitoring/data`

```
┌──────────────┐
│   Frontend   │
│ (React Page) │
└──────┬───────┘
       │ GET /api/v1/monitoring/data?category=network-probes
       ▼
┌──────────────────────────────┐
│     monitoring_unified.py    │
│  1. Busca cache KV           │
│  2. Filtra por categoria     │
│  3. Busca serviços Consul    │
│  4. Aplica filtros           │
└──────┬───────────────────────┘
       │ JSON Response
       ▼
┌──────────────────────────────┐
│   DynamicMonitoringPage.tsx │
│  - Renderiza ProTable        │
│  - Colunas dinâmicas         │
│  - Filtros dinâmicos         │
└──────────────────────────────┘
```

### Cache de 2 Níveis

```
┌─────────────────────────────────────┐
│         NÍVEL 1: MEMÓRIA            │
│  ConsulKVConfigManager._cache       │
│  TTL: 5 minutos                     │
│  Evita requisições ao Consul KV     │
└─────────────────────────────────────┘
                  │
                  ▼ (cache miss)
┌─────────────────────────────────────┐
│         NÍVEL 2: CONSUL KV          │
│  skills/eye/monitoring-types/cache  │
│  Persiste entre reinícios           │
└─────────────────────────────────────┘
                  │
                  ▼ (não existe)
┌─────────────────────────────────────┐
│      EXTRAÇÃO VIA SSH               │
│  MultiConfigManager.extract_...()   │
│  Tempo: 20-30 segundos              │
└─────────────────────────────────────┘
```

---

## 📡 ENDPOINTS DA API

### 1. GET `/api/v1/monitoring/data`

**Descrição:** Busca serviços do Consul filtrados por categoria

**Parâmetros:**
- `category` (required): `network-probes` | `web-probes` | `system-exporters` | `database-exporters`
- `company` (optional): Filtrar por empresa
- `site` (optional): Filtrar por site
- `env` (optional): Filtrar por ambiente

**Exemplo:**
```bash
curl "http://localhost:5000/api/v1/monitoring/data?category=network-probes&company=Ramada" | jq
```

**Resposta:**
```json
{
  "success": true,
  "category": "network-probes",
  "data": [
    {
      "ID": "icmp-ramada-palmas-gateway",
      "Service": "blackbox",
      "Address": "10.0.0.1",
      "Port": 9115,
      "Tags": ["icmp", "network"],
      "Meta": {
        "module": "icmp",
        "company": "Ramada",
        "site": "palmas",
        "name": "Gateway Principal"
      }
    }
  ],
  "total": 150,
  "modules": ["icmp", "tcp", "dns"],
  "job_names": ["blackbox"]
}
```

### 2. GET `/api/v1/monitoring/metrics`

**Descrição:** Busca métricas do Prometheus via PromQL

**Parâmetros:**
- `category` (required): Categoria de monitoramento
- `server` (optional): Servidor Prometheus específico
- `time_range` (optional): Intervalo de tempo (default: 5m)
- `company` (optional): Filtro de empresa
- `site` (optional): Filtro de site

**Exemplo:**
```bash
curl "http://localhost:5000/api/v1/monitoring/metrics?category=network-probes&time_range=10m" | jq
```

**Resposta:**
```json
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
```

### 3. POST `/api/v1/monitoring/sync-cache`

**Descrição:** Força sincronização do cache de tipos

**Exemplo:**
```bash
curl -X POST "http://localhost:5000/api/v1/monitoring/sync-cache" | jq
```

**Resposta:**
```json
{
  "success": true,
  "message": "Cache sincronizado com sucesso",
  "total_types": 45,
  "total_servers": 3,
  "categories": [
    {"category": "network-probes", "count": 8},
    {"category": "web-probes", "count": 10},
    {"category": "system-exporters", "count": 15},
    {"category": "database-exporters": "count": 12}
  ],
  "duration_seconds": 23.5
}
```

---

## ⚙️ CONFIGURAÇÃO DE VISIBILIDADE DE CAMPOS

### Via Interface Web (MetadataFields.tsx)

1. Acesse: http://localhost:8081/metadata-fields
2. Selecione um campo na tabela
3. Edite as 4 novas propriedades:
   - ☑️ Mostrar em Network Probes
   - ☑️ Mostrar em Web Probes
   - ☑️ Mostrar em System Exporters
   - ☑️ Mostrar em Database Exporters
4. Salve

### Via API Direta

```bash
curl -X PUT "http://localhost:5000/api/v1/metadata-fields/fields/company" \
  -H "Content-Type: application/json" \
  -d '{
    "show_in_network_probes": true,
    "show_in_web_probes": true,
    "show_in_system_exporters": false,
    "show_in_database_exporters": false
  }'
```

---

## 🧪 TESTES

### Teste Manual - 4 Páginas

```bash
# 1. Network Probes
curl "http://localhost:5000/api/v1/monitoring/data?category=network-probes"

# 2. Web Probes
curl "http://localhost:5000/api/v1/monitoring/data?category=web-probes"

# 3. System Exporters
curl "http://localhost:5000/api/v1/monitoring/data?category=system-exporters"

# 4. Database Exporters
curl "http://localhost:5000/api/v1/monitoring/data?category=database-exporters"
```

### Teste de Performance - Cache

```bash
# Primeira chamada (cold start) - ~500ms
time curl "http://localhost:5000/api/v1/monitoring/data?category=network-probes"

# Segunda chamada (cache hit) - ~50ms
time curl "http://localhost:5000/api/v1/monitoring/data?category=network-probes"
```

---

## 🐛 TROUBLESHOOTING

### Problema: "Cache de tipos não disponível"

**Causa:** Cache KV vazio (primeira vez)

**Solução:**
```bash
curl -X POST "http://localhost:5000/api/v1/monitoring/sync-cache"
```

### Problema: "Categoria não encontrada"

**Causa:** Script de migração não executado

**Solução:**
```bash
cd backend
python migrate_categorization_to_json.py
```

### Problema: Página em branco no frontend

**Causa:** Jinja2 não instalado

**Solução:**
```bash
cd backend
pip install Jinja2==3.1.4
python app.py  # Reiniciar
```

### Problema: Campos não aparecem nas novas páginas

**Causa:** Propriedades `show_in_*` não configuradas

**Solução:** Acesse /metadata-fields e configure os 4 checkboxes para cada campo

---

## 📝 MANUTENÇÃO

### Adicionar Nova Categoria

1. Edite o JSON no KV: `skills/eye/monitoring-types/categorization/rules`
2. Adicione nova regra no array `rules`:
```json
{
  "id": "custom_category",
  "priority": 90,
  "category": "custom-exporters",
  "display_name": "Custom Exporter",
  "exporter_type": "custom",
  "conditions": {
    "job_name_pattern": "^custom.*",
    "metrics_path": "/metrics"
  }
}
```
3. Sincronize o cache: `POST /api/v1/monitoring/sync-cache`

### Adicionar Novo Template PromQL

Edite `backend/core/dynamic_query_builder.py`:

```python
QUERY_TEMPLATES = {
    # ...existentes...

    "meu_novo_template": """
        my_metric{
            job=~"{{ jobs|join('|') }}"
            {% if company %},company="{{ company }}"{% endif %}
        }
    """
}
```

---

## 📚 REFERÊNCIAS

- Plano Completo: `docs/PLANO DE REFATORAÇÃO SKILLS EYE - VERSÃO COMPLETA 2.0.md`
- Ajustes: `docs/NOTA_AJUSTES_PLANO_V2.md`
- Jinja2 Docs: https://jinja.palletsprojects.com/
- FastAPI Docs: https://fastapi.tiangolo.com/
- ProTable Docs: https://procomponents.ant.design/components/table

---

## ✅ CHECKLIST DE IMPLANTAÇÃO

- [ ] Jinja2 instalado
- [ ] Script de migração executado
- [ ] Cache sincronizado (primeira vez)
- [ ] 4 páginas acessíveis no navegador
- [ ] Campos metadata configurados (4 checkboxes)
- [ ] Testes manuais executados
- [ ] Performance validada (cache hit < 100ms)

---

**Dúvidas? Consulte a documentação técnica completa ou abra uma issue no repositório.**
