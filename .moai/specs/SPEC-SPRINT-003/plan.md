# Plano de Implementação - SPEC-SPRINT-003

---
id: SPEC-SPRINT-003-PLAN
version: 1.0.0
status: draft
created: 2025-11-19
parent: SPEC-SPRINT-003
---

## TAG BLOCK

```
[TAG:SPEC-SPRINT-003-PLAN]
[PARENT:SPEC-SPRINT-003]
[TYPE:implementation-plan]
```

---

## 1. Resumo Executivo

Este plano detalha a implementação das funcionalidades restantes do Sprint 3 do Skills-Eye, focando em CRUD dinâmico completo com campos baseados em KV metadata-fields.

**Estimativa Total: 14-18 horas**

---

## 2. Fases de Implementação

### FASE 1: Preparação e Botão Refresh (1h)
**Prioridade:** Alta | **Dependências:** Nenhuma

#### 1.1 Botão Refresh em MonitoringTypes.tsx

**Arquivo:** `/home/adrianofante/projetos/Skills-Eye/frontend/src/pages/MonitoringTypes.tsx`

**Tarefas:**
1. Adicionar botão "Atualizar" ao lado dos botões existentes
2. Implementar handler que invalida cache local
3. Chamar `handleReload()` existente
4. Mostrar timestamp da última atualização
5. Integrar BadgeStatus para feedback

**Código de referência:**
```tsx
// Adicionar ao Space de botões (linha ~450)
<Tooltip title="Invalidar cache e recarregar tipos">
  <Button
    icon={<SyncOutlined spin={loading} />}
    onClick={async () => {
      await handleReload();
      message.success('Tipos de monitoramento atualizados');
    }}
  >
    Atualizar
  </Button>
</Tooltip>
```

**Testes:**
- Teste unitário: Botão chama handleReload
- Teste integração: Cache é invalidado após click

---

### FASE 2: Modal de Criação (3-4h)
**Prioridade:** Crítica | **Dependências:** Fase 1

#### 2.1 Estados e Hooks

**Arquivo:** `/home/adrianofante/projetos/Skills-Eye/frontend/src/pages/DynamicMonitoringPage.tsx`

**Tarefas:**
1. Importar componentes necessários:
   ```tsx
   import { Form } from 'antd';
   import FormFieldRenderer from '../components/FormFieldRenderer';
   import { useFormFields } from '../hooks/useMetadataFields';
   import { consulAPI } from '../services/api';
   ```

2. Adicionar estados para o modal:
   ```tsx
   const [form] = Form.useForm();
   const [submitLoading, setSubmitLoading] = useState(false);
   const [availableTypes, setAvailableTypes] = useState<MonitoringType[]>([]);
   const [selectedTypeId, setSelectedTypeId] = useState<string | null>(null);
   ```

3. Usar hook para campos dinâmicos:
   ```tsx
   // Mapear categoria para contexto
   const contextMap: Record<string, string> = {
     'network-probes': 'blackbox',
     'web-probes': 'blackbox',
     'system-exporters': 'exporters',
     'database-exporters': 'exporters',
   };
   const formContext = contextMap[category] || category;

   const { formFields, loading: fieldsLoading } = useFormFields(formContext);
   ```

#### 2.2 Carregamento de Tipos

**Tarefas:**
1. Carregar tipos disponíveis quando modal abre:
   ```tsx
   useEffect(() => {
     if (formOpen && formMode === 'create') {
       consulAPI.getMonitoringTypes()
         .then(response => {
           if (response.success) {
             setAvailableTypes(response.types);
           }
         })
         .catch(err => {
           message.error('Erro ao carregar tipos de monitoramento');
         });
     }
   }, [formOpen, formMode]);
   ```

#### 2.3 Renderização do Formulário

**Substituir conteúdo do Modal (linha ~1344):**

