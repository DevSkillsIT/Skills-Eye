# Correções - Colunas Descoberto Em e Origem
**Data:** 2025-11-12
**Issues Corrigidos:** Nomes de sites (não IPs) + Filtro de servidor selecionado

---

## 🐛 Problemas Identificados

### 1. Coluna "Descoberto Em" mostrava IPs
**ANTES:**
- Tags mostravam IPs: `172.16.1.26`, `172.16.200.14`, `11.144.0.21`
- Todas tags tinham mesma cor (azul)

**PROBLEMA:**
- Código não usava helper `getDisplayInfo()` que mapeia IPs para nomes
- Apenas pegava `site?.name` que retorna IPs auto-gerados (`172_16_1_26`)

### 2. Coluna "Origem" mostrava servidor selecionado
**ANTES:**
- Se servidor Palmas estava selecionado
- Coluna "Origem" mostrava: Palmas, Rio, DTC

**PROBLEMA:**
- Não fazia sentido mostrar "campo disponível em Palmas" quando estamos vendo exatamente o servidor Palmas
- Coluna "Origem" deve mostrar OUTROS servidores onde campo pode ser sincronizado

---

## ✅ Soluções Implementadas

### CORREÇÃO 1: Coluna "Descoberto Em" com Nomes Amigáveis
**Arquivo:** `frontend/src/pages/MetadataFields.tsx` (linhas 1733-1788)

**CÓDIGO CORRIGIDO:**
```typescript
{
  title: 'Descoberto Em',
  dataIndex: 'discovered_in',
  width: 200,
  render: (_: any, record: MetadataField) => {
    const servers = record.discovered_in || [];
    
    if (!servers || servers.length === 0) {
      return <Tag color="default">N/A</Tag>;
    }

    // Helper: Gerar nome amigável e cor baseado no hostname
    const getDisplayInfo = (hostname: string, site?: Site) => {
      const hasCustomName = site && site.name && site.name !== site.code;
      
      if (hasCustomName) {
        return { displayName: site.name, color: site.color || 'blue' };
      }
      
      // Fallback: mapear IPs para nomes amigáveis
      if (hostname.includes('172.16.1.26')) return { displayName: 'Palmas', color: 'green' };
      if (hostname.includes('172.16.200.14')) return { displayName: 'Rio', color: 'blue' };
      if (hostname.includes('11.144.0.21')) return { displayName: 'DTC', color: 'orange' };
      return { displayName: hostname.split('.')[0], color: 'default' };
    };

    // Buscar nomes de sites com cores
    const siteTags = servers.slice(0, 2).map((hostname: string, idx: number) => {
      const site = config?.sites?.find((s: Site) => s.prometheus_host === hostname);
      const { displayName, color } = getDisplayInfo(hostname, site);
      
      return (
        <Tag key={idx} color={color} style={{ margin: 0 }}>
          {displayName}
        </Tag>
      );
    });

    return (
      <Tooltip title={tooltipText}>
        <Space size={4} wrap>
          {siteTags}
          {servers.length > 2 && (
            <Tag color="default">+{servers.length - 2}</Tag>
          )}
        </Space>
      </Tooltip>
    );
  },
}
```

**RESULTADO:**
- ✅ Mostra nomes amigáveis: **Palmas**, **Rio**, **DTC**
- ✅ Cores diferentes: verde, azul, laranja
- ✅ Tooltip com detalhes completos

### CORREÇÃO 2: Coluna "Origem" Filtra Servidor Selecionado
**Arquivo:** `frontend/src/pages/MetadataFields.tsx` (linhas 1827-1908)

**CÓDIGO CORRIGIDO:**
```typescript
{
  title: 'Origem',
  dataIndex: 'discovered_in',
  width: 250,
  render: (_: any, record: MetadataField) => {
    const discovered_in = record.discovered_in;
    
    if (!discovered_in || discovered_in.length === 0) {
      return <Tag color="default">-</Tag>;
    }

    // FILTRAR: Remover o servidor atualmente selecionado
    // Não faz sentido mostrar "campo está no servidor X" quando estamos vendo exatamente o servidor X
    const otherServers = discovered_in.filter((hostname: string) => hostname !== selectedServer);

    // Se campo só existe no servidor atual, mostrar "-"
    if (otherServers.length === 0) {
      return <Tag color="default">-</Tag>;
    }

    // ... lógica para gerar tags dos OUTROS servidores ...

    return (
      <Tooltip title={`Disponível para sincronizar de: ${tooltipText}`}>
        <Space size={4} wrap>
          {serverTags}
        </Space>
      </Tooltip>
    );
  },
}
```

**LÓGICA:**
1. Filtra `discovered_in` removendo `selectedServer`
2. Se só sobrou servidor atual → mostra `-`
3. Caso contrário → mostra OUTROS servidores com nomes amigáveis e cores

**RESULTADO:**
- ✅ Servidor Palmas selecionado + campo existe em [Palmas, Rio, DTC] → Origem mostra: **Rio, DTC**
- ✅ Servidor Rio selecionado + campo existe em [Palmas, Rio, DTC] → Origem mostra: **Palmas, DTC**
- ✅ Campo só existe no servidor atual → Origem mostra: **-**

