# Padronização de Layout - Páginas de Listagem

## Resumo

Todas as três páginas de listagem (Services, BlackboxTargets e Exporters) agora seguem o MESMO padrão de layout.

---

## Estrutura Padronizada

Todas as páginas agora têm esta estrutura:

```
PageContainer (header simples, sem botões no extra)
  Space direction="vertical" size="middle"

    1️⃣ Card - SUMMARY/ESTATÍSTICAS
       Space size="large" wrap
         - Estatísticas em linha (com ícones e cores)

    2️⃣ Card size="small" - FILTROS E AÇÕES
       Space direction="vertical" size="middle"

         Space wrap (Linha 1)
           - MetadataFilterBar (com nodeSelector no extra)

         Space wrap (Linha 2)
           - Search (busca por nome)
           - Botão "Busca Avançada"
           - Botão "Limpar Filtros Avançados" (condicional)
           - ColumnSelector
           - Botão "Exportar CSV"
           - Botão "Atualizar"
           - Botão "Remover selecionados" (com Popconfirm)
           - Botões específicos (Novo, Importar, Config, etc.)

         AdvancedSearchPanel (condicional, se advancedOpen)

    3️⃣ ProTable
       - Com rowSelection
       - Com expandable (meta)
       - Com pagination padrão
       - Sem toolBarRender (tudo está no Card de filtros)
```

---

## Comparação: ANTES vs DEPOIS

### ❌ ANTES (Inconsistente)

**Services:**
- Botões no `extra` do PageContainer
- Cards de estatísticas soltos
- MetadataFilterBar solto
- Sem padrão visual

**BlackboxTargets:**
- Botões no `extra` do PageContainer
- Cards de estatísticas soltos
- MetadataFilterBar solto
- `toolBarRender` na tabela para "Remover selecionados"

**Exporters:**
- Já tinha o layout novo (estrutura em Cards)

### ✅ DEPOIS (Padronizado)

Todas as 3 páginas seguem EXATAMENTE o mesmo layout:
1. Card de estatísticas no topo
2. Card de filtros e ações no meio
3. Tabela embaixo

---

## Mudanças Específicas por Página

### Services (frontend/src/pages/Services.tsx)

✅ **Removido:** Botões do `extra` do PageContainer

✅ **Adicionado:**
- Card de estatísticas com ícone e cor
- Card de filtros com estrutura em duas linhas (Space wrap)
- AdvancedSearchPanel embutido no card de filtros
- Contagem de selecionados no botão "Remover selecionados (X)"
- Texto padronizado: "Busca Avançada", "Limpar Filtros Avançados"
- `advancedSearchFields` para o AdvancedSearchPanel

✅ **Layout final:**
```tsx
<PageContainer> (sem extra)
  <Space vertical>
    <Card> Estatísticas </Card>
    <Card size="small">
      <Space vertical>
        <Space wrap> MetadataFilterBar + nodeSelector </Space>
        <Space wrap>
          Search + Busca Avançada + Limpar + ColumnSelector +
          Exportar CSV + Atualizar + Remover selecionados + Novo serviço
        </Space>
        {advancedOpen && <AdvancedSearchPanel />}
      </Space>
    </Card>
    <ProTable />
  </Space>
</PageContainer>
```

---

### BlackboxTargets (frontend/src/pages/BlackboxTargets.tsx)

✅ **Removido:**
- Botões do `extra` do PageContainer
- `toolBarRender` da ProTable

✅ **Adicionado:**
- Card de estatísticas com ícone e cor
- Card de filtros com estrutura em duas linhas (Space wrap)
- Botão "Atualizar" (estava faltando!)
- AdvancedSearchPanel embutido no card de filtros
- Contagem de selecionados no botão "Remover selecionados (X)"
- Texto padronizado: "Busca Avançada", "Limpar Filtros Avançados"
- `advancedSearchFields` para o AdvancedSearchPanel
- `options` e `scroll` na ProTable

✅ **Layout final:**
```tsx
<PageContainer> (sem extra)
  <Space vertical>
    <Card> Estatísticas </Card>
    <Card size="small">
      <Space vertical>
        <Space wrap> MetadataFilterBar + nodeSelector </Space>
        <Space wrap>
          Search + Busca Avançada + Limpar + ColumnSelector +
          Exportar CSV + Atualizar + Remover selecionados +
          Importar + Configuracoes + Novo alvo
        </Space>
        {advancedOpen && <AdvancedSearchPanel />}
      </Space>
    </Card>
    <ProTable />
  </Space>
</PageContainer>
```

---

### Exporters (frontend/src/pages/Exporters.tsx)

✅ **Já estava padronizado** (foi usado como referência)

✅ **Pequenas melhorias:**
- Contagem de selecionados no botão "Remover selecionados (X)"
- Logs de debug detalhados para investigar problema de resultados vazios

---

## Elementos Comuns em Todas as Páginas

### 1. Card de Estatísticas

