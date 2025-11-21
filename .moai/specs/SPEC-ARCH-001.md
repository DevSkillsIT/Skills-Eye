# SPEC-ARCH-001: Integração do Sistema de Categorização Dinâmica

## Resumo Executivo

Esta especificação descreve a integração completa do sistema de categorização dinâmica do Skills-Eye, eliminando código hardcoded e estabelecendo as **regras do Consul KV como fonte única da verdade** para categorização de tipos de monitoramento.

**Objetivo Principal**: As regras criadas em `/monitoring/rules` devem controlar diretamente como os jobs do Prometheus são categorizados e em qual página aparecem.

**Status**: Em Análise
**Prioridade**: Alta
**Esforço Estimado**: 12-19 horas
**Data**: 2025-11-20

---

## Dados Atuais do Sistema

### KV `skills/eye/monitoring-types/categorization/rules`
- **Total de regras**: 48
- **Regras com form_schema**: 19
- **Regras sem form_schema**: 29
- **Categorias definidas**: 8

### KV `skills/eye/monitoring-types`
- **Total de tipos**: 10
- **Todos com form_schema**: Sim (2-13 campos cada)

### Categorias Disponíveis
| ID | Display Name | Regras |
|----|--------------|--------|
| network-probes | Network Probes (Rede) | 8 |
| web-probes | Web Probes (Aplicações) | 7 |
| system-exporters | Exporters: Sistemas | 4 |
| database-exporters | Exporters: Bancos de Dados | 8 |
| infrastructure-exporters | Exporters: Infraestrutura | 17 |
| hardware-exporters | Exporters: Hardware | 2 |
| network-devices | Dispositivos de Rede | 2 |
| custom-exporters | Exporters Customizados | 0 |

---

## 1. Problema Identificado

### 1.1 Situação Atual

O sistema possui **duas implementações paralelas e desconectadas** para categorização de tipos de monitoramento:

| Componente | Implementação | Afeta |
|------------|---------------|-------|
| `monitoring_types_dynamic.py` | **HARDCODED** (155 linhas de if/elif) | Extração de tipos do Prometheus |
| `categorization_rule_engine.py` | **DINÂMICO** (regras do KV) | Categorização de serviços do Consul |

### 1.2 Consequências

1. **Regras ignoradas**: Usuário edita regras em `/monitoring/rules` mas NÃO afeta `/monitoring-types`
2. **Duplicação de código**: Mesmos padrões em múltiplos lugares
3. **Manutenção custosa**: Novo exporter requer mudança em 2+ arquivos
4. **Inconsistência**: Categorização pode diferir entre tipos e serviços

### 1.3 Redundâncias Confirmadas

#### A) Lógica de Categorização Duplicada

| Local | Arquivo | Linhas | Descrição |
|-------|---------|--------|-----------|
| Hardcoded | `monitoring_types_dynamic.py` | 193-348 | `_infer_category_and_type()` |
| Dinâmico | `categorization_rule_engine.py` | 262-340 | `categorize()` |

#### B) Separação Clara de Responsabilidades

| Local | form_schema | Propósito Principal |
|-------|-------------|---------------------|
| KV `categorization/rules` | **NÃO** | Regras de categorização: categoria, display_name, exporter_type |
| KV `monitoring-types` | **SIM** | Tipos extraídos + form_schema customizado |

**Decisão de Arquitetura**:

**Regras** (`categorization/rules`) determinam:
- Em qual **página de monitoramento** o tipo aparece (categoria)
- Como o tipo aparece em **`/monitoring-types`** (display_name, exporter_type)
- **NÃO** armazena form_schema

**Tipos** (`monitoring-types`) armazenam:
- Tipos extraídos dos servidores Prometheus
- **form_schema** completo para cada tipo
- Dados específicos por servidor

**Exemplos de Schema nos Tipos**:
- Tipo `icmp`: 2 campos (target, module)
- Tipo `http_2xx`: 11 campos (URL, método, headers, etc.)
- Tipo `node_exporter`: 10 campos

#### C) DISPLAY_NAME_MAP e Funções Hardcoded - DEVEM SER REMOVIDAS

**Problema Atual**: Existe código hardcoded que deve ser substituído pelas regras dinâmicas.

