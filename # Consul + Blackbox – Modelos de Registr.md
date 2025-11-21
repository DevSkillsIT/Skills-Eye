# Consul + Blackbox – Modelos de Registro via API

Este documento reúne exemplos práticos de JSON para registro de serviços no Consul via `/v1/agent/service/register`, alinhados com o cenário:

* Descoberta de targets pelo Consul.
* Monitoramento ativo feito pelo Prometheus + Blackbox Exporter.
* Checks nativos do Consul apenas quando fizer sentido (HTTP/TCP/UDP), sem duplicar lógica de ICMP ou HTTP 4xx.

---

## 1. Observação importante sobre o bloco `Node`

Quando você vê respostas da API como:

```json
{
  "Node": {
    "ID": "fba96284-1a64-bf18-f1ff-b5b07bce537a",
    "Node": "glpi-grafana-prometheus.skillsit.com.br",
    "Address": "172.16.1.26",
    "Datacenter": "dtc-skills-local",
    "TaggedAddresses": {
      "lan": "172.16.1.26",
      "lan_ipv4": "172.16.1.26",
      "wan": "172.16.1.26",
      "wan_ipv4": "172.16.1.26"
    },
    "Meta": {
      "consul-network-segment": "",
      "consul-version": "1.22.0"
    },
    "CreateIndex": 8,
    "ModifyIndex": 147260348
  },
  "Service": { ... },
  "Checks": [ ... ]
}
```

Esse bloco `Node` **não é enviado** quando você registra um serviço via `/v1/agent/service/register`.

### 1.1. Quem define o `Node` no `/v1/agent/service/register`?

* O `Node` é sempre o **agente local** onde você faz a chamada HTTP.
* Se você faz o `PUT` em `http://172.16.1.26:8500`, o serviço será registrado no node `glpi-grafana-prometheus.skillsit.com.br` (Palmas).
* Se fizer o mesmo payload em `http://172.16.200.14:8500`, o serviço será registrado no node do Rio.
* `Datacenter`, `TaggedAddresses`, `Meta.consul-version`, `CreateIndex` e `ModifyIndex` são todos definidos pelo próprio agente.

> Para escolher *de onde* o alvo será monitorado, você decide **em qual agente** bater, não passando `Node`/`Datacenter` no JSON.

### 1.2. Quando eu uso `Node`/`Datacenter` no payload?

Apenas quando você trabalha com a API de **Catálogo**:

* `/v1/catalog/register`
* `/v1/catalog/deregister`

Nesses casos, o JSON inclui explicitamente `Node`, `Address` e `Datacenter` para criar ou atualizar entradas do catálogo de qualquer nó. Porém:

* Essa API mexe **diretamente no catálogo**,
* **Não** configura checks reais rodando no agente (script/HTTP/TCP/TTL),
* A própria HashiCorp recomenda preferir os endpoints de **`/v1/agent/...`** para registro/remoção de serviços no dia a dia.

Neste documento (e no Skills Eye), o fluxo recomendado é:

* Registrar/editar/remover serviços sempre via `/v1/agent/service/...` no agente correto (Palmas, Rio, etc.).
* Usar `/v1/catalog/...` apenas para casos muito específicos.

---

## 2. Padrão geral de JSON para `/v1/agent/service/register`

### 2.1. O que é realmente obrigatório

De acordo com a documentação do Consul para `/v1/agent/service/register`, o campo realmente obrigatório é:

* `Name` – nome lógico do serviço.

Para o seu cenário (Consul + Blackbox + Prometheus), os seguintes campos são **fortemente recomendados**:

* `ID` – identificador único por agente (padrão: `"<module>/<company>/<grupo>/<tipo>@<name>"`).
* `Tags` – para o Prometheus filtrar os serviços por módulo (`"http_2xx"`, `"icmp"`, etc.).
* `Address` – alvo que será passado ao Blackbox (via meta `instance`) e, opcionalmente, usado em checks nativos do Consul.
* `Port` – porta do serviço quando fizer sentido (HTTP/HTTPS/TCP/DNS); em cenários puramente ICMP você pode simplesmente **omitir** esse campo.
* `Meta` – toda a estrutura de metadata que o Prometheus consome via `__meta_consul_service_metadata_*`.
* `Check` / `Checks` – apenas quando você quer adicionar um health check nativo do Consul (HTTP/TCP/UDP).

> Campos como `Node`, `Datacenter`, `TaggedAddresses` etc. **não aparecem no payload** do `/v1/agent/service/register`; eles são inferidos do agente que recebeu a chamada.

### 2.2. `EnableTagOverride` é obrigatório?

Não. Esse campo é opcional.

* Default: `EnableTagOverride = false`.
* Ele só é relevante quando você combina registros de serviços vindos de múltiplas fontes (ex.: catálogo vs. agentes) e quer permitir que *tags do catálogo* sobrescrevam as tags do agente.

No seu cenário (Skills Eye registrando tudo via agent, com um único caminho de verdade), **você pode simplesmente omitir** `EnableTagOverride` e trabalhar sempre com o padrão (`false`).

### 2.3. Template canônico (para o Skills Eye)

```json
{
  "ID": "${module}/${company}/${grupo}/${tipo}@${name}",
  "Name": "blackbox_exporter",
  "Tags": [
    "${module}"
  ],
  "Address": "${target_host}",
  "Port": ${port_or_0},
  "Meta": {
    "company": "${company}",
    "module": "${module}",
    "instance": "${instance}",
    "name": "${name}",
    "tipo_monitoramento": "${tipo_monitoramento}",
    "grupo_monitoramento": "${grupo_monitoramento}",
    "localizacao": "${localizacao}",
    "fabricante": "${fabricante}",
    "tipo": "${tipo}",
    "modelo": "${modelo}",
    "cod_localidade": "${cod_localidade}",
    "tipo_dispositivo_abrev": "${tipo_dispositivo_abrev}",
    "cidade": "${cidade}",
    "notas": "${notas}",
    "glpi_url": "${glpi_url}",
    "provedor": "${provedor}",
    "campoextra1": "${campoextra1}",
    "campoextra2": "${campoextra2}",
    "testeSP": "${testeSP}"
  }
  /* ,
  "Check": {
    ... opcional, depende do módulo ...
  } */
}
```

O backend do Skills Eye deve:

* Escolher **qual agente** chamar (`http://172.16.1.26:8500`, `http://172.16.200.14:8500`, etc.) conforme o nó escolhido.
* Montar o JSON acima com os valores preenchidos.
* Opcionalmente adicionar o bloco `Check` conforme o módulo.

---

## 3. Exemplos reais por módulo

Abaixo, exemplos concretos para cada módulo, já alinhados com o cenário atual.

### 3.1. `http_2xx` – com check TCP nativo no Consul

Neste exemplo, o serviço `site-aprosoja` será registrado no agente onde você fizer o `PUT` (por exemplo, o node de Palmas). O Consul fará um check TCP simples em `aprosojato.com.br:80`, enquanto o Blackbox fará o HTTP completo (status code, latência etc.).

