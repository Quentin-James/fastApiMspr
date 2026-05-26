# MSPR IA — Microservice de recommandations

Microservice Python / FastAPI fournissant des **recommandations nutritionnelles et sportives personnalisées** via :

- **Hugging Face Inference API** — vision alimentaire (classification d'images) + génération de texte NLP
- **Google Vision API** — fallback vision si HF indisponible
- **MongoDB** — persistance asynchrone via Motor

Développé séparément du backend Spring Boot (port 8084) conformément au cahier des charges TPRE502.

---

## Stack technique

| Composant | Technologie | Version |
|---|---|---|
| Framework API | FastAPI + Uvicorn | 0.111 / 0.29 |
| Validation | Pydantic v2 | 2.7 |
| Base de données | MongoDB (Motor async) + MySQL (comptes utilisateurs) | 7 / 3.4 + SQLAlchemy |
| Client HTTP async | httpx | 0.27 |
| IA Vision | HF `nateraw/food` → Google Vision | — |
| IA NLP | HF `google/flan-t5-large` → Ollama | — |
| Rate limiting | slowapi | 0.1.9 |
| Tests | Pytest + pytest-asyncio | 8.2 / 0.23 |
| Container | Docker multi-stage + Compose | — |

---

## Démarrage rapide

### 1. Prérequis

- Docker & Docker Compose
- Un token Hugging Face valide (gratuit) : https://huggingface.co/settings/tokens

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
MYSQL_DATABASE_URL=mysql+pymysql://mspr:mspr@mysql:3306/mspr_users
SPRING_BACKEND_URL=http://localhost:8084
```

> **Important :** renouveler le token HF régulièrement sur https://huggingface.co/settings/tokens.
> Un token expiré provoque des erreurs 401 sur tous les appels IA.

### 3. Lancer avec Docker Compose

```bash
# Production (FastAPI + MongoDB + MySQL)
docker-compose up -d --build

# Développement (+ Mongo Express sur :8081)
docker-compose --profile dev up -d
```

### 4. Vérifier que le service tourne

```bash
curl http://localhost:8085/health
# {"status": "ok", "service": "mspr-ia-microservice", "version": "1.0.0"}
```

Swagger UI : http://localhost:8085/docs

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
  -F "file=@photo_repas.jpg;type=image/jpeg"
```

**Générer un plan nutritionnel :**
```bash
curl -X POST http://localhost:8085/nutrition/recommend \
  -H "Content-Type: application/json" \
  -d '{
    "patient_id": "1",
    "objective": "perte_de_poids",
    "allergies": [],
    "diet_type": "omnivore",
    "daily_calories_target": 2000,
    "excluded_foods": []
  }'
```

Valeurs `objective` : `perte_de_poids`, `prise_de_masse`, `maintenance`
Valeurs `diet_type` : `omnivore`, `vegetarian`, `vegan`, `keto`, `gluten_free`, `lactose_free`

### Sport

| Méthode | Endpoint | Description |
|---|---|---|
| `POST` | `/sport/recommend` | Programme sportif hebdomadaire |

**Générer un programme sportif :**
```bash
curl -X POST http://localhost:8085/sport/recommend \
  -H "Content-Type: application/json" \
  -d '{
    "patient_id": "1",
    "objective": "fat_loss",
    "fitness_level": "beginner",
    "equipment": "none",
    "available_days": ["lundi", "mercredi", "vendredi"],
    "limitations": [],
    "session_duration_max_minutes": 60
  }'
```

Valeurs `objective` : `fat_loss`, `muscle_gain`, `endurance`, `general_health`, `flexibility`
Valeurs `fitness_level` : `beginner`, `intermediate`, `advanced`
Valeurs `equipment` : `none`, `home`, `gym`

### Transverse

| Méthode | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Health check |

---

## Stratégie de fallback IA

```
Vision alimentaire
  ├── 1. Hugging Face (nateraw/food)    → classification image Food-101
  ├── 2. Google Vision API              → label detection générique
  ├── 3. Mock (APP_ENV=development)     → données fictives si tout échoue
  └── 4. Erreur 503                     → en production si tout échoue

Génération de texte (messages personnalisés)
  ├── 1. Hugging Face (flan-t5-large)  → text-to-text
  ├── 2. Ollama local (llama3)          → LLM auto-hébergé
  └── 3. Message par défaut (hardcodé) → toujours disponible
```

---

## Tests

```bash
pytest
pytest --cov=app --cov-report=html
```

---

## Variables d'environnement

| Variable | Description | Défaut |
|---|---|---|
| `APP_ENV` | `development` / `production` | `development` |
| `APP_PORT` | Port d'écoute | `8085` |
| `MONGODB_URL` | URI MongoDB | `mongodb://localhost:27017` |
| `MONGODB_DB_NAME` | Nom de la base | `mspr_ia` |
| `HUGGINGFACE_API_TOKEN` | Token HF (obligatoire) | — |
| `HUGGINGFACE_FOOD_MODEL` | Modèle HF vision | `nateraw/food` |
| `GOOGLE_VISION_API_KEY` | Clé Google Vision (fallback) | — |
| `SPRING_BACKEND_URL` | URL backend Spring Boot | `http://localhost:8084` |
| `OLLAMA_URL` | URL Ollama local | `http://localhost:11434` |
| `OLLAMA_MODEL` | Modèle Ollama | `llama3` |
| `ALLOWED_ORIGINS` | Origins CORS (virgule) | `http://localhost:3000,...` |
| `RATE_LIMIT` | Limite requêtes/IP | `10/minute` |

---

## Architecture

```
app/
├── main.py                    # FastAPI, middleware, lifecycle
├── config.py                  # Settings Pydantic (.env)
├── database.py                # MongoDB Motor async
├── models/
│   ├── nutrition.py           # Modèles nutrition
│   └── sport.py               # Modèles sport
├── routers/
│   ├── nutrition.py           # /nutrition/*
│   ├── sport.py               # /sport/*
│   └── recommendations.py    # /health
├── services/
│   ├── vision.py              # HF → Google Vision → mock
│   ├── nlp.py                 # HF → Ollama → défaut
│   ├── nutrition_engine.py    # Moteur nutrition
│   ├── sport_engine.py        # Moteur sport
│   └── spring_client.py       # Client HTTP Java
└── repositories/
    └── recommendation_repository.py
```

---

## Résolution de problèmes

| Symptôme | Cause | Solution |
|---|---|---|
| `401` sur les appels IA | Token HF expiré | Régénérer sur huggingface.co/settings/tokens |
| `404` modèle HF | Mauvais nom de modèle | Vérifier `HUGGINGFACE_FOOD_MODEL` dans `.env` |
| `503` vision | HF + Google Vision indisponibles | Vérifier les tokens, ou passer en `APP_ENV=development` pour le mock |
| MongoDB absent | Non lancé | Normal en dev — service continue avec warning |
