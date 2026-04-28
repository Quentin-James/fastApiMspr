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
    """Génération de texte via Hugging Face Inference API."""
    if not settings.huggingface_api_token:
        return None

    api_url = "https://api-inference.huggingface.co/models/mistralai/Mistral-7B-Instruct-v0.1"
    headers = {"Authorization": f"Bearer {settings.huggingface_api_token}"}
    payload = {
        "inputs": prompt,
        "parameters": {"max_new_tokens": max_tokens, "temperature": 0.7},
    }
    async with httpx.AsyncClient(timeout=45) as client:
        response = await client.post(api_url, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()

    if isinstance(data, list) and data:
        generated = data[0].get("generated_text", "")
        # Retirer le prompt du résultat si HF le répète
        return generated.replace(prompt, "").strip()
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
