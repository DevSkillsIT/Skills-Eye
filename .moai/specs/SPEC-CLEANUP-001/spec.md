---
id: SPEC-CLEANUP-001
version: "1.2.0"
status: draft
created: 2025-11-21
updated: 2025-11-21
author: Claude Code
priority: MEDIUM
---

# HISTORY

| Versao | Data       | Autor       | Descricao                      |
|--------|------------|-------------|--------------------------------|
| 1.0.0  | 2025-11-21 | Claude Code | Versao inicial do SPEC         |
| 1.1.0  | 2025-11-21 | Claude Code | Alterar para delecao completa  |
| 1.2.0  | 2025-11-21 | Claude Code | Analise completa de dependencias - services.py refatorado, BlackboxGroups adicionado |

---

# SPEC-CLEANUP-001: Remocao Completa de Paginas Obsoletas

## Resumo Executivo

Este SPEC define o processo de remocao completa das paginas estaticas obsoletas do projeto Skills-Eye (Services, Exporters, BlackboxTargets, BlackboxGroups, ServicePresets, TestMonitoringTypes) que foram substituidas pelo sistema dinamico `DynamicMonitoringPage`. O processo garante que nenhuma dependencia seja quebrada e que os arquivos sejam completamente removidos do projeto.

## Contexto e Motivacao

### Problema Identificado

O projeto Skills-Eye passou por uma migracao arquitetural onde 6 paginas estaticas foram substituidas por um sistema dinamico baseado em `DynamicMonitoringPage`. As paginas antigas ainda existem no codigo, causando:

| Problema | Impacto |
|----------|---------|
| Rotas duplicadas | Confusao de navegacao |
| Codigo morto | Manutencao desnecessaria |
| Menu poluido | UX degradada |
| Dependencias ocultas | Risco de regressao |

### Paginas a DELETAR

#### Frontend (7 arquivos)

| Arquivo | Rota | Status | Acao |
|---------|------|--------|------|
| `frontend/src/pages/Services.tsx` | /services | Obsoleto | DELETAR |
| `frontend/src/pages/Exporters.tsx` | /exporters | Obsoleto | DELETAR |
| `frontend/src/pages/BlackboxTargets.tsx` | /blackbox | Obsoleto | DELETAR |
| `frontend/src/pages/BlackboxGroups.tsx` | /blackbox-groups | Obsoleto | DELETAR |
| `frontend/src/pages/ServicePresets.tsx` | /presets | Obsoleto | DELETAR |
| `frontend/src/pages/TestMonitoringTypes.tsx` | N/A | Obsoleto | DELETAR |
| `frontend/src/hooks/useMonitoringType.ts` | N/A | Obsoleto | DELETAR |

#### Backend APIs

| Arquivo | Acao | Detalhes |
|---------|------|----------|
| `backend/api/services.py` | **REFATORAR** | Manter APENAS endpoints CRUD (POST /, PUT /{id}, DELETE /{id}) |
| `backend/api/services_optimized.py` | Mover para obsolete/backend_api/ | Nao utilizado |
| `backend/api/blackbox.py` | Mover para obsolete/backend_api/ | Nao utilizado |
| `backend/api/presets.py` | Mover para obsolete/backend_api/ | Nao utilizado |
| `backend/core/blackbox_manager.py` | Mover para obsolete/backend_core/ | Nao utilizado |
| `backend/core/service_preset_manager.py` | Mover para obsolete/backend_core/ | Nao utilizado |

### MUDANCA CRITICA: services.py NAO pode ser removido completamente!

**Dependencias identificadas em paginas que PERMANECEM**:

- **DynamicMonitoringPage.tsx**: usa `deleteService()`
- **DynamicCRUDModal.tsx**: usa `createService()` e `updateService()`

#### SOLUCAO: Refatorar services.py

**Endpoints a MANTER**:
- `POST /` - createService (usado por DynamicCRUDModal)
- `PUT /{service_id}` - updateService (usado por DynamicCRUDModal)
- `DELETE /{service_id}` - deleteService (usado por DynamicMonitoringPage)

**Endpoints a REMOVER**:
- `GET /` - listServices
- `GET /catalog/names` - getServiceCatalogNames
- `GET /metadata/unique-values` - getMetadataUniqueValues
- `GET /search/by-metadata` - searchByMetadata
- `GET /{service_id}` - getService
- `POST /bulk/register` - bulkRegister
- `DELETE /bulk/deregister` - bulkDeregister

