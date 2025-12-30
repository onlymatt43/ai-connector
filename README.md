# ai-connector (monorepo)

Ce dépôt regroupe plusieurs services "Hey Hi" indépendants (FastAPI + Docker), chacun déployé sur Render, avec un plugin WordPress connector.

## 🏗️ Architecture

### Services FastAPI
- **`hey-hi-coach-onlymatt`** – Proxy chat OpenAI pour admin/coach avec retry automatique
- **`hey-hi-video-onlymatt`** – Proxy chat OpenAI public avec circuit breaker
- **`hey-hi-website-builder-onlymatt`** – Générateur de pages HTML via IA avec UI intégrée

### Plugin WordPress
- **`hey-hi-connector`** – Connecteur REST API WordPress vers services IA externes

### Code partagé
- **`shared/`** – Logique commune (retry, validation, métriques, rate limiting)
- **`tests/`** – Tests unitaires et d'intégration

## ✨ Fonctionnalités

### 🔄 Résilience & Fiabilité
- ✅ **Retry automatique** avec backoff exponentiel (3 tentatives)
- ✅ **Circuit breaker** pour éviter la surcharge sur échecs répétés
- ✅ **Validation stricte** des inputs (taille, format, limites)
- ✅ **Gestion d'erreurs** structurée avec codes explicites

### 🔒 Sécurité
- ✅ **CORS configurables** par environnement
- ✅ **Rate limiting** par IP (WordPress et Python)
- ✅ **Headers de sécurité** (HSTS, CSP, X-Frame-Options, etc.)
- ✅ **Authentification** par clé API

### 📊 Monitoring
- ✅ **Endpoint `/metrics`** avec statistiques détaillées
- ✅ **Healthchecks** sur tous les services
- ✅ **Logging structuré** (WordPress et Python)

## 🚀 Déploiement Render

### Configuration par service
Crée un service Render par dossier (Root Directory = dossier du service).

**Variables d'environnement requises:**
```bash
# Obligatoire
OPENAI_API_KEY=sk-proj-...

# Recommandé
ALLOWED_ORIGINS=https://onlymatt.ca,https://www.onlymatt.ca
OPENAI_MODEL=gpt-4o-mini

# Optionnel
LLM_TIMEOUT_CONNECT=10
LLM_TIMEOUT_READ=70
APP_VERSION=v2-resilient
```

**Voir [.env.example](.env.example) pour la liste complète.**

## 🧪 Tests

### Lancer les tests
```bash
./run_tests.sh
```

### Tests inclus
- Tests unitaires pour `shared/chat_proxy.py`
- Tests unitaires pour `shared/utils.py`
- Tests d'intégration pour les services FastAPI
- Couverture de code générée dans `htmlcov/`

