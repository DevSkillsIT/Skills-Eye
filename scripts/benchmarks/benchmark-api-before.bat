@echo off
REM ============================================
REM BENCHMARK API - ANTES DAS OTIMIZACOES
REM ============================================
echo.
echo ========================================
echo  BENCHMARK API - BASELINE (ANTES)
echo ========================================
echo.
echo Data/Hora: %date% %time%
echo.

REM Teste 1: Listar arquivos do servidor master
echo [1/5] GET /files - Servidor Master (.26)
curl -w "\nTempo: %%{time_total}s | Status: %%{http_code}\n" -o nul -s "http://localhost:5000/api/v1/prometheus-config/files"
echo.

REM Teste 2: Listar arquivos do servidor slave
echo [2/5] GET /files - Servidor Slave (RIO)
curl -w "\nTempo: %%{time_total}s | Status: %%{http_code}\n" -o nul -s "http://localhost:5000/api/v1/prometheus-config/files"
echo.

REM Teste 3: Listar jobs do prometheus.yml
echo [3/5] GET /jobs - prometheus.yml
curl -w "\nTempo: %%{time_total}s | Status: %%{http_code}\n" -o nul -s "http://localhost:5000/api/v1/prometheus-config/jobs?file_path=/etc/prometheus/prometheus.yml"
echo.

REM Teste 4: Testar concorrencia (3 requests simultaneos)
echo [4/5] TESTE DE CONCORRENCIA (3 requests simultaneos)
echo Requisicao 1 (files):
start /B curl -w "\nTempo: %%{time_total}s\n" -o nul -s "http://localhost:5000/api/v1/prometheus-config/files" ^>temp1.txt
echo Requisicao 2 (jobs):
start /B curl -w "\nTempo: %%{time_total}s\n" -o nul -s "http://localhost:5000/api/v1/prometheus-config/jobs?file_path=/etc/prometheus/prometheus.yml" ^>temp2.txt
echo Requisicao 3 (files novamente):
start /B curl -w "\nTempo: %%{time_total}s\n" -o nul -s "http://localhost:5000/api/v1/prometheus-config/files" ^>temp3.txt

REM Aguardar conclusao
timeout /t 5 /nobreak >nul

echo Resultado requisicao 1:
type temp1.txt 2>nul
echo Resultado requisicao 2:
type temp2.txt 2>nul
echo Resultado requisicao 3:
type temp3.txt 2>nul

del temp1.txt temp2.txt temp3.txt 2>nul
echo.

REM Teste 5: Sequencia completa (simula carregamento da pagina)
echo [5/5] SEQUENCIA COMPLETA (simula load inicial da pagina)
echo.
echo Passo 1: Buscar arquivos...
curl -w "  Tempo: %%{time_total}s\n" -o nul -s "http://localhost:5000/api/v1/prometheus-config/files"

echo Passo 2: Buscar jobs do prometheus.yml...
curl -w "  Tempo: %%{time_total}s\n" -o nul -s "http://localhost:5000/api/v1/prometheus-config/jobs?file_path=/etc/prometheus/prometheus.yml"

echo.
echo ========================================
echo  BENCHMARK CONCLUIDO
echo ========================================
echo.
echo Resultados salvos em: benchmark-results-before.txt
echo.

REM Salvar em arquivo
echo BENCHMARK API - BEFORE > benchmark-results-before.txt
echo Data: %date% %time% >> benchmark-results-before.txt
echo. >> benchmark-results-before.txt
pause