| Hardcode | Arquivo | Substituir Por |
|----------|---------|----------------|
| `DISPLAY_NAME_MAP` | proposto display_names.py | `display_name` da regra |
| `CATEGORY_DISPLAY_MAP` | proposto display_names.py | `display_name` da categoria no KV |
| `_format_display_name()` | 2 arquivos | `result.get('display_name')` da regra |
| `_format_category_display_name()` | hardcoded | Buscar do KV `categories` |

**Conclusão**: O arquivo `display_names.py` proposto **NÃO deve ser criado**!!!!!!!!!!!

Os display_names devem vir **100% das regras dinâmicas**:

```python
# CORRETO - Display names vêm das regras
result = rule_engine.categorize(job_data)
display_name = result.get('display_name')  # Vem da regra!
category = result.get('category')          # Vem da regra!

# INCORRETO - Hardcoded (REMOVER)
display_name = DISPLAY_NAME_MAP.get(job_name, job_name)  # NÃO!
```

**Benefício**: Novos exporters podem ser adicionados criando regras, sem alterar código.

---

## 2.5 Análise de Campos das Regras

### Campos Disponíveis no KV `categorization/rules`

| Campo | Tipo | Propósito |
|-------|------|-----------|
| `id` | string | Identificador único da regra (ex: `blackbox_icmp`) |
| `priority` | number | Ordem de aplicação (maior = primeiro) |
| `category` | string | **Determina em qual página aparece** |
| `display_name` | string | Nome amigável para exibição |
| `exporter_type` | string | Tipo do exporter (ex: `blackbox`, `node`) |
| `conditions.job_name_pattern` | regex | Padrão para match do job_name |
| `conditions.metrics_path` | string | Path de métricas (ex: `/probe`) |
| `conditions.module_pattern` | regex | Padrão para match do módulo |
| `observations` | string | Notas/observações |
| ~~`form_schema`~~ | ~~object~~ | **REMOVER** - não deve existir aqui |

### Tratamento de Duplicatas

**Problema**: Existem múltiplas regras com mesmo `display_name` mas IDs diferentes.

**Exemplo**:
```
blackbox_icmp  → pattern: ^icmp.*  → display: "ICMP (Ping)"
blackbox_ping  → pattern: ^ping.*  → display: "ICMP (Ping)"
```

**Solução**:

1. **Chave de deduplicação**: `id` (único)
2. **Aplicação de regras**: Por `priority` (maior primeiro)
3. **Agrupamento na UI**: Por `display_name` quando necessário
4. **Na página de tipos**: Cada job do Prometheus que faz match com uma regra vira um tipo

**Fluxo de Match**:
```
Job "icmp_palmas" no Prometheus
    │
    ▼
Regra "blackbox_icmp" faz match (^icmp.*)
    │
    ▼
Tipo categorizado como:
- category: "network-probes"
- display_name: "ICMP (Ping)"
- exporter_type: "blackbox"
    │
    ▼
Aparece na página /monitoring/network-probes
```

### Qual Campo Determina o Display Name Final?

O campo `display_name` da **regra que fez match** é usado diretamente. Se o job "icmp_palmas" fizer match com a regra `blackbox_icmp`, o display_name será "ICMP (Ping)".

**Não há merge** - a primeira regra que faz match (por prioridade) define todos os valores.

---

## 2.6 Unificação de Arquivos Backend

### Análise: monitoring_types_dynamic.py vs categorization_rule_engine.py

| Arquivo | Função Atual | Usa KV Rules? |
|---------|--------------|---------------|
| `monitoring_types_dynamic.py` | Extração de tipos do Prometheus | **NÃO** (hardcoded) |
| `categorization_rule_engine.py` | Motor de regras dinâmico | **SIM** |

### Recomendação: INTEGRAR (não remover)

**MANTER ambos arquivos**, mas:

1. **`categorization_rule_engine.py`**: Manter como está (já funciona corretamente)
2. **`monitoring_types_dynamic.py`**: Modificar para USAR o engine

**Razão**: São responsabilidades diferentes:
- Engine: Aplica regras de categorização
- Dynamic: Extrai jobs do Prometheus e salva no KV

### Mudança Principal

