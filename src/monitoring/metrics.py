"""
Prometheus metrics for production observability.
Provides HTTP metrics, LLM metrics, cache metrics, and custom business metrics.
"""
import time
import os
import logging
from typing import Optional, Callable, Any
from functools import wraps
from contextlib import contextmanager

logger = logging.getLogger(__name__)

# Try to import prometheus_client, provide fallback if not available
try:
    from prometheus_client import (
        Counter, Histogram, Gauge, Info, Summary,
        generate_latest, CONTENT_TYPE_LATEST, REGISTRY
    )
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False
    logger.warning("prometheus_client not installed. Metrics disabled. Run: pip install prometheus-client")


# ================== Metrics Definitions ==================

if PROMETHEUS_AVAILABLE:
    # HTTP Request Metrics
    http_requests_total = Counter(
        'tradl_http_requests_total',
        'Total HTTP requests',
        ['method', 'endpoint', 'status']
    )
    
    http_request_duration = Histogram(
        'tradl_http_request_duration_seconds',
        'HTTP request latency',
        ['method', 'endpoint'],
        buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0)
    )
    
    # LLM Metrics
    llm_requests_total = Counter(
        'tradl_llm_requests_total',
        'Total LLM API calls',
        ['provider', 'model', 'status']
    )
    
    llm_request_duration = Histogram(
        'tradl_llm_request_duration_seconds',
        'LLM request latency',
        ['provider', 'model'],
        buckets=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0)
    )
    
    llm_tokens_total = Counter(
        'tradl_llm_tokens_total',
        'Total tokens processed',
        ['provider', 'direction']  # direction: input/output
    )
    
    # Cache Metrics
    cache_hits_total = Counter(
        'tradl_cache_hits_total',
        'Total cache hits',
        ['cache_type']  # embedding, query
    )
    
    cache_misses_total = Counter(
        'tradl_cache_misses_total',
        'Total cache misses',
        ['cache_type']
    )
    
    cache_size = Gauge(
        'tradl_cache_size',
        'Current cache size',
        ['cache_type']
    )
    
    # RAG Metrics
    rag_query_duration = Histogram(
        'tradl_rag_query_duration_seconds',
        'RAG query latency',
        buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0)
    )
    
    rag_documents_retrieved = Histogram(
        'tradl_rag_documents_retrieved',
        'Number of documents retrieved per query',
        buckets=(1, 5, 10, 20, 50, 100)
    )
    
    # News Processing Metrics
    news_articles_processed = Counter(
        'tradl_news_articles_processed_total',
        'Total news articles processed',
        ['source', 'status']
    )
    
    news_duplicates_detected = Counter(
        'tradl_news_duplicates_detected_total',
        'Total duplicate articles detected'
    )
    
    # Sentiment Analysis Metrics
    sentiment_analysis_duration = Histogram(
        'tradl_sentiment_analysis_duration_seconds',
        'Sentiment analysis latency',
        buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0)
    )
    
    sentiment_distribution = Counter(
        'tradl_sentiment_distribution_total',
        'Sentiment analysis results distribution',
        ['sentiment']  # positive, negative, neutral, bullish, bearish
    )
    
    # NER Metrics
    ner_extraction_duration = Histogram(
        'tradl_ner_extraction_duration_seconds',
        'NER extraction latency',
        buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0)
    )
    
    entities_extracted = Counter(
        'tradl_entities_extracted_total',
        'Total entities extracted',
        ['entity_type']  # ORG, STOCK, SECTOR, etc.
    )
    
    # Alert Metrics
    alerts_generated = Counter(
        'tradl_alerts_generated_total',
        'Total alerts generated',
        ['alert_type', 'severity']
    )
    
    # WebSocket Metrics
    websocket_connections = Gauge(
        'tradl_websocket_connections',
        'Active WebSocket connections'
    )
    
    # System Info
    app_info = Info(
        'tradl_app',
        'Application information'
    )


# ================== Decorator Helpers ==================

