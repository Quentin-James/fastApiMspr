# TODO — Microservice IA (FastAPI + MongoDB)

Ce dossier contiendra le microservice de recommandation IA, développé séparément du backend Spring Boot conformément aux exigences du cahier des charges (TPRE502).

**Stack cible :** Python · FastAPI · MongoDB · Hugging Face Transformers / Google Vision API · Pytest

---

## 1. Initialisation du projet

- [ ] Créer la structure de projet :
  ```
  fastapi/
  ├── app/
  │   ├── main.py              # point d'entrée FastAPI
  │   ├── config.py            # variables d'environnement (pydantic-settings)
  │   ├── database.py          # connexion MongoDB (motor ou pymongo)
  │   ├── routers/
  │   │   ├── nutrition.py     # endpoints recommandations nutritionnelles
  │   │   └── sport.py         # endpoints recommandations sportives
  │   ├── services/
  │   │   ├── vision.py        # appels API vision (Hugging Face / Google Vision)
  │   │   ├── nlp.py           # appels NLP (Hugging Face / Ollama)
  │   │   ├── nutrition_engine.py
  │   │   └── sport_engine.py
  │   ├── models/              # schémas Pydantic (request / response)
  │   └── repositories/        # accès MongoDB
  ├── tests/
  ├── requirements.txt
  ├── .env.example
  └── README.md
  ```
- [ ] Créer `requirements.txt` avec : `fastapi`, `uvicorn`, `motor` (MongoDB async), `pydantic-settings`, `httpx`, `python-multipart`, `pytest`, `pytest-asyncio`, `httpx` (client de test)
- [ ] Créer `.env.example` avec les variables nécessaires (clés API, URL MongoDB, port)
- [ ] Vérifier que le serveur démarre : `uvicorn app.main:app --reload --port 8085`

---

## 2. Connexion MongoDB

- [ ] Configurer la connexion async avec `motor` (client MongoDB asynchrone)
- [ ] Créer la collection `recommendations` : stocker chaque recommandation générée (type, contenu, patientId, date, API utilisée, score de confiance)
- [ ] Créer la collection `meal_plans` : plans de repas générés
- [ ] Créer la collection `sport_programs` : programmes sportifs générés
- [ ] Indexer par `patientId` et `created_at` pour les requêtes d'historique

---

## 3. Intégration API Vision (reconnaissance alimentaire)

- [ ] Implémenter `services/vision.py` :
  - Appel à **Hugging Face** (`google/vit-base-patch16-224` ou modèle food classification) via `httpx`
  - Appel à **Google Vision API** comme alternative / fallback
- [ ] Parser la réponse : extraire la liste des aliments détectés avec scores de confiance
- [ ] Mapper les aliments détectés vers une base de données nutritionnelle (utiliser les données existantes en PostgreSQL via appel au backend Spring, ou intégrer une source ouverte comme OpenFoodFacts)
- [ ] Calculer les macronutriments et calories à partir des aliments détectés
- [ ] Gérer le fallback : si Hugging Face est indisponible → Google Vision, si les deux tombent → réponse d'erreur structurée

---

## 4. Moteur de recommandations nutritionnelles

- [ ] Créer `POST /nutrition/analyze-photo` : accepte une image (multipart/form-data), retourne aliments + macros
- [ ] Créer `POST /nutrition/recommend` : accepte le profil utilisateur (objectif, allergies, budget, régime), retourne un plan de repas sur 7 jours
- [ ] Implémenter la logique de détection des déséquilibres (excès/déficits par rapport aux apports journaliers recommandés)
- [ ] Générer les suggestions via **NLP** (Hugging Face text generation ou Ollama en local) pour les messages personnalisés
- [ ] Sauvegarder chaque recommandation générée en MongoDB

---

## 5. Moteur de recommandations sportives

- [ ] Créer `POST /sport/recommend` : accepte profil utilisateur (objectif, niveau, équipement, disponibilités, limitations), retourne un programme hebdomadaire
- [ ] Implémenter l'algorithme de recommandation multi-critères :
  - Filtrage par objectif (perte de graisse, renforcement, endurance, santé générale)
  - Adaptation au niveau (débutant / intermédiaire / avancé)
  - Contraintes matérielles (avec/sans salle, équipements disponibles)
  - Exclusion des exercices contre-indiqués (blessures, fatigue)
- [ ] Implémenter la progression adaptative : augmenter la charge/durée selon les retours utilisateur
- [ ] Implémenter la rotation des exercices (éviter la répétition exacte d'une semaine à l'autre)
- [ ] Créer `PUT /sport/feedback/{recommendation_id}` : permettre à l'utilisateur de noter la recommandation → alimente la progression adaptative
- [ ] Sauvegarder chaque programme généré en MongoDB

---

## 6. Endpoints transverses

- [ ] Créer `GET /recommendations/{patient_id}` : historique de toutes les recommandations (nutrition + sport) d'un patient
- [ ] Créer `GET /health` : endpoint de health check (utile pour le monitoring et les fallbacks côté Spring)
- [ ] Ajouter rate limiting (ex. max 10 requêtes/minute par IP via `slowapi`)
- [ ] Configurer les headers CORS pour n'autoriser que le backend Spring et le frontend

---

## 7. Documentation OpenAPI

- [ ] Vérifier que FastAPI génère automatiquement `/docs` (Swagger UI) et `/openapi.json`
- [ ] Annoter tous les endpoints avec `summary`, `description`, exemples de request/response
- [ ] Exporter `openapi.json` comme livrable officiel
- [ ] Documenter les choix techniques (algorithmes, APIs IA utilisées, justifications) dans `/docs/choix-techniques.md`

---

## 8. Performance et métriques IA (livrable obligatoire)

- [ ] Construire un jeu de données de test annoté (photos de repas avec vérité terrain)
- [ ] Mesurer et documenter : **précision**, **rappel**, **F1-score** du module de reconnaissance alimentaire
- [ ] Mesurer la latence moyenne des appels API vision (objectif : < 3s)
- [ ] Produire le rapport de performance dans `/docs/metriques-ia.md`

---

## 9. Tests

- [ ] Écrire des tests unitaires pour `nutrition_engine.py` et `sport_engine.py` (logique pure, sans appels réseau)
- [ ] Écrire des tests d'intégration avec `httpx.AsyncClient` pour tous les endpoints (mocker les APIs externes)
- [ ] Écrire des tests de contrat MongoDB (vérifier que les documents sont bien persistés)
- [ ] Générer le rapport de couverture : `pytest --cov=app --cov-report=html`
- [ ] Objectif de couverture : ≥ 70 % sur les services critiques

---

## 10. Déploiement et opérationnel

- [ ] Créer un `Dockerfile` pour containeriser le microservice
- [ ] Créer un `docker-compose.yml` à la racine du dossier `fastapi/` incluant FastAPI + MongoDB
- [ ] Documenter la procédure de démarrage dans `README.md`
- [ ] Vérifier l'interopérabilité avec le backend Spring (appels depuis `RecommendationController` Spring → FastAPI)
