# Lógica de Reload de Serviços - Implementação Completa

## 📋 Visão Geral

Sistema inteligente de reload de serviços Prometheus/Blackbox/Alertmanager que:
- ✅ **Verifica status antes de agir** (evita erros de reload em serviços parados)
- ✅ **Usa reload ao invés de restart** (sem downtime quando possível)
- ✅ **Detecta automaticamente quais serviços recarregar** baseado no arquivo editado
- ✅ **Fallback automático** se reload falhar

---

## 🔍 PASSO 1: Verificação de Status

**ANTES de tentar qualquer ação, o sistema verifica:**

```bash
systemctl is-active prometheus
```

**Possíveis retornos:**
- `active` → Serviço rodando normalmente
- `inactive` → Serviço parado
- `failed` → Serviço falhou
- `unknown` → Status desconhecido

---

## ⚙️ PASSO 2: Decisão Inteligente de Ação

### Se Status = `active` (Serviço Rodando)

**Usa RELOAD (sem downtime):**
```bash
systemctl reload prometheus
```

**Vantagens:**
- ✅ Zero downtime
- ✅ Métricas continuam sendo coletadas
- ✅ Alertas continuam ativos
- ✅ Prometheus reconhece novas configurações sem parar

**Se reload falhar:**
- Fallback automático para `systemctl restart`

---

### Se Status = `inactive`, `failed`, ou `unknown` (Serviço Parado)

**Usa START:**
```bash
systemctl start prometheus
```

**Por quê?**
- ❌ `reload` NÃO funciona em serviços parados
- ✅ `start` inicia o serviço com as novas configurações já aplicadas

---

### Se Status = outro valor desconhecido

**Usa RESTART por segurança:**
```bash
systemctl restart prometheus
```

---

## 📁 PASSO 3: Lógica por Tipo de Arquivo

### Arquivo: `prometheus.yml`
```
Serviços recarregados: prometheus
Método preferido: reload
```

### Arquivo: `blackbox.yml`
```
Serviços recarregados: blackbox_exporter + prometheus
Método preferido: reload

Por quê dois serviços?
- Blackbox precisa recarregar seus módulos
- Prometheus precisa recarregar pois usa esses módulos
```

### Arquivo: `alertmanager.yml`
```
Serviços recarregados: alertmanager
Método preferido: reload
```

### Arquivos em `/etc/prometheus/` (rules, etc)
```
Serviços recarregados: prometheus
Método preferido: reload
```

---

## 🎯 Exemplos de Execução

### Exemplo 1: Prometheus Ativo - Reload Normal
```
[RELOAD] Verificando status de prometheus...
[RELOAD] Status atual de prometheus: active
[RELOAD] Serviço ativo - executando reload: systemctl reload prometheus
[RELOAD] ✅ Serviço prometheus processado via reload. Status final: active
```

### Exemplo 2: Prometheus Parado - Start
```
[RELOAD] Verificando status de prometheus...
[RELOAD] Status atual de prometheus: inactive
[RELOAD] Serviço está inactive - executando start: systemctl start prometheus
[RELOAD] ✅ Serviço prometheus processado via start. Status final: active
```

### Exemplo 3: Blackbox.yml - Dois Serviços
```
[RELOAD] Arquivo blackbox.yml detectado - recarregando blackbox_exporter + prometheus
[RELOAD] Verificando status de blackbox_exporter...
[RELOAD] Status atual de blackbox_exporter: active
[RELOAD] Serviço ativo - executando reload: systemctl reload blackbox_exporter
[RELOAD] ✅ Serviço blackbox_exporter processado via reload. Status final: active

[RELOAD] Verificando status de prometheus...
[RELOAD] Status atual de prometheus: active
[RELOAD] Serviço ativo - executando reload: systemctl reload prometheus
[RELOAD] ✅ Serviço prometheus processado via reload. Status final: active
```

