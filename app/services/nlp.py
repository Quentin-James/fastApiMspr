"""
Service NLP pour la génération de messages personnalisés.
Priorité : Hugging Face text-generation → Ollama (local) → message par défaut.
"""
import logging
from typing import Optional

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


async def _call_huggingface_nlp(prompt: str, max_tokens: int = 200) -> Optional[str]:
    """
    Génération de texte via Hugging Face Inference API.
    Utilise google/flan-t5-large (disponible sur le tier gratuit HF).
    Retourne None en cas d'erreur pour tomber sur le message par défaut.
    """
    if not settings.huggingface_api_token:
        return None

    # flan-t5-large : disponible sur l'API gratuite HF, bon pour la génération
    # de texte court en instruction-following
    api_url = "https://router.huggingface.co/hf-inference/models/google/flan-t5-large"
    headers = {"Authorization": f"Bearer {settings.huggingface_api_token}"}
    payload = {
        "inputs": prompt,
        "parameters": {"max_new_tokens": max_tokens, "temperature": 0.7},
    }
    try:
        async with httpx.AsyncClient(timeout=8) as client:
            response = await client.post(api_url, headers=headers, json=payload)

        if response.status_code == 503:
            # Modèle en cold start HF — pas une erreur fatale
            logger.warning("NLP HF : modèle en cours de chargement (503), utilisation du message par défaut.")
            return None

        response.raise_for_status()
        data = response.json()

        if isinstance(data, list) and data:
            generated = data[0].get("generated_text", "").strip()
            if generated and generated != prompt:
                return generated
        elif isinstance(data, dict) and "error" in data:
            logger.warning("NLP HF erreur API : %s", data["error"])

    except Exception as exc:
        logger.warning("NLP HF indisponible : %s — message par défaut utilisé.", exc)

    return None


async def _call_ollama(prompt: str, max_tokens: int = 200) -> Optional[str]:
    """Génération de texte via Ollama (serveur local)."""
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                f"{settings.ollama_url}/api/generate",
                json={
                    "model": settings.ollama_model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"num_predict": max_tokens, "temperature": 0.7},
                },
            )
            response.raise_for_status()
            return response.json().get("response", "").strip()
    except Exception as exc:
        logger.warning("Ollama indisponible : %s", exc)
        return None


async def generate_nutrition_message(
    objective: str,
    balance_notes: str,
    patient_id: str,
) -> str:
    """Génère un message nutritionnel personnalisé."""
    prompt = (
        f"Tu es un nutritionniste bienveillant. Rédige un court message d'encouragement "
        f"(3-4 phrases) en français pour un patient dont l'objectif est '{objective}'. "
        f"Points nutritionnels importants : {balance_notes}. "
        f"Le message doit être positif, motivant et pratique."
    )

    message = await _call_huggingface_nlp(prompt) or await _call_ollama(prompt)

    if not message:
        # Message par défaut
        message = (
            f"Votre plan nutritionnel est adapté à votre objectif de {objective}. "
            "Prenez soin de bien vous hydrater et de respecter les horaires de repas proposés. "
            "N'hésitez pas à ajuster les portions selon votre faim."
        )
    return message


async def generate_sport_message(
    objective: str,
    fitness_level: str,
    progression_notes: str,
) -> str:
    """Génère un message sportif personnalisé."""
    prompt = (
        f"Tu es un coach sportif bienveillant. Rédige un court message d'encouragement "
        f"(3-4 phrases) en français pour un patient de niveau '{fitness_level}' "
        f"avec pour objectif '{objective}'. "
        f"Notes de progression : {progression_notes}. "
        f"Le message doit être positif et motivant."
    )

    message = await _call_huggingface_nlp(prompt) or await _call_ollama(prompt)

    if not message:
        message = (
            f"Votre programme sportif est conçu pour votre niveau {fitness_level} "
            f"et votre objectif de {objective}. "
            "Respectez les temps de récupération et écoutez votre corps. "
            "La régularité est la clé du succès !"
        )
    return message
