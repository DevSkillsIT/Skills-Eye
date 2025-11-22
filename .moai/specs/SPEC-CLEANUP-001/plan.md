---
id: SPEC-CLEANUP-001
version: "1.2.0"
status: draft
created: 2025-11-21
updated: 2025-11-21
author: Claude Code
type: implementation-plan
---

# Plano de Implementacao - SPEC-CLEANUP-001

## Visao Geral

Este plano detalha as etapas para remocao completa das paginas obsoletas do projeto Skills-Eye, garantindo zero quebra de funcionalidade e limpeza total do codigo morto. **MUDANCA CRITICA**: services.py deve ser REFATORADO, NAO removido, pois endpoints CRUD sao usados por DynamicMonitoringPage e DynamicCRUDModal.

---

## Milestones por Prioridade

### Milestone 1: REFATORAR services.py do Backend (Prioridade: CRITICA)

**Objetivo**: Manter apenas endpoints CRUD usados por paginas ativas

**IMPORTANTE**: Este passo DEVE ser executado PRIMEIRO para garantir que funcionalidade critica nao seja perdida!

**Tarefas**:

1. **Identificar endpoints a MANTER**
   - `POST /` - createService (usado por DynamicCRUDModal)
   - `PUT /{service_id}` - updateService (usado por DynamicCRUDModal)
   - `DELETE /{service_id}` - deleteService (usado por DynamicMonitoringPage)

2. **Identificar endpoints a REMOVER**
   - `GET /` - listServices
   - `GET /catalog/names` - getServiceCatalogNames
   - `GET /metadata/unique-values` - getMetadataUniqueValues
   - `GET /search/by-metadata` - searchByMetadata
   - `GET /{service_id}` - getService
   - `POST /bulk/register` - bulkRegister
   - `DELETE /bulk/deregister` - bulkDeregister

3. **Refatorar o arquivo**
   - Remover funcoes dos endpoints a excluir
   - Manter estrutura do router
   - Manter imports necessarios

**Arquivos modificados**:
- `backend/api/services.py`

**Validacao**:
- [ ] Backend inicia sem erros
- [ ] POST / funciona
- [ ] PUT /{id} funciona
- [ ] DELETE /{id} funciona
- [ ] Endpoints removidos retornam 404

---

### Milestone 2: REMOVER Navegacao do ServiceGroups (Prioridade: ALTA)

**Objetivo**: Eliminar completamente a funcionalidade de clique em servicos

**Tarefas**:

1. **Localizar codigo de navegacao em ServiceGroups.tsx**
   - Encontrar funcao `handleServiceClick` (linha 93-96)
   - Identificar onde onClick eh usado nos elementos de servico

2. **REMOVER funcao handleServiceClick**
   ```typescript
   // REMOVER COMPLETAMENTE
   const handleServiceClick = (serviceName: string) => {
     navigate(`/services?service=${encodeURIComponent(serviceName)}`);
   };
   ```

3. **REMOVER onClick handlers**
   - Remover onClick dos elementos que chamam handleServiceClick
   - Manter apenas visualizacao estatica dos servicos

4. **Remover import de useNavigate** (se nao usado em outro lugar)

**Arquivos modificados**:
- `frontend/src/pages/ServiceGroups.tsx`

**Validacao**:
- [ ] Build passa
- [ ] Clique em servico nao causa navegacao
- [ ] Nao ha erros no console

---

### Milestone 3: Limpeza do App.tsx (Prioridade: ALTA)

**Objetivo**: Remover imports, rotas e itens de menu das paginas obsoletas

**Tarefas**:

1. **Remover imports (5)**
   ```typescript
   // REMOVER estas linhas
   import Services from './pages/Services';
   import Exporters from './pages/Exporters';
   import BlackboxTargets from './pages/BlackboxTargets';
   import BlackboxGroups from './pages/BlackboxGroups';
   import ServicePresets from './pages/ServicePresets';
   ```

2. **Remover rotas (5)**
   ```typescript
   // REMOVER estas Route
   <Route path="/services" element={<Services />} />
   <Route path="/exporters" element={<Exporters />} />
   <Route path="/blackbox" element={<BlackboxTargets />} />
   <Route path="/blackbox-groups" element={<BlackboxGroups />} />
   <Route path="/presets" element={<ServicePresets />} />
   ```

3. **Remover itens de menu (5)**
   - Localizar estrutura de menu no App.tsx
   - Remover item "Services"
   - Remover item "Exporters"
   - Remover item "Alvos Blackbox"
   - Remover item "Grupos Blackbox"
   - Remover item "Presets de Servicos"

4. **Verificar outros imports**
   - Buscar por referencias residuais
   - Limpar imports nao utilizados

**Arquivos modificados**:
- `frontend/src/App.tsx`

