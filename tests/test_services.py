"""
Tests d'intégration pour les services hey-hi
"""
import pytest
from fastapi.testclient import TestClient

# Test du service coach
def test_coach_service():
    """Teste les endpoints du service coach"""
    import sys
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'hey-hi-coach-onlymatt'))
    
    from app import app
    client = TestClient(app)
    
    # Test healthz
    response = client.get("/healthz")
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    assert "service" in data
    
    # Test version
    response = client.get("/__version")
    assert response.status_code == 200
    data = response.json()
    assert "version" in data
    assert "service" in data
    
    # Test metrics
    response = client.get("/metrics")
    assert response.status_code == 200
    data = response.json()
    assert "total_requests" in data
    assert "success_rate" in data

def test_video_service():
    """Teste les endpoints du service video"""
    import sys
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'hey-hi-video-onlymatt'))
    
    from app import app
    client = TestClient(app)
    
    # Test healthz
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json()["ok"] is True
    
    # Test version
    response = client.get("/__version")
    assert response.status_code == 200
    assert "version" in response.json()

def test_chat_endpoint_no_api_key():
    """Teste l'endpoint chat sans clé API"""
    import sys
    import os
    # Backup et clear de la clé API
    original_key = os.environ.get("OPENAI_API_KEY")
    if "OPENAI_API_KEY" in os.environ:
        del os.environ["OPENAI_API_KEY"]
    
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'hey-hi-coach-onlymatt'))
    
    # Reload pour prendre en compte la clé manquante
    import importlib
    if 'app' in sys.modules:
        importlib.reload(sys.modules['app'])
    
    from app import app
    client = TestClient(app)
    
    response = client.post("/api/chat", json={
        "messages": [
            {"role": "user", "content": "Hello"}
        ]
    })
    
    assert response.status_code == 500
    data = response.json()
    assert "MISSING_OPENAI_API_KEY" in str(data)
    
    # Restore
    if original_key:
        os.environ["OPENAI_API_KEY"] = original_key

def test_chat_endpoint_validation():
    """Teste la validation de l'endpoint chat"""
    import sys
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'hey-hi-coach-onlymatt'))
    
    from app import app
    client = TestClient(app)
    
    # Messages vide
    response = client.post("/api/chat", json={
        "messages": []
    })
    assert response.status_code == 422  # Validation error
    
    # Message sans role
    response = client.post("/api/chat", json={
        "messages": [
            {"content": "Hello"}
        ]
    })
    assert response.status_code == 422
    
    # Rôle invalide
    response = client.post("/api/chat", json={
        "messages": [
            {"role": "invalid", "content": "Hello"}
        ]
    })
    assert response.status_code == 422

def test_cors_headers():
    """Teste la présence des headers CORS"""
    import sys
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'hey-hi-coach-onlymatt'))
    
    from app import app
    client = TestClient(app)
    
    response = client.options("/api/chat", headers={
        "Origin": "https://example.com",
        "Access-Control-Request-Method": "POST"
    })
    
    assert "access-control-allow-origin" in response.headers or response.status_code == 200

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
