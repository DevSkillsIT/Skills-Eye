# 📋 TODO COMPLEMENTAR - CLAUDE CODE WEB

**Data:** 13/11/2025  
**Status:** ⚠️ ITENS FALTANTES NO PLANO ATUAL DO CLAUDE CODE

---

## 🚨 ITENS CRÍTICOS FALTANDO

### ❌ FALTOU: Dia 5 - Script de Migração de Categorização

**Status:** NÃO está no TODO do Claude Code  
**Prioridade:** 🔴 ALTA - Necessário ANTES de criar API unificada

**O QUE FAZER:**
```markdown
 FASE 2 - Backend: Criar script migrate_categorization_to_json.py (DIA 3 - MANHÃ)
  
  📝 DESCRIÇÃO:
  Script Python que extrai as 40+ regras de categorização hardcoded 
  do arquivo monitoring_types_dynamic.py e migra para JSON no Consul KV.
  
  📍 LOCALIZAÇÃO:
  - Arquivo: backend/migrate_categorization_to_json.py
  - Namespace KV: skills/eye/monitoring-types/categorization/rules
  
  🎯 FUNCIONALIDADES:
  1. Extrair padrões EXPORTER_PATTERNS do monitoring_types_dynamic.py
  2. Extrair módulos BLACKBOX_MODULES
  3. Converter para estrutura JSON com prioridades
  4. Salvar no Consul KV
  5. Validar que regras foram salvas corretamente
  
  📦 ESTRUTURA JSON ESPERADA:
  {
    "version": "1.0.0",
    "last_updated": "2025-11-13T14:00:00",
    "total_rules": 45,
    "rules": [
      {
        "id": "blackbox_icmp",
        "priority": 100,
        "category": "network-probes",
        "display_name": "Blackbox: ICMP Ping",
        "conditions": {
          "job_name_pattern": "^icmp.*",
          "metrics_path": "/probe",
          "module_pattern": "^icmp$"
        }
      },
      {
        "id": "exporter_mysql",
        "priority": 80,
        "category": "database-exporters",
        "display_name": "MySQL Exporter",
        "exporter_type": "mysqld_exporter",
        "conditions": {
          "job_name_pattern": "^mysql.*",
          "metrics_path": "/metrics"
        }
      }
      // ... mais 43 regras
    ],
    "default_category": "custom-exporters",
    "categories": [
      {"id": "network-probes", "display_name": "Network Probes (Rede)"},
      {"id": "web-probes", "display_name": "Web Probes (Aplicações)"},
      {"id": "system-exporters", "display_name": "Exporters: Sistemas"},
      {"id": "database-exporters", "display_name": "Exporters: Bancos de Dados"},
      {"id": "infrastructure-exporters", "display_name": "Exporters: Infraestrutura"},
      {"id": "hardware-exporters", "display_name": "Exporters: Hardware"},
      {"id": "network-devices", "display_name": "Dispositivos de Rede"},
      {"id": "custom-exporters", "display_name": "Exporters Customizados"}
    ]
  }
  
  🔧 CÓDIGO BASE (localizar em monitoring_types_dynamic.py):
  ```python
  # Linha ~85-120: EXPORTER_PATTERNS (40+ padrões)
  EXPORTER_PATTERNS = {
      'haproxy': ('infrastructure-exporters', 'HAProxy Exporter', 'haproxy_exporter'),
      'nginx': ('infrastructure-exporters', 'Nginx Exporter', 'nginx_exporter'),
      'mysql': ('database-exporters', 'MySQL Exporter', 'mysqld_exporter'),
      'postgres': ('database-exporters', 'PostgreSQL Exporter', 'postgres_exporter'),
      'redis': ('database-exporters', 'Redis Exporter', 'redis_exporter'),
      'mongodb': ('database-exporters', 'MongoDB Exporter', 'mongodb_exporter'),
      'node': ('system-exporters', 'Node Exporter (Linux)', 'node_exporter'),
      'windows': ('system-exporters', 'Windows Exporter', 'windows_exporter'),
      'snmp': ('system-exporters', 'SNMP Exporter', 'snmp_exporter'),
      # ... mais 30+ padrões
  }
  
  # Linha ~70-82: Módulos Blackbox
  BLACKBOX_MODULES = ['icmp', 'ping', 'tcp_connect', 'tcp', 'dns', 'ssh', 
                      'http_2xx', 'http_4xx', 'https', 'http_post', 'http_get']
  ```
  
  ⚡ EXECUÇÃO:
  ```bash
  cd /home/adrianofante/projetos/Skills-Eye/backend
  python migrate_categorization_to_json.py
  
  # Saída esperada:
  # 🔄 Iniciando migração de regras de categorização...
  # 📦 Convertendo regras de Blackbox...
  #   ✅ 11 regras de Blackbox
  # 📦 Convertendo regras de Exporters...
  #   ✅ 34 regras de Exporters
  # 💾 Salvando no Consul KV...
  #   ✅ Regras salvas em: skills/eye/monitoring-types/categorization/rules
  # ✅ MIGRAÇÃO CONCLUÍDA COM SUCESSO!
  ```
  
  ✅ VALIDAÇÃO:
  ```bash
  # Verificar no Consul KV
  curl "http://172.16.1.26:8500/v1/kv/skills/eye/monitoring-types/categorization/rules?pretty"
  
  # Deve retornar JSON com 45 regras
  ```
  
  ⚠️ IMPORTANTE:
  - Executar ANTES de criar CategorizationRuleEngine
  - Executar ANTES de criar API unificada
  - Validar que TODAS as 40+ regras foram migradas
  - Não remover código hardcoded ainda (será removido após testes)
```

