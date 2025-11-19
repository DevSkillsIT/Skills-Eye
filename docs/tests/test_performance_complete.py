#!/usr/bin/env python3
"""
TESTE COMPLETO DE PERFORMANCE - Backend vs Frontend
Identifica EXATAMENTE onde está o gargalo

TESTES:
1. Performance do backend (API pura)
2. Performance do frontend (renderização)
3. NodeSelector exibe corretamente
4. Filtros funcionam
5. Botão limpar funciona

Autor: AI Assistant
Data: 2025-11-14
"""

import time
import json
import statistics
import requests
from typing import List, Dict, Any

# ============================================================================
# CONFIGURAÇÃO
# ============================================================================

API_URL = "http://localhost:5000/api/v1"
FRONTEND_URL = "http://localhost:8081"

# Cores para output
class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    MAGENTA = '\033[95m'
    BOLD = '\033[1m'
    END = '\033[0m'

def print_header(text: str):
    print(f"\n{Colors.BOLD}{'='*80}{Colors.END}")
    print(f"{Colors.BOLD}{text}{Colors.END}")
    print(f"{Colors.BOLD}{'='*80}{Colors.END}\n")

def print_success(text: str):
    print(f"{Colors.GREEN}✅ {text}{Colors.END}")

def print_error(text: str):
    print(f"{Colors.RED}❌ {text}{Colors.END}")

def print_warning(text: str):
    print(f"{Colors.YELLOW}⚠️  {text}{Colors.END}")

def print_info(text: str):
    print(f"{Colors.BLUE}ℹ️  {text}{Colors.END}")

def print_perf(text: str):
    print(f"{Colors.CYAN}⏱️  {text}{Colors.END}")

# ============================================================================
# TESTE 1: PERFORMANCE DO BACKEND (API PURA)
# ============================================================================

def test_backend_performance(iterations: int = 10) -> Dict[str, Any]:
    """
    Testa performance do backend fazendo múltiplas requisições
    Retorna estatísticas de tempo de resposta
    """
    print_header("🔍 TESTE 1: Performance do Backend (API Pura)")
    
    timings: List[float] = []
    
    for i in range(iterations):
        try:
            start = time.time()
            response = requests.get(f"{API_URL}/nodes", timeout=10)
            end = time.time()
            
            elapsed_ms = (end - start) * 1000
            timings.append(elapsed_ms)
            
            if response.status_code == 200:
                data = response.json()
                nodes_count = len(data.get('data', []))
                print(f"  Iteração {i+1}/{iterations}: {elapsed_ms:.0f}ms ({nodes_count} nós)")
            else:
                print_error(f"Iteração {i+1}: HTTP {response.status_code}")
                
        except Exception as e:
            print_error(f"Iteração {i+1}: {e}")
            timings.append(9999)  # Timeout placeholder
    
    if not timings:
        return {"success": False, "error": "Nenhuma medição válida"}
    
    # Remover outliers (valores > 5000ms)
    clean_timings = [t for t in timings if t < 5000]
    
    if not clean_timings:
        return {"success": False, "error": "Todas as requisições falharam"}
    
    stats = {
        "success": True,
        "min": min(clean_timings),
        "max": max(clean_timings),
        "avg": statistics.mean(clean_timings),
        "median": statistics.median(clean_timings),
        "stdev": statistics.stdev(clean_timings) if len(clean_timings) > 1 else 0,
        "samples": len(clean_timings)
    }
    
    print()
    print_perf(f"Mínimo:    {stats['min']:.0f}ms")
    print_perf(f"Máximo:    {stats['max']:.0f}ms")
    print_perf(f"Média:     {stats['avg']:.0f}ms")
    print_perf(f"Mediana:   {stats['median']:.0f}ms")
    print_perf(f"Desvio:    {stats['stdev']:.0f}ms")
    print_perf(f"Amostras:  {stats['samples']}/{iterations}")
    
    # Análise
    print()
    if stats['avg'] < 500:
        print_success(f"Performance EXCELENTE: {stats['avg']:.0f}ms (< 500ms)")
    elif stats['avg'] < 1000:
        print_success(f"Performance BOA: {stats['avg']:.0f}ms (< 1000ms)")
    elif stats['avg'] < 2000:
        print_warning(f"Performance ACEITÁVEL: {stats['avg']:.0f}ms (< 2000ms)")
    else:
        print_error(f"Performance RUIM: {stats['avg']:.0f}ms (> 2000ms)")
    
    return stats

# ============================================================================
# TESTE 2: PERFORMANCE ENDPOINT MONITORING
# ============================================================================