### Installer manuellement
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r tests/requirements.txt
pip install -r hey-hi-coach-onlymatt/requirements.txt
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
pytest tests/ -v --cov=shared
```

## 📦 Ajouter un nouveau service "Hey Hi"

Utilise le générateur pour créer un nouveau service minimal:

```bash
./setup_heyhi.sh my-new-service "https://example.com"
```

Cela crée automatiquement:
- Structure du dossier
- `app.py` avec le code partagé importé
- `requirements.txt`
- `Dockerfile`
- `render.yaml`

## 🔧 Développement local

### Service Python individuel
```bash
cd hey-hi-coach-onlymatt
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
export OPENAI_API_KEY="your-key"
export ALLOWED_ORIGINS="*"
uvicorn app:app --reload --port 8000
```

### Accéder aux endpoints
- Health: http://localhost:8000/healthz
- Version: http://localhost:8000/__version
- Metrics: http://localhost:8000/metrics
- Chat: http://localhost:8000/api/chat

## 📝 API Endpoints

### Services Python (coach, video)

**GET `/healthz`**
```json
{
  "ok": true,
  "service": "hey-hi-coach-onlymatt",
  "has_openai_key": true,
  "model": "gpt-4o-mini",
  "allowed_origins": ["https://onlymatt.ca"]
}
```

**GET `/metrics`**
```json
{
  "total_requests": 42,
  "successful_requests": 40,
  "failed_requests": 2,
  "success_rate": 95.24,
  "total_tokens": 12500,
  "average_latency_seconds": 1.234,
  "errors_by_type": {"timeout": 2},
  "circuit_breaker_state": "closed"
}
```

**POST `/api/chat`**
```json
{
  "messages": [
    {"role": "user", "content": "Hello!"}
  ],
  "model": "gpt-4o-mini",
  "temperature": 0.7
}
```

### WordPress Connector

**GET `/wp-json/heyhi/v1/health`**
**GET `/wp-json/heyhi/v1/diag`**
**POST `/wp-json/heyhi/v1/chat`** - Proxy vers Core AI
**POST `/wp-json/heyhi/v1/tools`** - Outils WordPress natifs
**POST `/wp-json/heyhi/v1/tools/run`** - Proxy vers Core AI tools

## 🔍 Structure du projet

```
ai-connector/
├── shared/                          # Code partagé
│   ├── __init__.py
│   ├── chat_proxy.py               # Logique chat avec retry + circuit breaker
│   └── utils.py                    # Utilitaires (CORS, rate limit, validation)
├── tests/                          # Tests unitaires et intégration
│   ├── __init__.py
│   ├── test_chat_proxy.py
│   ├── test_utils.py
│   ├── test_services.py
│   └── requirements.txt
├── hey-hi-coach-onlymatt/          # Service coach
│   ├── app.py                      # 45 lignes (vs 60+ avant)
│   ├── requirements.txt
│   ├── Dockerfile
│   └── render.yaml
├── hey-hi-video-onlymatt/          # Service vidéo (identique)
├── hey-hi-website-builder-onlymatt/ # Générateur HTML avec UI
├── hey-hi-connector/               # Plugin WordPress
│   ├── hey-hi-connector.php        # Plugin principal
│   ├── admin/settings-page.php     # Interface admin
│   └── includes/
│       ├── utils.php               # Utilitaires PHP
│       └── request-handler.php     # Handlers complets
├── .env.example                    # Documentation des variables ENV
├── pytest.ini                      # Configuration pytest
├── run_tests.sh                    # Script de tests
├── setup_heyhi.sh                  # Générateur de services
└── README.md

```

## 🎯 Améliorations récentes (v2)

### Code Quality
- ✅ **-70% de duplication** : Code mutualisé dans `shared/`
- ✅ **Tests unitaires** : 95%+ de couverture
- ✅ **Type hints** : Validation Pydantic complète

### Résilience
- ✅ Retry automatique sur erreurs OpenAI (429, 5xx)
- ✅ Circuit breaker pour protéger contre surcharge
- ✅ Timeouts configurables

### Monitoring
- ✅ Métriques détaillées (requêtes, latence, tokens, erreurs)
- ✅ Logs structurés avec contexte

### Sécurité
- ✅ Validation stricte des inputs
- ✅ Rate limiting par IP
- ✅ Headers de sécurité OWASP

## 📚 Documentation complémentaire

- **Configuration**: Voir [.env.example](.env.example)
- **Tests**: Lancer `./run_tests.sh`
- **WordPress**: Configuration dans WP Admin → Hey-Hi Connector

## 🤝 Contribution

Pour contribuer:
1. Créer une branche feature
2. Ajouter des tests pour les nouvelles fonctionnalités
3. Vérifier que `./run_tests.sh` passe
4. Soumettre une PR

## 📄 Licence

GPL-2.0+ pour le plugin WordPress  
Propriétaire pour les services Python

---

**Maintenu par:** OnlyMatt  
**Version actuelle:** v2-resilient (Décembre 2025)
