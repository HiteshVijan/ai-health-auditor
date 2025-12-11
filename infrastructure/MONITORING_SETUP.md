# Prometheus + Grafana Monitoring Setup

## Overview

This setup provides comprehensive monitoring for the AI Health Bill Auditor application using:
- **Prometheus**: Metrics collection and storage
- **Grafana**: Visualization and dashboards
- **Exporters**: Redis, PostgreSQL, Node, and cAdvisor metrics

## Quick Start

### 1. Start the Monitoring Stack

```bash
cd infrastructure

# Start monitoring services
docker-compose -f docker-compose.monitoring.yml up -d

# Verify services are running
docker-compose -f docker-compose.monitoring.yml ps
```

### 2. Access Dashboards

| Service | URL | Credentials |
|---------|-----|-------------|
| Grafana | http://localhost:3001 | admin / admin |
| Prometheus | http://localhost:9090 | - |

### 3. Enable Metrics in Backend

Add the metrics middleware to your FastAPI application:

```python
# backend/app/main.py

from fastapi import FastAPI
from backend.app.core.metrics import router as metrics_router
from backend.app.middleware.metrics_middleware import MetricsMiddleware

app = FastAPI()

# Add metrics middleware
app.add_middleware(MetricsMiddleware)

# Include metrics endpoint
app.include_router(metrics_router)
```

### 4. Install Dependencies

```bash
pip install prometheus-client
```

## Tracked Metrics

### Uploads
| Metric | Type | Description |
|--------|------|-------------|
| `uploads_total` | Counter | Total uploads by status and content type |
| `uploads_in_progress` | Gauge | Currently processing uploads |
| `upload_size_bytes` | Histogram | Upload file sizes |

### Document Parsing
| Metric | Type | Description |
|--------|------|-------------|
| `documents_parsed_total` | Counter | Documents parsed by status |
| `parse_duration_seconds` | Histogram | Time to parse documents |
| `tables_extracted_total` | Counter | Tables extracted from PDFs |
| `pages_processed_total` | Counter | PDF pages processed |

### Audit Engine
| Metric | Type | Description |
|--------|------|-------------|
| `audits_completed_total` | Counter | Completed audits |
| `audit_duration_seconds` | Histogram | Audit processing time |
| `audit_issues_detected_total` | Counter | Issues by type and severity |
| `audit_score` | Histogram | Distribution of audit scores |
| `potential_savings_dollars_total` | Counter | Cumulative savings identified |

### Celery Queue
| Metric | Type | Description |
|--------|------|-------------|
| `celery_queue_length` | Gauge | Tasks pending per queue |
| `celery_active_workers` | Gauge | Active worker count |
| `celery_tasks_total` | Counter | Tasks by name and status |
| `celery_task_duration_seconds` | Histogram | Task execution time |

### HTTP Requests
| Metric | Type | Description |
|--------|------|-------------|
| `http_requests_total` | Counter | Requests by method, endpoint, status |
| `http_request_duration_seconds` | Histogram | Request latency |

## Usage in Code

### Track Upload

```python
from backend.app.core.metrics import track_upload

# After successful upload
track_upload(
    status="success",
    content_type="application/pdf",
    size_bytes=file.size
)
```

### Track Document Parsing

```python
from backend.app.core.metrics import track_parse_duration

# After parsing
track_parse_duration(
    duration_seconds=elapsed_time,
    status="completed",
    document_type="pdf"
)
```

### Track Audit Results

```python
from backend.app.core.metrics import track_audit_result

# After audit
track_audit_result(
    score=result.score,
    issues=result.issues,
    duration_seconds=elapsed_time,
    potential_savings=result.potential_savings
)
```

### Track Celery Tasks

```python
from backend.app.core.metrics import track_celery_task, update_celery_queue_length

# In Celery task
@celery_app.task
def my_task():
    start = time.time()
    try:
        # Task logic
        track_celery_task("my_task", "success", time.time() - start)
    except Exception:
        track_celery_task("my_task", "failure", time.time() - start)
        raise

# Update queue length periodically
update_celery_queue_length("celery", queue_length)
```

## Grafana Dashboard

The pre-configured dashboard includes:

### Overview Row
- Total uploads, documents parsed, audits completed
- Total issues detected
- Total savings identified
- Current Celery queue length

### Uploads & Processing Row
- Upload rate over time (by status)
- Document parse time percentiles (p50, p95, p99)

### Audit Engine Row
- Issues by type (pie chart)
- Issues by severity (pie chart)
- Median audit score (bar gauge)

### Celery Queue Row
- Queue length over time
- Task rate by name and status

### HTTP Requests Row
- Request rate (total + 5xx errors)
- Request latency percentiles

## Alerting Rules

Pre-configured alerts in `prometheus/rules/alerts.yml`:

| Alert | Condition | Severity |
|-------|-----------|----------|
| HighErrorRate | >5% HTTP 5xx errors | Critical |
| SlowResponseTime | p95 > 2s | Warning |
| SlowDocumentParsing | p95 > 60s | Warning |
| HighLowConfidenceRate | >30% low confidence | Warning |
| CeleryQueueBackup | >100 pending tasks | Warning |
| NoCeleryWorkers | 0 active workers | Critical |

## Directory Structure

```
infrastructure/
├── prometheus/
│   ├── prometheus.yml           # Main config
│   └── rules/
│       └── alerts.yml           # Alerting rules
├── grafana/
│   └── provisioning/
│       ├── datasources/
│       │   └── datasources.yml  # Prometheus datasource
│       └── dashboards/
│           ├── dashboards.yml   # Dashboard provider
│           └── json/
│               └── ai-health-auditor.json  # Dashboard
├── docker-compose.monitoring.yml
└── MONITORING_SETUP.md
```

## Troubleshooting

### Prometheus can't scrape backend
1. Ensure backend exposes `/metrics` endpoint
2. Check network connectivity between containers
3. Verify `prometheus.yml` target configuration

### Grafana dashboard not loading
1. Check datasource configuration
2. Verify Prometheus is accessible at `http://prometheus:9090`
3. Check Grafana logs: `docker logs grafana`

### Missing metrics
1. Ensure metrics middleware is added to FastAPI
2. Verify `prometheus-client` is installed
3. Check that metric helper functions are called in code

## Production Considerations

1. **Security**: Enable authentication for Prometheus/Grafana
2. **Retention**: Adjust `--storage.tsdb.retention.time` for data retention
3. **Resources**: Allocate sufficient memory for Prometheus
4. **Backup**: Regular backup of Grafana dashboards and Prometheus data
5. **Alerting**: Configure AlertManager for notifications

