# MSPR IA — Microservice de recommandations

Microservice Python / FastAPI fournissant des **recommandations nutritionnelles et sportives personnalisées** via :
- **Hugging Face Transformers** (vision alimentaire + NLP)
- **Google Vision API** (fallback vision)
- **Ollama** (fallback NLP local)
- **MongoDB** (persistance via Motor async)

Développé séparément du backend Spring Boot conformément au cahier des charges TPRE502.

---

## Stack technique

| Composant | Technologie |
|---|---|
| API | FastAPI 0.111 + Uvicorn |
| Base de données | MongoDB 7 (Motor async) |
| IA Vision | Hugging Face `google/vit-base-patch16-224` / Google Vision |
| IA NLP | Hugging Face `Mistral-7B-Instruct` / Ollama |
| Tests | Pytest + pytest-asyncio + httpx |
| Container | Docker + Docker Compose |

---

## Démarrage rapide

### 1. Prérequis

- Docker & Docker Compose
- Python 3.11+ (développement local)

### 2. Configuration

```bash
cp .env.example .env
# Éditer .env avec vos clés API et URLs
```

### 3. Lancer avec Docker Compose

```bash
# Production
docker-compose up -d

# Développement (inclut Mongo Express sur :8081)
docker-compose --profile dev up -d
```

### 4. Lancer en local (sans Docker)

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8085
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
| `http://localhost:8085/docs` | Swagger UI (interactif) |
| `http://localhost:8085/redoc` | ReDoc |
| `http://localhost:8085/openapi.json` | Schéma OpenAPI |

---

## Endpoints principaux

### Nutrition

| Méthode | Endpoint | Description |
|---|---|---|
| `POST` | `/nutrition/analyze-photo` | Analyse une photo de repas (multipart) |
| `POST` | `/nutrition/recommend` | Plan nutritionnel 7 jours personnalisé |

**Exemple — Générer un plan nutritionnel :**
```bash
curl -X POST http://localhost:8085/nutrition/recommend \
  -H "Content-Type: application/json" \
  -d '{
    "patient_id": "patient_001",
    "objective": "perte_de_poids",
    "allergies": ["gluten"],
    "diet_type": "omnivore",
    "daily_calories_target": 1600
  }'
```

### Sport

| Méthode | Endpoint | Description |
|---|---|---|
| `POST` | `/sport/recommend` | Programme sportif hebdomadaire |
| `PUT` | `/sport/feedback/{id}` | Soumettre un retour (progression adaptative) |

**Exemple — Générer un programme sportif :**
```bash
curl -X POST http://localhost:8085/sport/recommend \
  -H "Content-Type: application/json" \
  -d '{
    "patient_id": "patient_001",
    "objective": "fat_loss",
    "fitness_level": "beginner",
    "equipment": "none",
    "available_days": ["lundi", "mercredi", "vendredi"],
    "limitations": ["douleur genou droit"]
  }'
```

### Transverse

| Méthode | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Health check |
| `GET` | `/recommendations/{patient_id}` | Historique d'un patient |

---

## Tests

```bash
# Tests unitaires + intégration
pytest

# Avec rapport de couverture
pytest --cov=app --cov-report=html
# Rapport dans htmlcov/index.html
```

**Couverture actuelle :** 30 tests — 20 unitaires (nutrition + sport engine) + 10 d'intégration (endpoints).

---

## Interopérabilité avec Spring Boot

Le microservice est conçu pour être appelé depuis `RecommendationController` côté Spring :

```
Spring Boot (port 8080) → HTTP → FastAPI (port 8085)
```

Configurer `SPRING_BACKEND_URL` dans `.env` pour que le microservice puisse en retour interroger les données patients PostgreSQL via Spring.

---

## Variables d'environnement

| Variable | Description | Défaut |
|---|---|---|
| `MONGODB_URL` | URI MongoDB | `mongodb://localhost:27017` |
| `MONGODB_DB_NAME` | Nom de la base | `mspr_ia` |
| `HUGGINGFACE_API_TOKEN` | Token HF (obligatoire pour la vision) | — |
| `GOOGLE_VISION_API_KEY` | Clé Google Vision (fallback) | — |
| `SPRING_BACKEND_URL` | URL du backend Spring | `http://localhost:8080` |
| `OLLAMA_URL` | URL du serveur Ollama local | `http://localhost:11434` |
| `ALLOWED_ORIGINS` | CORS origins autorisées | `http://localhost:3000,...` |
| `RATE_LIMIT` | Limite de requêtes par IP | `10/minute` |