**Validacao**:
- [ ] Build passa sem erros
- [ ] ESLint sem warnings de imports
- [ ] Menu renderiza corretamente

---

### Milestone 4: DELETAR Paginas do Frontend (Prioridade: MEDIA)

**Objetivo**: Remover completamente os arquivos de paginas obsoletas

**Tarefas**:

1. **DELETAR Services.tsx**
   ```bash
   git rm frontend/src/pages/Services.tsx
   ```

2. **DELETAR Exporters.tsx**
   ```bash
   git rm frontend/src/pages/Exporters.tsx
   ```

3. **DELETAR BlackboxTargets.tsx**
   ```bash
   git rm frontend/src/pages/BlackboxTargets.tsx
   ```

4. **DELETAR BlackboxGroups.tsx**
   ```bash
   git rm frontend/src/pages/BlackboxGroups.tsx
   ```

5. **DELETAR ServicePresets.tsx**
   ```bash
   git rm frontend/src/pages/ServicePresets.tsx
   ```

6. **DELETAR TestMonitoringTypes.tsx**
   ```bash
   git rm frontend/src/pages/TestMonitoringTypes.tsx
   ```

**Arquivos DELETADOS**:
- `frontend/src/pages/Services.tsx`
- `frontend/src/pages/Exporters.tsx`
- `frontend/src/pages/BlackboxTargets.tsx`
- `frontend/src/pages/BlackboxGroups.tsx`
- `frontend/src/pages/ServicePresets.tsx`
- `frontend/src/pages/TestMonitoringTypes.tsx`

**Validacao**:
- [ ] Arquivos nao existem mais
- [ ] Build ainda passa

---

### Milestone 5: DELETAR Hook Exclusivo (Prioridade: MEDIA)

**Objetivo**: Remover hook que era usado apenas nas paginas deletadas

**Tarefas**:

1. **Verificar que useMonitoringType.ts NAO eh usado em outro lugar**
   ```bash
   grep -r "useMonitoringType" frontend/src --include="*.ts" --include="*.tsx"
   ```

2. **DELETAR useMonitoringType.ts**
   ```bash
   git rm frontend/src/hooks/useMonitoringType.ts
   ```

**Arquivos DELETADOS**:
- `frontend/src/hooks/useMonitoringType.ts`

**Validacao**:
- [ ] Nenhum erro de import
- [ ] Build passa

---

### Milestone 6: Atualizar api.ts do Frontend (Prioridade: MEDIA)

**Objetivo**: Remover metodos nao utilizados da API frontend

**Tarefas**:

1. **Remover metodos de blackbox**
   - createBlackboxGroup
   - listBlackboxGroups
   - getBlackboxGroup
   - updateBlackboxGroup
   - deleteBlackboxGroup
   - Todos outros metodos de blackbox

2. **Remover metodos de presets**
   - Todos metodos relacionados a presets

3. **Remover metodos de listagem de services**
   - listServices
   - getService
   - getServiceCatalogNames
   - getMetadataUniqueValues
   - searchByMetadata

4. **MANTER metodos CRUD de services**
   - createService
   - updateService
   - deleteService
   - deregisterService

**Arquivos modificados**:
- `frontend/src/services/api.ts`

**Validacao**:
- [ ] Build passa
- [ ] DynamicMonitoringPage funciona
- [ ] DynamicCRUDModal funciona

---

### Milestone 7: Atualizar app.py do Backend (Prioridade: MEDIA)

**Objetivo**: Remover imports e include_router das APIs movidas

**Tarefas**:

1. **Remover imports**
   ```python
   # REMOVER estas linhas
   from api.blackbox import router as blackbox_router
   from api.presets import router as presets_router
   ```

2. **Remover include_router**
   ```python
   # REMOVER estas linhas
   app.include_router(blackbox_router, prefix="/api/v1/blackbox", tags=["Blackbox"])
   app.include_router(presets_router, prefix="/api/v1/presets", tags=["Service Presets"])
   ```

3. **MANTER services_router** (endpoints CRUD ainda em uso)
   ```python
   # NAO REMOVER
   from api.services import router as services_router
   app.include_router(services_router, prefix="/api/v1/services", tags=["Services"])
   ```

**Arquivos modificados**:
- `backend/app.py`

**Validacao**:
- [ ] Backend inicia sem erros
- [ ] APIs de services funcionam

---

### Milestone 8: Atualizar models.py do Backend (Prioridade: BAIXA)

**Objetivo**: Remover models nao utilizados

**Tarefas**:

1. **REMOVER models de blackbox**
   - BlackboxTarget
   - BlackboxUpdateRequest
   - BlackboxDeleteRequest

2. **MANTER models de services**
   - ServiceCreateRequest (usado por createService)
   - ServiceUpdateRequest (usado por updateService)

**Arquivos modificados**:
- `backend/models.py`