```json
{
  "ID": "http_2xx/Aprosoja/None/None@site-aprosoja",
  "Name": "blackbox_exporter",
  "Tags": [
    "http_2xx"
  ],
  "Address": "aprosojato.com.br",
  "Port": 80,
  "Meta": {
    "company": "Aprosoja",
    "module": "http_2xx",
    "instance": "https://aprosojato.com.br/",
    "name": "site-aprosoja",
    "tipo_monitoramento": "site-externo",
    "grupo_monitoramento": "sites-corporativos",
    "localizacao": "Internet",
    "fabricante": "",
    "tipo": "web",
    "modelo": "",
    "cod_localidade": "",
    "tipo_dispositivo_abrev": "WEB",
    "cidade": "",
    "notas": "Site institucional principal",
    "glpi_url": "",
    "provedor": "Cloudflare",
    "campoextra1": "",
    "campoextra2": "",
    "testeSP": ""
  },
  "Check": {
    "Name": "http_2xx site-aprosoja (Consul TCP)",
    "TCP": "aprosojato.com.br:80",
    "Interval": "15s",
    "Timeout": "5s",
    "DeregisterCriticalServiceAfter": "24h"
  }
}
```

> Se você preferir que o Consul faça um check HTTP completo em vez de TCP, basta trocar o bloco `Check` para `HTTP`, `Method`, etc. – a lógica de registro no agente continua a mesma.

**Form Schema (http_2xx):**

```json
{
  "fields": [
    {
      "name": "tags",
      "label": "Tags",
      "type": "tags",
      "col_span": 10,
      "required": true,
      "default": ["http_2xx"],
      "placeholder": "Selecione ou digite tags...",
      "help": "Tags do serviço no Consul. A tag 'http_2xx' é obrigatória."
    },
    {
      "name": "address",
      "label": "Hostname (Address)",
      "type": "text",
      "col_span": 14,
      "required": true,
      "placeholder": "exemplo.com",
      "help": "Hostname do site SEM protocolo. Este campo vai para 'Address' do Consul.",
      "validation": {
        "pattern": "^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$|^(?!^[0-9.]+$)(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\\.)+[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?$",
        "message": "Deve ser um IP válido (0-255) ou Hostname válido (ex: teste.uol.com.br)."
      }
    },
    {
      "name": "port",
      "label": "Porta",
      "type": "number",
      "col_span": 6,
      "required": false,
      "default": 80,
      "placeholder": "80",
      "help": "Porta do serviço (80/HTTP, 443/HTTPS)",
      "validation": {
        "min": 1,
        "max": 65535,
        "message": "Porta deve estar entre 1 e 65535"
      }
    },
    {
      "name": "instance",
      "label": "URL Completa (Meta.instance)",
      "type": "text",
      "col_span": 18,
      "required": true,
      "placeholder": "https://exemplo.com/",
      "help": "URL completa do site COM protocolo (http:// ou https://).",
      "validation": {
        "pattern": "^https?:\\/\\/.*$",
        "message": "Deve ser uma URL válida começando com http:// ou https://"
      }
    },
    {
      "name": "enable_check",
      "label": "Ativar Check do Consul",
      "type": "checkbox",
      "col_span": 24,
      "required": false,
      "default": false,
      "help": "Se ativado, o Consul fará um check de saúde."
    },
    {
      "name": "check_TCP",
      "label": "Check TCP (hostname:porta)",
      "type": "text",
      "col_span": 12,
      "required": false,
      "placeholder": "exemplo.com:80",
      "help": "Endereço e porta para check TCP do Consul.",
      "depends_on": "enable_check",
      "validation": {
        "pattern": "^(?:(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)|^(?!^[0-9.]+$)(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\\.)+[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?):[0-9]{1,5}$",
        "message": "Formato inválido. Use hostname:porta (ex: google.com:80)"
      }
    },
    {
      "name": "check_HTTP",
      "label": "Check HTTP (URL completa)",
      "type": "text",
      "col_span": 12,
      "required": false,
      "placeholder": "https://exemplo.com",
      "help": "URL completa para check HTTP do Consul.",
      "depends_on": "enable_check",
      "validation": {
        "pattern": "^https?:\\/\\/.*$",
        "message": "Deve ser uma URL válida começando com http:// ou https://"
      }
    },
    {
      "name": "check_Interval",
      "label": "Intervalo",
      "type": "text",
      "col_span": 8,
      "required": false,
      "default": "30s",
      "placeholder": "30s",
      "help": "Intervalo entre checks.",
      "depends_on": "enable_check"
    },
    {
      "name": "check_Timeout",
      "label": "Timeout",
      "type": "text",
      "col_span": 8,
      "required": false,
      "default": "5s",
      "placeholder": "5s",
      "help": "Timeout do check.",
      "depends_on": "enable_check"
    },
    {
      "name": "check_DeregisterCriticalServiceAfter",
      "label": "Desregistrar Após",
      "type": "text",
      "col_span": 8,
      "required": false,
      "default": "96h",
      "placeholder": "96h",
      "help": "Tempo para desregistrar serviço crítico.",
      "depends_on": "enable_check"
    },
    {
      "name": "check_Name",
      "label": "Nome do Check",
      "type": "text",
      "col_span": 24,
      "required": false,
      "placeholder": "http_2xx {name} (Consul TCP)",
      "help": "Nome descritivo do check.",
      "depends_on": "enable_check"
    }
  ],
  "required_metadata": ["tags", "address", "instance"],
  "optional_metadata": ["port", "enable_check", "check_TCP", "check_HTTP", "check_Interval", "check_Timeout", "check_Name", "check_DeregisterCriticalServiceAfter"]
}
```

---

### 3.2. `icmp` – sem check nativo no Consul (Cenário B)

Aqui o Consul é usado apenas para descoberta e o ICMP é realizado exclusivamente pelo Blackbox Exporter + Prometheus. Para esse tipo de serviço:

* Você **não precisa** de `Port`.
* Pode deixar o `Address` vazio (`""`), usando apenas `Meta.instance` como destino real do ping.

Exemplo alinhado ao que você já tem hoje em produção:

```json
{
  "ID": "icmp/Aprosoja/Monitora_Provedor/Link_Primario@at-pmw-link-sim_LP",
  "Name": "blackbox_exporter",
  "Tags": [
    "icmp"
  ],
  "Address": "",
  "Meta": {
    "cidade": "PALMAS",
    "cod_localidade": "ATPMW",
    "company": "Aprosoja",
    "fabricante": "",
    "glpi_url": "",
    "grupo_monitoramento": "Monitora_Provedor",
    "instance": "177.126.85.178",
    "localizacao": "Escritório Palmas",
    "modelo": "",
    "module": "icmp",
    "name": "at-pmw-link-sim_LP",
    "notas": "Aprosoja Monitora_Provedor Link_Primario at-pmw-link-sim_LP 177.126.85.178",
    "provedor": "SIM",
    "tipo": "Monitora_Provedor",
    "tipo_dispositivo_abrev": "",
    "tipo_monitoramento": "Link_Primario"
  }
}
```

> Note que o IP real usado no ping está em `Meta.instance` (`177.126.85.178`). O Prometheus/Blackbox usa exatamente esse campo via relabel (`__meta_consul_service_metadata_instance` → `__param_target`).

**Form Schema (icmp):**

