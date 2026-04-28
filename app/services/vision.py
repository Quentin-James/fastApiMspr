"""
Service de reconnaissance visuelle des aliments.
Priorité : Hugging Face → Google Vision API → mode dev mock → erreur structurée.
"""
import base64
import logging
from typing import List

import httpx

from app.config import settings
from app.models.nutrition import FoodItem

logger = logging.getLogger(__name__)

# ─── Base nutritionnelle ──────────────────────────────────────────────────────
# Clés en minuscules, sans accents, avec variantes communes (labels ImageNet / HF)
FOOD_NUTRITION_DB: dict = {
    # Féculents / céréales
    "pizza": {"calories_per_100g": 266, "proteins_g": 11, "carbs_g": 33, "fats_g": 10},
    "bread": {"calories_per_100g": 265, "proteins_g": 9, "carbs_g": 49, "fats_g": 3.2},
    "bagel": {"calories_per_100g": 250, "proteins_g": 10, "carbs_g": 48, "fats_g": 1.5},
    "rice": {"calories_per_100g": 130, "proteins_g": 2.7, "carbs_g": 28, "fats_g": 0.3},
    "pasta": {"calories_per_100g": 131, "proteins_g": 5, "carbs_g": 25, "fats_g": 1.1},
    "spaghetti": {"calories_per_100g": 131, "proteins_g": 5, "carbs_g": 25, "fats_g": 1.1},
    "noodle": {"calories_per_100g": 138, "proteins_g": 4.5, "carbs_g": 25, "fats_g": 2},
    "waffle": {"calories_per_100g": 291, "proteins_g": 8, "carbs_g": 37, "fats_g": 13},
    "pancake": {"calories_per_100g": 227, "proteins_g": 6, "carbs_g": 28, "fats_g": 10},
    "french loaf": {"calories_per_100g": 270, "proteins_g": 9, "carbs_g": 52, "fats_g": 2},
    # Protéines animales
    "chicken": {"calories_per_100g": 165, "proteins_g": 31, "carbs_g": 0, "fats_g": 3.6},
    "hen": {"calories_per_100g": 165, "proteins_g": 31, "carbs_g": 0, "fats_g": 3.6},
    "steak": {"calories_per_100g": 271, "proteins_g": 26, "carbs_g": 0, "fats_g": 18},
    "beef": {"calories_per_100g": 250, "proteins_g": 26, "carbs_g": 0, "fats_g": 17},
    "pork": {"calories_per_100g": 242, "proteins_g": 27, "carbs_g": 0, "fats_g": 14},
    "ham": {"calories_per_100g": 145, "proteins_g": 17, "carbs_g": 2, "fats_g": 7},
    "sausage": {"calories_per_100g": 301, "proteins_g": 13, "carbs_g": 2, "fats_g": 27},
    "salmon": {"calories_per_100g": 208, "proteins_g": 20, "carbs_g": 0, "fats_g": 13},
    "fish": {"calories_per_100g": 130, "proteins_g": 22, "carbs_g": 0, "fats_g": 4},
    "tuna": {"calories_per_100g": 132, "proteins_g": 28, "carbs_g": 0, "fats_g": 1},
    "shrimp": {"calories_per_100g": 85, "proteins_g": 18, "carbs_g": 0, "fats_g": 1},
    "egg": {"calories_per_100g": 155, "proteins_g": 13, "carbs_g": 1.1, "fats_g": 11},
    # Produits laitiers
    "cheese": {"calories_per_100g": 402, "proteins_g": 25, "carbs_g": 1.3, "fats_g": 33},
    "yogurt": {"calories_per_100g": 59, "proteins_g": 10, "carbs_g": 3.6, "fats_g": 0.4},
    "milk": {"calories_per_100g": 61, "proteins_g": 3.2, "carbs_g": 4.8, "fats_g": 3.3},
    "ice cream": {"calories_per_100g": 207, "proteins_g": 3.5, "carbs_g": 24, "fats_g": 11},
    # Fruits
    "apple": {"calories_per_100g": 52, "proteins_g": 0.3, "carbs_g": 14, "fats_g": 0.2},
    "banana": {"calories_per_100g": 89, "proteins_g": 1.1, "carbs_g": 23, "fats_g": 0.3},
    "orange": {"calories_per_100g": 47, "proteins_g": 0.9, "carbs_g": 12, "fats_g": 0.1},
    "strawberry": {"calories_per_100g": 32, "proteins_g": 0.7, "carbs_g": 8, "fats_g": 0.3},
    "lemon": {"calories_per_100g": 29, "proteins_g": 1.1, "carbs_g": 9, "fats_g": 0.3},
    "fig": {"calories_per_100g": 74, "proteins_g": 0.8, "carbs_g": 19, "fats_g": 0.3},
    "pineapple": {"calories_per_100g": 50, "proteins_g": 0.5, "carbs_g": 13, "fats_g": 0.1},
    "pomegranate": {"calories_per_100g": 83, "proteins_g": 1.7, "carbs_g": 19, "fats_g": 1.2},
    # Légumes
    "salad": {"calories_per_100g": 15, "proteins_g": 1.3, "carbs_g": 2.9, "fats_g": 0.2},
    "broccoli": {"calories_per_100g": 34, "proteins_g": 2.8, "carbs_g": 7, "fats_g": 0.4},
    "mushroom": {"calories_per_100g": 22, "proteins_g": 3.1, "carbs_g": 3.3, "fats_g": 0.3},
    "cauliflower": {"calories_per_100g": 25, "proteins_g": 1.9, "carbs_g": 5, "fats_g": 0.3},
    "corn": {"calories_per_100g": 86, "proteins_g": 3.2, "carbs_g": 19, "fats_g": 1.2},
    "artichoke": {"calories_per_100g": 53, "proteins_g": 3, "carbs_g": 11, "fats_g": 0.2},
    "cucumber": {"calories_per_100g": 16, "proteins_g": 0.7, "carbs_g": 3.6, "fats_g": 0.1},
    "bell pepper": {"calories_per_100g": 31, "proteins_g": 1, "carbs_g": 6, "fats_g": 0.3},
    # Plats composés / snacks
    "burger": {"calories_per_100g": 295, "proteins_g": 17, "carbs_g": 24, "fats_g": 14},
    "hotdog": {"calories_per_100g": 290, "proteins_g": 11, "carbs_g": 23, "fats_g": 18},
    "sandwich": {"calories_per_100g": 250, "proteins_g": 12, "carbs_g": 30, "fats_g": 9},
    "soup": {"calories_per_100g": 50, "proteins_g": 3, "carbs_g": 7, "fats_g": 1.5},
    "guacamole": {"calories_per_100g": 152, "proteins_g": 2, "carbs_g": 9, "fats_g": 13},
    "carbonara": {"calories_per_100g": 320, "proteins_g": 15, "carbs_g": 38, "fats_g": 12},
    "lasagna": {"calories_per_100g": 135, "proteins_g": 8, "carbs_g": 13, "fats_g": 5},
    "burrito": {"calories_per_100g": 206, "proteins_g": 8, "carbs_g": 26, "fats_g": 8},
    "taco": {"calories_per_100g": 218, "proteins_g": 9, "carbs_g": 23, "fats_g": 10},
    "sushi": {"calories_per_100g": 150, "proteins_g": 6, "carbs_g": 26, "fats_g": 2},
    # Pâtisseries / desserts
    "chocolate": {"calories_per_100g": 546, "proteins_g": 5, "carbs_g": 60, "fats_g": 31},
    "cake": {"calories_per_100g": 347, "proteins_g": 5, "carbs_g": 56, "fats_g": 12},
    "donut": {"calories_per_100g": 452, "proteins_g": 5, "carbs_g": 51, "fats_g": 25},
    "pretzel": {"calories_per_100g": 380, "proteins_g": 9, "carbs_g": 80, "fats_g": 3},
    # Graisses / condiments
    "avocado": {"calories_per_100g": 160, "proteins_g": 2, "carbs_g": 9, "fats_g": 15},
    "butter": {"calories_per_100g": 717, "proteins_g": 0.9, "carbs_g": 0.1, "fats_g": 81},
}

