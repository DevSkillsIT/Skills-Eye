# Consul Manager API - Documentação

API FastAPI para gerenciamento de serviços Consul com suporte completo a metadados e configuração dinâmica.

## Configuração

### Variáveis de Ambiente

Copie o arquivo `.env.example` para `.env` e configure:

```bash
cp .env.example .env
```

Principais configurações:

- **CONSUL_HOST**: Endereço do servidor Consul (padrão: 172.16.1.26)
- **CONSUL_PORT**: Porta do Consul (padrão: 8500)
- **CONSUL_TOKEN**: Token de autenticação do Consul

### Configuração Dinâmica

A API suporta mudança de instância Consul em tempo de execução através de parâmetros de query `node_addr` em diversos endpoints, permitindo conectar em diferentes nós sem reiniciar o servidor.

## Endpoints Principais

### Base URL
```
http://localhost:5000/api/v1
```

### Documentação Interativa
- Swagger UI: `http://localhost:5000/docs`
- ReDoc: `http://localhost:5000/redoc`

---

## 📋 Services API (`/services`)

### `GET /services/`
Lista serviços com todos os metadados.

**Query Parameters:**
- `node_addr` (opcional): Endereço do nó específico ou 'ALL' para todos os nós
- `module` (opcional): Filtrar por módulo (icmp, http_2xx, etc)
- `company` (opcional): Filtrar por empresa
- `project` (opcional): Filtrar por projeto
- `env` (opcional): Filtrar por ambiente (prod, dev, etc)

**Exemplo:**
```bash
# Listar todos os serviços do servidor principal
curl http://localhost:5000/api/v1/services/

# Listar serviços de todos os nós
curl http://localhost:5000/api/v1/services/?node_addr=ALL

# Listar apenas serviços ICMP de produção
curl http://localhost:5000/api/v1/services/?module=icmp&env=prod

# Listar serviços de um nó específico
curl http://localhost:5000/api/v1/services/?node_addr=172.16.1.26
```

**Resposta:**
```json
{
  "success": true,
  "data": {
    "service-id-123": {
      "ID": "service-id-123",
      "Service": "blackbox_exporter",
      "Tags": ["monitoring"],
      "Port": 9115,
      "Meta": {
        "module": "icmp",
        "company": "Skills IT",
        "project": "Monitoring",
        "env": "prod",
        "name": "Gateway Principal",
        "instance": "172.16.1.1",
        "localizacao": "Data Center",
        "tipo": "Network"
      }
    }
  },
  "total": 1,
  "message": "Listados 1 serviços do nó 172.16.1.26"
}
```

### `GET /services/{service_id}`
Obtém detalhes de um serviço específico.

**Path Parameters:**
- `service_id`: ID do serviço

**Query Parameters:**
- `node_addr` (opcional): Endereço do nó onde buscar

**Exemplo:**
```bash
curl http://localhost:5000/api/v1/services/blackbox_icmp_gateway_prod
```

### `POST /services/`
Cria um novo serviço no Consul.

**Body (JSON):**
```json
{
  "id": "blackbox_icmp_gateway_prod",
  "name": "blackbox_exporter",
  "tags": ["monitoring", "icmp"],
  "port": 9115,
  "Meta": {
    "module": "icmp",
    "company": "Skills IT",
    "project": "Monitoring",
    "env": "prod",
    "name": "Gateway Principal",
    "instance": "172.16.1.1",
    "localizacao": "Data Center",
    "tipo": "Network",
    "cidade": "São Paulo"
  },
  "node_addr": "172.16.1.26"
}
```

**Validações Automáticas:**
- Campos obrigatórios: module, company, project, env, name, instance
- Verificação de duplicatas
- Validação de formato de instance baseado no módulo

### `PUT /services/{service_id}`
Atualiza um serviço existente.

**Path Parameters:**
- `service_id`: ID do serviço

**Body (JSON):**
```json
{
  "Meta": {
    "localizacao": "Nova Localização",
    "notas": "Atualizado em 2024"
  },
  "node_addr": "172.16.1.26"
}
```

### `DELETE /services/{service_id}`
Remove um serviço do Consul.

**Path Parameters:**
- `service_id`: ID do serviço

**Query Parameters:**
- `node_addr` (opcional): Endereço do nó onde remover

### `GET /services/search/by-metadata`
Busca serviços por filtros de metadados.

**Query Parameters:**
- `module`, `company`, `project`, `env`, `name`, `instance`: Filtros opcionais
- `node_addr` (opcional): Buscar em nó específico

