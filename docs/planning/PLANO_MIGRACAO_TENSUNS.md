# 📋 PLANO DETALHADO DE MIGRAÇÃO PARA ARQUITETURA TENSUNS

**Data**: 2025-01-09
**Objetivo**: Alinhar SkillsEye à arquitetura TenSunS eliminando dual storage, mantendo melhorias exclusivas
**Duração Estimada**: 5-7 dias
**Criticidade**: Alta (afeta armazenamento e performance)

---

## 📊 SUMÁRIO EXECUTIVO

### Problema Identificado
Criamos dual storage (Services API + KV) para blackbox targets **sem necessidade**. TenSunS original usa **APENAS** Services API com metadados.

### Solução
Migrar para arquitetura TenSunS pura:
- **Targets de monitoramento**: APENAS Consul Services API (Meta contém todos os dados)
- **KV Store**: APENAS para dados não relacionados a targets (settings, presets, audit, etc.)

### Impacto
- ✅ Redução de ~50% em operações de I/O
- ✅ Eliminação de sincronização manual
- ✅ Alinhamento com padrões do TenSunS
- ✅ Código mais simples e maintainável
- ⚠️ Requer refatoração de frontend e backend

---

## 🔍 FASE 1: ANÁLISE PROFUNDA E MAPEAMENTO (2 dias)

### 1.1. Análise Completa do TenSunS

#### Tarefa 1.1.1: Documentar Arquitetura de Storage TenSunS

**Arquivo**: `TenSunS/flask-consul/units/blackbox_manager.py`

**Evidências já coletadas**:
```python
# LINHA 50-66: add_service() cria DIRETO no Services API
def add_service(module,company,project,env,name,instance):
    sid = f"{module}/{company}/{project}/{env}@{name}".strip()
    data = {
        "id": sid,
        "name": 'blackbox_exporter',
        "tags": [module],
        "Meta": {'module':module,'company':company,'project':project,
                 'env':env,'name':name,'instance':instance}  # ← TUDO NO META
    }
    reg = requests.put(f'{consul_url}/agent/service/register', headers=headers, data=json.dumps(data))

# LINHA 31-48: get_service() lê DIRETO do Services API
def get_service():
    response = requests.get(f'{consul_url}/agent/services?filter=Service == blackbox_exporter', headers=headers)
    all_list = [i['Meta'] for i in info.values()]  # ← LÊ DO META

    # ÚNICO uso de KV: cache de lista de módulos
    consul_kv.put_kv('ConsulManager/record/blackbox/module_list',{'module_list':module_list})
```

**O que TenSunS USA KV** (baseado em `TenSunS/flask-consul/units/consul_kv.py`):
```
ConsulManager/
├── assets/
│   ├── secret/skey              # Secret key da aplicação
│   ├── {cloud}/aksk/{account}   # Credenciais cloud (AK/SK criptografadas)
│   ├── {cloud}/group/{account}  # Grupos de recursos cloud
│   ├── sync_ecs_custom/{id}     # Customizações de ECS
│   └── sync_redis_custom/{id}   # Customizações de Redis
├── record/
│   ├── jobs/{job_id}            # Logs de execução de jobs
│   ├── jms/{vendor}/{account}   # Status de sync JumpServer
│   └── blackbox/module_list     # ❗ ÚNICO uso para blackbox (CACHE)
└── jobs/                        # Configuração de jobs agendados
```

**AÇÃO**: Criar documento comparativo

**Script a criar**: `docs/TENSUNS_ARCHITECTURE_ANALYSIS.md`

```markdown
# Análise Arquitetural TenSunS vs SkillsEye

## Blackbox Targets

| Aspecto | TenSunS | SkillsEye Atual | SkillsEye Alvo |
|---------|---------|-----------------|----------------|
| Storage primário | Services API Meta | Services API Meta | Services API Meta ✅ |
| Storage secundário | NENHUM | ❌ KV `blackbox/targets/` | NENHUM ✅ |
| Cache | KV `module_list` apenas | KV targets completos | KV `module_list` apenas |
| Sincronização | NÃO PRECISA | Manual (risco divergência) | NÃO PRECISA ✅ |

## Campos Metadados (Fields)

TenSunS: Hardcoded em `blackbox_manager.py`
```python
Meta: {'module':module,'company':company,'project':project,
       'env':env,'name':name,'instance':instance}
```

SkillsEye: **MELHORIA** - Dinâmico via `skills/eye/metadata/fields` no KV
- ✅ Permite adicionar/editar campos sem code deploy
- ✅ Sync com prometheus.yml via UI
- ✅ MANTER esta arquitetura (melhoria sobre TenSunS)
```
---

#### Tarefa 1.1.2: Mapear TODOS os usos de KV em SkillsEye

**Script a criar**: `backend/analyze_kv_usage.py`

