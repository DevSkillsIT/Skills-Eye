# Considerações Críticas - SPEC-PERF-001

## Data
21/11/2025

## Objetivo
Consolidar, sem redundâncias, os pontos que ainda estão errados ou faltando no plano SPEC-PERF-001 após a junção das observações feitas por diferentes analistas/IA.

## Resumo executivo
- A chamada à Catalog API ainda depende de um único servidor Consul, sem fallback nem telemetria adequada, o que pode voltar a zerar `services_count`.
- O aumento de TTL para 60 s foi feito sem qualquer estratégia de invalidação ou coordenação entre múltiplas instâncias do backend.
- Há risco de saturar o líder do Consul por falta de limitação de paralelismo e por criar um cliente HTTP novo por requisição.
- O plano de validação/rollback não é executável: o script citado não existe e não há critérios objetivos para desfazer as fases.
- No frontend, a remoção de `onChange` das dependências do `NodeSelector` elimina sintomas, mas pode quebrar telas que trocam o callback dinamicamente.

---

## Problemas críticos identificados

### 1. Robustez insuficiente nas chamadas à Catalog API
**Evidência**:

```33:86:backend/api/nodes.py
        consul = ConsulManager()
        ...
            try:
                node_data = await asyncio.wait_for(
                    consul.get_node_services(member["node"]),
                    timeout=2.0
                )
                ...
            except Exception as e:
                # Silencioso - se falhar, deixa services_count = 0
                pass
```

- Toda a coleta usa um único `ConsulManager()` apontado para `Config.MAIN_SERVER`; caso o líder caia, todas as contagens retornam 0.
- Não há retry/backoff para diferenciar falha transitória de falha definitiva e o timeout de 2 s está hardcoded.
- Exceções são engolidas, impossibilitando RCA.

**Correções sugeridas**:
1. Reutilizar a lógica de fallback já existente em `ConsulManager.get_services_with_fallback()` ou manter uma lista de servidores Consul para tentar em sequência.
2. Introduzir retry único com backoff curto e tornar o timeout configurável via env (`CONSUL_CATALOG_TIMEOUT`).
3. Registrar `logger.warning`/métrica (`consul_node_enrich_failures`) sempre que o fallback precisar ser usado.

### 2. Cache inconsistente entre instâncias e sem invalidação
**Evidência**:

```92:102:backend/api/nodes.py
        result = {
            "success": True,
            "data": enriched_members,
            "total": len(enriched_members),
            "main_server": Config.MAIN_SERVER
        }
        await cache.set(cache_key, result, ttl=60)
```

- O TTL foi duplicado (30 s → 60 s), mas não há nenhum gatilho para invalidar o cache quando um nó entra/sai ou quando operadores precisam forçar atualização.
- O `LocalCache` é em memória; cada instância do backend terá uma visão diferente, o que gera métricas inconsistentes atrás de load balancer.

**Correções sugeridas**:
1. Expor um endpoint administrativo (`POST /admin/cache/nodes/flush`) ou um comando CLI que chame `cache.delete(cache_key)`.
2. Publicar eventos (Consul event, webhook ou cron) para invalidar o cache quando o membership mudar.
3. Documentar explicitamente a limitação de cache local e planejar migração para cache distribuído (Redis) quando houver mais de uma instância.

### 3. Gargalo potencial por tempestade de requisições à Catalog API
**Evidências**:

```89:90:backend/api/nodes.py
        enriched_members = await asyncio.gather(*[get_service_count(m) for m in members])
```

```112:145:backend/core/consul_manager.py
        async with httpx.AsyncClient() as client:
            start_time = time.time()
            response = await client.request(method, url, **kwargs)
            ...
```

- `asyncio.gather` dispara uma chamada por nó sem limite; com 20+ nós isso pode abrir dezenas de conexões simultâneas no líder Consul.
- Cada chamada cria um `httpx.AsyncClient` novo, impedindo reaproveitamento de conexões.

**Correções sugeridas**:
1. Envolver `get_service_count` em um `asyncio.Semaphore` (ex.: 5 chamadas simultâneas) parametrizado por env.
2. Manter um `httpx.AsyncClient` compartilhado por `ConsulManager` (pool persistente) para reduzir overhead de TLS/conexão.
3. Considerar leitura em lotes (usar `/catalog/services` + filtragem local) caso o número de nós cresça.

### 4. Observabilidade e UX do fallback inexistentes
**Evidência**: mesmo bloco citado no item 1 (linhas 71-86 de `backend/api/nodes.py`) termina em `pass`.

