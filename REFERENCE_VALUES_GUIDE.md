# 📘 Sistema de Reference Values - Guia Completo

## 🎯 Objetivo

Sistema de auto-cadastro/retroalimentação para campos metadata. Permite que valores digitados em formulários sejam automaticamente cadastrados e fiquem disponíveis para próximos usos.

## 🔑 Conceito Principal: Retroalimentação

### Fluxo Tradicional (SEM auto-cadastro):
1. Administrador precisa cadastrar manualmente todos os valores possíveis
2. Usuário só pode selecionar valores pré-cadastrados
3. **Problema:** Gargalo administrativo, valores não cobertos

### Fluxo com Reference Values (COM auto-cadastro):
1. Usuário digita "Empresa Ramada" ao cadastrar servidor
2. Sistema automaticamente cadastra "Empresa Ramada" no pool de empresas
3. Próximo cadastro: "Empresa Ramada" aparece como opção no select
4. **Vantagem:** Sistema se alimenta automaticamente com uso real

## 📋 Campos Suportados

Campos metadata com `available_for_registration: true` no `metadata_fields.json`:

| Campo | Nome | Exemplo |
|-------|------|---------|
| company | Empresa | "Empresa Ramada", "Acme Corp" |
| grupo_monitoramento | Grupo Monitoramento | "Infraestrutura", "Aplicações" |
| localizacao | Localização | "Datacenter SP", "AWS us-east-1" |
| tipo | Tipo | "Servidor Web", "Database" |
| modelo | Modelo | "Dell PowerEdge R740", "HP ProLiant" |
| cod_localidade | Código da Localidade | "DC-SP-01", "AWS-USE1" |
| tipo_dispositivo_abrev | Tipo Dispositivo (Abrev) | "SRV", "SW", "RT" |
| cidade | Cidade | "São Paulo", "Rio de Janeiro" |
| provedor | Provedor | "Vivo", "Claro", "Tim" |
| vendor | Fornecedor | "AWS", "Azure", "DigitalOcean" |
| fabricante | Fabricante | "Dell", "HP", "Cisco", "Mikrotik" |

**Total:** 11 campos

## 🔧 Normalização Automática (Title Case)

Todos os valores são automaticamente normalizados:

| Entrada do Usuário | Valor Cadastrado |
|--------------------|------------------|
| "empresa ramada" | "Empresa Ramada" |
| "SAO PAULO" | "Sao Paulo" |
| "acme-corp" | "Acme-Corp" |
| "DELL POWEREDGE" | "Dell Poweredge" |

**Regra:** Primeira letra de cada palavra em maiúscula.

## 🗄️ Storage em Consul KV

```
skills/cm/reference-values/
├── company/
│   ├── empresa_ramada.json
│   ├── acme_corp.json
│   └── techcorp.json
├── localizacao/
│   ├── datacenter_sp.json
│   └── aws_us_east_1.json
├── cidade/
│   ├── sao_paulo.json
│   └── rio_de_janeiro.json
├── provedor/
├── vendor/
├── fabricante/
├── grupo_monitoramento/
├── tipo/
├── modelo/
├── cod_localidade/
└── tipo_dispositivo_abrev/
```

**Estrutura do JSON:**
```json
{
  "field_name": "company",
  "value": "Empresa Ramada",
  "original_value": "empresa ramada",
  "created_at": "2025-10-31T12:00:00Z",
  "created_by": "user1",
  "usage_count": 15,
  "last_used_at": "2025-10-31T14:30:00Z",
  "metadata": {}
}
```

## 🔌 API Backend

### Endpoints Disponíveis

#### 1. **POST /api/v1/reference-values/ensure** (Auto-Cadastro)

**USO PRINCIPAL:** Chamado automaticamente ao salvar formulários.

**Request:**
```json
{
  "field_name": "company",
  "value": "empresa ramada",
  "metadata": {}
}
```

**Response:**
```json
{
  "success": true,
  "created": true,
  "value": "Empresa Ramada",
  "message": "Valor 'Empresa Ramada' cadastrado automaticamente"
}
```

#### 2. **GET /api/v1/reference-values/{field_name}** (Listar Valores)

**USO:** Popular selects com valores existentes.

**Example:**
```bash
GET /api/v1/reference-values/company?include_stats=true
```