```python
"""
Analisa TODOS os locais onde usamos Consul KV no projeto.
Identifica:
1. Namespaces em uso
2. Operações (read, write, delete)
3. Se há duplicação com Services API
"""
import asyncio
from core.consul_manager import ConsulManager
from core.kv_manager import KVManager
import json
from collections import defaultdict

async def analyze_kv_usage():
    print("=" * 80)
    print("ANÁLISE COMPLETA DE USO DO CONSUL KV")
    print("=" * 80)
    print()

    kv = KVManager()

    # 1. Listar TODAS as keys do KV
    print("[1/5] Listando todas as keys do KV...")
    all_keys = await kv.get_keys('skills/eye')
    total = len(all_keys)
    print(f"[OK] Total de keys: {total}")
    print()

    # 2. Agrupar por namespace
    print("[2/5] Agrupando por namespace...")
    by_namespace = defaultdict(list)
    for key in all_keys:
        parts = key.replace('skills/eye/', '').split('/')
        namespace = parts[0] if parts else 'root'
        by_namespace[namespace].append(key)

    print("DISTRIBUIÇÃO POR NAMESPACE:")
    for ns, keys in sorted(by_namespace.items(), key=lambda x: -len(x[1])):
        print(f"  {ns:30s} {len(keys):6d} keys")
    print()

    # 3. Verificar quais namespaces têm DUAL STORAGE
    print("[3/5] Verificando dual storage (KV + Services)...")

    cm = ConsulManager()

    # Listar todos os services
    services_overview = await cm.get_services_overview()
    total_services = services_overview.get('total', 0)
    print(f"  Total de Services registrados: {total_services}")

    # Verificar blackbox targets
    blackbox_targets_kv = len(by_namespace.get('blackbox', []))
    blackbox_services = 0

    # Contar services blackbox_exporter
    response = await cm.http_client.get(
        f'{cm.consul_url}/agent/services?filter=Service contains "blackbox"',
        headers=cm.headers
    )
    if response.status_code == 200:
        blackbox_services = len(response.json())

    print()
    print("  BLACKBOX TARGETS:")
    print(f"    KV (skills/eye/blackbox/targets): {blackbox_targets_kv} targets")
    print(f"    Services API (blackbox_exporter): {blackbox_services} services")

    if blackbox_targets_kv > 0 and blackbox_services > 0:
        print("    ❌ DUAL STORAGE DETECTADO!")
        print(f"    Redundância estimada: {min(blackbox_targets_kv, blackbox_services)} targets duplicados")
    print()

    # 4. Listar namespaces que NÃO devem ter dual storage
    print("[4/5] Namespaces corretos (sem dual storage):")
    safe_namespaces = ['metadata', 'settings', 'audit', 'services', 'reference_values']
    for ns in safe_namespaces:
        count = len(by_namespace.get(ns, []))
        if count > 0:
            print(f"  ✅ {ns:20s} {count:6d} keys (correto - KV only)")
    print()

    # 5. Recomendações
    print("[5/5] RECOMENDAÇÕES:")
    print()

    if blackbox_targets_kv > 0:
        print("  🔴 CRÍTICO: Eliminar skills/eye/blackbox/targets/")
        print(f"     - {blackbox_targets_kv} targets armazenados desnecessariamente no KV")
        print("     - Migrar lógica para ler 100% do Services API")
        print("     - Economia estimada: ~50% de operações I/O")

    print()
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(analyze_kv_usage())
```

**Executar**: `python analyze_kv_usage.py > docs/KV_USAGE_ANALYSIS.txt`

---

#### Tarefa 1.1.3: Inventariar código que usa blackbox/targets KV

**Script a criar**: `backend/find_dual_storage_code.py`

```python
"""
Busca TODOS os arquivos que acessam skills/eye/blackbox/targets
Para planejar refatoração
"""
import os
import re
from pathlib import Path

def find_kv_targets_usage():
    print("=" * 80)
    print("BUSCA DE CÓDIGO USANDO skills/eye/blackbox/targets")
    print("=" * 80)
    print()

    backend_dir = Path(__file__).parent
    patterns = [
        r'blackbox/targets',
        r'BLACKBOX_TARGETS',
        r'get_blackbox_target',
        r'create_blackbox_target',
        r'update_blackbox_target',
        r'delete_blackbox_target',
    ]

    findings = []

    for py_file in backend_dir.rglob('*.py'):
        if '__pycache__' in str(py_file) or 'venv' in str(py_file):
            continue

        with open(py_file, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            lines = content.splitlines()

        for pattern in patterns:
            for i, line in enumerate(lines, 1):
                if re.search(pattern, line, re.IGNORECASE):
                    findings.append({
                        'file': str(py_file.relative_to(backend_dir)),
                        'line': i,
                        'code': line.strip(),
                        'pattern': pattern
                    })

    # Agrupar por arquivo
    by_file = {}
    for f in findings:
        file_path = f['file']
        if file_path not in by_file:
            by_file[file_path] = []
        by_file[file_path].append(f)

    print(f"Total de arquivos afetados: {len(by_file)}")
    print()

    for file_path, matches in sorted(by_file.items()):
        print(f"📄 {file_path} ({len(matches)} ocorrências)")
        for match in matches:
            print(f"   Linha {match['line']}: {match['code'][:80]}")
        print()

    # Salvar em JSON para processamento posterior
    import json
    output = {
        'total_files': len(by_file),
        'total_occurrences': len(findings),
        'files': by_file
    }

    with open(backend_dir / 'docs' / 'dual_storage_code_locations.json', 'w') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print("=" * 80)
    print(f"Relatório salvo em: docs/dual_storage_code_locations.json")
    print("=" * 80)

if __name__ == "__main__":
    find_dual_storage_code()
```

**Executar**: `python find_dual_storage_code.py`

---

### 1.2. Criar Matriz de Decisão

**Documento a criar**: `docs/MIGRATION_DECISION_MATRIX.md`

