# Data - Dados de Teste e Baselines

Esta pasta contém TODOS os dados de teste, baselines e fixtures do projeto.

## 📂 Estrutura

```
data/
├── baselines/       # Baselines JSON para comparação (3 arquivos)
├── fixtures/        # Fixtures de teste reutilizáveis (4 arquivos)
└── temp/            # Arquivos temporários (gitignored)
```

---

## 📊 baselines/ - Dados de Baseline

**Finalidade:** Snapshots de dados conhecidos para comparação em testes e validações

### Arquivos

| Arquivo | Descrição | Quando Criado |
|---------|-----------|---------------|
| `BASELINE_ENDPOINTS.json` | Lista de endpoints da API | Setup inicial |
| `BASELINE_PRE_MIGRATION.json` | Dados antes de migração | Antes de migração KV |
| `TESTE_POS_FASE1_API.json` | Estado pós-Fase 1 | Após implementação Fase 1 |

### Uso

```python
import json

# Carregar baseline
with open('data/baselines/BASELINE_ENDPOINTS.json', 'r') as f:
    baseline = json.load(f)

# Comparar com estado atual
current_endpoints = get_current_endpoints()
diff = compare(baseline, current_endpoints)

if diff:
    print(f"❌ Divergências encontradas: {diff}")
else:
    print("✅ Sistema conforme baseline")
```

### Quando Criar Nova Baseline

- ✅ Antes de mudanças estruturais grandes
- ✅ Antes de migrações de dados
- ✅ Após implementação de fase importante
- ✅ Para documentar estado "conhecido como bom"

**Comando:**
```bash
# Criar nova baseline
python -c "import json; json.dump(get_current_state(), open('data/baselines/BASELINE_NEW.json', 'w'), indent=2)"
```

---

## 🧩 fixtures/ - Fixtures de Teste

**Finalidade:** Dados de teste reutilizáveis para testes automatizados

### Arquivos

| Arquivo | Descrição | Usado Por |
|---------|-----------|-----------|
| `test_3servers.json` | Config de 3 servidores | Testes multi-site |
| `test_exporters_fields.json` | Campos de exporters | Testes de campos dinâmicos |
| `test_filtered.json` | Dados filtrados | Testes de busca |
| `test_parallel.json` | Dados para testes paralelos | Testes de performance |

### Uso

```python
import json
import pytest

@pytest.fixture
def three_servers():
    """Fixture de 3 servidores para testes multi-site"""
    with open('data/fixtures/test_3servers.json', 'r') as f:
        return json.load(f)

def test_multi_site(three_servers):
    # Usar fixture
    result = process_servers(three_servers)
    assert len(result) == 3
```

### Criar Nova Fixture

1. **Identifique o caso de teste:**
   ```python
   # Exemplo: teste de campos de exporter Redis
   fixture_data = {
       "exporter": "redis",
       "fields": {
           "host": "redis.example.com",
           "port": 6379,
           "password": "test123"
       }
   }
   ```

2. **Salve em JSON:**
   ```python
   import json
   with open('data/fixtures/test_redis_exporter.json', 'w') as f:
       json.dump(fixture_data, f, indent=2)
   ```

3. **Use em testes:**
   ```python
   def test_redis_exporter():
       with open('data/fixtures/test_redis_exporter.json') as f:
           fixture = json.load(f)
       # Usar fixture...
   ```

---

## 🗑️ temp/ - Arquivos Temporários

**Finalidade:** Arquivos gerados durante execução (gitignored)

### Conteúdo Típico

- `temp_*.json` - Respostas de API temporárias
- `temp_profile_*.json` - Profiles de performance
- `temp_cache_*.json` - Cache temporário

### ⚠️ Importante

**Esta pasta é IGNORADA pelo Git:**
```bash
# .gitignore
data/temp/
temp_*.json
```

