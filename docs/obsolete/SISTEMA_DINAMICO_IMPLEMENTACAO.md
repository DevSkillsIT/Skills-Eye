# 🚀 Sistema Totalmente Dinâmico - Implementação Completa

## ✅ O QUE FOI IMPLEMENTADO (Backend)

### 1. Estrutura do metadata_fields.json Expandida ✅

**Arquivo**: `backend/config/metadata_fields.json`

Novas propriedades adicionadas a CADA campo:
```json
{
  "name": "company",
  "enabled": true,                      // Campo ativo no sistema
  "show_in_filter": true,               // Aparece na barra de filtros
  "show_in_blackbox": true,             // Aparece em Blackbox Targets
  "show_in_exporters": true,            // Aparece em Exporters
  "show_in_services": true,             // Aparece em Services
  "available_for_registration": true,   // Permite cadastrar novos valores
  "placeholder": "Selecione empresa",
  "default_value": null,
  "validation": {
    "required_message": "Informe a empresa"
  }
}
```

### 2. MetadataLoader - Fonte Única da Verdade ✅

**Arquivo**: `backend/core/metadata_loader.py`

Funções principais:
```python
from core.metadata_loader import metadata_loader

# Buscar todos os campos
fields = metadata_loader.get_all_fields()

# Buscar com filtros
blackbox_fields = metadata_loader.get_fields(
    enabled=True,
    show_in_blackbox=True,
    show_in_form=True
)

# Buscar apenas nomes (mais leve)
required_fields = metadata_loader.get_required_fields()
filter_fields = metadata_loader.get_field_names(show_in_filter=True)

# Validar metadata
result = metadata_loader.validate_metadata(
    {'company': 'ACME', 'name': 'test'},
    context='blackbox'
)
# Returns: {'valid': False, 'errors': [...], 'warnings': [...]}
```

### 3. Config.py Refatorado ✅

**Arquivo**: `backend/core/config.py`

Antes (hardcoded):
```python
META_FIELDS = ['company', 'env', 'project', ...]
REQUIRED_FIELDS = ['company', 'env', ...]
```

Depois (dinâmico):
```python
Config.get_meta_fields()      # Retorna do JSON
Config.get_required_fields()  # Retorna do JSON
```

### 4. FieldsExtractionService Refatorado ✅

**Arquivo**: `backend/core/fields_extraction_service.py`

Agora usa properties dinâmicas:
```python
service = FieldsExtractionService()
service.REQUIRED_FIELDS     # Carrega dinamicamente
service.DASHBOARD_FIELDS    # Carrega dinamicamente
```

### 5. Novo Endpoint API /metadata-dynamic ✅

**Arquivo**: `backend/api/metadata_dynamic.py`

Endpoints disponíveis:
```bash
# Buscar todos os campos (com filtros)
GET /api/v1/metadata-dynamic/fields?context=blackbox
GET /api/v1/metadata-dynamic/fields?context=exporters&show_in_form=true
GET /api/v1/metadata-dynamic/fields?show_in_filter=true

# Buscar apenas nomes (mais leve)
GET /api/v1/metadata-dynamic/fields/names?context=blackbox

# Buscar campos obrigatórios
GET /api/v1/metadata-dynamic/fields/required

# Recarregar cache
POST /api/v1/metadata-dynamic/reload

# Validar metadata
POST /api/v1/metadata-dynamic/validate
```

---

## 🔄 O QUE FALTA FAZER (Frontend)

### 1. Criar Serviço API no Frontend

**Arquivo a criar/editar**: `frontend/src/services/api.ts`

```typescript
// Adicionar novos métodos:

export const metadataDynamicAPI = {
  // Buscar campos dinâmicos
  getFields: (params?: {
    context?: 'blackbox' | 'exporters' | 'services';
    enabled?: boolean;
    required?: boolean;
    show_in_table?: boolean;
    show_in_form?: boolean;
    show_in_filter?: boolean;
    category?: string;
  }) => api.get('/metadata-dynamic/fields', { params }),

  // Buscar apenas nomes
  getFieldNames: (params?: {
    context?: string;
    enabled?: boolean;
    required?: boolean;
  }) => api.get('/metadata-dynamic/fields/names', { params }),

  // Buscar campos obrigatórios
  getRequiredFields: () => api.get('/metadata-dynamic/fields/required'),

  // Recarregar cache
  reloadCache: () => api.post('/metadata-dynamic/reload'),

  // Validar metadata
  validateMetadata: (metadata: any, context: string = 'general') =>
    api.post('/metadata-dynamic/validate', metadata, { params: { context } }),
};
```

### 2. Criar Hook React para Campos Dinâmicos

