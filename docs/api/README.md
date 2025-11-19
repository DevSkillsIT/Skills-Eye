# 🔌 API Reference

Documentação completa da API REST do Skills Eye.

## 📚 Documentação de API

### Endpoints Reference

- **[Endpoints Reference](endpoints-reference.md)** - Referência completa de todos os 100+ endpoints da API
  - Documentação de todas as rotas REST
  - Schemas de request/response
  - Exemplos de uso
  - Códigos de erro

## 🚀 Acesso Rápido

**Swagger UI Interativo:**
```
http://localhost:5000/docs
```
Quando o backend estiver rodando, acesse o Swagger UI para explorar todos os endpoints interativamente.

## 📡 Base URL

```
http://localhost:5000/api/v1
```

## 🔑 Principais Módulos de API

| Módulo | Documentação | Endpoints | Descrição |
|--------|--------------|-----------|-----------|
| **Services** | Endpoints Reference | 10 | CRUD + bulk + search de serviços Consul |
| **Monitoring Types** | Endpoints Reference | 5 | Tipos de monitoramento (detecção dinâmica) |
| **Metadata Fields** | Endpoints Reference | 10 | Campos dinâmicos + sincronização SSH |
| **Reference Values** | Endpoints Reference | 6 | Auto-cadastro de valores permitidos |
| **Blackbox Targets** | Endpoints Reference | 6 | Gerenciamento de alvos de probes |
| **Blackbox Groups** | Endpoints Reference | 4 | Organização de targets |
| **Search** | Endpoints Reference | 8 | Busca avançada com 12 operadores |
| **Prometheus Config** | Endpoints Reference | 12 | Editor YAML remoto via SSH |
| **Dashboard** | Endpoints Reference | 2 | Métricas agregadas com cache |
| **Health** | Endpoints Reference | 2 | Status e conectividade |

## 🏗️ Padrão de Resposta

Todas as respostas da API seguem este padrão:

```json
{
  "success": true,
  "data": {},
  "message": "Descrição da resposta",
  "timestamp": "2025-11-19T14:00:00Z"
}
```

## 🔐 Autenticação

A API pode requerer tokens de autorização. Veja [Guides - Security](../guides/) para detalhes de configuração.

## 📖 Próximos Passos

1. **Começar:** Acesse [endpoints-reference.md](endpoints-reference.md)
2. **Explorar:** Teste no [Swagger UI](http://localhost:5000/docs)
3. **Integrar:** Consulte exemplos de integração nos guias

---

[⬆ Voltar ao índice de documentação](../DOCUMENTATION_INDEX.md)
