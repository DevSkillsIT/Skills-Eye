"""
API otimizada de Dashboard
Endpoint único e RÁPIDO que retorna todas as métricas processadas
Similar ao TenSunS - processa tudo no backend
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, List, Optional
# SPRINT 2: Cache antigo removido - dashboard não usa mais cache local
# from core.cache_manager import cache_manager
from core.audit_manager import audit_manager
from core.config import Config
import requests
import time

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])

# Headers e URL do Consul
CONSUL_HEADERS = {"X-Consul-Token": Config.CONSUL_TOKEN}
CONSUL_URL = f"http://{Config.MAIN_SERVER}:{Config.CONSUL_PORT}/v1"


class DashboardMetrics(BaseModel):
    """Modelo de resposta das métricas do dashboard"""
    total_services: int
    blackbox_targets: int
    exporters: int
    active_nodes: int
    total_nodes: int
    health: Dict[str, int]
    by_env: Dict[str, int]
    by_datacenter: Dict[str, int]
    recent_changes: List[dict]
    load_time_ms: Optional[int] = None


@router.get("/metrics", response_model=DashboardMetrics)
def get_dashboard_metrics_fast():
    """
    Endpoint SUPER OTIMIZADO para métricas do dashboard

    Otimizações:
    - Cache de 30 segundos (retorna instantaneamente se cacheado)
    - UMA única chamada ao Consul (/internal/ui/services)
    - Processamento no backend (não sobrecarrega frontend)
    - Síncrono (sem overhead de async)
    - Similar ao TenSunS (método mais rápido)
    """
    start_time = time.time()

    # SPRINT 2: Cache removido - dashboard sempre busca dados frescos
    # O cache agora é feito no ConsulManager para get_all_services_catalog()

    try:
        # 1 CHAMADA AO CONSUL - Endpoint agregado (rápido!)
        services_response = requests.get(
            f"{CONSUL_URL}/internal/ui/services",
            headers=CONSUL_HEADERS,
            timeout=5
        )
        services_response.raise_for_status()
        services_list = [s for s in services_response.json() if s.get('Name') != 'consul']

        # Buscar nodes
        nodes_response = requests.get(
            f"{CONSUL_URL}/catalog/nodes",
            headers=CONSUL_HEADERS,
            timeout=5
        )
        nodes_response.raise_for_status()
        nodes_list = nodes_response.json()

        # Contadores
        total_services = 0
        blackbox_count = 0
        exporter_count = 0
        by_env: Dict[str, int] = {}
        by_datacenter: Dict[str, int] = {}
        health_stats = {'passing': 0, 'warning': 0, 'critical': 0}

        # Blackbox modules conhecidos
        blackbox_modules = ['icmp', 'http_2xx', 'http_4xx', 'http_5xx',
                          'http_post_2xx', 'https', 'tcp_connect',
                          'ssh_banner', 'pop3s_banner', 'irc_banner']

        # Processar serviços (JÁ AGREGADOS do /internal/ui/services)
        for svc in services_list:
            service_name = str(svc.get('Name', '')).lower()
            instance_count = svc.get('InstanceCount', 0)

            total_services += instance_count

            # Identificar tipo
            tags = [str(t).lower() for t in svc.get('Tags', [])]
            is_blackbox = any(bm in tag for tag in tags for bm in blackbox_modules)
            is_exporter = '_exporter' in service_name

            if is_blackbox:
                blackbox_count += instance_count
            elif is_exporter:
                exporter_count += instance_count

            # Por ambiente (extrair de tags)
            env = 'unknown'
            for tag in tags:
                if '=' in tag:
                    key, val = tag.split('=', 1)
                    if key in ['env', 'ambiente']:
                        env = val
                        break
            by_env[env] = by_env.get(env, 0) + instance_count

            # Por datacenter
            dc = svc.get('Datacenter', 'unknown')
            by_datacenter[dc] = by_datacenter.get(dc, 0) + instance_count

            # Health stats
            health_stats['passing'] += svc.get('ChecksPassing', 0)
            health_stats['critical'] += svc.get('ChecksCritical', 0)
            health_stats['warning'] += svc.get('ChecksWarning', 0)

        # Processar nodes
        active_nodes = 0
        total_nodes = len(nodes_list)

        for node in nodes_list:
            # Nodes no catalog/nodes não têm status, assumir alive
            active_nodes += 1

        # Eventos recentes de auditoria (últimos 10)
        recent_events, _ = audit_manager.get_events(limit=10)

        # Montar resposta
        metrics = {
            'total_services': total_services,
            'blackbox_targets': blackbox_count,
            'exporters': exporter_count,
            'active_nodes': active_nodes,
            'total_nodes': total_nodes,
            'health': health_stats,
            'by_env': by_env,
            'by_datacenter': by_datacenter,
            'recent_changes': recent_events,
            'load_time_ms': int((time.time() - start_time) * 1000),
        }

        # SPRINT 2: Cache removido - dados sempre frescos
        return metrics

    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=503, detail=f"Erro ao conectar com Consul: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao buscar métricas: {str(e)}")


@router.post("/clear-cache")
def clear_dashboard_cache():
    """SPRINT 2: Endpoint deprecado - use /api/v1/cache/clear"""
    return {
        "success": False,
        "message": "Endpoint deprecado. Use /api/v1/cache/clear para limpar o cache global"
    }