```markdown
# Matriz de Decisão - Migração TenSunS

## Storage de Targets de Monitoramento

### Blackbox Exporter Targets

| Dado | TenSunS | SkillsEye Atual | Decisão Final | Justificativa |
|------|---------|-----------------|---------------|---------------|
| **URL do target** | Service.Meta.instance | KV + Service.Meta.instance | **Service.Meta.instance** | Eliminar duplicação |
| **Módulo (http_2xx, icmp, etc.)** | Service.Tags + Service.Meta.module | KV + Service.Tags | **Service.Tags + Service.Meta.module** | Manter padrão TenSunS |
| **Company** | Service.Meta.company | KV + Service.Meta.company | **Service.Meta.company** | Eliminar duplicação |
| **Project** | Service.Meta.project | KV + Service.Meta.project | **Service.Meta.project** | Eliminar duplicação |
| **Env** | Service.Meta.env | KV + Service.Meta.env | **Service.Meta.env** | Eliminar duplicação |
| **Name** | Service.Meta.name | KV + Service.Meta.name | **Service.Meta.name** | Eliminar duplicação |
| **Campos extras** | ❌ Não tem | ✅ KV metadata dinâmicos | **Service.Meta.{field}** | Usar Meta fields dinâmicos |
| **Grouping** | ❌ Não tem | ✅ KV blackbox/groups | **MANTER KV blackbox/groups** | Feature adicional válida |
| **Import/Export** | CSV → Services API | CSV → KV → Services | **CSV → Services API** | Alinhar com TenSunS |

**DECISÃO**: Eliminar completamente `skills/eye/blackbox/targets/*` do KV

---

### Node Exporter (selfnode)

| Dado | TenSunS | SkillsEye Atual | Decisão Final |
|------|---------|-----------------|---------------|
| Storage | Services API | **VERIFICAR** | Services API (alinhar com TenSunS) |

**AÇÃO**: Investigar se temos dual storage para selfnode também

---

### MySQL/Redis Exporters

| Dado | TenSunS | SkillsEye Atual | Decisão Final |
|------|---------|-----------------|---------------|
| Storage | Services API | **VERIFICAR** | Services API (alinhar com TenSunS) |

**AÇÃO**: Investigar storage atual

---

## Features que MANTEMOS (melhorias sobre TenSunS)

| Feature | Onde Armazena | Justificativa |
|---------|---------------|---------------|
| **Metadata Fields Dinâmicos** | `skills/eye/metadata/fields` (KV) | ✅ Permite configurar campos via UI sem code deploy |
| **Prometheus Config SSH Editor** | Sem storage (edição direta remota) | ✅ Feature nova, não existe no TenSunS |
| **Service Presets** | `skills/eye/services/presets` (KV) | ✅ Templates reutilizáveis, melhoria sobre TenSunS |
| **Reference Values Autocomplete** | `skills/eye/reference_values` (KV) | ✅ UX melhorada, cache de valores |
| **Blackbox Groups** | `skills/eye/blackbox/groups` (KV) | ✅ Organização lógica, feature adicional |
| **Audit Logging** | `skills/eye/audit` (KV) | ✅ Rastreabilidade, já otimizado |
| **Settings/Credentials** | `skills/eye/settings` (KV) | ✅ Configurações centralizadas |
```

---

### 1.3. Estimar Impacto em Código

**Checklist de arquivos a refatorar**:

#### Backend
- [ ] `backend/core/blackbox_manager.py` - Remover lógica KV, usar apenas Services API
- [ ] `backend/api/blackbox.py` - Ajustar endpoints para não usar KV targets
- [ ] `backend/core/kv_manager.py` - Remover constante `BLACKBOX_TARGETS`
- [ ] `backend/api/search.py` - Buscar em Services API ao invés de KV (se aplicável)
- [ ] **VERIFICAR**: `selfnode_manager.py`, `selfrds_manager.py`, `selfredis_manager.py`

#### Frontend
- [ ] `frontend/src/pages/BlackboxTargets.tsx` - Buscar de Services API
- [ ] `frontend/src/services/api.ts` - Ajustar endpoints
- [ ] **VERIFICAR**: Páginas de self-exporters

**Total estimado**: 8-12 arquivos a refatorar

---

## 🔧 FASE 2: PREPARAÇÃO E BACKUP (1 dia)

### 2.1. Backup Completo do Estado Atual

**Script a criar**: `backend/backup_before_migration.py`

```python
"""
Cria backup COMPLETO antes da migração:
1. Export de TODOS os Services
2. Export de TODO o KV skills/eye/
3. Timestamp para rollback se necessário
"""
import asyncio
from datetime import datetime
from pathlib import Path
import json
from core.consul_manager import ConsulManager
from core.kv_manager import KVManager

async def backup_all():
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = Path(__file__).parent / 'backups' / f'pre_migration_{timestamp}'
    backup_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 80)
    print("BACKUP COMPLETO PRÉ-MIGRAÇÃO")
    print("=" * 80)
    print(f"Destino: {backup_dir}")
    print()

    cm = ConsulManager()
    kv = KVManager()

    # 1. Backup de TODOS os Services
    print("[1/3] Exportando Services...")
    response = await cm.http_client.get(f'{cm.consul_url}/agent/services', headers=cm.headers)
    services = response.json()

    with open(backup_dir / 'all_services.json', 'w', encoding='utf-8') as f:
        json.dump(services, f, indent=2, ensure_ascii=False)

    print(f"  ✓ {len(services)} services salvos")

    # 2. Backup de TODO o KV skills/eye/
    print("[2/3] Exportando KV skills/eye/...")
    kv_tree = await cm.get_kv_tree('skills/eye')

    with open(backup_dir / 'kv_full_tree.json', 'w', encoding='utf-8') as f:
        json.dump(kv_tree, f, indent=2, ensure_ascii=False)

    print(f"  ✓ {len(kv_tree)} keys salvas")

    # 3. Backup específico de blackbox/targets (para comparação)
    print("[3/3] Exportando blackbox/targets específico...")
    targets_kv = {k: v for k, v in kv_tree.items() if 'blackbox/targets' in k}

    with open(backup_dir / 'blackbox_targets_kv_only.json', 'w', encoding='utf-8') as f:
        json.dump(targets_kv, f, indent=2, ensure_ascii=False)

    print(f"  ✓ {len(targets_kv)} targets KV salvos")

    # 4. Manifest do backup
    manifest = {
        'timestamp': timestamp,
        'total_services': len(services),
        'total_kv_keys': len(kv_tree),
        'blackbox_targets_kv': len(targets_kv),
        'consul_version': '1.14.0',  # Atualizar se necessário
        'backup_files': [
            'all_services.json',
            'kv_full_tree.json',
            'blackbox_targets_kv_only.json'
        ]
    }

    with open(backup_dir / 'MANIFEST.json', 'w') as f:
        json.dump(manifest, f, indent=2)

    print()
    print("=" * 80)
    print("✅ BACKUP CONCLUÍDO")
    print(f"   Localização: {backup_dir}")
    print("=" * 80)
    print()
    print("PRÓXIMOS PASSOS:")
    print("1. Validar backups: ls backups/pre_migration_*/")
    print("2. Testar restore: python restore_backup.py <timestamp>")
    print("3. Prosseguir com migração apenas após validação")

if __name__ == "__main__":
    asyncio.run(backup_all())
```

### 2.2. Script de Restore (caso precise reverter)

**Script a criar**: `backend/restore_backup.py`

```python
"""
Restaura backup caso migração falhe.
USO: python restore_backup.py 20250109_143022
"""
import asyncio
import sys
import json
from pathlib import Path
from core.consul_manager import ConsulManager

