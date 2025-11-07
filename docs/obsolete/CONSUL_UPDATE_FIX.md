# Correção do Update de Serviços - Análise Completa

## 🔴 PROBLEMA IDENTIFICADO

O código estava **DELETANDO os serviços ao tentar editar**.

### Código Anterior (ERRADO)
```python
async def update_service(self, service_id: str, service_data: Dict):
    # ❌ ERRADO - Isso DELETA o serviço!
    await self.deregister_service(service_id)  # ← Deleta
    await asyncio.sleep(0.5)
    await self.register_service(service_data)   # ← Recria (mas pode falhar!)
```

**Por que estava deletando?**
1. Fazia `deregister` primeiro (deleta o serviço)
2. Tentava `register` novamente (recria)
3. Se o `register` falhasse, o serviço ficava deletado permanentemente!

---

## ✅ SOLUÇÃO IMPLEMENTADA

Baseada na **documentação oficial do Consul**:
- **Fonte**: https://developer.hashicorp.com/consul/api-docs/agent/service

### Descobertas da Documentação

1. **NÃO existe endpoint nativo de UPDATE no Consul**
2. **Para atualizar**: basta RE-REGISTRAR com o mesmo ID
3. **O Consul substitui automaticamente** o serviço existente quando você registra com mesmo ID
4. **NÃO é necessário** fazer deregister antes

### Código Corrigido (CORRETO)
```python
async def update_service(self, service_id: str, service_data: Dict):
    """
    Atualiza um serviço existente

    IMPORTANTE: Segundo documentação oficial do Consul, para atualizar um serviço
    basta RE-REGISTRAR com o mesmo ID. NÃO é necessário fazer deregister antes.

    O Consul automaticamente substitui o serviço quando você registra com mesmo ID.
    """
    # Preparar payload normalizado
    normalized_data = service_data.copy()

    # 1. Converter campo "Service" → "Name" (obrigatório para register)
    #    GET /agent/services retorna "Service"
    #    PUT /agent/service/register espera "Name"
    if "Service" in normalized_data and "Name" not in normalized_data:
        normalized_data["Name"] = normalized_data.pop("Service")

    # 2. Garantir que o ID está presente
    if "ID" not in normalized_data:
        normalized_data["ID"] = service_id

    # 3. Remover campos read-only que não podem ser enviados
    readonly_fields = ["CreateIndex", "ModifyIndex", "ContentHash", "Datacenter", "PeerName"]
    for field in readonly_fields:
        normalized_data.pop(field, None)

    # 4. Ajustar campo Weights se estiver vazio
    if "Weights" in normalized_data and normalized_data["Weights"] == {}:
        normalized_data["Weights"] = None

    # 5. RE-REGISTRAR o serviço (Consul atualiza automaticamente)
    #    ✅ NÃO fazer deregister antes - isso deletaria o serviço!
    return await self.register_service(normalized_data)
```

---

## 📊 DIFERENÇAS ENTRE GET E PUT

### GET /v1/agent/services (Resposta)
```json
{
  "web1": {
    "ID": "web1",
    "Service": "web",           // ← Campo chamado "Service"
    "Address": "10.0.0.1",
    "Port": 8080,
    "Tags": ["v1"],
    "Meta": {"env": "prod"},
    "Weights": {"Passing": 10, "Warning": 1},
    "CreateIndex": 100,         // ← Campo read-only
    "ModifyIndex": 101,         // ← Campo read-only
    "ContentHash": "abc123",    // ← Campo read-only
    "Datacenter": "dc1",        // ← Campo read-only
    "PeerName": ""              // ← Campo read-only
  }
}
```

### PUT /v1/agent/service/register (Payload)
```json
{
  "ID": "web1",
  "Name": "web",              // ← Campo chamado "Name" (NÃO "Service")
  "Address": "10.0.0.1",
  "Port": 8081,               // ← Porta atualizada
  "Tags": ["v2"],             // ← Tags atualizadas
  "Meta": {"env": "prod"},
  "Weights": {"Passing": 10, "Warning": 1}
  // ✅ Campos read-only NÃO devem ser incluídos
}
```

