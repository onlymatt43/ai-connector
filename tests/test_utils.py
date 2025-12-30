"""
Tests pour shared/utils.py
"""
import pytest
import time
from shared.utils import (
    get_allowed_origins, get_timeouts, get_security_headers,
    SimpleRateLimiter, validate_request_size, sanitize_input
)

def test_get_allowed_origins_default():
    """Teste la récupération des origines par défaut"""
    import os
    # Backup
    original = os.environ.get("ALLOWED_ORIGINS")
    if "ALLOWED_ORIGINS" in os.environ:
        del os.environ["ALLOWED_ORIGINS"]
    
    origins = get_allowed_origins("*")
    assert origins == ["*"]
    
    # Restore
    if original:
        os.environ["ALLOWED_ORIGINS"] = original

def test_get_allowed_origins_from_env():
    """Teste la récupération des origines depuis ENV"""
    import os
    os.environ["ALLOWED_ORIGINS"] = "https://example.com,https://test.com"
    
    origins = get_allowed_origins()
    assert len(origins) == 2
    assert "https://example.com" in origins
    assert "https://test.com" in origins

def test_get_timeouts_default():
    """Teste les timeouts par défaut"""
    import os
    # Backup
    original_connect = os.environ.get("LLM_TIMEOUT_CONNECT")
    original_read = os.environ.get("LLM_TIMEOUT_READ")
    
    if "LLM_TIMEOUT_CONNECT" in os.environ:
        del os.environ["LLM_TIMEOUT_CONNECT"]
    if "LLM_TIMEOUT_READ" in os.environ:
        del os.environ["LLM_TIMEOUT_READ"]
    
    connect, read = get_timeouts()
    assert connect == 10.0
    assert read == 70.0
    
    # Restore
    if original_connect:
        os.environ["LLM_TIMEOUT_CONNECT"] = original_connect
    if original_read:
        os.environ["LLM_TIMEOUT_READ"] = original_read

def test_get_security_headers():
    """Teste les headers de sécurité"""
    headers = get_security_headers()
    
    assert "X-Content-Type-Options" in headers
    assert "X-Frame-Options" in headers
    assert "Strict-Transport-Security" in headers
    assert headers["X-Content-Type-Options"] == "nosniff"
    assert headers["X-Frame-Options"] == "DENY"

def test_simple_rate_limiter():
    """Teste le rate limiter basique"""
    limiter = SimpleRateLimiter(max_requests=3, window_seconds=60)
    
    # Première requête: OK
    allowed, info = limiter.is_allowed("user1")
    assert allowed is True
    assert info["remaining"] == 2
    
    # Deuxième: OK
    allowed, info = limiter.is_allowed("user1")
    assert allowed is True
    assert info["remaining"] == 1
    
    # Troisième: OK
    allowed, info = limiter.is_allowed("user1")
    assert allowed is True
    assert info["remaining"] == 0
    
    # Quatrième: Bloquée
    allowed, info = limiter.is_allowed("user1")
    assert allowed is False
    assert "RATE_LIMIT_EXCEEDED" in info["error"]
    assert "retry_after_seconds" in info

def test_rate_limiter_different_users():
    """Teste que les utilisateurs sont isolés"""
    limiter = SimpleRateLimiter(max_requests=2, window_seconds=60)
    
    # User1
    allowed, _ = limiter.is_allowed("user1")
    assert allowed is True
    allowed, _ = limiter.is_allowed("user1")
    assert allowed is True
    
    # User2 peut encore faire des requêtes
    allowed, _ = limiter.is_allowed("user2")
    assert allowed is True

def test_rate_limiter_window_expiry():
    """Teste l'expiration de la fenêtre"""
    limiter = SimpleRateLimiter(max_requests=2, window_seconds=1)
    
    # Atteindre la limite
    limiter.is_allowed("user1")
    limiter.is_allowed("user1")
    allowed, _ = limiter.is_allowed("user1")
    assert allowed is False
    
    # Attendre l'expiration
    time.sleep(1.1)
    allowed, info = limiter.is_allowed("user1")
    assert allowed is True

def test_rate_limiter_headers():
    """Teste la génération des headers"""
    limiter = SimpleRateLimiter(max_requests=5, window_seconds=60)
    
    limiter.is_allowed("user1")
    headers = limiter.get_headers("user1")
    
    assert "X-RateLimit-Limit" in headers
    assert headers["X-RateLimit-Limit"] == "5"
    assert "X-RateLimit-Remaining" in headers

def test_validate_request_size():
    """Teste la validation de taille"""
    # Requête normale
    valid, msg = validate_request_size("Hello world", max_size=1000)
    assert valid is True
    assert msg == ""
    
    # Requête trop grande
    big_content = "x" * 101000
    valid, msg = validate_request_size(big_content, max_size=100000)
    assert valid is False
    assert "trop volumineuse" in msg

def test_sanitize_input():
    """Teste le nettoyage des inputs"""
    # Texte normal
    result = sanitize_input("Hello world")
    assert result == "Hello world"
    
    # Avec newlines (ok)
    result = sanitize_input("Line 1\nLine 2")
    assert result == "Line 1\nLine 2"
    
    # Tronquer si trop long
    long_text = "x" * 60000
    result = sanitize_input(long_text, max_length=50000)
    assert len(result) == 50000
    
    # Vide
    result = sanitize_input("")
    assert result == ""
    
    # None
    result = sanitize_input(None)
    assert result == ""

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