```python
# monitoring_types_dynamic.py

# ANTES (hardcoded)
category, type_info = _infer_category_and_type(job_name, job)

# DEPOIS (dinâmico)
from core.categorization_rule_engine import CategorizationRuleEngine

result = rule_engine.categorize({
    'job_name': job_name,
    'metrics_path': job.get('metrics_path'),
    'module': _extract_blackbox_module(job)
})
category = result.get('category', 'custom-exporters')
display_name = result.get('display_name', job_name)
exporter_type = result.get('exporter_type', job_name)
```

---
## 2.7 Páginas de Categorias e Subtítulos

### Tarefa: Melhorar Subtítulos das Páginas

Cada página de monitoramento deve ter um subtítulo claro explicando:
- Tipos de exporters disponíveis
- Exemplos de itens que podem ser cadastrados

| Página | Subtítulo Sugerido | Exemplos |
|--------|-------------------|----------|
| network-probes | Monitoramento de conectividade de rede | ICMP Ping, TCP Connect, DNS, SSH Banner |
| web-probes | Monitoramento de aplicações web e APIs | HTTP 2xx/4xx/5xx, HTTPS, HTTP POST |
| system-exporters | Métricas de sistemas operacionais | Linux (Node), Windows, VMware ESXi |
| database-exporters | Monitoramento de bancos de dados | MySQL, PostgreSQL, MongoDB, Redis, Elasticsearch |
| infrastructure-exporters | Infraestrutura e serviços | HAProxy, Nginx, Apache, RabbitMQ, Kafka |
| hardware-exporters | Hardware físico e IPMI | iDRAC, HP iLO, IPMI, Dell OMSA |
| network-devices | Dispositivos de rede | MikroTik, Cisco (SNMP), Switches, Roteadores |
| custom-exporters | Exporters customizados | Exporters personalizados não categorizados |

**Implementação**: Atualizar `CATEGORY_DISPLAY_NAMES` no `DynamicMonitoringPage.tsx` ou buscar do KV.

---

## 2.7.1 Páginas de Categorias Faltantes

### Status das Rotas no App.tsx

| Categoria | Rota | Status |
|-----------|------|--------|
| network-probes | /monitoring/network-probes | ✅ Existe |
| web-probes | /monitoring/web-probes | ✅ Existe |
| system-exporters | /monitoring/system-exporters | ✅ Existe |
| database-exporters | /monitoring/database-exporters | ✅ Existe |
| infrastructure-exporters | /monitoring/infrastructure-exporters | ❌ **CRIAR** |
| hardware-exporters | /monitoring/hardware-exporters | ❌ **CRIAR** |
| network-devices | /monitoring/network-devices | ❌ **CRIAR** |
| custom-exporters | /monitoring/custom-exporters | ❌ **CRIAR** |

### Implementação das Rotas Faltantes

Usar `DynamicMonitoringPage` com a categoria correspondente:

```tsx
// App.tsx - Adicionar rotas faltantes
<Route
  path="/monitoring/infrastructure-exporters"
  element={<DynamicMonitoringPage category="infrastructure-exporters" />}
/>
<Route
  path="/monitoring/hardware-exporters"
  element={<DynamicMonitoringPage category="hardware-exporters" />}
/>
<Route
  path="/monitoring/network-devices"
  element={<DynamicMonitoringPage category="network-devices" />}
/>
<Route
  path="/monitoring/custom-exporters"
  element={<DynamicMonitoringPage category="custom-exporters" />}
/>
```

---

## 2.8 Reorganização do Menu

### Mover MonitoringRules para Configurações

**Atual**: `/monitoring/rules` (dentro de Monitoring)
**Novo**: `/settings/monitoring-rules` (dentro de Configurações)

**Razão**: Regras de categorização são **configurações do sistema**, não operações de monitoramento.

### Estrutura de Menu Proposta

```
📊 Monitoring
├── Network Probes
├── Web Probes
├── System Exporters
├── Database Exporters
├── Infrastructure Exporters (NOVA)
├── Hardware Exporters (NOVA)
├── Network Devices (NOVA)
└── Custom Exporters (NOVA)

⚙️ Configurações
├── Settings
├── Monitoring Types     (já existe)
└── Monitoring Rules     (MOVER AQUI)
```

---

## 3. Arquitetura Proposta

### 2.1 Fluxo Unificado

