"""
API endpoints para status e saúde
"""
from fastapi import APIRouter, HTTPException
from typing import Dict, List
from core.consul_manager import ConsulManager
from core.config import Config
import requests

router = APIRouter()

@router.get("/status")
async def get_health_status():
    """Retorna status geral do sistema"""
    try:
        consul = ConsulManager()
        health_data = await consul.get_health_status()

        # Processar status
        passing = []
        warning = []
        critical = []
        
        for h in health_data:
            status = h.get("Status", "unknown")
            service_info = {
                "service": h.get("ServiceName", h.get("CheckID", "unknown")),
                "id": h.get("ServiceID", ""),
                "output": h.get("Output", "No output")[:200],
                "notes": h.get("Notes", "")
            }
            
            if status == "passing":
                passing.append(service_info)
            elif status == "warning":
                warning.append(service_info)
            elif status == "critical":
                critical.append(service_info)
        
        return {
            "success": True,
            "summary": {
                "passing": len(passing),
                "warning": len(warning),
                "critical": len(critical),
                "total": len(health_data)
            },
            "details": {
                "passing": passing[:10],
                "warning": warning[:10],
                "critical": critical[:10]
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/connectivity")
async def test_connectivity():
    """Testa conectividade com serviços principais"""
    services_to_test = {
        "consul": f"http://{Config.MAIN_SERVER}:8500/v1/status/leader",
        "prometheus": f"http://{Config.MAIN_SERVER}:9090/-/healthy",
        "grafana": f"http://{Config.MAIN_SERVER}:3000/api/health",
        "blackbox": f"http://{Config.MAIN_SERVER}:9115/metrics"
    }
    
    results = {}
    
    for service, url in services_to_test.items():
        try:
            response = requests.get(url, timeout=2)
            results[service] = {
                "status": "online",
                "code": response.status_code
            }
        except:
            results[service] = {
                "status": "offline",
                "code": 0
            }
    
    return {
        "success": True,
        "services": results,
        "main_server": Config.MAIN_SERVER
    }