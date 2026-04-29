# Guide d'apprentissage — Microservice IA MSPR

---

## 1. Vue d'ensemble

Ce microservice Python/FastAPI reçoit un profil patient et retourne :
- Un **plan de repas 7 jours** avec macronutriments calculés
- Un **programme sportif hebdomadaire** adapté au niveau et à l'équipement
- Une **analyse visuelle** de photo de repas (identification des aliments + macros)
- Un **message personnalisé** généré par IA (encouragement)

**Pourquoi un microservice séparé du Spring Boot ?**
Python dispose des meilleures bibliothèques IA (HuggingFace, etc.). Séparer permet de choisir la technologie adaptée à chaque domaine et de scaler indépendamment.

```
App mobile / Navigateur
       │
       ▼
Spring Boot :8080  (métier, PostgreSQL)
       │  HTTP POST JSON
       ▼
FastAPI :8085  (IA, recommandations, MongoDB)
```

---

## 2. Architecture en couches (SOLID)

```
Requête HTTP
     │
     ▼
routers/          → reçoit, valide (Pydantic), répond — ne connaît pas MongoDB directement
     │
     ▼
services/         → logique métier et appels IA — ne connaît pas FastAPI
     │
     ├── data/    → bases de connaissances (food_db, meal_templates, exercise_db)
     │              Étendre ici sans toucher aux services (OCP)
     └── repos/   → accès MongoDB — injectable et remplaçable (DIP)
```

**Principes SOLID appliqués :**
- **SRP** : chaque fichier a une seule responsabilité (données, logique, transport HTTP)
- **OCP** : ajouter un aliment → modifier `data/food_db.py` uniquement, pas le service
- **DIP** : les services dépendent d'abstractions (repository injecté via `Depends`)

---

## 3. FastAPI en bref

FastAPI génère automatiquement la validation, la sérialisation JSON et la doc Swagger.

```python
@router.post("/recommend", response_model=NutritionRecommendation, status_code=201)
async def recommend(profile: UserNutritionProfile, repo = Depends(get_repo)):
    result = await build_weekly_nutrition_plan(profile)
    await repo.save_meal_plan(result.model_dump())
    return result
```

`Depends()` injecte le repository — en test, on le remplace par un mock sans changer le code.

---

## 4. Programmation asynchrone

`async/await` permet de traiter plusieurs requêtes simultanément sans bloquer :

```
Req A → await appel HF    (en attente réseau → libère le thread)
Req B →  await MongoDB    (en attente DB    → s'exécute pendant que A attend)
```

Règle : toute I/O (HTTP, DB) doit être `await`. Jamais `time.sleep()` dans une coroutine.

---

## 5. Intelligence artificielle — notions clés

### Inférence vs Entraînement
On fait uniquement de l'**inférence** (utiliser un modèle déjà entraîné). Pas d'entraînement.

### Score de confiance
`{"label": "pizza", "score": 0.91}` = le modèle est sûr à 91 % que c'est une pizza.

### Hugging Face Inference API
On appelle les modèles via HTTP — pas besoin de GPU local :
```
Notre serveur → HTTP POST → HF API → Modèle GPU HF → JSON résultats
```
URL : `https://router.huggingface.co/hf-inference/models/{organisation}/{modèle}`

---

## 6. Vision par ordinateur (`vision.py`)