async def restore_backup(timestamp):
    backup_dir = Path(__file__).parent / 'backups' / f'pre_migration_{timestamp}'

    if not backup_dir.exists():
        print(f"❌ Backup não encontrado: {backup_dir}")
        return

    print("=" * 80)
    print("RESTORE DE BACKUP")
    print("=" * 80)
    print(f"Fonte: {backup_dir}")
    print()

    # Ler manifest
    with open(backup_dir / 'MANIFEST.json') as f:
        manifest = json.load(f)

    print(f"Backup timestamp: {manifest['timestamp']}")
    print(f"Services: {manifest['total_services']}")
    print(f"KV keys: {manifest['total_kv_keys']}")
    print()

    confirm = input("⚠️  ATENÇÃO: Isso irá SOBRESCREVER dados atuais. Confirmar? (s/N): ")
    if confirm.lower() != 's':
        print("Cancelado.")
        return

    cm = ConsulManager()

    # 1. Restaurar Services
    print("[1/2] Restaurando Services...")
    with open(backup_dir / 'all_services.json') as f:
        services = json.load(f)

    for service_id, service_data in services.items():
        try:
            await cm.register_service(
                service_id=service_data['ID'],
                name=service_data['Service'],
                address=service_data.get('Address'),
                port=service_data.get('Port'),
                tags=service_data.get('Tags', []),
                meta=service_data.get('Meta', {}),
                check=service_data.get('Check')
            )
            print(f"  ✓ {service_id}")
        except Exception as e:
            print(f"  ✗ {service_id}: {e}")

    # 2. Restaurar KV
    print("[2/2] Restaurando KV...")
    with open(backup_dir / 'kv_full_tree.json') as f:
        kv_tree = json.load(f)

    for key, value in kv_tree.items():
        try:
            await cm.put_kv(key, value)
            if len(kv_tree) < 100 or list(kv_tree.keys()).index(key) % 50 == 0:
                print(f"  ✓ {key}")
        except Exception as e:
            print(f"  ✗ {key}: {e}")

    print()
    print("=" * 80)
    print("✅ RESTORE CONCLUÍDO")
    print("=" * 80)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("USO: python restore_backup.py <timestamp>")
        print("Exemplo: python restore_backup.py 20250109_143022")
        sys.exit(1)

    asyncio.run(restore_backup(sys.argv[1]))
```

---

### 2.3. Validar que Metadata Fields JÁ está no KV

**Checkpoint**: Confirmar que `skills/eye/metadata/fields` está populado

```python
# Script de validação: backend/validate_metadata_in_kv.py
import asyncio
from core.kv_manager import KVManager

async def validate():
    kv = KVManager()
    fields_data = await kv.get_json('skills/eye/metadata/fields')

    if not fields_data:
        print("❌ ERRO: metadata/fields NÃO está no KV!")
        print("   AÇÃO: Rodar extração manual primeiro")
        return False

    fields = fields_data.get('fields', [])
    print(f"✅ metadata/fields ESTÁ no KV ({len(fields)} campos)")
    return True

if __name__ == "__main__":
    asyncio.run(validate())
```

---

## 🚧 FASE 3: MIGRAÇÃO DE DADOS (1 dia)

### 3.1. Criar Script de Migração de Blackbox Targets

**Objetivo**: Garantir que TODOS os targets do KV estão no Services API antes de deletar KV

**Script a criar**: `backend/migrate_blackbox_targets_to_services.py`

```python
"""
Migra blackbox targets do KV para Services API (se não existirem)

ESTRATÉGIA:
1. Ler TODOS os targets de skills/eye/blackbox/targets
2. Para cada target, verificar se JÁ existe no Services API
3. Se NÃO existir, criar no Services API
4. Se existir, comparar dados e avisar se houver divergência
5. NÃO deletar nada do KV (apenas FASE 4)
"""
import asyncio
from core.consul_manager import ConsulManager
from core.kv_manager import KVManager
import json