**Exemplo:**
```bash
curl "http://localhost:5000/api/v1/services/search/by-metadata?company=Skills%20IT&env=prod"
```

### `GET /services/metadata/unique-values`
Obtém valores únicos de um campo de metadados.

**Query Parameters:**
- `field` (obrigatório): Campo de metadados (module, company, project, env, etc)

**Exemplo:**
```bash
# Obter todas as empresas únicas
curl "http://localhost:5000/api/v1/services/metadata/unique-values?field=company"

# Obter todos os ambientes únicos
curl "http://localhost:5000/api/v1/services/metadata/unique-values?field=env"
```

**Resposta:**
```json
{
  "success": true,
  "field": "company",
  "values": ["Company A", "Company B", "Skills IT"],
  "total": 3
}
```

### `POST /services/bulk/register`
Registra múltiplos serviços em lote.

**Body (JSON):**
```json
[
  {
    "id": "service1",
    "name": "blackbox_exporter",
    "Meta": { ... }
  },
  {
    "id": "service2",
    "name": "blackbox_exporter",
    "Meta": { ... }
  }
]
```

### `DELETE /services/bulk/deregister`
Remove múltiplos serviços em lote.

**Body (JSON):**
```json
["service-id-1", "service-id-2", "service-id-3"]
```

---

## 🖥️ Nodes API (`/nodes`)

### `GET /nodes/`
Retorna todos os nós do cluster Consul.

**Resposta:**
```json
{
  "success": true,
  "data": [
    {
      "node": "glpi-grafana-prometheus.skillsit.com.br",
      "addr": "172.16.1.26",
      "status": "alive",
      "type": "server",
      "services_count": 15
    }
  ],
  "total": 1,
  "main_server": "172.16.1.26"
}
```

### `GET /nodes/{node_addr}/services`
Retorna serviços de um nó específico.

**Path Parameters:**
- `node_addr`: Endereço IP do nó

---

## ⚙️ Config API (`/config`)

### `GET /config/current`
Retorna configuração atual de conexão com Consul.

**Resposta:**
```json
{
  "host": "172.16.1.26",
  "port": 8500,
  "has_token": true,
  "main_server": "172.16.1.26",
  "known_nodes": {
    "glpi-grafana-prometheus.skillsit.com.br": "172.16.1.26",
    "consul-DTC-Genesis-Skills": "11.144.0.21",
    "consul-RMD-LDC-Rio": "172.16.200.14"
  }
}
```

### `GET /config/health`
Testa conectividade com servidor Consul.

**Query Parameters:**
- `host` (opcional): Host customizado para testar
- `port` (opcional): Porta customizada para testar
- `token` (opcional): Token customizado para testar

**Exemplo:**
```bash
# Testar com configuração atual
curl http://localhost:5000/api/v1/config/health

# Testar com servidor diferente
curl "http://localhost:5000/api/v1/config/health?host=11.144.0.21"
```

**Resposta:**
```json
{
  "healthy": true,
  "message": "Conectado com sucesso ao Consul em 172.16.1.26:8500",
  "consul_version": "1.17.0",
  "leader": "172.16.1.26:8300",
  "nodes_count": 3
}
```

### `GET /config/known-nodes`
Retorna lista de nós conhecidos.

**Resposta:**
```json
{
  "success": true,
  "nodes": [
    {
      "name": "glpi-grafana-prometheus.skillsit.com.br",
      "address": "172.16.1.26",
      "is_main": true
    }
  ],
  "total": 3
}
```

### `POST /config/test-connection`
Testa conexão com configurações customizadas.

**Body (JSON):**
```json
{
  "host": "172.16.1.26",
  "port": 8500,
  "token": "your-token-here"
}
```

### `GET /config/modules`
Retorna módulos de monitoramento disponíveis.

**Resposta:**
```json
{
  "success": true,
  "modules": [
    "icmp",
    "http_2xx",
    "http_4xx",
    "https",
    "http_post_2xx",
    "tcp_connect",
    "ssh_banner",
    "pop3s_banner",
    "irc_banner"
  ],
  "total": 9
}
```

### `GET /config/meta-fields`
Retorna campos de metadados disponíveis.

**Resposta:**
```json
{
  "success": true,
  "fields": {
    "all": ["module", "company", "project", "env", "name", "instance", "localizacao", "tipo", ...],
    "required": ["module", "company", "project", "env", "name", "instance"],
    "optional": ["localizacao", "tipo", "cod_localidade", ...]
  },
  "total": 15
}
```

