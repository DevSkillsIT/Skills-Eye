# 📌 NOTA IMPORTANTE - AJUSTES VALIDADOS

**Data:** 13/11/2025  
**Status:** ✅ DOCUMENTO ATUALIZADO COM AJUSTES CRÍTICOS

---

## ⚠️ LEIA ANTES DE IMPLEMENTAR

Este plano foi **REVISADO E AJUSTADO** após discussão com o desenvolvedor sênior. Os ajustes críticos identificados estão documentados em:

📄 **`docs/AJUSTES_CRITICOS_PLANO_V2.md`**

### Principais Ajustes Aplicados:

1. **✅ Estrutura KV Fields**
   - Sistema **JÁ EXISTE** (`show_in_services`, `show_in_exporters`, `show_in_blackbox`)
   - **AÇÃO:** Apenas adicionar 4 novas propriedades para as novas páginas
   - Página Metadata Fields já tem coluna "Páginas" funcionando

2. **✅ Endpoints Duplos (Consul + Prometheus)**
   - `/monitoring/data` → Buscar serviços do Consul (igual Services.tsx)
   - `/monitoring/metrics` → Buscar métricas do Prometheus via PromQL
   - **AÇÃO:** Implementar AMBOS na Fase 1 (Dia 5)

3. **✅ Centralizar API em consulAPI**
   - Adicionar método `getMonitoringData()` em `services/api.ts`
   - DynamicMonitoringPage usa consulAPI, não fetch direto
   - **AÇÃO:** Seguir padrão existente de Services.tsx

4. **✅ Migração de Regras + Página de Gerenciamento**
   - Criar script `migrate_categorization_to_json.py` (Dia 3)
   - Criar página `/monitoring/rules` OU aba em "Tipos de Monitoramento"
   - **AÇÃO:** Implementar migração ANTES de modificar código

5. **✅ Testes de Persistência Integrados**
   - Adicionar **Dia 9.5** ao plano de implementação
   - Executar `run_all_persistence_tests.sh` (já criado)
   - Validar que customizações persistem nas 4 novas páginas
   - **AÇÃO:** Integrar testes existentes ao fluxo

---

## 🎯 REFERÊNCIAS IMPORTANTES

### Código Existente que NÃO deve ser modificado:
- ✅ `metadata_fields_manager.py` - Sistema de `show_in_*` **JÁ FUNCIONA**
- ✅ `consul_manager.py` - Usa httpx async, **NÃO migrar** para python-consul
- ✅ Services.tsx e BlackboxTargets.tsx - **REFERÊNCIAS**, não base de código

### Código Novo que será criado:
- 🆕 `consul_kv_config_manager.py` - Cache KV com TTL
- 🆕 `categorization_rule_engine.py` - Motor de regras JSON
- 🆕 `dynamic_query_builder.py` - Templates PromQL com Jinja2
- 🆕 `monitoring_unified.py` - Endpoints `/data` e `/metrics`
- 🆕 `DynamicMonitoringPage.tsx` - Componente base único
- 🆕 `migrate_categorization_to_json.py` - Script de migração

---

## 📝 VALIDAÇÕES PRÉ-IMPLEMENTAÇÃO

Antes de iniciar a Fase 1, confirmar:

- [ ] Leu `docs/AJUSTES_CRITICOS_PLANO_V2.md` completamente
- [ ] Entendeu que Services.tsx é REFERÊNCIA, não base de código
- [ ] Confirmou que sistema de `show_in_*` já existe
- [ ] Entendeu estratégia dupla (Consul + Prometheus)
- [ ] Revisou script de migração de regras
- [ ] Sabe onde estão os testes de persistência (`backend/test_*.py`)

---

## 🚀 INÍCIO DA IMPLEMENTAÇÃO

Após validar todos os pontos acima:

1. **Fase 1 (Dias 1-2):** Preparação e análise
2. **Fase 2 (Dias 3-5):** Backend (componentes + endpoints)
3. **Fase 3 (Dias 6-8):** Frontend (DynamicMonitoringPage + rotas)
4. **Fase 4 (Dias 9-10):** Testes funcionais
5. **Fase 4.5 (Dia 9.5):** **NOVO** - Testes de persistência
6. **Fase 5 (Dia 11):** Deploy

**ESTIMATIVA AJUSTADA:** 12-13 dias (incluindo Dia 9.5)

---

**✅ PLANO VALIDADO E PRONTO PARA EXECUÇÃO**

**Próximo passo:** Iniciar Fase 1, Dia 1 - Análise e Setup