---

### ❌ FALTOU: Dia 9.5 - Testes de Persistência

**Status:** NÃO está no TODO do Claude Code  
**Prioridade:** 🟡 MÉDIA - Necessário para validação de qualidade

**O QUE FAZER:**
```markdown
 FASE 4 - Testes: Executar Testes de Persistência Completos (DIA 9.5)
  
  📝 DESCRIÇÃO:
  Executar bateria completa de testes de persistência que JÁ EXISTEM
  no backend para validar que customizações de metadata fields NÃO
  são perdidas após reinícios, sincronizações ou cache clears.
  
  📍 ARQUIVOS DE TESTE EXISTENTES:
  - backend/test_fields_merge.py (testes básicos de merge)
  - backend/test_all_scenarios.py (8 cenários de uso)
  - backend/test_stress_scenarios.py (6 testes de stress)
  - backend/test_frontend_integration.py (testes UI com Playwright)
  - backend/run_all_persistence_tests.sh (script executor)
  
  🎯 CENÁRIOS A VALIDAR:
  
  1. **Cenário 1: Persistência após reinício do backend**
     ```bash
     # 1. Customizar campo "company" (marcar required=true)
     # 2. Reiniciar backend: ./restart-backend.sh
     # 3. Validar que required=true persiste
     ```
  
  2. **Cenário 2: Persistência após sincronização de cache**
     ```bash
     # 1. Customizar campo "vendor"
     # 2. Clicar em "Sincronizar Cache" na interface
     # 3. Validar que customizações mantêm
     ```
  
  3. **Cenário 3: Persistência nas 4 novas páginas**
     ```bash
     # 1. Customizar campo "site" 
     # 2. Marcar checkbox "Network Probes" na coluna "Páginas"
     # 3. Acessar /monitoring/network-probes
     # 4. Validar que campo aparece na tabela
     # 5. Reiniciar backend
     # 6. Validar que campo ainda aparece
     ```
  
  ⚡ EXECUÇÃO:
  ```bash
  cd /home/adrianofante/projetos/Skills-Eye/backend
  ./run_all_persistence_tests.sh
  
  # Este script executa sequencialmente:
  # 1. test_fields_merge.py          - Testes básicos (5 min)
  # 2. test_all_scenarios.py          - 8 cenários (10 min)
  # 3. test_stress_scenarios.py       - Stress tests (8 min)
  # 4. test_frontend_integration.py   - UI tests (12 min)
  
  # TOTAL: ~35 minutos
  ```
  
  ✅ CRITÉRIO DE SUCESSO:
  - ✓ TODOS os testes passam (100%)
  - ✓ Customizações persistem após reinício
  - ✓ Customizações persistem após sync cache
  - ✓ Campos aparecem nas 4 novas páginas
  - ✓ Merge não perde campos existentes
  
  ⚠️ SE ALGUM TESTE FALHAR:
  - Analisar logs em backend/tests/logs/
  - Verificar merge logic em metadata_fields_manager.py
  - Validar que KV está sendo usado (não apenas memória)
```