DEFAULT_QUANTITY_G = 150.0

# Aliments de démonstration quand aucune API n'est disponible (mode dev)
MOCK_FOODS = [
    {"label": "chicken", "score": 0.82},
    {"label": "broccoli", "score": 0.74},
    {"label": "rice", "score": 0.68},
]


def _normalize_label(label: str) -> str:
    """Normalise un label HF/Google en clé de lookup."""
    # HF retourne parfois "carbonara, spaghetti carbonara" — on prend le 1er terme
    # ou on essaie plusieurs fragments si le 1er ne matche pas
    clean = label.lower().strip()
    fragments = [f.strip() for f in clean.replace(",", " ").split()]

    # Essai exact d'abord
    if clean in FOOD_NUTRITION_DB:
        return clean
    first_word = clean.split(",")[0].strip()
    if first_word in FOOD_NUTRITION_DB:
        return first_word

    # Essai mot par mot
    for fragment in fragments:
        if fragment in FOOD_NUTRITION_DB:
            return fragment

    # Essai de correspondance partielle (le label contient une clé connue)
    for key in FOOD_NUTRITION_DB:
        if key in clean:
            return key

    return first_word  # pas dans la DB → FoodItem sans macros


def _enrich_food(label: str, confidence: float) -> FoodItem:
    """Enrichit un label détecté avec ses données nutritionnelles."""
    key = _normalize_label(label)
    nutrition = FOOD_NUTRITION_DB.get(key, {})
    return FoodItem(
        name=label,
        confidence=round(confidence, 4),
        quantity_g=DEFAULT_QUANTITY_G,
        **nutrition,
    )


