# ⚡ Otimizações SSH

Otimizações e decisões sobre conexões SSH no Skills Eye.

## 🚀 Análise SSH Completa

Este diretório contém **1 documento** analisando otimizações de SSH.

### Conteúdo

- **ANALISE_SSH_COMPLETA.md** - Análise detalhada de SSH, decisões de migração Paramiko vs AsyncSSH

### Decisões de Implementação

#### AsyncSSH + TAR (P2 - Implementado)
Recomendado para:
- ✅ Múltiplos arquivos de múltiplos servidores
- ✅ Hot path (endpoints frequentes)
- ✅ Operações bulk/batch
- ✅ Cold start crítico (ganho: 79% mais rápido!)

#### Paramiko (Mantido)
Recomendado para:
- ✅ Operações individuais
- ✅ Operações interativas (instaladores)
- ✅ Operações raras
- ✅ Single-server local

## 📊 Resultados de Performance

**Antes (Paramiko):** 22.0s
**Depois (AsyncSSH + TAR):** 2.4s
**Ganho:** 79% mais rápido! ✅

## 🔗 Relacionados

- [Performance](../performance/) - Relatórios completos de otimização
- [Arquitetura](../developer/architecture/) - Detalhes técnicos de implementação
- [Histórico](../history/) - Fases de implementação da otimização

---

[⬆ Voltar ao índice de documentação](../DOCUMENTATION_INDEX.md)
