"""
Logique commune pour les proxies chat OpenAI avec:
- Retry automatique avec backoff exponentiel
- Circuit breaker basique
- Validation des inputs
- Métriques intégrées
- Gestion d'erreurs améliorée
"""
import os, time, asyncio, httpx
from typing import List, Dict, Any, Optional
from fastapi import HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator

# Configuration
DEFAULT_MODEL = "gpt-4o-mini"
OPENAI_CHAT_URL = "https://api.openai.com/v1/chat/completions"
MAX_MESSAGE_LENGTH = 50000
MAX_MESSAGES_COUNT = 100
MAX_RETRIES = 3
INITIAL_BACKOFF = 1.0

class Message(BaseModel):
    role: str
    content: str
    
    @field_validator('role')
    @classmethod
    def validate_role(cls, v):
        if v not in ['system', 'user', 'assistant', 'function', 'tool']:
            raise ValueError('Invalid role')
        return v
    
    @field_validator('content')
    @classmethod
    def validate_content(cls, v):
        if len(v) > MAX_MESSAGE_LENGTH:
            raise ValueError(f'Message too long (max {MAX_MESSAGE_LENGTH} chars)')
        return v

class ChatRequest(BaseModel):
    messages: List[Message] = Field(..., min_length=1, max_length=MAX_MESSAGES_COUNT)
    model: Optional[str] = None
    session_id: Optional[str] = None
    project_id: Optional[str] = None
    temperature: Optional[float] = Field(None, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(None, ge=1, le=16000)

class CircuitBreaker:
    """Circuit breaker basique pour éviter surcharge sur échecs répétés"""
    def __init__(self, failure_threshold=5, timeout=60):
        self.failure_count = 0
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.last_failure_time = 0
        self.state = "closed"  # closed, open, half_open
    
    def can_execute(self):
        if self.state == "closed":
            return True
        if self.state == "open":
            if time.time() - self.last_failure_time > self.timeout:
                self.state = "half_open"
                return True
            return False
        return True  # half_open
    
    def record_success(self):
        self.failure_count = 0
        self.state = "closed"
    
    def record_failure(self):
        self.failure_count += 1
        self.last_failure_time = time.time()
        if self.failure_count >= self.failure_threshold:
            self.state = "open"

# Instance globale du circuit breaker
circuit_breaker = CircuitBreaker()

class ChatMetrics:
    """Métriques simples pour monitoring"""
    def __init__(self):
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0
        self.total_tokens = 0
        self.total_latency = 0.0
        self.errors_by_type = {}
    
    def record_request(self, success: bool, latency: float, tokens: int = 0, error_type: str = None):
        self.total_requests += 1
        if success:
            self.successful_requests += 1
            self.total_tokens += tokens
        else:
            self.failed_requests += 1
            if error_type:
                self.errors_by_type[error_type] = self.errors_by_type.get(error_type, 0) + 1
        self.total_latency += latency
    
    def get_stats(self):
        avg_latency = self.total_latency / self.total_requests if self.total_requests > 0 else 0
        success_rate = self.successful_requests / self.total_requests if self.total_requests > 0 else 0
        return {
            "total_requests": self.total_requests,
            "successful_requests": self.successful_requests,
            "failed_requests": self.failed_requests,
            "success_rate": round(success_rate * 100, 2),
            "total_tokens": self.total_tokens,
            "average_latency_seconds": round(avg_latency, 3),
            "errors_by_type": self.errors_by_type,
            "circuit_breaker_state": circuit_breaker.state
        }

# Instance globale des métriques
metrics = ChatMetrics()

async def call_openai_with_retry(
    api_key: str,
    messages: List[Dict[str, str]],
    model: str,
    connect_timeout: float,
    read_timeout: float,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None
) -> Dict[str, Any]:
    """
    Appelle l'API OpenAI avec retry automatique et backoff exponentiel
    """
    if not circuit_breaker.can_execute():
        raise HTTPException(
            status_code=503,
            detail={
                "error": "CIRCUIT_BREAKER_OPEN",
                "message": "Service temporairement indisponible, trop d'échecs récents"
            }
        )
    
    payload = {
        "model": model,
        "messages": messages,
        "stream": False,
    }
    if temperature is not None:
        payload["temperature"] = temperature
    if max_tokens is not None:
        payload["max_tokens"] = max_tokens
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    timeout = httpx.Timeout(
        connect=connect_timeout,
        read=read_timeout,
        write=read_timeout,
        pool=connect_timeout
    )
    
    last_error = None
    backoff = INITIAL_BACKOFF
    
    for attempt in range(MAX_RETRIES):
        try:
            async with httpx.AsyncClient(timeout=timeout, http2=False) as client:
                response = await client.post(OPENAI_CHAT_URL, headers=headers, json=payload)
            
            if response.status_code == 200:
                circuit_breaker.record_success()
                return response.json()
            
            # Erreurs non-retriables (ne pas retry)
            if response.status_code in [400, 401, 403, 404]:
                circuit_breaker.record_failure()
                error_detail = {
                    "error": "OPENAI_CLIENT_ERROR",
                    "status": response.status_code,
                    "body": response.text[:500]
                }
                raise HTTPException(
                    status_code=response.status_code,
                    detail=error_detail
                )
            
            # Erreurs retriables (429, 5xx)
            last_error = {
                "error": "OPENAI_SERVER_ERROR",
                "status": response.status_code,
                "body": response.text[:500],
                "attempt": attempt + 1
            }
            
            if attempt < MAX_RETRIES - 1:
                await asyncio.sleep(backoff)
                backoff *= 2
            
        except httpx.TimeoutException as e:
            last_error = {
                "error": "OPENAI_TIMEOUT",
                "detail": str(e),
                "attempt": attempt + 1
            }
            if attempt < MAX_RETRIES - 1:
                await asyncio.sleep(backoff)
                backoff *= 2
        
        except httpx.NetworkError as e:
            last_error = {
                "error": "OPENAI_NETWORK_ERROR",
                "detail": str(e),
                "attempt": attempt + 1
            }
            if attempt < MAX_RETRIES - 1:
                await asyncio.sleep(backoff)
                backoff *= 2
        
        except HTTPException:
            # Re-raise HTTPException sans retry (erreurs client 4xx)
            raise
        
        except Exception as e:
            last_error = {
                "error": "OPENAI_UNKNOWN_ERROR",
                "detail": str(e),
                "attempt": attempt + 1
            }
            if attempt < MAX_RETRIES - 1:
                await asyncio.sleep(backoff)
                backoff *= 2
    
    # Tous les retries ont échoué
    circuit_breaker.record_failure()
    raise HTTPException(
        status_code=502,
        detail={
            **last_error,
            "message": f"Échec après {MAX_RETRIES} tentatives"
        }
    )

async def handle_chat_request(
    request: ChatRequest,
    api_key: str,
    default_model: str,
    connect_timeout: float,
    read_timeout: float
) -> Dict[str, Any]:
    """
    Handler principal pour les requêtes chat avec métriques et gestion d'erreurs
    """
    start_time = time.time()
    
    if not api_key:
        metrics.record_request(False, time.time() - start_time, error_type="missing_api_key")
        return JSONResponse(
            status_code=500,
            content={
                "error": "MISSING_OPENAI_API_KEY",
                "message": "La clé API OpenAI n'est pas configurée"
            }
        )
    
    try:
        messages = [{"role": m.role, "content": m.content} for m in request.messages]
        model = request.model or default_model
        
        result = await call_openai_with_retry(
            api_key=api_key,
            messages=messages,
            model=model,
            connect_timeout=connect_timeout,
            read_timeout=read_timeout,
            temperature=request.temperature,
            max_tokens=request.max_tokens
        )
        
        latency = time.time() - start_time
        tokens = result.get("usage", {}).get("total_tokens", 0)
        metrics.record_request(True, latency, tokens)
        
        return {
            "provider": "openai",
            "choices": result.get("choices", []),
            "usage": result.get("usage", {}),
            "model": result.get("model"),
            "latency_seconds": round(latency, 3)
        }
    
    except HTTPException as e:
        latency = time.time() - start_time
        error_type = e.detail.get("error") if isinstance(e.detail, dict) else "http_exception"
        metrics.record_request(False, latency, error_type=error_type)
        raise
    
    except Exception as e:
        latency = time.time() - start_time
        metrics.record_request(False, latency, error_type="unexpected_error")
        return JSONResponse(
            status_code=500,
            content={
                "error": "UNEXPECTED_ERROR",
                "message": "Erreur inattendue lors du traitement",
                "detail": str(e)
            }
        )