```tsx
<Modal
  title={formMode === 'create' ? 'Novo registro' : `Editar: ${currentRecord?.ID}`}
  open={formOpen}
  onCancel={() => {
    setFormOpen(false);
    setCurrentRecord(null);
    form.resetFields();
    setSelectedTypeId(null);
  }}
  onOk={() => form.submit()}
  confirmLoading={submitLoading}
  width={720}
  destroyOnHidden
>
  <Form
    form={form}
    layout="vertical"
    onFinish={handleFormSubmit}
    initialValues={currentRecord ? {
      ...currentRecord.Meta,
      type_id: currentRecord.Meta?.type_id,
    } : {}}
  >
    {/* Seleção de tipo (apenas na criação) */}
    {formMode === 'create' && (
      <Form.Item
        name="type_id"
        label="Tipo de Monitoramento"
        rules={[{ required: true, message: 'Selecione o tipo de monitoramento' }]}
      >
        <Select
          placeholder="Selecione o tipo"
          loading={!availableTypes.length}
          onChange={(value) => setSelectedTypeId(value)}
          showSearch
          optionFilterProp="children"
        >
          {availableTypes.map(type => (
            <Select.Option key={type.id} value={type.id}>
              {type.display_name} ({type.job_name})
            </Select.Option>
          ))}
        </Select>
      </Form.Item>
    )}

    <Divider>Campos de Metadata</Divider>

    {fieldsLoading ? (
      <Spin tip="Carregando campos..." />
    ) : (
      <>
        {/* Campos obrigatórios primeiro */}
        <Typography.Text strong style={{ marginBottom: 16, display: 'block' }}>
          Campos Obrigatórios
        </Typography.Text>
        {formFields
          .filter(f => f.required)
          .map(field => (
            <FormFieldRenderer
              key={field.name}
              field={field}
              mode={formMode}
            />
          ))
        }

        {/* Campos opcionais */}
        {formFields.filter(f => !f.required).length > 0 && (
          <>
            <Divider dashed />
            <Typography.Text type="secondary" style={{ marginBottom: 16, display: 'block' }}>
              Campos Opcionais
            </Typography.Text>
            {formFields
              .filter(f => !f.required)
              .map(field => (
                <FormFieldRenderer
                  key={field.name}
                  field={field}
                  mode={formMode}
                />
              ))
            }
          </>
        )}
      </>
    )}
  </Form>
</Modal>
```

#### 2.4 Handler de Submit (Criação)

```tsx
const handleFormSubmit = useCallback(async (values: Record<string, any>) => {
  setSubmitLoading(true);

  try {
    // Separar type_id dos metadata
    const { type_id, ...metadata } = values;

    // Montar payload
    const payload = {
      Meta: metadata,
      Tags: [category], // Tag da categoria
      type_id: type_id,
    };

    if (formMode === 'create') {
      // POST para criar
      const response = await consulAPI.createService(payload);

      if (response.success) {
        message.success(`Serviço criado com sucesso! ID: ${response.service_id}`);
        setFormOpen(false);
        form.resetFields();
        actionRef.current?.reload();
      } else {
        message.error(response.error || 'Erro ao criar serviço');
      }
    } else {
      // PUT para editar
      const serviceId = currentRecord?.ID;
      if (!serviceId) {
        message.error('ID do serviço não encontrado');
        return;
      }

      const response = await consulAPI.updateService(serviceId, payload);

      if (response.success) {
        message.success('Serviço atualizado com sucesso!');
        setFormOpen(false);
        form.resetFields();
        setCurrentRecord(null);
        actionRef.current?.reload();
      } else {
        message.error(response.error || 'Erro ao atualizar serviço');
      }
    }
  } catch (error: any) {
    message.error(`Erro: ${error.message || error}`);
  } finally {
    setSubmitLoading(false);
  }
}, [formMode, currentRecord, category, form]);
```

**Testes:**
- Teste unitário: Form valida campos obrigatórios
- Teste unitário: Submit chama API correta (POST/PUT)
- Teste integração: Serviço é criado no Consul
- Teste E2E: Fluxo completo de criação

---

### FASE 3: Modal de Edição (2-3h)
**Prioridade:** Crítica | **Dependências:** Fase 2

#### 3.1 Preencher Formulário com Dados

**Tarefas:**
1. Quando `formMode === 'edit'`, preencher form com currentRecord
2. Atualizar `handleEdit` para passar dados corretos
3. Ajustar initialValues do Form

**Código:**
```tsx
// Atualizar handleEdit (linha ~784)
const handleEdit = useCallback((record: MonitoringDataItem) => {
  setFormMode('edit');
  setCurrentRecord(record);

  // Preencher form com dados do registro
  form.setFieldsValue({
    ...record.Meta,
    type_id: record.Meta?.type_id || record.type_id,
  });

  setFormOpen(true);
}, [form]);
```

#### 3.2 Preservar Dados não Editáveis

**Tarefas:**
1. Adicionar campos readonly para ID, timestamps
2. Merge de metadata ao invés de replace

