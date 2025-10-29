# ============================================
# BENCHMARK FRONTEND - ANTES DAS OTIMIZACOES
# ============================================

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host " BENCHMARK FRONTEND - BASELINE (ANTES)" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Data/Hora: $(Get-Date)" -ForegroundColor Yellow
Write-Host ""

# Funcao para medir requests HTTP
function Get-NetworkRequests {
    param([string]$Url)

    Write-Host "Abrindo DevTools para monitorar requests..." -ForegroundColor Yellow
    Write-Host ""
    Write-Host "INSTRUCOES:" -ForegroundColor Green
    Write-Host "1. Abra o Chrome DevTools (F12)" -ForegroundColor White
    Write-Host "2. Va na aba Network" -ForegroundColor White
    Write-Host "3. Acesse: $Url" -ForegroundColor White
    Write-Host "4. Aguarde o carregamento completo" -ForegroundColor White
    Write-Host "5. Anote os seguintes dados:" -ForegroundColor White
    Write-Host ""
    Write-Host "   - Numero total de requests:" -ForegroundColor Cyan
    Write-Host "   - Requests para /api/v1/prometheus-config/files:" -ForegroundColor Cyan
    Write-Host "   - Requests para /api/v1/prometheus-config/jobs:" -ForegroundColor Cyan
    Write-Host "   - Tempo ate DOMContentLoaded:" -ForegroundColor Cyan
    Write-Host "   - Tempo ate Load completo:" -ForegroundColor Cyan
    Write-Host "   - Tamanho total transferido:" -ForegroundColor Cyan
    Write-Host ""
}

# Teste 1: Carregamento inicial
Write-Host "[1/4] TESTE: Carregamento inicial da pagina" -ForegroundColor Green
Write-Host "================================================" -ForegroundColor Gray
Get-NetworkRequests "http://localhost:8081/prometheus-config"
Write-Host ""
Read-Host "Pressione ENTER quando terminar a medicao"
Write-Host ""

# Teste 2: Troca de servidor
Write-Host "[2/4] TESTE: Troca de servidor (Master -> Slave)" -ForegroundColor Green
Write-Host "================================================" -ForegroundColor Gray
Write-Host "INSTRUCOES:" -ForegroundColor Yellow
Write-Host "1. Na pagina ja carregada, abra o seletor de servidor" -ForegroundColor White
Write-Host "2. Troque de Master (.26) para Slave (RIO)" -ForegroundColor White
Write-Host "3. Anote quantos requests foram disparados" -ForegroundColor White
Write-Host "4. Anote o tempo ate a lista de arquivos atualizar" -ForegroundColor White
Write-Host ""
Read-Host "Pressione ENTER quando terminar a medicao"
Write-Host ""

# Teste 3: Re-renders (Console)
Write-Host "[3/4] TESTE: Contagem de re-renders" -ForegroundColor Green
Write-Host "================================================" -ForegroundColor Gray
Write-Host "INSTRUCOES:" -ForegroundColor Yellow
Write-Host "1. Abra o Console do DevTools" -ForegroundColor White
Write-Host "2. Digite: " -ForegroundColor White
Write-Host '   let renderCount = 0;' -ForegroundColor Cyan
Write-Host '   const originalRender = React.Component.prototype.render;' -ForegroundColor Cyan
Write-Host '   React.Component.prototype.render = function() {' -ForegroundColor Cyan
Write-Host '     renderCount++;' -ForegroundColor Cyan
Write-Host '     console.log("Render:", renderCount);' -ForegroundColor Cyan
Write-Host '     return originalRender.apply(this, arguments);' -ForegroundColor Cyan
Write-Host '   };' -ForegroundColor Cyan
Write-Host ""
Write-Host "3. Recarregue a pagina e conte quantos 'Render:' aparecem" -ForegroundColor White
Write-Host "4. Anote o numero total de renders ate a pagina ficar interativa" -ForegroundColor White
Write-Host ""
Read-Host "Pressione ENTER quando terminar a medicao"
Write-Host ""

# Teste 4: Memoria
Write-Host "[4/4] TESTE: Uso de memoria" -ForegroundColor Green
Write-Host "================================================" -ForegroundColor Gray
Write-Host "INSTRUCOES:" -ForegroundColor Yellow
Write-Host "1. Abra DevTools -> Memory (ou Performance)" -ForegroundColor White
Write-Host "2. Tire um Heap Snapshot ANTES de qualquer acao" -ForegroundColor White
Write-Host "3. Execute as seguintes acoes:" -ForegroundColor White
Write-Host "   - Carregue a pagina" -ForegroundColor Cyan
Write-Host "   - Troque de servidor 3 vezes" -ForegroundColor Cyan
Write-Host "   - Abra e feche o Monaco Editor" -ForegroundColor Cyan
Write-Host "4. Tire outro Heap Snapshot DEPOIS" -ForegroundColor White
Write-Host "5. Compare o tamanho (procure por memory leaks)" -ForegroundColor White
Write-Host ""
Read-Host "Pressione ENTER quando terminar a medicao"
Write-Host ""

# Resultados
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host " BENCHMARK CONCLUIDO" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Anote os resultados em: benchmark-results-before.txt" -ForegroundColor Yellow
Write-Host ""

# Template para resultados
$template = @"
========================================
BENCHMARK FRONTEND - BEFORE (BASELINE)
========================================
Data: $(Get-Date)

[1] CARREGAMENTO INICIAL
- Total de requests HTTP: _____
- Requests para /files: _____
- Requests para /jobs: _____
- Tempo ate DOMContentLoaded: _____ ms
- Tempo ate Load completo: _____ ms
- Tamanho transferido: _____ KB

[2] TROCA DE SERVIDOR
- Requests disparados: _____
- Tempo ate atualizar lista: _____ ms

[3] RE-RENDERS
- Total de renders ate interativo: _____

[4] MEMORIA
- Heap size ANTES: _____ MB
- Heap size DEPOIS: _____ MB
- Diferenca (leak?): _____ MB

OBSERVACOES:
- _____________________
- _____________________

"@

$template | Out-File -FilePath "benchmark-results-before.txt" -Encoding UTF8
Write-Host "Template de resultados criado em: benchmark-results-before.txt" -ForegroundColor Green
Write-Host "Preencha os valores medidos!" -ForegroundColor Yellow
Write-Host ""
