"""
Tests unitaires pour shared/chat_proxy.py
"""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from fastapi import HTTPException
from shared.chat_proxy import (
    Message, ChatRequest, CircuitBreaker, ChatMetrics,
    call_openai_with_retry, handle_chat_request, metrics
)

# Tests des modèles Pydantic
def test_message_validation():
    """Teste la validation des messages"""
    # Message valide
    msg = Message(role="user", content="Hello")
    assert msg.role == "user"
    assert msg.content == "Hello"
    
    # Rôle invalide
    with pytest.raises(ValueError):
        Message(role="invalid", content="Hello")
    
    # Message trop long
    long_content = "x" * 51000
    with pytest.raises(ValueError):
        Message(role="user", content=long_content)

def test_chat_request_validation():
    """Teste la validation des requêtes chat"""
    # Requête valide
    req = ChatRequest(messages=[
        Message(role="user", content="Hello")
    ])
    assert len(req.messages) == 1
    
    # Messages vide
    with pytest.raises(ValueError):
        ChatRequest(messages=[])
    
    # Trop de messages
    many_messages = [Message(role="user", content="test")] * 101
    with pytest.raises(ValueError):
        ChatRequest(messages=many_messages)
    
    # Temperature hors limites
    with pytest.raises(ValueError):
        ChatRequest(
            messages=[Message(role="user", content="test")],
            temperature=3.0
        )

# Tests du Circuit Breaker
def test_circuit_breaker_states():
    """Teste les états du circuit breaker"""
    cb = CircuitBreaker(failure_threshold=3, timeout=1)
    
    # État initial: closed
    assert cb.state == "closed"
    assert cb.can_execute() is True
    
    # Enregistrer des échecs
    cb.record_failure()
    cb.record_failure()
    assert cb.state == "closed"
    
    # Atteindre le seuil -> open
    cb.record_failure()
    assert cb.state == "open"
    assert cb.can_execute() is False
    
    # Succès réinitialise
    cb.record_success()
    assert cb.state == "closed"
    assert cb.failure_count == 0

def test_circuit_breaker_timeout():
    """Teste le timeout du circuit breaker"""
    import time
    cb = CircuitBreaker(failure_threshold=2, timeout=1)
    
    # Ouvrir le circuit
    cb.record_failure()
    cb.record_failure()
    assert cb.state == "open"
    assert cb.can_execute() is False
    
    # Attendre le timeout
    time.sleep(1.1)
    assert cb.can_execute() is True
    assert cb.state == "half_open"

# Tests des métriques
def test_metrics_tracking():
    """Teste le tracking des métriques"""
    m = ChatMetrics()
    
    # Enregistrer succès
    m.record_request(True, 1.5, tokens=100)
    assert m.total_requests == 1
    assert m.successful_requests == 1
    assert m.total_tokens == 100
    
    # Enregistrer échec
    m.record_request(False, 0.5, error_type="timeout")
    assert m.total_requests == 2
    assert m.failed_requests == 1
    assert m.errors_by_type["timeout"] == 1
    
    # Statistiques
    stats = m.get_stats()
    assert stats["total_requests"] == 2
    assert stats["success_rate"] == 50.0
    assert stats["total_tokens"] == 100
    assert "average_latency_seconds" in stats

# Tests de l'appel OpenAI avec retry
@pytest.mark.asyncio
async def test_call_openai_success():
    """Teste un appel OpenAI réussi"""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "choices": [{"message": {"content": "Hello"}}],
        "usage": {"total_tokens": 50}
    }
    
    with patch('httpx.AsyncClient') as mock_client:
        mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)
        
        result = await call_openai_with_retry(
            api_key="test-key",
            messages=[{"role": "user", "content": "Hi"}],
            model="gpt-4o-mini",
            connect_timeout=10,
            read_timeout=70
        )
        
        assert "choices" in result
        assert result["usage"]["total_tokens"] == 50

@pytest.mark.asyncio
async def test_call_openai_retry_on_500():
    """Teste le retry sur erreur 500"""
    mock_response = Mock()
    mock_response.status_code = 500
    mock_response.text = "Internal Server Error"
    
    with patch('httpx.AsyncClient') as mock_client:
        mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)
        
        with pytest.raises(HTTPException) as exc_info:
            await call_openai_with_retry(
                api_key="test-key",
                messages=[{"role": "user", "content": "Hi"}],
                model="gpt-4o-mini",
                connect_timeout=10,
                read_timeout=70
            )
        
        assert exc_info.value.status_code == 502
        # Vérifier que plusieurs tentatives ont été faites
        assert mock_client.return_value.__aenter__.return_value.post.call_count == 3

@pytest.mark.asyncio
async def test_call_openai_no_retry_on_400():
    """Teste qu'on ne retry pas sur erreur 400"""
    mock_response = Mock()
    mock_response.status_code = 400
    mock_response.text = "Bad Request"
    
    with patch('httpx.AsyncClient') as mock_client:
        mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)
        
        with pytest.raises(HTTPException) as exc_info:
            await call_openai_with_retry(
                api_key="test-key",
                messages=[{"role": "user", "content": "Hi"}],
                model="gpt-4o-mini",
                connect_timeout=10,
                read_timeout=70
            )
        
        assert exc_info.value.status_code == 400
        # Une seule tentative
        assert mock_client.return_value.__aenter__.return_value.post.call_count == 1

@pytest.mark.asyncio
async def test_handle_chat_request_no_api_key():
    """Teste la gestion d'une clé API manquante"""
    request = ChatRequest(messages=[Message(role="user", content="Hi")])
    
    response = await handle_chat_request(
        request=request,
        api_key="",
        default_model="gpt-4o-mini",
        connect_timeout=10,
        read_timeout=70
    )
    
    assert response.status_code == 500
    assert "MISSING_OPENAI_API_KEY" in str(response.body)

@pytest.mark.asyncio
async def test_handle_chat_request_success():
    """Teste un handler de chat réussi"""
    request = ChatRequest(messages=[Message(role="user", content="Hi")])
    
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "choices": [{"message": {"content": "Hello!"}}],
        "usage": {"total_tokens": 25},
        "model": "gpt-4o-mini"
    }
    
    with patch('httpx.AsyncClient') as mock_client:
        mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)
        
        result = await handle_chat_request(
            request=request,
            api_key="test-key",
            default_model="gpt-4o-mini",
            connect_timeout=10,
            read_timeout=70
        )
        
        assert result["provider"] == "openai"
        assert "latency_seconds" in result
        assert result["usage"]["total_tokens"] == 25

# Fixture pour réinitialiser le circuit breaker entre les tests
@pytest.fixture(autouse=True)
def reset_circuit_breaker():
    """Reset le circuit breaker avant chaque test"""
    from shared.chat_proxy import circuit_breaker
    circuit_breaker.state = "closed"
    circuit_breaker.failure_count = 0
    circuit_breaker.last_failure_time = 0
    yield

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
