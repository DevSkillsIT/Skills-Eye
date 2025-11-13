# Instruções de Uso - External Labels

## 🎯 O Que São External Labels?

**External labels** são labels **globais** configurados no `prometheus.yml` que identificam **unicamente cada servidor Prometheus**. Eles são adicionados AUTOMATICAMENTE pelo Prometheus a **todas as métricas** coletadas por aquele servidor.

### Exemplo de Configuração (prometheus.yml)
```yaml
# Servidor Prometheus de Palmas
global:
  external_labels:
    cluster: 'dtc-skills'
    datacenter: 'palmas'
    site: 'palmas'
    environment: 'production'
    prometheus_instance: '172.16.1.26'
```

```yaml
# Servidor Prometheus do Rio
global:
  external_labels:
    cluster: 'dtc-remote'
    datacenter: 'rio-de-janeiro'
    site: 'rio'
    environment: 'production'
    prometheus_instance: '172.16.200.14'
```

---

## 🖥️ Como Configurar External Labels no Sistema

### Passo 1: Acessar Página Settings

1. Acesse o menu **Configurações** / **Settings**
2. Role até a seção **Sites Configurados**

### Passo 2: Criar ou Editar um Site

#### Criar Novo Site
1. Clique no botão **Adicionar Site**
2. Preencha os campos:
   - **Código do Site:** Ex: `saopaulo`, `brasilia` (lowercase, sem espaços)
   - **Nome Descritivo:** Ex: "São Paulo (SP)"
   - **Site Padrão:** Marque se este site NÃO deve receber sufixo
   - **Cor do Badge:** Escolha uma cor para identificação visual

3. **Configuração Prometheus (Opcional mas Recomendado):**
   - **Host do Prometheus:** IP ou hostname do servidor (ex: `172.16.1.26`)
   - **Porta do Prometheus:** Porta do serviço (padrão: `9090`)

4. **External Labels (JSON):**
   ```json
   {
     "cluster": "dtc-skills",
     "datacenter": "palmas",
     "site": "palmas",
     "environment": "production"
   }
   ```

   **IMPORTANTE:**
   - Use formato JSON válido: `{"chave":"valor"}`
   - Copie os external_labels do `prometheus.yml` do servidor correspondente
   - Pode deixar vazio se não souber (pode preencher depois)

5. Clique em **Confirmar**

#### Editar Site Existente
1. Clique no botão **Editar** na linha do site
2. Modifique os campos necessários
3. Adicione/atualize o campo **External Labels** com o JSON correspondente
4. Clique em **Confirmar**

---

## 📊 Visualização dos External Labels

Na tabela de sites, você verá:

| Código | Nome | Site Padrão | Cor | **Prometheus** | **External Labels** |
|--------|------|-------------|-----|----------------|---------------------|
| palmas | Palmas (TO) | Sim | 🔵 | `172.16.1.26:9090` | 🏷️ 4 labels |
| rio | Rio de Janeiro (RJ) | Não | 🟢 | `172.16.200.14:9090` | 🏷️ 4 labels |
| dtc | DTC/Genesis | Não | 🟠 | `-` | Não configurado |

**Para ver os labels completos:**
- Passe o mouse sobre o badge "X labels"
- Um tooltip mostrará o JSON formatado completo

---

## ⚠️ Importante Entender

### O Que External Labels NÃO Fazem
❌ **NÃO são injetados** no Meta dos serviços do Consul
❌ **NÃO afetam** a forma como você registra serviços
❌ **NÃO mudam** o comportamento de sufixos automáticos

### O Que External Labels Fazem
✅ Servem como **referência visual** no sistema
✅ Documentam a **configuração de cada servidor**
✅ Facilitam **troubleshooting** ao identificar de qual Prometheus vieram as métricas
✅ Podem ser usados no futuro para **sincronização automática** com prometheus.yml

---

## 🔍 Diferença: External Labels vs Meta/Tags

### External Labels (Global - Prometheus)
```yaml
# prometheus.yml
global:
  external_labels:
    cluster: 'dtc-skills'         # ← Identifica o SERVIDOR
    datacenter: 'palmas'           # ← Identifica o DATACENTER
    site: 'palmas'                 # ← Identifica o SITE
    environment: 'production'      # ← Identifica o AMBIENTE do Prometheus
```
**Aplicado por:** Próprio Prometheus
**Escopo:** TODAS as métricas coletadas
**Finalidade:** Identificar o servidor emissor

### Meta/Tags (Individual - Consul)
```json
// Serviço registrado no Consul
{
  "ID": "icmp/Ramada/Monitora/prod@linkvivo",
  "Meta": {
    "company": "Ramada",           // ← Identifica a EMPRESA do target
    "project": "Monitora",         // ← Identifica o PROJETO
    "env": "prod",                 // ← Identifica o AMBIENTE do target
    "remote_site": "rio"           // ← Target está no Rio, mas pode ser monitorado de Palmas
  }
}
```
**Aplicado por:** Sistema ao registrar serviço
**Escopo:** Apenas aquele target específico
**Finalidade:** Identificar características do target

