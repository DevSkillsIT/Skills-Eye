"""
Captura console.logs do browser para diagnosticar re-renders
"""
from playwright.sync_api import sync_playwright
import time

FRONTEND_URL = "http://localhost:8081"

def capture_console_logs():
    """
    Abre Services e captura TODOS os console.logs
    """
    print("=" * 80)
    print("CAPTURANDO CONSOLE.LOGS - Services Page")
    print("=" * 80)
    print()

    with sync_playwright() as p:
        # Abrir browser visível (headless=False) para debug
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={'width': 1920, 'height': 1080})
        page = context.new_page()

        # Capturar console.logs
        console_logs = []

        def handle_console(msg):
            # Filtrar apenas logs de RENDER e PERF
            text = msg.text
            if '[RENDER' in text or '[PERF]' in text:
                console_logs.append({
                    'time': time.time(),
                    'text': text,
                    'type': msg.type
                })
                print(text)

        page.on("console", handle_console)

        # Navegar para Services
        print("Navegando para /services...")
        start_time = time.time()
        page.goto(f"{FRONTEND_URL}/services")

        # Aguardar dados aparecerem
        print("Aguardando dados aparecerem...")
        try:
            page.wait_for_selector("tbody tr.ant-table-row td", timeout=30000)
            elapsed = (time.time() - start_time) * 1000
            print(f"\nDados apareceram em {elapsed:.0f}ms\n")
        except Exception as e:
            print(f"ERRO: {e}")

        # Aguardar mais um pouco para capturar todos os logs
        time.sleep(2)

        # Analisar logs
        print("\n" + "=" * 80)
        print("ANALISE DOS LOGS")
        print("=" * 80)

        # Contar re-renders
        render_logs = [log for log in console_logs if '[RENDER #' in log['text']]
        perf_logs = [log for log in console_logs if '[PERF]' in log['text']]

        print(f"\nTotal de re-renders: {len(render_logs)}")
        print(f"Total de recalculos: {len(perf_logs)}")

        # Mostrar timeline
        if render_logs:
            print("\nTIMELINE DE RENDERS:")
            first_time = render_logs[0]['time']
            for log in render_logs:
                rel_time = (log['time'] - first_time) * 1000
                print(f"  +{rel_time:7.0f}ms - {log['text']}")

        # Mostrar recalculos
        if perf_logs:
            print("\nRECALCULOS DETECTADOS:")
            for log in perf_logs:
                print(f"  {log['text']}")

        # Diagnóstico
        print("\n" + "=" * 80)
        print("DIAGNOSTICO")
        print("=" * 80)

        if len(render_logs) > 10:
            print(f"[CRITICO] {len(render_logs)} re-renders detectados!")
            print("Causa provavel: Dependencias incorretas em useMemo/useCallback")
        elif len(render_logs) > 5:
            print(f"[ALERTA] {len(render_logs)} re-renders (esperado 2-4)")
            print("Alguma otimizacao ainda necessaria")
        else:
            print(f"[OK] {len(render_logs)} re-renders (aceitavel)")

        # Fechar
        browser.close()

        print("\n" + "=" * 80)
        print("FIM DA CAPTURA")
        print("=" * 80)


if __name__ == "__main__":
    capture_console_logs()