### Analise de Dependencias

#### IMPACTO CRITICO

**ServiceGroups.tsx** (linha 95) navega para `/services?service=...`:

```typescript
const handleServiceClick = (serviceName: string) => {
  navigate(`/services?service=${encodeURIComponent(serviceName)}`);
};
```

**ACAO REQUERIDA**: REMOVER completamente esta funcionalidade de navegacao.

#### Componentes COMPARTILHADOS (NAO remover)

- ColumnSelector
- ResizableTitle
- AdvancedSearchPanel
- FormFieldRenderer
- SiteBadge
- BadgeStatus
- MetadataFilterBar
- NodeSelector
- TagsInput

#### Hooks COMPARTILHADOS (NAO remover)

- useConsulDelete (usado em 8 arquivos)
- useServiceTags
- useReferenceValues / useBatchEnsure
- useMetadataFields

#### Hook EXCLUSIVO (DELETAR)

- `useMonitoringType.ts` (usado apenas em TestMonitoringTypes.tsx)

---

## Functional Requirements (MUST)

### FR-001: DELETAR Paginas Obsoletas do Frontend

**EARS Format**: O sistema **DEVE** deletar os 7 arquivos de paginas/hooks obsoletos do frontend.

**Detalhes**:
- DELETAR `frontend/src/pages/Services.tsx`
- DELETAR `frontend/src/pages/Exporters.tsx`
- DELETAR `frontend/src/pages/BlackboxTargets.tsx`
- DELETAR `frontend/src/pages/BlackboxGroups.tsx`
- DELETAR `frontend/src/pages/ServicePresets.tsx`
- DELETAR `frontend/src/pages/TestMonitoringTypes.tsx`
- DELETAR `frontend/src/hooks/useMonitoringType.ts`

**Justificativa**: Remocao completa de codigo morto sem deixar resquicios no projeto.

### FR-002: Remover Imports no App.tsx

**EARS Format**: O sistema **DEVE** remover os 5 imports das paginas desativadas no arquivo `App.tsx`.

**Detalhes**:
- Remover import de Services
- Remover import de Exporters
- Remover import de BlackboxTargets
- Remover import de BlackboxGroups
- Remover import de ServicePresets

**Codigo a remover**:
```typescript
import Services from './pages/Services';
import Exporters from './pages/Exporters';
import BlackboxTargets from './pages/BlackboxTargets';
import BlackboxGroups from './pages/BlackboxGroups';
import ServicePresets from './pages/ServicePresets';
```

### FR-003: Remover Rotas no App.tsx

**EARS Format**: O sistema **DEVE** remover as 5 rotas `<Route>` das paginas desativadas no arquivo `App.tsx`.

**Detalhes**:
- Remover Route para /services
- Remover Route para /exporters
- Remover Route para /blackbox
- Remover Route para /blackbox-groups
- Remover Route para /presets

**Codigo a remover**:
```typescript
<Route path="/services" element={<Services />} />
<Route path="/exporters" element={<Exporters />} />
<Route path="/blackbox" element={<BlackboxTargets />} />
<Route path="/blackbox-groups" element={<BlackboxGroups />} />
<Route path="/presets" element={<ServicePresets />} />
```

### FR-004: Remover Itens de Menu no App.tsx

**EARS Format**: O sistema **DEVE** remover os 5 itens de menu correspondentes as paginas desativadas.

**Detalhes**:
- Remover item "Services" do menu Monitoramento
- Remover item "Exporters" do menu Monitoramento
- Remover item "Alvos Blackbox" do menu Monitoramento
- Remover item "Grupos Blackbox" do menu Monitoramento
- Remover item "Presets de Servicos" do menu Monitoramento

### FR-005: REMOVER Funcionalidade de Navegacao do ServiceGroups

**EARS Format**: O sistema **DEVE** remover completamente a funcionalidade de navegacao ao clicar em servico no componente `ServiceGroups.tsx`.

**Detalhes**:
- REMOVER funcao `handleServiceClick` (linha 93-96)
- REMOVER onClick handler dos servicos
- NAO implementar navegacao alternativa
- Manter apenas visualizacao dos servicos sem clique

