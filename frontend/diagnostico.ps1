# Script de Diagnóstico - Tela Branca
Write-Host "=== DIAGNÓSTICO DO FRONTEND ===" -ForegroundColor Cyan
Write-Host ""

# 1. Verificar se arquivos existem
Write-Host "1. Verificando arquivos criados..." -ForegroundColor Yellow
$arquivos = @(
    "src\pages\Dashboard.tsx",
    "src\pages\ServicePresets.tsx",
    "src\pages\BlackboxGroups.tsx",
    "src\pages\KVBrowser.tsx",
    "src\pages\AuditLog.tsx",
    "src\components\AdvancedSearchPanel.tsx",
    "src\components\ColumnSelector.tsx",
    "src\services\api.ts",
    "src\App.tsx",
    "src\main.tsx",
    "index.html"
)

foreach ($arquivo in $arquivos) {
    if (Test-Path $arquivo) {
        Write-Host "   ✓ $arquivo" -ForegroundColor Green
    } else {
        Write-Host "   ✗ $arquivo FALTANDO!" -ForegroundColor Red
    }
}

Write-Host ""

# 2. Verificar node_modules
Write-Host "2. Verificando pacotes críticos..." -ForegroundColor Yellow
$pacotes = @(
    "node_modules\@ant-design\charts",
    "node_modules\@dnd-kit\core",
    "node_modules\@dnd-kit\sortable",
    "node_modules\react",
    "node_modules\antd"
)

foreach ($pacote in $pacotes) {
    if (Test-Path $pacote) {
        Write-Host "   ✓ $pacote" -ForegroundColor Green
    } else {
        Write-Host "   ✗ $pacote FALTANDO!" -ForegroundColor Red
    }
}

Write-Host ""

# 3. Tentar compilar TypeScript
Write-Host "3. Verificando erros TypeScript..." -ForegroundColor Yellow
Write-Host "   Executando: npx tsc --noEmit" -ForegroundColor Gray
$tscOutput = npx tsc --noEmit 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "   ✓ Sem erros TypeScript!" -ForegroundColor Green
} else {
    Write-Host "   ✗ ERROS TypeScript encontrados:" -ForegroundColor Red
    Write-Host $tscOutput -ForegroundColor Red
}

Write-Host ""

# 4. Verificar processos nas portas
Write-Host "4. Verificando portas em uso..." -ForegroundColor Yellow
$portas = @(5000, 8081, 8082, 8083)
foreach ($porta in $portas) {
    $processo = netstat -ano | Select-String ":$porta " | Select-Object -First 1
    if ($processo) {
        Write-Host "   Porta $porta em uso: $processo" -ForegroundColor Cyan
    }
}

Write-Host ""

# 5. Verificar backend
Write-Host "5. Testando backend..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "http://localhost:5000/api/v1/services" -Method GET -TimeoutSec 3 -ErrorAction Stop
    Write-Host "   ✓ Backend respondendo na porta 5000!" -ForegroundColor Green
} catch {
    Write-Host "   ✗ Backend NÃO está respondendo!" -ForegroundColor Red
    Write-Host "   Inicie o backend: cd ..\backend && python app.py" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "=== FIM DO DIAGNÓSTICO ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "PRÓXIMOS PASSOS:" -ForegroundColor Yellow
Write-Host "1. Abra o navegador em http://localhost:8083 (ou porta que apareceu)" -ForegroundColor White
Write-Host "2. Pressione F12 para abrir DevTools" -ForegroundColor White
Write-Host "3. Vá na aba Console" -ForegroundColor White
Write-Host "4. Copie TODOS os erros vermelhos e envie" -ForegroundColor White
Write-Host ""
Write-Host "Se não houver erros no Console:" -ForegroundColor Yellow
Write-Host "- Vá na aba Network (Rede)" -ForegroundColor White
Write-Host "- Recarregue a página (Ctrl+R)" -ForegroundColor White
Write-Host "- Procure por arquivos com status 404 ou 500" -ForegroundColor White
Write-Host "- Tire um print e envie" -ForegroundColor White