**Response:**
```json
{
  "success": true,
  "field_name": "company",
  "total": 3,
  "values": [
    {
      "value": "Acme Corp",
      "created_at": "2025-01-01T12:00:00",
      "created_by": "admin",
      "usage_count": 15,
      "last_used_at": "2025-10-31T10:30:00"
    },
    {
      "value": "Empresa Ramada",
      "created_at": "2025-01-02T14:30:00",
      "created_by": "user1",
      "usage_count": 8,
      "last_used_at": "2025-10-30T16:45:00"
    }
  ]
}
```

#### 3. **POST /api/v1/reference-values/** (Criar Manual)

**USO:** Cadastro manual via página de administração.

**Request:**
```json
{
  "field_name": "cidade",
  "value": "São Paulo",
  "metadata": {
    "estado": "SP",
    "regiao": "Sudeste"
  }
}
```

#### 4. **DELETE /api/v1/reference-values/{field_name}/{value}** (Deletar)

**PROTEÇÃO:** Bloqueia deleção se valor em uso!

**Example:**
```bash
DELETE /api/v1/reference-values/company/Empresa%20Ramada
```

**Response (bloqueado):**
```json
{
  "success": false,
  "error": "Valor 'Empresa Ramada' está em uso em 15 instância(s). Não é possível deletar."
}
```

#### 5. **POST /api/v1/reference-values/batch-ensure** (Batch Operation)

**USO:** Processar múltiplos campos de uma vez.

**Request:**
```json
[
  {"field_name": "company", "value": "Empresa Ramada"},
  {"field_name": "cidade", "value": "sao paulo"},
  {"field_name": "provedor", "value": "AWS"}
]
```

**Response:**
```json
{
  "success": true,
  "total_processed": 3,
  "created": 2,
  "existing": 1,
  "results": [...]
}
```

## ⚛️ Frontend - React Hooks

### Hook: `useReferenceValues`

```typescript
import { useReferenceValues } from '../hooks/useReferenceValues';

function MyComponent() {
  const {
    values,           // ["Empresa Ramada", "Acme Corp", ...]
    loading,          // boolean
    error,            // string | null
    ensureValue,      // (value: string) => Promise<EnsureValueResult>
    createValue,      // (value: string) => Promise<boolean>
    deleteValue,      // (value: string, force?: boolean) => Promise<boolean>
    refreshValues     // () => Promise<void>
  } = useReferenceValues({
    fieldName: 'company',
    autoLoad: true,
    includeStats: false
  });

  // Exemplo: Auto-cadastro ao salvar formulário
  const handleSubmit = async (formData) => {
    // Garantir que empresa existe (auto-cadastro)
    const result = await ensureValue(formData.company);

    console.log(result.value); // "Empresa Ramada" (normalizado)
    console.log(result.created); // true (foi criado agora) ou false (já existia)
  };

  return (
    // ... UI
  );
}
```

### Componente: `ReferenceValueInput`

```typescript
import ReferenceValueInput from '../components/ReferenceValueInput';

function FormularioCadastro() {
  const [empresa, setEmpresa] = useState('');

  return (
    <ReferenceValueInput
      fieldName="company"
      value={empresa}
      onChange={setEmpresa}
      placeholder="Selecione ou digite empresa"
      required={true}
    />
  );
}
```

**Features:**
- ✅ AutoComplete com valores existentes
- ✅ Permite digitar valores novos
- ✅ Indicador visual: "Novo valor será criado: X"
- ✅ Normalização automática via backend

## 🔐 Proteção Contra Deleção

Sistema **bloqueia automaticamente** deleção de valores em uso:

```javascript
// Tentar deletar "Ramada" que está em 15 servidores
const result = await deleteValue("Ramada");

// Erro:
// "Valor 'Ramada' está em uso em 15 instância(s). Não é possível deletar."
```

**Forçar deleção (NÃO RECOMENDADO!):**
```javascript
const result = await deleteValue("Ramada", true);  // force=true
```

## 📝 Exemplo Completo de Uso

### 1. Cadastrar Servidor com Auto-Cadastro

