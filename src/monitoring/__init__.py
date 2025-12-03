# Tradl AI - Monitoring Module
# Prometheus metrics and health checks

from .metrics import (
    metrics,
    MetricsCollector,
    create_metrics_endpoint,
    get_metrics,
    set_app_info,
    track_request_metrics,
    track_llm_call,
    record_cache_access,
    record_sentiment,
    record_entity,
    record_alert,
    record_duplicate,
    set_websocket_count,
    PROMETHEUS_AVAILABLE
)

__all__ = [
    'metrics',
    'MetricsCollector', 
    'create_metrics_endpoint',
    'get_metrics',
    'set_app_info',
    'track_request_metrics',
    'track_llm_call',
    'record_cache_access',
    'record_sentiment',
    'record_entity',
    'record_alert',
    'record_duplicate',
    'set_websocket_count',
    'PROMETHEUS_AVAILABLE'
]