**Codigo a REMOVER**:
```typescript
const handleServiceClick = (serviceName: string) => {
  navigate(`/services?service=${encodeURIComponent(serviceName)}`);
};
```

**Justificativa**: Nao ha destino valido para navegacao apos remocao das paginas.

### FR-006: Preservar Componentes Compartilhados

**EARS Format**: O sistema **DEVE** preservar todos os componentes e hooks compartilhados listados na analise de dependencias.

**Detalhes**:
- NAO remover nenhum componente da pasta `components/`
- NAO remover hooks compartilhados da pasta `hooks/`
- Verificar uso antes de qualquer remocao

### FR-007: REFATORAR services.py (NAO remover completamente!)

**EARS Format**: O sistema **DEVE** refatorar o arquivo `backend/api/services.py` mantendo apenas endpoints CRUD usados por paginas ativas.

**IMPORTANTE**: Este arquivo NAO pode ser movido para obsolete/ porque eh usado por DynamicMonitoringPage e DynamicCRUDModal!

**Endpoints a MANTER**:
- `POST /` - createService
- `PUT /{service_id}` - updateService
- `DELETE /{service_id}` - deleteService

**Endpoints a REMOVER**:
- `GET /` - listServices
- `GET /catalog/names` - getServiceCatalogNames
- `GET /metadata/unique-values` - getMetadataUniqueValues
- `GET /search/by-metadata` - searchByMetadata
- `GET /{service_id}` - getService
- `POST /bulk/register` - bulkRegister
- `DELETE /bulk/deregister` - bulkDeregister

**Justificativa**: Manter funcionalidade CRUD usada pelo sistema dinamico.

### FR-008: Mover APIs Backend para obsolete/

**EARS Format**: O sistema **DEVE** mover arquivos de API backend nao utilizados para pasta `obsolete/`.

**Detalhes**:
- Criar pasta `obsolete/backend_api/`
- Criar pasta `obsolete/backend_core/`
- Mover `backend/api/services_optimized.py` → `obsolete/backend_api/services_optimized.py`
- Mover `backend/api/blackbox.py` → `obsolete/backend_api/blackbox.py`
- Mover `backend/api/presets.py` → `obsolete/backend_api/presets.py`
- Mover `backend/core/blackbox_manager.py` → `obsolete/backend_core/blackbox_manager.py`
- Mover `backend/core/service_preset_manager.py` → `obsolete/backend_core/service_preset_manager.py`

**NOTA**: `backend/api/services.py` NAO sera movido, apenas refatorado (ver FR-007).

**Justificativa**: Preservar codigo para referencia futura sem poluir o projeto principal.

### FR-009: Atualizar app.py do Backend

**EARS Format**: O sistema **DEVE** remover imports e include_router das APIs movidas para obsolete/.

**Imports a REMOVER**:
```python
from api.blackbox import router as blackbox_router
from api.presets import router as presets_router
```

**Include_router a REMOVER**:
```python
app.include_router(blackbox_router, prefix="/api/v1/blackbox", tags=["Blackbox"])
app.include_router(presets_router, prefix="/api/v1/presets", tags=["Service Presets"])
```

**MANTER** (services_router tem endpoints usados):
```python
from api.services import router as services_router
app.include_router(services_router, prefix="/api/v1/services", tags=["Services"])
```

### FR-010: Atualizar api.ts do Frontend

**EARS Format**: O sistema **DEVE** remover metodos nao utilizados da API frontend.

**Metodos a REMOVER**:
- Todos os metodos de blackbox (createBlackboxGroup, listBlackboxGroups, etc)
- Todos os metodos de presets
- Metodos de listagem de services (listServices, getService, getServiceCatalogNames, etc)

**Metodos a MANTER**:
- createService
- updateService
- deleteService
- deregisterService

### FR-011: Atualizar models.py do Backend

**EARS Format**: O sistema **DEVE** remover models nao utilizados do backend.

**REMOVER**:
- BlackboxTarget
- BlackboxUpdateRequest
- BlackboxDeleteRequest

**MANTER**:
- ServiceCreateRequest (usado por createService)
- ServiceUpdateRequest (usado por updateService)

---

## Non-Functional Requirements (SHOULD)

### NFR-001: Execucao Reversivel

