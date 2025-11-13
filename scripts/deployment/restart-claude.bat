@echo off
REM ========================================
REM RESTART SCRIPT - Para Claude executar
REM ========================================

echo.
echo [1/5] Matando processos...
taskkill /F /IM python.exe /T >nul 2>&1
taskkill /F /IM node.exe /T >nul 2>&1
timeout /t 2 /nobreak >nul

echo [2/5] Limpando cache...
if exist "backend\__pycache__" rmdir /S /Q "backend\__pycache__" 2>nul
if exist "backend\api\__pycache__" rmdir /S /Q "backend\api\__pycache__" 2>nul
if exist "backend\core\__pycache__" rmdir /S /Q "backend\core\__pycache__" 2>nul
if exist "frontend\node_modules\.vite" rmdir /S /Q "frontend\node_modules\.vite" 2>nul

echo [3/5] Iniciando Backend...
start /B /MIN cmd /c "cd backend && python app.py > NUL 2>&1"
timeout /t 3 /nobreak >nul

echo [4/5] Iniciando Frontend...
start /B /MIN cmd /c "cd frontend && npm run dev > NUL 2>&1"
timeout /t 5 /nobreak >nul

echo [5/5] Verificando...
netstat -ano 2>nul | findstr ":5000" | findstr "LISTENING" >nul && echo Backend OK || echo Backend ERRO
netstat -ano 2>nul | findstr ":8081" | findstr "LISTENING" >nul && echo Frontend OK || echo Frontend ERRO

echo.
echo CONCLUIDO!
