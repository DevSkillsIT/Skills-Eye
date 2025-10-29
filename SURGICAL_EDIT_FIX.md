# Correção da Edição Cirúrgica YAML - Preservação de Comentários

**Data:** 2025-10-28
**Status:** ✅ CORREÇÕES IMPLEMENTADAS - PRONTO PARA TESTE

---

## 🐛 Problema Identificado

Ao editar jobs no arquivo `prometheus.yml`:
- ✅ **Alterações aplicadas corretamente** (ex: `tags: ['http_2xx']` → `tags: ['http_2xx-teste']`)
- ❌ **TODOS os comentários perdidos** (inline e de seção)
- ❌ **Formatação alterada** (flow-style → block-style, aspas removidas)

### Exemplo do Problema:

**ANTES (prometheus.yml.backup):**
```yaml
# Monitoramento HTTP com código 2xx usando o Blackbox Exporter
- job_name: 'http_2xx'
  metrics_path: /probe
  params:
    module: [http_2xx]    # Módulo do Blackbox Exporter para monitorar HTTP
  consul_sd_configs:
  - server: '172.16.1.26:8500'      # Servidor Consul central
    token: '8382a112-81e0-cd6d-2b92-8565925a0675'
    services: ['blackbox_exporter']
    tags: ['http_2xx']      # Tag específica ← ALTERAÇÃO AQUI
```

**DEPOIS (prometheus.yml - PROBLEMA):**
```yaml
- job_name: http_2xx
  metrics_path: /probe
  params:
    module:
    - http_2xx
  consul_sd_configs:
  - server: 172.16.1.26:8500
    token: 8382a112-81e0-cd6d-2b92-8565925a0675
    services:
    - blackbox_exporter
    tags:
    - http_2xx-teste  ← MUDOU CORRETAMENTE, MAS PERDEU TUDO!
```

---

## 🔧 Correções Implementadas

### 1. Removida Substituição Destrutiva em `prometheus_config.py`

**Arquivo:** `backend/api/prometheus_config.py` (linha 790-792)

**ANTES (ERRADO):**
```python
# IMPORTANTE: Atualizar scrape_configs preservando estrutura ruamel.yaml
config['scrape_configs'] = jobs  # ← DESTRÓI comentários!
print(f"[UPDATE JOBS] scrape_configs atualizado com {len(jobs)} jobs")
```

**DEPOIS (CORRETO):**
```python
# IMPORTANTE: NÃO substituir scrape_configs aqui!
# Isso destrói comentários. A edição cirúrgica será feita em update_jobs_in_file()
print(f"[UPDATE JOBS] Mantendo estrutura original para preservar comentários")
```

**Motivo:** Substituir `config['scrape_configs'] = jobs` destruía toda a estrutura `CommentedMap` do ruamel.yaml, perdendo todos os comentários anexados.

---

### 2. Preservação de Flow-Style em Listas

**Arquivo:** `backend/core/yaml_config_service.py` (linha 66)

**ANTES (ERRADO):**
```python
self.yaml.default_flow_style = False  # Força block-style: ['a'] → - a
```

**DEPOIS (CORRETO):**
```python
self.yaml.default_flow_style = None  # None = preserva estilo original
```

**Motivo:** `False` forçava todas as listas para block-style. `None` preserva o estilo original (flow ou block).

---

### 3. Preservação de Flow Attributes em CommentedSeq

**Arquivo:** `backend/core/multi_config_manager.py` (linhas 688-709)

**ANTES (ERRADO):**
```python
if isinstance(old_value, CommentedSeq):
    old_value.clear()
    old_value.extend(new_value)  # ← Perde flow attributes!
```

**DEPOIS (CORRETO):**
```python
if isinstance(old_value, CommentedSeq):
    # Preservar flow attributes (se era ['a', 'b'], manter assim)
    fa = old_value.fa if hasattr(old_value, 'fa') else None

    old_value.clear()
    old_value.extend(new_value)

    # Restaurar flow attributes
    if fa is not None:
        old_value.fa = fa
```

**Motivo:** O `CommentedSeq.fa` (flow attributes) armazena informações de que a lista era flow-style. Ao fazer `.clear()` e `.extend()`, precisamos restaurar essa informação.

---

## ✅ Resultado Esperado

Agora ao editar `tags: ['http_2xx']` → `tags: ['http_2xx-teste']`, o arquivo DEVE ficar:

```yaml
# Monitoramento HTTP com código 2xx usando o Blackbox Exporter
- job_name: 'http_2xx'
  metrics_path: /probe
  params:
    module: [http_2xx]    # Módulo do Blackbox Exporter para monitorar HTTP
  consul_sd_configs:
  - server: '172.16.1.26:8500'      # Servidor Consul central
    token: '8382a112-81e0-cd6d-2b92-8565925a0675'
    services: ['blackbox_exporter']
    tags: ['http_2xx-teste']      # Tag específica ← APENAS ESTA LINHA MUDA!
```

**Preservado:**
- ✅ Comentários inline (ex: `# Módulo do Blackbox Exporter`)
- ✅ Comentários de seção (ex: `# Monitoramento HTTP com código 2xx`)
- ✅ Aspas simples (ex: `'http_2xx'` não vira `http_2xx`)
- ✅ Flow-style de listas (ex: `[http_2xx]` não vira `- http_2xx`)
- ✅ Formatação de listas inline (ex: `['a', 'b']` não vira `- a\\n- b`)

---