---

### ❌ FALTOU: Dia 11 - Migração de Categorização para Produção

**Status:** NÃO está no TODO do Claude Code  
**Prioridade:** 🟡 MÉDIA - Necessário para eliminar hardcode

**O QUE FAZER:**
```markdown
 FASE 5 - Deploy: Migração de Categorização Hardcoded → JSON KV (DIA 11)
  
  📝 DESCRIÇÃO:
  Após validar que CategorizationRuleEngine funciona com regras JSON,
  modificar monitoring_types_dynamic.py para usar o engine ao invés
  de lógica hardcoded.
  
  🎯 OBJETIVO:
  Eliminar código hardcoded em monitoring_types_dynamic.py e usar
  CategorizationRuleEngine que lê regras do Consul KV.
  
  📍 ARQUIVO A MODIFICAR:
  - backend/api/monitoring_types_dynamic.py (linhas 70-120)
  
  🔧 MODIFICAÇÃO NECESSÁRIA:
  
  **ANTES (hardcoded - linhas 85-120):**
  ```python
  # monitoring_types_dynamic.py
  
  EXPORTER_PATTERNS = {
      'haproxy': ('infrastructure-exporters', 'HAProxy Exporter', 'haproxy_exporter'),
      'nginx': ('infrastructure-exporters', 'Nginx Exporter', 'nginx_exporter'),
      'mysql': ('database-exporters', 'MySQL Exporter', 'mysqld_exporter'),
      # ... mais 37 padrões hardcoded
  }
  
  def _infer_category_and_type(job_name: str, job_config: Dict) -> tuple:
      job_lower = job_name.lower()
      
      # Lógica hardcoded (60+ linhas)
      if 'blackbox' in job_lower:
          # ...
      if 'mysql' in job_lower:
          return 'database-exporters', {...}
      # ... etc
  ```
  
  **DEPOIS (usando engine):**
  ```python
  # monitoring_types_dynamic.py
  
  from core.categorization_rule_engine import CategorizationRuleEngine
  from core.consul_kv_config_manager import ConsulKVConfigManager
  
  # Instanciar engine globalmente
  _config_manager = ConsulKVConfigManager()
  _categorization_engine = CategorizationRuleEngine(_config_manager)
  
  async def _ensure_rules_loaded():
      """Garante que regras foram carregadas do KV"""
      if not _categorization_engine.rules:
          await _categorization_engine.load_rules()
  
  def _infer_category_and_type(job_name: str, job_config: Dict) -> tuple:
      """
      NOVA IMPLEMENTAÇÃO: Usa CategorizationRuleEngine
      
      Migrado de lógica hardcoded para regras JSON no KV.
      """
      # Garantir que regras foram carregadas
      await _ensure_rules_loaded()
      
      # Preparar dados do job para o engine
      job_data = {
          'job_name': job_name,
          'metrics_path': job_config.get('metrics_path', '/metrics'),
          'labels': {}
      }
      
      # Extrair module se for blackbox
      if job_config.get('metrics_path') == '/probe':
          module = _extract_blackbox_module(job_config)
          job_data['labels']['module'] = module
      
      # Usar engine para categorizar
      result = _categorization_engine.categorize(job_data)
      
      # Converter resultado do engine para formato esperado
      category = result['category']
      type_info = {
          'id': job_name,
          'display_name': result['display_name'],
          'category': category,
          'job_name': job_name,
          'matched_rule_id': result['matched_rule_id']
      }
      
      return category, type_info
  ```
  
  ⚡ PASSOS DE MIGRAÇÃO:
  
  1. **Backup do código original**
     ```bash
     cp backend/api/monitoring_types_dynamic.py \
        backend/api/monitoring_types_dynamic.py.BACKUP_BEFORE_MIGRATION
     ```
  
  2. **Aplicar modificações** (usar código DEPOIS acima)
  
  3. **Testar que categorização produz mesmos resultados**
     ```bash
     # Testar endpoint
     curl "http://localhost:5000/api/v1/monitoring-types-dynamic/from-prometheus?server=ALL" | jq
     
     # Comparar com backup anterior
     # Categorias devem ser IDÊNTICAS
     ```
  
  4. **Validar nas 4 páginas novas**
     ```bash
     # Acessar cada página e validar que dados aparecem
     # - /monitoring/network-probes
     # - /monitoring/web-probes
     # - /monitoring/system-exporters
     # - /monitoring/database-exporters
     ```
  
  5. **Remover código hardcoded** (após validação completa)
     ```python
     # Remover EXPORTER_PATTERNS (linhas 85-120)
     # Remover lógica if/else hardcoded (linhas 200-260)
     # Manter apenas chamada ao engine
     ```
  
  ✅ CRITÉRIO DE SUCESSO:
  - ✓ Endpoint /monitoring-types-dynamic retorna mesmos dados
  - ✓ 4 novas páginas carregam corretamente
  - ✓ Categorização funciona igual ao hardcode
  - ✓ Código hardcoded foi removido
  - ✓ Testes passam (pytest)
  
  ⚠️ ROLLBACK SE NECESSÁRIO:
  ```bash
  # Se algo falhar, restaurar backup
  cp backend/api/monitoring_types_dynamic.py.BACKUP_BEFORE_MIGRATION \
     backend/api/monitoring_types_dynamic.py
  
  # Reiniciar backend
  ./restart-backend.sh
  ```
```