### Resultado Final nas Métricas
```promql
# Métrica coletada em Palmas de um target no Rio
probe_success{
  # External labels (do Prometheus de Palmas):
  cluster="dtc-skills",
  datacenter="palmas",
  site="palmas",
  environment="production",

  # Labels do target (do Meta do Consul):
  company="Ramada",
  project="Monitora",
  env="prod",
  remote_site="rio",

  # Outros labels:
  instance="10.x.x.x",
  job="blackbox_remote_rio",
  module="icmp"
}
```

---

## 💡 Exemplo Prático de Uso

### Cenário: Monitoramento Multi-Site

Você tem 3 servidores Prometheus:
- **Palmas** (master) - Monitora Palmas + targets remotos
- **Rio** (slave) - Monitora apenas Rio
- **DTC** (slave) - Monitora apenas DTC

### Configuração Recomendada

#### 1. Palmas (172.16.1.26)
**prometheus.yml:**
```yaml
global:
  external_labels:
    cluster: 'dtc-skills-master'
    datacenter: 'palmas'
    site: 'palmas'
    environment: 'production'
    prometheus_instance: '172.16.1.26'
```

**Settings → Site Palmas:**
```json
{
  "code": "palmas",
  "name": "Palmas (TO)",
  "is_default": true,
  "prometheus_host": "172.16.1.26",
  "prometheus_port": 9090,
  "external_labels": {
    "cluster": "dtc-skills-master",
    "datacenter": "palmas",
    "site": "palmas",
    "environment": "production",
    "prometheus_instance": "172.16.1.26"
  }
}
```

#### 2. Rio (172.16.200.14)
**prometheus.yml:**
```yaml
global:
  external_labels:
    cluster: 'dtc-remote-rio'
    datacenter: 'rio-de-janeiro'
    site: 'rio'
    environment: 'production'
    prometheus_instance: '172.16.200.14'
```

**Settings → Site Rio:**
```json
{
  "code": "rio",
  "name": "Rio de Janeiro (RJ)",
  "is_default": false,
  "prometheus_host": "172.16.200.14",
  "prometheus_port": 9090,
  "external_labels": {
    "cluster": "dtc-remote-rio",
    "datacenter": "rio-de-janeiro",
    "site": "rio",
    "environment": "production",
    "prometheus_instance": "172.16.200.14"
  }
}
```

#### 3. DTC (172.16.1.27)
**prometheus.yml:**
```yaml
global:
  external_labels:
    cluster: 'dtc-genesis'
    datacenter: 'genesis-dtc'
    site: 'dtc'
    environment: 'production'
    prometheus_instance: '172.16.1.27'
```

**Settings → Site DTC:**
```json
{
  "code": "dtc",
  "name": "DTC/Genesis",
  "is_default": false,
  "prometheus_host": "172.16.1.27",
  "prometheus_port": 9090,
  "external_labels": {
    "cluster": "dtc-genesis",
    "datacenter": "genesis-dtc",
    "site": "dtc",
    "environment": "production",
    "prometheus_instance": "172.16.1.27"
  }
}
```

---

## 🔧 Troubleshooting

### Como Buscar External Labels do prometheus.yml?

#### Método 1: SSH Manual
```bash
ssh prometheus@172.16.1.26
cat /etc/prometheus/prometheus.yml | grep -A 10 "global:"
```

#### Método 2: Via Sistema (Futuro)
- Feature planejada: Botão "Sync from prometheus.yml"
- Buscará automaticamente via SSH e preencherá o campo

### External Labels Não Aparecem?

**Possíveis causas:**
1. Campo deixado vazio ao criar o site
2. JSON inválido (erro de sintaxe)
3. Servidor Prometheus não tem external_labels configurados

**Solução:**
1. Acesse **Settings** → Editar site
2. Valide o JSON no campo **External Labels**
3. Copie do prometheus.yml se necessário
4. Salve novamente

### Como Validar se Está Correto?

1. Acesse Grafana
2. Execute query:
   ```promql
   up{job="consul"}
   ```
3. Verifique os labels retornados:
   - Se tiver `cluster`, `datacenter`, `site` → External labels estão ativos
   - Compare com o que está configurado no Settings

---

## 📚 Referências

- **Prometheus Docs:** https://prometheus.io/docs/prometheus/latest/configuration/configuration/#configuration-file
- **External Labels:** https://prometheus.io/docs/prometheus/latest/configuration/configuration/#global
- **Consul Service Discovery:** https://prometheus.io/docs/prometheus/latest/configuration/configuration/#consul_sd_config

---

**Data:** 2025-11-05
**Autor:** Sistema Skills Eye
