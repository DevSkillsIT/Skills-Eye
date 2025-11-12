# 📘 Guia Completo - Sistema de Naming Dinâmico

**Data:** 2025-11-12  
**Objetivo:** Explicar onde e como o sistema de naming é usado

---

## 🎯 O Que É o Sistema de Naming?

Sistema que **automaticamente adiciona sufixos aos nomes de serviços** baseado no site/datacenter, resolvendo conflitos de nomes em ambientes multi-site.

### Problema Que Resolve:
```
❌ SEM NAMING SYSTEM:
- Site Palmas: node_exporter
- Site Rio: node_exporter  ← CONFLITO! Mesmo nome
- Site DTC: node_exporter  ← CONFLITO! Mesmo nome

✅ COM NAMING SYSTEM (option2):
- Site Palmas: node_exporter (padrão - sem sufixo)
- Site Rio: node_exporter_rio
- Site DTC: node_exporter_dtc
```

---

## 📁 Arquivos Backend e Suas Funções

### 1. **`backend/core/naming_utils.py`** - CORE DO SISTEMA
**Função:** Biblioteca principal com toda lógica de naming

**Funções Principais:**
```python
# 1. Aplicar sufixo ao nome do serviço
apply_site_suffix(service_name, site=None, cluster=None) -> str
# Exemplo: apply_site_suffix("node_exporter", site="rio") → "node_exporter_rio"

# 2. Extrair site dos metadados
extract_site_from_metadata(meta: dict) -> str
# Exemplo: extract_site_from_metadata({"cluster": "rmd-ldc-cliente"}) → "rio"

# 3. Buscar site padrão
get_default_site() -> Optional[str]
# Retorna: "palmas" (site com is_default=true no KV)

# 4. Obter configuração de naming
get_naming_config() -> dict
# Retorna: {"naming_strategy": "option2", "suffix_enabled": True}
```

**🔍 Usado Por (Backend):**

1. **`backend/api/services.py`** - Criação/edição de Services
   ```python
   # Linha 403-407: Ao criar service
   site = extract_site_from_metadata(meta)
   suffixed_name = apply_site_suffix(original_name, site=site)
   # "node_exporter" → "node_exporter_rio"
   ```

2. **`backend/core/blackbox_manager.py`** - Blackbox Targets
   ```python
   # Aplica sufixo em targets blackbox
   suffixed_name = apply_site_suffix(target_name, site=site)
   ```

3. **`backend/api/settings.py`** - Endpoint de configuração
   ```python
   # GET /api/v1/settings/naming-config
   config = get_naming_config()
   default_site = get_default_site()
   ```

4. **`test_naming_baseline.py`** - Testes automatizados

**❌ NÃO é usado por `monitoring-types`** - Esse módulo extrai tipos de monitoramento do Prometheus, não lida com sufixos

---

### 2. **`backend/api/settings.py`** - ENDPOINTS DE CONFIGURAÇÃO
**Função:** Expõe configurações de naming para o frontend

**Endpoints:**

#### `GET /api/v1/settings/naming-config`
Retorna configuração de naming strategy
```json
{
  "naming_strategy": "option2",
  "suffix_enabled": true,
  "default_site": "palmas"
}
```

**🔍 Usado Por (Frontend):**
- **`frontend/src/pages/Services.tsx`** - Exibe estratégia ativa
- **Hook `useSites()`** - Carrega configuração global
- **Qualquer página que precise saber a estratégia de naming**

#### `GET /api/v1/settings/sites-config`
Retorna sites + naming em um único endpoint
```json
{
  "success": true,
  "sites": [
    {"code": "palmas", "name": "Palmas", "is_default": true, "color": "red"},
    {"code": "rio", "name": "Rio de Janeiro", "is_default": false, "color": "gold"},
    {"code": "dtc", "name": "Dtc", "is_default": false, "color": "blue"}
  ],
  "naming": {
    "strategy": "option2",
    "suffix_enabled": true
  },
  "default_site": "palmas",
  "total_sites": 3
}
```

**🔍 Usado Por (Frontend):**
- **Hook `useSites()`** - Principal consumidor
- **Qualquer componente que precise de lista de sites**

---

### 3. **`backend/api/metadata_fields_manager.py`** - GERENCIAMENTO VIA UI
**Função:** Endpoints para editar naming config pela interface web

**Endpoints:**

#### `PATCH /api/v1/metadata-fields/config/naming`
Atualiza naming_strategy e suffix_enabled
```bash
curl -X PATCH http://localhost:5000/api/v1/metadata-fields/config/naming \
  -H "Content-Type: application/json" \
  -d '{"naming_strategy": "option2", "suffix_enabled": true}'
```

**🔍 Usado Por (Frontend):**
- **`frontend/src/pages/MetadataFields.tsx`** - Card "Configuração Global de Naming Strategy"