O sistema **DEVERIA** executar o processo em etapas reversiveis, permitindo rollback facil.

**Metricas alvo**:
- Cada etapa deve ser um commit separado
- Commits devem ser atomicos e reversiveis

### NFR-002: Compilacao Sem Erros

O sistema **DEVERIA** compilar sem erros apos cada etapa de modificacao.

**Validacao**:
- Executar `npm run build` apos cada fase
- Corrigir erros antes de prosseguir

### NFR-003: Testes Passando

O sistema **DEVERIA** manter todos os testes passando apos a conclusao.

**Validacao**:
- Executar `npm test` apos todas as modificacoes
- Corrigir testes quebrados se houver

### NFR-004: Zero Downtime

O sistema **DEVERIA** permitir deploy sem downtime durante a transicao.

---

## Interface Requirements (SHALL)

### IR-001: Menu Sem Links Quebrados

O sistema **NAO DEVERA** apresentar links quebrados no menu de navegacao.

**Validacao**:
- Todos os itens de menu devem apontar para rotas validas
- Nenhum item deve resultar em pagina 404

### IR-002: Sem Imports Nao Utilizados

O sistema **NAO DEVERA** conter imports nao utilizados apos a desativacao.

**Validacao**:
- ESLint nao deve reportar warnings de imports nao utilizados
- Build nao deve ter warnings relacionados

### IR-003: Console Limpo

O sistema **NAO DEVERA** apresentar erros ou warnings no console do navegador apos a desativacao.

### IR-004: ServiceGroups Sem Navegacao

O sistema **NAO DEVERA** navegar para lugar nenhum ao clicar em servicos no ServiceGroups.

**Validacao**:
- Clique em servico nao deve causar navegacao
- Nao deve haver erros no console ao clicar

### IR-005: CRUD de Services Funcional

O sistema **NAO DEVERA** quebrar a funcionalidade CRUD de services usada pelo DynamicMonitoringPage.

**Validacao**:
- createService funciona em DynamicCRUDModal
- updateService funciona em DynamicCRUDModal
- deleteService funciona em DynamicMonitoringPage

---

## Design Constraints (MUST)

### DC-001: Verificacao de APIs Backend ANTES de Mover

As APIs do backend **DEVEM** ser verificadas quanto a dependencias em outras paginas ANTES de serem movidas.

**Justificativa**:
- Garantir que nenhuma funcionalidade ativa seja quebrada
- Verificar imports em outros modulos

### DC-002: Arquivos Completamente Removidos

Os arquivos de pagina do frontend **DEVEM** ser completamente DELETADOS, NAO renomeados.

**Justificativa**:
- Remocao completa de codigo morto
- Projeto limpo sem resquicios
- Backend APIs vao para obsolete/ para referencia futura

### DC-003: ServiceGroups Sem Comportamento de Clique

A pagina ServiceGroups **DEVE** remover completamente o comportamento de clique em servicos.

**Justificativa**:
- Nao ha destino valido para navegacao
- Evitar confusao do usuario com cliques que nao fazem nada util

### DC-004: Sem Alteracao de DynamicMonitoringPage

O componente DynamicMonitoringPage **NAO DEVE** ser alterado neste SPEC.

**Justificativa**: Evitar efeitos colaterais em sistema ja funcional.

### DC-005: Manter Funcionalidade CRUD de Services

O sistema **DEVE** manter a funcionalidade CRUD de services para o DynamicMonitoringPage.

**Justificativa**:
- DynamicMonitoringPage usa deleteService
- DynamicCRUDModal usa createService e updateService

---

## Arquivos a Serem Modificados

### Frontend - Modificacoes

| Arquivo | Modificacao | Risco |
|---------|-------------|-------|
| `frontend/src/App.tsx` | Remover 5 imports, 5 rotas e 5 menu items | Medio |
| `frontend/src/pages/ServiceGroups.tsx` | REMOVER handleServiceClick completamente | Medio |
| `frontend/src/services/api.ts` | Remover metodos nao utilizados | Baixo |

### Frontend - DELETAR (6 paginas + 1 hook)