```tsx
// No handleFormSubmit, modo edit:
const response = await consulAPI.updateService(serviceId, {
  ...currentRecord, // Preservar dados existentes
  Meta: {
    ...currentRecord.Meta, // Preservar metadata existente
    ...metadata, // Sobrescrever com novos valores
  },
});
```

**Testes:**
- Teste unitário: Form é preenchido com dados corretos
- Teste unitário: Campos readonly não são editáveis
- Teste integração: Update preserva dados não alterados

---

### FASE 4: Exclusão Individual e Batch (2-3h)
**Prioridade:** Alta | **Dependências:** Nenhuma (paralela com Fase 2-3)

#### 4.1 Implementar handleDelete

**Arquivo:** `/home/adrianofante/projetos/Skills-Eye/frontend/src/pages/DynamicMonitoringPage.tsx`

**Substituir TODO na linha ~791:**

```tsx
const handleDelete = useCallback(async (record: MonitoringDataItem) => {
  try {
    const serviceId = record.ID;

    // Chamar API de exclusão
    const response = await consulAPI.deleteService(serviceId);

    if (response.success) {
      message.success(`Serviço "${serviceId}" excluído com sucesso`);
      actionRef.current?.reload();
    } else {
      message.error(response.error || 'Erro ao excluir serviço');
    }
  } catch (error: any) {
    if (error.response?.status === 404) {
      message.error('Serviço não encontrado');
    } else if (error.response?.status === 409) {
      message.error('Serviço em uso, não pode ser excluído');
    } else {
      message.error('Erro ao excluir: ' + (error.message || error));
    }
  }
}, []);
```

#### 4.2 Implementar handleBatchDelete

**Substituir TODO na linha ~806:**

```tsx
const handleBatchDelete = useCallback(async () => {
  if (!selectedRows.length) return;

  try {
    // Limitar concorrência a 10
    const batchSize = 10;
    const results: { success: string[]; failed: string[] } = { success: [], failed: [] };

    // Processar em batches
    for (let i = 0; i < selectedRows.length; i += batchSize) {
      const batch = selectedRows.slice(i, i + batchSize);

      // Executar batch em paralelo
      const promises = batch.map(async (record) => {
        try {
          const response = await consulAPI.deleteService(record.ID);
          if (response.success) {
            results.success.push(record.ID);
          } else {
            results.failed.push(record.ID);
          }
        } catch {
          results.failed.push(record.ID);
        }
      });

      await Promise.all(promises);
    }

    // Mostrar resultado
    if (results.failed.length === 0) {
      message.success(`${results.success.length} serviços excluídos com sucesso`);
    } else {
      message.warning(
        `${results.success.length} excluídos, ${results.failed.length} falhas`
      );
      console.error('Falhas na exclusão:', results.failed);
    }

    // Limpar seleção e recarregar
    setSelectedRowKeys([]);
    setSelectedRows([]);
    actionRef.current?.reload();

  } catch (error: any) {
    message.error('Erro ao excluir: ' + (error.message || error));
  }
}, [selectedRows]);
```

#### 4.3 Adicionar Coluna de Ações na Tabela

**Verificar se existe e adicionar Popconfirm:**

```tsx
// Na definição de columns, adicionar/atualizar coluna de ações
{
  title: 'Ações',
  key: 'actions',
  width: 120,
  fixed: 'right',
  render: (_, record) => (
    <Space size="small">
      <Tooltip title="Editar">
        <Button
          type="link"
          icon={<EditOutlined />}
          onClick={() => handleEdit(record)}
        />
      </Tooltip>
      <Popconfirm
        title="Remover serviço?"
        description={`ID: ${record.ID}`}
        onConfirm={() => handleDelete(record)}
        okText="Sim"
        cancelText="Não"
        okButtonProps={{ danger: true }}
      >
        <Tooltip title="Excluir">
          <Button
            type="link"
            danger
            icon={<DeleteOutlined />}
          />
        </Tooltip>
      </Popconfirm>
    </Space>
  ),
}
```

**Testes:**
- Teste unitário: handleDelete chama API correta
- Teste unitário: handleBatchDelete processa em batches
- Teste unitário: Erros são tratados individualmente
- Teste integração: Serviços são removidos do Consul

---

### FASE 5: Geração Dinâmica de ID - Backend (2-3h)
**Prioridade:** Alta | **Dependências:** Nenhuma (pode ser paralela)