```tsx
<Card>
  <Space size="large" wrap>
    <Statistic
      title="..."
      value={...}
      prefix={<IconOutlined />}
      valueStyle={{ color: '#3f8600' }}
    />
    {/* Mais estatísticas */}
  </Space>
</Card>
```

### 2. Card de Filtros (Linha 1)

```tsx
<Space wrap>
  <MetadataFilterBar
    value={filters}
    options={metadataOptions}
    onChange={setFilters}
    onReset={() => {...}}
    extra={nodeSelector}  // Seletor de nós
  />
</Space>
```

### 3. Card de Filtros (Linha 2)

```tsx
<Space wrap>
  <Search ... enterButton style={{ width: 300 }} />

  <Button icon={<FilterOutlined />}>
    Busca Avancada {count && `(${count})`}
  </Button>

  {conditions.length > 0 && (
    <Button icon={<ClearOutlined />}>
      Limpar Filtros Avancados
    </Button>
  )}

  <ColumnSelector ... />

  <Button icon={<DownloadOutlined />}>
    Exportar CSV
  </Button>

  <Button icon={<ReloadOutlined />}>
    Atualizar
  </Button>

  <Popconfirm ...>
    <Button danger icon={<DeleteOutlined />}>
      Remover selecionados ({count})
    </Button>
  </Popconfirm>

  {/* Botões específicos da página */}
  <Button type="primary" icon={<PlusOutlined />}>
    Novo ...
  </Button>
</Space>
```

### 4. AdvancedSearchPanel (Condicional)

```tsx
{advancedOpen && (
  <AdvancedSearchPanel
    availableFields={advancedSearchFields}
    onSearch={handleAdvancedSearch}
    onClear={handleAdvancedClear}
    initialConditions={advancedConditions}
    initialLogicalOperator={advancedLogicalOperator}
  />
)}
```

### 5. ProTable Padrão

```tsx
<ProTable
  rowKey="key"
  columns={visibleColumns}
  search={false}
  actionRef={actionRef}
  request={requestHandler}
  params={{ keyword: searchValue }}
  rowSelection={{...}}
  pagination={{
    defaultPageSize: 20,
    showSizeChanger: true,
    pageSizeOptions: ['10', '20', '30', '50', '100'],
  }}
  locale={{ emptyText: '...' }}
  options={{ density: true, fullScreen: true, reload: false, setting: false }}
  scroll={{ x: 1400 }}
  expandable={{...}}
/>
```

---

## Benefícios da Padronização

1. ✅ **Consistência Visual**: Todas as páginas têm a mesma aparência
2. ✅ **Manutenção Fácil**: Estrutura uniforme facilita updates
3. ✅ **UX Melhorada**: Usuário sabe onde encontrar as funções
4. ✅ **Menos Código Duplicado**: Padrão reutilizável
5. ✅ **Componentes Compartilhados**: MetadataFilterBar, ColumnSelector, AdvancedSearchPanel

---

## Checklist de Padronização ✅

| Feature | Services | BlackboxTargets | Exporters |
|---------|----------|-----------------|-----------|
| Card de Estatísticas | ✅ | ✅ | ✅ |
| Card de Filtros (2 linhas) | ✅ | ✅ | ✅ |
| Search com enterButton | ✅ | ✅ | ✅ |
| Busca Avançada com contador | ✅ | ✅ | ✅ |
| Limpar Filtros Avançados | ✅ | ✅ | ✅ |
| ColumnSelector | ✅ | ✅ | ✅ |
| Exportar CSV | ✅ | ✅ | ✅ |
| Atualizar | ✅ | ✅ | ✅ |
| Remover selecionados (com contador) | ✅ | ✅ | ✅ |
| AdvancedSearchPanel embutido | ✅ | ✅ | ✅ |
| Sem botões no header extra | ✅ | ✅ | ✅ |
| Sem toolBarRender | ✅ | ✅ | ✅ |

---

## Página Hosts - Melhorias

Adicionado card de resumo rápido no topo mostrando:
- **Uso de Memória** (com % e progress bar colorida)
- **Uso de Disco** (com % e progress bar colorida)
- **CPU Cores** (número de núcleos)
- **Tempo Ativo** (uptime em dias)

Layout mais visual e informativo, mantendo todos os cards detalhados existentes.

---

## Arquivos Modificados

1. ✅ `frontend/src/pages/Services.tsx` - Layout padronizado
2. ✅ `frontend/src/pages/BlackboxTargets.tsx` - Layout padronizado
3. ✅ `frontend/src/pages/Exporters.tsx` - Mantido como referência
4. ✅ `frontend/src/pages/Hosts.tsx` - Card de resumo rápido adicionado

---

## Próximos Passos

1. **Testar visualmente** as três páginas para confirmar consistência
2. **Resolver problema do Exporters** (não retorna resultados) - logs de debug ativados
3. **Verificar responsividade** em diferentes resoluções
