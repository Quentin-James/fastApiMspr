# MSPR IA — Microservice de recommandations

Microservice Python / FastAPI fournissant des **recommandations nutritionnelles et sportives personnalisées** via :

- **Hugging Face Inference API** — vision alimentaire (classification d'images) + génération de texte NLP
- **Google Vision API** — fallback vision si HF indisponible
- **Ollama** — fallback NLP local (LLM auto-hébergé)
- **MongoDB** — persistance asynchrone via Motor

Développé séparément du backend Spring Boot (port 8080) conformément au cahier des charges TPRE502.

---

## Stack technique

| Composant | Technologie | Version |
|---|---|---|
| Framework API | FastAPI + Uvicorn | 0.111 / 0.29 |
| Validation | Pydantic v2 | 2.7 |
| Base de données | MongoDB (Motor async) | 7 / 3.4 |
| Client HTTP async | httpx | 0.27 |
| IA Vision | HF `nateraw/food` → Google Vision | — |
| IA NLP | HF `google/flan-t5-large` → Ollama | — |
| Rate limiting | slowapi | 0.1.9 |
| Tests | Pytest + pytest-asyncio | 8.2 / 0.23 |
| Container | Docker multi-stage + Compose | — |

---

## Démarrage rapide

### 1. Prérequis

- Python 3.11+
- Un token Hugging Face valide (gratuit) : https://huggingface.co/settings/tokens
- Docker & Docker Compose (déploiement)

### 2. Configuration

```bash
cp .env.example .env
# Renseigner au minimum HUGGINGFACE_API_TOKEN
```

Variables clés dans `.env` :

```env
APP_ENV=development          # development | production
APP_PORT=8085

HUGGINGFACE_API_TOKEN=hf_...  # Obligatoire pour la vision et le NLP
HUGGINGFACE_FOOD_MODEL=nateraw/food

GOOGLE_VISION_API_KEY=        # Optionnel — fallback vision
MONGODB_URL=mongodb://localhost:27017
OLLAMA_URL=http://localhost:11434
```

> **Important :** renouveler le token HF régulièrement sur https://huggingface.co/settings/tokens.
> Un token expiré provoque des erreurs 401 sur tous les appels IA.

### 3. Lancer en local

```bash
python -m venv .venv
source .venv/Scripts/activate   # Windows
# source .venv/bin/activate     # Linux / macOS

pip install -r requirements.txt
uvicorn app.main:app --reload --port 8085
```

> MongoDB est **optionnel au démarrage** : si MongoDB n'est pas disponible, le service démarre
> avec un avertissement et continue de fonctionner sans persistance.

### 4. Lancer avec Docker Compose

```bash
# Production (FastAPI + MongoDB)
docker-compose up -d

# Développement (+ Mongo Express sur :8081)
docker-compose --profile dev up -d
```

### 5. Vérifier que le service tourne

```bash
curl http://localhost:8085/health
# {"status": "ok", "service": "mspr-ia-microservice", "version": "1.0.0"}
```

---

## Documentation API

| URL | Description |
|---|---|
| `http://localhost:8085/docs` | Swagger UI interactif |
| `http://localhost:8085/redoc` | ReDoc |
| `http://localhost:8085/openapi.json` | Schéma OpenAPI 3.1 |

---

## Endpoints

### Nutrition

| Méthode | Endpoint | Description |
|---|---|---|
| `POST` | `/nutrition/analyze-photo` | Analyse une image de repas (multipart/form-data) |
| `POST` | `/nutrition/recommend` | Plan de repas 7 jours personnalisé |

**Analyser une photo :**
```bash
curl -X POST http://localhost:8085/nutrition/analyze-photo \
  -H "accept: application/json" \
  -F "file=@photo_repas.jpg;type=image/jpeg"
```

**Générer un plan nutritionnel :**
```bash
curl -X POST http://localhost:8085/nutrition/recommend \
  -H "Content-Type: application/json" \
  -d '{
    "patient_id": "patient_001",
    "objective": "perte_de_poids",
    "allergies": ["gluten"],
    "diet_type": "omnivore",
    "daily_calories_target": 1600,
    "excluded_foods": []
  }'
```

Valeurs acceptées pour `objective` : `perte_de_poids`, `prise_de_masse`, `maintenance`, `endurance`
Valeurs acceptées pour `diet_type` : `omnivore`, `vegetarian`, `vegan`, `keto`, `gluten_free`, `lactose_free`

### Sport

| Méthode | Endpoint | Description |
|---|---|---|
| `POST` | `/sport/recommend` | Programme sportif hebdomadaire |
| `PUT` | `/sport/feedback/{id}` | Retour utilisateur (progression adaptative) |

**Générer un programme sportif :**
```bash
curl -X POST http://localhost:8085/sport/recommend \
  -H "Content-Type: application/json" \
  -d '{
    "patient_id": "patient_001",
    "objective": "fat_loss",
    "fitness_level": "beginner",
    "equipment": "none",
    "available_days": ["lundi", "mercredi", "vendredi"],
    "limitations": ["douleur genou droit"],
    "session_duration_max_minutes": 45
  }'
```

Valeurs acceptées :
- `objective` : `fat_loss`, `muscle_gain`, `endurance`, `general_health`, `flexibility`
- `fitness_level` : `beginner`, `intermediate`, `advanced`
- `equipment` : `none`, `home`, `gym`

### Transverse

| Méthode | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Health check |
| `GET` | `/recommendations/{patient_id}` | Historique des recommandations d'un patient |

---

## Stratégie de fallback IA

```
Vision alimentaire
  ├── 1. Hugging Face (nateraw/food)     → classification image Food-101
  ├── 2. Google Vision API               → label detection générique
  └── 3. Erreur 503 structurée           → si les deux API échouent
       └── Mode mock (dev uniquement)    → si AUCUN token configuré

Génération de texte (messages personnalisés)
  ├── 1. Hugging Face (flan-t5-large)   → text-to-text instruction-following
  ├── 2. Ollama local (llama3)           → LLM auto-hébergé
  └── 3. Message par défaut (hardcodé)  → toujours disponible
```

> Le mode mock s'active **uniquement** quand `APP_ENV=development` ET qu'aucun token API
> n'est configuré (`HUGGINGFACE_API_TOKEN` et `GOOGLE_VISION_API_KEY` tous deux vides).
> Avec un token configuré, une vraie erreur IA retourne un 503 explicite plutôt que des données fictives.

---

## Tests

```bash
# Tous les tests
pytest

# Avec couverture
pytest --cov=app --cov-report=html
# Rapport : htmlcov/index.html

# Test manuel end-to-end (serveur doit tourner)
python test_api_manual.py
```

---

## Variables d'environnement complètes

| Variable | Description | Défaut |
|---|---|---|
| `APP_ENV` | Environnement (`development` / `production`) | `development` |
| `APP_PORT` | Port d'écoute | `8085` |
| `MONGODB_URL` | URI de connexion MongoDB | `mongodb://localhost:27017` |
| `MONGODB_DB_NAME` | Nom de la base MongoDB | `mspr_ia` |
| `HUGGINGFACE_API_TOKEN` | Token HF (obligatoire pour l'IA) | — |
| `HUGGINGFACE_FOOD_MODEL` | Modèle HF de classification alimentaire | `nateraw/food` |
| `GOOGLE_VISION_API_KEY` | Clé API Google Vision (fallback) | — |
| `SPRING_BACKEND_URL` | URL du backend Spring Boot | `http://localhost:8080` |
| `OLLAMA_URL` | URL du serveur Ollama local | `http://localhost:11434` |
| `OLLAMA_MODEL` | Modèle Ollama utilisé | `llama3` |
| `ALLOWED_ORIGINS` | Origins CORS autorisées (virgule) | `http://localhost:3000,...` |
| `RATE_LIMIT` | Limite de requêtes par IP/minute | `10/minute` |

---

## Architecture des fichiers

```
app/
├── main.py                    # Point d'entrée FastAPI, middleware, lifecycle
├── config.py                  # Settings Pydantic (lecture .env)
├── database.py                # Connexion MongoDB (Motor async)
├── models/
│   ├── nutrition.py           # Modèles Pydantic nutrition (FoodItem, Macros, …)
│   └── sport.py               # Modèles Pydantic sport (Exercise, WorkoutSession, …)
├── routers/
│   ├── nutrition.py           # Endpoints /nutrition/*
│   ├── sport.py               # Endpoints /sport/*
│   └── recommendations.py    # Endpoints /health, /recommendations/*
├── services/
│   ├── vision.py              # Reconnaissance visuelle (HF → Google Vision → mock)
│   ├── nlp.py                 # Génération de texte (HF → Ollama → défaut)
│   ├── nutrition_engine.py    # Moteur de recommandations nutritionnelles
│   └── sport_engine.py        # Moteur de recommandations sportives
└── repositories/
    └── recommendation_repository.py  # CRUD MongoDB
```

---

## Interopérabilité Spring Boot

```
Spring Boot :8080  →  HTTP POST  →  FastAPI :8085
                   ←  JSON       ←
```

Le microservice est conçu pour être appelé depuis `RecommendationController` côté Spring.
Configurer `SPRING_BACKEND_URL` pour que le microservice puisse interroger les données patients via Spring si nécessaire.

---

## Résolution de problèmes courants

| Symptôme | Cause probable | Solution |
|---|---|---|
| `401` sur tous les appels IA | Token HF expiré | Régénérer sur huggingface.co/settings/tokens |
| `404` sur `api-inference.huggingface.co` | Ancienne URL HF (migrée) | L'URL correcte est `router.huggingface.co/hf-inference/models/…` |
| Démarrage échoue avec MongoDB | MongoDB non lancé | Normal en dev — le service continue avec un warning |
| Port 8085 occupé (Windows) | Socket orphelin Windows Store Python | Utiliser `--port 8086` ou redémarrer Windows |
| Réponse mock au lieu de vrais résultats | Token HF non défini dans `.env` | Vérifier `HUGGINGFACE_API_TOKEN` dans `.env` |