### `GET /config/environment-info`
Retorna informações completas do ambiente.

---

## 🔄 Mudança de Instância em Tempo Real

A API suporta conectar em diferentes instâncias Consul sem reiniciar o servidor. Use o parâmetro `node_addr` em qualquer endpoint:

**Exemplos:**

```bash
# Listar serviços do servidor principal (172.16.1.26)
curl http://localhost:5000/api/v1/services/

# Listar serviços do nó DTC
curl "http://localhost:5000/api/v1/services/?node_addr=11.144.0.21"

# Listar serviços do nó Rio
curl "http://localhost:5000/api/v1/services/?node_addr=172.16.200.14"

# Listar de TODOS os nós
curl "http://localhost:5000/api/v1/services/?node_addr=ALL"

# Criar serviço em nó específico
curl -X POST http://localhost:5000/api/v1/services/ \
  -H "Content-Type: application/json" \
  -d '{"id": "test", "name": "blackbox_exporter", "Meta": {...}, "node_addr": "11.144.0.21"}'
```

## 📊 Metadados de Serviços

### Campos Obrigatórios
- `module`: Módulo de monitoramento (icmp, http_2xx, etc)
- `company`: Nome da empresa
- `project`: Nome do projeto
- `env`: Ambiente (prod, dev, staging, etc)
- `name`: Nome do serviço
- `instance`: Instância alvo (IP, URL, etc)

### Campos Opcionais
- `localizacao`: Localização física
- `tipo`: Tipo do dispositivo/serviço
- `cod_localidade`: Código da localidade
- `cidade`: Cidade
- `notas`: Notas adicionais
- `provedor`: Provedor do serviço
- `fabricante`: Fabricante do equipamento
- `modelo`: Modelo do equipamento
- `tipo_dispositivo_abrev`: Tipo do dispositivo (abreviado)
- `glpi_url`: URL do item no GLPI

## 🚀 Iniciar a API

```bash
cd backend

# Instalar dependências
pip install -r requirements.txt

# Configurar .env
cp .env.example .env
# Edite .env com suas configurações

# Iniciar servidor
python app.py
```

A API estará disponível em `http://localhost:5000`

## 📝 Exemplos de Uso Completos

### Criar um serviço de monitoramento ICMP

```python
import requests

url = "http://localhost:5000/api/v1/services/"
data = {
    "id": "blackbox_icmp_router_prod",
    "name": "blackbox_exporter",
    "tags": ["monitoring", "network"],
    "port": 9115,
    "Meta": {
        "module": "icmp",
        "company": "Skills IT",
        "project": "Network Monitoring",
        "env": "prod",
        "name": "Router Principal",
        "instance": "192.168.1.1",
        "localizacao": "Data Center Principal",
        "tipo": "Router",
        "cidade": "São Paulo",
        "fabricante": "Cisco",
        "modelo": "ASR 1000"
    }
}

response = requests.post(url, json=data)
print(response.json())
```

### Buscar todos os serviços de produção

```python
import requests

url = "http://localhost:5000/api/v1/services/"
params = {"env": "prod"}

response = requests.get(url, params=params)
services = response.json()

print(f"Total de serviços em produção: {services['total']}")
for service_id, service_data in services['data'].items():
    meta = service_data.get('Meta', {})
    print(f"- {meta.get('name')}: {meta.get('instance')}")
```

### Obter valores únicos para popular um dropdown

```python
import requests

# Obter todas as empresas
url = "http://localhost:5000/api/v1/services/metadata/unique-values"
params = {"field": "company"}
response = requests.get(url, params=params)
companies = response.json()['values']

print("Empresas disponíveis:", companies)
```

## 🔒 Segurança

- O token do Consul nunca é exposto nas respostas da API
- Use HTTPS em produção
- Configure CORS adequadamente no `app.py`
- Mantenha o `.env` fora do controle de versão

## 🐛 Troubleshooting

### Erro ao conectar com Consul

```bash
# Testar conectividade
curl http://localhost:5000/api/v1/config/health

# Verificar configuração
curl http://localhost:5000/api/v1/config/current
```

### Verificar logs da API

O servidor exibe logs detalhados no console, incluindo tentativas de conexão e erros.

## 📚 Recursos Adicionais

- [Documentação Consul](https://www.consul.io/docs)
- [FastAPI Docs](https://fastapi.tiangolo.com/)
- Swagger UI: `http://localhost:5000/docs`
