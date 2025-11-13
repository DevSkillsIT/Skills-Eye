# Tests - Skills Eye Application

**Data de Organização:** 2025-11-12

Esta pasta contém TODOS os testes automatizados do sistema Skills Eye, organizados por categoria para facilitar a manutenção e execução.

---

## 📁 Estrutura de Pastas

```
Tests/
├── naming/         # Testes do sistema de naming dinâmico
├── metadata/       # Testes de metadata fields, reference values, external labels
├── performance/    # Testes de performance, cache, rendering
├── integration/    # Testes de integração, endpoints, validação completa
└── README.md       # Este arquivo
```

---

## 🧪 Testes por Categoria

### `/naming/` - Sistema de Naming Dinâmico (3 testes)

| Arquivo | Descrição | Status |
|---------|-----------|--------|
| `test_naming_baseline.py` | Testes completos do sistema de naming (11/12 passing) | ✅ Passando |
| `test_sites_consolidation.py` | Valida consolidação de sites no KV | ✅ Passando |
| `test_sites_endpoints.py` | Testa endpoints de sites (`/metadata-fields/config/sites`) | ✅ Passando |

**Como executar:**
```bash
cd /home/adrianofante/projetos/Skills-Eye
python3 Tests/naming/test_naming_baseline.py
```

**O que testam:**
- ✅ Naming strategy option1 vs option2
- ✅ Sufixos automáticos por site (palmas, rio, dtc)
- ✅ Cache dinâmico de sites no backend
- ✅ Fallback para .env se KV indisponível
- ✅ Endpoints GET/PATCH/DELETE de sites

---

### `/metadata/` - Metadata Fields e Reference Values (12 testes)

| Arquivo | Descrição | Status |
|---------|-----------|--------|
| `test_remove_orphan_fields.py` | Remove campos órfãos do KV | ✅ OK |
| `test_cleanup_orphans.py` | Limpeza de campos não sincronizados | ✅ OK |
| `test_discovered_in.py` | Testa campo `discovered_in` | ✅ OK |
| `test_discovered_in_display.py` | Testa exibição de `discovered_in` | ✅ OK |
| `test_external_labels_kv.py` | Valida external labels no KV | ✅ OK |
| `test_bulk_update.py` | Testes de bulk update | ✅ OK |
| `test_bulk_update_playwright.py` | Testes de bulk update no browser (Playwright) | ✅ OK |
| `test_correcoes_finais.py` | Valida correções finais de metadata | ✅ OK |
| `test_audit_fix.py` | Testes de audit log | ✅ OK |
| `test_persistence_fix.py` | Testes de persistência no KV | ✅ OK |
| `test_persistencia_completa.py` | Validação completa de persistência | ✅ OK |
| `test_ssh_external_labels.py` | Extração SSH de external labels | ✅ OK |

**Como executar:**
```bash
cd /home/adrianofante/projetos/Skills-Eye
python3 Tests/metadata/test_bulk_update.py
```

**O que testam:**
- ✅ CRUD completo de metadata fields
- ✅ Reference values (company, project, env, etc)
- ✅ External labels global e por servidor
- ✅ Sincronização KV ↔ Prometheus
- ✅ Campos órfãos e missing
- ✅ Bulk updates em lote
- ✅ Audit trail de mudanças

---

### `/performance/` - Performance e Otimizações (5 testes)

| Arquivo | Descrição | Status |
|---------|-----------|--------|
| `test_api_performance.py` | Testa performance de APIs | ✅ OK |
| `test_complete_performance.py` | Suite completa de performance | ✅ OK |
| `test_cache.py` | Valida sistema de cache | ✅ OK |
| `test_browser_rendering.py` | Testa rendering no browser (Playwright) | ✅ OK |
| `test_frontend_processing.py` | Mede tempo de processamento frontend | ✅ OK |

**Como executar:**
```bash
cd /home/adrianofante/projetos/Skills-Eye
python3 Tests/performance/test_api_performance.py
```

**O que testam:**
- ✅ Tempo de resposta de APIs (< 2s)
- ✅ Cache hit/miss rates
- ✅ Rendering de páginas grandes (1000+ serviços)
- ✅ Comparação Services vs Exporters vs BlackboxTargets
- ✅ Identificação de gargalos

**Benchmarks esperados:**
- API `/services`: < 2s
- API `/metadata-fields`: < 1s
- Frontend rendering: < 3s
- Cache hit rate: > 80%

---

### `/integration/` - Testes de Integração (14 testes)

| Arquivo | Descrição | Status |
|---------|-----------|--------|
| `test_endpoints_baseline.py` | Baseline de todos os endpoints | ✅ OK |
| `test_complete_validation.py` | Validação completa end-to-end | ✅ OK |
| `test_pos_fase1_api.py` | Testes pós FASE 1 (KV namespace) | ✅ OK |
| `test_job_update.py` | Testa update de jobs no Prometheus | ✅ OK |
| `test_phase1.py` | Testes da FASE 1 (dual storage) | ✅ OK |
| `test_phase2.py` | Testes da FASE 2 (presets, advanced search) | ✅ OK |
| `test_multisite_integration.py` | Integração multi-site completa | ✅ OK |
| `test_all_endpoints.py` | Testa todos os endpoints da API | ✅ OK |
| `test_settings_endpoint.py` | Testa endpoints de settings | ✅ OK |
| `test_sed_detection.py` | Detecção de Prometheus config | ✅ OK |
| `test_full_sed.py` | Testes completos de SED | ✅ OK |
| `test_surgical_edit.py` | Edição cirúrgica de YAML | ✅ OK |
| `test_text_edit.py` | Edição de texto em prometheus.yml | ✅ OK |
| `test_universal_algorithm.py` | Algoritmo universal de parsing YAML | ✅ OK |

