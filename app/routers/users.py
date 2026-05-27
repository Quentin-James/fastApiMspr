"""Router FastAPI - profils utilisateurs et historique recommandations."""

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.database import get_db
from app.models.user_profile import (
    UserProfileDocument,
    UserProfileUpdate,
    UserRecommendationsResponse,
)
from app.repositories.recommendation_repository import RecommendationRepository

router = APIRouter(prefix="/users", tags=["Users"])


def get_repo() -> RecommendationRepository:
    return RecommendationRepository(get_db())


@router.put(
    "/{patient_id}/profile",
    response_model=UserProfileDocument,
    summary="Créer ou mettre à jour le profil utilisateur",
    status_code=status.HTTP_200_OK,
)
async def upsert_profile(
    patient_id: str,
    payload: UserProfileUpdate,
    repo: RecommendationRepository = Depends(get_repo),
) -> UserProfileDocument:
    update_data = payload.model_dump(exclude_none=True)
    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Aucune donnée à mettre à jour.",
        )

    saved = await repo.upsert_user_profile(patient_id, update_data)
    return UserProfileDocument(**saved)


@router.get(
    "/{patient_id}/profile",
    response_model=UserProfileDocument,
    summary="Récupérer le profil utilisateur",
    status_code=status.HTTP_200_OK,
)
async def get_profile(
    patient_id: str,
    repo: RecommendationRepository = Depends(get_repo),
) -> UserProfileDocument:
    profile = await repo.get_user_profile(patient_id)
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profil utilisateur introuvable.",
        )
    return UserProfileDocument(**profile)


@router.get(
    "/{patient_id}/recommendations",
    response_model=UserRecommendationsResponse,
    summary="Lister les recommandations nutrition et sport d'un utilisateur",
    status_code=status.HTTP_200_OK,
)
async def list_user_recommendations(
    patient_id: str,
    limit: int = Query(default=10, ge=1, le=100),
    repo: RecommendationRepository = Depends(get_repo),
) -> UserRecommendationsResponse:
    meal_plans = await repo.list_meal_plans(patient_id, limit)
    sport_programs = await repo.list_sport_programs(patient_id, limit)

    return UserRecommendationsResponse(
        patient_id=patient_id,
        meal_plans=meal_plans,
        sport_programs=sport_programs,
    )