| Arquivo | Motivo | Risco |
|---------|--------|-------|
| `frontend/src/pages/Services.tsx` | Obsoleto | Baixo |
| `frontend/src/pages/Exporters.tsx` | Obsoleto | Baixo |
| `frontend/src/pages/BlackboxTargets.tsx` | Obsoleto | Baixo |
| `frontend/src/pages/BlackboxGroups.tsx` | Obsoleto | Baixo |
| `frontend/src/pages/ServicePresets.tsx` | Obsoleto | Baixo |
| `frontend/src/pages/TestMonitoringTypes.tsx` | Obsoleto | Baixo |
| `frontend/src/hooks/useMonitoringType.ts` | Hook exclusivo | Baixo |

### Backend - Modificacoes

| Arquivo | Modificacao | Risco |
|---------|-------------|-------|
| `backend/api/services.py` | REFATORAR - manter apenas CRUD | Alto |
| `backend/app.py` | Remover imports e include_router | Medio |
| `backend/models.py` | Remover models de blackbox | Baixo |

### Backend - Mover para obsolete/

| Arquivo Original | Destino | Risco |
|-----------------|---------|-------|
| `backend/api/services_optimized.py` | `obsolete/backend_api/services_optimized.py` | Baixo |
| `backend/api/blackbox.py` | `obsolete/backend_api/blackbox.py` | Medio |
| `backend/api/presets.py` | `obsolete/backend_api/presets.py` | Baixo |
| `backend/core/blackbox_manager.py` | `obsolete/backend_core/blackbox_manager.py` | Baixo |
| `backend/core/service_preset_manager.py` | `obsolete/backend_core/service_preset_manager.py` | Baixo |

---

## Riscos e Mitigacoes

| Risco | Probabilidade | Impacto | Mitigacao |
|-------|---------------|---------|-----------|
| CRUD de services quebrado | Alta | Critico | Refatorar cuidadosamente services.py |
| API backend usada por outra pagina | Media | Alto | Verificar TODOS imports antes de mover |
| Import esquecido no App.tsx | Media | Medio | Verificar todos imports apos remocao |
| Componente compartilhado removido | Baixa | Alto | Analise de dependencias previa |
| Build falha | Media | Medio | Testar build apos cada etapa |
| Testes quebram | Media | Baixo | Executar testes apos cada etapa |

---

## Dependencias Tecnicas

1. **git rm** - Comando para deletar arquivos com tracking
2. **mkdir -p** - Criar estrutura obsolete/
3. **git mv** - Mover arquivos backend mantendo historico
4. **npm run build** - Validacao de compilacao
5. **npm test** - Validacao de testes
6. **ESLint** - Validacao de imports nao utilizados

---

## Estimativa de Complexidade

- **Total**: Media-Alta
- **Refatoracao services.py**: Alta (manter apenas CRUD)
- **Analise de dependencias backend**: Media (verificar todos imports)
- **Modificacoes frontend**: Baixa (delecao direta)
- **Modificacoes app.py**: Media (remover imports e routers)
- **Validacao**: Media (testes e build)

---

## Notas de Implementacao

1. **Ordem de execucao**: REFATORAR services.py PRIMEIRO, depois limpar App.tsx, DELETAR arquivos frontend, MOVER backend APIs
2. **Commits atomicos**: Um commit por fase para facilitar rollback
3. **Build continuo**: Validar build apos cada modificacao
4. **DELETAR completamente**: NAO usar .old-deprecated, DELETAR do frontend
5. **Backend services.py**: REFATORAR, NAO mover para obsolete/
6. **Testar CRUD**: Verificar createService, updateService, deleteService apos refatoracao

---

## Tags de Rastreabilidade

<!-- TAG_BLOCK_START -->
- [SPEC-CLEANUP-001] Especificacao de remocao de paginas obsoletas
- [FR-001] DELETAR paginas obsoletas do frontend (6 paginas + 1 hook)
- [FR-002] Remover imports no App.tsx (5 imports)
- [FR-003] Remover rotas no App.tsx (5 rotas)
- [FR-004] Remover itens de menu (5 items)
- [FR-005] REMOVER navegacao ServiceGroups
- [FR-006] Preservar componentes compartilhados
- [FR-007] REFATORAR services.py (manter CRUD)
- [FR-008] Mover APIs backend para obsolete
- [FR-009] Atualizar app.py do backend
- [FR-010] Atualizar api.ts do frontend
- [FR-011] Atualizar models.py do backend
<!-- TAG_BLOCK_END -->