#### 5.1 Implementar Método no ConsulManager

**Arquivo:** `/home/adrianofante/projetos/Skills-Eye/backend/core/consul_manager.py`

**Adicionar método:**

```python
async def generate_dynamic_service_id(self, meta: dict) -> str:
    """
    Gera ID de serviço dinamicamente baseado nos campos obrigatórios do KV.

    Usa abordagem híbrida:
    - Tenta ler campos obrigatórios do KV
    - Se falhar, usa padrão hardcoded como fallback

    Args:
        meta: Dicionário com metadata do serviço

    Returns:
        ID gerado no formato: campo1/campo2/.../campoN@name

    Raises:
        ValueError: Se campos obrigatórios estiverem faltando
    """
    try:
        # Tentar obter campos obrigatórios do KV
        required_fields = await self._get_required_fields_from_kv()

        if required_fields:
            logger.info(f"Usando campos dinâmicos do KV: {required_fields}")
        else:
            # Fallback: campos hardcoded
            required_fields = ['module', 'company', 'project', 'env', 'name']
            logger.warning("KV indisponível, usando campos hardcoded como fallback")

        # Separar 'name' que vai após o @
        name_field = 'name'
        prefix_fields = [f for f in required_fields if f != name_field]

        # Validar campos obrigatórios
        missing = []
        for field in required_fields:
            if field not in meta or not meta[field]:
                missing.append(field)

        if missing:
            raise ValueError(f"Campos obrigatórios faltando: {', '.join(missing)}")

        # Gerar ID
        prefix_parts = [self._sanitize_id_part(meta[f]) for f in prefix_fields]
        name_part = self._sanitize_id_part(meta[name_field])

        service_id = f"{'/'.join(prefix_parts)}@{name_part}"

        return service_id

    except ValueError:
        raise
    except Exception as e:
        logger.error(f"Erro ao gerar ID dinâmico: {e}")
        # Fallback completo
        return self._generate_fallback_id(meta)

async def _get_required_fields_from_kv(self) -> list:
    """
    Obtém lista de campos obrigatórios do KV metadata-fields.

    Returns:
        Lista de nomes de campos obrigatórios ordenados por 'order'
    """
    try:
        # Buscar configuração do KV
        kv_key = "skills-eye/config/metadata-fields"
        value = await self.get_kv(kv_key)

        if not value:
            return []

        fields = json.loads(value)

        # Filtrar campos obrigatórios e ordenar
        required = [
            f['name'] for f in fields
            if f.get('required', False) and f.get('enabled', True)
        ]

        # Ordenar por 'order' se disponível
        required_with_order = [
            (f['name'], f.get('order', 999))
            for f in fields
            if f.get('required', False) and f.get('enabled', True)
        ]
        required_with_order.sort(key=lambda x: x[1])

        return [name for name, _ in required_with_order]

    except Exception as e:
        logger.warning(f"Erro ao ler campos do KV: {e}")
        return []

def _sanitize_id_part(self, value: str) -> str:
    """
    Sanitiza parte do ID removendo caracteres especiais.
    """
    import re
    # Remover caracteres não alfanuméricos exceto - e _
    sanitized = re.sub(r'[^a-zA-Z0-9\-_]', '', str(value))
    return sanitized.lower()

def _generate_fallback_id(self, meta: dict) -> str:
    """
    Gera ID usando padrão hardcoded (fallback).
    """
    parts = [
        meta.get('module', 'unknown'),
        meta.get('company', 'unknown'),
        meta.get('project', 'unknown'),
        meta.get('env', 'unknown'),
    ]
    name = meta.get('name', 'unnamed')

    sanitized_parts = [self._sanitize_id_part(p) for p in parts]
    sanitized_name = self._sanitize_id_part(name)

    return f"{'/'.join(sanitized_parts)}@{sanitized_name}"
```

**Testes:**
- Teste unitário: Gera ID com campos do KV
- Teste unitário: Fallback quando KV falha
- Teste unitário: Sanitização de caracteres especiais
- Teste unitário: Erro quando campos obrigatórios faltam

---

### FASE 6: Prewarm no Startup (1-2h)
**Prioridade:** Média | **Dependências:** Fase 5

#### 6.1 Adicionar Prewarm em app.py

**Arquivo:** `/home/adrianofante/projetos/Skills-Eye/backend/app.py`

