"""
Sentry Integration Module.

Configures Sentry for error tracking, performance monitoring,
and logging integration for the backend application.
"""

import logging
import os
from typing import Optional, Dict, Any, Callable
from functools import wraps

import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.starlette import StarletteIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
from sentry_sdk.integrations.celery import CeleryIntegration
from sentry_sdk.integrations.redis import RedisIntegration
from sentry_sdk.integrations.logging import LoggingIntegration

logger = logging.getLogger(__name__)


def init_sentry(
    dsn: Optional[str] = None,
    environment: Optional[str] = None,
    release: Optional[str] = None,
    sample_rate: float = 1.0,
    traces_sample_rate: float = 0.1,
    profiles_sample_rate: float = 0.1,
    enable_tracing: bool = True,
) -> None:
    """
    Initialize Sentry SDK with optimal configuration for FastAPI backend.
    
    Args:
        dsn: Sentry DSN (Data Source Name). Falls back to SENTRY_DSN env var.
        environment: Environment name (production, staging, development).
        release: Application release/version string.
        sample_rate: Error event sample rate (0.0 to 1.0).
        traces_sample_rate: Performance transaction sample rate.
        profiles_sample_rate: Profiling sample rate.
        enable_tracing: Whether to enable performance tracing.
    """
    sentry_dsn = dsn or os.getenv("SENTRY_DSN")
    
    if not sentry_dsn:
        logger.warning("Sentry DSN not configured. Error tracking disabled.")
        return
    
    env = environment or os.getenv("ENVIRONMENT", "development")
    app_release = release or os.getenv("APP_VERSION", "1.0.0")
    
    # Configure logging integration
    logging_integration = LoggingIntegration(
        level=logging.WARNING,  # Capture warnings and above
        event_level=logging.ERROR,  # Send errors as Sentry events
    )
    
    sentry_sdk.init(
        dsn=sentry_dsn,
        environment=env,
        release=f"ai-health-auditor-backend@{app_release}",
        
        # Sample rates
        sample_rate=sample_rate,
        traces_sample_rate=traces_sample_rate if enable_tracing else 0.0,
        profiles_sample_rate=profiles_sample_rate if enable_tracing else 0.0,
        
        # Integrations
        integrations=[
            FastApiIntegration(transaction_style="endpoint"),
            StarletteIntegration(transaction_style="endpoint"),
            SqlalchemyIntegration(),
            CeleryIntegration(),
            RedisIntegration(),
            logging_integration,
        ],
        
        # Data scrubbing
        send_default_pii=False,  # Don't send PII by default
        
        # Before send hook for filtering/enriching events
        before_send=before_send_handler,
        before_send_transaction=before_send_transaction_handler,
        
        # Attach stacktrace to log messages
        attach_stacktrace=True,
        
        # Include local variables in stack traces
        include_local_variables=True,
        
        # Max breadcrumbs to store
        max_breadcrumbs=50,
    )
    
    logger.info(f"Sentry initialized for environment: {env}")