#### `PATCH /api/v1/metadata-fields/config/sites/{code}`
Atualiza configurações de um site (name, color, is_default)

**🔍 Usado Por (Frontend):**
- **`frontend/src/pages/MetadataFields.tsx`** - Modal de edição de site

---

## 🖥️ Frontend - Onde Acessar e Validar

### 1. **Página Principal: Metadata Fields**
**URL:** `http://localhost:3000/metadata-fields`

**Aba: "Gerenciar Sites"**

#### Card 1: Configuração Global de Naming Strategy
```
┌─────────────────────────────────────────────────────┐
│ Configuração Global de Naming Strategy             │
│ ┌─────────────────────────────────────────────────┐ │
│ │ ⓘ Estas configurações afetam TODOS os sites    │ │
│ └─────────────────────────────────────────────────┘ │
│                                                     │
│ Estratégia de Nomenclatura: [Opção 2 ▼]            │
│ Sufixos Automáticos: [⚪ Habilitado]               │
│                                                     │
│ [Salvar Configuração Global]                        │
└─────────────────────────────────────────────────────┘
```

**Como Validar:**
1. Acesse `http://localhost:3000/metadata-fields`
2. Clique na aba **"Gerenciar Sites"**
3. Veja o card no topo: **"Configuração Global de Naming Strategy"**
4. Altere entre "Opção 1" e "Opção 2"
5. Desabilite/habilite sufixos
6. Clique **"Salvar Configuração Global"**
7. ✅ Deve mostrar: "Naming Strategy atualizada com sucesso!"

#### Tabela de Sites
```
┌───────────────────────────────────────────────────────────────────┐
│ Código │ Nome              │ Site Padrão      │ Cor    │ Ações    │
├───────────────────────────────────────────────────────────────────┤
│ PALMAS │ Palmas            │ ✓ Sim (sem sufixo)│ red    │ [Editar] │
│ RIO    │ Rio de Janeiro    │ ○ Não            │ gold   │ [Editar] │
│ DTC    │ Dtc               │ ○ Não            │ blue   │ [Editar] │
└───────────────────────────────────────────────────────────────────┘
```

**Como Validar:**
1. Clique em **"Editar"** em qualquer site
2. Altere **Nome**, **Cor** ou **Site Padrão**
3. Clique **"Salvar"**
4. ✅ Deve atualizar na tabela imediatamente

---

### 2. **Hook React: `useSites()`**
**Arquivo:** `frontend/src/hooks/useSites.tsx`

**Como Usar em Qualquer Componente:**
```tsx
import { useSites } from '../hooks/useSites';

function MeuComponente() {
  const { sites, namingConfig, defaultSite, getSiteByCode } = useSites();
  
  // sites: Lista de sites
  // namingConfig: {strategy, suffix_enabled}
  // defaultSite: Site padrão
  // getSiteByCode('rio'): Busca site específico
  
  return (
    <div>
      {sites.map(site => (
        <Tag key={site.code} color={site.color}>
          {site.name}
        </Tag>
      ))}
    </div>
  );
}
```

**Componentes Que Usam:**
- `Services.tsx` - Lista de serviços
- `Exporters.tsx` - Lista de exporters
- `BlackboxTargets.tsx` - Targets blackbox
- Qualquer página que precise de dados de sites

---

### 3. **Página Services - Validação Prática**
**URL:** `http://localhost:3000/services`

**Teste Prático:**

**Cenário 1: Criar Serviço no Site Padrão (Palmas)**
```
1. Clique em "Novo Service"
2. Nome: "teste_naming"
3. Site: "palmas" (padrão)
4. Salve

✅ Resultado: Nome final = "teste_naming" (SEM sufixo)
```

**Cenário 2: Criar Serviço em Site Não-Padrão (Rio)**
```
1. Clique em "Novo Service"
2. Nome: "teste_naming"
3. Site: "rio"
4. Salve

✅ Resultado: Nome final = "teste_naming_rio" (COM sufixo)
```

**Cenário 3: Desabilitar Sufixos**
```
1. Vá para Metadata Fields → Gerenciar Sites
2. Desabilite "Sufixos Automáticos"
3. Salve
4. Crie novo serviço em Rio com nome "teste2"

✅ Resultado: Nome final = "teste2" (SEM sufixo mesmo em Rio)
```

---

## 🔄 Fluxo Completo do Sistema

### Criação de Serviço (Services.tsx)