**Nunca commite arquivos temp:**
- ❌ Contêm dados dinâmicos
- ❌ Podem ter dados sensíveis
- ❌ São regenerados automaticamente

**Limpeza:**
```bash
# Limpar temporários antigos
rm -rf data/temp/*

# Ou usar script
./scripts/deployment/restart-all.sh  # Limpa automaticamente
```

---

## 📝 Formato dos Arquivos

### JSON Padronizado

Todos os arquivos JSON devem seguir o padrão:

```json
{
  "metadata": {
    "created_at": "2025-11-12T10:30:00Z",
    "purpose": "Descrição da finalidade",
    "version": "1.0",
    "author": "developer_name"
  },
  "data": {
    // Dados reais aqui
  }
}
```

### Validação

```python
import json
import jsonschema

# Schema básico
schema = {
    "type": "object",
    "required": ["metadata", "data"],
    "properties": {
        "metadata": {
            "type": "object",
            "required": ["created_at", "purpose"]
        },
        "data": {"type": "object"}
    }
}

# Validar arquivo
with open('data/baselines/BASELINE_ENDPOINTS.json') as f:
    data = json.load(f)
    jsonschema.validate(data, schema)
```

---

## 🔧 Manutenção

### Atualizar Baseline

**Quando:** Após mudanças estruturais que alteram o "estado normal"

```bash
# 1. Backup da baseline antiga
cp data/baselines/BASELINE_ENDPOINTS.json data/baselines/BASELINE_ENDPOINTS.json.old

# 2. Gerar nova baseline
python scripts/development/generate_baseline.py > data/baselines/BASELINE_ENDPOINTS.json

# 3. Validar nova baseline
python scripts/migration/validate_migration.py
```

### Limpar Dados Antigos

```bash
# Remover baselines antigas (mais de 6 meses)
find data/baselines/ -name "*.json.old" -mtime +180 -delete

# Limpar temporários
rm -rf data/temp/*
```

### Versionar Baselines

```bash
# Criar versão timestamped
cp data/baselines/BASELINE_ENDPOINTS.json \
   data/baselines/BASELINE_ENDPOINTS_$(date +%Y%m%d).json

# Manter apenas últimas 5 versões
ls -t data/baselines/BASELINE_ENDPOINTS_*.json | tail -n +6 | xargs rm -f
```

---

## 🧪 Testes com Fixtures

### Exemplo Completo

```python
import pytest
import json
from pathlib import Path

# Carregar todas as fixtures
FIXTURES_DIR = Path(__file__).parent.parent / 'data' / 'fixtures'

@pytest.fixture
def load_fixture():
    """Factory para carregar fixtures"""
    def _load(filename):
        with open(FIXTURES_DIR / filename, 'r') as f:
            return json.load(f)
    return _load

def test_multi_server_processing(load_fixture):
    """Teste usando fixture de 3 servidores"""
    servers = load_fixture('test_3servers.json')
    
    result = process_servers(servers['data'])
    
    assert len(result) == 3
    assert all(s['status'] == 'online' for s in result)

def test_exporter_fields(load_fixture):
    """Teste usando fixture de campos"""
    fields = load_fixture('test_exporters_fields.json')
    
    result = validate_fields(fields['data'])
    
    assert result['valid'] is True
```

---

## 📊 Estatísticas

### Tamanho dos Dados

```bash
# Ver tamanho de cada categoria
du -sh data/*/

# Output esperado:
# 124K    data/baselines/
# 56K     data/fixtures/
# 8K      data/temp/
```

### Quantidades

```bash
# Contar arquivos
find data/baselines -type f | wc -l  # 3 baselines
find data/fixtures -type f | wc -l   # 4 fixtures
```

---

## 🔗 Ver Também

- [Tests/README.md](../Tests/README.md) - Como usar fixtures em testes
- [scripts/README.md](../scripts/README.md) - Scripts que geram dados
- [docs/guides/migration.md](../docs/guides/migration.md) - Guia de migração com baselines
