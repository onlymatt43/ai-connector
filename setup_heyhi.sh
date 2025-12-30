#!/usr/bin/env bash
set -euo pipefail

if [ $# -lt 1 ]; then
  echo "Usage: $0 <service-name> [custom-domain1,custom-domain2]" >&2
  exit 1
fi

NAME="$1"
ORIGINS="${2:-https://example.com}"

DIR="ai-connector/${NAME}"
mkdir -p "${DIR}"
mkdir -p "ai-connector/shared"

# app.py
cat > "${DIR}/app.py" <<'PY'
import os, json, httpx
from fastapi import FastAPI, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from shared.utils import get_allowed_origins, get_timeouts

APP_NAME     = os.getenv("APP_NAME", "hey-hi-proxy")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL   = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
OPENAI_CHAT_URL = "https://api.openai.com/v1/chat/completions"
ALLOWED_ORIGINS = get_allowed_origins("*")
CONNECT_TIMEOUT, READ_TIMEOUT = get_timeouts()
__VERSION__ = os.getenv("APP_VERSION", "hardened-v1")

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["POST","GET","OPTIONS"],
    allow_headers=["Content-Type","Authorization","Accept","Cache-Control"]
)

@app.get("/__version")
async def version():
    return {"service": APP_NAME, "version": __VERSION__, "model": OPENAI_MODEL}

@app.get("/healthz")
async def healthz():
    return {"ok": True, "has_openai_key": bool(OPENAI_API_KEY), "model": OPENAI_MODEL, "allowed": ALLOWED_ORIGINS}

class Msg(BaseModel):
    role: str
    content: str

class ChatBody(BaseModel):
    messages: list[Msg]
    model: str | None = None
    session_id: str | None = None
    project_id: str | None = None

@app.post("/api/chat")
async def chat(body: ChatBody):
    if not OPENAI_API_KEY:
        return JSONResponse(status_code=500, content={"error":"MISSING_OPENAI_API_KEY"})
    payload = {
        "model": body.model or OPENAI_MODEL,
        "messages": [m.model_dump() for m in body.messages],
        "stream": False,
    }
    headers = {"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type":"application/json"}
    timeout = httpx.Timeout(connect=CONNECT_TIMEOUT, read=READ_TIMEOUT, write=READ_TIMEOUT, pool=CONNECT_TIMEOUT)
    try:
        async with httpx.AsyncClient(timeout=timeout, http2=False) as c:
            r = await c.post(OPENAI_CHAT_URL, headers=headers, json=payload)
        if r.status_code >= 400:
            return JSONResponse(status_code=r.status_code, content={"error":"UPSTREAM_ERROR","status":r.status_code,"body":r.text})
        d = r.json()
        return {"provider":"openai","choices": d.get("choices",[]), "usage": d.get("usage",{})}
    except Exception as e:
        return JSONResponse(status_code=502, content={"error":"OPENAI_PROXY_FAIL","detail": str(e)})

PY

# requirements.txt
cat > "${DIR}/requirements.txt" <<'REQ'
fastapi==0.115.2
uvicorn[standard]==0.30.6
httpx==0.27.2
pydantic==2.9.2

REQ

# Dockerfile
cat > "${DIR}/Dockerfile" <<'DOCK'
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 10000
ENV PORT=10000

CMD exec uvicorn app:app --host 0.0.0.0 --port ${PORT}

DOCK

# render.yaml
cat > "${DIR}/render.yaml" <<YAML
services:
  - type: web
    name: ${NAME}
    runtime: docker
    autoDeploy: true
    envVars:
      - key: OPENAI_API_KEY
        sync: false
      - key: OPENAI_MODEL
        value: gpt-4o-mini
      - key: ALLOWED_ORIGINS
        value: ${ORIGINS}
      - key: APP_NAME
        value: ${NAME}
      - key: APP_VERSION
        value: hardened-v1
      - key: LLM_TIMEOUT_CONNECT
        value: 10
      - key: LLM_TIMEOUT_READ
        value: 70
    healthCheckPath: /healthz
    plan: free

YAML

echo "✅ Created ${DIR}"
echo "Now commit & push, then create a new Render service with Root Directory = ${DIR}"
