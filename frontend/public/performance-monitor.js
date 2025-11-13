/**
 * Script para medir performance de rendering no browser
 * Injeta no HTML para capturar métricas de carregamento
 */

// Capturar quando página começou a carregar
const pageLoadStart = performance.now();

// Marcar quando DOM está pronto
document.addEventListener('DOMContentLoaded', () => {
  const domReady = performance.now() - pageLoadStart;
  console.log(`[PERF] DOM Ready: ${domReady.toFixed(0)}ms`);
});

// Marcar quando página terminou de carregar
window.addEventListener('load', () => {
  const pageLoad = performance.now() - pageLoadStart;
  console.log(`[PERF] Page Load: ${pageLoad.toFixed(0)}ms`);

  // Aguardar React montar e tabela aparecer
  setTimeout(() => {
    // Contar linhas da tabela
    const tableRows = document.querySelectorAll('.ant-table-tbody tr').length;
    const renderComplete = performance.now() - pageLoadStart;

    console.log(`[PERF] Render Complete: ${renderComplete.toFixed(0)}ms`);
    console.log(`[PERF] Table Rows: ${tableRows}`);

    // Medir Layout Shift
    if (window.PerformanceObserver) {
      let cls = 0;
      new PerformanceObserver((list) => {
        for (const entry of list.getEntries()) {
          if (!entry.hadRecentInput) {
            cls += entry.value;
          }
        }
        console.log(`[PERF] CLS (Cumulative Layout Shift): ${cls.toFixed(3)}`);
      }).observe({ type: 'layout-shift', buffered: true });
    }
  }, 2000); // Aguardar 2s para garantir que tabela renderizou
});

// Medir Largest Contentful Paint
if (window.PerformanceObserver) {
  new PerformanceObserver((list) => {
    const entries = list.getEntries();
    const lastEntry = entries[entries.length - 1];
    console.log(`[PERF] LCP (Largest Contentful Paint): ${lastEntry.renderTime.toFixed(0)}ms`);
  }).observe({ type: 'largest-contentful-paint', buffered: true });
}