```json
{
  "fields": [
    {
      "name": "tags",
      "label": "Tags",
      "type": "tags",
      "col_span": 10,
      "required": true,
      "default": ["icmp"],
      "placeholder": "Selecione tags...",
      "help": "Tags do serviço (obrigatório 'icmp')."
    },
    {
      "name": "instance",
      "label": "IP ou Hostname",
      "type": "text",
      "col_span": 14,
      "required": true,
      "placeholder": "192.168.1.1 ou server.local",
      "help": "Endereço IP ou hostname para ping.",
      "validation": {
        "pattern": "^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$|^(?!^[0-9.]+$)(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\\.)+[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?$",
        "message": "Deve ser um IP válido (0-255) ou Hostname válido (ex: teste.uol.com.br)."
      }
    }
  ],
  "required_metadata": ["tags", "instance"],
  "optional_metadata": []
}
```

---

### 3.3. `selfnode_exporter` – Windows (porta 9115)

Exemplo de serviço Windows registrado para um exporter (por exemplo, Windows Exporter) acessível em `172.16.1.36:9115`. Aqui faz sentido manter `Address` e `Port`, pois o Prometheus fará scrape HTTP nessa porta e você pode, se quiser, adicionar um check TCP/HTTP do Consul.

```json
{
  "ID": "GrupoWink/AD/Cliente/DTC_Cluster_Local@Cli_GWPMWVM010-AD_172.16.1.36",
  "Name": "selfnode_exporter",
  "Tags": [
    "windows",
    "grupowink"
  ],
  "Address": "172.16.1.36",
  "Port": 9115,
  "Meta": {
    "account": "AD",
    "group": "DTC_Cluster_Local",
    "instance": "172.16.1.36:9115",
    "name": "Cli_GWPMWVM010-AD_172.16.1.36",
    "os": "windows",
    "region": "Cliente",
    "vendor": "GrupoWink"
  },
  "Check": {
    "Name": "Cli_GWPMWVM010-AD_172.16.1.36 (Consul TCP)",
    "TCP": "172.16.1.36:9115",
    "Interval": "30s",
    "Timeout": "5s",
    "DeregisterCriticalServiceAfter": "90m"
  }
}
```

> O bloco `TaggedAddresses` que aparece nas respostas de health (`lan_ipv4` / `wan_ipv4`) é opcional no registro. Se quiser, você pode incluí-lo no `Service` também, mas para o teu fluxo Prometheus/Consul ele não é estritamente necessário.

**Form Schema (selfnode_exporter - Windows):**

```json
{
  "fields": [
    {
      "name": "tags",
      "label": "Tags",
      "type": "tags",
      "col_span": 10,
      "required": true,
      "default": ["windows"],
      "placeholder": "Selecione tags...",
      "help": "Tags do serviço (obrigatório 'windows')."
    },
    {
      "name": "address",
      "label": "Hostname (Address)",
      "type": "text",
      "col_span": 14,
      "required": true,
      "placeholder": "172.16.1.36",
      "help": "Hostname ou IP do servidor Windows.",
      "validation": {
        "pattern": "^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$|^(?!^[0-9.]+$)(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\\.)+[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?$",
        "message": "Deve ser um IP válido (0-255) ou Hostname válido."
      }
    },
    {
      "name": "port",
      "label": "Porta",
      "type": "number",
      "col_span": 6,
      "required": true,
      "default": 9182,
      "placeholder": "9182",
      "help": "Porta do Windows Exporter (padrão 9182).",
      "validation": {
        "min": 1,
        "max": 65535,
        "message": "Porta deve estar entre 1 e 65535"
      }
    },
    {
      "name": "instance",
      "label": "Host:Porta (Meta.instance)",
      "type": "text",
      "col_span": 18,
      "required": true,
      "placeholder": "172.16.1.36:9115",
      "help": "Alvo no formato Host:Porta.",
      "validation": {
        "pattern": "^(?:(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)|^(?!^[0-9.]+$)(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\\.)+[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?):[0-9]{1,5}$",
        "message": "Formato inválido. Use hostname:porta"
      }
    },
    {
      "name": "enable_check",
      "label": "Ativar Check do Consul",
      "type": "checkbox",
      "col_span": 24,
      "required": false,
      "default": true,
      "help": "Se ativado, o Consul fará um check de saúde TCP."
    },
    {
      "name": "check_TCP",
      "label": "Check TCP (hostname:porta)",
      "type": "text",
      "col_span": 8,
      "required": false,
      "placeholder": "172.16.1.36:9115",
      "help": "Endereço e porta para check TCP.",
      "depends_on": "enable_check",
      "validation": {
        "pattern": "^(?:(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)|^(?!^[0-9.]+$)(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\\.)+[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?):[0-9]{1,5}$",
        "message": "Formato inválido. Use hostname:porta"
      }
    },
    {
      "name": "check_Interval",
      "label": "Intervalo",
      "type": "text",
      "col_span": 8,
      "required": false,
      "default": "30s",
      "placeholder": "30s",
      "help": "Intervalo entre checks.",
      "depends_on": "enable_check"
    },
    {
      "name": "check_Timeout",
      "label": "Timeout",
      "type": "text",
      "col_span": 8,
      "required": false,
      "default": "5s",
      "placeholder": "5s",
      "help": "Timeout do check.",
      "depends_on": "enable_check"
    },
    {
      "name": "check_DeregisterCriticalServiceAfter",
      "label": "Desregistrar Após",
      "type": "text",
      "col_span": 8,
      "required": false,
      "default": "96h",
      "placeholder": "96h",
      "help": "Tempo para desregistrar serviço crítico.",
      "depends_on": "enable_check"
    },
    {
      "name": "check_Name",
      "label": "Nome do Check",
      "type": "text",
      "col_span": 8,
      "required": false,
      "placeholder": "windows_node {name} (Consul TCP)",
      "help": "Nome descritivo do check.",
      "depends_on": "enable_check"
    }
  ],
  "required_metadata": ["tags", "address", "instance", "port"],
  "optional_metadata": ["enable_check", "check_TCP", "check_Interval", "check_Timeout", "check_Name", "check_DeregisterCriticalServiceAfter"]
}
```

---

### 3.4. `selfnode_exporter` – Linux (porta 9100)

Exemplo de serviço Linux para o Node Exporter padrão em `172.16.1.25:9100`.

```json
{
  "ID": "Skills/Aplicacao/InfraLocal/DTC_Cluster_Local@HUDU_172.16.1.25",
  "Name": "selfnode_exporter",
  "Tags": [
    "Skills",
    "linux"
  ],
  "Address": "172.16.1.25",
  "Port": 9100,
  "Meta": {
    "account": "Aplicacao",
    "group": "DTC_Cluster_Local",
    "instance": "172.16.1.25:9100",
    "name": "HUDU_172.16.1.25"
  },
  "Check": {
    "Name": "HUDU_172.16.1.25 (Consul TCP)",
    "TCP": "172.16.1.25:9100",
    "Interval": "30s",
    "Timeout": "5s",
    "DeregisterCriticalServiceAfter": "90m"
  }
}
```

> Aqui novamente o Consul pode fazer apenas um check TCP simples (porta aberta). Quem valida de fato as métricas expostas (HTTP 200, conteúdo, etc.) é o Prometheus.

**Form Schema (selfnode_exporter - Linux):**

