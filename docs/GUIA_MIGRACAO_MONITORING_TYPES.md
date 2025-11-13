# 🔄 Guia de Migração: monitoring_types_dynamic.py

**Data:** 13/11/2025
**Objetivo:** Substituir lógica hardcoded por CategorizationRuleEngine
**Criticidade:** 🔴 ALTA - Sistema não funcionará sem esta migração

---

## 📝 RESUMO DA MUDANÇA

**ANTES:** 250+ linhas de código hardcoded com if/elif
**DEPOIS:** 30 linhas usando CategorizationRuleEngine que lê regras do Consul KV

---

## ⚠️ PRÉ-REQUISITOS

Antes de modificar o arquivo, certifique-se:

1. ✅ Script `migrate_categorization_to_json.py` foi executado
2. ✅ Regras estão no Consul KV:
   ```bash
   curl "http://172.16.1.26:8500/v1/kv/skills/eye/monitoring-types/categorization/rules?raw" | jq '.total_rules'
   # Deve retornar: 47
   ```
3. ✅ Backup do arquivo original foi feito:
   ```bash
   cp backend/api/monitoring_types_dynamic.py backend/api/monitoring_types_dynamic.py.BACKUP
   ```

---

## 🔧 MODIFICAÇÕES NECESSÁRIAS

### PASSO 1: Adicionar Imports (Linha ~15)

**ANTES:**
```python
from fastapi import APIRouter, HTTPException, Query
from typing import Dict, List, Any, Optional
import re
```

**DEPOIS:**
```python
from fastapi import APIRouter, HTTPException, Query
from typing import Dict, List, Any, Optional
import re

# ⭐ ADICIONAR estes imports
from core.categorization_rule_engine import CategorizationRuleEngine
from core.consul_kv_config_manager import ConsulKVConfigManager
```

---

### PASSO 2: Instanciar Engine Globalmente (Linha ~30)

**ADICIONAR APÓS as definições de constantes:**

```python
# ⭐ Instanciar engine de categorização globalmente
_config_manager = ConsulKVConfigManager()
_categorization_engine = CategorizationRuleEngine(_config_manager)
_engine_loaded = False

async def _ensure_rules_loaded():
    """
    Garante que regras foram carregadas do KV uma única vez.

    Esta função é chamada automaticamente antes de categorizar.
    """
    global _engine_loaded
    if not _engine_loaded:
        logger.info("[CATEGORIZATION] Carregando regras do Consul KV...")
        await _categorization_engine.load_rules()
        _engine_loaded = True
        logger.info(f"[CATEGORIZATION] {len(_categorization_engine.rules)} regras carregadas")
```

---

### PASSO 3: Substituir Função _infer_category_and_type (Linha ~200)

**LOCALIZAR** a função que tem 200+ linhas com if/elif:
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

    # Blackbox detection (50 linhas)
    is_blackbox = (...)

    # Node Exporter (20 linhas)
    if 'node' in job_lower:
        ...

    # MySQL (15 linhas)
    if 'mysql' in job_lower:
        ...

    # ... mais 150 linhas de if/elif
```

**SUBSTITUIR COMPLETAMENTE POR:**
```python
async def _infer_category_and_type(job_name: str, job_config: Dict) -> tuple:
    """
    ⭐ NOVA IMPLEMENTAÇÃO: Usa CategorizationRuleEngine

    Migrado de lógica hardcoded (250 linhas) para regras JSON no KV.

    Args:
        job_name: Nome do job do Prometheus (ex: "icmp", "mysql-exporter")
        job_config: Configuração do job com relabel_configs, metrics_path, etc

    Returns:
        tuple: (categoria, dict_com_info_do_tipo)

    Exemplo:
        >>> await _infer_category_and_type("icmp", {"metrics_path": "/probe"})
        ("network-probes", {"id": "icmp", "display_name": "Blackbox: ICMP", ...})
    """
    # STEP 1: Garantir que regras foram carregadas do KV
    await _ensure_rules_loaded()

    # STEP 2: Preparar dados do job para o engine
    job_data = {
        'job_name': job_name,
        'metrics_path': job_config.get('metrics_path', '/metrics'),
        'labels': {}
    }

    # STEP 3: Extrair module se for blackbox (metrics_path = /probe)
    if job_config.get('metrics_path') == '/probe':
        # Procurar __param_module nos relabel_configs
        module = None
        for relabel in job_config.get('relabel_configs', []):
            if relabel.get('target_label') == '__param_module':
                module = relabel.get('replacement')
                break

        if module:
            job_data['labels']['module'] = module

    # STEP 4: Usar engine para categorizar (aplica 47 regras com prioridade)
    result = _categorization_engine.categorize(job_data)

    # STEP 5: Converter resultado do engine para formato esperado pelo código existente
    category = result['category']

    # Extrair campos metadata dos relabel_configs
    fields = _extract_metadata_fields(job_config)

    type_info = {
        'id': job_name,
        'display_name': result['display_name'],
        'category': category,
        'job_name': job_name,
        'matched_rule_id': result.get('matched_rule_id'),
        'exporter_type': result.get('exporter_type', 'unknown'),
        'fields': fields,
        'metrics_path': job_config.get('metrics_path', '/metrics')
    }

    # Adicionar module se for blackbox
    if 'module' in job_data['labels']:
        type_info['module'] = job_data['labels']['module']

    logger.debug(f"[CATEGORIZATION] {job_name} → {category} (regra: {result.get('matched_rule_id')})")

    return category, type_info
