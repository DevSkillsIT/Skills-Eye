# ========================================
# Script de Restart Completo (PowerShell)
# Consul Manager Web Application
# ========================================

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host " REINICIANDO CONSUL MANAGER" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# [1/6] Parar processos Node.js
Write-Host "[1/6] Parando processos Node.js..." -ForegroundColor Yellow
$nodeProcesses = Get-Process -Name node -ErrorAction SilentlyContinue
if ($nodeProcesses) {
    $nodeProcesses | Stop-Process -Force
    Write-Host "  - $($nodeProcesses.Count) processo(s) Node.js finalizados" -ForegroundColor Green
} else {
    Write-Host "  - Nenhum processo Node.js ativo" -ForegroundColor Gray
}

# [2/6] Parar processos Python
Write-Host ""
Write-Host "[2/6] Parando processos Python..." -ForegroundColor Yellow
$pythonProcesses = Get-Process -Name python -ErrorAction SilentlyContinue
if ($pythonProcesses) {
    $pythonProcesses | Stop-Process -Force
    Write-Host "  - $($pythonProcesses.Count) processo(s) Python finalizados" -ForegroundColor Green
} else {
    Write-Host "  - Nenhum processo Python ativo" -ForegroundColor Gray
}

# [3/6] Limpar cache do Backend
Write-Host ""
Write-Host "[3/6] Limpando cache do Backend..." -ForegroundColor Yellow
$cacheDirs = @(
    "backend\__pycache__",
    "backend\api\__pycache__",
    "backend\core\__pycache__",
    "backend\core\installers\__pycache__"
)

foreach ($dir in $cacheDirs) {
    if (Test-Path $dir) {
        Remove-Item -Path $dir -Recurse -Force -ErrorAction SilentlyContinue
        Write-Host "  - $dir removido" -ForegroundColor Green
    }
}
Write-Host "  - Cache Python limpo!" -ForegroundColor Green

# [4/6] Limpar cache do Frontend
Write-Host ""
Write-Host "[4/6] Limpando cache do Frontend..." -ForegroundColor Yellow
$frontendCache = @(
    "frontend\node_modules\.vite",
    "frontend\dist"
)

foreach ($dir in $frontendCache) {
    if (Test-Path $dir) {
        Remove-Item -Path $dir -Recurse -Force -ErrorAction SilentlyContinue
        Write-Host "  - $dir removido" -ForegroundColor Green
    }
}
Write-Host "  - Cache Frontend limpo!" -ForegroundColor Green

# [5/6] Aguardar
Write-Host ""
Write-Host "[5/6] Aguardando 3 segundos..." -ForegroundColor Yellow
Start-Sleep -Seconds 3

# [6/6] Iniciar aplicação
Write-Host ""
Write-Host "[6/6] Iniciando aplicacao..." -ForegroundColor Yellow
Write-Host ""

# Iniciar Backend
Write-Host "Iniciando Backend (Python)..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd backend; python app.py" -WindowStyle Normal
Start-Sleep -Seconds 2

# Iniciar Frontend
Write-Host "Iniciando Frontend (Node)..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd frontend; npm run dev" -WindowStyle Normal

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host " APLICACAO REINICIADA!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Backend:  http://localhost:5000" -ForegroundColor White
Write-Host "Frontend: http://localhost:8081" -ForegroundColor White
Write-Host ""
Write-Host "Pressione qualquer tecla para fechar..." -ForegroundColor Gray
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
