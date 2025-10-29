# Relatório de Atualização - Debugging e Correções

**Data:** 2025-10-28
**Objetivo:** Adicionar logs de debug para rastrear corrupção de dados e corrigir warnings

---

## 🔍 Problema Principal

O sistema estava salvando arquivos corrompidos apesar de:
- Console mostrar "Jobs finais a serem salvos: 14"
- Validações de lista vazia implementadas
- Proteção backend contra perda de dados

**Sintoma:** Contagem de jobs está correta (14) mas os DADOS estão sendo corrompidos durante a transmissão do frontend para o backend.

---

## ✅ Correções Implementadas

### 1. Logging Detalhado no Backend

**Arquivo:** `backend/api/prometheus_config.py` (linhas 747-758)

```python
# CRÍTICO: Logar payload COMPLETO recebido
import json
print(f"[CRITICAL BACKEND] Payload recebido:")
print(json.dumps(jobs, indent=2, default=str))

# Verificar se jobs contém dados válidos
if jobs:
    print(f"[CRITICAL BACKEND] Primeiro job: {json.dumps(jobs[0], indent=2, default=str)}")
    empty_jobs = [i for i, j in enumerate(jobs) if not j or not isinstance(j, dict) or len(j) == 0]
    if empty_jobs:
        print(f"[CRITICAL BACKEND] ⚠️ Jobs vazios detectados nos índices: {empty_jobs}")
```

**Efeito:** Agora podemos ver EXATAMENTE o que o backend recebe do frontend, não apenas a contagem.

### 2. Logging Detalhado no Frontend (já implementado)

**Arquivo:** `frontend/src/pages/PrometheusConfig.tsx` (linhas 457-474)

```typescript
// CRÍTICO: Logar payload COMPLETO antes de enviar
console.log('[CRITICAL] Payload sendo enviado:', {
    url: selectedFile,
    jobsCount: updatedJobs.length,
    payload: updatedJobs,
    payloadString: JSON.stringify(updatedJobs, null, 2)
});

// Validação final: verificar se jobs têm conteúdo
const emptyJobs = updatedJobs.filter(j => !j || Object.keys(j).length === 0);
if (emptyJobs.length > 0) {
    Modal.error({
        title: '⚠️ Jobs Vazios Detectados',
        content: `${emptyJobs.length} jobs estão vazios ou corrompidos!`
    });
    return;
}
```

**Efeito:** Vemos o payload COMPLETO antes de enviar via axios, não apenas contagem.

### 3. Correção do Warning do Modal.info

**Problema:** Warning `[antd: Modal] Static function can not consume context like dynamic theme`

**Arquivo:** `frontend/src/pages/PrometheusConfig.tsx`

**Mudanças:**
- **Linhas 124-125:** Adicionadas variáveis de estado
  ```typescript
  const [previewModalVisible, setPreviewModalVisible] = useState(false);
  const [previewData, setPreviewData] = useState<any>(null);
  ```

- **Linhas 1253-1267:** Substituído `Modal.info()` estático por estado
  ```typescript
  // ANTES (causava warning)
  Modal.info({
      title: 'Preview da Configuração JSON',
      content: <pre>...</pre>
  });

  // DEPOIS (sem warning)
  setPreviewData(editingJobData);
  setPreviewModalVisible(true);
  ```

- **Linhas 1400-1421:** Adicionado componente Modal controlado por estado
  ```typescript
  <Modal
      open={previewModalVisible}
      onOk={() => setPreviewModalVisible(false)}
      onCancel={() => setPreviewModalVisible(false)}
      title="Preview da Configuração JSON"
      width={800}
  >
      <pre>...</pre>
  </Modal>
  ```

**Efeito:** ✅ Botão "Ver Preview" agora funciona SEM warnings do Ant Design

---

## 🧪 Como Testar

### 1. Reiniciar aplicação
```bash
restart-app.bat
```

### 2. Abrir navegador
- Frontend: http://localhost:8081
- Abrir Console do navegador (F12)

### 3. Tentar editar um job
1. Ir em "Prometheus Config"
2. Selecionar arquivo
3. Editar algum job (exemplo: mudar uma tag)
4. Clicar em "Salvar"

