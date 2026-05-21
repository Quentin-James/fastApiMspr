"""Router FastAPI — recommandations sportives."""
import logging

from fastapi import APIRouter, Depends, HTTPException, status

from app.database import get_db
from app.models.sport import FitnessLevel, SportRecommendation, UserSportProfile
from app.repositories.recommendation_repository import RecommendationRepository
from app.services.sport_engine import build_weekly_sport_program
from app.services.spring_client import fetch_patient_profile, push_recommendation

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/sport", tags=["Sport"])

# Correspondance physical_activity_level Java → FitnessLevel FastAPI
_ACTIVITY_TO_LEVEL: dict[str, FitnessLevel] = {
    "sedentary":      FitnessLevel.beginner,
    "light":          FitnessLevel.beginner,
    "moderate":       FitnessLevel.intermediate,
    "active":         FitnessLevel.intermediate,
    "very_active":    FitnessLevel.advanced,
    "extremely_active": FitnessLevel.advanced,
}


def get_repo() -> RecommendationRepository:
    return RecommendationRepository(get_db())


# ─── Programme sportif ────────────────────────────────────────────────────────

@router.post(
    "/recommend",
    response_model=SportRecommendation,
    summary="Générer un programme sportif hebdomadaire",
    description=(
        "Accepte le profil utilisateur (objectif, niveau, équipement, disponibilités, limitations) "
        "et retourne un programme sportif sur 7 jours avec progression adaptative. "
        "Si clerk_user_id est fourni : enrichit le profil depuis le backend Java "
        "(maladie → limitations, activité physique → niveau) et pousse le résultat vers Java."
    ),
    status_code=status.HTTP_201_CREATED,
)
async def recommend_sport(
    profile: UserSportProfile,
    repo: RecommendationRepository = Depends(get_repo),
) -> SportRecommendation:

    # ── 1. Enrichissement depuis Java si clerk_user_id fourni ────────────────
    patient_id_java: int | None = None

    if profile.clerk_user_id:
        java_profile = await fetch_patient_profile(profile.clerk_user_id)
        if java_profile:
            patient_id_java = java_profile.patient_id
            logger.info(
                "Profil Java récupéré pour clerk=%s (patient_id=%s)",
                profile.clerk_user_id, patient_id_java,
            )
            updates: dict = {}

            # disease_type + severity → ajouter aux limitations physiques
            extra_limitations = list(profile.limitations)
            if java_profile.disease_type:
                lim = java_profile.disease_type
                if java_profile.severity:
                    lim += f" {java_profile.severity}"
                if lim not in extra_limitations:
                    extra_limitations.append(lim)
            if extra_limitations != list(profile.limitations):
                updates["limitations"] = extra_limitations

            # physical_activity_level Java → fitness_level si non précisé
            if java_profile.physical_activity_level:
                mapped = _ACTIVITY_TO_LEVEL.get(
                    java_profile.physical_activity_level.lower(),
                    None,
                )
                # On n'écrase que si le client n'a pas envoyé de valeur explicite
                # (le profil par défaut n'existe pas dans l'enum, donc on laisse le profil fourni)
                if mapped and mapped != profile.fitness_level:
                    logger.info(
                        "Niveau fitness ajusté depuis Java : %s → %s",
                        java_profile.physical_activity_level, mapped.value,
                    )
                    updates["fitness_level"] = mapped

            if updates:
                profile = profile.model_copy(update=updates)

    # ── 2. Génération du programme ───────────────────────────────────────────
    try:
        recommendation = await build_weekly_sport_program(profile)
    except Exception as exc:
        logger.exception("Erreur lors de la génération du programme sportif.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur interne : {str(exc)}",
        )

    # ── 3. Persistance MongoDB (non bloquant) ────────────────────────────────
    try:
        doc = recommendation.model_dump()
        doc["patientId"] = profile.patient_id
        doc["type"] = "sport_program"
        program_id = await repo.save_sport_program(doc)
        logger.info("Programme sportif sauvegardé MongoDB : %s", program_id)
    except Exception as exc:
        logger.warning("Impossible de sauvegarder le programme sportif en MongoDB : %s", exc)

    # ── 4. Push vers Java (non bloquant) ─────────────────────────────────────
    if profile.clerk_user_id:
        await push_recommendation(
            clerk_user_id        = profile.clerk_user_id,
            recommendation_type  = "sport",
            content              = recommendation.model_dump(),
            personalized_message = recommendation.personalized_message,
            objective            = profile.objective.value,
            api_used             = recommendation.api_used,
            confidence_score     = recommendation.confidence_score,
            patient_id           = patient_id_java,
        )

    return recommendation