Le modèle `nateraw/food` est un **Vision Transformer (ViT)** fine-tuné sur Food-101 (101 catégories d'aliments).

**Cascade de fallback :**
1. Hugging Face (qualité supérieure)
2. Google Vision API (si token HF absent ou erreur)
3. Mock dev (si aucune clé configurée + `APP_ENV=development`)
4. Erreur 503 en production

Une fois les aliments détectés, `_enrich_food()` les associe aux données nutritionnelles de `data/food_db.py`.
La formule macros : `kcal = calories_100g × quantité_g / 100` (quantité assumée : 150 g).

---

## 7. NLP — génération de texte (`nlp.py`)

`google/flan-t5-large` est un modèle **seq2seq** : il reçoit un prompt et génère du texte court.

**Cascade :** HF flan-t5 (timeout 8 s) → Ollama local → message par défaut hardcodé.

**Prompt engineering** — structure à respecter :
1. Rôle : *« Tu es nutritionniste »*
2. Contrainte : *« 3-4 phrases en français »*
3. Contexte : *objectif du patient, notes nutritionnelles*
4. Ton : *positif, motivant*

`interpret_physical_limitations()` utilise le même LLM pour convertir *« jambe en moins »*
en mots-clés à exclure du programme sportif (`["jambes", "quadriceps", "course", …]`).

---

## 8. Moteurs de règles

### Pourquoi des règles et pas du ML ?
Les règles nutritionnelles et les contraindications médicales sont bien connues, interprétables et auditables. Un modèle ML nécessiterait des milliers d'exemples labellisés.

### Moteur nutritionnel (`nutrition_engine.py`)
1. Mappe l'objectif utilisateur (`"perte_de_poids"` → `"fat_loss"`)
2. Récupère les templates de `data/meal_templates.py`
3. Filtre selon régime et allergies (`EXCLUDED_BY_DIET`)
4. Rotation cyclique sur 7 jours pour éviter la répétition
5. Calcule les moyennes et détecte les déséquilibres (ratios ANSES/OMS)

### Moteur sportif (`sport_engine.py`)
1. Interprète les limitations via LLM → mots-clés exclus
2. Filtre `data/exercise_db.py` : équipement + niveau + objectif + contraindications
3. Attribue un type de séance par jour disponible (HIIT, Renforcement, Récupération, Repos)
4. Adapte la progression selon les feedbacks passés

---

## 9. Résilience et fallback

Règle : **ne jamais crasher sur une dépendance externe.**

| Situation | Comportement |
|---|---|
| HF retourne 503 (cold start) | Exception RuntimeError → fallback Google Vision |
| Google Vision absent | Fallback mock (dev) ou erreur 503 (prod) |
| MongoDB non disponible | Log warning, recommandation retournée quand même |
| NLP indisponible | Message par défaut hardcodé retourné |

---

## 10. MongoDB et repository pattern

MongoDB stocke des documents JSON imbriqués — adapté aux plans de repas et programmes sportifs sans schéma fixe.

`Motor` est le driver async de PyMongo. Le `RecommendationRepository` centralise tous les accès DB : les routers n'écrivent jamais de requêtes MongoDB directement. Cela permet de remplacer MongoDB en test par un mock sans changer les routers.

---

## 11. Sécurité

- **Variables d'environnement** : les clés API ne sont jamais dans le code (`.env` + pydantic-settings)
- **Rate limiting** : slowapi limite à 10 req/min par IP → protège les crédits HF
- **CORS** : origins autorisées configurées via `ALLOWED_ORIGINS`
- **Utilisateur non-root** dans Docker : limite l'impact d'une faille applicative

---

## 12. Tests

```
tests/
├── conftest.py              # fixtures partagées
├── test_endpoints.py        # tests d'intégration (routes HTTP via ASGITransport)
├── test_nutrition_engine.py # tests unitaires du moteur nutritionnel
└── test_sport_engine.py     # tests unitaires du moteur sportif
```

```bash
pytest tests/test_nutrition_engine.py tests/test_sport_engine.py  # unitaires (rapides)
pytest tests/test_endpoints.py                                     # intégration
pytest --cov=app --cov-report=html                                 # avec couverture
python test_api_manual.py                                          # test manuel complet
```

---

## 13. Résumé des technologies IA

| Notion | Technologie | Fichier |
|---|---|---|
| Classification d'images | ViT `nateraw/food` | `services/vision.py` |
| Génération de texte | Flan-T5 seq2seq | `services/nlp.py` |
| Recommandations par règles | Expert system | `services/nutrition_engine.py`, `sport_engine.py` |
| Données du domaine | Dictionnaires Python | `data/food_db.py`, `meal_templates.py`, `exercise_db.py` |
| Fallback en cascade | Architecture | `vision.py`, `nlp.py` |
| Progression adaptative | Feedback loop | `services/sport_engine.py` |