```json
{
  "fields": [
    {
      "name": "tags",
      "label": "Tags",
      "type": "tags",
      "col_span": 10,
      "required": true,
      "default": ["linux"],
      "placeholder": "Selecione tags...",
      "help": "Tags do serviço (obrigatório 'linux')."
    },
    {
      "name": "address",
      "label": "Hostname (Address)",
      "type": "text",
      "col_span": 14,
      "required": true,
      "placeholder": "172.16.1.25",
      "help": "Hostname ou IP do servidor Linux.",
      "validation": {
        "pattern": "^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$|^(?!^[0-9.]+$)(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\\.)+[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?$",
        "message": "Deve ser um IP válido (0-255) ou Hostname válido."
      }
    },
    {
      "name": "port",
      "label": "Porta",
      "type": "number",
      "col_span": 6,
      "required": true,
      "default": 9100,
      "placeholder": "9100",
      "help": "Porta do Node Exporter (padrão 9100).",
      "validation": {
        "min": 1,
        "max": 65535,
        "message": "Porta deve estar entre 1 e 65535"
      }
    },
    {
      "name": "instance",
      "label": "Host:Porta (Meta.instance)",
      "type": "text",
      "col_span": 18,
      "required": true,
      "placeholder": "172.16.1.25:9100",
      "help": "Alvo no formato Host:Porta.",
      "validation": {
        "pattern": "^(?:(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)|^(?!^[0-9.]+$)(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\\.)+[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?):[0-9]{1,5}$",
        "message": "Formato inválido. Use hostname:porta"
      }
    },
    {
      "name": "enable_check",
      "label": "Ativar Check do Consul",
      "type": "checkbox",
      "col_span": 24,
      "required": false,
      "default": true,
      "help": "Se ativado, o Consul fará um check de saúde TCP."
    },
    {
      "name": "check_TCP",
      "label": "Check TCP (hostname:porta)",
      "type": "text",
      "col_span": 8,
      "required": false,
      "placeholder": "172.16.1.25:9100",
      "help": "Endereço e porta para check TCP.",
      "depends_on": "enable_check",
      "validation": {
        "pattern": "^(?:(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)|^(?!^[0-9.]+$)(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\\.)+[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?):[0-9]{1,5}$",
        "message": "Formato inválido. Use hostname:porta"
      }
    },
    {
      "name": "check_Interval",
      "label": "Intervalo",
      "type": "text",
      "col_span": 8,
      "required": false,
      "default": "30s",
      "placeholder": "30s",
      "help": "Intervalo entre checks.",
      "depends_on": "enable_check"
    },
    {
      "name": "check_Timeout",
      "label": "Timeout",
      "type": "text",
      "col_span": 8,
      "required": false,
      "default": "5s",
      "placeholder": "5s",
      "help": "Timeout do check.",
      "depends_on": "enable_check"
    },
    {
      "name": "check_DeregisterCriticalServiceAfter",
      "label": "Desregistrar Após",
      "type": "text",
      "col_span": 8,
      "required": false,
      "default": "96h",
      "placeholder": "96h",
      "help": "Tempo para desregistrar serviço crítico.",
      "depends_on": "enable_check"
    },
    {
      "name": "check_Name",
      "label": "Nome do Check",
      "type": "text",
      "col_span": 8,
      "required": false,
      "placeholder": "linux_node {name} (Consul TCP)",
      "help": "Nome descritivo do check.",
      "depends_on": "enable_check"
    }
  ],
  "required_metadata": ["tags", "address", "instance", "port"],
  "optional_metadata": ["enable_check", "check_TCP", "check_Interval", "check_Timeout", "check_Name", "check_DeregisterCriticalServiceAfter"]
}
```

---

### 3.5. `http_4xx` – apenas Blackbox (sem check nativo Consul)

No módulo `http_4xx` do Blackbox, você espera códigos de resposta 4xx (por exemplo, 400/401/403/404) e quer considerar isso **OK** do ponto de vista de monitoramento.

O Consul, por padrão, considera respostas 4xx como **falhas** em checks HTTP nativos. Por isso, a recomendação aqui é:

* **Não configurar check nativo do Consul** para esse serviço.
* Deixar toda a lógica de "4xx é saudável" por conta do Blackbox + Prometheus.

Exemplo:

```json
{
  "ID": "http_4xx/EmpresaX/Apis-Teste/ErroEsperado@api-erro-controle",
  "Name": "blackbox_exporter",
  "Tags": [
    "http_4xx"
  ],
  "Address": "api.exemplo.com.br",
  "Port": 80,
  "Meta": {
    "company": "EmpresaX",
    "module": "http_4xx",
    "instance": "http://api.exemplo.com.br/endpoint-que-retorna-404",
    "name": "api-erro-controle",
    "tipo_monitoramento": "api-interna",
    "grupo_monitoramento": "apis-4xx",
    "localizacao": "Datacenter-SP",
    "fabricante": "",
    "tipo": "api",
    "modelo": "",
    "cod_localidade": "SP-DC1",
    "tipo_dispositivo_abrev": "API",
    "cidade": "São Paulo",
    "notas": "Endpoint que deve retornar 404 para testes",
    "glpi_url": "",
    "provedor": "Interno",
    "campoextra1": "",
    "campoextra2": "",
    "testeSP": ""
  }
}
```

> O Blackbox (módulo `http_4xx`) é quem valida se o retorno 4xx é o esperado. O Consul apenas registra o serviço e deixa o health baseado no `serfHealth` do node (ou em outros checks que você eventualmente adicionar).

**Form Schema (http_4xx):**

```json
{
  "fields": [
    {
      "name": "tags",
      "label": "Tags",
      "type": "tags",
      "col_span": 10,
      "required": true,
      "default": ["http_4xx"],
      "placeholder": "Selecione ou digite tags...",
      "help": "Tags do serviço no Consul. A tag 'http_4xx' é obrigatória."
    },
    {
      "name": "address",
      "label": "Hostname (Address)",
      "type": "text",
      "col_span": 14,
      "required": true,
      "placeholder": "api.exemplo.com.br",
      "help": "Hostname do site SEM protocolo. Este campo vai para 'Address' do Consul.",
      "validation": {
        "pattern": "^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$|^(?!^[0-9.]+$)(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\\.)+[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?$",
        "message": "Deve ser um IP válido (0-255) ou Hostname válido (ex: teste.uol.com.br)."
      }
    },
    {
      "name": "port",
      "label": "Porta",
      "type": "number",
      "col_span": 6,
      "required": false,
      "default": 80,
      "placeholder": "80",
      "help": "Porta do serviço (80 para HTTP)",
      "validation": {
        "min": 1,
        "max": 65535,
        "message": "Porta deve estar entre 1 e 65535"
      }
    },
    {
      "name": "instance",
      "label": "URL Completa (Meta.instance)",
      "type": "text",
      "col_span": 18,
      "required": true,
      "placeholder": "http://api.exemplo.com.br/endpoint-que-retorna-404",
      "help": "URL completa do site COM protocolo. Este campo vai para Meta.instance e é usado pelo Blackbox Exporter.",
      "validation": {
        "pattern": "^https?:\\/\\/.*$",
        "message": "Deve ser uma URL válida começando com http:// ou https://"
      }
    }
  ],
  "required_metadata": ["tags", "address", "instance"],
  "optional_metadata": ["port"]
}
```

---

### 3.6. `https` – check HTTP/HTTPS no Blackbox + opcional no Consul

