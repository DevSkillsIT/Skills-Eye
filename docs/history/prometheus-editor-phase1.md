# Editor de Configurações YAML do Prometheus - FASE 1 (MVP) ✅

## 🎯 DECISÃO ARQUITETURAL

### ❌ SEM BANCO DE DADOS
Após análise, concluímos que **banco de dados é desnecessário**:
- **YAML é a fonte da verdade** - Prometheus lê dele
- **Duplicação = Problema** - Ter dados no banco E YAML cria conflitos
- **Filesystem suficiente** - Backups em arquivos `.bak`

### ✅ ARQUITETURA IMPLEMENTADA
```
Frontend React → API REST → YAML Service → prometheus.yml
                            ↓
                         Backups (.bak)
                         Audit Log (JSON)
```

---

## 📦 O QUE FOI IMPLEMENTADO

### 1. Backend - Serviços Core

#### 📄 `backend/core/yaml_config_service.py`
**Serviço principal de manipulação de YAML**

**Funcionalidades**:
- ✅ **Leitura** de `prometheus.yml` com preservação de formatação
- ✅ **Parse** para estrutura Python dict
- ✅ **CRUD completo** de jobs (create, read, update, delete)
- ✅ **Validação** com `promtool` antes de salvar
- ✅ **Backup automático** ao modificar (com metadados JSON)
- ✅ **Restore** de backups anteriores
- ✅ **Reload** do Prometheus via API (POST /-/reload)
- ✅ **Preview** de YAML antes de aplicar
- ✅ **Audit log** de todas as mudanças

**Tecnologias**:
- `ruamel.yaml` - Preserva comentários e formatação
- `subprocess` - Validação com promtool
- `requests` - Reload do Prometheus

**Exemplo de uso**:
```python
service = YamlConfigService()

# Listar jobs
jobs = service.get_all_jobs()

# Criar novo job
service.create_job({
    'job_name': 'https_monitoring',
    'scrape_interval': '30s',
    'consul_sd_configs': [...]
})

# Validar + Backup + Salvar
service.save_config(config, "Adicionado monitoramento HTTPS")

# Recarregar Prometheus
service.reload_prometheus()
```

---

#### 📄 `backend/core/fields_extraction_service.py`
**Serviço de extração de campos metadata dinâmicos**

**Funcionalidades**:
- ✅ **Análise automática** de `relabel_configs`
- ✅ **Identificação de campos** Consul metadata (`__meta_consul_service_metadata_*`)
- ✅ **Inferência de tipos** (string, number, select)
- ✅ **Enriquecimento** com valores únicos do Consul
- ✅ **Validação** de metadata de serviços
- ✅ **Sugestão de campos** baseado em serviços existentes
- ✅ **Estatísticas** por campo (contagens, top values)

**Campos detectados automaticamente**:
```python
{
    "name": "company",
    "display_name": "Empresa",
    "source_label": "__meta_consul_service_metadata_company",
    "field_type": "select",
    "required": True,
    "show_in_table": True,
    "show_in_dashboard": True,
    "options": ["Skills", "ClienteX", "ClienteY"]  # Do Consul
}
```

**Exemplo de uso**:
```python
service = FieldsExtractionService(consul_manager)

# Extrair campos de jobs
fields = service.extract_fields_from_jobs(jobs)

# Enriquecer com valores do Consul
fields = await service.enrich_fields_with_values(fields)

# Sugerir novos campos
suggested = service.suggest_fields_from_services(consul_services)
```

---

### 2. Backend - API REST

#### 📄 `backend/api/prometheus_config.py`
**API completa para gerenciar configurações**

**Endpoints implementados**:

##### 📚 Listagem e Leitura
```
GET  /api/v1/prometheus-config/jobs
     → Lista todos os scrape jobs

GET  /api/v1/prometheus-config/jobs/{job_name}
     → Detalhes de um job específico

GET  /api/v1/prometheus-config/fields?enrich_with_values=true
     → Campos metadata extraídos dos relabels
     → Usado para gerar formulários dinâmicos!

GET  /api/v1/prometheus-config/fields/{field_name}/values
     → Valores únicos de um campo + estatísticas
```

##### ✏️ CRUD de Jobs
```
POST   /api/v1/prometheus-config/jobs
       → Criar novo job

PUT    /api/v1/prometheus-config/jobs/{job_name}
       → Atualizar job existente

DELETE /api/v1/prometheus-config/jobs/{job_name}
       → Remover job
```

##### 🔍 Preview e Aplicação
```
GET  /api/v1/prometheus-config/preview
     → Preview do YAML atual

POST /api/v1/prometheus-config/apply
     → Valida → Backup → Salva → Reload

POST /api/v1/prometheus-config/reload
     → Recarrega Prometheus sem mudar config
```

