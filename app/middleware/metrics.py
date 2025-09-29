"""
Metrics middleware for monitoring and observability
"""

import time
import logging
from typing import Callable
from fastapi import Request, Response
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from app.config import settings

logger = logging.getLogger(__name__)

# Prometheus metrics
REQUEST_COUNT = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status_code']
)

REQUEST_DURATION = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration in seconds',
    ['method', 'endpoint']
)

PROCESSING_DURATION = Histogram(
    'pdf_processing_duration_seconds',
    'PDF processing duration in seconds',
    ['status']
)

FILE_SIZE = Histogram(
    'pdf_file_size_bytes',
    'PDF file size in bytes',
    ['operation']
)

REDACTION_COUNT = Counter(
    'pdf_redactions_total',
    'Total number of redactions performed',
    ['reason']
)


async def metrics_middleware(request: Request, call_next: Callable) -> Response:
    """Middleware to collect HTTP metrics"""
    
    start_time = time.time()
    
    # Get request info
    method = request.method
    endpoint = request.url.path
    
    # Process request
    response = await call_next(request)
    
    # Calculate duration
    duration = time.time() - start_time
    
    # Record metrics
    REQUEST_COUNT.labels(
        method=method,
        endpoint=endpoint,
        status_code=response.status_code
    ).inc()
    
    REQUEST_DURATION.labels(
        method=method,
        endpoint=endpoint
    ).observe(duration)
    
    return response


def record_processing_metrics(
    processing_time: float,
    file_size: int,
    redaction_count: int,
    success: bool,
    redaction_reasons: dict = None
):
    """Record PDF processing metrics"""
    
    status_label = "success" if success else "failure"
    
    PROCESSING_DURATION.labels(status=status_label).observe(processing_time)
    FILE_SIZE.labels(operation="processed").observe(file_size)
    
    if redaction_reasons:
        for reason, count in redaction_reasons.items():
            REDACTION_COUNT.labels(reason=reason).inc(count)


def get_metrics():
    """Get Prometheus metrics"""
    return generate_latest()