async def migrate_targets():
    print("=" * 80)
    print("MIGRAÇÃO BLACKBOX TARGETS: KV → Services API")
    print("=" * 80)
    print()

    cm = ConsulManager()
    kv = KVManager()

    # 1. Buscar targets do KV
    print("[1/5] Carregando targets do KV...")
    kv_tree = await cm.get_kv_tree('skills/eye/blackbox/targets')
    targets_kv = {k: v for k, v in kv_tree.items() if isinstance(v, dict)}

    print(f"  ✓ {len(targets_kv)} targets encontrados no KV")
    print()

    # 2. Buscar services blackbox_exporter existentes
    print("[2/5] Carregando services existentes...")
    response = await cm.http_client.get(
        f'{cm.consul_url}/agent/services?filter=Service == "blackbox_exporter"',
        headers=cm.headers
    )

    services_existing = {}
    if response.status_code == 200:
        services_data = response.json()
        services_existing = {s['ID']: s for s in services_data.values()}

    print(f"  ✓ {len(services_existing)} services blackbox_exporter existentes")
    print()

    # 3. Comparar e identificar ações necessárias
    print("[3/5] Comparando KV vs Services API...")

    to_create = []   # Targets que NÃO existem no Services
    to_update = []   # Targets com divergência
    already_ok = []  # Targets já corretos

    for kv_key, kv_data in targets_kv.items():
        # Extrair dados do KV
        target_data = kv_data.get('data', {})
        target_meta = kv_data.get('meta', {})

        # Construir service_id esperado (padrão TenSunS)
        module = target_data.get('module', 'http_2xx')
        company = target_data.get('company', '_')
        project = target_data.get('project', '_')
        env = target_data.get('env', '_')
        name = target_data.get('name', '_')
        instance = target_data.get('instance', '')

        # Sanitizar service_id
        service_id = f"{module}/{company}/{project}/{env}@{name}"
        service_id = cm.sanitize_service_id(service_id)

        # Verificar se existe no Services API
        if service_id in services_existing:
            # Comparar dados
            existing_service = services_existing[service_id]
            existing_meta = existing_service.get('Meta', {})

            # Verificar divergências
            divergences = []
            if existing_meta.get('instance') != instance:
                divergences.append(f"instance: '{existing_meta.get('instance')}' != '{instance}'")
            if existing_meta.get('module') != module:
                divergences.append(f"module: '{existing_meta.get('module')}' != '{module}'")

            if divergences:
                to_update.append({
                    'service_id': service_id,
                    'kv_data': target_data,
                    'service_data': existing_meta,
                    'divergences': divergences
                })
            else:
                already_ok.append(service_id)
        else:
            to_create.append({
                'service_id': service_id,
                'module': module,
                'company': company,
                'project': project,
                'env': env,
                'name': name,
                'instance': instance,
                'kv_data': target_data
            })

    print(f"  ✓ Análise concluída:")
    print(f"    - Criar no Services: {len(to_create)}")
    print(f"    - Atualizar (divergência): {len(to_update)}")
    print(f"    - Já corretos: {len(already_ok)}")
    print()

    # 4. Criar targets que não existem
    if to_create:
        print(f"[4/5] Criando {len(to_create)} novos services...")

        created_count = 0
        failed_count = 0

        for target in to_create:
            try:
                # Registrar service (padrão TenSunS)
                success, msg = await cm.register_service(
                    service_id=target['service_id'],
                    name='blackbox_exporter',
                    tags=[target['module']],
                    meta={
                        'module': target['module'],
                        'company': target['company'],
                        'project': target['project'],
                        'env': target['env'],
                        'name': target['name'],
                        'instance': target['instance']
                    }
                )

                if success:
                    created_count += 1
                    if created_count % 10 == 0:
                        print(f"  Progresso: {created_count}/{len(to_create)}")
                else:
                    failed_count += 1
                    print(f"  ✗ Erro ao criar {target['service_id']}: {msg}")

            except Exception as e:
                failed_count += 1
                print(f"  ✗ Exceção ao criar {target['service_id']}: {e}")

        print(f"  ✓ Criados: {created_count}")
        if failed_count > 0:
            print(f"  ✗ Falhas: {failed_count}")
    else:
        print("[4/5] Nenhum service novo a criar (todos já existem)")

    print()

    # 5. Relatar divergências (NÃO atualizar automaticamente)
    if to_update:
        print(f"[5/5] ⚠️  {len(to_update)} divergências detectadas:")
        print()
        for div in to_update[:5]:  # Mostrar apenas 5 primeiros
            print(f"  Service: {div['service_id']}")
            for d in div['divergences']:
                print(f"    - {d}")

        if len(to_update) > 5:
            print(f"  ... e mais {len(to_update) - 5} divergências")

        print()
        print("  AÇÃO MANUAL NECESSÁRIA:")
        print("  1. Revisar divergências manualmente")
        print("  2. Decidir qual fonte é correta (KV ou Services)")
        print("  3. Corrigir manualmente se necessário")
    else:
        print("[5/5] Nenhuma divergência detectada")

    print()
    print("=" * 80)
    print("RESUMO DA MIGRAÇÃO")
    print("=" * 80)
    print(f"Total de targets no KV: {len(targets_kv)}")
    print(f"Já existentes no Services: {len(already_ok)}")
    print(f"Criados no Services: {created_count if to_create else 0}")
    print(f"Com divergências: {len(to_update)}")
    print("=" * 80)
    print()

    if to_update:
        print("⚠️  ATENÇÃO: Divergências detectadas!")
        print("   NÃO prossiga para FASE 4 sem resolver divergências")
    elif failed_count > 0:
        print("⚠️  ATENÇÃO: Algumas criações falharam!")
        print("   Revise os erros antes de prosseguir")
    else:
        print("✅ MIGRAÇÃO CONCLUÍDA COM SUCESSO")
        print("   Pode prosseguir para FASE 4 (refatoração de código)")

if __name__ == "__main__":
    asyncio.run(migrate_targets())
```

**Executar**: `python migrate_blackbox_targets_to_services.py`

---

## 👨‍💻 FASE 4: REFATORAÇÃO DE CÓDIGO (2-3 dias)

### 4.1. Backend - Blackbox Manager

**Arquivo**: `backend/core/blackbox_manager.py`

**Mudanças necessárias**:

```python
# ANTES (dual storage):
class BlackboxManager:
    async def create_target(self, target_data: Dict) -> Tuple[bool, str]:
        # 1. Criar no Services API
        service_id = self._build_service_id(target_data)
        await self.consul.register_service(...)

        # 2. Criar no KV ← REMOVER ISSO
        await self.kv.put_blackbox_target(service_id, target_data)  # ❌ DELETAR

    async def get_target(self, target_id: str) -> Optional[Dict]:
        # Ler do KV ← MUDAR
        return await self.kv.get_blackbox_target(target_id)  # ❌ DELETAR

    async def list_targets(self, filters: Dict) -> List[Dict]:
        # Ler do KV ← MUDAR
        return await self.kv.list_blackbox_targets(filters)  # ❌ DELETAR

# DEPOIS (Services API only - padrão TenSunS):
class BlackboxManager:
    async def create_target(self, target_data: Dict) -> Tuple[bool, str]:
        # APENAS Services API (padrão TenSunS)
        service_id = self._build_service_id(target_data)
        return await self.consul.register_service(
            service_id=service_id,
            name='blackbox_exporter',
            tags=[target_data['module']],
            meta={
                'module': target_data['module'],
                'company': target_data['company'],
                'project': target_data['project'],
                'env': target_data['env'],
                'name': target_data['name'],
                'instance': target_data['instance'],
                # Campos extras dinâmicos (melhoria sobre TenSunS)
                **{k: v for k, v in target_data.items()
                   if k not in ['module', 'company', 'project', 'env', 'name', 'instance']}
            }
        )

    async def get_target(self, target_id: str) -> Optional[Dict]:
        # Ler do Services API
        response = await self.consul.http_client.get(
            f'{self.consul.consul_url}/agent/service/{target_id}',
            headers=self.consul.headers
        )

        if response.status_code == 200:
            service = response.json()
            return service.get('Meta', {})
        return None

    async def list_targets(self, filters: Dict) -> List[Dict]:
        # Ler do Services API com filtros
        filter_expr = self._build_consul_filter(filters)
        response = await self.consul.http_client.get(
            f'{self.consul.consul_url}/agent/services?filter={filter_expr}',
            headers=self.consul.headers
        )

        if response.status_code == 200:
            services = response.json()
            # Retornar Meta de cada service
            return [s['Meta'] for s in services.values()]
        return []

    def _build_consul_filter(self, filters: Dict) -> str:
        """
        Converte filtros dict para Consul filter expression

        Exemplo:
            {'module': 'http_2xx', 'company': 'ACME'}
            → 'Service == "blackbox_exporter" and Meta.module == "http_2xx" and Meta.company == "ACME"'
        """
        expressions = ['Service == "blackbox_exporter"']

        for key, value in filters.items():
            if value:  # Ignorar valores vazios
                expressions.append(f'Meta.{key} == "{value}"')

        return ' and '.join(expressions)
