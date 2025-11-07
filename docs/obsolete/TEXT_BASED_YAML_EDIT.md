# Solução Definitiva: Edição TEXT-BASED de YAML

## 🎯 Problema

A abordagem ruamel.yaml NÃO está funcionando para preservar comentários porque:
1. Frontend envia JSON puro (sem metadados de comentários)
2. Tentar copiar `.ca` attributes causa erros
3. ruamel.yaml perde comentários ao fazer dump/load

## ✅ Solução: Edição Baseada em Texto/Regex

Para mudanças **simples e cirúrgicas** (como alterar uma tag), usar **edição de texto puro** é 100% confiável.

### Vantagens:
- ✅ **100% de preservação** de comentários, formatação, aspas
- ✅ **Simples e previsível**
- ✅ **Sem dependências** de ruamel.yaml internals
- ✅ **Rápido** (apenas substituição de string)

### Desvantagens:
- ❌ Limitado a mudanças simples (não pode adicionar/remover jobs facilmente)
- ❌ Precisa de cuidado com regex para não alterar partes erradas

## 📝 Implementação

### Estratégia Híbrida:

1. **Mudanças SIMPLES** → Edição TEXT-BASED
   - Alterar valor de um campo existente
   - Mudar tag, IP, porta, etc.

2. **Mudanças COMPLEXAS** → ruamel.yaml
   - Adicionar/remover jobs
   - Reestruturar arquivo
   - (Aceitar perda de comentários com aviso ao usuário)

### Código:

```python
def update_yaml_value_text_based(content: str, job_name: str, field_path: str, old_value: Any, new_value: Any) -> str:
    """
    Atualiza um valor específico no YAML usando edição de texto.

    Args:
        content: Conteúdo YAML como string
        job_name: Nome do job a modificar
        field_path: Caminho do campo (ex: "tags.0", "consul_sd_configs.0.server")
        old_value: Valor antigo (para validar)
        new_value: Novo valor

    Returns:
        Conteúdo YAML modificado
    """
    import re

    # Exemplo: Mudar tags: ['http_2xx'] → tags: ['http_2xx-teste']
    if field_path == "consul_sd_configs.0.tags":
        # Encontrar o job específico e substituir a linha de tags
        pattern = rf"(- job_name: ['\"]?{re.escape(job_name)}['\"]?.*?tags:\s*)\[.*?\]"
        replacement = rf"\1{new_value}"
        content = re.sub(pattern, replacement, content, flags=re.DOTALL)

    return content
```

## 🔍 Exemplo Real:

**ANTES:**
```yaml
- job_name: 'http_2xx'
  metrics_path: /probe
  params:
    module: [http_2xx]    # Módulo do Blackbox Exporter
  consul_sd_configs:
  - server: '172.16.1.26:8500'
    tags: ['http_2xx']      # Tag específica
```

**Regex:**
```python
pattern = r"(- job_name: 'http_2xx'.*?tags:\s*\[)[^\]]+(\])"
replacement = r"\1'http_2xx-teste'\2"
```

**DEPOIS:**
```yaml
- job_name: 'http_2xx'
  metrics_path: /probe
  params:
    module: [http_2xx]    # Módulo do Blackbox Exporter  ← PRESERVADO!
  consul_sd_configs:
  - server: '172.16.1.26:8500'
    tags: ['http_2xx-teste']      # Tag específica  ← PRESERVADO!
```

## 🚀 Próximos Passos:

1. Detectar se mudança é SIMPLES (apenas valores alterados)
2. Se SIMPLES → usar TEXT-BASED
3. Se COMPLEXO → usar ruamel.yaml com aviso de perda de comentários

## 📦 Implementação Completa:

Criar novo método em `multi_config_manager.py`:

```python
def detect_simple_change(self, old_jobs: List[Dict], new_jobs: List[Dict]) -> Optional[Dict]:
    """
    Detecta se a mudança é SIMPLES (apenas valores alterados em job existente).

    Returns:
        Dict com info da mudança se SIMPLES, None se COMPLEXO
    """
    if len(old_jobs) != len(new_jobs):
        return None  # Adicionou/removeu jobs - COMPLEXO

    # Criar mapa de jobs
    old_map = {j.get('job_name'): j for j in old_jobs}
    new_map = {j.get('job_name'): j for j in new_jobs}

    if set(old_map.keys()) != set(new_map.keys()):
        return None  # Jobs diferentes - COMPLEXO

    # Encontrar mudanças
    changes = []
    for job_name in old_map:
        old_job = old_map[job_name]
        new_job = new_map[job_name]

        # Comparar campos
        diff = find_diff(old_job, new_job)
        if diff:
            changes.append({
                'job_name': job_name,
                'diff': diff
            })

    # Se apenas 1 mudança simples, retornar
    if len(changes) == 1 and is_simple_diff(changes[0]['diff']):
        return changes[0]

    return None  # COMPLEXO
```

Esta é a **solução definitiva** para o problema!
