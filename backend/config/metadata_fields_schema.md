# Metadata Fields Schema - Sistema Dinâmico Completo

## Estrutura de Cada Campo

```json
{
  "name": "company",              // Identificador único (usado em código)
  "display_name": "Empresa",       // Nome exibido na UI
  "description": "...",            // Tooltip/help text
  "source_label": "__meta_consul_service_metadata_company", // Label do Prometheus
  "field_type": "string|select|number|boolean",  // Tipo do campo

  // CONTROLES DE OBRIGATORIEDADE
  "required": true,                // Campo obrigatório em cadastros

  // CONTROLES DE VISIBILIDADE (onde aparece)
  "enabled": true,                 // Campo ativo no sistema
  "show_in_table": true,           // Aparece em colunas de tabelas
  "show_in_dashboard": true,       // Aparece no dashboard principal
  "show_in_form": true,            // Aparece em formulários de cadastro
  "show_in_filter": true,          // Aparece na barra de filtros

  // CONTROLES POR TIPO DE EXPORTER/SERVIÇO
  "show_in_blackbox": true,        // Aparece em Blackbox Targets (ICMP, HTTP, etc)
  "show_in_exporters": true,       // Aparece em Exporters (Node, Windows)
  "show_in_services": true,        // Aparece em Services gerais

  // CONTROLES DE EDIÇÃO
  "editable": true,                // Pode ser editado após criação
  "available_for_registration": true,  // Usuário pode cadastrar novos valores

  // METADADOS
  "options": ["prod", "dev"],      // Opções pré-definidas (para select)
  "default_value": "prod",         // Valor padrão
  "placeholder": "Selecione...",   // Placeholder do input
  "order": 10,                     // Ordem de exibição
  "category": "basic|infrastructure|location|business|technical",
  "validation": {                  // Regras de validação
    "min_length": 3,
    "max_length": 100,
    "regex": "^[a-zA-Z0-9-_]+$"
  }
}
```

## Categorias

- `basic`: Campos básicos obrigatórios (company, name, instance)
- `infrastructure`: Infra (vendor, region, account)
- `location`: Localização (cidade, cod_localidade)
- `business`: Negócio (project, env, grupo)
- `technical`: Técnicos (tipo, modelo, fabricante)

## Comportamento Dinâmico

### Backend
```python
# Ao invés de:
REQUIRED_FIELDS = ['company', 'env', ...]

# Agora:
required_fields = get_fields(required=True)
blackbox_fields = get_fields(show_in_blackbox=True)
filter_fields = get_fields(show_in_filter=True)
```

### Frontend
```typescript
// Ao invés de:
const columns = [
  { key: 'company', title: 'Empresa' },
  ...
]

// Agora:
const fields = await api.getMetadataFields();
const columns = fields
  .filter(f => f.show_in_table && f.show_in_blackbox)
  .map(f => ({ key: f.name, title: f.display_name }));
```

## Fluxo de Uso

1. **Administrador** acessa página MetadataFields
2. **Edita campo** "env" → renomeia para "tipo_monitoramento"
3. **Salva** → atualiza metadata_fields.json
4. **Backend** recarrega JSON automaticamente
5. **Frontend** busca campos atualizados da API
6. **TODAS as páginas** refletem a mudança AUTOMATICAMENTE
7. **Zero edições** de código necessárias!

## Exemplo Prático

```json
{
  "name": "tipo_monitoramento",
  "display_name": "Tipo Monitoramento",
  "description": "Tipo de monitoramento (ambiente de execução)",
  "source_label": "__meta_consul_service_metadata_tipo_monitoramento",
  "field_type": "select",
  "required": true,
  "enabled": true,
  "show_in_table": true,
  "show_in_dashboard": true,
  "show_in_form": true,
  "show_in_filter": true,
  "show_in_blackbox": true,
  "show_in_exporters": true,
  "show_in_services": true,
  "editable": true,
  "available_for_registration": false,
  "options": ["prod", "hml", "dev", "test", "staging"],
  "default_value": "prod",
  "placeholder": "Selecione o tipo de monitoramento",
  "order": 10,
  "category": "basic",
  "validation": {
    "required_message": "Informe o tipo de monitoramento"
  }
}
```