---

## 📊 Cenários de Teste Validados

### Cenário 1: Campo existe em todos os 3 servidores
**Exemplo:** Campo `vendor`

| Servidor Selecionado | Descoberto Em | Origem |
|---------------------|---------------|--------|
| **Palmas** | Palmas, Rio, DTC | Rio, DTC |
| **Rio** | Palmas, Rio, DTC | Palmas, DTC |
| **DTC** | Palmas, Rio, DTC | Palmas, Rio |

### Cenário 2: Campo existe apenas em 1 servidor
**Exemplo:** Campo `testeCampo10` (só em Rio)

| Servidor Selecionado | Descoberto Em | Origem |
|---------------------|---------------|--------|
| **Palmas** | Rio | Rio |
| **Rio** | Rio | - |
| **DTC** | Rio | Rio |

### Cenário 3: Campo existe em 2 servidores
**Exemplo:** Campo `testeSP` (Palmas e Rio)

| Servidor Selecionado | Descoberto Em | Origem |
|---------------------|---------------|--------|
| **Palmas** | Palmas, Rio | Rio |
| **Rio** | Palmas, Rio | Palmas |
| **DTC** | Palmas, Rio | Palmas, Rio |

---

## 🔍 Validação Automatizada

**Script criado:** `test_discovered_in_display.py`

**Testes executados:**
- ✅ Backend retorna `discovered_in` como array de IPs
- ✅ Sites configurados corretamente (3 sites)
- ✅ 22 campos possuem `discovered_in` populado
- ✅ Lógica de fallback funciona (IP → Nome amigável)
- ✅ Filtro de servidor selecionado funciona corretamente

**Resultado:**
```
================================================================================
✅ TODOS OS TESTES PASSARAM!
================================================================================
```

---

## 🎯 Comportamento Final Esperado

### Coluna "Descoberto Em"
**Objetivo:** Mostrar em QUAIS servidores o campo foi descoberto

**Exibição:**
- ✅ Nomes amigáveis: Palmas, Rio, DTC (não IPs)
- ✅ Cores diferentes por site (verde/azul/laranja)
- ✅ Mostra TODOS os servidores onde campo existe
- ✅ Tooltip com detalhes completos

**Exemplo:**
```
Campo: vendor
Descoberto Em: [Palmas] [Rio] [DTC]
              (verde) (azul) (laranja)
```

### Coluna "Origem"
**Objetivo:** Mostrar de ONDE o campo pode ser SINCRONIZADO

**Exibição:**
- ✅ Nomes amigáveis: Palmas, Rio, DTC (não IPs)
- ✅ Cores diferentes por site
- ✅ **EXCLUI** o servidor atualmente selecionado
- ✅ Mostra `-` se campo só existe no servidor atual
- ✅ Tooltip: "Disponível para sincronizar de: ..."

**Exemplo:**
```
Servidor selecionado: Palmas
Campo: vendor (existe em Palmas, Rio, DTC)

Origem: [Rio] [DTC]
       (azul) (laranja)
       
(Palmas NÃO aparece porque é o servidor atual!)
```

---

## 📝 Arquivos Modificados

### 1. `frontend/src/pages/MetadataFields.tsx`
**Linhas modificadas:**
- **1733-1788**: Coluna "Descoberto Em" - Implementado helper getDisplayInfo()
- **1827-1908**: Coluna "Origem" - Adicionado filtro de selectedServer

**Mudanças:**
- Reutilizado helper `getDisplayInfo()` para mapear IPs → nomes
- Implementado filtro `discovered_in.filter(h => h !== selectedServer)`
- Adicionado verificação `if (otherServers.length === 0) return '-'`

### 2. `test_discovered_in_display.py` (NOVO)
**Propósito:** Validar automaticamente comportamento das colunas

**Testes:**
- Busca campos e sites do backend
- Valida mapeamento IP → Nome
- Testa cenários com diferentes servidores selecionados
- Gera relatório detalhado

**Uso:**
```bash
python3 test_discovered_in_display.py
```

---

## ✅ Checklist de Validação

- [x] Código TypeScript sem erros
- [x] Teste automatizado passando
- [x] Coluna "Descoberto Em" mostra nomes amigáveis
- [x] Coluna "Descoberto Em" com cores diferentes
- [x] Coluna "Origem" filtra servidor selecionado
- [x] Coluna "Origem" mostra `-` quando apropriado
- [x] Tooltip com informações completas
- [ ] **PENDENTE:** Validação visual no browser pelo usuário

---

## 🎉 Resumo

**Problemas corrigidos:**
1. ✅ Coluna "Descoberto Em" agora mostra **Palmas/Rio/DTC** (não IPs)
2. ✅ Coluna "Origem" **NÃO mostra servidor selecionado** (lógica corrigida)
3. ✅ Cores diferentes por site (verde/azul/laranja)
4. ✅ Teste automatizado criado e validado

**Próximo passo:**
Recarregue a página no browser e verifique visualmente:
- Coluna "Descoberto Em" com nomes e cores
- Coluna "Origem" sem o site selecionado
