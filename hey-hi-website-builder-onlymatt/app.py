import os, json, httpx
from fastapi import FastAPI, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
from shared.utils import get_allowed_origins, get_timeouts

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
ALLOWED_ORIGINS = get_allowed_origins("*")
CONNECT_TIMEOUT, READ_TIMEOUT = get_timeouts()
OPENAI_CHAT_URL = "https://api.openai.com/v1/chat/completions"
__VERSION__ = "om-website-builder-v1"
APP_NAME = os.getenv("APP_NAME", "hey-hi-website-builder-onlymatt" )

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["POST","OPTIONS","GET"],
    allow_headers=["Authorization","Content-Type","Accept","Cache-Control"],
)

INDEX_HTML = """<!doctype html>
<html lang="fr">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>AI Website Builder</title>
  <style>
    body{font-family:system-ui,-apple-system,Segoe UI,Roboto,Arial,sans-serif;margin:24px;max-width:1100px}
    .row{display:flex;gap:16px;flex-wrap:wrap}
    .col{flex:1;min-width:320px}
    textarea{width:100%;min-height:240px;padding:10px;border:1px solid #ccc;border-radius:8px}
    input[type="text"]{width:100%;padding:10px;border:1px solid #ccc;border-radius:8px}
    button{padding:10px 14px;border:0;border-radius:8px;background:#111;color:#fff;cursor:pointer}
    button[disabled]{opacity:.6;cursor:not-allowed}
    .bar{display:flex;gap:8px;align-items:center;margin:8px 0}
    iframe{width:100%;height:520px;border:1px solid #ddd;border-radius:8px;background:#fff}
    .note{font-size:12px;opacity:.7}
    .pill{display:inline-block;padding:3px 8px;border-radius:999px;border:1px solid #ddd;margin-left:8px;font-size:12px}
    .ok{color:green;border-color:green}
    .err{color:#b00;border-color:#b00}
    .toast{position:fixed;bottom:16px;right:16px;background:#111;color:#fff;padding:10px 14px;border-radius:8px;opacity:.95}
  </style>
</head>
<body>
  <h1>AI Website Builder <span class="pill">v__VERSION__</span></h1>

  <div class="row">
    <div class="col">
      <h3>Brief</h3>
      <div class="bar">
        <input id="title" type="text" placeholder="Titre de la page (ex: Offre Coaching Vidéo)" />
        <button id="build">Générer la page</button>
      </div>
      <textarea id="instructions" placeholder="Donne des consignes claires :
- Un hero avec un titre fort, sous-titre et bouton CTA
- Une section 3 colonnes (avantages)
- Une section témoignage
Palette sobre, lisible. HTML propre sans <script>."></textarea>
      <div class="note">L'IA renvoie un fragment HTML5 autonome (sections, classes utilitaires, style minimal inline si nécessaire).</div>
    </div>

    <div class="col">
      <h3>Aperçu</h3>
      <iframe id="preview"></iframe>
      <div class="bar">
        <button id="copy">Copier le HTML</button>
        <button id="download">Télécharger .html</button>
        <span id="status" class="pill">prêt</span>
      </div>
    </div>
  </div>

<script>
(() => {
  const status = document.getElementById("status");
  const title  = document.getElementById("title");
  const ins    = document.getElementById("instructions");
  const prev   = document.getElementById("preview");
  const btnB   = document.getElementById("build");
  const btnC   = document.getElementById("copy");
  const btnD   = document.getElementById("download");

  function setStatus(text, ok){
    status.textContent = text;
    status.className = "pill " + (ok===true ? "ok" : ok===false ? "err" : "");
  }
  function setPreview(html){
    const doc = prev.contentDocument || prev.contentWindow.document;
    doc.open(); doc.write(html); doc.close();
  }
  function toast(msg){
    const el = document.createElement("div"); el.className = "toast"; el.textContent = msg;
    document.body.appendChild(el); setTimeout(()=>{ el.remove(); }, 2200);
  }

  async function build(){
    const t = (title.value || "").trim();
    const i = (ins.value || "").trim();
    if(!i){ setStatus("brief requis", false); return; }
    btnB.disabled = true; setStatus("génération…");
    try {
      const r = await fetch("/build", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title: t || "Page sans titre", instructions: i })
      });
      const txt = await r.text();
      if(!r.ok){
        setStatus("erreur", false);
        try{ setPreview(`<pre style='padding:16px'>${JSON.stringify(JSON.parse(txt),null,2)}</pre>`); }
        catch{ setPreview(`<pre style='padding:16px'>${txt.slice(0,2000)}</pre>`); }
        return;
      }
      const data = JSON.parse(txt);
      const html = data?.html || "";
      if(!html.trim()){ setStatus("html vide", false); setPreview("<pre style='padding:16px'>HTML vide</pre>"); return; }
      setStatus("ok", true);
      setPreview(html);
      prev.dataset.html = html;
    } catch(e){
      setStatus("réseau", false);
      setPreview(`<pre style='padding:16px'>${e?.message||e}</pre>`);
    } finally {
      btnB.disabled = false;
    }
  }

  btnB.addEventListener("click", build);
  btnC.addEventListener("click", async () => {
    const html = prev.dataset.html || "";
    if(!html){ toast("Pas de HTML à copier"); return; }
    try { await navigator.clipboard.writeText(html); toast("HTML copié"); }
    catch { toast("Impossible de copier"); }
  });
  btnD.addEventListener("click", () => {
    const html = prev.dataset.html || "";
    if(!html){ toast("Pas de HTML à télécharger"); return; }
    const blob = new Blob([html], {type:"text/html"});
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = (title.value || "page").replace(/\s+/g,"-").toLowerCase()+".html";
    a.click();
    URL.revokeObjectURL(a.href);
  });
})();
</script>
</body>
</html>
""".replace("__VERSION__", __VERSION__)

