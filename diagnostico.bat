@echo off
REM ========================================
REM Script de Diagnóstico - Consul Manager
REM ========================================

echo.
echo ========================================
echo  DIAGNOSTICO CONSUL MANAGER
echo ========================================
echo.

echo [1/8] Verificando Python...
python --version 2>nul
if %ERRORLEVEL% == 0 (
    echo   ✓ Python instalado
) else (
    echo   ✗ Python NAO encontrado - INSTALE PYTHON 3.12+
    goto :ERROR
)

echo.
echo [2/8] Verificando Node.js...
node --version 2>nul
if %ERRORLEVEL% == 0 (
    echo   ✓ Node.js instalado
) else (
    echo   ✗ Node.js NAO encontrado - INSTALE NODE.JS
    goto :ERROR
)

echo.
echo [3/8] Verificando venv do Backend...
if exist "backend\venv\Scripts\activate.bat" (
    echo   ✓ Virtual environment existe
) else (
    echo   ✗ Virtual environment NAO existe
    echo   Criando venv...
    cd backend
    python -m venv venv
    cd ..
    echo   ✓ venv criado
)

echo.
echo [4/8] Verificando dependencias Python...
if exist "backend\venv\Lib\site-packages\fastapi" (
    echo   ✓ Dependencias Python instaladas
) else (
    echo   ✗ Dependencias Python NAO instaladas
    echo   Instalando dependencias...
    cd backend
    call venv\Scripts\activate.bat
    pip install -r requirements.txt
    cd ..
    echo   ✓ Dependencias instaladas
)

echo.
echo [5/8] Verificando node_modules do Frontend...
if exist "frontend\node_modules" (
    echo   ✓ node_modules existe
) else (
    echo   ✗ node_modules NAO existe
    echo   Instalando dependencias...
    cd frontend
    npm install
    cd ..
    echo   ✓ Dependencias instaladas
)

echo.
echo [6/8] Verificando arquivo .env do Backend...
if exist "backend\.env" (
    echo   ✓ Arquivo .env existe
    echo.
    echo   Configuracoes principais:
    findstr /C:"CONSUL_HOST" /C:"CONSUL_PORT" /C:"API_PORT" /C:"CORS_ALLOW_ALL" backend\.env
) else (
    echo   ✗ Arquivo .env NAO existe - CRIE O ARQUIVO .env
    goto :ERROR
)

echo.
echo [7/8] Testando conectividade com Consul...
curl -s -o nul -w "%%{http_code}" http://172.16.1.26:8500/v1/status/leader 2>nul | findstr "200" >nul
if %ERRORLEVEL% == 0 (
    echo   ✓ Consul acessivel em 172.16.1.26:8500
) else (
    echo   ⚠ Consul NAO acessivel - Verifique rede/firewall
)

echo.
echo [8/8] Verificando portas 5000 e 8081...
netstat -ano | findstr :5000 | findstr LISTENING >nul
if %ERRORLEVEL% == 0 (
    echo   ⚠ Porta 5000 JA em uso
) else (
    echo   ✓ Porta 5000 livre
)

netstat -ano | findstr :8081 | findstr LISTENING >nul
if %ERRORLEVEL% == 0 (
    echo   ⚠ Porta 8081 JA em uso
) else (
    echo   ✓ Porta 8081 livre
)

echo.
echo ========================================
echo  DIAGNOSTICO CONCLUIDO - TUDO OK!
echo ========================================
echo.
echo Agora execute: restart-app.bat
echo.
goto :END

:ERROR
echo.
echo ========================================
echo  DIAGNOSTICO FALHOU - CORRIJA OS ERROS
echo ========================================
echo.

:END
pause
