# 📋 PLANO DE TESTE: ServersContext - Otimização de Servidores

**Data:** 16/11/2025  
**Objetivo:** Garantir que todas as funcionalidades continuem funcionando após criar ServersContext

---

## 🎯 OBJETIVOS DO TESTE

### Funcionalidades a Validar
1. ✅ **PrometheusConfig** - Seleção de servidor funciona
2. ✅ **MetadataFields** - Seleção de servidor funciona
3. ✅ **MonitoringTypes** - Seleção de servidor funciona
4. ✅ **ServerSelector** - Componente funciona isoladamente

### Performance a Medir
1. ✅ **Requests duplicados** - Deve reduzir de 4 para 1
2. ✅ **Tempo de carregamento** - Deve melhorar
3. ✅ **Cache hit rate** - Deve aumentar

---

## 📊 FASE 1: BASELINE (ANTES DAS MELHORIAS)

### 1.1 Teste de Funcionalidades

#### PrometheusConfig
- [ ] Página carrega sem erros
- [ ] Servidor master é selecionado automaticamente
- [ ] Dropdown de servidores funciona
- [ ] Trocar servidor funciona
- [ ] Arquivos são carregados corretamente
- [ ] Edição de arquivos funciona

#### MetadataFields
- [ ] Página carrega sem erros
- [ ] Servidor master é selecionado automaticamente
- [ ] Dropdown de servidores funciona
- [ ] Trocar servidor funciona
- [ ] Campos são carregados corretamente
- [ ] Sincronização funciona

#### MonitoringTypes
- [ ] Página carrega sem erros
- [ ] ServerSelector funciona
- [ ] Trocar servidor funciona
- [ ] Tipos são carregados corretamente
- [ ] Modo "all" vs "specific" funciona

### 1.2 Teste de Performance

#### Requests de API
- [ ] Contar requests para `/metadata-fields/servers` ao abrir cada página
- [ ] Medir tempo de resposta do endpoint
- [ ] Verificar cache hit/miss

#### Métricas a Capturar
```json
{
  "baseline": {
    "prometheus_config": {
      "requests_count": 0,
      "load_time_ms": 0,
      "server_selection_works": false
    },
    "metadata_fields": {
      "requests_count": 0,
      "load_time_ms": 0,
      "server_selection_works": false
    },
    "monitoring_types": {
      "requests_count": 0,
      "load_time_ms": 0,
      "server_selection_works": false
    },
    "total_requests": 0,
    "average_load_time_ms": 0
  }
}
```

---

## 🔧 FASE 2: IMPLEMENTAÇÃO

### 2.1 Criar ServersContext
- [ ] Criar `frontend/src/contexts/ServersContext.tsx`
- [ ] Seguir padrão do NodesContext
- [ ] Adicionar ao App.tsx

### 2.2 Refatorar ServerSelector
- [ ] Usar ServersContext ao invés de request próprio
- [ ] Manter compatibilidade com props existentes

### 2.3 Refatorar Páginas
- [ ] PrometheusConfig usar ServersContext
- [ ] MetadataFields usar ServersContext
- [ ] MonitoringTypes usar ServersContext

---

## 📊 FASE 3: TESTE PÓS-MELHORIAS

### 3.1 Teste de Funcionalidades (Mesmos testes da Fase 1.1)
- [ ] PrometheusConfig - Todas funcionalidades
- [ ] MetadataFields - Todas funcionalidades
- [ ] MonitoringTypes - Todas funcionalidades

### 3.2 Teste de Performance (Mesmas métricas da Fase 1.2)
- [ ] Contar requests para `/metadata-fields/servers`
- [ ] Medir tempo de resposta
- [ ] Verificar cache hit/miss

### 3.3 Comparação
- [ ] Comparar requests_count (deve reduzir)
- [ ] Comparar load_time (deve melhorar)
- [ ] Validar que funcionalidades continuam funcionando

---

## ✅ CRITÉRIOS DE SUCESSO

### Funcionalidades
- ✅ Todas as 3 páginas funcionam normalmente
- ✅ Seleção de servidor funciona em todas
- ✅ Nenhum erro no console
- ✅ Nenhum erro visual na UI

### Performance
- ✅ Requests reduzidos de 4 para 1 (75% redução)
- ✅ Tempo de carregamento melhorado ou mantido
- ✅ Cache funcionando corretamente

---

## 📝 CHECKLIST FINAL

### Antes de Commitar
- [ ] Todos os testes de funcionalidade passaram
- [ ] Performance melhorou ou manteve
- [ ] Nenhum erro no console
- [ ] Documentação atualizada
- [ ] Commits organizados

---

**Documento criado em:** 16/11/2025  
**Autor:** Plano de Teste - ServersContext

