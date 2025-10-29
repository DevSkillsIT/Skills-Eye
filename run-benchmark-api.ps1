Write-Host "=== BENCHMARK API - BASELINE (ANTES) ===" -ForegroundColor Cyan
Write-Host ""

# Teste 1: GET /files (3 tentativas)
Write-Host "[1/3] GET /files (medir latencia)" -ForegroundColor Yellow
$times1 = @()
1..3 | ForEach-Object {
    $tentativa = $_
    $sw = [Diagnostics.Stopwatch]::StartNew()
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:5000/api/v1/prometheus-config/files" -UseBasicParsing -ErrorAction Stop
        $sw.Stop()
        $ms = $sw.ElapsedMilliseconds
        $times1 += $ms
        Write-Host "  Tentativa ${tentativa}: $($response.StatusCode) - $ms ms" -ForegroundColor Green
    } catch {
        $sw.Stop()
        $erro = $_.Exception.Message
        Write-Host "  Tentativa ${tentativa}: ERRO - $erro" -ForegroundColor Red
    }
}
$avg1 = ($times1 | Measure-Object -Average).Average
Write-Host "  Media: $([math]::Round($avg1, 2)) ms" -ForegroundColor Cyan
Write-Host ""

# Teste 2: GET /jobs
Write-Host "[2/3] GET /jobs prometheus.yml (medir latencia)" -ForegroundColor Yellow
$times2 = @()
1..3 | ForEach-Object {
    $tentativa = $_
    $sw = [Diagnostics.Stopwatch]::StartNew()
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:5000/api/v1/prometheus-config/jobs?file_path=/etc/prometheus/prometheus.yml" -UseBasicParsing -ErrorAction Stop
        $sw.Stop()
        $ms = $sw.ElapsedMilliseconds
        $times2 += $ms
        Write-Host "  Tentativa ${tentativa}: $($response.StatusCode) - $ms ms" -ForegroundColor Green
    } catch {
        $sw.Stop()
        $erro = $_.Exception.Message
        Write-Host "  Tentativa ${tentativa}: ERRO - $erro" -ForegroundColor Red
    }
}
$avg2 = ($times2 | Measure-Object -Average).Average
Write-Host "  Media: $([math]::Round($avg2, 2)) ms" -ForegroundColor Cyan
Write-Host ""

# Teste 3: Sequencia completa (simula load da pagina)
Write-Host "[3/3] SEQUENCIA COMPLETA (files + jobs)" -ForegroundColor Yellow
$swTotal = [Diagnostics.Stopwatch]::StartNew()

Write-Host "  Passo 1: Buscar arquivos..."
$sw = [Diagnostics.Stopwatch]::StartNew()
$r1 = Invoke-WebRequest -Uri "http://localhost:5000/api/v1/prometheus-config/files" -UseBasicParsing
$sw.Stop()
Write-Host "    -> $($sw.ElapsedMilliseconds) ms" -ForegroundColor Gray

Write-Host "  Passo 2: Buscar jobs..."
$sw = [Diagnostics.Stopwatch]::StartNew()
$r2 = Invoke-WebRequest -Uri "http://localhost:5000/api/v1/prometheus-config/jobs?file_path=/etc/prometheus/prometheus.yml" -UseBasicParsing
$sw.Stop()
Write-Host "    -> $($sw.ElapsedMilliseconds) ms" -ForegroundColor Gray

$swTotal.Stop()
Write-Host "  TOTAL: $($swTotal.ElapsedMilliseconds) ms" -ForegroundColor Cyan
Write-Host ""

# Resumo
Write-Host "========================================" -ForegroundColor Cyan
Write-Host " RESUMO" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "GET /files (media):        $([math]::Round($avg1, 2)) ms" -ForegroundColor White
Write-Host "GET /jobs (media):         $([math]::Round($avg2, 2)) ms" -ForegroundColor White
Write-Host "Load completo (files+jobs): $($swTotal.ElapsedMilliseconds) ms" -ForegroundColor White
Write-Host ""
Write-Host "Salvar estes dados para comparacao DEPOIS das otimizacoes!" -ForegroundColor Yellow
Write-Host ""