```
prometheus.yml
      │
      ▼ (SSH)
MultiConfigManager.read_config_file()
      │
      ▼
extract_types_from_prometheus_jobs()
      │
      ▼
┌─────────────────────────────────┐
│  CategorizationRuleEngine       │  ◀── ÚNICA FONTE DE CATEGORIZAÇÃO
│  .categorize(job_data)          │
└─────────────────────────────────┘
      │
      ▼
Salvar em KV: skills/eye/monitoring-types
      │
      ▼
Frontend consome tipos categorizados
```

### 2.2 Hierarquia de form_schema

```
1. Tipo específico (servidor)     → Prioridade MÁXIMA
2. Regra de categorização         → Fallback
3. Schema genérico                → Fallback final
```

### 2.3 Componentes Afetados

#### Backend
- `api/monitoring_types_dynamic.py` - Integrar engine
- `api/categorization_rules.py` - Remover form_schema
- `core/categorization_rule_engine.py` - Remover form_schema
- **NOVO**: `core/display_names.py` - Utilitário compartilhado

#### Frontend
- `pages/MonitoringRules.tsx` - Remover UI form_schema (se existir)
- `pages/MonitoringTypes.tsx` - Manter como está (fonte de schema)

---

## 3. Especificação Técnica

### 3.1 Mudanças no Backend

#### 3.1.1 monitoring_types_dynamic.py

**ANTES** (linha ~169):
```python
category, type_info = _infer_category_and_type(job_name, job)
```

**DEPOIS**:
```python
from core.categorization_rule_engine import CategorizationRuleEngine

# Instanciar engine global
rule_engine = CategorizationRuleEngine(multi_config)

async def extract_types_from_prometheus_jobs(...):
    # Carregar regras se necessário
    await rule_engine.load_rules()

    for job_name, job in prometheus_jobs:
        # Usar engine dinâmico
        result = rule_engine.categorize({
            'job_name': job_name,
            'metrics_path': job.get('metrics_path', '/metrics'),
            'module': _extract_blackbox_module(job),
            'tags': extract_consul_tags(job)
        })

        category = result.get('category', 'custom-exporters')
        exporter_type = result.get('exporter_type', job_name)
        display_name = result.get('display_name', job_name)

        # ... resto da lógica
```

**Funções a REMOVER**:
- `_infer_category_and_type()` (linhas 193-348)
- `_format_display_name()` (linhas 374-391)
- `_format_category_display_name()` (linhas 394-406)

**Funções a MANTER**:
- `_extract_blackbox_module()` - Ainda necessária para extrair módulo

#### 3.1.2 categorization_rules.py - REMOVER form_schema

**REMOVER** form_schema das regras - deve existir APENAS em monitoring-types:

```python
# REMOVER de CategorizationRuleModel
form_schema: Optional[FormSchema] = None  # REMOVER

# REMOVER classes (se não usadas em outro lugar)
class FormSchemaField(BaseModel): ...  # REMOVER
class FormSchema(BaseModel): ...        # REMOVER

# REMOVER de RuleCreateRequest e RuleUpdateRequest
form_schema: Optional[Dict] = None  # REMOVER
```

**IMPORTANTE**: form_schema deve existir APENAS no KV `monitoring-types`, não nas regras.

#### 3.1.3 categorization_rule_engine.py - REMOVER form_schema

**REMOVER** form_schema do engine:

```python
# REMOVER da classe CategorizationRule
self.form_schema = rule_data.get('form_schema')  # REMOVER

# O método categorize() retorna APENAS:
return {
    'category': matched_rule.category,
    'exporter_type': matched_rule.exporter_type,
    'display_name': matched_rule.display_name
    # SEM form_schema
}
```

O form_schema é buscado DIRETAMENTE do KV `monitoring-types` pelo `monitoring_types_dynamic.py`.

#### 3.1.4 NÃO CRIAR display_names.py - Usar Regras Dinâmicas

**IMPORTANTE**: Não criar arquivo `display_names.py` com mapeamentos hardcoded.

Todos os display_names devem vir das **regras dinâmicas no KV**:

```python
# monitoring_types_dynamic.py - Usar engine
result = rule_engine.categorize({
    'job_name': job_name,
    'metrics_path': job.get('metrics_path'),
    'module': _extract_blackbox_module(job)
})

# Display names vêm da regra
display_name = result.get('display_name', job_name)
category = result.get('category', 'custom-exporters')
exporter_type = result.get('exporter_type', job_name)

# Para categoria display_name, buscar do KV categories
category_info = get_category_from_kv(category)
category_display = category_info.get('display_name', category)
```