### 4. Analisar logs

**No Console do Navegador (F12):**
```
[SAVE DEBUG] Estado atual: {...}
[CRITICAL] Payload sendo enviado: {
    url: "/etc/prometheus/prometheus.yml",
    jobsCount: 14,
    payload: [...],  // ← VERIFICAR SE JOBS TÊM CONTEÚDO
    payloadString: "..."
}
```

**No Terminal do Backend (cmd Python):**
```
[UPDATE JOBS] Recebidos 14 jobs
[CRITICAL BACKEND] Payload recebido:
[
  {
    "job_name": "http_4xx",
    "metrics_path": "/probe",
    ...  // ← VERIFICAR SE DADOS ESTÃO COMPLETOS
  },
  ...
]
[CRITICAL BACKEND] Primeiro job: {...}
```

### 5. Comparar
- ✅ **Payload frontend** deve ter jobs completos com todos os campos
- ✅ **Payload backend** deve receber os mesmos dados
- ❌ Se backend receber `[]` ou jobs vazios, encontramos o ponto de corrupção

---

## 🎯 O Que Procurar

### Cenário 1: Corrupção no Frontend (antes de enviar)
Se `[CRITICAL] Payload sendo enviado` mostrar jobs vazios ou corrompidos:
- Problema: Estado `jobs` ou lógica `jobs.map()` no frontend
- Solução: Investigar linha 388 (`jobs.map(...)`)

### Cenário 2: Corrupção na Transmissão (axios)
Se frontend mostra dados OK mas backend recebe dados vazios:
- Problema: Serialização axios ou limites de payload
- Solução: Investigar axios config, timeout, ou tamanho do payload

### Cenário 3: Corrupção no Backend (após receber)
Se backend recebe dados OK mas salva errado:
- Problema: Lógica de edição cirúrgica em `multi_config_manager.py`
- Solução: Investigar `update_jobs_in_file()` e `_update_dict_surgically()`

---

## 📊 Status dos Botões

| Botão | Status | Localização | Observações |
|-------|--------|-------------|-------------|
| **Ver Preview** | ✅ CORRIGIDO | Linha 1253-1267 | Modal.info warning resolvido |
| **Formatar** | ✅ OK | Linha 1268-1304 | Já funcionava |
| **Recarregar** | ✅ OK | Linha 894-901 | Já funcionava |
| **"Atualizar"** | ❓ NÃO ENCONTRADO | ? | Não existe botão "Atualizar" no código |

**Nota:** O usuário mencionou botão "Atualizar" mas não existe no código. Talvez seja:
- Botão "Editar" da tabela (linha 792-796)
- Botão "Adicionar Job" (linha 885-893)
- Botão "Salvar" do drawer de edição

---

## 🚀 Próximos Passos

1. ✅ Reiniciar aplicação com `restart-app.bat`
2. ⏳ Testar edição de job e analisar logs
3. ⏳ Comparar payload frontend vs backend
4. ⏳ Identificar ponto exato da corrupção
5. ⏳ Implementar correção específica baseada nos logs

---

## 📝 Observações

- **Validações já implementadas funcionam para detectar CONTAGEM de jobs**
- **Validações NÃO detectam CONTEÚDO corrompido (jobs vazios com contagem correta)**
- **Logs detalhados adicionados são CRÍTICOS para diagnosticar o problema**
- **User tem backups funcionando - sistema de proteção básico OK**

---

## 🔗 Arquivos Modificados

1. `backend/api/prometheus_config.py` - Logs de debug backend
2. `frontend/src/pages/PrometheusConfig.tsx` - Logs frontend + correção Modal.info
3. Este relatório: `DEBUG_UPDATE_REPORT.md`

---

## ⚠️ Avisos Importantes

- **NÃO testar em produção sem backup**
- **Verificar SEMPRE logs antes e depois de salvar**
- **Se corrupção continuar, NÃO salvar - cancelar e analisar logs**
- **Restaurar de backup se necessário**

---

**Próxima ação:** Reiniciar aplicação e testar com logs ativados para identificar ponto de corrupção.
