# Guide de Déploiement

Ce guide explique comment déployer les services Python et le plugin WordPress.

## 🚀 Déploiement Services Python sur Render

### Prérequis
- Compte Render.com
- Repository GitHub connecté: https://github.com/onlymatt43/ai-connector
- Clé API OpenAI

### Configuration par service

Créer **3 services Web** sur Render (un par dossier).

---

#### Service 1: hey-hi-coach-onlymatt

**Settings:**
- **Name:** `hey-hi-coach-onlymatt`
- **Environment:** `Python 3`
- **Region:** `Oregon (US West)` ou le plus proche
- **Branch:** `main`
- **Root Directory:** `hey-hi-coach-onlymatt`
- **Build Command:** `pip install -r requirements.txt && pip install -r ../shared/requirements.txt`
- **Start Command:** `cd .. && PYTHONPATH=$PYTHONPATH:$(pwd) uvicorn hey-hi-coach-onlymatt.app:app --host 0.0.0.0 --port $PORT`

**Environment Variables:**
```bash
OPENAI_API_KEY=sk-proj-your-key-here
ALLOWED_ORIGINS=https://onlymatt.ca,https://www.onlymatt.ca,*
OPENAI_MODEL=gpt-4o-mini
APP_NAME=hey-hi-coach-onlymatt
APP_VERSION=v2-resilient
LLM_TIMEOUT_CONNECT=10
LLM_TIMEOUT_READ=70
```

**URL finale:** `https://hey-hi-coach-onlymatt.onrender.com`

**Endpoints disponibles:**
- `GET /healthz` - Health check
- `GET /__version` - Version info
- `GET /metrics` - Métriques de monitoring
- `POST /api/chat` - Chat OpenAI

---

#### Service 2: hey-hi-video-onlymatt

**Settings:** (identiques au coach, sauf Root Directory)
- **Name:** `hey-hi-video-onlymatt`
- **Root Directory:** `hey-hi-video-onlymatt`
- **Build Command:** `pip install -r requirements.txt && pip install -r ../shared/requirements.txt`
- **Start Command:** `cd .. && PYTHONPATH=$PYTHONPATH:$(pwd) uvicorn hey-hi-video-onlymatt.app:app --host 0.0.0.0 --port $PORT`

**Environment Variables:** (identiques, changer APP_NAME)
```bash
OPENAI_API_KEY=sk-proj-your-key-here
ALLOWED_ORIGINS=https://video.onlymatt.ca,*
APP_NAME=hey-hi-video-onlymatt
```

**URL finale:** `https://hey-hi-video-onlymatt.onrender.com`

---

#### Service 3: hey-hi-website-builder-onlymatt

**Settings:**
- **Name:** `hey-hi-website-builder-onlymatt`
- **Root Directory:** `hey-hi-website-builder-onlymatt`
- **Build Command:** `pip install -r requirements.txt`
- **Start Command:** `uvicorn app:app --host 0.0.0.0 --port $PORT`

**Environment Variables:**
```bash
OPENAI_API_KEY=sk-proj-your-key-here
ALLOWED_ORIGINS=*
APP_NAME=hey-hi-website-builder-onlymatt
```

**URL finale:** `https://hey-hi-website-builder-onlymatt.onrender.com`

**Endpoints:**
- `GET /` - Interface web builder
- `POST /build` - Générer HTML via IA
- `GET /healthz`, `/__version`, `/metrics`

---

### Vérification post-déploiement

Pour chaque service:

```bash
# Health check
curl https://hey-hi-coach-onlymatt.onrender.com/healthz

# Réponse attendue:
{
  "ok": true,
  "service": "hey-hi-coach-onlymatt",
  "has_openai_key": true,
  "model": "gpt-4o-mini",
  "allowed_origins": ["https://onlymatt.ca"]
}

# Metrics
curl https://hey-hi-coach-onlymatt.onrender.com/metrics

# Test chat (avec ta clé API)
curl -X POST https://hey-hi-coach-onlymatt.onrender.com/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"role": "user", "content": "Hello!"}
    ]
  }'
```

---