**Benefício**: 100% dinâmico - novos exporters via regras, sem código.

### 3.2 Mudanças no Frontend

#### 3.2.1 MonitoringRules.tsx - REMOVER form_schema

**PROPÓSITO**: Gerenciar regras que determinam em qual página/categoria cada tipo de probe aparece.

**MANTER**:
- CRUD completo de regras
- Campos: id, pattern, category, exporter_type, display_name, priority, observations

**REMOVER**:
- Qualquer referência a form_schema
- Coluna de form_schema na tabela (se existir)
- Campos de form_schema no modal de edição (se existir)

**MOVER**: De `/monitoring/rules` para `/settings/monitoring-rules` (menu Configurações)

#### 3.2.2 MonitoringTypes.tsx - MANTER COMO ESTÁ

**PROPÓSITO**: Visualizar e customizar tipos extraídos dos servidores Prometheus.

**MANTER**:
- Botão "Schema" com Monaco Editor
- Customização de form_schema por tipo/servidor
- ÚNICO lugar para editar form_schema

#### 3.2.3 App.tsx - ADICIONAR ROTAS FALTANTES

**ADICIONAR rotas**:
```tsx
// Páginas de monitoramento faltantes
<Route path="/monitoring/infrastructure-exporters" element={<DynamicMonitoringPage category="infrastructure-exporters" />} />
<Route path="/monitoring/hardware-exporters" element={<DynamicMonitoringPage category="hardware-exporters" />} />
<Route path="/monitoring/network-devices" element={<DynamicMonitoringPage category="network-devices" />} />
<Route path="/monitoring/custom-exporters" element={<DynamicMonitoringPage category="custom-exporters" />} />

// Mover MonitoringRules para Configurações
<Route path="/settings/monitoring-rules" element={<MonitoringRules />} />
```

#### 3.2.4 Menu/Sidebar - REORGANIZAR

**ADICIONAR** ao menu Monitoring:
- Infrastructure Exporters
- Hardware Exporters
- Network Devices
- Custom Exporters

**MOVER** MonitoringRules para menu Configurações

### 3.3 Estrutura Final do KV

```
skills/eye/
├── monitoring-types/
│   ├── servers/                    # Tipos por servidor
│   │   └── {ip}/
│   │       └── types: [...]        # Com form_schema específico
│   ├── all_types: [...]            # Todos únicos
│   └── last_updated: "..."
│
├── monitoring-types/categorization/
│   └── rules                       # Regras SEM form_schema
│       ├── rules: [
│       │   {
│       │     id, pattern, category,
│       │     exporter_type, display_name,
│       │     priority, enabled
│       │     // SEM form_schema
│       │   }
│       │ ]
│       ├── categories: [...]
│       └── default_category: "custom-exporters"
```

---

## 4. Plano de Implementação

### Fase 1: Preparação (1-2 horas)

#### 1.1 Script de Validação
Criar script que compare categorização atual vs futura:

```python
# scripts/validate_categorization.py
async def compare_categorization():
    """Compara hardcoded vs engine para todos os jobs"""

    # 1. Extrair jobs do Prometheus
    jobs = await extract_prometheus_jobs()

    # 2. Categorizar com hardcoded
    hardcoded_results = {}
    for job_name, job in jobs:
        cat, info = _infer_category_and_type(job_name, job)
        hardcoded_results[job_name] = (cat, info)

    # 3. Categorizar com engine
    engine = CategorizationRuleEngine(config)
    await engine.load_rules()
    engine_results = {}
    for job_name, job in jobs:
        result = engine.categorize({...})
        engine_results[job_name] = result

    # 4. Comparar e reportar divergências
    divergences = []
    for job_name in hardcoded_results:
        if hardcoded_results[job_name] != engine_results[job_name]:
            divergences.append({
                'job': job_name,
                'hardcoded': hardcoded_results[job_name],
                'engine': engine_results[job_name]
            })

    return divergences
```

#### 1.2 Criar Regras Iniciais
Migrar padrões hardcoded para KV (se ainda não existirem):

```bash
# Usar endpoint existente ou script de migração
POST /api/v1/categorization-rules/migrate-from-hardcoded
```

### Fase 2: Integração Core (4-6 horas)

