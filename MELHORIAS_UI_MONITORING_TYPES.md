# Melhorias na UI da Página Monitoring Types

**Data:** 2025-11-04
**Versão:** 2.0 - Refatoração Completa

---

## 🎯 **OBJETIVO**

Padronizar COMPLETAMENTE a página **Monitoring Types** seguindo o padrão estabelecido na página **PrometheusConfig**, incluindo controles de densidade, seletor de colunas e layout profissional.

---

## ✅ **MUDANÇAS IMPLEMENTADAS**

### **1. Substituição do Segmented por Radio.Group**

**Problema Anterior:**
- Segmented tinha layout estranho
- Ícones não apareciam
- Botões muito grandes

**Solução:**
```tsx
<Radio.Group value={viewMode} onChange={(e) => handleViewModeChange(e.target.value)} size="large">
  <Radio.Button value="all">
    <GlobalOutlined /> Todos os Servidores
  </Radio.Button>
  <Radio.Button value="specific">
    <CloudServerOutlined /> Servidor Específico
  </Radio.Button>
</Radio.Group>
```

**Benefícios:**
- ✅ Ícones aparecem corretamente inline
- ✅ Layout compacto e profissional
- ✅ Padrão consistente com outras páginas
- ✅ Mais intuitivo

---

### **2. Controles de Densidade e Colunas (NOVO)**

**Implementado padrão PrometheusConfig:**
```tsx
<Space.Compact size="large">
  <Dropdown menu={{ items: [{ key: 'small', label: 'Compacto' }, ...], onClick: ... }}>
    <Button icon={<ColumnHeightOutlined />} size="large">
      Densidade
    </Button>
  </Dropdown>
  <ColumnSelector
    columns={columnConfig}
    onChange={setColumnConfig}
    storageKey="monitoring-types-columns"
    buttonSize="large"
  />
</Space.Compact>
```

**Características:**
- ✅ **Densidade**: Controla espaçamento da tabela (Compacto/Médio/Grande)
- ✅ **ColumnSelector**: Permite mostrar/ocultar colunas com drag-and-drop
- ✅ **Persistência**: Preferências salvas no localStorage
- ✅ **Space.Compact**: Botões agrupados visualmente

---

### **3. Correção da Coluna "Servidores"**

**Problema:**
- Coluna não mostrava múltiplos servidores mesmo em modo "ALL"

**Causa Raiz:**
- Cada servidor usa job_names DIFERENTES (`node_exporter`, `node_exporter_rio`, `node_exporter_dtc_remote`)
- Portanto, são tipos DIFERENTES (IDs diferentes)
- Backend só popula `servers` (array) quando o MESMO job_name existe em múltiplos servidores

**Solução (Render Correto):**
```tsx
{
  key: 'servers',
  title: 'Servidores',
  render: (_: any, record: MonitoringType) => {
    const serverList = record.servers || (record.server ? [record.server] : []);
    return (
      <Space wrap>
        {serverList.map((srv: string) => (
          <Tag key={srv} icon={<CloudServerOutlined />} color="orange">{srv}</Tag>
        ))}
      </Space>
    );
  },
}
```

**Resultado:**
- ✅ Mostra hostname correto para cada tipo
- ✅ Suporta array de servidores (quando aplicável)
- ✅ Fallback para servidor único

---

### **4. Layout Reestruturado Completamente**

**Nova Estrutura:**
```
┌──────────────────────────────────────────────────────┐
│ 📊 Estatísticas Gerais (4 cards)                    │
├──────────────────────────────────────────────────────┤
│ ℹ️ Alert: Visualização Atual                        │
├──────────────────────────────────────────────────────┤
│ ⚙️ Controles de Visualização                        │
│  ┌────────────────────────────────────────────────┐ │
│  │ [○ Todos] [● Específico]  [Densidade] [Colunas]│ │
│  │ ↑ Radio.Group           ↑ Space.Compact       │ │
│  │                                                │ │
│  │ [ServerSelector] (apenas modo específico)     │ │
│  └────────────────────────────────────────────────┘ │
├──────────────────────────────────────────────────────┤
│ 📋 Tabs por Categoria + Tabela                     │
└──────────────────────────────────────────────────────┘
```

---

## 📊 **COMPARAÇÃO VISUAL**

### **ANTES (Segmented - Problemático):**
```
┌──────────────────────────────────────────────┐
│ [        Todos os Servidores        ]       │
│ [       Servidor Específico        ]       │
│ ↑ Sem ícones, layout estranho               │
└──────────────────────────────────────────────┘
```

### **DEPOIS (Radio.Group + Space.Compact):**
```
┌──────────────────────────────────────────────┐
│ [🌐 Todos] [☁️ Específico]  [📏][⚙️]         │
│ ↑ Compacto      ↑ Ícones  ↑ Controles juntos │
└──────────────────────────────────────────────┘
```

---

## 🎨 **CARACTERÍSTICAS DETALHADAS**

### **Radio.Group:**
- **Tipo:** Radio.Button (estilo botão)
- **Tamanho:** `large`
- **Ícones:** `GlobalOutlined` (🌐) e `CloudServerOutlined` (☁️)
- **Valores:** 'all' | 'specific'