```
┌──────────────────────────────────────────────────────────────┐
│ FRONTEND (Services.tsx)                                      │
│                                                              │
│ 1. Usuário preenche formulário:                             │
│    - Nome: "node_exporter"                                   │
│    - Site: "rio"                                             │
│    - Outros campos...                                        │
│                                                              │
│ 2. Frontend envia POST /api/v1/services                      │
│    Body: {name: "node_exporter", Meta: {site: "rio"}}       │
└──────────────────────────────────────────────────────────────┘
                          ↓
┌──────────────────────────────────────────────────────────────┐
│ BACKEND (services.py)                                        │
│                                                              │
│ 3. Recebe request                                            │
│    original_name = "node_exporter"                           │
│    meta = {site: "rio"}                                      │
│                                                              │
│ 4. Extrai site:                                              │
│    site = extract_site_from_metadata(meta)  # → "rio"       │
│                                                              │
│ 5. Aplica sufixo:                                            │
│    final_name = apply_site_suffix(original_name, site)       │
│    # → "node_exporter_rio"                                   │
│                                                              │
│ 6. Registra no Consul com nome final                         │
└──────────────────────────────────────────────────────────────┘
                          ↓
┌──────────────────────────────────────────────────────────────┐
│ CONSUL                                                       │
│                                                              │
│ 7. Service registrado:                                       │
│    Name: "node_exporter_rio"                                 │
│    Meta: {site: "rio", ...}                                  │
└──────────────────────────────────────────────────────────────┘
```

---

## 🔧 Troubleshooting

### Problema: Sufixos não estão sendo aplicados

**Verificar:**
1. Naming strategy está em "option2"?
   ```bash
   curl http://localhost:5000/api/v1/settings/naming-config
   ```

2. Sufixos estão habilitados?
   ```json
   {"suffix_enabled": true}
   ```

3. Site tem `is_default=true`?
   - Se sim, serviços NESSE site não recebem sufixo
   - Outros sites recebem sufixo normalmente

### Problema: Site padrão retorna null

**Solução:**
1. Marque um site como padrão:
   - Metadata Fields → Gerenciar Sites
   - Editar site → Checkbox "Site Padrão"
   - Salvar

### Problema: Alterações não refletem

**Solução:**
1. Reinicie backend:
   ```bash
   ./restart-backend.sh
   ```

2. Limpe cache do browser (Ctrl+Shift+R)

---

## 📊 Arquivos Relacionados - Resumo

### Backend (4 arquivos principais)
| Arquivo | Função | Usado Por |
|---------|--------|-----------|
| `core/naming_utils.py` | Lógica CORE | services.py, blackbox_manager.py, settings.py |
| `api/settings.py` | Endpoints de config | Frontend (useSites hook) |
| `api/services.py` | Criação de services | Frontend (Services.tsx) |
| `api/metadata_fields_manager.py` | Gerenciamento UI | Frontend (MetadataFields.tsx) |

### Frontend (3 arquivos principais)
| Arquivo | Função | Acesso |
|---------|--------|--------|
| `hooks/useSites.tsx` | Hook dinâmico | Usado por todos componentes |
| `pages/MetadataFields.tsx` | UI de gerenciamento | `/metadata-fields` aba "Gerenciar Sites" |
| `pages/Services.tsx` | Criação de services | `/services` |

### Testes
| Arquivo | Função |
|---------|--------|
| `test_naming_baseline.py` | Testes automatizados (11/12 passando) |

---

## ✅ Checklist de Validação Completa

- [ ] **Backend rodando:** `./restart-backend.sh` → OK
- [ ] **Acessar UI:** http://localhost:3000/metadata-fields → Aba "Gerenciar Sites"
- [ ] **Ver configuração atual:** Card "Configuração Global" mostra option2 + sufixos habilitados
- [ ] **Ver sites:** Tabela mostra 3 sites (Palmas, Rio, DTC)
- [ ] **Editar naming:** Alterar strategy → Salvar → Mensagem de sucesso
- [ ] **Editar site:** Clicar Editar → Alterar nome/cor → Salvar → Atualiza na tabela
- [ ] **Criar service Palmas:** Nome final SEM sufixo
- [ ] **Criar service Rio:** Nome final COM sufixo `_rio`
- [ ] **API naming-config:** `curl http://localhost:5000/api/v1/settings/naming-config` retorna JSON válido
- [ ] **API sites-config:** `curl http://localhost:5000/api/v1/settings/sites-config` retorna sites + naming

---

## 🎓 Resumo Executivo

**Sistema de Naming:**
- ✅ Totalmente dinâmico via KV
- ✅ Gerenciável 100% via UI web
- ✅ Usado automaticamente ao criar Services/Exporters/Blackbox
- ✅ Portável (funciona para qualquer empresa)
- ✅ 11/12 testes automatizados passando

**Onde Validar:**
1. **UI Principal:** Metadata Fields → Gerenciar Sites
2. **Teste Prático:** Services → Criar novo serviço em site diferente
3. **API:** curl endpoints /naming-config e /sites-config

**Não Usado Por:**
- ❌ monitoring-types (extração de tipos do Prometheus)
- ❌ prometheus-config (edição de YAML)
- ❌ reference-values (valores de referência)

**Usado Por:**
- ✅ Services (criação/edição)
- ✅ Exporters (criação/edição)
- ✅ Blackbox Targets (criação/edição)
- ✅ Qualquer componente que use hook useSites()
