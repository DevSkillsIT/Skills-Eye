# Scripts Deprecated - NÃO USAR

## ❌ populate_external_labels.py.deprecated

**Status:** OBSOLETO - não usar mais!

**Problema:** Tinha hardcoding de:
- IPs de servidores (172.16.1.26, 172.16.200.14, etc)
- External labels estáticos por site
- Clusters hardcoded

**Substituído por:**
- Extração automática via SSH do prometheus.yml
- Endpoint: `POST /api/v1/metadata-fields/force-extract`
- External labels são extraídos em tempo real e salvos no KV
- Comando: "Sincronizar com Prometheus" no frontend

**Por que foi criado:**
- Migração inicial quando sistema ainda não tinha extração SSH
- População manual dos dados

**Por que está deprecated:**
- Sistema agora é 100% dinâmico
- External labels vêm do prometheus.yml via SSH
- Não precisa mais de população manual
- Hardcoding viola princípio de portabilidade

---

## ✅ Como fazer agora:

1. **Via Frontend:**
   - Ir em MetadataFields
   - Clicar em "Sincronizar com Prometheus"
   - Aguardar extração SSH
   - External labels são salvos automaticamente no KV

2. **Via API:**
   ```bash
   curl -X POST http://localhost:5000/api/v1/metadata-fields/force-extract
   ```

3. **Resultado:**
   - External labels extraídos do prometheus.yml
   - Salvos em `skills/eye/metadata/fields` (KV)
   - Sites auto-populados em `skills/eye/metadata/sites` (KV)
   - Tudo dinâmico, zero hardcoding

---

## 📌 Princípio:

**NUNCA hardcode dados de infraestrutura em scripts!**
- ✅ Extrair via SSH/API
- ✅ Salvar em KV
- ✅ Usar via endpoints
- ❌ Hardcoding de IPs, clusters, external_labels

Data: 2025-11-12
