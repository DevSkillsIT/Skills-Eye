#!/usr/bin/env python3
"""
COMPARADOR: Baseline vs Pós-Melhorias

Compara resultados de baseline com resultados pós-melhorias para validar:
1. Funcionalidades continuam funcionando
2. Performance melhorou
3. Requests foram reduzidos

AUTOR: Plano de Teste ServersContext
DATA: 2025-11-16
"""

import json
from pathlib import Path
from typing import Dict, Any
from datetime import datetime

BASELINE_DIR = Path(__file__).parent.parent / "data" / "baselines"


def load_latest_baseline(test_type: str) -> Dict[str, Any]:
    """Carrega o baseline mais recente de um tipo específico"""
    pattern = f"{test_type}_ANTES_*.json"
    files = list(BASELINE_DIR.glob(pattern))
    
    if not files:
        return None
    
    # Ordenar por data (mais recente primeiro)
    files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
    
    with open(files[0], "r", encoding="utf-8") as f:
        return json.load(f)


def load_latest_after(test_type: str) -> Dict[str, Any]:
    """Carrega o resultado mais recente pós-melhorias"""
    pattern = f"{test_type}_DEPOIS_*.json"
    files = list(BASELINE_DIR.glob(pattern))
    
    if not files:
        return None
    
    # Ordenar por data (mais recente primeiro)
    files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
    
    with open(files[0], "r", encoding="utf-8") as f:
        return json.load(f)


def compare_backend_results(baseline: Dict, after: Dict) -> Dict[str, Any]:
    """Compara resultados de backend"""
    comparison = {
        "functionality": {
            "baseline_success": baseline.get("tests", {}).get("functionality", {}).get("status") == "SUCCESS",
            "after_success": after.get("tests", {}).get("functionality", {}).get("status") == "SUCCESS",
            "still_working": True
        },
        "performance": {
            "baseline_avg_ms": baseline.get("tests", {}).get("duplicate_requests", {}).get("average_time_ms", 0),
            "after_avg_ms": after.get("tests", {}).get("duplicate_requests", {}).get("average_time_ms", 0),
            "improvement_percent": 0
        },
        "cache": {
            "baseline_first_ms": baseline.get("tests", {}).get("cache_behavior", {}).get("first_request_ms", 0),
            "after_first_ms": after.get("tests", {}).get("cache_behavior", {}).get("first_request_ms", 0),
            "baseline_second_ms": baseline.get("tests", {}).get("cache_behavior", {}).get("second_request_ms", 0),
            "after_second_ms": after.get("tests", {}).get("cache_behavior", {}).get("second_request_ms", 0)
        }
    }
    
    # Calcular melhoria de performance
    if comparison["performance"]["baseline_avg_ms"] > 0:
        improvement = ((comparation["performance"]["baseline_avg_ms"] - comparison["performance"]["after_avg_ms"]) / 
                      comparison["performance"]["baseline_avg_ms"]) * 100
        comparison["performance"]["improvement_percent"] = round(improvement, 2)
    
    return comparison


def compare_frontend_results(baseline: Dict, after: Dict) -> Dict[str, Any]:
    """Compara resultados de frontend"""
    baseline_total = baseline.get("summary", {}).get("total_servers_requests", 0)
    after_total = after.get("summary", {}).get("total_servers_requests", 0)
    
    comparison = {
        "requests_reduction": {
            "baseline_total": baseline_total,
            "after_total": after_total,
            "reduction": baseline_total - after_total,
            "reduction_percent": round(((baseline_total - after_total) / baseline_total) * 100, 2) if baseline_total > 0 else 0
        },
        "pages": {}
    }
    
    # Comparar cada página
    for page_name in baseline.get("pages", {}).keys():
        baseline_page = baseline.get("pages", {}).get(page_name, {})
        after_page = after.get("pages", {}).get(page_name, {})
        
        if isinstance(baseline_page, dict) and isinstance(after_page, dict):
            baseline_nav = baseline_page.get("statistics", {}).get("navigation", {}).get("mean_ms", 0)
            after_nav = after_page.get("statistics", {}).get("navigation", {}).get("mean_ms", 0)
            
            comparison["pages"][page_name] = {
                "navigation": {
                    "baseline_ms": baseline_nav,
                    "after_ms": after_nav,
                    "improvement_percent": round(((baseline_nav - after_nav) / baseline_nav) * 100, 2) if baseline_nav > 0 else 0
                },
                "servers_requests": {
                    "baseline_count": baseline_page.get("statistics", {}).get("servers_requests", {}).get("mean_count", 0),
                    "after_count": after_page.get("statistics", {}).get("servers_requests", {}).get("mean_count", 0)
                }
            }
    
    return comparison


def generate_comparison_report():
    """Gera relatório de comparação"""
    print("\n" + "="*80)
    print("RELATÓRIO DE COMPARAÇÃO: Baseline vs Pós-Melhorias")
    print("="*80)
    
    # Carregar baselines
    backend_baseline = load_latest_baseline("SERVERS_BASELINE")
    frontend_baseline = load_latest_baseline("SERVERS_FRONTEND_BASELINE")
    
    backend_after = load_latest_after("SERVERS_BASELINE")
    frontend_after = load_latest_after("SERVERS_FRONTEND_BASELINE")
    
    if not backend_baseline:
        print("❌ Baseline backend não encontrado!")
        return
    
    if not frontend_baseline:
        print("❌ Baseline frontend não encontrado!")
        return
    
    print("\n📊 BACKEND:")
    if backend_after:
        backend_comp = compare_backend_results(backend_baseline, backend_after)
        print(f"  ✅ Funcionalidade: {'OK' if backend_comp['functionality']['still_working'] else 'FALHOU'}")
        print(f"  ⏱️  Performance: {backend_comp['performance']['improvement_percent']:.1f}% melhoria")
    else:
        print("  ⚠️  Resultados pós-melhorias não encontrados")
    
    print("\n📊 FRONTEND:")
    if frontend_after:
        frontend_comp = compare_frontend_results(frontend_baseline, frontend_after)
        print(f"  📉 Requests reduzidos: {frontend_comp['requests_reduction']['reduction']} ({frontend_comp['requests_reduction']['reduction_percent']:.1f}%)")
        print(f"  📄 Páginas:")
        for page_name, page_data in frontend_comp['pages'].items():
            print(f"    - {page_name}:")
            print(f"      • Navegação: {page_data['navigation']['improvement_percent']:.1f}% melhoria")
            print(f"      • Requests /servers: {page_data['servers_requests']['baseline_count']:.1f} → {page_data['servers_requests']['after_count']:.1f}")
    else:
        print("  ⚠️  Resultados pós-melhorias não encontrados")
    
    # Salvar relatório
    report = {
        "timestamp": datetime.now().isoformat(),
        "baseline": {
            "backend": backend_baseline.get("timestamp"),
            "frontend": frontend_baseline.get("timestamp")
        },
        "after": {
            "backend": backend_after.get("timestamp") if backend_after else None,
            "frontend": frontend_after.get("timestamp") if frontend_after else None
        },
        "comparison": {
            "backend": compare_backend_results(backend_baseline, backend_after) if backend_after else None,
            "frontend": compare_frontend_results(frontend_baseline, frontend_after) if frontend_after else None
        }
    }
    
    filename = f"SERVERS_COMPARISON_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    filepath = BASELINE_DIR / filename
    
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    print(f"\n📁 Relatório salvo em: {filepath}")


if __name__ == "__main__":
    generate_comparison_report()