O módulo `https` do Blackbox faz uma requisição HTTPS completa, checando status code e a camada TLS conforme a sua configuração (por exemplo, certificados válidos, sem `insecure_skip_verify`, etc.).

No Consul, você pode complementar com:

* Um **check HTTP** direto na URL,
* Ou, se quiser algo mais simples, um check **TCP** em `host:443`.

Exemplo usando check HTTP no Consul:

```json
{
  "ID": "https/Ramada/Portais/Clientes@portal-ramada",
  "Name": "blackbox_exporter",
  "Tags": [
    "https"
  ],
  "Address": "portal.ramada.com.br",
  "Port": 443,
  "Meta": {
    "company": "Ramada",
    "module": "https",
    "instance": "https://portal.ramada.com.br/",
    "name": "portal-ramada",
    "tipo_monitoramento": "portal-cliente",
    "grupo_monitoramento": "sites-corporativos",
    "localizacao": "Internet",
    "fabricante": "",
    "tipo": "web",
    "modelo": "",
    "cod_localidade": "",
    "tipo_dispositivo_abrev": "WEB",
    "cidade": "",
    "notas": "Portal do cliente Ramada",
    "glpi_url": "",
    "provedor": "Cloud Provider",
    "campoextra1": "",
    "campoextra2": "",
    "testeSP": ""
  },
  "Check": {
    "Name": "https portal-ramada (Consul HTTP)",
    "HTTP": "https://portal.ramada.com.br/",
    "Method": "GET",
    "TLSSkipVerify": false,
    "Interval": "30s",
    "Timeout": "5s",
    "DeregisterCriticalServiceAfter": "90m"
  }
}
```

> O Blackbox continua sendo o "dono" da lógica de status codes e TLS. O Consul apenas adiciona uma visão de health mais básica, mas útil na UI e em automações que dependem do catálogo.

**Form Schema (https):**

```json
{
  "fields": [
    {
      "name": "tags",
      "label": "Tags",
      "type": "tags",
      "col_span": 10,
      "required": true,
      "default": ["https"],
      "placeholder": "Selecione ou digite tags...",
      "help": "Tags do serviço no Consul. A tag 'https' é obrigatória."
    },
    {
      "name": "address",
      "label": "Hostname (Address)",
      "type": "text",
      "col_span": 14,
      "required": true,
      "placeholder": "portal.ramada.com.br",
      "help": "Hostname do site SEM protocolo. Este campo vai para 'Address' do Consul.",
      "validation": {
        "pattern": "^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$|^(?!^[0-9.]+$)(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\\.)+[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?$",
        "message": "Deve ser um IP válido (0-255) ou Hostname válido (ex: teste.uol.com.br)."
      }
    },
    {
      "name": "port",
      "label": "Porta",
      "type": "number",
      "col_span": 6,
      "required": true,
      "default": 443,
      "placeholder": "443",
      "help": "Porta do serviço (443 para HTTPS)",
      "validation": {
        "min": 1,
        "max": 65535,
        "message": "Porta deve estar entre 1 e 65535"
      }
    },
    {
      "name": "instance",
      "label": "URL Completa (Meta.instance)",
      "type": "text",
      "col_span": 18,
      "required": true,
      "placeholder": "https://portal.ramada.com.br/",
      "help": "URL completa do site com HTTPS.",
      "validation": {
        "pattern": "^https?:\\/\\/.*$",
        "message": "Deve ser uma URL válida começando com http:// ou https://"
      }
    },
    {
      "name": "enable_check",
      "label": "Ativar Check do Consul",
      "type": "checkbox",
      "col_span": 24,
      "required": false,
      "default": true,
      "help": "Se ativado, o Consul fará um check de saúde (HTTP ou TCP)."
    },
    {
      "name": "check_TCP",
      "label": "Check TCP (hostname:porta)",
      "type": "text",
      "col_span": 12,
      "required": false,
      "placeholder": "portal.ramada.com.br:443",
      "help": "Endereço e porta para check TCP.",
      "depends_on": "enable_check",
      "validation": {
        "pattern": "^(?:(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)|^(?!^[0-9.]+$)(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\\.)+[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?):[0-9]{1,5}$",
        "message": "Formato inválido. Use hostname:porta (ex: google.com:443)"
      }
    },
    {
      "name": "check_HTTP",
      "label": "Check HTTP (URL completa)",
      "type": "text",
      "col_span": 12,
      "required": false,
      "placeholder": "https://portal.ramada.com.br/",
      "help": "URL completa para check HTTP do Consul.",
      "depends_on": "enable_check",
      "validation": {
        "pattern": "^https?:\\/\\/.*$",
        "message": "Deve ser uma URL válida começando com http:// ou https://"
      }
    },
    {
      "name": "check_Interval",
      "label": "Intervalo",
      "type": "text",
      "col_span": 8,
      "required": false,
      "default": "30s",
      "placeholder": "30s",
      "help": "Intervalo entre checks.",
      "depends_on": "enable_check"
    },
    {
      "name": "check_Timeout",
      "label": "Timeout",
      "type": "text",
      "col_span": 8,
      "required": false,
      "default": "5s",
      "placeholder": "5s",
      "help": "Timeout do check.",
      "depends_on": "enable_check"
    },
    {
      "name": "check_Name",
      "label": "Nome do Check",
      "type": "text",
      "col_span": 8,
      "required": false,
      "placeholder": "https {name} (Consul HTTP)",
      "help": "Nome descritivo do check.",
      "depends_on": "enable_check"
    },
    {
      "name": "check_DeregisterCriticalServiceAfter",
      "label": "Desregistrar Após",
      "type": "text",
      "col_span": 24,
      "required": false,
      "default": "96h",
      "placeholder": "96h",
      "help": "Tempo para desregistrar serviço crítico.",
      "depends_on": "enable_check"
    }
  ],
  "required_metadata": ["tags", "address", "instance", "port"],
  "optional_metadata": ["enable_check", "check_TCP", "check_HTTP", "check_Interval", "check_Timeout", "check_Name", "check_DeregisterCriticalServiceAfter"]
}
```

---

### 3.7. `http_post_2xx` – webhooks / APIs que usam POST

O módulo `http_post_2xx` do Blackbox faz requisições HTTP `POST` esperando código 2xx. É perfeito para webhooks e endpoints de integrações.

No Consul, você pode adicionar um check HTTP `POST` simples apontando para um endpoint de health ou para o próprio webhook (se for idempotente e barato):

```json
{
  "ID": "http_post_2xx/Ramada/Integracoes/NF@webhook-notas-fiscais",
  "Name": "blackbox_exporter",
  "Tags": [
    "http_post_2xx"
  ],
  "Address": "api.ramada.com.br",
  "Port": 443,
  "Meta": {
    "company": "Ramada",
    "module": "http_post_2xx",
    "instance": "https://api.ramada.com.br/webhook/health",
    "name": "webhook-notas-fiscais",
    "tipo_monitoramento": "webhook",
    "grupo_monitoramento": "integracoes-fiscais",
    "localizacao": "Datacenter-RJ",
    "fabricante": "",
    "tipo": "api",
    "modelo": "",
    "cod_localidade": "RJ-DC1",
    "tipo_dispositivo_abrev": "API",
    "cidade": "Rio de Janeiro",
    "notas": "Webhook de notas fiscais",
    "glpi_url": "",
    "provedor": "Interno",
    "campoextra1": "",
    "campoextra2": "",
    "testeSP": ""
  },
  "Check": {
    "Name": "webhook-notas-fiscais (Consul HTTP POST)",
    "HTTP": "https://api.ramada.com.br/webhook/health",
    "Method": "POST",
    "Header": {
      "Content-Type": ["application/json"]
    },
    "Body": "{\"healthcheck\": true}",
    "Interval": "30s",
    "Timeout": "5s",
    "DeregisterCriticalServiceAfter": "90m"
  }
}
```

