import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from shared.utils import get_allowed_origins, get_timeouts
from shared.chat_proxy import ChatRequest, handle_chat_request, metrics

APP_NAME     = os.getenv("APP_NAME", "hey-hi-video-onlymatt")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL   = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
ALLOWED_ORIGINS = get_allowed_origins("*")
CONNECT_TIMEOUT, READ_TIMEOUT = get_timeouts()
__VERSION__ = os.getenv("APP_VERSION", "v2-resilient")

app = FastAPI(title=APP_NAME, version=__VERSION__)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["POST","GET","OPTIONS"],
    allow_headers=["Content-Type","Authorization","Accept","Cache-Control","X-Request-ID"]
)

@app.get("/__version")
async def version():
    return {"service": APP_NAME, "version": __VERSION__, "model": OPENAI_MODEL}

@app.get("/healthz")
async def healthz():
    return {
        "ok": True,
        "service": APP_NAME,
        "has_openai_key": bool(OPENAI_API_KEY),
        "model": OPENAI_MODEL,
        "allowed_origins": ALLOWED_ORIGINS
    }

@app.get("/metrics")
async def get_metrics():
    """Endpoint pour monitoring/observabilité"""
    return metrics.get_stats()

@app.post("/api/chat")
async def chat(request: ChatRequest):
    """Endpoint chat avec retry automatique, circuit breaker et validation"""
    return await handle_chat_request(
        request=request,
        api_key=OPENAI_API_KEY,
        default_model=OPENAI_MODEL,
        connect_timeout=CONNECT_TIMEOUT,
        read_timeout=READ_TIMEOUT
    )
