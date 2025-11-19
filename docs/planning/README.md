# 📋 Planejamento & Roadmap

Documentação de roadmap, sprints e planejamento futuro do projeto.

## 🎯 Roadmap

Este diretório contém **16 documentos** sobre planejamento e direção futura.

### Fases Planejadas

- **Phase 1** - KV Namespace e Dual Storage (Implementado)
- **Phase 2** - Service Presets e Advanced Search (Implementado)
- **Phase 3** - Frontend Modernization (Implementado)
- **P0-P2** - Performance Optimization (Implementado)
- **Future** - Clean Architecture Refactoring (Planejado)

### Documentação de Planejamento

| Documento | Descrição |
|-----------|-----------|
| **refactoring-plan.md** | Plano detalhado de refatoração futura |
| **refactoring-architecture.md** | Proposta de Clean Architecture |
| **Sprints** | Planejamento de sprints específicas |
| **Mais planos** | Documentação adicional de roadmap |

## 🚀 Visão Futura

### Clean Architecture
- Separação clara de camadas (Domain → Application → Infrastructure)
- CQRS pattern para queries complexas
- Event sourcing para auditoria

### Melhorias Técnicas
- Testes automatizados (unit + integration)
- Docker Compose para deploy fácil
- Kubernetes service discovery
- Dashboard customizável com widgets
- Alerting rules editor
- Grafana dashboard generator
- CLI tool para automação
- Backup/restore automático

## 🔗 Relacionados

- [Histórico de Implementação](../history/) - Fases já realizadas
- [Performance](../performance/) - Otimizações completadas
- [Arquitetura](../developer/architecture/) - Design atual

## 📈 Status de Implementação

**Completado:**
- ✅ Sistema de monitoring types dinâmico
- ✅ Multi-site Prometheus com replicação
- ✅ Campos dinâmicos extraídos do Prometheus
- ✅ Reference values com auto-cadastro
- ✅ Context API para performance
- ✅ Multi-connector installer (SSH/WinRM/PSExec)
- ✅ Editor YAML remoto com preservação de comentários
- ✅ Cache inteligente multi-layer

**Em Planejamento:**
- [ ] Refatoração arquitetural (Clean Architecture)
- [ ] Testes automatizados (unit + integration)
- [ ] Docker Compose para deploy
- [ ] Kubernetes service discovery
- [ ] Dashboard customizável
- [ ] Alerting rules editor
- [ ] Grafana dashboard generator
- [ ] CLI tool
- [ ] Backup/restore automático

---

[⬆ Voltar ao índice de documentação](../DOCUMENTATION_INDEX.md)
