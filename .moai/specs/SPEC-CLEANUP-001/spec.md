---
id: SPEC-CLEANUP-001
version: "1.4.0"
status: completed
created: 2025-11-21
updated: 2025-11-22
author: Claude Code
priority: MEDIUM
---

# HISTORY

| Versao | Data       | Autor       | Descricao                      |
|--------|------------|-------------|--------------------------------|
| 1.0.0  | 2025-11-21 | Claude Code | Versao inicial do SPEC         |
| 1.1.0  | 2025-11-21 | Claude Code | Alterar para delecao completa  |
| 1.2.0  | 2025-11-21 | Claude Code | Analise completa de dependencias - services.py refatorado, BlackboxGroups adicionado |
| 1.3.0  | 2025-11-21 | Claude Code | Correcoes criticas auditoria: testes, Dashboard.tsx, scripts diagnostico, caminho models.py, bulkDeleteServices |
| 1.4.0  | 2025-11-22 | Claude Code | Preservar funcoes bulk (register/deregister), corrigir caminhos Tests/, remover referencia diagnostico.ps1 |

---

# SPEC-CLEANUP-001: Remocao Completa de Paginas Obsoletas

## Resumo Executivo

Este SPEC define o processo de remocao completa das paginas estaticas obsoletas do projeto Skills-Eye (Services, Exporters, BlackboxTargets, BlackboxGroups, ServicePresets, TestMonitoringTypes) que foram substituidas pelo sistema dinamico `DynamicMonitoringPage`. O processo garante que nenhuma dependencia seja quebrada e que os arquivos sejam completamente removidos do projeto.

**MUDANCAS v1.4.0**: Preservar endpoints bulk (register/deregister) para uso futuro, manter bulkDeleteServices no api.ts, corrigir caminhos dos testes em Tests/, remover referencia a diagnostico.ps1 (arquivo inexistente).

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
- `POST /bulk/register` - bulkRegister (preservado para importacao em massa futura)
- `DELETE /bulk/deregister` - bulkDeregister (preservado para limpeza em massa futura)

**Endpoints a REMOVER**:
- `GET /` - listServices
- `GET /catalog/names` - getServiceCatalogNames
- `GET /metadata/unique-values` - getMetadataUniqueValues
- `GET /search/by-metadata` - searchByMetadata
- `GET /{service_id}` - getService

### Analise de Dependencias

#### IMPACTO CRITICO

**ServiceGroups.tsx** (linha 95) navega para `/services?service=...`:

```typescript
const handleServiceClick = (serviceName: string) => {
  navigate(`/services?service=${encodeURIComponent(serviceName)}`);
};
```

**ACAO REQUERIDA**: REMOVER completamente esta funcionalidade de navegacao.

#### IMPACTO CRITICO - Dashboard.tsx (v1.3.0)

**Dashboard.tsx** (linhas 401-433) contem botoes que navegam para rotas que serao removidas:

```typescript
<Button onClick={() => navigate('/blackbox?create=true')}>Novo alvo Blackbox</Button>
<Button onClick={() => navigate('/services?create=true')}>Registrar servico</Button>
<Button onClick={() => navigate('/services')}>Ver todos os servicos</Button>
```

**ACAO REQUERIDA**: REMOVER ou REDIRECIONAR esses botoes para fluxos validos (DynamicMonitoringPage).

#### IMPACTO CRITICO - Testes em Tests/ (v1.3.0)

A pasta `Tests/` contem scripts de integracao que importam BlackboxManager e ServicePresetManager:
- `Tests/integration/test_phase1.py`
- `Tests/integration/test_phase2.py`
- `Tests/metadata/test_audit_fix.py`

**ACAO REQUERIDA**: Atualizar ou remover testes ANTES de mover modulos para obsolete/.

#### IMPACTO CRITICO - Scripts de Diagnostico (v1.4.0)

**scripts/development/analyze_react_complexity.py** (linhas 16-17):
- Le diretamente BlackboxTargets.tsx e Services.tsx

**ACAO REQUERIDA**: Atualizar este utilitario para nao referenciar arquivos deletados.

**NOTA v1.4.0**: Referencia a `diagnostico.ps1` removida - arquivo nao existe no projeto.

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

**EARS Format**: O sistema **DEVE** refatorar o arquivo `backend/api/services.py` mantendo endpoints CRUD e bulk usados ou preservados para uso futuro.