**Validacao**:
- [ ] Backend inicia sem erros
- [ ] Nenhum import quebrado

---

### Milestone 9: Mover APIs Backend para obsolete/ (Prioridade: MEDIA)

**Objetivo**: Preservar APIs backend em pasta separada para referencia

**IMPORTANTE**: services.py NAO sera movido - apenas REFATORADO no Milestone 1!

**Tarefas**:

1. **Criar estrutura de pastas**
   ```bash
   mkdir -p obsolete/backend_api
   mkdir -p obsolete/backend_core
   ```

2. **Mover arquivos de API** (exceto services.py)
   ```bash
   git mv backend/api/services_optimized.py obsolete/backend_api/services_optimized.py
   git mv backend/api/blackbox.py obsolete/backend_api/blackbox.py
   git mv backend/api/presets.py obsolete/backend_api/presets.py
   ```

3. **Mover arquivos core**
   ```bash
   git mv backend/core/blackbox_manager.py obsolete/backend_core/blackbox_manager.py
   git mv backend/core/service_preset_manager.py obsolete/backend_core/service_preset_manager.py
   ```

**Arquivos movidos**:
- `backend/api/services_optimized.py` → `obsolete/backend_api/services_optimized.py`
- `backend/api/blackbox.py` → `obsolete/backend_api/blackbox.py`
- `backend/api/presets.py` → `obsolete/backend_api/presets.py`
- `backend/core/blackbox_manager.py` → `obsolete/backend_core/blackbox_manager.py`
- `backend/core/service_preset_manager.py` → `obsolete/backend_core/service_preset_manager.py`

**Validacao**:
- [ ] Backend inicia sem erros
- [ ] Nenhum import quebrado
- [ ] APIs ativas ainda funcionam

---

### Milestone 10: Validacao Final (Prioridade: CRITICA)

**Objetivo**: Garantir que o sistema funciona corretamente

**Tarefas**:

1. **Build completo frontend**
   ```bash
   cd frontend && npm run build
   ```

2. **Testes automatizados frontend**
   ```bash
   cd frontend && npm test
   ```

3. **Iniciar backend**
   ```bash
   cd backend && python app.py
   ```

4. **Testar CRUD de services**
   - Verificar createService em DynamicCRUDModal
   - Verificar updateService em DynamicCRUDModal
   - Verificar deleteService em DynamicMonitoringPage

5. **Testes manuais de navegacao**
   - Verificar menu de monitoramento
   - Navegar por todas as paginas restantes
   - Verificar console para erros

6. **Verificar rotas 404**
   - Acessar /services manualmente → deve dar 404
   - Acessar /exporters manualmente → deve dar 404
   - Acessar /blackbox manualmente → deve dar 404
   - Acessar /blackbox-groups manualmente → deve dar 404
   - Acessar /presets manualmente → deve dar 404

7. **Verificar ServiceGroups**
   - Navegar para ServiceGroups
   - Clicar em um servico
   - Confirmar que NAO navega para lugar nenhum
   - Verificar que nao ha erros no console

8. **Verificar arquivos deletados**
   ```bash
   # Confirmar que arquivos NAO existem
   ls frontend/src/pages/Services.tsx 2>/dev/null && echo "ERRO" || echo "OK - deletado"
   ls frontend/src/pages/BlackboxGroups.tsx 2>/dev/null && echo "ERRO" || echo "OK - deletado"
   ```

**Validacao**:
- [ ] Build sem erros
- [ ] Testes passando
- [ ] Backend rodando
- [ ] CRUD de services funciona
- [ ] Navegacao funcionando
- [ ] Console limpo
- [ ] ServiceGroups sem navegacao em clique
- [ ] Arquivos realmente deletados

---

## Abordagem Tecnica

### Estrategia de Git

1. **Branch dedicada**: `feature/SPEC-CLEANUP-001`
2. **Commits atomicos**: Um commit por milestone
3. **Mensagens descritivas**: Seguir padrao do projeto

**Exemplo de commits**:
```bash
git commit -m "refactor(services): manter apenas endpoints CRUD em services.py"
git commit -m "fix(servicegroups): remover funcionalidade de navegacao ao clicar em servico"
git commit -m "refactor(app): remover imports e rotas de paginas obsoletas"
git commit -m "chore(cleanup): deletar paginas obsoletas do frontend"
git commit -m "chore(cleanup): deletar hook exclusivo useMonitoringType"
git commit -m "refactor(api): remover metodos nao utilizados do api.ts"
git commit -m "refactor(backend): atualizar app.py removendo routers obsoletos"
git commit -m "refactor(models): remover models de blackbox"
git commit -m "chore(cleanup): mover APIs backend obsoletas para obsolete/"
```

### Ordem de Execucao

