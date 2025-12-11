"""
Rate limiting configuration for API abuse prevention.

Uses slowapi to implement rate limiting on FastAPI endpoints.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request
from fastapi.responses import JSONResponse
from typing import Callable


def get_real_client_ip(request: Request) -> str:
    """
    Get the real client IP address, handling proxies.
    
    Checks X-Forwarded-For and X-Real-IP headers for proxy setups.
    
    Args:
        request: FastAPI request object
        
    Returns:
        str: Client IP address
    """
    # Check for forwarded headers (when behind proxy/load balancer)
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        # X-Forwarded-For can contain multiple IPs, take the first one
        return forwarded.split(",")[0].strip()
    
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip.strip()
    
    # Fall back to direct connection IP
    return get_remote_address(request)


# Create the limiter instance
limiter = Limiter(key_func=get_real_client_ip)


# Rate limit configurations for different endpoint types
RATE_LIMITS = {
    # Authentication endpoints (stricter limits to prevent brute force)
    "auth": "5/minute",
    "login": "10/minute",
    "register": "3/minute",
    
    # Document upload (resource intensive)
    "upload": "10/minute",
    
    # Audit operations (computationally intensive)
    "audit": "20/minute",
    
    # General API calls
    "default": "100/minute",
    
    # Search/list operations
    "search": "60/minute",
    
    # Negotiation letter generation (LLM calls)
    "negotiation": "10/minute",
}


def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    """
    Custom handler for rate limit exceeded errors.
    
    Args:
        request: The request that triggered the error
        exc: The rate limit exception
        
    Returns:
        JSONResponse: Error response with retry-after header
    """
    response = JSONResponse(
        status_code=429,
        content={
            "error": "rate_limit_exceeded",
            "message": f"Rate limit exceeded: {exc.detail}",
            "detail": "Too many requests. Please try again later.",
        },
    )
    
    # Add Retry-After header if available
    if hasattr(exc, "retry_after"):
        response.headers["Retry-After"] = str(exc.retry_after)
    
    return response


# Decorator functions for common rate limits
def limit_auth(func: Callable) -> Callable:
    """Apply authentication rate limit."""
    return limiter.limit(RATE_LIMITS["auth"])(func)


def limit_upload(func: Callable) -> Callable:
    """Apply upload rate limit."""
    return limiter.limit(RATE_LIMITS["upload"])(func)


def limit_audit(func: Callable) -> Callable:
    """Apply audit rate limit."""
    return limiter.limit(RATE_LIMITS["audit"])(func)


def limit_negotiation(func: Callable) -> Callable:
    """Apply negotiation rate limit."""
    return limiter.limit(RATE_LIMITS["negotiation"])(func)


def limit_default(func: Callable) -> Callable:
    """Apply default rate limit."""
    return limiter.limit(RATE_LIMITS["default"])(func)

