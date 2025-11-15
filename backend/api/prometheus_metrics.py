"""
Prometheus Metrics Parser API

Endpoint que parseia /metrics (formato texto Prometheus) e retorna JSON
para consumo fácil pelo frontend.

SPRINT 2 - 2025-11-15
"""
from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
import re
from typing import Dict, List, Any
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

router = APIRouter(prefix="/prometheus-metrics", tags=["Prometheus Metrics"])


def parse_prometheus_text(text: str) -> Dict[str, Any]:
    """
    Parseia formato texto Prometheus e retorna estrutura JSON.

    Args:
        text: Texto no formato Prometheus (# HELP, # TYPE, métrica valor)

    Returns:
        Dict com métricas organizadas por nome
    """
    metrics = {}
    current_metric = None
    current_help = None
    current_type = None

    for line in text.split('\n'):
        line = line.strip()

        # Ignorar linhas vazias
        if not line:
            continue

        # Parse HELP
        if line.startswith('# HELP'):
            parts = line.split(' ', 3)
            if len(parts) >= 4:
                current_metric = parts[2]
                current_help = parts[3]
                if current_metric not in metrics:
                    metrics[current_metric] = {
                        'help': current_help,
                        'type': None,
                        'values': []
                    }
            continue

        # Parse TYPE
        if line.startswith('# TYPE'):
            parts = line.split(' ', 3)
            if len(parts) >= 4:
                current_metric = parts[2]
                current_type = parts[3]
                if current_metric not in metrics:
                    metrics[current_metric] = {
                        'help': None,
                        'type': current_type,
                        'values': []
                    }
                else:
                    metrics[current_metric]['type'] = current_type
            continue

        # Ignorar outros comentários
        if line.startswith('#'):
            continue

        # Parse valor da métrica
        # Formato: metric_name{label1="value1",label2="value2"} value timestamp
        # ou: metric_name value timestamp
        match = re.match(r'^([a-zA-Z_:][a-zA-Z0-9_:]*)\{([^}]*)\}\s+([\d.eE+-]+)', line)
        if match:
            metric_name = match.group(1)
            labels_str = match.group(2)
            value = float(match.group(3))

            # Parsear labels
            labels = {}
            for label_pair in labels_str.split(','):
                label_match = re.match(r'([^=]+)="([^"]*)"', label_pair.strip())
                if label_match:
                    labels[label_match.group(1)] = label_match.group(2)

            if metric_name not in metrics:
                metrics[metric_name] = {
                    'help': None,
                    'type': None,
                    'values': []
                }

            metrics[metric_name]['values'].append({
                'labels': labels,
                'value': value
            })
        else:
            # Métrica sem labels
            match_simple = re.match(r'^([a-zA-Z_:][a-zA-Z0-9_:]*)\s+([\d.eE+-]+)', line)
            if match_simple:
                metric_name = match_simple.group(1)
                value = float(match_simple.group(2))

                if metric_name not in metrics:
                    metrics[metric_name] = {
                        'help': None,
                        'type': None,
                        'values': []
                    }

                metrics[metric_name]['values'].append({
                    'labels': {},
                    'value': value
                })

    return metrics


@router.get("/parsed")
async def get_parsed_metrics():
    """
    Retorna métricas Prometheus parseadas em JSON.

    Returns:
        Dict com métricas estruturadas:
        {
            "consul_cache_hits_total": {
                "help": "Total de cache hits...",
                "type": "counter",
                "values": [
                    {"labels": {"endpoint": "/catalog/services"}, "value": 5},
                    ...
                ]
            },
            ...
        }
    """
    try:
        # Gerar métricas Prometheus (formato texto)
        metrics_text = generate_latest().decode('utf-8')

        # Parsear para JSON
        parsed = parse_prometheus_text(metrics_text)

        return {
            "success": True,
            "metrics": parsed,
            "total_metrics": len(parsed)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao parsear métricas: {str(e)}")


@router.get("/summary")
async def get_metrics_summary():
    """
    Retorna resumo das métricas principais para dashboard.

    Returns:
        Dict com KPIs principais:
        {
            "cache_hits": 42,
            "cache_misses": 5,
            "cache_hit_rate": 89.4,
            "stale_responses": 2,
            "fallback_events": 0,
            "total_requests": 150
        }
    """
    try:
        metrics_text = generate_latest().decode('utf-8')
        parsed = parse_prometheus_text(metrics_text)

        # Extrair KPIs principais
        summary = {
            "cache_hits": 0,
            "cache_misses": 0,
            "cache_hit_rate": 0.0,
            "stale_responses": 0,
            "fallback_events": 0,
            "total_requests": 0,
        }

        # Cache hits
        if 'consul_cache_hits_total' in parsed:
            for entry in parsed['consul_cache_hits_total']['values']:
                summary['cache_hits'] += entry['value']

        # Stale responses
        if 'consul_stale_responses_total' in parsed:
            for entry in parsed['consul_stale_responses_total']['values']:
                summary['stale_responses'] += entry['value']

        # Fallback events
        if 'consul_fallback_total' in parsed:
            for entry in parsed['consul_fallback_total']['values']:
                summary['fallback_events'] += entry['value']

        # Total requests (aproximado: hits + misses)
        summary['total_requests'] = summary['cache_hits'] + summary['cache_misses']

        # Hit rate
        if summary['total_requests'] > 0:
            summary['cache_hit_rate'] = round((summary['cache_hits'] / summary['total_requests']) * 100, 1)

        return summary
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao gerar resumo: {str(e)}")
