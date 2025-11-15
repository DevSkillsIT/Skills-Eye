@echo off
REM ========================================
REM Script de Restart com DEBUG
REM Consul Manager Web Application
REM ========================================

echo.
echo ========================================
echo  REINICIANDO CONSUL MANAGER (DEBUG)
echo ========================================
echo.

echo [1/7] Parando processos Node.js...
taskkill /F /IM node.exe /T 2>nul
if %ERRORLEVEL% == 0 (
    echo   - Processos Node.js finalizados
) else (
    echo   - Nenhum processo Node.js ativo
)

echo.
echo [2/7] Parando processos Python...
taskkill /F /IM python.exe /T 2>nul
if %ERRORLEVEL% == 0 (
    echo   - Processos Python finalizados
) else (
    echo   - Nenhum processo Python ativo
)

echo.
echo [3/7] Limpando cache do Backend...
if exist "backend\__pycache__" rmdir /S /Q "backend\__pycache__"
if exist "backend\api\__pycache__" rmdir /S /Q "backend\api\__pycache__"
if exist "backend\core\__pycache__" rmdir /S /Q "backend\core\__pycache__"
if exist "backend\core\installers\__pycache__" rmdir /S /Q "backend\core\installers\__pycache__"
echo   - Cache Python limpo!

echo.
echo [4/7] Limpando cache do Frontend...
if exist "frontend\node_modules\.vite" rmdir /S /Q "frontend\node_modules\.vite"
if exist "frontend\dist" rmdir /S /Q "frontend\dist"
echo   - Cache Frontend limpo!

echo.
echo [5/7] Aguardando 2 segundos...
timeout /t 2 /nobreak > nul

echo.
echo [6/7] Iniciando Backend (Python) com DEBUG...
echo.
echo ========================================
echo TENTANDO INICIAR BACKEND...
echo ========================================
echo.

REM Tentar iniciar backend e capturar erros
cd backend

REM Verificar se venv existe
if not exist "venv\Scripts\activate.bat" (
    echo ✗ ERRO: Virtual environment nao encontrado!
    echo Execute: cd backend ^&^& python -m venv venv ^&^& venv\Scripts\activate ^&^& pip install -r requirements.txt
    pause
    exit /b 1
)

REM Ativar venv e iniciar
echo Ativando virtual environment...
call venv\Scripts\activate.bat

echo.
echo Iniciando app.py...
echo Se aparecer erros abaixo, corrija-os antes de continuar.
echo.
echo ----------------------------------------

REM Tentar iniciar Python - se falhar, mostra erro e pausa
python app.py
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ✗ BACKEND FALHOU AO INICIAR!
    echo Verifique os erros acima.
    pause
    exit /b 1
)

cd ..

REM Se chegou aqui, backend iniciou com sucesso
REM Agora iniciar frontend em nova janela

echo.
echo [7/7] Iniciando Frontend (Node) em nova janela...
start "Consul Manager - Frontend" cmd /k "cd /d \"%~dp0frontend\" && npm run dev"

echo.
echo ========================================
echo  APLICACAO INICIADA (MODO DEBUG)
echo ========================================
echo.
echo Backend rodando nesta janela
echo Frontend rodando em janela separada
echo.
echo Backend: http://localhost:5000
echo Frontend: http://localhost:8081
echo.
echo Mantenha esta janela aberta para ver logs do backend!
echo.

REM Manter janela aberta
pause
