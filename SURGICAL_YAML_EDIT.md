# Sistema de Edição Cirúrgica de YAML

## 🎯 Objetivo

Implementar edição **cirúrgica** de arquivos YAML Prometheus, modificando **apenas as linhas alteradas** e preservando:
- ✅ Comentários
- ✅ Formatação original
- ✅ Espaçamento
- ✅ Estrutura
- ✅ Ordem dos campos

## 📋 Problema Anterior

Antes, quando você editava uma única linha como:
```yaml
tags: ['http_4xx']  →  tags: ['http_4xx-teste']
```

O sistema:
1. ❌ Lia o arquivo completo
2. ❌ **Deletava todos os jobs**
3. ❌ **Reconstruía todos os jobs do zero**
4. ❌ Reescrevia o arquivo inteiro

Isso causava:
- Perda sutil de formatação
- Possível reorganização de estruturas
- Re-parse desnecessário

## ✅ Solução Implementada

### 1. Método `_update_dict_surgically()`

Novo método em [multi_config_manager.py](backend/core/multi_config_manager.py#L648-L715) que:

**Funcionalidades:**
- Compara campo por campo entre valor antigo e novo
- Modifica **apenas** valores que mudaram
- Preserva objetos `CommentedMap` e `CommentedSeq` do ruamel.yaml
- Recursão para objetos aninhados
- Logs detalhados de cada modificação

**Exemplo de log:**
```
[CIRÚRGICO] ✏️  Modificando: job[http_4xx].consul_sd_configs[0].tags
              Antes: ['http_4xx']
              Depois: ['http_4xx-teste']
```

### 2. Método `update_jobs_in_file()` Refatorado

Novo fluxo em [multi_config_manager.py](backend/core/multi_config_manager.py#L717-L805):

**Etapas:**
1. Lê configuração atual preservando metadados ruamel.yaml
2. Cria mapa de jobs (antigos vs novos) por `job_name`
3. Para cada job existente:
   - **Edição cirúrgica**: atualiza apenas campos modificados
4. Adiciona novos jobs (que não existiam antes)
5. Remove jobs deletados (se aplicável)
6. Gera YAML preservando estrutura
7. Salva arquivo

**Diferença chave:**
```python
# ❌ ANTES: Deletar tudo e reconstruir
original_scrape_configs.clear()
for job in jobs:
    original_scrape_configs.append(job_yaml)

# ✅ AGORA: Edição cirúrgica
for job_name, new_job in jobs_map.items():
    if job_name in original_jobs_map:
        changes = self._update_dict_surgically(old_job, new_job)
```

### 3. Atualização do Frontend

Modificação em [PrometheusConfig.tsx](frontend/src/pages/PrometheusConfig.tsx#L432-L435):

**Adicionado após salvar:**
```typescript
// CRÍTICO: Recarregar dados do servidor após salvar
await axios.post(`${API_URL}/prometheus-config/clear-cache`);
await fetchJobs(selectedFile!);
```

**Por quê?**
- Garante que qualquer modificação do backend seja refletida
- Invalida cache para forçar releitura do arquivo
- Sincroniza estado frontend com realidade do servidor

## 🧪 Teste Automatizado

Criado [test_surgical_edit.py](backend/test_surgical_edit.py) que valida:

### Cenário de Teste
```yaml
# ANTES
tags: ['http_4xx']  # TAG ORIGINAL

# DEPOIS
tags:                 # TAG ORIGINAL
- http_4xx-teste
```

### Validações
- ✅ Comentário "# TAG ORIGINAL" preservado
- ✅ Outros comentários preservados
- ✅ Tag modificada presente
- ✅ Job node_exporter intacto (não modificado)
- ✅ Estrutura geral mantida

### Executar teste
```bash
cd backend
python test_surgical_edit.py
```

**Resultado esperado:**
```
[SUCESSO] TODOS OS TESTES PASSARAM!
[OK] Edicao cirurgica funcionando corretamente
[OK] Comentarios preservados
[OK] Apenas campo modificado foi alterado
```

## 🔧 Como Usar

### Reiniciar aplicação com cache limpo
```bash
# Na raiz do projeto
restart-app.bat
```

Esse script:
1. Mata processos Node.js e Python
2. Limpa `__pycache__` do backend
3. Limpa cache `.vite` do frontend
4. Reinicia ambos os servidores

### Editar via interface web

1. Acesse http://localhost:8081
2. Navegue até "Prometheus Config"
3. Selecione arquivo (ex: `/etc/prometheus/prometheus.yml`)
4. Edite job
5. Clique em "Salvar"

**Após salvar:**
- Backend aplica edição cirúrgica
- Cache é limpo automaticamente
- Dados são recarregados do servidor
- Modal de sucesso é exibido

## 📊 Comparação

| Aspecto | Antes | Agora |
|---------|-------|-------|
| Comentários | ⚠️ Podem ser perdidos | ✅ Preservados |
| Formatação | ⚠️ Pode mudar | ✅ Mantida |
| Performance | ❌ Reescreve tudo | ✅ Apenas mudanças |
| Logs | ❌ Genéricos | ✅ Detalhados por campo |
| Rastreabilidade | ❌ Baixa | ✅ Alta |
| Segurança | ⚠️ Maior risco | ✅ Menor risco |

## 🎓 Técnicas Utilizadas

### 1. Preservação de Metadados ruamel.yaml

```python
# NÃO fazer: perde metadados
config['scrape_configs'] = jobs

# FAZER: preserva CommentedSeq/CommentedMap
original_scrape_configs = config['scrape_configs']
for i, job in enumerate(jobs):
    self._update_dict_surgically(original_scrape_configs[i], job)
```

### 2. Deep Copy Correto

```python
# ❌ ERRADO: shallow copy
job_dict = dict(job)

# ✅ CORRETO: deep copy
import copy
job_dict = copy.deepcopy(dict(job))
```

### 3. Comparação Recursiva

```python
# Se ambos são dicts - recursão
if isinstance(new_value, dict) and isinstance(old_value, dict):
    sub_changes = self._update_dict_surgically(old_value, new_value)
```

## 🔍 Debugging

### Ver logs detalhados

No backend, os logs mostram cada modificação:
```
[CIRÚRGICO] Iniciando atualização cirúrgica
[CIRÚRGICO] Jobs no arquivo: 10
[CIRÚRGICO] Jobs novos: 10
[CIRÚRGICO] Atualizando job existente: http_4xx
[CIRÚRGICO] ✏️  Modificando: job[http_4xx].consul_sd_configs[0].tags
              Antes: ['http_4xx']
              Depois: ['http_4xx-teste']
[CIRÚRGICO] ✓ Job 'http_4xx' - 1 campo(s) modificado(s)
[CIRÚRGICO] ✅ Total de alterações: 1
```

### Testar manualmente via API

```bash
# Listar jobs
curl http://localhost:5000/api/v1/prometheus-config/file/jobs?file_path=/etc/prometheus/prometheus.yml

# Atualizar jobs (edição cirúrgica)
curl -X PUT http://localhost:5000/api/v1/prometheus-config/file/jobs?file_path=/etc/prometheus/prometheus.yml \
  -H "Content-Type: application/json" \
  -d @jobs.json
```

## 📝 Notas Importantes

1. **Não remove campos ausentes**: Se um campo não está no novo job mas estava no antigo, ele é **mantido**. Isso evita perda acidental de dados.

2. **Listas são atualizadas por completo**: Para listas (tags, services, etc), a lista inteira é substituída, mas mantendo o objeto `CommentedSeq`.

3. **Validação antes de salvar**: Arquivos Prometheus são validados com `promtool` antes de serem escritos no disco.

4. **Backup automático**: Antes de sobrescrever, um backup é criado automaticamente.

5. **Recarregamento após salvar**: Frontend recarrega dados após salvar para garantir sincronização.

## 🚀 Próximos Passos

- [ ] Adicionar comparação visual de diff antes de salvar
- [ ] Implementar undo/redo de edições
- [ ] Adicionar histórico de mudanças com timestamps
- [ ] Suportar edição cirúrgica em outros tipos de arquivos (blackbox.yml, alertmanager.yml)

## 📚 Referências

- [ruamel.yaml Documentation](https://yaml.readthedocs.io/)
- [Prometheus Configuration](https://prometheus.io/docs/prometheus/latest/configuration/configuration/)
- [CLAUDE.md - Project Documentation](CLAUDE.md)
