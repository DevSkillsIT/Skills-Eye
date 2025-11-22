# Pendências frente ao relatório “CONSOLIDAÇÃO-ANÁLISES-IMPLEMENTAÇÃO-SPEC-PERF-002”

## 1. Falha arquitetural de paginação (item 1 do relatório)
- O back-end passou a aceitar o parâmetro `q` e expõe `/monitoring/summary`, porém o front não envia o termo de busca: `consulAPI.getMonitoringData` só propaga paginação, ordenação, filtros e nó (`frontend/src/services/api.ts`, linhas 900-944).
- A busca global continua filtrando apenas os registros carregados na página vigente (`frontend/src/pages/DynamicMonitoringPage.tsx`, linhas 947-972), portanto qualquer item fora da página atual continua “invisível”.
- As condições avançadas também seguem executando exclusivamente no cliente (`frontend/src/pages/DynamicMonitoringPage.tsx`, linhas 413-470), mantendo o mesmo problema citado no relatório (filtros só enxergam ≤50 itens por vez). Nenhuma parte do payload enviado ao back-end inclui `advancedConditions`.
- Resultado: embora o dashboard agora consuma `/monitoring/summary`, busca textual e filtros avançados ainda apresentam o comportamento incorreto descrito originalmente (precisam ir para o servidor).

## 2. Dropdown de filtro não aplica múltiplos valores (item 6)
- O front passou a aceitar múltiplas opções e envia `selectedKeys.join(',')` (`frontend/src/pages/DynamicMonitoringPage.tsx`, linhas 664-703), mas o servidor continua tratando cada filtro como igualdade estrita (`backend/core/monitoring_filters.py`, linhas 74-117). Não há split por vírgulas nem suporte a arrays.
- Assim, mesmo selecionando vários valores (ou “Selecionar todos”), o back-end só retornará registros cujo campo tenha exatamente o texto “valor1,valor2,…”, mantendo o bug relatado.

## 3. Exportação CSV parcial (item 10)
- `handleExport` ainda gera o CSV apenas a partir de `tableSnapshot`, que contém somente os registros carregados no ProTable na última requisição (`frontend/src/pages/DynamicMonitoringPage.tsx`, linhas 1129-1174). Não há chamada ao novo endpoint nem iteração sobre todas as páginas.
- Consequência: o usuário continua exportando, no máximo, os 50 itens visíveis, exatamente como apontado no relatório.

## 4. Batch delete limitado à página atual (item 11)
- O batch delete prepara o payload a partir de `selectedRows` do ProTable (`frontend/src/pages/DynamicMonitoringPage.tsx`, linhas 1107-1122). O componente de seleção continua operando apenas sobre as linhas renderizadas, portanto a ação “Remover selecionados” só considera os registros daquela página.
- O comportamento descrito no relatório (“Selecionar todos só marca os 50 atuais”) permanece.

## 5. Processamento server-side das buscas avan çadas
- O relatório exigia mover os filtros avançados/regex para o back-end. Mesmo com o parâmetro `search_query` disponível no servidor, nenhuma rota usa as condições avançadas e elas seguem degradando o front.
- Pendência associada: adaptar `process_monitoring_data`/`apply_advanced_filters` no back-end e enviar as condições a partir da tela (provavelmente via novo payload JSON em `/monitoring/data`).

> Obs.: Problemas tratados no relatório, como cache intermediário, ordenação descendente e renderização das colunas, foram validados após os commits `bdfa30a` e `a9f65bb` e não aparecem aqui.