def before_send_handler(event: Dict[str, Any], hint: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Process events before sending to Sentry.
    
    Used for:
    - Filtering out noisy/irrelevant errors
    - Scrubbing sensitive data
    - Enriching events with additional context
    """
    # Filter out specific exceptions
    if "exc_info" in hint:
        exc_type, exc_value, _ = hint["exc_info"]
        
        # Ignore common non-critical exceptions
        ignored_exceptions = (
            "ConnectionResetError",
            "BrokenPipeError",
            "ClientDisconnected",
        )
        
        if exc_type.__name__ in ignored_exceptions:
            return None
    
    # Scrub sensitive headers
    if "request" in event:
        headers = event["request"].get("headers", {})
        sensitive_headers = ["authorization", "x-api-key", "cookie"]
        for header in sensitive_headers:
            if header in headers:
                headers[header] = "[Filtered]"
    
    return event


def before_send_transaction_handler(
    event: Dict[str, Any], 
    hint: Dict[str, Any]
) -> Optional[Dict[str, Any]]:
    """
    Process transactions before sending to Sentry.
    
    Used for filtering out health check and metrics endpoints.
    """
    # Filter out noisy endpoints
    transaction_name = event.get("transaction", "")
    
    ignored_endpoints = [
        "/health",
        "/ready",
        "/metrics",
        "/favicon.ico",
    ]
    
    for endpoint in ignored_endpoints:
        if endpoint in transaction_name:
            return None
    
    return event


def capture_exception(
    error: Exception,
    context: Optional[Dict[str, Any]] = None,
    tags: Optional[Dict[str, str]] = None,
    level: str = "error",
) -> Optional[str]:
    """
    Capture an exception with additional context.
    
    Args:
        error: The exception to capture.
        context: Additional context data.
        tags: Tags for categorization.
        level: Severity level (error, warning, info).
    
    Returns:
        Sentry event ID if captured, None otherwise.
    """
    with sentry_sdk.push_scope() as scope:
        if context:
            for key, value in context.items():
                scope.set_context(key, value)
        
        if tags:
            for key, value in tags.items():
                scope.set_tag(key, value)
        
        scope.level = level
        
        event_id = sentry_sdk.capture_exception(error)
        
        logger.error(
            f"Exception captured in Sentry: {type(error).__name__} - {str(error)[:100]}",
            extra={"sentry_event_id": event_id}
        )
        
        return event_id


def capture_message(
    message: str,
    level: str = "info",
    context: Optional[Dict[str, Any]] = None,
    tags: Optional[Dict[str, str]] = None,
) -> Optional[str]:
    """
    Capture a message event in Sentry.
    
    Args:
        message: The message to capture.
        level: Severity level (error, warning, info, debug).
        context: Additional context data.
        tags: Tags for categorization.
    
    Returns:
        Sentry event ID if captured, None otherwise.
    """
    with sentry_sdk.push_scope() as scope:
        if context:
            for key, value in context.items():
                scope.set_context(key, value)
        
        if tags:
            for key, value in tags.items():
                scope.set_tag(key, value)
        
        scope.level = level
        
        return sentry_sdk.capture_message(message)


def set_user_context(
    user_id: Optional[str] = None,
    email: Optional[str] = None,
    username: Optional[str] = None,
) -> None:
    """
    Set user context for subsequent events.
    
    Args:
        user_id: Unique user identifier.
        email: User email (optional).
        username: Username (optional).
    """
    sentry_sdk.set_user({
        "id": user_id,
        "email": email,
        "username": username,
    })


def add_breadcrumb(
    message: str,
    category: str = "custom",
    level: str = "info",
    data: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Add a breadcrumb for debugging context.
    
    Args:
        message: Breadcrumb message.
        category: Category for grouping.
        level: Severity level.
        data: Additional data.
    """
    sentry_sdk.add_breadcrumb(
        message=message,
        category=category,
        level=level,
        data=data or {},
    )


def track_llm_error(func: Callable) -> Callable:
    """
    Decorator to track LLM API errors with rich context.
    
    Usage:
        @track_llm_error
        def call_openai(prompt: str) -> str:
            ...
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            capture_exception(
                error=e,
                context={
                    "llm": {
                        "function": func.__name__,
                        "args_count": len(args),
                        "kwargs_keys": list(kwargs.keys()),
                    }
                },
                tags={
                    "error_type": "llm_error",
                    "llm_function": func.__name__,
                },
            )
            raise
    
    return wrapper


def track_api_call(service_name: str) -> Callable:
    """
    Decorator to track external API call errors.
    
    Usage:
        @track_api_call("stripe")
        def charge_customer(amount: float) -> dict:
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            add_breadcrumb(
                message=f"Calling {service_name} API: {func.__name__}",
                category="api_call",
                level="info",
            )
            
            try:
                return func(*args, **kwargs)
            except Exception as e:
                capture_exception(
                    error=e,
                    context={
                        "api_call": {
                            "service": service_name,
                            "function": func.__name__,
                        }
                    },
                    tags={
                        "error_type": "api_error",
                        "service": service_name,
                    },
                )
                raise
        
        return wrapper
    return decorator


class SentrySpan:
    """
    Context manager for creating custom Sentry spans.
    
    Usage:
        with SentrySpan("process_document", description="Parse PDF") as span:
            span.set_tag("document_type", "pdf")
            # ... processing
    """
    
    def __init__(self, op: str, description: Optional[str] = None):
        self.op = op
        self.description = description
        self.span = None
    
    def __enter__(self):
        self.span = sentry_sdk.start_span(
            op=self.op,
            description=self.description,
        )
        return self.span
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.span:
            if exc_type:
                self.span.set_status("internal_error")
            else:
                self.span.set_status("ok")
            self.span.finish()
        return False

