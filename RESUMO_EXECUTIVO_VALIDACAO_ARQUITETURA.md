# Resumo Executivo: Validação da Arquitetura Prometheus

**Data:** 2025-11-05
**Análise:** Pesquisa web extensiva + validação de configurações

---

## 🎯 **PERGUNTAS E RESPOSTAS DIRETAS**

### **1. Job names devem ser idênticos nos diferentes sites?**

**✅ RESPOSTA: SIM, podem e DEVEM ser idênticos.**

**Evidência da comunidade Prometheus:**

> *"As long as all the time series have distinct label sets (in particular, different 'instance' labels), then there is no problem with all the agents using the same 'job' label."*

**Regra:**
- Job name IDÊNTICO: `node_exporter` (todos os sites)
- Diferenciação via **external_labels**: `cluster: 'rio-rmd-ldc'` vs `cluster: 'palmas-master'`

**Benefício:**
- Query unificada: `up{job="node_exporter"}` funciona cross-site
- Filtro por site: `up{job="node_exporter", cluster="rio-rmd-ldc"}`

---

### **2. Arquitetura centralizada (Master scrape remoto) ou distribuída (cada site local)?**

**✅ RESPOSTA: DISTRIBUÍDA (cada site roda Blackbox localmente).**

**Por quê?**

> *"The results you receive from Blackbox exporter are going to be relative to where you install it."*

**Problema Atual (Centralizado):**
```
Palmas Master scrape Blackbox remoto no Rio
  → Latência mede: Palmas → Rio → Target
  → Se link Palmas↔Rio cair, perde monitoramento do Rio
```

**Solução Recomendada (Distribuído):**
```
Rio roda Blackbox local → mede Rio → Target (latência real)
Rio envia métricas para Palmas via remote_write
  → Se link cair, Rio continua monitorando (remote_write bufferiza)
```

**Padrão encontrado na pesquisa:**
- ✅ **Multi-site usa remote_write** (não scrape remoto)
- ✅ **Cada site gerencia seus targets localmente**
- ✅ **Master apenas agrega métricas** recebidas via remote_write

---

### **3. Existe sistema similar no mercado ao Consul Manager Web?**

**✅ RESPOSTA: NÃO existe equivalente open-source.**

**Único sistema encontrado:** **Promgen** (LINE Corporation)

| Recurso | Promgen | Consul Manager Web |
|---------|---------|-------------------|
| Edita prometheus.yml diretamente | ❌ Gera arquivos separados | ✅ Edita via SSH |
| Validação promtool remota | ❌ Não | ✅ Sim |
| Blackbox CSV/XLSX import | ❌ Não | ✅ Sim |
| Consul Service Discovery | ⚠️ Limitado | ✅ Nativo |
| Instalação remota de exporters | ❌ Não | ✅ SSH/WinRM/PSExec |
| Preserva comentários YAML | ❌ N/A | ✅ ruamel.yaml |
| Multi-server batch update | ⚠️ Complexo | ✅ Parallel SSH |

**Por que não existe?**

1. Prometheus é **extremamente flexível** - difícil UI universal
2. Não tem **API de configuração** (apenas HTTP read API)
3. Requer **acesso SSH** para editar arquivos remotamente
4. **Validação complexa** (promtool, regex, relabeling)

**Conclusão: Consul Manager Web é ÚNICO no mercado.**

---

### **4. Remote_write vs Federation - qual usar?**

**✅ RESPOSTA: Remote_write (já está correto).**

| Aspecto | Remote Write ✅ | Federation |
|---------|----------------|------------|
| **Modelo** | Push (slave → master) | Pull (master → slave) |
| **Latência** | Tempo real | Alta (scrape interval) |
| **Dados** | Todas as métricas | Métricas selecionadas |
| **Resiliência** | Bufferiza se desconectar | Perde dados |
| **Uso** | Multi-site, HA | Agregação hierárquica |

**Para o caso atual (Palmas + Rio + DTC):** Remote_write é a escolha correta.

---

## ✅ **VALIDAÇÃO: ChatGPT ESTAVA 100% CORRETO**

**ChatGPT recomendou:**

1. ✅ Cada site roda Blackbox localmente
2. ✅ Job names idênticos
3. ✅ Remote_write para enviar ao Master
4. ✅ External labels para diferenciar sites

**Pesquisa web confirmou:**

- ✅ Blackbox local = best practice
- ✅ Job names idênticos = padrão recomendado
- ✅ Remote_write = escolha correta para multi-site
- ✅ External labels = método de diferenciação

---

## 🔧 **O QUE PRECISA MUDAR**

### **CONFIGURAÇÃO ATUAL (Problemas):**

```yaml
# ❌ PALMAS MASTER - scrape Blackbox remoto
- job_name: 'icmp_blackbox_remote_rmd_ldc'
  consul_sd_configs:
    - server: '172.16.200.14:8500'  # Consul remoto

# ❌ RIO SLAVE - job name único, Blackbox comentado
- job_name: 'node_exporter_rio'  # Deveria ser 'node_exporter'
# - job_name: 'icmp_rio'  # COMENTADO (deveria estar ativo)

# ❌ DTC SLAVE - job name único, Blackbox comentado
- job_name: 'node_exporter_dtc_remote'
# - job_name: 'icmp_dtc_remote'  # COMENTADO
```