---

### ❌ FALTOU: Endpoint /monitoring/sync-cache

**Status:** NÃO está explícito no TODO do Claude Code  
**Prioridade:** 🟠 MÉDIA-ALTA - Necessário para botão "Sincronizar Cache"

**O QUE FAZER:**
```markdown
 FASE 2 - Backend: Criar endpoint POST /api/v1/monitoring/sync-cache
  
  📝 DESCRIÇÃO:
  Endpoint para forçar recarga do cache de tipos de monitoramento.
  Chamado pelo botão "Sincronizar Cache" no frontend.
  
  📍 LOCALIZAÇÃO:
  - Arquivo: backend/api/monitoring_unified.py
  - Rota: POST /api/v1/monitoring/sync-cache
  
  🎯 FUNCIONALIDADES:
  1. Limpar cache local do ConsulKVConfigManager
  2. Forçar extração nova do Prometheus
  3. Salvar novo cache no Consul KV
  4. Retornar status da sincronização
  
  🔧 CÓDIGO:
  ```python
  # backend/api/monitoring_unified.py
  
  @router.post("/sync-cache")
  async def sync_monitoring_cache(
      force: bool = Query(False, description="Forçar sync mesmo se cache válido")
  ):
      """
      Sincroniza cache de tipos de monitoramento
      
      Força backend a:
      1. Limpar cache local
      2. Re-extrair tipos do Prometheus
      3. Atualizar KV com dados frescos
      
      Args:
          force: Se True, ignora TTL e força sync
          
      Returns:
          {
              "success": true,
              "message": "Cache sincronizado com sucesso",
              "stats": {
                  "types_updated": 15,
                  "categories_updated": 8,
                  "cache_ttl": 300
              }
          }
      """
      try:
          from api.monitoring_types_dynamic import extract_monitoring_types_from_all_servers
          from core.consul_kv_config_manager import ConsulKVConfigManager
          
          config_manager = ConsulKVConfigManager()
          
          # STEP 1: Limpar cache local
          logger.info("[SYNC CACHE] Limpando cache local...")
          config_manager.clear_cache()
          
          # STEP 2: Extrair tipos novamente
          logger.info("[SYNC CACHE] Extraindo tipos do Prometheus...")
          result = await extract_monitoring_types_from_all_servers()
          
          if not result['success']:
              raise HTTPException(
                  status_code=500,
                  detail="Falha ao extrair tipos do Prometheus"
              )
          
          # STEP 3: Salvar no KV com TTL de 5 minutos
          logger.info("[SYNC CACHE] Salvando cache no KV...")
          
          for category in ['network-probes', 'web-probes', 
                          'system-exporters', 'database-exporters']:
              
              # Filtrar tipos da categoria
              category_types = [
                  t for t in result['all_types']
                  if t.get('category') == category
              ]
              
              # Salvar no KV
              cache_key = f"cache/{category}"
              await config_manager.set(cache_key, {
                  'types': category_types,
                  'total': len(category_types),
                  'last_sync': datetime.now().isoformat()
              }, ttl=300)  # 5 minutos
          
          # STEP 4: Retornar estatísticas
          return {
              "success": True,
              "message": "Cache sincronizado com sucesso!",
              "stats": {
                  "types_updated": result['total_types'],
                  "categories_updated": len(result['categories']),
                  "servers_scanned": len(result['servers']),
                  "cache_ttl": 300
              },
              "timestamp": datetime.now().isoformat()
          }
      
      except HTTPException:
          raise
      except Exception as e:
          logger.error(f"[SYNC CACHE ERROR] {e}", exc_info=True)
          raise HTTPException(
              status_code=500,
              detail=f"Erro ao sincronizar cache: {str(e)}"
          )
  ```
  
  ⚡ TESTE DO ENDPOINT:
  ```bash
  # Forçar sincronização
  curl -X POST "http://localhost:5000/api/v1/monitoring/sync-cache?force=true"
  
  # Resposta esperada:
  # {
  #   "success": true,
  #   "message": "Cache sincronizado com sucesso!",
  #   "stats": {
  #     "types_updated": 15,
  #     "categories_updated": 8,
  #     "servers_scanned": 2,
  #     "cache_ttl": 300
  #   }
  # }
  ```
  
  ✅ INTEGRAÇÃO FRONTEND:
  O DynamicMonitoringPage.tsx JÁ tem o handler:
  ```typescript
  const handleSyncCache = async () => {
    const result = await consulAPI.syncMonitoringCache();
    message.success(result.message);
    actionRef.current?.reload();
  };
  ```
```

