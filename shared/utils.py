"""
Utilitaires partagés pour les services Hey Hi
- Configuration CORS et timeouts
- Validation des requêtes
- Headers de sécurité
- Rate limiting basique
"""
import os
import time
from typing import List
from collections import defaultdict

def get_allowed_origins(default="*") -> List[str]:
    """Parse les origines CORS depuis l'environnement"""
    raw = os.getenv("ALLOWED_ORIGINS", default)
    origins = [o.strip() for o in raw.split(",") if o.strip()]
    return origins if origins else [default]

def get_timeouts() -> tuple[float, float]:
    """Récupère les timeouts de connexion et lecture"""
    connect = float(os.getenv("LLM_TIMEOUT_CONNECT", "10"))
    read = float(os.getenv("LLM_TIMEOUT_READ", "70"))
    return connect, read

def get_security_headers() -> dict:
    """
    Headers de sécurité recommandés pour les services API
    https://owasp.org/www-project-secure-headers/
    """
    return {
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "X-XSS-Protection": "1; mode=block",
        "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
        "Content-Security-Policy": "default-src 'self'",
        "Referrer-Policy": "strict-origin-when-cross-origin",
        "Permissions-Policy": "geolocation=(), microphone=(), camera=()"
    }

class SimpleRateLimiter:
    """
    Rate limiter simple en mémoire (par IP)
    Note: En production, utiliser Redis ou un service dédié
    """
    def __init__(self, max_requests: int = 60, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = defaultdict(list)
    
    def is_allowed(self, identifier: str) -> tuple[bool, dict]:
        """
        Vérifie si la requête est autorisée
        Returns: (is_allowed, info_dict)
        """
        now = time.time()
        window_start = now - self.window_seconds
        
        # Nettoyer les anciennes requêtes
        self.requests[identifier] = [
            req_time for req_time in self.requests[identifier]
            if req_time > window_start
        ]
        
        current_count = len(self.requests[identifier])
        
        if current_count >= self.max_requests:
            oldest_request = min(self.requests[identifier])
            retry_after = int(oldest_request + self.window_seconds - now) + 1
            return False, {
                "error": "RATE_LIMIT_EXCEEDED",
                "message": f"Limite de {self.max_requests} requêtes par {self.window_seconds}s atteinte",
                "retry_after_seconds": retry_after,
                "current_count": current_count,
                "limit": self.max_requests
            }
        
        self.requests[identifier].append(now)
        remaining = self.max_requests - (current_count + 1)
        
        return True, {
            "remaining": remaining,
            "limit": self.max_requests,
            "window_seconds": self.window_seconds
        }
    
    def get_headers(self, identifier: str) -> dict:
        """Génère les headers X-RateLimit standard"""
        _, info = self.is_allowed(identifier)
        headers = {
            "X-RateLimit-Limit": str(self.max_requests),
            "X-RateLimit-Window": str(self.window_seconds)
        }
        if "remaining" in info:
            headers["X-RateLimit-Remaining"] = str(info["remaining"])
        if "retry_after_seconds" in info:
            headers["Retry-After"] = str(info["retry_after_seconds"])
        return headers

def validate_request_size(content: str, max_size: int = 100000) -> tuple[bool, str]:
    """Valide la taille d'une requête"""
    size = len(content.encode('utf-8'))
    if size > max_size:
        return False, f"Requête trop volumineuse: {size} bytes (max: {max_size})"
    return True, ""

def sanitize_input(text: str, max_length: int = 50000) -> str:
    """Nettoie et tronque l'input utilisateur"""
    if not text:
        return ""
    # Supprimer caractères de contrôle sauf newlines/tabs
    cleaned = "".join(char for char in text if char.isprintable() or char in ['\n', '\t', '\r'])
    return cleaned[:max_length]