```

**Tarefas**:
- [ ] Remover todas as chamadas a `kv.put_blackbox_target()`
- [ ] Remover todas as chamadas a `kv.get_blackbox_target()`
- [ ] Implementar `_build_consul_filter()` para queries
- [ ] Adicionar testes unitários para nova lógica

---

### 4.2. Backend - KV Manager

**Arquivo**: `backend/core/kv_manager.py`

**Mudanças**:

```python
# ANTES:
class KVManager:
    PREFIX = "skills/eye"
    BLACKBOX_TARGETS = f"{PREFIX}/blackbox/targets"  # ❌ REMOVER
    BLACKBOX_GROUPS = f"{PREFIX}/blackbox/groups"    # ✅ MANTER
    BLACKBOX_MODULES = f"{PREFIX}/blackbox/modules.json"  # ✅ MANTER

    async def put_blackbox_target(self, target_id: str, data: Dict):  # ❌ REMOVER
        ...

    async def get_blackbox_target(self, target_id: str):  # ❌ REMOVER
        ...

# DEPOIS:
class KVManager:
    PREFIX = "skills/eye"
    # BLACKBOX_TARGETS REMOVIDO ← Não precisa mais
    BLACKBOX_GROUPS = f"{PREFIX}/blackbox/groups"    # ✅ MANTER
    BLACKBOX_MODULES = f"{PREFIX}/blackbox/modules.json"  # ✅ MANTER

    # Métodos put_blackbox_target e get_blackbox_target REMOVIDOS
```

---

### 4.3. Backend - API Endpoints

**Arquivo**: `backend/api/blackbox.py`

**Mudanças**:

```python
# ANTES:
@router.get("/targets")
async def list_targets(module: str = None, company: str = None):
    kv = KVManager()
    targets = await kv.list_blackbox_targets({'module': module, 'company': company})  # ❌
    return {"success": True, "data": targets}

# DEPOIS:
@router.get("/targets")
async def list_targets(module: str = None, company: str = None):
    from core.blackbox_manager import BlackboxManager
    manager = BlackboxManager()
    targets = await manager.list_targets({'module': module, 'company': company})  # ✅
    return {"success": True, "data": targets}
```

---

### 4.4. Frontend - BlackboxTargets Page

**Arquivo**: `frontend/src/pages/BlackboxTargets.tsx`

**Mudanças**:

```typescript
// ANTES:
const { data, loading } = await api.get('/api/v1/kv/tree?prefix=skills/eye/blackbox/targets');  // ❌

// DEPOIS:
const { data, loading } = await api.get('/api/v1/blackbox/targets');  // ✅
// Endpoint já retorna dados do Services API (após refatoração backend)
```

---

### 4.5. Import/Export CSV/XLSX

**Arquivo**: `backend/core/blackbox_manager.py`

**Método**: `import_from_csv()`

**Mudança**: Importar DIRETO para Services API (como TenSunS faz)

```python
# ANTES:
async def import_from_csv(self, csv_content: str):
    for row in csv.DictReader(csv_content):
        # 1. Criar no Services
        # 2. Criar no KV  ← REMOVER

# DEPOIS (padrão TenSunS):
async def import_from_csv(self, csv_content: str):
    for row in csv.DictReader(StringIO(csv_content)):
        # APENAS criar no Services (padrão TenSunS upload.py linha 10-80)
        target_data = {
            'module': row['module'],
            'company': row['company'],
            'project': row['project'],
            'env': row['env'],
            'name': row['name'],
            'instance': row['instance']
        }
        await self.create_target(target_data)  # Já adaptado na FASE 4.1
```

---

## 🧹 FASE 5: LIMPEZA E VALIDAÇÃO (1 dia)

### 5.1. Deletar Namespace `blackbox/targets` do KV

**Script a criar**: `backend/cleanup_blackbox_targets_kv.py`

```python
"""
APENAS executar DEPOIS de:
1. FASE 3 concluída (migração de dados)
2. FASE 4 concluída (refatoração de código)
3. Testes validados (FASE 5.2)
"""
import asyncio
from core.kv_manager import KVManager
from core.consul_manager import ConsulManager

async def cleanup_kv():
    print("=" * 80)
    print("LIMPEZA FINAL - DELETAR skills/eye/blackbox/targets")
    print("=" * 80)
    print()

    print("⚠️  ATENÇÃO: Este script irá DELETAR PERMANENTEMENTE:")
    print("   - skills/eye/blackbox/targets/*")
    print()

    confirm1 = input("Você confirmou que FASE 3 e FASE 4 estão completas? (s/N): ")
    if confirm1.lower() != 's':
        print("Cancelado.")
        return

    confirm2 = input("Você validou que tudo funciona sem KV targets? (s/N): ")
    if confirm2.lower() != 's':
        print("Cancelado.")
        return

    confirm3 = input("ÚLTIMA CONFIRMAÇÃO - DELETAR skills/eye/blackbox/targets? (s/N): ")
    if confirm3.lower() != 's':
        print("Cancelado.")
        return

    cm = ConsulManager()

    # Contar quantas keys serão deletadas
    kv_tree = await cm.get_kv_tree('skills/eye/blackbox/targets')
    total_keys = len([k for k in kv_tree.keys() if 'blackbox/targets' in k])

    print(f"\n  Total de keys a deletar: {total_keys}")
    print()

    # Deletar recursivamente
    print("  Deletando...")
    success = await cm.delete_kv_tree('skills/eye/blackbox/targets')

    if success:
        print()
        print("=" * 80)
        print("✅ LIMPEZA CONCLUÍDA")
        print(f"   {total_keys} keys deletadas de skills/eye/blackbox/targets")
        print("=" * 80)
        print()
        print("PRÓXIMOS PASSOS:")
        print("1. Validar que aplicação continua funcionando")
        print("2. Monitorar logs por 24h")
        print("3. Se tudo OK, commit da migração")
    else:
        print("❌ ERRO ao deletar keys")