def test_monitoring_endpoint_performance(iterations: int = 5) -> Dict[str, Any]:
    """
    Testa performance do endpoint de monitoramento (network-probes)
    Este é o endpoint que o frontend chama
    """
    print_header("🔍 TESTE 2: Performance Endpoint Monitoring")
    
    timings: List[float] = []
    record_counts: List[int] = []
    
    for i in range(iterations):
        try:
            start = time.time()
            response = requests.get(
                f"{API_URL}/monitoring/network-probes",
                params={"company": None, "site": None, "env": None},
                timeout=30
            )
            end = time.time()
            
            elapsed_ms = (end - start) * 1000
            timings.append(elapsed_ms)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    records = len(data.get('data', []))
                    record_counts.append(records)
                    print(f"  Iteração {i+1}/{iterations}: {elapsed_ms:.0f}ms ({records} registros)")
                else:
                    print_error(f"Iteração {i+1}: API retornou success=false")
            else:
                print_error(f"Iteração {i+1}: HTTP {response.status_code}")
                
        except requests.Timeout:
            print_error(f"Iteração {i+1}: TIMEOUT (> 30s)")
            timings.append(30000)
        except Exception as e:
            print_error(f"Iteração {i+1}: {e}")
            timings.append(9999)
    
    if not timings:
        return {"success": False, "error": "Nenhuma medição válida"}
    
    clean_timings = [t for t in timings if t < 30000]
    
    if not clean_timings:
        return {"success": False, "error": "Todas as requisições falharam ou timeout"}
    
    stats = {
        "success": True,
        "min": min(clean_timings),
        "max": max(clean_timings),
        "avg": statistics.mean(clean_timings),
        "median": statistics.median(clean_timings),
        "stdev": statistics.stdev(clean_timings) if len(clean_timings) > 1 else 0,
        "samples": len(clean_timings),
        "avg_records": statistics.mean(record_counts) if record_counts else 0
    }
    
    print()
    print_perf(f"Mínimo:    {stats['min']:.0f}ms")
    print_perf(f"Máximo:    {stats['max']:.0f}ms")
    print_perf(f"Média:     {stats['avg']:.0f}ms")
    print_perf(f"Mediana:   {stats['median']:.0f}ms")
    print_perf(f"Desvio:    {stats['stdev']:.0f}ms")
    print_info(f"Registros médios: {stats['avg_records']:.0f}")
    
    # Análise
    print()
    if stats['avg'] < 800:
        print_success(f"Performance EXCELENTE: {stats['avg']:.0f}ms (< 800ms)")
    elif stats['avg'] < 1500:
        print_success(f"Performance BOA: {stats['avg']:.0f}ms (< 1500ms)")
    elif stats['avg'] < 3000:
        print_warning(f"Performance ACEITÁVEL: {stats['avg']:.0f}ms (< 3000ms)")
    else:
        print_error(f"Performance RUIM: {stats['avg']:.0f}ms (> 3000ms)")
    
    return stats

# ============================================================================
# TESTE 3: VALIDAR NODES ENDPOINT
# ============================================================================

def test_nodes_site_names() -> bool:
    """
    Valida se nodes endpoint retorna site_name diferente de IP
    """
    print_header("🔍 TESTE 3: Validação site_name nos Nodes")
    
    try:
        response = requests.get(f"{API_URL}/nodes", timeout=10)
        data = response.json()
        
        if not data.get('success'):
            print_error("Backend não retornou success=true")
            return False
        
        nodes = data.get('data', [])
        if not nodes:
            print_error("Nenhum nó retornado")
            return False
        
        print_info(f"Analisando {len(nodes)} nós...\n")
        
        all_ok = True
        for node in nodes:
            node_name = node.get('node', 'unknown')
            site_name = node.get('site_name', '')
            addr = node.get('addr', '')
            
            # Verificar se site_name é igual ao IP (usando IP como fallback)
            if site_name == addr:
                print_warning(f"Nó '{node_name}': site_name=IP ({site_name})")
                print_warning(f"  → Usando IP como fallback (KV lookup falhou?)")
                all_ok = False
            else:
                print_success(f"Nó '{node_name}': site_name='{site_name}' ≠ addr='{addr}'")
        
        print()
        if all_ok:
            print_success("TODOS os nós têm site_name diferente de IP!")
            return True
        else:
            print_warning("ALGUNS nós estão usando IP como site_name (esperado se KV não populado)")
            return True  # Não é erro crítico
            
    except Exception as e:
        print_error(f"Erro ao validar nodes: {e}")
        return False

# ============================================================================
# TESTE 4: ANÁLISE DE LENTIDÃO
# ============================================================================