async def _call_huggingface(image_bytes: bytes) -> List[FoodItem]:
    """Appel au modèle Hugging Face de classification d'images."""
    if not settings.huggingface_api_token:
        raise RuntimeError("HUGGINGFACE_API_TOKEN non configuré.")

    api_url = f"https://api-inference.huggingface.co/models/{settings.huggingface_food_model}"
    headers = {
        "Authorization": f"Bearer {settings.huggingface_api_token}",
        "Content-Type": "application/octet-stream",
    }

    async with httpx.AsyncClient(timeout=45) as client:
        response = await client.post(api_url, headers=headers, content=image_bytes)

    logger.debug("HF status=%s body=%s", response.status_code, response.text[:200])

    # Modèle en cours de chargement (cold start HF)
    if response.status_code == 503:
        data = response.json()
        estimated = data.get("estimated_time", "?")
        raise RuntimeError(
            f"Modèle Hugging Face en cours de chargement (estimated_time={estimated}s). "
            "Réessayez dans quelques secondes."
        )

    response.raise_for_status()
    predictions = response.json()

    # Réponse d'erreur HF en JSON (ex: {"error": "..."})
    if isinstance(predictions, dict) and "error" in predictions:
        raise RuntimeError(f"Erreur Hugging Face : {predictions['error']}")

    if isinstance(predictions, list) and predictions:
        foods = [
            _enrich_food(pred["label"], pred["score"])
            for pred in predictions[:8]
            if pred.get("score", 0) > 0.02
        ]
        logger.info("HF : %d label(s) reçu(s), dont %d retenus.", len(predictions), len(foods))
        return foods

    logger.warning("HF : réponse inattendue → %s", predictions)
    return []


async def _call_google_vision(image_bytes: bytes) -> List[FoodItem]:
    """Appel à Google Vision API (label detection) comme fallback."""
    if not settings.google_vision_api_key:
        raise RuntimeError("GOOGLE_VISION_API_KEY non configuré.")

    api_url = (
        f"https://vision.googleapis.com/v1/images:annotate"
        f"?key={settings.google_vision_api_key}"
    )
    payload = {
        "requests": [
            {
                "image": {"content": base64.b64encode(image_bytes).decode()},
                "features": [{"type": "LABEL_DETECTION", "maxResults": 10}],
            }
        ]
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
    """Retourne des aliments fictifs pour le développement (aucune clé API disponible)."""
    foods = [_enrich_food(item["label"], item["score"]) for item in MOCK_FOODS]
    logger.warning(
        "⚠️  Mode MOCK activé (aucune API vision configurée). "
        "Configurez HUGGINGFACE_API_TOKEN ou GOOGLE_VISION_API_KEY pour une vraie analyse."
    )
    return foods, "mock_dev"


async def analyze_food_image(image_bytes: bytes) -> tuple[List[FoodItem], str]:
    """
    Analyse une image alimentaire.
    Retourne (liste_aliments, api_utilisée).

    Cascade : Hugging Face → Google Vision → mock (dev uniquement) → erreur 503
    """
    last_error = "Aucune API configurée."

    # 1. Tentative Hugging Face
    foods = await _call_huggingface(image_bytes)
    if foods:
        logger.info("Vision : %d aliment(s) détecté(s) via Hugging Face.", len(foods))
        return foods, "huggingface"
    # Liste vide = le modèle n'a rien retourné (image floue, etc.)
    last_error = "Hugging Face n'a détecté aucun aliment sur cette image."

    # 2. Fallback Google Vision
    try:
        foods = await _call_google_vision(image_bytes)
        if foods:
            logger.info("Vision : %d aliment(s) détecté(s) via Google Vision.", len(foods))
            return foods, "google_vision"
        last_error = "Google Vision n'a détecté aucun aliment sur cette image."
    except RuntimeError as exc:
        last_error = str(exc)
        logger.warning("Google Vision indisponible : %s", exc)
    except Exception as exc:
        last_error = str(exc)
        logger.error("Erreur Google Vision : %s", exc)

    # 3. Mode mock en développement
    if settings.app_env in ("development", "dev"):
        return _mock_analysis()

    # 4. Production sans API disponible → erreur structurée
    raise RuntimeError(
        f"Aucune API de vision disponible. Dernière erreur : {last_error}"
    )
