# Guide d'apprentissage — Microservice IA MSPR

Ce document explique en profondeur le code développé, les choix d'architecture, et les notions
d'intelligence artificielle mises en œuvre. Il est conçu pour permettre à quelqu'un de comprendre
le projet de zéro, même sans expérience préalable en IA ou en FastAPI.

---

## Table des matières

1. [Vue d'ensemble du projet](#1-vue-densemble-du-projet)
2. [FastAPI — le framework](#2-fastapi--le-framework)
3. [Programmation asynchrone en Python](#3-programmation-asynchrone-en-python)
4. [Pydantic — validation et sérialisation](#4-pydantic--validation-et-sérialisation)
5. [Architecture en couches](#5-architecture-en-couches)
6. [Intelligence artificielle — notions fondamentales](#6-intelligence-artificielle--notions-fondamentales)
7. [Vision par ordinateur — reconnaissance alimentaire](#7-vision-par-ordinateur--reconnaissance-alimentaire)
8. [NLP — génération de texte personnalisé](#8-nlp--génération-de-texte-personnalisé)
9. [Moteur de recommandations par règles](#9-moteur-de-recommandations-par-règles)
10. [Stratégie de fallback et résilience](#10-stratégie-de-fallback-et-résilience)
11. [MongoDB et persistance asynchrone](#11-mongodb-et-persistance-asynchrone)
12. [Sécurité et bonne pratiques API](#12-sécurité-et-bonnes-pratiques-api)
13. [Docker et containerisation](#13-docker-et-containerisation)
14. [Tests et qualité du code](#14-tests-et-qualité-du-code)
15. [Flux complets de bout en bout](#15-flux-complets-de-bout-en-bout)

---

## 1. Vue d'ensemble du projet

### Qu'est-ce que ce microservice fait ?

Il reçoit des données sur un patient (objectif, régime, niveau sportif…) et retourne :

- Un **plan de repas sur 7 jours** avec macronutriments calculés
- Un **programme sportif hebdomadaire** adapté au niveau et à l'équipement
- Une **analyse visuelle** d'une photo de repas (identification des aliments)
- Un **message personnalisé** généré par IA pour motiver le patient

### Pourquoi un microservice séparé ?

Le backend principal est en **Spring Boot (Java)**. La logique IA (vision, NLP, moteur de règles)
est plus naturellement développée en Python qui dispose des meilleures bibliothèques IA
(HuggingFace, PyTorch, etc.). Séparer en microservice permet :

- De choisir la technologie la plus adaptée à chaque domaine
- De déployer et scaler indépendamment
- De ne pas alourdir le backend métier avec des dépendances IA volumineuses

### Communication inter-services

```
Navigateur / App mobile
        │
        ▼
Spring Boot :8080  (logique métier, PostgreSQL)
        │  HTTP POST JSON
        ▼
FastAPI :8085  (IA, recommandations, MongoDB)
```

---

## 2. FastAPI — le framework

### Qu'est-ce que FastAPI ?

FastAPI est un framework Python moderne pour construire des APIs REST. Il est bâti sur :
- **Starlette** (routing HTTP asynchrone)
- **Pydantic** (validation des données)
- **OpenAPI** (documentation automatique)

### Déclaration d'une route

```python
# app/routers/nutrition.py
from fastapi import APIRouter

router = APIRouter(prefix="/nutrition", tags=["Nutrition"])

@router.post(
    "/recommend",
    response_model=NutritionRecommendation,   # Pydantic valide la réponse
    status_code=201,
)
async def recommend_nutrition(profile: UserNutritionProfile) -> NutritionRecommendation:
    # FastAPI désérialise automatiquement le JSON du corps de la requête
    # vers le modèle Pydantic UserNutritionProfile
    recommendation = await build_weekly_nutrition_plan(profile)
    return recommendation
```

**Ce que FastAPI fait automatiquement :**
- Lit et valide le JSON entrant (type, champs requis, contraintes)
- Génère une erreur 422 si la validation échoue, avec le détail des champs invalides
- Sérialise la réponse Python en JSON
- Génère la documentation Swagger et ReDoc sans configuration supplémentaire

### Injection de dépendances

```python
# Pattern Depends() — FastAPI instancie et injecte automatiquement
def get_repo() -> RecommendationRepository:
    return RecommendationRepository(get_db())

@router.post("/recommend")
async def recommend_nutrition(
    profile: UserNutritionProfile,
    repo: RecommendationRepository = Depends(get_repo),  # injection
):
    ...
```

`Depends()` permet de centraliser la création d'objets (connexions DB, services) et de les
réutiliser facilement en test en les remplaçant par des mocks.

### Application principale

```python
# app/main.py
app = FastAPI(title="MSPR IA", version="1.0.0")

@app.on_event("startup")
async def startup():
    await connect_db()   # appelé une seule fois au démarrage du serveur

@app.on_event("shutdown")
async def shutdown():
    await close_db()     # nettoyage propre des connexions
```

---

## 3. Programmation asynchrone en Python

### Pourquoi async/await ?

Un serveur web traite souvent des dizaines de requêtes simultanément. Si chaque requête fait
appel à une API externe (HuggingFace, MongoDB), attendre le résultat de façon bloquante signifie
qu'un seul thread ne peut traiter qu'une requête à la fois.

L'**I/O asynchrone** permet de libérer le thread pendant l'attente :

```
Requête A : envoi → [attend réponse HF] → traitement → réponse
Requête B :         envoi → [attend réponse MongoDB] → traitement → réponse
                  ↑ Pendant que A attend, B peut avancer
```

### async / await en pratique

```python
# Fonction synchrone (bloquante) — mauvais pour un serveur
def call_api_sync():
    response = requests.post(url, ...)  # bloque le thread pendant 2s
    return response.json()

# Fonction asynchrone (non-bloquante) — correct
async def call_api_async():
    async with httpx.AsyncClient() as client:
        response = await client.post(url, ...)  # libère le thread pendant l'attente
    return response.json()
```

`await` signifie : "lance cette opération, et pendant qu'elle tourne, passe à autre chose".

### L'event loop

Python utilise une **boucle d'événements** (event loop) qui gère la concurrence :

```
Event Loop
    ├── Requête 1 → await appel HF    (en attente réseau)
    ├── Requête 2 → await appel MongoDB (en attente DB)
    └── Requête 3 → calcul CPU        (s'exécute maintenant)
```

Uvicorn (le serveur ASGI qui lance FastAPI) gère cette event loop.

### Pièges courants

```python
# ERREUR : fonction synchrone bloquante dans une coroutine
async def bad():
    time.sleep(5)        # bloque TOUT le serveur pendant 5s

# CORRECT : version asynchrone
async def good():
    await asyncio.sleep(5)   # libère l'event loop pendant 5s
```

Dans `database.py`, `create_index` de PyMongo est synchrone et tourne dans un thread pool
(via Motor) pour ne pas bloquer l'event loop.

---

## 4. Pydantic — validation et sérialisation

### Rôle de Pydantic

Pydantic transforme des dictionnaires Python/JSON en objets typés et validés :

```python
# app/models/nutrition.py
from pydantic import BaseModel, Field
from typing import Optional, List
from enum import Enum

class DietType(str, Enum):
    omnivore = "omnivore"
    vegan = "vegan"
    # ...

class UserNutritionProfile(BaseModel):
    patient_id: str
    objective: str = Field(description="ex: perte_de_poids, prise_de_masse")
    allergies: List[str] = Field(default_factory=list)   # liste vide par défaut
    daily_calories_target: Optional[float] = None        # champ optionnel
    diet_type: DietType = DietType.omnivore              # valeur par défaut
```

**Quand FastAPI reçoit ce JSON :**
```json
{
  "patient_id": "123",
  "objective": "perte_de_poids",
  "diet_type": "vegan",
  "daily_calories_target": "abc"
}
```

Pydantic retourne automatiquement :
```json
{
  "detail": [{"loc": ["body", "daily_calories_target"], "msg": "value is not a valid float"}]
}
```

### Contraintes de validation

```python
class FoodItem(BaseModel):
    confidence: float = Field(ge=0.0, le=1.0)  # entre 0 et 1 obligatoirement
    calories_per_100g: Optional[float] = None

class FeedbackRequest(BaseModel):
    rating: int = Field(ge=1, le=5)  # note entre 1 et 5
```

### Sérialisation

```python
recommendation = NutritionRecommendation(patient_id="p1", weekly_plan=[...], ...)
# FastAPI appelle automatiquement recommendation.model_dump() pour la réponse JSON
```

---

## 5. Architecture en couches

```
HTTP Request
     │
     ▼
┌─────────────────────────────┐
│         ROUTERS             │  Reçoit la requête HTTP, valide via Pydantic,
│  nutrition.py, sport.py     │  appelle les services, retourne la réponse
└─────────────┬───────────────┘
              │
              ▼
┌─────────────────────────────┐
│         SERVICES            │  Logique métier et intégration IA
│  vision.py, nlp.py,         │  N'a aucune connaissance de HTTP
│  nutrition_engine.py,       │
│  sport_engine.py            │
└─────────────┬───────────────┘
              │
     ┌────────┴────────┐
     ▼                 ▼
┌──────────┐    ┌──────────────┐
│ REPO     │    │  APIs IA     │
│ MongoDB  │    │  HuggingFace │
│ Motor    │    │  Google      │
└──────────┘    └──────────────┘
```

**Principe de séparation :**
- Les routers ne connaissent pas MongoDB directement — ils reçoivent un repository injecté
- Les services ne connaissent pas FastAPI — ils peuvent être testés sans serveur HTTP
- Les modèles Pydantic définissent le contrat de données entre toutes les couches

---

## 6. Intelligence artificielle — notions fondamentales

### Qu'est-ce qu'un modèle IA ?

Un modèle IA est une fonction mathématique entraînée sur des données :

```
Image de pizza  →  [Modèle IA]  →  {"pizza": 0.91, "bread": 0.06, "cake": 0.03}
```

Le modèle a été entraîné sur des millions d'images avec leurs labels (supervisé). Il a appris
à associer des patterns visuels à des catégories.

### Inférence vs Entraînement

- **Entraînement** : process long (heures à semaines sur GPU) pour ajuster les poids du modèle
- **Inférence** : utiliser un modèle déjà entraîné pour prédire sur de nouvelles données (rapide)

Dans ce projet, on fait uniquement de **l'inférence** — on n'entraîne pas de modèles.

### Score de confiance

```json
{"label": "pizza", "score": 0.91}
```

Le score représente la **probabilité** que le modèle attribue à cette prédiction.
Un score de 0.91 signifie que le modèle est sûr à 91% que l'image contient de la pizza.

Dans le code, on filtre les prédictions avec un score trop bas :
```python
# vision.py
foods = [
    _enrich_food(pred["label"], pred["score"])
    for pred in predictions[:8]
    if pred.get("score", 0) > 0.02   # on ignore les classes très improbables
]
```

### Hugging Face

**Hugging Face** est une plateforme hébergeant des milliers de modèles IA open-source.
Elle propose une **Inference API** qui permet d'appeler ces modèles via HTTP sans avoir à
les télécharger ou à gérer un GPU.

```
Notre serveur → HTTP POST image → HF Inference API → Modèle GPU HF → JSON résultats
```

URL de l'API (format actuel) :
```
https://router.huggingface.co/hf-inference/models/{organisation}/{modèle}
```

> L'URL historique `api-inference.huggingface.co/models/…` a été migrée vers
> `router.huggingface.co/hf-inference/models/…` en 2024-2025.

---

## 7. Vision par ordinateur — reconnaissance alimentaire

### Comment fonctionne la classification d'images ?

Le modèle utilisé (`nateraw/food`) est un **Vision Transformer (ViT)** fine-tuné sur **Food-101**,
un dataset de 101 000 photos de repas dans 101 catégories.

**Architecture ViT (simplifié) :**

```
Image (224×224 px)
     │
     ▼
Découpage en patches (16×16 px chacun)     ← 196 patches pour une image 224×224
     │
     ▼
Encodage linéaire de chaque patch          ← transformation en vecteurs numériques
     │
     ▼
Transformer (attention multi-têtes)         ← chaque patch "regarde" tous les autres
     │
     ▼
Tête de classification (MLP)
     │
     ▼
Softmax → probabilités par classe          ← pizza: 0.91, bread: 0.06, …
```

Le **Transformer** est la même architecture que dans les LLMs (GPT, BERT). Appliqué aux images,
il apprend les relations spatiales entre les différentes parties d'une image.

### Implémentation dans `vision.py`

```python
async def _call_huggingface(image_bytes: bytes) -> List[FoodItem]:
    """Envoie l'image brute à l'API HF et reçoit les classifications."""
    api_url = f"https://router.huggingface.co/hf-inference/models/{settings.huggingface_food_model}"
    headers = {
        "Authorization": f"Bearer {settings.huggingface_api_token}",
        "Content-Type": "application/octet-stream",   # image brute, pas de JSON
    }

    async with httpx.AsyncClient(timeout=45) as client:
        response = await client.post(api_url, headers=headers, content=image_bytes)
    # L'API retourne : [{"label": "pizza", "score": 0.91}, {"label": "bread", "score": 0.06}, ...]
```

**Pourquoi `Content-Type: application/octet-stream` ?**
Les modèles de classification d'images sur HF reçoivent les bytes bruts de l'image,
pas un JSON avec base64. C'est plus efficace (pas d'overhead d'encodage).

### Enrichissement nutritionnel

Une fois les aliments détectés, on les enrichit avec des données nutritionnelles :

```python
FOOD_NUTRITION_DB = {
    "pizza": {"calories_per_100g": 266, "proteins_g": 11, "carbs_g": 33, "fats_g": 10},
    "chicken": {"calories_per_100g": 165, "proteins_g": 31, "carbs_g": 0, "fats_g": 3.6},
    # ...
}

def _enrich_food(label: str, confidence: float) -> FoodItem:
    key = _normalize_label(label)          # "spaghetti carbonara" → "carbonara"
    nutrition = FOOD_NUTRITION_DB.get(key, {})
    return FoodItem(name=label, confidence=confidence, quantity_g=150.0, **nutrition)
```

**Normalisation des labels :**
HF retourne parfois `"carbonara, spaghetti carbonara"` — on cherche le fragment le plus long
qui correspond à une entrée de la base, puis on essaie mot par mot.

### Calcul des macronutriments totaux

```python
# nutrition.py (router)
total_calories = sum(
    (f.calories_per_100g or 0) * (f.quantity_g or 150) / 100
    for f in foods
)
```

La formule est `kcal = (calories_pour_100g × quantité_en_grammes) / 100`.
On assume 150g par aliment faute de détection de la portion.

---

## 8. NLP — génération de texte personnalisé

### Qu'est-ce que le NLP ?

**NLP (Natural Language Processing)** = traitement automatique du langage naturel.
Ici on l'utilise pour générer un message d'encouragement personnalisé pour chaque patient.

### Modèle utilisé : Flan-T5

`google/flan-t5-large` est un modèle **seq2seq** (séquence vers séquence) :
- **Entrée** : un texte d'instruction (prompt)
- **Sortie** : un texte généré

```
Prompt : "Tu es nutritionniste. Rédige un message d'encouragement
          pour un patient dont l'objectif est perte_de_poids.
          Points nutritionnels : ✅ Équilibre satisfaisant."

Réponse : "Bravo pour vos efforts ! Votre alimentation équilibrée vous
           aidera à atteindre votre objectif de perte de poids..."
```

**Différence avec GPT / ChatGPT :**
- GPT est un modèle **autorégressif** (génère mot par mot, très long)
- Flan-T5 est **encoder-decoder** (encode le prompt entier, puis décode la réponse)
- T5 est plus rapide mais moins créatif que GPT

### Implémentation dans `nlp.py`

```python
async def _call_huggingface_nlp(prompt: str, max_tokens: int = 200) -> Optional[str]:
    api_url = "https://router.huggingface.co/hf-inference/models/google/flan-t5-large"
    payload = {
        "inputs": prompt,
        "parameters": {
            "max_new_tokens": max_tokens,
            "temperature": 0.7,    # créativité : 0 = déterministe, 1 = très créatif
        },
    }
    try:
        async with httpx.AsyncClient(timeout=8) as client:  # 8s max
            response = await client.post(api_url, headers=headers, json=payload)
        ...
        if isinstance(data, list) and data:
            generated = data[0].get("generated_text", "").strip()
            if generated and generated != prompt:   # éviter la répétition du prompt
                return generated
    except Exception as exc:
        logger.warning("NLP HF indisponible : %s", exc)
    return None   # None = tomber sur le fallback
```

**Pourquoi timeout=8s ?**
Flan-T5 large peut prendre 5-15s selon la charge sur HF (cold start du modèle).
8 secondes est un compromis : assez long pour laisser le modèle répondre dans la plupart
des cas, assez court pour ne pas bloquer l'utilisateur.

### Prompt engineering

La qualité de la réponse dépend fortement de la formulation du prompt :

```python
# Prompt nutritionnel — structure claire avec rôle + consigne + contexte
prompt = (
    f"Tu es un nutritionniste bienveillant. "
    f"Rédige un court message d'encouragement (3-4 phrases) en français "
    f"pour un patient dont l'objectif est '{objective}'. "
    f"Points nutritionnels importants : {balance_notes}. "
    f"Le message doit être positif, motivant et pratique."
)
```

**Bonnes pratiques de prompt :**
1. Définir un **rôle** ("Tu es un nutritionniste")
2. Donner des **contraintes claires** (3-4 phrases, en français)
3. Fournir le **contexte** (objectif du patient, notes nutritionnelles)
4. Préciser le **ton** souhaité (positif, motivant)

### Fallback Ollama

Si HF est indisponible, le service essaie **Ollama** — un outil pour faire tourner des LLMs
en local (Llama3, Mistral, etc.) :

```python
async def _call_ollama(prompt: str) -> Optional[str]:
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(
            f"{settings.ollama_url}/api/generate",
            json={"model": settings.ollama_model, "prompt": prompt, "stream": False},
        )
        return response.json().get("response", "").strip()
```

Si Ollama n'est pas installé, la connexion échoue immédiatement (connection refused) et on
passe au message par défaut hardcodé.

---

## 9. Moteur de recommandations par règles

### Approche hybride IA + règles

Le moteur de recommandations **n'utilise pas d'IA** pour choisir les repas ou les exercices.
Il utilise un **système de règles métier** (expert system) :

```
Profil patient →  Règles de filtrage → Plan hebdomadaire
                  Calcul macros       + Message IA personnalisé
                  Détection déséquilibres
```

**Pourquoi des règles plutôt que du ML ?**
- Les règles nutritionnelles sont **bien connues** (AJR, besoins par objectif)
- Les exercices ont des **contraindications médicales** précises
- Un modèle ML nécessiterait des milliers d'exemples labellisés de plans corrects
- Les règles sont **interprétables** et **auditables** par des professionnels de santé

### Moteur nutritionnel (`nutrition_engine.py`)

#### Structure des templates

```python
MEAL_TEMPLATES = {
    "fat_loss": {
        "breakfast": [
            {
                "name": "Bol de flocons d'avoine aux fruits rouges",
                "foods": ["flocons d'avoine", "lait écrémé", "fraises"],
                "macros": Macros(calories=320, proteins_g=14, carbs_g=52, fats_g=6),
            },
            # ... 2 autres options de petit-déjeuner
        ],
        "lunch": [...],
        "dinner": [...],
        "snack": [...],
    },
    "muscle_gain": {...},
    "maintenance": {...},
}
```

#### Filtrage par régime alimentaire

```python
def _filter_meals_for_diet(meals, diet_type, allergies):
    excluded_by_diet = {
        DietType.vegan: ["poulet", "bœuf", "saumon", "lait", "fromage", "œuf", ...],
        DietType.vegetarian: ["poulet", "bœuf", "saumon", ...],  # garde les œufs/laitages
        DietType.gluten_free: ["pain", "pâtes", "crackers", "wrap", ...],
        DietType.lactose_free: ["lait", "fromage", "yaourt", ...],
    }

    exclusions = excluded_by_diet.get(diet_type, []) + [a.lower() for a in allergies]

    filtered = []
    for meal in meals:
        foods_lower = [f.lower() for f in meal["foods"]]
        if not any(exc in " ".join(foods_lower) for exc in exclusions):
            filtered.append(meal)
    return filtered or meals  # si tout est filtré, retourner tout plutôt que rien
```

#### Rotation pour éviter la répétition

```python
for i, day_name in enumerate(DAYS):  # i = 0 (lundi) à 6 (dimanche)
    for meal_type in ["breakfast", "lunch", "dinner", "snack"]:
        options = templates.get(meal_type, [])
        template = options[i % len(options)]  # rotation cyclique
```

Si on a 3 options de petit-déjeuner et 7 jours :
- Lundi (i=0) : option 0
- Mardi (i=1) : option 1
- Mercredi (i=2) : option 2
- Jeudi (i=3) : option 0 (retour au début)
- ...

#### Détection des déséquilibres nutritionnels

```python
def _detect_imbalances(macros, target_calories, objective_key):
    # Calcul des ratios macronutriments
    protein_ratio = macros.proteins_g * 4 / macros.calories   # 4 kcal par gramme de protéine
    carb_ratio = macros.carbs_g * 4 / macros.calories
    fat_ratio = macros.fats_g * 9 / macros.calories            # 9 kcal par gramme de lipide

    notes = []
    if objective_key == "fat_loss":
        if protein_ratio < 0.25:
            notes.append("⚠️ Apport protéique insuffisant pour préserver la masse musculaire")
        if carb_ratio > 0.55:
            notes.append("⚠️ Glucides légèrement élevés pour un objectif perte de poids")
    # ...
```

Ces seuils sont basés sur les **recommandations nutritionnelles standard** (ANSES, OMS) :
- Protéines : 15-35% des calories totales
- Glucides : 40-55% (moins en perte de poids)
- Lipides : 20-35%

### Moteur sportif (`sport_engine.py`)

#### Base d'exercices avec métadonnées

```python
EXERCISE_DB = {
    "push_up": {
        "name": "Pompes",
        "sets": 3, "reps": "8-15", "rest_seconds": 60,
        "muscles_targeted": ["pectoraux", "triceps", "épaules"],
        "equipment": "none",                         # sans matériel
        "level": ["beginner", "intermediate", "advanced"],
        "objectives": ["muscle_gain", "general_health"],
        "contraindications": ["douleur épaule", "tunnel carpien"],
    },
    "deadlift": {
        "equipment": "gym",
        "level": ["intermediate", "advanced"],
        "contraindications": ["hernie discale", "douleur lombaire"],
    },
    # 20+ exercices avec leurs métadonnées complètes
}
```

#### Filtrage multi-critères

```python
def _filter_exercises(objective, level, equipment, limitations):
    filtered = []
    for key, ex in EXERCISE_DB.items():
        # 1. Équipement disponible
        if equipment == Equipment.none and ex["equipment"] not in ["none"]:
            continue

        # 2. Niveau de l'utilisateur
        if level.value not in ex["level"]:
            continue

        # 3. Objectif sportif
        if objective.value not in ex["objectives"]:
            continue

        # 4. Contre-indications médicales
        excluded = False
        for contra in ex["contraindications"]:
            if any(lim in contra.lower() or contra.lower() in lim
                   for lim in [l.lower() for l in limitations]):
                excluded = True
                break
        if not excluded:
            filtered.append({**ex, "key": key})

    return filtered
```

**Matching des contra-indications :**
Si le patient déclare `"douleur genou droit"`, l'exercice avec contra `"douleur genou"` est
exclu (correspondance partielle bidirectionnelle).

#### Progression adaptative

```python
def _compute_progression_notes(level, objective, feedbacks=[]):
    base = {
        FitnessLevel.beginner: "Commencez avec des charges légères. Maîtrisez la technique...",
        FitnessLevel.intermediate: "Augmentez la charge de 2.5-5% dès que vous réussissez...",
        FitnessLevel.advanced: "Variez les techniques (drop-sets, super-sets)...",
    }
    note = base[level]

    if feedbacks:
        avg_rating = sum(f.rating for f in feedbacks) / len(feedbacks)
        if avg_rating >= 4 and any(f.too_easy for f in feedbacks):
            note += " | Retours positifs : augmentez l'intensité dès la prochaine séance."
        elif avg_rating <= 2 and any(f.too_hard for f in feedbacks):
            note += " | Programme trop difficile : réduisez la charge de 10-15%."
    return note
```

---

## 10. Stratégie de fallback et résilience

### Principe général

Dans un système qui dépend de services tiers (APIs), il faut toujours prévoir le cas où
ces services sont indisponibles. Une bonne stratégie de fallback :

1. **Tente** l'API principale
2. **Attrape** l'exception si elle échoue
3. **Essaie** un service alternatif
4. **Retourne** une valeur dégradée acceptable si tout échoue
5. **Ne crashe jamais** sur une dépendance externe

### Cascade vision

```python
async def analyze_food_image(image_bytes: bytes):
    last_error = "Aucune API configurée."

    # 1. Hugging Face (qualité supérieure)
    try:
        foods = await _call_huggingface(image_bytes)
        if foods:
            return foods, "huggingface"
        last_error = "HF n'a rien détecté."
    except RuntimeError as exc:         # 503 cold start, modèle en chargement
        last_error = str(exc)
        logger.warning("HF indisponible : %s", exc)
    except Exception as exc:            # 401, 404, timeout réseau, etc.
        last_error = str(exc)
        logger.warning("Erreur HF : %s", exc)

    # 2. Google Vision (fallback)
    try:
        foods = await _call_google_vision(image_bytes)
        if foods:
            return foods, "google_vision"
    except Exception as exc:
        last_error = str(exc)

    # 3. Mock uniquement si AUCUNE clé API configurée (mode dev sans clés)
    no_api = not settings.huggingface_api_token and not settings.google_vision_api_key
    if settings.app_env in ("development", "dev") and no_api:
        return _mock_analysis()

    # 4. Erreur structurée en production ou avec clé invalide
    raise RuntimeError(f"Aucune API disponible. Dernière erreur : {last_error}")
```

### Gestion des erreurs HuggingFace

| Code HTTP | Signification | Traitement |
|---|---|---|
| 200 | Succès | Retourner les prédictions |
| 401 | Token invalide/expiré | Exception → fallback |
| 503 + `estimated_time` | Modèle en cold start HF | Exception RuntimeError avec message "réessayez dans Xs" |
| 503 sans body JSON | Surcharge serveur HF | Exception → fallback |
| Timeout réseau | Serveur HF trop lent | Exception httpx.TimeoutException → fallback |

### MongoDB non-bloquant

```python
# database.py
async def connect_db():
    global _client, _db
    _client = AsyncIOMotorClient(settings.mongodb_url, serverSelectionTimeoutMS=5000)
    _db = _client[settings.mongodb_db_name]

    try:
        await _db.recommendations.create_index(...)  # tente de créer les index
        logger.info("MongoDB connecté")
    except Exception as exc:
        logger.warning("MongoDB non disponible — persistence désactivée")
        # _db est quand même défini, mais les opérations DB échoueront plus tard
```

```python
# routers/nutrition.py — sauvegarde non fatale
try:
    await repo.save_recommendation({...})
except Exception as exc:
    logger.warning("Impossible de sauvegarder en MongoDB : %s", exc)
    # On continue et retourne quand même le résultat au client
```

**Principe :** la recommandation générée a de la valeur même si elle n'est pas persistée.
Mieux vaut répondre sans sauvegarder que de faire échouer toute la requête.

---

## 11. MongoDB et persistance asynchrone

### Pourquoi MongoDB ?

Les recommandations sont des documents JSON de structure variable :

```json
{
  "patient_id": "p001",
  "type": "nutrition_plan",
  "weekly_plan": [
    {
      "day": "Lundi",
      "meals": [
        {"name": "Bol d'avoine", "macros": {"calories": 320, ...}},
        ...
      ]
    }
  ]
}
```

Ce document imbriqué est difficile à modéliser en SQL (PostgreSQL). MongoDB stocke
nativement des documents JSON (BSON), ce qui correspond exactement à la structure des données.

### Motor — driver async

```python
# Motor est le wrapper async de PyMongo pour asyncio
from motor.motor_asyncio import AsyncIOMotorClient

client = AsyncIOMotorClient("mongodb://localhost:27017")
db = client["mspr_ia"]

# Insertion (async)
result = await db.recommendations.insert_one(document)
print(result.inserted_id)  # ObjectId MongoDB

# Requête (async)
cursor = db.recommendations.find({"patientId": "p001"}).sort("created_at", -1).limit(50)
docs = await cursor.to_list(length=50)
```

### Repository Pattern

```python
# repositories/recommendation_repository.py
class RecommendationRepository:
    """Encapsule tous les accès MongoDB. Les routers n'écrivent jamais de requêtes MongoDB directement."""

    def __init__(self, db: AsyncIOMotorDatabase):
        self.recommendations = db.recommendations
        self.meal_plans = db.meal_plans
        self.sport_programs = db.sport_programs

    async def save_recommendation(self, data: dict) -> str:
        data["created_at"] = datetime.utcnow()
        result = await self.recommendations.insert_one(data)
        return str(result.inserted_id)
```

**Avantages du repository pattern :**
- On peut remplacer MongoDB par PostgreSQL sans toucher aux routers
- Les tests unitaires peuvent injecter un mock du repository
- La logique de requête est centralisée et réutilisable

### Index MongoDB

```python
await db.recommendations.create_index(
    [("patientId", ASCENDING), ("created_at", ASCENDING)]
)
```

Sans index, une requête `find({"patientId": "p001"})` scanne toute la collection.
Avec un index sur `patientId`, MongoDB accède directement aux documents concernés.

---

## 12. Sécurité et bonnes pratiques API

### Rate limiting

```python
# main.py
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address, default_limits=["10/minute"])
app.state.limiter = limiter
```

Sans rate limiting, un attaquant pourrait appeler `/nutrition/recommend` en boucle,
consommant tous les crédits HuggingFace ou surchargeant le serveur.
`slowapi` compte les requêtes par adresse IP et retourne 429 (Too Many Requests) au-delà du seuil.

### CORS

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,  # ["http://localhost:3000", "http://localhost:8080"]
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)
```

**CORS (Cross-Origin Resource Sharing)** : un navigateur bloque par défaut les requêtes
vers un domaine différent. Le header `Access-Control-Allow-Origin` indique quels domaines
peuvent appeler l'API. En production, remplacer `*` par les domaines exacts.

### Variables d'environnement

```python
# config.py — Pydantic Settings lit automatiquement .env
class Settings(BaseSettings):
    huggingface_api_token: str = ""  # jamais en dur dans le code !
    google_vision_api_key: str = ""

settings = Settings()  # chargement au démarrage
```

**Pourquoi ne jamais mettre une clé API dans le code ?**
- Le code est souvent versionné sur Git (public ou interne)
- Une clé commitée peut être extraite de l'historique même après suppression
- Les variables d'environnement sont injectées au runtime sans apparaître dans le code

### Gestion globale des erreurs

```python
# main.py
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception("Erreur non gérée : %s", exc)
    return JSONResponse(
        status_code=500,
        content={"detail": "Erreur interne du serveur. Veuillez réessayer."},
    )
```

Ce handler attrape toute exception non gérée et retourne un message générique au client
(sans exposer la stack trace) tout en la loggant côté serveur.

---

## 13. Docker et containerisation

### Dockerfile multi-stage

```dockerfile
# Étape 1 : builder — installe les dépendances dans un environnement isolé
FROM python:3.11-slim AS builder
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends gcc
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Étape 2 : image finale — copie seulement le nécessaire
FROM python:3.11-slim
WORKDIR /app
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY app/ ./app/
```

**Pourquoi multi-stage ?**
L'étape builder a besoin de `gcc` pour compiler certaines dépendances Python.
L'image finale n'en a plus besoin. Sans multi-stage, l'image finale inclurait `gcc` inutilement
(+200 MB). Avec multi-stage, l'image finale est plus petite et la surface d'attaque est réduite.

### Utilisateur non-root

```dockerfile
RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser
USER appuser
```

Par défaut, les containers Docker tournent en root. Si un attaquant exploite une vulnérabilité
dans l'application, il obtiendrait des droits root dans le container (dangereux si le container
partage des volumes avec l'hôte). Un utilisateur non-root limite l'impact.

### Health check

```dockerfile
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
  CMD python -c "import httpx; httpx.get('http://localhost:8085/health').raise_for_status()"
```

Docker Compose et Kubernetes utilisent ce health check pour savoir si le container est
opérationnel avant de lui envoyer du trafic.

### Docker Compose

```yaml
# docker-compose.yml
services:
  fastapi:
    build: .
    ports:
      - "8085:8085"
    env_file: .env
    depends_on:
      - mongo
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8085/health"]

  mongo:
    image: mongo:7
    volumes:
      - mongo_data:/data/db   # persistance des données entre redémarrages
```

`depends_on` garantit que MongoDB démarre avant FastAPI. Mais cela ne garantit pas que
MongoDB est *prêt* à accepter des connexions — c'est pourquoi le code a une gestion
de l'indisponibilité MongoDB (voir section 10).

---

## 14. Tests et qualité du code

### Structure des tests

```
tests/
├── conftest.py              # fixtures partagées (client HTTP de test, mocks)
├── test_endpoints.py        # tests d'intégration (routes HTTP)
├── test_nutrition_engine.py # tests unitaires du moteur nutritionnel
└── test_sport_engine.py     # tests unitaires du moteur sportif
```

### Test d'intégration (endpoint)

```python
# tests/test_endpoints.py
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app

@pytest.mark.asyncio
async def test_nutrition_recommend():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/nutrition/recommend", json={
            "patient_id": "p1",
            "objective": "perte_de_poids",
            "diet_type": "omnivore",
        })
    assert response.status_code == 201
    data = response.json()
    assert "weekly_plan" in data
    assert len(data["weekly_plan"]) == 7
```

`ASGITransport` permet d'appeler l'application FastAPI directement en mémoire,
sans réseau réel — rapide et fiable.

### Test unitaire (service)

```python
# tests/test_nutrition_engine.py
import pytest
from app.services.nutrition_engine import _filter_meals_for_diet
from app.models.nutrition import DietType

def test_filter_vegan_excludes_chicken():
    meals = [
        {"name": "Salade poulet", "foods": ["poulet grillé", "salade"]},
        {"name": "Tofu légumes", "foods": ["tofu", "courgettes"]},
    ]
    result = _filter_meals_for_diet(meals, DietType.vegan, allergies=[])
    assert len(result) == 1
    assert result[0]["name"] == "Tofu légumes"
```

### Test manuel avec script

```bash
# Avec le serveur qui tourne :
python test_api_manual.py

# Sortie attendue :
# [1] GET /health ...       ✅ OK
# [2] POST /nutrition/analyze-photo ...  ✅ OK  (mock ou HF selon la config)
# [3] POST /nutrition/recommend ...      ✅ OK
# [4] POST /sport/recommend ...          ✅ OK
```

### Couverture de code

```bash
pytest --cov=app --cov-report=html
# Rapport HTML dans htmlcov/index.html
```

La couverture mesure le pourcentage de lignes de code exécutées pendant les tests.
Une couverture de 80%+ est généralement visée, mais la qualité des tests importe
plus que le pourcentage.

---

## 15. Flux complets de bout en bout

### Flux 1 — Analyse photo

```
1. Client envoie POST /nutrition/analyze-photo avec l'image (multipart/form-data)
2. Router vérifie le type MIME (jpeg/png/webp uniquement) et la taille (< 10MB)
3. Router appelle analyze_food_image(image_bytes)
4. vision.py envoie les bytes à HF router.huggingface.co/hf-inference/models/nateraw/food
5. HF retourne [{"label": "pizza", "score": 0.91}, {"label": "bread", "score": 0.06}]
6. _enrich_food() associe chaque label à ses macronutriments (FOOD_NUTRITION_DB)
7. Router calcule les macros totales (somme calories × quantité / 100)
8. Router tente de sauvegarder en MongoDB (non bloquant si MongoDB absent)
9. Retourne 200 avec PhotoAnalysisResponse
```

### Flux 2 — Plan nutritionnel

```
1. Client envoie POST /nutrition/recommend avec UserNutritionProfile JSON
2. FastAPI valide avec Pydantic (champs requis, types, valeurs enum)
3. Router appelle build_weekly_nutrition_plan(profile)
4. nutrition_engine.py :
   a. Mappe l'objectif ("perte_de_poids" → "fat_loss")
   b. Sélectionne les templates pour cet objectif
   c. Pour chaque jour (7), pour chaque repas (4) :
      - Filtre selon diet_type et allergies
      - Sélectionne un template par rotation cyclique
      - Exclut les aliments blacklistés
   d. Calcule les macros de chaque jour et les moyennes hebdomadaires
   e. Détecte les déséquilibres (ratio protéines/glucides/lipides)
5. Appelle generate_nutrition_message(objectif, notes, patient_id)
   → Essaie HF flan-t5-large (timeout 8s)
   → Si échec, essaie Ollama
   → Si échec, retourne message par défaut
6. Retourne NutritionRecommendation complet
7. Router sauvegarde en MongoDB (non bloquant)
8. Retourne 201
```

### Flux 3 — Programme sportif

```
1. Client envoie POST /sport/recommend avec UserSportProfile JSON
2. Validation Pydantic (objective, fitness_level, equipment sont des enums)
3. Router appelle build_weekly_sport_program(profile)
4. sport_engine.py :
   a. _filter_exercises() : sélectionne les exercices compatibles
      - Filtre par équipement (none/home/gym)
      - Filtre par niveau (beginner/intermediate/advanced)
      - Filtre par objectif (fat_loss, muscle_gain, etc.)
      - Filtre par contra-indications médicales
   b. Pour chaque jour disponible :
      - Détermine le type de séance (HIIT, Renforcement, Récupération, Repos)
      - _build_session() construit la séance avec rotation des exercices
      - Calcule la durée totale (ne dépasse pas session_duration_max_minutes)
   c. _compute_progression_notes() génère les conseils de progression
5. Appelle generate_sport_message() → même cascade HF/Ollama/défaut que nutrition
6. Retourne SportRecommendation
```

---

## Résumé des notions IA mises en œuvre

| Notion | Technologie | Fichier | Description |
|---|---|---|---|
| Classification d'images | ViT (Vision Transformer) | `vision.py` | Identifier les aliments sur une photo |
| Génération de texte | Flan-T5 (seq2seq) | `nlp.py` | Écrire des messages personnalisés |
| Filtrage par règles | Expert system | `nutrition_engine.py`, `sport_engine.py` | Recommandations sans ML |
| Score de confiance | Softmax output | `vision.py` | Probabilité de la prédiction |
| Prompt engineering | NLP | `nlp.py` | Formuler les instructions pour l'IA |
| Fallback en cascade | Architecture | `vision.py`, `nlp.py` | Résilience si une IA est indisponible |
| Inférence distante | HF Inference API | `vision.py`, `nlp.py` | Appel à un modèle GPU via HTTP |
| Progression adaptative | Feedback loop | `sport_engine.py` | Ajuster selon les retours utilisateur |