## 📦 Installation Plugin WordPress

### Préparation du ZIP

```bash
cd hey-hi-connector
zip -r hey-hi-connector.zip . -x "*.DS_Store" -x "__MACOSX"
```

### Installation sur WordPress

1. **Via l'interface admin:**
   - Aller dans `Extensions` → `Ajouter`
   - Cliquer sur `Téléverser une extension`
   - Sélectionner `hey-hi-connector.zip`
   - Cliquer sur `Installer maintenant`
   - Activer l'extension

2. **Via FTP/SFTP:**
   ```bash
   # Dézipper et uploader dans:
   /wp-content/plugins/hey-hi-connector/
   ```

3. **Via WP-CLI:**
   ```bash
   wp plugin install hey-hi-connector.zip --activate
   ```

### Configuration

1. Aller dans `Réglages` → `Hey-Hi Connector`

2. Configurer les paramètres:

   **Core AI Base URL:**
   ```
   https://hey-hi-coach-onlymatt.onrender.com
   ```
   (ou ton URL Render principale)

   **WP API Key:**
   ```
   votre-cle-secrete-complexe-ici
   ```
   (générer une clé aléatoire sécurisée)

   **Allowed Origins (CORS):**
   ```
   https://onlymatt.ca,https://www.onlymatt.ca,https://video.onlymatt.ca
   ```

   **Rate Limit / minute:**
   ```
   120
   ```

   **Debug logs:** ☑️ Activer (en dev), ☐ Désactiver (en prod)

3. Cliquer sur `Enregistrer`

### Vérification

**Tester les endpoints WordPress:**

```bash
# Health check
curl https://onlymatt.ca/wp-json/heyhi/v1/health

# Diagnostics
curl https://onlymatt.ca/wp-json/heyhi/v1/diag

# Chat (avec authentification)
curl -X POST https://onlymatt.ca/wp-json/heyhi/v1/chat \
  -H "Content-Type: application/json" \
  -H "X-HeyHi-Key: votre-cle-secrete" \
  -d '{
    "messages": [
      {"role": "user", "content": "Test depuis WordPress"}
    ]
  }'

# Tools WordPress natifs
curl -X POST https://onlymatt.ca/wp-json/heyhi/v1/tools \
  -H "Content-Type: application/json" \
  -H "X-HeyHi-Key: votre-cle-secrete" \
  -d '{
    "action": "get_posts",
    "post_type": "post",
    "limit": 5
  }'
```

**Réponse attendue (health):**
```json
{
  "status": "ok",
  "version": "1.0.0"
}
```

**Réponse attendue (diag):**
```json
{
  "status": "ok",
  "core_ai_base": "https://hey-hi-coach-onlymatt.onrender.com",
  "has_api_key": true,
  "allowed_origins": ["https://onlymatt.ca"],
  "rate_limit_per_min": 120,
  "debug": false
}
```

---

## 🎯 Utilisation depuis le Frontend

### Option 1: Appel direct aux services Render

```javascript
// Depuis n'importe quel site web
async function chatWithAI(message) {
  const response = await fetch('https://hey-hi-coach-onlymatt.onrender.com/api/chat', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      messages: [
        { role: 'user', content: message }
      ]
    })
  });
  
  const data = await response.json();
  return data.choices[0].message.content;
}

// Utilisation
const reply = await chatWithAI('Bonjour!');
console.log(reply);
```

### Option 2: Via WordPress (avec auth)

```javascript
// Passe par WordPress
async function chatViaWordPress(message) {
  const response = await fetch('https://onlymatt.ca/wp-json/heyhi/v1/chat', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-HeyHi-Key': 'votre-cle-secrete'  // Important!
    },
    body: JSON.stringify({
      messages: [
        { role: 'user', content: message }
      ]
    })
  });
  
  const data = await response.json();
  return data.choices[0].message.content;
}
```

### Option 3: Website Builder