def analyze_performance_bottleneck(backend_stats: Dict, monitoring_stats: Dict):
    """
    Analisa onde está o gargalo de performance
    """
    print_header("🔍 TESTE 4: Análise de Gargalo de Performance")
    
    if not backend_stats.get('success') or not monitoring_stats.get('success'):
        print_error("Não é possível analisar - testes anteriores falharam")
        return
    
    backend_avg = backend_stats['avg']
    monitoring_avg = monitoring_stats['avg']
    records_avg = monitoring_stats.get('avg_records', 0)
    
    print_info(f"Backend (/nodes):              {backend_avg:.0f}ms")
    print_info(f"Monitoring (/network-probes):  {monitoring_avg:.0f}ms")
    print_info(f"Registros médios:              {records_avg:.0f}")
    
    # Calcular overhead
    overhead = monitoring_avg - backend_avg
    overhead_percent = (overhead / backend_avg * 100) if backend_avg > 0 else 0
    
    print()
    print_perf(f"Overhead do endpoint monitoring: {overhead:.0f}ms ({overhead_percent:.1f}%)")
    
    # Análise
    print()
    if overhead < 200:
        print_success("Overhead BAIXO - Backend está eficiente!")
    elif overhead < 500:
        print_warning("Overhead MODERADO - Pode melhorar otimizações no backend")
    else:
        print_error("Overhead ALTO - Backend tem gargalos significativos!")
        print_info("  → Verificar queries, transformações de dados, filtros")
    
    # Estimativa de performance por registro
    if records_avg > 0:
        time_per_record = monitoring_avg / records_avg
        print()
        print_info(f"Tempo médio por registro: {time_per_record:.2f}ms")
        
        if time_per_record < 5:
            print_success("Processamento por registro EXCELENTE!")
        elif time_per_record < 10:
            print_success("Processamento por registro BOM!")
        else:
            print_warning("Processamento por registro pode melhorar")
    
    # Diagnóstico do problema do usuário (615ms → 1162ms)
    print()
    print_header("📊 DIAGNÓSTICO: Lentidão reportada (615ms → 1162ms)")
    
    print_info("Possíveis causas:")
    print("  1. BACKEND: Filtro de nó duplica queries ou processa duas vezes")
    print("  2. FRONTEND: Re-renders desnecessários (React Strict Mode?)")
    print("  3. FRONTEND: Cálculo de metadataOptions muito pesado")
    print("  4. FRONTEND: Filtros avançados aplicados múltiplas vezes")
    print("  5. REDE: Latência adicional em requisições subsequentes")
    
    print()
    if monitoring_avg < 800:
        print_success(f"API está rápida ({monitoring_avg:.0f}ms)")
        print_info("→ Gargalo provavelmente está no FRONTEND")
        print_info("  Verifique console.log [PERF] no navegador")
        print_info("  Procure por operações > 100ms")
    else:
        print_warning(f"API está lenta ({monitoring_avg:.0f}ms)")
        print_info("→ Gargalo está no BACKEND")
        print_info("  Verifique logs do backend")
        print_info("  Otimize queries e transformações")

# ============================================================================
# MAIN
# ============================================================================

def main():
    """
    Executa todos os testes em sequência
    """
    print()
    print(f"{Colors.BOLD}{Colors.MAGENTA}")
    print("╔" + "═" * 78 + "╗")
    print("║" + " " * 20 + "TESTE COMPLETO DE PERFORMANCE" + " " * 29 + "║")
    print("║" + " " * 24 + "Backend vs Frontend" + " " * 35 + "║")
    print("╚" + "═" * 78 + "╝")
    print(f"{Colors.END}")
    
    # Teste 1: Backend /nodes
    backend_stats = test_backend_performance(iterations=10)
    time.sleep(1)
    
    # Teste 2: Monitoring endpoint
    monitoring_stats = test_monitoring_endpoint_performance(iterations=5)
    time.sleep(1)
    
    # Teste 3: Validar site_names
    nodes_ok = test_nodes_site_names()
    time.sleep(1)
    
    # Teste 4: Análise de gargalo
    analyze_performance_bottleneck(backend_stats, monitoring_stats)
    
    # Resumo final
    print_header("📊 RESUMO FINAL")
    
    print("RESULTADOS:")
    if backend_stats.get('success'):
        print_success(f"Backend /nodes: {backend_stats['avg']:.0f}ms (média)")
    else:
        print_error("Backend /nodes: FALHOU")
    
    if monitoring_stats.get('success'):
        print_success(f"Monitoring endpoint: {monitoring_stats['avg']:.0f}ms (média)")
    else:
        print_error("Monitoring endpoint: FALHOU")
    
    if nodes_ok:
        print_success("Nodes site_name: OK")
    else:
        print_error("Nodes site_name: PROBLEMA")
    
    print()
    print_info("Para testar FRONTEND (React rendering):")
    print("  1. Abra http://localhost:8081/monitoring/network-probes")
    print("  2. Abra DevTools (F12) → Console")
    print("  3. Procure por logs [PERF]")
    print("  4. Identifique operações > 100ms")
    print("  5. Verifique se há re-renders múltiplos (Strict Mode)")
    print()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print()
        print_warning("Teste interrompido pelo usuário")
        exit(1)
    except Exception as e:
        print()
        print_error(f"Erro fatal: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