> O Blackbox valida a lógica de status code e tempo de resposta; o Consul garante uma visão de disponibilidade básica daquele endpoint.

**Form Schema (http_post_2xx):**

```json
{
  "fields": [
    {
      "name": "tags",
      "label": "Tags",
      "type": "tags",
      "col_span": 10,
      "required": true,
      "default": ["http_post_2xx"],
      "placeholder": "Selecione ou digite tags...",
      "help": "Tags do serviço no Consul. A tag 'http_post_2xx' é obrigatória."
    },
    {
      "name": "address",
      "label": "Hostname (Address)",
      "type": "text",
      "col_span": 14,
      "required": true,
      "placeholder": "api.ramada.com.br",
      "help": "Hostname do site SEM protocolo. Este campo vai para 'Address' do Consul.",
      "validation": {
        "pattern": "^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$|^(?!^[0-9.]+$)(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\\.)+[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?$",
        "message": "Deve ser um IP válido (0-255) ou Hostname válido."
      }
    },
    {
      "name": "port",
      "label": "Porta",
      "type": "number",
      "col_span": 6,
      "required": true,
      "default": 443,
      "placeholder": "443",
      "help": "Porta do serviço (80/HTTP, 443/HTTPS)",
      "validation": {
        "min": 1,
        "max": 65535,
        "message": "Porta deve estar entre 1 e 65535"
      }
    },
    {
      "name": "instance",
      "label": "URL Completa (Meta.instance)",
      "type": "text",
      "col_span": 18,
      "required": true,
      "placeholder": "https://api.ramada.com.br/webhook/health",
      "help": "URL completa do site com HTTPS (para POST).",
      "validation": {
        "pattern": "^https?:\\/\\/.*$",
        "message": "Deve ser uma URL válida começando com http:// ou https://"
      }
    },
    {
      "name": "enable_check",
      "label": "Ativar Check do Consul",
      "type": "checkbox",
      "col_span": 24,
      "required": false,
      "default": true,
      "help": "Se ativado, o Consul fará um check de saúde."
    },
    {
      "name": "check_TCP",
      "label": "Check TCP (hostname:porta)",
      "type": "text",
      "col_span": 12,
      "required": false,
      "placeholder": "api.ramada.com.br:443",
      "help": "Endereço e porta para check TCP.",
      "depends_on": "enable_check",
      "validation": {
        "pattern": "^(?:(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)|^(?!^[0-9.]+$)(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\\.)+[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?):[0-9]{1,5}$",
        "message": "Formato inválido. Use hostname:porta"
      }
    },
    {
      "name": "check_HTTP",
      "label": "Check HTTP (URL completa)",
      "type": "text",
      "col_span": 12,
      "required": false,
      "placeholder": "https://api.ramada.com.br/webhook/health",
      "help": "URL completa para check HTTP POST do Consul.",
      "depends_on": "enable_check",
      "validation": {
        "pattern": "^https?:\\/\\/.*$",
        "message": "Deve ser uma URL válida começando com http:// ou https://"
      }
    },
    {
      "name": "check_Method",
      "label": "Método HTTP Check",
      "type": "text",
      "col_span": 8,
      "required": false,
      "default": "POST",
      "placeholder": "POST",
      "help": "Método HTTP para o check do Consul.",
      "depends_on": "enable_check"
    },
    {
      "name": "check_Body",
      "label": "Corpo do Request (JSON)",
      "type": "textarea",
      "col_span": 24,
      "required": false,
      "placeholder": "{\"healthcheck\": true}",
      "help": "Corpo da requisição para o check POST.",
      "depends_on": "enable_check"
    },
    {
      "name": "check_Interval",
      "label": "Intervalo",
      "type": "text",
      "col_span": 8,
      "required": false,
      "default": "30s",
      "placeholder": "30s",
      "help": "Intervalo entre checks.",
      "depends_on": "enable_check"
    },
    {
      "name": "check_Timeout",
      "label": "Timeout",
      "type": "text",
      "col_span": 8,
      "required": false,
      "default": "5s",
      "placeholder": "5s",
      "help": "Timeout do check.",
      "depends_on": "enable_check"
    },
    {
      "name": "check_Name",
      "label": "Nome do Check",
      "type": "text",
      "col_span": 8,
      "required": false,
      "placeholder": "http_post_2xx {name}",
      "help": "Nome descritivo do check.",
      "depends_on": "enable_check"
    },
    {
      "name": "check_DeregisterCriticalServiceAfter",
      "label": "Desregistrar Após",
      "type": "text",
      "col_span": 24,
      "required": false,
      "default": "96h",
      "placeholder": "96h",
      "help": "Tempo para desregistrar serviço crítico.",
      "depends_on": "enable_check"
    }
  ],
  "required_metadata": ["tags", "address", "instance", "port"],
  "optional_metadata": ["enable_check", "check_TCP", "check_HTTP", "check_Method", "check_Body", "check_Interval", "check_Timeout", "check_Name", "check_DeregisterCriticalServiceAfter"]
}
```

---

### 3.8. `tcp_connect` – conectividade TCP genérica

O módulo `tcp_connect` do Blackbox testa abertura de conexão TCP em uma porta específica, útil para bancos de dados, filas, serviços internos, etc.

No Consul, faz bastante sentido usar um check TCP nativo apontando para o mesmo host/porta:

```json
{
  "ID": "tcp_connect/Ramada/Servicos/BD@sql-principal",
  "Name": "blackbox_exporter",
  "Tags": [
    "tcp_connect"
  ],
  "Address": "172.16.200.10",
  "Port": 1433,
  "Meta": {
    "company": "Ramada",
    "module": "tcp_connect",
    "instance": "172.16.200.10:1433",
    "name": "sql-principal",
    "tipo_monitoramento": "banco-de-dados",
    "grupo_monitoramento": "servicos-internos",
    "localizacao": "Matriz",
    "fabricante": "Microsoft",
    "tipo": "sql-server",
    "modelo": "SQL 2019",
    "cod_localidade": "PALMAS-MTZ",
    "tipo_dispositivo_abrev": "DB",
    "cidade": "Palmas",
    "notas": "Banco principal do ERP",
    "glpi_url": "",
    "provedor": "Interno",
    "campoextra1": "",
    "campoextra2": "",
    "testeSP": ""
  },
  "Check": {
    "Name": "sql-principal (Consul TCP)",
    "TCP": "172.16.200.10:1433",
    "Interval": "30s",
    "Timeout": "5s",
    "DeregisterCriticalServiceAfter": "90m"
  }
}
```

> O Blackbox pode, por exemplo, diferenciar latência alta/baixa na conexão TCP; o Consul fica com a visão binária "abre ou não abre" a conexão.