```

**⚠️ IMPORTANTE:** Note que a função agora é `async` (antes era `def`, agora é `async def`)

---

### PASSO 4: Atualizar Chamadas da Função (Linha ~400)

**LOCALIZAR** onde a função é chamada (geralmente dentro de `extract_monitoring_types_from_prometheus`):

**ANTES:**
```python
category, type_info = _infer_category_and_type(job_name, job_config)
```

**DEPOIS:**
```python
category, type_info = await _infer_category_and_type(job_name, job_config)
```

**⚠️ ADICIONAR `await` em TODAS as chamadas!**

---

### PASSO 5: Remover Código Hardcoded (Opcional - Após Validação)

**APÓS TESTAR** que tudo funciona, você pode remover:

1. **Dicionário EXPORTER_PATTERNS** (linhas ~85-120):
```python
# ❌ REMOVER APÓS VALIDAR
EXPORTER_PATTERNS = {
    'haproxy': ('infrastructure-exporters', 'HAProxy Exporter', 'haproxy_exporter'),
    'nginx': ('infrastructure-exporters', 'Nginx Exporter', 'nginx_exporter'),
    # ... 40+ linhas
}
```

2. **Lista BLACKBOX_MODULES** (linhas ~70-82):
```python
# ❌ REMOVER APÓS VALIDAR
BLACKBOX_MODULES = ['icmp', 'ping', 'tcp_connect', ...]
```

**⚠️ DEIXE ESTE CÓDIGO COMENTADO** até ter 100% de certeza que tudo funciona!

---

## ✅ VALIDAÇÃO DA MIGRAÇÃO

### Teste 1: Endpoint ainda funciona

```bash
curl "http://localhost:5000/api/v1/monitoring-types-dynamic/from-prometheus?server=ALL" | jq
```

**Esperado:** JSON com 8 categorias e 15+ tipos

---

### Teste 2: Categorização é idêntica

```bash
# Salvar resultado ANTES da migração (se tiver backup)
curl "http://localhost:5000/api/v1/monitoring-types-dynamic/from-prometheus?server=ALL" > /tmp/before.json

# Fazer migração

# Salvar resultado DEPOIS
curl "http://localhost:5000/api/v1/monitoring-types-dynamic/from-prometheus?server=ALL" > /tmp/after.json

# Comparar
diff /tmp/before.json /tmp/after.json
```

**Esperado:** Sem diferenças (ou diferenças apenas em `matched_rule_id`)

---

### Teste 3: 4 Páginas carregam

```bash
# Network Probes
curl "http://localhost:5000/api/v1/monitoring/data?category=network-probes" | jq '.total'

# Web Probes
curl "http://localhost:5000/api/v1/monitoring/data?category=web-probes" | jq '.total'

# System Exporters
curl "http://localhost:5000/api/v1/monitoring/data?category=system-exporters" | jq '.total'

# Database Exporters
curl "http://localhost:5000/api/v1/monitoring/data?category=database-exporters" | jq '.total'
```

**Esperado:** Cada categoria retorna número > 0

---

### Teste 4: Frontend carrega

Abrir no navegador:
- http://localhost:8081/monitoring/network-probes
- http://localhost:8081/monitoring/web-probes
- http://localhost:8081/monitoring/system-exporters
- http://localhost:8081/monitoring/database-exporters

**Esperado:** Tabelas com dados, sem erros no console

---

## 🐛 TROUBLESHOOTING

### Problema: "CategorizationRuleEngine not found"

**Causa:** Import incorreto ou arquivo não existe

**Solução:**
```bash
ls -lh backend/core/categorization_rule_engine.py
# Deve mostrar arquivo de ~390 linhas
```

---

### Problema: "No rules loaded"

**Causa:** Regras não estão no KV ou engine não conseguiu carregar

**Solução:**
```bash
# Verificar KV
curl "http://172.16.1.26:8500/v1/kv/skills/eye/monitoring-types/categorization/rules?raw" | jq '.total_rules'

# Se retornar erro, executar migração
cd backend
python migrate_categorization_to_json.py
```

---

### Problema: "Categorização diferente do esperado"

**Causa:** Prioridade das regras ou patterns incorretos

**Solução:**
```bash
# Ver qual regra foi aplicada
curl "http://localhost:5000/api/v1/monitoring-types-dynamic/from-prometheus?server=ALL" | jq '.all_types[] | {id, category, matched_rule_id}'

# Verificar regra específica no KV
curl "http://172.16.1.26:8500/v1/kv/skills/eye/monitoring-types/categorization/rules?raw" | jq '.rules[] | select(.id=="blackbox_icmp")'
```

---

### Problema: "await outside async function"

**Causa:** Esqueceu de adicionar `async` na definição da função

**Solução:** Trocar `def` por `async def` na linha da definição

---

## 📊 RESUMO DAS MUDANÇAS

| Item | Antes | Depois |
|------|-------|--------|
| Linhas de código | ~250 linhas | ~30 linhas |
| Lógica | Hardcoded if/elif | Regras JSON no KV |
| Manutenção | Editar Python | Editar JSON via UI |
| Padrões | 47 hardcoded | 47 em KV (editáveis) |
| Função | `def` síncrona | `async def` assíncrona |
| Testes | Difícil | Fácil (mock KV) |

---

## ✅ CHECKLIST FINAL

Antes de considerar migração completa:

- [ ] Imports adicionados no topo do arquivo
- [ ] Engine instanciado globalmente
- [ ] Função `_ensure_rules_loaded()` criada
- [ ] Função `_infer_category_and_type` substituída por versão async
- [ ] `await` adicionado em TODAS as chamadas
- [ ] Backup do arquivo original feito
- [ ] Teste 1 passou (endpoint funciona)
- [ ] Teste 2 passou (categorização idêntica)
- [ ] Teste 3 passou (4 endpoints retornam dados)
- [ ] Teste 4 passou (frontend carrega)

---

**Dúvidas?** Consulte `docs/README_MONITORING_PAGES.md` ou abra uma issue no repositório.