**IMPORTANTE**: Este arquivo NAO pode ser movido para obsolete/ porque eh usado por DynamicMonitoringPage e DynamicCRUDModal!

**Endpoints a MANTER**:
- `POST /` - createService (usado por DynamicCRUDModal)
- `PUT /{service_id}` - updateService (usado por DynamicCRUDModal)
- `DELETE /{service_id}` - deleteService (usado por DynamicMonitoringPage)
- `POST /bulk/register` - bulkRegister (preservado para importacao em massa futura)
- `DELETE /bulk/deregister` - bulkDeregister (preservado para limpeza em massa futura)

**Endpoints a REMOVER**:
- `GET /` - listServices
- `GET /catalog/names` - getServiceCatalogNames
- `GET /metadata/unique-values` - getMetadataUniqueValues
- `GET /search/by-metadata` - searchByMetadata
- `GET /{service_id}` - getService

**Justificativa**: Manter funcionalidade CRUD e bulk para uso atual e futuro do sistema dinamico.

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

**EARS Format**: O sistema **DEVE** remover metodos nao utilizados da API frontend, preservando CRUD e bulk.

**Metodos a REMOVER**:
- Todos os metodos de blackbox (createBlackboxGroup, listBlackboxGroups, etc)
- Todos os metodos de presets
- Metodos de listagem de services (listServices, getService, getServiceCatalogNames, etc)

**Metodos a MANTER**:
- createService
- updateService
- deleteService
- deregisterService
- bulkDeleteServices (preservado para operacoes em massa futuras)

### FR-011: Atualizar models.py do Backend

**EARS Format**: O sistema **DEVE** remover models nao utilizados do backend.

**IMPORTANTE**: O caminho correto eh `backend/api/models.py`, NAO `backend/models.py`.

**REMOVER**:
- BlackboxTarget
- BlackboxUpdateRequest
- BlackboxDeleteRequest

**MANTER**:
- ServiceCreateRequest (usado por createService)
- ServiceUpdateRequest (usado por updateService)

### FR-012: Atualizar Testes em Tests/ (v1.4.0)

**EARS Format**: O sistema **DEVE** atualizar ou remover testes que dependem de modulos obsoletos ANTES de mover para obsolete/.

**Detalhes**:
- Atualizar ou remover `Tests/integration/test_phase1.py` (importa BlackboxManager)
- Atualizar ou remover `Tests/integration/test_phase2.py` (importa BlackboxManager, ServicePresetManager)
- Atualizar ou remover `Tests/metadata/test_audit_fix.py` (importa ServicePresetManager)

**Justificativa**: Evitar quebra de testes ao mover modulos para obsolete/.

### FR-013: Remover Atalhos Quebrados do Dashboard.tsx (v1.3.0)

**EARS Format**: O sistema **DEVE** remover ou redirecionar botoes do Dashboard.tsx que navegam para rotas obsoletas.

**Botoes a REMOVER** (linhas 401-433):
```typescript
<Button onClick={() => navigate('/blackbox?create=true')}>Novo alvo Blackbox</Button>
<Button onClick={() => navigate('/services?create=true')}>Registrar servico</Button>
<Button onClick={() => navigate('/services')}>Ver todos os servicos</Button>
```

**Alternativa**: Redirecionar para fluxos validos em DynamicMonitoringPage (ex: /monitoring/system-exporters).

**Justificativa**: Evitar navegacao para rotas que nao existem mais.

### FR-014: Atualizar Scripts de Diagnostico (v1.4.0)

**EARS Format**: O sistema **DEVE** atualizar scripts de diagnostico para nao referenciar arquivos removidos.

**Scripts a atualizar**:
- `scripts/development/analyze_react_complexity.py`: Remover leitura de BlackboxTargets.tsx e Services.tsx

**NOTA v1.4.0**: Referencia a `diagnostico.ps1` removida - arquivo nao existe no projeto.

**Justificativa**: Evitar falha de scripts ao procurar arquivos deletados.

### FR-015: REMOVIDO (v1.4.0)

**NOTA**: Este requisito foi removido na v1.4.0. O metodo `bulkDeleteServices` sera MANTIDO no api.ts para permitir operacoes em massa futuras, ja que os endpoints bulk tambem serao preservados em services.py.

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

### IR-006: Testes Nao Quebram (v1.3.0)

O sistema **NAO DEVERA** ter testes quebrados por import error apos mover modulos para obsolete/.

