"""
Client HTTP asynchrone vers le backend Java Spring Boot.

Responsabilité unique :
  - Lire le profil patient depuis Java (GET /api/patients/by-clerk/{clerkUserId})
  - Pousser les recommandations IA vers Java (POST /api/recommendations)

Toutes les erreurs sont loggées et retournent None / False pour ne pas bloquer
la génération de la recommandation (résilience).
"""
import json
import logging
from typing import Optional

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

TIMEOUT = 10  # secondes


# ─── Modèles de données (Java DTOs côté Python) ───────────────────────────────

class PatientProfile:
    """
    Profil patient tel que retourné par GET /api/patients/by-clerk/{clerkUserId}.
    Correspond au DietDTO Java.
    """
    def __init__(self, data: dict):
        self.patient_id: int | None     = data.get("patientId")
        self.age: int | None             = data.get("age")
        self.gender: str | None          = data.get("gender")
        self.weight_kg: float | None     = data.get("weightKg")
        self.height_cm: float | None     = data.get("heightCm")
        self.bmi: float | None           = data.get("bmi")
        # HealthProfile
        self.disease_type: str | None            = data.get("diseaseType")
        self.severity: str | None                = data.get("severity")
        self.physical_activity_level: str | None = data.get("physicalActivityLevel")
        self.daily_caloric_intake: int | None     = data.get("dailyCaloricIntake")
        self.cholesterol_mg_dl: float | None      = data.get("cholesterolMgDl")
        self.blood_pressure_mmhg: int | None      = data.get("bloodPressureMmhg")
        self.glucose_mg_dl: float | None          = data.get("glucoseMgDl")
        # DietPreference
        self.dietary_restrictions: str | None     = data.get("dietaryRestrictions")
        self.allergies: str | None                = data.get("allergies")
        self.preferred_cuisine: str | None        = data.get("preferredCuisine")
        self.weekly_exercise_frequency: int | None = data.get("weeklyExerciseFrequency")
        self.adherence_to_diet: float | None      = data.get("adherenceToDiet")


# ─── Lecture du profil patient ────────────────────────────────────────────────

async def fetch_patient_profile(clerk_user_id: str) -> Optional[PatientProfile]:
    """
    Récupère le profil complet du patient depuis Java via son ID Clerk.
    Retourne None si Java est inaccessible ou si le patient n'existe pas.
    """
    url = f"{settings.spring_backend_url}/api/patients/by-clerk/{clerk_user_id}"
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            response = await client.get(url)

        if response.status_code == 404:
            logger.info("Patient Clerk '%s' introuvable dans Java.", clerk_user_id)
            return None

        response.raise_for_status()
        return PatientProfile(response.json())

    except httpx.ConnectError:
        logger.warning("Java backend inaccessible (%s) — profil non enrichi.", settings.spring_backend_url)
        return None
    except Exception as exc:
        logger.warning("Erreur fetch_patient_profile('%s') : %s", clerk_user_id, exc)
        return None


# ─── Push des recommandations vers Java ───────────────────────────────────────

async def push_recommendation(
    clerk_user_id: str,
    recommendation_type: str,       # "nutrition" | "sport"
    content: dict,                  # le plan complet (sérialisable en JSON)
    personalized_message: str,
    objective: str,
    api_used: str,
    confidence_score: float,
    patient_id: int | None = None,
) -> bool:
    """
    Envoie la recommandation IA au backend Java (POST /api/recommendations).
    Retourne True si l'envoi a réussi, False sinon (non bloquant).
    """
    url = f"{settings.spring_backend_url}/api/recommendations"
    payload = {
        "clerkUserId":         clerk_user_id,
        "patientId":           patient_id,
        "recommendationType":  recommendation_type,
        "content":             json.dumps(content, ensure_ascii=False, default=str),
        "personalizedMessage": personalized_message,
        "objective":           objective,
        "apiUsed":             api_used,
        "confidenceScore":     confidence_score,
    }

    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            response = await client.post(url, json=payload)
        response.raise_for_status()
        logger.info(
            "Recommandation %s poussée vers Java (clerk=%s, id=%s).",
            recommendation_type, clerk_user_id, response.json().get("id"),
        )
        return True

    except httpx.ConnectError:
        logger.warning("Java backend inaccessible — recommandation non persistée côté Java.")
        return False
    except Exception as exc:
        logger.warning("Erreur push_recommendation (clerk=%s) : %s", clerk_user_id, exc)
        return False