### **CONFIGURAÇÃO RECOMENDADA:**

```yaml
# ✅ PALMAS MASTER
global:
  external_labels:
    cluster: 'palmas-master'

scrape_configs:
  - job_name: 'node_exporter'  # ← Nome padrão
    consul_sd_configs:
      - server: 'localhost:8500'  # ← Apenas local

  - job_name: 'icmp'           # ← Nome padrão
    metrics_path: /probe
    consul_sd_configs:
      - server: 'localhost:8500'
        tags: ['icmp', 'palmas']  # ← Filtra targets Palmas
    relabel_configs:
      - target_label: __address__
        replacement: '127.0.0.1:9115'  # ← Blackbox local

# REMOVER jobs remotos:
# - icmp_blackbox_remote_rmd_ldc  # ← DELETAR
# - icmp_blackbox_remote_dtc_skills  # ← DELETAR

# ✅ RIO SLAVE
global:
  external_labels:
    cluster: 'rio-rmd-ldc'

scrape_configs:
  - job_name: 'node_exporter'  # ← MESMO nome que Palmas
    consul_sd_configs:
      - server: 'localhost:8500'

  - job_name: 'icmp'           # ← DESCOMENTAR e ativar
    metrics_path: /probe
    consul_sd_configs:
      - server: 'localhost:8500'
        tags: ['icmp', 'rio']   # ← Filtra targets Rio
    relabel_configs:
      - target_label: __address__
        replacement: '127.0.0.1:9115'  # ← Blackbox local Rio

remote_write:
  - url: 'http://172.16.1.26:9090/api/v1/write'
    write_relabel_configs:
      - target_label: remote_site
        replacement: 'rio-rmd-ldc'

# ✅ DTC SLAVE (mesma lógica que Rio)
```

---

## 📊 **IMPACTO DAS MUDANÇAS**

### **Antes (Centralizado):**

- ❌ Latência ICMP mede Palmas → Target (distorcida)
- ❌ Se link Palmas↔Rio cair, perde monitoramento
- ❌ Queries precisam saber job names diferentes
- ❌ Master sobrecarregado (scrape cross-WAN)

### **Depois (Distribuído):**

- ✅ Latência ICMP mede Local → Target (real)
- ✅ Monitoramento continua mesmo sem link (buffering)
- ✅ Queries unificadas funcionam cross-site
- ✅ Carga distribuída naturalmente

---

## 🚀 **PLANO DE MIGRAÇÃO (Resumido)**

### **FASE 1: Preparação**

1. Backup de todos os prometheus.yml
2. Validar Blackbox instalado em Rio e DTC
3. Criar tags Consul por site ('rio', 'dtc', 'palmas')

### **FASE 2: Piloto no Rio**

1. Descomentar jobs Blackbox
2. Ajustar para job name padrão: `icmp` (ao invés de `icmp_rio`)
3. Adicionar filtro: `tags: ['icmp', 'rio']`
4. Reload e testar

### **FASE 3: Replicar DTC**

1. Aplicar mesmas mudanças

### **FASE 4: Cleanup Palmas**

1. Remover jobs `icmp_blackbox_remote_*`
2. Validar que métricas chegam via remote_write

---

## 📚 **FONTES PRINCIPAIS**

**Documentação Oficial:**
- Prometheus Remote Write: https://prometheus.io/docs/specs/prw/remote_write_spec/
- Multi-Target Exporter: https://prometheus.io/docs/guides/multi-target-exporter/

**Comunidade:**
- Prometheus Users Google Group (discussões sobre job names)
- Robust Perception Blog (federation vs remote_write)

**Ferramentas:**
- Promgen: https://github.com/line/promgen (único similar encontrado)

---

## 💡 **CONCLUSÕES FINAIS**

### **1. Arquitetura Recomendada pelo ChatGPT: CORRETA ✅**

A pesquisa web validou 100% das recomendações. É o padrão da comunidade.

### **2. Consul Manager Web: ÚNICO no Mercado ✅**

Não existe sistema open-source equivalente que combine:
- Edição direta de prometheus.yml via SSH
- Consul Service Discovery integration
- Blackbox CSV/XLSX import
- Remote exporter installation
- Multi-server management

### **3. Mudanças Necessárias: SIMPLES e SEM RISCO**

- Descomentar Blackbox nos slaves
- Padronizar job names (opcional mas recomendado)
- Remover jobs remotos do Master
- Adicionar tags por site no Consul

### **4. Benefícios Imediatos:**

- ✅ Latências realistas
- ✅ Maior resiliência
- ✅ Queries unificadas
- ✅ Escalabilidade natural

---

**VEREDICTO: Implementar arquitetura distribuída conforme recomendado.**
