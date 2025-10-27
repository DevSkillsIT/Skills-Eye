# Resumo das Melhorias - Installer Module

## 🎯 Objetivo

Implementar segurança e melhorias de usabilidade no módulo de instalação remota de Node Exporter, garantindo que as métricas não fiquem expostas publicamente.

---

## ✨ Melhorias Implementadas

### 1. 🔐 Segurança - Basic Authentication

#### Frontend (Installer.tsx)
- ✅ Nova seção "Autenticação Basic Auth" na etapa de configuração
- ✅ Toggle para habilitar/desabilitar Basic Auth (padrão: habilitado)
- ✅ Campos de usuário (padrão: `prometheus`) e senha
- ✅ Alert informativo explicando a proteção e integração com Prometheus
- ✅ Exibição apenas para instalações Linux
- ✅ Inclusão das credenciais no resumo de instalação
- ✅ Informações de Basic Auth no plano de instalação visual

#### Backend (linux_ssh.py)
- ✅ Parâmetros `basic_auth_user` e `basic_auth_password` adicionados
- ✅ Geração automática de hash bcrypt em Python (biblioteca bcrypt)
- ✅ Fallback para htpasswd no servidor remoto se bcrypt não disponível
- ✅ Auto-instalação de apache2-utils/httpd-tools se necessário
- ✅ Criação de `/etc/node_exporter/config.yml` com:
  ```yaml
  basic_auth_users:
    prometheus: $2a$10$hash_bcrypt_gerado
  ```
- ✅ Permissões corretas: `chmod 640` e `chown node_exporter:node_exporter`
- ✅ Flag `--web.config.file=/etc/node_exporter/config.yml` no ExecStart
- ✅ Validação testando métricas com credenciais corretas

#### API (installer.py)
- ✅ Campos `basic_auth_user` e `basic_auth_password` em `LinuxSSHInstallRequest`
- ✅ Passagem de credenciais para `install_exporter()` e `validate_installation()`
- ✅ Metadados de Basic Auth salvos no Consul:
  - `basic_auth_enabled: "true"`
  - `basic_auth_user: "prometheus"`
- ✅ Warning log para configurar Prometheus com as credenciais
- ✅ Adição de `bcrypt==4.1.1` ao requirements.txt

---

### 2. 🎨 Melhorias de UX/UI

#### Tooltips nos Coletores
- ✅ Componente `Tooltip` do Ant Design aplicado
- ✅ Descrição aparece ao passar o mouse sobre cada coletor
- ✅ Placement="right" para melhor visualização
- ✅ Informações contextuais sobre cada tipo de coletor

#### Coletores Padrão Atualizados
**Antes**: `['node']`  
**Agora**: `['node', 'filesystem', 'systemd']`

Justificativa:
- `node`: Métricas base (CPU, memória, rede)
- `filesystem`: Uso de disco por filesystem (essencial)
- `systemd`: Status de serviços systemd (muito útil)

#### Resumo de Instalação
- ✅ Campo "Basic Auth" adicionado ao resumo
- ✅ Mostra se está habilitado e qual usuário
- ✅ Apresentação clara do status de segurança

---

### 3. 🛠️ Melhorias no Script de Instalação

#### systemd Service
**Antes**:
```ini
ExecStart=/usr/local/bin/node_exporter \
    --web.listen-address=:9100 \
    --collector.cpu --collector.filesystem
```

**Agora**:
```ini
ExecStart=/usr/local/bin/node_exporter \
    --web.listen-address=:9100 \
    --web.config.file=/etc/node_exporter/config.yml \
    --collector.cpu --collector.filesystem --collector.systemd
```

#### Enable Automático
**Antes**: `systemctl enable --now node_exporter`  
**Agora**: 
```bash
systemctl enable node_exporter
systemctl restart node_exporter
```

Benefício: Garante que o serviço sempre inicia no boot

#### Error Logging Aprimorado
**Antes**: Apenas "FAILED"  
**Agora**: 
```bash
if systemctl is-active --quiet node_exporter; then
    echo "SUCCESS"
else
    echo "FAILED"
    journalctl -u node_exporter -n 20 --no-pager
    exit 1
fi
```

Benefício: Logs detalhados facilitam troubleshooting

---

### 4. 📊 Integração com Consul e Prometheus

#### Metadados Estendidos
```json
{
  "Meta": {
    "instance": "192.168.1.100:9100",
    "name": "hostname",
    "company": "Skills IT",
    "env": "prod",
    "module": "node_exporter",
    "basic_auth_enabled": "true",
    "basic_auth_user": "prometheus"
  }
}
```

#### Uso no Prometheus
O Prometheus pode usar os metadados do Consul para:
1. Filtrar targets com/sem Basic Auth
2. Aplicar credenciais automaticamente
3. Configurar scrapes condicionalmente

Exemplo:
```yaml
scrape_configs:
  - job_name: 'node_exporter_auth'
    consul_sd_configs:
      - server: '172.16.1.26:8500'
        services: ['selfnode_exporter']
    relabel_configs:
      - source_labels: [__meta_consul_service_metadata_basic_auth_enabled]
        regex: 'true'
        action: keep
    basic_auth:
      username: prometheus
      password_file: /etc/prometheus/secrets/node_exporter.txt
```

---

## 🔒 Fluxo de Segurança

### Instalação do Node Exporter
1. Usuário preenche formulário com credenciais
2. Backend gera hash bcrypt da senha
3. Cria `/etc/node_exporter/config.yml` no servidor remoto
4. Inicia serviço com `--web.config.file`
5. Métricas agora requerem autenticação