---

### ❌ FALTOU: Atualizar MetadataFields.tsx

**Status:** PARCIALMENTE no TODO (só menciona metadata_fields_manager.py)  
**Prioridade:** 🟠 MÉDIA-ALTA - Necessário para UI gerenciar novos campos

**O QUE FAZER:**
```markdown
 FASE 3 - Frontend: Atualizar MetadataFields.tsx (adicionar 4 checkboxes)
  
  📝 DESCRIÇÃO:
  Modificar página frontend/src/pages/MetadataFields.tsx para incluir
  checkboxes das 4 novas páginas na coluna "Páginas".
  
  📍 LOCALIZAÇÃO:
  - Arquivo: frontend/src/pages/MetadataFields.tsx
  - Coluna: "Páginas" (render com checkboxes)
  
  🔧 MODIFICAÇÃO NECESSÁRIA:
  
  **ANTES (3 checkboxes):**
  ```typescript
  // frontend/src/pages/MetadataFields.tsx (linha ~180)
  
  const pagesColumn = {
    title: 'Páginas',
    dataIndex: 'pages',
    width: 200,
    render: (_, record) => {
      const pages = [
        { key: 'services', label: 'Services', value: record.show_in_services },
        { key: 'exporters', label: 'Exporters', value: record.show_in_exporters },
        { key: 'blackbox', label: 'Blackbox', value: record.show_in_blackbox },
      ];
      
      return (
        <Space direction="vertical" size={0}>
          {pages.filter(p => p.value).map(p => (
            <Tag key={p.key} color="blue">{p.label}</Tag>
          ))}
        </Space>
      );
    }
  };
  ```
  
  **DEPOIS (7 checkboxes - 3 antigas + 4 novas):**
  ```typescript
  // frontend/src/pages/MetadataFields.tsx (linha ~180)
  
  const pagesColumn = {
    title: 'Páginas',
    dataIndex: 'pages',
    width: 250,  // ⚠️ Aumentar largura para caber mais tags
    render: (_, record) => {
      const pages = [
        // ✅ 3 páginas antigas (manter)
        { key: 'services', label: 'Services', value: record.show_in_services },
        { key: 'exporters', label: 'Exporters', value: record.show_in_exporters },
        { key: 'blackbox', label: 'Blackbox', value: record.show_in_blackbox },
        
        // ⭐ 4 NOVAS páginas
        { key: 'network_probes', label: 'Network Probes', value: record.show_in_network_probes },
        { key: 'web_probes', label: 'Web Probes', value: record.show_in_web_probes },
        { key: 'system_exporters', label: 'System Exporters', value: record.show_in_system_exporters },
        { key: 'database_exporters', label: 'Database Exporters', value: record.show_in_database_exporters },
      ];
      
      return (
        <Space direction="vertical" size={0}>
          {pages.filter(p => p.value).map(p => (
            <Tag key={p.key} color="blue" style={{ marginBottom: 4 }}>
              {p.label}
            </Tag>
          ))}
        </Space>
      );
    }
  };
  ```
  
  🔧 TAMBÉM ATUALIZAR MODAL DE EDIÇÃO:
  ```typescript
  // Modal de edição de campo (linha ~350)
  
  <Form.Item label="Mostrar nas Páginas" name="pages">
    <Checkbox.Group>
      <Space direction="vertical">
        {/* 3 antigas */}
        <Checkbox value="services">Services</Checkbox>
        <Checkbox value="exporters">Exporters</Checkbox>
        <Checkbox value="blackbox">Blackbox Targets</Checkbox>
        
        {/* ⭐ 4 NOVAS */}
        <Divider style={{ margin: '8px 0' }} />
        <Checkbox value="network_probes">Network Probes</Checkbox>
        <Checkbox value="web_probes">Web Probes</Checkbox>
        <Checkbox value="system_exporters">System Exporters</Checkbox>
        <Checkbox value="database_exporters">Database Exporters</Checkbox>
      </Space>
    </Checkbox.Group>
  </Form.Item>
  ```
  
  ✅ VALIDAÇÃO:
  1. Acessar http://localhost:8081/metadata-fields
  2. Clicar em "Editar" em qualquer campo
  3. Verificar que modal tem 7 checkboxes (3 antigos + 4 novos)
  4. Marcar "Network Probes"
  5. Salvar
  6. Validar que tag "Network Probes" aparece na coluna "Páginas"
```