#### 2.1 Criar display_names.py
- Implementar utilitário compartilhado
- Adicionar todos os mapeamentos

#### 2.2 Modificar monitoring_types_dynamic.py
- Importar e instanciar CategorizationRuleEngine
- Substituir `_infer_category_and_type()` por `engine.categorize()`
- Remover funções hardcoded
- Atualizar para usar `display_names.py`

#### 2.3 Atualizar categorization_rule_engine.py
- Usar `display_names.py`
- Garantir compatibilidade com novo fluxo

### Fase 3: Remover form_schema das Regras (2-3 horas)

#### 3.1 Backend - Remover form_schema

**categorization_rules.py**:
- Remover campo `form_schema` de todos os modelos
- Remover classes `FormSchema` e `FormSchemaField`
- Atualizar endpoints de CRUD

**categorization_rule_engine.py**:
- Remover `self.form_schema` da classe `CategorizationRule`
- Atualizar método `categorize()` para não retornar form_schema

#### 3.2 Frontend - Remover form_schema

**MonitoringRules.tsx**:
- Remover interface/tipo `FormSchema`
- Remover coluna de form_schema da tabela
- Remover campos de form_schema do modal de edição

#### 3.3 Migrar Dados do KV

Script para remover form_schema das regras existentes:

```python
async def migrate_remove_form_schema():
    """Remove form_schema de todas as regras no KV"""
    rules = await get_all_rules()

    for rule in rules:
        if 'form_schema' in rule:
            del rule['form_schema']

    await save_all_rules(rules)
```

### Fase 3.5: Adicionar Rotas e Menu (1-2 horas)

#### 3.5.1 App.tsx - Rotas Faltantes
Adicionar 4 rotas de categorias:
- infrastructure-exporters
- hardware-exporters
- network-devices
- custom-exporters

#### 3.5.2 Menu/Sidebar
- Adicionar 4 itens no menu Monitoring
- Mover MonitoringRules para Configurações

### Fase 4: Testes e Validação (2-4 horas)

#### 4.1 Testes Automatizados
```python
# test_categorization_integration.py

async def test_rule_affects_types():
    """Criar regra deve afetar tipos extraídos"""

    # 1. Baseline - extrair tipos
    baseline = await get_types()

    # 2. Criar regra customizada
    await create_rule({
        'pattern': 'my-custom-job',
        'category': 'custom-exporters',
        'exporter_type': 'custom',
        'display_name': 'Meu Job Customizado'
    })

    # 3. Re-extrair tipos
    after = await get_types()

    # 4. Verificar que job foi categorizado conforme regra
    assert find_type(after, 'my-custom-job').category == 'custom-exporters'
```

#### 4.2 Testes Manuais
1. Verificar tipos em `/monitoring-types`
2. Criar regra em `/monitoring/rules`
3. Forçar re-extração de tipos
4. Verificar que categorização mudou
5. Testar cadastro de serviço com form_schema

---

## 5. Riscos e Mitigações

### 5.1 Riscos de Implementação

| Risco | Probabilidade | Impacto | Mitigação |
|-------|---------------|---------|-----------|
| Categorização muda | MÉDIA | ALTO | Script de validação antes/depois |
| Regras KV vazias | BAIXA | MÉDIO | Fallback para categoria default |
| Performance | BAIXA | BAIXO | Engine já usa cache |
| form_schema perdido | BAIXA | ALTO | Backup antes de remover |

### 5.2 Rollback Plan

1. Manter função `_infer_category_and_type()` comentada
2. Adicionar flag `USE_DYNAMIC_RULES=true` em .env
3. Se problemas, desabilitar flag para voltar ao hardcoded

---

## 6. Critérios de Aceite

### 6.1 Funcional
- [ ] Regras criadas em `/monitoring/rules` afetam tipos em `/monitoring-types`
- [ ] Novos exporters podem ser categorizados sem mudança de código
- [ ] form_schema é editável apenas em `/monitoring-types`
- [ ] Cadastro de serviço usa form_schema corretamente

### 6.2 Técnico
- [ ] Função `_infer_category_and_type()` removida
- [ ] CategorizationRuleEngine usado em monitoring_types_dynamic.py
- [ ] form_schema REMOVIDO das regras (backend e frontend)
- [ ] form_schema existe APENAS em monitoring-types
- [ ] Display names vêm 100% das regras (sem DISPLAY_NAME_MAP hardcoded)
- [ ] 4 rotas de categorias adicionadas
- [ ] MonitoringRules movido para Configurações
- [ ] Subtítulos das páginas atualizados com exemplos