### Acesso às Métricas
**Sem autenticação**:
```bash
curl http://192.168.1.100:9100/metrics
# HTTP/1.1 401 Unauthorized
```

**Com autenticação**:
```bash
curl -u prometheus:senha http://192.168.1.100:9100/metrics
# node_cpu_seconds_total{...} 12345
```

### Coleta pelo Prometheus
1. Prometheus usa credenciais do arquivo de senha
2. Consulta Consul para descobrir targets
3. Identifica targets com `basic_auth_enabled=true`
4. Aplica autenticação automaticamente no scrape
5. Coleta métricas normalmente

---

## 📁 Arquivos Modificados

### Frontend
- `frontend/src/pages/Installer.tsx`
  - Estados de Basic Auth adicionados
  - UI de configuração implementada
  - Plano de instalação atualizado
  - Resumo estendido

### Backend
- `backend/core/installers/linux_ssh.py`
  - Método `install_exporter()` com novos parâmetros
  - Método `validate_installation()` com autenticação
  - Lógica de geração de hash bcrypt
  - Script de instalação aprimorado

- `backend/api/installer.py`
  - Model `LinuxSSHInstallRequest` estendido
  - Função `run_installation()` atualizada
  - Função `register_in_consul()` com metadados

- `backend/requirements.txt`
  - `bcrypt==4.1.1` adicionado

### Documentação
- `PROMETHEUS_BASIC_AUTH_GUIDE.md` (novo)
  - Guia completo de configuração
  - Opções de autenticação
  - Scripts de automação
  - Troubleshooting

- `INSTALLER_IMPROVEMENTS_SUMMARY.md` (este arquivo)

---

## 🧪 Como Testar

### 1. Frontend
```bash
cd frontend
npm run dev
```

Acesse: http://localhost:8081/installer

**Verificar**:
- [ ] Tooltips aparecem ao passar mouse nos coletores
- [ ] Seção "Autenticação Basic Auth" visível
- [ ] Toggle funciona corretamente
- [ ] Campos de usuário/senha aparecem quando habilitado
- [ ] Resumo mostra status do Basic Auth
- [ ] Coletores padrão são: node, filesystem, systemd

### 2. Backend
```bash
cd backend
pip install -r requirements.txt
python app.py
```

**Testar API**:
```bash
# Test connection
curl -X POST http://localhost:5000/api/v1/installer/test-connection \
  -H "Content-Type: application/json" \
  -d '{
    "os_type": "linux",
    "method": "ssh",
    "host": "192.168.1.100",
    "username": "root",
    "password": "senha"
  }'

# Start installation with Basic Auth
curl -X POST http://localhost:5000/api/v1/installer/install \
  -H "Content-Type: application/json" \
  -d '{
    "os_type": "linux",
    "method": "ssh",
    "host": "192.168.1.100",
    "username": "root",
    "password": "senha",
    "collector_profile": "recommended",
    "basic_auth_user": "prometheus",
    "basic_auth_password": "SenhaForte123!",
    "register_in_consul": true
  }'
```

### 3. Instalação Completa
```bash
# Após instalação, testar no servidor
ssh user@servidor-instalado

# Verificar config
sudo cat /etc/node_exporter/config.yml

# Verificar serviço
sudo systemctl status node_exporter

# Testar sem auth (deve falhar)
curl http://localhost:9100/metrics

# Testar com auth (deve funcionar)
curl -u prometheus:SenhaForte123! http://localhost:9100/metrics
```

---

## 📈 Benefícios

### Segurança
- ✅ Métricas protegidas contra acesso não autorizado
- ✅ Hash bcrypt (10 rounds) - alta segurança
- ✅ Permissões de arquivo adequadas
- ✅ Apenas Prometheus configurado tem acesso

### Usabilidade
- ✅ Tooltips educativos para usuários
- ✅ Configuração intuitiva via toggle
- ✅ Coletores padrão mais completos
- ✅ Feedback claro no resumo

### Manutenibilidade
- ✅ Metadados no Consul facilitam automação
- ✅ Logs detalhados para troubleshooting
- ✅ Documentação completa do processo
- ✅ Scripts reutilizáveis

### Conformidade
- ✅ Boas práticas de segurança
- ✅ Auditoria facilitada (credenciais rastreáveis)
- ✅ Padrão de mercado (Basic Auth)

---

## 🚀 Próximos Passos

### Curto Prazo
- [ ] Testar instalação em diferentes distribuições Linux
- [ ] Criar dashboard Grafana mostrando status de autenticação
- [ ] Implementar rotação automática de senhas

### Médio Prazo
- [ ] Suporte a TLS/SSL para criptografia de transporte
- [ ] Integração com Vault para gestão de segredos
- [ ] Alertas para falhas de autenticação

### Longo Prazo
- [ ] Suporte a OAuth2/OIDC
- [ ] Multi-tenancy com credenciais por empresa
- [ ] Auditoria centralizada de acessos

---

## 📞 Suporte

Para dúvidas ou problemas:
1. Consulte `PROMETHEUS_BASIC_AUTH_GUIDE.md`
2. Verifique logs: `journalctl -u node_exporter`
3. Teste acesso local antes de remoto
4. Valide credenciais no Consul

---

**Data**: 27/10/2025  
**Versão**: 2.4.0  
**Autor**: Implementação via AI Assistant