---

### ❌ FALTOU: Testes E2E das 4 Páginas

**Status:** NÃO está no TODO do Claude Code  
**Prioridade:** 🟡 MÉDIA - Necessário para validação final

**O QUE FAZER:**
```markdown
 FASE 4 - Testes: Criar testes E2E para 4 novas páginas (DIA 9)
  
  📝 DESCRIÇÃO:
  Criar testes end-to-end automatizados com Playwright para validar
  que as 4 novas páginas funcionam corretamente.
  
  📍 LOCALIZAÇÃO:
  - Arquivo: backend/test_dynamic_pages_e2e.py (CRIAR NOVO)
  
  🎯 CENÁRIOS DE TESTE:
  
  **Teste 1: Network Probes - Carregamento**
  ```python
  @pytest.mark.asyncio
  async def test_network_probes_loads(page):
      # Navegar para página
      await page.goto("http://localhost:8081/monitoring/network-probes")
      
      # Aguardar tabela carregar
      await page.wait_for_selector(".ant-table")
      
      # Validar título
      title = await page.text_content("h1")
      assert "Network Probes" in title
      
      # Validar que tem dados
      rows = await page.query_selector_all(".ant-table-row")
      assert len(rows) > 0
      
      # Validar colunas dinâmicas
      headers = await page.query_selector_all(".ant-table-thead th")
      assert len(headers) >= 5  # Mínimo de colunas esperadas
  ```
  
  **Teste 2: Sincronizar Cache**
  ```python
  @pytest.mark.asyncio
  async def test_sync_cache_button(page):
      await page.goto("http://localhost:8081/monitoring/network-probes")
      
      # Clicar no botão "Sincronizar Cache"
      await page.click('button:has-text("Sincronizar Cache")')
      
      # Aguardar loading
      await page.wait_for_selector('.ant-spin', state='hidden', timeout=10000)
      
      # Validar mensagem de sucesso
      success_msg = await page.text_content('.ant-message-success')
      assert "sincronizado" in success_msg.lower()
  ```
  
  **Teste 3: Filtros Dinâmicos**
  ```python
  @pytest.mark.asyncio
  async def test_dynamic_filters(page):
      await page.goto("http://localhost:8081/monitoring/web-probes")
      
      # Abrir painel de filtros
      await page.click('button:has-text("Filtros")')
      
      # Validar que campos metadata aparecem
      company_filter = await page.query_selector('[placeholder="Empresa"]')
      assert company_filter is not None
      
      # Aplicar filtro
      await company_filter.fill("Ramada")
      await page.click('button:has-text("Buscar")')
      
      # Aguardar filtro aplicar
      await page.wait_for_timeout(1000)
      
      # Validar que resultados foram filtrados
      rows = await page.query_selector_all(".ant-table-row")
      assert len(rows) > 0
  ```
  
  **Teste 4: Navegação Entre Páginas**
  ```python
  @pytest.mark.asyncio
  async def test_navigation_between_pages(page):
      # Começar em Network Probes
      await page.goto("http://localhost:8081/monitoring/network-probes")
      assert "Network Probes" in await page.text_content("h1")
      
      # Navegar para Web Probes via menu
      await page.click('text="Web Probes"')
      await page.wait_for_url("**/monitoring/web-probes")
      assert "Web Probes" in await page.text_content("h1")
      
      # Navegar para System Exporters
      await page.click('text="System Exporters"')
      await page.wait_for_url("**/monitoring/system-exporters")
      assert "System Exporters" in await page.text_content("h1")
      
      # Navegar para Database Exporters
      await page.click('text="Database Exporters"')
      await page.wait_for_url("**/monitoring/database-exporters")
      assert "Database Exporters" in await page.text_content("h1")
  ```
  
  ⚡ EXECUÇÃO:
  ```bash
  cd /home/adrianofante/projetos/Skills-Eye/backend
  
  # Instalar Playwright se necessário
  pip install playwright pytest-playwright
  playwright install
  
  # Executar testes
  pytest test_dynamic_pages_e2e.py -v --headed
  
  # Resultado esperado: 4/4 testes PASSANDO
  ```
```

