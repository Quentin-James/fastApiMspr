# Choix techniques — Microservice IA MSPR

## Architecture

Le microservice suit une architecture **clean en couches** :

```
Routers (HTTP) → Services (logique métier) → Repositories (MongoDB)
```

Les dépendances extérieures (APIs IA) sont isolées dans la couche `services/` pour faciliter les mocks en test et le remplacement d'API.

## Pourquoi FastAPI ?

FastAPI a été choisi pour ses performances asynchrones (basé sur Starlette/anyio), sa génération automatique d'OpenAPI, et sa compatibilité native avec Pydantic v2 pour la validation des données.

## Pourquoi MongoDB ?

Les recommandations sont des documents JSON de structure variable (plans de repas, programmes sportifs) — MongoDB est mieux adapté que PostgreSQL pour ce schéma flexible. Motor fournit un client 100 % async compatible avec l'event loop FastAPI.

## Stratégie de fallback IA

La vision alimentaire suit une cascade : Hugging Face (priorité) → Google Vision API (fallback) → erreur structurée 503. Cela garantit la disponibilité du service même si une API est indisponible.

Le mode mock (`MOCK_FOODS`) ne s'active qu'en `development` **et** uniquement si aucun token API n'est configuré. Avec un token défini, un échec IA remonte une erreur 503 explicite plutôt que des données fictives.

**URL de l'API HuggingFace (mise à jour 2024-2025) :**
L'ancienne URL `https://api-inference.huggingface.co/models/{model}` a migré vers
`https://router.huggingface.co/hf-inference/models/{model}`. L'ancienne URL retourne 404.

## Moteur de recommandations

Le moteur nutritionnel et sportif est basé sur des **règles métier** (filtrage multi-critères) combinées à la **génération NLP** pour personnaliser les messages. Cette approche hybride évite la dépendance totale à des modèles IA dont la disponibilité et le coût peuvent varier.

## Progression adaptative (sport)

Les retours utilisateur (rating, too_hard, too_easy) alimentent la fonction `_compute_progression_notes` qui adapte les recommandations futures. En production, ces feedbacks seraient persistés en MongoDB et rechargés à chaque nouvelle génération de programme.

## Sécurité

- Rate limiting via `slowapi` (max 10 req/min/IP)
- CORS restreint aux origines autorisées (Spring + frontend)
- Utilisateur non-root dans le container Docker
- Variables sensibles via `.env` (jamais en dur dans le code)