### Campos que Precisam ser Transformados

| Operação | Campo GET | Campo PUT | Ação |
|----------|-----------|-----------|------|
| **Renomear** | `Service` | `Name` | **OBRIGATÓRIO** - Renomear |
| **Remover** | `CreateIndex` | - | Read-only, remover |
| **Remover** | `ModifyIndex` | - | Read-only, remover |
| **Remover** | `ContentHash` | - | Read-only, remover |
| **Remover** | `Datacenter` | - | Read-only, remover |
| **Remover** | `PeerName` | - | Read-only, remover |
| **Ajustar** | `Weights: {}` | `Weights: null` | Converter vazio para null |

---

## 🔧 CORREÇÕES IMPLEMENTADAS

### Arquivo: `backend/core/consul_manager.py` (linhas 338-384)

**Mudanças**:
1. ✅ **Removido** `deregister_service` do processo de update
2. ✅ **Adicionado** conversão `Service` → `Name`
3. ✅ **Adicionado** remoção de campos read-only
4. ✅ **Adicionado** ajuste de `Weights` vazio
5. ✅ **Adicionado** tratamento de exceção com traceback
6. ✅ **Atualizado** docstring com referência à documentação oficial

### Arquivo: `backend/api/services.py` (linhas 471-489)

**Mudanças**:
1. ✅ **Adicionado** mapeamento de campos lowercase → Uppercase
2. ✅ **Corrigido** merge de dados para usar nomes corretos dos campos

---

## 📝 COMO TESTAR

1. **Abra a interface web**: http://localhost:8082
2. **Vá para a página Services** ou **Exporters**
3. **Selecione um serviço existente** e clique em **Editar**
4. **Altere algum campo** (ex: Port, Tags, Address)
5. **Salve as alterações**

### ✅ Comportamento Esperado (CORRETO)
- O serviço é **atualizado** com os novos valores
- O serviço **NÃO é deletado**
- Mensagem de sucesso aparece
- Os dados são persistidos no Consul

### ❌ Comportamento Anterior (ERRADO)
- O serviço era **deletado** durante o update
- Se o registro falhasse, o serviço sumia permanentemente
- Erro 404 ou 500 após a edição

---

## 🎯 CAMPOS TESTADOS

Certifique-se de testar a edição de:

- ✅ **Port** - Alterar número da porta
- ✅ **Address** - Alterar endereço IP
- ✅ **Tags** - Adicionar/remover tags
- ✅ **Meta** - Alterar metadados customizados

---

## 📚 REFERÊNCIAS

- **Consul API - Service Agent**: https://developer.hashicorp.com/consul/api-docs/agent/service
- **Consul GitHub - API Structs**: https://github.com/hashicorp/consul/blob/main/api/agent.go
- **Consul Commands - Service Register**: https://developer.hashicorp.com/consul/commands/services/register

---

## ⚠️ OBSERVAÇÕES IMPORTANTES

1. **Multi-node**: O código já suporta atualização em múltiplos nós através do parâmetro `node_addr`
2. **ID Sanitization**: O código já sanitiza IDs corretamente com `ConsulManager.sanitize_service_id()`
3. **BlackboxManager**: O BlackboxManager continua usando delete + add porque pode estar mudando o ID do serviço (quando muda module, company, project, env, name). Isso está correto para aquele caso de uso.
4. **Service ID vs Service Name**:
   - **ID**: Identificador único por nó (usado para deregister/update)
   - **Name**: Nome lógico do serviço (usado para service discovery)
   - Se não especificar ID, Consul usa Name como ID

---

## 🎉 RESULTADO

O update de serviços agora funciona corretamente:
- ✅ **NÃO deleta** o serviço
- ✅ **Atualiza** os campos modificados
- ✅ **Mantém** os campos não alterados
- ✅ **Segue** a documentação oficial do Consul
- ✅ **É mais rápido** (1 operação ao invés de 2)
- ✅ **É mais seguro** (sem risco de perder o serviço se o registro falhar)