---

## 📊 RESUMO DE ITENS FALTANTES

| # | Item Faltando | Prioridade | Fase | Dia |
|---|---------------|------------|------|-----|
| 1 | Script migrate_categorization_to_json.py | 🔴 ALTA | 2 | 3 |
| 2 | Endpoint POST /monitoring/sync-cache | 🟠 MÉDIA-ALTA | 2 | 5 |
| 3 | Atualizar MetadataFields.tsx (4 checkboxes) | 🟠 MÉDIA-ALTA | 3 | 8 |
| 4 | Testes de Persistência (Dia 9.5) | 🟡 MÉDIA | 4 | 9.5 |
| 5 | Testes E2E das 4 páginas | 🟡 MÉDIA | 4 | 9 |
| 6 | Migração Produção (Dia 11) | 🟡 MÉDIA | 5 | 11 |

---

## ✅ PRÓXIMOS PASSOS

1. **Enviar este TODO ao Claude Code Web**
2. **Instruir para implementar itens na ordem de prioridade**
3. **Eu (VSCode) executarei:**
   - Testes (pytest, Playwright)
   - Scripts de migração
   - Validações de endpoints (curl)
   - Commits Git

---

**DOCUMENTO CRIADO EM:** 13/11/2025 14:30  
**AUTOR:** AI Assistant (VSCode) + Análise de Gaps  
**STATUS:** 📋 PRONTO PARA ENVIO AO CLAUDE CODE WEB