if __name__ == "__main__":
    asyncio.run(cleanup_kv())
```

---

### 5.2. Testes de Validação

**Script a criar**: `backend/test_migration_validation.py`

```python
"""
Valida que migração funcionou:
1. Targets estão acessíveis via Services API
2. CRUD funciona corretamente
3. Filtros funcionam
4. Import/Export funciona
"""
import asyncio
from core.blackbox_manager import BlackboxManager

async def test_migration():
    print("=" * 80)
    print("VALIDAÇÃO PÓS-MIGRAÇÃO")
    print("=" * 80)
    print()

    manager = BlackboxManager()

    # TEST 1: Listar targets
    print("[TEST 1/5] Listar targets...")
    targets = await manager.list_targets({})
    print(f"  ✓ {len(targets)} targets encontrados")
    assert len(targets) > 0, "Nenhum target encontrado!"

    # TEST 2: Filtros
    print("[TEST 2/5] Testar filtros...")
    filtered = await manager.list_targets({'module': 'http_2xx'})
    print(f"  ✓ {len(filtered)} targets com module=http_2xx")

    # TEST 3: Criar target
    print("[TEST 3/5] Criar target de teste...")
    test_target = {
        'module': 'http_2xx',
        'company': 'TEST_MIGRATION',
        'project': 'validation',
        'env': 'test',
        'name': 'test-target',
        'instance': 'http://test.example.com'
    }
    success, msg = await manager.create_target(test_target)
    print(f"  ✓ Criado: {msg}")
    assert success, f"Falha ao criar: {msg}"

    # TEST 4: Buscar target criado
    print("[TEST 4/5] Buscar target criado...")
    service_id = "http_2xx/TEST_MIGRATION/validation/test@test-target"
    found = await manager.get_target(service_id)
    print(f"  ✓ Encontrado: {found['name']}")
    assert found is not None, "Target não encontrado após criação!"

    # TEST 5: Deletar target de teste
    print("[TEST 5/5] Deletar target de teste...")
    success, msg = await manager.delete_target(service_id)
    print(f"  ✓ Deletado: {msg}")
    assert success, f"Falha ao deletar: {msg}"

    print()
    print("=" * 80)
    print("✅ TODOS OS TESTES PASSARAM")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(test_migration())
```

**Executar**: `python test_migration_validation.py`

---

### 5.3. Documentar Mudanças

**Atualizar**: `MIGRATION_GUIDE.md`

```markdown
# Data Migration - Blackbox Targets

## ⚠️ BREAKING CHANGE

**Data**: 2025-01-09
**Versão**: 2.0.0

### O que mudou

Eliminamos dual storage de blackbox targets. Agora usamos **APENAS** Consul Services API (alinhado com TenSunS original).

### Antes (v1.x)

```
Blackbox Target cadastrado:
├── Consul Services API (blackbox_exporter service)
└── Consul KV (skills/eye/blackbox/targets/{id}.json)  ← REDUNDANTE
```

### Depois (v2.0+)

```
Blackbox Target cadastrado:
└── Consul Services API (blackbox_exporter service)  ← FONTE ÚNICA
```

### Impacto no Código

#### Backend
- `BlackboxManager` agora lê/escreve APENAS no Services API
- Namespace `skills/eye/blackbox/targets` DELETADO do KV
- Métodos `kv.put_blackbox_target()` e `kv.get_blackbox_target()` REMOVIDOS

#### Frontend
- Endpoints `/api/v1/blackbox/targets` agora retornam dados do Services API
- Nenhuma mudança na interface do usuário

### Benefícios

- ✅ 50% menos operações I/O
- ✅ Sem sincronização manual
- ✅ Alinhado com TenSunS
- ✅ Código mais simples

### Rollback

Se necessário reverter:
```bash
python restore_backup.py <timestamp>
```

Backups disponíveis em: `backend/backups/pre_migration_*/`
```

---

## 📊 FASE 6: MONITORAMENTO E AJUSTES FINAIS (ongoing)

### 6.1. Monitorar Logs por 24-48h

**Criar**: `backend/monitor_migration.py`

```python
"""
Monitora aplicação após migração:
- Erros relacionados a KV blackbox/targets
- Performance de queries
- Alertas de divergência
"""
import asyncio
import logging
from datetime import datetime, timedelta

async def monitor():
    print("=" * 80)
    print("MONITORAMENTO PÓS-MIGRAÇÃO")
    print("=" * 80)
    print("Início:", datetime.now().isoformat())
    print()
    print("Monitorando por 48h...")
    print("Pressione Ctrl+C para parar")
    print()

    # Configurar logging para capturar erros
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s',
        handlers=[
            logging.FileHandler('migration_monitoring.log'),
            logging.StreamHandler()
        ]
    )

    # Keywords suspeitas
    suspicious_keywords = [
        'blackbox/targets',
        'BLACKBOX_TARGETS',
        'kv.get_blackbox_target',
        'kv.put_blackbox_target',
        '404',
        'KeyError',
        'dual storage'
    ]

    # Monitorar logs do backend
    # Implementar lógica de parsing de logs aqui

    print("Monitoramento ativo. Verifique migration_monitoring.log")

if __name__ == "__main__":
    asyncio.run(monitor())
```

---

### 6.2. Performance Benchmark

**Criar**: `backend/benchmark_after_migration.py`

```python
"""
Compara performance antes vs depois da migração

BASELINE (antes): Ver backup/benchmark_before_migration.json
ATUAL (depois): Medir agora
"""
import asyncio
import time
from core.blackbox_manager import BlackboxManager