@app.get("/", response_class=HTMLResponse)
async def home():
    return INDEX_HTML

@app.get("/__version")
async def version():
    return {"service": APP_NAME, "version": __VERSION__, "model": OPENAI_MODEL}

@app.get("/healthz")
async def healthz():
    return {"ok": True, "has_openai_key": bool(OPENAI_API_KEY), "model": OPENAI_MODEL, "allowed": ALLOWED_ORIGINS}

class BuildBody(BaseModel):
    title: str
    instructions: str

def build_prompt(title, instructions):
    return [
        {"role":"system","content":"Tu es un assistant qui génère du HTML5 propre, sans <script>, responsive et accessible (labels, alt)."},
        {"role":"user","content": f"Génère une page intitulée '{title}'. Consignes :\n{instructions}\n\nRetourne UNIQUEMENT le HTML final."}
    ]

@app.post("/build")
async def build_page(body: BuildBody = Body(...)):
    if not OPENAI_API_KEY:
        raise HTTPException(status_code=500, detail="Missing OPENAI_API_KEY")
    headers = {"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"}
    payload = {"model": OPENAI_MODEL, "messages": build_prompt(body.title, body.instructions)}
    timeout_connect, timeout_read = CONNECT_TIMEOUT, READ_TIMEOUT
    timeout = httpx.Timeout(connect=timeout_connect, read=timeout_read, write=timeout_read, pool=timeout_connect)
    try:
        async with httpx.AsyncClient(timeout=timeout, http2=False) as c:
            r = await c.post(OPENAI_CHAT_URL, headers=headers, json=payload)
        if r.status_code >= 400:
            return JSONResponse(status_code=r.status_code, content={"error":"UPSTREAM_ERROR","status":r.status_code,"body":r.text})
        d = r.json()
        html = d.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
        return {"html": html, "model": d.get("model")}
    except Exception as e:
        return JSONResponse(status_code=502, content={"error":"OPENAI_FAIL","detail": str(e)})
