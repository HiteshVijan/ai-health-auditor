"""
Sentry Error Handling Middleware.

Provides enhanced error capturing for FastAPI requests with
additional context and user information.
"""

import logging
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

import sentry_sdk
from app.core.sentry import set_user_context, add_breadcrumb

logger = logging.getLogger(__name__)


class SentryContextMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add request context to Sentry events.
    
    Enriches Sentry events with:
    - User context (if authenticated)
    - Request metadata
    - Custom breadcrumbs
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and add Sentry context."""
        
        # Add request breadcrumb
        add_breadcrumb(
            message=f"{request.method} {request.url.path}",
            category="http",
            level="info",
            data={
                "method": request.method,
                "path": request.url.path,
                "query": str(request.query_params),
            },
        )
        
        # Set user context if authenticated
        user = getattr(request.state, "user", None)
        if user:
            set_user_context(
                user_id=str(user.id),
                email=getattr(user, "email", None),
                username=getattr(user, "username", None),
            )
        
        # Set request tags
        with sentry_sdk.configure_scope() as scope:
            scope.set_tag("request.method", request.method)
            scope.set_tag("request.path", request.url.path)
            
            # Add custom context
            scope.set_context("request", {
                "url": str(request.url),
                "method": request.method,
                "headers": dict(request.headers),
                "client_ip": request.client.host if request.client else None,
            })
        
        try:
            response = await call_next(request)
            
            # Add response breadcrumb
            add_breadcrumb(
                message=f"Response: {response.status_code}",
                category="http",
                level="info" if response.status_code < 400 else "warning",
                data={"status_code": response.status_code},
            )
            
            return response
            
        except Exception as e:
            # Let Sentry's FastAPI integration handle the exception
            # but add extra context first
            with sentry_sdk.configure_scope() as scope:
                scope.set_context("error_context", {
                    "endpoint": request.url.path,
                    "method": request.method,
                })
            raise

