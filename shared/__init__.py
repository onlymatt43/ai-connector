"""
Script d'initialisation du package shared pour les imports
"""
from .utils import (
    get_allowed_origins,
    get_timeouts,
    get_security_headers,
    SimpleRateLimiter,
    validate_request_size,
    sanitize_input
)

from .chat_proxy import (
    Message,
    ChatRequest,
    CircuitBreaker,
    ChatMetrics,
    call_openai_with_retry,
    handle_chat_request,
    metrics,
    circuit_breaker
)

__all__ = [
    # utils
    'get_allowed_origins',
    'get_timeouts',
    'get_security_headers',
    'SimpleRateLimiter',
    'validate_request_size',
    'sanitize_input',
    # chat_proxy
    'Message',
    'ChatRequest',
    'CircuitBreaker',
    'ChatMetrics',
    'call_openai_with_retry',
    'handle_chat_request',
    'metrics',
    'circuit_breaker',
]
