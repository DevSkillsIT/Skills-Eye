@echo off
REM ========================================
REM Script de Restart Completo
REM Consul Manager Web Application
REM ========================================

echo.
echo ========================================
echo  REINICIANDO CONSUL MANAGER
echo ========================================
echo.

echo [1/6] Parando processos Node.js...
taskkill /F /IM node.exe /T 2>nul
if %ERRORLEVEL% == 0 (
    echo   - Processos Node.js finalizados
) else (
    echo   - Nenhum processo Node.js ativo
)

echo.
echo [2/6] Parando processos Python...
taskkill /F /IM python.exe /T 2>nul
if %ERRORLEVEL% == 0 (
    echo   - Processos Python finalizados
) else (
    echo   - Nenhum processo Python ativo
)

echo.
echo [3/6] Limpando cache do Backend...
if exist "backend\__pycache__" (
    rmdir /S /Q "backend\__pycache__"
    echo   - __pycache__ removido
)
if exist "backend\api\__pycache__" (
    rmdir /S /Q "backend\api\__pycache__"
    echo   - api\__pycache__ removido
)
if exist "backend\core\__pycache__" (
    rmdir /S /Q "backend\core\__pycache__"
    echo   - core\__pycache__ removido
)
if exist "backend\core\installers\__pycache__" (
    rmdir /S /Q "backend\core\installers\__pycache__"
    echo   - installers\__pycache__ removido
)
echo   - Cache Python limpo!

echo.
echo [4/6] Limpando cache do Frontend...
if exist "frontend\node_modules\.vite" (
    rmdir /S /Q "frontend\node_modules\.vite"
    echo   - Vite cache removido
)
if exist "frontend\dist" (
    rmdir /S /Q "frontend\dist"
    echo   - Dist removido
)
echo   - Cache Frontend limpo!

echo.
echo [5/6] Aguardando 3 segundos...
timeout /t 3 /nobreak > nul

echo.
echo [6/6] Iniciando aplicacao...
echo.

echo Iniciando Backend (Python)...
start "Consul Manager - Backend" cmd /k "cd backend && python app.py"
timeout /t 2 /nobreak > nul

echo Iniciando Frontend (Node)...
start "Consul Manager - Frontend" cmd /k "cd frontend && npm run dev"

echo.
echo ========================================
echo  APLICACAO REINICIADA!
echo ========================================
echo.
echo Backend: http://localhost:5001
echo Frontend: http://localhost:8082
echo.
echo Pressione qualquer tecla para fechar...
pause > nul
