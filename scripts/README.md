# Scripts - Skills Eye

Esta pasta contém TODOS os scripts de automação do projeto, organizados por finalidade.

## 📂 Estrutura

```
scripts/
├── deployment/      # Scripts de deploy e restart (15 scripts)
├── migration/       # Scripts de migração de dados (5 scripts)
├── development/     # Scripts de análise e debug (7 scripts)
└── benchmarks/      # Scripts de performance tests (3 scripts)
```

---

## 🚀 deployment/ - Deploy e Restart

**Finalidade:** Reiniciar aplicação, backend, frontend, gerenciar processos

### Scripts Principais

| Script | Plataforma | Descrição |
|--------|-----------|-----------|
| `restart-all.sh` | Linux/WSL | Reinicia backend + frontend + limpa cache |
| `restart-app.sh` | Linux/WSL | Reinicia aplicação completa |
| `restart-app.bat` | Windows | Reinicia aplicação (CMD) |
| `restart-app.ps1` | Windows | Reinicia aplicação (PowerShell) |
| `restart-backend.sh` | Linux/WSL | Reinicia apenas backend |
| `restart-frontend.sh` | Linux/WSL | Reinicia apenas frontend |
| `start-app.sh` | Linux/WSL | Inicia aplicação |
| `start-backend.sh` | Linux/WSL | Inicia apenas backend |
| `start-frontend.sh` | Linux/WSL | Inicia apenas frontend |
| `stop-all.sh` | Linux/WSL | Para todos os processos |
| `stop-app.sh` | Linux/WSL | Para aplicação |

### Uso Típico

**Desenvolvimento local (WSL/Linux):**
```bash
# Reiniciar tudo
./scripts/deployment/restart-all.sh

# Reiniciar apenas backend após mudança na API
./scripts/deployment/restart-backend.sh

# Reiniciar apenas frontend após mudança na UI
./scripts/deployment/restart-frontend.sh
```

**Windows:**
```cmd
# CMD
scripts\deployment\restart-app.bat

# PowerShell
.\scripts\deployment\restart-app.ps1
```

---

## 🔄 migration/ - Migrações de Dados

**Finalidade:** Migrar dados entre versões, namespaces, estruturas

### Scripts Principais

| Script | Descrição | Quando Usar |
|--------|-----------|-------------|
| `migrate_consul_kv.py` | Migra dados no Consul KV | Mudança de schema KV |
| `migrate_namespace.py` | Migra entre namespaces | Mudança de namespace |
| `migrate_naming_to_kv.py` | Migra naming patterns para KV | Atualização do sistema de nomenclatura |
| `migrate_sites_structure.py` | Migra estrutura de sites | Mudança multi-site |
| `validate_migration.py` | Valida integridade pós-migração | Após qualquer migração |

### Uso Típico

```bash
# Executar migração
cd /home/adrianofante/projetos/Skills-Eye
python scripts/migration/migrate_consul_kv.py

# SEMPRE validar depois
python scripts/migration/validate_migration.py
```

**⚠️ IMPORTANTE:**
- Faça backup antes de migrar
- Teste em ambiente de desenvolvimento primeiro
- SEMPRE execute `validate_migration.py` após migração

---

## 🔬 development/ - Análise e Debug

**Finalidade:** Análise de performance, debug, comparação de páginas

### Scripts Principais

| Script | Descrição | Quando Usar |
|--------|-----------|-------------|
| `analyze_profile.py` | Analisa profile de performance | Debug de lentidão |
| `analyze_profile_1613.py` | Análise específica de profile | Caso específico |
| `analyze_react_complexity.py` | Analisa complexidade do React | Otimizar frontend |
| `compare_pages_performance.py` | Compara performance entre páginas | A/B testing de páginas |
| `inspect_profile.py` | Inspeção detalhada de profiles | Debug profundo |
| `test_single_server_extraction.sh` | Testa extração de 1 servidor | Debug de SSH/YAML |

### Uso Típico

```bash
# Analisar performance de uma página
python scripts/development/analyze_profile.py

# Comparar Services vs Exporters
python scripts/development/compare_pages_performance.py

# Analisar complexidade do código React
python scripts/development/analyze_react_complexity.py
```

**Output Esperado:**
- Gráficos de flame graph
- Métricas de tempo de execução
- Sugestões de otimização

---

## ⚡ benchmarks/ - Performance Tests

**Finalidade:** Medir performance de API e frontend

### Scripts Principais

| Script | Plataforma | Descrição |
|--------|-----------|-----------|
| `benchmark-api-before.bat` | Windows | Benchmark da API (antes de mudança) |
| `benchmark-frontend-before.ps1` | Windows | Benchmark do frontend (antes de mudança) |
| `run-benchmark-api.ps1` | Windows | Executa benchmark da API |

### Uso Típico

**Antes de otimização:**
```bash
# Baseline ANTES da mudança
.\scripts\benchmarks\benchmark-api-before.bat
```

**Depois de otimização:**
```bash
# Benchmark DEPOIS da mudança
.\scripts\benchmarks\run-benchmark-api.ps1

# Comparar resultados
```

**Métricas Medidas:**
- Tempo de resposta (ms)
- Throughput (req/s)
- Taxa de erro (%)
- Percentis (P50, P95, P99)

---

## 🔧 Manutenção de Scripts

### Adicionar Novo Script

1. **Identifique a categoria:**
   - Deploy/Restart → `deployment/`
   - Migração de dados → `migration/`
   - Análise/Debug → `development/`
   - Performance test → `benchmarks/`

2. **Adicione permissão de execução (Linux):**
   ```bash
   chmod +x scripts/categoria/meu_script.sh
   ```

3. **Documente no README:**
   - Adicione linha na tabela apropriada
   - Descreva finalidade e uso

4. **Teste antes de commitar:**
   ```bash
   # Teste o script
   ./scripts/categoria/meu_script.sh
   
   # Valide que funcionou
   ```

### Boas Práticas

- ✅ Scripts DEVEM ter comentários explicativos
- ✅ Scripts DEVEM validar pré-requisitos (ex: serviço rodando)
- ✅ Scripts DEVEM ter saída clara (logs, mensagens)
- ✅ Scripts DEVEM ter tratamento de erro
- ❌ NUNCA hardcode credenciais em scripts
- ❌ NUNCA commite scripts com dados sensíveis

---

## 📝 Logs de Execução

Scripts podem gerar logs em `/logs/`:
```bash
# Ver logs recentes
tail -f /home/adrianofante/projetos/Skills-Eye/logs/backend.log

# Ver logs de migração
cat /home/adrianofante/projetos/Skills-Eye/logs/migration_report.txt
```

---

## 🔗 Ver Também

- [Tests/README.md](../Tests/README.md) - Testes automatizados
- [docs/guides/restart-guide.md](../docs/guides/restart-guide.md) - Guia de restart
- [COMANDOS_RAPIDOS.md](../COMANDOS_RAPIDOS.md) - Quick reference