**Arquivo a criar**: `frontend/src/hooks/useMetadataFields.ts`

```typescript
import { useState, useEffect } from 'react';
import { metadataDynamicAPI } from '../services/api';

export interface MetadataField {
  name: string;
  display_name: string;
  description: string;
  field_type: string;
  required: boolean;
  enabled: boolean;
  show_in_table: boolean;
  show_in_dashboard: boolean;
  show_in_form: boolean;
  show_in_filter: boolean;
  show_in_blackbox: boolean;
  show_in_exporters: boolean;
  show_in_services: boolean;
  editable: boolean;
  available_for_registration: boolean;
  options: string[];
  default_value: any;
  placeholder: string;
  order: number;
  category: string;
  validation: any;
}

export function useMetadataFields(context?: string) {
  const [fields, setFields] = useState<MetadataField[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchFields() {
      try {
        setLoading(true);
        const { data } = await metadataDynamicAPI.getFields({ context });
        setFields(data.fields);
        setError(null);
      } catch (err: any) {
        setError(err.message);
        console.error('Erro ao carregar campos:', err);
      } finally {
        setLoading(false);
      }
    }

    fetchFields();
  }, [context]);

  return { fields, loading, error };
}
```

### 3. Refatorar Services.tsx (EXEMPLO COMPLETO)

**Antes** (hardcoded):
```typescript
const DEFAULT_COLUMNS = [
  { key: 'company', title: 'Empresa', visible: true },
  { key: 'project', title: 'Projeto', visible: true },
  { key: 'env', title: 'Ambiente', visible: true },
  ...
];
```

**Depois** (dinâmico):
```typescript
import { useMetadataFields } from '../hooks/useMetadataFields';

function Services() {
  const { fields, loading } = useMetadataFields('services');

  // Gerar colunas dinamicamente
  const columns = useMemo(() => {
    return fields
      .filter(f => f.enabled && f.show_in_table && f.show_in_services)
      .sort((a, b) => a.order - b.order)
      .map(f => ({
        key: f.name,
        title: f.display_name,
        dataIndex: ['meta', f.name],
        width: 200,
        ellipsis: true,
      }));
  }, [fields]);

  // Gerar campos de formulário dinamicamente
  const formFields = useMemo(() => {
    return fields
      .filter(f => f.enabled && f.show_in_form && f.show_in_services)
      .sort((a, b) => a.order - b.order)
      .map(f => (
        <ProFormText
          key={f.name}
          name={f.name}
          label={f.display_name}
          placeholder={f.placeholder}
          rules={[
            {
              required: f.required,
              message: f.validation?.required_message || `Informe ${f.display_name.toLowerCase()}`
            }
          ]}
        />
      ));
  }, [fields]);

  // Gerar filtros dinamicamente
  const filterFields = useMemo(() => {
    return fields.filter(f => f.enabled && f.show_in_filter && f.show_in_services);
  }, [fields]);

  return (
    <div>
      {/* MetadataFilterBar agora é dinâmico */}
      <MetadataFilterBar fields={filterFields} onChange={handleFilter} />

      {/* ProTable com colunas dinâmicas */}
      <ProTable columns={columns} ... />

      {/* Modal com campos dinâmicos */}
      <ModalForm>
        {formFields}
      </ModalForm>
    </div>
  );
}
```

### 4. Refatorar BlackboxTargets.tsx

Similar ao Services.tsx:
- Usar `useMetadataFields('blackbox')`
- Gerar colunas dinamicamente
- Gerar formulários dinamicamente

### 5. Refatorar Exporters.tsx

Similar, mas com `useMetadataFields('exporters')`.

### 6. Refatorar MetadataFilterBar.tsx

**Antes** (hardcoded):
```typescript
<Select placeholder="Projeto" ... />
<Select placeholder="Ambiente" ... />
```

**Depois** (dinâmico):
```typescript
interface MetadataFilterBarProps {
  fields: MetadataField[];  // Campos passados pelo componente pai
  onChange: (key: string, value: any) => void;
}

function MetadataFilterBar({ fields, onChange }: MetadataFilterBarProps) {
  return (
    <div>
      {fields.map(field => (
        <Select
          key={field.name}
          placeholder={field.placeholder}
          onChange={(val) => onChange(field.name, val)}
        >
          {field.options?.map(opt => (
            <Option key={opt} value={opt}>{opt}</Option>
          ))}
        </Select>
      ))}
    </div>
  );
}
```

---

## 📊 FLUXO COMPLETO