### 6.3 Performance
- [ ] Extração de tipos não degrada (< 5% mais lento)
- [ ] Cache de regras funciona corretamente

---

## 7. Próximos Passos

1. **APROVAR** esta especificação
2. **CRIAR BRANCH** `feature/SPEC-ARCH-001`
3. **EXECUTAR** Fase 1 (Preparação)
4. **VALIDAR** divergências antes de continuar
5. **IMPLEMENTAR** Fases 2-4
6. **TESTAR** manual e automatizado
7. **MERGE** após aprovação

---

## Anexo A: Mapeamento de Padrões Hardcoded

| Padrão | Categoria | Exporter Type | Display Name |
|--------|-----------|---------------|--------------|
| `icmp`, `ping` | network-probes | blackbox | ICMP (Ping) |
| `tcp`, `tcp_connect` | network-probes | blackbox | TCP Connect |
| `http_2xx` | web-probes | blackbox | HTTP 2xx |
| `ssh_banner` | network-probes | blackbox | SSH Banner |
| `dns` | network-probes | blackbox | DNS |
| `node`, `selfnode` | system-exporters | node | Node Exporter |
| `windows` | system-exporters | windows | Windows Exporter |
| `snmp` | infrastructure-exporters | snmp | SNMP Exporter |
| `mysql` | database-exporters | mysql | MySQL |
| `postgres`, `pg` | database-exporters | postgres | PostgreSQL |
| `redis` | database-exporters | redis | Redis |
| `mongo` | database-exporters | mongodb | MongoDB |
| `mktxp`, `mikrotik` | infrastructure-exporters | mktxp | MikroTik (MKTXP) |

---

## Anexo B: Endpoints Afetados

| Endpoint | Mudança |
|----------|---------|
| `GET /monitoring-types-dynamic/from-prometheus` | Usar engine para categorização |
| `PUT /monitoring-types-dynamic/type/{id}/form-schema` | Manter (ÚNICO lugar para schema) |
| `GET /categorization-rules` | REMOVER form_schema da resposta |
| `POST /categorization-rules` | REMOVER form_schema do request |
| `PUT /categorization-rules/{id}` | REMOVER form_schema do request |

## Anexo C: Fluxo de form_schema (Simplificado)

```
┌─────────────────────────────────────────────────────────┐
│        FORM_SCHEMA APENAS EM MONITORING-TYPES           │
└─────────────────────────────────────────────────────────┘

1. Usuário cria regra em /settings/monitoring-rules
   └─ Define APENAS: pattern, category, display_name, exporter_type
   └─ NÃO define form_schema
         │
         ▼
2. Sistema extrai tipos do Prometheus
   └─ Usa engine para categorizar (categoria, display_name)
   └─ Busca form_schema DIRETAMENTE do KV monitoring-types
         │
         ▼
3. Usuário customiza schema em /monitoring-types
   └─ Monaco Editor para editar form_schema
   └─ ÚNICO lugar para definir campos do formulário
         │
         ▼
4. DynamicCRUDModal busca schema
   └─ Busca form_schema do tipo no KV monitoring-types
   └─ Se não existir, usa schema vazio (campos genéricos)
```

**IMPORTANTE**: Não há mais hierarquia/fallback. form_schema existe em UM único lugar.

## Anexo D: Categorias e Páginas

A categoria da regra determina em qual página o tipo aparece:

| Categoria | Página | URL |
|-----------|--------|-----|
| network-probes | Network Probes | /monitoring/network-probes |
| web-probes | Web Probes | /monitoring/web-probes |
| system-exporters | System Exporters | /monitoring/system-exporters |
| database-exporters | Database Exporters | /monitoring/database-exporters |
| infrastructure-exporters | Infrastructure | /monitoring/infrastructure-exporters |
| hardware-exporters | Hardware | /monitoring/hardware-exporters |
| network-devices | Network Devices | /monitoring/network-devices |
| custom-exporters | Custom | /monitoring/custom-exporters |

---

*Documento gerado em 2025-11-20*
*Baseado em análise arquitetural do Skills-Eye*
*Autor: Análise Automatizada + Revisão Manual*
