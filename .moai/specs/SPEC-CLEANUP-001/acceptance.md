---
id: SPEC-CLEANUP-001
version: "1.4.0"
status: completed
created: 2025-11-21
updated: 2025-11-22
author: Claude Code
type: acceptance-criteria
---

# Criterios de Aceitacao - SPEC-CLEANUP-001

## Visao Geral

Este documento define os criterios de aceitacao detalhados para a remocao completa das paginas obsoletas do projeto Skills-Eye, com cenarios de teste em formato Given-When-Then. **MUDANCA CRITICA v1.2.0**: services.py deve ser REFATORADO (nao removido) e BlackboxGroups.tsx foi adicionado a lista de remocao.

**MUDANCAS v1.4.0**:
- Endpoints bulk (POST /bulk/register, DELETE /bulk/deregister) agora serao MANTIDOS
- bulkDeleteServices no api.ts sera MANTIDO para operacoes em massa futuras
- Cenario 14 atualizado: endpoints bulk NAO devem retornar 404
- Cenario 18 atualizado: diagnostico.ps1 removido (nao existe)
- Cenario 19 atualizado: validar que bulkDeleteServices esta MANTIDO
- Caminhos de testes corrigidos para Tests/integration/ e Tests/metadata/

---

## Cenarios de Teste

### Cenario 1: Menu Sem Paginas Desativadas

**Objetivo**: Validar que o menu nao exibe as paginas desativadas

```gherkin
DADO que o usuario esta autenticado no sistema
QUANDO acessar o menu de navegacao principal
ENTAO NAO deve ver o item "Services"
E NAO deve ver o item "Exporters"
E NAO deve ver o item "Alvos Blackbox"
E NAO deve ver o item "Grupos Blackbox"
E NAO deve ver o item "Presets de Servicos"
E deve ver apenas os itens de menu validos
```

**Passos de teste**:
1. Abrir aplicacao em http://localhost:5173
2. Clicar no menu lateral
3. Expandir secao "Monitoramento"
4. Verificar items visiveis

**Resultado esperado**: Apenas paginas ativas aparecem no menu

---

### Cenario 2: ServiceGroups NAO Navega ao Clicar em Servico

**Objetivo**: Validar que clicar em servico no ServiceGroups NAO causa navegacao

```gherkin
DADO que o usuario esta na pagina ServiceGroups
E existe pelo menos um grupo de servico listado
QUANDO clicar no nome de um servico especifico
ENTAO NAO deve ser redirecionado para lugar nenhum
E a URL deve permanecer a mesma (/service-groups)
E NAO deve haver erros no console
E o usuario permanece na mesma pagina
```

**Passos de teste**:
1. Navegar para /service-groups
2. Identificar um servico na lista
3. Clicar no nome do servico
4. Verificar que nada acontece
5. Verificar URL permanece igual
6. Verificar console sem erros

**Resultado esperado**: Clique em servico nao causa nenhuma acao de navegacao

---

### Cenario 3: Build Sem Erros

**Objetivo**: Validar que o projeto compila sem erros

```gherkin
DADO que todas as modificacoes foram aplicadas
QUANDO executar o comando de build
ENTAO o build deve completar com sucesso
E nao deve haver erros de TypeScript
E nao deve haver warnings de imports nao utilizados
```

**Passos de teste**:
```bash
cd frontend
npm run build
```

**Resultado esperado**: Build completa com exit code 0

---

### Cenario 4: Rotas Antigas Retornam 404

**Objetivo**: Validar que rotas desativadas nao sao acessiveis

```gherkin
DADO que as rotas foram removidas do App.tsx
QUANDO acessar diretamente a URL /services
ENTAO deve exibir pagina 404 ou redirecionar para home
E nao deve exibir a pagina Services antiga
```

**Variantes**:
- `/services` → 404
- `/exporters` → 404
- `/blackbox` → 404
- `/blackbox-groups` → 404
- `/presets` → 404

**Passos de teste**:
1. Abrir navegador
2. Digitar URL diretamente
3. Verificar resposta

**Resultado esperado**: Pagina 404 ou redirecionamento

---

### Cenario 5: Arquivos DELETADOS Completamente

**Objetivo**: Validar que arquivos foram deletados, nao renomeados

