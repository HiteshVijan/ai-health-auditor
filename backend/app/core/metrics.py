"""
Prometheus Metrics Module.

Exposes application metrics for monitoring with Prometheus.
"""

from prometheus_client import Counter, Histogram, Gauge, Info, generate_latest, CONTENT_TYPE_LATEST
from fastapi import APIRouter, Response
import time

# ============================================
# Application Info
# ============================================
APP_INFO = Info(
    "app_info",
    "Application information"
)
APP_INFO.info({
    "app_name": "ai_health_bill_auditor",
    "version": "1.0.0",
})

# ============================================
# Upload Metrics
# ============================================
UPLOADS_TOTAL = Counter(
    "uploads_total",
    "Total number of document uploads",
    ["status", "content_type"]
)

UPLOADS_IN_PROGRESS = Gauge(
    "uploads_in_progress",
    "Number of uploads currently being processed"
)

UPLOAD_SIZE_BYTES = Histogram(
    "upload_size_bytes",
    "Size of uploaded documents in bytes",
    buckets=[1024, 10240, 102400, 1048576, 5242880, 10485760]  # 1KB to 10MB
)

# ============================================
# Document Parsing Metrics
# ============================================
DOCUMENTS_PARSED_TOTAL = Counter(
    "documents_parsed_total",
    "Total number of documents parsed",
    ["status", "document_type"]
)

PARSE_DURATION_SECONDS = Histogram(
    "parse_duration_seconds",
    "Time spent parsing documents",
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0, 120.0]
)

TABLES_EXTRACTED_TOTAL = Counter(
    "tables_extracted_total",
    "Total number of tables extracted from documents"
)

PAGES_PROCESSED_TOTAL = Counter(
    "pages_processed_total",
    "Total number of document pages processed"
)

OCR_DURATION_SECONDS = Histogram(
    "ocr_duration_seconds",
    "Time spent on OCR processing per page",
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0]
)

# ============================================
# Field Extraction Metrics
# ============================================
FIELDS_EXTRACTED_TOTAL = Counter(
    "fields_extracted_total",
    "Total number of fields extracted",
    ["field_name", "source"]
)

FIELD_CONFIDENCE = Histogram(
    "field_confidence",
    "Confidence scores for extracted fields",
    ["field_name"],
    buckets=[0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
)

LOW_CONFIDENCE_FIELDS_TOTAL = Counter(
    "low_confidence_fields_total",
    "Number of fields with low confidence requiring review",
    ["field_name"]
)

# ============================================
# Audit Engine Metrics
# ============================================
AUDITS_COMPLETED_TOTAL = Counter(
    "audits_completed_total",
    "Total number of audits completed"
)

AUDIT_DURATION_SECONDS = Histogram(
    "audit_duration_seconds",
    "Time spent on audit processing",
    buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0]
)

AUDIT_ISSUES_DETECTED_TOTAL = Counter(
    "audit_issues_detected_total",
    "Total number of audit issues detected",
    ["issue_type", "severity"]
)

