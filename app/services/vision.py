"""
Service de reconnaissance visuelle des aliments.

Cascade d'appel : Hugging Face → Google Vision API → mock (dev sans clé) → erreur 503.

Responsabilité : orchestrer les appels API et enrichir les labels avec les données nutritionnelles.
Les données (FOOD_NUTRITION_DB, MOCK_FOODS) sont dans app/data/food_db.py.
"""
import base64
import logging
from typing import List

import httpx

from app.config import settings
from app.data.food_db import DEFAULT_QUANTITY_G, FOOD_NUTRITION_DB, MOCK_FOODS
from app.models.nutrition import FoodItem

logger = logging.getLogger(__name__)


# ─── Normalisation et enrichissement ─────────────────────────────────────────

def _normalize_label(label: str) -> str:
    """
    Convertit un label HF/Google en clé de lookup dans FOOD_NUTRITION_DB.
    HF retourne parfois « carbonara, spaghetti carbonara » — on tente plusieurs fragments.
    """
    clean = label.lower().strip()

    if clean in FOOD_NUTRITION_DB:
        return clean

    first_word = clean.split(",")[0].strip()
    if first_word in FOOD_NUTRITION_DB:
        return first_word

    for fragment in clean.replace(",", " ").split():
        if fragment in FOOD_NUTRITION_DB:
            return fragment

    for key in FOOD_NUTRITION_DB:
        if key in clean:
            return key

    return first_word  # inconnu → FoodItem sans macros


def _enrich_food(label: str, confidence: float) -> FoodItem:
    """Associe un label détecté à ses données nutritionnelles."""
    key = _normalize_label(label)
    nutrition = FOOD_NUTRITION_DB.get(key, {})
    return FoodItem(
        name=label,
        confidence=round(confidence, 4),
        quantity_g=DEFAULT_QUANTITY_G,
        **nutrition,
    )


# ─── Appels API ───────────────────────────────────────────────────────────────

async def _call_huggingface(image_bytes: bytes) -> List[FoodItem]:
    """Classification d'image via Hugging Face Inference API."""
    if not settings.huggingface_api_token:
        raise RuntimeError("HUGGINGFACE_API_TOKEN non configuré.")

    api_url = (
        f"https://router.huggingface.co/hf-inference/models/"
        f"{settings.huggingface_food_model}"
    )
    headers = {
        "Authorization": f"Bearer {settings.huggingface_api_token}",
        "Content-Type": "application/octet-stream",
    }

    async with httpx.AsyncClient(timeout=45) as client:
        response = await client.post(api_url, headers=headers, content=image_bytes)

    logger.debug("HF status=%s body=%s", response.status_code, response.text[:200])

    if response.status_code == 401:
        raise RuntimeError(
            "Token Hugging Face invalide ou expiré (401). "
            "Vérifiez HUGGINGFACE_API_TOKEN dans votre .env."
        )
    if response.status_code == 403:
        raise RuntimeError(
            f"Accès refusé au modèle {settings.huggingface_food_model} (403). "
            "Vérifiez les permissions du token ou acceptez les conditions du modèle sur HuggingFace."
        )
    if response.status_code == 404:
        raise RuntimeError(
            f"Modèle Hugging Face introuvable : {settings.huggingface_food_model} (404). "
            "Vérifiez HUGGINGFACE_FOOD_MODEL dans votre .env."
        )
    if response.status_code == 503:
        data = response.json()
        estimated = data.get("estimated_time", "?")
        raise RuntimeError(
            f"Modèle Hugging Face en cours de chargement (estimated_time={estimated}s). "
            "Réessayez dans quelques secondes."
        )

    response.raise_for_status()
    predictions = response.json()

    if isinstance(predictions, dict) and "error" in predictions:
        raise RuntimeError(f"Erreur Hugging Face : {predictions['error']}")

    if isinstance(predictions, list) and predictions:
        foods = [
            _enrich_food(pred["label"], pred["score"])
            for pred in predictions[:8]
            if pred.get("score", 0) > 0.02
        ]
        logger.info("HF : %d label(s) reçu(s), %d retenus.", len(predictions), len(foods))
        return foods

    logger.warning("HF : réponse inattendue → %s", predictions)
    return []


async def _call_google_vision(image_bytes: bytes) -> List[FoodItem]:
    """Détection de labels via Google Vision API (fallback)."""
    if not settings.google_vision_api_key:
        raise RuntimeError("GOOGLE_VISION_API_KEY non configuré.")

    api_url = (
        f"https://vision.googleapis.com/v1/images:annotate"
        f"?key={settings.google_vision_api_key}"
    )
    payload = {
        "requests": [{
            "image": {"content": base64.b64encode(image_bytes).decode()},
            "features": [{"type": "LABEL_DETECTION", "maxResults": 10}],
        }]
    }
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(api_url, json=payload)
        response.raise_for_status()
        data = response.json()

    labels = data["responses"][0].get("labelAnnotations", [])
    foods = [
        _enrich_food(label["description"], label["score"])
        for label in labels[:8]
        if label.get("score", 0) > 0.4
    ]
    logger.info("Google Vision : %d label(s) retenu(s).", len(foods))
    return foods


def _mock_analysis() -> tuple[List[FoodItem], str]:
    """Données fictives pour le développement (aucune clé API configurée)."""
    foods = [_enrich_food(item["label"], item["score"]) for item in MOCK_FOODS]
    logger.warning(
        "⚠️  Mode MOCK activé — configurez HUGGINGFACE_API_TOKEN ou "
        "GOOGLE_VISION_API_KEY pour une vraie analyse."
    )
    return foods, "mock_dev"


# ─── Point d'entrée public ────────────────────────────────────────────────────

async def analyze_food_image(image_bytes: bytes) -> tuple[List[FoodItem], str]:
    """
    Analyse une image alimentaire et retourne (liste_aliments, api_utilisée).
    Cascade : Hugging Face → Google Vision → mock (dev sans clé) → erreur 503.
    """
    last_error = "Aucune API configurée."

    try:
        foods = await _call_huggingface(image_bytes)
        if foods:
            return foods, "huggingface"
        last_error = "Hugging Face n'a détecté aucun aliment sur cette image."
    except RuntimeError as exc:
        last_error = str(exc)
        logger.warning("Hugging Face indisponible : %s — passage au fallback.", exc)
    except Exception as exc:
        last_error = str(exc)
        logger.warning("Erreur Hugging Face : %s", exc)

    try:
        foods = await _call_google_vision(image_bytes)
        if foods:
            return foods, "google_vision"
        last_error = "Google Vision n'a détecté aucun aliment sur cette image."
    except RuntimeError as exc:
        last_error = str(exc)
        logger.warning("Google Vision indisponible : %s", exc)
    except Exception as exc:
        last_error = str(exc)
        logger.error("Erreur Google Vision : %s", exc)

    # Fallback mock : toutes les APIs ont échoué → on renvoie des données fictives
    # plutôt qu'un 503 (utile en démo / hébergement gratuit sans clés valides)
    logger.warning(
        "⚠️ Toutes les APIs de vision ont échoué → mode MOCK "
        "(APP_ENV=%s). Dernière erreur : %s",
        settings.app_env, last_error,
    )
    return _mock_analysis()
