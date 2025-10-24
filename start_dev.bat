@echo off
echo ========================================
echo   CONSUL MANAGER - Development Mode
echo ========================================
echo.

REM Start Backend
echo [1/2] Starting Backend API (port 5000)...
start cmd /k "cd backend && python app.py"

timeout /t 5 /nobreak > nul

REM Start Frontend (detecta porta automaticamente)
echo [2/2] Starting Frontend (port 8081)...
start cmd /k "cd frontend && npm run dev -- --port 8081"

echo.
echo ========================================
echo    Servers Started Successfully!
echo ========================================
echo Backend API: http://localhost:5000
echo Frontend:    http://localhost:8081
echo API Docs:    http://localhost:5000/docs
echo ========================================
pause