# Regras de Categorização - Guia do Usuário

## Visão Geral

A página **Regras de Categorização** (`/settings/monitoring-rules`) permite gerenciar as regras que determinam como os tipos de monitoramento são categorizados automaticamente. Essas regras são a **fonte única de verdade** para categorização de jobs do Prometheus.

---

## Acessando a Página

1. Navegue até **Configurações** no menu lateral
2. Clique em **Regras de Monitoramento**
3. URL direta: `http://localhost:8081/settings/monitoring-rules`

---

## Funcionalidades Principais

### 1. Visualizar Regras

A tabela principal exibe todas as regras com as seguintes informações:

| Coluna | Descrição |
|--------|-----------|
| **ID** | Identificador único da regra (ex: `blackbox_icmp`) |
| **Prioridade** | Valor de 1-100 (maior = aplicada primeiro) |
| **Categoria** | Categoria de destino (ex: Network Probes) |
| **Display Name** | Nome amigável para exibição |
| **Exporter Type** | Tipo de exporter (blackbox, node, mysql, etc) |
| **Ações** | Editar, Duplicar, Excluir |

### 2. Ordenação e Filtros

**Ordenação:**
- Clique no cabeçalho de qualquer coluna para ordenar
- Por padrão, ordenado por **Prioridade** (decrescente)

**Filtros:**
- Use os filtros de coluna para filtrar por:
  - Categoria
  - Display Name
  - Exporter Type
- Botão **Limpar Filtros** para remover todos os filtros

### 3. Criar Nova Regra

1. Clique no botão **Nova Regra**
2. Preencha os campos obrigatórios:
   - **ID**: Identificador único (ex: `blackbox_https_custom`)
   - **Prioridade**: Valor de 1 a 100
   - **Categoria**: Selecione uma categoria existente
   - **Display Name**: Nome amigável para exibição
3. Configure as condições de match:
   - **Job Name Pattern**: Regex para nome do job
   - **Metrics Path**: Caminho de métricas (`/probe` ou `/metrics`)
   - **Module Pattern**: Regex para módulo (opcional)
4. Use o **Testador de Regex** para validar os patterns
5. Clique em **Salvar**

### 4. Editar Regra Existente

1. Clique no ícone de **lápis** na linha da regra
2. Modifique os campos desejados
3. Use o **Testador de Regex** para validar alterações
4. Clique em **Salvar**

### 5. Duplicar Regra

Útil para criar regras similares:

1. Clique no ícone de **cópia** na linha da regra
2. O modal abre com dados pré-preenchidos
3. Altere o **ID** (obrigatório - deve ser único)
4. Modifique outros campos conforme necessário
5. Clique em **Salvar**

### 6. Excluir Regra

1. Clique no ícone de **lixeira** na linha da regra
2. Confirme a exclusão no popup

---

## Testador de Regex

O modal de edição inclui um **Testador de Regex em tempo real** para cada campo de pattern:

### Como Usar

1. Preencha o campo de pattern (ex: `^http.*2xx.*`)
2. No **Testador de Regex** abaixo do campo:
   - Digite um valor de teste (ex: `http_2xx_check`)
   - Clique em **Testar**
3. O resultado mostra:
   - **Match Confirmado** (verde): O valor corresponde ao pattern
   - **Nenhum Match** (amarelo): O valor não corresponde

### Exemplos de Patterns

| Pattern | Descrição | Exemplos que fazem match |
|---------|-----------|-------------------------|
| `^icmp.*` | Começa com "icmp" | icmp, icmp_check, icmp_v4 |
| `^http.*2xx.*` | HTTP com 2xx | http_2xx, http_2xx_check |
| `^node.*exporter.*` | Node Exporter | node_exporter, node_exporter_v2 |
| `^(mysql\|postgres).*` | MySQL ou PostgreSQL | mysql_exporter, postgres_exporter |

---

## Sistema de Prioridades

As regras são aplicadas em ordem de **prioridade decrescente** (maior primeiro):

| Prioridade | Uso Recomendado | Cor |
|------------|-----------------|-----|
| 100 | Blackbox/Probes específicos | Vermelho |
| 90 | Muito Alta | Laranja escuro |
| 80 | Exporters padrão | Laranja |
| 70 | Média-Alta | Dourado |
| 60 | Média | Verde claro |
| 50 | Baixa | Verde |

**Importante**: Se duas regras podem fazer match no mesmo job, a regra com **maior prioridade** é aplicada.

---

## Categorias Disponíveis

| ID | Display Name | Cor |
|----|-------------|-----|
| network-probes | Network Probes (Rede) | Roxo |
| web-probes | Web Probes (Aplicações) | Ciano |
| system-exporters | Exporters: Sistemas | Verde |
| database-exporters | Exporters: Bancos de Dados | Magenta |
| infrastructure-exporters | Exporters: Infraestrutura | Azul |
| hardware-exporters | Exporters: Hardware | Laranja |
| network-devices | Dispositivos de Rede | Dourado |
| custom-exporters | Exporters Customizados | Cinza |

---

## Boas Práticas

### 1. Nomeação de IDs

- Use prefixo descritivo: `blackbox_`, `exporter_`, `custom_`
- Use snake_case: `blackbox_http_2xx`
- Seja específico: `blackbox_icmp_remote` em vez de `icmp`

### 2. Prioridades

- **100**: Reserve para casos muito específicos (ex: ICMP remoto)
- **80-90**: Exporters e probes padrão
- **50-70**: Regras genéricas

### 3. Patterns de Regex

- Sempre use `^` para ancorar no início
- Teste o pattern antes de salvar
- Use grupos para alternativas: `^(icmp|ping).*`

### 4. Manutenção

- Revise regras periodicamente
- Remova regras não utilizadas
- Documente o propósito em **Observações**

---

## Troubleshooting

### Regra não está fazendo match

1. Verifique a **prioridade** - outra regra pode estar sendo aplicada primeiro
2. Use o **Testador de Regex** para validar o pattern
3. Confirme que o **metrics_path** está correto (`/probe` vs `/metrics`)

### Job indo para categoria errada

1. Verifique as prioridades das regras
2. Confirme que não há regex conflitante
3. Teste o job_name no **Testador de Regex** de cada regra suspeita

### Regex inválido

- O sistema valida regex em tempo real
- Erros são exibidos abaixo do campo
- Use o **Testador de Regex** para depurar

---

## Atalhos e Dicas

- **Recarregar**: Clique no ícone de refresh no canto superior direito
- **Ordenação rápida**: Clique no cabeçalho da coluna
- **Filtros múltiplos**: Combine filtros de diferentes colunas
- **Limpar tudo**: Use "Limpar Filtros e Ordenação"

---

## Próximos Passos

Após configurar as regras:

1. Execute um **Force Refresh** na página de [Tipos de Monitoramento](/monitoring-types)
2. Verifique se os tipos foram categorizados corretamente
3. Ajuste as regras conforme necessário

---

**Versão**: 2.0.0
**Última atualização**: 2025-11-21
**Autor**: Sistema Skills Eye