def track_request_metrics(endpoint: str):
    """Decorator to track HTTP request metrics"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            if not PROMETHEUS_AVAILABLE:
                return await func(*args, **kwargs)
            
            start_time = time.time()
            status = "success"
            
            try:
                result = await func(*args, **kwargs)
                return result
            except Exception as e:
                status = "error"
                raise
            finally:
                duration = time.time() - start_time
                http_requests_total.labels(
                    method="POST" if "POST" in endpoint else "GET",
                    endpoint=endpoint,
                    status=status
                ).inc()
                http_request_duration.labels(
                    method="POST" if "POST" in endpoint else "GET",
                    endpoint=endpoint
                ).observe(duration)
        
        return wrapper
    return decorator


def track_llm_call(provider: str, model: str):
    """Context manager to track LLM API calls"""
    @contextmanager
    def tracker():
        if not PROMETHEUS_AVAILABLE:
            yield
            return
        
        start_time = time.time()
        status = "success"
        
        try:
            yield
        except Exception as e:
            status = "error"
            raise
        finally:
            duration = time.time() - start_time
            llm_requests_total.labels(
                provider=provider,
                model=model,
                status=status
            ).inc()
            llm_request_duration.labels(
                provider=provider,
                model=model
            ).observe(duration)
    
    return tracker()


def record_cache_access(cache_type: str, hit: bool):
    """Record cache hit/miss"""
    if not PROMETHEUS_AVAILABLE:
        return
    
    if hit:
        cache_hits_total.labels(cache_type=cache_type).inc()
    else:
        cache_misses_total.labels(cache_type=cache_type).inc()


def record_sentiment(sentiment: str):
    """Record sentiment analysis result"""
    if not PROMETHEUS_AVAILABLE:
        return
    sentiment_distribution.labels(sentiment=sentiment.lower()).inc()


def record_entity(entity_type: str, count: int = 1):
    """Record extracted entities"""
    if not PROMETHEUS_AVAILABLE:
        return
    entities_extracted.labels(entity_type=entity_type).inc(count)


def record_alert(alert_type: str, severity: str):
    """Record generated alert"""
    if not PROMETHEUS_AVAILABLE:
        return
    alerts_generated.labels(alert_type=alert_type, severity=severity).inc()


def record_duplicate():
    """Record duplicate detection"""
    if not PROMETHEUS_AVAILABLE:
        return
    news_duplicates_detected.inc()


def set_websocket_count(count: int):
    """Set current WebSocket connection count"""
    if not PROMETHEUS_AVAILABLE:
        return
    websocket_connections.set(count)


# ================== Metrics Endpoint ==================

def get_metrics() -> tuple[bytes, str]:
    """
    Generate Prometheus metrics output.
    Returns (content, content_type)
    """
    if not PROMETHEUS_AVAILABLE:
        return b"# Prometheus metrics disabled - install prometheus-client", "text/plain"
    
    return generate_latest(REGISTRY), CONTENT_TYPE_LATEST


def set_app_info(version: str = "1.0.0", environment: str = None):
    """Set application info metric"""
    if not PROMETHEUS_AVAILABLE:
        return
    
    app_info.info({
        'version': version,
        'environment': environment or os.getenv('ENVIRONMENT', 'development'),
        'python_version': os.getenv('PYTHON_VERSION', '3.11')
    })


# ================== FastAPI Integration ==================

def create_metrics_endpoint():
    """
    Create FastAPI router for /metrics endpoint.
    
    Usage:
        from src.monitoring.metrics import create_metrics_endpoint
        app.include_router(create_metrics_endpoint())
    """
    try:
        from fastapi import APIRouter, Response
        
        router = APIRouter()
        
        @router.get("/metrics")
        async def metrics():
            content, content_type = get_metrics()
            return Response(content=content, media_type=content_type)
        
        return router
        
    except ImportError:
        logger.warning("FastAPI not available for metrics endpoint")
        return None


# ================== Metric Collection Utilities ==================

class MetricsCollector:
    """
    Centralized metrics collector for the application.
    Use this class to collect and report metrics throughout the codebase.
    """
    
    def __init__(self):
        self.enabled = PROMETHEUS_AVAILABLE
    
    def request_started(self, method: str, endpoint: str) -> float:
        """Mark the start of a request, returns start time"""
        return time.time()
    
    def request_completed(
        self,
        method: str,
        endpoint: str,
        status: str,
        start_time: float
    ):
        """Record completed request metrics"""
        if not self.enabled:
            return
        
        duration = time.time() - start_time
        http_requests_total.labels(
            method=method,
            endpoint=endpoint,
            status=status
        ).inc()
        http_request_duration.labels(
            method=method,
            endpoint=endpoint
        ).observe(duration)
    
    def llm_call(
        self,
        provider: str,
        model: str,
        duration: float,
        status: str = "success",
        input_tokens: int = 0,
        output_tokens: int = 0
    ):
        """Record LLM API call metrics"""
        if not self.enabled:
            return
        
        llm_requests_total.labels(
            provider=provider,
            model=model,
            status=status
        ).inc()
        
        llm_request_duration.labels(
            provider=provider,
            model=model
        ).observe(duration)
        
        if input_tokens > 0:
            llm_tokens_total.labels(provider=provider, direction="input").inc(input_tokens)
        if output_tokens > 0:
            llm_tokens_total.labels(provider=provider, direction="output").inc(output_tokens)
    
    def rag_query(self, duration: float, num_documents: int):
        """Record RAG query metrics"""
        if not self.enabled:
            return
        
        rag_query_duration.observe(duration)
        rag_documents_retrieved.observe(num_documents)
    
    def news_processed(self, source: str, status: str = "success"):
        """Record news processing"""
        if not self.enabled:
            return
        news_articles_processed.labels(source=source, status=status).inc()
    
    def sentiment(self, label: str, duration: float):
        """Record sentiment analysis"""
        if not self.enabled:
            return
        sentiment_analysis_duration.observe(duration)
        sentiment_distribution.labels(sentiment=label.lower()).inc()
    
    def ner(self, entity_counts: dict, duration: float):
        """Record NER extraction"""
        if not self.enabled:
            return
        ner_extraction_duration.observe(duration)
        for entity_type, count in entity_counts.items():
            entities_extracted.labels(entity_type=entity_type).inc(count)


# Global collector instance
metrics = MetricsCollector()
