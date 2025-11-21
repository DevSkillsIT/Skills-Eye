# Tipos de Monitoramento - Guia do Usuário

## Visão Geral

A página **Tipos de Monitoramento** (`/monitoring-types`) exibe todos os tipos de monitoramento extraídos dinamicamente dos arquivos `prometheus.yml` dos seus servidores. Esta é a visualização principal de todos os jobs de monitoramento configurados no seu ambiente.

---

## Acessando a Página

1. Clique em **Tipos de Monitoramento** no menu lateral
2. URL direta: `http://localhost:8081/monitoring-types`

---

## Interface Principal

### Estatísticas no Topo

A página exibe estatísticas gerais:

- **Total de Tipos**: Quantidade de tipos únicos encontrados
- **Total de Servidores**: Quantidade de servidores analisados
- **Servidores com Sucesso**: Quantos servidores retornaram dados
- **Fonte dos Dados**: Cache ou extração em tempo real

### Modos de Visualização

Escolha entre dois modos usando o seletor:

| Modo | Descrição |
|------|-----------|
| **Todos os Servidores** | Visualiza tipos agregados de todos os servidores |
| **Servidor Específico** | Visualiza tipos de um servidor específico |

---

## Funcionalidades Principais

### 1. Visualização por Categorias

Os tipos são organizados em abas por categoria:

- **Network Probes (Rede)**: ICMP, TCP, DNS
- **Web Probes (Aplicações)**: HTTP, HTTPS
- **Exporters: Sistemas**: Node Exporter, Windows Exporter
- **Exporters: Bancos de Dados**: MySQL, PostgreSQL
- **Exporters: Infraestrutura**: SNMP
- **Exporters: Hardware**: IPMI
- **Dispositivos de Rede**: Switches, Roteadores
- **Exporters Customizados**: Jobs não categorizados

Cada aba mostra a quantidade de tipos entre parênteses.

### 2. Tabela de Tipos

Cada categoria contém uma tabela com as seguintes colunas:

| Coluna | Descrição |
|--------|-----------|
| **Nome** | Display name do tipo |
| **Job Name** | Nome do job no prometheus.yml |
| **Exporter Type** | Tipo de exporter (blackbox, node, etc) |
| **Módulo** | Módulo blackbox (para probes) |
| **Campos Metadata** | Labels extraídos do job |
| **Servidores** | Lista de servidores onde o tipo existe |
| **Ações** | Ver JSON, Form Schema, Job Config |

### 3. Ações por Tipo

Cada linha da tabela tem três botões de ação:

#### Ver JSON
- Exibe o JSON completo do tipo
- Inclui todas as propriedades e configurações
- Útil para debug

#### Editar Form Schema
- Permite configurar o formulário de cadastro para este tipo
- Define campos, tipos, validações
- Personaliza a experiência de criação de monitoramentos

#### Ver Job Config
- Exibe o job original extraído do `prometheus.yml`
- Mostra `scrape_configs`, `relabel_configs`, etc
- Útil para entender a configuração Prometheus

### 4. Seletor de Servidor

Quando no modo "Servidor Específico":

1. Clique no seletor de servidor
2. Escolha o servidor desejado da lista
3. A tabela é atualizada com tipos daquele servidor

### 5. Configuração de Colunas

Personalize quais colunas são exibidas:

1. Clique no ícone de engrenagem no canto superior direito
2. Marque/desmarque as colunas desejadas
3. As alterações são aplicadas imediatamente

### 6. Tamanho da Tabela

Ajuste o espaçamento da tabela:

- **Compacto**: Linhas menores, mais dados na tela
- **Médio**: Espaçamento padrão
- **Grande**: Linhas maiores, mais espaçamento

---

## Force Refresh

### Quando Usar

Use o **Force Refresh** quando:

- Acabou de alterar o `prometheus.yml` de um servidor
- Adicionou novos jobs de monitoramento
- Alterou regras de categorização
- Dados parecem desatualizados

### Como Fazer

1. Clique no botão **Force Refresh** (ícone de raio)
2. Aguarde o modal de progresso
3. O modal mostra:
   - Servidores sendo processados
   - Status de cada servidor (sucesso/falha)
   - Tempo de processamento
   - Quantidade de tipos extraídos

### Modal de Progresso

O modal exibe informações detalhadas:

- **Barra de progresso**: Porcentagem de conclusão
- **Lista de servidores**: Status individual
  - ✅ Sucesso: Dados extraídos com sucesso
  - ❌ Falha: Erro na extração (mostra detalhes)
