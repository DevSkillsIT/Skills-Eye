---
id: SPEC-CLEANUP-001
version: "1.4.0"
status: draft
created: 2025-11-21
updated: 2025-11-22
author: Claude Code
type: implementation-plan
---

# Plano de Implementacao - SPEC-CLEANUP-001

## Visao Geral

Este plano detalha as etapas para remocao completa das paginas obsoletas do projeto Skills-Eye, garantindo zero quebra de funcionalidade e limpeza total do codigo morto. **MUDANCA CRITICA**: services.py deve ser REFATORADO, NAO removido, pois endpoints CRUD e bulk sao usados ou preservados para uso futuro.

**MUDANCAS v1.4.0**:
- Endpoints bulk (POST /bulk/register, DELETE /bulk/deregister) agora serao MANTIDOS
- bulkDeleteServices no api.ts sera MANTIDO para operacoes em massa futuras
- Caminhos de testes corrigidos (Tests/integration/, Tests/metadata/)
- Referencia a diagnostico.ps1 removida (arquivo nao existe)
- Milestone 0, 1, 6, 10 atualizados com novas preservacoes

---

## Milestones por Prioridade

### Milestone 0: Preparacao - Testes e Scripts (Prioridade: CRITICA) [v1.4.0]

**Objetivo**: Atualizar ou remover testes e scripts que dependem de modulos obsoletos ANTES de qualquer remocao

**IMPORTANTE**: Este passo DEVE ser executado PRIMEIRO para evitar quebra de testes ao mover modulos para obsolete/!

**Tarefas**:

1. **Atualizar/remover testes em Tests/**
   - Verificar `Tests/integration/test_phase1.py` - importa BlackboxManager
   - Verificar `Tests/integration/test_phase2.py` - importa BlackboxManager, ServicePresetManager
   - Verificar `Tests/metadata/test_audit_fix.py` - importa ServicePresetManager
   - Listar todos arquivos em Tests/ que importam modulos obsoletos
   ```bash
   grep -r "BlackboxManager\|ServicePresetManager" Tests/ --include="*.py"
   ```

2. **Decidir acao para cada teste**
   - Se teste pode ser atualizado → atualizar imports e logica
   - Se teste nao faz mais sentido → remover arquivo
   - Documentar decisao para cada arquivo

3. **Atualizar scripts/development/analyze_react_complexity.py**
   - Remover leitura de BlackboxTargets.tsx (linhas 16-17)
   - Remover leitura de Services.tsx
   - Atualizar lista de arquivos analisados

**NOTA v1.4.0**: Referencia a `diagnostico.ps1` removida - arquivo nao existe no projeto.

**Arquivos modificados**:
- `Tests/integration/test_phase1.py` (atualizar ou remover)
- `Tests/integration/test_phase2.py` (atualizar ou remover)
- `Tests/metadata/test_audit_fix.py` (atualizar ou remover)
- `scripts/development/analyze_react_complexity.py` (atualizar)

**Validacao**:
- [ ] Nenhum teste importa BlackboxManager
- [ ] Nenhum teste importa ServicePresetManager
- [ ] analyze_react_complexity.py nao le arquivos que serao deletados
- [ ] Scripts executam sem erros

---

### Milestone 1: REFATORAR services.py do Backend (Prioridade: CRITICA)

**Objetivo**: Manter endpoints CRUD e bulk usados ou preservados para uso futuro

**IMPORTANTE**: Este passo DEVE ser executado PRIMEIRO para garantir que funcionalidade critica nao seja perdida!

**Tarefas**:

1. **Identificar endpoints a MANTER**
   - `POST /` - createService (usado por DynamicCRUDModal)
   - `PUT /{service_id}` - updateService (usado por DynamicCRUDModal)
   - `DELETE /{service_id}` - deleteService (usado por DynamicMonitoringPage)
   - `POST /bulk/register` - bulkRegister (preservado para importacao em massa futura)
   - `DELETE /bulk/deregister` - bulkDeregister (preservado para limpeza em massa futura)

2. **Identificar endpoints a REMOVER**
   - `GET /` - listServices
   - `GET /catalog/names` - getServiceCatalogNames
   - `GET /metadata/unique-values` - getMetadataUniqueValues
   - `GET /search/by-metadata` - searchByMetadata
   - `GET /{service_id}` - getService

3. **Refatorar o arquivo**
   - Remover funcoes dos endpoints GET
   - Manter estrutura do router
   - Manter imports necessarios
   - Manter endpoints bulk para uso futuro

**Arquivos modificados**:
- `backend/api/services.py`

**Validacao**:
- [ ] Backend inicia sem erros
- [ ] POST / funciona
- [ ] PUT /{id} funciona
- [ ] DELETE /{id} funciona
- [ ] POST /bulk/register funciona
- [ ] DELETE /bulk/deregister funciona
- [ ] Endpoints GET removidos retornam 404

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

### Milestone 2.1: Dashboard.tsx - Remover Atalhos Quebrados (Prioridade: ALTA) [v1.3.0]

**Objetivo**: Remover ou redirecionar botoes que navegam para rotas obsoletas

**Tarefas**:

1. **Localizar botoes em Dashboard.tsx** (linhas 401-433)
   ```typescript
   // IDENTIFICAR ESTES BOTOES
   <Button onClick={() => navigate('/blackbox?create=true')}>Novo alvo Blackbox</Button>
   <Button onClick={() => navigate('/services?create=true')}>Registrar servico</Button>
   <Button onClick={() => navigate('/services')}>Ver todos os servicos</Button>
   ```

2. **Opcao A: REMOVER botoes** (recomendado se funcionalidade nao faz mais sentido)
   - Deletar completamente os botoes
   - Ajustar layout se necessario

3. **Opcao B: REDIRECIONAR botoes** (se funcionalidade ainda faz sentido)
   - Redirecionar para DynamicMonitoringPage equivalente
   - Exemplo: `/services` → `/monitoring/system-exporters`
   - Exemplo: `/blackbox` → `/monitoring/network-probes`

4. **Atualizar imports** (se necessario)
   - Remover imports nao utilizados apos remocao

**Arquivos modificados**:
- `frontend/src/pages/Dashboard.tsx`

**Validacao**:
- [ ] Build passa
- [ ] Dashboard renderiza corretamente
- [ ] Nenhum botao navega para /services ou /blackbox
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

**Objetivo**: Remover metodos nao utilizados da API frontend, preservando CRUD e bulk

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

4. **MANTER metodos CRUD e bulk de services**
   - createService
   - updateService
   - deleteService
   - deregisterService
   - **bulkDeleteServices** (preservado para operacoes em massa futuras) [v1.4.0]

**Arquivos modificados**:
- `frontend/src/services/api.ts`

**Validacao**:
- [ ] Build passa
- [ ] DynamicMonitoringPage funciona
- [ ] DynamicCRUDModal funciona
- [ ] bulkDeleteServices esta disponivel para uso futuro

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

**IMPORTANTE v1.3.0**: O caminho correto eh `backend/api/models.py`, NAO `backend/models.py`!

**Tarefas**:

1. **REMOVER models de blackbox**
   - BlackboxTarget
   - BlackboxUpdateRequest
   - BlackboxDeleteRequest

2. **MANTER models de services**
   - ServiceCreateRequest (usado por createService)
   - ServiceUpdateRequest (usado por updateService)

**Arquivos modificados**:
- `backend/api/models.py` (caminho correto!)

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

8. **Verificar Dashboard** [v1.3.0]
   - Navegar para Dashboard
   - Confirmar que NAO ha botoes para /services ou /blackbox
   - Verificar que nao ha erros no console

9. **Verificar testes em Tests/** [v1.4.0]
   ```bash
   # Executar testes atualizados
   python -m pytest Tests/ -v
   ```

10. **Verificar scripts de diagnostico** [v1.4.0]
    ```bash
    # Executar script e verificar que nao falha
    python scripts/development/analyze_react_complexity.py
    ```

11. **Verificar endpoints bulk funcionam** [v1.4.0]
    ```bash
    # Verificar que endpoints bulk estao acessiveis
    curl -X POST http://localhost:8000/api/v1/services/bulk/register -d '[]'
    curl -X DELETE http://localhost:8000/api/v1/services/bulk/deregister -d '[]'
    ```

12. **Verificar arquivos deletados**
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
- [ ] Endpoints bulk funcionam [v1.4.0]
- [ ] Navegacao funcionando
- [ ] Console limpo
- [ ] ServiceGroups sem navegacao em clique
- [ ] Dashboard sem atalhos quebrados
- [ ] Testes em Tests/ passam
- [ ] Scripts de diagnostico funcionam
- [ ] Arquivos realmente deletados
- [ ] bulkDeleteServices disponivel no api.ts [v1.4.0]

---

## Abordagem Tecnica

### Estrategia de Git

1. **Branch dedicada**: `feature/SPEC-CLEANUP-001`
2. **Commits atomicos**: Um commit por milestone
3. **Mensagens descritivas**: Seguir padrao do projeto

**Exemplo de commits**:
```bash
git commit -m "chore(tests): atualizar testes e scripts para remocao de modulos obsoletos"
git commit -m "refactor(services): manter endpoints CRUD e bulk em services.py"
git commit -m "fix(servicegroups): remover funcionalidade de navegacao ao clicar em servico"
git commit -m "fix(dashboard): remover atalhos para rotas obsoletas"
git commit -m "refactor(app): remover imports e rotas de paginas obsoletas"
git commit -m "chore(cleanup): deletar paginas obsoletas do frontend"
git commit -m "chore(cleanup): deletar hook exclusivo useMonitoringType"
git commit -m "refactor(api): remover metodos nao utilizados do api.ts (manter bulkDeleteServices)"
git commit -m "refactor(backend): atualizar app.py removendo routers obsoletos"
git commit -m "refactor(models): remover models de blackbox em backend/api/models.py"
git commit -m "chore(cleanup): mover APIs backend obsoletas para obsolete/"
```

### Ordem de Execucao (v1.4.0)

```
[Milestone 0] → [Milestone 1] → [Milestone 2] → [Milestone 2.1] → [Milestone 3]
     |              |              |               |                  |
 Preparacao     REFATORAR      REMOVER        Dashboard.tsx      Limpar App
Testes/Scripts services.py   ServiceGroups   Atalhos             .tsx
              (CRUD+bulk)

     ↓
[Milestone 4] → [Milestone 5] → [Milestone 6] → [Milestone 7] → [Milestone 8]
     |              |              |              |              |
  DELETAR        DELETAR      Atualizar      Atualizar       Atualizar
  Paginas         Hook        api.ts         app.py       api/models.py
                          (manter bulk)

     ↓
[Milestone 9] → [Milestone 10]
     |              |
  Mover APIs      Validar
   Backend        Final
```

**IMPORTANTE**: NAO pular etapas. Milestone 0 DEVE ser executado PRIMEIRO para evitar quebra de testes!

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
| Preparar testes/scripts PRIMEIRO | Evitar quebra de testes ao mover modulos |
| REFATORAR services.py (CRUD + bulk) | CRUD usado por DynamicMonitoringPage e DynamicCRUDModal, bulk preservado para uso futuro |
| MANTER endpoints bulk [v1.4.0] | Preservar funcoes de registro em massa para importacao/automacao futura |
| MANTER bulkDeleteServices [v1.4.0] | Preservar no frontend para operacoes em massa futuras |
| REMOVER atalhos Dashboard.tsx | Evitar navegacao para rotas inexistentes |
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

### Risco 5: Testes Quebrados por Import Error [v1.3.0]

**Sintoma**: Testes em Tests/ falham ao importar BlackboxManager ou ServicePresetManager

**Contingencia**:
1. Verificar se Milestone 0 foi executado
2. Atualizar ou remover testes que importam modulos obsoletos
3. Executar testes novamente

### Risco 6: Dashboard com Atalhos Quebrados [v1.3.0]

**Sintoma**: Clique em botao no Dashboard navega para rota 404

**Contingencia**:
1. Verificar se Milestone 2.1 foi executado
2. Remover ou redirecionar botoes problematicos
3. Atualizar layout se necessario

---

## Checklist Pre-Implementacao

- [ ] Branch `feature/SPEC-CLEANUP-001` criada
- [ ] Working directory limpo (git status)
- [ ] Build atual passa
- [ ] Backend inicia corretamente
- [ ] Entendimento claro de cada etapa
- [ ] **CRITICO**: Entender que services.py deve ser REFATORADO, NAO removido
- [ ] **CRITICO**: Entender que Milestone 0 (testes/scripts) deve ser PRIMEIRO
- [ ] **CRITICO**: Caminho correto eh `backend/api/models.py`
- [ ] **CRITICO v1.4.0**: Entender que endpoints bulk e bulkDeleteServices serao MANTIDOS

---

## Checklist Pos-Implementacao

- [ ] Testes em Tests/ atualizados/removidos
- [ ] Scripts de diagnostico atualizados
- [ ] services.py refatorado (CRUD + bulk mantidos)
- [ ] Todos os 6 arquivos de pagina DELETADOS
- [ ] Hook useMonitoringType DELETADO
- [ ] App.tsx limpo de referencias
- [ ] ServiceGroups sem navegacao em clique
- [ ] Dashboard sem atalhos quebrados
- [ ] api.ts atualizado (metodos removidos, bulkDeleteServices MANTIDO) [v1.4.0]
- [ ] app.py atualizado (routers removidos)
- [ ] backend/api/models.py atualizado (models removidos)
- [ ] APIs backend movidas para obsolete/
- [ ] CRUD de services funciona
- [ ] Endpoints bulk funcionam [v1.4.0]
- [ ] Build frontend passa
- [ ] Backend inicia sem erros
- [ ] Testes em Tests/ passam
- [ ] Console limpo
- [ ] Menu funcionando
- [ ] Rotas GET antigas retornam 404
- [ ] Commits feitos e organizados
- [ ] PR criado (se aplicavel)

---

## Tags de Rastreabilidade

<!-- TAG_BLOCK_START -->
- [SPEC-CLEANUP-001] Plano de implementacao v1.4.0
- [MILESTONE-0] Preparacao - Testes e Scripts (caminhos corrigidos)
- [MILESTONE-1] REFATORAR services.py (CRUD + bulk mantidos)
- [MILESTONE-2] REMOVER navegacao ServiceGroups
- [MILESTONE-2.1] Dashboard.tsx - Remover atalhos quebrados
- [MILESTONE-3] Limpeza do App.tsx
- [MILESTONE-4] DELETAR paginas do frontend (6)
- [MILESTONE-5] DELETAR hook exclusivo
- [MILESTONE-6] Atualizar api.ts (manter bulkDeleteServices)
- [MILESTONE-7] Atualizar app.py
- [MILESTONE-8] Atualizar backend/api/models.py
- [MILESTONE-9] Mover APIs backend para obsolete
- [MILESTONE-10] Validacao final (incluir endpoints bulk)
<!-- TAG_BLOCK_END -->