```
[Milestone 1] → [Milestone 2] → [Milestone 3] → [Milestone 4] → [Milestone 5]
     |              |              |              |              |
  REFATORAR      REMOVER       Limpar App     DELETAR        DELETAR
 services.py   ServiceGroups     .tsx         Paginas         Hook

     ↓
[Milestone 6] → [Milestone 7] → [Milestone 8] → [Milestone 9] → [Milestone 10]
     |              |              |              |              |
  Atualizar     Atualizar      Atualizar       Mover APIs     Validar
   api.ts        app.py        models.py       Backend        Final
```

**IMPORTANTE**: NAO pular etapas. Cada milestone depende do anterior.

---

## Direcao de Arquitetura

### Principios Aplicados

1. **Refatoracao antes de remocao**: services.py eh refatorado, nao removido
2. **Remocao completa**: Deletar codigo morto, nao renomear
3. **Reversibilidade**: Cada etapa eh revertivel independentemente
4. **Minimo impacto**: Nao alterar codigo que funciona
5. **Preservacao seletiva**: Backend APIs vao para obsolete/ para referencia

### Decisoes Arquiteturais

| Decisao | Justificativa |
|---------|---------------|
| REFATORAR services.py | CRUD usado por DynamicMonitoringPage e DynamicCRUDModal |
| DELETAR paginas frontend | Remocao completa de codigo morto |
| Mover APIs para obsolete/ | Preservar para referencia sem poluir projeto |
| REMOVER navegacao ServiceGroups | Nao ha destino valido |
| Manter models de services | Usados por endpoints CRUD |

---

## Riscos e Plano de Contingencia

### Risco 1: CRUD de Services Quebrado (CRITICO)

**Sintoma**: DynamicMonitoringPage ou DynamicCRUDModal nao funciona

**Contingencia**:
1. Verificar refatoracao de services.py
2. Verificar api.ts mantem metodos CRUD
3. Testar cada endpoint individualmente
4. Reverter commit se necessario: `git revert HEAD`

### Risco 2: Build Falha Apos Delecao

**Sintoma**: Erro de import ou componente nao encontrado

**Contingencia**:
1. Verificar todos imports no arquivo com erro
2. Buscar referencias residuais com grep
3. Reverter commit se necessario: `git revert HEAD`

### Risco 3: API Backend Usada por Outra Pagina

**Sintoma**: Erro ao iniciar backend ou funcionalidade quebrada

**Contingencia**:
1. Verificar TODOS imports antes de mover
2. Se tiver dependencia, NAO mover o arquivo
3. Documentar dependencia encontrada

### Risco 4: Menu Quebrado

**Sintoma**: Menu nao renderiza ou items faltando

**Contingencia**:
1. Verificar estrutura de menu no App.tsx
2. Comparar com versao anterior
3. Restaurar items necessarios

---

## Checklist Pre-Implementacao

- [ ] Branch `feature/SPEC-CLEANUP-001` criada
- [ ] Working directory limpo (git status)
- [ ] Build atual passa
- [ ] Backend inicia corretamente
- [ ] Entendimento claro de cada etapa
- [ ] **CRITICO**: Entender que services.py deve ser REFATORADO, NAO removido

---

## Checklist Pos-Implementacao

- [ ] services.py refatorado (apenas CRUD)
- [ ] Todos os 6 arquivos de pagina DELETADOS
- [ ] Hook useMonitoringType DELETADO
- [ ] App.tsx limpo de referencias
- [ ] ServiceGroups sem navegacao em clique
- [ ] api.ts atualizado (metodos removidos)
- [ ] app.py atualizado (routers removidos)
- [ ] models.py atualizado (models removidos)
- [ ] APIs backend movidas para obsolete/
- [ ] CRUD de services funciona
- [ ] Build frontend passa
- [ ] Backend inicia sem erros
- [ ] Testes passam
- [ ] Console limpo
- [ ] Menu funcionando
- [ ] Rotas antigas retornam 404
- [ ] Commits feitos e organizados
- [ ] PR criado (se aplicavel)

---

## Tags de Rastreabilidade

<!-- TAG_BLOCK_START -->
- [SPEC-CLEANUP-001] Plano de implementacao
- [MILESTONE-1] REFATORAR services.py (CRUD apenas)
- [MILESTONE-2] REMOVER navegacao ServiceGroups
- [MILESTONE-3] Limpeza do App.tsx
- [MILESTONE-4] DELETAR paginas do frontend (6)
- [MILESTONE-5] DELETAR hook exclusivo
- [MILESTONE-6] Atualizar api.ts
- [MILESTONE-7] Atualizar app.py
- [MILESTONE-8] Atualizar models.py
- [MILESTONE-9] Mover APIs backend para obsolete
- [MILESTONE-10] Validacao final
<!-- TAG_BLOCK_END -->