**Adicionar ao evento startup:**

```python
@app.on_event("startup")
async def startup_event():
    """
    Evento de inicialização da aplicação.

    - Carrega tipos de monitoramento em cache
    - Pré-aquece cache de metadata-fields
    """
    logger.info("Iniciando Skills-Eye Backend...")

    # Prewarm de Monitoring Types
    try:
        from api.monitoring_types_dynamic import extract_types_from_all_servers

        logger.info("Executando prewarm de monitoring types...")
        result = await extract_types_from_all_servers()

        if result.get('success'):
            types_count = len(result.get('types', []))
            logger.info(f"Prewarm concluído: {types_count} tipos carregados")
        else:
            logger.warning(f"Prewarm parcial: {result.get('error', 'erro desconhecido')}")

    except Exception as e:
        # Não bloquear startup se prewarm falhar
        logger.error(f"Erro no prewarm de monitoring types: {e}")
        logger.info("Aplicação continuará sem prewarm")

    # Prewarm de metadata-fields
    try:
        from core.consul_manager import ConsulManager
        consul = ConsulManager()

        logger.info("Carregando metadata-fields...")
        fields = await consul.get_metadata_fields()
        logger.info(f"Metadata-fields carregados: {len(fields)} campos")

    except Exception as e:
        logger.error(f"Erro ao carregar metadata-fields: {e}")

    logger.info("Skills-Eye Backend iniciado com sucesso!")
```

#### 6.2 Retry em Background

**Adicionar task de retry se prewarm falhar:**

```python
import asyncio

_prewarm_retry_task = None

async def _prewarm_retry_loop():
    """
    Tenta executar prewarm novamente se falhou no startup.
    """
    await asyncio.sleep(30)  # Esperar 30 segundos

    try:
        from api.monitoring_types_dynamic import extract_types_from_all_servers
        result = await extract_types_from_all_servers()

        if result.get('success'):
            logger.info("Prewarm retry bem-sucedido")
        else:
            logger.warning("Prewarm retry falhou, próxima tentativa em 60s")
            await asyncio.sleep(60)
            await _prewarm_retry_loop()

    except Exception as e:
        logger.error(f"Erro no prewarm retry: {e}")
```

**Testes:**
- Teste unitário: Prewarm executa no startup
- Teste unitário: Falha não bloqueia startup
- Teste integração: Cache é populado após startup

---

### FASE 7: Testes Obrigatórios (3-4h)
**Prioridade:** Crítica | **Dependências:** Fases 1-6

#### 7.1 Testes Frontend (Jest/Vitest)

**Arquivo:** `/home/adrianofante/projetos/Skills-Eye/frontend/src/__tests__/DynamicMonitoringPage.test.tsx`

```typescript
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { vi } from 'vitest';
import DynamicMonitoringPage from '../pages/DynamicMonitoringPage';
import { consulAPI } from '../services/api';

// Mock da API
vi.mock('../services/api', () => ({
  consulAPI: {
    getServices: vi.fn(),
    createService: vi.fn(),
    updateService: vi.fn(),
    deleteService: vi.fn(),
    getMonitoringTypes: vi.fn(),
  },
}));

describe('DynamicMonitoringPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('Modal de Criação', () => {
    it('deve abrir modal ao clicar em Novo registro', async () => {
      render(<DynamicMonitoringPage />);

      const newButton = screen.getByText('Novo registro');
      fireEvent.click(newButton);

      await waitFor(() => {
        expect(screen.getByText('Novo registro')).toBeInTheDocument();
      });
    });

    it('deve renderizar campos dinâmicos', async () => {
      // Implementar
    });

    it('deve validar campos obrigatórios', async () => {
      // Implementar
    });

    it('deve chamar API ao submeter', async () => {
      // Implementar
    });
  });

  describe('Modal de Edição', () => {
    it('deve preencher form com dados do registro', async () => {
      // Implementar
    });
  });

  describe('Exclusão', () => {
    it('deve chamar API ao confirmar exclusão', async () => {
      // Implementar
    });

    it('deve processar batch delete em paralelo', async () => {
      // Implementar
    });
  });
});
```

#### 7.2 Testes Backend (Pytest)

**Arquivo:** `/home/adrianofante/projetos/Skills-Eye/backend/tests/test_id_generation.py`

