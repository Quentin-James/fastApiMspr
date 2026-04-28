"""Router FastAPI — endpoints transverses (historique, health)."""
import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status

from app.database import get_db
from app.repositories.recommendation_repository import RecommendationRepository

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Transverse"])


def get_repo() -> RecommendationRepository:
    return RecommendationRepository(get_db())


@router.get(
    "/health",
    summary="Health check",
    description="Endpoint de vérification de l'état du service (utile pour le monitoring côté Spring).",
    status_code=status.HTTP_200_OK,
)
async def health_check() -> dict:
    return {
        "status": "ok",
        "service": "mspr-ia-microservice",
        "version": "1.0.0",
    }


@router.get(
    "/recommendations/{patient_id}",
    summary="Historique des recommandations d'un patient",
    description=(
        "Retourne l'historique complet des recommandations (nutrition + sport) "
        "d'un patient, triées par date décroissante."
    ),
    status_code=status.HTTP_200_OK,
)
async def get_patient_recommendations(
    patient_id: str,
    limit: int = 50,
    repo: RecommendationRepository = Depends(get_repo),
) -> dict:
    if limit > 200:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La limite maximale est 200.",
        )

    recommendations = await repo.get_recommendations_by_patient(patient_id, limit)
    meal_plans = await repo.get_meal_plans_by_patient(patient_id, limit)

    return {
        "patient_id": patient_id,
        "total": len(recommendations) + len(meal_plans),
        "general_recommendations": recommendations,
        "nutrition_plans": meal_plans,
    }
