"""Router FastAPI — recommandations sportives."""
import logging

from fastapi import APIRouter, Depends, HTTPException, status

from app.database import get_db
from app.models.sport import FeedbackRequest, SportRecommendation, UserSportProfile
from app.repositories.recommendation_repository import RecommendationRepository
from app.services.sport_engine import build_weekly_sport_program

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/sport", tags=["Sport"])


def get_repo() -> RecommendationRepository:
    return RecommendationRepository(get_db())


@router.post(
    "/recommend",
    response_model=SportRecommendation,
    summary="Générer un programme sportif hebdomadaire",
    description=(
        "Accepte le profil utilisateur (objectif, niveau, équipement, disponibilités, limitations) "
        "et retourne un programme sportif sur 7 jours avec progression adaptative. "
        "Le programme est sauvegardé en MongoDB."
    ),
    status_code=status.HTTP_201_CREATED,
)
async def recommend_sport(
    profile: UserSportProfile,
    repo: RecommendationRepository = Depends(get_repo),
) -> SportRecommendation:
    # Récupérer les feedbacks existants du patient pour la progression adaptative
    past_programs = await repo.get_sport_program_by_id("000000000000000000000000")  # placeholder
    previous_feedbacks = []  # En prod : charger les feedbacks MongoDB

    try:
        recommendation = await build_weekly_sport_program(profile, previous_feedbacks)
    except Exception as exc:
        logger.exception("Erreur lors de la génération du programme sportif.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur interne : {str(exc)}",
        )

    # Persister en MongoDB
    doc = recommendation.model_dump()
    doc["patientId"] = profile.patient_id
    doc["type"] = "sport_program"
    program_id = await repo.save_sport_program(doc)
    logger.info("Programme sportif sauvegardé : %s", program_id)

    return recommendation


@router.put(
    "/feedback/{recommendation_id}",
    summary="Soumettre un retour sur une recommandation sportive",
    description=(
        "Permet à l'utilisateur de noter la recommandation (1-5 étoiles) "
        "et d'indiquer si elle était trop difficile / trop facile. "
        "Ces retours alimentent la progression adaptative."
    ),
    status_code=status.HTTP_200_OK,
)
async def submit_feedback(
    recommendation_id: str,
    feedback: FeedbackRequest,
    repo: RecommendationRepository = Depends(get_repo),
) -> dict:
    updated = await repo.update_sport_program_feedback(
        recommendation_id, feedback.model_dump()
    )

    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Recommandation introuvable : {recommendation_id}",
        )

    return {
        "message": "Retour enregistré avec succès. Votre prochain programme sera adapté.",
        "recommendation_id": recommendation_id,
        "rating": feedback.rating,
    }
