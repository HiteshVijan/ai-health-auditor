"""
Prometheus Metrics Middleware.

Automatically tracks HTTP request metrics for all endpoints.
"""

import time
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app.core.metrics import track_http_request


class MetricsMiddleware(BaseHTTPMiddleware):
    """
    Middleware to track HTTP request metrics.
    
    Records request count, duration, and status codes for all endpoints.
    """
    
    # Endpoints to exclude from metrics (to avoid recursion)
    EXCLUDED_PATHS = {"/metrics", "/health", "/ready"}
    
    async def dispatch(self, request: Request, call_next) -> Response:
        """Process request and track metrics."""
        # Skip excluded paths
        if request.url.path in self.EXCLUDED_PATHS:
            return await call_next(request)
        
        # Track request timing
        start_time = time.perf_counter()
        
        try:
            response = await call_next(request)
            status_code = response.status_code
        except Exception as e:
            status_code = 500
            raise
        finally:
            # Calculate duration
            duration = time.perf_counter() - start_time
            
            # Normalize endpoint path (replace IDs with placeholders)
            endpoint = self._normalize_path(request.url.path)
            
            # Track metrics
            track_http_request(
                method=request.method,
                endpoint=endpoint,
                status_code=status_code,
                duration_seconds=duration
            )
        
        return response
    
    def _normalize_path(self, path: str) -> str:
        """
        Normalize path by replacing dynamic segments with placeholders.
        
        E.g., /api/v1/documents/123 -> /api/v1/documents/{id}
        """
        parts = path.split("/")
        normalized = []
        
        for part in parts:
            if part.isdigit():
                normalized.append("{id}")
            elif len(part) == 36 and "-" in part:  # UUID
                normalized.append("{uuid}")
            else:
                normalized.append(part)
        
        return "/".join(normalized)