```python
import pytest
from core.consul_manager import ConsulManager

@pytest.mark.asyncio
async def test_generate_dynamic_service_id_success():
    """Testa geração de ID com campos do KV"""
    consul = ConsulManager()

    meta = {
        'module': 'icmp',
        'company': 'TestCorp',
        'project': 'main',
        'env': 'prod',
        'name': 'test-service'
    }

    service_id = await consul.generate_dynamic_service_id(meta)

    assert service_id is not None
    assert '@' in service_id
    assert 'test-service' in service_id

@pytest.mark.asyncio
async def test_generate_dynamic_service_id_fallback():
    """Testa fallback quando KV falha"""
    # Implementar com mock

@pytest.mark.asyncio
async def test_generate_dynamic_service_id_missing_fields():
    """Testa erro quando campos obrigatórios faltam"""
    consul = ConsulManager()

    meta = {'name': 'test'}  # Faltando campos obrigatórios

    with pytest.raises(ValueError) as exc_info:
        await consul.generate_dynamic_service_id(meta)

    assert 'Campos obrigatórios faltando' in str(exc_info.value)

@pytest.mark.asyncio
async def test_sanitize_id_part():
    """Testa sanitização de caracteres especiais"""
    consul = ConsulManager()

    assert consul._sanitize_id_part('Test Corp!@#') == 'testcorp'
    assert consul._sanitize_id_part('my-project_v2') == 'my-project_v2'
```

**Arquivo:** `/home/adrianofante/projetos/Skills-Eye/backend/tests/test_services_crud.py`

```python
import pytest
from httpx import AsyncClient
from app import app

@pytest.mark.asyncio
async def test_create_service():
    """Testa criação de serviço via API"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post("/api/v1/services", json={
            "Meta": {
                "module": "icmp",
                "company": "test",
                "project": "test",
                "env": "test",
                "name": "test-service"
            },
            "Tags": ["test"]
        })

        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        assert "service_id" in data

@pytest.mark.asyncio
async def test_delete_service():
    """Testa exclusão de serviço via API"""
    # Implementar

@pytest.mark.asyncio
async def test_prewarm_on_startup():
    """Testa que prewarm executa no startup"""
    # Implementar
```

---

## 3. Cronograma Sugerido

| Fase | Duração | Início | Dependências |
|------|---------|--------|--------------|
| 1. Botão Refresh | 1h | T+0h | - |
| 2. Modal Criação | 3-4h | T+1h | Fase 1 |
| 3. Modal Edição | 2-3h | T+5h | Fase 2 |
| 4. Exclusão | 2-3h | T+1h | - (paralela) |
| 5. ID Dinâmico | 2-3h | T+1h | - (paralela) |
| 6. Prewarm | 1-2h | T+8h | Fase 5 |
| 7. Testes | 3-4h | T+9h | Fases 1-6 |

**Total: 14-18 horas**

---

## 4. Critérios de Conclusão

- [ ] Todos os TODOs removidos dos arquivos
- [ ] Modal de criação funcional com campos dinâmicos
- [ ] Modal de edição preenchendo dados existentes
- [ ] Exclusão individual com confirmação
- [ ] Batch delete processando em paralelo
- [ ] Geração de ID híbrida (KV + fallback)
- [ ] Prewarm executando no startup
- [ ] Cobertura de testes >= 80%
- [ ] Sem erros no console do navegador
- [ ] Sem warnings de TypeScript

---

## 5. Recursos Necessários

### 5.1 Documentação de Referência

- Ant Design Pro: https://procomponents.ant.design/
- FormFieldRenderer: `/frontend/src/components/FormFieldRenderer.tsx`
- useMetadataFields: `/frontend/src/hooks/useMetadataFields.ts`
- consulAPI: `/frontend/src/services/api.ts`

### 5.2 Componentes Existentes

| Componente | Uso |
|------------|-----|
| FormFieldRenderer | Renderizar campos dinâmicos |
| ReferenceValueInput | Autocomplete com cadastro |
| BadgeStatus | Indicador de cache |
| NodeSelector | Seleção de nó Consul |

---

## 6. Riscos do Plano

| Risco | Mitigação |
|-------|-----------|
| Campos dinâmicos não carregam | Verificar contexto correto no useFormFields |
| API retorna erro 500 | Adicionar tratamento de erro detalhado |
| Performance em batch delete | Limitar concorrência a 10 |
| Testes demoram muito | Usar mocks para APIs externas |

---

**[END:SPEC-SPRINT-003-PLAN]**
