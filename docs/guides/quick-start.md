# 🚀 Quick Start Guide - Consul Manager

## Início Rápido em 5 Minutos

### 1️⃣ Instalar Dependências Backend

```bash
cd backend
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate

pip install -r requirements.txt
```

### 2️⃣ Configurar Variáveis de Ambiente

Crie o arquivo `backend/.env`:

```env
CONSUL_HOST=localhost
CONSUL_PORT=8500
CONSUL_SCHEME=http
MAIN_SERVER=localhost
ENABLE_KV_STORAGE=true
```

### 3️⃣ Iniciar Backend

```bash
cd backend
python app.py
```

✅ Backend rodando em **http://localhost:5000**
✅ Swagger UI em **http://localhost:5000/docs**

---

### 4️⃣ Instalar Dependências Frontend

```bash
cd frontend
npm install
```

**Pacotes instalados:**
- React 19
- Ant Design Pro
- @ant-design/charts (gráficos)
- @dnd-kit (drag & drop)
- TypeScript

### 5️⃣ Iniciar Frontend

```bash
npm run dev
```

✅ Frontend rodando em **http://localhost:8080**

---

## 🎉 Pronto! Acesse a Aplicação

Abra o navegador em: **http://localhost:8080**

### Navegação Inicial

1. **Dashboard** (/) - Visão geral com métricas
2. **Serviços** (/services) - Gerenciar serviços do Consul
3. **Alvos Blackbox** (/blackbox) - Targets de monitoramento
4. **Grupos Blackbox** (/blackbox-groups) - Organizar targets
5. **Service Presets** (/presets) - Templates de serviços
6. **KV Store** (/kv-browser) - Navegador do KV
7. **Audit Log** (/audit-log) - Histórico de operações
8. **Instalar Exporters** (/installer) - SSH remote install

---

## 📝 Primeiros Passos

### Criar Presets Built-in

1. Vá em **Service Presets**
2. Os presets built-in são criados automaticamente:
   - node-exporter-linux
   - windows-exporter
   - blackbox-icmp
   - redis-exporter

### Criar um Alvo Blackbox

1. Vá em **Alvos Blackbox**
2. Clique em **"Novo Target"**
3. Preencha:
   - Module: `icmp` ou `http_2xx`
   - Company: Nome da empresa
   - Project: Nome do projeto
   - Environment: `prod`, `dev`, `staging`
   - Name: Nome descritivo
   - Instance: IP ou hostname

### Criar um Grupo

1. Vá em **Grupos Blackbox**
2. Clique em **"Novo Grupo"**
3. Preencha:
   - ID: `projeto-cliente-prod` (kebab-case)
   - Nome: "Projeto Cliente - Produção"
   - Descrição: Opcional
   - Tags: `producao, cliente-x`

### Registrar Serviço de Preset

1. Vá em **Service Presets**
2. Clique em **"Registrar"** em um preset
3. Preencha as variáveis:
   - `address`: IP do servidor
   - `env`: ambiente (prod/dev)
   - `datacenter`: nome do datacenter
   - `hostname`: identificador do host
4. Opcional: clique **"Preview"** para ver o payload
5. Clique **"Registrar Serviço"**

---

## 🔍 Testar Funcionalidades

### Dashboard

✅ Visualize métricas em tempo real
✅ Veja gráficos de distribuição
✅ Confira atividades recentes
✅ Use botões de ação rápida

### Busca Avançada

1. Vá em qualquer página com tabela
2. Clique em **"Busca Avançada"**
3. Adicione condições:
   - Campo: `Meta.company`
   - Operador: `eq` (igual)
   - Valor: nome da empresa
4. Adicione mais condições (+ botão)
5. Escolha **AND** ou **OR**
6. Clique **"Buscar"**

### KV Browser

1. Vá em **KV Store**
2. Navegue pela árvore à esquerda
3. Clique em uma chave para ver valor
4. Crie nova chave:
   - Chave: `skills/eye/test/my-key`
   - Valor: `{"test": "value"}` (JSON)

### Audit Log

1. Vá em **Audit Log**
2. Filtre por:
   - Período (date range)
   - Ação (create, update, delete)
   - Tipo de recurso
3. Clique em **"Ver Detalhes"** de qualquer evento

---

## 🧪 Testar Backend

### Via Swagger UI

1. Acesse **http://localhost:5000/docs**
2. Teste qualquer endpoint
3. Exemplo - Listar presets:
   - GET `/api/v1/presets`
   - Click "Try it out"
   - Execute

### Via cURL

```bash
# Listar serviços
curl http://localhost:5000/api/v1/services

# Obter health status
curl http://localhost:5000/api/v1/health/status

# Listar presets
curl http://localhost:5000/api/v1/presets

# Busca avançada
curl -X POST http://localhost:5000/api/v1/search/advanced \
  -H "Content-Type: application/json" \
  -d '{
    "conditions": [
      {"field": "Meta.company", "operator": "eq", "value": "Ramada"}
    ],
    "logical_operator": "and",
    "page": 1,
    "page_size": 20
  }'
```

---

## 🛠️ Troubleshooting

### Backend não inicia

**Erro:** `ModuleNotFoundError: No module named 'fastapi'`

**Solução:**
```bash
cd backend
pip install -r requirements.txt
```

### Frontend não inicia

**Erro:** `Cannot find module '@ant-design/charts'`

**Solução:**
```bash
cd frontend
npm install
```

### Consul não conecta

**Erro:** `Connection refused to localhost:8500`

**Solução:**
1. Verifique se Consul está rodando: `consul agent -dev`
2. Configure `.env` com IP correto do Consul

### Página em branco no frontend

**Solução:**
1. Abra DevTools (F12)
2. Veja erros no Console
3. Verifique se backend está rodando
4. Verifique se `api.ts` aponta para `http://localhost:5000`

---

## 📚 Documentação Completa

Para mais detalhes, consulte:

- **[README.md](README.md)** - Documentação principal
- **[PHASE3_SUMMARY.md](PHASE3_SUMMARY.md)** - Detalhes da Phase 3
- **[PHASE2_SUMMARY.md](PHASE2_SUMMARY.md)** - Service Presets e Search
- **[IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md)** - KV Store e Dual Storage
- **[MIGRATION_GUIDE.md](MIGRATION_GUIDE.md)** - Migração de dados

---

## 🎯 Próximos Passos Recomendados

1. ✅ Explore o Dashboard
2. ✅ Crie alguns presets customizados
3. ✅ Organize targets em grupos
4. ✅ Teste a busca avançada
5. ✅ Navegue pelo KV Store
6. ✅ Confira o Audit Log
7. ✅ Instale um exporter remotamente
8. ✅ Configure tema claro/escuro
9. ✅ Customize colunas das tabelas

---

## 💡 Dicas

- Use **auto-refresh** no Dashboard para monitorar em tempo real
- Salve suas **preferências de colunas** - elas são persistidas
- Use **Preview** antes de registrar serviços de presets
- **Grupos** ajudam a organizar centenas de targets
- **Audit Log** mostra quem fez o quê e quando
- **KV Browser** é útil para debug de configurações
- **Busca Avançada** economiza tempo em ambientes grandes

---

<div align="center">

**Pronto para produção! 🚀**

Se precisar de ajuda, consulte a [documentação completa](README.md)

</div>