### Exemplo 4: Reload Falhou - Fallback para Restart
```
[RELOAD] Verificando status de prometheus...
[RELOAD] Status atual de prometheus: active
[RELOAD] Serviço ativo - executando reload: systemctl reload prometheus
[RELOAD] Reload falhou para prometheus, tentando restart: Job for prometheus.service invalid
[RELOAD] ✅ Serviço prometheus processado via restart (fallback). Status final: active
```

---

## 📊 Resposta da API

A API retorna informações detalhadas de cada serviço:

```json
{
  "success": true,
  "message": "Serviço(s) blackbox_exporter, prometheus recarregado(s) com sucesso no host 172.16.1.26",
  "services": [
    {
      "service": "blackbox_exporter",
      "success": true,
      "method": "reload",
      "status": "active",
      "previous_status": "active"
    },
    {
      "service": "prometheus",
      "success": true,
      "method": "reload",
      "status": "active",
      "previous_status": "active"
    }
  ],
  "file_path": "/etc/prometheus/blackbox.yml"
}
```

---

## 🔄 Fluxograma Completo

```
┌─────────────────────────────┐
│  Arquivo YAML editado       │
└──────────┬──────────────────┘
           │
           ▼
┌─────────────────────────────┐
│ Determinar serviços         │
│ baseado no arquivo          │
└──────────┬──────────────────┘
           │
           ▼
┌─────────────────────────────┐
│ Para cada serviço:          │
│ Verificar status atual      │
│ (systemctl is-active)       │
└──────────┬──────────────────┘
           │
           ▼
      ┌────┴────┐
      │ Status? │
      └────┬────┘
           │
    ┌──────┼──────┐
    │      │      │
    ▼      ▼      ▼
 active inactive other
    │      │      │
    ▼      ▼      ▼
 RELOAD  START  RESTART
    │      │      │
    └──────┼──────┘
           │
           ▼
   ┌───────────────┐
   │ Falhou?       │
   └───┬───────┬───┘
       │       │
      Sim     Não
       │       │
       ▼       ▼
   FALLBACK  SUCESSO
   restart     │
       │       │
       └───┬───┘
           │
           ▼
    ┌─────────────┐
    │ Verificar   │
    │ status final│
    └─────────────┘
```

---

## 🛡️ Segurança e Confiabilidade

### Verificações Implementadas:

1. ✅ **Status pré-reload** - Evita erros de comando inválido
2. ✅ **Fallback automático** - Se reload falhar, tenta restart
3. ✅ **Verificação pós-operação** - Confirma que serviço está active
4. ✅ **Logs detalhados** - Toda operação é logada para auditoria
5. ✅ **Resposta estruturada** - API retorna detalhes de cada serviço

### Tratamento de Erros:

- ❌ **Serviço não existe** → Retorna erro com detalhes
- ❌ **Permissão negada** → Retorna erro SSH
- ❌ **Timeout SSH** → Retorna erro de conexão
- ❌ **Comando falhou** → Tenta fallback antes de reportar falha

---

## 🎯 Benefícios da Implementação

| Aspecto | Antes | Agora |
|---------|-------|-------|
| **Downtime** | Restart sempre (5-10s) | Reload (0s) ou Start se parado |
| **Serviço parado** | ❌ Reload falhava | ✅ Detecta e usa Start |
| **Verificação** | ❌ Nenhuma | ✅ Verifica antes e depois |
| **Blackbox** | ❌ Só reload prometheus | ✅ Recarrega ambos corretamente |
| **Feedback** | ❌ Genérico | ✅ Detalhado por serviço |
| **Logs** | ❌ Básicos | ✅ Completos com status |

---

## 📝 Referências

- [Prometheus Configuration Reload](https://prometheus.io/docs/prometheus/latest/configuration/configuration/)
- [systemctl reload vs restart](https://www.freedesktop.org/software/systemd/man/systemctl.html)
- [Blackbox Exporter Configuration](https://github.com/prometheus/blackbox_exporter)

---

**Data de Implementação:** 2025-10-29
**Versão:** 1.0
**Status:** ✅ Produção