```gherkin
DADO que o processo de remocao foi concluido
QUANDO verificar o diretorio frontend/src/pages/
ENTAO NAO deve existir o arquivo Services.tsx
E NAO deve existir o arquivo Exporters.tsx
E NAO deve existir o arquivo BlackboxTargets.tsx
E NAO deve existir o arquivo BlackboxGroups.tsx
E NAO deve existir o arquivo ServicePresets.tsx
E NAO deve existir o arquivo TestMonitoringTypes.tsx
E NAO deve existir o arquivo Services.old-deprecated
E NAO deve existir nenhum arquivo .old-deprecated
```

**Passos de teste**:
```bash
# Verificar que arquivos NAO existem
ls frontend/src/pages/Services.tsx 2>/dev/null && echo "ERRO: ainda existe" || echo "OK"
ls frontend/src/pages/Exporters.tsx 2>/dev/null && echo "ERRO: ainda existe" || echo "OK"
ls frontend/src/pages/BlackboxTargets.tsx 2>/dev/null && echo "ERRO: ainda existe" || echo "OK"
ls frontend/src/pages/BlackboxGroups.tsx 2>/dev/null && echo "ERRO: ainda existe" || echo "OK"
ls frontend/src/pages/ServicePresets.tsx 2>/dev/null && echo "ERRO: ainda existe" || echo "OK"
ls frontend/src/pages/TestMonitoringTypes.tsx 2>/dev/null && echo "ERRO: ainda existe" || echo "OK"

# Verificar que NAO existem arquivos .old-deprecated
ls frontend/src/pages/*.old-deprecated 2>/dev/null && echo "ERRO: deprecated existe" || echo "OK"
```

**Resultado esperado**: Arquivos completamente removidos do projeto

---

### Cenario 6: Hook Exclusivo DELETADO

**Objetivo**: Validar que hook useMonitoringType foi removido

```gherkin
DADO que o processo de remocao foi concluido
QUANDO verificar o diretorio frontend/src/hooks/
ENTAO NAO deve existir o arquivo useMonitoringType.ts
```

**Passos de teste**:
```bash
ls frontend/src/hooks/useMonitoringType.ts 2>/dev/null && echo "ERRO: ainda existe" || echo "OK"
```

**Resultado esperado**: Hook deletado completamente

---

### Cenario 7: Console Limpo

**Objetivo**: Validar que nao ha erros no console do navegador

```gherkin
DADO que a aplicacao esta rodando
QUANDO navegar por todas as paginas de monitoramento
ENTAO o console NAO deve exibir erros (vermelho)
E o console NAO deve exibir warnings criticos
E NAO deve haver erros de import ou componente nao encontrado
```