##### 💾 Backups
```
GET  /api/v1/prometheus-config/backups
     → Lista todos os backups

POST /api/v1/prometheus-config/backups/create
     → Criar backup manual

POST /api/v1/prometheus-config/backups/{filename}/restore
     → Restaurar backup
```

##### 🔧 Utilitários
```
POST /api/v1/prometheus-config/validate
     → Valida config sem salvar

GET  /api/v1/prometheus-config/suggest-fields
     → Sugere campos baseado em serviços existentes
```

---

### 3. Integração

#### ✅ Registrado em `backend/app.py`
```python
from api.prometheus_config import router as prometheus_config_router

app.include_router(
    prometheus_config_router,
    prefix="/api/v1",
    tags=["prometheus-config"]
)
```

#### ✅ Dependência adicionada
```
# requirements.txt
ruamel.yaml==0.18.5
```

---

## 🚀 PRÓXIMOS PASSOS

### FASE 2 - Frontend (Próxima)

#### Página Principal: `ConfigEditor.tsx`
- Tabela listando todos os jobs
- Botão "Adicionar Job"
- Modal de edição visual
- Preview do YAML (Monaco Editor)
- Validação em tempo real

#### Componentes:
- `JobsTable` - Lista de jobs
- `JobForm` - Formulário dinâmico
- `YamlPreview` - Editor Monaco
- `BackupsList` - Gestão de backups

### FASE 3 - Integração (Depois)

#### Atualizar páginas existentes:
- `Services.tsx` - Usar campos dinâmicos da API `/fields`
- `Exporters.tsx` - Formulários baseados em `/fields`
- `Dashboard.tsx` - Métricas por campos dinâmicos

---

## 📊 BENEFÍCIOS JÁ OBTIDOS

### ✅ Sem Banco de Dados
- Sem duplicação de dados
- Sem risco de dessincronia
- Mais simples de manter

### ✅ YAML como Fonte Única
- Prometheus lê direto do arquivo
- Git-friendly (pode versionar)
- Portável (copiar arquivo = copiar config)

### ✅ Validação Garantida
- Promtool valida antes de salvar
- Backup automático antes de mudanças
- Rollback fácil se der errado

### ✅ Campos Dinâmicos
- Frontend se adapta automaticamente aos relabels
- Novos campos no YAML = Novos campos no form
- Não precisa hardcode no frontend

---

## 🧪 COMO TESTAR

### 1. Instalar dependência
```bash
cd backend
pip install ruamel.yaml==0.18.5
```

### 2. Reiniciar backend
```bash
python app.py
```

### 3. Testar endpoints
```bash
# Listar jobs
curl http://localhost:5000/api/v1/prometheus-config/jobs

# Obter campos dinâmicos
curl http://localhost:5000/api/v1/prometheus-config/fields?enrich_with_values=true

# Preview do YAML
curl http://localhost:5000/api/v1/prometheus-config/preview

# Listar backups
curl http://localhost:5000/api/v1/prometheus-config/backups
```

### 4. Ver documentação interativa
```
http://localhost:5000/docs#/prometheus-config
```

---

## 📝 CONFIGURAÇÃO NECESSÁRIA

### Arquivo prometheus.yml esperado em:
```
/etc/prometheus/prometheus.yml (Linux)
C:\prometheus\prometheus.yml (Windows)
```

### Ou customizar path:
```python
service = YamlConfigService(config_path="/caminho/custom/prometheus.yml")
```

### Promtool deve estar no PATH:
```bash
# Verificar
promtool --version

# Ou especificar path
service.promtool_path = "/usr/local/bin/promtool"
```

---

## 🎉 RESUMO

**FASE 1 (MVP) COMPLETA** ✅

✅ Backend completamente implementado
✅ API REST funcional
✅ Validação com promtool
✅ Backup automático
✅ Campos dinâmicos extraídos
✅ Sem banco de dados (decisão correta!)

**Próximo passo**: Criar frontend React para visualizar e editar!

---

## 📚 ARQUIVOS CRIADOS

```
backend/
├── core/
│   ├── yaml_config_service.py         ✅ NOVO - 500+ linhas
│   └── fields_extraction_service.py   ✅ NOVO - 400+ linhas
├── api/
│   └── prometheus_config.py           ✅ NOVO - 600+ linhas
├── app.py                             ✅ MODIFICADO (+ router)
└── requirements.txt                   ✅ MODIFICADO (+ ruamel.yaml)
```

**Total**: ~1.500 linhas de código backend funcional!
