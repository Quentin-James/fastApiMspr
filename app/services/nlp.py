"""
Service NLP pour la génération de messages personnalisés et l'interprétation des limitations.
Priorité : Hugging Face text-generation → Ollama (local) → message par défaut.
"""
import logging
import re
from typing import List, Optional

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


_STOP_WORDS = {
    "en", "le", "la", "les", "de", "du", "des", "un", "une", "au", "aux",
    "et", "ou", "mon", "ma", "mes", "son", "sa", "ses", "pas", "plus",
    "avec", "sans", "sur", "sous", "dans", "par", "pour", "qui", "que",
    "mais", "donc", "car", "ni", "je", "tu", "il", "elle", "nous", "vous",
    "ils", "elles", "me", "te", "se", "lui", "leur", "est", "ont", "fait",
}


def _extract_keywords_basic(limitations: List[str]) -> List[str]:
    """
    Extraction heuristique de mots-clés sans LLM.
    Retire les mots grammaticaux et retourne les termes significatifs.
    Exemple : 'jambe en moins' → ['jambe', 'moins']
              'bras cassé'     → ['bras', 'casse']
    """
    keywords = []
    for lim in limitations:
        words = re.findall(r"[a-zA-ZÀ-ÿ]+", lim.lower())
        keywords.extend(w for w in words if w not in _STOP_WORDS and len(w) > 2)
    return list(dict.fromkeys(keywords))  # dédoublonnage ordre-préservant


async def interpret_physical_limitations(limitations: List[str]) -> List[str]:
    """
    Convertit des limitations physiques en langage naturel (ex : 'jambe en moins', 'cancer',
    'bras cassé') en une liste de mots-clés à exclure du programme sportif.

    Cascade :
    1. LLM (HF flan-t5 ou Ollama) — retourne des mots-clés musculaires riches et contextuels
    2. Extraction basique sans LLM — extrait les mots significatifs de la phrase utilisateur
       (toujours actif, couvre les cas simples même sans token HF)
    """
    if not limitations:
        return []

    limitations_str = ", ".join(limitations)
    prompt = (
        "Tu es kinésithérapeute. "
        f"Limitations physiques du patient : {limitations_str}. "
        "Liste les mots-clés à éviter dans un programme sportif : groupes musculaires "
        "(ex: quadriceps, pectoraux, épaules), types de mouvement (ex: saut, course, impact), "
        "intensité (ex: intense, explosif). "
        "Réponds UNIQUEMENT avec des mots-clés français séparés par des virgules, sans phrase."
    )

    raw = await _call_huggingface_nlp(prompt, max_tokens=60) or await _call_ollama(prompt, max_tokens=60)

    if raw:
        raw_clean = re.sub(r"[.;!\?]", ",", raw)
        tokens = [t.strip().lower() for t in raw_clean.split(",")]
        llm_keywords = [
            t for t in tokens
            if 2 < len(t) <= 30
            and t not in _STOP_WORDS
            and not any(t.startswith(p) for p in ("tu ", "le ", "la ", "je "))
        ]
        if llm_keywords:
            logger.info("LLM '%s' → exclusions : %s", limitations_str, llm_keywords)
            return llm_keywords

    # Fallback : extraction basique depuis le texte utilisateur
    basic = _extract_keywords_basic(limitations)
    if basic:
        logger.info("Extraction basique '%s' → exclusions : %s", limitations_str, basic)
    return basic


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