AUDIT_SCORE = Histogram(
    "audit_score",
    "Distribution of audit scores",
    buckets=[0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
)

POTENTIAL_SAVINGS_DOLLARS = Counter(
    "potential_savings_dollars_total",
    "Total potential savings identified in dollars"
)

# ============================================
# Review Task Metrics
# ============================================
REVIEW_TASKS_TOTAL = Counter(
    "review_tasks_total",
    "Total number of review tasks created"
)

REVIEW_TASKS_COMPLETED = Counter(
    "review_tasks_completed_total",
    "Total number of review tasks completed",
    ["result"]  # approved, rejected
)

REVIEW_TASKS_PENDING = Gauge(
    "review_tasks_pending",
    "Number of pending review tasks"
)

# ============================================
# Celery Queue Metrics
# ============================================
CELERY_QUEUE_LENGTH = Gauge(
    "celery_queue_length",
    "Number of tasks in Celery queue",
    ["queue_name"]
)

CELERY_ACTIVE_WORKERS = Gauge(
    "celery_active_workers",
    "Number of active Celery workers"
)

CELERY_TASKS_TOTAL = Counter(
    "celery_tasks_total",
    "Total number of Celery tasks processed",
    ["task_name", "status"]
)

CELERY_TASK_DURATION_SECONDS = Histogram(
    "celery_task_duration_seconds",
    "Duration of Celery tasks",
    ["task_name"],
    buckets=[0.1, 0.5, 1.0, 5.0, 10.0, 30.0, 60.0, 300.0]
)

# ============================================
# Negotiation Metrics
# ============================================
NEGOTIATIONS_TOTAL = Counter(
    "negotiations_total",
    "Total number of negotiation letters generated",
    ["tone", "channel"]
)

NEGOTIATIONS_SENT_TOTAL = Counter(
    "negotiations_sent_total",
    "Total number of negotiations sent",
    ["channel", "status"]
)

# ============================================
# HTTP Request Metrics
# ============================================
HTTP_REQUESTS_TOTAL = Counter(
    "http_requests_total",
    "Total number of HTTP requests",
    ["method", "endpoint", "status_code"]
)

HTTP_REQUEST_DURATION_SECONDS = Histogram(
    "http_request_duration_seconds",
    "Duration of HTTP requests",
    ["method", "endpoint"],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
)

# ============================================
# Database Metrics
# ============================================
DB_CONNECTIONS_ACTIVE = Gauge(
    "db_connections_active",
    "Number of active database connections"
)

DB_QUERY_DURATION_SECONDS = Histogram(
    "db_query_duration_seconds",
    "Duration of database queries",
    buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0]
)

# ============================================
# Metrics Router
# ============================================
router = APIRouter()


@router.get("/metrics", include_in_schema=False)
async def metrics():
    """
    Expose Prometheus metrics endpoint.
    
    Returns metrics in Prometheus text format.
    """
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )


# ============================================
# Helper Functions
# ============================================
def track_upload(status: str, content_type: str, size_bytes: int):
    """Track an upload event."""
    UPLOADS_TOTAL.labels(status=status, content_type=content_type).inc()
    if size_bytes > 0:
        UPLOAD_SIZE_BYTES.observe(size_bytes)


def track_parse_duration(duration_seconds: float, status: str, document_type: str):
    """Track document parsing duration."""
    PARSE_DURATION_SECONDS.observe(duration_seconds)
    DOCUMENTS_PARSED_TOTAL.labels(status=status, document_type=document_type).inc()


def track_field_extraction(field_name: str, confidence: float, source: str):
    """Track field extraction metrics."""
    FIELDS_EXTRACTED_TOTAL.labels(field_name=field_name, source=source).inc()
    FIELD_CONFIDENCE.labels(field_name=field_name).observe(confidence)
    
    if confidence < 0.75:
        LOW_CONFIDENCE_FIELDS_TOTAL.labels(field_name=field_name).inc()


def track_audit_result(score: int, issues: list, duration_seconds: float, potential_savings: float):
    """Track audit results."""
    AUDITS_COMPLETED_TOTAL.inc()
    AUDIT_DURATION_SECONDS.observe(duration_seconds)
    AUDIT_SCORE.observe(score)
    
    if potential_savings > 0:
        POTENTIAL_SAVINGS_DOLLARS.inc(potential_savings)
    
    for issue in issues:
        AUDIT_ISSUES_DETECTED_TOTAL.labels(
            issue_type=issue.get("type", "unknown"),
            severity=issue.get("severity", "unknown")
        ).inc()


def track_celery_task(task_name: str, status: str, duration_seconds: float):
    """Track Celery task execution."""
    CELERY_TASKS_TOTAL.labels(task_name=task_name, status=status).inc()
    CELERY_TASK_DURATION_SECONDS.labels(task_name=task_name).observe(duration_seconds)


def update_celery_queue_length(queue_name: str, length: int):
    """Update Celery queue length gauge."""
    CELERY_QUEUE_LENGTH.labels(queue_name=queue_name).set(length)


def track_http_request(method: str, endpoint: str, status_code: int, duration_seconds: float):
    """Track HTTP request metrics."""
    HTTP_REQUESTS_TOTAL.labels(
        method=method,
        endpoint=endpoint,
        status_code=str(status_code)
    ).inc()
    HTTP_REQUEST_DURATION_SECONDS.labels(
        method=method,
        endpoint=endpoint
    ).observe(duration_seconds)

