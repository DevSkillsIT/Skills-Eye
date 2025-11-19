# 🧪 Teste de Enriquecimento de Monitoring-Types com Sites

## ✅ Implementação Completa

### 1. Função de Enriquecimento
- **Arquivo:** `backend/api/monitoring_types_dynamic.py`
- **Função:** `_enrich_servers_with_sites_data()`
- **Funcionalidade:**
  - Busca sites do KV `skills/eye/metadata/sites`
  - Faz match entre `hostname` do servidor e `prometheus_host`/`prometheus_instance` do site
  - Enriquece cada servidor com dados do site (code, name, color, cluster, datacenter, environment, etc)

### 2. Aplicação do Enriquecimento
- ✅ **Endpoint:** `GET /api/v1/monitoring-types-dynamic/from-prometheus?force_refresh=true`
- ✅ **Prewarm:** `_prewarm_monitoring_types_cache()` em `backend/app.py`

### 3. Estrutura Enriquecida
Cada servidor no KV agora tem:
```json
{
  "172.16.1.26": {
    "types": [...],
    "total": 10,
    "prometheus_file": "/etc/prometheus/prometheus.yml",
    "site": {
      "code": "palmas",
      "name": "Palmas (TO)",
      "color": "blue",
      "is_default": true,
      "cluster": "palmas-master",
      "datacenter": "skillsit-palmas-to",
      "environment": "production",
      "site": "palmas",
      "prometheus_port": 5522,
      "ssh_port": 22
    }
  }
}
```

---

## 🧪 Testes a Realizar

### Teste 1: Verificar Enriquecimento no KV
```bash
# 1. Verificar se KV de sites existe
curl http://localhost:5000/api/v1/metadata-fields/config/sites

# 2. Forçar refresh de monitoring-types
curl "http://localhost:5000/api/v1/monitoring-types-dynamic/from-prometheus?force_refresh=true"

# 3. Verificar KV de monitoring-types (via Consul UI ou API)
# Deve conter campo "site" em cada servidor
```

### Teste 2: Botão "Atualizar" no Frontend
1. Acessar: `http://localhost:8081/monitoring-types`
2. Clicar no botão "Atualizar" (ícone SyncOutlined)
3. Verificar:
   - Modal de progresso aparece
   - Dados são extraídos via SSH
   - KV é atualizado com dados enriquecidos
   - Frontend exibe dados atualizados

### Teste 3: Botão "Recarregar" no Frontend
1. Acessar: `http://localhost:8081/monitoring-types`
2. Clicar no botão "Recarregar" (ícone ReloadOutlined)
3. Verificar:
   - Dados são carregados do cache KV (rápido)
   - Não mostra modal
   - Dados enriquecidos aparecem

### Teste 4: Pre-warm (Deletar KV e Reiniciar)
```bash
# 1. Deletar KV de monitoring-types
curl -X DELETE http://localhost:8500/v1/kv/skills/eye/monitoring-types?recurse

# 2. Reiniciar backend
cd ~/projetos/Skills-Eye
./restart-all.sh

# 3. Verificar logs do backend
tail -f backend/backend.log | grep -E "PRE-WARM|ENRICH|MONITORING-TYPES"

# 4. Aguardar ~20-30 segundos para prewarm completar

# 5. Verificar se KV foi populado
curl http://localhost:5000/api/v1/monitoring-types-dynamic/from-prometheus

# 6. Verificar se dados estão enriquecidos
# Cada servidor deve ter campo "site" com dados do KV de sites
```

### Teste 5: Análise de Logs
```bash
# Backend
tail -f ~/projetos/Skills-Eye/backend/backend.log | grep -E "ENRICH-SITES|MONITORING-TYPES|PRE-WARM"

# Frontend
tail -f ~/projetos/Skills-Eye/frontend/frontend.log
```

**Logs esperados:**
- `[ENRICH-SITES] X sites mapeados para enriquecimento`
- `[ENRICH-SITES] Servidor X.X.X.X enriquecido com site Y`
- `[MONITORING-TYPES] Enriquecendo servidores com dados de sites...`
- `[PRE-WARM MONITORING-TYPES] Enriquecendo servidores com dados de sites...`

---

## ✅ Critérios de Sucesso

1. ✅ KV de monitoring-types contém campo `site` em cada servidor
2. ✅ Dados de sites são corretos (code, name, cluster, datacenter, etc)
3. ✅ Botão "Atualizar" força extração e enriquece dados
4. ✅ Botão "Recarregar" carrega dados enriquecidos do cache
5. ✅ Pre-warm popula KV com dados enriquecidos no startup
6. ✅ Logs mostram enriquecimento funcionando

---

## 🔍 Verificação Manual do KV

```bash
# Via Consul API
curl http://localhost:8500/v1/kv/skills/eye/monitoring-types?raw | jq '.servers["172.16.1.26"].site'

# Deve retornar:
{
  "code": "palmas",
  "name": "Palmas (TO)",
  "color": "blue",
  "is_default": true,
  "cluster": "palmas-master",
  "datacenter": "skillsit-palmas-to",
  "environment": "production",
  "site": "palmas",
  "prometheus_port": 5522,
  "ssh_port": 22
}
```