```
┌─────────────────────────────────────────────────────────┐
│  1. Administrador acessa MetadataFields                 │
│     Edita campo "env" → renomeia para "tipo_monitoring" │
│     Salva → atualiza metadata_fields.json               │
└────────────────┬────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────┐
│  2. Backend                                             │
│     metadata_loader detecta mudança (ou recarrega)      │
│     Config.get_meta_fields() retorna novos nomes        │
│     FieldsExtractionService usa novos nomes             │
└────────────────┬────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────┐
│  3. Frontend faz requisição                             │
│     GET /api/v1/metadata-dynamic/fields?context=services│
└────────────────┬────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────┐
│  4. Frontend recebe campos atualizados                  │
│     useMetadataFields('services') retorna novos campos  │
│     Colunas, formulários, filtros atualizam AUTOMATICAMENTE
└─────────────────────────────────────────────────────────┘
```

**Resultado**: ZERO edições de código necessárias!

---

## 🎯 PRÓXIMOS PASSOS (Ordem de Prioridade)

1. ✅ **Backend completado** - Sistema totalmente dinâmico
2. ⏳ **Criar serviço API** em `frontend/src/services/api.ts`
3. ⏳ **Criar hook** `useMetadataFields.ts`
4. ⏳ **Refatorar Services.tsx** (exemplo completo)
5. ⏳ **Refatorar BlackboxTargets.tsx**
6. ⏳ **Refatorar Exporters.tsx**
7. ⏳ **Refatorar MetadataFilterBar.tsx**
8. ⏳ **Testar sistema completo**
9. ⏳ **Remover código hardcoded antigo**
10. ⏳ **Documentar para o usuário**

---

## 🧪 TESTES REALIZADOS

```bash
# Teste 1: Campos obrigatórios
GET /api/v1/metadata-dynamic/fields/required
✅ Retorna: ['instance', 'company', 'tipo_monitoramento', 'name', 'grupo_monitoramento']

# Teste 2: Campos para filtros
GET /api/v1/metadata-dynamic/fields?show_in_filter=true
✅ Retorna: 5 campos (vendor, instance, company, tipo_monitoramento, grupo_monitoramento)

# Teste 3: Campos para blackbox
GET /api/v1/metadata-dynamic/fields?context=blackbox
✅ Retorna: 19 campos com show_in_blackbox=true

# Teste 4: Campos para exporters com formulário
GET /api/v1/metadata-dynamic/fields?context=exporters&show_in_form=true
✅ Retorna: 19 campos filtrados para exporters
```

---

## 📝 NOTAS IMPORTANTES

1. **PrometheusConfig continua como está** - Já é dinâmico via SSH
2. **Backward compatibility** - Config.META_FIELDS ainda funciona via property
3. **Cache inteligente** - metadata_loader tem cache de 60s
4. **Reload sob demanda** - POST /metadata-dynamic/reload limpa cache
5. **Validação** - metadata_loader valida metadata automaticamente

---

## 🎓 EXEMPLO DE USO COMPLETO

### Cenário: Adicionar novo campo "criticidade"

**Passo 1**: Administrador acessa MetadataFields, adiciona campo:
```json
{
  "name": "criticidade",
  "display_name": "Criticidade",
  "field_type": "select",
  "required": false,
  "enabled": true,
  "show_in_blackbox": true,
  "show_in_exporters": true,
  "show_in_services": true,
  "show_in_form": true,
  "show_in_table": true,
  "show_in_filter": true,
  "options": ["baixa", "media", "alta", "critica"],
  "order": 15
}
```

**Passo 2**: Salvar → metadata_fields.json atualizado

**Passo 3**: Frontend recarrega (ou faz nova requisição)

**Resultado**:
- ✅ Campo aparece em TODAS as tabelas
- ✅ Campo aparece em TODOS os formulários
- ✅ Campo aparece na barra de filtros
- ✅ Select com 4 opções criado automaticamente
- ✅ ZERO código alterado!

---

## 🚀 BENEFÍCIOS

1. **Manutenção Zero** - Adicionar/remover campos sem tocar em código
2. **Consistência** - Um campo, uma definição
3. **Flexibilidade** - Controle granular de onde cada campo aparece
4. **Performance** - Cache inteligente evita reads desnecessários
5. **Validação** - Validação centralizada e reutilizável
6. **Escalabilidade** - Adicionar 100 campos não aumenta complexidade

---

## ⚠️ ATENÇÃO

Após refatorar o frontend, **REMOVER**:
- Todas as listas DEFAULT_COLUMNS hardcoded
- Todos os campos em MetadataFilterBar hardcoded
- Todas as referências a 'env', 'project' (já renomeados para tipo_monitoramento, grupo_monitoramento)

Manter apenas:
- useMetadataFields(context)
- Geração dinâmica de colunas/forms/filtros