**Passos de teste**:
1. Abrir DevTools (F12)
2. Ir para aba Console
3. Limpar console
4. Navegar por: Home, ServiceGroups, todas as /monitoring/*
5. Verificar mensagens

**Resultado esperado**: Console sem erros vermelhos

---

### Cenario 8: Componentes Compartilhados Funcionam

**Objetivo**: Validar que componentes compartilhados nao foram afetados

```gherkin
DADO que componentes compartilhados sao usados em multiplas paginas
QUANDO acessar paginas que usam NodeSelector
ENTAO o componente NodeSelector deve renderizar
E deve funcionar normalmente
E nao deve haver erros de import
```

**Variantes de teste**:
- `/monitoring/system-exporters` usa NodeSelector
- `/monitoring/network-probes` usa NodeSelector
- `/hosts` usa NodeSelector

**Passos de teste**:
1. Navegar para cada pagina listada
2. Verificar renderizacao do NodeSelector
3. Interagir com o componente
4. Verificar funcionalidade

**Resultado esperado**: Todos componentes funcionam normalmente

---

### Cenario 9: Hooks Compartilhados Funcionam

**Objetivo**: Validar que hooks compartilhados nao foram removidos

```gherkin
DADO que hooks como useConsulDelete sao usados em 8 arquivos
QUANDO acessar paginas que usam funcionalidade de delete
ENTAO a funcionalidade de delete deve estar disponivel
E nao deve haver erros de import do hook
```

**Passos de teste**:
1. Navegar para /hosts
2. Tentar deletar um item (se possivel em dev)
3. Verificar que modal de confirmacao aparece
4. Verificar console para erros

**Resultado esperado**: Funcionalidade de delete funcionando

---

### Cenario 10: Paginas de Monitoramento Dinamico Intactas

**Objetivo**: Validar que DynamicMonitoringPage nao foi afetada

```gherkin
DADO que as paginas de monitoramento dinamico existem
QUANDO acessar /monitoring/system-exporters
ENTAO a pagina deve carregar normalmente
E NodeSelector deve funcionar
E filtros devem funcionar
E tabela deve renderizar dados
```

**Paginas a testar**:
- `/monitoring/network-probes`
- `/monitoring/web-probes`
- `/monitoring/system-exporters`
- `/monitoring/database-exporters`
- `/monitoring/infrastructure-exporters`
- `/monitoring/hardware-exporters`
- `/monitoring/network-devices`
- `/monitoring/custom-exporters`

**Passos de teste**:
1. Navegar para cada rota
2. Verificar carregamento
3. Interagir com componentes
4. Verificar dados

**Resultado esperado**: Todas as 8 paginas funcionam normalmente

---

### Cenario 11: APIs Backend Movidas para obsolete/

**Objetivo**: Validar que APIs backend foram movidas corretamente

```gherkin
DADO que o processo de remocao foi concluido
QUANDO verificar a pasta obsolete/
ENTAO deve existir obsolete/backend_api/services_optimized.py
E deve existir obsolete/backend_api/blackbox.py
E deve existir obsolete/backend_api/presets.py
E deve existir obsolete/backend_core/blackbox_manager.py
E deve existir obsolete/backend_core/service_preset_manager.py
E NAO deve existir backend/api/services_optimized.py
E NAO deve existir backend/api/blackbox.py
E NAO deve existir backend/api/presets.py
E backend/api/services.py DEVE existir (refatorado, nao movido)
```

**Passos de teste**:
```bash
# Verificar que arquivos existem em obsolete/
ls obsolete/backend_api/services_optimized.py && echo "OK"
ls obsolete/backend_api/blackbox.py && echo "OK"
ls obsolete/backend_api/presets.py && echo "OK"

# Verificar que arquivos NAO existem em backend/
ls backend/api/services_optimized.py 2>/dev/null && echo "ERRO" || echo "OK - movido"
ls backend/api/blackbox.py 2>/dev/null && echo "ERRO" || echo "OK - movido"
ls backend/api/presets.py 2>/dev/null && echo "ERRO" || echo "OK - movido"

# Verificar que services.py AINDA existe (foi refatorado, nao movido)
ls backend/api/services.py && echo "OK - services.py existe (refatorado)"
```

**Resultado esperado**: Arquivos movidos para obsolete/, exceto services.py

---

### Cenario 12: Backend Inicia Sem Erros

**Objetivo**: Validar que backend nao foi quebrado

```gherkin
DADO que APIs foram movidas para obsolete/
E services.py foi refatorado
QUANDO iniciar o backend
ENTAO deve iniciar sem erros de import
E todas as rotas ativas devem funcionar
E nao deve haver erros no log
```

**Passos de teste**:
```bash
cd backend
python app.py
```

**Resultado esperado**: Backend inicia e funciona normalmente

---

### Cenario 13: CRUD de Services Funciona (CRITICO)

**Objetivo**: Validar que endpoints CRUD de services permanecem funcionais

```gherkin
DADO que services.py foi refatorado para manter apenas CRUD
QUANDO usar DynamicCRUDModal para criar um service
ENTAO createService deve funcionar corretamente
E o service deve ser criado no Consul
```

```gherkin
DADO que services.py foi refatorado para manter apenas CRUD
QUANDO usar DynamicCRUDModal para atualizar um service
ENTAO updateService deve funcionar corretamente
E o service deve ser atualizado no Consul
```

```gherkin
DADO que services.py foi refatorado para manter apenas CRUD
QUANDO usar DynamicMonitoringPage para deletar um service
ENTAO deleteService deve funcionar corretamente
E o service deve ser removido do Consul
```

**Passos de teste**:
1. Navegar para uma pagina de monitoramento dinamico
2. Criar um novo service via modal
3. Verificar que aparece na lista
4. Editar o service criado
5. Verificar que alteracoes foram salvas
6. Deletar o service
7. Verificar que foi removido da lista

**Resultado esperado**: Todas operacoes CRUD funcionam normalmente

---

### Cenario 14: Endpoints GET Removidos de services.py Retornam 404, Bulk Funciona [v1.4.0]

**Objetivo**: Validar que endpoints GET foram removidos e bulk permanece funcional

```gherkin
DADO que endpoints de listagem GET foram removidos de services.py
QUANDO acessar GET /api/v1/services/
ENTAO deve retornar 404 ou erro de rota nao encontrada
```

```gherkin
DADO que endpoints bulk foram MANTIDOS em services.py [v1.4.0]
QUANDO acessar POST /api/v1/services/bulk/register
ENTAO deve retornar sucesso (200/201)
E o endpoint deve estar funcional
```

**Endpoints a testar (devem retornar 404)**:
- `GET /api/v1/services/` - listServices
- `GET /api/v1/services/catalog/names` - getServiceCatalogNames
- `GET /api/v1/services/metadata/unique-values` - getMetadataUniqueValues
- `GET /api/v1/services/search/by-metadata` - searchByMetadata
- `GET /api/v1/services/{id}` - getService

**Endpoints a testar (devem FUNCIONAR) [v1.4.0]**:
- `POST /api/v1/services/bulk/register` - bulkRegister (preservado)
- `DELETE /api/v1/services/bulk/deregister` - bulkDeregister (preservado)

**Passos de teste**:
```bash
# Testar endpoints GET removidos
curl -X GET http://localhost:8000/api/v1/services/ | jq
# Esperado: 404 ou {"detail": "Not Found"}

# Testar endpoints bulk MANTIDOS [v1.4.0]
curl -X POST http://localhost:8000/api/v1/services/bulk/register -d '[]' -H "Content-Type: application/json"
# Esperado: 200 ou 201 (endpoint funcional)
curl -X DELETE http://localhost:8000/api/v1/services/bulk/deregister -d '[]' -H "Content-Type: application/json"
# Esperado: 200 ou 201 (endpoint funcional)
```

**Resultado esperado**: Endpoints GET retornam 404, endpoints bulk funcionam

---

### Cenario 15: api.ts do Frontend Atualizado

**Objetivo**: Validar que metodos nao utilizados foram removidos do api.ts

```gherkin
DADO que api.ts foi atualizado
QUANDO buscar por metodos de blackbox
ENTAO NAO deve existir createBlackboxGroup
E NAO deve existir listBlackboxGroups
E NAO deve existir outros metodos de blackbox
```

```gherkin
DADO que api.ts foi atualizado
QUANDO buscar por metodos CRUD de services
ENTAO DEVE existir createService
E DEVE existir updateService
E DEVE existir deleteService
```

**Passos de teste**:
```bash
# Verificar que metodos de blackbox foram removidos
grep -c "Blackbox" frontend/src/services/api.ts
# Esperado: 0 ou muito baixo

# Verificar que metodos CRUD existem
grep "createService" frontend/src/services/api.ts && echo "OK"
grep "updateService" frontend/src/services/api.ts && echo "OK"
grep "deleteService" frontend/src/services/api.ts && echo "OK"
```

**Resultado esperado**: Metodos de blackbox removidos, CRUD mantido

---

### Cenario 16: Testes Nao Quebram [v1.4.0]

**Objetivo**: Validar que testes em Tests/ funcionam apos mover modulos para obsolete/

```gherkin
DADO que os modulos BlackboxManager e ServicePresetManager foram movidos para obsolete/
QUANDO executar os testes em Tests/
ENTAO nenhum teste deve falhar por import error
E todos os testes atualizados devem passar
```

**Arquivos de teste a verificar [v1.4.0]**:
- `Tests/integration/test_phase1.py` (importa BlackboxManager)
- `Tests/integration/test_phase2.py` (importa BlackboxManager, ServicePresetManager)
- `Tests/metadata/test_audit_fix.py` (importa ServicePresetManager)

**Passos de teste**:
```bash
# Verificar que nao ha imports de modulos obsoletos
grep -r "BlackboxManager\|ServicePresetManager" Tests/ --include="*.py"
# Esperado: nenhum resultado ou apenas em comentarios

# Executar testes
python -m pytest Tests/ -v
```

**Resultado esperado**: Todos os testes passam sem ImportError

---

### Cenario 17: Dashboard Sem Atalhos Quebrados [v1.3.0]

**Objetivo**: Validar que Dashboard nao tem botoes que navegam para rotas obsoletas

```gherkin
DADO que as rotas /services e /blackbox foram removidas
QUANDO acessar o Dashboard
ENTAO NAO deve haver botao "Novo alvo Blackbox"
E NAO deve haver botao "Registrar servico"
E NAO deve haver botao "Ver todos os servicos"
OU os botoes devem redirecionar para fluxos validos
```

**Passos de teste**:
1. Navegar para Dashboard (/)
2. Verificar botoes de atalho
3. Se existirem, clicar em cada um
4. Verificar que navegam para rotas validas
5. Verificar console para erros

**Resultado esperado**: Nenhum botao navega para rotas que retornam 404

---

### Cenario 18: Scripts de Diagnostico Funcionam [v1.4.0]

**Objetivo**: Validar que scripts de diagnostico nao falham por arquivo nao encontrado

```gherkin
DADO que os arquivos Services.tsx, BlackboxTargets.tsx foram deletados
QUANDO executar scripts/development/analyze_react_complexity.py
ENTAO o script NAO deve falhar por arquivo nao encontrado
E NAO deve tentar ler arquivos deletados
```

**NOTA v1.4.0**: Referencia a `diagnostico.ps1` removida - arquivo nao existe no projeto.

**Passos de teste**:
```bash
# Testar analyze_react_complexity.py
python scripts/development/analyze_react_complexity.py
```

**Resultado esperado**: Script executa sem erros de arquivo nao encontrado

---

### Cenario 19: bulkDeleteServices MANTIDO no api.ts [v1.4.0]

**Objetivo**: Validar que metodo bulkDeleteServices foi MANTIDO no api.ts para operacoes em massa futuras

```gherkin
DADO que api.ts foi atualizado preservando funcoes bulk [v1.4.0]
QUANDO buscar por bulkDeleteServices
ENTAO DEVE existir o metodo bulkDeleteServices
E DEVE haver referencia a /services/bulk/deregister
```

**Passos de teste**:
```bash
# Verificar que metodo foi MANTIDO
grep "bulkDeleteServices" frontend/src/services/api.ts
# Esperado: encontrar o metodo

# Verificar que endpoint foi MANTIDO
grep "bulk/deregister" frontend/src/services/api.ts
# Esperado: encontrar a referencia
```

**Resultado esperado**: Metodo bulkDeleteServices mantido e funcional para uso futuro

---

## Quality Gates

### Gate 1: Pre-Merge

**Criterios obrigatorios para merge**:

- [ ] Build passa sem erros
- [ ] Zero erros de TypeScript
- [ ] Zero warnings de imports nao utilizados
- [ ] Todos os cenarios de teste passam (1-19)
- [ ] Console limpo (sem erros)
- [ ] Backend inicia sem erros
- [ ] ServiceGroups nao navega ao clicar
- [ ] **CRITICO**: CRUD de services funciona
- [ ] **CRITICO v1.4.0**: Endpoints bulk funcionam
- [ ] Testes em Tests/ passam
- [ ] Dashboard sem atalhos quebrados
- [ ] Scripts de diagnostico funcionam
- [ ] **v1.4.0**: bulkDeleteServices MANTIDO no api.ts

### Gate 2: Pre-Deploy

**Criterios obrigatorios para deploy**:

- [ ] Gate 1 passou
- [ ] Testes manuais completados
- [ ] Revisao de PR aprovada
- [ ] Nenhuma regressao identificada
- [ ] CRUD de services testado em staging
- [ ] **v1.4.0**: Endpoints bulk testados em staging
- [ ] Testes em Tests/ executados em staging
- [ ] Scripts de diagnostico testados

---

## Metodos de Verificacao

### Automatizados

| Verificacao | Comando | Criterio |
|-------------|---------|----------|
| Build | `npm run build` | Exit code 0 |
| TypeScript | `npx tsc --noEmit` | Zero erros |
| ESLint | `npm run lint` | Zero erros |
| Testes frontend | `npm test` | Todos passam |
| Backend | `python app.py` | Inicia sem erros |
| Testes Tests/ | `python -m pytest Tests/ -v` | Todos passam |
| analyze_react [v1.4.0] | `python scripts/development/analyze_react_complexity.py` | Exit code 0 |
| Endpoints bulk [v1.4.0] | `curl POST/DELETE bulk endpoints` | Status 200/201 |

### Manuais

| Verificacao | Metodo | Criterio |
|-------------|--------|----------|
| Menu | Inspecao visual | Items corretos |
| ServiceGroups | Click testing | NAO navega |
| Dashboard [v1.3.0] | Click testing | Sem atalhos quebrados |
| Console | DevTools | Sem erros |
| CRUD services | Criar/Editar/Deletar | Funciona |
| Funcionalidade | Uso real | Comportamento esperado |

---

## Definition of Done

### Para services.py (REFATORADO):
- [ ] Endpoints CRUD e bulk existem [v1.4.0]
- [ ] POST / funciona
- [ ] PUT /{id} funciona
- [ ] DELETE /{id} funciona
- [ ] POST /bulk/register funciona [v1.4.0]
- [ ] DELETE /bulk/deregister funciona [v1.4.0]
- [ ] Endpoints GET removidos retornam 404
- [ ] DynamicMonitoringPage funciona
- [ ] DynamicCRUDModal funciona

### Para cada arquivo deletado:
- [ ] Arquivo NAO existe mais no projeto
- [ ] Nenhum arquivo .old-deprecated criado
- [ ] Nenhuma referencia ao arquivo no codigo
- [ ] Build passa

### Para App.tsx:
- [ ] Imports removidos (5)
- [ ] Rotas removidas (5)
- [ ] Menu items removidos (5)
- [ ] Sem warnings de lint

### Para ServiceGroups:
- [ ] Funcao handleServiceClick REMOVIDA
- [ ] onClick handlers REMOVIDOS
- [ ] Clique em servico NAO navega
- [ ] Nao ha erros no console

### Para Backend:
- [ ] services.py REFATORADO (nao movido)
- [ ] APIs movidas para obsolete/
- [ ] Backend inicia sem erros
- [ ] Nenhum import quebrado
- [ ] Rotas ativas funcionam
- [ ] CRUD de services funciona

### Para api.ts:
- [ ] Metodos de blackbox removidos
- [ ] Metodos de presets removidos
- [ ] Metodos de listagem de services removidos
- [ ] bulkDeleteServices MANTIDO [v1.4.0]
- [ ] createService mantido
- [ ] updateService mantido
- [ ] deleteService mantido
- [ ] deregisterService mantido

### Para Testes e Scripts [v1.4.0]:
- [ ] Tests/integration/test_phase1.py atualizado/removido
- [ ] Tests/integration/test_phase2.py atualizado/removido
- [ ] Tests/metadata/test_audit_fix.py atualizado/removido
- [ ] Nenhum teste importa modulos obsoletos
- [ ] scripts/development/analyze_react_complexity.py atualizado
- [ ] Todos scripts executam sem erros

### Para Dashboard [v1.3.0]:
- [ ] Botao "Novo alvo Blackbox" REMOVIDO ou redirecionado
- [ ] Botao "Registrar servico" REMOVIDO ou redirecionado
- [ ] Botao "Ver todos os servicos" REMOVIDO ou redirecionado
- [ ] Nenhum botao navega para rotas 404

### Para o SPEC completo:
- [ ] Todos os cenarios de teste passam (1-19)
- [ ] Quality gates satisfeitos
- [ ] Documentacao atualizada
- [ ] PR revisado e aprovado

---

## Criterios de Rollback

### Quando fazer rollback:

1. **CRUD de services quebrado** - funcionalidade critica
2. **Build falha** apos tentativas de correcao
3. **Backend nao inicia** e nao pode ser corrigido rapidamente
4. **Funcionalidade critica quebrada** que nao pode ser corrigida rapidamente
5. **Regressao em DynamicMonitoringPage** ou outras paginas ativas
6. **Erro em producao** identificado apos deploy
7. **Testes em Tests/ quebrados [v1.3.0]** - impede validacao automatizada
8. **Dashboard inacessivel [v1.3.0]** - pagina principal quebrada

### Como fazer rollback:

```bash
# Reverter ultimo commit
git revert HEAD

# Ou reverter multiplos commits
git revert HEAD~5..HEAD

# Ou resetar para estado anterior (com cuidado)
git reset --hard <commit-hash>
```

---

## Metricas de Sucesso

| Metrica | Valor Esperado | Metodo de Medicao |
|---------|----------------|-------------------|
| Tempo de build | < 2 minutos | `time npm run build` |
| Erros de console | 0 | Inspecao DevTools |
| Paginas funcionais | 100% | Teste manual |
| Cobertura de testes | Mantida | `npm test -- --coverage` |
| Tamanho do bundle | Reduzido ~10% | Comparar antes/depois |
| Arquivos removidos | 11 (6 paginas + 1 hook + 4 backend) | Contagem manual |
| CRUD services | 100% funcional | Teste manual |
| Endpoints bulk [v1.4.0] | 100% funcional | Teste curl |
| Testes Tests/ | 100% passando | `python -m pytest Tests/` |
| Scripts diagnostico | 0 erros | Execucao manual |
| Cenarios de teste | 19/19 passando | Contagem manual |

---

## Notas Finais

### Prioridade de Validacao

1. **CRITICO**: CRUD de services funciona
2. **CRITICO v1.4.0**: Endpoints bulk funcionam
3. **CRITICO**: Build passa
4. **CRITICO**: Backend inicia
5. **CRITICO**: ServiceGroups NAO navega
6. **CRITICO**: Testes em Tests/ passam
7. **ALTO**: Menu correto
8. **ALTO**: Console limpo
9. **ALTO**: Dashboard sem atalhos quebrados
10. **MEDIO**: Arquivos realmente deletados
11. **MEDIO**: Scripts de diagnostico funcionam

### Dicas para Tester

- Sempre limpar cache do navegador antes de testar
- Testar em modo incognito para evitar cache
- Verificar console ANTES e DEPOIS de cada navegacao
- Documentar qualquer comportamento inesperado
- **CRITICO**: Testar CRUD de services em DynamicMonitoringPage
- **CRITICO v1.4.0**: Testar endpoints bulk com curl
- **IMPORTANTE**: Confirmar que clique em servico no ServiceGroups NAO faz nada
- **IMPORTANTE**: Verificar que services.py existe e foi refatorado (nao movido)
- **IMPORTANTE**: Executar testes em Tests/ apos CADA milestone
- **IMPORTANTE**: Verificar Dashboard apos remocao de rotas
- **IMPORTANTE**: Caminho correto eh `backend/api/models.py`
- **IMPORTANTE v1.4.0**: Verificar que bulkDeleteServices existe no api.ts

---

## Tags de Rastreabilidade

<!-- TAG_BLOCK_START -->
- [SPEC-CLEANUP-001] Criterios de aceitacao v1.4.0
- [TEST-001] Menu sem paginas desativadas (5 items)
- [TEST-002] ServiceGroups NAO navega ao clicar
- [TEST-003] Build sem erros
- [TEST-004] Rotas 404 (5 rotas GET)
- [TEST-005] Arquivos DELETADOS completamente (6 paginas)
- [TEST-006] Hook exclusivo DELETADO
- [TEST-007] Console limpo
- [TEST-008] Componentes compartilhados
- [TEST-009] Hooks compartilhados
- [TEST-010] Paginas dinamicas intactas
- [TEST-011] APIs backend movidas (exceto services.py)
- [TEST-012] Backend inicia sem erros
- [TEST-013] CRUD de services funciona (CRITICO)
- [TEST-014] Endpoints GET removidos 404, bulk funciona (v1.4.0)
- [TEST-015] api.ts atualizado
- [TEST-016] Testes nao quebram - Tests/
- [TEST-017] Dashboard sem atalhos quebrados
- [TEST-018] Scripts de diagnostico funcionam (v1.4.0)
- [TEST-019] bulkDeleteServices MANTIDO no api.ts (v1.4.0)
<!-- TAG_BLOCK_END -->