**Form Schema (tcp_connect):**

```json
{
  "fields": [
    {
      "name": "tags",
      "label": "Tags",
      "type": "tags",
      "col_span": 10,
      "required": true,
      "default": ["tcp_connect"],
      "placeholder": "Selecione ou digite tags...",
      "help": "Tags do serviço no Consul. A tag 'tcp_connect' é obrigatória."
    },
    {
      "name": "address",
      "label": "Hostname (Address)",
      "type": "text",
      "col_span": 14,
      "required": true,
      "placeholder": "172.16.200.10",
      "help": "Hostname ou IP do alvo. Este campo vai para 'Address' do Consul.",
      "validation": {
        "pattern": "^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$|^(?!^[0-9.]+$)(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\\.)+[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?$",
        "message": "Deve ser um IP válido ou Hostname válido."
      }
    },
    {
      "name": "port",
      "label": "Porta",
      "type": "number",
      "col_span": 6,
      "required": true,
      "placeholder": "1433",
      "help": "Porta TCP a ser testada.",
      "validation": {
        "min": 1,
        "max": 65535,
        "message": "Porta deve estar entre 1 e 65535"
      }
    },
    {
      "name": "instance",
      "label": "Host:Porta (Meta.instance)",
      "type": "text",
      "col_span": 18,
      "required": true,
      "placeholder": "172.16.200.10:1433",
      "help": "Alvo no formato Host:Porta.",
      "validation": {
        "pattern": "^(?:(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)|^(?!^[0-9.]+$)(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\\.)+[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?):[0-9]{1,5}$",
        "message": "Formato inválido. Use hostname:porta"
      }
    },
    {
      "name": "enable_check",
      "label": "Ativar Check do Consul",
      "type": "checkbox",
      "col_span": 24,
      "required": false,
      "default": true,
      "help": "Se ativado, o Consul fará um check de saúde TCP."
    },
    {
      "name": "check_TCP",
      "label": "Check TCP (hostname:porta)",
      "type": "text",
      "col_span": 24,
      "required": false,
      "placeholder": "172.16.200.10:1433",
      "help": "Endereço e porta para check TCP.",
      "depends_on": "enable_check",
      "validation": {
        "pattern": "^(?:(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)|^(?!^[0-9.]+$)(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\\.)+[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?):[0-9]{1,5}$",
        "message": "Formato inválido. Use hostname:porta"
      }
    },
    {
      "name": "check_Interval",
      "label": "Intervalo",
      "type": "text",
      "col_span": 8,
      "required": false,
      "default": "30s",
      "placeholder": "30s",
      "help": "Intervalo entre checks.",
      "depends_on": "enable_check"
    },
    {
      "name": "check_Timeout",
      "label": "Timeout",
      "type": "text",
      "col_span": 8,
      "required": false,
      "default": "5s",
      "placeholder": "5s",
      "help": "Timeout do check.",
      "depends_on": "enable_check"
    },
    {
      "name": "check_Name",
      "label": "Nome do Check",
      "type": "text",
      "col_span": 8,
      "required": false,
      "placeholder": "tcp_connect {name}",
      "help": "Nome descritivo do check.",
      "depends_on": "enable_check"
    },
    {
      "name": "check_DeregisterCriticalServiceAfter",
      "label": "Desregistrar Após",
      "type": "text",
      "col_span": 24,
      "required": false,
      "default": "96h",
      "placeholder": "96h",
      "help": "Tempo para desregistrar serviço crítico.",
      "depends_on": "enable_check"
    }
  ],
  "required_metadata": ["tags", "address", "instance", "port"],
  "optional_metadata": ["enable_check", "check_TCP", "check_Interval", "check_Timeout", "check_Name", "check_DeregisterCriticalServiceAfter"]
}
```

---

### 3.9. `ssh_banner` – validação de SSH (banner)

O módulo `ssh_banner` do Blackbox faz um handshake simples de TCP/SSH para garantir que o serviço devolve um banner começando com `SSH-2.0-`.

No Consul, o check nativo continua sendo apenas TCP na porta 22 – toda a inteligência de validar o banner fica no Blackbox.

```json
{
  "ID": "ssh_banner/SkillsIT/Servidores/Core@datacenter-palmas",
  "Name": "blackbox_exporter",
  "Tags": [
    "ssh_banner"
  ],
  "Address": "172.16.1.50",
  "Port": 22,
  "Meta": {
    "company": "Skills IT",
    "module": "ssh_banner",
    "instance": "172.16.1.50:22",
    "name": "datacenter-palmas",
    "tipo_monitoramento": "ssh",
    "grupo_monitoramento": "infra-core",
    "localizacao": "Datacenter-Palmas",
    "fabricante": "Dell",
    "tipo": "servidor",
    "modelo": "PowerEdge",
    "cod_localidade": "PALMAS-DC",
    "tipo_dispositivo_abrev": "SRV",
    "cidade": "Palmas",
    "notas": "Servidor core de infraestrutura",
    "glpi_url": "",
    "provedor": "Interno",
    "campoextra1": "",
    "campoextra2": "",
    "testeSP": ""
  },
  "Check": {
    "Name": "datacenter-palmas (Consul TCP SSH)",
    "TCP": "172.16.1.50:22",
    "Interval": "30s",
    "Timeout": "5s",
    "DeregisterCriticalServiceAfter": "90m"
  }
}
```

> Assim você tem nos dashboards: métricas detalhadas do Blackbox sobre SSH, e no Consul um health check simples para visualização rápida e automações.

**Form Schema (ssh_banner):**