**Validacao**:
- Executar testes em Tests/
- Nenhum ImportError relacionado a BlackboxManager ou ServicePresetManager

### IR-007: Dashboard Sem Atalhos Quebrados (v1.3.0)

O sistema **NAO DEVERA** ter botoes no Dashboard que navegam para rotas obsoletas.

**Validacao**:
- Nenhum botao navega para /blackbox ou /services
- Ou botoes redirecionam para fluxos validos

### IR-008: Scripts de Diagnostico Funcionam (v1.3.0)

O sistema **NAO DEVERA** ter scripts de diagnostico que falham por arquivo nao encontrado.

**Validacao**:
- diagnostico.ps1 executa sem erros
- analyze_react_complexity.py executa sem erros

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
| `frontend/src/pages/Dashboard.tsx` | REMOVER botoes que navegam para /blackbox e /services | Medio |
| `frontend/src/services/api.ts` | Remover metodos nao utilizados (manter bulkDeleteServices) | Baixo |

### Testes e Scripts - Modificacoes (v1.4.0)

| Arquivo | Modificacao | Risco |
|---------|-------------|-------|
| `Tests/integration/test_phase1.py` | Atualizar/remover imports de BlackboxManager | Alto |
| `Tests/integration/test_phase2.py` | Atualizar/remover imports de BlackboxManager/ServicePresetManager | Alto |
| `Tests/metadata/test_audit_fix.py` | Atualizar/remover imports de ServicePresetManager | Alto |
| `scripts/development/analyze_react_complexity.py` | Remover leitura de arquivos deletados | Baixo |

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
| `backend/api/models.py` | Remover models de blackbox | Baixo |

**NOTA v1.3.0**: Caminho correto eh `backend/api/models.py`, NAO `backend/models.py`.

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
| Testes em Tests/ quebrados (v1.3.0) | Alta | Alto | Atualizar testes ANTES de mover modulos |
| Dashboard com atalhos quebrados (v1.3.0) | Alta | Medio | Remover botoes ou redirecionar |
| Scripts diagnostico falham (v1.3.0) | Media | Baixo | Atualizar scripts antes de deletar arquivos |
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

1. **Ordem de execucao v1.4.0**: Preparar testes/scripts PRIMEIRO, depois REFATORAR services.py, limpar Dashboard.tsx e App.tsx, DELETAR arquivos frontend, MOVER backend APIs
2. **Commits atomicos**: Um commit por fase para facilitar rollback
3. **Build continuo**: Validar build apos cada modificacao
4. **DELETAR completamente**: NAO usar .old-deprecated, DELETAR do frontend
5. **Backend services.py**: REFATORAR, NAO mover para obsolete/
6. **Testar CRUD e Bulk**: Verificar createService, updateService, deleteService, bulkRegister, bulkDeregister apos refatoracao
7. **Caminho models.py**: Usar `backend/api/models.py`, NAO `backend/models.py`
8. **MANTER bulkDeleteServices**: Preservar no api.ts para operacoes em massa futuras
9. **Caminhos Tests/**: Usar caminhos corretos em Tests/integration/ e Tests/metadata/

---

## Tags de Rastreabilidade

<!-- TAG_BLOCK_START -->
- [SPEC-CLEANUP-001] Especificacao de remocao de paginas obsoletas v1.4.0
- [FR-001] DELETAR paginas obsoletas do frontend (6 paginas + 1 hook)
- [FR-002] Remover imports no App.tsx (5 imports)
- [FR-003] Remover rotas no App.tsx (5 rotas)
- [FR-004] Remover itens de menu (5 items)
- [FR-005] REMOVER navegacao ServiceGroups
- [FR-006] Preservar componentes compartilhados
- [FR-007] REFATORAR services.py (manter CRUD + bulk)
- [FR-008] Mover APIs backend para obsolete
- [FR-009] Atualizar app.py do backend
- [FR-010] Atualizar api.ts do frontend (manter bulkDeleteServices)
- [FR-011] Atualizar backend/api/models.py
- [FR-012] Atualizar testes em Tests/ (v1.4.0 - caminhos corrigidos)
- [FR-013] Remover atalhos Dashboard.tsx
- [FR-014] Atualizar scripts de diagnostico (v1.4.0 - sem diagnostico.ps1)
- [FR-015] REMOVIDO (bulkDeleteServices sera mantido)
<!-- TAG_BLOCK_END -->