### **Dropdown de Densidade:**
- **Ícone:** `ColumnHeightOutlined` (📏)
- **Opções:** Compacto, Médio, Grande
- **Efeito:** Altera prop `size` da Table

### **ColumnSelector:**
- **Configuração Inicial:** 6 colunas
  1. Nome
  2. Job Name
  3. Exporter Type
  4. Módulo
  5. Campos Metadata
  6. Servidores
- **Drag-and-Drop:** Reordena colunas
- **Checkbox:** Mostra/oculta
- **Persistência:** `localStorage` key `monitoring-types-columns`

---

## 📚 **CATEGORIAS DE MONITORAMENTO**

O backend classifica automaticamente em **5 categorias**:

### **1. Network Probes (network-probes)**
- Módulos: icmp, ping, tcp, dns, ssh
- Display: "Network Probes (Rede)"

### **2. Web Probes (web-probes)**
- Módulos: http_2xx, http_4xx, https, http_post_2xx
- Display: "Web Probes (Aplicações)"

### **3. System Exporters (system-exporters)**
- Exporters: node, windows, snmp
- Display: "Exporters: Sistemas"

### **4. Database Exporters (database-exporters)**
- Exporters: mysql, postgres, redis, mongo
- Display: "Exporters: Bancos de Dados"

### **5. Custom Exporters (custom-exporters)**
- Padrão: Qualquer outro job
- Display: "Exporters: Customizados"

**Atualmente no ambiente:**
- ✅ Custom Exporters (7 tipos)
- ✅ System Exporters (6 tipos)
- ✅ Network Probes (2 tipos)
- ⚠️ Web Probes (0 - não configurados)
- ⚠️ Database Exporters (0 - não configurados)

---

## 🧪 **TESTE COMPLETO**

### **Teste 1: Ícones Visíveis**
1. Acesse http://localhost:8081/monitoring-types
2. Verifique Radio.Group
3. ✅ Deve ver ícone 🌐 ao lado de "Todos os Servidores"
4. ✅ Deve ver ícone ☁️ ao lado de "Servidor Específico"

### **Teste 2: Controle de Densidade**
1. Clique em "Densidade"
2. Selecione "Compacto"
3. ✅ Tabela fica compacta
4. ✅ Seleção persiste ao recarregar

### **Teste 3: Seletor de Colunas**
1. Clique no botão de engrenagem
2. Desmarque "Módulo"
3. ✅ Coluna desaparece
4. Arraste "Job Name" para cima
5. ✅ Ordem muda
6. Recarregue página
7. ✅ Configuração persiste

### **Teste 4: Coluna Servidores**
1. Modo "Todos os Servidores"
2. Observe coluna "Servidores"
3. ✅ Cada tipo mostra seu servidor
4. ✅ Se houver tipo duplicado, mostrará múltiplos servidores

---

## 📁 **ARQUIVOS MODIFICADOS**

```
frontend/src/pages/MonitoringTypes.tsx (REESCRITO COMPLETAMENTE - 600 linhas)
├─ Import: Radio, Dropdown, ColumnSelector
├─ State: tableSize, columnConfig (NOVO)
├─ Radio.Group (substituiu Segmented)
├─ Space.Compact com controles
├─ Filtro dinâmico de colunas
└─ Persistência em localStorage

backend/api/monitoring_types_dynamic.py (SEM ALTERAÇÕES)
└─ 5 categorias já estavam implementadas corretamente
```

---

## 🎁 **BENEFÍCIOS**

### **UX Profissional:**
- ✅ Layout limpo e organizado
- ✅ Ícones visíveis e intuitivos
- ✅ Controles agrupados logicamente
- ✅ 100% consistente com PrometheusConfig

### **Funcionalidades Avançadas:**
- ✅ Densidade ajustável
- ✅ Colunas customizáveis
- ✅ Persistência automática
- ✅ Drag-and-drop

### **Performance:**
- ✅ Filtragem frontend (sem requests extras)
- ✅ Memoização

---

## 📚 **REFERÊNCIAS**

- **Padrão:** [frontend/src/pages/PrometheusConfig.tsx](../frontend/src/pages/PrometheusConfig.tsx) (linhas 2336-2358)
- **ColumnSelector:** [frontend/src/components/ColumnSelector.tsx](../frontend/src/components/ColumnSelector.tsx)
- **Backend API:** [backend/api/monitoring_types_dynamic.py](../backend/api/monitoring_types_dynamic.py)

---

## ✅ **CHECKLIST**

- [x] Substituir Segmented por Radio.Group
- [x] Adicionar controle de densidade
- [x] Adicionar ColumnSelector
- [x] Agrupar com Space.Compact
- [x] Corrigir coluna "Servidores"
- [x] Implementar filtro dinâmico de colunas
- [x] Persistência localStorage
- [x] Validar TypeScript
- [x] Revisar 5 categorias do backend
- [x] Atualizar documentação

---

**Status Final:** ✅ **Refatoração Completa com Sucesso!**
**Alinhamento:** 100% com padrão PrometheusConfig
**Qualidade:** Profissional e escalável
