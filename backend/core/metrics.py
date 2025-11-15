"""
Métricas Prometheus para Monitoramento do Skills Eye

Este módulo centraliza TODAS as métricas Prometheus do sistema.
Inclui métricas de performance do Consul, endpoints, cache, etc.

SPRINT 1 - 2025-11-14: Métricas iniciais para otimização Consul
"""
import logging
from prometheus_client import Histogram, Counter, Gauge, Info

logger = logging.getLogger(__name__)

# ============================================================================
# MÉTRICAS CONSUL - Monitoramento de Performance e Disponibilidade
# ============================================================================

consul_request_duration = Histogram(
    'consul_request_duration_seconds',
    'Tempo de resposta das requisições ao Consul Agent/Catalog API',
    ['method', 'endpoint', 'node']
)

consul_requests_total = Counter(
    'consul_requests_total',
    'Total de requisições ao Consul Agent/Catalog API',
    ['method', 'endpoint', 'node', 'status']
)

consul_nodes_available = Gauge(
    'consul_nodes_available',
    'Número de nodes Consul disponíveis no momento'
)

consul_fallback_total = Counter(
    'consul_fallback_total',
    'Total de fallbacks executados (master offline → clients)',
    ['from_node', 'to_node']
)

# SPRINT 1 CORREÇÕES (2025-11-15): Métricas Agent Caching e Stale Reads
consul_cache_hits = Counter(
    'consul_cache_hits_total',
    'Total de cache hits no Agent Caching',
    ['endpoint', 'age_bucket']  # age_bucket: fresh|stale|very_stale
)

consul_stale_responses = Counter(
    'consul_stale_responses_total',
    'Total de respostas stale (>1s lag)',
    ['endpoint', 'lag_bucket']  # lag_bucket: 1s-5s|5s-10s|>10s
)

consul_api_type = Counter(
    'consul_api_calls_total',
    'Total de chamadas por tipo de API',
    ['api_type']  # api_type: agent|catalog|kv|health
)

# ============================================================================
# MÉTRICAS DE NEGÓCIO - Serviços e Targets
# ============================================================================

services_discovered_total = Gauge(
    'services_discovered_total',
    'Total de serviços descobertos no Consul',
    ['category']
)

blackbox_targets_total = Gauge(
    'blackbox_targets_total',
    'Total de alvos Blackbox Exporter cadastrados',
    ['module', 'group']
)

# ============================================================================
# MÉTRICAS DE CACHE - Performance do Sistema de Cache
# ============================================================================

cache_hits_total = Counter(
    'cache_hits_total',
    'Total de hits no cache KV',
    ['cache_key']
)

cache_misses_total = Counter(
    'cache_misses_total',
    'Total de misses no cache KV',
    ['cache_key']
)

cache_ttl_seconds = Histogram(
    'cache_ttl_seconds',
    'Tempo de vida dos itens no cache',
    ['cache_key']
)

# ============================================================================
# MÉTRICAS DE API - Performance dos Endpoints
# ============================================================================

api_request_duration = Histogram(
    'api_request_duration_seconds',
    'Tempo de resposta dos endpoints da API',
    ['method', 'endpoint', 'status_code']
)

api_requests_total = Counter(
    'api_requests_total',
    'Total de requisições aos endpoints da API',
    ['method', 'endpoint', 'status_code']
)

# ============================================================================
# INFORMAÇÕES DO SISTEMA - Metadados
# ============================================================================

system_info = Info(
    'skills_eye_system',
    'Informações do sistema Skills Eye'
)

# Inicializar com informações básicas
system_info.info({
    'version': '2.0',
    'component': 'backend',
    'language': 'python',
    'framework': 'fastapi'
})

logger.info("✅ Métricas Prometheus inicializadas com sucesso")