- Não existe log, métrica ou flag para diferenciar “0 serviços reais” de “falha ao consultar o nó”.
- O fallback exigido em DC-001 do SPEC funciona, mas deixa o operador cego.

**Correções sugeridas**:
1. Registrar `logger.warning` com IP/nome do nó e razão da falha.
2. Incluir `member["services_status"] = "error"` quando der timeout para que o frontend sinalize (badge/tooltip).
3. Exportar métricas Prometheus (total de timeouts, média de tempo por nó) e criar alerta quando `services_count=0` disparar em massa.

### 5. Remoção de `onChange` do NodeSelector sem estratégia para callbacks dinâmicos
**Evidência**:

```58:82:frontend/src/components/NodeSelector.tsx
  useEffect(() => {
    if (!loading && nodes.length > 0 && !selectedNode) {
      ...
      if (onChange) {
        onChange(mainNode.addr, mainNode);
      }
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [loading, nodes, mainServer, selectedNode, showAllNodesOption]);
```

- O `eslint-disable` elimina re-renderizações extras, mas se o componente pai trocar o callback (ex.: alterar filtros ou telemetria), o efeito não dispara novamente e o estado inicial pode ficar inconsistente.

**Correções sugeridas**:
1. Reintroduzir `onChange` nas dependências e encapsular a versão mais recente em um `useRef`.
2. Documentar nos consumers que o callback precisa ser memoizado com `useCallback`.
3. Alternativamente, mover a lógica de seleção inicial para o próprio contexto de nós e expor apenas o valor já resolvido.

### 6. Metadados de sites (KV) sem cache dedicado
**Evidência**:

```36:54:backend/api/nodes.py
        from core.kv_manager import KVManager
        kv = KVManager()
        sites_data = await kv.get_json('skills/eye/metadata/sites')
        ...
        for site in sites_list:
            ...
            sites_map[ip] = name
```

- A cada cache miss de `nodes` ocorre uma leitura completa do KV, que pode se tornar o novo gargalo quando o Consul KV estiver sob carga.

**Correções sugeridas**:
1. Cachear o `sites_map` com TTL próprio (ex.: 5 minutos) ou pré-carregar em background.
2. Manter o último valor válido para evitar regressões quando o KV estiver lento.

### 7. Roteiro de validação e testes incompleto
**Evidência**:

```150:154:.moai/specs/SPEC-PERF-001/plan-updated-v2.md
### Fase 4: Validacao Final
1. Executar teste de comparacao: `python test_performance_nodes.py --mode compare`
```

- O arquivo `test_performance_nodes.py` não existe no repositório (verificado via `find . -name test_performance_nodes.py`, sem resultados), logo a fase 4 é inexequível.
- O plano não descreve testes unitários/integrados automatizados; toda a verificação é manual.

**Correções sugeridas**:
1. Criar um script versionado (ex.: `scripts/bench_nodes.py`) que colete baseline/compare e gere um relatório com P50/P95/P99.
2. Adicionar testes unitários para `get_service_count` (simulando timeout, erro, sucesso) e um teste de integração de `/api/v1/nodes`.
3. Registrar no SPEC os pré-requisitos do ambiente de teste (Consul estável, sem requisições paralelas).

### 8. Falta de estratégia concreta de rollback
**Evidência**:

```294:300:.moai/specs/SPEC-PERF-001/spec.md
3. **Monitorar logs**: Verificar se timeouts estao ocorrendo com 2s
4. **Rollback facil**: Mudancas sao reversiveis com alteracao de valores
```

- O SPEC apenas afirma que o rollback é “fácil”, mas não define gatilhos (métricas ou erros) que determinem quando desfazer cada fase, nem o passo a passo para reverter.

**Correções sugeridas**:
1. Definir métricas de aceitação (ex.: taxa de timeout > 5% por 10 min) que disparem rollback.
2. Especificar a ordem: reverter primeiro o frontend (deps `onChange`), depois Catalog API, por fim TTL e timeout.
3. Automatizar via script ou documentação operacional para evitar erro humano durante incidentes.

---

## Itens confirmados como corretos (não repetir)
- Uso da Catalog API no lugar da Agent API.
- Memoização do `NodesContext`.
- Estrutura do plano em fases.

---

## Próximos passos recomendados
1. Implementar as correções de backend (fallback, cache, observabilidade) antes de mexer no frontend.
2. Ajustar o `NodeSelector` para lidar com callbacks instáveis sem violar as regras de hooks.
3. Criar o tooling de testes/benchmark e registrar procedimento de rollback antes de iniciar a Fase 4.
#