```typescript
import { useReferenceValues } from '../hooks/useReferenceValues';
import { useBatchEnsure } from '../hooks/useReferenceValues';

function CadastrarServidor() {
  const { batchEnsure } = useBatchEnsure();

  const handleSubmit = async (values) => {
    // PASSO 1: Garantir que todos os valores metadata existem
    await batchEnsure([
      { fieldName: 'company', value: values.company },
      { fieldName: 'cidade', value: values.cidade },
      { fieldName: 'vendor', value: values.vendor },
      { fieldName: 'fabricante', value: values.fabricante }
    ]);

    // PASSO 2: Cadastrar servidor no Consul
    await cadastrarServidor(values);
  };

  return (
    <Form onFinish={handleSubmit}>
      <ReferenceValueInput
        fieldName="company"
        name="company"
        label="Empresa"
        required
      />
      <ReferenceValueInput
        fieldName="cidade"
        name="cidade"
        label="Cidade"
      />
      {/* ... outros campos ... */}
    </Form>
  );
}
```

### 2. Popular Select com Valores Existentes

```typescript
function FiltroEmpresa() {
  const { values, loading } = useReferenceValues({
    fieldName: 'company',
    autoLoad: true
  });

  return (
    <Select
      loading={loading}
      options={values.map(v => ({ label: v, value: v }))}
      placeholder="Filtrar por empresa"
    />
  );
}
```

### 3. Página de Administração de Valores

```typescript
function AdministrarEmpresas() {
  const {
    valuesWithMetadata,
    loading,
    createValue,
    deleteValue,
    refreshValues
  } = useReferenceValues({
    fieldName: 'company',
    autoLoad: true,
    includeStats: true  // Incluir estatísticas de uso
  });

  const handleDelete = async (value) => {
    try {
      await deleteValue(value);
      message.success(`Empresa '${value}' deletada`);
    } catch (err) {
      message.error(err.message);  // "Valor em uso em N instâncias"
    }
  };

  return (
    <Table
      dataSource={valuesWithMetadata}
      columns={[
        { title: 'Empresa', dataIndex: 'value' },
        { title: 'Criado em', dataIndex: 'created_at' },
        { title: 'Criado por', dataIndex: 'created_by' },
        { title: 'Uso', dataIndex: 'usage_count' },
        {
          title: 'Ações',
          render: (_, record) => (
            <Button onClick={() => handleDelete(record.value)}>
              Deletar
            </Button>
          )
        }
      ]}
    />
  );
}
```

## ⚠️ Importantes Notas Técnicas

### 1. **Categoria** NÃO é Campo Metadata

**ERRO COMUM:** Confundir "category" do metadata_fields.json com campo metadata.

**CORRETO:**
- `category` é propriedade **interna** do metadata_fields.json
- Usada para **organizar os próprios campos** metadata na interface
- Valores: "infrastructure", "basic", "device", "extra"
- **NÃO é campo dos serviços!**

### 2. **Tags** São Array, Não Campo Metadata

**Tags dos serviços Consul:**
```json
{
  "Service": "node_exporter",
  "Tags": ["windows", "linux", "monitoring"]  ← Array de strings
}
```

**NÃO confundir com campo metadata!**

Sistema de retroalimentação para tags será implementado separadamente.

### 3. **Vendor vs Fabricante**

**vendor (Fornecedor):** Cloud providers, ISPs, datacenters
- Exemplos: AWS, Azure, GCP, DigitalOcean, Vivo, Claro

**fabricante:** Hardware manufacturers
- Exemplos: Dell, HP, Cisco, Mikrotik, Ubiquiti

Ambos agora são retroalimentáveis!

## 🚀 Próximos Passos

- [ ] Integrar auto-cadastro em formulários (Services, Exporters, Blackbox)
- [ ] Adicionar coluna "Suporta Auto-Cadastro" em MetadataFields.tsx
- [ ] Criar helper para batch-ensure ao salvar formulários
- [ ] Implementar sistema de retroalimentação para Tags (array)
- [ ] Página de administração completa para Reference Values
- [ ] Dashboard com estatísticas de uso

## 📚 Arquivos Relacionados

**Backend:**
- `backend/core/reference_values_manager.py` - Manager principal
- `backend/api/reference_values.py` - API endpoints
- `backend/config/metadata_fields.json` - Configuração de campos

**Frontend:**
- `frontend/src/hooks/useReferenceValues.ts` - Hook React
- `frontend/src/components/ReferenceValueInput.tsx` - Componente AutoComplete

**Documentação:**
- `REFERENCE_VALUES_GUIDE.md` (este arquivo)
- `REFACTORING_ARCHITECTURE.md` - Arquitetura configuration-driven
- `CLAUDE.md` - Visão geral do projeto

---

**Última atualização:** 2025-10-31
**Versão:** 1.0.0
**Status:** ✅ Implementado (Backend + Frontend base)