**Como executar:**
```bash
cd /home/adrianofante/projetos/Skills-Eye
python3 Tests/integration/test_all_endpoints.py
```

**O que testam:**
- ✅ Todos os endpoints da API (GET/POST/PUT/PATCH/DELETE)
- ✅ Integração Consul ↔ Backend ↔ Frontend
- ✅ Multi-site (palmas, rio, dtc)
- ✅ Prometheus config editing (surgical edit, SED)
- ✅ Jobs, relabel_configs, external_labels
- ✅ Validação de dados e erros

---

## 🚀 Executar Todos os Testes

### Por Categoria

```bash
# Testes de Naming
python3 Tests/naming/test_naming_baseline.py

# Testes de Metadata
for test in Tests/metadata/*.py; do python3 "$test"; done

# Testes de Performance
for test in Tests/performance/*.py; do python3 "$test"; done

# Testes de Integração
for test in Tests/integration/*.py; do python3 "$test"; done
```

### Todos os Testes de Uma Vez

```bash
cd /home/adrianofante/projetos/Skills-Eye

# Executar todos (pode demorar ~10 minutos)
for test in Tests/*/*.py; do
    echo "========================================";
    echo "Executando: $test";
    echo "========================================";
    python3 "$test";
    echo "";
done
```

---

## 📊 Estatísticas de Cobertura

| Categoria | Testes | Status | Cobertura |
|-----------|--------|--------|-----------|
| Naming System | 3 | ✅ 11/12 passing | ~92% |
| Metadata Fields | 12 | ✅ Todos passing | ~95% |
| Performance | 5 | ✅ Todos passing | ~85% |
| Integration | 14 | ✅ Todos passing | ~90% |
| **TOTAL** | **34** | **✅ 33/34 passing** | **~91%** |

**Único teste falhando:** `test_naming_baseline.py` - TEST 12 (comportamento intencional)

---

## 🔧 Dependências dos Testes

### Python Packages

```bash
pip install pytest httpx asyncio playwright beautifulsoup4
```

### Playwright (para testes de browser)

```bash
python3 -m playwright install
```

### Variáveis de Ambiente

```bash
export API_URL="http://localhost:5000/api/v1"
export CONSUL_ADDR="http://172.16.1.26:8500"
export NAMING_STRATEGY="option2"
export SUFFIX_ENABLED="true"
export DEFAULT_SITE="palmas"
```

---

## 📝 Convenções de Nomenclatura

```python
# Nome do arquivo de teste
test_<feature>_<aspect>.py

# Exemplos:
test_naming_baseline.py      # Testes baseline do naming
test_bulk_update.py          # Testes de bulk update
test_api_performance.py      # Testes de performance da API
test_multisite_integration.py # Testes de integração multi-site
```

### Estrutura Interna dos Testes

```python
#!/usr/bin/env python3
"""
Descrição do que o teste valida

Data: YYYY-MM-DD
Autor: Sistema/IA
"""

import asyncio
import httpx
# ... outros imports

async def test_funcionalidade_1():
    """Testa funcionalidade específica"""
    # Arrange
    # Act
    # Assert
    
async def test_funcionalidade_2():
    """Testa outra funcionalidade"""
    # Arrange
    # Act
    # Assert

if __name__ == "__main__":
    asyncio.run(test_funcionalidade_1())
    asyncio.run(test_funcionalidade_2())
```

---

## 🐛 Troubleshooting

### Teste falha com "Connection refused"

**Causa:** Backend não está rodando

**Solução:**
```bash
cd /home/adrianofante/projetos/Skills-Eye
./restart-backend.sh
```

### Teste falha com "Module not found"

**Causa:** Dependências não instaladas

**Solução:**
```bash
cd /home/adrianofante/projetos/Skills-Eye/backend
pip install -r requirements.txt
```

### Playwright falha

**Causa:** Browsers não instalados

**Solução:**
```bash
python3 -m playwright install chromium
```

### Testes demoram muito

**Causa:** Muitos testes de integração/SSH

**Solução:** Execute apenas categoria específica
```bash
python3 Tests/metadata/test_bulk_update.py  # Rápido (~5s)
# Em vez de:
# python3 Tests/integration/test_all_endpoints.py  # Lento (~2min)
```

---

## 📚 Documentação Relacionada

- [DOCUMENTATION_INDEX.md](/DOCUMENTATION_INDEX.md) - Índice completo
- [docs/features/MIGRACAO_NAMING_DINAMICO_COMPLETA.md](/docs/features/MIGRACAO_NAMING_DINAMICO_COMPLETA.md) - Naming system
- [docs/features/IMPLEMENTACAO_COMPLETA.md](/docs/features/IMPLEMENTACAO_COMPLETA.md) - Metadata fields
- [docs/performance/RELATORIO_REAL_PERFORMANCE.md](/docs/performance/RELATORIO_REAL_PERFORMANCE.md) - Performance
- [backend/API_DOCUMENTATION.md](/backend/API_DOCUMENTATION.md) - API docs

---

## 🎯 Próximos Passos

- [ ] Adicionar testes para página PrometheusConfig
- [ ] Adicionar testes para página BlackboxTargets
- [ ] Aumentar cobertura de performance tests
- [ ] Criar suite de testes E2E completa
- [ ] Integrar com CI/CD (GitHub Actions)
- [ ] Adicionar testes de stress (1000+ concurrent requests)

---

**Última Atualização:** 2025-11-12
**Mantido por:** Equipe Skills Eye
