# 🚨 CORREÇÕES URGENTES: Estrutura KV e Remoção de Órfãos

## 🔴 PROBLEMA 1: Estrutura do KV skills/eye/metadata/sites MUDOU

### ESTRUTURA ANTIGA (settings.py - CORRETA):
```json
{
  "sites": [
    {
      "code": "palmas",
      "name": "Palmas (TO)",
      "is_default": true,
      "color": "blue",
      "prometheus_host": "172.16.1.26",
      "prometheus_port": 9090,
      "external_labels": {"site": "palmas", "datacenter": "genesis"}
    },
    {
      "code": "rio",
      "name": "Rio Ramada",
      "is_default": false,
      "color": "green"
    }
  ]
}
```

### ESTRUTURA NOVA (metadata_fields_manager.py - **ERRADA**):
```json
{
  "palmas": {
    "name": "Palmas (TO)",
    "color": "blue",
    "is_default": true
  },
  "rio": {
    "name": "Rio Ramada",
    "color": "green",
    "is_default": false
  }
}
```

### ❌ POR QUE ISSO É UM PROBLEMA:

1. **Código antigo em settings.py ainda usa estrutura antiga** (linha 80-95)
2. **populate_external_labels.py usa estrutura antiga** (linha 52, 82)
3. **Queries no Consul KV quebram** - esperam array `sites[]`, não dict
4. **Frontend pode quebrar** se buscar estrutura antiga

### ✅ SOLUÇÃO:

**MANTER estrutura ANTIGA (array) no KV `skills/eye/metadata/sites`**

**MOTIVOS:**
- Compatibilidade retroativa com código existente
- Mais fácil iterar (array vs dict keys)
- Estrutura já testada e funcionando em produção
- Permite adicionar campos futuros sem breaking changes

---

## 🔴 PROBLEMA 2: Remoção de Campos Órfãos

### SITUAÇÃO ATUAL:

**Backend:**
- ✅ Endpoint `POST /metadata-fields/remove-orphans` existe (linha 1916)
- ✅ Aceita `{"field_names": ["campo1", "campo2"]}`
- ✅ Remove campos do KV

**Frontend:**
- ❌ **NÃO TEM botão "Remover" na tabela de campos**
- ❌ Comentário linha 1798: "Botão DELETE removido - campos vêm do Prometheus"
- ❌ Usuário NÃO consegue remover órfãos manualmente

### ❌ POR QUE ISSO É UM PROBLEMA:

1. **Campos órfãos acumulam no KV** (removidos do Prometheus mas não do KV)
2. **Usuário não tem como limpar** sem acessar backend diretamente
3. **Status "missing" fica forever** sem ação do usuário

### ✅ SOLUÇÃO:

**Adicionar botão "Remover" CONDICIONAL na tabela:**
- Mostrar APENAS quando `sync_status === 'missing'` (órfão)
- Chamar `POST /metadata-fields/remove-orphans`
- Confirmar remoção com Popconfirm

**LÓGICA:**
```tsx
{record.sync_status === 'missing' && (
  <Popconfirm
    title="Remover Campo Órfão?"
    description={`Campo "${record.name}" não existe no Prometheus. Deseja removê-lo do KV?`}
    onConfirm={() => handleRemoveOrphan(record.name)}
    okText="Sim, remover"
    cancelText="Não"
  >
    <Button type="link" danger size="small" icon={<DeleteOutlined />}>
      Remover
    </Button>
  </Popconfirm>
)}
```

---

## 📋 CHECKLIST DE CORREÇÕES

### 1. CORRIGIR ESTRUTURA KV (PRIORIDADE MÁXIMA)

- [ ] Reverter `metadata_fields_manager.py` para usar array `{"sites": [...]}`
- [ ] Atualizar `GET /config/sites` (linha 2355-2470)
- [ ] Atualizar `PATCH /config/sites/{code}` (linha 2479-2566)
- [ ] Atualizar `POST /config/sites/sync` (linha 2570-2654)
- [ ] Atualizar `POST /config/sites/cleanup` (linha 2655-2743)
- [ ] Testar todas as operações (GET/PATCH/POST)

### 2. ADICIONAR BOTÃO REMOVER ÓRFÃOS NO FRONTEND

- [ ] Adicionar handler `handleRemoveOrphan` em MetadataFields.tsx
- [ ] Adicionar botão condicional na coluna "Ações" (linha 1760-1798)
- [ ] Adicionar Popconfirm para confirmar remoção
- [ ] Testar remoção de campo órfão
- [ ] Atualizar tabela após remoção (reload)

### 3. CRIAR SCRIPT DE MIGRAÇÃO (SE NECESSÁRIO)

Se já existe KV com estrutura nova (dict), criar script para migrar:

```python
# migrate_sites_kv_structure.py
import asyncio
from core.kv_manager import KVManager

async def migrate():
    kv = KVManager()
    
    # Ler estrutura atual
    current = await kv.get_json('skills/eye/metadata/sites')
    
    # Se já é array, não fazer nada
    if isinstance(current, dict) and 'sites' in current:
        print("✅ Estrutura já está correta (array)")
        return
    
    # Se é dict (nova estrutura ERRADA), converter para array
    if isinstance(current, dict) and 'sites' not in current:
        print("⚠️  Estrutura errada detectada, convertendo...")
        sites_array = []
        for code, config in current.items():
            site = {"code": code, **config}
            sites_array.append(site)
        
        # Salvar estrutura correta
        await kv.put_json('skills/eye/metadata/sites', {"sites": sites_array})
        print(f"✅ Migrados {len(sites_array)} sites para estrutura de array")

if __name__ == '__main__':
    asyncio.run(migrate())
```

---

## 🎯 PRIORIDADES

1. **URGENTE:** Corrigir estrutura KV (quebra compatibilidade)
2. **IMPORTANTE:** Adicionar botão remover órfãos (UX crítica)
3. **OPCIONAL:** Script de migração (se KV já foi alterado)

---

## 📝 NOTAS TÉCNICAS

### Por que array é melhor que dict para sites?

**Array `{"sites": [...]}`:**
- ✅ Fácil iterar: `for site in sites`
- ✅ Ordem preservada
- ✅ Compatível com código legado
- ✅ Estrutura padrão REST API

**Dict `{"code": {...}}`:**
- ❌ Precisa iterar keys: `for code, config in sites.items()`
- ❌ Ordem não garantida (Python <3.7)
- ❌ Quebra código existente
- ❌ Menos idiomático para listas

### Por que remoção manual de órfãos?

**Automática (backend):**
- ❌ Pode deletar campos temporariamente removidos
- ❌ Sem controle do usuário
- ❌ Perda de dados acidental

**Manual (frontend):**
- ✅ Usuário decide o que remover
- ✅ Popconfirm evita acidentes
- ✅ Auditável (usuário sabe o que fez)
- ✅ Reversível (pode re-extrair depois)

---

## 🚀 PRÓXIMOS PASSOS

1. Implementar correções da estrutura KV
2. Testar endpoints após correção
3. Adicionar botão remover no frontend
4. Testar fluxo completo end-to-end
5. Documentar mudanças no CHANGELOG