## 🧪 Como Testar

### 1. Certifique-se de ter backup
```bash
# No servidor 172.16.1.26
cp /etc/prometheus/prometheus.yml /etc/prometheus/prometheus.yml.backup-$(date +%Y%m%d-%H%M%S)
```

### 2. Acesse o frontend
- URL: http://localhost:8081
- Vá em "Prometheus Config"
- **Abra o Console do navegador (F12)**

### 3. Faça uma pequena edição
- Selecione o servidor 172.16.1.26
- Selecione o arquivo `/etc/prometheus/prometheus.yml`
- Edite um job (ex: job `http_2xx`)
- Altere algo pequeno (ex: mudar uma tag)
- Clique em "Salvar"

### 4. Verifique os logs

**Console do Navegador (F12 → Console):**
```
[CRITICAL] Payload sendo enviado: {...}
```

**Terminal do Backend:**
```
[CRITICAL BACKEND] Payload recebido: [...]
[CIRÚRGICO] Atualizando job existente: http_2xx
[CIRÚRGICO] ✏️  Modificando: job[http_2xx].consul_sd_configs.0.tags
```

### 5. Compare os arquivos

**No servidor 172.16.1.26:**
```bash
# Ver diferença entre backup e arquivo atualizado
diff /etc/prometheus/prometheus.yml.backup /etc/prometheus/prometheus.yml

# Ou usar git diff se arquivo estiver em git
git diff /etc/prometheus/prometheus.yml
```

**Resultado esperado:** Apenas a linha que você editou deve aparecer no diff!

---

## 📊 Checklist de Validação

Após salvar, verifique:

- [ ] **Comentários preservados:** Comentários inline e de seção continuam no arquivo
- [ ] **Flow-style preservado:** Listas como `['a', 'b']` não viraram block-style
- [ ] **Aspas preservadas:** Valores com aspas simples continuam com aspas
- [ ] **Apenas linha alterada mudou:** Diff mostra apenas a linha editada
- [ ] **Formatação geral intacta:** Indentação, espaçamento e estrutura mantidos

---

## 🐛 Se Ainda Houver Problemas

### Problema: Comentários ainda sendo perdidos

**Possível causa:** O arquivo foi lido de cache antes das correções.

**Solução:**
1. Limpar cache do backend:
   ```
   POST http://localhost:5000/api/v1/prometheus-config/clear-cache
   ```
2. Recarregar arquivo no frontend (botão "Recarregar")
3. Tentar novamente

### Problema: Flow-style ainda virando block-style

**Possível causa:** Backend antigo ainda rodando.

**Solução:**
1. Verificar se backend foi reiniciado:
   ```bash
   # Ver processos Python
   tasklist | findstr python
   ```
2. Matar processos antigos:
   ```bash
   taskkill /F /IM python.exe /T
   ```
3. Reiniciar backend:
   ```bash
   cd backend
   python app.py
   ```

### Problema: Arquivo corrompido durante teste

**Solução rápida:**
```bash
# Restaurar do backup
cp /etc/prometheus/prometheus.yml.backup /etc/prometheus/prometheus.yml

# Recarregar Prometheus
curl -X POST http://172.16.1.26:9090/-/reload
```

---

## 📝 Logs de Debug Disponíveis

Os logs detalhados agora mostram:

**Backend:**
- `[CRITICAL BACKEND] Payload recebido:` - JSON completo recebido do frontend
- `[CRITICAL BACKEND] Primeiro job:` - Primeiro job do payload
- `[CIRÚRGICO] Atualizando job existente:` - Qual job está sendo modificado
- `[CIRÚRGICO] ✏️  Modificando:` - Qual campo específico mudou
- `[CIRÚRGICO] Lista atualizada:` - Quando listas são atualizadas
- `[CIRÚRGICO] ✅ Total de alterações:` - Quantos campos foram modificados

**Frontend:**
- `[SAVE DEBUG] Estado atual:` - Estado antes de salvar
- `[CRITICAL] Payload sendo enviado:` - Payload completo enviado ao backend

---

## 🎯 Testes Recomendados

### Teste 1: Alterar apenas uma tag
```yaml
# ANTES
tags: ['http_2xx']

# DEPOIS (esperado)
tags: ['http_2xx-TESTE']
```

### Teste 2: Alterar um valor com comentário inline
```yaml
# ANTES
scrape_interval: 30s     # Intervalo de coleta

# DEPOIS (esperado - comentário preservado!)
scrape_interval: 60s     # Intervalo de coleta
```

### Teste 3: Adicionar um novo campo
```yaml
# ANTES
- job_name: 'http_2xx'
  metrics_path: /probe

# DEPOIS (esperado - comentário de seção preservado!)
- job_name: 'http_2xx'
  metrics_path: /probe
  scrape_timeout: 10s     # NOVO CAMPO ADICIONADO
```

---

## 🚀 Status

- ✅ Backend reiniciado com correções
- ✅ Frontend rodando (porta 8081)
- ⏳ **AGUARDANDO TESTE DO USUÁRIO**

**Próximo passo:** Testar uma edição pequena e verificar se comentários são preservados!

---

## 📄 Arquivos Modificados

1. `backend/api/prometheus_config.py` - Removida substituição destrutiva
2. `backend/core/yaml_config_service.py` - Preservação de flow-style
3. `backend/core/multi_config_manager.py` - Preservação de flow attributes
4. `backend/core/installers/windows_psexec.py` - Correção de indentação (não relacionado)