async def benchmark():
    print("=" * 80)
    print("BENCHMARK PÓS-MIGRAÇÃO")
    print("=" * 80)
    print()

    manager = BlackboxManager()

    # TEST 1: List all targets (100x)
    print("[1/3] List all targets (100 iterações)...")
    start = time.time()
    for _ in range(100):
        await manager.list_targets({})
    elapsed = time.time() - start
    avg_list = elapsed / 100
    print(f"  ✓ Tempo médio: {avg_list*1000:.2f}ms")

    # TEST 2: Get single target (100x)
    print("[2/3] Get single target (100 iterações)...")
    targets = await manager.list_targets({})
    if targets:
        first_id = targets[0].get('id', 'test')
        start = time.time()
        for _ in range(100):
            await manager.get_target(first_id)
        elapsed = time.time() - start
        avg_get = elapsed / 100
        print(f"  ✓ Tempo médio: {avg_get*1000:.2f}ms")

    # TEST 3: Filtered query (100x)
    print("[3/3] Filtered query (100 iterações)...")
    start = time.time()
    for _ in range(100):
        await manager.list_targets({'module': 'http_2xx'})
    elapsed = time.time() - start
    avg_filter = elapsed / 100
    print(f"  ✓ Tempo médio: {avg_filter*1000:.2f}ms")

    print()
    print("=" * 80)
    print("BENCHMARK COMPLETO")
    print("=" * 80)
    print(f"List all:   {avg_list*1000:.2f}ms")
    print(f"Get single: {avg_get*1000:.2f}ms")
    print(f"Filtered:   {avg_filter*1000:.2f}ms")
    print("=" * 80)

    # Comparar com baseline (se existir)
    try:
        import json
        with open('backups/benchmark_before_migration.json') as f:
            baseline = json.load(f)

        print()
        print("COMPARAÇÃO COM BASELINE:")
        print(f"List all:   {avg_list*1000:.2f}ms (antes: {baseline['list_all']*1000:.2f}ms) → {((avg_list/baseline['list_all'])-1)*100:+.1f}%")
        print(f"Get single: {avg_get*1000:.2f}ms (antes: {baseline['get_single']*1000:.2f}ms) → {((avg_get/baseline['get_single'])-1)*100:+.1f}%")
        print(f"Filtered:   {avg_filter*1000:.2f}ms (antes: {baseline['filtered']*1000:.2f}ms) → {((avg_filter/baseline['filtered'])-1)*100:+.1f}%")

        if avg_list < baseline['list_all']:
            print("\n✅ PERFORMANCE MELHOROU!")
        else:
            print("\n⚠️  Performance piorou - investigar")
    except FileNotFoundError:
        print("\nℹ️  Baseline não encontrado - criar benchmark_before_migration.json antes da próxima migração")

if __name__ == "__main__":
    asyncio.run(benchmark())
```

---

## 📝 CHECKLIST FINAL

### Antes de Iniciar Migração
- [ ] Backup completo realizado
- [ ] Restore testado com sucesso
- [ ] Equipe notificada sobre janela de manutenção
- [ ] Ambiente de homologação testado

### FASE 1 - Análise
- [ ] Análise TenSunS documentada
- [ ] KV usage mapeado
- [ ] Dual storage code identificado
- [ ] Matriz de decisão aprovada

### FASE 2 - Preparação
- [ ] Backup completo criado
- [ ] Script de restore validado
- [ ] Metadata fields confirmado no KV
- [ ] Benchmarks de performance (baseline)

### FASE 3 - Migração de Dados
- [ ] Targets migrados para Services API
- [ ] Divergências resolvidas
- [ ] Validação de integridade 100%

### FASE 4 - Refatoração
- [ ] Backend refatorado
  - [ ] `blackbox_manager.py`
  - [ ] `kv_manager.py`
  - [ ] `api/blackbox.py`
  - [ ] Import/Export CSV
- [ ] Frontend refatorado
  - [ ] `BlackboxTargets.tsx`
  - [ ] `api.ts`
- [ ] Testes unitários atualizados

### FASE 5 - Limpeza
- [ ] KV `blackbox/targets` deletado
- [ ] Testes de validação 100% passando
- [ ] Documentação atualizada
- [ ] MIGRATION_GUIDE.md criado

### FASE 6 - Monitoramento
- [ ] 24h de monitoramento sem erros
- [ ] Benchmark de performance validado
- [ ] Rollback plan documentado
- [ ] Commit final com tag v2.0.0

---

## 🚨 RISCOS E MITIGAÇÕES

| Risco | Probabilidade | Impacto | Mitigação |
|-------|--------------|---------|-----------|
| Perda de dados durante migração | Baixa | Alto | Backup completo + validação antes de deletar KV |
| Divergência KV vs Services | Média | Médio | Script de comparação + resolução manual |
| Downtime durante migração | Baixa | Alto | Migração em horário de baixo uso + rollback rápido |
| Código não funciona após refatoração | Média | Alto | Testes automatizados + ambiente de homologação |
| Performance pior após migração | Baixa | Médio | Benchmark antes/depois + otimizações |

---

## 📞 SUPORTE E ROLLBACK

### Se algo der errado:

```bash
# 1. Parar aplicação
pm2 stop skillseye

# 2. Restaurar backup
cd backend
python restore_backup.py <timestamp>

# 3. Reverter código (git)
git revert <commit-hash-da-migração>

# 4. Reiniciar aplicação
pm2 start skillseye

# 5. Validar
curl http://localhost:5000/api/v1/health
```

### Contatos de Emergência
- Desenvolvedor Principal: [seu-contato]
- DevOps: [contato-devops]
- Backup do Backup: `backups/pre_migration_*/`

---

## 🎯 MÉTRICAS DE SUCESSO

### Após migração completa, validar:

- [ ] **Performance**: Queries 30-50% mais rápidas
- [ ] **Storage**: ~50% menos keys no KV
- [ ] **Código**: 200-300 linhas de código removidas
- [ ] **Complexidade**: Eliminação de sincronização manual
- [ ] **Alinhamento**: 100% alinhado com TenSunS

---

## 📚 REFERÊNCIAS

- TenSunS GitHub: https://github.com/starsliao/TenSunS
- TenSunS docs/blackbox站点监控.md
- TenSunS flask-consul/units/blackbox_manager.py
- TenSunS flask-consul/units/consul_kv.py
- TenSunS flask-consul/units/upload.py
- Consul Services API: https://developer.hashicorp.com/consul/api-docs/agent/service
- Consul KV API: https://developer.hashicorp.com/consul/api-docs/kv

---

**FIM DO PLANO DE MIGRAÇÃO**

**Versão**: 1.0
**Última atualização**: 2025-01-09
**Aprovação pendente**: [ ] Desenvolvedor Principal  [ ] DevOps  [ ] Product Owner