- **Estatísticas finais**: Total de tipos, servidores, tempo

---

## Edição de Form Schema

### O que é Form Schema

O Form Schema define como o formulário de criação de monitoramento é renderizado. Permite personalizar:

- Campos do formulário
- Tipos de input (texto, select, número)
- Validações (obrigatório, min/max)
- Valores padrão
- Textos de ajuda

### Como Editar

1. Clique no botão **Editar Form Schema** (ícone de edição)
2. O editor Monaco abre com o JSON atual
3. Edite o JSON conforme necessário
4. Clique em **Salvar**

### Exemplo de Form Schema

```json
{
  "fields": [
    {
      "name": "target",
      "label": "Target",
      "type": "text",
      "required": true,
      "placeholder": "Ex: 192.168.1.1",
      "help": "IP ou hostname do alvo"
    },
    {
      "name": "module",
      "label": "Módulo",
      "type": "select",
      "required": true,
      "options": [
        {"value": "icmp", "label": "ICMP (Ping)"},
        {"value": "tcp_connect", "label": "TCP Connect"}
      ]
    },
    {
      "name": "timeout",
      "label": "Timeout (segundos)",
      "type": "number",
      "default": 10,
      "min": 1,
      "max": 60
    }
  ],
  "required_metadata": ["target", "module"],
  "optional_metadata": ["timeout"]
}
```

### Tipos de Campo Suportados

| Tipo | Descrição |
|------|-----------|
| `text` | Campo de texto simples |
| `number` | Campo numérico |
| `select` | Lista de opções |
| `textarea` | Texto multilinha |
| `checkbox` | Caixa de seleção |

---

## Visualização de Campos Metadata

A coluna **Campos Metadata** mostra os labels configurados no job. Estes são os campos que serão solicitados ao criar um monitoramento deste tipo.

Exemplo para ICMP:
- `target`
- `module`

Exemplo para Node Exporter:
- `instance`
- `job`

---

## Dicas de Uso

### 1. Verificar Categorização

Se um tipo está na categoria errada:

1. Verifique as [Regras de Categorização](/settings/monitoring-rules)
2. Ajuste a prioridade ou pattern da regra
3. Execute Force Refresh

### 2. Entender Job Config

Use o botão **Ver Job Config** para:

- Ver a configuração original do Prometheus
- Entender labels e relabel_configs
- Debug de problemas de scraping

### 3. Personalizar Formulários

Use o **Form Schema** para:

- Simplificar a criação de monitoramentos
- Adicionar validações específicas
- Definir valores padrão úteis

### 4. Filtrar por Servidor

Use o modo **Servidor Específico** para:

- Ver tipos de um ambiente específico
- Comparar configurações entre servidores
- Identificar tipos únicos de um servidor

---

## Troubleshooting

### Nenhum tipo aparece

1. Verifique se o servidor Prometheus está acessível
2. Confirme que o arquivo `prometheus.yml` existe
3. Execute Force Refresh para atualizar dados

### Servidor com erro na extração

1. Verifique conectividade SSH com o servidor
2. Confirme credenciais no KV `sites`
3. Verifique logs do backend para detalhes

### Tipo na categoria errada

1. Acesse [Regras de Categorização](/settings/monitoring-rules)
2. Verifique prioridades das regras
3. Ajuste patterns ou crie nova regra
4. Execute Force Refresh

### Form Schema não salva

1. Verifique se o JSON é válido
2. Confirme que não há caracteres especiais
3. Verifique logs do backend

---

## Cache vs Extração

### Cache (Rápido)

- Dados são buscados do Consul KV
- Resposta imediata (~100ms)
- Indicado na interface: "Do Cache"

### Extração (Lento)

- Dados extraídos via SSH do prometheus.yml
- Tempo varia: 5-30s por servidor
- Indicado na interface: "Extração em tempo real"

Use **Force Refresh** apenas quando necessário, pois a extração consome recursos.

---

## Próximos Passos

Após visualizar os tipos:

1. Configure [Form Schemas](#edição-de-form-schema) para tipos frequentes
2. Crie [Regras de Categorização](/settings/monitoring-rules) para tipos customizados
3. Use a página de [Serviços](/monitoring/services) para cadastrar monitoramentos

---

**Versão**: 2.0.0
**Última atualização**: 2025-11-21
**Autor**: Sistema Skills Eye