```json
{
  "fields": [
    {
      "name": "tags",
      "label": "Tags",
      "type": "tags",
      "col_span": 10,
      "required": true,
      "default": ["ssh_banner"],
      "placeholder": "Selecione ou digite tags...",
      "help": "Tags do serviço no Consul. A tag 'ssh_banner' é obrigatória."
    },
    {
      "name": "address",
      "label": "Hostname (Address)",
      "type": "text",
      "col_span": 14,
      "required": true,
      "placeholder": "172.16.1.50",
      "help": "Hostname ou IP do alvo.",
      "validation": {
        "pattern": "^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$|^(?!^[0-9.]+$)(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\\.)+[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?$",
        "message": "Deve ser um IP válido ou Hostname válido."
      }
    },
    {
      "name": "port",
      "label": "Porta",
      "type": "number",
      "col_span": 6,
      "required": true,
      "default": 22,
      "placeholder": "22",
      "help": "Porta SSH (22).",
      "validation": {
        "min": 1,
        "max": 65535,
        "message": "Porta deve estar entre 1 e 65535"
      }
    },
    {
      "name": "instance",
      "label": "Host:Porta (Meta.instance)",
      "type": "text",
      "col_span": 18,
      "required": true,
      "placeholder": "172.16.1.50:22",
      "help": "Alvo no formato Host:Porta.",
      "validation": {
        "pattern": "^(?:(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)|^(?!^[0-9.]+$)(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\\.)+[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?):[0-9]{1,5}$",
        "message": "Formato inválido. Use hostname:porta"
      }
    },
    {
      "name": "enable_check",
      "label": "Ativar Check do Consul",
      "type": "checkbox",
      "col_span": 24,
      "required": false,
      "default": true,
      "help": "Se ativado, o Consul fará um check de saúde TCP."
    },
    {
      "name": "check_TCP",
      "label": "Check TCP (hostname:porta)",
      "type": "text",
      "col_span": 24,
      "required": false,
      "placeholder": "172.16.1.50:22",
      "help": "Endereço e porta para check TCP.",
      "depends_on": "enable_check",
      "validation": {
        "pattern": "^(?:(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)|^(?!^[0-9.]+$)(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\\.)+[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?):[0-9]{1,5}$",
        "message": "Formato inválido. Use hostname:porta"
      }
    },
    {
      "name": "check_Interval",
      "label": "Intervalo",
      "type": "text",
      "col_span": 8,
      "required": false,
      "default": "30s",
      "placeholder": "30s",
      "help": "Intervalo entre checks.",
      "depends_on": "enable_check"
    },
    {
      "name": "check_Timeout",
      "label": "Timeout",
      "type": "text",
      "col_span": 8,
      "required": false,
      "default": "5s",
      "placeholder": "5s",
      "help": "Timeout do check.",
      "depends_on": "enable_check"
    },
    {
      "name": "check_Name",
      "label": "Nome do Check",
      "type": "text",
      "col_span": 8,
      "required": false,
      "placeholder": "ssh_banner {name}",
      "help": "Nome descritivo do check.",
      "depends_on": "enable_check"
    },
    {
      "name": "check_DeregisterCriticalServiceAfter",
      "label": "Desregistrar Após",
      "type": "text",
      "col_span": 24,
      "required": false,
      "default": "96h",
      "placeholder": "96h",
      "help": "Tempo para desregistrar serviço crítico.",
      "depends_on": "enable_check"
    }
  ],
  "required_metadata": ["tags", "address", "instance", "port"],
  "optional_metadata": ["enable_check", "check_TCP", "check_Interval", "check_Timeout", "check_Name", "check_DeregisterCriticalServiceAfter"]
}
```

---

### 3.10. `dns` – disponibilidade de serviço DNS (UDP 53)

Para um módulo `dns` no Blackbox (que realiza queries DNS reais – A, MX, etc.), o Consul pode complementar testando apenas se há algo respondendo em UDP 53.

Exemplo de registro para um DNS interno:

```json
{
  "ID": "dns/Ramada/DNS/Infra@dns-interno-palmas",
  "Name": "blackbox_exporter",
  "Tags": [
    "dns"
  ],
  "Address": "172.16.1.175",
  "Port": 53,
  "Meta": {
    "company": "Ramada",
    "module": "dns",
    "instance": "172.16.1.175",
    "name": "dns-interno-palmas",
    "tipo_monitoramento": "dns",
    "grupo_monitoramento": "infra-dns",
    "localizacao": "Matriz",
    "fabricante": "Microsoft",
    "tipo": "dns",
    "modelo": "Windows DNS",
    "cod_localidade": "PALMAS-MTZ",
    "tipo_dispositivo_abrev": "DNS",
    "cidade": "Palmas",
    "notas": "Servidor DNS interno principal",
    "glpi_url": "",
    "provedor": "Interno",
    "campoextra1": "",
    "campoextra2": "",
    "testeSP": ""
  },
  "Check": {
    "Name": "dns-interno-palmas (Consul UDP 53)",
    "UDP": "172.16.1.175:53",
    "Interval": "30s",
    "Timeout": "1s",
    "DeregisterCriticalServiceAfter": "90m"
  }
}
```

> O Blackbox faz queries DNS completas para confirmar resolução de nomes. O Consul só garante que o serviço está ouvindo na porta 53/UDP a partir daquele node.

**Form Schema (dns):**

```json
{
  "fields": [
    {
      "name": "tags",
      "label": "Tags",
      "type": "tags",
      "col_span": 10,
      "required": true,
      "default": ["dns"],
      "placeholder": "Selecione ou digite tags...",
      "help": "Tags do serviço no Consul. A tag 'dns' é obrigatória."
    },
    {
      "name": "address",
      "label": "Hostname (Address)",
      "type": "text",
      "col_span": 14,
      "required": true,
      "placeholder": "172.16.1.175",
      "help": "Hostname ou IP do servidor DNS.",
      "validation": {
        "pattern": "^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$|^(?!^[0-9.]+$)(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\\.)+[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?$",
        "message": "Deve ser um IP válido ou Hostname válido."
      }
    },
    {
      "name": "port",
      "label": "Porta",
      "type": "number",
      "col_span": 6,
      "required": true,
      "default": 53,
      "placeholder": "53",
      "help": "Porta DNS (53).",
      "validation": {
        "min": 1,
        "max": 65535,
        "message": "Porta deve estar entre 1 e 65535"
      }
    },
    {
      "name": "instance",
      "label": "IP ou Hostname (Meta.instance)",
      "type": "text",
      "col_span": 18,
      "required": true,
      "placeholder": "172.16.1.175",
      "help": "Alvo DNS (IP ou Hostname). O Blackbox usa porta 53 por padrão.",
      "validation": {
        "pattern": "^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$|^(?!^[0-9.]+$)(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\\.)+[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?$",
        "message": "Deve ser um IP válido ou Hostname válido."
      }
    },
    {
      "name": "enable_check",
      "label": "Ativar Check do Consul",
      "type": "checkbox",
      "col_span": 24,
      "required": false,
      "default": true,
      "help": "Se ativado, o Consul fará um check UDP na porta 53."
    },
    {
      "name": "check_UDP",
      "label": "Check UDP (hostname:porta)",
      "type": "text",
      "col_span": 24,
      "required": false,
      "placeholder": "172.16.1.175:53",
      "help": "Endereço e porta para check UDP.",
      "depends_on": "enable_check",
      "validation": {
        "pattern": "^(?:(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)|^(?!^[0-9.]+$)(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\\.)+[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?):[0-9]{1,5}$",
        "message": "Formato inválido. Use hostname:porta"
      }
    },
    {
      "name": "check_Interval",
      "label": "Intervalo",
      "type": "text",
      "col_span": 8,
      "required": false,
      "default": "30s",
      "placeholder": "30s",
      "help": "Intervalo entre checks.",
      "depends_on": "enable_check"
    },
    {
      "name": "check_Timeout",
      "label": "Timeout",
      "type": "text",
      "col_span": 8,
      "required": false,
      "default": "1s",
      "placeholder": "1s",
      "help": "Timeout do check UDP (recomendado curto para UDP).",
      "depends_on": "enable_check"
    },
    {
      "name": "check_Name",
      "label": "Nome do Check",
      "type": "text",
      "col_span": 8,
      "required": false,
      "placeholder": "dns {name} (Consul UDP)",
      "help": "Nome descritivo do check.",
      "depends_on": "enable_check"
    },
    {
      "name": "check_DeregisterCriticalServiceAfter",
      "label": "Desregistrar Após",
      "type": "text",
      "col_span": 24,
      "required": false,
      "default": "96h",
      "placeholder": "96h",
      "help": "Tempo para desregistrar serviço crítico.",
      "depends_on": "enable_check"
    }
  ],
  "required_metadata": ["tags", "address", "instance", "port"],
  "optional_metadata": ["enable_check", "check_UDP", "check_Interval", "check_Timeout", "check_Name", "check_DeregisterCriticalServiceAfter"]
}
```