```javascript
// Générer une page HTML
async function buildWebsite(title, instructions) {
  const response = await fetch('https://hey-hi-website-builder-onlymatt.onrender.com/build', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      title: title,
      instructions: instructions
    })
  });
  
  const data = await response.json();
  return data.html;  // HTML complet prêt à afficher
}

// Utilisation
const html = await buildWebsite(
  'Landing Page Coach',
  'Créer une page avec un hero, 3 colonnes bénéfices, et un formulaire contact'
);
```

---

## 🔒 Sécurité en Production

### Variables sensibles

**Ne jamais commit:**
- ❌ `OPENAI_API_KEY`
- ❌ Clés API WordPress
- ❌ Tokens secrets

**Toujours utiliser:**
- ✅ Variables d'environnement Render
- ✅ WordPress Settings (base de données)
- ✅ `.env` locaux (gitignored)

### CORS

**En production, restreindre les origines:**
```bash
ALLOWED_ORIGINS=https://onlymatt.ca,https://www.onlymatt.ca
```

**Ne PAS utiliser `*` en production!**

### Rate Limiting

Le rate limiting est actif:
- Python: Via `SimpleRateLimiter` (in-memory)
- WordPress: Via transients (60 req/min par IP)

Pour production intensive, considérer Redis.

---

## 📊 Monitoring

### Endpoints de monitoring

Tous les services exposent:

```bash
# Métriques détaillées
curl https://hey-hi-coach-onlymatt.onrender.com/metrics

# Réponse:
{
  "total_requests": 1234,
  "successful_requests": 1200,
  "failed_requests": 34,
  "success_rate": 97.25,
  "total_tokens": 125000,
  "average_latency_seconds": 1.234,
  "errors_by_type": {
    "timeout": 20,
    "rate_limit": 14
  },
  "circuit_breaker_state": "closed"
}
```

### Logs WordPress

Si debug activé, logs dans:
```
/wp-content/uploads/heyhi-logs/heyhi-YYYY-MM-DD.log
```

Format JSON pour parsing facile.

---

## 🐛 Troubleshooting

### Service Python ne démarre pas

**Vérifier:**
1. Build command correct: `pip install -r requirements.txt`
2. Start command: `uvicorn app:app --host 0.0.0.0 --port $PORT`
3. Root Directory pointe vers le bon dossier
4. `OPENAI_API_KEY` est défini

**Logs Render:** Dashboard → Service → Logs

### Plugin WordPress erreur

**Vérifier:**
1. Extensions → Hey-Hi Connector est activé
2. Core AI Base URL est accessible (tester avec curl)
3. CORS autorise l'origine WordPress
4. Clé API est définie (si auth activée)

**Debug:**
- Activer debug dans settings
- Consulter `/wp-content/uploads/heyhi-logs/`

### CORS erreur

```
Access to fetch at '...' from origin '...' has been blocked by CORS policy
```

**Solution:**
- Ajouter l'origine dans `ALLOWED_ORIGINS` (Render)
- Ou dans WordPress settings → Allowed Origins

### Rate limit dépassé

```json
{
  "error": "RATE_LIMIT_EXCEEDED",
  "message": "Trop de requêtes, réessayez dans 1 minute"
}
```

**Solution:**
- Attendre 60 secondes
- Augmenter la limite dans settings (WordPress ou code)
- Implémenter un système de queue côté client

---

## 🔄 Mises à jour

### Déployer une mise à jour

```bash
# Faire les modifications
git add .
git commit -m "feat: nouvelle fonctionnalité"
git push origin main

# Render redéploiera automatiquement!
```

### Mettre à jour le plugin WordPress

1. Modifier le code dans `hey-hi-connector/`
2. Incrémenter la version dans `hey-hi-connector.php`:
   ```php
   * Version: 1.1.0
   ```
3. Commit et push
4. Recréer le ZIP et réinstaller

---

## 📚 Documentation supplémentaire

- **README.md** - Vue d'ensemble du projet
- **CHANGELOG.md** - Historique des changements
- **.env.example** - Liste des variables d'environnement
- **Tests:** `./run_tests.sh`

---

**Maintenu par:** OnlyMatt  
**Support:** https://github.com/onlymatt43/ai-connector/issues  
**Dernière mise à jour:** Décembre 2025
