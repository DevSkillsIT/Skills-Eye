# Guia de Configuração - Basic Auth no Prometheus

## 📋 Visão Geral

Este guia explica como configurar o Prometheus para fazer scrape de Node Exporters protegidos com Basic Authentication, utilizando a descoberta de serviços via Consul.

---

## 🔐 Como Funciona

### 1. Node Exporter com Basic Auth

Quando o Node Exporter é instalado com Basic Auth habilitado:

```yaml
# /etc/node_exporter/config.yml
basic_auth_users:
  prometheus: $2a$10$hash_bcrypt_da_senha
```

O serviço inicia com a flag:
```bash
ExecStart=/usr/local/bin/node_exporter \
    --web.listen-address=:9100 \
    --web.config.file=/etc/node_exporter/config.yml
```

### 2. Metadados no Consul

O serviço é registrado no Consul com metadados indicando o uso de Basic Auth:

```json
{
  "ID": "selfnode_exporter/hostname@192.168.1.100",
  "Service": "selfnode_exporter",
  "Address": "192.168.1.100",
  "Port": 9100,
  "Meta": {
    "basic_auth_enabled": "true",
    "basic_auth_user": "prometheus",
    "instance": "192.168.1.100:9100",
    "env": "prod"
  }
}
```

### 3. Configuração do Prometheus

O Prometheus precisa ser configurado para usar as credenciais ao fazer scrape dos targets.

---

## ⚙️ Configuração do Prometheus

### Opção 1: Credenciais Estáticas (Simples)

Use esta opção se todos os Node Exporters usam as mesmas credenciais:

```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'node_exporter'
    consul_sd_configs:
      - server: '172.16.1.26:8500'
        services: ['selfnode_exporter']
    
    # Aplicar Basic Auth para todos os targets deste job
    basic_auth:
      username: prometheus
      password: 'sua_senha_segura_aqui'
    
    relabel_configs:
      - source_labels: [__meta_consul_service_metadata_instance]
        target_label: instance
      - source_labels: [__meta_consul_service_metadata_env]
        target_label: env
      - source_labels: [__meta_consul_service_metadata_company]
        target_label: company
```

### Opção 2: Credenciais por Target (Avançado)

Use `file_sd_configs` com arquivos gerados automaticamente:

```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'node_exporter_auth'
    file_sd_configs:
      - files:
          - '/etc/prometheus/targets/node_exporter_*.yml'
        refresh_interval: 30s
```

Gere arquivos de targets com credenciais específicas:

```yaml
# /etc/prometheus/targets/node_exporter_prod.yml
- targets:
    - '192.168.1.100:9100'
  labels:
    env: 'prod'
    company: 'Skills IT'
  basic_auth:
    username: prometheus
    password: 'senha_do_target_1'

- targets:
    - '192.168.1.101:9100'
  labels:
    env: 'prod'
    company: 'Skills IT'
  basic_auth:
    username: prometheus
    password: 'senha_do_target_2'
```

### Opção 3: Credenciais de Arquivo (Recomendado)

Use arquivos de senha para maior segurança:

```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'node_exporter'
    consul_sd_configs:
      - server: '172.16.1.26:8500'
        services: ['selfnode_exporter']
    
    basic_auth:
      username: prometheus
      password_file: /etc/prometheus/secrets/node_exporter_password.txt
    
    relabel_configs:
      - source_labels: [__meta_consul_service_metadata_instance]
        target_label: instance
```

Crie o arquivo de senha:

```bash
echo -n 'sua_senha_segura' > /etc/prometheus/secrets/node_exporter_password.txt
chmod 600 /etc/prometheus/secrets/node_exporter_password.txt
chown prometheus:prometheus /etc/prometheus/secrets/node_exporter_password.txt
```

---

## 🎯 Configuração Condicional (Misto)

Se você tem targets com e sem Basic Auth:

```yaml
scrape_configs:
  # Targets SEM Basic Auth
  - job_name: 'node_exporter_no_auth'
    consul_sd_configs:
      - server: '172.16.1.26:8500'
        services: ['selfnode_exporter']
    
    # Filtrar apenas targets sem basic_auth_enabled
    relabel_configs:
      - source_labels: [__meta_consul_service_metadata_basic_auth_enabled]
        regex: 'true'
        action: drop
      - source_labels: [__meta_consul_service_metadata_instance]
        target_label: instance

  # Targets COM Basic Auth
  - job_name: 'node_exporter_auth'
    consul_sd_configs:
      - server: '172.16.1.26:8500'
        services: ['selfnode_exporter']
    
    # Filtrar apenas targets com basic_auth_enabled=true
    relabel_configs:
      - source_labels: [__meta_consul_service_metadata_basic_auth_enabled]
        regex: 'true'
        action: keep
      - source_labels: [__meta_consul_service_metadata_instance]
        target_label: instance
    
    basic_auth:
      username: prometheus
      password_file: /etc/prometheus/secrets/node_exporter_password.txt
```

---

## 🔧 Automação com Script

Crie um script para gerar automaticamente a configuração:

```bash
#!/bin/bash
# generate_prometheus_targets.sh

CONSUL_URL="http://172.16.1.26:8500"
OUTPUT_DIR="/etc/prometheus/targets"
PASSWORD_FILE="/etc/prometheus/secrets/node_exporter_password.txt"

# Buscar serviços do Consul
curl -s "${CONSUL_URL}/v1/catalog/service/selfnode_exporter" | \
  jq -r '.[] | select(.ServiceMeta.basic_auth_enabled == "true") | 
  "- targets: [\"" + .ServiceAddress + ":" + (.ServicePort | tostring) + "\"]
  labels:
    env: \"" + .ServiceMeta.env + "\"
    company: \"" + .ServiceMeta.company + "\"
  basic_auth:
    username: " + .ServiceMeta.basic_auth_user + "
    password_file: " + "'"${PASSWORD_FILE}"'"' \
  > "${OUTPUT_DIR}/node_exporter_auth.yml"

# Recarregar Prometheus
curl -X POST http://localhost:9090/-/reload
```

Execute via cron:

```bash
# Atualizar targets a cada 5 minutos
*/5 * * * * /usr/local/bin/generate_prometheus_targets.sh
```

---

## 🧪 Testando a Configuração

### 1. Testar acesso ao Node Exporter

```bash
# Sem autenticação (deve falhar)
curl http://192.168.1.100:9100/metrics
# HTTP/1.1 401 Unauthorized

# Com autenticação (deve funcionar)
curl -u prometheus:sua_senha http://192.168.1.100:9100/metrics
# node_cpu_seconds_total{cpu="0",mode="idle"} 123456.78
```

### 2. Verificar targets no Prometheus

Acesse: http://seu-prometheus:9090/targets

Verifique se:
- ✅ Targets aparecem como UP
- ✅ Labels corretos (env, company, instance)
- ✅ Sem erros de autenticação

### 3. Validar métricas

```promql
# Query no Prometheus
up{job="node_exporter_auth"}

# Deve retornar 1 para targets UP
```

---

## 🔒 Boas Práticas de Segurança

1. **Senhas Fortes**: Use senhas com pelo menos 16 caracteres
   ```bash
   openssl rand -base64 24
   ```

2. **Rotação de Senhas**: Agende trocas periódicas
   - Gere nova senha
   - Atualize `/etc/node_exporter/config.yml` em todos os servidores
   - Atualize arquivo de senha do Prometheus
   - Recarregue ambos os serviços

3. **Permissões de Arquivo**:
   ```bash
   chmod 640 /etc/node_exporter/config.yml
   chmod 600 /etc/prometheus/secrets/*.txt
   ```

4. **Firewall**: Restrinja acesso à porta 9100
   ```bash
   # Permitir apenas do servidor Prometheus
   sudo ufw allow from 172.16.1.26 to any port 9100
   ```

5. **Monitoramento**: Configure alertas para falhas de autenticação
   ```yaml
   groups:
     - name: authentication
       rules:
         - alert: NodeExporterAuthFailure
           expr: up{job="node_exporter_auth"} == 0
           for: 5m
           annotations:
             summary: "Node Exporter autenticação falhou em {{ $labels.instance }}"
   ```

---

## 📚 Referências

- [Node Exporter - Web Configuration](https://github.com/prometheus/node_exporter#tls-and-basic-authentication)
- [Prometheus - Configuration](https://prometheus.io/docs/prometheus/latest/configuration/configuration/#scrape_config)
- [Consul Service Discovery](https://prometheus.io/docs/prometheus/latest/configuration/configuration/#consul_sd_config)

---

## 🆘 Troubleshooting

### Erro: "401 Unauthorized"

**Causa**: Credenciais incorretas ou não configuradas

**Solução**:
```bash
# Verificar config do Node Exporter
sudo cat /etc/node_exporter/config.yml

# Testar manualmente
curl -u prometheus:senha http://localhost:9100/metrics

# Verificar logs
sudo journalctl -u node_exporter -n 50
```

### Erro: "connection refused"

**Causa**: Serviço não está rodando ou firewall bloqueando

**Solução**:
```bash
# Verificar serviço
sudo systemctl status node_exporter

# Testar porta local
curl http://localhost:9100/metrics

# Verificar firewall
sudo ufw status
```

### Targets sempre DOWN no Prometheus

**Causa**: Prometheus não tem as credenciais corretas

**Solução**:
1. Verificar `basic_auth` no `prometheus.yml`
2. Validar arquivo de senha existe e está legível
3. Recarregar Prometheus: `curl -X POST http://localhost:9090/-/reload`

---

## ✅ Checklist de Implementação

- [ ] Node Exporter instalado com Basic Auth habilitado
- [ ] `/etc/node_exporter/config.yml` criado com hash bcrypt
- [ ] Serviço reiniciado e testado localmente
- [ ] Serviço registrado no Consul com metadados corretos
- [ ] Prometheus configurado com credenciais
- [ ] Targets aparecem como UP no Prometheus
- [ ] Métricas sendo coletadas corretamente
- [ ] Alertas configurados para falhas
- [ ] Documentação atualizada para a equipe
- [ ] Senhas armazenadas em vault/gestor de senhas
