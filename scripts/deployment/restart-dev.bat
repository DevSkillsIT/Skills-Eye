@echo off
REM ========================================
REM Script de Restart AGRESSIVO
REM Consul Manager Web Application
REM ========================================

echo.
echo ==========================================
echo  RESTART DEV - LIMPEZA AGRESSIVA
echo ==========================================
echo.

REM ========================================
REM PASSO 1: MATAR TUDO 3 VEZES (garantir limpeza)
REM ========================================
echo [1/5] Matando TODOS os processos Python e Node (3x)...

REM Rodada 1
taskkill /F /IM python.exe /T >nul 2>&1
taskkill /F /IM node.exe /T >nul 2>&1

REM Aguardar 1s
timeout /t 1 /nobreak >nul

REM Rodada 2
taskkill /F /IM python.exe /T >nul 2>&1
taskkill /F /IM node.exe /T >nul 2>&1

REM Aguardar 1s
timeout /t 1 /nobreak >nul

REM Rodada 3 (matar por porta se ainda tiver algo)
for /f "tokens=5" %%a in ('netstat -ano 2^>nul ^| findstr ":5001" ^| findstr "LISTENING"') do taskkill /F /PID %%a >nul 2>&1
for /f "tokens=5" %%a in ('netstat -ano 2^>nul ^| findstr ":8082" ^| findstr "LISTENING"') do taskkill /F /PID %%a >nul 2>&1

echo   - Limpeza agressiva concluida

REM ========================================
REM PASSO 2: LIMPAR CACHE (paralelo)
REM ========================================
echo.
echo [2/5] Limpando cache Python e Vite...
if exist "backend\__pycache__" rmdir /S /Q "backend\__pycache__" 2>nul
if exist "backend\api\__pycache__" rmdir /S /Q "backend\api\__pycache__" 2>nul
if exist "backend\core\__pycache__" rmdir /S /Q "backend\core\__pycache__" 2>nul
if exist "backend\core\installers\__pycache__" rmdir /S /Q "backend\core\installers\__pycache__" 2>nul
if exist "frontend\node_modules\.vite" rmdir /S /Q "frontend\node_modules\.vite" 2>nul
if exist "frontend\dist" rmdir /S /Q "frontend\dist" 2>nul
echo   - Cache limpo

REM ========================================
REM PASSO 3: INICIAR BACKEND (minimizado)
REM ========================================
echo.
echo [3/5] Iniciando Backend (porta 5001)...
start /MIN "" powershell -NoExit -Command "cd c:\consul-manager-web\backend; python app.py"
timeout /t 3 /nobreak >nul
echo   - Backend iniciado

REM ========================================
REM PASSO 4: INICIAR FRONTEND (minimizado)
REM ========================================
echo.
echo [4/5] Iniciando Frontend (porta 8082)...
start /MIN "" powershell -NoExit -Command "cd c:\consul-manager-web\frontend; npm run dev"
timeout /t 3 /nobreak >nul
echo   - Frontend iniciado

REM ========================================
REM PASSO 5: VERIFICACAO FINAL
REM ========================================
echo.
echo [5/5] Verificando portas (aguarde 4s)...
timeout /t 4 /nobreak >nul

netstat -ano 2>nul | findstr ":5001" | findstr "LISTENING" >nul
if %ERRORLEVEL% == 0 (
    echo   [OK] Backend em http://localhost:5001
) else (
    echo   [AVISO] Backend pode ainda estar subindo...
)

netstat -ano 2>nul | findstr ":8082" | findstr "LISTENING" >nul
if %ERRORLEVEL% == 0 (
    echo   [OK] Frontend em http://localhost:8082
) else (
    echo   [AVISO] Frontend pode ainda estar subindo...
)

echo.
echo ==========================================
echo  RESTART CONCLUIDO (10s total)
echo ==========================================
echo.
echo Backend:  http://localhost:5001
echo Frontend: http://localhost:8082
echo.
echo Janelas minimizadas criadas.
echo Para fechar tudo: taskkill /F /IM python.exe /T ^&^& taskkill /F /IM node.exe /T
echo.
